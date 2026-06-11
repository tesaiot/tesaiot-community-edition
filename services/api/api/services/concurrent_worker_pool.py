# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""Concurrent worker pool for CSR/PU batch processing.

This module provides a thread pool implementation with health monitoring
for processing Protected Update CSR signing and publishing jobs concurrently.

Features:
- Configurable max workers
- Batch submission with per-job timeout
- Active job tracking for monitoring
- Graceful shutdown with wait

Usage:
    pool = ConcurrentWorkerPool(max_workers=5, name_prefix="pu-signing")
    pool.start()

    results = pool.submit_batch(
        jobs=[{"job_id": "1"}, {"job_id": "2"}],
        handler=lambda job: sign_csr(job),
        timeout=60,
    )

    pool.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FutureTimeout
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class ConcurrentWorkerPool:
    """
    Thread pool with health monitoring for CSR/PU workers.

    Provides batch job submission with timeout handling, active job tracking,
    and graceful shutdown. Each pool instance has a unique worker ID for
    job claiming attribution.
    """

    def __init__(
        self,
        max_workers: int,
        name_prefix: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize the worker pool.

        Args:
            max_workers: Maximum concurrent worker threads
            name_prefix: Thread name prefix for debugging
            logger: Optional logger instance (creates one if not provided)
        """
        self.max_workers = max_workers
        self.name_prefix = name_prefix
        self.logger = logger or logging.getLogger(f"{self.__class__.__name__}.{name_prefix}")

        self._executor: Optional[ThreadPoolExecutor] = None
        self._active_jobs: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._worker_id = f"{name_prefix}-{uuid4().hex[:8]}"
        self._started = False

        # Statistics
        self._total_submitted = 0
        self._total_succeeded = 0
        self._total_failed = 0
        self._total_timeout = 0

    @property
    def worker_id(self) -> str:
        """Unique identifier for this worker pool instance."""
        return self._worker_id

    @property
    def active_count(self) -> int:
        """Number of currently processing jobs."""
        with self._lock:
            return len(self._active_jobs)

    @property
    def is_started(self) -> bool:
        """Whether the pool is started and ready for submissions."""
        return self._started

    @property
    def stats(self) -> Dict[str, int]:
        """Return processing statistics."""
        return {
            "total_submitted": self._total_submitted,
            "total_succeeded": self._total_succeeded,
            "total_failed": self._total_failed,
            "total_timeout": self._total_timeout,
            "active_count": self.active_count,
        }

    def start(self) -> None:
        """
        Start the worker pool.

        Creates the underlying ThreadPoolExecutor. Safe to call multiple times;
        subsequent calls are no-ops if already started.
        """
        if self._started:
            self.logger.debug("Worker pool '%s' already started", self.name_prefix)
            return

        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=self.name_prefix,
        )
        self._started = True
        self.logger.info(
            "Worker pool '%s' started with %d workers (id=%s)",
            self.name_prefix,
            self.max_workers,
            self._worker_id,
        )

    def stop(self, timeout: int = 30) -> None:
        """
        Stop the worker pool gracefully.

        Waits for active jobs to complete up to the specified timeout.
        Does not cancel running futures.

        Args:
            timeout: Maximum seconds to wait for active jobs
        """
        if not self._started or not self._executor:
            self.logger.debug("Worker pool '%s' not started", self.name_prefix)
            return

        self.logger.info(
            "Stopping worker pool '%s' (active=%d, timeout=%ds)...",
            self.name_prefix,
            self.active_count,
            timeout,
        )

        # Shutdown executor, wait for running tasks
        self._executor.shutdown(wait=True, cancel_futures=False)
        self._started = False

        self.logger.info(
            "Worker pool '%s' stopped (stats: submitted=%d, succeeded=%d, failed=%d, timeout=%d)",
            self.name_prefix,
            self._total_submitted,
            self._total_succeeded,
            self._total_failed,
            self._total_timeout,
        )

    def submit_batch(
        self,
        jobs: List[Dict[str, Any]],
        handler: Callable[[Dict[str, Any]], None],
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Submit batch of jobs and wait for completion.

        Submits all jobs to the thread pool and waits for each to complete
        or timeout. Returns categorized results for success/failure handling.

        Args:
            jobs: List of job documents to process (must have 'job_id' key)
            handler: Function to handle each job (receives job dict)
            timeout: Maximum seconds to wait for each job

        Returns:
            Dict with keys:
                - succeeded: List of job_ids that completed successfully
                - failed: List of dicts with job_id and error message
                - timeout: List of job_ids that timed out

        Raises:
            RuntimeError: If pool not started
        """
        if not self._started or not self._executor:
            raise RuntimeError(f"Worker pool '{self.name_prefix}' not started")

        if not jobs:
            return {"succeeded": [], "failed": [], "timeout": []}

        batch_id = uuid4().hex[:8]
        batch_start = time.time()
        futures: Dict[str, Future] = {}

        self.logger.debug(
            "Submitting batch %s: %d jobs, timeout=%ds",
            batch_id,
            len(jobs),
            timeout,
        )

        # Submit all jobs to thread pool
        with self._lock:
            for job in jobs:
                job_id = job.get("job_id", str(uuid4()))
                future = self._executor.submit(self._safe_handler, handler, job)
                futures[job_id] = future
                self._active_jobs[job_id] = future
                self._total_submitted += 1

        # Collect results with per-job timeout
        results: Dict[str, List] = {
            "succeeded": [],
            "failed": [],
            "timeout": [],
        }

        for job_id, future in futures.items():
            try:
                # Calculate remaining time for this job
                elapsed = time.time() - batch_start
                remaining = max(1, timeout - elapsed)

                error = future.result(timeout=remaining)
                if error is None:
                    results["succeeded"].append(job_id)
                    self._total_succeeded += 1
                else:
                    results["failed"].append({"job_id": job_id, "error": error})
                    self._total_failed += 1

            except FutureTimeout:
                results["timeout"].append(job_id)
                self._total_timeout += 1
                future.cancel()
                self.logger.warning(
                    "Job %s timed out after %ds (batch=%s)",
                    job_id,
                    timeout,
                    batch_id,
                )

            except Exception as e:
                results["failed"].append({"job_id": job_id, "error": str(e)})
                self._total_failed += 1
                self.logger.error(
                    "Job %s failed with exception (batch=%s): %s",
                    job_id,
                    batch_id,
                    e,
                )

            finally:
                with self._lock:
                    self._active_jobs.pop(job_id, None)

        batch_duration = time.time() - batch_start
        self.logger.info(
            "Batch %s completed: %d succeeded, %d failed, %d timeout (%.2fs)",
            batch_id,
            len(results["succeeded"]),
            len(results["failed"]),
            len(results["timeout"]),
            batch_duration,
        )

        return results

    def _safe_handler(
        self,
        handler: Callable[[Dict[str, Any]], None],
        job: Dict[str, Any],
    ) -> Optional[str]:
        """
        Wrap handler to catch and return exceptions.

        Args:
            handler: The actual job handler function
            job: Job document to process

        Returns:
            None on success, error message string on failure
        """
        try:
            handler(job)
            return None
        except Exception as e:
            self.logger.debug(
                "Handler exception for job %s: %s",
                job.get("job_id", "unknown"),
                e,
            )
            return str(e)
