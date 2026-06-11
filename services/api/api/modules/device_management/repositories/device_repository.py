# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId
import pymongo

from ..interfaces.device_interfaces import IDeviceRepository
from ....core.database import get_db
from ...dashboard.utils.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class DeviceRepository(IDeviceRepository):
    """MongoDB implementation of Device Repository"""
    
    def __init__(self, collection_name: str = "devices"):
        self.collection_name = collection_name
        logger.info(f"DeviceRepository initialized with collection: {collection_name}")
    
    def _get_collection(self):
        """Get MongoDB collection"""
        db = get_db()
        if db is None:
            raise ConnectionError("Database connection not available")
        return db[self.collection_name]
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def create(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create device in database"""
        try:
            collection = self._get_collection()
            
            # Ensure _id is ObjectId
            if "_id" not in device_data:
                device_data["_id"] = ObjectId()
            
            # Insert device
            result = collection.insert_one(device_data)
            
            # Return created device
            created_device = collection.find_one({"_id": result.inserted_id})
            return self._serialize_document(created_device)
            
        except Exception as e:
            logger.error(f"Error creating device: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def find_by_id(self, device_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        """Find device by ID"""
        try:
            collection = self._get_collection()
            
            # Query with both device_id and org_id for security
            device = collection.find_one({
                "device_id": device_id,
                "org_id": org_id
            })
            
            return self._serialize_document(device) if device else None
            
        except Exception as e:
            logger.error(f"Error finding device {device_id}: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def update(self, device_id: str, updates: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Update device in database"""
        try:
            collection = self._get_collection()
            
            # Remove _id from updates if present
            updates.pop("_id", None)
            
            # Update device
            result = collection.find_one_and_update(
                {"device_id": device_id, "org_id": org_id},
                {"$set": updates},
                return_document=pymongo.ReturnDocument.AFTER
            )
            
            if not result:
                raise ValueError(f"Device not found: {device_id}")
            
            return self._serialize_document(result)
            
        except Exception as e:
            logger.error(f"Error updating device {device_id}: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def delete(self, device_id: str, org_id: str) -> bool:
        """Delete device from database"""
        try:
            collection = self._get_collection()
            
            # Delete device
            result = collection.delete_one({
                "device_id": device_id,
                "org_id": org_id
            })
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def find_many(self, filters: Dict[str, Any], skip: int, limit: int, org_id: str) -> List[Dict[str, Any]]:
        """Find multiple devices with pagination"""
        try:
            collection = self._get_collection()
            
            # Build query
            query = {"org_id": org_id}
            
            # Add filters
            if filters.get("status"):
                query["status"] = filters["status"]
            
            if filters.get("device_type"):
                query["device_type"] = filters["device_type"]
            
            if filters.get("protocol"):
                query["protocol"] = filters["protocol"]
            
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            
            if filters.get("group_id"):
                query["group_ids"] = filters["group_id"]
            
            if filters.get("search"):
                # Search in name and serial number
                search_regex = {"$regex": filters["search"], "$options": "i"}
                query["$or"] = [
                    {"name": search_regex},
                    {"serial_number": search_regex}
                ]
            
            # Sort order
            sort_field = filters.get("sort_by", "created_at")
            sort_order = pymongo.DESCENDING if filters.get("sort_order", "desc") == "desc" else pymongo.ASCENDING
            
            # Execute query with pagination
            cursor = collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
            
            # Convert to list
            devices = []
            for device in cursor:
                devices.append(self._serialize_document(device))
            
            return devices
            
        except Exception as e:
            logger.error(f"Error finding devices: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def count(self, filters: Dict[str, Any], org_id: str) -> int:
        """Count devices matching filters"""
        try:
            collection = self._get_collection()
            
            # Build query (same as find_many)
            query = {"org_id": org_id}
            
            if filters.get("status"):
                query["status"] = filters["status"]
            
            if filters.get("device_type"):
                query["device_type"] = filters["device_type"]
            
            if filters.get("protocol"):
                query["protocol"] = filters["protocol"]
            
            if filters.get("tags"):
                query["tags"] = {"$in": filters["tags"]}
            
            if filters.get("group_id"):
                query["group_ids"] = filters["group_id"]
            
            if filters.get("search"):
                search_regex = {"$regex": filters["search"], "$options": "i"}
                query["$or"] = [
                    {"name": search_regex},
                    {"serial_number": search_regex}
                ]
            
            # Count documents
            return collection.count_documents(query)
            
        except Exception as e:
            logger.error(f"Error counting devices: {str(e)}")
            raise
    
    async def get_by_id(self, device_id: str, org_id: str) -> Optional[Any]:
        """Get device by ID (alias for find_by_id)"""
        return await self.find_by_id(device_id, org_id)
    
    def _serialize_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize MongoDB document for API response"""
        if not doc:
            return doc
        
        # Convert ObjectId to string
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
        
        # Convert datetime objects to ISO strings
        for field in ["created_at", "updated_at", "last_seen"]:
            if field in doc and isinstance(doc[field], datetime):
                doc[field] = doc[field].isoformat()
        
        return doc
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def find_with_options(
        self,
        query: Dict[str, Any],
        projection: Optional[Dict[str, int]] = None,
        sort: Optional[List[tuple]] = None,
        skip: int = 0,
        limit: int = 20,
        timeout_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Find devices with advanced options
        
        Args:
            query: MongoDB query
            projection: Field projection
            sort: Sort specification
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            timeout_ms: Query timeout in milliseconds
            
        Returns:
            List of devices
        """
        try:
            collection = self._get_collection()
            
            # Build cursor with options
            cursor = collection.find(query, projection=projection)
            
            # Apply sort if provided
            if sort:
                cursor = cursor.sort(sort)
            
            # Apply pagination
            cursor = cursor.skip(skip).limit(limit)
            
            # Apply timeout if provided
            if timeout_ms:
                cursor = cursor.max_time_ms(timeout_ms)
            
            # Execute query and serialize results
            devices = []
            for device in cursor:
                devices.append(self._serialize_document(device))
            
            return devices
            
        except Exception as e:
            logger.error(f"Error in find_with_options: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def aggregate(self, pipeline: List[Dict[str, Any]], timeout_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute aggregation pipeline
        
        Args:
            pipeline: MongoDB aggregation pipeline
            timeout_ms: Query timeout in milliseconds
            
        Returns:
            List of aggregation results
        """
        try:
            collection = self._get_collection()
            
            # Execute aggregation
            cursor = collection.aggregate(pipeline)
            
            # Apply timeout if provided
            if timeout_ms:
                cursor = cursor.max_time_ms(timeout_ms)
            
            # Collect results
            results = []
            for result in cursor:
                # Serialize any datetime fields in aggregation results
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                    elif key == "_id" and isinstance(value, dict):
                        # Handle grouped _id fields
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, datetime):
                                value[sub_key] = sub_value.isoformat()
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in aggregate: {str(e)}")
            raise