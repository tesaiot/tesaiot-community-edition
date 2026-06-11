# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class IDeviceService(ABC):
    """Interface for Device Management Service"""
    
    @abstractmethod
    async def register_device(self, device_data: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Register a new device in the platform"""
        pass
    
    @abstractmethod
    async def get_device(self, device_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        """Get device details by ID"""
        pass
    
    @abstractmethod
    async def update_device(self, device_id: str, updates: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Update device information"""
        pass
    
    @abstractmethod
    async def delete_device(self, device_id: str, org_id: str) -> bool:
        """Delete a device"""
        pass
    
    @abstractmethod
    async def list_devices(self, filters: Dict[str, Any], pagination: Dict[str, int], org_id: str) -> List[Dict[str, Any]]:
        """List devices with filters and pagination"""
        pass
    
    @abstractmethod
    async def get_device_status(self, device_id: str, org_id: str) -> Dict[str, Any]:
        """Get current device status"""
        pass
    
    @abstractmethod
    async def update_device_status(self, device_id: str, status: Dict[str, Any], org_id: str) -> bool:
        """Update device status"""
        pass


class IDeviceRepository(ABC):
    """Interface for Device Repository"""
    
    @abstractmethod
    async def create(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create device in database"""
        pass
    
    @abstractmethod
    async def find_by_id(self, device_id: str, org_id: str) -> Optional[Dict[str, Any]]:
        """Find device by ID"""
        pass
    
    @abstractmethod
    async def update(self, device_id: str, updates: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Update device in database"""
        pass
    
    @abstractmethod
    async def delete(self, device_id: str, org_id: str) -> bool:
        """Delete device from database"""
        pass
    
    @abstractmethod
    async def find_many(self, filters: Dict[str, Any], skip: int, limit: int, org_id: str) -> List[Dict[str, Any]]:
        """Find multiple devices with pagination"""
        pass
    
    @abstractmethod
    async def count(self, filters: Dict[str, Any], org_id: str) -> int:
        """Count devices matching filters"""
        pass
    
    @abstractmethod
    async def get_by_id(self, device_id: str, org_id: str) -> Optional[Any]:
        """Get device by ID (alias for find_by_id)"""
        pass


class IDeviceValidator(ABC):
    """Interface for Device Validation"""
    
    @abstractmethod
    def validate_device_data(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate device registration data"""
        pass
    
    @abstractmethod
    def validate_device_update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate device update data"""
        pass
    
    @abstractmethod
    def validate_device_id(self, device_id: str) -> bool:
        """Validate device ID format"""
        pass
    
    @abstractmethod
    def validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search filters"""
        pass


class IDeviceCommandService(ABC):
    """Interface for Device Command Service"""
    
    @abstractmethod
    async def send_command(self, device_id: str, command: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Send command to device"""
        pass
    
    @abstractmethod
    async def get_command_status(self, device_id: str, command_id: str, org_id: str) -> Dict[str, Any]:
        """Get command execution status"""
        pass
    
    @abstractmethod
    async def list_command_history(self, device_id: str, filters: Dict[str, Any], org_id: str) -> List[Dict[str, Any]]:
        """List command history for device"""
        pass


class IDeviceAuthService(ABC):
    """Interface for Device Authentication Service"""
    
    @abstractmethod
    async def generate_device_certificate(self, device_id: str, org_id: str) -> Dict[str, Any]:
        """Generate device certificate"""
        pass
    
    @abstractmethod
    async def validate_device_certificate(self, certificate_data: str) -> Dict[str, Any]:
        """Validate device certificate"""
        pass
    
    @abstractmethod
    async def revoke_device_certificate(self, device_id: str, org_id: str) -> bool:
        """Revoke device certificate"""
        pass
    
    @abstractmethod
    async def rotate_device_credentials(self, device_id: str, org_id: str) -> Dict[str, Any]:
        """Rotate device credentials"""
        pass


class IDeviceProvisioningService(ABC):
    """Interface for Device Provisioning Service"""
    
    @abstractmethod
    async def provision_device(self, device_data: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Auto-provision a device"""
        pass
    
    @abstractmethod
    async def get_provisioning_template(self, template_id: str, org_id: str) -> Dict[str, Any]:
        """Get provisioning template"""
        pass
    
    @abstractmethod
    async def create_provisioning_template(self, template_data: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Create provisioning template"""
        pass
    
    @abstractmethod
    async def bulk_provision_devices(self, devices: List[Dict[str, Any]], template_id: str, org_id: str) -> List[Dict[str, Any]]:
        """Bulk provision multiple devices"""
        pass


class IDeviceConfigService(ABC):
    """Interface for Device Configuration Service"""
    
    @abstractmethod
    async def get_device_config(self, device_id: str, org_id: str) -> Dict[str, Any]:
        """Get device configuration"""
        pass
    
    @abstractmethod
    async def update_device_config(self, device_id: str, config: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Update device configuration"""
        pass
    
    @abstractmethod
    async def apply_config_template(self, device_id: str, template_id: str, org_id: str) -> Dict[str, Any]:
        """Apply configuration template to device"""
        pass
    
    @abstractmethod
    async def validate_config(self, device_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration for device type"""
        pass


class IDeviceCacheRepository(ABC):
    """Interface for Device Cache Repository"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        pass


class IGroupRepository(ABC):
    """Interface for Group Repository"""
    
    @abstractmethod
    async def create_group(self, group: Any) -> Any:
        """Create a new device group"""
        pass
    
    @abstractmethod
    async def get_group(self, group_id: str, org_id: str) -> Optional[Any]:
        """Get a group by ID"""
        pass
    
    @abstractmethod
    async def update_group(self, group: Any) -> Any:
        """Update a group"""
        pass
    
    @abstractmethod
    async def delete_group(self, group_id: str, org_id: str) -> bool:
        """Delete a group and all its memberships"""
        pass
    
    @abstractmethod
    async def list_groups(self, org_id: str, filters: Optional[Dict[str, Any]] = None, skip: int = 0, limit: int = 100) -> List[Any]:
        """List groups with optional filters"""
        pass
    
    @abstractmethod
    async def add_device_to_group(self, device_id: str, group_id: str, org_id: str, added_by: Optional[str] = None, membership_type: str = "static") -> Any:
        """Add a device to a group"""
        pass
    
    @abstractmethod
    async def remove_device_from_group(self, device_id: str, group_id: str, org_id: str) -> bool:
        """Remove a device from a group"""
        pass
    
    @abstractmethod
    async def get_device_groups(self, device_id: str, org_id: str) -> List[str]:
        """Get all groups a device belongs to"""
        pass
    
    @abstractmethod
    async def get_group_devices(self, group_id: str, org_id: str, include_subgroups: bool = False) -> List[str]:
        """Get all devices in a group"""
        pass
    
    @abstractmethod
    async def get_group_hierarchy(self, org_id: str, root_group_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the hierarchical structure of groups"""
        pass
    
    @abstractmethod
    async def evaluate_dynamic_membership(self, group: Any, device_attributes: Dict[str, Any]) -> bool:
        """Evaluate if a device should be in a dynamic group based on rules"""
        pass


class IGroupService(ABC):
    """Interface for Group Service"""
    
    @abstractmethod
    async def create_group(self, group_data: Dict[str, Any], org_id: str, created_by: Optional[str] = None) -> Any:
        """Create a new device group"""
        pass
    
    @abstractmethod
    async def update_group(self, group_id: str, updates: Dict[str, Any], org_id: str, updated_by: Optional[str] = None) -> Any:
        """Update a device group"""
        pass
    
    @abstractmethod
    async def delete_group(self, group_id: str, org_id: str, deleted_by: Optional[str] = None, cascade: bool = False) -> bool:
        """Delete a device group"""
        pass
    
    @abstractmethod
    async def add_devices_to_group(self, group_id: str, device_ids: List[str], org_id: str, added_by: Optional[str] = None) -> Dict[str, Any]:
        """Add multiple devices to a group"""
        pass
    
    @abstractmethod
    async def remove_devices_from_group(self, group_id: str, device_ids: List[str], org_id: str, removed_by: Optional[str] = None) -> Dict[str, Any]:
        """Remove multiple devices from a group"""
        pass
    
    @abstractmethod
    async def get_group_devices(self, group_id: str, org_id: str, include_subgroups: bool = False, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Get all devices in a group"""
        pass
    
    @abstractmethod
    async def execute_group_operation(self, group_id: str, operation_type: str, payload: Dict[str, Any], org_id: str, executed_by: Optional[str] = None, include_subgroups: bool = False) -> Any:
        """Execute an operation on all devices in a group"""
        pass
    
    @abstractmethod
    async def get_group_hierarchy(self, org_id: str, root_group_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the hierarchical structure of groups"""
        pass
    
    @abstractmethod
    async def create_group_from_template(self, template_name: str, group_name: str, org_id: str, created_by: Optional[str] = None, customizations: Optional[Dict[str, Any]] = None) -> Any:
        """Create a group from a predefined template"""
        pass


# Backward-compatibility aliases for services that use different naming convention
DeviceRepositoryInterface = IDeviceRepository
DeviceServiceInterface = IDeviceService
DeviceCacheRepositoryInterface = IDeviceCacheRepository
GroupRepositoryInterface = IGroupRepository
GroupServiceInterface = IGroupService