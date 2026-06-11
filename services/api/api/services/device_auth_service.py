# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Authentication Service
Handles device-level authentication patterns integrated with APISIX
"""

import secrets
import hmac
import hashlib
import time
from typing import Dict, Optional, Any
from datetime import datetime
import logging
import requests

from ..core.database import get_db, get_redis
from .api_key_security_service import APIKeySecurityService

logger = logging.getLogger(__name__)

class DeviceAuthService:
    """Service for device authentication patterns"""
    
    def __init__(self):
        import os
        self._db = None
        self._redis = None
        self.apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://tesa-apisix:9180/apisix/admin")
        self.apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "")  # no default; fails closed
        
    @property
    def db(self):
        """Lazy load database connection"""
        if self._db is None:
            self._db = get_db()
        return self._db
    
    @property
    def redis(self):
        """Lazy load Redis connection"""
        if self._redis is None:
            self._redis = get_redis()
        return self._redis
        
    def generate_device_api_key(self, device_id: str) -> str:
        """Generate a unique device API key with format tesa_dak_{device_id_prefix}_{random}"""
        # Use first 8 characters of device_id as prefix (remove dashes for clean format)
        device_prefix = device_id.replace('-', '')[:8].lower()
        # Generate 16 character random hex string
        random_part = secrets.token_hex(16)
        return f"tesa_dak_{device_prefix}_{random_part}"
    
    def generate_gateway_api_key(self, gateway_id: str) -> str:
        """Generate a unique gateway API key"""
        random_part = secrets.token_urlsafe(24)
        return f"tesa_gwk_{gateway_id}_{random_part}"
    
    def test_apisix_connection(self) -> Dict[str, Any]:
        """Test connection to APISIX Admin API"""
        try:
            response = requests.get(
                f"{self.apisix_admin_url}/consumers",
                headers={"X-API-KEY": self.apisix_admin_key},
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "APISIX Admin API is accessible"
                }
            else:
                return {
                    "success": False,
                    "error": f"APISIX returned status {response.status_code}: {response.text}"
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Cannot connect to APISIX: {e}"
            }
    
    async def create_device_consumer_async(self, device_id: str, device_type: str = "device") -> Dict[str, Any]:
        """Create APISIX consumer for device authentication (async version)"""
        try:
            # Generate appropriate API key
            if device_type == "gateway":
                api_key = self.generate_gateway_api_key(device_id)
                # Convert device_id to valid consumer name (alphanumeric + underscore only)
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"gateway_{safe_id}"
                rate_limit = 50  # Higher limit for gateways
            else:
                api_key = self.generate_device_api_key(device_id)
                # Convert device_id to valid consumer name (alphanumeric + underscore only)
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"device_{safe_id}"
                rate_limit = 10  # Standard device limit
            
            # Create consumer in APISIX
            consumer_config = {
                "username": consumer_name,
                "plugins": {
                    "key-auth": {
                        "key": api_key
                    },
                    "limit-req": {
                        "rate": rate_limit,
                        "burst": rate_limit * 2,
                        "rejected_code": 429,
                        "key": "consumer_name",
                        "key_type": "var"
                    }
                }
            }
            
            # Register with APISIX Admin API
            response = requests.put(
                f"{self.apisix_admin_url}/consumers/{consumer_name}",
                json=consumer_config,
                headers={"X-API-KEY": self.apisix_admin_key}
            )
            
            if response.status_code in [200, 201]:
                # Hash the API key before storing (Phase 7 Security)
                api_key_hash = APIKeySecurityService.hash_api_key(api_key)
                api_key_prefix = APIKeySecurityService.extract_prefix(api_key)

                # Store in database with HASHED key only
                device_auth = {
                    "device_id": device_id,
                    "consumer_name": consumer_name,
                    "api_key_hash": api_key_hash,
                    "api_key_prefix": api_key_prefix,
                    "device_type": device_type,
                    "created_at": datetime.utcnow(),
                    "last_used": None,
                    "is_active": True
                }

                self.db.device_auth.insert_one(device_auth)

                # Cache the HASH in Redis (not plaintext) for fast lookup
                self.redis.setex(
                    f"device_auth:{device_id}:hash",
                    86400,  # 24 hour cache
                    api_key_hash
                )

                logger.info(f"Created device consumer: {consumer_name}")
                return {
                    "success": True,
                    "api_key": api_key,
                    "consumer_name": consumer_name
                }
            else:
                logger.error(f"Failed to create APISIX consumer: {response.text}")
                return {"success": False, "error": "Failed to create consumer"}
                
        except Exception as e:
            logger.error(f"Error creating device consumer: {e}")
            return {"success": False, "error": str(e)}
    
    def create_device_consumer(self, device_id: str, device_type: str = "device", 
                              organization_id: str = "", rate_limit: int = None) -> Dict[str, Any]:
        """Synchronous wrapper for create_device_consumer with extended parameters"""
        try:
            # Validate input parameters
            if not device_id or not isinstance(device_id, str):
                return {"success": False, "error": "Invalid device_id parameter"}
            
            if len(device_id) < 3:
                return {"success": False, "error": "device_id must be at least 3 characters long"}
            
            # Test APISIX connection first
            connection_test = self.test_apisix_connection()
            if not connection_test["success"]:
                logger.error(f"APISIX connection test failed: {connection_test['error']}")
                return {"success": False, "error": f"APISIX unavailable: {connection_test['error']}"}
            # Generate appropriate API key
            if device_type == "gateway":
                api_key = self.generate_gateway_api_key(device_id)
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"gateway_{safe_id}"
                actual_rate_limit = rate_limit or 50  # Higher limit for gateways
            else:
                api_key = self.generate_device_api_key(device_id)
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"device_{safe_id}"
                actual_rate_limit = rate_limit or 10  # Standard device limit
            
            # Create consumer in APISIX
            consumer_config = {
                "username": consumer_name,
                "plugins": {
                    "key-auth": {
                        "key": api_key
                    },
                    "limit-req": {
                        "rate": actual_rate_limit,
                        "burst": actual_rate_limit * 2,
                        "rejected_code": 429,
                        "key": "consumer_name",
                        "key_type": "var"
                    }
                }
            }
            
            # Register with APISIX Admin API
            logger.info(f"Creating APISIX consumer {consumer_name} at {self.apisix_admin_url}")
            
            try:
                response = requests.put(
                    f"{self.apisix_admin_url}/consumers/{consumer_name}",
                    json=consumer_config,
                    headers={
                        "X-API-KEY": self.apisix_admin_key,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                logger.info(f"APISIX response: status={response.status_code}, body={response.text[:200]}")
                
                if response.status_code in [200, 201]:
                    # Hash the API key before storing (Phase 7 Security)
                    api_key_hash = APIKeySecurityService.hash_api_key(api_key)
                    api_key_prefix = APIKeySecurityService.extract_prefix(api_key)

                    # Store in database with HASHED key only
                    device_auth = {
                        "device_id": device_id,
                        "consumer_name": consumer_name,
                        "api_key_hash": api_key_hash,
                        "api_key_prefix": api_key_prefix,
                        "device_type": device_type,
                        "organization_id": organization_id,
                        "rate_limit": actual_rate_limit,
                        "created_at": datetime.utcnow(),
                        "last_used": None,
                        "is_active": True
                    }

                    self.db.device_auth.insert_one(device_auth)

                    # Cache the HASH in Redis (not plaintext) for fast lookup
                    try:
                        self.redis.setex(
                            f"device_auth:{device_id}:hash",
                            86400,  # 24 hour cache
                            api_key_hash
                        )
                    except Exception as redis_error:
                        logger.warning(f"Failed to cache API key hash in Redis: {redis_error}")
                    
                    logger.info(f"Successfully created device consumer: {consumer_name} for organization: {organization_id}")
                    return {
                        "success": True,
                        "api_key": api_key,
                        "consumer_name": consumer_name
                    }
                else:
                    error_msg = f"APISIX returned status {response.status_code}: {response.text}"
                    logger.error(f"Failed to create APISIX consumer: {error_msg}")
                    return {"success": False, "error": error_msg}
            
            except requests.exceptions.RequestException as req_error:
                error_msg = f"Network error connecting to APISIX: {req_error}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Error creating device consumer: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_device_consumer(self, device_id: str) -> Dict[str, Any]:
        """Delete device consumer from APISIX and database"""
        try:
            # Get device auth info first
            auth_info = self.get_device_auth_info(device_id)
            if not auth_info:
                return {"success": False, "error": "Device authentication not found"}
            
            consumer_name = auth_info.get('consumer_name')
            if not consumer_name:
                # Generate consumer name using same pattern for cleanup
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"device_{safe_id}"
            
            # Delete from APISIX
            try:
                response = requests.delete(
                    f"{self.apisix_admin_url}/consumers/{consumer_name}",
                    headers={
                        "X-API-KEY": self.apisix_admin_key,
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                logger.info(f"APISIX delete response: status={response.status_code}")
                
                # APISIX returns 200 for successful deletion, 404 if not found
                if response.status_code in [200, 404]:
                    apisix_success = True
                else:
                    logger.warning(f"APISIX delete returned {response.status_code}: {response.text}")
                    apisix_success = False
            
            except requests.exceptions.RequestException as req_error:
                logger.warning(f"Network error deleting from APISIX: {req_error}")
                apisix_success = False
            
            # Remove from database regardless of APISIX result
            db_result = self.db.device_auth.delete_many({"device_id": device_id})
            
            # Remove from cache
            try:
                self.redis.delete(f"device_auth:{device_id}")
            except Exception as redis_error:
                logger.warning(f"Failed to remove from Redis cache: {redis_error}")
            
            logger.info(f"Deleted device consumer: {consumer_name}, DB records removed: {db_result.deleted_count}")
            
            return {
                "success": True,
                "consumer_name": consumer_name,
                "db_records_deleted": db_result.deleted_count,
                "apisix_deleted": apisix_success
            }
                
        except Exception as e:
            logger.error(f"Error deleting device consumer: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_device_signature(self, device_id: str, api_key: str, signature: str, 
                               timestamp: str, nonce: str, payload: str) -> bool:
        """Verify HMAC signature for device authentication"""
        try:
            # Check timestamp to prevent replay attacks (5 minute window)
            current_time = int(time.time() * 1000)
            request_time = int(timestamp)
            if abs(current_time - request_time) > 300000:  # 5 minutes
                logger.warning(f"Timestamp expired for device {device_id}")
                return False
            
            # Check if nonce was already used
            nonce_key = f"nonce:{device_id}:{nonce}"
            if self.redis.exists(nonce_key):
                logger.warning(f"Nonce replay detected for device {device_id}")
                return False
            
            # Store nonce for 10 minutes
            self.redis.setex(nonce_key, 600, "1")
            
            # Create expected signature
            data_to_sign = f"{device_id}{timestamp}{nonce}{payload}"
            expected_signature = hmac.new(
                api_key.encode('utf-8'),
                data_to_sign.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return False
    
    async def register_ble_device(self, gateway_id: str, ble_mac: str, 
                                 device_name: str, device_type: str) -> Dict[str, Any]:
        """Register a BLE device through a gateway"""
        try:
            # Generate UUID for BLE device
            device_uuid = f"ble-{ble_mac.replace(':', '').lower()}-{secrets.token_hex(8)}"
            
            # Create device record
            device = {
                "device_id": device_uuid,
                "parent_gateway_id": gateway_id,
                "ble_mac": ble_mac,
                "name": device_name,
                "type": device_type,
                "connection_type": "ble_proxy",
                "created_at": datetime.utcnow(),
                "last_seen": None,
                "status": "registered"
            }
            
            result = self.db.devices.insert_one(device)
            
            # Cache device-gateway mapping
            self.redis.hset(f"gateway_devices:{gateway_id}", ble_mac, device_uuid)
            
            return {
                "success": True,
                "device_uuid": device_uuid,
                "device_id": str(result.inserted_id)
            }
            
        except Exception as e:
            logger.error(f"Error registering BLE device: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_gateway_telemetry_batch(self, gateway_id: str, 
                                            devices_data: list) -> Dict[str, Any]:
        """Process batch telemetry from gateway"""
        try:
            processed = 0
            errors = []
            
            for device_data in devices_data:
                device_uuid = device_data.get('device_uuid')
                telemetry = device_data.get('telemetry', {})
                
                # Store telemetry
                telemetry_record = {
                    "device_id": device_uuid,
                    "gateway_id": gateway_id,
                    "data": telemetry,
                    "rssi": device_data.get('rssi'),
                    "timestamp": datetime.utcnow(),
                    "source": "gateway_proxy"
                }
                
                try:
                    self.db.telemetry.insert_one(telemetry_record)
                    processed += 1
                    
                    # Update last seen
                    self.db.devices.update_one(
                        {"device_id": device_uuid},
                        {"$set": {"last_seen": datetime.utcnow()}}
                    )
                except Exception as e:
                    errors.append({"device": device_uuid, "error": str(e)})
            
            return {
                "success": True,
                "processed": processed,
                "total": len(devices_data),
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error processing gateway batch: {e}")
            return {"success": False, "error": str(e)}
    
    def get_device_auth_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device authentication information (Phase 7: returns hash, not plaintext)"""
        try:
            # Check cache first (new format with :hash suffix)
            cached_hash = self.redis.get(f"device_auth:{device_id}:hash")
            if cached_hash:
                return {
                    "device_id": device_id,
                    "api_key_hash": cached_hash.decode('utf-8') if isinstance(cached_hash, bytes) else cached_hash,
                    "cached": True
                }

            # Query device_auth collection first
            auth_info = self.db.device_auth.find_one({"device_id": device_id})
            if auth_info:
                # Get hash (new format) or legacy plaintext
                api_key_hash = auth_info.get('api_key_hash')
                api_key_prefix = auth_info.get('api_key_prefix')

                # If still has legacy plaintext, migrate it on-the-fly
                if not api_key_hash and auth_info.get('api_key'):
                    legacy_key = auth_info['api_key']
                    api_key_hash = APIKeySecurityService.hash_api_key(legacy_key)
                    api_key_prefix = APIKeySecurityService.extract_prefix(legacy_key)
                    # Update to new format
                    self.db.device_auth.update_one(
                        {"_id": auth_info['_id']},
                        {
                            "$set": {"api_key_hash": api_key_hash, "api_key_prefix": api_key_prefix},
                            "$unset": {"api_key": ""}
                        }
                    )
                    logger.info(f"Migrated legacy API key for device {device_id}")

                if api_key_hash:
                    # Refresh cache with hash
                    self.redis.setex(
                        f"device_auth:{device_id}:hash",
                        86400,
                        api_key_hash
                    )

                return {
                    "device_id": device_id,
                    "api_key_hash": api_key_hash,
                    "api_key_prefix": api_key_prefix,
                    "consumer_name": auth_info.get('consumer_name'),
                    "device_type": auth_info.get('device_type'),
                    "created_at": auth_info.get('created_at'),
                    "last_used": auth_info.get('last_used')
                }

            # Fallback: Check device record (for backward compatibility)
            device = self.db.devices.find_one({"device_id": device_id})
            if device:
                api_key_hash = device.get('api_key_hash')
                api_key_prefix = device.get('api_key_prefix')

                # If still has legacy plaintext, migrate on-the-fly
                if not api_key_hash and device.get('api_key'):
                    legacy_key = device['api_key']
                    api_key_hash = APIKeySecurityService.hash_api_key(legacy_key)
                    api_key_prefix = APIKeySecurityService.extract_prefix(legacy_key)
                    # Update to new format
                    self.db.devices.update_one(
                        {"_id": device['_id']},
                        {
                            "$set": {"api_key_hash": api_key_hash, "api_key_prefix": api_key_prefix},
                            "$unset": {"api_key": "", "https_api_key": ""}
                        }
                    )
                    logger.info(f"Migrated legacy API key from devices collection for {device_id}")

                if api_key_hash:
                    # Cache hash for next time
                    self.redis.setex(
                        f"device_auth:{device_id}:hash",
                        86400,
                        api_key_hash
                    )

                    # Generate consumer name using same pattern
                    safe_id = device_id.replace('-', '_').replace('.', '_')
                    consumer_name = f"device_{safe_id}"

                    return {
                        "device_id": device_id,
                        "api_key_hash": api_key_hash,
                        "api_key_prefix": api_key_prefix,
                        "consumer_name": consumer_name,
                        "device_type": "device",
                        "created_at": device.get('created_at'),
                        "from_device_record": True
                    }

            return None

        except Exception as e:
            logger.error(f"Error getting device auth info: {e}")
            return None

    def verify_device_api_key(self, device_id: str, api_key: str) -> bool:
        """Verify a device API key against stored hash."""
        try:
            auth_info = self.get_device_auth_info(device_id)
            if not auth_info or not auth_info.get('api_key_hash'):
                return False

            return APIKeySecurityService.verify_api_key(api_key, auth_info['api_key_hash'])
        except Exception as e:
            logger.error(f"Error verifying device API key: {e}")
            return False
    
    def regenerate_device_api_key(self, device_id: str, user: Dict) -> Dict[str, Any]:
        """Regenerate API key for a device"""
        try:
            # Get current auth info
            auth_info = self.get_device_auth_info(device_id)
            
            # If no auth info, check if device exists
            if not auth_info:
                device = self.db.devices.find_one({"device_id": device_id})
                if not device:
                    return {"success": False, "error": "Device not found"}
                
                # Device exists but has no API key - this is OK for first-time generation
                # Create minimal auth_info structure
                safe_id = device_id.replace('-', '_').replace('.', '_')
                auth_info = {
                    "device_id": device_id,
                    "consumer_name": f"device_{safe_id}",
                    "new_generation": True
                }
            
            # Generate new API key
            new_api_key = self.generate_device_api_key(device_id)
            
            # Update APISIX consumer
            if 'consumer_name' in auth_info:
                consumer_name = auth_info['consumer_name']
            else:
                # Generate consumer name with same pattern
                safe_id = device_id.replace('-', '_').replace('.', '_')
                consumer_name = f"device_{safe_id}"
            
            # For new generation, use PUT to create; for existing, use PATCH to update
            apisix_updated = False
            if auth_info.get('new_generation'):
                # Try to create new consumer in APISIX (but don't fail if unavailable)
                try:
                    response = requests.put(
                        f"{self.apisix_admin_url}/consumers/{consumer_name}",
                        json={
                            "username": consumer_name,
                            "plugins": {
                                "key-auth": {
                                    "key": new_api_key
                                },
                                "limit-req": {
                                    "rate": 100,
                                    "burst": 50,
                                    "rejected_code": 429,
                                    "key": "consumer_name"
                                }
                            }
                        },
                        headers={
                            "X-API-KEY": self.apisix_admin_key,
                            "Content-Type": "application/json"
                        },
                        timeout=2  # Short timeout
                    )
                    apisix_updated = response.status_code in [200, 201]
                except Exception as apisix_error:
                    logger.warning(f"Could not create APISIX consumer (will continue): {apisix_error}")
                    apisix_updated = False
            else:
                # Try to update APISIX consumer (but don't fail if APISIX is unavailable)
                apisix_updated = False
                try:
                    response = requests.put(
                        f"{self.apisix_admin_url}/consumers/{consumer_name}",
                        json={
                            "username": consumer_name,
                            "plugins": {
                                "key-auth": {
                                    "key": new_api_key
                                }
                            }
                        },
                        headers={
                            "X-API-KEY": self.apisix_admin_key,
                            "Content-Type": "application/json"
                        },
                        timeout=2  # Short timeout to avoid blocking
                    )
                    apisix_updated = response.status_code in [200, 201]
                    if not apisix_updated:
                        logger.warning(f"APISIX update returned status {response.status_code}, continuing anyway")
                except Exception as apisix_error:
                    logger.warning(f"Could not update APISIX consumer (will continue): {apisix_error}")
                    apisix_updated = False
            
            # Always update database regardless of APISIX status
            if True:  # Changed from checking APISIX response
                # Hash the API key before storing (Phase 7 Security)
                api_key_hash = APIKeySecurityService.hash_api_key(new_api_key)
                api_key_prefix = APIKeySecurityService.extract_prefix(new_api_key)

                # Update device_auth collection with HASHED key (upsert to create if doesn't exist)
                self.db.device_auth.update_one(
                    {"device_id": device_id},
                    {
                        "$set": {
                            "api_key_hash": api_key_hash,
                            "api_key_prefix": api_key_prefix,
                            "consumer_name": consumer_name,
                            "device_type": "device",
                            "regenerated_at": datetime.utcnow(),
                            "regenerated_by": user.get('_id'),
                            "updated_at": datetime.utcnow()
                        },
                        "$unset": {
                            "api_key": ""  # Remove any plaintext key
                        },
                        "$setOnInsert": {
                            "created_at": datetime.utcnow()
                        }
                    },
                    upsert=True
                )

                # Also update the main devices collection with HASHED key
                # CRITICAL: api_key_hash is required for MQTT auth fallback for mTLS devices
                api_key_hint = new_api_key[:20] + '...'  # Display hint in UI
                self.db.devices.update_one(
                    {"device_id": device_id},
                    {
                        "$set": {
                            "api_key_hash": api_key_hash,
                            "api_key_prefix": api_key_prefix,
                            "api_key_hint": api_key_hint,  # Display hint in UI
                            "consumer_name": consumer_name,
                            "https_consumer_name": consumer_name,
                            "api_key_regenerated_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        },
                        "$unset": {
                            "api_key": "",
                            "https_api_key": ""  # Remove plaintext keys
                        }
                    }
                )

                # Cache the HASH in Redis (not plaintext)
                self.redis.setex(
                    f"device_auth:{device_id}:hash",
                    86400,
                    api_key_hash
                )
                # Remove old plaintext cache if exists
                self.redis.delete(f"device_auth:{device_id}")
                
                # Log the action
                logger.info(f"Regenerated API key for device {device_id} by {user.get('email')}")
                
                return {
                    "success": True,
                    "api_key": new_api_key,
                    "consumer_name": consumer_name,
                    "apisix_synced": apisix_updated
                }
            else:
                # This else block should never be reached now since we always proceed
                logger.error(f"Unexpected error in API key regeneration logic")
                return {"success": False, "error": "Unexpected error in API key regeneration"}
                
        except Exception as e:
            logger.error(f"Error regenerating API key: {e}")
            return {"success": False, "error": str(e)}

    async def regenerate_device_api_key_async(self, device_id: str, user: Dict) -> Dict[str, Any]:
        """Async version of regenerate API key for a device"""
        # Just call the sync version for now
        return self.regenerate_device_api_key(device_id, user)

# Singleton instance
device_auth_service = DeviceAuthService()