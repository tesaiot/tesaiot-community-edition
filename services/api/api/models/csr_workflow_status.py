# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - CSR Workflow Status Models
Module: Device Logs Improvement Feature
Version: v2026.01
Build: 2026-01-09
Status: Development

This module provides models for tracking CSR (Certificate Signing Request)
workflow status. Designed for debugging and monitoring PSoC Edge + OPTIGA
Trust M device certificate provisioning.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class WorkflowStep(str, Enum):
    """CSR workflow steps in order"""
    MQTT_CONNECTED = "mqtt_connected"
    CSR_SUBMITTED = "csr_submitted"
    CSR_VALIDATED = "csr_validated"
    CERTIFICATE_SIGNED = "certificate_signed"
    CERTIFICATE_DELIVERED = "certificate_delivered"
    DEVICE_ACKNOWLEDGED = "device_acknowledged"


class StepStatus(str, Enum):
    """Status of a workflow step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Overall workflow status"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Workflow step order for validation
WORKFLOW_STEP_ORDER = [
    WorkflowStep.MQTT_CONNECTED,
    WorkflowStep.CSR_SUBMITTED,
    WorkflowStep.CSR_VALIDATED,
    WorkflowStep.CERTIFICATE_SIGNED,
    WorkflowStep.CERTIFICATE_DELIVERED,
    WorkflowStep.DEVICE_ACKNOWLEDGED
]


class WorkflowStepDetail(BaseModel):
    """Details of a single workflow step"""
    status: StepStatus = Field(StepStatus.PENDING, description="Step status")
    timestamp: Optional[datetime] = Field(None, description="When status changed")
    details: Optional[str] = Field(None, description="Additional details")
    duration_ms: Optional[int] = Field(None, description="Duration since previous step (ms)")

    class Config:
        extra = "allow"


class WorkflowError(BaseModel):
    """Error information for failed workflows"""
    step: str = Field(..., description="Step where error occurred")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    suggestion: Optional[str] = Field(None, description="Suggested resolution")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "allow"


class CSRWorkflowStatusModel(BaseModel):
    """Complete CSR workflow status model"""

    # Identity
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    device_id: str = Field(..., description="Device identifier")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    correlation_id: str = Field(..., description="Correlation ID for tracing")

    # Workflow steps
    steps: Dict[str, WorkflowStepDetail] = Field(
        default_factory=lambda: {
            WorkflowStep.MQTT_CONNECTED.value: WorkflowStepDetail(),
            WorkflowStep.CSR_SUBMITTED.value: WorkflowStepDetail(),
            WorkflowStep.CSR_VALIDATED.value: WorkflowStepDetail(),
            WorkflowStep.CERTIFICATE_SIGNED.value: WorkflowStepDetail(),
            WorkflowStep.CERTIFICATE_DELIVERED.value: WorkflowStepDetail(),
            WorkflowStep.DEVICE_ACKNOWLEDGED.value: WorkflowStepDetail()
        },
        description="Status of each workflow step"
    )

    # Current state
    current_step: Optional[str] = Field(None, description="Currently active step")
    workflow_status: WorkflowStatus = Field(WorkflowStatus.ACTIVE, description="Overall status")

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="Workflow start time")
    completed_at: Optional[datetime] = Field(None, description="Workflow completion time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")

    # Error information
    error: Optional[WorkflowError] = Field(None, description="Error details if failed")

    # Metadata
    csr_info: Optional[Dict[str, Any]] = Field(None, description="CSR details")
    certificate_info: Optional[Dict[str, Any]] = Field(None, description="Certificate details")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        extra = "allow"
        # Pydantic v1 compatibility - use allow_population_by_field_name instead of v2's populate_by_name
        allow_population_by_field_name = True

    def get_progress_percentage(self) -> int:
        """Calculate workflow progress percentage"""
        completed_steps = sum(
            1 for step in self.steps.values()
            if step.status == StepStatus.COMPLETED
        )
        total_steps = len(WORKFLOW_STEP_ORDER)
        return int((completed_steps / total_steps) * 100)

    def get_total_duration_ms(self) -> Optional[int]:
        """Get total workflow duration in milliseconds"""
        if not self.completed_at:
            return None
        delta = self.completed_at - self.started_at
        return int(delta.total_seconds() * 1000)

    def is_step_valid_transition(self, from_step: str, to_step: str) -> bool:
        """Validate if step transition is allowed"""
        try:
            from_idx = WORKFLOW_STEP_ORDER.index(WorkflowStep(from_step))
            to_idx = WORKFLOW_STEP_ORDER.index(WorkflowStep(to_step))
            # Allow same step (status change) or next step only
            return to_idx == from_idx or to_idx == from_idx + 1
        except (ValueError, IndexError):
            return False

    def to_mongo_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB-compatible dictionary"""
        data = self.model_dump(by_alias=True, exclude_none=True)

        # Ensure timestamps are datetime objects
        for field in ['started_at', 'completed_at', 'updated_at']:
            if field in data and isinstance(data[field], str):
                data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))

        # Convert step timestamps
        for step_data in data.get('steps', {}).values():
            if 'timestamp' in step_data and isinstance(step_data['timestamp'], str):
                step_data['timestamp'] = datetime.fromisoformat(
                    step_data['timestamp'].replace('Z', '+00:00')
                )

        return data


class CSRWorkflowStatusCreate(BaseModel):
    """Schema for creating a new CSR workflow status"""
    device_id: str = Field(..., description="Device identifier")
    organization_id: Optional[str] = Field(None, description="Organization ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID (auto-generated if not provided)")

    class Config:
        extra = "allow"


class CSRWorkflowStepUpdate(BaseModel):
    """Schema for updating a workflow step"""
    step: WorkflowStep = Field(..., description="Step to update")
    status: StepStatus = Field(..., description="New status")
    details: Optional[str] = Field(None, description="Additional details")

    class Config:
        extra = "allow"


class CSRWorkflowStatusResponse(BaseModel):
    """Response schema for CSR workflow status"""
    device_id: str
    correlation_id: str
    workflow_status: str
    current_step: Optional[str]
    steps: Dict[str, Dict[str, Any]]
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    progress_percentage: int
    total_duration_ms: Optional[int] = None

    class Config:
        extra = "allow"


class CSRWorkflowListResponse(BaseModel):
    """Response schema for list of CSR workflows"""
    workflows: List[CSRWorkflowStatusResponse]
    total: int
    active_count: int
    completed_count: int
    failed_count: int


def generate_csr_correlation_id(device_id: str) -> str:
    """Generate a correlation ID for CSR workflow"""
    timestamp = int(datetime.utcnow().timestamp())
    return f"csr-{device_id[:8]}-{timestamp}"


# Error codes and suggestions for common CSR workflow failures
CSR_ERROR_SUGGESTIONS = {
    "TLS_CERT_REQUIRED": {
        "code": "TLS_CERT_REQUIRED",
        "message": "No client certificate provided during TLS handshake",
        "suggestion": "Ensure device has valid certificate in OPTIGA Trust M OID 0xE0E0 (factory) or 0xE0E1 (device). Check firmware for certificate staging before MQTT connect."
    },
    "TLS_CERT_INVALID": {
        "code": "TLS_CERT_INVALID",
        "message": "Client certificate validation failed",
        "suggestion": "Certificate may be expired, revoked, or not signed by trusted CA. Check certificate chain and validity dates."
    },
    "TLS_CERT_EXPIRED": {
        "code": "TLS_CERT_EXPIRED",
        "message": "Client certificate has expired",
        "suggestion": "Device certificate has expired. Trigger certificate renewal via factory certificate or use out-of-band provisioning."
    },
    "CSR_INVALID_FORMAT": {
        "code": "CSR_INVALID_FORMAT",
        "message": "CSR format is invalid",
        "suggestion": "Ensure CSR is properly Base64-encoded PEM format. Check for truncation or encoding errors during MQTT transmission."
    },
    "CSR_SIGNATURE_INVALID": {
        "code": "CSR_SIGNATURE_INVALID",
        "message": "CSR signature does not match public key",
        "suggestion": "CSR was not signed with the correct private key. Ensure OPTIGA Trust M OID 0xE0F1 contains matching keypair."
    },
    "VAULT_SIGNING_FAILED": {
        "code": "VAULT_SIGNING_FAILED",
        "message": "Vault CA failed to sign certificate",
        "suggestion": "Check Vault service health and PKI role configuration. Verify CSR Common Name matches allowed patterns."
    },
    "MQTT_PUBLISH_FAILED": {
        "code": "MQTT_PUBLISH_FAILED",
        "message": "Failed to publish certificate to device topic",
        "suggestion": "Check EMQX broker connectivity and device subscription status. Verify device is subscribed to commands/# topic."
    },
    "DEVICE_ACK_TIMEOUT": {
        "code": "DEVICE_ACK_TIMEOUT",
        "message": "Device did not acknowledge certificate receipt",
        "suggestion": "Device may have disconnected or certificate write failed. Check device serial output for errors."
    }
}


def get_error_suggestion(error_code: str) -> Optional[Dict[str, str]]:
    """Get error suggestion for a given error code"""
    return CSR_ERROR_SUGGESTIONS.get(error_code)
