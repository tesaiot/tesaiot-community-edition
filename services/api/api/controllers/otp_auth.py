# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - OTP Authentication Controller
Copyright (C) 2024-2025 TESA IoT Platform

OTP-based authentication endpoints for user verification and password reset
"""

import logging
import json
import os
from flask import Blueprint, request, jsonify, g
from datetime import datetime

from ..services.otp_service import OTPService
from ..services.email_service import EmailService
from ..services.user_service import create_user_in_vault
from ..core.auth import generate_token, verify_token
from ..core.database import get_db, get_redis
from ..core.rbac import RBAC
from bson import ObjectId

# Create blueprint
otp_auth_bp = Blueprint('otp_auth', __name__)
logger = logging.getLogger(__name__)

# Initialize services
otp_service = OTPService()
email_service = EmailService()


def _otp_rate_limit_response(result):
    """Build a 429 with Retry-After computed from the actual OTP rate window.

    Project rule: every 429 must tell the client when to retry.
    """
    retry_after = None
    info = getattr(result, 'rate_limit_info', None) or {}
    # rate_limit_info is either a single entry or a dict of entries.
    candidates = []
    if 'reset_time' in info:
        candidates.append(info.get('reset_time'))
    else:
        for entry in info.values():
            if isinstance(entry, dict) and entry.get('reset_time'):
                candidates.append(entry['reset_time'])
    for reset_iso in candidates:
        try:
            reset_dt = datetime.fromisoformat(str(reset_iso))
            seconds = int((reset_dt - datetime.utcnow()).total_seconds())
            if seconds > 0 and (retry_after is None or seconds < retry_after):
                retry_after = seconds
        except (ValueError, TypeError):
            continue
    if retry_after is None:
        # Fall back to the configured cooldown window
        retry_after = int(getattr(otp_service, 'cooldown_seconds', 30)) or 30

    response = jsonify({
        'error': f"{result.message} Retry after {retry_after} seconds.",
        'code': 'RATE_LIMIT_EXCEEDED',
        'retry_after_seconds': retry_after
    })
    response.headers['Retry-After'] = str(retry_after)
    return response, 429

@otp_auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """
    Send OTP to user's email for verification.
    Used for new user activation and password reset.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        purpose = data.get('purpose', 'verification')  # 'verification' or 'password_reset'
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Check if user exists
        db = get_db()
        user = db.users.find_one({'email': email})
        
        if purpose == 'verification' and not user:
            return jsonify({'error': 'User not found. Please contact your administrator.'}), 404
        
        if purpose == 'password_reset' and not user:
            # Don't reveal if user exists for security
            return jsonify({'message': 'If the email exists, you will receive a password reset code.'}), 200
        
        # Get client IP for rate limiting
        client_ip = request.remote_addr
        is_admin = False
        
        # Check if request is from admin (authenticated request)
        if hasattr(g, 'current_user') and g.current_user:
            is_admin = RBAC.is_admin(g.current_user)
        
        # Generate OTP
        result = otp_service.generate_otp(
            identifier=email,
            ip_address=client_ip,
            is_admin=is_admin
        )
        
        if not result.success:
            return _otp_rate_limit_response(result)  # 429 with Retry-After
        
        # Prepare email data
        user_name = user.get('name', email.split('@')[0]) if user else 'User'
        
        if purpose == 'verification':
            template = 'otp_verification'
            subject = 'Verify Your TESA IoT Platform Account'
        else:
            template = 'password_reset'
            subject = 'Reset Your TESA IoT Platform Password'
        
        # Send OTP email
        email_result = email_service.send_email_sync(
            to_email=email,
            subject=subject,
            template_name=template,
            template_data={
                'user_name': user_name,
                'otp_code': result.otp_code,
                'request_ip': client_ip,
                'request_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                'verification_url': f'https://{os.getenv("TESA_ADMIN_DOMAIN", "admin.localhost")}/auth/verify?email={email}'
            }
        )
        
        if not email_result['success']:
            logger.error(f"Failed to send OTP email to {email}: {email_result.get('error')}")
            return jsonify({'error': 'Failed to send verification email. Please try again.'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Verification code sent to your email.',
            'expires_in': getattr(result, 'expires_in', 900)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in send_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP code entered by user.
    Returns a temporary token for password setup if successful.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        otp_code = data.get('otp')
        
        # Debug logging
        logger.info(f"Verify OTP request - Email: {email}, OTP: {otp_code[:2] if otp_code else 'None'}***")
        
        if not email or not otp_code:
            return jsonify({'error': 'Email and OTP code are required'}), 400
        
        # Normalize email to lowercase for consistency
        email = email.lower().strip()
        logger.info(f"Normalized email: {email}")
        
        # Verify OTP
        result = otp_service.verify_otp(
            identifier=email,
            otp_code=otp_code
        )
        
        if not result.success:
            return jsonify({'error': result.message}), 400
        
        # Update user verification status
        db = get_db()
        user = db.users.find_one({'email': email})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Mark email as verified
        db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {
                    'email_verified': True,
                    'email_verified_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        # Create a secure session for password setup (no time limit, following OWASP best practices)
        # Generate a secure session ID
        import secrets
        session_id = secrets.token_urlsafe(32)
        
        # Store session state in Redis with user binding
        redis_client = get_redis()
        if redis_client:
            session_data = {
                'user_id': str(user['_id']),
                'email': email,
                'purpose': 'password_setup',
                'otp_verified': True,
                'created_at': datetime.utcnow().isoformat(),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }
            # Store without expiry - session remains valid until password is set
            session_key = f'otp_session:{session_id}'
            redis_client.set(session_key, json.dumps(session_data))
            logger.info(f"Created OTP session for {email} with unlimited validity")
        
        # For backward compatibility, still generate a token but with much longer expiry
        # This acts as a session identifier
        temp_token = session_id
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully',
            'temp_token': temp_token,
            'user_id': str(user['_id']),
            'requires_password': not user.get('password_set', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in verify_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/set-initial-password', methods=['POST'])
def set_initial_password():
    """
    Set initial password for newly verified user.
    Requires temporary token from OTP verification.
    """
    try:
        data = request.get_json()
        temp_token = data.get('temp_token')
        password = data.get('password')
        
        if not temp_token or not password:
            return jsonify({'error': 'Token and password are required'}), 400
        
        # Verify session instead of JWT token (following OWASP session management best practices)
        logger.info(f"Attempting to verify OTP session for password setup")
        
        # First try to validate as session ID
        redis_client = get_redis()
        session_data = None
        
        if redis_client:
            session_key = f'otp_session:{temp_token}'
            session_json = redis_client.get(session_key)
            
            if session_json:
                try:
                    session_data = json.loads(session_json)
                    logger.info(f"Found valid OTP session for email: {session_data.get('email')}")
                except:
                    session_data = None
        
        # If no session found, fall back to JWT token validation for backward compatibility
        if not session_data:
            logger.info("No session found, trying JWT token validation")
            token_data, error_msg = verify_token(temp_token)
            
            if not token_data:
                logger.warning(f"Both session and token verification failed: {error_msg}")
                return jsonify({'error': 'Invalid or expired session. Please verify OTP again.'}), 401
                
            if token_data.get('purpose') != 'password_setup':
                logger.warning(f"Token purpose mismatch: expected 'password_setup', got '{token_data.get('purpose')}'")
                return jsonify({'error': 'Invalid session purpose'}), 401
            
            email = token_data.get('email')
            user_id = token_data.get('user_id')
        else:
            # Use session data
            if session_data.get('purpose') != 'password_setup':
                return jsonify({'error': 'Invalid session purpose'}), 401
            
            if not session_data.get('otp_verified'):
                return jsonify({'error': 'OTP not verified'}), 401
            
            email = session_data.get('email')
            user_id = session_data.get('user_id')
            
            # Optional: Validate session binding for extra security
            if request.remote_addr != session_data.get('ip_address'):
                logger.warning(f"Session IP mismatch for {email}: {request.remote_addr} != {session_data.get('ip_address')}")
                # For now, just log it, don't block (some users may have changing IPs)
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Get user
        db = get_db()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create user in Vault or generate bcrypt hash
        success, password_hash = create_user_in_vault(user['username'], password)
        
        if not success:
            return jsonify({'error': 'Failed to set password'}), 500
        
        # Update user record
        update_data = {
            'password_set': True,
            'password_set_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': True
        }
        
        # Store bcrypt hash if not using Vault
        if password_hash:
            update_data['password_hash'] = password_hash
        
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': update_data}
        )
        
        # Clean up the OTP session after successful password setup
        if redis_client and session_data:
            session_key = f'otp_session:{temp_token}'
            redis_client.delete(session_key)
            logger.info(f"Cleaned up OTP session for {email} after password setup")
        
        # Generate login token
        login_token = generate_token(
            user_data={
                'user_id': str(user['_id']),
                'email': user['email'],
                'username': user.get('username', user['email'].split('@')[0]),
                'role': user.get('role', 'user'),
                'organization_id': user.get('organization_id')
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Password set successfully. You can now login.',
            'token': login_token,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'name': user.get('name'),
                'role': user.get('role')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in set_initial_password: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/forgot-password/send-otp', methods=['POST'])
def forgot_password_send_otp():
    """
    Send OTP for password reset.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Call send_otp with password_reset purpose
        request.json = {'email': email, 'purpose': 'password_reset'}
        return send_otp()
        
    except Exception as e:
        logger.error(f"Error in forgot_password_send_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/forgot-password/reset', methods=['POST'])
def reset_password_with_otp():
    """
    Reset password using OTP verification.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        otp_code = data.get('otp')
        new_password = data.get('new_password')
        
        if not all([email, otp_code, new_password]):
            return jsonify({'error': 'Email, OTP, and new password are required'}), 400
        
        # Verify OTP
        result = otp_service.verify_otp(
            identifier=email,
            otp_code=otp_code
        )
        
        if not result.success:
            return jsonify({'error': result.message}), 400
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Get user
        db = get_db()
        user = db.users.find_one({'email': email})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password in Vault or bcrypt
        success, password_hash = create_user_in_vault(user['username'], new_password)
        
        if not success:
            return jsonify({'error': 'Failed to reset password'}), 500
        
        # Update user record
        update_data = {
            'password_reset_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Store bcrypt hash if not using Vault
        if password_hash:
            update_data['password_hash'] = password_hash
        
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': update_data}
        )
        
        # Send confirmation email
        email_service.send_email_sync(
            to_email=email,
            subject='Password Reset Successful',
            template_name='password_reset_success',
            template_data={
                'user_name': user.get('name', email.split('@')[0]),
                'reset_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. Please login with your new password.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in reset_password_with_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/forgot-password/verify-otp', methods=['POST'])
def forgot_password_verify_otp():
    """
    Verify OTP for password reset and return temp token.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        otp_code = data.get('otp')
        
        if not email or not otp_code:
            return jsonify({'error': 'Email and OTP code are required'}), 400
        
        # Verify OTP
        result = otp_service.verify_otp(
            identifier=email,
            otp_code=otp_code
        )
        
        if not result.success:
            return jsonify({'error': result.message}), 400
        
        # Get user
        db = get_db()
        user = db.users.find_one({'email': email})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Generate temporary token for password reset (valid for 30 minutes)
        temp_token = generate_token(
            user_data={
                'user_id': str(user['_id']),
                'email': email,
                'purpose': 'password_reset'
            },
            expires_in=1800  # 30 minutes
        )
        
        return jsonify({
            'success': True,
            'message': 'OTP verified successfully',
            'temp_token': temp_token
        }), 200
        
    except Exception as e:
        logger.error(f"Error in forgot_password_verify_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/forgot-password/reset-password', methods=['POST'])
def forgot_password_reset_password():
    """
    Reset password using temporary token from OTP verification.
    """
    try:
        data = request.get_json()
        temp_token = data.get('temp_token')
        password = data.get('password')
        
        if not temp_token or not password:
            return jsonify({'error': 'Temporary token and password are required'}), 400
        
        # Verify temp token
        try:
            token_data, error_msg = verify_token(temp_token)
            if not token_data or token_data.get('purpose') != 'password_reset':
                return jsonify({'error': error_msg or 'Invalid or expired token'}), 400
            
            user_id = token_data.get('user_id')
            email = token_data.get('email')
            
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return jsonify({'error': 'Invalid or expired token'}), 400
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        # Get user
        db = get_db()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update password in Vault or bcrypt
        success, password_hash = create_user_in_vault(user['username'], password)
        
        if not success:
            return jsonify({'error': 'Failed to reset password'}), 500
        
        # Update user record
        update_data = {
            'password_reset_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Store bcrypt hash if not using Vault
        if password_hash:
            update_data['password_hash'] = password_hash
        
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': update_data}
        )
        
        # Log password reset event
        logger.info(f"Password reset successfully for user: {user['username']} ({email})")
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully. Please login with your new password.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in forgot_password_reset_password: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@otp_auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """
    Resend OTP with cooldown protection.
    """
    try:
        data = request.get_json()
        email = data.get('email')
        purpose = data.get('purpose', 'verification')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get client IP
        client_ip = request.remote_addr
        
        # Try to resend OTP
        result = otp_service.resend_otp(
            identifier=email,
            ip_address=client_ip
        )
        
        if not result.success:
            return _otp_rate_limit_response(result)  # 429 with Retry-After
        
        # Send email
        db = get_db()
        user = db.users.find_one({'email': email})
        user_name = user.get('name', email.split('@')[0]) if user else 'User'
        
        if purpose == 'verification':
            template = 'otp_verification'
            subject = 'Verify Your TESA IoT Platform Account (Resent)'
        else:
            template = 'password_reset'
            subject = 'Reset Your TESA IoT Platform Password (Resent)'
        
        email_result = email_service.send_email_sync(
            to_email=email,
            subject=subject,
            template_name=template,
            template_data={
                'user_name': user_name,
                'otp_code': result.otp_code,
                'request_ip': client_ip,
                'request_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                'verification_url': f'https://{os.getenv("TESA_ADMIN_DOMAIN", "admin.localhost")}/auth/verify?email={email}'
            }
        )
        
        if not email_result['success']:
            return jsonify({'error': 'Failed to send email'}), 500
        
        return jsonify({
            'success': True,
            'message': 'New verification code sent to your email.',
            'cooldown_seconds': getattr(result, 'cooldown_seconds', 30)
        }), 200
        
    except Exception as e:
        logger.error(f"Error in resend_otp: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500