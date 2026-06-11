# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Certificate Service Implementation for TESA IoT Platform
======================================================
Version: v2025.08
Module: Security/Certificate Service
Purpose: Modular implementation of certificate management

This module implements the ICertificateService interface as part
of the safe modularization effort. It provides certificate lifecycle
management while maintaining compatibility with the existing system.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import asyncio

from ..interfaces import (
    ICertificateService,
    Certificate,
    CertificateRequest,
    CertificateRevocation,
    CertificateGenerationError,
    CertificateNotFoundError,
    CertificateRenewalError
)
from ....core.di_container import Injectable
from ....core.database import db_manager, get_vault_client
from ....services.parallel_runner import parallel_run
from ....services.feature_flags import feature_flag

logger = logging.getLogger(__name__)


class ModularCertificateService(ICertificateService, Injectable):
    """
    Modular implementation of certificate service.
    
    This service is designed to gradually replace the existing
    certificate_service.py functionality using the parallel runner
    and feature flag systems for safe rollout.
    """
    
    def __init__(self):
        super().__init__()
        self.mongo_db = None
        self.vault_client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of database connections."""
        if not self._initialized:
            self.mongo_db = db_manager.mongo_db
            # Use get_vault_client() for lazy initialization and re-authentication
            self.vault_client = get_vault_client()
            self._initialized = True
            self.logger.info("ModularCertificateService initialized")
    
    @parallel_run("security.certificates")
    @feature_flag("modular_certificates")
    async def generate_certificate(
        self, 
        request: CertificateRequest
    ) -> Certificate:
        """
        Generate a new certificate for a device.
        
        This method runs in parallel with the legacy implementation
        and is controlled by the modular_certificates feature flag.
        """
        await self._ensure_initialized()
        
        try:
            # Log the request for monitoring
            self.logger.info(f"Generating certificate for device {request.device_id}")
            
            # Validate request
            if not request.device_id or not request.organization_id:
                raise CertificateGenerationError("Device ID and Organization ID are required")
            
            # Check if device already has a certificate
            existing = await self.get_certificate(request.device_id)
            if existing and existing.status == "active":
                raise CertificateGenerationError(f"Device {request.device_id} already has an active certificate")
            
            # Generate certificate using Vault
            cert_data = await self._generate_with_vault(request)
            
            # Create Certificate object
            certificate = Certificate(
                device_id=request.device_id,
                certificate_pem=cert_data['certificate'],
                private_key_pem=cert_data.get('private_key'),
                chain_pem=cert_data.get('ca_chain'),
                fingerprint=cert_data['fingerprint'],
                serial_number=cert_data['serial_number'],
                subject=cert_data['subject'],
                issuer=cert_data['issuer'],
                not_before=datetime.utcnow(),
                not_after=datetime.utcnow() + timedelta(days=request.validity_days),
                status="active",
                algorithm=cert_data.get('algorithm', 'RSA-2048'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Store in database
            await self._store_certificate(certificate)
            
            self.logger.info(f"Certificate generated successfully for device {request.device_id}")
            return certificate
            
        except Exception as e:
            self.logger.error(f"Certificate generation failed: {str(e)}")
            raise CertificateGenerationError(f"Failed to generate certificate: {str(e)}")
    
    async def get_certificate(
        self, 
        device_id: str
    ) -> Optional[Certificate]:
        """Get certificate for a specific device."""
        await self._ensure_initialized()
        
        try:
            # Query from MongoDB
            cert_doc = await self.mongo_db.certificates.find_one({
                "device_id": device_id,
                "status": {"$ne": "revoked"}
            })
            
            if not cert_doc:
                return None
            
            # Convert to Certificate object
            return self._document_to_certificate(cert_doc)
            
        except Exception as e:
            self.logger.error(f"Error retrieving certificate: {str(e)}")
            return None
    
    async def revoke_certificate(
        self, 
        device_id: str, 
        reason: str, 
        user_id: str
    ) -> CertificateRevocation:
        """Revoke a device certificate."""
        await self._ensure_initialized()
        
        # Get existing certificate
        certificate = await self.get_certificate(device_id)
        if not certificate:
            raise CertificateNotFoundError(f"No certificate found for device {device_id}")
        
        try:
            # Revoke in Vault
            await self._revoke_in_vault(certificate.serial_number)
            
            # Update database
            await self.mongo_db.certificates.update_one(
                {"device_id": device_id},
                {
                    "$set": {
                        "status": "revoked",
                        "revoked_at": datetime.utcnow(),
                        "revoked_by": user_id,
                        "revocation_reason": reason,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Create revocation record
            revocation = CertificateRevocation(
                certificate_id=certificate.serial_number,
                reason=reason,
                revoked_at=datetime.utcnow(),
                revoked_by=user_id
            )
            
            self.logger.info(f"Certificate revoked for device {device_id}")
            return revocation
            
        except Exception as e:
            self.logger.error(f"Certificate revocation failed: {str(e)}")
            raise
    
    async def renew_certificate(
        self, 
        device_id: str, 
        validity_days: int = 365
    ) -> Certificate:
        """Renew an existing certificate."""
        await self._ensure_initialized()
        
        # Get existing certificate
        existing = await self.get_certificate(device_id)
        if not existing:
            raise CertificateNotFoundError(f"No certificate found for device {device_id}")
        
        try:
            # Revoke old certificate
            await self.revoke_certificate(device_id, "Renewal", "system")
            
            # Generate new certificate with same parameters
            request = CertificateRequest(
                device_id=device_id,
                device_name=existing.subject.split("CN=")[1].split(",")[0],
                organization_id=existing.subject.split("O=")[1].split(",")[0],
                common_name=existing.subject.split("CN=")[1].split(",")[0],
                validity_days=validity_days
            )
            
            # Generate new certificate
            new_cert = await self.generate_certificate(request)
            
            self.logger.info(f"Certificate renewed for device {device_id}")
            return new_cert
            
        except Exception as e:
            self.logger.error(f"Certificate renewal failed: {str(e)}")
            raise CertificateRenewalError(f"Failed to renew certificate: {str(e)}")
    
    async def validate_certificate(
        self, 
        certificate_pem: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate a certificate."""
        await self._ensure_initialized()
        
        try:
            # Use Vault to validate
            result = await self._validate_with_vault(certificate_pem)
            return result
            
        except Exception as e:
            self.logger.error(f"Certificate validation error: {str(e)}")
            return False, str(e)
    
    async def list_certificates(
        self, 
        organization_id: str, 
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Certificate], int]:
        """List certificates for an organization."""
        await self._ensure_initialized()
        
        try:
            # Build query
            query = {"organization_id": organization_id}
            if status:
                query["status"] = status
            
            # Get total count
            total_count = await self.mongo_db.certificates.count_documents(query)
            
            # Get certificates with pagination
            cursor = self.mongo_db.certificates.find(query).skip(skip).limit(limit)
            cert_docs = await cursor.to_list(length=limit)
            
            # Convert to Certificate objects
            certificates = [self._document_to_certificate(doc) for doc in cert_docs]
            
            return certificates, total_count
            
        except Exception as e:
            self.logger.error(f"Error listing certificates: {str(e)}")
            return [], 0
    
    async def get_certificate_chain(
        self, 
        device_id: str
    ) -> Optional[str]:
        """Get the full certificate chain for a device."""
        await self._ensure_initialized()
        
        certificate = await self.get_certificate(device_id)
        if not certificate:
            return None
        
        return certificate.chain_pem
    
    async def bulk_revoke_certificates(
        self, 
        device_ids: List[str], 
        reason: str, 
        user_id: str
    ) -> List[CertificateRevocation]:
        """Bulk revoke multiple certificates."""
        await self._ensure_initialized()
        
        revocations = []
        errors = []
        
        # Process in parallel with limited concurrency
        semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent revocations
        
        async def revoke_with_semaphore(device_id):
            async with semaphore:
                try:
                    revocation = await self.revoke_certificate(device_id, reason, user_id)
                    return revocation, None
                except Exception as e:
                    return None, (device_id, str(e))
        
        # Run revocations in parallel
        tasks = [revoke_with_semaphore(device_id) for device_id in device_ids]
        results = await asyncio.gather(*tasks)
        
        # Process results
        for revocation, error in results:
            if revocation:
                revocations.append(revocation)
            if error:
                errors.append(error)
        
        # Log errors
        if errors:
            self.logger.error(f"Bulk revocation errors: {errors}")
        
        self.logger.info(f"Bulk revoked {len(revocations)} certificates")
        return revocations
    
    # Private helper methods
    
    async def _generate_with_vault(self, request: CertificateRequest) -> Dict[str, Any]:
        """Generate certificate using Vault."""
        # This is a placeholder - actual implementation would call Vault
        # For now, return mock data for parallel testing
        return {
            'certificate': f"-----BEGIN CERTIFICATE-----\nMOCK_CERT_FOR_{request.device_id}\n-----END CERTIFICATE-----",
            'private_key': f"-----BEGIN PRIVATE KEY-----\nMOCK_KEY_FOR_{request.device_id}\n-----END PRIVATE KEY-----",
            'ca_chain': "-----BEGIN CERTIFICATE-----\nMOCK_CA_CHAIN\n-----END CERTIFICATE-----",
            'fingerprint': f"mock:fingerprint:{request.device_id}",
            'serial_number': f"mock:serial:{request.device_id}",
            'subject': f"CN={request.common_name},O={request.organization}",
            'issuer': "CN=TESA IoT CA,O=TESA",
            'algorithm': 'RSA-2048'
        }
    
    async def _store_certificate(self, certificate: Certificate):
        """Store certificate in database."""
        cert_doc = {
            'device_id': certificate.device_id,
            'certificate_pem': certificate.certificate_pem,
            'private_key_pem': certificate.private_key_pem,
            'chain_pem': certificate.chain_pem,
            'fingerprint': certificate.fingerprint,
            'serial_number': certificate.serial_number,
            'subject': certificate.subject,
            'issuer': certificate.issuer,
            'not_before': certificate.not_before,
            'not_after': certificate.not_after,
            'status': certificate.status,
            'algorithm': certificate.algorithm,
            'created_at': certificate.created_at,
            'updated_at': certificate.updated_at,
            'organization_id': certificate.subject.split("O=")[1].split(",")[0]
        }
        
        await self.mongo_db.certificates.insert_one(cert_doc)
    
    async def _revoke_in_vault(self, serial_number: str):
        """Revoke certificate in Vault."""
        # Placeholder for Vault revocation
        self.logger.info(f"Revoking certificate {serial_number} in Vault")
    
    async def _validate_with_vault(self, certificate_pem: str) -> Tuple[bool, Optional[str]]:
        """Validate certificate with Vault."""
        # Placeholder for Vault validation
        return True, None
    
    def _document_to_certificate(self, doc: Dict[str, Any]) -> Certificate:
        """Convert MongoDB document to Certificate object."""
        return Certificate(
            device_id=doc['device_id'],
            certificate_pem=doc['certificate_pem'],
            private_key_pem=doc.get('private_key_pem'),
            chain_pem=doc.get('chain_pem'),
            fingerprint=doc['fingerprint'],
            serial_number=doc['serial_number'],
            subject=doc['subject'],
            issuer=doc['issuer'],
            not_before=doc['not_before'],
            not_after=doc['not_after'],
            status=doc['status'],
            algorithm=doc.get('algorithm', 'RSA-2048'),
            created_at=doc['created_at'],
            updated_at=doc['updated_at']
        )