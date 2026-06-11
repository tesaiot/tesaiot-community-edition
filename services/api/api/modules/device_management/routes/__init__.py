# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Routes (CE)

Aggregates the in-scope FastAPI routers for the Device Management module that
back the IoT Telemetry Dashboard inside Device Details. Out-of-scope routers
(advanced dashboards, monitoring, edge/zero-trust, licensing, OTA rollout) are
not included in the Community Edition.
"""

from fastapi import APIRouter

# Import in-scope routers only
from .telemetry_routes import router as telemetry_router
from .device_group_routes import router as device_group_router
from .template_routes import router as template_router

# Create main device management router
# Note: No prefix here because the mount point already includes /device-management
device_management_router = APIRouter(tags=["Device Management"])

# Include all in-scope sub-routers
device_management_router.include_router(telemetry_router)
device_management_router.include_router(device_group_router)
device_management_router.include_router(template_router)

__all__ = [
    "device_management_router",
    "telemetry_router",
    "device_group_router",
    "template_router",
]
