# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Authentication
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: Dynamic (read from VERSION.txt)
Module: Authentication Middleware
Build: 2025-06-08 10:55:00 UTC

Provides authentication decorators and JWT token management.
"""

import jwt
import hashlib
import logging
import os
import hmac
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app, g
from .database import get_db, get_redis
from .rbac import RBAC
# from ..services.enhanced_certificate_validation import validate_device_certificate_enhanced, validate_with_circuit_breaker

logger = logging.getLogger(__name__)

# Roles that grant write/admin capabilities. When the user database is down we
# cannot confirm such an account still exists/is active, so requests carrying
# these role claims are rejected (503) instead of trusted from the JWT alone.
PRIVILEGED_ROLES = frozenset({
    'admin', 'organization_admin', 'platform_admin',
    'super_admin', 'org_admin', 'manager',
})


def _get_jwt_secret():
    """Resolve the JWT signing secret.

    SECURITY: the JWT secret must be configured explicitly via JWT_SECRET_KEY
    or JWT_SECRET. The historical silent fallback to Flask's SECRET_KEY has
    been removed - it coupled session-cookie signing with API-token signing
    and could silently weaken both. Boot validation
    (Config.validate_security_config) enforces presence in production.
    """
    jwt_secret = (
        current_app.config.get('JWT_SECRET_KEY') or
        current_app.config.get('JWT_SECRET') or
        os.environ.get('JWT_SECRET_KEY') or
        os.environ.get('JWT_SECRET')
    )
    if not jwt_secret:
        logger.error(
            "JWT secret is not configured (set JWT_SECRET_KEY or JWT_SECRET). "
            "Refusing to sign or verify tokens."
        )
    return jwt_secret


def verify_token(token):
    """
    Verify JWT token and return payload with detailed error info.

    Args:
        token: JWT token string

    Returns:
        tuple: (payload, error_message) - payload is None if invalid
    """
    try:
        jwt_secret = _get_jwt_secret()
        if not jwt_secret:
            return None, "Authentication system configuration error. Please contact support."

        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=['HS256']
        )
        
        # Check if token is blacklisted
        redis_client = get_redis()
        if redis_client and redis_client.get(f"blacklist_{token}"):
            logger.warning(f"Blacklisted token used: {token[:20]}...")
            return None, "Your session has been terminated. Please login again."
        
        # Verify user still exists and is active
        db = get_db()
        if db is not None:
            user = db.users.find_one({
                'email': payload.get('email')
            })
            # ================================================================
            # ⚠️ BREAK-GLASS FLAG - ALLOW_DBLESS_PLATFORM_ADMIN ⚠️
            # SECURITY: A platform_admin JWT claim is NOT sufficient on its own.
            # The account must exist and be active in the DB. The DB-less bypass
            # below is gated behind this explicit, off-by-default flag and is
            # intended ONLY for emergency recovery (e.g. the admin account was
            # deleted). Leaving it enabled lets anyone holding a forged/stale
            # platform_admin JWT act as an admin without any DB-backed account.
            # Every use is logged at WARNING. Turn it off immediately after use.
            # ================================================================
            allow_dbless_admin = os.environ.get(
                'ALLOW_DBLESS_PLATFORM_ADMIN', 'false'
            ).strip().lower() in ('1', 'true', 'yes')

            if not user and allow_dbless_admin and RBAC.is_platform_admin(
                {'email': payload.get('email'), 'role': payload.get('role')}
            ):
                logger.warning(
                    "[SECURITY] DB-less platform admin bypass ENABLED via "
                    f"ALLOW_DBLESS_PLATFORM_ADMIN for {payload.get('email')}"
                )
            elif not user:
                logger.warning(f"Token for non-existent user: {payload.get('email')}")
                return None, "User account not found. Please contact support."
            elif user.get('status') == 'inactive':
                logger.warning(f"Token for inactive user: {payload.get('email')}")
                return None, "Your account has been deactivated. Please contact support."
        
        return payload, None
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None, "Your session has expired. Please login again."
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None, "Invalid authentication token. Please login again."
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None, "Authentication error. Please try again."

def require_auth(f):
    """
    Decorator to require authentication for routes.
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            # Access current user via g.current_user
            return jsonify(g.current_user)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        # Extract token. SECURITY: never log the Authorization header or full
        # token value - they are bearer credentials.
        try:
            parts = auth_header.split(' ')
            if len(parts) != 2:
                logger.warning(f"Invalid authorization header format - expected 2 parts, got {len(parts)}")
                return jsonify({'error': 'Invalid authorization header format - expected "Bearer <token>"'}), 401

            token = parts[1]  # Bearer <token>
        except IndexError:
            return jsonify({'error': 'Invalid authorization header format'}), 401

        # Verify token
        payload, error_msg = verify_token(token)
        if not payload:
            logger.warning(f"Token verification failed: {error_msg} - Token length: {len(token)}")
            return jsonify({
                'error': error_msg or 'Invalid authentication token',
                'error_code': 'AUTH_TOKEN_INVALID',
                'timestamp': datetime.utcnow().isoformat()
            }), 401

        # Expose the verified payload (e.g. session_start for refresh checks)
        g.token_payload = payload
        
        # Get full user data
        db = get_db()
        if db is not None:
            user = db.users.find_one(
                {'email': payload.get('email')},
                {'password': 0}  # Exclude password
            )
            if user:
                # Convert ObjectId to string
                user['_id'] = str(user['_id'])
                user['role'] = RBAC.canonicalize_role(user.get('role', 'user'))
                g.current_user = user
                g.user_id = user.get('_id')
                g.user_email = user['email']
                g.user_role = user['role']
                # Fix: Use 'organization' field from user record
                g.organization_id = user.get('organization_id') or user.get('organization')
            elif (
                os.environ.get('ALLOW_DBLESS_PLATFORM_ADMIN', 'false').strip().lower()
                in ('1', 'true', 'yes')
                and RBAC.is_platform_admin(
                    {'email': payload.get('email'), 'role': payload.get('role')}
                )
            ):
                # ============================================================
                # ⚠️ BREAK-GLASS ONLY - ALLOW_DBLESS_PLATFORM_ADMIN ⚠️
                # Platform admin synthesized from a JWT claim WITHOUT a matching
                # DB account is allowed solely when this explicit, off-by-default
                # flag is set. Anyone with a valid platform_admin JWT bypasses
                # the account-existence check while it is on. Disable right
                # after the emergency. Every use is logged at WARNING.
                # ============================================================
                logger.warning(
                    "[SECURITY] DB-less platform admin bypass ENABLED via "
                    f"ALLOW_DBLESS_PLATFORM_ADMIN for {payload.get('email')}"
                )
                g.current_user = {
                    'email': payload.get('email'),
                    'name': 'TESA Platform Admin',
                    'role': payload.get('role', 'platform_admin'),
                    'organization_id': 'tesa-platform',  # Separate from customer orgs
                    '_id': '507f1f77bcf86cd799439011'
                }
                g.user_email = payload.get('email')
                g.user_role = payload.get('role', 'platform_admin')
                g.organization_id = 'tesa-platform'
                g.user_id = g.current_user['_id']
            else:
                return jsonify({'error': 'User not found'}), 401
        else:
            # SECURITY: user database unavailable. We cannot verify the account
            # still exists or is active, so JWT role claims alone must NOT grant
            # privileged access - FAIL CLOSED for admin-class roles (503).
            canonical_role = RBAC.canonicalize_role(payload.get('role', 'user'))
            if canonical_role in PRIVILEGED_ROLES:
                logger.error(
                    "Rejecting privileged request (role=%s) for %s: user database "
                    "unavailable, cannot verify account (fail-closed)",
                    canonical_role, payload.get('email')
                )
                return jsonify({
                    'error': 'Authentication backend unavailable',
                    'message': 'Cannot verify privileged account while the user database is down',
                    'code': 'AUTH_BACKEND_UNAVAILABLE'
                }), 503

            # Non-privileged (read-only) user: minimal context from the verified
            # token so plain dashboard reads keep working during a DB blip.
            g.current_user = {
                '_id': payload.get('user_id'),
                'id': payload.get('user_id'),
                'email': payload.get('email'),
                'role': canonical_role,
                'organization_id': payload.get('organization_id')
            }
            g.user_id = payload.get('user_id')
            g.user_email = payload.get('email')
            g.user_role = canonical_role
            g.organization_id = payload.get('organization_id')

        return f(*args, **kwargs)
    
    return decorated_function

def require_role(allowed_roles):
    """
    Decorator to require specific roles for routes.
    
    Args:
        allowed_roles: List of allowed roles or single role string
        
    Usage:
        @app.route('/admin')
        @require_auth
        @require_role(['admin', 'organization_admin', 'platform_admin'])
        def admin_route():
            return jsonify({'message': 'Admin access granted'})
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user_role'):
                return jsonify({'error': 'Authentication required'}), 401
            
            if g.user_role not in allowed_roles:
                logger.warning(f"Access denied for role {g.user_role} to {request.path}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'required_roles': allowed_roles,
                    'current_role': g.user_role
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

def generate_token(user_data, expires_in=None, session_start=None):
    """
    Generate JWT token for user.

    Args:
        user_data: Dictionary with user information
        expires_in: Token expiration time in seconds (optional)
        session_start: Epoch seconds of the ORIGINAL login that started this
            session. Carried across refreshes so /auth/refresh can enforce an
            absolute session lifetime (MAX_SESSION_LIFETIME_HOURS) instead of
            an indefinite sliding window. Defaults to "now" (fresh login).

    Returns:
        str: JWT token
    """
    if expires_in is None:
        expires_in = current_app.config.get('TOKEN_EXPIRATION_HOURS', 24) * 3600

    jwt_secret = _get_jwt_secret()
    if not jwt_secret:
        raise ValueError("Authentication system configuration error")

    now = datetime.utcnow()
    payload = {
        'user_id': str(user_data.get('_id', user_data.get('user_id', user_data.get('id', '')))),
        'email': user_data.get('email'),
        'role': user_data.get('role', 'user'),
        'organization_id': user_data.get('organization_id'),
        'exp': now + timedelta(seconds=expires_in),
        'iat': now,
        'session_start': int(session_start) if session_start else int(now.timestamp())
    }

    token = jwt.encode(
        payload,
        jwt_secret,
        algorithm='HS256'
    )

    return token

def extract_api_key_from_request():
    """Extract the API key from headers (or query fallback), de-duplicated."""
    api_key = (
        request.headers.get('X-API-KEY') or
        request.headers.get('X-API-Key') or
        request.headers.get('X-Api-Key') or
        request.args.get('api_key')
    )
    # Handle duplicate headers that get concatenated with commas
    if api_key and ',' in api_key:
        api_key_parts = [part.strip() for part in api_key.split(',') if part.strip()]
        if api_key_parts:
            api_key = api_key_parts[0]
            logger.debug("API key header contained duplicates, using first value")
    return api_key


def validate_device_api_key(db, api_key):
    """Validate a tesa_dak_* device API key against hashed storage.

    Lookup order:
      1. device_auth collection (hashed, primary after Phase 7 Security)
      2. devices collection by prefix (hashed, backward compatibility)
      3. devices collection legacy PLAINTEXT field - on a successful match the
         record is migrated on-the-fly: the key is re-stored as a salted hash
         (api_key_security_service format) and the plaintext field is removed.

    Returns:
        dict | None: the active device document, or None when invalid.
    """
    from ..services.api_key_security_service import APIKeySecurityService

    api_key_prefix = APIKeySecurityService.extract_prefix(api_key)

    # 1) device_auth collection (hashed)
    device = None
    auth_record = db.device_auth.find_one({
        'api_key_prefix': api_key_prefix,
        'is_active': True
    })
    if auth_record and auth_record.get('api_key_hash') and \
            APIKeySecurityService.verify_api_key(api_key, auth_record['api_key_hash']):
        device = db.devices.find_one({
            'device_id': auth_record['device_id'],
            'status': 'active'
        })
        if device:
            logger.debug(f"Valid device API key (device_auth) for device {device.get('device_id')}")

    # 2) devices collection by prefix (hashed)
    if not device:
        device_by_prefix = db.devices.find_one({
            'api_key_prefix': api_key_prefix,
            'status': 'active'
        })
        if device_by_prefix:
            stored_hash = device_by_prefix.get('api_key_hash')
            if stored_hash and APIKeySecurityService.verify_api_key(api_key, stored_hash):
                device = device_by_prefix
                logger.debug(f"Valid device API key (devices) for device {device.get('device_id')}")

    # 3) Legacy plaintext fallback - migrate to hashed storage on first use.
    if not device:
        device = db.devices.find_one({
            'api_key': api_key,
            'status': 'active'
        })
        if device:
            logger.warning(
                "DEPRECATED: device %s authenticated with a legacy PLAINTEXT API "
                "key; migrating to hashed storage and removing the plaintext field.",
                device.get('device_id')
            )
            try:
                db.devices.update_one(
                    {'_id': device['_id']},
                    {
                        '$set': {
                            'api_key_hash': APIKeySecurityService.hash_api_key(api_key),
                            'api_key_prefix': api_key_prefix,
                            'api_key_migrated_at': datetime.utcnow(),
                        },
                        '$unset': {'api_key': ''}
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to migrate plaintext API key for device "
                    f"{device.get('device_id')}: {e}"
                )

    return device


def _lookup_standard_api_key(db, api_key):
    """Look up a standard (org/user) API key record in api_keys.

    Prefers SHA-256 hashed storage ('key_hash', the format api_key_service
    writes). Falls back to legacy PLAINTEXT 'key' records and migrates them to
    hashed storage on first successful use, removing the plaintext field.

    Returns:
        dict | None: the active, unexpired API key record.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    record = db.api_keys.find_one({
        'key_hash': key_hash,
        'status': 'active',
        'expires_at': {'$gt': datetime.utcnow()}
    })
    if record:
        return record

    # Legacy plaintext fallback - migrate on use.
    record = db.api_keys.find_one({
        'key': api_key,
        'status': 'active',
        'expires_at': {'$gt': datetime.utcnow()}
    })
    if record:
        logger.warning(
            "DEPRECATED: API key record %s matched by legacy PLAINTEXT value; "
            "migrating to hashed storage and removing the plaintext field.",
            record.get('_id')
        )
        try:
            db.api_keys.update_one(
                {'_id': record['_id']},
                {
                    '$set': {
                        'key_hash': key_hash,
                        'key_migrated_at': datetime.utcnow(),
                    },
                    '$unset': {'key': ''}
                }
            )
        except Exception as e:
            logger.error(f"Failed to migrate plaintext API key record {record.get('_id')}: {e}")
    return record


def _device_api_key_record(api_key, device):
    """Build the synthetic api_key context record for an authenticated device."""
    return {
        'type': 'device',
        'device_id': device.get('device_id'),
        'organization_id': device.get('organization_id'),
        'scopes': ['telemetry:write', 'device:read'],
        'owner_id': device.get('device_id'),
        'name': f"Device {device.get('name', device.get('device_id'))}",
        'permissions': ['device:telemetry:publish', 'device:status:update', 'device:config:read']
    }


def _validate_api_key_request(api_key, db):
    """Shared API key validation used by the API-key decorators.

    Returns:
        tuple: (api_key_record, error_response) - exactly one is set.
    """
    # Device API key (format: tesa_dak_*) - hashed verification
    if api_key.startswith('tesa_dak_'):
        device = validate_device_api_key(db, api_key)
        if device:
            api_key_record = _device_api_key_record(api_key, device)

            # Set device context
            g.device_id = device.get('device_id')
            g.device = device
            g.organization_id = device.get('organization_id')
            g.api_key_permissions = api_key_record['permissions']

            logger.debug(f"Device API key validated for device {device.get('device_id')}")
            return api_key_record, None

        logger.warning(f"Device not found for presented API key prefix: {api_key[:12]}...")
        return None, (jsonify({
            'error': 'Invalid or expired API key',
            'code': 'API_KEY_INVALID'
        }), 401)

    # New-format device API key (format: tesaiot_dev_*) - hashed in api_keys
    if api_key.startswith('tesaiot_dev_'):
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        api_key_record = db.api_keys.find_one({
            'key_hash': key_hash,
            'key_type': 'device_api_key',
            'status': 'active',
            'expires_at': {'$gt': datetime.utcnow()}
        })
        if api_key_record:
            logger.debug(f"Valid hashed device API key used for device {api_key_record.get('device_id')}")
            return api_key_record, None
        logger.warning(f"Hashed device API key not found or expired (prefix {api_key[:12]}...)")
        return None, (jsonify({
            'error': 'Invalid or expired API key',
            'code': 'API_KEY_INVALID'
        }), 401)

    # Standard API key (hashed-first lookup with plaintext migrate-on-use)
    api_key_record = _lookup_standard_api_key(db, api_key)
    if not api_key_record:
        logger.warning(f"Invalid or expired API key (prefix {api_key[:8]}...)")
        return None, (jsonify({
            'error': 'Invalid or expired API key',
            'code': 'API_KEY_INVALID'
        }), 401)
    return api_key_record, None


def require_api_key(f):
    """
    Decorator to require API key authentication for routes.

    This decorator expects the API key to be provided via:
    1. X-API-KEY header (preferred)
    2. X-API-Key header (alternative)
    3. api_key query parameter (fallback)

    Usage:
        @app.route('/api/endpoint')
        @require_api_key
        def api_endpoint():
            return jsonify({'message': 'Authenticated via API key'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for API key in headers
        api_key = extract_api_key_from_request()

        if not api_key:
            logger.warning(f"API key missing for {request.path}")
            return jsonify({
                'error': 'API key required',
                'message': 'Provide API key via X-API-KEY header',
                'code': 'API_KEY_MISSING'
            }), 401

        # Validate API key against database
        try:
            db = get_db()
            if db is None:
                # SECURITY: no database means no way to validate the key.
                # FAIL CLOSED (mirrors the mTLS registry-unavailable path)
                # instead of assuming an upstream gateway already validated it.
                logger.error("API key validation unavailable: database down (fail-closed)")
                return jsonify({
                    'error': 'Authentication unavailable',
                    'message': 'Unable to validate API key against the credential store',
                    'code': 'AUTH_BACKEND_UNAVAILABLE'
                }), 503

            api_key_record, error_response = _validate_api_key_request(api_key, db)
            if error_response:
                return error_response

            # Set API key context in g
            g.api_key = api_key_record
            g.api_key_owner = api_key_record.get('owner_id')
            g.api_key_scopes = api_key_record.get('scopes', [])

            # Update last used timestamp (standard keys only)
            if api_key_record.get('type') != 'device' and '_id' in api_key_record:
                db.api_keys.update_one(
                    {'_id': api_key_record['_id']},
                    {
                        '$set': {'last_used': datetime.utcnow()},
                        '$inc': {'usage_count': 1}
                    }
                )

            logger.debug(f"Valid API key used by {api_key_record.get('name', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return jsonify({
                'error': 'API key validation error',
                'code': 'API_KEY_VALIDATION_ERROR'
            }), 500

        return f(*args, **kwargs)

    return decorated_function

def authenticate_mtls_request():
    """Authenticate the current request via nginx-verified mTLS headers.

    mTLS device authentication (NON-SPOOFABLE):

    The X-Client-* request headers are trusted ONLY when X-Client-Verify
    == 'SUCCESS'. That header is produced by the mTLS terminator
    (config/nginx/conf.d/30-iot-mtls.conf) from nginx's $ssl_client_verify
    AFTER nginx performed a real TLS verify_peer of the client certificate
    against the Vault PKI CA bundle ("ssl_verify_client on"). nginx also
    unconditionally overwrites every X-Client-* header from its $ssl_client_*
    variables, so a client cannot forge them. Any request that did NOT
    traverse the mTLS listener arrives with X-Client-Verify == 'NONE'
    (the nginx default for non-mTLS server blocks) or absent, and is
    therefore rejected here. We FAIL CLOSED: in doubt, DENY.

    On success this sets the g.* device/cert context (g.device_id,
    g.auth_method='mtls', g.cert_* ...).

    Returns:
        tuple: (attempted, device, error_response)
          - attempted: True when the request presented mTLS headers at all
          - device: device document when authentication succeeded, else None
          - error_response: (flask_response, status_code) when attempted but
            failed; None otherwise
    """
    client_verify = (request.headers.get('X-Client-Verify') or '').strip()
    client_cert = request.headers.get('X-Client-Cert')

    # Treat the request as an mTLS attempt only if nginx asserted a verify
    # outcome. A bare X-Client-Cert with no verify result (or a non-SUCCESS
    # verify, e.g. FAILED/NONE) is NOT a valid device credential.
    mtls_attempted = bool(client_verify) or bool(client_cert)
    if not mtls_attempted:
        return False, None, None

    logger.info("mTLS authentication attempt; verify=%s", client_verify or 'MISSING')

    # 0) DEFENCE IN DEPTH: prove the request actually traversed the mTLS
    #    terminator before trusting ANY X-Client-* header.
    #
    #    The mTLS listener (config/nginx/conf.d/30-iot-mtls.conf) injects
    #    a non-guessable marker header X-MTLS-Gateway == MTLS_GATEWAY_SECRET
    #    ONLY after nginx has cryptographically verified the client
    #    certificate. Every other ingress (the serverTLS 443 block,
    #    APISIX, or a direct connection to the container) clears that
    #    header to empty. A request that did not come through the mTLS
    #    terminator therefore cannot present the correct marker, so even
    #    a perfectly forged "X-Client-Verify: SUCCESS" is rejected here.
    #
    #    FAIL CLOSED: if MTLS_GATEWAY_SECRET is not configured, header-
    #    based mTLS auth is disabled entirely (we cannot prove origin).
    gateway_secret = (os.environ.get('MTLS_GATEWAY_SECRET') or '').strip()
    # Treat the unmodified .env placeholder as "not configured": a known
    # public constant must never be accepted as the trusted marker, even
    # if an operator skipped generate-secrets.sh. Fail-closed.
    if gateway_secret == 'CHANGEME_MTLS_GATEWAY_SECRET':
        gateway_secret = ''
    presented_marker = (request.headers.get('X-MTLS-Gateway') or '').strip()
    marker_ok = bool(gateway_secret) and hmac.compare_digest(
        presented_marker, gateway_secret
    )
    if not marker_ok:
        if not gateway_secret:
            logger.error(
                "mTLS rejected: MTLS_GATEWAY_SECRET is not configured; "
                "refusing to honour X-Client-* headers (fail-closed) for %s",
                request.path
            )
        else:
            logger.warning(
                "mTLS rejected: missing/invalid X-MTLS-Gateway marker for %s; "
                "request did not traverse the verified mTLS terminator "
                "(possible header-forgery spoof)", request.path
            )
        return True, None, (jsonify({
            'error': 'Client certificate verification failed',
            'message': 'A valid, CA-verified client certificate is required',
            'code': 'MTLS_VERIFY_FAILED',
            'timestamp': datetime.utcnow().isoformat()
        }), 401)

    # 1) Require a successful peer-certificate verification by nginx.
    #    Anything other than the exact string 'SUCCESS' is rejected.
    if client_verify != 'SUCCESS':
        logger.warning(
            "mTLS rejected: X-Client-Verify=%r (expected 'SUCCESS') for %s",
            client_verify or 'MISSING', request.path
        )
        return True, None, (jsonify({
            'error': 'Client certificate verification failed',
            'message': 'A valid, CA-verified client certificate is required',
            'code': 'MTLS_VERIFY_FAILED',
            'timestamp': datetime.utcnow().isoformat()
        }), 401)

    try:
        # 2) Derive the verified identity from nginx-supplied, TLS-verified
        #    fields ONLY. Prefer the subject DN ($ssl_client_s_dn) and the
        #    serial ($ssl_client_serial); these come from the verified peer
        #    certificate, not from any client-controllable body.
        subject_dn = (request.headers.get('X-Client-S-DN') or '').strip()
        cert_serial = (request.headers.get('X-Client-Serial') or '').strip()
        cert_fingerprint = (request.headers.get('X-Client-Fingerprint') or '').strip()

        # Extract CN from the verified subject DN.
        common_name = None
        if 'CN=' in subject_dn:
            common_name = subject_dn.split('CN=', 1)[1].split(',', 1)[0].strip()

        if not common_name and not cert_serial:
            logger.warning(
                "mTLS rejected: verify=SUCCESS but no usable subject CN/serial (S-DN=%r)",
                subject_dn
            )
            return True, None, (jsonify({
                'error': 'Client certificate verification failed',
                'message': 'Verified certificate did not present a usable identity',
                'code': 'MTLS_NO_IDENTITY',
                'timestamp': datetime.utcnow().isoformat()
            }), 401)

        # 3) Bind the verified certificate to a registered device. The
        #    device certificate CN is the canonical device identity; the
        #    optional X-Device-ID / URL device id must be consistent with it.
        requested_device_id = request.headers.get('X-Device-ID')
        if not requested_device_id:
            path_parts = request.path.split('/')
            if 'devices' in path_parts:
                try:
                    device_idx = path_parts.index('devices')
                    if device_idx + 1 < len(path_parts):
                        requested_device_id = path_parts[device_idx + 1]
                except (ValueError, IndexError):
                    pass

        db = get_db()
        if db is None:
            # No registry to validate against -> cannot prove the cert maps
            # to a real, non-revoked device. FAIL CLOSED.
            logger.error("mTLS rejected: device registry unavailable, cannot validate certificate")
            return True, None, (jsonify({
                'error': 'Device authentication unavailable',
                'message': 'Unable to validate client certificate against device registry',
                'code': 'MTLS_REGISTRY_UNAVAILABLE',
                'timestamp': datetime.utcnow().isoformat()
            }), 503)

        # Match the verified cert to a device by CN (== device_id /
        # trustm_uid / cert_common_name) and/or serial number.
        lookup_or = []
        if common_name:
            lookup_or.extend([
                {'device_id': common_name},
                {'trustm_uid': common_name},
                {'cert_common_name': common_name},
                {'certificate_common_name': common_name},
            ])
        if cert_serial:
            lookup_or.append({'certificate_serial': cert_serial})

        device = db.devices.find_one({'$or': lookup_or}) if lookup_or else None

        if not device:
            logger.warning(
                "mTLS rejected: verified cert CN=%r serial=%r matches no registered device",
                common_name, cert_serial
            )
            return True, None, (jsonify({
                'error': 'Unknown device certificate',
                'message': 'Certificate is valid but is not registered to any device',
                'code': 'MTLS_DEVICE_NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 403)

        resolved_device_id = device.get('device_id')

        # 4) Enforce revocation: a device whose certificate has been
        #    revoked (Vault PKI revoke / admin revoke) must NOT authenticate,
        #    even if the cert is still cryptographically valid and unexpired.
        cert_status = (device.get('certificate_status') or '').lower()
        if cert_status in ('revoked', 'disabled', 'suspended'):
            logger.warning(
                "mTLS rejected: device %s certificate_status=%s",
                resolved_device_id, cert_status
            )
            return True, None, (jsonify({
                'error': 'Certificate revoked',
                'message': 'This device certificate has been revoked or disabled',
                'code': 'MTLS_CERT_REVOKED',
                'timestamp': datetime.utcnow().isoformat()
            }), 403)

        # 5) Defence in depth: if the device record pins a serial, the
        #    presented (verified) serial must match it.
        registered_serial = (device.get('certificate_serial') or '').strip()
        if registered_serial and cert_serial:
            if registered_serial.replace(':', '').lower() != cert_serial.replace(':', '').lower():
                logger.warning(
                    "mTLS rejected: serial mismatch for device %s (presented=%s registered=%s)",
                    resolved_device_id, cert_serial, registered_serial
                )
                return True, None, (jsonify({
                    'error': 'Certificate mismatch',
                    'message': 'Presented certificate does not match the registered device certificate',
                    'code': 'MTLS_SERIAL_MISMATCH',
                    'timestamp': datetime.utcnow().isoformat()
                }), 403)

        # 6) If a device id was requested (header/URL), it must resolve to
        #    the same device the certificate belongs to. Block lateral
        #    access to another device's resources.
        if requested_device_id and requested_device_id not in (
            resolved_device_id, device.get('trustm_uid'), common_name
        ):
            logger.warning(
                "mTLS rejected: cert for device %s attempted to act as %s",
                resolved_device_id, requested_device_id
            )
            return True, None, (jsonify({
                'error': 'Certificate/device mismatch',
                'message': 'Certificate identity does not match the requested device',
                'code': 'MTLS_IDENTITY_MISMATCH',
                'timestamp': datetime.utcnow().isoformat()
            }), 403)

        # Verified, registered, non-revoked device. Authenticate.
        logger.info("mTLS authentication successful for device: %s", resolved_device_id)
        g.auth_method = 'mtls'
        g.device_id = resolved_device_id
        g.device = device
        g.organization_id = device.get('organization_id')
        g.cert_common_name = common_name
        g.cert_serial = cert_serial or registered_serial or None
        g.cert_fingerprint = cert_fingerprint or None
        g.cert_subject_dn = subject_dn or None
        g.cert_validation = {'valid': True, 'verified_by': 'nginx_mtls'}
        if client_cert:
            g.client_cert = client_cert
        return True, device, None

    except Exception as cert_error:
        # FAIL CLOSED on any unexpected error during validation.
        logger.error(f"mTLS certificate processing error: {cert_error}")
        return True, None, (jsonify({
            'error': 'Certificate processing failed',
            'message': 'Unable to process client certificate',
            'code': 'CERT_PROCESSING_ERROR'
        }), 401)


def require_api_key_or_mtls(f):
    """
    Decorator to require either API key OR mTLS certificate authentication.

    This decorator accepts authentication via:
    1. X-API-KEY header (standard API key)
    2. nginx-verified mTLS headers gated by the X-MTLS-Gateway marker
       (see authenticate_mtls_request)

    Usage:
        @app.route('/api/endpoint')
        @require_api_key_or_mtls
        def api_endpoint():
            return jsonify({'message': 'Authenticated'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # mTLS device authentication (fail-closed; see authenticate_mtls_request)
        mtls_attempted, mtls_device, mtls_error = authenticate_mtls_request()
        if mtls_attempted:
            if mtls_error:
                return mtls_error
            return f(*args, **kwargs)

        # Fall back to API key authentication
        api_key = extract_api_key_from_request()

        if not api_key:
            logger.warning(f"No authentication provided for {request.path}")
            return jsonify({
                'error': 'Authentication required',
                'message': 'Provide API key via X-API-KEY header or use mTLS certificate',
                'code': 'AUTH_MISSING'
            }), 401

        # Validate API key against database
        try:
            db = get_db()
            if db is None:
                # SECURITY: no database means no way to validate the key.
                # FAIL CLOSED, mirroring the mTLS registry-unavailable path.
                logger.error("API key validation unavailable: database down (fail-closed)")
                return jsonify({
                    'error': 'Authentication unavailable',
                    'message': 'Unable to validate API key against the credential store',
                    'code': 'AUTH_BACKEND_UNAVAILABLE'
                }), 503

            api_key_record, error_response = _validate_api_key_request(api_key, db)
            if error_response:
                return error_response

            # Set API key context in g
            g.api_key = api_key_record
            g.api_key_owner = api_key_record.get('owner_id')
            g.api_key_scopes = api_key_record.get('scopes', [])
            g.auth_method = 'api_key'

            # Update last used timestamp (only for standard API keys, not device keys)
            if api_key_record.get('type') != 'device' and '_id' in api_key_record:
                db.api_keys.update_one(
                    {'_id': api_key_record['_id']},
                    {
                        '$set': {'last_used': datetime.utcnow()},
                        '$inc': {'usage_count': 1}
                    }
                )

            logger.debug("Valid API key authentication")

        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            return jsonify({
                'error': 'Authentication validation failed',
                'code': 'AUTH_ERROR'
            }), 500

        return f(*args, **kwargs)

    return decorated_function


def require_telemetry_ingest(f):
    """Authentication for telemetry-ingest endpoints.

    Accepts, in order:
      1. nginx-verified device mTLS (X-MTLS-Gateway marker) - binds g.device_id.
      2. A device/standard API key (X-API-KEY) - device keys bind g.device_id.
      3. A trusted SERVICE RELAY: a valid JWT whose role carries
         Permission.TELEMETRY_INGEST (e.g. the MQTT bridge's 'service'
         account). The relay does NOT set g.device_id, so the handler's
         "body device_id must equal the authenticated device" check is skipped
         and the relay may forward telemetry for any device. This is safe
         because device identity for relayed messages is established upstream
         at the EMQX ACL layer (each device may only publish to its own topic),
         and the relay holds only TELEMETRY_INGEST/DEVICE_UPDATE/DEVICE_VIEW.

    Fail-closed: anything else is 401/503. g.auth_method records which path
    authenticated the request.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Device mTLS (fail-closed; see authenticate_mtls_request)
        mtls_attempted, _mtls_device, mtls_error = authenticate_mtls_request()
        if mtls_attempted:
            if mtls_error:
                return mtls_error
            return f(*args, **kwargs)

        # 2. API key (device or standard) - reuses the shared validator that
        #    binds g.device_id for device keys.
        api_key = extract_api_key_from_request()
        if api_key:
            db = get_db()
            if db is None:
                logger.error("Telemetry auth unavailable: database down (fail-closed)")
                return jsonify({
                    'error': 'Authentication unavailable',
                    'code': 'AUTH_BACKEND_UNAVAILABLE'
                }), 503
            api_key_record, error_response = _validate_api_key_request(api_key, db)
            if error_response:
                return error_response
            g.api_key = api_key_record
            g.api_key_owner = api_key_record.get('owner_id')
            g.api_key_scopes = api_key_record.get('scopes', [])
            g.auth_method = 'api_key'
            if api_key_record.get('type') != 'device' and '_id' in api_key_record:
                db.api_keys.update_one(
                    {'_id': api_key_record['_id']},
                    {'$set': {'last_used': datetime.utcnow()}, '$inc': {'usage_count': 1}}
                )
            return f(*args, **kwargs)

        # 3. Trusted service relay via JWT bearing TELEMETRY_INGEST.
        from .rbac import Permission  # local import avoids a circular import
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split(' ')
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            payload, error_msg = verify_token(parts[1])
            if payload:
                role = RBAC.canonicalize_role(payload.get('role', 'user'))
                if RBAC.has_permission(role, Permission.TELEMETRY_INGEST):
                    g.auth_method = 'service_relay'
                    g.relay_user = payload.get('email')
                    g.relay_role = role
                    # Intentionally NOT setting g.device_id - relay submits for
                    # many devices.
                    return f(*args, **kwargs)
                logger.warning(
                    "Telemetry relay denied: role '%s' lacks TELEMETRY_INGEST", role
                )
                return jsonify({
                    'error': 'Insufficient permissions for telemetry ingest',
                    'code': 'AUTH_FORBIDDEN'
                }), 403

        logger.warning(f"No telemetry-ingest authentication provided for {request.path}")
        return jsonify({
            'error': 'Authentication required',
            'message': 'Provide a device API key, mTLS certificate, or a service-account token with telemetry ingest permission',
            'code': 'AUTH_MISSING'
        }), 401

    return decorated_function

def blacklist_token(token):
    """
    Add token to blacklist (for logout).
    
    Args:
        token: JWT token to blacklist
    """
    try:
        redis_client = get_redis()
        if redis_client:
            jwt_secret = _get_jwt_secret()

            # Decode to get expiration time
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=['HS256']
            )
            exp = payload.get('exp', 0)
            ttl = exp - datetime.utcnow().timestamp()
            
            if ttl > 0:
                redis_client.setex(
                    f"blacklist_{token}",
                    int(ttl),
                    "1"
                )
                logger.info(f"Token blacklisted for {ttl} seconds")
        else:
            logger.warning("Redis not available for token blacklisting")
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
