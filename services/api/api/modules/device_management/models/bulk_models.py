# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Bulk Operation Models
Provides models for bulk device operations with progress tracking

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid


class BulkOperationType(Enum):
    """Type of bulk operation"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STATUS_CHANGE = "status_change"
    CONFIG_UPDATE = "config_update"
    GROUP_ASSIGN = "group_assign"


class BulkOperationStatus(Enum):
    """Status of bulk operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_SUCCESS = "partial_success"


class ItemStatus(Enum):
    """Status of individual item in bulk operation"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BulkOperationItem:
    """Individual item in a bulk operation"""
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    index: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    status: ItemStatus = ItemStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "item_id": self.item_id,
            "index": self.index,
            "data": self.data,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }


@dataclass
class BulkCreateRequest:
    """Request for bulk device creation"""
    devices: List[Dict[str, Any]]
    provisioning_template_id: Optional[str] = None
    auto_generate_certificates: bool = False
    validate_only: bool = False
    continue_on_error: bool = True
    batch_size: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the request"""
        if not self.devices:
            raise ValueError("No devices provided for bulk creation")
        if len(self.devices) > 10000:
            raise ValueError("Maximum 10,000 devices allowed per bulk operation")
        if self.batch_size < 1 or self.batch_size > 1000:
            raise ValueError("Batch size must be between 1 and 1000")


@dataclass
class BulkUpdateRequest:
    """Request for bulk device update"""
    device_ids: List[str]
    updates: Dict[str, Any]
    filters: Optional[Dict[str, Any]] = None  # Alternative to device_ids
    validate_only: bool = False
    continue_on_error: bool = True
    batch_size: int = 100
    partial_update: bool = True  # Allow partial updates
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the request"""
        if not self.device_ids and not self.filters:
            raise ValueError("Either device_ids or filters must be provided")
        if self.device_ids and len(self.device_ids) > 10000:
            raise ValueError("Maximum 10,000 devices allowed per bulk operation")
        if not self.updates:
            raise ValueError("No updates provided")
        if self.batch_size < 1 or self.batch_size > 1000:
            raise ValueError("Batch size must be between 1 and 1000")


@dataclass
class BulkDeleteRequest:
    """Request for bulk device deletion"""
    device_ids: List[str]
    filters: Optional[Dict[str, Any]] = None  # Alternative to device_ids
    force: bool = False  # Skip safety checks
    delete_telemetry: bool = False  # Also delete associated telemetry data
    delete_certificates: bool = False  # Also revoke/delete certificates
    validate_only: bool = False
    continue_on_error: bool = True
    batch_size: int = 100
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate the request"""
        if not self.device_ids and not self.filters:
            raise ValueError("Either device_ids or filters must be provided")
        if self.device_ids and len(self.device_ids) > 10000:
            raise ValueError("Maximum 10,000 devices allowed per bulk operation")
        if self.batch_size < 1 or self.batch_size > 1000:
            raise ValueError("Batch size must be between 1 and 1000")


@dataclass
class BulkOperationProgress:
    """Progress tracking for bulk operations"""
    operation_id: str
    operation_type: BulkOperationType
    total_items: int
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    current_batch: int = 0
    total_batches: int = 0
    percent_complete: float = 0.0
    estimated_time_remaining: Optional[int] = None  # seconds
    current_item: Optional[str] = None
    
    def update(self, processed: int = 0, success: int = 0, failed: int = 0, skipped: int = 0):
        """Update progress counters"""
        self.processed_items += processed
        self.successful_items += success
        self.failed_items += failed
        self.skipped_items += skipped
        
        if self.total_items > 0:
            self.percent_complete = (self.processed_items / self.total_items) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "total_items": self.total_items,
            "processed_items": self.processed_items,
            "successful_items": self.successful_items,
            "failed_items": self.failed_items,
            "skipped_items": self.skipped_items,
            "current_batch": self.current_batch,
            "total_batches": self.total_batches,
            "percent_complete": round(self.percent_complete, 2),
            "estimated_time_remaining": self.estimated_time_remaining,
            "current_item": self.current_item
        }


@dataclass
class BulkOperationResult:
    """Result of a bulk operation"""
    operation_id: str
    operation_type: BulkOperationType
    status: BulkOperationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    items: List[BulkOperationItem] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: Optional[float] = None
    
    def add_item_result(self, item: BulkOperationItem):
        """Add an item result"""
        self.items.append(item)
        if item.status == ItemStatus.SUCCESS:
            self.successful_items += 1
        elif item.status == ItemStatus.FAILED:
            self.failed_items += 1
            if item.error:
                self.errors.append({
                    "item_id": item.item_id,
                    "index": item.index,
                    "error": item.error
                })
        elif item.status == ItemStatus.SKIPPED:
            self.skipped_items += 1
    
    def finalize(self):
        """Finalize the operation result"""
        self.completed_at = datetime.utcnow()
        if self.started_at and self.completed_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        # Determine final status
        if self.failed_items == 0 and self.successful_items > 0:
            self.status = BulkOperationStatus.COMPLETED
        elif self.successful_items == 0 and self.failed_items > 0:
            self.status = BulkOperationStatus.FAILED
        elif self.successful_items > 0 and self.failed_items > 0:
            self.status = BulkOperationStatus.PARTIAL_SUCCESS
        elif self.status == BulkOperationStatus.IN_PROGRESS:
            self.status = BulkOperationStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "summary": {
                "total_items": self.total_items,
                "successful_items": self.successful_items,
                "failed_items": self.failed_items,
                "skipped_items": self.skipped_items,
                "success_rate": round((self.successful_items / self.total_items * 100), 2) if self.total_items > 0 else 0
            },
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata
        }
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary (without item details)"""
        summary = self.to_dict()
        summary.pop("items", None)  # Remove detailed items for summary view
        return summary


@dataclass
class BulkOperationFilter:
    """Filter for querying bulk operations"""
    operation_ids: Optional[List[str]] = None
    operation_types: Optional[List[BulkOperationType]] = None
    statuses: Optional[List[BulkOperationStatus]] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    has_errors: Optional[bool] = None
    
    def to_query(self) -> Dict[str, Any]:
        """Convert to database query"""
        query = {}
        
        if self.operation_ids:
            query["operation_id"] = {"$in": self.operation_ids}
        if self.operation_types:
            query["operation_type"] = {"$in": [t.value for t in self.operation_types]}
        if self.statuses:
            query["status"] = {"$in": [s.value for s in self.statuses]}
        if self.user_id:
            query["metadata.user_id"] = self.user_id
        if self.organization_id:
            query["metadata.organization_id"] = self.organization_id
        if self.start_date:
            query["started_at"] = {"$gte": self.start_date}
        if self.end_date:
            query.setdefault("started_at", {})["$lte"] = self.end_date
        if self.min_items is not None:
            query["total_items"] = {"$gte": self.min_items}
        if self.max_items is not None:
            query.setdefault("total_items", {})["$lte"] = self.max_items
        if self.has_errors is not None:
            if self.has_errors:
                query["failed_items"] = {"$gt": 0}
            else:
                query["failed_items"] = 0
        
        return query


@dataclass
class BulkOperationResponse:
    """Response for bulk operation initiation"""
    operation_id: str
    operation_type: BulkOperationType
    status: BulkOperationStatus
    accepted_items: int
    rejected_items: int
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    estimated_duration_seconds: Optional[int] = None
    progress_url: Optional[str] = None
    result_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation_id": self.operation_id,
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "accepted_items": self.accepted_items,
            "rejected_items": self.rejected_items,
            "validation_errors": self.validation_errors,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "progress_url": self.progress_url,
            "result_url": self.result_url
        }