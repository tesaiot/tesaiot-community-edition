# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Enhanced Database Connection Pooling
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Module: Enhanced Connection Pool Management
Version: v2025.07-beta.1
Build Date: 2025-07-04

Description:
    Provides robust connection pooling for MongoDB and PostgreSQL/TimescaleDB
    with advanced features:
    - Thread-safe connection management
    - Health checks and monitoring
    - Automatic retry and reconnection
    - Connection pool statistics
    - Graceful degradation
"""

import time
import logging
import threading
import json
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import motor.motor_asyncio
import pymongo
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class PoolStatistics:
    """Connection pool statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    total_wait_time: float = 0.0
    max_wait_time: float = 0.0
    connection_errors: List[str] = field(default_factory=list)
    last_error_time: Optional[datetime] = None
    pool_exhaustion_count: int = 0
    health_check_failures: int = 0


class ConnectionPoolMonitor:
    """Monitor and track connection pool health"""
    
    def __init__(self, name: str):
        self.name = name
        self.stats = PoolStatistics()
        self.lock = threading.Lock()
        self.health_check_interval = 30  # seconds
        self.last_health_check = datetime.now()
        
    def record_connection_acquired(self, wait_time: float):
        """Record successful connection acquisition"""
        with self.lock:
            self.stats.total_requests += 1
            self.stats.active_connections += 1
            self.stats.idle_connections = max(0, self.stats.idle_connections - 1)
            self.stats.total_wait_time += wait_time
            self.stats.max_wait_time = max(self.stats.max_wait_time, wait_time)
            
    def record_connection_released(self):
        """Record connection release"""
        with self.lock:
            self.stats.active_connections = max(0, self.stats.active_connections - 1)
            self.stats.idle_connections += 1
            
    def record_connection_error(self, error: str):
        """Record connection error"""
        with self.lock:
            self.stats.failed_connections += 1
            self.stats.connection_errors.append(f"{datetime.now()}: {error}")
            # Keep only last 100 errors
            if len(self.stats.connection_errors) > 100:
                self.stats.connection_errors = self.stats.connection_errors[-100:]
            self.stats.last_error_time = datetime.now()
            
    def record_pool_exhaustion(self):
        """Record pool exhaustion event"""
        with self.lock:
            self.stats.pool_exhaustion_count += 1
            
    def record_health_check_failure(self):
        """Record health check failure"""
        with self.lock:
            self.stats.health_check_failures += 1
            
    def get_stats(self) -> Dict[str, Any]:
        """Get current pool statistics"""
        with self.lock:
            avg_wait_time = (
                self.stats.total_wait_time / self.stats.total_requests
                if self.stats.total_requests > 0 else 0
            )
            return {
                "pool_name": self.name,
                "total_connections": self.stats.total_connections,
                "active_connections": self.stats.active_connections,
                "idle_connections": self.stats.idle_connections,
                "failed_connections": self.stats.failed_connections,
                "total_requests": self.stats.total_requests,
                "average_wait_time": avg_wait_time,
                "max_wait_time": self.stats.max_wait_time,
                "pool_exhaustion_count": self.stats.pool_exhaustion_count,
                "health_check_failures": self.stats.health_check_failures,
                "last_error_time": self.stats.last_error_time.isoformat() if self.stats.last_error_time else None,
                "recent_errors": self.stats.connection_errors[-10:]  # Last 10 errors
            }


class EnhancedPostgreSQLPool:
    """Enhanced PostgreSQL/TimescaleDB connection pool with monitoring"""
    
    def __init__(self, dsn: str, min_conn: int = 2, max_conn: int = 20):
        self.dsn = dsn
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.pool = None
        self.monitor = ConnectionPoolMonitor("PostgreSQL")
        self.health_check_thread = None
        self.running = False
        self.lock = threading.Lock()
        
        # Initialize the pool
        self._initialize_pool()
        
    def _initialize_pool(self):
        """Initialize the connection pool with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.pool = ThreadedConnectionPool(
                    self.min_conn,
                    self.max_conn,
                    self.dsn,
                    cursor_factory=None,  # Use default cursor
                    connect_timeout=10,
                    options='-c statement_timeout=30000'  # 30 second statement timeout
                )
                
                # Test the pool
                conn = self.pool.getconn()
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
                self.pool.putconn(conn)
                
                self.monitor.stats.total_connections = self.max_conn
                self.monitor.stats.idle_connections = self.min_conn
                
                # Start health check thread
                self._start_health_check()
                
                logger.info(f"PostgreSQL connection pool initialized: min={self.min_conn}, max={self.max_conn}")
                return
                
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL pool (attempt {attempt + 1}/{max_retries}): {e}")
                self.monitor.record_connection_error(str(e))
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    raise
                    
    def _start_health_check(self):
        """Start background health check thread"""
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        
    def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                time.sleep(self.monitor.health_check_interval)
                if not self.running:
                    break
                    
                # Perform health check
                start_time = time.time()
                conn = self.pool.getconn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    self.pool.putconn(conn)
                    
                    check_time = time.time() - start_time
                    if check_time > 1.0:  # Slow response warning
                        logger.warning(f"PostgreSQL health check slow: {check_time:.2f}s")
                        
                except Exception as e:
                    self.pool.putconn(conn, close=True)
                    raise e
                    
            except Exception as e:
                logger.error(f"PostgreSQL health check failed: {e}")
                self.monitor.record_health_check_failure()
                
    @contextmanager
    def get_connection(self, timeout: float = 5.0):
        """Get a connection from the pool with monitoring"""
        start_time = time.time()
        conn = None
        
        try:
            # Try to get connection with timeout
            conn = self.pool.getconn()
            wait_time = time.time() - start_time
            
            if wait_time > timeout:
                raise TimeoutError(f"Connection acquisition took too long: {wait_time:.2f}s")
                
            self.monitor.record_connection_acquired(wait_time)
            
            # Set connection properties
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            conn.autocommit = False
            
            yield conn
            
            # Commit if no exception
            if not conn.closed:
                conn.commit()
                
        except Exception as e:
            # Rollback on error
            if conn and not conn.closed:
                try:
                    conn.rollback()
                except:
                    pass
                    
            logger.error(f"PostgreSQL connection error: {e}")
            self.monitor.record_connection_error(str(e))
            raise
            
        finally:
            # Return connection to pool
            if conn:
                try:
                    # Check if connection is still valid
                    if conn.closed:
                        self.pool.putconn(conn, close=True)
                    else:
                        cursor = conn.cursor()
                        cursor.execute('SELECT 1')
                        cursor.close()
                        self.pool.putconn(conn)
                except:
                    # Connection is bad, close it
                    self.pool.putconn(conn, close=True)
                    
                self.monitor.record_connection_released()
                
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return self.monitor.get_stats()
        
    def close(self):
        """Close the connection pool"""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL connection pool closed")


class EnhancedMongoDBPool:
    """Enhanced MongoDB connection pool with Motor for async support"""
    
    def __init__(self, uri: str, db_name: str, min_pool_size: int = 5, max_pool_size: int = 50):
        self.uri = uri
        self.db_name = db_name
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        
        # Synchronous client for backward compatibility
        self.sync_client = None
        self.sync_db = None
        
        # Async client for high performance
        self.async_client = None
        self.async_db = None
        
        self.monitor = ConnectionPoolMonitor("MongoDB")
        self.health_check_thread = None
        self.running = False
        
        # Initialize connections
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize both sync and async MongoDB clients"""
        # Common connection options
        connection_options = {
            'minPoolSize': self.min_pool_size,
            'maxPoolSize': self.max_pool_size,
            'maxIdleTimeMS': 30000,  # 30 seconds
            'waitQueueTimeoutMS': 5000,  # 5 seconds
            'serverSelectionTimeoutMS': 5000,
            'connectTimeoutMS': 5000,
            'socketTimeoutMS': 10000,
            'retryWrites': True,
            'retryReads': True,
            'heartbeatFrequencyMS': 10000,
            'appName': 'TESA_IoT_Platform',
            'compressors': ['zstd', 'snappy', 'zlib'],  # Enable compression
        }
        
        try:
            # Initialize synchronous client
            self.sync_client = pymongo.MongoClient(self.uri, **connection_options)
            
            # Test connection
            self.sync_client.admin.command('ping')
            self.sync_db = self.sync_client[self.db_name]
            
            # Initialize async client
            self.async_client = motor.motor_asyncio.AsyncIOMotorClient(
                self.uri, **connection_options
            )
            self.async_db = self.async_client[self.db_name]
            
            self.monitor.stats.total_connections = self.max_pool_size
            self.monitor.stats.idle_connections = self.min_pool_size
            
            # Start health check
            self._start_health_check()
            
            logger.info(f"MongoDB connection pool initialized: min={self.min_pool_size}, max={self.max_pool_size}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB pool: {e}")
            self.monitor.record_connection_error(str(e))
            raise
            
    def _start_health_check(self):
        """Start background health check thread"""
        self.running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        
    def _health_check_loop(self):
        """Background health check loop"""
        while self.running:
            try:
                time.sleep(self.monitor.health_check_interval)
                if not self.running:
                    break
                    
                # Perform health check
                start_time = time.time()
                self.sync_client.admin.command('ping')
                
                check_time = time.time() - start_time
                if check_time > 1.0:  # Slow response warning
                    logger.warning(f"MongoDB health check slow: {check_time:.2f}s")
                    
            except Exception as e:
                logger.error(f"MongoDB health check failed: {e}")
                self.monitor.record_health_check_failure()
                
                # Try to reconnect
                try:
                    self._initialize_clients()
                except:
                    pass
                    
    def get_sync_database(self):
        """Get synchronous database instance"""
        try:
            # Validate connection
            self.sync_client.admin.command('ping')
            self.monitor.record_connection_acquired(0)
            return self.sync_db
        except Exception as e:
            logger.error(f"MongoDB sync connection error: {e}")
            self.monitor.record_connection_error(str(e))
            
            # Try to reconnect
            try:
                self._initialize_clients()
                return self.sync_db
            except:
                return None
                
    def get_async_database(self):
        """Get async database instance"""
        self.monitor.record_connection_acquired(0)
        return self.async_db
        
    async def execute_async(self, collection_name: str, operation: str, *args, **kwargs):
        """Execute async MongoDB operation with monitoring"""
        start_time = time.time()
        
        try:
            collection = self.async_db[collection_name]
            method = getattr(collection, operation)
            result = await method(*args, **kwargs)
            
            execution_time = time.time() - start_time
            if execution_time > 1.0:
                logger.warning(f"Slow MongoDB operation: {operation} took {execution_time:.2f}s")
                
            return result
            
        except Exception as e:
            logger.error(f"MongoDB async operation error: {e}")
            self.monitor.record_connection_error(str(e))
            raise
            
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        stats = self.monitor.get_stats()
        
        # Add MongoDB-specific stats
        if self.sync_client:
            try:
                server_status = self.sync_client.admin.command('serverStatus')
                stats['mongodb_connections'] = server_status.get('connections', {})
                stats['mongodb_opcounters'] = server_status.get('opcounters', {})
            except:
                pass
                
        return stats
        
    def close(self):
        """Close all connections"""
        self.running = False
        if self.health_check_thread:
            self.health_check_thread.join(timeout=5)
            
        if self.sync_client:
            self.sync_client.close()
            
        if self.async_client:
            self.async_client.close()
            
        logger.info("MongoDB connection pool closed")


class ConnectionPoolManager:
    """Central manager for all connection pools"""
    
    def __init__(self):
        self.pools: Dict[str, Any] = {}
        self.monitors: Dict[str, ConnectionPoolMonitor] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.stats_collection_interval = 60  # seconds
        self.stats_thread = None
        self.running = False
        
    def initialize_postgresql_pool(self, dsn: str, min_conn: int = 2, max_conn: int = 20):
        """Initialize PostgreSQL connection pool"""
        try:
            # Check if pool already exists
            if 'postgresql' in self.pools:
                logger.info("PostgreSQL pool already initialized")
                return True
            
            pool = EnhancedPostgreSQLPool(dsn, min_conn, max_conn)
            self.pools['postgresql'] = pool
            self.monitors['postgresql'] = pool.monitor
            logger.info("PostgreSQL pool initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pool: {e}")
            # Clean up on failure
            if 'postgresql' in self.pools:
                del self.pools['postgresql']
            if 'postgresql' in self.monitors:
                del self.monitors['postgresql']
            return False
            
    def initialize_mongodb_pool(self, uri: str, db_name: str, min_size: int = 5, max_size: int = 50):
        """Initialize MongoDB connection pool"""
        try:
            pool = EnhancedMongoDBPool(uri, db_name, min_size, max_size)
            self.pools['mongodb'] = pool
            self.monitors['mongodb'] = pool.monitor
            logger.info("MongoDB pool initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB pool: {e}")
            return False
            
    def get_postgresql_connection(self, timeout: float = 5.0):
        """Get PostgreSQL connection context manager"""
        pool = self.pools.get('postgresql')
        if not pool:
            logger.error("PostgreSQL pool not initialized - attempting to reinitialize")
            # Try to reinitialize the pool with default configuration
            try:
                import os
                # No embedded credentials: the connection string must come from the
                # environment (POSTGRES_URI). Skip reinit if it is not configured.
                postgres_uri = os.getenv('POSTGRES_URI')
                if postgres_uri and self.initialize_postgresql_pool(postgres_uri):
                    pool = self.pools.get('postgresql')
                    if pool:
                        return pool.get_connection(timeout)
                raise RuntimeError("PostgreSQL pool reinitialization failed")
            except Exception as e:
                logger.error(f"Failed to reinitialize PostgreSQL pool: {e}")
                raise RuntimeError("PostgreSQL pool not initialized")
        return pool.get_connection(timeout)
        
    def get_mongodb_sync_db(self):
        """Get MongoDB synchronous database"""
        pool = self.pools.get('mongodb')
        if not pool:
            raise RuntimeError("MongoDB pool not initialized")
        return pool.get_sync_database()
        
    def get_mongodb_async_db(self):
        """Get MongoDB async database"""
        pool = self.pools.get('mongodb')
        if not pool:
            raise RuntimeError("MongoDB pool not initialized")
        return pool.get_async_database()
        
    def start_monitoring(self):
        """Start pool monitoring"""
        self.running = True
        self.stats_thread = threading.Thread(
            target=self._collect_stats_loop,
            daemon=True
        )
        self.stats_thread.start()
        
    def _collect_stats_loop(self):
        """Collect and log pool statistics periodically"""
        while self.running:
            try:
                time.sleep(self.stats_collection_interval)
                if not self.running:
                    break
                    
                # Collect stats from all pools
                all_stats = {}
                for name, pool in self.pools.items():
                    try:
                        all_stats[name] = pool.get_stats()
                    except Exception as e:
                        logger.error(f"Failed to get stats for {name}: {e}")
                        
                # Log statistics
                logger.info(f"Connection pool statistics: {json.dumps(all_stats, indent=2)}")
                
                # Check for issues
                for name, stats in all_stats.items():
                    if stats.get('pool_exhaustion_count', 0) > 0:
                        logger.warning(f"{name} pool exhaustion detected: {stats['pool_exhaustion_count']} times")
                        
                    if stats.get('health_check_failures', 0) > 5:
                        logger.error(f"{name} health check failures: {stats['health_check_failures']}")
                        
            except Exception as e:
                logger.error(f"Error in stats collection: {e}")
                
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics from all pools"""
        all_stats = {}
        for name, pool in self.pools.items():
            try:
                all_stats[name] = pool.get_stats()
            except Exception as e:
                logger.error(f"Failed to get stats for {name}: {e}")
                all_stats[name] = {"error": str(e)}
                
        return all_stats
        
    def close_all(self):
        """Close all connection pools"""
        self.running = False
        
        if self.stats_thread:
            self.stats_thread.join(timeout=5)
            
        for name, pool in self.pools.items():
            try:
                pool.close()
                logger.info(f"Closed {name} connection pool")
            except Exception as e:
                logger.error(f"Error closing {name} pool: {e}")
                
        self.executor.shutdown(wait=True)
        logger.info("All connection pools closed")


# Global connection pool manager instance
pool_manager = ConnectionPoolManager()