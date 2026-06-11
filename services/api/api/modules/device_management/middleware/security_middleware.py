# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Security middleware for device management

This module provides middleware components for device authentication,
rate limiting, security headers, and threat detection.
"""

import logging
import time
from typing import Optional, Callable
from datetime import datetime
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..services.security_service import SecurityService
from ..models.security_models import (
    AuthenticationType, PermissionScope, ThreatLevel
)

logger = logging.getLogger(__name__)


class DeviceAuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for device authentication"""
    
    def __init__(self, app, security_service: SecurityService):
        super().__init__(app)
        self.security_service = security_service
        self.bearer_scheme = HTTPBearer(auto_error=False)
        
    async def dispatch(self, request: Request, call_next):
        """Process device authentication"""
        # Skip auth for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract authentication credentials
        auth_type, credentials = await self._extract_credentials(request)
        
        if not auth_type or not credentials:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication credentials"}
            )
        
        # Get source IP
        source_ip = self._get_client_ip(request)
        
        # Authenticate based on type
        device_info = None
        
        try:
            if auth_type == AuthenticationType.API_KEY:
                api_key_obj = await self.security_service.validate_api_key(
                    credentials,
                    source_ip=source_ip
                )
                if api_key_obj:
                    device_info = {
                        "device_id": api_key_obj.device_id,
                        "org_id": api_key_obj.org_id,
                        "auth_type": auth_type,
                        "scopes": api_key_obj.scopes
                    }
            
            elif auth_type == AuthenticationType.CERTIFICATE:
                # Extract certificate from TLS connection
                cert_fingerprint = self._get_client_certificate_fingerprint(request)
                if cert_fingerprint:
                    cert_auth = await self.security_service.validate_certificate(
                        cert_fingerprint,
                        credentials,  # org_id
                        source_ip=source_ip
                    )
                    if cert_auth:
                        device_info = {
                            "device_id": cert_auth.device_id,
                            "org_id": cert_auth.org_id,
                            "auth_type": auth_type,
                            "certificate_id": cert_auth.certificate_id
                        }
            
            elif auth_type == AuthenticationType.JWT:
                # JWT validation would go here
                pass
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication processing error"}
            )
        
        if not device_info:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication credentials"}
            )
        
        # Store device info in request state
        request.state.device_info = device_info
        request.state.source_ip = source_ip
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _extract_credentials(
        self,
        request: Request
    ) -> tuple[Optional[AuthenticationType], Optional[str]]:
        """Extract authentication credentials from request"""
        # Check API key in header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return AuthenticationType.API_KEY, api_key
        
        # Check Bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Determine if it's JWT or OAuth token
            if token.startswith("tesa_at_"):
                return AuthenticationType.OAUTH2, token
            else:
                return AuthenticationType.JWT, token
        
        # Check client certificate
        if hasattr(request, "transport") and hasattr(request.transport, "get_extra_info"):
            ssl_object = request.transport.get_extra_info("ssl_object")
            if ssl_object:
                return AuthenticationType.CERTIFICATE, request.headers.get("X-Organization-Id")
        
        return None, None
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        public_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/device-management/v1/public"
        ]
        return any(path.startswith(p) for p in public_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _get_client_certificate_fingerprint(self, request: Request) -> Optional[str]:
        """Extract client certificate fingerprint from TLS connection"""
        # This would need to be implemented based on the web server
        # For now, check a header that might be set by reverse proxy
        return request.headers.get("X-Client-Certificate-Fingerprint")


class DeviceRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for device rate limiting"""
    
    def __init__(
        self,
        app,
        security_service: SecurityService,
        default_limit: int = 100
    ):
        super().__init__(app)
        self.security_service = security_service
        self.default_limit = default_limit
        
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""
        # Skip rate limiting for internal endpoints
        if request.url.path.startswith("/internal/"):
            return await call_next(request)
        
        # Get device info from request state
        device_info = getattr(request.state, "device_info", None)
        if not device_info:
            # No authenticated device, apply default limit
            return await call_next(request)
        
        # Check rate limit
        is_allowed, limit_info = await self.security_service.check_rate_limit(
            device_info["device_id"],
            device_info["org_id"],
            request.url.path,
            getattr(request.state, "source_ip", None)
        )
        
        if not is_allowed:
            # Add rate limit headers
            headers = {
                "X-RateLimit-Limit": str(limit_info.get("limit_per_minute", self.default_limit)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": limit_info.get("blocked_until", ""),
                "Retry-After": str(limit_info.get("retry_after", 60))
            }
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "limit_info": limit_info
                },
                headers=headers
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        if limit_info:
            response.headers["X-RateLimit-Limit"] = str(
                limit_info.get("limit_per_minute", self.default_limit)
            )
            response.headers["X-RateLimit-Remaining"] = str(
                limit_info.get("remaining", self.default_limit)
            )
        
        return response


class DeviceSecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    def __init__(self, app):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Add CORS headers for device endpoints
        if request.url.path.startswith("/device-management/"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Authorization, Content-Type"
            response.headers["Access-Control-Max-Age"] = "86400"
        
        return response


class ThreatDetectionMiddleware(BaseHTTPMiddleware):
    """Middleware for threat detection and anomaly monitoring"""
    
    def __init__(self, app, security_service: SecurityService):
        super().__init__(app)
        self.security_service = security_service
        
    async def dispatch(self, request: Request, call_next):
        """Monitor requests for threats"""
        start_time = time.time()
        
        # Get device info
        device_info = getattr(request.state, "device_info", None)
        source_ip = getattr(request.state, "source_ip", "unknown")
        
        # Collect request data for analysis
        activity_data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "source_ip": source_ip,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check for suspicious patterns before processing
        if device_info:
            threats = await self.security_service.detect_threats(
                device_info["device_id"],
                device_info["org_id"],
                "request",
                activity_data,
                source_ip
            )
            
            # If critical threat detected, block request
            if any(t.threat_level == ThreatLevel.CRITICAL for t in threats):
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Request blocked due to security threat"}
                )
        
        # Process request
        response = await call_next(request)
        
        # Collect response data
        process_time = time.time() - start_time
        activity_data.update({
            "response_status": response.status_code,
            "process_time": process_time,
            "response_size": response.headers.get("content-length", 0)
        })
        
        # Post-request threat analysis
        if device_info and response.status_code >= 400:
            # Check for patterns like repeated 4xx errors
            await self.security_service.detect_threats(
                device_info["device_id"],
                device_info["org_id"],
                "response_error",
                activity_data,
                source_ip
            )
        
        return response


# Decorator-based security for specific endpoints

def require_device_permission(permission: PermissionScope):
    """Decorator to require specific device permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get device info from request
            device_info = getattr(request.state, "device_info", None)
            if not device_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Device authentication required"
                )
            
            # Check if device has required permission
            if "scopes" in device_info:
                if permission not in device_info["scopes"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Device lacks required permission: {permission.value}"
                    )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def enforce_organization_access(func: Callable) -> Callable:
    """Decorator to enforce organization-level access"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Get device info
        device_info = getattr(request.state, "device_info", None)
        if not device_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device authentication required"
            )
        
        # Extract org_id from path or query
        org_id = kwargs.get("org_id") or request.query_params.get("org_id")
        
        if org_id and org_id != device_info["org_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-organization access denied"
            )
        
        return await func(request, *args, **kwargs)
    
    return wrapper


def audit_device_action(action: str):
    """Decorator to audit device actions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get device info
            device_info = getattr(request.state, "device_info", None)
            
            # Execute function
            try:
                result = await func(request, *args, **kwargs)
                
                # Log successful action
                if device_info:
                    logger.info(
                        f"Device action succeeded - "
                        f"Device: {device_info.get('device_id')}, "
                        f"Action: {action}, "
                        f"Path: {request.url.path}"
                    )
                
                return result
                
            except Exception as e:
                # Log failed action
                if device_info:
                    logger.error(
                        f"Device action failed - "
                        f"Device: {device_info.get('device_id')}, "
                        f"Action: {action}, "
                        f"Path: {request.url.path}, "
                        f"Error: {str(e)}"
                    )
                raise
        
        return wrapper
    return decorator