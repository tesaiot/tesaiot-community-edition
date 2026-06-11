# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Monitoring Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: certificate_monitoring.py
Purpose: API endpoints for certificate monitoring and health checks
Version: v2025.06-beta-1
Build Date: 2025-06-14
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

from flask import Blueprint, jsonify, request
import logging

from ..core.auth import require_auth
from ..services.certificate_monitoring_service import certificate_monitoring_service

logger = logging.getLogger(__name__)

# Create Blueprint
cert_monitoring_bp = Blueprint('certificate_monitoring', __name__, url_prefix='/api/v1/certificates')

@cert_monitoring_bp.route('/health', methods=['GET'])
@require_auth
def get_certificate_health():
    """
    Get certificate health overview
    
    Returns comprehensive certificate health statistics including:
    - Total certificates and their status
    - Expiry distribution
    - Algorithm distribution
    - Health score
    
    Returns:
        JSON response with certificate health data
    """
    try:
        # Get health overview
        health_data = certificate_monitoring_service.get_certificate_health_overview()
        
        return jsonify({
            'success': True,
            'data': health_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate health: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve certificate health data'
        }), 500

@cert_monitoring_bp.route('/expiring', methods=['GET'])
@require_auth
def get_expiring_certificates():
    """
    Get list of expiring certificates
    
    Query parameters:
    - days: Number of days to look ahead (default: 30)
    - limit: Maximum number of results (default: 100)
    
    Returns:
        JSON response with list of expiring certificates
    """
    try:
        # Get query parameters
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 100, type=int)
        
        # Get expiring certificates
        expiring_certs = certificate_monitoring_service.check_expiring_certificates()
        
        # Filter by days if specified
        if days:
            expiring_certs = [
                cert for cert in expiring_certs 
                if cert.get('days_until_expiry', float('inf')) <= days
            ]
        
        # Apply limit
        expiring_certs = expiring_certs[:limit]
        
        return jsonify({
            'success': True,
            'data': {
                'certificates': expiring_certs,
                'total': len(expiring_certs)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting expiring certificates: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve expiring certificates'
        }), 500

@cert_monitoring_bp.route('/alerts', methods=['GET'])
@require_auth
def get_certificate_alerts():
    """
    Get certificate alerts
    
    Query parameters:
    - severity: Filter by severity (warning, urgent, critical)
    - limit: Maximum number of results (default: 50)
    
    Returns:
        JSON response with certificate alerts
    """
    try:
        # Get query parameters
        severity = request.args.get('severity')
        limit = request.args.get('limit', 50, type=int)
        
        # Generate alerts
        alerts = certificate_monitoring_service.generate_certificate_alerts()
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert.get('severity') == severity]
        
        # Apply limit
        alerts = alerts[:limit]
        
        return jsonify({
            'success': True,
            'data': {
                'alerts': alerts,
                'total': len(alerts)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate alerts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve certificate alerts'
        }), 500

@cert_monitoring_bp.route('/renewal-candidates', methods=['GET'])
@require_auth
def get_renewal_candidates():
    """
    Get certificates eligible for renewal
    
    Returns:
        JSON response with renewal candidates
    """
    try:
        # Get renewal candidates
        candidates = certificate_monitoring_service.get_certificate_renewal_candidates()
        
        return jsonify({
            'success': True,
            'data': {
                'candidates': candidates,
                'total': len(candidates)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting renewal candidates: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve renewal candidates'
        }), 500

@cert_monitoring_bp.route('/statistics/organization/<org_id>', methods=['GET'])
@require_auth
def get_organization_certificate_stats(org_id):
    """
    Get certificate statistics for a specific organization
    
    Args:
        org_id: Organization ID
        
    Returns:
        JSON response with organization certificate statistics
    """
    try:
        # Get organization stats
        stats = certificate_monitoring_service.get_certificate_statistics_by_organization(org_id)
        
        if not stats:
            return jsonify({
                'success': False,
                'error': 'Organization not found or no data available'
            }), 404
        
        return jsonify({
            'success': True,
            'data': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting organization certificate stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve organization statistics'
        }), 500

@cert_monitoring_bp.route('/device/<device_id>/status', methods=['GET'])
@require_auth
def get_device_certificate_status(device_id):
    """
    Get certificate status for a specific device
    
    Args:
        device_id: Device ID
        
    Returns:
        JSON response with device certificate status
    """
    try:
        from ..core.database import get_db
        db = get_db()
        
        # Find device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
        
        # Get certificate status
        cert_status = certificate_monitoring_service._get_certificate_status(device)
        
        if not cert_status:
            return jsonify({
                'success': True,
                'data': {
                    'device_id': device_id,
                    'has_certificate': False,
                    'message': 'No certificate found for this device'
                }
            }), 200
        
        return jsonify({
            'success': True,
            'data': cert_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting device certificate status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve device certificate status'
        }), 500