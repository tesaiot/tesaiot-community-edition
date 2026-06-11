# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Metrics Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Prometheus Metrics Controller
Version: v2025.07-beta.1
"""

import hmac
import os
import time
import math
import logging
from datetime import datetime
from functools import wraps
from flask import Blueprint, Response, jsonify, request
from typing import Iterable, List

from ..core.database import get_db, get_redis, get_postgres_conn, db_manager
from ..core.connection_pool import pool_manager

logger = logging.getLogger(__name__)

# Create blueprint
metrics_bp = Blueprint('metrics', __name__)

_ADMIN_ROLES = ('admin', 'organization_admin', 'platform_admin', 'super_admin', 'org_admin')


def _require_metrics_auth(f):
    """Gate operational endpoints behind admin auth or the internal secret.

    SECURITY: /metrics and /debug/pools used to be unauthenticated and leaked
    infrastructure details. Access requires either:
      - X-Service-Secret matching INTERNAL_SERVICE_SECRET (constant-time;
        intended for Prometheus scrapers and in-cluster services), or
      - a valid JWT with an admin-class role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1) Internal-service shared secret (scraper-friendly)
        configured_secret = (os.environ.get('INTERNAL_SERVICE_SECRET') or '').strip()
        presented_secret = (request.headers.get('X-Service-Secret') or '').strip()
        if configured_secret and presented_secret and \
                hmac.compare_digest(presented_secret, configured_secret):
            return f(*args, **kwargs)

        # 2) Admin JWT
        try:
            from ..core.auth import verify_token
            auth_header = request.headers.get('Authorization') or ''
            parts = auth_header.split(' ')
            if len(parts) == 2:
                payload, _err = verify_token(parts[1])
                if payload and (payload.get('role') or '').lower() in _ADMIN_ROLES:
                    return f(*args, **kwargs)
        except Exception as e:
            logger.debug(f"Metrics auth JWT check failed: {e}")

        logger.warning(f"Unauthorized metrics access attempt: {request.path}")
        return jsonify({'error': 'Unauthorized'}), 401

    return decorated_function

def get_prometheus_metrics() -> str:
    """Generate Prometheus metrics format"""
    try:
        metrics = []
        
        # System metrics
        metrics.append("# HELP tesa_iot_api_up API service availability")
        metrics.append("# TYPE tesa_iot_api_up gauge")
        metrics.append("tesa_iot_api_up 1")
        
        # Database connection metrics
        try:
            db = get_db()
            if db is not None:
                metrics.append("# HELP tesa_iot_mongodb_connected MongoDB connection status")
                metrics.append("# TYPE tesa_iot_mongodb_connected gauge")
                metrics.append("tesa_iot_mongodb_connected 1")
                
                # Get device count
                device_count = db.devices.count_documents({})
                metrics.append("# HELP tesa_iot_devices_total Total number of devices")
                metrics.append("# TYPE tesa_iot_devices_total gauge")
                metrics.append(f"tesa_iot_devices_total {device_count}")
                
                # Get active device count
                active_devices = db.devices.count_documents({"status": "active"})
                metrics.append("# HELP tesa_iot_devices_active Active devices")
                metrics.append("# TYPE tesa_iot_devices_active gauge")
                metrics.append(f"tesa_iot_devices_active {active_devices}")
                
                # Get user count
                user_count = db.users.count_documents({})
                metrics.append("# HELP tesa_iot_users_total Total number of users")
                metrics.append("# TYPE tesa_iot_users_total gauge")
                metrics.append(f"tesa_iot_users_total {user_count}")

                # Protected update metrics
                try:
                    collection = getattr(db, 'protected_update_csr_jobs', None)
                    if collection is not None:
                        metrics.append("# HELP tesa_protected_update_jobs_total Number of protected update CSR jobs by status")
                        metrics.append("# TYPE tesa_protected_update_jobs_total gauge")

                        tracked_statuses = [
                            "queued",
                            "blocked",
                            "ready",
                            "signing",
                            "signed",
                            "published",
                            "failed",
                        ]
                        for status in tracked_statuses:
                            count = collection.count_documents({"status": status})
                            metrics.append(
                                'tesa_protected_update_jobs_total{status="%s"} %s'
                                % (status, count)
                            )

                        metrics.append("# HELP tesa_protected_update_publish_status_total Protected update publish status counts")
                        metrics.append("# TYPE tesa_protected_update_publish_status_total gauge")
                        publish_statuses = ["pending", "publishing", "succeeded", "failed"]
                        for publish_status in publish_statuses:
                            count = collection.count_documents({"publish_status": publish_status})
                            metrics.append(
                                'tesa_protected_update_publish_status_total{status="%s"} %s'
                                % (publish_status, count)
                            )

                        signing_failures = collection.count_documents({"status": "failed"})
                        publish_failures = collection.count_documents({"publish_status": "failed"})
                        metrics.append("# HELP tesa_protected_update_signing_failures_total Protected update signing failures")
                        metrics.append("# TYPE tesa_protected_update_signing_failures_total gauge")
                        metrics.append(f"tesa_protected_update_signing_failures_total {signing_failures}")
                        metrics.append("# HELP tesa_protected_update_publish_failures_total Protected update publish failures")
                        metrics.append("# TYPE tesa_protected_update_publish_failures_total gauge")
                        metrics.append(f"tesa_protected_update_publish_failures_total {publish_failures}")

                        def _latency_stats(values: Iterable[float]) -> List[str]:
                            series = [v for v in values if v is not None and v >= 0]
                            if not series:
                                return ["0", "0", "0"]
                            series.sort()
                            count = len(series)
                            average = sum(series) / count
                            maximum = series[-1]
                            p95_index = max(0, min(count - 1, math.ceil(0.95 * count) - 1))
                            p95_value = series[p95_index]
                            return [
                                f"{average:.3f}",
                                f"{p95_value:.3f}",
                                f"{maximum:.3f}",
                            ]

                        job_cursor = collection.find(
                            {},
                            {
                                "created_at": 1,
                                "signed_at": 1,
                                "published_at": 1,
                                "status": 1,
                            },
                        )

                        queue_latencies: List[float] = []
                        publish_latencies: List[float] = []
                        total_jobs = 0

                        for doc in job_cursor:
                            total_jobs += 1
                            created_at = doc.get("created_at")
                            signed_at = doc.get("signed_at")
                            published_at = doc.get("published_at")

                            if created_at and signed_at:
                                queue_latencies.append((signed_at - created_at).total_seconds())
                            if signed_at and published_at:
                                publish_latencies.append((published_at - signed_at).total_seconds())

                        metrics.append("# HELP tesa_protected_update_jobs_processed_total Total protected update CSR jobs tracked")
                        metrics.append("# TYPE tesa_protected_update_jobs_processed_total gauge")
                        metrics.append(f"tesa_protected_update_jobs_processed_total {total_jobs}")

                        avg_queue, p95_queue, max_queue = _latency_stats(queue_latencies)
                        metrics.append("# HELP tesa_protected_update_queue_latency_seconds Protected update queue-to-sign latency")
                        metrics.append("# TYPE tesa_protected_update_queue_latency_seconds gauge")
                        metrics.append(f'tesa_protected_update_queue_latency_seconds{{stat="avg"}} {avg_queue}')
                        metrics.append(f'tesa_protected_update_queue_latency_seconds{{stat="p95"}} {p95_queue}')
                        metrics.append(f'tesa_protected_update_queue_latency_seconds{{stat="max"}} {max_queue}')

                        avg_publish, p95_publish, max_publish = _latency_stats(publish_latencies)
                        metrics.append("# HELP tesa_protected_update_publish_latency_seconds Protected update sign-to-publish latency")
                        metrics.append("# TYPE tesa_protected_update_publish_latency_seconds gauge")
                        metrics.append(f'tesa_protected_update_publish_latency_seconds{{stat="avg"}} {avg_publish}')
                        metrics.append(f'tesa_protected_update_publish_latency_seconds{{stat="p95"}} {p95_publish}')
                        metrics.append(f'tesa_protected_update_publish_latency_seconds{{stat="max"}} {max_publish}')

                except Exception as protected_update_error:  # pragma: no cover - defensive metrics guard
                    logger.error(
                        "Error building protected update metrics: %s",
                        protected_update_error,
                        exc_info=True,
                    )

            else:
                metrics.append("# HELP tesa_iot_mongodb_connected MongoDB connection status")
                metrics.append("# TYPE tesa_iot_mongodb_connected gauge")
                metrics.append("tesa_iot_mongodb_connected 0")
        except Exception as e:
            logger.error(f"Error getting MongoDB metrics: {e}")
            metrics.append("tesa_iot_mongodb_connected 0")
        
        # Redis metrics
        try:
            redis_client = get_redis()
            if redis_client is not None:
                metrics.append("# HELP tesa_iot_redis_connected Redis connection status")
                metrics.append("# TYPE tesa_iot_redis_connected gauge")
                metrics.append("tesa_iot_redis_connected 1")
                
                # Get Redis info
                redis_info = redis_client.info()
                used_memory = redis_info.get('used_memory', 0)
                connected_clients = redis_info.get('connected_clients', 0)
                
                metrics.append("# HELP tesa_iot_redis_memory_used_bytes Redis memory usage")
                metrics.append("# TYPE tesa_iot_redis_memory_used_bytes gauge")
                metrics.append(f"tesa_iot_redis_memory_used_bytes {used_memory}")
                
                metrics.append("# HELP tesa_iot_redis_connected_clients Redis connected clients")
                metrics.append("# TYPE tesa_iot_redis_connected_clients gauge")
                metrics.append(f"tesa_iot_redis_connected_clients {connected_clients}")
            else:
                metrics.append("# HELP tesa_iot_redis_connected Redis connection status")
                metrics.append("# TYPE tesa_iot_redis_connected gauge")
                metrics.append("tesa_iot_redis_connected 0")
        except Exception as e:
            logger.error(f"Error getting Redis metrics: {e}")
            metrics.append("tesa_iot_redis_connected 0")
        
        # PostgreSQL metrics
        try:
            postgres_conn = get_postgres_conn()
            if postgres_conn is not None:
                metrics.append("# HELP tesa_iot_postgres_connected PostgreSQL connection status")
                metrics.append("# TYPE tesa_iot_postgres_connected gauge")
                metrics.append("tesa_iot_postgres_connected 1")
                
                # Get PostgreSQL statistics
                cursor = postgres_conn.cursor()
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
                cursor.close()
                
                metrics.append("# HELP tesa_iot_postgres_active_connections PostgreSQL active connections")
                metrics.append("# TYPE tesa_iot_postgres_active_connections gauge")
                metrics.append(f"tesa_iot_postgres_active_connections {active_connections}")
            else:
                metrics.append("# HELP tesa_iot_postgres_connected PostgreSQL connection status")
                metrics.append("# TYPE tesa_iot_postgres_connected gauge")
                metrics.append("tesa_iot_postgres_connected 0")
        except Exception as e:
            logger.error(f"Error getting PostgreSQL metrics: {e}")
            metrics.append("tesa_iot_postgres_connected 0")
        
        # Connection pool metrics
        try:
            if db_manager.use_enhanced_pooling:
                pool_stats = pool_manager.get_all_stats()
                
                for pool_name, stats in pool_stats.items():
                    if isinstance(stats, dict) and 'error' not in stats:
                        metrics.append(f"# HELP tesa_iot_pool_{pool_name}_total_connections Total connections in pool")
                        metrics.append(f"# TYPE tesa_iot_pool_{pool_name}_total_connections gauge")
                        metrics.append(f"tesa_iot_pool_{pool_name}_total_connections {stats.get('total_connections', 0)}")
                        
                        metrics.append(f"# HELP tesa_iot_pool_{pool_name}_active_connections Active connections in pool")
                        metrics.append(f"# TYPE tesa_iot_pool_{pool_name}_active_connections gauge")
                        metrics.append(f"tesa_iot_pool_{pool_name}_active_connections {stats.get('active_connections', 0)}")
                        
                        metrics.append(f"# HELP tesa_iot_pool_{pool_name}_failed_connections Failed connections in pool")
                        metrics.append(f"# TYPE tesa_iot_pool_{pool_name}_failed_connections counter")
                        metrics.append(f"tesa_iot_pool_{pool_name}_failed_connections {stats.get('failed_connections', 0)}")
        except Exception as e:
            logger.error(f"Error getting connection pool metrics: {e}")
        
        # API metrics
        metrics.append("# HELP tesa_iot_api_requests_total Total API requests")
        metrics.append("# TYPE tesa_iot_api_requests_total counter")
        metrics.append("tesa_iot_api_requests_total 0")  # Would need request tracking
        
        # Timestamp
        metrics.append("# HELP tesa_iot_last_metrics_update_timestamp Last metrics update timestamp")
        metrics.append("# TYPE tesa_iot_last_metrics_update_timestamp gauge")
        metrics.append(f"tesa_iot_last_metrics_update_timestamp {time.time()}")
        
        return "\n".join(metrics)
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return f"# Error generating metrics: {str(e)}\n"

@metrics_bp.route('/metrics')
@_require_metrics_auth
def prometheus_metrics():
    """Prometheus metrics endpoint (admin or internal-service secret)"""
    try:
        metrics_output = get_prometheus_metrics()
        return Response(metrics_output, mimetype='text/plain')
    except Exception as e:
        logger.error(f"Error serving Prometheus metrics: {e}")
        return Response(f"# Error: {str(e)}\n", mimetype='text/plain', status=500)

@metrics_bp.route('/health')
def health_check():
    """Health check endpoint for metrics service"""
    try:
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'mongodb': get_db() is not None,
                'redis': get_redis() is not None,
                'postgres': get_postgres_conn() is not None,
                'enhanced_pooling': db_manager.use_enhanced_pooling
            }
        }
        return jsonify(health_data), 200
    except Exception as e:
        # Status-only: internal error details are logged, never returned.
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat()
        }), 500

@metrics_bp.route('/debug/pools')
@_require_metrics_auth
def debug_pools():
    """Debug endpoint for connection pool status (admin or internal secret)"""
    try:
        pool_info = {
            'enhanced_pooling_enabled': db_manager.use_enhanced_pooling,
            'service_health': db_manager.service_health,
            'pool_stats': {}
        }
        
        if db_manager.use_enhanced_pooling:
            try:
                pool_info['pool_stats'] = pool_manager.get_all_stats()
            except Exception as e:
                pool_info['pool_stats_error'] = str(e)
        
        return jsonify(pool_info), 200
    except Exception as e:
        logger.error(f"Debug pools error: {e}")
        return jsonify({'error': str(e)}), 500
