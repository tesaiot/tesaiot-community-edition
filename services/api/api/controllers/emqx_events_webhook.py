# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - EMQX Events Webhook Controller
Version: v2026.01
Build: 2026-01-09
Module: Device Logs Improvement Feature

Handles EMQX webhook events for enhanced device logging:
- client.connected: Device connected to MQTT broker
- client.disconnected: Device disconnected from broker
- client.connack: Connection acknowledgment
- message.publish: Message published (for CSR workflow tracking)
- message.delivered: Message delivered to device

Note: TLS handshake events are NOT exposed by EMQX webhook API.
For TLS errors, see ISS-001 in ISSUES.md for workaround approaches.
"""

import logging
import asyncio
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

from ..services.enhanced_device_log_service import (
    log_mqtt_event,
    log_security_event
)
from ..services.csr_workflow_service import CSRWorkflowService
from ..models.device_log_enhanced import LogLevel
from ..models.csr_workflow_status import WorkflowStep, StepStatus
# SECURITY: reuse the constant-time, fail-closed bearer check used by the
# EMQX auth/ACL webhooks (EMQX_WEBHOOK_SECRET; unset/CHANGEME* => deny).
from .emqx_auth import _validate_webhook_authorization

logger = logging.getLogger(__name__)

# Create blueprint
emqx_webhook_bp = Blueprint('emqx_events', __name__, url_prefix='/api/v1/webhook/emqx')


def _extract_device_id(client_id: str) -> Optional[str]:
    """Extract device ID from EMQX client ID"""
    # Client ID format: device_id or device_id_suffix
    if not client_id:
        return None
    # If client_id is UUID format, use it directly
    parts = client_id.split('_')
    return parts[0] if parts else client_id


def _run_async(coro):
    """Run async function from sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Schedule on existing loop
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=5)
    else:
        return loop.run_until_complete(coro)


@emqx_webhook_bp.route('/events', methods=['POST'])
def handle_emqx_event():
    """
    Handle EMQX webhook events.

    EMQX sends various events via webhook. This endpoint processes:
    - client.connected: Log MQTT connection
    - client.disconnected: Log disconnection with reason
    - client.connack: Log connection acknowledgment
    - message.publish: Track CSR workflow messages
    - message.delivered: Track message delivery

    Expected payload format (varies by event type):
    {
        "event": "client.connected",
        "clientid": "device-uuid",
        "username": "device-uuid",
        "peername": "192.168.1.100:54321",
        "proto_name": "MQTT",
        "proto_ver": 5,
        "keepalive": 60,
        "clean_start": true,
        "connected_at": 1704793200000,
        ...
    }
    """
    # SECURITY: this endpoint was completely unauthenticated. Require the
    # EMQX webhook bearer secret (constant-time compare, fail-closed when the
    # secret is unset or still a CHANGEME* placeholder).
    if not _validate_webhook_authorization():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Validate content type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        event_type = data.get("event")

        if not event_type:
            return jsonify({"error": "Missing event type"}), 400

        # Route to appropriate handler
        if event_type == "client.connected":
            _run_async(_handle_client_connected(data))

        elif event_type == "client.disconnected":
            _run_async(_handle_client_disconnected(data))

        elif event_type == "client.connack":
            _run_async(_handle_client_connack(data))

        elif event_type == "message.publish":
            _run_async(_handle_message_publish(data))

        elif event_type == "message.delivered":
            _run_async(_handle_message_delivered(data))

        elif event_type == "client.authenticate":
            _run_async(_handle_client_authenticate(data))

        elif event_type == "client.authorize":
            _run_async(_handle_client_authorize(data))

        else:
            # Log unknown event types for debugging
            logger.debug(f"Unhandled EMQX event type: {event_type}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        # Log details server-side; never leak internals to the caller.
        logger.error(f"Error handling EMQX webhook: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


async def _handle_client_connected(data: Dict[str, Any]):
    """Handle client.connected event"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    # Build details
    details = {
        "client_id": client_id,
        "username": data.get("username"),
        "peername": data.get("peername"),
        "proto_name": data.get("proto_name", "MQTT"),
        "proto_ver": data.get("proto_ver"),
        "keepalive": data.get("keepalive"),
        "clean_start": data.get("clean_start"),
        "connected_at": data.get("connected_at")
    }

    # Log the connection
    await log_mqtt_event(
        device_id=device_id,
        event_type="mqtt_connected",
        message=f"Device connected to MQTT broker from {data.get('peername', 'unknown')}",
        level=LogLevel.INFO,
        details=details
    )

    # Update CSR workflow if active
    try:
        await CSRWorkflowService.update_step(
            device_id=device_id,
            step=WorkflowStep.MQTT_CONNECTED,
            status=StepStatus.COMPLETED,
            details=f"Connected from {data.get('peername', 'unknown')}"
        )
    except Exception as e:
        logger.debug(f"No active CSR workflow for device {device_id}: {e}")


async def _handle_client_disconnected(data: Dict[str, Any]):
    """Handle client.disconnected event"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    reason = data.get("reason", "unknown")
    disconnected_at = data.get("disconnected_at")

    # Determine log level based on reason
    level = LogLevel.INFO
    if reason in ["kicked", "banned", "auth_error", "protocol_error"]:
        level = LogLevel.WARN
    elif reason in ["takenover"]:
        level = LogLevel.WARN

    details = {
        "client_id": client_id,
        "reason": reason,
        "disconnected_at": disconnected_at,
        "peername": data.get("peername")
    }

    await log_mqtt_event(
        device_id=device_id,
        event_type="mqtt_disconnected",
        message=f"Device disconnected from MQTT broker. Reason: {reason}",
        level=level,
        details=details
    )


async def _handle_client_connack(data: Dict[str, Any]):
    """Handle client.connack event"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    reason_code = data.get("reason_code", 0)
    conn_ack = data.get("conn_ack", "success")

    # Check if connection was rejected
    if reason_code != 0:
        level = LogLevel.ERROR
        message = f"MQTT connection rejected. Reason code: {reason_code}, ACK: {conn_ack}"
    else:
        level = LogLevel.DEBUG
        message = f"MQTT connection acknowledged"

    details = {
        "client_id": client_id,
        "reason_code": reason_code,
        "conn_ack": conn_ack,
        "session_present": data.get("session_present")
    }

    await log_mqtt_event(
        device_id=device_id,
        event_type="mqtt_connack",
        message=message,
        level=level,
        details=details
    )


async def _handle_message_publish(data: Dict[str, Any]):
    """Handle message.publish event - track CSR workflow messages"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)
    topic = data.get("topic", "")

    if not device_id:
        return

    # Check if this is a CSR-related topic
    if "/commands/csr" in topic:
        await log_mqtt_event(
            device_id=device_id,
            event_type="csr_message_published",
            message=f"CSR message published to topic: {topic}",
            level=LogLevel.INFO,
            details={
                "topic": topic,
                "qos": data.get("qos"),
                "payload_size": len(data.get("payload", ""))
            }
        )

        # Update CSR workflow
        try:
            await CSRWorkflowService.update_step(
                device_id=device_id,
                step=WorkflowStep.CSR_SUBMITTED,
                status=StepStatus.COMPLETED,
                details="CSR message received by broker"
            )
        except Exception as e:
            logger.debug(f"No active CSR workflow for device {device_id}")

    elif "/commands/certificate" in topic:
        # Certificate delivery message
        await log_mqtt_event(
            device_id=device_id,
            event_type="certificate_message_published",
            message=f"Certificate message published to device topic",
            level=LogLevel.INFO,
            details={
                "topic": topic,
                "qos": data.get("qos")
            }
        )


async def _handle_message_delivered(data: Dict[str, Any]):
    """Handle message.delivered event - track certificate delivery"""
    # This event is triggered when message is delivered to subscriber
    topic = data.get("topic", "")
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    # Check if certificate was delivered
    if "/commands/certificate" in topic:
        await log_mqtt_event(
            device_id=device_id,
            event_type="certificate_delivered",
            message="Certificate delivered to device via MQTT",
            level=LogLevel.INFO,
            details={
                "topic": topic,
                "from_clientid": data.get("from_clientid")
            }
        )

        # Update CSR workflow
        try:
            await CSRWorkflowService.update_step(
                device_id=device_id,
                step=WorkflowStep.CERTIFICATE_DELIVERED,
                status=StepStatus.COMPLETED,
                details="Certificate message delivered to device"
            )
        except Exception as e:
            logger.debug(f"No active CSR workflow for device {device_id}")


async def _handle_client_authenticate(data: Dict[str, Any]):
    """Handle client.authenticate event - log authentication attempts"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    result = data.get("result", "unknown")

    if result == "success":
        level = LogLevel.DEBUG
        message = "MQTT authentication successful"
    else:
        level = LogLevel.WARN
        message = f"MQTT authentication failed: {result}"

    await log_security_event(
        device_id=device_id,
        event_type="mqtt_authenticate",
        message=message,
        level=level,
        details={
            "client_id": client_id,
            "username": data.get("username"),
            "result": result,
            "peername": data.get("peername")
        }
    )


async def _handle_client_authorize(data: Dict[str, Any]):
    """Handle client.authorize event - log authorization attempts"""
    client_id = data.get("clientid")
    device_id = _extract_device_id(client_id)

    if not device_id:
        return

    result = data.get("result", "unknown")
    action = data.get("action", "unknown")
    topic = data.get("topic", "")

    if result != "allow":
        level = LogLevel.WARN
        message = f"MQTT authorization denied for {action} on topic: {topic}"

        await log_security_event(
            device_id=device_id,
            event_type="mqtt_authorize_denied",
            message=message,
            level=level,
            details={
                "client_id": client_id,
                "action": action,
                "topic": topic,
                "result": result
            }
        )
