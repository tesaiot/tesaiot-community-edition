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


class DeviceStatus(Enum):
    """Device status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"


class DeviceType(Enum):
    """Device type enumeration"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    CONTROLLER = "controller"
    HYBRID = "hybrid"


class ConnectionProtocol(Enum):
    """Device connection protocol"""
    MQTT = "mqtt"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    COAP = "coap"
    LORAWAN = "lorawan"


@dataclass
class Device:
    """Device domain model"""
    device_id: str
    org_id: str
    name: str
    device_type: DeviceType
    status: DeviceStatus
    protocol: ConnectionProtocol
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    serial_number: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None
    certificate_id: Optional[str] = None
    group_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "device_id": self.device_id,
            "org_id": self.org_id,
            "name": self.name,
            "device_type": self.device_type.value,
            "status": self.status.value,
            "protocol": self.protocol.value,
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "firmware_version": self.firmware_version,
            "hardware_version": self.hardware_version,
            "serial_number": self.serial_number,
            "location": self.location,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "certificate_id": self.certificate_id,
            "group_ids": self.group_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Create from dictionary"""
        return cls(
            device_id=data["device_id"],
            org_id=data["org_id"],
            name=data["name"],
            device_type=DeviceType(data["device_type"]),
            status=DeviceStatus(data.get("status", "inactive")),
            protocol=ConnectionProtocol(data.get("protocol", "mqtt")),
            mac_address=data.get("mac_address"),
            ip_address=data.get("ip_address"),
            firmware_version=data.get("firmware_version"),
            hardware_version=data.get("hardware_version"),
            serial_number=data.get("serial_number"),
            location=data.get("location"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at", datetime.utcnow()),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at", datetime.utcnow()),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            certificate_id=data.get("certificate_id"),
            group_ids=data.get("group_ids", [])
        )


@dataclass
class DeviceCommand:
    """Device command model"""
    command_id: str
    device_id: str
    org_id: str
    command_type: str
    payload: Dict[str, Any]
    status: str = "pending"  # pending, sent, acknowledged, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30


@dataclass
class DeviceConfiguration:
    """Device configuration model"""
    device_id: str
    org_id: str
    config_version: str
    configuration: Dict[str, Any]
    template_id: Optional[str] = None
    applied_at: datetime = field(default_factory=datetime.utcnow)
    applied_by: Optional[str] = None
    validation_status: str = "valid"  # valid, invalid, pending
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class DeviceCertificate:
    """Device certificate model"""
    certificate_id: str
    device_id: str
    org_id: str
    certificate_pem: str
    private_key_pem: Optional[str] = None  # Only returned on creation
    fingerprint: str = ""
    serial_number: str = ""
    subject: Dict[str, str] = field(default_factory=dict)
    issuer: Dict[str, str] = field(default_factory=dict)
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_until: datetime = field(default_factory=datetime.utcnow)
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProvisioningTemplate:
    """Device provisioning template model"""
    template_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    device_type: DeviceType = DeviceType.SENSOR
    protocol: ConnectionProtocol = ConnectionProtocol.MQTT
    default_configuration: Dict[str, Any] = field(default_factory=dict)
    metadata_template: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    auto_generate_certificate: bool = True
    auto_assign_groups: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_active: bool = True


@dataclass
class DeviceGroup:
    """Device group model"""
    group_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    parent_group_id: Optional[str] = None
    device_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None