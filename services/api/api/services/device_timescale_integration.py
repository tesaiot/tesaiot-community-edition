# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device TimescaleDB Integration
Hooks into device creation/update to automatically sync schemas
"""

import logging
from typing import Optional
from src.python.api.services.timescaledb_auto_schema import TimescaleDBAutoSchema
from src.python.api.utils.database import get_timescale_connection

logger = logging.getLogger(__name__)

class DeviceTimescaleIntegration:
    """
    Integrates device operations with TimescaleDB schema management
    """
    
    def __init__(self):
        self.auto_schema = None
        self._initialize()
    
    def _initialize(self):
        """
        Initialize TimescaleDB connection
        """
        try:
            conn = get_timescale_connection()
            if conn:
                self.auto_schema = TimescaleDBAutoSchema(conn)
                logger.info("TimescaleDB auto-schema integration initialized")
        except Exception as e:
            logger.warning(f"TimescaleDB integration not available: {e}")
    
    async def on_device_created(self, device_data: dict) -> Optional[dict]:
        """
        Called when a device is created
        Automatically creates/updates TimescaleDB schema
        """
        if not self.auto_schema:
            return None
        
        try:
            device_id = device_data.get('device_id') or device_data.get('_id')
            
            # Only process if device has telemetry schema
            if not device_data.get('telemetrySchema'):
                logger.debug(f"Device {device_id} has no telemetry schema")
                return None
            
            # Sync schema to TimescaleDB
            result = await self.auto_schema.sync_device_schema(
                device_id=str(device_id),
                device_data=device_data
            )
            
            if result.get('success'):
                logger.info(f"Device {device_id} schema synced to TimescaleDB: {result.get('table_name')}")
                
                # Update device record with TimescaleDB info
                return {
                    'timescale_table': result.get('table_name'),
                    'timescale_columns': result.get('columns_created', []),
                    'timescale_sync_status': 'active'
                }
            else:
                logger.error(f"Failed to sync device {device_id} schema: {result.get('error')}")
                return {
                    'timescale_sync_status': 'failed',
                    'timescale_sync_error': result.get('error')
                }
                
        except Exception as e:
            logger.error(f"Error in on_device_created: {e}")
            return None
    
    async def on_device_updated(self, device_id: str, updates: dict) -> Optional[dict]:
        """
        Called when a device is updated
        Evolves TimescaleDB schema if needed
        """
        if not self.auto_schema:
            return None
        
        try:
            # Check if telemetry schema was updated
            if 'telemetrySchema' not in updates:
                return None
            
            # Get full device data (need device type, etc.)
            from src.python.api.services.device_service import DeviceService
            device_service = DeviceService()
            device_data = device_service.get_device(device_id)
            
            if not device_data:
                logger.warning(f"Device {device_id} not found")
                return None
            
            # Update with new schema
            device_data['telemetrySchema'] = updates['telemetrySchema']
            
            # Sync updated schema
            result = await self.auto_schema.sync_device_schema(
                device_id=device_id,
                device_data=device_data
            )
            
            if result.get('success'):
                logger.info(f"Device {device_id} schema evolved in TimescaleDB")
                return {
                    'timescale_table': result.get('table_name'),
                    'timescale_sync_status': 'active'
                }
            else:
                logger.error(f"Failed to evolve device {device_id} schema: {result.get('error')}")
                return {
                    'timescale_sync_status': 'failed',
                    'timescale_sync_error': result.get('error')
                }
                
        except Exception as e:
            logger.error(f"Error in on_device_updated: {e}")
            return None
    
    async def on_telemetry_received(
        self, 
        device_id: str,
        organization_id: str,
        telemetry_data: dict,
        table_name: Optional[str] = None
    ) -> bool:
        """
        Called when telemetry is received
        Stores in TimescaleDB if table exists
        """
        if not self.auto_schema or not table_name:
            return False
        
        try:
            # Store in TimescaleDB
            success = await self.auto_schema.store_telemetry(
                device_id=device_id,
                organization_id=organization_id,
                telemetry_data=telemetry_data,
                table_name=table_name
            )
            
            if success:
                logger.debug(f"Telemetry stored in TimescaleDB for device {device_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing telemetry in TimescaleDB: {e}")
            return False
    
    def get_table_preview(self, schema_def: dict, device_type: str) -> str:
        """
        Generates SQL preview of what table would be created
        Used by Admin UI to show preview
        """
        if not self.auto_schema:
            return "TimescaleDB integration not available"
        
        try:
            # Generate table name
            table_name = self.auto_schema._generate_table_name(device_type, 'preview')
            
            # Parse schema
            properties = schema_def.get('properties', {})
            required_fields = schema_def.get('required', [])
            
            sql_preview = f"-- Table: {table_name}\n"
            sql_preview += "CREATE TABLE IF NOT EXISTS {} (\n".format(table_name)
            sql_preview += "    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),\n"
            sql_preview += "    device_id VARCHAR(255) NOT NULL,\n"
            sql_preview += "    organization_id VARCHAR(255),\n"
            
            # Add columns
            indexed_cols = []
            for prop_name, prop_def in properties.items():
                if prop_name.lower() in ['timestamp', 'time', 'datetime']:
                    continue
                
                if self.auto_schema._should_be_column(prop_name, prop_def, required_fields):
                    sql_type = self.auto_schema._json_type_to_sql(prop_def.get('type', 'string'))
                    sql_preview += f"    {prop_name} {sql_type},\n"
                    
                    if prop_name.lower() in self.auto_schema.common_metrics:
                        indexed_cols.append(prop_name)
            
            sql_preview += "    data JSONB,\n"
            sql_preview += "    metadata JSONB,\n"
            sql_preview += "    PRIMARY KEY (device_id, time)\n"
            sql_preview += ");\n\n"
            
            # Add hypertable
            sql_preview += f"SELECT create_hypertable('{table_name}', 'time');\n\n"
            
            # Add indexes
            for col in indexed_cols:
                sql_preview += f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col});\n"
            
            return sql_preview
            
        except Exception as e:
            return f"Error generating preview: {str(e)}"

# Singleton instance
_integration = DeviceTimescaleIntegration()

def get_timescale_integration():
    """
    Get the singleton TimescaleDB integration instance
    """
    return _integration