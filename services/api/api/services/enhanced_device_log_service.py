# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Enhanced Device Log Service
Version: v2026.01
Build: 2026-01-09
Module: Device Logs Improvement Feature

This service provides enhanced device logging functionality with:
- Category-based filtering (security, mqtt, csr, telemetry, command, system)
- Level-based filtering (TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL)
- Correlation ID tracking for distributed tracing
- Regex search support
- Real-time WebSocket broadcasting
- 30-day TTL with automatic cleanup
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..core.database import get_db
from ..models.device_log_enhanced import (
    EnhancedDeviceLog,
    EnhancedDeviceLogCreate,
    EnhancedDeviceLogResponse,
    EnhancedDeviceLogListResponse,
    LogFilterParams,
    LogLevel,
    LogCategory,
    LogSource,
    generate_correlation_id
)

logger = logging.getLogger(__name__)


class EnhancedDeviceLogService:
    """Service for managing enhanced device logs"""

    COLLECTION_NAME = "device_logs_enhanced"

    # Phase 1 category mapping
    PHASE1_CATEGORY_MAPPING = {
        LogCategory.SECURITY: "USER_CRITICAL",
        LogCategory.MQTT: "API_PROBLEMS",
        LogCategory.CSR: "DEVICE_ISSUES",
        LogCategory.TELEMETRY: "API_PROBLEMS",
        LogCategory.COMMAND: "API_PROBLEMS",
        LogCategory.SYSTEM: "DEVICE_ISSUES",
        LogCategory.CONNECTIVITY: "DEVICE_ISSUES"
    }

    @staticmethod
    def _get_collection():
        """Get the MongoDB collection"""
        db = get_db()
        if db is None:
            raise Exception("Database connection not available")
        return db[EnhancedDeviceLogService.COLLECTION_NAME]

    @staticmethod
    async def add_enhanced_log(log_entry: EnhancedDeviceLogCreate) -> Dict[str, Any]:
        """
        Add a new enhanced log entry AND broadcast to WebSocket clients.

        Phase 5.1: Log Persistence & Real-time Broadcasting
        - Persists log to MongoDB for historical access
        - Broadcasts to active WebSocket connections for real-time streaming

        Args:
            log_entry: Log entry to add

        Returns:
            Created log entry with _id
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            # Create the full log entry
            full_log = EnhancedDeviceLog(
                device_id=log_entry.device_id,
                timestamp=datetime.utcnow(),
                level=log_entry.level,
                category=log_entry.category,
                source=log_entry.source,
                event_type=log_entry.event_type,
                message=log_entry.message,
                correlation_id=log_entry.correlation_id,
            )

            # Add details if provided
            if log_entry.details:
                full_log.details = log_entry.details

            # Add error if provided
            if log_entry.error:
                full_log.error = log_entry.error

            # Convert to MongoDB document
            doc = full_log.to_mongo_dict()

            # Insert to MongoDB
            result = collection.insert_one(doc)

            doc['_id'] = str(result.inserted_id)

            logger.debug(f"Added enhanced log for device {log_entry.device_id}: {log_entry.event_type}")

            # Phase 5.1: Broadcast to WebSocket clients (real-time streaming)
            try:
                from ..controllers.device_logs_ws import broadcast_device_log

                # Convert timestamp to ISO format for JSON serialization
                broadcast_entry = {
                    'level': log_entry.level.value if hasattr(log_entry.level, 'value') else str(log_entry.level),
                    'category': log_entry.category.value if hasattr(log_entry.category, 'value') else str(log_entry.category),
                    'source': log_entry.source.value if hasattr(log_entry.source, 'value') else str(log_entry.source),
                    'event_type': log_entry.event_type,
                    'message': log_entry.message,
                    'correlation_id': log_entry.correlation_id,
                    'details': log_entry.details,
                    'error': log_entry.error,
                    'timestamp': full_log.timestamp.isoformat()
                }

                # Broadcast to active WebSocket connections
                broadcast_device_log(log_entry.device_id, broadcast_entry)

            except Exception as broadcast_error:
                # Non-critical: Log was saved to MongoDB, broadcasting failed is acceptable
                logger.warning(f"Failed to broadcast log to WebSocket (non-critical): {broadcast_error}")

            return doc

        except Exception as e:
            logger.error(f"Error adding enhanced log: {e}")
            raise

    @staticmethod
    async def add_log_sync(
        device_id: str,
        event_type: str,
        message: str,
        level: LogLevel = LogLevel.INFO,
        category: LogCategory = LogCategory.SYSTEM,
        source: LogSource = LogSource.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous helper to add a log entry.

        Args:
            device_id: Device identifier
            event_type: Type of event (e.g., 'mqtt_connect', 'csr_received')
            message: Log message
            level: Log severity level
            category: Log category
            source: Source of the event
            details: Additional details
            correlation_id: Correlation ID for tracing
            error: Error information if applicable

        Returns:
            Created log entry
        """
        log_entry = EnhancedDeviceLogCreate(
            device_id=device_id,
            level=level,
            category=category,
            source=source,
            event_type=event_type,
            message=message,
            details=details,
            correlation_id=correlation_id,
            error=error
        )
        return await EnhancedDeviceLogService.add_enhanced_log(log_entry)

    @staticmethod
    async def get_logs(
        device_id: str,
        filters: Optional[LogFilterParams] = None,
        organization_id: Optional[str] = None
    ) -> EnhancedDeviceLogListResponse:
        """
        Get enhanced logs for a device with filtering.

        Args:
            device_id: Device identifier
            filters: Filter parameters
            organization_id: Organization ID for access control

        Returns:
            List of logs with pagination info
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            # Build query
            query: Dict[str, Any] = {"device_id": device_id}

            if organization_id:
                query["organization_id"] = organization_id

            if filters:
                # Category filter
                if filters.categories:
                    query["category"] = {"$in": [c.value for c in filters.categories]}

                # Level filter
                if filters.levels:
                    query["level"] = {"$in": [l.value for l in filters.levels]}

                # Source filter
                if filters.sources:
                    query["source"] = {"$in": [s.value for s in filters.sources]}

                # Event type filter
                if filters.event_types:
                    query["event_type"] = {"$in": filters.event_types}

                # Time range filter
                if filters.from_time or filters.to_time:
                    query["timestamp"] = {}
                    if filters.from_time:
                        query["timestamp"]["$gte"] = filters.from_time
                    if filters.to_time:
                        query["timestamp"]["$lte"] = filters.to_time

                # Correlation ID filter
                if filters.correlation_id:
                    query["correlation_id"] = filters.correlation_id

                # Search filter (regex)
                if filters.search:
                    try:
                        # Try to compile as regex
                        regex_pattern = re.compile(filters.search, re.IGNORECASE)
                        query["$or"] = [
                            {"message": {"$regex": filters.search, "$options": "i"}},
                            {"event_type": {"$regex": filters.search, "$options": "i"}}
                        ]
                    except re.error:
                        # If invalid regex, use exact match
                        query["message"] = {"$regex": re.escape(filters.search), "$options": "i"}

            # Get total count
            total = collection.count_documents(query)

            # Set pagination defaults
            limit = filters.limit if filters else 100
            offset = filters.offset if filters else 0

            # Execute query with pagination
            cursor = collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)

            logs = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                logs.append(EnhancedDeviceLogResponse(**doc))

            return EnhancedDeviceLogListResponse(
                logs=logs,
                total=total,
                limit=limit,
                offset=offset,
                filters_applied={
                    "device_id": device_id,
                    "categories": [c.value for c in filters.categories] if filters and filters.categories else None,
                    "levels": [l.value for l in filters.levels] if filters and filters.levels else None,
                    "search": filters.search if filters else None
                }
            )

        except Exception as e:
            logger.error(f"Error getting enhanced logs: {e}")
            raise

    @staticmethod
    async def get_logs_by_correlation_id(correlation_id: str) -> List[Dict[str, Any]]:
        """
        Get all logs for a specific correlation ID.

        Args:
            correlation_id: Correlation ID to search

        Returns:
            List of logs sorted by timestamp
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            cursor = collection.find(
                {"correlation_id": correlation_id}
            ).sort("timestamp", 1)  # Ascending for chronological order

            logs = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                logs.append(doc)

            return logs

        except Exception as e:
            logger.error(f"Error getting logs by correlation ID: {e}")
            raise

    @staticmethod
    async def get_recent_errors(
        device_id: str,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent error logs for a device.

        Args:
            device_id: Device identifier
            hours: Number of hours to look back
            limit: Maximum number of errors to return

        Returns:
            List of error logs
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            since = datetime.utcnow() - timedelta(hours=hours)

            cursor = collection.find({
                "device_id": device_id,
                "level": {"$in": [LogLevel.ERROR.value, LogLevel.CRITICAL.value]},
                "timestamp": {"$gte": since}
            }).sort("timestamp", -1).limit(limit)

            logs = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                if 'timestamp' in doc and isinstance(doc['timestamp'], datetime):
                    doc['timestamp'] = doc['timestamp'].isoformat()
                logs.append(doc)

            return logs

        except Exception as e:
            logger.error(f"Error getting recent errors: {e}")
            raise

    @staticmethod
    async def get_log_statistics(
        device_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get log statistics for a device.

        Args:
            device_id: Device identifier
            hours: Number of hours to analyze

        Returns:
            Statistics including counts by level and category
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            since = datetime.utcnow() - timedelta(hours=hours)

            pipeline = [
                {
                    "$match": {
                        "device_id": device_id,
                        "timestamp": {"$gte": since}
                    }
                },
                {
                    "$facet": {
                        "by_level": [
                            {"$group": {"_id": "$level", "count": {"$sum": 1}}}
                        ],
                        "by_category": [
                            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
                        ],
                        "by_source": [
                            {"$group": {"_id": "$source", "count": {"$sum": 1}}}
                        ],
                        "total": [
                            {"$count": "count"}
                        ]
                    }
                }
            ]

            result = list(collection.aggregate(pipeline))

            if not result:
                return {
                    "device_id": device_id,
                    "period_hours": hours,
                    "total": 0,
                    "by_level": {},
                    "by_category": {},
                    "by_source": {}
                }

            data = result[0]

            return {
                "device_id": device_id,
                "period_hours": hours,
                "total": data["total"][0]["count"] if data["total"] else 0,
                "by_level": {item["_id"]: item["count"] for item in data["by_level"]},
                "by_category": {item["_id"]: item["count"] for item in data["by_category"]},
                "by_source": {item["_id"]: item["count"] for item in data["by_source"]},
                "analyzed_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting log statistics: {e}")
            raise

    @staticmethod
    async def delete_old_logs(days: int = 30) -> int:
        """
        Delete logs older than specified days.
        Note: This is a backup cleanup in addition to TTL index.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted logs
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            cutoff = datetime.utcnow() - timedelta(days=days)

            result = collection.delete_many({
                "timestamp": {"$lt": cutoff}
            })

            logger.info(f"Deleted {result.deleted_count} old enhanced logs")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Error deleting old logs: {e}")
            raise

    @staticmethod
    async def delete_device_logs(device_id: str) -> int:
        """
        Delete all logs for a specific device.

        Args:
            device_id: Device identifier

        Returns:
            Number of deleted logs
        """
        try:
            collection = EnhancedDeviceLogService._get_collection()

            result = collection.delete_many({
                "device_id": device_id
            })

            logger.info(f"Deleted {result.deleted_count} logs for device {device_id}")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Error deleting device logs: {e}")
            raise

    @staticmethod
    def generate_correlation_id(device_id: str, prefix: str = "log") -> str:
        """
        Generate a correlation ID for tracing.

        Args:
            device_id: Device identifier
            prefix: Prefix for the correlation ID (e.g., 'csr', 'mqtt')

        Returns:
            Correlation ID string
        """
        return generate_correlation_id(device_id, prefix)


# Convenience functions for quick logging
async def log_security_event(
    device_id: str,
    event_type: str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    error: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Log a security-related event"""
    return await EnhancedDeviceLogService.add_log_sync(
        device_id=device_id,
        event_type=event_type,
        message=message,
        level=level,
        category=LogCategory.SECURITY,
        source=LogSource.EMQX,
        details=details,
        correlation_id=correlation_id,
        error=error
    )


async def log_mqtt_event(
    device_id: str,
    event_type: str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """Log an MQTT-related event"""
    return await EnhancedDeviceLogService.add_log_sync(
        device_id=device_id,
        event_type=event_type,
        message=message,
        level=level,
        category=LogCategory.MQTT,
        source=LogSource.MQTT_BRIDGE,
        details=details,
        correlation_id=correlation_id
    )


async def log_csr_event(
    device_id: str,
    event_type: str,
    message: str,
    level: LogLevel = LogLevel.INFO,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    error: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Log a CSR workflow event"""
    return await EnhancedDeviceLogService.add_log_sync(
        device_id=device_id,
        event_type=event_type,
        message=message,
        level=level,
        category=LogCategory.CSR,
        source=LogSource.CSR_BRIDGE,
        details=details,
        correlation_id=correlation_id,
        error=error
    )


# Create service instance
enhanced_device_log_service = EnhancedDeviceLogService()
