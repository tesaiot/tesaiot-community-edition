# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Database Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: Dynamic (read from VERSION.txt)
Module: Database Connections
Build: 2025-06-08 10:55:00 UTC

Manages all database connections for the platform.
"""

import os
import logging
import time
import pymongo
import redis
from psycopg2.pool import SimpleConnectionPool
from psycopg2 import OperationalError as PsycopgError
import hvac
from flask import g
from typing import Optional
from functools import wraps
from pymongo.errors import (
    PyMongoError, ConnectionFailure, ServerSelectionTimeoutError,
    AutoReconnect
)
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError
from hvac.exceptions import VaultError, InvalidRequest

# Import enhanced connection pooling
from .connection_pool import pool_manager

logger = logging.getLogger(__name__)

# Immutable fallback configuration for service degradation
FALLBACK_CONFIG = {
    'mongodb': {
        'uri': 'mongodb://localhost:27017/tesa_iot_fallback',
        'timeout': 5,
        'max_retries': 3,
        'retry_delay': 1
    },
    'redis': {
        'uri': 'redis://localhost:6379/0',
        'timeout': 5,
        'max_retries': 3,
        'retry_delay': 1
    },
    'postgres': {
        'uri': 'postgresql://localhost:5432/tesa_fallback',
        'timeout': 10,
        'max_retries': 3,
        'retry_delay': 2
    },
    'vault': {
        'addr': 'http://localhost:8200',
        'timeout': 10,
        'max_retries': 2,
        'retry_delay': 3
    }
}

# Circuit breaker for database connections
class ConnectionCircuitBreaker:
    """Circuit breaker pattern for database connections."""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker transitioning to HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker closed - service restored")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold and self.state != 'OPEN':
                self.state = 'OPEN'
                logger.error(f"Circuit breaker opened due to {self.failure_count} failures")
            raise

def with_graceful_degradation(service_name: str):
    """Decorator for graceful service degradation."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{service_name} service unavailable, activating graceful degradation: {e}")
                # Return None or empty result to signal degraded mode
                return None
        return wrapper
    return decorator

class DatabaseManager:
    """Manages all database connections with defensive programming."""
    
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_uri: Optional[str] = None
        self.redis_client = None
        self.postgres_pool = None
        self.vault_client = None
        self.vault_addr: Optional[str] = None
        self.vault_role_id: Optional[str] = None
        self.vault_secret_id: Optional[str] = None
        self.initialized = False
        self.use_enhanced_pooling = True  # Flag to use enhanced pooling
        
        # Circuit breakers for each service
        self.circuit_breakers = {
            'mongodb': ConnectionCircuitBreaker(failure_threshold=5, timeout=60),
            'redis': ConnectionCircuitBreaker(failure_threshold=3, timeout=30),
            'postgres': ConnectionCircuitBreaker(failure_threshold=4, timeout=45),
            'vault': ConnectionCircuitBreaker(failure_threshold=3, timeout=120)
        }
        
        # Service health status
        self.service_health = {
            'mongodb': True,
            'redis': True,
            'postgres': True,
            'vault': True
        }
    
    @with_graceful_degradation('MongoDB')
    def init_mongodb(self, uri: str, max_retries: int = None) -> bool:
        """Initialize MongoDB connection with retry logic and fail-safe defaults."""
        if max_retries is None:
            max_retries = FALLBACK_CONFIG['mongodb']['max_retries']
        
        # Try to use enhanced pooling first
        if self.use_enhanced_pooling:
            try:
                # Extract database name from URI
                db_name = pymongo.uri_parser.parse_uri(uri).get('database', 'tesa_iot')
                
                # Initialize enhanced MongoDB pool
                if pool_manager.initialize_mongodb_pool(uri, db_name, min_size=5, max_size=50):
                    logger.info("MongoDB initialized with enhanced connection pooling")
                    # Keep handles for fallback logic
                    self.mongo_uri = uri
                    pool = pool_manager.pools.get('mongodb')
                    if pool:
                        try:
                            self.mongo_db = pool.get_sync_database()
                            self.mongo_client = pool.sync_client
                        except Exception:  # pragma: no cover - safety guard
                            self.mongo_db = None
                    return True
            except Exception as e:
                logger.warning(f"Enhanced MongoDB pooling failed, falling back to standard: {e}")
                self.use_enhanced_pooling = False
        
        # Fallback to standard connection
        retry_delay = FALLBACK_CONFIG['mongodb']['retry_delay']
        
        for attempt in range(max_retries):
            try:
                self.mongo_client = pymongo.MongoClient(
                    uri, 
                    serverSelectionTimeoutMS=5000,  # 5 second timeout
                    connectTimeoutMS=5000,          # 5 second connect timeout
                    socketTimeoutMS=10000,          # 10 second socket timeout
                    maxPoolSize=20,                 # Increased connection pool
                    minPoolSize=5,                  # Minimum connections
                    maxIdleTimeMS=30000,           # 30 second idle timeout
                    retryWrites=True,              # Enable retries for resilience
                    retryReads=True,               # Enable read retries
                    heartbeatFrequencyMS=10000     # 10 second heartbeat
                )
                
                # Force connection to verify it works with timeout
                self.mongo_client.admin.command('ping')
                self.mongo_db = self.mongo_client.get_database()
                logger.info(f"MongoDB connection established on attempt {attempt + 1}")
                self.mongo_uri = uri
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError, AutoReconnect) as e:
                logger.warning(f"MongoDB connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"MongoDB connection failed after {max_retries} attempts")
                    return False
                    
            except PyMongoError as e:
                logger.error(f"MongoDB configuration error: {e}")
                return False
                
            except Exception as e:
                logger.error(f"Unexpected MongoDB connection error: {e}")
                return False
                
        return False
    
    def init_redis(self, url, max_retries=3):
        """Initialize Redis connection with retry logic and timeout."""
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.from_url(
                    url, 
                    decode_responses=True,
                    socket_timeout=5,        # 5 second socket timeout
                    socket_connect_timeout=5, # 5 second connect timeout
                    health_check_interval=30, # Health check every 30 seconds
                    retry_on_timeout=True,    # Retry on timeout
                    max_connections=20,       # Connection pool size
                    retry_on_error=[RedisConnectionError]  # Retry on connection errors
                )
                
                # Test connection
                self.redis_client.ping()
                logger.info(f"Redis connection established on attempt {attempt + 1}")
                return True
                
            except (RedisConnectionError, RedisError) as e:
                logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Redis connection failed after {max_retries} attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected Redis connection error: {e}")
                return False
                
        return False
    
    def init_postgres(self, uri, max_retries=3):
        """Initialize PostgreSQL connection pool with retry logic."""
        # Try to use enhanced pooling first
        if self.use_enhanced_pooling:
            try:
                # Initialize enhanced PostgreSQL pool
                if pool_manager.initialize_postgresql_pool(uri, min_conn=5, max_conn=50):
                    logger.info("PostgreSQL initialized with enhanced connection pooling")
                    self.service_health['postgres'] = True
                    return True
            except Exception as e:
                logger.warning(f"Enhanced PostgreSQL pooling failed, falling back to standard: {e}")
                self.use_enhanced_pooling = False
        
        # Fallback to standard pool
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                # Create connection pool with better configuration
                self.postgres_pool = SimpleConnectionPool(
                    minconn=2,      # Minimum connections
                    maxconn=20,     # Maximum connections
                    dsn=uri
                )
                
                # Test connection with timeout
                conn = self.postgres_pool.getconn()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
                    cursor.close()
                    self.postgres_pool.putconn(conn)
                    logger.info(f"PostgreSQL connection pool established on attempt {attempt + 1}")
                    self.service_health['postgres'] = True
                    return True
                else:
                    raise PsycopgError("Failed to get connection from pool")
                    
            except PsycopgError as e:
                logger.warning(f"PostgreSQL connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"PostgreSQL connection failed after {max_retries} attempts")
                    self.service_health['postgres'] = False
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected PostgreSQL connection error: {e}")
                self.service_health['postgres'] = False
                return False
                
        return False
    
    def init_vault(self, addr, role_id, secret_id, max_retries=10):
        """Initialize Vault connection with retry logic and timeout.

        Args:
            addr: Vault server address
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            max_retries: Maximum retry attempts (default: 10, ~90 seconds total)

        Returns:
            bool: True if successfully connected, False otherwise
        """
        retry_delay = 3  # seconds (increased from 2)

        # Persist credentials for reuse (e.g., token renewal)
        self.vault_addr = addr
        self.vault_role_id = role_id
        self.vault_secret_id = secret_id
        
        for attempt in range(max_retries):
            try:
                # Create Vault client with timeout
                self.vault_client = hvac.Client(
                    url=addr,
                    timeout=10,  # 10 second timeout
                    verify=True  # Verify SSL certificates
                )
                
                # Check for VAULT_TOKEN - prefer file-based token from Vault Agent
                vault_token_file = os.getenv('VAULT_TOKEN_FILE')
                vault_token = None

                if vault_token_file and os.path.exists(vault_token_file):
                    try:
                        with open(vault_token_file, 'r') as f:
                            vault_token = f.read().strip()
                        logger.info(f"Loaded Vault token from file: {vault_token_file}")
                    except Exception as e:
                        logger.warning(f"Failed to read Vault token from file: {e}")

                # Fall back to environment variable if file not available
                if not vault_token:
                    vault_token = os.getenv('VAULT_TOKEN')
                
                if role_id and secret_id and not vault_token:
                    # Only try AppRole if no token is provided
                    logger.info(f"Initializing Vault with AppRole authentication (attempt {attempt + 1})")
                    logger.info(f"Role ID: {role_id}, Secret ID: {secret_id[:8]}...")
                    
                    try:
                        response = self.vault_client.auth.approle.login(
                            role_id=role_id,
                            secret_id=secret_id
                        )
                        
                        if response and 'auth' in response and 'client_token' in response['auth']:
                            self.vault_client.token = response['auth']['client_token']
                            
                            # Verify authentication
                            if self.vault_client.is_authenticated():
                                logger.info(f"Vault AppRole authentication successful! Token: {self.vault_client.token[:20]}...")
                                self.service_health['vault'] = True
                                return True
                            else:
                                raise VaultError("Token verification failed")
                        else:
                            raise VaultError("Invalid authentication response")
                            
                    except (VaultError, InvalidRequest) as e:
                        logger.warning(f"Vault AppRole authentication attempt {attempt + 1}/{max_retries} failed: {e}")
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (attempt + 1)
                            logger.info(f"Retrying AppRole authentication in {wait_time} seconds...")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Vault AppRole authentication failed after {max_retries} attempts")
                            # Fall through to token auth if available
                        
                if vault_token:
                    if vault_token_file:
                        logger.info("Using Vault token from file (managed by Vault Agent)")
                    else:
                        logger.warning("Using VAULT_TOKEN from environment (not recommended for production)")
                    self.vault_client.token = vault_token
                    
                    # Verify the token works with timeout
                    try:
                        if self.vault_client.is_authenticated():
                            logger.info("Vault token authentication successful")
                            self.service_health['vault'] = True
                            return True
                        else:
                            raise VaultError("Token authentication failed")
                    except VaultError as e:
                        logger.error(f"Vault token authentication failed: {e}")
                        self.vault_client = None
                        return False
                else:
                    logger.warning("Vault credentials not provided, running in degraded mode")
                    self.vault_client = None
                    self.service_health['vault'] = False
                    return False
                    
            except (VaultError, InvalidRequest) as e:
                logger.warning(f"Vault connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Retrying vault connection in {wait_time} seconds... (Vault may still be unsealing)")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Vault connection failed after {max_retries} attempts (~{max_retries * retry_delay} seconds)")
                    logger.error("This may indicate Vault is not running, sealed, or network issues")
                    self.vault_client = None
                    self.service_health['vault'] = False
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected Vault connection error: {e}")
                self.vault_client = None
                self.service_health['vault'] = False
                return False
                
        return False
    
    def get_postgres_connection(self):
        """Get a PostgreSQL connection from the pool with error handling."""
        if not self.postgres_pool:
            logger.error("PostgreSQL connection pool not initialized")
            # Try to reinitialize the pool
            try:
                from .config import BaseConfig
                config_instance = BaseConfig()
                db_config = config_instance.get_database_config()
                if self.init_postgres(db_config.postgres_uri):
                    logger.info("PostgreSQL pool reinitialized successfully")
                else:
                    logger.error("Failed to reinitialize PostgreSQL pool")
                    return None
            except Exception as e:
                logger.error(f"Error reinitializing PostgreSQL pool: {e}")
                return None
            
        try:
            conn = self.postgres_pool.getconn()
            if conn:
                # Test connection before returning
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.fetchone()
                cursor.close()
                return conn
            else:
                logger.error("Failed to get connection from PostgreSQL pool")
                return None
                
        except PsycopgError as e:
            logger.error(f"PostgreSQL connection pool error: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error getting PostgreSQL connection: {e}")
            return None
    
    def return_postgres_connection(self, conn):
        """Return a PostgreSQL connection to the pool with error handling."""
        if not conn:
            logger.debug("No connection to return to PostgreSQL pool")
            return
            
        # If using enhanced pooling, this method shouldn't be called
        if self.use_enhanced_pooling:
            logger.debug("Enhanced pooling active, connection cleanup handled by context manager")
            # Try to close the connection directly if it's not already closed
            try:
                if hasattr(conn, 'closed') and not conn.closed:
                    conn.close()
            except Exception as e:
                logger.debug(f"Error closing connection during enhanced pooling cleanup: {e}")
            return
            
        if not self.postgres_pool:
            logger.warning("PostgreSQL connection pool not available for returning connection")
            # Try to close the connection directly
            try:
                if hasattr(conn, 'closed') and not conn.closed:
                    conn.close()
            except Exception as e:
                logger.error(f"Error closing orphaned connection: {e}")
            return
            
        try:
            # Check if connection is still valid before returning
            if not conn.closed:
                self.postgres_pool.putconn(conn)
            else:
                logger.debug("Connection was closed, not returning to pool")
                
        except PsycopgError as e:
            logger.error(f"Error returning connection to PostgreSQL pool: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error returning PostgreSQL connection: {e}")
    
    def close_all(self):
        """Close all database connections with error handling."""
        # Close enhanced pools if using them
        if self.use_enhanced_pooling:
            try:
                pool_manager.close_all()
                logger.info("Enhanced connection pools closed")
            except Exception as e:
                logger.error(f"Error closing enhanced pools: {e}")
        
        # Close standard connections
        # Close MongoDB connection
        if self.mongo_client is not None:
            try:
                self.mongo_client.close()
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
                
        # Close Redis connection
        if self.redis_client is not None:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
                
        # Close PostgreSQL connection pool
        if self.postgres_pool is not None:
            try:
                self.postgres_pool.closeall()
                logger.info("PostgreSQL connection pool closed")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection pool: {e}")
                
        # Reset state
        self.mongo_client = None
        self.mongo_db = None
        self.redis_client = None
        self.postgres_pool = None
        self.vault_client = None
        self.initialized = False

# Global database manager instance
db_manager = DatabaseManager()

def init_databases(app):
    """Initialize all database connections."""
    config = app.config
    
    # Initialize MongoDB
    db_manager.init_mongodb(config['MONGODB_URI'])
    
    # Initialize Redis
    db_manager.init_redis(config['REDIS_URL'])
    
    # Initialize PostgreSQL
    db_manager.init_postgres(config['POSTGRES_URI'])
    
    # Initialize Vault
    vault_addr = config['VAULT_ADDR']
    role_id = config.get('API_ROLE_ID')
    secret_id = config.get('API_SECRET_ID')
    
    logger.info(f"Initializing Vault with addr={vault_addr}")
    logger.info(f"API_ROLE_ID present: {bool(role_id)}")
    logger.info(f"API_SECRET_ID present: {bool(secret_id)}")
    
    db_manager.init_vault(vault_addr, role_id, secret_id)
    
    db_manager.initialized = True
    
    # Start connection pool monitoring if using enhanced pooling
    if db_manager.use_enhanced_pooling:
        pool_manager.start_monitoring()
        logger.info("Connection pool monitoring started")
    
    # Run database initialization service
    mongo_db = get_db()
    if mongo_db is not None:
        logger.info("Running database initialization service...")
        from ..services.database_init_service import initialize_database
        try:
            if initialize_database(mongo_db):
                logger.info("Database initialization completed successfully")
            else:
                logger.warning("Database initialization completed with warnings")
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            # Continue anyway - don't fail startup
    
    # Setup teardown handlers
    @app.teardown_appcontext
    def close_db(error):
        """Close database connections on teardown."""
        # Handle enhanced pooling cleanup
        if hasattr(g, 'postgres_conn_mgr'):
            try:
                # Exit the context manager properly
                g.postgres_conn_mgr.__exit__(None, None, None)
                delattr(g, 'postgres_conn_mgr')
                if hasattr(g, 'postgres_conn'):
                    delattr(g, 'postgres_conn')
            except Exception as e:
                logger.error(f"Error closing enhanced PostgreSQL connection: {e}")
        # Handle standard pooling cleanup
        elif hasattr(g, 'postgres_conn'):
            db_manager.return_postgres_connection(g.postgres_conn)
            delattr(g, 'postgres_conn')

def get_db():
    """Get MongoDB database instance with connection validation."""
    # Try enhanced pooling first
    if db_manager.use_enhanced_pooling:
        try:
            db = pool_manager.get_mongodb_sync_db()
            if db is not None:
                return db
        except RuntimeError as exc:
            logger.warning(f"Enhanced MongoDB pool failed: {exc}")
            # Attempt to re-initialise the pool on demand (common under hot reloads)
            try:
                mongo_uri = db_manager.mongo_uri or os.getenv('MONGODB_URI')
                if mongo_uri:
                    db_name = pymongo.uri_parser.parse_uri(mongo_uri).get('database', 'tesa_iot')
                    if pool_manager.initialize_mongodb_pool(mongo_uri, db_name, min_size=5, max_size=50):
                        logger.info("MongoDB pool reinitialised successfully")
                        db_manager.mongo_uri = mongo_uri
                        db = pool_manager.get_mongodb_sync_db()
                        if db is not None:
                            # Keep a direct handle for fallback paths
                            db_manager.mongo_db = db
                            pool = pool_manager.pools.get('mongodb')
                            if pool:
                                db_manager.mongo_client = getattr(pool, 'sync_client', None)
                            return db
            except Exception as reinit_exc:  # pragma: no cover - defensive path
                logger.error(f"MongoDB pool reinitialisation failed: {reinit_exc}")
        except Exception as e:
            logger.warning(f"Enhanced MongoDB pool failed: {e}")

    # Fallback to standard connection
    if db_manager.mongo_db is None:
        logger.error("MongoDB database not initialized")
        return None
        
    try:
        # Validate connection with a quick ping
        db_manager.mongo_client.admin.command('ping')
        return db_manager.mongo_db
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error(f"MongoDB connection validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating MongoDB connection: {e}")
        return None

def get_redis():
    """Get Redis client instance with connection validation."""
    if db_manager.redis_client is None:
        logger.error("Redis client not initialized")
        return None
        
    try:
        # Validate connection with a quick ping
        db_manager.redis_client.ping()
        return db_manager.redis_client
    except (RedisConnectionError, RedisError) as e:
        logger.error(f"Redis connection validation failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating Redis connection: {e}")
        return None


# Alias for backward compatibility with Device Management module
get_redis_client = get_redis


def get_postgres_conn():
    """Get PostgreSQL connection from pool with error handling."""
    # Try enhanced pooling first
    if db_manager.use_enhanced_pooling:
        try:
            # Store connection manager in g for proper cleanup
            if not hasattr(g, 'postgres_conn_mgr'):
                g.postgres_conn_mgr = pool_manager.get_postgresql_connection()
                g.postgres_conn = g.postgres_conn_mgr.__enter__()
            return g.postgres_conn
        except Exception as e:
            logger.warning(f"Enhanced PostgreSQL pool failed: {e}")
            # Fallback to standard pool
            db_manager.use_enhanced_pooling = False
    
    # Fallback to standard pool
    if not hasattr(g, 'postgres_conn') or g.postgres_conn is None:
        try:
            g.postgres_conn = db_manager.get_postgres_connection()
            if not g.postgres_conn:
                logger.error("Failed to get PostgreSQL connection from pool")
                return None
        except Exception as e:
            logger.error(f"Error getting PostgreSQL connection: {e}")
            return None
    return g.postgres_conn

def _refresh_vault_token_from_file():
    """Reload Vault token from file if VAULT_TOKEN_FILE is set.

    This ensures we always use the latest token from Vault Agent,
    providing automatic token renewal without requiring API restart.

    Returns:
        bool: True if token was refreshed, False otherwise.
    """
    vault_token_file = os.getenv('VAULT_TOKEN_FILE')
    if not vault_token_file or not os.path.exists(vault_token_file):
        return False

    if not db_manager.vault_client:
        return False

    try:
        with open(vault_token_file, 'r') as f:
            new_token = f.read().strip()

        if not new_token:
            logger.warning("Vault token file is empty")
            return False

        current_token = db_manager.vault_client.token
        if current_token != new_token:
            logger.info("Vault token refreshed from file (Vault Agent renewed token)")
            db_manager.vault_client.token = new_token
            return True
    except Exception as e:
        logger.warning(f"Failed to refresh Vault token from file: {e}")

    return False


# Track token refresh attempts and timing
_last_token_refresh_time = 0
_TOKEN_REFRESH_INTERVAL_SECONDS = 60  # Refresh from file every 60 seconds minimum
_last_vault_recovery_attempt = 0
_VAULT_RECOVERY_COOLDOWN_SECONDS = 30  # Minimum seconds between recovery attempts


def _force_refresh_vault_token() -> bool:
    """Force refresh Vault token from file, bypassing cache.

    Best Practice: Read the latest token from Vault Agent's sink file.
    Vault Agent automatically renews tokens before expiry, so the file
    always contains a valid token (assuming Vault Agent is healthy).

    Returns:
        bool: True if token was refreshed and validated successfully.
    """
    global _last_token_refresh_time

    vault_token_file = os.getenv('VAULT_TOKEN_FILE', '/vault/token/api-token')

    if not vault_token_file or not os.path.exists(vault_token_file):
        logger.warning(f"Vault token file not found: {vault_token_file}")
        return False

    try:
        with open(vault_token_file, 'r') as f:
            new_token = f.read().strip()

        if not new_token or len(new_token) < 20:
            logger.warning("Vault token file is empty or invalid")
            return False

        if db_manager.vault_client:
            old_token = db_manager.vault_client.token
            if old_token != new_token:
                logger.info("🔄 Refreshing Vault token from file (Vault Agent token detected)")
                db_manager.vault_client.token = new_token
                _last_token_refresh_time = time.time()

                # Validate the new token
                try:
                    if db_manager.vault_client.is_authenticated():
                        logger.info("✅ Vault token refresh successful - token is valid")
                        db_manager.service_health['vault'] = True
                        return True
                    else:
                        logger.warning("New token loaded but authentication check failed")
                        return False
                except Exception as auth_err:
                    logger.warning(f"Token validation error: {auth_err}")
                    return False
            else:
                # Token unchanged, but validate it
                try:
                    if db_manager.vault_client.is_authenticated():
                        _last_token_refresh_time = time.time()
                        return True
                except Exception:
                    pass
                return False
        return False

    except Exception as e:
        logger.error(f"Failed to force refresh Vault token: {e}")
        return False


def _trigger_vault_agent_token_refresh(max_wait_seconds: int = 15) -> bool:
    """Trigger Vault Agent to regenerate token when current token is invalid.

    This is the FALLBACK recovery mechanism when _force_refresh_vault_token()
    fails. It uses Docker Python SDK to restart vault-agent container.

    Args:
        max_wait_seconds: Maximum time to wait for new token after restart

    Returns:
        bool: True if recovery was successful and new valid token is available

    Safety:
        - Uses cooldown to prevent rapid-fire restart attempts
        - Uses Docker Python SDK (more reliable than subprocess)
        - Validates new token before declaring success
    """
    global _last_vault_recovery_attempt

    # Check cooldown to prevent rapid-fire recovery attempts
    current_time = time.time()
    if current_time - _last_vault_recovery_attempt < _VAULT_RECOVERY_COOLDOWN_SECONDS:
        logger.debug("Vault recovery attempted too recently, skipping")
        return False

    _last_vault_recovery_attempt = current_time

    vault_token_file = os.getenv('VAULT_TOKEN_FILE', '/vault/token/api-token')
    vault_agent_container = os.getenv('VAULT_AGENT_CONTAINER', 'tesa-vault-agent')

    try:
        import docker
        docker_client = docker.from_env()

        # Get the current token's mtime for comparison
        old_mtime = 0
        if os.path.exists(vault_token_file):
            old_mtime = os.path.getmtime(vault_token_file)

        logger.warning(f"🔄 Triggering Vault Agent token recovery (restarting {vault_agent_container})...")

        try:
            container = docker_client.containers.get(vault_agent_container)
            container.restart(timeout=10)
            logger.info(f"✅ Vault Agent container restarted, waiting for new token...")
        except docker.errors.NotFound:
            logger.error(f"Vault Agent container '{vault_agent_container}' not found")
            return False
        except docker.errors.APIError as api_err:
            logger.error(f"Docker API error restarting vault-agent: {api_err}")
            return False

        # Wait for new token file to be written
        wait_interval = 1
        waited = 0
        while waited < max_wait_seconds:
            time.sleep(wait_interval)
            waited += wait_interval

            if os.path.exists(vault_token_file):
                new_mtime = os.path.getmtime(vault_token_file)
                if new_mtime > old_mtime:
                    # Token file was updated, try to use it
                    if _force_refresh_vault_token():
                        logger.info(f"✅ Vault token recovery SUCCESSFUL!")
                        return True

        logger.error(f"Vault token recovery timed out after {max_wait_seconds}s")
        return False

    except ImportError:
        logger.error("Docker Python SDK not available - cannot trigger Vault Agent recovery")
        return False
    except Exception as e:
        logger.error(f"Vault Agent token recovery failed: {e}")
        return False


def get_vault_client():
    """Get Vault client instance with authentication validation and lazy initialization.

    This function supports lazy initialization: if Vault was not available during
    startup, it will attempt to connect when first needed.

    Token Refresh: Automatically reads latest token from VAULT_TOKEN_FILE before
    validating authentication, ensuring Vault Agent token renewals are picked up.
    """
    # If vault_client is None, try to initialize it (lazy init)
    if db_manager.vault_client is None:
        logger.warning("Vault client not initialized; attempting lazy initialization...")
        if db_manager.vault_addr and (db_manager.vault_role_id or os.getenv('VAULT_TOKEN')):
            # Try AppRole auth first
            if db_manager.vault_role_id and db_manager.vault_secret_id:
                logger.info("Attempting lazy Vault initialization with AppRole credentials")
                if db_manager.init_vault(db_manager.vault_addr, db_manager.vault_role_id, db_manager.vault_secret_id, max_retries=5):
                    logger.info("Lazy Vault initialization successful!")
                    return db_manager.vault_client
            # Fallback to token if available
            elif os.getenv('VAULT_TOKEN'):
                logger.info("Attempting lazy Vault initialization with token")
                if db_manager.init_vault(db_manager.vault_addr, None, None, max_retries=5):
                    logger.info("Lazy Vault initialization successful!")
                    return db_manager.vault_client
        logger.error("Lazy Vault initialization failed or credentials unavailable")
        return None

    # Refresh token from file in case Vault Agent has renewed it
    # This is the key to automatic token renewal without API restart
    _refresh_vault_token_from_file()

    try:
        # Validate authentication status
        if db_manager.vault_client.is_authenticated():
            return db_manager.vault_client
        else:
            logger.warning("Vault client not authenticated; attempting re-authentication")
            # Refresh token again before re-auth attempt
            if _refresh_vault_token_from_file():
                # Token was refreshed, try authentication check again
                if db_manager.vault_client.is_authenticated():
                    logger.info("Vault authentication successful after token refresh")
                    return db_manager.vault_client
            if db_manager.vault_addr and (db_manager.vault_role_id or os.getenv('VAULT_TOKEN')):
                # Try AppRole re-auth first
                if db_manager.vault_role_id and db_manager.vault_secret_id:
                    if db_manager.init_vault(db_manager.vault_addr, db_manager.vault_role_id, db_manager.vault_secret_id, max_retries=5):
                        return db_manager.vault_client
                # Fallback to token if available
                elif os.getenv('VAULT_TOKEN'):
                    if db_manager.init_vault(db_manager.vault_addr, None, None, max_retries=5):
                        return db_manager.vault_client

            # AUTO-RECOVERY Layer 1: Force refresh token from file
            logger.warning("🔄 Attempting token refresh from file (Layer 1)...")
            if _force_refresh_vault_token():
                logger.info("✅ Token refresh from file successful!")
                return db_manager.vault_client

            # AUTO-RECOVERY Layer 2: Restart vault-agent as last resort
            logger.warning("🔄 Token refresh failed, attempting vault-agent restart (Layer 2)...")
            if _trigger_vault_agent_token_refresh():
                logger.info("✅ Vault auto-recovery via container restart successful!")
                return db_manager.vault_client

            logger.error("Vault re-authentication and auto-recovery failed")
            return None
    except VaultError as e:
        logger.error(f"Vault authentication validation failed: {e}")
        # AUTO-RECOVERY: Try Layer 1 first (token refresh), then Layer 2 (container restart)
        logger.warning("🔄 VaultError detected, attempting recovery...")
        if _force_refresh_vault_token():
            logger.info("✅ Token refresh successful after VaultError!")
            return db_manager.vault_client
        if _trigger_vault_agent_token_refresh():
            logger.info("✅ Vault auto-recovery successful after VaultError!")
            return db_manager.vault_client
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating Vault client: {e}")
        return None

def get_postgres():
    """Get PostgreSQL connection with error handling."""
    return get_postgres_conn()  # Use the same enhanced logic

def get_vault():
    """Get Vault client instance with validation."""
    return get_vault_client()  # Use the validated version
