# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Event Streaming Service
Generates and manages real-time events from device operations

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

from ..models.event_streaming_models import (
    EventPayload, DeviceEventPayload, TelemetryEventPayload,
    CommandEventPayload, SecurityEventPayload, EventType,
    EventPriority, EventCategory, StreamConfiguration,
    EventStreamStats
)
from ..models.device_models import Device
from ..models.telemetry_models import TelemetryData
from ..models.audit_models import DeviceAuditAction
from ..services.websocket_service import websocket_service
from ..services.audit_logging_service import device_audit_service
from ..repositories.device_repository import DeviceRepository
from ..repositories.telemetry_repository import TelemetryRepository
from ....core.database import get_db
from ....core.redis import redis_client

logger = logging.getLogger(__name__)


class EventStreamingService:
    """Service for generating and streaming real-time device events"""
    
    def __init__(
        self,
        redis_channel_prefix: str = "device_events",
        event_retention_hours: int = 24,
        stats_update_interval: int = 60,
        rate_limit_window_seconds: int = 60,
        max_events_per_window: int = 1000
    ):
        self.redis_channel_prefix = redis_channel_prefix
        self.event_retention_hours = event_retention_hours
        self.stats_update_interval = stats_update_interval
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.max_events_per_window = max_events_per_window
        
        # Repositories
        self.device_repository = DeviceRepository()
        self.telemetry_repository = TelemetryRepository()
        
        # Stream configurations
        self.stream_configs: Dict[str, StreamConfiguration] = {}
        
        # Event statistics
        self.stream_stats: Dict[str, EventStreamStats] = {}
        
        # Rate limiting
        self.event_counts: Dict[str, deque] = defaultdict(lambda: deque())
        
        # Event handlers
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # Background tasks
        self.stats_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Database
        self.db = get_db()
        
        logger.info("EventStreamingService initialized")
    
    async def initialize(self):
        """Initialize the service and start background tasks"""
        # Load stream configurations from database
        await self._load_stream_configurations()
        
        # Start background tasks
        self.stats_task = asyncio.create_task(self._update_statistics())
        self.cleanup_task = asyncio.create_task(self._cleanup_old_events())
        
        # Subscribe to Redis channels for distributed events
        if redis_client:
            asyncio.create_task(self._redis_event_listener())
        
        logger.info("EventStreamingService initialized")
    
    async def shutdown(self):
        """Shutdown the service"""
        # Cancel background tasks
        if self.stats_task:
            self.stats_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        logger.info("EventStreamingService shut down")
    
    async def emit_device_event(
        self,
        event_type: EventType,
        device: Device,
        user_id: Optional[str] = None,
        priority: EventPriority = EventPriority.MEDIUM,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Emit a device-related event"""
        try:
            # Check rate limit
            if not self._check_rate_limit(device.org_id):
                logger.warning(f"Rate limit exceeded for organization {device.org_id}")
                return ""
            
            # Create event payload
            event = DeviceEventPayload(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                organization_id=device.org_id,
                device_id=device.device_id,
                device_name=device.name,
                device_type=device.device_type.value,
                device_status=device.status.value,
                group_ids=device.group_ids,
                user_id=user_id,
                priority=priority,
                category=self._get_event_category(event_type),
                data=data or {},
                metadata=metadata or {}
            )
            
            # Process event
            await self._process_event(event)
            
            return event.event_id
        
        except Exception as e:
            logger.error(f"Error emitting device event: {e}")
            return ""
    
    async def emit_telemetry_event(
        self,
        event_type: EventType,
        device_id: str,
        organization_id: str,
        telemetry_data: TelemetryData,
        threshold_name: Optional[str] = None,
        threshold_value: Optional[float] = None,
        anomaly_score: Optional[float] = None,
        user_id: Optional[str] = None,
        priority: EventPriority = EventPriority.MEDIUM
    ) -> str:
        """Emit a telemetry-related event"""
        try:
            # Check rate limit
            if not self._check_rate_limit(organization_id):
                logger.warning(f"Rate limit exceeded for organization {organization_id}")
                return ""
            
            # Create event payload
            event = TelemetryEventPayload(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                organization_id=organization_id,
                device_id=device_id,
                telemetry_type=telemetry_data.telemetry_type,
                value=telemetry_data.value,
                unit=telemetry_data.unit,
                quality=telemetry_data.quality,
                threshold_name=threshold_name,
                threshold_value=threshold_value,
                anomaly_score=anomaly_score,
                user_id=user_id,
                priority=priority,
                category=EventCategory.TELEMETRY,
                data={
                    "timestamp": telemetry_data.timestamp.isoformat(),
                    "metadata": telemetry_data.metadata
                }
            )
            
            # Process event
            await self._process_event(event)
            
            return event.event_id
        
        except Exception as e:
            logger.error(f"Error emitting telemetry event: {e}")
            return ""
    
    async def emit_command_event(
        self,
        event_type: EventType,
        device_id: str,
        organization_id: str,
        command_id: str,
        command_type: str,
        command_status: str,
        response_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None,
        user_id: Optional[str] = None,
        priority: EventPriority = EventPriority.MEDIUM
    ) -> str:
        """Emit a command-related event"""
        try:
            # Check rate limit
            if not self._check_rate_limit(organization_id):
                logger.warning(f"Rate limit exceeded for organization {organization_id}")
                return ""
            
            # Create event payload
            event = CommandEventPayload(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                organization_id=organization_id,
                device_id=device_id,
                command_id=command_id,
                command_type=command_type,
                command_status=command_status,
                response_data=response_data,
                error_message=error_message,
                duration_ms=duration_ms,
                user_id=user_id,
                priority=priority,
                category=EventCategory.COMMAND
            )
            
            # Process event
            await self._process_event(event)
            
            return event.event_id
        
        except Exception as e:
            logger.error(f"Error emitting command event: {e}")
            return ""
    
    async def emit_security_event(
        self,
        event_type: EventType,
        organization_id: str,
        action: str,
        device_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        certificate_id: Optional[str] = None,
        violation_type: Optional[str] = None,
        risk_score: Optional[float] = None,
        priority: EventPriority = EventPriority.HIGH
    ) -> str:
        """Emit a security-related event"""
        try:
            # Check rate limit
            if not self._check_rate_limit(organization_id):
                logger.warning(f"Rate limit exceeded for organization {organization_id}")
                return ""
            
            # Create event payload
            event = SecurityEventPayload(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                timestamp=datetime.utcnow(),
                organization_id=organization_id,
                device_id=device_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent,
                certificate_id=certificate_id,
                violation_type=violation_type,
                risk_score=risk_score,
                user_id=user_id,
                priority=priority,
                category=EventCategory.SECURITY
            )
            
            # Process event
            await self._process_event(event)
            
            return event.event_id
        
        except Exception as e:
            logger.error(f"Error emitting security event: {e}")
            return ""
    
    async def create_stream_configuration(
        self,
        name: str,
        organization_id: str,
        description: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        categories: Optional[List[EventCategory]] = None,
        priorities: Optional[List[EventPriority]] = None,
        device_ids: Optional[List[str]] = None,
        group_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        rate_limit_per_minute: Optional[int] = None,
        retention_hours: int = 24
    ) -> StreamConfiguration:
        """Create a new stream configuration"""
        try:
            # Create configuration
            config = StreamConfiguration(
                stream_id=str(uuid.uuid4()),
                organization_id=organization_id,
                name=name,
                description=description,
                event_types=event_types or [],
                categories=categories or [],
                priorities=priorities or [],
                device_ids=device_ids or [],
                group_ids=group_ids or [],
                filters=filters or {},
                rate_limit_per_minute=rate_limit_per_minute,
                retention_hours=retention_hours
            )
            
            # Save to database
            if self.db:
                collection = self.db.event_stream_configs
                await collection.insert_one(config.__dict__)
            
            # Cache configuration
            self.stream_configs[config.stream_id] = config
            
            # Initialize statistics
            self.stream_stats[config.stream_id] = EventStreamStats(stream_id=config.stream_id)
            
            logger.info(f"Created stream configuration {config.stream_id}")
            return config
        
        except Exception as e:
            logger.error(f"Error creating stream configuration: {e}")
            raise
    
    async def update_stream_configuration(
        self,
        stream_id: str,
        updates: Dict[str, Any]
    ) -> Optional[StreamConfiguration]:
        """Update an existing stream configuration"""
        try:
            if stream_id not in self.stream_configs:
                return None
            
            config = self.stream_configs[stream_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            
            # Update in database
            if self.db:
                collection = self.db.event_stream_configs
                await collection.update_one(
                    {"stream_id": stream_id},
                    {"$set": updates}
                )
            
            logger.info(f"Updated stream configuration {stream_id}")
            return config
        
        except Exception as e:
            logger.error(f"Error updating stream configuration: {e}")
            return None
    
    async def delete_stream_configuration(self, stream_id: str) -> bool:
        """Delete a stream configuration"""
        try:
            if stream_id not in self.stream_configs:
                return False
            
            # Remove from cache
            del self.stream_configs[stream_id]
            
            # Remove statistics
            if stream_id in self.stream_stats:
                del self.stream_stats[stream_id]
            
            # Remove from database
            if self.db:
                collection = self.db.event_stream_configs
                await collection.delete_one({"stream_id": stream_id})
            
            logger.info(f"Deleted stream configuration {stream_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting stream configuration: {e}")
            return False
    
    def register_event_handler(self, event_type: EventType, handler: Callable):
        """Register a custom event handler"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    def unregister_event_handler(self, event_type: EventType, handler: Callable):
        """Unregister a custom event handler"""
        if handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            logger.info(f"Unregistered handler for {event_type.value}")
    
    async def _process_event(self, event: EventPayload):
        """Process an event through all channels"""
        try:
            # Update statistics
            await self._update_event_stats(event)
            
            # Store event in database
            await self._store_event(event)
            
            # Publish to WebSocket clients
            await websocket_service.publish_event(event)
            
            # Publish to Redis for distributed processing
            if redis_client:
                await self._publish_to_redis(event)
            
            # Call custom handlers
            await self._call_event_handlers(event)
            
            # Check stream configurations
            await self._process_stream_configs(event)
            
            # Log high-priority events
            if event.priority in [EventPriority.HIGH, EventPriority.CRITICAL]:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_EVENT_STREAMED,
                    user={"_id": event.user_id, "organization_id": event.organization_id},
                    device_id=event.device_id,
                    details={
                        "event_type": event.event_type.value,
                        "priority": event.priority.value,
                        "event_id": event.event_id
                    }
                )
        
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    async def _store_event(self, event: EventPayload):
        """Store event in database"""
        try:
            if self.db:
                collection = self.db.device_events
                
                # Convert event to dict
                event_dict = event.to_dict()
                event_dict["_id"] = event.event_id
                event_dict["expires_at"] = datetime.utcnow() + timedelta(hours=self.event_retention_hours)
                
                # Insert event
                await collection.insert_one(event_dict)
        
        except Exception as e:
            logger.error(f"Error storing event: {e}")
    
    async def _publish_to_redis(self, event: EventPayload):
        """Publish event to Redis for distributed processing"""
        try:
            channel = f"{self.redis_channel_prefix}:{event.organization_id}"
            await redis_client.publish(channel, event.to_json())
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")
    
    async def _call_event_handlers(self, event: EventPayload):
        """Call registered event handlers"""
        handlers = self.event_handlers.get(event.event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    async def _process_stream_configs(self, event: EventPayload):
        """Process event against stream configurations"""
        for config in self.stream_configs.values():
            if config.matches_event(event):
                # Update stream statistics
                stats = self.stream_stats.get(config.stream_id)
                if stats:
                    stats.total_events += 1
                    stats.events_per_type[event.event_type.value] = \
                        stats.events_per_type.get(event.event_type.value, 0) + 1
                    stats.last_event_at = datetime.utcnow()
    
    async def _update_event_stats(self, event: EventPayload):
        """Update event statistics"""
        for stats in self.stream_stats.values():
            stats.total_events += 1
            stats.events_per_type[event.event_type.value] = \
                stats.events_per_type.get(event.event_type.value, 0) + 1
            stats.events_per_category[event.category.value] = \
                stats.events_per_category.get(event.category.value, 0) + 1
            stats.events_per_priority[event.priority.value] = \
                stats.events_per_priority.get(event.priority.value, 0) + 1
            
            if event.device_id:
                stats.events_per_device[event.device_id] = \
                    stats.events_per_device.get(event.device_id, 0) + 1
            
            stats.last_event_at = datetime.utcnow()
    
    def _check_rate_limit(self, organization_id: str) -> bool:
        """Check if organization has exceeded rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.rate_limit_window_seconds)
        
        # Clean old timestamps
        events = self.event_counts[organization_id]
        while events and events[0] < window_start:
            events.popleft()
        
        # Check limit
        if len(events) >= self.max_events_per_window:
            return False
        
        # Add current timestamp
        events.append(now)
        return True
    
    def _get_event_category(self, event_type: EventType) -> EventCategory:
        """Get category for an event type"""
        category_map = {
            EventType.DEVICE_CREATED: EventCategory.LIFECYCLE,
            EventType.DEVICE_UPDATED: EventCategory.LIFECYCLE,
            EventType.DEVICE_DELETED: EventCategory.LIFECYCLE,
            EventType.DEVICE_STATUS_CHANGED: EventCategory.LIFECYCLE,
            EventType.DEVICE_CONNECTED: EventCategory.CONNECTIVITY,
            EventType.DEVICE_DISCONNECTED: EventCategory.CONNECTIVITY,
            EventType.DEVICE_HEARTBEAT: EventCategory.CONNECTIVITY,
            EventType.TELEMETRY_RECEIVED: EventCategory.TELEMETRY,
            EventType.TELEMETRY_THRESHOLD_EXCEEDED: EventCategory.TELEMETRY,
            EventType.TELEMETRY_ANOMALY_DETECTED: EventCategory.TELEMETRY,
            EventType.COMMAND_SENT: EventCategory.COMMAND,
            EventType.COMMAND_ACKNOWLEDGED: EventCategory.COMMAND,
            EventType.COMMAND_COMPLETED: EventCategory.COMMAND,
            EventType.COMMAND_FAILED: EventCategory.COMMAND,
            EventType.CONFIG_UPDATED: EventCategory.CONFIGURATION,
            EventType.CONFIG_APPLIED: EventCategory.CONFIGURATION,
            EventType.CONFIG_REJECTED: EventCategory.CONFIGURATION,
            EventType.CERTIFICATE_GENERATED: EventCategory.SECURITY,
            EventType.CERTIFICATE_REVOKED: EventCategory.SECURITY,
            EventType.AUTH_FAILED: EventCategory.SECURITY,
            EventType.UNAUTHORIZED_ACCESS: EventCategory.SECURITY,
            EventType.GROUP_CREATED: EventCategory.GROUP,
            EventType.GROUP_UPDATED: EventCategory.GROUP,
            EventType.GROUP_DELETED: EventCategory.GROUP,
            EventType.DEVICE_GROUP_ASSIGNED: EventCategory.GROUP,
            EventType.DEVICE_GROUP_REMOVED: EventCategory.GROUP,
            EventType.AUDIT_LOG_CREATED: EventCategory.AUDIT,
            EventType.COMPLIANCE_VIOLATION: EventCategory.AUDIT,
            EventType.SYSTEM_HEALTH_UPDATE: EventCategory.SYSTEM,
            EventType.SYSTEM_ALERT: EventCategory.SYSTEM,
            EventType.SYSTEM_ERROR: EventCategory.SYSTEM
        }
        
        return category_map.get(event_type, EventCategory.SYSTEM)
    
    async def _load_stream_configurations(self):
        """Load stream configurations from database"""
        try:
            if self.db:
                collection = self.db.event_stream_configs
                configs = await collection.find({}).to_list(None)
                
                for config_data in configs:
                    config = StreamConfiguration(**config_data)
                    self.stream_configs[config.stream_id] = config
                    self.stream_stats[config.stream_id] = EventStreamStats(stream_id=config.stream_id)
                
                logger.info(f"Loaded {len(self.stream_configs)} stream configurations")
        
        except Exception as e:
            logger.error(f"Error loading stream configurations: {e}")
    
    async def _redis_event_listener(self):
        """Listen for events from Redis"""
        try:
            # Subscribe to all organization channels
            pubsub = redis_client.pubsub()
            pattern = f"{self.redis_channel_prefix}:*"
            await pubsub.psubscribe(pattern)
            
            # Process messages
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Parse event
                        event_data = json.loads(message["data"])
                        event_type = EventType(event_data["event_type"])
                        
                        # Recreate event object based on type
                        if event_data["category"] == EventCategory.TELEMETRY.value:
                            event = TelemetryEventPayload(**event_data)
                        elif event_data["category"] == EventCategory.COMMAND.value:
                            event = CommandEventPayload(**event_data)
                        elif event_data["category"] == EventCategory.SECURITY.value:
                            event = SecurityEventPayload(**event_data)
                        else:
                            event = DeviceEventPayload(**event_data)
                        
                        # Process locally (skip Redis publish to avoid loop)
                        await websocket_service.publish_event(event)
                        await self._call_event_handlers(event)
                    
                    except Exception as e:
                        logger.error(f"Error processing Redis event: {e}")
        
        except Exception as e:
            logger.error(f"Error in Redis event listener: {e}")
    
    async def _update_statistics(self):
        """Periodically update statistics"""
        while True:
            try:
                await asyncio.sleep(self.stats_update_interval)
                
                # Save statistics to database
                if self.db:
                    collection = self.db.event_stream_stats
                    
                    for stream_id, stats in self.stream_stats.items():
                        stats.updated_at = datetime.utcnow()
                        await collection.update_one(
                            {"stream_id": stream_id},
                            {"$set": stats.__dict__},
                            upsert=True
                        )
            
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
    
    async def _cleanup_old_events(self):
        """Periodically cleanup old events"""
        while True:
            try:
                await asyncio.sleep(3600)  # 1 hour
                
                # Remove expired events
                if self.db:
                    collection = self.db.device_events
                    result = await collection.delete_many({
                        "expires_at": {"$lt": datetime.utcnow()}
                    })
                    
                    if result.deleted_count > 0:
                        logger.info(f"Cleaned up {result.deleted_count} expired events")
            
            except Exception as e:
                logger.error(f"Error cleaning up events: {e}")
    
    def get_stream_statistics(self, stream_id: Optional[str] = None) -> Dict[str, Any]:
        """Get streaming statistics"""
        if stream_id:
            stats = self.stream_stats.get(stream_id)
            return stats.__dict__ if stats else {}
        
        # Return all statistics
        return {
            "total_streams": len(self.stream_configs),
            "active_streams": len([c for c in self.stream_configs.values() if c.enabled]),
            "total_events": sum(s.total_events for s in self.stream_stats.values()),
            "streams": {sid: stats.__dict__ for sid, stats in self.stream_stats.items()}
        }


# Global instance
event_streaming_service = EventStreamingService()