# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Module Interfaces
Purpose: Define contracts for dashboard services
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .models.dashboard_models import DashboardStatsRequest, DashboardAnalyticsRequest

# Optional pandas import
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False


class IDashboardStatsService(ABC):
    """Dashboard statistics service interface"""
    
    @abstractmethod
    async def get_organization_stats(
        self,
        organization_id: str,
        include_devices: bool = True,
        include_users: bool = True,
        include_activity: bool = True
    ) -> Dict[str, Any]:
        """
        Get comprehensive organization statistics
        
        Args:
            organization_id: Organization identifier
            include_devices: Include device statistics
            include_users: Include user statistics  
            include_activity: Include activity statistics
            
        Returns:
            Dict containing organization statistics
        """
        pass
    
    @abstractmethod
    async def get_device_summary_stats(
        self,
        organization_id: str,
        time_period: str = "7d",
        device_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get device summary statistics
        
        Args:
            organization_id: Organization identifier
            time_period: Time period for statistics
            device_types: Optional device type filter
            
        Returns:
            Dict containing device statistics
        """
        pass


class IDashboardAnalyticsService(ABC):
    """Dashboard analytics service interface"""
    
    @abstractmethod
    async def get_metrics_analytics(
        self,
        organization_id: str,
        metrics: List[str],
        start_date: datetime,
        end_date: datetime,
        aggregation: str = "hourly"
    ) -> Dict[str, Any]:
        """
        Get metrics analytics for dashboard
        
        Args:
            organization_id: Organization identifier
            metrics: List of metrics to analyze
            start_date: Start of analysis period
            end_date: End of analysis period
            aggregation: Data aggregation level
            
        Returns:
            Dict containing metrics analytics
        """
        pass
    
    @abstractmethod
    async def get_trend_analysis(
        self,
        organization_id: str,
        metric: str,
        time_window: int = 30,
        trend_type: str = "linear"
    ) -> Dict[str, Any]:
        """
        Analyze trends in dashboard metrics
        
        Args:
            organization_id: Organization identifier
            metric: Metric to analyze
            time_window: Time window in days
            trend_type: Type of trend analysis
            
        Returns:
            Dict containing trend analysis
        """
        pass


class IMonitoringDashboardService(ABC):
    """Real-time monitoring dashboard service interface"""
    
    @abstractmethod
    async def get_system_health_status(
        self,
        organization_id: str,
        components: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get real-time system health status
        
        Args:
            organization_id: Organization identifier
            components: Optional component filter
            
        Returns:
            Dict containing system health status
        """
        pass
    
    @abstractmethod
    async def get_real_time_metrics(
        self,
        organization_id: str,
        metric_types: List[str],
        time_window: int = 300
    ) -> Dict[str, Any]:
        """
        Get real-time metrics for monitoring dashboard
        
        Args:
            organization_id: Organization identifier
            metric_types: Types of metrics to retrieve
            time_window: Time window in seconds
            
        Returns:
            Dict containing real-time metrics
        """
        pass


class IUsageAnalyticsService(ABC):
    """Usage analytics service interface"""
    
    @abstractmethod
    async def get_usage_patterns(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
        pattern_type: str = "daily"
    ) -> Dict[str, Any]:
        """
        Analyze usage patterns
        
        Args:
            organization_id: Organization identifier
            start_date: Start of analysis period
            end_date: End of analysis period
            pattern_type: Type of pattern analysis
            
        Returns:
            Dict containing usage patterns
        """
        pass
    
    @abstractmethod
    async def get_feature_usage_stats(
        self,
        organization_id: str,
        features: Optional[List[str]] = None,
        time_period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get feature usage statistics
        
        Args:
            organization_id: Organization identifier
            features: Optional feature filter
            time_period: Time period for analysis
            
        Returns:
            Dict containing feature usage stats
        """
        pass


class IAPIKeyAnalyticsService(ABC):
    """API key analytics service interface"""
    
    @abstractmethod
    async def get_api_key_usage(
        self,
        organization_id: str,
        api_key_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get API key usage analytics
        
        Args:
            organization_id: Organization identifier
            api_key_id: Optional API key filter
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Dict containing API key usage data
        """
        pass
    
    @abstractmethod
    async def get_rate_limit_analytics(
        self,
        organization_id: str,
        time_window: int = 3600
    ) -> Dict[str, Any]:
        """
        Get rate limiting analytics
        
        Args:
            organization_id: Organization identifier
            time_window: Time window in seconds
            
        Returns:
            Dict containing rate limit analytics
        """
        pass


class IUsageTrendsService(ABC):
    """Usage trends service interface"""
    
    @abstractmethod
    async def analyze_historical_trends(
        self,
        organization_id: str,
        metrics: List[str],
        time_range: Tuple[datetime, datetime],
        trend_period: str = "weekly"
    ) -> Dict[str, Any]:
        """
        Analyze historical usage trends
        
        Args:
            organization_id: Organization identifier
            metrics: Metrics to analyze trends for
            time_range: Time range for analysis
            trend_period: Period for trend calculation
            
        Returns:
            Dict containing trend analysis
        """
        pass
    
    @abstractmethod
    async def detect_usage_anomalies(
        self,
        organization_id: str,
        baseline_days: int = 30,
        sensitivity: float = 0.05
    ) -> Dict[str, Any]:
        """
        Detect anomalies in usage patterns
        
        Args:
            organization_id: Organization identifier
            baseline_days: Days to use for baseline
            sensitivity: Anomaly detection sensitivity
            
        Returns:
            Dict containing detected anomalies
        """
        pass


class ISystemHealthService(ABC):
    """System health service interface"""
    
    @abstractmethod
    async def get_infrastructure_health(
        self,
        organization_id: str,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Get infrastructure health status
        
        Args:
            organization_id: Organization identifier
            include_dependencies: Include dependency health
            
        Returns:
            Dict containing infrastructure health
        """
        pass
    
    @abstractmethod
    async def perform_health_checks(
        self,
        organization_id: str,
        check_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive health checks
        
        Args:
            organization_id: Organization identifier
            check_types: Optional check type filter
            
        Returns:
            Dict containing health check results
        """
        pass


class IRealtimeIoTMetricsService(ABC):
    """Real-time IoT metrics service interface"""
    
    @abstractmethod
    async def get_live_telemetry(
        self,
        organization_id: str,
        device_ids: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        time_window: int = 60
    ) -> Dict[str, Any]:
        """
        Get live telemetry data
        
        Args:
            organization_id: Organization identifier
            device_ids: Optional device filter
            metrics: Optional metric filter
            time_window: Time window in seconds
            
        Returns:
            Dict containing live telemetry
        """
        pass
    
    @abstractmethod
    async def get_aggregated_metrics(
        self,
        organization_id: str,
        aggregation_level: str = "device",
        time_period: str = "1h"
    ) -> Dict[str, Any]:
        """
        Get aggregated IoT metrics
        
        Args:
            organization_id: Organization identifier
            aggregation_level: Level of aggregation
            time_period: Time period for aggregation
            
        Returns:
            Dict containing aggregated metrics
        """
        pass


class ISecurityHealthService(ABC):
    """Security health service interface"""
    
    @abstractmethod
    async def get_security_status(
        self,
        organization_id: str,
        include_threats: bool = True,
        include_compliance: bool = True
    ) -> Dict[str, Any]:
        """
        Get security health status
        
        Args:
            organization_id: Organization identifier
            include_threats: Include threat assessment
            include_compliance: Include compliance status
            
        Returns:
            Dict containing security status
        """
        pass
    
    @abstractmethod
    async def scan_security_vulnerabilities(
        self,
        organization_id: str,
        scan_scope: List[str],
        severity_threshold: str = "medium"
    ) -> Dict[str, Any]:
        """
        Scan for security vulnerabilities
        
        Args:
            organization_id: Organization identifier
            scan_scope: Scope of security scan
            severity_threshold: Minimum severity level
            
        Returns:
            Dict containing vulnerability scan results
        """
        pass


class IPlatformAdminService(ABC):
    """Platform administration service interface"""
    
    @abstractmethod
    async def get_platform_overview(
        self,
        admin_level: str = "organization",
        include_performance: bool = True
    ) -> Dict[str, Any]:
        """
        Get platform-wide overview
        
        Args:
            admin_level: Level of admin access
            include_performance: Include performance metrics
            
        Returns:
            Dict containing platform overview
        """
        pass
    
    @abstractmethod
    async def manage_resource_allocation(
        self,
        organization_id: str,
        resource_type: str,
        allocation_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Manage platform resource allocation
        
        Args:
            organization_id: Organization identifier
            resource_type: Type of resource to manage
            allocation_changes: Changes to make
            
        Returns:
            Dict containing allocation results
        """
        pass


class IGeographicAnalyticsService(ABC):
    """Geographic analytics service interface"""
    
    @abstractmethod
    async def get_geographic_distribution(
        self,
        organization_id: str,
        entity_type: str = "devices",
        aggregation_level: str = "country"
    ) -> Dict[str, Any]:
        """
        Get geographic distribution analytics
        
        Args:
            organization_id: Organization identifier
            entity_type: Type of entity to analyze
            aggregation_level: Geographic aggregation level
            
        Returns:
            Dict containing geographic distribution
        """
        pass
    
    @abstractmethod
    async def analyze_location_patterns(
        self,
        organization_id: str,
        pattern_type: str = "usage",
        time_period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Analyze location-based patterns
        
        Args:
            organization_id: Organization identifier
            pattern_type: Type of pattern to analyze
            time_period: Time period for analysis
            
        Returns:
            Dict containing location pattern analysis
        """
        pass


class IDashboardUtilitiesService(ABC):
    """Dashboard utilities service interface"""
    
    @abstractmethod
    def get_services(self) -> Dict[str, Any]:
        """
        Initialize and return modularized services
        
        Returns:
            Dict containing initialized services
        """
        pass
    
    @abstractmethod
    def sanitize_numeric_value(
        self,
        value: Union[int, float, str, None],
        fallback: Union[int, float] = 0
    ) -> Union[int, float]:
        """
        Sanitize numeric values to prevent NaN/Infinity in JSON responses
        
        Args:
            value: Value to sanitize
            fallback: Fallback value if sanitization fails
            
        Returns:
            Sanitized numeric value
        """
        pass
    
    @abstractmethod
    def sanitize_response_data(self, data: Any) -> Any:
        """
        Recursively sanitize response data to prevent chart errors
        
        Args:
            data: Data to sanitize (dict, list, or primitive)
            
        Returns:
            Sanitized data structure
        """
        pass
    
    @abstractmethod
    def validate_dashboard_request(
        self,
        request_data: Dict[str, Any],
        required_fields: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate dashboard request data
        
        Args:
            request_data: Request data to validate
            required_fields: Required field names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    def format_time_series_data(
        self,
        data: Any,  # Changed from pd.DataFrame to Any for flexibility
        time_column: str = 'timestamp',
        value_columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Format time series data for dashboard charts
        
        Args:
            data: Raw time series data
            time_column: Name of timestamp column
            value_columns: Columns to include in output
            
        Returns:
            Formatted data for chart rendering
        """
        pass


class IDashboardRepository(ABC):
    """Dashboard data repository interface"""
    
    @abstractmethod
    async def get_dashboard_data(
        self,
        organization_id: str,
        data_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> Any:  # Changed from pd.DataFrame to Any for flexibility
        """
        Retrieve dashboard data
        
        Args:
            organization_id: Organization identifier
            data_type: Type of data to retrieve
            filters: Optional data filters
            limit: Maximum records to return
            
        Returns:
            Data containing dashboard data (DataFrame if pandas available, otherwise dict/list)
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass


# Unified Dashboard Service Interface for Bridge Pattern
class IDashboardService(ABC):
    """
    Unified dashboard service interface for bridge pattern integration.
    Combines all dashboard functionality in a single interface.
    """
    
    @abstractmethod
    async def get_organization_stats(
        self,
        request: 'DashboardStatsRequest'
    ) -> Dict[str, Any]:
        """
        Get organization statistics
        
        Args:
            request: Dashboard statistics request
            
        Returns:
            Dict containing organization statistics
        """
        pass
    
    @abstractmethod
    async def get_analytics_data(
        self,
        request: 'DashboardAnalyticsRequest'
    ) -> Dict[str, Any]:
        """
        Get dashboard analytics data
        
        Args:
            request: Dashboard analytics request
            
        Returns:
            Dict containing analytics data
        """
        pass
    
    @abstractmethod
    async def get_realtime_metrics(
        self,
        organization_id: str,
        metric_types: Optional[List[str]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get real-time metrics
        
        Args:
            organization_id: Organization identifier
            metric_types: Types of metrics to retrieve
            user_context: User context for authorization
            
        Returns:
            Dict containing real-time metrics
        """
        pass