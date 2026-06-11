# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Vault PKI Integration for TESA IoT Platform  ---  QUARANTINED / DO NOT USE  ---

!!! LEGACY MOCK MODULE - NOT WIRED INTO THE RUNNING PLATFORM !!!

This module is dead code: nothing in the codebase imports it (verified by grep).
It is INSECURE and must NOT be reintroduced as-is because it:
  * returns _mock_certificate(...) with fake "mock-<id>" serials when Vault is
    unavailable (issuing trustless certs),
  * revokes against the WRONG mount ('pki/revoke') and swallows the result,
  * has no CRL/OCSP enforcement.

The real, enforced implementation lives in:
  * api/services/pki_provisioning_service.py  (issue + revoke via pki-int)
  * api/services/device_service.py            (revoke_device_certificate, fail-CLOSED)
  * api/services/certificate_service.py       (CSR signing via pki-int)

Importing this module raises immediately to prevent accidental use. If you are
intentionally salvaging code from here, read it as a reference and delete this
guard in a focused commit.
"""

raise ImportError(
    "vault_integration.py is QUARANTINED legacy mock code and must not be "
    "imported. Use api/services/pki_provisioning_service.py and "
    "api/services/device_service.py instead."
)

import os
import hvac
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VaultPKI:
    """Vault PKI integration for certificate-based authentication"""
    
    def __init__(self):
        self.vault_addr = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = os.environ.get('VAULT_TOKEN', 'dev-only-token')
        
        # Initialize Vault client
        self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        
        # Check if Vault is available
        try:
            if self.client.is_authenticated():
                logger.info(f"✅ Connected to Vault at {self.vault_addr}")
                self.initialize_pki()
            else:
                logger.warning("⚠️  Vault authentication failed - using development mode")
                self.client = None
        except Exception as e:
            logger.warning(f"⚠️  Vault not available: {e} - using development mode")
            self.client = None
    
    def initialize_pki(self):
        """Initialize PKI backend if not already done"""
        try:
            # Enable PKI engine if not enabled
            engines = self.client.sys.list_mounted_secrets_engines()
            if 'pki/' not in engines:
                self.client.sys.enable_secrets_engine(
                    backend_type='pki',
                    path='pki',
                    config={'max_lease_ttl': '87600h'}  # 10 years
                )
                logger.info("✅ Enabled PKI secrets engine")
            
            # Check if root CA exists
            try:
                self.client.read('pki/cert/ca')
                logger.info("✅ Root CA already exists")
            except:
                # Generate root CA
                root_ca = self.client.write(
                    'pki/root/generate/internal',
                    common_name='TESA IoT Platform Root CA',
                    ttl='87600h',
                    key_type='rsa',
                    key_bits=4096
                )
                logger.info("✅ Generated Root CA")
                
                # Configure CA and CRL URLs
                self.client.write(
                    'pki/config/urls',
                    issuing_certificates=f"{self.vault_addr}/v1/pki/ca",
                    crl_distribution_points=f"{self.vault_addr}/v1/pki/crl"
                )
            
            # Create device role for issuing certificates
            try:
                self.client.read('pki/roles/iot-device')
            except:
                self.client.write(
                    'pki/roles/iot-device',
                    allowed_domains='tesa.iot',
                    allow_subdomains=True,
                    allow_glob_domains=True,
                    allow_any_name=True,
                    max_ttl='8760h',  # 1 year
                    key_type='rsa',
                    key_bits=2048,
                    require_cn=True,
                    organization='TESA IoT Platform',
                    ou='IoT Devices'
                )
                logger.info("✅ Created IoT device certificate role")
                
        except Exception as e:
            logger.error(f"Failed to initialize PKI: {e}")
    
    def issue_device_certificate(self, device_id, organization_id, tls_version='1.3'):
        """Issue certificate for IoT device"""
        if not self.client:
            # Development mode - return mock certificate
            return self._mock_certificate(device_id, organization_id, tls_version)
        
        try:
            # Issue certificate from Vault
            common_name = f"{device_id}.{organization_id}.tesa.iot"
            
            cert_response = self.client.write(
                'pki/issue/iot-device',
                common_name=common_name,
                alt_names=f"{device_id}.local,{device_id}.tesa.iot",
                ttl='8760h',  # 1 year
                format='pem',
                private_key_format='pem',
                # TLS version constraints
                key_usage=['DigitalSignature', 'KeyAgreement', 'KeyEncipherment'],
                ext_key_usage=['ServerAuth', 'ClientAuth'] if tls_version == '1.3' else ['ClientAuth']
            )
            
            return {
                'certificate': cert_response['data']['certificate'],
                'private_key': cert_response['data']['private_key'],
                'ca_chain': cert_response['data']['ca_chain'],
                'serial_number': cert_response['data']['serial_number'],
                'expiration': cert_response['data']['expiration'],
                'tls_version': tls_version,
                'issued_by': 'Vault PKI'
            }
            
        except Exception as e:
            logger.error(f"Failed to issue certificate: {e}")
            return self._mock_certificate(device_id, organization_id, tls_version)
    
    def revoke_certificate(self, serial_number):
        """Revoke a certificate"""
        if not self.client:
            return True  # Mock success in dev mode
        
        try:
            self.client.write(
                'pki/revoke',
                serial_number=serial_number
            )
            logger.info(f"✅ Revoked certificate {serial_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke certificate: {e}")
            return False
    
    def validate_certificate(self, certificate_pem):
        """Validate certificate against Vault CA"""
        if not self.client:
            return True  # Mock validation in dev mode
        
        try:
            # In production, would validate against CRL and OCSP
            # For now, basic validation
            return True
        except Exception as e:
            logger.error(f"Certificate validation failed: {e}")
            return False
    
    def audit_log(self, action, entity_id, details):
        """Log security events to Vault audit"""
        if not self.client:
            logger.info(f"AUDIT (dev): {action} - {entity_id} - {details}")
            return
        
        try:
            # Vault automatically logs all operations
            # Additional custom audit can be added here
            logger.info(f"AUDIT: {action} - {entity_id} - {details}")
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")
    
    def _mock_certificate(self, device_id, organization_id, tls_version):
        """Generate mock certificate for development"""
        return {
            'certificate': f"""-----BEGIN CERTIFICATE-----
Mock Certificate for Development
Device: {device_id}
Organization: {organization_id}
TLS Version: {tls_version}
Issued: {datetime.utcnow().isoformat()}
Expires: {(datetime.utcnow() + timedelta(days=365)).isoformat()}
-----END CERTIFICATE-----""",
            'private_key': """-----BEGIN PRIVATE KEY-----
Mock Private Key - DO NOT USE IN PRODUCTION
-----END PRIVATE KEY-----""",
            'ca_chain': """-----BEGIN CERTIFICATE-----
Mock TESA IoT Platform Root CA
-----END CERTIFICATE-----""",
            'serial_number': f"mock-{device_id[:8]}",
            'expiration': (datetime.utcnow() + timedelta(days=365)).timestamp(),
            'tls_version': tls_version,
            'issued_by': 'Mock PKI (Dev Mode)'
        }

# Global instance
vault_pki = VaultPKI()

# Authentication functions
def authenticate_device_certificate(cert_pem):
    """Authenticate device using certificate"""
    return vault_pki.validate_certificate(cert_pem)

def issue_device_credentials(device_id, organization_id, tls_version='1.3'):
    """Issue credentials for new device"""
    cert_data = vault_pki.issue_device_certificate(device_id, organization_id, tls_version)
    vault_pki.audit_log('device_certificate_issued', device_id, {
        'organization_id': organization_id,
        'tls_version': tls_version,
        'serial_number': cert_data['serial_number']
    })
    return cert_data

def revoke_device_credentials(device_id, serial_number, reason='unspecified'):
    """Revoke device credentials"""
    success = vault_pki.revoke_certificate(serial_number)
    vault_pki.audit_log('device_certificate_revoked', device_id, {
        'serial_number': serial_number,
        'reason': reason,
        'success': success
    })
    return success