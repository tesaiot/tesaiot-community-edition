# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - WebSocket Telemetry Service
Enhanced real-time telemetry streaming with JWT authentication
"""

import asyncio
import json
import logging
import time
import jwt
from datetime import datetime
from typing import Dict, Set, Optional, Any
from collections import defaultdict, deque
from threading import Thread, Lock
import os

logger = logging.getLogger(__name__)

# Database imports (with error handling)
try:
    import pymongo
    from pymongo.change_stream import ChangeStream  # noqa: F401
    MONGODB_AVAILABLE = True
except ImportError:
    logger.warning("pymongo not available - MongoDB change streams disabled")
    MONGODB_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("redis not available - Redis caching disabled")
    REDIS_AVAILABLE = False

try:
    import psycopg2
    from psycopg2 import sql  # noqa: F401
    POSTGRES_AVAILABLE = True
except ImportError:
    logger.warning("psycopg2 not available - TimescaleDB polling disabled")
    POSTGRES_AVAILABLE = False

# WebSocket imports
from simple_websocket import Server, ConnectionClosed
from flask import request

# Flask-SocketIO removed from requirements (archived)
# Keep conditional import for backwards compatibility
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect  # noqa: F401
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    SocketIO = None  # type: ignore

class WebSocketTelemetryService:
    """
    Enhanced WebSocket telemetry service supporting:
    - 10,000+ concurrent connections
    - JWT authentication 
    - Real-time database change streaming
    - Rate limiting and abuse prevention
    - Both Socket.IO and native WebSocket protocols
    """
    
    def __init__(self, app=None):
        self.app = app
        
        # Connection management
        self.native_connections: Dict[str, Any] = {}
        self.socketio_connections: Dict[str, Any] = {}
        self.connection_lock = Lock()
        
        # Subscription management
        self.device_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self.user_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        
        # Rate limiting (per connection)
        self.rate_limiter: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.RATE_LIMIT_WINDOW = 60  # 1 minute
        self.RATE_LIMIT_MAX = 100    # Max 100 messages per minute per connection
        
        # Database connections
        self.mongo_client = None
        self.redis_client = None
        self.postgres_conn = None
        
        # Change streams
        self.mongo_change_stream = None
        self.timescale_polling_thread = None
        self.change_stream_thread = None
        self.running = False
        
        # JWT configuration
        # SECURITY: Fail closed. Never fall back to a public/default constant.
        self.jwt_secret = (
            os.getenv('JWT_SECRET_KEY')
            or os.getenv('JWT_SECRET')
            or os.getenv('SECRET_KEY')
        )
        if not self.jwt_secret or self.jwt_secret.startswith('CHANGEME'):
            raise RuntimeError(
                "WebSocketTelemetryService: JWT secret is not configured. "
                "Set JWT_SECRET_KEY (or JWT_SECRET / SECRET_KEY) to a strong value; "
                "CHANGEME* placeholders are rejected."
            )
        self.jwt_algorithm = 'HS256'
        
        # Message queue for broadcasting
        self.message_queue = asyncio.Queue() if hasattr(asyncio, 'Queue') else deque()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the service with Flask app"""
        self.app = app
        
        # Initialize database connections
        self._init_database_connections()
        
        # Start background services
        self._start_background_services()
        
        logger.info("WebSocket Telemetry Service initialized")
    
    def _init_database_connections(self):
        """Initialize database connections for change monitoring"""
        try:
            # MongoDB connection
            if MONGODB_AVAILABLE:
                mongo_uri = os.getenv('MONGODB_URI', 'mongodb://tesa-mongodb:27017/tesa_iot')
                self.mongo_client = pymongo.MongoClient(mongo_uri)
                logger.info("MongoDB connection initialized")
            else:
                logger.warning("MongoDB not available - change streams disabled")
            
            # Redis connection
            if REDIS_AVAILABLE:
                redis_host = os.getenv('REDIS_HOST', 'tesa-redis')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                logger.info("Redis connection initialized")
            else:
                logger.warning("Redis not available - caching disabled")
            
            # PostgreSQL/TimescaleDB connection
            if POSTGRES_AVAILABLE:
                postgres_config = {
                    'host': os.getenv('POSTGRES_HOST', 'tesa-timescaledb'),
                    'port': int(os.getenv('POSTGRES_PORT', 5432)),
                    'database': os.getenv('POSTGRES_DB', 'tesa_iot'),
                    'user': os.getenv('POSTGRES_USER', 'tesa_admin'),
                    'password': os.getenv('POSTGRES_PASSWORD', '')  # no default; fails closed
                }
                self.postgres_conn = psycopg2.connect(**postgres_config)
                logger.info("PostgreSQL/TimescaleDB connection initialized")
            else:
                logger.warning("PostgreSQL not available - TimescaleDB polling disabled")
            
            logger.info("Database connections initialized for telemetry streaming")
            
        except Exception as e:
            logger.error(f"Database connection initialization failed: {e}")
    
    def _start_background_services(self):
        """Start background threads for database monitoring"""
        if not self.running:
            self.running = True
            
            # Start MongoDB change stream monitoring (if available)
            if MONGODB_AVAILABLE and self.mongo_client:
                self.change_stream_thread = Thread(target=self._monitor_mongo_changes, daemon=True)
                self.change_stream_thread.start()
                logger.info("MongoDB change stream monitoring started")
            
            # Start TimescaleDB polling for telemetry updates (if available)
            if POSTGRES_AVAILABLE and self.postgres_conn:
                self.timescale_polling_thread = Thread(target=self._monitor_timescale_changes, daemon=True)
                self.timescale_polling_thread.start()
                logger.info("TimescaleDB polling monitoring started")
            
            logger.info("Background database monitoring services started")
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode and verify token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check token expiration
            if 'exp' in payload and payload['exp'] < time.time():
                logger.warning("JWT token expired")
                return None

            # Token revocation: reject blacklisted (logged-out/revoked) tokens,
            # mirroring core/auth.py so a WS connection cannot outlive a logout.
            # Infra blips skip the check (the subscribe-time org gate is the real
            # authorization boundary and is already fail-closed).
            if self.redis_client is not None:
                try:
                    if self.redis_client.get(f"blacklist_{token}"):
                        logger.warning("Rejected blacklisted WS token")
                        return None
                except Exception as e:
                    logger.error(f"WS blacklist check unavailable, skipping: {e}")

            # Account check: the user must still exist and not be deactivated.
            if self.mongo_client is not None:
                try:
                    query = ({'email': payload['email']} if payload.get('email')
                             else {'_id': payload.get('sub')})
                    user = self.mongo_client.tesa_iot.users.find_one(query)
                    if not user:
                        logger.warning("WS token for non-existent user")
                        return None
                    if str(user.get('status', '')).strip().lower() == 'inactive':
                        logger.warning("WS token for deactivated user")
                        return None
                except Exception as e:
                    logger.error(f"WS user-active check unavailable, skipping: {e}")

            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
        
        return None
    
    def _user_can_access_device(self, user_data: Dict[str, Any], device_id: str) -> bool:
        """
        Fail-closed per-device authorization for telemetry subscriptions.

        A token may only stream a device that belongs to the same organization
        encoded in the token. Platform admins are intentionally NOT granted
        customer device access (consistent with RBAC.get_devices_for_user).
        """
        if not user_data or not device_id:
            return False

        # Platform admins never stream customer device data.
        role = (user_data.get('role') or '').strip().lower()
        if role == 'platform_admin':
            logger.warning(
                "[SECURITY] platform_admin token attempted device subscription - DENIED "
                f"(device={device_id})"
            )
            return False

        token_org = (
            user_data.get('organization_id')
            or user_data.get('organization')
            or ''
        )
        token_org = str(token_org).strip()
        if not token_org:
            logger.warning(
                f"[SECURITY] device subscription denied: token has no organization (device={device_id})"
            )
            return False

        # Look up the device and verify it belongs to the token's organization.
        if not (MONGODB_AVAILABLE and self.mongo_client is not None):
            # No way to authorize -> fail closed.
            logger.error(
                "[SECURITY] device subscription denied: device registry unavailable for "
                f"ownership check (device={device_id})"
            )
            return False

        try:
            db = self.mongo_client.get_default_database()
            device = db['devices'].find_one(
                {'device_id': device_id},
                {'organization_id': 1, 'organization': 1}
            )
            if not device:
                logger.warning(
                    f"[SECURITY] device subscription denied: unknown device {device_id}"
                )
                return False

            device_orgs = {
                str(device.get('organization_id') or '').strip(),
                str(device.get('organization') or '').strip(),
            }
            device_orgs.discard('')

            if token_org in device_orgs:
                return True

            logger.warning(
                "[SECURITY] device subscription denied: cross-organization access "
                f"(device={device_id}, token_org={token_org})"
            )
            return False
        except Exception as e:
            # Fail closed on any lookup error.
            logger.error(f"[SECURITY] device ownership check failed for {device_id}: {e}")
            return False

    def is_rate_limited(self, connection_id: str) -> bool:
        """Check if connection is rate limited"""
        current_time = time.time()
        
        # Clean old entries
        rate_queue = self.rate_limiter[connection_id]
        while rate_queue and current_time - rate_queue[0] > self.RATE_LIMIT_WINDOW:
            rate_queue.popleft()
        
        # Check rate limit
        if len(rate_queue) >= self.RATE_LIMIT_MAX:
            logger.warning(f"Rate limit exceeded for connection {connection_id}")
            return True
        
        # Add current request
        rate_queue.append(current_time)
        return False
    
    # Native WebSocket Protocol Handler
    def handle_native_websocket(self):
        """Handle native WebSocket connections (browser WebSocket API)"""
        ws = Server.accept(request.environ)
        connection_id = None
        user_data = None
        
        try:
            # Authenticate connection
            auth_token = None
            
            # Try to get token from subprotocol (Bearer.token format)
            if hasattr(request, 'environ') and 'HTTP_SEC_WEBSOCKET_PROTOCOL' in request.environ:
                protocols = request.environ['HTTP_SEC_WEBSOCKET_PROTOCOL'].split(',')
                for protocol in protocols:
                    protocol = protocol.strip()
                    if protocol.startswith('Bearer.'):
                        auth_token = protocol[7:]  # Remove 'Bearer.' prefix
                        break
            
            # Try to get token from query parameters
            if not auth_token and hasattr(request, 'args'):
                auth_token = request.args.get('token')
            
            # Try to get token from headers
            if not auth_token and hasattr(request, 'headers'):
                auth_header = request.headers.get('Authorization', '')
                if auth_header.startswith('Bearer '):
                    auth_token = auth_header[7:]
            
            # Verify authentication
            if auth_token:
                user_data = self.verify_jwt_token(auth_token)
                if not user_data:
                    ws.send(json.dumps({
                        'type': 'error',
                        'message': 'Authentication failed',
                        'timestamp': datetime.utcnow().isoformat()
                    }))
                    ws.close()
                    return
            else:
                # Allow unauthenticated connections but with limited access
                logger.info("Unauthenticated WebSocket connection established")
            
            # Generate connection ID and register
            connection_id = f"native_{id(ws)}_{int(time.time())}"
            
            with self.connection_lock:
                self.native_connections[connection_id] = {
                    'ws': ws,
                    'user_data': user_data,
                    'subscriptions': set(),
                    'connected_at': datetime.utcnow(),
                    'last_activity': datetime.utcnow()
                }
            
            # Send connection confirmation
            ws.send(json.dumps({
                'type': 'connected',
                'connection_id': connection_id,
                'authenticated': user_data is not None,
                'user_id': user_data.get('sub') if user_data else None,
                'timestamp': datetime.utcnow().isoformat(),
                'server_info': {
                    'protocol': 'native_websocket',
                    'version': '1.0.0',
                    'features': ['telemetry_streaming', 'device_subscriptions', 'real_time_updates']
                }
            }))
            
            logger.info(f"Native WebSocket connected: {connection_id}, authenticated: {user_data is not None}")
            
            # Message handling loop
            while True:
                try:
                    # Check rate limiting
                    if self.is_rate_limited(connection_id):
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': 'Rate limit exceeded',
                            'timestamp': datetime.utcnow().isoformat()
                        }))
                        continue
                    
                    # Receive message
                    data = ws.receive(timeout=30.0)  # 30 second timeout
                    if data is None:
                        # Client closed connection
                        break
                    
                    # Parse and handle message
                    try:
                        message = json.loads(data)
                        self._handle_websocket_message(connection_id, message, 'native')
                    except json.JSONDecodeError:
                        ws.send(json.dumps({
                            'type': 'error',
                            'message': 'Invalid JSON format',
                            'timestamp': datetime.utcnow().isoformat()
                        }))
                    
                    # Update last activity
                    if connection_id in self.native_connections:
                        self.native_connections[connection_id]['last_activity'] = datetime.utcnow()
                        
                except ConnectionClosed:
                    logger.info(f"Native WebSocket connection closed: {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"Error in native WebSocket loop: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Native WebSocket error: {e}")
        
        finally:
            # Clean up connection
            if connection_id and connection_id in self.native_connections:
                with self.connection_lock:
                    # Unsubscribe from all devices
                    conn_data = self.native_connections[connection_id]
                    for device_id in conn_data['subscriptions']:
                        self.device_subscriptions[device_id].discard(connection_id)
                        if user_data:
                            self.user_subscriptions[user_data.get('sub', '')].discard(device_id)
                    
                    # Remove connection
                    del self.native_connections[connection_id]
                    
                    # Clean rate limiter
                    if connection_id in self.rate_limiter:
                        del self.rate_limiter[connection_id]
                
                logger.info(f"Native WebSocket disconnected and cleaned up: {connection_id}")
            
            ws.close()
        
        return ''
    
    def _handle_websocket_message(self, connection_id: str, message: Dict[str, Any], protocol: str):
        """Handle WebSocket message from client"""
        message_type = message.get('type', '')
        
        # Get connection data
        if protocol == 'native':
            conn_data = self.native_connections.get(connection_id)
            ws = conn_data['ws'] if conn_data else None
            send_func = lambda msg: ws.send(json.dumps(msg)) if ws else None
        else:
            # Socket.IO - implementation will be added
            return
        
        if not conn_data:
            logger.warning(f"Message from unknown connection: {connection_id}")
            return
        
        try:
            if message_type == 'ping':
                # Handle ping/keepalive
                send_func({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat(),
                    'echo': message.get('data')
                })
            
            elif message_type == 'subscribe':
                # Subscribe to device telemetry
                device_ids = message.get('deviceIds', [])
                if isinstance(device_ids, str):
                    device_ids = [device_ids]
                
                # Check authentication for device access
                user_data = conn_data['user_data']
                if user_data:
                    # SECURITY: enforce per-device org/ownership. A token must not
                    # be able to stream arbitrary device_ids.
                    granted = []
                    denied = []
                    for device_id in device_ids:
                        if self._user_can_access_device(user_data, device_id):
                            self.device_subscriptions[device_id].add(connection_id)
                            conn_data['subscriptions'].add(device_id)
                            self.user_subscriptions[user_data.get('sub', '')].add(device_id)
                            granted.append(device_id)
                        else:
                            denied.append(device_id)

                    send_func({
                        'type': 'subscribed',
                        'deviceIds': granted,
                        'deniedDeviceIds': denied,
                        'status': 'success' if granted and not denied else (
                            'partial' if granted else 'denied'
                        ),
                        'timestamp': datetime.utcnow().isoformat()
                    })

                    if denied:
                        logger.warning(
                            f"Connection {connection_id} denied subscription to devices: {denied}"
                        )
                    if granted:
                        logger.info(
                            f"Connection {connection_id} subscribed to devices: {granted}"
                        )
                else:
                    send_func({
                        'type': 'error',
                        'message': 'Authentication required for device subscriptions',
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            elif message_type == 'unsubscribe':
                # Unsubscribe from device telemetry
                device_ids = message.get('deviceIds', [])
                if isinstance(device_ids, str):
                    device_ids = [device_ids]
                
                user_data = conn_data['user_data']
                for device_id in device_ids:
                    self.device_subscriptions[device_id].discard(connection_id)
                    conn_data['subscriptions'].discard(device_id)
                    if user_data:
                        self.user_subscriptions[user_data.get('sub', '')].discard(device_id)
                
                send_func({
                    'type': 'unsubscribed',
                    'deviceIds': device_ids,
                    'status': 'success',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Connection {connection_id} unsubscribed from devices: {device_ids}")
            
            elif message_type == 'get_stats':
                # Return connection statistics
                send_func({
                    'type': 'stats',
                    'data': {
                        'active_connections': len(self.native_connections),
                        'device_subscriptions': len(self.device_subscriptions),
                        'total_subscriptions': sum(len(subs) for subs in self.device_subscriptions.values()),
                        'user_id': conn_data['user_data'].get('sub') if conn_data['user_data'] else None,
                        'connected_at': conn_data['connected_at'].isoformat(),
                        'subscribed_devices': list(conn_data['subscriptions'])
                    },
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            else:
                send_func({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            if send_func:
                send_func({
                    'type': 'error',
                    'message': 'Internal server error',
                    'timestamp': datetime.utcnow().isoformat()
                })
    
    def broadcast_telemetry(self, device_id: str, telemetry_data: Dict[str, Any], source: str = 'unknown'):
        """Broadcast telemetry data to subscribed connections"""
        if not self.device_subscriptions.get(device_id):
            return  # No subscribers for this device
        
        message = {
            'type': 'device_telemetry',
            'deviceId': device_id,
            'data': telemetry_data,
            'source': source,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        json_message = json.dumps(message)
        disconnected_connections = []
        
        # Broadcast to native WebSocket connections
        with self.connection_lock:
            for connection_id in self.device_subscriptions[device_id].copy():
                if connection_id in self.native_connections:
                    try:
                        ws = self.native_connections[connection_id]['ws']
                        ws.send(json_message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            self._cleanup_connection(conn_id)
        
        logger.debug(f"Broadcasted telemetry for device {device_id} to {len(self.device_subscriptions[device_id])} subscribers")
    
    def broadcast_system_metrics(self, metrics: Dict[str, Any]):
        """Broadcast system metrics to all authenticated connections"""
        message = {
            'type': 'metrics_update',
            'data': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        json_message = json.dumps(message)
        disconnected_connections = []
        
        # Broadcast to all authenticated native connections
        with self.connection_lock:
            for connection_id, conn_data in self.native_connections.items():
                if conn_data['user_data']:  # Only send to authenticated connections
                    try:
                        ws = conn_data['ws']
                        ws.send(json_message)
                    except Exception as e:
                        logger.error(f"Error broadcasting metrics to {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for conn_id in disconnected_connections:
            self._cleanup_connection(conn_id)
    
    def _cleanup_connection(self, connection_id: str):
        """Clean up a disconnected connection"""
        with self.connection_lock:
            if connection_id in self.native_connections:
                conn_data = self.native_connections[connection_id]
                
                # Unsubscribe from all devices
                for device_id in conn_data['subscriptions']:
                    self.device_subscriptions[device_id].discard(connection_id)
                
                # Remove from user subscriptions
                if conn_data['user_data']:
                    user_id = conn_data['user_data'].get('sub', '')
                    for device_id in conn_data['subscriptions']:
                        self.user_subscriptions[user_id].discard(device_id)
                
                # Remove connection
                del self.native_connections[connection_id]
                
                # Clean rate limiter
                if connection_id in self.rate_limiter:
                    del self.rate_limiter[connection_id]
                
                logger.info(f"Cleaned up connection: {connection_id}")
    
    def _monitor_mongo_changes(self):
        """Monitor MongoDB changes for real-time updates"""
        while self.running:
            try:
                if not self.mongo_client:
                    logger.warning("MongoDB client not available, retrying in 5 seconds")
                    time.sleep(5)
                    continue
                
                # Monitor telemetry collection changes
                db = self.mongo_client.tesa_iot
                collection = db.telemetry
                
                # Create change stream
                change_stream = collection.watch([
                    {'$match': {'operationType': 'insert'}}
                ], full_document='updateLookup')
                
                logger.info("MongoDB change stream started for telemetry collection")
                
                for change in change_stream:
                    if not self.running:
                        break
                    
                    # Process telemetry insert
                    if change['operationType'] == 'insert':
                        document = change['fullDocument']
                        device_id = document.get('device_id')
                        
                        if device_id and device_id in self.device_subscriptions:
                            # Broadcast telemetry data
                            telemetry_data = {
                                'timestamp': document.get('timestamp'),
                                'data': document.get('data', {}),
                                'location': document.get('location'),
                                'metadata': document.get('metadata', {})
                            }
                            
                            self.broadcast_telemetry(device_id, telemetry_data, source='mongodb')
                
            except Exception as e:
                logger.error(f"MongoDB change stream error: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _monitor_timescale_changes(self):
        """Monitor TimescaleDB for recent telemetry updates (polling-based)"""
        last_check = datetime.utcnow()
        
        while self.running:
            try:
                if not self.postgres_conn:
                    logger.warning("PostgreSQL connection not available, retrying in 10 seconds")
                    time.sleep(10)
                    continue
                
                # Query for recent telemetry data
                # Updated 2026-01-24: Uses device_telemetry table with normalized schema
                # Aggregates metric_name/metric_value pairs into JSON data object
                current_time = datetime.utcnow()

                with self.postgres_conn.cursor() as cursor:
                    query = """
                    SELECT
                        device_id,
                        time as timestamp,
                        jsonb_object_agg(metric_name, metric_value) as data,
                        MAX(location) as location
                    FROM device_telemetry
                    WHERE time > %s
                    GROUP BY device_id, time
                    ORDER BY time DESC
                    LIMIT 1000
                    """

                    cursor.execute(query, (last_check,))
                    rows = cursor.fetchall()

                    for row in rows:
                        device_id, timestamp, data, location = row

                        if device_id in self.device_subscriptions:
                            # Broadcast telemetry data
                            telemetry_data = {
                                'timestamp': timestamp.isoformat() if timestamp else None,
                                'data': data if isinstance(data, dict) else {},
                                'location': location if isinstance(location, dict) else None
                            }

                            self.broadcast_telemetry(device_id, telemetry_data, source='timescaledb')
                
                last_check = current_time
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"TimescaleDB polling error: {e}")
                time.sleep(10)  # Wait before retrying
                
                # Reconnect if connection lost
                try:
                    if self.postgres_conn:
                        self.postgres_conn.rollback()
                except:
                    pass
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics"""
        with self.connection_lock:
            return {
                'active_connections': {
                    'native_websocket': len(self.native_connections),
                    'socketio': len(self.socketio_connections),
                    'total': len(self.native_connections) + len(self.socketio_connections)
                },
                'device_subscriptions': len(self.device_subscriptions),
                'total_subscriptions': sum(len(subs) for subs in self.device_subscriptions.values()),
                'most_subscribed_devices': [
                    {'device_id': device_id, 'subscribers': len(subs)} 
                    for device_id, subs in sorted(
                        self.device_subscriptions.items(), 
                        key=lambda x: len(x[1]), 
                        reverse=True
                    )[:10]
                ],
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def shutdown(self):
        """Gracefully shutdown the service"""
        logger.info("Shutting down WebSocket Telemetry Service...")
        
        self.running = False
        
        # Close all connections
        with self.connection_lock:
            for connection_id, conn_data in self.native_connections.items():
                try:
                    ws = conn_data['ws']
                    ws.send(json.dumps({
                        'type': 'server_shutdown',
                        'message': 'Server is shutting down',
                        'timestamp': datetime.utcnow().isoformat()
                    }))
                    ws.close()
                except:
                    pass
        
        # Close database connections
        if self.mongo_client:
            self.mongo_client.close()
        
        if self.redis_client:
            self.redis_client.close()
        
        if self.postgres_conn:
            self.postgres_conn.close()
        
        logger.info("WebSocket Telemetry Service shutdown completed")

# Global service instance
websocket_telemetry_service = None

def init_websocket_telemetry_service(app):
    """Initialize the WebSocket telemetry service"""
    global websocket_telemetry_service
    
    if not websocket_telemetry_service:
        websocket_telemetry_service = WebSocketTelemetryService(app)
    
    return websocket_telemetry_service

def get_websocket_telemetry_service():
    """Get the global WebSocket telemetry service instance"""
    return websocket_telemetry_service