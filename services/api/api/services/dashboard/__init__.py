# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Service Module

Modular services for dashboard controller:
- DashboardStatsService: Statistics and analytics endpoints
"""

from .dashboard_stats_service import DashboardStatsService

__all__ = ['DashboardStatsService']
