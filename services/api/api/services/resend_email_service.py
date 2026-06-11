# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Resend Email Service
Uses Resend API for reliable email delivery
"""

import os
import logging
from typing import Dict, Any, List, Union

logger = logging.getLogger(__name__)


def _admin_domain() -> str:
    """Host for account-setup / password-reset links sent in emails.

    Domain-agnostic self-host: defaults from the install's DOMAIN so links
    point at THIS deployment, not a baked-in admin.tesaiot.dev.
    TESA_ADMIN_DOMAIN (wired by generate-secrets.sh --domain) overrides.
    """
    return os.getenv(
        "TESA_ADMIN_DOMAIN",
        f"admin.{os.getenv('DOMAIN', 'localhost')}",
    )

class ResendEmailService:
    """Email service using Resend API for reliable delivery"""
    
    def __init__(self):
        # No hardcoded fallback: if RESEND_API_KEY is unset, email is disabled.
        self.api_key = os.getenv('RESEND_API_KEY')
        self.from_email = os.getenv(
            'EMAIL_FROM_ADDRESS',
            f"noreply@{os.getenv('DOMAIN', 'localhost')}",
        )
        self.from_name = os.getenv('EMAIL_FROM_NAME', 'TESA IoT Platform')

        if not self.api_key:
            logger.warning(
                "RESEND_API_KEY is not set; email delivery is disabled. "
                "Set RESEND_API_KEY to enable outgoing email."
            )
            self.resend = None
            self.initialized = False
            return

        # Initialize Resend
        try:
            import resend
            resend.api_key = self.api_key
            self.resend = resend
            self.initialized = True
            logger.info("Resend email service initialized successfully")
        except ImportError:
            logger.warning("Resend module not installed, using requests fallback")
            self.resend = None
            self.initialized = False
    
    def send_email(
        self, 
        to_email: Union[str, List[str]], 
        subject: str, 
        html_content: str = None, 
        text_content: str = None,
        reply_to: str = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Send email using Resend API
        
        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body
            reply_to: Reply-to email address
            headers: Additional email headers
            
        Returns:
            dict: Result with success status and message_id or error
        """
        
        # Email disabled when no API key is configured
        if not self.api_key:
            logger.warning("Email not sent: RESEND_API_KEY is not configured (email disabled)")
            return {'success': False, 'error': 'Email delivery is disabled (RESEND_API_KEY not set)'}

        # Ensure to_email is a list
        if isinstance(to_email, str):
            to_email = [to_email]
        
        # Validate inputs
        if not to_email:
            return {'success': False, 'error': 'No recipient email provided'}
        
        if not subject:
            return {'success': False, 'error': 'No subject provided'}
        
        if not html_content and not text_content:
            return {'success': False, 'error': 'No email content provided'}
        
        # Use Resend SDK if available
        if self.resend and self.initialized:
            return self._send_via_sdk(to_email, subject, html_content, text_content, reply_to, headers)
        else:
            return self._send_via_api(to_email, subject, html_content, text_content, reply_to, headers)
    
    def _send_via_sdk(
        self, 
        to_email: List[str], 
        subject: str, 
        html_content: str = None, 
        text_content: str = None,
        reply_to: str = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Send email using Resend Python SDK"""
        try:
            # Build email parameters
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": to_email,
                "subject": subject
            }
            
            if html_content:
                params["html"] = html_content
            if text_content:
                params["text"] = text_content
            if reply_to:
                params["reply_to"] = reply_to
            if headers:
                params["headers"] = headers
            
            # Send email
            response = self.resend.Emails.send(params)
            
            # Extract message ID from response
            message_id = response.get('id', 'unknown')
            
            logger.info(f"Email sent successfully via Resend SDK to {to_email[0]}, ID: {message_id}")
            
            return {
                'success': True,
                'message_id': message_id,
                'provider': 'resend_sdk'
            }
            
        except Exception as e:
            logger.error(f"Resend SDK error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'resend_sdk'
            }
    
    def _send_via_api(
        self, 
        to_email: List[str], 
        subject: str, 
        html_content: str = None, 
        text_content: str = None,
        reply_to: str = None,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Send email using Resend REST API directly"""
        try:
            import requests
            
            url = "https://api.resend.com/emails"
            
            # Build request headers
            api_headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Build email data
            data = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": to_email,
                "subject": subject
            }
            
            if html_content:
                data["html"] = html_content
            if text_content:
                data["text"] = text_content
            if reply_to:
                data["reply_to"] = reply_to
            if headers:
                data["headers"] = headers
            
            # Send request
            response = requests.post(url, json=data, headers=api_headers, timeout=30)
            
            if response.status_code in [200, 201]:
                result = response.json()
                message_id = result.get('id', 'unknown')
                
                logger.info(f"Email sent successfully via Resend API to {to_email[0]}, ID: {message_id}")
                
                return {
                    'success': True,
                    'message_id': message_id,
                    'provider': 'resend_api'
                }
            else:
                error_msg = f"Resend API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'provider': 'resend_api'
                }
                
        except Exception as e:
            logger.error(f"Resend API request error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'provider': 'resend_api'
            }
    
    def send_otp_email(
        self, 
        to_email: str, 
        otp_code: str, 
        user_name: str = None,
        expiry_minutes: int = 15,
        invited_by: str = None,
        organization_name: str = None,
        password_setup_url: str = None
    ) -> Dict[str, Any]:
        """
        Send OTP verification email
        
        Args:
            to_email: Recipient email
            otp_code: OTP verification code
            user_name: User's name for personalization
            expiry_minutes: OTP expiry time in minutes
            invited_by: Name of person who invited this user
            organization_name: Organization name
            password_setup_url: URL to set password after verification
            
        Returns:
            dict: Result with success status and message_id or error
        """
        
        # Build subject based on context
        if invited_by:
            subject = f"You're invited to TESA IoT Platform by {organization_name or 'your organization'}"
        else:
            subject = "Your TESA IoT Platform Verification Code"
        
        # Default password setup URL if not provided
        if not password_setup_url:
            password_setup_url = f'https://{_admin_domain()}/auth/verify'

        # Support contact shown in the email body (env-driven, no baked-in org)
        support_email = os.getenv('SUPPORT_EMAIL', os.getenv('ADMIN_EMAIL', 'admin@localhost'))
        
        # Build invitation context message
        invitation_message = ""
        if invited_by and organization_name:
            invitation_message = f"""
            <div style="background: #e8f5e9; border-left: 4px solid #4caf50; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <strong>🎉 You're invited!</strong><br>
                {invited_by} ({organization_name} Admin) has invited you to join the TESA IoT Platform.
            </div>
            """
        
        # HTML email content with professional styling
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .content {{
            padding: 30px 20px;
        }}
        .otp-box {{
            background: #f8f9fa;
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin: 25px 0;
            text-align: center;
        }}
        .otp-code {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }}
        .expiry-notice {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 14px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white !important;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: 600;
        }}
        .button:hover {{
            background: #5a67d8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 TESA IoT Platform</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Account Verification</p>
        </div>
        <div class="content">
            <p style="font-size: 18px;">Hello {user_name or 'User'},</p>
            
            {invitation_message}
            
            <p>Please use the verification code below to complete your account setup:</p>
            
            <div class="otp-box">
                <div style="color: #6c757d; font-size: 14px; margin-bottom: 10px;">Your Verification Code</div>
                <div class="otp-code">{otp_code}</div>
            </div>
            
            <div class="expiry-notice">
                <strong>⏰ Important:</strong> This code will expire soon. Please use it promptly.
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="margin-bottom: 10px;">Click the button below to enter your verification code and set your password:</p>
                <a href="{password_setup_url}" class="button" style="color: white !important;">Set Your Password</a>
                <p style="font-size: 12px; color: #6c757d; margin-top: 10px;">
                    Or copy this link: <br>
                    <span style="color: #667eea; word-break: break-all;">{password_setup_url}</span>
                </p>
            </div>
            
            <p>If you didn't request this verification code, please ignore this email or contact our support team if you have concerns about your account security.</p>
            
            <p style="margin-top: 30px;">Need help? Contact our support team at <a href="mailto:{support_email}">{support_email}</a></p>
        </div>
        <div class="footer">
            <p>© 2025 TESA IoT Platform by Thai Embedded Systems Association (TESA). All rights reserved.</p>
            <p style="margin-top: 10px; font-size: 12px; color: #999;">
                This is an automated message. Please do not reply to this email.
            </p>
        </div>
    </div>
</body>
</html>
"""
        
        # Plain text version
        invitation_text = ""
        if invited_by and organization_name:
            invitation_text = f"""
You're invited!
{invited_by} ({organization_name} Admin) has invited you to join the TESA IoT Platform.

"""
        
        text_content = f"""
TESA IoT Platform - Account Verification

Hello {user_name or 'User'},

{invitation_text}Please use the verification code below to complete your account setup:

Your Verification Code: {otp_code}

This code will expire soon. Please use it promptly.

To set your password, visit:
{password_setup_url}

If you didn't request this verification code, please ignore this email or contact our support team if you have concerns about your account security.

Need help? Contact our support team at {support_email}

© 2025 TESA IoT Platform by Thai Embedded Systems Association (TESA). All rights reserved.
"""
        
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        organization_name: str = None
    ) -> Dict[str, Any]:
        """
        Send welcome email to new user
        
        Args:
            to_email: Recipient email
            user_name: User's name
            organization_name: Organization name
            
        Returns:
            dict: Result with success status and message_id or error
        """
        
        subject = "Welcome to TESA IoT Platform"
        admin_domain = _admin_domain()

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to TESA IoT Platform!</h1>
        </div>
        <div class="content">
            <h2>Hello {user_name},</h2>
            <p>Your account has been successfully created{f' for {organization_name}' if organization_name else ''}.</p>
            <p>You now have access to:</p>
            <ul>
                <li>Real-time device monitoring and management</li>
                <li>Advanced analytics and reporting</li>
                <li>Secure API access for integrations</li>
                <li>24/7 technical support</li>
            </ul>
            <p>Get started by logging in to your dashboard:</p>
            <a href="https://{admin_domain}" class="button">Access Dashboard</a>
            <p style="margin-top: 30px;">If you have any questions, our support team is here to help!</p>
        </div>
    </div>
</body>
</html>
"""
        
        text_content = f"""
Welcome to TESA IoT Platform!

Hello {user_name},

Your account has been successfully created{f' for {organization_name}' if organization_name else ''}.

You now have access to:
- Real-time device monitoring and management
- Advanced analytics and reporting
- Secure API access for integrations
- 24/7 technical support

Get started by logging in at: https://{admin_domain}

If you have any questions, our support team is here to help!

© 2025 TESA IoT Platform
"""
        
        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


# Convenience functions for direct usage
def send_otp_email_resend(to_email: str, otp_code: str, user_name: str = None) -> Dict[str, Any]:
    """Send OTP email using Resend service"""
    service = ResendEmailService()
    return service.send_otp_email(to_email, otp_code, user_name)

def send_welcome_email_resend(to_email: str, user_name: str, organization_name: str = None) -> Dict[str, Any]:
    """Send welcome email using Resend service"""
    service = ResendEmailService()
    return service.send_welcome_email(to_email, user_name, organization_name)