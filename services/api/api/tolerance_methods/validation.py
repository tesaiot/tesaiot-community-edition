# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""Input validation utilities."""

import re
from typing import Any, Optional


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password: str) -> bool:
    """Validate password strength."""
    if not password:
        return False
    
    # At least 8 characters
    if len(password) < 8:
        return False
    
    # Contains at least one uppercase, one lowercase, one digit
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit


def sanitize_string(value: Any, max_length: Optional[int] = None) -> str:
    """Sanitize string input with optional max length trimming."""
    if value is None:
        return ""
    
    # Convert to string
    value = str(value)

    # Truncate to requested maximum length when provided
    if max_length is not None:
        value = value[:max_length]
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    # Remove control characters
    value = ''.join(char for char in value if ord(char) >= 32)
    
    return value


def validate_device_id(device_id: str) -> bool:
    """Validate device ID format."""
    if not device_id:
        return False
    
    # Device ID should be alphanumeric with optional hyphens/underscores
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, device_id))


def validate_organization_name(name: str) -> bool:
    """Validate organization name."""
    if not name:
        return False
    
    # Organization name should be 2-100 characters
    return 2 <= len(name) <= 100
