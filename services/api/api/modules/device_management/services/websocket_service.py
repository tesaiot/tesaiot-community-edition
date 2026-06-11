# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - WebSocket Service
Manages WebSocket connections for real-time event streaming

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import asyncio
import json
import uuid
import time
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from ..models.event_streaming_models import (
    EventPayload, EventSubscription, WebSocketMessage, WebSocketConnection,
    EventType, EventPriority, EventCategory
)
from ..models.audit_models import DeviceAuditAction
from ..services.audit_logging_service import device_audit_service
from ....core.database import get_db
from ....core.auth import verify_token

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Manages WebSocket connections with pooling and health monitoring"""
    
    def __init__(self, max_connections_per_user: int = 5, max_total_connections: int = 1000):
        self.max_connections_per_user = max_connections_per_user
        self.max_total_connections = max_total_connections
        self.connections: Dict[str, WebSocketConnection] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.lock = asyncio.Lock()
        
    async def add_connection(
        self,
        websocket: WebSocket,
        user_id: str,
        organization_id: str,
        client_id: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> WebSocketConnection:
        """Add a new connection to the pool"""
        async with self.lock:
            # Check total connections limit
            if len(self.connections) >= self.max_total_connections:
                raise Exception("Maximum total connections reached")
            
            # Check per-user connections limit
            if len(self.user_connections[user_id]) >= self.max_connections_per_user:
                # Remove oldest connection for this user
                oldest_conn_id = min(self.user_connections[user_id], 
                                    key=lambda cid: self.connections[cid].connected_at)
                await self.remove_connection(oldest_conn_id)
            
            # Create new connection
            connection_id = str(uuid.uuid4())
            connection = WebSocketConnection(
                connection_id=connection_id,
                client_id=client_id,
                user_id=user_id,
                organization_id=organization_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.connections[connection_id] = connection
            self.websockets[connection_id] = websocket
            self.user_connections[user_id].add(connection_id)
            
            logger.info(f"Added WebSocket connection {connection_id} for user {user_id}")
            return connection
    
    async def remove_connection(self, connection_id: str):
        """Remove a connection from the pool"""
        async with self.lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                
                # Close WebSocket if still open
                if connection_id in self.websockets:
                    websocket = self.websockets[connection_id]
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.close()
                    del self.websockets[connection_id]
                
                # Remove from user connections
                self.user_connections[connection.user_id].discard(connection_id)
                if not self.user_connections[connection.user_id]:
                    del self.user_connections[connection.user_id]
                
                # Remove connection
                del self.connections[connection_id]
                
                logger.info(f"Removed WebSocket connection {connection_id}")
    
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get a connection by ID"""
        return self.connections.get(connection_id)
    
    def get_websocket(self, connection_id: str) -> Optional[WebSocket]:
        """Get a WebSocket by connection ID"""
        return self.websockets.get(connection_id)
    
    def get_user_connections(self, user_id: str) -> List[WebSocketConnection]:
        """Get all connections for a user"""
        return [self.connections[cid] for cid in self.user_connections.get(user_id, [])]
    
    def get_organization_connections(self, organization_id: str) -> List[WebSocketConnection]:
        """Get all connections for an organization"""
        return [conn for conn in self.connections.values() 
                if conn.organization_id == organization_id]


class WebSocketService:
    """Service for managing WebSocket connections and event streaming"""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 60,
        max_message_size: int = 1024 * 1024,  # 1MB
        rate_limit_per_minute: int = 100
    ):
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.max_message_size = max_message_size
        self.rate_limit_per_minute = rate_limit_per_minute
        
        # Connection management
        self.connection_pool = ConnectionPool()
        self.subscriptions: Dict[str, EventSubscription] = {}
        self.connection_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Rate limiting
        self.message_counts: Dict[str, List[float]] = defaultdict(list)
        
        # Background tasks
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Event queues for each connection
        self.event_queues: Dict[str, asyncio.Queue] = {}
        
        # Database
        self.db = get_db()
        
        logger.info("WebSocketService initialized")
    
    async def initialize(self):
        """Initialize the service and start background tasks"""
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        logger.info("WebSocketService background tasks started")
    
    async def shutdown(self):
        """Shutdown the service and cleanup resources"""
        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Close all connections
        connection_ids = list(self.connection_pool.connections.keys())
        for conn_id in connection_ids:
            await self.connection_pool.remove_connection(conn_id)
        
        logger.info("WebSocketService shut down")
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        token: str,
        client_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Handle a new WebSocket connection"""
        connection = None
        
        try:
            # Verify authentication
            user = verify_token(token)
            if not user:
                await websocket.close(code=4001, reason="Unauthorized")
                return
            
            # Accept connection
            await websocket.accept()
            
            # Create connection record
            connection = await self.connection_pool.add_connection(
                websocket=websocket,
                user_id=str(user.get('_id', user.get('id'))),
                organization_id=user.get('organization_id'),
                client_id=client_id or str(uuid.uuid4()),
                ip_address=ip_address or "unknown",
                user_agent=user_agent
            )
            
            # Create event queue for this connection
            self.event_queues[connection.connection_id] = asyncio.Queue(maxsize=1000)
            
            # Send welcome message
            welcome_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="connected",
                timestamp=datetime.utcnow(),
                payload={
                    "connection_id": connection.connection_id,
                    "heartbeat_interval": self.heartbeat_interval,
                    "max_message_size": self.max_message_size,
                    "rate_limit": self.rate_limit_per_minute
                }
            )
            await self._send_message(connection.connection_id, welcome_msg)
            
            # Log connection
            await device_audit_service.log_device_operation(
                action=DeviceAuditAction.DEVICE_WEBSOCKET_CONNECTED,
                user=user,
                details={
                    "connection_id": connection.connection_id,
                    "client_id": client_id
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Start event sender task
            event_sender_task = asyncio.create_task(
                self._event_sender(connection.connection_id)
            )
            
            # Handle incoming messages
            while True:
                try:
                    # Receive message with timeout
                    message_data = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=self.heartbeat_timeout
                    )
                    
                    # Check rate limit
                    if not self._check_rate_limit(connection.connection_id):
                        error_msg = WebSocketMessage(
                            message_id=str(uuid.uuid4()),
                            message_type="error",
                            timestamp=datetime.utcnow(),
                            payload={"error": "Rate limit exceeded"}
                        )
                        await self._send_message(connection.connection_id, error_msg)
                        continue
                    
                    # Process message
                    await self._handle_message(connection, message_data)
                    
                except asyncio.TimeoutError:
                    # Connection timeout
                    logger.warning(f"WebSocket connection {connection.connection_id} timed out")
                    break
                    
                except WebSocketDisconnect:
                    # Client disconnected
                    logger.info(f"WebSocket client {connection.connection_id} disconnected")
                    break
                    
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")
                    connection.error_count += 1
                    
                    if connection.error_count > 10:
                        logger.error(f"Too many errors for connection {connection.connection_id}")
                        break
        
        except Exception as e:
            logger.error(f"Error in WebSocket connection handler: {e}")
        
        finally:
            # Cleanup
            if connection:
                # Cancel event sender task
                event_sender_task.cancel()
                
                # Remove subscriptions
                for sub_id in self.connection_subscriptions.get(connection.connection_id, []):
                    del self.subscriptions[sub_id]
                del self.connection_subscriptions[connection.connection_id]
                
                # Remove event queue
                if connection.connection_id in self.event_queues:
                    del self.event_queues[connection.connection_id]
                
                # Remove connection
                await self.connection_pool.remove_connection(connection.connection_id)
                
                # Log disconnection
                try:
                    await device_audit_service.log_device_operation(
                        action=DeviceAuditAction.DEVICE_WEBSOCKET_DISCONNECTED,
                        user={"_id": connection.user_id, "organization_id": connection.organization_id},
                        details={
                            "connection_id": connection.connection_id,
                            "duration_seconds": (datetime.utcnow() - connection.connected_at).total_seconds(),
                            "message_count": connection.message_count,
                            "error_count": connection.error_count
                        }
                    )
                except:
                    pass
    
    async def _handle_message(self, connection: WebSocketConnection, message_data: str):
        """Handle incoming WebSocket message"""
        try:
            # Parse message
            data = json.loads(message_data)
            message_type = data.get("type")
            payload = data.get("payload", {})
            
            # Update connection activity
            connection.last_activity = datetime.utcnow()
            connection.message_count += 1
            
            # Handle different message types
            if message_type == "ping":
                # Respond with pong
                pong_msg = WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    message_type="pong",
                    timestamp=datetime.utcnow(),
                    payload={"timestamp": payload.get("timestamp")}
                )
                await self._send_message(connection.connection_id, pong_msg)
                connection.last_ping = datetime.utcnow()
                
            elif message_type == "subscribe":
                # Create subscription
                await self._handle_subscribe(connection, payload)
                
            elif message_type == "unsubscribe":
                # Remove subscription
                await self._handle_unsubscribe(connection, payload)
                
            elif message_type == "update_filters":
                # Update subscription filters
                await self._handle_update_filters(connection, payload)
                
            else:
                # Unknown message type
                error_msg = WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    message_type="error",
                    timestamp=datetime.utcnow(),
                    payload={"error": f"Unknown message type: {message_type}"}
                )
                await self._send_message(connection.connection_id, error_msg)
        
        except json.JSONDecodeError:
            error_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="error",
                timestamp=datetime.utcnow(),
                payload={"error": "Invalid JSON"}
            )
            await self._send_message(connection.connection_id, error_msg)
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="error",
                timestamp=datetime.utcnow(),
                payload={"error": "Internal error"}
            )
            await self._send_message(connection.connection_id, error_msg)
    
    async def _handle_subscribe(self, connection: WebSocketConnection, payload: Dict[str, Any]):
        """Handle subscription request"""
        try:
            # Create subscription
            subscription = EventSubscription(
                subscription_id=str(uuid.uuid4()),
                client_id=connection.client_id,
                user_id=connection.user_id,
                organization_id=connection.organization_id,
                event_types=[EventType(et) for et in payload.get("event_types", [])],
                categories=[EventCategory(cat) for cat in payload.get("categories", [])],
                priorities=[EventPriority(pri) for pri in payload.get("priorities", [])],
                device_ids=payload.get("device_ids", []),
                group_ids=payload.get("group_ids", []),
                filters=payload.get("filters", {})
            )
            
            # Store subscription
            self.subscriptions[subscription.subscription_id] = subscription
            self.connection_subscriptions[connection.connection_id].add(subscription.subscription_id)
            connection.subscriptions.add(subscription.subscription_id)
            
            # Send confirmation
            confirm_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="subscribed",
                timestamp=datetime.utcnow(),
                payload={
                    "subscription_id": subscription.subscription_id,
                    "event_types": [et.value for et in subscription.event_types],
                    "categories": [cat.value for cat in subscription.categories]
                }
            )
            await self._send_message(connection.connection_id, confirm_msg)
            
            logger.info(f"Created subscription {subscription.subscription_id} for connection {connection.connection_id}")
        
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
            error_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="error",
                timestamp=datetime.utcnow(),
                payload={"error": "Failed to create subscription"}
            )
            await self._send_message(connection.connection_id, error_msg)
    
    async def _handle_unsubscribe(self, connection: WebSocketConnection, payload: Dict[str, Any]):
        """Handle unsubscribe request"""
        subscription_id = payload.get("subscription_id")
        
        if subscription_id in self.subscriptions:
            # Remove subscription
            del self.subscriptions[subscription_id]
            self.connection_subscriptions[connection.connection_id].discard(subscription_id)
            connection.subscriptions.discard(subscription_id)
            
            # Send confirmation
            confirm_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="unsubscribed",
                timestamp=datetime.utcnow(),
                payload={"subscription_id": subscription_id}
            )
            await self._send_message(connection.connection_id, confirm_msg)
            
            logger.info(f"Removed subscription {subscription_id}")
        else:
            error_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="error",
                timestamp=datetime.utcnow(),
                payload={"error": "Subscription not found"}
            )
            await self._send_message(connection.connection_id, error_msg)
    
    async def _handle_update_filters(self, connection: WebSocketConnection, payload: Dict[str, Any]):
        """Handle filter update request"""
        subscription_id = payload.get("subscription_id")
        
        if subscription_id in self.subscriptions:
            subscription = self.subscriptions[subscription_id]
            
            # Update filters
            if "event_types" in payload:
                subscription.event_types = [EventType(et) for et in payload["event_types"]]
            if "categories" in payload:
                subscription.categories = [EventCategory(cat) for cat in payload["categories"]]
            if "priorities" in payload:
                subscription.priorities = [EventPriority(pri) for pri in payload["priorities"]]
            if "device_ids" in payload:
                subscription.device_ids = payload["device_ids"]
            if "group_ids" in payload:
                subscription.group_ids = payload["group_ids"]
            if "filters" in payload:
                subscription.filters = payload["filters"]
            
            # Send confirmation
            confirm_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="filters_updated",
                timestamp=datetime.utcnow(),
                payload={"subscription_id": subscription_id}
            )
            await self._send_message(connection.connection_id, confirm_msg)
            
            logger.info(f"Updated filters for subscription {subscription_id}")
        else:
            error_msg = WebSocketMessage(
                message_id=str(uuid.uuid4()),
                message_type="error",
                timestamp=datetime.utcnow(),
                payload={"error": "Subscription not found"}
            )
            await self._send_message(connection.connection_id, error_msg)
    
    async def publish_event(self, event: EventPayload):
        """Publish an event to all matching subscriptions"""
        try:
            # Find matching subscriptions
            for sub_id, subscription in self.subscriptions.items():
                if subscription.matches_event(event):
                    # Find connection for this subscription
                    for conn_id, sub_ids in self.connection_subscriptions.items():
                        if sub_id in sub_ids and conn_id in self.event_queues:
                            # Queue event for this connection
                            try:
                                await self.event_queues[conn_id].put(event)
                                subscription.event_count += 1
                                subscription.last_event_at = datetime.utcnow()
                            except asyncio.QueueFull:
                                logger.warning(f"Event queue full for connection {conn_id}")
        
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
    
    async def _event_sender(self, connection_id: str):
        """Send queued events to a connection"""
        try:
            queue = self.event_queues.get(connection_id)
            if not queue:
                return
            
            while True:
                # Get event from queue
                event = await queue.get()
                
                # Create event message
                event_msg = WebSocketMessage(
                    message_id=str(uuid.uuid4()),
                    message_type="event",
                    timestamp=datetime.utcnow(),
                    payload=event.to_dict()
                )
                
                # Send to client
                await self._send_message(connection_id, event_msg)
        
        except asyncio.CancelledError:
            # Task cancelled
            pass
        except Exception as e:
            logger.error(f"Error in event sender: {e}")
    
    async def _send_message(self, connection_id: str, message: WebSocketMessage) -> bool:
        """Send a message to a connection"""
        try:
            websocket = self.connection_pool.get_websocket(connection_id)
            connection = self.connection_pool.get_connection(connection_id)
            
            if websocket and connection:
                # Check message size
                message_json = message.to_json()
                if len(message_json) > self.max_message_size:
                    logger.warning(f"Message too large for connection {connection_id}")
                    return False
                
                # Send message
                await websocket.send_text(message_json)
                connection.message_count += 1
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False
    
    def _check_rate_limit(self, connection_id: str) -> bool:
        """Check if connection has exceeded rate limit"""
        now = time.time()
        
        # Clean old timestamps
        self.message_counts[connection_id] = [
            ts for ts in self.message_counts[connection_id]
            if now - ts < 60
        ]
        
        # Check limit
        if len(self.message_counts[connection_id]) >= self.rate_limit_per_minute:
            return False
        
        # Add current timestamp
        self.message_counts[connection_id].append(now)
        return True
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with periodic heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Send heartbeat to all connections
                for conn_id, connection in list(self.connection_pool.connections.items()):
                    try:
                        # Check if connection is stale
                        if (datetime.utcnow() - connection.last_activity).total_seconds() > self.heartbeat_timeout:
                            logger.warning(f"Connection {conn_id} is stale, removing")
                            await self.connection_pool.remove_connection(conn_id)
                            continue
                        
                        # Send heartbeat
                        heartbeat_msg = WebSocketMessage(
                            message_id=str(uuid.uuid4()),
                            message_type="heartbeat",
                            timestamp=datetime.utcnow(),
                            payload={"connection_time": (datetime.utcnow() - connection.connected_at).total_seconds()}
                        )
                        
                        success = await self._send_message(conn_id, heartbeat_msg)
                        if not success:
                            logger.warning(f"Failed to send heartbeat to {conn_id}")
                            await self.connection_pool.remove_connection(conn_id)
                    
                    except Exception as e:
                        logger.error(f"Error sending heartbeat to {conn_id}: {e}")
            
            except Exception as e:
                logger.error(f"Error in heartbeat monitor: {e}")
    
    async def _cleanup_inactive_connections(self):
        """Periodically cleanup inactive connections"""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                # Find inactive connections
                now = datetime.utcnow()
                inactive_threshold = timedelta(minutes=30)
                
                for conn_id, connection in list(self.connection_pool.connections.items()):
                    if now - connection.last_activity > inactive_threshold:
                        logger.info(f"Removing inactive connection {conn_id}")
                        await self.connection_pool.remove_connection(conn_id)
            
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        total_connections = len(self.connection_pool.connections)
        connections_by_org = defaultdict(int)
        connections_by_user = defaultdict(int)
        total_subscriptions = len(self.subscriptions)
        
        for connection in self.connection_pool.connections.values():
            connections_by_org[connection.organization_id] += 1
            connections_by_user[connection.user_id] += 1
        
        return {
            "total_connections": total_connections,
            "connections_by_organization": dict(connections_by_org),
            "connections_by_user": dict(connections_by_user),
            "total_subscriptions": total_subscriptions,
            "active_event_queues": len(self.event_queues),
            "rate_limited_connections": len([
                c for c in self.message_counts
                if len(self.message_counts[c]) >= self.rate_limit_per_minute
            ])
        }


# Global instance
websocket_service = WebSocketService()