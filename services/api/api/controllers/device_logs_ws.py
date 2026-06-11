# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Logs WebSocket Streaming
Version: v2026.01
Build: 2026-01-09

Real-time log streaming via WebSocket for debugging PSoC devices.
"""

import logging
import json
from datetime import datetime
from typing import Set, Dict
from geventwebsocket.websocket import WebSocket
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)

# Active WebSocket connections: device_id -> Set[WebSocket]
active_log_streams: Dict[str, Set[WebSocket]] = {}
MAX_CONNECTIONS_PER_DEVICE = 10


def handle_device_log_stream(environ, start_response):
    """
    WebSocket endpoint for real-time device log streaming.

    Path: /ws/device-logs/<device_id>

    Query Parameters:
    - token: JWT authentication token (required)
    - category: Filter by category (security, mqtt, csr, etc.)
    - level: Filter by level (DEBUG, INFO, ERROR, etc.)
    """
    device_id = None
    try:
        ws = environ.get('wsgi.websocket')
        if not ws:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'WebSocket connection required']

        # Extract device_id from path
        path_info = environ.get('PATH_INFO', '')
        parts = path_info.split('/')
        if len(parts) < 4:
            ws.send(json.dumps({'error': 'Invalid path, expected /ws/device-logs/<device_id>'}))
            ws.close()
            return []

        device_id = parts[3]

        # Extract and validate authentication token
        query_string = environ.get('QUERY_STRING', '')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if not token:
            logger.warning(f"WebSocket connection attempt without token for device {device_id}")
            ws.send(json.dumps({
                'error': 'Authentication required',
                'message': 'JWT token must be provided via token query parameter'
            }))
            ws.close()
            return []

        # Validate token using existing auth infrastructure
        from ..core.auth import verify_token
        payload, error_msg = verify_token(token)

        if not payload:
            logger.warning(f"WebSocket authentication failed for device {device_id}: {error_msg}")
            ws.send(json.dumps({
                'error': 'Authentication failed',
                'message': error_msg or 'Invalid authentication token'
            }))
            ws.close()
            return []

        # Log successful authentication
        user_email = payload.get('email', 'unknown')
        user_role = payload.get('role', 'unknown')
        logger.info(f"WebSocket authenticated: {user_email} (role: {user_role}) for device {device_id}")

        # Check connection limit
        if device_id not in active_log_streams:
            active_log_streams[device_id] = set()

        if len(active_log_streams[device_id]) >= MAX_CONNECTIONS_PER_DEVICE:
            ws.send(json.dumps({
                'error': f'Maximum {MAX_CONNECTIONS_PER_DEVICE} concurrent connections per device exceeded'
            }))
            ws.close()
            return []

        # Add connection
        active_log_streams[device_id].add(ws)
        logger.info(f"WebSocket connected for device {device_id}, total connections: {len(active_log_streams[device_id])}")

        # Send connection confirmation
        ws.send(json.dumps({
            'type': 'connected',
            'device_id': device_id,
            'timestamp': datetime.utcnow().isoformat()
        }))

        # Keep connection alive and handle incoming messages
        while not ws.closed:
            message = ws.receive()
            if message is None:
                break

            # Handle ping/pong
            if message == 'ping':
                ws.send(json.dumps({'type': 'pong'}))

    except Exception as e:
        logger.error(f"WebSocket error for device logs: {e}")
    finally:
        # Cleanup connection
        if device_id and device_id in active_log_streams:
            active_log_streams[device_id].discard(ws)
            if not active_log_streams[device_id]:
                del active_log_streams[device_id]
            logger.info(f"WebSocket disconnected for device {device_id}")

    return []


def broadcast_device_log(device_id: str, log_entry: dict):
    """
    Persist log to MongoDB AND broadcast to all active WebSocket connections.

    Phase 5.1: Log Persistence
    - Logs are persisted to MongoDB first for historical access
    - Then broadcast to active WebSocket clients for real-time streaming
    - If MongoDB save fails, broadcasting continues (degraded mode)

    Args:
        device_id: Device ID
        log_entry: Log entry dictionary with keys:
            - level: Log level (TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL)
            - category: Log category (security, mqtt, csr, telemetry, command, system)
            - source: Source (device, platform, emqx, mqtt_bridge, csr_bridge, system)
            - event_type: Event type identifier (e.g., 'mqtt_connect', 'csr_received')
            - message: Log message
            - details: Additional details dict (optional)
            - correlation_id: Correlation ID for tracing (optional)
            - error: Error information dict (optional)
    """
    # Phase 5.1: Persist to MongoDB first (critical for history)
    try:
        from ..models.device_log_enhanced import EnhancedDeviceLog, LogLevel, LogCategory, LogSource

        # Extract and validate fields
        level_str = log_entry.get('level', 'INFO').upper()
        category_str = log_entry.get('category', 'system').lower()
        source_str = log_entry.get('source', 'platform').lower()

        # Convert to enum values with fallback
        try:
            level = LogLevel[level_str]
        except KeyError:
            logger.warning(f"Invalid log level '{level_str}', defaulting to INFO")
            level = LogLevel.INFO

        try:
            category = LogCategory[category_str.upper()]
        except KeyError:
            logger.warning(f"Invalid log category '{category_str}', defaulting to SYSTEM")
            category = LogCategory.SYSTEM

        try:
            source = LogSource[source_str.upper()]
        except KeyError:
            logger.warning(f"Invalid log source '{source_str}', defaulting to PLATFORM")
            source = LogSource.PLATFORM

        # Get MongoDB collection directly (bypass async wrapper since using sync pymongo)
        from ..core.database import get_db
        db = get_db()
        if db:
            collection = db['device_logs_enhanced']

            # Create log document
            full_log = EnhancedDeviceLog(
                device_id=device_id,
                timestamp=datetime.utcnow(),
                level=level,
                category=category,
                source=source,
                event_type=log_entry.get('event_type', 'unknown'),
                message=log_entry.get('message', ''),
                correlation_id=log_entry.get('correlation_id')
            )

            # Add optional fields
            if log_entry.get('details'):
                full_log.details = log_entry.get('details')
            if log_entry.get('error'):
                full_log.error = log_entry.get('error')

            # Convert to MongoDB document and insert
            doc = full_log.to_mongo_dict()
            collection.insert_one(doc)

            logger.debug(f"✅ Persisted log to MongoDB for device {device_id}: {log_entry.get('event_type')}")
        else:
            logger.warning("Database connection not available, skipping MongoDB persistence")

    except Exception as e:
        logger.error(f"❌ Failed to persist log to MongoDB for device {device_id}: {e}")
        # Continue with WebSocket broadcast even if DB save fails (degraded mode)

    # Phase 5.1: Broadcast to active WebSocket connections (existing functionality)
    if device_id not in active_log_streams:
        # No active connections, but log was saved to DB for historical access
        return

    message = json.dumps({
        'type': 'log',
        'device_id': device_id,
        'log': log_entry,
        'timestamp': datetime.utcnow().isoformat()
    })

    disconnected = set()

    for ws in active_log_streams[device_id]:
        try:
            if not ws.closed:
                ws.send(message)
            else:
                disconnected.add(ws)
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {e}")
            disconnected.add(ws)

    # Cleanup disconnected sockets
    for ws in disconnected:
        active_log_streams[device_id].discard(ws)

    if not active_log_streams[device_id]:
        del active_log_streams[device_id]


def get_active_stream_count(device_id: str = None) -> int:
    """Get count of active WebSocket connections."""
    if device_id:
        return len(active_log_streams.get(device_id, set()))

    return sum(len(connections) for connections in active_log_streams.values())
