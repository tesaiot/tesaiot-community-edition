# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - User Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import jwt
import json
import secrets
import bcrypt
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bson import ObjectId

from ..core.database import get_db, get_redis, get_vault
from ..core.rbac import RBAC, Permission
from ..core.config import Config
from ..services.notification_acl_service import create_notification_safe

import sys
sys.path.append('/app/audit')

from api.tolerance_methods.exception_handling import (
    with_error_handling, ErrorSeverity, ErrorCategory
)
from api.tolerance_methods.retry import (
    with_retry, RetryPolicy, CircuitBreaker, with_timeout
)
from api.tolerance_methods.validation import (
    validate_email, sanitize_string, ValidationError
)

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.getenv('JWT_SECRET')
if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable must be set")
JWT_ALGORITHM = 'HS256'

# Circuit breakers for authentication operations
auth_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=300)
vault_auth_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)

def create_user_in_vault(username, password):
    """
    Create user in Vault UserPass backend with fallback to bcrypt.
    
    Args:
        username: Vault username
        password: User password
        
    Returns:
        tuple: (success, password_hash) - hash is None if Vault successful
    """
    # Try Vault first if available and not in development mode
    vault_client = get_vault()
    if vault_client and not Config.is_development_mode():
        try:
            vault_client.auth.userpass.create_or_update_user(
                username=username,
                password=password,
                policies=['default']
            )
            logger.info(f"Created Vault user: {username}")
            return True, None
        except Exception as e:
            logger.warning(f"Failed to create Vault user, falling back to bcrypt: {e}")
    
    # Fallback to bcrypt hash storage
    try:
        security_config = Config.get_config().get_security_config()
        salt = bcrypt.gensalt(rounds=security_config.bcrypt_log_rounds)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        logger.info(f"Generated bcrypt hash for user: {username}")
        return True, password_hash
    except Exception as e:
        logger.error(f"Failed to create bcrypt hash: {e}")
        return False, None

def verify_vault_password(username, password, user_data=None):
    """
    Verify password against Vault with bcrypt fallback.
    
    Args:
        username: Vault username
        password: Password to verify
        user_data: User database record (for bcrypt hash)
        
    Returns:
        bool: True if valid
    """
    # Try Vault first if available and not in development mode
    vault_client = get_vault()
    if vault_client and not Config.is_development_mode():
        try:
            # Try to login with userpass
            import hvac
            temp_client = hvac.Client(url=os.getenv('VAULT_ADDR', 'http://localhost:8200'), timeout=2)
            resp = temp_client.auth.userpass.login(
                username=username,
                password=password
            )
            logger.debug(f"Vault authentication successful for {username}")
            return True
        except Exception as e:
            logger.warning(f"Vault auth failed for {username}, trying bcrypt fallback: {str(e)}")
    
    # Bcrypt fallback - check stored hash
    if user_data and user_data.get('password_hash'):
        try:
            password_hash = user_data['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), password_hash):
                logger.debug(f"Bcrypt authentication successful for {username}")
                return True
        except Exception as e:
            logger.warning(f"Bcrypt verification failed for {username}: {e}")
    
    # Development fallback - use environment variables only
    if Config.is_development_mode():
        admin_creds = Config.get_admin_credentials()
        
        # Check admin credentials from environment
        if (username == admin_creds['bdh_admin']['username'] and 
            password == admin_creds['bdh_admin']['password'] and
            admin_creds['bdh_admin']['password']):
            return True
        elif (username == admin_creds['org_admin']['username'] and 
              password == admin_creds['org_admin']['password'] and
              admin_creds['org_admin']['password']):
            return True
        elif (username == admin_creds['platform_admin']['username'] and 
              password == admin_creds['platform_admin']['password'] and
              admin_creds['platform_admin']['password']):
            return True
    
    return False

def migrate_user_to_hybrid_auth(user_id, password):
    """
    Migrate existing Vault-only user to hybrid Vault/bcrypt authentication.
    This creates a bcrypt hash backup when Vault is unavailable.
    
    Args:
        user_id: User identifier
        password: User's current password
        
    Returns:
        bool: True if migration successful
    """
    try:
        db = get_db()
        if db is None:
            return False
        
        user = db.users.find_one({'_id': user_id})
        if not user:
            return False
        
        # Skip if user already has bcrypt hash
        if user.get('password_hash'):
            return True
        
        # Generate bcrypt hash
        security_config = Config.get_config().get_security_config()
        salt = bcrypt.gensalt(rounds=security_config.bcrypt_log_rounds)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Update user with bcrypt hash
        result = db.users.update_one(
            {'_id': user_id},
            {'$set': {
                'password_hash': password_hash,
                'auth_migrated_at': datetime.now(),
                'auth_mode': 'hybrid'  # Vault + bcrypt fallback
            }}
        )
        
        if result.modified_count > 0:
            logger.info(f"Migrated user {user.get('email')} to hybrid authentication")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error migrating user to hybrid auth: {e}")
        return False

def generate_jwt_token(user):
    """
    Generate JWT token for authenticated user.
    
    Args:
        user: User object
        
    Returns:
        str: JWT token
    """
    canonical_role = RBAC.canonicalize_role(user.get('role', 'user'))

    token_payload = {
        'user_id': str(user['_id']),
        'email': user['email'],
        'name': user.get('name', ''),
        'role': canonical_role,
        'organization': user.get('organization', ''),
        'organization_id': user.get('organization_id', ''),
        'exp': datetime.now() + timedelta(hours=24)
    }
    
    return jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    """
    Verify JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        dict: Token payload or None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None

@auth_circuit_breaker
@with_timeout(timeout_seconds=10)
@with_retry(max_retries=2, delay=1.0, backoff_policy=RetryPolicy.LINEAR_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.AUTHENTICATION,
    user_message="Authentication failed. Please try again.",
    return_on_error=(None, None)
)
def authenticate_user(email, password):
    """
    Authenticate user with email and password.
    
    Args:
        email: User email
        password: User password
        
    Returns:
        tuple: (user, token) or (None, None)
    """
    # Validate and sanitize inputs
    if not validate_email(email):
        raise ValidationError("Invalid email format")
    
    email = sanitize_string(email.lower().strip())
    
    # Basic password validation for authentication
    if not password or len(password) < 1:
        raise ValidationError("Password is required")
    
    try:
        db = get_db()
        redis_client = get_redis()
        
        # Find user in database
        user = db.users.find_one({'email': email.lower()})
        if not user:
            # Development mode fallback - use environment variables
            if Config.is_development_mode():
                admin_creds = Config.get_admin_credentials()
                
                # Check against environment credentials only
                if (password == admin_creds['org_admin']['password'] and
                    admin_creds['org_admin']['password'] and
                    admin_creds['org_admin']['email'] == email):
                    test_user = {'email': email, 'role': 'super_admin'}
                    if RBAC.is_platform_admin(test_user):
                        user = {
                            '_id': '507f1f77bcf86cd799439011',
                            'email': email,
                            'name': 'Platform Admin',
                            'role': 'super_admin',
                            'organization': 'TESA',
                            'organization_id': 'tesa-org',
                            'vault_user': admin_creds['org_admin']['username']
                        }
            
            if not user:
                return None, None
        
        # Get vault username
        vault_user = user.get('vault_user')
        if not vault_user:
            # Use environment-based mapping
            admin_creds = Config.get_admin_credentials()
            
            if email == admin_creds['bdh_admin']['email']:
                vault_user = admin_creds['bdh_admin']['username']
            elif email == admin_creds['org_admin']['email']:
                vault_user = admin_creds['org_admin']['username']
            elif email == admin_creds['platform_admin']['email']:
                vault_user = admin_creds['platform_admin']['username']
            else:
                return None, None
        
        # Verify password with Vault/bcrypt fallback
        if not verify_vault_password(vault_user, password, user):
            return None, None
        
        # Auto-migrate to hybrid auth if successful Vault login but no bcrypt hash
        # This provides fallback capability for future Vault outages
        if not Config.is_development_mode() and not user.get('password_hash'):
            try:
                migrate_user_to_hybrid_auth(str(user.get('_id')), password)
            except Exception as e:
                logger.warning(f"Failed to auto-migrate user to hybrid auth: {e}")
        
        # Generate JWT token
        token = generate_jwt_token(user)
        
        # Store session in Redis
        if redis_client:
            session_key = f"session:{token[:20]}"
            redis_client.setex(session_key, 86400, json.dumps({
                'user_id': str(user['_id']),
                'email': user['email'],
                'login_time': datetime.now().isoformat()
            }))
        
        user['role'] = RBAC.canonicalize_role(user.get('role', 'user'))

        return user, token
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None, None

def logout_user(token):
    """
    Logout user by invalidating session.
    
    Args:
        token: JWT token
        
    Returns:
        bool: True if successful
    """
    try:
        redis_client = get_redis()
        if redis_client:
            session_key = f"session:{token[:20]}"
            redis_client.delete(session_key)
        return True
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return False

def get_user_by_id(user_id, current_user=None):
    """
    Get user by ID with organization validation.
    
    Args:
        user_id: User identifier
        current_user: Current user for ACL check
        
    Returns:
        dict: User object or None
    """
    try:
        db = get_db()
        
        # If database is unavailable and we're looking for current user, return current_user data
        if db is None and current_user and (
            str(current_user.get('_id', '')) == str(user_id) or 
            str(current_user.get('id', '')) == str(user_id)
        ):
            logger.info("Database unavailable - returning current user data for environment credential user")
            return current_user
        elif db is None:
            return None
        
        # Try to find by string ID first, then by ObjectId
        user = db.users.find_one({'_id': user_id})
        if not user:
            try:
                user = db.users.find_one({'_id': ObjectId(user_id)})
            except:
                pass
        
        if not user:
            return None

        user['role'] = RBAC.canonicalize_role(user.get('role', 'user'))

        # SECURITY: Validate organization access
        if current_user:
            # SECURITY: Platform admins can NEVER access customer user data
            if RBAC.is_platform_admin(current_user):
                logger.warning(f"[SECURITY] Platform admin {current_user.get('email')} attempted to access user {user_id} - DENIED")
                return None
                
            # Check if user belongs to same organization
            user_org_id = str(user.get('organization_id', ''))
            current_org_id = str(current_user.get('organization_id', ''))
            
            # Handle both ObjectId and string comparisons
            # Also check if they're both references to the same org (e.g., both 'infineon')
            org_match = False
            
            # Direct string match
            if user_org_id == current_org_id:
                org_match = True
            # Check if both are the same organization string ID (e.g., 'infineon')
            elif user_org_id and current_org_id:
                # Both might be organization string IDs like 'infineon'
                if user_org_id.lower() == current_org_id.lower():
                    org_match = True
                # Check if one is an ObjectId and fetch the org to compare
                else:
                    try:
                        # Check if either is an ObjectId and resolve to org string ID
                        if ObjectId.is_valid(user_org_id) and not ObjectId.is_valid(current_org_id):
                            # user_org_id is ObjectId, current_org_id is string
                            org = db.organizations.find_one({'_id': ObjectId(user_org_id)})
                            if org and org.get('organization_id', '').lower() == current_org_id.lower():
                                org_match = True
                        elif ObjectId.is_valid(current_org_id) and not ObjectId.is_valid(user_org_id):
                            # current_org_id is ObjectId, user_org_id is string
                            org = db.organizations.find_one({'_id': ObjectId(current_org_id)})
                            if org and org.get('organization_id', '').lower() == user_org_id.lower():
                                org_match = True
                    except:
                        pass
            
            if not org_match:
                logger.warning(f"Access denied: {current_user.get('email')} (org: {current_org_id}) tried to access user from different org (org: {user_org_id})")
                return None
        
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def get_all_users(current_user):
    """
    Get users filtered by permissions and organization.
    
    Args:
        current_user: Current user object
        
    Returns:
        list: List of users
    """
    try:
        # Check permissions - need user view permission
        if not RBAC.has_permission(current_user.get('role', ''), Permission.USER_VIEW):
            logger.info(f"User {current_user.get('email')} lacks USER_VIEW permission")
            return []
        
        # SECURITY: Platform admins can NEVER access customer user data
        if RBAC.is_platform_admin(current_user):
            logger.warning(f"[SECURITY] Platform admin {current_user.get('email')} attempted to access user list - DENIED")
            # Platform admins see NO customer users
            return []
        
        db = get_db()
        if db is None:
            # Database unavailable - for environment users, return minimal data
            logger.warning("Database unavailable - returning current user only for environment credential users")
            if current_user.get('email') and current_user.get('role'):
                # Return just the current user formatted properly
                canonical_role = RBAC.canonicalize_role(current_user.get('role', 'user'))

                return [{
                    '_id': str(current_user.get('_id', current_user.get('id', ''))),
                    'email': current_user.get('email'),
                    'name': current_user.get('name', ''),
                    'role': canonical_role,
                    'organization': current_user.get('organization', ''),
                    'organization_id': current_user.get('organization_id', ''),
                    'status': current_user.get('status', 'active'),
                    'created_at': current_user.get('created_at', ''),
                    'last_login': current_user.get('last_login', ''),
                    'avatar': current_user.get('avatar', ''),
                    'pic': current_user.get('pic', '')
                }]
            else:
                return []
        
        # Organization admin only sees users from their organization
        user_org_id = current_user.get('organization_id', '')
        user_org_name = current_user.get('organization', '') or current_user.get('organization_name', '')
        
        # Find the organization to get both ObjectId and string ID
        org_filter = {}
        if user_org_id:
            if ObjectId.is_valid(user_org_id):
                org_filter = {'_id': ObjectId(user_org_id)}
            else:
                org_filter = {'organization_id': user_org_id}
        elif user_org_name:
            org_filter = {'name': user_org_name}
        
        users = []
        if org_filter:
            org = db.organizations.find_one(org_filter)
            if org:
                org_object_id = str(org['_id'])
                org_string_id = org.get('organization_id', '')
                
                # SECURITY: Only filter by organization_id, not organization name
                # to prevent cross-organization data leakage
                user_filter = {
                    '$or': [
                        {'organization_id': org_object_id},
                        {'organization_id': org_string_id}
                    ]
                }
                users = list(db.users.find(user_filter))
                
                logger.info(f"Found {len(users)} users for org: {org.get('name')} (ObjectId: {org_object_id}, StringId: {org_string_id})")
            else:
                logger.warning(f"Organization not found for user: {current_user.get('email')}")
        else:
            # If no organization found, but we have a valid user, return just the current user
            if current_user.get('email') and current_user.get('role'):
                users = [current_user]
        
        # Format response
        result = []
        for user in users:
            def convert_objectid_to_string(value):
                """Convert ObjectId fields to strings to prevent JSON serialization errors"""
                if isinstance(value, ObjectId):
                    return str(value)
                elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    # Handle other non-serializable types by converting to string
                    return str(value)
                else:
                    return value
                    
            canonical_role = RBAC.canonicalize_role(user.get('role', 'user'))

            user_data = {
                '_id': str(user.get('_id', user.get('id', ''))),
                'email': user.get('email', ''),
                'name': user.get('name', ''),
                'role': canonical_role,
                'organization': convert_objectid_to_string(user.get('organization', '')),
                'organization_id': convert_objectid_to_string(user.get('organization_id', '')),
                'status': user.get('status', 'active'),
                'created_at': convert_objectid_to_string(user.get('created_at', '')),
                'last_login': convert_objectid_to_string(user.get('last_login', '')),
                'avatar': user.get('avatar', ''),  # Include avatar field
                'pic': user.get('pic', '')  # Also include pic field as fallback
            }
            result.append(user_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        # Return empty list instead of raising exception
        return []

def create_user(data, current_user):
    """
    Create new user with organization validation.
    
    Args:
        data: User data
        current_user: Current user
        
    Returns:
        tuple: (user, temp_password) or (None, error_message)
    """
    try:
        db = get_db()
        
        # Check permissions - need user create permission
        if not RBAC.has_permission(current_user.get('role', ''), Permission.USER_CREATE):
            return None, 'Insufficient permissions to create users'
        
        email = data.get('email', '').lower()
        requested_role = RBAC.canonicalize_role(data.get('role', 'user'))

        # Check if user exists
        existing_user = db.users.find_one({'email': email})
        if existing_user is not None:
            return None, 'User already exists'
        
        # SECURITY: Enforce organization boundaries
        if not RBAC.is_platform_admin(current_user):
            # Force new user to be in same organization as creator
            data['organization_id'] = current_user.get('organization_id', '')
            data['organization'] = current_user.get('organization', '')
            
            # Validate organization_id if provided
            if 'organization_id' in data and data['organization_id'] != current_user.get('organization_id'):
                logger.warning(f"Access denied: {current_user.get('email')} tried to create user in different org")
                return None, 'Cannot create users in other organizations'
        
        # Generate vault username
        vault_user = email.split('@')[0].replace('.', '_')
        
        # Generate password if not provided
        password = data.get('password', secrets.token_urlsafe(12))
        
        # Create user in Vault with bcrypt fallback
        vault_success, password_hash = create_user_in_vault(vault_user, password)
        if not vault_success:
            return None, 'Failed to create user authentication'
        
        # Create user in database
        user = {
            '_id': str(ObjectId()),
            'email': email,
            'name': data.get('name', ''),
            'role': requested_role,
            'organization': data.get('organization', ''),
            'organization_id': data.get('organization_id', ''),
            'vault_user': vault_user,
            'status': 'active',
            'created_at': datetime.now(),
            'created_by': current_user.get('email')
        }
        
        # Store bcrypt hash if Vault wasn't used
        if password_hash:
            user['password_hash'] = password_hash
            logger.info(f"User {email} created with bcrypt authentication")
        else:
            logger.info(f"User {email} created with Vault authentication")
        
        db.users.insert_one(user)
        user['created_at'] = user['created_at'].isoformat()

        org_id_str = str(user.get('organization_id') or current_user.get('organization_id') or '')
        creator_name = current_user.get('name') or current_user.get('email')
        user_name = user.get('name') or user.get('email')

        if org_id_str:
            create_notification_safe({
                'type': 'user',
                'subtype': 'user_created',
                'title': 'New user added',
                'message': f"{user_name} was added to the organization by {creator_name}.",
                'organization_id': org_id_str,
                'recipient_type': 'organization',
                'recipient_id': org_id_str,
                'severity': 'info',
                'priority': 'medium',
                'metadata': {
                    'user_id': user['_id'],
                    'user_email': user.get('email'),
                    'created_by': creator_name,
                }
            })

        create_notification_safe({
            'type': 'user',
            'subtype': 'user_created',
            'title': 'Welcome to TESAIoT Platform',
            'message': 'Your account has been created and is ready to use.',
            'organization_id': org_id_str or None,
            'recipient_type': 'user',
            'recipient_id': user['_id'],
            'severity': 'info',
            'priority': 'medium',
            'metadata': {
                'temporary_password_issued': 'password' in data,
                'created_by': creator_name,
            }
        })

        return user, password
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None, 'Failed to create user'

def update_user(user_id, data, current_user):
    """
    Update user information with organization validation.
    
    Args:
        user_id: User identifier
        data: Update data
        current_user: Current user
        
    Returns:
        bool: True if successful
    """
    try:
        db = get_db()
        
        # Check permissions
        current_user_role = RBAC.canonicalize_role(current_user.get('role', 'user'))
        if current_user_role not in ['admin', 'super_admin', 'organization_admin']:
            return False
        
        # SECURITY: Verify user belongs to same organization
        target_user = get_user_by_id(user_id, current_user)
        if not target_user:
            logger.warning(f"Access denied: {current_user.get('email')} tried to update user in different org")
            return False
        
        # SECURITY: NEVER allow changing organization across customer boundaries
        if 'organization_id' in data or 'organization' in data:
            # Platform admins cannot modify customer data
            if RBAC.is_platform_admin(current_user):
                logger.warning(f"[SECURITY] Platform admin {current_user.get('email')} tried to change user organization - DENIED")
                return False
            # Regular users/admins cannot change organizations
            logger.warning(f"Access denied: {current_user.get('email')} tried to change user organization")
            return False
        
        # Build update data
        update_data = {
            'updated_at': datetime.now(),
            'updated_by': current_user.get('email')
        }

        previous_role = RBAC.canonicalize_role(target_user.get('role'))
        new_role = RBAC.canonicalize_role(data.get('role', previous_role))
        role_changed = new_role != previous_role

        if 'name' in data:
            update_data['name'] = data['name']
        if 'role' in data:
            update_data['role'] = new_role
        if 'organization' in data:
            update_data['organization'] = data['organization']
        if 'organization_id' in data:
            update_data['organization_id'] = data['organization_id']
        
        result = db.users.update_one(
            {'_id': user_id},
            {'$set': update_data}
        )
        
        if result.modified_count > 0 and role_changed:
            org_id_str = str(target_user.get('organization_id') or current_user.get('organization_id') or '')
            updated_by = current_user.get('name') or current_user.get('email')
            target_name = target_user.get('name') or target_user.get('email')
            create_notification_safe({
                'type': 'user',
                'subtype': 'role_changed',
                'title': 'User role updated',
                'message': f"{target_name} role changed from {previous_role} to {new_role} by {updated_by}.",
                'organization_id': org_id_str or None,
                'recipient_type': 'organization' if org_id_str else 'user',
                'recipient_id': org_id_str if org_id_str else str(target_user.get('_id')),
                'severity': 'info',
                'priority': 'medium',
                'metadata': {
                    'user_id': str(target_user.get('_id')),
                    'previous_role': previous_role,
                    'new_role': new_role,
                    'updated_by': updated_by,
                }
            })

            create_notification_safe({
                'type': 'user',
                'subtype': 'role_changed',
                'title': 'Your role has been updated',
                'message': f"Your account role is now {new_role}.",
                'organization_id': org_id_str or None,
                'recipient_type': 'user',
                'recipient_id': str(target_user.get('_id')),
                'severity': 'info',
                'priority': 'medium',
                'metadata': {
                    'previous_role': previous_role,
                    'new_role': new_role,
                    'updated_by': updated_by,
                }
            })

        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False

def reset_user_password(user_id, current_user):
    """
    Reset user password with organization validation.
    
    Args:
        user_id: User identifier
        current_user: Current user
        
    Returns:
        tuple: (success, new_password) or (False, error_message)
    """
    try:
        db = get_db()
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'super_admin', 'organization_admin']:
            return False, 'Admin access required'
        
        # SECURITY: Verify user belongs to same organization
        user = get_user_by_id(user_id, current_user)
        if not user:
            logger.warning(f"Access denied: {current_user.get('email')} tried to reset password for user in different org")
            return False, 'User not found or access denied'
        
        # Generate new password
        new_password = secrets.token_urlsafe(12)
        
        # Update in Vault with bcrypt fallback
        vault_user = user.get('vault_user')
        if vault_user:
            vault_success, password_hash = create_user_in_vault(vault_user, new_password)
            if not vault_success:
                return False, 'Failed to update password'
            
            # Update bcrypt hash in database if used
            if password_hash:
                db.users.update_one(
                    {'_id': user_id},
                    {'$set': {'password_hash': password_hash}}
                )
            else:
                # Remove bcrypt hash if Vault was used
                db.users.update_one(
                    {'_id': user_id},
                    {'$unset': {'password_hash': ''}}
                )
        
        # Update password reset info
        db.users.update_one(
            {'_id': user_id},
            {'$set': {
                'password_reset_at': datetime.now(),
                'password_reset_by': current_user.get('email')
            }}
        )
        
        org_id_str = str(user.get('organization_id') or current_user.get('organization_id') or '')
        create_notification_safe({
            'type': 'user',
            'subtype': 'password_reset',
            'title': 'Password reset completed',
            'message': 'A new password was generated for your account.',
            'organization_id': org_id_str or None,
            'recipient_type': 'user',
            'recipient_id': str(user.get('_id')),
            'severity': 'info',
            'priority': 'medium',
            'metadata': {
                'reset_by': current_user.get('email'),
                'timestamp': datetime.now().isoformat()
            }
        })

        return True, new_password
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return False, 'Failed to reset password'

def delete_user(user_id, current_user):
    """
    Delete a user with organization validation.
    
    Args:
        user_id: User identifier
        current_user: Current user
        
    Returns:
        tuple: (success, message)
    """
    try:
        logger.info(f"delete_user called: user_id={user_id}, by {current_user.get('email')}")
        
        db = get_db()
        vault_client = get_vault()
        
        # Check permissions - must have USER_DELETE permission
        user_role = current_user.get('role', '')
        logger.info(f"Checking USER_DELETE permission for role: {user_role}")
        
        if not RBAC.has_permission(user_role, Permission.USER_DELETE):
            logger.warning(f"User {current_user.get('email')} with role {user_role} lacks USER_DELETE permission")
            return False, 'You do not have permission to delete users'
        
        logger.info(f"Permission check passed, fetching user {user_id}")
        
        # SECURITY: Verify user belongs to same organization
        user = get_user_by_id(user_id, current_user)
        if not user:
            logger.warning(f"Access denied: {current_user.get('email')} tried to delete user {user_id} - user not found or different org")
            return False, 'User not found or access denied'
        
        logger.info(f"User found: {user.get('email')}, proceeding with deletion")
        
        # Prevent deleting yourself
        if str(user['_id']) == current_user.get('user_id'):
            return False, 'Cannot delete your own account'
        
        # Prevent deleting super admin unless you are super admin
        if user.get('role') == 'super_admin' and current_user.get('role') != 'super_admin':
            return False, 'Cannot delete super admin'
        
        # Remove user from Vault if exists
        vault_user = user.get('vault_user')
        if vault_user and vault_client:
            try:
                vault_client.auth.userpass.delete_user(vault_user)
                logger.info(f"Deleted user {vault_user} from Vault")
            except Exception as e:
                logger.warning(f"Could not delete user from Vault: {e}")
        
        # Delete user from database
        # Use the user's actual _id from the fetched user object
        user_object_id = user.get('_id')
        logger.info(f"Deleting user with _id: {user_object_id} (type: {type(user_object_id)})")
        
        result = db.users.delete_one({'_id': user_object_id})
        logger.info(f"Delete result: deleted_count={result.deleted_count}")
        
        if result.deleted_count == 0:
            logger.error(f"Failed to delete user - no documents matched _id: {user_object_id}")
            return False, 'Failed to delete user'
        
        org_id_str = str(user.get('organization_id') or current_user.get('organization_id') or '')
        user_name = user.get('name') or user.get('email')
        delete_actor = current_user.get('name') or current_user.get('email')
        if org_id_str:
            create_notification_safe({
                'type': 'user',
                'subtype': 'user_deleted',
                'title': 'User account removed',
                'message': f"{user_name} was removed by {delete_actor}.",
                'organization_id': org_id_str,
                'recipient_type': 'organization',
                'recipient_id': org_id_str,
                'severity': 'medium',
                'priority': 'medium',
                'metadata': {
                    'deleted_user_email': user.get('email'),
                    'deleted_by': delete_actor,
                }
            })
        
        return True, f'User {user.get("name", user.get("email"))} deleted successfully'
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False, 'Failed to delete user'

def activate_user(user_id, current_user):
    """
    Activate a user account.
    
    Args:
        user_id: User identifier
        current_user: Current user
        
    Returns:
        tuple: (success, user_info)
    """
    try:
        db = get_db()
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'super_admin']:
            return False, None
        
        # Find user by ID
        try:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        except:
            user = db.users.find_one({'_id': user_id})
        
        if not user:
            return False, None
        
        # Update user status
        result = db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {
                    'status': 'active',
                    'activated_at': datetime.now(),
                    'activated_by': current_user.get('email')
                },
                '$unset': {
                    'deactivated_at': '',
                    'deactivated_by': ''
                }
            }
        )
        
        if result.modified_count == 0:
            return False, None
        
        return True, {
            'user_id': str(user['_id']),
            'email': user.get('email')
        }
        
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        return False, None

def deactivate_user(user_id, current_user):
    """
    Deactivate a user account.
    
    Args:
        user_id: User identifier
        current_user: Current user
        
    Returns:
        tuple: (success, user_info)
    """
    try:
        db = get_db()
        
        # Check permissions
        if current_user.get('role') not in ['admin', 'super_admin']:
            return False, None
        
        # Find user by ID
        try:
            user = db.users.find_one({'_id': ObjectId(user_id)})
        except:
            user = db.users.find_one({'_id': user_id})
        
        if not user:
            return False, None
        
        # Update user status
        result = db.users.update_one(
            {'_id': user['_id']},
            {'$set': {
                'status': 'inactive',
                'deactivated_at': datetime.now(),
                'deactivated_by': current_user.get('email')
            }}
        )
        
        if result.modified_count == 0:
            return False, None
        
        return True, {
            'user_id': str(user['_id']),
            'email': user.get('email')
        }
        
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        return False, None

def ensure_admin_users():
    """
    Ensure default admin users exist.
    This should be called during system initialization.
    """
    try:
        db = get_db()
        
        # Create default-organization admin - only if credentials are provided
        admin_creds = Config.get_admin_credentials()
        org_admin_email = admin_creds['bdh_admin']['email']
        org_admin_password = admin_creds['bdh_admin']['password']
        org_admin_username = admin_creds['bdh_admin']['username']

        if org_admin_email and org_admin_password and org_admin_username:
            existing_admin = db.users.find_one({'email': org_admin_email})
            if not existing_admin:
                # Create in Vault with bcrypt fallback
                vault_success, password_hash = create_user_in_vault(org_admin_username, org_admin_password)

                user_doc = {
                    '_id': str(ObjectId()),
                    'email': org_admin_email,
                    'name': 'Organization Admin',
                    'role': 'admin',
                    'organization': Config.DEFAULT_ORG_NAME,
                    'organization_id': Config.DEFAULT_ORG_ID,
                    'vault_user': org_admin_username,
                    'status': 'active',
                    'created_at': datetime.now()
                }

                # Store bcrypt hash if Vault wasn't used
                if password_hash:
                    user_doc['password_hash'] = password_hash

                # Create in database
                db.users.insert_one(user_doc)
                logger.info(f"✅ Created organization admin user: {org_admin_email} ({'Vault' if not password_hash else 'bcrypt'} auth)")
        else:
            logger.warning("Organization admin credentials not provided via environment variables")
        
        # Create TESA admin - only if credentials are provided
        org_email = admin_creds['org_admin']['email']
        org_password = admin_creds['org_admin']['password']
        org_username = admin_creds['org_admin']['username']
        
        if org_email and org_password and org_username:
            tesa_admin = db.users.find_one({'email': org_email})
            if not tesa_admin:
                # Create in Vault with bcrypt fallback
                vault_success, password_hash = create_user_in_vault(org_username, org_password)
                
                user_doc = {
                    '_id': str(ObjectId()),
                    'email': org_email,
                    'name': 'TESA Admin',
                    'role': 'super_admin',
                    'organization': 'Thai Embedded Systems Association',
                    'organization_id': 'tesa',
                    'vault_user': org_username,
                    'status': 'active',
                    'created_at': datetime.now()
                }
                
                # Store bcrypt hash if Vault wasn't used
                if password_hash:
                    user_doc['password_hash'] = password_hash
                
                # Create in database
                db.users.insert_one(user_doc)
                logger.info(f"✅ Created TESA admin user: {org_email} ({'Vault' if not password_hash else 'bcrypt'} auth)")
        else:
            logger.warning("TESA admin credentials not provided via environment variables")
        
        # Create TESA Platform Admin - only if credentials are provided
        platform_email = admin_creds['platform_admin']['email']
        platform_password = admin_creds['platform_admin']['password']
        platform_username = admin_creds['platform_admin']['username']
        
        if platform_email and platform_password and platform_username:
            platform_admin = db.users.find_one({'email': platform_email})
            if not platform_admin:
                # Create in Vault with bcrypt fallback
                vault_success, password_hash = create_user_in_vault(platform_username, platform_password)
                
                user_doc = {
                    '_id': str(ObjectId()),
                    'email': platform_email,
                    'name': 'Platform Admin',
                    'role': 'platform_admin',
                    'organization': 'TESA Platform Infrastructure',
                    'organization_id': 'tesa-platform',  # Different from customer orgs
                    'vault_user': platform_username,
                    'status': 'active',
                    'created_at': datetime.now()
                }
                
                # Store bcrypt hash if Vault wasn't used
                if password_hash:
                    user_doc['password_hash'] = password_hash
                
                # Create in database with platform_admin role
                db.users.insert_one(user_doc)
                logger.info(f"✅ Created TESA platform admin user: {platform_email} ({'Vault' if not password_hash else 'bcrypt'} auth)")
        else:
            logger.warning("Platform admin credentials not provided via environment variables")
        
        # Ensure organizations exist
        default_org = db.organizations.find_one({'_id': Config.DEFAULT_ORG_ID})
        if default_org is None:
            db.organizations.insert_one({
                '_id': Config.DEFAULT_ORG_ID,
                'name': Config.DEFAULT_ORG_NAME,
                'description': 'Default organization',
                'created_at': datetime.now()
            })
        
        tesa_org = db.organizations.find_one({'_id': 'tesa'})
        if tesa_org is None:
            db.organizations.insert_one({
                '_id': 'tesa',
                'name': 'Thai Embedded Systems Association',
                'description': 'TESA IoT Platform Provider',
                'created_at': datetime.now()
            })
        
        platform_org = db.organizations.find_one({'_id': 'tesa-platform'})
        if platform_org is None:
            db.organizations.insert_one({
                '_id': 'tesa-platform',
                'name': 'TESA Platform Infrastructure',
                'description': 'TESA IoT Platform Infrastructure Management',
                'created_at': datetime.now()
            })

        # Ensure the MQTT-bridge least-privilege service account
        ensure_bridge_service_account(db)

    except Exception as e:
        logger.error(f"Error ensuring admin users: {e}")


def ensure_bridge_service_account(db=None):
    """
    Ensure a dedicated, least-privilege service account for the MQTT bridge.

    COORDINATION CONTRACT (bridge service account):
    The mqtt-bridge container authenticates against POST /api/v1/auth/login
    with BRIDGE_API_USER / BRIDGE_API_PASSWORD (both passed to the api
    container) instead of reusing an admin account. The JWT it obtains is
    used for the endpoints the bridge actually calls
    (services/mqtt-bridge/mqtt_telemetry_bridge.py):

      - POST /api/v1/telemetry                      (telemetry ingest)
      - PUT  /api/v1/devices/<device_id>            (device status update;
        guarded by require_permission(Permission.DEVICE_UPDATE))
      - POST /api/v1/devices/<device_id>/heartbeat  (best-effort; the bridge
        tolerates 404)

    Least-privilege mapping: the dedicated 'service' role (Role.SERVICE) grants
    EXACTLY the three permissions these calls need - TELEMETRY_INGEST,
    DEVICE_UPDATE, DEVICE_VIEW - and nothing else (no user management, no
    certificate issue/revoke/download, no settings, no audit/export, no org
    administration, no device create/delete). This is tighter than any built-in
    human role (e.g. 'manager' would also carry CERTIFICATE_DOWNLOAD,
    DEVICE_CREATE/CONTROL and SETTINGS_VIEW, and yet still lacks
    TELEMETRY_INGEST). The MQTT bridge is a trusted relay, so the telemetry
    endpoints accept its JWT in 'service relay' mode (see
    require_telemetry_ingest in core/auth.py) and do NOT bind it to a single
    device identity - it forwards telemetry for every device whose data arrives
    on its EMQX-ACL-scoped topics.

    Fail-closed behaviour: the account is only created/updated when BOTH env
    vars are set and the password is not a CHANGEME* placeholder. The env
    password is the source of truth - if it changes, the stored bcrypt hash
    is rotated on the next boot. The role is pinned back to 'service' if it
    ever drifts.
    """
    try:
        if db is None:
            db = get_db()
        if db is None:
            logger.warning("Bridge service account: database unavailable, skipping")
            return

        bridge_user = (os.getenv('BRIDGE_API_USER') or '').strip()
        bridge_password = (os.getenv('BRIDGE_API_PASSWORD') or '').strip()

        if not bridge_user or not bridge_password:
            logger.info(
                "Bridge service account not configured "
                "(set BRIDGE_API_USER and BRIDGE_API_PASSWORD); skipping"
            )
            return
        if bridge_password.startswith('CHANGEME'):
            logger.warning(
                "Bridge service account NOT created: BRIDGE_API_PASSWORD is a "
                "CHANGEME* placeholder (fail-closed)"
            )
            return
        if '@' not in bridge_user:
            logger.warning(
                "Bridge service account NOT created: BRIDGE_API_USER must be an "
                "email address (the login endpoint validates email format)"
            )
            return

        bridge_email = bridge_user.lower()
        default_org_id = getattr(Config, 'DEFAULT_ORG_ID', None) or \
            os.getenv('DEFAULT_ORG_ID', 'default')

        existing = db.users.find_one({'email': bridge_email})
        password_hash = bcrypt.hashpw(
            bridge_password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

        if existing is None:
            db.users.insert_one({
                '_id': str(ObjectId()),
                'email': bridge_email,
                'name': 'MQTT Bridge Service',
                # Dedicated least-privilege service role (see docstring)
                'role': 'service',
                'organization_id': default_org_id,
                'is_service_account': True,
                'service': 'mqtt-bridge',
                'password_hash': password_hash,
                'status': 'active',
                'created_at': datetime.now()
            })
            logger.info(f"✅ Created MQTT bridge service account: {bridge_email} (role=service)")
        else:
            updates = {}
            # Rotate the stored hash when the env password changed.
            try:
                stored_hash = (existing.get('password_hash') or '').encode('utf-8')
                if not stored_hash or not bcrypt.checkpw(
                    bridge_password.encode('utf-8'), stored_hash
                ):
                    updates['password_hash'] = password_hash
            except Exception:
                updates['password_hash'] = password_hash
            # Never allow the service account to drift to a privileged role.
            if existing.get('role') != 'service':
                updates['role'] = 'service'
            if existing.get('status') != 'active':
                updates['status'] = 'active'
            if not existing.get('is_service_account'):
                updates['is_service_account'] = True
            if updates:
                updates['updated_at'] = datetime.now()
                db.users.update_one({'_id': existing['_id']}, {'$set': updates})
                logger.info(
                    f"Updated MQTT bridge service account {bridge_email}: "
                    f"{sorted(updates.keys())}"
                )
    except Exception as e:
        logger.error(f"Error ensuring bridge service account: {e}")

def send_password_reset_email(email, reset_token):
    """
    Send password reset email.
    
    Args:
        email: User email
        reset_token: Password reset token
        
    Returns:
        bool: True if successful
    """
    try:
        # Get SMTP settings from environment
        smtp_host = os.environ.get('SMTP_HOST', 'localhost')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_pass = os.environ.get('SMTP_PASS', '')
        smtp_from = os.environ.get('SMTP_FROM', 'noreply@tesa.local')
        smtp_tls = os.environ.get('SMTP_TLS', 'true').lower() == 'true'
        
        if not smtp_host:
            logger.warning("SMTP not configured, skipping email")
            return False
        
        # Create message
        subject = "TESA IoT Platform - Password Reset Request"
        reset_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:5566')}/auth/reset-password?token={reset_token}"
        
        body = f"""
Hello,

You have requested to reset your password for the TESA IoT Platform.

Please click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
TESA IoT Platform Team
"""
        
        msg = MIMEMultipart()
        msg['From'] = smtp_from
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_tls:
                server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            
            server.send_message(msg)
        
        logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False

def get_user_permissions(user):
    """
    Get user permissions based on role using RBAC system.
    
    Args:
        user: User object
        
    Returns:
        dict: Permissions object
    """
    role = user.get('role', 'user')
    
    # Get permissions from RBAC system
    rbac_permissions = RBAC.get_role_permissions(role)
    
    # Convert RBAC permissions to UI permissions
    permissions = {
        'dashboard': True,
        'profile': True,
    }
    
    # Map RBAC permissions to UI permissions
    for perm in rbac_permissions:
        perm_value = perm.value if hasattr(perm, 'value') else str(perm)
        
        if 'user.view' in perm_value:
            permissions['users_view'] = True
        if 'user.create' in perm_value or 'user.update' in perm_value or 'user.delete' in perm_value:
            permissions['users_manage'] = True
        if 'organization' in perm_value:
            permissions['organizations_manage'] = True
            permissions['organizations_view'] = True
        if 'device.view' in perm_value:
            permissions['devices_view'] = True
        if 'device.create' in perm_value or 'device.update' in perm_value or 'device.delete' in perm_value:
            permissions['devices_manage'] = True
        if 'certificate' in perm_value:
            permissions['certificates_view'] = True
            permissions['certificates_manage'] = True
        if 'settings' in perm_value:
            permissions['settings_manage'] = True
        if 'audit' in perm_value:
            permissions['audit_logs'] = True
        if 'platform' in perm_value:
            permissions['platform_manage'] = True
            permissions['system_config'] = True
    
    # Handle backward compatibility for legacy roles
    if role in ['admin', 'super_admin', 'organization_admin']:
        permissions.update({
            'users_view': True,
            'users_manage': True,
            'organizations_view': True,
            'devices_view': True,
            'devices_manage': True,
            'certificates_view': True,
            'certificates_manage': True,
            'settings_manage': True,
            'audit_logs': True,
        })
        if role == 'super_admin':
            permissions['system_config'] = True
    elif role == 'platform_admin':
        permissions.update({
            'platform_manage': True,
            'system_config': True,
            # NO customer data access for platform admin
        })
    elif role == 'manager':
        permissions.update({
            'users_view': True,
            'devices_view': True,
            'devices_manage': True,
            'certificates_view': True,
            'certificates_manage': True,
            'audit_logs': True
        })
    else:  # regular user
        permissions.update({
            'users_view': True,  # Users can at least view user list for their org
            'devices_view': True,
            'certificates_view': True
        })
    
    return permissions

def update_last_login(user_id):
    """
    Update user's last login timestamp.
    
    Args:
        user_id: User identifier
    """
    try:
        db = get_db()
        db.users.update_one(
            {'_id': user_id},
            {'$set': {'last_login': datetime.now()}}
        )
    except Exception as e:
        logger.error(f"Error updating last login: {e}")

def get_user_activity_log(user_id, limit=50):
    """
    Get user activity log.
    
    Args:
        user_id: User identifier
        limit: Maximum records
        
    Returns:
        list: Activity log entries
    """
    try:
        db = get_db()
        
        # Get activity logs for user
        activities = list(db.activity_logs.find(
            {'user_id': user_id}
        ).sort('timestamp', -1).limit(limit))
        
        # Format response
        result = []
        for activity in activities:
            result.append({
                'timestamp': activity.get('timestamp', ''),
                'action': activity.get('action', ''),
                'resource': activity.get('resource', ''),
                'details': activity.get('details', {}),
                'ip_address': activity.get('ip_address', '')
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting activity log: {e}")
        return []


def update_user_profile(user_id, profile_data):
    """
    Update user profile information.
    
    Args:
        user_id: User ID
        profile_data: Dictionary with profile fields to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        
        # Convert string ID to ObjectId if needed
        if isinstance(user_id, str):
            try:
                user_id = ObjectId(user_id)
            except:
                pass
        
        # Prepare update data with proper nesting for profile fields
        update_fields = {}
        profile_fields = ['phone', 'department', 'title', 'bio', 'location', 'avatar_url']
        
        for field, value in profile_data.items():
            if field == 'name':
                # Name is a top-level field
                update_fields['name'] = value
            elif field in profile_fields:
                # These go under profile subdocument
                update_fields[f'profile.{field}'] = value
        
        # Add update timestamp
        update_fields['profile.updated_at'] = datetime.utcnow()
        
        # Update the user document
        result = db.users.update_one(
            {'_id': user_id},
            {'$set': update_fields}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated profile for user {user_id}")
            return True
            
        # Check if user exists but no changes were made
        user = db.users.find_one({'_id': user_id})
        if user:
            return True  # User exists, possibly no changes needed
            
        return False
        
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return False

def change_user_password(user_id, current_password, new_password):
    """
    Change user password after verifying current password.
    
    Args:
        user_id: User ID
        current_password: Current password for verification
        new_password: New password to set
        
    Returns:
        bool: True if successful, False if current password is wrong
    """
    try:
        db = get_db()
        
        # Convert string ID to ObjectId if needed
        if isinstance(user_id, str):
            try:
                user_id = ObjectId(user_id)
            except:
                pass
        
        # Get user to verify current password
        user = db.users.find_one({'_id': user_id})
        if not user:
            return False
        
        # Verify current password (check both password and password_hash fields for compatibility)
        stored_password = user.get('password_hash') or user.get('password', '')
        if not stored_password:
            logger.error(f"No password found for user {user_id}")
            return False
            
        # Handle both encoded and decoded password formats
        if isinstance(stored_password, str):
            stored_password = stored_password.encode('utf-8')
            
        if not bcrypt.checkpw(current_password.encode('utf-8'), stored_password):
            logger.warning(f"Failed password change attempt for user {user_id} - incorrect current password")
            return False
        
        # Hash new password
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update password and track change time (use password_hash field to match existing schema)
        result = db.users.update_one(
            {'_id': user_id},
            {
                '$set': {
                    'password_hash': hashed_password.decode('utf-8'),
                    'security.password_changed_at': datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Invalidate existing sessions (optional - implement if session management exists)
            # TODO: Implement session invalidation
            
            logger.info(f"Password changed successfully for user {user_id}")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error changing user password: {e}")
        return False

def get_user_preferences(user_id):
    """
    Get user preferences.
    
    Args:
        user_id: User ID
        
    Returns:
        dict: User preferences or None
    """
    try:
        db = get_db()
        
        # Convert string ID to ObjectId if needed
        if isinstance(user_id, str):
            try:
                user_id = ObjectId(user_id)
            except:
                pass
        
        user = db.users.find_one(
            {'_id': user_id},
            {'preferences': 1}
        )
        
        if user:
            return user.get('preferences', {})
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting user preferences: {e}")
        return None

def update_user_preferences(user_id, preferences_data):
    """
    Update user preferences.
    
    Args:
        user_id: User ID
        preferences_data: Dictionary with preferences to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        db = get_db()
        
        # Convert string ID to ObjectId if needed
        if isinstance(user_id, str):
            try:
                user_id = ObjectId(user_id)
            except:
                pass
        
        # Prepare update fields with proper nesting
        update_fields = {}
        
        for key, value in preferences_data.items():
            if key == 'notifications' and isinstance(value, dict):
                # Handle nested notifications preferences
                for notif_key, notif_value in value.items():
                    update_fields[f'preferences.notifications.{notif_key}'] = notif_value
            else:
                # Handle other preference fields
                update_fields[f'preferences.{key}'] = value
        
        # Update the user document
        result = db.users.update_one(
            {'_id': user_id},
            {'$set': update_fields}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated preferences for user {user_id}")
            return True
            
        # Check if user exists
        user = db.users.find_one({'_id': user_id})
        if user:
            return True  # User exists, possibly no changes needed
            
        return False
        
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        return False

# User service is a module with functions, not a class
# No service instance needed as functions are imported directly
