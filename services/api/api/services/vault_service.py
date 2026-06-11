# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import hashlib
import time
from datetime import datetime
from ..core.config import Config
from hvac.exceptions import VaultError, InvalidRequest, Forbidden

logger = logging.getLogger(__name__)

# Import the proper CircuitBreaker from audit tolerance methods
import sys
sys.path.append('/app/audit')
from api.tolerance_methods.retry import CircuitBreaker

# Global circuit breaker for Vault operations
vault_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

def create_user_in_vault(vault_client, username, password, metadata=None):
    """
    Create or update a user in Vault with retry logic and circuit breaker.
    
    Args:
        vault_client: Vault client instance
        username: Username to create
        password: Password to set
        metadata: Additional metadata to store
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not vault_client:
        logger.warning("Vault client not available - running in degraded mode")
        return False
    
    max_retries = 3
    retry_delay = 1
    
    def _create_user():
        for attempt in range(max_retries):
            try:
                # Validate client authentication
                if not vault_client.is_authenticated():
                    raise VaultError("Vault client not authenticated")
                # Hash the password
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                # Prepare user data
                user_data = {
                    'password_hash': password_hash,
                    'created_at': datetime.now().isoformat(),
                    'metadata': metadata or {}
                }
                
                # Write to Vault userpass auth with timeout
                vault_client.write(
                    f'auth/userpass/users/{username}',
                    password=password,
                    policies=['default', 'tesa-iot-user']
                )
                
                # Store additional metadata
                vault_client.write(
                    f'secret/data/users/{username}',
                    data=user_data
                )
                
                logger.info(f"User {username} created in Vault on attempt {attempt + 1}")
                return True
                
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.warning(f"Vault operation attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to create user in Vault after {max_retries} attempts: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error creating user in Vault: {e}")
                return False
                
        return False
    
    try:
        return vault_circuit_breaker.call(_create_user)
    except Exception as e:
        logger.error(f"Circuit breaker prevented Vault operation: {e}")
        return False

def verify_vault_password(vault_client, username, password):
    """
    Verify password against Vault with retry logic and fallback.
    
    Args:
        vault_client: Vault client instance
        username: Username to verify
        password: Password to verify
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Check environment fallback first for performance
    def check_env_fallback():
        if Config.is_development_mode():
            admin_creds = Config.get_admin_credentials()
            
            # Check admin credentials from environment
            if (username == admin_creds['org_admin']['username'] and 
                password == admin_creds['org_admin']['password'] and
                admin_creds['org_admin']['password']):
                return True
            elif (username == admin_creds['bdh_admin']['username'] and 
                  password == admin_creds['bdh_admin']['password'] and
                  admin_creds['bdh_admin']['password']):
                return True
            elif (username == admin_creds['platform_admin']['username'] and 
                  password == admin_creds['platform_admin']['password'] and
                  admin_creds['platform_admin']['password']):
                return True
        return False
    
    if not vault_client:
        # Development mode - check environment variables only
        if check_env_fallback():
            logger.info("Using environment credentials (Vault not available)")
            return True
        logger.warning("Vault not available and no valid environment credentials found")
        return False
    
    max_retries = 2  # Reduced retries for authentication
    retry_delay = 0.5
    
    def _verify_password():
        for attempt in range(max_retries):
            try:
                # Validate client authentication first
                if not vault_client.is_authenticated():
                    raise VaultError("Vault client not authenticated")
                
                # Try to authenticate with userpass
                response = vault_client.auth.userpass.login(
                    username=username,
                    password=password
                )
                
                # Validate response
                if response and 'auth' in response and 'client_token' in response['auth']:
                    logger.info(f"Vault authentication successful for {username} on attempt {attempt + 1}")
                    return True
                else:
                    raise VaultError("Invalid authentication response")
                    
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.debug(f"Vault authentication attempt {attempt + 1}/{max_retries} failed for {username}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.debug(f"Vault authentication failed after {max_retries} attempts for {username}")
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error during Vault authentication for {username}: {e}")
                break
                
        return False
    
    try:
        # Try Vault authentication with circuit breaker
        if vault_circuit_breaker.call(_verify_password):
            return True
    except Exception as e:
        logger.debug(f"Circuit breaker prevented Vault authentication: {e}")
    
    # Fallback to environment credentials
    if check_env_fallback():
        logger.info("Using environment credentials (Vault auth failed)")
        return True
    
    return False

def update_vault_password(vault_client, username, new_password):
    """
    Update user password in Vault with retry logic.
    
    Args:
        vault_client: Vault client instance
        username: Username to update
        new_password: New password to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not vault_client:
        logger.warning("Vault client not available - password update skipped")
        return False
    
    max_retries = 3
    retry_delay = 1
    
    def _update_password():
        for attempt in range(max_retries):
            try:
                # Validate client authentication
                if not vault_client.is_authenticated():
                    raise VaultError("Vault client not authenticated")
                
                # Update password in userpass
                vault_client.write(
                    f'auth/userpass/users/{username}/password',
                    password=new_password
                )
                
                # Update metadata
                vault_client.write(
                    f'secret/data/users/{username}',
                    data={
                        'password_updated': datetime.now().isoformat(),
                        'updated_by': 'system'
                    }
                )
                
                logger.info(f"Password updated for {username} in Vault on attempt {attempt + 1}")
                return True
                
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.warning(f"Vault password update attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"Failed to update password in Vault after {max_retries} attempts: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error updating password in Vault: {e}")
                return False
                
        return False
    
    try:
        return vault_circuit_breaker.call(_update_password)
    except Exception as e:
        logger.error(f"Circuit breaker prevented Vault password update: {e}")
        return False

def delete_vault_user(vault_client, username):
    """
    Delete user from Vault with retry logic.
    
    Args:
        vault_client: Vault client instance
        username: Username to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not vault_client:
        logger.warning("Vault client not available - user deletion skipped")
        return False
    
    max_retries = 3
    retry_delay = 1
    
    def _delete_user():
        for attempt in range(max_retries):
            try:
                # Validate client authentication
                if not vault_client.is_authenticated():
                    raise VaultError("Vault client not authenticated")
                
                # Delete from userpass
                vault_client.delete(f'auth/userpass/users/{username}')
                
                # Delete metadata (ignore if it doesn't exist)
                try:
                    vault_client.delete(f'secret/data/users/{username}')
                except Exception:
                    logger.debug(f"Metadata for user {username} not found or already deleted")
                
                logger.info(f"User {username} deleted from Vault on attempt {attempt + 1}")
                return True
                
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.warning(f"Vault user deletion attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"Failed to delete user from Vault after {max_retries} attempts: {e}")
                    return False
                    
            except Exception as e:
                logger.error(f"Unexpected error deleting user from Vault: {e}")
                return False
                
        return False
    
    try:
        return vault_circuit_breaker.call(_delete_user)
    except Exception as e:
        logger.error(f"Circuit breaker prevented Vault user deletion: {e}")
        return False

def get_vault_policies(vault_client):
    """
    Get list of available Vault policies with retry logic and fallback.
    
    Args:
        vault_client: Vault client instance
        
    Returns:
        list: List of policy names
    """
    default_policies = ['default', 'tesa-iot-user', 'tesa-iot-admin']
    
    if not vault_client:
        logger.warning("Vault client not available - returning default policies")
        return default_policies
    
    max_retries = 2
    retry_delay = 0.5
    
    def _get_policies():
        for attempt in range(max_retries):
            try:
                # Validate client authentication
                if not vault_client.is_authenticated():
                    raise VaultError("Vault client not authenticated")
                
                policies = vault_client.sys.list_policies()
                if policies and 'data' in policies and 'policies' in policies['data']:
                    policy_list = policies['data']['policies']
                    logger.debug(f"Retrieved {len(policy_list)} Vault policies on attempt {attempt + 1}")
                    return policy_list
                else:
                    raise VaultError("Invalid policies response format")
                    
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.warning(f"Vault policies retrieval attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    logger.error(f"Failed to retrieve Vault policies after {max_retries} attempts")
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error retrieving Vault policies: {e}")
                break
                
        return default_policies
    
    try:
        return vault_circuit_breaker.call(_get_policies)
    except Exception as e:
        logger.error(f"Circuit breaker prevented Vault policies retrieval: {e}")
        return default_policies


# Vault service is a module with functions, not a class
# No service instance needed as functions are imported directly