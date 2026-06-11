# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Enhanced Device Log Models
Module: Device Logs Improvement Feature
Version: v2026.01
Build: 2026-01-09
Status: Development

This module provides enhanced device logging models for improved debugging
and troubleshooting of IoT device connectivity issues, particularly for
CSR (Certificate Signing Request) workflow with PSoC Edge + OPTIGA Trust M devices.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class LogLevel(str, Enum):
    """Log severity levels"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log categories for filtering and classification"""
    SECURITY = "security"       # TLS, certificates, authentication
    MQTT = "mqtt"               # Connection, subscribe, publish events
    CSR = "csr"                 # CSR workflow events
    TELEMETRY = "telemetry"     # Data ingestion events
    COMMAND = "command"         # Commands sent to device
    SYSTEM = "system"           # Platform system events
    CONNECTIVITY = "connectivity"  # Network connectivity events


class LogSource(str, Enum):
    """Source of log events"""
    EMQX = "emqx"
    MQTT_BRIDGE = "mqtt-bridge"
    API = "api"
    VAULT = "vault"
    DEVICE = "device"
    CSR_BRIDGE = "csr-bridge"
    SYSTEM = "system"


# TLS/Security Event Types
class TLSEventType(str, Enum):
    """TLS-related event types"""
    HANDSHAKE_START = "tls_handshake_start"
    HANDSHAKE_SUCCESS = "tls_handshake_success"
    HANDSHAKE_FAILED = "tls_handshake_failed"
    CERTIFICATE_REQUIRED = "tls_certificate_required"
    CERTIFICATE_INVALID = "tls_certificate_invalid"
    CERTIFICATE_EXPIRED = "tls_certificate_expired"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"


# MQTT Event Types
class MQTTEventType(str, Enum):
    """MQTT-related event types"""
    CONNECT = "mqtt_connect"
    DISCONNECT = "mqtt_disconnect"
    SUBSCRIBE = "mqtt_subscribe"
    UNSUBSCRIBE = "mqtt_unsubscribe"
    PUBLISH = "mqtt_publish"
    DELIVER = "mqtt_deliver"
    KEEPALIVE_TIMEOUT = "mqtt_keepalive_timeout"


# CSR Workflow Event Types
class CSREventType(str, Enum):
    """CSR workflow event types"""
    CSR_RECEIVED = "csr_received"
    CSR_VALIDATED = "csr_validated"
    CSR_VALIDATION_FAILED = "csr_validation_failed"
    CSR_FORWARDED_TO_VAULT = "csr_forwarded_to_vault"
    CERTIFICATE_SIGNED = "certificate_signed"
    CERTIFICATE_SIGNING_FAILED = "certificate_signing_failed"
    CERTIFICATE_PUBLISHED = "certificate_published"
    CERTIFICATE_DELIVERED = "certificate_delivered"
    CERTIFICATE_ACK = "certificate_ack"


class LogErrorDetail(BaseModel):
    """Error details for log entries"""
    code: str = Field(..., description="Error code (e.g., TLS_CERT_REQUIRED)")
    message: str = Field(..., description="Human-readable error message")
    stack: Optional[str] = Field(None, description="Stack trace if available")
    suggestion: Optional[str] = Field(None, description="Suggested action to resolve")

    class Config:
        extra = "allow"


class LogDetails(BaseModel):
    """Extended details for log entries"""
    client_ip: Optional[str] = Field(None, description="Client IP address")
    client_port: Optional[int] = Field(None, description="Client port")
    tls_version: Optional[str] = Field(None, description="TLS version (e.g., TLS 1.3)")
    cipher_suite: Optional[str] = Field(None, description="TLS cipher suite")
    certificate_cn: Optional[str] = Field(None, description="Certificate Common Name")
    error_code: Optional[str] = Field(None, description="Error code from source")
    mqtt_topic: Optional[str] = Field(None, description="MQTT topic")
    mqtt_qos: Optional[int] = Field(None, description="MQTT QoS level")
    payload_size: Optional[int] = Field(None, description="Payload size in bytes")

    class Config:
        extra = "allow"


class EnhancedDeviceLog(BaseModel):
    """Enhanced device log entry with comprehensive metadata"""

    # Identity
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    device_id: str = Field(..., description="Device identifier")
    organization_id: Optional[str] = Field(None, description="Organization ID")

    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Log timestamp (UTC)")

    # Classification
    level: LogLevel = Field(LogLevel.INFO, description="Log severity level")
    category: LogCategory = Field(LogCategory.SYSTEM, description="Log category")
    source: LogSource = Field(LogSource.SYSTEM, description="Source of log event")
    event_type: str = Field(..., description="Specific event type")

    # Content
    message: str = Field(..., description="Log message")
    details: Optional[LogDetails] = Field(default_factory=LogDetails, description="Extended details")

    # Correlation
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing across services")
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")
    span_id: Optional[str] = Field(None, description="Distributed trace span ID")

    # Error information
    error: Optional[LogErrorDetail] = Field(None, description="Error details if applicable")

    # Metadata for Phase 1 compatibility
    phase1_category: Optional[str] = Field(None, description="Phase 1 activity log category")
    severity_score: Optional[int] = Field(None, description="Severity score (1-5) for sorting")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        extra = "allow"
        # Pydantic v1 compatibility - use allow_population_by_field_name instead of v2's populate_by_name
        allow_population_by_field_name = True

    def calculate_severity_score(self) -> int:
        """Calculate severity score based on log level"""
        scores = {
            LogLevel.TRACE: 1,
            LogLevel.DEBUG: 1,
            LogLevel.INFO: 2,
            LogLevel.WARN: 3,
            LogLevel.ERROR: 4,
            LogLevel.CRITICAL: 5
        }
        return scores.get(self.level, 2)

    def to_mongo_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB-compatible dictionary"""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Ensure timestamp is datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))

        # Calculate severity score
        data['severity_score'] = self.calculate_severity_score()

        # Map to phase1 category
        phase1_mapping = {
            LogCategory.SECURITY: "USER_CRITICAL",
            LogCategory.MQTT: "API_PROBLEMS",
            LogCategory.CSR: "DEVICE_ISSUES",
            LogCategory.TELEMETRY: "API_PROBLEMS",
            LogCategory.COMMAND: "API_PROBLEMS",
            LogCategory.SYSTEM: "DEVICE_ISSUES",
            LogCategory.CONNECTIVITY: "DEVICE_ISSUES"
        }
        data['phase1_category'] = phase1_mapping.get(self.category, "DEVICE_ISSUES")

        return data


class EnhancedDeviceLogCreate(BaseModel):
    """Schema for creating a new enhanced device log"""
    device_id: str = Field(..., description="Device identifier")
    level: LogLevel = Field(LogLevel.INFO, description="Log severity level")
    category: LogCategory = Field(LogCategory.SYSTEM, description="Log category")
    source: LogSource = Field(LogSource.SYSTEM, description="Source of log event")
    event_type: str = Field(..., description="Specific event type")
    message: str = Field(..., description="Log message")
    details: Optional[Dict[str, Any]] = Field(None, description="Extended details")
    correlation_id: Optional[str] = Field(None, description="Correlation ID")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")

    class Config:
        extra = "allow"


class EnhancedDeviceLogResponse(BaseModel):
    """Response schema for enhanced device log"""
    id: str = Field(..., alias="_id")
    device_id: str
    timestamp: str
    level: str
    category: str
    source: str
    event_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    phase1_category: Optional[str] = None
    severity_score: Optional[int] = None

    class Config:
        # Pydantic v1 compatibility - use allow_population_by_field_name instead of v2's populate_by_name
        allow_population_by_field_name = True


class EnhancedDeviceLogListResponse(BaseModel):
    """Response schema for list of enhanced device logs"""
    logs: List[EnhancedDeviceLogResponse]
    total: int
    limit: int
    offset: int
    filters_applied: Optional[Dict[str, Any]] = None


class LogFilterParams(BaseModel):
    """Parameters for filtering device logs"""
    categories: Optional[List[LogCategory]] = Field(None, description="Filter by categories")
    levels: Optional[List[LogLevel]] = Field(None, description="Filter by log levels")
    sources: Optional[List[LogSource]] = Field(None, description="Filter by sources")
    from_time: Optional[datetime] = Field(None, description="Start time (inclusive)")
    to_time: Optional[datetime] = Field(None, description="End time (inclusive)")
    search: Optional[str] = Field(None, description="Search query (supports regex)")
    correlation_id: Optional[str] = Field(None, description="Filter by correlation ID")
    event_types: Optional[List[str]] = Field(None, description="Filter by event types")
    limit: int = Field(100, ge=1, le=1000, description="Max results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")


def generate_correlation_id(device_id: str, prefix: str = "log") -> str:
    """Generate a correlation ID for tracing"""
    timestamp = int(datetime.utcnow().timestamp())
    short_uuid = str(uuid.uuid4())[:8]
    return f"{prefix}-{device_id[:8]}-{timestamp}-{short_uuid}"
