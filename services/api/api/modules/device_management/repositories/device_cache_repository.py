# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
import json
from typing import Optional, Any
import redis
from redis.exceptions import RedisError

from ..interfaces.device_interfaces import IDeviceCacheRepository
from ....core.database import get_redis_client

logger = logging.getLogger(__name__)


class DeviceCacheRepository(IDeviceCacheRepository):
    """Redis implementation of Device Cache Repository"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None, default_ttl: int = 300):
        self.redis_client = redis_client or get_redis_client()
        self.default_ttl = default_ttl
        logger.info("DeviceCacheRepository initialized")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return None
            
            value = self.redis_client.get(key)
            
            if value:
                # Deserialize JSON
                return json.loads(value)
            
            return None
            
        except RedisError as e:
            logger.error(f"Redis error getting key {key}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            # Serialize to JSON
            serialized_value = json.dumps(value)
            
            # Set with TTL
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, serialized_value)
            
            logger.debug(f"Cached key {key} with TTL {ttl}")
            return True
            
        except RedisError as e:
            logger.error(f"Redis error setting key {key}: {str(e)}")
            return False
        except json.JSONEncodeError as e:
            logger.error(f"JSON encode error for key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            result = self.redis_client.delete(key)
            logger.debug(f"Deleted key {key}: {result}")
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis error deleting key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return False
            
            return self.redis_client.exists(key) > 0
            
        except RedisError as e:
            logger.error(f"Redis error checking key {key}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking key {key}: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        try:
            if not self.redis_client:
                logger.warning("Redis client not available")
                return 0
            
            # Use SCAN to avoid blocking on large datasets
            count = 0
            cursor = 0
            
            while True:
                cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
                
                if keys:
                    # Delete in batch
                    self.redis_client.delete(*keys)
                    count += len(keys)
                
                if cursor == 0:
                    break
            
            logger.debug(f"Cleared {count} keys matching pattern {pattern}")
            return count
            
        except RedisError as e:
            logger.error(f"Redis error clearing pattern {pattern}: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error clearing pattern {pattern}: {str(e)}")
            return 0