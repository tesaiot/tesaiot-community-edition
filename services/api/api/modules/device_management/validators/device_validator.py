# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

import logging
import re
from typing import Dict, Any
from uuid import UUID

from ..interfaces.device_interfaces import IDeviceValidator
from ..models.device_models import DeviceType, DeviceStatus, ConnectionProtocol

logger = logging.getLogger(__name__)


class DeviceValidator(IDeviceValidator):
    """Implementation of Device Validation"""
    
    def __init__(self):
        # Regex patterns for validation
        self.mac_address_pattern = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        self.ip_address_pattern = re.compile(
            r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        )
        self.device_id_pattern = re.compile(r"^[a-zA-Z0-9\-_]+$")
        
        logger.info("DeviceValidator initialized")
    
    def validate_device_data(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate device registration data"""
        errors = {}
        validated_data = {}
        
        # Required fields
        if not device_data.get("name"):
            errors["name"] = "Device name is required"
        else:
            name = str(device_data["name"]).strip()
            if len(name) < 1 or len(name) > 255:
                errors["name"] = "Device name must be between 1 and 255 characters"
            else:
                validated_data["name"] = name
        
        # Device type validation
        if not device_data.get("device_type"):
            errors["device_type"] = "Device type is required"
        else:
            try:
                device_type = device_data["device_type"]
                if isinstance(device_type, str):
                    DeviceType(device_type)  # Validate enum value
                    validated_data["device_type"] = device_type
                else:
                    errors["device_type"] = "Device type must be a string"
            except ValueError:
                valid_types = [t.value for t in DeviceType]
                errors["device_type"] = f"Invalid device type. Must be one of: {', '.join(valid_types)}"
        
        # Protocol validation (optional, defaults to mqtt)
        if device_data.get("protocol"):
            try:
                protocol = device_data["protocol"]
                if isinstance(protocol, str):
                    ConnectionProtocol(protocol)  # Validate enum value
                    validated_data["protocol"] = protocol
                else:
                    errors["protocol"] = "Protocol must be a string"
            except ValueError:
                valid_protocols = [p.value for p in ConnectionProtocol]
                errors["protocol"] = f"Invalid protocol. Must be one of: {', '.join(valid_protocols)}"
        else:
            validated_data["protocol"] = ConnectionProtocol.MQTT.value
        
        # MAC address validation (optional)
        if device_data.get("mac_address"):
            mac_address = device_data["mac_address"]
            if not self.mac_address_pattern.match(mac_address):
                errors["mac_address"] = "Invalid MAC address format"
            else:
                validated_data["mac_address"] = mac_address.upper()
        
        # IP address validation (optional)
        if device_data.get("ip_address"):
            ip_address = device_data["ip_address"]
            if not self.ip_address_pattern.match(ip_address):
                errors["ip_address"] = "Invalid IP address format"
            else:
                validated_data["ip_address"] = ip_address
        
        # Firmware version validation (optional)
        if device_data.get("firmware_version"):
            firmware_version = str(device_data["firmware_version"]).strip()
            if len(firmware_version) > 50:
                errors["firmware_version"] = "Firmware version must be 50 characters or less"
            else:
                validated_data["firmware_version"] = firmware_version
        
        # Hardware version validation (optional)
        if device_data.get("hardware_version"):
            hardware_version = str(device_data["hardware_version"]).strip()
            if len(hardware_version) > 50:
                errors["hardware_version"] = "Hardware version must be 50 characters or less"
            else:
                validated_data["hardware_version"] = hardware_version
        
        # Serial number validation (optional)
        if device_data.get("serial_number"):
            serial_number = str(device_data["serial_number"]).strip()
            if len(serial_number) > 100:
                errors["serial_number"] = "Serial number must be 100 characters or less"
            else:
                validated_data["serial_number"] = serial_number
        
        # Location validation (optional)
        if device_data.get("location"):
            location = device_data["location"]
            if isinstance(location, dict):
                # Basic location validation
                if "lat" in location and "lng" in location:
                    try:
                        lat = float(location["lat"])
                        lng = float(location["lng"])
                        if -90 <= lat <= 90 and -180 <= lng <= 180:
                            validated_data["location"] = location
                        else:
                            errors["location"] = "Invalid latitude/longitude values"
                    except (ValueError, TypeError):
                        errors["location"] = "Latitude and longitude must be numbers"
                else:
                    validated_data["location"] = location
            else:
                errors["location"] = "Location must be an object"
        
        # Metadata validation (optional)
        if device_data.get("metadata"):
            if isinstance(device_data["metadata"], dict):
                validated_data["metadata"] = device_data["metadata"]
            else:
                errors["metadata"] = "Metadata must be an object"
        
        # Tags validation (optional)
        if device_data.get("tags"):
            if isinstance(device_data["tags"], list):
                # Validate each tag
                valid_tags = []
                for tag in device_data["tags"]:
                    if isinstance(tag, str) and len(tag.strip()) > 0:
                        valid_tags.append(tag.strip())
                validated_data["tags"] = valid_tags
            else:
                errors["tags"] = "Tags must be an array"
        
        # Group IDs validation (optional)
        if device_data.get("group_ids"):
            if isinstance(device_data["group_ids"], list):
                # Validate each group ID
                valid_group_ids = []
                for group_id in device_data["group_ids"]:
                    if isinstance(group_id, str) and len(group_id.strip()) > 0:
                        valid_group_ids.append(group_id.strip())
                validated_data["group_ids"] = valid_group_ids
            else:
                errors["group_ids"] = "Group IDs must be an array"
        
        # If there are validation errors, raise exception
        if errors:
            raise ValueError(f"Validation errors: {errors}")
        
        return validated_data
    
    def validate_device_update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate device update data"""
        errors = {}
        validated_updates = {}
        
        # Name validation (optional for updates)
        if "name" in updates:
            name = str(updates["name"]).strip()
            if len(name) < 1 or len(name) > 255:
                errors["name"] = "Device name must be between 1 and 255 characters"
            else:
                validated_updates["name"] = name
        
        # Firmware version validation
        if "firmware_version" in updates:
            firmware_version = str(updates["firmware_version"]).strip()
            if len(firmware_version) > 50:
                errors["firmware_version"] = "Firmware version must be 50 characters or less"
            else:
                validated_updates["firmware_version"] = firmware_version
        
        # Hardware version validation
        if "hardware_version" in updates:
            hardware_version = str(updates["hardware_version"]).strip()
            if len(hardware_version) > 50:
                errors["hardware_version"] = "Hardware version must be 50 characters or less"
            else:
                validated_updates["hardware_version"] = hardware_version
        
        # Location validation
        if "location" in updates:
            location = updates["location"]
            if isinstance(location, dict):
                if "lat" in location and "lng" in location:
                    try:
                        lat = float(location["lat"])
                        lng = float(location["lng"])
                        if -90 <= lat <= 90 and -180 <= lng <= 180:
                            validated_updates["location"] = location
                        else:
                            errors["location"] = "Invalid latitude/longitude values"
                    except (ValueError, TypeError):
                        errors["location"] = "Latitude and longitude must be numbers"
                else:
                    validated_updates["location"] = location
            else:
                errors["location"] = "Location must be an object"
        
        # Metadata validation
        if "metadata" in updates:
            if isinstance(updates["metadata"], dict):
                validated_updates["metadata"] = updates["metadata"]
            else:
                errors["metadata"] = "Metadata must be an object"
        
        # Tags validation
        if "tags" in updates:
            if isinstance(updates["tags"], list):
                valid_tags = []
                for tag in updates["tags"]:
                    if isinstance(tag, str) and len(tag.strip()) > 0:
                        valid_tags.append(tag.strip())
                validated_updates["tags"] = valid_tags
            else:
                errors["tags"] = "Tags must be an array"
        
        # Group IDs validation
        if "group_ids" in updates:
            if isinstance(updates["group_ids"], list):
                valid_group_ids = []
                for group_id in updates["group_ids"]:
                    if isinstance(group_id, str) and len(group_id.strip()) > 0:
                        valid_group_ids.append(group_id.strip())
                validated_updates["group_ids"] = valid_group_ids
            else:
                errors["group_ids"] = "Group IDs must be an array"
        
        # Don't allow certain fields to be updated
        forbidden_fields = ["device_id", "org_id", "created_at", "device_type", "protocol"]
        for field in forbidden_fields:
            if field in updates:
                errors[field] = f"Field '{field}' cannot be updated"
        
        # If there are validation errors, raise exception
        if errors:
            raise ValueError(f"Validation errors: {errors}")
        
        return validated_updates
    
    def validate_device_id(self, device_id: str) -> bool:
        """Validate device ID format"""
        if not device_id:
            return False
        
        # Check if it's a valid UUID
        try:
            UUID(device_id)
            return True
        except ValueError:
            pass
        
        # Check if it matches custom pattern
        if self.device_id_pattern.match(device_id):
            return True
        
        return False
    
    def validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search filters"""
        validated_filters = {}
        errors = {}
        
        # Status filter
        if filters.get("status"):
            try:
                DeviceStatus(filters["status"])
                validated_filters["status"] = filters["status"]
            except ValueError:
                valid_statuses = [s.value for s in DeviceStatus]
                errors["status"] = f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        # Device type filter
        if filters.get("device_type"):
            try:
                DeviceType(filters["device_type"])
                validated_filters["device_type"] = filters["device_type"]
            except ValueError:
                valid_types = [t.value for t in DeviceType]
                errors["device_type"] = f"Invalid device type. Must be one of: {', '.join(valid_types)}"
        
        # Protocol filter
        if filters.get("protocol"):
            try:
                ConnectionProtocol(filters["protocol"])
                validated_filters["protocol"] = filters["protocol"]
            except ValueError:
                valid_protocols = [p.value for p in ConnectionProtocol]
                errors["protocol"] = f"Invalid protocol. Must be one of: {', '.join(valid_protocols)}"
        
        # Tags filter
        if filters.get("tags"):
            if isinstance(filters["tags"], list):
                validated_filters["tags"] = filters["tags"]
            else:
                errors["tags"] = "Tags filter must be an array"
        
        # Group ID filter
        if filters.get("group_id"):
            if isinstance(filters["group_id"], str):
                validated_filters["group_id"] = filters["group_id"]
            else:
                errors["group_id"] = "Group ID must be a string"
        
        # Search filter
        if filters.get("search"):
            if isinstance(filters["search"], str):
                validated_filters["search"] = filters["search"]
            else:
                errors["search"] = "Search must be a string"
        
        # Sort field validation
        valid_sort_fields = ["created_at", "updated_at", "name", "device_type", "status", "last_seen"]
        if filters.get("sort_by"):
            if filters["sort_by"] in valid_sort_fields:
                validated_filters["sort_by"] = filters["sort_by"]
            else:
                errors["sort_by"] = f"Invalid sort field. Must be one of: {', '.join(valid_sort_fields)}"
        
        # Sort order validation
        if filters.get("sort_order"):
            if filters["sort_order"] in ["asc", "desc"]:
                validated_filters["sort_order"] = filters["sort_order"]
            else:
                errors["sort_order"] = "Sort order must be 'asc' or 'desc'"
        
        # If there are validation errors, raise exception
        if errors:
            raise ValueError(f"Filter validation errors: {errors}")
        
        return validated_filters