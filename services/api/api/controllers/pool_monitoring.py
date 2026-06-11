# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Connection Pool Monitoring Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Connection Pool Monitoring API
Version: v2025.07-beta.1
Build Date: 2025-07-04

Description:
    Provides REST API endpoints for monitoring database connection pools
"""

import logging
from flask import Blueprint, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ..core.database import pool_manager, db_manager
from ..core.auth import require_auth
from ..core.rbac import require_permission, Permission

logger = logging.getLogger(__name__)

# Create blueprint
pool_monitoring_bp = Blueprint('pool_monitoring', __name__, url_prefix='/api/v1/monitoring/pools')

# Rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per hour", "20 per minute"]
)


@pool_monitoring_bp.route('/status', methods=['GET'])
@require_auth
@require_permission(Permission.PLATFORM_MONITORING)
@limiter.limit("10 per minute")
def get_pool_status():
    """Get current connection pool status"""
    try:
        # Get pool statistics
        if db_manager.use_enhanced_pooling:
            stats = pool_manager.get_all_stats()
            
            # Add overall health status
            health_status = 'healthy'
            issues = []
            
            for pool_name, pool_stats in stats.items():
                if isinstance(pool_stats, dict) and 'error' not in pool_stats:
                    # Check for issues
                    if pool_stats.get('pool_exhaustion_count', 0) > 0:
                        health_status = 'warning'
                        issues.append(f"{pool_name}: Pool exhaustion detected")
                        
                    if pool_stats.get('health_check_failures', 0) > 5:
                        health_status = 'critical'
                        issues.append(f"{pool_name}: Multiple health check failures")
                        
                    if pool_stats.get('failed_connections', 0) > pool_stats.get('total_requests', 1) * 0.1:
                        health_status = 'warning'
                        issues.append(f"{pool_name}: High connection failure rate")
                else:
                    health_status = 'critical'
                    issues.append(f"{pool_name}: Pool error")
            
            response = {
                'status': 'success',
                'enhanced_pooling': True,
                'health_status': health_status,
                'issues': issues,
                'pools': stats
            }
        else:
            # Basic status for standard pooling
            response = {
                'status': 'success',
                'enhanced_pooling': False,
                'health_status': 'unknown',
                'message': 'Enhanced pooling not enabled'
            }
            
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve pool status'
        }), 500


@pool_monitoring_bp.route('/metrics', methods=['GET'])
@require_auth
@require_permission(Permission.PLATFORM_MONITORING)
@limiter.limit("10 per minute")
def get_pool_metrics():
    """Get detailed connection pool metrics"""
    try:
        if not db_manager.use_enhanced_pooling:
            return jsonify({
                'status': 'error',
                'message': 'Enhanced pooling not enabled'
            }), 400
            
        stats = pool_manager.get_all_stats()
        
        # Calculate aggregated metrics
        total_active = 0
        total_idle = 0
        total_requests = 0
        total_failures = 0
        
        for pool_name, pool_stats in stats.items():
            if isinstance(pool_stats, dict) and 'error' not in pool_stats:
                total_active += pool_stats.get('active_connections', 0)
                total_idle += pool_stats.get('idle_connections', 0)
                total_requests += pool_stats.get('total_requests', 0)
                total_failures += pool_stats.get('failed_connections', 0)
        
        metrics = {
            'status': 'success',
            'summary': {
                'total_active_connections': total_active,
                'total_idle_connections': total_idle,
                'total_requests': total_requests,
                'total_failures': total_failures,
                'failure_rate': (total_failures / total_requests * 100) if total_requests > 0 else 0,
                'utilization': (total_active / (total_active + total_idle) * 100) if (total_active + total_idle) > 0 else 0
            },
            'details': stats
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting pool metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve pool metrics'
        }), 500


@pool_monitoring_bp.route('/health', methods=['GET'])
@limiter.limit("30 per minute")
def check_pool_health():
    """Quick health check endpoint for monitoring systems"""
    try:
        if db_manager.use_enhanced_pooling:
            stats = pool_manager.get_all_stats()
            
            # Simple health check
            all_healthy = True
            for pool_name, pool_stats in stats.items():
                if isinstance(pool_stats, dict):
                    if 'error' in pool_stats:
                        all_healthy = False
                        break
                    if pool_stats.get('health_check_failures', 0) > 5:
                        all_healthy = False
                        break
            
            return jsonify({
                'status': 'healthy' if all_healthy else 'unhealthy',
                'enhanced_pooling': True
            }), 200 if all_healthy else 503
        else:
            return jsonify({
                'status': 'unknown',
                'enhanced_pooling': False
            }), 200
            
    except Exception as e:
        logger.error(f"Pool health check error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503


@pool_monitoring_bp.route('/reset/<pool_name>', methods=['POST'])
@require_auth
@require_permission(Permission.PLATFORM_MANAGE)
@limiter.limit("5 per hour")
def reset_pool(pool_name):
    """Reset a specific connection pool (admin only)"""
    try:
        if not db_manager.use_enhanced_pooling:
            return jsonify({
                'status': 'error',
                'message': 'Enhanced pooling not enabled'
            }), 400
            
        valid_pools = ['mongodb', 'postgresql']
        if pool_name not in valid_pools:
            return jsonify({
                'status': 'error',
                'message': f'Invalid pool name. Must be one of: {valid_pools}'
            }), 400
            
        # Close and reinitialize the specific pool
        success = False
        if pool_name == 'mongodb':
            pool = pool_manager.pools.get('mongodb')
            if pool:
                pool.close()
                # Reinitialize from config
                from ..core.config import Config
                config = Config()
                success = pool_manager.initialize_mongodb_pool(
                    config.MONGODB_URI,
                    config.MONGODB_DATABASE
                )
        elif pool_name == 'postgresql':
            pool = pool_manager.pools.get('postgresql')
            if pool:
                pool.close()
                # Reinitialize from config
                from ..core.config import Config
                config = Config()
                success = pool_manager.initialize_postgresql_pool(
                    config.POSTGRES_URI
                )
                
        if success:
            logger.info(f"Successfully reset {pool_name} connection pool")
            return jsonify({
                'status': 'success',
                'message': f'{pool_name} pool reset successfully'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to reset {pool_name} pool'
            }), 500
            
    except Exception as e:
        logger.error(f"Error resetting pool {pool_name}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to reset pool: {str(e)}'
        }), 500


# Error handlers
@pool_monitoring_bp.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded (429s must carry Retry-After)"""
    retry_after = max(1, int(getattr(e, 'retry_after', 60) or 60))
    response = jsonify({
        'status': 'error',
        'message': f'Rate limit exceeded. Retry after {retry_after} seconds.',
        'retry_after_seconds': retry_after
    })
    response.headers['Retry-After'] = str(retry_after)
    return response, 429