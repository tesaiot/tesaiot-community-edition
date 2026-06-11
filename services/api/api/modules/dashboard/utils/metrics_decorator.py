# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Metrics Decorator
Purpose: Track performance metrics for dashboard module methods
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 2
"""

import time
import logging
import functools
from typing import Any, Callable, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


def track_dashboard_method(
    service_name: str = None,
    include_args: bool = False,
    *,
    method_name: str = None,
    module: str = None,
    operation: str = None
):
    """
    Decorator to track dashboard method performance and usage

    Args:
        service_name: Name of the service for metrics tracking
        include_args: Whether to include method arguments in logs
        method_name: Alternative name for the method (used as service_name if service_name is None)
        module: Module name for additional context (optional)
        operation: Operation type (create/read/update/delete) for additional context (optional)
    """
    # Support both calling conventions:
    # @track_dashboard_method(service_name="my_service")
    # @track_dashboard_method(method_name="my_method", module="device_management", operation="read")
    effective_service_name = service_name or method_name or "unknown"
    if module:
        effective_service_name = f"{module}.{effective_service_name}"
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            start_time = time.time()

            try:
                # Log method entry
                log_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_start'
                }

                if include_args and args:
                    # Only log non-sensitive arguments
                    safe_args = _sanitize_args(args, kwargs)
                    log_data['args'] = safe_args

                logger.info(f"Starting {effective_service_name}.{func_name}", extra=log_data)

                # Execute the method
                result = await func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Log successful completion
                completion_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_success'
                }

                logger.info(
                    f"Completed {effective_service_name}.{func_name} in {execution_time:.3f}s",
                    extra=completion_data
                )

                # Track metrics if metrics service is available
                _track_method_metrics(effective_service_name, func_name, execution_time, True)

                return result

            except Exception as e:
                # Calculate execution time for failed requests
                execution_time = time.time() - start_time

                # Log error
                error_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_error'
                }

                logger.error(
                    f"Error in {effective_service_name}.{func_name}: {str(e)}",
                    extra=error_data
                )

                # Track error metrics
                _track_method_metrics(effective_service_name, func_name, execution_time, False)

                # Re-raise the exception
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            func_name = func.__name__
            start_time = time.time()

            try:
                # Log method entry
                log_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_start'
                }

                if include_args and args:
                    # Only log non-sensitive arguments
                    safe_args = _sanitize_args(args, kwargs)
                    log_data['args'] = safe_args

                logger.info(f"Starting {effective_service_name}.{func_name}", extra=log_data)

                # Execute the method
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Log successful completion
                completion_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_success'
                }

                logger.info(
                    f"Completed {effective_service_name}.{func_name} in {execution_time:.3f}s",
                    extra=completion_data
                )

                # Track metrics if metrics service is available
                _track_method_metrics(effective_service_name, func_name, execution_time, True)

                return result

            except Exception as e:
                # Calculate execution time for failed requests
                execution_time = time.time() - start_time

                # Log error
                error_data = {
                    'service': effective_service_name,
                    'method': func_name,
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'method_error'
                }

                logger.error(
                    f"Error in {effective_service_name}.{func_name}: {str(e)}",
                    extra=error_data
                )

                # Track error metrics
                _track_method_metrics(effective_service_name, func_name, execution_time, False)
                
                # Re-raise the exception
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def _sanitize_args(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """
    Sanitize method arguments for logging (remove sensitive data)
    
    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Sanitized arguments dictionary
    """
    sanitized = {}
    
    # Sanitize keyword arguments
    for key, value in kwargs.items():
        if _is_sensitive_key(key):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, tuple)) and len(value) < 10:
            # Only include small collections
            sanitized[key] = f"<{type(value).__name__}[{len(value)}]>"
        else:
            sanitized[key] = f"<{type(value).__name__}>"
    
    # Include count of positional arguments
    if args:
        sanitized['_positional_args_count'] = len(args)
    
    return sanitized


def _is_sensitive_key(key: str) -> bool:
    """
    Check if a key contains sensitive information
    
    Args:
        key: Key name to check
        
    Returns:
        True if key is sensitive
    """
    sensitive_keys = {
        'password', 'passwd', 'secret', 'token', 'key', 'auth',
        'api_key', 'access_token', 'refresh_token', 'private_key',
        'session_id', 'cookie', 'authorization'
    }
    
    key_lower = key.lower()
    return any(sensitive in key_lower for sensitive in sensitive_keys)


def _track_method_metrics(
    service_name: str,
    method_name: str,
    execution_time: float,
    success: bool
) -> None:
    """
    Track method metrics if metrics service is available
    
    Args:
        service_name: Name of the service
        method_name: Name of the method
        execution_time: Method execution time in seconds
        success: Whether the method succeeded
    """
    try:
        # Try to import and use metrics service if available
        from ....services.modularization_metrics import ModularizationMetrics
        
        metrics_service = ModularizationMetrics()
        
        # Track method execution
        metrics_service.track_method_execution(
            service=service_name,
            method=method_name,
            execution_time=execution_time,
            success=success
        )
        
    except ImportError:
        # Metrics service not available, skip tracking
        pass
    except Exception as e:
        # Log error but don't fail the main operation
        logger.warning(f"Failed to track metrics for {service_name}.{method_name}: {e}")


def track_dashboard_operation(operation_name: str):
    """
    Decorator for tracking high-level dashboard operations
    
    Args:
        operation_name: Name of the dashboard operation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            
            try:
                logger.info(f"Starting dashboard operation: {operation_name}")
                
                result = func(*args, **kwargs)
                
                execution_time = time.time() - start_time
                logger.info(f"Completed dashboard operation: {operation_name} in {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Error in dashboard operation {operation_name}: {str(e)}")
                raise
        
        return wrapper
    
    return decorator


class DashboardMetricsCollector:
    """Utility class for collecting dashboard-specific metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = datetime.utcnow()
    
    def record_stat_computation(self, stat_type: str, execution_time: float, record_count: int):
        """Record statistics computation metrics"""
        if stat_type not in self.metrics:
            self.metrics[stat_type] = []
        
        self.metrics[stat_type].append({
            'execution_time': execution_time,
            'record_count': record_count,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def record_cache_operation(self, operation: str, hit: bool, key: str):
        """Record cache operation metrics"""
        cache_key = f"cache_{operation}"
        if cache_key not in self.metrics:
            self.metrics[cache_key] = []
        
        self.metrics[cache_key].append({
            'hit': hit,
            'key_hash': hash(key) % 10000,  # Anonymized key
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            'collection_period': {
                'start': self.start_time.isoformat(),
                'end': datetime.utcnow().isoformat()
            },
            'metrics': self.metrics,
            'total_operations': sum(len(ops) for ops in self.metrics.values())
        }