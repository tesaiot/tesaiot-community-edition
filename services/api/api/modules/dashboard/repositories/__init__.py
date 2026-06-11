# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dashboard Repositories Module
Purpose: Export dashboard repository implementations
Date: July 26, 2025
Part of TESA IoT Platform Safe Modularization Initiative - Week 03 Day 1-2
"""

from .dashboard_stats_repository import DashboardStatsRepository

__all__ = [
    "DashboardStatsRepository",
]