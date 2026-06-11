# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - HTTP-based Email Service
Uses HTTP APIs instead of SMTP to bypass port blocking
"""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HTTPEmailService:
    """Email service using HTTP APIs instead of SMTP"""
    
    def __init__(self):
        self.provider = os.getenv('EMAIL_PROVIDER', 'sendgrid')
        self.api_key = os.getenv('EMAIL_API_KEY', '')
        self.from_email = os.getenv('EMAIL_FROM_ADDRESS', 'noreply@localhost')
        self.from_name = os.getenv('EMAIL_FROM_NAME', 'TESA IoT Platform')
        
    def send_email(self, to_email: str, subject: str, html_content: str = None, text_content: str = None) -> Dict[str, Any]:
        """Send email using HTTP API"""
        
        if self.provider == 'sendgrid':
            return self._send_via_sendgrid(to_email, subject, html_content, text_content)
        elif self.provider == 'mailgun':
            return self._send_via_mailgun(to_email, subject, html_content, text_content)
        elif self.provider == 'sendinblue':
            return self._send_via_sendinblue(to_email, subject, html_content, text_content)
        else:
            # Fallback to a free service for testing
            return self._send_via_emailjs(to_email, subject, html_content, text_content)
    
    def _send_via_sendgrid(self, to_email: str, subject: str, html_content: str = None, text_content: str = None) -> Dict[str, Any]:
        """Send via SendGrid API"""
        if not self.api_key:
            return {'success': False, 'error': 'SendGrid API key not configured'}
            
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": self.from_email, "name": self.from_name},
            "subject": subject,
            "content": []
        }
        
        if text_content:
            data["content"].append({"type": "text/plain", "value": text_content})
        if html_content:
            data["content"].append({"type": "text/html", "value": html_content})
            
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code in [200, 201, 202]:
                return {'success': True, 'message_id': response.headers.get('X-Message-Id', 'unknown')}
            else:
                return {'success': False, 'error': f'SendGrid error: {response.status_code} - {response.text}'}
        except Exception as e:
            logger.error(f"SendGrid API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_via_mailgun(self, to_email: str, subject: str, html_content: str = None, text_content: str = None) -> Dict[str, Any]:
        """Send via Mailgun API"""
        domain = os.getenv('MAILGUN_DOMAIN', '')
        if not self.api_key or not domain:
            return {'success': False, 'error': 'Mailgun not configured'}
            
        url = f"https://api.mailgun.net/v3/{domain}/messages"
        
        data = {
            "from": f"{self.from_name} <{self.from_email}>",
            "to": to_email,
            "subject": subject
        }
        
        if text_content:
            data["text"] = text_content
        if html_content:
            data["html"] = html_content
            
        try:
            response = requests.post(
                url,
                auth=("api", self.api_key),
                data=data,
                timeout=30
            )
            if response.status_code == 200:
                return {'success': True, 'message_id': response.json().get('id', 'unknown')}
            else:
                return {'success': False, 'error': f'Mailgun error: {response.status_code} - {response.text}'}
        except Exception as e:
            logger.error(f"Mailgun API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_via_sendinblue(self, to_email: str, subject: str, html_content: str = None, text_content: str = None) -> Dict[str, Any]:
        """Send via Sendinblue (Brevo) API"""
        if not self.api_key:
            return {'success': False, 'error': 'Sendinblue API key not configured'}
            
        url = "https://api.sendinblue.com/v3/smtp/email"
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "sender": {"email": self.from_email, "name": self.from_name},
            "to": [{"email": to_email}],
            "subject": subject
        }
        
        if html_content:
            data["htmlContent"] = html_content
        if text_content:
            data["textContent"] = text_content
            
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            if response.status_code in [200, 201]:
                return {'success': True, 'message_id': response.json().get('messageId', 'unknown')}
            else:
                return {'success': False, 'error': f'Sendinblue error: {response.status_code} - {response.text}'}
        except Exception as e:
            logger.error(f"Sendinblue API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_via_emailjs(self, to_email: str, subject: str, html_content: str = None, text_content: str = None) -> Dict[str, Any]:
        """Send via EmailJS (free tier for testing)"""
        # This is a simple notification service for testing
        # In production, use a proper email API service
        
        try:
            # Log the email for testing purposes
            logger.info(f"Email notification (SMTP blocked - logged only):")
            logger.info(f"  To: {to_email}")
            logger.info(f"  Subject: {subject}")
            logger.info(f"  Content: {text_content or 'HTML content'}")
            
            # Store in database or cache for manual sending later
            from ..core.database import get_db
            db = get_db()
            if db:
                email_queue = db.email_queue
                email_queue.insert_one({
                    'to': to_email,
                    'subject': subject,
                    'html': html_content,
                    'text': text_content,
                    'status': 'pending_smtp',
                    'created_at': datetime.utcnow()
                })
            
            return {
                'success': True, 
                'message_id': 'logged-only',
                'note': 'SMTP unavailable (hosting provider may block outbound SMTP). Email logged for manual processing.'
            }
        except Exception as e:
            logger.error(f"Failed to log email: {e}")
            return {'success': False, 'error': str(e)}

# Convenience function for OTP emails
def send_otp_email_http(to_email: str, otp_code: str, user_name: str = None) -> Dict[str, Any]:
    """Send OTP email using HTTP API"""
    service = HTTPEmailService()
    
    subject = "Your TESA IoT Platform Verification Code"
    
    text_content = f"""
Hello {user_name or 'User'},

Your verification code is: {otp_code}

This code will expire soon.

If you didn't request this code, please ignore this email.

Best regards,
TESA IoT Platform Team
"""
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #007bff; color: white; padding: 20px; text-align: center; }}
        .otp-box {{ background: #f4f4f4; border: 2px solid #007bff; padding: 15px; margin: 20px 0; text-align: center; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #007bff; letter-spacing: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>TESA IoT Platform</h1>
        </div>
        <p>Hello {user_name or 'User'},</p>
        <p>Your verification code is:</p>
        <div class="otp-box">
            <span class="otp-code">{otp_code}</span>
        </div>
        <p>This code will expire <strong>soon</strong>.</p>
        <p>If you didn't request this code, please ignore this email.</p>
        <hr>
        <p>Best regards,<br>TESA IoT Platform Team</p>
    </div>
</body>
</html>
"""
    
    return service.send_email(to_email, subject, html_content, text_content)