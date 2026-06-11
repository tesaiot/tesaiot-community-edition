# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Redis Client Wrapper
Version: v2026.01
Build: 2026-01-10

This module provides Redis client exports for backward compatibility
with Device Management module imports.
"""

from api.core.database import get_redis, get_redis_client

# Export redis_client as alias for get_redis()
redis_client = get_redis()

__all__ = ['redis_client', 'get_redis', 'get_redis_client']
