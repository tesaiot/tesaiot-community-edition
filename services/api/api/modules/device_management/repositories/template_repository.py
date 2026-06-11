# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Maximum length for a user-supplied $regex search term (ReDoS mitigation).
MAX_TEMPLATE_SEARCH_LENGTH = 128
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from ..models.template_models import (
    DeviceTemplate, TemplateVersion, TemplateInstance,
    TemplateStatus
)
from ....core.exceptions import ValidationError, ResourceNotFoundError

logger = logging.getLogger(__name__)


class TemplateRepository:
    """Repository for device template operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.templates_collection: AsyncIOMotorCollection = db.device_templates
        self.versions_collection: AsyncIOMotorCollection = db.template_versions
        self.instances_collection: AsyncIOMotorCollection = db.template_instances
        
    async def initialize_indexes(self):
        """Initialize database indexes for optimal performance"""
        try:
            # Device templates indexes
            await self.templates_collection.create_index([("template_id", ASCENDING), ("org_id", ASCENDING)], unique=True)
            await self.templates_collection.create_index([("org_id", ASCENDING), ("status", ASCENDING)])
            await self.templates_collection.create_index([("org_id", ASCENDING), ("category", ASCENDING)])
            await self.templates_collection.create_index([("org_id", ASCENDING), ("device_type", ASCENDING)])
            await self.templates_collection.create_index([("parent_template_id", ASCENDING)])
            await self.templates_collection.create_index([("composed_template_ids", ASCENDING)])
            await self.templates_collection.create_index([("created_at", DESCENDING)])
            
            # Template versions indexes
            await self.versions_collection.create_index([("version_id", ASCENDING), ("template_id", ASCENDING)], unique=True)
            await self.versions_collection.create_index([("template_id", ASCENDING), ("version_number", ASCENDING)], unique=True)
            await self.versions_collection.create_index([("template_id", ASCENDING), ("created_at", DESCENDING)])
            
            # Template instances indexes
            await self.instances_collection.create_index([("instance_id", ASCENDING), ("org_id", ASCENDING)], unique=True)
            await self.instances_collection.create_index([("device_id", ASCENDING), ("org_id", ASCENDING)])
            await self.instances_collection.create_index([("template_id", ASCENDING), ("org_id", ASCENDING)])
            await self.instances_collection.create_index([("instantiated_at", DESCENDING)])
            
            logger.info("Template repository indexes initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing template indexes: {e}")
            raise
    
    # Template CRUD operations
    async def create_template(self, template: DeviceTemplate) -> DeviceTemplate:
        """Create a new device template"""
        try:
            template_dict = template.to_dict()
            result = await self.templates_collection.insert_one(template_dict)
            
            if result.inserted_id:
                logger.info(f"Template created: {template.template_id}")
                return template
            else:
                raise ValidationError("Failed to create template")
                
        except DuplicateKeyError:
            raise ValidationError(f"Template with ID {template.template_id} already exists")
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            raise
    
    async def get_template(self, template_id: str, org_id: str) -> Optional[DeviceTemplate]:
        """Get a template by ID"""
        try:
            template_dict = await self.templates_collection.find_one({
                "template_id": template_id,
                "org_id": org_id
            })
            
            if template_dict:
                return DeviceTemplate.from_dict(template_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving template: {e}")
            raise
    
    async def update_template(self, template: DeviceTemplate) -> DeviceTemplate:
        """Update an existing template"""
        try:
            template.updated_at = datetime.utcnow()
            template_dict = template.to_dict()
            
            result = await self.templates_collection.replace_one(
                {"template_id": template.template_id, "org_id": template.org_id},
                template_dict
            )
            
            if result.modified_count > 0:
                logger.info(f"Template updated: {template.template_id}")
                return template
            else:
                raise ResourceNotFoundError(f"Template not found: {template.template_id}")
                
        except Exception as e:
            logger.error(f"Error updating template: {e}")
            raise
    
    async def delete_template(self, template_id: str, org_id: str) -> bool:
        """Delete a template (soft delete by changing status)"""
        try:
            result = await self.templates_collection.update_one(
                {"template_id": template_id, "org_id": org_id},
                {
                    "$set": {
                        "status": TemplateStatus.ARCHIVED.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"Template archived: {template_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting template: {e}")
            raise
    
    async def list_templates(
        self,
        org_id: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "created_at",
        sort_order: int = -1
    ) -> Tuple[List[DeviceTemplate], int]:
        """List templates with pagination and filtering"""
        try:
            query = {"org_id": org_id}
            
            if filters:
                if "status" in filters:
                    query["status"] = filters["status"]
                if "category" in filters:
                    query["category"] = filters["category"]
                if "device_type" in filters:
                    query["device_type"] = filters["device_type"]
                if "search" in filters:
                    # Regex-escape and length-cap the user-supplied search term
                    # to prevent NoSQL regex injection and ReDoS.
                    raw_search = filters["search"]
                    if not isinstance(raw_search, str):
                        raise ValueError("search filter must be a string")
                    if len(raw_search) > MAX_TEMPLATE_SEARCH_LENGTH:
                        raise ValueError(
                            f"search filter exceeds maximum length of "
                            f"{MAX_TEMPLATE_SEARCH_LENGTH}"
                        )
                    search_literal = re.escape(raw_search)
                    query["$or"] = [
                        {"name": {"$regex": search_literal, "$options": "i"}},
                        {"description": {"$regex": search_literal, "$options": "i"}}
                    ]
            
            # Get total count
            total_count = await self.templates_collection.count_documents(query)
            
            # Get paginated results
            cursor = self.templates_collection.find(query)
            cursor = cursor.sort(sort_by, sort_order).skip(skip).limit(limit)
            
            templates = []
            async for doc in cursor:
                templates.append(DeviceTemplate.from_dict(doc))
            
            return templates, total_count
            
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            raise
    
    # Template version operations
    async def create_version(self, version: TemplateVersion) -> TemplateVersion:
        """Create a new template version"""
        try:
            version_dict = version.to_dict()
            result = await self.versions_collection.insert_one(version_dict)
            
            if result.inserted_id:
                logger.info(f"Template version created: {version.version_id}")
                return version
            else:
                raise ValidationError("Failed to create template version")
                
        except DuplicateKeyError:
            raise ValidationError(f"Version {version.version_number} already exists for template {version.template_id}")
        except Exception as e:
            logger.error(f"Error creating template version: {e}")
            raise
    
    async def get_template_versions(self, template_id: str, org_id: str) -> List[TemplateVersion]:
        """Get all versions of a template"""
        try:
            cursor = self.versions_collection.find({
                "template_id": template_id,
                "org_id": org_id
            }).sort("created_at", DESCENDING)
            
            versions = []
            async for doc in cursor:
                versions.append(TemplateVersion.from_dict(doc))
            
            return versions
            
        except Exception as e:
            logger.error(f"Error retrieving template versions: {e}")
            raise
    
    async def get_template_version(self, template_id: str, version_number: str, org_id: str) -> Optional[TemplateVersion]:
        """Get a specific version of a template"""
        try:
            version_dict = await self.versions_collection.find_one({
                "template_id": template_id,
                "version_number": version_number,
                "org_id": org_id
            })
            
            if version_dict:
                return TemplateVersion.from_dict(version_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving template version: {e}")
            raise
    
    # Template instance operations
    async def create_instance(self, instance: TemplateInstance) -> TemplateInstance:
        """Create a template instance record"""
        try:
            instance_dict = instance.to_dict()
            result = await self.instances_collection.insert_one(instance_dict)
            
            if result.inserted_id:
                # Update template usage count
                await self.templates_collection.update_one(
                    {"template_id": instance.template_id, "org_id": instance.org_id},
                    {
                        "$inc": {"usage_count": 1},
                        "$set": {"last_used_at": datetime.utcnow()}
                    }
                )
                
                logger.info(f"Template instance created: {instance.instance_id}")
                return instance
            else:
                raise ValidationError("Failed to create template instance")
                
        except DuplicateKeyError:
            raise ValidationError(f"Instance {instance.instance_id} already exists")
        except Exception as e:
            logger.error(f"Error creating template instance: {e}")
            raise
    
    async def get_device_template_instance(self, device_id: str, org_id: str) -> Optional[TemplateInstance]:
        """Get template instance for a device"""
        try:
            instance_dict = await self.instances_collection.find_one({
                "device_id": device_id,
                "org_id": org_id
            })
            
            if instance_dict:
                return TemplateInstance.from_dict(instance_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving template instance: {e}")
            raise
    
    async def get_template_instances(self, template_id: str, org_id: str) -> List[TemplateInstance]:
        """Get all instances of a template"""
        try:
            cursor = self.instances_collection.find({
                "template_id": template_id,
                "org_id": org_id
            }).sort("instantiated_at", DESCENDING)
            
            instances = []
            async for doc in cursor:
                instances.append(TemplateInstance.from_dict(doc))
            
            return instances
            
        except Exception as e:
            logger.error(f"Error retrieving template instances: {e}")
            raise
    
    # Template hierarchy operations
    async def get_child_templates(self, parent_template_id: str, org_id: str) -> List[DeviceTemplate]:
        """Get all templates that inherit from a parent template"""
        try:
            cursor = self.templates_collection.find({
                "parent_template_id": parent_template_id,
                "org_id": org_id
            })
            
            templates = []
            async for doc in cursor:
                templates.append(DeviceTemplate.from_dict(doc))
            
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving child templates: {e}")
            raise
    
    async def get_composed_templates(self, template_id: str, org_id: str) -> List[DeviceTemplate]:
        """Get all templates that are composed into this template"""
        try:
            template = await self.get_template(template_id, org_id)
            if not template or not template.composed_template_ids:
                return []
            
            cursor = self.templates_collection.find({
                "template_id": {"$in": template.composed_template_ids},
                "org_id": org_id
            })
            
            templates = []
            async for doc in cursor:
                templates.append(DeviceTemplate.from_dict(doc))
            
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving composed templates: {e}")
            raise
    
    # Template statistics
    async def get_template_statistics(self, org_id: str) -> Dict[str, Any]:
        """Get template usage statistics"""
        try:
            pipeline = [
                {"$match": {"org_id": org_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_templates": {"$sum": 1},
                        "active_templates": {
                            "$sum": {"$cond": [{"$eq": ["$status", TemplateStatus.ACTIVE.value]}, 1, 0]}
                        },
                        "total_usage": {"$sum": "$usage_count"},
                        "by_category": {
                            "$push": {
                                "category": "$category",
                                "count": 1
                            }
                        },
                        "by_device_type": {
                            "$push": {
                                "device_type": "$device_type",
                                "count": 1
                            }
                        }
                    }
                }
            ]
            
            result = await self.templates_collection.aggregate(pipeline).to_list(1)
            
            if result:
                stats = result[0]
                # Process category and device type counts
                category_counts = {}
                device_type_counts = {}
                
                for item in stats.get("by_category", []):
                    category = item["category"]
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                for item in stats.get("by_device_type", []):
                    device_type = item["device_type"]
                    device_type_counts[device_type] = device_type_counts.get(device_type, 0) + 1
                
                return {
                    "total_templates": stats.get("total_templates", 0),
                    "active_templates": stats.get("active_templates", 0),
                    "total_usage": stats.get("total_usage", 0),
                    "by_category": category_counts,
                    "by_device_type": device_type_counts
                }
            
            return {
                "total_templates": 0,
                "active_templates": 0,
                "total_usage": 0,
                "by_category": {},
                "by_device_type": {}
            }
            
        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            raise