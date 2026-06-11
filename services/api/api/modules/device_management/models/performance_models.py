# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Performance Models for Device Management Module

This module defines data models for performance monitoring, optimization,
and caching strategies.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from dataclasses import dataclass, field


class PerformanceMetricType(str, Enum):
    """Types of performance metrics tracked"""
    RESPONSE_TIME = "response_time"
    QUERY_TIME = "query_time"
    CACHE_HIT_RATE = "cache_hit_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    CONNECTION_POOL_USAGE = "connection_pool_usage"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_SIZE = "queue_size"
    BATCH_PROCESSING_TIME = "batch_processing_time"


class OptimizationStrategy(str, Enum):
    """Optimization strategies available"""
    QUERY_OPTIMIZATION = "query_optimization"
    CACHE_WARMING = "cache_warming"
    CONNECTION_POOLING = "connection_pooling"
    BATCH_PROCESSING = "batch_processing"
    MEMORY_OPTIMIZATION = "memory_optimization"
    INDEX_OPTIMIZATION = "index_optimization"
    ASYNC_PROCESSING = "async_processing"


class CacheStrategy(str, Enum):
    """Cache strategies for different data types"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    REFRESH_AHEAD = "refresh_ahead"


class AlertSeverity(str, Enum):
    """Performance alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric measurement"""
    metric_type: PerformanceMetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "unit": self.unit,
            "tags": self.tags,
            "metadata": self.metadata
        }


class QueryOptimizationModel(BaseModel):
    """Model for query optimization configurations"""
    model_config = ConfigDict(validate_assignment=True)

    query_pattern: str = Field(..., description="Query pattern to optimize")
    optimization_hints: List[str] = Field(default_factory=list)
    index_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    execution_plan: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    optimization_applied: bool = False
    performance_gain: Optional[float] = None
    
    # Query statistics
    avg_execution_time: Optional[float] = None
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    
    # Resource usage
    avg_documents_scanned: Optional[int] = None
    avg_documents_returned: Optional[int] = None
    index_hit_ratio: Optional[float] = None


class CacheConfigurationModel(BaseModel):
    """Model for cache configuration and strategy"""
    model_config = ConfigDict(validate_assignment=True)

    cache_name: str = Field(..., description="Unique cache identifier")
    strategy: CacheStrategy = Field(default=CacheStrategy.LRU)
    max_size: int = Field(default=1000, ge=1)
    ttl_seconds: Optional[int] = Field(default=3600, ge=1)
    warm_up_queries: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Cache statistics
    hit_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    miss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    eviction_count: int = Field(default=0, ge=0)
    
    # Performance metrics
    avg_hit_time_ms: Optional[float] = None
    avg_miss_time_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    
    # Advanced settings
    enable_compression: bool = Field(default=False)
    enable_statistics: bool = Field(default=True)
    refresh_ahead_factor: float = Field(default=0.8, ge=0.0, le=1.0)


class ConnectionPoolMetrics(BaseModel):
    """Metrics for connection pool monitoring"""
    model_config = ConfigDict(validate_assignment=True)

    pool_name: str = Field(..., description="Connection pool identifier")
    total_connections: int = Field(..., ge=0)
    active_connections: int = Field(..., ge=0)
    idle_connections: int = Field(..., ge=0)
    pending_requests: int = Field(default=0, ge=0)
    
    # Performance metrics
    avg_acquisition_time_ms: Optional[float] = None
    avg_connection_lifetime_seconds: Optional[float] = None
    connection_errors: int = Field(default=0, ge=0)
    timeout_errors: int = Field(default=0, ge=0)
    
    # Pool configuration
    min_connections: int = Field(..., ge=1)
    max_connections: int = Field(..., ge=1)
    connection_timeout_ms: int = Field(default=5000, ge=100)
    idle_timeout_seconds: int = Field(default=300, ge=1)


class BatchProcessingConfig(BaseModel):
    """Configuration for batch processing optimization"""
    model_config = ConfigDict(validate_assignment=True)

    batch_size: int = Field(default=100, ge=1, le=10000)
    parallel_workers: int = Field(default=4, ge=1, le=32)
    queue_size: int = Field(default=1000, ge=1)
    timeout_seconds: int = Field(default=300, ge=1)
    
    # Processing strategies
    enable_streaming: bool = Field(default=True)
    enable_compression: bool = Field(default=False)
    retry_failed_items: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0)
    
    # Performance tracking
    items_processed: int = Field(default=0, ge=0)
    processing_rate: Optional[float] = None  # items per second
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_item_processing_time_ms: Optional[float] = None


class MemoryOptimizationConfig(BaseModel):
    """Configuration for memory optimization"""
    model_config = ConfigDict(validate_assignment=True)

    # Memory limits
    max_heap_size_mb: int = Field(default=512, ge=64)
    max_cache_size_mb: int = Field(default=128, ge=16)
    max_buffer_size_mb: int = Field(default=64, ge=8)
    
    # Garbage collection settings
    gc_threshold: float = Field(default=0.8, ge=0.1, le=1.0)
    gc_interval_seconds: int = Field(default=60, ge=1)
    
    # Object pooling
    enable_object_pooling: bool = Field(default=True)
    pool_sizes: Dict[str, int] = Field(default_factory=dict)
    
    # Memory usage tracking
    current_heap_usage_mb: Optional[float] = None
    peak_heap_usage_mb: Optional[float] = None
    gc_collection_count: int = Field(default=0, ge=0)
    gc_time_ms: Optional[float] = None


class PerformanceAlert(BaseModel):
    """Model for performance alerts"""
    model_config = ConfigDict(validate_assignment=True)

    alert_id: str = Field(..., description="Unique alert identifier")
    metric_type: PerformanceMetricType
    severity: AlertSeverity
    threshold_value: float
    actual_value: float
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Alert context
    component: str = Field(..., description="Component that triggered alert")
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Alert handling
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None


class PerformanceSnapshot(BaseModel):
    """Complete performance snapshot at a point in time"""
    model_config = ConfigDict(validate_assignment=True)

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # System metrics
    cpu_usage_percent: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    disk_io_mb_per_sec: Optional[float] = None
    network_io_mb_per_sec: Optional[float] = None
    
    # Application metrics
    active_requests: int = Field(default=0, ge=0)
    request_rate_per_sec: Optional[float] = None
    avg_response_time_ms: Optional[float] = None
    error_rate_percent: Optional[float] = None
    
    # Database metrics
    db_connections_active: int = Field(default=0, ge=0)
    db_query_rate_per_sec: Optional[float] = None
    db_avg_query_time_ms: Optional[float] = None
    
    # Cache metrics
    cache_hit_rate_percent: Optional[float] = None
    cache_memory_usage_mb: Optional[float] = None
    
    # Custom metrics
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class OptimizationResult(BaseModel):
    """Result of applying an optimization strategy"""
    model_config = ConfigDict(validate_assignment=True)

    optimization_id: str = Field(..., description="Unique optimization identifier")
    strategy: OptimizationStrategy
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    success: bool
    
    # Performance impact
    metrics_before: Dict[str, float] = Field(default_factory=dict)
    metrics_after: Dict[str, float] = Field(default_factory=dict)
    improvement_percent: Optional[float] = None
    
    # Optimization details
    configuration: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    rollback_available: bool = Field(default=False)


class PerformanceRecommendation(BaseModel):
    """Model for performance improvement recommendations"""
    model_config = ConfigDict(validate_assignment=True)

    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    title: str
    description: str
    impact: str = Field(..., description="Expected performance impact")
    effort: str = Field(..., description="Implementation effort required")
    priority: int = Field(..., ge=1, le=5)
    
    # Recommendation details
    affected_components: List[str] = Field(default_factory=list)
    optimization_strategies: List[OptimizationStrategy] = Field(default_factory=list)
    estimated_improvement_percent: Optional[float] = None
    
    # Implementation guidance
    implementation_steps: List[str] = Field(default_factory=list)
    configuration_changes: Dict[str, Any] = Field(default_factory=dict)
    risks: List[str] = Field(default_factory=list)
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    implemented: bool = Field(default=False)
    implemented_at: Optional[datetime] = None
    actual_improvement_percent: Optional[float] = None