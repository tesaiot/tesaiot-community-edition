# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - WebSocket Controller (ARCHIVED)

This file has been archived as part of the WebSocket architecture cleanup.
Socket.IO implementation has been removed in favor of native WebSocket.

Use websocket_native.py and services/websocket_telemetry.py for WebSocket functionality.

Archived on: 2025-08-26
Reason: Simplified WebSocket architecture - removed Socket.IO dependency
"""

# This file is archived and should not be imported
import logging

logger = logging.getLogger(__name__)
logger.warning("websocket.py has been archived - use websocket_native.py instead")

# Placeholder functions for backward compatibility
def init_websocket(app):
    """Archived: Socket.IO initialization removed"""
    logger.warning("Socket.IO WebSocket initialization archived - using native WebSocket instead")
    return None

def broadcast_telemetry(device_id, telemetry_data):
    """Archived: Use services/websocket_telemetry.py instead"""
    logger.warning("Socket.IO broadcast_telemetry archived - use WebSocketTelemetryService.broadcast_telemetry instead")
    
    # Try to use the new service if available
    try:
        from ..services.websocket_telemetry import get_websocket_telemetry_service
        service = get_websocket_telemetry_service()
        if service:
            service.broadcast_telemetry(device_id, telemetry_data, source='legacy')
    except Exception as e:
        logger.error(f"Failed to use new telemetry service: {e}")

def broadcast_device_status(device_id, status):
    """Archived: Socket.IO device status broadcast removed"""
    logger.warning("Socket.IO broadcast_device_status archived")

# Set socketio to None to indicate it's not available
socketio = None