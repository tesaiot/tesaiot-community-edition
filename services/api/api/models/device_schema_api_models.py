# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Schema API Models
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Request/Response models for Device Schema API endpoints.
These models define the structure for API communication and validation.
"""

from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field

# API Request Models

@dataclass
class SchemaFieldConstraintRequest:
    """Request model for schema field constraints"""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    enum_values: Optional[List[Any]] = None
    required: bool = True
    unique: bool = False

@dataclass
class SchemaFieldRequest:
    """Request model for schema field definition"""
    field_type: str  # SchemaFieldType enum value
    description: Optional[str] = None
    unit: Optional[str] = None
    indexed: bool = False
    nullable: bool = True
    default_value: Optional[Any] = None
    constraints: Optional[SchemaFieldConstraintRequest] = None
    optimization_hints: List[str] = field(default_factory=list)  # SchemaOptimizationHint enum values
    storage_strategy: str = "hybrid"  # SchemaStorageStrategy enum value
    privacy_level: str = "public"  # public, private, sensitive, pii
    is_feature: bool = False  # Used in ML feature extraction
    is_target: bool = False   # ML prediction target

@dataclass
class DeviceSchemaCreateRequest:
    """Request model for creating a new device schema"""
    device_type: str
    fields: Dict[str, SchemaFieldRequest]
    description: Optional[str] = None
    validation_level: str = "strict"  # SchemaValidationLevel enum value
    allow_additional_fields: bool = True
    estimated_data_points_per_day: int = 1000
    retention_days: int = 365
    compression_threshold_days: int = 7
    enable_real_time_analytics: bool = True
    enable_ml_features: bool = False

@dataclass
class DeviceSchemaUpdateRequest:
    """Request model for updating a device schema"""
    description: Optional[str] = None
    fields: Optional[Dict[str, SchemaFieldRequest]] = None
    validation_level: Optional[str] = None
    allow_additional_fields: Optional[bool] = None
    estimated_data_points_per_day: Optional[int] = None
    retention_days: Optional[int] = None
    compression_threshold_days: Optional[int] = None
    enable_real_time_analytics: Optional[bool] = None
    enable_ml_features: Optional[bool] = None
    changes: Optional[List[str]] = None  # Description of changes for versioning

@dataclass
class SchemaValidationRequest:
    """Request model for data validation against schema"""
    data: Dict[str, Any]
    validation_level: Optional[str] = None  # Override schema validation level

@dataclass
class SchemaFromTemplateRequest:
    """Request model for creating schema from template"""
    device_type: str
    description: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None

# API Response Models

@dataclass
class SchemaFieldConstraintResponse:
    """Response model for schema field constraints"""
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    required: bool = True
    unique: bool = False

@dataclass
class SchemaFieldResponse:
    """Response model for schema field"""
    name: str
    field_type: str
    description: Optional[str] = None
    unit: Optional[str] = None
    indexed: bool = False
    nullable: bool = True
    default_value: Optional[Any] = None
    constraints: Optional[SchemaFieldConstraintResponse] = None
    optimization_hints: List[str] = field(default_factory=list)
    storage_strategy: str = "hybrid"
    privacy_level: str = "public"
    is_feature: bool = False
    is_target: bool = False
    access_frequency: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SchemaVersionResponse:
    """Response model for schema version information"""
    version: int
    created_at: str  # ISO format datetime
    created_by: Optional[str] = None
    description: Optional[str] = None
    changes: List[str] = field(default_factory=list)
    backward_compatible: bool = True

@dataclass
class DeviceSchemaResponse:
    """Response model for device schema"""
    schema_id: str
    device_type: str
    version: int
    description: Optional[str] = None
    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime
    created_by: Optional[str] = None
    fields: Dict[str, SchemaFieldResponse] = field(default_factory=dict)
    validation_level: str = "strict"
    allow_additional_fields: bool = True
    table_name: Optional[str] = None
    hypertable_enabled: bool = True
    estimated_data_points_per_day: int = 1000
    retention_days: int = 365
    compression_threshold_days: int = 7
    enable_real_time_analytics: bool = True
    enable_ml_features: bool = False
    schema_hash: Optional[str] = None
    schema_versions: List[SchemaVersionResponse] = field(default_factory=list)
    is_template: bool = False
    created_from_template: Optional[str] = None

@dataclass
class DeviceSchemaListResponse:
    """Response model for listing device schemas"""
    schemas: List[DeviceSchemaResponse]
    templates: Optional[List[DeviceSchemaResponse]] = None
    total: int = 0
    limit: int = 50
    offset: int = 0

@dataclass
class SchemaValidationFieldResult:
    """Response model for individual field validation"""
    valid: bool
    error: Optional[str] = None
    type_expected: Optional[str] = None
    type_received: Optional[str] = None
    unexpected: bool = False

@dataclass
class SchemaValidationResponse:
    """Response model for data validation result"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    validation_level: str = "strict"
    field_count: int = 0
    schema_version: int = 1
    timestamp: str = ""  # ISO format datetime
    field_validation: Dict[str, SchemaValidationFieldResult] = field(default_factory=dict)

@dataclass
class TableColumnResponse:
    """Response model for table column definition"""
    name: str
    type: str
    nullable: bool = True
    indexed: bool = False
    description: Optional[str] = None
    unit: Optional[str] = None

@dataclass
class TableIndexResponse:
    """Response model for table index definition"""
    field: str
    type: str = "B-tree"

@dataclass
class EstimatedSizeResponse:
    """Response model for estimated storage size"""
    daily_rows: int
    daily_size_mb: float
    monthly_size_gb: float

@dataclass
class SchemaTablePreviewResponse:
    """Response model for schema table preview"""
    table_name: str
    columns: List[TableColumnResponse]
    indexes: List[TableIndexResponse]
    hypertable_enabled: bool
    chunk_time_interval: str
    retention_days: int
    sql_preview: List[str]
    estimated_size: EstimatedSizeResponse

@dataclass
class SchemaTemplateListResponse:
    """Response model for listing schema templates"""
    templates: List[DeviceSchemaResponse]
    total: int = 0

@dataclass
class TableMetadataResponse:
    """Response model for table creation metadata"""
    schema_id: str
    device_type: str
    version: int
    table_name: str
    hypertable_enabled: bool
    partitioning_column: str
    chunk_time_interval: str
    estimated_data_points_per_day: int
    retention_days: int
    compression_threshold_days: int
    enable_real_time_analytics: bool
    field_count: int
    columnar_fields: int
    jsonb_fields: int
    indexed_fields: int

# Error Response Models

@dataclass
class ApiErrorResponse:
    """Standard error response model"""
    error: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class ValidationErrorResponse:
    """Validation error response model"""
    error: str
    field_errors: Optional[Dict[str, List[str]]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

# Utility Functions for Model Conversion

def dict_to_schema_field_request(data: Dict[str, Any]) -> SchemaFieldRequest:
    """Convert dictionary to SchemaFieldRequest"""
    constraints = None
    if "constraints" in data and data["constraints"]:
        constraints = SchemaFieldConstraintRequest(**data["constraints"])
    
    return SchemaFieldRequest(
        field_type=data["field_type"],
        description=data.get("description"),
        unit=data.get("unit"),
        indexed=data.get("indexed", False),
        nullable=data.get("nullable", True),
        default_value=data.get("default_value"),
        constraints=constraints,
        optimization_hints=data.get("optimization_hints", []),
        storage_strategy=data.get("storage_strategy", "hybrid"),
        privacy_level=data.get("privacy_level", "public"),
        is_feature=data.get("is_feature", False),
        is_target=data.get("is_target", False)
    )

def dict_to_device_schema_create_request(data: Dict[str, Any]) -> DeviceSchemaCreateRequest:
    """Convert dictionary to DeviceSchemaCreateRequest"""
    fields = {}
    if "fields" in data:
        for field_name, field_data in data["fields"].items():
            fields[field_name] = dict_to_schema_field_request(field_data)
    
    return DeviceSchemaCreateRequest(
        device_type=data["device_type"],
        fields=fields,
        description=data.get("description"),
        validation_level=data.get("validation_level", "strict"),
        allow_additional_fields=data.get("allow_additional_fields", True),
        estimated_data_points_per_day=data.get("estimated_data_points_per_day", 1000),
        retention_days=data.get("retention_days", 365),
        compression_threshold_days=data.get("compression_threshold_days", 7),
        enable_real_time_analytics=data.get("enable_real_time_analytics", True),
        enable_ml_features=data.get("enable_ml_features", False)
    )

def dict_to_device_schema_update_request(data: Dict[str, Any]) -> DeviceSchemaUpdateRequest:
    """Convert dictionary to DeviceSchemaUpdateRequest"""
    fields = None
    if "fields" in data:
        fields = {}
        for field_name, field_data in data["fields"].items():
            fields[field_name] = dict_to_schema_field_request(field_data)
    
    return DeviceSchemaUpdateRequest(
        description=data.get("description"),
        fields=fields,
        validation_level=data.get("validation_level"),
        allow_additional_fields=data.get("allow_additional_fields"),
        estimated_data_points_per_day=data.get("estimated_data_points_per_day"),
        retention_days=data.get("retention_days"),
        compression_threshold_days=data.get("compression_threshold_days"),
        enable_real_time_analytics=data.get("enable_real_time_analytics"),
        enable_ml_features=data.get("enable_ml_features"),
        changes=data.get("changes")
    )

# OpenAPI/Swagger Schema Definitions
# These can be used with Flask-RESTX or similar libraries for automatic documentation

OPENAPI_SCHEMAS = {
    "SchemaFieldConstraint": {
        "type": "object",
        "properties": {
            "min_value": {"type": "number"},
            "max_value": {"type": "number"},
            "min_length": {"type": "integer"},
            "max_length": {"type": "integer"},
            "pattern": {"type": "string", "description": "Regular expression pattern"},
            "enum_values": {"type": "array", "items": {}},
            "required": {"type": "boolean"},
            "unique": {"type": "boolean"}
        }
    },
    "SchemaField": {
        "type": "object",
        "required": ["field_type"],
        "properties": {
            "field_type": {
                "type": "string",
                "enum": ["string", "integer", "number", "float", "double", "boolean", "datetime", "date", "array", "object", "jsonb"]
            },
            "description": {"type": "string"},
            "unit": {"type": "string"},
            "indexed": {"type": "boolean"},
            "nullable": {"type": "boolean"},
            "default_value": {},
            "constraints": {"$ref": "#/components/schemas/SchemaFieldConstraint"},
            "optimization_hints": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["index_frequently", "index_rarely", "full_text_search", "range_queries", "exact_match", "aggregate", "time_series"]
                }
            },
            "storage_strategy": {
                "type": "string",
                "enum": ["columnar", "jsonb", "hybrid"]
            },
            "privacy_level": {
                "type": "string",
                "enum": ["public", "private", "sensitive", "pii"]
            },
            "is_feature": {"type": "boolean"},
            "is_target": {"type": "boolean"}
        }
    },
    "DeviceSchemaCreate": {
        "type": "object",
        "required": ["device_type", "fields"],
        "properties": {
            "device_type": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
            "description": {"type": "string"},
            "fields": {
                "type": "object",
                "additionalProperties": {"$ref": "#/components/schemas/SchemaField"}
            },
            "validation_level": {
                "type": "string",
                "enum": ["strict", "lenient", "disabled"]
            },
            "allow_additional_fields": {"type": "boolean"},
            "estimated_data_points_per_day": {"type": "integer", "minimum": 1},
            "retention_days": {"type": "integer", "minimum": 1},
            "compression_threshold_days": {"type": "integer", "minimum": 0},
            "enable_real_time_analytics": {"type": "boolean"},
            "enable_ml_features": {"type": "boolean"}
        }
    },
    "DeviceSchema": {
        "type": "object",
        "properties": {
            "schema_id": {"type": "string", "format": "uuid"},
            "device_type": {"type": "string"},
            "version": {"type": "integer"},
            "description": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"},
            "created_by": {"type": "string"},
            "fields": {
                "type": "object",
                "additionalProperties": {"$ref": "#/components/schemas/SchemaField"}
            },
            "validation_level": {"type": "string", "enum": ["strict", "lenient", "disabled"]},
            "allow_additional_fields": {"type": "boolean"},
            "table_name": {"type": "string"},
            "hypertable_enabled": {"type": "boolean"},
            "estimated_data_points_per_day": {"type": "integer"},
            "retention_days": {"type": "integer"},
            "compression_threshold_days": {"type": "integer"},
            "enable_real_time_analytics": {"type": "boolean"},
            "enable_ml_features": {"type": "boolean"},
            "schema_hash": {"type": "string"},
            "schema_versions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "version": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                        "created_by": {"type": "string"},
                        "description": {"type": "string"},
                        "changes": {"type": "array", "items": {"type": "string"}},
                        "backward_compatible": {"type": "boolean"}
                    }
                }
            }
        }
    },
    "ValidationRequest": {
        "type": "object",
        "required": ["data"],
        "properties": {
            "data": {"type": "object"},
            "validation_level": {
                "type": "string",
                "enum": ["strict", "lenient", "disabled"]
            }
        }
    },
    "ValidationResponse": {
        "type": "object",
        "properties": {
            "valid": {"type": "boolean"},
            "errors": {"type": "array", "items": {"type": "string"}},
            "validation_level": {"type": "string"},
            "field_count": {"type": "integer"},
            "schema_version": {"type": "integer"},
            "timestamp": {"type": "string", "format": "date-time"},
            "field_validation": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "valid": {"type": "boolean"},
                        "error": {"type": "string"},
                        "type_expected": {"type": "string"},
                        "type_received": {"type": "string"},
                        "unexpected": {"type": "boolean"}
                    }
                }
            }
        }
    },
    "Error": {
        "type": "object",
        "properties": {
            "error": {"type": "string"},
            "details": {"type": "object"},
            "timestamp": {"type": "string", "format": "date-time"}
        }
    }
}

# Example request/response payloads for documentation
EXAMPLE_REQUESTS = {
    "create_environmental_sensor": {
        "device_type": "environmental_sensor_v2",
        "description": "Enhanced environmental sensor with air quality monitoring",
        "validation_level": "strict",
        "allow_additional_fields": False,
        "estimated_data_points_per_day": 2880,  # Every 30 seconds
        "retention_days": 730,  # 2 years
        "enable_real_time_analytics": True,
        "enable_ml_features": True,
        "fields": {
            "temperature": {
                "field_type": "double",
                "description": "Ambient temperature",
                "unit": "celsius",
                "indexed": True,
                "nullable": False,
                "constraints": {
                    "min_value": -50,
                    "max_value": 85,
                    "required": True
                },
                "optimization_hints": ["index_frequently", "range_queries"],
                "is_feature": True
            },
            "humidity": {
                "field_type": "double", 
                "description": "Relative humidity",
                "unit": "percent",
                "indexed": True,
                "constraints": {
                    "min_value": 0,
                    "max_value": 100,
                    "required": True
                },
                "optimization_hints": ["index_frequently", "range_queries"],
                "is_feature": True
            },
            "co2_level": {
                "field_type": "integer",
                "description": "CO2 concentration",
                "unit": "ppm",
                "indexed": True,
                "constraints": {
                    "min_value": 300,
                    "max_value": 5000,
                    "required": False
                },
                "optimization_hints": ["index_frequently"]
            },
            "air_quality_index": {
                "field_type": "string",
                "description": "Air quality category",
                "indexed": True,
                "constraints": {
                    "enum_values": ["good", "moderate", "unhealthy_sensitive", "unhealthy", "very_unhealthy", "hazardous"],
                    "required": False
                },
                "optimization_hints": ["exact_match"]
            },
            "battery_level": {
                "field_type": "integer",
                "description": "Battery level percentage", 
                "unit": "percent",
                "indexed": False,
                "constraints": {
                    "min_value": 0,
                    "max_value": 100
                }
            }
        }
    },
    "validate_data": {
        "data": {
            "temperature": 23.5,
            "humidity": 65.2,
            "co2_level": 420,
            "air_quality_index": "good",
            "battery_level": 85,
            "additional_sensor": "unexpected_value"
        },
        "validation_level": "strict"
    },
    "create_from_template": {
        "device_type": "my_environmental_sensor",
        "description": "Custom environmental sensor based on template",
        "customizations": {
            "retention_days": 1095,
            "estimated_data_points_per_day": 8640,
            "fields": {
                "temperature": {
                    "constraints": {
                        "min_value": -10,
                        "max_value": 50
                    }
                }
            }
        }
    }
}

EXAMPLE_RESPONSES = {
    "device_schema": {
        "schema_id": "550e8400-e29b-41d4-a716-446655440000",
        "device_type": "environmental_sensor_v2", 
        "version": 1,
        "description": "Enhanced environmental sensor with air quality monitoring",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "created_by": "user123",
        "fields": {
            "temperature": {
                "name": "temperature",
                "field_type": "double",
                "description": "Ambient temperature",
                "unit": "celsius",
                "indexed": True,
                "nullable": False,
                "constraints": {
                    "min_value": -50,
                    "max_value": 85,
                    "required": True
                },
                "optimization_hints": ["index_frequently", "range_queries"],
                "storage_strategy": "columnar",
                "is_feature": True
            }
        },
        "validation_level": "strict",
        "table_name": "device_data_environmental_sensor_v2",
        "schema_hash": "abc123def456",
        "schema_versions": [
            {
                "version": 1,
                "created_at": "2024-01-15T10:30:00Z",
                "created_by": "user123",
                "description": "Initial schema version",
                "changes": [],
                "backward_compatible": True
            }
        ]
    },
    "validation_result": {
        "valid": False,
        "errors": ["Field 'additional_sensor': Field not defined in schema"],
        "validation_level": "strict",
        "field_count": 6,
        "schema_version": 1,
        "timestamp": "2024-01-15T10:35:00Z",
        "field_validation": {
            "temperature": {
                "valid": True,
                "type_expected": "double",
                "type_received": "float"
            },
            "additional_sensor": {
                "valid": False,
                "error": "Field not defined in schema",
                "unexpected": True
            }
        }
    }
}