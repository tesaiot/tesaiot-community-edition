# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Telemetry Cache Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Provides Redis caching for telemetry data queries with:
- TTL-based cache expiration (5 minutes)
- Device-based cache keys
- Cache invalidation on new data
- Metrics tracking for cache hits/misses
- Graceful fallback to database on Redis failures
"""

import json
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import wraps

from ..core.database import get_redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)

# Cache configuration
TELEMETRY_CACHE_TTL = 300  # 5 minutes in seconds
CACHE_KEY_PREFIX = "telemetry"
CACHE_METRICS_KEY = "telemetry_cache_metrics"
CACHE_VERSION = "v1"  # Version for cache invalidation

class TelemetryCacheService:
    """Service for caching telemetry data in Redis."""
    
    def __init__(self):
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0,
            'cache_sets': 0,
            'cache_invalidations': 0
        }
        self._last_metrics_update = time.time()
    
    def _get_cache_key(self, device_id: str, limit: int = None) -> str:
        """Generate cache key for device telemetry."""
        if limit:
            return f"{CACHE_KEY_PREFIX}:{CACHE_VERSION}:device:{device_id}:limit:{limit}"
        return f"{CACHE_KEY_PREFIX}:{CACHE_VERSION}:device:{device_id}:all"
    
    def _get_device_cache_pattern(self, device_id: str) -> str:
        """Get pattern for all cache keys for a device."""
        return f"{CACHE_KEY_PREFIX}:{CACHE_VERSION}:device:{device_id}:*"
    
    def _update_metrics(self, metric: str, value: int = 1):
        """Update cache metrics."""
        self.metrics[metric] += value
        self.metrics['total_requests'] += 1 if metric in ['hits', 'misses'] else 0
        
        # Periodically persist metrics to Redis (every 60 seconds)
        current_time = time.time()
        if current_time - self._last_metrics_update > 60:
            self._persist_metrics()
            self._last_metrics_update = current_time
    
    def _persist_metrics(self):
        """Persist metrics to Redis."""
        try:
            redis_client = get_redis()
            if redis_client:
                redis_client.hset(
                    CACHE_METRICS_KEY,
                    mapping={
                        'hits': str(self.metrics['hits']),
                        'misses': str(self.metrics['misses']),
                        'errors': str(self.metrics['errors']),
                        'total_requests': str(self.metrics['total_requests']),
                        'cache_sets': str(self.metrics['cache_sets']),
                        'cache_invalidations': str(self.metrics['cache_invalidations']),
                        'hit_rate': str(self._calculate_hit_rate()),
                        'last_updated': datetime.now().isoformat()
                    }
                )
                redis_client.expire(CACHE_METRICS_KEY, 86400)  # 24 hours
        except Exception as e:
            logger.warning(f"Failed to persist cache metrics: {e}")
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.metrics['total_requests'] == 0:
            return 0.0
        return (self.metrics['hits'] / self.metrics['total_requests']) * 100
    
    def get_telemetry_from_cache(self, device_id: str, limit: int = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get telemetry data from cache.
        
        Args:
            device_id: Device identifier
            limit: Maximum number of records
            
        Returns:
            List of telemetry data if found in cache, None otherwise
        """
        try:
            redis_client = get_redis()
            if not redis_client:
                logger.debug("Redis client not available for cache retrieval")
                return None
            
            cache_key = self._get_cache_key(device_id, limit)
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                logger.debug(f"Cache hit for device {device_id} with limit {limit}")
                self._update_metrics('hits')
                
                # Parse cached data
                telemetry_data = json.loads(cached_data)
                return telemetry_data
            else:
                logger.debug(f"Cache miss for device {device_id} with limit {limit}")
                self._update_metrics('misses')
                return None
                
        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis error retrieving cached telemetry: {e}")
            self._update_metrics('errors')
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding cached telemetry data: {e}")
            self._update_metrics('errors')
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving cached telemetry: {e}")
            self._update_metrics('errors')
            return None
    
    def set_telemetry_cache(self, device_id: str, telemetry_data: List[Dict[str, Any]], limit: int = None) -> bool:
        """
        Cache telemetry data.
        
        Args:
            device_id: Device identifier
            telemetry_data: Telemetry data to cache
            limit: Limit used in query (for cache key)
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            redis_client = get_redis()
            if not redis_client:
                logger.debug("Redis client not available for caching")
                return False
            
            cache_key = self._get_cache_key(device_id, limit)
            
            # Serialize telemetry data
            serialized_data = json.dumps(telemetry_data, default=str)
            
            # Set with TTL
            redis_client.setex(cache_key, TELEMETRY_CACHE_TTL, serialized_data)
            
            logger.debug(f"Cached telemetry for device {device_id} with TTL {TELEMETRY_CACHE_TTL}s")
            self._update_metrics('cache_sets')
            
            return True
            
        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis error caching telemetry: {e}")
            self._update_metrics('errors')
            return False
        except Exception as e:
            logger.error(f"Unexpected error caching telemetry: {e}")
            self._update_metrics('errors')
            return False
    
    def invalidate_device_cache(self, device_id: str) -> bool:
        """
        Invalidate all cached telemetry for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            True if successfully invalidated, False otherwise
        """
        try:
            redis_client = get_redis()
            if not redis_client:
                logger.debug("Redis client not available for cache invalidation")
                return False
            
            # Get all cache keys for the device
            pattern = self._get_device_cache_pattern(device_id)
            
            # Use SCAN to find keys (more efficient than KEYS for production)
            deleted_count = 0
            for key in redis_client.scan_iter(match=pattern, count=100):
                redis_client.delete(key)
                deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Invalidated {deleted_count} cache entries for device {device_id}")
                self._update_metrics('cache_invalidations', deleted_count)
            
            return True
            
        except (RedisConnectionError, RedisError) as e:
            logger.warning(f"Redis error invalidating cache: {e}")
            self._update_metrics('errors')
            return False
        except Exception as e:
            logger.error(f"Unexpected error invalidating cache: {e}")
            self._update_metrics('errors')
            return False
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """
        Get cache performance metrics.
        
        Returns:
            Dictionary containing cache metrics
        """
        # Update with latest persisted metrics if available
        try:
            redis_client = get_redis()
            if redis_client:
                persisted_metrics = redis_client.hgetall(CACHE_METRICS_KEY)
                if persisted_metrics:
                    # Merge persisted metrics with current in-memory metrics
                    for key, value in persisted_metrics.items():
                        if key in ['hits', 'misses', 'errors', 'total_requests', 'cache_sets', 'cache_invalidations']:
                            self.metrics[key] = max(self.metrics[key], int(value))
        except Exception as e:
            logger.warning(f"Failed to retrieve persisted metrics: {e}")
        
        return {
            'hits': self.metrics['hits'],
            'misses': self.metrics['misses'],
            'errors': self.metrics['errors'],
            'total_requests': self.metrics['total_requests'],
            'hit_rate': self._calculate_hit_rate(),
            'cache_sets': self.metrics['cache_sets'],
            'cache_invalidations': self.metrics['cache_invalidations']
        }

# Global instance
telemetry_cache_service = TelemetryCacheService()

def with_telemetry_cache(func):
    """
    Decorator to add caching to telemetry query functions.
    
    The decorated function should:
    - Accept device_id as first parameter
    - Accept user as second parameter
    - Accept limit as third parameter (optional)
    - Return telemetry data list
    """
    @wraps(func)
    def wrapper(device_id: str, user: Dict[str, Any], limit: int = 100, *args, **kwargs):
        # Try to get from cache first
        cached_data = telemetry_cache_service.get_telemetry_from_cache(device_id, limit)
        if cached_data is not None:
            logger.debug(f"Returning cached telemetry for device {device_id}")
            return cached_data
        
        # Cache miss - get from database
        telemetry_data = func(device_id, user, limit, *args, **kwargs)
        
        # Cache the result if we got data
        if telemetry_data and isinstance(telemetry_data, list):
            telemetry_cache_service.set_telemetry_cache(device_id, telemetry_data, limit)
        
        return telemetry_data
    
    return wrapper

def invalidate_telemetry_cache_on_ingest(device_id: str):
    """
    Invalidate telemetry cache when new data is ingested.
    
    Args:
        device_id: Device identifier
    """
    telemetry_cache_service.invalidate_device_cache(device_id)