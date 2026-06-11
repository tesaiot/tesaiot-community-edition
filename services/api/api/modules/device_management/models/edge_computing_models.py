# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Edge computing models for Device Management module.

This module defines data models for edge computing capabilities including:
- Edge node models
- Edge deployment configurations
- Edge function definitions
- Data processing pipelines
- Edge-cloud synchronization models
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class EdgeNodeStatus(Enum):
    """Edge node status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    PROVISIONING = "provisioning"
    ERROR = "error"


class EdgeNodeType(Enum):
    """Edge node type enumeration"""
    GATEWAY = "gateway"
    FOG_NODE = "fog_node"
    MEC_SERVER = "mec_server"  # Multi-access Edge Computing
    EDGE_SERVER = "edge_server"
    MICRO_DATACENTER = "micro_datacenter"


class EdgeFunctionType(Enum):
    """Edge function type enumeration"""
    DATA_FILTER = "data_filter"
    DATA_AGGREGATION = "data_aggregation"
    DATA_TRANSFORMATION = "data_transformation"
    ANALYTICS = "analytics"
    MACHINE_LEARNING = "machine_learning"
    RULE_ENGINE = "rule_engine"
    PROTOCOL_TRANSLATION = "protocol_translation"


class SyncStrategy(Enum):
    """Edge-cloud synchronization strategy"""
    REAL_TIME = "real_time"
    BATCH = "batch"
    PERIODIC = "periodic"
    EVENT_DRIVEN = "event_driven"
    ON_DEMAND = "on_demand"
    DIFFERENTIAL = "differential"


class DeploymentStatus(Enum):
    """Edge deployment status"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    UPDATING = "updating"
    REMOVING = "removing"


@dataclass
class EdgeNode:
    """Edge node model representing a computing node at the edge"""
    node_id: str
    org_id: str
    name: str
    node_type: EdgeNodeType
    status: EdgeNodeStatus
    location: Dict[str, Any]  # Geographic location, zone, region
    capabilities: Dict[str, Any] = field(default_factory=dict)
    resources: 'EdgeResources' = None
    connected_devices: List[str] = field(default_factory=list)
    deployed_functions: List[str] = field(default_factory=list)
    parent_node_id: Optional[str] = None  # For hierarchical edge architectures
    child_node_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    version: str = "1.0.0"
    security_config: Optional['EdgeSecurityConfig'] = None


@dataclass
class EdgeResources:
    """Edge node resource specifications"""
    cpu_cores: int
    memory_gb: float
    storage_gb: float
    gpu_available: bool = False
    gpu_memory_gb: float = 0.0
    network_bandwidth_mbps: float = 100.0
    max_concurrent_functions: int = 10
    current_cpu_usage: float = 0.0
    current_memory_usage: float = 0.0
    current_storage_usage: float = 0.0


@dataclass
class EdgeFunction:
    """Edge function definition for deployment"""
    function_id: str
    org_id: str
    name: str
    function_type: EdgeFunctionType
    runtime: str  # e.g., "python3.9", "nodejs16", "wasm"
    handler: str  # Entry point for the function
    code: Optional[str] = None  # Base64 encoded or reference
    code_url: Optional[str] = None  # URL to download code
    dependencies: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    resource_requirements: 'FunctionResources' = None
    triggers: List['FunctionTrigger'] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    timeout_seconds: int = 300
    max_retries: int = 3
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


@dataclass
class FunctionResources:
    """Resource requirements for edge functions"""
    min_cpu_cores: float = 0.1
    max_cpu_cores: float = 1.0
    min_memory_mb: int = 128
    max_memory_mb: int = 512
    ephemeral_storage_mb: int = 512
    gpu_required: bool = False
    gpu_memory_mb: int = 0


@dataclass
class FunctionTrigger:
    """Trigger configuration for edge functions"""
    trigger_type: str  # "event", "schedule", "data", "http"
    source: str  # Device ID, topic, endpoint
    conditions: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # Cron expression for scheduled triggers


@dataclass
class EdgeDeployment:
    """Edge deployment configuration"""
    deployment_id: str
    org_id: str
    function_id: str
    target_nodes: List[str]  # List of edge node IDs
    status: DeploymentStatus
    deployment_strategy: str  # "rolling", "blue_green", "canary"
    replicas: int = 1
    auto_scaling: Optional['AutoScalingConfig'] = None
    placement_constraints: Dict[str, Any] = field(default_factory=dict)
    health_check: Optional['HealthCheckConfig'] = None
    rollback_on_failure: bool = True
    deployment_timestamp: datetime = field(default_factory=datetime.utcnow)
    completed_timestamp: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class AutoScalingConfig:
    """Auto-scaling configuration for edge deployments"""
    enabled: bool = False
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_utilization: float = 70.0
    target_memory_utilization: float = 80.0
    scale_up_threshold: float = 80.0
    scale_down_threshold: float = 20.0
    cool_down_period_seconds: int = 300


@dataclass
class HealthCheckConfig:
    """Health check configuration for deployed functions"""
    enabled: bool = True
    endpoint: str = "/health"
    interval_seconds: int = 30
    timeout_seconds: int = 10
    success_threshold: int = 1
    failure_threshold: int = 3


@dataclass
class DataProcessingPipeline:
    """Data processing pipeline configuration"""
    pipeline_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    stages: List['PipelineStage'] = field(default_factory=list)
    input_sources: List[str] = field(default_factory=list)  # Device IDs or topics
    output_destinations: List[str] = field(default_factory=list)
    error_handling: str = "continue"  # "continue", "stop", "retry"
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


@dataclass
class PipelineStage:
    """Individual stage in a data processing pipeline"""
    stage_id: str
    name: str
    function_id: str  # Edge function to execute
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    filters: List[Dict[str, Any]] = field(default_factory=list)
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    parallel_execution: bool = False
    timeout_seconds: int = 60
    retry_count: int = 3


@dataclass
class EdgeCloudSync:
    """Edge-cloud synchronization configuration"""
    sync_id: str
    org_id: str
    edge_node_id: str
    sync_strategy: SyncStrategy
    data_types: List[str] = field(default_factory=list)  # Types of data to sync
    sync_interval_seconds: Optional[int] = None  # For periodic sync
    batch_size: int = 1000
    compression_enabled: bool = True
    encryption_enabled: bool = True
    conflict_resolution: str = "last_write_wins"  # "last_write_wins", "merge", "manual"
    filters: Dict[str, Any] = field(default_factory=dict)
    last_sync_timestamp: Optional[datetime] = None
    next_sync_timestamp: Optional[datetime] = None
    sync_status: str = "idle"  # "idle", "syncing", "failed"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EdgeSecurityConfig:
    """Security configuration for edge nodes"""
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    tls_enabled: bool = True
    tls_version: str = "1.3"
    certificate_path: Optional[str] = None
    private_key_path: Optional[str] = None
    ca_certificate_path: Optional[str] = None
    api_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    allowed_ips: List[str] = field(default_factory=list)
    firewall_rules: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class EdgeAnalytics:
    """Edge analytics configuration and results"""
    analytics_id: str
    org_id: str
    edge_node_id: str
    analytics_type: str  # "real_time", "batch", "streaming"
    metrics: Dict[str, Any] = field(default_factory=dict)
    aggregations: List['AggregationConfig'] = field(default_factory=list)
    time_window_seconds: int = 300
    retention_days: int = 7
    output_format: str = "json"  # "json", "parquet", "csv"
    destinations: List[str] = field(default_factory=list)
    enabled: bool = True
    last_run_timestamp: Optional[datetime] = None
    next_run_timestamp: Optional[datetime] = None


@dataclass
class AggregationConfig:
    """Configuration for data aggregation at the edge"""
    field_name: str
    aggregation_type: str  # "sum", "avg", "min", "max", "count", "percentile"
    group_by: List[str] = field(default_factory=list)
    time_bucket: Optional[str] = None  # "1m", "5m", "1h", etc.
    percentile_value: Optional[float] = None  # For percentile aggregations


@dataclass
class EdgeEvent:
    """Event model for edge computing events"""
    event_id: str
    event_type: str  # "deployment", "sync", "error", "health", "data"
    source_id: str  # Node ID or Function ID
    timestamp: datetime
    severity: str  # "info", "warning", "error", "critical"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    org_id: str = ""


@dataclass
class EdgeMetrics:
    """Metrics collected from edge nodes"""
    node_id: str
    timestamp: datetime
    cpu_usage_percent: float
    memory_usage_percent: float
    storage_usage_percent: float
    network_in_mbps: float
    network_out_mbps: float
    active_functions: int
    processed_messages: int
    error_count: int
    latency_ms: float
    custom_metrics: Dict[str, float] = field(default_factory=dict)