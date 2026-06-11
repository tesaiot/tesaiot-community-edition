# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Audit Logging Service
Provides comprehensive audit logging for all device management operations

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import uuid
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from contextlib import asynccontextmanager

from ..models.audit_models import (
    DeviceAuditEntry, DeviceAuditAction, AuditSeverity, 
    AuditCategory, DeviceAuditSummary, DeviceAuditFilter,
    ComplianceReport
)
from ..interfaces.device_interfaces import IDeviceCacheRepository
from ....core.database import get_db
from ....services.audit_service import audit_service as platform_audit_service, AuditAction

logger = logging.getLogger(__name__)


class DeviceAuditLoggingService:
    """Service for comprehensive audit logging of device management operations"""
    
    def __init__(
        self,
        cache_repository: Optional[IDeviceCacheRepository] = None,
        batch_size: int = 100,
        flush_interval: int = 5
    ):
        self.cache = cache_repository
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.audit_buffer: List[DeviceAuditEntry] = []
        self._last_flush = time.time()
        self._flush_task = None
        self.db = get_db()
        self.collection = self.db.device_audit_logs if self.db is not None else None

        # Ensure collection exists with indexes
        if self.db is not None and 'device_audit_logs' not in self.db.list_collection_names():
            self._create_audit_collection()
    
    def _create_audit_collection(self):
        """Create audit collection with appropriate indexes"""
        try:
            self.db.create_collection('device_audit_logs')
            
            # Create indexes for efficient querying
            self.collection.create_index([("timestamp", -1)])
            self.collection.create_index([("organization_id", 1), ("timestamp", -1)])
            self.collection.create_index([("device.id", 1), ("timestamp", -1)])
            self.collection.create_index([("user.id", 1), ("timestamp", -1)])
            self.collection.create_index([("action", 1)])
            self.collection.create_index([("category", 1)])
            self.collection.create_index([("severity", 1)])
            self.collection.create_index([("operation.status", 1)])
            
            # Text index for search
            self.collection.create_index([("$**", "text")])
            
            logger.info("Created device_audit_logs collection with indexes")
        except Exception as e:
            logger.error(f"Failed to create audit collection: {e}")
    
    async def log_device_operation(
        self,
        action: DeviceAuditAction,
        user: Dict[str, Any],
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        operation_duration_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        compliance_flags: Optional[List[str]] = None,
        data_sensitivity: str = "low",
        parent_audit_id: Optional[str] = None
    ) -> str:
        """
        Log a device management operation with comprehensive context
        
        Returns:
            str: The audit entry ID
        """
        try:
            # Determine category and severity
            category = self._determine_category(action)
            severity = self._determine_severity(action, status)
            
            # Create audit entry
            audit_entry = DeviceAuditEntry(
                audit_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                action=action,
                category=category,
                severity=severity,
                user_id=str(user.get('_id', user.get('id', ''))),
                user_email=user.get('email', ''),
                user_role=user.get('role', ''),
                organization_id=user.get('organization_id', ''),
                device_id=device_id,
                device_name=device_name,
                device_type=device_type,
                operation_status=status,
                error_message=error_message,
                operation_duration_ms=operation_duration_ms,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id or user.get('session_id'),
                request_id=request_id,
                details=details or {},
                compliance_flags=compliance_flags or [],
                data_sensitivity=data_sensitivity,
                parent_audit_id=parent_audit_id
            )
            
            # Add to buffer for batch processing
            self.audit_buffer.append(audit_entry)
            
            # Flush if buffer is full or interval exceeded
            if len(self.audit_buffer) >= self.batch_size or \
               time.time() - self._last_flush > self.flush_interval:
                await self._flush_audit_buffer()
            
            # Also log to platform audit service for critical operations
            if severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
                self._log_to_platform_audit(action, user, device_id, details, status, ip_address, user_agent)
            
            # Cache recent audit entry for quick access
            if self.cache:
                cache_key = f"audit:device:{device_id}:recent"
                await self.cache.set(cache_key, audit_entry.to_dict(), ttl=3600)
            
            logger.debug(f"Logged device audit: {action.value} for device {device_id}")
            return audit_entry.audit_id
            
        except Exception as e:
            logger.error(f"Failed to log device operation: {e}")
            # Fallback to platform audit service
            self._log_to_platform_audit(action, user, device_id, details, "audit_failure", ip_address, user_agent)
            return ""
    
    async def _flush_audit_buffer(self):
        """Flush audit buffer to database"""
        if not self.audit_buffer or not self.collection:
            return
        
        try:
            # Convert entries to dictionaries
            entries = [entry.to_dict() for entry in self.audit_buffer]
            
            # Bulk insert
            result = self.collection.insert_many(entries)
            logger.debug(f"Flushed {len(result.inserted_ids)} audit entries to database")
            
            # Clear buffer
            self.audit_buffer.clear()
            self._last_flush = time.time()
            
        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {e}")
            # Keep entries in buffer for retry
    
    def _determine_category(self, action: DeviceAuditAction) -> AuditCategory:
        """Determine audit category based on action"""
        action_category_map = {
            # CRUD operations
            DeviceAuditAction.DEVICE_CREATED: AuditCategory.CRUD,
            DeviceAuditAction.DEVICE_UPDATED: AuditCategory.CRUD,
            DeviceAuditAction.DEVICE_DELETED: AuditCategory.CRUD,
            DeviceAuditAction.DEVICE_VIEWED: AuditCategory.CRUD,
            DeviceAuditAction.DEVICE_LISTED: AuditCategory.CRUD,
            
            # Status operations
            DeviceAuditAction.DEVICE_STATUS_CHANGED: AuditCategory.STATUS,
            DeviceAuditAction.DEVICE_ACTIVATED: AuditCategory.STATUS,
            DeviceAuditAction.DEVICE_DEACTIVATED: AuditCategory.STATUS,
            
            # Provisioning operations
            DeviceAuditAction.DEVICE_PROVISIONED: AuditCategory.PROVISIONING,
            DeviceAuditAction.DEVICE_BULK_PROVISIONED: AuditCategory.PROVISIONING,
            
            # Configuration operations
            DeviceAuditAction.DEVICE_CONFIG_UPDATED: AuditCategory.CONFIGURATION,
            DeviceAuditAction.DEVICE_CONFIG_APPLIED: AuditCategory.CONFIGURATION,
            
            # Security operations
            DeviceAuditAction.DEVICE_CERTIFICATE_GENERATED: AuditCategory.SECURITY,
            DeviceAuditAction.DEVICE_CERTIFICATE_REVOKED: AuditCategory.SECURITY,
            DeviceAuditAction.DEVICE_AUTH_FAILED: AuditCategory.SECURITY,
            DeviceAuditAction.DEVICE_UNAUTHORIZED_ACCESS: AuditCategory.SECURITY,
            
            # Command operations
            DeviceAuditAction.DEVICE_COMMAND_SENT: AuditCategory.COMMAND,
            DeviceAuditAction.DEVICE_COMMAND_COMPLETED: AuditCategory.COMMAND,
            
            # Group operations
            DeviceAuditAction.DEVICE_GROUP_ASSIGNED: AuditCategory.GROUP,
            DeviceAuditAction.DEVICE_GROUP_CREATED: AuditCategory.GROUP,
            
            # Data operations
            DeviceAuditAction.DEVICE_DATA_ACCESSED: AuditCategory.DATA,
            DeviceAuditAction.DEVICE_DATA_EXPORTED: AuditCategory.DATA,
        }
        
        return action_category_map.get(action, AuditCategory.CRUD)
    
    def _determine_severity(self, action: DeviceAuditAction, status: str) -> AuditSeverity:
        """Determine audit severity based on action and status"""
        if status in ["failure", "error"]:
            if action in [
                DeviceAuditAction.DEVICE_AUTH_FAILED,
                DeviceAuditAction.DEVICE_UNAUTHORIZED_ACCESS,
                DeviceAuditAction.DEVICE_COMPLIANCE_VIOLATION
            ]:
                return AuditSeverity.CRITICAL
            return AuditSeverity.ERROR
        
        # Security-related actions
        if action in [
            DeviceAuditAction.DEVICE_CERTIFICATE_REVOKED,
            DeviceAuditAction.DEVICE_CREDENTIALS_ROTATED,
            DeviceAuditAction.DEVICE_DATA_PURGED
        ]:
            return AuditSeverity.WARNING
        
        # Normal operations
        return AuditSeverity.INFO
    
    def _log_to_platform_audit(
        self,
        action: DeviceAuditAction,
        user: Dict[str, Any],
        device_id: Optional[str],
        details: Optional[Dict[str, Any]],
        status: str,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ):
        """Log to platform-wide audit service"""
        try:
            # Map device actions to platform actions
            platform_action_map = {
                DeviceAuditAction.DEVICE_CREATED: AuditAction.DEVICE_CREATE,
                DeviceAuditAction.DEVICE_UPDATED: AuditAction.DEVICE_UPDATE,
                DeviceAuditAction.DEVICE_DELETED: AuditAction.DEVICE_DELETE,
                DeviceAuditAction.DEVICE_VIEWED: AuditAction.DEVICE_VIEW,
                DeviceAuditAction.DEVICE_LISTED: AuditAction.DEVICE_LIST,
            }
            
            platform_action = platform_action_map.get(action, AuditAction.DEVICE_VIEW)
            
            platform_audit_service.log_action(
                action=platform_action,
                user=user,
                resource_type="device",
                resource_id=device_id,
                details=details,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Failed to log to platform audit: {e}")
    
    async def get_audit_logs(
        self,
        filter_criteria: DeviceAuditFilter
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs based on filter criteria"""
        try:
            if not self.collection:
                return []
            
            # Build query from filter
            query = filter_criteria.to_query()
            
            # Execute query with pagination
            cursor = self.collection.find(query)\
                .sort(filter_criteria.sort_by, -1 if filter_criteria.sort_order == "desc" else 1)\
                .skip(filter_criteria.offset)\
                .limit(filter_criteria.limit)
            
            logs = []
            async for log in cursor:
                log['_id'] = str(log['_id'])
                logs.append(log)
            
            return logs
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
    
    async def get_audit_summary(
        self,
        organization_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> DeviceAuditSummary:
        """Generate audit summary for reporting"""
        try:
            if not self.collection:
                return DeviceAuditSummary(
                    organization_id=organization_id,
                    start_date=start_date,
                    end_date=end_date
                )
            
            # Base query
            query = {
                "organization_id": organization_id,
                "timestamp": {"$gte": start_date, "$lte": end_date}
            }
            
            # Aggregation pipeline
            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": None,
                    "total_events": {"$sum": 1},
                    "total_failures": {"$sum": {"$cond": [{"$ne": ["$operation.status", "success"]}, 1, 0]}},
                    "security_events": {"$sum": {"$cond": [{"$eq": ["$category", "security"]}, 1, 0]}},
                    "compliance_violations": {"$sum": {"$cond": [{"$in": ["compliance_violation", "$compliance.flags"]}, 1, 0]}},
                    "avg_duration": {"$avg": "$operation.duration_ms"},
                    "max_duration": {"$max": "$operation.duration_ms"},
                    "events_by_action": {"$push": "$action"},
                    "events_by_category": {"$push": "$category"},
                    "events_by_severity": {"$push": "$severity"},
                    "events_by_user": {"$push": "$user.email"},
                    "events_by_device": {"$push": "$device.id"}
                }}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if not result:
                return DeviceAuditSummary(
                    organization_id=organization_id,
                    start_date=start_date,
                    end_date=end_date
                )
            
            data = result[0]
            
            # Process grouped data
            summary = DeviceAuditSummary(
                organization_id=organization_id,
                start_date=start_date,
                end_date=end_date,
                total_events=data['total_events'],
                total_failures=data['total_failures'],
                failure_rate=data['total_failures'] / data['total_events'] if data['total_events'] > 0 else 0,
                security_events=data['security_events'],
                compliance_violations=data['compliance_violations'],
                avg_operation_duration_ms=data['avg_duration'] or 0,
                max_operation_duration_ms=data['max_duration'] or 0
            )
            
            # Count occurrences
            for action in data['events_by_action']:
                summary.events_by_action[action] = summary.events_by_action.get(action, 0) + 1
            
            for category in data['events_by_category']:
                summary.events_by_category[category] = summary.events_by_category.get(category, 0) + 1
            
            for severity in data['events_by_severity']:
                summary.events_by_severity[severity] = summary.events_by_severity.get(severity, 0) + 1
            
            for user in data['events_by_user']:
                summary.events_by_user[user] = summary.events_by_user.get(user, 0) + 1
            
            for device in data['events_by_device']:
                if device:
                    summary.events_by_device[device] = summary.events_by_device.get(device, 0) + 1
            
            # Get top operations
            summary.top_actions = sorted(
                [{"action": k, "count": v} for k, v in summary.events_by_action.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
            
            summary.top_users = sorted(
                [{"user": k, "count": v} for k, v in summary.events_by_user.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
            
            summary.top_devices = sorted(
                [{"device": k, "count": v} for k, v in summary.events_by_device.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate audit summary: {e}")
            return DeviceAuditSummary(
                organization_id=organization_id,
                start_date=start_date,
                end_date=end_date
            )
    
    async def generate_compliance_report(
        self,
        organization_id: str,
        report_period: str
    ) -> ComplianceReport:
        """Generate compliance report based on audit data"""
        try:
            # Parse report period (e.g., "2024-Q1")
            year, quarter = report_period.split('-Q')
            quarter_start_month = (int(quarter) - 1) * 3 + 1
            start_date = datetime(int(year), quarter_start_month, 1)
            
            if quarter_start_month + 3 > 12:
                end_date = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(int(year), quarter_start_month + 3, 1) - timedelta(days=1)
            
            # Get audit summary
            summary = await self.get_audit_summary(organization_id, start_date, end_date)
            
            # Query specific compliance metrics
            gdpr_query = {
                "organization_id": organization_id,
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "compliance.flags": "GDPR"
            }
            
            gdpr_data_access = self.collection.count_documents({
                **gdpr_query,
                "action": DeviceAuditAction.DEVICE_DATA_ACCESSED.value
            })
            
            gdpr_data_deletion = self.collection.count_documents({
                **gdpr_query,
                "action": DeviceAuditAction.DEVICE_DATA_PURGED.value
            })
            
            # Security metrics
            failed_auth = self.collection.count_documents({
                "organization_id": organization_id,
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "action": DeviceAuditAction.DEVICE_AUTH_FAILED.value
            })
            
            unauthorized_access = self.collection.count_documents({
                "organization_id": organization_id,
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "action": DeviceAuditAction.DEVICE_UNAUTHORIZED_ACCESS.value
            })
            
            # Get compliance violations
            violations_cursor = self.collection.find({
                "organization_id": organization_id,
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "action": DeviceAuditAction.DEVICE_COMPLIANCE_VIOLATION.value
            }).limit(100)
            
            violations = []
            for violation in violations_cursor:
                violations.append({
                    "timestamp": violation['timestamp'].isoformat(),
                    "device_id": violation['device']['id'],
                    "details": violation['details']
                })
            
            # Generate report
            report = ComplianceReport(
                organization_id=organization_id,
                report_period=report_period,
                generated_at=datetime.utcnow(),
                total_operations=summary.total_events,
                compliant_operations=summary.total_events - summary.compliance_violations,
                compliance_rate=(summary.total_events - summary.compliance_violations) / summary.total_events if summary.total_events > 0 else 1.0,
                gdpr_data_access_logs=gdpr_data_access,
                gdpr_data_deletion_logs=gdpr_data_deletion,
                failed_auth_attempts=failed_auth,
                unauthorized_access_attempts=unauthorized_access,
                certificate_operations=summary.events_by_category.get(AuditCategory.SECURITY.value, 0),
                data_exports=summary.events_by_action.get(DeviceAuditAction.DEVICE_DATA_EXPORTED.value, 0),
                data_purges=summary.events_by_action.get(DeviceAuditAction.DEVICE_DATA_PURGED.value, 0),
                compliance_violations=violations
            )
            
            # Add recommendations
            if report.compliance_rate < 0.95:
                report.recommendations.append("Increase compliance monitoring and training")
            
            if failed_auth > 100:
                report.recommendations.append("Review authentication mechanisms and implement rate limiting")
            
            if unauthorized_access > 0:
                report.recommendations.append("Strengthen access controls and review permissions")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return ComplianceReport(
                organization_id=organization_id,
                report_period=report_period,
                generated_at=datetime.utcnow()
            )
    
    @asynccontextmanager
    async def audit_context(
        self,
        action: DeviceAuditAction,
        user: Dict[str, Any],
        device_id: Optional[str] = None,
        **kwargs
    ):
        """Context manager for automatic audit logging with timing"""
        start_time = time.time()
        audit_id = None
        
        try:
            # Log operation start
            audit_id = await self.log_device_operation(
                action=action,
                user=user,
                device_id=device_id,
                status="in_progress",
                **kwargs
            )
            
            yield audit_id
            
            # Log success
            duration_ms = (time.time() - start_time) * 1000
            await self.log_device_operation(
                action=action,
                user=user,
                device_id=device_id,
                status="success",
                operation_duration_ms=duration_ms,
                parent_audit_id=audit_id,
                **kwargs
            )
            
        except Exception as e:
            # Log failure
            duration_ms = (time.time() - start_time) * 1000
            await self.log_device_operation(
                action=action,
                user=user,
                device_id=device_id,
                status="failure",
                error_message=str(e),
                operation_duration_ms=duration_ms,
                parent_audit_id=audit_id,
                **kwargs
            )
            raise
    
    def audit_device_operation(
        self,
        action: DeviceAuditAction,
        track_duration: bool = True,
        **audit_kwargs
    ):
        """Decorator for automatic audit logging of device operations"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time() if track_duration else None
                
                # Extract context from function arguments
                user = kwargs.get('user') or (args[1] if len(args) > 1 else None)
                device_id = kwargs.get('device_id') or (args[2] if len(args) > 2 else None)
                
                try:
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Log success
                    duration_ms = (time.time() - start_time) * 1000 if track_duration else None
                    await self.log_device_operation(
                        action=action,
                        user=user,
                        device_id=device_id,
                        status="success",
                        operation_duration_ms=duration_ms,
                        details={"function": func.__name__},
                        **audit_kwargs
                    )
                    
                    return result
                    
                except Exception as e:
                    # Log failure
                    duration_ms = (time.time() - start_time) * 1000 if track_duration else None
                    await self.log_device_operation(
                        action=action,
                        user=user,
                        device_id=device_id,
                        status="failure",
                        error_message=str(e),
                        operation_duration_ms=duration_ms,
                        details={"function": func.__name__, "error_type": type(e).__name__},
                        **audit_kwargs
                    )
                    raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For synchronous functions, create event loop if needed
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_wrapper(*args, **kwargs))
            
            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator
    
    async def cleanup(self):
        """Cleanup resources and flush remaining audit entries"""
        try:
            # Flush any remaining entries
            if self.audit_buffer:
                await self._flush_audit_buffer()
            
            # Cancel flush task if running
            if self._flush_task:
                self._flush_task.cancel()
                
        except Exception as e:
            logger.error(f"Error during audit service cleanup: {e}")


# Global instance
device_audit_service = DeviceAuditLoggingService()

# Convenience decorators
audit_device_create = lambda **kwargs: device_audit_service.audit_device_operation(
    DeviceAuditAction.DEVICE_CREATED, **kwargs
)

audit_device_update = lambda **kwargs: device_audit_service.audit_device_operation(
    DeviceAuditAction.DEVICE_UPDATED, **kwargs
)

audit_device_delete = lambda **kwargs: device_audit_service.audit_device_operation(
    DeviceAuditAction.DEVICE_DELETED, **kwargs
)

audit_device_view = lambda **kwargs: device_audit_service.audit_device_operation(
    DeviceAuditAction.DEVICE_VIEWED, track_duration=False, **kwargs
)

audit_device_security = lambda action: device_audit_service.audit_device_operation(
    action, data_sensitivity="high", compliance_flags=["SECURITY"]
)

# Backward-compatibility alias
AuditLoggingService = DeviceAuditLoggingService