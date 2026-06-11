# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Cache Optimization Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Cache Optimization Configuration for 75% Rollout
Version: Dynamic (read from VERSION.txt)
Build Date: 2025-07-27

Description:
    Enhanced cache configuration based on 75% rollout load testing insights:
    - Memory allocation improvements
    - Cache warming strategies  
    - TTL optimization
    - Hit rate optimization
"""

import os
from typing import Dict, Any
from enum import Enum


class CacheLevel(Enum):
    """Cache level priorities"""
    L1_CRITICAL = "l1_critical"      # Most frequently accessed
    L2_FREQUENT = "l2_frequent"      # Frequently accessed
    L3_NORMAL = "l3_normal"          # Normal access pattern
    L4_BACKGROUND = "l4_background"  # Background/analytics


class CacheOptimizationConfig:
    """Enhanced cache configuration for optimal performance"""
    
    @staticmethod
    def get_redis_config() -> Dict[str, Any]:
        """Get optimized Redis configuration based on load test insights"""
        env = os.getenv('ENVIRONMENT', 'production')
        
        base_config = {
            # Memory optimization (based on 73.8% utilization in load test)
            'maxmemory': os.getenv('REDIS_MAX_MEMORY', '1.5GB'),  # Increased from default
            'maxmemory-policy': 'allkeys-lfu',  # LFU for better hit rates
            
            # Connection pool optimization
            'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '200')),
            'connection_pool_kwargs': {
                'socket_keepalive': True,
                'socket_keepalive_options': {},
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True,
                'health_check_interval': 30
            },
            
            # Persistence optimization
            'save': [
                (900, 1),    # Save after 900 sec if at least 1 key changed
                (300, 10),   # Save after 300 sec if at least 10 keys changed
                (60, 10000)  # Save after 60 sec if at least 10000 keys changed
            ],
            
            # Network optimization
            'tcp-backlog': 511,
            'tcp-keepalive': 300,
            'timeout': 0,  # No timeout for persistent connections
            
            # Performance tuning
            'hash-max-ziplist-entries': 512,
            'hash-max-ziplist-value': 64,
            'list-max-ziplist-size': -2,
            'set-max-intset-entries': 512,
            'zset-max-ziplist-entries': 128,
            'zset-max-ziplist-value': 64,
            
            # Lazy freeing for better performance
            'lazyfree-lazy-eviction': True,
            'lazyfree-lazy-expire': True,
            'lazyfree-lazy-server-del': True,
            
            # Client output buffer limits
            'client-output-buffer-limit': [
                'normal 0 0 0',
                'replica 256mb 64mb 60',
                'pubsub 32mb 8mb 60'
            ]
        }
        
        # Environment-specific overrides
        if env == 'production':
            base_config.update({
                'maxmemory': '2GB',  # Production gets more memory
                'max_connections': 300,
                'rdbcompression': True,
                'rdbchecksum': True
            })
        elif env == 'staging':
            base_config.update({
                'maxmemory': '1GB',
                'max_connections': 150
            })
        elif env == 'development':
            base_config.update({
                'maxmemory': '512MB',
                'max_connections': 50,
                'save': []  # No persistence in dev
            })
        
        return base_config
    
    @staticmethod
    def get_cache_strategies() -> Dict[str, Dict[str, Any]]:
        """Get cache strategies for different data types"""
        return {
            # Device metadata cache - critical for API performance
            'device_metadata': {
                'level': CacheLevel.L1_CRITICAL,
                'ttl_seconds': 1800,  # 30 minutes
                'max_size_mb': 200,
                'eviction_policy': 'lfu',
                'preload': True,
                'key_pattern': 'device:meta:{org_id}:{device_id}',
                'warming_queries': [
                    {
                        'collection': 'devices',
                        'filter': {'status': {'$in': ['online', 'active']}},
                        'projection': {'_id': 1, 'device_id': 1, 'name': 1, 'status': 1, 'device_type': 1},
                        'priority': 'high'
                    }
                ]
            },
            
            # Device status cache - frequent updates
            'device_status': {
                'level': CacheLevel.L1_CRITICAL,
                'ttl_seconds': 300,   # 5 minutes
                'max_size_mb': 100,
                'eviction_policy': 'lru',
                'preload': True,
                'key_pattern': 'device:status:{org_id}:{device_id}',
                'batch_update': True,
                'batch_size': 100
            },
            
            # Device telemetry cache - recent data
            'device_telemetry': {
                'level': CacheLevel.L2_FREQUENT,
                'ttl_seconds': 600,   # 10 minutes
                'max_size_mb': 300,
                'eviction_policy': 'lru',
                'key_pattern': 'telemetry:recent:{org_id}:{device_id}',
                'compression': True
            },
            
            # Device groups cache
            'device_groups': {
                'level': CacheLevel.L2_FREQUENT,
                'ttl_seconds': 3600,  # 1 hour
                'max_size_mb': 50,
                'eviction_policy': 'lfu',
                'key_pattern': 'groups:{org_id}:{group_id}',
                'preload': True
            },
            
            # Analytics cache - longer TTL, larger data
            'analytics_data': {
                'level': CacheLevel.L3_NORMAL,
                'ttl_seconds': 7200,  # 2 hours
                'max_size_mb': 400,
                'eviction_policy': 'lru',
                'key_pattern': 'analytics:{org_id}:{query_hash}',
                'compression': True,
                'async_refresh': True
            },
            
            # API response cache
            'api_responses': {
                'level': CacheLevel.L2_FREQUENT,
                'ttl_seconds': 180,   # 3 minutes
                'max_size_mb': 150,
                'eviction_policy': 'lru',
                'key_pattern': 'api:response:{endpoint}:{params_hash}',
                'compression': True
            },
            
            # Search results cache
            'search_results': {
                'level': CacheLevel.L3_NORMAL,
                'ttl_seconds': 900,   # 15 minutes
                'max_size_mb': 100,
                'eviction_policy': 'lru',
                'key_pattern': 'search:{org_id}:{query_hash}',
                'compression': True
            }
        }
    
    @staticmethod
    def get_warming_config() -> Dict[str, Any]:
        """Get cache warming configuration based on load test insights"""
        return {
            # Warming schedule
            'schedule': {
                'startup': {
                    'enabled': True,
                    'timeout_seconds': 120,
                    'parallel_workers': 5,
                    'priorities': ['device_metadata', 'device_status', 'device_groups']
                },
                'periodic': {
                    'enabled': True,
                    'interval_seconds': 1800,  # Every 30 minutes
                    'max_duration_seconds': 300,
                    'priorities': ['device_metadata', 'analytics_data']
                },
                'demand': {
                    'enabled': True,
                    'threshold_hit_rate': 0.7,  # Warm if hit rate drops below 70%
                    'threshold_response_time_ms': 50  # Warm if response time > 50ms
                }
            },
            
            # Warming strategies
            'strategies': {
                'predictive': {
                    'enabled': True,
                    'ml_model_path': '/opt/cache_prediction_model.pkl',
                    'prediction_window_minutes': 60,
                    'confidence_threshold': 0.8
                },
                'pattern_based': {
                    'enabled': True,
                    'historical_days': 7,
                    'pattern_detection_interval': 3600  # 1 hour
                },
                'user_behavior': {
                    'enabled': True,
                    'session_analysis': True,
                    'prefetch_depth': 3
                }
            },
            
            # Monitoring
            'monitoring': {
                'hit_rate_alerting': {
                    'threshold': 0.65,  # Alert if hit rate < 65%
                    'window_minutes': 15
                },
                'memory_alerting': {
                    'threshold_percent': 85,  # Alert if memory > 85%
                    'window_minutes': 5
                },
                'eviction_alerting': {
                    'threshold_per_minute': 100,  # Alert if > 100 evictions/min
                    'window_minutes': 10
                }
            }
        }
    
    @staticmethod
    def get_ttl_optimization() -> Dict[str, Any]:
        """Get TTL optimization based on data access patterns"""
        return {
            # Dynamic TTL adjustment
            'dynamic_ttl': {
                'enabled': True,
                'base_factors': {
                    'access_frequency': 0.4,  # 40% weight
                    'data_volatility': 0.3,   # 30% weight
                    'business_priority': 0.2,  # 20% weight
                    'system_load': 0.1        # 10% weight
                },
                'adjustment_interval_seconds': 300,
                'max_ttl_multiplier': 3.0,
                'min_ttl_multiplier': 0.5
            },
            
            # TTL strategies by data type
            'strategies': {
                'static_data': {
                    'base_ttl': 3600,
                    'max_ttl': 86400,
                    'volatility_factor': 0.1
                },
                'semi_static_data': {
                    'base_ttl': 1800,
                    'max_ttl': 7200,
                    'volatility_factor': 0.3
                },
                'dynamic_data': {
                    'base_ttl': 300,
                    'max_ttl': 1800,
                    'volatility_factor': 0.7
                },
                'real_time_data': {
                    'base_ttl': 60,
                    'max_ttl': 300,
                    'volatility_factor': 0.9
                }
            },
            
            # Cache invalidation
            'invalidation': {
                'strategies': ['tag_based', 'dependency_graph', 'time_based'],
                'tag_patterns': {
                    'device_data': ['device:{device_id}', 'org:{org_id}', 'type:{device_type}'],
                    'analytics': ['analytics', 'org:{org_id}', 'timeframe:{timeframe}'],
                    'api_responses': ['api', 'endpoint:{endpoint}', 'version:{api_version}']
                },
                'cascade_invalidation': True,
                'async_invalidation': True
            }
        }
    
    @staticmethod
    def get_compression_config() -> Dict[str, Any]:
        """Get compression configuration for cache optimization"""
        return {
            'algorithms': {
                'default': 'zstd',  # Best compression ratio and speed
                'fallbacks': ['lz4', 'gzip', 'none'],
                'per_data_type': {
                    'json': 'zstd',
                    'binary': 'lz4',
                    'text': 'gzip',
                    'large_objects': 'zstd'
                }
            },
            'thresholds': {
                'min_size_bytes': 1024,     # Don't compress < 1KB
                'max_size_bytes': 10485760,  # Don't compress > 10MB
                'compression_ratio_threshold': 0.8  # Skip if compression < 20%
            },
            'performance': {
                'compression_level': {
                    'zstd': 3,    # Balanced speed/ratio
                    'gzip': 6,    # Standard level
                    'lz4': 1      # Fast compression
                },
                'dictionary_enabled': True,
                'dictionary_size_kb': 64,
                'adaptive_compression': True
            }
        }
    
    @staticmethod
    def get_monitoring_config() -> Dict[str, Any]:
        """Get cache monitoring configuration"""
        return {
            'metrics': {
                'collection_interval_seconds': 30,
                'retention_hours': 168,  # 7 days
                'aggregation_levels': ['1m', '5m', '1h', '1d'],
                'custom_metrics': [
                    'cache_hit_rate_by_level',
                    'cache_memory_utilization_by_strategy',
                    'cache_eviction_rate_by_policy',
                    'cache_warming_effectiveness',
                    'ttl_optimization_impact'
                ]
            },
            'alerting': {
                'channels': ['webhook', 'email', 'slack'],
                'rules': [
                    {
                        'name': 'low_hit_rate',
                        'condition': 'hit_rate < 0.7',
                        'severity': 'warning',
                        'cooldown_minutes': 15
                    },
                    {
                        'name': 'high_memory_usage',
                        'condition': 'memory_usage > 0.85',
                        'severity': 'critical',
                        'cooldown_minutes': 5
                    },
                    {
                        'name': 'high_eviction_rate',
                        'condition': 'eviction_rate > 100/min',
                        'severity': 'warning',
                        'cooldown_minutes': 10
                    }
                ]
            },
            'dashboards': {
                'cache_performance': {
                    'panels': [
                        'hit_rate_trend',
                        'memory_utilization',
                        'response_time_percentiles',
                        'eviction_patterns',
                        'warming_effectiveness'
                    ]
                },
                'cache_health': {
                    'panels': [
                        'connection_pool_status',
                        'redis_cluster_health',
                        'cache_level_distribution',
                        'error_rates',
                        'performance_anomalies'
                    ]
                }
            }
        }