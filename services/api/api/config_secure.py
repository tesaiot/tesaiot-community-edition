# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Secure Configuration for TESA IoT Platform API
This module demonstrates how to use the SecretManager for secure credential handling
"""

import os
from datetime import timedelta
from utils.secret_manager import get_secret_manager

# Initialize secret manager
secret_manager = get_secret_manager()


class Config:
    """Base configuration with secure secret handling"""
    
    # Flask Configuration
    SECRET_KEY = secret_manager.get_jwt_secret()
    FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
    DEBUG = FLASK_ENV == 'development'
    
    # API Configuration
    API_HOST = os.environ.get('API_HOST', '0.0.0.0')
    API_PORT = int(os.environ.get('API_PORT', 5566))
    
    # Database Configuration with Secrets
    MONGODB_URI = secret_manager.get_database_uri('mongodb')
    POSTGRES_URI = secret_manager.get_database_uri('postgresql')
    REDIS_URL = secret_manager.get_database_uri('redis')
    
    # JWT Configuration
    JWT_SECRET_KEY = secret_manager.get_jwt_secret()
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Vault Configuration
    VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://vault:8200')
    VAULT_TOKEN = secret_manager.get_vault_token()
    VAULT_PKI_PATH = os.environ.get('VAULT_PKI_PATH', 'pki-iot')
    
    # Admin Configuration
    PLATFORM_ADMIN_EMAIL = os.environ.get('PLATFORM_ADMIN_EMAIL', 'admin@example.com')
    PLATFORM_ADMIN_USERNAME = os.environ.get('PLATFORM_ADMIN_USERNAME', 'platform_admin')
    PLATFORM_ADMIN_PASSWORD = secret_manager.get_admin_password('platform')
    
    ORG_ADMIN_EMAIL = os.environ.get('ORG_ADMIN_EMAIL', 'admin@tesa.local')
    ORG_ADMIN_USERNAME = os.environ.get('ORG_ADMIN_USERNAME', 'org_admin')
    ORG_ADMIN_PASSWORD = secret_manager.get_admin_password('org')
    
    BDH_ADMIN_EMAIL = os.environ.get('BDH_ADMIN_EMAIL', 'admin@example.com')
    BDH_ADMIN_USERNAME = os.environ.get('BDH_ADMIN_USERNAME', 'admin')
    BDH_ADMIN_PASSWORD = secret_manager.get_admin_password('bdh')
    
    # Connection Pool Configuration
    ENABLE_CONNECTION_POOLING = os.environ.get('ENABLE_CONNECTION_POOLING', 'true').lower() == 'true'
    POSTGRES_POOL_SIZE = int(os.environ.get('POSTGRES_POOL_SIZE', 20))
    POSTGRES_MAX_OVERFLOW = int(os.environ.get('POSTGRES_MAX_OVERFLOW', 10))
    POSTGRES_POOL_TIMEOUT = int(os.environ.get('POSTGRES_POOL_TIMEOUT', 30))
    POSTGRES_POOL_RECYCLE = int(os.environ.get('POSTGRES_POOL_RECYCLE', 3600))
    
    # Redis Configuration
    ENABLE_REDIS_CACHE = os.environ.get('ENABLE_REDIS_CACHE', 'true').lower() == 'true'
    REDIS_CACHE_TTL = int(os.environ.get('REDIS_CACHE_TTL', 300))
    REDIS_POOL_MAX_CONNECTIONS = int(os.environ.get('REDIS_POOL_MAX_CONNECTIONS', 50))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_secrets(cls):
        """Validate that all required secrets are available"""
        required_secrets = [
            ('JWT_SECRET_KEY', cls.JWT_SECRET_KEY),
            ('MONGODB_URI', cls.MONGODB_URI),
            ('POSTGRES_URI', cls.POSTGRES_URI),
            ('REDIS_URL', cls.REDIS_URL),
        ]
        
        missing = []
        for name, value in required_secrets:
            if not value or value == 'None':
                missing.append(name)
        
        if missing:
            raise ValueError(f"Missing required secrets: {', '.join(missing)}")
        
        return True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development can use less secure defaults if secrets are not available
    # This allows developers to run without full secret setup
    def __init__(self):
        # Check if we're in true development mode (no secrets)
        if not os.path.exists('/run/secrets') and not os.path.exists('./secrets'):
            print("WARNING: Running in development mode without secrets!")
            print("         Using insecure default credentials.")
            # Override with development values from environment. SECURITY: no
            # literal fallbacks - missing secrets stay empty and fail closed.
            self.JWT_SECRET_KEY = os.getenv('JWT_SECRET', '')

            # Build MongoDB URI from environment variables
            mongo_host = os.getenv('MONGODB_HOST', 'tesa-mongodb')
            mongo_port = os.getenv('MONGO_PORT', '27017')
            mongo_db = os.getenv('MONGO_INITDB_DATABASE', 'tesa_iot')
            self.MONGODB_URI = f'mongodb://{mongo_host}:{mongo_port}/{mongo_db}'
            
            # Build PostgreSQL URI from environment variables  
            postgres_host = os.getenv('POSTGRES_HOST', 'tesa-timescaledb')
            postgres_port = os.getenv('POSTGRES_PORT', '5432')
            postgres_user = os.getenv('POSTGRES_USER', 'postgres')
            postgres_password = os.getenv('POSTGRES_PASSWORD', '')
            postgres_db = os.getenv('POSTGRES_DB', 'tesa_telemetry')
            self.POSTGRES_URI = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
            
            # Build Redis URL from environment variables
            redis_host = os.getenv('REDIS_HOST', 'tesa-redis')
            redis_port = os.getenv('REDIS_PORT', '6379')
            redis_password = os.getenv('REDIS_PASSWORD', '')
            if redis_password:
                self.REDIS_URL = f'redis://:{redis_password}@{redis_host}:{redis_port}'
            else:
                self.REDIS_URL = f'redis://{redis_host}:{redis_port}'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    def __init__(self):
        # Production MUST have secrets
        try:
            self.validate_secrets()
        except ValueError as e:
            print(f"FATAL: {e}")
            print("Production requires proper secret configuration!")
            raise


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory databases for testing
    MONGODB_URI = 'mongodb://localhost:27017/tesa_iot_test'
    POSTGRES_URI = 'sqlite:///:memory:'
    REDIS_URL = 'redis://localhost:6379/1'
    
    # Fixed test credentials
    JWT_SECRET_KEY = 'test-jwt-secret-key'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'production')
    
    config_class = config.get(env, config['default'])
    
    # Instantiate and return
    return config_class()


# Example usage in app.py:
# from config_secure import get_config
# app.config.from_object(get_config())