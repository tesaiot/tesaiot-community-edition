# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Self-Service Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: certificate_self_service.py
Purpose: Self-service certificate management API endpoints
Version: v2025.07-production
Build Date: 2025-07-19
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

from flask import Blueprint, request, jsonify, g
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from ..core.auth import require_auth
from ..core.database import get_db
from ..core.rbac import Permission, require_permission
from ..services.audit_service import audit_log, AuditAction
from ..services.certificate_service import (
    issue_device_certificate
)
from ..services.certificate_monitoring_service import certificate_monitoring_service
from ..services.notification_service import send_email_notification

logger = logging.getLogger(__name__)

# Create Blueprint
cert_self_service_bp = Blueprint('certificate_self_service', __name__, url_prefix='/api/v1/certificates/self-service')

@cert_self_service_bp.route('/my-certificates', methods=['GET'])
@require_auth
def get_my_certificates():
    """
    Get certificates for current user's devices
    
    Query Parameters:
        status: Filter by status (valid, expiring, expired, revoked)
        days_ahead: Filter by days until expiry (default: 90)
        include_revoked: Include revoked certificates (default: false)
        
    Returns:
        JSON response with user's certificates and their status
    """
    try:
        db = get_db()
        
        # Get query parameters
        status_filter = request.args.get('status')
        days_ahead = int(request.args.get('days_ahead', 90))
        include_revoked = request.args.get('include_revoked', 'false').lower() == 'true'
        
        # Build query for user's devices
        device_query = {'created_by': g.current_user['email']}
        
        # Add organization filter for non-super admins
        if g.current_user.get('role') != 'super_admin':
            device_query['organization_id'] = g.current_user.get('organization_id')
        
        # Find user's devices with certificates
        devices = db.devices.find({
            **device_query,
            'certificate_serial': {'$exists': True, '$ne': None}
        })
        
        user_certificates = []
        
        for device in devices:
            cert_status = certificate_monitoring_service._get_certificate_status(device)
            
            if not cert_status:
                continue
            
            # Apply filters
            if not include_revoked and cert_status['status'] == 'revoked':
                continue
            
            if status_filter:
                if status_filter == 'expiring' and cert_status['urgency'] not in ['warning', 'urgent', 'critical']:
                    continue
                elif status_filter == 'expired' and cert_status['status'] != 'expired':
                    continue
                elif status_filter == 'valid' and cert_status['status'] != 'valid':
                    continue
                elif status_filter == 'revoked' and cert_status['status'] != 'revoked':
                    continue
            
            # Filter by days ahead
            if cert_status.get('days_until_expiry') is not None:
                if cert_status['days_until_expiry'] > days_ahead:
                    continue
            
            # Add renewal recommendation
            cert_status['renewal_recommended'] = _should_recommend_renewal(cert_status)
            cert_status['can_self_renew'] = _can_self_renew(device, g.current_user)
            cert_status['renewal_methods'] = _get_available_renewal_methods(device, g.current_user)
            
            user_certificates.append(cert_status)
        
        # Sort by urgency and days until expiry
        user_certificates.sort(key=lambda x: (
            {'critical': 0, 'urgent': 1, 'warning': 2, 'normal': 3}.get(x.get('urgency', 'normal'), 3),
            x.get('days_until_expiry', float('inf'))
        ))
        
        # Generate summary statistics
        summary = {
            'total_certificates': len(user_certificates),
            'valid': len([c for c in user_certificates if c['status'] == 'valid']),
            'expiring_soon': len([c for c in user_certificates if c['urgency'] in ['warning', 'urgent', 'critical']]),
            'expired': len([c for c in user_certificates if c['status'] == 'expired']),
            'revoked': len([c for c in user_certificates if c['status'] == 'revoked']),
            'renewal_recommended': len([c for c in user_certificates if c.get('renewal_recommended')])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'certificates': user_certificates,
                'summary': summary,
                'last_updated': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user certificates: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve certificates'
        }), 500

@cert_self_service_bp.route('/renew/<device_id>', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def renew_certificate(device_id):
    """
    Self-service certificate renewal for user's devices
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "renewal_method": "automatic|csr",
            "validity_days": 365,
            "key_algorithm": "RSA-2048|ECC-P256",
            "csr_content": "PEM-encoded CSR" // Required if renewal_method = "csr"
        }
    
    Returns:
        JSON response with renewal status and new certificate info
    """
    try:
        db = get_db()
        data = request.get_json() or {}
        
        # Verify device ownership
        device = db.devices.find_one({
            'device_id': device_id,
            'created_by': g.current_user['email']
        })
        
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found or access denied'
            }), 404
        
        # Check if user can renew this certificate
        if not _can_self_renew(device, g.current_user):
            return jsonify({
                'success': False,
                'error': 'Certificate renewal not allowed for this device'
            }), 403
        
        # Validate renewal parameters
        renewal_method = data.get('renewal_method', 'automatic')
        validity_days = data.get('validity_days', 365)
        key_algorithm = data.get('key_algorithm', 'RSA-2048')
        
        if renewal_method not in ['automatic', 'csr']:
            return jsonify({
                'success': False,
                'error': 'Invalid renewal method. Must be "automatic" or "csr"'
            }), 400
        
        if not (30 <= validity_days <= 1095):  # 30 days to 3 years
            return jsonify({
                'success': False,
                'error': 'Invalid validity period. Must be between 30 and 1095 days'
            }), 400
        
        if key_algorithm not in ['RSA-2048', 'RSA-3072', 'RSA-4096', 'ECC-P256', 'ECC-P384']:
            return jsonify({
                'success': False,
                'error': 'Invalid key algorithm'
            }), 400
        
        # Check renewal eligibility
        eligibility = _check_renewal_eligibility(device)
        if not eligibility['eligible']:
            return jsonify({
                'success': False,
                'error': eligibility['reason']
            }), 400
        
        # Perform renewal based on method
        if renewal_method == 'automatic':
            result = _perform_automatic_renewal(device, validity_days, key_algorithm, g.current_user)
        else:  # CSR method
            csr_content = data.get('csr_content')
            if not csr_content:
                return jsonify({
                    'success': False,
                    'error': 'CSR content is required for CSR renewal method'
                }), 400
            
            result = _perform_csr_renewal(device, csr_content, validity_days, g.current_user)
        
        if result['success']:
            # Log audit event
            audit_log(
                action=AuditAction.CERTIFICATE_SELF_RENEWAL,
                user=g.current_user,
                resource_type='certificate',
                resource_id=device_id,
                details={
                    'renewal_method': renewal_method,
                    'validity_days': validity_days,
                    'key_algorithm': key_algorithm,
                    'old_certificate_serial': device.get('certificate_serial'),
                    'new_certificate_serial': result.get('certificate_serial')
                }
            )
            
            # Send success notification
            _send_renewal_notification(device, result, g.current_user)
            
            return jsonify({
                'success': True,
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Certificate renewal failed')
            }), 500
        
    except Exception as e:
        logger.error(f"Error renewing certificate for {device_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Certificate renewal failed'
        }), 500

@cert_self_service_bp.route('/renewal-status/<device_id>', methods=['GET'])
@require_auth
def get_renewal_status(device_id):
    """
    Get certificate renewal status and history for a device
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response with renewal status and history
    """
    try:
        db = get_db()
        
        # Verify device ownership
        device = db.devices.find_one({
            'device_id': device_id,
            'created_by': g.current_user['email']
        })
        
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found or access denied'
            }), 404
        
        # Get current certificate status
        cert_status = certificate_monitoring_service._get_certificate_status(device)
        
        # Get renewal history
        renewal_history = list(db.certificate_renewal_history.find({
            'device_id': device_id
        }).sort('renewal_date', -1).limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for renewal in renewal_history:
            renewal['_id'] = str(renewal['_id'])
        
        # Check renewal eligibility
        eligibility = _check_renewal_eligibility(device)
        
        # Get available renewal methods
        renewal_methods = _get_available_renewal_methods(device, g.current_user)
        
        return jsonify({
            'success': True,
            'data': {
                'device_id': device_id,
                'current_certificate': cert_status,
                'renewal_eligibility': eligibility,
                'available_methods': renewal_methods,
                'renewal_history': renewal_history,
                'can_self_renew': _can_self_renew(device, g.current_user)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting renewal status for {device_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get renewal status'
        }), 500

@cert_self_service_bp.route('/batch-renew', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def batch_renew_certificates():
    """
    Batch renewal of multiple certificates for user's devices
    
    Request JSON:
        {
            "device_ids": ["device1", "device2", ...],
            "renewal_options": {
                "validity_days": 365,
                "key_algorithm": "RSA-2048",
                "renewal_method": "automatic"
            },
            "notify_on_completion": true
        }
    
    Returns:
        JSON response with batch renewal job status
    """
    try:
        db = get_db()
        data = request.get_json()
        
        if not data or 'device_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'Device IDs are required'
            }), 400
        
        device_ids = data['device_ids']
        renewal_options = data.get('renewal_options', {})
        notify_on_completion = data.get('notify_on_completion', True)
        
        if not isinstance(device_ids, list) or len(device_ids) == 0:
            return jsonify({
                'success': False,
                'error': 'Device IDs must be a non-empty list'
            }), 400
        
        if len(device_ids) > 50:  # Limit batch size
            return jsonify({
                'success': False,
                'error': 'Maximum 50 devices allowed per batch'
            }), 400
        
        # Verify all devices belong to user
        devices = list(db.devices.find({
            'device_id': {'$in': device_ids},
            'created_by': g.current_user['email']
        }))
        
        if len(devices) != len(device_ids):
            found_ids = [d['device_id'] for d in devices]
            missing_ids = [did for did in device_ids if did not in found_ids]
            return jsonify({
                'success': False,
                'error': f'Devices not found or access denied: {missing_ids}'
            }), 404
        
        # Create batch renewal job
        job_id = f"batch_renewal_{int(datetime.now().timestamp())}_{g.current_user['email'].replace('@', '_')}"
        
        batch_job = {
            'job_id': job_id,
            'type': 'batch_certificate_renewal',
            'created_by': g.current_user['email'],
            'organization_id': g.current_user.get('organization_id'),
            'device_ids': device_ids,
            'renewal_options': renewal_options,
            'notify_on_completion': notify_on_completion,
            'status': 'queued',
            'created_at': datetime.now(),
            'progress': {
                'total': len(device_ids),
                'completed': 0,
                'failed': 0,
                'results': []
            }
        }
        
        db.certificate_batch_renewal_jobs.insert_one(batch_job)
        
        # Queue job for processing (implement async processing)
        _queue_batch_renewal_job(job_id)
        
        # Log audit event
        audit_log(
            action=AuditAction.CERTIFICATE_BATCH_RENEWAL,
            user=g.current_user,
            resource_type='certificate',
            resource_id=job_id,
            details={
                'device_count': len(device_ids),
                'renewal_options': renewal_options
            }
        )
        
        return jsonify({
            'success': True,
            'data': {
                'job_id': job_id,
                'status': 'queued',
                'device_count': len(device_ids),
                'estimated_completion': (datetime.now() + timedelta(minutes=len(device_ids) * 2)).isoformat()
            }
        }), 202
        
    except Exception as e:
        logger.error(f"Error creating batch renewal job: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create batch renewal job'
        }), 500

@cert_self_service_bp.route('/batch-jobs/<job_id>', methods=['GET'])
@require_auth
def get_batch_job_status(job_id):
    """
    Get status of a batch renewal job
    
    Args:
        job_id: Batch job identifier
        
    Returns:
        JSON response with job status and progress
    """
    try:
        db = get_db()
        
        # Find job
        job = db.certificate_batch_renewal_jobs.find_one({
            'job_id': job_id,
            'created_by': g.current_user['email']
        })
        
        if not job:
            return jsonify({
                'success': False,
                'error': 'Batch job not found or access denied'
            }), 404
        
        # Convert ObjectId to string
        job['_id'] = str(job['_id'])
        
        return jsonify({
            'success': True,
            'data': job
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting batch job status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get job status'
        }), 500

@cert_self_service_bp.route('/alerts', methods=['GET'])
@require_auth
def get_my_certificate_alerts():
    """
    Get certificate alerts for current user's devices
    
    Query Parameters:
        severity: Filter by severity (warning, urgent, critical)
        limit: Maximum number of alerts (default: 20)
        acknowledged: Filter by acknowledged status (true/false)
        
    Returns:
        JSON response with user's certificate alerts
    """
    try:
        db = get_db()
        
        # Get query parameters
        severity_filter = request.args.get('severity')
        limit = int(request.args.get('limit', 20))
        acknowledged_filter = request.args.get('acknowledged')
        
        # Get user's devices
        user_devices = list(db.devices.find({
            'created_by': g.current_user['email']
        }, {'device_id': 1}))
        
        device_ids = [d['device_id'] for d in user_devices]
        
        # Build alert query
        alert_query = {
            'device_id': {'$in': device_ids},
            'status': 'active'
        }
        
        if severity_filter:
            alert_query['severity'] = severity_filter
        
        if acknowledged_filter is not None:
            alert_query['acknowledged'] = acknowledged_filter.lower() == 'true'
        
        # Get alerts
        alerts = list(db.certificate_alerts.find(alert_query)
                     .sort('created_at', -1)
                     .limit(limit))
        
        # Convert ObjectId to string
        for alert in alerts:
            alert['_id'] = str(alert['_id'])
        
        return jsonify({
            'success': True,
            'data': {
                'alerts': alerts,
                'total': len(alerts)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user certificate alerts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve alerts'
        }), 500

@cert_self_service_bp.route('/alerts/<alert_id>/acknowledge', methods=['POST'])
@require_auth
def acknowledge_alert(alert_id):
    """
    Acknowledge a certificate alert
    
    Args:
        alert_id: Alert identifier
        
    Returns:
        JSON response with acknowledgment status
    """
    try:
        db = get_db()
        
        # Find alert and verify ownership
        alert = db.certificate_alerts.find_one({'alert_id': alert_id})
        
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        # Verify device ownership
        device = db.devices.find_one({
            'device_id': alert['device_id'],
            'created_by': g.current_user['email']
        })
        
        if not device:
            return jsonify({
                'success': False,
                'error': 'Access denied'
            }), 403
        
        # Acknowledge alert
        db.certificate_alerts.update_one(
            {'alert_id': alert_id},
            {
                '$set': {
                    'acknowledged': True,
                    'acknowledged_by': g.current_user['email'],
                    'acknowledged_at': datetime.now()
                }
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Alert acknowledged successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to acknowledge alert'
        }), 500

# Helper functions

def _should_recommend_renewal(cert_status: Dict) -> bool:
    """Check if renewal should be recommended"""
    days_until_expiry = cert_status.get('days_until_expiry')
    if days_until_expiry is None:
        return False
    
    return (days_until_expiry <= 30 and 
            cert_status['status'] not in ['expired', 'revoked'])

def _can_self_renew(device: Dict, user: Dict) -> bool:
    """Check if user can self-renew certificate for device"""
    # User must own the device
    if device.get('created_by') != user['email']:
        return False
    
    # Device must have a certificate
    if not device.get('certificate_serial'):
        return False
    
    # Check organization settings
    org_id = user.get('organization_id')
    if org_id:
        db = get_db()
        org = db.organizations.find_one({'_id': org_id})
        if org:
            cert_settings = org.get('certificate_settings', {})
            if not cert_settings.get('self_service_renewal_enabled', True):
                return False
    
    return True

def _get_available_renewal_methods(device: Dict, user: Dict) -> List[str]:
    """Get available renewal methods for device"""
    methods = []
    
    if _can_self_renew(device, user):
        methods.append('automatic')
        
        # Check if CSR method is allowed
        org_id = user.get('organization_id')
        if org_id:
            db = get_db()
            org = db.organizations.find_one({'_id': org_id})
            if org:
                cert_settings = org.get('certificate_settings', {})
                if cert_settings.get('csr_renewal_enabled', True):
                    methods.append('csr')
    
    return methods

def _check_renewal_eligibility(device: Dict) -> Dict:
    """Check if device is eligible for certificate renewal"""
    if not device.get('certificate_serial'):
        return {
            'eligible': False,
            'reason': 'No certificate found for device'
        }
    
    # Check if device is active
    if device.get('status') == 'inactive':
        return {
            'eligible': False,
            'reason': 'Device is inactive'
        }
    
    # Check if there's a recent renewal
    db = get_db()
    recent_renewal = db.certificate_renewal_history.find_one({
        'device_id': device['device_id'],
        'renewal_date': {'$gte': datetime.now() - timedelta(days=1)}
    })
    
    if recent_renewal:
        return {
            'eligible': False,
            'reason': 'Certificate was renewed recently. Please wait 24 hours between renewals'
        }
    
    return {
        'eligible': True,
        'reason': 'Device is eligible for certificate renewal'
    }

def _perform_automatic_renewal(device: Dict, validity_days: int, key_algorithm: str, user: Dict) -> Dict:
    """Perform automatic certificate renewal"""
    try:
        # Store old certificate info
        old_cert_serial = device.get('certificate_serial')
        
        # Issue new certificate
        result = issue_device_certificate(device['device_id'], user)
        
        if result and not result.get('error'):
            # Record renewal in history
            _record_renewal_history(device['device_id'], {
                'method': 'automatic',
                'old_certificate_serial': old_cert_serial,
                'new_certificate_serial': result.get('certificate_serial'),
                'validity_days': validity_days,
                'key_algorithm': key_algorithm,
                'renewed_by': user['email'],
                'renewal_date': datetime.now()
            })
            
            return {
                'success': True,
                'certificate_serial': result.get('certificate_serial'),
                'validity_days': validity_days,
                'expires_at': result.get('expires_at'),
                'renewal_method': 'automatic'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Certificate issuance failed')
            }
    
    except Exception as e:
        logger.error(f"Automatic renewal failed for {device['device_id']}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def _perform_csr_renewal(device: Dict, csr_content: str, validity_days: int, user: Dict) -> Dict:
    """Perform CSR-based certificate renewal"""
    try:
        from ..services.certificate_service import sign_device_csr
        
        # Store old certificate info
        old_cert_serial = device.get('certificate_serial')
        
        # Sign CSR
        result = sign_device_csr(
            device_id=device['device_id'],
            csr_content=csr_content,
            validity_days=validity_days,
            user=user
        )
        
        if result and not result.get('error'):
            # Record renewal in history
            _record_renewal_history(device['device_id'], {
                'method': 'csr',
                'old_certificate_serial': old_cert_serial,
                'new_certificate_serial': result.get('certificate_serial'),
                'validity_days': validity_days,
                'renewed_by': user['email'],
                'renewal_date': datetime.now(),
                'csr_used': True
            })
            
            return {
                'success': True,
                'certificate_serial': result.get('certificate_serial'),
                'certificate_pem': result.get('certificate_pem'),
                'validity_days': validity_days,
                'renewal_method': 'csr'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'CSR signing failed')
            }
    
    except Exception as e:
        logger.error(f"CSR renewal failed for {device['device_id']}: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def _record_renewal_history(device_id: str, renewal_data: Dict):
    """Record certificate renewal in history"""
    try:
        db = get_db()
        db.certificate_renewal_history.insert_one({
            'device_id': device_id,
            **renewal_data
        })
    except Exception as e:
        logger.error(f"Error recording renewal history: {e}")

def _send_renewal_notification(device: Dict, renewal_result: Dict, user: Dict):
    """Send certificate renewal notification"""
    try:
        if user.get('email'):
            subject = f"Certificate Renewed Successfully - {device['device_id']}"
            body = f"""
Your certificate for device '{device['device_id']}' has been renewed successfully.

Details:
- Device: {device['device_id']}
- New Certificate Serial: {renewal_result.get('certificate_serial')}
- Renewal Method: {renewal_result.get('renewal_method')}
- Valid Until: {renewal_result.get('expires_at', 'N/A')}
- Renewed At: {datetime.now().isoformat()}

Please update your device configuration with the new certificate.

TESA IoT Platform - Certificate Self-Service
"""
            
            send_email_notification(user['email'], subject, body)
    
    except Exception as e:
        logger.error(f"Error sending renewal notification: {e}")

def _queue_batch_renewal_job(job_id: str):
    """Queue batch renewal job for background processing"""
    # This would integrate with your task queue system (Celery, RQ, etc.)
    # For now, log that the job is queued
    logger.info(f"Batch renewal job {job_id} queued for processing")
    
    # TODO: Implement actual job queuing
    # Example: celery_app.send_task('process_batch_renewal', args=[job_id])