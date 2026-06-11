# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Event Streaming Models
Provides models for real-time event streaming and WebSocket communication

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import json


class EventType(Enum):
    """Types of events that can be streamed"""
    # Device lifecycle events
    DEVICE_CREATED = "device.created"
    DEVICE_UPDATED = "device.updated"
    DEVICE_DELETED = "device.deleted"
    DEVICE_STATUS_CHANGED = "device.status_changed"
    
    # Device connectivity events
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_HEARTBEAT = "device.heartbeat"
    
    # Telemetry events
    TELEMETRY_RECEIVED = "telemetry.received"
    TELEMETRY_THRESHOLD_EXCEEDED = "telemetry.threshold_exceeded"
    TELEMETRY_ANOMALY_DETECTED = "telemetry.anomaly_detected"
    
    # Command events
    COMMAND_SENT = "command.sent"
    COMMAND_ACKNOWLEDGED = "command.acknowledged"
    COMMAND_COMPLETED = "command.completed"
    COMMAND_FAILED = "command.failed"
    
    # Configuration events
    CONFIG_UPDATED = "config.updated"
    CONFIG_APPLIED = "config.applied"
    CONFIG_REJECTED = "config.rejected"
    
    # Security events
    CERTIFICATE_GENERATED = "certificate.generated"
    CERTIFICATE_REVOKED = "certificate.revoked"
    AUTH_FAILED = "auth.failed"
    UNAUTHORIZED_ACCESS = "unauthorized.access"
    
    # Group events
    GROUP_CREATED = "group.created"
    GROUP_UPDATED = "group.updated"
    GROUP_DELETED = "group.deleted"
    DEVICE_GROUP_ASSIGNED = "device.group_assigned"
    DEVICE_GROUP_REMOVED = "device.group_removed"
    
    # Audit events
    AUDIT_LOG_CREATED = "audit.log_created"
    COMPLIANCE_VIOLATION = "compliance.violation"
    
    # System events
    SYSTEM_HEALTH_UPDATE = "system.health_update"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_ERROR = "system.error"


class EventPriority(Enum):
    """Priority levels for events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventCategory(Enum):
    """Categories for grouping events"""
    LIFECYCLE = "lifecycle"
    CONNECTIVITY = "connectivity"
    TELEMETRY = "telemetry"
    COMMAND = "command"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    GROUP = "group"
    AUDIT = "audit"
    SYSTEM = "system"


@dataclass
class EventPayload:
    """Base class for event payloads"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    organization_id: str
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    priority: EventPriority = EventPriority.MEDIUM
    category: EventCategory = EventCategory.LIFECYCLE
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "organization_id": self.organization_id,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "priority": self.priority.value,
            "category": self.category.value,
            "data": self.data,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class DeviceEventPayload(EventPayload):
    """Payload for device-specific events"""
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    device_status: Optional[str] = None
    group_ids: List[str] = field(default_factory=list)


@dataclass
class TelemetryEventPayload(EventPayload):
    """Payload for telemetry events"""
    telemetry_type: str = ""
    value: Any = None
    unit: Optional[str] = None
    quality: Optional[str] = None
    threshold_name: Optional[str] = None
    threshold_value: Optional[float] = None
    anomaly_score: Optional[float] = None


@dataclass
class CommandEventPayload(EventPayload):
    """Payload for command events"""
    command_id: str = ""
    command_type: str = ""
    command_status: str = ""
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class SecurityEventPayload(EventPayload):
    """Payload for security events"""
    action: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    certificate_id: Optional[str] = None
    violation_type: Optional[str] = None
    risk_score: Optional[float] = None


@dataclass
class StreamConfiguration:
    """Configuration for event streaming"""
    stream_id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    enabled: bool = True
    event_types: List[EventType] = field(default_factory=list)
    categories: List[EventCategory] = field(default_factory=list)
    priorities: List[EventPriority] = field(default_factory=list)
    device_ids: List[str] = field(default_factory=list)
    group_ids: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: Optional[int] = None
    retention_hours: int = 24
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def matches_event(self, event: EventPayload) -> bool:
        """Check if an event matches this stream configuration"""
        # Check if stream is enabled
        if not self.enabled:
            return False
        
        # Check organization
        if event.organization_id != self.organization_id:
            return False
        
        # Check event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check category filter
        if self.categories and event.category not in self.categories:
            return False
        
        # Check priority filter
        if self.priorities and event.priority not in self.priorities:
            return False
        
        # Check device filter
        if self.device_ids and event.device_id not in self.device_ids:
            return False
        
        # Check group filter (if event has group info)
        if self.group_ids and isinstance(event, DeviceEventPayload):
            if not any(gid in self.group_ids for gid in event.group_ids):
                return False
        
        # Apply custom filters
        if self.filters:
            for key, value in self.filters.items():
                event_value = event.data.get(key)
                if isinstance(value, dict) and "$in" in value:
                    if event_value not in value["$in"]:
                        return False
                elif isinstance(value, dict) and "$gt" in value:
                    if not (event_value and event_value > value["$gt"]):
                        return False
                elif isinstance(value, dict) and "$lt" in value:
                    if not (event_value and event_value < value["$lt"]):
                        return False
                elif event_value != value:
                    return False
        
        return True


@dataclass
class EventSubscription:
    """Subscription to event streams"""
    subscription_id: str
    client_id: str
    user_id: str
    organization_id: str
    stream_ids: List[str] = field(default_factory=list)
    event_types: List[EventType] = field(default_factory=list)
    categories: List[EventCategory] = field(default_factory=list)
    priorities: List[EventPriority] = field(default_factory=list)
    device_ids: List[str] = field(default_factory=list)
    group_ids: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_event_at: Optional[datetime] = None
    event_count: int = 0
    
    def matches_event(self, event: EventPayload) -> bool:
        """Check if an event matches this subscription"""
        # Check if subscription is active
        if not self.active:
            return False
        
        # Check organization
        if event.organization_id != self.organization_id:
            return False
        
        # Check event type filter
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # Check category filter
        if self.categories and event.category not in self.categories:
            return False
        
        # Check priority filter
        if self.priorities and event.priority not in self.priorities:
            return False
        
        # Check device filter
        if self.device_ids and event.device_id and event.device_id not in self.device_ids:
            return False
        
        # Check group filter
        if self.group_ids and isinstance(event, DeviceEventPayload):
            if not any(gid in self.group_ids for gid in event.group_ids):
                return False
        
        # Apply custom filters
        for key, value in self.filters.items():
            if key in event.data:
                if event.data[key] != value:
                    return False
        
        return True


@dataclass
class EventFilter:
    """Advanced filtering for events"""
    name: str
    description: Optional[str] = None
    event_types: Optional[List[EventType]] = None
    categories: Optional[List[EventCategory]] = None
    priorities: Optional[List[EventPriority]] = None
    device_ids: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    user_ids: Optional[List[str]] = None
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    metadata_filters: Dict[str, Any] = field(default_factory=dict)
    data_filters: Dict[str, Any] = field(default_factory=dict)
    exclude_event_types: Optional[List[EventType]] = None
    exclude_device_ids: Optional[List[str]] = None
    
    def apply(self, event: EventPayload) -> bool:
        """Apply filter to an event"""
        # Time range filter
        if self.time_range_start and event.timestamp < self.time_range_start:
            return False
        if self.time_range_end and event.timestamp > self.time_range_end:
            return False
        
        # Inclusion filters
        if self.event_types and event.event_type not in self.event_types:
            return False
        if self.categories and event.category not in self.categories:
            return False
        if self.priorities and event.priority not in self.priorities:
            return False
        if self.device_ids and event.device_id not in self.device_ids:
            return False
        if self.user_ids and event.user_id not in self.user_ids:
            return False
        
        # Exclusion filters
        if self.exclude_event_types and event.event_type in self.exclude_event_types:
            return False
        if self.exclude_device_ids and event.device_id in self.exclude_device_ids:
            return False
        
        # Metadata filters
        for key, value in self.metadata_filters.items():
            if key not in event.metadata or event.metadata[key] != value:
                return False
        
        # Data filters
        for key, value in self.data_filters.items():
            if key not in event.data or event.data[key] != value:
                return False
        
        return True


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    message_id: str
    message_type: str  # "event", "subscribe", "unsubscribe", "ping", "pong", "error"
    timestamp: datetime
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


@dataclass
class WebSocketConnection:
    """WebSocket connection state"""
    connection_id: str
    client_id: str
    user_id: str
    organization_id: str
    ip_address: str
    user_agent: Optional[str] = None
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    subscriptions: Set[str] = field(default_factory=set)
    message_count: int = 0
    error_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventStreamStats:
    """Statistics for event streaming"""
    stream_id: str
    total_events: int = 0
    events_per_type: Dict[str, int] = field(default_factory=dict)
    events_per_category: Dict[str, int] = field(default_factory=dict)
    events_per_priority: Dict[str, int] = field(default_factory=dict)
    events_per_device: Dict[str, int] = field(default_factory=dict)
    active_subscriptions: int = 0
    total_subscribers: int = 0
    messages_sent: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    last_event_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)