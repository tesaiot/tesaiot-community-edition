# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Integration Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


This module integrates the local certificate generator with the existing certificate service,
providing a unified interface for certificate generation using either Vault PKI or local CA.
"""

import os
import logging
from typing import Dict, Optional, Union
from datetime import datetime, timezone
from bson import ObjectId

from .certificate_service import (
    audit_log,
    AuditAction,
    with_error_handling,
    ErrorSeverity,
    ErrorCategory,
    with_retry
)
from .local_certificate_generator import (
    create_local_certificate_generator
)
from ..core.database import get_db
from ..core.rbac import RBAC, Permission

logger = logging.getLogger(__name__)


class CertificateIntegrationService:
    """
    Unified certificate service that integrates Vault PKI and local certificate generation.
    """
    
    def __init__(self, use_local_ca: bool = False, ca_path: Optional[str] = None):
        """
        Initialize the certificate integration service.
        
        Args:
            use_local_ca: Use local CA instead of Vault PKI
            ca_path: Path to local CA certificates (if use_local_ca is True)
        """
        self.use_local_ca = use_local_ca or os.environ.get('USE_LOCAL_CA', 'false').lower() == 'true'
        self.local_generator = None
        
        if self.use_local_ca:
            try:
                self.local_generator = create_local_certificate_generator(ca_path)
                logger.info("Initialized with local CA certificate generator")
            except Exception as e:
                logger.error(f"Failed to initialize local CA generator: {e}")
                raise
    
    @with_retry(max_retries=3, delay=1.0)
    @with_error_handling(
        severity=ErrorSeverity.HIGH,
        category=ErrorCategory.SECURITY,
        user_message="Unable to generate device certificate. Please try again.",
        return_on_error=None
    )
    def generate_device_certificate(
        self,
        device_id: str,
        organization_id: str,
        user_id: str,
        algorithm: str = "RSA-2048",
        validity_days: int = 365,
        certificate_type: str = "device",
        metadata: Optional[Dict] = None
    ) -> Dict[str, Union[str, bytes]]:
        """
        Generate a device certificate using either Vault PKI or local CA.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            user_id: User ID requesting the certificate
            algorithm: Key algorithm
            validity_days: Certificate validity period
            certificate_type: Type of certificate
            metadata: Additional metadata
            
        Returns:
            Dictionary containing certificate data and metadata
        """
        try:
            # Validate permissions
            if not RBAC.check_permission(user_id, Permission.MANAGE_CERTIFICATES, organization_id):
                audit_log(
                    user_id=user_id,
                    action=AuditAction.CERTIFICATE_GENERATION_DENIED,
                    resource_type="certificate",
                    resource_id=device_id,
                    details={"reason": "Insufficient permissions"}
                )
                raise PermissionError("Insufficient permissions to generate certificates")
            
            # Get organization name from database
            db = get_db()
            org = db.organizations.find_one({"_id": ObjectId(organization_id)})
            organization_name = org.get("name", "TESA IoT Platform") if org else "TESA IoT Platform"
            
            if self.use_local_ca:
                # Generate certificate using local CA
                cert_pem, key_pem, ca_chain = self.local_generator.generate_device_certificate(
                    device_id=device_id,
                    organization=organization_name,
                    algorithm=algorithm,
                    validity_days=validity_days,
                    san_entries=[device_id, f"{device_id}.local"],
                    additional_subject_attrs={
                        'serialNumber': device_id,
                        'email': f"{device_id}@{organization_name.lower().replace(' ', '')}.com"
                    }
                )
                
                # Store certificate metadata in database
                cert_data = {
                    "device_id": device_id,
                    "organization_id": organization_id,
                    "certificate_type": certificate_type,
                    "algorithm": algorithm,
                    "validity_days": validity_days,
                    "issued_at": datetime.now(timezone.utc),
                    "issued_by": "local_ca",
                    "issuer_dn": "CN=TESAIoT Intermediate CA,OU=Certificate Authority,O=TESA IoT Platform,L=Bangkok,ST=Bangkok,C=TH",
                    "status": "active",
                    "created_by": user_id,
                    "metadata": metadata or {}
                }
                
                # Extract certificate info
                cert_info = self.local_generator._get_certificate_info(cert_pem)
                cert_data.update({
                    "serial_number": cert_info["serial_number"],
                    "not_before": cert_info["not_before"],
                    "not_after": cert_info["not_after"],
                    "subject_dn": self._format_dn(cert_info["subject"])
                })
                
                # Store in database
                db.device_certificates.insert_one(cert_data)
                
                # Generate MQTT client config
                mqtt_config = self.local_generator.generate_mqtt_client_config(
                    device_id=device_id,
                    environment=os.environ.get('ENVIRONMENT', 'production')
                )
                
                # Audit log
                audit_log(
                    user_id=user_id,
                    action=AuditAction.CERTIFICATE_GENERATED,
                    resource_type="certificate",
                    resource_id=device_id,
                    details={
                        "algorithm": algorithm,
                        "validity_days": validity_days,
                        "method": "local_ca"
                    }
                )
                
                return {
                    "certificate": cert_pem.decode('utf-8'),
                    "private_key": key_pem.decode('utf-8'),
                    "ca_chain": ca_chain.decode('utf-8'),
                    "mqtt_config": mqtt_config,
                    "metadata": cert_data
                }
                
            else:
                # Use existing Vault PKI implementation
                from .certificate_service import generate_device_certificate_vault
                return generate_device_certificate_vault(
                    device_id=device_id,
                    organization_id=organization_id,
                    user_id=user_id,
                    algorithm=algorithm,
                    validity_days=validity_days,
                    certificate_type=certificate_type,
                    metadata=metadata
                )
                
        except Exception as e:
            logger.error(f"Error generating certificate for device {device_id}: {e}")
            raise
    
    def create_certificate_bundle(
        self,
        device_id: str,
        organization_id: str,
        user_id: str,
        algorithm: str = "RSA-2048",
        validity_days: int = 365,
        bundle_format: str = "zip",
        broker_config: Optional[Dict] = None
    ) -> bytes:
        """
        Create a complete certificate bundle for device deployment.
        
        Args:
            device_id: Device identifier
            organization_id: Organization ID
            user_id: User ID requesting the bundle
            algorithm: Key algorithm
            validity_days: Certificate validity period
            bundle_format: Bundle format (zip/tar)
            broker_config: MQTT broker configuration
            
        Returns:
            Bundle file content as bytes
        """
        try:
            # Check permissions
            if not RBAC.check_permission(user_id, Permission.MANAGE_CERTIFICATES, organization_id):
                raise PermissionError("Insufficient permissions to create certificate bundles")
            
            if self.use_local_ca:
                # Get organization name
                db = get_db()
                org = db.organizations.find_one({"_id": ObjectId(organization_id)})
                organization_name = org.get("name", "TESA IoT Platform") if org else "TESA IoT Platform"
                
                # Create bundle using local generator
                bundle = self.local_generator.create_certificate_bundle(
                    device_id=device_id,
                    organization=organization_name,
                    algorithm=algorithm,
                    validity_days=validity_days,
                    broker_config=broker_config,
                    include_config=True,
                    bundle_format=bundle_format
                )
                
                # Audit log
                audit_log(
                    user_id=user_id,
                    action=AuditAction.CERTIFICATE_BUNDLE_CREATED,
                    resource_type="certificate_bundle",
                    resource_id=device_id,
                    details={
                        "algorithm": algorithm,
                        "validity_days": validity_days,
                        "format": bundle_format,
                        "method": "local_ca"
                    }
                )
                
                return bundle
                
            else:
                # Use Vault-based bundle creation
                raise NotImplementedError("Vault-based bundle creation not yet implemented")
                
        except Exception as e:
            logger.error(f"Error creating certificate bundle for device {device_id}: {e}")
            raise
    
    def verify_certificate(self, certificate_pem: bytes) -> bool:
        """
        Verify a certificate against the appropriate CA chain.
        
        Args:
            certificate_pem: Certificate in PEM format
            
        Returns:
            True if certificate is valid
        """
        try:
            if self.use_local_ca:
                return self.local_generator.verify_certificate_chain(certificate_pem)
            else:
                # Implement Vault-based verification
                raise NotImplementedError("Vault-based certificate verification not yet implemented")
                
        except Exception as e:
            logger.error(f"Error verifying certificate: {e}")
            return False
    
    def _format_dn(self, dn_dict: Dict[str, str]) -> str:
        """Format a DN dictionary into a string."""
        dn_order = ['CN', 'OU', 'O', 'L', 'ST', 'C', 'emailAddress', 'serialNumber']
        dn_parts = []
        
        # Add in order
        for key in dn_order:
            if key in dn_dict:
                dn_parts.append(f"{key}={dn_dict[key]}")
        
        # Add any remaining
        for key, value in dn_dict.items():
            if key not in dn_order:
                dn_parts.append(f"{key}={value}")
        
        return ','.join(dn_parts)
    
    def get_certificate_generation_method(self) -> str:
        """Get the current certificate generation method."""
        return "local_ca" if self.use_local_ca else "vault_pki"
    
    def switch_to_local_ca(self, ca_path: Optional[str] = None) -> None:
        """Switch to using local CA for certificate generation."""
        try:
            self.local_generator = create_local_certificate_generator(ca_path)
            self.use_local_ca = True
            logger.info("Switched to local CA certificate generation")
        except Exception as e:
            logger.error(f"Failed to switch to local CA: {e}")
            raise
    
    def switch_to_vault_pki(self) -> None:
        """Switch to using Vault PKI for certificate generation."""
        self.use_local_ca = False
        self.local_generator = None
        logger.info("Switched to Vault PKI certificate generation")


# Global instance
_certificate_integration_service = None


def get_certificate_integration_service() -> CertificateIntegrationService:
    """Get or create the global certificate integration service instance."""
    global _certificate_integration_service
    
    if _certificate_integration_service is None:
        _certificate_integration_service = CertificateIntegrationService()
    
    return _certificate_integration_service


# Convenience functions for direct access
def generate_device_certificate(
    device_id: str,
    organization_id: str,
    user_id: str,
    **kwargs
) -> Dict[str, Union[str, bytes]]:
    """Generate a device certificate using the integrated service."""
    service = get_certificate_integration_service()
    return service.generate_device_certificate(
        device_id=device_id,
        organization_id=organization_id,
        user_id=user_id,
        **kwargs
    )


def create_certificate_bundle(
    device_id: str,
    organization_id: str,
    user_id: str,
    **kwargs
) -> bytes:
    """Create a certificate bundle using the integrated service."""
    service = get_certificate_integration_service()
    return service.create_certificate_bundle(
        device_id=device_id,
        organization_id=organization_id,
        user_id=user_id,
        **kwargs
    )


def verify_certificate(certificate_pem: bytes) -> bool:
    """Verify a certificate using the integrated service."""
    service = get_certificate_integration_service()
    return service.verify_certificate(certificate_pem)


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example: Switch to local CA mode
    service = get_certificate_integration_service()
    service.switch_to_local_ca()
    
    print(f"Certificate generation method: {service.get_certificate_generation_method()}")