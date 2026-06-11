# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - User Service with OTP Extensions
Copyright (C) 2024-2025 TESA IoT Platform

Extensions to user service for OTP-based user creation and activation
"""

import logging
import asyncio
import os
from datetime import datetime
from bson import ObjectId

from .otp_service import OTPService
from .email_service import EmailService
from .logging_service import logging_service
from ..core.database import get_db
from ..core.rbac import RBAC, Role

logger = logging.getLogger(__name__)

# Initialize services
otp_service = OTPService()
email_service = EmailService()

def send_email_sync(**kwargs):
    """Synchronous wrapper for async email sending"""
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Check if this is a templated email
        if 'template_name' in kwargs:
            # Use send_templated_email for template-based emails
            result = loop.run_until_complete(email_service.send_templated_email(**kwargs))
        else:
            # Use send_email for raw emails
            result = loop.run_until_complete(email_service.send_email(**kwargs))
        return {'success': True, 'result': result}
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        return {'success': False, 'error': str(e)}

def create_user_with_otp(data, current_user):
    """
    Create new user without password - send OTP for activation.
    
    Args:
        data: User data (email, name, role, organization_id)
        current_user: Current admin user creating the account
        
    Returns:
        tuple: (user_dict, message) - user or (None, error_message)
    """
    try:
        db = get_db()
        
        # Validate required fields
        email = data.get('email', '').lower().strip()
        name = data.get('name', '').strip()
        role = RBAC.canonicalize_role(data.get('role', 'user'))
        
        # Handle both organization_id and organizationId (from frontend)
        organization_id = data.get('organization_id') or data.get('organizationId')
        reason = (data.get('reason') or data.get('creation_reason') or '').strip()
        
        if not email:
            return None, "Email is required"
        
        if not name:
            return None, "Name is required"
        
        # Check if user already exists
        existing_user = db.users.find_one({'email': email})
        if existing_user:
            return None, "User with this email already exists"
        
        # Handle organization for different admin types
        if RBAC.is_platform_admin(current_user):
            # Platform admin can create users for any organization but must specify target org
            if not organization_id:
                return None, "Organization ID is required for platform admin"
        elif current_user.get('role') == Role.SUPER_ADMIN.value:
            # Super admin can create users across organizations but we expect explicit org
            if not organization_id:
                return None, "Organization ID is required for super admin"
            if not reason:
                logger.warning("Super admin %s created user without providing onboarding reason", current_user.get('email'))
        else:
            # For org admins and other roles
            admin_org = current_user.get('organization_id') or current_user.get('organizationId')

            if not organization_id:
                # Use the admin's organization if not specified
                if admin_org:
                    organization_id = admin_org
                    logger.info(f"Using admin's organization: {organization_id}")
                else:
                    return None, "Organization ID is required"
            else:
                # Verify admin has access to the specified organization
                if not RBAC.can_access_organization(current_user, str(organization_id)):
                    return None, "You can only create users for your organization"
        
        # Generate username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        
        # Ensure unique username
        while db.users.find_one({'username': username}):
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user document (without password)
        user_doc = {
            'email': email,
            'username': username,
            'name': name,
            'role': role,
            'organization_id': organization_id,
            'organization': data.get('organization', ''),
            'is_active': False,  # Inactive until email verified and password set
            'email_verified': False,
            'password_set': False,
            'created_at': datetime.utcnow(),
            'created_by': str(current_user.get('_id', current_user.get('id'))),
            'updated_at': datetime.utcnow()
        }
        
        # Insert user into database
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
        
        # Generate OTP for email verification
        client_ip = '127.0.0.1'  # Internal creation
        otp_result = otp_service.generate_otp(
            identifier=email,
            ip_address=client_ip,
            is_admin=True  # Admin creating user bypasses rate limits
        )
        
        if not otp_result.success:
            # Rollback user creation if OTP generation fails
            db.users.delete_one({'_id': result.inserted_id})
            return None, f"Failed to generate verification code: {otp_result.message}"
        
        # Send welcome email with OTP
        # Try SMTP first, fallback to HTTP if SMTP is blocked
        email_result = send_email_sync(
            to_addresses=[email],
            template_name='welcome',
            template_data={
                'user_name': name,
                'email': email,
                'otp_code': otp_result.otp_code,
                'organization_name': data.get('organization', 'Your Organization'),
                'admin_name': current_user.get('name', 'Administrator'),
                'platform_name': 'TESA IoT Platform',
                'invited_by': current_user.get('name'),  # Pass inviting admin's name
                'verification_url': f'https://{os.getenv("TESA_ADMIN_DOMAIN", "admin.localhost")}/auth/verify?email={email}',  # Add verification URL with email parameter
                'password_setup_url': f'https://{os.getenv("TESA_ADMIN_DOMAIN", "admin.localhost")}/auth/verify'  # Keep for backward compatibility
            }
        )
        
        if not email_result['success']:
            # SMTP failed, try Resend email service
            logger.warning(f"SMTP failed, trying Resend email service: {email_result.get('error')}")
            try:
                from .resend_email_service import ResendEmailService
                resend_service = ResendEmailService()
                resend_result = resend_service.send_otp_email(
                    to_email=email,
                    otp_code=otp_result.otp_code,
                    user_name=name,
                    invited_by=current_user.get('name'),
                    organization_name=data.get('organization', 'Your Organization'),
                    password_setup_url=f'https://{os.getenv("TESA_ADMIN_DOMAIN", "admin.localhost")}/auth/verify?email={email}'
                )
                if resend_result['success']:
                    logger.info(f"Email sent via Resend to {email}, ID: {resend_result.get('message_id')}")
                    email_result = resend_result
                else:
                    logger.error(f"Resend email also failed: {resend_result.get('error')}")
            except Exception as e:
                logger.error(f"Failed to use Resend email service: {e}")
        
        if not email_result['success']:
            logger.error(f"Failed to send welcome email to {email}: {email_result.get('error')}")
            # Don't rollback - admin can resend OTP later
        
        # Audit trail for onboarding actions
        audit_reason = reason if reason else 'not_provided'
        try:
            logging_service.log_activity(
                action='user_create_otp',
                resource_type='user',
                resource_id=str(user_doc['_id']),
                result='success',
                organization_id=str(organization_id) if organization_id else None,
                user_id=str(current_user.get('_id', current_user.get('id'))),
                metadata={
                    'created_user_email': email,
                    'created_role': role,
                    'created_user_id': str(user_doc['_id']),
                    'requested_by': current_user.get('email'),
                    'reason': audit_reason,
                    'target_organization': str(organization_id) if organization_id else None,
                    'created_via': 'create-with-otp'
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to log activity for onboarding user {email}: {audit_error}")

        # Return user info (without sensitive data)
        return {
            'id': str(user_doc['_id']),
            'email': user_doc['email'],
            'username': user_doc['username'],
            'name': user_doc['name'],
            'role': role,
            'organization_id': user_doc['organization_id'],
            'is_active': user_doc['is_active'],
            'email_verified': user_doc['email_verified'],
            'password_set': user_doc['password_set'],
            'otp_sent': email_result['success']
        }, "User created successfully. Activation email sent."
        
    except Exception as e:
        logger.error(f"Error creating user with OTP: {str(e)}")
        return None, f"Failed to create user: {str(e)}"

def update_user_fields_for_otp(user_id):
    """
    Update existing user collection to support OTP fields.
    This is a migration helper function.
    """
    try:
        db = get_db()
        
        # Add new fields to existing users
        db.users.update_many(
            {'email_verified': {'$exists': False}},
            {
                '$set': {
                    'email_verified': True,  # Existing users are considered verified
                    'password_set': True,     # Existing users have passwords
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        logger.info("Updated existing users with OTP fields")
        return True
        
    except Exception as e:
        logger.error(f"Error updating user fields: {str(e)}")
        return False

def get_user_by_email(email):
    """
    Get user by email address.
    
    Args:
        email: User email
        
    Returns:
        dict: User document or None
    """
    try:
        db = get_db()
        return db.users.find_one({'email': email.lower()})
    except Exception as e:
        logger.error(f"Error getting user by email: {str(e)}")
        return None

def update_user(user_id, update_data):
    """
    Update user document.
    
    Args:
        user_id: User ID (string or ObjectId)
        update_data: Fields to update
        
    Returns:
        bool: Success status
    """
    try:
        db = get_db()
        
        # Ensure user_id is ObjectId
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        # Add update timestamp
        update_data['updated_at'] = datetime.utcnow()
        
        result = db.users.update_one(
            {'_id': user_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
        
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return False
