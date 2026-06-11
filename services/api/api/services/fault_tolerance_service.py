# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Fault Tolerance Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Centralized fault tolerance service providing pre-configured decorators
and patterns for production-grade resilience.
"""

import logging
import time
from functools import wraps
from typing import Callable, Any, Optional, Dict

# Import fault tolerance patterns from local audit module
try:
    # Try relative import first
    from ....audit.tolerance_methods.exception_handling import (
        with_error_handling, ErrorSeverity, ErrorCategory, error_handler
    )
    from ....audit.tolerance_methods.retry import (
        with_retry, RetryPolicy, CircuitBreaker, with_timeout,
        with_graceful_degradation
    )
    from ....audit.tolerance_methods.validation import (
        validate_email, validate_password, validate_device_id,
        sanitize_string,
        ValidationError, SecurityError
    )
except ImportError:
    # Fallback: Add audit path and import
    import sys
    import os
    audit_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'audit')
    if audit_path not in sys.path:
        sys.path.insert(0, audit_path)
    
    from api.tolerance_methods.exception_handling import (
        with_error_handling, ErrorSeverity, ErrorCategory, error_handler
    )
    from api.tolerance_methods.retry import (
        with_retry, RetryPolicy, CircuitBreaker, with_timeout, 
        with_graceful_degradation
    )
    from api.tolerance_methods.validation import (
        validate_email, validate_password, validate_device_id, 
        sanitize_string, ValidationError, SecurityError
    )

logger = logging.getLogger(__name__)

class FaultToleranceService:
    """
    Centralized service providing fault tolerance patterns for IoT platform services.
    """
    
    def __init__(self):
        """Initialize fault tolerance service with metrics tracking."""
        self.operation_metrics = {}
        self.circuit_breakers = {}
        
    # Database Operations Decorators
    @staticmethod
    def database_operation(
        max_retries: int = 3,
        timeout_seconds: Optional[float] = 30,
        circuit_breaker_threshold: int = 5,
        fallback_value: Any = None
    ) -> Callable:
        """
        Decorator for database operations with comprehensive fault tolerance.
        
        Args:
            max_retries: Maximum retry attempts
            timeout_seconds: Operation timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
            fallback_value: Value to return on complete failure
        """
        def decorator(func: Callable) -> Callable:
            # Create circuit breaker for this function
            circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=60  # 1 minute circuit breaker timeout
            )
            
            @circuit_breaker
            @with_retry(
                max_retries=max_retries,
                delay=1.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                exceptions=(
                    ConnectionError, TimeoutError, 
                    # MongoDB specific exceptions
                    Exception  # Broad exception catching with proper logging
                )
            )
            @with_timeout(timeout_seconds) if timeout_seconds else lambda f: f
            @with_error_handling(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.DATABASE,
                return_on_error=fallback_value
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    # Track success metrics
                    operation_time = time.time() - start_time
                    logger.debug(f"Database operation {func.__name__} completed in {operation_time:.2f}s")
                    return result
                except Exception as e:
                    operation_time = time.time() - start_time
                    logger.error(f"Database operation {func.__name__} failed after {operation_time:.2f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def vault_operation(
        max_retries: int = 3,
        timeout_seconds: Optional[float] = 15,
        circuit_breaker_threshold: int = 3,
        fallback_value: Any = None
    ) -> Callable:
        """
        Decorator for Vault operations with external service fault tolerance.
        
        Args:
            max_retries: Maximum retry attempts
            timeout_seconds: Operation timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
            fallback_value: Value to return on failure
        """
        def decorator(func: Callable) -> Callable:
            circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=120  # 2 minute circuit breaker timeout for external service
            )
            
            @circuit_breaker
            @with_retry(
                max_retries=max_retries,
                delay=2.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                exceptions=(
                    ConnectionError, TimeoutError,
                    # Vault specific exceptions
                    Exception  # Catch all with specific Vault error handling
                )
            )
            @with_timeout(timeout_seconds) if timeout_seconds else lambda f: f
            @with_error_handling(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.EXTERNAL_SERVICE,
                user_message="Certificate service temporarily unavailable. Please try again later.",
                return_on_error=fallback_value
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    operation_time = time.time() - start_time
                    logger.debug(f"Vault operation {func.__name__} completed in {operation_time:.2f}s")
                    return result
                except Exception as e:
                    operation_time = time.time() - start_time
                    logger.error(f"Vault operation {func.__name__} failed after {operation_time:.2f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def authentication_operation(
        max_retries: int = 2,
        timeout_seconds: Optional[float] = 10,
        circuit_breaker_threshold: int = 5
    ) -> Callable:
        """
        Decorator for authentication operations with security-focused fault tolerance.
        
        Args:
            max_retries: Maximum retry attempts (lower for security)
            timeout_seconds: Operation timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
        """
        def decorator(func: Callable) -> Callable:
            circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=300  # 5 minute circuit breaker timeout for auth
            )
            
            @circuit_breaker
            @with_retry(
                max_retries=max_retries,
                delay=1.0,
                backoff_policy=RetryPolicy.LINEAR_BACKOFF,  # Linear for auth to prevent hammering
                exceptions=(ConnectionError, TimeoutError)
            )
            @with_timeout(timeout_seconds) if timeout_seconds else lambda f: f
            @with_error_handling(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.AUTHENTICATION,
                user_message="Authentication service temporarily unavailable. Please try again.",
                return_on_error=None
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    operation_time = time.time() - start_time
                    logger.debug(f"Auth operation {func.__name__} completed in {operation_time:.2f}s")
                    return result
                except Exception as e:
                    operation_time = time.time() - start_time
                    logger.warning(f"Auth operation {func.__name__} failed after {operation_time:.2f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def external_api_operation(
        max_retries: int = 3,
        timeout_seconds: Optional[float] = 20,
        circuit_breaker_threshold: int = 4,
        fallback_value: Any = None
    ) -> Callable:
        """
        Decorator for external API calls with comprehensive fault tolerance.
        
        Args:
            max_retries: Maximum retry attempts
            timeout_seconds: Operation timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
            fallback_value: Value to return on failure
        """
        def decorator(func: Callable) -> Callable:
            circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=180  # 3 minute circuit breaker timeout
            )
            
            @circuit_breaker
            @with_retry(
                max_retries=max_retries,
                delay=2.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                jitter=True,  # Add jitter to prevent thundering herd
                exceptions=(ConnectionError, TimeoutError, Exception)
            )
            @with_timeout(timeout_seconds) if timeout_seconds else lambda f: f
            @with_graceful_degradation(fallback_value=fallback_value)
            @with_error_handling(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.EXTERNAL_SERVICE,
                user_message="External service temporarily unavailable. Using cached data if available.",
                return_on_error=fallback_value
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    operation_time = time.time() - start_time
                    logger.debug(f"External API operation {func.__name__} completed in {operation_time:.2f}s")
                    return result
                except Exception as e:
                    operation_time = time.time() - start_time
                    logger.warning(f"External API operation {func.__name__} failed after {operation_time:.2f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def critical_operation(
        max_retries: int = 5,
        timeout_seconds: Optional[float] = 60,
        circuit_breaker_threshold: int = 3
    ) -> Callable:
        """
        Decorator for critical system operations requiring highest reliability.
        
        Args:
            max_retries: Maximum retry attempts (higher for critical ops)
            timeout_seconds: Operation timeout
            circuit_breaker_threshold: Circuit breaker failure threshold
        """
        def decorator(func: Callable) -> Callable:
            circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                timeout=600  # 10 minute circuit breaker timeout for critical ops
            )
            
            @circuit_breaker
            @with_retry(
                max_retries=max_retries,
                delay=3.0,
                backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF,
                exceptions=(ConnectionError, TimeoutError, Exception)
            )
            @with_timeout(timeout_seconds) if timeout_seconds else lambda f: f
            @with_error_handling(
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.SYSTEM,
                user_message="Critical system operation failed. Support has been notified.",
                re_raise=True  # Re-raise for critical operations
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    operation_time = time.time() - start_time
                    logger.info(f"Critical operation {func.__name__} completed in {operation_time:.2f}s")
                    return result
                except Exception as e:
                    operation_time = time.time() - start_time
                    logger.critical(f"Critical operation {func.__name__} failed after {operation_time:.2f}s: {e}")
                    raise
            
            return wrapper
        return decorator
    
    # Input Validation Decorators
    @staticmethod
    def validate_input_data(validation_rules: Dict[str, Callable]) -> Callable:
        """
        Decorator for input validation with comprehensive error handling.
        
        Args:
            validation_rules: Dictionary of field_name -> validation_function
        """
        def decorator(func: Callable) -> Callable:
            @with_error_handling(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.VALIDATION,
                user_message="Invalid input data provided."
            )
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract data from arguments (assume first arg after self is data)
                if len(args) > 1:
                    data = args[1] if not isinstance(args[0], dict) else args[0]
                else:
                    data = kwargs.get('data', {})
                
                # Validate each field
                validation_errors = {}
                for field_name, validator in validation_rules.items():
                    if field_name in data:
                        try:
                            value = data[field_name]
                            # Sanitize string inputs
                            if isinstance(value, str):
                                value = sanitize_string(value)
                                data[field_name] = value
                            
                            # Run validation
                            result = validator(value)
                            if isinstance(result, tuple) and not result[0]:
                                validation_errors[field_name] = result[1]
                            elif result is False:
                                validation_errors[field_name] = f"Invalid {field_name}"
                        except ValidationError as ve:
                            validation_errors[field_name] = ve.message
                        except Exception as e:
                            validation_errors[field_name] = f"Validation error: {str(e)}"
                
                if validation_errors:
                    raise ValidationError(
                        f"Validation failed for fields: {', '.join(validation_errors.keys())}",
                        field=list(validation_errors.keys())[0],
                        code='VALIDATION_FAILED'
                    )
                
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    # Utility Methods
    @staticmethod
    def get_error_statistics() -> Dict[str, Any]:
        """Get comprehensive error statistics from the error handler."""
        return error_handler.get_error_statistics()
    
    @staticmethod
    def reset_circuit_breaker(operation_name: str) -> bool:
        """
        Manually reset a circuit breaker.
        
        Args:
            operation_name: Name of the operation to reset
            
        Returns:
            bool: True if reset successful
        """
        try:
            # This would need to be implemented based on circuit breaker storage
            logger.info(f"Circuit breaker reset requested for {operation_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker for {operation_name}: {e}")
            return False

# Create singleton instance
fault_tolerance_service = FaultToleranceService()

# Export commonly used decorators for easy import
database_operation = fault_tolerance_service.database_operation
vault_operation = fault_tolerance_service.vault_operation
authentication_operation = fault_tolerance_service.authentication_operation
external_api_operation = fault_tolerance_service.external_api_operation
critical_operation = fault_tolerance_service.critical_operation
validate_input_data = fault_tolerance_service.validate_input_data

# Pre-configured validation rules for common use cases
DEVICE_VALIDATION_RULES = {
    'device_id': validate_device_id,
    'name': lambda x: len(x.strip()) > 0 if isinstance(x, str) else False,
    'email': validate_email,
}

AUTH_VALIDATION_RULES = {
    'email': validate_email,
    'password': validate_password,
}

CERTIFICATE_VALIDATION_RULES = {
    'device_id': validate_device_id,
    'certificate_algorithm': lambda x: x in ['ecc-p256', 'ecc-p384', 'rsa-3072', 'rsa-4096'],
}

# Export validation rules
__all__ = [
    'fault_tolerance_service',
    'database_operation',
    'vault_operation', 
    'authentication_operation',
    'external_api_operation',
    'critical_operation',
    'validate_input_data',
    'DEVICE_VALIDATION_RULES',
    'AUTH_VALIDATION_RULES', 
    'CERTIFICATE_VALIDATION_RULES',
    'ValidationError',
    'SecurityError'
]