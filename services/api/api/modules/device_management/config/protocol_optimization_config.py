# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Protocol Optimization Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Protocol Optimization for 75% Rollout
Version: Dynamic (read from VERSION.txt)
Build Date: 2025-07-27

Description:
    Protocol optimizations based on load testing insights:
    - Message compression tuning
    - Batch size optimization
    - Connection reuse improvements
    - Protocol-specific optimizations
"""

from typing import Dict, Any
from enum import Enum


class ProtocolType(Enum):
    """Supported IoT protocols"""
    HTTP_REST = "http_rest"
    MQTT = "mqtt"
    WEBSOCKET = "websocket"
    COAP = "coap"
    AMQP = "amqp"


class CompressionLevel(Enum):
    """Compression level settings"""
    NONE = 0
    LOW = 1
    MEDIUM = 3
    HIGH = 6
    MAXIMUM = 9


class ProtocolOptimizationConfig:
    """Protocol optimization configuration for maximum performance"""
    
    @staticmethod
    def get_http_optimization() -> Dict[str, Any]:
        """HTTP/REST API optimization settings"""
        return {
            # Connection pooling
            'connection_pool': {
                'max_pool_size': 100,
                'max_pool_connections': 20,
                'max_keepalive_connections': 20,
                'keepalive_expiry': 300,  # 5 minutes
                'pool_timeout': 10.0,
                'connection_timeout': 5.0,
                'read_timeout': 30.0
            },
            
            # HTTP/2 optimization
            'http2': {
                'enabled': True,
                'max_concurrent_streams': 100,
                'initial_window_size': 65535,
                'max_frame_size': 16384,
                'enable_server_push': False  # Not needed for API
            },
            
            # Compression settings
            'compression': {
                'enabled': True,
                'algorithms': ['br', 'gzip', 'deflate'],  # Brotli preferred
                'min_size_bytes': 1024,
                'level': CompressionLevel.MEDIUM.value,
                'exclude_content_types': [
                    'image/*',
                    'video/*',
                    'application/octet-stream'
                ]
            },
            
            # Request optimization
            'request_optimization': {
                'batch_enabled': True,
                'max_batch_size': 100,
                'batch_timeout_ms': 50,
                'request_compression_threshold': 1024,
                'response_streaming': True,
                'chunked_transfer': True
            },
            
            # Caching headers
            'caching_headers': {
                'device_metadata': {
                    'cache_control': 'private, max-age=1800',  # 30 minutes
                    'etag_enabled': True,
                    'last_modified_enabled': True
                },
                'device_status': {
                    'cache_control': 'private, max-age=300',   # 5 minutes
                    'etag_enabled': True
                },
                'static_data': {
                    'cache_control': 'public, max-age=3600',   # 1 hour
                    'etag_enabled': True,
                    'immutable': True
                }
            },
            
            # Rate limiting optimization
            'rate_limiting': {
                'burst_size': 1000,
                'refill_rate': 100,  # requests per second
                'sliding_window_seconds': 60,
                'adaptive_limiting': True,
                'priority_queues': {
                    'high': {'weight': 0.5, 'queue_size': 500},
                    'medium': {'weight': 0.3, 'queue_size': 300},
                    'low': {'weight': 0.2, 'queue_size': 200}
                }
            }
        }
    
    @staticmethod
    def get_mqtt_optimization() -> Dict[str, Any]:
        """MQTT protocol optimization settings"""
        return {
            # Connection optimization
            'connection': {
                'keep_alive_seconds': 60,
                'clean_session': False,  # Persistent sessions for reliability
                'max_inflight_messages': 20,
                'message_retry_interval': 20,
                'automatic_reconnect': True,
                'reconnect_delay_seconds': [1, 2, 4, 8, 16, 32, 60],
                'max_reconnect_delay': 60
            },
            
            # Quality of Service optimization
            'qos_optimization': {
                'default_qos': 1,  # At least once delivery
                'critical_topics_qos': 2,  # Exactly once for critical data
                'telemetry_qos': 0,  # At most once for high-frequency telemetry
                'command_qos': 2,   # Exactly once for commands
                'adaptive_qos': True,
                'qos_downgrade_threshold_ms': 1000
            },
            
            # Message optimization
            'message_optimization': {
                'max_payload_size': 262144,  # 256KB
                'compression_enabled': True,
                'compression_threshold': 1024,
                'compression_algorithm': 'zstd',
                'message_batching': {
                    'enabled': True,
                    'max_batch_size': 50,
                    'batch_timeout_ms': 100,
                    'batch_compression': True
                }
            },
            
            # Topic optimization
            'topic_optimization': {
                'topic_aliases': True,
                'shared_subscriptions': True,
                'subscription_wildcards': {
                    'max_levels': 8,
                    'optimization_enabled': True
                },
                'topic_hierarchy': {
                    'device_telemetry': 'tel/{org_id}/{device_type}/{device_id}',
                    'device_commands': 'cmd/{org_id}/{device_id}',
                    'device_status': 'status/{org_id}/{device_id}',
                    'system_events': 'sys/{event_type}'
                }
            },
            
            # Broker optimization
            'broker_optimization': {
                'session_expiry_interval': 3600,  # 1 hour
                'max_packet_size': 268435456,  # 256MB
                'receive_maximum': 65535,
                'topic_alias_maximum': 65535,
                'request_response_information': True,
                'request_problem_information': True
            },
            
            # Security optimization
            'security_optimization': {
                'tls_version': '1.3',
                'cipher_suites': [
                    'TLS_AES_256_GCM_SHA384',
                    'TLS_CHACHA20_POLY1305_SHA256',
                    'TLS_AES_128_GCM_SHA256'
                ],
                'certificate_validation': True,
                'sni_enabled': True,
                'session_tickets': True,
                'ocsp_stapling': True
            }
        }
    
    @staticmethod
    def get_websocket_optimization() -> Dict[str, Any]:
        """WebSocket optimization settings"""
        return {
            # Connection optimization
            'connection': {
                'ping_interval': 30,
                'ping_timeout': 10,
                'close_timeout': 10,
                'max_size': 1048576,  # 1MB
                'max_queue': 32,
                'read_limit': 65536,
                'write_limit': 65536,
                'compression': 'deflate'
            },
            
            # Message optimization
            'message_optimization': {
                'binary_format': True,  # Use binary instead of text when possible
                'message_compression': True,
                'compression_threshold': 1024,
                'frame_compression': True,
                'per_message_deflate': {
                    'enabled': True,
                    'server_max_window_bits': 15,
                    'client_max_window_bits': 15,
                    'server_no_context_takeover': False,
                    'client_no_context_takeover': False,
                    'compress_threshold': 1024
                }
            },
            
            # Batching and buffering
            'batching': {
                'enabled': True,
                'max_batch_size': 100,
                'batch_timeout_ms': 50,
                'priority_batching': True,
                'adaptive_batching': True,
                'buffer_size': 65536
            },
            
            # Flow control
            'flow_control': {
                'enabled': True,
                'send_buffer_size': 131072,  # 128KB
                'receive_buffer_size': 131072,
                'backpressure_threshold': 0.8,
                'rate_limiting': {
                    'messages_per_second': 1000,
                    'bytes_per_second': 1048576  # 1MB/s
                }
            },
            
            # Protocol extensions
            'extensions': {
                'permessage_deflate': True,
                'x_webkit_deflate_frame': False,  # Legacy, disabled
                'custom_extensions': []
            }
        }
    
    @staticmethod
    def get_coap_optimization() -> Dict[str, Any]:
        """CoAP protocol optimization settings"""
        return {
            # UDP optimization
            'udp_optimization': {
                'socket_buffer_size': 65536,
                'multicast_enabled': True,
                'block_transfer': {
                    'enabled': True,
                    'block_size': 1024,
                    'max_block_size': 4096
                }
            },
            
            # Reliability optimization
            'reliability': {
                'acknowledgment_timeout': 2.0,
                'acknowledgment_random_factor': 1.5,
                'max_retransmit': 4,
                'max_latency': 100.0,
                'processing_delay': 2.0,
                'max_rtt': 202.0
            },
            
            # Message optimization
            'message_optimization': {
                'piggyback_optimization': True,
                'separate_response_optimization': True,
                'token_length_optimization': True,
                'option_compression': True,
                'payload_compression': {
                    'enabled': True,
                    'threshold': 64,
                    'algorithm': 'deflate'
                }
            },
            
            # Observe pattern optimization
            'observe_optimization': {
                'max_age': 3600,
                'notification_threshold': 0.1,
                'batch_notifications': True,
                'adaptive_observe': True
            }
        }
    
    @staticmethod
    def get_protocol_switching() -> Dict[str, Any]:
        """Protocol switching and fallback configuration"""
        return {
            # Protocol selection criteria
            'selection_criteria': {
                'device_type_mapping': {
                    'sensor': ['mqtt', 'coap'],
                    'gateway': ['mqtt', 'http_rest'],
                    'edge_device': ['mqtt', 'websocket'],
                    'mobile': ['http_rest', 'websocket'],
                    'web_client': ['websocket', 'http_rest']
                },
                'network_condition_mapping': {
                    'low_bandwidth': ['coap', 'mqtt'],
                    'high_latency': ['mqtt', 'http_rest'],
                    'unstable': ['mqtt', 'coap'],
                    'high_throughput': ['websocket', 'http_rest']
                }
            },
            
            # Fallback strategies
            'fallback_strategies': {
                'primary_failure': {
                    'timeout_ms': 5000,
                    'max_retries': 3,
                    'backoff_factor': 2.0
                },
                'protocol_degradation': {
                    'websocket_to_http': True,
                    'mqtt_to_coap': True,
                    'http2_to_http1': True
                },
                'automatic_recovery': {
                    'enabled': True,
                    'check_interval_seconds': 30,
                    'success_threshold': 3
                }
            },
            
            # Load balancing
            'load_balancing': {
                'algorithm': 'weighted_round_robin',
                'health_check_interval': 10,
                'protocol_weights': {
                    'http_rest': 0.4,
                    'websocket': 0.3,
                    'mqtt': 0.2,
                    'coap': 0.1
                },
                'adaptive_weights': True,
                'circuit_breaker': {
                    'failure_threshold': 5,
                    'reset_timeout': 60,
                    'half_open_max_calls': 3
                }
            }
        }
    
    @staticmethod
    def get_batch_processing() -> Dict[str, Any]:
        """Batch processing optimization configuration"""
        return {
            # Global batch settings
            'global_settings': {
                'max_batch_size': 1000,
                'min_batch_size': 10,
                'batch_timeout_ms': 100,
                'max_wait_time_ms': 5000,
                'priority_processing': True
            },
            
            # Protocol-specific batching
            'protocol_specific': {
                'http_rest': {
                    'batch_endpoint': '/api/v1/devices/batch',
                    'max_size': 100,
                    'timeout_ms': 50,
                    'compression': True
                },
                'mqtt': {
                    'topic_batching': True,
                    'payload_aggregation': True,
                    'max_size': 50,
                    'timeout_ms': 100
                },
                'websocket': {
                    'frame_batching': True,
                    'message_aggregation': True,
                    'max_size': 200,
                    'timeout_ms': 25
                }
            },
            
            # Operation-specific batching
            'operation_batching': {
                'device_updates': {
                    'enabled': True,
                    'max_size': 500,
                    'timeout_ms': 200,
                    'deduplicate': True
                },
                'telemetry_ingestion': {
                    'enabled': True,
                    'max_size': 1000,
                    'timeout_ms': 100,
                    'time_window_aggregation': True
                },
                'status_updates': {
                    'enabled': True,
                    'max_size': 200,
                    'timeout_ms': 50,
                    'latest_value_only': True
                }
            },
            
            # Performance monitoring
            'monitoring': {
                'batch_size_distribution': True,
                'processing_time_metrics': True,
                'throughput_metrics': True,
                'error_rate_tracking': True,
                'optimization_recommendations': True
            }
        }
    
    @staticmethod
    def get_connection_reuse() -> Dict[str, Any]:
        """Connection reuse optimization configuration"""
        return {
            # Connection pooling strategy
            'pooling_strategy': {
                'pool_type': 'per_endpoint',  # or 'global', 'per_host'
                'initial_pool_size': 10,
                'max_pool_size': 100,
                'min_idle_connections': 5,
                'max_idle_connections': 20,
                'connection_idle_timeout': 300,  # 5 minutes
                'pool_cleanup_interval': 60     # 1 minute
            },
            
            # Connection lifecycle
            'lifecycle_management': {
                'preemptive_creation': True,
                'connection_validation': {
                    'enabled': True,
                    'validation_query': 'ping',
                    'validation_timeout': 5
                },
                'connection_recycling': {
                    'max_requests_per_connection': 10000,
                    'max_connection_age_seconds': 3600,
                    'recycle_on_error': True
                }
            },
            
            # Protocol-specific reuse
            'protocol_reuse': {
                'http': {
                    'keep_alive': True,
                    'keep_alive_timeout': 300,
                    'max_keep_alive_requests': 1000,
                    'tcp_no_delay': True,
                    'tcp_keep_alive': True
                },
                'mqtt': {
                    'persistent_sessions': True,
                    'session_reuse': True,
                    'connection_sharing': False  # Each device gets own connection
                },
                'websocket': {
                    'connection_sharing': True,
                    'multiplexing': True,
                    'heartbeat_enabled': True,
                    'auto_reconnect': True
                }
            },
            
            # Load distribution
            'load_distribution': {
                'sticky_sessions': False,
                'session_affinity': 'none',  # 'none', 'ip_hash', 'device_id'
                'connection_spreading': True,
                'health_aware_routing': True
            },
            
            # Monitoring and metrics
            'monitoring': {
                'pool_utilization_tracking': True,
                'connection_lifetime_stats': True,
                'reuse_efficiency_metrics': True,
                'error_correlation_analysis': True,
                'performance_impact_tracking': True
            }
        }
    
    @staticmethod
    def get_optimization_monitoring() -> Dict[str, Any]:
        """Protocol optimization monitoring configuration"""
        return {
            # Performance metrics
            'performance_metrics': {
                'latency_percentiles': [50, 90, 95, 99, 99.9],
                'throughput_tracking': True,
                'error_rate_tracking': True,
                'connection_metrics': True,
                'protocol_efficiency': True
            },
            
            # Alerting thresholds
            'alerting': {
                'high_latency_threshold_ms': 100,
                'low_throughput_threshold_rps': 50,
                'high_error_rate_threshold': 0.05,  # 5%
                'connection_pool_exhaustion_threshold': 0.9,
                'protocol_fallback_threshold': 0.1
            },
            
            # Optimization triggers
            'optimization_triggers': {
                'auto_tuning': {
                    'enabled': True,
                    'trigger_conditions': [
                        'high_latency_sustained',
                        'low_throughput_sustained',
                        'high_error_rate',
                        'resource_exhaustion'
                    ],
                    'optimization_actions': [
                        'adjust_batch_sizes',
                        'modify_connection_pools',
                        'switch_protocols',
                        'enable_compression'
                    ]
                },
                'manual_overrides': {
                    'enabled': True,
                    'override_timeout_minutes': 60,
                    'emergency_protocols': ['coap', 'mqtt']
                }
            },
            
            # Reporting
            'reporting': {
                'daily_optimization_report': True,
                'weekly_performance_summary': True,
                'monthly_trend_analysis': True,
                'real_time_dashboard': True,
                'alert_aggregation': True
            }
        }