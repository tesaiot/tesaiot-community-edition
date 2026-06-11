# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - Group Models
Domain models for device grouping and hierarchical organization

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum


class GroupType(Enum):
    """Types of device groups"""
    STATIC = "static"  # Manual membership
    DYNAMIC = "dynamic"  # Rule-based membership
    HYBRID = "hybrid"  # Both manual and rule-based


class PolicyAction(Enum):
    """Policy actions that can be applied to groups"""
    ALLOW = "allow"
    DENY = "deny"
    INHERIT = "inherit"


class GroupingStrategy(Enum):
    """Common grouping strategies"""
    LOCATION = "location"
    TYPE = "type"
    CUSTOMER = "customer"
    FUNCTION = "function"
    TAG = "tag"
    CUSTOM = "custom"


@dataclass
class GroupRule:
    """Rule for dynamic group membership"""
    rule_id: str
    field: str  # Field to evaluate (e.g., "location.city", "device_type", "tags")
    operator: str  # eq, ne, in, not_in, contains, starts_with, regex
    value: Any  # Value to compare against
    case_sensitive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "case_sensitive": self.case_sensitive
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupRule":
        """Create from dictionary"""
        return cls(
            rule_id=data.get("rule_id", ""),
            field=data["field"],
            operator=data["operator"],
            value=data["value"],
            case_sensitive=data.get("case_sensitive", False)
        )


@dataclass
class GroupPolicy:
    """Policy that can be applied to a group"""
    policy_id: str
    name: str
    resource: str  # Resource the policy applies to (e.g., "telemetry", "commands", "configuration")
    action: PolicyAction
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority policies override lower ones
    inheritable: bool = True  # Whether child groups inherit this policy
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "resource": self.resource,
            "action": self.action.value,
            "conditions": self.conditions,
            "priority": self.priority,
            "inheritable": self.inheritable
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GroupPolicy":
        """Create from dictionary"""
        return cls(
            policy_id=data["policy_id"],
            name=data["name"],
            resource=data["resource"],
            action=PolicyAction(data["action"]),
            conditions=data.get("conditions", {}),
            priority=data.get("priority", 0),
            inheritable=data.get("inheritable", True)
        )


@dataclass
class DeviceGroup:
    """Enhanced device group model with hierarchical structure and policies"""
    group_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    group_type: GroupType = GroupType.STATIC
    parent_group_id: Optional[str] = None
    child_group_ids: List[str] = field(default_factory=list)
    
    # Membership
    device_ids: Set[str] = field(default_factory=set)  # Static members
    rules: List[GroupRule] = field(default_factory=list)  # Dynamic membership rules
    rule_logic: str = "AND"  # AND or OR for multiple rules
    
    # Policies and settings
    policies: List[GroupPolicy] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    grouping_strategy: Optional[GroupingStrategy] = None
    
    # Audit fields
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    # Performance optimization
    member_count: int = 0  # Cached count of members
    last_membership_update: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "group_id": self.group_id,
            "org_id": self.org_id,
            "name": self.name,
            "description": self.description,
            "group_type": self.group_type.value,
            "parent_group_id": self.parent_group_id,
            "child_group_ids": self.child_group_ids,
            "device_ids": list(self.device_ids),
            "rules": [rule.to_dict() for rule in self.rules],
            "rule_logic": self.rule_logic,
            "policies": [policy.to_dict() for policy in self.policies],
            "settings": self.settings,
            "metadata": self.metadata,
            "tags": self.tags,
            "grouping_strategy": self.grouping_strategy.value if self.grouping_strategy else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "member_count": self.member_count,
            "last_membership_update": self.last_membership_update.isoformat() if self.last_membership_update else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceGroup":
        """Create from dictionary"""
        return cls(
            group_id=data["group_id"],
            org_id=data["org_id"],
            name=data["name"],
            description=data.get("description"),
            group_type=GroupType(data.get("group_type", "static")),
            parent_group_id=data.get("parent_group_id"),
            child_group_ids=data.get("child_group_ids", []),
            device_ids=set(data.get("device_ids", [])),
            rules=[GroupRule.from_dict(r) for r in data.get("rules", [])],
            rule_logic=data.get("rule_logic", "AND"),
            policies=[GroupPolicy.from_dict(p) for p in data.get("policies", [])],
            settings=data.get("settings", {}),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            grouping_strategy=GroupingStrategy(data["grouping_strategy"]) if data.get("grouping_strategy") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
            member_count=data.get("member_count", 0),
            last_membership_update=datetime.fromisoformat(data["last_membership_update"]) if data.get("last_membership_update") else None
        )


@dataclass
class GroupMembership:
    """Many-to-many relationship between devices and groups"""
    membership_id: str
    device_id: str
    group_id: str
    org_id: str
    membership_type: str = "static"  # static or dynamic
    added_at: datetime = field(default_factory=datetime.utcnow)
    added_by: Optional[str] = None
    rule_id: Optional[str] = None  # If added by rule, which rule
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "membership_id": self.membership_id,
            "device_id": self.device_id,
            "group_id": self.group_id,
            "org_id": self.org_id,
            "membership_type": self.membership_type,
            "added_at": self.added_at.isoformat(),
            "added_by": self.added_by,
            "rule_id": self.rule_id,
            "metadata": self.metadata
        }


@dataclass
class GroupOperation:
    """Operation to be applied to all devices in a group"""
    operation_id: str
    group_id: str
    org_id: str
    operation_type: str  # update, command, configuration, etc.
    payload: Dict[str, Any]
    status: str = "pending"  # pending, in_progress, completed, failed
    device_statuses: Dict[str, str] = field(default_factory=dict)  # device_id -> status
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    error_message: Optional[str] = None
    total_devices: int = 0
    completed_devices: int = 0
    failed_devices: int = 0


@dataclass
class GroupHierarchy:
    """Represents the hierarchical structure of groups"""
    group_id: str
    name: str
    level: int
    parent_id: Optional[str] = None
    children: List["GroupHierarchy"] = field(default_factory=list)
    device_count: int = 0
    total_device_count: int = 0  # Including all descendants
    policies: List[GroupPolicy] = field(default_factory=list)
    inherited_policies: List[GroupPolicy] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including children"""
        return {
            "group_id": self.group_id,
            "name": self.name,
            "level": self.level,
            "parent_id": self.parent_id,
            "children": [child.to_dict() for child in self.children],
            "device_count": self.device_count,
            "total_device_count": self.total_device_count,
            "policies": [p.to_dict() for p in self.policies],
            "inherited_policies": [p.to_dict() for p in self.inherited_policies]
        }


@dataclass
class GroupTemplate:
    """Template for creating groups with predefined settings"""
    template_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    group_type: GroupType = GroupType.STATIC
    default_rules: List[GroupRule] = field(default_factory=list)
    default_policies: List[GroupPolicy] = field(default_factory=list)
    default_settings: Dict[str, Any] = field(default_factory=dict)
    grouping_strategy: Optional[GroupingStrategy] = None
    metadata_template: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_active: bool = True