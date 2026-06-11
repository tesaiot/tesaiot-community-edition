# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Exception Definitions
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

class APIException(Exception):
    """Base exception class for API errors."""
    status_code = 500
    message = "An error occurred"
    
    def __init__(self, message=None, status_code=None, payload=None):
        final_message = message if message is not None else self.message
        super().__init__(final_message)
        self.message = final_message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        """Convert exception to dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv

class ValidationError(APIException):
    """Raised when request validation fails."""
    status_code = 400
    message = "Validation error"

class AuthenticationError(APIException):
    """Raised when authentication fails."""
    status_code = 401
    message = "Authentication required"

class AuthorizationError(APIException):
    """Raised when user lacks permission."""
    status_code = 403
    message = "Permission denied"

class NotFoundError(APIException):
    """Raised when resource is not found."""
    status_code = 404
    message = "Resource not found"

class ConflictError(APIException):
    """Raised when there's a conflict (e.g., duplicate)."""
    status_code = 409
    message = "Resource conflict"

class RateLimitError(APIException):
    """Raised when rate limit is exceeded."""
    status_code = 429
    message = "Rate limit exceeded"

class ServiceUnavailableError(APIException):
    """Raised when a service is unavailable."""
    status_code = 503
    message = "Service temporarily unavailable"

class ServiceError(APIException):
    """Raised when a service operation fails."""
    status_code = 500
    message = "Service operation failed"

class DatabaseError(APIException):
    """Raised when a database operation fails."""
    status_code = 500
    message = "Database operation failed"

class DuplicateResourceError(ConflictError):
    """Raised when attempting to create a duplicate resource."""
    status_code = 409
    message = "Resource already exists"

class BusinessLogicError(APIException):
    """Raised when business logic validation fails."""
    status_code = 422
    message = "Business logic validation failed"

# FastAPI-compatible alias for AuthenticationError
class UnauthorizedException(AuthenticationError):
    """Raised when authentication fails (FastAPI-compatible alias)."""
    pass


# Aliases for backward compatibility with module imports
ResourceNotFoundError = NotFoundError
ResourceNotFound = NotFoundError

def handle_api_exception(error):
    """Handle custom API exceptions."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    
    # Log the error
    if error.status_code >= 500:
        logger.error(f"API Error {error.status_code}: {error.message}", exc_info=True)
    else:
        logger.warning(f"API Error {error.status_code}: {error.message}")
    
    return response

def handle_http_exception(error):
    """Handle Werkzeug HTTP exceptions."""
    response = jsonify({
        'error': error.description,
        'status_code': error.code
    })
    response.status_code = error.code
    
    logger.warning(f"HTTP Error {error.code}: {error.description}")
    return response

def handle_generic_exception(error):
    """Handle unexpected exceptions."""
    logger.error("Unexpected error", exc_info=True)
    
    response = jsonify({
        'error': 'An unexpected error occurred',
        'status_code': 500
    })
    response.status_code = 500
    return response

def setup_error_handlers(app):
    """
    Setup error handlers for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Handle custom API exceptions
    app.register_error_handler(APIException, handle_api_exception)
    
    # Handle specific API exceptions
    for exc_class in [
        ValidationError, AuthenticationError, AuthorizationError,
        NotFoundError, ConflictError, RateLimitError, ServiceUnavailableError
    ]:
        app.register_error_handler(exc_class, handle_api_exception)
    
    # Handle Werkzeug HTTP exceptions
    app.register_error_handler(HTTPException, handle_http_exception)
    
    # Handle all other exceptions
    app.register_error_handler(Exception, handle_generic_exception)
    
    # CORS headers are now handled by flask-cors in __init__.py
    # This after_request handler is no longer needed as it can conflict
    
    logger.info("Error handlers configured")
