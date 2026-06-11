# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Service Modular Bridge
================================
Version: v2025.08
Module: Dashboard Bridge
Purpose: Bridge between legacy and modular dashboard implementations

This module provides the integration layer between the existing
dashboard controller and the new modular dashboard service.
It uses feature flags and parallel runner to ensure safe migration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from flask import g
from datetime import datetime

from .feature_flags import feature_flags
from .parallel_runner import parallel_runner
from ..modules.dashboard.interfaces import IDashboardService
from ..modules.dashboard.models.dashboard_models import DashboardStatsRequest, DashboardAnalyticsRequest
from ..core.di_container import container

logger = logging.getLogger(__name__)

# Register the modular services in DI container
def register_dashboard_service():
    """Register dashboard services in DI container when available"""
    try:
        from ..modules.dashboard.services import DashboardStatsService
        from ..modules.dashboard.services.dashboard_analytics_service import DashboardAnalyticsService
        from ..modules.dashboard.interfaces import IDashboardAnalyticsService

        container.register_singleton(IDashboardService, DashboardStatsService)
        container.register_singleton(IDashboardAnalyticsService, DashboardAnalyticsService)
        logger.info("Dashboard modular services registered successfully")
    except ImportError as e:
        logger.warning(f"Dashboard modular services not available yet: {e}")


class DashboardModularBridge:
    """
    Bridge between legacy and modular dashboard implementations.
    Ensures zero-risk transition through parallel execution and validation.
    """
    
    def __init__(self):
        """Initialize bridge with both implementations"""
        self.legacy_service = None  # Will be injected
        self.modular_service = None  # Will be resolved from DI container
        self._initialized = False
    
    def initialize(self, legacy_service: Any = None):
        """
        Initialize bridge with legacy service reference
        
        Args:
            legacy_service: Existing dashboard implementation (optional)
        """
        self.legacy_service = legacy_service
        
        # Try to get modular service from DI container
        try:
            register_dashboard_service()
            self.modular_service = container.resolve(IDashboardService)
            logger.info("Dashboard modular service resolved from DI container")
        except Exception as e:
            logger.warning(f"Could not resolve modular dashboard service: {e}")
            self.modular_service = None
        
        self._initialized = True
    
    def _ensure_initialized(self):
        """Ensure bridge is initialized"""
        if not self._initialized:
            self.initialize()
    
    async def get_dashboard_stats_with_parallel(
        self,
        organization_id: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics with parallel execution between legacy and modular implementations.
        
        Args:
            organization_id: Organization identifier
            user_context: Optional user context for RBAC
            
        Returns:
            Dashboard statistics
        """
        self._ensure_initialized()
        
        # Check feature flag
        context = {
            'user_id': user_context.get('_id') if user_context else None,
            'is_internal': user_context.get('is_internal', False) if user_context else False,
            'ip': g.get('client_ip', '127.0.0.1')
        }
        
        if not feature_flags.is_enabled('modular_dashboard', context):
            # Feature disabled, use legacy implementation only
            return await self._get_legacy_dashboard_stats(organization_id, user_context)
        
        try:
            # Run both implementations in parallel
            result = await parallel_runner.run_parallel(
                module_name="dashboard.stats",
                function_name="get_dashboard_stats",
                old_func=lambda: self._get_legacy_dashboard_stats_sync(organization_id, user_context),
                new_func=lambda: asyncio.create_task(self._get_modular_dashboard_stats(organization_id, user_context))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Parallel dashboard stats execution failed: {str(e)}")
            feature_flags.record_error('modular_dashboard')
            # Fallback to legacy implementation
            return await self._get_legacy_dashboard_stats(organization_id, user_context)
    
    async def get_dashboard_analytics_with_parallel(
        self,
        organization_id: str,
        time_range: str = "24h",
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard analytics with parallel execution.
        
        Args:
            organization_id: Organization identifier
            time_range: Time range for analytics (1h, 6h, 24h, 7d)
            user_context: Optional user context for RBAC
            
        Returns:
            Dashboard analytics data
        """
        self._ensure_initialized()
        
        # Check feature flag
        context = {
            'user_id': user_context.get('_id') if user_context else None,
            'is_internal': user_context.get('is_internal', False) if user_context else False,
            'ip': g.get('client_ip', '127.0.0.1')
        }
        
        if not feature_flags.is_enabled('modular_dashboard', context):
            # Feature disabled, use legacy implementation only
            return await self._get_legacy_dashboard_analytics(organization_id, time_range, user_context)
        
        try:
            # Run both implementations in parallel
            result = await parallel_runner.run_parallel(
                module_name="dashboard.analytics",
                function_name="get_dashboard_analytics",
                old_func=lambda: self._get_legacy_dashboard_analytics_sync(organization_id, time_range, user_context),
                new_func=lambda: asyncio.create_task(self._get_modular_dashboard_analytics(organization_id, time_range, user_context))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Parallel dashboard analytics execution failed: {str(e)}")
            feature_flags.record_error('modular_dashboard')
            # Fallback to legacy implementation
            return await self._get_legacy_dashboard_analytics(organization_id, time_range, user_context)
    
    async def get_realtime_metrics_with_parallel(
        self,
        organization_id: str,
        metric_types: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get real-time metrics with parallel execution.
        
        Args:
            organization_id: Organization identifier
            metric_types: Optional list of specific metrics to retrieve
            user_context: Optional user context for RBAC
            
        Returns:
            Real-time metrics data
        """
        self._ensure_initialized()
        
        # Check feature flag
        context = {
            'user_id': user_context.get('_id') if user_context else None,
            'is_internal': user_context.get('is_internal', False) if user_context else False,
            'ip': g.get('client_ip', '127.0.0.1')
        }
        
        if not feature_flags.is_enabled('modular_dashboard', context):
            # Feature disabled, use legacy implementation only
            return await self._get_legacy_realtime_metrics(organization_id, metric_types, user_context)
        
        try:
            # Run both implementations in parallel
            result = await parallel_runner.run_parallel(
                module_name="dashboard.realtime",
                function_name="get_realtime_metrics",
                old_func=lambda: self._get_legacy_realtime_metrics_sync(organization_id, metric_types, user_context),
                new_func=lambda: asyncio.create_task(self._get_modular_realtime_metrics(organization_id, metric_types, user_context))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Parallel realtime metrics execution failed: {str(e)}")
            feature_flags.record_error('modular_dashboard')
            # Fallback to legacy implementation
            return await self._get_legacy_realtime_metrics(organization_id, metric_types, user_context)
    
    async def get_monitoring_dashboard_with_parallel(
        self,
        organization_id: str,
        components: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get monitoring dashboard with parallel execution.
        
        Args:
            organization_id: Organization identifier
            components: Optional list of components to monitor
            user_context: Optional user context for RBAC
            
        Returns:
            Monitoring dashboard data
        """
        self._ensure_initialized()
        
        # Check feature flag
        context = {
            'user_id': user_context.get('_id') if user_context else None,
            'is_internal': user_context.get('is_internal', False) if user_context else False,
            'ip': g.get('client_ip', '127.0.0.1')
        }
        
        if not feature_flags.is_enabled('modular_dashboard', context):
            # Feature disabled, use legacy implementation only
            return await self._get_legacy_monitoring_dashboard(organization_id, components, user_context)
        
        try:
            # Run both implementations in parallel
            result = await parallel_runner.run_parallel(
                module_name="dashboard.monitoring",
                function_name="get_monitoring_dashboard",
                old_func=lambda: self._get_legacy_monitoring_dashboard_sync(organization_id, components, user_context),
                new_func=lambda: asyncio.create_task(self._get_modular_monitoring_dashboard(organization_id, components, user_context))
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Parallel monitoring dashboard execution failed: {str(e)}")
            feature_flags.record_error('modular_dashboard')
            # Fallback to legacy implementation
            return await self._get_legacy_monitoring_dashboard(organization_id, components, user_context)
    
    # Legacy implementation wrappers
    async def _get_legacy_dashboard_stats(self, organization_id: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call legacy dashboard stats implementation"""
        # Import here to avoid circular imports
        from ..controllers.dashboard import _get_dashboard_stats_legacy
        
        # Set up Flask g context for legacy function
        if user_context:
            g.current_user = user_context
            g.organization_id = organization_id
        
        try:
            # Call legacy implementation (it returns a tuple with JSON response and status)
            response, status = _get_dashboard_stats_legacy()
            if status == 200:
                return response.get_json()
            else:
                raise Exception(f"Legacy stats failed with status {status}")
        except Exception as e:
            logger.error(f"Legacy dashboard stats failed: {e}")
            raise
    
    def _get_legacy_dashboard_stats_sync(self, organization_id: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronous wrapper for legacy dashboard stats"""
        return asyncio.run(self._get_legacy_dashboard_stats(organization_id, user_context))
    
    async def _get_legacy_dashboard_analytics(self, organization_id: str, time_range: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call legacy dashboard analytics implementation"""
        # Import here to avoid circular imports
        from ..controllers.dashboard import get_analytics
        
        # Set up Flask g context for legacy function
        if user_context:
            g.current_user = user_context
            g.organization_id = organization_id
        
        try:
            # Call legacy implementation
            response, status = get_analytics()
            if status == 200:
                return response.get_json()
            else:
                raise Exception(f"Legacy analytics failed with status {status}")
        except Exception as e:
            logger.error(f"Legacy dashboard analytics failed: {e}")
            raise
    
    def _get_legacy_dashboard_analytics_sync(self, organization_id: str, time_range: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronous wrapper for legacy dashboard analytics"""
        return asyncio.run(self._get_legacy_dashboard_analytics(organization_id, time_range, user_context))
    
    async def _get_legacy_realtime_metrics(self, organization_id: str, metric_types: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call legacy realtime metrics implementation"""
        # Placeholder for legacy realtime metrics - would integrate with existing services
        return {
            'success': True,
            'metrics': {
                'active_devices': 0,
                'messages_per_minute': 0,
                'avg_latency': 0
            },
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'legacy'
        }
    
    def _get_legacy_realtime_metrics_sync(self, organization_id: str, metric_types: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronous wrapper for legacy realtime metrics"""
        return asyncio.run(self._get_legacy_realtime_metrics(organization_id, metric_types, user_context))
    
    # Modular implementation wrappers
    async def _get_modular_dashboard_stats(self, organization_id: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call modular dashboard stats implementation"""
        if not self.modular_service:
            raise RuntimeError("Modular dashboard service not available")
        
        try:
            # Create request object
            request = DashboardStatsRequest(
                organization_id=organization_id,
                include_devices=True,
                include_users=True,
                include_activity=True,
                user_context=user_context
            )
            
            # Call modular service
            result = await self.modular_service.get_organization_stats(request)
            return result
            
        except Exception as e:
            logger.error(f"Modular dashboard stats failed: {e}")
            raise
    
    async def _get_modular_dashboard_analytics(self, organization_id: str, time_range: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call modular dashboard analytics implementation"""
        if not self.modular_service:
            # Try to get analytics service directly
            try:
                from ..modules.dashboard.interfaces import IDashboardAnalyticsService
                analytics_service = container.resolve(IDashboardAnalyticsService)
                
                if analytics_service:
                    return await analytics_service.get_dashboard_analytics(
                        organization_id=organization_id,
                        time_range=time_range,
                        user_context=user_context
                    )
                else:
                    raise RuntimeError("Analytics service not available")
                    
            except Exception as e:
                logger.error(f"Could not resolve analytics service: {e}")
                raise RuntimeError("Modular dashboard service not available")
        
        try:
            # Create request object
            request = DashboardAnalyticsRequest(
                organization_id=organization_id,
                time_range=time_range,
                include_telemetry=True,
                include_devices=True,
                include_users=True,
                user_context=user_context
            )
            
            # Call modular service
            result = await self.modular_service.get_analytics_data(request)
            return result
            
        except Exception as e:
            logger.error(f"Modular dashboard analytics failed: {e}")
            raise
    
    async def _get_modular_realtime_metrics(self, organization_id: str, metric_types: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call modular realtime metrics implementation"""
        if not self.modular_service:
            # Try to get monitoring service directly
            try:
                from ..modules.dashboard.interfaces import IMonitoringDashboardService
                monitoring_service = container.resolve(IMonitoringDashboardService)
                
                if monitoring_service:
                    return await monitoring_service.get_real_time_metrics(
                        organization_id=organization_id,
                        metric_types=metric_types or [],
                        time_window=300
                    )
                else:
                    raise RuntimeError("Monitoring service not available")
                    
            except Exception as e:
                logger.error(f"Could not resolve monitoring service: {e}")
                raise RuntimeError("Modular monitoring service not available")
        
        try:
            # Call modular service through bridge interface
            result = await self.modular_service.get_realtime_metrics(
                organization_id=organization_id,
                metric_types=metric_types,
                user_context=user_context
            )
            return result
            
        except Exception as e:
            logger.error(f"Modular realtime metrics failed: {e}")
            raise
    
    async def _get_modular_monitoring_dashboard(self, organization_id: str, components: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call modular monitoring dashboard implementation"""
        try:
            from ..modules.dashboard.interfaces import IMonitoringDashboardService
            from ..modules.dashboard.services.monitoring_dashboard_service import MonitoringDashboardRequest
            
            monitoring_service = container.resolve(IMonitoringDashboardService)
            
            if not monitoring_service:
                raise RuntimeError("Monitoring service not available")
            
            # Create request object
            request = MonitoringDashboardRequest(
                organization_id=organization_id,
                user_context=user_context,
                components=components or [],
                metric_types=['system', 'network', 'requests', 'alerts'],
                time_window=300
            )
            
            # Call modular service
            result = await monitoring_service.get_monitoring_dashboard(request)
            return result.to_dict()
            
        except Exception as e:
            logger.error(f"Modular monitoring dashboard failed: {e}")
            raise
    
    # Legacy wrapper methods for sync execution
    def _get_legacy_monitoring_dashboard_sync(self, organization_id: str, components: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync wrapper for legacy monitoring dashboard"""
        return asyncio.get_event_loop().run_until_complete(
            self._get_legacy_monitoring_dashboard(organization_id, components, user_context)
        )
    
    async def _get_legacy_monitoring_dashboard(self, organization_id: str, components: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call legacy monitoring dashboard implementation"""
        # Mock legacy implementation - would call dashboard.py endpoint
        return {
            'services': {
                'api_server': {'status': 'healthy', 'uptime': '2h 45m'},
                'database': {'status': 'healthy', 'connections': 15},
                'vault': {'status': 'healthy', 'sealed': False},
                'redis': {'status': 'healthy', 'memory_usage': '45MB'}
            },
            'external_links': {
                'grafana': 'http://localhost:3000',
                'prometheus': 'http://localhost:9091'
            },
            'recent_alerts': [],
            'system_metrics': {'total_requests_24h': 12450},
            'generated_at': datetime.now().isoformat(),
            'source': 'legacy'
        }
    
    def _get_legacy_realtime_metrics_sync(self, organization_id: str, metric_types: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync wrapper for legacy realtime metrics"""
        return asyncio.get_event_loop().run_until_complete(
            self._get_legacy_realtime_metrics(organization_id, metric_types, user_context)
        )
    
    async def _get_legacy_realtime_metrics(self, organization_id: str, metric_types: Optional[List[str]], user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Call legacy realtime metrics implementation"""
        # Mock legacy implementation - would call dashboard.py endpoint
        return {
            'status': 'success',
            'data': {
                'system': {'cpu_usage': 45.2, 'memory_usage': 67.8},
                'network': {'bytes_sent': 1024000, 'bytes_recv': 2048000},
                'requests': {'total_requests': 1245, 'successful_requests': 1215}
            },
            'timestamp': datetime.now().isoformat(),
            'source': 'legacy'
        }

# Global instance
dashboard_bridge = DashboardModularBridge()


# Export functions for easy integration
__all__ = [
    'DashboardModularBridge',
    'dashboard_bridge'
]