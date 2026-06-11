# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Database Configuration
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Centralized MongoDB connection configuration for all environments.
"""

import os
import logging
from typing import Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class MongoDBConfig:
    """MongoDB connection configuration and management."""
    
    @staticmethod
    def get_connection_string() -> str:
        """
        Get the appropriate MongoDB connection string based on the environment.
        
        Returns:
            str: MongoDB connection string
        """
        # Check if we're running inside a Docker container
        is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV', '').lower() == 'true'
        
        # Check for explicit MongoDB URI from environment
        mongo_uri = os.getenv('MONGODB_URI')
        if mongo_uri:
            # Replace localhost with container name if running in Docker
            if is_docker and 'localhost' in mongo_uri:
                logger.warning("Detected localhost in MONGODB_URI while running in Docker. Replacing with container name.")
                mongo_uri = mongo_uri.replace('localhost', 'tesa-mongodb')
            return mongo_uri
        
        # Build connection string based on environment
        if is_docker:
            # Running inside Docker - use container name
            host = 'tesa-mongodb'
            port = 27017
        else:
            # Running on host - use localhost with mapped port
            host = 'localhost'
            port = int(os.getenv('MONGODB_PORT', '27018'))  # Default to mapped port
        
        # Get credentials. Canonical env names (MONGODB_*) are what docker-compose
        # and .env provide; MONGO_* are accepted as aliases. No hardcoded password.
        username = os.getenv('MONGODB_USER') or os.getenv('MONGO_USERNAME', 'iot_user')
        password = os.getenv('MONGODB_PASSWORD') or os.getenv('MONGO_PASSWORD', '')
        database = os.getenv('MONGODB_DATABASE') or os.getenv('MONGO_DATABASE', 'tesa_iot')
        auth_source = os.getenv('MONGODB_AUTH_SOURCE') or os.getenv('MONGO_AUTH_SOURCE', 'admin')
        
        # Build connection string
        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={auth_source}"
        else:
            return f"mongodb://{host}:{port}/{database}"
    
    @staticmethod
    def get_client(**kwargs) -> MongoClient:
        """
        Get a MongoDB client with proper configuration.
        
        Args:
            **kwargs: Additional arguments to pass to MongoClient
        
        Returns:
            MongoClient: Configured MongoDB client
        """
        connection_string = MongoDBConfig.get_connection_string()
        
        # Default connection parameters for reliability
        default_params = {
            'serverSelectionTimeoutMS': 5000,
            'connectTimeoutMS': 5000,
            'socketTimeoutMS': 5000,
            'maxPoolSize': 100,
            'minPoolSize': 10,
            'maxIdleTimeMS': 60000,
            'waitQueueTimeoutMS': 10000
        }
        
        # Merge with user-provided parameters
        default_params.update(kwargs)
        
        try:
            client = MongoClient(connection_string, **default_params)
            # Test the connection
            client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB at {connection_string.split('@')[1].split('/')[0]}")
            return client
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @staticmethod
    def get_database(db_name: Optional[str] = None, **kwargs):
        """
        Get a MongoDB database instance.
        
        Args:
            db_name: Database name (defaults to MONGO_DATABASE env var or 'tesa_iot')
            **kwargs: Additional arguments to pass to MongoClient
        
        Returns:
            Database: MongoDB database instance
        """
        client = MongoDBConfig.get_client(**kwargs)
        if not db_name:
            db_name = os.getenv('MONGODB_DATABASE') or os.getenv('MONGO_DATABASE', 'tesa_iot')
        return client[db_name]
    
    @staticmethod
    def get_test_config() -> dict:
        """
        Get configuration for test scripts.
        
        Returns:
            dict: Configuration dictionary with connection details
        """
        is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV', '').lower() == 'true'
        
        return {
            'connection_string': MongoDBConfig.get_connection_string(),
            'host': 'tesa-mongodb' if is_docker else 'localhost',
            'port': 27017 if is_docker else int(os.getenv('MONGODB_PORT', '27018')),
            'database': os.getenv('MONGODB_DATABASE') or os.getenv('MONGO_DATABASE', 'tesa_iot'),
            'username': os.getenv('MONGODB_USER') or os.getenv('MONGO_USERNAME', 'iot_user'),
            'password': os.getenv('MONGODB_PASSWORD') or os.getenv('MONGO_PASSWORD', ''),
            'auth_source': os.getenv('MONGODB_AUTH_SOURCE') or os.getenv('MONGO_AUTH_SOURCE', 'admin'),
            'is_docker': is_docker
        }

# Convenience functions for backward compatibility
def get_mongo_client(**kwargs):
    """Get a MongoDB client (backward compatibility)."""
    return MongoDBConfig.get_client(**kwargs)

def get_mongo_database(db_name: Optional[str] = None, **kwargs):
    """Get a MongoDB database (backward compatibility)."""
    return MongoDBConfig.get_database(db_name, **kwargs)