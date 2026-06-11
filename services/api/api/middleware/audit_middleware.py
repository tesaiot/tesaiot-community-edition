# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Audit Logging Middleware
Copyright (C) 2024-2025 TESA IoT Platform

Comprehensive audit logging for all admin actions and security events
"""

import json
import logging
import time
from datetime import datetime
from functools import wraps
from flask import request, g
from typing import Dict, Any, Optional

# Configure audit loggers
audit_logger = logging.getLogger('audit')
security_logger = logging.getLogger('security')
admin_logger = logging.getLogger('admin')
auth_logger = logging.getLogger('auth')
api_logger = logging.getLogger('api')

class AuditEvent:
    """Audit event data structure"""
    
    def __init__(self, 
                 event_type: str,
                 action: str,
                 resource: str,
                 user_id: Optional[str] = None,
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None,
                 details: Optional[Dict] = None,
                 status: str = 'success',
                 error_message: Optional[str] = None):
        
        self.timestamp = datetime.utcnow().isoformat()
        self.event_type = event_type
        self.action = action
        self.resource = resource
        self.user_id = user_id or getattr(g, 'user_id', 'anonymous')
        self.ip_address = ip_address or self._get_client_ip()
        self.user_agent = user_agent or request.headers.get('User-Agent', 'unknown')
        self.details = details or {}
        self.status = status
        self.error_message = error_message
        self.session_id = getattr(g, 'session_id', None)
        self.request_id = getattr(g, 'request_id', None)
    
    def _get_client_ip(self) -> str:
        """Get client IP address handling proxies"""
        # Check for forwarded IP (behind proxy)
        forwarded_ip = request.headers.get('X-Forwarded-For')
        if forwarded_ip:
            return forwarded_ip.split(',')[0].strip()
        
        # Check for real IP (nginx)
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to remote address
        return request.remote_addr or 'unknown'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'action': self.action,
            'resource': self.resource,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'details': self.details,
            'status': self.status,
            'error_message': self.error_message,
            'session_id': self.session_id,
            'request_id': self.request_id
        }
    
    def to_json(self) -> str:
        """Convert audit event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

class AuditLogger:
    """Main audit logging class"""
    
    @staticmethod
    def log_admin_action(action: str, resource: str, details: Dict = None, status: str = 'success', error_message: str = None):
        """Log admin actions"""
        event = AuditEvent(
            event_type='admin_action',
            action=action,
            resource=resource,
            details=details,
            status=status,
            error_message=error_message
        )
        
        admin_logger.info(event.to_json())
        audit_logger.info(event.to_json())
        
        # Log security events for sensitive actions
        if action in ['user_delete', 'role_change', 'system_config', 'cert_generate', 'vault_access']:
            security_logger.warning(f"SENSITIVE_ACTION: {action} on {resource} by {event.user_id}")
    
    @staticmethod
    def log_auth_event(action: str, user_id: str = None, status: str = 'success', details: Dict = None, error_message: str = None):
        """Log authentication events"""
        event = AuditEvent(
            event_type='authentication',
            action=action,
            resource='auth_system',
            user_id=user_id,
            details=details,
            status=status,
            error_message=error_message
        )
        
        auth_logger.info(event.to_json())
        audit_logger.info(event.to_json())
        
        # Log failed auth attempts as security events
        if status == 'failed':
            security_logger.warning(f"AUTH_FAILURE: {action} from {event.ip_address} for user {user_id}")
    
    @staticmethod
    def log_api_access(endpoint: str, method: str, status_code: int, response_time: float = None, details: Dict = None):
        """Log API access"""
        event = AuditEvent(
            event_type='api_access',
            action=f"{method}_{endpoint}",
            resource='api',
            details={
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time_ms': response_time,
                **(details or {})
            },
            status='success' if 200 <= status_code < 400 else 'failed'
        )
        
        api_logger.info(event.to_json())
        
        # Log suspicious API activity
        if status_code in [401, 403, 429] or (response_time and response_time > 5000):
            security_logger.warning(f"SUSPICIOUS_API: {method} {endpoint} - {status_code} from {event.ip_address}")
    
    @staticmethod
    def log_security_event(event_type: str, description: str, severity: str = 'medium', details: Dict = None):
        """Log security events"""
        event = AuditEvent(
            event_type='security_event',
            action=event_type,
            resource='security_system',
            details={
                'description': description,
                'severity': severity,
                **(details or {})
            }
        )
        
        security_logger.warning(event.to_json())
        audit_logger.info(event.to_json())

def audit_admin_action(action: str, resource: str = None):
    """Decorator for auditing admin actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            resource_name = resource or f.__name__
            
            try:
                # Execute the function
                result = f(*args, **kwargs)
                
                # Log successful action
                AuditLogger.log_admin_action(
                    action=action,
                    resource=resource_name,
                    details={
                        'function': f.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys()),
                        'execution_time_ms': round((time.time() - start_time) * 1000, 2)
                    },
                    status='success'
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditLogger.log_admin_action(
                    action=action,
                    resource=resource_name,
                    details={
                        'function': f.__name__,
                        'execution_time_ms': round((time.time() - start_time) * 1000, 2)
                    },
                    status='failed',
                    error_message=str(e)
                )
                raise
        
        return decorated_function
    return decorator

def audit_api_request():
    """Middleware for auditing API requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Execute the function
                result = f(*args, **kwargs)
                
                # Determine status code
                if hasattr(result, 'status_code'):
                    status_code = result.status_code
                elif isinstance(result, tuple) and len(result) > 1:
                    status_code = result[1]
                else:
                    status_code = 200
                
                # Log API access
                AuditLogger.log_api_access(
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=status_code,
                    response_time=round((time.time() - start_time) * 1000, 2),
                    details={
                        'content_length': request.content_length,
                        'content_type': request.content_type
                    }
                )
                
                return result
                
            except Exception as e:
                # Log failed API request
                AuditLogger.log_api_access(
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=500,
                    response_time=round((time.time() - start_time) * 1000, 2),
                    details={
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                )
                raise
        
        return decorated_function
    return decorator

class AuditMiddleware:
    """Flask middleware for comprehensive audit logging"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the audit middleware with Flask app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.teardown_appcontext(self.teardown)
    
    def before_request(self):
        """Log before request processing"""
        g.audit_start_time = time.time()
        g.request_id = f"req_{int(time.time() * 1000)}"
        
        # Log sensitive endpoints
        sensitive_paths = ['/admin', '/auth', '/api/v1/users', '/api/v1/certificates', '/api/v1/vault']
        
        if any(request.path.startswith(path) for path in sensitive_paths):
            AuditLogger.log_security_event(
                event_type='sensitive_endpoint_access',
                description=f"Access to sensitive endpoint: {request.path}",
                severity='low',
                details={
                    'method': request.method,
                    'endpoint': request.path,
                    'query_params': dict(request.args)
                }
            )
    
    def after_request(self, response):
        """Log after request processing"""
        if hasattr(g, 'audit_start_time'):
            response_time = round((time.time() - g.audit_start_time) * 1000, 2)
            
            # Log all requests to audit log
            if not request.path.startswith('/static'):
                AuditLogger.log_api_access(
                    endpoint=request.endpoint or request.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time=response_time
                )
        
        return response
    
    def teardown(self, exception):
        """Clean up audit context"""
        if exception:
            AuditLogger.log_security_event(
                event_type='request_exception',
                description=f"Unhandled exception in request: {str(exception)}",
                severity='high',
                details={
                    'exception_type': type(exception).__name__,
                    'endpoint': request.endpoint or request.path,
                    'method': request.method
                }
            )

# Commonly used audit decorators for specific actions
def audit_user_management(action):
    """Audit decorator for user management actions"""
    return audit_admin_action(f"user_{action}", "user_management")

def audit_device_management(action):
    """Audit decorator for device management actions"""
    return audit_admin_action(f"device_{action}", "device_management")

def audit_certificate_management(action):
    """Audit decorator for certificate management actions"""
    return audit_admin_action(f"cert_{action}", "certificate_management")

def audit_system_config(action):
    """Audit decorator for system configuration actions"""
    return audit_admin_action(f"config_{action}", "system_configuration")