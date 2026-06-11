# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .device_models import DeviceType, ConnectionProtocol


class TemplateCategory(Enum):
    """Template category enumeration"""
    INDUSTRIAL = "industrial"
    CONSUMER = "consumer"
    AGRICULTURE = "agriculture"
    HEALTHCARE = "healthcare"
    AUTOMOTIVE = "automotive"
    SMART_HOME = "smart_home"
    SMART_CITY = "smart_city"
    ENERGY = "energy"
    CUSTOM = "custom"


class TemplateStatus(Enum):
    """Template status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class ValidationRule:
    """Validation rule for template fields"""
    field_path: str  # JSON path to field (e.g., "metadata.sensor.range.min")
    rule_type: str  # required, type, range, regex, enum
    value: Any  # The validation value/constraint
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_path": self.field_path,
            "rule_type": self.rule_type,
            "value": self.value,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationRule":
        return cls(
            field_path=data["field_path"],
            rule_type=data["rule_type"],
            value=data["value"],
            error_message=data.get("error_message")
        )


@dataclass
class TemplateMetadata:
    """Template metadata with schema and defaults"""
    schema: Dict[str, Any]  # JSON Schema for validation
    defaults: Dict[str, Any]  # Default values
    required_fields: List[str] = field(default_factory=list)
    field_descriptions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "defaults": self.defaults,
            "required_fields": self.required_fields,
            "field_descriptions": self.field_descriptions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateMetadata":
        return cls(
            schema=data["schema"],
            defaults=data["defaults"],
            required_fields=data.get("required_fields", []),
            field_descriptions=data.get("field_descriptions", {})
        )


@dataclass
class DeviceTemplate:
    """Device template model with metadata, configs, and validation"""
    template_id: str
    org_id: str
    name: str
    description: str
    category: TemplateCategory
    device_type: DeviceType
    status: TemplateStatus = TemplateStatus.DRAFT
    
    # Template configuration
    default_config: Dict[str, Any] = field(default_factory=dict)
    metadata_template: TemplateMetadata = field(default_factory=lambda: TemplateMetadata({}, {}))
    
    # Connection settings
    supported_protocols: List[ConnectionProtocol] = field(default_factory=list)
    default_protocol: Optional[ConnectionProtocol] = None
    
    # Validation rules
    validation_rules: List[ValidationRule] = field(default_factory=list)
    validation_schema: Optional[Dict[str, Any]] = None  # JSON Schema
    
    # Inheritance and composition
    parent_template_id: Optional[str] = None
    composed_template_ids: List[str] = field(default_factory=list)
    allow_inheritance: bool = True
    
    # Versioning
    version: str = "1.0.0"
    version_notes: Optional[str] = None
    
    # Industry standards
    standards_compliance: List[str] = field(default_factory=list)  # e.g., ["ISO-12345", "IEC-67890"]
    
    # Default settings
    default_tags: List[str] = field(default_factory=list)
    default_groups: List[str] = field(default_factory=list)
    
    # Auto-provisioning
    auto_provision: bool = False
    provision_script: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    # Usage tracking
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "template_id": self.template_id,
            "org_id": self.org_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "device_type": self.device_type.value,
            "status": self.status.value,
            "default_config": self.default_config,
            "metadata_template": self.metadata_template.to_dict(),
            "supported_protocols": [p.value for p in self.supported_protocols],
            "default_protocol": self.default_protocol.value if self.default_protocol else None,
            "validation_rules": [r.to_dict() for r in self.validation_rules],
            "validation_schema": self.validation_schema,
            "parent_template_id": self.parent_template_id,
            "composed_template_ids": self.composed_template_ids,
            "allow_inheritance": self.allow_inheritance,
            "version": self.version,
            "version_notes": self.version_notes,
            "standards_compliance": self.standards_compliance,
            "default_tags": self.default_tags,
            "default_groups": self.default_groups,
            "auto_provision": self.auto_provision,
            "provision_script": self.provision_script,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceTemplate":
        """Create from dictionary"""
        return cls(
            template_id=data["template_id"],
            org_id=data["org_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"]),
            device_type=DeviceType(data["device_type"]),
            status=TemplateStatus(data.get("status", "draft")),
            default_config=data.get("default_config", {}),
            metadata_template=TemplateMetadata.from_dict(data["metadata_template"]) if data.get("metadata_template") else TemplateMetadata({}, {}),
            supported_protocols=[ConnectionProtocol(p) for p in data.get("supported_protocols", [])],
            default_protocol=ConnectionProtocol(data["default_protocol"]) if data.get("default_protocol") else None,
            validation_rules=[ValidationRule.from_dict(r) for r in data.get("validation_rules", [])],
            validation_schema=data.get("validation_schema"),
            parent_template_id=data.get("parent_template_id"),
            composed_template_ids=data.get("composed_template_ids", []),
            allow_inheritance=data.get("allow_inheritance", True),
            version=data.get("version", "1.0.0"),
            version_notes=data.get("version_notes"),
            standards_compliance=data.get("standards_compliance", []),
            default_tags=data.get("default_tags", []),
            default_groups=data.get("default_groups", []),
            auto_provision=data.get("auto_provision", False),
            provision_script=data.get("provision_script"),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
            usage_count=data.get("usage_count", 0),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None
        )


@dataclass
class TemplateVersion:
    """Template version tracking"""
    version_id: str
    template_id: str
    org_id: str
    version_number: str  # Semantic versioning: major.minor.patch
    changes: List[str]  # List of changes in this version
    template_snapshot: Dict[str, Any]  # Full template at this version
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "template_id": self.template_id,
            "org_id": self.org_id,
            "version_number": self.version_number,
            "changes": self.changes,
            "template_snapshot": self.template_snapshot,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVersion":
        return cls(
            version_id=data["version_id"],
            template_id=data["template_id"],
            org_id=data["org_id"],
            version_number=data["version_number"],
            changes=data.get("changes", []),
            template_snapshot=data["template_snapshot"],
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            created_by=data.get("created_by"),
            is_active=data.get("is_active", True)
        )


@dataclass
class TemplateInstance:
    """Instance of a device created from a template"""
    instance_id: str
    device_id: str
    template_id: str
    template_version: str
    org_id: str
    
    # Overrides from template defaults
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    metadata_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Instance metadata
    instantiated_at: datetime = field(default_factory=datetime.utcnow)
    instantiated_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "device_id": self.device_id,
            "template_id": self.template_id,
            "template_version": self.template_version,
            "org_id": self.org_id,
            "config_overrides": self.config_overrides,
            "metadata_overrides": self.metadata_overrides,
            "instantiated_at": self.instantiated_at.isoformat(),
            "instantiated_by": self.instantiated_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateInstance":
        return cls(
            instance_id=data["instance_id"],
            device_id=data["device_id"],
            template_id=data["template_id"],
            template_version=data["template_version"],
            org_id=data["org_id"],
            config_overrides=data.get("config_overrides", {}),
            metadata_overrides=data.get("metadata_overrides", {}),
            instantiated_at=datetime.fromisoformat(data["instantiated_at"]) if isinstance(data.get("instantiated_at"), str) else data.get("instantiated_at", datetime.utcnow()),
            instantiated_by=data.get("instantiated_by")
        )


# Industry standard templates - predefined configurations
INDUSTRY_STANDARD_TEMPLATES = {
    "temperature_sensor": {
        "name": "Temperature Sensor",
        "description": "Standard temperature sensor template",
        "category": TemplateCategory.INDUSTRIAL,
        "device_type": DeviceType.SENSOR,
        "default_config": {
            "sampling_rate": 60,  # seconds
            "unit": "celsius",
            "precision": 0.1,
            "range": {"min": -50, "max": 150}
        },
        "metadata_template": {
            "schema": {
                "type": "object",
                "properties": {
                    "sensor": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["temperature"]},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit", "kelvin"]},
                            "accuracy": {"type": "number"},
                            "resolution": {"type": "number"}
                        },
                        "required": ["type", "unit"]
                    }
                }
            },
            "defaults": {
                "sensor": {
                    "type": "temperature",
                    "unit": "celsius",
                    "accuracy": 0.5,
                    "resolution": 0.1
                }
            }
        },
        "supported_protocols": [ConnectionProtocol.MQTT, ConnectionProtocol.HTTPS],
        "default_protocol": ConnectionProtocol.MQTT,
        "standards_compliance": ["ISO/IEC 30141", "IEC 61131-9"]
    },
    
    "gateway_device": {
        "name": "IoT Gateway",
        "description": "Standard IoT gateway template for edge computing",
        "category": TemplateCategory.INDUSTRIAL,
        "device_type": DeviceType.GATEWAY,
        "default_config": {
            "max_devices": 100,
            "edge_computing": True,
            "data_aggregation": True,
            "local_storage": "1GB",
            "protocols": ["mqtt", "modbus", "opcua"]
        },
        "metadata_template": {
            "schema": {
                "type": "object",
                "properties": {
                    "gateway": {
                        "type": "object",
                        "properties": {
                            "manufacturer": {"type": "string"},
                            "model": {"type": "string"},
                            "cpu": {"type": "string"},
                            "memory": {"type": "string"},
                            "storage": {"type": "string"},
                            "interfaces": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["manufacturer", "model"]
                    }
                }
            },
            "defaults": {
                "gateway": {
                    "interfaces": ["ethernet", "wifi", "cellular"]
                }
            }
        },
        "supported_protocols": [ConnectionProtocol.MQTT, ConnectionProtocol.HTTPS, ConnectionProtocol.WEBSOCKET],
        "default_protocol": ConnectionProtocol.MQTT,
        "standards_compliance": ["ISO/IEC 30141", "IEEE 2413-2019"]
    },
    
    "smart_actuator": {
        "name": "Smart Actuator",
        "description": "Actuator with feedback and control capabilities",
        "category": TemplateCategory.INDUSTRIAL,
        "device_type": DeviceType.ACTUATOR,
        "default_config": {
            "control_modes": ["manual", "automatic", "scheduled"],
            "feedback_enabled": True,
            "safety_limits": True,
            "response_time_ms": 100
        },
        "metadata_template": {
            "schema": {
                "type": "object",
                "properties": {
                    "actuator": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "power_rating": {"type": "string"},
                            "control_signal": {"type": "string"},
                            "feedback_type": {"type": "string"}
                        },
                        "required": ["type", "control_signal"]
                    }
                }
            },
            "defaults": {
                "actuator": {
                    "control_signal": "4-20mA",
                    "feedback_type": "position"
                }
            }
        },
        "supported_protocols": [ConnectionProtocol.MQTT, ConnectionProtocol.HTTPS],
        "default_protocol": ConnectionProtocol.MQTT,
        "standards_compliance": ["IEC 61131", "ISA-95"]
    }
}