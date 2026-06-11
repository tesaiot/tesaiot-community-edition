# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from ..services.telemetry_service import telemetry_service
from ..models.telemetry_models import TelemetryPriority, AggregationType
from ....auth.dependencies import get_current_user
from ....auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/ingest/{device_id}")
async def ingest_telemetry(
    device_id: str,
    data: Dict[str, Any] = Body(...),
    priority: str = Query(default="normal", description="Telemetry priority: critical, high, normal, low"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Ingest telemetry data from a device
    
    Request body should contain:
    - telemetry_type: Type of telemetry (sensor_data, metrics, status_update, etc.)
    - data_points: List of data points with timestamp, value, unit, quality
    - tags: Optional list of tags
    - metadata: Optional metadata dictionary
    """
    try:
        # Validate request data
        if "telemetry_type" not in data:
            raise HTTPException(status_code=400, detail="telemetry_type is required")
        if "data_points" not in data:
            raise HTTPException(status_code=400, detail="data_points is required")
        
        # Convert string priority to enum
        try:
            priority_enum = TelemetryPriority(priority)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid priority: {priority}")
        
        # Ingest telemetry
        result = await telemetry_service.ingest_telemetry(
            device_id=device_id,
            org_id=current_user.org_id,
            telemetry_type=data["telemetry_type"],
            data_points=data["data_points"],
            priority=priority_enum,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            user=current_user.dict()
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting telemetry for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/ingest")
async def batch_ingest_telemetry(
    data: List[Dict[str, Any]] = Body(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Batch ingest telemetry data from multiple devices
    
    Request body should be a list of telemetry objects, each containing:
    - device_id: Device identifier
    - telemetry_type: Type of telemetry
    - data_points: List of data points
    - priority: Optional priority (default: normal)
    - tags: Optional list of tags
    - metadata: Optional metadata
    """
    try:
        results = {
            "total": len(data),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for telemetry_data in data:
            try:
                # Validate required fields
                if "device_id" not in telemetry_data:
                    raise ValueError("device_id is required")
                if "telemetry_type" not in telemetry_data:
                    raise ValueError("telemetry_type is required")
                if "data_points" not in telemetry_data:
                    raise ValueError("data_points is required")
                
                # Ingest telemetry
                await telemetry_service.ingest_telemetry(
                    device_id=telemetry_data["device_id"],
                    org_id=current_user.org_id,
                    telemetry_type=telemetry_data["telemetry_type"],
                    data_points=telemetry_data["data_points"],
                    priority=telemetry_data.get("priority", "normal"),
                    tags=telemetry_data.get("tags", []),
                    metadata=telemetry_data.get("metadata", {}),
                    user=current_user.dict()
                )
                
                results["successful"] += 1
                
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "device_id": telemetry_data.get("device_id", "unknown"),
                    "error": str(e)
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error in batch telemetry ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/query/{device_id}")
async def query_telemetry(
    device_id: str,
    start_time: datetime = Query(..., description="Start time for query"),
    end_time: datetime = Query(..., description="End time for query"),
    metrics: Optional[List[str]] = Query(default=None, description="Specific metrics to query"),
    aggregation: str = Query(default="none", description="Aggregation type: none, average, sum, min, max, count"),
    interval_minutes: Optional[int] = Query(default=None, description="Aggregation interval in minutes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Query historical telemetry data for a device"""
    try:
        # Validate time range
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time")
        
        # Validate aggregation
        try:
            aggregation_enum = AggregationType(aggregation)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid aggregation type: {aggregation}")
        
        # Query telemetry
        data = await telemetry_service.query_telemetry(
            device_id=device_id,
            org_id=current_user.org_id,
            start_time=start_time,
            end_time=end_time,
            metrics=metrics,
            aggregation=aggregation_enum,
            interval_minutes=interval_minutes
        )
        
        return {
            "device_id": device_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "data_points": data,
            "count": len(data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying telemetry for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{device_id}")
async def get_latest_telemetry(
    device_id: str,
    limit: int = Query(default=10, ge=1, le=100, description="Number of latest data points to retrieve"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get latest telemetry data for a device"""
    try:
        data = await telemetry_service.get_latest_telemetry(
            device_id=device_id,
            org_id=current_user.org_id,
            limit=limit
        )
        
        return {
            "device_id": device_id,
            "data_points": data,
            "count": len(data)
        }
        
    except Exception as e:
        logger.error(f"Error getting latest telemetry for device {device_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ingestion_stats(
    period_minutes: int = Query(default=60, ge=1, le=1440, description="Statistics period in minutes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get telemetry ingestion statistics for the organization"""
    try:
        stats = await telemetry_service.get_ingestion_stats(
            org_id=current_user.org_id,
            period_minutes=period_minutes
        )

        return stats.to_dict()

    except Exception as e:
        logger.error(f"Error getting ingestion stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/availability/summary")
async def get_devices_availability_summary(
    device_ids: Optional[str] = Query(default=None, description="Comma-separated device IDs (optional, returns all devices in org if not provided)"),
    device_names: Optional[str] = Query(default=None, description="Comma-separated device names for fallback matching"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get telemetry data availability summary for multiple devices in one call.
    Returns first/last dates, total days, and data point count for each device.

    This endpoint is optimized for Edge AI Telemetry Dashboard to pre-fetch
    device availability data without making N parallel API calls.

    Note: TimescaleDB may store device_id differently than MongoDB. This endpoint
    supports both device_ids and device_names to handle ID mismatch scenarios.
    """
    try:
        from ....core.database import get_postgres

        conn = get_postgres()
        if not conn:
            # Fall back to empty response if TimescaleDB not available
            return {
                "devices": {},
                "total_devices": 0,
                "has_data_devices": 0,
                "source": "unavailable"
            }

        # Parse device IDs and names if provided
        device_id_list = None
        device_name_list = None
        if device_ids:
            device_id_list = [d.strip() for d in device_ids.split(',') if d.strip()]
        if device_names:
            device_name_list = [n.strip() for n in device_names.split(',') if n.strip()]

        # Combine all possible identifiers for query
        all_identifiers = []
        if device_id_list:
            all_identifiers.extend(device_id_list)
        if device_name_list:
            all_identifiers.extend(device_name_list)
        # Remove duplicates while preserving order
        all_identifiers = list(dict.fromkeys(all_identifiers))

        results = {}

        with conn.cursor() as cursor:
            # Query BOTH telemetry_generic AND device_telemetry tables
            # Some devices store data in telemetry_generic, others in device_telemetry
            # Use UNION ALL to combine results from both tables
            if all_identifiers:
                # Query specific devices by ID or name from BOTH tables
                cursor.execute("""
                    SELECT
                        device_id::text as device_id,
                        MIN(first_ts) as first_timestamp,
                        MAX(last_ts) as last_timestamp,
                        SUM(point_count) as data_point_count,
                        SUM(day_count) as unique_days
                    FROM (
                        -- Query telemetry_generic table
                        SELECT
                            device_id::text as device_id,
                            MIN(time) as first_ts,
                            MAX(time) as last_ts,
                            COUNT(*) as point_count,
                            COUNT(DISTINCT DATE(time)) as day_count
                        FROM telemetry_generic
                        WHERE device_id::text = ANY(%s)
                        GROUP BY device_id

                        UNION ALL

                        -- Query device_telemetry table
                        SELECT
                            device_id::text as device_id,
                            MIN(time) as first_ts,
                            MAX(time) as last_ts,
                            COUNT(*) as point_count,
                            COUNT(DISTINCT DATE(time)) as day_count
                        FROM device_telemetry
                        WHERE device_id = ANY(%s)
                        GROUP BY device_id
                    ) combined
                    GROUP BY device_id
                """, (all_identifiers, all_identifiers))
            else:
                # Query all devices from BOTH tables (limit to prevent huge results)
                cursor.execute("""
                    SELECT
                        device_id,
                        MIN(first_ts) as first_timestamp,
                        MAX(last_ts) as last_timestamp,
                        SUM(point_count) as data_point_count,
                        SUM(day_count) as unique_days
                    FROM (
                        -- Query telemetry_generic table
                        SELECT
                            device_id::text as device_id,
                            MIN(time) as first_ts,
                            MAX(time) as last_ts,
                            COUNT(*) as point_count,
                            COUNT(DISTINCT DATE(time)) as day_count
                        FROM telemetry_generic
                        GROUP BY device_id

                        UNION ALL

                        -- Query device_telemetry table
                        SELECT
                            device_id::text as device_id,
                            MIN(time) as first_ts,
                            MAX(time) as last_ts,
                            COUNT(*) as point_count,
                            COUNT(DISTINCT DATE(time)) as day_count
                        FROM device_telemetry
                        GROUP BY device_id
                    ) combined
                    GROUP BY device_id
                    ORDER BY MAX(last_ts) DESC
                    LIMIT 100
                """)

            rows = cursor.fetchall()

            for row in rows:
                device_id, first_ts, last_ts, count, unique_days = row

                # Calculate total days span
                if first_ts and last_ts:
                    total_days = (last_ts.date() - first_ts.date()).days + 1
                else:
                    total_days = 0

                results[device_id] = {
                    "has_data": count > 0,
                    "first_date": first_ts.strftime('%Y-%m-%d') if first_ts else None,
                    "last_date": last_ts.strftime('%Y-%m-%d') if last_ts else None,
                    "first_timestamp": first_ts.isoformat() if first_ts else None,
                    "last_timestamp": last_ts.isoformat() if last_ts else None,
                    "total_days": total_days,
                    "unique_days": unique_days,
                    "data_point_count": count
                }

        # Add devices from the request that have no data
        if device_id_list:
            for device_id in device_id_list:
                if device_id not in results:
                    results[device_id] = {
                        "has_data": False,
                        "first_date": None,
                        "last_date": None,
                        "first_timestamp": None,
                        "last_timestamp": None,
                        "total_days": 0,
                        "unique_days": 0,
                        "data_point_count": 0
                    }

        has_data_count = sum(1 for d in results.values() if d["has_data"])

        return {
            "devices": results,
            "total_devices": len(results),
            "has_data_devices": has_data_count,
            "source": "timescaledb"
        }

    except Exception as e:
        logger.error(f"Error getting device availability summary: {str(e)}")
        # Return empty result instead of error to not break UI
        return {
            "devices": {},
            "total_devices": 0,
            "has_data_devices": 0,
            "source": "error",
            "error": str(e)
        }


@router.get("/health")
async def telemetry_health_check() -> Dict[str, Any]:
    """Check telemetry service health"""
    try:
        # Check if service is initialized
        if not telemetry_service.redis:
            return {
                "status": "unhealthy",
                "message": "Telemetry service not initialized"
            }
        
        # Check Redis connection
        await telemetry_service.redis.ping()
        
        # Get buffer status
        buffer_count = len(telemetry_service.device_buffers)
        queue_size = telemetry_service.batch_queue.qsize()
        
        return {
            "status": "healthy",
            "active_buffers": buffer_count,
            "queue_size": queue_size,
            "max_queue_size": telemetry_service.batch_queue.maxsize
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }


# WebSocket endpoint for real-time telemetry streaming
from fastapi import WebSocket, WebSocketDisconnect
import json

@router.websocket("/stream/{device_id}")
async def telemetry_stream(
    websocket: WebSocket,
    device_id: str,
    token: str = Query(..., description="Authentication token")
):
    """WebSocket endpoint for real-time telemetry streaming"""
    await websocket.accept()
    
    try:
        # TODO: Validate token and get user
        # For now, we'll use a placeholder org_id
        org_id = "default_org"
        
        # Subscribe to device telemetry updates
        pubsub = telemetry_service.redis.pubsub()
        channel = f"telemetry:{org_id}:{device_id}"
        await pubsub.subscribe(channel)
        
        # Send current status
        latest_data = await telemetry_service.get_latest_telemetry(device_id, org_id, limit=1)
        if latest_data:
            await websocket.send_json({
                "type": "current",
                "data": latest_data[0]
            })
        
        # Stream updates
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json({
                    "type": "update",
                    "data": data
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for device {device_id}")
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id}: {str(e)}")
        await websocket.close(code=1000)
    finally:
        if pubsub:
            await pubsub.unsubscribe(channel)
            await pubsub.close()


# Alias for backwards compatibility with Flask blueprint naming
telemetry_bp = router