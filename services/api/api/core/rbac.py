# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Role-Based Access Control (RBAC)
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


This module defines the RBAC system for the platform.
All role checks should use this module for consistency.
"""

from enum import Enum
from typing import List, Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)

class Role(Enum):
    """Platform roles with hierarchical permissions"""
    PLATFORM_ADMIN = "platform_admin"  # TESA platform infrastructure admin (NO customer data access)
    ORGANIZATION_ADMIN = "organization_admin"  # Customer organization admin (full org + sub-org access)
    ADMIN = "admin"  # Department/team admin within organization
    MANAGER = "manager"  # Device/user manager within organization
    USER = "user"  # Regular user with read-only access
    DEVICE = "device"  # IoT device role (API access only)
    SERVICE = "service"  # Internal trusted service account (e.g. MQTT telemetry bridge) - least-privilege, non-human
    GUEST = "guest"  # Limited guest access
    
    # Aliases for backward compatibility
    SUPER_ADMIN = "super_admin"  # Alias for ORGANIZATION_ADMIN
    ORG_USER = "org_user"  # Alias for USER (frontend compatibility)
    ORG_ADMIN = "org_admin"  # Alias for ORGANIZATION_ADMIN

class Permission(Enum):
    """Granular permissions for resources"""
    # Platform permissions (platform_admin only - TESA infrastructure)
    PLATFORM_MANAGE = "platform.manage"
    PLATFORM_VIEW_ALL = "platform.view_all"
    PLATFORM_INFRASTRUCTURE = "platform.infrastructure"
    PLATFORM_MONITORING = "platform.monitoring"
    
    # Organization permissions
    ORGANIZATION_CREATE = "organization.create"
    ORGANIZATION_UPDATE = "organization.update"
    ORGANIZATION_DELETE = "organization.delete"
    ORGANIZATION_VIEW = "organization.view"
    ORGANIZATION_VIEW_ALL = "organization.view_all"
    
    # User permissions
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_VIEW = "user.view"
    USER_RESET_PASSWORD = "user.reset_password"
    
    # Device permissions
    DEVICE_CREATE = "device.create"
    DEVICE_UPDATE = "device.update"
    DEVICE_DELETE = "device.delete"
    DEVICE_VIEW = "device.view"
    DEVICE_CONTROL = "device.control"
    
    # Certificate permissions
    CERTIFICATE_CREATE = "certificate.create"  # Alias for certificate.issue
    CERTIFICATE_ISSUE = "certificate.issue"
    CERTIFICATE_REVOKE = "certificate.revoke"
    CERTIFICATE_DOWNLOAD = "certificate.download"
    CERTIFICATE_VIEW = "certificate.view"
    
    # Telemetry permissions
    TELEMETRY_INGEST = "telemetry.ingest"
    TELEMETRY_VIEW = "telemetry.view"
    TELEMETRY_EXPORT = "telemetry.export"
    
    # Analytics permissions
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"
    
    # Audit permissions
    AUDIT_VIEW = "audit.view"
    AUDIT_EXPORT = "audit.export"
    
    # Settings permissions
    SETTINGS_UPDATE = "settings.update"
    SETTINGS_VIEW = "settings.view"

# Platform Administrator Email Allowlist
#
# Platform-admin grants are NOT baked into the source. Configure the allowlist
# via the PLATFORM_ADMIN_EMAILS environment variable as a comma-separated list
# of email addresses, e.g.:
#     PLATFORM_ADMIN_EMAILS="admin@your-org.example,ops@your-org.example"
# If unset, no email is treated as a platform admin (deny by default); grant
# platform-admin access through your roles/config provisioning instead.
PLATFORM_ADMIN_EMAILS = {
    email.strip().lower()
    for email in os.getenv("PLATFORM_ADMIN_EMAILS", "").split(",")
    if email.strip()
}

# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.PLATFORM_ADMIN: [
        # TESA Platform infrastructure management AND full access to all platform resources
        Permission.PLATFORM_MANAGE,
        Permission.PLATFORM_VIEW_ALL,
        Permission.PLATFORM_INFRASTRUCTURE,
        Permission.PLATFORM_MONITORING,
        # Full permissions for platform administration
        Permission.ORGANIZATION_CREATE,
        Permission.ORGANIZATION_UPDATE,
        Permission.ORGANIZATION_DELETE,
        Permission.ORGANIZATION_VIEW,
        Permission.ORGANIZATION_VIEW_ALL,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_VIEW,
        Permission.USER_RESET_PASSWORD,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_DELETE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_CREATE,
        Permission.CERTIFICATE_ISSUE,
        Permission.CERTIFICATE_REVOKE,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_INGEST,
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.SETTINGS_UPDATE,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.SUPER_ADMIN: [
        # Backward compatibility - maps to ORGANIZATION_ADMIN
        Permission.ORGANIZATION_CREATE,
        Permission.ORGANIZATION_UPDATE,
        Permission.ORGANIZATION_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_VIEW,
        Permission.USER_RESET_PASSWORD,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_DELETE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_CREATE,
        Permission.CERTIFICATE_ISSUE,
        Permission.CERTIFICATE_REVOKE,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_INGEST,
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.SETTINGS_UPDATE,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.ORGANIZATION_ADMIN: [
        # Can manage everything within their organization + sub-organizations
        Permission.ORGANIZATION_CREATE,  # Can create sub-organizations
        Permission.ORGANIZATION_UPDATE,
        Permission.ORGANIZATION_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_VIEW,
        Permission.USER_RESET_PASSWORD,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_DELETE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_CREATE,
        Permission.CERTIFICATE_ISSUE,
        Permission.CERTIFICATE_REVOKE,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_INGEST,
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.SETTINGS_UPDATE,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.ADMIN: [
        # Department/team admin - can manage users and devices
        Permission.ORGANIZATION_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_VIEW,
        Permission.USER_RESET_PASSWORD,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_DELETE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_CREATE,
        Permission.CERTIFICATE_ISSUE,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.ANALYTICS_VIEW,
        Permission.AUDIT_VIEW,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.MANAGER: [
        # Can manage devices but not users
        Permission.ORGANIZATION_VIEW,
        Permission.USER_VIEW,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.USER: [
        # Read-only access
        Permission.ORGANIZATION_VIEW,
        Permission.USER_VIEW,
        Permission.DEVICE_VIEW,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_VIEW,
        Permission.ANALYTICS_VIEW,
        Permission.SETTINGS_VIEW,
    ],

    Role.SERVICE: [
        # Internal trusted relay (MQTT telemetry bridge). Exactly the
        # permissions the bridge's API calls require and nothing else:
        # ingest telemetry on behalf of forwarded devices, update device
        # last-seen/status, and read device records. Deliberately NO user,
        # certificate, settings, or device create/delete permissions.
        Permission.TELEMETRY_INGEST,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_VIEW,
    ],
    
    Role.DEVICE: [
        # IoT device permissions
        Permission.TELEMETRY_INGEST,
        Permission.DEVICE_VIEW,  # Can view own device info
        Permission.CERTIFICATE_DOWNLOAD,  # Can download own certificate
    ],
    
    Role.GUEST: [
        # Minimal permissions
        Permission.ORGANIZATION_VIEW,
        Permission.DEVICE_VIEW,
    ],
    
    # Aliases map to their actual roles
    Role.ORG_USER: [
        # Organization user - can manage their own devices
        Permission.ORGANIZATION_VIEW,
        Permission.USER_VIEW,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CREATE,    # Can create devices
        Permission.DEVICE_UPDATE,    # Can update own devices
        Permission.DEVICE_DELETE,    # Can delete own devices
        Permission.CERTIFICATE_VIEW,
        Permission.CERTIFICATE_DOWNLOAD,  # Can download certs for own devices
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_INGEST,  # Can send telemetry for own devices
        Permission.ANALYTICS_VIEW,
        Permission.SETTINGS_VIEW,
    ],
    
    Role.ORG_ADMIN: [
        # Same as ORGANIZATION_ADMIN - full org management
        Permission.ORGANIZATION_CREATE,  # Can create sub-organizations
        Permission.ORGANIZATION_UPDATE,
        Permission.ORGANIZATION_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_VIEW,
        Permission.USER_RESET_PASSWORD,
        Permission.DEVICE_CREATE,
        Permission.DEVICE_UPDATE,
        Permission.DEVICE_DELETE,
        Permission.DEVICE_VIEW,
        Permission.DEVICE_CONTROL,
        Permission.CERTIFICATE_CREATE,
        Permission.CERTIFICATE_ISSUE,
        Permission.CERTIFICATE_REVOKE,
        Permission.CERTIFICATE_DOWNLOAD,
        Permission.CERTIFICATE_VIEW,
        Permission.TELEMETRY_INGEST,
        Permission.TELEMETRY_VIEW,
        Permission.TELEMETRY_EXPORT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.SETTINGS_UPDATE,
        Permission.SETTINGS_VIEW,
    ],
}

class RBAC:
    """Role-Based Access Control implementation"""

    @staticmethod
    def canonicalize_role(user_role: Optional[str]) -> str:
        """Return the canonical string for a given role alias."""
        if not user_role:
            return Role.USER.value

        alias_map = {
            'org_admin': Role.ORGANIZATION_ADMIN.value,
        }

        return alias_map.get(user_role, user_role)

    @staticmethod
    def has_permission(user_role: str, permission: Permission) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            user_role: User's role as string
            permission: Permission to check
            
        Returns:
            bool: True if role has permission
        """
        try:
            # Handle role aliases - normalize to actual role
            role_mapping = {
                'org_user': Role.ORG_USER.value,  # Maps to USER permissions
                'org_admin': Role.ORGANIZATION_ADMIN.value,  # Maps to ORGANIZATION_ADMIN permissions
                'super_admin': 'super_admin'  # Alias retains elevated badge
            }

            # Use mapped role if it exists, otherwise use original
            normalized_role = role_mapping.get(user_role, user_role)
            
            role = Role(normalized_role)
            role_permissions = ROLE_PERMISSIONS.get(role, [])
            return permission in role_permissions
        except ValueError:
            logger.warning(f"Invalid role: {user_role}")
            return False
    
    @staticmethod
    def has_any_permission(user_role: str, permissions: List[Permission]) -> bool:
        """
        Check if a role has any of the specified permissions.
        
        Args:
            user_role: User's role as string
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has any permission
        """
        return any(RBAC.has_permission(user_role, perm) for perm in permissions)
    
    @staticmethod
    def has_all_permissions(user_role: str, permissions: List[Permission]) -> bool:
        """
        Check if a role has all of the specified permissions.
        
        Args:
            user_role: User's role as string
            permissions: List of permissions to check
            
        Returns:
            bool: True if role has all permissions
        """
        return all(RBAC.has_permission(user_role, perm) for perm in permissions)
    
    @staticmethod
    def get_role_permissions(user_role: str) -> List[Permission]:
        """
        Get all permissions for a role.
        
        Args:
            user_role: User's role as string
            
        Returns:
            List of permissions
        """
        try:
            role = Role(user_role)
            return ROLE_PERMISSIONS.get(role, [])
        except ValueError:
            logger.warning(f"Invalid role: {user_role}")
            return []
    
    @staticmethod
    def is_admin_role(user_role: str) -> bool:
        """
        Check if role is any type of admin.
        
        Args:
            user_role: User's role as string
            
        Returns:
            bool: True if admin role
        """
        admin_roles = [Role.PLATFORM_ADMIN, Role.SUPER_ADMIN, Role.ORGANIZATION_ADMIN, Role.ADMIN]
        try:
            role = Role(user_role)
            return role in admin_roles
        except ValueError:
            return False
    
    @staticmethod
    def is_platform_admin(user: dict) -> bool:
        """
        Check if user is a TESA platform infrastructure admin.
        Platform admins can ONLY manage infrastructure - NO customer data access.

        Args:
            user: User object (can be None)

        Returns:
            bool: True if TESA platform admin (infrastructure only), False if user is None
        """
        # Handle None user gracefully (defensive programming)
        if user is None:
            return False

        user_email = user.get('email', '').strip().lower()
        user_role = user.get('role', '')

        # Must have platform_admin role AND be in the configured email allowlist
        return (user_role == Role.PLATFORM_ADMIN.value and
                user_email in PLATFORM_ADMIN_EMAILS)
    
    @staticmethod
    def is_organization_admin(user: dict) -> bool:
        """
        Check if user is an organization admin (can access customer data).
        
        Args:
            user: User object
            
        Returns:
            bool: True if organization admin
        """
        user_role = user.get('role', '')
        return user_role in [Role.ORGANIZATION_ADMIN.value, Role.SUPER_ADMIN.value]
    
    @staticmethod
    def can_access_organization(user: dict, target_org_id: str) -> bool:
        """
        Check if user can access a specific organization.
        Platform admins have full access to all organizations.
        
        Args:
            user: User object
            target_org_id: Target organization ID
            
        Returns:
            bool: True if can access
        """
        # SECURITY FIX: Platform admin can ONLY access infrastructure organizations, NOT customer data
        if RBAC.is_platform_admin(user):
            # Import here to avoid circular import
            from ..services.organization_service import get_organization_by_id
            
            # Check if target organization is infrastructure-only
            org = get_organization_by_id(target_org_id)
            if org:
                is_infrastructure = (
                    org.get('category') in ['infrastructure', 'platform'] or
                    org.get('organization_id') in ['tesa-platform', 'infrastructure', 'monitoring'] or
                    any(keyword in org.get('name', '').lower() for keyword in ['tesa', 'infrastructure', 'platform', 'monitoring'])
                )
                if is_infrastructure:
                    logger.info(f"[SECURITY_AUDIT] Platform admin {user.get('email')} accessing infrastructure org: {target_org_id}")
                    return True
                else:
                    logger.warning(f"[SECURITY_VIOLATION_PREVENTED] Platform admin {user.get('email')} BLOCKED from accessing customer org: {target_org_id}")
                    return False
            return False
        
        # Organization admin can access their org + sub-organizations
        if RBAC.is_organization_admin(user):
            if user.get('role') == Role.SUPER_ADMIN.value:
                return True
            user_org_id = user.get('organization_id', '')
            if user_org_id == target_org_id:
                return True
            # TODO: Check if target_org is a sub-organization
            # For now, only allow same organization
            return False
        
        # Regular users can only access their own organization
        user_org_id = user.get('organization_id', '')
        return user_org_id == target_org_id
    
    @staticmethod
    def filter_by_organization(user: dict, query: dict) -> dict:
        """
        Add organization filter to a database query based on user's role.
        Platform admins see all data across all organizations.
        
        Args:
            user: User object
            query: Database query dict
            
        Returns:
            dict: Updated query with organization filter
        """
        # SECURITY FIX: Platform admin can ONLY see infrastructure data, NOT customer data
        if RBAC.is_platform_admin(user):
            logger.info(f"[SECURITY_AUDIT] Platform admin {user.get('email')} accessing infrastructure data only")
            # Add infrastructure-only filter for platform admins
            infrastructure_filter = {
                '$or': [
                    {'category': 'infrastructure'},
                    {'category': 'platform'},
                    {'organization_id': {'$in': ['tesa-platform', 'infrastructure', 'monitoring']}},
                    {'name': {'$regex': '^(TESA|Infrastructure|Platform|Monitoring)', '$options': 'i'}}
                ]
            }
            # Merge with existing query
            if query:
                query = {'$and': [query, infrastructure_filter]}
            else:
                query = infrastructure_filter
            return query
        
        # Organization admin sees their org + sub-organizations
        if RBAC.is_organization_admin(user):
            user_org_id = user.get('organization_id', '')
            # TODO: Expand to include sub-organization IDs
            query['organization_id'] = user_org_id
            return query
        
        # Everyone else sees only their organization's data
        query['organization_id'] = user.get('organization_id', '')
        return query
    
    @staticmethod
    def has_device_access(user: dict, device: dict) -> bool:
        """
        Check if user has access to a specific device.
        
        Args:
            user: User object
            device: Device object
            
        Returns:
            bool: True if user has access, False otherwise
        """
        # Platform admins have access to all devices
        if RBAC.is_platform_admin(user):
            return True
            
        # Check organization match
        user_org = user.get('organization_id', '')
        device_org = device.get('organization_id', '')
        
        if not user_org or not device_org:
            return False
            
        return user_org == device_org

# Convenience functions for common permission checks
def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for an endpoint.
    
    Usage:
        @require_permission(Permission.DEVICE_CREATE)
        def create_device():
            ...
    """
    from functools import wraps
    from flask import g, jsonify
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                logger.warning(f"No current_user in context for permission check: {permission.value}")
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = g.current_user.get('role', '')
            user_email = g.current_user.get('email', 'unknown')
            logger.info(f"Permission check: {user_email} (role: {user_role}) requesting {permission.value}")
            
            if not RBAC.has_permission(user_role, permission):
                logger.warning(f"Access denied: {user_email} (role: {user_role}) lacks {permission.value}")
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin():
    """
    Decorator to require admin role for an endpoint.
    
    Usage:
        @require_admin()
        def admin_function():
            ...
    """
    from functools import wraps
    from flask import g, jsonify
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_role = g.current_user.get('role', '')
            if not RBAC.is_admin_role(user_role):
                logger.warning(f"Admin access denied: {g.current_user.get('email')}")
                return jsonify({'error': 'Admin access required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
