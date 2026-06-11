# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESAIoT Community Edition - Device Management Module

Provides the FastAPI device-management sub-application that is mounted by the
Flask app factory at /api/v1/device-management. It backs the IoT Telemetry
Dashboard inside Device Details. The heavyweight initialization helpers from the
full platform (connection-pool warmup, bulk-operations workers, OTA rollout)
are intentionally omitted from the Community Edition; the FastAPI services
initialize lazily on first use.
"""

import logging

logger = logging.getLogger(__name__)

__all__ = []
