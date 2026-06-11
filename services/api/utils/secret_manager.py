# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Secret Manager for TESA IoT Platform
Handles reading secrets from Docker secrets or environment variables
"""

import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SecretManager:
    """Manages secrets for the application"""
    
    def __init__(self, secrets_path: str = "/run/secrets"):
        self.secrets_path = secrets_path
        self._cache: Dict[str, str] = {}
        
    def read_secret(self, secret_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Read a secret from Docker secret file or environment variable
        
        Priority:
        1. Docker secret file (/run/secrets/<secret_name>)
        2. Environment variable with _FILE suffix (<SECRET_NAME>_FILE)
        3. Environment variable (<SECRET_NAME>)
        4. Default value
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]
            
        # Try Docker secret file
        secret_file = os.path.join(self.secrets_path, secret_name.lower())
        if os.path.exists(secret_file):
            try:
                with open(secret_file, 'r') as f:
                    value = f.read().strip()
                    self._cache[secret_name] = value
                    return value
            except Exception as e:
                logger.warning(f"Failed to read secret file {secret_file}: {e}")
        
        # Try environment variable with _FILE suffix
        env_file_var = f"{secret_name.upper()}_FILE"
        if env_file_var in os.environ:
            try:
                with open(os.environ[env_file_var], 'r') as f:
                    value = f.read().strip()
                    self._cache[secret_name] = value
                    return value
            except Exception as e:
                logger.warning(f"Failed to read file from {env_file_var}: {e}")
        
        # Try direct environment variable
        env_var = secret_name.upper()
        if env_var in os.environ:
            value = os.environ[env_var]
            self._cache[secret_name] = value
            return value
            
        # Return default
        if default is not None:
            self._cache[secret_name] = default
        return default
    
    def get_database_uri(self, db_type: str) -> str:
        """
        Construct database URI with secrets
        """
        if db_type == "mongodb":
            # Use environment variables ONLY - no hardcoded values!
            mongodb_uri = os.environ.get("MONGODB_URI")
            if mongodb_uri:
                return mongodb_uri
            
            # Build URI from individual env vars
            host = os.environ.get("MONGODB_HOST")
            port = os.environ.get("MONGODB_PORT", "27017")  # Default MongoDB port
            user = os.environ.get("MONGODB_USER")
            password = os.environ.get("MONGODB_PASSWORD")
            database = os.environ.get("MONGODB_DATABASE", "tesa_iot")
            
            if not all([host, user, password]):
                raise ValueError(f"Missing MongoDB configuration. Check environment variables: MONGODB_HOST={host}, MONGODB_USER={user}, MONGODB_PASSWORD={'***' if password else None}")
            
            return f"mongodb://{user}:{password}@{host}:{port}/{database}?authSource=admin"
            
        elif db_type == "postgresql":
            # Use environment variables ONLY - no hardcoded values!
            # First try complete URI from env
            postgres_uri = os.environ.get("POSTGRES_URI")
            if postgres_uri:
                return postgres_uri
            
            # Build URI from individual env vars if no complete URI
            host = os.environ.get("POSTGRES_HOST")
            port = os.environ.get("POSTGRES_PORT", "5432")  # Default port is standard
            user = os.environ.get("POSTGRES_USER")
            password = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("TIMESCALE_PASSWORD")
            db = os.environ.get("POSTGRES_DB") or os.environ.get("POSTGRES_DATABASE")
            
            if not all([host, user, password, db]):
                raise ValueError(f"Missing PostgreSQL configuration. Check environment variables: POSTGRES_HOST={host}, POSTGRES_USER={user}, POSTGRES_PASSWORD={'***' if password else None}, POSTGRES_DB={db}")
            
            return f"postgresql://{user}:{password}@{host}:{port}/{db}"
            
        elif db_type == "redis":
            # Use environment variables ONLY - no hardcoded values!
            redis_url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_URI")
            if redis_url:
                return redis_url
            
            # Build URI from individual env vars
            host = os.environ.get("REDIS_HOST")
            port = os.environ.get("REDIS_PORT", "6379")  # Default Redis port
            password = os.environ.get("REDIS_PASSWORD")
            
            if not host:
                raise ValueError(f"Missing Redis configuration. Check environment variables: REDIS_HOST={host}")
            
            if password:
                return f"redis://:{password}@{host}:{port}"
            else:
                return f"redis://{host}:{port}"
            
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        secret = self.read_secret("jwt_secret_key", os.environ.get("JWT_SECRET_KEY", ""))
        if not secret or secret.startswith("CHANGEME"):
            raise ValueError(
                "JWT secret is not configured (set JWT_SECRET_KEY or the "
                "jwt_secret_key secret); refusing to use a placeholder."
            )
        return secret
    
    def get_vault_token(self) -> str:
        """Get Vault token (fail-closed: NO default).

        Resolution order: docker secret / VAULT_ROOT_TOKEN(_FILE) via
        read_secret, then VAULT_TOKEN_FILE, then VAULT_TOKEN. The historical
        fallback to the literal 'root' token has been removed - a missing
        token now raises instead of silently using root access.
        """
        token = self.read_secret("vault_root_token", None)
        if not token:
            token_file = (os.environ.get("VAULT_TOKEN_FILE") or "").strip()
            if token_file and os.path.exists(token_file):
                try:
                    with open(token_file, "r") as f:
                        token = f.read().strip()
                except OSError as e:
                    logger.error(f"VAULT_TOKEN_FILE is set but unreadable: {e}")
        if not token:
            token = (os.environ.get("VAULT_TOKEN") or "").strip()
        if not token:
            raise ValueError(
                "No Vault token configured. Set VAULT_TOKEN_FILE or VAULT_TOKEN "
                "(or provide the vault_root_token secret); refusing to fall back "
                "to a default token."
            )
        return token
    
    def get_admin_password(self, admin_type: str) -> str:
        """Get admin password (no placeholder default; empty when unset)."""
        if admin_type == "platform":
            return self.read_secret("platform_admin_password", "") or ""
        elif admin_type == "org":
            return self.read_secret("org_admin_password", "") or ""
        elif admin_type == "bdh":
            return self.read_secret("bdh_admin_password", "") or ""
        else:
            raise ValueError(f"Unknown admin type: {admin_type}")
    
    def clear_cache(self):
        """Clear the secret cache"""
        self._cache.clear()


# Global instance
_secret_manager = None


def get_secret_manager() -> SecretManager:
    """Get the global SecretManager instance"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


# Convenience functions
def read_secret(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    """Read a secret using the global SecretManager"""
    return get_secret_manager().read_secret(secret_name, default)


def get_database_uri(db_type: str) -> str:
    """Get database URI with secrets"""
    return get_secret_manager().get_database_uri(db_type)


def get_jwt_secret() -> str:
    """Get JWT secret key"""
    return get_secret_manager().get_jwt_secret()


def get_vault_token() -> str:
    """Get Vault token"""
    return get_secret_manager().get_vault_token()