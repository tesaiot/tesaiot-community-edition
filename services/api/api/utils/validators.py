# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Request Validation Utilities
"""

from typing import Any, Dict, List, Optional


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


def validate_uuid(value: str, field_name: str = "id") -> str:
    """Validate UUID format"""
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    if not uuid_pattern.match(value):
        raise ValueError(f"Invalid UUID format for {field_name}")
    return value


def validate_email(value: str) -> str:
    """Validate email format"""
    import re
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(value):
        raise ValueError("Invalid email format")
    return value


def validate_pagination(page: int = 1, page_size: int = 20, max_page_size: int = 100):
    """Validate pagination parameters"""
    if page < 1:
        raise ValueError("Page must be >= 1")
    if page_size < 1:
        raise ValueError("Page size must be >= 1")
    if page_size > max_page_size:
        raise ValueError(f"Page size cannot exceed {max_page_size}")
    return page, page_size
