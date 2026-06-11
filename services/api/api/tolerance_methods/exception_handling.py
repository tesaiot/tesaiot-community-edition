# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""Exception handling utilities for fault tolerance."""

import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"
    SECURITY = "security"
    CONFIGURATION = "configuration"


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """Decorator for retrying failed operations with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    attempt += 1
            
            return None
        
        return wrapper
    return decorator


def safe_operation(
    default: Any = None,
    log_errors: bool = True
) -> Callable:
    """Decorator for safe operations that return a default value on failure."""
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Safe operation failed in {func.__name__}: {e}")
                return default
        
        return wrapper
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    timeout: float = 60.0
) -> Callable:
    """Circuit breaker pattern implementation."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        failures = 0
        last_failure_time = None
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            nonlocal failures, last_failure_time
            
            # Check if circuit should be reset
            if last_failure_time and time.time() - last_failure_time > timeout:
                failures = 0
                last_failure_time = None
            
            # Check if circuit is open
            if failures >= failure_threshold:
                raise Exception(f"Circuit breaker open for {func.__name__}")
            
            try:
                result = func(*args, **kwargs)
                failures = 0  # Reset on success
                return result
            except Exception as e:
                failures += 1
                last_failure_time = time.time()
                raise
        
        return wrapper
    return decorator


def with_error_handling(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    user_message: str = "An error occurred",
    return_on_error: Any = None
) -> Callable:
    """Decorator for error handling with severity and category."""
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"[{severity.value.upper()}] [{category.value}] "
                    f"Error in {func.__name__}: {e}"
                )
                
                # Log additional context for high/critical errors
                if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                
                return return_on_error
        
        return wrapper
    return decorator