# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: Dynamic (read from VERSION.txt)
Module: Configuration Management
Build: 2025-06-08 10:55:00 UTC

Centralized configuration management for different environments.

Network Mode Support:
- NETWORK_MODE=host: Uses localhost for all services (remote server deployment)
- NETWORK_MODE=docker: Uses container service names (local docker-compose)
- If NETWORK_MODE not set, auto-detects based on Docker environment

Supported Environment Variables:
- Database Hosts: MONGODB_HOST, REDIS_HOST, POSTGRES_HOST, VAULT_HOST
- Database Ports: MONGODB_PORT, REDIS_PORT, POSTGRES_PORT, VAULT_PORT
- Full URIs: MONGODB_URI, REDIS_URL, POSTGRES_URI, VAULT_ADDR
"""

import os
import logging
from datetime import timedelta
from typing import Dict
from collections import namedtuple

logger = logging.getLogger(__name__)

# Import API version
def get_api_version():
    """Get API version from VERSION.txt"""
    try:
        # Look for VERSION.txt in multiple possible locations
        version_paths = [
            os.path.join(os.path.dirname(__file__), '../../../../VERSION.txt'),
            os.path.join(os.path.dirname(__file__), '../../../VERSION.txt'),
            '/app/VERSION.txt',  # Docker container path
            'VERSION.txt'  # Current directory
        ]
        
        for path in version_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    version = f.read().strip()
                    if version:
                        return version
        
        # Fallback version if file not found
        return "v2025.07-beta.1"
    except Exception as e:
        logger.warning(f"Failed to read VERSION.txt: {e}")
        return "v2025.07-beta.1"

# Immutable configuration structures
SecurityConfig = namedtuple('SecurityConfig', [
    'bcrypt_log_rounds', 'token_expiration_hours', 'max_login_attempts', 
    'lockout_duration', 'max_content_length'
])

DatabaseConfig = namedtuple('DatabaseConfig', [
    'mongodb_uri', 'redis_url', 'postgres_uri', 'connection_timeout'
])

EmailConfig = namedtuple('EmailConfig', [
    'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_use_tls'
])

# Immutable limits and boundaries
SYSTEM_LIMITS = {
    'max_page_size': 100,
    'default_page_size': 20,
    'max_file_size_mb': 16,
    'max_concurrent_connections': 1000,
    'api_rate_limit_per_hour': 3600,
    'max_retry_attempts': 3
}

ALLOWED_FILE_EXTENSIONS = frozenset({'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bin', 'hex'})

# Security validation patterns (immutable)
WEAK_SECRETS = frozenset({
    'CHANGEME_SET_SECRET_KEY_VIA_ENV',
    'CHANGEME_SET_JWT_SECRET_VIA_ENV',
    'CHANGEME_EMQX_WEBHOOK_SECRET',
    'CHANGEME_MTLS_GATEWAY_SECRET',
    'CHANGEME', 'changeme', 'your-secret-key',
    'admin123', 'password', 'secret', 'admin', 'test123'
})

def _get_safe_database_config() -> DatabaseConfig:
    """Get database configuration with fail-safe defaults and multiple connection support."""
    # Check network mode - prefer NETWORK_MODE env var, fallback to Docker detection
    network_mode = os.getenv('NETWORK_MODE', '').lower()
    is_host_network = network_mode == 'host'
    
    # If NETWORK_MODE not set, fallback to Docker environment detection
    if not network_mode:
        is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV', '').lower() == 'true'
        is_host_network = not is_docker
    
    # Get MongoDB URI with robust fallback logic
    mongodb_uri = _get_mongodb_connection_string(is_host_network)
    
    # Get Redis URL with fallback options
    redis_url = _get_redis_connection_string(is_host_network)
    
    # Get PostgreSQL URI with fallback options
    postgres_uri = _get_postgres_connection_string(is_host_network)
    
    return DatabaseConfig(
        mongodb_uri=mongodb_uri,
        redis_url=redis_url,
        postgres_uri=postgres_uri,
        connection_timeout=int(os.getenv('DB_CONNECTION_TIMEOUT', '30'))
    )

def _get_mongodb_connection_string(is_host_network: bool) -> str:
    """Get MongoDB connection string with multiple fallback options."""
    # Priority 1: Check for explicit MONGODB_URI
    mongodb_uri = os.getenv('MONGODB_URI')
    if mongodb_uri:
        logger.info(f"Using explicit MONGODB_URI")
        return mongodb_uri
    
    # Priority 2: Build from individual components
    mongo_user = os.getenv('MONGODB_USER', os.getenv('MONGO_INITDB_ROOT_USERNAME', 'iot_user'))
    mongo_password = os.getenv('MONGODB_PASSWORD', os.getenv('MONGO_INITDB_ROOT_PASSWORD', ''))
    mongo_database = os.getenv('MONGO_INITDB_DATABASE', 'tesa_iot')
    
    # Priority 3: Determine host based on network mode
    mongo_host = os.getenv('MONGODB_HOST')
    if mongo_host:
        # Use explicit host from environment
        primary_host = mongo_host
        mongo_port = os.getenv('MONGODB_PORT', '27017')
        logger.info(f"Using explicit MONGODB_HOST: {primary_host}")
    elif is_host_network:
        # Running in host network mode - use localhost
        primary_host = 'localhost'
        mongo_port = os.getenv('MONGODB_PORT', '27017')
        logger.info("Detected host network mode - using localhost")
    else:
        # Running in docker network mode - use container service names
        mongodb_hosts = [
            'tesa-mongodb',  # Primary service name
            'mongodb',       # Alternative service name
            'mongo'          # Fallback service name
        ]
        primary_host = mongodb_hosts[0]
        mongo_port = '27017'  # Internal container port
        logger.info("Detected docker network mode - using container service names")
    
    # Build connection string with proper parameters
    connection_params = {
        'authSource': 'admin',
        'maxPoolSize': os.getenv('MONGODB_MAX_POOL_SIZE', '100'),
        'minPoolSize': os.getenv('MONGODB_MIN_POOL_SIZE', '10'),
        'maxIdleTimeMS': os.getenv('MONGODB_MAX_IDLE_TIME', '60000'),
        'waitQueueTimeoutMS': os.getenv('MONGODB_WAIT_QUEUE_TIMEOUT', '10000'),
        'maxConnecting': os.getenv('MONGODB_MAX_CONNECTING', '20'),
        'heartbeatFrequencyMS': os.getenv('MONGODB_HEARTBEAT_FREQ', '10000'),
        'serverSelectionTimeoutMS': os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT', '5000'),
        'connectTimeoutMS': '10000',
        'socketTimeoutMS': '20000',
        'retryWrites': 'true',
        'retryReads': 'true'
    }
    
    # Create connection string
    params_string = '&'.join([f'{k}={v}' for k, v in connection_params.items()])
    mongodb_uri = f'mongodb://{mongo_user}:{mongo_password}@{primary_host}:{mongo_port}/{mongo_database}?{params_string}'
    
    logger.info(f"Built MongoDB URI for host: {primary_host}:{mongo_port}")
    return mongodb_uri

def _get_redis_connection_string(is_host_network: bool) -> str:
    """Get Redis connection string with fallback options."""
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return redis_url
    
    redis_password = os.getenv('REDIS_PASSWORD', '')
    
    # Check for explicit Redis host from environment
    redis_host = os.getenv('REDIS_HOST')
    if redis_host:
        # Use explicit host from environment
        redis_port = os.getenv('REDIS_PORT', '6379')
        logger.info(f"Using explicit REDIS_HOST: {redis_host}")
    elif is_host_network:
        # Running in host network mode - use localhost
        redis_host = 'localhost'
        redis_port = os.getenv('REDIS_PORT', '6379')
        logger.info("Detected host network mode - using localhost for Redis")
    else:
        # Running in docker network mode - use container service name
        redis_host = 'tesa-redis'
        redis_port = '6379'
        logger.info("Detected docker network mode - using container service name for Redis")
    
    if redis_password:
        return f'redis://:{redis_password}@{redis_host}:{redis_port}'
    else:
        return f'redis://{redis_host}:{redis_port}'

def _get_postgres_connection_string(is_host_network: bool) -> str:
    """Get PostgreSQL connection string with fallback options."""
    postgres_uri = os.getenv('POSTGRES_URI')
    if postgres_uri:
        return postgres_uri
    
    postgres_user = os.getenv('POSTGRES_USER', 'postgres')
    # SECURITY: no literal fallback. An unset password yields an unusable URI
    # (connection fails closed); production presence is enforced by
    # validate_security_config.
    postgres_password = os.getenv('POSTGRES_PASSWORD', '')
    postgres_db = os.getenv('POSTGRES_DB', 'tesa_telemetry')
    
    # Check for explicit PostgreSQL host from environment
    postgres_host = os.getenv('POSTGRES_HOST')
    if postgres_host:
        # Use explicit host from environment
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        logger.info(f"Using explicit POSTGRES_HOST: {postgres_host}")
    elif is_host_network:
        # Running in host network mode - use localhost
        postgres_host = 'localhost'
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        logger.info("Detected host network mode - using localhost for PostgreSQL")
    else:
        # Running in docker network mode - use container service name
        postgres_host = 'tesa-timescaledb'
        postgres_port = '5432'
        logger.info("Detected docker network mode - using container service name for PostgreSQL")
    
    return f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'

def _get_vault_addr(is_host_network: bool) -> str:
    """Get Vault address with fallback options."""
    vault_addr = os.getenv('VAULT_ADDR')
    if vault_addr:
        return vault_addr
    
    # Check for explicit Vault host from environment
    vault_host = os.getenv('VAULT_HOST')
    vault_port = os.getenv('VAULT_PORT', '8200')
    vault_scheme = os.getenv('VAULT_SCHEME', 'http')
    
    if vault_host:
        # Use explicit host from environment
        logger.info(f"Using explicit VAULT_HOST: {vault_host}")
        return f'{vault_scheme}://{vault_host}:{vault_port}'
    elif is_host_network:
        # Running in host network mode - use localhost
        logger.info("Detected host network mode - using localhost for Vault")
        return f'{vault_scheme}://localhost:{vault_port}'
    else:
        # Running in docker network mode - use container service name
        logger.info("Detected docker network mode - using container service name for Vault")
        return f'{vault_scheme}://tesa-vault:{vault_port}'

def _get_safe_security_config() -> SecurityConfig:
    """Get security configuration with validation."""
    return SecurityConfig(
        bcrypt_log_rounds=max(4, min(15, int(os.getenv('BCRYPT_LOG_ROUNDS', '12')))),
        token_expiration_hours=max(1, min(168, int(os.getenv('TOKEN_EXPIRATION_HOURS', '24')))),  # 1-168 hours
        max_login_attempts=max(3, min(10, int(os.getenv('MAX_LOGIN_ATTEMPTS', '5')))),  # 3-10 attempts
        lockout_duration=max(60, min(3600, int(os.getenv('LOCKOUT_DURATION', '300')))),  # 1-60 minutes
        max_content_length=max(1, min(100, int(os.getenv('MAX_CONTENT_LENGTH_MB', '16')))) * 1024 * 1024
    )

def _get_safe_email_config() -> EmailConfig:
    """Get email configuration with validation."""
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    if smtp_port not in [25, 465, 587, 2525]:  # Common SMTP ports
        smtp_port = 587
    
    return EmailConfig(
        smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        smtp_port=smtp_port,
        smtp_username=os.getenv('SMTP_USERNAME', ''),
        smtp_password=os.getenv('SMTP_PASSWORD', ''),
        smtp_use_tls=os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
    )

class BaseConfig:
    """Base configuration class with defensive programming."""
    # Check network mode for vault configuration
    _network_mode = os.getenv('NETWORK_MODE', '').lower()
    _is_host_network = _network_mode == 'host'
    
    # If NETWORK_MODE not set, fallback to Docker environment detection
    if not _network_mode:
        _is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV', '').lower() == 'true'
        _is_host_network = not _is_docker
    
    # Get immutable configuration structures
    _db_config = _get_safe_database_config()
    _security_config = _get_safe_security_config()
    _email_config = _get_safe_email_config()
    
    # Flask settings. SECURITY: no CHANGEME literal fallback - an unset
    # SECRET_KEY stays empty and validate_security_config fails the boot in
    # production. JWT_SECRET_KEY deliberately does NOT fall back to SECRET_KEY
    # anymore (session-cookie and API-token signing must not share a secret).
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('JWT_SECRET', ''))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=_security_config.token_expiration_hours)
    
    # Database connections (immutable access)
    MONGODB_URI = _db_config.mongodb_uri
    REDIS_URL = _db_config.redis_url
    POSTGRES_URI = _db_config.postgres_uri
    
    # Vault configuration with validation
    VAULT_ADDR = _get_vault_addr(_is_host_network)

    # Helper to read secrets from secure files (never commit)
    @staticmethod
    def _read_file_safe(path: str) -> str:
        try:
            if path and os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read().strip()
        except Exception:
            return ''
        return ''

    @staticmethod
    def _resolve_secure_base() -> str:
        """Resolve secure base directory without hardcoding absolute paths.

        Priority:
        1) Env var TESA_SECURE_BASE or SECURE_BASE_DIR
        2) Repo-local 'secure' directory relative to this file
        3) Empty string (disabled)
        """
        for env_key in ('TESA_SECURE_BASE', 'SECURE_BASE_DIR'):
            val = os.getenv(env_key, '').strip()
            if val:
                return val
        # repo-local: src/python/api/core/config.py -> repo_root/secure
        repo_secure = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../secure'))
        if os.path.isdir(repo_secure):
            return repo_secure
        return ''

    _SECURE_BASE = _resolve_secure_base.__func__()

    # Prefer env, fallback to secure base (repo-local or env-provided)
    API_ROLE_ID = os.getenv('API_ROLE_ID', '') or (
        _read_file_safe.__func__(os.path.join(_SECURE_BASE, 'vault/api/role-id')) if _SECURE_BASE else ''
    )
    API_SECRET_ID = os.getenv('API_SECRET_ID', '') or (
        _read_file_safe.__func__(os.path.join(_SECURE_BASE, 'vault/api/secret-id')) if _SECURE_BASE else ''
    )
    
    # Email configuration (immutable access)
    SMTP_SERVER = _email_config.smtp_server
    SMTP_PORT = _email_config.smtp_port
    SMTP_USERNAME = _email_config.smtp_username
    SMTP_PASSWORD = _email_config.smtp_password
    SMTP_USE_TLS = _email_config.smtp_use_tls
    
    # API settings (immutable)
    API_VERSION = get_api_version()
    API_TITLE = 'TESA IoT Platform API'
    API_DESCRIPTION = 'Enterprise IoT Device Management Platform'
    
    # Security settings (immutable access)
    BCRYPT_LOG_ROUNDS = _security_config.bcrypt_log_rounds
    TOKEN_EXPIRATION_HOURS = _security_config.token_expiration_hours
    MAX_LOGIN_ATTEMPTS = _security_config.max_login_attempts
    LOCKOUT_DURATION = _security_config.lockout_duration
    MAX_CONTENT_LENGTH = _security_config.max_content_length
    
    # Platform admin credentials from environment (NEVER hardcode!)
    PLATFORM_ADMIN_EMAIL = os.getenv('PLATFORM_ADMIN_EMAIL', '')
    PLATFORM_ADMIN_PASSWORD = os.getenv('PLATFORM_ADMIN_PASSWORD', '')
    PLATFORM_ADMIN_USERNAME = os.getenv('PLATFORM_ADMIN_USERNAME', '')
    
    # Single-organization (CE) defaults. The self-host distribution targets one
    # organization; these identify it. Override via environment, never hardcode.
    DEFAULT_ORG_ID = os.getenv('DEFAULT_ORG_ID', 'default')
    DEFAULT_ORG_NAME = os.getenv('DEFAULT_ORG_NAME', 'Default Organization')

    # Organization admin credentials from environment (NEVER hardcode!)
    ORG_ADMIN_EMAIL = os.getenv('ORG_ADMIN_EMAIL', '')
    ORG_ADMIN_PASSWORD = os.getenv('ORG_ADMIN_PASSWORD', '')
    ORG_ADMIN_USERNAME = os.getenv('ORG_ADMIN_USERNAME', '')
    
    # BDH admin credentials from environment (NEVER hardcode!)
    BDH_ADMIN_EMAIL = os.getenv('BDH_ADMIN_EMAIL', '')
    BDH_ADMIN_PASSWORD = os.getenv('BDH_ADMIN_PASSWORD', '')
    BDH_ADMIN_USERNAME = os.getenv('BDH_ADMIN_USERNAME', '')
    
    # File upload settings (immutable)
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = ALLOWED_FILE_EXTENSIONS  # Use immutable frozenset

    # Pagination (immutable)
    DEFAULT_PAGE_SIZE = SYSTEM_LIMITS['default_page_size']
    MAX_PAGE_SIZE = SYSTEM_LIMITS['max_page_size']

    # Rate limiting
    RATELIMIT_STORAGE_URL = _db_config.redis_url
    RATELIMIT_DEFAULT = f"{SYSTEM_LIMITS['api_rate_limit_per_hour']} per hour"

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Protected update feature gate & paths
    PROTECTED_UPDATE_ENABLED = os.getenv('PROTECTED_UPDATE_ENABLED', 'false').lower() == 'true'
    PROTECTED_UPDATE_FEATURE_FLAG = os.getenv('PROTECTED_UPDATE_FLAG', 'protected_update')
    PROTECTED_UPDATE_CLI_PATH = os.getenv(
        'PROTECTED_UPDATE_CLI_PATH',
        '/app/scripts/python_protected_update_cli.py'  # Python CLI (RFC 8152 compliant) - Fixed path
    )
    PROTECTED_UPDATE_LIBRARY_PATH = os.getenv(
        'PROTECTED_UPDATE_LIBRARY_PATH',
        '/opt/tesa/protected-update/libtrustm_update.so'
    )
    PROTECTED_UPDATE_SAMPLES_PATH = os.getenv(
        'PROTECTED_UPDATE_SAMPLES_PATH',
        '/opt/tesa/protected-update/samples'
    )
    PROTECTED_UPDATE_SIGNING_KEY_VAULT_PATH = os.getenv(
        'PROTECTED_UPDATE_SIGNING_KEY_VAULT_PATH',
        'tesa-protected-update/signing-key'
    )
    PROTECTED_UPDATE_SIGNING_ENDPOINT = os.getenv(
        'PROTECTED_UPDATE_SIGNING_ENDPOINT',
        'sign-csr'
    )
    PROTECTED_UPDATE_SIGNING_MOUNT = os.getenv(
        'PROTECTED_UPDATE_SIGNING_MOUNT',
        ''
    )
    PROTECTED_UPDATE_SIGNING_ROLE = os.getenv(
        'PROTECTED_UPDATE_SIGNING_ROLE',
        ''
    )
    PROTECTED_UPDATE_SIGNING_KEY_SECRET_PATH = os.getenv(
        'PROTECTED_UPDATE_SIGNING_KEY_SECRET_PATH',
        ''
    )
    PROTECTED_UPDATE_SIGNING_KEY_SECRET_MOUNT = os.getenv(
        'PROTECTED_UPDATE_SIGNING_KEY_SECRET_MOUNT',
        'secret'
    )
    PROTECTED_UPDATE_SIGNING_KEY_FILE = os.getenv(
        'PROTECTED_UPDATE_SIGNING_KEY_FILE',
        ''
    )
    PROTECTED_UPDATE_DATASET_RETENTION_DAYS = int(os.getenv(
        'PROTECTED_UPDATE_DATASET_RETENTION_DAYS',
        '90'
    ))
    PROTECTED_UPDATE_PIPELINE_INTERVAL_SECONDS = int(os.getenv(
        'PROTECTED_UPDATE_PIPELINE_INTERVAL_SECONDS',
        '5'
    ))
    PROTECTED_UPDATE_CERT_TTL_HOURS = os.getenv('PROTECTED_UPDATE_CERT_TTL_HOURS')
    PROTECTED_UPDATE_SIGNING_MAX_ATTEMPTS = int(os.getenv(
        'PROTECTED_UPDATE_SIGNING_MAX_ATTEMPTS',
        '5'
    ))
    PROTECTED_UPDATE_PUBLISH_MAX_ATTEMPTS = int(os.getenv(
        'PROTECTED_UPDATE_PUBLISH_MAX_ATTEMPTS',
        '5'
    ))
    PROTECTED_UPDATE_MQTT_HOST = os.getenv('PROTECTED_UPDATE_MQTT_HOST', os.getenv('TESA_PUBLIC_MQTT_HOST', os.getenv('DOMAIN', 'localhost')))
    PROTECTED_UPDATE_MQTT_PORT = int(os.getenv('PROTECTED_UPDATE_MQTT_PORT', os.getenv('TESA_PUBLIC_MQTT_TLS_PORT', '8884')))
    PROTECTED_UPDATE_MQTT_USERNAME = os.getenv('PROTECTED_UPDATE_MQTT_USERNAME', os.getenv('MQTT_USERNAME', 'mqtt-bridge'))
    PROTECTED_UPDATE_MQTT_PASSWORD = os.getenv('PROTECTED_UPDATE_MQTT_PASSWORD', os.getenv('MQTT_BRIDGE_PASSWORD', ''))
    PROTECTED_UPDATE_MQTT_CA_PATH = os.getenv('PROTECTED_UPDATE_MQTT_CA_PATH', '/app/certs/chain/ca-chain.crt')
    PROTECTED_UPDATE_MQTT_CLIENT_ID = os.getenv('PROTECTED_UPDATE_MQTT_CLIENT_ID', 'tesa-protected-update-service')
    # Split Topics: Best practice for IoT OTA (RFC 9019 SUIT compliance)
    # When enabled, publishes to separate topics: commands/manifest and commands/fragment
    # Default: True (recommended for new deployments)
    PROTECTED_UPDATE_USE_SPLIT_TOPICS = os.getenv('PROTECTED_UPDATE_USE_SPLIT_TOPICS', 'true').lower() in ('true', '1', 'yes')
    # Delay between fragment publishes (ms) - allows device to process each fragment
    PROTECTED_UPDATE_FRAGMENT_DELAY_MS = int(os.getenv('PROTECTED_UPDATE_FRAGMENT_DELAY_MS', '100'))

    @classmethod
    def get_security_config(cls) -> SecurityConfig:
        """Get immutable security configuration."""
        return cls._security_config
    
    @classmethod
    def get_database_config(cls) -> DatabaseConfig:
        """Get immutable database configuration."""
        return cls._db_config
    
    @classmethod
    def get_email_config(cls) -> EmailConfig:
        """Get immutable email configuration."""
        return cls._email_config

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'

class TestingConfig(BaseConfig):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    MONGODB_URI = os.getenv('TEST_MONGODB_URI', 'mongodb://localhost:27017/tesa_iot_test')
    POSTGRES_URI = os.getenv('TEST_POSTGRES_URI', 'postgresql://localhost:5432/tesa_telemetry_test')

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    # Override with production values from environment
    SECRET_KEY = os.getenv('SECRET_KEY', os.getenv('JWT_SECRET'))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('JWT_SECRET'))
    
    # Enforce HTTPS in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING')
    
    def __init__(self):
        super().__init__()
        # Validate security configuration in production
        Config.validate_security_config()

class Config:
    """Configuration factory."""
    
    configs = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
        'default': ProductionConfig
    }
    
    @classmethod
    def get_config(cls, config_name='default'):
        """Get configuration by name."""
        return cls.configs.get(config_name, cls.configs['default'])

    @staticmethod
    def get_security_config() -> 'SecurityConfig':
        """Return the validated runtime SecurityConfig (bcrypt rounds, lockout, etc.)."""
        return _get_safe_security_config()

    DEFAULT_ORG_ID = os.getenv('DEFAULT_ORG_ID', 'default')
    DEFAULT_ORG_NAME = os.getenv('DEFAULT_ORG_NAME', 'Default Organization')

    # Secrets that must be present and strong when running in production.
    # SECRET_KEY / JWT_SECRET_KEY accept JWT_SECRET as an alias (see ProductionConfig).
    PRODUCTION_REQUIRED_SECRETS = (
        'SECRET_KEY', 'JWT_SECRET_KEY', 'VAULT_ADDR',
        'API_ROLE_ID', 'API_SECRET_ID', 'EMQX_WEBHOOK_SECRET',
    )

    # Variables that must be cryptographically strong (length + not weak/default).
    PRODUCTION_STRONG_SECRETS = (
        'SECRET_KEY', 'JWT_SECRET_KEY', 'EMQX_WEBHOOK_SECRET',
    )

    @staticmethod
    def _resolve_secret(var: str) -> str:
        """Resolve a secret allowing the JWT_SECRET alias used by ProductionConfig."""
        value = os.getenv(var, '').strip()
        if not value and var in ('SECRET_KEY', 'JWT_SECRET_KEY'):
            value = os.getenv('JWT_SECRET', '').strip()
        return value

    @staticmethod
    def validate_security_config(config_name: str = None):
        """Validate that no hardcoded/weak credentials are used in production.

        Driven off the selected configuration (config_name from create_app /
        FLASK_ENV) rather than a separate ENVIRONMENT variable, so the check
        cannot be silently bypassed. Fails CLOSED on missing, short, weak, or
        CHANGEME* secrets.
        """
        if config_name is None:
            config_name = os.getenv('FLASK_ENV') or os.getenv('ENVIRONMENT', 'development')
        config_name = (config_name or '').strip().lower()

        # Derive the production gate from the configuration class that is ACTUALLY
        # selected by Config.get_config (the same call create_app uses), NOT from a
        # separate string allowlist. get_config maps every unknown/typo name
        # (e.g. 'staging', 'prod', 'foobar') to ProductionConfig via the 'default'
        # fallback. A string allowlist would treat those as non-production and skip
        # validation while the app still boots ProductionConfig with empty/CHANGEME
        # secrets -- a fail-OPEN bypass. Gating on the selected class keeps the two
        # in lockstep and fails CLOSED: only explicit development/testing skip.
        selected_config = Config.get_config(config_name)
        is_production = issubclass(selected_config, ProductionConfig)
        if not is_production:
            logger.warning(
                f"Running in '{config_name}' mode - production secret validation skipped"
            )
            return

        missing_vars = []
        for var in Config.PRODUCTION_REQUIRED_SECRETS:
            env_value = Config._resolve_secret(var)
            if not env_value or len(env_value) < 8:
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing or insufficient environment variables in production: {missing_vars}"
            )

        # Database credentials must be configured (either full URI or password).
        if not (os.getenv('POSTGRES_URI') or '').strip() and \
                not (os.getenv('POSTGRES_PASSWORD') or '').strip():
            raise ValueError(
                "POSTGRES_PASSWORD (or POSTGRES_URI) must be set in production; "
                "there is no default database password."
            )

        # Strong-secret enforcement: reject CHANGEME*, weak/default, and short secrets.
        for var in Config.PRODUCTION_STRONG_SECRETS:
            value = Config._resolve_secret(var)
            if value.startswith('CHANGEME'):
                raise ValueError(
                    f"{var} still uses a CHANGEME* placeholder; set a strong secret in production"
                )
            if value.lower() in WEAK_SECRETS:
                raise ValueError(f"Weak or default secret detected for {var} in production")
            if len(value) < 32:
                raise ValueError(f"{var} must be at least 32 characters long in production")
            if len(set(value)) < 8:
                logger.warning(
                    f"{var} has low character diversity - consider a stronger secret"
                )

        logger.info("Security configuration validation passed")
    
    @staticmethod
    def get_admin_credentials() -> Dict[str, Dict[str, str]]:
        """Get admin credentials from environment variables with validation."""
        # Create immutable credential structure
        AdminCredentials = namedtuple('AdminCredentials', ['email', 'password', 'username'])
        
        def _get_safe_credentials(email_var: str, password_var: str, username_var: str, 
                                default_email: str = '', default_username: str = '') -> AdminCredentials:
            """Get credentials with validation and sanitization."""
            email = os.getenv(email_var, default_email).strip()
            password = os.getenv(password_var, '').strip()
            username = os.getenv(username_var, default_username).strip()
            
            # Basic validation
            if email and '@' not in email:
                logger.warning(f"Invalid email format for {email_var}")
                email = default_email
            
            if email and len(email) > 254:  # RFC 5321 limit
                email = email[:254]
            
            if username and len(username) > 100:
                username = username[:100]
            
            return AdminCredentials(email=email, password=password, username=username)
        
        # Get credentials with validation
        platform_admin = _get_safe_credentials(
            'PLATFORM_ADMIN_EMAIL', 'PLATFORM_ADMIN_PASSWORD', 'PLATFORM_ADMIN_USERNAME'
        )
        org_admin = _get_safe_credentials(
            'ORG_ADMIN_EMAIL', 'ORG_ADMIN_PASSWORD', 'ORG_ADMIN_USERNAME'
        )
        bdh_admin = _get_safe_credentials(
            'BDH_ADMIN_EMAIL', 'BDH_ADMIN_PASSWORD', 'BDH_ADMIN_USERNAME'
        )
        
        # Return as dictionary for compatibility, but with validated data
        return {
            'platform_admin': {
                'email': platform_admin.email,
                'password': platform_admin.password,
                'username': platform_admin.username
            },
            'org_admin': {
                'email': org_admin.email,
                'password': org_admin.password,
                'username': org_admin.username
            },
            'bdh_admin': {
                'email': bdh_admin.email,
                'password': bdh_admin.password,
                'username': bdh_admin.username
            }
        }
    
    @staticmethod
    def is_development_mode():
        """Check if running in development mode."""
        return os.getenv('ENVIRONMENT', 'development') == 'development'
