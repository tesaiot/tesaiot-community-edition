# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Telemetry Controller
Copyright (C) 2024-2025 Thai Embedded Systems Association (TESA)

Telemetry data ingestion with dual storage and WebSocket broadcasting.
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from ..core.database import get_db, get_postgres, get_redis
from ..core.auth import require_api_key, require_api_key_or_mtls, require_auth, require_telemetry_ingest
from ..utils.validation import (
    validate_device_id, sanitize_string, validate_request_size
)

# Protected Update (OTA) is out of scope for the Community Edition.
logger = logging.getLogger(__name__)
telemetry_bp = Blueprint('telemetry', __name__)

def broadcast_telemetry_websocket(device_id, timestamp, data, metadata, organization_id=None, source='api'):
    # Real-time WebSocket fan-out (the WebSocket-B2B service) is out of scope for
    # the Community Edition. Telemetry is persisted to MongoDB/TimescaleDB and is
    # available via the unified telemetry REST endpoints used by the dashboard.
    # This is intentionally a no-op so ingestion stays unaffected.
    return

MAX_TELEMETRY_SIZE = 10 * 1024 * 1024
MAX_BATCH_SIZE = 1000

def convert_device_telemetry_format(device_data):
    try:
        device_id = device_data.get('device_id', 'c5a22a8f-7d4e-4ca4-a604-9a26ece2d131')
        timestamp = device_data.get('timestamp')
        telemetry_data = {}
        metadata = {
            'sensor_type': 'BMI270',
            'device_type': 'https-mtls-device',
            'manufacturer': 'TESA IoT Platform'
        }
        
        if 'accel' in device_data and isinstance(device_data['accel'], dict):
            accel = device_data['accel']
            telemetry_data['accel_x'] = float(accel.get('x', 0.0))
            telemetry_data['accel_y'] = float(accel.get('y', 0.0))
            telemetry_data['accel_z'] = float(accel.get('z', 0.0))
            metadata['units'] = metadata.get('units', {})
            metadata['units'].update({
                'accel_x': 'g',
                'accel_y': 'g', 
                'accel_z': 'g'
            })
        
        if 'gyro' in device_data and isinstance(device_data['gyro'], dict):
            gyro = device_data['gyro']
            telemetry_data['gyro_x'] = float(gyro.get('x', 0.0))
            telemetry_data['gyro_y'] = float(gyro.get('y', 0.0))
            telemetry_data['gyro_z'] = float(gyro.get('z', 0.0))
            metadata['units'] = metadata.get('units', {})
            metadata['units'].update({
                'gyro_x': 'dps',
                'gyro_y': 'dps',
                'gyro_z': 'dps'
            })
        
        if 'step_count' in device_data:
            telemetry_data['step_count'] = int(device_data['step_count'])
            metadata['units'] = metadata.get('units', {})
            metadata['units']['step_count'] = 'steps'
        
        if 'activity' in device_data:
            telemetry_data['activity'] = str(device_data['activity'])
            
        if 'sensor_status_ok' in device_data:
            telemetry_data['sensor_status'] = 'ok' if device_data['sensor_status_ok'] else 'warning'
            
        if 'sample_count' in device_data:
            telemetry_data['sample_count'] = int(device_data['sample_count'])
        standard_format = {
            'device_id': device_id,
            'timestamp': timestamp,
            'data': telemetry_data,
            'metadata': metadata
        }
        
        return standard_format
        
    except Exception as e:
        logger.error(f"Error converting device telemetry format: {e}")
        return device_data

def validate_telemetry_data(data):
    try:
        if not isinstance(data, dict):
            return False, "Invalid data format - must be JSON object", None
        
        device_id = data.get('device_id')
        if not device_id:
            return False, "device_id is required", None
        
        if not validate_device_id(device_id):
            return False, "Invalid device_id format", None
        
        telemetry_data = data.get('data')
        if not telemetry_data or not isinstance(telemetry_data, dict):
            return False, "data field is required and must be an object", None
        
        timestamp_str = data.get('timestamp')
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                # Ensure timezone-aware (treat naive as UTC)
                if timestamp.tzinfo is None:
                    from datetime import timezone as _tz
                    timestamp = timestamp.replace(tzinfo=_tz.utc)
            except ValueError:
                return False, "Invalid timestamp format - use ISO 8601", None
        else:
            from datetime import timezone as _tz
            timestamp = datetime.utcnow().replace(tzinfo=_tz.utc)
        
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            return False, "metadata must be an object if provided", None
        validated_data = {
            'device_id': sanitize_string(device_id, 50),
            'timestamp': timestamp,
            'data': telemetry_data,
            'metadata': metadata
        }
        
        return True, None, validated_data
        
    except Exception as e:
        logger.error(f"Error validating telemetry data: {e}")
        return False, f"Validation error: {str(e)}", None

def store_mongodb_telemetry(device_id, timestamp, data, metadata, organization_id=None):
    try:
        db = get_db()
        telemetry_doc = {
            'device_id': device_id,
            'timestamp': timestamp,
            'data': data,
            'metadata': metadata,
            'organization_id': organization_id,
            'source': 'api_v1_telemetry',
            'created_at': datetime.utcnow()
        }
        
        result = db.telemetry.insert_one(telemetry_doc)
        
        logger.debug(f"Stored telemetry in MongoDB: {result.inserted_id}")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error storing telemetry in MongoDB: {e}")
        raise

def flatten_telemetry_data(data):
    flattened = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat_key = f"{key}_{sub_key}"
                flattened[flat_key] = sub_value
        else:
            flattened[key] = value
    
    return flattened


_PROTECTED_UPDATE_STATUS_MAP = {
    'ok': 'applied',
    'success': 'applied',
    'applied': 'applied',
    'completed': 'applied',
    'done': 'applied',
    'ack': 'acknowledged',
    'acknowledged': 'acknowledged',
    'received': 'acknowledged',
    'pending': 'acknowledged',
    'fail': 'failed',
    'failed': 'failed',
    'error': 'failed',
    'rejected': 'failed',
}


def _normalise_protected_update_status(value: str) -> str:
    lowered = (value or '').strip().lower()
    return _PROTECTED_UPDATE_STATUS_MAP.get(lowered, lowered or 'unknown')


def _extract_protected_update_feedback(payload: dict, metadata: dict):
    candidate = {}
    if isinstance(payload.get('protected_update'), dict):
        candidate = payload['protected_update']
    elif isinstance(metadata.get('protected_update'), dict):
        candidate = metadata['protected_update']

    status = (
        candidate.get('status')
        or payload.get('protected_update_status')
        or metadata.get('protected_update_status')
    )
    if not status:
        return None

    job_id = (
        candidate.get('job_id')
        or payload.get('protected_update_job_id')
        or metadata.get('protected_update_job_id')
    )
    correlation_id = (
        candidate.get('correlation_id')
        or metadata.get('protected_update_correlation_id')
    )
    version = (
        candidate.get('version')
        or payload.get('protected_update_version')
        or metadata.get('protected_update_version')
    )
    try:
        version = int(version) if version is not None else None
    except (TypeError, ValueError):
        version = None

    details = (
        candidate.get('detail')
        or candidate.get('error')
        or payload.get('protected_update_error')
        or metadata.get('protected_update_error')
    )

    return {
        'status': _normalise_protected_update_status(status),
        'job_id': job_id,
        'payload_version': version,
        'details': details,
        'correlation_id': correlation_id,
    }


def _handle_protected_update_feedback(device_id: str, payload: dict, metadata: dict, timestamp: datetime) -> None:
    # Protected Update (OTA) feedback handling is out of scope for the CE
    # distribution. Telemetry ingestion continues unaffected.
    return


def store_telemetry_timeseries(device_id, timestamp, data, metadata, organization_id=None):
    """Write a telemetry sample to TimescaleDB (secondary time-series store).

    Returns:
        bool: True if the sample was committed to TimescaleDB, False if the
              write failed or the time-series store was unavailable.

    This NEVER raises: TimescaleDB is a secondary analytics store and a failure
    here must not crash an ingest request whose primary (MongoDB) write already
    succeeded. But the failure is logged at ERROR level and reflected in the
    returned bool so callers can surface it to the client instead of falsely
    claiming the time-series write succeeded.
    """
    try:
        from ..services.telemetry_timescale_integration import get_telemetry_timescale_integration
        integration = get_telemetry_timescale_integration()
        if integration and integration.enabled:
            stored = bool(
                integration.store_telemetry(device_id, timestamp, data, metadata, organization_id)
            )
            if not stored:
                logger.error(
                    f"TimescaleDB time-series write FAILED for device {device_id} "
                    f"(primary store already succeeded); sample is NOT available for "
                    f"time-series analytics."
                )
            return stored
        # Integration disabled/unavailable -> fall back to the legacy direct writer.
        return store_timescaledb_metrics(device_id, timestamp, data, metadata, organization_id)
    except Exception as e:
        logger.error(
            f"TimescaleDB time-series write raised for device {device_id} "
            f"(primary store already succeeded): {e}",
            exc_info=True,
        )
        return False


def store_timescaledb_metrics(device_id, timestamp, data, metadata, organization_id=None):
    """Legacy direct writer to the device_telemetry table.

    Returns True only if the metrics were committed, False otherwise. Errors are
    logged at ERROR level and never re-raised (secondary store).
    """
    flattened_data = flatten_telemetry_data(data)
    logger.info(f"Attempting to store telemetry in TimescaleDB for device {device_id}, flattened data: {flattened_data}")
    try:
        postgres_conn = get_postgres()
        if not postgres_conn:
            logger.warning("TimescaleDB not available, skipping time-series storage")
            return False

        with postgres_conn.cursor() as cursor:
                if not organization_id:
                    organization_id = metadata.get('organization_id', 'default') if isinstance(metadata, dict) else 'default'

                for metric_name, metric_value in flattened_data.items():
                    if isinstance(metric_value, (int, float)):
                        unit = None
                        if isinstance(metadata, dict):
                            units = metadata.get('units', {})
                            unit = units.get(metric_name)
                        cursor.execute("""
                            INSERT INTO device_telemetry 
                            (time, device_id, organization_id, metric_name, metric_value, unit, metadata)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING;
                        """, (timestamp, device_id, organization_id, metric_name, metric_value, unit, json.dumps(metadata)))
                
                postgres_conn.commit()
                logger.info(f"Successfully stored telemetry in device_telemetry table for device {device_id} - {len([k for k,v in data.items() if isinstance(v, (int, float))])} metrics")
        return True

    except Exception as e:
        logger.error(f"Error storing metrics in TimescaleDB: {e}", exc_info=True)
        return False

def cache_latest_telemetry(device_id, timestamp, data):
    try:
        redis_client = get_redis()
        if not redis_client:
            return
        
        cache_key = f"device:telemetry:latest:{device_id}"
        cache_data = {
            'timestamp': timestamp.isoformat(),
            'data': data
        }
        
        redis_client.setex(cache_key, 3600, json.dumps(cache_data))
        
        logger.debug(f"Cached latest telemetry for device {device_id}")
        
    except Exception as e:
        logger.error(f"Error caching telemetry: {e}")

@telemetry_bp.route('/api/v1/telemetry', methods=['POST'])
@require_telemetry_ingest
@validate_request_size(max_size=MAX_TELEMETRY_SIZE)
def submit_telemetry():
    try:
        # Parse and validate request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'error': 'Invalid JSON data',
                'code': 'INVALID_JSON'
            }), 400
        
        is_valid, error_msg, validated_data = validate_telemetry_data(request_data)
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'code': 'VALIDATION_ERROR'
            }), 400
        
        device_id = validated_data['device_id']
        timestamp = validated_data['timestamp']
        data = validated_data['data']
        metadata = validated_data['metadata']

        # SECURITY: when the credential is bound to a device (device API key or
        # mTLS cert sets g.device_id), the body device_id MUST match it. A
        # device must not be able to write telemetry under another identity.
        authenticated_device_id = getattr(g, 'device_id', None)
        if authenticated_device_id and device_id != authenticated_device_id:
            logger.warning(
                "Telemetry device_id mismatch: credential belongs to %s but body "
                "claims %s", authenticated_device_id, device_id
            )
            return jsonify({
                'error': 'Device identity mismatch',
                'message': 'Authenticated device credential does not match the telemetry device_id',
                'code': 'DEVICE_ID_MISMATCH'
            }), 403

        # Get device info for organization context
        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        organization_id = device.get('organization_id') if device else None

        # Store in MongoDB (primary storage)
        telemetry_id = store_mongodb_telemetry(
            device_id, timestamp, data, metadata, organization_id
        )
        
        # Store metrics in TimescaleDB (secondary time-series analytics store).
        # MongoDB above is the primary store and already succeeded. The helper
        # never raises, but returns False on failure so we can honestly report
        # the time-series outcome instead of silently claiming success.
        timescale_stored = store_telemetry_timeseries(
            device_id, timestamp, data, metadata, organization_id
        )

        # Cache latest data in Redis (real-time access)
        cache_latest_telemetry(device_id, timestamp, data)
        
        # Broadcast via WebSocket to subscribed clients
        # Flatten data for proper display in dashboard
        flattened_broadcast_data = flatten_telemetry_data(data)
        broadcast_telemetry_websocket(device_id, timestamp, flattened_broadcast_data, metadata, organization_id, 'api')
        
        # Update device last seen if exists
        if device:
            db.devices.update_one(
                {'_id': device['_id']},
                {
                    '$set': {
                        'last_seen': timestamp,
                        'last_telemetry': timestamp
                    },
                    '$inc': {'telemetry_count': 1}
                }
            )
        
        # Identify which metrics were stored in TimescaleDB
        # Flatten nested data to properly count all numeric metrics
        flattened_for_metrics = flatten_telemetry_data(data)
        metrics_stored = [
            key for key, value in flattened_for_metrics.items() 
            if isinstance(value, (int, float))
        ]
        
        # Enhanced logging for certificate validation
        auth_method = getattr(g, 'auth_method', 'api_key')
        cert_validation = getattr(g, 'cert_validation', None)
        
        if auth_method == 'mtls' and cert_validation:
            cert_info = cert_validation.get('certificate_info', {})
            logger.info(f"Telemetry stored successfully for device {device_id}: "
                       f"MongoDB ID {telemetry_id}, {len(metrics_stored)} metrics, "
                       f"auth: mTLS (cert: {cert_info.get('common_name', 'N/A')}, "
                       f"serial: {cert_info.get('serial_number', 'N/A')})")
        else:
            logger.info(f"Telemetry stored successfully for device {device_id}: "
                       f"MongoDB ID {telemetry_id}, {len(metrics_stored)} metrics, auth: {auth_method}")
        
        # Report storage outcome honestly: MongoDB (primary) succeeded, but the
        # TimescaleDB time-series write may have failed. Do not claim time-series
        # storage succeeded when it did not.
        response_body = {
            'success': True,
            'message': 'Telemetry data stored successfully',
            'telemetry_id': telemetry_id,
            'device_id': device_id,
            'timestamp': timestamp.isoformat(),
            'metrics_stored': metrics_stored,
            'storage': {
                'primary': 'mongodb',
                'mongodb_stored': True,
                'timeseries_stored': bool(timescale_stored),
            },
        }
        if not timescale_stored:
            response_body['message'] = (
                'Telemetry data stored in primary store; time-series (TimescaleDB) '
                'write failed and was not persisted.'
            )
            response_body['warnings'] = ['timeseries_write_failed']
        return jsonify(response_body), 200
        
    except Exception as e:
        logger.error(f"Error processing telemetry submission: {e}")
        return jsonify({
            'error': 'Failed to process telemetry data',
            'code': 'PROCESSING_ERROR'
        }), 500

@telemetry_bp.route('/api/v1/telemetry/batch', methods=['POST'])
@require_api_key
@validate_request_size(max_size=MAX_TELEMETRY_SIZE)
def submit_telemetry_batch():
    """
    Submit batch telemetry data endpoint.
    
    Request body:
        {
            "telemetry": [
                {
                    "device_id": "device_123",
                    "timestamp": "2025-01-24T10:30:00Z",
                    "data": {"temperature": 25.5},
                    "metadata": {}
                },
                {
                    "device_id": "device_456",
                    "timestamp": "2025-01-24T10:31:00Z",
                    "data": {"temperature": 26.0},
                    "metadata": {}
                }
            ]
        }
        
    Returns:
        200: Batch processing results
        400: Invalid request data
        401: Authentication failed
        413: Payload too large
        500: Server error
    """
    try:
        request_data = request.get_json()
        if not request_data or not isinstance(request_data, dict):
            return jsonify({
                'error': 'Invalid JSON data',
                'code': 'INVALID_JSON'
            }), 400
        
        telemetry_batch = request_data.get('telemetry')
        if not telemetry_batch or not isinstance(telemetry_batch, list):
            return jsonify({
                'error': 'telemetry array is required',
                'code': 'MISSING_TELEMETRY_ARRAY'
            }), 400
        
        if len(telemetry_batch) > MAX_BATCH_SIZE:
            return jsonify({
                'error': f'Batch size exceeds maximum of {MAX_BATCH_SIZE}',
                'code': 'BATCH_TOO_LARGE'
            }), 400

        # SECURITY: device-bound credentials may only ingest for their own
        # device. Reject the whole batch if any item claims another identity.
        authenticated_device_id = getattr(g, 'device_id', None)
        if authenticated_device_id:
            for idx, item in enumerate(telemetry_batch):
                item_device_id = item.get('device_id') if isinstance(item, dict) else None
                if item_device_id != authenticated_device_id:
                    logger.warning(
                        "Batch telemetry device_id mismatch at index %s: credential "
                        "belongs to %s but item claims %s",
                        idx, authenticated_device_id, item_device_id
                    )
                    return jsonify({
                        'error': 'Device identity mismatch',
                        'message': 'Authenticated device credential does not match a batch item device_id',
                        'code': 'DEVICE_ID_MISMATCH',
                        'index': idx
                    }), 403

        # Process each telemetry record
        results = {
            'total': len(telemetry_batch),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'telemetry_ids': []
        }
        
        for idx, item in enumerate(telemetry_batch):
            try:
                # Validate individual record
                is_valid, error_msg, validated_data = validate_telemetry_data(item)
                if not is_valid:
                    results['failed'] += 1
                    results['errors'].append({
                        'index': idx,
                        'error': error_msg
                    })
                    continue
                
                device_id = validated_data['device_id']
                timestamp = validated_data['timestamp']
                data = validated_data['data']
                metadata = validated_data['metadata']
                
                # Get device info
                db = get_db()
                device = db.devices.find_one({'device_id': device_id})
                organization_id = device.get('organization_id') if device else None
                
                # Store data
                telemetry_id = store_mongodb_telemetry(
                    device_id, timestamp, data, metadata, organization_id
                )
                
                # Store in TimescaleDB (secondary time-series store). Helper never
                # raises and returns False on failure (logged at ERROR inside).
                timescale_stored = store_telemetry_timeseries(
                    device_id, timestamp, data, metadata, organization_id
                )

                cache_latest_telemetry(device_id, timestamp, data)
                
                # Update device if exists
                if device:
                    db.devices.update_one(
                        {'_id': device['_id']},
                        {
                            '$set': {
                                'last_seen': timestamp,
                                'last_telemetry': timestamp
                            },
                            '$inc': {'telemetry_count': 1}
                        }
                    )
                
                results['successful'] += 1
                results['telemetry_ids'].append({
                    'index': idx,
                    'device_id': device_id,
                    'telemetry_id': telemetry_id,
                    # Honest per-item time-series outcome; primary (MongoDB) is stored.
                    'timeseries_stored': bool(timescale_stored)
                })
                if not timescale_stored:
                    results.setdefault('warnings', []).append({
                        'index': idx,
                        'device_id': device_id,
                        'warning': 'timeseries_write_failed'
                    })
                
            except Exception as e:
                logger.error(f"Error processing batch item {idx}: {e}")
                results['failed'] += 1
                results['errors'].append({
                    'index': idx,
                    'error': f'Processing error: {str(e)}'
                })
        
        logger.info(f"Batch telemetry processed: {results['successful']} successful, "
                   f"{results['failed']} failed out of {results['total']} records")
        
        return jsonify({
            'success': True,
            'message': f"Processed {results['total']} telemetry records",
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing telemetry batch: {e}")
        return jsonify({
            'error': 'Failed to process telemetry batch',
            'code': 'PROCESSING_ERROR'
        }), 500

@telemetry_bp.route('/api/v1/devices/telemetry', methods=['POST'])
@require_telemetry_ingest  # device API key / mTLS, or a trusted service relay (JWT + TELEMETRY_INGEST)
@validate_request_size(max_size=MAX_TELEMETRY_SIZE)
def submit_device_telemetry():
    """
    Submit device telemetry data endpoint with mTLS support.
    
    This endpoint specifically supports mTLS authentication for embedded devices
    like Device04. It accepts the same telemetry data format as the main telemetry
    endpoint but is designed for direct device communication with client certificates.
    
    Authentication:
        - mTLS client certificate (forwarded from NGINX)
        - API key (X-API-KEY header) as fallback
    
    Request body:
        {
            "device_id": "c5a22a8f-7d4e-4ca4-a604-9a26ece2d131",
            "timestamp": "2025-08-24T10:30:00.000Z",
            "accel": {
                "x": 0.123,
                "y": -0.456,
                "z": 9.810
            },
            "gyro": {
                "x": 12.34,
                "y": -56.78,
                "z": 90.12
            },
            "step_count": 1234,
            "activity": "walking"
        }
        
    Returns:
        200: {
            "success": true,
            "message": "Device telemetry stored successfully",
            "telemetry_id": "mongodb_document_id",
            "device_id": "c5a22a8f-7d4e-4ca4-a604-9a26ece2d131",
            "timestamp": "2025-08-24T10:30:00.123456Z",
            "auth_method": "mtls|api_key"
        }
        400: Invalid request data
        401: Authentication failed
        413: Payload too large
        500: Server error
    """
    try:
        # Parse and validate request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'error': 'Invalid JSON data',
                'code': 'INVALID_JSON'
            }), 400
        
        # Device04 sends data in BMI270 format, convert to standard telemetry format
        device_telemetry_data = convert_device_telemetry_format(request_data)
        
        is_valid, error_msg, validated_data = validate_telemetry_data(device_telemetry_data)
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'code': 'VALIDATION_ERROR'
            }), 400
        
        device_id = validated_data['device_id']
        timestamp = validated_data['timestamp']
        data = validated_data['data']
        metadata = validated_data['metadata']

        # SECURITY: when the credential is bound to a device (device API key or
        # mTLS cert sets g.device_id), the body device_id MUST match it. A
        # device must not be able to write telemetry under another identity.
        authenticated_device_id = getattr(g, 'device_id', None)
        if authenticated_device_id and device_id != authenticated_device_id:
            logger.warning(
                "Telemetry device_id mismatch: credential belongs to %s but body "
                "claims %s", authenticated_device_id, device_id
            )
            return jsonify({
                'error': 'Device identity mismatch',
                'message': 'Authenticated device credential does not match the telemetry device_id',
                'code': 'DEVICE_ID_MISMATCH'
            }), 403

        # Get device info for organization context
        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        organization_id = device.get('organization_id') if device else None

        # Store in MongoDB (primary storage)
        telemetry_id = store_mongodb_telemetry(
            device_id, timestamp, data, metadata, organization_id
        )
        
        # Store metrics in TimescaleDB (secondary time-series analytics store).
        # MongoDB above is the primary store and already succeeded. The helper
        # never raises, but returns False on failure so we can honestly report
        # the time-series outcome instead of silently claiming success.
        timescale_stored = store_telemetry_timeseries(
            device_id, timestamp, data, metadata, organization_id
        )

        # Cache latest data in Redis (real-time access)
        cache_latest_telemetry(device_id, timestamp, data)
        
        # Broadcast via WebSocket to subscribed clients
        # Flatten data for proper display in dashboard
        flattened_broadcast_data = flatten_telemetry_data(data)
        broadcast_telemetry_websocket(device_id, timestamp, flattened_broadcast_data, metadata, organization_id, 'api')
        
        # Update device last seen if exists
        if device:
            db.devices.update_one(
                {'_id': device['_id']},
                {
                    '$set': {
                        'last_seen': timestamp,
                        'last_telemetry': timestamp
                    },
                    '$inc': {'telemetry_count': 1}
                }
            )
        
        # Identify which metrics were stored in TimescaleDB
        # Flatten nested data to properly count all numeric metrics
        flattened_for_metrics = flatten_telemetry_data(data)
        metrics_stored = [
            key for key, value in flattened_for_metrics.items() 
            if isinstance(value, (int, float))
        ]
        
        # Enhanced logging for certificate validation
        auth_method = getattr(g, 'auth_method', 'api_key')
        cert_validation = getattr(g, 'cert_validation', None)
        
        if auth_method == 'mtls' and cert_validation:
            cert_info = cert_validation.get('certificate_info', {})
            validation_details = cert_validation.get('validation_details', {})
            logger.info(f"Device telemetry stored successfully for device {device_id}: "
                       f"MongoDB ID {telemetry_id}, {len(metrics_stored)} metrics, "
                       f"auth: mTLS (cert: {cert_info.get('common_name', 'N/A')}, "
                       f"serial: {cert_info.get('serial_number', 'N/A')}, "
                       f"vault_validated: {validation_details.get('ca_available', False)})")
        else:
            logger.info(f"Device telemetry stored successfully for device {device_id}: "
                       f"MongoDB ID {telemetry_id}, {len(metrics_stored)} metrics, auth: {auth_method}")
        
        response_body = {
            'success': True,
            'message': 'Device telemetry stored successfully',
            'telemetry_id': telemetry_id,
            'device_id': device_id,
            'timestamp': timestamp.isoformat(),
            'metrics_stored': metrics_stored,
            'auth_method': auth_method,
            'storage': {
                'primary': 'mongodb',
                'mongodb_stored': True,
                'timeseries_stored': bool(timescale_stored),
            },
        }
        if not timescale_stored:
            response_body['message'] = (
                'Device telemetry stored in primary store; time-series (TimescaleDB) '
                'write failed and was not persisted.'
            )
            response_body['warnings'] = ['timeseries_write_failed']
        return jsonify(response_body), 200
        
    except Exception as e:
        logger.error(f"Error processing device telemetry submission: {e}")
        return jsonify({
            'error': 'Failed to process device telemetry data',
            'code': 'PROCESSING_ERROR'
        }), 500

@telemetry_bp.route('/api/v1/telemetry/bridge', methods=['POST'])
@require_auth
def submit_telemetry_bridge():
    """
    Submit telemetry data from MQTT Bridge (JWT authenticated).
    
    This endpoint is specifically for the MQTT Bridge service to forward telemetry
    data from MQTT devices. It accepts JWT authentication from the bridge service user.
    
    Request body: Same as /api/v1/telemetry endpoint
    
    Returns:
        200: Success with telemetry_id
        400: Invalid request data
        401: Authentication failed
        500: Server error
    """
    try:
        # Parse and validate request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({
                'error': 'Invalid JSON data',
                'code': 'INVALID_JSON'
            }), 400
        
        # Bridge already sends data in standard format, no conversion needed
        is_valid, error_msg, validated_data = validate_telemetry_data(request_data)
        
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'code': 'VALIDATION_ERROR'
            }), 400
        
        device_id = validated_data['device_id']
        timestamp = validated_data['timestamp']
        data = validated_data['data']
        metadata = validated_data['metadata']
        
        # Add bridge info to metadata
        metadata['forwarded_by'] = 'mqtt_bridge'
        metadata['auth_method'] = 'jwt'
        
        # Get device info for organization context
        db = get_db()
        device = db.devices.find_one({'device_id': device_id})
        organization_id = device.get('organization_id') if device else None
        
        # Store in MongoDB (primary storage)
        telemetry_id = store_mongodb_telemetry(
            device_id, timestamp, data, metadata, organization_id
        )
        
        # Store in TimescaleDB (secondary time-series store). Failure is logged at
        # ERROR level inside the helper and reflected in the bool below; it does
        # not crash the request because MongoDB (primary) already persisted it.
        timescale_stored = store_telemetry_timeseries(
            device_id, timestamp, data, metadata, organization_id
        )

        # Cache latest data in Redis for fast read path
        try:
            cache_latest_telemetry(device_id, timestamp, data)
        except Exception as e:
            logger.debug(f"Cache latest telemetry failed for {device_id}: {e}")

        # Broadcast via WebSocket to subscribed clients (unify behavior with /api/v1/telemetry)
        try:
            flattened_broadcast_data = flatten_telemetry_data(data)
            broadcast_telemetry_websocket(device_id, timestamp, flattened_broadcast_data, metadata, organization_id, 'bridge')
        except Exception as e:
            logger.debug(f"WebSocket broadcast failed for {device_id}: {e}")

        # Update device last seen timestamp
        if device:
            db.devices.update_one(
                {'_id': device['_id']},
                {
                    '$set': {
                        'last_seen': timestamp,
                        'last_telemetry': timestamp
                    },
                    '$inc': {'telemetry_count': 1}
                }
            )
            logger.debug(f"Updated last_seen for device {device_id} to {timestamp}")

        try:
            _handle_protected_update_feedback(device_id, data, metadata, timestamp)
        except Exception as feedback_exc:  # pragma: no cover - defensive logging
            logger.debug(f"Protected update feedback handler error for {device_id}: {feedback_exc}")

        logger.info(f"Device telemetry stored successfully (bridge) for device {device_id}: MongoDB ID {telemetry_id}")

        response_body = {
            'success': True,
            'message': 'Telemetry data stored successfully',
            'telemetry_id': str(telemetry_id),
            'device_id': device_id,
            'timestamp': timestamp,
            'auth_method': 'jwt_bridge',
            'storage': {
                'primary': 'mongodb',
                'mongodb_stored': True,
                'timeseries_stored': bool(timescale_stored),
            },
        }
        if not timescale_stored:
            response_body['message'] = (
                'Telemetry data stored in primary store; time-series (TimescaleDB) '
                'write failed and was not persisted.'
            )
            response_body['warnings'] = ['timeseries_write_failed']
        return jsonify(response_body), 200
        
    except Exception as e:
        logger.error(f"Error processing bridge telemetry submission: {e}")
        return jsonify({
            'error': 'Failed to process telemetry data',
            'code': 'PROCESSING_ERROR'
        }), 500

@telemetry_bp.route('/api/v1/devices/mtls/test', methods=['GET', 'POST'])
@require_api_key_or_mtls
def test_mtls_authentication():
    """
    Test endpoint for mTLS authentication verification.
    
    This endpoint helps Device04 and other mTLS clients verify that their
    client certificate authentication is working correctly.
    
    Returns:
        200: {
            "success": true,
            "message": "mTLS authentication test successful",
            "auth_method": "mtls|api_key",
            "client_info": {
                "cert_present": true|false,
                "cert_verified": "SUCCESS"|"NONE"|"FAILED",
                "cert_subject": "...",
                "cert_issuer": "...",
                "cert_serial": "...",
                "cert_fingerprint": "..."
            },
            "request_headers": {...}
        }
    """
    try:
        # Determine authentication method used
        auth_method = getattr(g, 'auth_method', 'api_key')
        client_cert = getattr(g, 'client_cert', None)
        
        # Extract client certificate information from NGINX forwarded headers
        cert_info = {
            'cert_present': request.headers.get('X-Client-Cert') is not None,
            'cert_verified': request.headers.get('X-Client-Verify', 'NONE'),
            'cert_subject': request.headers.get('X-Client-S-DN', ''),
            'cert_issuer': request.headers.get('X-Client-I-DN', ''),
            'cert_serial': request.headers.get('X-Client-Serial', ''),
            'cert_fingerprint': request.headers.get('X-Client-Fingerprint', '')
        }
        
        # Include relevant request headers for debugging
        relevant_headers = {}
        for header in request.headers:
            if header.startswith(('X-Client-', 'X-API-', 'X-Real-IP', 'X-Forwarded-')):
                relevant_headers[header] = request.headers.get(header)
        
        logger.info(f"mTLS test endpoint accessed via {auth_method}, "
                   f"cert_present: {cert_info['cert_present']}, "
                   f"cert_verified: {cert_info['cert_verified']}")
        
        return jsonify({
            'success': True,
            'message': 'mTLS authentication test successful',
            'auth_method': auth_method,
            'client_info': cert_info,
            'request_headers': relevant_headers,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in mTLS test endpoint: {e}")
        return jsonify({
            'error': 'mTLS test endpoint error',
            'code': 'MTLS_TEST_ERROR',
            'message': str(e)
        }), 500

@telemetry_bp.route('/api/v1/telemetry/health', methods=['GET'])
def telemetry_health():
    """
    Health check for telemetry service.
    
    Returns:
        200: Service status
    """
    try:
        # Check database connections
        db_status = {'mongodb': False, 'timescaledb': False, 'redis': False}
        
        # Check MongoDB
        try:
            db = get_db()
            db.command('ping')
            db_status['mongodb'] = True
        except:
            pass
        
        # Check TimescaleDB/PostgreSQL
        try:
            postgres_conn = get_postgres()
            if postgres_conn:
                cursor = postgres_conn.cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()  # Ensure we get the result
                cursor.close()
                db_status['timescaledb'] = True
        except Exception as e:
            logger.warning(f"TimescaleDB health check failed: {e}")
            pass
        
        # Check Redis
        try:
            redis_client = get_redis()
            if redis_client:
                redis_client.ping()
                db_status['redis'] = True
        except:
            pass
        
        # Overall health
        is_healthy = db_status['mongodb']  # MongoDB is required
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'databases': db_status,
            'message': 'MongoDB is required, TimescaleDB and Redis are optional'
        }), 200 if is_healthy else 503
        
    except Exception as e:
        logger.error(f"Error in telemetry health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


# ============================================================================
# Unified Telemetry API - Fetch from MongoDB + TimescaleDB
# Added: 2025-12-05 for Edge AI Telemetry Dashboard
# ============================================================================

@telemetry_bp.route('/api/v1/telemetry/availability/summary', methods=['GET'])
@require_auth
def get_devices_availability_summary():
    """
    Get telemetry data availability summary for multiple devices.
    Returns first/last dates, total days, and data point count for each device.

    Query params:
        device_ids: Optional comma-separated device IDs (returns all if not provided)
        source: 'mongodb', 'timescaledb', or 'both' (default: 'both')

    Returns:
        200: {
            "devices": {
                "<device_id>": {
                    "has_data": true|false,
                    "mongodb_count": number,
                    "timescaledb_count": number,
                    "first_date": "YYYY-MM-DD" or null,
                    "last_date": "YYYY-MM-DD" or null,
                    "total_days": number
                }
            },
            "total_devices": number,
            "has_data_devices": number,
            "source": "both|mongodb|timescaledb"
        }
    """
    try:
        device_ids_param = request.args.get('device_ids', '')
        source = request.args.get('source', 'both')

        device_id_list = [d.strip() for d in device_ids_param.split(',') if d.strip()] if device_ids_param else None

        results = {}

        # Query MongoDB
        mongodb_data = {}
        if source in ['both', 'mongodb']:
            try:
                db = get_db()
                pipeline = [
                    {'$group': {
                        '_id': '$device_id',
                        'count': {'$sum': 1},
                        'first_timestamp': {'$min': '$timestamp'},
                        'last_timestamp': {'$max': '$timestamp'}
                    }}
                ]

                if device_id_list:
                    pipeline.insert(0, {'$match': {'device_id': {'$in': device_id_list}}})

                cursor = db.telemetry.aggregate(pipeline)
                for doc in cursor:
                    device_id = doc['_id']
                    first_ts = doc.get('first_timestamp')
                    last_ts = doc.get('last_timestamp')

                    mongodb_data[device_id] = {
                        'count': doc['count'],
                        'first_timestamp': first_ts,
                        'last_timestamp': last_ts,
                        'first_date': first_ts.strftime('%Y-%m-%d') if first_ts else None,
                        'last_date': last_ts.strftime('%Y-%m-%d') if last_ts else None,
                    }
            except Exception as e:
                logger.warning(f"MongoDB availability query failed: {e}")

        # Query TimescaleDB - Query BOTH telemetry_generic AND device_telemetry tables
        # X-Brain and other devices may store data in device_telemetry instead of telemetry_generic
        timescaledb_data = {}
        if source in ['both', 'timescaledb']:
            try:
                conn = get_postgres()
                if conn:
                    with conn.cursor() as cursor:
                        if device_id_list:
                            # Use UNION to query both tables
                            # CAST device_id to TEXT for type compatibility (telemetry_generic uses UUID, device_telemetry uses VARCHAR)
                            cursor.execute("""
                                SELECT device_id::text, MIN(first_ts) as first_timestamp,
                                       MAX(last_ts) as last_timestamp, SUM(cnt) as data_point_count
                                FROM (
                                    SELECT device_id::text, MIN(time) as first_ts, MAX(time) as last_ts, COUNT(*) as cnt
                                    FROM telemetry_generic
                                    WHERE device_id::text = ANY(%s)
                                    GROUP BY device_id::text
                                    UNION ALL
                                    SELECT device_id, MIN(time) as first_ts, MAX(time) as last_ts, COUNT(*) as cnt
                                    FROM device_telemetry
                                    WHERE device_id = ANY(%s)
                                    GROUP BY device_id
                                ) combined
                                GROUP BY device_id
                            """, (device_id_list, device_id_list))
                        else:
                            cursor.execute("""
                                SELECT device_id::text, MIN(first_ts) as first_timestamp,
                                       MAX(last_ts) as last_timestamp, SUM(cnt) as data_point_count
                                FROM (
                                    SELECT device_id::text, MIN(time) as first_ts, MAX(time) as last_ts, COUNT(*) as cnt
                                    FROM telemetry_generic
                                    GROUP BY device_id::text
                                    UNION ALL
                                    SELECT device_id, MIN(time) as first_ts, MAX(time) as last_ts, COUNT(*) as cnt
                                    FROM device_telemetry
                                    GROUP BY device_id
                                ) combined
                                GROUP BY device_id
                                ORDER BY MAX(last_ts) DESC
                                LIMIT 100
                            """)

                        for row in cursor.fetchall():
                            device_id, first_ts, last_ts, count = row
                            timescaledb_data[device_id] = {
                                'count': count,
                                'first_timestamp': first_ts,
                                'last_timestamp': last_ts,
                                'first_date': first_ts.strftime('%Y-%m-%d') if first_ts else None,
                                'last_date': last_ts.strftime('%Y-%m-%d') if last_ts else None,
                            }
            except Exception as e:
                logger.warning(f"TimescaleDB availability query failed: {e}")

        # Merge results
        all_device_ids = set(mongodb_data.keys()) | set(timescaledb_data.keys())
        if device_id_list:
            all_device_ids.update(device_id_list)

        for device_id in all_device_ids:
            mongo_info = mongodb_data.get(device_id, {})
            ts_info = timescaledb_data.get(device_id, {})

            mongo_count = mongo_info.get('count', 0)
            ts_count = ts_info.get('count', 0)
            has_data = mongo_count > 0 or ts_count > 0

            # Use the earliest first_date and latest last_date
            first_date = mongo_info.get('first_date') or ts_info.get('first_date')
            last_date = mongo_info.get('last_date') or ts_info.get('last_date')

            if mongo_info.get('first_date') and ts_info.get('first_date'):
                first_date = min(mongo_info['first_date'], ts_info['first_date'])
            if mongo_info.get('last_date') and ts_info.get('last_date'):
                last_date = max(mongo_info['last_date'], ts_info['last_date'])

            # Calculate total days
            total_days = 0
            if first_date and last_date:
                from datetime import datetime as dt
                d1 = dt.strptime(first_date, '%Y-%m-%d')
                d2 = dt.strptime(last_date, '%Y-%m-%d')
                total_days = (d2 - d1).days + 1

            results[device_id] = {
                'has_data': has_data,
                'mongodb_count': mongo_count,
                'timescaledb_count': ts_count,
                'total_count': mongo_count + ts_count,
                'first_date': first_date,
                'last_date': last_date,
                'total_days': total_days
            }

        has_data_count = sum(1 for d in results.values() if d['has_data'])

        return jsonify({
            'devices': results,
            'total_devices': len(results),
            'has_data_devices': has_data_count,
            'source': source
        }), 200

    except Exception as e:
        logger.error(f"Error getting device availability summary: {e}")
        return jsonify({
            'error': 'Failed to get availability summary',
            'message': str(e)
        }), 500


@telemetry_bp.route('/api/v1/telemetry/unified/<device_id>', methods=['GET'])
@require_auth
def get_unified_telemetry(device_id):
    """
    Get telemetry data from MongoDB with fallback to TimescaleDB.
    Supports fetching raw data and AI inference results.

    Query params:
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        limit: Max records to return (default: 100, max: 1000)
        source: 'mongodb', 'timescaledb', or 'auto' (default: 'auto')
        include_ai: Include AI inference fields if available (default: true)

    Returns:
        200: {
            "device_id": string,
            "source": "mongodb|timescaledb",
            "data_points": [...],
            "total_count": number,
            "has_ai_data": boolean
        }
    """
    try:
        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = min(int(request.args.get('limit', 100)), 1000)
        source = request.args.get('source', 'auto')
        include_ai = request.args.get('include_ai', 'true').lower() == 'true'

        data_points = []
        actual_source = None
        has_ai_data = False

        # Try MongoDB first (if source is 'auto' or 'mongodb')
        if source in ['auto', 'mongodb']:
            try:
                db = get_db()
                query = {'device_id': device_id}

                if start_date or end_date:
                    query['timestamp'] = {}
                    if start_date:
                        from datetime import datetime as dt
                        query['timestamp']['$gte'] = dt.strptime(start_date, '%Y-%m-%d')
                    if end_date:
                        from datetime import datetime as dt
                        end_dt = dt.strptime(end_date, '%Y-%m-%d')
                        end_dt = end_dt.replace(hour=23, minute=59, second=59)
                        query['timestamp']['$lte'] = end_dt

                cursor = db.telemetry.find(query).sort('timestamp', -1).limit(limit)

                for doc in cursor:
                    point = {
                        'timestamp': doc['timestamp'].isoformat() if hasattr(doc['timestamp'], 'isoformat') else doc['timestamp'],
                        'device_id': doc['device_id'],
                    }

                    # Extract data fields
                    if 'data' in doc and isinstance(doc['data'], dict):
                        for key, value in doc['data'].items():
                            if isinstance(value, (int, float)):
                                point[key] = value
                                # Check for AI fields
                                if key.startswith('ai_'):
                                    has_ai_data = True

                    # Also check top-level AI fields
                    for ai_key in ['ai_confidence', 'ai_anomalyScore', 'ai_prediction', 'ai_latency', 'ai_model_version']:
                        if ai_key in doc:
                            point[ai_key] = doc[ai_key]
                            has_ai_data = True

                    data_points.append(point)

                if data_points:
                    actual_source = 'mongodb'
                    # Reverse to chronological order
                    data_points = data_points[::-1]

            except Exception as e:
                logger.warning(f"MongoDB query failed for device {device_id}: {e}")

        # Fallback to TimescaleDB (if source is 'auto' and no MongoDB data, or source is 'timescaledb')
        if (source == 'auto' and not data_points) or source == 'timescaledb':
            try:
                conn = get_postgres()
                if conn:
                    with conn.cursor() as cursor:
                        sql = """
                            SELECT time, device_id, metrics
                            FROM telemetry_generic
                            WHERE device_id = %s
                        """
                        params = [device_id]

                        if start_date:
                            sql += " AND time >= %s"
                            params.append(start_date)
                        if end_date:
                            sql += " AND time <= %s::date + interval '1 day'"
                            params.append(end_date)

                        sql += " ORDER BY time DESC LIMIT %s"
                        params.append(limit)

                        cursor.execute(sql, params)

                        for row in cursor.fetchall():
                            time_val, dev_id, metrics = row
                            point = {
                                'timestamp': time_val.isoformat() if hasattr(time_val, 'isoformat') else str(time_val),
                                'device_id': dev_id,
                            }

                            # Extract metrics from JSONB
                            if metrics and isinstance(metrics, dict):
                                for key, value in metrics.items():
                                    if isinstance(value, (int, float)):
                                        point[key] = value
                                        if key.startswith('ai_'):
                                            has_ai_data = True

                            data_points.append(point)

                        if data_points:
                            actual_source = 'timescaledb'
                            # Reverse to chronological order
                            data_points = data_points[::-1]

            except Exception as e:
                logger.warning(f"TimescaleDB query failed for device {device_id}: {e}")

        if not data_points:
            return jsonify({
                'device_id': device_id,
                'source': None,
                'data_points': [],
                'total_count': 0,
                'has_ai_data': False,
                'message': 'No telemetry data found for this device'
            }), 200

        return jsonify({
            'device_id': device_id,
            'source': actual_source,
            'data_points': data_points,
            'total_count': len(data_points),
            'has_ai_data': has_ai_data
        }), 200

    except Exception as e:
        logger.error(f"Error getting unified telemetry for device {device_id}: {e}")
        return jsonify({
            'error': 'Failed to get telemetry data',
            'message': str(e)
        }), 500
