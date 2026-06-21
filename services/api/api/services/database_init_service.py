# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Database Initialization Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import os
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)


def _require_vault_token() -> str:
    """Resolve the Vault token from VAULT_TOKEN_FILE or VAULT_TOKEN.

    SECURITY: no default. The historical fallback to the literal 'root' token
    silently granted root Vault access in misconfigured deployments. Fail
    closed with a clear error instead (callers catch and log the failure).
    """
    token_file = (os.environ.get('VAULT_TOKEN_FILE') or '').strip()
    if token_file:
        try:
            with open(token_file, 'r') as f:
                token = f.read().strip()
            if token:
                return token
        except OSError as e:
            raise RuntimeError(f"VAULT_TOKEN_FILE is set but unreadable: {e}")
    token = (os.environ.get('VAULT_TOKEN') or '').strip()
    if not token:
        raise RuntimeError(
            "No Vault token configured. Set VAULT_TOKEN_FILE or VAULT_TOKEN; "
            "refusing to fall back to a default token."
        )
    return token


class DatabaseInitService:
    """
    Service responsible for initializing database with required data,
    running migrations, and ensuring data integrity on startup.
    """
    
    def __init__(self, db):
        self.db = db
        self.migrations_run = []
        
    def initialize(self):
        """Run all initialization tasks."""
        logger.info("Starting database initialization...")
        
        try:
            # 1. Ensure indexes exist. Index tuning must never block the rest of
            #    initialization (esp. admin seeding): a pre-existing index with a
            #    differing spec (e.g. organizations.organization_id created
            #    unique by init-mongo.js vs sparse here) raises IndexKeySpecsConflict.
            #    Treat index errors as non-fatal so default-data seeding still runs.
            try:
                self._ensure_indexes()
            except Exception as idx_err:  # noqa: BLE001
                logger.warning(f"Index creation reported a non-fatal error: {idx_err}")

            # 2. Run data migrations
            self._run_migrations()
            
            # 3. Ensure default data exists
            self._ensure_default_data()
            
            # 4. Verify data integrity
            self._verify_data_integrity()
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def _ensure_indexes(self):
        """Create required database indexes for performance and uniqueness."""
        logger.info("Ensuring database indexes...")
        
        # Users collection indexes
        self.db.users.create_index("email", unique=True)
        self.db.users.create_index("organization_id")
        self.db.users.create_index([("email", 1), ("organization_id", 1)])
        
        # Devices collection indexes
        self.db.devices.create_index("device_id", unique=True)
        self.db.devices.create_index("organization_id")
        self.db.devices.create_index([("organization_id", 1), ("status", 1)])
        self.db.devices.create_index("last_seen")
        
        # Telemetry collection indexes (with organization_id for GDPR compliance)
        self.db.telemetry.create_index([("device_id", 1), ("timestamp", -1)])
        self.db.telemetry.create_index([("organization_id", 1), ("timestamp", -1)])
        self.db.telemetry.create_index("timestamp", expireAfterSeconds=2592000)  # 30 days TTL
        
        # Audit logs collection indexes
        self.db.audit_logs.create_index([("user_id", 1), ("timestamp", -1)])
        self.db.audit_logs.create_index([("organization_id", 1), ("timestamp", -1)])
        self.db.audit_logs.create_index("action")
        self.db.audit_logs.create_index("timestamp", expireAfterSeconds=7776000)  # 90 days TTL
        
        # Organizations collection indexes
        self.db.organizations.create_index("name", unique=True)
        self.db.organizations.create_index("organization_id", sparse=True)
        
        # API keys collection indexes
        self.db.api_keys.create_index("key_hash", unique=True)
        self.db.api_keys.create_index("organization_id")
        self.db.api_keys.create_index([("organization_id", 1), ("status", 1)])
        
        # CSR tracking collection indexes
        self._ensure_csr_indexes()
        
        logger.info("Database indexes created/verified")
    
    def _ensure_csr_indexes(self):
        """Create CSR tracking collection indexes."""
        logger.info("Creating CSR tracking collection indexes...")
        
        # Import the CSR tracking collection creation function
        try:
            from pymongo import ASCENDING, DESCENDING
            
            # 1. CSR Submissions Collection
            if 'csr_submissions' not in self.db.list_collection_names():
                self.db.create_collection('csr_submissions')
            
            self.db.csr_submissions.create_index([('csr_id', ASCENDING)], unique=True)
            self.db.csr_submissions.create_index([('device_id', ASCENDING), ('status', ASCENDING)])
            self.db.csr_submissions.create_index([('organization_id', ASCENDING), ('submitted_at', DESCENDING)])
            self.db.csr_submissions.create_index([('status', ASCENDING), ('submitted_at', DESCENDING)])
            self.db.csr_submissions.create_index([('csr_content.sha256_hash', ASCENDING)], unique=True)
            
            # 2. CSR Processing Log Collection
            if 'csr_processing_log' not in self.db.list_collection_names():
                self.db.create_collection('csr_processing_log')
            
            self.db.csr_processing_log.create_index([('log_id', ASCENDING)], unique=True)
            self.db.csr_processing_log.create_index([('csr_id', ASCENDING), ('timestamp', DESCENDING)])
            self.db.csr_processing_log.create_index([('organization_id', ASCENDING), ('timestamp', DESCENDING)])
            
            # 3. CSR Certificates Collection
            if 'csr_certificates' not in self.db.list_collection_names():
                self.db.create_collection('csr_certificates')
            
            self.db.csr_certificates.create_index([('mapping_id', ASCENDING)], unique=True)
            self.db.csr_certificates.create_index([('csr_id', ASCENDING)], unique=True)
            self.db.csr_certificates.create_index([('certificate_serial', ASCENDING)], unique=True)
            self.db.csr_certificates.create_index([('device_id', ASCENDING), ('issued_at', DESCENDING)])
            
            # 4. CSR Validation History Collection
            if 'csr_validation_history' not in self.db.list_collection_names():
                self.db.create_collection('csr_validation_history')
            
            self.db.csr_validation_history.create_index([('validation_id', ASCENDING)], unique=True)
            self.db.csr_validation_history.create_index([('csr_id', ASCENDING), ('validated_at', DESCENDING)])
            self.db.csr_validation_history.create_index([('organization_id', ASCENDING), ('is_valid', ASCENDING)])
            
            # 5. CSR Analytics Collection
            if 'csr_analytics' not in self.db.list_collection_names():
                self.db.create_collection('csr_analytics')
            
            self.db.csr_analytics.create_index([('organization_id', ASCENDING), ('date', ASCENDING), ('metric_type', ASCENDING)], unique=True)
            self.db.csr_analytics.create_index([('date', DESCENDING), ('metric_type', ASCENDING)])
            
            # TTL indexes for automatic cleanup
            self.db.csr_processing_log.create_index([('timestamp', ASCENDING)], expireAfterSeconds=365*24*60*60)  # 1 year
            self.db.csr_validation_history.create_index([('validated_at', ASCENDING)], expireAfterSeconds=180*24*60*60)  # 6 months
            
            logger.info("CSR tracking collection indexes created/verified")
            
        except Exception as e:
            logger.error(f"Error creating CSR tracking indexes: {e}")
    
    def _run_migrations(self):
        """Run data migrations to ensure data consistency."""
        logger.info("Running data migrations...")
        
        # Check migration history
        migration_history = self.db.migration_history.find_one({"_id": "migrations"})
        if not migration_history:
            migration_history = {"_id": "migrations", "completed": []}
        
        completed = set(migration_history.get("completed", []))
        
        # Migration 1: Add organization_id to telemetry records
        if "add_org_id_to_telemetry" not in completed:
            self._migrate_telemetry_organization_id()
            completed.add("add_org_id_to_telemetry")
            
        # Migration 2: Update admin role to super_admin
        if "update_admin_to_super_admin" not in completed:
            self._migrate_admin_role()
            completed.add("update_admin_to_super_admin")
            
        # Migration 3: Ensure all devices have proper organization_id
        if "fix_device_org_ids" not in completed:
            self._fix_device_organization_ids()
            completed.add("fix_device_org_ids")
            
        # Migration 4: Create CSR tracking collections
        if "create_csr_tracking_collections" not in completed:
            self._migrate_csr_tracking_collections()
            completed.add("create_csr_tracking_collections")
        
        # Migration 5: Create device public key tracking collections
        if "create_device_public_key_tracking" not in completed:
            self._migrate_device_public_key_tracking()
            completed.add("create_device_public_key_tracking")
        
        # Migration 6: Add missing menu items to service configurations
        if "add_missing_menu_items_to_service_config" not in completed:
            self._migrate_add_missing_menu_items()
            completed.add("add_missing_menu_items_to_service_config")
        
        # Migration 7: Initialize CA chain from Vault PKI
        if "initialize_ca_chain_v2" not in completed:
            if self._initialize_ca_chain():
                completed.add("initialize_ca_chain_v2")
            else:
                logger.warning("CA chain initialization deferred - will retry on next startup")
        
        # Migration 8: Initialize PKI roles for certificate generation
        if "initialize_pki_roles_v1" not in completed:
            if self._initialize_pki_roles():
                completed.add("initialize_pki_roles_v1")
                logger.info("PKI roles initialized successfully")
            else:
                logger.warning("PKI roles initialization deferred - will retry on next startup")
        
        # Update migration history
        self.db.migration_history.update_one(
            {"_id": "migrations"},
            {"$set": {"completed": list(completed), "last_run": datetime.now()}},
            upsert=True
        )
        
        logger.info(f"Completed {len(completed)} migrations")
    
    def _migrate_telemetry_organization_id(self):
        """Add organization_id to telemetry records for GDPR compliance."""
        logger.info("Migrating telemetry records to include organization_id...")
        
        # Find telemetry records without organization_id
        cursor = self.db.telemetry.find(
            {"organization_id": {"$exists": False}},
            {"device_id": 1}
        ).limit(1000)  # Process in batches
        
        updates = []
        devices_cache = {}
        
        for record in cursor:
            device_id = record.get('device_id')
            if not device_id:
                continue
                
            # Get device organization from cache or database
            if device_id not in devices_cache:
                device = self.db.devices.find_one(
                    {"device_id": device_id},
                    {"organization_id": 1}
                )
                if device:
                    devices_cache[device_id] = device.get('organization_id', '')
                else:
                    devices_cache[device_id] = ''
            
            org_id = devices_cache[device_id]
            if org_id:
                updates.append({
                    "updateOne": {
                        "filter": {"_id": record["_id"]},
                        "update": {"$set": {"organization_id": org_id}}
                    }
                })
        
        if updates:
            result = self.db.telemetry.bulk_write(updates)
            logger.info(f"Updated {result.modified_count} telemetry records with organization_id")
        
        # Handle orphaned records
        orphaned_count = self.db.telemetry.count_documents({
            "organization_id": {"$exists": False}
        })
        
        if orphaned_count > 0:
            logger.warning(f"Found {orphaned_count} orphaned telemetry records")
            # Mark orphaned records
            self.db.telemetry.update_many(
                {"organization_id": {"$exists": False}},
                {"$set": {"organization_id": "orphaned", "orphaned_at": datetime.now()}}
            )
    
    def _migrate_admin_role(self):
        """Update admin@tesa.local and other platform admins to super_admin role."""
        logger.info("Migrating admin users to super_admin role...")
        
        # Update specific admin users
        admin_emails = ['admin@tesa.local', 'platform-admin@tesa.local']
        
        result = self.db.users.update_many(
            {
                "$or": [
                    {"email": {"$in": admin_emails}},
                    {"role": "admin", "organization_id": "tesa"}
                ]
            },
            {"$set": {"role": "super_admin", "updated_at": datetime.now()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated {result.modified_count} admin users to super_admin role")
    
    def _fix_device_organization_ids(self):
        """Ensure all devices have valid organization_id."""
        logger.info("Fixing device organization IDs...")
        
        # Find devices with missing or invalid organization_id
        devices = self.db.devices.find({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": ""},
                {"organization_id": None}
            ]
        })
        
        fixed_count = 0
        for device in devices:
            # Try to determine organization from device metadata or creator
            org_id = None
            
            # Check if device has organization field
            if device.get('organization'):
                org = self.db.organizations.find_one({"name": device['organization']})
                if org:
                    org_id = str(org['_id'])
            
            # Check creator's organization
            if not org_id and device.get('created_by'):
                user = self.db.users.find_one({"_id": ObjectId(device['created_by'])})
                if user and user.get('organization_id'):
                    org_id = user['organization_id']
            
            # Default to 'default-org' if cannot determine
            if not org_id:
                org_id = 'default-org'
            
            # Update device
            self.db.devices.update_one(
                {"_id": device['_id']},
                {"$set": {"organization_id": org_id, "updated_at": datetime.now()}}
            )
            fixed_count += 1
        
        if fixed_count > 0:
            logger.info(f"Fixed organization_id for {fixed_count} devices")
    
    def _migrate_csr_tracking_collections(self):
        """Run the CSR tracking collections migration."""
        logger.info("Running CSR tracking collections migration...")
        
        try:
            # Import and run the CSR tracking collections creation
            import sys
            import os
            
            # Add migrations directory to path
            migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
            sys.path.append(migrations_dir)
            
            from create_csr_tracking_collections import create_csr_tracking_collections
            
            # Run the migration
            success = create_csr_tracking_collections()
            
            if success:
                logger.info("CSR tracking collections migration completed successfully")
            else:
                logger.error("CSR tracking collections migration failed")
                
        except ImportError as e:
            logger.warning(f"CSR tracking migration script not found: {e}")
            logger.info("Creating CSR collections using built-in method...")
            self._ensure_csr_indexes()
        except Exception as e:
            logger.error(f"Error running CSR tracking migration: {e}")
            # Fallback to built-in method
            self._ensure_csr_indexes()
    
    def _migrate_device_public_key_tracking(self):
        """Run the device public key tracking collections migration."""
        logger.info("Running device public key tracking collections migration...")
        
        try:
            # Import and run the device public key tracking collections creation
            import sys
            import os
            
            # Add migrations directory to path
            migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
            sys.path.append(migrations_dir)
            
            from add_device_public_key_fields import create_device_public_key_collections
            
            # Run the migration
            success = create_device_public_key_collections()
            
            if success:
                logger.info("Device public key tracking collections migration completed successfully")
            else:
                logger.error("Device public key tracking collections migration failed")
                
        except ImportError as e:
            logger.warning(f"Device public key tracking migration script not found: {e}")
            logger.info("Creating device public key collections using built-in method...")
            self._ensure_device_public_key_indexes()
        except Exception as e:
            logger.error(f"Error running device public key tracking migration: {e}")
            # Fallback to built-in method
            self._ensure_device_public_key_indexes()
    
    def _migrate_add_missing_menu_items(self):
        """Add missing menu items to existing service configurations."""
        logger.info("Running add missing menu items migration...")
        
        try:
            # Import and run the missing menu items migration
            import sys
            import os
            
            # Add migrations directory to path
            migrations_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
            sys.path.append(migrations_dir)
            
            from add_missing_menu_items import add_missing_menu_items
            
            # Run the migration
            success = add_missing_menu_items()
            
            if success:
                logger.info("Add missing menu items migration completed successfully")
            else:
                logger.error("Add missing menu items migration failed")
                
        except ImportError as e:
            logger.warning(f"Add missing menu items migration script not found: {e}")
            logger.info("Adding missing menu items using built-in method...")
            self._ensure_missing_menu_items()
        except Exception as e:
            logger.error(f"Error running add missing menu items migration: {e}")
            # Fallback to built-in method
            self._ensure_missing_menu_items()
    
    def _ensure_missing_menu_items(self):
        """Fallback method to add missing menu items to service configurations."""
        logger.info("Adding missing menu items using built-in method...")
        
        try:
            # Define the new menu items that need to be added
            new_menu_items = {
                "menu_certificates": True,
                "menu_system_health": True,
                "menu_activity_logs": True,
                "menu_organizations": True,
                "menu_api_keys": True
            }
            
            # Get all existing service configurations
            configurations = list(self.db.service_configurations.find({}))
            
            if not configurations:
                logger.info("No existing service configurations found. New organizations will get the updated default features.")
                return True
            
            updated_count = 0
            
            for config in configurations:
                organization_id = config.get('organization_id')
                current_features = config.get('features', {})
                
                # Check if any of the new menu items are missing
                needs_update = False
                features_to_add = {}
                
                for menu_item, default_value in new_menu_items.items():
                    if menu_item not in current_features:
                        features_to_add[menu_item] = default_value
                        needs_update = True
                
                if needs_update:
                    # Update the features dictionary
                    updated_features = current_features.copy()
                    updated_features.update(features_to_add)
                    
                    # Update the configuration
                    update_result = self.db.service_configurations.update_one(
                        {"organization_id": organization_id},
                        {
                            "$set": {
                                "features": updated_features,
                                "updated_at": datetime.now().isoformat(),
                                "updated_by": "system_migration"
                            }
                        }
                    )
                    
                    if update_result.modified_count > 0:
                        updated_count += 1
                        added_items = ", ".join(features_to_add.keys())
                        logger.info(f"Updated organization {organization_id}: Added {added_items}")
                        
                        # Create audit entry
                        audit_entry = {
                            "organization_id": organization_id,
                            "action": "migration_update",
                            "changes": [
                                {
                                    "feature": item,
                                    "old_value": None,
                                    "new_value": value
                                } for item, value in features_to_add.items()
                            ],
                            "user_email": "system_migration",
                            "migration_type": "add_missing_menu_items_builtin",
                            "created_at": datetime.now().isoformat()
                        }
                        
                        try:
                            self.db.service_configuration_audit.insert_one(audit_entry)
                        except Exception as e:
                            logger.warning(f"Failed to create audit entry for org {organization_id}: {e}")
            
            logger.info(f"Built-in migration completed. Updated {updated_count} organizations.")
            return True
            
        except Exception as e:
            logger.error(f"Error in built-in missing menu items migration: {e}")
            return False
    
    def _ensure_device_public_key_indexes(self):
        """Create device public key tracking collection indexes."""
        logger.info("Creating device public key tracking collection indexes...")
        
        try:
            from pymongo import ASCENDING, DESCENDING
            
            # 1. Device Public Keys Collection
            if 'device_public_keys' not in self.db.list_collection_names():
                self.db.create_collection('device_public_keys')
            
            self.db.device_public_keys.create_index([('key_id', ASCENDING)], unique=True)
            self.db.device_public_keys.create_index([('device_id', ASCENDING), ('fingerprint', ASCENDING)], unique=True)
            self.db.device_public_keys.create_index([('device_id', ASCENDING), ('status', ASCENDING), ('created_at', DESCENDING)])
            self.db.device_public_keys.create_index([('fingerprint', ASCENDING), ('status', ASCENDING)])
            self.db.device_public_keys.create_index([('organization_id', ASCENDING), ('status', ASCENDING), ('created_at', DESCENDING)])
            self.db.device_public_keys.create_index([('expires_at', ASCENDING)])
            
            # 2. Public Key History Collection
            if 'device_public_key_history' not in self.db.list_collection_names():
                self.db.create_collection('device_public_key_history')
            
            self.db.device_public_key_history.create_index([('history_id', ASCENDING)], unique=True)
            self.db.device_public_key_history.create_index([('device_id', ASCENDING), ('timestamp', DESCENDING)])
            self.db.device_public_key_history.create_index([('key_id', ASCENDING), ('timestamp', DESCENDING)])
            
            # 3. Key Rotation Tracking Collection
            if 'device_key_rotation_tracking' not in self.db.list_collection_names():
                self.db.create_collection('device_key_rotation_tracking')
            
            self.db.device_key_rotation_tracking.create_index([('rotation_id', ASCENDING)], unique=True)
            self.db.device_key_rotation_tracking.create_index([('device_id', ASCENDING), ('scheduled_at', ASCENDING)])
            
            # TTL indexes for automatic cleanup
            self.db.device_public_key_history.create_index([('timestamp', ASCENDING)], expireAfterSeconds=2*365*24*60*60)  # 2 years
            self.db.device_key_rotation_tracking.create_index([('completed_at', ASCENDING)], expireAfterSeconds=365*24*60*60)  # 1 year
            
            # Update devices collection indexes for public key tracking
            if 'devices' in self.db.list_collection_names():
                self.db.devices.create_index([('current_public_key.fingerprint', ASCENDING)], sparse=True)
                self.db.devices.create_index([('public_key_history', ASCENDING)], sparse=True)
            
            logger.info("Device public key tracking collection indexes created/verified")
            
        except Exception as e:
            logger.error(f"Error creating device public key tracking indexes: {e}")
    
    def _ensure_default_data(self):
        """Ensure required default data exists."""
        logger.info("Ensuring default data exists...")
        
        # Import services
        from .user_service import ensure_admin_users
        from .organization_service import ensure_default_organizations
        
        # Create default organizations
        ensure_default_organizations()
        
        # Create default admin users
        ensure_admin_users()
        
        # Ensure audit log indexes exist
        self._ensure_audit_collections()
        
        logger.info("Default data verification completed")
    
    def _ensure_audit_collections(self):
        """Ensure audit log collections exist with proper structure."""
        # Create audit_logs collection if not exists
        if 'audit_logs' not in self.db.list_collection_names():
            self.db.create_collection('audit_logs')
            logger.info("Created audit_logs collection")
        
        # Create security_violations collection if not exists
        if 'security_violations' not in self.db.list_collection_names():
            self.db.create_collection('security_violations')
            logger.info("Created security_violations collection")
        
        # Create migration_history collection if not exists
        if 'migration_history' not in self.db.list_collection_names():
            self.db.create_collection('migration_history')
            logger.info("Created migration_history collection")
    
    def _verify_data_integrity(self):
        """Verify data integrity and log any issues."""
        logger.info("Verifying data integrity...")
        
        issues = []
        
        # Check for devices without organization_id
        orphan_devices = self.db.devices.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": ""},
                {"organization_id": None}
            ]
        })
        if orphan_devices > 0:
            issues.append(f"{orphan_devices} devices without organization_id")
        
        # Check for telemetry without organization_id
        orphan_telemetry = self.db.telemetry.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": "orphaned"}
            ]
        })
        if orphan_telemetry > 0:
            issues.append(f"{orphan_telemetry} telemetry records without valid organization_id")
        
        # Check for users without organization_id
        orphan_users = self.db.users.count_documents({
            "$or": [
                {"organization_id": {"$exists": False}},
                {"organization_id": ""},
                {"organization_id": None}
            ],
            "role": {"$ne": "super_admin"}  # Super admins may not have org
        })
        if orphan_users > 0:
            issues.append(f"{orphan_users} users without organization_id")
        
        # Log integrity report
        if issues:
            logger.warning(f"Data integrity issues found: {', '.join(issues)}")
        else:
            logger.info("Data integrity check passed - no issues found")
        
        # Create integrity report
        self.db.system_health.update_one(
            {"_id": "data_integrity"},
            {
                "$set": {
                    "last_check": datetime.now(),
                    "issues": issues,
                    "status": "healthy" if not issues else "needs_attention"
                }
            },
            upsert=True
        )
    
    def _initialize_ca_chain(self):
        """
        Initialize CA chain from Vault PKI for certificate downloads.
        This ensures the CA chain is always available when devices need it.
        
        Best Practice Implementation:
        - Part of core initialization, not external script
        - Self-healing: recreates if missing or invalid
        - Uses application configuration, not hardcoded paths
        - Includes proper error handling and logging
        """
        logger.info("Initializing CA chain from Vault PKI...")
        
        try:
            import requests
            from ..core.config import Config
            
            # Get configuration
            config = Config.get_config()
            vault_addr = os.environ.get('VAULT_ADDR', 'http://tesa-vault:8200')
            vault_token = _require_vault_token()
            
            # Define CA chain storage path
            ca_dir = "/app/scripts/ca"
            ca_chain_file = f"{ca_dir}/tesaiot-ca-chain.pem"
            
            # Create directory if it doesn't exist
            os.makedirs(ca_dir, exist_ok=True)
            
            # Check if valid CA chain already exists
            if os.path.exists(ca_chain_file):
                try:
                    with open(ca_chain_file, 'r') as f:
                        content = f.read()
                        if "BEGIN CERTIFICATE" in content and "END CERTIFICATE" in content:
                            logger.info(f"Valid CA chain already exists at: {ca_chain_file}")
                            return True
                except Exception as e:
                    logger.warning(f"Existing CA chain invalid, regenerating: {e}")
            
            # Fetch certificates from Vault PKI
            headers = {'X-Vault-Token': vault_token}
            ca_chain_parts = []
            
            # Get Intermediate CA
            try:
                response = requests.get(
                    f"{vault_addr}/v1/pki-int/cert/ca",
                    headers=headers,
                    verify=False,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    intermediate_cert = data.get('data', {}).get('certificate', '')
                    if intermediate_cert:
                        ca_chain_parts.append(intermediate_cert)
                        logger.info("Retrieved Intermediate CA from Vault")
            except Exception as e:
                logger.warning(f"Could not retrieve Intermediate CA: {e}")
            
            # Get Root CA
            try:
                response = requests.get(
                    f"{vault_addr}/v1/pki/cert/ca",
                    headers=headers,
                    verify=False,
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    root_cert = data.get('data', {}).get('certificate', '')
                    if root_cert:
                        ca_chain_parts.append(root_cert)
                        logger.info("Retrieved Root CA from Vault")
            except Exception as e:
                logger.warning(f"Could not retrieve Root CA: {e}")
            
            # If we have certificates, create the chain
            if ca_chain_parts:
                # Create CA chain with header
                ca_chain_content = """# TESA IoT Platform CA Certificate Chain
# ==========================================
# This certificate chain includes the CA hierarchy
# used by the platform for all device certificates.
# 
# Auto-generated during platform initialization
# Source: Vault PKI (pki-int and pki root)
# 
# Installation Instructions:
# -------------------------
# 
# For Linux/Raspberry Pi:
#   sudo cp tesaiot-ca-chain.pem /usr/local/share/ca-certificates/tesa-iot-ca.crt
#   sudo update-ca-certificates
# 
# For PSoC Edge/Embedded Devices:
#   Include this certificate in your firmware's trust store
# 
# For Python MQTT Clients:
#   client.tls_set(ca_certs='tesaiot-ca-chain.pem')

"""
                # Add certificates
                ca_chain_content += '\n'.join(ca_chain_parts)
                
                # Write to file
                with open(ca_chain_file, 'w') as f:
                    f.write(ca_chain_content)
                
                # Set proper permissions
                os.chmod(ca_chain_file, 0o644)
                
                logger.info(f"CA chain successfully created at: {ca_chain_file}")
                logger.info(f"CA chain contains {len(ca_chain_parts)} certificate(s)")
                
                # Store CA chain path in database for reference
                self.db.system_config.update_one(
                    {"_id": "ca_chain"},
                    {
                        "$set": {
                            "path": ca_chain_file,
                            "created_at": datetime.now(),
                            "certificates_count": len(ca_chain_parts),
                            "source": "vault_pki"
                        }
                    },
                    upsert=True
                )
                
                return True
            else:
                logger.error("No certificates retrieved from Vault PKI")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize CA chain: {e}")
            # Don't fail the entire initialization, just log the error
            # The certificate service will handle the missing CA chain gracefully
            return False
    
    def _initialize_pki_roles(self):
        """Initialize all required PKI roles in Vault for certificate generation."""
        try:
            import hvac
            
            vault_addr = os.environ.get('VAULT_ADDR', 'http://tesa-vault:8200')
            vault_token = _require_vault_token()
            
            vault_client = hvac.Client(url=vault_addr, token=vault_token)
            
            if not vault_client.is_authenticated():
                logger.error("Unable to authenticate with Vault for PKI role initialization")
                return False
            
            # Base configuration for all IoT device roles
            base_config = {
                "allowed_domains": ["device.tesa.iot", "sensor.tesa.iot", "gateway.tesa.iot", "tesa.iot", "localhost"],
                "allow_subdomains": True,
                "allow_bare_domains": True,
                "allow_localhost": True,
                "allow_ip_sans": True,
                "allow_any_name": False,
                "enforce_hostnames": False,
                "require_cn": True,
                "organization": ["TESA IoT Platform"],
                "ou": ["IoT Devices"],
                "country": ["TH"],
                "key_usage": ["DigitalSignature", "KeyAgreement", "KeyEncipherment"],
                "client_flag": True,
                "server_flag": True
            }
            
            # Define all required PKI roles
            pki_roles = [
                # ECC roles for low-power devices
                {"name": "iot-device-ecc", "key_type": "ec", "key_bits": 256},
                {"name": "iot-sensor-ecc", "key_type": "ec", "key_bits": 256},
                {"name": "iot-device-ecc-p384", "key_type": "ec", "key_bits": 384},
                {"name": "iot-gateway-ecc", "key_type": "ec", "key_bits": 384},
                # RSA roles for standard and high-performance devices
                {"name": "iot-device-rsa", "key_type": "rsa", "key_bits": 2048},
                {"name": "iot-gateway-rsa", "key_type": "rsa", "key_bits": 3072},
                {"name": "iot-device-rsa-4096", "key_type": "rsa", "key_bits": 4096},
                # Specialized device roles
                {"name": "iot-medical-device", "key_type": "rsa", "key_bits": 3072},
                {"name": "iot-industrial-sensor", "key_type": "rsa", "key_bits": 2048},
                {"name": "iot-edge-ai", "key_type": "rsa", "key_bits": 4096}
            ]
            
            created_roles = []
            for role in pki_roles:
                try:
                    # Create role configuration
                    role_config = base_config.copy()
                    role_config.update({
                        "key_type": role["key_type"],
                        "key_bits": role["key_bits"],
                        "max_ttl": "8760h",  # 1 year
                        "ttl": "720h"  # 30 days
                    })
                    
                    # Write role to Vault
                    vault_client.write(f'pki-int/roles/{role["name"]}', **role_config)
                    created_roles.append(role["name"])
                    logger.info(f"Created PKI role: {role['name']}")
                    
                except Exception as e:
                    logger.warning(f"PKI role {role['name']} may already exist or error: {e}")
            
            # Verify roles were created
            try:
                roles_list = vault_client.list('pki-int/roles')
                if roles_list and 'data' in roles_list and 'keys' in roles_list['data']:
                    existing_roles = roles_list['data']['keys']
                    logger.info(f"PKI roles available: {existing_roles}")
                    
                    # Store PKI roles configuration in database
                    self.db.system_config.update_one(
                        {"_id": "pki_roles"},
                        {
                            "$set": {
                                "roles": existing_roles,
                                "created_at": datetime.now(),
                                "source": "vault_pki_init"
                            }
                        },
                        upsert=True
                    )
                    return True
            except Exception as e:
                logger.error(f"Failed to verify PKI roles: {e}")
            
            return len(created_roles) > 0
            
        except Exception as e:
            logger.error(f"Failed to initialize PKI roles: {e}")
            return False

# Service initialization function
def initialize_database(db):
    """Initialize database with all required data and migrations."""
    service = DatabaseInitService(db)
    return service.initialize()