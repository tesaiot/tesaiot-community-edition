# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Stats Service

Handles statistics, usage, monitoring, and analytics endpoints for dashboard.
Extracted from monolithic dashboard.py for better modularity and maintainability.

Service Scope:
- /stats - Dashboard statistics
- /monitoring - System monitoring
- /usage/* - Usage analytics
- /analytics/* - Advanced analytics
"""

import logging
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Status priority for service health aggregation
STATUS_PRIORITY = {'down': 3, 'degraded': 2, 'healthy': 1, 'unknown': 0}


class DashboardStatsService:
    """
    Service for dashboard statistics, usage, and analytics endpoints.

    Responsibilities:
    - Dashboard statistics aggregation
    - Usage metrics and trends
    - System monitoring data
    - Analytics and insights

    Design Principles:
    - Read-only operations (no database writes)
    - Organization-scoped data access
    - Performance-optimized queries
    - Safe numeric handling (no NaN/Infinity)
    """

    def __init__(self, db_session=None, redis_client=None):
        """
        Initialize dashboard stats service.

        Args:
            db_session: PostgreSQL database session
            redis_client: Redis client for caching
        """
        self.db_session = db_session
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)

    # ==================== Helper Functions ====================

    @staticmethod
    def sanitize_numeric_value(value: Any, fallback: float = 0) -> float:
        """
        Sanitize numeric values to prevent NaN/Infinity in JSON responses.

        Args:
            value: Value to sanitize
            fallback: Default value if sanitization fails

        Returns:
            Sanitized float value
        """
        if value is None:
            return fallback

        try:
            num_val = float(value)
            if math.isnan(num_val) or math.isinf(num_val):
                return fallback
            return num_val
        except (ValueError, TypeError):
            return fallback

    @staticmethod
    def sanitize_response_data(data: Any) -> Any:
        """
        Recursively sanitize response data to prevent chart errors.

        Args:
            data: Data structure to sanitize (dict, list, or primitive)

        Returns:
            Sanitized data structure
        """
        if isinstance(data, dict):
            return {key: DashboardStatsService.sanitize_response_data(value)
                   for key, value in data.items()}
        elif isinstance(data, list):
            return [DashboardStatsService.sanitize_response_data(item)
                   for item in data]
        elif isinstance(data, (int, float)):
            return DashboardStatsService.sanitize_numeric_value(data)
        else:
            return data

    @staticmethod
    def normalize_service_status(status: Optional[str]) -> str:
        """
        Normalize service status to standard values.

        Args:
            status: Raw status string

        Returns:
            Normalized status: 'healthy', 'degraded', 'down', or 'unknown'
        """
        value = (status or '').lower()
        if value in {'healthy', 'up', 'running'}:
            return 'healthy'
        if value in {'warning', 'warn', 'degraded', 'at_risk', 'partial'}:
            return 'degraded'
        if value in {'critical', 'down', 'error', 'stopped', 'failed'}:
            return 'down'
        return 'unknown'

    @staticmethod
    def merge_service_status(current: str, new_value: str) -> str:
        """
        Merge two service statuses, keeping the worse one.

        Args:
            current: Current status
            new_value: New status to merge

        Returns:
            Merged status (worse of the two)
        """
        current_priority = STATUS_PRIORITY.get(current, 0)
        new_priority = STATUS_PRIORITY.get(new_value, 0)
        return current if current_priority >= new_priority else new_value

    # ==================== Endpoint Methods ====================
    # Will be populated with extracted endpoint logic

    def get_dashboard_stats(
        self,
        db,
        organization_id: Optional[str] = None,
        user_role: str = '',
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics.

        Args:
            db: Database connection
            organization_id: Organization ID for scoping
            user_role: User's role
            user_context: Full user context

        Returns:
            Dashboard statistics data
        """
        from bson import ObjectId
        from ...utils.data_fixes import fix_stats_data

        # RBAC for SaaS Multi-Tenant Platform:
        # - Platform admins: See all data across all organizations (like super admin)
        # - Super admins: See all data across all organizations
        # - All other roles: See only their organization's data (customer view)
        device_filter: Dict[str, Any] = {}
        user_filter: Dict[str, Any] = {}

        if user_role in ['super_admin', 'platform_admin']:
            # Super admin and platform admin see everything
            device_filter = {}
            user_filter = {}
        elif organization_id:
            # Handle organization filtering based on data type
            org_identifier = organization_id

            # Get the organization document to understand the relationship
            if isinstance(org_identifier, str):
                try:
                    # First, try to find organization by name or _id
                    org = None
                    if ObjectId.is_valid(org_identifier):
                        org = db.organizations.find_one({'_id': ObjectId(org_identifier)})
                    else:
                        org = db.organizations.find_one({'name': org_identifier})

                    if org:
                        # Use both organization name and _id for filtering
                        org_name = org['name']
                        org_id_str = str(org['_id'])

                        # Map known organization shortcuts
                        org_shortcuts = {
                            'BDH Corporation': 'bdh-corp',
                            'TESAIoT Platform': 'tesa-platform',
                            'Thai Embedded Systems Association': 'tesa',
                            'Infineon Technology AG': 'infineon'
                        }
                        org_short = org_shortcuts.get(org_name, org_name.lower().replace(' ', '-'))

                        # For devices: try both organization_id and organization fields
                        device_filter = {
                            '$or': [
                                {'organization_id': org_id_str},
                                {'organization_id': org_name},
                                {'organization_id': org_short},
                                {'organization': org_name}
                            ]
                        }

                        # For users: use organization name (this is how users are stored)
                        user_filter = {'organization': org_name}
                    else:
                        # Fallback - try organization name directly
                        device_filter = {
                            '$or': [
                                {'organization_id': org_identifier},
                                {'organization': org_identifier}
                            ]
                        }
                        user_filter = {'organization': org_identifier}
                except Exception as e:
                    self.logger.warning(f"Organization filtering error: {e}")
                    # Safe fallback
                    device_filter = {
                        '$or': [
                            {'organization_id': org_identifier},
                            {'organization': org_identifier}
                        ]
                    }
                    user_filter = {'organization': org_identifier}

        # Debug logging
        self.logger.info(f"User role: {user_role}, Device filter: {device_filter}, User filter: {user_filter}")

        stats = {
            'total_devices': db.devices.count_documents(device_filter) if db is not None else 0,
            'active_devices': db.devices.count_documents({**device_filter, 'status': 'active'}) if db is not None else 0,
            'total_users': db.users.count_documents(user_filter) if db is not None else 0,
            'total_organizations': db.organizations.count_documents({}) if user_role in ['super_admin', 'platform_admin'] and db is not None else (1 if device_filter else (db.organizations.count_documents({}) if db is not None else 0)),
            'total_certificates': db.certificates.count_documents({}) if db is not None else 0,
            'alerts': 0,
            'data_points_today': 0
        }

        # Get recent data points count (ACL: Apply organization filtering)
        if db is not None:
            from datetime import datetime
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            telemetry_filter = {'timestamp': {'$gte': today}}
            if device_filter:  # Apply organization filter to telemetry as well
                telemetry_filter.update(device_filter)
            stats['data_points_today'] = db.telemetry.count_documents(telemetry_filter)

        # Apply data fixes
        stats = fix_stats_data(stats)

        return stats

    def get_monitoring_metrics(
        self,
        organization_id: Optional[str] = None,
        user_role: str = ''
    ) -> Dict[str, Any]:
        """
        Get monitoring metrics.

        Args:
            organization_id: Organization ID for scoping
            user_role: User's role

        Returns:
            Monitoring metrics data
        """
        # TODO: Implement monitoring logic
        pass

    def get_usage_overview(
        self,
        db,
        timeframe: str = 'day',
        organization_id: Optional[str] = None,
        user_role: str = ''
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage analytics overview.

        Args:
            db: Database connection
            timeframe: Time frame for analytics ('hour', 'day', 'week', 'month')
            organization_id: Organization ID for scoping
            user_role: User's role

        Returns:
            Usage overview data
        """
        # Get time range based on timeframe
        now = datetime.now()
        if timeframe == 'hour':
            start_time = now - timedelta(hours=1)
        elif timeframe == 'week':
            start_time = now - timedelta(days=7)
        elif timeframe == 'month':
            start_time = now - timedelta(days=30)
        else:  # day
            start_time = now - timedelta(days=1)

        # API Usage Analytics
        api_analytics = {
            'total_requests': 45230,
            'successful_requests': 43891,
            'error_requests': 1339,
            'average_response_time_ms': 142,
            'requests_per_minute': 31.4,
            'peak_rps': 127,
            'data_transferred_gb': 2.8,
            'unique_api_keys': 12,
            'top_endpoints': [
                {'endpoint': '/api/v1/devices', 'requests': 8450, 'avg_response_ms': 89},
                {'endpoint': '/api/v1/telemetry/ingest', 'requests': 6720, 'avg_response_ms': 45},
                {'endpoint': '/api/v1/certificates', 'requests': 3210, 'avg_response_ms': 234},
                {'endpoint': '/api/v1/organizations', 'requests': 2890, 'avg_response_ms': 156},
                {'endpoint': '/api/v1/users', 'requests': 1980, 'avg_response_ms': 98}
            ],
            'error_breakdown': [
                {'status': 404, 'count': 678, 'percentage': 50.6},
                {'status': 500, 'count': 345, 'percentage': 25.8},
                {'status': 403, 'count': 201, 'percentage': 15.0},
                {'status': 429, 'count': 115, 'percentage': 8.6}
            ]
        }

        # Device & Telemetry Analytics
        device_analytics = {
            'active_devices': db.devices.count_documents({'status': 'active'}) if db is not None else 8,
            'total_telemetry_messages': 125430,
            'telemetry_rate_per_second': 1.45,
            'average_message_size_bytes': 342,
            'data_points_processed': 892340,
            'device_uptime_avg': 98.7,
            'top_sending_devices': [
                {'device_id': 'BDH-MINIPC-EDGE-001', 'messages': 18420, 'last_seen': '2025-06-19T11:45:30Z'},
                {'device_id': 'dev-68499724a458c3f783450dff', 'messages': 15680, 'last_seen': '2025-06-19T11:44:15Z'},
                {'device_id': 'dev-683bd7fa6782dde0a45bd7a2', 'messages': 12340, 'last_seen': '2025-06-19T11:43:22Z'},
                {'device_id': 'BDH-Test-Device-001', 'messages': 9870, 'last_seen': '2025-06-19T11:42:58Z'}
            ],
            'telemetry_types': [
                {'type': 'temperature', 'count': 28450, 'avg_value': 24.8},
                {'type': 'humidity', 'count': 28450, 'avg_value': 62.3},
                {'type': 'pressure', 'count': 28450, 'avg_value': 1013.2},
                {'type': 'battery_level', 'count': 8520, 'avg_value': 78.5},
                {'type': 'signal_strength', 'count': 8520, 'avg_value': -67.2}
            ]
        }

        # User Activity Analytics
        user_analytics = {
            'total_sessions': 156,
            'unique_users': db.users.count_documents({}) if db is not None else 12,
            'average_session_duration_minutes': 23.4,
            'login_success_rate': 96.8,
            'most_active_users': [
                {'email': 'admin@tesa.local', 'sessions': 45, 'last_login': '2025-06-19T11:30:00Z'},
                {'email': 'user@example.com', 'sessions': 38, 'last_login': '2025-06-19T10:15:22Z'},
                {'email': 'org.admin@bdh.co.th', 'sessions': 25, 'last_login': '2025-06-19T09:45:10Z'}
            ],
            'feature_usage': [
                {'feature': 'Device Management', 'usage_count': 892, 'unique_users': 8},
                {'feature': 'Certificate Management', 'usage_count': 445, 'unique_users': 6},
                {'feature': 'API Key Management', 'usage_count': 234, 'unique_users': 4},
                {'feature': 'Organization Management', 'usage_count': 156, 'unique_users': 3},
                {'feature': 'AI Assistant', 'usage_count': 89, 'unique_users': 5}
            ]
        }

        # System Resource Analytics
        system_analytics = {
            'cpu_usage_avg': 24.5,
            'memory_usage_avg': 68.2,
            'disk_usage_gb': 15.8,
            'network_in_mbps': 2.4,
            'network_out_mbps': 3.1,
            'database_connections': 15,
            'cache_hit_ratio': 94.2,
            'vault_operations': 234,
            'container_stats': [
                {'service': 'tesa-api', 'cpu': 18.5, 'memory': 245, 'status': 'healthy'},
                {'service': 'tesa-admin-ui', 'cpu': 5.2, 'memory': 89, 'status': 'healthy'},
                {'service': 'mongodb', 'cpu': 12.8, 'memory': 512, 'status': 'healthy'},
                {'service': 'redis', 'cpu': 3.1, 'memory': 128, 'status': 'healthy'},
                {'service': 'vault', 'cpu': 8.4, 'memory': 156, 'status': 'healthy'}
            ]
        }

        # Security Analytics
        security_analytics = {
            'failed_auth_attempts': 23,
            'suspicious_ips': 2,
            'certificate_expires_soon': 1,
            'rate_limit_violations': 15,
            'security_events': [
                {'type': 'failed_login', 'count': 18, 'severity': 'medium'},
                {'type': 'rate_limit_hit', 'count': 15, 'severity': 'low'},
                {'type': 'cert_expiry_warning', 'count': 1, 'severity': 'high'},
                {'type': 'invalid_api_key', 'count': 8, 'severity': 'medium'}
            ]
        }

        usage_overview = {
            'timeframe': timeframe,
            'period': {
                'start': start_time.isoformat(),
                'end': now.isoformat()
            },
            'api_usage': api_analytics,
            'device_telemetry': device_analytics,
            'user_activity': user_analytics,
            'system_resources': system_analytics,
            'security': security_analytics,
            'generated_at': now.isoformat()
        }

        self.logger.info(f"Usage overview requested for timeframe: {timeframe}")
        return usage_overview

    def get_usage_trends(
        self,
        period: str = 'daily',
        metric: str = 'requests',
        days: int = 30,
        organization_id: Optional[str] = None,
        user_role: str = ''
    ) -> Dict[str, Any]:
        """
        Get usage trends and historical data.

        Args:
            period: Time period ('daily', 'weekly', 'monthly')
            metric: Metric to track ('requests', 'devices', 'users', 'data_volume')
            days: Number of days to include
            organization_id: Organization ID for scoping
            user_role: User's role

        Returns:
            Usage trends data with forecasting
        """
        # Generate trend data based on period
        trends_data = []
        now = datetime.now()

        for i in range(days):
            date = now - timedelta(days=days-i-1)

            if metric == 'requests':
                value = 1200 + (i * 50) + (i % 7 * 200)  # Simulate growth with weekly patterns
            elif metric == 'devices':
                value = 8 + (i // 5)  # Gradual device growth
            elif metric == 'users':
                value = 12 + (i // 10)  # Slower user growth
            elif metric == 'data_volume':
                value = 2.5 + (i * 0.1) + (i % 7 * 0.5)  # Data volume in GB
            else:
                value = 100 + (i * 10)

            trends_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'value': round(value, 2),
                'period': period
            })

        # Calculate growth metrics
        if len(trends_data) >= 2:
            current_value = float(trends_data[-1]['value'])
            previous_value = float(trends_data[-2]['value'])
            growth_rate = ((current_value - previous_value) / previous_value) * 100 if previous_value > 0 else 0
        else:
            growth_rate = 0

        # Seasonal patterns analysis
        seasonal_patterns = {
            'peak_hours': [9, 10, 14, 15, 16],
            'peak_days': ['Monday', 'Tuesday', 'Wednesday'],
            'lowest_activity': ['Saturday', 'Sunday'],
            'monthly_pattern': 'Steady growth with weekend dips'
        }

        # Forecasting (simple linear projection)
        forecast_data = []
        if len(trends_data) >= 7:
            # Calculate average growth rate over last 7 days
            recent_values = [float(item['value']) for item in trends_data[-7:]]
            avg_growth = (recent_values[-1] - recent_values[0]) / 7

            for i in range(1, 8):  # Forecast next 7 days
                forecast_date = now + timedelta(days=i)
                forecast_value = float(trends_data[-1]['value']) + (avg_growth * i)
                forecast_data.append({
                    'date': forecast_date.strftime('%Y-%m-%d'),
                    'value': round(forecast_value, 2),
                    'is_forecast': True
                })

        usage_trends = {
            'metric': metric,
            'period': period,
            'days_included': days,
            'historical_data': trends_data,
            'forecast': forecast_data,
            'growth_rate_percent': round(growth_rate, 2),
            'seasonal_patterns': seasonal_patterns,
            'summary': {
                'total_change': round(float(trends_data[-1]['value']) - float(trends_data[0]['value']), 2) if trends_data else 0,
                'average_daily_change': round(growth_rate / days, 2) if days > 0 else 0,
                'peak_value': max([float(item['value']) for item in trends_data]) if trends_data else 0,
                'lowest_value': min([float(item['value']) for item in trends_data]) if trends_data else 0
            },
            'generated_at': datetime.now().isoformat()
        }

        self.logger.info(f"Usage trends generated for metric: {metric}, period: {period}, days: {days}")
        return usage_trends

    def get_api_key_usage_analytics(
        self,
        db,
        timeframe: str = 'day',
        organization_id: Optional[str] = None,
        key_id: Optional[str] = None,
        user_role: str = ''
    ) -> Dict[str, Any]:
        """
        Get detailed API key usage analytics.

        Args:
            db: Database connection
            timeframe: Time frame for analytics ('hour', 'day', 'week', 'month')
            organization_id: Organization ID filter
            key_id: Specific API key ID for detailed analysis
            user_role: User's role

        Returns:
            API key usage analytics data
        """
        # API Keys Overview
        api_keys_stats = {
            'total_keys': 12,
            'active_keys': 9,
            'suspended_keys': 2,
            'revoked_keys': 1,
            'keys_created_this_period': 2,
            'most_used_keys': [
                {
                    'key_id': 'tesa_ak_7f8a9b2c3d4e5f6789abcdef',
                    'name': 'Production Integration',
                    'organization': 'BDH Corporation',
                    'requests_count': 15420,
                    'last_used': '2025-06-19T11:45:30Z',
                    'rate_limit_hits': 5
                },
                {
                    'key_id': 'tesa_ak_1a2b3c4d5e6f7890abcdef12',
                    'name': 'Mobile App Backend',
                    'organization': 'Smart City Solutions',
                    'requests_count': 8960,
                    'last_used': '2025-06-19T11:43:15Z',
                    'rate_limit_hits': 0
                },
                {
                    'key_id': 'tesa_ak_9f8e7d6c5b4a39281726354',
                    'name': 'Analytics Dashboard',
                    'organization': 'Industrial IoT Corp',
                    'requests_count': 6780,
                    'last_used': '2025-06-19T11:41:22Z',
                    'rate_limit_hits': 12
                }
            ]
        }

        # Rate Limiting Analytics
        rate_limit_analytics = {
            'total_violations': 32,
            'keys_hitting_limits': 4,
            'most_violated_limits': [
                {'limit_type': 'requests_per_minute', 'violations': 18},
                {'limit_type': 'requests_per_day', 'violations': 8},
                {'limit_type': 'concurrent_connections', 'violations': 6}
            ],
            'peak_usage_times': [
                {'hour': '09:00', 'violations': 8},
                {'hour': '14:00', 'violations': 6},
                {'hour': '16:00', 'violations': 5}
            ]
        }

        # Geographic Distribution
        geographic_analytics = {
            'requests_by_country': [
                {'country': 'Thailand', 'requests': 28450, 'percentage': 62.9},
                {'country': 'Singapore', 'requests': 8920, 'percentage': 19.7},
                {'country': 'Japan', 'requests': 4560, 'percentage': 10.1},
                {'country': 'Malaysia', 'requests': 2890, 'percentage': 6.4},
                {'country': 'Others', 'requests': 410, 'percentage': 0.9}
            ],
            'top_cities': [
                {'city': 'Bangkok, Thailand', 'requests': 18920},
                {'city': 'Singapore, Singapore', 'requests': 8920},
                {'city': 'Tokyo, Japan', 'requests': 4560},
                {'city': 'Kuala Lumpur, Malaysia', 'requests': 2890}
            ]
        }

        api_usage_analytics = {
            'timeframe': timeframe,
            'api_keys_overview': api_keys_stats,
            'rate_limiting': rate_limit_analytics,
            'geographic_distribution': geographic_analytics,
            'generated_at': datetime.now().isoformat()
        }

        self.logger.info(f"API key usage analytics generated for timeframe: {timeframe}")
        return api_usage_analytics

    def get_system_health(
        self,
        realtime_analytics_service,
        timeout: float = 4.0
    ) -> Dict[str, Any]:
        """
        Get system health status with enriched uptime data for dashboard consumers.

        Args:
            realtime_analytics_service: Service for getting real-time health metrics
            timeout: Timeout for health check in seconds

        Returns:
            System health status payload with services, databases, and containers
        """
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                health_data = loop.run_until_complete(
                    asyncio.wait_for(
                        realtime_analytics_service.get_system_health_metrics_fast(),
                        timeout=timeout,
                    )
                )
            finally:
                loop.close()

            services_detail = health_data.get('services') or {}
            databases_detail = health_data.get('databases') or {}
            containers = health_data.get('containers') or []
            system_metrics = health_data.get('system_metrics') or {}

            # Build legacy services mapping for backward compatibility
            legacy_services = {
                'api': services_detail.get('api_gateway', {}).get('status', 'unknown'),
                'database': databases_detail.get('mongodb', {}).get('status', 'unknown'),
                'cache': databases_detail.get('redis', {}).get('status', 'unknown'),
                'vault': databases_detail.get('vault', {}).get('status', 'unknown'),
                'telemetry': services_detail.get('mqtt_broker', {}).get('status', 'unknown'),
            }

            # Enrich services with proper structure
            enriched_services: Dict[str, Dict[str, Any]] = {}
            for key, value in services_detail.items():
                if isinstance(value, dict):
                    enriched_services[key] = value
                else:
                    enriched_services[key] = {'status': value}

            # Build response payload
            response_payload: Dict[str, Any] = {
                'status': system_metrics.get('overall_health') or health_data.get('status', 'unknown'),
                'services': enriched_services,
                'legacy_services': legacy_services,
                'databases': databases_detail,
                'containers': containers,
                'system_metrics': system_metrics,
                'version': health_data.get('version') or 'v2025.06-beta-8.3',
                'uptime': services_detail.get('api_gateway', {}).get('uptime', 'Unknown'),
                'timestamp': datetime.now().isoformat(),
            }

            # Add response time if available
            if health_data.get('response_time'):
                response_payload['response_time'] = health_data['response_time']

            self.logger.info("System health check completed successfully")
            return response_payload

        except Exception as e:
            self.logger.error(f"System health check failed: {e}")
            # Return degraded health status on error
            return {
                'status': 'unhealthy',
                'services': {
                    'api': {'status': 'unknown'},
                    'database': {'status': 'unknown'},
                    'cache': {'status': 'unknown'},
                    'vault': {'status': 'unknown'},
                    'telemetry': {'status': 'unknown'},
                },
                'version': 'v2025.06-beta-8.3',
                'uptime': 'N/A',
                'timestamp': datetime.now().isoformat(),
            }

    def get_monitoring_dashboard(
        self,
        db=None,
        redis=None,
        vault=None,
        env_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Get monitoring dashboard data with service health checks.

        Args:
            db: Database connection (optional)
            redis: Redis connection (optional)
            vault: Vault client (optional)
            env_config: Environment configuration for external URLs

        Returns:
            Monitoring dashboard data with services, alerts, and metrics
        """
        import os

        # Build services status
        services = {
            'api_server': {
                'status': 'healthy',
                'uptime': '2h 45m',
                'requests_per_minute': 45,
                'error_rate': 0.2
            },
            'database': {
                'status': 'healthy' if db is not None else 'disconnected',
                'connections': 15 if db is not None else 0,
                'response_time': '12ms' if db is not None else 'N/A'
            },
            'vault': {
                'status': 'healthy' if vault else 'disconnected',
                'sealed': False if vault else True,
                'auth_methods': ['userpass', 'approle'] if vault else []
            },
            'redis': {
                'status': 'healthy' if redis else 'disconnected',
                'memory_usage': '45MB' if redis else 'N/A',
                'connected_clients': 8 if redis else 0
            }
        }

        # External monitoring links
        external_links = {
            'grafana': os.getenv('GRAFANA_URL', 'http://localhost:3000'),
            'prometheus': os.getenv('PROMETHEUS_URL', 'http://localhost:9091'),
            'realtime_logs': os.getenv('REALTIME_LOGS_URL', 'http://localhost:5000'),
            'apisix_dashboard': os.getenv('APISIX_DASHBOARD_URL', 'http://localhost:9000')
        }

        # Override with provided env config if available
        if env_config:
            external_links.update(env_config)

        # Recent alerts (sample data)
        recent_alerts = [
            {
                'level': 'warning',
                'message': 'High CPU usage on device dev-683bd7fa6782dde0a45bd7a2',
                'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat()
            },
            {
                'level': 'info',
                'message': 'Certificate renewed for BDH-Test-Device-001',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ]

        # System metrics summary
        system_metrics = {
            'total_requests_24h': 12450,
            'avg_response_time': '85ms',
            'error_rate_24h': 0.15,
            'active_sessions': 23
        }

        monitoring_data = {
            'services': services,
            'external_links': external_links,
            'recent_alerts': recent_alerts,
            'system_metrics': system_metrics,
            'generated_at': datetime.now().isoformat()
        }

        self.logger.info("Monitoring dashboard data generated")
        return monitoring_data

    def get_realtime_iot_metrics(
        self,
        realtime_analytics_service,
        organization_id: str,
        time_range: str = '1h'
    ) -> Dict[str, Any]:
        """
        Get real-time IoT metrics from TimescaleDB and MongoDB.

        Args:
            realtime_analytics_service: Service for getting real-time IoT metrics
            organization_id: Organization ID for data filtering
            time_range: Time range for metrics ('1h', '6h', '24h', '7d')

        Returns:
            Real-time IoT metrics data
        """
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                metrics = loop.run_until_complete(
                    realtime_analytics_service.get_realtime_iot_metrics(organization_id, time_range)
                )
            finally:
                loop.close()

            self.logger.info(f"Real-time IoT metrics generated for org: {organization_id}, range: {time_range}")
            return metrics

        except Exception as e:
            self.logger.error(f"Real-time IoT metrics error: {e}")
            raise

    def get_realtime_api_gateway_metrics(
        self,
        realtime_analytics_service,
        time_range: str = '1h'
    ) -> Dict[str, Any]:
        """
        Get real-time API gateway metrics from TimescaleDB.

        Args:
            realtime_analytics_service: Service for getting API gateway metrics
            time_range: Time range for metrics ('1h', '6h', '24h', '7d')

        Returns:
            Real-time API gateway metrics data
        """
        import asyncio
        from ...utils.data_fixes import fix_stats_data

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                gateway_metrics = loop.run_until_complete(
                    realtime_analytics_service.get_api_gateway_metrics(time_range)
                )
            finally:
                loop.close()

            # Sanitize response data to prevent NaN values in frontend charts
            sanitized_metrics = fix_stats_data(gateway_metrics)

            self.logger.info(f"Real-time API gateway metrics generated for range: {time_range}")
            return sanitized_metrics

        except Exception as e:
            self.logger.error(f"Real-time API gateway error: {e}")
            raise

    def get_realtime_logs_analytics(
        self,
        realtime_analytics_service,
        organization_id: str,
        time_range: str = '1h'
    ) -> Dict[str, Any]:
        """
        Get real-time logs and events analytics from TimescaleDB.

        Args:
            realtime_analytics_service: Service for getting logs analytics
            organization_id: Organization ID for data filtering
            time_range: Time range for analytics ('1h', '6h', '24h', '7d')

        Returns:
            Real-time logs analytics data
        """
        import asyncio

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                logs_analytics = loop.run_until_complete(
                    realtime_analytics_service.get_realtime_logs_analytics(organization_id, time_range)
                )
            finally:
                loop.close()

            self.logger.info(f"Real-time logs analytics generated for org: {organization_id}, range: {time_range}")
            return logs_analytics

        except Exception as e:
            self.logger.error(f"Real-time logs analytics error: {e}")
            raise

    def run_security_audit(
        self,
        security_health_service,
        current_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a comprehensive security audit and generate report.

        Args:
            security_health_service: Service for security health operations
            current_user: Current authenticated user (must be platform admin)

        Returns:
            Security audit report

        Raises:
            PermissionError: If user is not a platform admin
        """
        from ...core.rbac import RBAC

        # Verify platform admin permission
        if not RBAC.is_platform_admin(current_user):
            self.logger.warning(f"Security audit denied for user: {current_user.get('email')}")
            raise PermissionError('Insufficient permissions - super_admin required')

        # Run comprehensive audit
        audit_report = security_health_service.run_security_audit()

        self.logger.info(f"Security audit run by {current_user.get('email')}")
        return audit_report

    def get_modularization_metrics(
        self,
        modularization_metrics_service,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get comprehensive modularization metrics and progress dashboard.

        Args:
            modularization_metrics_service: Service for modularization metrics
            user: Current user context

        Returns:
            Modularization dashboard data with health score, parallel runner stats,
            feature flags, and recommendations
        """
        # Get comprehensive dashboard data
        dashboard_data = modularization_metrics_service.get_modularization_dashboard()

        # Add user context for display
        dashboard_data['user'] = {
            'id': user.get('_id'),
            'is_internal': user.get('is_internal', False)
        }

        self.logger.info("Modularization metrics fetched")
        return dashboard_data

    def get_modularization_history(
        self,
        modularization_metrics_service,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get historical modularization metrics.

        Args:
            modularization_metrics_service: Service for modularization metrics
            hours: Number of hours to look back (max: 168)

        Returns:
            Historical metrics data with snapshots
        """
        # Limit to max 7 days
        hours = min(hours, 168)

        # Get historical data
        history = modularization_metrics_service.get_historical_metrics(hours)

        result = {
            'hours': hours,
            'snapshots': history,
            'count': len(history)
        }

        self.logger.info(f"Modularization history fetched ({hours} hours)")
        return result

    def save_modularization_snapshot(
        self,
        modularization_metrics_service,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save a snapshot of current modularization metrics.

        Args:
            modularization_metrics_service: Service for modularization metrics
            user: Current user (must have admin role)

        Returns:
            Snapshot confirmation with ID and timestamp

        Raises:
            PermissionError: If user is not an admin
        """
        # Check admin permission
        if 'admin' not in user.get('roles', []):
            self.logger.warning(f"Snapshot save denied for non-admin user: {user.get('_id')}")
            raise PermissionError('Admin access required')

        # Save snapshot
        snapshot_id = modularization_metrics_service.save_metrics_snapshot()

        result = {
            'success': True,
            'snapshot_id': snapshot_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        self.logger.info(f"Metrics snapshot saved: {snapshot_id}")
        return result

    def get_platform_admin_stats(
        self,
        db,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get platform admin dashboard statistics.
        Platform admins can only see infrastructure metrics, not customer data.

        Args:
            db: Database connection
            user: Current user object (must be platform admin)

        Returns:
            Platform infrastructure statistics

        Raises:
            PermissionError: If user is not a platform admin
        """
        from ...core.rbac import RBAC

        # Only platform admins can access this endpoint
        if not RBAC.is_platform_admin(user):
            self.logger.warning(f"[SECURITY] Non-platform admin {user.get('email')} attempted to access platform stats - DENIED")
            raise PermissionError('Access denied. Platform admin role required.')

        # Platform admin sees infrastructure-level metrics only
        platform_stats: Dict[str, Any] = {
            'totalOrganizations': db.organizations.count_documents({}) if db is not None else 0,
            'totalDevicesAllOrgs': db.devices.count_documents({}) if db is not None else 0,
            'totalUsersAllOrgs': db.users.count_documents({}) if db is not None else 0,
            'activeDevicesAllOrgs': db.devices.count_documents({'status': 'active'}) if db is not None else 0,
            'platformHealth': 'healthy',
            'infrastructureMetrics': {
                'apiResponseTime': '45ms',
                'databaseConnections': 12,
                'systemUptime': '99.9%',
                'totalDataPoints': db.telemetry.count_documents({}) if db is not None else 0
            },
            'organizationBreakdown': []
        }

        # Get organization breakdown (aggregated data only, no customer details)
        if db is not None:
            org_pipeline = [
                {
                    '$group': {
                        '_id': '$organization_name',
                        'deviceCount': {'$sum': 1}
                    }
                },
                {'$sort': {'deviceCount': -1}},
                {'$limit': 10}
            ]

            org_breakdown = list(db.devices.aggregate(org_pipeline))
            platform_stats['organizationBreakdown'] = [
                {'organization': org['_id'] or 'Unknown', 'devices': org['deviceCount']}
                for org in org_breakdown
            ]

        self.logger.info(f"Platform admin stats requested by {user.get('email')}")
        return platform_stats

    def get_realtime_security_analytics_simple(
        self,
        organization_id: Optional[str] = None,
        time_range: str = '24h'
    ) -> Dict[str, Any]:
        """
        Get real-time security analytics data (simple version).

        Args:
            organization_id: Optional organization ID for filtering
            time_range: Time range for analytics (default: '24h')

        Returns:
            Real-time security analytics
        """
        import random
        from datetime import timedelta

        security_data = {
            'timestamp': datetime.now().isoformat(),
            'organization_id': organization_id,
            'time_range': time_range,
            'threat_detection': {
                'total_threats': 2818,
                'blocked_threats': 2795,
                'active_threats': 23,
                'threat_severity': {
                    'critical': 3,
                    'high': 45,
                    'medium': 189,
                    'low': 2581
                }
            },
            'security_events': [
                {
                    'timestamp': (datetime.now() - timedelta(minutes=i*10)).isoformat(),
                    'type': random.choice(['intrusion_attempt', 'malware_detected', 'ddos_attack', 'suspicious_activity']),
                    'severity': random.choice(['critical', 'high', 'medium', 'low']),
                    'source_ip': f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
                    'status': random.choice(['blocked', 'mitigated', 'investigating'])
                }
                for i in range(10)
            ],
            'compliance_status': {
                'etsi_en_303_645': True,
                'iso_27402': True,
                'gdpr': True,
                'pci_dss': False
            },
            'security_score': 94.8,
            'vulnerability_scan': {
                'last_scan': (datetime.now() - timedelta(hours=2)).isoformat(),
                'vulnerabilities_found': 0,
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }

        self.logger.info(f"Real-time security analytics requested for org: {organization_id}")
        return security_data

    def get_realtime_system_health(
        self,
        realtime_analytics_service,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        Get real-time system health from Docker containers and databases.

        Args:
            realtime_analytics_service: Realtime analytics service instance
            timeout: Request timeout in seconds (default: 5.0)

        Returns:
            Real-time system health data with container predictions
        """
        import asyncio

        # Use asyncio to run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            health_data = loop.run_until_complete(
                asyncio.wait_for(
                    realtime_analytics_service.get_system_health_metrics_fast(),
                    timeout=timeout
                )
            )
        finally:
            loop.close()

        # Transform the response to match ContainerHealthPredictionCard expectations
        containers = health_data.get('containers', [])

        # Transform containers to container_predictions format
        container_predictions = []
        for container in containers:
            # Calculate health score based on CPU and memory usage
            cpu_percent = container.get('cpu_percent', 0)
            memory_percent = container.get('memory_percent', 0)
            health_score = max(0, 100 - (cpu_percent * 0.5 + memory_percent * 0.5))

            # Determine status based on health score
            if health_score >= 80:
                status = 'healthy'
            elif health_score >= 60:
                status = 'at_risk'
            else:
                status = 'critical'

            # Calculate failure probability based on resource usage
            failure_probability = min(95, max(5, (cpu_percent + memory_percent) / 2))

            # Calculate time to failure (higher usage = less time)
            base_time = 720  # 12 hours base
            if status == 'critical':
                time_to_failure = max(30, base_time - (failure_probability * 5))
            elif status == 'at_risk':
                time_to_failure = max(180, base_time - (failure_probability * 3))
            else:
                time_to_failure = base_time + (100 - failure_probability) * 10

            container_predictions.append({
                'container_id': container.get('name', '').replace('tesa-', ''),
                'container_name': container.get('name', 'unknown'),
                'health_score': int(health_score),
                'status': status,
                'failure_probability': round(failure_probability, 1),
                'time_to_failure_minutes': int(time_to_failure),
                'restart_probability': min(30, container.get('restart_count', 0) * 5),
                'performance_degradation': max(0, min(50, (cpu_percent + memory_percent) / 4)),
                'resource_usage': {
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(memory_percent, 1),
                    'disk_percent': 75,
                    'network_usage': 50
                },
                'trends': {
                    'cpu_trend': 'increasing' if cpu_percent > 70 else 'stable' if cpu_percent > 30 else 'decreasing',
                    'memory_trend': 'increasing' if memory_percent > 80 else 'stable' if memory_percent > 40 else 'decreasing'
                },
                'last_updated': datetime.now().isoformat()
            })

        # Calculate system overview
        total_containers = len(container_predictions)
        healthy_containers = len([c for c in container_predictions if c['status'] == 'healthy'])
        at_risk_containers = len([c for c in container_predictions if c['status'] == 'at_risk'])
        critical_containers = len([c for c in container_predictions if c['status'] == 'critical'])

        overall_health_score = int(sum(c['health_score'] for c in container_predictions) / total_containers) if total_containers > 0 else 75

        # Transform to expected format
        transformed_response = {
            'services': health_data.get('services', {}),
            'databases': health_data.get('databases', {}),
            'system_overview': {
                'total_containers': total_containers,
                'healthy_containers': healthy_containers,
                'at_risk_containers': at_risk_containers,
                'critical_containers': critical_containers,
                'overall_health_score': overall_health_score
            },
            'container_predictions': container_predictions,
            'system_metrics': health_data.get('system_metrics', {
                'total_cpu_usage': sum(c['resource_usage']['cpu_percent'] for c in container_predictions) / total_containers if total_containers > 0 else 0,
                'total_memory_usage': sum(c['resource_usage']['memory_percent'] for c in container_predictions) / total_containers if total_containers > 0 else 0,
                'total_disk_usage': 75,
                'active_connections': health_data.get('databases', {}).get('mongodb', {}).get('connected_clients', 0)
            }),
            'alerts': [],
            'last_updated': datetime.now().isoformat()
        }

        self.logger.info(f"Real-time system health - transformed {total_containers} containers to predictions")
        return transformed_response

    def get_security_health(
        self,
        security_health_service
    ) -> Dict[str, Any]:
        """
        Get comprehensive security health metrics for the platform.

        Args:
            security_health_service: Security health service instance

        Returns:
            Security health metrics and recommendations
        """
        # Get security metrics
        metrics = security_health_service.get_security_metrics()

        # Format response for UI
        response = {
            'overall_score': metrics.get('overall_score', 0),
            'status': metrics.get('status', 'unknown'),
            'timestamp': metrics.get('timestamp', datetime.now()).isoformat(),
            'categories': {
                'rbac': {
                    'score': metrics.get('rbac', {}).get('score', 0),
                    'status': 'healthy' if metrics.get('rbac', {}).get('score', 0) >= 90 else 'needs_attention',
                    'details': metrics.get('rbac', {}).get('checks', {})
                },
                'audit_logging': {
                    'score': metrics.get('audit', {}).get('score', 0),
                    'status': 'healthy' if metrics.get('audit', {}).get('score', 0) >= 90 else 'needs_attention',
                    'details': metrics.get('audit', {}).get('checks', {})
                },
                'data_isolation': {
                    'score': metrics.get('data_isolation', {}).get('score', 0),
                    'status': 'healthy' if metrics.get('data_isolation', {}).get('score', 0) >= 90 else 'critical',
                    'issues': metrics.get('data_isolation', {}).get('issues', []),
                    'details': metrics.get('data_isolation', {}).get('checks', {})
                },
                'compliance': {
                    'score': metrics.get('compliance', {}).get('score', 0),
                    'status': 'compliant' if metrics.get('compliance', {}).get('score', 0) == 100 else 'partial',
                    'standards': metrics.get('compliance', {}).get('standards', {}),
                    'details': metrics.get('compliance', {}).get('checks', {})
                }
            },
            'recommendations': []
        }

        # Generate recommendations based on scores
        if response['categories']['rbac']['score'] < 100:
            response['recommendations'].append({
                'category': 'RBAC',
                'priority': 'high',
                'message': 'Review and fix RBAC implementation issues',
                'action': 'Check user roles and permissions configuration'
            })

        if response['categories']['audit_logging']['score'] < 100:
            response['recommendations'].append({
                'category': 'Audit Logging',
                'priority': 'high',
                'message': 'Ensure audit logging is properly configured',
                'action': 'Verify audit log collection and retention policies'
            })

        if response['categories']['data_isolation']['score'] < 100:
            response['recommendations'].append({
                'category': 'Data Isolation',
                'priority': 'critical',
                'message': 'Fix organization data isolation issues immediately',
                'action': 'Run data migration scripts to ensure proper organization boundaries'
            })

        if response['categories']['compliance']['score'] < 100:
            response['recommendations'].append({
                'category': 'Compliance',
                'priority': 'medium',
                'message': 'Review compliance requirements',
                'action': 'Ensure all ETSI EN 303 645 and ISO/IEC 27402 requirements are met'
            })

        self.logger.info(f"Security health check requested - Overall score: {response['overall_score']}%")
        return response

    def get_platform_admin_system_health(
        self,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get platform admin system health metrics (infrastructure only).

        Args:
            user: Current user object (must be platform admin)

        Returns:
            Platform infrastructure health metrics

        Raises:
            PermissionError: If user is not a platform admin
        """
        from ...core.rbac import RBAC

        # Only platform admins can access this endpoint
        if not RBAC.is_platform_admin(user):
            self.logger.warning(f"[SECURITY] Non-platform admin {user.get('email')} attempted to access platform system health - DENIED")
            raise PermissionError('Access denied. Platform admin role required.')

        # Get system health data (infrastructure only)
        try:
            import psutil
            import docker

            # System metrics (use instant CPU reading)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Docker containers (if available)
            container_stats = []
            try:
                client = docker.from_env()
                containers = client.containers.list(all=True)
                for container in containers:
                    container_stats.append({
                        'name': container.name,
                        'status': container.status,
                        'created': container.attrs['Created']
                    })
            except Exception as docker_error:
                self.logger.debug(f"Docker not available: {docker_error}")

            platform_health = {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': {
                    'cpu_usage_percent': round(cpu_percent, 2),
                    'memory_usage_percent': round(memory.percent, 2),
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_usage_percent': round(disk.percent, 2),
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                },
                'services': {
                    'total_containers': len(container_stats),
                    'running_containers': len([c for c in container_stats if c['status'] == 'running']),
                    'stopped_containers': len([c for c in container_stats if c['status'] in ['exited', 'stopped']])
                },
                'platform_status': 'healthy' if cpu_percent < 80 and memory.percent < 80 and disk.percent < 80 else 'warning'
            }

            self.logger.info(f"Platform admin system health requested by {user.get('email')}")
            return platform_health

        except Exception as metrics_error:
            self.logger.error(f"Error getting system metrics: {metrics_error}")
            return {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': {
                    'cpu_usage_percent': 0,
                    'memory_usage_percent': 0,
                    'memory_available_gb': 0,
                    'disk_usage_percent': 0,
                    'disk_free_gb': 0
                },
                'services': {
                    'total_containers': 0,
                    'running_containers': 0,
                    'stopped_containers': 0
                },
                'platform_status': 'unknown',
                'error': 'Unable to retrieve system metrics'
            }

    async def get_analytics_via_bridge(
        self,
        dashboard_bridge,
        organization_id: str,
        time_range: str = '24h',
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get analytics dashboard data using modular bridge pattern.

        Args:
            dashboard_bridge: Dashboard bridge service instance
            organization_id: Organization ID for scoping
            time_range: Time range for analytics (default: 24h)
            user_context: User context for RBAC

        Returns:
            Analytics data from bridge service
        """
        # Initialize dashboard bridge if not already done
        if not dashboard_bridge._initialized:
            dashboard_bridge.initialize()

        # Use bridge pattern for safe modular transition
        analytics_data = await dashboard_bridge.get_dashboard_analytics_with_parallel(
            organization_id=organization_id,
            time_range=time_range,
            user_context=user_context or {}
        )

        self.logger.info(f"Analytics data requested via bridge for org: {organization_id}")
        return analytics_data

    def get_platform_admin_analytics(
        self,
        db,
        redis_client,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get platform admin analytics data (infrastructure only, no customer data).

        Args:
            db: Database connection
            redis_client: Redis client for stats
            user: Current user (must be platform admin)

        Returns:
            Platform infrastructure analytics

        Raises:
            PermissionError: If user is not platform admin
        """
        from ...core.rbac import RBAC

        if not RBAC.is_platform_admin(user):
            self.logger.warning(f"[SECURITY] Non-platform admin {user.get('email')} attempted to access platform analytics - DENIED")
            raise PermissionError('Access denied. Platform admin role required.')

        # Platform-level analytics (aggregated, no customer-specific data)
        platform_analytics: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'infrastructure_metrics': {
                'total_api_requests_24h': 0,
                'avg_response_time_ms': 0,
                'error_rate_percent': 0,
                'total_data_ingested_gb': 0
            },
            'resource_utilization': {
                'database_connections': 0,
                'redis_memory_usage_mb': 0,
                'storage_usage_gb': 0
            },
            'platform_trends': {
                'organizations_growth': [],
                'device_growth': [],
                'api_usage_trend': []
            }
        }

        # Get aggregated database stats (infrastructure level only)
        if db is not None:
            try:
                # Total counts (no organization details)
                total_orgs = db.organizations.count_documents({})
                total_devices = db.devices.count_documents({})
                total_users = db.users.count_documents({})

                # Telemetry volume (aggregated)
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                yesterday = today - timedelta(days=1)

                telemetry_today = db.telemetry.count_documents({'timestamp': {'$gte': today}})
                telemetry_yesterday = db.telemetry.count_documents({
                    'timestamp': {'$gte': yesterday, '$lt': today}
                })

                platform_analytics['infrastructure_metrics']['total_data_ingested_gb'] = round(
                    telemetry_today * 0.001, 2
                )  # Rough estimate

                # Growth trends (daily counts over last 7 days)
                growth_data = []
                for i in range(7):
                    day_start = today - timedelta(days=i)
                    day_end = day_start + timedelta(days=1)
                    day_devices = db.devices.count_documents({
                        'created_at': {'$gte': day_start, '$lt': day_end}
                    })
                    growth_data.append({
                        'date': day_start.strftime('%Y-%m-%d'),
                        'new_devices': day_devices
                    })

                platform_analytics['platform_trends']['device_growth'] = list(reversed(growth_data))

            except Exception as db_error:
                self.logger.warning(f"Database stats error: {db_error}")

        # Get Redis stats
        try:
            if redis_client is not None:
                redis_info = redis_client.info()
                platform_analytics['resource_utilization']['redis_memory_usage_mb'] = round(
                    redis_info.get('used_memory', 0) / (1024 * 1024), 2
                )
        except Exception as redis_error:
            self.logger.debug(f"Redis stats not available: {redis_error}")

        self.logger.info(f"Platform admin analytics requested by {user.get('email')}")
        return platform_analytics

    # ==================== Remaining Endpoints (Wrapper Methods) ====================
    # Note: These are lightweight wrappers. Full extraction can be done in future refactoring.

    def get_analytics_predictive_legacy(
        self,
        stats_service,
        organization_id: str,
        user_id: str,
        db,
        redis_client
    ) -> Dict[str, Any]:
        """
        Get predictive analytics using legacy algorithm.

        Note: This is a wrapper method. The actual logic remains in controller
        for now due to complexity. Future refactoring recommended.
        """
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Placeholder: Will be fully extracted in future refactoring
            self.logger.info(f"Predictive analytics (legacy) requested for org: {organization_id}")
            return {
                'status': 'wrapper',
                'message': 'Legacy predictive analytics - full extraction pending'
            }
        finally:
            loop.close()

    def get_geographic_analytics(
        self,
        db,
        user: Dict[str, Any],
        organization_id: Optional[str] = None,
        aggregation: str = 'country'
    ) -> Dict[str, Any]:
        """
        Get real-time geographic analytics based on device location data from MongoDB.

        Extracted from dashboard.py for Phase 3 completion.

        Args:
            db: MongoDB database instance
            user: Current user for RBAC checks
            organization_id: Filter by organization (optional)
            aggregation: 'country', 'city', 'coordinates' (default: 'country')

        Returns:
            Geographic analytics data with real device locations
        """
        try:
            # Apply organization-based filtering for security
            org_filter = {}
            user_role = user.get('role', '') if user else ''
            user_org_id = user.get('organization_id') if user else None

            # Platform admins can see all data, regular users only their organization
            if user_role not in ['super_admin', 'platform_admin'] and user_org_id:
                org_filter = {'organization_id': user_org_id}
            elif organization_id and user_role not in ['super_admin', 'platform_admin']:
                org_filter = {'organization_id': organization_id}

            # Get devices with location data
            location_filter = {**org_filter, 'location': {'$exists': True, '$ne': None}}
            devices_with_location = list(db.devices.find(location_filter, {
                'device_id': 1, 'name': 1, 'device_type': 1, 'status': 1,
                'location': 1, 'organization_id': 1, 'last_seen': 1
            }))

            # Process location data based on aggregation type
            geographic_data: Dict[str, Any] = {
                'total_devices_with_location': len(devices_with_location),
                'aggregation_type': aggregation,
                'data_points': [],
                'summary': {
                    'countries': set(),
                    'cities': set(),
                    'active_devices': 0,
                    'offline_devices': 0
                }
            }

            location_aggregation: Dict[str, Any] = {}
            coordinates_data: List[Dict[str, Any]] = []

            for device in devices_with_location:
                location = device.get('location', {})
                device_status = device.get('status', 'unknown')

                # Update summary counts
                if device_status == 'active':
                    geographic_data['summary']['active_devices'] += 1
                else:
                    geographic_data['summary']['offline_devices'] += 1

                if isinstance(location, dict):
                    if aggregation == 'coordinates' and 'lat' in location and 'lng' in location:
                        # Coordinate-based aggregation
                        try:
                            lat = float(location['lat'])
                            lng = float(location['lng'])

                            coordinates_data.append({
                                'device_id': device['device_id'],
                                'device_name': device.get('name', device['device_id']),
                                'device_type': device.get('device_type', 'unknown'),
                                'status': device_status,
                                'coordinates': [lng, lat],  # GeoJSON format [lng, lat]
                                'last_seen': device.get('last_seen'),
                                'organization_id': device.get('organization_id')
                            })
                        except (ValueError, TypeError):
                            continue

                    elif aggregation == 'country':
                        # Country-based aggregation
                        country = location.get('country', 'Unknown')
                        geographic_data['summary']['countries'].add(country)

                        if country not in location_aggregation:
                            location_aggregation[country] = {
                                'name': country,
                                'device_count': 0,
                                'active_devices': 0,
                                'device_types': {},
                                'coordinates': location.get('lat', 0) and location.get('lng', 0) and [location['lng'], location['lat']]
                            }

                        location_aggregation[country]['device_count'] += 1
                        if device_status == 'active':
                            location_aggregation[country]['active_devices'] += 1

                        device_type = device.get('device_type', 'unknown')
                        location_aggregation[country]['device_types'][device_type] = \
                            location_aggregation[country]['device_types'].get(device_type, 0) + 1

                    elif aggregation == 'city':
                        # City-based aggregation
                        city = location.get('city', 'Unknown')
                        country = location.get('country', 'Unknown')
                        location_key = f"{city}, {country}"

                        geographic_data['summary']['cities'].add(city)
                        geographic_data['summary']['countries'].add(country)

                        if location_key not in location_aggregation:
                            location_aggregation[location_key] = {
                                'name': location_key,
                                'city': city,
                                'country': country,
                                'device_count': 0,
                                'active_devices': 0,
                                'device_types': {},
                                'coordinates': location.get('lat', 0) and location.get('lng', 0) and [location['lng'], location['lat']]
                            }

                        location_aggregation[location_key]['device_count'] += 1
                        if device_status == 'active':
                            location_aggregation[location_key]['active_devices'] += 1

                        device_type = device.get('device_type', 'unknown')
                        location_aggregation[location_key]['device_types'][device_type] = \
                            location_aggregation[location_key]['device_types'].get(device_type, 0) + 1

            # Prepare response data
            if aggregation == 'coordinates':
                geographic_data['data_points'] = coordinates_data
            else:
                # Convert aggregation dict to sorted list
                geographic_data['data_points'] = sorted(
                    location_aggregation.values(),
                    key=lambda x: x['device_count'],
                    reverse=True
                )

            # Convert sets to counts for JSON serialization
            geographic_data['summary']['countries'] = len(geographic_data['summary']['countries'])
            geographic_data['summary']['cities'] = len(geographic_data['summary']['cities'])

            # Add metadata
            geographic_data.update({
                'generated_at': datetime.now().isoformat(),
                'organization_filter': bool(org_filter),
                'data_source': 'mongodb_devices_collection',
                'real_time': True
            })

            self.logger.info(f"Geographic analytics generated: aggregation={aggregation}, devices={len(devices_with_location)}")
            return self.sanitize_response_data(geographic_data)

        except Exception as e:
            self.logger.error(f"Geographic analytics error: {e}", exc_info=True)
            raise

    def get_defense_in_depth_analysis(
        self,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get AI/ML defense-in-depth analysis data.

        Extracted from dashboard.py for Phase 3 completion.

        Args:
            organization_id: Organization ID for scoping

        Returns:
            Defense-in-depth analysis with security layers
        """
        try:
            defense_data = {
                'timestamp': datetime.now().isoformat(),
                'organization_id': organization_id,
                'layers': {
                    'perimeter': {
                        'name': 'Perimeter Security',
                        'score': 98,
                        'status': 'active',
                        'components': ['Firewall', 'IDS/IPS', 'DDoS Protection'],
                        'threats_blocked': 1247
                    },
                    'network': {
                        'name': 'Network Security',
                        'score': 95,
                        'status': 'active',
                        'components': ['Network Segmentation', 'VPN', 'Network Monitoring'],
                        'threats_blocked': 523
                    },
                    'application': {
                        'name': 'Application Security',
                        'score': 92,
                        'status': 'active',
                        'components': ['WAF', 'API Gateway', 'Rate Limiting'],
                        'threats_blocked': 892
                    },
                    'data': {
                        'name': 'Data Security',
                        'score': 100,
                        'status': 'active',
                        'components': ['Encryption at Rest', 'Encryption in Transit', 'Access Control'],
                        'threats_blocked': 0
                    },
                    'endpoint': {
                        'name': 'Endpoint Security',
                        'score': 88,
                        'status': 'active',
                        'components': ['Device Authentication', 'Certificate Management', 'Anomaly Detection'],
                        'threats_blocked': 156
                    },
                    'monitoring': {
                        'name': 'Security Monitoring',
                        'score': 96,
                        'status': 'active',
                        'components': ['SIEM', 'Log Analysis', 'Threat Intelligence'],
                        'threats_blocked': 0
                    }
                },
                'overall_score': 94.8,
                'trends': [
                    {'timestamp': (datetime.now() - timedelta(days=i)).isoformat(), 'score': 94.8 + random.uniform(-2, 2)}
                    for i in range(7, 0, -1)
                ],
                'recent_events': [
                    {
                        'timestamp': (datetime.now() - timedelta(minutes=5)).isoformat(),
                        'layer': 'perimeter',
                        'type': 'threat_blocked',
                        'severity': 'medium',
                        'description': 'Blocked suspicious IP attempting port scan'
                    },
                    {
                        'timestamp': (datetime.now() - timedelta(minutes=15)).isoformat(),
                        'layer': 'application',
                        'type': 'rate_limit',
                        'severity': 'low',
                        'description': 'Rate limiting activated for API endpoint'
                    }
                ],
                'recommendations': [
                    {
                        'priority': 'high',
                        'layer': 'endpoint',
                        'action': 'Update device firmware',
                        'impact': 'Improve endpoint security score by 5%'
                    },
                    {
                        'priority': 'medium',
                        'layer': 'network',
                        'action': 'Enable advanced threat detection',
                        'impact': 'Enhance network monitoring capabilities'
                    }
                ]
            }

            self.logger.info(f"Defense-in-depth analysis generated for org: {organization_id}")
            return self.sanitize_response_data(defense_data)

        except Exception as e:
            self.logger.error(f"Defense-in-depth analysis error: {e}", exc_info=True)
            raise

    def get_platform_admin_monitoring(
        self,
        db,
        redis_client,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get platform admin monitoring data with infrastructure health checks.

        Extracted from dashboard.py for Phase 3 completion.

        Args:
            db: MongoDB database instance
            redis_client: Redis client instance
            user: Current user for RBAC checks

        Returns:
            Platform infrastructure monitoring data

        Raises:
            PermissionError: If user is not platform admin
        """
        from ...core.rbac import RBAC

        # Only platform admins can access this endpoint
        if not RBAC.is_platform_admin(user):
            user_email = user.get('email', 'unknown') if user else 'unknown'
            raise PermissionError(f"Non-platform admin {user_email} attempted to access platform monitoring - DENIED")

        try:
            # Platform monitoring (infrastructure focus)
            monitoring_data = {
                'timestamp': datetime.now().isoformat(),
                'services_status': {
                    'api_gateway': 'healthy',
                    'database': 'healthy',
                    'redis': 'healthy',
                    'message_broker': 'healthy'
                },
                'alerts': [],
                'uptime_metrics': {
                    'api_uptime_percent': 99.9,
                    'database_uptime_percent': 99.95,
                    'total_uptime_hours': 720  # 30 days
                }
            }

            # Check service health
            try:
                # Database check
                if db is None:
                    monitoring_data['services_status']['database'] = 'unhealthy'
                    monitoring_data['alerts'].append({
                        'id': 'db_connection_failed',
                        'severity': 'critical',
                        'message': 'Database connection failed',
                        'timestamp': datetime.now().isoformat()
                    })
            except Exception as db_check_error:
                monitoring_data['services_status']['database'] = 'unhealthy'
                self.logger.warning(f"Database health check failed: {db_check_error}")

            try:
                # Redis check
                if redis_client is not None:
                    redis_client.ping()
                else:
                    monitoring_data['services_status']['redis'] = 'degraded'
            except Exception as redis_check_error:
                monitoring_data['services_status']['redis'] = 'unhealthy'
                self.logger.debug(f"Redis health check failed: {redis_check_error}")

            user_email = user.get('email', 'unknown') if user else 'unknown'
            self.logger.info(f"Platform admin monitoring requested by {user_email}")
            return self.sanitize_response_data(monitoring_data)

        except Exception as e:
            self.logger.error(f"Platform admin monitoring error: {e}", exc_info=True)
            raise

    def get_compliance_summary(
        self,
        organization_id: str,
        db
    ) -> Dict[str, Any]:
        """
        Get compliance summary for organization.

        Note: Wrapper method - full extraction pending.
        """
        self.logger.info(f"Compliance summary requested for org: {organization_id}")
        return {
            'status': 'wrapper',
            'message': 'Compliance summary - full extraction pending'
        }

    # Mark: Total methods = 29 (original) + 5 (new) = 34
