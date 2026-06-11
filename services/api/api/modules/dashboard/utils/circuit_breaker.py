# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Circuit Breaker Decorator Wrapper
Version: v2026.01
Build: 2026-01-10

This module provides a decorator-style wrapper around the CircuitBreaker class
for backward compatibility with existing code that expects a decorator interface.
"""

import functools
import logging
from typing import Callable, TypeVar, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Type variables for generic decorator
F = TypeVar('F', bound=Callable[..., Any])


class CircuitBreakerState(Enum):
    """Circuit breaker states - alias for compatibility"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Circuit breaker decorator (no-op implementation for now).

    This is a lightweight no-op decorator that allows methods to be marked
    with circuit breaker intent without actual implementation.
    In production, this can be replaced with full CircuitBreaker logic.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type to catch

    Returns:
        Decorator function

    Usage:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        async def some_method(self):
            # method implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # No-op: just call the original function
            # In production, this would wrap with CircuitBreaker.call()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Export for compatibility
__all__ = ['circuit_breaker', 'CircuitBreakerState']
