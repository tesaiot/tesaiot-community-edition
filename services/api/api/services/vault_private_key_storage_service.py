# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Private Key Storage Service

Security rule: private keys are stored exclusively in Vault, never in
MongoDB — the database may only hold Vault path references.

This service provides:
- Store private keys in Vault KV v2 secrets engine
- Retrieve private keys from Vault (with audit logging)
- Delete private keys from Vault
- Key existence verification

NEVER store private keys in MongoDB - only Vault references allowed in database.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Optional
from cryptography.hazmat.primitives import serialization
from hvac.exceptions import VaultError

from ..core.database import get_vault
from .audit_service import audit_log, AuditAction

logger = logging.getLogger(__name__)

# Vault KV v2 mount path for device private keys
VAULT_PRIVATE_KEY_MOUNT = "secret"
VAULT_PRIVATE_KEY_BASE_PATH = "pki-devices/keys"


class VaultPrivateKeyStorageError(Exception):
    """Custom error for Vault private key operations."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class VaultPrivateKeyStorageService:
    """
    Service for storing device private keys exclusively in HashiCorp Vault.

    Security Policy:
    - Private keys are NEVER stored in MongoDB
    - Only vault_key_path references are stored in database
    - All key access is audit logged
    - Keys are stored encrypted at rest in Vault
    """

    def __init__(self):
        self._vault_client = None

    def _get_vault_client(self):
        """Get Vault client with lazy initialization."""
        if not self._vault_client:
            self._vault_client = get_vault()
        return self._vault_client

    def _get_key_path(self, device_id: str, organization_id: str = None) -> str:
        """
        Generate Vault path for device private key.

        Path format: pki-devices/keys/{organization_id}/{device_id}
        """
        if organization_id:
            return f"{VAULT_PRIVATE_KEY_BASE_PATH}/{organization_id}/{device_id}"
        return f"{VAULT_PRIVATE_KEY_BASE_PATH}/{device_id}"

    def store_private_key(
        self,
        device_id: str,
        private_key_pem: str,
        organization_id: str = None,
        algorithm: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Store a device private key in Vault.

        Args:
            device_id: Device identifier
            private_key_pem: Private key in PEM format
            organization_id: Organization ID (optional)
            algorithm: Key algorithm (e.g., 'RSA-2048', 'EC-P256')
            metadata: Additional metadata

        Returns:
            Dict with vault_key_path and key_fingerprint

        Raises:
            VaultPrivateKeyStorageError: If storage fails
        """
        try:
            vault_client = self._get_vault_client()
            if not vault_client:
                raise VaultPrivateKeyStorageError(
                    "Vault client not available",
                    code="VAULT_UNAVAILABLE"
                )

            # Generate vault path
            vault_path = self._get_key_path(device_id, organization_id)

            # Calculate key fingerprint (SHA256 of public key for verification)
            key_fingerprint = self._calculate_key_fingerprint(private_key_pem)

            # Prepare data for storage
            secret_data = {
                "private_key_pem": private_key_pem,
                "device_id": device_id,
                "organization_id": organization_id or "",
                "algorithm": algorithm or "unknown",
                "key_fingerprint": key_fingerprint,
                "stored_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }

            # Store in Vault KV v2
            vault_client.secrets.kv.v2.create_or_update_secret(
                path=vault_path,
                secret=secret_data,
                mount_point=VAULT_PRIVATE_KEY_MOUNT
            )

            logger.info(f"Stored private key in Vault for device: {device_id}")

            return {
                "vault_key_path": f"{VAULT_PRIVATE_KEY_MOUNT}/{vault_path}",
                "key_fingerprint": key_fingerprint,
                "algorithm": algorithm,
                "stored_at": datetime.now().isoformat()
            }

        except VaultError as e:
            logger.error(f"Vault error storing private key for device {device_id}: {e}")
            raise VaultPrivateKeyStorageError(
                f"Failed to store private key in Vault: {str(e)}",
                code="VAULT_STORE_ERROR"
            )
        except Exception as e:
            logger.error(f"Error storing private key for device {device_id}: {e}")
            raise VaultPrivateKeyStorageError(
                f"Private key storage failed: {str(e)}",
                code="STORAGE_ERROR"
            )

    def retrieve_private_key(
        self,
        device_id: str,
        organization_id: str = None,
        requester: Dict = None
    ) -> Optional[Dict]:
        """
        Retrieve a device private key from Vault.

        Args:
            device_id: Device identifier
            organization_id: Organization ID (optional)
            requester: User/system requesting the key (for audit)

        Returns:
            Dict with private_key_pem and metadata, or None if not found

        Raises:
            VaultPrivateKeyStorageError: If retrieval fails
        """
        try:
            vault_client = self._get_vault_client()
            if not vault_client:
                raise VaultPrivateKeyStorageError(
                    "Vault client not available",
                    code="VAULT_UNAVAILABLE"
                )

            vault_path = self._get_key_path(device_id, organization_id)

            # Retrieve from Vault KV v2
            try:
                response = vault_client.secrets.kv.v2.read_secret_version(
                    path=vault_path,
                    mount_point=VAULT_PRIVATE_KEY_MOUNT
                )
            except Exception as e:
                if "secret not found" in str(e).lower() or "404" in str(e):
                    return None
                raise

            if not response or 'data' not in response or 'data' not in response['data']:
                return None

            secret_data = response['data']['data']

            # Audit log the access
            if requester:
                audit_log(
                    action=AuditAction.KEY_VIEW,
                    user=requester,
                    resource_type='device_private_key',
                    resource_id=device_id,
                    details={
                        'vault_path': vault_path,
                        'organization_id': organization_id,
                        'algorithm': secret_data.get('algorithm')
                    }
                )

            logger.info(f"Retrieved private key from Vault for device: {device_id}")

            return {
                "private_key_pem": secret_data.get('private_key_pem'),
                "device_id": secret_data.get('device_id'),
                "organization_id": secret_data.get('organization_id'),
                "algorithm": secret_data.get('algorithm'),
                "key_fingerprint": secret_data.get('key_fingerprint'),
                "stored_at": secret_data.get('stored_at'),
                "metadata": secret_data.get('metadata', {}),
                "vault_version": response['data'].get('metadata', {}).get('version')
            }

        except VaultPrivateKeyStorageError:
            raise
        except VaultError as e:
            logger.error(f"Vault error retrieving private key for device {device_id}: {e}")
            raise VaultPrivateKeyStorageError(
                f"Failed to retrieve private key from Vault: {str(e)}",
                code="VAULT_RETRIEVE_ERROR"
            )
        except Exception as e:
            logger.error(f"Error retrieving private key for device {device_id}: {e}")
            raise VaultPrivateKeyStorageError(
                f"Private key retrieval failed: {str(e)}",
                code="RETRIEVAL_ERROR"
            )

    def delete_private_key(
        self,
        device_id: str,
        organization_id: str = None,
        requester: Dict = None
    ) -> bool:
        """
        Delete a device private key from Vault.

        Args:
            device_id: Device identifier
            organization_id: Organization ID (optional)
            requester: User/system requesting deletion (for audit)

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            vault_client = self._get_vault_client()
            if not vault_client:
                raise VaultPrivateKeyStorageError(
                    "Vault client not available",
                    code="VAULT_UNAVAILABLE"
                )

            vault_path = self._get_key_path(device_id, organization_id)

            # Delete from Vault (all versions)
            try:
                vault_client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=vault_path,
                    mount_point=VAULT_PRIVATE_KEY_MOUNT
                )
            except Exception as e:
                if "secret not found" in str(e).lower() or "404" in str(e):
                    return False
                raise

            # Audit log the deletion
            if requester:
                audit_log(
                    action=AuditAction.KEY_DELETE,
                    user=requester,
                    resource_type='device_private_key',
                    resource_id=device_id,
                    details={
                        'vault_path': vault_path,
                        'organization_id': organization_id
                    }
                )

            logger.info(f"Deleted private key from Vault for device: {device_id}")
            return True

        except VaultPrivateKeyStorageError:
            raise
        except Exception as e:
            logger.error(f"Error deleting private key for device {device_id}: {e}")
            raise VaultPrivateKeyStorageError(
                f"Private key deletion failed: {str(e)}",
                code="DELETION_ERROR"
            )

    def key_exists(self, device_id: str, organization_id: str = None) -> bool:
        """
        Check if a private key exists in Vault.

        Args:
            device_id: Device identifier
            organization_id: Organization ID (optional)

        Returns:
            bool: True if key exists
        """
        try:
            vault_client = self._get_vault_client()
            if not vault_client:
                return False

            vault_path = self._get_key_path(device_id, organization_id)

            try:
                response = vault_client.secrets.kv.v2.read_secret_version(
                    path=vault_path,
                    mount_point=VAULT_PRIVATE_KEY_MOUNT
                )
                return response is not None and 'data' in response
            except Exception:
                return False

        except Exception:
            return False

    def _calculate_key_fingerprint(self, private_key_pem: str) -> str:
        """
        Calculate SHA256 fingerprint of the public key derived from private key.

        Args:
            private_key_pem: Private key in PEM format

        Returns:
            str: SHA256 fingerprint in hex format
        """
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            from cryptography.hazmat.backends import default_backend

            private_key = load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )

            public_key_der = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            return hashlib.sha256(public_key_der).hexdigest()

        except Exception as e:
            logger.warning(f"Could not calculate key fingerprint: {e}")
            return hashlib.sha256(private_key_pem.encode()).hexdigest()


# Singleton instance
vault_private_key_storage_service = VaultPrivateKeyStorageService()
