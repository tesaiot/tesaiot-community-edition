# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Common Utility Functions for TESA IoT Platform
"""

import logging
from typing import Dict, Any, Optional, List
from flask import request
from datetime import datetime

logger = logging.getLogger(__name__)


def get_client_info() -> Dict[str, Any]:
    """
    Extract client information from the current request.

    Returns:
        Dictionary containing client information such as IP, user agent, etc.
    """
    client_info = {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'timestamp': datetime.utcnow().isoformat(),
        'method': request.method,
        'path': request.path,
        'content_type': request.content_type
    }

    # Try to get real IP from proxy headers
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain (client IP)
        client_info['ip_address'] = forwarded_for.split(',')[0].strip()
        client_info['forwarded_for'] = forwarded_for

    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        client_info['real_ip'] = real_ip

    return client_info


def validate_request_data(
    data: Dict[str, Any],
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None,
    field_types: Optional[Dict[str, type]] = None
) -> Dict[str, Any]:
    """
    Validate request data against required and optional fields.

    Args:
        data: The request data dictionary to validate
        required_fields: List of required field names
        optional_fields: List of optional field names (if provided, extra fields are rejected)
        field_types: Optional dictionary mapping field names to expected types

    Returns:
        Validated and sanitized data dictionary

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(data, dict):
        raise ValueError("Request data must be a dictionary")

    errors = []
    validated = {}

    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Required field cannot be null: {field}")
        else:
            validated[field] = data[field]

    # Check optional fields
    if optional_fields is not None:
        allowed_fields = set(required_fields) | set(optional_fields)
        for field in data:
            if field not in allowed_fields:
                errors.append(f"Unknown field: {field}")
            elif field in optional_fields and data[field] is not None:
                validated[field] = data[field]
    else:
        # Accept all extra fields if optional_fields not specified
        for field in data:
            if field not in validated:
                validated[field] = data[field]

    # Type checking
    if field_types:
        for field, expected_type in field_types.items():
            if field in validated and validated[field] is not None:
                if not isinstance(validated[field], expected_type):
                    errors.append(
                        f"Field '{field}' must be of type {expected_type.__name__}, "
                        f"got {type(validated[field]).__name__}"
                    )

    if errors:
        raise ValueError("; ".join(errors))

    return validated


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string value for safe storage and display.

    Args:
        value: The string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        value = str(value)

    # Truncate if too long
    if len(value) > max_length:
        value = value[:max_length]

    # Remove null bytes and control characters (except newlines and tabs)
    value = ''.join(
        char for char in value
        if char in '\n\t' or (ord(char) >= 32 and ord(char) != 127)
    )

    return value.strip()


def format_response(
    data: Any = None,
    message: str = None,
    success: bool = True,
    status_code: int = 200,
    meta: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Format a standard API response.

    Args:
        data: The response data
        message: Optional message
        success: Whether the operation was successful
        status_code: HTTP status code
        meta: Optional metadata

    Returns:
        Formatted response dictionary
    """
    response = {
        'success': success,
        'status_code': status_code,
        'timestamp': datetime.utcnow().isoformat()
    }

    if message:
        response['message'] = message

    if data is not None:
        response['data'] = data

    if meta:
        response['meta'] = meta

    return response
