# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Telemetry TimescaleDB Integration
Safe integration layer for automatic schema management
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TelemetryTimescaleIntegration:
    """
    Safely integrates automatic TimescaleDB schema with telemetry flow
    """
    
    def __init__(self):
        self.enabled = False  # Start disabled for safety
        self.auto_schema = None
        self._initialize()
    
    def _initialize(self):
        """
        Initialize integration if environment allows
        """
        try:
            # Check if feature flag is enabled
            import os
            if os.getenv('ENABLE_AUTO_TIMESCALE_SCHEMA', 'false').lower() == 'true':
                from .timescaledb_auto_schema import TimescaleDBAutoSchema
                from ..core.database import get_postgres
                
                conn = get_postgres()
                if conn:
                    self.auto_schema = TimescaleDBAutoSchema(conn)
                    self.enabled = True
                    logger.info("✅ TimescaleDB auto-schema integration ENABLED")
                else:
                    logger.warning("TimescaleDB connection not available")
            else:
                logger.info("TimescaleDB auto-schema integration disabled (set ENABLE_AUTO_TIMESCALE_SCHEMA=true to enable)")
        except Exception as e:
            logger.error(f"Failed to initialize TimescaleDB integration: {e}")
            self.enabled = False
    
    def should_store_in_timescale(self, device_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if device should store data in TimescaleDB
        Returns: (should_store, table_name)
        """
        if not self.enabled:
            return False, None
        
        try:
            # Check if dual storage is enabled (default true)
            import os
            if os.getenv('ENABLE_DUAL_STORAGE', 'true').lower() != 'true':
                return False, None
            
            # ALL devices use the generic table by default
            # This ensures EVERY device can store in TimescaleDB
            return True, 'telemetry_generic'
            
        except Exception as e:
            logger.error(f"Error checking TimescaleDB status for device {device_id}: {e}")
            return False, None
    
    def _table_exists(self, table_name: str) -> bool:
        """
        Check if TimescaleDB table exists
        """
        try:
            from ..core.database import get_postgres
            conn = get_postgres()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table_name,))
                result = cursor.fetchone()
                return result[0] if result else False
                
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def register_device(self, device_id: str, organization_id: str, device_type: str = 'sensor') -> bool:
        """
        Register device presence in TimescaleDB for analytics readiness.

        Creates a lightweight devices_registry table if missing and inserts the
        device entry (device_id, organization_id, device_type, created_at).
        Safe no-op if integration disabled or connection missing.
        """
        if not self.enabled:
            return False
        try:
            from ..core.database import get_postgres
            conn = get_postgres()
            if not conn:
                return False
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS devices_registry (
                        device_id TEXT PRIMARY KEY,
                        organization_id TEXT,
                        device_type TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO devices_registry (device_id, organization_id, device_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (device_id) DO NOTHING
                    """,
                    (device_id, organization_id or 'default', (device_type or 'sensor'))
                )
            conn.commit()
            logger.info(f"✅ Registered device {device_id} in Timescale devices_registry")
            return True
        except Exception as e:
            logger.warning(f"Could not register device in Timescale: {e}")
            return False
    
    def store_telemetry(
        self,
        device_id: str,
        timestamp: datetime,
        data: Dict[str, Any],
        metadata: Dict[str, Any],
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Store telemetry in TimescaleDB if appropriate
        """
        if not self.enabled:
            return False
        
        try:
            # Check if device should use TimescaleDB
            should_store, table_name = self.should_store_in_timescale(device_id)
            
            if not should_store or not table_name:
                logger.debug(f"Device {device_id} not configured for TimescaleDB")
                return False
            
            # Get device type from MongoDB
            device_type = 'sensor'  # Default
            try:
                from ..core.database import get_db
                db = get_db()
                device = db.devices.find_one({'device_id': device_id})
                if device:
                    device_type = device.get('type', 'sensor')
                else:
                    # Check device_auth collection
                    device_auth = db.device_auth.find_one({'device_id': device_id})
                    if device_auth:
                        device_type = device_auth.get('device_type', 'sensor')
            except Exception as e:
                logger.warning(f"Could not get device type: {e}")
            
            # Get connection
            from ..core.database import get_postgres
            conn = get_postgres()
            if not conn:
                return False
            
            with conn.cursor() as cursor:
                # For generic table, we store everything in JSONB
                if table_name == 'telemetry_generic':
                    # Ensure table exists (should already exist from initialization)
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS telemetry_generic (
                            time TIMESTAMPTZ NOT NULL,
                            device_id TEXT NOT NULL,
                            device_type VARCHAR(255),
                            organization_id VARCHAR(255),
                            data JSONB,
                            metadata JSONB
                        );

                        SELECT create_hypertable('telemetry_generic', 'time', if_not_exists => TRUE);
                    """)
                    
                    # Create indexes if not exist
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_telemetry_generic_device_id 
                        ON telemetry_generic(device_id, time DESC);
                        
                        CREATE INDEX IF NOT EXISTS idx_telemetry_generic_device_type 
                        ON telemetry_generic(device_type, time DESC);
                        
                        CREATE INDEX IF NOT EXISTS idx_telemetry_generic_org 
                        ON telemetry_generic(organization_id, time DESC);
                    """)
                    
                    # Device IDs are arbitrary strings (e.g. "test-sensor-001"),
                    # not UUIDs, so device_id is stored as TEXT (see CREATE above)
                    # and inserted as-is.
                    insert_sql = """
                        INSERT INTO telemetry_generic (time, device_id, device_type, organization_id, data, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """

                    cursor.execute(insert_sql, (
                        timestamp,
                        device_id,
                        device_type,
                        organization_id or 'default',
                        json.dumps(data),
                        json.dumps(metadata) if metadata else json.dumps({})
                    ))

                    # ✅ DUAL STORAGE: Also write to device_telemetry (metric_name/metric_value format) for BDH AI
                    self._store_metrics_format(cursor, device_id, timestamp, data, metadata, organization_id)

                    # Also update device metadata table (created on demand; a
                    # missing table here must not roll back the telemetry write).
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS device_telemetry_metadata (
                            device_type VARCHAR(255) PRIMARY KEY,
                            table_name VARCHAR(255),
                            schema_definition JSONB,
                            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    cursor.execute("""
                        INSERT INTO device_telemetry_metadata (device_type, table_name, schema_definition)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (device_type) DO UPDATE
                        SET updated_at = CURRENT_TIMESTAMP
                    """, (
                        device_type,
                        f'telemetry_{device_type.lower()}',
                        json.dumps({'fields': list(data.keys())})
                    ))
                else:
                    # Legacy path for specific tables (kept for backward compatibility)
                    # Get table columns
                    cursor.execute("""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = %s
                        AND table_schema = 'public';
                    """, (table_name,))
                    
                    columns = {row[0] for row in cursor.fetchall()}
                    
                    # Flatten nested data for columnar storage
                    flattened_data = self._flatten_data(data)
                    
                    # Prepare insert data
                    insert_cols = ['time', 'device_id']
                    insert_vals = [timestamp, device_id]
                    
                    if 'organization_id' in columns and organization_id:
                        insert_cols.append('organization_id')
                        insert_vals.append(organization_id)
                    
                    # Add data columns
                    jsonb_data = {}
                    for key, value in flattened_data.items():
                        if key in columns:
                            insert_cols.append(key)
                            insert_vals.append(value)
                        else:
                            jsonb_data[key] = value
                    
                    # Add JSONB data if any
                    if jsonb_data and 'data' in columns:
                        insert_cols.append('data')
                        insert_vals.append(json.dumps(jsonb_data))
                    
                    # Add metadata if column exists
                    if metadata and 'metadata' in columns:
                        insert_cols.append('metadata')
                        insert_vals.append(json.dumps(metadata))
                    
                    # Build and execute INSERT
                    placeholders = ', '.join(['%s'] * len(insert_vals))
                    insert_sql = f"""
                        INSERT INTO {table_name} ({', '.join(insert_cols)})
                        VALUES ({placeholders})
                        ON CONFLICT (device_id, time) DO UPDATE
                        SET data = EXCLUDED.data,
                            metadata = EXCLUDED.metadata;
                    """
                    
                    cursor.execute(insert_sql, insert_vals)
                
                conn.commit()
                logger.info(f"✅ Stored telemetry in TimescaleDB table {table_name} for device {device_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error storing telemetry in TimescaleDB: {e}")
            return False
    
    def _flatten_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested data structure
        Example: {"accel": {"x": 1}} → {"accel_x": 1}
        """
        flattened = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Flatten nested dict
                for sub_key, sub_value in value.items():
                    flattened[f"{key}_{sub_key}"] = sub_value
            else:
                flattened[key] = value

        return flattened

    def _store_metrics_format(
        self,
        cursor,
        device_id: str,
        timestamp: datetime,
        data: Dict[str, Any],
        metadata: Dict[str, Any],
        organization_id: Optional[str] = None
    ) -> None:
        """
        Store telemetry data in device_telemetry table (metric_name/metric_value format)
        This format is required by BDH AI for time-series analytics

        Converts JSONB data like:
          {"data_temperature": 22.5, "data_humidity": 60}
        Into metric rows:
          (temperature, 22.5, °C)
          (humidity, 60, %)
        """
        # Metric mapping: field_name → (metric_name, unit)
        METRIC_MAPPINGS = {
            'data_temperature': ('temperature', '°C'),
            'data_humidity': ('humidity', '%'),
            'data_pressure': ('pressure', 'hPa'),
            'temperature': ('temperature', '°C'),
            'humidity': ('humidity', '%'),
            'pressure': ('pressure', 'hPa'),
            'battery': ('battery', '%'),
            'voltage': ('voltage', 'V'),
            'signal_strength': ('signal_strength', 'dBm'),
            'accel_x': ('accel_x', 'm/s²'),
            'accel_y': ('accel_y', 'm/s²'),
            'accel_z': ('accel_z', 'm/s²'),
            'gyro_x': ('gyro_x', 'rad/s'),
            'gyro_y': ('gyro_y', 'rad/s'),
            'gyro_z': ('gyro_z', 'rad/s'),
            'latitude': ('latitude', '°'),
            'longitude': ('longitude', '°'),
            'altitude': ('altitude', 'm'),
        }

        try:
            # Ensure device_telemetry table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_telemetry (
                    time TIMESTAMPTZ NOT NULL,
                    device_id VARCHAR(255) NOT NULL,
                    organization_id VARCHAR(255),
                    metric_name VARCHAR(100) NOT NULL,
                    metric_value DOUBLE PRECISION NOT NULL,
                    unit VARCHAR(50),
                    location JSONB,
                    metadata JSONB
                );

                SELECT create_hypertable('device_telemetry', 'time', if_not_exists => TRUE);

                CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
                ON device_telemetry(device_id, time DESC);

                CREATE INDEX IF NOT EXISTS idx_telemetry_metric
                ON device_telemetry(metric_name, time DESC);

                CREATE INDEX IF NOT EXISTS idx_telemetry_org_time
                ON device_telemetry(organization_id, time DESC);
            """)

            # Extract metrics from data
            metrics_to_insert = []

            for field_name, field_value in data.items():
                # Skip non-numeric values
                if not isinstance(field_value, (int, float)):
                    continue

                # Get metric name and unit
                if field_name in METRIC_MAPPINGS:
                    metric_name, unit = METRIC_MAPPINGS[field_name]
                else:
                    # Unknown metric, skip metadata fields
                    if field_name.startswith('metadata_'):
                        continue
                    # Use field name as-is for unmapped metrics
                    metric_name = field_name
                    unit = None

                metrics_to_insert.append({
                    'time': timestamp,
                    'device_id': device_id,
                    'organization_id': organization_id or 'default',
                    'metric_name': metric_name,
                    'metric_value': float(field_value),
                    'unit': unit,
                    'metadata': json.dumps(metadata) if metadata else None
                })

            if not metrics_to_insert:
                return

            # Batch insert metrics
            insert_query = """
                INSERT INTO device_telemetry (time, device_id, organization_id, metric_name, metric_value, unit, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """

            cursor.executemany(insert_query, [
                (
                    m['time'],
                    m['device_id'],
                    m['organization_id'],
                    m['metric_name'],
                    m['metric_value'],
                    m['unit'],
                    m['metadata']
                )
                for m in metrics_to_insert
            ])

            logger.debug(f"✅ Stored {len(metrics_to_insert)} metrics in device_telemetry for device {device_id}")

        except Exception as e:
            logger.warning(f"Failed to store metrics format: {e}")
            # Don't fail the main telemetry storage if metrics storage fails
            pass
    
    def create_table_for_device(self, device_id: str) -> Optional[str]:
        """
        Create TimescaleDB table for a device based on its type
        Called when device is created/updated
        """
        if not self.enabled or not self.auto_schema:
            return None
        
        try:
            from ..core.database import get_db
            db = get_db()
            
            # Get device info
            device_auth = db.device_auth.find_one({'device_id': device_id})
            if not device_auth:
                logger.warning(f"Device {device_id} not found")
                return None
            
            # Check if device sends IMU data (Device02, Device03 pattern)
            # This is a simple heuristic - in production, use device schema
            device_type = device_auth.get('device_type', 'sensor')
            org_id = device_auth.get('organization_id', 'default')
            
            # For demonstration, create IMU table for our test devices
            if device_id in ['22e3c632-4611-4976-80e6-14dbeb8892b9', '2a757995-4107-406d-9893-6b1b93a3f137']:
                table_name = f"telemetry_imu_{org_id[:8]}"
                
                from ..core.database import get_postgres
                conn = get_postgres()
                if not conn:
                    return None
                
                with conn.cursor() as cursor:
                    # Create IMU-specific table
                    create_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        device_id VARCHAR(255) NOT NULL,
                        organization_id VARCHAR(255),
                        accel_x DOUBLE PRECISION,
                        accel_y DOUBLE PRECISION,
                        accel_z DOUBLE PRECISION,
                        gyro_x DOUBLE PRECISION,
                        gyro_y DOUBLE PRECISION,
                        gyro_z DOUBLE PRECISION,
                        step_count INTEGER,
                        activity TEXT,
                        data JSONB,
                        metadata JSONB,
                        PRIMARY KEY (device_id, time)
                    );
                    
                    -- Convert to hypertable if not already
                    SELECT create_hypertable(
                        '{table_name}',
                        'time',
                        if_not_exists => TRUE
                    );
                    
                    -- Create indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_accel 
                    ON {table_name}(accel_x, accel_y, accel_z)
                    WHERE accel_x IS NOT NULL;
                    
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_device_time
                    ON {table_name}(device_id, time DESC);
                    """
                    
                    cursor.execute(create_sql)
                    conn.commit()
                    
                    logger.info(f"✅ Created TimescaleDB table {table_name} for device {device_id}")
                    
                    # Update device record
                    db.devices.update_one(
                        {'device_id': device_id},
                        {'$set': {'timescale_table': table_name}},
                        upsert=True
                    )
                    
                    return table_name
                    
        except Exception as e:
            logger.error(f"Error creating table for device {device_id}: {e}")
            return None

# Singleton instance
_integration = TelemetryTimescaleIntegration()

def get_telemetry_timescale_integration():
    """Get the singleton integration instance"""
    return _integration
