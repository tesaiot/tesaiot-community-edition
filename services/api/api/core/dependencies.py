# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Core Dependencies
Version: v2026.01
Build: 2026-01-10

FastAPI dependency injection providers for core services.
Re-exports from database module for backward compatibility.
"""

from api.core.database import get_redis, get_redis_client, get_db

__all__ = ['get_redis', 'get_redis_client', 'get_db']
