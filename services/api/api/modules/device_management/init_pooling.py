# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Management Pool Initialization
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Connection Pool Initialization
Version: Dynamic (read from VERSION.txt)
Build Date: 2025-07-27

Description:
    Initializes enhanced MongoDB connection pooling for the Device Management module
"""

import os
import logging
import asyncio

from ...core.connection_pool import pool_manager
from .config.mongodb_pool_config import MongoDBPoolConfig
from .monitoring.pool_health_monitor import pool_health_monitor

logger = logging.getLogger(__name__)


class DeviceManagementPooling:
    """Manages connection pooling for Device Management module"""
    
    def __init__(self):
        self.initialized = False
        self.pool_config = MongoDBPoolConfig()
        
    async def initialize(self) -> bool:
        """Initialize connection pooling with monitoring"""
        try:
            # Get MongoDB URI from environment
            mongodb_uri = os.getenv('MONGODB_URI')
            if not mongodb_uri:
                logger.error("MONGODB_URI not set in environment")
                return False
            
            # Extract database name from URI or use default
            import pymongo
            parsed_uri = pymongo.uri_parser.parse_uri(mongodb_uri)
            db_name = parsed_uri.get('database', 'tesa_iot')
            
            # Get pool configuration
            pool_config = self.pool_config.get_pool_config()
            
            # Initialize MongoDB pool with enhanced configuration
            success = pool_manager.initialize_mongodb_pool(
                uri=mongodb_uri,
                db_name=db_name,
                min_size=pool_config['minPoolSize'],
                max_size=pool_config['maxPoolSize']
            )
            
            if not success:
                logger.error("Failed to initialize MongoDB connection pool")
                return False
            
            # Apply additional pool configuration
            await self._configure_pool(pool_config)
            
            # Create indexes
            await self._ensure_indexes()
            
            # Start health monitoring
            monitoring_config = self.pool_config.get_monitoring_config()
            if monitoring_config['metrics_enabled']:
                alert_webhook = monitoring_config.get('alert_webhook_url')
                pool_health_monitor.alert_webhook_url = alert_webhook
                await pool_health_monitor.start_monitoring()
                logger.info("Connection pool health monitoring started")
            
            self.initialized = True
            logger.info("Device Management connection pooling initialized successfully")
            
            # Log pool configuration
            logger.info(f"MongoDB Pool Configuration: "
                       f"min={pool_config['minPoolSize']}, "
                       f"max={pool_config['maxPoolSize']}, "
                       f"timeout={pool_config['serverSelectionTimeoutMS']}ms")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing connection pooling: {e}")
            return False
    
    async def _configure_pool(self, pool_config: dict):
        """Apply additional pool configuration"""
        try:
            # Get MongoDB pool from pool manager
            mongodb_pool = pool_manager.pools.get('mongodb')
            if not mongodb_pool:
                logger.warning("MongoDB pool not found in pool manager")
                return
            
            # Update client options if possible
            if hasattr(mongodb_pool, 'sync_client') and mongodb_pool.sync_client:
                # Log current pool stats
                server_info = mongodb_pool.sync_client.server_info()
                logger.info(f"MongoDB server version: {server_info.get('version')}")
                
        except Exception as e:
            logger.error(f"Error configuring pool: {e}")
    
    async def _ensure_indexes(self):
        """Ensure required indexes exist"""
        try:
            # Get database
            db = pool_manager.get_mongodb_sync_db()
            if db is None:
                logger.warning("Could not get database for index creation")
                return
            
            # Get index configuration
            index_config = self.pool_config.get_index_config()
            
            for collection_name, indexes in index_config.items():
                collection = db[collection_name]
                
                for index in indexes:
                    try:
                        # Create index in background
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            collection.create_index,
                            index['keys'],
                            **index['options']
                        )
                        logger.info(f"Created index on {collection_name}: {index['keys']}")
                    except Exception as e:
                        # Index might already exist
                        logger.debug(f"Index creation skipped: {e}")
            
            logger.info("Database indexes verified/created")
            
        except Exception as e:
            logger.error(f"Error ensuring indexes: {e}")
    
    async def shutdown(self):
        """Shutdown connection pooling and monitoring"""
        try:
            # Stop health monitoring
            if pool_health_monitor.running:
                await pool_health_monitor.stop_monitoring()
            
            # Get final pool stats
            final_stats = pool_manager.get_all_stats()
            logger.info(f"Final pool statistics: {final_stats}")
            
            self.initialized = False
            logger.info("Device Management connection pooling shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during pooling shutdown: {e}")
    
    def get_pool_stats(self) -> dict:
        """Get current pool statistics"""
        try:
            stats = {
                'initialized': self.initialized,
                'pool_stats': pool_manager.get_all_stats(),
                'health_summary': pool_health_monitor.get_pool_health_summary()
            }
            return stats
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {'error': str(e)}


# Global pooling manager instance
device_pooling = DeviceManagementPooling()


async def init_device_management_pooling():
    """Initialize Device Management connection pooling"""
    return await device_pooling.initialize()


async def shutdown_device_management_pooling():
    """Shutdown Device Management connection pooling"""
    return await device_pooling.shutdown()