# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class TelemetryType(Enum):
    """Telemetry data type enumeration"""
    SENSOR_DATA = "sensor_data"
    METRICS = "metrics"
    STATUS_UPDATE = "status_update"
    EVENT = "event"
    ALERT = "alert"
    DIAGNOSTIC = "diagnostic"
    PERFORMANCE = "performance"
    LOCATION = "location"


class TelemetryPriority(Enum):
    """Telemetry priority levels for processing"""
    CRITICAL = "critical"  # Process immediately
    HIGH = "high"         # Process within seconds
    NORMAL = "normal"     # Process within minutes
    LOW = "low"          # Batch process


class DataQuality(Enum):
    """Data quality indicators"""
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"


class AggregationType(Enum):
    """Aggregation types for telemetry data"""
    NONE = "none"
    AVERAGE = "average"
    SUM = "sum"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    LAST = "last"
    FIRST = "first"


@dataclass
class TelemetryPoint:
    """Individual telemetry data point"""
    timestamp: datetime
    value: Union[float, int, str, bool, Dict[str, Any]]
    unit: Optional[str] = None
    quality: DataQuality = DataQuality.GOOD
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "quality": self.quality.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryPoint":
        """Create from dictionary"""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            value=data["value"],
            unit=data.get("unit"),
            quality=DataQuality(data.get("quality", "good")),
            metadata=data.get("metadata", {})
        )


@dataclass
class TelemetryData:
    """Telemetry data container"""
    telemetry_id: str
    device_id: str
    org_id: str
    telemetry_type: TelemetryType
    priority: TelemetryPriority = TelemetryPriority.NORMAL
    data_points: List[TelemetryPoint] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    received_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "telemetry_id": self.telemetry_id,
            "device_id": self.device_id,
            "org_id": self.org_id,
            "telemetry_type": self.telemetry_type.value,
            "priority": self.priority.value,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "tags": self.tags,
            "metadata": self.metadata,
            "received_at": self.received_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TelemetryData":
        """Create from dictionary"""
        return cls(
            telemetry_id=data["telemetry_id"],
            device_id=data["device_id"],
            org_id=data["org_id"],
            telemetry_type=TelemetryType(data["telemetry_type"]),
            priority=TelemetryPriority(data.get("priority", "normal")),
            data_points=[TelemetryPoint.from_dict(dp) for dp in data.get("data_points", [])],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            received_at=datetime.fromisoformat(data["received_at"]) if isinstance(data.get("received_at"), str) else data.get("received_at", datetime.utcnow()),
            processed_at=datetime.fromisoformat(data["processed_at"]) if data.get("processed_at") else None
        )


@dataclass
class TelemetryBatch:
    """Batch of telemetry data for bulk processing"""
    batch_id: str
    org_id: str
    device_ids: List[str]
    telemetry_count: int
    total_data_points: int
    priority: TelemetryPriority
    telemetry_data: List[TelemetryData] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None
    
    def add_telemetry(self, telemetry: TelemetryData) -> None:
        """Add telemetry to batch"""
        self.telemetry_data.append(telemetry)
        if telemetry.device_id not in self.device_ids:
            self.device_ids.append(telemetry.device_id)
        self.telemetry_count += 1
        self.total_data_points += len(telemetry.data_points)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "batch_id": self.batch_id,
            "org_id": self.org_id,
            "device_ids": self.device_ids,
            "telemetry_count": self.telemetry_count,
            "total_data_points": self.total_data_points,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "processing_started_at": self.processing_started_at.isoformat() if self.processing_started_at else None,
            "processing_completed_at": self.processing_completed_at.isoformat() if self.processing_completed_at else None,
            "status": self.status,
            "error_message": self.error_message
        }


@dataclass
class TelemetryBuffer:
    """Buffer for accumulating telemetry data before processing"""
    buffer_id: str
    device_id: str
    org_id: str
    buffer_type: str  # "time_based", "size_based", "hybrid"
    max_size: int = 1000
    max_age_seconds: int = 60
    current_size: int = 0
    data_points: List[TelemetryPoint] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_flush_at: Optional[datetime] = None
    flush_count: int = 0
    
    def add_point(self, point: TelemetryPoint) -> bool:
        """Add data point to buffer. Returns True if buffer should be flushed."""
        self.data_points.append(point)
        self.current_size += 1
        
        # Check if buffer should be flushed
        if self.buffer_type == "size_based":
            return self.current_size >= self.max_size
        elif self.buffer_type == "time_based":
            age = (datetime.utcnow() - self.created_at).total_seconds()
            return age >= self.max_age_seconds
        else:  # hybrid
            age = (datetime.utcnow() - self.created_at).total_seconds()
            return self.current_size >= self.max_size or age >= self.max_age_seconds
    
    def flush(self) -> List[TelemetryPoint]:
        """Flush buffer and return data points"""
        flushed_points = self.data_points.copy()
        self.data_points.clear()
        self.current_size = 0
        self.last_flush_at = datetime.utcnow()
        self.flush_count += 1
        return flushed_points


@dataclass
class TelemetryAggregation:
    """Aggregated telemetry data"""
    device_id: str
    org_id: str
    metric_name: str
    aggregation_type: AggregationType
    period_start: datetime
    period_end: datetime
    value: Union[float, int]
    unit: Optional[str] = None
    sample_count: int = 0
    min_value: Optional[Union[float, int]] = None
    max_value: Optional[Union[float, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "device_id": self.device_id,
            "org_id": self.org_id,
            "metric_name": self.metric_name,
            "aggregation_type": self.aggregation_type.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "sample_count": self.sample_count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "metadata": self.metadata
        }


@dataclass
class TelemetryAlert:
    """Alert generated from telemetry data"""
    alert_id: str
    device_id: str
    org_id: str
    alert_type: str
    severity: str  # "critical", "high", "medium", "low"
    condition: str
    threshold_value: Union[float, int]
    actual_value: Union[float, int]
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    is_active: bool = True
    notification_sent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "device_id": self.device_id,
            "org_id": self.org_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "condition": self.condition,
            "threshold_value": self.threshold_value,
            "actual_value": self.actual_value,
            "triggered_at": self.triggered_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "is_active": self.is_active,
            "notification_sent": self.notification_sent,
            "metadata": self.metadata
        }


@dataclass
class TelemetryIngestionStats:
    """Statistics for telemetry ingestion"""
    org_id: str
    period_start: datetime
    period_end: datetime
    total_messages: int = 0
    total_data_points: int = 0
    successful_ingestions: int = 0
    failed_ingestions: int = 0
    average_latency_ms: float = 0.0
    peak_latency_ms: float = 0.0
    devices_reporting: int = 0
    data_volume_bytes: int = 0
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "org_id": self.org_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_messages": self.total_messages,
            "total_data_points": self.total_data_points,
            "successful_ingestions": self.successful_ingestions,
            "failed_ingestions": self.failed_ingestions,
            "average_latency_ms": self.average_latency_ms,
            "peak_latency_ms": self.peak_latency_ms,
            "devices_reporting": self.devices_reporting,
            "data_volume_bytes": self.data_volume_bytes,
            "error_counts": self.error_counts
        }