# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Data Models
Purpose: Define data structures for dashboard module
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from enum import Enum

# Optional pandas and numpy imports
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class DashboardTimeRange(Enum):
    """Supported dashboard time ranges"""
    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    CUSTOM = "custom"


class AggregationLevel(Enum):
    """Data aggregation levels"""
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class TrendDirection(Enum):
    """Trend direction indicators"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OrganizationStats:
    """Organization-level statistics"""
    organization_id: str
    total_devices: int
    active_devices: int
    total_users: int
    active_users: int
    total_data_points: int
    data_ingestion_rate: float
    storage_usage_gb: float
    uptime_percentage: float
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceStats:
    """Device statistics summary"""
    device_id: str
    device_name: str
    device_type: str
    status: str
    last_seen: datetime
    data_points_count: int
    avg_latency_ms: float
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    device_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric data"""
    metric_name: str
    unit: str
    data_points: List[MetricPoint]
    aggregation_level: AggregationLevel
    time_range: Tuple[datetime, datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    metric: str
    direction: TrendDirection
    magnitude: float
    confidence: float
    start_value: float
    end_value: float
    percentage_change: float
    analysis_period: str
    significant: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsagePattern:
    """Usage pattern analysis"""
    pattern_type: str
    period: str
    peak_hours: List[int]
    peak_days: List[str]
    usage_distribution: Dict[str, float]
    seasonal_factors: Dict[str, float] = field(default_factory=dict)
    anomalies: List[datetime] = field(default_factory=list)


@dataclass
class Forecast:
    """Forecast data point"""
    timestamp: datetime
    predicted_value: float
    confidence_interval: Tuple[float, float]
    confidence_level: float
    model_used: str


@dataclass
class ForecastResult:
    """Forecasting analysis result"""
    metric: str
    forecasts: List[Forecast]
    model_performance: Dict[str, float]
    forecast_horizon: int
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthCheck:
    """Individual system health check"""
    component: str
    status: HealthStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    last_check: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealthSummary:
    """Overall system health summary"""
    organization_id: str
    overall_status: HealthStatus
    health_checks: List[SystemHealthCheck]
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RealTimeMetric:
    """Real-time metric data"""
    metric_name: str
    current_value: float
    previous_value: Optional[float] = None
    change_percentage: Optional[float] = None
    unit: str = ""
    status: HealthStatus = HealthStatus.HEALTHY
    threshold_breached: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class APIKeyUsage:
    """API key usage statistics"""
    api_key_id: str
    organization_id: str
    total_requests: int
    requests_per_hour: float
    last_used: datetime
    rate_limit_hits: int
    error_rate: float
    popular_endpoints: List[Dict[str, Any]] = field(default_factory=list)
    usage_pattern: Dict[str, int] = field(default_factory=dict)


@dataclass
class FeatureUsage:
    """Feature usage statistics"""
    feature_name: str
    usage_count: int
    unique_users: int
    avg_session_duration: float
    last_used: datetime
    adoption_rate: float
    user_segments: Dict[str, int] = field(default_factory=dict)


@dataclass
class SecurityAlert:
    """Security alert data"""
    alert_id: str
    organization_id: str
    severity: AlertSeverity
    alert_type: str
    description: str
    affected_resources: List[str]
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    mitigation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityStatus:
    """Security health status"""
    organization_id: str
    overall_score: int
    active_threats: int
    resolved_threats: int
    compliance_score: float
    last_scan: datetime
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GeographicPoint:
    """Geographic data point"""
    latitude: float
    longitude: float
    country: str
    region: str
    city: Optional[str] = None
    entity_count: int = 0
    entity_type: str = "device"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeographicDistribution:
    """Geographic distribution analysis"""
    organization_id: str
    entity_type: str
    total_entities: int
    geographic_points: List[GeographicPoint]
    top_countries: List[Dict[str, Any]]
    top_regions: List[Dict[str, Any]]
    coverage_percentage: float
    analysis_date: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MLInsight:
    """Machine learning insight"""
    insight_id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    impact_score: float
    data_sources: List[str]
    recommendations: List[str]
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlatformResource:
    """Platform resource information"""
    resource_type: str
    resource_name: str
    current_usage: float
    max_capacity: float
    utilization_percentage: float
    status: HealthStatus
    allocation_details: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PlatformOverview:
    """Platform-wide overview"""
    total_organizations: int
    total_devices: int
    total_users: int
    total_data_points: int
    system_resources: List[PlatformResource]
    overall_health: HealthStatus
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DashboardRequest:
    """Generic dashboard data request"""
    organization_id: str
    request_type: str
    parameters: Dict[str, Any]
    time_range: DashboardTimeRange
    aggregation: AggregationLevel
    filters: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=datetime.utcnow)
    priority: str = "normal"


@dataclass
class DashboardResponse:
    """Generic dashboard response"""
    request_id: str
    response_type: str
    data: Union[
        OrganizationStats,
        List[DeviceStats],
        MetricSeries,
        TrendAnalysis,
        ForecastResult,
        SystemHealthSummary,
        Dict[str, Any]
    ]
    execution_time_ms: float
    cached: bool = False
    cache_ttl: Optional[int] = None
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardCache:
    """Dashboard cache entry"""
    cache_key: str
    organization_id: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if cache entry is valid"""
        return not self.is_expired()


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    widget_id: str
    widget_type: str
    title: str
    data_source: str
    refresh_interval: int
    position: Dict[str, int]
    size: Dict[str, int]
    configuration: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)


@dataclass
class UserDashboard:
    """User dashboard configuration"""
    dashboard_id: str
    user_id: str
    organization_id: str
    name: str
    description: str
    widgets: List[DashboardWidget]
    layout: Dict[str, Any]
    is_default: bool = False
    shared: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TelemetrySnapshot:
    """Real-time telemetry snapshot"""
    organization_id: str
    device_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    device_status: str
    connection_quality: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_metric_value(self, metric_name: str) -> Optional[float]:
        """Get value for specific metric"""
        return self.metrics.get(metric_name)
    
    def add_metric(self, metric_name: str, value: float) -> None:
        """Add or update metric value"""
        self.metrics[metric_name] = value


# Dashboard Statistics Models
@dataclass
class DashboardStatsResult:
    """Dashboard statistics result"""
    organization_id: str
    total_devices: int
    active_devices: int
    total_users: int
    total_organizations: int
    alerts: int
    data_points_today: int
    computed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'totalDevices': self.total_devices,
            'activeDevices': self.active_devices,
            'totalUsers': self.total_users,
            'totalOrganizations': self.total_organizations,
            'alerts': self.alerts,
            'dataPointsToday': self.data_points_today,
            'computed_at': self.computed_at.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class DeviceSummaryStats:
    """Device summary statistics for time period"""
    organization_id: str
    total_devices: int
    active_devices: int
    inactive_devices: int
    offline_devices: int
    devices_by_type: Dict[str, int]
    avg_uptime: float
    data_ingestion_rate: float
    time_period: str
    computed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'organization_id': self.organization_id,
            'total_devices': self.total_devices,
            'active_devices': self.active_devices,
            'inactive_devices': self.inactive_devices,
            'offline_devices': self.offline_devices,
            'devices_by_type': self.devices_by_type,
            'avg_uptime': self.avg_uptime,
            'data_ingestion_rate': self.data_ingestion_rate,
            'time_period': self.time_period,
            'computed_at': self.computed_at.isoformat()
        }


@dataclass
class StatsFilter:
    """Filter for statistics queries"""
    organization_id: str
    include_devices: bool = True
    include_users: bool = True
    include_activity: bool = True
    device_types: Optional[List[str]] = None
    time_period: str = "7d"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    def to_db_filter(self) -> Dict[str, Any]:
        """Convert to database filter"""
        base_filter = {'organization_id': self.organization_id}
        
        if self.device_types:
            base_filter['device_type'] = {'$in': self.device_types}
        
        if self.start_date and self.end_date:
            base_filter['timestamp'] = {
                '$gte': self.start_date,
                '$lte': self.end_date
            }
        
        return base_filter


@dataclass
class StatsSecurityContext:
    """Security context for statistics access"""
    user_role: str
    organization_id: Optional[str] = None
    platform_admin: bool = False
    allowed_organizations: List[str] = field(default_factory=list)
    
    def validate_access(self, target_org_id: str) -> bool:
        """Validate access to organization statistics"""
        # Platform admins should use dedicated endpoints
        if self.platform_admin:
            return False
        
        # Check organization access
        if self.organization_id:
            return self.organization_id == target_org_id
        
        # Check allowed organizations list
        return target_org_id in self.allowed_organizations
    
    def get_org_filter(self) -> Dict[str, Any]:
        """Get organization filter for database queries"""
        if self.organization_id:
            return {'organization_id': self.organization_id}
        elif self.allowed_organizations:
            return {'organization_id': {'$in': self.allowed_organizations}}
        else:
            return {}


# Request Models for Bridge Pattern
@dataclass
class DashboardStatsRequest:
    """Request for dashboard statistics"""
    organization_id: str
    include_devices: bool = True
    include_users: bool = True
    include_activity: bool = True
    user_context: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate request parameters"""
        return bool(self.organization_id)


@dataclass
class DashboardAnalyticsRequest:
    """Request for dashboard analytics"""
    organization_id: str
    time_range: str = "24h"
    include_telemetry: bool = True
    include_devices: bool = True
    include_users: bool = True
    user_context: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Validate request parameters"""
        valid_ranges = ["1h", "6h", "24h", "7d", "30d", "90d"]
        return bool(self.organization_id) and self.time_range in valid_ranges


@dataclass
class RealtimeMetricsRequest:
    """Request for real-time metrics"""
    organization_id: str
    metric_types: Optional[List[str]] = None
    user_context: Optional[Dict[str, Any]] = None
    refresh_rate: int = 60  # seconds
    
    def validate(self) -> bool:
        """Validate request parameters"""
        return bool(self.organization_id) and self.refresh_rate > 0