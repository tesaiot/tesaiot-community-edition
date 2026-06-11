# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Audit Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


This module provides comprehensive audit logging for GDPR compliance.
All data access and modifications are logged with full context.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

# Import MongoDB exceptions
try:
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, WriteError, PyMongoError
except ImportError:
    # Fallback if pymongo not available
    class ConnectionFailure(Exception):
        pass
    class ServerSelectionTimeoutError(Exception):
        pass
    class WriteError(Exception):
        pass
    class PyMongoError(Exception):
        pass

from ..core.database import get_db
from ..core.rbac import RBAC

logger = logging.getLogger(__name__)

class AuditAction(Enum):
    """Audit action types for tracking"""
    # Authentication actions
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_RESET = "auth.password_reset"
    
    # User actions
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_VIEW = "user.view"
    USER_LIST = "user.list"
    
    # Device actions
    DEVICE_CREATE = "device.create"
    DEVICE_UPDATE = "device.update"
    DEVICE_DELETE = "device.delete"
    DEVICE_VIEW = "device.view"
    DEVICE_LIST = "device.list"
    DEVICE_AUTO_REGISTER = "device.auto_register"
    
    # Provisioning actions
    BULK_IMPORT = "provisioning.bulk_import"
    TEMPLATE_CREATE = "provisioning.template_create"
    TEMPLATE_UPDATE = "provisioning.template_update"
    TEMPLATE_DELETE = "provisioning.template_delete"
    ZERO_TOUCH_PROVISION = "provisioning.zero_touch"
    PROTECTED_UPDATE_CREATE = "provisioning.protected_update.create"
    PROTECTED_UPDATE_PUBLISH = "provisioning.protected_update.publish"
    PROTECTED_UPDATE_CSR_ENQUEUE = "provisioning.protected_update.csr.enqueue"
    PROTECTED_UPDATE_CSR_SIGN = "provisioning.protected_update.csr.sign"
    PROTECTED_UPDATE_CSR_SIGNED = "provisioning.protected_update.csr.signed"
    PROTECTED_UPDATE_CSR_PUBLISH = "provisioning.protected_update.csr.publish"
    
    # Certificate actions
    CERTIFICATE_ISSUE = "certificate.issue"
    CERTIFICATE_REVOKE = "certificate.revoke"
    CERTIFICATE_DOWNLOAD = "certificate.download"
    CERTIFICATE_VIEW = "certificate.view"
    CERTIFICATE_CSR_VALIDATED = "certificate.csr_validated"
    CERTIFICATE_CSR_SIGNED = "certificate.csr_signed"
    
    # Key provisioning actions
    KEY_GENERATE = "key.generate"
    KEY_DISTRIBUTE = "key.distribute"
    KEY_DOWNLOAD = "key.download"
    KEY_REVOKE = "key.revoke"
    KEY_ROTATE = "key.rotate"
    KEY_ESCROW = "key.escrow"
    KEY_RELEASE = "key.release"
    KEY_POLICY_UPDATE = "key.policy_update"
    KEY_VIEW = "key.view"
    KEY_BULK_GENERATE = "key.bulk_generate"
    
    # Telemetry actions
    TELEMETRY_INGEST = "telemetry.ingest"
    TELEMETRY_VIEW = "telemetry.view"
    TELEMETRY_EXPORT = "telemetry.export"
    
    # Organization actions
    ORGANIZATION_CREATE = "organization.create"
    ORGANIZATION_UPDATE = "organization.update"
    ORGANIZATION_DELETE = "organization.delete"
    ORGANIZATION_VIEW = "organization.view"
    
    # Analytics actions
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"
    
    # Security actions
    ACCESS_DENIED = "security.access_denied"
    PERMISSION_VIOLATION = "security.permission_violation"
    CROSS_ORG_ATTEMPT = "security.cross_org_attempt"

class AuditService:
    """Service for comprehensive audit logging"""
    
    def __init__(self):
        self.db = get_db()
        self.collection = self.db.audit_logs if self.db is not None else None
        # Ensure audit_logs collection exists
        if self.db is not None and 'audit_logs' not in self.db.list_collection_names():
            self.db.create_collection('audit_logs')
            logger.info("Created audit_logs collection")
    
    def log_action(
        self,
        action: AuditAction,
        user: Dict[str, Any],
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Log an audit action with full context.
        
        Args:
            action: The action being performed
            user: User performing the action
            resource_type: Type of resource (user, device, etc.)
            resource_id: ID of the specific resource
            details: Additional details about the action
            status: Status of the action (success, failure, denied)
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            bool: True if logged successfully
        """
        try:
            if self.collection is None:
                # Attempt lazy reinitialisation in case service was constructed before DB ready
                self.db = get_db()
                if self.db is None:
                    logger.error("Audit collection not available (database unreachable)")
                    return False
                self.collection = self.db.audit_logs
                # Ensure collection exists (create lazily if missing)
                collection_names = list(self.db.list_collection_names())
                if 'audit_logs' not in collection_names:
                    self.db.create_collection('audit_logs')
                    logger.info("Created audit_logs collection on-demand")

            # Build audit entry
            audit_entry = {
                'timestamp': datetime.utcnow(),
                'action': action.value,
                'status': status,
                'user': {
                    'id': str(user.get('_id', '')),
                    'email': user.get('email', ''),
                    'name': user.get('name', ''),
                    'role': user.get('role', ''),
                    'organization_id': user.get('organization_id', '')
                },
                'resource': {
                    'type': resource_type,
                    'id': resource_id
                },
                'details': details or {},
                'metadata': {
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'session_id': user.get('session_id', '')
                },
                'organization_id': user.get('organization_id', '')  # For filtering
            }
            
            # Insert audit log
            self.collection.insert_one(audit_entry)
            
            # Log critical security events
            if action in [AuditAction.ACCESS_DENIED, AuditAction.PERMISSION_VIOLATION, 
                         AuditAction.CROSS_ORG_ATTEMPT]:
                logger.warning(f"Security event: {action.value} by {user.get('email')} "
                             f"on {resource_type}/{resource_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
            return False
    
    def log_data_access(
        self,
        user: Dict[str, Any],
        collection: str,
        query: Dict[str, Any],
        record_count: int,
        operation: str = "read",
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Log database access for GDPR compliance.
        
        Args:
            user: User accessing data
            collection: Database collection accessed
            query: Query parameters used
            record_count: Number of records accessed
            operation: Type of operation (read, write, delete)
            ip_address: Client IP address
            
        Returns:
            bool: True if logged successfully
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                if self.collection is None:
                    return False
                
                # Sanitize query to remove sensitive data
                safe_query = self._sanitize_query(query)
                
                access_log = {
                    'timestamp': datetime.utcnow(),
                    'type': 'data_access',
                    'operation': operation,
                    'user': {
                        'id': str(user.get('_id', '')),
                        'email': user.get('email', ''),
                        'role': user.get('role', ''),
                        'organization_id': user.get('organization_id', '')
                    },
                    'access': {
                        'collection': collection,
                        'query': safe_query,
                        'record_count': record_count
                    },
                    'metadata': {
                        'ip_address': ip_address
                    },
                    'organization_id': user.get('organization_id', '')
                }
                
                # Insert data access log
                self.collection.insert_one(access_log)
                
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.debug(f"Audit data access logging connection error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    self._initialize_db()  # Try to reconnect
                    continue
                else:
                    logger.warning(f"Failed to log data access after {max_retries} attempts: connection failed")
                    return False
                    
            except WriteError as e:
                logger.warning(f"Audit data access write error: {e}")
                return False
                
            except PyMongoError as e:
                logger.warning(f"Audit data access database error: {e}")
                return False
                
            except Exception as e:
                logger.error(f"Unexpected error logging data access: {e}")
                return False
                
        return False
    
    def log_security_violation(
        self,
        user: Dict[str, Any],
        violation_type: str,
        target_resource: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> bool:
        """
        Log security violations for immediate attention.
        
        Args:
            user: User causing the violation
            violation_type: Type of violation
            target_resource: Resource being accessed
            details: Violation details
            ip_address: Client IP address
            
        Returns:
            bool: True if logged successfully
        """
        try:
            # Determine audit action based on violation type
            action_map = {
                'cross_org_access': AuditAction.CROSS_ORG_ATTEMPT,
                'permission_denied': AuditAction.PERMISSION_VIOLATION,
                'unauthorized_access': AuditAction.ACCESS_DENIED
            }
            
            action = action_map.get(violation_type, AuditAction.ACCESS_DENIED)
            
            # Log with high priority
            return self.log_action(
                action=action,
                user=user,
                resource_type='security',
                resource_id=target_resource,
                details={
                    'violation_type': violation_type,
                    'severity': 'high',
                    **details
                },
                status='violation',
                ip_address=ip_address
            )
            
        except Exception as e:
            logger.error(f"Failed to log security violation: {e}")
            return False
    
    def get_audit_logs(
        self,
        user: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> list:
        """
        Retrieve audit logs with organization filtering and error handling.
        
        Args:
            user: User requesting logs
            filters: Additional filters
            limit: Maximum records to return
            
        Returns:
            list: Audit log entries
        """
        max_retries = 2
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # Ensure database connection
                if not self._ensure_connection():
                    logger.error("Audit database connection not available for log retrieval")
                    return []
                
                # Build query with organization filter
                query = filters or {}
                
                # Apply organization filter unless platform admin
                if not RBAC.is_platform_admin(user):
                    query['organization_id'] = user.get('organization_id', '')
                
                # Get logs
                logs = list(self.collection.find(query).sort('timestamp', -1).limit(limit))
                
                # Format for response
                for log in logs:
                    log['_id'] = str(log['_id'])
                    log['timestamp'] = log['timestamp'].isoformat() if log.get('timestamp') else ''
                
                return logs
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                logger.warning(f"Audit log retrieval connection error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    self._initialize_db()  # Try to reconnect
                    continue
                else:
                    logger.error(f"Failed to retrieve audit logs after {max_retries} attempts: connection failed")
                    return []
                    
            except PyMongoError as e:
                logger.error(f"Audit log retrieval database error: {e}")
                return []
                
            except Exception as e:
                logger.error(f"Unexpected error retrieving audit logs: {e}")
                return []
                
        return []
    
    def _ensure_connection(self) -> bool:
        """
        Ensure database connection is available.
        
        Returns:
            bool: True if connection is available, False otherwise
        """
        try:
            if self.db is None:
                self.db = get_db()
                self.collection = self.db.audit_logs if self.db is not None else None
            
            if self.db is not None and self.collection is not None:
                # Test the connection with a simple ping
                self.db.command('ping')
                return True
            return False
        except Exception as e:
            logger.debug(f"Database connection check failed: {e}")
            return False
    
    def _initialize_db(self):
        """
        Re-initialize database connection.
        """
        try:
            self.db = get_db()
            self.collection = self.db.audit_logs if self.db is not None else None
            
            # Ensure audit_logs collection exists
            if self.db is not None and 'audit_logs' not in self.db.list_collection_names():
                self.db.create_collection('audit_logs')
                logger.info("Created audit_logs collection")
        except Exception as e:
            logger.debug(f"Database initialization failed: {e}")
            self.db = None
            self.collection = None
    
    def _sanitize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize query to remove sensitive data like passwords.
        
        Args:
            query: Original query
            
        Returns:
            dict: Sanitized query
        """
        sensitive_fields = ['password', 'private_key', 'secret', 'token']
        sanitized = {}
        
        for key, value in query.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_query(value)
            else:
                sanitized[key] = value
        
        return sanitized

# Global audit service instance
audit_service = AuditService()

# Convenience functions
def audit_log(
    action: AuditAction,
    user: Dict[str, Any],
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status: str = "success",
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Convenience function for audit logging"""
    return audit_service.log_action(
        action, user, resource_type, resource_id, 
        details, status, ip_address, user_agent
    )

def audit_data_access(
    user: Dict[str, Any],
    collection: str,
    query: Dict[str, Any],
    record_count: int,
    operation: str = "read",
    ip_address: Optional[str] = None
):
    """Convenience function for data access logging"""
    return audit_service.log_data_access(
        user, collection, query, record_count, operation, ip_address
    )

def audit_security_violation(
    user: Dict[str, Any],
    violation_type: str,
    target_resource: str,
    details: Dict[str, Any],
    ip_address: Optional[str] = None
):
    """Convenience function for security violation logging"""
    return audit_service.log_security_violation(
        user, violation_type, target_resource, details, ip_address
    )


class AuditMiddleware:
    """
    Flask middleware to automatically audit all API requests.
    Captures authentication, authorization, and data access events.
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        
        # Store start time for performance tracking
        import time
        from flask import g
        
        @app.before_request
        def track_request_start():
            g.request_start_time = time.time()
    
    def _before_request(self):
        """Called before each request"""
        from flask import request, g
        import time
        
        # Track request timing
        if not hasattr(g, 'request_start_time'):
            g.request_start_time = time.time()
        
        # Generate request ID for correlation
        g.request_id = f"{time.time()}-{hash(request.path) % 10000}"
    
    def _after_request(self, response):
        """Called after each request"""
        from flask import request, g
        import time
        
        try:
            # Calculate response time
            response_time = (time.time() - getattr(g, 'request_start_time', time.time())) * 1000
            
            # Get user context if available
            current_user = getattr(g, 'current_user', None)
            
            # Skip health checks and static files
            if self._should_skip_audit(request.path):
                return response
            
            # Log API access
            if current_user:
                audit_log(
                    action=self._get_audit_action(request.method, request.path),
                    user=current_user,
                    resource_type="api_endpoint",
                    resource_id=request.path,
                    details={
                        "method": request.method,
                        "status_code": response.status_code,
                        "response_time_ms": round(response_time, 2),
                        "request_size": request.content_length or 0,
                        "response_size": len(response.get_data()) if response.get_data() else 0
                    },
                    status="success" if response.status_code < 400 else "error",
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                # Log security violations for 401/403
                if response.status_code in [401, 403]:
                    audit_security_violation(
                        user=current_user or {"email": "unknown", "organization_id": ""},
                        violation_type="access_denied",
                        target_resource=request.path,
                        details={
                            "method": request.method,
                            "status_code": response.status_code,
                            "reason": "authentication_failed" if response.status_code == 401 else "authorization_failed"
                        },
                        ip_address=request.remote_addr
                    )
            
            # Log suspicious activity (slow requests)
            if response_time > 5000:  # > 5 seconds
                audit_log(
                    action=AuditAction.ACCESS_DENIED,  # Using existing enum
                    user=current_user or {"email": "unknown", "organization_id": "", "_id": ""},
                    resource_type="performance",
                    resource_id=request.path,
                    details={
                        "response_time_ms": round(response_time, 2),
                        "threshold_exceeded": "5000ms",
                        "method": request.method
                    },
                    status="warning",
                    ip_address=request.remote_addr
                )
            
        except Exception as e:
            logger.error(f"Audit middleware error: {e}")
            # Don't fail the request due to audit issues
        
        return response
    
    def _should_skip_audit(self, path):
        """Determine if this path should skip audit logging"""
        skip_paths = [
            '/api/v1/health',
            '/version.json',
            '/favicon.ico',
            '/static/',
            '/_health'
        ]
        return any(path.startswith(skip) for skip in skip_paths)
    
    def _get_audit_action(self, method, path):
        """Map HTTP method and path to audit action"""
        # Device operations
        if 'devices' in path:
            if method == 'POST':
                return AuditAction.DEVICE_CREATE
            elif method in ['PUT', 'PATCH']:
                return AuditAction.DEVICE_UPDATE
            elif method == 'DELETE':
                return AuditAction.DEVICE_DELETE
            else:
                return AuditAction.DEVICE_VIEW
        
        # User operations
        elif 'users' in path:
            if method == 'POST':
                return AuditAction.USER_CREATE
            elif method in ['PUT', 'PATCH']:
                return AuditAction.USER_UPDATE
            elif method == 'DELETE':
                return AuditAction.USER_DELETE
            else:
                return AuditAction.USER_VIEW
        
        # Certificate operations
        elif 'certificate' in path:
            if 'download' in path:
                return AuditAction.CERTIFICATE_DOWNLOAD
            elif method == 'POST':
                return AuditAction.CERTIFICATE_ISSUE
            elif method == 'DELETE':
                return AuditAction.CERTIFICATE_REVOKE
            else:
                return AuditAction.CERTIFICATE_VIEW
        
        # Organization operations
        elif 'organization' in path:
            if method == 'POST':
                return AuditAction.ORGANIZATION_CREATE
            elif method in ['PUT', 'PATCH']:
                return AuditAction.ORGANIZATION_UPDATE
            elif method == 'DELETE':
                return AuditAction.ORGANIZATION_DELETE
            else:
                return AuditAction.ORGANIZATION_VIEW
        
        # Telemetry operations
        elif 'telemetry' in path:
            if method == 'POST':
                return AuditAction.TELEMETRY_INGEST
            else:
                return AuditAction.TELEMETRY_VIEW
        
        # Analytics operations
        elif 'analytics' in path or 'dashboard' in path:
            return AuditAction.ANALYTICS_VIEW
        
        # Authentication
        elif 'auth' in path or 'login' in path:
            return AuditAction.LOGIN
        
        # Default for other operations
        else:
            return AuditAction.USER_VIEW  # Generic view action
