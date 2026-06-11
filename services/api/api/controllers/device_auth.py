# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Authentication Controller
Implements the authentication pattern endpoints
"""

import hmac
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from ..core.auth import require_auth
from ..services.device_auth_service import device_auth_service
from ..core.database import get_db

logger = logging.getLogger(__name__)


def _secrets_match(presented, stored) -> bool:
    """Constant-time comparison of secrets (None-safe, fail-closed).

    NOTE: device_auth_service still returns plaintext API keys; full
    hash-at-rest migration for that store is handled by the tesa_dak_*
    path in core/auth.py. At minimum all comparisons here are constant-time.
    """
    if not presented or not stored:
        return False
    return hmac.compare_digest(str(presented), str(stored))


def get_device_for_user(device_id, user):
    """Get a single device if user has access"""
    db = get_db()
    
    # Build query based on user role
    query = {'device_id': device_id}
    if user.get('role') != 'super_admin':
        query['organization_id'] = user.get('organization_id')
    
    device = db.devices.find_one(query)
    
    # Try by ObjectId if not found
    if not device and ObjectId.is_valid(device_id):
        query = {'_id': ObjectId(device_id)}
        if user.get('role') != 'super_admin':
            query['organization_id'] = user.get('organization_id')
        device = db.devices.find_one(query)
    
    return device

# Create blueprint
device_auth_bp = Blueprint('device_auth', __name__)

@device_auth_bp.route('/devices/<device_id>/telemetry/authenticated', methods=['POST'])
def authenticated_telemetry(device_id):
    """
    Pattern 1: Device telemetry with API key authentication
    No user auth required - uses device API key
    """
    try:
        # Get headers
        api_key = request.headers.get('X-Device-API-Key')
        device_id_header = request.headers.get('X-Device-ID')
        signature = request.headers.get('X-Device-Signature')
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')
        
        # Validate required headers
        if not all([api_key, device_id_header, signature, timestamp, nonce]):
            return jsonify({'error': 'Missing required authentication headers'}), 401
        
        # Verify device ID matches
        if device_id != device_id_header:
            return jsonify({'error': 'Device ID mismatch'}), 401
        
        # Get device auth info
        auth_info = device_auth_service.get_device_auth_info(device_id)
        if not auth_info:
            return jsonify({'error': 'Device not registered for API key authentication'}), 401
        
        # Verify API key matches (constant-time)
        if not _secrets_match(api_key, auth_info.get('api_key')):
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Verify signature
        payload = request.get_data(as_text=True)
        if not device_auth_service.verify_device_signature(
            device_id, api_key, signature, timestamp, nonce, payload
        ):
            return jsonify({'error': 'Invalid signature or expired timestamp'}), 401
        
        # Process telemetry
        telemetry_data = request.get_json()
        
        # Store telemetry
        from ..core.database import get_db
        db = get_db()
        telemetry_record = {
            'device_id': device_id,
            'data': telemetry_data,
            'timestamp': datetime.utcnow(),
            'source': 'authenticated_api',
            'auth_type': 'device_api_key'
        }
        
        db.telemetry.insert_one(telemetry_record)
        
        # Update device last seen and auth usage
        db.devices.update_one(
            {'device_id': device_id},
            {'$set': {'last_seen': datetime.utcnow()}}
        )
        
        db.device_auth.update_one(
            {'device_id': device_id},
            {'$set': {'last_used': datetime.utcnow()}}
        )
        
        logger.info(f"Authenticated telemetry received from device {device_id}")
        
        return jsonify({
            'success': True,
            'message': 'Telemetry received',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing authenticated telemetry: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@device_auth_bp.route('/gateways/<gateway_id>/devices', methods=['POST'])
def register_gateway_device(gateway_id):
    """
    Pattern 2: Register BLE device through gateway
    Uses gateway API key authentication
    """
    try:
        # Verify gateway API key
        gateway_api_key = request.headers.get('X-Gateway-API-Key')
        if not gateway_api_key:
            return jsonify({'error': 'Missing gateway API key'}), 401
        
        # Verify gateway exists and API key matches (constant-time)
        auth_info = device_auth_service.get_device_auth_info(gateway_id)
        if not auth_info or not _secrets_match(gateway_api_key, auth_info.get('api_key')):
            return jsonify({'error': 'Invalid gateway credentials'}), 401

        # Get registration data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No registration data provided'}), 400
        
        # Validate required fields
        ble_mac = data.get('ble_mac')
        device_name = data.get('device_name', f'BLE Device {ble_mac}')
        device_type = data.get('device_type', 'ble_sensor')
        
        if not ble_mac:
            return jsonify({'error': 'BLE MAC address required'}), 400
        
        # Register the device
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            device_auth_service.register_ble_device(
                gateway_id, ble_mac, device_name, device_type
            )
        )
        loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'device_uuid': result['device_uuid'],
                'message': 'BLE device registered successfully'
            }), 201
        else:
            return jsonify({'error': result.get('error', 'Registration failed')}), 400
            
    except Exception as e:
        logger.error(f"Error registering BLE device: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@device_auth_bp.route('/gateways/<gateway_id>/telemetry/batch', methods=['POST'])
def gateway_batch_telemetry(gateway_id):
    """
    Pattern 2: Batch telemetry submission from gateway
    """
    try:
        # Verify gateway API key
        gateway_api_key = request.headers.get('X-Gateway-API-Key')
        if not gateway_api_key:
            return jsonify({'error': 'Missing gateway API key'}), 401
        
        # Verify gateway credentials (constant-time)
        auth_info = device_auth_service.get_device_auth_info(gateway_id)
        if not auth_info or not _secrets_match(gateway_api_key, auth_info.get('api_key')):
            return jsonify({'error': 'Invalid gateway credentials'}), 401
        
        # Get batch data
        data = request.get_json()
        if not data or 'devices' not in data:
            return jsonify({'error': 'Invalid batch data format'}), 400
        
        devices_data = data.get('devices', [])
        if not devices_data:
            return jsonify({'error': 'No device data provided'}), 400
        
        # Limit batch size
        if len(devices_data) > 100:
            return jsonify({'error': 'Batch size exceeds limit (100)'}), 400
        
        # Process batch
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            device_auth_service.process_gateway_telemetry_batch(
                gateway_id, devices_data
            )
        )
        loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'processed': result['processed'],
                'total': result['total'],
                'errors': result.get('errors', [])
            }), 200
        else:
            return jsonify({'error': result.get('error', 'Batch processing failed')}), 400
            
    except Exception as e:
        logger.error(f"Error processing gateway batch: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@device_auth_bp.route('/devices/<device_uuid>/telemetry', methods=['POST'])
def uuid_authenticated_telemetry(device_uuid):
    """
    Pattern 3: Device telemetry with UUID + API key authentication
    """
    try:
        # Get headers
        device_uuid_header = request.headers.get('X-Device-UUID')
        api_key = request.headers.get('X-Device-API-Key')
        signature = request.headers.get('X-Device-Signature')
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')
        
        # Validate headers
        if not all([device_uuid_header, api_key, signature, timestamp, nonce]):
            return jsonify({'error': 'Missing required authentication headers'}), 401
        
        # Verify UUID matches
        if device_uuid != device_uuid_header:
            return jsonify({'error': 'Device UUID mismatch'}), 401
        
        # Get device by UUID
        from ..core.database import get_db
        db = get_db()
        device = db.devices.find_one({'device_id': device_uuid})
        if not device:
            # Try alternate UUID field
            device = db.devices.find_one({'uuid': device_uuid})
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Get auth info
        device_id = device.get('device_id', device.get('_id'))
        auth_info = device_auth_service.get_device_auth_info(str(device_id))
        if not auth_info or not _secrets_match(api_key, auth_info.get('api_key')):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verify signature (using UUID instead of device_id)
        payload = request.get_data(as_text=True)
        data_to_sign = f"{device_uuid}{timestamp}{nonce}{payload}"

        import hashlib
        expected_signature = hmac.new(
            api_key.encode('utf-8'),
            data_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Process telemetry
        telemetry_data = request.get_json()
        
        # Store telemetry
        telemetry_record = {
            'device_id': device_uuid,
            'data': telemetry_data,
            'timestamp': datetime.utcnow(),
            'source': 'uuid_authenticated',
            'auth_type': 'uuid_api_key'
        }
        
        db.telemetry.insert_one(telemetry_record)
        
        # Update last seen
        db.devices.update_one(
            {'device_id': device_uuid},
            {'$set': {'last_seen': datetime.utcnow()}}
        )
        
        logger.info(f"UUID authenticated telemetry received from {device_uuid}")
        
        return jsonify({
            'success': True,
            'message': 'Telemetry received',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing UUID telemetry: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@device_auth_bp.route('/proxy/ble/telemetry', methods=['POST'])
@require_auth
def mobile_proxy_telemetry():
    """
    Mobile app BLE proxy endpoint
    Requires both user authentication (OAuth) and organization API key
    """
    try:
        # Verify organization API key
        org_api_key = request.headers.get('X-Organization-API-Key')
        if not org_api_key:
            return jsonify({'error': 'Missing organization API key'}), 401
        
        # Verify org API key belongs to user's organization
        user_org = g.current_user.get('organization_id')
        # TODO: Implement org API key validation
        
        # Get proxy data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        proxy_info = data.get('proxy_info', {})
        device_data = data.get('device_data', {})
        
        if not device_data:
            return jsonify({'error': 'No device data provided'}), 400
        
        # Store telemetry with proxy information
        from ..core.database import get_db
        db = get_db()
        
        telemetry_record = {
            'device_id': device_data.get('device_id'),
            'mac_address': device_data.get('mac_address'),
            'data': device_data.get('telemetry', {}),
            'rssi': device_data.get('rssi'),
            'timestamp': datetime.utcnow(),
            'source': 'mobile_proxy',
            'proxy_info': {
                'user_id': str(g.current_user.get('_id')),
                'app_id': proxy_info.get('app_id'),
                'app_version': request.headers.get('X-Proxy-App-Version'),
                'timestamp': proxy_info.get('timestamp')
            }
        }
        
        db.telemetry.insert_one(telemetry_record)
        
        logger.info(f"Mobile proxy telemetry received for device {device_data.get('device_id')}")
        
        return jsonify({
            'success': True,
            'message': 'Proxy telemetry received',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing mobile proxy telemetry: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@device_auth_bp.route('/devices/<device_id>/auth/regenerate', methods=['POST'])
@require_auth
def regenerate_device_api_key(device_id):
    """
    Regenerate API key for a device
    Requires user authentication and device ownership
    """
    try:
        # Verify user has access to device
        device = get_device_for_user(device_id, g.current_user)
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Regenerate API key
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            device_auth_service.regenerate_device_api_key(
                device_id, g.current_user
            )
        )
        loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'api_key': result['api_key'],
                'message': 'API key regenerated successfully'
            }), 200
        else:
            return jsonify({'error': result.get('error', 'Regeneration failed')}), 400
            
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        return jsonify({'error': 'Internal server error'}), 500