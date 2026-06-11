# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Performance Utilities for Device Management Module

This module provides utility functions and decorators for performance
optimization and monitoring.
"""

import asyncio
import time
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
import hashlib
from collections import OrderedDict
import gc
import weakref
import threading
from contextlib import asynccontextmanager, contextmanager

from ..models.performance_models import PerformanceMetricType


logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class TimedCache:
    """Time-based cache with TTL support"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._hits += 1
                    return value
                else:
                    # Expired
                    del self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "ttl_seconds": self.ttl_seconds,
                "max_size": self.max_size
            }


def performance_monitor(
    metric_type: PerformanceMetricType = PerformanceMetricType.RESPONSE_TIME,
    unit: str = "ms",
    log_slow: float = None
) -> Callable[[F], F]:
    """
    Decorator to monitor function performance
    
    Args:
        metric_type: Type of metric to record
        unit: Unit of measurement
        log_slow: Log if execution time exceeds this threshold (in seconds)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log slow operations
                if log_slow and duration > log_slow:
                    logger.warning(
                        f"{func.__name__} took {duration:.2f}s "
                        f"(threshold: {log_slow}s)"
                    )
                
                # Record metric (would integrate with monitoring service)
                _record_performance_metric(
                    func.__name__,
                    metric_type,
                    duration * 1000,  # Convert to milliseconds
                    unit
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed after {duration:.2f}s: {e}"
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log slow operations
                if log_slow and duration > log_slow:
                    logger.warning(
                        f"{func.__name__} took {duration:.2f}s "
                        f"(threshold: {log_slow}s)"
                    )
                
                # Record metric
                _record_performance_metric(
                    func.__name__,
                    metric_type,
                    duration * 1000,
                    unit
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed after {duration:.2f}s: {e}"
                )
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cached(
    ttl_seconds: int = 300,
    max_size: int = 1000,
    key_func: Optional[Callable] = None
) -> Callable[[F], F]:
    """
    Decorator for caching function results
    
    Args:
        ttl_seconds: Time to live for cache entries
        max_size: Maximum number of cache entries
        key_func: Custom function to generate cache key
    """
    def decorator(func: F) -> F:
        cache = TimedCache(ttl_seconds=ttl_seconds, max_size=max_size)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            
            return result
        
        # Add cache control methods
        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.cache_stats = cache.get_stats
        
        return wrapper
    
    return decorator


def batch_processor(
    batch_size: int = 100,
    timeout_seconds: float = 1.0
) -> Callable[[F], F]:
    """
    Decorator to batch process function calls
    
    Args:
        batch_size: Maximum batch size
        timeout_seconds: Maximum time to wait for batch to fill
    """
    def decorator(func: F) -> F:
        batch_queue = asyncio.Queue(maxsize=batch_size * 2)
        result_futures: Dict[str, asyncio.Future] = {}
        processor_task = None
        
        async def process_batch(items: List[tuple]):
            """Process a batch of items"""
            try:
                # Extract arguments
                batch_args = [item[1] for item in items]
                
                # Call function with batch
                results = await func(batch_args)
                
                # Distribute results
                for (item_id, _, _), result in zip(items, results):
                    if item_id in result_futures:
                        result_futures[item_id].set_result(result)
                        del result_futures[item_id]
                        
            except Exception as e:
                # Set exception for all items in batch
                for item_id, _, _ in items:
                    if item_id in result_futures:
                        result_futures[item_id].set_exception(e)
                        del result_futures[item_id]
        
        async def batch_processor_loop():
            """Main batch processing loop"""
            batch = []
            last_process_time = time.time()
            
            while True:
                try:
                    # Collect items for batch
                    while len(batch) < batch_size:
                        try:
                            timeout = max(0.1, timeout_seconds - 
                                        (time.time() - last_process_time))
                            item = await asyncio.wait_for(
                                batch_queue.get(),
                                timeout=timeout
                            )
                            batch.append(item)
                        except asyncio.TimeoutError:
                            break
                    
                    # Process batch if we have items
                    if batch:
                        await process_batch(batch)
                        batch = []
                        last_process_time = time.time()
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Batch processor error: {e}")
                    await asyncio.sleep(0.1)
        
        @functools.wraps(func)
        async def wrapper(item):
            nonlocal processor_task
            
            # Start processor if not running
            if processor_task is None:
                processor_task = asyncio.create_task(batch_processor_loop())
            
            # Create future for result
            item_id = str(time.time())
            future = asyncio.Future()
            result_futures[item_id] = future
            
            # Add to batch queue
            await batch_queue.put((item_id, item, future))
            
            # Wait for result
            return await future
        
        return wrapper
    
    return decorator


def rate_limiter(
    max_calls: int,
    time_window: float = 1.0
) -> Callable[[F], F]:
    """
    Decorator to rate limit function calls
    
    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds
    """
    def decorator(func: F) -> F:
        calls = []
        lock = asyncio.Lock()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with lock:
                now = time.time()
                
                # Remove old calls outside time window
                calls[:] = [t for t in calls if now - t < time_window]
                
                # Check rate limit
                if len(calls) >= max_calls:
                    oldest_call = calls[0]
                    wait_time = time_window - (now - oldest_call)
                    if wait_time > 0:
                        await asyncio.sleep(wait_time)
                        # Retry after waiting
                        return await async_wrapper(*args, **kwargs)
                
                # Record call and proceed
                calls.append(now)
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove old calls outside time window
            calls[:] = [t for t in calls if now - t < time_window]
            
            # Check rate limit
            if len(calls) >= max_calls:
                oldest_call = calls[0]
                wait_time = time_window - (now - oldest_call)
                if wait_time > 0:
                    time.sleep(wait_time)
                    # Retry after waiting
                    return sync_wrapper(*args, **kwargs)
            
            # Record call and proceed
            calls.append(now)
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ObjectPool:
    """Generic object pool for resource reuse"""
    
    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 10,
        pre_create: int = 0
    ):
        self.factory = factory
        self.max_size = max_size
        self._pool: List[T] = []
        self._in_use: weakref.WeakSet = weakref.WeakSet()
        self._lock = threading.RLock()
        
        # Pre-create objects
        for _ in range(min(pre_create, max_size)):
            self._pool.append(factory())
    
    def acquire(self) -> T:
        """Acquire an object from the pool"""
        with self._lock:
            if self._pool:
                obj = self._pool.pop()
            else:
                obj = self.factory()
            
            self._in_use.add(obj)
            return obj
    
    def release(self, obj: T):
        """Release an object back to the pool"""
        with self._lock:
            if obj in self._in_use:
                self._in_use.remove(obj)
                
                if len(self._pool) < self.max_size:
                    self._pool.append(obj)
    
    def clear(self):
        """Clear the pool"""
        with self._lock:
            self._pool.clear()
            # Objects in use will be garbage collected
    
    @contextmanager
    def get(self) -> T:
        """Context manager for pool objects"""
        obj = self.acquire()
        try:
            yield obj
        finally:
            self.release(obj)


@asynccontextmanager
async def measure_performance(
    name: str,
    metric_type: PerformanceMetricType = PerformanceMetricType.RESPONSE_TIME
):
    """
    Async context manager for measuring performance
    
    Usage:
        async with measure_performance("database_query"):
            result = await db.query(...)
    """
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        _record_performance_metric(
            name,
            metric_type,
            duration * 1000,
            "ms"
        )


def optimize_batch_size(
    min_size: int = 10,
    max_size: int = 1000,
    target_time_ms: float = 100
) -> int:
    """
    Calculate optimal batch size based on performance target
    
    Args:
        min_size: Minimum batch size
        max_size: Maximum batch size
        target_time_ms: Target processing time in milliseconds
        
    Returns:
        Optimal batch size
    """
    # This would be dynamically calculated based on actual performance
    # For now, return a reasonable default
    return min(max(min_size, 100), max_size)


def memory_efficient_iterator(
    items: List[Any],
    chunk_size: int = 1000
):
    """
    Memory-efficient iterator for large lists
    
    Args:
        items: List of items to iterate
        chunk_size: Size of chunks to process
        
    Yields:
        Chunks of items
    """
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        yield chunk
        
        # Force garbage collection after processing large chunks
        if chunk_size > 10000:
            gc.collect()


def profile_memory(func: F) -> F:
    """
    Decorator to profile memory usage of a function
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        import tracemalloc
        
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]
        
        try:
            result = await func(*args, **kwargs)
            
            current, peak = tracemalloc.get_traced_memory()
            memory_used = (current - start_memory) / 1024 / 1024  # MB
            peak_memory = peak / 1024 / 1024  # MB
            
            logger.info(
                f"{func.__name__} memory usage: {memory_used:.2f} MB "
                f"(peak: {peak_memory:.2f} MB)"
            )
            
            return result
            
        finally:
            tracemalloc.stop()
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        import tracemalloc
        
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]
        
        try:
            result = func(*args, **kwargs)
            
            current, peak = tracemalloc.get_traced_memory()
            memory_used = (current - start_memory) / 1024 / 1024  # MB
            peak_memory = peak / 1024 / 1024  # MB
            
            logger.info(
                f"{func.__name__} memory usage: {memory_used:.2f} MB "
                f"(peak: {peak_memory:.2f} MB)"
            )
            
            return result
            
        finally:
            tracemalloc.stop()
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """Generate cache key for function call"""
    key_parts = [func.__module__, func.__name__]
    
    # Add arguments
    for arg in args:
        if hasattr(arg, '__dict__'):
            # For objects, use their dict representation
            key_parts.append(str(sorted(arg.__dict__.items())))
        else:
            key_parts.append(str(arg))
    
    # Add keyword arguments
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # Generate hash
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def _record_performance_metric(
    name: str,
    metric_type: PerformanceMetricType,
    value: float,
    unit: str
):
    """Record a performance metric"""
    # In a real implementation, this would send to monitoring service
    logger.debug(
        f"Performance metric: {name} - {metric_type.value}: {value:.2f} {unit}"
    )


class LazyProxy:
    """Lazy loading proxy for expensive objects"""
    
    def __init__(self, factory: Callable[[], Any]):
        self._factory = factory
        self._instance = None
        self._lock = threading.Lock()
    
    def __getattr__(self, name):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return getattr(self._instance, name)
    
    def __getitem__(self, key):
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance[key]


def create_lazy(factory: Callable[[], T]) -> T:
    """Create a lazy-loaded object"""
    return LazyProxy(factory)


class PerformanceContext:
    """Context for tracking performance across multiple operations"""
    
    def __init__(self, name: str):
        self.name = name
        self.metrics: Dict[str, List[float]] = {}
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.record("total_time", (self.end_time - self.start_time) * 1000)
    
    def record(self, metric_name: str, value: float):
        """Record a metric value"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of recorded metrics"""
        summary = {
            "name": self.name,
            "duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else None,
            "metrics": {}
        }
        
        for name, values in self.metrics.items():
            if values:
                summary["metrics"][name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "sum": sum(values)
                }
        
        return summary