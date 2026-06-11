# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device API Key Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Device API Key Management Controller
Handles API key generation, validation, and management for HTTPS devices
like Raspberry Pi that don't use MQTT certificates.
"""

from flask import Blueprint, request, jsonify, g
import logging
from functools import wraps

from ..services.api_key_service import (
    generate_device_api_key,
    validate_device_api_key,
    revoke_device_api_key,
    rotate_device_api_key,
    get_device_api_key_info,
    get_api_key_stats
)
from ..core.database import get_db
from ..core.rbac import require_permission
from ..core.auth import require_api_key_or_mtls, require_auth

logger = logging.getLogger(__name__)

# Create Blueprint
device_api_key_bp = Blueprint('device_api_key', __name__, url_prefix='/api/v1/devices')

def require_api_key(f):
    """
    Decorator to require valid API key for device endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Please provide API key in X-API-Key header'
            }), 401
        
        # Remove "Bearer " prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        # Validate API key
        validation_result = validate_device_api_key(api_key)
        
        if not validation_result['valid']:
            return jsonify({
                'error': 'Invalid API key',
                'message': validation_result['reason']
            }), 401
        
        # Store device info in request context
        g.device_id = validation_result['device_id']
        g.device = validation_result['device']
        g.organization_id = validation_result['organization_id']
        g.api_key_permissions = validation_result['permissions']
        
        return f(*args, **kwargs)
    
    return decorated_function

@device_api_key_bp.route('/<device_id>/api-key', methods=['POST'])
@require_permission('device:manage')
def generate_api_key(device_id):
    """
    Generate a new API key for a device.
    
    This endpoint is used by administrators to generate API keys
    for devices that will connect via HTTPS instead of MQTT.
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response with API key details
    """
    try:
        # Validate device exists
        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        
        if not device:
            return jsonify({
                'error': 'Device not found',
                'device_id': device_id
            }), 404
        
        # Check if device already has an active API key
        existing_key = get_device_api_key_info(device_id)
        if existing_key:
            return jsonify({
                'error': 'Device already has an active API key',
                'existing_key': existing_key,
                'message': 'Use rotation endpoint to generate a new key'
            }), 409
        
        # Get organization ID
        organization_id = device.get('organization_id')
        if not organization_id:
            return jsonify({
                'error': 'Device has no organization assigned'
            }), 400
        
        # Get expiration days from request (default 365)
        request_data = request.get_json() or {}
        expires_days = request_data.get('expires_days', 365)
        
        if expires_days < 1 or expires_days > 3650:  # Max 10 years
            return jsonify({
                'error': 'Invalid expiration period',
                'message': 'expires_days must be between 1 and 3650'
            }), 400
        
        # Generate API key
        api_key_info = generate_device_api_key(device_id, organization_id, expires_days)
        
        logger.info(f"API key generated for device: {device_id}")
        
        return jsonify({
            'message': 'API key generated successfully',
            'device_id': device_id,
            'api_key': api_key_info['api_key'],
            'key_id': api_key_info['key_id'],
            'expires_at': api_key_info['expires_at'],
            'permissions': api_key_info['permissions'],
            'warning': 'Store this API key securely. It will not be shown again.'
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to generate API key for device {device_id}: {e}")
        return jsonify({
            'error': 'Failed to generate API key',
            'message': str(e)
        }), 500

@device_api_key_bp.route('/<device_id>/api-key', methods=['DELETE'])
@require_permission('device:manage')
def revoke_api_key(device_id):
    """
    Revoke API key for a device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response confirming revocation
    """
    try:
        request_data = request.get_json() or {}
        reason = request_data.get('reason', 'Revoked by administrator')
        
        success = revoke_device_api_key(device_id, reason)
        
        if success:
            logger.info(f"API key revoked for device: {device_id}")
            return jsonify({
                'message': 'API key revoked successfully',
                'device_id': device_id,
                'reason': reason
            }), 200
        else:
            return jsonify({
                'error': 'No active API key found for device',
                'device_id': device_id
            }), 404
        
    except Exception as e:
        logger.error(f"Failed to revoke API key for device {device_id}: {e}")
        return jsonify({
            'error': 'Failed to revoke API key',
            'message': str(e)
        }), 500

@device_api_key_bp.route('/<device_id>/api-key/rotate', methods=['POST'])
@require_permission('device:manage')
def rotate_api_key(device_id):
    """
    Rotate API key for a device (revoke old, generate new).
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response with new API key
    """
    try:
        # Validate device exists
        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        
        if not device:
            return jsonify({
                'error': 'Device not found',
                'device_id': device_id
            }), 404
        
        organization_id = device.get('organization_id')
        if not organization_id:
            return jsonify({
                'error': 'Device has no organization assigned'
            }), 400
        
        # Rotate API key
        new_api_key_info = rotate_device_api_key(device_id, organization_id)
        
        logger.info(f"API key rotated for device: {device_id}")
        
        return jsonify({
            'message': 'API key rotated successfully',
            'device_id': device_id,
            'api_key': new_api_key_info['api_key'],
            'key_id': new_api_key_info['key_id'],
            'expires_at': new_api_key_info['expires_at'],
            'permissions': new_api_key_info['permissions'],
            'warning': 'Store this API key securely. It will not be shown again.'
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to rotate API key for device {device_id}: {e}")
        return jsonify({
            'error': 'Failed to rotate API key',
            'message': str(e)
        }), 500

@device_api_key_bp.route('/<device_id>/api-key', methods=['GET'])
@require_permission('device:read')
def get_api_key_info(device_id):
    """
    Get API key information for a device (without the actual key).
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response with API key metadata
    """
    try:
        api_key_info = get_device_api_key_info(device_id)
        
        if not api_key_info:
            return jsonify({
                'error': 'No active API key found for device',
                'device_id': device_id
            }), 404
        
        return jsonify({
            'device_id': device_id,
            'api_key_info': api_key_info
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get API key info for device {device_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve API key information',
            'message': str(e)
        }), 500

# Device endpoints that use API key authentication

@device_api_key_bp.route('/telemetry', methods=['POST'])
@require_api_key_or_mtls
def submit_telemetry():
    """
    Submit telemetry data using API key authentication.
    
    This endpoint is used by devices like Raspberry Pi that connect
    via HTTPS instead of MQTT.
    
    Expected payload:
    {
        "timestamp": "2025-06-30T10:00:00Z",
        "data": {
            "temperature": 22.5,
            "humidity": 65.0,
            "cpu_usage": 45.2
        },
        "metadata": {
            "firmware_version": "1.0.0",
            "location": "Lab-A"
        }
    }
    
    Returns:
        JSON response confirming data submission
    """
    try:
        # Check permissions
        if 'device:telemetry:publish' not in g.api_key_permissions:
            return jsonify({
                'error': 'Insufficient permissions',
                'required': 'device:telemetry:publish'
            }), 403
        
        telemetry_data = request.get_json()
        
        if not telemetry_data:
            return jsonify({
                'error': 'No telemetry data provided'
            }), 400
        
        # Validate required fields
        if 'data' not in telemetry_data:
            return jsonify({
                'error': 'Missing telemetry data field'
            }), 400
        
        # Add device context
        telemetry_data['device_id'] = g.device_id
        telemetry_data['organization_id'] = g.organization_id
        telemetry_data['received_at'] = datetime.now()
        telemetry_data['source'] = 'https_api'
        
        # Store in database
        db = get_db()
        result = db.telemetry.insert_one(telemetry_data)
        
        # Update device last activity
        db.devices.update_one(
            {'device_id': g.device_id},
            {
                '$set': {
                    'last_telemetry': datetime.now(),
                    'last_activity': datetime.now()
                }
            }
        )
        
        logger.info(f"Telemetry received from device: {g.device_id}")
        
        return jsonify({
            'message': 'Telemetry data received successfully',
            'device_id': g.device_id,
            'telemetry_id': str(result.inserted_id),
            'timestamp': telemetry_data['received_at'].isoformat()
        }), 201
        
    except Exception as e:
        logger.error(f"Failed to process telemetry from device {g.device_id}: {e}")
        return jsonify({
            'error': 'Failed to process telemetry data',
            'message': str(e)
        }), 500

# Compatibility route to serve Server‑TLS bundle under /api/v1/devices/<id>/server-tls-bundle.zip
@device_api_key_bp.route('/<device_id>/server-tls-bundle.zip', methods=['GET'])
@require_auth
def download_server_tls_bundle_compat(device_id: str):
    from .server_tls_bundle import download_server_tls_bundle as _impl
    return _impl(device_id)

@device_api_key_bp.route('/status', methods=['POST'])
@require_api_key
def update_status():
    """
    Update device status using API key authentication.
    
    Expected payload:
    {
        "status": "online",
        "health": "healthy",
        "details": {
            "uptime": 3600,
            "memory_usage": 45.2,
            "disk_usage": 23.1
        }
    }
    
    Returns:
        JSON response confirming status update
    """
    try:
        # Check permissions
        if 'device:status:update' not in g.api_key_permissions:
            return jsonify({
                'error': 'Insufficient permissions',
                'required': 'device:status:update'
            }), 403
        
        status_data = request.get_json()
        
        if not status_data:
            return jsonify({
                'error': 'No status data provided'
            }), 400
        
        # Update device status in database
        db = get_db()
        update_fields = {
            'last_activity': datetime.now(),
            'status_updated_at': datetime.now()
        }
        
        # Add status fields if provided
        if 'status' in status_data:
            update_fields['connection_status'] = status_data['status']
        
        if 'health' in status_data:
            update_fields['health_status'] = status_data['health']
        
        if 'details' in status_data:
            update_fields['status_details'] = status_data['details']
        
        db.devices.update_one(
            {'device_id': g.device_id},
            {'$set': update_fields}
        )
        
        logger.info(f"Status updated for device: {g.device_id}")
        
        return jsonify({
            'message': 'Device status updated successfully',
            'device_id': g.device_id,
            'timestamp': update_fields['status_updated_at'].isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update status for device {g.device_id}: {e}")
        return jsonify({
            'error': 'Failed to update device status',
            'message': str(e)
        }), 500

@device_api_key_bp.route('/config', methods=['GET'])
@require_api_key
def get_device_config():
    """
    Get device configuration using API key authentication.
    
    Returns:
        JSON response with device configuration
    """
    try:
        # Check permissions
        if 'device:config:read' not in g.api_key_permissions:
            return jsonify({
                'error': 'Insufficient permissions',
                'required': 'device:config:read'
            }), 403
        
        # Get device configuration
        device_config = g.device.get('config', {})
        
        # Remove sensitive fields
        safe_config = {k: v for k, v in device_config.items() if not k.startswith('_')}
        
        return jsonify({
            'device_id': g.device_id,
            'config': safe_config,
            'last_updated': g.device.get('config_updated_at', '').isoformat() if g.device.get('config_updated_at') else None
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get config for device {g.device_id}: {e}")
        return jsonify({
            'error': 'Failed to retrieve device configuration',
            'message': str(e)
        }), 500

# Administrative endpoints

@device_api_key_bp.route('/api-keys/stats', methods=['GET'])
@require_permission('admin:read')
def get_api_key_statistics():
    """
    Get API key usage statistics.
    
    Returns:
        JSON response with API key statistics
    """
    try:
        stats = get_api_key_stats()
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Failed to get API key stats: {e}")
        return jsonify({
            'error': 'Failed to retrieve API key statistics',
            'message': str(e)
        }), 500

# Import datetime for telemetry endpoint
from datetime import datetime
