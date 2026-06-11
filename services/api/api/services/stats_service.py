# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Statistics Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
import asyncio
import random

from .base_service import BaseService


class StatsService(BaseService):
    """
    Service for handling all statistics-related operations.
    
    Provides:
    - Device statistics (total, active, inactive)
    - User statistics and activity metrics
    - Organization metrics
    - Telemetry statistics
    - System health metrics
    - Cached aggregations for performance
    """
    
    async def validate_permissions(
        self, 
        user_role: str, 
        org_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: str = 'read'
    ) -> bool:
        """
        Validate user permissions for statistics access.
        
        All authenticated users can view stats for their organization.
        Platform admins can view global stats.
        """
        if action != 'read':
            # Stats are read-only
            return False
            
        # Platform admins have full read access
        if user_role == 'platform_admin':
            return True
            
        # Other authenticated users can read their org's stats
        return user_role in ['admin', 'user', 'super_admin']
    
    @BaseService.timing_decorator
    async def get_dashboard_stats(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics.
        
        Args:
            org_id: Organization ID for filtering (None for platform-wide stats)
            
        Returns:
            Dictionary containing all dashboard statistics
        """
        cache_key = f"dashboard:stats:{org_id or 'global'}"
        
        async def compute():
            # Run all stat queries in parallel for performance
            results = await asyncio.gather(
                self.get_device_stats(org_id),
                self.get_user_stats(org_id),
                self.get_organization_stats(org_id),
                self.get_telemetry_summary(org_id),
                self.get_system_health_metrics(org_id),
                return_exceptions=True
            )
            
            # Handle any errors in individual queries
            stats = {}
            stat_types = ['devices', 'users', 'organizations', 'telemetry', 'system_health']
            
            for i, (stat_type, result) in enumerate(zip(stat_types, results)):
                if isinstance(result, Exception):
                    self.logger.error(f"Error getting {stat_type} stats: {result}")
                    stats[stat_type] = self._get_default_stats(stat_type)
                else:
                    stats[stat_type] = result
                    
            # Add metadata
            stats['metadata'] = {
                'generated_at': datetime.utcnow().isoformat(),
                'scope': 'organization' if org_id else 'platform',
                'organization_id': org_id
            }
            
            # Ensure all numeric values are properly sanitized
            return self.sanitize_response_data(stats)
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    @BaseService.timing_decorator
    async def get_device_stats(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get device statistics with caching.
        
        Args:
            org_id: Organization ID for filtering
            
        Returns:
            Device statistics including counts and health metrics
        """
        cache_key = f"devices:{org_id or 'all'}"
        
        async def compute():
            if self.db is None:
                return self._get_default_stats('devices')
                
            try:
                # Build organization filter
                org_filter = {'organization_id': org_id} if org_id else {}
                
                # Get total devices
                total_devices = await self.db.devices.count_documents(org_filter)
                
                # Get active devices
                active_filter = {**org_filter, 'status': 'active'}
                active_devices = await self.db.devices.count_documents(active_filter)
                
                # Get inactive devices
                inactive_devices = total_devices - active_devices
                
                # Get devices by type
                device_types = await self.db.devices.aggregate([
                    {'$match': org_filter},
                    {'$group': {
                        '_id': '$type',
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 5}
                ]).to_list(length=5)
                
                # Calculate health percentage
                health_percentage = (active_devices / total_devices * 100) if total_devices > 0 else 0
                
                return {
                    'total_devices': total_devices,
                    'active_devices': active_devices,
                    'inactive_devices': inactive_devices,
                    'health_percentage': self.sanitize_numeric_value(health_percentage, 0),
                    'device_types': [
                        {'type': dt['_id'], 'count': dt['count']} 
                        for dt in device_types
                    ],
                    'recent_additions': await self._get_recent_device_additions(org_filter)
                }
                
            except Exception as e:
                self.logger.error(f"Error computing device stats: {e}")
                return self._get_default_stats('devices')
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    @BaseService.timing_decorator
    async def get_user_stats(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user statistics and activity metrics.
        
        Args:
            org_id: Organization ID for filtering
            
        Returns:
            User statistics including activity and engagement metrics
        """
        cache_key = f"users:{org_id or 'all'}"
        
        async def compute():
            if self.db is None:
                return self._get_default_stats('users')
                
            try:
                org_filter = {'organization_id': org_id} if org_id else {}
                
                # Get total users
                total_users = await self.db.users.count_documents(org_filter)
                
                # Get active users (last 7 days)
                week_ago = datetime.utcnow() - timedelta(days=7)
                active_week_filter = {
                    **org_filter,
                    'last_login': {'$gte': week_ago}
                }
                active_users_week = await self.db.users.count_documents(active_week_filter)
                
                # Get active users (last 30 days)
                month_ago = datetime.utcnow() - timedelta(days=30)
                active_month_filter = {
                    **org_filter,
                    'last_login': {'$gte': month_ago}
                }
                active_users_month = await self.db.users.count_documents(active_month_filter)
                
                # Get users by role
                user_roles = await self.db.users.aggregate([
                    {'$match': org_filter},
                    {'$group': {
                        '_id': '$role',
                        'count': {'$sum': 1}
                    }}
                ]).to_list(length=10)
                
                # Calculate engagement rate
                engagement_rate = (active_users_week / total_users * 100) if total_users > 0 else 0
                
                return {
                    'total_users': total_users,
                    'active_users_week': active_users_week,
                    'active_users_month': active_users_month,
                    'engagement_rate': self.sanitize_numeric_value(engagement_rate, 0),
                    'user_roles': [
                        {'role': ur['_id'], 'count': ur['count']} 
                        for ur in user_roles
                    ],
                    'new_users_today': await self._get_new_users_count(org_filter, days=1),
                    'new_users_week': await self._get_new_users_count(org_filter, days=7)
                }
                
            except Exception as e:
                self.logger.error(f"Error computing user stats: {e}")
                return self._get_default_stats('users')
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=300)
    
    @BaseService.timing_decorator
    async def get_organization_stats(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get organization statistics.
        
        Args:
            org_id: Organization ID for specific org stats
            
        Returns:
            Organization statistics and metrics
        """
        cache_key = f"organizations:{org_id or 'all'}"
        
        async def compute():
            if self.db is None:
                return self._get_default_stats('organizations')
                
            try:
                if org_id:
                    # Get specific organization stats
                    org = await self.db.organizations.find_one({'_id': ObjectId(org_id)})
                    if not org:
                        return self._get_default_stats('organizations')
                        
                    return {
                        'organization_name': org.get('name', 'Unknown'),
                        'subscription_type': org.get('subscription_type', 'free'),
                        'created_at': org.get('created_at', datetime.utcnow()).isoformat(),
                        'device_limit': org.get('device_limit', 10),
                        'user_limit': org.get('user_limit', 5),
                        'api_rate_limit': org.get('api_rate_limit', 1000),
                        'storage_used_gb': self.sanitize_numeric_value(
                            org.get('storage_used_gb', 0), 0
                        ),
                        'storage_limit_gb': org.get('storage_limit_gb', 10),
                        'features_enabled': org.get('features_enabled', [])
                    }
                else:
                    # Get platform-wide organization stats
                    total_orgs = await self.db.organizations.count_documents({})
                    
                    # Get organizations by subscription type
                    org_types = await self.db.organizations.aggregate([
                        {'$group': {
                            '_id': '$subscription_type',
                            'count': {'$sum': 1}
                        }}
                    ]).to_list(length=10)
                    
                    return {
                        'total_organizations': total_orgs,
                        'subscription_breakdown': [
                            {'type': ot['_id'], 'count': ot['count']} 
                            for ot in org_types
                        ],
                        'new_organizations_week': await self._get_new_orgs_count(days=7),
                        'new_organizations_month': await self._get_new_orgs_count(days=30)
                    }
                    
            except Exception as e:
                self.logger.error(f"Error computing organization stats: {e}")
                return self._get_default_stats('organizations')
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=600)
    
    @BaseService.timing_decorator
    async def get_telemetry_summary(
        self, 
        org_id: Optional[str] = None, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get telemetry statistics for the specified period.
        
        Args:
            org_id: Organization ID for filtering
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Telemetry summary including message counts and processing metrics
        """
        cache_key = f"telemetry:{org_id or 'all'}:{hours}h"
        
        async def compute():
            if self.db is None:
                return self._get_default_stats('telemetry')
                
            try:
                since = datetime.utcnow() - timedelta(hours=hours)
                
                # Build filter
                telemetry_filter = {'timestamp': {'$gte': since}}
                if org_id:
                    # Need to join with devices to filter by org
                    device_ids = await self.db.devices.find(
                        {'organization_id': org_id},
                        {'_id': 1}
                    ).to_list(length=None)
                    device_ids = [d['_id'] for d in device_ids]
                    telemetry_filter['device_id'] = {'$in': device_ids}
                
                # Get message counts
                total_messages = await self.db.telemetry.count_documents(telemetry_filter)
                
                # Get unique devices
                unique_devices = len(await self.db.telemetry.distinct(
                    'device_id', telemetry_filter
                ))
                
                # Get message types breakdown
                message_types = await self.db.telemetry.aggregate([
                    {'$match': telemetry_filter},
                    {'$group': {
                        '_id': '$type',
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 5}
                ]).to_list(length=5)
                
                # Calculate rates
                message_rate = total_messages / hours if hours > 0 else 0
                
                return {
                    'total_messages': total_messages,
                    'unique_devices': unique_devices,
                    'message_rate_per_hour': self.sanitize_numeric_value(message_rate, 0),
                    'period_hours': hours,
                    'message_types': [
                        {'type': mt['_id'], 'count': mt['count']} 
                        for mt in message_types
                    ],
                    'peak_hour': await self._get_peak_telemetry_hour(telemetry_filter)
                }
                
            except Exception as e:
                self.logger.error(f"Error computing telemetry stats: {e}")
                return self._get_default_stats('telemetry')
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=60)
    
    @BaseService.timing_decorator
    async def get_system_health_metrics(self, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get system health and performance metrics.
        
        Returns:
            System health metrics including API performance and resource usage
        """
        cache_key = f"system_health:{org_id or 'all'}"
        
        async def compute():
            # For now, return simulated metrics
            # In production, these would come from monitoring systems
            return {
                'api_health': {
                    'status': 'healthy',
                    'uptime_percentage': 99.95,
                    'response_time_ms': self.sanitize_numeric_value(random.uniform(20, 50), 35),
                    'error_rate': self.sanitize_numeric_value(random.uniform(0.01, 0.1), 0.05)
                },
                'database_health': {
                    'status': 'healthy',
                    'connection_pool_usage': self.sanitize_numeric_value(random.uniform(10, 30), 20),
                    'query_performance_ms': self.sanitize_numeric_value(random.uniform(5, 15), 10)
                },
                'cache_health': {
                    'status': 'healthy',
                    'hit_rate': self.sanitize_numeric_value(random.uniform(85, 95), 90),
                    'memory_usage_mb': self.sanitize_numeric_value(random.uniform(100, 500), 300)
                },
                'last_updated': datetime.utcnow().isoformat()
            }
        
        return await self.get_cached_or_compute(cache_key, compute, ttl=30)
    
    # Helper methods
    
    async def _get_recent_device_additions(
        self, 
        org_filter: Dict[str, Any], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recently added devices."""
        try:
            recent_devices = await self.db.devices.find(
                org_filter,
                {'name': 1, 'type': 1, 'created_at': 1}
            ).sort('created_at', -1).limit(limit).to_list(length=limit)
            
            return [
                {
                    'id': str(d['_id']),
                    'name': d.get('name', 'Unknown'),
                    'type': d.get('type', 'Unknown'),
                    'added_at': d.get('created_at', datetime.utcnow()).isoformat()
                }
                for d in recent_devices
            ]
        except Exception:
            return []
    
    async def _get_new_users_count(
        self, 
        org_filter: Dict[str, Any], 
        days: int
    ) -> int:
        """Get count of new users in the specified period."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            filter_with_date = {
                **org_filter,
                'created_at': {'$gte': since}
            }
            return await self.db.users.count_documents(filter_with_date)
        except Exception:
            return 0
    
    async def _get_new_orgs_count(self, days: int) -> int:
        """Get count of new organizations in the specified period."""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            return await self.db.organizations.count_documents({
                'created_at': {'$gte': since}
            })
        except Exception:
            return 0
    
    async def _get_peak_telemetry_hour(self, telemetry_filter: Dict[str, Any]) -> str:
        """Get the hour with peak telemetry traffic."""
        try:
            peak_hour = await self.db.telemetry.aggregate([
                {'$match': telemetry_filter},
                {'$group': {
                    '_id': {'$hour': '$timestamp'},
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': 1}
            ]).to_list(length=1)
            
            if peak_hour:
                hour = peak_hour[0]['_id']
                return f"{hour:02d}:00-{hour:02d}:59"
            return "N/A"
        except Exception:
            return "N/A"
    
    def _get_default_stats(self, stat_type: str) -> Dict[str, Any]:
        """Get default stats structure when database is unavailable."""
        defaults = {
            'devices': {
                'total_devices': 0,
                'active_devices': 0,
                'inactive_devices': 0,
                'health_percentage': 0,
                'device_types': [],
                'recent_additions': []
            },
            'users': {
                'total_users': 0,
                'active_users_week': 0,
                'active_users_month': 0,
                'engagement_rate': 0,
                'user_roles': [],
                'new_users_today': 0,
                'new_users_week': 0
            },
            'organizations': {
                'total_organizations': 0,
                'subscription_breakdown': [],
                'new_organizations_week': 0,
                'new_organizations_month': 0
            },
            'telemetry': {
                'total_messages': 0,
                'unique_devices': 0,
                'message_rate_per_hour': 0,
                'period_hours': 24,
                'message_types': [],
                'peak_hour': 'N/A'
            },
            'system_health': {
                'api_health': {'status': 'unknown'},
                'database_health': {'status': 'unknown'},
                'cache_health': {'status': 'unknown'},
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
        return defaults.get(stat_type, {})