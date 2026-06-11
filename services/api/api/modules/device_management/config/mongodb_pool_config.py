# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - MongoDB Connection Pool Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: MongoDB Pool Configuration
Version: Dynamic (read from VERSION.txt)
Build Date: 2025-07-27

Description:
    Production-ready MongoDB connection pool configuration with:
    - Environment-based configuration
    - Performance tuning
    - Security best practices
    - Monitoring integration
"""

import os
from typing import Dict, Any


class MongoDBPoolConfig:
    """MongoDB connection pool configuration"""
    
    @staticmethod
    def get_pool_config() -> Dict[str, Any]:
        """Get MongoDB pool configuration based on environment"""
        env = os.getenv('ENVIRONMENT', 'production')
        
        # Base configuration
        base_config = {
            # Connection pool sizing
            'minPoolSize': int(os.getenv('MONGODB_MIN_POOL_SIZE', '10')),
            'maxPoolSize': int(os.getenv('MONGODB_MAX_POOL_SIZE', '100')),
            
            # Timeouts (in milliseconds)
            'serverSelectionTimeoutMS': int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT', '5000')),
            'connectTimeoutMS': int(os.getenv('MONGODB_CONNECT_TIMEOUT', '5000')),
            'socketTimeoutMS': int(os.getenv('MONGODB_SOCKET_TIMEOUT', '10000')),
            'maxIdleTimeMS': int(os.getenv('MONGODB_MAX_IDLE_TIME', '30000')),
            'waitQueueTimeoutMS': int(os.getenv('MONGODB_WAIT_QUEUE_TIMEOUT', '5000')),
            
            # Connection behavior
            'retryWrites': True,
            'retryReads': True,
            'directConnection': False,
            
            # Monitoring
            'heartbeatFrequencyMS': int(os.getenv('MONGODB_HEARTBEAT_FREQUENCY', '10000')),
            'appName': 'TESA_IoT_Device_Management',
            
            # Compression
            'compressors': ['zstd', 'snappy', 'zlib'],
            
            # Read/Write preferences
            'readPreference': 'primaryPreferred',
            'readConcernLevel': 'majority',
            'w': 'majority',
            'j': True,  # Journal write concern
            
            # Connection pool behavior
            'maxConnecting': 5,  # Max simultaneous connection attempts
            'minPoolSizeCheckFrequencyMS': 60000,  # Check pool size every minute
        }
        
        # Environment-specific overrides
        if env == 'development':
            base_config.update({
                'minPoolSize': 5,
                'maxPoolSize': 20,
                'serverSelectionTimeoutMS': 10000,
                'readPreference': 'primary'
            })
        elif env == 'staging':
            base_config.update({
                'minPoolSize': 10,
                'maxPoolSize': 50,
                'readPreference': 'primaryPreferred'
            })
        elif env == 'production':
            base_config.update({
                'minPoolSize': 20,
                'maxPoolSize': 120,  # Increased from 100 based on load test
                'serverSelectionTimeoutMS': 3000,
                'readPreference': 'primaryPreferred',
                'readConcernLevel': 'majority',
                # Additional optimizations based on 75% rollout load test
                'maxConnecting': 8,  # Increased from 5
                'waitQueueTimeoutMS': 3000,  # Reduced for faster failure detection
                'socketTimeoutMS': 8000,  # Reduced for better responsiveness
                'maxIdleTimeMS': 20000,  # Reduced idle time
                'heartbeatFrequencyMS': 5000,  # More frequent health checks
            })
        
        return base_config
    
    @staticmethod
    def get_index_config() -> Dict[str, Any]:
        """Get recommended indexes for device collection"""
        return {
            'devices': [
                # Primary lookup indexes
                {
                    'keys': [('device_id', 1), ('org_id', 1)],
                    'options': {'unique': True, 'background': True}
                },
                # Organization queries
                {
                    'keys': [('org_id', 1), ('status', 1), ('created_at', -1)],
                    'options': {'background': True}
                },
                # Search queries
                {
                    'keys': [('org_id', 1), ('name', 'text'), ('serial_number', 'text')],
                    'options': {'background': True}
                },
                # Type and protocol filtering
                {
                    'keys': [('org_id', 1), ('device_type', 1), ('protocol', 1)],
                    'options': {'background': True}
                },
                # Group membership
                {
                    'keys': [('org_id', 1), ('group_ids', 1)],
                    'options': {'background': True}
                },
                # Tag queries
                {
                    'keys': [('org_id', 1), ('tags', 1)],
                    'options': {'background': True}
                },
                # Last seen tracking
                {
                    'keys': [('org_id', 1), ('last_seen', -1)],
                    'options': {'background': True}
                },
                # Device health monitoring index (optimized for analytics)
                {
                    'keys': [('org_id', 1), ('status', 1), ('last_seen', -1), ('device_type', 1)],
                    'options': {'background': True, 'name': 'device_health_monitoring'}
                },
                # Telemetry aggregation optimization index
                {
                    'keys': [('org_id', 1), ('protocol', 1), ('created_at', -1)],
                    'options': {'background': True, 'name': 'telemetry_protocol_time'}
                },
                # Performance monitoring compound index
                {
                    'keys': [('org_id', 1), ('device_type', 1), ('status', 1), ('last_seen', -1)],
                    'options': {'background': True, 'name': 'performance_monitoring_idx'}
                },
                # TTL index for device cleanup (optional)
                {
                    'keys': [('expires_at', 1)],
                    'options': {'expireAfterSeconds': 0, 'sparse': True}
                }
            ]
        }
    
    @staticmethod
    def get_monitoring_config() -> Dict[str, Any]:
        """Get monitoring configuration for connection pool"""
        return {
            'health_check_interval': int(os.getenv('MONGODB_HEALTH_CHECK_INTERVAL', '30')),
            'stats_collection_interval': int(os.getenv('MONGODB_STATS_INTERVAL', '60')),
            'slow_query_threshold_ms': int(os.getenv('MONGODB_SLOW_QUERY_MS', '1000')),
            'pool_exhaustion_threshold': int(os.getenv('MONGODB_POOL_EXHAUSTION_THRESHOLD', '5')),
            'connection_error_threshold': int(os.getenv('MONGODB_ERROR_THRESHOLD', '10')),
            'alert_webhook_url': os.getenv('MONGODB_ALERT_WEBHOOK'),
            'metrics_enabled': os.getenv('MONGODB_METRICS_ENABLED', 'true').lower() == 'true'
        }
    
    @staticmethod
    def get_security_config() -> Dict[str, Any]:
        """Get security configuration for MongoDB connections"""
        return {
            # TLS/SSL Configuration
            'tls': os.getenv('MONGODB_TLS_ENABLED', 'true').lower() == 'true',
            'tlsCAFile': os.getenv('MONGODB_TLS_CA_FILE'),
            'tlsCertificateKeyFile': os.getenv('MONGODB_TLS_CERT_KEY_FILE'),
            'tlsAllowInvalidCertificates': False,
            'tlsAllowInvalidHostnames': False,
            
            # Authentication
            'authMechanism': os.getenv('MONGODB_AUTH_MECHANISM', 'SCRAM-SHA-256'),
            'authSource': os.getenv('MONGODB_AUTH_SOURCE', 'admin'),
            
            # Network security
            'serverApi': '1',  # Stable API version
            'serverApiStrict': True,
            'serverApiDeprecationErrors': True
        }