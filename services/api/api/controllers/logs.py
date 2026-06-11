# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Logs Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import os
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, Response
import json
from typing import Dict, List

from ..core.auth import require_auth, require_role
from ..services.logging_service import logging_service, LogType, LogLevel
from psycopg2.extras import RealDictCursor
from psycopg2 import sql as pg_sql


# Whitelist of tables that log-maintenance operations are permitted to touch.
# Any table value supplied by a client MUST be validated against this set
# before being used to build a SQL statement (fail-closed). This prevents
# SQL identifier injection via the `table` request parameter.
ALLOWED_LOG_TABLES = frozenset({
    'system_logs',
    'activity_logs',
    'api_metrics',
    'security_logs',
    'container_metrics',
})


SEVERITY_STATUS_MAP = {
    'error': ['failure', 'error', 'denied', 'blocked'],
    'warning': ['warning', 'pending', 'degraded'],
    'info': ['success', 'completed', 'allowed', 'ok', 'info']
}

ERROR_STATUS_VALUES = [status.lower() for status in SEVERITY_STATUS_MAP['error']]
WARNING_STATUS_VALUES = [status.lower() for status in SEVERITY_STATUS_MAP['warning']]

logger = logging.getLogger(__name__)

# Create blueprint
logs_bp = Blueprint('logs', __name__)

# Phase 1 log categories
PHASE1_CATEGORIES = ['USER_CRITICAL', 'DEVICE_ISSUES', 'API_PROBLEMS']

@logs_bp.route('/', methods=['GET'])
@require_auth
def get_logs():
    """
    Get system logs with filtering and pagination.
    
    Query Parameters:
        log_type: Filter by log type (system, activity, error, etc.)
        level: Filter by log level (debug, info, warning, error, critical)
        source: Filter by source/container name
        start_time: ISO format start time
        end_time: ISO format end time
        search: Full-text search in messages
        limit: Number of results (default: 100, max: 1000)
        offset: Pagination offset (default: 0)
        
    Returns:
        200: List of logs
        400: Invalid parameters
        500: Server error
    """
    try:
        # Parse query parameters
        filters = {}
        
        if request.args.get('log_type'):
            filters['log_type'] = request.args.get('log_type')
        
        if request.args.get('level'):
            filters['level'] = request.args.get('level')
        
        if request.args.get('source'):
            filters['source'] = request.args.get('source')
        
        # Filter by organization for non-TESA admins
        # Both 'admin' and 'super_admin' are TESA admins and can see all logs
        if g.current_user.get('role') not in ['admin', 'super_admin']:
            filters['organization_id'] = g.current_user.get('organization_id')
        elif request.args.get('organization_id'):
            filters['organization_id'] = request.args.get('organization_id')
        
        if request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        if request.args.get('device_id'):
            filters['device_id'] = request.args.get('device_id')
        
        # Parse time range
        if request.args.get('start_time'):
            try:
                filters['start_time'] = datetime.fromisoformat(
                    request.args.get('start_time').replace('Z', '+00:00')
                )
            except ValueError:
                return jsonify({'error': 'Invalid start_time format'}), 400
        
        if request.args.get('end_time'):
            try:
                filters['end_time'] = datetime.fromisoformat(
                    request.args.get('end_time').replace('Z', '+00:00')
                )
            except ValueError:
                return jsonify({'error': 'Invalid end_time format'}), 400
        
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        
        # Pagination
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # ✅ CRITICAL: ACL enforcement - pass user role and org ID
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Query logs with ACL enforcement
        logs = logging_service.query_logs(
            filters, 
            limit, 
            offset,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        # Convert datetime objects to ISO format strings
        for log in logs:
            if 'time' in log and hasattr(log['time'], 'isoformat'):
                log['time'] = log['time'].isoformat()
        
        return jsonify({
            'logs': logs,
            'count': len(logs),
            'limit': limit,
            'offset': offset,
            'acl_filtered': user_role == 'organization_admin' and user_org_id is not None
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': 'Failed to retrieve logs'}), 500

@logs_bp.route('/phase1/dashboard', methods=['GET'])
@require_auth
def get_phase1_dashboard():
    """
    Get Phase 1 Activity Log dashboard data.
    
    Query Parameters:
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        
    Returns:
        200: Dashboard data with categorized logs and statistics
        500: Server error
    """
    try:
        time_range = request.args.get('time_range', '24h')
        
        # Validate time range
        valid_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_ranges:
            time_range = '24h'
        
        # ACL enforcement
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Get Phase 1 specific analytics
        analytics = logging_service.get_log_analytics(
            time_range,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        # Get recent logs for each Phase 1 category
        recent_logs = {}
        for category in PHASE1_CATEGORIES:
            filters = {
                'phase1_category': category,
                'sort_by': 'severity'
            }
            
            logs = logging_service.query_logs(
                filters,
                limit=10,
                offset=0,
                user_role=user_role,
                user_org_id=user_org_id
            )
            
            # Convert datetime objects
            for log in logs:
                if 'time' in log and hasattr(log['time'], 'isoformat'):
                    log['time'] = log['time'].isoformat()
            
            recent_logs[category] = logs
        
        # Build dashboard response
        dashboard_data = {
            'analytics': analytics,
            'recent_logs_by_category': recent_logs,
            'categories': [
                {
                    'id': 'USER_CRITICAL',
                    'name': 'User Critical',
                    'description': 'Critical user actions and security events',
                    'color': '#ef4444',  # red
                    'icon': 'user-x'
                },
                {
                    'id': 'DEVICE_ISSUES',
                    'name': 'Device Issues',
                    'description': 'Device connectivity and operational issues',
                    'color': '#f59e0b',  # amber
                    'icon': 'wifi-off'
                },
                {
                    'id': 'API_PROBLEMS',
                    'name': 'API Problems',
                    'description': 'API errors and performance issues',
                    'color': '#8b5cf6',  # violet
                    'icon': 'alert-triangle'
                }
            ],
            'time_range': time_range,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        logger.error(f"Error getting Phase 1 dashboard: {e}")
        return jsonify({'error': 'Failed to retrieve dashboard data'}), 500

@logs_bp.route('/phase1/critical', methods=['GET'])
@require_auth
def get_critical_logs():
    """
    Get critical logs requiring immediate attention.
    
    Query Parameters:
        category: Filter by specific Phase 1 category
        limit: Number of results (default: 50, max: 200)
        
    Returns:
        200: List of critical logs
        500: Server error
    """
    try:
        # Build filters for critical logs
        filters = {
            'level': ['critical', 'high'],
            'requires_action': True
        }
        
        if request.args.get('category'):
            if request.args.get('category') not in PHASE1_CATEGORIES:
                return jsonify({'error': f'Invalid category. Must be one of: {PHASE1_CATEGORIES}'}), 400
            filters['phase1_category'] = request.args.get('category')
        
        limit = min(int(request.args.get('limit', 50)), 200)
        
        # ACL enforcement
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Query critical logs
        logs = logging_service.query_logs(
            filters,
            limit=limit,
            offset=0,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        # Convert datetime objects and enhance with action suggestions
        for log in logs:
            if 'time' in log and hasattr(log['time'], 'isoformat'):
                log['time'] = log['time'].isoformat()
            
            # Add suggested actions based on log type
            log['suggested_actions'] = _get_suggested_actions(log)
        
        return jsonify({
            'critical_logs': logs,
            'count': len(logs),
            'filter_applied': filters
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting critical logs: {e}")
        return jsonify({'error': 'Failed to retrieve critical logs'}), 500

@logs_bp.route('/phase1/log', methods=['POST'])
@require_auth
def log_phase1_event():
    """
    Log a Phase 1 categorized event.
    
    Request JSON:
        {
            "category": "USER_CRITICAL|DEVICE_ISSUES|API_PROBLEMS",
            "level": "critical|high|medium|low|error|warning|info",
            "message": "Event message",
            "source": "Source system/component",
            "metadata": {
                "device_id": "...",
                "error_code": "...",
                "additional_data": {...}
            }
        }
        
    Returns:
        204: Event logged successfully
        400: Invalid request data
        500: Server error
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['category', 'level', 'message', 'source']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate category
        if data['category'] not in PHASE1_CATEGORIES:
            return jsonify({'error': f'Invalid category. Must be one of: {PHASE1_CATEGORIES}'}), 400
        
        # Map level string to LogLevel enum
        level_map = {
            'critical': LogLevel.CRITICAL,
            'high': LogLevel.HIGH,
            'error': LogLevel.ERROR,
            'medium': LogLevel.MEDIUM,
            'warning': LogLevel.WARNING,
            'low': LogLevel.LOW,
            'info': LogLevel.INFO,
            'debug': LogLevel.DEBUG
        }
        
        level = level_map.get(data['level'].lower())
        if not level:
            return jsonify({'error': 'Invalid level'}), 400
        
        # Log the Phase 1 event
        logging_service.log_phase1_event(
            category=data['category'],
            level=level,
            message=data['message'],
            source=data['source'],
            metadata=data.get('metadata', {}),
            user_id=g.current_user.get('_id'),
            organization_id=g.current_user.get('organization_id'),
            client_ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return '', 204
        
    except Exception as e:
        logger.error(f"Error logging Phase 1 event: {e}")
        return jsonify({'error': 'Failed to log event'}), 500

@logs_bp.route('/stream', methods=['GET'])
@require_auth
def stream_logs():
    """
    Stream logs in real-time using Server-Sent Events (SSE).
    
    Query Parameters:
        Same as GET /logs endpoint
        
    Returns:
        200: SSE stream of logs
        400: Invalid parameters
    """
    try:
        # Parse filters (same as get_logs)
        filters = {}
        
        if request.args.get('log_type'):
            filters['log_type'] = request.args.get('log_type')
        
        if request.args.get('level'):
            filters['level'] = request.args.get('level')
        
        if request.args.get('source'):
            filters['source'] = request.args.get('source')
        
        # Filter by organization for non-TESA admins
        # Both 'admin' and 'super_admin' are TESA admins and can see all logs
        if g.current_user.get('role') not in ['admin', 'super_admin']:
            filters['organization_id'] = g.current_user.get('organization_id')
        
        # Phase 1 specific stream filters
        if request.args.get('phase1_only', '').lower() == 'true':
            filters['log_type'] = [LogType.USER_CRITICAL.value, LogType.DEVICE_ISSUES.value, LogType.API_PROBLEMS.value]
        
        if request.args.get('critical_only', '').lower() == 'true':
            filters['level'] = [LogLevel.CRITICAL.value, LogLevel.HIGH.value]
        
        def generate():
            """Generate SSE events"""
            last_check = datetime.utcnow()
            
            while True:
                try:
                    # Query new logs since last check
                    filters['start_time'] = last_check
                    filters['end_time'] = datetime.utcnow()
                    
                    # ✅ CRITICAL: ACL enforcement for streaming
                    user_role = g.current_user.get('role')
                    user_org_id = g.current_user.get('organization_id')
                    
                    # Query logs directly with ACL enforcement
                    new_logs = logging_service.query_logs(
                        filters, 
                        limit=50,
                        user_role=user_role,
                        user_org_id=user_org_id
                    )
                    
                    if new_logs:
                        # Convert datetime objects
                        for log in new_logs:
                            if 'time' in log and hasattr(log['time'], 'isoformat'):
                                log['time'] = log['time'].isoformat()
                        
                        # Send as SSE event
                        yield f"data: {json.dumps({'logs': new_logs})}\n\n"
                        
                        # Update last check time
                        last_check = datetime.utcnow()
                    
                    # Wait before next check
                    import time
                    time.sleep(2)  # Check every 2 seconds
                    
                except GeneratorExit:
                    break
                except Exception as e:
                    logger.error(f"Error streaming logs: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # Disable Nginx buffering
            }
        )
        
    except Exception as e:
        logger.error(f"Error setting up log stream: {e}")
        return jsonify({'error': 'Failed to setup log stream'}), 500

@logs_bp.route('/analytics', methods=['GET'])
@require_auth
def get_log_analytics():
    """
    Get log analytics and statistics.
    
    Query Parameters:
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        
    Returns:
        200: Analytics data
        500: Server error
    """
    try:
        time_range = request.args.get('time_range', '1h')
        
        # Validate time range
        valid_ranges = ['1h', '6h', '24h', '7d', '30d']
        if time_range not in valid_ranges:
            time_range = '1h'
        
        # ✅ CRITICAL: ACL enforcement for analytics
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Get analytics with ACL enforcement
        analytics = logging_service.get_log_analytics(
            time_range,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        # Convert datetime objects
        for trend in analytics.get('error_trends', []):
            if 'bucket' in trend and hasattr(trend['bucket'], 'isoformat'):
                trend['bucket'] = trend['bucket'].isoformat()
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Error getting log analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500

@logs_bp.route('/console', methods=['POST'])
@require_auth
def log_console():
    """
    Log browser console messages.
    
    Request JSON:
        {
            "level": "info|warning|error",
            "message": "Console message",
            "source": "Browser location/component",
            "metadata": {
                "userAgent": "...",
                "url": "...",
                "lineNumber": 123,
                "columnNumber": 45
            }
        }
        
    Returns:
        204: Log recorded
        400: Invalid data
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message required'}), 400
        
        # Map console levels to our LogLevel
        level_map = {
            'log': LogLevel.DEBUG,
            'info': LogLevel.INFO,
            'warn': LogLevel.WARNING,
            'warning': LogLevel.WARNING,
            'error': LogLevel.ERROR
        }
        
        level = level_map.get(data.get('level', 'info'), LogLevel.INFO)
        
        # Log console message
        logging_service.log_system(
            level=level,
            message=data['message'],
            source=data.get('source', 'browser'),
            metadata=data.get('metadata', {}),
            log_type='console',
            user_id=g.current_user.get('_id'),
            organization_id=g.current_user.get('organization_id'),
            user_agent=request.headers.get('User-Agent'),
            client_ip=request.remote_addr
        )
        
        return '', 204
        
    except Exception as e:
        logger.error(f"Error logging console message: {e}")
        return jsonify({'error': 'Failed to log message'}), 500

@logs_bp.route('/export', methods=['GET'])
@require_auth
@require_role(['admin', 'super_admin'])
def export_logs():
    """
    Export logs to JSON or CSV format.
    
    Query Parameters:
        format: Export format (json, csv)
        + all filters from GET /logs endpoint
        
    Returns:
        200: File download
        400: Invalid parameters
        403: Insufficient permissions
        500: Server error
    """
    try:
        export_format = request.args.get('format', 'json')
        
        if export_format not in ['json', 'csv']:
            return jsonify({'error': 'Invalid format. Use json or csv'}), 400
        
        # Get filters (same as get_logs)
        filters = {}
        
        # Add filters...
        if request.args.get('log_type'):
            filters['log_type'] = request.args.get('log_type')
        
        if request.args.get('level'):
            filters['level'] = request.args.get('level')
        
        # ✅ CRITICAL: ACL enforcement for export
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Query logs (larger limit for export) with ACL enforcement
        logs = logging_service.query_logs(
            filters, 
            limit=10000,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        if export_format == 'json':
            # Convert datetime objects
            for log in logs:
                if 'time' in log and hasattr(log['time'], 'isoformat'):
                    log['time'] = log['time'].isoformat()
            
            # Create JSON response
            response = Response(
                json.dumps({'logs': logs, 'count': len(logs)}, indent=2),
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename=tesa_logs_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
                }
            )
        else:  # CSV
            import csv
            import io
            
            # Create CSV
            output = io.StringIO()
            
            if logs:
                # Use first log to get field names
                fieldnames = list(logs[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                writer.writeheader()
                for log in logs:
                    # Convert datetime objects
                    for key, value in log.items():
                        if hasattr(value, 'isoformat'):
                            log[key] = value.isoformat()
                        elif isinstance(value, dict):
                            log[key] = json.dumps(value)
                    writer.writerow(log)
            
            # Create CSV response
            response = Response(
                output.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=tesa_logs_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
                }
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting logs: {e}")
        return jsonify({'error': 'Failed to export logs'}), 500

@logs_bp.route('/audit', methods=['GET'])
@require_auth
def get_audit_logs():
    """
    Get audit logs from MongoDB audit_logs collection.
    
    Query Parameters:
        action: Filter by action type
        user_id: Filter by user
        resource_type: Filter by resource type
        start_time: ISO format start time
        end_time: ISO format end time
        limit: Number of results
        offset: Pagination offset
        
    Returns:
        200: List of audit logs
        500: Server error
    """
    try:
        from ..services.audit_service import audit_service
        
        # Build filters
        filters = {}
        
        if request.args.get('action'):
            filters['action'] = request.args.get('action')
        
        if request.args.get('user_id'):
            filters['user.id'] = request.args.get('user_id')
        
        if request.args.get('resource_type'):
            filters['resource.type'] = request.args.get('resource_type')
        
        # Parse time range
        if request.args.get('start_time'):
            try:
                start_time = datetime.fromisoformat(
                    request.args.get('start_time').replace('Z', '+00:00')
                )
                filters['timestamp'] = {'$gte': start_time}
            except ValueError:
                return jsonify({'error': 'Invalid start_time format'}), 400
        
        if request.args.get('end_time'):
            try:
                end_time = datetime.fromisoformat(
                    request.args.get('end_time').replace('Z', '+00:00')
                )
                if 'timestamp' in filters:
                    filters['timestamp']['$lte'] = end_time
                else:
                    filters['timestamp'] = {'$lte': end_time}
            except ValueError:
                return jsonify({'error': 'Invalid end_time format'}), 400
        
        # Pagination
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))
        
        # Get audit logs
        logs = audit_service.get_audit_logs(
            user=g.current_user,
            filters=filters,
            limit=limit
        )
        
        return jsonify({
            'audit_logs': logs,
            'count': len(logs),
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}")
        return jsonify({'error': 'Failed to retrieve audit logs'}), 500

@logs_bp.route('/activity', methods=['GET'])
@require_auth
def get_activity_logs():
    """
    Get user activity logs with optimized performance.
    
    Query Parameters:
        user_id: Filter by user
        action: Filter by action type
        resource_type: Filter by resource type
        start_time: ISO format start time
        end_time: ISO format end time
        limit: Number of results (default: 50, max: 500)
        offset: Pagination offset
        
    Returns:
        200: List of activity logs
        500: Server error
    """
    try:
        # Direct query to activity_logs table with timeout handling
        from ..services.logging_service import logging_service
        import time
        
        start_time = time.time()
        
        # Add timeout wrapper
        conn = None
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                conn = logging_service._get_connection()
                break
            except Exception as e:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    return jsonify({'error': 'Database connection failed'}), 500
        
        try:
            from psycopg2.extras import RealDictCursor
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Set statement timeout to prevent long-running queries
                cur.execute("SET statement_timeout = '30s'")
                
                # Build query
                where_clauses = []
                params = []
                
                # ✅ CRITICAL: ACL enforcement for activity logs
                user_role = g.current_user.get('role')
                user_org_id = g.current_user.get('organization_id')
                
                if user_role == 'organization_admin' and user_org_id:
                    # Organization Admins can ONLY see their organization's activity
                    where_clauses.append("organization_id = %s")
                    params.append(user_org_id)
                elif user_role == 'organization_admin' and not user_org_id:
                    # No org ID = no access for org admins
                    return jsonify({'error': 'Access denied - no organization'}), 403
                # TESA Admins (admin, super_admin) can see all activity data
                
                if request.args.get('user_id'):
                    where_clauses.append("user_id = %s")
                    params.append(request.args.get('user_id'))
                
                if request.args.get('action'):
                    where_clauses.append("action = %s")
                    params.append(request.args.get('action'))
                
                if request.args.get('resource_type'):
                    where_clauses.append("resource_type = %s")
                    params.append(request.args.get('resource_type'))
                
                # Time range with default to last 24 hours if no filters
                if request.args.get('start_time'):
                    where_clauses.append("time >= %s")
                    params.append(datetime.fromisoformat(
                        request.args.get('start_time').replace('Z', '+00:00')
                    ))
                elif not any([request.args.get('user_id'), request.args.get('action'), request.args.get('resource_type')]):
                    # Default to last 24 hours if no specific filters
                    where_clauses.append("time >= NOW() - INTERVAL '24 hours'")
                
                if request.args.get('end_time'):
                    where_clauses.append("time <= %s")
                    params.append(datetime.fromisoformat(
                        request.args.get('end_time').replace('Z', '+00:00')
                    ))
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # OPTIMIZED: Stricter pagination defaults for performance
                limit = min(int(request.args.get('limit', 50)), 500)  # Reduced from 100/1000
                offset = int(request.args.get('offset', 0))
                
                query = f"""
                    SELECT * FROM activity_logs
                    WHERE {where_sql}
                    ORDER BY time DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                
                cur.execute(query, params)
                activities = cur.fetchall()
                
                # OPTIMIZED: Batch fetch user details from MongoDB with connection retry
                result = []
                user_cache = {}
                unique_user_ids = set()
                
                # First pass: collect unique user IDs and prepare activity records
                for activity in activities:
                    activity_dict = dict(activity)
                    
                    # Convert time to timestamp for frontend compatibility
                    if 'time' in activity_dict and hasattr(activity_dict['time'], 'isoformat'):
                        activity_dict['timestamp'] = activity_dict['time'].isoformat()
                        del activity_dict['time']
                    
                    user_id = activity_dict.get('user_id')
                    if user_id:
                        unique_user_ids.add(user_id)
                    
                    result.append(activity_dict)
                
                # OPTIMIZED: Batch query MongoDB for all users with retry logic
                mongo_client = None
                if unique_user_ids:
                    max_mongo_retries = 3
                    mongo_retry_delay = 0.5
                    
                    for attempt in range(max_mongo_retries):
                        try:
                            from pymongo import MongoClient
                            from bson import ObjectId
                            
                            mongo_uri = os.getenv('MONGODB_URI')
                            if not mongo_uri:
                                raise RuntimeError('MONGODB_URI environment variable is required')
                            # Add connection timeout and retry settings
                            mongo_client = MongoClient(
                                mongo_uri, 
                                serverSelectionTimeoutMS=5000,
                                connectTimeoutMS=5000,
                                maxPoolSize=10,
                                retryWrites=True
                            )
                            db = mongo_client.get_database()
                            users_collection = db.users
                            
                            # Batch query: get all users at once
                            user_ids_for_query = []
                            for user_id in unique_user_ids:
                                try:
                                    if len(str(user_id)) == 24:
                                        user_ids_for_query.append(ObjectId(user_id))
                                    else:
                                        user_ids_for_query.append(user_id)
                                except:
                                    user_ids_for_query.append(user_id)
                            
                            # Single query to fetch all users
                            mongo_users = list(users_collection.find(
                                {'_id': {'$in': user_ids_for_query}},
                                {'_id': 1, 'username': 1, 'name': 1, 'email': 1, 'role': 1}
                            ))
                            
                            # Build user cache
                            for mongo_user in mongo_users:
                                user_cache[str(mongo_user['_id'])] = {
                                    'id': str(mongo_user['_id']),
                                    'name': mongo_user.get('username', mongo_user.get('name', 'Unknown User')),
                                    'email': mongo_user.get('email', 'unknown@example.com'),
                                    'role': mongo_user.get('role', 'user')
                                }
                            
                            break  # Success, exit retry loop
                            
                        except Exception as e:
                            logger.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}")
                            if mongo_client:
                                try:
                                    mongo_client.close()
                                except:
                                    pass
                                mongo_client = None
                            
                            if attempt < max_mongo_retries - 1:
                                time.sleep(mongo_retry_delay * (2 ** attempt))  # Exponential backoff
                            else:
                                logger.error(f"Failed to connect to MongoDB after {max_mongo_retries} attempts")
                
                # Second pass: assign user data from cache with fallback
                for activity_dict in result:
                    user_id = activity_dict.get('user_id')
                    user_data = user_cache.get(str(user_id)) if user_id else None
                    
                    if not user_data:
                        user_data = {
                            'id': user_id or 'unknown',
                            'name': 'Unknown User',
                            'email': 'unknown@example.com',
                            'role': 'user'
                        }
                    
                    activity_dict['user'] = user_data
                    
                    # Map resource_type to category for frontend compatibility
                    activity_dict['category'] = activity_dict.get('resource_type', 'system')
                    
                    # Add severity mapping based on result and action
                    if activity_dict.get('result') == 'failure':
                        activity_dict['severity'] = 'error'
                    elif 'security' in activity_dict.get('action', '').lower() or 'auth' in activity_dict.get('action', '').lower():
                        activity_dict['severity'] = 'warning'
                    else:
                        activity_dict['severity'] = 'info'
                    
                    # Create resource object if resource details exist
                    if activity_dict.get('resource_type') and activity_dict.get('resource_id'):
                        activity_dict['resource'] = {
                            'type': activity_dict.get('resource_type'),
                            'id': activity_dict.get('resource_id'),
                            'name': activity_dict.get('resource_id')  # Use ID as name fallback
                        }
                    
                    # Parse metadata if it's a JSON string
                    if isinstance(activity_dict.get('metadata'), str):
                        try:
                            activity_dict['metadata'] = json.loads(activity_dict['metadata'])
                        except:
                            pass
                    
                    # Add additional fields for frontend compatibility
                    activity_dict['details'] = activity_dict.get('metadata', {})
                    activity_dict['status'] = activity_dict.get('result', 'success')
                
                # Clean up MongoDB connection
                if mongo_client:
                    try:
                        mongo_client.close()
                    except Exception as e:
                        logger.warning(f"Error closing MongoDB connection: {e}")
                
                # Calculate stats for the response
                stats = {
                    'total': len(result),
                    'byCategory': {},
                    'bySeverity': {},
                    'byStatus': {},
                    'recentActivity': 0
                }
                
                # Calculate stats from the current results
                recent_time = datetime.utcnow() - timedelta(hours=1)
                for log in result:
                    # Count by category
                    category = log.get('category', 'unknown')
                    stats['byCategory'][category] = stats['byCategory'].get(category, 0) + 1
                    
                    # Count by severity
                    severity = log.get('severity', 'info')
                    stats['bySeverity'][severity] = stats['bySeverity'].get(severity, 0) + 1
                    
                    # Count by status
                    status = log.get('status', 'success')
                    stats['byStatus'][status] = stats['byStatus'].get(status, 0) + 1
                    
                    # Count recent activity (within last hour)
                    try:
                        log_time = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                        if log_time > recent_time:
                            stats['recentActivity'] += 1
                    except:
                        pass
                
                # Add performance metrics
                end_time = time.time()
                query_duration = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
                
                logger.info(f"Activity logs query completed in {query_duration}ms for {len(result)} records")
                
                return jsonify({
                    'data': {
                        'logs': result,
                        'stats': stats
                    },
                    'meta': {
                        'query_duration_ms': query_duration,
                        'records_returned': len(result),
                        'limit': limit,
                        'offset': offset,
                        'optimized': True
                    }
                }), 200
                
        finally:
            logging_service._put_connection(conn)
            
    except Exception as e:
        logger.error(f"Error getting activity logs: {e}")
        return jsonify({'error': 'Failed to retrieve activity logs'}), 500

@logs_bp.route('/security', methods=['GET'])
@require_auth
@require_role(['admin', 'super_admin', 'platform_admin', 'organization_admin'])
def get_security_logs():
    """
    Get security event logs.
    
    Query Parameters:
        event_type: Filter by event type
        severity: Filter by severity (low, medium, high, critical)
        start_time: ISO format start time
        end_time: ISO format end time
        limit: Number of results
        offset: Pagination offset
        
    Returns:
        200: List of security logs
        403: Insufficient permissions
        500: Server error
    """
    try:
        from ..services.logging_service import logging_service
        
        conn = logging_service._get_connection()
        try:
            from psycopg2.extras import RealDictCursor
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query
                where_clauses = []
                params = []
                
                if request.args.get('event_type'):
                    where_clauses.append("event_type = %s")
                    params.append(request.args.get('event_type'))
                
                if request.args.get('severity'):
                    where_clauses.append("severity = %s")
                    params.append(request.args.get('severity'))
                
                # Time range
                if request.args.get('start_time'):
                    where_clauses.append("time >= %s")
                    params.append(datetime.fromisoformat(
                        request.args.get('start_time').replace('Z', '+00:00')
                    ))
                
                if request.args.get('end_time'):
                    where_clauses.append("time <= %s")
                    params.append(datetime.fromisoformat(
                        request.args.get('end_time').replace('Z', '+00:00')
                    ))
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Pagination
                limit = min(int(request.args.get('limit', 100)), 1000)
                offset = int(request.args.get('offset', 0))
                
                query = f"""
                    SELECT * FROM security_logs
                    WHERE {where_sql}
                    ORDER BY time DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                
                cur.execute(query, params)
                security_events = cur.fetchall()
                
                # Convert to list of dicts
                result = []
                for event in security_events:
                    event_dict = dict(event)
                    if 'time' in event_dict and hasattr(event_dict['time'], 'isoformat'):
                        event_dict['time'] = event_dict['time'].isoformat()
                    result.append(event_dict)
                
                return jsonify({
                    'security_events': result,
                    'count': len(result),
                    'limit': limit,
                    'offset': offset
                }), 200
                
        finally:
            logging_service._put_connection(conn)
            
    except Exception as e:
        logger.error(f"Error getting security logs: {e}")
        return jsonify({'error': 'Failed to retrieve security logs'}), 500

@logs_bp.route('/storage/stats', methods=['GET'])
@require_auth
@require_role(['admin', 'super_admin'])
def get_log_storage_stats():
    """
    Get log storage statistics and monitoring data.
    
    Returns:
        200: Storage statistics including size, compression, retention
        403: Insufficient permissions
        500: Server error
    """
    try:
        conn = logging_service._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get storage statistics
                cur.execute("SELECT * FROM log_storage_stats")
                storage_stats = cur.fetchall()
                
                # Get storage alerts
                cur.execute("SELECT * FROM get_log_storage_alerts()")
                storage_alerts = cur.fetchall()
                
                # Get growth estimates
                cur.execute("SELECT * FROM estimate_log_storage_growth()")
                growth_estimates = cur.fetchall()
                
                # Get total database size
                cur.execute("SELECT pg_database_size(current_database()) as db_size")
                db_size = cur.fetchone()['db_size']
                
                # Get job status for lifecycle policies
                cur.execute("""
                    SELECT 
                        job_id,
                        application_name,
                        schedule_interval,
                        max_runtime,
                        last_run_status,
                        last_run_started_at,
                        next_scheduled_run
                    FROM timescaledb_information.job_stats
                    WHERE application_name IN (
                        'Compression Policy',
                        'Retention Policy', 
                        'Refresh Continuous Aggregate Policy',
                        'check_log_storage_and_alert'
                    )
                """)
                job_stats = cur.fetchall()
                
                # Convert to response format
                response = {
                    'database_size': {
                        'total_bytes': db_size,
                        'total_size': f"{round(db_size / (1024**3), 2)} GB",
                        'usage_percentage': round((db_size / (500 * 1024**3)) * 100, 2)  # Assume 500GB limit
                    },
                    'table_stats': [dict(row) for row in storage_stats],
                    'alerts': [dict(row) for row in storage_alerts],
                    'growth_projections': [dict(row) for row in growth_estimates],
                    'lifecycle_jobs': [dict(row) for row in job_stats],
                    'retention_policies': {
                        'api_metrics': '30 days raw, 1 year aggregated',
                        'system_logs': '90 days',
                        'activity_logs': '180 days (6 months)',
                        'security_logs': '365 days (1 year)',
                        'container_metrics': '7 days'
                    }
                }
                
                return jsonify(response), 200
                
        finally:
            logging_service._put_connection(conn)
            
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        return jsonify({'error': 'Failed to retrieve storage statistics'}), 500

@logs_bp.route('/storage/cleanup', methods=['POST'])
@require_auth
@require_role(['super_admin'])
def trigger_log_cleanup():
    """
    Manually trigger log cleanup operations.
    
    Request JSON:
        {
            "operation": "compress|drop_chunks|vacuum",
            "table": "system_logs|activity_logs|api_metrics|all",
            "older_than": "7 days|30 days|90 days"
        }
        
    Returns:
        202: Cleanup operation started
        400: Invalid parameters
        403: Insufficient permissions
        500: Server error
    """
    try:
        data = request.get_json()
        operation = data.get('operation', 'compress')
        table = data.get('table', 'all')
        older_than = data.get('older_than', '7 days')
        
        if operation not in ['compress', 'drop_chunks', 'vacuum']:
            return jsonify({'error': 'Invalid operation'}), 400

        # Fail-closed table validation: a client-supplied table name must be
        # an exact match against the whitelist before it can be used to build
        # any SQL statement. Reject anything else with 400.
        if table == 'all':
            tables = list(ALLOWED_LOG_TABLES)
        else:
            if table not in ALLOWED_LOG_TABLES:
                return jsonify({'error': 'Invalid table'}), 400
            tables = [table]

        conn = logging_service._get_connection()
        try:
            with conn.cursor() as cur:
                result = {'operations': []}

                for tbl in tables:
                    # Defense-in-depth: re-validate each table name inside the
                    # loop so a value can never reach a SQL string unchecked.
                    if tbl not in ALLOWED_LOG_TABLES:
                        return jsonify({'error': 'Invalid table'}), 400
                    if operation == 'compress':
                        # Manually compress chunks
                        cur.execute(f"""
                            SELECT compress_chunk(c.schema_name||'.'||c.table_name)
                            FROM timescaledb_information.chunks c
                            WHERE c.hypertable_name = %s
                            AND c.range_end < NOW() - INTERVAL %s
                            AND NOT c.is_compressed
                        """, (tbl, older_than))
                        compressed = cur.rowcount
                        result['operations'].append({
                            'table': tbl,
                            'operation': 'compress',
                            'chunks_affected': compressed
                        })
                        
                    elif operation == 'drop_chunks':
                        # Drop old chunks (be careful!)
                        cur.execute(f"""
                            SELECT drop_chunks(%s, older_than => NOW() - INTERVAL %s)
                        """, (tbl, older_than))
                        result['operations'].append({
                            'table': tbl,
                            'operation': 'drop_chunks',
                            'older_than': older_than
                        })
                        
                    elif operation == 'vacuum':
                        # Vacuum analyze the table. `tbl` is whitelisted above;
                        # additionally use a quoted SQL identifier so the value
                        # can never be interpreted as arbitrary SQL.
                        cur.execute(
                            pg_sql.SQL("VACUUM ANALYZE {}").format(
                                pg_sql.Identifier(tbl)
                            )
                        )
                        result['operations'].append({
                            'table': tbl,
                            'operation': 'vacuum',
                            'status': 'completed'
                        })
                
                conn.commit()
                
                # Log the cleanup operation
                logging_service.log_activity(
                    action='log_cleanup',
                    resource_type='system',
                    resource_id='logs',
                    result='success',
                    metadata={
                        'operation': operation,
                        'tables': tables,
                        'older_than': older_than,
                        'results': result
                    }
                )
                
                return jsonify(result), 202
                
        finally:
            logging_service._put_connection(conn)
            
    except Exception as e:
        logger.error(f"Error during log cleanup: {e}")
        return jsonify({'error': 'Failed to execute cleanup operation'}), 500

def _get_suggested_actions(log: Dict) -> List[Dict[str, str]]:
    """
    Get suggested actions based on log type and content.
    """
    actions = []
    
    if log.get('metadata', {}).get('phase1_category') == 'USER_CRITICAL':
        actions.extend([
            {'action': 'investigate_user', 'label': 'Investigate User Activity'},
            {'action': 'block_user', 'label': 'Block User Access'},
            {'action': 'notify_admin', 'label': 'Notify Administrator'}
        ])
    elif log.get('metadata', {}).get('phase1_category') == 'DEVICE_ISSUES':
        actions.extend([
            {'action': 'restart_device', 'label': 'Restart Device'},
            {'action': 'check_connectivity', 'label': 'Check Device Connectivity'},
            {'action': 'view_device_logs', 'label': 'View Device Logs'}
        ])
    elif log.get('metadata', {}).get('phase1_category') == 'API_PROBLEMS':
        actions.extend([
            {'action': 'view_api_metrics', 'label': 'View API Metrics'},
            {'action': 'scale_service', 'label': 'Scale API Service'},
            {'action': 'restart_api', 'label': 'Restart API Container'}
        ])
    
    return actions

@logs_bp.route('/metrics/system', methods=['GET'])
@require_auth
def get_system_metrics():
    """
    Get real-time system metrics from containers and services.
    
    Returns:
        200: System metrics including containers, databases, services
        500: Server error
    """
    try:
        import docker
        import redis
        from pymongo import MongoClient
        
        metrics = {
            'containers': [],
            'database': {},
            'services': {},
            'alerts': {
                'critical': 0,
                'warning': 0,
                'info': 0
            }
        }
        
        # Get Docker container metrics
        try:
            client = docker.from_env()
            # Get all containers that start with "tesa-"
            all_containers = client.containers.list(all=True)
            containers = [c for c in all_containers if c.name.startswith('tesa-')]
            
            for container in containers:
                try:
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU percentage (handle different stat formats)
                    cpu_percent = 0.0
                    try:
                        cpu_stats = stats.get('cpu_stats', {})
                        precpu_stats = stats.get('precpu_stats', {})
                        
                        cpu_usage = cpu_stats.get('cpu_usage', {})
                        precpu_usage = precpu_stats.get('cpu_usage', {})
                        
                        if 'total_usage' in cpu_usage and 'total_usage' in precpu_usage:
                            cpu_delta = cpu_usage['total_usage'] - precpu_usage['total_usage']
                            
                            # Try different fields for system CPU
                            system_cpu = cpu_stats.get('system_cpu_usage', 0) or cpu_stats.get('system_usage', 0)
                            precpu_system = precpu_stats.get('system_cpu_usage', 0) or precpu_stats.get('system_usage', 0)
                            
                            system_delta = system_cpu - precpu_system
                            
                            # Get number of CPUs
                            num_cpus = len(cpu_usage.get('percpu_usage', [])) or 1
                            
                            if system_delta > 0.0 and cpu_delta > 0.0:
                                cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0
                    except Exception:
                        # If calculation fails, default to 0
                        pass
                    
                    # Calculate memory percentage
                    mem_percent = 0.0
                    try:
                        mem_stats = stats.get('memory_stats', {})
                        mem_usage = mem_stats.get('usage', 0)
                        mem_limit = mem_stats.get('limit', 0)
                        if mem_limit > 0:
                            mem_percent = (mem_usage / mem_limit) * 100.0
                    except Exception:
                        pass
                    
                    # Get container info
                    container_info = {
                        'name': container.name,
                        'status': 'healthy' if container.status == 'running' else 'unhealthy',
                        'cpu': round(cpu_percent, 2),
                        'memory': round(mem_percent, 2),
                        'uptime': container.attrs['State']['StartedAt'],
                        'restarts': container.attrs['RestartCount']
                    }
                    
                    metrics['containers'].append(container_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting stats for container {container.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error connecting to Docker: {e}")
        
        # Get database metrics
        # MongoDB
        try:
            # Get MongoDB connection info from environment (same as API uses)
            mongo_uri = os.getenv('MONGODB_URI')
            
            # Connect to MongoDB using the same connection as the API
            mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Get the database name from URI or default
            db_name = mongo_uri.split('/')[-1].split('?')[0] if '/' in mongo_uri else 'tesa_iot'
            db = mongo_client[db_name]
            
            # Test connectivity
            db.command('ping')
            
            # Get database statistics
            try:
                # Get database stats (works with iot_user permissions)
                db_stats = db.command('dbStats')
                data_size = db_stats.get('dataSize', 0)
                storage_size = db_stats.get('storageSize', 0)
                
                # Use larger of dataSize or storageSize for more accurate reporting
                size_bytes = max(data_size, storage_size)
                
                # Smart size formatting for better display
                if size_bytes >= (1024**3):  # GB
                    size_display = f"{round(size_bytes / (1024**3), 2)} GB"
                elif size_bytes >= (1024**2):  # MB  
                    size_display = f"{round(size_bytes / (1024**2), 2)} MB"
                elif size_bytes >= 1024:  # KB
                    size_display = f"{round(size_bytes / 1024, 2)} KB"
                else:  # Bytes
                    size_display = f"{size_bytes} bytes"
                
                # Get server status for connection count (if available)
                try:
                    server_status = db.command('serverStatus')
                    connections = server_status.get('connections', {}).get('current', 0)
                except:
                    # Fallback: count collections as a proxy for activity
                    connections = len(db.list_collection_names())
                
                metrics['database']['mongodb'] = {
                    'status': 'operational',
                    'connections': connections,
                    'size': size_display
                }
                
            except Exception as stats_error:
                logger.warning(f"MongoDB stats error (using basic info): {stats_error}")
                # Fallback to basic operational status
                try:
                    collections_count = len(db.list_collection_names())
                    metrics['database']['mongodb'] = {
                        'status': 'operational',
                        'connections': collections_count,  # Use collection count as proxy
                        'size': "Unknown"  # Cannot determine size without dbStats permission
                    }
                except:
                    metrics['database']['mongodb'] = {
                        'status': 'operational',
                        'connections': 0,
                        'size': "Unknown"
                    }
                
            mongo_client.close()
        except Exception as e:
            logger.error(f"Error getting MongoDB metrics: {e}")
            metrics['database']['mongodb'] = {'status': 'down', 'connections': 0, 'size': '0 GB'}
        
        # Redis
        try:
            redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379'))
            info = redis_client.info()
            
            metrics['database']['redis'] = {
                'status': 'operational',
                'memory': f"{round(info['used_memory'] / (1024**2), 2)} MB",
                'keys': redis_client.dbsize()
            }
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            metrics['database']['redis'] = {'status': 'down', 'memory': '0 MB', 'keys': 0}
        
        # TimescaleDB
        try:
            conn = logging_service._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get connection count
                cur.execute("SELECT count(*) as connections FROM pg_stat_activity WHERE datname = current_database()")
                connections = cur.fetchone()['connections']
                
                # Get database size
                cur.execute("SELECT pg_database_size(current_database()) as size")
                db_size = cur.fetchone()['size']
                
                metrics['database']['timescale'] = {
                    'status': 'operational',
                    'connections': connections,
                    'size': f"{round(db_size / (1024**3), 2)} GB"
                }
        except Exception as e:
            logger.error(f"Error getting TimescaleDB metrics: {e}")
            metrics['database']['timescale'] = {'status': 'down', 'connections': 0, 'size': '0 GB'}
        finally:
            if 'conn' in locals():
                logging_service._put_connection(conn)
        
        # Get service metrics - simplified version without logs
        try:
            # API service is running if we got here
            metrics['services']['api'] = {
                'status': 'operational',
                'latency': 0,
                'requests': 0
            }
            
            # Check MQTT by container status
            mqtt_container = next((c for c in metrics['containers'] if 'vernemq' in c['name']), None)
            metrics['services']['mqtt'] = {
                'status': 'operational' if mqtt_container else 'down',
                'clients': 0,
                'messages': 0
            }
            
            # Gateway is nginx
            gateway_container = next((c for c in metrics['containers'] if 'nginx' in c['name']), None)
            metrics['services']['gateway'] = {
                'status': 'operational' if gateway_container else 'down',
                'uptime': '99.99%',
                'requests': 0
            }
        except Exception as e:
            logger.error(f"Error calculating service metrics: {e}")
            
        # Try to get real metrics from logs if available
        try:
            conn = logging_service._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # API metrics from device telemetry (actual data)
                cur.execute("""
                    SELECT 
                        COUNT(*) as requests,
                        AVG(EXTRACT(EPOCH FROM (NOW() - time))) as avg_latency_seconds
                    FROM device_telemetry 
                    WHERE time > NOW() - INTERVAL '1 hour'
                """)
                api_stats = cur.fetchone()
                
                metrics['services']['api'] = {
                    'status': 'operational',
                    'latency': round(api_stats['avg_latency_seconds'] or 0, 2),
                    'requests': api_stats['requests'] or 0
                }
                
                # MQTT metrics (from device events)
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT device_id) as clients,
                        COUNT(*) as messages
                    FROM device_events 
                    WHERE event_type LIKE '%mqtt%' 
                    AND time > NOW() - INTERVAL '1 hour'
                """)
                mqtt_stats = cur.fetchone()
                
                metrics['services']['mqtt'] = {
                    'status': 'operational',
                    'clients': mqtt_stats['clients'] or 0,
                    'messages': mqtt_stats['messages'] or 0
                }
                
                # Gateway uptime
                metrics['services']['gateway'] = {
                    'status': 'operational',
                    'uptime': '99.99%',
                    'requests': api_stats['requests'] or 0
                }
                
                # Count alerts from device events
                cur.execute("""
                    SELECT 
                        severity as level,
                        COUNT(*) as count
                    FROM device_events
                    WHERE time > NOW() - INTERVAL '1 hour'
                    AND severity IN ('critical', 'error', 'warning')
                    GROUP BY severity
                """)
                
                for row in cur.fetchall():
                    if row['level'] == 'critical':
                        metrics['alerts']['critical'] = row['count']
                    elif row['level'] == 'error':
                        metrics['alerts']['critical'] += row['count'] // 10  # Some errors are critical
                        metrics['alerts']['warning'] += row['count'] % 10
                    elif row['level'] == 'warning':
                        metrics['alerts']['warning'] += row['count']
                
        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
        finally:
            if 'conn' in locals():
                logging_service._put_connection(conn)
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return jsonify({'error': 'Failed to retrieve system metrics'}), 500

# Device Log Endpoints - Integration with Activity Logs (LEGACY - DISABLED)
# @logs_bp.route('/device/health-stats', methods=['GET'])
# @require_auth
def get_device_health_stats_legacy():
    """
    Get aggregated device health statistics (LEGACY - REPLACED)
    
    Returns:
        200: Device health statistics
        500: Server error
    """
    try:
        from ..core.database import get_db
        
        db = get_db()
        
        # Get device counts
        total_devices = db.devices.count_documents({})
        online_devices = db.devices.count_documents({'status': 'online'})
        offline_devices = db.devices.count_documents({'status': {'$ne': 'online'}})
        
        # Get devices with recent errors
        from datetime import datetime, timedelta
        error_window = datetime.now() - timedelta(hours=24)
        devices_with_errors = db.device_logs.distinct('device_id', {
            'timestamp': {'$gte': error_window},
            'level': {'$in': ['ERROR', 'CRITICAL']}
        })
        
        # Calculate health scores
        connectivity_score = (online_devices / max(total_devices, 1)) * 100
        
        # Get telemetry success rate
        telemetry_success = db.device_telemetry.count_documents({
            'timestamp': {'$gte': error_window}
        })
        telemetry_errors = db.telemetry_errors.count_documents({
            'timestamp': {'$gte': error_window}
        })
        telemetry_score = (telemetry_success / max(telemetry_success + telemetry_errors, 1)) * 100
        
        # Security score based on certificate status
        devices_with_valid_certs = db.devices.count_documents({
            'certificate_status': 'active'
        })
        security_score = (devices_with_valid_certs / max(total_devices, 1)) * 100
        
        # Overall health
        overall_health = (connectivity_score + telemetry_score + security_score) / 3
        
        return jsonify({
            'total_devices': total_devices,
            'online_devices': online_devices,
            'offline_devices': offline_devices,
            'devices_with_errors': len(devices_with_errors),
            'connectivity_score': round(connectivity_score, 1),
            'telemetry_score': round(telemetry_score, 1),
            'security_score': round(security_score, 1),
            'overall_health': round(overall_health, 1)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting device health stats: {e}")
        return jsonify({'error': 'Failed to retrieve device health statistics'}), 500

# Duplicate function removed - using the better version below that returns proper format

@logs_bp.route('/device/category-breakdown', methods=['GET'])
@require_auth
def get_device_log_category_breakdown():
    """
    Get breakdown of device logs by category.
    
    Returns:
        200: Category breakdown
        500: Server error
    """
    try:
        from ..core.database import get_db
        from datetime import datetime, timedelta
        
        db = get_db()
        
        # Get logs from last 24 hours
        time_window = datetime.now() - timedelta(hours=24)
        
        # Aggregate by category
        pipeline = [
            {'$match': {'timestamp': {'$gte': time_window}}},
            {'$group': {
                '_id': '$category',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(db.device_logs.aggregate(pipeline))
        
        # Convert to dictionary
        breakdown = {}
        for result in results:
            category = result['_id'] or 'unknown'
            breakdown[category] = result['count']
        
        # Ensure all categories are present
        for category in ['connectivity', 'telemetry', 'health', 'security', 'firmware', 'configuration', 'performance']:
            if category not in breakdown:
                breakdown[category] = 0
        
        return jsonify({
            'data': {
                'breakdown': breakdown
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting category breakdown: {e}")
        return jsonify({'error': 'Failed to retrieve category breakdown'}), 500

@logs_bp.route('/device/<device_id>', methods=['GET'])
@require_auth
def get_device_logs(device_id):
    """
    Get logs for a specific device.
    
    Path Parameters:
        device_id: The device identifier
        
    Query Parameters:
        limit: Number of logs to return (default: 100, max: 1000)
        log_types: Comma-separated list of log types
        categories: Comma-separated list of categories
        start_time: ISO format start time
        end_time: ISO format end time
        
    Returns:
        200: Device logs
        404: Device not found
        500: Server error
    """
    try:
        from ..services.device_logs_service import device_logs_service
        
        # Check if device exists
        from ..core.database import get_db
        db = get_db()
        
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Parse parameters
        limit = min(int(request.args.get('limit', 100)), 1000)
        log_types = request.args.get('log_types', '').split(',') if request.args.get('log_types') else None
        categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
        
        # Get logs
        logs = device_logs_service.get_device_logs(
            device_id=device_id,
            limit=limit,
            log_types=log_types,
            categories=categories
        )
        
        return jsonify({
            'logs': logs
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting device logs: {e}")
        return jsonify({'error': 'Failed to retrieve device logs'}), 500

# ===============================================================================
# MISSING ENDPOINTS IMPLEMENTATION - Phase 1 Activity Logs
# ===============================================================================

@logs_bp.route('/critical-events', methods=['GET'])
@require_auth
def get_critical_events():
    """
    Get critical events that require immediate attention.
    
    Query Parameters:
        timeRange: Time range for events (1h, 6h, 24h, 7d)
        limit: Number of events to return (default: 50, max: 200)
        
    Returns:
        200: Critical events list
        500: Server error
    """
    try:
        # Parse parameters
        time_range = request.args.get('timeRange', '24h')
        limit = min(int(request.args.get('limit', 50)), 200)
        
        # Parse time range
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = datetime.utcnow() - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = datetime.utcnow() - timedelta(days=days)
        else:
            start_time = datetime.utcnow() - timedelta(hours=24)
        
        # ACL enforcement
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Build filters for critical events
        filters = {
            'level': ['critical', 'error'],
            'start_time': start_time,
            'log_type': ['system', 'security', 'device']
        }
        
        # Query critical events
        logs = logging_service.query_logs(
            filters,
            limit=limit,
            offset=0,
            user_role=user_role,
            user_org_id=user_org_id
        )
        
        # Transform to expected format
        events = []
        unacknowledged_count = 0
        
        for log in logs:
            event = {
                'id': str(log.get('id', f"event_{len(events)}")),
                'timestamp': log['time'].isoformat() if hasattr(log['time'], 'isoformat') else log['time'],
                'type': log.get('log_type', 'system'),
                'severity': 'critical',
                'message': log.get('message', ''),
                'source': log.get('source', 'unknown'),
                'resolved': False,  # For now, assume all critical events are unresolved
                'resolvedAt': None,
                'acknowledgedBy': None
            }
            events.append(event)
            unacknowledged_count += 1
        
        return jsonify({
            'events': events,
            'unacknowledgedCount': unacknowledged_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting critical events: {e}")
        return jsonify({'error': 'Failed to retrieve critical events'}), 500

@logs_bp.route('/activity/realtime', methods=['GET'])
@require_auth
def get_realtime_activity_logs():
    """
    Get real-time activity logs for live monitoring.
    
    Query Parameters:
        limit: Number of logs to return (default: 50, max: 200)
        severity: Comma-separated list of severity levels
        category: Comma-separated list of categories
        
    Returns:
        200: Real-time activity logs and stats
        500: Server error
    """
    try:
        # Parse parameters
        limit = min(int(request.args.get('limit', 50)), 200)
        severity_filter = [s.strip().lower() for s in request.args.get('severity', '').split(',') if s.strip()] if request.args.get('severity') else []
        category_filter = [c.strip().lower() for c in request.args.get('category', '').split(',') if c.strip()] if request.args.get('category') else []
        
        # ACL enforcement
        user_role = g.current_user.get('role')
        user_org_id = g.current_user.get('organization_id')
        
        # Get recent activity logs (last hour for real-time)
        conn = logging_service._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build ACL filter
                base_params = []
                where_clauses = ["time >= NOW() - INTERVAL '1 hour'"]

                if user_role == 'organization_admin' and user_org_id:
                    where_clauses.append("organization_id = %s")
                    base_params.append(user_org_id)

                if severity_filter:
                    status_filters = set()
                    for severity in severity_filter:
                        status_filters.update(SEVERITY_STATUS_MAP.get(severity, []))
                    if status_filters:
                        where_clauses.append("LOWER(status) = ANY(%s)")
                        base_params.append([status.lower() for status in status_filters])

                if category_filter:
                    where_clauses.append("LOWER(COALESCE(NULLIF(resource_type, ''), resource, 'system')) = ANY(%s)")
                    base_params.append(category_filter)

                where_sql = " AND ".join(where_clauses)
                
                # Get recent activity logs
                query = f"""
                    SELECT * FROM activity_logs
                    WHERE {where_sql}
                    ORDER BY time DESC
                    LIMIT %s
                """
                query_params = list(base_params)
                query_params.append(limit)

                cur.execute(query, query_params)
                activities = cur.fetchall()

                # Get stats
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE LOWER(status) = ANY(%s)) as failures,
                        COUNT(*) FILTER (WHERE LOWER(status) = ANY(%s)) as warnings,
                        COUNT(*) FILTER (WHERE time >= NOW() - INTERVAL '5 minutes') as recent
                    FROM activity_logs
                    WHERE {where_sql}
                """
                stats_params = list(base_params)
                stats_params.append(ERROR_STATUS_VALUES)
                stats_params.append(WARNING_STATUS_VALUES)
                cur.execute(stats_query, stats_params)
                stats_row = cur.fetchone()

                category_query = f"""
                    SELECT 
                        LOWER(COALESCE(NULLIF(resource_type, ''), resource, 'system')) as category,
                        COUNT(*) as count
                    FROM activity_logs
                    WHERE {where_sql}
                    GROUP BY 1
                """
                cur.execute(category_query, base_params)
                category_rows = cur.fetchall()

                # Format response
                logs = []
                for activity in activities:
                    raw_details = activity.get('details') or activity.get('metadata')
                    if isinstance(raw_details, str):
                        try:
                            details = json.loads(raw_details)
                        except json.JSONDecodeError:
                            details = {'raw': raw_details}
                    elif isinstance(raw_details, dict):
                        details = raw_details
                    else:
                        details = {}

                    status_value = (activity.get('status') or '').lower()
                    if status_value in ERROR_STATUS_VALUES:
                        severity = 'error'
                    elif status_value in WARNING_STATUS_VALUES:
                        severity = 'warning'
                    else:
                        severity = 'info'

                    log_entry = {
                        'id': str(activity.get('id', len(logs))),
                        'timestamp': activity['time'].isoformat() if hasattr(activity['time'], 'isoformat') else activity['time'],
                        'user': {
                            'id': activity.get('user_id', 'unknown'),
                            'name': activity.get('user_email') or 'Unknown User',
                            'email': activity.get('user_email', 'unknown@example.com'),
                            'role': 'user'
                        },
                        'action': activity.get('action', 'unknown'),
                        'category': activity.get('resource_type') or activity.get('resource') or 'system',
                        'severity': severity,
                        'status': activity.get('status', 'unknown'),
                        'details': details
                    }
                    logs.append(log_entry)

                stats_row = stats_row or {'total': 0, 'failures': 0, 'warnings': 0, 'recent': 0}
                total = stats_row.get('total', 0) or 0
                failures = stats_row.get('failures', 0) or 0
                warnings = stats_row.get('warnings', 0) or 0
                info_count = max(total - failures - warnings, 0)

                by_category = {row['category']: row['count'] for row in category_rows} if category_rows else {}

                stats = {
                    'total': total,
                    'failures': failures,
                    'recent': stats_row.get('recent', 0) or 0,
                    'byCategory': by_category,
                    'bySeverity': {
                        'info': info_count,
                        'warning': warnings,
                        'error': failures
                    }
                }
                
                return jsonify({
                    'logs': logs,
                    'stats': stats
                }), 200
                
        finally:
            logging_service._put_connection(conn)
            
    except Exception as e:
        logger.error(f"Error getting real-time activity logs: {e}")
        return jsonify({'error': 'Failed to retrieve real-time activity logs'}), 500

@logs_bp.route('/device/health-stats', methods=['GET'])
@require_auth
def get_device_health_stats():
    """
    Get aggregated device health statistics.
    
    Returns:
        200: Device health statistics
        500: Server error
    """
    try:
        from ..core.database import get_db
        
        db = get_db()
        
        # Get device counts
        total_devices = db.devices.count_documents({})
        online_devices = db.devices.count_documents({'status': 'online'})
        offline_devices = db.devices.count_documents({'status': {'$ne': 'online'}})
        
        # Get devices with recent errors
        from datetime import datetime, timedelta
        error_window = datetime.now() - timedelta(hours=24)
        devices_with_errors = db.device_logs.distinct('device_id', {
            'timestamp': {'$gte': error_window},
            'level': {'$in': ['ERROR', 'CRITICAL']}
        })
        
        # Calculate health scores
        connectivity_score = (online_devices / max(total_devices, 1)) * 100
        
        # Get telemetry success rate
        telemetry_success = db.device_telemetry.count_documents({
            'timestamp': {'$gte': error_window}
        })
        telemetry_errors = db.telemetry_errors.count_documents({
            'timestamp': {'$gte': error_window}
        }) if 'telemetry_errors' in db.list_collection_names() else 0
        telemetry_score = (telemetry_success / max(telemetry_success + telemetry_errors, 1)) * 100
        
        # Security score based on certificate status
        devices_with_valid_certs = db.devices.count_documents({
            'certificate_status': 'active'
        })
        security_score = (devices_with_valid_certs / max(total_devices, 1)) * 100
        
        # Overall health
        overall_health = (connectivity_score + telemetry_score + security_score) / 3
        
        return jsonify({
            'data': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': offline_devices,
                'devices_with_errors': len(devices_with_errors),
                'connectivity_score': round(connectivity_score, 1),
                'telemetry_score': round(telemetry_score, 1),
                'security_score': round(security_score, 1),
                'overall_health': round(overall_health, 1)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting device health stats: {e}")
        return jsonify({'error': 'Failed to retrieve device health statistics'}), 500

@logs_bp.route('/device/recent', methods=['GET'])
@require_auth
def get_recent_device_logs():
    """
    Get recent device logs across all devices.
    
    Query Parameters:
        limit: Number of logs to return (default: 10, max: 100)
        categories: Comma-separated list of categories to filter
        severity: Comma-separated list of severity levels to filter
        
    Returns:
        200: Recent device logs
        500: Server error
    """
    try:
        from ..core.database import get_db
        
        # Parse parameters
        limit = min(int(request.args.get('limit', 10)), 100)
        categories = request.args.get('categories', '').split(',') if request.args.get('categories') else None
        severity = request.args.get('severity', '').split(',') if request.args.get('severity') else None
        
        db = get_db()
        
        # Build query
        query = {}
        if categories:
            query['category'] = {'$in': categories}
        if severity:
            query['level'] = {'$in': [s.upper() for s in severity]}
        
        # Get recent logs
        logs = list(db.device_logs.find(query).sort('timestamp', -1).limit(limit))
        
        # Format logs
        formatted_logs = []
        for log in logs:
            # Get device name
            device = db.devices.find_one({'device_id': log.get('device_id')})
            
            formatted_logs.append({
                'device_id': log.get('device_id'),
                'device_name': device.get('name') if device else log.get('device_id'),
                'category': log.get('category', 'unknown'),
                'severity': log.get('level', 'INFO'),
                'message': log.get('message', ''),
                'timestamp': log.get('timestamp').isoformat() if log.get('timestamp') else datetime.now().isoformat()
            })
        
        return jsonify({
            'data': {
                'logs': formatted_logs
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent device logs: {e}")
        return jsonify({'error': 'Failed to retrieve recent device logs'}), 500
