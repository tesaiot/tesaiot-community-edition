# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Input Validation Utilities
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.

Input validation, rate limiting (Redis-backed with in-memory fallback),
trusted-proxy-aware client IP resolution, and SSRF-safe webhook URL checks.
"""

import re
import os
import socket
import logging
import ipaddress
from functools import wraps
from urllib.parse import urlparse
from flask import request, jsonify
from jsonschema import validate, draft7_format_checker
from typing import Dict, Any, Optional, List, Tuple
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

# In-memory rate limiting storage (fallback when Redis is unavailable)
login_attempts = defaultdict(list)
request_sizes = {}

# Security constants
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 900  # 15 minutes
MIN_PASSWORD_LENGTH = 8
MAX_FIELD_LENGTH = 1000
# The host part may be a dotted domain (user@example.com) OR a single-label
# host such as the self-host default `admin@localhost`. The TLD is therefore
# optional; the host must still start and end with an alphanumeric character.
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?$')
DEVICE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,64}$')

# ---------------------------------------------------------------------------
# Emergency rate-limit bypass (env-driven; defaults OFF)
#
# SECURITY: This used to be a hardcoded module constant. It is now driven by
# the RATE_LIMIT_EMERGENCY_BYPASS environment variable, defaults to disabled,
# and logs loudly (CRITICAL) on every bypassed check so it cannot be left on
# silently. Never enable in normal operation.
# ---------------------------------------------------------------------------
def _emergency_bypass_active() -> bool:
    active = os.getenv('RATE_LIMIT_EMERGENCY_BYPASS', 'false').strip().lower() in (
        '1', 'true', 'yes'
    )
    if active:
        logger.critical(
            "RATE_LIMIT_EMERGENCY_BYPASS is ENABLED - rate limiting is OFF. "
            "Disable this env var immediately after the emergency is resolved."
        )
    return active


# ---------------------------------------------------------------------------
# Trusted-proxy-aware client IP resolution
#
# X-Forwarded-For is attacker-controlled unless the direct TCP peer is a
# trusted reverse proxy. The API normally sits behind in-cluster nginx/APISIX,
# so the default trust list is loopback + RFC1918. Override via env:
#   TRUSTED_PROXY_IPS   - comma-separated IPs
#   TRUSTED_PROXY_CIDRS - comma-separated CIDRs
# ---------------------------------------------------------------------------
_DEFAULT_TRUSTED_PROXY_CIDRS = (
    '127.0.0.0/8', '::1/128', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'
)
_trusted_proxy_networks_cache: Optional[List] = None


def _get_trusted_proxy_networks() -> List:
    """Parse trusted proxy IPs/CIDRs from env (cached)."""
    global _trusted_proxy_networks_cache
    if _trusted_proxy_networks_cache is not None:
        return _trusted_proxy_networks_cache

    entries: List[str] = []
    for env_key in ('TRUSTED_PROXY_IPS', 'TRUSTED_PROXY_CIDRS'):
        raw = os.getenv(env_key, '')
        entries.extend(part.strip() for part in raw.split(',') if part.strip())
    if not entries:
        entries = list(_DEFAULT_TRUSTED_PROXY_CIDRS)

    networks = []
    for entry in entries:
        try:
            if '/' in entry:
                networks.append(ipaddress.ip_network(entry, strict=False))
            else:
                networks.append(ipaddress.ip_network(entry))
        except ValueError:
            logger.warning(f"Ignoring invalid trusted proxy entry: {entry!r}")
    _trusted_proxy_networks_cache = networks
    return networks


def _is_trusted_proxy(ip_str: str) -> bool:
    """Check whether an IP belongs to the trusted proxy set."""
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except (ValueError, AttributeError):
        return False
    return any(addr in net for net in _get_trusted_proxy_networks())


def get_client_ip() -> str:
    """Resolve the real client IP for rate limiting / audit.

    X-Forwarded-For is honoured ONLY when the direct peer (request.remote_addr)
    is a trusted proxy. The chain is walked right-to-left, skipping trusted
    proxy hops; the first untrusted hop is the client. This prevents spoofed
    XFF headers from rotating rate-limit buckets.
    """
    remote = (request.remote_addr or '').strip()
    if not remote or not _is_trusted_proxy(remote):
        return remote or 'unknown'

    xff = request.headers.get('X-Forwarded-For', '')
    hops = [h.strip() for h in xff.split(',') if h.strip()]
    for hop in reversed(hops):
        if not _is_trusted_proxy(hop):
            return hop
    if hops:
        # Entire chain is trusted proxies; leftmost entry is the origin.
        return hops[0]
    real_ip = request.headers.get('X-Real-IP', '').strip()
    return real_ip or remote

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)

class SecurityError(Exception):
    """Security-related error"""
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)

def validate_email(email: str) -> bool:
    """
    Validate email format with comprehensive checks.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
        
    if len(email) > 254:  # RFC 5321 limit
        return False
        
    if not EMAIL_REGEX.match(email):
        return False
        
    # Additional checks
    local, domain = email.rsplit('@', 1)
    if len(local) > 64:  # RFC 5321 limit for local part
        return False
        
    if '..' in email:  # No consecutive dots
        return False
        
    return True

def validate_password(password: str):
    """
    Validate password strength with comprehensive requirements.
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
        
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
        
    if len(password) > 128:  # Reasonable upper limit
        return False, "Password is too long"
        
    # Check for complexity
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    if not (has_upper and has_lower and has_digit and has_special):
        return False, "Password must contain uppercase, lowercase, digit, and special character"
        
    # Check for common patterns
    if password.lower() in ['password', '12345678', 'qwerty123', 'admin123']:
        return False, "Password is too common"
        
    return True, ""

def validate_device_id(device_id: str) -> bool:
    """
    Validate device ID format.
    
    Args:
        device_id: Device ID to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not device_id or not isinstance(device_id, str):
        return False
        
    return bool(DEVICE_ID_REGEX.match(device_id))

def sanitize_string(value: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    """
    Sanitize string input to prevent XSS and injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized string
    """
    if not isinstance(value, str):
        return str(value)
        
    # Truncate to max length
    value = value[:max_length]
    
    # Remove null bytes and control characters
    value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
    
    # Basic HTML escaping
    value = value.replace('&', '&amp;')
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&#x27;')
    
    return value.strip()

def _get_rate_limit_redis():
    """Best-effort Redis client for rate-limit counters.

    Used when ENABLE_REDIS_CACHE is on (default) or REDIS_HOST/REDIS_URL is
    configured. Returns None on any failure so callers fall back to the
    in-memory store (interface preserved).
    """
    enabled = os.getenv('ENABLE_REDIS_CACHE', 'true').strip().lower() in ('1', 'true', 'yes')
    if not enabled and not (os.getenv('REDIS_HOST') or os.getenv('REDIS_URL')):
        return None
    try:
        # Lazy import to avoid circular imports at module load time.
        from ..core.database import get_redis
        return get_redis()
    except Exception:
        return None


def check_rate_limit_status(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS,
                            window_seconds: int = LOGIN_ATTEMPT_WINDOW) -> Tuple[bool, int]:
    """
    Check whether an identifier has exceeded its rate limit.

    Uses Redis counters when available (shared across workers/restarts) and
    falls back to the in-memory store otherwise.

    Args:
        identifier: IP address or user identifier
        max_attempts: Maximum attempts allowed
        window_seconds: Time window in seconds

    Returns:
        tuple: (allowed, retry_after_seconds). retry_after_seconds is the
        number of seconds until the window resets (0 when allowed).
    """
    if _emergency_bypass_active():
        return True, 0

    # Redis-backed fixed-window counter (preferred)
    redis_client = _get_rate_limit_redis()
    if redis_client is not None:
        try:
            key = f"tesa:ratelimit:{identifier}"
            count = redis_client.incr(key)
            if count == 1:
                redis_client.expire(key, window_seconds)
            if count > max_attempts:
                ttl = redis_client.ttl(key)
                if ttl is None or ttl < 0:
                    # Key lost its TTL (e.g. INCR after expiry race) - reset it.
                    redis_client.expire(key, window_seconds)
                    ttl = window_seconds
                return False, max(1, int(ttl))
            return True, 0
        except Exception as e:
            logger.warning(f"Redis rate limit check failed, using in-memory fallback: {e}")

    # In-memory sliding-window fallback
    current_time = time.time()
    login_attempts[identifier] = [
        attempt_time for attempt_time in login_attempts[identifier]
        if current_time - attempt_time < window_seconds
    ]

    if len(login_attempts[identifier]) >= max_attempts:
        oldest = min(login_attempts[identifier])
        retry_after = int(window_seconds - (current_time - oldest)) + 1
        return False, max(1, retry_after)

    login_attempts[identifier].append(current_time)
    return True, 0


def is_rate_limited(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS,
                    window_seconds: int = LOGIN_ATTEMPT_WINDOW) -> Tuple[bool, int]:
    """Peek at the rate-limit state WITHOUT recording an attempt.

    Used e.g. for account lockout, where only FAILED attempts are recorded
    (via check_rate_limit_status) but every login must first check the state.

    Returns:
        tuple: (limited, retry_after_seconds)
    """
    if _emergency_bypass_active():
        return False, 0

    redis_client = _get_rate_limit_redis()
    if redis_client is not None:
        try:
            key = f"tesa:ratelimit:{identifier}"
            raw = redis_client.get(key)
            count = int(raw) if raw else 0
            if count >= max_attempts:
                ttl = redis_client.ttl(key)
                if ttl is None or ttl < 0:
                    ttl = window_seconds
                return True, max(1, int(ttl))
            return False, 0
        except Exception as e:
            logger.warning(f"Redis rate limit peek failed, using in-memory fallback: {e}")

    current_time = time.time()
    attempts = [
        attempt_time for attempt_time in login_attempts.get(identifier, [])
        if current_time - attempt_time < window_seconds
    ]
    if len(attempts) >= max_attempts:
        retry_after = int(window_seconds - (current_time - min(attempts))) + 1
        return True, max(1, retry_after)
    return False, 0


def reset_rate_limit(identifier: str):
    """Clear the rate-limit counter for an identifier (e.g. after success)."""
    try:
        redis_client = _get_rate_limit_redis()
        if redis_client is not None:
            redis_client.delete(f"tesa:ratelimit:{identifier}")
    except Exception:
        pass
    login_attempts.pop(identifier, None)


def check_rate_limit(identifier: str, max_attempts: int = MAX_LOGIN_ATTEMPTS,
                    window_seconds: int = LOGIN_ATTEMPT_WINDOW) -> bool:
    """
    Check if identifier has exceeded rate limit (boolean compatibility wrapper).

    Args:
        identifier: IP address or user identifier
        max_attempts: Maximum attempts allowed
        window_seconds: Time window in seconds

    Returns:
        bool: True if within limits, False if exceeded
    """
    allowed, _ = check_rate_limit_status(identifier, max_attempts, window_seconds)
    return allowed


def rate_limit_response(message: str, retry_after_seconds: int,
                        code: str = 'RATE_LIMIT_EXCEEDED'):
    """Build a 429 response with a Retry-After header and retry_after_seconds.

    Project rule: every 429 MUST tell the client when to retry, not just
    "try again later".
    """
    retry_after = max(1, int(retry_after_seconds or 1))
    response = jsonify({
        'error': f"{message} Retry after {retry_after} seconds.",
        'code': code,
        'retry_after_seconds': retry_after
    })
    response.headers['Retry-After'] = str(retry_after)
    return response, 429


# ---------------------------------------------------------------------------
# SSRF-safe webhook URL validation
# ---------------------------------------------------------------------------
def validate_webhook_url(url: str) -> Tuple[bool, str]:
    """Validate an outbound (admin-configured) webhook URL against SSRF.

    Enforces http(s) scheme and resolves the hostname, rejecting loopback,
    link-local (incl. the cloud metadata IP 169.254.169.254), private,
    multicast, reserved and unspecified addresses unless the deployment
    explicitly opts in via ALLOW_PRIVATE_WEBHOOKS=true (default false).

    Returns:
        tuple: (ok, reason)
    """
    if not url or not isinstance(url, str):
        return False, 'Webhook URL is empty'

    try:
        parsed = urlparse(url)
    except Exception:
        return False, 'Webhook URL could not be parsed'

    if parsed.scheme not in ('http', 'https'):
        return False, f'Unsupported webhook URL scheme: {parsed.scheme!r}'
    hostname = parsed.hostname
    if not hostname:
        return False, 'Webhook URL has no hostname'

    allow_private = os.getenv('ALLOW_PRIVATE_WEBHOOKS', 'false').strip().lower() in (
        '1', 'true', 'yes'
    )
    if allow_private:
        return True, ''

    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        return False, f'Webhook hostname did not resolve: {e}'

    for info in addr_infos:
        ip_str = info[4][0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f'Webhook resolved to invalid address: {ip_str}'
        if (
            addr.is_loopback or addr.is_link_local or addr.is_private
            or addr.is_multicast or addr.is_reserved or addr.is_unspecified
            or ip_str == '169.254.169.254'
        ):
            return False, (
                f'Webhook resolves to a disallowed address ({ip_str}); '
                'set ALLOW_PRIVATE_WEBHOOKS=true to permit internal targets'
            )

    return True, ''

def validate_request_size(max_size: int = MAX_REQUEST_SIZE):
    """
    Decorator to validate request content length.
    
    Args:
        max_size: Maximum allowed request size in bytes
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            if content_length and content_length > max_size:
                logger.warning(f"Request size {content_length} exceeds limit {max_size}")
                return jsonify({
                    'error': 'Request too large',
                    'code': 'REQUEST_TOO_LARGE'
                }), 413
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def normalize_device_data(data):
    """
    Normalize device data for case-insensitive handling
    """
    if not data:
        return data
    
    # Create a deep copy to avoid modifying the original
    import copy
    normalized_data = copy.deepcopy(data)
    
    # Normalize auth_mode to lowercase
    if 'auth_mode' in normalized_data:
        normalized_data['auth_mode'] = normalized_data['auth_mode'].lower()
    
    # Normalize protocol in metadata to lowercase
    if 'metadata' in normalized_data and isinstance(normalized_data['metadata'], dict):
        if 'protocol' in normalized_data['metadata']:
            normalized_data['metadata']['protocol'] = normalized_data['metadata']['protocol'].lower()
    
    return normalized_data

def validate_json_schema(schema: Dict[str, Any]):
    """
    Decorator to validate JSON request against schema.
    
    Args:
        schema: JSON Schema definition
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    return jsonify({
                        'error': 'Invalid JSON or no data provided',
                        'code': 'INVALID_JSON'
                    }), 400
                    
                validate(data, schema, format_checker=draft7_format_checker)
                return f(*args, **kwargs)
                
            except ValidationError as e:
                logger.warning(f"JSON schema validation failed: {e.message}")
                return jsonify({
                    'error': 'Invalid request data',
                    'details': e.message,
                    'code': 'SCHEMA_VALIDATION_FAILED'
                }), 400
            except Exception as e:
                logger.error(f"Schema validation error: {e}")
                return jsonify({
                    'error': 'Validation error',
                    'code': 'VALIDATION_ERROR'
                }), 400
                
        return decorated_function
    return decorator

def validate_input(**field_validators):
    """
    Decorator to validate individual input fields.
    
    Args:
        **field_validators: Dict of field_name -> validator_function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json() or {}
                errors = {}
                
                for field_name, validator in field_validators.items():
                    if field_name in data:
                        try:
                            result = validator(data[field_name])
                            if isinstance(result, tuple) and not result[0]:
                                errors[field_name] = result[1]
                            elif result is False:
                                errors[field_name] = f"Invalid {field_name}"
                        except Exception as e:
                            errors[field_name] = str(e)
                
                if errors:
                    return jsonify({
                        'error': 'Validation failed',
                        'field_errors': errors,
                        'code': 'FIELD_VALIDATION_FAILED'
                    }), 400
                    
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Input validation error: {e}")
                return jsonify({
                    'error': 'Validation error',
                    'code': 'VALIDATION_ERROR'
                }), 400
                
        return decorated_function
    return decorator

def validate_auth_request():
    """
    Decorator specifically for authentication request validation.
    Includes rate limiting, email/password validation, and security checks.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = 'unknown'
            try:
                # Get client IP (trusted-proxy aware; spoofed XFF is ignored)
                client_ip = get_client_ip()

                # Check rate limiting (per-IP)
                allowed, retry_after = check_rate_limit_status(f"auth_ip:{client_ip}")
                if not allowed:
                    logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                    return rate_limit_response(
                        'Too many login attempts.', retry_after
                    )
                
                # Validate request size
                if request.content_length and request.content_length > MAX_REQUEST_SIZE:
                    return jsonify({
                        'error': 'Request too large',
                        'code': 'REQUEST_TOO_LARGE'
                    }), 413
                
                # Check Content-Type header
                content_type = request.headers.get('Content-Type', '').lower()
                if not content_type.startswith('application/json'):
                    return jsonify({
                        'error': 'Content-Type must be application/json',
                        'code': 'INVALID_CONTENT_TYPE'
                    }), 400
                
                # Get and validate JSON data with proper error handling
                try:
                    data = request.get_json(force=False, silent=False)
                except Exception as json_error:
                    logger.warning(f"JSON parsing failed from IP {client_ip}: {json_error}")
                    return jsonify({
                        'error': 'Invalid JSON format in request body',
                        'code': 'MALFORMED_JSON'
                    }), 400
                
                if not data:
                    return jsonify({
                        'error': 'Request body is empty or contains no valid JSON data',
                        'code': 'EMPTY_REQUEST_BODY'
                    }), 400
                
                # Validate required fields
                email = data.get('email', '').strip().lower()
                password = data.get('password', '')
                
                if not email or not password:
                    return jsonify({
                        'error': 'Email and password are required',
                        'code': 'MISSING_CREDENTIALS'
                    }), 400
                
                # Validate email format
                if not validate_email(email):
                    return jsonify({
                        'error': 'Invalid email format',
                        'field': 'email',
                        'code': 'INVALID_EMAIL'
                    }), 400
                
                # Validate password strength for registration/reset
                if request.endpoint in ['auth.register', 'auth.reset_password']:
                    is_valid, error_msg = validate_password(password)
                    if not is_valid:
                        return jsonify({
                            'error': error_msg,
                            'field': 'password',
                            'code': 'INVALID_PASSWORD'
                        }), 400
                
                # Sanitize email for security
                data['email'] = sanitize_string(email, 254)
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Authentication validation error from IP {client_ip}: {str(e)}")
                
                # Provide more specific error messages for common issues
                error_str = str(e).lower()
                if 'json' in error_str or 'parse' in error_str:
                    return jsonify({
                        'error': 'Invalid JSON format in request',
                        'code': 'JSON_PARSE_ERROR'
                    }), 400
                elif 'content-type' in error_str:
                    return jsonify({
                        'error': 'Invalid or missing Content-Type header',
                        'code': 'CONTENT_TYPE_ERROR'
                    }), 400
                else:
                    return jsonify({
                        'error': 'Authentication validation failed',
                        'code': 'AUTH_VALIDATION_ERROR'
                    }), 400
                
        return decorated_function
    return decorator

def validate_device_request():
    """
    Decorator for device-related request validation.
    Validates device IDs, names, and telemetry data.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Validate request size
                if request.content_length and request.content_length > MAX_REQUEST_SIZE:
                    return jsonify({
                        'error': 'Request too large',
                        'code': 'REQUEST_TOO_LARGE'
                    }), 413
                
                # For routes with device_id parameter
                device_id = kwargs.get('device_id')
                if device_id and not validate_device_id(device_id):
                    return jsonify({
                        'error': 'Invalid device ID format',
                        'code': 'INVALID_DEVICE_ID'
                    }), 400
                
                # For POST/PUT requests, validate JSON data
                if request.method in ['POST', 'PUT']:
                    data = request.get_json()
                    if not data:
                        return jsonify({
                            'error': 'Invalid JSON or no data provided',
                            'code': 'INVALID_JSON'
                        }), 400
                    
                    # Validate device name if present
                    if 'name' in data:
                        name = data['name']
                        if not isinstance(name, str) or not name.strip():
                            return jsonify({
                                'error': 'Device name must be a non-empty string',
                                'field': 'name',
                                'code': 'INVALID_DEVICE_NAME'
                            }), 400
                        
                        # Sanitize device name
                        data['name'] = sanitize_string(name, 100)
                    
                    # Validate device_id if present in data
                    if 'device_id' in data:
                        if not validate_device_id(data['device_id']):
                            return jsonify({
                                'error': 'Invalid device ID format',
                                'field': 'device_id',
                                'code': 'INVALID_DEVICE_ID'
                            }), 400
                    
                    # Validate telemetry data structure for ingest endpoints
                    if 'telemetry/ingest' in request.path and 'data' in data:
                        telemetry_data = data['data']
                        if not isinstance(telemetry_data, dict):
                            return jsonify({
                                'error': 'Telemetry data must be an object',
                                'field': 'data',
                                'code': 'INVALID_TELEMETRY_DATA'
                            }), 400
                        
                        # Validate telemetry values
                        for key, value in telemetry_data.items():
                            if not isinstance(key, str) or len(key) > 50:
                                return jsonify({
                                    'error': f'Invalid telemetry key: {key}',
                                    'code': 'INVALID_TELEMETRY_KEY'
                                }), 400
                            
                            # Sanitize key
                            clean_key = sanitize_string(key, 50)
                            if clean_key != key:
                                telemetry_data[clean_key] = telemetry_data.pop(key)
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Device validation error: {e}")
                return jsonify({
                    'error': 'Device validation failed',
                    'code': 'DEVICE_VALIDATION_ERROR'
                }), 400
                
        return decorated_function
    return decorator

# JSON Schema definitions for common requests
LOGIN_SCHEMA = {
    "type": "object",
    "properties": {
        "email": {
            "type": "string",
            "format": "email",
            "maxLength": 254
        },
        "password": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128
        }
    },
    "required": ["email", "password"],
    "additionalProperties": False
}

DEVICE_CREATE_SCHEMA = {
    "type": "object",
    "properties": {
        "device_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9_-]{3,64}$"
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
        },
        "type": {
            "type": "string",
            "maxLength": 50
        },
        "location": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "minimum": -90, "maximum": 90},
                "lng": {"type": "number", "minimum": -180, "maximum": 180}
            }
        },
        "auth_mode": {
            "type": "string",
            "enum": [
                "mtls",
                "server_tls",
                "optiga_trust_mtls",
                "MTLS",
                "SERVER_TLS",
                "mTLS",
                "OPTIGA_TRUST_MTLS"
            ]
        },
        "metadata": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string",
                    "enum": ["mqtts", "https", "MQTTS", "HTTPS"]  
                },
                "network_type": {
                    "type": "string",
                    "enum": ["nbiot", "lorawan", "wifi", "cellular", "bluetooth", "zigbee", "modbus", "opcua", "matter"]
                },
                "manufacturer": {"type": "string"},
                "model": {"type": "string"},
                "ipAddress": {"type": "string"},
                "macAddress": {"type": "string"},
                "devicePicture": {"type": ["string", "null"]},
                "industry": {"type": "string"},
                "industrySpecificData": {"type": ["object", "null"]}
            }
        }
    },
    "required": ["name"],
    "additionalProperties": True
}

TELEMETRY_INGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "minProperties": 1
        },
        "metadata": {
            "type": "object"
        }
    },
    "required": ["data"],
    "additionalProperties": True
}

# Loud boot-time notice if the env-driven emergency bypass is enabled.
if os.getenv('RATE_LIMIT_EMERGENCY_BYPASS', 'false').strip().lower() in ('1', 'true', 'yes'):
    logger.critical(
        "RATE_LIMIT_EMERGENCY_BYPASS=true - ALL rate limiting is disabled. "
        "This must only be used during an emergency and turned off immediately after."
    )
