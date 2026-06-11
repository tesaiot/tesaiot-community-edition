# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""Retry and circuit breaker utilities."""

import functools
import time
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar('T')


class RetryPolicy(Enum):
    """Retry backoff policies."""
    LINEAR_BACKOFF = "linear"
    EXPONENTIAL_BACKOFF = "exponential"
    FIXED_DELAY = "fixed"


class CircuitBreaker:
    """Simple circuit breaker implementation."""
    
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def __call__(self, func):
        """Decorator for circuit breaker."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if circuit should be reset
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                self.failures = 0
                self.is_open = False
            
            # Check if circuit is open
            if self.is_open:
                raise Exception(f"Circuit breaker is open for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                self.failures = 0  # Reset on success
                return result
            except Exception as e:
                self.failures += 1
                self.last_failure_time = time.time()
                if self.failures >= self.failure_threshold:
                    self.is_open = True
                raise
        
        return wrapper


def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_policy: RetryPolicy = RetryPolicy.EXPONENTIAL_BACKOFF
) -> Callable:
    """Decorator for retrying failed operations."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    
                    time.sleep(current_delay)
                    
                    if backoff_policy == RetryPolicy.EXPONENTIAL_BACKOFF:
                        current_delay *= 2
                    elif backoff_policy == RetryPolicy.LINEAR_BACKOFF:
                        current_delay += delay
            
            return None
        
        return wrapper
    return decorator


def with_timeout(timeout_seconds: float = 30.0) -> Callable:
    """Decorator for timeout (simplified - would need threading/asyncio for real timeout)."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Simplified - just pass through
            # Real implementation would use threading or asyncio
            return func(*args, **kwargs)
        
        return wrapper
    return decorator