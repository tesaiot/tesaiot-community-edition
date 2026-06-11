# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Module
Purpose: Main dashboard module for TESA IoT Platform
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1

This module provides dashboard services and interfaces following the proven
patterns established in the Analytics module during Week 02.
"""

from .interfaces import (
    # Service Interfaces
    IDashboardStatsService,
    IDashboardAnalyticsService,
    IMonitoringDashboardService,
    IUsageAnalyticsService,
    IAPIKeyAnalyticsService,
    IUsageTrendsService,
    ISystemHealthService,
    IRealtimeIoTMetricsService,
    ISecurityHealthService,
    IPlatformAdminService,
    IGeographicAnalyticsService,
    IDashboardUtilitiesService,
    IDashboardRepository,
)

from .models import (
    # Enums
    DashboardTimeRange,
    AggregationLevel,
    HealthStatus,
    TrendDirection,
    AlertSeverity,
    
    # Core Data Models
    OrganizationStats,
    DeviceStats,
    MetricPoint,
    MetricSeries,
    TrendAnalysis,
    UsagePattern,
    Forecast,
    ForecastResult,
    
    # Health and Monitoring
    SystemHealthCheck,
    SystemHealthSummary,
    RealTimeMetric,
    
    # Usage Analytics
    APIKeyUsage,
    FeatureUsage,
    
    # Security
    SecurityAlert,
    SecurityStatus,
    
    # Geographic
    GeographicPoint,
    GeographicDistribution,
    
    # AI/ML
    MLInsight,
    
    # Platform
    PlatformResource,
    PlatformOverview,
    
    # Request/Response
    DashboardRequest,
    DashboardResponse,
    DashboardCache,
    
    # UI/UX
    DashboardWidget,
    UserDashboard,
    
    # Real-time
    TelemetrySnapshot,
)

# Module metadata
__version__ = "v2025.08"
__author__ = "TESA IoT Platform Team"
__description__ = "Dashboard module for comprehensive IoT platform analytics and monitoring"

# Service implementations (in-scope subset)
from .services import DashboardUtilitiesService, ModularDashboardStatsService, DashboardAnalyticsService

# Aliases for easier imports
DashboardStatsService = ModularDashboardStatsService

# Repository implementations will be imported here as they are created  
# from .repositories import ...

# Utility functions will be imported here as they are created
# from .utils import ...

__all__ = [
    # Interfaces
    "IDashboardStatsService",
    "IDashboardAnalyticsService",
    "IMonitoringDashboardService",
    "IUsageAnalyticsService",
    "IAPIKeyAnalyticsService",
    "IUsageTrendsService",
    "ISystemHealthService",
    "IRealtimeIoTMetricsService",
    "ISecurityHealthService",
    "IPlatformAdminService",
    "IGeographicAnalyticsService",
    "IDashboardUtilitiesService",
    "IDashboardRepository",
    
    # Services
    "DashboardUtilitiesService",
    "DashboardStatsService",
    "DashboardAnalyticsService",

    # Enums
    "DashboardTimeRange",
    "AggregationLevel",
    "HealthStatus", 
    "TrendDirection",
    "AlertSeverity",
    
    # Core Data Models
    "OrganizationStats",
    "DeviceStats",
    "MetricPoint",
    "MetricSeries",
    "TrendAnalysis",
    "UsagePattern",
    "Forecast",
    "ForecastResult",
    
    # Health and Monitoring
    "SystemHealthCheck",
    "SystemHealthSummary",
    "RealTimeMetric",
    
    # Usage Analytics
    "APIKeyUsage",
    "FeatureUsage",
    
    # Security
    "SecurityAlert",
    "SecurityStatus",
    
    # Geographic
    "GeographicPoint",
    "GeographicDistribution",
    
    # AI/ML
    "MLInsight",
    
    # Platform
    "PlatformResource",
    "PlatformOverview",
    
    # Request/Response
    "DashboardRequest",
    "DashboardResponse",
    "DashboardCache",
    
    # UI/UX
    "DashboardWidget",
    "UserDashboard",
    
    # Real-time
    "TelemetrySnapshot",
]


def get_module_info() -> dict:
    """
    Get dashboard module information
    
    Returns:
        Dict containing module metadata
    """
    return {
        "name": "dashboard",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "services_count": 14,
        "interfaces_count": 14,
        "models_count": len([name for name in __all__ if not name.startswith('I')]),
        "created_date": "2025-07-26",
        "week": "Week 03 Day 1",
        "based_on": "Analytics module patterns from Week 02"
    }