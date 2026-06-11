# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Services Module
Purpose: Export dashboard service implementations
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1-3
"""

from .dashboard_utilities import DashboardUtilitiesService
from .dashboard_stats_service import ModularDashboardStatsService, create_dashboard_stats_service
from .dashboard_analytics_service import DashboardAnalyticsService

# System monitoring (psutil), predictive analytics (numpy/sklearn/prophet) and the
# associated ML cache-warming services are out of scope for the Community Edition.

__all__ = [
    "DashboardUtilitiesService",
    "ModularDashboardStatsService",
    "create_dashboard_stats_service",
    "DashboardAnalyticsService",
]