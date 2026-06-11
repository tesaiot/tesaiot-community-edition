# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Certificate API Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: device_certificate_api.py
Purpose: Device-side API endpoints for certificate status and management
Version: v2025.07-production
Build Date: 2025-07-19
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..core.auth import require_auth
from ..core.database import get_db
from ..services.certificate_monitoring_service import certificate_monitoring_service
from ..services.audit_service import audit_log, AuditAction

logger = logging.getLogger(__name__)

# Create Blueprint
device_cert_api_bp = Blueprint('device_certificate_api', __name__, url_prefix='/api/v1/device')

@device_cert_api_bp.route('/<device_id>/certificate/status', methods=['GET'])
@require_auth
def get_device_certificate_status(device_id):
    """
    Get certificate status for a specific device (device-side API)
    
    This endpoint is designed for IoT devices to check their own certificate status
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        include_chain: Include certificate chain info (true/false, default: false)
        check_revocation: Check revocation status (true/false, default: true)
        
    Returns:
        JSON response with certificate status optimized for device consumption
    """
    try:
        db = get_db()
        
        # Get query parameters
        include_chain = request.args.get('include_chain', 'false').lower() == 'true'
        check_revocation = request.args.get('check_revocation', 'true').lower() == 'true'
        
        # Find device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'status': 'error',
                'error': 'DEVICE_NOT_FOUND',
                'message': 'Device not found'
            }), 404
        
        # Get certificate status
        cert_status = certificate_monitoring_service._get_certificate_status(device)
        
        if not cert_status:
            return jsonify({
                'status': 'no_certificate',
                'device_id': device_id,
                'message': 'No certificate found for this device',
                'timestamp': datetime.now().isoformat(),
                'next_check_recommended': (datetime.now() + timedelta(hours=24)).isoformat()
            }), 200
        
        # Build device-optimized response
        response_data = {
            'status': 'ok',
            'device_id': device_id,
            'certificate': {
                'serial': cert_status['certificate_serial'],
                'status': cert_status['status'],
                'urgency': cert_status['urgency'],
                'algorithm': cert_status.get('algorithm'),
                'expires_at': cert_status.get('expiry_date'),
                'days_until_expiry': cert_status.get('days_until_expiry'),
                'is_valid': cert_status['status'] == 'valid',
                'needs_renewal': _device_needs_renewal(cert_status),
                'renewal_recommended_by': _get_renewal_recommendation_date(cert_status)
            },
            'timestamp': datetime.now().isoformat(),
            'next_check_recommended': _get_next_check_time(cert_status).isoformat()
        }
        
        # Add certificate chain info if requested
        if include_chain:
            chain_info = _get_certificate_chain_info(device)
            if chain_info:
                response_data['certificate']['chain'] = chain_info
        
        # Add revocation status if requested
        if check_revocation:
            revocation_status = _check_revocation_status(device)
            response_data['certificate']['revocation'] = revocation_status
        
        # Add renewal instructions if needed
        if response_data['certificate']['needs_renewal']:
            response_data['renewal'] = _get_device_renewal_instructions(device)
        
        # Add alerts if any
        alerts = _get_device_alerts(device_id)
        if alerts:
            response_data['alerts'] = alerts
        
        # Log device status check
        audit_log(
            action=AuditAction.DEVICE_CERTIFICATE_STATUS_CHECK,
            user={'device_id': device_id, 'type': 'device'},
            resource_type='certificate',
            resource_id=device_id,
            details={
                'certificate_status': cert_status['status'],
                'days_until_expiry': cert_status.get('days_until_expiry'),
                'include_chain': include_chain,
                'check_revocation': check_revocation
            }
        )
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate status for device {device_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'STATUS_CHECK_FAILED',
            'message': 'Failed to check certificate status',
            'timestamp': datetime.now().isoformat()
        }), 500

@device_cert_api_bp.route('/<device_id>/certificate/health', methods=['GET'])
@require_auth
def get_device_certificate_health(device_id):
    """
    Get detailed certificate health information for device
    
    Args:
        device_id: Device identifier
        
    Returns:
        JSON response with detailed health metrics
    """
    try:
        db = get_db()
        
        # Find device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'status': 'error',
                'error': 'DEVICE_NOT_FOUND'
            }), 404
        
        # Get certificate status
        cert_status = certificate_monitoring_service._get_certificate_status(device)
        
        if not cert_status:
            return jsonify({
                'status': 'no_certificate',
                'health_score': 0,
                'issues': ['No certificate configured']
            }), 200
        
        # Calculate health score and issues
        health_score, issues, recommendations = _calculate_device_health_score(cert_status, device)
        
        # Get certificate history
        cert_history = _get_device_certificate_history(device_id)
        
        response_data = {
            'status': 'ok',
            'device_id': device_id,
            'health': {
                'score': health_score,
                'grade': _get_health_grade(health_score),
                'issues': issues,
                'recommendations': recommendations
            },
            'certificate': {
                'serial': cert_status['certificate_serial'],
                'status': cert_status['status'],
                'algorithm': cert_status.get('algorithm'),
                'expires_at': cert_status.get('expiry_date'),
                'days_until_expiry': cert_status.get('days_until_expiry'),
                'created_at': cert_status.get('certificate_created')
            },
            'history': cert_history,
            'last_renewal': _get_last_renewal_info(device_id),
            'compliance': _check_device_compliance(cert_status),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate health for device {device_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'HEALTH_CHECK_FAILED'
        }), 500

@device_cert_api_bp.route('/<device_id>/certificate/renew-request', methods=['POST'])
@require_auth
def request_certificate_renewal(device_id):
    """
    Request certificate renewal from device
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "reason": "expiring|expired|compromised|upgrade",
            "urgency": "low|medium|high|critical",
            "csr": "Optional PEM-encoded CSR",
            "device_info": {
                "firmware_version": "1.2.3",
                "hardware_revision": "A1",
                "location": "Building A, Floor 2"
            }
        }
    
    Returns:
        JSON response with renewal request status
    """
    try:
        db = get_db()
        data = request.get_json() or {}
        
        # Find device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'status': 'error',
                'error': 'DEVICE_NOT_FOUND'
            }), 404
        
        # Validate request
        reason = data.get('reason', 'expiring')
        urgency = data.get('urgency', 'medium')
        csr = data.get('csr')
        device_info = data.get('device_info', {})
        
        if reason not in ['expiring', 'expired', 'compromised', 'upgrade']:
            return jsonify({
                'status': 'error',
                'error': 'INVALID_REASON'
            }), 400
        
        if urgency not in ['low', 'medium', 'high', 'critical']:
            return jsonify({
                'status': 'error',
                'error': 'INVALID_URGENCY'
            }), 400
        
        # Check if device can request renewal
        eligibility = _check_device_renewal_eligibility(device)
        if not eligibility['eligible']:
            return jsonify({
                'status': 'error',
                'error': 'RENEWAL_NOT_ALLOWED',
                'message': eligibility['reason']
            }), 403
        
        # Create renewal request
        request_id = f"dev_renewal_{int(datetime.now().timestamp())}_{device_id}"
        
        renewal_request = {
            'request_id': request_id,
            'device_id': device_id,
            'reason': reason,
            'urgency': urgency,
            'requested_by': 'device',
            'requested_at': datetime.now(),
            'status': 'pending',
            'csr_provided': csr is not None,
            'device_info': device_info,
            'organization_id': device.get('organization_id')
        }
        
        # Store CSR if provided
        if csr:
            renewal_request['csr'] = csr
        
        # Store renewal request
        db.device_certificate_renewal_requests.insert_one(renewal_request)
        
        # Create alert for administrators
        _create_device_renewal_alert(device, renewal_request)
        
        # Log audit event
        audit_log(
            action=AuditAction.DEVICE_CERTIFICATE_RENEWAL_REQUEST,
            user={'device_id': device_id, 'type': 'device'},
            resource_type='certificate',
            resource_id=device_id,
            details={
                'request_id': request_id,
                'reason': reason,
                'urgency': urgency,
                'csr_provided': csr is not None
            }
        )
        
        # Determine processing timeline
        processing_timeline = _get_renewal_processing_timeline(urgency)
        
        response_data = {
            'status': 'ok',
            'request_id': request_id,
            'message': 'Certificate renewal request submitted successfully',
            'processing': {
                'status': 'pending',
                'expected_processing_time': processing_timeline,
                'next_status_check': (datetime.now() + timedelta(hours=1)).isoformat()
            },
            'instructions': _get_device_renewal_wait_instructions(urgency),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response_data), 202
        
    except Exception as e:
        logger.error(f"Error processing renewal request for device {device_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'RENEWAL_REQUEST_FAILED'
        }), 500

@device_cert_api_bp.route('/<device_id>/certificate/renewal-status/<request_id>', methods=['GET'])
@require_auth
def get_renewal_request_status(device_id, request_id):
    """
    Get status of a certificate renewal request
    
    Args:
        device_id: Device identifier
        request_id: Renewal request identifier
        
    Returns:
        JSON response with renewal request status
    """
    try:
        db = get_db()
        
        # Find renewal request
        renewal_request = db.device_certificate_renewal_requests.find_one({
            'request_id': request_id,
            'device_id': device_id
        })
        
        if not renewal_request:
            return jsonify({
                'status': 'error',
                'error': 'REQUEST_NOT_FOUND'
            }), 404
        
        # Convert ObjectId to string
        renewal_request['_id'] = str(renewal_request['_id'])
        
        # Add additional status information
        status_info = {
            'request': renewal_request,
            'device_id': device_id,
            'current_time': datetime.now().isoformat()
        }
        
        # Add certificate download info if completed
        if renewal_request['status'] == 'completed':
            download_info = _get_certificate_download_info(device_id, request_id)
            if download_info:
                status_info['download'] = download_info
        
        # Add estimated completion time if pending
        elif renewal_request['status'] == 'pending':
            estimated_completion = _estimate_renewal_completion(renewal_request)
            status_info['estimated_completion'] = estimated_completion
        
        return jsonify({
            'status': 'ok',
            'data': status_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting renewal status for {request_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'STATUS_CHECK_FAILED'
        }), 500

@device_cert_api_bp.route('/<device_id>/certificate/alerts', methods=['GET'])
@require_auth
def get_device_certificate_alerts(device_id):
    """
    Get certificate alerts for a specific device
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        severity: Filter by severity (warning, urgent, critical)
        limit: Maximum number of alerts (default: 10)
        
    Returns:
        JSON response with device certificate alerts
    """
    try:
        # Get query parameters
        severity_filter = request.args.get('severity')
        limit = int(request.args.get('limit', 10))
        
        alerts = _get_device_alerts(device_id, severity_filter, limit)
        
        return jsonify({
            'status': 'ok',
            'device_id': device_id,
            'alerts': alerts,
            'alert_count': len(alerts),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting alerts for device {device_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'ALERTS_FETCH_FAILED'
        }), 500

@device_cert_api_bp.route('/<device_id>/certificate/download', methods=['GET'])
@require_auth
def download_device_certificate(device_id):
    """
    Download current certificate for device
    
    Args:
        device_id: Device identifier
        
    Query Parameters:
        format: Response format (pem, der, json) - default: pem
        include_chain: Include CA chain (true/false) - default: true
        
    Returns:
        Certificate file or JSON response
    """
    try:
        db = get_db()
        
        # Get query parameters
        format_type = request.args.get('format', 'pem').lower()
        include_chain = request.args.get('include_chain', 'true').lower() == 'true'
        
        if format_type not in ['pem', 'der', 'json']:
            return jsonify({
                'status': 'error',
                'error': 'INVALID_FORMAT'
            }), 400
        
        # Find device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'status': 'error',
                'error': 'DEVICE_NOT_FOUND'
            }), 404
        
        if not device.get('certificate_serial'):
            return jsonify({
                'status': 'error',
                'error': 'NO_CERTIFICATE'
            }), 404
        
        # Get certificate data (this would integrate with your certificate storage)
        cert_data = _get_device_certificate_data(device, format_type, include_chain)
        
        if not cert_data:
            return jsonify({
                'status': 'error',
                'error': 'CERTIFICATE_UNAVAILABLE'
            }), 404
        
        # Log download
        audit_log(
            action=AuditAction.DEVICE_CERTIFICATE_DOWNLOAD,
            user={'device_id': device_id, 'type': 'device'},
            resource_type='certificate',
            resource_id=device_id,
            details={
                'format': format_type,
                'include_chain': include_chain
            }
        )
        
        if format_type == 'json':
            return jsonify({
                'status': 'ok',
                'device_id': device_id,
                'certificate': cert_data,
                'downloaded_at': datetime.now().isoformat()
            }), 200
        else:
            # Return binary certificate data
            from flask import Response
            
            mimetype = 'application/x-pem-file' if format_type == 'pem' else 'application/x-x509-ca-cert'
            filename = f"{device_id}.{format_type}"
            
            response = Response(
                cert_data,
                mimetype=mimetype,
                headers={
                    'Content-Disposition': f'attachment; filename={filename}',
                    'Content-Type': mimetype
                }
            )
            return response
        
    except Exception as e:
        logger.error(f"Error downloading certificate for device {device_id}: {e}")
        return jsonify({
            'status': 'error',
            'error': 'DOWNLOAD_FAILED'
        }), 500

# Helper functions

def _device_needs_renewal(cert_status: Dict) -> bool:
    """Check if device needs certificate renewal"""
    days_until_expiry = cert_status.get('days_until_expiry')
    
    if cert_status['status'] in ['expired', 'revoked']:
        return True
    
    if days_until_expiry is not None and days_until_expiry <= 30:
        return True
    
    return False

def _get_renewal_recommendation_date(cert_status: Dict) -> Optional[str]:
    """Get recommended renewal date"""
    days_until_expiry = cert_status.get('days_until_expiry')
    
    if days_until_expiry is not None and days_until_expiry > 30:
        renewal_date = datetime.now() + timedelta(days=days_until_expiry - 30)
        return renewal_date.isoformat()
    
    return None

def _get_next_check_time(cert_status: Dict) -> datetime:
    """Get recommended next check time"""
    days_until_expiry = cert_status.get('days_until_expiry')
    
    if cert_status['status'] in ['expired', 'revoked']:
        return datetime.now() + timedelta(hours=1)  # Check hourly if expired/revoked
    elif days_until_expiry is not None:
        if days_until_expiry <= 7:
            return datetime.now() + timedelta(hours=6)  # Check every 6 hours if expires soon
        elif days_until_expiry <= 30:
            return datetime.now() + timedelta(hours=12)  # Check twice daily
        else:
            return datetime.now() + timedelta(days=1)  # Daily check
    else:
        return datetime.now() + timedelta(days=1)  # Default daily

def _get_certificate_chain_info(device: Dict) -> Optional[Dict]:
    """Get certificate chain information"""
    # This would integrate with your certificate storage system
    # Return basic chain info for now
    return {
        'root_ca': 'TESA IoT Root CA',
        'intermediate_ca': 'TESA IoT Intermediate CA',
        'chain_length': 3,
        'all_valid': True
    }

def _check_revocation_status(device: Dict) -> Dict:
    """Check certificate revocation status.

    Reflects the authoritative platform state: a certificate revoked via the
    API (Vault pki-int/revoke + CRL + MongoDB status='revoked') is reported as
    revoked here too, instead of always returning revoked=False. This keeps the
    device-facing status endpoint honest and fail-safe.
    """
    cert_status = str(device.get('certificate_status', '')).lower()
    is_revoked = cert_status == 'revoked'
    return {
        'checked': True,
        'revoked': is_revoked,
        'serial': device.get('certificate_serial'),
        'revoked_at': (
            device.get('certificate_revoked_at').isoformat()
            if is_revoked and hasattr(device.get('certificate_revoked_at'), 'isoformat')
            else (str(device.get('certificate_revoked_at')) if is_revoked else None)
        ),
        'reason': device.get('certificate_revoke_reason') if is_revoked else None,
        'check_time': datetime.now().isoformat(),
        'next_check': (datetime.now() + timedelta(hours=4)).isoformat()
    }

def _get_device_renewal_instructions(device: Dict) -> Dict:
    """Get renewal instructions for device"""
    return {
        'method': 'api_request',
        'endpoint': f'/api/v1/device/{device["device_id"]}/certificate/renew-request',
        'instructions': [
            'Submit renewal request via API',
            'Wait for administrator approval',
            'Download new certificate when ready',
            'Update device configuration'
        ],
        'estimated_time': '2-4 hours'
    }

def _get_device_alerts(device_id: str, severity_filter: str = None, limit: int = 10) -> List[Dict]:
    """Get certificate alerts for device"""
    try:
        db = get_db()
        
        query = {
            'device_id': device_id,
            'status': 'active'
        }
        
        if severity_filter:
            query['severity'] = severity_filter
        
        alerts = list(db.certificate_alerts.find(query)
                     .sort('created_at', -1)
                     .limit(limit))
        
        # Simplify alerts for device consumption
        device_alerts = []
        for alert in alerts:
            device_alerts.append({
                'id': alert['alert_id'],
                'severity': alert['severity'],
                'message': alert['message'],
                'created_at': alert['created_at'].isoformat(),
                'acknowledged': alert.get('acknowledged', False)
            })
        
        return device_alerts
    
    except Exception as e:
        logger.error(f"Error getting device alerts: {e}")
        return []

def _calculate_device_health_score(cert_status: Dict, device: Dict) -> tuple:
    """Calculate device certificate health score"""
    score = 100
    issues = []
    recommendations = []
    
    days_until_expiry = cert_status.get('days_until_expiry')
    
    # Check certificate status
    if cert_status['status'] == 'expired':
        score -= 50
        issues.append('Certificate has expired')
        recommendations.append('Renew certificate immediately')
    elif cert_status['status'] == 'revoked':
        score -= 60
        issues.append('Certificate has been revoked')
        recommendations.append('Request new certificate immediately')
    
    # Check expiry timeline
    if days_until_expiry is not None:
        if days_until_expiry <= 1:
            score -= 30
            issues.append('Certificate expires very soon')
            recommendations.append('Renew certificate urgently')
        elif days_until_expiry <= 7:
            score -= 20
            issues.append('Certificate expires soon')
            recommendations.append('Plan certificate renewal')
        elif days_until_expiry <= 30:
            score -= 10
            issues.append('Certificate expires within 30 days')
            recommendations.append('Schedule certificate renewal')
    
    # Check algorithm strength
    algorithm = cert_status.get('algorithm', '').upper()
    if 'RSA-1024' in algorithm:
        score -= 15
        issues.append('Weak key algorithm (RSA-1024)')
        recommendations.append('Upgrade to stronger algorithm (RSA-2048+ or ECC)')
    elif 'SHA1' in algorithm:
        score -= 10
        issues.append('Weak signature algorithm (SHA1)')
        recommendations.append('Upgrade to SHA256 or higher')
    
    # Ensure score doesn't go below 0
    score = max(0, score)
    
    return score, issues, recommendations

def _get_health_grade(score: int) -> str:
    """Convert health score to grade"""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

def _get_device_certificate_history(device_id: str) -> List[Dict]:
    """Get certificate history for device"""
    try:
        db = get_db()
        
        history = list(db.certificate_renewal_history.find({
            'device_id': device_id
        }).sort('renewal_date', -1).limit(5))
        
        # Simplify history for device consumption
        device_history = []
        for item in history:
            device_history.append({
                'renewal_date': item['renewal_date'].isoformat(),
                'method': item.get('method', 'unknown'),
                'certificate_serial': item.get('new_certificate_serial'),
                'validity_days': item.get('validity_days')
            })
        
        return device_history
    
    except Exception as e:
        logger.error(f"Error getting certificate history: {e}")
        return []

def _get_last_renewal_info(device_id: str) -> Optional[Dict]:
    """Get last renewal information"""
    try:
        db = get_db()
        
        last_renewal = db.certificate_renewal_history.find_one({
            'device_id': device_id
        }, sort=[('renewal_date', -1)])
        
        if last_renewal:
            return {
                'date': last_renewal['renewal_date'].isoformat(),
                'method': last_renewal.get('method', 'unknown'),
                'days_ago': (datetime.now() - last_renewal['renewal_date']).days
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error getting last renewal info: {e}")
        return None

def _check_device_compliance(cert_status: Dict) -> Dict:
    """Check device certificate compliance"""
    compliance = {
        'etsi_en_303_645': True,
        'iso_iec_27402': True,
        'issues': []
    }
    
    # Check algorithm compliance
    algorithm = cert_status.get('algorithm', '').upper()
    if 'RSA-1024' in algorithm or 'SHA1' in algorithm:
        compliance['etsi_en_303_645'] = False
        compliance['issues'].append('Weak cryptographic algorithm')
    
    # Check validity period
    days_until_expiry = cert_status.get('days_until_expiry')
    if days_until_expiry is not None and days_until_expiry < 0:
        compliance['etsi_en_303_645'] = False
        compliance['iso_iec_27402'] = False
        compliance['issues'].append('Expired certificate')
    
    return compliance

def _check_device_renewal_eligibility(device: Dict) -> Dict:
    """Check if device is eligible for renewal request"""
    # Check if device has certificate
    if not device.get('certificate_serial'):
        return {
            'eligible': False,
            'reason': 'No certificate found'
        }
    
    # Check if device is active
    if device.get('status') == 'inactive':
        return {
            'eligible': False,
            'reason': 'Device is inactive'
        }
    
    # Check for recent requests
    db = get_db()
    recent_request = db.device_certificate_renewal_requests.find_one({
        'device_id': device['device_id'],
        'requested_at': {'$gte': datetime.now() - timedelta(hours=24)},
        'status': {'$in': ['pending', 'processing']}
    })
    
    if recent_request:
        return {
            'eligible': False,
            'reason': 'Recent renewal request pending'
        }
    
    return {
        'eligible': True,
        'reason': 'Device is eligible for renewal'
    }

def _create_device_renewal_alert(device: Dict, renewal_request: Dict):
    """Create alert for device renewal request"""
    try:
        db = get_db()
        
        alert = {
            'alert_id': f"dev_renewal_alert_{renewal_request['request_id']}",
            'type': 'device_renewal_request',
            'severity': renewal_request['urgency'],
            'device_id': device['device_id'],
            'message': f"Device {device['device_id']} requested certificate renewal: {renewal_request['reason']}",
            'organization_id': device.get('organization_id'),
            'created_at': datetime.now(),
            'status': 'active',
            'acknowledged': False,
            'metadata': {
                'request_id': renewal_request['request_id'],
                'reason': renewal_request['reason'],
                'csr_provided': renewal_request['csr_provided']
            }
        }
        
        db.certificate_alerts.insert_one(alert)
    
    except Exception as e:
        logger.error(f"Error creating device renewal alert: {e}")

def _get_renewal_processing_timeline(urgency: str) -> str:
    """Get expected processing timeline based on urgency"""
    timelines = {
        'critical': '1-2 hours',
        'high': '2-6 hours',
        'medium': '6-24 hours',
        'low': '1-3 days'
    }
    return timelines.get(urgency, '6-24 hours')

def _get_device_renewal_wait_instructions(urgency: str) -> List[str]:
    """Get instructions for device while waiting for renewal"""
    if urgency in ['critical', 'high']:
        return [
            'Monitor certificate status frequently',
            'Prepare for service interruption if certificate expires',
            'Contact administrator if urgent',
            'Check renewal status every hour'
        ]
    else:
        return [
            'Continue normal operation',
            'Check renewal status periodically',
            'Certificate will be renewed automatically',
            'Update configuration when new certificate is ready'
        ]

def _estimate_renewal_completion(renewal_request: Dict) -> str:
    """Estimate renewal completion time"""
    requested_at = renewal_request['requested_at']
    urgency = renewal_request['urgency']
    
    processing_hours = {
        'critical': 2,
        'high': 6,
        'medium': 24,
        'low': 72
    }
    
    hours = processing_hours.get(urgency, 24)
    estimated_completion = requested_at + timedelta(hours=hours)
    
    return estimated_completion.isoformat()

def _get_certificate_download_info(device_id: str, request_id: str) -> Optional[Dict]:
    """Get certificate download information"""
    # This would provide secure download links/tokens
    return {
        'download_available': True,
        'download_methods': ['api', 'secure_link'],
        'api_endpoint': f'/api/v1/device/{device_id}/certificate/download',
        'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
    }

def _get_device_certificate_data(device: Dict, format_type: str, include_chain: bool) -> Optional[str]:
    """Get certificate data for device download"""
    # This would integrate with your certificate storage system
    # Return mock data for now
    if format_type == 'json':
        return {
            'certificate': 'PEM_CERTIFICATE_DATA',
            'private_key': 'PEM_PRIVATE_KEY_DATA',
            'ca_chain': ['INTERMEDIATE_CA', 'ROOT_CA'] if include_chain else []
        }
    else:
        return "-----BEGIN CERTIFICATE-----\nMOCK_CERTIFICATE_DATA\n-----END CERTIFICATE-----"