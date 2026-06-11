# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import time

from ..interfaces.device_interfaces import IDeviceService, IDeviceRepository, IDeviceValidator, IDeviceCacheRepository
from ..models.device_models import Device, DeviceStatus
from ..models.audit_models import DeviceAuditAction
from ..models.query_models import DeviceQuery, QueryResult, AggregationQuery
from ..models.bulk_models import (
    BulkCreateRequest, BulkUpdateRequest, BulkDeleteRequest,
    BulkOperationResponse, BulkOperationProgress, BulkOperationFilter
)
from ..services.audit_logging_service import device_audit_service
from ..services.event_streaming_service import event_streaming_service
from ..services.query_builder import DeviceQueryBuilder
from ..models.event_streaming_models import EventType, EventPriority
from ...dashboard.utils.circuit_breaker import circuit_breaker
from ...dashboard.utils.metrics_decorator import track_dashboard_method
from ....core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ModularDeviceService(IDeviceService):
    """Modular implementation of Device Service"""
    
    def __init__(
        self,
        repository: IDeviceRepository,
        cache_repository: IDeviceCacheRepository,
        validator: IDeviceValidator,
        cache_ttl: int = 300
    ):
        self.repository = repository
        self.cache = cache_repository
        self.validator = validator
        self.cache_ttl = cache_ttl
        self.query_builder = DeviceQueryBuilder()
        self._bulk_operations_service = None  # Will be set during initialization
        logger.info("ModularDeviceService initialized")
    
    @track_dashboard_method(
        method_name="device_register",
        module="device_management",
        operation="create"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def register_device(self, device_data: Dict[str, Any], org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Register a new device in the platform"""
        start_time = time.time()
        audit_details = {
            "device_type": device_data.get("device_type"),
            "protocol": device_data.get("protocol", "mqtt"),
            "has_certificate": bool(device_data.get("certificate_id")),
            "group_count": len(device_data.get("group_ids", []))
        }
        
        try:
            # Validate input data
            validated_data = self.validator.validate_device_data(device_data)
            
            # Generate device ID if not provided
            device_id = validated_data.get("device_id") or str(uuid.uuid4())
            
            # Create device model
            device = Device(
                device_id=device_id,
                org_id=org_id,
                name=validated_data["name"],
                device_type=validated_data["device_type"],
                status=DeviceStatus.PROVISIONING,
                protocol=validated_data.get("protocol", "mqtt"),
                mac_address=validated_data.get("mac_address"),
                ip_address=validated_data.get("ip_address"),
                firmware_version=validated_data.get("firmware_version"),
                hardware_version=validated_data.get("hardware_version"),
                serial_number=validated_data.get("serial_number"),
                location=validated_data.get("location"),
                metadata=validated_data.get("metadata", {}),
                tags=validated_data.get("tags", []),
                group_ids=validated_data.get("group_ids", [])
            )
            
            # Save to database
            device_dict = device.to_dict()
            saved_device = await self.repository.create(device_dict)
            
            # Cache the device
            cache_key = self._get_cache_key(device_id, org_id)
            await self.cache.set(cache_key, saved_device, self.cache_ttl)
            
            # Log registration
            logger.info(f"Device registered: {device_id} for org: {org_id}")
            
            # Audit log the device creation
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_CREATED,
                    user=user,
                    device_id=device_id,
                    device_name=device.name,
                    device_type=device.device_type.value,
                    details={
                        **audit_details,
                        "created_device": saved_device
                    },
                    status="success",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["GDPR"] if "personal_data" in device_data.get("metadata", {}) else [],
                    data_sensitivity="medium"
                )
            
            # Emit device created event
            await event_streaming_service.emit_device_event(
                event_type=EventType.DEVICE_CREATED,
                device=device,
                user_id=str(user.get('_id', user.get('id'))) if user else None,
                priority=EventPriority.MEDIUM,
                data={
                    "registration_type": "manual",
                    "has_certificate": bool(device_data.get("certificate_id")),
                    "initial_status": device.status.value
                }
            )
            
            return saved_device
            
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_CREATED,
                    user=user,
                    device_name=device_data.get("name"),
                    device_type=device_data.get("device_type"),
                    details=audit_details,
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_get",
        module="device_management",
        operation="read"
    )
    async def get_device(self, device_id: str, org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get device details by ID"""
        try:
            # Validate device ID
            if not self.validator.validate_device_id(device_id):
                raise ValueError(f"Invalid device ID format: {device_id}")
            
            # Check cache first
            cache_key = self._get_cache_key(device_id, org_id)
            cached_device = await self.cache.get(cache_key)
            
            if cached_device:
                logger.debug(f"Device {device_id} found in cache")
                return cached_device
            
            # Get from database
            device = await self.repository.find_by_id(device_id, org_id)
            
            if device:
                # Cache the result
                await self.cache.set(cache_key, device, self.cache_ttl)
                logger.debug(f"Device {device_id} loaded from database")
            
            # Audit log device view
            if user and device:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_VIEWED,
                    user=user,
                    device_id=device_id,
                    device_name=device.get("name"),
                    device_type=device.get("device_type"),
                    details={"fields_accessed": list(device.keys())},
                    status="success",
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return device
            
        except Exception as e:
            logger.error(f"Error getting device {device_id}: {str(e)}")
            
            # Audit log the failure
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_VIEWED,
                    user=user,
                    device_id=device_id,
                    status="failure",
                    error_message=str(e),
                    ip_address=ip_address
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_update",
        module="device_management",
        operation="update"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def update_device(self, device_id: str, updates: Dict[str, Any], org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Update device information"""
        start_time = time.time()
        
        # Track what fields are being updated for audit
        updated_fields = list(updates.keys())
        is_security_update = any(field in ["certificate_id", "credentials", "status"] for field in updated_fields)
        
        try:
            # Validate device ID
            if not self.validator.validate_device_id(device_id):
                raise ValueError(f"Invalid device ID format: {device_id}")
            
            # Validate update data
            validated_updates = self.validator.validate_device_update(updates)
            
            # Add updated timestamp
            validated_updates["updated_at"] = datetime.utcnow()
            
            # Update in database
            updated_device = await self.repository.update(device_id, validated_updates, org_id)
            
            # Invalidate cache
            cache_key = self._get_cache_key(device_id, org_id)
            await self.cache.delete(cache_key)
            
            # Cache the updated device
            await self.cache.set(cache_key, updated_device, self.cache_ttl)
            
            logger.info(f"Device updated: {device_id}")
            
            # Audit log the update
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_UPDATED,
                    user=user,
                    device_id=device_id,
                    device_name=updated_device.get("name"),
                    device_type=updated_device.get("device_type"),
                    details={
                        "updated_fields": updated_fields,
                        "is_security_update": is_security_update,
                        "updates": {k: v for k, v in updates.items() if k not in ["password", "private_key", "secret"]}
                    },
                    status="success",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["SECURITY"] if is_security_update else [],
                    data_sensitivity="high" if is_security_update else "medium"
                )
            
            # Emit device updated event
            device_model = Device.from_dict(updated_device)
            await event_streaming_service.emit_device_event(
                event_type=EventType.DEVICE_UPDATED,
                device=device_model,
                user_id=str(user.get('_id', user.get('id'))) if user else None,
                priority=EventPriority.HIGH if is_security_update else EventPriority.MEDIUM,
                data={
                    "updated_fields": updated_fields,
                    "is_security_update": is_security_update
                }
            )
            
            # Check for status changes
            if "status" in updates:
                await event_streaming_service.emit_device_event(
                    event_type=EventType.DEVICE_STATUS_CHANGED,
                    device=device_model,
                    user_id=str(user.get('_id', user.get('id'))) if user else None,
                    priority=EventPriority.MEDIUM,
                    data={
                        "old_status": updated_device.get("previous_status"),
                        "new_status": updates["status"]
                    }
                )
            
            return updated_device
            
        except Exception as e:
            logger.error(f"Error updating device {device_id}: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_UPDATED,
                    user=user,
                    device_id=device_id,
                    details={
                        "attempted_updates": updated_fields,
                        "is_security_update": is_security_update
                    },
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_delete",
        module="device_management",
        operation="delete"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def delete_device(self, device_id: str, org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
        """Delete a device"""
        start_time = time.time()
        device_info = None
        
        try:
            # Get device info before deletion for audit
            device_info = await self.repository.find_by_id(device_id, org_id)
            # Validate device ID
            if not self.validator.validate_device_id(device_id):
                raise ValueError(f"Invalid device ID format: {device_id}")
            
            # Delete from database
            result = await self.repository.delete(device_id, org_id)
            
            # Remove from cache
            cache_key = self._get_cache_key(device_id, org_id)
            await self.cache.delete(cache_key)
            
            # Clear related cache patterns
            await self.cache.clear_pattern(f"org:{org_id}:devices:*")
            
            logger.info(f"Device deleted: {device_id}")
            
            # Audit log the deletion
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DELETED,
                    user=user,
                    device_id=device_id,
                    device_name=device_info.get("name") if device_info else None,
                    device_type=device_info.get("device_type") if device_info else None,
                    details={
                        "device_info": device_info,
                        "cascaded_deletions": ["cache", "related_patterns"]
                    },
                    status="success",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    compliance_flags=["GDPR", "DATA_DELETION"],
                    data_sensitivity="high"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DELETED,
                    user=user,
                    device_id=device_id,
                    device_name=device_info.get("name") if device_info else None,
                    device_type=device_info.get("device_type") if device_info else None,
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_list",
        module="device_management",
        operation="list"
    )
    async def list_devices(self, filters: Dict[str, Any], pagination: Dict[str, int], org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """List devices with filters and pagination"""
        try:
            # Validate filters
            validated_filters = self.validator.validate_filters(filters)
            
            # Add org_id to filters
            validated_filters["org_id"] = org_id
            
            # Get pagination parameters
            skip = (pagination.get("page", 1) - 1) * pagination.get("page_size", 20)
            limit = pagination.get("page_size", 20)
            
            # Check cache for this query
            cache_key = self._get_list_cache_key(validated_filters, skip, limit, org_id)
            cached_result = await self.cache.get(cache_key)
            
            if cached_result:
                logger.debug("Device list found in cache")
                return cached_result
            
            # Get from database
            devices = await self.repository.find_many(validated_filters, skip, limit, org_id)
            
            # Cache the result (shorter TTL for lists)
            await self.cache.set(cache_key, devices, ttl=60)
            
            # Audit log device listing
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_LISTED,
                    user=user,
                    details={
                        "filters": validated_filters,
                        "pagination": pagination,
                        "result_count": len(devices),
                        "from_cache": bool(cached_result)
                    },
                    status="success",
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return devices
            
        except Exception as e:
            logger.error(f"Error listing devices: {str(e)}")
            
            # Audit log the failure
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_LISTED,
                    user=user,
                    details={"filters": filters, "pagination": pagination},
                    status="failure",
                    error_message=str(e),
                    ip_address=ip_address
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_get_status",
        module="device_management",
        operation="read"
    )
    async def get_device_status(self, device_id: str, org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """Get current device status"""
        try:
            # Get device first
            device = await self.get_device(device_id, org_id)
            
            if not device:
                raise ValueError(f"Device not found: {device_id}")
            
            # Get real-time status from cache (Redis)
            status_key = f"org:{org_id}:device:{device_id}:status"
            real_time_status = await self.cache.get(status_key)
            
            # Combine device info with real-time status
            status = {
                "device_id": device_id,
                "status": real_time_status.get("status") if real_time_status else device.get("status"),
                "last_seen": real_time_status.get("last_seen") if real_time_status else device.get("last_seen"),
                "online": real_time_status.get("online", False) if real_time_status else False,
                "metrics": real_time_status.get("metrics", {}) if real_time_status else {},
                "alerts": real_time_status.get("alerts", []) if real_time_status else []
            }
            
            # Audit log status access
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_DATA_ACCESSED,
                    user=user,
                    device_id=device_id,
                    device_name=device.get("name"),
                    device_type=device.get("device_type"),
                    details={
                        "data_type": "status",
                        "has_real_time_data": bool(real_time_status),
                        "online_status": status.get("online")
                    },
                    status="success",
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting device status {device_id}: {str(e)}")
            raise
    
    @track_dashboard_method(
        method_name="device_update_status",
        module="device_management",
        operation="update"
    )
    async def update_device_status(self, device_id: str, status: Dict[str, Any], org_id: str, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> bool:
        """Update device status"""
        start_time = time.time()
        old_status = None
        
        try:
            # Get current status for audit comparison
            status_key = f"org:{org_id}:device:{device_id}:status"
            old_status = await self.cache.get(status_key) if self.cache else None
            # Validate device ID
            if not self.validator.validate_device_id(device_id):
                raise ValueError(f"Invalid device ID format: {device_id}")
            
            # Update real-time status in cache
            status_key = f"org:{org_id}:device:{device_id}:status"
            status_data = {
                "status": status.get("status"),
                "last_seen": datetime.utcnow().isoformat(),
                "online": status.get("online", True),
                "metrics": status.get("metrics", {}),
                "alerts": status.get("alerts", [])
            }
            
            # Set with longer TTL for status
            await self.cache.set(status_key, status_data, ttl=600)
            
            # Update last_seen in database (async, don't wait)
            # This is a fire-and-forget operation
            await self.repository.update(
                device_id,
                {"last_seen": datetime.utcnow(), "status": status.get("status")},
                org_id
            )
            
            logger.debug(f"Device status updated: {device_id}")
            
            # Audit log status change
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_STATUS_CHANGED,
                    user=user,
                    device_id=device_id,
                    details={
                        "old_status": old_status.get("status") if old_status else None,
                        "new_status": status.get("status"),
                        "online_status": status.get("online"),
                        "alerts_count": len(status.get("alerts", [])),
                        "metrics_updated": bool(status.get("metrics"))
                    },
                    status="success",
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating device status {device_id}: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_STATUS_CHANGED,
                    user=user,
                    device_id=device_id,
                    details={"attempted_status": status.get("status")},
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address
                )
            
            raise
    
    def _get_cache_key(self, device_id: str, org_id: str) -> str:
        """Generate cache key for device"""
        return f"org:{org_id}:device:{device_id}"
    
    def _get_list_cache_key(self, filters: Dict[str, Any], skip: int, limit: int, org_id: str) -> str:
        """Generate cache key for device list query"""
        # Create a deterministic key from filters
        filter_str = ":".join([f"{k}={v}" for k, v in sorted(filters.items())])
        return f"org:{org_id}:devices:list:{filter_str}:skip={skip}:limit={limit}"
    
    @track_dashboard_method(
        method_name="device_advanced_query",
        module="device_management",
        operation="advanced_query"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def query_devices(self, query: DeviceQuery, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> QueryResult:
        """
        Execute advanced device query
        
        Args:
            query: DeviceQuery object with complex conditions
            user: User executing the query
            ip_address: Client IP address
            
        Returns:
            QueryResult with devices and metadata
        """
        start_time = time.time()
        
        try:
            # Validate query
            query.validate()
            
            # Convert to MongoDB query
            mongo_query = query.to_mongo_query()
            sort_spec = query.get_sort_spec()
            
            # Apply cursor-based pagination if cursor is provided
            if query.pagination.cursor:
                cursor_data = self.query_builder.decode_cursor(query.pagination.cursor)
                mongo_query = self.query_builder.apply_cursor_to_query(
                    mongo_query, cursor_data, query.sort_options
                )
            
            # Get projection
            projection = query.options.get_projection()
            
            # Log query for debugging (without sensitive data)
            logger.debug(f"Executing advanced query for org {query.org_id}")
            
            # Execute query
            if hasattr(self.repository, 'find_with_options'):
                # Use advanced find method if available
                devices = await self.repository.find_with_options(
                    query=mongo_query,
                    projection=projection,
                    sort=sort_spec,
                    skip=0 if query.pagination.cursor else (query.pagination.page - 1) * query.pagination.page_size if query.pagination.page else 0,
                    limit=query.pagination.page_size + 1,  # Get one extra to check if there are more
                    timeout_ms=query.options.timeout_ms
                )
            else:
                # Fallback to basic find_many
                skip = 0 if query.pagination.cursor else (query.pagination.page - 1) * query.pagination.page_size if query.pagination.page else 0
                devices = await self.repository.find_many(
                    filters=mongo_query,
                    skip=skip,
                    limit=query.pagination.page_size + 1,
                    org_id=query.org_id
                )
            
            # Check if there are more results
            has_more = len(devices) > query.pagination.page_size
            if has_more:
                devices = devices[:query.pagination.page_size]
            
            # Generate next cursor if needed
            next_cursor = None
            if has_more and devices:
                last_device = devices[-1]
                sort_fields = [opt.field for opt in query.sort_options]
                next_cursor = self.query_builder.encode_cursor(last_device, sort_fields)
            
            # Get total count if requested
            total_count = None
            if query.options.include_count:
                total_count = await self.repository.count(mongo_query, query.org_id)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create result
            result = QueryResult(
                items=devices,
                total_count=total_count,
                next_cursor=next_cursor,
                has_more=has_more,
                execution_time_ms=execution_time_ms
            )
            
            # Audit log the query
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_QUERIED,
                    user=user,
                    details={
                        "query_complexity": self._calculate_query_complexity(query),
                        "result_count": len(devices),
                        "has_cursor": bool(query.pagination.cursor),
                        "execution_time_ms": execution_time_ms,
                        "includes_count": query.options.include_count
                    },
                    status="success",
                    operation_duration_ms=execution_time_ms,
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing advanced query: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_QUERIED,
                    user=user,
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address
                )
            
            raise
    
    @track_dashboard_method(
        method_name="device_aggregate",
        module="device_management",
        operation="aggregation"
    )
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def aggregate_devices(self, aggregation: AggregationQuery, user: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Execute device aggregation query
        
        Args:
            aggregation: AggregationQuery object
            user: User executing the query
            ip_address: Client IP address
            
        Returns:
            List of aggregation results
        """
        start_time = time.time()
        
        try:
            # Convert to MongoDB pipeline
            pipeline = aggregation.to_mongo_pipeline()
            
            # Log aggregation for debugging
            logger.debug(f"Executing aggregation for org {aggregation.org_id}")
            
            # Execute aggregation
            if hasattr(self.repository, 'aggregate'):
                results = await self.repository.aggregate(pipeline)
            else:
                # Fallback error if repository doesn't support aggregation
                raise NotImplementedError("Repository does not support aggregation")
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Audit log the aggregation
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_AGGREGATED,
                    user=user,
                    details={
                        "group_by": aggregation.group_by,
                        "metrics": aggregation.metrics,
                        "result_count": len(results),
                        "execution_time_ms": execution_time_ms
                    },
                    status="success",
                    operation_duration_ms=execution_time_ms,
                    ip_address=ip_address,
                    data_sensitivity="low"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing aggregation: {str(e)}")
            
            # Audit log the failure
            if user:
                duration_ms = (time.time() - start_time) * 1000
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_AGGREGATED,
                    user=user,
                    status="failure",
                    error_message=str(e),
                    operation_duration_ms=duration_ms,
                    ip_address=ip_address
                )
            
            raise
    
    def _calculate_query_complexity(self, query: DeviceQuery) -> int:
        """Calculate query complexity score"""
        complexity = 0
        
        # Base complexity for filters
        if query.device_types:
            complexity += len(query.device_types)
        if query.statuses:
            complexity += len(query.statuses)
        if query.tags:
            complexity += len(query.tags) * 2
        
        # Complex conditions add more complexity
        if query.conditions:
            complexity += self._count_conditions(query.conditions) * 3
        
        # Date ranges
        if query.created_date_range:
            complexity += 2
        if query.updated_date_range:
            complexity += 2
        if query.last_seen_date_range:
            complexity += 2
        
        # Location filter is expensive
        if query.location_filter:
            complexity += 5
        
        # Text search
        if query.text_search:
            complexity += len(query.text_search_fields) * 2
        
        return complexity
    
    def _count_conditions(self, condition) -> int:
        """Recursively count conditions"""
        if hasattr(condition, 'conditions'):
            return 1 + sum(self._count_conditions(c) for c in condition.conditions)
        return 1
    
    def set_bulk_operations_service(self, bulk_service):
        """Set the bulk operations service instance"""
        self._bulk_operations_service = bulk_service
    
    # Bulk Operations Methods
    async def bulk_create_devices(
        self,
        request: BulkCreateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """Initiate bulk device creation"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.bulk_create_devices(
            request, org_id, user, ip_address, user_agent
        )
    
    async def bulk_update_devices(
        self,
        request: BulkUpdateRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """Initiate bulk device update"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.bulk_update_devices(
            request, org_id, user, ip_address, user_agent
        )
    
    async def bulk_delete_devices(
        self,
        request: BulkDeleteRequest,
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> BulkOperationResponse:
        """Initiate bulk device deletion"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.bulk_delete_devices(
            request, org_id, user, ip_address, user_agent
        )
    
    async def get_bulk_operation_progress(
        self,
        operation_id: str,
        org_id: str
    ) -> Optional[BulkOperationProgress]:
        """Get progress of a bulk operation"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.get_operation_progress(
            operation_id, org_id
        )
    
    async def get_bulk_operation_result(
        self,
        operation_id: str,
        org_id: str,
        include_details: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get result of a bulk operation"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.get_operation_result(
            operation_id, org_id, include_details
        )
    
    async def cancel_bulk_operation(
        self,
        operation_id: str,
        org_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Cancel an in-progress bulk operation"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.cancel_operation(
            operation_id, org_id, user
        )
    
    async def list_bulk_operations(
        self,
        filter_params: BulkOperationFilter,
        org_id: str
    ) -> List[Dict[str, Any]]:
        """List bulk operations with filtering"""
        if not self._bulk_operations_service:
            raise RuntimeError("Bulk operations service not initialized")
        
        return await self._bulk_operations_service.list_operations(
            filter_params, org_id
        )
    
    # Template-based device creation
    async def register_device_from_template(
        self,
        template_id: str,
        device_data: Dict[str, Any],
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a device using a template
        
        Args:
            template_id: ID of the template to use
            device_data: Device-specific data and overrides
            org_id: Organization ID
            user: User creating the device
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Created device dictionary
        """
        # This method will be called by the template service
        # The template service handles merging template defaults with device data
        # and validation against template schema
        return await self.register_device(
            device_data=device_data,
            org_id=org_id,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def get_device_template_info(self, device_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get template information for a device if it was created from a template
        
        Args:
            device_id: Device ID
            org_id: Organization ID
            
        Returns:
            Template information including template_id and version
        """
        # This will be implemented by checking template instances
        # For now, return None as template repository handles this
        return None
    
    # Group-related operations
    async def update_device_groups(
        self,
        device_id: str,
        group_ids: List[str],
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        operation: str = "set"  # set, add, remove
    ) -> Dict[str, Any]:
        """
        Update device group membership
        
        Args:
            device_id: Device ID
            group_ids: List of group IDs
            org_id: Organization ID
            user: User performing the operation
            operation: Operation type - set (replace all), add, remove
            
        Returns:
            Updated device dictionary
        """
        try:
            # Get current device
            device = await self.get_device(device_id, org_id)
            if not device:
                raise ValidationError(f"Device {device_id} not found")
            
            current_groups = set(device.get("group_ids", []))
            
            # Calculate new group list based on operation
            if operation == "set":
                new_groups = set(group_ids)
            elif operation == "add":
                new_groups = current_groups.union(set(group_ids))
            elif operation == "remove":
                new_groups = current_groups.difference(set(group_ids))
            else:
                raise ValidationError(f"Invalid operation: {operation}")
            
            # Update device
            updates = {"group_ids": list(new_groups)}
            updated_device = await self.update_device(
                device_id=device_id,
                updates=updates,
                org_id=org_id,
                user=user
            )
            
            # Log group changes
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_GROUPS_UPDATED,
                    user=user,
                    device_id=device_id,
                    device_name=device.get("name"),
                    device_type=device.get("device_type"),
                    details={
                        "operation": operation,
                        "previous_groups": list(current_groups),
                        "new_groups": list(new_groups),
                        "added": list(new_groups - current_groups),
                        "removed": list(current_groups - new_groups)
                    },
                    status="success"
                )
            
            return updated_device
            
        except Exception as e:
            logger.error(f"Error updating device groups: {str(e)}")
            if user:
                await device_audit_service.log_device_operation(
                    action=DeviceAuditAction.DEVICE_GROUPS_UPDATED,
                    user=user,
                    device_id=device_id,
                    status="failure",
                    error_message=str(e)
                )
            raise
    
    async def get_devices_by_group(
        self,
        group_id: str,
        org_id: str,
        filters: Optional[Dict[str, Any]] = None,
        pagination: Optional[Dict[str, int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all devices in a specific group
        
        Args:
            group_id: Group ID
            org_id: Organization ID
            filters: Additional filters
            pagination: Pagination parameters
            
        Returns:
            List of devices in the group
        """
        # Build query
        query = {
            "org_id": org_id,
            "group_ids": group_id
        }
        
        # Add additional filters
        if filters:
            query.update(filters)
        
        # Default pagination
        if not pagination:
            pagination = {"skip": 0, "limit": 100}
        
        # Get devices
        devices = await self.repository.find_many(
            filters=query,
            skip=pagination.get("skip", 0),
            limit=pagination.get("limit", 100),
            org_id=org_id
        )
        
        return devices
    
    async def remove_device_from_all_groups(
        self,
        device_id: str,
        org_id: str,
        user: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Remove a device from all groups
        
        Args:
            device_id: Device ID
            org_id: Organization ID
            user: User performing the operation
            
        Returns:
            Updated device dictionary
        """
        return await self.update_device_groups(
            device_id=device_id,
            group_ids=[],
            org_id=org_id,
            user=user,
            operation="set"
        )
    
    async def batch_update_device_groups(
        self,
        device_ids: List[str],
        group_ids: List[str],
        org_id: str,
        user: Optional[Dict[str, Any]] = None,
        operation: str = "add"  # add or remove
    ) -> Dict[str, Any]:
        """
        Update group membership for multiple devices
        
        Args:
            device_ids: List of device IDs
            group_ids: List of group IDs
            org_id: Organization ID
            user: User performing the operation
            operation: Operation type - add or remove
            
        Returns:
            Summary of the operation
        """
        results = {
            "total": len(device_ids),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for device_id in device_ids:
            try:
                await self.update_device_groups(
                    device_id=device_id,
                    group_ids=group_ids,
                    org_id=org_id,
                    user=user,
                    operation=operation
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "device_id": device_id,
                    "error": str(e)
                })
                logger.error(f"Failed to update groups for device {device_id}: {str(e)}")
        
        return results