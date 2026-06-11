# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import uuid
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from redis import asyncio as aioredis  # Python 3.11+ compatible

from ..models.telemetry_models import (
    TelemetryData, TelemetryPoint, TelemetryBatch, TelemetryBuffer,
    TelemetryType, TelemetryPriority, DataQuality, AggregationType,
    TelemetryAlert, TelemetryIngestionStats
)
from ..models.audit_models import DeviceAuditAction
from ..models.event_streaming_models import EventType, EventPriority
from ..services.audit_logging_service import device_audit_service
from ..services.event_streaming_service import event_streaming_service
from api.services.notification_service import send_device_alert_notification
from ....core.database import get_db
from ...dashboard.utils.circuit_breaker import circuit_breaker
from ...dashboard.utils.metrics_decorator import track_dashboard_method

logger = logging.getLogger(__name__)


class TelemetryService:
    """High-performance telemetry service for IoT data ingestion and processing"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        mongodb_url: str = None,
        buffer_size: int = 1000,
        batch_size: int = 500,
        flush_interval_seconds: int = 10,
        max_workers: int = 4
    ):
        self.redis_url = redis_url
        self.mongodb_url = mongodb_url
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.max_workers = max_workers
        
        # In-memory buffers for each device
        self.device_buffers: Dict[str, TelemetryBuffer] = {}
        self.buffer_lock = asyncio.Lock()
        
        # Batch processing queue
        self.batch_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        # Thread pool for CPU-intensive operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Redis connection for real-time data
        self.redis: Optional[aioredis.Redis] = None
        
        # Statistics tracking
        self.stats = defaultdict(lambda: {
            "messages": 0,
            "data_points": 0,
            "errors": 0,
            "latency_sum": 0.0,
            "max_latency": 0.0
        })
        
        # Background tasks
        self.flush_task: Optional[asyncio.Task] = None
        self.batch_processor_task: Optional[asyncio.Task] = None
        
        logger.info(f"TelemetryService initialized with buffer_size={buffer_size}, batch_size={batch_size}")
    
    async def initialize(self):
        """Initialize connections and start background tasks"""
        try:
            # Initialize Redis connection
            self.redis = await aioredis.create_redis_pool(self.redis_url)
            
            # Start background tasks
            self.flush_task = asyncio.create_task(self._periodic_flush())
            self.batch_processor_task = asyncio.create_task(self._batch_processor())
            
            logger.info("TelemetryService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TelemetryService: {str(e)}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the service"""
        try:
            # Cancel background tasks
            if self.flush_task:
                self.flush_task.cancel()
            if self.batch_processor_task:
                self.batch_processor_task.cancel()
            
            # Flush all buffers
            await self._flush_all_buffers()
            
            # Close connections
            if self.redis:
                self.redis.close()
                await self.redis.wait_closed()
            
            # Shutdown executor
            self.executor.shutdown(wait=True)
            
            logger.info("TelemetryService shutdown complete")
        except Exception as e:
            logger.error(f"Error during TelemetryService shutdown: {str(e)}")
    
    @track_dashboard_method(
        method_name="telemetry_ingest",
        module="device_management",
        operation="create"
    )
    @circuit_breaker(failure_threshold=5, recovery_timeout=30, expected_exception=Exception)
    async def ingest_telemetry(
        self,
        device_id: str,
        org_id: str,
        telemetry_type: Union[str, TelemetryType],
        data_points: List[Dict[str, Any]],
        priority: Union[str, TelemetryPriority] = TelemetryPriority.NORMAL,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingest telemetry data from a device"""
        start_time = time.time()
        telemetry_id = str(uuid.uuid4())
        
        try:
            # Convert string enums if necessary
            if isinstance(telemetry_type, str):
                telemetry_type = TelemetryType(telemetry_type)
            if isinstance(priority, str):
                priority = TelemetryPriority(priority)
            
            # Create telemetry data object
            telemetry = TelemetryData(
                telemetry_id=telemetry_id,
                device_id=device_id,
                org_id=org_id,
                telemetry_type=telemetry_type,
                priority=priority,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            # Convert data points
            for dp in data_points:
                point = TelemetryPoint(
                    timestamp=dp.get("timestamp", datetime.utcnow()),
                    value=dp["value"],
                    unit=dp.get("unit"),
                    quality=DataQuality(dp.get("quality", "good")),
                    metadata=dp.get("metadata", {})
                )
                telemetry.data_points.append(point)
            
            # Update statistics
            self._update_stats(org_id, len(data_points), time.time() - start_time)
            
            # Handle based on priority
            if priority == TelemetryPriority.CRITICAL:
                # Process immediately for critical data
                await self._process_critical_telemetry(telemetry)
            else:
                # Buffer for batch processing
                await self._buffer_telemetry(telemetry)
            
            # Store real-time data in Redis for immediate access
            await self._store_realtime_data(device_id, org_id, telemetry)
            
            # Emit telemetry received event
            for point in telemetry.data_points:
                await event_streaming_service.emit_telemetry_event(
                    event_type=EventType.TELEMETRY_RECEIVED,
                    device_id=device_id,
                    organization_id=org_id,
                    telemetry_data=telemetry,
                    user_id=str(user.get('_id', user.get('id'))) if user else None,
                    priority=EventPriority.HIGH if priority == TelemetryPriority.CRITICAL else EventPriority.MEDIUM
                )
            
            # Audit log the ingestion
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DATA_ACCESSED,
                    user=user,
                    device_id=device_id,
                    details={
                        "telemetry_id": telemetry_id,
                        "type": telemetry_type.value,
                        "priority": priority.value,
                        "data_points": len(data_points),
                        "tags": tags
                    },
                    status="success",
                    operation_duration_ms=(time.time() - start_time) * 1000
                )
            
            return {
                "telemetry_id": telemetry_id,
                "status": "accepted",
                "data_points_received": len(data_points),
                "processing_time_ms": (time.time() - start_time) * 1000
            }
            
        except Exception as e:
            logger.error(f"Error ingesting telemetry for device {device_id}: {str(e)}")
            self.stats[org_id]["errors"] += 1
            
            # Audit log the failure
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DATA_ACCESSED,
                    user=user,
                    device_id=device_id,
                    details={
                        "type": telemetry_type.value if isinstance(telemetry_type, TelemetryType) else telemetry_type,
                        "data_points_attempted": len(data_points)
                    },
                    status="failure",
                    error_message=str(e)
                )
            
            raise
    
    async def _buffer_telemetry(self, telemetry: TelemetryData):
        """Buffer telemetry data for batch processing"""
        async with self.buffer_lock:
            buffer_key = f"{telemetry.org_id}:{telemetry.device_id}"
            
            # Get or create buffer for device
            if buffer_key not in self.device_buffers:
                self.device_buffers[buffer_key] = TelemetryBuffer(
                    buffer_id=str(uuid.uuid4()),
                    device_id=telemetry.device_id,
                    org_id=telemetry.org_id,
                    buffer_type="hybrid",
                    max_size=self.buffer_size,
                    max_age_seconds=self.flush_interval_seconds
                )
            
            buffer = self.device_buffers[buffer_key]
            
            # Add data points to buffer
            should_flush = False
            for point in telemetry.data_points:
                if buffer.add_point(point):
                    should_flush = True
            
            # Flush if needed
            if should_flush:
                await self._flush_buffer(buffer_key)
    
    async def _flush_buffer(self, buffer_key: str):
        """Flush a specific device buffer"""
        if buffer_key not in self.device_buffers:
            return
        
        buffer = self.device_buffers[buffer_key]
        if buffer.current_size == 0:
            return
        
        # Get data points and reset buffer
        data_points = buffer.flush()
        
        # Create batch for processing
        batch = TelemetryBatch(
            batch_id=str(uuid.uuid4()),
            org_id=buffer.org_id,
            device_ids=[buffer.device_id],
            telemetry_count=1,
            total_data_points=len(data_points),
            priority=TelemetryPriority.NORMAL
        )
        
        # Create telemetry data object
        telemetry = TelemetryData(
            telemetry_id=str(uuid.uuid4()),
            device_id=buffer.device_id,
            org_id=buffer.org_id,
            telemetry_type=TelemetryType.SENSOR_DATA,
            data_points=data_points
        )
        
        batch.add_telemetry(telemetry)
        
        # Add to processing queue
        try:
            await self.batch_queue.put(batch)
            logger.debug(f"Flushed buffer for {buffer_key}: {len(data_points)} points")
        except asyncio.QueueFull:
            logger.warning(f"Batch queue full, dropping batch for {buffer_key}")
    
    async def _flush_all_buffers(self):
        """Flush all device buffers"""
        async with self.buffer_lock:
            buffer_keys = list(self.device_buffers.keys())
            
        for buffer_key in buffer_keys:
            await self._flush_buffer(buffer_key)
    
    async def _periodic_flush(self):
        """Periodically flush buffers based on age"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval_seconds)
                await self._flush_all_buffers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {str(e)}")
    
    async def _batch_processor(self):
        """Process batches from the queue"""
        while True:
            try:
                # Get batch from queue
                batch = await self.batch_queue.get()
                
                # Process batch
                await self._process_batch(batch)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {str(e)}")
    
    async def _process_batch(self, batch: TelemetryBatch):
        """Process a batch of telemetry data"""
        try:
            batch.processing_started_at = datetime.utcnow()
            batch.status = "processing"
            
            # Process telemetry data in the batch
            for telemetry in batch.telemetry_data:
                # Store in time-series database (MongoDB or specialized DB)
                await self._store_telemetry(telemetry)
                
                # Update aggregations
                await self._update_aggregations(telemetry)
                
                # Check for alerts
                await self._check_alerts(telemetry)
            
            batch.processing_completed_at = datetime.utcnow()
            batch.status = "completed"
            
            logger.info(f"Processed batch {batch.batch_id}: {batch.telemetry_count} messages, {batch.total_data_points} points")
            
        except Exception as e:
            batch.status = "failed"
            batch.error_message = str(e)
            logger.error(f"Failed to process batch {batch.batch_id}: {str(e)}")
    
    async def _process_critical_telemetry(self, telemetry: TelemetryData):
        """Process critical telemetry immediately"""
        try:
            # Store immediately
            await self._store_telemetry(telemetry)
            
            # Check for critical alerts
            alerts = await self._check_alerts(telemetry)
            
            # Notify if critical alerts found
            for alert in alerts:
                if alert.severity == "critical":
                    await self._notify_critical_alert(alert)
            
            logger.info(f"Processed critical telemetry {telemetry.telemetry_id}")
            
        except Exception as e:
            logger.error(f"Failed to process critical telemetry: {str(e)}")
            raise
    
    async def _store_telemetry(self, telemetry: TelemetryData):
        """Store telemetry in database"""
        # This would integrate with MongoDB or a time-series database
        # For now, we'll store in Redis with TTL
        key = f"telemetry:{telemetry.org_id}:{telemetry.device_id}:{telemetry.telemetry_id}"
        ttl = 86400  # 24 hours
        
        if self.redis:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(telemetry.to_dict())
            )
    
    async def _store_realtime_data(self, device_id: str, org_id: str, telemetry: TelemetryData):
        """Store real-time data in Redis for immediate access"""
        if not self.redis:
            return
        
        # Store latest values for each metric
        for point in telemetry.data_points:
            if isinstance(point.value, (int, float)):
                # Store as sorted set for time-series queries
                key = f"realtime:{org_id}:{device_id}:metrics"
                score = point.timestamp.timestamp()
                member = json.dumps({
                    "value": point.value,
                    "unit": point.unit,
                    "quality": point.quality.value
                })
                
                await self.redis.zadd(key, score, member)
                
                # Keep only recent data (last hour)
                cutoff = (datetime.utcnow() - timedelta(hours=1)).timestamp()
                await self.redis.zremrangebyscore(key, 0, cutoff)
        
        # Update device last seen
        status_key = f"org:{org_id}:device:{device_id}:status"
        await self.redis.hset(status_key, "last_telemetry", datetime.utcnow().isoformat())
    
    async def _update_aggregations(self, telemetry: TelemetryData):
        """Update aggregated metrics"""
        # This would update various aggregations in the database
        # For example: hourly, daily, weekly aggregations
        pass
    
    async def _check_alerts(self, telemetry: TelemetryData) -> List[TelemetryAlert]:
        """Check telemetry data against alert rules"""
        alerts = []
        
        # This would check against configured alert rules
        # For now, we'll implement a simple threshold check
        for point in telemetry.data_points:
            if isinstance(point.value, (int, float)):
                # Example: Alert if temperature > 80
                if point.unit == "celsius" and point.value > 80:
                    alert = TelemetryAlert(
                        alert_id=str(uuid.uuid4()),
                        device_id=telemetry.device_id,
                        org_id=telemetry.org_id,
                        alert_type="high_temperature",
                        severity="high",
                        condition="temperature > 80",
                        threshold_value=80,
                        actual_value=point.value,
                        triggered_at=datetime.utcnow()
                    )
                    alerts.append(alert)
                    
                    # Emit threshold exceeded event
                    await event_streaming_service.emit_telemetry_event(
                        event_type=EventType.TELEMETRY_THRESHOLD_EXCEEDED,
                        device_id=telemetry.device_id,
                        organization_id=telemetry.org_id,
                        telemetry_data=telemetry,
                        threshold_name="high_temperature",
                        threshold_value=80,
                        priority=EventPriority.HIGH
                    )
        
        return alerts
    
    async def _notify_critical_alert(self, alert: TelemetryAlert):
        """Send notifications for critical alerts"""
        logger.warning(f"Critical alert: {alert.alert_type} for device {alert.device_id}")

        try:
            device_payload: Dict[str, Any] = {}
            db = get_db()
            if db is not None:
                device_doc = db.devices.find_one({'device_id': alert.device_id})
                if device_doc:
                    device_payload = dict(device_doc)

            if not device_payload:
                device_payload = {
                    'device_id': alert.device_id,
                    'name': alert.device_id,
                    'organization_id': alert.org_id,
                }
            else:
                device_payload.setdefault('device_id', alert.device_id)
                device_payload.setdefault('organization_id', alert.org_id)

            message = (
                f"{alert.alert_type.replace('_', ' ').title()} triggered. "
                f"Threshold: {alert.threshold_value}, actual: {alert.actual_value}"
            )

            send_device_alert_notification(
                device_payload,
                alert.alert_type,
                message,
                metadata={
                    'alert_id': alert.alert_id,
                    'severity': alert.severity,
                    'condition': alert.condition,
                    'threshold_value': alert.threshold_value,
                    'actual_value': alert.actual_value,
                    'triggered_at': alert.triggered_at.isoformat() if getattr(alert, 'triggered_at', None) else None,
                }
            )

        except Exception as exc:
            logger.error(f"Failed to emit device alert notification: {exc}")
    
    def _update_stats(self, org_id: str, data_points: int, latency: float):
        """Update ingestion statistics"""
        stats = self.stats[org_id]
        stats["messages"] += 1
        stats["data_points"] += data_points
        stats["latency_sum"] += latency
        stats["max_latency"] = max(stats["max_latency"], latency)
    
    async def get_ingestion_stats(self, org_id: str, period_minutes: int = 60) -> TelemetryIngestionStats:
        """Get telemetry ingestion statistics"""
        stats = self.stats.get(org_id, {})
        
        # Calculate averages
        avg_latency = 0.0
        if stats.get("messages", 0) > 0:
            avg_latency = (stats.get("latency_sum", 0) / stats["messages"]) * 1000
        
        return TelemetryIngestionStats(
            org_id=org_id,
            period_start=datetime.utcnow() - timedelta(minutes=period_minutes),
            period_end=datetime.utcnow(),
            total_messages=stats.get("messages", 0),
            total_data_points=stats.get("data_points", 0),
            successful_ingestions=stats.get("messages", 0) - stats.get("errors", 0),
            failed_ingestions=stats.get("errors", 0),
            average_latency_ms=avg_latency,
            peak_latency_ms=stats.get("max_latency", 0) * 1000,
            devices_reporting=len(self.device_buffers)
        )
    
    @track_dashboard_method(
        method_name="telemetry_query",
        module="device_management",
        operation="read"
    )
    async def query_telemetry(
        self,
        device_id: str,
        org_id: str,
        start_time: datetime,
        end_time: datetime,
        metrics: List[str] = None,
        aggregation: AggregationType = AggregationType.NONE,
        interval_minutes: int = None
    ) -> List[Dict[str, Any]]:
        """Query historical telemetry data"""
        if not self.redis:
            return []
        
        results = []
        
        # Query from Redis sorted sets
        key = f"realtime:{org_id}:{device_id}:metrics"
        start_score = start_time.timestamp()
        end_score = end_time.timestamp()
        
        # Get data points in time range
        data = await self.redis.zrangebyscore(
            key,
            start_score,
            end_score,
            withscores=True
        )
        
        # Parse and filter results
        for member, score in data:
            point_data = json.loads(member)
            timestamp = datetime.fromtimestamp(score)
            
            results.append({
                "timestamp": timestamp.isoformat(),
                "value": point_data["value"],
                "unit": point_data.get("unit"),
                "quality": point_data.get("quality", "good")
            })
        
        # Apply aggregation if requested
        if aggregation != AggregationType.NONE and interval_minutes:
            results = await self._aggregate_results(results, aggregation, interval_minutes)
        
        return results
    
    async def _aggregate_results(
        self,
        data_points: List[Dict[str, Any]],
        aggregation: AggregationType,
        interval_minutes: int
    ) -> List[Dict[str, Any]]:
        """Aggregate telemetry results"""
        if not data_points:
            return []
        
        # Group by time intervals
        intervals = defaultdict(list)
        
        for point in data_points:
            timestamp = datetime.fromisoformat(point["timestamp"])
            interval_key = timestamp.replace(
                minute=(timestamp.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0
            )
            intervals[interval_key].append(point["value"])
        
        # Apply aggregation
        results = []
        for interval, values in sorted(intervals.items()):
            if aggregation == AggregationType.AVERAGE:
                value = sum(values) / len(values)
            elif aggregation == AggregationType.SUM:
                value = sum(values)
            elif aggregation == AggregationType.MIN:
                value = min(values)
            elif aggregation == AggregationType.MAX:
                value = max(values)
            elif aggregation == AggregationType.COUNT:
                value = len(values)
            elif aggregation == AggregationType.FIRST:
                value = values[0]
            elif aggregation == AggregationType.LAST:
                value = values[-1]
            else:
                value = values[0]  # Default to first
            
            results.append({
                "timestamp": interval.isoformat(),
                "value": value,
                "aggregation": aggregation.value,
                "sample_count": len(values)
            })
        
        return results
    
    async def get_latest_telemetry(
        self,
        device_id: str,
        org_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get latest telemetry data for a device"""
        if not self.redis:
            return []
        
        key = f"realtime:{org_id}:{device_id}:metrics"
        
        # Get latest data points
        data = await self.redis.zrevrange(key, 0, limit - 1, withscores=True)
        
        results = []
        for member, score in data:
            point_data = json.loads(member)
            timestamp = datetime.fromtimestamp(score)
            
            results.append({
                "timestamp": timestamp.isoformat(),
                "value": point_data["value"],
                "unit": point_data.get("unit"),
                "quality": point_data.get("quality", "good")
            })
        
        return results


# Global telemetry service instance
telemetry_service = TelemetryService()
