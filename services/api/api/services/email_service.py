# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Professional Email Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import asyncio
import logging
import smtplib
import time
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import os
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis
        aioredis = redis
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False
        aioredis = None

try:
    from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    Environment = FileSystemLoader = Template = select_autoescape = None


def _autoescape_policy():
    """Jinja2 autoescape policy enabling escaping for HTML/XML templates.

    Used everywhere a template is rendered so user-supplied template data is
    HTML-escaped by default, mitigating stored/reflected XSS in emails.
    """
    return select_autoescape(['html', 'xml']) if select_autoescape else True


def _make_inline_template(source: str):
    """Build an inline Jinja2 Template with autoescape enabled.

    `jinja2.Template` does not honor a global autoescape policy on its own, so
    we render it through an autoescaping Environment instead of constructing a
    raw Template (which renders unescaped).
    """
    env = Environment(autoescape=_autoescape_policy())
    return env.from_string(source)
import hashlib

try:
    from .base_service import BaseService
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    try:
        from base_service import BaseService
    except ImportError:
        # Create a minimal BaseService if not available
        class BaseService:
            def __init__(self, db_session=None, redis_client=None, logger=None):
                self.db = db_session
                self.redis = redis_client
                self.logger = logger or logging.getLogger(self.__class__.__name__)
            
            @staticmethod
            def timing_decorator(func):
                return func
            
            async def validate_permissions(self, user_role, org_id=None, resource_id=None, action='read'):
                return True

# Configure logging
logger = logging.getLogger(__name__)

class EmailPriority(Enum):
    """Email priority levels"""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"

class EmailStatus(Enum):
    """Email delivery status"""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class EmailTemplate:
    """Email template configuration"""
    name: str
    subject_template: str
    html_template: Optional[str] = None
    text_template: Optional[str] = None
    template_variables: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EmailAttachment:
    """Email attachment configuration"""
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"

@dataclass
class EmailMessage:
    """Email message data structure"""
    to_addresses: List[str]
    subject: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    cc_addresses: List[str] = field(default_factory=list)
    bcc_addresses: List[str] = field(default_factory=list)
    attachments: List[EmailAttachment] = field(default_factory=list)
    priority: EmailPriority = EmailPriority.NORMAL
    template: Optional[EmailTemplate] = None
    template_data: Dict[str, Any] = field(default_factory=dict)
    tracking_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EmailDeliveryResult:
    """Email delivery result"""
    message_id: str
    status: EmailStatus
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    delivery_time_ms: Optional[int] = None

class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass

class EmailServiceError(Exception):
    """Base email service exception"""
    pass

class EmailService(BaseService):
    """
    Professional Email Service with Gmail SMTP integration
    
    Features:
    - Async email sending with proper error handling
    - HTML and plain text email support
    - Rate limiting awareness
    - Retry mechanism for failed sends
    - Email queuing with Redis
    - Template system with Jinja2
    - Comprehensive logging and audit trail
    - Attachment support
    - Email tracking and delivery status
    """
    
    def __init__(self, db_session=None, redis_client=None, logger=None):
        """
        Initialize Email Service
        
        Args:
            db_session: Database session for audit logging
            redis_client: Redis client for queuing and rate limiting
            logger: Logger instance
        """
        super().__init__(db_session, redis_client, logger)
        
        # Load configuration from environment
        self.config = self._load_configuration()
        
        # Initialize template environment
        self.template_env = None
        self._setup_template_environment()
        
        # Rate limiting configuration
        self.rate_limits = {
            'per_minute': int(os.getenv('EMAIL_RATE_LIMIT_MINUTE', '10')),
            'per_hour': int(os.getenv('EMAIL_RATE_LIMIT_HOUR', '100')),
            'per_day': int(os.getenv('EMAIL_RATE_LIMIT_DAY', '1000'))
        }
        
        # Retry configuration
        self.retry_config = {
            'max_attempts': int(os.getenv('EMAIL_MAX_RETRY_ATTEMPTS', '3')),
            'base_delay': int(os.getenv('EMAIL_RETRY_BASE_DELAY', '5')),
            'max_delay': int(os.getenv('EMAIL_RETRY_MAX_DELAY', '300')),
            'backoff_multiplier': float(os.getenv('EMAIL_RETRY_BACKOFF', '2.0'))
        }
        
        # Queue configuration
        self.queue_config = {
            'name': 'tesa:email:queue',
            'processing_batch_size': int(os.getenv('EMAIL_QUEUE_BATCH_SIZE', '5')),
            'max_queue_size': int(os.getenv('EMAIL_MAX_QUEUE_SIZE', '1000'))
        }
        
        self.logger.info("EmailService initialized successfully")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load email configuration from environment variables"""
        config = {
            'enabled': os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
            'host': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
            'port': int(os.getenv('EMAIL_PORT', '587')),
            'use_tls': os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
            'use_ssl': os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true',
            'username': os.getenv('EMAIL_USER', ''),
            'password': os.getenv('EMAIL_PASSWORD', ''),
            'from_name': os.getenv('EMAIL_FROM_NAME', 'TESA IoT Platform'),
            'from_address': os.getenv('EMAIL_FROM_ADDRESS', ''),
            'reply_to': os.getenv('EMAIL_REPLY_TO', ''),
            'timeout': int(os.getenv('EMAIL_TIMEOUT', '30')),
            'max_message_size': int(os.getenv('EMAIL_MAX_SIZE', '25')) * 1024 * 1024,  # 25MB default
        }
        
        # Validation
        if config['enabled']:
            required_fields = ['host', 'username', 'password', 'from_address']
            missing = [field for field in required_fields if not config.get(field)]
            if missing:
                self.logger.error(f"Missing required email configuration: {missing}")
                config['enabled'] = False
        
        return config
    
    def _setup_template_environment(self):
        """Setup Jinja2 template environment"""
        if not JINJA2_AVAILABLE:
            self.logger.warning("Jinja2 not available, template features will be limited")
            self.template_env = None
            return
            
        try:
            # Try to find templates directory
            template_dirs = [
                '/app/templates/email',
                './templates/email'
            ]
            
            template_dir = None
            for dir_path in template_dirs:
                if os.path.exists(dir_path):
                    template_dir = dir_path
                    break
            
            if template_dir:
                self.template_env = Environment(
                    loader=FileSystemLoader(template_dir),
                    autoescape=_autoescape_policy()
                )
                self.logger.info(f"Template environment initialized with directory: {template_dir}")
            else:
                # Create a basic string template environment with HTML/XML
                # autoescaping enabled (XSS mitigation).
                self.template_env = Environment(autoescape=_autoescape_policy())
                self.logger.warning("No template directory found, using string templates only")
                
        except Exception as e:
            self.logger.error(f"Failed to setup template environment: {e}")
            self.template_env = None
    
    async def validate_permissions(
        self, 
        user_role: str, 
        org_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: str = 'send_email'
    ) -> bool:
        """
        Validate user permissions for email operations
        
        Args:
            user_role: User's role
            org_id: Organization ID
            resource_id: Email template ID or recipient
            action: Action to perform
            
        Returns:
            True if user has permission
        """
        # Platform admins can perform all email operations
        if user_role == 'platform_admin':
            return True
        
        # Organization admins can send emails within their org
        if user_role == 'admin' and org_id:
            return True
        
        # Regular users can send basic notifications
        if user_role == 'user' and action in ['send_notification', 'send_otp']:
            return True
        
        return False
    
    def _generate_tracking_id(self, to_address: str, subject: str) -> str:
        """Generate unique tracking ID for email"""
        timestamp = str(int(time.time() * 1000))
        content = f"{to_address}:{subject}:{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def _check_rate_limit(self, identifier: str = "global") -> bool:
        """
        Check if rate limit is exceeded
        
        Args:
            identifier: Rate limit identifier (email address, IP, etc.)
            
        Returns:
            True if within limits, False if exceeded
        """
        if not self.redis:
            return True  # Skip rate limiting if Redis not available
        
        try:
            now = datetime.utcnow()
            
            # Check minute limit
            minute_key = f"email:rate_limit:{identifier}:minute:{now.strftime('%Y%m%d%H%M')}"
            minute_count = await self.redis.incr(minute_key)
            if minute_count == 1:
                await self.redis.expire(minute_key, 60)
            
            if minute_count > self.rate_limits['per_minute']:
                self.logger.warning(f"Rate limit exceeded (per minute) for {identifier}: {minute_count}")
                return False
            
            # Check hour limit
            hour_key = f"email:rate_limit:{identifier}:hour:{now.strftime('%Y%m%d%H')}"
            hour_count = await self.redis.incr(hour_key)
            if hour_count == 1:
                await self.redis.expire(hour_key, 3600)
            
            if hour_count > self.rate_limits['per_hour']:
                self.logger.warning(f"Rate limit exceeded (per hour) for {identifier}: {hour_count}")
                return False
            
            # Check day limit
            day_key = f"email:rate_limit:{identifier}:day:{now.strftime('%Y%m%d')}"
            day_count = await self.redis.incr(day_key)
            if day_count == 1:
                await self.redis.expire(day_key, 86400)
            
            if day_count > self.rate_limits['per_day']:
                self.logger.warning(f"Rate limit exceeded (per day) for {identifier}: {day_count}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Rate limit check failed: {e}")
            return True  # Allow sending if rate limit check fails
    
    async def _render_template(self, template: EmailTemplate, data: Dict[str, Any]) -> tuple:
        """
        Render email template with data
        
        Args:
            template: Email template configuration
            data: Template data
            
        Returns:
            Tuple of (subject, html_body, text_body)
        """
        try:
            # Merge template variables with provided data
            template_data = {**template.template_variables, **data}
            
            # Render subject (simple string substitution if Jinja2 not available)
            if JINJA2_AVAILABLE:
                subject_tmpl = _make_inline_template(template.subject_template)
                subject = subject_tmpl.render(**template_data)
            else:
                subject = template.subject_template.format(**template_data)
            
            # Render HTML body
            html_body = None
            if template.html_template:
                if JINJA2_AVAILABLE and self.template_env:
                    try:
                        html_tmpl = self.template_env.get_template(template.html_template)
                        html_body = html_tmpl.render(**template_data)
                    except Exception:
                        # Fallback to string template (autoescaped -> XSS-safe)
                        html_tmpl = _make_inline_template(template.html_template)
                        html_body = html_tmpl.render(**template_data)
                else:
                    # Simple string substitution fallback
                    html_body = template.html_template.format(**template_data)
            
            # Render text body
            text_body = None
            if template.text_template:
                if JINJA2_AVAILABLE:
                    try:
                        if self.template_env:
                            text_tmpl = self.template_env.get_template(template.text_template)
                            text_body = text_tmpl.render(**template_data)
                        else:
                            text_tmpl = _make_inline_template(template.text_template)
                            text_body = text_tmpl.render(**template_data)
                    except Exception:
                        text_tmpl = _make_inline_template(template.text_template)
                        text_body = text_tmpl.render(**template_data)
                else:
                    # Simple string substitution fallback
                    text_body = template.text_template.format(**template_data)
            
            return subject, html_body, text_body
            
        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            raise EmailServiceError(f"Template rendering failed: {str(e)}")
    
    async def _create_mime_message(self, email_msg: EmailMessage) -> MIMEMultipart:
        """
        Create MIME message from EmailMessage
        
        Args:
            email_msg: Email message data
            
        Returns:
            MIME message ready for sending
        """
        # Create message
        msg = MIMEMultipart('mixed')
        
        # Set headers
        msg['Subject'] = email_msg.subject
        msg['From'] = formataddr((
            email_msg.from_name or self.config['from_name'],
            email_msg.from_address or self.config['from_address']
        ))
        msg['To'] = ', '.join(email_msg.to_addresses)
        
        if email_msg.cc_addresses:
            msg['Cc'] = ', '.join(email_msg.cc_addresses)
        
        if email_msg.reply_to or self.config.get('reply_to'):
            msg['Reply-To'] = email_msg.reply_to or self.config['reply_to']
        
        # Set priority header
        if email_msg.priority == EmailPriority.HIGH:
            msg['X-Priority'] = '2'
            msg['X-MSMail-Priority'] = 'High'
        elif email_msg.priority == EmailPriority.URGENT:
            msg['X-Priority'] = '1'
            msg['X-MSMail-Priority'] = 'High'
        elif email_msg.priority == EmailPriority.LOW:
            msg['X-Priority'] = '4'
            msg['X-MSMail-Priority'] = 'Low'
        
        # Add tracking headers
        if email_msg.tracking_id:
            msg['X-TESA-Tracking-ID'] = email_msg.tracking_id
            msg['Message-ID'] = f"<{email_msg.tracking_id}@{self.config['host']}>"
        
        # Create body container
        body_container = MIMEMultipart('alternative')
        
        # Add text body
        if email_msg.text_body:
            text_part = MIMEText(email_msg.text_body, 'plain', 'utf-8')
            body_container.attach(text_part)
        
        # Add HTML body
        if email_msg.html_body:
            html_part = MIMEText(email_msg.html_body, 'html', 'utf-8')
            body_container.attach(html_part)
        
        # Attach body to message
        msg.attach(body_container)
        
        # Add attachments
        for attachment in email_msg.attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment.filename}'
            )
            msg.attach(part)
        
        return msg
    
    async def _send_email_smtp(self, email_msg: EmailMessage) -> EmailDeliveryResult:
        """
        Send email via SMTP
        
        Args:
            email_msg: Email message to send
            
        Returns:
            Email delivery result
        """
        start_time = time.time()
        tracking_id = email_msg.tracking_id or self._generate_tracking_id(
            email_msg.to_addresses[0], email_msg.subject
        )
        
        try:
            # Create MIME message
            mime_msg = await self._create_mime_message(email_msg)
            
            # All recipients (to, cc, bcc)
            all_recipients = list(set(
                email_msg.to_addresses + 
                email_msg.cc_addresses + 
                email_msg.bcc_addresses
            ))
            
            # Connect to SMTP server
            if self.config['use_ssl']:
                server = smtplib.SMTP_SSL(
                    self.config['host'], 
                    self.config['port'],
                    timeout=self.config['timeout']
                )
            else:
                server = smtplib.SMTP(
                    self.config['host'], 
                    self.config['port'],
                    timeout=self.config['timeout']
                )
                
                if self.config['use_tls']:
                    server.starttls()
            
            # Authenticate
            if self.config['username'] and self.config['password']:
                server.login(self.config['username'], self.config['password'])
            
            # Send message
            server.send_message(
                mime_msg,
                from_addr=email_msg.from_address or self.config['from_address'],
                to_addrs=all_recipients
            )
            
            server.quit()
            
            # Calculate delivery time
            delivery_time_ms = int((time.time() - start_time) * 1000)
            
            # Log successful delivery
            await self._log_email_delivery(
                tracking_id=tracking_id,
                recipients=email_msg.to_addresses,
                subject=email_msg.subject,
                status=EmailStatus.SENT,
                delivery_time_ms=delivery_time_ms,
                metadata=email_msg.metadata
            )
            
            return EmailDeliveryResult(
                message_id=tracking_id,
                status=EmailStatus.SENT,
                sent_at=datetime.utcnow(),
                delivery_time_ms=delivery_time_ms
            )
            
        except Exception as e:
            delivery_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            # Log failed delivery
            await self._log_email_delivery(
                tracking_id=tracking_id,
                recipients=email_msg.to_addresses,
                subject=email_msg.subject,
                status=EmailStatus.FAILED,
                error_message=error_msg,
                delivery_time_ms=delivery_time_ms,
                metadata=email_msg.metadata
            )
            
            return EmailDeliveryResult(
                message_id=tracking_id,
                status=EmailStatus.FAILED,
                error_message=error_msg,
                delivery_time_ms=delivery_time_ms
            )
    
    async def _log_email_delivery(
        self,
        tracking_id: str,
        recipients: List[str],
        subject: str,
        status: EmailStatus,
        delivery_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log email delivery attempt for audit trail
        
        Args:
            tracking_id: Email tracking ID
            recipients: List of recipients
            subject: Email subject
            status: Delivery status
            delivery_time_ms: Delivery time in milliseconds
            error_message: Error message if failed
            metadata: Additional metadata
        """
        try:
            log_entry = {
                'tracking_id': tracking_id,
                'timestamp': datetime.utcnow().isoformat(),
                'recipients': recipients,
                'subject': subject[:100],  # Truncate long subjects
                'status': status.value,
                'delivery_time_ms': delivery_time_ms,
                'error_message': error_message,
                'smtp_host': self.config['host'],
                'from_address': self.config['from_address'],
                'metadata': metadata or {}
            }
            
            # Log to application logger
            if status == EmailStatus.SENT:
                self.logger.info(f"Email sent successfully: {json.dumps(log_entry)}")
            else:
                self.logger.error(f"Email delivery failed: {json.dumps(log_entry)}")
            
            # Store in Redis for audit trail
            if self.redis:
                audit_key = f"email:audit:{tracking_id}"
                await self.redis.setex(audit_key, 86400 * 30, json.dumps(log_entry))  # 30 days
            
            # Store in database if available
            if self.db:
                # Implementation depends on database schema
                pass
                
        except Exception as e:
            self.logger.error(f"Failed to log email delivery: {e}")
    
    async def _queue_email(self, email_msg: EmailMessage, retry_count: int = 0) -> str:
        """
        Queue email for later processing
        
        Args:
            email_msg: Email message to queue
            retry_count: Current retry count
            
        Returns:
            Queue message ID
        """
        if not self.redis:
            raise EmailServiceError("Redis not available for email queuing")
        
        tracking_id = email_msg.tracking_id or self._generate_tracking_id(
            email_msg.to_addresses[0], email_msg.subject
        )
        
        queue_item = {
            'tracking_id': tracking_id,
            'email_msg': {
                'to_addresses': email_msg.to_addresses,
                'subject': email_msg.subject,
                'html_body': email_msg.html_body,
                'text_body': email_msg.text_body,
                'from_address': email_msg.from_address,
                'from_name': email_msg.from_name,
                'reply_to': email_msg.reply_to,
                'cc_addresses': email_msg.cc_addresses,
                'bcc_addresses': email_msg.bcc_addresses,
                'priority': email_msg.priority.value,
                'metadata': email_msg.metadata
            },
            'retry_count': retry_count,
            'queued_at': datetime.utcnow().isoformat(),
            'scheduled_for': datetime.utcnow().isoformat()
        }
        
        # Check queue size
        queue_size = await self.redis.llen(self.queue_config['name'])
        if queue_size >= self.queue_config['max_queue_size']:
            raise EmailServiceError("Email queue is full")
        
        # Add to queue
        await self.redis.lpush(self.queue_config['name'], json.dumps(queue_item))
        
        self.logger.info(f"Email queued with tracking ID: {tracking_id}")
        return tracking_id
    
    @BaseService.timing_decorator
    async def send_email(
        self,
        to_addresses: Union[str, List[str]],
        subject: str,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template: Optional[EmailTemplate] = None,
        template_data: Optional[Dict[str, Any]] = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        attachments: Optional[List[EmailAttachment]] = None,
        **kwargs
    ) -> EmailDeliveryResult:
        """
        Send email with comprehensive error handling and retry logic
        
        Args:
            to_addresses: Recipient email address(es)
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content  
            template: Email template to use
            template_data: Data for template rendering
            priority: Email priority
            attachments: File attachments
            **kwargs: Additional email options
            
        Returns:
            Email delivery result
        """
        if not self.config['enabled']:
            raise EmailServiceError("Email service is disabled")
        
        # Normalize to_addresses to list
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]
        
        # Validate recipients
        if not to_addresses:
            raise EmailServiceError("No recipients specified")
        
        # Check rate limits
        for recipient in to_addresses:
            if not await self._check_rate_limit(recipient):
                raise RateLimitError(f"Rate limit exceeded for recipient: {recipient}")
        
        # Create email message
        email_msg = EmailMessage(
            to_addresses=to_addresses,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_address=kwargs.get('from_address'),
            from_name=kwargs.get('from_name'),
            reply_to=kwargs.get('reply_to'),
            cc_addresses=kwargs.get('cc_addresses', []),
            bcc_addresses=kwargs.get('bcc_addresses', []),
            attachments=attachments or [],
            priority=priority,
            template=template,
            template_data=template_data or {},
            tracking_id=kwargs.get('tracking_id'),
            metadata=kwargs.get('metadata', {})
        )
        
        # Render template if provided
        if template:
            rendered_subject, rendered_html, rendered_text = await self._render_template(
                template, template_data or {}
            )
            email_msg.subject = rendered_subject
            if rendered_html:
                email_msg.html_body = rendered_html
            if rendered_text:
                email_msg.text_body = rendered_text
        
        # Ensure we have either HTML or text body
        if not email_msg.html_body and not email_msg.text_body:
            raise EmailServiceError("Email must have either HTML or text body")
        
        # Generate tracking ID if not provided
        if not email_msg.tracking_id:
            email_msg.tracking_id = self._generate_tracking_id(
                to_addresses[0], email_msg.subject
            )
        
        # Try to send immediately
        try:
            result = await self._send_email_smtp(email_msg)
            
            if result.status == EmailStatus.SENT:
                return result
            else:
                # Queue for retry if sending failed
                await self._queue_email(email_msg, retry_count=1)
                return result
                
        except Exception as e:
            self.logger.error(f"Failed to send email immediately: {e}")
            
            # Queue for later processing
            try:
                tracking_id = await self._queue_email(email_msg)
                return EmailDeliveryResult(
                    message_id=tracking_id,
                    status=EmailStatus.QUEUED,
                    error_message=str(e)
                )
            except Exception as queue_error:
                self.logger.error(f"Failed to queue email: {queue_error}")
                raise EmailServiceError(f"Failed to send or queue email: {str(e)}")
    
    @BaseService.timing_decorator
    async def send_templated_email(
        self,
        to_addresses: Union[str, List[str]],
        template_name: str,
        template_data: Dict[str, Any],
        priority: EmailPriority = EmailPriority.NORMAL,
        **kwargs
    ) -> EmailDeliveryResult:
        """
        Send email using predefined template
        
        Args:
            to_addresses: Recipient email address(es)
            template_name: Template name/identifier
            template_data: Data for template rendering
            priority: Email priority
            **kwargs: Additional options
            
        Returns:
            Email delivery result
        """
        # Load template (this could be from database, files, etc.)
        template = await self._get_email_template(template_name)
        if not template:
            raise EmailServiceError(f"Template not found: {template_name}")
        
        return await self.send_email(
            to_addresses=to_addresses,
            subject="",  # Will be set by template
            template=template,
            template_data=template_data,
            priority=priority,
            **kwargs
        )
    
    async def _get_email_template(self, template_name: str) -> Optional[EmailTemplate]:
        """
        Get email template by name
        
        Args:
            template_name: Template name
            
        Returns:
            Email template or None if not found
        """
        # This is a basic implementation - in production you might load from database
        templates = {
            'welcome': EmailTemplate(
                name='welcome',
                subject_template='Welcome to {{ platform_name }}',
                html_template='<h2>Welcome to {{ platform_name }}!</h2><p>Dear {{ user_name }},</p><p>Your account has been successfully created. You can now access all platform features.</p><p>Best regards,<br>{{ platform_name }} Team</p>',
                text_template='Welcome to {{ platform_name }}!\n\nDear {{ user_name }},\n\nYour account has been successfully created. You can now access all platform features.\n\nBest regards,\n{{ platform_name }} Team'
            ),
            'otp': EmailTemplate(
                name='otp',
                subject_template='Your verification code: {{ otp_code }}',
                text_template='Your verification code is: {{ otp_code }}\n\nThis code expires in {{ expiry_minutes }} minutes.\n\nIf you did not request this code, please ignore this email.\n\nBest regards,\n{{ platform_name }}'
            ),
            'password_reset': EmailTemplate(
                name='password_reset',
                subject_template='Password Reset Request for {{ platform_name }}',
                html_template='<h2>Password Reset Request</h2><p>Dear {{ user_name }},</p><p>You requested a password reset for your {{ platform_name }} account.</p><p>If you did not make this request, please ignore this email.</p><p>Best regards,<br>{{ platform_name }} Team</p>',
                text_template='Password Reset Request\n\nDear {{ user_name }},\n\nYou requested a password reset for your {{ platform_name }} account.\n\nIf you did not make this request, please ignore this email.\n\nBest regards,\n{{ platform_name }} Team'
            ),
            'device_alert': EmailTemplate(
                name='device_alert',
                subject_template='Device Alert: {{ device_name }}',
                html_template='<h2>Device Alert</h2><p><strong>Device:</strong> {{ device_name }}</p><p><strong>Alert:</strong> {{ alert_message }}</p><p><strong>Severity:</strong> {{ severity }}</p><p><strong>Time:</strong> {{ timestamp }}</p><p>Please check your device immediately.</p>',
                text_template='Device Alert\n\nDevice: {{ device_name }}\nAlert: {{ alert_message }}\nSeverity: {{ severity }}\nTime: {{ timestamp }}\n\nPlease check your device immediately.'
            )
        }
        
        return templates.get(template_name)
    
    @BaseService.timing_decorator  
    async def process_email_queue(self, batch_size: Optional[int] = None) -> List[EmailDeliveryResult]:
        """
        Process queued emails
        
        Args:
            batch_size: Number of emails to process (default from config)
            
        Returns:
            List of delivery results
        """
        if not self.redis:
            self.logger.warning("Redis not available, cannot process email queue")
            return []
        
        batch_size = batch_size or self.queue_config['processing_batch_size']
        results = []
        
        try:
            # Get batch of queued emails
            queue_items = []
            for _ in range(batch_size):
                item_data = await self.redis.rpop(self.queue_config['name'])
                if not item_data:
                    break
                queue_items.append(json.loads(item_data))
            
            # Process each email
            for item in queue_items:
                try:
                    # Reconstruct email message
                    msg_data = item['email_msg']
                    email_msg = EmailMessage(
                        to_addresses=msg_data['to_addresses'],
                        subject=msg_data['subject'],
                        html_body=msg_data.get('html_body'),
                        text_body=msg_data.get('text_body'),
                        from_address=msg_data.get('from_address'),
                        from_name=msg_data.get('from_name'),
                        reply_to=msg_data.get('reply_to'),
                        cc_addresses=msg_data.get('cc_addresses', []),
                        bcc_addresses=msg_data.get('bcc_addresses', []),
                        priority=EmailPriority(msg_data.get('priority', 'normal')),
                        tracking_id=item['tracking_id'],
                        metadata=msg_data.get('metadata', {})
                    )
                    
                    # Try to send
                    result = await self._send_email_smtp(email_msg)
                    
                    # Handle retry logic
                    if result.status == EmailStatus.FAILED and item['retry_count'] < self.retry_config['max_attempts']:
                        # Calculate delay for retry
                        retry_delay = min(
                            self.retry_config['base_delay'] * (
                                self.retry_config['backoff_multiplier'] ** item['retry_count']
                            ),
                            self.retry_config['max_delay']
                        )
                        
                        # Re-queue with delay
                        item['retry_count'] += 1
                        item['scheduled_for'] = (
                            datetime.utcnow() + timedelta(seconds=retry_delay)
                        ).isoformat()
                        
                        await self.redis.lpush(self.queue_config['name'], json.dumps(item))
                        
                        result.status = EmailStatus.RETRY
                        result.retry_count = item['retry_count']
                    
                    results.append(result)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process queued email {item.get('tracking_id')}: {e}")
                    results.append(EmailDeliveryResult(
                        message_id=item.get('tracking_id', 'unknown'),
                        status=EmailStatus.FAILED,
                        error_message=str(e)
                    ))
            
            if results:
                self.logger.info(f"Processed {len(results)} emails from queue")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to process email queue: {e}")
            return []
    
    async def get_delivery_status(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """
        Get email delivery status by tracking ID
        
        Args:
            tracking_id: Email tracking ID
            
        Returns:
            Delivery status information or None
        """
        if not self.redis:
            return None
        
        try:
            audit_key = f"email:audit:{tracking_id}"
            status_data = await self.redis.get(audit_key)
            
            if status_data:
                return json.loads(status_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get delivery status for {tracking_id}: {e}")
            return None
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get email queue status information
        
        Returns:
            Queue status information
        """
        if not self.redis:
            return {
                'queue_size': 0, 
                'redis_available': False,
                'service_enabled': self.config['enabled'],
                'smtp_host': self.config['host']
            }
        
        try:
            queue_size = await self.redis.llen(self.queue_config['name'])
            
            return {
                'queue_size': queue_size,
                'max_queue_size': self.queue_config['max_queue_size'],
                'processing_batch_size': self.queue_config['processing_batch_size'],
                'redis_available': True,
                'service_enabled': self.config['enabled'],
                'smtp_host': self.config['host'],
                'rate_limits': self.rate_limits
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get queue status: {e}")
            return {'error': str(e), 'redis_available': False}
    
    # Convenience methods for common email types
    
    async def send_otp_email(
        self, 
        to_address: str, 
        otp_code: str, 
        expiry_minutes: int = 15
    ) -> EmailDeliveryResult:
        """Send OTP verification email"""
        return await self.send_templated_email(
            to_addresses=[to_address],
            template_name='otp',
            template_data={
                'otp_code': otp_code,
                'expiry_minutes': expiry_minutes,
                'platform_name': self.config['from_name']
            },
            priority=EmailPriority.HIGH
        )
    
    async def send_welcome_email(
        self, 
        to_address: str, 
        user_name: str
    ) -> EmailDeliveryResult:
        """Send welcome email to new user"""
        return await self.send_templated_email(
            to_addresses=[to_address],
            template_name='welcome',
            template_data={
                'user_name': user_name,
                'platform_name': self.config['from_name']
            }
        )
    
    async def send_device_alert_email(
        self,
        to_address: str,
        device_name: str,
        alert_message: str,
        severity: str = 'medium'
    ) -> EmailDeliveryResult:
        """Send device alert email"""
        priority = EmailPriority.HIGH if severity in ['high', 'critical'] else EmailPriority.NORMAL
        
        return await self.send_templated_email(
            to_addresses=[to_address],
            template_name='device_alert',
            template_data={
                'device_name': device_name,
                'alert_message': alert_message,
                'severity': severity,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            },
            priority=priority
        )
    
    def send_email_sync(self, to_email: str, subject: str, template_name: str, template_data: dict) -> dict:
        """
        Synchronous wrapper for send_email to be used from non-async contexts.
        Simply calls the async send_email method directly and waits for the result.
        """
        import nest_asyncio
        
        # Allow nested event loops (for cases where Flask is already running in a loop)
        nest_asyncio.apply()
        
        async def _send():
            result = await self.send_email(
                to_addresses=to_email,
                subject=subject,
                template_name=template_name,
                template_data=template_data
            )
            return result
        
        # Run the async function and get the result
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_send())
            loop.close()
            return result
        except Exception as e:
            self.logger.error(f"Error in send_email_sync: {str(e)}")
            return {'success': False, 'error': str(e)}