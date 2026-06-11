# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Notification Configuration Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Module: certificate_notification_config.py
Purpose: Configuration management for certificate monitoring and notifications
Version: v2025.07-production
Build Date: 2025-07-19
Compliance: ETSI EN 303 645, ISO/IEC 27402
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from ..core.database import get_db

logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"
    DASHBOARD = "dashboard"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    URGENT = "urgent"
    CRITICAL = "critical"

@dataclass
class AlertThresholds:
    """Alert threshold configuration"""
    critical_days: int = 1
    urgent_days: int = 7
    warning_days: int = 30
    info_days: int = 90

@dataclass
class NotificationSettings:
    """Notification channel settings"""
    enabled_channels: List[NotificationChannel]
    email_recipients: List[str]
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    sms_recipients: List[str] = None
    dashboard_alerts: bool = True

@dataclass
class MonitoringSchedule:
    """Monitoring schedule configuration"""
    check_interval_minutes: int = 60
    health_report_time: str = "09:00"  # Daily health report time
    weekly_analytics_day: str = "monday"  # Day for weekly analytics
    weekly_analytics_time: str = "08:00"
    cleanup_interval_hours: int = 6

@dataclass
class AutoRenewalConfig:
    """Auto-renewal configuration"""
    enabled: bool = False
    threshold_days: int = 30
    allowed_algorithms: List[str] = None
    max_validity_days: int = 365
    require_approval: bool = True
    allowed_device_types: List[str] = None

@dataclass
class CertificateMonitoringConfig:
    """Complete certificate monitoring configuration"""
    organization_id: str
    enabled: bool = True
    alert_thresholds: AlertThresholds = None
    notification_settings: NotificationSettings = None
    monitoring_schedule: MonitoringSchedule = None
    auto_renewal: AutoRenewalConfig = None
    custom_settings: Dict[str, Any] = None
    created_at: datetime = None
    updated_at: datetime = None
    created_by: str = None
    updated_by: str = None

    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = AlertThresholds()
        if self.notification_settings is None:
            self.notification_settings = NotificationSettings(
                enabled_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
                email_recipients=[],
                sms_recipients=[]
            )
        if self.monitoring_schedule is None:
            self.monitoring_schedule = MonitoringSchedule()
        if self.auto_renewal is None:
            self.auto_renewal = AutoRenewalConfig(
                allowed_algorithms=["RSA-2048", "RSA-3072", "RSA-4096", "ECC-P256", "ECC-P384"]
            )
        if self.custom_settings is None:
            self.custom_settings = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class CertificateNotificationConfigService:
    """Service for managing certificate monitoring and notification configuration"""
    
    def __init__(self):
        self.db = get_db()
        self.collection = self.db.certificate_monitoring_configs
    
    def get_organization_config(self, organization_id: str) -> Optional[CertificateMonitoringConfig]:
        """
        Get certificate monitoring configuration for an organization
        
        Args:
            organization_id: Organization identifier
            
        Returns:
            CertificateMonitoringConfig or None if not found
        """
        try:
            config_doc = self.collection.find_one({'organization_id': organization_id})
            
            if not config_doc:
                # Return default configuration
                return self._create_default_config(organization_id)
            
            # Convert document to config object
            return self._doc_to_config(config_doc)
            
        except Exception as e:
            logger.error(f"Error getting organization config for {organization_id}: {e}")
            return self._create_default_config(organization_id)
    
    def save_organization_config(self, config: CertificateMonitoringConfig, user: Dict) -> bool:
        """
        Save certificate monitoring configuration for an organization
        
        Args:
            config: Configuration to save
            user: User making the change
            
        Returns:
            bool: True if saved successfully
        """
        try:
            config.updated_at = datetime.now()
            config.updated_by = user.get('email', 'system')
            
            # Convert config to document
            config_doc = self._config_to_doc(config)
            
            # Upsert configuration
            result = self.collection.update_one(
                {'organization_id': config.organization_id},
                {'$set': config_doc},
                upsert=True
            )
            
            logger.info(f"Saved certificate monitoring config for organization {config.organization_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving organization config: {e}")
            return False
    
    def get_global_defaults(self) -> CertificateMonitoringConfig:
        """
        Get global default configuration
        
        Returns:
            CertificateMonitoringConfig with global defaults
        """
        try:
            defaults_doc = self.collection.find_one({'organization_id': 'global_defaults'})
            
            if defaults_doc:
                return self._doc_to_config(defaults_doc)
            else:
                # Create and save default global config
                default_config = self._create_default_config('global_defaults')
                self.save_organization_config(default_config, {'email': 'system'})
                return default_config
                
        except Exception as e:
            logger.error(f"Error getting global defaults: {e}")
            return self._create_default_config('global_defaults')
    
    def update_alert_thresholds(self, organization_id: str, thresholds: AlertThresholds, user: Dict) -> bool:
        """
        Update alert thresholds for an organization
        
        Args:
            organization_id: Organization identifier
            thresholds: New alert thresholds
            user: User making the change
            
        Returns:
            bool: True if updated successfully
        """
        try:
            result = self.collection.update_one(
                {'organization_id': organization_id},
                {
                    '$set': {
                        'alert_thresholds': asdict(thresholds),
                        'updated_at': datetime.now(),
                        'updated_by': user.get('email', 'system')
                    }
                },
                upsert=True
            )
            
            logger.info(f"Updated alert thresholds for organization {organization_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating alert thresholds: {e}")
            return False
    
    def update_notification_settings(self, organization_id: str, settings: NotificationSettings, user: Dict) -> bool:
        """
        Update notification settings for an organization
        
        Args:
            organization_id: Organization identifier
            settings: New notification settings
            user: User making the change
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Convert enum values to strings
            settings_dict = asdict(settings)
            settings_dict['enabled_channels'] = [ch.value for ch in settings.enabled_channels]
            
            result = self.collection.update_one(
                {'organization_id': organization_id},
                {
                    '$set': {
                        'notification_settings': settings_dict,
                        'updated_at': datetime.now(),
                        'updated_by': user.get('email', 'system')
                    }
                },
                upsert=True
            )
            
            logger.info(f"Updated notification settings for organization {organization_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating notification settings: {e}")
            return False
    
    def update_auto_renewal_config(self, organization_id: str, auto_renewal: AutoRenewalConfig, user: Dict) -> bool:
        """
        Update auto-renewal configuration for an organization
        
        Args:
            organization_id: Organization identifier
            auto_renewal: New auto-renewal configuration
            user: User making the change
            
        Returns:
            bool: True if updated successfully
        """
        try:
            result = self.collection.update_one(
                {'organization_id': organization_id},
                {
                    '$set': {
                        'auto_renewal': asdict(auto_renewal),
                        'updated_at': datetime.now(),
                        'updated_by': user.get('email', 'system')
                    }
                },
                upsert=True
            )
            
            logger.info(f"Updated auto-renewal config for organization {organization_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating auto-renewal config: {e}")
            return False
    
    def get_effective_config(self, organization_id: str) -> CertificateMonitoringConfig:
        """
        Get effective configuration by merging organization config with global defaults
        
        Args:
            organization_id: Organization identifier
            
        Returns:
            CertificateMonitoringConfig: Effective configuration
        """
        try:
            # Get organization-specific config
            org_config = self.get_organization_config(organization_id)
            
            # If organization has complete config, return it
            if org_config:
                return org_config
            
            # Otherwise, return global defaults
            return self.get_global_defaults()
            
        except Exception as e:
            logger.error(f"Error getting effective config: {e}")
            return self._create_default_config(organization_id)
    
    def validate_config(self, config: CertificateMonitoringConfig) -> tuple[bool, List[str]]:
        """
        Validate certificate monitoring configuration
        
        Args:
            config: Configuration to validate
            
        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Validate alert thresholds
            if config.alert_thresholds:
                if config.alert_thresholds.critical_days < 0:
                    errors.append("Critical alert threshold must be >= 0")
                if config.alert_thresholds.urgent_days < config.alert_thresholds.critical_days:
                    errors.append("Urgent alert threshold must be >= critical threshold")
                if config.alert_thresholds.warning_days < config.alert_thresholds.urgent_days:
                    errors.append("Warning alert threshold must be >= urgent threshold")
                if config.alert_thresholds.info_days < config.alert_thresholds.warning_days:
                    errors.append("Info alert threshold must be >= warning threshold")
            
            # Validate notification settings
            if config.notification_settings:
                if config.notification_settings.enabled_channels:
                    if NotificationChannel.EMAIL in config.notification_settings.enabled_channels:
                        if not config.notification_settings.email_recipients:
                            errors.append("Email recipients required when email notifications enabled")
                    
                    if NotificationChannel.WEBHOOK in config.notification_settings.enabled_channels:
                        if not config.notification_settings.webhook_url:
                            errors.append("Webhook URL required when webhook notifications enabled")
                        elif not config.notification_settings.webhook_url.startswith(('http://', 'https://')):
                            errors.append("Webhook URL must be a valid HTTP/HTTPS URL")
                    
                    if NotificationChannel.SLACK in config.notification_settings.enabled_channels:
                        if not config.notification_settings.slack_webhook_url:
                            errors.append("Slack webhook URL required when Slack notifications enabled")
            
            # Validate monitoring schedule
            if config.monitoring_schedule:
                if config.monitoring_schedule.check_interval_minutes < 1:
                    errors.append("Check interval must be at least 1 minute")
                if config.monitoring_schedule.check_interval_minutes > 1440:  # 24 hours
                    errors.append("Check interval must not exceed 24 hours")
            
            # Validate auto-renewal config
            if config.auto_renewal:
                if config.auto_renewal.threshold_days < 1:
                    errors.append("Auto-renewal threshold must be at least 1 day")
                if config.auto_renewal.max_validity_days < 30:
                    errors.append("Maximum validity must be at least 30 days")
                if config.auto_renewal.max_validity_days > 3650:  # 10 years
                    errors.append("Maximum validity must not exceed 10 years")
            
            return len(errors) == 0, errors
            
        except Exception as e:
            logger.error(f"Error validating config: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def get_all_organization_configs(self) -> List[CertificateMonitoringConfig]:
        """
        Get all organization configurations
        
        Returns:
            List of CertificateMonitoringConfig objects
        """
        try:
            configs = []
            
            for config_doc in self.collection.find({'organization_id': {'$ne': 'global_defaults'}}):
                try:
                    config = self._doc_to_config(config_doc)
                    configs.append(config)
                except Exception as e:
                    logger.error(f"Error converting config document: {e}")
                    continue
            
            return configs
            
        except Exception as e:
            logger.error(f"Error getting all organization configs: {e}")
            return []
    
    def delete_organization_config(self, organization_id: str, user: Dict) -> bool:
        """
        Delete organization configuration (reverts to global defaults)
        
        Args:
            organization_id: Organization identifier
            user: User making the change
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            if organization_id == 'global_defaults':
                logger.warning("Cannot delete global defaults configuration")
                return False
            
            result = self.collection.delete_one({'organization_id': organization_id})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted certificate monitoring config for organization {organization_id}")
                return True
            else:
                logger.warning(f"No config found for organization {organization_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting organization config: {e}")
            return False
    
    def export_config(self, organization_id: str) -> Optional[Dict]:
        """
        Export configuration as JSON-serializable dictionary
        
        Args:
            organization_id: Organization identifier
            
        Returns:
            Dict or None if not found
        """
        try:
            config = self.get_organization_config(organization_id)
            if config:
                return self._config_to_export_dict(config)
            return None
            
        except Exception as e:
            logger.error(f"Error exporting config: {e}")
            return None
    
    def import_config(self, config_dict: Dict, user: Dict) -> bool:
        """
        Import configuration from dictionary
        
        Args:
            config_dict: Configuration dictionary
            user: User making the change
            
        Returns:
            bool: True if imported successfully
        """
        try:
            config = self._import_dict_to_config(config_dict)
            if config:
                # Validate imported config
                is_valid, errors = self.validate_config(config)
                if not is_valid:
                    logger.error(f"Invalid imported config: {errors}")
                    return False
                
                return self.save_organization_config(config, user)
            return False
            
        except Exception as e:
            logger.error(f"Error importing config: {e}")
            return False
    
    # Private helper methods
    
    def _create_default_config(self, organization_id: str) -> CertificateMonitoringConfig:
        """Create default configuration for an organization"""
        return CertificateMonitoringConfig(
            organization_id=organization_id,
            enabled=True,
            alert_thresholds=AlertThresholds(),
            notification_settings=NotificationSettings(
                enabled_channels=[NotificationChannel.EMAIL, NotificationChannel.DASHBOARD],
                email_recipients=[],
                sms_recipients=[]
            ),
            monitoring_schedule=MonitoringSchedule(),
            auto_renewal=AutoRenewalConfig(),
            custom_settings={}
        )
    
    def _doc_to_config(self, doc: Dict) -> CertificateMonitoringConfig:
        """Convert database document to configuration object"""
        try:
            # Handle alert thresholds
            alert_thresholds = None
            if 'alert_thresholds' in doc:
                alert_thresholds = AlertThresholds(**doc['alert_thresholds'])
            
            # Handle notification settings
            notification_settings = None
            if 'notification_settings' in doc:
                ns_data = doc['notification_settings'].copy()
                # Convert channel strings back to enums
                if 'enabled_channels' in ns_data:
                    ns_data['enabled_channels'] = [
                        NotificationChannel(ch) for ch in ns_data['enabled_channels']
                    ]
                notification_settings = NotificationSettings(**ns_data)
            
            # Handle monitoring schedule
            monitoring_schedule = None
            if 'monitoring_schedule' in doc:
                monitoring_schedule = MonitoringSchedule(**doc['monitoring_schedule'])
            
            # Handle auto-renewal config
            auto_renewal = None
            if 'auto_renewal' in doc:
                auto_renewal = AutoRenewalConfig(**doc['auto_renewal'])
            
            return CertificateMonitoringConfig(
                organization_id=doc['organization_id'],
                enabled=doc.get('enabled', True),
                alert_thresholds=alert_thresholds,
                notification_settings=notification_settings,
                monitoring_schedule=monitoring_schedule,
                auto_renewal=auto_renewal,
                custom_settings=doc.get('custom_settings', {}),
                created_at=doc.get('created_at'),
                updated_at=doc.get('updated_at'),
                created_by=doc.get('created_by'),
                updated_by=doc.get('updated_by')
            )
            
        except Exception as e:
            logger.error(f"Error converting document to config: {e}")
            raise
    
    def _config_to_doc(self, config: CertificateMonitoringConfig) -> Dict:
        """Convert configuration object to database document"""
        doc = {
            'organization_id': config.organization_id,
            'enabled': config.enabled,
            'custom_settings': config.custom_settings,
            'created_at': config.created_at,
            'updated_at': config.updated_at,
            'created_by': config.created_by,
            'updated_by': config.updated_by
        }
        
        if config.alert_thresholds:
            doc['alert_thresholds'] = asdict(config.alert_thresholds)
        
        if config.notification_settings:
            ns_dict = asdict(config.notification_settings)
            # Convert enums to strings
            ns_dict['enabled_channels'] = [ch.value for ch in config.notification_settings.enabled_channels]
            doc['notification_settings'] = ns_dict
        
        if config.monitoring_schedule:
            doc['monitoring_schedule'] = asdict(config.monitoring_schedule)
        
        if config.auto_renewal:
            doc['auto_renewal'] = asdict(config.auto_renewal)
        
        return doc
    
    def _config_to_export_dict(self, config: CertificateMonitoringConfig) -> Dict:
        """Convert configuration to export-friendly dictionary"""
        export_dict = {
            'organization_id': config.organization_id,
            'enabled': config.enabled,
            'alert_thresholds': asdict(config.alert_thresholds) if config.alert_thresholds else None,
            'monitoring_schedule': asdict(config.monitoring_schedule) if config.monitoring_schedule else None,
            'auto_renewal': asdict(config.auto_renewal) if config.auto_renewal else None,
            'custom_settings': config.custom_settings,
            'exported_at': datetime.now().isoformat(),
            'exported_by': config.updated_by
        }
        
        # Handle notification settings carefully (exclude sensitive data)
        if config.notification_settings:
            ns_dict = asdict(config.notification_settings)
            # Convert enums to strings
            ns_dict['enabled_channels'] = [ch.value for ch in config.notification_settings.enabled_channels]
            # Remove sensitive information
            ns_dict.pop('webhook_secret', None)
            export_dict['notification_settings'] = ns_dict
        
        return export_dict
    
    def _import_dict_to_config(self, config_dict: Dict) -> Optional[CertificateMonitoringConfig]:
        """Convert import dictionary to configuration object"""
        try:
            # Reconstruct notification settings
            notification_settings = None
            if 'notification_settings' in config_dict and config_dict['notification_settings']:
                ns_data = config_dict['notification_settings'].copy()
                if 'enabled_channels' in ns_data:
                    ns_data['enabled_channels'] = [
                        NotificationChannel(ch) for ch in ns_data['enabled_channels']
                    ]
                notification_settings = NotificationSettings(**ns_data)
            
            # Reconstruct other components
            alert_thresholds = None
            if 'alert_thresholds' in config_dict and config_dict['alert_thresholds']:
                alert_thresholds = AlertThresholds(**config_dict['alert_thresholds'])
            
            monitoring_schedule = None
            if 'monitoring_schedule' in config_dict and config_dict['monitoring_schedule']:
                monitoring_schedule = MonitoringSchedule(**config_dict['monitoring_schedule'])
            
            auto_renewal = None
            if 'auto_renewal' in config_dict and config_dict['auto_renewal']:
                auto_renewal = AutoRenewalConfig(**config_dict['auto_renewal'])
            
            return CertificateMonitoringConfig(
                organization_id=config_dict['organization_id'],
                enabled=config_dict.get('enabled', True),
                alert_thresholds=alert_thresholds,
                notification_settings=notification_settings,
                monitoring_schedule=monitoring_schedule,
                auto_renewal=auto_renewal,
                custom_settings=config_dict.get('custom_settings', {})
            )
            
        except Exception as e:
            logger.error(f"Error converting import dict to config: {e}")
            return None

# Global service instance
certificate_notification_config_service = CertificateNotificationConfigService()