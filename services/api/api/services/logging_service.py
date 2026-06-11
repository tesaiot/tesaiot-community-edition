# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Comprehensive Logging Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import ThreadedConnectionPool
# import aiohttp  # Removed - using requests instead for sync operations
from flask import g, request
import time
import traceback


logger = logging.getLogger(__name__)

class LogType(Enum):
    SYSTEM = "system"
    ACTIVITY = "activity"
    ERROR = "error"
    CONSOLE = "console"
    CONTAINER = "container"
    API = "api"
    SECURITY = "security"
    # Phase 1 additions
    USER_CRITICAL = "user_critical"
    DEVICE_ISSUES = "device_issues"
    API_PROBLEMS = "api_problems"

class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    WARNING = "warning"
    HIGH = "high"
    ERROR = "error"
    CRITICAL = "critical"

class LoggingService:
    """Comprehensive logging service for TESA IoT Platform"""
    
    def __init__(self):
        """Initialize the logging service with TimescaleDB connection pool"""
        self.pool = None
        self._init_connection_pool()
        self._setup_python_logging()
        
    def _init_connection_pool(self):
        """Initialize PostgreSQL/TimescaleDB connection pool"""
        try:
            # Build URI from environment variables
            postgres_host = os.getenv('POSTGRES_HOST', 'tesa-timescaledb')
            postgres_port = os.getenv('POSTGRES_PORT', '5432')
            postgres_user = os.getenv('POSTGRES_USER', 'postgres')
            postgres_password = os.getenv('POSTGRES_PASSWORD', '')  # no default; fails closed
            postgres_db = os.getenv('POSTGRES_DB', 'tesa_telemetry')
            
            postgres_uri = os.getenv('POSTGRES_URI', 
                f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}')
            
            # Parse connection string or use individual params
            import urllib.parse
            parsed = urllib.parse.urlparse(postgres_uri)
            
            # Use parsed values or fall back to individual env vars
            db_host = parsed.hostname or postgres_host
            db_port = parsed.port or int(postgres_port)
            db_name = parsed.path[1:] if parsed.path else postgres_db
            db_user = parsed.username or postgres_user
            db_password = parsed.password or postgres_password
            
            # Ensure host is not None (None causes Unix socket connection)
            if not db_host:
                raise ValueError("PostgreSQL host not configured. Set POSTGRES_HOST or POSTGRES_URI")
            
            self.pool = ThreadedConnectionPool(
                minconn=5,          # Increased from 2 for better concurrency
                maxconn=20,         # Increased from 10 for activity logs endpoint
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                # Add connection optimization parameters
                connect_timeout=10,  # 10 second connection timeout
                application_name='tesa_iot_logging_service'
            )
            logger.info("TimescaleDB connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TimescaleDB pool: {e}")
            raise
    
    def _setup_python_logging(self):
        """Setup Python logging to also write to TimescaleDB"""
        handler = TimescaleDBHandler(self)
        handler.setLevel(logging.INFO)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
    
    def _get_connection(self):
        """Get a connection from the pool"""
        return self.pool.getconn()
    
    def _get_connection_with_retry(self, max_retries=3, retry_delay=0.5):
        """Get a connection from the pool with retry logic"""
        for attempt in range(max_retries):
            try:
                return self.pool.getconn()
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise
    
    def _put_connection(self, conn):
        """Return a connection to the pool"""
        self.pool.putconn(conn)
    
    def log_system(self, level: LogLevel, message: str, source: str, 
                        metadata: Optional[Dict] = None, **kwargs):
        """Log system-level events"""
        self._insert_log(
            log_type=LogType.SYSTEM,
            level=level,
            message=message,
            source=source,
            metadata=metadata,
            **kwargs
        )
    
    def log_activity(self, action: str, resource_type: str, 
                          resource_id: str, result: str = "success",
                          duration_ms: Optional[int] = None, **kwargs):
        """Log user activity"""
        user_id = kwargs.get('user_id') or (g.current_user.get('_id') if hasattr(g, 'current_user') else None)
        org_id = kwargs.get('organization_id') or (g.current_user.get('organizationId') if hasattr(g, 'current_user') else None)
        
        # Build enhanced metadata
        enhanced_metadata = kwargs.get('metadata', {})
        enhanced_metadata.update({
            'timestamp': datetime.utcnow().isoformat(),
            'action_type': action,
            'resource_details': {
                'type': resource_type,
                'id': resource_id
            }
        })
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO activity_logs 
                    (time, user_id, organization_id, action, resource_type, 
                     resource_id, result, duration_ms, client_ip, user_agent, metadata)
                    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(user_id) if user_id else None,
                    str(org_id) if org_id else None,
                    action,
                    resource_type,
                    resource_id,
                    result,
                    duration_ms,
                    request.remote_addr if request else None,
                    request.headers.get('User-Agent') if request else None,
                    json.dumps(enhanced_metadata)
                ))
                conn.commit()
                
                # Broadcast significant activities
                if result == 'failure' or enhanced_metadata.get('impact_level') == 'high':
                    self._broadcast_activity_alert(action, resource_type, resource_id, result, user_id, org_id, enhanced_metadata)
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            conn.rollback()
        finally:
            self._put_connection(conn)
    
    def log_phase1_event(self, category: str, level: LogLevel, message: str, 
                        source: str, metadata: Optional[Dict] = None, **kwargs):
        """Log Phase 1 categorized events for Activity Logs"""
        enhanced_metadata = metadata or {}
        enhanced_metadata.update({
            'phase1_category': category,
            'event_source': source,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        self._insert_log(
            log_type=LogType.ACTIVITY,
            level=level,
            message=message,
            source=source,
            metadata=enhanced_metadata,
            **kwargs
        )
    
    def _broadcast_activity_alert(self, action: str, resource_type: str, resource_id: str,
                                 result: str, user_id: str, org_id: str, metadata: Dict):
        """Broadcast activity alerts for significant events"""
        try:
            # This could be enhanced to send WebSocket messages, webhooks, etc.
            logger.info(f"Activity Alert: {action} on {resource_type}:{resource_id} - {result}")
        except Exception as e:
            logger.error(f"Failed to broadcast activity alert: {e}")
    
    def log_error(self, error: Exception, context: Optional[Dict] = None, **kwargs):
        """Log error events with stack trace"""
        metadata = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'context': context or {}
        }
        
        self._insert_log(
            log_type=LogType.ERROR,
            level=LogLevel.ERROR,
            message=f"{type(error).__name__}: {str(error)}",
            source=kwargs.get('source', 'api'),
            metadata=metadata,
            **kwargs
        )
    
    def log_api_request(self, endpoint: str, method: str, 
                             status_code: int, response_time_ms: int,
                             error_message: Optional[str] = None, **kwargs):
        """Log API request metrics"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO api_metrics
                    (time, endpoint, method, status_code, response_time_ms,
                     request_size_bytes, response_size_bytes, user_id, 
                     organization_id, trace_id, error_message)
                    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    endpoint,
                    method,
                    status_code,
                    response_time_ms,
                    kwargs.get('request_size_bytes'),
                    kwargs.get('response_size_bytes'),
                    kwargs.get('user_id'),
                    kwargs.get('organization_id'),
                    kwargs.get('trace_id'),
                    error_message
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log API metrics: {e}")
            conn.rollback()
        finally:
            self._put_connection(conn)
    
    def log_security_event(self, event_type: str, severity: str,
                                details: Dict, **kwargs):
        """Log security-related events"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO security_logs
                    (time, event_type, severity, user_id, organization_id,
                     source_ip, target_resource, action_taken, threat_score, details)
                    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    event_type,
                    severity,
                    kwargs.get('user_id'),
                    kwargs.get('organization_id'),
                    kwargs.get('source_ip', request.remote_addr if request else None),
                    kwargs.get('target_resource'),
                    kwargs.get('action_taken', 'logged'),
                    kwargs.get('threat_score', 0),
                    json.dumps(details)
                ))
                conn.commit()
                
                # Send critical security alerts
                if severity == 'critical':
                    self._send_security_alert(event_type, details)
                    
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
            conn.rollback()
        finally:
            self._put_connection(conn)
    
    def _insert_log(self, log_type: LogType, level: LogLevel, 
                         message: str, source: str, metadata: Optional[Dict] = None,
                         **kwargs):
        """Insert a log entry into the system_logs table"""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO system_logs
                    (time, log_type, level, source, container_name, 
                     organization_id, user_id, device_id, message, metadata,
                    trace_id, span_id, request_id, client_ip, user_agent)
                    VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    log_type.value,
                    level.value,
                    source,
                    kwargs.get('container_name', os.getenv('CONTAINER_NAME', 'tesa-api')),
                    kwargs.get('organization_id'),
                    kwargs.get('user_id'),
                    kwargs.get('device_id'),
                    message,
                    json.dumps(metadata) if metadata else None,
                    kwargs.get('trace_id'),
                    kwargs.get('span_id'),
                    kwargs.get('request_id'),
                    kwargs.get('client_ip', request.remote_addr if request else None),
                    kwargs.get('user_agent', request.headers.get('User-Agent') if request else None)
                ))
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to insert log: {e}")
            conn.rollback()
        finally:
            self._put_connection(conn)

    def bulk_insert_logs(self, logs: List[Dict[str, Any]]) -> int:
        """
        Bulk insert multiple log entries efficiently.
        
        Args:
            logs: List of log dictionaries with required fields
            
        Returns:
            Number of logs successfully inserted
        """
        if not logs:
            return 0
            
        conn = self._get_connection()
        inserted_count = 0
        
        try:
            with conn.cursor() as cur:
                # Prepare data for bulk insert
                values = []
                for log in logs:
                    # Ensure all required fields are present
                    values.append((
                        log.get('time', datetime.utcnow()),
                        log.get('log_type', LogType.SYSTEM.value),
                        log.get('level', LogLevel.INFO.value),
                        log.get('source', 'unknown'),
                        log.get('container_name'),
                        log.get('organization_id'),
                        log.get('user_id'),
                        log.get('device_id'),
                        log.get('message', ''),
                        json.dumps(log.get('metadata', {})),
                        log.get('trace_id'),
                        log.get('span_id'),
                        log.get('request_id'),
                        log.get('client_ip'),
                        log.get('user_agent')
                    ))
                
                # Use execute_values for efficient bulk insert
                execute_values(
                    cur,
                    """
                    INSERT INTO system_logs
                    (time, log_type, level, source, container_name,
                     organization_id, user_id, device_id, message, metadata,
                     trace_id, span_id, request_id, client_ip, user_agent)
                    VALUES %s
                    """,
                    values,
                    template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                )
                
                inserted_count = cur.rowcount
                conn.commit()
                
                logger.info(f"Successfully bulk inserted {inserted_count} logs")
                
        except Exception as e:
            logger.error(f"Failed to bulk insert logs: {e}")
            conn.rollback()
            raise
        finally:
            self._put_connection(conn)
            
        return inserted_count

    def query_logs(self, filters: Dict[str, Any], 
                        limit: int = 100, offset: int = 0,
                        user_role: Optional[str] = None,
                        user_org_id: Optional[str] = None) -> List[Dict]:
        """Query logs with filters and strict ACL enforcement"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build WHERE clause
                where_clauses = []
                params = []
                
                # ✅ CRITICAL: ACL ENFORCEMENT - Organization Admin filtering
                if user_role == 'organization_admin' and user_org_id:
                    # Organization Admins can ONLY see their organization's data
                    where_clauses.append("organization_id = %s")
                    params.append(user_org_id)
                    logger.info(f"ACL: Organization Admin {user_org_id} filtered to own org data only")
                elif user_role == 'organization_admin' and not user_org_id:
                    # No org ID = no access for org admins
                    logger.warning("ACL: Organization Admin without org ID - access denied")
                    return []
                # TESA Admins (admin, super_admin) can see all data - no additional filtering
                
                if 'log_type' in filters:
                    where_clauses.append("log_type = %s")
                    params.append(filters['log_type'])
                
                if 'level' in filters:
                    where_clauses.append("level = %s")
                    params.append(filters['level'])
                
                if 'source' in filters:
                    where_clauses.append("source = %s")
                    params.append(filters['source'])
                
                if 'organization_id' in filters:
                    # Additional org filter (must still respect ACL)
                    if user_role == 'organization_admin' and filters['organization_id'] != user_org_id:
                        # Org admin trying to access different org data - denied
                        logger.warning(f"ACL: Organization Admin {user_org_id} denied access to org {filters['organization_id']}")
                        return []
                    where_clauses.append("organization_id = %s")
                    params.append(filters['organization_id'])
                
                if 'user_id' in filters:
                    where_clauses.append("user_id = %s")
                    params.append(filters['user_id'])
                
                if 'device_id' in filters:
                    where_clauses.append("device_id = %s")
                    params.append(filters['device_id'])
                
                if 'start_time' in filters:
                    where_clauses.append("time >= %s")
                    params.append(filters['start_time'])
                
                if 'end_time' in filters:
                    where_clauses.append("time <= %s")
                    params.append(filters['end_time'])
                
                if 'search' in filters:
                    where_clauses.append("message ILIKE %s")
                    params.append(f"%{filters['search']}%")
                
                where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Execute query
                query = f"""
                    SELECT * FROM system_logs
                    WHERE {where_sql}
                    ORDER BY time DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                
                cur.execute(query, params)
                logs = cur.fetchall()
                
                # Convert to list of dicts
                return [dict(log) for log in logs]
                
        except Exception as e:
            logger.error(f"Failed to query logs: {e}")
            return []
        finally:
            self._put_connection(conn)
    
    def get_log_analytics(self, time_range: str = '1h',
                               user_role: Optional[str] = None,
                               user_org_id: Optional[str] = None) -> Dict[str, Any]:
        """Get log analytics for dashboard with ACL enforcement"""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Parse time range
                if time_range.endswith('h'):
                    interval = f"{time_range[:-1]} hours"
                elif time_range.endswith('d'):
                    interval = f"{time_range[:-1]} days"
                else:
                    interval = "1 hour"
                
                # ✅ CRITICAL: Build ACL filter for analytics
                org_filter = ""
                org_params = []
                
                if user_role == 'organization_admin' and user_org_id:
                    org_filter = "AND organization_id = %s"
                    org_params = [user_org_id]
                    logger.info(f"ACL: Analytics filtered for org admin {user_org_id}")
                elif user_role == 'organization_admin' and not user_org_id:
                    logger.warning("ACL: Organization Admin without org ID - analytics denied")
                    return {}
                
                # Get log statistics
                cur.execute(f"""
                    SELECT 
                        log_type,
                        level,
                        COUNT(*) as count
                    FROM system_logs
                    WHERE time >= NOW() - INTERVAL '{interval}'
                        {org_filter}
                    GROUP BY log_type, level
                """, org_params)
                log_stats = cur.fetchall()
                
                # Get error trends
                cur.execute(f"""
                    SELECT 
                        time_bucket('5 minutes', time) as bucket,
                        COUNT(*) as error_count
                    FROM system_logs
                    WHERE level IN ('error', 'critical')
                        AND time >= NOW() - INTERVAL '{interval}'
                        {org_filter}
                    GROUP BY bucket
                    ORDER BY bucket
                """, org_params)
                error_trends = cur.fetchall()
                
                # Get top error sources
                cur.execute(f"""
                    SELECT 
                        source,
                        COUNT(*) as error_count
                    FROM system_logs
                    WHERE level IN ('error', 'critical')
                        AND time >= NOW() - INTERVAL '{interval}'
                        {org_filter}
                    GROUP BY source
                    ORDER BY error_count DESC
                    LIMIT 10
                """, org_params)
                top_error_sources = cur.fetchall()
                
                # Get API performance stats (filter by org for org admins)
                api_filter = org_filter.replace('organization_id', 'organization_id') if org_filter else ""
                cur.execute(f"""
                    SELECT 
                        endpoint,
                        method,
                        COUNT(*) as request_count,
                        AVG(response_time_ms) as avg_response_time,
                        MAX(response_time_ms) as max_response_time,
                        percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time
                    FROM api_metrics
                    WHERE time >= NOW() - INTERVAL '{interval}'
                        {api_filter}
                    GROUP BY endpoint, method
                    ORDER BY request_count DESC
                    LIMIT 20
                """, org_params)
                api_stats = cur.fetchall()
                
                return {
                    'log_statistics': [dict(row) for row in log_stats],
                    'error_trends': [dict(row) for row in error_trends],
                    'top_error_sources': [dict(row) for row in top_error_sources],
                    'api_performance': [dict(row) for row in api_stats],
                    'filtered_for_org': user_org_id if user_role == 'organization_admin' else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get log analytics: {e}")
            return {}
        finally:
            self._put_connection(conn)
    
    def _send_security_alert(self, event_type: str, details: Dict):
        """Send security alert via webhook"""
        webhook_url = os.getenv('SECURITY_WEBHOOK_URL')
        if not webhook_url:
            return

        try:
            # SSRF guard: enforce http(s), resolve the hostname and reject
            # loopback/link-local/private/multicast targets (incl. the
            # 169.254.169.254 metadata IP) unless ALLOW_PRIVATE_WEBHOOKS=true.
            from ..utils.validation import validate_webhook_url
            url_ok, url_reason = validate_webhook_url(webhook_url)
            if not url_ok:
                logger.error(f"SECURITY_WEBHOOK_URL rejected (SSRF guard): {url_reason}")
                return

            import requests
            payload = {
                'event_type': event_type,
                'severity': 'critical',
                'timestamp': datetime.utcnow().isoformat(),
                'details': details,
                'platform': 'tesa-iot'
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {os.getenv('SECURITY_WEBHOOK_TOKEN', '')}"
            }

            response = requests.post(
                webhook_url, json=payload, headers=headers,
                timeout=(5, 10),  # (connect, read)
                allow_redirects=False
            )
            if response.status_code != 200:
                logger.error(f"Failed to send security alert: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending security alert: {e}")
    
    def close(self):
        """Close the connection pool"""
        if self.pool:
            self.pool.closeall()


class TimescaleDBHandler(logging.Handler):
    """Python logging handler that writes to TimescaleDB"""
    
    def __init__(self, logging_service: LoggingService):
        super().__init__()
        self.logging_service = logging_service
    
    def emit(self, record):
        """Emit a log record to TimescaleDB"""
        try:
            # Map Python log levels to our LogLevel enum
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL
            }
            
            level = level_map.get(record.levelno, LogLevel.INFO)
            
            # Extract additional context
            metadata = {}
            if hasattr(record, 'exc_info') and record.exc_info:
                metadata['exception'] = {
                    'type': record.exc_info[0].__name__,
                    'message': str(record.exc_info[1]),
                    'traceback': self.format(record)
                }
            
            # Log directly in sync context
            self.logging_service.log_system(
                level=level,
                message=record.getMessage(),
                source=record.name,
                metadata=metadata,
                container_name=os.getenv('CONTAINER_NAME', 'tesa-api')
            )
        except Exception:
            self.handleError(record)


# Global logging service instance
logging_service = LoggingService()

# Middleware for API request logging
class LoggingMiddleware:
    """Flask middleware for automatic API request logging"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
    
    def _before_request(self):
        """Called before each request"""
        g.request_start_time = time.time()
        g.request_id = request.headers.get('X-Request-ID', 
                                          f"{time.time()}-{os.getpid()}")
    
    def _after_request(self, response):
        """Called after each request"""
        if hasattr(g, 'request_start_time'):
            # Calculate response time
            response_time_ms = int((time.time() - g.request_start_time) * 1000)
            
            # Get user info safely
            user_id = None
            org_id = None
            if hasattr(g, 'current_user') and g.current_user:
                user_id = g.current_user.get('_id')
                org_id = g.current_user.get('organization_id') or g.current_user.get('organizationId')
            
            # Log API request
            logging_service.log_api_request(
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                request_size_bytes=request.content_length,
                response_size_bytes=response.content_length,
                user_id=user_id,
                organization_id=org_id,
                trace_id=g.get('request_id'),
                error_message=None if response.status_code < 400 else response.get_data(as_text=True)[:500]
            )
            
            # Log activity for modifying operations
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] and response.status_code < 400 and user_id:
                # Only log if we have a valid user_id (activity_logs requires it)
                # Extract resource info from path
                path_parts = request.path.strip('/').split('/')
                if len(path_parts) >= 3 and path_parts[2] not in ['auth', 'health']:  # Skip auth endpoints
                    resource_type = path_parts[2]
                    resource_id = path_parts[3] if len(path_parts) > 3 else 'new'
                    
                    action_map = {
                        'POST': 'create',
                        'PUT': 'update',
                        'PATCH': 'update',
                        'DELETE': 'delete'
                    }
                    
                    logging_service.log_activity(
                        action=f"{action_map[request.method]}_{resource_type}",
                        resource_type=resource_type,
                        resource_id=resource_id,
                        result='success',
                        duration_ms=response_time_ms,
                        user_id=user_id,
                        organization_id=org_id
                    )
        
        return response
