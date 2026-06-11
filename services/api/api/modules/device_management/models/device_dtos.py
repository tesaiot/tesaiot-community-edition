# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class DeviceCreateDTO(BaseModel):
    """DTO for device creation"""
    name: str = Field(..., min_length=1, max_length=255)
    device_type: str = Field(..., description="Device type: sensor, actuator, gateway, controller, hybrid")
    protocol: str = Field(default="mqtt", description="Connection protocol")
    mac_address: Optional[str] = Field(None, regex="^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
    ip_address: Optional[str] = Field(None)
    firmware_version: Optional[str] = Field(None, max_length=50)
    hardware_version: Optional[str] = Field(None, max_length=50)
    serial_number: Optional[str] = Field(None, max_length=100)
    location: Optional[Dict[str, Any]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    tags: Optional[List[str]] = Field(default_factory=list)
    group_ids: Optional[List[str]] = Field(default_factory=list)
    auto_generate_certificate: bool = Field(default=True)
    
    @validator('device_type')
    def validate_device_type(cls, v):
        valid_types = ["sensor", "actuator", "gateway", "controller", "hybrid"]
        if v not in valid_types:
            raise ValueError(f"Device type must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('protocol')
    def validate_protocol(cls, v):
        valid_protocols = ["mqtt", "https", "websocket", "coap", "lorawan"]
        if v not in valid_protocols:
            raise ValueError(f"Protocol must be one of: {', '.join(valid_protocols)}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "name": "Temperature Sensor 01",
                "device_type": "sensor",
                "protocol": "mqtt",
                "mac_address": "00:1A:2B:3C:4D:5E",
                "firmware_version": "1.2.3",
                "location": {"lat": 13.7563, "lng": 100.5018},
                "tags": ["temperature", "indoor"],
                "auto_generate_certificate": True
            }
        }


class DeviceUpdateDTO(BaseModel):
    """DTO for device update"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    firmware_version: Optional[str] = Field(None, max_length=50)
    hardware_version: Optional[str] = Field(None, max_length=50)
    location: Optional[Dict[str, Any]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    group_ids: Optional[List[str]] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Temperature Sensor 01 - Updated",
                "firmware_version": "1.2.4",
                "location": {"lat": 13.7563, "lng": 100.5018, "floor": 2}
            }
        }


class DeviceResponseDTO(BaseModel):
    """DTO for device response"""
    device_id: str
    org_id: str
    name: str
    device_type: str
    status: str
    protocol: str
    mac_address: Optional[str]
    ip_address: Optional[str]
    firmware_version: Optional[str]
    hardware_version: Optional[str]
    serial_number: Optional[str]
    location: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime]
    certificate_id: Optional[str]
    group_ids: List[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceListQueryDTO(BaseModel):
    """DTO for device list query parameters"""
    status: Optional[str] = Field(None)
    device_type: Optional[str] = Field(None)
    protocol: Optional[str] = Field(None)
    tags: Optional[List[str]] = Field(None)
    group_id: Optional[str] = Field(None)
    search: Optional[str] = Field(None, description="Search in name, serial number")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")


class DeviceListResponseDTO(BaseModel):
    """DTO for device list response"""
    devices: List[DeviceResponseDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class DeviceCommandDTO(BaseModel):
    """DTO for device command"""
    command_type: str = Field(..., min_length=1, max_length=50)
    payload: Dict[str, Any] = Field(...)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    class Config:
        schema_extra = {
            "example": {
                "command_type": "restart",
                "payload": {"force": False, "delay_seconds": 5},
                "timeout_seconds": 60,
                "max_retries": 3
            }
        }


class DeviceCommandResponseDTO(BaseModel):
    """DTO for device command response"""
    command_id: str
    device_id: str
    command_type: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    completed_at: Optional[datetime]
    response: Optional[Dict[str, Any]]
    error: Optional[str]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceStatusUpdateDTO(BaseModel):
    """DTO for device status update"""
    status: str = Field(..., description="active, inactive, maintenance, error, offline")
    reason: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(None)
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["active", "inactive", "maintenance", "error", "offline"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class DeviceConfigurationDTO(BaseModel):
    """DTO for device configuration"""
    configuration: Dict[str, Any] = Field(...)
    template_id: Optional[str] = Field(None)
    validate_before_apply: bool = Field(default=True)
    
    class Config:
        schema_extra = {
            "example": {
                "configuration": {
                    "sampling_interval": 60,
                    "reporting_interval": 300,
                    "thresholds": {"temperature": {"min": -10, "max": 50}}
                },
                "validate_before_apply": True
            }
        }


class BulkDeviceOperationDTO(BaseModel):
    """DTO for bulk device operations"""
    device_ids: List[str] = Field(..., min_items=1, max_items=100)
    operation: str = Field(..., description="update, delete, command")
    data: Optional[Dict[str, Any]] = Field(None)
    
    @validator('operation')
    def validate_operation(cls, v):
        valid_operations = ["update", "delete", "command"]
        if v not in valid_operations:
            raise ValueError(f"Operation must be one of: {', '.join(valid_operations)}")
        return v


class DeviceProvisioningDTO(BaseModel):
    """DTO for device provisioning"""
    template_id: Optional[str] = Field(None)
    devices: List[DeviceCreateDTO] = Field(..., min_items=1, max_items=100)
    auto_start: bool = Field(default=False)
    
    class Config:
        schema_extra = {
            "example": {
                "template_id": "default-sensor-template",
                "devices": [
                    {
                        "name": "Sensor 001",
                        "device_type": "sensor",
                        "mac_address": "00:1A:2B:3C:4D:5E"
                    }
                ],
                "auto_start": True
            }
        }