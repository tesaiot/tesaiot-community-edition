# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Load Testing Models for Device Management Module

This module defines data models for load testing scenarios, patterns, and results.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class LoadPattern(str, Enum):
    """Supported load patterns for testing"""
    RAMP_UP = "ramp_up"
    STEADY = "steady"
    SPIKE = "spike"
    WAVE = "wave"
    STRESS = "stress"
    CUSTOM = "custom"


class DeviceType(str, Enum):
    """Device types for simulation"""
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    GATEWAY = "gateway"
    EDGE_DEVICE = "edge_device"
    SMART_METER = "smart_meter"
    INDUSTRIAL_CONTROLLER = "industrial_controller"


class TestScenarioModel(BaseModel):
    """Model for defining load test scenarios"""
    scenario_id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Scenario name")
    description: Optional[str] = Field(None, description="Scenario description")
    duration_seconds: int = Field(..., gt=0, description="Test duration in seconds")
    target_devices: int = Field(..., gt=0, description="Target number of devices")
    device_distribution: Dict[DeviceType, float] = Field(
        default_factory=lambda: {DeviceType.SENSOR: 0.7, DeviceType.ACTUATOR: 0.3},
        description="Distribution of device types (percentages)"
    )
    load_pattern: LoadPattern = Field(..., description="Load pattern to apply")
    pattern_config: Dict[str, Any] = Field(default_factory=dict, description="Pattern-specific configuration")
    
    # Telemetry configuration
    telemetry_interval_ms: int = Field(5000, gt=0, description="Telemetry reporting interval in milliseconds")
    telemetry_batch_size: int = Field(10, gt=0, description="Number of telemetry messages per batch")
    telemetry_variance: float = Field(0.1, ge=0, le=1, description="Variance in telemetry timing (0-1)")
    
    # Device behavior configuration
    device_failure_rate: float = Field(0.01, ge=0, le=1, description="Percentage of devices that fail")
    reconnection_delay_ms: int = Field(30000, gt=0, description="Delay before reconnection attempts")
    command_response_time_ms: int = Field(100, gt=0, description="Average command response time")
    
    # Resource limits
    max_concurrent_connections: Optional[int] = Field(None, description="Maximum concurrent connections")
    max_messages_per_second: Optional[int] = Field(None, description="Maximum messages per second")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('device_distribution')
    def validate_distribution(cls, v):
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Device distribution must sum to 1.0, got {total}")
        return v


class LoadPatternConfig(BaseModel):
    """Configuration for specific load patterns"""
    
    class RampUpConfig(BaseModel):
        """Configuration for ramp-up pattern"""
        initial_devices: int = Field(0, ge=0)
        ramp_duration_seconds: int = Field(60, gt=0)
        hold_duration_seconds: int = Field(120, gt=0)
        
    class SpikeConfig(BaseModel):
        """Configuration for spike pattern"""
        baseline_devices: int = Field(100, gt=0)
        spike_multiplier: float = Field(5.0, gt=1.0)
        spike_duration_seconds: int = Field(30, gt=0)
        spike_interval_seconds: int = Field(300, gt=0)
        
    class WaveConfig(BaseModel):
        """Configuration for wave pattern"""
        min_devices: int = Field(50, gt=0)
        max_devices: int = Field(500, gt=0)
        wave_period_seconds: int = Field(120, gt=0)
        
    class StressConfig(BaseModel):
        """Configuration for stress testing"""
        start_devices: int = Field(100, gt=0)
        increment_devices: int = Field(50, gt=0)
        increment_interval_seconds: int = Field(60, gt=0)
        max_devices: Optional[int] = Field(None)


class PerformanceMetric(BaseModel):
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    percentiles: Optional[Dict[str, float]] = None  # p50, p90, p95, p99


class PerformanceBaseline(BaseModel):
    """Performance baseline for comparison"""
    baseline_id: str = Field(..., description="Unique baseline identifier")
    name: str = Field(..., description="Baseline name")
    description: Optional[str] = Field(None)
    scenario_id: str = Field(..., description="Associated scenario ID")
    
    # Key metrics
    avg_response_time_ms: float = Field(..., gt=0)
    p95_response_time_ms: float = Field(..., gt=0)
    p99_response_time_ms: float = Field(..., gt=0)
    
    throughput_messages_per_sec: float = Field(..., gt=0)
    concurrent_connections: int = Field(..., gt=0)
    
    # Resource utilization
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_mb: float = Field(..., gt=0)
    network_bandwidth_mbps: float = Field(..., gt=0)
    
    # Error rates
    error_rate: float = Field(..., ge=0, le=1)
    timeout_rate: float = Field(..., ge=0, le=1)
    
    # Thresholds for alerting
    thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "max_response_time_ms": 1000,
            "max_error_rate": 0.05,
            "max_cpu_percent": 80,
            "max_memory_mb": 4096
        }
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    environment: str = Field("production", description="Environment where baseline was measured")


class TestResult(BaseModel):
    """Results from a load test execution"""
    result_id: str = Field(..., description="Unique result identifier")
    scenario_id: str = Field(..., description="Scenario that was executed")
    baseline_id: Optional[str] = Field(None, description="Baseline used for comparison")
    
    # Execution details
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    status: Literal["completed", "failed", "aborted"] = Field(...)
    
    # Device statistics
    total_devices_simulated: int
    peak_concurrent_devices: int
    device_connection_failures: int
    
    # Message statistics
    total_messages_sent: int
    total_messages_received: int
    messages_per_second_avg: float
    messages_per_second_peak: float
    
    # Performance metrics
    response_times: Dict[str, float] = Field(
        ..., 
        description="Response time percentiles (p50, p90, p95, p99, max)"
    )
    throughput_timeline: List[PerformanceMetric] = Field(
        default_factory=list,
        description="Throughput measurements over time"
    )
    
    # Resource utilization
    resource_usage: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Resource usage statistics (cpu, memory, network)"
    )
    
    # Error analysis
    error_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of errors by type"
    )
    error_rate: float = Field(..., ge=0, le=1)
    
    # Baseline comparison
    baseline_comparison: Optional[Dict[str, Dict[str, float]]] = Field(
        None,
        description="Comparison with baseline (metric: {current, baseline, delta_percent})"
    )
    
    # Anomalies and issues
    anomalies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detected anomalies during test"
    )
    
    # Raw data reference
    raw_data_path: Optional[str] = Field(None, description="Path to raw test data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeviceSimulationProfile(BaseModel):
    """Profile for simulating device behavior"""
    profile_id: str = Field(..., description="Unique profile identifier")
    device_type: DeviceType
    
    # Telemetry behavior
    telemetry_schema: Dict[str, Any] = Field(..., description="Schema for telemetry data")
    telemetry_generation_rules: Dict[str, Dict[str, Any]] = Field(
        ...,
        description="Rules for generating telemetry values"
    )
    
    # Command handling
    supported_commands: List[str] = Field(default_factory=list)
    command_success_rate: float = Field(0.95, ge=0, le=1)
    command_processing_time_ms: Dict[str, float] = Field(
        default_factory=dict,
        description="Processing time per command type"
    )
    
    # Network behavior
    network_latency_ms: Dict[str, float] = Field(
        default_factory=lambda: {"min": 10, "max": 100, "avg": 30},
        description="Network latency simulation parameters"
    )
    packet_loss_rate: float = Field(0.001, ge=0, le=1)
    
    # Resource consumption
    cpu_usage_per_device: float = Field(0.1, description="CPU usage per device (cores)")
    memory_usage_per_device_mb: float = Field(10, description="Memory usage per device (MB)")
    bandwidth_usage_kbps: float = Field(1, description="Bandwidth usage per device (Kbps)")


class LoadTestConfiguration(BaseModel):
    """Complete configuration for a load test"""
    test_id: str = Field(..., description="Unique test identifier")
    name: str = Field(..., description="Test name")
    description: Optional[str] = Field(None)
    
    # Test components
    scenario: TestScenarioModel
    device_profiles: List[DeviceSimulationProfile]
    baseline: Optional[PerformanceBaseline] = None
    
    # Infrastructure configuration
    target_endpoints: List[str] = Field(..., description="API endpoints to test")
    authentication_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Authentication configuration"
    )
    
    # Test execution settings
    warm_up_duration_seconds: int = Field(30, gt=0, description="Warm-up period before measurements")
    cool_down_duration_seconds: int = Field(30, gt=0, description="Cool-down period after test")
    measurement_interval_seconds: int = Field(5, gt=0, description="Interval for collecting metrics")
    
    # Data collection
    collect_detailed_metrics: bool = Field(True, description="Collect detailed performance metrics")
    store_raw_data: bool = Field(False, description="Store raw test data for analysis")
    
    # Alerting
    alert_on_threshold_breach: bool = Field(True, description="Send alerts on threshold breaches")
    alert_webhooks: List[str] = Field(default_factory=list, description="Webhook URLs for alerts")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="User who created the configuration")
    
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class LoadTestSummary(BaseModel):
    """Summary of load test results for reporting"""
    test_id: str
    test_name: str
    execution_time: datetime
    duration_minutes: float
    
    # High-level metrics
    total_devices: int
    total_messages: int
    avg_throughput_mps: float  # messages per second
    peak_throughput_mps: float
    
    # Performance summary
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    
    # Success metrics
    success_rate: float
    error_rate: float
    timeout_rate: float
    
    # Resource utilization peaks
    peak_cpu_percent: float
    peak_memory_mb: float
    peak_network_mbps: float
    
    # Baseline comparison
    baseline_met: Optional[bool] = None
    performance_delta: Optional[Dict[str, float]] = None
    
    # Key findings
    bottlenecks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Status
    overall_status: Literal["passed", "failed", "degraded"] = Field(...)
    status_reason: Optional[str] = None