# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - PKI Provisioning Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend

from ..core.database import get_db
from .audit_service import audit_log, AuditAction
from .vault_private_key_storage_service import vault_private_key_storage_service
from .vault_certificate_storage_service import vault_certificate_storage_service

logger = logging.getLogger(__name__)

class PKIProvisioningError(Exception):
    """Custom PKI provisioning error."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class PKIProvisioningService:
    """Service for PKI certificate provisioning and management."""
    
    def __init__(self):
        self.db = None
        
    def get_db(self):
        """Get database connection with lazy initialization."""
        if not self.db:
            self.db = get_db()
        return self.db
    
    def generate_device_certificate(self, device_data: Dict, user: Dict, vault_client=None) -> Dict:
        """
        Generate and issue a certificate for a device.
        
        Args:
            device_data: Device information
            user: User requesting the certificate
            vault_client: Vault client instance (optional)
            
        Returns:
            Certificate information
        """
        try:
            device_id = device_data.get('device_id')
            organization_id = device_data.get('organization_id')
            
            if not device_id:
                raise PKIProvisioningError("Device ID is required", "MISSING_DEVICE_ID")
            
            # Determine certificate algorithm
            cert_algorithm = device_data.get('certificate_algorithm', 'RSA-2048')
            validity_days = device_data.get('certificate_validity_days', 365)
            
            # Generate key pair based on algorithm
            if cert_algorithm.startswith('RSA'):
                key_size = int(cert_algorithm.split('-')[1]) if '-' in cert_algorithm else 2048
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=key_size,
                    backend=default_backend()
                )
            elif cert_algorithm.startswith('EC'):
                # Extract curve from algorithm (e.g., "EC-P256")
                curve_name = cert_algorithm.split('-')[1] if '-' in cert_algorithm else 'P256'
                if curve_name == 'P256':
                    curve = ec.SECP256R1()
                elif curve_name == 'P384':
                    curve = ec.SECP384R1()
                else:
                    curve = ec.SECP256R1()  # Default fallback
                
                private_key = ec.generate_private_key(curve, default_backend())
            else:
                # Default to RSA-2048
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
            
            # Try Vault PKI first if available
            if vault_client:
                try:
                    cert_info = self._issue_certificate_via_vault(
                        device_id, organization_id, private_key, validity_days, vault_client
                    )
                    if cert_info:
                        return cert_info
                except Exception as e:
                    logger.warning(f"Vault PKI issuance failed: {e}")

            # Fail CLOSED by default: a self-signed cert is neither CRL-revocable
            # (no Vault entry, so revocation can never be enforced) nor able to
            # chain to the Vault CA for EMQX mTLS. Minting one would break the
            # 'every issued cert is CRL-revocable' invariant the platform's
            # revocation guarantee depends on. Only allow the self-signed path
            # when an operator explicitly opts in for local development.
            allow_self_signed = os.environ.get(
                'ALLOW_SELF_SIGNED_DEV', ''
            ).strip().lower() in ('1', 'true', 'yes')

            if not allow_self_signed:
                raise PKIProvisioningError(
                    "Vault PKI is unavailable and self-signed issuance is "
                    "disabled (fail-closed). Refusing to mint a non-revocable, "
                    "non-mTLS-connectable certificate. Set ALLOW_SELF_SIGNED_DEV=true "
                    "only for local development to permit this.",
                    "VAULT_UNAVAILABLE",
                )

            logger.warning(
                "ALLOW_SELF_SIGNED_DEV is enabled: issuing a self-signed "
                "certificate that CANNOT be revoked via Vault CRL and CANNOT "
                "connect to EMQX mTLS. This must NOT be used in production."
            )
            return self._generate_self_signed_certificate(
                device_id, organization_id, private_key, validity_days
            )
            
        except PKIProvisioningError:
            # Fail-closed issuance refusal (e.g. Vault unavailable, self-signed
            # disabled); propagate unchanged with its accurate code.
            raise
        except Exception as e:
            logger.error(f"Error generating device certificate: {e}")
            raise PKIProvisioningError(f"Certificate generation failed: {str(e)}")

    def _issue_certificate_via_vault(self, device_id: str, organization_id: str,
                                   private_key, validity_days: int, vault_client) -> Optional[Dict]:
        """
        Issue certificate via Vault PKI.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            private_key: Private key for certificate
            validity_days: Certificate validity period
            vault_client: Vault client
            
        Returns:
            Certificate information or None if failed
        """
        try:
            # Generate CSR
            csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, device_id),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"TESA-IoT-{organization_id}"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Devices"),
            ])).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(f"{device_id}.iot.local"),
                    x509.DNSName(device_id),
                ]),
                critical=False,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Convert CSR to PEM
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
            
            # Issue certificate via Vault (INTERMEDIATE PKI to align with EMQX)
            # Normalize CN=DEVICE_ID and provide SANs for forward-compatibility
            response = vault_client.write(
                'pki-int/issue/device-cert',
                common_name=device_id,
                alt_names=f"{device_id}.device.tesa.iot,{device_id}.sensor.tesa.iot,{device_id}.gateway.tesa.iot",
                uri_sans=f"urn:tesa:iot:device:{device_id}",
                exclude_cn_from_sans=True,
                ttl=f"{validity_days}d",
                format='pem'
            )
            
            if response and 'data' in response:
                cert_data = response['data']
                serial_number = cert_data.get('serial_number')
                certificate_pem = cert_data.get('certificate')
                ca_chain_pem = cert_data.get('ca_chain', [])
                
                # Store certificate info in database
                self._store_certificate_info(device_id, organization_id, {
                    'serial_number': serial_number,
                    'certificate_pem': certificate_pem,
                    'ca_chain': ca_chain_pem,
                    'private_key_pem': private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ).decode(),
                    'issued_via': 'vault_pki',
                    'validity_days': validity_days
                })
                
                return {
                    'serial_number': serial_number,
                    'certificate': certificate_pem,
                    'ca_chain': ca_chain_pem,
                    'status': 'valid',
                    'issued_at': datetime.now().isoformat(),
                    'expires_at': (datetime.now() + timedelta(days=validity_days)).isoformat(),
                    'issuer': 'vault_pki'
                }
            
        except Exception as e:
            logger.error(f"Vault PKI certificate issuance failed: {e}")
            
        return None
    
    def _generate_self_signed_certificate(self, device_id: str, organization_id: str,
                                        private_key, validity_days: int) -> Dict:
        """
        Generate a self-signed certificate.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            private_key: Private key for certificate
            validity_days: Certificate validity period
            
        Returns:
            Certificate information
        """
        try:
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, device_id),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"TESA-IoT-{organization_id}"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Devices"),
            ])
            
            # Generate serial number
            serial_number = uuid.uuid4().int & (1 << 64) - 1
            
            certificate = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                serial_number
            ).not_valid_before(
                datetime.now()
            ).not_valid_after(
                datetime.now() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(f"{device_id}.iot.local"),
                    x509.DNSName(device_id),
                ]),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True,
            ).sign(private_key, hashes.SHA256(), default_backend())
            
            # Convert to PEM format
            certificate_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
            private_key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            
            # Store certificate info
            self._store_certificate_info(device_id, organization_id, {
                'serial_number': hex(serial_number),
                'certificate_pem': certificate_pem,
                'private_key_pem': private_key_pem,
                'issued_via': 'self_signed',
                'validity_days': validity_days
            })
            
            return {
                'serial_number': hex(serial_number),
                'certificate': certificate_pem,
                'status': 'valid',
                'issued_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=validity_days)).isoformat(),
                'issuer': 'self_signed'
            }
            
        except Exception as e:
            logger.error(f"Self-signed certificate generation failed: {e}")
            raise PKIProvisioningError(f"Self-signed certificate generation failed: {str(e)}")
    
    def _store_certificate_info(self, device_id: str, organization_id: str, cert_info: Dict):
        """
        Store certificate information securely.

        SECURITY: Private keys are stored ONLY in Vault, NOT in MongoDB.
        MongoDB stores only metadata and vault path references.

        Args:
            device_id: Device identifier
            organization_id: Organization ID
            cert_info: Certificate information
        """
        try:
            db = self.get_db()

            vault_key_path = None
            vault_cert_path = None
            key_fingerprint = None
            cert_fingerprint = None

            # Store private key in Vault (if provided)
            private_key_pem = cert_info.get('private_key_pem')
            if private_key_pem:
                try:
                    key_result = vault_private_key_storage_service.store_private_key(
                        device_id=device_id,
                        private_key_pem=private_key_pem,
                        organization_id=organization_id,
                        algorithm=cert_info.get('algorithm'),
                        metadata={
                            'issued_via': cert_info.get('issued_via', 'unknown'),
                            'serial_number': cert_info.get('serial_number')
                        }
                    )
                    vault_key_path = key_result.get('vault_key_path')
                    key_fingerprint = key_result.get('key_fingerprint')
                    logger.info(f"Stored private key in Vault for device {device_id}")
                except Exception as e:
                    logger.error(f"Failed to store private key in Vault for device {device_id}: {e}")
                    # Continue without private key in Vault - will be logged but not stored in DB

            # Store certificate in Vault
            certificate_pem = cert_info.get('certificate_pem')
            if certificate_pem:
                try:
                    cert_result = vault_certificate_storage_service.store_certificate(
                        device_id=device_id,
                        certificate_pem=certificate_pem,
                        organization_id=organization_id,
                        ca_chain=cert_info.get('ca_chain', []),
                        serial_number=cert_info.get('serial_number'),
                        metadata={
                            'issued_via': cert_info.get('issued_via', 'unknown'),
                            'validity_days': cert_info.get('validity_days', 365)
                        }
                    )
                    vault_cert_path = cert_result.get('vault_cert_path')
                    cert_fingerprint = cert_result.get('cert_fingerprint')
                    logger.info(f"Stored certificate in Vault for device {device_id}")
                except Exception as e:
                    logger.error(f"Failed to store certificate in Vault for device {device_id}: {e}")

            # Store ONLY metadata in MongoDB - NO private_key_pem!
            certificate_record = {
                'device_id': device_id,
                'organization_id': organization_id,
                'serial_number': cert_info['serial_number'],
                # SECURITY: Store Vault references instead of actual key/cert
                'vault_key_path': vault_key_path,
                'vault_cert_path': vault_cert_path,
                'key_fingerprint': key_fingerprint,
                'cert_fingerprint': cert_fingerprint,
                # Metadata only - NO certificate_pem or private_key_pem
                'ca_chain_count': len(cert_info.get('ca_chain', [])),
                'issued_via': cert_info.get('issued_via', 'unknown'),
                'validity_days': cert_info.get('validity_days', 365),
                'status': 'valid',
                'issued_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(days=cert_info.get('validity_days', 365)),
                'created_at': datetime.now()
            }

            db.device_certificates.insert_one(certificate_record)

            # Update device record with metadata only
            db.devices.update_one(
                {'device_id': device_id, 'organization_id': organization_id},
                {
                    '$set': {
                        'certificate_serial': cert_info['serial_number'],
                        'certificate_status': 'valid',
                        'certificate_issued_at': datetime.now(),
                        'certificate_expires_at': datetime.now() + timedelta(days=cert_info.get('validity_days', 365)),
                        'vault_key_path': vault_key_path,
                        'vault_cert_path': vault_cert_path
                    }
                }
            )

            logger.info(f"Stored certificate metadata for device {device_id} (keys/certs in Vault)")

        except Exception as e:
            logger.error(f"Error storing certificate info: {e}")
    
    def revoke_device_certificate(self, device_id: str, organization_id: str, 
                                reason: str, user: Dict, vault_client=None) -> bool:
        """
        Revoke a device certificate.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            reason: Revocation reason
            user: User performing revocation
            vault_client: Vault client (optional)
            
        Returns:
            bool: True if successful
        """
        try:
            db = self.get_db()
            
            # Get certificate info
            cert_record = db.device_certificates.find_one({
                'device_id': device_id,
                'organization_id': organization_id,
                'status': 'valid'
            })
            
            if not cert_record:
                raise PKIProvisioningError("Certificate not found", "CERT_NOT_FOUND")
            
            # Revoke via Vault PKI (fail CLOSED). Certs are issued from the
            # intermediate mount (pki-int), so revoke there - NOT 'pki'.
            #
            # We do NOT gate this on issued_via=='vault_pki'. Gating on that tag
            # would let an old/mistagged record skip the CRL and stay
            # connectable. Instead, every serial that looks Vault-issued is
            # ALWAYS pushed to pki-int/revoke, and any failure is fatal so the
            # platform never reports "revoked" while the cert can still connect.
            #
            # Only a genuinely non-Vault serial (e.g. a legacy self_signed record
            # that never had a Vault entry and therefore cannot chain to the CA
            # nor connect to EMQX mTLS) is exempt from the Vault call, and even
            # then only when it is explicitly tagged as such.
            # Reuse the canonical serial normalizer from device_service so the
            # serial is sent to Vault in its expected 'xx:xx:..' colon form.
            from .device_service import _normalize_cert_serial
            serial_number = cert_record.get('serial_number')
            normalized_serial = _normalize_cert_serial(serial_number)
            is_self_signed = cert_record.get('issued_via') == 'self_signed'

            if is_self_signed and not normalized_serial:
                # Non-revocable, non-connectable legacy record: nothing to push
                # to the CRL. Safe to fall through to the DB status flip.
                logger.info(
                    f"Certificate for device {device_id} is self_signed with no "
                    f"Vault serial; no CRL entry to revoke"
                )
            else:
                if not normalized_serial:
                    raise PKIProvisioningError(
                        "Certificate has no usable serial to revoke in Vault PKI",
                        "NO_SERIAL",
                    )
                if not vault_client:
                    raise PKIProvisioningError(
                        "Vault client required to revoke a certificate",
                        "VAULT_UNAVAILABLE",
                    )
                pki_mount = os.environ.get('VAULT_PKI_INT_MOUNT', 'pki-int').strip('/')
                try:
                    vault_client.write(
                        f'{pki_mount}/revoke',
                        serial_number=normalized_serial
                    )
                    logger.info(
                        f"Revoked certificate via Vault PKI ({pki_mount}): "
                        f"{normalized_serial}"
                    )
                    # Refresh the CRL so the broker/proxy reject it promptly.
                    try:
                        vault_client.read(f'{pki_mount}/crl/rotate')
                    except Exception as rotate_err:
                        logger.warning(f"Vault CRL rotate after revoke returned: {rotate_err}")
                except Exception as e:
                    msg = str(e).lower()
                    if 'already revoked' not in msg and 'already_revoked' not in msg:
                        raise PKIProvisioningError(
                            f"Vault PKI revocation failed: {e}",
                            "VAULT_REVOKE_FAILED",
                        )
                    logger.info(
                        f"Certificate {normalized_serial} was already revoked in Vault PKI"
                    )
            
            # Update certificate status in database
            db.device_certificates.update_one(
                {'_id': cert_record['_id']},
                {
                    '$set': {
                        'status': 'revoked',
                        'revoked_at': datetime.now(),
                        'revoked_by': user.get('email', ''),
                        'revocation_reason': reason
                    }
                }
            )
            
            # Update device record
            db.devices.update_one(
                {'device_id': device_id, 'organization_id': organization_id},
                {
                    '$set': {
                        'certificate_status': 'revoked',
                        'certificate_revoked_at': datetime.now(),
                        'certificate_revoked_by': user.get('email', ''),
                        'certificate_revoke_reason': reason
                    }
                }
            )
            
            # Audit log
            audit_log(
                action=AuditAction.CERTIFICATE_REVOKE,
                user=user,
                resource_type='certificate',
                resource_id=cert_record['serial_number'],
                details={
                    'device_id': device_id,
                    'reason': reason,
                    'issued_via': cert_record.get('issued_via')
                }
            )
            
            logger.info(f"Revoked certificate for device {device_id}")
            return True
            
        except PKIProvisioningError:
            # Already a fail-closed revocation error (e.g. Vault unavailable or
            # Vault revoke failed); propagate it unchanged so callers see the
            # accurate code instead of a generic wrapper.
            raise
        except Exception as e:
            logger.error(f"Error revoking certificate: {e}")
            raise PKIProvisioningError(f"Certificate revocation failed: {str(e)}")

    def get_certificate_status(self, device_id: str, organization_id: str) -> Optional[Dict]:
        """
        Get certificate status for a device.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            
        Returns:
            Certificate status information or None
        """
        try:
            db = self.get_db()
            
            cert_record = db.device_certificates.find_one({
                'device_id': device_id,
                'organization_id': organization_id
            }, sort=[('issued_at', -1)])  # Get latest certificate
            
            if not cert_record:
                return None
            
            # Check if certificate is expired
            current_time = datetime.now()
            is_expired = cert_record.get('expires_at', current_time) < current_time
            
            status = cert_record.get('status', 'unknown')
            if is_expired and status == 'valid':
                status = 'expired'
            
            return {
                'serial_number': cert_record.get('serial_number'),
                'status': status,
                'issued_at': cert_record.get('issued_at').isoformat() if cert_record.get('issued_at') else None,
                'expires_at': cert_record.get('expires_at').isoformat() if cert_record.get('expires_at') else None,
                'issued_via': cert_record.get('issued_via'),
                'revoked_at': cert_record.get('revoked_at').isoformat() if cert_record.get('revoked_at') else None,
                'revocation_reason': cert_record.get('revocation_reason')
            }
            
        except Exception as e:
            logger.error(f"Error getting certificate status: {e}")
            return None
    
    def bulk_issue_certificates(self, devices: List[Dict], user: Dict, vault_client=None) -> Dict:
        """
        Bulk issue certificates for multiple devices.
        
        Args:
            devices: List of device data
            user: User requesting certificates
            vault_client: Vault client (optional)
            
        Returns:
            Results summary
        """
        try:
            results = {
                'successful': 0,
                'failed': 0,
                'errors': [],
                'certificates': []
            }
            
            for device_data in devices:
                try:
                    cert_info = self.generate_device_certificate(device_data, user, vault_client)
                    results['successful'] += 1
                    results['certificates'].append({
                        'device_id': device_data.get('device_id'),
                        'serial_number': cert_info.get('serial_number'),
                        'status': 'issued'
                    })
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'device_id': device_data.get('device_id', 'unknown'),
                        'error': str(e)
                    })
                    logger.error(f"Failed to issue certificate for device {device_data.get('device_id')}: {e}")
            
            logger.info(f"Bulk certificate issuance: {results['successful']} successful, {results['failed']} failed")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk certificate issuance: {e}")
            raise PKIProvisioningError(f"Bulk certificate issuance failed: {str(e)}")

# Create service instance
pki_provisioning_service = PKIProvisioningService()
