# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - API Key Service
Copyright (C) 2024-2025 Thai Embedded Systems Association (TESA)

API key generation, validation, and lifecycle management.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta

from ..core.database import get_db
from .api_key_security_service import APIKeySecurityService

logger = logging.getLogger(__name__)

def generate_device_api_key(device_id, organization_id, expires_days=365):
    try:
        db = get_db()

        device_prefix = device_id.replace('-', '')[:8]
        random_part = secrets.token_hex(16)
        api_key = f"tesaiot_dev_{device_prefix}_{random_part}"

        # Simple hash for api_keys collection (legacy)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        if not key_hash:
            raise ValueError("Failed to generate key hash")

        # Salted hash for devices collection (for MQTT auth fallback)
        # This format is compatible with APIKeySecurityService.verify_api_key()
        salted_key_hash = APIKeySecurityService.hash_api_key(api_key)
        key_hint = api_key[:20] + '...'  # Show prefix for identification

        # Calculate expiration
        expires_at = datetime.now() + timedelta(days=expires_days)

        # Store API key metadata in api_keys collection
        api_key_doc = {
            'device_id': device_id,
            'organization_id': organization_id,
            'key_hash': key_hash,
            'key_prefix': api_key[:16],  # Store prefix for identification
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'last_used': None,
            'usage_count': 0,
            'status': 'active',
            'key_type': 'device_api_key',
            'permissions': [
                'device:telemetry:publish',
                'device:status:update',
                'device:config:read'
            ]
        }

        # Final validation before database insertion
        if 'key_hash' not in api_key_doc or not api_key_doc['key_hash']:
            raise ValueError("Cannot insert API key without key_hash")

        # Insert into api_keys collection
        result = db.api_keys.insert_one(api_key_doc)

        # Update device record with api_key_hash for MQTT auth fallback
        # CRITICAL: api_key_hash is required for mTLS devices to use API key as fallback
        db.devices.update_one(
            {'device_id': device_id},
            {
                '$set': {
                    'api_key_id': result.inserted_id,
                    'api_key_hash': salted_key_hash,  # Salted hash for MQTT auth
                    'api_key_hint': key_hint,  # Display hint in UI
                    'api_key_created': datetime.now(),
                    'auth_method': 'api_key',
                    'updated_at': datetime.now()
                }
            }
        )

        logger.info(f"Generated API key for device: {device_id} (hash stored in devices collection)")

        return {
            'api_key': api_key,
            'key_id': str(result.inserted_id),
            'expires_at': expires_at.isoformat(),
            'permissions': api_key_doc['permissions']
        }

    except Exception as e:
        logger.error(f"Failed to generate API key for device {device_id}: {e}")
        raise

def validate_device_api_key(api_key, device_id=None):
    """
    Validate device API key and update usage statistics.
    
    Args:
        api_key: API key to validate
        device_id: Optional device ID for additional validation
        
    Returns:
        dict: Validation result with device info if valid
    """
    try:
        if not api_key or not api_key.startswith('tesaiot_dev_'):
            return {'valid': False, 'reason': 'Invalid API key format'}
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        db = get_db()
        
        # Find API key in database
        api_key_doc = db.api_keys.find_one({
            'key_hash': key_hash,
            'key_type': 'device_api_key',
            'status': 'active'
        })
        
        if not api_key_doc:
            logger.warning(f"API key not found or inactive: {api_key[:16]}...")
            return {'valid': False, 'reason': 'API key not found or inactive'}
        
        # Check expiration
        if api_key_doc['expires_at'] < datetime.now():
            logger.warning(f"Expired API key used: {api_key[:16]}...")
            return {'valid': False, 'reason': 'API key expired'}
        
        # Validate device ID if provided
        key_device_id = api_key_doc['device_id']
        if device_id and device_id != key_device_id:
            logger.warning(f"Device ID mismatch: expected {key_device_id}, got {device_id}")
            return {'valid': False, 'reason': 'Device ID mismatch'}
        
        # Get device information
        device = db.devices.find_one({'device_id': key_device_id})
        if not device:
            logger.warning(f"Device not found for API key: {key_device_id}")
            return {'valid': False, 'reason': 'Associated device not found'}
        
        # Check device status
        if device.get('status') != 'active':
            logger.warning(f"Device not active: {key_device_id}")
            return {'valid': False, 'reason': 'Device not active'}
        
        # Update usage statistics
        db.api_keys.update_one(
            {'_id': api_key_doc['_id']},
            {
                '$set': {'last_used': datetime.now()},
                '$inc': {'usage_count': 1}
            }
        )
        
        # Update device last activity
        db.devices.update_one(
            {'device_id': key_device_id},
            {
                '$set': {
                    'last_activity': datetime.now(),
                    'connection_status': 'connected'
                }
            }
        )
        
        logger.info(f"API key validated successfully for device: {key_device_id}")
        
        return {
            'valid': True,
            'device_id': key_device_id,
            'device': device,
            'organization_id': api_key_doc['organization_id'],
            'permissions': api_key_doc['permissions'],
            'key_id': str(api_key_doc['_id'])
        }
        
    except Exception as e:
        logger.error(f"API key validation error: {e}")
        return {'valid': False, 'reason': 'Internal validation error'}

def revoke_device_api_key(device_id, reason="Manual revocation"):
    """
    Revoke API key for a device.
    
    Args:
        device_id: Device identifier
        reason: Reason for revocation
        
    Returns:
        bool: True if revoked successfully
    """
    try:
        db = get_db()
        
        # Find and revoke API key
        result = db.api_keys.update_many(
            {
                'device_id': device_id,
                'key_type': 'device_api_key',
                'status': 'active'
            },
            {
                '$set': {
                    'status': 'revoked',
                    'revoked_at': datetime.now(),
                    'revocation_reason': reason
                }
            }
        )
        
        # Update device record - remove api_key_hash and api_key_hint
        db.devices.update_one(
            {'device_id': device_id},
            {
                '$unset': {
                    'api_key_id': '',
                    'api_key_hash': '',  # Remove hash so MQTT auth fallback won't work
                    'api_key_hint': ''   # Remove hint from UI display
                },
                '$set': {
                    'api_key_revoked': datetime.now(),
                    'updated_at': datetime.now()
                }
            }
        )

        logger.info(f"Revoked {result.modified_count} API key(s) for device: {device_id}")
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Failed to revoke API key for device {device_id}: {e}")
        return False

def rotate_device_api_key(device_id, organization_id):
    """
    Rotate API key for a device (revoke old, generate new).
    
    Args:
        device_id: Device identifier
        organization_id: Organization ID
        
    Returns:
        dict: New API key information
    """
    try:
        # Revoke existing key
        revoke_device_api_key(device_id, "Key rotation")
        
        # Generate new key
        return generate_device_api_key(device_id, organization_id)
        
    except Exception as e:
        logger.error(f"Failed to rotate API key for device {device_id}: {e}")
        raise

def get_device_api_key_info(device_id):
    """
    Get API key information for a device (without the actual key).
    
    Args:
        device_id: Device identifier
        
    Returns:
        dict: API key metadata
    """
    try:
        db = get_db()
        
        api_key_doc = db.api_keys.find_one(
            {
                'device_id': device_id,
                'key_type': 'device_api_key',
                'status': 'active'
            },
            {
                'key_hash': 0  # Exclude sensitive data
            }
        )
        
        if not api_key_doc:
            return None
        
        return {
            'key_id': str(api_key_doc['_id']),
            'device_id': api_key_doc['device_id'],
            'key_prefix': api_key_doc['key_prefix'],
            'created_at': api_key_doc['created_at'].isoformat(),
            'expires_at': api_key_doc['expires_at'].isoformat(),
            'last_used': api_key_doc['last_used'].isoformat() if api_key_doc['last_used'] else None,
            'usage_count': api_key_doc['usage_count'],
            'permissions': api_key_doc['permissions']
        }
        
    except Exception as e:
        logger.error(f"Failed to get API key info for device {device_id}: {e}")
        return None

def cleanup_expired_api_keys():
    """
    Clean up expired API keys from the database.
    This should be run periodically as a maintenance task.
    
    Returns:
        int: Number of expired keys cleaned up
    """
    try:
        db = get_db()
        
        # Find expired API keys
        expired_keys = db.api_keys.find({
            'expires_at': {'$lt': datetime.now()},
            'status': 'active'
        })
        
        count = 0
        for key_doc in expired_keys:
            # Mark as expired
            db.api_keys.update_one(
                {'_id': key_doc['_id']},
                {
                    '$set': {
                        'status': 'expired',
                        'expired_at': datetime.now()
                    }
                }
            )
            
            # Update associated device
            db.devices.update_one(
                {'device_id': key_doc['device_id']},
                {
                    '$unset': {'api_key_id': ''},
                    '$set': {'api_key_expired': datetime.now()}
                }
            )
            
            count += 1
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired API keys")
        
        return count
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired API keys: {e}")
        return 0

def get_api_key_stats():
    """
    Get statistics about API key usage.
    
    Returns:
        dict: API key statistics
    """
    try:
        db = get_db()
        
        total_keys = db.api_keys.count_documents({'key_type': 'device_api_key'})
        active_keys = db.api_keys.count_documents({
            'key_type': 'device_api_key',
            'status': 'active'
        })
        expired_keys = db.api_keys.count_documents({
            'key_type': 'device_api_key',
            'status': 'expired'
        })
        revoked_keys = db.api_keys.count_documents({
            'key_type': 'device_api_key',
            'status': 'revoked'
        })
        
        # Keys used in last 24 hours
        since_24h = datetime.now() - timedelta(hours=24)
        active_24h = db.api_keys.count_documents({
            'key_type': 'device_api_key',
            'status': 'active',
            'last_used': {'$gte': since_24h}
        })
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'expired_keys': expired_keys,
            'revoked_keys': revoked_keys,
            'active_24h': active_24h,
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get API key stats: {e}")
        return {'error': 'Failed to retrieve statistics'}