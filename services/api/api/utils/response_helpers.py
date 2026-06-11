# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Response Helper Utilities
Standard response formatting for API endpoints.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: The response data
        message: Success message
        status_code: HTTP status code
        meta: Optional metadata

    Returns:
        Formatted response dictionary
    """
    response = {
        "success": True,
        "message": message,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat()
    }

    if data is not None:
        response["data"] = data

    if meta:
        response["meta"] = meta

    return response


def error_response(
    message: str = "An error occurred",
    error_code: Optional[str] = None,
    status_code: int = 500,
    details: Optional[Union[str, List[str], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        message: Error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error details

    Returns:
        Formatted error response dictionary
    """
    response = {
        "success": False,
        "error": {
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    if error_code:
        response["error"]["code"] = error_code

    if details:
        response["error"]["details"] = details

    return response


def paginated_response(
    data: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "Success"
) -> Dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        data: List of items for the current page
        total: Total number of items
        page: Current page number
        page_size: Number of items per page
        message: Success message

    Returns:
        Formatted paginated response dictionary
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        },
        "timestamp": datetime.utcnow().isoformat()
    }


def validation_error_response(
    errors: Union[List[Dict[str, str]], Dict[str, List[str]]],
    message: str = "Validation failed"
) -> Dict[str, Any]:
    """
    Create a standardized validation error response.

    Args:
        errors: Validation errors (list of field errors or dict of field->errors)
        message: Error message

    Returns:
        Formatted validation error response
    """
    return {
        "success": False,
        "error": {
            "message": message,
            "code": "VALIDATION_ERROR",
            "status_code": 422,
            "validation_errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
