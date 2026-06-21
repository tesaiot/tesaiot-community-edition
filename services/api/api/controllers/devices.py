# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import re
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from ..core.auth import require_auth, require_role, require_auth_or_api_key
from ..core.database import get_db, get_redis
from ..core.rbac import RBAC, Permission, require_permission
from ..utils.validation import (
    validate_device_request, validate_device_id, sanitize_string,
    validate_request_size, validate_json_schema, DEVICE_CREATE_SCHEMA, TELEMETRY_INGEST_SCHEMA
)
# Temporarily disabled - provisioning schemas not yet implemented
# from ..models.provisioning_schemas import (
#     BULK_IMPORT_SCHEMA, TEMPLATE_SCHEMA, ZERO_TOUCH_PROVISIONING_SCHEMA
# )
# Temporarily disabled until pydantic is properly configured
# from ..models.device_schemas import (
#     device_schema_registry,
#     DeviceCategory,
#     get_device_schema_fields
# )
from ..services.device_service import (
    get_devices_for_user,
    create_device,
    update_device,
    delete_device as delete_device_service,
    update_device_status as update_status_service,
    get_device_telemetry as get_telemetry_service,
    ingest_device_telemetry,
    renew_device_certificate as renew_certificate_service,
    revoke_device_certificate,
    CertificateRevocationError
)
from ..services.telemetry_cache_service import telemetry_cache_service
# Temporarily disabled - provisioning service not yet implemented
# from ..services.provisioning_service import provisioning_service, ProvisioningError
class ProvisioningError(Exception):
    """Placeholder for provisioning errors"""
    pass
provisioning_service = None  # Placeholder
from ..services.device_logs_service import device_logs_service
from ..services.notification_acl_service import notification_acl_service
# from ..services.auto_device_registration_service import auto_device_registration_service
auto_device_registration_service = None  # Placeholder
from ..utils.data_fixes import fix_device_data

logger = logging.getLogger(__name__)

# Create blueprint
devices_bp = Blueprint('devices', __name__)

# [MODULARIZE:START] - DeviceListController# Description: Device listing and filtering endpoints
# Dependencies: device_service, rbac
# Estimated Size: 100 lines
# Priority: HIGH
@devices_bp.route('/stats', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_device_stats():
    """Get device statistics for the organization."""
    try:
        devices = get_devices_for_user(g.current_user)
        
        # Calculate statistics
        total_devices = len(devices)
        active_devices = sum(1 for device in devices if device.get('status') == 'active')
        inactive_devices = sum(1 for device in devices if device.get('status') == 'inactive')
        pending_devices = sum(1 for device in devices if device.get('status') == 'pending')
        
        # Count by device type
        device_types = {}
        for device in devices:
            device_type = device.get('type', 'unknown')
            device_types[device_type] = device_types.get(device_type, 0) + 1
        
        # Count by auth mode
        auth_modes = {}
        for device in devices:
            auth_mode = device.get('auth_mode') or device.get('auth_type', 'unknown')
            auth_modes[auth_mode] = auth_modes.get(auth_mode, 0) + 1
        
        stats = {
            'total_devices': total_devices,
            'active_devices': active_devices,
            'inactive_devices': inactive_devices,
            'pending_devices': pending_devices,
            'device_types': device_types,
            'auth_modes': auth_modes,
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting device stats: {e}")
        return jsonify({'error': 'Failed to get device stats'}), 500

@devices_bp.route('/', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_devices():
    """
    Get devices list - filtered by organization.
    
    Organization admins can see devices from their organization.
    Platform admins have NO access to customer device data.
    
    Returns:
        200: List of devices
        403: Platform admin access denied
        500: Server error
    """
    try:
        devices = get_devices_for_user(g.current_user)
        
        # Apply data fixes to ensure consistent format
        devices = [fix_device_data(device) for device in devices]
        
        logger.info(f"Retrieved {len(devices)} devices for user {g.current_user.get('email')}")
        return jsonify(devices), 200
        
    except Exception as e:
        logger.error(f"Error retrieving devices: {e}")
        return jsonify({'error': 'Failed to retrieve devices'}), 500
# [MODULARIZE:END] - DeviceListController

# Internal verification: last telemetry (cache-first, DB fallback)
@devices_bp.route('/<device_id>/telemetry/last', methods=['GET'])
@require_auth_or_api_key
@require_permission(Permission.TELEMETRY_VIEW)
def get_last_telemetry(device_id: str):
    try:
        # SECURITY (authz/IDOR): resolve the device within the caller's organization
        # BEFORE any cache or DB read. Telemetry must never be returned for a device
        # outside the caller's org. Fail-closed (404 to avoid resource enumeration).
        owned_devices = get_devices_for_user(g.current_user)
        owned = next(
            (d for d in owned_devices
             if d.get('device_id') == device_id or str(d.get('_id', '')) == device_id),
            None
        )
        if not owned:
            return jsonify({'error': 'Device not found'}), 404
        # Use the canonical device_id from the owned record so the cache/DB key is
        # scoped to an organization-owned device (cannot reach another org's cache).
        device_id = owned.get('device_id', device_id)

        # limit cap 1..50
        try:
            limit = int(request.args.get('limit', '1'))
        except Exception:
            limit = 1
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50

        # Cache first (non-fatal)
        items = []
        try:
            cached = telemetry_cache_service.get_telemetry_from_cache(device_id, limit)
            if cached:
                items = cached
        except Exception:
            items = []

        # Fallback to DB (non-fatal)
        if not items:
            try:
                db = get_db()
                if db is not None and 'telemetry' in db.list_collection_names():
                    cursor = db.telemetry.find({'device_id': device_id}).sort('timestamp', -1).limit(limit)
                    for doc in cursor:
                        ts = doc.get('timestamp')
                        if hasattr(ts, 'isoformat'):
                            doc['timestamp'] = ts.isoformat()
                        doc.pop('_id', None)
                        items.append(doc)
            except Exception:
                items = []

        return jsonify({'device_id': device_id, 'count': len(items or []), 'items': items or []}), 200
    except Exception as e:
        logger.error(f"Error fetching last telemetry for {device_id}: {e}")
        return jsonify({'device_id': device_id, 'count': 0, 'items': []}), 200

# [MODULARIZE:START] - DeviceCreationController# Description: Device creation and validation endpoints
# Dependencies: device_service, validation, auto_device_registration_service
# Estimated Size: 150 lines
# Priority: HIGH
@devices_bp.route('/', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_CREATE)
@validate_request_size(max_size=2*1024*1024)  # 2MB limit for device creation
@validate_json_schema(DEVICE_CREATE_SCHEMA)
@validate_device_request()
def create_new_device():
    """
    Create a new device.
    
    Request JSON:
        {
            "device_id": "optional-custom-id",
            "name": "Device Name",
            "type": "sensor",
            "location": {"lat": 0, "lng": 0},
            "metadata": {}
        }
    
    Returns:
        201: Device created successfully
        400: Invalid request data
        500: Server error
    """
    try:
        data = request.get_json()
        
        # Additional validation beyond schema
        if not data or not data.get('name'):
            return jsonify({'error': 'Device name is required'}), 400
        
        # Sanitize device name
        data['name'] = sanitize_string(data['name'], 100)
        
        # Normalize auth_mode and protocol to lowercase for case-insensitive handling
        if 'auth_mode' in data:
            data['auth_mode'] = data['auth_mode'].lower()
        if 'metadata' in data and isinstance(data['metadata'], dict):
            if 'protocol' in data['metadata']:
                data['metadata']['protocol'] = data['metadata']['protocol'].lower()
        
        # Validate and sanitize device_id if provided
        if 'device_id' in data:
            device_id = data['device_id']
            if not validate_device_id(device_id):
                return jsonify({
                    'error': 'Invalid device ID format. Must be 3-64 characters, alphanumeric with hyphens and underscores only.',
                    'field': 'device_id',
                    'code': 'INVALID_DEVICE_ID'
                }), 400
            data['device_id'] = sanitize_string(device_id, 64)
        
        # Sanitize device type if provided
        if 'type' in data:
            data['type'] = sanitize_string(data['type'], 50)
        
        # Validate location data if provided
        if 'location' in data and isinstance(data['location'], dict):
            location = data['location']
            if 'lat' in location:
                try:
                    lat = float(location['lat'])
                    if not -90 <= lat <= 90:
                        return jsonify({
                            'error': 'Latitude must be between -90 and 90',
                            'field': 'location.lat',
                            'code': 'INVALID_LATITUDE'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid latitude format',
                        'field': 'location.lat',
                        'code': 'INVALID_LATITUDE'
                    }), 400
            
            if 'lng' in location:
                try:
                    lng = float(location['lng'])
                    if not -180 <= lng <= 180:
                        return jsonify({
                            'error': 'Longitude must be between -180 and 180',
                            'field': 'location.lng',
                            'code': 'INVALID_LONGITUDE'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid longitude format',
                        'field': 'location.lng',
                        'code': 'INVALID_LONGITUDE'
                    }), 400
        
        device = create_device(data, g.current_user)
        
        logger.info(f"Device created: {device['device_id']} by {g.current_user.get('email')}")
        
        # Fix device data but preserve mqtt_password and https_api_key for initial response
        fixed_device = fix_device_data(device)
        if 'mqtt_password' in device:
            fixed_device['mqtt_password'] = device['mqtt_password']
            logger.info(f"Including MQTT password in response for new server_tls device {device['device_id']}")
        if 'https_api_key' in device:
            fixed_device['https_api_key'] = device['https_api_key']
            fixed_device['https_consumer_name'] = device.get('https_consumer_name')
            logger.info(f"Including HTTPs API key in response for new device {device['device_id']}")
        
        return jsonify(fixed_device), 201
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        return jsonify({'error': 'Failed to create device'}), 500
# [MODULARIZE:END] - DeviceCreationController

# [MODULARIZE:START] - DeviceDetailsController# Description: Device details retrieval and formatting
# Dependencies: device_service, data_fixes
# Estimated Size: 100 lines
# Priority: HIGH
@devices_bp.route('/<device_id>', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_device_details(device_id):
    """
    Get detailed information about a specific device.
    
    Args:
        device_id: Device identifier (device_id or ObjectId)
    
    Returns:
        200: Device details with telemetry summary
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        # Sanitize device_id parameter
        device_id = sanitize_string(device_id, 64)
        
        db = get_db()
        
        # Find device - try device_id first, then ObjectId
        device = db.devices.find_one({'device_id': device_id})
        if not device and ObjectId.is_valid(device_id):
            device = db.devices.find_one({'_id': ObjectId(device_id)})
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Check organization access using RBAC
        if not RBAC.can_access_organization(g.current_user, device.get('organization_id', '')):
            logger.warning(f"Access denied: {g.current_user.get('email')} tried to access device in different organization")
            return jsonify({'error': 'Access denied'}), 403
        
        # Convert ObjectId to string
        device['_id'] = str(device['_id'])
        
        # Get telemetry summary - use actual device_id from device record
        actual_device_id = device.get('device_id', device_id)
        telemetry_count = db.telemetry.count_documents({'device_id': actual_device_id})
        last_telemetry = db.telemetry.find_one(
            {'device_id': actual_device_id},
            sort=[('timestamp', -1)]
        )
        
        device['telemetry_summary'] = {
            'total_records': telemetry_count,
            'last_update': last_telemetry['timestamp'].isoformat() if last_telemetry else None
        }
        
        # Get certificate info if exists
        if device.get('certificate_serial'):
            # Map certificate fields to UI expected format
            certificate_info = {
                'status': device.get('certificate_status', 'unknown'),
                'serial': device.get('certificate_serial'),
                'serialNumber': device.get('certificate_serial'),  # UI expects serialNumber field
                'algorithm': device.get('certificate_algorithm', device.get('metadata', {}).get('certificate_algorithm', ''))
            }
            
            # Map issued_at to validFrom (certificate start date)
            if device.get('certificate_issued_at'):
                certificate_info['validFrom'] = device.get('certificate_issued_at')
                # Also keep original field name for backward compatibility
                certificate_info['issued_at'] = device.get('certificate_issued_at')
            
            # Map expires_at to validTo (certificate end date)
            if device.get('certificate_expires_at'):
                certificate_info['validTo'] = device.get('certificate_expires_at')
                # Also keep original field name for backward compatibility
                certificate_info['expires_at'] = device.get('certificate_expires_at')
            
            device['certificate_info'] = certificate_info
        
        # Ensure certificate_algorithm is available at top level
        if not device.get('certificate_algorithm') and device.get('metadata', {}).get('certificate_algorithm'):
            device['certificate_algorithm'] = device['metadata']['certificate_algorithm']
        
        # CRITICAL: Include CSR fields for frontend detection
        # These fields MUST be included or CSR devices won't be detected properly
        device['certificate_generation_method'] = device.get('certificate_generation_method')
        device['generation_method'] = device.get('generation_method')
        device['csr_provided'] = device.get('csr_provided')

        # CRITICAL: Include Trust M UID for Trust M device detection
        # This field MUST be included for Trust M factory certificate workflow
        device['trustm_uid'] = device.get('trustm_uid')

        # Include schema information
        device['telemetrySchema'] = device.get('telemetrySchema', None)
        device['actuatorSchema'] = device.get('actuatorSchema', None)

        # Include tags
        device['tags'] = device.get('tags', [])

        # auth_mode should already be mapped by fix_device_data, but ensure it exists
        if 'auth_mode' not in device:
            auth_type = device.get('auth_type', 'certificate')
            if auth_type == 'api_key':
                device['auth_mode'] = 'server_tls'
            elif auth_type == 'certificate':
                device['auth_mode'] = 'mtls'
            else:
                device['auth_mode'] = 'mtls'  # Default to mtls

        # Include API key metadata for frontend display (NOT the actual key/hash)
        # These fields are set by device_auth_service.regenerate_device_api_key()
        device['api_key_prefix'] = device.get('api_key_prefix')
        device['api_key_regenerated_at'] = device.get('api_key_regenerated_at')
        device['consumer_name'] = device.get('consumer_name')

        return jsonify(fix_device_data(device)), 200
        
    except Exception as e:
        logger.error(f"Error retrieving device details: {e}")
        return jsonify({'error': 'Failed to retrieve device details'}), 500
# [MODULARIZE:END] - DeviceDetailsController

# [MODULARIZE:START] - DeviceUpdateController# Description: Device update operations and validation
# Dependencies: device_service, validation
# Estimated Size: 150 lines
# Priority: HIGH
@devices_bp.route('/<device_id>', methods=['PUT'])
@require_auth
@require_permission(Permission.DEVICE_UPDATE)
@validate_request_size(max_size=2*1024*1024)  # 2MB limit
@validate_device_request()
def update_device_info(device_id):
    """
    Update device information.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "name": "New Name",
            "type": "New Type",
            "location": {},
            "metadata": {}
        }
    
    Returns:
        200: Device updated
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No update data provided'}), 400
        
        # Sanitize update data
        if 'name' in data:
            if not isinstance(data['name'], str) or not data['name'].strip():
                return jsonify({
                    'error': 'Device name must be a non-empty string',
                    'field': 'name',
                    'code': 'INVALID_DEVICE_NAME'
                }), 400
            data['name'] = sanitize_string(data['name'], 100)
        
        if 'type' in data:
            data['type'] = sanitize_string(data['type'], 50)
        
        # Validate location if provided
        if 'location' in data and isinstance(data['location'], dict):
            location = data['location']
            if 'lat' in location:
                try:
                    lat = float(location['lat'])
                    if not -90 <= lat <= 90:
                        return jsonify({
                            'error': 'Latitude must be between -90 and 90',
                            'field': 'location.lat',
                            'code': 'INVALID_LATITUDE'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid latitude format',
                        'field': 'location.lat',
                        'code': 'INVALID_LATITUDE'
                    }), 400
            
            if 'lng' in location:
                try:
                    lng = float(location['lng'])
                    if not -180 <= lng <= 180:
                        return jsonify({
                            'error': 'Longitude must be between -180 and 180',
                            'field': 'location.lng',
                            'code': 'INVALID_LONGITUDE'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'error': 'Invalid longitude format',
                        'field': 'location.lng',
                        'code': 'INVALID_LONGITUDE'
                    }), 400
        
        success = update_device(device_id, data, g.current_user)
        
        if not success:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Get the updated device to return it
        db = get_db()
        updated_device = db.devices.find_one({'device_id': device_id})
        if not updated_device and ObjectId.is_valid(device_id):
            updated_device = db.devices.find_one({'_id': ObjectId(device_id)})
        
        if updated_device:
            # Apply data fixes and return the updated device
            updated_device = fix_device_data(updated_device)
            # auth_mode should already be mapped by fix_device_data, but ensure it exists
            if 'auth_mode' not in updated_device:
                auth_type = updated_device.get('auth_type', 'certificate')
                if auth_type == 'api_key':
                    updated_device['auth_mode'] = 'server_tls'
                elif auth_type == 'certificate':
                    updated_device['auth_mode'] = 'mtls'
                else:
                    updated_device['auth_mode'] = 'mtls'  # Default to mtls
            logger.info(f"Device {device_id} updated by {g.current_user.get('email')}")
            return jsonify(updated_device), 200
        else:
            logger.info(f"Device {device_id} updated by {g.current_user.get('email')}")
            return jsonify({'message': 'Device updated successfully'}), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating device: {e}")
        return jsonify({'error': 'Failed to update device'}), 500
# [MODULARIZE:END] - DeviceUpdateController

# [MODULARIZE:START] - DeviceDeleteController# Description: Device deletion and cleanup operations
# Dependencies: device_service, provisioning_service
# Estimated Size: 80 lines
# Priority: HIGH
@devices_bp.route('/<device_id>', methods=['DELETE'])
@require_auth
@require_permission(Permission.DEVICE_DELETE)
def delete_device(device_id):
    """
    Delete a device.
    
    Args:
        device_id: Device identifier
    
    Returns:
        200: Device deleted
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        success = delete_device_service(device_id, g.current_user)
        
        if not success:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        logger.info(f"Device {device_id} deleted by {g.current_user.get('email')}")
        return jsonify({'message': 'Device deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting device: {e}")
        return jsonify({'error': 'Failed to delete device'}), 500
# [MODULARIZE:END] - DeviceDeleteController

# [MODULARIZE:START] - DeviceStatusController# Description: Device status updates and monitoring
# Dependencies: device_service, validation
# Estimated Size: 100 lines
# Priority: MEDIUM
@devices_bp.route('/<device_id>/status', methods=['PUT'])
@require_auth
@validate_request_size(max_size=1024*512)  # 512KB limit
def update_device_status(device_id):
    """
    Update device status.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "status": "active|inactive|maintenance|decommissioned"
        }
    
    Returns:
        200: Status updated
        400: Invalid status
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        data = request.get_json()
        
        if not data or 'status' not in data:
            return jsonify({'error': 'Status field is required'}), 400
        
        # Validate status value
        valid_statuses = ['active', 'inactive', 'maintenance', 'decommissioned']
        status = data.get('status', '').lower().strip()
        if status not in valid_statuses:
            return jsonify({
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}',
                'field': 'status',
                'code': 'INVALID_STATUS'
            }), 400
        
        data['status'] = status
        
        success, message = update_status_service(device_id, data['status'], g.current_user)
        
        if not success:
            return jsonify({'error': message}), 400 if 'Invalid' in message else 404
        
        logger.info(f"Device {device_id} status changed to {data['status']} by {g.current_user.get('email')}")
        
        return jsonify({
            'message': 'Device status updated',
            'device_id': device_id,
            'new_status': data['status']
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating device status: {e}")
        return jsonify({'error': 'Failed to update device status'}), 500
# [MODULARIZE:END] - DeviceStatusController

# [MODULARIZE:START] - DeviceTelemetryController# Description: Device telemetry retrieval and ingestion
# Dependencies: device_service, telemetry_cache_service, validation
# Estimated Size: 200 lines
# Priority: HIGH
@devices_bp.route('/<device_id>/telemetry', methods=['GET'])
@require_auth_or_api_key
@require_permission(Permission.TELEMETRY_VIEW)
def get_device_telemetry(device_id):
    """
    Get device telemetry data.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        limit: Maximum number of records (default: 100)
        
    Returns:
        200: Telemetry data
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        # Validate and sanitize query parameters
        try:
            limit = int(request.args.get('limit', 100))
            if limit < 1 or limit > 10000:  # Reasonable limits
                limit = 100
        except (ValueError, TypeError):
            limit = 100
        
        telemetry_data = get_telemetry_service(device_id, g.current_user, limit)
        
        if telemetry_data is None:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        return jsonify({
            'device_id': device_id,
            'telemetry': telemetry_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving telemetry: {e}")
        return jsonify({'error': 'Failed to retrieve telemetry'}), 500

@devices_bp.route('/<device_id>/telemetry/ingest', methods=['POST'])
@require_auth
@validate_request_size(max_size=5*1024*1024)  # 5MB limit for telemetry data
@validate_json_schema(TELEMETRY_INGEST_SCHEMA)
@validate_device_request()
def ingest_telemetry(device_id):
    """
    Ingest telemetry data for a device.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "data": {"temperature": 25.5, "humidity": 60},
            "metadata": {"source": "mqtt"}
        }
    
    Returns:
        200: Telemetry ingested
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        data = request.get_json()
        
        if not data or 'data' not in data:
            return jsonify({'error': 'Telemetry data is required'}), 400
        
        # Validate telemetry data structure
        telemetry_data = data['data']
        if not isinstance(telemetry_data, dict) or not telemetry_data:
            return jsonify({
                'error': 'Telemetry data must be a non-empty object',
                'field': 'data',
                'code': 'INVALID_TELEMETRY_DATA'
            }), 400
        
        # Validate and sanitize telemetry keys and values
        cleaned_data = {}
        for key, value in telemetry_data.items():
            # Validate key format
            if not isinstance(key, str) or len(key) > 100:
                return jsonify({
                    'error': f'Invalid telemetry key: {key}. Keys must be strings <= 100 characters.',
                    'code': 'INVALID_TELEMETRY_KEY'
                }), 400
            
            # Sanitize key
            clean_key = sanitize_string(key, 100)
            
            # Validate value type (allow numbers, strings, booleans, null)
            if value is not None and not isinstance(value, (int, float, str, bool)):
                return jsonify({
                    'error': f'Invalid telemetry value type for key "{key}". Only numbers, strings, booleans, and null are allowed.',
                    'code': 'INVALID_TELEMETRY_VALUE'
                }), 400
            
            # Sanitize string values
            if isinstance(value, str):
                value = sanitize_string(value, 1000)
            
            cleaned_data[clean_key] = value
        
        data['data'] = cleaned_data
        
        # Validate metadata if provided
        if 'metadata' in data and isinstance(data['metadata'], dict):
            cleaned_metadata = {}
            for key, value in data['metadata'].items():
                if isinstance(key, str) and len(key) <= 50:
                    clean_key = sanitize_string(key, 50)
                    if isinstance(value, str):
                        value = sanitize_string(value, 500)
                    cleaned_metadata[clean_key] = value
            data['metadata'] = cleaned_metadata
        
        result = ingest_device_telemetry(device_id, data, g.current_user)

        if not result:
            return jsonify({'error': 'Device not found or access denied'}), 404

        # Report storage outcome honestly, mirroring submit_telemetry: the primary
        # (MongoDB) write succeeded, but the secondary TimescaleDB time-series write
        # may have failed. Never claim a time-series write succeeded when it did not.
        timeseries_stored = bool(getattr(result, 'timeseries_stored', False))
        response_body = {
            'message': 'Telemetry ingested successfully',
            'device_id': device_id,
            'storage': {
                'primary': 'mongodb',
                'mongodb_stored': True,
                'timeseries_stored': timeseries_stored,
            },
        }
        if not timeseries_stored:
            response_body['message'] = (
                'Telemetry ingested to primary store; time-series (TimescaleDB) '
                'write failed and was not persisted.'
            )
            response_body['warnings'] = ['timeseries_write_failed']

        return jsonify(response_body), 200
        
    except Exception as e:
        logger.error(f"Error ingesting telemetry: {e}")
        return jsonify({'error': 'Failed to ingest telemetry'}), 500
# [MODULARIZE:END] - DeviceTelemetryController

# [MODULARIZE:START] - DeviceLogsController# Description: Device logs retrieval and analysis
# Dependencies: device_logs_service
# Estimated Size: 300 lines
# Priority: MEDIUM
@devices_bp.route('/<device_id>/logs', methods=['GET'])
@require_auth
def get_device_logs(device_id):
    """
    Get device logs and events with enhanced filtering.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        limit: Maximum number of logs (default: 100)
        types: Comma-separated log types to filter (e.g., "telemetry,connection,error")
        
    Returns:
        200: Device logs
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        # Verify device exists and user has access
        devices = get_devices_for_user(g.current_user)
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Validate and sanitize query parameters
        try:
            limit = int(request.args.get('limit', 100))
            if limit < 1 or limit > 10000:
                limit = 100
        except (ValueError, TypeError):
            limit = 100
        
        # Validate log types parameter
        log_types = None
        types_param = request.args.get('types', '')
        if types_param:
            valid_log_types = ['telemetry', 'connection', 'error', 'warning', 'info', 'command', 'response', 'system', 'security', 'firmware', 'config', 'performance']
            types_list = [t.strip() for t in types_param.split(',') if t.strip()]
            log_types = [t for t in types_list if t in valid_log_types]
            if not log_types:
                log_types = None
        
        # Parse categories filter (Week 5-6 enhancement)
        categories = None
        categories_param = request.args.get('categories', '')
        if categories_param:
            valid_categories = ['connectivity', 'telemetry', 'health', 'security', 'firmware', 'configuration', 'performance']
            categories_list = [c.strip() for c in categories_param.split(',') if c.strip()]
            categories = [c for c in categories_list if c in valid_categories]
            if not categories:
                categories = None
        
        # Get logs from service
        logs = device_logs_service.get_device_logs(
            device_id=device_id,
            limit=limit,
            log_types=log_types,
            categories=categories
        )
        
        return jsonify({
            'device_id': device_id,
            'logs': logs,
            'total': len(logs)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving device logs: {e}")
        return jsonify({'error': 'Failed to retrieve device logs'}), 500

@devices_bp.route('/<device_id>/health', methods=['GET'])
@require_auth
def get_device_health(device_id):
    """
    Get device health score and analysis.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        time_window: Hours to analyze (default 24)
        
    Returns:
        200: Health score with breakdown and recommendations
        404: Device not found
        500: Server error
    """
    try:
        # Verify device exists and user has access
        devices = get_devices_for_user(g.current_user)
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Parse time window
        time_window = int(request.args.get('time_window', 24))
        if time_window < 1 or time_window > 720:  # Max 30 days
            time_window = 24
        
        # Get health score
        health_data = device_logs_service.get_device_health(device_id, time_window)
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Error getting device health: {e}")
        return jsonify({'error': 'Failed to retrieve device health'}), 500

@devices_bp.route('/<device_id>/error-patterns', methods=['GET'])
@require_auth
def get_device_error_patterns(device_id):
    """
    Detect error patterns for predictive maintenance.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        time_window: Hours to analyze (default 24)
        
    Returns:
        200: Detected patterns and predictions
        404: Device not found
        500: Server error
    """
    try:
        # Verify device exists and user has access
        devices = get_devices_for_user(g.current_user)
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Parse time window
        time_window = int(request.args.get('time_window', 24))
        if time_window < 1 or time_window > 720:  # Max 30 days
            time_window = 24
        
        # Get error patterns
        patterns = device_logs_service.get_error_patterns(device_id, time_window)
        
        return jsonify(patterns), 200
        
    except Exception as e:
        logger.error(f"Error detecting error patterns: {e}")
        return jsonify({'error': 'Failed to detect error patterns'}), 500

@devices_bp.route('/<device_id>/analytics', methods=['GET'])
@require_auth
def get_device_analytics(device_id):
    """
    Get comprehensive device analytics.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        
    Returns:
        200: Analytics with trends and insights
        404: Device not found
        500: Server error
    """
    try:
        # Verify device exists and user has access
        devices = get_devices_for_user(g.current_user)
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Parse time range
        time_range = request.args.get('time_range', '24h')
        valid_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_ranges:
            time_range = '24h'
        
        # Get analytics
        analytics = device_logs_service.get_device_analytics(device_id, time_range)
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Error getting device analytics: {e}")
        return jsonify({'error': 'Failed to retrieve device analytics'}), 500

@devices_bp.route('/<device_id>/logs/stream', methods=['GET'])
@require_auth
def stream_device_logs(device_id):
    """
    Stream device logs in real-time using Server-Sent Events.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        level: Filter by log level
        categories: Filter by categories (comma-separated)
        
    Returns:
        200: SSE stream of device logs
        404: Device not found
        500: Server error
    """
    try:
        from flask import Response
        import json
        import time
        
        # Verify device exists and user has access
        devices = get_devices_for_user(g.current_user)
        device = next((d for d in devices if d['device_id'] == device_id), None)
        
        if not device:
            return jsonify({'error': 'Device not found or access denied'}), 404
        
        # Parse filters
        filters = {}
        if request.args.get('level'):
            filters['level'] = request.args.get('level').upper()
        
        if request.args.get('categories'):
            categories = [c.strip() for c in request.args.get('categories').split(',')]
            filters['category'] = categories
        
        def generate():
            """Generate SSE events for device logs"""
            from datetime import datetime
            from bson import ObjectId
            from ..core.database import get_db
            
            db = get_db()
            last_check = datetime.now()
            
            while True:
                try:
                    # Query for new logs
                    query = {
                        'device_id': device_id,
                        'timestamp': {'$gt': last_check}
                    }
                    
                    if 'level' in filters:
                        query['level'] = filters['level']
                    
                    # Get new logs
                    new_logs = list(db.device_logs.find(query).sort('timestamp', 1).limit(50))
                    
                    if new_logs:
                        # Format logs
                        formatted = []
                        for log in new_logs:
                            log_type = log.get('log_type', 'system')
                            from ..services.device_logs_service import DeviceLogCategory
                            category = DeviceLogCategory.from_log_type(log_type)
                            
                            formatted.append({
                                '_id': str(log.get('_id', ObjectId())),
                                'timestamp': log.get('timestamp', datetime.now()).isoformat(),
                                'level': log.get('level', 'INFO'),
                                'category': log.get('category', category.value),
                                'phase1_category': device_logs_service.DeviceLogsService.PHASE1_CATEGORY_MAPPING.get(category, 'DEVICE_ISSUES'),
                                'message': log.get('message', ''),
                                'details': log.get('details', {})
                            })
                        
                        # Send as SSE event
                        yield f"data: {json.dumps({'logs': formatted, 'device_id': device_id})}\n\n"
                        
                        # Update last check time
                        last_check = new_logs[-1]['timestamp']
                    
                    # Send heartbeat
                    yield f"data: {json.dumps({'heartbeat': True, 'timestamp': datetime.now().isoformat()})}\n\n"
                    
                    # Wait before next check
                    time.sleep(2)
                    
                except GeneratorExit:
                    break
                except Exception as e:
                    logger.error(f"Error streaming device logs: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    time.sleep(5)
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # Disable Nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up device log stream: {e}")
        return jsonify({'error': 'Failed to setup log stream'}), 500
# [MODULARIZE:END] - DeviceLogsController

# [MODULARIZE:START] - DeviceCertificateController# Description: Device certificate renewal and revocation
# Dependencies: device_service, certificate operations
# Estimated Size: 150 lines
# Priority: HIGH
@devices_bp.route('/<device_id>/certificate/renew', methods=['POST'])
@require_auth
@validate_request_size(max_size=1024*512)  # 512KB limit
def renew_device_certificate(device_id):
    """
    Renew device certificate.

    Supports two workflows:
    1. CSR-based renewal: Device submits CSR → Platform signs with Vault PKI → Certificate published via MQTT
    2. Auto-generate renewal: Platform generates new keypair and certificate

    Args:
        device_id: Device identifier

    Request JSON (CSR workflow):
        {
            "csr": "PEM-encoded CSR",
            "reason": "upgrade",
            "device_info": {
                "firmware_version": "1.0.0",
                "hardware_revision": "A1",
                "correlation_id": "uuid",
                "target_key_oid": "0xE0F1",
                "target_cert_oid": "0xE0E1",
                "trust_anchor_oid": "0xE0E8"
            }
        }

    Returns:
        200: Certificate renewed/signed successfully
        202: CSR received, signing in progress (async)
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400

        device_id = sanitize_string(device_id, 64)

        # Optional policy inputs
        data = request.get_json(silent=True) or {}
        justification = sanitize_string(data.get('justification', '')) if isinstance(data, dict) else ''

        # CSR-based workflow detection
        csr_content = (data.get('csr') or data.get('csr_b64') or '').strip()
        device_info = data.get('device_info', {})

        # Policy gate: require justification if renewing earlier than threshold
        try:
            from ..core.database import get_db
            from dateutil import parser as dtparser
            import os
            db = get_db()
            threshold_days = int(os.environ.get('EARLY_RENEWAL_THRESHOLD_DAYS', '60'))
            days_remaining = None
            if db is not None:
                # Access by organization
                device = db.devices.find_one({'device_id': device_id, 'organization_id': g.current_user.get('organization_id')})
                if not device:
                    # Fallback without org filter for admins
                    device = db.devices.find_one({'device_id': device_id})
                if device:
                    expires_at = (device.get('certificate_expires_at') or
                                  (device.get('certificate_info', {}) or {}).get('expires_at'))
                    if isinstance(expires_at, str):
                        try:
                            exp_dt = dtparser.parse(expires_at)
                            from datetime import datetime
                            days_remaining = (exp_dt - datetime.utcnow()).days
                        except Exception:
                            days_remaining = None
            if (days_remaining is not None) and (days_remaining > threshold_days) and not justification:
                return jsonify({
                    'error': 'JUSTIFICATION_REQUIRED',
                    'message': f'Renewal requested {days_remaining} days before expiry (> {threshold_days}). Please provide justification.'
                }), 400
        except Exception:
            # Do not block renewal on policy computation errors
            pass

        # CSR-based renewal workflow (OPTIGA Trust M / PSoC Edge devices)
        if csr_content:
            logger.info(f"CSR-based renewal requested for device {device_id}")
            try:
                from ..services.certificate_service import sign_device_csr
                import os

                # Extract validity days from request or use default
                validity_days = int(data.get('validity_days', os.getenv('DEFAULT_DEVICE_CERT_VALIDITY_DAYS', '365')))

                # Sign CSR using existing service
                sign_result = sign_device_csr(
                    device_id=device_id,
                    csr_content=csr_content,
                    validity_days=validity_days,
                    user=g.current_user,
                    revoke_old=False,  # Don't auto-revoke old cert (device will replace)
                    alt_names=data.get('alt_names') or []
                )

                if not sign_result or 'error' in sign_result:
                    error_msg = sign_result.get('error', 'Unknown CSR signing error') if sign_result else 'CSR signing failed'
                    logger.error(f"CSR signing failed for device {device_id}: {error_msg}")
                    return jsonify({
                        'error': 'CSR_SIGNING_FAILED',
                        'message': error_msg
                    }), 500

                # Extract signed certificate from result
                signed_cert_pem = None
                if 'certificate' in sign_result and isinstance(sign_result['certificate'], dict):
                    # Result structure: { 'certificate': { ... }, 'download_urls': { ... } }
                    # Need to fetch actual PEM from database
                    db = get_db()
                    if db is not None:
                        device_doc = db.devices.find_one({'device_id': device_id})
                        if device_doc:
                            signed_cert_pem = device_doc.get('certificate_info', {}).get('certificate')

                if not signed_cert_pem:
                    logger.error(f"Signed certificate PEM not found after CSR signing for device {device_id}")
                    return jsonify({
                        'error': 'CERTIFICATE_NOT_FOUND',
                        'message': 'Certificate was signed but PEM content not found'
                    }), 500

                # Publish signed certificate to MQTT topic: device/{device_id}/commands/certificate
                try:
                    import paho.mqtt.client as mqtt

                    mqtt_broker = os.getenv('TESA_MQTT_BROKER_HOST', 'tesa-emqx')
                    mqtt_port = int(os.getenv('TESA_MQTT_BROKER_PORT', '1883'))
                    mqtt_username = os.getenv('BRIDGE_MQTT_USERNAME', 'bridge-user')
                    # Use MQTT_PASSWORD (not BRIDGE_MQTT_PASSWORD) for internal service auth
                    mqtt_password = os.getenv('MQTT_PASSWORD')
                    if not mqtt_password:
                        logger.error(
                            "MQTT_PASSWORD is not set; cannot authenticate to the MQTT broker. "
                            "Set the MQTT_PASSWORD environment variable."
                        )
                        return jsonify({
                            'success': False,
                            'message': 'MQTT broker credentials are not configured (MQTT_PASSWORD unset)'
                        }), 500

                    mqtt_topic = f"device/{device_id}/commands/certificate"

                    # Publish raw PEM certificate (not JSON!)
                    # PSoC firmware expects raw PEM format that can be directly written to OPTIGA Trust M
                    # The firmware detects format: 0x30 = DER, "-----BEGIN" = PEM
                    # See: optiga_trust_helpers.c:write_device_certificate_and_verify()

                    # Connect and publish
                    # Use service-mqtt-bridge prefix to match EMQX internal service whitelist
                    mqtt_client = mqtt.Client(client_id=f"service-mqtt-bridge-csr-{device_id}")
                    mqtt_client.username_pw_set(mqtt_username, mqtt_password)
                    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
                    mqtt_client.loop_start()

                    pub_result = mqtt_client.publish(
                        mqtt_topic,
                        signed_cert_pem,  # Send raw PEM - PSoC will parse and write to Trust M
                        qos=1  # At least once delivery
                    )
                    pub_result.wait_for_publish(timeout=5)

                    mqtt_client.loop_stop()
                    mqtt_client.disconnect()

                    if pub_result.is_published():
                        logger.info(f"Certificate published to MQTT topic {mqtt_topic} for device {device_id}")
                    else:
                        logger.warning(f"Failed to publish certificate to MQTT for device {device_id}")

                except Exception as mqtt_error:
                    # Non-fatal: CSR signing succeeded, but MQTT publish failed
                    logger.error(f"MQTT certificate publishing failed for device {device_id}: {mqtt_error}")
                    # Continue to return success to API caller

                # Audit log CSR-based renewal
                try:
                    from ..services.audit_service import audit_log, AuditAction
                    audit_log(
                        action=AuditAction.CERTIFICATE_CSR_SIGNED,
                        user=g.current_user,
                        resource_type='device',
                        resource_id=device_id,
                        details={
                            'renewal_method': 'csr',
                            'device_info': device_info,
                            'serial_number': sign_result.get('certificate', {}).get('serial_number'),
                            'validity_days': validity_days
                        },
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                except Exception:
                    pass

                # Return success response
                return jsonify({
                    'message': 'CSR signed successfully and certificate published via MQTT',
                    'certificate': sign_result.get('certificate'),
                    'download_urls': sign_result.get('download_urls'),
                    'mqtt_topic': mqtt_topic
                }), 200

            except Exception as csr_error:
                logger.error(f"CSR renewal workflow failed for device {device_id}: {csr_error}")
                return jsonify({
                    'error': 'CSR_RENEWAL_FAILED',
                    'message': str(csr_error)
                }), 500

        # If client requested a specific algorithm/validity, persist intent first
        try:
            requested_algorithm = (data.get('requested_algorithm') or data.get('algorithm') or '').strip()
            requested_validity_years = data.get('requested_validity_years')
            norm_algo = None
            if requested_algorithm:
                # Normalize to canonical tokens used server‑side
                al = requested_algorithm.lower().replace(' ', '').replace('_', '-')
                if al in ('ecdsa-p256', 'ecc-p256', 'ec-p256', 'p-256'):
                    norm_algo = 'ecc-p256'
                elif al in ('ecdsa-p384', 'ecc-p384', 'ec-p384', 'p-384'):
                    norm_algo = 'ecc-p384'
                elif al in ('rsa-4096', 'rsa4096'):
                    norm_algo = 'rsa-4096'
                elif al in ('rsa-3072', 'rsa3072'):
                    norm_algo = 'rsa-3072'
                else:
                    # Keep raw value but lowercased
                    norm_algo = al

            if norm_algo:
                db = get_db()
                if db is not None:
                    # Scope by organization for non‑super admins
                    org_filter = {}
                    if g.current_user.get('role') != 'super_admin':
                        org_filter = {'organization_id': g.current_user.get('organization_id')}
                    dev = db.devices.find_one({'device_id': device_id, **org_filter}) or db.devices.find_one({'device_id': device_id})
                    if dev:
                        db.devices.update_one({'_id': dev['_id']}, {'$set': {
                            'certificate_algorithm': norm_algo,
                            'metadata.certificate_algorithm': norm_algo
                        }})
        except Exception as e_set:
            logger.warning(f"Renewal requested algorithm persist failed for {device_id}: {e_set}")

        # Prefer PKI‑backed issuance for renewal so algorithm actually changes
        from ..services.certificate_service import issue_device_certificate as issue_service
        try:
            issue_result = issue_service(device_id, g.current_user)
            if isinstance(issue_result, dict) and 'error' not in issue_result:
                logger.info(f"PKI renewal (issue) completed for {device_id} by {g.current_user.get('email')}")
                # Unwrap to match UI expectations: return the certificate object
                result = issue_result.get('certificate') if isinstance(issue_result, dict) else issue_result
            else:
                raise RuntimeError(str(getattr(issue_result, 'get', lambda *_: '')('error') or 'Unknown issuance error'))
        except Exception as e_issue:
            logger.warning(f"PKI issuance path failed for renewal of {device_id}: {e_issue}. Falling back to legacy renew.")
            # Legacy in-place renew (date/serial only; does not change algorithm)
            result = renew_certificate_service(device_id, g.current_user)
            if not result:
                return jsonify({'error': 'Device not found or access denied'}), 404
            
        logger.info(f"Certificate renewed for device {device_id} by {g.current_user.get('email')}")

        # Notify organization admins about the renewal (best effort)
        try:
            db = get_db()
            device_doc = device
            if not device_doc and db:
                device_doc = db.devices.find_one({'device_id': device_id})
            if device_doc and device_doc.get('organization_id'):
                notification_acl_service.create_device_certificate_notification(
                    event='certificate_renewed',
                    device=device_doc,
                    organization_id=str(device_doc.get('organization_id')),
                    actor=g.current_user,
                    priority='medium',
                    metadata={
                        'days_remaining': days_remaining,
                        'renewal_method': data.get('renewal_method', 'automatic'),
                    },
                )
        except Exception as notify_error:
            logger.debug(f"Certificate renewal notification skipped: {notify_error}")

        # Audit log with early-renewal context
        try:
            from ..services.audit_service import audit_log, AuditAction
            details = {
                'early_renewal': bool((days_remaining or 0) > int(os.environ.get('EARLY_RENEWAL_THRESHOLD_DAYS', '60'))),
                'days_remaining': days_remaining,
                'justification': justification or None
            }
            audit_log(
                action=AuditAction.CERTIFICATE_ISSUE,
                user=g.current_user,
                resource_type='device',
                resource_id=device_id,
                details=details,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception:
            pass
        
        return jsonify({
            'message': 'Certificate renewed successfully',
            'certificate': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error renewing certificate: {e}")
        return jsonify({'error': 'Failed to renew certificate'}), 500

@devices_bp.route('/<device_id>/certificate/revoke', methods=['POST'])
@require_auth
@validate_request_size(max_size=1024*512)  # 512KB limit
def revoke_certificate(device_id):
    """
    Revoke device certificate.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "reason": "Reason for revocation"
        }
    
    Returns:
        200: Certificate revoked
        404: Device not found
        500: Server error
    """
    try:
        # Validate device_id parameter
        if not device_id or len(device_id) > 64:
            return jsonify({
                'error': 'Invalid device ID parameter',
                'code': 'INVALID_DEVICE_ID'
            }), 400
        
        device_id = sanitize_string(device_id, 64)
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Manual revocation requested')
        
        # Sanitize reason field
        if isinstance(reason, str):
            reason = sanitize_string(reason, 500)
        else:
            reason = 'Manual revocation requested'
        
        try:
            result = revoke_device_certificate(device_id, reason, g.current_user)
        except CertificateRevocationError as rev_err:
            # Fail CLOSED: Vault PKI revocation could not be enforced, so we did
            # NOT flip the MongoDB status. Surface an accurate error instead of
            # pretending the certificate was revoked.
            logger.error(
                f"Certificate revocation NOT enforced for device {device_id}: {rev_err}"
            )
            return jsonify({
                'error': 'Certificate revocation could not be enforced',
                'code': getattr(rev_err, 'code', 'REVOCATION_FAILED'),
                'details': str(rev_err)
            }), getattr(rev_err, 'status_code', 502)

        if result is None:
            return jsonify({'error': 'Device not found or access denied'}), 404

        logger.info(f"Certificate revoked for device {device_id} by {g.current_user.get('email')}")

        try:
            db = get_db()
            device_doc = db.devices.find_one({'device_id': device_id}) if db is not None else None
            if device_doc and device_doc.get('organization_id'):
                notification_acl_service.create_device_certificate_notification(
                    event='certificate_revoked',
                    device=device_doc,
                    organization_id=str(device_doc.get('organization_id')),
                    actor=g.current_user,
                    priority='high',
                    metadata={'reason': reason},
                )
        except Exception as notify_error:
            logger.debug(f"Certificate revocation notification skipped: {notify_error}")
        
        return jsonify({
            'message': 'Certificate revoked successfully',
            'device_id': device_id,
            'revoked_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error revoking certificate: {e}")
        return jsonify({'error': 'Failed to revoke certificate'}), 500

def convert_fields_to_properties(fields):
    """
    Convert fields format to JSON Schema properties format.
    
    Args:
        fields: Either a dict or list of field definitions
        
    Returns:
        Dict with properties and required fields in JSON Schema format
    """
    properties = {}
    required = []
    
    if isinstance(fields, dict):
        # Handle dict format (e.g., medical_device)
        for field_name, field_def in fields.items():
            properties[field_name] = {
                'type': field_def.get('type', 'string'),
                'description': field_def.get('label', ''),
            }
            
            # Add enum values if present
            if 'options' in field_def:
                properties[field_name]['enum'] = field_def['options']
                
            # Add default value if present
            if 'default' in field_def:
                properties[field_name]['default'] = field_def['default']
                
            # Track required fields
            if field_def.get('required', False):
                required.append(field_name)
                
    elif isinstance(fields, list):
        # Handle list format (e.g., industrial_iot)
        for field_def in fields:
            field_name = field_def.get('name')
            if field_name:
                properties[field_name] = {
                    'type': field_def.get('type', 'string'),
                    'description': field_def.get('label', ''),
                }
                
                # Track required fields
                if field_def.get('required', False):
                    required.append(field_name)
    
    return {
        'properties': properties,
        'required': required
    }

@devices_bp.route('/schemas/<schema_type>', methods=['GET'])
@require_auth
def get_device_schema(schema_type):
    """
    Get device schema for a specific industry/type.
    
    Args:
        schema_type: Schema type (e.g., medical_device, wellness_device)
        
    Returns:
        200: Schema definition
        404: Schema not found
    """
    # Define schemas for different device types
    schemas = {
        'medical_device': {
            'type': 'medical_device',
            'name': 'Medical Device',
            'fields': {
                'fda_class': {
                    'type': 'select',
                    'label': 'FDA Device Class',
                    'options': ['Class I', 'Class II', 'Class III'],
                    'required': False
                },
                'clinical_parameters': {
                    'type': 'multiselect',
                    'label': 'Clinical Parameters',
                    'options': ['Heart Rate', 'Blood Pressure', 'Temperature', 'SpO2', 'ECG'],
                    'required': False
                },
                'hipaa_compliant': {
                    'type': 'boolean',
                    'label': 'HIPAA Compliant',
                    'default': False
                },
                'emergency_contact': {
                    'type': 'text',
                    'label': 'Emergency Contact',
                    'required': False
                }
            }
        },
        'wellness_device': {
            'type': 'wellness_device',
            'name': 'Wellness Device',
            'fields': {
                'device_type': {
                    'type': 'select',
                    'label': 'Device Type',
                    'options': ['Fitness Tracker', 'Sleep Monitor', 'Smart Scale', 'Wellness Hub'],
                    'required': False
                },
                'metrics_tracked': {
                    'type': 'multiselect',
                    'label': 'Metrics Tracked',
                    'options': ['Steps', 'Calories', 'Sleep Quality', 'Heart Rate Variability', 'Stress Level'],
                    'required': False
                },
                'companion_app': {
                    'type': 'text',
                    'label': 'Companion App',
                    'required': False
                }
            }
        },
        'industrial_device': {
            'type': 'industrial_device',
            'name': 'Industrial Device',
            'fields': {
                'protocol': {
                    'type': 'select',
                    'label': 'Communication Protocol',
                    'options': ['mqtts', 'https'],
                    'required': False
                },
                'network_type': {
                    'type': 'select',
                    'label': 'Network Type',
                    'options': ['nbiot', 'lorawan', 'wifi', 'cellular', 'bluetooth', 'zigbee', 'modbus', 'opcua', 'matter'],
                    'required': False
                },
                'safety_zone': {
                    'type': 'select',
                    'label': 'Safety Zone',
                    'options': ['Zone 0', 'Zone 1', 'Zone 2', 'Safe Area'],
                    'required': False
                }
            }
        },
        'smart_city_device': {
            'type': 'smart_city_device',
            'name': 'Smart City Device',
            'fields': {
                'deployment_location': {
                    'type': 'select',
                    'label': 'Deployment Location',
                    'options': ['Street', 'Park', 'Building', 'Transit Station'],
                    'required': False
                },
                'public_access': {
                    'type': 'boolean',
                    'label': 'Public Access Enabled',
                    'default': False
                }
            }
        },
        'smart_energy_device': {
            'type': 'smart_energy_device',
            'name': 'Smart Energy Device',
            'fields': {
                'energy_type': {
                    'type': 'select',
                    'label': 'Energy Type',
                    'options': ['Solar', 'Wind', 'Battery', 'Grid-tied'],
                    'required': False
                },
                'grid_connection': {
                    'type': 'boolean',
                    'label': 'Grid Connected',
                    'default': False
                }
            }
        },
        'agricultural_device': {
            'type': 'agricultural_device',
            'name': 'Agricultural Device',
            'fields': {
                'sensor_type': {
                    'type': 'select',
                    'label': 'Sensor Type',
                    'options': ['Soil Moisture', 'Temperature', 'pH', 'Light', 'Humidity'],
                    'required': False
                },
                'crop_type': {
                    'type': 'text',
                    'label': 'Crop Type',
                    'required': False
                }
            }
        },
        # Industry 4.0 device schemas
        'industrial_iot': {
            'type': 'industrial_iot',
            'name': 'Industrial IoT',
            'fields': [
                {'name': 'communication_protocol', 'label': 'Communication Protocol', 'type': 'select', 'options': ['mqtts', 'https'], 'required': True},
                {'name': 'network_type', 'label': 'Network Type', 'type': 'select', 'options': ['nbiot', 'lorawan', 'wifi', 'cellular', 'bluetooth', 'zigbee', 'modbus', 'opcua', 'matter'], 'required': False},
                {'name': 'plc_type', 'label': 'PLC Type', 'type': 'text', 'required': False},
                {'name': 'scada_integration', 'label': 'SCADA Integration', 'type': 'switch', 'required': False},
                {'name': 'data_frequency', 'label': 'Data Frequency', 'type': 'number', 'required': False}
            ]
        },
        'robotics': {
            'type': 'robotics',
            'name': 'Robotics',
            'fields': [
                {'name': 'robot_type', 'label': 'Robot Type', 'type': 'text', 'required': True},
                {'name': 'payload_capacity', 'label': 'Payload Capacity', 'type': 'number', 'required': False},
                {'name': 'safety_mode', 'label': 'Safety Mode', 'type': 'text', 'required': False}
            ]
        },
        'amr_agv': {
            'type': 'amr_agv',
            'name': 'AMR/AGV',
            'fields': [
                {'name': 'vehicle_type', 'label': 'Vehicle Type', 'type': 'text', 'required': True},
                {'name': 'max_load', 'label': 'Max Load', 'type': 'number', 'required': False},
                {'name': 'navigation_type', 'label': 'Navigation Type', 'type': 'text', 'required': False}
            ]
        },
        # Gateway schema
        'gateway': {
            'type': 'gateway',
            'name': 'Gateway',
            'fields': {
                'gateway_type': {
                    'type': 'select',
                    'label': 'Gateway Type',
                    'options': ['Edge Gateway', 'Protocol Gateway', 'Cloud Gateway', 'Industrial Gateway'],
                    'required': False
                },
                'supported_protocols': {
                    'type': 'multiselect',
                    'label': 'Supported Protocols',
                    'options': ['mqtts', 'https'],
                    'required': False
                },
                'network_type': {
                    'type': 'select',
                    'label': 'Network Type',
                    'options': ['nbiot', 'lorawan', 'wifi', 'cellular', 'bluetooth', 'zigbee', 'modbus', 'opcua', 'matter'],
                    'required': False
                },
                'max_connections': {
                    'type': 'number',
                    'label': 'Max Connections',
                    'required': False
                },
                'edge_computing': {
                    'type': 'boolean',
                    'label': 'Edge Computing Enabled',
                    'default': False
                },
                'data_processing': {
                    'type': 'multiselect',
                    'label': 'Data Processing Capabilities',
                    'options': ['Filtering', 'Aggregation', 'Analytics', 'Machine Learning', 'Protocol Translation'],
                    'required': False
                }
            }
        },
        # Actuator schema
        'actuator': {
            'type': 'actuator',
            'name': 'Actuator',
            'fields': {
                'actuator_type': {
                    'type': 'select',
                    'label': 'Actuator Type',
                    'options': ['Motor', 'Valve', 'Relay', 'Solenoid', 'Servo', 'Pump', 'Light', 'HVAC Control'],
                    'required': False
                },
                'control_type': {
                    'type': 'select',
                    'label': 'Control Type',
                    'options': ['On/Off', 'PWM', 'Analog', 'Digital', 'Proportional'],
                    'required': False
                },
                'power_rating': {
                    'type': 'number',
                    'label': 'Power Rating (W)',
                    'required': False
                },
                'voltage_rating': {
                    'type': 'text',
                    'label': 'Voltage Rating',
                    'required': False
                },
                'response_time': {
                    'type': 'number',
                    'label': 'Response Time (ms)',
                    'required': False
                },
                'safety_features': {
                    'type': 'multiselect',
                    'label': 'Safety Features',
                    'options': ['Emergency Stop', 'Overload Protection', 'Position Feedback', 'Fault Detection', 'Manual Override'],
                    'required': False
                }
            }
        },
        # Sensor schema
        'sensor': {
            'type': 'sensor',
            'name': 'Sensor',
            'fields': {
                'sensor_type': {
                    'type': 'select',
                    'label': 'Sensor Type',
                    'options': ['Temperature', 'Humidity', 'Pressure', 'Motion', 'Light', 'Sound', 'Gas', 'Vibration', 'Proximity', 'Flow'],
                    'required': False
                },
                'measurement_unit': {
                    'type': 'text',
                    'label': 'Measurement Unit',
                    'required': False
                },
                'measurement_range': {
                    'type': 'text',
                    'label': 'Measurement Range',
                    'required': False
                },
                'accuracy': {
                    'type': 'text',
                    'label': 'Accuracy',
                    'required': False
                },
                'sampling_rate': {
                    'type': 'number',
                    'label': 'Sampling Rate (Hz)',
                    'required': False
                },
                'calibration_required': {
                    'type': 'boolean',
                    'label': 'Calibration Required',
                    'default': False
                }
            }
        },
        # Controller schema
        'controller': {
            'type': 'controller',
            'name': 'Controller',
            'fields': {
                'controller_type': {
                    'type': 'select',
                    'label': 'Controller Type',
                    'options': ['PLC', 'Microcontroller', 'Industrial PC', 'PAC', 'DCS', 'RTU'],
                    'required': False
                },
                'programming_language': {
                    'type': 'multiselect',
                    'label': 'Programming Languages',
                    'options': ['Ladder Logic', 'Function Block', 'Structured Text', 'C/C++', 'Python', 'IEC 61131-3'],
                    'required': False
                },
                'io_points': {
                    'type': 'number',
                    'label': 'I/O Points',
                    'required': False
                },
                'communication_interfaces': {
                    'type': 'multiselect',
                    'label': 'Communication Interfaces',
                    'options': ['Ethernet', 'RS-232', 'RS-485', 'CAN', 'USB', 'Wireless'],
                    'required': False
                },
                'redundancy': {
                    'type': 'boolean',
                    'label': 'Redundancy Support',
                    'default': False
                }
            }
        },
        # Smart Home schema
        'smart_home': {
            'type': 'smart_home',
            'name': 'Smart Home',
            'fields': {
                'device_category': {
                    'type': 'select',
                    'label': 'Device Category',
                    'options': ['Lighting', 'Security', 'Climate', 'Entertainment', 'Appliance', 'Voice Assistant'],
                    'required': False
                },
                'integration_platform': {
                    'type': 'multiselect',
                    'label': 'Integration Platforms',
                    'options': ['Alexa', 'Google Home', 'Apple HomeKit', 'SmartThings', 'Hubitat', 'Home Assistant'],
                    'required': False
                },
                'connectivity': {
                    'type': 'multiselect',
                    'label': 'Connectivity',
                    'options': ['WiFi', 'Zigbee', 'Z-Wave', 'Bluetooth', 'Thread', 'Matter'],
                    'required': False
                },
                'voice_control': {
                    'type': 'boolean',
                    'label': 'Voice Control Enabled',
                    'default': False
                },
                'automation_support': {
                    'type': 'boolean',
                    'label': 'Automation Support',
                    'default': True
                }
            }
        }
    }
    
    if schema_type not in schemas:
        return jsonify({'error': f'Schema not found: {schema_type}'}), 404
    
    # Get the schema definition
    schema = schemas[schema_type]
    
    # Convert fields to properties format if needed
    if 'fields' in schema:
        schema_properties = convert_fields_to_properties(schema['fields'])
        # Return schema in JSON Schema format expected by frontend
        return jsonify({
            'type': schema.get('type', schema_type),
            'name': schema.get('name', ''),
            'properties': schema_properties['properties'],
            'required': schema_properties['required']
        }), 200
    else:
        # Schema is already in the correct format
        return jsonify(schema), 200
# [MODULARIZE:END] - DeviceCertificateController

# [MODULARIZE:START] - AutoRegistrationController# Description: Automatic device registration management
# Dependencies: auto_device_registration_service
# Estimated Size: 200 lines
# Priority: MEDIUM
@devices_bp.route('/auto-registration/settings', methods=['GET', 'PUT'])
@require_auth
@require_role(['admin', 'super_admin', 'organization_admin'])
@validate_request_size(max_size=1024*1024)  # 1MB limit
def manage_auto_registration_settings():
    """
    Manage automatic device registration settings for organization.
    
    GET: Returns current auto-registration settings
    PUT: Updates auto-registration settings
    
    Returns:
        200: Settings retrieved/updated successfully
        403: Insufficient permissions
        500: Server error
    """
    if request.method == 'GET':
        try:
            db = get_db()
            org_id = g.current_user.get('organization_id', '')
            
            # Get organization to check current settings
            org = db.organizations.find_one({
                '$or': [
                    {'_id': ObjectId(org_id) if ObjectId.is_valid(org_id) else None},
                    {'organization_id': org_id}
                ]
            })
            
            if not org:
                return jsonify({'error': 'Organization not found'}), 404
            
            settings = {
                'auto_registration_enabled': org.get('auto_registration_enabled', True),
                'auto_registration_notifications': org.get('auto_registration_notifications', True),
                'auto_registration_require_approval': org.get('auto_registration_require_approval', False),
                'auto_registration_default_type': org.get('auto_registration_default_type', 'sensor')
            }
            
            return jsonify(settings), 200
            
        except Exception as e:
            logger.error(f"Error getting auto-registration settings: {e}")
            return jsonify({'error': 'Failed to retrieve settings'}), 500
    
    else:  # PUT
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No settings data provided'}), 400
            
            # Validate settings data
            valid_keys = {
                'auto_registration_enabled', 'auto_registration_notifications',
                'auto_registration_require_approval', 'auto_registration_default_type'
            }
            
            # Remove invalid keys and sanitize values
            cleaned_data = {}
            for key, value in data.items():
                if key in valid_keys:
                    if key.endswith('_enabled') or key.endswith('_notifications') or key.endswith('_approval'):
                        # Boolean fields
                        cleaned_data[key] = bool(value)
                    elif key == 'auto_registration_default_type':
                        # String field with limited values
                        valid_types = ['sensor', 'actuator', 'gateway', 'medical_device', 'wellness_device']
                        if isinstance(value, str) and value in valid_types:
                            cleaned_data[key] = value
                        else:
                            cleaned_data[key] = 'sensor'
            
            data = cleaned_data
            if not data:
                return jsonify({'error': 'No valid settings data provided'}), 400
            
            org_id = g.current_user.get('organization_id', '')
            
            success = auto_device_registration_service.update_organization_auto_registration_settings(
                org_id, data, g.current_user
            )
            
            if success:
                return jsonify({
                    'message': 'Auto-registration settings updated successfully',
                    'settings': data
                }), 200
            else:
                return jsonify({'error': 'Failed to update settings'}), 500
            
        except Exception as e:
            logger.error(f"Error updating auto-registration settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500

@devices_bp.route('/auto-registration/history', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_auto_registration_history():
    """
    Get auto-registration history for organization.
    
    Query Parameters:
        limit: Maximum number of records (default: 100)
        
    Returns:
        200: Auto-registration history
        500: Server error
    """
    try:
        # Validate query parameters
        try:
            limit = int(request.args.get('limit', 100))
            if limit < 1 or limit > 10000:
                limit = 100
        except (ValueError, TypeError):
            limit = 100
        org_id = g.current_user.get('organization_id', '')
        
        history = auto_device_registration_service.get_auto_registration_history(org_id, limit)
        
        return jsonify({
            'organization_id': org_id,
            'history': history,
            'total': len(history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting auto-registration history: {e}")
        return jsonify({'error': 'Failed to retrieve history'}), 500

@devices_bp.route('/telemetry/cache/metrics', methods=['GET'])
@require_auth
@require_role(['admin', 'super_admin', 'organization_admin'])
def get_telemetry_cache_metrics():
    """
    Get telemetry cache performance metrics.
    
    Returns:
        200: Cache metrics including hit rate, misses, errors
        500: Server error
    """
    try:
        metrics = telemetry_cache_service.get_cache_metrics()
        
        return jsonify({
            'cache_metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving cache metrics: {e}")
        return jsonify({'error': 'Failed to retrieve cache metrics'}), 500
# [MODULARIZE:END] - AutoRegistrationController

# =============================================================================
# PROVISIONING ENDPOINTS
# =============================================================================

# [MODULARIZE:START] - BulkProvisioningController# Description: Bulk device import and provisioning
# Dependencies: provisioning_service, validation
# Estimated Size: 300 lines
# Priority: MEDIUM

@devices_bp.route('/bulk-import/template', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def download_csv_template():
    """
    Download CSV template for bulk device import with Trust M UID support.

    Returns:
        200: CSV template file
        500: Server error
    """
    try:
        from ..utils.csv_parser import TrustMCSVParser
        from flask import make_response

        csv_content = TrustMCSVParser.generate_template_csv()

        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=device_bulk_import_template.csv'

        logger.info(f"CSV template downloaded by {g.current_user.get('email')}")
        return response

    except Exception as e:
        logger.error(f"Error generating CSV template: {e}")
        return jsonify({'error': 'Failed to generate CSV template'}), 500

@devices_bp.route('/bulk-import/validate-csv', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
@validate_request_size(max_size=10*1024*1024)  # 10MB limit
def validate_csv_import():
    """
    Validate CSV file for bulk import without creating devices.

    Request JSON:
        {
            "csv_content": "device_id,name,type,auth_mode,trustm_uid\n..."
        }

    Returns:
        200: Validation results with preview
        400: Invalid CSV format
        500: Server error
    """
    try:
        from ..utils.csv_parser import TrustMCSVParser, CSVParserError

        data = request.get_json()
        csv_content = data.get('csv_content', '')

        if not csv_content:
            return jsonify({'error': 'No CSV content provided'}), 400

        # Validate CSV
        result = TrustMCSVParser.validate_csv_file(csv_content)

        logger.info(f"CSV validation by {g.current_user.get('email')}: {result['device_count']} devices, valid={result['valid']}")
        return jsonify(result), 200

    except CSVParserError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error validating CSV: {e}")
        return jsonify({'error': 'Failed to validate CSV'}), 500

@devices_bp.route('/bulk-import', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_CREATE)
@validate_request_size(max_size=10*1024*1024)  # 10MB limit for bulk imports
# @validate_json_schema(BULK_IMPORT_SCHEMA)  # Temporarily disabled - schema not imported
def bulk_import_devices():
    """
    Bulk import devices from CSV/JSON data.

    Request JSON:
        {
            "template_id": "optional-template-id",
            "file_format": "csv|json",
            "csv_content": "device_id,name,...",  // For CSV format
            "devices": [...],  // For JSON format
            "options": {
                "auto_activate": true,
                "generate_certificates": true,
                "skip_duplicates": true
            }
        }

    Returns:
        201: Bulk import session created
        400: Invalid request data
        403: Insufficient permissions
        500: Server error
    """
    try:
        from ..utils.csv_parser import TrustMCSVParser, CSVParserError

        data = request.get_json()
        file_format = data.get('file_format', 'json').lower()

        # Parse CSV if format is CSV
        if file_format == 'csv':
            csv_content = data.get('csv_content', '')
            if not csv_content:
                return jsonify({'error': 'No CSV content provided'}), 400

            try:
                devices = TrustMCSVParser.parse_csv_string(csv_content)
                data['devices'] = devices
                data['file_format'] = 'csv'
                logger.info(f"Parsed {len(devices)} devices from CSV")
            except CSVParserError as e:
                return jsonify({'error': f'CSV parsing error: {str(e)}'}), 400

        # Bulk create devices using device_service
        devices_data = data.get('devices', [])
        if not devices_data:
            return jsonify({'error': 'No devices provided'}), 400

        options = data.get('options', {})
        organization_id = g.current_user.get('organization_id')
        created_by = g.current_user.get('email')

        created_devices = []
        failed_devices = []

        for device_data in devices_data:
            try:
                # Add organization and creator info
                device_data['organization_id'] = organization_id
                device_data['created_by'] = created_by

                # Create device
                device = create_device(device_data, g.current_user)
                created_devices.append({
                    'device_id': device.get('device_id'),
                    'status': 'created'
                })
            except Exception as device_error:
                if options.get('skip_duplicates') and 'already exists' in str(device_error).lower():
                    continue
                failed_devices.append({
                    'device_id': device_data.get('device_id', 'unknown'),
                    'error': str(device_error)
                })

        result = {
            'success': len(failed_devices) == 0,
            'created_count': len(created_devices),
            'failed_count': len(failed_devices),
            'created_devices': created_devices,
            'failed_devices': failed_devices
        }

        logger.info(f"Bulk import by {created_by}: {len(created_devices)} created, {len(failed_devices)} failed")
        return jsonify(result), 201 if result['success'] else 207

    except Exception as e:
        logger.error(f"Error in bulk import: {e}")
        return jsonify({'error': 'Failed to start bulk import'}), 500

@devices_bp.route('/templates', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_provisioning_templates():
    """
    Get provisioning templates for the organization.
    
    Returns:
        200: List of templates
        500: Server error
    """
    try:
        organization_id = g.current_user.get('organization_id', '')
        templates = provisioning_service.get_templates(organization_id, g.current_user)
        
        return jsonify({
            'templates': templates,
            'total': len(templates)
        }), 200
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error getting templates: {e.message}")
        return jsonify({
            'error': e.message,
            'code': e.code
        }), 400
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return jsonify({'error': 'Failed to get templates'}), 500

@devices_bp.route('/templates', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_CREATE)
@validate_request_size(max_size=1024*1024)  # 1MB limit
# @validate_json_schema(TEMPLATE_SCHEMA)  # Temporarily disabled - schema not imported
def create_provisioning_template():
    """
    Create a new provisioning template.
    
    Request JSON:
        {
            "name": "Template Name",
            "description": "Template description",
            "device_type": "sensor|actuator|gateway",
            "auth_type": "certificate|api_key|shared_secret",
            "default_settings": {
                "certificate_algorithm": "RSA-2048",
                "certificate_validity_days": 365,
                "telemetry_interval": 60
            },
            "provisioning_config": {
                "auto_activate": true,
                "require_approval": false,
                "notification_enabled": true,
                "batch_size": 100
            }
        }
    
    Returns:
        201: Template created
        400: Invalid request data
        500: Server error
    """
    try:
        data = request.get_json()
        
        template = provisioning_service.create_template(data, g.current_user)
        
        logger.info(f"Provisioning template created by {g.current_user.get('email')}: {template['template_id']}")
        return jsonify(template), 201
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error creating template: {e.message}")
        return jsonify({
            'error': e.message,
            'code': e.code
        }), 400
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return jsonify({'error': 'Failed to create template'}), 500

@devices_bp.route('/templates/<template_id>', methods=['PUT'])
@require_auth
@require_permission(Permission.DEVICE_UPDATE)
@validate_request_size(max_size=1024*1024)  # 1MB limit
def update_provisioning_template(template_id):
    """
    Update an existing provisioning template.
    
    Args:
        template_id: Template ID to update
        
    Request JSON: Partial template data to update
    
    Returns:
        200: Template updated
        404: Template not found
        500: Server error
    """
    try:
        # Validate template_id parameter
        if not template_id or len(template_id) > 100:
            return jsonify({
                'error': 'Invalid template ID parameter',
                'code': 'INVALID_TEMPLATE_ID'
            }), 400
        
        template_id = sanitize_string(template_id, 100)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No update data provided'}), 400
        
        template = provisioning_service.update_template(template_id, data, g.current_user)
        
        logger.info(f"Provisioning template updated by {g.current_user.get('email')}: {template_id}")
        return jsonify(template), 200
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error updating template: {e.message}")
        status_code = 404 if e.code == 'TEMPLATE_NOT_FOUND' else 400
        return jsonify({
            'error': e.message,
            'code': e.code
        }), status_code
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        return jsonify({'error': 'Failed to update template'}), 500

@devices_bp.route('/templates/<template_id>', methods=['DELETE'])
@require_auth
@require_permission(Permission.DEVICE_DELETE)
def delete_provisioning_template(template_id):
    """
    Delete a provisioning template.
    
    Args:
        template_id: Template ID to delete
    
    Returns:
        200: Template deleted
        404: Template not found
        500: Server error
    """
    try:
        # Validate template_id parameter
        if not template_id or len(template_id) > 100:
            return jsonify({
                'error': 'Invalid template ID parameter',
                'code': 'INVALID_TEMPLATE_ID'
            }), 400
        
        template_id = sanitize_string(template_id, 100)
        
        success = provisioning_service.delete_template(template_id, g.current_user)
        
        if not success:
            return jsonify({'error': 'Failed to delete template'}), 500
        
        logger.info(f"Provisioning template deleted by {g.current_user.get('email')}: {template_id}")
        return jsonify({'message': 'Template deleted successfully'}), 200
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error deleting template: {e.message}")
        status_code = 404 if e.code == 'TEMPLATE_NOT_FOUND' else 400
        return jsonify({
            'error': e.message,
            'code': e.code
        }), status_code
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        return jsonify({'error': 'Failed to delete template'}), 500

@devices_bp.route('/provision/zero-touch', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_CREATE)
@validate_request_size(max_size=1024*1024)  # 1MB limit
# @validate_json_schema(ZERO_TOUCH_PROVISIONING_SCHEMA)  # Temporarily disabled - schema not imported
def zero_touch_provisioning():
    """
    Start zero-touch provisioning for auto-discovery of devices.
    
    Request JSON:
        {
            "template_id": "template-id",
            "discovery_method": "dhcp|mdns|scan",
            "network_range": "192.168.1.0/24",
            "device_filters": {
                "manufacturer": "ACME",
                "model": "Sensor-v2",
                "mac_prefixes": ["00:1A:2B"]
            },
            "auto_provision": true,
            "require_approval": false
        }
    
    Returns:
        202: Zero-touch provisioning started
        400: Invalid request data
        500: Server error
    """
    try:
        # Platform admins can perform zero-touch provisioning
        
        data = request.get_json()
        
        # For now, return a placeholder response
        # TODO: Implement actual zero-touch provisioning logic
        session_id = f"ztp_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Zero-touch provisioning requested by {g.current_user.get('email')}")
        return jsonify({
            'message': 'Zero-touch provisioning started',
            'session_id': session_id,
            'status': 'pending',
            'discovery_method': data.get('discovery_method'),
            'auto_provision': data.get('auto_provision', False)
        }), 202
        
    except Exception as e:
        logger.error(f"Error in zero-touch provisioning: {e}")
        return jsonify({'error': 'Failed to start zero-touch provisioning'}), 500

@devices_bp.route('/provisioning/status/<session_id>', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_provisioning_status(session_id):
    """
    Get provisioning session status.
    
    Args:
        session_id: Provisioning session ID
    
    Returns:
        200: Session status
        404: Session not found
        500: Server error
    """
    try:
        # Validate session_id parameter
        if not session_id or len(session_id) > 100:
            return jsonify({
                'error': 'Invalid session ID parameter',
                'code': 'INVALID_SESSION_ID'
            }), 400
        
        session_id = sanitize_string(session_id, 100)
        
        session = provisioning_service.get_provisioning_status(session_id, g.current_user)
        
        return jsonify(session), 200
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error getting status: {e.message}")
        status_code = 404 if e.code == 'SESSION_NOT_FOUND' else 400
        return jsonify({
            'error': e.message,
            'code': e.code
        }), status_code
    except Exception as e:
        logger.error(f"Error getting provisioning status: {e}")
        return jsonify({'error': 'Failed to get provisioning status'}), 500

@devices_bp.route('/provisioning/history', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_provisioning_history():
    """
    Get provisioning history for the organization.
    
    Query Parameters:
        limit: Maximum number of records (default: 100)
    
    Returns:
        200: Provisioning history
        500: Server error
    """
    try:
        # Validate query parameters
        try:
            limit = int(request.args.get('limit', 100))
            if limit < 1 or limit > 1000:
                limit = 100
        except (ValueError, TypeError):
            limit = 100
        
        history = provisioning_service.get_provisioning_history(g.current_user, limit)
        
        return jsonify({
            'history': history,
            'total': len(history)
        }), 200
        
    except ProvisioningError as e:
        logger.warning(f"Provisioning error getting history: {e.message}")
        return jsonify({
            'error': e.message,
            'code': e.code
        }), 400
    except Exception as e:
        logger.error(f"Error getting provisioning history: {e}")
        return jsonify({'error': 'Failed to get provisioning history'}), 500
# [MODULARIZE:END] - BulkProvisioningController

# Public Key Registration endpoints

# [MODULARIZE:START] - PublicKeyController# Description: Device public key registration and retrieval
# Dependencies: device_service, certificate_service
# Estimated Size: 200 lines
# Priority: HIGH
@devices_bp.route('/<device_id>/public-key', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def register_device_public_key(device_id):
    """
    Register or update a device's public key.
    
    This endpoint allows devices or administrators to register a public key
    for a device. The public key can be in PEM format and will be validated
    before storage.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "public_key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----",
            "algorithm": "RSA-2048|RSA-4096|ECC-P256|ECC-P384",  # Optional, will be detected
            "key_usage": ["digital_signature", "key_agreement"],   # Optional
            "expires_at": "2025-12-31T23:59:59Z",                # Optional, ISO format
            "metadata": {                                         # Optional
                "generated_by": "device|admin|external_ca",
                "generation_method": "on_device|cloud|hsm",
                "comments": "Additional information"
            }
        }
    
    Returns:
        200: Public key registered successfully
        400: Invalid public key or parameters
        403: Access denied
        404: Device not found
        500: Registration failed
    """
    try:
        data = request.get_json()
        
        if not data or 'public_key' not in data:
            return jsonify({
                'error': 'MISSING_PUBLIC_KEY',
                'message': 'Public key is required'
            }), 400
        
        public_key_pem = data.get('public_key', '').strip()
        algorithm = data.get('algorithm')
        key_usage = data.get('key_usage', ['digital_signature'])
        expires_at = data.get('expires_at')
        metadata = data.get('metadata', {})
        
        # Validate public key format
        if not public_key_pem:
            return jsonify({
                'error': 'EMPTY_PUBLIC_KEY',
                'message': 'Public key cannot be empty'
            }), 400
        
        # Check PEM format
        if not (public_key_pem.startswith('-----BEGIN PUBLIC KEY-----') or 
                public_key_pem.startswith('-----BEGIN RSA PUBLIC KEY-----') or
                public_key_pem.startswith('-----BEGIN EC PUBLIC KEY-----')):
            return jsonify({
                'error': 'INVALID_FORMAT',
                'message': 'Public key must be in PEM format'
            }), 400
        
        # Validate expiration date if provided
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_dt <= datetime.now():
                    return jsonify({
                        'error': 'INVALID_EXPIRY',
                        'message': 'Expiration date must be in the future'
                    }), 400
            except ValueError:
                return jsonify({
                    'error': 'INVALID_DATE_FORMAT',
                    'message': 'Expiration date must be in ISO format'
                }), 400
        
        # Call service function to register public key
        from ..services.certificate_service import register_device_public_key as register_key_service
        
        result = register_key_service(
            device_id=device_id,
            public_key_pem=public_key_pem,
            algorithm=algorithm,
            key_usage=key_usage,
            expires_at=expires_at,
            metadata=metadata,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error registering public key for device {device_id}: {e}")
        return jsonify({
            'error': 'REGISTRATION_FAILED',
            'message': 'Failed to register public key',
            'details': str(e)
        }), 500

@devices_bp.route('/<device_id>/public-key', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_device_public_key(device_id):
    """
    Get the registered public key for a device.
    
    This endpoint retrieves the currently registered public key for a device,
    including its metadata and validation status.
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        format: Response format (json|pem|der) - defaults to json
        include_history: Include key rotation history (true|false) - defaults to false
        
    Returns:
        200: Public key information
        404: Device not found or no public key registered
        403: Access denied
        500: Server error
    """
    try:
        response_format = request.args.get('format', 'json').lower()
        include_history = request.args.get('include_history', 'false').lower() == 'true'
        
        # Validate format parameter
        if response_format not in ['json', 'pem', 'der']:
            return jsonify({
                'error': 'INVALID_FORMAT',
                'message': 'Format must be one of: json, pem, der'
            }), 400
        
        # Call service function to get public key
        from ..services.certificate_service import get_device_public_key as get_key_service
        
        result = get_key_service(
            device_id=device_id,
            include_history=include_history,
            user=g.current_user
        )
        
        if not result:
            return jsonify({
                'error': 'NOT_FOUND',
                'message': 'Device not found or no public key registered'
            }), 404
        
        # Handle different response formats
        if response_format == 'json':
            return jsonify(result), 200
        elif response_format == 'pem':
            # Return just the PEM-encoded public key
            if 'public_key' not in result:
                return jsonify({
                    'error': 'NO_PUBLIC_KEY',
                    'message': 'No public key found for device'
                }), 404
            
            from flask import Response
            response = Response(
                result['public_key'],
                mimetype='application/x-pem-file',
                headers={
                    'Content-Disposition': f'attachment; filename={device_id}-public-key.pem',
                    'Content-Type': 'application/x-pem-file'
                }
            )
            return response
        elif response_format == 'der':
            # Convert PEM to DER format
            if 'public_key' not in result:
                return jsonify({
                    'error': 'NO_PUBLIC_KEY',
                    'message': 'No public key found for device'
                }), 404
            
            try:
                from cryptography.hazmat.backends import default_backend
                from cryptography.hazmat.primitives import serialization
                from flask import Response
                
                # Load PEM key
                public_key = serialization.load_pem_public_key(
                    result['public_key'].encode('utf-8'),
                    backend=default_backend()
                )
                
                # Convert to DER
                der_bytes = public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                response = Response(
                    der_bytes,
                    mimetype='application/octet-stream',
                    headers={
                        'Content-Disposition': f'attachment; filename={device_id}-public-key.der',
                        'Content-Type': 'application/octet-stream'
                    }
                )
                return response
            except Exception as e:
                logger.error(f"Error converting PEM to DER: {e}")
                return jsonify({
                    'error': 'CONVERSION_ERROR',
                    'message': 'Failed to convert public key to DER format'
                }), 500
        
    except Exception as e:
        logger.error(f"Error retrieving public key for device {device_id}: {e}")
        return jsonify({
            'error': 'RETRIEVAL_FAILED',
            'message': 'Failed to retrieve public key',
            'details': str(e)
        }), 500
# [MODULARIZE:END] - PublicKeyController

@devices_bp.route('/<device_id>/reset-password', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_UPDATE)
@validate_request_size(max_size=1024)  # 1KB limit
def reset_device_password(device_id):
    """
    Reset the password for a server-TLS authenticated device.
    
    Only works for devices with auth_mode='server_tls'.
    Generates a new secure password and returns it in a one-time view token.
    
    Request body (optional):
    {
        "notify": true,  # Send notification to device owner (default: true)
        "reason": "Password reset requested by admin"  # Audit reason
    }
    
    Response:
    {
        "status": "success",
        "message": "Password reset successfully",
        "reset_token": "unique-token-for-one-time-view",
        "expires_at": "2025-01-30T10:15:00Z",
        "view_url": "/api/v1/devices/{device_id}/password/view/{token}"
    }
    """
    try:
        # Validate device ID
        if not validate_device_id(device_id):
            return jsonify({
                'error': 'INVALID_DEVICE_ID',
                'message': 'Invalid device ID format'
            }), 400
        
        # Get request data
        data = request.get_json() or {}
        notify = data.get('notify', True)
        reason = sanitize_string(data.get('reason', 'Password reset requested by administrator'))
        
        # Import required services
        from ..services.device_service import reset_device_password as reset_password_service
        from ..services.audit_service import audit_log, AuditAction
        
        # Check if device exists and is server-tls
        db = get_db()
        device = db.devices.find_one({
            'device_id': device_id,
            'organization_id': g.current_user.get('organization_id')
        })
        
        if not device:
            return jsonify({
                'error': 'DEVICE_NOT_FOUND',
                'message': 'Device not found'
            }), 404
        
        # Check auth mode
        auth_mode = device.get('auth_mode') or device.get('auth_type', '')
        if auth_mode != 'server_tls':
            return jsonify({
                'error': 'INVALID_AUTH_MODE',
                'message': f'Password reset only available for server-TLS devices. This device uses {auth_mode} authentication.'
            }), 400
        
        # Rate limiting check
        redis = get_redis()
        rate_limit_key = f"password_reset:{device_id}"
        reset_count = redis.get(rate_limit_key)
        
        if reset_count and int(reset_count) >= 3:
            # Compute the real remaining window for Retry-After (project rule:
            # 429s must say when to retry).
            try:
                retry_after = max(1, int(redis.ttl(rate_limit_key)))
            except Exception:
                retry_after = 3600
            response = jsonify({
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': f'Too many password reset attempts. Retry after {retry_after} seconds.',
                'retry_after_seconds': retry_after
            })
            response.headers['Retry-After'] = str(retry_after)
            return response, 429
        
        # Call service to reset password
        result = reset_password_service(
            device_id=device_id,
            reset_by=g.current_user.get('email', g.current_user.get('username', 'unknown')),
            reason=reason,
            notify=notify
        )
        
        if not result:
            return jsonify({
                'error': 'RESET_FAILED',
                'message': 'Failed to reset device password'
            }), 500
        
        # Update rate limit
        redis.incr(rate_limit_key)
        redis.expire(rate_limit_key, 3600)  # 1 hour expiry
        
        # Log security event
        audit_log(
            action=AuditAction.PASSWORD_RESET,
            user=g.current_user,
            resource_type='device',
            resource_id=device_id,
            details={
                'device_name': device.get('name'),
                'reason': reason,
                'notify': notify,
                'reset_token': result.get('reset_token')
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Return success with one-time view token
        return jsonify({
            'status': 'success',
            'message': 'Password reset successfully',
            'reset_token': result.get('reset_token'),
            'expires_at': result.get('expires_at'),
            'view_url': f"/api/v1/devices/{device_id}/password/view/{result.get('reset_token')}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting password for device {device_id}: {e}")
        return jsonify({
            'error': 'RESET_ERROR',
            'message': 'An error occurred while resetting the password',
            'details': str(e) if g.debug_mode else None
        }), 500

@devices_bp.route('/<device_id>/password/view/<token>', methods=['GET'])
@require_auth
def view_device_password(device_id, token):
    """
    View the new password using a one-time token.
    
    The token expires after 5 minutes or after first use.
    """
    try:
        # Validate inputs
        if not validate_device_id(device_id):
            return jsonify({
                'error': 'INVALID_DEVICE_ID',
                'message': 'Invalid device ID format'
            }), 400
        
        if not token or not re.match(r'^[a-zA-Z0-9\-_]{32,64}$', token):
            return jsonify({
                'error': 'INVALID_TOKEN',
                'message': 'Invalid token format'
            }), 400
        
        # Import service
        from ..services.device_service import retrieve_reset_password
        from ..services.audit_service import audit_log, AuditAction
        
        # Retrieve password with token
        result = retrieve_reset_password(
            device_id=device_id,
            token=token,
            user_id=g.current_user.get('id'),
            organization_id=g.current_user.get('organization_id')
        )
        
        if not result:
            return jsonify({
                'error': 'INVALID_OR_EXPIRED',
                'message': 'Token is invalid or has expired'
            }), 404
        
        # Log password view event
        audit_log(
            action=AuditAction.PASSWORD_RESET,
            user=g.current_user,
            resource_type='device',
            resource_id=device_id,
            details={
                'token': token,
                'viewed_by': g.current_user.get('email', g.current_user.get('username', 'unknown'))
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'status': 'success',
            'device_id': device_id,
            'password': result.get('password'),
            'created_at': result.get('created_at'),
            'expires_at': result.get('expires_at'),
            'note': 'This password will not be shown again. Please save it securely.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error viewing password for device {device_id}: {e}")
        return jsonify({
            'error': 'VIEW_ERROR',
            'message': 'An error occurred while retrieving the password',
            'details': str(e) if g.debug_mode else None
        }), 500

@devices_bp.route('/<device_id>/regenerate-api-key', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_UPDATE)
@validate_request_size(max_size=1024)  # 1KB limit
def regenerate_device_api_key_endpoint(device_id):
    """
    Regenerate API key for an existing device.
    
    This endpoint generates a new API key for the device and updates the APISIX consumer.
    The new API key is returned in the response and is the only time it will be visible.
    
    Args:
        device_id: Device identifier
    
    Request body (optional):
    {
        "reason": "API key compromised"  # Audit reason
    }
    
    Response:
    {
        "status": "success",
        "message": "API key regenerated successfully",
        "device_id": "device-123",
        "api_key": "tesa_dak_12345678_abc123...",
        "regenerated_at": "2025-01-30T10:15:00Z",
        "note": "This API key will not be shown again. Please save it securely."
    }
    
    Returns:
        200: API key regenerated successfully
        400: Invalid device ID or device not found
        403: Access denied
        404: Device not found
        500: Server error
    """
    try:
        # Validate device ID
        if not validate_device_id(device_id):
            return jsonify({
                'error': 'INVALID_DEVICE_ID',
                'message': 'Invalid device ID format'
            }), 400
        
        # Get request data
        data = request.get_json() or {}
        reason = sanitize_string(data.get('reason', 'API key regeneration requested by administrator'))
        
        # Import required services
        from ..services.device_auth_service import device_auth_service
        from ..services.audit_service import audit_log, AuditAction
        
        # Check if device exists and user has access
        db = get_db()
        
        # For super_admin and org_admin, allow access to all devices in their org
        if g.current_user.get('role') in ['super_admin', 'org_admin']:
            device = db.devices.find_one({'device_id': device_id})
        else:
            # For regular users, check organization match
            device = db.devices.find_one({
                'device_id': device_id,
                'organization_id': g.current_user.get('organization_id')
            })
        
        if not device:
            return jsonify({
                'error': 'DEVICE_NOT_FOUND',
                'message': 'Device not found or access denied'
            }), 404
        
        # Check rate limiting (max 5 regenerations per hour per device)
        redis = get_redis()
        rate_limit_key = f"api_key_regen:{device_id}"
        current_count = redis.get(rate_limit_key)
        
        if current_count and int(current_count) >= 5:
            # Compute the real remaining window for Retry-After (project rule:
            # 429s must say when to retry).
            try:
                retry_after = max(1, int(redis.ttl(rate_limit_key)))
            except Exception:
                retry_after = 3600
            response = jsonify({
                'error': 'RATE_LIMIT_EXCEEDED',
                'message': f'Too many API key regeneration attempts. Retry after {retry_after} seconds.',
                'retry_after_seconds': retry_after
            })
            response.headers['Retry-After'] = str(retry_after)
            return response, 429
        
        # Call the regenerate API key service
        result = device_auth_service.regenerate_device_api_key(device_id, g.current_user)
        
        if not result.get('success'):
            return jsonify({
                'error': 'REGENERATION_FAILED',
                'message': result.get('error', 'Failed to regenerate API key')
            }), 500
        
        # Update rate limit
        redis.incr(rate_limit_key)
        redis.expire(rate_limit_key, 3600)  # 1 hour expiry
        
        # Log security event
        audit_log(
            action=AuditAction.DEVICE_UPDATE,
            user=g.current_user,
            resource_type='device',
            resource_id=device_id,
            details={
                'action': 'api_key_regenerated',
                'device_name': device.get('name'),
                'reason': reason,
                'new_api_key_prefix': result.get('api_key', '')[:20] + '...' if result.get('api_key') else 'unknown'
            },
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Log to device logs
        try:
            device_logs_service.add_device_log(
                device_id=device_id,
                level='INFO',
                message='API key regenerated successfully',
                log_type='security',
                details={
                    'regenerated_by': g.current_user.get('email'),
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                },
                source='api'
            )
        except Exception as log_error:
            logger.warning(f"Failed to add device log: {log_error}")
        
        # Return success with new API key
        return jsonify({
            'status': 'success',
            'message': 'API key regenerated successfully',
            'device_id': device_id,
            'api_key': result.get('api_key'),
            'regenerated_at': datetime.now().isoformat() + 'Z',
            'note': 'This API key will not be shown again. Please save it securely.'
        }), 200

    except Exception as e:
        logger.error(f"Error regenerating API key for device {device_id}: {e}")
        return jsonify({
            'error': 'REGENERATION_ERROR',
            'message': 'An error occurred while regenerating the API key',
            'details': str(e) if g.debug_mode else None
        }), 500

# =============================================================================
# QR CODE ENDPOINTS - Trust M Device Provisioning
# =============================================================================

@devices_bp.route('/<device_id>/qrcode', methods=['GET'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def get_device_qr_code(device_id):
    """
    Generate QR code for a Trust M device.

    Args:
        device_id: Device identifier

    Query Parameters:
        format: 'png' (default) or 'svg'
        size: QR code box size (default: 10)

    Returns:
        200: QR code data
        404: Device not found or no Trust M UID
        500: Generation failed
    """
    try:
        from ..services.qr_code_service import qr_code_service

        # Get device
        db = get_db()
        device = db.devices.find_one({
            'device_id': device_id,
            'organization_id': g.current_user.get('organization_id')
        })

        if not device:
            return jsonify({'error': 'Device not found'}), 404

        trustm_uid = device.get('trustm_uid')
        if not trustm_uid:
            return jsonify({
                'error': 'NO_TRUSTM_UID',
                'message': 'This device does not have a Trust M UID'
            }), 404

        # Get query parameters
        qr_format = request.args.get('format', 'png').lower()
        box_size = int(request.args.get('size', 10))

        # Generate QR code
        if qr_format == 'svg':
            svg_content = qr_code_service.generate_qr_code_svg(
                trustm_uid=trustm_uid,
                device_id=device_id
            )
            return jsonify({
                'device_id': device_id,
                'trustm_uid': trustm_uid,
                'format': 'svg',
                'svg_content': svg_content
            }), 200
        else:
            qr_result = qr_code_service.generate_qr_code(
                trustm_uid=trustm_uid,
                device_id=device_id,
                box_size=box_size,
                return_base64=True
            )
            return jsonify(qr_result), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error generating QR code for device {device_id}: {e}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

@devices_bp.route('/qrcode/bulk', methods=['POST'])
@require_auth
@require_permission(Permission.DEVICE_VIEW)
def generate_bulk_qr_codes():
    """
    Generate QR codes for multiple Trust M devices.

    Request JSON:
        {
            "device_ids": ["PSoC-E84-001", "PSoC-E84-002"],
            "box_size": 10  // Optional
        }

    Returns:
        200: Array of QR code results
        400: Invalid request
        500: Generation failed
    """
    try:
        from ..services.qr_code_service import qr_code_service

        data = request.get_json()
        device_ids = data.get('device_ids', [])
        box_size = data.get('box_size', 10)

        if not device_ids:
            return jsonify({'error': 'No device_ids provided'}), 400

        # Get devices from database
        db = get_db()
        devices = list(db.devices.find({
            'device_id': {'$in': device_ids},
            'organization_id': g.current_user.get('organization_id'),
            'trustm_uid': {'$exists': True, '$ne': None}
        }))

        if not devices:
            return jsonify({
                'error': 'NO_DEVICES_FOUND',
                'message': 'No devices with Trust M UID found for the provided IDs'
            }), 404

        # Generate QR codes
        qr_results = qr_code_service.generate_bulk_qr_codes(
            devices=devices,
            box_size=box_size
        )

        logger.info(f"Generated {len(qr_results)} QR codes for organization {g.current_user.get('organization_id')}")
        return jsonify({
            'total': len(qr_results),
            'qr_codes': qr_results
        }), 200

    except Exception as e:
        logger.error(f"Error generating bulk QR codes: {e}")
        return jsonify({'error': 'Failed to generate QR codes'}), 500

@devices_bp.route('/qrcode/scan', methods=['POST'])
def scan_qr_code():
    """
    Public endpoint to scan and parse QR code content (NO AUTHENTICATION REQUIRED).

    This endpoint allows unauthenticated scanning of Trust M QR codes to extract
    device information for provisioning workflows.

    Request JSON:
        {
            "qr_content": "TESA:TRUSTM:cdcd0008...:4797831a-e4cb-41f0-8dbc-e7de2dffe696"
        }

    Response:
        {
            "valid": true,
            "trustm_uid": "cdcd0008...",
            "device_id": "4797831a-e4cb-41f0-8dbc-e7de2dffe696",  # Optional
            "format": "new"  # or "legacy"
        }

    Security Note:
        - This endpoint is intentionally public for device provisioning
        - Only parses and validates QR content, does not expose sensitive data
        - Does NOT query database or return device details
    """
    try:
        data = request.get_json()

        if not data or 'qr_content' not in data:
            return jsonify({
                'error': 'Missing qr_content in request body'
            }), 400

        qr_content = data['qr_content']

        # Parse QR content
        from ..services.qr_code_service import qr_code_service
        parsed = qr_code_service.parse_qr_content(qr_content)

        if not parsed:
            return jsonify({
                'valid': False,
                'error': 'Invalid QR code format'
            }), 200

        # Determine format (new format has device_id, legacy doesn't)
        format_type = "new" if 'device_id' in parsed else "legacy"

        response = {
            'valid': True,
            'trustm_uid': parsed['trustm_uid'],
            'format': format_type
        }

        # Include device_id if present
        if 'device_id' in parsed:
            response['device_id'] = parsed['device_id']

        logger.info(f"Public QR scan: trustm_uid={parsed['trustm_uid'][:10]}..., format={format_type}")

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Error scanning QR code: {e}")
        return jsonify({'error': 'Failed to scan QR code'}), 500
