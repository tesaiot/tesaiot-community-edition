# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Statistics Repository Implementation
Purpose: Data access layer for dashboard statistics
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 2
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from pymongo.errors import PyMongoError

from ..interfaces import IDashboardRepository
from ..models.dashboard_models import (
    DashboardStatsResult, DeviceSummaryStats, StatsFilter, 
    StatsSecurityContext
)
from ..utils.metrics_decorator import track_dashboard_method

logger = logging.getLogger(__name__)


class DashboardStatsRepository(IDashboardRepository):
    """Repository for dashboard statistics data access"""
    
    def __init__(self, db_session: Any, cache_service: Optional[Any] = None):
        """
        Initialize dashboard stats repository
        
        Args:
            db_session: Database session/connection
            cache_service: Optional cache service
        """
        self.db = db_session
        self.cache = cache_service
        self.logger = logger
    
    @track_dashboard_method('dashboard_stats_repository')
    async def get_organization_stats(
        self,
        security_context: StatsSecurityContext,
        stats_filter: StatsFilter
    ) -> DashboardStatsResult:
        """
        Get organization statistics with security validation
        
        Args:
            security_context: Security context with RBAC
            stats_filter: Filter for stats query
            
        Returns:
            DashboardStatsResult with organization statistics
            
        Raises:
            ValueError: If access validation fails
            Exception: If database query fails
        """
        try:
            # Validate access
            if not security_context.validate_access(stats_filter.organization_id):
                raise ValueError("Access denied: insufficient permissions for organization statistics")
            
            # Get organization filter with security context
            org_filter = security_context.get_org_filter()
            
            # Platform admins should use dedicated endpoints
            if security_context.platform_admin:
                raise ValueError("Platform admins should use platform-admin specific endpoints")
            
            # Calculate stats concurrently for performance
            stats_tasks = []
            
            if stats_filter.include_devices:
                stats_tasks.append(self._get_device_counts(org_filter))
            else:
                stats_tasks.append(asyncio.create_task(asyncio.coroutine(lambda: (0, 0))()))
            
            if stats_filter.include_users:
                stats_tasks.append(self._get_user_count(org_filter))
            else:
                stats_tasks.append(asyncio.create_task(asyncio.coroutine(lambda: 0)()))
            
            if stats_filter.include_activity:
                stats_tasks.append(self._get_data_points_today(org_filter))
            else:
                stats_tasks.append(asyncio.create_task(asyncio.coroutine(lambda: 0)()))
            
            # Execute all queries concurrently
            results = await asyncio.gather(*stats_tasks, return_exceptions=True)
            
            # Process results
            total_devices, active_devices = results[0] if not isinstance(results[0], Exception) else (0, 0)
            total_users = results[1] if not isinstance(results[1], Exception) else 0
            data_points_today = results[2] if not isinstance(results[2], Exception) else 0
            
            # Calculate organization count (1 for org-scoped, or actual count)
            total_organizations = 1 if org_filter else await self._get_organization_count()
            
            # Get alerts count (placeholder - can be extended)
            alerts = 0
            
            result = DashboardStatsResult(
                organization_id=stats_filter.organization_id,
                total_devices=total_devices,
                active_devices=active_devices,
                total_users=total_users,
                total_organizations=total_organizations,
                alerts=alerts,
                data_points_today=data_points_today,
                metadata={
                    'security_context': security_context.user_role,
                    'filter_applied': bool(org_filter),
                    'computed_fields': {
                        'devices': stats_filter.include_devices,
                        'users': stats_filter.include_users,
                        'activity': stats_filter.include_activity
                    }
                }
            )
            
            self.logger.info(
                f"Retrieved organization stats for org_id={stats_filter.organization_id}, "
                f"user_role={security_context.user_role}"
            )
            
            return result
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Error getting organization stats: {e}")
            raise Exception(f"Failed to retrieve organization statistics: {str(e)}")
    
    async def get_device_summary_stats(
        self,
        security_context: StatsSecurityContext,
        stats_filter: StatsFilter
    ) -> DeviceSummaryStats:
        """
        Get device summary statistics
        
        Args:
            security_context: Security context with RBAC
            stats_filter: Filter for stats query
            
        Returns:
            DeviceSummaryStats with device summary
        """
        try:
            # Validate access
            if not security_context.validate_access(stats_filter.organization_id):
                raise ValueError("Access denied: insufficient permissions for device statistics")
            
            org_filter = security_context.get_org_filter()
            
            # Get device statistics
            total_devices, active_devices = await self._get_device_counts(org_filter)
            
            # Get device status breakdown
            status_counts = await self._get_device_status_counts(org_filter)
            inactive_devices = status_counts.get('inactive', 0)
            offline_devices = status_counts.get('offline', 0)
            
            # Get devices by type
            devices_by_type = await self._get_devices_by_type(org_filter)
            
            # Calculate uptime and ingestion rate (placeholder - can be extended)
            avg_uptime = 98.5  # Placeholder
            data_ingestion_rate = 150.0  # Placeholder
            
            result = DeviceSummaryStats(
                organization_id=stats_filter.organization_id,
                total_devices=total_devices,
                active_devices=active_devices,
                inactive_devices=inactive_devices,
                offline_devices=offline_devices,
                devices_by_type=devices_by_type,
                avg_uptime=avg_uptime,
                data_ingestion_rate=data_ingestion_rate,
                time_period=stats_filter.time_period
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting device summary stats: {e}")
            raise Exception(f"Failed to retrieve device summary statistics: {str(e)}")
    
    async def get_dashboard_data(
        self,
        organization_id: str,
        data_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Any:
        """
        Retrieve dashboard data (implementation of IDashboardRepository)
        
        Args:
            organization_id: Organization identifier
            data_type: Type of data to retrieve
            filters: Optional data filters
            limit: Maximum records to return
            
        Returns:
            Data containing dashboard data
        """
        try:
            base_filter = {'organization_id': organization_id}
            if filters:
                base_filter.update(filters)
            
            if data_type == 'devices':
                return await self._get_devices_data(base_filter, limit)
            elif data_type == 'telemetry':
                return await self._get_telemetry_data(base_filter, limit)
            elif data_type == 'users':
                return await self._get_users_data(base_filter, limit)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            self.logger.error(f"Error retrieving dashboard data: {e}")
            raise
    
    async def cache_dashboard_result(
        self,
        organization_id: str,
        cache_key: str,
        data: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> bool:
        """
        Cache dashboard result for performance
        
        Args:
            organization_id: Organization identifier
            cache_key: Cache key for the data
            data: Data to cache
            ttl_seconds: Time to live in seconds
            
        Returns:
            Boolean indicating success
        """
        try:
            if not self.cache:
                return False
            
            # Add organization context to cached data
            cached_data = {
                'organization_id': organization_id,
                'data': data,
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': ttl_seconds
            }
            
            await self.cache.setex(cache_key, ttl_seconds, cached_data)
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to cache dashboard result: {e}")
            return False
    
    async def get_cached_result(
        self,
        organization_id: str,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached dashboard result
        
        Args:
            organization_id: Organization identifier
            cache_key: Cache key for the data
            
        Returns:
            Cached data or None if not found
        """
        try:
            if not self.cache:
                return None
            
            cached_data = await self.cache.get(cache_key)
            if not cached_data:
                return None
            
            # Verify organization context
            if cached_data.get('organization_id') != organization_id:
                self.logger.warning(f"Organization mismatch in cached data for key: {cache_key}")
                return None
            
            return cached_data.get('data')
            
        except Exception as e:
            self.logger.warning(f"Failed to retrieve cached result: {e}")
            return None
    
    # Private helper methods
    async def _get_device_counts(self, org_filter: Dict[str, Any]) -> tuple[int, int]:
        """Get total and active device counts"""
        try:
            if not self.db:
                return 0, 0
            
            total_devices = await self._execute_count_query('devices', org_filter)
            active_filter = {**org_filter, 'status': 'active'}
            active_devices = await self._execute_count_query('devices', active_filter)
            
            return total_devices, active_devices
            
        except Exception as e:
            self.logger.error(f"Error getting device counts: {e}")
            return 0, 0
    
    async def _get_user_count(self, org_filter: Dict[str, Any]) -> int:
        """Get user count"""
        try:
            if not self.db:
                return 0
            
            return await self._execute_count_query('users', org_filter)
            
        except Exception as e:
            self.logger.error(f"Error getting user count: {e}")
            return 0
    
    async def _get_data_points_today(self, org_filter: Dict[str, Any]) -> int:
        """Get data points count for today"""
        try:
            if not self.db:
                return 0
            
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            telemetry_filter = {
                **org_filter,
                'timestamp': {'$gte': today}
            }
            
            return await self._execute_count_query('telemetry', telemetry_filter)
            
        except Exception as e:
            self.logger.error(f"Error getting data points today: {e}")
            return 0
    
    async def _get_organization_count(self) -> int:
        """Get total organization count"""
        try:
            if not self.db:
                return 0
            
            return await self._execute_count_query('organizations', {})
            
        except Exception as e:
            self.logger.error(f"Error getting organization count: {e}")
            return 0
    
    async def _get_device_status_counts(self, org_filter: Dict[str, Any]) -> Dict[str, int]:
        """Get device counts by status"""
        try:
            if not self.db:
                return {}
            
            # This would ideally use aggregation pipeline
            # For now, return placeholder values
            return {
                'inactive': 5,
                'offline': 2
            }
            
        except Exception as e:
            self.logger.error(f"Error getting device status counts: {e}")
            return {}
    
    async def _get_devices_by_type(self, org_filter: Dict[str, Any]) -> Dict[str, int]:
        """Get device counts by type"""
        try:
            if not self.db:
                return {}
            
            # This would ideally use aggregation pipeline
            # For now, return placeholder values
            return {
                'sensor': 25,
                'gateway': 3,
                'actuator': 8
            }
            
        except Exception as e:
            self.logger.error(f"Error getting devices by type: {e}")
            return {}
    
    async def _execute_count_query(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        """Execute count query on collection"""
        try:
            collection_obj = getattr(self.db, collection, None)
            if not collection_obj:
                self.logger.warning(f"Collection '{collection}' not found")
                return 0
            
            # Handle both sync and async count operations
            if hasattr(collection_obj, 'count_documents'):
                if asyncio.iscoroutinefunction(collection_obj.count_documents):
                    return await collection_obj.count_documents(filter_dict)
                else:
                    return collection_obj.count_documents(filter_dict)
            else:
                return 0
                
        except PyMongoError as e:
            self.logger.error(f"MongoDB error in count query: {e}")
            return 0
        except Exception as e:
            self.logger.error(f"Error executing count query: {e}")
            return 0
    
    async def _get_devices_data(self, filters: Dict[str, Any], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Get devices data"""
        try:
            if not self.db or not hasattr(self.db, 'devices'):
                return []
            
            cursor = self.db.devices.find(filters)
            if limit:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Error getting devices data: {e}")
            return []
    
    async def _get_telemetry_data(self, filters: Dict[str, Any], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Get telemetry data"""
        try:
            if not self.db or not hasattr(self.db, 'telemetry'):
                return []
            
            cursor = self.db.telemetry.find(filters)
            if limit:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Error getting telemetry data: {e}")
            return []
    
    async def _get_users_data(self, filters: Dict[str, Any], limit: Optional[int]) -> List[Dict[str, Any]]:
        """Get users data"""
        try:
            if not self.db or not hasattr(self.db, 'users'):
                return []
            
            cursor = self.db.users.find(filters)
            if limit:
                cursor = cursor.limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            self.logger.error(f"Error getting users data: {e}")
            return []