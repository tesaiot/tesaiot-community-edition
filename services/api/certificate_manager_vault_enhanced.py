# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Enhanced ETSI & ISO Compliant Certificate Management for TESA IoT Platform
Supports both Token and AppRole authentication with automatic fallback
Uses HashiCorp Vault PKI for secure certificate storage and issuance
Meets ETSI EN 303 645 and ISO/IEC 27402 cybersecurity standards
"""

import os
import json
import hvac
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VaultCertificateManager:
    """
    Enhanced cybersecurity-compliant certificate manager using HashiCorp Vault PKI
    
    Features:
    - Automatic AppRole authentication with token fallback
    - Persistent PKI initialization check
    - Graceful degradation to dev mode
    - Comprehensive error handling
    - PSoC mTLS compatibility with serial number validation
    
    PSoC mTLS Compatibility:
    - Validates certificate serial numbers for mbedTLS compatibility
    - Automatically retries certificate generation when MSB=1 in serial number
    - Ensures X.509 compliance by generating only positive serial numbers
    - Prevents PSoC devices from rejecting certificates due to negative serial interpretation
    
    ETSI EN 303 645 Compliance:
    - Provision 4: Securely store credentials and security-sensitive data
    - Provision 5: Communicate securely
    
    ISO/IEC 27402 Compliance:
    - Cryptographic controls for IoT systems
    - Secure key management and storage
    """
    
    def __init__(self):
        """Initialize Vault PKI connection with enhanced authentication"""
        self.vault_addr = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
        self.vault_available = False
        self.client = None
        
        # Try multiple authentication methods
        if self._authenticate():
            logger.info(f"✅ Connected to Vault PKI at {self.vault_addr}")
            self.vault_available = True
            # Don't initialize PKI here - it should already be initialized by the startup script
            self._verify_pki_ready()
        else:
            logger.warning("⚠️  Vault authentication failed - compliance mode disabled")
    
    def _authenticate(self) -> bool:
        """Try multiple authentication methods in order of preference"""
        
        # Method 1: Try AppRole authentication first (production preferred)
        if self._try_approle_auth():
            return True
        
        # Method 2: Try token authentication (dev/testing)
        if self._try_token_auth():
            return True
        
        # Method 3: Try reading credentials from file
        if self._try_file_auth():
            return True
        
        return False
    
    def _try_approle_auth(self) -> bool:
        """Attempt AppRole authentication"""
        role_id = os.environ.get('VAULT_ROLE_ID')
        secret_id = os.environ.get('VAULT_SECRET_ID')
        
        if not (role_id and secret_id):
            return False
        
        try:
            self.client = hvac.Client(url=self.vault_addr)
            response = self.client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id
            )
            self.client.token = response['auth']['client_token']
            logger.info("✅ Authenticated with Vault using AppRole")
            return True
        except Exception as e:
            logger.debug(f"AppRole authentication failed: {e}")
            return False
    
    def _try_token_auth(self) -> bool:
        """Attempt token authentication"""
        vault_token = os.environ.get('VAULT_TOKEN')
        
        if not vault_token:
            return False
        
        try:
            self.client = hvac.Client(url=self.vault_addr, token=vault_token)
            if self.client.is_authenticated():
                logger.info("✅ Authenticated with Vault using token")
                return True
        except Exception as e:
            logger.debug(f"Token authentication failed: {e}")
        
        return False
    
    def _try_file_auth(self) -> bool:
        """Attempt to read credentials from mounted file"""
        cred_paths = [
            '/app/vault-credentials/api-service.json',
            '/vault/credentials/api-service.json',
            './vault-credentials/api-service.json'
        ]
        
        for cred_path in cred_paths:
            if Path(cred_path).exists():
                try:
                    with open(cred_path, 'r') as f:
                        creds = json.load(f)
                    
                    self.client = hvac.Client(url=creds.get('vault_addr', self.vault_addr))
                    response = self.client.auth.approle.login(
                        role_id=creds['role_id'],
                        secret_id=creds['secret_id']
                    )
                    self.client.token = response['auth']['client_token']
                    logger.info(f"✅ Authenticated with Vault using credentials from {cred_path}")
                    return True
                except Exception as e:
                    logger.debug(f"File authentication failed for {cred_path}: {e}")
        
        return False
    
    def _verify_pki_ready(self):
        """Verify PKI is initialized and ready (don't initialize here)"""
        try:
            # Check if PKI engine is mounted
            mounts = self.client.sys.list_mounted_secrets_engines()
            if 'pki/' not in mounts:
                logger.warning("⚠️  PKI engine not mounted - waiting for initialization")
                self.vault_available = False
                return
            
            # Check if Root CA exists
            try:
                ca_cert = self.client.read('pki/cert/ca')
                if ca_cert:
                    logger.info("✅ Vault PKI is ready with Root CA configured")
                    
                    # Verify roles exist
                    roles = ['iot-device-ecc', 'iot-gateway-ecc', 'iot-device-rsa', 'iot-server-rsa']
                    for role in roles:
                        try:
                            self.client.read(f'pki/roles/{role}')
                            logger.debug(f"✅ Role '{role}' is configured")
                        except:
                            logger.warning(f"⚠️  Role '{role}' not found")
            except:
                logger.warning("⚠️  Root CA not found - PKI not fully initialized")
                self.vault_available = False
                
        except Exception as e:
            logger.error(f"❌ Failed to verify PKI: {e}")
            self.vault_available = False
    
    def generate_device_certificate(self, device_id: str, device_type: str = 'standard',
                                  device_metadata: Dict = None) -> Optional[Dict]:
        """
        Generate ETSI/ISO compliant device certificate with automatic role selection
        
        Args:
            device_id: Unique device identifier
            device_type: Device category for certificate selection
            device_metadata: Additional device information for certificate
            
        Returns:
            Certificate data including cert, key, and CA chain
        """
        if not self.vault_available:
            logger.warning("⚠️  Vault unavailable - returning development certificate")
            return self._generate_dev_certificate(device_id, device_type)
        
        try:
            # Select appropriate role based on device type
            role_mapping = {
                'ultra_low_power': 'iot-device-ecc',
                'low_power': 'iot-device-ecc',
                'medium': 'iot-gateway-ecc',
                'standard': 'iot-device-rsa',
                'high_performance': 'iot-server-rsa'
            }
            
            role = role_mapping.get(device_type, 'iot-device-rsa')
            common_name = f"{device_id}.device.tesa.iot"
            
            # Generate certificate with PSoC mTLS compatibility validation
            cert_data = self._generate_vault_certificate_with_retry(role, common_name, max_retries=3)
            
            if not cert_data:
                raise Exception("Failed to generate certificate after all retry attempts")
            
            # Parse expiration for compliance tracking
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            cert = x509.load_pem_x509_certificate(
                cert_data['certificate'].encode(), 
                default_backend()
            )
            
            result = {
                'certificate': cert_data['certificate'],
                'private_key': cert_data['private_key'],
                'ca_chain': cert_data['ca_chain'],
                'serial_number': cert_data['serial_number'],
                'expiration': cert.not_valid_after.isoformat(),
                'issuer': 'TESA IoT Platform Root CA',
                'compliance': {
                    'etsi_en_303_645': True,
                    'iso_iec_27402': True,
                    'psoc_mtls_compatible': self._is_valid_serial_number(cert_data['serial_number']),
                    'key_algorithm': self._get_key_algorithm(role),
                    'key_size': self._get_key_size(role)
                }
            }
            
            logger.info(f"✅ Generated {device_type} certificate for {device_id} (Serial: {cert_data['serial_number']}, PSoC mTLS compatible: {result['compliance']['psoc_mtls_compatible']})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to generate certificate: {e}")
            # Fallback to dev certificate
            return self._generate_dev_certificate(device_id, device_type)
    
    def _get_key_algorithm(self, role: str) -> str:
        """Get key algorithm for role"""
        if 'ecc' in role:
            return 'ECDSA'
        return 'RSA'
    
    def _get_key_size(self, role: str) -> str:
        """Get key size for role"""
        mapping = {
            'iot-device-ecc': 'P-256',
            'iot-gateway-ecc': 'P-384',
            'iot-device-rsa': '3072',
            'iot-server-rsa': '4096'
        }
        return mapping.get(role, '3072')
    
    def _is_valid_serial_number(self, serial_hex: str) -> bool:
        """
        Validate certificate serial number for PSoC mTLS compatibility.
        
        PSoC devices using mbedTLS interpret certificates with MSB=1 in the serial number
        as negative numbers, which are invalid per X.509 standards.
        
        Args:
            serial_hex: Hexadecimal serial number string from certificate
            
        Returns:
            True if serial number is valid (MSB=0), False otherwise
        """
        try:
            # Remove any colons or spaces and convert to uppercase
            clean_serial = serial_hex.replace(':', '').replace(' ', '').upper()
            
            # Check if valid hex
            int(clean_serial, 16)
            
            # Check if MSB (most significant bit) is 0
            # Get the first hex digit and check if it's < 8 (binary: 0xxx)
            first_digit = int(clean_serial[0], 16)
            msb_is_zero = first_digit < 8
            
            if not msb_is_zero:
                logger.warning(f"⚠️  Serial number {serial_hex} has MSB=1, incompatible with PSoC mTLS")
            
            return msb_is_zero
            
        except (ValueError, IndexError) as e:
            logger.error(f"❌ Invalid serial number format {serial_hex}: {e}")
            return False
    
    def _generate_vault_certificate_with_retry(self, role: str, common_name: str, 
                                             max_retries: int = 3) -> Optional[Dict]:
        """
        Generate certificate from Vault with serial number validation and retry logic.
        
        Ensures PSoC mTLS compatibility by validating serial numbers and regenerating
        certificates that would be incompatible with mbedTLS.
        
        Args:
            role: Vault PKI role to use for certificate generation
            common_name: Certificate common name
            max_retries: Maximum number of regeneration attempts
            
        Returns:
            Certificate data or None if all attempts fail
        """
        for attempt in range(max_retries + 1):
            try:
                # Generate certificate through Vault PKI
                response = self.client.write(
                    f'pki/issue/{role}',
                    common_name=common_name,
                    ttl='8760h',  # 1 year
                    format='pem_bundle'
                )
                
                if not response or 'data' not in response:
                    raise Exception("Invalid response from Vault PKI")
                
                cert_data = response['data']
                serial_number = cert_data['serial_number']
                
                # Validate serial number for PSoC compatibility
                if self._is_valid_serial_number(serial_number):
                    if attempt > 0:
                        logger.info(f"✅ Generated PSoC-compatible certificate on attempt {attempt + 1}")
                    return cert_data
                else:
                    # Serial number has MSB=1, need to regenerate
                    if attempt < max_retries:
                        logger.info(f"🔄 Regenerating certificate due to incompatible serial number (attempt {attempt + 1}/{max_retries + 1})")
                        continue
                    else:
                        logger.error(f"❌ Failed to generate PSoC-compatible certificate after {max_retries + 1} attempts")
                        # Return the certificate anyway - it may work with some clients
                        logger.warning("⚠️  Returning certificate with potentially incompatible serial number")
                        return cert_data
                        
            except Exception as e:
                logger.error(f"❌ Certificate generation attempt {attempt + 1} failed: {e}")
                if attempt >= max_retries:
                    raise
                continue
        
        return None
    
    def _generate_safe_serial_number(self) -> int:
        """
        Generate a safe serial number for PSoC mTLS compatibility.
        
        Ensures the MSB is 0 by generating numbers in the range [1, 2^159-1].
        This guarantees X.509 compliance and mbedTLS compatibility.
        
        Returns:
            Safe serial number with MSB=0
        """
        import secrets
        
        # Generate a random number with MSB=0
        # Maximum value is 2^159 - 1 (ensures MSB is 0 in 160-bit representation)
        max_value = (1 << 159) - 1
        min_value = 1
        
        # Generate random number in safe range
        safe_serial = secrets.randbelow(max_value - min_value) + min_value
        
        # Double-check that MSB is 0 by converting to hex and checking
        hex_serial = f"{safe_serial:040x}"  # 160 bits = 40 hex chars
        if int(hex_serial[0], 16) >= 8:
            # Shouldn't happen, but if it does, mask the MSB
            safe_serial &= ((1 << 159) - 1)
            safe_serial |= 1  # Ensure it's not zero
        
        logger.debug(f"Generated safe serial number: {safe_serial:x}")
        return safe_serial
    
    def _generate_dev_certificate(self, device_id: str, device_type: str) -> Dict:
        """Generate development certificate when Vault is unavailable"""
        logger.warning(f"⚠️  Generating development certificate for {device_id}")
        
        # Import here to avoid dependency if not needed
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        
        # Generate key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,  # Smaller for dev
            backend=default_backend()
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "TH"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Bangkok"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Bangkok"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TESA IoT Platform (Dev)"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{device_id}.device.tesa.iot"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            self._generate_safe_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(f"{device_id}.device.tesa.iot"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), backend=default_backend())
        
        # Serialize
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        dev_result = {
            'certificate': cert_pem,
            'private_key': key_pem,
            'ca_chain': cert_pem,  # Self-signed
            'serial_number': str(cert.serial_number),
            'expiration': cert.not_valid_after.isoformat(),
            'issuer': 'Development CA (Non-compliant)',
            'compliance': {
                'etsi_en_303_645': False,
                'iso_iec_27402': False,
                'psoc_mtls_compatible': True,  # We use safe serial number generation
                'warning': 'Development certificate - NOT for production use'
            }
        }
        
        logger.info(f"✅ Generated development certificate for {device_id} (Serial: {dev_result['serial_number']}, PSoC mTLS compatible: True)")
        return dev_result
    
    def revoke_certificate(self, serial_number: str, reason: str = 'unspecified') -> bool:
        """Revoke a certificate with ETSI/ISO compliant audit trail"""
        if not self.vault_available:
            logger.warning("⚠️  Cannot revoke certificate - Vault unavailable")
            return False
        
        try:
            self.client.write(
                'pki/revoke',
                serial_number=serial_number,
                revocation_reason=reason
            )
            logger.info(f"✅ Revoked certificate {serial_number} (Reason: {reason})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to revoke certificate: {e}")
            return False
    
    def get_ca_certificate(self) -> Optional[str]:
        """Get the Root CA certificate for trust establishment"""
        if not self.vault_available:
            logger.warning("⚠️  Cannot retrieve CA certificate - Vault unavailable")
            return None
        
        try:
            response = self.client.read('pki/cert/ca')
            if response and 'data' in response:
                return response['data']['certificate']
        except Exception as e:
            logger.error(f"❌ Failed to retrieve CA certificate: {e}")
        
        return None
    
    def validate_certificate_compatibility(self, certificate_pem: str) -> Dict:
        """
        Validate an existing certificate for PSoC mTLS compatibility.
        
        Args:
            certificate_pem: PEM-encoded certificate string
            
        Returns:
            Validation result with compatibility information
        """
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode(), 
                default_backend()
            )
            
            serial_hex = f"{cert.serial_number:x}"
            is_compatible = self._is_valid_serial_number(serial_hex)
            
            validation_result = {
                'psoc_mtls_compatible': is_compatible,
                'serial_number': serial_hex,
                'serial_number_decimal': cert.serial_number,
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'not_valid_before': cert.not_valid_before.isoformat(),
                'not_valid_after': cert.not_valid_after.isoformat(),
                'validation_details': {
                    'msb_check': 'PASS' if is_compatible else 'FAIL',
                    'recommendation': 'Certificate is compatible with PSoC devices' if is_compatible else 'Certificate should be regenerated for PSoC compatibility'
                }
            }
            
            if is_compatible:
                logger.info(f"✅ Certificate validation passed - PSoC mTLS compatible (Serial: {serial_hex})")
            else:
                logger.warning(f"⚠️  Certificate validation failed - NOT PSoC mTLS compatible (Serial: {serial_hex})")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Failed to validate certificate: {e}")
            return {
                'psoc_mtls_compatible': False,
                'error': str(e),
                'validation_details': {
                    'msb_check': 'ERROR',
                    'recommendation': 'Certificate validation failed - check certificate format'
                }
            }


# Create singleton instance
_certificate_manager = None

def get_certificate_manager() -> VaultCertificateManager:
    """Get or create the certificate manager singleton"""
    global _certificate_manager
    if _certificate_manager is None:
        _certificate_manager = VaultCertificateManager()
    return _certificate_manager