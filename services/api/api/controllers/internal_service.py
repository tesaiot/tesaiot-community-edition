# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Internal Service API Controller

This module provides internal API endpoints for platform services (like MQTT Bridge)
that need to communicate with the API without user authentication.

These endpoints:
- Use service-to-service authentication (shared secret)
- Bypass organization-based RBAC (platform-level access)
- Are only accessible from within the Docker network

Security:
- X-Internal-Service header identifies the calling service
- X-Service-Secret header provides the shared secret
- Endpoints are NOT exposed externally (internal Docker network only)

Created: 2026-01-13
Author: TESAIoT Platform Team
"""

import hmac
import os
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, g

logger = logging.getLogger(__name__)

# Blueprint for internal service endpoints
internal_service_bp = Blueprint('internal_service', __name__, url_prefix='/internal/v1')

# ============================================================================
# Internal Service Authentication
# ============================================================================

# Load service secret from environment.
# There is intentionally NO default: a shared default would let anyone forge
# internal service-to-service auth (X-Service-Secret). Fail closed if unset.
INTERNAL_SERVICE_SECRET = os.environ.get('INTERNAL_SERVICE_SECRET')
if not INTERNAL_SERVICE_SECRET:
    raise RuntimeError(
        "INTERNAL_SERVICE_SECRET environment variable is required and must be "
        "set to a strong, unique value. Refusing to start with no internal "
        "service secret configured."
    )

# Allowed internal services
ALLOWED_SERVICES = {
    'mqtt-bridge': ['certificate.sign', 'device.read'],
    'mqtt-bridge-csr': ['certificate.sign'],
    'mqtt-bridge-protected-update': ['certificate.sign', 'protected-update.execute'],
    'vault-agent': ['certificate.sign', 'certificate.revoke'],
}


def require_internal_service_auth(required_permission=None):
    """
    Decorator for internal service authentication.

    Validates:
    1. X-Internal-Service header (service name)
    2. X-Service-Secret header (shared secret)
    3. Optional: required permission for the operation

    Usage:
        @require_internal_service_auth('certificate.sign')
        def sign_certificate():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get headers
            service_name = request.headers.get('X-Internal-Service', '').strip()
            service_secret = request.headers.get('X-Service-Secret', '').strip()

            # Validate service name
            if not service_name:
                logger.warning("Internal service auth failed: missing X-Internal-Service header")
                return jsonify({
                    'error': 'MISSING_SERVICE_HEADER',
                    'message': 'X-Internal-Service header is required'
                }), 401

            # Validate service secret (constant-time; no timing side channel)
            if not service_secret or not hmac.compare_digest(service_secret, INTERNAL_SERVICE_SECRET):
                logger.warning(f"Internal service auth failed: invalid secret from service '{service_name}'")
                return jsonify({
                    'error': 'INVALID_SERVICE_SECRET',
                    'message': 'Invalid service secret'
                }), 401

            # Validate service is allowed
            if service_name not in ALLOWED_SERVICES:
                logger.warning(f"Internal service auth failed: unknown service '{service_name}'")
                return jsonify({
                    'error': 'UNKNOWN_SERVICE',
                    'message': f"Service '{service_name}' is not registered"
                }), 403

            # Validate permission if required
            if required_permission:
                allowed_permissions = ALLOWED_SERVICES.get(service_name, [])
                if required_permission not in allowed_permissions:
                    logger.warning(
                        f"Internal service auth failed: service '{service_name}' "
                        f"does not have permission '{required_permission}'"
                    )
                    return jsonify({
                        'error': 'PERMISSION_DENIED',
                        'message': f"Service '{service_name}' does not have permission '{required_permission}'"
                    }), 403

            # Set service context for downstream use
            g.internal_service = {
                'name': service_name,
                'permissions': ALLOWED_SERVICES.get(service_name, [])
            }

            logger.debug(f"Internal service auth successful: {service_name}")
            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ============================================================================
# Internal Certificate Signing Endpoint
# ============================================================================

@internal_service_bp.route('/certificates/sign', methods=['POST'])
@require_internal_service_auth('certificate.sign')
def internal_sign_csr():
    """
    Sign a CSR for any device (internal service use only).

    This endpoint bypasses organization-based RBAC and allows signing
    CSRs for devices in any organization. It's designed for internal
    platform services like MQTT Bridge.

    Headers:
        X-Internal-Service: mqtt-bridge (required)
        X-Service-Secret: <shared-secret> (required)

    Request JSON:
        {
            "device_id": "uuid",
            "csr": "PEM-encoded CSR",
            "validity_days": 365 (optional, default 365),
            "correlation_id": "uuid" (optional, for tracking)
        }

    Returns:
        200: Certificate signed successfully
        400: Invalid request
        401: Authentication failed
        403: Permission denied
        404: Device not found
        500: Server error
    """
    try:
        data = request.get_json(silent=True) or {}

        # Validate required fields
        device_id = data.get('device_id', '').strip()
        csr_content = data.get('csr', '').strip()

        if not device_id:
            return jsonify({
                'error': 'MISSING_DEVICE_ID',
                'message': 'device_id is required'
            }), 400

        if not csr_content:
            return jsonify({
                'error': 'MISSING_CSR',
                'message': 'csr is required'
            }), 400

        # Optional parameters
        validity_days = int(data.get('validity_days', 365))
        correlation_id = data.get('correlation_id', '')

        logger.info(
            f"Internal CSR signing request from {g.internal_service['name']}: "
            f"device_id={device_id}, correlation_id={correlation_id}"
        )

        # Import certificate service
        from ..services.certificate_service import sign_device_csr_internal

        # Sign CSR using internal service function (bypasses org check)
        result = sign_device_csr_internal(
            device_id=device_id,
            csr_content=csr_content,
            validity_days=validity_days,
            requesting_service=g.internal_service['name'],
            correlation_id=correlation_id
        )

        if not result or 'error' in result:
            error_msg = result.get('error', 'Unknown error') if result else 'CSR signing failed'
            logger.error(f"Internal CSR signing failed for device {device_id}: {error_msg}")
            return jsonify({
                'error': 'CSR_SIGNING_FAILED',
                'message': error_msg
            }), 500

        logger.info(f"Internal CSR signing successful for device {device_id}")

        return jsonify({
            'success': True,
            'device_id': device_id,
            'certificate': result.get('certificate'),
            'serial_number': result.get('serial_number'),
            'expires_at': result.get('expires_at'),
            'correlation_id': correlation_id
        }), 200

    except Exception as e:
        logger.exception(f"Internal CSR signing error: {str(e)}")
        return jsonify({
            'error': 'INTERNAL_ERROR',
            'message': str(e)
        }), 500


@internal_service_bp.route('/health', methods=['GET'])
def internal_health():
    """
    Health check endpoint for internal service API.
    Does not require authentication.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'internal-api',
        'version': os.environ.get('API_VERSION', 'unknown')
    }), 200


# ============================================================================
# Service Registration Info (for debugging)
# ============================================================================

@internal_service_bp.route('/services', methods=['GET'])
@require_internal_service_auth()
def list_registered_services():
    """
    List registered internal services and their permissions.
    Requires internal service authentication.
    """
    return jsonify({
        'services': {
            name: {'permissions': perms}
            for name, perms in ALLOWED_SERVICES.items()
        }
    }), 200

# Protected Update (OTA) internal endpoints are out of scope for the CE
# distribution and have been removed.
