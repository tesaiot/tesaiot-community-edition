# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Notification Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import smtplib
import requests
import os
import time
import copy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from functools import wraps
from typing import Dict, Any, List, Optional

from .notification_acl_service import create_notification_safe

# Import API version
try:
    from .. import API_VERSION
except ImportError:
    API_VERSION = os.getenv("API_VERSION", "v2025.07-beta.1")

logger = logging.getLogger(__name__)

# Immutable configuration constants for defensive programming
NOTIFICATION_LIMITS = {
    'max_subject_length': 200,
    'max_body_length': 10000,
    'max_email_length': 254,
    'max_concurrent_notifications': 20,
    'max_retries': 3,
    'timeout_seconds': 30
}

SMTP_TIMEOUTS = (10, 30)  # (connect_timeout, read_timeout)
HTTP_TIMEOUTS = (5, 15)   # (connect_timeout, read_timeout)

# Thread pool for async notifications with limits
executor = ThreadPoolExecutor(max_workers=NOTIFICATION_LIMITS['max_concurrent_notifications'])

def validate_notification_inputs(func):
    """Decorator for input validation with fail-safe defaults."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Validate email addresses
        if 'to_email' in kwargs or (len(args) > 0 and '@' in str(args[0])):
            email = kwargs.get('to_email', args[0] if args else '')
            if not email or len(email) > NOTIFICATION_LIMITS['max_email_length'] or '@' not in email:
                logger.warning(f"Invalid email address: {email}")
                return False
        
        # Validate subject length
        if 'subject' in kwargs or (len(args) > 1):
            subject = kwargs.get('subject', args[1] if len(args) > 1 else '')
            if subject and len(subject) > NOTIFICATION_LIMITS['max_subject_length']:
                kwargs['subject'] = subject[:NOTIFICATION_LIMITS['max_subject_length']] + '...'
        
        # Validate body length
        if 'body' in kwargs or (len(args) > 2):
            body = kwargs.get('body', args[2] if len(args) > 2 else '')
            if body and len(body) > NOTIFICATION_LIMITS['max_body_length']:
                kwargs['body'] = body[:NOTIFICATION_LIMITS['max_body_length']] + '\n\n[Message truncated]'
        
        return func(*args, **kwargs)
    return wrapper

def retry_notification(func):
    """Decorator for retry logic with exponential backoff."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = NOTIFICATION_LIMITS['max_retries']
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"All retry attempts failed for {func.__name__}: {e}")
                    return False
                
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        return False
    return wrapper

@validate_notification_inputs
@retry_notification
def send_email_notification(to_email, subject, body, html_body=None):
    """
    Send email notification with defensive programming.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
        
    Returns:
        bool: True if sent successfully
    """
    try:
        # Get configuration with fail-safe defaults
        try:
            config = current_app.config
        except RuntimeError:
            # Fallback to environment variables if Flask context not available
            config = {
                'SMTP_SERVER': os.getenv('SMTP_SERVER', 'localhost'),
                'SMTP_PORT': int(os.getenv('SMTP_PORT', '587')),
                'SMTP_USERNAME': os.getenv('SMTP_USERNAME', 'noreply@tesa.io'),
                'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD', ''),
                'SMTP_USE_TLS': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
            }
        
        # Validate required configuration
        smtp_server = config.get('SMTP_SERVER')
        smtp_port = config.get('SMTP_PORT', 587)
        
        if not smtp_server:
            logger.error("SMTP server not configured")
            return False
        
        # Create message with defensive checks
        msg = MIMEMultipart('alternative')
        msg['Subject'] = str(subject or 'No Subject')[:NOTIFICATION_LIMITS['max_subject_length']]
        msg['From'] = str(config.get('SMTP_USERNAME', 'noreply@tesa.io'))
        msg['To'] = str(to_email)
        
        # Add text part with size validation
        safe_body = str(body or '')[:NOTIFICATION_LIMITS['max_body_length']]
        text_part = MIMEText(safe_body, 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Add HTML part if provided with size validation
        if html_body:
            safe_html = str(html_body)[:NOTIFICATION_LIMITS['max_body_length']]
            html_part = MIMEText(safe_html, 'html', 'utf-8')
            msg.attach(html_part)
        
        # Send email with timeout protection
        with smtplib.SMTP(smtp_server, smtp_port, timeout=SMTP_TIMEOUTS[0]) as server:
            server.set_debuglevel(0)  # Disable debug output
            
            if config.get('SMTP_USE_TLS'):
                server.starttls()
            
            smtp_username = config.get('SMTP_USERNAME')
            smtp_password = config.get('SMTP_PASSWORD')
            
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            
            server.send_message(msg, timeout=SMTP_TIMEOUTS[1])
        
        logger.info(f"Email sent to {to_email}: {subject[:50]}...")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

@retry_notification
def send_webhook_notification(url, payload, headers=None):
    """
    Send webhook notification with defensive programming.
    
    Args:
        url: Webhook URL
        payload: JSON payload to send
        headers: Optional headers
        
    Returns:
        bool: True if sent successfully
    """
    try:
        # Validate URL
        if not url or not isinstance(url, str):
            logger.error("Invalid webhook URL provided")
            return False
        
        if not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid webhook URL protocol: {url}")
            return False

        # SSRF guard: resolve the hostname and reject loopback/link-local/
        # private/multicast targets (incl. 169.254.169.254 metadata) unless
        # ALLOW_PRIVATE_WEBHOOKS=true.
        from ..utils.validation import validate_webhook_url
        url_ok, url_reason = validate_webhook_url(url)
        if not url_ok:
            logger.error(f"Webhook URL rejected (SSRF guard): {url_reason}")
            return False

        # Validate payload size
        if payload:
            try:
                import json
                payload_size = len(json.dumps(payload).encode('utf-8'))
                max_payload_size = 1024 * 1024  # 1MB limit
                if payload_size > max_payload_size:
                    logger.error(f"Webhook payload too large: {payload_size} bytes")
                    return False
            except Exception as e:
                logger.error(f"Failed to validate payload: {e}")
                return False
        
        # Defensive headers with immutable defaults
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'TESA-IoT-Platform/{API_VERSION}',
            'Accept': 'application/json',
            'Connection': 'close'  # Prevent connection pooling issues
        }
        
        if headers and isinstance(headers, dict):
            # Create safe copy and validate headers
            safe_headers = copy.deepcopy(default_headers)
            for key, value in headers.items():
                if isinstance(key, str) and isinstance(value, str):
                    safe_headers[str(key)[:100]] = str(value)[:500]  # Limit header sizes
        else:
            safe_headers = default_headers
        
        # Make request with defensive settings
        response = requests.post(
            url,
            json=payload,
            headers=safe_headers,
            timeout=HTTP_TIMEOUTS,
            allow_redirects=False,  # Prevent redirect attacks
            verify=True,  # Verify SSL certificates
            stream=False  # Don't stream large responses
        )
        
        # Validate response
        if response.status_code >= 400:
            logger.warning(f"Webhook returned error status {response.status_code}: {response.text[:200]}")
            return False
        
        logger.info(f"Webhook sent to {url[:50]}...: {response.status_code}")
        return True
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Webhook timeout to {url}: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Webhook connection error to {url}: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook request failed to {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending webhook to {url}: {e}")
        return False

def send_login_notification(user, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """
    Send login notification (async).
    
    Args:
        user: User object with email and name
    """
    def _send():
        try:
            # Check if user has login notifications enabled
            if not user.get('notifications', {}).get('login_alerts', False):
                return
            
            subject = "Login to TESA IoT Platform"
            body = f"""
Hello {user.get('name', 'User')},

A new login to your TESA IoT Platform account was detected.

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
IP Address: {ip_address or 'Unknown'}

If this wasn't you, please contact your administrator immediately.

Best regards,
TESA IoT Platform Team
            """
            
            send_email_notification(user['email'], subject, body)

            try:
                recipient_id = None
                if user.get('_id'):
                    recipient_id = str(user['_id'])

                if recipient_id:
                    create_notification_safe({
                        'type': 'user',
                        'subtype': 'login_alert',
                        'title': 'New login detected',
                        'message': f"A new login was detected for {user.get('email')} from {ip_address or 'unknown IP'}.",
                        'severity': 'info',
                        'priority': 'medium',
                        'organization_id': str(user.get('organization_id') or ''),
                        'recipient_type': 'user',
                        'recipient_id': recipient_id,
                        'metadata': {
                            'ip_address': ip_address,
                            'user_agent': user_agent,
                            'timestamp': datetime.now().isoformat()
                        }
                    })
            except Exception as notify_exc:
                logger.debug(f"Login notification feed emit skipped: {notify_exc}")

        except Exception as e:
            logger.error(f"Failed to send login notification: {e}")
    
    # Execute async
    executor.submit(_send)

def send_certificate_expiry_notification(
    certificate,
    days_until_expiry,
    recipients=None,
    *,
    send_email: bool = True,
    send_webhook: bool = True
):
    """
    Send certificate expiry notification.
    
    Args:
        certificate: Certificate object
        days_until_expiry: Days until certificate expires
    """
    def _send():
        try:
            # Determine email recipients
            recipient_list: List[str] = []
            if send_email and recipients:
                if isinstance(recipients, (list, tuple, set)):
                    recipient_list.extend([str(r) for r in recipients])
                else:
                    recipient_list.append(str(recipients))

            owner_email = certificate.get('owner_email')
            if send_email and owner_email:
                recipient_list.append(owner_email)

            # Remove duplicates while preserving order
            seen = set()
            recipient_list = [r for r in recipient_list if not (r in seen or seen.add(r))]

            if not recipient_list:
                logger.warning('No recipients defined for certificate expiry notification')
            
            subject = f"Certificate Expiring Soon - {certificate.get('device_name', 'Unknown Device')}"
            
            body = f"""
Hello,

The certificate for device '{certificate.get('device_name', 'Unknown')}' will expire in {days_until_expiry} days.

Certificate Details:
- Device ID: {certificate.get('device_id')}
- Serial Number: {certificate.get('serial_number')}
- Expires: {certificate.get('valid_to')}

Please renew the certificate before it expires to avoid service interruption.

You can renew the certificate from the TESA IoT Platform dashboard:
https://platform.tesa.io/certificates

Best regards,
TESA IoT Platform Team
            """
            
            if send_email:
                for recipient in recipient_list:
                    send_email_notification(recipient, subject, body)

            # Also send webhook if configured
            webhook_url = certificate.get('webhook_url')
            if send_webhook and webhook_url:
                send_webhook_notification(webhook_url, {
                    'event': 'certificate_expiring',
                    'device_id': certificate.get('device_id'),
                    'device_name': certificate.get('device_name'),
                    'serial_number': certificate.get('serial_number'),
                    'days_until_expiry': days_until_expiry,
                    'expires_at': certificate.get('valid_to')
                })
            
            # Create in-app notification for organization admins
            organization_id = certificate.get('organization_id') or certificate.get('organization')
            if organization_id:
                try:
                    org_id_str = str(organization_id)
                    severity = 'critical' if days_until_expiry <= 7 else 'high' if days_until_expiry <= 30 else 'medium'
                    priority = 'high' if severity in ['critical', 'high'] else 'medium'
                    message = (
                        f"Certificate for device {certificate.get('device_name', 'Unknown Device')} "
                        f"expires in {days_until_expiry} day(s)."
                    )
                    create_notification_safe({
                        'type': 'device',
                        'subtype': 'certificate_expiry',
                        'title': 'Device certificate expiring soon',
                        'message': message,
                        'severity': severity,
                        'priority': priority,
                        'organization_id': org_id_str,
                        'recipient_type': 'organization',
                        'recipient_id': org_id_str,
                        'metadata': {
                            'device_id': certificate.get('device_id'),
                            'device_name': certificate.get('device_name'),
                            'serial_number': certificate.get('serial_number'),
                            'days_until_expiry': days_until_expiry,
                            'expires_at': certificate.get('valid_to')
                        }
                    })
                except Exception as exc:
                    logger.error(f"Failed to create certificate expiry notification record: {exc}")

        except Exception as e:
            logger.error(f"Failed to send certificate expiry notification: {e}")
    
    # Execute async
    executor.submit(_send)

def send_device_alert_notification(device, alert_type, message, metadata: Optional[Dict[str, Any]] = None):
    """
    Send device alert notification.
    
    Args:
        device: Device object
        alert_type: Type of alert
        message: Alert message
    """
    def _send():
        try:
            # Get device owner
            owner_email = device.get('owner_email')
            subject = f"Device Alert - {device.get('name', 'Unknown Device')}"

            body = f"""
Hello,

An alert has been triggered for device '{device.get('name', 'Unknown')}':

Alert Type: {alert_type}
Message: {message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Device Details:
- Device ID: {device.get('device_id')}
- Type: {device.get('type')}
- Location: {device.get('location', 'Unknown')}

Please check the device status in the TESA IoT Platform dashboard:
            https://platform.tesa.io/devices/{device.get('device_id')}

Best regards,
TESA IoT Platform Team
            """
            
            if owner_email:
                send_email_notification(owner_email, subject, body)
            
            organization_id = device.get('organization_id') or device.get('organization')
            if organization_id:
                try:
                    org_id_str = str(organization_id)
                    metadata_payload = {
                        'device_id': device.get('device_id'),
                        'device_name': device.get('name'),
                        'alert_type': alert_type,
                        'message': message
                    }
                    if metadata:
                        metadata_payload.update(metadata)
                    create_notification_safe({
                        'type': 'device',
                        'subtype': alert_type or 'device_offline',
                        'title': subject,
                        'message': message,
                        'severity': 'critical' if alert_type in ['device_offline', 'telemetry_alert'] else 'medium',
                        'priority': 'high' if alert_type in ['device_offline', 'telemetry_alert'] else 'medium',
                        'organization_id': org_id_str,
                        'recipient_type': 'organization',
                        'recipient_id': org_id_str,
                        'metadata': metadata_payload
                    })
                except Exception as exc:
                    logger.error(f"Failed to create device notification record: {exc}")

        except Exception as e:
            logger.error(f"Failed to send device alert notification: {e}")

    # Execute async
    executor.submit(_send)

def send_ai_ml_notification(notification_type, metadata):
    """
    Send AI/ML related notification.
    
    Args:
        notification_type: Type of AI/ML notification
        metadata: Dictionary containing notification metadata
    """
    def _send():
        try:
            # Get recipient email
            recipient_email = metadata.get('recipient_email')
            
            # Map notification types to subjects and bodies
            if notification_type == 'model_training_complete':
                subject = f"AI Model Training Complete - {metadata.get('model_name', 'Unknown Model')}"
                body = f"""
Hello,

The AI model '{metadata.get('model_name', 'Unknown')}' has completed training.

Training Results:
- Duration: {metadata.get('training_duration', 'N/A')}
- Final Accuracy: {metadata.get('accuracy', 'N/A')}%
- Loss: {metadata.get('loss', 'N/A')}
- Epochs: {metadata.get('epochs', 'N/A')}
- Dataset Size: {metadata.get('dataset_size', 'N/A')} samples

Model ID: {metadata.get('model_id', 'N/A')}
View detailed results: https://platform.tesa.io/ai/models/{metadata.get('model_id', '')}

Best regards,
TESA IoT Platform AI Team
                """
                
            elif notification_type == 'anomaly_detected':
                subject = f"Anomaly Detected - {metadata.get('device_name', 'Unknown Device')}"
                body = f"""
Hello,

An anomaly has been detected by our AI system:

Anomaly Details:
- Device: {metadata.get('device_name', 'Unknown')}
- Anomaly Score: {metadata.get('anomaly_score', 'N/A')}
- Detected Pattern: {metadata.get('pattern', 'N/A')}
- Severity: {metadata.get('severity', 'Medium')}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Recommended Actions:
{metadata.get('recommendations', '- Review device logs' + chr(10) + '- Check sensor readings' + chr(10) + '- Inspect physical device')}

View details: https://platform.tesa.io/ai/anomalies/{metadata.get('anomaly_id', '')}

Best regards,
TESA IoT Platform AI Team
                """
                
            elif notification_type == 'predictive_maintenance':
                subject = f"Predictive Maintenance Alert - {metadata.get('device_name', 'Unknown Device')}"
                body = f"""
Hello,

Our AI system has identified a potential maintenance requirement:

Maintenance Prediction:
- Device: {metadata.get('device_name', 'Unknown')}
- Component: {metadata.get('component', 'Unknown')}
- Predicted Failure: {metadata.get('failure_prediction', 'N/A')}
- Confidence: {metadata.get('confidence', 'N/A')}%
- Recommended Action By: {metadata.get('action_by_date', 'N/A')}

Suggested Actions:
{metadata.get('maintenance_steps', '1. Schedule inspection' + chr(10) + '2. Order replacement parts' + chr(10) + '3. Plan maintenance window')}

View maintenance schedule: https://platform.tesa.io/maintenance/{metadata.get('device_id', '')}

Best regards,
TESA IoT Platform AI Team
                """
                
            elif notification_type == 'performance_optimization':
                subject = f"Performance Optimization Suggestion - {metadata.get('system_name', 'System')}"
                body = f"""
Hello,

Our AI system has identified performance optimization opportunities:

Optimization Details:
- System: {metadata.get('system_name', 'Unknown')}
- Current Performance: {metadata.get('current_performance', 'N/A')}
- Potential Improvement: {metadata.get('improvement_percentage', 'N/A')}%
- Optimization Type: {metadata.get('optimization_type', 'N/A')}

Suggested Optimizations:
{metadata.get('suggestions', '- Review and apply suggested configuration changes')}

Estimated Benefits:
- Performance Gain: {metadata.get('performance_gain', 'N/A')}%
- Energy Savings: {metadata.get('energy_savings', 'N/A')}%
- Cost Reduction: {metadata.get('cost_reduction', 'N/A')}%

Apply optimizations: https://platform.tesa.io/ai/optimizations/{metadata.get('optimization_id', '')}

Best regards,
TESA IoT Platform AI Team
                """
                
            elif notification_type == 'model_accuracy_update':
                subject = f"Model Accuracy Update - {metadata.get('model_name', 'Unknown Model')}"
                body = f"""
Hello,

The accuracy of AI model '{metadata.get('model_name', 'Unknown')}' has been updated:

Accuracy Metrics:
- Previous Accuracy: {metadata.get('previous_accuracy', 'N/A')}%
- Current Accuracy: {metadata.get('current_accuracy', 'N/A')}%
- Change: {metadata.get('accuracy_change', 'N/A')}%
- Evaluation Date: {datetime.now().strftime('%Y-%m-%d')}

Performance Trends:
- Precision: {metadata.get('precision', 'N/A')}
- Recall: {metadata.get('recall', 'N/A')}
- F1 Score: {metadata.get('f1_score', 'N/A')}

{metadata.get('recommendation', 'Consider retraining if accuracy has decreased significantly.')}

View detailed metrics: https://platform.tesa.io/ai/models/{metadata.get('model_id', '')}/metrics

Best regards,
TESA IoT Platform AI Team
                """
                
            elif notification_type == 'system_health_ai_alert':
                subject = f"AI System Health Alert - {metadata.get('alert_level', 'Warning')}"
                body = f"""
Hello,

Our AI monitoring system has detected a health issue:

Alert Details:
- Level: {metadata.get('alert_level', 'Warning')}
- Component: {metadata.get('affected_component', 'Unknown')}
- Issue: {metadata.get('issue_description', 'N/A')}
- Impact: {metadata.get('impact', 'N/A')}
- Detection Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

AI Analysis:
- Root Cause: {metadata.get('root_cause', 'Under investigation')}
- Probability: {metadata.get('confidence', 'N/A')}%
- Predicted Resolution Time: {metadata.get('resolution_time', 'N/A')}

Recommended Actions:
{metadata.get('recommended_actions', '1. Review system logs' + chr(10) + '2. Check resource utilization' + chr(10) + '3. Contact support if issue persists')}

View system health dashboard: https://platform.tesa.io/system-health

Best regards,
TESA IoT Platform AI Team
                """
            else:
                # Generic AI/ML notification
                subject = f"AI/ML Notification - {notification_type}"
                body = f"""
Hello,

An AI/ML event has occurred:

Type: {notification_type}
Details: {metadata.get('message', 'No additional details available')}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Best regards,
TESA IoT Platform AI Team
                """
            
            if recipient_email:
                send_email_notification(recipient_email, subject, body)
            
            # Also send webhook if configured
            webhook_url = metadata.get('webhook_url')
            if webhook_url:
                send_webhook_notification(webhook_url, {
                    'event': f'ai_ml_{notification_type}',
                    'metadata': metadata,
                    'timestamp': datetime.now().isoformat()
                })

            organization_id = metadata.get('organization_id')
            recipient_user_id = metadata.get('recipient_user_id')
            if organization_id or recipient_user_id:
                try:
                    org_id_str = str(organization_id) if organization_id else None
                    message_preview = metadata.get('summary') or metadata.get('message') or notification_type.replace('_', ' ').title()
                    notification_payload: Dict[str, Any] = {
                        'type': 'ai_ml',
                        'subtype': notification_type,
                        'title': subject,
                        'message': message_preview,
                        'severity': metadata.get('severity', 'medium'),
                        'priority': metadata.get('priority', 'medium'),
                        'metadata': {k: v for k, v in metadata.items() if k not in {'recipient_email'}},
                    }

                    if recipient_user_id:
                        notification_payload['recipient_type'] = 'user'
                        notification_payload['recipient_id'] = str(recipient_user_id)
                        if org_id_str:
                            notification_payload['organization_id'] = org_id_str
                    elif org_id_str:
                        notification_payload['recipient_type'] = 'organization'
                        notification_payload['recipient_id'] = org_id_str
                        notification_payload['organization_id'] = org_id_str
                    else:
                        raise ValueError('Missing organization context for AI notification')

                    create_notification_safe(notification_payload)
                except Exception as exc:
                    logger.error(f"Failed to create AI/ML notification record: {exc}")
            
        except Exception as e:
            logger.error(f"Failed to send AI/ML notification: {e}")
    
    # Execute async
    executor.submit(_send)


# Notification service is a module with functions, not a class
# No service instance needed as functions are imported directly
