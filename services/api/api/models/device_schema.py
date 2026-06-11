# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Schema Data Models
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Enhanced device schema models for dynamic schema evolution and validation.
Integrates with the schema evolution service for automatic table generation.
"""

from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime
from enum import Enum
import json
import uuid
import hashlib
from dataclasses import dataclass, field, asdict

# Schema field types
class SchemaFieldType(str, Enum):
    """Supported schema field types for device data"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    FLOAT = "float"
    DOUBLE = "double"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    ARRAY = "array"
    OBJECT = "object"
    JSONB = "jsonb"

class SchemaOptimizationHint(str, Enum):
    """Optimization hints for schema field handling"""
    INDEX_FREQUENTLY = "index_frequently"  # Create B-tree index
    INDEX_RARELY = "index_rarely"         # No dedicated index
    FULL_TEXT_SEARCH = "full_text_search"  # Create GIN index for text search
    RANGE_QUERIES = "range_queries"        # Optimize for range queries
    EXACT_MATCH = "exact_match"           # Optimize for exact matching
    AGGREGATE = "aggregate"               # Field used in aggregations
    TIME_SERIES = "time_series"           # Time-based data pattern

class SchemaValidationLevel(str, Enum):
    """Validation strictness levels"""
    STRICT = "strict"      # Fail on any validation error
    LENIENT = "lenient"    # Warn on validation errors but proceed
    DISABLED = "disabled"  # Skip validation

class SchemaStorageStrategy(str, Enum):
    """Storage strategies for different data types"""
    COLUMNAR = "columnar"      # Store as dedicated column
    JSONB = "jsonb"           # Store in JSONB field
    HYBRID = "hybrid"         # Use both based on access patterns

@dataclass
class SchemaFieldConstraint:
    """Constraints for schema fields"""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    enum_values: Optional[List[Any]] = None
    required: bool = True
    unique: bool = False
    
    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a value against these constraints"""
        if value is None:
            if self.required:
                return False, "Field is required but value is None"
            return True, None
        
        # Type-specific validations
        if isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return False, f"Value {value} is less than minimum {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Value {value} is greater than maximum {self.max_value}"
        
        if isinstance(value, str):
            if self.min_length is not None and len(value) < self.min_length:
                return False, f"String length {len(value)} is less than minimum {self.min_length}"
            if self.max_length is not None and len(value) > self.max_length:
                return False, f"String length {len(value)} is greater than maximum {self.max_length}"
            if self.pattern is not None:
                import re
                if not re.match(self.pattern, value):
                    return False, f"String '{value}' does not match pattern '{self.pattern}'"
        
        if self.enum_values is not None and value not in self.enum_values:
            return False, f"Value '{value}' is not in allowed values {self.enum_values}"
        
        return True, None

@dataclass
class SchemaField:
    """Enhanced schema field definition"""
    name: str
    field_type: SchemaFieldType
    description: Optional[str] = None
    unit: Optional[str] = None
    constraints: Optional[SchemaFieldConstraint] = None
    optimization_hints: List[SchemaOptimizationHint] = field(default_factory=list)
    storage_strategy: SchemaStorageStrategy = SchemaStorageStrategy.HYBRID
    indexed: bool = False
    nullable: bool = True
    default_value: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Analytics and ML hints
    is_feature: bool = False  # Used in ML feature extraction
    is_target: bool = False   # ML prediction target
    privacy_level: str = "public"  # public, private, sensitive, pii
    
    # Performance tracking
    access_frequency: float = 0.0  # Access frequency (0.0 to 1.0)
    query_patterns: Set[str] = field(default_factory=set)  # Common query patterns
    
    def should_be_column(self) -> bool:
        """Determine if field should be stored as a dedicated column"""
        # Force column storage for these cases
        if (self.indexed or 
            self.storage_strategy == SchemaStorageStrategy.COLUMNAR or
            self.optimization_hints and SchemaOptimizationHint.INDEX_FREQUENTLY in self.optimization_hints):
            return True
        
        # Common metrics should be columns
        common_metrics = {
            'temperature', 'humidity', 'pressure', 'voltage', 
            'current', 'power', 'battery_level', 'signal_strength',
            'location_lat', 'location_lon', 'speed', 'acceleration',
            'co2', 'pm25', 'pm10', 'light_level', 'noise_level'
        }
        if self.name.lower() in common_metrics:
            return True
        
        # Numeric types with high access frequency
        if (self.field_type in [SchemaFieldType.INTEGER, SchemaFieldType.NUMBER, 
                               SchemaFieldType.FLOAT, SchemaFieldType.DOUBLE] and
            self.access_frequency > 0.3):
            return True
        
        # Frequently queried fields
        if self.access_frequency > 0.5:
            return True
        
        return False
    
    def get_sql_type(self) -> str:
        """Get appropriate PostgreSQL type for this field"""
        type_mapping = {
            SchemaFieldType.STRING: "TEXT",
            SchemaFieldType.INTEGER: "INTEGER",
            SchemaFieldType.NUMBER: "DOUBLE PRECISION",
            SchemaFieldType.FLOAT: "DOUBLE PRECISION",
            SchemaFieldType.DOUBLE: "DOUBLE PRECISION",
            SchemaFieldType.BOOLEAN: "BOOLEAN",
            SchemaFieldType.DATETIME: "TIMESTAMPTZ",
            SchemaFieldType.DATE: "DATE",
            SchemaFieldType.ARRAY: "JSONB",
            SchemaFieldType.OBJECT: "JSONB",
            SchemaFieldType.JSONB: "JSONB"
        }
        
        base_type = type_mapping.get(self.field_type, "JSONB")
        
        # Apply constraints to SQL type
        if (self.field_type == SchemaFieldType.STRING and 
            self.constraints and self.constraints.max_length and 
            self.constraints.max_length <= 255):
            base_type = f"VARCHAR({self.constraints.max_length})"
        
        # Add NOT NULL constraint if required
        if not self.nullable and self.constraints and self.constraints.required:
            base_type += " NOT NULL"
        
        # Add default value
        if self.default_value is not None:
            if isinstance(self.default_value, str):
                base_type += f" DEFAULT '{self.default_value}'"
            else:
                base_type += f" DEFAULT {self.default_value}"
        
        return base_type
    
    def validate_value(self, value: Any) -> tuple[bool, Optional[str]]:
        """Validate a value against this field definition"""
        if self.constraints:
            return self.constraints.validate(value)
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

@dataclass
class SchemaVersion:
    """Schema versioning information"""
    version: int
    created_at: datetime
    created_by: Optional[str] = None
    description: Optional[str] = None
    changes: List[str] = field(default_factory=list)
    backward_compatible: bool = True
    migration_sql: Optional[str] = None
    rollback_sql: Optional[str] = None

@dataclass  
class DeviceSchema:
    """Enhanced device schema definition with evolution capabilities"""
    schema_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_type: str = ""
    version: int = 1
    fields: Dict[str, SchemaField] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    description: Optional[str] = None
    
    # Evolution tracking
    schema_versions: List[SchemaVersion] = field(default_factory=list)
    parent_schema_id: Optional[str] = None
    
    # Performance and optimization
    estimated_data_points_per_day: int = 1000
    retention_days: int = 365
    compression_threshold_days: int = 7
    
    # Validation settings
    validation_level: SchemaValidationLevel = SchemaValidationLevel.STRICT
    allow_additional_fields: bool = True  # Allow fields not in schema
    
    # Table configuration
    table_name: Optional[str] = None
    hypertable_enabled: bool = True
    partitioning_column: str = "time"
    chunk_time_interval: str = "1 day"
    
    # Analytics configuration
    enable_real_time_analytics: bool = True
    enable_ml_features: bool = False
    feature_extraction_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.table_name:
            self.table_name = f"device_data_{self.device_type.lower().replace('-', '_').replace(' ', '_')}"
        
        # Initialize first version if none exist
        if not self.schema_versions:
            self.schema_versions.append(SchemaVersion(
                version=1,
                created_at=self.created_at,
                created_by=self.created_by,
                description="Initial schema version"
            ))
    
    def add_field(self, field: SchemaField) -> bool:
        """Add a new field to the schema"""
        if field.name in self.fields:
            return False
        
        self.fields[field.name] = field
        self.updated_at = datetime.utcnow()
        return True
    
    def remove_field(self, field_name: str) -> bool:
        """Remove a field from the schema (marks as deprecated)"""
        if field_name not in self.fields:
            return False
        
        # Don't actually remove - mark as deprecated for backward compatibility
        self.fields[field_name].metadata['deprecated'] = True
        self.fields[field_name].metadata['deprecated_at'] = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow()
        return True
    
    def update_field(self, field_name: str, updated_field: SchemaField) -> bool:
        """Update an existing field"""
        if field_name not in self.fields:
            return False
        
        self.fields[field_name] = updated_field
        self.updated_at = datetime.utcnow()
        return True
    
    def get_columnar_fields(self) -> Dict[str, SchemaField]:
        """Get fields that should be stored as columns"""
        return {name: field for name, field in self.fields.items() 
                if field.should_be_column() and not field.metadata.get('deprecated', False)}
    
    def get_jsonb_fields(self) -> Dict[str, SchemaField]:
        """Get fields that should be stored in JSONB"""
        return {name: field for name, field in self.fields.items() 
                if not field.should_be_column() and not field.metadata.get('deprecated', False)}
    
    def get_indexed_fields(self) -> List[str]:
        """Get fields that should have indexes"""
        indexed_fields = []
        for name, field in self.fields.items():
            if (field.indexed or 
                SchemaOptimizationHint.INDEX_FREQUENTLY in field.optimization_hints or
                field.access_frequency > 0.5):
                if not field.metadata.get('deprecated', False):
                    indexed_fields.append(name)
        return indexed_fields
    
    def validate_data(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate data against this schema"""
        errors = []
        
        if self.validation_level == SchemaValidationLevel.DISABLED:
            return True, []
        
        # Check required fields
        for field_name, field in self.fields.items():
            if field.metadata.get('deprecated', False):
                continue
                
            if field_name not in data:
                if field.constraints and field.constraints.required:
                    if self.validation_level == SchemaValidationLevel.STRICT:
                        errors.append(f"Required field '{field_name}' is missing")
                    # For LENIENT, we'll use default value if available
                    elif field.default_value is not None:
                        data[field_name] = field.default_value
            else:
                # Validate field value
                valid, error = field.validate_value(data[field_name])
                if not valid:
                    if self.validation_level == SchemaValidationLevel.STRICT:
                        errors.append(f"Field '{field_name}': {error}")
        
        # Check for unexpected fields
        if not self.allow_additional_fields:
            schema_fields = set(self.fields.keys())
            data_fields = set(data.keys())
            unexpected_fields = data_fields - schema_fields
            if unexpected_fields:
                if self.validation_level == SchemaValidationLevel.STRICT:
                    errors.append(f"Unexpected fields: {list(unexpected_fields)}")
        
        return len(errors) == 0, errors
    
    def create_new_version(self, changes: List[str], created_by: Optional[str] = None) -> int:
        """Create a new schema version"""
        new_version = max([v.version for v in self.schema_versions]) + 1
        
        version_info = SchemaVersion(
            version=new_version,
            created_at=datetime.utcnow(),
            created_by=created_by,
            description=f"Schema evolution v{new_version}",
            changes=changes
        )
        
        self.schema_versions.append(version_info)
        self.version = new_version
        self.updated_at = datetime.utcnow()
        
        return new_version
    
    def get_current_version(self) -> SchemaVersion:
        """Get the current schema version info"""
        return max(self.schema_versions, key=lambda v: v.version)
    
    def to_timescaledb_schema(self) -> Dict[str, Any]:
        """Convert to TimescaleDB schema format for evolution service"""
        schema_dict = {}
        
        for field_name, field in self.fields.items():
            if field.metadata.get('deprecated', False):
                continue
                
            schema_dict[field_name] = {
                'type': field.field_type.value,
                'indexed': field.indexed or field.access_frequency > 0.5,
                'nullable': field.nullable,
                'unit': field.unit,
                'description': field.description,
                'optimization_hints': [hint.value for hint in field.optimization_hints],
                'constraints': asdict(field.constraints) if field.constraints else None
            }
        
        return schema_dict
    
    def get_table_creation_metadata(self) -> Dict[str, Any]:
        """Get metadata for table creation"""
        return {
            'schema_id': self.schema_id,
            'device_type': self.device_type,
            'version': self.version,
            'table_name': self.table_name,
            'hypertable_enabled': self.hypertable_enabled,
            'partitioning_column': self.partitioning_column,
            'chunk_time_interval': self.chunk_time_interval,
            'estimated_data_points_per_day': self.estimated_data_points_per_day,
            'retention_days': self.retention_days,
            'compression_threshold_days': self.compression_threshold_days,
            'enable_real_time_analytics': self.enable_real_time_analytics,
            'field_count': len([f for f in self.fields.values() if not f.metadata.get('deprecated', False)]),
            'columnar_fields': len(self.get_columnar_fields()),
            'jsonb_fields': len(self.get_jsonb_fields()),
            'indexed_fields': len(self.get_indexed_fields())
        }
    
    def calculate_schema_hash(self) -> str:
        """Calculate hash of current schema for change detection"""
        # Create a normalized representation of the schema
        schema_data = {
            'device_type': self.device_type,
            'fields': {
                name: {
                    'type': field.field_type.value,
                    'indexed': field.indexed,
                    'nullable': field.nullable,
                    'constraints': asdict(field.constraints) if field.constraints else None
                }
                for name, field in self.fields.items()
                if not field.metadata.get('deprecated', False)
            }
        }
        
        # Sort keys for consistent hashing
        schema_json = json.dumps(schema_data, sort_keys=True)
        return hashlib.sha256(schema_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        
        # Convert datetime objects to ISO strings
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        
        # Convert schema versions
        result['schema_versions'] = [
            {
                **asdict(version),
                'created_at': version.created_at.isoformat()
            }
            for version in self.schema_versions
        ]
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceSchema':
        """Create DeviceSchema from dictionary"""
        # Convert string dates back to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert fields
        if 'fields' in data:
            fields = {}
            for field_name, field_data in data['fields'].items():
                if isinstance(field_data, dict):
                    # Reconstruct SchemaField objects
                    field_data['field_type'] = SchemaFieldType(field_data['field_type'])
                    if 'constraints' in field_data and field_data['constraints']:
                        field_data['constraints'] = SchemaFieldConstraint(**field_data['constraints'])
                    if 'optimization_hints' in field_data:
                        field_data['optimization_hints'] = [
                            SchemaOptimizationHint(hint) for hint in field_data['optimization_hints']
                        ]
                    if 'storage_strategy' in field_data:
                        field_data['storage_strategy'] = SchemaStorageStrategy(field_data['storage_strategy'])
                    
                    fields[field_name] = SchemaField(**field_data)
                else:
                    # Legacy format - simple field definition
                    fields[field_name] = SchemaField(
                        name=field_name,
                        field_type=SchemaFieldType(field_data.get('type', 'string')),
                        indexed=field_data.get('indexed', False)
                    )
            data['fields'] = fields
        
        # Convert schema versions
        if 'schema_versions' in data:
            versions = []
            for version_data in data['schema_versions']:
                if isinstance(version_data.get('created_at'), str):
                    version_data['created_at'] = datetime.fromisoformat(version_data['created_at'])
                versions.append(SchemaVersion(**version_data))
            data['schema_versions'] = versions
        
        return cls(**data)

# Predefined schema templates
class SchemaTemplates:
    """Pre-defined schema templates for common device types"""
    
    @staticmethod
    def environmental_sensor() -> DeviceSchema:
        """Schema for environmental sensors"""
        schema = DeviceSchema(
            device_type="environmental_sensor",
            description="Standard environmental monitoring sensor"
        )
        
        # Common environmental fields
        schema.add_field(SchemaField(
            name="temperature",
            field_type=SchemaFieldType.DOUBLE,
            description="Ambient temperature",
            unit="celsius",
            indexed=True,
            constraints=SchemaFieldConstraint(min_value=-50, max_value=85),
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY, SchemaOptimizationHint.RANGE_QUERIES]
        ))
        
        schema.add_field(SchemaField(
            name="humidity",
            field_type=SchemaFieldType.DOUBLE,
            description="Relative humidity",
            unit="percent",
            indexed=True,
            constraints=SchemaFieldConstraint(min_value=0, max_value=100),
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY, SchemaOptimizationHint.RANGE_QUERIES]
        ))
        
        schema.add_field(SchemaField(
            name="pressure",
            field_type=SchemaFieldType.DOUBLE,
            description="Atmospheric pressure",
            unit="hPa",
            indexed=False,
            constraints=SchemaFieldConstraint(min_value=300, max_value=1200)
        ))
        
        schema.add_field(SchemaField(
            name="battery_level",
            field_type=SchemaFieldType.INTEGER,
            description="Battery level percentage",
            unit="percent",
            indexed=True,
            constraints=SchemaFieldConstraint(min_value=0, max_value=100),
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY]
        ))
        
        return schema
    
    @staticmethod
    def industrial_iot() -> DeviceSchema:
        """Schema for industrial IoT devices"""
        schema = DeviceSchema(
            device_type="industrial_iot",
            description="Industrial IoT monitoring device",
            retention_days=1095,  # 3 years
            estimated_data_points_per_day=8640  # Every 10 seconds
        )
        
        # Industrial metrics
        schema.add_field(SchemaField(
            name="vibration_x",
            field_type=SchemaFieldType.DOUBLE,
            description="Vibration in X axis",
            unit="m/s²",
            indexed=True,
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY, SchemaOptimizationHint.RANGE_QUERIES]
        ))
        
        schema.add_field(SchemaField(
            name="vibration_y", 
            field_type=SchemaFieldType.DOUBLE,
            description="Vibration in Y axis",
            unit="m/s²",
            indexed=True
        ))
        
        schema.add_field(SchemaField(
            name="vibration_z",
            field_type=SchemaFieldType.DOUBLE, 
            description="Vibration in Z axis",
            unit="m/s²",
            indexed=True
        ))
        
        schema.add_field(SchemaField(
            name="rpm",
            field_type=SchemaFieldType.INTEGER,
            description="Rotations per minute",
            unit="rpm",
            indexed=True,
            constraints=SchemaFieldConstraint(min_value=0, max_value=50000),
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY]
        ))
        
        schema.add_field(SchemaField(
            name="temperature",
            field_type=SchemaFieldType.DOUBLE,
            description="Operating temperature",
            unit="celsius",
            indexed=True,
            constraints=SchemaFieldConstraint(min_value=-40, max_value=150)
        ))
        
        return schema
    
    @staticmethod
    def wearable_device() -> DeviceSchema:
        """Schema for wearable devices"""
        schema = DeviceSchema(
            device_type="wearable",
            description="Wearable health monitoring device",
            enable_ml_features=True,
            validation_level=SchemaValidationLevel.LENIENT
        )
        
        # Health metrics
        schema.add_field(SchemaField(
            name="heart_rate",
            field_type=SchemaFieldType.INTEGER,
            description="Heart rate in beats per minute",
            unit="bpm",
            indexed=True,
            is_feature=True,
            constraints=SchemaFieldConstraint(min_value=30, max_value=250),
            optimization_hints=[SchemaOptimizationHint.INDEX_FREQUENTLY],
            privacy_level="private"
        ))
        
        schema.add_field(SchemaField(
            name="step_count",
            field_type=SchemaFieldType.INTEGER,
            description="Number of steps taken",
            unit="steps",
            indexed=True,
            is_feature=True,
            constraints=SchemaFieldConstraint(min_value=0, max_value=100000)
        ))
        
        schema.add_field(SchemaField(
            name="spo2",
            field_type=SchemaFieldType.INTEGER,
            description="Blood oxygen saturation",
            unit="percent",
            indexed=True,
            is_feature=True,
            constraints=SchemaFieldConstraint(min_value=70, max_value=100),
            privacy_level="sensitive"
        ))
        
        schema.add_field(SchemaField(
            name="activity_type",
            field_type=SchemaFieldType.STRING,
            description="Current activity type",
            indexed=True,
            constraints=SchemaFieldConstraint(
                enum_values=["resting", "walking", "running", "cycling", "swimming", "other"]
            ),
            optimization_hints=[SchemaOptimizationHint.EXACT_MATCH]
        ))
        
        return schema

# Schema registry for managing templates
class DeviceSchemaRegistry:
    """Registry for managing device schemas and templates"""
    
    def __init__(self):
        self._schemas: Dict[str, DeviceSchema] = {}
        self._templates: Dict[str, callable] = {
            'environmental_sensor': SchemaTemplates.environmental_sensor,
            'industrial_iot': SchemaTemplates.industrial_iot, 
            'wearable': SchemaTemplates.wearable_device
        }
    
    def register_schema(self, schema: DeviceSchema):
        """Register a schema in the registry"""
        self._schemas[schema.device_type] = schema
    
    def get_schema(self, device_type: str) -> Optional[DeviceSchema]:
        """Get schema for device type"""
        return self._schemas.get(device_type)
    
    def get_template(self, template_name: str) -> Optional[DeviceSchema]:
        """Get schema template by name"""
        if template_name in self._templates:
            return self._templates[template_name]()
        return None
    
    def list_templates(self) -> List[str]:
        """List available schema templates"""
        return list(self._templates.keys())
    
    def list_schemas(self) -> List[str]:
        """List registered device types"""
        return list(self._schemas.keys())

# Global registry instance
device_schema_registry = DeviceSchemaRegistry()