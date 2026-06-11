# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Automatic TimescaleDB Schema Generation
Automatically creates optimized TimescaleDB tables from device data schemas
"""

import json
import logging
from datetime import datetime
# import asyncpg  # Not needed - using psycopg2 directly
# from sqlalchemy import text  # Not needed - using psycopg2 directly

logger = logging.getLogger(__name__)

class TimescaleDBAutoSchema:
    """
    Automatically generates and manages TimescaleDB tables based on device telemetry schemas
    """
    
    def __init__(self, timescale_conn):
        self.conn = timescale_conn
        self.common_metrics = {
            'temperature', 'humidity', 'pressure', 'voltage', 'current', 'power',
            'battery_level', 'signal_strength', 'location_lat', 'location_lon',
            'speed', 'acceleration', 'co2', 'pm25', 'pm10', 'light_level',
            'noise_level', 'vibration', 'flow_rate', 'ph', 'dissolved_oxygen'
        }
    
    async def sync_device_schema(self, device_id: str, device_data: dict) -> dict:
        """
        Synchronizes device telemetry schema with TimescaleDB
        Called when device is created or updated
        """
        try:
            # Extract telemetry schema from device data
            telemetry_schema = device_data.get('telemetrySchema', {})
            schema_def = telemetry_schema.get('schema', {})
            
            if not schema_def or not schema_def.get('properties'):
                logger.info(f"Device {device_id} has no telemetry schema, skipping TimescaleDB sync")
                return {'success': True, 'message': 'No schema to sync'}
            
            # Get device type for table naming
            device_type = device_data.get('type', 'generic')
            device_name = device_data.get('name', '')
            organization_id = device_data.get('organization_id', 'default')
            
            # Generate table name based on device type
            table_name = self._generate_table_name(device_type, organization_id)
            
            # Check if table exists
            table_exists = await self._table_exists(table_name)
            
            if table_exists:
                # Evolve existing schema if needed
                result = await self._evolve_schema(table_name, schema_def)
                logger.info(f"Evolved schema for device {device_id}: {result}")
            else:
                # Create new table
                result = await self._create_table_from_schema(
                    table_name, 
                    schema_def,
                    device_type,
                    device_name
                )
                logger.info(f"Created table for device {device_id}: {result}")
            
            # Update device record with TimescaleDB table info
            return {
                'success': True,
                'table_name': table_name,
                'message': f'Schema synced to TimescaleDB table: {table_name}',
                'columns_created': result.get('columns', []),
                'indexes_created': result.get('indexes', [])
            }
            
        except Exception as e:
            logger.error(f"Error syncing schema for device {device_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_table_name(self, device_type: str, organization_id: str) -> str:
        """
        Generates table name from device type and organization
        Groups similar devices in same table for efficiency
        """
        # Normalize device type for table name
        type_normalized = device_type.lower().replace(' ', '_').replace('-', '_')
        
        # Common device type mappings to group similar devices
        type_mappings = {
            'sensor': 'sensor_data',
            'actuator': 'actuator_data',
            'gateway': 'gateway_data',
            'controller': 'controller_data',
            'environmental': 'environmental_data',
            'industrial': 'industrial_data',
            'medical': 'medical_data',
            'wearable': 'wearable_data',
            'imu': 'imu_data',
            'vibration': 'vibration_data',
            'air_quality': 'air_quality_data'
        }
        
        # Check if type matches common patterns
        for pattern, table_suffix in type_mappings.items():
            if pattern in type_normalized:
                return f"telemetry_{table_suffix}_{organization_id[:8]}"
        
        # Default table name
        return f"telemetry_{type_normalized[:20]}_{organization_id[:8]}"
    
    async def _table_exists(self, table_name: str) -> bool:
        """
        Checks if TimescaleDB table exists
        """
        query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
        """
        result = await self.conn.fetchval(query, table_name)
        return result
    
    async def _create_table_from_schema(
        self, 
        table_name: str, 
        schema_def: dict,
        device_type: str,
        device_name: str
    ) -> dict:
        """
        Creates TimescaleDB table from device telemetry schema
        """
        # Parse schema properties
        properties = schema_def.get('properties', {})
        required_fields = schema_def.get('required', [])
        
        # Start building CREATE TABLE statement
        columns = [
            "time TIMESTAMPTZ NOT NULL DEFAULT NOW()",
            "device_id VARCHAR(255) NOT NULL",
            "organization_id VARCHAR(255)"
        ]
        
        indexed_columns = []
        jsonb_fields = []
        
        # Analyze each property in the schema
        for prop_name, prop_def in properties.items():
            # Skip timestamp as we have 'time' column
            if prop_name.lower() in ['timestamp', 'time', 'datetime']:
                continue
            
            # Determine if should be column or JSONB
            if self._should_be_column(prop_name, prop_def, required_fields):
                sql_type = self._json_type_to_sql(prop_def.get('type', 'string'))
                columns.append(f"{prop_name} {sql_type}")
                
                # Mark for indexing if common metric or marked important
                if prop_name.lower() in self.common_metrics or prop_name in required_fields:
                    indexed_columns.append(prop_name)
            else:
                jsonb_fields.append(prop_name)
        
        # Always add JSONB column for flexibility
        columns.append("data JSONB")
        columns.append("metadata JSONB")
        
        # Create table
        create_sql = f"""
        -- Auto-generated from device schema: {device_name}
        -- Device type: {device_type}
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(columns)},
            PRIMARY KEY (device_id, time)
        );
        
        -- Convert to hypertable
        SELECT create_hypertable(
            '{table_name}',
            'time',
            if_not_exists => TRUE
        );
        """
        
        # Execute table creation
        await self.conn.execute(create_sql)
        
        # Create indexes for performance
        indexes_created = []
        for col in indexed_columns:
            index_name = f"idx_{table_name}_{col}"
            index_sql = f"""
            CREATE INDEX IF NOT EXISTS {index_name}
            ON {table_name}({col})
            WHERE {col} IS NOT NULL;
            """
            await self.conn.execute(index_sql)
            indexes_created.append(index_name)
        
        # Add compression policy (compress after 7 days)
        compression_sql = f"""
        SELECT add_compression_policy(
            '{table_name}', 
            compress_after => INTERVAL '7 days',
            if_not_exists => TRUE
        );
        """
        try:
            await self.conn.execute(compression_sql)
        except Exception as e:
            logger.warning(f"Could not add compression policy: {e}")
        
        logger.info(f"Created TimescaleDB table {table_name} with {len(columns)} columns")
        
        return {
            'columns': columns,
            'indexes': indexes_created,
            'jsonb_fields': jsonb_fields
        }
    
    async def _evolve_schema(self, table_name: str, schema_def: dict) -> dict:
        """
        Evolves existing table when schema changes
        Safe operation - only adds new columns, never removes
        """
        properties = schema_def.get('properties', {})
        required_fields = schema_def.get('required', [])
        
        # Get existing columns
        existing_columns_query = """
        SELECT column_name, data_type 
        FROM information_schema.columns
        WHERE table_name = %s
        AND table_schema = 'public';
        """
        existing = await self.conn.fetch(existing_columns_query, table_name)
        existing_cols = {row['column_name'] for row in existing}
        
        added_columns = []
        
        # Check for new fields to add
        for prop_name, prop_def in properties.items():
            # Skip if already exists or should be in JSONB
            if prop_name in existing_cols:
                continue
            
            if prop_name.lower() in ['timestamp', 'time', 'datetime']:
                continue
            
            # Only add as column if it's important
            if self._should_be_column(prop_name, prop_def, required_fields):
                sql_type = self._json_type_to_sql(prop_def.get('type', 'string'))
                
                alter_sql = f"""
                ALTER TABLE {table_name}
                ADD COLUMN IF NOT EXISTS {prop_name} {sql_type};
                """
                
                await self.conn.execute(alter_sql)
                added_columns.append(prop_name)
                
                # Add index if needed
                if prop_name.lower() in self.common_metrics:
                    index_sql = f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_{prop_name}
                    ON {table_name}({prop_name})
                    WHERE {prop_name} IS NOT NULL;
                    """
                    await self.conn.execute(index_sql)
        
        if added_columns:
            logger.info(f"Added {len(added_columns)} columns to {table_name}: {added_columns}")
        
        return {
            'columns': added_columns,
            'message': f"Added {len(added_columns)} new columns"
        }
    
    def _should_be_column(self, prop_name: str, prop_def: dict, required_fields: list) -> bool:
        """
        Determines if a schema property should be a dedicated column
        """
        # Common metrics get columns for performance
        if prop_name.lower() in self.common_metrics:
            return True
        
        # Required fields are likely important
        if prop_name in required_fields:
            return True
        
        # Numeric types perform better as columns
        if prop_def.get('type') in ['number', 'integer']:
            return True
        
        # Fields with constraints are likely important
        if 'minimum' in prop_def or 'maximum' in prop_def:
            return True
        
        # Arrays and objects go to JSONB
        if prop_def.get('type') in ['array', 'object']:
            return False
        
        return False
    
    def _json_type_to_sql(self, json_type: str) -> str:
        """
        Maps JSON schema types to PostgreSQL types
        """
        type_mapping = {
            'string': 'TEXT',
            'number': 'DOUBLE PRECISION',
            'integer': 'INTEGER',
            'boolean': 'BOOLEAN',
            'array': 'JSONB',
            'object': 'JSONB'
        }
        return type_mapping.get(json_type, 'TEXT')
    
    async def store_telemetry(
        self, 
        device_id: str,
        organization_id: str,
        telemetry_data: dict,
        table_name: str
    ) -> bool:
        """
        Stores telemetry data in the appropriate TimescaleDB table
        """
        try:
            # Get table columns to know what to insert
            columns_query = """
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = %s
            AND table_schema = 'public';
            """
            columns = await self.conn.fetch(columns_query, table_name)
            column_names = {row['column_name'] for row in columns}
            
            # Prepare data for insertion
            insert_data = {
                'time': telemetry_data.get('timestamp', datetime.utcnow()),
                'device_id': device_id,
                'organization_id': organization_id
            }
            
            jsonb_data = {}
            
            # Separate columnar data from JSONB data
            for key, value in telemetry_data.get('data', {}).items():
                if key in column_names:
                    insert_data[key] = value
                else:
                    jsonb_data[key] = value
            
            # Add JSONB data if any
            if jsonb_data:
                insert_data['data'] = json.dumps(jsonb_data)
            
            # Add metadata
            metadata = telemetry_data.get('metadata', {})
            if metadata:
                insert_data['metadata'] = json.dumps(metadata)
            
            # Build INSERT statement
            columns_list = list(insert_data.keys())
            values_list = [f"${i+1}" for i in range(len(columns_list))]
            
            insert_sql = f"""
            INSERT INTO {table_name} ({', '.join(columns_list)})
            VALUES ({', '.join(values_list)})
            ON CONFLICT (device_id, time) DO UPDATE
            SET data = EXCLUDED.data,
                metadata = EXCLUDED.metadata;
            """
            
            # Execute insertion
            await self.conn.execute(insert_sql, *insert_data.values())
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing telemetry in TimescaleDB: {str(e)}")
            return False