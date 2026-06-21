# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Monitoring Routes Registration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: routes_certificate_monitoring.py
Purpose: Register certificate monitoring and self-service API routes
Version: v2025.07-production
Build Date: 2025-07-19
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

from flask import Flask
from .controllers.certificate_monitoring import cert_monitoring_bp
from .controllers.certificate_self_service import cert_self_service_bp

def register_certificate_monitoring_routes(app: Flask):
    """
    Register all certificate monitoring related routes

    Args:
        app: Flask application instance
    """

    # Certificate monitoring endpoints
    app.register_blueprint(cert_monitoring_bp)

    # User self-service certificate endpoints
    app.register_blueprint(cert_self_service_bp)

    # NOTE: device_cert_api_bp ('/api/v1/device/...') is registered once in
    # api/__init__.py; do not re-register it here (Flask rejects a duplicate
    # blueprint name, which previously aborted this whole registration).
    print("✓ Certificate monitoring routes registered successfully")

def get_certificate_monitoring_endpoints():
    """
    Get list of all certificate monitoring API endpoints
    
    Returns:
        Dict: Organized list of endpoints with descriptions
    """
    
    return {
        "certificate_monitoring": {
            "base_path": "/api/v1/certificates",
            "endpoints": {
                "GET /health": "Get comprehensive certificate health overview",
                "GET /expiring": "Get list of expiring certificates with filters",
                "GET /alerts": "Get certificate alerts with severity filtering",
                "GET /renewal-candidates": "Get certificates eligible for renewal",
                "GET /statistics/organization/<org_id>": "Get certificate statistics for organization",
                "GET /device/<device_id>/status": "Get certificate status for specific device"
            }
        },
        "self_service": {
            "base_path": "/api/v1/certificates/self-service",
            "endpoints": {
                "GET /my-certificates": "Get certificates for current user's devices",
                "POST /renew/<device_id>": "Self-service certificate renewal",
                "GET /renewal-status/<device_id>": "Get certificate renewal status and history",
                "POST /batch-renew": "Batch renewal of multiple certificates",
                "GET /batch-jobs/<job_id>": "Get status of batch renewal job",
                "GET /alerts": "Get certificate alerts for user's devices",
                "POST /alerts/<alert_id>/acknowledge": "Acknowledge certificate alert"
            }
        },
        "device_api": {
            "base_path": "/api/v1/device",
            "endpoints": {
                "GET /<device_id>/certificate/status": "Get certificate status (device-side)",
                "GET /<device_id>/certificate/health": "Get detailed certificate health",
                "POST /<device_id>/certificate/renew-request": "Request certificate renewal from device",
                "GET /<device_id>/certificate/renewal-status/<request_id>": "Get renewal request status",
                "GET /<device_id>/certificate/alerts": "Get certificate alerts for device",
                "GET /<device_id>/certificate/download": "Download device certificate"
            }
        },
        "configuration": {
            "base_path": "/api/v1/certificates",
            "endpoints": {
                "GET /config": "Get certificate monitoring configuration",
                "POST /config": "Update certificate monitoring configuration",
                "GET /config/export": "Export configuration as JSON",
                "POST /config/import": "Import configuration from JSON"
            }
        }
    }