# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Key Management Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from hvac.exceptions import VaultError

from ..core.database import get_db, get_vault
from .audit_service import audit_log, AuditAction
from .vault_service import vault_circuit_breaker

logger = logging.getLogger(__name__)

class VaultKeyError(Exception):
    """Custom Vault key management error."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class VaultKeyService:
    """Service for managing keys in HashiCorp Vault."""
    
    def __init__(self):
        self.vault_client = None
        self.db = None
        
    def get_vault_client(self):
        """Get Vault client with lazy initialization."""
        if not self.vault_client:
            self.vault_client = get_vault()
        return self.vault_client
    
    def get_db(self):
        """Get database connection with lazy initialization."""
        if not self.db:
            self.db = get_db()
        return self.db
    
    @vault_circuit_breaker
    def store_key_in_vault(self, key_data: Dict, vault_path: str, metadata: Dict = None) -> Dict:
        """
        Store a key in Vault KV store.
        
        Args:
            key_data: Key data to store
            vault_path: Vault path for storage
            metadata: Additional metadata
            
        Returns:
            Storage result information
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Prepare data for storage
            storage_data = {
                'private_key': key_data.get('private_key_pem'),
                'public_key': key_data.get('public_key_pem'),
                'algorithm': key_data.get('algorithm'),
                'device_id': key_data.get('device_id'),
                'organization_id': key_data.get('organization_id'),
                'key_fingerprint': key_data.get('key_fingerprint'),
                'generated_at': datetime.now().isoformat(),
                'expires_at': key_data.get('expires_at'),
                'status': 'active',
                'metadata': metadata or {}
            }
            
            # Store in Vault
            response = vault_client.write(vault_path, **storage_data)
            
            logger.info(f"Stored key in Vault at path: {vault_path}")
            
            return {
                'vault_path': vault_path,
                'version': response.get('data', {}).get('version') if response else None,
                'stored_at': datetime.now().isoformat(),
                'status': 'stored'
            }
            
        except VaultError as e:
            logger.error(f"Vault error storing key: {e}")
            raise VaultKeyError(f"Failed to store key in Vault: {str(e)}")
        except Exception as e:
            logger.error(f"Error storing key in Vault: {e}")
            raise VaultKeyError(f"Key storage failed: {str(e)}")
    
    @vault_circuit_breaker
    def retrieve_key_from_vault(self, vault_path: str, user: Dict) -> Optional[Dict]:
        """
        Retrieve a key from Vault KV store.
        
        Args:
            vault_path: Vault path to retrieve from
            user: User requesting the key
            
        Returns:
            Key data or None if not found
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Retrieve from Vault
            response = vault_client.read(vault_path)
            
            if not response or 'data' not in response:
                return None
            
            key_data = response['data']
            
            # Log access
            audit_log(
                action=AuditAction.KEY_VIEW,
                user=user,
                resource_type='vault_key',
                resource_id=vault_path,
                details={
                    'vault_path': vault_path,
                    'device_id': key_data.get('device_id'),
                    'algorithm': key_data.get('algorithm')
                }
            )
            
            logger.info(f"Retrieved key from Vault path: {vault_path}")
            
            return {
                'private_key_pem': key_data.get('private_key'),
                'public_key_pem': key_data.get('public_key'),
                'algorithm': key_data.get('algorithm'),
                'device_id': key_data.get('device_id'),
                'organization_id': key_data.get('organization_id'),
                'key_fingerprint': key_data.get('key_fingerprint'),
                'generated_at': key_data.get('generated_at'),
                'expires_at': key_data.get('expires_at'),
                'status': key_data.get('status'),
                'metadata': key_data.get('metadata', {}),
                'vault_version': response.get('data', {}).get('version')
            }
            
        except VaultError as e:
            logger.error(f"Vault error retrieving key: {e}")
            raise VaultKeyError(f"Failed to retrieve key from Vault: {str(e)}")
        except Exception as e:
            logger.error(f"Error retrieving key from Vault: {e}")
            raise VaultKeyError(f"Key retrieval failed: {str(e)}")
    
    @vault_circuit_breaker
    def revoke_key_in_vault(self, vault_path: str, reason: str, user: Dict) -> Dict:
        """
        Revoke a key in Vault by updating its status.
        
        Args:
            vault_path: Vault path to the key
            reason: Revocation reason
            user: User performing revocation
            
        Returns:
            Revocation result
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # First, retrieve current key data
            current_data = self.retrieve_key_from_vault(vault_path, user)
            if not current_data:
                raise VaultKeyError("Key not found in Vault")
            
            # Update status to revoked
            current_data['status'] = 'revoked'
            current_data['revoked_at'] = datetime.now().isoformat()
            current_data['revoked_by'] = user.get('email', '')
            current_data['revocation_reason'] = reason
            
            # Store updated data
            response = vault_client.write(vault_path, **current_data)
            
            # Log revocation
            audit_log(
                action=AuditAction.KEY_REVOKE,
                user=user,
                resource_type='vault_key',
                resource_id=vault_path,
                details={
                    'vault_path': vault_path,
                    'device_id': current_data.get('device_id'),
                    'reason': reason,
                    'algorithm': current_data.get('algorithm')
                }
            )
            
            logger.info(f"Revoked key in Vault at path: {vault_path}")
            
            return {
                'vault_path': vault_path,
                'status': 'revoked',
                'revoked_at': current_data['revoked_at'],
                'reason': reason
            }
            
        except VaultError as e:
            logger.error(f"Vault error revoking key: {e}")
            raise VaultKeyError(f"Failed to revoke key in Vault: {str(e)}")
        except Exception as e:
            logger.error(f"Error revoking key in Vault: {e}")
            raise VaultKeyError(f"Key revocation failed: {str(e)}")
    
    @vault_circuit_breaker
    def list_keys_in_vault(self, organization_id: str, user: Dict) -> List[Dict]:
        """
        List keys for an organization in Vault.
        
        Args:
            organization_id: Organization ID
            user: User requesting the list
            
        Returns:
            List of key information
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # List keys under organization path
            base_path = f"secret/keys/{organization_id}"
            
            try:
                response = vault_client.list(base_path)
            except Exception:
                # Path might not exist yet
                return []
            
            if not response or 'data' not in response:
                return []
            
            keys_list = []
            device_ids = response['data'].get('keys', [])
            
            for device_id in device_ids:
                try:
                    key_path = f"{base_path}/{device_id}"
                    key_data = self.retrieve_key_from_vault(key_path, user)
                    
                    if key_data:
                        keys_list.append({
                            'device_id': device_id,
                            'vault_path': key_path,
                            'algorithm': key_data.get('algorithm'),
                            'status': key_data.get('status'),
                            'generated_at': key_data.get('generated_at'),
                            'expires_at': key_data.get('expires_at'),
                            'key_fingerprint': key_data.get('key_fingerprint')
                        })
                except Exception as e:
                    logger.warning(f"Failed to retrieve key for device {device_id}: {e}")
                    continue
            
            # Log list access
            audit_log(
                action=AuditAction.KEY_VIEW,
                user=user,
                resource_type='vault_key_list',
                resource_id=organization_id,
                details={
                    'organization_id': organization_id,
                    'keys_count': len(keys_list)
                }
            )
            
            logger.info(f"Listed {len(keys_list)} keys for organization {organization_id}")
            
            return keys_list
            
        except VaultError as e:
            logger.error(f"Vault error listing keys: {e}")
            raise VaultKeyError(f"Failed to list keys in Vault: {str(e)}")
        except Exception as e:
            logger.error(f"Error listing keys in Vault: {e}")
            raise VaultKeyError(f"Key listing failed: {str(e)}")
    
    @vault_circuit_breaker
    def create_key_transit_key(self, key_name: str, key_type: str = "rsa-2048") -> Dict:
        """
        Create a transit encryption key in Vault for key encryption.
        
        Args:
            key_name: Name for the transit key
            key_type: Type of key to create
            
        Returns:
            Transit key information
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Create transit key
            response = vault_client.write(
                f"transit/keys/{key_name}",
                type=key_type,
                exportable=False,
                allow_plaintext_backup=False
            )
            
            logger.info(f"Created transit key: {key_name}")
            
            return {
                'key_name': key_name,
                'key_type': key_type,
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
            
        except VaultError as e:
            logger.error(f"Vault error creating transit key: {e}")
            raise VaultKeyError(f"Failed to create transit key: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating transit key: {e}")
            raise VaultKeyError(f"Transit key creation failed: {str(e)}")
    
    @vault_circuit_breaker
    def encrypt_with_transit(self, key_name: str, plaintext: str) -> str:
        """
        Encrypt data using Vault transit encryption.
        
        Args:
            key_name: Transit key name
            plaintext: Data to encrypt
            
        Returns:
            Encrypted ciphertext
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Encode plaintext to base64
            plaintext_b64 = base64.b64encode(plaintext.encode('utf-8')).decode('utf-8')
            
            # Encrypt with transit
            response = vault_client.write(
                f"transit/encrypt/{key_name}",
                plaintext=plaintext_b64
            )
            
            if not response or 'data' not in response:
                raise VaultKeyError("Invalid encryption response from Vault")
            
            ciphertext = response['data']['ciphertext']
            
            logger.debug(f"Encrypted data with transit key: {key_name}")
            
            return ciphertext
            
        except VaultError as e:
            logger.error(f"Vault error encrypting data: {e}")
            raise VaultKeyError(f"Failed to encrypt with transit: {str(e)}")
        except Exception as e:
            logger.error(f"Error encrypting with transit: {e}")
            raise VaultKeyError(f"Transit encryption failed: {str(e)}")
    
    @vault_circuit_breaker
    def decrypt_with_transit(self, key_name: str, ciphertext: str) -> str:
        """
        Decrypt data using Vault transit encryption.
        
        Args:
            key_name: Transit key name
            ciphertext: Data to decrypt
            
        Returns:
            Decrypted plaintext
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Decrypt with transit
            response = vault_client.write(
                f"transit/decrypt/{key_name}",
                ciphertext=ciphertext
            )
            
            if not response or 'data' not in response:
                raise VaultKeyError("Invalid decryption response from Vault")
            
            # Decode from base64
            plaintext_b64 = response['data']['plaintext']
            plaintext = base64.b64decode(plaintext_b64).decode('utf-8')
            
            logger.debug(f"Decrypted data with transit key: {key_name}")
            
            return plaintext
            
        except VaultError as e:
            logger.error(f"Vault error decrypting data: {e}")
            raise VaultKeyError(f"Failed to decrypt with transit: {str(e)}")
        except Exception as e:
            logger.error(f"Error decrypting with transit: {e}")
            raise VaultKeyError(f"Transit decryption failed: {str(e)}")
    
    def setup_key_management_policies(self, organization_id: str) -> Dict:
        """
        Setup Vault policies for key management.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Policy setup results
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Define key management policy
            policy_name = f"key-management-{organization_id}"
            policy_rules = f'''
path "secret/data/keys/{organization_id}/*" {{
  capabilities = ["create", "read", "update", "delete", "list"]
}}

path "secret/metadata/keys/{organization_id}/*" {{
  capabilities = ["list", "read", "delete"]
}}

path "transit/encrypt/org-{organization_id}" {{
  capabilities = ["update"]
}}

path "transit/decrypt/org-{organization_id}" {{
  capabilities = ["update"]
}}

path "transit/keys/org-{organization_id}" {{
  capabilities = ["read"]
}}

path "pki-int/issue/iot-device-*" {{
  capabilities = ["update"]
}}

path "pki-int/sign/iot-device-*" {{
  capabilities = ["update"]
}}
'''
            
            # Create policy
            vault_client.sys.create_or_update_policy(
                name=policy_name,
                policy=policy_rules
            )
            
            # Create organization-specific transit key
            transit_key_name = f"org-{organization_id}"
            try:
                self.create_key_transit_key(transit_key_name, "aes256-gcm96")
            except Exception as e:
                logger.warning(f"Transit key might already exist: {e}")
            
            logger.info(f"Setup key management policies for organization: {organization_id}")
            
            return {
                'policy_name': policy_name,
                'transit_key': transit_key_name,
                'setup_at': datetime.now().isoformat(),
                'status': 'configured'
            }
            
        except VaultError as e:
            logger.error(f"Vault error setting up policies: {e}")
            raise VaultKeyError(f"Failed to setup policies: {str(e)}")
        except Exception as e:
            logger.error(f"Error setting up policies: {e}")
            raise VaultKeyError(f"Policy setup failed: {str(e)}")
    
    def get_key_distribution_token(self, device_id: str, organization_id: str, 
                                  expiry_hours: int = 24) -> Dict:
        """
        Create a temporary token for secure key distribution.
        
        Args:
            device_id: Device ID
            organization_id: Organization ID
            expiry_hours: Token expiry time in hours
            
        Returns:
            Distribution token information
        """
        try:
            vault_client = self.get_vault_client()
            if not vault_client:
                raise VaultKeyError("Vault client not available")
            
            # Create a limited-scope token for key retrieval
            token_policies = [f"key-management-{organization_id}"]
            
            response = vault_client.auth.token.create(
                policies=token_policies,
                ttl=f"{expiry_hours}h",
                renewable=False,
                meta={
                    'device_id': device_id,
                    'organization_id': organization_id,
                    'purpose': 'key_distribution'
                }
            )
            
            token_data = response['auth']
            
            logger.info(f"Created distribution token for device: {device_id}")
            
            return {
                'token': token_data['client_token'],
                'device_id': device_id,
                'organization_id': organization_id,
                'expires_at': (datetime.now() + timedelta(hours=expiry_hours)).isoformat(),
                'policies': token_policies,
                'created_at': datetime.now().isoformat()
            }
            
        except VaultError as e:
            logger.error(f"Vault error creating distribution token: {e}")
            raise VaultKeyError(f"Failed to create distribution token: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating distribution token: {e}")
            raise VaultKeyError(f"Distribution token creation failed: {str(e)}")

# Create service instance
vault_key_service = VaultKeyService()