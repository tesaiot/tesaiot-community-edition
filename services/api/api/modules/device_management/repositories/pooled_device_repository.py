# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Pooled Device Repository
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Device Repository with Enhanced Connection Pooling
Version: Dynamic (read from VERSION.txt)
Build Date: 2025-07-27

Description:
    Production-ready MongoDB repository implementation with:
    - Advanced connection pooling
    - Automatic retry mechanisms
    - Connection health monitoring
    - Performance optimizations
    - Graceful degradation
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import time
from contextlib import asynccontextmanager

from ..interfaces.device_interfaces import IDeviceRepository
from ....core.connection_pool import pool_manager
from ...dashboard.utils.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)


class PooledDeviceRepository(IDeviceRepository):
    """MongoDB Device Repository with advanced connection pooling"""
    
    def __init__(self, collection_name: str = "devices"):
        self.collection_name = collection_name
        self.pool_stats = {
            'operations': 0,
            'total_duration': 0.0,
            'errors': 0,
            'last_error': None
        }
        logger.info(f"PooledDeviceRepository initialized with collection: {collection_name}")
    
    @asynccontextmanager
    async def _get_collection(self):
        """Get MongoDB collection with connection pool monitoring"""
        start_time = time.time()
        
        try:
            # Get database from enhanced pool
            db = pool_manager.get_mongodb_sync_db()
            if db is None:
                raise ConnectionError("Database connection pool not available")
            
            collection = db[self.collection_name]
            
            # Validate connection with ping
            await asyncio.get_event_loop().run_in_executor(
                None, db.client.admin.command, 'ping'
            )
            
            # Update stats
            self.pool_stats['operations'] += 1
            
            yield collection
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection pool error: {e}")
            self.pool_stats['errors'] += 1
            self.pool_stats['last_error'] = str(e)
            raise ConnectionError(f"Database connection failed: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error getting collection: {e}")
            self.pool_stats['errors'] += 1
            self.pool_stats['last_error'] = str(e)
            raise
            
        finally:
            # Record operation duration
            duration = time.time() - start_time
            self.pool_stats['total_duration'] += duration
            
            if duration > 1.0:
                logger.warning(f"Slow collection access: {duration:.2f}s")
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def create(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create device with connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Ensure _id is ObjectId
                if "_id" not in device_data:
                    device_data["_id"] = ObjectId()
                
                # Run insert in executor to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    None, collection.insert_one, device_data
                )
                
                # Retrieve created device
                created_device = await asyncio.get_event_loop().run_in_executor(
                    None, collection.find_one, {"_id": result.inserted_id}
                )
                
                return self._serialize_document(created_device)
                
        except Exception as e:
            logger.error(f"Error creating device: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def find_by_id(self, device_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        """Find device by ID with connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Execute find in thread pool
                device = await asyncio.get_event_loop().run_in_executor(
                    None,
                    collection.find_one,
                    {"device_id": device_id, "org_id": org_id}
                )
                
                return self._serialize_document(device) if device else None
                
        except Exception as e:
            logger.error(f"Error finding device {device_id}: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def update(self, device_id: str, updates: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Update device with connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Remove _id from updates if present
                updates.pop("_id", None)
                
                # Execute update in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    collection.find_one_and_update,
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
        """Delete device with connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Execute delete in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    collection.delete_one,
                    {"device_id": device_id, "org_id": org_id}
                )
                
                return result.deleted_count > 0
                
        except Exception as e:
            logger.error(f"Error deleting device {device_id}: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def find_many(self, filters: Dict[str, Any], skip: int, limit: int, org_id: str) -> List[Dict[str, Any]]:
        """Find multiple devices with connection pooling and optimizations"""
        try:
            async with self._get_collection() as collection:
                # Build query
                query = self._build_query(filters, org_id)
                
                # Sort configuration
                sort_field = filters.get("sort_by", "created_at")
                sort_order = pymongo.DESCENDING if filters.get("sort_order", "desc") == "desc" else pymongo.ASCENDING
                
                # Create cursor with batch size optimization
                cursor = collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
                
                # Set batch size for better performance
                cursor.batch_size(min(100, limit))
                
                # Execute query in thread pool
                devices = await asyncio.get_event_loop().run_in_executor(
                    None, list, cursor
                )
                
                # Serialize documents
                return [self._serialize_document(device) for device in devices]
                
        except Exception as e:
            logger.error(f"Error finding devices: {str(e)}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30, expected_exception=Exception)
    async def count(self, filters: Dict[str, Any], org_id: str) -> int:
        """Count devices with connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Build query
                query = self._build_query(filters, org_id)
                
                # Execute count in thread pool with hint for performance
                count = await asyncio.get_event_loop().run_in_executor(
                    None,
                    collection.count_documents,
                    query,
                    {'hint': {'org_id': 1}}  # Use org_id index hint
                )
                
                return count
                
        except Exception as e:
            logger.error(f"Error counting devices: {str(e)}")
            raise
    
    async def batch_find_by_ids(self, device_ids: List[str], org_id: str) -> List[Dict[str, Any]]:
        """Batch find devices by IDs - optimized for connection pooling"""
        try:
            async with self._get_collection() as collection:
                # Build batch query
                query = {
                    "device_id": {"$in": device_ids},
                    "org_id": org_id
                }
                
                # Execute with optimized batch size
                cursor = collection.find(query).batch_size(100)
                
                devices = await asyncio.get_event_loop().run_in_executor(
                    None, list, cursor
                )
                
                return [self._serialize_document(device) for device in devices]
                
        except Exception as e:
            logger.error(f"Error batch finding devices: {str(e)}")
            raise
    
    async def update_last_seen_batch(self, device_updates: List[Dict[str, Any]], org_id: str) -> int:
        """Batch update last seen timestamps - optimized for high throughput"""
        try:
            async with self._get_collection() as collection:
                # Prepare bulk operations
                bulk_ops = []
                current_time = datetime.utcnow()
                
                for update in device_updates:
                    bulk_ops.append(
                        pymongo.UpdateOne(
                            {
                                "device_id": update["device_id"],
                                "org_id": org_id
                            },
                            {
                                "$set": {
                                    "last_seen": current_time,
                                    "status": update.get("status", "online")
                                }
                            }
                        )
                    )
                
                # Execute bulk write
                if bulk_ops:
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        collection.bulk_write,
                        bulk_ops,
                        ordered=False  # Allow parallel execution
                    )
                    return result.modified_count
                
                return 0
                
        except Exception as e:
            logger.error(f"Error batch updating devices: {str(e)}")
            raise
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get repository and connection pool statistics"""
        # Get pool manager stats
        pool_stats = pool_manager.get_all_stats()
        
        # Add repository stats
        avg_duration = (
            self.pool_stats['total_duration'] / self.pool_stats['operations']
            if self.pool_stats['operations'] > 0 else 0
        )
        
        return {
            'repository': {
                'collection': self.collection_name,
                'total_operations': self.pool_stats['operations'],
                'total_errors': self.pool_stats['errors'],
                'average_operation_time': avg_duration,
                'last_error': self.pool_stats['last_error']
            },
            'connection_pools': pool_stats
        }
    
    def _build_query(self, filters: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Build MongoDB query from filters"""
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
        
        return query
    
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