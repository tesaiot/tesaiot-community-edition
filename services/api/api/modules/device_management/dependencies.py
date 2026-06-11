# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Management Dependencies
Version: v2026.01
Build: 2026-01-10

FastAPI dependency injection providers for Device Management module.
"""

from fastapi import HTTPException, status, Request, Path
import redis.asyncio as redis

from .models.device_models import Device, DeviceStatus, DeviceType
from api.core.database import get_redis, get_db


async def get_redis_client() -> redis.Redis:
    """Get async Redis client instance for dependency injection"""
    return get_redis()


async def get_current_device(
    device_id: str = Path(..., description="Device ID"),
    request: Request = None
) -> Device:
    """
    Get current device from database by device_id.

    This is a FastAPI dependency that extracts device information
    from the path parameter and database.
    """
    db = get_db()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )

    # Try to find device in database
    device_data = db.devices.find_one({"device_id": device_id})

    if not device_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # Convert to Device model
    try:
        device = Device(
            id=str(device_data.get('_id', '')),
            device_id=device_data.get('device_id', device_id),
            name=device_data.get('name', device_id),
            type=DeviceType(device_data.get('type', 'sensor')),
            status=DeviceStatus(device_data.get('status', 'unknown')),
            firmware_version=device_data.get('firmware_version'),
            hardware_version=device_data.get('hardware_version'),
            manufacturer=device_data.get('manufacturer'),
            model=device_data.get('model'),
            tags=device_data.get('tags', []),
            metadata=device_data.get('metadata', {}),
            created_at=device_data.get('created_at'),
            updated_at=device_data.get('updated_at'),
            last_seen_at=device_data.get('last_seen')
        )
        return device
    except Exception as e:
        # Return a minimal device if conversion fails
        return Device(
            id=str(device_data.get('_id', '')),
            device_id=device_id,
            name=device_data.get('name', device_id),
            type=DeviceType.SENSOR,
            status=DeviceStatus.UNKNOWN
        )


__all__ = ['get_redis_client', 'get_current_device']
