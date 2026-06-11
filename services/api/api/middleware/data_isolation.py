# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from functools import wraps
from flask import request, jsonify, current_app, g
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class DataIsolationMiddleware:
    """Enforce organization-based data isolation for multi-tenant security"""
    
    def __init__(self):
        self.bypass_paths = ['/api/v1/health', '/api/v1/auth/login', '/api/v1/auth/register']
    
    def get_user_organization(self, user_id):
        """Get user's organization ID from database"""
        try:
            user = current_app.db.users.find_one({'_id': ObjectId(user_id)})
            if user:
                return str(user.get('organization_id', ''))
            return None
        except Exception as e:
            logger.error(f"Error getting user organization: {str(e)}")
            return None
    
    def inject_organization_filter(self, collection_name, query=None):
        """Inject organization filter into MongoDB queries"""
        if query is None:
            query = {}
        
        # Get organization from request context
        org_id = getattr(g, 'organization_id', None)
        
        if org_id:
            # Add organization filter based on collection
            if collection_name in ['devices', 'certificates', 'telemetry', 'alerts']:
                query['organization_id'] = ObjectId(org_id)
            elif collection_name == 'users':
                # Users can only see users in their organization
                query['organization_id'] = ObjectId(org_id)
        
        return query
    
    def verify_resource_access(self, resource_type, resource_id):
        """Verify user has access to a specific resource"""
        org_id = getattr(g, 'organization_id', None)
        if not org_id:
            return False
        
        # Check resource belongs to user's organization
        collection_map = {
            'device': 'devices',
            'certificate': 'certificates',
            'user': 'users',
            'telemetry': 'telemetry',
            'alert': 'alerts'
        }
        
        collection = collection_map.get(resource_type)
        if not collection:
            return False
        
        try:
            resource = current_app.db[collection].find_one({
                '_id': ObjectId(resource_id),
                'organization_id': ObjectId(org_id)
            })
            return resource is not None
        except Exception as e:
            logger.error(f"Error verifying resource access: {str(e)}")
            return False
    
    def enforce_isolation(self, f):
        """Decorator to enforce data isolation on routes"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip for bypass paths
            if request.path in self.bypass_paths:
                return f(*args, **kwargs)
            
            # Get current user from existing auth system
            try:
                # Get user from g.current_user (set by require_auth decorator)
                if not hasattr(g, 'current_user') or not g.current_user:
                    return jsonify({'error': 'Authentication required'}), 401
                
                user_id = str(g.current_user.get('_id', ''))
                if not user_id:
                    return jsonify({'error': 'Authentication required'}), 401
                
                # Get and store organization ID
                org_id = g.current_user.get('organization_id', '')
                if not org_id:
                    org_id = self.get_user_organization(user_id)
                
                if not org_id:
                    return jsonify({'error': 'User organization not found'}), 403
                
                g.organization_id = org_id
                g.user_id = user_id
                
                # Check resource access if resource ID in URL
                if 'device_id' in kwargs:
                    if not self.verify_resource_access('device', kwargs['device_id']):
                        return jsonify({'error': 'Access denied to this device'}), 403
                
                if 'certificate_id' in kwargs:
                    if not self.verify_resource_access('certificate', kwargs['certificate_id']):
                        return jsonify({'error': 'Access denied to this certificate'}), 403
                
                if 'user_id' in kwargs and kwargs['user_id'] != user_id:
                    # Users can only access their own profile or users in their org
                    if not self.verify_resource_access('user', kwargs['user_id']):
                        return jsonify({'error': 'Access denied to this user'}), 403
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Data isolation error: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500
        
        return decorated_function
    
    def get_isolated_query(self, base_query=None):
        """Get a query with organization filter applied"""
        if base_query is None:
            base_query = {}
        
        org_id = getattr(g, 'organization_id', None)
        if org_id:
            base_query['organization_id'] = ObjectId(org_id)
        
        return base_query
    
    def sanitize_response(self, data):
        """Remove sensitive fields from response data"""
        if isinstance(data, dict):
            # Remove internal fields
            sensitive_fields = ['password', 'secret_key', 'api_token', '__v']
            for field in sensitive_fields:
                data.pop(field, None)
            
            # Recursively sanitize nested objects
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    data[key] = self.sanitize_response(value)
        
        elif isinstance(data, list):
            return [self.sanitize_response(item) for item in data]
        
        return data

# Singleton instance
data_isolation = DataIsolationMiddleware()

# Helper functions for use in routes
def get_organization_filter():
    """Get organization filter for current request"""
    return data_isolation.get_isolated_query()

def verify_device_access(device_id):
    """Verify current user has access to device"""
    return data_isolation.verify_resource_access('device', device_id)

def verify_user_access(user_id):
    """Verify current user has access to user data"""
    return data_isolation.verify_resource_access('user', user_id)