# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Audit Models
Provides comprehensive audit logging models for device operations

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

# Maximum length for a user-supplied $regex search term (ReDoS mitigation).
MAX_AUDIT_SEARCH_LENGTH = 128


class DeviceAuditAction(Enum):
    """Device-specific audit actions"""
    # Device CRUD operations
    DEVICE_CREATED = "device.created"
    DEVICE_UPDATED = "device.updated"
    DEVICE_DELETED = "device.deleted"
    DEVICE_VIEWED = "device.viewed"
    DEVICE_LISTED = "device.listed"
    DEVICE_EXPORTED = "device.exported"
    
    # Device status operations
    DEVICE_STATUS_CHANGED = "device.status_changed"
    DEVICE_ACTIVATED = "device.activated"
    DEVICE_DEACTIVATED = "device.deactivated"
    DEVICE_MAINTENANCE_MODE = "device.maintenance_mode"
    
    # Device provisioning
    DEVICE_PROVISIONED = "device.provisioned"
    DEVICE_BULK_PROVISIONED = "device.bulk_provisioned"
    DEVICE_AUTO_PROVISIONED = "device.auto_provisioned"
    DEVICE_PROVISIONING_FAILED = "device.provisioning_failed"
    
    # Device configuration
    DEVICE_CONFIG_UPDATED = "device.config_updated"
    DEVICE_CONFIG_APPLIED = "device.config_applied"
    DEVICE_CONFIG_ROLLBACK = "device.config_rollback"
    DEVICE_TEMPLATE_APPLIED = "device.template_applied"
    
    # Device security
    DEVICE_CERTIFICATE_GENERATED = "device.certificate_generated"
    DEVICE_CERTIFICATE_RENEWED = "device.certificate_renewed"
    DEVICE_CERTIFICATE_REVOKED = "device.certificate_revoked"
    DEVICE_CREDENTIALS_ROTATED = "device.credentials_rotated"
    DEVICE_AUTH_FAILED = "device.auth_failed"
    
    # Device commands
    DEVICE_COMMAND_SENT = "device.command_sent"
    DEVICE_COMMAND_ACKNOWLEDGED = "device.command_acknowledged"
    DEVICE_COMMAND_COMPLETED = "device.command_completed"
    DEVICE_COMMAND_FAILED = "device.command_failed"
    
    # Device groups
    DEVICE_GROUP_ASSIGNED = "device.group_assigned"
    DEVICE_GROUP_REMOVED = "device.group_removed"
    DEVICE_GROUPS_UPDATED = "device.groups_updated"
    GROUP_CREATED = "group.created"
    GROUP_UPDATED = "group.updated"
    GROUP_DELETED = "group.deleted"
    GROUP_MEMBERSHIP_ADDED = "group.membership_added"
    GROUP_MEMBERSHIP_REMOVED = "group.membership_removed"
    GROUP_OPERATION_EXECUTED = "group.operation_executed"
    
    # Security violations
    DEVICE_UNAUTHORIZED_ACCESS = "device.unauthorized_access"
    DEVICE_SUSPICIOUS_ACTIVITY = "device.suspicious_activity"
    DEVICE_COMPLIANCE_VIOLATION = "device.compliance_violation"
    
    # Data operations
    DEVICE_DATA_ACCESSED = "device.data_accessed"
    DEVICE_DATA_EXPORTED = "device.data_exported"
    DEVICE_DATA_PURGED = "device.data_purged"
    
    # Query operations
    DEVICE_QUERIED = "device.queried"
    DEVICE_AGGREGATED = "device.aggregated"
    
    # Event streaming operations
    DEVICE_WEBSOCKET_CONNECTED = "device.websocket_connected"
    DEVICE_WEBSOCKET_DISCONNECTED = "device.websocket_disconnected"
    DEVICE_EVENT_STREAMED = "device.event_streamed"
    DEVICE_STREAM_SUBSCRIBED = "device.stream_subscribed"
    DEVICE_STREAM_UNSUBSCRIBED = "device.stream_unsubscribed"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(Enum):
    """Audit event categories for filtering and reporting"""
    CRUD = "crud"
    STATUS = "status"
    PROVISIONING = "provisioning"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    COMMAND = "command"
    GROUP = "group"
    COMPLIANCE = "compliance"
    DATA = "data"


@dataclass
class DeviceAuditEntry:
    """Comprehensive audit log entry for device operations"""
    # Core identifiers
    audit_id: str
    timestamp: datetime
    action: DeviceAuditAction
    category: AuditCategory
    severity: AuditSeverity
    
    # User context
    user_id: str
    user_email: str
    user_role: str
    organization_id: str
    
    # Device context
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    
    # Operation details
    operation_status: str = "success"  # success, failure, partial
    error_message: Optional[str] = None
    
    # Request context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Additional details
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Compliance metadata
    compliance_flags: List[str] = field(default_factory=list)  # GDPR, HIPAA, etc.
    data_sensitivity: str = "low"  # low, medium, high, critical
    
    # Performance metrics
    operation_duration_ms: Optional[float] = None
    
    # Relationships
    related_audit_ids: List[str] = field(default_factory=list)
    parent_audit_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit entry to dictionary for storage"""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "user": {
                "id": self.user_id,
                "email": self.user_email,
                "role": self.user_role,
                "organization_id": self.organization_id
            },
            "device": {
                "id": self.device_id,
                "name": self.device_name,
                "type": self.device_type
            },
            "operation": {
                "status": self.operation_status,
                "error_message": self.error_message,
                "duration_ms": self.operation_duration_ms
            },
            "request": {
                "ip_address": self.ip_address,
                "user_agent": self.user_agent,
                "session_id": self.session_id,
                "request_id": self.request_id
            },
            "details": self.details,
            "compliance": {
                "flags": self.compliance_flags,
                "data_sensitivity": self.data_sensitivity
            },
            "relationships": {
                "parent_audit_id": self.parent_audit_id,
                "related_audit_ids": self.related_audit_ids
            }
        }
    
    def to_json(self) -> str:
        """Convert audit entry to JSON string"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceAuditEntry":
        """Create audit entry from dictionary"""
        return cls(
            audit_id=data["audit_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action=DeviceAuditAction(data["action"]),
            category=AuditCategory(data["category"]),
            severity=AuditSeverity(data["severity"]),
            user_id=data["user"]["id"],
            user_email=data["user"]["email"],
            user_role=data["user"]["role"],
            organization_id=data["user"]["organization_id"],
            device_id=data["device"].get("id"),
            device_name=data["device"].get("name"),
            device_type=data["device"].get("type"),
            operation_status=data["operation"]["status"],
            error_message=data["operation"].get("error_message"),
            operation_duration_ms=data["operation"].get("duration_ms"),
            ip_address=data["request"].get("ip_address"),
            user_agent=data["request"].get("user_agent"),
            session_id=data["request"].get("session_id"),
            request_id=data["request"].get("request_id"),
            details=data.get("details", {}),
            compliance_flags=data["compliance"].get("flags", []),
            data_sensitivity=data["compliance"].get("data_sensitivity", "low"),
            parent_audit_id=data["relationships"].get("parent_audit_id"),
            related_audit_ids=data["relationships"].get("related_audit_ids", [])
        )


@dataclass
class DeviceAuditSummary:
    """Summary of audit activities for reporting"""
    organization_id: str
    start_date: datetime
    end_date: datetime
    total_events: int = 0
    
    # Event counts by action
    events_by_action: Dict[str, int] = field(default_factory=dict)
    
    # Event counts by category
    events_by_category: Dict[str, int] = field(default_factory=dict)
    
    # Event counts by severity
    events_by_severity: Dict[str, int] = field(default_factory=dict)
    
    # Event counts by user
    events_by_user: Dict[str, int] = field(default_factory=dict)
    
    # Event counts by device
    events_by_device: Dict[str, int] = field(default_factory=dict)
    
    # Failure statistics
    total_failures: int = 0
    failure_rate: float = 0.0
    
    # Security statistics
    security_events: int = 0
    compliance_violations: int = 0
    
    # Performance statistics
    avg_operation_duration_ms: float = 0.0
    max_operation_duration_ms: float = 0.0
    
    # Top operations
    top_actions: List[Dict[str, Any]] = field(default_factory=list)
    top_users: List[Dict[str, Any]] = field(default_factory=list)
    top_devices: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeviceAuditFilter:
    """Filter criteria for querying audit logs"""
    organization_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actions: Optional[List[DeviceAuditAction]] = None
    categories: Optional[List[AuditCategory]] = None
    severities: Optional[List[AuditSeverity]] = None
    user_ids: Optional[List[str]] = None
    device_ids: Optional[List[str]] = None
    operation_status: Optional[str] = None
    compliance_flags: Optional[List[str]] = None
    search_text: Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort_by: str = "timestamp"
    sort_order: str = "desc"
    
    def to_query(self) -> Dict[str, Any]:
        """Convert filter to database query"""
        query = {"organization_id": self.organization_id}
        
        if self.start_date:
            query["timestamp"] = {"$gte": self.start_date}
        if self.end_date:
            query.setdefault("timestamp", {})["$lte"] = self.end_date
        
        if self.actions:
            query["action"] = {"$in": [a.value for a in self.actions]}
        if self.categories:
            query["category"] = {"$in": [c.value for c in self.categories]}
        if self.severities:
            query["severity"] = {"$in": [s.value for s in self.severities]}
        
        if self.user_ids:
            query["user.id"] = {"$in": self.user_ids}
        if self.device_ids:
            query["device.id"] = {"$in": self.device_ids}
        
        if self.operation_status:
            query["operation.status"] = self.operation_status
        
        if self.compliance_flags:
            query["compliance.flags"] = {"$in": self.compliance_flags}
        
        if self.search_text:
            # Regex-escape and length-cap the user-supplied search term to
            # prevent NoSQL regex injection and ReDoS.
            if not isinstance(self.search_text, str):
                raise ValueError("search_text must be a string")
            if len(self.search_text) > MAX_AUDIT_SEARCH_LENGTH:
                raise ValueError(
                    f"search_text exceeds maximum length of "
                    f"{MAX_AUDIT_SEARCH_LENGTH}"
                )
            search_literal = re.escape(self.search_text)
            query["$or"] = [
                {"user.email": {"$regex": search_literal, "$options": "i"}},
                {"device.name": {"$regex": search_literal, "$options": "i"}},
                {"details": {"$regex": search_literal, "$options": "i"}}
            ]
        
        return query


@dataclass
class ComplianceReport:
    """Compliance report based on audit data"""
    organization_id: str
    report_period: str  # e.g., "2024-Q1"
    generated_at: datetime
    
    # Compliance metrics
    total_operations: int = 0
    compliant_operations: int = 0
    compliance_rate: float = 0.0
    
    # GDPR compliance
    gdpr_data_access_logs: int = 0
    gdpr_data_deletion_logs: int = 0
    gdpr_consent_logs: int = 0
    
    # Security compliance
    failed_auth_attempts: int = 0
    unauthorized_access_attempts: int = 0
    certificate_operations: int = 0
    
    # Data governance
    data_exports: int = 0
    data_purges: int = 0
    sensitive_data_access: int = 0
    
    # Violations
    compliance_violations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)