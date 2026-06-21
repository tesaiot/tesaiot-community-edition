# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Authentication Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from flask import Blueprint, request, jsonify, g
import bcrypt

from ..core.auth import generate_token, blacklist_token, require_auth
from ..core.database import get_db, get_redis, get_vault
from ..core.rbac import RBAC
from ..core.config import Config
from ..services.vault_service import verify_vault_password
from ..services.notification_service import send_login_notification
from ..utils.data_fixes import fix_user_data
from ..services.logging_service import logging_service, LogLevel
from ..utils.validation import (
    validate_auth_request, validate_email, validate_password,
    sanitize_string, check_rate_limit_status,
    is_rate_limited, reset_rate_limit, rate_limit_response,
    admin_bypass_rate_limit,
    get_client_ip, validate_request_size,
    ValidationError, SecurityError
)

logger = logging.getLogger(__name__)

def verify_bcrypt_password(password: str, password_hash: str) -> bool:
    """
    Verify password against bcrypt hash with security best practices.
    
    Args:
        password: Plain text password to verify
        password_hash: Bcrypt hash from database
        
    Returns:
        bool: True if password matches hash, False otherwise
    """
    try:
        # Validate inputs
        if not password or not password_hash:
            return False
        
        # Ensure inputs are bytes for bcrypt
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        
        # Basic validation of bcrypt hash format
        if not password_hash.startswith(b'$2b$') and not password_hash.startswith(b'$2a$'):
            logger.warning("Invalid bcrypt hash format detected")
            return False
        
        # Use bcrypt to verify password
        return bcrypt.checkpw(password, password_hash)
    except Exception as e:
        logger.error(f"Error verifying bcrypt password: {e}")
        return False

def create_bcrypt_hash(password: str) -> str:
    """
    Create bcrypt hash for a password using configured security settings.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        str: Bcrypt hash string
    """
    try:
        # Validate input
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Get security configuration
        security_config = Config.get_security_config()
        
        # Generate salt with configured rounds
        salt = bcrypt.gensalt(rounds=security_config.bcrypt_log_rounds)
        
        # Create hash
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return password_hash.decode('utf-8')
    except Exception as e:
        logger.error(f"Error creating bcrypt hash: {e}")
        raise

# Create blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@auth_bp.route('/token', methods=['POST'])
@validate_request_size(max_size=1024*1024)  # 1MB limit for auth requests
@validate_auth_request()
def login():
    """
    User login endpoint - verifies credentials against Vault.
    
    Request JSON:
        {
            "email": "user@example.com",
            "password": "password"
        }
    
    Returns:
        200: Login successful with token
        400: Missing credentials
        401: Invalid credentials
    """
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password')
        
        # Additional input validation and sanitization
        try:
            # Sanitize email input
            email = sanitize_string(email, 254).lower()
            
            # Validate email format
            if not validate_email(email):
                logger.warning(f"Login failed - invalid email format: {email}")
                return jsonify({
                    'error': 'Invalid email format',
                    'code': 'INVALID_EMAIL'
                }), 400
            
            # Basic password validation (not strength, just presence)
            if not password or len(password) > 128:
                logger.warning(f"Login failed - invalid password for email: {email}")
                return jsonify({
                    'error': 'Invalid password',
                    'code': 'INVALID_PASSWORD'
                }), 400
                
        except ValidationError as ve:
            logger.warning(f"Login validation failed for {email}: {ve.message}")
            return jsonify({
                'error': ve.message,
                'code': ve.code or 'VALIDATION_ERROR'
            }), 400
        except SecurityError as se:
            logger.warning(f"Login security error for {email}: {se.message}")
            # SecurityError carries no rate window; use a conservative
            # 60-second Retry-After so the 429 still tells clients when to retry.
            return rate_limit_response(se.message, 60, code=se.code or 'SECURITY_ERROR')
        
        # Log login attempt
        logger.info(f"Login attempt for email: {email}")
        
        if not email or not password:
            logger.warning(f"Login failed - missing credentials for email: {email}")
            return jsonify({'error': 'Email and password required'}), 400

        # Account lockout: enforce MAX_LOGIN_ATTEMPTS / LOCKOUT_DURATION from
        # core config. Only FAILED attempts are recorded (further below); here
        # we just peek so a successful login never throttles itself.
        security_config = Config.get_security_config()
        lockout_key = f"login_lock:{email}"
        # ADMIN_BYPASS_RATE_LIMIT lets the configured bootstrap admin skip the
        # account-lockout gate as well (mirrors the per-IP bypass in the
        # validate_auth_request decorator) so an operator is never locked out.
        if not admin_bypass_rate_limit(email):
            locked, lock_retry_after = is_rate_limited(
                lockout_key,
                max_attempts=security_config.max_login_attempts,
                window_seconds=security_config.lockout_duration,
            )
            if locked:
                logger.warning(f"Account lockout active for {email}")
                return rate_limit_response(
                    'Account temporarily locked after too many failed login attempts.',
                    lock_retry_after,
                    code='ACCOUNT_LOCKED'
                )

        # Initialize database connection
        db = get_db()
        user = None

        # Find user in database first
        try:
            logger.debug(f"Looking up user {email} in database")
            if db is not None:
                user = db.users.find_one({'email': email})

                # If user found, verify password and get organization details
                if user:
                    logger.debug(f"Found user {email} in database with role: {user.get('role')}")

                    authenticated = False
                    if user.get('password_hash'):
                        # Primary path: bcrypt hash verification
                        try:
                            password_hash = user['password_hash'].encode('utf-8')
                            authenticated = bcrypt.checkpw(password.encode('utf-8'), password_hash)
                        except Exception as e:
                            logger.error(f"Password verification error: {e}")
                            authenticated = False
                    elif user.get('password'):
                        # Legacy unsalted SHA-256 fallback (pre-bcrypt accounts).
                        # SECURITY: constant-time compare; on success the account
                        # is migrated on-login: the password is immediately
                        # re-hashed with bcrypt into password_hash and the
                        # legacy plaintext-equivalent field is deleted.
                        legacy_hash = hashlib.sha256(password.encode()).hexdigest()
                        stored_legacy = user.get('password') or ''
                        if hmac.compare_digest(str(stored_legacy), legacy_hash):
                            authenticated = True
                            try:
                                new_hash = create_bcrypt_hash(password)
                                db.users.update_one(
                                    {'_id': user['_id']},
                                    {
                                        '$set': {
                                            'password_hash': new_hash,
                                            'password_migrated_at': datetime.now(),
                                        },
                                        '$unset': {'password': ''}
                                    }
                                )
                                user['password_hash'] = new_hash
                                user.pop('password', None)
                                logger.info(f"Migrated legacy SHA-256 password to bcrypt for {email}")
                            except Exception as e:
                                logger.error(f"Failed to migrate legacy password for {email}: {e}")
                    elif user.get('vault_user') or user.get('vault_username'):
                        # Vault-managed account without a local hash: Vault is
                        # the primary verifier (previously this case fell
                        # through with NO password check at all - fail-open).
                        vault_client_primary = get_vault()
                        vault_user_primary = user.get('vault_user') or user.get('vault_username')
                        if vault_client_primary:
                            authenticated = verify_vault_password(
                                vault_client_primary, vault_user_primary, password
                            )

                    if not authenticated:
                        logger.warning(f"Invalid password for user {email}")
                        user = None  # Reset user if password doesn't match

                    # Resolve organization details for the authenticated user
                    if user:
                        if user.get('organization_id'):
                            # Ensure organization_id is a string
                            org_id_str = str(user['organization_id'])
                            user['organization_id'] = org_id_str

                            # Look up organization name if not already present
                            if not user.get('organization'):
                                try:
                                    from bson import ObjectId as BsonObjectId
                                    org = db.organizations.find_one({'_id': BsonObjectId(org_id_str)})
                                    if org:
                                        user['organization'] = org['name']
                                except Exception as e:
                                    logger.warning(f"Could not look up organization name: {e}")
                        elif user.get('organization'):
                            # Organization field exists (possibly as ObjectId)
                            org_field = user.get('organization')
                            if hasattr(org_field, '__str__'):
                                user['organization_id'] = str(org_field)
                else:
                    logger.info(f"User {email} not found in database")
        except Exception as e:
            logger.error(f"Database error during login: {e}")

        if user is None:
            # Record the failed attempt towards account lockout. Unknown user
            # and wrong password are treated identically (no user enumeration).
            check_rate_limit_status(
                lockout_key,
                max_attempts=security_config.max_login_attempts,
                window_seconds=security_config.lockout_duration,
            )
            # Log failed login attempt for unknown user
            # Cannot use activity_logs due to NOT NULL constraint on user_id
            # Log to system logs instead
            try:
                logging_service.log_system(
                    level=LogLevel.WARNING,
                    message=f"Failed login attempt for unknown user: {email}",
                    source='auth',
                    metadata={
                        'email': email,
                        'reason': 'user_not_found',
                        'action': 'user.login',
                        'result': 'failure'
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log failed login activity: {e}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check user status
        if user.get('status') == 'inactive':
            # Log failed login attempt for inactive account
            try:
                logging_service.log_activity(
                    action='user.login',
                    resource_type='auth',
                    resource_id=str(user['_id']),
                    result='failure',
                    user_id=str(user['_id']),
                    organization_id=user.get('organization_id', ''),
                    metadata={
                        'email': email,
                        'reason': 'account_inactive'
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log inactive account login activity: {e}")
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Authentication is already done above using database password
        # Set auth method based on what was used
        auth_method = 'database'
        
        # Check if we should also verify with Vault (optional, for additional security)
        vault_user = user.get('vault_user') or user.get('vault_username')
        vault_client = get_vault()
        
        if vault_client and vault_user:
            # Try Vault authentication as secondary check (optional)
            vault_auth_success = verify_vault_password(vault_client, vault_user, password)
            if vault_auth_success:
                logger.info(f"Additional Vault authentication successful for {email}")
                auth_method = 'vault'
            else:
                logger.debug(f"Vault authentication not available or failed for {email}, using database auth")
        
        # Generate JWT token (fresh session: session_start = now, used by
        # /auth/refresh to enforce the absolute session lifetime)
        token = generate_token({
            'user_id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name', ''),
            'role': user.get('role', 'user'),
            'organization': user.get('organization', ''),
            'organization_id': user.get('organization_id', '')
        })

        # Log successful login
        logger.info(f"Login successful for {email} (role: {user.get('role')})")

        # Clear the account-lockout counter on success
        reset_rate_limit(lockout_key)
        
        # Log activity to activity_logs table
        try:
            # auth_method was already determined in the authentication flow above
            
            logging_service.log_activity(
                action='user.login',
                resource_type='auth',
                resource_id=str(user['_id']),
                result='success',
                user_id=str(user['_id']),
                organization_id=user.get('organization_id', ''),
                metadata={
                    'email': email,
                    'role': user.get('role', 'user'),
                    'vault_authenticated': bool(vault_client),
                    'auth_method': auth_method
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log login activity: {e}")
            # Don't fail login if activity logging fails
        
        # Store session in Redis
        redis_client = get_redis()
        if redis_client:
            try:
                session_key = f"session:{token[:20]}"
                session_data = {
                    'user_id': str(user['_id']),
                    'email': user['email'],
                    'login_time': datetime.now().isoformat()
                }
                redis_client.setex(session_key, 86400, json.dumps(session_data))
            except Exception as e:
                logger.warning(f"Failed to store session in Redis: {e}")
        
        # Send login notification (async)
        try:
            client_ip = get_client_ip()
            user_agent = request.headers.get('User-Agent')
            send_login_notification(user, client_ip, user_agent)
        except Exception as e:
            logger.warning(f"Failed to send login notification: {e}")
            # Don't fail login if notification fails
        
        # Update last login
        if db is not None:
            try:
                db.users.update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.now()}}
                )
            except Exception as e:
                logger.error(f"Failed to update last login: {e}")
        
        # Prepare user response
        user_response = {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user.get('name', ''),
            'role': user.get('role', 'user'),
            'organization': user.get('organization', ''),
            'organization_id': str(user.get('organization_id', '')) if user.get('organization_id') else '',
            'avatar': user.get('avatar', ''),
            'phone': user.get('phone', ''),
            'department': user.get('department', ''),
            'position': user.get('position', ''),
            'vault_authenticated': bool(vault_client)
        }
        
        fixed_user = fix_user_data(user_response)
        # SECURITY: never log the full user object; id/email only.
        logger.debug(
            "Login response prepared for user id=%s email=%s",
            fixed_user.get('id'), fixed_user.get('email')
        )

        return jsonify({
            'success': True,
            'token': token,
            'user': fixed_user
        }), 200

    except Exception as e:
        # SECURITY: log the full traceback server-side only. Never return
        # exception details or stack traces to the client.
        logger.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    User logout endpoint - invalidates token and clears session.
    
    Requires: Authentication header
    
    Returns:
        200: Logout successful
    """
    # Get token from header
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            token = auth_header.split(' ')[1]
            
            # Blacklist the token
            blacklist_token(token)
            
            # Remove session from Redis
            redis_client = get_redis()
            if redis_client:
                session_key = f"session:{token[:20]}"
                redis_client.delete(session_key)
            
            logger.info(f"User {g.current_user.get('email')} logged out")
            
            # Log logout activity
            try:
                logging_service.log_activity(
                    action='user.logout',
                    resource_type='auth',
                    resource_id=g.current_user.get('_id') or g.current_user.get('id'),
                    result='success',
                    metadata={
                        'email': g.current_user.get('email')
                    }
                )
            except Exception as activity_e:
                logger.warning(f"Failed to log logout activity: {activity_e}")
                # Don't fail logout if activity logging fails
        except Exception as e:
            logger.error(f"Error during logout: {e}")
    
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/refresh', methods=['POST'])
@require_auth
def refresh_token():
    """
    Refresh authentication token.
    
    Requires: Valid authentication token

    Enforces an ABSOLUTE session lifetime: each token carries the
    session_start claim of the original login. Refresh is refused once
    now - session_start exceeds MAX_SESSION_LIFETIME_HOURS (env, default
    720h / 30 days), so refresh can no longer extend a session forever.

    Returns:
        200: New token
        401: Invalid token / session lifetime exceeded
    """
    # Absolute session lifetime check (anti indefinite sliding session)
    token_payload = getattr(g, 'token_payload', None) or {}
    session_start = token_payload.get('session_start') or token_payload.get('iat')
    try:
        max_lifetime_hours = float(os.environ.get('MAX_SESSION_LIFETIME_HOURS', '720'))
    except ValueError:
        max_lifetime_hours = 720.0
    if session_start:
        session_age_seconds = time.time() - float(session_start)
        if session_age_seconds > max_lifetime_hours * 3600:
            logger.info(
                "Refresh refused for %s: session age %.0fh exceeds max %sh",
                g.current_user.get('email'), session_age_seconds / 3600, max_lifetime_hours
            )
            return jsonify({
                'error': 'Session lifetime exceeded. Please login again.',
                'code': 'SESSION_LIFETIME_EXCEEDED'
            }), 401

    # Generate new token with same user data, carrying the ORIGINAL
    # session_start forward so the absolute lifetime cannot be reset.
    new_token = generate_token({
        'user_id': g.current_user.get('_id') or g.current_user.get('id'),
        'email': g.current_user.get('email'),
        'name': g.current_user.get('name', ''),
        'role': g.current_user.get('role', 'user'),
        'organization': g.current_user.get('organization', ''),
        'organization_id': g.current_user.get('organization_id', '')
    }, session_start=session_start)
    
    # Blacklist old token
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            old_token = auth_header.split(' ')[1]
            blacklist_token(old_token)
        except Exception as e:
            logger.error(f"Error blacklisting old token: {e}")
    
    logger.info(f"Token refreshed for {g.current_user.get('email')}")
    
    return jsonify({
        'success': True,
        'token': new_token
    }), 200

@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify_token():
    """
    Verify current token is valid.
    
    Requires: Authentication header
    
    Returns:
        200: Token is valid
        401: Token is invalid
    """
    return jsonify({
        'valid': True,
        'user': g.current_user
    }), 200

@auth_bp.route('/validate-token', methods=['POST'])
@validate_request_size(max_size=1024*4)  # 4KB limit for token validation
def validate_token():
    """
    Validate JWT token for WebSocket services.
    This endpoint is used by internal services (like Rust WebSocket) to validate tokens.
    
    Request JSON:
        {
            "token": "JWT_TOKEN_STRING"
        }
    
    Returns:
        200: Token is valid with user info
        400: Missing or invalid token format
        401: Token is invalid/expired
    """
    try:
        from ..core.auth import verify_token as verify_jwt_token
        
        data = request.get_json()
        if not data:
            return jsonify({
                'valid': False,
                'error': 'Invalid JSON or no data provided'
            }), 400
            
        token = data.get('token')
        if not token:
            return jsonify({
                'valid': False,
                'error': 'Token required'
            }), 400
        
        # Sanitize token input
        token = sanitize_string(token, 2048)  # JWT tokens can be long
        
        # Verify the token using the existing verify_token function
        payload, error_msg = verify_jwt_token(token)
        
        if not payload:
            logger.debug(f"Token validation failed: {error_msg}")
            return jsonify({
                'valid': False,
                'error': error_msg or 'Invalid token'
            }), 401
        
        # Get user info from database if available
        user_info = {
            'email': payload.get('email'),
            'role': payload.get('role', 'user'),
            'organization_id': payload.get('organization_id'),
            'user_id': payload.get('user_id') or payload.get('email')
        }
        
        # Try to get additional user data from database
        db = get_db()
        if db is not None:
            try:
                user = db.users.find_one(
                    {'email': payload.get('email')},
                    {'password': 0, 'password_hash': 0}  # Exclude sensitive fields
                )
                if user:
                    user_info.update({
                        'user_id': str(user['_id']),
                        'name': user.get('name', ''),
                        'organization': str(user.get('organization', '')),
                        'organization_id': str(user.get('organization', user_info.get('organization_id', ''))),
                        'status': user.get('status', 'active')
                    })
            except Exception as e:
                logger.warning(f"Failed to get user data for token validation: {e}")
                # Continue with basic payload info
        
        logger.debug(f"Token validation successful for user: {payload.get('email')}")
        
        return jsonify({
            'valid': True,
            'user': user_info,
            'expires_at': payload.get('exp')
        }), 200
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({
            'valid': False,
            'error': 'Token validation failed'
        }), 401

@auth_bp.route('/forgot-password', methods=['POST'])
@validate_request_size(max_size=1024*512)  # 512KB limit
def forgot_password():
    """
    Initiate password reset process.
    
    Request JSON:
        {
            "email": "user@example.com"
        }
    
    Returns:
        200: Reset email sent (if email exists)
        400: Missing email
    """
    try:
        # Get client IP for rate limiting (trusted-proxy aware)
        client_ip = get_client_ip()

        # Rate limit password reset requests
        allowed, retry_after = check_rate_limit_status(
            f"forgot_pw_{client_ip}", max_attempts=3, window_seconds=3600
        )
        if not allowed:
            logger.warning(f"Password reset rate limit exceeded for IP: {client_ip}")
            return rate_limit_response(
                'Too many password reset attempts.', retry_after
            )
        
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid JSON or no data provided',
                'code': 'INVALID_JSON'
            }), 400
            
        email = data.get('email', '').lower()
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
            
        # Validate and sanitize email
        email = sanitize_string(email, 254).lower()
        if not validate_email(email):
            return jsonify({
                'error': 'Invalid email format',
                'code': 'INVALID_EMAIL'
            }), 400
        
        # Generate reset token
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # Store token in Redis with expiry
        redis_client = get_redis()
        if redis_client:
            redis_client.setex(
                f"password_reset:{reset_token}",
                3600,  # 1 hour expiry
                email
            )
        
        # Send reset email
        from ..services.user_service import send_password_reset_email
        send_password_reset_email(email, reset_token)
        
        # Log password reset request
        try:
            # We don't know if the user exists, so log as activity without user_id
            logging_service.log_activity(
                action='user.password_reset_request',
                resource_type='auth',
                resource_id='password_reset',
                result='success',
                metadata={
                    'email': email
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log password reset request activity: {e}")
        
        return jsonify({
            'message': 'If the email exists, a password reset link has been sent'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        return jsonify({'error': 'Failed to process request'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
@validate_request_size(max_size=1024*512)  # 512KB limit
def reset_password():
    """
    Reset password with token.
    
    Request JSON:
        {
            "token": "reset_token",
            "password": "new_password"
        }
    
    Returns:
        200: Password reset successful
        400: Invalid/expired token or missing data
        404: User not found
        500: Server error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': 'Invalid JSON or no data provided',
                'code': 'INVALID_JSON'
            }), 400
            
        token = data.get('token', '')
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and password required'}), 400
            
        # Validate token format (basic sanitization)
        token = sanitize_string(token, 128)
        if len(token) < 16:  # Tokens should be reasonably long
            return jsonify({
                'error': 'Invalid token format',
                'code': 'INVALID_TOKEN'
            }), 400
            
        # Validate password strength
        is_valid, error_msg = validate_password(new_password)
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'field': 'password',
                'code': 'INVALID_PASSWORD'
            }), 400
        
        # Verify token from Redis
        redis_client = get_redis()
        
        if not redis_client:
            return jsonify({'error': 'Password reset not available'}), 503
        
        email = redis_client.get(f"password_reset:{token}")
        if not email:
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        email = email.decode('utf-8')
        
        # Find user
        db = get_db()
        user = db.users.find_one({'email': email})
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password in Vault and/or MongoDB
        vault_user = user.get('vault_user')
        vault_update_success = False
        
        if vault_user:
            from ..services.user_service import create_user_in_vault
            vault_update_success = create_user_in_vault(vault_user, new_password)
            if not vault_update_success:
                logger.warning(f"Failed to update password in Vault for {email}")
        
        # Also update bcrypt hash in MongoDB for fallback authentication
        try:
            # Generate bcrypt hash
            password_hash = create_bcrypt_hash(new_password)
            
            # Update password hash in MongoDB
            db.users.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'password_hash': password_hash,
                        'password_updated': datetime.now(),
                        'updated_by': 'password_reset'
                    }
                }
            )
            logger.info(f"Password hash updated in MongoDB for {email}")
        except Exception as e:
            logger.error(f"Failed to update password hash in MongoDB for {email}: {e}")
            # If both Vault and MongoDB updates failed, return error
            if not vault_update_success:
                return jsonify({'error': 'Failed to update password'}), 500
        
        # Delete token
        redis_client.delete(f"password_reset:{token}")
        
        # Log successful password reset
        try:
            logging_service.log_activity(
                action='user.password_reset_complete',
                resource_type='auth',
                resource_id=str(user['_id']),
                result='success',
                user_id=str(user['_id']),
                organization_id=user.get('organization_id', ''),
                metadata={
                    'email': email,
                    'vault_user': vault_user
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log password reset activity: {e}")
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return jsonify({'error': 'Failed to reset password'}), 500

@auth_bp.route('/user/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user information from JWT token"""
    try:
        # Get user info from g.current_user (set by require_auth decorator)
        canonical_role = RBAC.canonicalize_role(g.current_user.get('role', 'user'))

        user_data = {
            'email': g.current_user.get('email'),
            'name': g.current_user.get('name', 'Unknown'),
            'role': canonical_role,
            'organization': g.current_user.get('organization', 'Unknown'),
            'organization_id': g.current_user.get('organization_id', ''),
            'id': g.current_user.get('_id') or g.current_user.get('id', '')
        }
        
        # Try to get additional user info from database if needed
        db = get_db()
        if db is not None:
            try:
                user = db.users.find_one({'email': g.current_user.get('email')})
                if user:
                    canonical_db_role = RBAC.canonicalize_role(user.get('role', user_data['role']))
                    user_data.update({
                        'name': user.get('name', user_data['name']),
                        'organization': user.get('organization', user_data['organization']),
                        'organization_id': str(user.get('organization_id', '')),
                        'id': str(user.get('_id', '')),
                        'role': canonical_db_role
                    })
            except Exception as e:
                logger.warning(f"Failed to get additional user data: {e}")
        
        return jsonify(user_data), 200
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        return jsonify({'error': 'Failed to get user information'}), 500
