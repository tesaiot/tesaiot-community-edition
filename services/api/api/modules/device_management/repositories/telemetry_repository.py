# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import pymongo

from ..models.telemetry_models import TelemetryData, TelemetryAggregation, AggregationType
from ....core.database import get_db

logger = logging.getLogger(__name__)


class TelemetryRepository:
    """Repository for telemetry data persistence"""

    def __init__(self, db: Optional[Union[AsyncIOMotorDatabase, Any]] = None):
        """Initialize TelemetryRepository with optional database.

        Args:
            db: MongoDB database instance (Motor async or pymongo sync).
                If None, will lazy-load from get_db().
        """
        self._db = db
        self._collection = None
        self._aggregations_collection = None
        self._alerts_collection = None
        self._indexes_created = False

    @property
    def db(self):
        """Lazy-load database if not provided."""
        if self._db is None:
            self._db = get_db()
        return self._db

    @property
    def collection(self):
        """Lazy-load telemetry_data collection."""
        if self._collection is None and self.db is not None:
            self._collection = self.db.telemetry_data
            self._ensure_indexes()
        return self._collection

    @property
    def aggregations_collection(self):
        """Lazy-load telemetry_aggregations collection."""
        if self._aggregations_collection is None and self.db is not None:
            self._aggregations_collection = self.db.telemetry_aggregations
        return self._aggregations_collection

    @property
    def alerts_collection(self):
        """Lazy-load telemetry_alerts collection."""
        if self._alerts_collection is None and self.db is not None:
            self._alerts_collection = self.db.telemetry_alerts
        return self._alerts_collection

    def _ensure_indexes(self):
        """Create indexes if not already created."""
        if not self._indexes_created:
            self._create_indexes()
            self._indexes_created = True
    
    def _create_indexes(self):
        """Create database indexes for optimal query performance"""
        try:
            # Telemetry data indexes
            self.collection.create_index([
                ("device_id", pymongo.ASCENDING),
                ("org_id", pymongo.ASCENDING),
                ("received_at", pymongo.DESCENDING)
            ])
            self.collection.create_index([
                ("org_id", pymongo.ASCENDING),
                ("received_at", pymongo.DESCENDING)
            ])
            self.collection.create_index([
                ("telemetry_type", pymongo.ASCENDING),
                ("priority", pymongo.ASCENDING)
            ])
            
            # TTL index to automatically delete old data
            self.collection.create_index(
                "received_at",
                expireAfterSeconds=30 * 24 * 60 * 60  # 30 days
            )
            
            # Aggregations indexes
            self.aggregations_collection.create_index([
                ("device_id", pymongo.ASCENDING),
                ("metric_name", pymongo.ASCENDING),
                ("period_start", pymongo.DESCENDING)
            ])
            
            # Alerts indexes
            self.alerts_collection.create_index([
                ("device_id", pymongo.ASCENDING),
                ("is_active", pymongo.ASCENDING),
                ("triggered_at", pymongo.DESCENDING)
            ])
            
            logger.info("Telemetry repository indexes created")
            
        except Exception as e:
            logger.error(f"Error creating telemetry indexes: {str(e)}")
    
    async def store_telemetry(self, telemetry: TelemetryData) -> str:
        """Store telemetry data"""
        try:
            telemetry_dict = telemetry.to_dict()
            result = await self.collection.insert_one(telemetry_dict)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing telemetry: {str(e)}")
            raise
    
    async def store_telemetry_batch(self, telemetry_list: List[TelemetryData]) -> List[str]:
        """Store multiple telemetry records in batch"""
        try:
            documents = [t.to_dict() for t in telemetry_list]
            result = await self.collection.insert_many(documents)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error storing telemetry batch: {str(e)}")
            raise
    
    async def get_telemetry(
        self,
        device_id: str,
        org_id: str,
        start_time: datetime,
        end_time: datetime,
        telemetry_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get telemetry data for a device within time range"""
        try:
            query = {
                "device_id": device_id,
                "org_id": org_id,
                "received_at": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }
            
            if telemetry_type:
                query["telemetry_type"] = telemetry_type
            
            cursor = self.collection.find(query).sort("received_at", pymongo.DESCENDING).limit(limit)
            
            results = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting telemetry: {str(e)}")
            raise
    
    async def get_latest_telemetry(
        self,
        device_id: str,
        org_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get latest telemetry data for a device"""
        try:
            query = {
                "device_id": device_id,
                "org_id": org_id
            }
            
            cursor = self.collection.find(query).sort("received_at", pymongo.DESCENDING).limit(limit)
            
            results = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting latest telemetry: {str(e)}")
            raise
    
    async def aggregate_telemetry(
        self,
        device_id: str,
        org_id: str,
        metric_name: str,
        aggregation_type: AggregationType,
        start_time: datetime,
        end_time: datetime,
        interval_minutes: int
    ) -> List[TelemetryAggregation]:
        """Aggregate telemetry data over time intervals"""
        try:
            # Build aggregation pipeline
            pipeline = [
                # Match documents
                {
                    "$match": {
                        "device_id": device_id,
                        "org_id": org_id,
                        "received_at": {
                            "$gte": start_time,
                            "$lte": end_time
                        }
                    }
                },
                # Unwind data points
                {"$unwind": "$data_points"},
                # Filter by metric if specified
                {
                    "$match": {
                        "data_points.metadata.metric_name": metric_name
                    } if metric_name else {"$match": {}}
                },
                # Group by time interval
                {
                    "$group": {
                        "_id": {
                            "$dateToString": {
                                "date": "$received_at",
                                "format": "%Y-%m-%d %H:%M",
                                "timezone": "UTC"
                            }
                        },
                        "values": {"$push": "$data_points.value"},
                        "count": {"$sum": 1},
                        "min": {"$min": "$data_points.value"},
                        "max": {"$max": "$data_points.value"},
                        "sum": {"$sum": "$data_points.value"},
                        "unit": {"$first": "$data_points.unit"}
                    }
                },
                # Sort by time
                {"$sort": {"_id": 1}}
            ]
            
            cursor = self.collection.aggregate(pipeline)
            
            aggregations = []
            async for doc in cursor:
                # Calculate aggregated value based on type
                if aggregation_type == AggregationType.AVERAGE:
                    value = doc["sum"] / doc["count"] if doc["count"] > 0 else 0
                elif aggregation_type == AggregationType.SUM:
                    value = doc["sum"]
                elif aggregation_type == AggregationType.MIN:
                    value = doc["min"]
                elif aggregation_type == AggregationType.MAX:
                    value = doc["max"]
                elif aggregation_type == AggregationType.COUNT:
                    value = doc["count"]
                else:
                    value = doc["values"][-1] if doc["values"] else 0  # LAST
                
                # Parse timestamp
                timestamp = datetime.strptime(doc["_id"], "%Y-%m-%d %H:%M")
                
                aggregation = TelemetryAggregation(
                    device_id=device_id,
                    org_id=org_id,
                    metric_name=metric_name or "all",
                    aggregation_type=aggregation_type,
                    period_start=timestamp,
                    period_end=timestamp + timedelta(minutes=interval_minutes),
                    value=value,
                    unit=doc.get("unit"),
                    sample_count=doc["count"],
                    min_value=doc["min"],
                    max_value=doc["max"]
                )
                
                aggregations.append(aggregation)
            
            return aggregations
            
        except Exception as e:
            logger.error(f"Error aggregating telemetry: {str(e)}")
            raise
    
    async def store_aggregation(self, aggregation: TelemetryAggregation) -> str:
        """Store pre-computed aggregation"""
        try:
            agg_dict = aggregation.to_dict()
            result = await self.aggregations_collection.insert_one(agg_dict)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing aggregation: {str(e)}")
            raise
    
    async def get_device_telemetry_stats(
        self,
        device_id: str,
        org_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get telemetry statistics for a device"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            pipeline = [
                {
                    "$match": {
                        "device_id": device_id,
                        "org_id": org_id,
                        "received_at": {"$gte": start_time}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_messages": {"$sum": 1},
                        "total_data_points": {"$sum": {"$size": "$data_points"}},
                        "telemetry_types": {"$addToSet": "$telemetry_type"},
                        "priorities": {"$addToSet": "$priority"},
                        "first_message": {"$min": "$received_at"},
                        "last_message": {"$max": "$received_at"}
                    }
                }
            ]
            
            cursor = self.collection.aggregate(pipeline)
            result = await cursor.to_list(length=1)
            
            if result:
                stats = result[0]
                stats.pop("_id", None)
                return stats
            else:
                return {
                    "total_messages": 0,
                    "total_data_points": 0,
                    "telemetry_types": [],
                    "priorities": [],
                    "first_message": None,
                    "last_message": None
                }
                
        except Exception as e:
            logger.error(f"Error getting device telemetry stats: {str(e)}")
            raise
    
    async def cleanup_old_telemetry(self, days: int = 30) -> int:
        """Clean up telemetry data older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            result = await self.collection.delete_many({
                "received_at": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old telemetry records")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old telemetry: {str(e)}")
            raise