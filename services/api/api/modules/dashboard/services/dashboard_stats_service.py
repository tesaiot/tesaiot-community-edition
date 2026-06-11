# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Statistics Service Implementation
Purpose: Core statistics service for dashboard operations
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 2
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from ..interfaces import IDashboardStatsService
from ..repositories.dashboard_stats_repository import DashboardStatsRepository
from ..models.dashboard_models import (
    StatsFilter, StatsSecurityContext
)
from ..utils.metrics_decorator import track_dashboard_method, DashboardMetricsCollector

logger = logging.getLogger(__name__)


class ModularDashboardStatsService(IDashboardStatsService):
    """Modular implementation of dashboard statistics service"""
    
    def __init__(
        self,
        repository: DashboardStatsRepository,
        cache_service: Optional[Any] = None,
        utilities_service: Optional[Any] = None
    ):
        """
        Initialize dashboard stats service
        
        Args:
            repository: Data repository for statistics
            cache_service: Optional cache service
            utilities_service: Optional utilities service
        """
        self.repository = repository
        self.cache = cache_service
        self.utilities = utilities_service
        self.metrics_collector = DashboardMetricsCollector()
        self.logger = logger
    
    @track_dashboard_method('dashboard_stats_service')
    async def get_organization_stats(
        self,
        organization_id: str,
        include_devices: bool = True,
        include_users: bool = True,
        include_activity: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive organization statistics with RBAC enforcement
        
        Args:
            organization_id: Organization identifier
            include_devices: Include device statistics
            include_users: Include user statistics  
            include_activity: Include activity statistics
            
        Returns:
            Dict containing organization statistics
            
        Raises:
            ValueError: If organization_id is invalid or access denied
            Exception: If statistics retrieval fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate input
            if not organization_id or not isinstance(organization_id, str):
                raise ValueError("organization_id must be a non-empty string")
            
            # Create security context from current request context
            security_context = self._get_security_context(organization_id)
            
            # Create stats filter
            stats_filter = StatsFilter(
                organization_id=organization_id,
                include_devices=include_devices,
                include_users=include_users,
                include_activity=include_activity
            )
            
            # Check cache first
            cache_key = self._create_cache_key(
                'org_stats',
                organization_id,
                {
                    'devices': include_devices,
                    'users': include_users,
                    'activity': include_activity
                }
            )
            
            cached_result = await self._get_cached_stats(cache_key, organization_id)
            if cached_result:
                self.metrics_collector.record_cache_operation('get', True, cache_key)
                return cached_result
            
            self.metrics_collector.record_cache_operation('get', False, cache_key)
            
            # Get stats from repository
            stats_result = await self.repository.get_organization_stats(
                security_context, stats_filter
            )
            
            # Apply data sanitization
            sanitized_stats = self._sanitize_stats_data(stats_result.to_dict())
            
            # Cache the result
            await self._cache_stats_result(cache_key, organization_id, sanitized_stats)
            
            # Record metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics_collector.record_stat_computation(
                'organization_stats', execution_time, 1
            )
            
            self.logger.info(
                f"Retrieved organization stats for org_id={organization_id}, "
                f"execution_time={execution_time:.3f}s"
            )
            
            return sanitized_stats
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Error getting organization stats: {e}")
            raise Exception(f"Failed to retrieve organization statistics: {str(e)}")
    
    @track_dashboard_method('dashboard_stats_service')
    async def get_device_summary_stats(
        self,
        organization_id: str,
        time_period: str = "7d",
        device_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get device summary statistics for specified time period
        
        Args:
            organization_id: Organization identifier
            time_period: Time period for statistics
            device_types: Optional device type filter
            
        Returns:
            Dict containing device statistics
            
        Raises:
            ValueError: If parameters are invalid
            Exception: If statistics retrieval fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate input
            if not organization_id or not isinstance(organization_id, str):
                raise ValueError("organization_id must be a non-empty string")
            
            if time_period not in ['1h', '6h', '24h', '7d', '30d', '90d']:
                raise ValueError("Invalid time_period. Must be one of: 1h, 6h, 24h, 7d, 30d, 90d")
            
            # Create security context
            security_context = self._get_security_context(organization_id)
            
            # Create stats filter with time range
            start_date, end_date = self._parse_time_period(time_period)
            stats_filter = StatsFilter(
                organization_id=organization_id,
                device_types=device_types,
                time_period=time_period,
                start_date=start_date,
                end_date=end_date
            )
            
            # Check cache
            cache_key = self._create_cache_key(
                'device_summary',
                organization_id,
                {
                    'time_period': time_period,
                    'device_types': device_types or []
                }
            )
            
            cached_result = await self._get_cached_stats(cache_key, organization_id)
            if cached_result:
                self.metrics_collector.record_cache_operation('get', True, cache_key)
                return cached_result
            
            self.metrics_collector.record_cache_operation('get', False, cache_key)
            
            # Get device summary from repository
            device_summary = await self.repository.get_device_summary_stats(
                security_context, stats_filter
            )
            
            # Convert to dict and sanitize
            result_dict = device_summary.to_dict()
            sanitized_result = self._sanitize_stats_data(result_dict)
            
            # Cache the result
            await self._cache_stats_result(cache_key, organization_id, sanitized_result, ttl=180)
            
            # Record metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.metrics_collector.record_stat_computation(
                'device_summary', execution_time, 1
            )
            
            return sanitized_result
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Error getting device summary stats: {e}")
            raise Exception(f"Failed to retrieve device summary statistics: {str(e)}")
    
    # Security and validation methods
    def _get_security_context(self, organization_id: str) -> StatsSecurityContext:
        """
        Create security context from current request
        
        Args:
            organization_id: Target organization ID
            
        Returns:
            StatsSecurityContext with current user's permissions
        """
        try:
            # Try to get current user context from Flask g object
            from flask import g
            
            if hasattr(g, 'current_user') and g.current_user:
                user_role = g.current_user.get('role', '')
                user_org_id = g.organization_id if hasattr(g, 'organization_id') else None
                
                # Check if user is platform admin
                platform_admin = user_role == 'platform_admin'
                
                return StatsSecurityContext(
                    user_role=user_role,
                    organization_id=user_org_id,
                    platform_admin=platform_admin
                )
            else:
                # Fallback for testing or non-Flask contexts
                return StatsSecurityContext(
                    user_role='user',
                    organization_id=organization_id,
                    platform_admin=False
                )
                
        except ImportError:
            # Flask not available, create minimal context
            return StatsSecurityContext(
                user_role='user',
                organization_id=organization_id,
                platform_admin=False
            )
        except Exception as e:
            self.logger.warning(f"Error creating security context: {e}")
            # Create safe fallback context
            return StatsSecurityContext(
                user_role='user',
                organization_id=organization_id,
                platform_admin=False
            )
    
    def _parse_time_period(self, time_period: str) -> tuple[datetime, datetime]:
        """
        Parse time period string to start and end dates
        
        Args:
            time_period: Time period string (e.g., '7d', '24h')
            
        Returns:
            Tuple of (start_date, end_date)
        """
        end_date = datetime.utcnow()
        
        if time_period == '1h':
            start_date = end_date - timedelta(hours=1)
        elif time_period == '6h':
            start_date = end_date - timedelta(hours=6)
        elif time_period == '24h':
            start_date = end_date - timedelta(hours=24)
        elif time_period == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_period == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            # Default to 7 days
            start_date = end_date - timedelta(days=7)
        
        return start_date, end_date
    
    # Cache management methods
    def _create_cache_key(
        self,
        operation: str,
        organization_id: str,
        parameters: Dict[str, Any]
    ) -> str:
        """
        Create cache key for statistics
        
        Args:
            operation: Type of operation
            organization_id: Organization identifier
            parameters: Operation parameters
            
        Returns:
            Cache key string
        """
        try:
            if self.utilities and hasattr(self.utilities, 'create_cache_key'):
                return self.utilities.create_cache_key(organization_id, operation, parameters)
            else:
                # Fallback cache key generation
                import hashlib
                param_str = str(sorted(parameters.items()))
                param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
                return f"dashboard_stats:{organization_id}:{operation}:{param_hash}"
                
        except Exception as e:
            self.logger.warning(f"Error creating cache key: {e}")
            return f"dashboard_stats:{organization_id}:{operation}:{hash(str(parameters))}"
    
    async def _get_cached_stats(
        self,
        cache_key: str,
        organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached statistics result
        
        Args:
            cache_key: Cache key
            organization_id: Organization identifier
            
        Returns:
            Cached result or None
        """
        try:
            if self.repository:
                return await self.repository.get_cached_result(organization_id, cache_key)
            return None
            
        except Exception as e:
            self.logger.warning(f"Error getting cached stats: {e}")
            return None
    
    async def _cache_stats_result(
        self,
        cache_key: str,
        organization_id: str,
        data: Dict[str, Any],
        ttl: int = 300
    ) -> None:
        """
        Cache statistics result
        
        Args:
            cache_key: Cache key
            organization_id: Organization identifier
            data: Data to cache
            ttl: Time to live in seconds
        """
        try:
            if self.repository:
                await self.repository.cache_dashboard_result(
                    organization_id, cache_key, data, ttl
                )
                self.metrics_collector.record_cache_operation('set', True, cache_key)
                
        except Exception as e:
            self.logger.warning(f"Error caching stats result: {e}")
            self.metrics_collector.record_cache_operation('set', False, cache_key)
    
    # Data sanitization methods
    def _sanitize_stats_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize statistics data to prevent NaN/Infinity issues
        
        Args:
            data: Raw statistics data
            
        Returns:
            Sanitized data
        """
        try:
            if self.utilities and hasattr(self.utilities, 'sanitize_response_data'):
                return self.utilities.sanitize_response_data(data)
            else:
                # Fallback sanitization
                return self._fallback_sanitize_data(data)
                
        except Exception as e:
            self.logger.warning(f"Error sanitizing data: {e}")
            return data
    
    def _fallback_sanitize_data(self, data: Any) -> Any:
        """
        Fallback data sanitization when utilities service is not available
        
        Args:
            data: Data to sanitize
            
        Returns:
            Sanitized data
        """
        import math
        
        if isinstance(data, dict):
            return {key: self._fallback_sanitize_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._fallback_sanitize_data(item) for item in data]
        elif isinstance(data, (int, float)):
            if math.isnan(data) or math.isinf(data):
                return 0
            return data
        else:
            return data
    
    # Metrics and monitoring
    def get_service_metrics(self) -> Dict[str, Any]:
        """
        Get service performance metrics
        
        Returns:
            Dict containing service metrics
        """
        return self.metrics_collector.get_summary()
    
    def reset_metrics(self) -> None:
        """Reset metrics collector"""
        self.metrics_collector = DashboardMetricsCollector()


# Factory function for creating service instance
def create_dashboard_stats_service(
    db_session: Any,
    cache_service: Optional[Any] = None,
    utilities_service: Optional[Any] = None
) -> ModularDashboardStatsService:
    """
    Factory function to create dashboard stats service
    
    Args:
        db_session: Database session
        cache_service: Optional cache service
        utilities_service: Optional utilities service
        
    Returns:
        Configured ModularDashboardStatsService instance
    """
    repository = DashboardStatsRepository(db_session, cache_service)
    
    return ModularDashboardStatsService(
        repository=repository,
        cache_service=cache_service,
        utilities_service=utilities_service
    )