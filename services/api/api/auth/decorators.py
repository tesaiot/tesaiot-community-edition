# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Authentication and Authorization Decorators
Re-exports and extends decorators from core.auth for module compatibility.
"""

import functools
import logging
from typing import List, Callable
from flask import request, jsonify, g

# Re-export from core.auth
from ..core.auth import require_auth, verify_token

logger = logging.getLogger(__name__)


def require_permissions(permissions: List[str]):
    """
    Decorator to check if user has required permissions.

    Args:
        permissions: List of required permission names

    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # Get user from request context (set by require_auth)
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({'error': 'Authentication required'}), 401

            # Check permissions
            user_permissions = user.get('permissions', [])
            user_roles = user.get('roles', [])

            # Admin bypass
            if 'admin' in user_roles or 'super_admin' in user_roles:
                return f(*args, **kwargs)

            # Check if user has all required permissions
            missing = [p for p in permissions if p not in user_permissions]
            if missing:
                logger.warning(f"User {user.get('id')} missing permissions: {missing}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'required': permissions,
                    'missing': missing
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_device_access(device_id_param: str = 'device_id'):
    """
    Decorator to check if user has access to a specific device.

    Args:
        device_id_param: Name of the parameter containing device_id

    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # Get user from request context
            user = getattr(g, 'current_user', None)
            if not user:
                return jsonify({'error': 'Authentication required'}), 401

            # Get device_id from kwargs or request
            device_id = kwargs.get(device_id_param) or request.view_args.get(device_id_param)

            if not device_id:
                return jsonify({'error': 'Device ID required'}), 400

            # Admin bypass
            user_roles = user.get('roles', [])
            if 'admin' in user_roles or 'super_admin' in user_roles:
                return f(*args, **kwargs)

            # Check device access
            # For now, allow access if user owns the device or has device:read permission
            user_devices = user.get('devices', [])
            user_permissions = user.get('permissions', [])
            org_id = user.get('org_id')

            # Check ownership or organization access
            if (device_id in user_devices or
                'device:read:all' in user_permissions or
                'device:admin' in user_permissions):
                return f(*args, **kwargs)

            logger.warning(f"User {user.get('id')} denied access to device {device_id}")
            return jsonify({
                'error': 'Access denied to device',
                'device_id': device_id
            }), 403

        return decorated_function
    return decorator


def optional_auth(f: Callable) -> Callable:
    """
    Decorator that attempts authentication but doesn't require it.
    Sets g.current_user if token is valid, otherwise leaves it as None.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        g.current_user = None

        # Try to get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                user_data = verify_token(token)
                if user_data:
                    g.current_user = user_data
            except Exception:
                pass  # Token invalid, continue as unauthenticated

        return f(*args, **kwargs)
    return decorated_function


def rate_limit(max_requests: int = 100, window_seconds: int = 60):
    """
    Simple rate limiting decorator.

    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        Decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # For now, just pass through - rate limiting should be handled by gateway
            # This is a placeholder for future implementation
            return f(*args, **kwargs)
        return decorated_function
    return decorator
