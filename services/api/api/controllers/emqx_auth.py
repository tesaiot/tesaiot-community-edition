# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - EMQX Authentication Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




EMQX Webhook Controller for EMQX Integration
Handles authentication and ACL webhooks from EMQX broker
Implements Zero Trust Architecture for IoT device authentication
"""

from flask import Blueprint, request, jsonify
import logging
import time
import json
import os
import hmac

from ..services.mqtt_auth_service import (
    validate_mqtt_auth,
    handle_mqtt_disconnect,
    get_mqtt_auth_stats
)
from ..core.database import get_db, get_vault

logger = logging.getLogger(__name__)

# Create Blueprint
emqx_auth_bp = Blueprint('emqx_auth', __name__, url_prefix='/api/v1/emqx')

def _redact_webhook_payload(data):
    """Return a copy of a webhook payload safe for logging.

    SECURITY: EMQX auth webhooks carry plaintext MQTT passwords and full
    certificate PEMs. Redact password / *_secret / token fields and omit PEM
    bodies before anything reaches the logs.
    """
    if not isinstance(data, dict):
        return data
    redacted = {}
    for key, value in data.items():
        key_l = str(key).lower()
        if key_l == 'password' or key_l.endswith('_secret') or key_l in ('secret', 'token', 'api_key'):
            redacted[key] = '***REDACTED***' if value else value
        elif key_l in ('cert_pem', 'peer_cert', 'certificate') and isinstance(value, str) and value:
            redacted[key] = f'<PEM omitted, {len(value)} bytes>'
        elif isinstance(value, dict):
            redacted[key] = _redact_webhook_payload(value)
        else:
            redacted[key] = value
    return redacted


def _validate_webhook_authorization():
    """
    Validate EMQX webhook authorization header.
    
    Returns:
        bool: True if authorized, False if denied
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            logger.warning("EMQX webhook called without Authorization header")
            return False

        # SECURITY: Fail closed. No default secret. Reject when the webhook
        # secret is unset or still a CHANGEME* placeholder.
        expected_secret = (os.getenv('EMQX_WEBHOOK_SECRET') or '').strip()
        if not expected_secret or expected_secret.startswith('CHANGEME'):
            logger.error(
                "EMQX_WEBHOOK_SECRET is not configured (unset or CHANGEME*) - denying webhook"
            )
            return False

        expected_auth = f"Bearer {expected_secret}"

        # Constant-time comparison to avoid timing side channels.
        if not hmac.compare_digest(auth_header, expected_auth):
            logger.warning("EMQX webhook called with invalid authorization")
            return False

        return True
        
    except Exception as e:
        logger.error(f"Webhook authorization validation error: {e}")
        return False

@emqx_auth_bp.route('/auth', methods=['POST'])
def emqx_auth_webhook():
    """
    EMQX authentication webhook endpoint.
    
    This endpoint is called by EMQX for every device connection attempt.
    It validates device certificates against Vault PKI and device registry.
    
    Expected EMQX webhook payload for certificate auth:
    {
        "clientid": "device-001",
        "username": "device-001",
        "certificate": "-----BEGIN CERTIFICATE-----...",
        "protocol": "mqtt",
        "sockport": 8883,
        "cn": "device-001.device.tesa.iot",
        "dn": "CN=device-001.device.tesa.iot,O=BDH Corporation"
    }
    
    Expected EMQX webhook payload for username/password auth:
    {
        "clientid": "device-001",
        "username": "device-001",
        "password": "device-secret",
        "protocol": "mqtt",
        "sockport": 1883
    }
    
    Returns:
        JSON response for EMQX:
        - {"result": "allow"} - Allow connection
        - {"result": "deny"} - Deny connection
    """
    start_time = time.time()
    
    # Validate webhook authorization
    if not _validate_webhook_authorization():
        return jsonify({'result': 'deny'}), 401
    
    try:
        # Get webhook data from EMQX
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.warning("EMQX auth webhook called with no data")
            return jsonify({
                'result': 'deny'
            }), 200
        
        # Log incoming authentication request
        client_id = webhook_data.get('clientid', 'unknown')
        logger.info(f"EMQX auth request received for client: {client_id}")
        
        # Redacted payload at DEBUG only (passwords / PEMs never reach logs)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"EMQX webhook data (redacted): "
                f"{json.dumps(_redact_webhook_payload(webhook_data), indent=2, default=str)}"
            )
        
        # Transform EMQX format to VerneMQ format for compatibility
        vernemq_format = _transform_emqx_to_vernemq_format(webhook_data)
        
        # Validate authentication using existing service
        auth_result = validate_mqtt_auth(vernemq_format)
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Transform result back to EMQX format
        result_status = auth_result.get('result', 'error')
        logger.info(f"EMQX auth result for {client_id}: {result_status} ({processing_time:.1f}ms)")
        
        # Return response to EMQX
        if result_status == 'ok':
            return jsonify({'result': 'allow'}), 200
        else:
            return jsonify({'result': 'deny'}), 200
            
    except Exception as e:
        processing_time = (time.time() - start_time) * 1000
        logger.error(f"EMQX auth webhook error: {e} ({processing_time:.1f}ms)")
        
        return jsonify({
            'result': 'deny'
        }), 200

@emqx_auth_bp.route('/acl', methods=['POST'])
def emqx_acl_webhook():
    """
    EMQX ACL (Access Control List) webhook endpoint.
    
    This endpoint is called by EMQX to check if a client can publish/subscribe to a topic.
    
    Expected EMQX webhook payload:
    {
        "clientid": "device-001",
        "username": "device-001",
        "action": "publish",  # or "subscribe"
        "topic": "devices/device-001/telemetry",
        "protocol": "mqtt",
        "sockport": 8883
    }
    
    Returns:
        JSON response for EMQX:
        - {"result": "allow"} - Allow access
        - {"result": "deny"} - Deny access
    """
    # Validate webhook authorization
    if not _validate_webhook_authorization():
        return jsonify({'result': 'deny'}), 401
    
    try:
        webhook_data = request.get_json()
        
        if not webhook_data:
            logger.warning("EMQX ACL webhook called with no data")
            return jsonify({'result': 'deny'}), 200
        
        client_id = webhook_data.get('clientid', '')
        username = webhook_data.get('username', '')
        action = webhook_data.get('action', '')
        topic = webhook_data.get('topic', '')
        
        logger.info(f"EMQX ACL request: client={client_id}, action={action}, topic={topic}")
        
        # Check if it's an internal service account
        internal_service_patterns = [
            'mqtt-bridge',
            'service-mqtt-bridge',
            'grafana-mqtt',
            'analytics-service',
            'tesa-protected-update-service',
            'protected-update-service',
            'protected-update',
            # OTA Phase 2: MQTT Chunk-based Transfer (Added: 2026-01-05)
            'ota-mqtt-publisher',
            'tesa-ota-service',
            'ota-service'
        ]
        
        is_internal_service = any(client_id.startswith(pattern) for pattern in internal_service_patterns)
        
        # Check for MQTT API token clients (WSS third-party integration)
        # API tokens are used as both username and client_id prefix
        is_api_token_client = username and username.startswith('tesa_mqtt_')

        if is_api_token_client:
            # API token clients can ONLY subscribe to telemetry topics, cannot publish
            if action == 'subscribe':
                # Allow subscribing to telemetry topics for all devices in their organization
                # Topic patterns: device/+/telemetry/#, device/<device_id>/telemetry, device/<device_id>/telemetry/<sensor>
                if topic.startswith('device/') and '/telemetry' in topic:
                    logger.info(f"API token ACL allowed: {username[:30]}... subscribe to {topic}")
                    return jsonify({'result': 'allow'}), 200
                elif topic.startswith('devices/') and '/telemetry' in topic:
                    logger.info(f"API token ACL allowed: {username[:30]}... subscribe to {topic}")
                    return jsonify({'result': 'allow'}), 200
                else:
                    logger.warning(f"API token ACL denied: {username[:30]}... subscribe to {topic} (not a telemetry topic)")
                    return jsonify({'result': 'deny'}), 200
            elif action == 'publish':
                # API tokens cannot publish
                logger.warning(f"API token ACL denied: {username[:30]}... publish to {topic} (publish not allowed for API tokens)")
                return jsonify({'result': 'deny'}), 200

        if is_internal_service:
            # v2026.02: Allow internal services to subscribe to $SYS topics (Clear Retained on Connect)
            if action == 'subscribe' and topic.startswith('$SYS/'):
                logger.info(f"Internal service ACL allowed: {client_id} subscribe to {topic}")
                return jsonify({'result': 'allow'}), 200
            # Allow internal services to subscribe to all device topics (both singular and plural)
            if action == 'subscribe' and (topic.startswith('devices/') or topic.startswith('device/')):
                logger.info(f"Internal service ACL allowed: {client_id} subscribe to {topic}")
                return jsonify({'result': 'allow'}), 200
            # Also allow internal services to publish to device topics (for testing/simulation)
            if action == 'publish' and (topic.startswith('devices/') or topic.startswith('device/')):
                logger.info(f"Internal service ACL allowed: {client_id} publish to {topic}")
                return jsonify({'result': 'allow'}), 200
            # Allow internal services to subscribe to telemetry topics (new format)
            if action == 'subscribe' and topic.startswith('telemetry/'):
                logger.info(f"Internal service ACL allowed: {client_id} subscribe to {topic}")
                return jsonify({'result': 'allow'}), 200
            # Allow internal services to publish to telemetry topics
            if action == 'publish' and topic.startswith('telemetry/'):
                logger.info(f"Internal service ACL allowed: {client_id} publish to {topic}")
                return jsonify({'result': 'allow'}), 200
        
        # For regular devices, check topic permissions
        acl_result = _check_device_acl(client_id, action, topic)
        
        if acl_result:
            return jsonify({'result': 'allow'}), 200
        else:
            return jsonify({'result': 'deny'}), 200
            
    except Exception as e:
        logger.error(f"EMQX ACL webhook error: {e}")
        return jsonify({'result': 'deny'}), 200

@emqx_auth_bp.route('/disconnect', methods=['POST'])
def emqx_disconnect_webhook():
    """
    EMQX disconnect webhook endpoint.
    
    Called when a device disconnects from EMQX broker.
    Updates device connection status and logs the event.
    
    Expected EMQX webhook payload:
    {
        "clientid": "device-001",
        "username": "device-001",
        "reason": "normal",
        "protocol": "mqtt",
        "sockport": 8883
    }
    
    Returns:
        JSON response acknowledging the disconnect
    """
    # Validate webhook authorization
    if not _validate_webhook_authorization():
        return jsonify({'result': 'ok'}), 401
    
    try:
        webhook_data = request.get_json()
        
        if webhook_data:
            client_id = webhook_data.get('clientid', 'unknown')
            reason = webhook_data.get('reason', 'unknown')
            
            logger.info(f"EMQX disconnect: {client_id} - {reason}")
            
            # Transform to VerneMQ format and handle disconnect
            vernemq_format = {
                'client_id': client_id,
                'username': webhook_data.get('username', client_id),
                'reason': reason
            }
            
            result = handle_mqtt_disconnect(vernemq_format)
            return jsonify({'result': 'ok'}), 200
        else:
            return jsonify({'result': 'ok'}), 200
            
    except Exception as e:
        logger.error(f"EMQX disconnect webhook error: {e}")
        return jsonify({'result': 'ok'}), 200  # Don't block disconnect

def _is_admin_request():
    """Check whether the request carries a valid admin JWT (no decorator)."""
    try:
        from ..core.auth import verify_token
        auth_header = request.headers.get('Authorization') or ''
        parts = auth_header.split(' ')
        if len(parts) != 2:
            return False
        payload, _err = verify_token(parts[1])
        if not payload:
            return False
        role = (payload.get('role') or '').lower()
        return role in ('admin', 'organization_admin', 'platform_admin', 'super_admin', 'org_admin')
    except Exception:
        return False


@emqx_auth_bp.route('/stats', methods=['GET'])
def emqx_auth_statistics():
    """
    Get EMQX authentication statistics (operational endpoint).

    SECURITY: previously unauthenticated. Requires either the EMQX webhook
    bearer secret or an admin JWT.

    Returns:
        JSON response with authentication statistics
    """
    if not (_validate_webhook_authorization() or _is_admin_request()):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stats = get_mqtt_auth_stats()
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting EMQX auth stats: {e}")
        return jsonify({
            'error': 'Failed to retrieve authentication statistics'
        }), 500

@emqx_auth_bp.route('/health', methods=['GET'])
def emqx_auth_health():
    """
    EMQX authentication service health check.
    
    Verifies that the authentication service dependencies are available:
    - Database connection
    - Vault PKI connection
    - Service configuration
    
    Returns:
        JSON response with service health status
    """
    try:
        health_status = {
            'service': 'emqx_auth',
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        # Check database connection. SECURITY: status-only - internal error
        # strings (connection URIs, Vault details) are logged, never returned.
        try:
            db = get_db()
            db.devices.count_documents({}, limit=1)
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            logger.warning(f"EMQX auth health: database unhealthy: {e}")
            health_status['checks']['database'] = 'unhealthy'
            health_status['status'] = 'degraded'

        # Check Vault connection
        try:
            vault_client = get_vault()
            if vault_client and vault_client.is_authenticated():
                health_status['checks']['vault_pki'] = 'healthy'
            else:
                health_status['checks']['vault_pki'] = 'unhealthy'
                health_status['status'] = 'degraded'
        except Exception as e:
            logger.warning(f"EMQX auth health: vault unhealthy: {e}")
            health_status['checks']['vault_pki'] = 'unhealthy'
            health_status['status'] = 'degraded'

        # Check EMQX webhook configuration
        health_status['checks']['emqx_webhook'] = 'configured'

        # Return appropriate status code
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"EMQX auth health check error: {e}")
        return jsonify({
            'service': 'emqx_auth',
            'status': 'unhealthy',
            'timestamp': time.time()
        }), 503

# Helper functions

def _transform_emqx_to_vernemq_format(emqx_data):
    """
    Transform EMQX webhook format to VerneMQ format for compatibility.
    
    Args:
        emqx_data: EMQX webhook payload
        
    Returns:
        dict: VerneMQ compatible format
    """
    # Redacted payload at DEBUG only (passwords / PEMs never reach logs)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"EMQX webhook data received (redacted): "
            f"{json.dumps(_redact_webhook_payload(emqx_data), indent=2, default=str)}"
        )
    
    # Map EMQX fields to VerneMQ fields
    # EMQX v5 sends 'client_id' with underscore, not 'clientid'
    vernemq_format = {
        'client_id': emqx_data.get('client_id', emqx_data.get('clientid', '')),  # Try both formats
        'username': emqx_data.get('username', ''),
        'password': emqx_data.get('password', ''),
        'mountpoint': '',
        'clean_session': True,
        'protocol': emqx_data.get('protocol', 'mqtt'),
        'sockport': emqx_data.get('sockport', emqx_data.get('peerport', 1883))  # Also fixed port field
    }
    
    # EMQX v5 certificate fields based on documentation
    # Check for cert_subject and cert_common_name which are the documented fields
    if 'cert_subject' in emqx_data and emqx_data['cert_subject']:
        # cert_subject contains the full subject DN
        subject = emqx_data['cert_subject']
        vernemq_format['peer_cert_subject'] = subject
        logger.info(f"Certificate subject found: {subject}")
        
        # Extract CN from subject if available
        if 'CN=' in subject:
            cn = subject.split('CN=')[1].split(',')[0].strip()
            vernemq_format['peer_cert_cn'] = cn
            logger.info(f"Extracted CN from subject: {cn}")
    
    if 'cert_common_name' in emqx_data and emqx_data['cert_common_name']:
        # cert_common_name is the CN directly
        vernemq_format['peer_cert_cn'] = emqx_data['cert_common_name']
        logger.info(f"Certificate common name found: {emqx_data['cert_common_name']}")
    
    # EMQX also sends 'cert_subject' and 'cert_common_name' fields for mTLS authentication
    if 'cert_subject' in emqx_data and emqx_data['cert_subject']:
        # cert_subject contains the full subject DN
        vernemq_format['peer_cert_subject'] = emqx_data['cert_subject']
        logger.info(f"Certificate DN found: {emqx_data['cert_subject']}")
        
        # Extract CN from DN if not already set
        if 'peer_cert_cn' not in vernemq_format and 'CN=' in emqx_data['cert_subject']:
            cn = emqx_data['cert_subject'].split('CN=')[1].split(',')[0].strip()
            vernemq_format['peer_cert_cn'] = cn
            logger.info(f"Extracted CN from DN: {cn}")
    
    if 'cert_common_name' in emqx_data and emqx_data['cert_common_name']:
        # cert_common_name is the common name directly
        vernemq_format['peer_cert_cn'] = emqx_data['cert_common_name']
        logger.info(f"Certificate CN found: {emqx_data['cert_common_name']}")
    
    # Check for certificate field (full PEM certificate)
    if 'cert_pem' in emqx_data and emqx_data['cert_pem']:
        # Check if EMQX sent literal ${cert_pem} instead of actual certificate
        if emqx_data['cert_pem'] == '${cert_pem}':
            logger.warning(f"EMQX sent literal ${{cert_pem}} instead of certificate content for client: {emqx_data.get('clientid')}")
            # Skip adding the certificate to avoid validation errors
        else:
            vernemq_format['peer_cert'] = emqx_data['cert_pem']
            logger.info(f"Full certificate found for client: {emqx_data.get('clientid')}")
    
    # Check if we're on port 8883 (TLS port) but no certificate data
    # Also handle when peerport is sent as literal ${peerport}
    sockport = emqx_data.get('peerport', 0)
    if isinstance(sockport, str) and sockport == '${peerport}':
        # Assume TLS port if we see the literal placeholder
        sockport = 8883
        logger.warning(f"EMQX sent literal ${{peerport}} - assuming port 8883")
    elif isinstance(sockport, str):
        try:
            sockport = int(sockport)
        except ValueError:
            sockport = 0
    
    if sockport == 8883:
        cert_data_found = any([
            'cert_subject' in emqx_data and emqx_data['cert_subject'] and emqx_data['cert_subject'] != '${cert_subject}',
            'cert_common_name' in emqx_data and emqx_data['cert_common_name'] and emqx_data['cert_common_name'] != '${cert_common_name}',
            'cert_pem' in emqx_data and emqx_data['cert_pem'] and emqx_data['cert_pem'] != '${cert_pem}'
        ])
        
        if not cert_data_found:
            # Check if we have CN/Subject but EMQX sent placeholders
            if ('cert_common_name' in emqx_data and emqx_data['cert_common_name'] and 
                emqx_data['cert_common_name'] != '${cert_common_name}'):
                # We have CN from TLS handshake even if certificate wasn't expanded
                vernemq_format['peer_cert_cn'] = emqx_data['cert_common_name']
                vernemq_format['tls_validated'] = True
                logger.info(f"Client {emqx_data.get('clientid')} has CN from TLS: {emqx_data['cert_common_name']}")
            elif ('cert_subject' in emqx_data and emqx_data['cert_subject'] and 
                  emqx_data['cert_subject'] != '${cert_subject}'):
                # We have subject from TLS handshake
                vernemq_format['peer_cert_subject'] = emqx_data['cert_subject']
                vernemq_format['tls_validated'] = True
                logger.info(f"Client {emqx_data.get('clientid')} has subject from TLS: {emqx_data['cert_subject']}")
            else:
                logger.info(f"Client {emqx_data.get('clientid')} connected on TLS port 8883 with server-only TLS (no client certificate)")
                # This is likely a server-only TLS connection
                # The device authenticated using TLS but without client certificate
                vernemq_format['tls_validated'] = True
    
    # Log what we found
    logger.info(f"Transformed format - has cert data: {'peer_cert_cn' in vernemq_format or 'peer_cert_subject' in vernemq_format}")
    logger.info(f"VerneMQ format fields: {list(vernemq_format.keys())}")
    if 'peer_cert_cn' in vernemq_format:
        logger.info(f"Certificate CN: {vernemq_format['peer_cert_cn']}")
    if 'peer_cert_subject' in vernemq_format:
        logger.info(f"Certificate Subject: {vernemq_format['peer_cert_subject']}")
    if 'peer_cert' in vernemq_format:
        logger.info(f"Certificate PEM: {'Present' if vernemq_format['peer_cert'] else 'Empty'}")
    
    return vernemq_format

def _check_device_acl(client_id, action, topic):
    """
    Check if a device has permission to publish/subscribe to a topic.
    
    Args:
        client_id: Device client ID
        action: "publish" or "subscribe"
        topic: MQTT topic
        
    Returns:
        bool: True if allowed, False if denied
    """
    try:
        # Get database connection at the beginning of the function
        db = get_db()

        # Default topic patterns for devices
        # Devices can publish to their own telemetry/status/events/metrics topics
        # Devices can subscribe to their own commands/config/firmware topics

        # For Trust M devices: client_id = trustm_uid, but topics use device_id
        # Need to lookup device by trustm_uid to get the associated device_id
        device = db.devices.find_one({
            '$or': [
                {'device_id': client_id},
                {'trustm_uid': client_id}
            ]
        })

        # Get the actual device_id (may differ from client_id for Trust M devices)
        actual_device_id = device.get('device_id') if device else client_id

        # Debug logging for Trust M devices
        if device and device.get('trustm_uid'):
            logger.info(f"ACL check for Trust M device: client_id={client_id}, device_id={actual_device_id}, action={action}, topic={topic}")

        topic_parts = topic.split('/')

        if topic_parts:
            first_segment = topic_parts[0]

            if first_segment in ['device', 'devices'] and len(topic_parts) > 1:
                topic_device_id = topic_parts[1]
                # Allow if topic_device_id matches EITHER client_id OR actual_device_id
                if topic_device_id != client_id and topic_device_id != actual_device_id:
                    logger.warning(
                        f"ACL denied: {client_id} (device_id: {actual_device_id}) tried to access {topic_device_id}'s topic"
                    )
                    return False
            elif first_segment not in ['device', 'devices', client_id]:
                # Fast-fail topics outside the device namespace unless custom ACL allows it
                logger.warning(
                    f"ACL soft-deny (outside namespace): {client_id} {action} {topic}"
                )
            elif first_segment == client_id and len(topic_parts) > 1 and topic_parts[1] != '#':
                # Ensure the leaf topic still belongs to this device
                pass

        # For Trust M devices: topics use device_id, not trustm_uid (client_id)
        # So base_paths must be built from actual_device_id
        base_paths = [
            f"device/{actual_device_id}",
            f"devices/{actual_device_id}",
            actual_device_id,
        ]

        # Deduplicate while preserving order
        seen = set()
        canonical_base_paths = []
        for path in base_paths:
            if path not in seen:
                seen.add(path)
                canonical_base_paths.append(path)

        allowed_publish_types = ['telemetry', 'status', 'events', 'metrics']
        allowed_subscribe_types = ['commands', 'config', 'firmware']

        if action == 'publish':
            publish_patterns = []
            for base in canonical_base_paths:
                for topic_type in allowed_publish_types:
                    publish_patterns.append(f"{base}/{topic_type}")
                    publish_patterns.append(f"{base}/{topic_type}/#")

                # Special case: Allow devices to publish CSR to commands/csr topic
                publish_patterns.append(f"{base}/commands/csr")
                # Special case: Allow devices to publish to commands/request for Protected Update
                publish_patterns.append(f"{base}/commands/request")
                # Special case: Allow devices to publish to commands/check_certificate for Smart Auto-Fallback
                publish_patterns.append(f"{base}/commands/check_certificate")
                # Special case: Allow devices to publish to commands/upload_certificate for Smart Auto-Fallback
                publish_patterns.append(f"{base}/commands/upload_certificate")
                # Special case: Allow devices to publish to commands/sync_certificate for Smart Auto-Fallback v0.5.51
                publish_patterns.append(f"{base}/commands/sync_certificate")
                # Special case: Allow devices to publish to commands/init for MQTT slot initialization (v0.5.54 workaround)
                publish_patterns.append(f"{base}/commands/init")
                # OTA Polling Mode: Allow devices to publish OTA status/requests
                publish_patterns.append(f"{base}/commands/ota/check")          # Device asks: Any update?
                publish_patterns.append(f"{base}/commands/ota/request")        # Device requests firmware
                publish_patterns.append(f"{base}/commands/ota/chunk_request")  # Resume download (specific chunk)
                publish_patterns.append(f"{base}/commands/ota/result")         # Report update success/failure

                # ================================================================
                # OTA Phase 2: MQTT Chunk-based Transfer (Infineon cy_ota_agent)
                # Added: 2026-01-05
                # ================================================================
                # Device → Platform: Request job, request chunks, report result
                publish_patterns.append(f"{base}/ota/request")           # Device requests OTA job
                publish_patterns.append(f"{base}/ota/chunk/request")     # Device requests specific chunk
                publish_patterns.append(f"{base}/ota/result")            # Device reports OTA result
                # Phase 3: Per-chunk ACK
                publish_patterns.append(f"{base}/ota/chunk/ack")         # Device ACKs chunk received
                publish_patterns.append(f"{base}/ota/chunk/nack")        # Device NACKs chunk (retry)

            for pattern in publish_patterns:
                if _match_topic_pattern(topic, pattern):
                    logger.info(f"ACL allowed: {client_id} publish to {topic} (pattern {pattern})")
                    return True

        elif action == 'subscribe':
            subscribe_patterns = []
            for base in canonical_base_paths:
                for topic_type in allowed_subscribe_types:
                    subscribe_patterns.append(f"{base}/{topic_type}")
                    subscribe_patterns.append(f"{base}/{topic_type}/#")
                subscribe_patterns.append(f"{base}/#")

                # ================================================================
                # OTA Phase 2: MQTT Chunk-based Transfer (Infineon cy_ota_agent)
                # Added: 2026-01-05
                # ================================================================
                # Platform → Device: Push job info and chunk data
                subscribe_patterns.append(f"{base}/ota/job")              # Device subscribes to OTA job announcements
                subscribe_patterns.append(f"{base}/ota/chunk/data")       # Device subscribes to chunk data stream

            # Debug: log all generated patterns
            logger.info(f"ACL subscribe patterns for {client_id}: {subscribe_patterns}")

            for pattern in subscribe_patterns:
                match_result = _match_topic_pattern(topic, pattern)
                logger.debug(f"ACL pattern match: topic={topic}, pattern={pattern}, result={match_result}")
                if match_result:
                    logger.info(f"ACL allowed: {client_id} subscribe to {topic} (pattern {pattern})")
                    return True

        # Check if device exists and has custom ACL rules
        # Note: device and actual_device_id already retrieved at the beginning of this function
        # For custom ACL, use the actual_device_id (not client_id which may be trustm_uid)
        custom_device = db.devices.find_one({'device_id': actual_device_id})

        if custom_device:
            # Check custom ACL rules if defined
            custom_acl = custom_device.get('mqtt_acl', {})
            
            if action == 'publish' and 'publish_topics' in custom_acl:
                for allowed_topic in custom_acl['publish_topics']:
                    if _match_topic_pattern(topic, allowed_topic):
                        logger.info(f"ACL allowed (custom): {client_id} publish to {topic}")
                        return True
                        
            elif action == 'subscribe' and 'subscribe_topics' in custom_acl:
                for allowed_topic in custom_acl['subscribe_topics']:
                    if _match_topic_pattern(topic, allowed_topic):
                        logger.info(f"ACL allowed (custom): {client_id} subscribe to {topic}")
                        return True
        
        # Default deny
        logger.warning(f"ACL denied: {client_id} {action} {topic}")
        return False
        
    except Exception as e:
        logger.error(f"ACL check error: {e}")
        return False

def _match_topic_pattern(topic, pattern):
    """
    Match MQTT topic against a pattern with wildcards.
    
    Args:
        topic: Actual topic (e.g., "devices/dev1/telemetry")
        pattern: Pattern with wildcards (e.g., "devices/+/telemetry", "devices/#")
        
    Returns:
        bool: True if topic matches pattern
    """
    try:
        # Split topics into parts
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        # Multi-level wildcard (#) must be at the end
        if '#' in pattern and pattern_parts[-1] != '#':
            return False
        
        # Compare each part
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                # Multi-level wildcard matches everything from here
                return True
                
            if i >= len(topic_parts):
                # Pattern is longer than topic
                return False
                
            if pattern_part == '+':
                # Single-level wildcard matches any value at this level
                continue
                
            if pattern_part != topic_parts[i]:
                # Exact match required but doesn't match
                return False
        
        # All parts matched, check if lengths are equal
        return len(topic_parts) == len(pattern_parts)
        
    except Exception as e:
        logger.error(f"Topic pattern matching error: {e}")
        return False

# Error handlers
@emqx_auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({
        'result': 'deny',
        'message': 'Bad request format'
    }), 200

@emqx_auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'result': 'deny',
        'message': 'Internal server error'
    }), 200
