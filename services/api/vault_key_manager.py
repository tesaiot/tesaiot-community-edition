# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Key Manager
Manages PKI certificates and secrets using HashiCorp Vault
"""

import os
import logging
import requests
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _require_vault_token() -> str:
    """Resolve the Vault token from VAULT_TOKEN_FILE or VAULT_TOKEN.

    SECURITY: no default. The historical fallback to the literal 'root' token
    silently granted root Vault access in misconfigured deployments. Fail
    closed with a clear error instead.
    """
    token_file = (os.getenv('VAULT_TOKEN_FILE') or '').strip()
    if token_file:
        try:
            with open(token_file, 'r') as f:
                token = f.read().strip()
            if token:
                return token
        except OSError as e:
            raise RuntimeError(f"VAULT_TOKEN_FILE is set but unreadable: {e}")
    token = (os.getenv('VAULT_TOKEN') or '').strip()
    if not token:
        raise RuntimeError(
            "No Vault token configured. Set VAULT_TOKEN_FILE or VAULT_TOKEN; "
            "refusing to fall back to a default token."
        )
    return token


class VaultKeyManager:
    """Manages certificates and secrets with Vault"""

    def __init__(self, vault_addr: str = None, vault_token: str = None):
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = vault_token or _require_vault_token()
        self.headers = {'X-Vault-Token': self.vault_token}
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Vault connection"""
        try:
            response = requests.get(
                f"{self.vault_addr}/v1/sys/health",
                headers=self.headers
            )
            if response.status_code != 200:
                logger.warning(f"Vault health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to connect to Vault: {e}")
    
    def issue_device_certificate(self, device_id: str, common_name: str = None) -> Dict:
        """Issue a new device certificate"""
        try:
            # Default common name if not provided
            if not common_name:
                common_name = f"{device_id}.device.tesa.local"
            
            # Certificate parameters
            data = {
                'common_name': common_name,
                'alt_names': f"{device_id}.device.tesa.local",
                'ttl': '8760h',  # 1 year
                'format': 'pem_bundle'
            }
            
            # Request certificate from Vault
            response = requests.post(
                f"{self.vault_addr}/v1/pki-int/issue/iot-device",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                cert_data = response.json()['data']
                
                # Extract certificate components
                result = {
                    'certificate': cert_data['certificate'],
                    'private_key': cert_data['private_key'],
                    'ca_chain': cert_data['ca_chain'],
                    'serial_number': cert_data['serial_number'],
                    'expiration': cert_data['expiration']
                }
                
                logger.info(f"Issued certificate for device {device_id}, serial: {result['serial_number']}")
                return result
            else:
                logger.error(f"Failed to issue certificate: {response.text}")
                raise Exception(f"Certificate issuance failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error issuing certificate for {device_id}: {e}")
            raise
    
    def revoke_certificate(self, serial_number: str) -> bool:
        """Revoke a certificate"""
        try:
            data = {'serial_number': serial_number}
            
            response = requests.post(
                f"{self.vault_addr}/v1/pki-int/revoke",
                headers=self.headers,
                json=data
            )
            
            if response.status_code == 200:
                logger.info(f"Revoked certificate with serial: {serial_number}")
                return True
            else:
                logger.error(f"Failed to revoke certificate: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error revoking certificate {serial_number}: {e}")
            return False
    
    def get_ca_certificate(self) -> str:
        """Get CA certificate chain"""
        try:
            response = requests.get(
                f"{self.vault_addr}/v1/pki-int/ca_chain",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to get CA chain: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error getting CA chain: {e}")
            return ""
    
    def get_crl(self) -> str:
        """Get Certificate Revocation List"""
        try:
            response = requests.get(
                f"{self.vault_addr}/v1/pki-int/crl",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Failed to get CRL: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"Error getting CRL: {e}")
            return ""
    
    def verify_certificate(self, serial_number: str) -> bool:
        """Verify if certificate is valid (not revoked)"""
        try:
            # Get CRL and check if serial is in it
            crl = self.get_crl()
            
            # For production, parse CRL properly
            # For now, simple check
            if serial_number in crl:
                return False  # Certificate is revoked
            
            return True  # Certificate is valid
            
        except Exception as e:
            logger.error(f"Error verifying certificate {serial_number}: {e}")
            return False
    
    def get_secret(self, path: str) -> Optional[Dict]:
        """Get secret from KV store"""
        try:
            response = requests.get(
                f"{self.vault_addr}/v1/secret/data/{path}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()['data']['data']
            else:
                logger.error(f"Failed to get secret {path}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting secret {path}: {e}")
            return None
    
    def put_secret(self, path: str, data: Dict) -> bool:
        """Store secret in KV store"""
        try:
            payload = {'data': data}
            
            response = requests.post(
                f"{self.vault_addr}/v1/secret/data/{path}",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 204]:
                logger.info(f"Stored secret at {path}")
                return True
            else:
                logger.error(f"Failed to store secret {path}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing secret {path}: {e}")
            return False
    
    def create_approle_secret_id(self, role_name: str) -> Optional[str]:
        """Create a new secret ID for AppRole"""
        try:
            response = requests.post(
                f"{self.vault_addr}/v1/auth/approle/role/{role_name}/secret-id",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()['data']['secret_id']
            else:
                logger.error(f"Failed to create secret ID: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating secret ID for {role_name}: {e}")
            return None


# Singleton instance
_vault_manager = None

def get_vault_manager() -> VaultKeyManager:
    """Get or create Vault manager instance"""
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultKeyManager()
    return _vault_manager