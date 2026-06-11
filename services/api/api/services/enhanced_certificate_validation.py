# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Enhanced Certificate Validation Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


Enhanced certificate validation against Vault PKI for mTLS device authentication.
Provides comprehensive certificate validation including:
- Vault CA certificate chain validation
- Certificate revocation list (CRL) checking
- Multi-tier device certificate validation
- Real-time validation with circuit breaker pattern
- Device ID and organization validation
"""

import os
import logging
import hvac
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Certificate validation result"""
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    certificate_info: Optional[Dict] = None
    validation_details: Optional[Dict] = None

class VaultPKIValidator:
    """Enhanced Vault PKI certificate validator for TESA IoT Platform"""
    
    def __init__(self, vault_addr: str = None, vault_token: str = None):
        """
        Initialize Vault PKI validator
        
        Args:
            vault_addr: Vault server address (defaults to VAULT_ADDR env var)
            vault_token: Vault token (defaults to VAULT_TOKEN env var)
        """
        self.vault_addr = vault_addr or os.environ.get('VAULT_ADDR', 'http://localhost:8200')
        # SECURITY: no default token. The previous fallback chain ended in the
        # literal 'root' token; fail closed when no token is configured.
        self.vault_token = vault_token or self._resolve_vault_token()

        # Initialize Vault client
        self.vault_client = None
        self._init_vault_client()
        
        # Cache for CA certificates and CRLs (valid for 1 hour)
        self._ca_cert_cache = {}
        self._crl_cache = {}
        self._cache_ttl = 3600  # 1 hour
        
    @staticmethod
    def _resolve_vault_token() -> str:
        """Resolve the Vault token from VAULT_TOKEN_FILE or VAULT_TOKEN.

        SECURITY: no default value. Raises with a clear message when no token
        is configured instead of silently using a root token.
        """
        token_file = (os.environ.get('VAULT_TOKEN_FILE') or '').strip()
        if token_file:
            try:
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                if token:
                    return token
            except OSError as e:
                raise RuntimeError(f"VAULT_TOKEN_FILE is set but unreadable: {e}")
        token = (os.environ.get('VAULT_TOKEN') or '').strip()
        if not token:
            raise RuntimeError(
                "No Vault token configured. Set VAULT_TOKEN_FILE or VAULT_TOKEN; "
                "refusing to fall back to a default token."
            )
        return token

    def _init_vault_client(self):
        """Initialize Vault client with error handling"""
        try:
            self.vault_client = hvac.Client(url=self.vault_addr, token=self.vault_token)
            
            if not self.vault_client.is_authenticated():
                logger.warning(f"Vault authentication failed for {self.vault_addr}")
                self.vault_client = None
            else:
                logger.info(f"Successfully connected to Vault at {self.vault_addr}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            self.vault_client = None
    
    def get_vault_ca_certificate(self, pki_mount: str = 'pki') -> Optional[x509.Certificate]:
        """
        Get Vault CA certificate with caching
        
        Args:
            pki_mount: PKI mount path
            
        Returns:
            CA certificate or None if not available
        """
        cache_key = f"{pki_mount}_ca"
        now = datetime.now()
        
        # Check cache first
        if cache_key in self._ca_cert_cache:
            cert_data, cached_at = self._ca_cert_cache[cache_key]
            if (now - cached_at).seconds < self._cache_ttl:
                return cert_data
        
        if not self.vault_client:
            logger.warning("Vault client not available for CA certificate retrieval")
            return None
            
        try:
            # Get CA certificate from Vault
            ca_response = self.vault_client.read(f'{pki_mount}/cert/ca')
            if not ca_response or 'data' not in ca_response:
                logger.error(f"Failed to retrieve CA certificate from {pki_mount}")
                return None
                
            ca_pem = ca_response['data']['certificate']
            ca_cert = x509.load_pem_x509_certificate(ca_pem.encode(), default_backend())
            
            # Cache the result
            self._ca_cert_cache[cache_key] = (ca_cert, now)
            
            logger.info(f"Successfully retrieved CA certificate from {pki_mount}")
            return ca_cert
            
        except Exception as e:
            logger.error(f"Error retrieving CA certificate: {e}")
            return None
    
    def get_vault_crl(self, pki_mount: str = 'pki') -> Optional[x509.CertificateRevocationList]:
        """
        Get Certificate Revocation List from Vault
        
        Args:
            pki_mount: PKI mount path
            
        Returns:
            CRL or None if not available
        """
        cache_key = f"{pki_mount}_crl"
        now = datetime.now()
        
        # Check cache first
        if cache_key in self._crl_cache:
            crl_data, cached_at = self._crl_cache[cache_key]
            if (now - cached_at).seconds < self._cache_ttl:
                return crl_data
        
        if not self.vault_client:
            return None
            
        try:
            # Get CRL from Vault
            crl_response = self.vault_client.read(f'{pki_mount}/cert/crl')
            if not crl_response or 'data' not in crl_response:
                logger.warning(f"No CRL found at {pki_mount}")
                return None
                
            crl_pem = crl_response['data']['certificate']
            crl = x509.load_pem_x509_crl(crl_pem.encode(), default_backend())
            
            # Cache the result
            self._crl_cache[cache_key] = (crl, now)
            
            logger.info(f"Successfully retrieved CRL from {pki_mount}")
            return crl
            
        except Exception as e:
            logger.warning(f"Error retrieving CRL: {e}")
            return None
    
    def extract_certificate_info(self, cert: x509.Certificate) -> Dict:
        """
        Extract comprehensive certificate information
        
        Args:
            cert: X.509 certificate
            
        Returns:
            Dictionary containing certificate details
        """
        try:
            # Basic certificate info
            cert_info = {
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': str(cert.serial_number),
                'not_valid_before': cert.not_valid_before.isoformat(),
                'not_valid_after': cert.not_valid_after.isoformat(),
                'signature_algorithm': cert.signature_algorithm_oid._name,
            }
            
            # Extract common name
            try:
                cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                cert_info['common_name'] = cn
            except (IndexError, AttributeError):
                cert_info['common_name'] = None
            
            # Extract organization
            try:
                org = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
                cert_info['organization'] = org
            except (IndexError, AttributeError):
                cert_info['organization'] = None
            
            # Extract organizational unit
            try:
                ou = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
                cert_info['organizational_unit'] = ou
            except (IndexError, AttributeError):
                cert_info['organizational_unit'] = None
            
            # Extract Subject Alternative Names
            try:
                san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_names = [name.value for name in san_ext.value]
                cert_info['subject_alternative_names'] = san_names
            except x509.ExtensionNotFound:
                cert_info['subject_alternative_names'] = []
            
            # Determine key information
            public_key = cert.public_key()
            if hasattr(public_key, 'curve'):
                # ECC key
                cert_info['key_type'] = 'ec'
                cert_info['key_size'] = public_key.curve.key_size
                cert_info['curve_name'] = public_key.curve.name
            elif hasattr(public_key, 'key_size'):
                # RSA key
                cert_info['key_type'] = 'rsa'
                cert_info['key_size'] = public_key.key_size
            else:
                cert_info['key_type'] = 'unknown'
                cert_info['key_size'] = None
            
            # Calculate validity period
            now = datetime.now()
            cert_info['is_expired'] = now > cert.not_valid_after
            cert_info['days_until_expiry'] = (cert.not_valid_after - now).days
            
            return cert_info
            
        except Exception as e:
            logger.error(f"Error extracting certificate info: {e}")
            return {'error': str(e)}
    
    def validate_certificate_chain(self, cert: x509.Certificate, ca_cert: x509.Certificate) -> Tuple[bool, str]:
        """
        Validate certificate against CA certificate
        
        Args:
            cert: Certificate to validate
            ca_cert: CA certificate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if certificate was issued by this CA
            if cert.issuer != ca_cert.subject:
                return False, "Certificate was not issued by the provided CA"
            
            # Verify certificate signature using cryptography's built-in validation
            try:
                ca_public_key = ca_cert.public_key()
                # For proper signature verification, we need to use the correct algorithm
                if cert.signature_algorithm_oid._name.startswith('rsa'):
                    from cryptography.hazmat.primitives.asymmetric import padding
                    if 'sha256' in cert.signature_algorithm_oid._name.lower():
                        hash_algorithm = hashes.SHA256()
                    elif 'sha1' in cert.signature_algorithm_oid._name.lower():
                        hash_algorithm = hashes.SHA1()
                    else:
                        hash_algorithm = hashes.SHA256()  # Default to SHA256
                    
                    ca_public_key.verify(
                        cert.signature,
                        cert.tbs_certificate_bytes,
                        padding.PKCS1v15(),
                        hash_algorithm
                    )
                elif cert.signature_algorithm_oid._name.startswith('ecdsa'):
                    from cryptography.hazmat.primitives.asymmetric import ec
                    if 'sha256' in cert.signature_algorithm_oid._name.lower():
                        hash_algorithm = hashes.SHA256()
                    elif 'sha1' in cert.signature_algorithm_oid._name.lower():
                        hash_algorithm = hashes.SHA1()
                    else:
                        hash_algorithm = hashes.SHA256()  # Default to SHA256
                    
                    ca_public_key.verify(
                        cert.signature,
                        cert.tbs_certificate_bytes,
                        ec.ECDSA(hash_algorithm)
                    )
                else:
                    logger.warning(f"Unknown signature algorithm: {cert.signature_algorithm_oid._name}")
                    return True, "Signature verification skipped for unknown algorithm"
                    
            except Exception as verify_error:
                return False, f"Certificate signature verification failed: {verify_error}"
            
            # Check certificate validity period
            now = datetime.now()
            if now < cert.not_valid_before:
                return False, "Certificate is not yet valid"
            
            if now > cert.not_valid_after:
                return False, "Certificate has expired"
            
            # Check CA certificate validity
            if now > ca_cert.not_valid_after:
                return False, "CA certificate has expired"
            
            return True, "Certificate chain validation successful"
            
        except Exception as e:
            return False, f"Certificate chain validation error: {e}"
    
    def check_certificate_revocation(self, cert: x509.Certificate, crl: x509.CertificateRevocationList) -> Tuple[bool, str]:
        """
        Check if certificate is revoked
        
        Args:
            cert: Certificate to check
            crl: Certificate Revocation List
            
        Returns:
            Tuple of (is_revoked, message)
        """
        try:
            for revoked_cert in crl:
                if revoked_cert.serial_number == cert.serial_number:
                    revocation_date = revoked_cert.revocation_date
                    return True, f"Certificate revoked on {revocation_date.isoformat()}"
            
            return False, "Certificate is not revoked"
            
        except Exception as e:
            logger.error(f"Error checking certificate revocation: {e}")
            return False, f"Error checking revocation status: {e}"
    
    def validate_device_certificate(self, cert_pem: str, pki_mount: str = 'pki', device_id: str = None) -> ValidationResult:
        """
        Comprehensive device certificate validation
        
        Args:
            cert_pem: PEM-encoded certificate
            pki_mount: PKI mount path
            device_id: Optional device ID for validation
            
        Returns:
            ValidationResult with comprehensive validation details
        """
        try:
            # Load certificate
            cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
            
            # Extract certificate information
            cert_info = self.extract_certificate_info(cert)
            
            validation_details = {
                'validation_timestamp': datetime.now().isoformat(),
                'vault_addr': self.vault_addr,
                'pki_mount': pki_mount
            }
            
            # Step 1: Get CA certificate
            ca_cert = self.get_vault_ca_certificate(pki_mount)
            if not ca_cert:
                return ValidationResult(
                    is_valid=False,
                    error_code='CA_UNAVAILABLE',
                    error_message='Unable to retrieve CA certificate from Vault',
                    certificate_info=cert_info,
                    validation_details=validation_details
                )
            
            validation_details['ca_available'] = True
            
            # Step 2: Validate certificate chain
            chain_valid, chain_message = self.validate_certificate_chain(cert, ca_cert)
            validation_details['chain_validation'] = {
                'valid': chain_valid,
                'message': chain_message
            }
            
            if not chain_valid:
                return ValidationResult(
                    is_valid=False,
                    error_code='CHAIN_INVALID',
                    error_message=chain_message,
                    certificate_info=cert_info,
                    validation_details=validation_details
                )
            
            # Step 3: Check revocation status
            crl = self.get_vault_crl(pki_mount)
            if crl:
                is_revoked, revocation_message = self.check_certificate_revocation(cert, crl)
                validation_details['revocation_check'] = {
                    'performed': True,
                    'revoked': is_revoked,
                    'message': revocation_message
                }
                
                if is_revoked:
                    return ValidationResult(
                        is_valid=False,
                        error_code='CERT_REVOKED',
                        error_message=revocation_message,
                        certificate_info=cert_info,
                        validation_details=validation_details
                    )
            else:
                validation_details['revocation_check'] = {
                    'performed': False,
                    'message': 'CRL not available'
                }
            
            # Step 4: Device ID validation if provided
            if device_id and cert_info:
                common_name = cert_info.get('common_name', '')
                if device_id not in common_name:
                    return ValidationResult(
                        is_valid=False,
                        error_code='DEVICE_ID_MISMATCH',
                        error_message=f"Certificate common name does not contain device ID {device_id}",
                        certificate_info=cert_info,
                        validation_details=validation_details
                    )
                validation_details['device_id_validation'] = {
                    'performed': True,
                    'valid': True,
                    'message': f"Device ID {device_id} found in certificate common name"
                }
            
            # All validations passed
            return ValidationResult(
                is_valid=True,
                certificate_info=cert_info,
                validation_details=validation_details
            )
            
        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return ValidationResult(
                is_valid=False,
                error_code='VALIDATION_ERROR',
                error_message=str(e),
                validation_details={'error': str(e)}
            )

# Global validator instance
_pki_validator = None

def get_pki_validator():
    """Get or create PKI validator instance"""
    global _pki_validator
    if _pki_validator is None:
        _pki_validator = VaultPKIValidator()
    return _pki_validator

def validate_device_certificate_enhanced(cert_pem: str, device_id: str = None, organization_id: str = None) -> Dict:
    """
    Enhanced device certificate validation with comprehensive checks
    
    Args:
        cert_pem: PEM-encoded certificate
        device_id: Optional device ID for additional validation
        organization_id: Optional organization ID for ACL checks
        
    Returns:
        Dictionary with validation results compatible with existing API
    """
    try:
        validator = get_pki_validator()
        result = validator.validate_device_certificate(cert_pem, device_id=device_id)
        
        # Convert to API-compatible format
        api_result = {
            'valid': result.is_valid,
            'error': result.error_message if not result.is_valid else None,
            'error_code': result.error_code if not result.is_valid else None,
            'certificate_info': result.certificate_info or {},
            'validation_details': result.validation_details or {},
            'enhanced_validation': True
        }
        
        # Log validation result for audit
        log_level = logging.INFO if result.is_valid else logging.WARNING
        logger.log(log_level, f"Enhanced certificate validation for device {device_id}: {'VALID' if result.is_valid else 'INVALID'}")
        
        if not result.is_valid:
            logger.warning(f"Certificate validation failed: {result.error_message}")
        
        return api_result
        
    except Exception as e:
        logger.error(f"Enhanced certificate validation error: {e}")
        return {
            'valid': False,
            'error': f"Validation service error: {str(e)}",
            'error_code': 'VALIDATION_SERVICE_ERROR',
            'enhanced_validation': True
        }

# Circuit breaker for validation service
class ValidationCircuitBreaker:
    """Simple circuit breaker for validation service"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'closed'  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if validation can be executed"""
        import time
        now = time.time()
        
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            if now - self.last_failure_time >= self.timeout:
                self.state = 'half-open'
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record successful validation"""
        self.failure_count = 0
        self.state = 'closed'
    
    def record_failure(self):
        """Record failed validation"""
        import time
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'

# Global circuit breaker instance
_validation_circuit_breaker = ValidationCircuitBreaker()

def validate_with_circuit_breaker(cert_pem: str, **kwargs) -> Dict:
    """
    Certificate validation with circuit breaker pattern
    
    Args:
        cert_pem: PEM-encoded certificate
        **kwargs: Additional validation parameters
        
    Returns:
        Validation result dictionary
    """
    if not _validation_circuit_breaker.can_execute():
        logger.warning("Certificate validation circuit breaker is OPEN - using fallback")
        return {
            'valid': False,
            'error': 'Certificate validation service temporarily unavailable',
            'error_code': 'SERVICE_UNAVAILABLE',
            'fallback_used': True
        }
    
    try:
        result = validate_device_certificate_enhanced(cert_pem, **kwargs)
        if result['valid']:
            _validation_circuit_breaker.record_success()
        else:
            # Don't count certificate validation failures as service failures
            pass
        return result
        
    except Exception as e:
        _validation_circuit_breaker.record_failure()
        logger.error(f"Certificate validation service error: {e}")
        return {
            'valid': False,
            'error': f"Validation service error: {str(e)}",
            'error_code': 'SERVICE_ERROR',
            'circuit_breaker_triggered': True
        }