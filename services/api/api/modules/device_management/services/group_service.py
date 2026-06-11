# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Group Service
Business logic for device group management

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import asyncio

from ..models.group_models import (
    DeviceGroup, GroupRule, GroupPolicy,
    GroupType, GroupingStrategy, GroupOperation
)
from ..models.device_models import Device
from ..interfaces.device_interfaces import IGroupService, IGroupRepository, IDeviceRepository
from ..services.audit_logging_service import device_audit_service
from ..models.audit_models import DeviceAuditAction
from ....core.exceptions import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class GroupService(IGroupService):
    """Service for managing device groups"""
    
    def __init__(
        self,
        group_repository: IGroupRepository,
        device_repository: IDeviceRepository
    ):
        self.group_repo = group_repository
        self.device_repo = device_repository
        logger.info("GroupService initialized")
    
    async def create_group(
        self,
        group_data: Dict[str, Any],
        org_id: str,
        created_by: Optional[str] = None
    ) -> DeviceGroup:
        """Create a new device group"""
        try:
            # Validate group data
            self._validate_group_data(group_data)
            
            # Create group instance
            group = DeviceGroup(
                group_id=group_data.get("group_id", str(uuid.uuid4())),
                org_id=org_id,
                name=group_data["name"],
                description=group_data.get("description"),
                group_type=GroupType(group_data.get("group_type", "static")),
                parent_group_id=group_data.get("parent_group_id"),
                rules=[GroupRule.from_dict(r) for r in group_data.get("rules", [])],
                rule_logic=group_data.get("rule_logic", "AND"),
                policies=[GroupPolicy.from_dict(p) for p in group_data.get("policies", [])],
                settings=group_data.get("settings", {}),
                metadata=group_data.get("metadata", {}),
                tags=group_data.get("tags", []),
                grouping_strategy=GroupingStrategy(group_data["grouping_strategy"]) if group_data.get("grouping_strategy") else None,
                created_by=created_by
            )
            
            # Create in repository
            created_group = await self.group_repo.create_group(group)
            
            # Log audit event
            await device_audit_service.log_event(
                org_id=org_id,
                device_id=None,
                action=DeviceAuditAction.GROUP_CREATED,
                details={
                    "group_id": created_group.group_id,
                    "group_name": created_group.name,
                    "group_type": created_group.group_type.value
                },
                user=created_by
            )
            
            # If dynamic group, evaluate membership for existing devices
            if created_group.group_type in [GroupType.DYNAMIC, GroupType.HYBRID]:
                await self._evaluate_dynamic_membership(created_group)
            
            logger.info(f"Created group {created_group.group_id}")
            return created_group
            
        except Exception as e:
            logger.error(f"Failed to create group: {str(e)}")
            raise
    
    async def update_group(
        self,
        group_id: str,
        updates: Dict[str, Any],
        org_id: str,
        updated_by: Optional[str] = None
    ) -> DeviceGroup:
        """Update a device group"""
        try:
            # Get existing group
            group = await self.group_repo.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Track changes for audit
            changes = {}
            
            # Update allowed fields
            if "name" in updates and updates["name"] != group.name:
                changes["name"] = {"old": group.name, "new": updates["name"]}
                group.name = updates["name"]
            
            if "description" in updates:
                changes["description"] = {"old": group.description, "new": updates["description"]}
                group.description = updates["description"]
            
            if "rules" in updates:
                old_rules = [r.to_dict() for r in group.rules]
                group.rules = [GroupRule.from_dict(r) for r in updates["rules"]]
                changes["rules"] = {"old": old_rules, "new": updates["rules"]}
            
            if "rule_logic" in updates:
                changes["rule_logic"] = {"old": group.rule_logic, "new": updates["rule_logic"]}
                group.rule_logic = updates["rule_logic"]
            
            if "policies" in updates:
                old_policies = [p.to_dict() for p in group.policies]
                group.policies = [GroupPolicy.from_dict(p) for p in updates["policies"]]
                changes["policies"] = {"old": old_policies, "new": updates["policies"]}
            
            if "settings" in updates:
                changes["settings"] = {"old": group.settings, "new": updates["settings"]}
                group.settings = updates["settings"]
            
            if "metadata" in updates:
                group.metadata.update(updates["metadata"])
            
            if "tags" in updates:
                changes["tags"] = {"old": group.tags, "new": updates["tags"]}
                group.tags = updates["tags"]
            
            # Update timestamp and user
            group.updated_at = datetime.utcnow()
            group.updated_by = updated_by
            
            # Save changes
            updated_group = await self.group_repo.update_group(group)
            
            # Log audit event
            await device_audit_service.log_event(
                org_id=org_id,
                device_id=None,
                action=DeviceAuditAction.GROUP_UPDATED,
                details={
                    "group_id": group_id,
                    "changes": changes
                },
                user=updated_by
            )
            
            # Re-evaluate dynamic membership if rules changed
            if "rules" in changes or "rule_logic" in changes:
                if updated_group.group_type in [GroupType.DYNAMIC, GroupType.HYBRID]:
                    await self._evaluate_dynamic_membership(updated_group)
            
            logger.info(f"Updated group {group_id}")
            return updated_group
            
        except Exception as e:
            logger.error(f"Failed to update group: {str(e)}")
            raise
    
    async def delete_group(
        self,
        group_id: str,
        org_id: str,
        deleted_by: Optional[str] = None,
        cascade: bool = False
    ) -> bool:
        """Delete a device group"""
        try:
            # Get group to check for children
            group = await self.group_repo.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Handle child groups
            if group.child_group_ids:
                if not cascade:
                    raise ValidationError("Cannot delete group with child groups. Use cascade=True to delete all.")
                else:
                    # Delete all child groups recursively
                    for child_id in group.child_group_ids:
                        await self.delete_group(child_id, org_id, deleted_by, cascade=True)
            
            # Get member count before deletion
            member_count = len(await self.group_repo.get_group_devices(group_id, org_id))
            
            # Delete the group
            result = await self.group_repo.delete_group(group_id, org_id)
            
            # Log audit event
            await device_audit_service.log_event(
                org_id=org_id,
                device_id=None,
                action=DeviceAuditAction.GROUP_DELETED,
                details={
                    "group_id": group_id,
                    "group_name": group.name,
                    "member_count": member_count,
                    "cascade": cascade
                },
                user=deleted_by
            )
            
            logger.info(f"Deleted group {group_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete group: {str(e)}")
            raise
    
    async def add_devices_to_group(
        self,
        group_id: str,
        device_ids: List[str],
        org_id: str,
        added_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add multiple devices to a group"""
        try:
            # Validate group exists
            group = await self.group_repo.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Validate devices exist
            existing_devices = []
            for device_id in device_ids:
                device = await self.device_repo.get_by_id(device_id, org_id)
                if device:
                    existing_devices.append(device_id)
            
            if not existing_devices:
                raise ValidationError("No valid devices found")
            
            # Add devices to group
            added = []
            already_members = []
            
            for device_id in existing_devices:
                try:
                    membership = await self.group_repo.add_device_to_group(
                        device_id=device_id,
                        group_id=group_id,
                        org_id=org_id,
                        added_by=added_by,
                        membership_type="static"
                    )
                    added.append(device_id)
                except Exception as e:
                    if "already" in str(e).lower():
                        already_members.append(device_id)
                    else:
                        logger.error(f"Failed to add device {device_id}: {str(e)}")
            
            # Update device group_ids
            for device_id in added:
                await self.device_repo.update(
                    device_id,
                    {"$addToSet": {"group_ids": group_id}},
                    org_id
                )
            
            # Log audit event
            if added:
                await device_audit_service.log_event(
                    org_id=org_id,
                    device_id=None,
                    action=DeviceAuditAction.GROUP_MEMBERSHIP_ADDED,
                    details={
                        "group_id": group_id,
                        "devices_added": added,
                        "count": len(added)
                    },
                    user=added_by
                )
            
            result = {
                "group_id": group_id,
                "requested": len(device_ids),
                "added": len(added),
                "already_members": len(already_members),
                "devices_added": added,
                "devices_already_members": already_members
            }
            
            logger.info(f"Added {len(added)} devices to group {group_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to add devices to group: {str(e)}")
            raise
    
    async def remove_devices_from_group(
        self,
        group_id: str,
        device_ids: List[str],
        org_id: str,
        removed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remove multiple devices from a group"""
        try:
            # Validate group exists
            group = await self.group_repo.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Remove devices from group
            removed = []
            not_members = []
            
            for device_id in device_ids:
                result = await self.group_repo.remove_device_from_group(
                    device_id=device_id,
                    group_id=group_id,
                    org_id=org_id
                )
                if result:
                    removed.append(device_id)
                else:
                    not_members.append(device_id)
            
            # Update device group_ids
            for device_id in removed:
                await self.device_repo.update(
                    device_id,
                    {"$pull": {"group_ids": group_id}},
                    org_id
                )
            
            # Log audit event
            if removed:
                await device_audit_service.log_event(
                    org_id=org_id,
                    device_id=None,
                    action=DeviceAuditAction.GROUP_MEMBERSHIP_REMOVED,
                    details={
                        "group_id": group_id,
                        "devices_removed": removed,
                        "count": len(removed)
                    },
                    user=removed_by
                )
            
            result = {
                "group_id": group_id,
                "requested": len(device_ids),
                "removed": len(removed),
                "not_members": len(not_members),
                "devices_removed": removed,
                "devices_not_members": not_members
            }
            
            logger.info(f"Removed {len(removed)} devices from group {group_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to remove devices from group: {str(e)}")
            raise
    
    async def get_group_devices(
        self,
        group_id: str,
        org_id: str,
        include_subgroups: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Device]:
        """Get all devices in a group"""
        try:
            # Get device IDs from group
            device_ids = await self.group_repo.get_group_devices(
                group_id, org_id, include_subgroups
            )
            
            if not device_ids:
                return []
            
            # Build query
            query = {
                "device_id": {"$in": device_ids},
                "org_id": org_id
            }
            
            # Add additional filters
            if filters:
                if "status" in filters:
                    query["status"] = filters["status"]
                if "device_type" in filters:
                    query["device_type"] = filters["device_type"]
                if "protocol" in filters:
                    query["protocol"] = filters["protocol"]
            
            # Get devices
            devices = await self.device_repo.find_many(query)
            
            return devices
            
        except Exception as e:
            logger.error(f"Failed to get group devices: {str(e)}")
            raise
    
    async def execute_group_operation(
        self,
        group_id: str,
        operation_type: str,
        payload: Dict[str, Any],
        org_id: str,
        executed_by: Optional[str] = None,
        include_subgroups: bool = False
    ) -> GroupOperation:
        """Execute an operation on all devices in a group"""
        try:
            # Validate group exists
            group = await self.group_repo.get_group(group_id, org_id)
            if not group:
                raise NotFoundError(f"Group {group_id} not found")
            
            # Get all devices in the group
            devices = await self.get_group_devices(
                group_id, org_id, include_subgroups
            )
            
            if not devices:
                raise ValidationError("No devices in group")
            
            # Create operation record
            operation = GroupOperation(
                operation_id=str(uuid.uuid4()),
                group_id=group_id,
                org_id=org_id,
                operation_type=operation_type,
                payload=payload,
                created_by=executed_by,
                total_devices=len(devices),
                started_at=datetime.utcnow()
            )
            
            # Execute operation on each device
            operation.status = "in_progress"
            results = await self._execute_on_devices(
                devices, operation_type, payload, org_id
            )
            
            # Update operation status
            operation.device_statuses = results["device_statuses"]
            operation.completed_devices = results["completed"]
            operation.failed_devices = results["failed"]
            operation.completed_at = datetime.utcnow()
            
            if results["failed"] == 0:
                operation.status = "completed"
            elif results["completed"] == 0:
                operation.status = "failed"
            else:
                operation.status = "partial"
            
            # Log audit event
            await device_audit_service.log_event(
                org_id=org_id,
                device_id=None,
                action=DeviceAuditAction.GROUP_OPERATION_EXECUTED,
                details={
                    "group_id": group_id,
                    "operation_type": operation_type,
                    "total_devices": operation.total_devices,
                    "completed": operation.completed_devices,
                    "failed": operation.failed_devices
                },
                user=executed_by
            )
            
            logger.info(f"Executed {operation_type} on group {group_id}")
            return operation
            
        except Exception as e:
            logger.error(f"Failed to execute group operation: {str(e)}")
            raise
    
    async def get_group_hierarchy(
        self,
        org_id: str,
        root_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get the hierarchical structure of groups"""
        try:
            hierarchy = await self.group_repo.get_group_hierarchy(org_id, root_group_id)
            return hierarchy
        except Exception as e:
            logger.error(f"Failed to get group hierarchy: {str(e)}")
            raise
    
    async def create_group_from_template(
        self,
        template_name: str,
        group_name: str,
        org_id: str,
        created_by: Optional[str] = None,
        customizations: Optional[Dict[str, Any]] = None
    ) -> DeviceGroup:
        """Create a group from a predefined template"""
        try:
            # Get template configuration
            template = self._get_group_template(template_name)
            if not template:
                raise ValidationError(f"Template {template_name} not found")
            
            # Apply customizations
            group_data = template.copy()
            group_data["name"] = group_name
            
            if customizations:
                group_data.update(customizations)
            
            # Create the group
            return await self.create_group(group_data, org_id, created_by)
            
        except Exception as e:
            logger.error(f"Failed to create group from template: {str(e)}")
            raise
    
    def _validate_group_data(self, group_data: Dict[str, Any]):
        """Validate group data"""
        # Required fields
        if not group_data.get("name"):
            raise ValidationError("Group name is required")
        
        # Validate group type
        if "group_type" in group_data:
            try:
                GroupType(group_data["group_type"])
            except ValueError:
                raise ValidationError(f"Invalid group type: {group_data['group_type']}")
        
        # Validate rules for dynamic groups
        if group_data.get("group_type") in ["dynamic", "hybrid"]:
            if not group_data.get("rules"):
                raise ValidationError("Dynamic groups require at least one rule")
        
        # Validate rule logic
        if "rule_logic" in group_data and group_data["rule_logic"] not in ["AND", "OR"]:
            raise ValidationError("Rule logic must be AND or OR")
    
    async def _evaluate_dynamic_membership(self, group: DeviceGroup):
        """Evaluate and update membership for a dynamic group"""
        try:
            # Get all devices in the organization
            devices = await self.device_repo.find_many({"org_id": group.org_id})
            
            current_members = set(await self.group_repo.get_group_devices(
                group.group_id, group.org_id
            ))
            new_members = set()
            
            # Evaluate each device
            for device in devices:
                device_dict = device.to_dict() if hasattr(device, 'to_dict') else device
                
                if await self.group_repo.evaluate_dynamic_membership(group, device_dict):
                    new_members.add(device_dict["device_id"])
            
            # Add new members
            to_add = new_members - current_members
            for device_id in to_add:
                await self.group_repo.add_device_to_group(
                    device_id, group.group_id, group.org_id,
                    membership_type="dynamic"
                )
            
            # Remove old members (only if purely dynamic group)
            if group.group_type == GroupType.DYNAMIC:
                to_remove = current_members - new_members
                for device_id in to_remove:
                    await self.group_repo.remove_device_from_group(
                        device_id, group.group_id, group.org_id
                    )
            
            logger.info(f"Updated dynamic membership for group {group.group_id}: "
                       f"+{len(to_add)} -{len(current_members - new_members)}")
            
        except Exception as e:
            logger.error(f"Failed to evaluate dynamic membership: {str(e)}")
    
    async def _execute_on_devices(
        self,
        devices: List[Device],
        operation_type: str,
        payload: Dict[str, Any],
        org_id: str
    ) -> Dict[str, Any]:
        """Execute operation on multiple devices"""
        device_statuses = {}
        completed = 0
        failed = 0
        
        # Execute in batches for better performance
        batch_size = 10
        for i in range(0, len(devices), batch_size):
            batch = devices[i:i + batch_size]
            
            # Execute operations concurrently within batch
            tasks = []
            for device in batch:
                device_id = device.device_id if hasattr(device, 'device_id') else device["device_id"]
                
                if operation_type == "update":
                    task = self.device_repo.update(device_id, payload, org_id)
                elif operation_type == "command":
                    # Implement command execution
                    task = self._send_device_command(device_id, payload, org_id)
                elif operation_type == "configuration":
                    # Implement configuration update
                    task = self._update_device_configuration(device_id, payload, org_id)
                else:
                    logger.warning(f"Unknown operation type: {operation_type}")
                    continue
                
                tasks.append((device_id, task))
            
            # Wait for batch to complete
            for device_id, task in tasks:
                try:
                    await task
                    device_statuses[device_id] = "completed"
                    completed += 1
                except Exception as e:
                    device_statuses[device_id] = f"failed: {str(e)}"
                    failed += 1
        
        return {
            "device_statuses": device_statuses,
            "completed": completed,
            "failed": failed
        }
    
    async def _send_device_command(
        self,
        device_id: str,
        command: Dict[str, Any],
        org_id: str
    ):
        """Send command to device (placeholder)"""
        # TODO: Implement actual command sending
        logger.info(f"Sending command to device {device_id}: {command}")
        await asyncio.sleep(0.1)  # Simulate command execution
    
    async def _update_device_configuration(
        self,
        device_id: str,
        configuration: Dict[str, Any],
        org_id: str
    ):
        """Update device configuration (placeholder)"""
        # TODO: Implement actual configuration update
        logger.info(f"Updating configuration for device {device_id}: {configuration}")
        await asyncio.sleep(0.1)  # Simulate configuration update
    
    def _get_group_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get predefined group templates"""
        templates = {
            "location_based": {
                "group_type": "dynamic",
                "grouping_strategy": "location",
                "rules": [
                    {
                        "rule_id": str(uuid.uuid4()),
                        "field": "location.building",
                        "operator": "eq",
                        "value": "{{building_name}}",
                        "case_sensitive": False
                    }
                ],
                "metadata": {
                    "template": "location_based",
                    "description": "Group devices by physical location"
                }
            },
            "type_based": {
                "group_type": "dynamic",
                "grouping_strategy": "type",
                "rules": [
                    {
                        "rule_id": str(uuid.uuid4()),
                        "field": "device_type",
                        "operator": "eq",
                        "value": "{{device_type}}",
                        "case_sensitive": False
                    }
                ],
                "metadata": {
                    "template": "type_based",
                    "description": "Group devices by device type"
                }
            },
            "customer_based": {
                "group_type": "dynamic",
                "grouping_strategy": "customer",
                "rules": [
                    {
                        "rule_id": str(uuid.uuid4()),
                        "field": "metadata.customer_id",
                        "operator": "eq",
                        "value": "{{customer_id}}",
                        "case_sensitive": True
                    }
                ],
                "metadata": {
                    "template": "customer_based",
                    "description": "Group devices by customer"
                }
            },
            "tag_based": {
                "group_type": "dynamic",
                "grouping_strategy": "tag",
                "rules": [
                    {
                        "rule_id": str(uuid.uuid4()),
                        "field": "tags",
                        "operator": "contains",
                        "value": "{{tag_name}}",
                        "case_sensitive": False
                    }
                ],
                "metadata": {
                    "template": "tag_based",
                    "description": "Group devices by tags"
                }
            }
        }
        
        return templates.get(template_name)