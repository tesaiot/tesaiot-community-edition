# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Native WebSocket Controller
Handles real-time telemetry streaming via native WebSocket connections
Compatible with browser WebSocket API
"""

import logging
import json
from datetime import datetime
from flask import request
from simple_websocket import Server, ConnectionClosed

logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections = {}

def handle_websocket():
    """Handle native WebSocket connections"""
    ws = Server.accept(request.environ)
    connection_id = None
    
    try:
        # Send initial connection message
        ws.send(json.dumps({
            'type': 'connected',
            'status': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }))
        
        # Generate unique connection ID
        connection_id = f"ws_{id(ws)}_{datetime.utcnow().timestamp()}"
        active_connections[connection_id] = ws
        logger.info(f"WebSocket client connected: {connection_id}")
        
        while True:
            try:
                # Receive message from client
                data = ws.receive()
                if data is None:
                    break
                    
                # Parse message
                try:
                    message = json.loads(data)
                    message_type = message.get('type', '')
                    
                    # Handle different message types
                    if message_type == 'ping':
                        # Respond to ping
                        ws.send(json.dumps({
                            'type': 'pong',
                            'timestamp': datetime.utcnow().isoformat(),
                            'echo': message.get('data')
                        }))
                        
                    elif message_type == 'subscribe':
                        # Subscribe to device telemetry
                        device_id = message.get('device_id')
                        if device_id:
                            # Store subscription info (simplified for now)
                            ws.send(json.dumps({
                                'type': 'subscribed',
                                'device_id': device_id,
                                'status': 'subscribed',
                                'timestamp': datetime.utcnow().isoformat()
                            }))
                            logger.info(f"Client {connection_id} subscribed to device: {device_id}")
                            
                    elif message_type == 'unsubscribe':
                        # Unsubscribe from device telemetry
                        device_id = message.get('device_id')
                        if device_id:
                            ws.send(json.dumps({
                                'type': 'unsubscribed',
                                'device_id': device_id,
                                'status': 'unsubscribed',
                                'timestamp': datetime.utcnow().isoformat()
                            }))
                            logger.info(f"Client {connection_id} unsubscribed from device: {device_id}")
                            
                except json.JSONDecodeError:
                    ws.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON format'
                    }))
                    
            except ConnectionClosed:
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        
    finally:
        # Clean up connection
        if connection_id and connection_id in active_connections:
            del active_connections[connection_id]
        logger.info(f"WebSocket client disconnected: {connection_id}")
        ws.close()
    
    return ''

def broadcast_telemetry(device_id, telemetry_data):
    """
    Broadcast telemetry data to all connected WebSocket clients.
    
    Args:
        device_id: Device identifier
        telemetry_data: Telemetry data to broadcast
    """
    message = json.dumps({
        'type': 'telemetry_update',
        'device_id': device_id,
        'data': telemetry_data,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send to all active connections
    disconnected = []
    for conn_id, ws in active_connections.items():
        try:
            ws.send(message)
        except Exception as e:
            logger.error(f"Error sending to {conn_id}: {e}")
            disconnected.append(conn_id)
    
    # Clean up disconnected clients
    for conn_id in disconnected:
        del active_connections[conn_id]

def broadcast_device_status(device_id, status):
    """
    Broadcast device status updates to all connected WebSocket clients.
    
    Args:
        device_id: Device identifier
        status: Device status
    """
    message = json.dumps({
        'type': 'device_status',
        'device_id': device_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send to all active connections
    disconnected = []
    for conn_id, ws in active_connections.items():
        try:
            ws.send(message)
        except Exception as e:
            logger.error(f"Error sending to {conn_id}: {e}")
            disconnected.append(conn_id)
    
    # Clean up disconnected clients
    for conn_id in disconnected:
        del active_connections[conn_id]