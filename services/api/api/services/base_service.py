# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Base Service Class
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Callable
import logging
from functools import wraps
import time
import json
import asyncio
from datetime import datetime

T = TypeVar('T')


class BaseService(ABC):
    """
    Base class for all services with common functionality.
    
    Provides:
    - Timing and performance monitoring
    - Caching with Redis
    - Error handling and logging
    - Permission validation framework
    - Database and Redis connection management
    """
    
    def __init__(self, db_session=None, redis_client=None, logger=None):
        """
        Initialize base service with optional dependencies.
        
        Args:
            db_session: Database session (MongoDB or PostgreSQL)
            redis_client: Redis client for caching
            logger: Logger instance (creates default if not provided)
        """
        self.db = db_session
        self.redis = redis_client
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._cache_prefix = f"tesa:{self.__class__.__name__.lower()}"
        
    @staticmethod
    def timing_decorator(func):
        """
        Decorator to measure function execution time.
        
        Logs execution time and errors for monitoring.
        """
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = await func(self, *args, **kwargs)
                execution_time = time.time() - start_time
                self.logger.info(
                    f"{func.__name__} executed successfully in {execution_time:.3f}s"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(
                    f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                    exc_info=True
                )
                raise
                
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time
                self.logger.info(
                    f"{func.__name__} executed successfully in {execution_time:.3f}s"
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(
                    f"{func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                    exc_info=True
                )
                raise
                
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    def _generate_cache_key(self, key_parts: list) -> str:
        """
        Generate a standardized cache key.
        
        Args:
            key_parts: List of key components
            
        Returns:
            Formatted cache key string
        """
        # Filter out None values and convert to strings
        clean_parts = [str(part) for part in key_parts if part is not None]
        return f"{self._cache_prefix}:{':'.join(clean_parts)}"
    
    async def get_cached_or_compute(
        self, 
        key: str, 
        compute_func: Callable, 
        ttl: int = 300,
        force_refresh: bool = False
    ) -> Any:
        """
        Get data from cache or compute and cache it.
        
        Args:
            key: Cache key
            compute_func: Async function to compute data if not cached
            ttl: Time to live in seconds (default: 5 minutes)
            force_refresh: Force recomputation even if cached
            
        Returns:
            Cached or computed data
        """
        cache_key = self._generate_cache_key([key])
        
        # Try to get from cache if not forcing refresh
        if self.redis and not force_refresh:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    self.logger.debug(f"Cache hit for key: {cache_key}")
                    # Deserialize JSON data
                    return json.loads(cached_data)
            except Exception as e:
                self.logger.warning(f"Cache retrieval error: {str(e)}")
        
        # Compute the data
        self.logger.debug(f"Cache miss for key: {cache_key}, computing...")
        result = await compute_func()
        
        # Cache the result
        if self.redis and result is not None:
            try:
                # Serialize to JSON for storage
                serialized_data = json.dumps(result, default=str)
                await self.redis.setex(cache_key, ttl, serialized_data)
                self.logger.debug(f"Cached result for key: {cache_key} with TTL: {ttl}s")
            except Exception as e:
                self.logger.warning(f"Cache storage error: {str(e)}")
        
        return result
    
    async def invalidate_cache(self, key_pattern: str = None):
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            key_pattern: Pattern to match cache keys (default: all service keys)
        """
        if not self.redis:
            return
            
        try:
            if key_pattern:
                pattern = self._generate_cache_key([key_pattern, '*'])
            else:
                pattern = f"{self._cache_prefix}:*"
                
            # Find all matching keys
            keys = await self.redis.keys(pattern)
            
            if keys:
                # Delete all matching keys
                await self.redis.delete(*keys)
                self.logger.info(f"Invalidated {len(keys)} cache entries matching: {pattern}")
        except Exception as e:
            self.logger.error(f"Cache invalidation error: {str(e)}")
    
    @abstractmethod
    async def validate_permissions(
        self, 
        user_role: str, 
        org_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: str = 'read'
    ) -> bool:
        """
        Validate user permissions for this service.
        
        Must be implemented by each service to define access control.
        
        Args:
            user_role: User's role (e.g., 'admin', 'user', 'platform_admin')
            org_id: Organization ID for multi-tenant access control
            resource_id: Specific resource ID if applicable
            action: Action to perform ('read', 'write', 'delete')
            
        Returns:
            True if user has permission, False otherwise
        """
        pass
    
    def sanitize_numeric_value(self, value: Any, fallback: float = 0) -> float:
        """
        Sanitize numeric values to prevent NaN/Infinity in responses.
        
        Args:
            value: Value to sanitize
            fallback: Default value if invalid
            
        Returns:
            Sanitized numeric value
        """
        if value is None:
            return fallback
            
        try:
            import math
            num_val = float(value)
            if math.isnan(num_val) or math.isinf(num_val):
                return fallback
            return num_val
        except (ValueError, TypeError):
            return fallback
    
    def sanitize_response_data(self, data: Any) -> Any:
        """
        Recursively sanitize response data to prevent errors.
        
        Args:
            data: Data structure to sanitize
            
        Returns:
            Sanitized data structure
        """
        if isinstance(data, dict):
            return {key: self.sanitize_response_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_response_data(item) for item in data]
        elif isinstance(data, (int, float)):
            return self.sanitize_numeric_value(data)
        else:
            return data
    
    async def handle_service_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Centralized error handling for services.
        
        Args:
            error: Exception that occurred
            context: Additional context for debugging
        """
        error_info = {
            'service': self.__class__.__name__,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self.logger.error(f"Service error: {json.dumps(error_info)}", exc_info=True)
        
        # You could also send to monitoring service here
        # await self.send_to_monitoring(error_info)
        
    def create_response(
        self, 
        success: bool, 
        data: Any = None, 
        error: str = None,
        status_code: int = 200
    ) -> tuple:
        """
        Create standardized service response.
        
        Args:
            success: Whether operation was successful
            data: Response data
            error: Error message if any
            status_code: HTTP status code
            
        Returns:
            Tuple of (response_dict, status_code)
        """
        response = {
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if success and data is not None:
            response['data'] = self.sanitize_response_data(data)
        elif error:
            response['error'] = error
            
        return response, status_code