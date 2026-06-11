# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Credentials Management Controller
Handles MQTT password reset and credential management
"""

from flask import Blueprint, request, jsonify
from ..core.auth import require_auth
from ..core.database import get_db
from ..services.api_key_security_service import APIKeySecurityService
import secrets
import string
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

device_credentials_bp = Blueprint('device_credentials', __name__)

def generate_mqtt_password(length=16):
    """Generate a secure MQTT password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

@device_credentials_bp.route('/api/v1/devices/<device_id>/reset-mqtt-password', methods=['POST'])
@require_auth
def reset_mqtt_password(device_id):
    """
    Reset MQTT password for a device using username/password authentication
    """
    try:
        db = get_db()
        devices_collection = db.devices
        
        # Get current user info from JWT or session
        from flask_jwt_extended import get_jwt
        try:
            user_info = get_jwt()
        except:
            # Fallback to request context
            user_info = getattr(request, 'user_info', {'email': 'system', 'role': 'admin'})
        
        # Find the device
        device = devices_collection.find_one({"device_id": device_id})
        if not device:
            return jsonify({"error": "Device not found"}), 404
            
        # Check if user has permission for this device
        if user_info.get('role') != 'admin':
            if device.get('organization_id') != user_info.get('organization_id'):
                return jsonify({"error": "Permission denied"}), 403
        
        # Check if device uses Server-TLS authentication (which uses username/password)
        auth_mode = device.get('auth_mode', device.get('authentication', {}).get('mode'))
        if auth_mode != 'server_tls':
            return jsonify({
                "error": f"Device uses '{auth_mode}' authentication. Password reset only applies to Server-TLS devices with MQTT username/password authentication"
            }), 400
        
        # Generate new password
        new_password = generate_mqtt_password()

        # Hash the password securely; prefer SecurityUtils (argon2id), fallback to bcrypt
        try:
            import sys, os as _os
            sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), 'security'))
            from security_utils import SecurityUtils  # type: ignore
            password_hash = SecurityUtils.hash_password(new_password)
            algorithm = 'argon2id'
        except Exception:
            import bcrypt
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            algorithm = 'bcrypt'

        # Update device in database (store hash only; remove plaintext fields)
        update_result = devices_collection.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "password_hash": password_hash,
                    "password_algorithm": algorithm,
                    "credentials_updated_at": datetime.utcnow(),
                    "credentials_updated_by": user_info.get('email')
                },
                "$unset": {
                    "authentication.mqtt_password": "",
                    "mqtt_password": ""
                }
            }
        )
        
        if update_result.modified_count == 0:
            return jsonify({"error": "Failed to update device password"}), 500
        
        # Log the action
        logger.info(f"MQTT password reset for device {device_id} by {user_info.get('email')}")
        
        # Return success with new password (only shown once)
        return jsonify({
            "success": True,
            "device_id": device_id,
            "mqtt_username": device.get('authentication', {}).get('mqtt_username', device_id),
            "mqtt_password": new_password,
            "message": "MQTT password has been reset. Please save this password; it is shown only once.",
            "password_algorithm": algorithm
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting MQTT password for device {device_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@device_credentials_bp.route('/api/v1/devices/<device_id>/regenerate-api-key', methods=['POST'])
@require_auth
def regenerate_api_key(device_id):
    """
    Regenerate API key for a device.

    This endpoint generates a new API key and stores its HASH in the devices collection.
    The plaintext key is returned ONLY once to the user and is NOT stored.

    API key authentication can be used as:
    - Primary auth for server_tls devices (HTTPS/MQTT without client cert)
    - Fallback auth for mTLS/optiga_trust_mtls devices (emergency server-TLS mode)
    """
    try:
        db = get_db()
        devices_collection = db.devices

        # Get current user info from JWT or session
        from flask_jwt_extended import get_jwt
        try:
            user_info = get_jwt()
        except:
            # Fallback to request context
            user_info = getattr(request, 'user_info', {'email': 'system', 'role': 'admin'})

        # Find the device
        device = devices_collection.find_one({"device_id": device_id})
        if not device:
            return jsonify({"error": "Device not found"}), 404

        # Check if user has permission for this device
        if user_info.get('role') != 'admin':
            if device.get('organization_id') != user_info.get('organization_id'):
                return jsonify({"error": "Permission denied"}), 403

        # Allow API key generation for any device type
        # - server_tls devices: API key is primary auth
        # - mTLS/optiga_trust_mtls devices: API key is fallback for emergency access
        auth_type = device.get('auth_type', device.get('authentication', {}).get('method', 'unknown'))
        logger.info(f"Regenerating API key for device {device_id} (auth_type: {auth_type})")

        # Generate new API key using secure format
        device_prefix = device_id.replace('-', '')[:8].lower()
        random_part = secrets.token_hex(16)
        new_api_key = f"tesa_dak_{device_prefix}_{random_part}"

        # Generate salted hash for secure storage (compatible with MQTT auth fallback)
        api_key_hash = APIKeySecurityService.hash_api_key(new_api_key)
        api_key_hint = new_api_key[:20] + '...'  # Show prefix for identification

        # Update device in database - store HASH only, NOT plaintext
        # CRITICAL: api_key_hash is required for MQTT auth fallback for mTLS devices
        update_result = devices_collection.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "api_key_hash": api_key_hash,  # Salted hash for verification
                    "api_key_hint": api_key_hint,  # Display hint in UI
                    "api_key_prefix": new_api_key[:16],  # Prefix for identification
                    "api_key_regenerated_at": datetime.utcnow(),
                    "credentials_updated_at": datetime.utcnow(),
                    "credentials_updated_by": user_info.get('email'),
                    "updated_at": datetime.utcnow()
                },
                "$unset": {
                    "api_key": "",  # Remove any plaintext key (security cleanup)
                    "authentication.api_key": ""  # Remove legacy plaintext storage
                }
            }
        )

        if update_result.modified_count == 0:
            return jsonify({"error": "Failed to update device API key"}), 500

        # Log the action
        logger.info(f"API key regenerated for device {device_id} by {user_info.get('email')} (hash stored, plaintext NOT stored)")

        # Return success with new API key (shown ONCE only)
        return jsonify({
            "success": True,
            "device_id": device_id,
            "api_key": new_api_key,  # Return plaintext to user ONCE
            "api_key_prefix": api_key_hint,
            "message": "API key has been regenerated successfully. Store it securely - it will not be shown again."
        }), 200

    except Exception as e:
        logger.error(f"Error regenerating API key for device {device_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@device_credentials_bp.route('/api/v1/devices/<device_id>/credentials', methods=['GET'])
@require_auth
def get_device_credentials(device_id):
    """
    Get device credential information (without sensitive data)
    """
    try:
        db = get_db()
        devices_collection = db.devices
        
        # Get current user info from JWT or session
        from flask_jwt_extended import get_jwt
        try:
            user_info = get_jwt()
        except:
            # Fallback to request context
            user_info = getattr(request, 'user_info', {'email': 'system', 'role': 'admin'})
        
        # Find the device
        device = devices_collection.find_one({"device_id": device_id})
        if not device:
            return jsonify({"error": "Device not found"}), 404
            
        # Check if user has permission for this device
        if user_info.get('role') != 'admin':
            if device.get('organization_id') != user_info.get('organization_id'):
                return jsonify({"error": "Permission denied"}), 403
        
        # Prepare credential info
        auth_info = device.get('authentication', {})
        credentials = {
            "device_id": device_id,
            "authentication_method": auth_info.get('method'),
            "mqtt_username": auth_info.get('mqtt_username'),
            "has_api_key": bool(device.get('api_key')),
            "has_mqtt_password": bool(auth_info.get('mqtt_password')),
            "has_certificate": bool(auth_info.get('certificate')),
            "credentials_updated_at": device.get('credentials_updated_at'),
            "credentials_updated_by": device.get('credentials_updated_by')
        }
        
        return jsonify(credentials), 200
        
    except Exception as e:
        logger.error(f"Error getting credentials for device {device_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
