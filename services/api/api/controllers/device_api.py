# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device API Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Device API endpoints for device telemetry submission and configuration.
Supports authentication via APISIX headers (X-Device-ID, X-Auth-Type).
"""

import logging
import json
import msgpack
from datetime import datetime
from flask import Blueprint, request, jsonify, Response, g
from bson import ObjectId

import hashlib

from ..core.database import get_db, get_redis
from ..core.auth import (
    require_auth, authenticate_mtls_request, validate_device_api_key,
    extract_api_key_from_request,
)
from ..services.telemetry_cache_service import telemetry_cache_service
from ..utils.validation import (
    validate_device_id, sanitize_string, validate_request_size,
    ValidationError
)

logger = logging.getLogger(__name__)

# Create blueprint
device_api_bp = Blueprint('device_api', __name__)

# Constants
MAX_TELEMETRY_SIZE = 5 * 1024 * 1024  # 5MB
MAX_BATCH_SIZE = 1000  # Maximum telemetry records in a batch
SUPPORTED_CONTENT_TYPES = ['application/json', 'application/msgpack', 'application/x-msgpack']

def verify_device_auth():
    """
    Authenticate the calling device with REAL credentials (fail-closed).

    SECURITY: this used to trust the X-Device-ID / X-Auth-Type headers with no
    credential check at all, letting anyone submit telemetry or read another
    device's configuration just by naming it. It now accepts ONLY:

      (a) nginx-verified mTLS headers, honoured exclusively with a valid
          X-MTLS-Gateway marker - the same fail-closed helper used by
          core.auth.require_api_key_or_mtls (hmac.compare_digest marker check,
          CHANGEME-treated-as-unset, registry binding, revocation check); or
      (b) a device API key (X-API-KEY or X-Device-API-Key header) validated
          against hashed storage via the API-key security service.

    The authenticated identity is BINDING: when the client also claims an
    X-Device-ID it must match the authenticated device, otherwise 403.

    Returns:
        tuple: (device, error_response)
          - device: the authenticated device document, or None on failure
          - error_response: a ready Flask response tuple to return, or None
    """
    try:
        claimed_device_id = (request.headers.get('X-Device-ID') or '').strip() or None
        if claimed_device_id and not validate_device_id(claimed_device_id):
            return None, format_response({
                'error': 'Invalid device ID format',
                'code': 'INVALID_DEVICE_ID'
            }, 400)

        # ------------------------------------------------------------------
        # (a) mTLS - reuse the fail-closed gateway-marker helper. It already
        # rejects forged X-Client-* headers, unverified certs, revoked certs,
        # and X-Device-ID values that do not belong to the presented cert.
        # ------------------------------------------------------------------
        mtls_attempted, device, mtls_error = authenticate_mtls_request()
        if mtls_attempted:
            if mtls_error:
                return None, mtls_error
            if device.get('status') != 'active':
                logger.warning(f"Inactive device attempted access: {device.get('device_id')}")
                return None, format_response({
                    'error': 'Device is not active',
                    'code': 'DEVICE_INACTIVE'
                }, 403)
            db = get_db()
            db.devices.update_one(
                {'_id': device['_id']},
                {'$set': {'last_seen': datetime.utcnow()}}
            )
            return device, None

        # ------------------------------------------------------------------
        # (b) Device API key
        # ------------------------------------------------------------------
        api_key = extract_api_key_from_request() or \
            (request.headers.get('X-Device-API-Key') or '').strip()
        if not api_key:
            return None, format_response({
                'error': 'Authentication required',
                'message': 'Provide a device API key (X-API-KEY) or use an mTLS client certificate',
                'code': 'AUTH_REQUIRED'
            }, 401)

        db = get_db()
        if db is None:
            # FAIL CLOSED: no credential store, no authentication.
            logger.error("Device authentication unavailable: database down (fail-closed)")
            return None, format_response({
                'error': 'Authentication unavailable',
                'code': 'AUTH_BACKEND_UNAVAILABLE'
            }, 503)

        device = None
        if api_key.startswith('tesa_dak_'):
            device = validate_device_api_key(db, api_key)
        elif api_key.startswith('tesaiot_dev_'):
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            key_record = db.api_keys.find_one({
                'key_hash': key_hash,
                'key_type': 'device_api_key',
                'status': 'active',
                'expires_at': {'$gt': datetime.utcnow()}
            })
            if key_record and key_record.get('device_id'):
                device = db.devices.find_one({
                    'device_id': key_record['device_id'],
                    'status': 'active'
                })

        if not device:
            logger.warning(
                "Device authentication failed for %s (claimed device: %s)",
                request.path, claimed_device_id or 'none'
            )
            return None, format_response({
                'error': 'Invalid device credentials',
                'code': 'AUTH_FAILED'
            }, 401)

        if device.get('status') != 'active':
            logger.warning(f"Inactive device attempted access: {device.get('device_id')}")
            return None, format_response({
                'error': 'Device is not active',
                'code': 'DEVICE_INACTIVE'
            }, 403)

        # API key is an allowed credential for these auth modes only.
        # Note: mTLS / optiga_trust_mtls devices may use an API key as an
        # emergency fallback (matches prior platform behaviour).
        device_auth_type = device.get('auth_type', 'certificate')
        if device_auth_type not in ['api_key', 'server_tls', 'mtls', 'optiga_trust_mtls']:
            return None, format_response({
                'error': 'Device not configured for API key authentication',
                'code': 'AUTH_TYPE_NOT_ALLOWED'
            }, 403)

        # BIND identity: a claimed X-Device-ID must match the device that the
        # validated credential belongs to. Reject lateral movement.
        resolved_ids = {device.get('device_id'), device.get('trustm_uid')}
        if claimed_device_id and claimed_device_id not in resolved_ids:
            logger.warning(
                "Device identity mismatch: credential belongs to %s but request "
                "claimed X-Device-ID=%s", device.get('device_id'), claimed_device_id
            )
            return None, format_response({
                'error': 'Device identity mismatch',
                'message': 'Authenticated credential does not belong to the claimed device',
                'code': 'DEVICE_ID_MISMATCH'
            }, 403)

        # Bind authenticated device context for downstream handlers.
        g.device_id = device.get('device_id')
        g.device = device
        g.organization_id = device.get('organization_id')
        g.auth_method = 'api_key'

        # Update last seen
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {'last_seen': datetime.utcnow()}}
        )

        return device, None

    except Exception as e:
        logger.error(f"Error in device authentication: {e}")
        # FAIL CLOSED on unexpected errors.
        return None, format_response({
            'error': 'Authentication error',
            'code': 'AUTH_ERROR'
        }, 500)

def parse_request_data():
    """
    Parse request data based on content type.
    Supports JSON and MessagePack formats.
    
    Returns:
        dict: Parsed data
    """
    content_type = request.content_type or 'application/json'
    
    if 'application/json' in content_type:
        return request.get_json()
    elif 'msgpack' in content_type:
        try:
            return msgpack.unpackb(request.data, raw=False)
        except Exception as e:
            logger.error(f"Failed to parse MessagePack data: {e}")
            raise ValidationError("Invalid MessagePack data")
    else:
        raise ValidationError(f"Unsupported content type: {content_type}")

def format_response(data, status_code=200):
    """
    Format response based on Accept header.
    Supports JSON and MessagePack formats.
    
    Args:
        data: Response data
        status_code: HTTP status code
        
    Returns:
        Response object
    """
    accept_header = request.headers.get('Accept', 'application/json')
    
    if 'msgpack' in accept_header:
        return Response(
            msgpack.packb(data, use_bin_type=True),
            status=status_code,
            content_type='application/msgpack'
        )
    else:
        return jsonify(data), status_code

@device_api_bp.route('/devices/<device_id>/telemetry/last', methods=['GET'])
@require_auth
def get_last_telemetry(device_id: str):
    """
    Internal verification endpoint to fetch recent telemetry for a device.
    - First tries Redis cache
    - Falls back to MongoDB if cache miss

    Query params:
      - limit (int, optional, default 1, max 50)

    Returns: { device_id, count, items: [ {timestamp, data, ...} ] }
    """
    try:
        # Clamp limit
        try:
            limit = int(request.args.get('limit', '1'))
        except Exception:
            limit = 1
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50

        # Try cache first (non-fatal on error)
        items = []
        try:
            cached = telemetry_cache_service.get_telemetry_from_cache(device_id, limit)
            if cached:
                items = cached
        except Exception:
            # Cache miss or cache error should not fail the endpoint
            items = []

        # Fallback to DB (non-fatal on error)
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
                # Return empty result instead of error to avoid false negatives during verification
                items = []

        return format_response({
            'device_id': device_id,
            'count': len(items or []),
            'items': items or []
        }, 200)
    except Exception:
        # On unexpected errors, do not leak internals; return empty set for stability
        return format_response({'device_id': device_id, 'count': 0, 'items': []}, 200)

@device_api_bp.route('/telemetry', methods=['POST'])
@validate_request_size(max_size=MAX_TELEMETRY_SIZE)
def submit_telemetry():
    """
    Submit device telemetry data.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type (api_key or certificate)
        
    Request body (JSON or MessagePack):
        {
            "timestamp": "2025-01-24T10:30:00Z",  # Optional, defaults to current time
            "data": {
                "temperature": 25.5,
                "humidity": 60
            },
            "metadata": {  # Optional
                "location": "sensor-1",
                "firmware": "v1.2.3"
            }
        }
        
    Returns:
        200: Telemetry accepted
        400: Invalid request
        401: Authentication failed
        413: Payload too large
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Parse request data
        try:
            data = parse_request_data()
        except ValidationError as e:
            return format_response({
                'error': str(e),
                'code': 'INVALID_DATA'
            }, 400)
        
        if not data or not isinstance(data, dict):
            return format_response({
                'error': 'Invalid telemetry data format',
                'code': 'INVALID_FORMAT'
            }, 400)
        
        # Validate telemetry data
        telemetry_data = data.get('data')
        if not telemetry_data or not isinstance(telemetry_data, dict):
            return format_response({
                'error': 'Telemetry data field is required',
                'code': 'MISSING_DATA'
            }, 400)
        
        # Parse timestamp or use current time
        timestamp_str = data.get('timestamp')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                return format_response({
                    'error': 'Invalid timestamp format. Use ISO format.',
                    'code': 'INVALID_TIMESTAMP'
                }, 400)
        else:
            timestamp = datetime.utcnow()
        
        # Prepare telemetry record
        telemetry_record = {
            'device_id': device['device_id'],
            'timestamp': timestamp,
            'data': telemetry_data,
            'metadata': data.get('metadata', {}),
            'organization_id': device.get('organization_id'),
            'source': 'device_api',
            'auth_type': request.headers.get('X-Auth-Type', 'api_key')
        }
        
        # Store telemetry
        db = get_db()
        result = db.telemetry.insert_one(telemetry_record)
        
        # Log telemetry event
        logger.info(f"Telemetry received from device {device['device_id']}")
        
        # Update device telemetry stats
        db.devices.update_one(
            {'_id': device['_id']},
            {
                '$inc': {'telemetry_count': 1},
                '$set': {'last_telemetry': timestamp}
            }
        )
        
        # Cache latest telemetry in Redis for real-time access
        redis_client = get_redis()
        if redis_client:
            cache_key = f"device:telemetry:latest:{device['device_id']}"
            redis_client.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps({
                    'timestamp': timestamp.isoformat(),
                    'data': telemetry_data
                })
            )
        
        return format_response({
            'success': True,
            'message': 'Telemetry data accepted',
            'telemetry_id': str(result.inserted_id),
            'timestamp': timestamp.isoformat()
        }, 200)
        
    except Exception as e:
        logger.error(f"Error processing telemetry: {e}")
        return format_response({
            'error': 'Failed to process telemetry',
            'code': 'PROCESSING_ERROR'
        }, 500)

@device_api_bp.route('/telemetry/batch', methods=['POST'])
@validate_request_size(max_size=MAX_TELEMETRY_SIZE)
def submit_telemetry_batch():
    """
    Submit batch telemetry data.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type
        
    Request body (JSON or MessagePack):
        {
            "telemetry": [
                {
                    "timestamp": "2025-01-24T10:30:00Z",
                    "data": {"temperature": 25.5}
                },
                {
                    "timestamp": "2025-01-24T10:31:00Z",
                    "data": {"temperature": 25.6}
                }
            ]
        }
        
    Returns:
        200: Batch accepted
        400: Invalid request
        401: Authentication failed
        413: Payload too large
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Parse request data
        try:
            data = parse_request_data()
        except ValidationError as e:
            return format_response({
                'error': str(e),
                'code': 'INVALID_DATA'
            }, 400)
        
        if not data or not isinstance(data, dict):
            return format_response({
                'error': 'Invalid batch data format',
                'code': 'INVALID_FORMAT'
            }, 400)
        
        # Validate batch data
        telemetry_batch = data.get('telemetry')
        if not telemetry_batch or not isinstance(telemetry_batch, list):
            return format_response({
                'error': 'Telemetry array is required',
                'code': 'MISSING_TELEMETRY'
            }, 400)
        
        if len(telemetry_batch) > MAX_BATCH_SIZE:
            return format_response({
                'error': f'Batch size exceeds maximum of {MAX_BATCH_SIZE}',
                'code': 'BATCH_TOO_LARGE'
            }, 400)
        
        # Process batch
        db = get_db()
        records = []
        errors = []
        
        for idx, item in enumerate(telemetry_batch):
            try:
                if not isinstance(item, dict):
                    errors.append({
                        'index': idx,
                        'error': 'Invalid telemetry format'
                    })
                    continue
                
                telemetry_data = item.get('data')
                if not telemetry_data or not isinstance(telemetry_data, dict):
                    errors.append({
                        'index': idx,
                        'error': 'Missing or invalid data field'
                    })
                    continue
                
                # Parse timestamp
                timestamp_str = item.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append({
                            'index': idx,
                            'error': 'Invalid timestamp format'
                        })
                        continue
                else:
                    timestamp = datetime.utcnow()
                
                # Prepare record
                records.append({
                    'device_id': device['device_id'],
                    'timestamp': timestamp,
                    'data': telemetry_data,
                    'metadata': item.get('metadata', {}),
                    'organization_id': device.get('organization_id'),
                    'source': 'device_api_batch',
                    'auth_type': request.headers.get('X-Auth-Type', 'api_key'),
                    'batch_index': idx
                })
                
            except Exception as e:
                logger.error(f"Error processing batch item {idx}: {e}")
                errors.append({
                    'index': idx,
                    'error': 'Processing error'
                })
        
        # Insert valid records
        inserted_count = 0
        if records:
            result = db.telemetry.insert_many(records)
            inserted_count = len(result.inserted_ids)
            
            # Update device stats
            db.devices.update_one(
                {'_id': device['_id']},
                {
                    '$inc': {'telemetry_count': inserted_count},
                    '$set': {'last_telemetry': datetime.utcnow()}
                }
            )
        
        logger.info(f"Batch telemetry received from device {device['device_id']}: "
                   f"{inserted_count} records, {len(errors)} errors")
        
        response_data = {
            'success': True,
            'message': f'Processed {len(telemetry_batch)} telemetry records',
            'accepted': inserted_count,
            'rejected': len(errors)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return format_response(response_data, 200)
        
    except Exception as e:
        logger.error(f"Error processing telemetry batch: {e}")
        return format_response({
            'error': 'Failed to process telemetry batch',
            'code': 'PROCESSING_ERROR'
        }, 500)

@device_api_bp.route('/configuration', methods=['GET'])
def get_device_configuration():
    """
    Get device configuration.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type
        
    Query parameters:
        version: Configuration version (optional)
        
    Returns:
        200: Configuration data
        401: Authentication failed
        404: Configuration not found
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Get configuration version
        version = request.args.get('version')
        
        db = get_db()
        
        # Build query
        query = {
            'device_id': device['device_id'],
            'active': True
        }
        if version:
            query['version'] = version
        
        # Get configuration
        config = db.device_configurations.find_one(
            query,
            sort=[('created_at', -1)]  # Latest first
        )
        
        if not config:
            # Check if device has any configuration
            any_config = db.device_configurations.find_one({'device_id': device['device_id']})
            if not any_config:
                # Return default configuration
                config = {
                    'version': 'default',
                    'telemetry_interval': 60,
                    'features': {
                        'telemetry': True,
                        'commands': False,
                        'ota': False
                    },
                    'settings': {}
                }
            else:
                return format_response({
                    'error': 'Configuration version not found',
                    'code': 'CONFIG_NOT_FOUND'
                }, 404)
        else:
            # Remove internal fields
            config.pop('_id', None)
            config.pop('organization_id', None)
            config.pop('created_by', None)
        
        # Log configuration request
        logger.info(f"Configuration requested by device {device['device_id']}, "
                   f"version: {version or 'latest'}")
        
        # Update device config sync time
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {'last_config_sync': datetime.utcnow()}}
        )
        
        return format_response({
            'success': True,
            'configuration': config,
            'timestamp': datetime.utcnow().isoformat()
        }, 200)
        
    except Exception as e:
        logger.error(f"Error retrieving device configuration: {e}")
        return format_response({
            'error': 'Failed to retrieve configuration',
            'code': 'CONFIG_ERROR'
        }, 500)

@device_api_bp.route('/configuration', methods=['POST'])
def acknowledge_configuration():
    """
    Acknowledge configuration update.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type
        
    Request body:
        {
            "version": "v1.2.3",
            "status": "applied|failed",
            "message": "Optional status message"
        }
        
    Returns:
        200: Acknowledgment received
        400: Invalid request
        401: Authentication failed
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Parse request data
        try:
            data = parse_request_data()
        except ValidationError as e:
            return format_response({
                'error': str(e),
                'code': 'INVALID_DATA'
            }, 400)
        
        if not data or not isinstance(data, dict):
            return format_response({
                'error': 'Invalid acknowledgment data',
                'code': 'INVALID_FORMAT'
            }, 400)
        
        # Validate required fields
        version = data.get('version')
        status = data.get('status')
        
        if not version or not status:
            return format_response({
                'error': 'Version and status are required',
                'code': 'MISSING_FIELDS'
            }, 400)
        
        if status not in ['applied', 'failed']:
            return format_response({
                'error': 'Status must be "applied" or "failed"',
                'code': 'INVALID_STATUS'
            }, 400)
        
        # Record acknowledgment
        db = get_db()
        ack_record = {
            'device_id': device['device_id'],
            'organization_id': device.get('organization_id'),
            'config_version': version,
            'status': status,
            'message': data.get('message', ''),
            'timestamp': datetime.utcnow()
        }
        
        db.device_config_acks.insert_one(ack_record)
        
        # Update device configuration status
        update_data = {
            'config_version': version,
            'config_status': status,
            'config_updated': datetime.utcnow()
        }
        
        if status == 'failed':
            update_data['config_error'] = data.get('message', 'Configuration failed')
        
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': update_data}
        )
        
        logger.info(f"Configuration acknowledgment from device {device['device_id']}: "
                   f"version={version}, status={status}")
        
        return format_response({
            'success': True,
            'message': 'Configuration acknowledgment received',
            'timestamp': datetime.utcnow().isoformat()
        }, 200)
        
    except Exception as e:
        logger.error(f"Error processing configuration acknowledgment: {e}")
        return format_response({
            'error': 'Failed to process acknowledgment',
            'code': 'PROCESSING_ERROR'
        }, 500)

@device_api_bp.route('/heartbeat', methods=['POST'])
def device_heartbeat():
    """
    Device heartbeat endpoint.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type
        
    Request body (optional):
        {
            "uptime": 3600,
            "firmware_version": "v1.2.3",
            "free_memory": 1024,
            "signal_strength": -65
        }
        
    Returns:
        200: Heartbeat acknowledged
        401: Authentication failed
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Parse optional heartbeat data
        heartbeat_data = {}
        try:
            data = parse_request_data()
            if data and isinstance(data, dict):
                heartbeat_data = data
        except:
            # Heartbeat data is optional
            pass
        
        # Update device status
        db = get_db()
        update_data = {
            'last_heartbeat': datetime.utcnow(),
            'online': True
        }
        
        # Add optional heartbeat fields if provided
        if heartbeat_data.get('firmware_version'):
            update_data['firmware_version'] = sanitize_string(heartbeat_data['firmware_version'], 50)
        if heartbeat_data.get('uptime'):
            update_data['uptime'] = int(heartbeat_data.get('uptime', 0))
        if heartbeat_data.get('free_memory'):
            update_data['free_memory'] = int(heartbeat_data.get('free_memory', 0))
        if heartbeat_data.get('signal_strength'):
            update_data['signal_strength'] = int(heartbeat_data.get('signal_strength', 0))
        
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': update_data}
        )
        
        # Log heartbeat
        logger.debug(f"Heartbeat from device {device['device_id']}")
        
        # Check if device needs configuration update
        needs_config_update = False
        latest_config = db.device_configurations.find_one(
            {'device_id': device['device_id'], 'active': True},
            sort=[('created_at', -1)]
        )
        
        if latest_config:
            current_version = device.get('config_version')
            if current_version != latest_config.get('version'):
                needs_config_update = True
        
        return format_response({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'needs_config_update': needs_config_update
        }, 200)
        
    except Exception as e:
        logger.error(f"Error processing heartbeat: {e}")
        return format_response({
            'error': 'Failed to process heartbeat',
            'code': 'PROCESSING_ERROR'
        }, 500)

@device_api_bp.route('/command/response', methods=['POST'])
@validate_request_size(max_size=1024 * 1024)  # 1MB limit
def submit_command_response():
    """
    Submit response to a command.
    
    Expects APISIX headers:
        X-Device-ID: Device identifier
        X-Auth-Type: Authentication type
        
    Request body:
        {
            "command_id": "cmd_123",
            "status": "completed|failed|timeout",
            "response": {
                "result": "Command executed successfully",
                "data": {}
            },
            "error": "Optional error message"
        }
        
    Returns:
        200: Response recorded
        400: Invalid request
        401: Authentication failed
        404: Command not found
        500: Server error
    """
    try:
        # Verify device authentication (credential-based, identity-binding)
        device, auth_error = verify_device_auth()
        if auth_error:
            return auth_error
        
        # Parse request data
        try:
            data = parse_request_data()
        except ValidationError as e:
            return format_response({
                'error': str(e),
                'code': 'INVALID_DATA'
            }, 400)
        
        if not data or not isinstance(data, dict):
            return format_response({
                'error': 'Invalid response data',
                'code': 'INVALID_FORMAT'
            }, 400)
        
        # Validate required fields
        command_id = data.get('command_id')
        status = data.get('status')
        
        if not command_id or not status:
            return format_response({
                'error': 'Command ID and status are required',
                'code': 'MISSING_FIELDS'
            }, 400)
        
        if status not in ['completed', 'failed', 'timeout']:
            return format_response({
                'error': 'Invalid status. Must be: completed, failed, or timeout',
                'code': 'INVALID_STATUS'
            }, 400)
        
        # Verify command exists and belongs to device
        db = get_db()
        command = db.device_commands.find_one({
            '_id': ObjectId(command_id) if ObjectId.is_valid(command_id) else None,
            'device_id': device['device_id']
        })
        
        if not command:
            return format_response({
                'error': 'Command not found',
                'code': 'COMMAND_NOT_FOUND'
            }, 404)
        
        # Update command with response
        update_data = {
            'status': status,
            'completed_at': datetime.utcnow(),
            'response': data.get('response', {}),
            'response_received': True
        }
        
        if status == 'failed':
            update_data['error'] = data.get('error', 'Command failed')
        
        db.device_commands.update_one(
            {'_id': command['_id']},
            {'$set': update_data}
        )
        
        logger.info(f"Command response from device {device['device_id']}: "
                   f"command_id={command_id}, status={status}")
        
        return format_response({
            'success': True,
            'message': 'Command response recorded',
            'timestamp': datetime.utcnow().isoformat()
        }, 200)
        
    except Exception as e:
        logger.error(f"Error processing command response: {e}")
        return format_response({
            'error': 'Failed to process command response',
            'code': 'PROCESSING_ERROR'
        }, 500)

# Health check endpoint for device API
@device_api_bp.route('/health', methods=['GET'])
def device_api_health():
    """
    Health check endpoint for device API.
    
    Returns:
        200: Service healthy
    """
    return jsonify({
        'status': 'healthy',
        'service': 'device_api',
        'timestamp': datetime.utcnow().isoformat(),
        'supported_content_types': SUPPORTED_CONTENT_TYPES
    }), 200
