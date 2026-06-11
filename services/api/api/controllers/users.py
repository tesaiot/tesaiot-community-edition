# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - User Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from ..services import user_service
from ..services.user_service_otp import create_user_with_otp
from ..core.auth import require_auth
from ..core.rbac import RBAC, Permission, require_permission

# Create blueprint
users_bp = Blueprint('users', __name__)
logger = logging.getLogger(__name__)

def fix_user_data(user_data):
    """Fix user data to prevent empty strings"""
    if user_data.get('organization') == '':
        user_data['organization'] = 'Unknown'
    if user_data.get('organization_id') == '':
        user_data['organization_id'] = 'unknown'
    if user_data.get('name') == '':
        user_data['name'] = user_data.get('email', 'Unknown User')
    return user_data

# Profile endpoints

@users_bp.route('/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get current user profile (alias for /me endpoint)"""
    return get_current_user_profile()

@users_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user_profile():
    """Get current user info"""
    try:
        current_user = g.current_user
        
        # Special handling for platform admin user
        if RBAC.is_platform_admin(current_user):
            user_data = {
                'id': current_user.get('_id', '507f1f77bcf86cd799439011'),
                'email': current_user.get('email'),
                'name': current_user.get('name', 'Platform Admin'),
                'role': current_user.get('role', 'platform_admin'),
                'organization': 'TESA Platform Infrastructure',
                'organization_id': 'tesa-platform',
                'permissions': {
                    'platform_manage': True,
                    'platform_view_all': True,
                    'platform_infrastructure': True,
                    'platform_monitoring': True,
                    # NO customer data access permissions
                    'users': [],
                    'devices': [],
                    'organizations': []
                },
                'vault_authenticated': True
            }
            return jsonify(user_data), 200
        
        user_id = current_user.get('_id') or current_user.get('id')
        
        # For environment-based users (not in DB), use current_user data directly
        user = user_service.get_user_by_id(user_id)
        if not user:
            # Check if this is an environment credential user
            if current_user.get('email') and current_user.get('role'):
                # Environment user not in database - use current_user data
                user = current_user.copy()  # Use the data from JWT/auth middleware
                # Ensure we have the required fields for environment users
                if not user.get('name'):
                    user['name'] = user.get('email', '').split('@')[0]
                if not user.get('organization'):
                    if RBAC.is_platform_admin(user):
                        user['organization'] = 'TESA Platform Infrastructure'
                    else:
                        user['organization'] = 'Environment User'
                if not user.get('organization_id'):
                    if RBAC.is_platform_admin(user):
                        user['organization_id'] = 'tesa-platform'
                    else:
                        user['organization_id'] = 'env-user'
            else:
                return jsonify({'error': 'User not found'}), 404
        
        # Get permissions
        permissions = user_service.get_user_permissions(user)
        
        # Convert organization ObjectId to string if needed
        org_value = user.get('organization', '')
        if hasattr(org_value, '__str__') and not isinstance(org_value, str):
            org_value = str(org_value)
        
        user_data = {
            'id': str(user.get('_id', user.get('id', ''))),
            'email': user['email'],
            'name': user.get('name', ''),
            'role': user.get('role', 'user'),
            'organization': org_value,
            'organization_id': str(user.get('organization_id', '')) if user.get('organization_id') else '',
            'avatar': user.get('avatar', ''),
            'phone': user.get('phone', ''),
            'department': user.get('department', ''),
            'position': user.get('position', ''),
            'permissions': permissions
        }
        
        # Apply fix_user_data to ensure no empty strings and convert ObjectIds
        user_data = fix_user_data(user_data)
        
        return jsonify(user_data), 200
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500

@users_bp.route('/me', methods=['PUT', 'PATCH'])
@require_auth
def update_current_user_profile():
    """
    Update current user's own profile.
    Users can update their own profile information.
    """
    try:
        current_user = g.current_user
        user_id = current_user.get('_id') or current_user.get('id')
        data = request.get_json()
        
        # Fields that users can update themselves
        allowed_fields = [
            'name', 'phone', 'department', 'title', 
            'bio', 'location', 'avatar_url'
        ]
        
        # Filter to only allowed fields
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Validate phone number if provided
        if 'phone' in update_data and update_data['phone']:
            phone = update_data['phone'].strip()
            if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                return jsonify({'error': 'Invalid phone number format'}), 400
        
        # Update user profile
        success = user_service.update_user_profile(user_id, update_data)
        
        if success:
            # Get updated user data
            updated_user = user_service.get_user_by_id(user_id)
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'user': fix_user_data(updated_user)
            }), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
            
    except Exception as e:
        logger.error(f"Error updating current user profile: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

@users_bp.route('/me/change-password', methods=['POST'])
@require_auth
def change_own_password():
    """
    Change current user's password.
    Requires current password verification.
    """
    try:
        current_user = g.current_user
        user_id = current_user.get('_id') or current_user.get('id')
        data = request.get_json()
        
        # Validate required fields
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check password confirmation
        if new_password != confirm_password:
            return jsonify({'error': 'New passwords do not match'}), 400
        
        # Validate password complexity
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        has_upper = any(c.isupper() for c in new_password)
        has_lower = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        
        if not (has_upper and has_lower and has_digit):
            return jsonify({
                'error': 'Password must contain at least one uppercase letter, one lowercase letter, and one number'
            }), 400
        
        # Verify current password and change to new one
        success = user_service.change_user_password(
            user_id, 
            current_password, 
            new_password
        )
        
        if success:
            # Log security event
            logger.info(f"Password changed for user {current_user.get('email')}")
            
            return jsonify({
                'success': True,
                'message': 'Password changed successfully. Please login with your new password.'
            }), 200
        else:
            return jsonify({'error': 'Current password is incorrect'}), 401
            
    except Exception as e:
        logger.error(f"Error changing password for user: {e}")
        return jsonify({'error': 'Failed to change password'}), 500

@users_bp.route('/me/preferences', methods=['GET'])
@require_auth
def get_user_preferences():
    """Get current user's preferences"""
    try:
        current_user = g.current_user
        user_id = current_user.get('_id') or current_user.get('id')
        
        preferences = user_service.get_user_preferences(user_id)
        
        # Default preferences if none exist
        if not preferences:
            preferences = {
                'theme': 'light',
                'language': 'en',
                'timezone': 'Asia/Bangkok',
                'date_format': 'DD/MM/YYYY',
                'notifications': {
                    'email': True,
                    'push': False,
                    'sms': False
                }
            }
        
        return jsonify(preferences), 200
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return jsonify({'error': 'Failed to get preferences'}), 500

@users_bp.route('/me/preferences', methods=['PUT'])
@require_auth
def update_user_preferences():
    """Update current user's preferences"""
    try:
        current_user = g.current_user
        user_id = current_user.get('_id') or current_user.get('id')
        data = request.get_json()
        
        # Validate theme
        if 'theme' in data and data['theme'] not in ['light', 'dark', 'auto']:
            return jsonify({'error': 'Invalid theme value'}), 400
        
        # Validate language
        if 'language' in data and data['language'] not in ['en', 'th']:
            return jsonify({'error': 'Invalid language value'}), 400
        
        success = user_service.update_user_preferences(user_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Preferences updated successfully',
                'preferences': data
            }), 200
        else:
            return jsonify({'error': 'Failed to update preferences'}), 500
            
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        return jsonify({'error': 'Failed to update preferences'}), 500

# User management endpoints
@users_bp.route('/', methods=['GET'])
@users_bp.route('/list', methods=['GET'])
@require_auth
@require_permission(Permission.USER_VIEW)
def get_users():
    """
    Get users list - filtered by organization.
    
    Organization admins can see users from their organization.
    Platform admins can access all user data for platform management.
    
    Returns:
        200: List of users
        500: Server error
    """
    try:
        current_user = g.current_user
        
        users = user_service.get_all_users(current_user)
        
        # Apply fixes to prevent empty strings
        for user in users:
            fix_user_data(user)
        
        return jsonify({'success': True, 'users': users}), 200
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Failed to get users'}), 500

@users_bp.route('/', methods=['POST'])
@require_auth
@require_permission(Permission.USER_CREATE)
def create_user():
    """Create new user (legacy - with temporary password)"""
    try:
        current_user = g.current_user
        data = request.get_json()
        
        # Create user
        user, password = user_service.create_user(data, current_user)
        
        if not user:
            return jsonify({'error': password}), 400
        
        return jsonify({
            'user': user,
            'temp_password': password
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@users_bp.route('/create-with-otp', methods=['POST'])
@require_auth
@require_permission(Permission.USER_CREATE)
def create_user_otp():
    """Create new user with OTP email verification (no password required)"""
    try:
        current_user = g.current_user
        data = request.get_json()
        
        # Create user with OTP
        user, message = create_user_with_otp(data, current_user)
        
        if not user:
            return jsonify({'error': message}), 400
        
        return jsonify({
            'success': True,
            'user': user,
            'message': message
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating user with OTP: {e}")
        return jsonify({'error': 'Failed to create user'}), 500

@users_bp.route('/<user_id>', methods=['PUT'])
@require_auth
@require_permission(Permission.USER_UPDATE)
def update_user(user_id):
    """Update user"""
    try:
        current_user = g.current_user
        data = request.get_json()
        
        success = user_service.update_user(user_id, data, current_user)
        
        if not success:
            return jsonify({'error': 'User not found or update failed'}), 404
        
        return jsonify({'message': 'User updated'}), 200
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

@users_bp.route('/<user_id>/reset-password', methods=['POST'])
@require_auth
def reset_user_password(user_id):
    """Reset user password"""
    try:
        current_user = g.current_user
        
        success, result = user_service.reset_user_password(user_id, current_user)
        
        if not success:
            return jsonify({'error': result}), 403
        
        return jsonify({
            'message': 'Password reset successfully',
            'temp_password': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return jsonify({'error': 'Failed to reset password'}), 500

@users_bp.route('/<user_id>', methods=['DELETE'])
@require_auth
@require_permission(Permission.USER_DELETE)
def delete_user(user_id):
    """Delete a user"""
    try:
        current_user = g.current_user
        logger.info(f"Delete request for user {user_id} by {current_user.get('email')} (role: {current_user.get('role')})")
        
        success, message = user_service.delete_user(user_id, current_user)
        
        if not success:
            return jsonify({'error': message}), 403
        
        return jsonify({'message': message}), 200
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An unexpected error occurred',
                'timestamp': datetime.now().isoformat(),
                'error_id': f'ERR-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }
        }), 500

@users_bp.route('/<user_id>/deactivate', methods=['POST'])
@require_auth
def deactivate_user_endpoint(user_id):
    """Deactivate a user account"""
    try:
        current_user = g.current_user
        
        success, user_info = user_service.deactivate_user(user_id, current_user)
        
        if not success:
            return jsonify({'error': 'User not found or deactivation failed'}), 404
        
        logger.info(f"User {user_info['email']} deactivated by {current_user.get('email')}")
        
        return jsonify({
            'message': 'User deactivated successfully',
            'user_id': user_info['user_id'],
            'email': user_info['email']
        }), 200
        
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        return jsonify({'error': 'Failed to deactivate user'}), 500

@users_bp.route('/<user_id>/activate', methods=['POST'])
@require_auth
def activate_user_endpoint(user_id):
    """Activate a user account"""
    try:
        current_user = g.current_user
        
        success, user_info = user_service.activate_user(user_id, current_user)
        
        if not success:
            return jsonify({'error': 'User not found or activation failed'}), 404
        
        logger.info(f"User {user_info['email']} activated by {current_user.get('email')}")
        
        return jsonify({
            'message': 'User activated successfully',
            'user_id': user_info['user_id'],
            'email': user_info['email']
        }), 200
        
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        return jsonify({'error': 'Failed to activate user'}), 500

@users_bp.route('/<user_id>/activity', methods=['GET'])
@require_auth
def get_user_activity(user_id):
    """Get user activity log"""
    try:
        current_user = g.current_user
        
        # Check permissions - admin or viewing own activity
        if current_user.get('role') not in ['admin', 'super_admin'] and current_user.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        limit = request.args.get('limit', 50, type=int)
        activities = user_service.get_user_activity_log(user_id, limit)
        
        return jsonify({
            'success': True,
            'activities': activities
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        return jsonify({'error': 'Failed to get activity log'}), 500

