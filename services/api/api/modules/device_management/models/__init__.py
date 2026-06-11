# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

from .device_models import (
    Device, DeviceStatus, DeviceType, ConnectionProtocol,
    DeviceCommand, DeviceConfiguration, DeviceCertificate,
    ProvisioningTemplate
)
from .device_dtos import DeviceCreateDTO, DeviceUpdateDTO
from .audit_models import DeviceAuditEntry, DeviceAuditAction
from .group_models import (
    DeviceGroup, GroupType, GroupRule, GroupPolicy, PolicyAction,
    GroupingStrategy, GroupMembership, GroupOperation, GroupHierarchy,
    GroupTemplate
)
from .telemetry_models import (
    TelemetryData, TelemetryPoint, TelemetryBatch, TelemetryBuffer,
    TelemetryType, TelemetryPriority, DataQuality, AggregationType,
    TelemetryAggregation, TelemetryAlert, TelemetryIngestionStats
)
from .bulk_models import (
    BulkOperationType, BulkOperationStatus, ItemStatus,
    BulkOperationItem, BulkCreateRequest, BulkUpdateRequest,
    BulkDeleteRequest, BulkOperationProgress, BulkOperationResult,
    BulkOperationFilter, BulkOperationResponse
)
from .template_models import (
    DeviceTemplate, TemplateCategory, TemplateStatus,
    ValidationRule, TemplateMetadata, TemplateVersion,
    TemplateInstance, INDUSTRY_STANDARD_TEMPLATES
)
from .event_streaming_models import (
    EventType, EventPriority, EventCategory, EventPayload,
    DeviceEventPayload, TelemetryEventPayload, CommandEventPayload,
    SecurityEventPayload, StreamConfiguration, EventSubscription,
    EventFilter, WebSocketMessage, WebSocketConnection, EventStreamStats
)
from .security_models import (
    AuthenticationType, PermissionScope, ThreatLevel, SecurityEventType,
    DeviceApiKey, DeviceOAuthToken, DeviceCertificateAuth, DeviceRole,
    AccessControlPolicy, SecurityPolicy, RateLimitRule, ThreatDetectionRule,
    SecurityEvent, DeviceSecurityProfile, SecurityAuditLog
)
from .performance_models import (
    PerformanceMetricType, OptimizationStrategy, CacheStrategy, AlertSeverity,
    PerformanceMetric, QueryOptimizationModel, CacheConfigurationModel,
    ConnectionPoolMetrics, BatchProcessingConfig, MemoryOptimizationConfig,
    PerformanceAlert, PerformanceSnapshot, OptimizationResult,
    PerformanceRecommendation
)
from .protocol_optimization_models import (
    CompressionAlgorithm, QoSLevel, ProtocolType, MessagePriority,
    ProtocolMetrics, CompressionStrategy, QoSConfiguration,
    MQTTOptimizationConfig, HTTPOptimizationConfig, CoAPOptimizationConfig,
    WebSocketOptimizationConfig, ProtocolOptimizationProfile,
    MessageBatch, ProtocolCapabilities
)
from .load_testing_models import (
    LoadPattern, DeviceType as LoadTestDeviceType, TestScenarioModel,
    LoadPatternConfig, PerformanceBaseline,
    TestResult, DeviceSimulationProfile, LoadTestConfiguration,
    LoadTestSummary
)

__all__ = [
    # Device models
    "Device", "DeviceStatus", "DeviceType", "ConnectionProtocol",
    "DeviceCommand", "DeviceConfiguration", "DeviceCertificate",
    "ProvisioningTemplate",
    
    # Group models
    "DeviceGroup", "GroupType", "GroupRule", "GroupPolicy", "PolicyAction",
    "GroupingStrategy", "GroupMembership", "GroupOperation", "GroupHierarchy",
    "GroupTemplate",
    
    # DTOs
    "DeviceCreateDTO", "DeviceUpdateDTO",
    
    # Audit models
    "DeviceAuditEntry", "DeviceAuditAction",
    
    # Telemetry models
    "TelemetryData", "TelemetryPoint", "TelemetryBatch", "TelemetryBuffer",
    "TelemetryType", "TelemetryPriority", "DataQuality", "AggregationType",
    "TelemetryAggregation", "TelemetryAlert", "TelemetryIngestionStats",
    
    # Bulk operation models
    "BulkOperationType", "BulkOperationStatus", "ItemStatus",
    "BulkOperationItem", "BulkCreateRequest", "BulkUpdateRequest",
    "BulkDeleteRequest", "BulkOperationProgress", "BulkOperationResult",
    "BulkOperationFilter", "BulkOperationResponse",
    
    # Template models
    "DeviceTemplate", "TemplateCategory", "TemplateStatus",
    "ValidationRule", "TemplateMetadata", "TemplateVersion",
    "TemplateInstance", "INDUSTRY_STANDARD_TEMPLATES",
    
    # Event streaming models
    "EventType", "EventPriority", "EventCategory", "EventPayload",
    "DeviceEventPayload", "TelemetryEventPayload", "CommandEventPayload",
    "SecurityEventPayload", "StreamConfiguration", "EventSubscription",
    "EventFilter", "WebSocketMessage", "WebSocketConnection", "EventStreamStats",
    
    # Security models
    "AuthenticationType", "PermissionScope", "ThreatLevel", "SecurityEventType",
    "DeviceApiKey", "DeviceOAuthToken", "DeviceCertificateAuth", "DeviceRole",
    "AccessControlPolicy", "SecurityPolicy", "RateLimitRule", "ThreatDetectionRule",
    "SecurityEvent", "DeviceSecurityProfile", "SecurityAuditLog",
    
    # Performance models
    "PerformanceMetricType", "OptimizationStrategy", "CacheStrategy", "AlertSeverity",
    "PerformanceMetric", "QueryOptimizationModel", "CacheConfigurationModel",
    "ConnectionPoolMetrics", "BatchProcessingConfig", "MemoryOptimizationConfig",
    "PerformanceAlert", "PerformanceSnapshot", "OptimizationResult",
    "PerformanceRecommendation",
    
    # Protocol optimization models
    "CompressionAlgorithm", "QoSLevel", "ProtocolType", "MessagePriority",
    "ProtocolMetrics", "CompressionStrategy", "QoSConfiguration",
    "MQTTOptimizationConfig", "HTTPOptimizationConfig", "CoAPOptimizationConfig",
    "WebSocketOptimizationConfig", "ProtocolOptimizationProfile",
    "MessageBatch", "ProtocolCapabilities",
    
    # Load testing models
    "LoadPattern", "LoadTestDeviceType", "TestScenarioModel",
    "LoadPatternConfig", "PerformanceBaseline",
    "TestResult", "DeviceSimulationProfile", "LoadTestConfiguration",
    "LoadTestSummary"
]