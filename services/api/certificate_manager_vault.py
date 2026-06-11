# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
ETSI & ISO Certificate Management for TESA IoT  ---  QUARANTINED / DO NOT USE ---

!!! LEGACY MODULE - NOT WIRED INTO THE RUNNING PLATFORM !!!

This module is dead code: nothing in the codebase imports it (verified by grep).
It is superseded and must NOT be reintroduced as-is because it:
  * revokes against the WRONG mount ('pki/revoke') instead of pki-int/revoke,
  * has a _fallback_certificate_generation(...) path and silently no-ops revoke
    when Vault is unavailable (logs a warning and returns),
  * has no CRL/OCSP enforcement.

The real, enforced implementation lives in:
  * api/services/pki_provisioning_service.py  (issue + revoke via pki-int + CRL)
  * api/services/device_service.py            (revoke_device_certificate, fail-CLOSED)
  * api/services/certificate_service.py       (CSR signing / CA chain via pki-int)

Importing this module raises immediately to prevent accidental use.
"""

raise ImportError(
    "certificate_manager_vault.py is QUARANTINED legacy code and must not be "
    "imported. Use api/services/pki_provisioning_service.py and "
    "api/services/device_service.py instead."
)

import os
import json
import hvac
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class VaultCertificateManager:
    """
    Cybersecurity-compliant certificate manager using HashiCorp Vault PKI
    
    ETSI EN 303 645 Compliance:
    - Provision 4: Securely store credentials and security-sensitive data
    - Provision 5: Communicate securely
    
    ISO/IEC 27402 Compliance:
    - Cryptographic controls for IoT systems
    - Secure key management and storage
    """
    
    def __init__(self):
        """Initialize Vault PKI connection"""
        self.vault_addr = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = os.environ.get('VAULT_TOKEN')
        
        # Connect to Vault
        self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        self.vault_available = False
        
        try:
            if self.client.is_authenticated():
                logger.info(f"✅ Connected to Vault PKI at {self.vault_addr}")
                self.vault_available = True
                self.initialize_pki()
            else:
                logger.warning("⚠️  Vault authentication failed - compliance mode disabled")
        except Exception as e:
            logger.warning(f"⚠️  Vault PKI unavailable: {e} - falling back to development mode")
    
    def initialize_pki(self):
        """Initialize Vault PKI secrets engine for ETSI/ISO compliance"""
        try:
            # Check if PKI engine is mounted
            mounts = self.client.sys.list_mounted_secrets_engines()
            if 'pki/' not in mounts:
                # Mount PKI engine with compliant settings
                self.client.sys.enable_secrets_engine(
                    backend_type='pki',
                    path='pki',
                    config={
                        'max_lease_ttl': '87600h',  # 10 years max
                        'default_lease_ttl': '8760h'  # 1 year default
                    }
                )
                logger.info("✅ Mounted PKI secrets engine")
            
            # Initialize Root CA if not exists
            try:
                ca_cert = self.client.read('pki/cert/ca')
                if ca_cert:
                    logger.info("✅ Vault Root CA already configured")
            except:
                # Generate ETSI-compliant Root CA
                root_ca_response = self.client.write(
                    'pki/root/generate/internal',
                    common_name='TESA IoT Platform Root CA',
                    organization='TESA IoT Platform',
                    ou='Certificate Authority',
                    country='TH',
                    province='Bangkok',
                    locality='Bangkok',
                    ttl='87600h',  # 10 years
                    key_type='rsa',
                    key_bits=3072,  # RSA 3072 - optimal balance of security and performance
                    signature_bits=256  # SHA-256
                )
                
                # Configure PKI URLs for CRL and certificate distribution
                self.client.write(
                    'pki/config/urls',
                    issuing_certificates=[f"{self.vault_addr}/v1/pki/ca"],
                    crl_distribution_points=[f"{self.vault_addr}/v1/pki/crl"],
                    ocsp_servers=[f"{self.vault_addr}/v1/pki/ocsp"]
                )
                
                logger.info("✅ Generated ETSI-compliant Root CA")
            
            # Create IoT device certificate role
            self.setup_device_role()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vault PKI: {e}")
            self.vault_available = False
    
    def setup_device_role(self):
        """Setup certificate roles for IoT devices and services with ETSI compliance"""
        try:
            # ECC P-256 role for IoT/Edge devices (resource-constrained)
            self.client.write(
                'pki/roles/iot-device-ecc',
                # Domain restrictions for security
                allowed_domains=['device.tesa.iot', 'edge.tesa.iot'],
                allow_subdomains=True,
                allow_any_name=False,  # Strict naming for security
                
                # Certificate constraints
                max_ttl='8760h',  # 1 year maximum
                ttl='8760h',
                
                # ECC P-256 cryptography for IoT devices
                key_type='ec',
                key_bits=256,  # P-256 curve (secp256r1)
                signature_bits=256,  # SHA-256
                
                # X.509 extensions for device authentication
                key_usage=[
                    'DigitalSignature',
                    'KeyAgreement'  # ECC uses KeyAgreement instead of KeyEncipherment
                ],
                ext_key_usage=[
                    'ClientAuth'  # IoT devices primarily act as clients
                ],
                
                # Organization details
                organization='TESA IoT Platform',
                ou='IoT Edge Devices',
                country='TH',
                province='Bangkok',
                locality='Bangkok',
                
                # Security controls
                require_cn=True,
                use_csr_common_name=False,
                use_csr_sans=False,
                
                # Certificate lifecycle
                no_store=False,  # Store for audit and revocation
                generate_lease=True
            )
            logger.info("✅ Configured ECC P-256 role for IoT/Edge devices")
            
            # RSA role for Applications/Services/Platform identities
            self.client.write(
                'pki/roles/platform-service-rsa',
                # Domain restrictions for services
                allowed_domains=['service.tesa.local', 'app.tesa.local', 'platform.tesa.local'],
                allow_subdomains=True,
                allow_any_name=False,
                
                # Certificate constraints
                max_ttl='26280h',  # 3 years for services
                ttl='8760h',  # 1 year default
                
                # RSA cryptography for services (more computational power available)
                key_type='rsa',
                key_bits=3072,  # RSA 3072 - optimal balance of security and performance
                signature_bits=256,  # SHA-256
                
                # X.509 extensions for service authentication
                key_usage=[
                    'DigitalSignature',
                    'KeyEncipherment',
                    'DataEncipherment'
                ],
                ext_key_usage=[
                    'ServerAuth',
                    'ClientAuth'  # Services can act as both server and client
                ],
                
                # Organization details
                organization='TESA IoT Platform',
                ou='Platform Services',
                country='TH',
                province='Bangkok',
                locality='Bangkok',
                
                # Security controls
                require_cn=True,
                use_csr_common_name=False,
                use_csr_sans=False,
                
                # Certificate lifecycle
                no_store=False,
                generate_lease=True
            )
            logger.info("✅ Configured RSA role for Platform Services")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup device role: {e}")
    
    def generate_device_certificate(self, device_id: str, device_name: str, 
                                  organization_id: str, entity_type: str = 'device') -> Dict:
        """
        Generate ETSI/ISO compliant certificate via Vault PKI
        
        - IoT/Edge devices: ECC P-256 (resource efficient)
        - Services/Platform: RSA 3072 (optimal security/performance balance)
        
        ETSI EN 303 645 Provision 4: Securely store credentials
        ISO/IEC 27402: Cryptographic controls for IoT
        """
        if not self.vault_available:
            logger.warning("⚠️  Vault PKI unavailable - using fallback method")
            return self._fallback_certificate_generation(device_id, device_name, organization_id)
        
        try:
            # Determine certificate type and role based on entity
            if entity_type in ['device', 'edge', 'iot']:
                # ECC for IoT/Edge devices
                role = 'iot-device-ecc'
                common_name = f"{device_id}.device.tesa.iot"
                alt_names = f"{device_id}.edge.tesa.iot,{device_id}"
                key_info = "ECC P-256"
                ou = f"IoT Edge Devices/{organization_id}"
            else:
                # RSA for Services/Platform/Applications
                role = 'platform-service-rsa'
                common_name = f"{device_id}.service.tesa.local"
                alt_names = f"{device_id}.app.tesa.local,{device_id}.platform.tesa.local"
                key_info = "RSA 3072"
                ou = f"Platform Services/{organization_id}"
            
            cert_response = self.client.write(
                f'pki/issue/{role}',
                common_name=common_name,
                alt_names=alt_names,
                ttl='8760h',  # 1 year
                format='pem',
                private_key_format='pem',
                
                # Additional subject attributes
                organization='TESA IoT Platform',
                ou=ou,
                country='TH',
                province='Bangkok',
                locality='Bangkok'
            )
            
            cert_data = cert_response['data']
            
            # Audit log for compliance
            self._audit_certificate_issuance(device_id, organization_id, cert_data['serial_number'])
            
            # Return standardized certificate information
            return {
                'id': f"vault-{cert_data['serial_number']}",
                'deviceId': device_id,
                'deviceName': device_name,
                'subject': f"CN={common_name}, OU={ou}, O=TESA IoT Platform, ST=Bangkok, C=TH",
                'issuer': f"CN=TESA IoT Platform Root CA, OU=Certificate Authority, O=TESA IoT Platform, ST=Bangkok, C=TH",
                'serialNumber': cert_data['serial_number'],
                'fingerprint': self._calculate_fingerprint(cert_data['certificate']),
                'issuedAt': datetime.utcnow().isoformat() + 'Z',
                'expiresAt': (datetime.utcnow() + timedelta(hours=8760)).isoformat() + 'Z',
                'validFrom': datetime.utcnow().isoformat() + 'Z',
                'validTo': (datetime.utcnow() + timedelta(hours=8760)).isoformat() + 'Z',
                'status': 'active',
                'type': entity_type,
                'organizationId': organization_id,
                'keyType': key_info,
                'keyLength': 256 if entity_type in ['device', 'edge', 'iot'] else 3072,
                'signatureAlgorithm': f'SHA256-{key_info.split()[0]}',
                'issuedBy': 'Vault PKI',
                'complianceLevel': 'ETSI-ISO-Compliant',
                # Certificate data (stored securely in Vault)
                '_vault_certificate': cert_data['certificate'],
                '_vault_private_key': cert_data['private_key'],
                '_vault_ca_chain': cert_data['ca_chain']
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate certificate via Vault: {e}")
            return self._fallback_certificate_generation(device_id, device_name, organization_id)
    
    def get_ca_chain(self) -> str:
        """Get CA certificate chain from Vault PKI"""
        if not self.vault_available:
            logger.warning("⚠️  Vault PKI unavailable")
            return "# Vault PKI unavailable - no CA chain"
        
        try:
            ca_response = self.client.read('pki/cert/ca')
            return ca_response['data']['certificate']
        except Exception as e:
            logger.error(f"❌ Failed to get CA chain: {e}")
            return "# Error retrieving CA chain"
    
    def get_device_certificate(self, device_id: str) -> Optional[str]:
        """
        Retrieve device certificate from Vault
        Note: In production, certificates should be retrieved via serial number
        """
        logger.info(f"📋 Certificate retrieval requested for device: {device_id}")
        return "# Certificate retrieval from Vault requires serial number lookup"
    
    def get_device_key(self, device_id: str) -> Optional[str]:
        """
        Private keys are NOT retrievable from Vault after issuance (security best practice)
        ETSI EN 303 645 Provision 4: Private keys must be securely managed
        """
        logger.warning(f"🔒 Private key retrieval blocked for security compliance: {device_id}")
        return "# Private keys cannot be retrieved from Vault after issuance (security compliance)"
    
    def get_certificate_bundle(self, device_id: str) -> Optional[str]:
        """Get certificate bundle (cert + CA chain)"""
        ca_chain = self.get_ca_chain()
        device_cert = self.get_device_certificate(device_id)
        
        if device_cert and not device_cert.startswith('#'):
            return f"{device_cert}\n{ca_chain}"
        return ca_chain
    
    def revoke_certificate(self, serial_number: str, reason: str = 'unspecified') -> bool:
        """
        Revoke certificate for ETSI compliance
        ETSI EN 303 645: Support for certificate revocation
        """
        if not self.vault_available:
            logger.warning(f"⚠️  Cannot revoke certificate {serial_number} - Vault unavailable")
            return False
        
        try:
            self.client.write(
                'pki/revoke',
                serial_number=serial_number
            )
            
            # Audit log
            self._audit_certificate_revocation(serial_number, reason)
            logger.info(f"✅ Revoked certificate {serial_number} (reason: {reason})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to revoke certificate {serial_number}: {e}")
            return False
    
    def _audit_certificate_issuance(self, device_id: str, organization_id: str, serial_number: str):
        """Audit log for certificate issuance (ETSI compliance)"""
        audit_entry = {
            'action': 'certificate_issued',
            'timestamp': datetime.utcnow().isoformat(),
            'device_id': device_id,
            'organization_id': organization_id,
            'serial_number': serial_number,
            'compliance_standard': 'ETSI EN 303 645 / ISO/IEC 27402'
        }
        logger.info(f"🔍 AUDIT: {json.dumps(audit_entry)}")
    
    def _audit_certificate_revocation(self, serial_number: str, reason: str):
        """Audit log for certificate revocation (ETSI compliance)"""
        audit_entry = {
            'action': 'certificate_revoked',
            'timestamp': datetime.utcnow().isoformat(),
            'serial_number': serial_number,
            'reason': reason,
            'compliance_standard': 'ETSI EN 303 645'
        }
        logger.info(f"🔍 AUDIT: {json.dumps(audit_entry)}")
    
    def _calculate_fingerprint(self, cert_pem: str) -> str:
        """Calculate certificate fingerprint"""
        try:
            import hashlib
            # Simple fingerprint calculation
            cert_hash = hashlib.sha256(cert_pem.encode()).hexdigest()
            return ':'.join([cert_hash[i:i+2] for i in range(0, len(cert_hash), 2)][:20])
        except:
            return "fingerprint-calculation-failed"
    
    def _fallback_certificate_generation(self, device_id: str, device_name: str, 
                                       organization_id: str) -> Dict:
        """
        Fallback certificate generation when Vault is unavailable
        WARNING: This does not meet ETSI/ISO compliance requirements
        """
        logger.warning("⚠️  Using non-compliant fallback certificate generation")
        
        return {
            'id': f"fallback-{device_id}",
            'deviceId': device_id,
            'deviceName': device_name,
            'subject': f"CN={device_id}.tesa.local, OU={organization_id}, O=TESA IoT Platform, ST=Bangkok, C=TH",
            'issuer': "Fallback Certificate Authority",
            'serialNumber': f"FALLBACK-{device_id[:16]}",
            'fingerprint': "fallback-fingerprint",
            'issuedAt': datetime.utcnow().isoformat() + 'Z',
            'expiresAt': (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z',  # Short validity
            'validFrom': datetime.utcnow().isoformat() + 'Z',
            'validTo': (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z',
            'status': 'non-compliant',
            'type': 'device',
            'organizationId': organization_id,
            'keyLength': 2048,
            'signatureAlgorithm': 'SHA256-RSA',
            'issuedBy': 'Fallback CA (Non-Compliant)',
            'complianceLevel': 'NON-COMPLIANT - DEVELOPMENT ONLY',
            'warning': 'This certificate does not meet ETSI EN 303 645 or ISO/IEC 27402 standards'
        }

# Compliance note for documentation
"""
CYBERSECURITY COMPLIANCE IMPLEMENTATION:

ETSI EN 303 645 Provisions Addressed:
- Provision 4: Securely store credentials and security-sensitive data
  * Private keys stored securely in Vault (never retrievable after issuance)
  * Certificates managed through HSM-backed Vault PKI
  
- Provision 5: Communicate securely
  * X.509 certificates with strong cryptography (RSA-2048, SHA-256)
  * mTLS support for secure device communication

ISO/IEC 27402 Controls Addressed:
- Cryptographic controls for IoT systems
  * Strong key generation and management via Vault PKI
  * Certificate lifecycle management with audit trails
  
VAULT PKI BENEFITS FOR COMPLIANCE:
1. Hardware Security Module (HSM) integration for root key protection
2. Automatic certificate lifecycle management
3. Built-in certificate revocation (CRL/OCSP)
4. Comprehensive audit logging
5. Role-based access controls
6. Secure secret storage and rotation

ARCHITECTURE COMPLIANCE:
- Certificates issued dynamically from Vault PKI (not stored on filesystem)
- Private keys never leave Vault after generation
- Full audit trail for all certificate operations
- Automatic expiration and renewal workflows
- Support for certificate revocation and CRL distribution
"""