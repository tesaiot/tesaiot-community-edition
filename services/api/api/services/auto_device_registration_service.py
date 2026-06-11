# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Automatic Device Registration Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any, Tuple

from ..core.database import get_db
from ..core.rbac import RBAC
from .audit_service import audit_log, AuditAction
from .device_service import create_device
from .notification_service import send_email_notification

logger = logging.getLogger(__name__)

class AutoDeviceRegistrationService:
    """
    Service for automatic device registration during certificate issuance.
    
    This service provides:
    1. Automatic device creation when certificates are requested
    2. Pre-registration validation
    3. Registration failure handling
    4. Integration with existing certificate workflow
    """
    
    def __init__(self):
        self._db = None
    
    def _get_db(self):
        """Lazy database connection"""
        if self._db is None:
            self._db = get_db()
        return self._db
    
    def is_auto_registration_enabled(self, organization_id: str) -> bool:
        """
        Check if auto-registration is enabled for an organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            bool: True if auto-registration is enabled
        """
        try:
            org = self._get_db().organizations.find_one({
                '$or': [
                    {'_id': ObjectId(organization_id) if ObjectId.is_valid(organization_id) else None},
                    {'organization_id': organization_id}
                ]
            })
            
            if not org:
                # Default to enabled if organization not found (for backward compatibility)
                return True
            
            # Check organization setting, default to True for backward compatibility
            return org.get('auto_registration_enabled', True)
            
        except Exception as e:
            logger.error(f"Error checking auto-registration setting: {e}")
            # Default to enabled on error for backward compatibility
            return True
    
    def validate_device_registration_request(self, device_id: str, organization_id: str, 
                                           user: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate if a device can be automatically registered.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            user: User requesting certificate
            
        Returns:
            Tuple of (is_valid, message, existing_device)
        """
        try:
            # Check if device already exists
            existing_device = self._get_db().devices.find_one({
                '$or': [
                    {'device_id': device_id},
                    {'_id': ObjectId(device_id) if ObjectId.is_valid(device_id) else None}
                ]
            })
            
            if existing_device:
                # Device exists - check if it belongs to the same organization
                if existing_device.get('organization_id') == organization_id:
                    logger.info(f"Device {device_id} already registered in organization {organization_id}")
                    return True, "Device already registered", existing_device
                else:
                    logger.warning(f"Device {device_id} exists in different organization")
                    return False, "Device ID already exists in different organization", None
            
            # Check organization access
            if not RBAC.can_access_organization(user, organization_id):
                logger.warning(f"User {user.get('email')} cannot register device in organization {organization_id}")
                return False, "Access denied to organization", None
            
            # Check organization limits
            device_count = self._get_db().devices.count_documents({'organization_id': organization_id})
            org = self._get_db().organizations.find_one({
                '$or': [
                    {'_id': ObjectId(organization_id) if ObjectId.is_valid(organization_id) else None},
                    {'organization_id': organization_id}
                ]
            })
            
            if org:
                device_limit = org.get('device_limit', 1000)  # Default limit
                if device_count >= device_limit:
                    logger.warning(f"Organization {organization_id} device limit exceeded: {device_count}/{device_limit}")
                    return False, f"Device limit exceeded ({device_count}/{device_limit})", None
            
            logger.info(f"Device {device_id} validation passed for organization {organization_id}")
            return True, "Validation passed", None
            
        except Exception as e:
            logger.error(f"Error validating device registration: {e}")
            return False, f"Validation error: {str(e)}", None
    
    def auto_register_device(self, device_id: str, device_type: str, organization_id: str, 
                           user: Dict[str, Any], certificate_algorithm: str = None,
                           metadata: Dict[str, Any] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Automatically register a device during certificate issuance.
        
        Args:
            device_id: Device identifier
            device_type: Type of device (sensor, gateway, etc.)
            organization_id: Organization ID
            user: User requesting certificate
            certificate_algorithm: Certificate algorithm preference
            metadata: Additional device metadata
            
        Returns:
            Tuple of (success, message, device_data)
        """
        try:
            # Check if auto-registration is enabled for this organization
            if not self.is_auto_registration_enabled(organization_id):
                return False, "Auto-registration is disabled for this organization", None
            
            # Validate registration request
            is_valid, validation_msg, existing_device = self.validate_device_registration_request(
                device_id, organization_id, user
            )
            
            if not is_valid:
                return False, validation_msg, None
            
            # If device already exists, return it
            if existing_device:
                return True, "Device already registered", existing_device
            
            # Auto-detect device type based on device_id pattern if not provided
            if not device_type or device_type == 'unknown':
                device_type = self._detect_device_type(device_id)
            
            # Prepare device data for automatic registration
            device_data = {
                'device_id': device_id,
                'name': self._generate_device_name(device_id, device_type),
                'type': device_type,
                'location': {},
                'metadata': metadata or {},
                'certificate_algorithm': certificate_algorithm,
                'auth_type': 'certificate',  # Default for auto-registered devices
                'auto_registered': True,
                'auto_registration_timestamp': datetime.now().isoformat(),
                'auto_registration_user': user.get('email')
            }
            
            # Add certificate algorithm to metadata as well
            if certificate_algorithm:
                device_data['metadata']['certificate_algorithm'] = certificate_algorithm
            
            # Create device using existing service
            created_device = create_device(device_data, user)
            
            # Ensure we return the full device document from database
            if created_device and '_id' in created_device:
                # Reload device from database to get complete document
                if isinstance(created_device['_id'], str) and ObjectId.is_valid(created_device['_id']):
                    created_device = self._get_db().devices.find_one({'_id': ObjectId(created_device['_id'])})
                elif isinstance(created_device['_id'], ObjectId):
                    created_device = self._get_db().devices.find_one({'_id': created_device['_id']})
                else:
                    # Try by device_id as fallback
                    created_device = self._get_db().devices.find_one({'device_id': device_id})
            
            logger.info(f"Auto-registered device {device_id} for organization {organization_id}")
            
            # Log auto-registration event
            self._get_db().device_auto_registration_log.insert_one({
                'device_id': device_id,
                'device_type': device_type,
                'organization_id': organization_id,
                'user_email': user.get('email'),
                'timestamp': datetime.now(),
                'certificate_algorithm': certificate_algorithm,
                'success': True,
                'message': 'Device auto-registered successfully'
            })
            
            # Audit log
            audit_log(
                action=AuditAction.DEVICE_AUTO_REGISTER,
                user=user,
                resource_type='device',
                resource_id=device_id,
                details={
                    'device_type': device_type,
                    'auto_registered': True,
                    'certificate_algorithm': certificate_algorithm
                }
            )
            
            # Send notification if enabled
            self._send_auto_registration_notification(created_device, user, organization_id)
            
            return True, "Device auto-registered successfully", created_device
            
        except Exception as e:
            logger.error(f"Error auto-registering device {device_id}: {e}")
            
            # Log failed registration
            self._get_db().device_auto_registration_log.insert_one({
                'device_id': device_id,
                'device_type': device_type,
                'organization_id': organization_id,
                'user_email': user.get('email'),
                'timestamp': datetime.now(),
                'certificate_algorithm': certificate_algorithm,
                'success': False,
                'error': str(e),
                'message': 'Device auto-registration failed'
            })
            
            return False, f"Auto-registration failed: {str(e)}", None
    
    def _detect_device_type(self, device_id: str) -> str:
        """
        Auto-detect device type based on device ID pattern.
        
        Args:
            device_id: Device identifier
            
        Returns:
            str: Detected device type
        """
        device_id_lower = device_id.lower()
        
        # Pattern-based detection
        if 'gateway' in device_id_lower or 'gw' in device_id_lower:
            return 'gateway'
        elif 'sensor' in device_id_lower or 'sens' in device_id_lower:
            return 'sensor'
        elif 'psoc' in device_id_lower:
            return 'edge_device'
        elif 'rpi' in device_id_lower or 'raspberry' in device_id_lower:
            return 'gateway'
        elif 'env' in device_id_lower or 'environment' in device_id_lower:
            return 'environmental_sensor'
        elif 'nav' in device_id_lower or 'navigation' in device_id_lower:
            return 'navigation_device'
        elif 'health' in device_id_lower or 'medical' in device_id_lower:
            return 'medical_device'
        elif 'actuator' in device_id_lower or 'act' in device_id_lower:
            return 'actuator'
        else:
            return 'sensor'  # Default fallback
    
    def _generate_device_name(self, device_id: str, device_type: str) -> str:
        """
        Generate a friendly device name for auto-registered devices.
        
        Args:
            device_id: Device identifier
            device_type: Device type
            
        Returns:
            str: Generated device name
        """
        # Clean up device_id for display
        clean_id = device_id.replace('-', ' ').replace('_', ' ').title()
        
        # Add type-specific prefix
        type_prefixes = {
            'gateway': 'Gateway',
            'sensor': 'Sensor',
            'edge_device': 'Edge Device',
            'environmental_sensor': 'Environmental Sensor',
            'navigation_device': 'Navigation Device',
            'medical_device': 'Medical Device',
            'actuator': 'Actuator'
        }
        
        prefix = type_prefixes.get(device_type, 'Device')
        
        # If device_id is already descriptive, use it as-is
        if len(clean_id) > 10 and any(word in clean_id.lower() for word in ['sensor', 'gateway', 'device', 'psoc', 'rpi']):
            return clean_id
        else:
            return f"{prefix} {clean_id}"
    
    def _send_auto_registration_notification(self, device: Dict[str, Any], user: Dict[str, Any], 
                                           organization_id: str) -> None:
        """
        Send notification about auto-registration if enabled.
        
        Args:
            device: Created device data
            user: User who triggered registration
            organization_id: Organization ID
        """
        try:
            # Check if notifications are enabled for the organization
            org = self._get_db().organizations.find_one({
                '$or': [
                    {'_id': ObjectId(organization_id) if ObjectId.is_valid(organization_id) else None},
                    {'organization_id': organization_id}
                ]
            })
            
            if not org:
                return
            
            notifications_enabled = org.get('auto_registration_notifications', True)
            if not notifications_enabled:
                return
            
            # Get organization admins
            admin_emails = []
            org_admins = self._get_db().users.find({
                'organization_id': organization_id,
                'role': {'$in': ['organization_admin', 'admin']}
            })
            
            for admin in org_admins:
                if admin.get('email'):
                    admin_emails.append(admin['email'])
            
            # Add the requesting user's email
            if user.get('email') and user['email'] not in admin_emails:
                admin_emails.append(user['email'])
            
            if not admin_emails:
                return
            
            # Send notification
            subject = f"[TESA IoT] Device Auto-Registered: {device.get('name')}"
            body = f"""
A new device has been automatically registered in your TESA IoT Platform organization.

Device Details:
- Device ID: {device.get('device_id')}
- Device Name: {device.get('name')}
- Device Type: {device.get('type')}
- Organization: {org.get('name', organization_id)}
- Registered By: {user.get('email')}
- Registration Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

This device was automatically registered when a certificate was requested. The device is now ready for certificate issuance and can begin connecting to the platform.

To manage this device, visit your Device Management dashboard.

Best regards,
TESA IoT Platform Team
"""
            
            for email in admin_emails:
                try:
                    send_email_notification(email, subject, body)
                except Exception as e:
                    logger.warning(f"Failed to send auto-registration notification to {email}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending auto-registration notification: {e}")
    
    def get_auto_registration_history(self, organization_id: str, limit: int = 100) -> list:
        """
        Get auto-registration history for an organization.
        
        Args:
            organization_id: Organization ID
            limit: Maximum number of records
            
        Returns:
            list: Auto-registration history
        """
        try:
            history = list(self._get_db().device_auto_registration_log.find(
                {'organization_id': organization_id}
            ).sort('timestamp', -1).limit(limit))
            
            # Convert ObjectId to string
            for record in history:
                record['_id'] = str(record['_id'])
                if isinstance(record.get('timestamp'), datetime):
                    record['timestamp'] = record['timestamp'].isoformat()
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting auto-registration history: {e}")
            return []
    
    def update_organization_auto_registration_settings(self, organization_id: str, 
                                                     settings: Dict[str, Any], 
                                                     user: Dict[str, Any]) -> bool:
        """
        Update auto-registration settings for an organization.
        
        Args:
            organization_id: Organization ID
            settings: Settings to update
            user: User making the change
            
        Returns:
            bool: Success status
        """
        try:
            # Validate settings
            valid_settings = {
                'auto_registration_enabled': bool,
                'auto_registration_notifications': bool,
                'auto_registration_require_approval': bool,
                'auto_registration_default_type': str
            }
            
            update_data = {}
            for key, expected_type in valid_settings.items():
                if key in settings:
                    if isinstance(settings[key], expected_type):
                        update_data[key] = settings[key]
                    else:
                        logger.warning(f"Invalid type for {key}: expected {expected_type.__name__}")
            
            if not update_data:
                return False
            
            # Add audit fields
            update_data['auto_registration_settings_updated_at'] = datetime.now()
            update_data['auto_registration_settings_updated_by'] = user.get('email')
            
            # Update organization
            result = self._get_db().organizations.update_one(
                {
                    '$or': [
                        {'_id': ObjectId(organization_id) if ObjectId.is_valid(organization_id) else None},
                        {'organization_id': organization_id}
                    ]
                },
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated auto-registration settings for organization {organization_id}")
                return True
            else:
                logger.warning(f"No organization found with ID {organization_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating auto-registration settings: {e}")
            return False

# Create service instance
auto_device_registration_service = AutoDeviceRegistrationService()