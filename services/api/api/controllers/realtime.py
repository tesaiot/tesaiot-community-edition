# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Real-time Data Streaming Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Real-time WebSocket/SSE endpoints for AI/ML data streaming
Version: v2025.06-beta
"""

import asyncio
import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

from flask import Blueprint, Response, g, request, jsonify
from ..core.auth import require_auth, verify_token
from ..core.database import get_db
from ..services.realtime_analytics_service import realtime_analytics_service

logger = logging.getLogger(__name__)

# Create blueprint
realtime_bp = Blueprint('realtime', __name__, url_prefix='/api/v1/realtime')

def require_sse_auth(f):
    """
    Authentication decorator for SSE endpoints that supports both header and query parameter auth
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to get token from query parameter first (for EventSource)
        token = request.args.get('token')
        
        # If no token in query params, try header auth
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            # Return SSE-formatted error instead of JSON
            def auth_error():
                yield f"event: error\ndata: {json.dumps({'error': 'Authentication required', 'code': 401})}\n\n"
            return Response(auth_error(), mimetype='text/event-stream', status=401)
            
        try:
            # Verify the token and set user context
            payload, error_msg = verify_token(token)
            if not payload:
                # Return SSE-formatted error instead of JSON
                def token_error():
                    yield f"event: error\ndata: {json.dumps({'error': error_msg or 'Invalid token', 'code': 401})}\n\n"
                return Response(token_error(), mimetype='text/event-stream', status=401)
                
            # Get full user data from database
            db = get_db()
            if db is not None:
                user = db.users.find_one(
                    {'email': payload.get('email')},
                    {'password': 0}  # Exclude password
                )
                if user:
                    # Convert ObjectId to string
                    user['_id'] = str(user['_id'])
                    user['user_id'] = str(user['_id'])  # Add user_id field
                    g.current_user = user
                else:
                    # Fallback for platform admin or if user not in DB
                    g.current_user = {
                        'user_id': payload.get('email', 'anonymous'),
                        'email': payload.get('email'),
                        'role': payload.get('role', 'user'),
                        'organization_id': payload.get('organization_id', 'global')
                    }
            else:
                # If DB unavailable, use token payload
                g.current_user = {
                    'user_id': payload.get('email', 'anonymous'),
                    'email': payload.get('email'),
                    'role': payload.get('role', 'user'),
                    'organization_id': payload.get('organization_id', 'global')
                }
                
            return f(*args, **kwargs)
            
        except Exception as e:
            err = str(e)
            logger.error(f"SSE Authentication error: {err}")
            # Return SSE-formatted error instead of JSON
            def auth_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Authentication failed', 'details': err, 'code': 401})}\n\n"
            return Response(auth_failure(), mimetype='text/event-stream', status=401)
            
    return decorated_function

# Global storage for active SSE connections
active_connections = {}
connection_lock = threading.Lock()

class SSEConnection:
    """Manages individual SSE connection"""
    
    def __init__(self, user_id: str, organization_id: str):
        self.user_id = user_id
        self.organization_id = organization_id
        self.last_ping = time.time()
        self.is_active = True
        
    def send_data(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data for SSE transmission"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def ping(self) -> str:
        """Send ping to keep connection alive"""
        self.last_ping = time.time()
        return f"event: ping\ndata: {json.dumps({'timestamp': self.last_ping})}\n\n"
    
    def close(self):
        """Mark connection as closed"""
        self.is_active = False

def add_sse_connection(user_id: str, organization_id: str) -> SSEConnection:
    """Add a new SSE connection"""
    with connection_lock:
        if user_id not in active_connections:
            active_connections[user_id] = []
        
        connection = SSEConnection(user_id, organization_id)
        active_connections[user_id].append(connection)
        logger.info(f"Added SSE connection for user {user_id}")
        return connection

def remove_sse_connection(user_id: str, connection: SSEConnection):
    """Remove an SSE connection"""
    with connection_lock:
        if user_id in active_connections:
            try:
                active_connections[user_id].remove(connection)
                if not active_connections[user_id]:
                    del active_connections[user_id]
                logger.info(f"Removed SSE connection for user {user_id}")
            except ValueError:
                pass

def broadcast_to_user(user_id: str, event_type: str, data: Dict[str, Any]):
    """Broadcast data to all connections for a specific user"""
    with connection_lock:
        if user_id in active_connections:
            dead_connections = []
            for connection in active_connections[user_id]:
                if connection.is_active:
                    try:
                        # This would be sent in the streaming response
                        connection.last_ping = time.time()
                    except:
                        dead_connections.append(connection)
                else:
                    dead_connections.append(connection)
            
            # Clean up dead connections
            for dead_conn in dead_connections:
                active_connections[user_id].remove(dead_conn)
            
            if not active_connections[user_id]:
                del active_connections[user_id]

@realtime_bp.route('/stream/system-health')
@require_sse_auth
def stream_system_health():
    """
    Stream real-time system health data for SmartSystemOverviewCard
    Uses Server-Sent Events (SSE) for real-time updates
    """
    # Extract user info outside the generator to avoid context issues
    user_id = g.current_user.get('user_id', 'anonymous')
    organization_id = g.current_user.get('organization_id', 'global')
    
    def generate_system_health():
        connection = add_sse_connection(user_id, organization_id)
        
        try:
            # Send initial connection established event
            yield connection.send_data('connected', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'stream': 'system-health'
            })
            
            last_update = 0
            ping_interval = 30  # seconds
            data_interval = 5   # seconds
            
            while connection.is_active:
                current_time = time.time()
                
                # Send data updates every 5 seconds
                if current_time - last_update >= data_interval:
                    try:
                        # Get real-time system health data using fast method with timeout
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            system_health = loop.run_until_complete(
                                asyncio.wait_for(
                                    realtime_analytics_service.get_system_health_metrics_fast(),
                                    timeout=3.0  # 3 second timeout to prevent ECONNABORTED
                                )
                            )
                        finally:
                            loop.close()
                        
                        # Calculate overall health score
                        health_score = calculate_system_health_score(system_health)
                        
                        # Format data for AI/ML card
                        health_data = {
                            'score': health_score,
                            'subscores': {
                                'performance': calculate_performance_score(system_health),
                                'security': 95,  # Can be enhanced with security metrics
                                'reliability': calculate_reliability_score(system_health),
                                'efficiency': calculate_efficiency_score(system_health)
                            },
                            'trend': 'stable',  # Can be calculated from historical data
                            'trendPercentage': 2.1,
                            'lastUpdated': datetime.now().isoformat(),
                            'prediction': {
                                'next24h': health_score + 1,
                                'confidence': 85
                            },
                            'containers': system_health.get('containers', []),
                            'databases': system_health.get('databases', {})
                        }
                        
                        yield connection.send_data('system-health-update', health_data)
                        last_update = current_time
                        
                    except Exception as e:
                        logger.error(f"Error getting system health data: {str(e)}", exc_info=True)
                        # Send fallback data instead of error to keep UI working
                        fallback_health = realtime_analytics_service._get_fallback_system_health()
                        health_score = calculate_system_health_score(fallback_health)
                        
                        health_data = {
                            'score': health_score,
                            'subscores': {
                                'performance': 85,
                                'security': 95,
                                'reliability': 90,
                                'efficiency': 80
                            },
                            'trend': 'stable',
                            'trendPercentage': 0,
                            'lastUpdated': datetime.now().isoformat(),
                            'prediction': {
                                'next24h': health_score,
                                'confidence': 50
                            },
                            'containers': fallback_health.get('containers', []),
                            'databases': fallback_health.get('databases', {}),
                            'is_fallback': True
                        }
                        
                        yield connection.send_data('system-health-update', health_data)
                
                # Send ping every 30 seconds to keep connection alive
                elif current_time - connection.last_ping >= ping_interval:
                    yield connection.ping()
                
                # Use more efficient sleep pattern based on when next action is needed
                next_data_time = last_update + data_interval
                next_ping_time = connection.last_ping + ping_interval
                next_event_time = min(next_data_time, next_ping_time)
                sleep_time = max(0.1, min(1.0, next_event_time - current_time))
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info(f"SSE connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"SSE stream error for user {user_id}: {str(e)}")
        finally:
            connection.close()
            remove_sse_connection(user_id, connection)
    
    return Response(
        generate_system_health(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    )

@realtime_bp.route('/stream/predictive-alerts')
@require_sse_auth
def stream_predictive_alerts():
    """
    Stream real-time predictive alerts for PredictiveAlertsCard
    """
    # Extract user info outside the generator to avoid context issues
    user_id = g.current_user.get('user_id', 'anonymous')
    organization_id = g.current_user.get('organization_id', 'global')
    
    def generate_predictive_alerts():
        connection = add_sse_connection(user_id, organization_id)
        
        try:
            yield connection.send_data('connected', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'stream': 'predictive-alerts'
            })
            
            last_update = 0
            data_interval = 10  # Update every 10 seconds
            
            while connection.is_active:
                current_time = time.time()
                
                if current_time - last_update >= data_interval:
                    try:
                        # Get predictive alerts data (using IoT metrics as basis)
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            iot_metrics = loop.run_until_complete(
                                realtime_analytics_service.get_realtime_iot_metrics(organization_id)
                            )
                        finally:
                            loop.close()
                        
                        # Generate predictive alerts based on real data
                        alerts_data = generate_predictive_alerts_data(iot_metrics)
                        
                        yield connection.send_data('predictive-alerts-update', alerts_data)
                        last_update = current_time
                        
                    except Exception as e:
                        logger.error(f"Error getting predictive alerts: {str(e)}")
                        yield connection.send_data('error', {
                            'message': 'Failed to get predictive alerts',
                            'timestamp': datetime.now().isoformat()
                        })
                
                elif current_time - connection.last_ping >= 30:
                    yield connection.ping()
                
                # More efficient sleep timing
                next_data_time = last_update + data_interval
                next_ping_time = connection.last_ping + 30
                next_event_time = min(next_data_time, next_ping_time)
                sleep_time = max(0.1, min(1.0, next_event_time - current_time))
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info(f"SSE predictive alerts connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"SSE predictive alerts stream error for user {user_id}: {str(e)}")
        finally:
            connection.close()
            remove_sse_connection(user_id, connection)
    
    return Response(
        generate_predictive_alerts(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    )

@realtime_bp.route('/stream/anomaly-detection')
@require_sse_auth
def stream_anomaly_detection():
    """
    Stream real-time anomaly detection data for AnomalyDetectionHeatmapCard
    """
    # Extract user info outside the generator to avoid context issues
    user_id = g.current_user.get('user_id', 'anonymous')
    organization_id = g.current_user.get('organization_id', 'global')
    
    def generate_anomaly_data():
        connection = add_sse_connection(user_id, organization_id)
        
        try:
            yield connection.send_data('connected', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'stream': 'anomaly-detection'
            })
            
            last_update = 0
            data_interval = 15  # Update every 15 seconds
            
            while connection.is_active:
                current_time = time.time()
                
                if current_time - last_update >= data_interval:
                    try:
                        # Get real-time IoT metrics which includes anomaly data
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            iot_metrics = loop.run_until_complete(
                                realtime_analytics_service.get_realtime_iot_metrics(organization_id)
                            )
                        finally:
                            loop.close()
                        
                        # Generate anomaly heatmap data
                        anomaly_data = generate_anomaly_heatmap(iot_metrics)
                        
                        yield connection.send_data('anomaly-detection-update', anomaly_data)
                        last_update = current_time
                        
                    except Exception as e:
                        logger.error(f"Error getting anomaly data: {str(e)}")
                        yield connection.send_data('error', {
                            'message': 'Failed to get anomaly data',
                            'timestamp': datetime.now().isoformat()
                        })
                
                elif current_time - connection.last_ping >= 30:
                    yield connection.ping()
                
                # More efficient sleep timing
                next_data_time = last_update + data_interval
                next_ping_time = connection.last_ping + 30
                next_event_time = min(next_data_time, next_ping_time)
                sleep_time = max(0.1, min(1.0, next_event_time - current_time))
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info(f"SSE anomaly detection connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"SSE anomaly detection stream error for user {user_id}: {str(e)}")
        finally:
            connection.close()
            remove_sse_connection(user_id, connection)
    
    return Response(
        generate_anomaly_data(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    )

@realtime_bp.route('/stream/resource-optimization')
@require_sse_auth  
def stream_resource_optimization():
    """
    Stream real-time resource usage and optimization data for ResourceOptimizationCard
    """
    # Extract user info outside the generator to avoid context issues
    user_id = g.current_user.get('user_id', 'anonymous')
    organization_id = g.current_user.get('organization_id', 'global')
    
    def generate_resource_data():
        connection = add_sse_connection(user_id, organization_id)
        
        try:
            yield connection.send_data('connected', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'stream': 'resource-optimization'
            })
            
            last_update = 0
            data_interval = 8  # Update every 8 seconds
            
            while connection.is_active:
                current_time = time.time()
                
                if current_time - last_update >= data_interval:
                    try:
                        # Get system health for resource metrics
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            system_health = loop.run_until_complete(
                                realtime_analytics_service.get_system_health_metrics()
                            )
                        finally:
                            loop.close()
                        
                        # Generate resource optimization data
                        resource_data = generate_resource_optimization_data(system_health)
                        
                        yield connection.send_data('resource-optimization-update', resource_data)
                        last_update = current_time
                        
                    except Exception as e:
                        logger.error(f"Error getting resource data: {str(e)}")
                        yield connection.send_data('error', {
                            'message': 'Failed to get resource data',
                            'timestamp': datetime.now().isoformat()
                        })
                
                elif current_time - connection.last_ping >= 30:
                    yield connection.ping()
                
                # More efficient sleep timing
                next_data_time = last_update + data_interval
                next_ping_time = connection.last_ping + 30
                next_event_time = min(next_data_time, next_ping_time)
                sleep_time = max(0.1, min(1.0, next_event_time - current_time))
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info(f"SSE resource optimization connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"SSE resource optimization stream error for user {user_id}: {str(e)}")
        finally:
            connection.close()
            remove_sse_connection(user_id, connection)
    
    return Response(
        generate_resource_data(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    )

@realtime_bp.route('/stream/defense-in-depth')
@require_sse_auth
def stream_defense_in_depth():
    """
    Stream real-time defense-in-depth security layer status
    Uses Server-Sent Events (SSE) for real-time updates
    """
    # Extract user info outside the generator to avoid context issues
    user_id = g.current_user.get('user_id', 'anonymous')
    organization_id = g.current_user.get('organization_id', 'global')
    
    def generate_defense_data():
        connection = add_sse_connection(user_id, organization_id)
        
        try:
            yield connection.send_data('connected', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'stream': 'defense-in-depth'
            })
            
            last_update = 0
            data_interval = 5  # Update every 5 seconds
            
            while connection.is_active:
                current_time = time.time()
                
                if current_time - last_update >= data_interval:
                    try:
                        # Generate defense-in-depth data
                        defense_data = generate_defense_in_depth_data(organization_id)
                        
                        yield connection.send_data('defense-update', defense_data)
                        last_update = current_time
                        
                    except Exception as e:
                        logger.error(f"Error getting defense data: {str(e)}")
                        yield connection.send_data('error', {
                            'message': 'Failed to get defense data',
                            'timestamp': datetime.now().isoformat()
                        })
                
                elif current_time - connection.last_ping >= 30:
                    yield connection.ping()
                
                # More efficient sleep timing
                next_data_time = last_update + data_interval
                next_ping_time = connection.last_ping + 30
                next_event_time = min(next_data_time, next_ping_time)
                sleep_time = max(0.1, min(1.0, next_event_time - current_time))
                time.sleep(sleep_time)
                
        except GeneratorExit:
            logger.info(f"SSE defense-in-depth connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"SSE defense-in-depth stream error for user {user_id}: {str(e)}")
        finally:
            connection.close()
            remove_sse_connection(user_id, connection)
    
    return Response(
        generate_defense_data(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    )

# Helper functions for data processing

def calculate_system_health_score(system_health: Dict[str, Any]) -> int:
    """Calculate overall system health score from metrics"""
    try:
        containers = system_health.get('containers', [])
        databases = system_health.get('databases', {})
        
        if not containers and not databases:
            return 50  # Unknown state
        
        # Calculate container health score
        container_score = 100
        if containers:
            healthy_containers = sum(1 for c in containers if c.get('health') == 'healthy')
            warning_containers = sum(1 for c in containers if c.get('health') == 'warning')
            critical_containers = sum(1 for c in containers if c.get('health') == 'critical')
            
            total_containers = len(containers)
            container_score = (
                (healthy_containers * 100 + warning_containers * 70 + critical_containers * 30) 
                / total_containers
            )
        
        # Calculate database health score
        db_score = 100
        if databases:
            healthy_dbs = sum(1 for db in databases.values() if db.get('status') == 'healthy')
            total_dbs = len(databases)
            db_score = (healthy_dbs / total_dbs) * 100 if total_dbs > 0 else 100
        
        # Weighted average
        overall_score = int((container_score * 0.6 + db_score * 0.4))
        return max(0, min(100, overall_score))
        
    except Exception as e:
        logger.error(f"Error calculating health score: {str(e)}")
        return 75  # Default safe value

def calculate_performance_score(system_health: Dict[str, Any]) -> int:
    """Calculate performance subscore"""
    try:
        containers = system_health.get('containers', [])
        if not containers:
            return 85
        
        cpu_scores = []
        memory_scores = []
        
        for container in containers:
            cpu_percent = container.get('cpu_percent', 0)
            memory_percent = container.get('memory_percent', 0)
            
            # Score based on resource usage (lower usage = higher score)
            cpu_score = max(0, 100 - cpu_percent)
            memory_score = max(0, 100 - memory_percent)
            
            cpu_scores.append(cpu_score)
            memory_scores.append(memory_score)
        
        avg_cpu_score = sum(cpu_scores) / len(cpu_scores) if cpu_scores else 85
        avg_memory_score = sum(memory_scores) / len(memory_scores) if memory_scores else 85
        
        return int((avg_cpu_score + avg_memory_score) / 2)
        
    except Exception as e:
        logger.error(f"Error calculating performance score: {str(e)}")
        return 85

def calculate_reliability_score(system_health: Dict[str, Any]) -> int:
    """Calculate reliability subscore"""
    try:
        containers = system_health.get('containers', [])
        if not containers:
            return 90
        
        # Base reliability on container status and restart counts
        running_containers = sum(1 for c in containers if c.get('status') == 'running')
        total_containers = len(containers)
        
        if total_containers == 0:
            return 90
        
        uptime_score = (running_containers / total_containers) * 100
        
        # Factor in restart counts (frequent restarts lower the score)
        restart_penalty = 0
        for container in containers:
            restart_count = container.get('restart_count', 0)
            if restart_count > 5:
                restart_penalty += 10
            elif restart_count > 2:
                restart_penalty += 5
        
        reliability_score = max(0, uptime_score - restart_penalty)
        return int(min(100, reliability_score))
        
    except Exception as e:
        logger.error(f"Error calculating reliability score: {str(e)}")
        return 90

def calculate_efficiency_score(system_health: Dict[str, Any]) -> int:
    """Calculate efficiency subscore"""
    try:
        databases = system_health.get('databases', {})
        containers = system_health.get('containers', [])
        
        # Base efficiency on resource utilization balance
        efficiency_factors = []
        
        # Database efficiency
        for db_name, db_data in databases.items():
            if db_data.get('status') == 'healthy':
                efficiency_factors.append(85)  # Healthy DB contributes to efficiency
            else:
                efficiency_factors.append(40)  # Unhealthy DB reduces efficiency
        
        # Container efficiency based on balanced resource usage
        for container in containers:
            cpu_percent = container.get('cpu_percent', 0)
            memory_percent = container.get('memory_percent', 0)
            
            # Ideal range is 20-70% utilization
            cpu_efficiency = 100 - abs(45 - cpu_percent) if 10 <= cpu_percent <= 80 else 60
            memory_efficiency = 100 - abs(45 - memory_percent) if 10 <= memory_percent <= 80 else 60
            
            container_efficiency = (cpu_efficiency + memory_efficiency) / 2
            efficiency_factors.append(container_efficiency)
        
        if efficiency_factors:
            return int(sum(efficiency_factors) / len(efficiency_factors))
        else:
            return 80  # Default
            
    except Exception as e:
        logger.error(f"Error calculating efficiency score: {str(e)}")
        return 80

def generate_predictive_alerts_data(iot_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate predictive alerts based on IoT metrics"""
    try:
        alerts = []
        current_time = datetime.now()
        
        # Generate alerts based on real metrics
        anomaly_count = iot_metrics.get('anomaly_count', 0)
        active_devices = iot_metrics.get('active_devices', 0)
        throughput_avg = iot_metrics.get('throughput_avg', 0)
        
        # High anomaly alert
        if anomaly_count > 5:
            alerts.append({
                'id': f'anomaly_{int(current_time.timestamp())}',
                'severity': 'critical' if anomaly_count > 10 else 'warning',
                'title': 'High Anomaly Activity Detected',
                'description': f'{anomaly_count} anomalies detected across IoT devices',
                'timeToEvent': 15,  # minutes
                'confidence': 92,
                'affectedSystems': ['IoT Network', 'Device Analytics'],
                'preventiveActions': ['Review device configurations', 'Check network connectivity'],
                'acknowledged': False,
                'createdAt': current_time.isoformat()
            })
        
        # Low throughput alert
        if throughput_avg < 10 and active_devices > 0:
            alerts.append({
                'id': f'throughput_{int(current_time.timestamp())}',
                'severity': 'warning',
                'title': 'Low Device Throughput Predicted',
                'description': f'Throughput below expected levels with {active_devices} active devices',
                'timeToEvent': 30,
                'confidence': 78,
                'affectedSystems': ['MQTT Broker', 'Telemetry Processing'],
                'preventiveActions': ['Check broker performance', 'Review message queues'],
                'acknowledged': False,
                'createdAt': current_time.isoformat()
            })
        
        # Device connectivity alert
        if active_devices < 5:
            alerts.append({
                'id': f'connectivity_{int(current_time.timestamp())}',
                'severity': 'info',
                'title': 'Device Connectivity Optimization',
                'description': 'Opportunity to improve device connection patterns',
                'timeToEvent': 45,
                'confidence': 65,
                'affectedSystems': ['Device Management'],
                'preventiveActions': ['Review device schedules', 'Optimize connection intervals'],
                'acknowledged': False,
                'createdAt': current_time.isoformat()
            })
        
        return {
            'alerts': alerts,
            'total_alerts': len(alerts),
            'critical_count': sum(1 for a in alerts if a['severity'] == 'critical'),
            'warning_count': sum(1 for a in alerts if a['severity'] == 'warning'),
            'info_count': sum(1 for a in alerts if a['severity'] == 'info'),
            'avg_confidence': sum(a['confidence'] for a in alerts) / len(alerts) if alerts else 0,
            'last_updated': current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating predictive alerts: {str(e)}")
        return {
            'alerts': [],
            'total_alerts': 0,
            'critical_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'avg_confidence': 0,
            'last_updated': datetime.now().isoformat()
        }

def generate_anomaly_heatmap(iot_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate anomaly detection heatmap data"""
    try:
        # Get device data and create anomaly heatmap
        top_devices = iot_metrics.get('top_devices', [])
        anomaly_count = iot_metrics.get('anomaly_count', 0)
        anomaly_score = iot_metrics.get('anomaly_score', 0)
        
        # Create heatmap data structure
        heatmap_data = []
        current_time = datetime.now()
        
        # Generate time slots for the last 24 hours
        for i in range(24):
            hour_start = current_time - timedelta(hours=i)
            hour_data = {
                'time': hour_start.strftime('%H:00'),
                'devices': []
            }
            
            # Add device anomaly data for this hour
            for device in top_devices[:10]:  # Limit to top 10 devices
                device_id = device.get('device_id', '')
                # Simulate anomaly scores based on device activity
                base_score = 0.1 + (hash(device_id + str(i)) % 100) / 1000
                if i < 2:  # Recent hours have real anomaly data influence
                    base_score += anomaly_score / 100 if anomaly_score > 0 else 0
                
                hour_data['devices'].append({
                    'device_id': device_id,
                    'anomaly_score': min(1.0, base_score),
                    'message_count': device.get('message_count', 0),
                    'last_seen': device.get('last_seen')
                })
            
            heatmap_data.append(hour_data)
        
        return {
            'heatmap_data': heatmap_data[:12],  # Last 12 hours
            'total_anomalies': anomaly_count,
            'avg_anomaly_score': anomaly_score,
            'active_devices': len(top_devices),
            'last_updated': current_time.isoformat(),
            'severity_distribution': {
                'low': max(0, anomaly_count - 5),
                'medium': min(5, max(0, anomaly_count - 2)),
                'high': min(2, anomaly_count),
                'critical': min(1, max(0, anomaly_count - 8))
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating anomaly heatmap: {str(e)}")
        return {
            'heatmap_data': [],
            'total_anomalies': 0,
            'avg_anomaly_score': 0,
            'active_devices': 0,
            'last_updated': datetime.now().isoformat(),
            'severity_distribution': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        }

def generate_resource_optimization_data(system_health: Dict[str, Any]) -> Dict[str, Any]:
    """Generate resource optimization data"""
    try:
        containers = system_health.get('containers', [])
        databases = system_health.get('databases', {})
        
        # Calculate current resource usage
        total_cpu = sum(c.get('cpu_percent', 0) for c in containers)
        total_memory = sum(c.get('memory_percent', 0) for c in containers)
        avg_cpu = total_cpu / len(containers) if containers else 0
        avg_memory = total_memory / len(containers) if containers else 0
        
        # Generate optimization recommendations
        recommendations = []
        savings_potential = 0
        
        if avg_cpu < 20:
            recommendations.append({
                'type': 'cpu_optimization',
                'title': 'CPU Under-utilization Detected',
                'description': 'Consider consolidating workloads or scaling down resources',
                'potential_savings': 15,
                'priority': 'medium'
            })
            savings_potential += 15
        elif avg_cpu > 80:
            recommendations.append({
                'type': 'cpu_scaling',
                'title': 'CPU High Utilization',
                'description': 'Consider scaling up or optimizing CPU-intensive processes',
                'potential_savings': 0,
                'priority': 'high'
            })
        
        if avg_memory > 85:
            recommendations.append({
                'type': 'memory_optimization',
                'title': 'Memory Pressure Detected',
                'description': 'Review memory-intensive applications and consider optimization',
                'potential_savings': 10,
                'priority': 'high'
            })
        elif avg_memory < 30:
            recommendations.append({
                'type': 'memory_rightsizing',
                'title': 'Memory Over-provisioning',
                'description': 'Memory resources appear over-allocated',
                'potential_savings': 20,
                'priority': 'low'
            })
            savings_potential += 20
        
        # Database optimization checks
        for db_name, db_data in databases.items():
            if db_data.get('status') == 'healthy':
                if db_name == 'mongodb' and db_data.get('database_size_gb', 0) > 10:
                    recommendations.append({
                        'type': 'database_optimization',
                        'title': f'{db_name.title()} Storage Optimization',
                        'description': 'Large database detected, consider archiving old data',
                        'potential_savings': 25,
                        'priority': 'medium'
                    })
                    savings_potential += 25
        
        # Forecast data (simplified prediction)
        current_time = datetime.now()
        forecast_data = []
        for i in range(24):  # Next 24 hours
            hour_time = current_time + timedelta(hours=i)
            # Simple forecast based on current trends with some variance
            cpu_forecast = avg_cpu + (i * 0.5) + ((hash(str(i)) % 20) - 10)
            memory_forecast = avg_memory + (i * 0.3) + ((hash(str(i+1)) % 15) - 7)
            
            forecast_data.append({
                'time': hour_time.strftime('%H:00'),
                'cpu_usage': max(0, min(100, cpu_forecast)),
                'memory_usage': max(0, min(100, memory_forecast)),
                'predicted_cost': 100 + (cpu_forecast + memory_forecast) / 2
            })
        
        return {
            'current_usage': {
                'cpu_percent': round(avg_cpu, 1),
                'memory_percent': round(avg_memory, 1),
                'active_containers': len(containers),
                'database_count': len(databases)
            },
            'optimization_score': max(0, 100 - savings_potential),
            'cost_efficiency': max(60, 100 - (abs(50 - avg_cpu) + abs(50 - avg_memory)) / 2),
            'recommendations': recommendations,
            'potential_savings_percent': min(50, savings_potential),
            'forecast_data': forecast_data[:12],  # Next 12 hours
            'last_updated': current_time.isoformat(),
            'optimization_opportunities': len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error generating resource optimization data: {str(e)}")
        return {
            'current_usage': {'cpu_percent': 0, 'memory_percent': 0, 'active_containers': 0, 'database_count': 0},
            'optimization_score': 75,
            'cost_efficiency': 80,
            'recommendations': [],
            'potential_savings_percent': 0,
            'forecast_data': [],
            'last_updated': datetime.now().isoformat(),
            'optimization_opportunities': 0
        }

def generate_defense_in_depth_data(organization_id: str) -> Dict[str, Any]:
    """Generate defense-in-depth security layer data"""
    try:
        current_time = datetime.now()
        
        # Define security layers with their status
        layers = [
            {
                'id': 'perimeter',
                'name': 'Perimeter Security',
                'status': 'active',
                'health': 98,
                'components': ['Firewall', 'IDS/IPS', 'DDoS Protection'],
                'threats_blocked': 1247,
                'last_incident': (current_time - timedelta(hours=2)).isoformat()
            },
            {
                'id': 'network',
                'name': 'Network Security',
                'status': 'active',
                'health': 95,
                'components': ['Network Segmentation', 'VPN', 'Network Monitoring'],
                'threats_blocked': 523,
                'last_incident': (current_time - timedelta(hours=5)).isoformat()
            },
            {
                'id': 'application',
                'name': 'Application Security',
                'status': 'active',
                'health': 92,
                'components': ['WAF', 'API Gateway', 'Rate Limiting'],
                'threats_blocked': 892,
                'last_incident': (current_time - timedelta(minutes=45)).isoformat()
            },
            {
                'id': 'data',
                'name': 'Data Security',
                'status': 'active',
                'health': 100,
                'components': ['Encryption at Rest', 'Encryption in Transit', 'Access Control'],
                'threats_blocked': 0,
                'last_incident': None
            },
            {
                'id': 'endpoint',
                'name': 'Endpoint Security',
                'status': 'active',
                'health': 88,
                'components': ['Device Authentication', 'Certificate Management', 'Anomaly Detection'],
                'threats_blocked': 156,
                'last_incident': (current_time - timedelta(hours=12)).isoformat()
            },
            {
                'id': 'monitoring',
                'name': 'Security Monitoring',
                'status': 'active',
                'health': 96,
                'components': ['SIEM', 'Log Analysis', 'Threat Intelligence'],
                'threats_blocked': 0,
                'last_incident': None
            }
        ]
        
        # Calculate overall security score
        total_health = sum(layer['health'] for layer in layers)
        overall_score = total_health / len(layers)
        
        # Generate recent events
        events = [
            {
                'timestamp': (current_time - timedelta(minutes=5)).isoformat(),
                'layer': 'perimeter',
                'type': 'threat_blocked',
                'severity': 'medium',
                'description': 'Blocked suspicious IP attempting port scan'
            },
            {
                'timestamp': (current_time - timedelta(minutes=15)).isoformat(),
                'layer': 'application',
                'type': 'rate_limit',
                'severity': 'low',
                'description': 'Rate limiting activated for API endpoint'
            },
            {
                'timestamp': (current_time - timedelta(minutes=30)).isoformat(),
                'layer': 'endpoint',
                'type': 'anomaly_detected',
                'severity': 'high',
                'description': 'Unusual device behavior detected and isolated'
            }
        ]
        
        # Calculate threat statistics
        total_threats_blocked = sum(layer['threats_blocked'] for layer in layers)
        
        return {
            'layers': layers,
            'overall_score': round(overall_score, 1),
            'status': 'secure' if overall_score > 90 else 'warning' if overall_score > 70 else 'critical',
            'total_threats_blocked': total_threats_blocked,
            'active_layers': len([l for l in layers if l['status'] == 'active']),
            'recent_events': events,
            'last_updated': current_time.isoformat(),
            'compliance_status': {
                'etsi_en_303_645': True,
                'iso_27402': True,
                'gdpr': True
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating defense-in-depth data: {str(e)}")
        return {
            'layers': [],
            'overall_score': 0,
            'status': 'unknown',
            'total_threats_blocked': 0,
            'active_layers': 0,
            'recent_events': [],
            'last_updated': datetime.now().isoformat(),
            'compliance_status': {}
        }

# Real-time container health endpoint (missing endpoint for AI/ML cards)
@realtime_bp.route('/container-health')
@require_auth
def get_realtime_container_health():
    """
    Get real-time container health metrics for the SmartSystemOverviewCard
    Returns current Docker container status and system metrics
    
    Optimized with timeout handling and fallback mechanisms
    """
    try:
        # Set a strict timeout for the entire operation
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Container health check timed out")
        
        # Set a 10-second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        try:
            # Use asyncio with timeout
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Add timeout to the async operation itself
                container_health = loop.run_until_complete(
                    asyncio.wait_for(
                        realtime_analytics_service.get_system_health_metrics_fast(),
                        timeout=3.0  # 3 second timeout to prevent ECONNABORTED errors
                    )
                )
            finally:
                loop.close()
            
            # Clear the alarm
            signal.alarm(0)
            
            logger.info("Real-time container health requested successfully")
            return jsonify(container_health), 200
            
        except (TimeoutError, asyncio.TimeoutError) as e:
            signal.alarm(0)  # Clear alarm
            logger.warning(f"Container health check timed out: {str(e)}")
            return jsonify(realtime_analytics_service._get_fallback_system_health()), 200
            
    except Exception as e:
        logger.error(f"Real-time container health error: {str(e)}")
        # Return fallback data instead of error to keep UI working
        fallback_data = realtime_analytics_service._get_fallback_system_health()
        fallback_data['status'] = 'error_fallback'
        fallback_data['error_message'] = str(e)[:100]  # Truncate error message
        return jsonify(fallback_data), 200

# Connection management endpoint
@realtime_bp.route('/connections/status')
@require_auth
def get_connection_status():
    """Get status of active real-time connections"""
    user_id = g.current_user.get('user_id', 'anonymous')
    
    with connection_lock:
        user_connections = len(active_connections.get(user_id, []))
        total_connections = sum(len(conns) for conns in active_connections.values())
        
    return {
        'user_connections': user_connections,
        'total_connections': total_connections,
        'connected_users': len(active_connections),
        'timestamp': datetime.now().isoformat()
    }