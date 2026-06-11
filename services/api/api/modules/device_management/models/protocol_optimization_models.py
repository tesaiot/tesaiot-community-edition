# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Protocol Optimization Models for IoT Device Management

This module defines models for optimizing various IoT protocols
to reduce bandwidth, improve latency, and handle device constraints.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class CompressionAlgorithm(Enum):
    """Supported compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    BROTLI = "brotli"
    LZ4 = "lz4"
    ZSTD = "zstd"  # Zstandard - good for IoT
    DEFLATE = "deflate"


class QoSLevel(Enum):
    """Quality of Service levels"""
    AT_MOST_ONCE = 0    # Fire and forget
    AT_LEAST_ONCE = 1   # Acknowledged delivery
    EXACTLY_ONCE = 2    # Assured delivery


class ProtocolType(Enum):
    """Supported IoT protocols"""
    MQTT = "mqtt"
    MQTT5 = "mqtt5"
    HTTP = "http"
    HTTP2 = "http2"
    COAP = "coap"
    WEBSOCKET = "websocket"
    AMQP = "amqp"
    LORAWAN = "lorawan"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ProtocolMetrics:
    """Performance metrics for protocol optimization"""
    protocol: ProtocolType
    device_id: str
    org_id: str
    
    # Bandwidth metrics
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    compression_ratio: float = 0.0
    
    # Latency metrics
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Connection metrics
    connection_count: int = 0
    reconnection_count: int = 0
    connection_failures: int = 0
    uptime_seconds: float = 0.0
    
    # Error metrics
    send_errors: int = 0
    receive_errors: int = 0
    timeout_errors: int = 0
    protocol_errors: int = 0
    
    # Resource usage
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    battery_impact_percent: Optional[float] = None
    
    # Timestamps
    measured_at: datetime = field(default_factory=datetime.utcnow)
    measurement_duration_seconds: float = 3600.0  # Default 1 hour
    
    def calculate_efficiency_score(self) -> float:
        """Calculate overall protocol efficiency score (0-100)"""
        # Weighted scoring based on various metrics
        bandwidth_score = min(100, (1 - (self.bytes_sent / (self.messages_sent * 1024))) * 100) if self.messages_sent > 0 else 0
        latency_score = min(100, (1 - (self.avg_latency_ms / 1000)) * 100) if self.avg_latency_ms > 0 else 100
        reliability_score = min(100, ((self.messages_sent - self.send_errors) / self.messages_sent) * 100) if self.messages_sent > 0 else 100
        
        # Weighted average
        return (bandwidth_score * 0.4 + latency_score * 0.4 + reliability_score * 0.2)


@dataclass
class CompressionStrategy:
    """Compression strategy configuration"""
    algorithm: CompressionAlgorithm
    compression_level: int = 6  # 1-9 for most algorithms
    min_size_bytes: int = 100  # Minimum size to compress
    enabled: bool = True
    
    # Algorithm-specific settings
    dictionary: Optional[bytes] = None  # For dictionary-based compression
    window_size: Optional[int] = None  # For streaming compression
    
    # Performance hints
    cpu_intensive: bool = False
    memory_intensive: bool = False
    battery_friendly: bool = True
    
    def should_compress(self, data_size: int) -> bool:
        """Determine if data should be compressed"""
        return self.enabled and data_size >= self.min_size_bytes


@dataclass
class QoSConfiguration:
    """Quality of Service configuration"""
    default_level: QoSLevel = QoSLevel.AT_LEAST_ONCE
    
    # Priority-based QoS mapping
    priority_qos_map: Dict[MessagePriority, QoSLevel] = field(default_factory=lambda: {
        MessagePriority.LOW: QoSLevel.AT_MOST_ONCE,
        MessagePriority.NORMAL: QoSLevel.AT_LEAST_ONCE,
        MessagePriority.HIGH: QoSLevel.EXACTLY_ONCE,
        MessagePriority.CRITICAL: QoSLevel.EXACTLY_ONCE
    })
    
    # Retry configuration
    retry_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: int = 1000
    retry_backoff_multiplier: float = 2.0
    max_retry_delay_ms: int = 30000
    
    # Timeout configuration
    message_timeout_ms: int = 30000
    connection_timeout_ms: int = 10000
    
    def get_qos_for_priority(self, priority: MessagePriority) -> QoSLevel:
        """Get QoS level for given priority"""
        return self.priority_qos_map.get(priority, self.default_level)


@dataclass
class MQTTOptimizationConfig:
    """MQTT-specific optimization configuration"""
    # Connection pooling
    enable_connection_pooling: bool = True
    max_connections_per_broker: int = 10
    connection_idle_timeout_seconds: int = 300
    
    # Message batching
    enable_batching: bool = True
    batch_size: int = 100
    batch_timeout_ms: int = 1000
    max_batch_bytes: int = 65536  # 64KB
    
    # Topic optimization
    enable_topic_aliases: bool = True  # MQTT 5.0
    max_topic_alias: int = 100
    enable_shared_subscriptions: bool = True
    
    # Persistence
    enable_persistence: bool = True
    max_inflight_messages: int = 20
    max_queued_messages: int = 1000
    
    # Keep-alive optimization
    keepalive_interval_seconds: int = 60
    enable_adaptive_keepalive: bool = True
    min_keepalive_seconds: int = 30
    max_keepalive_seconds: int = 300
    
    # Protocol version
    prefer_mqtt5: bool = True
    fallback_to_mqtt3: bool = True


@dataclass
class HTTPOptimizationConfig:
    """HTTP/HTTP2-specific optimization configuration"""
    # Protocol selection
    prefer_http2: bool = True
    fallback_to_http1: bool = True
    
    # Connection management
    enable_connection_pooling: bool = True
    max_connections_per_host: int = 10
    connection_idle_timeout_seconds: int = 300
    enable_keep_alive: bool = True
    
    # Request optimization
    enable_request_batching: bool = True
    batch_endpoint: str = "/batch"
    max_batch_size: int = 50
    batch_timeout_ms: int = 100
    
    # Compression
    accept_encoding: List[str] = field(default_factory=lambda: ["gzip", "deflate", "br"])
    min_compression_size_bytes: int = 1000
    
    # HTTP/2 specific
    enable_server_push: bool = False  # Usually not needed for IoT
    max_concurrent_streams: int = 100
    initial_window_size: int = 65536
    enable_header_compression: bool = True
    
    # Caching
    enable_caching: bool = True
    cache_control_header: str = "max-age=300"
    enable_etag: bool = True


@dataclass
class CoAPOptimizationConfig:
    """CoAP-specific optimization configuration"""
    # Message layer
    enable_confirmable_messages: bool = True
    max_retransmit: int = 4
    ack_timeout_seconds: float = 2.0
    ack_random_factor: float = 1.5
    
    # Block-wise transfer
    enable_blockwise_transfer: bool = True
    preferred_block_size: int = 512  # bytes
    
    # Observation
    enable_observe: bool = True
    max_observe_relationships: int = 100
    
    # DTLS security
    enable_dtls: bool = True
    dtls_handshake_timeout_seconds: int = 10
    
    # Multicast
    enable_multicast: bool = True
    multicast_address: str = "224.0.1.187"
    multicast_port: int = 5683
    
    # Resource discovery
    enable_resource_discovery: bool = True
    discovery_multicast_enabled: bool = True


@dataclass
class WebSocketOptimizationConfig:
    """WebSocket-specific optimization configuration"""
    # Frame optimization
    enable_frame_compression: bool = True
    compression_threshold_bytes: int = 100
    max_frame_size: int = 65536
    
    # Message batching
    enable_message_batching: bool = True
    batch_size: int = 50
    batch_timeout_ms: int = 50
    
    # Ping/Pong optimization
    ping_interval_seconds: int = 30
    pong_timeout_seconds: int = 10
    enable_adaptive_ping: bool = True
    
    # Binary vs Text
    prefer_binary_frames: bool = True
    
    # Multiplexing
    enable_multiplexing: bool = True
    max_channels_per_connection: int = 10
    
    # Reconnection
    enable_auto_reconnect: bool = True
    reconnect_delay_ms: int = 1000
    max_reconnect_delay_ms: int = 30000
    reconnect_backoff_multiplier: float = 1.5


@dataclass
class ProtocolOptimizationProfile:
    """Complete protocol optimization profile for a device"""
    device_id: str
    org_id: str
    profile_name: str
    
    # Protocol selection
    primary_protocol: ProtocolType
    fallback_protocols: List[ProtocolType] = field(default_factory=list)
    protocol_selection_strategy: str = "adaptive"  # adaptive, fixed, round-robin
    
    # Compression
    compression_strategy: CompressionStrategy = field(default_factory=lambda: CompressionStrategy(CompressionAlgorithm.GZIP))
    
    # QoS
    qos_config: QoSConfiguration = field(default_factory=QoSConfiguration)
    
    # Protocol-specific configurations
    mqtt_config: Optional[MQTTOptimizationConfig] = None
    http_config: Optional[HTTPOptimizationConfig] = None
    coap_config: Optional[CoAPOptimizationConfig] = None
    websocket_config: Optional[WebSocketOptimizationConfig] = None
    
    # Device constraints
    max_bandwidth_bps: Optional[int] = None  # bits per second
    max_message_rate_per_minute: Optional[int] = None
    battery_constrained: bool = False
    memory_limit_mb: Optional[int] = None
    cpu_constrained: bool = False
    
    # Adaptive optimization
    enable_adaptive_optimization: bool = True
    optimization_interval_seconds: int = 300
    metric_collection_enabled: bool = True
    
    # Creation metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_protocol_config(self, protocol: ProtocolType) -> Optional[Union[MQTTOptimizationConfig, HTTPOptimizationConfig, CoAPOptimizationConfig, WebSocketOptimizationConfig]]:
        """Get protocol-specific configuration"""
        config_map = {
            ProtocolType.MQTT: self.mqtt_config,
            ProtocolType.MQTT5: self.mqtt_config,
            ProtocolType.HTTP: self.http_config,
            ProtocolType.HTTP2: self.http_config,
            ProtocolType.COAP: self.coap_config,
            ProtocolType.WEBSOCKET: self.websocket_config
        }
        return config_map.get(protocol)


@dataclass
class MessageBatch:
    """Batch of messages for optimized transmission"""
    batch_id: str
    protocol: ProtocolType
    device_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    total_size_bytes: int = 0
    compression_applied: bool = False
    compressed_size_bytes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.NORMAL
    
    def add_message(self, message: Dict[str, Any], size_bytes: int) -> bool:
        """Add message to batch, return True if successful"""
        self.messages.append(message)
        self.total_size_bytes += size_bytes
        return True
    
    def get_compression_ratio(self) -> float:
        """Get compression ratio if compression was applied"""
        if self.compression_applied and self.compressed_size_bytes:
            return 1 - (self.compressed_size_bytes / self.total_size_bytes)
        return 0.0


@dataclass
class ProtocolCapabilities:
    """Device protocol capabilities"""
    device_id: str
    supported_protocols: List[ProtocolType]
    supported_compression: List[CompressionAlgorithm]
    max_message_size_bytes: int
    max_connection_count: int
    supports_batch_operations: bool
    supports_binary_data: bool
    supports_streaming: bool
    supports_multiplexing: bool
    supports_qos: bool
    max_qos_level: Optional[QoSLevel] = None
    
    # Resource constraints
    cpu_mhz: Optional[int] = None
    ram_mb: Optional[int] = None
    storage_mb: Optional[int] = None
    battery_mah: Optional[int] = None
    network_type: Optional[str] = None  # wifi, cellular, lora, etc.
    
    def supports_protocol(self, protocol: ProtocolType) -> bool:
        """Check if device supports given protocol"""
        return protocol in self.supported_protocols
    
    def get_optimal_compression(self) -> CompressionAlgorithm:
        """Get optimal compression algorithm based on capabilities"""
        if self.battery_mah and self.battery_mah < 1000:
            # Battery constrained - prefer lightweight compression
            if CompressionAlgorithm.LZ4 in self.supported_compression:
                return CompressionAlgorithm.LZ4
        
        if self.cpu_mhz and self.cpu_mhz < 100:
            # CPU constrained - avoid heavy compression
            if CompressionAlgorithm.DEFLATE in self.supported_compression:
                return CompressionAlgorithm.DEFLATE
        
        # Default to most efficient
        if CompressionAlgorithm.ZSTD in self.supported_compression:
            return CompressionAlgorithm.ZSTD
        elif CompressionAlgorithm.GZIP in self.supported_compression:
            return CompressionAlgorithm.GZIP
        
        return CompressionAlgorithm.NONE