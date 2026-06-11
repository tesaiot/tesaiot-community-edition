# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Bulk Operations Service
Provides efficient bulk operations for device management with progress tracking

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
from concurrent.futures import ThreadPoolExecutor
import math

from ..models.bulk_models import (
    BulkOperationType, BulkOperationStatus, ItemStatus,
    BulkOperationItem, BulkCreateRequest, BulkUpdateRequest,
    BulkDeleteRequest, BulkOperationProgress, BulkOperationResult,
    BulkOperationResponse, BulkOperationFilter
)
from ..models.audit_models import DeviceAuditAction
from ..interfaces.device_interfaces import IDeviceService, IDeviceRepository, IDeviceCacheRepository
from ..services.audit_logging_service import device_audit_service
from ..validators.device_validator import DeviceValidator
from ...dashboard.utils.circuit_breaker import circuit_breaker
from ...dashboard.utils.metrics_decorator import track_dashboard_method

logger = logging.getLogger(__name__)


class BulkOperationsService:
    """Service for handling bulk device operations"""
    
    def __init__(
        self,
        device_service: IDeviceService,
        repository: IDeviceRepository,
        cache_repository: IDeviceCacheRepository,
        validator: DeviceValidator,
        max_workers: int = 4,
        operation_timeout: int = 3600  # 1 hour default timeout
    ):
        self.device_service = device_service
        self.repository = repository
        self.cache = cache_repository
        self.validator = validator
        self.max_workers = max_workers
        self.operation_timeout = operation_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_operations: Dict[str, BulkOperationProgress] = {}
        self.operation_results: Dict[str, BulkOperationResult] = {}
        self.cancellation_flags: Dict[str, bool] = {}
        
        logger.info(f"BulkOperationsService initialized with {max_workers} workers")
    
    @track_dashboard_method(
        method_name="bulk_create_devices",
        module="device_management",
        operation="bulk_create"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def bulk_create_devices(
        self,
        request: BulkCreateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """
        Initiate bulk device creation
        
        Args:
            request: Bulk create request
            org_id: Organization ID
            user: User performing the operation
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            BulkOperationResponse with operation ID and status
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            # Validate request
            request.validate()
            
            # Pre-validate all devices
            validation_errors = []
            valid_devices = []
            
            for idx, device_data in enumerate(request.devices):
                try:
                    # Apply provisioning template if specified
                    if request.provisioning_template_id:
                        device_data = await self._apply_provisioning_template(
                            device_data, request.provisioning_template_id, org_id
                        )
                    
                    # Validate device data
                    validated_data = self.validator.validate_device_data(device_data)
                    valid_devices.append((idx, validated_data))
                    
                except Exception as e:
                    validation_errors.append({
                        "index": idx,
                        "device_name": device_data.get("name", "Unknown"),
                        "error": str(e)
                    })
                    if not request.continue_on_error:
                        break
            
            # If validate_only, return validation results
            if request.validate_only:
                return BulkOperationResponse(
                    operation_id=operation_id,
                    operation_type=BulkOperationType.CREATE,
                    status=BulkOperationStatus.COMPLETED,
                    accepted_items=len(valid_devices),
                    rejected_items=len(validation_errors),
                    validation_errors=validation_errors
                )
            
            # Initialize operation tracking
            progress = BulkOperationProgress(
                operation_id=operation_id,
                operation_type=BulkOperationType.CREATE,
                total_items=len(valid_devices),
                total_batches=math.ceil(len(valid_devices) / request.batch_size)
            )
            self.active_operations[operation_id] = progress
            
            # Initialize result tracking
            result = BulkOperationResult(
                operation_id=operation_id,
                operation_type=BulkOperationType.CREATE,
                status=BulkOperationStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                total_items=len(valid_devices),
                metadata={
                    "org_id": org_id,
                    "user_id": user.get("id") if user else None,
                    "request_metadata": request.metadata
                }
            )
            self.operation_results[operation_id] = result
            
            # Start async processing
            asyncio.create_task(self._process_bulk_create(
                operation_id=operation_id,
                devices=valid_devices,
                request=request,
                org_id=org_id,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            ))
            
            # Audit log bulk operation start
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_BULK_PROVISIONED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "total_devices": len(request.devices),
                        "accepted_devices": len(valid_devices),
                        "rejected_devices": len(validation_errors),
                        "auto_generate_certificates": request.auto_generate_certificates,
                        "provisioning_template_id": request.provisioning_template_id
                    },
                    status="initiated",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION"],
                    data_sensitivity="high"
                )
            
            # Calculate estimated duration (rough estimate: 100 devices/second)
            estimated_duration = max(len(valid_devices) / 100, 1)
            
            return BulkOperationResponse(
                operation_id=operation_id,
                operation_type=BulkOperationType.CREATE,
                status=BulkOperationStatus.IN_PROGRESS,
                accepted_items=len(valid_devices),
                rejected_items=len(validation_errors),
                validation_errors=validation_errors[:10],  # Return first 10 errors
                estimated_duration_seconds=int(estimated_duration),
                progress_url=f"/api/v1/devices/bulk/{operation_id}/progress",
                result_url=f"/api/v1/devices/bulk/{operation_id}/result"
            )
            
        except Exception as e:
            logger.error(f"Error initiating bulk create: {str(e)}")
            raise
    
    async def _process_bulk_create(
        self,
        operation_id: str,
        devices: List[tuple],
        request: BulkCreateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Process bulk create operation in background"""
        progress = self.active_operations.get(operation_id)
        result = self.operation_results.get(operation_id)
        
        if not progress or not result:
            logger.error(f"Operation {operation_id} not found in tracking")
            return
        
        try:
            # Process in batches
            for batch_num in range(0, len(devices), request.batch_size):
                # Check for cancellation
                if self.cancellation_flags.get(operation_id, False):
                    result.status = BulkOperationStatus.CANCELLED
                    break
                
                batch = devices[batch_num:batch_num + request.batch_size]
                progress.current_batch = batch_num // request.batch_size + 1
                
                # Process batch concurrently
                batch_results = await asyncio.gather(
                    *[self._create_single_device(
                        idx, device_data, org_id, user, ip_address, user_agent,
                        request.auto_generate_certificates
                    ) for idx, device_data in batch],
                    return_exceptions=True
                )
                
                # Update progress and results
                for (idx, device_data), batch_result in zip(batch, batch_results):
                    item = BulkOperationItem(
                        index=idx,
                        data=device_data
                    )
                    
                    if isinstance(batch_result, Exception):
                        item.status = ItemStatus.FAILED
                        item.error = str(batch_result)
                        progress.update(processed=1, failed=1)
                    else:
                        item.status = ItemStatus.SUCCESS
                        item.result = batch_result
                        progress.update(processed=1, success=1)
                    
                    item.processed_at = datetime.utcnow()
                    result.add_item_result(item)
                
                # Update progress tracking
                if progress.total_items > 0:
                    # Estimate remaining time based on current processing rate
                    elapsed = (datetime.utcnow() - result.started_at).total_seconds()
                    rate = progress.processed_items / elapsed if elapsed > 0 else 0
                    remaining_items = progress.total_items - progress.processed_items
                    progress.estimated_time_remaining = int(remaining_items / rate) if rate > 0 else None
                
                # Small delay between batches to prevent overload
                await asyncio.sleep(0.1)
            
            # Finalize operation
            result.finalize()
            
            # Clear cache patterns for the organization
            await self.cache.clear_pattern(f"org:{org_id}:devices:*")
            
            # Audit log completion
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_BULK_PROVISIONED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "total_items": result.total_items,
                        "successful_items": result.successful_items,
                        "failed_items": result.failed_items,
                        "duration_seconds": result.duration_seconds
                    },
                    status="completed",
                    operation_duration_ms=result.duration_seconds * 1000 if result.duration_seconds else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION"],
                    data_sensitivity="high"
                )
            
        except Exception as e:
            logger.error(f"Error processing bulk create {operation_id}: {str(e)}")
            result.status = BulkOperationStatus.FAILED
            result.errors.append({
                "type": "system_error",
                "error": str(e)
            })
            result.finalize()
        finally:
            # Clean up active operation tracking after a delay
            await asyncio.sleep(300)  # Keep in memory for 5 minutes
            self.active_operations.pop(operation_id, None)
    
    async def _create_single_device(
        self,
        idx: int,
        device_data: Dict[str, Any],
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str],
        auto_generate_certificate: bool
    ) -> Dict[str, Any]:
        """Create a single device"""
        try:
            # Generate certificate if requested
            if auto_generate_certificate:
                # TODO: Integrate with certificate service
                device_data["certificate_id"] = f"cert_{uuid.uuid4()}"
            
            # Create device using device service
            device = await self.device_service.register_device(
                device_data, org_id, user, ip_address, user_agent
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error creating device at index {idx}: {str(e)}")
            raise
    
    @track_dashboard_method(
        method_name="bulk_update_devices",
        module="device_management",
        operation="bulk_update"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def bulk_update_devices(
        self,
        request: BulkUpdateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """
        Initiate bulk device update
        
        Args:
            request: Bulk update request
            org_id: Organization ID
            user: User performing the operation
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            BulkOperationResponse with operation ID and status
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            # Validate request
            request.validate()
            
            # Validate update data
            validated_updates = self.validator.validate_device_update(request.updates)
            
            # Get device IDs if using filters
            device_ids = request.device_ids
            if not device_ids and request.filters:
                # Query devices matching filters
                devices = await self.repository.find_many(
                    filters={**request.filters, "org_id": org_id},
                    skip=0,
                    limit=10000,  # Max limit
                    org_id=org_id
                )
                device_ids = [d["device_id"] for d in devices]
            
            if not device_ids:
                raise ValueError("No devices found matching the criteria")
            
            # If validate_only, return validation results
            if request.validate_only:
                return BulkOperationResponse(
                    operation_id=operation_id,
                    operation_type=BulkOperationType.UPDATE,
                    status=BulkOperationStatus.COMPLETED,
                    accepted_items=len(device_ids),
                    rejected_items=0,
                    validation_errors=[]
                )
            
            # Initialize operation tracking
            progress = BulkOperationProgress(
                operation_id=operation_id,
                operation_type=BulkOperationType.UPDATE,
                total_items=len(device_ids),
                total_batches=math.ceil(len(device_ids) / request.batch_size)
            )
            self.active_operations[operation_id] = progress
            
            # Initialize result tracking
            result = BulkOperationResult(
                operation_id=operation_id,
                operation_type=BulkOperationType.UPDATE,
                status=BulkOperationStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                total_items=len(device_ids),
                metadata={
                    "org_id": org_id,
                    "user_id": user.get("id") if user else None,
                    "updates": validated_updates,
                    "request_metadata": request.metadata
                }
            )
            self.operation_results[operation_id] = result
            
            # Start async processing
            asyncio.create_task(self._process_bulk_update(
                operation_id=operation_id,
                device_ids=device_ids,
                updates=validated_updates,
                request=request,
                org_id=org_id,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            ))
            
            # Audit log bulk operation start
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_UPDATED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "bulk_operation": True,
                        "total_devices": len(device_ids),
                        "updates": validated_updates,
                        "partial_update": request.partial_update
                    },
                    status="initiated",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION"],
                    data_sensitivity="medium"
                )
            
            # Calculate estimated duration
            estimated_duration = max(len(device_ids) / 200, 1)  # Faster than create
            
            return BulkOperationResponse(
                operation_id=operation_id,
                operation_type=BulkOperationType.UPDATE,
                status=BulkOperationStatus.IN_PROGRESS,
                accepted_items=len(device_ids),
                rejected_items=0,
                validation_errors=[],
                estimated_duration_seconds=int(estimated_duration),
                progress_url=f"/api/v1/devices/bulk/{operation_id}/progress",
                result_url=f"/api/v1/devices/bulk/{operation_id}/result"
            )
            
        except Exception as e:
            logger.error(f"Error initiating bulk update: {str(e)}")
            raise
    
    async def _process_bulk_update(
        self,
        operation_id: str,
        device_ids: List[str],
        updates: Dict[str, Any],
        request: BulkUpdateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Process bulk update operation in background"""
        progress = self.active_operations.get(operation_id)
        result = self.operation_results.get(operation_id)
        
        if not progress or not result:
            logger.error(f"Operation {operation_id} not found in tracking")
            return
        
        try:
            # Process in batches
            for batch_num in range(0, len(device_ids), request.batch_size):
                # Check for cancellation
                if self.cancellation_flags.get(operation_id, False):
                    result.status = BulkOperationStatus.CANCELLED
                    break
                
                batch_ids = device_ids[batch_num:batch_num + request.batch_size]
                progress.current_batch = batch_num // request.batch_size + 1
                
                # Process batch concurrently
                batch_results = await asyncio.gather(
                    *[self._update_single_device(
                        device_id, updates, org_id, user, ip_address, user_agent
                    ) for device_id in batch_ids],
                    return_exceptions=True
                )
                
                # Update progress and results
                for device_id, batch_result in zip(batch_ids, batch_results):
                    item = BulkOperationItem(
                        index=device_ids.index(device_id),
                        data={"device_id": device_id, "updates": updates}
                    )
                    
                    if isinstance(batch_result, Exception):
                        item.status = ItemStatus.FAILED
                        item.error = str(batch_result)
                        progress.update(processed=1, failed=1)
                        
                        if not request.continue_on_error:
                            result.status = BulkOperationStatus.FAILED
                            break
                    else:
                        item.status = ItemStatus.SUCCESS
                        item.result = batch_result
                        progress.update(processed=1, success=1)
                    
                    item.processed_at = datetime.utcnow()
                    result.add_item_result(item)
                
                # Update progress tracking
                if progress.total_items > 0:
                    elapsed = (datetime.utcnow() - result.started_at).total_seconds()
                    rate = progress.processed_items / elapsed if elapsed > 0 else 0
                    remaining_items = progress.total_items - progress.processed_items
                    progress.estimated_time_remaining = int(remaining_items / rate) if rate > 0 else None
                
                # Small delay between batches
                await asyncio.sleep(0.05)
            
            # Finalize operation
            result.finalize()
            
            # Clear cache patterns
            await self.cache.clear_pattern(f"org:{org_id}:devices:*")
            
            # Audit log completion
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_UPDATED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "bulk_operation": True,
                        "total_items": result.total_items,
                        "successful_items": result.successful_items,
                        "failed_items": result.failed_items,
                        "duration_seconds": result.duration_seconds
                    },
                    status="completed",
                    operation_duration_ms=result.duration_seconds * 1000 if result.duration_seconds else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION"],
                    data_sensitivity="medium"
                )
            
        except Exception as e:
            logger.error(f"Error processing bulk update {operation_id}: {str(e)}")
            result.status = BulkOperationStatus.FAILED
            result.errors.append({
                "type": "system_error",
                "error": str(e)
            })
            result.finalize()
        finally:
            # Clean up after delay
            await asyncio.sleep(300)
            self.active_operations.pop(operation_id, None)
    
    async def _update_single_device(
        self,
        device_id: str,
        updates: Dict[str, Any],
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> Dict[str, Any]:
        """Update a single device"""
        try:
            # Update device using device service
            device = await self.device_service.update_device(
                device_id, updates, org_id, user, ip_address, user_agent
            )
            
            return device
            
        except Exception as e:
            logger.error(f"Error updating device {device_id}: {str(e)}")
            raise
    
    @track_dashboard_method(
        method_name="bulk_delete_devices",
        module="device_management",
        operation="bulk_delete"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def bulk_delete_devices(
        self,
        request: BulkDeleteRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """
        Initiate bulk device deletion
        
        Args:
            request: Bulk delete request
            org_id: Organization ID
            user: User performing the operation
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            BulkOperationResponse with operation ID and status
        """
        start_time = time.time()
        operation_id = str(uuid.uuid4())
        
        try:
            # Validate request
            request.validate()
            
            # Get device IDs if using filters
            device_ids = request.device_ids
            if not device_ids and request.filters:
                # Query devices matching filters
                devices = await self.repository.find_many(
                    filters={**request.filters, "org_id": org_id},
                    skip=0,
                    limit=10000,
                    org_id=org_id
                )
                device_ids = [d["device_id"] for d in devices]
            
            if not device_ids:
                raise ValueError("No devices found matching the criteria")
            
            # Safety check - warn if deleting many devices
            if len(device_ids) > 100 and not request.force:
                logger.warning(f"Attempting to delete {len(device_ids)} devices without force flag")
                raise ValueError(f"Deleting {len(device_ids)} devices requires force=True")
            
            # If validate_only, return validation results
            if request.validate_only:
                return BulkOperationResponse(
                    operation_id=operation_id,
                    operation_type=BulkOperationType.DELETE,
                    status=BulkOperationStatus.COMPLETED,
                    accepted_items=len(device_ids),
                    rejected_items=0,
                    validation_errors=[]
                )
            
            # Initialize operation tracking
            progress = BulkOperationProgress(
                operation_id=operation_id,
                operation_type=BulkOperationType.DELETE,
                total_items=len(device_ids),
                total_batches=math.ceil(len(device_ids) / request.batch_size)
            )
            self.active_operations[operation_id] = progress
            
            # Initialize result tracking
            result = BulkOperationResult(
                operation_id=operation_id,
                operation_type=BulkOperationType.DELETE,
                status=BulkOperationStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                total_items=len(device_ids),
                metadata={
                    "org_id": org_id,
                    "user_id": user.get("id") if user else None,
                    "delete_telemetry": request.delete_telemetry,
                    "delete_certificates": request.delete_certificates,
                    "request_metadata": request.metadata
                }
            )
            self.operation_results[operation_id] = result
            
            # Start async processing
            asyncio.create_task(self._process_bulk_delete(
                operation_id=operation_id,
                device_ids=device_ids,
                request=request,
                org_id=org_id,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            ))
            
            # Audit log bulk operation start
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DELETED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "bulk_operation": True,
                        "total_devices": len(device_ids),
                        "delete_telemetry": request.delete_telemetry,
                        "delete_certificates": request.delete_certificates,
                        "force": request.force
                    },
                    status="initiated",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION", "DATA_DELETION"],
                    data_sensitivity="critical"
                )
            
            # Calculate estimated duration
            estimated_duration = max(len(device_ids) / 150, 1)
            
            return BulkOperationResponse(
                operation_id=operation_id,
                operation_type=BulkOperationType.DELETE,
                status=BulkOperationStatus.IN_PROGRESS,
                accepted_items=len(device_ids),
                rejected_items=0,
                validation_errors=[],
                estimated_duration_seconds=int(estimated_duration),
                progress_url=f"/api/v1/devices/bulk/{operation_id}/progress",
                result_url=f"/api/v1/devices/bulk/{operation_id}/result"
            )
            
        except Exception as e:
            logger.error(f"Error initiating bulk delete: {str(e)}")
            raise
    
    async def _process_bulk_delete(
        self,
        operation_id: str,
        device_ids: List[str],
        request: BulkDeleteRequest,
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Process bulk delete operation in background"""
        progress = self.active_operations.get(operation_id)
        result = self.operation_results.get(operation_id)
        
        if not progress or not result:
            logger.error(f"Operation {operation_id} not found in tracking")
            return
        
        try:
            # Process in batches
            for batch_num in range(0, len(device_ids), request.batch_size):
                # Check for cancellation
                if self.cancellation_flags.get(operation_id, False):
                    result.status = BulkOperationStatus.CANCELLED
                    break
                
                batch_ids = device_ids[batch_num:batch_num + request.batch_size]
                progress.current_batch = batch_num // request.batch_size + 1
                
                # Process batch concurrently
                batch_results = await asyncio.gather(
                    *[self._delete_single_device(
                        device_id, request, org_id, user, ip_address, user_agent
                    ) for device_id in batch_ids],
                    return_exceptions=True
                )
                
                # Update progress and results
                for device_id, batch_result in zip(batch_ids, batch_results):
                    item = BulkOperationItem(
                        index=device_ids.index(device_id),
                        data={"device_id": device_id}
                    )
                    
                    if isinstance(batch_result, Exception):
                        item.status = ItemStatus.FAILED
                        item.error = str(batch_result)
                        progress.update(processed=1, failed=1)
                        
                        if not request.continue_on_error:
                            result.status = BulkOperationStatus.FAILED
                            break
                    else:
                        item.status = ItemStatus.SUCCESS
                        item.result = {"deleted": True, "device_id": device_id}
                        progress.update(processed=1, success=1)
                    
                    item.processed_at = datetime.utcnow()
                    result.add_item_result(item)
                
                # Update progress tracking
                if progress.total_items > 0:
                    elapsed = (datetime.utcnow() - result.started_at).total_seconds()
                    rate = progress.processed_items / elapsed if elapsed > 0 else 0
                    remaining_items = progress.total_items - progress.processed_items
                    progress.estimated_time_remaining = int(remaining_items / rate) if rate > 0 else None
                
                # Small delay between batches
                await asyncio.sleep(0.05)
            
            # Finalize operation
            result.finalize()
            
            # Clear all cache patterns for the organization
            await self.cache.clear_pattern(f"org:{org_id}:*")
            
            # Audit log completion
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DELETED,
                    user=user,
                    details={
                        "operation_id": operation_id,
                        "bulk_operation": True,
                        "total_items": result.total_items,
                        "successful_items": result.successful_items,
                        "failed_items": result.failed_items,
                        "duration_seconds": result.duration_seconds
                    },
                    status="completed",
                    operation_duration_ms=result.duration_seconds * 1000 if result.duration_seconds else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["BULK_OPERATION", "DATA_DELETION"],
                    data_sensitivity="critical"
                )
            
        except Exception as e:
            logger.error(f"Error processing bulk delete {operation_id}: {str(e)}")
            result.status = BulkOperationStatus.FAILED
            result.errors.append({
                "type": "system_error",
                "error": str(e)
            })
            result.finalize()
        finally:
            # Clean up after delay
            await asyncio.sleep(300)
            self.active_operations.pop(operation_id, None)
    
    async def _delete_single_device(
        self,
        device_id: str,
        request: BulkDeleteRequest,
        org_id: str,
        user: Optional[Dict[str, Any]],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> bool:
        """Delete a single device"""
        try:
            # TODO: Delete telemetry data if requested
            if request.delete_telemetry:
                # Integration with telemetry service
                pass
            
            # TODO: Revoke certificates if requested
            if request.delete_certificates:
                # Integration with certificate service
                pass
            
            # Delete device using device service
            success = await self.device_service.delete_device(
                device_id, org_id, user, ip_address, user_agent
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            raise
    
    async def get_operation_progress(
        self,
        operation_id: str,
        org_id: str
    ) -> Optional[BulkOperationProgress]:
        """Get progress of a bulk operation"""
        progress = self.active_operations.get(operation_id)
        if progress:
            # Verify organization access
            result = self.operation_results.get(operation_id)
            if result and result.metadata.get("org_id") == org_id:
                return progress
        return None
    
    async def get_operation_result(
        self,
        operation_id: str,
        org_id: str,
        include_details: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get result of a bulk operation"""
        result = self.operation_results.get(operation_id)
        if result:
            # Verify organization access
            if result.metadata.get("org_id") == org_id:
                if include_details:
                    return result.to_dict()
                else:
                    return result.to_summary_dict()
        return None
    
    async def cancel_operation(
        self,
        operation_id: str,
        org_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cancel an in-progress bulk operation"""
        result = self.operation_results.get(operation_id)
        if result and result.metadata.get("org_id") == org_id:
            if result.status == BulkOperationStatus.IN_PROGRESS:
                self.cancellation_flags[operation_id] = True
                
                # Audit log cancellation
                if user:
                    await device_audit_service.log_device_operation(
                        action=DeviceAuditAction.DEVICE_BULK_PROVISIONED,
                        user=user,
                        details={
                            "operation_id": operation_id,
                            "action": "cancelled"
                        },
                        status="cancelled",
                        compliance_flags=["BULK_OPERATION"]
                    )
                
                return True
        return False
    
    async def list_operations(
        self,
        filter_params: BulkOperationFilter,
        org_id: str
    ) -> List[Dict[str, Any]]:
        """List bulk operations with filtering"""
        # Filter operations for the organization
        operations = []
        for op_id, result in self.operation_results.items():
            if result.metadata.get("org_id") == org_id:
                # Apply filters
                if filter_params.operation_ids and op_id not in filter_params.operation_ids:
                    continue
                if filter_params.operation_types and result.operation_type not in filter_params.operation_types:
                    continue
                if filter_params.statuses and result.status not in filter_params.statuses:
                    continue
                if filter_params.user_id and result.metadata.get("user_id") != filter_params.user_id:
                    continue
                if filter_params.start_date and result.started_at < filter_params.start_date:
                    continue
                if filter_params.end_date and result.started_at > filter_params.end_date:
                    continue
                
                operations.append(result.to_summary_dict())
        
        # Sort by start date descending
        operations.sort(key=lambda x: x["started_at"], reverse=True)
        
        return operations
    
    async def _apply_provisioning_template(
        self,
        device_data: Dict[str, Any],
        template_id: str,
        org_id: str
    ) -> Dict[str, Any]:
        """Apply provisioning template to device data"""
        # TODO: Implement template application
        # This would fetch the template and merge with device data
        return device_data
    
    async def cleanup_old_operations(self, retention_hours: int = 24):
        """Clean up old operation results from memory"""
        cutoff_time = datetime.utcnow() - timedelta(hours=retention_hours)
        
        operations_to_remove = []
        for op_id, result in self.operation_results.items():
            if result.completed_at and result.completed_at < cutoff_time:
                operations_to_remove.append(op_id)
        
        for op_id in operations_to_remove:
            self.operation_results.pop(op_id, None)
            self.active_operations.pop(op_id, None)
            self.cancellation_flags.pop(op_id, None)
        
        if operations_to_remove:
            logger.info(f"Cleaned up {len(operations_to_remove)} old bulk operations")


# Global instance
bulk_operations_service = None


def get_bulk_operations_service() -> BulkOperationsService:
    """Get the bulk operations service instance"""
    global bulk_operations_service
    if not bulk_operations_service:
        raise RuntimeError("Bulk operations service not initialized")
    return bulk_operations_service


def set_bulk_operations_service(service: BulkOperationsService):
    """Set the bulk operations service instance"""
    global bulk_operations_service
    bulk_operations_service = service