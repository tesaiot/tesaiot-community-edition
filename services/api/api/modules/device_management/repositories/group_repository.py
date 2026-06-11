# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Group Repository
Repository implementation for device groups with MongoDB

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError

from ..models.group_models import DeviceGroup, GroupMembership, GroupRule
from ..interfaces.device_interfaces import IGroupRepository
from ....core.exceptions import (
    DatabaseError, NotFoundError, ValidationError, DuplicateResourceError
)

logger = logging.getLogger(__name__)


class GroupRepository(IGroupRepository):
    """MongoDB implementation of Group Repository"""
    
    def __init__(self, database: AsyncIOMotorDatabase):
        self.db = database
        self.groups_collection: AsyncIOMotorCollection = self.db.device_groups
        self.memberships_collection: AsyncIOMotorCollection = self.db.group_memberships
        self.operations_collection: AsyncIOMotorCollection = self.db.group_operations
        self._ensure_indexes_created = False
        logger.info("GroupRepository initialized")
    
    async def _ensure_indexes(self):
        """Create necessary indexes for optimal performance"""
        if self._ensure_indexes_created:
            return
            
        try:
            # Groups collection indexes
            await self.groups_collection.create_indexes([
                [("group_id", ASCENDING), ("org_id", ASCENDING)],
                [("org_id", ASCENDING), ("name", ASCENDING)],
                [("parent_group_id", ASCENDING)],
                [("tags", ASCENDING)],
                [("grouping_strategy", ASCENDING)],
                [("created_at", DESCENDING)],
                [("name", TEXT), ("description", TEXT)]
            ])
            
            # Unique constraint on group_id
            await self.groups_collection.create_index(
                "group_id", 
                unique=True,
                name="unique_group_id"
            )
            
            # Memberships collection indexes
            await self.memberships_collection.create_indexes([
                [("device_id", ASCENDING), ("group_id", ASCENDING)],
                [("group_id", ASCENDING)],
                [("org_id", ASCENDING)],
                [("membership_type", ASCENDING)],
                [("added_at", DESCENDING)]
            ])
            
            # Unique constraint on device-group membership
            await self.memberships_collection.create_index(
                [("device_id", ASCENDING), ("group_id", ASCENDING)],
                unique=True,
                name="unique_device_group_membership"
            )
            
            # Operations collection indexes
            await self.operations_collection.create_indexes([
                [("operation_id", ASCENDING)],
                [("group_id", ASCENDING)],
                [("org_id", ASCENDING)],
                [("status", ASCENDING)],
                [("created_at", DESCENDING)]
            ])
            
            self._ensure_indexes_created = True
            logger.info("Group repository indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
            raise DatabaseError(f"Failed to create indexes: {str(e)}")
    
    async def create_group(self, group: DeviceGroup) -> DeviceGroup:
        """Create a new device group"""
        await self._ensure_indexes()
        
        try:
            # Validate parent group exists if specified
            if group.parent_group_id:
                parent = await self.groups_collection.find_one({
                    "group_id": group.parent_group_id,
                    "org_id": group.org_id
                })
                if not parent:
                    raise ValidationError(f"Parent group {group.parent_group_id} not found")
            
            # Convert to dict and insert
            group_dict = group.to_dict()
            group_dict["_id"] = group.group_id
            
            await self.groups_collection.insert_one(group_dict)
            
            # Update parent's child_group_ids if parent exists
            if group.parent_group_id:
                await self.groups_collection.update_one(
                    {"group_id": group.parent_group_id},
                    {"$push": {"child_group_ids": group.group_id}}
                )
            
            logger.info(f"Created group {group.group_id}")
            return group
            
        except DuplicateKeyError:
            raise DuplicateResourceError(f"Group with ID {group.group_id} already exists")
        except Exception as e:
            logger.error(f"Failed to create group: {str(e)}")
            raise DatabaseError(f"Failed to create group: {str(e)}")
    
    async def get_group(self, group_id: str, org_id: str) -> Optional[DeviceGroup]:
        """Get a group by ID"""
        await self._ensure_indexes()
        
        try:
            group_dict = await self.groups_collection.find_one({
                "group_id": group_id,
                "org_id": org_id
            })
            
            if not group_dict:
                return None
            
            # Remove MongoDB _id field
            group_dict.pop("_id", None)
            
            return DeviceGroup.from_dict(group_dict)
            
        except Exception as e:
            logger.error(f"Failed to get group: {str(e)}")
            raise DatabaseError(f"Failed to get group: {str(e)}")
    
    async def update_group(self, group: DeviceGroup) -> DeviceGroup:
        """Update a group"""
        await self._ensure_indexes()
        
        try:
            group.updated_at = datetime.utcnow()
            group_dict = group.to_dict()
            group_dict.pop("_id", None)
            
            result = await self.groups_collection.update_one(
                {"group_id": group.group_id, "org_id": group.org_id},
                {"$set": group_dict}
            )
            
            if result.matched_count == 0:
                raise NotFoundError(f"Group {group.group_id} not found")
            
            logger.info(f"Updated group {group.group_id}")
            return group
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update group: {str(e)}")
            raise DatabaseError(f"Failed to update group: {str(e)}")
    
    async def delete_group(self, group_id: str, org_id: str) -> bool:
        """Delete a group and all its memberships"""
        await self._ensure_indexes()
        
        try:
            # Get the group first
            group = await self.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Check if group has children
            if group.child_group_ids:
                raise ValidationError("Cannot delete group with child groups")
            
            # Remove from parent's child list if applicable
            if group.parent_group_id:
                await self.groups_collection.update_one(
                    {"group_id": group.parent_group_id},
                    {"$pull": {"child_group_ids": group_id}}
                )
            
            # Delete all memberships
            await self.memberships_collection.delete_many({
                "group_id": group_id,
                "org_id": org_id
            })
            
            # Delete the group
            result = await self.groups_collection.delete_one({
                "group_id": group_id,
                "org_id": org_id
            })
            
            logger.info(f"Deleted group {group_id}")
            return result.deleted_count > 0
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete group: {str(e)}")
            raise DatabaseError(f"Failed to delete group: {str(e)}")
    
    async def list_groups(
        self,
        org_id: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DeviceGroup]:
        """List groups with optional filters"""
        await self._ensure_indexes()
        
        try:
            query = {"org_id": org_id}
            
            if filters:
                # Add filter conditions
                if "parent_group_id" in filters:
                    query["parent_group_id"] = filters["parent_group_id"]
                if "group_type" in filters:
                    query["group_type"] = filters["group_type"]
                if "tags" in filters:
                    query["tags"] = {"$in": filters["tags"]}
                if "grouping_strategy" in filters:
                    query["grouping_strategy"] = filters["grouping_strategy"]
                if "search" in filters:
                    # Sanitize the raw $text search string: cap length and
                    # strip Mongo operator characters / quotes so user input
                    # cannot inject phrase/negation operators.
                    raw_search = str(filters["search"])[:256]
                    safe_search = re.sub(r'[${}"\\]', ' ', raw_search).strip()
                    if safe_search:
                        query["$text"] = {"$search": safe_search}
            
            cursor = self.groups_collection.find(query).skip(skip).limit(limit)
            groups = []
            
            async for group_dict in cursor:
                group_dict.pop("_id", None)
                groups.append(DeviceGroup.from_dict(group_dict))
            
            return groups
            
        except Exception as e:
            logger.error(f"Failed to list groups: {str(e)}")
            raise DatabaseError(f"Failed to list groups: {str(e)}")
    
    async def add_device_to_group(
        self,
        device_id: str,
        group_id: str,
        org_id: str,
        added_by: Optional[str] = None,
        membership_type: str = "static"
    ) -> GroupMembership:
        """Add a device to a group"""
        await self._ensure_indexes()
        
        try:
            # Check if group exists
            group = await self.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Create membership
            membership = GroupMembership(
                membership_id=str(uuid.uuid4()),
                device_id=device_id,
                group_id=group_id,
                org_id=org_id,
                membership_type=membership_type,
                added_by=added_by
            )
            
            membership_dict = membership.to_dict()
            await self.memberships_collection.insert_one(membership_dict)
            
            # Update group's device_ids set and member count
            await self.groups_collection.update_one(
                {"group_id": group_id},
                {
                    "$addToSet": {"device_ids": device_id},
                    "$inc": {"member_count": 1},
                    "$set": {"last_membership_update": datetime.utcnow()}
                }
            )
            
            logger.info(f"Added device {device_id} to group {group_id}")
            return membership
            
        except DuplicateKeyError:
            logger.warning(f"Device {device_id} already in group {group_id}")
            # Return existing membership
            existing = await self.memberships_collection.find_one({
                "device_id": device_id,
                "group_id": group_id
            })
            return GroupMembership(**existing)
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add device to group: {str(e)}")
            raise DatabaseError(f"Failed to add device to group: {str(e)}")
    
    async def remove_device_from_group(
        self,
        device_id: str,
        group_id: str,
        org_id: str
    ) -> bool:
        """Remove a device from a group"""
        await self._ensure_indexes()
        
        try:
            # Delete membership
            result = await self.memberships_collection.delete_one({
                "device_id": device_id,
                "group_id": group_id,
                "org_id": org_id
            })
            
            if result.deleted_count > 0:
                # Update group's device_ids set and member count
                await self.groups_collection.update_one(
                    {"group_id": group_id},
                    {
                        "$pull": {"device_ids": device_id},
                        "$inc": {"member_count": -1},
                        "$set": {"last_membership_update": datetime.utcnow()}
                    }
                )
                
                logger.info(f"Removed device {device_id} from group {group_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove device from group: {str(e)}")
            raise DatabaseError(f"Failed to remove device from group: {str(e)}")
    
    async def get_device_groups(self, device_id: str, org_id: str) -> List[str]:
        """Get all groups a device belongs to"""
        await self._ensure_indexes()
        
        try:
            memberships = await self.memberships_collection.find({
                "device_id": device_id,
                "org_id": org_id
            }).to_list(None)
            
            return [m["group_id"] for m in memberships]
            
        except Exception as e:
            logger.error(f"Failed to get device groups: {str(e)}")
            raise DatabaseError(f"Failed to get device groups: {str(e)}")
    
    async def get_group_devices(
        self,
        group_id: str,
        org_id: str,
        include_subgroups: bool = False
    ) -> List[str]:
        """Get all devices in a group"""
        await self._ensure_indexes()
        
        try:
            device_ids = set()
            
            # Get direct members
            memberships = await self.memberships_collection.find({
                "group_id": group_id,
                "org_id": org_id
            }).to_list(None)
            
            device_ids.update(m["device_id"] for m in memberships)
            
            # If including subgroups, get devices from child groups
            if include_subgroups:
                group = await self.get_group(group_id, org_id)
                if group and group.child_group_ids:
                    for child_id in group.child_group_ids:
                        child_devices = await self.get_group_devices(
                            child_id, org_id, include_subgroups=True
                        )
                        device_ids.update(child_devices)
            
            return list(device_ids)
            
        except Exception as e:
            logger.error(f"Failed to get group devices: {str(e)}")
            raise DatabaseError(f"Failed to get group devices: {str(e)}")
    
    async def get_group_hierarchy(self, org_id: str, root_group_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the hierarchical structure of groups"""
        await self._ensure_indexes()
        
        try:
            # Get all groups for the organization
            all_groups = await self.list_groups(org_id, limit=1000)
            
            # Build hierarchy
            groups_by_id = {g.group_id: g for g in all_groups}
            hierarchy = []
            
            # Find root groups or start from specified root
            if root_group_id:
                root_groups = [g for g in all_groups if g.group_id == root_group_id]
            else:
                root_groups = [g for g in all_groups if not g.parent_group_id]
            
            # Build tree structure
            def build_tree(group: DeviceGroup, level: int = 0) -> Dict[str, Any]:
                node = {
                    "group_id": group.group_id,
                    "name": group.name,
                    "level": level,
                    "parent_id": group.parent_group_id,
                    "device_count": group.member_count,
                    "children": []
                }
                
                # Add children
                for child_id in group.child_group_ids:
                    if child_id in groups_by_id:
                        child_node = build_tree(groups_by_id[child_id], level + 1)
                        node["children"].append(child_node)
                
                # Calculate total device count
                node["total_device_count"] = node["device_count"] + sum(
                    child["total_device_count"] for child in node["children"]
                )
                
                return node
            
            for root in root_groups:
                hierarchy.append(build_tree(root))
            
            return {
                "org_id": org_id,
                "total_groups": len(all_groups),
                "hierarchy": hierarchy
            }
            
        except Exception as e:
            logger.error(f"Failed to get group hierarchy: {str(e)}")
            raise DatabaseError(f"Failed to get group hierarchy: {str(e)}")
    
    async def evaluate_dynamic_membership(
        self,
        group: DeviceGroup,
        device_attributes: Dict[str, Any]
    ) -> bool:
        """Evaluate if a device should be in a dynamic group based on rules"""
        if not group.rules:
            return False
        
        results = []
        
        for rule in group.rules:
            # Get the field value from device attributes
            field_parts = rule.field.split(".")
            value = device_attributes
            
            for part in field_parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    value = None
                    break
            
            # Evaluate the rule
            result = self._evaluate_rule(rule, value)
            results.append(result)
        
        # Apply rule logic (AND/OR)
        if group.rule_logic == "AND":
            return all(results)
        else:  # OR
            return any(results)
    
    def _evaluate_rule(self, rule: GroupRule, value: Any) -> bool:
        """Evaluate a single rule"""
        if value is None:
            return False
        
        # Convert to string for comparison if needed
        if not rule.case_sensitive and isinstance(value, str):
            value = value.lower()
            rule_value = str(rule.value).lower()
        else:
            rule_value = rule.value
        
        # Evaluate based on operator
        if rule.operator == "eq":
            return value == rule_value
        elif rule.operator == "ne":
            return value != rule_value
        elif rule.operator == "in":
            return value in rule_value if isinstance(rule_value, (list, set)) else False
        elif rule.operator == "not_in":
            return value not in rule_value if isinstance(rule_value, (list, set)) else True
        elif rule.operator == "contains":
            return rule_value in str(value)
        elif rule.operator == "starts_with":
            return str(value).startswith(str(rule_value))
        elif rule.operator == "regex":
            import re
            return bool(re.match(rule_value, str(value)))
        else:
            logger.warning(f"Unknown operator: {rule.operator}")
            return False