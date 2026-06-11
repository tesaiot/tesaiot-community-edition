# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Device Group Routes
REST API endpoints for device group management

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
from flask import Blueprint, jsonify
from fastapi import APIRouter
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create FastAPI router for module integration
router = APIRouter(prefix="/groups", tags=["device-groups"])

# Create Flask blueprint for legacy support
device_group_bp = Blueprint('device_groups', __name__, url_prefix='/api/v1/device-groups')


# FastAPI endpoint for health check
@router.get("/health")
async def fastapi_health_check() -> Dict[str, Any]:
    """Health check endpoint for device groups (FastAPI)"""
    return {
        'status': 'healthy',
        'service': 'device-groups'
    }


# Flask endpoint for health check (legacy)
@device_group_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for device groups"""
    return jsonify({
        'status': 'healthy',
        'service': 'device-groups'
    })


# TODO: Implement device group management endpoints
# - Create device group
# - Get device group
# - Update device group
# - Delete device group
# - List device groups
# - Add devices to group
# - Remove devices from group
# - Get devices in group