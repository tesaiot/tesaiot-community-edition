# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Service Configuration Management Service

This service handles the management of service features and configurations
for different organizations in the TESA IoT Platform.

SPDX-License-Identifier: Apache-2.0
Copyright 2026 TESAIoT Platform contributors.
"""

from typing import Dict, List, Any
from datetime import datetime
from bson import ObjectId

from ..core.database import get_db
import logging

logger = logging.getLogger(__name__)


class ServiceConfigurationService:
    """Service for managing organization-specific service configurations"""
    
    def __init__(self):
        pass  # Initialize connection only when needed
    
    def _ensure_indexes(self, db):
        """Ensure necessary indexes exist for performance"""
        try:
            # Unique index on organization_id
            db.service_configurations.create_index("organization_id", unique=True)
            # Index for audit queries
            db.service_configuration_audit.create_index([
                ("organization_id", 1),
                ("created_at", -1)
            ])
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
    
    def get_default_features(self) -> Dict[str, bool]:
        """Get default feature configuration for new organizations"""
        return {
            # Core Features
            "device_management": True,
            "user_management": True,
            "certificates": True,
            "organizations": True,
            
            # Dashboard Cards
            "system_health_card": True,
            "device_stats_card": True,
            "alert_summary_card": True,
            "recent_activity_card": True,
            
            # Menu Items
            "menu_dashboard": True,
            "menu_devices": True,
            "menu_users": True,
            "menu_certificates": True,
            "menu_system_health": True,
            "menu_activity_logs": True,
            "menu_analytics": True,
            "menu_compliance": True,
            "menu_organizations": True,
            "menu_api_keys": True,
            "menu_security": True,
            "menu_settings": True,
            
            # Feature Buttons
            "bulk_operations": True,
            "export_data": True,
            "quick_actions": True,
            "notifications": True,
            "device_data_dashboard": True,
            "ai_assistant": True,
            
            # Analytics
            "basic_analytics": True,
            "advanced_analytics": True,
            "ai_analytics": True,
            "predictive_maintenance": True,
            
            # Security
            "two_factor_auth": True,
            "sso_integration": True,
            "audit_logs": True,
            "compliance_reports": True
        }
    
    def get_configuration(self, organization_id: str, user_email: str = None) -> Dict[str, Any]:
        """
        Get service configuration for an organization
        
        Args:
            organization_id: Organization ID
            user_email: Email of requesting user (for audit)
            
        Returns:
            Service configuration dict
        """
        try:
            db = get_db()
            if db is None:
                raise ValueError("Database connection not available")
            
            # Handle special platform organization
            if organization_id == "tesa-platform":
                # Return platform-level configuration with all features enabled
                return {
                    "organization_id": organization_id,
                    "features": self.get_default_features(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_by": "platform",
                    "updated_by": "platform",
                    "tier": "platform",
                    "type": "platform"
                }
            
            # Check if organization exists
            # Try as ObjectId first, then as string
            org = None
            try:
                org = db.organizations.find_one({"_id": ObjectId(organization_id)})
            except:
                org = db.organizations.find_one({"_id": organization_id})
            
            # If organization doesn't exist, still provide default configuration
            # This prevents 404 errors in the frontend
            if not org:
                logger.info(f"Organization {organization_id} not found in database, providing default configuration")
                default_config = {
                    "organization_id": organization_id,
                    "features": self.get_default_features(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_by": user_email or "system",
                    "updated_by": user_email or "system",
                    "tier": "STARTUP",  # Default tier
                    "is_default": True,  # Flag to indicate this is a default config
                    "note": "Default configuration - organization not found in database"
                }
                return default_config
            
            # Try to get existing configuration
            config = db.service_configurations.find_one({"organization_id": organization_id})
            
            if config:
                # Remove MongoDB internal fields
                config.pop("_id", None)
                return config
            else:
                # Return default configuration for new organization
                default_config = {
                    "organization_id": organization_id,
                    "features": self.get_default_features(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "created_by": user_email or "system",
                    "updated_by": user_email or "system"
                }
                return default_config
                
        except Exception as e:
            logger.error(f"Error getting configuration for org {organization_id}: {e}")
            raise
    
    def save_configuration(self, organization_id: str, features: Dict[str, bool], 
                          user_email: str) -> Dict[str, Any]:
        """
        Save service configuration for an organization
        
        Args:
            organization_id: Organization ID
            features: Feature configuration dict
            user_email: Email of user making the change
            
        Returns:
            Updated configuration
        """
        try:
            db = get_db()
            if db is None:
                raise ValueError("Database connection not available")
            
            # Ensure indexes on first save
            self._ensure_indexes(db)
            
            # Handle special platform organization - allow configuration but don't validate in DB
            if organization_id != "tesa-platform":
                # Validate organization exists for non-platform organizations
                # Try as ObjectId first, then as string
                try:
                    org = db.organizations.find_one({"_id": ObjectId(organization_id)})
                except:
                    org = db.organizations.find_one({"_id": organization_id})
                
                if not org:
                    raise ValueError(f"Organization {organization_id} not found")
            
            # Get existing configuration for comparison
            existing = db.service_configurations.find_one({"organization_id": organization_id})
            
            # Prepare configuration document
            config_doc = {
                "organization_id": organization_id,
                "features": features,
                "updated_at": datetime.utcnow().isoformat(),
                "updated_by": user_email
            }
            
            if existing:
                # Update existing configuration
                result = db.service_configurations.update_one(
                    {"organization_id": organization_id},
                    {"$set": config_doc}
                )
                
                # Create audit entry for changes
                if existing.get("features") != features:
                    self._create_audit_entry(
                        organization_id=organization_id,
                        action="update",
                        old_features=existing.get("features", {}),
                        new_features=features,
                        user_email=user_email
                    )
            else:
                # Create new configuration
                config_doc["created_at"] = datetime.utcnow().isoformat()
                config_doc["created_by"] = user_email
                
                result = db.service_configurations.insert_one(config_doc)
                
                # Create audit entry for creation
                self._create_audit_entry(
                    organization_id=organization_id,
                    action="create",
                    old_features={},
                    new_features=features,
                    user_email=user_email
                )
            
            logger.info(f"Configuration saved for org {organization_id} by {user_email}")
            
            # Return the saved configuration
            return self.get_configuration(organization_id, user_email)
            
        except Exception as e:
            logger.error(f"Error saving configuration for org {organization_id}: {e}")
            raise
    
    def _create_audit_entry(self, organization_id: str, action: str,
                           old_features: Dict, new_features: Dict,
                           user_email: str):
        """Create an audit log entry for configuration changes"""
        try:
            # Calculate what changed
            changes = []
            all_keys = set(old_features.keys()) | set(new_features.keys())
            
            for key in all_keys:
                old_val = old_features.get(key)
                new_val = new_features.get(key)
                if old_val != new_val:
                    changes.append({
                        "feature": key,
                        "old_value": old_val,
                        "new_value": new_val
                    })
            
            db = get_db()
            if db is not None:
                audit_entry = {
                    "organization_id": organization_id,
                    "action": action,
                    "changes": changes,
                    "user_email": user_email,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                db.service_configuration_audit.insert_one(audit_entry)
            
        except Exception as e:
            logger.warning(f"Failed to create audit entry: {e}")
    
    def get_audit_log(self, organization_id: str, limit: int = 50) -> List[Dict]:
        """
        Get audit log for an organization's configuration changes
        
        Args:
            organization_id: Organization ID
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        try:
            db = get_db()
            if db is None:
                return []
            
            cursor = db.service_configuration_audit.find(
                {"organization_id": organization_id}
            ).sort("created_at", -1).limit(limit)
            
            audit_log = []
            for entry in cursor:
                entry.pop("_id", None)
                audit_log.append(entry)
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Error getting audit log for org {organization_id}: {e}")
            return []
    
    def bulk_update_configurations(self, updates: List[Dict], user_email: str) -> Dict:
        """
        Bulk update configurations for multiple organizations
        
        Args:
            updates: List of {organization_id, features} dicts
            user_email: Email of user making the changes
            
        Returns:
            Summary of updates
        """
        success_count = 0
        failed_count = 0
        errors = []
        
        for update in updates:
            try:
                org_id = update.get("organization_id")
                features = update.get("features")
                
                if not org_id or features is None:
                    failed_count += 1
                    errors.append(f"Invalid update data: {update}")
                    continue
                
                self.save_configuration(org_id, features, user_email)
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to update {org_id}: {str(e)}")
        
        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }