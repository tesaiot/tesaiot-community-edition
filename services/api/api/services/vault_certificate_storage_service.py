# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Certificate Storage Service

Security rule: certificates are stored in Vault; MongoDB holds only
metadata and Vault path references.

This service provides:
- Store certificates in Vault KV v2 secrets engine
- Retrieve certificates from Vault
- Store only metadata/references in MongoDB

Database should only store:
- vault_cert_path (reference to Vault)
- certificate fingerprint
- serial number
- validity dates
- status

NEVER store full certificate PEM in MongoDB for Protected Update jobs.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Optional, List
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from hvac.exceptions import VaultError

from ..core.database import get_vault
from .audit_service import audit_log, AuditAction

logger = logging.getLogger(__name__)

# Vault KV v2 mount path for certificates
VAULT_CERT_MOUNT = "secret"
VAULT_CERT_BASE_PATH = "pki-devices/certs"
VAULT_PROTECTED_UPDATE_CERT_PATH = "protected-update/certs"


class VaultCertificateStorageError(Exception):
    """Custom error for Vault certificate operations."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class VaultCertificateStorageService:
    """
    Service for storing device certificates in HashiCorp Vault.

    Security Policy:
    - Full certificate PEM stored in Vault only
    - MongoDB stores only metadata and vault_cert_path reference
    - All certificate access is audit logged
    """

    def _get_vault_client(self):
        """Get fresh Vault client on every call.

        NEVER cache the client — the underlying token has a TTL (typically 4h)
        and will expire.  ``get_vault()`` in ``database.py`` reads the latest
        token from the token-sink file and auto-refreshes when needed.
        Caching here previously caused "permission denied / invalid token"
        errors when the stored client outlived its token.
        """
        return get_vault()

    def _get_cert_path(self, device_id: str, organization_id: str = None) -> str:
        """Generate Vault path for device certificate."""
        if organization_id:
            return f"{VAULT_CERT_BASE_PATH}/{organization_id}/{device_id}"
        return f"{VAULT_CERT_BASE_PATH}/{device_id}"

    def _get_protected_update_cert_path(self, job_id: str) -> str:
        """Generate Vault path for Protected Update job certificate."""
        return f"{VAULT_PROTECTED_UPDATE_CERT_PATH}/{job_id}"

    def store_certificate(
        self,
        device_id: str,
        certificate_pem: str,
        organization_id: str = None,
        ca_chain: List[str] = None,
        serial_number: str = None,
        metadata: Dict = None
    ) -> Dict:
        """
        Store a device certificate in Vault.

        On token-related VaultError the method fetches a fresh client and
        retries once.

        Args:
            device_id: Device identifier
            certificate_pem: Certificate in PEM format
            organization_id: Organization ID (optional)
            ca_chain: CA chain certificates (optional)
            serial_number: Certificate serial number
            metadata: Additional metadata

        Returns:
            Dict with vault_cert_path and certificate fingerprint
        """
        vault_path = self._get_cert_path(device_id, organization_id)

        cert_metadata = self._parse_certificate_metadata(certificate_pem)
        cert_fingerprint = self._calculate_cert_fingerprint(certificate_pem)

        secret_data = {
            "certificate_pem": certificate_pem,
            "ca_chain_pem": ca_chain or [],
            "device_id": device_id,
            "organization_id": organization_id or "",
            "serial_number": serial_number or cert_metadata.get('serial_number'),
            "subject_cn": cert_metadata.get('subject_cn'),
            "issuer_cn": cert_metadata.get('issuer_cn'),
            "valid_from": cert_metadata.get('valid_from'),
            "valid_until": cert_metadata.get('valid_until'),
            "fingerprint": cert_fingerprint,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        last_error: Optional[Exception] = None
        for attempt in range(2):
            try:
                vault_client = self._get_vault_client()
                if not vault_client:
                    raise VaultCertificateStorageError(
                        "Vault client not available",
                        code="VAULT_UNAVAILABLE"
                    )

                vault_client.secrets.kv.v2.create_or_update_secret(
                    path=vault_path,
                    secret=secret_data,
                    mount_point=VAULT_CERT_MOUNT
                )

                logger.info(
                    "Stored certificate in Vault for device: %s%s",
                    device_id,
                    " (after token refresh)" if attempt > 0 else "",
                )

                return {
                    "vault_cert_path": f"{VAULT_CERT_MOUNT}/{vault_path}",
                    "cert_fingerprint": cert_fingerprint,
                    "serial_number": secret_data['serial_number'],
                    "subject_cn": secret_data['subject_cn'],
                    "issuer_cn": secret_data['issuer_cn'],
                    "valid_from": secret_data['valid_from'],
                    "valid_until": secret_data['valid_until'],
                    "stored_at": secret_data['stored_at']
                }

            except VaultError as e:
                last_error = e
                err_lower = str(e).lower()
                if attempt == 0 and ("permission denied" in err_lower or "invalid token" in err_lower or "403" in err_lower):
                    logger.warning(
                        "Vault token error storing cert for device %s, refreshing and retrying: %s",
                        device_id, e,
                    )
                    continue
                logger.error("Vault error storing certificate for device %s: %s", device_id, e)
                raise VaultCertificateStorageError(
                    f"Failed to store certificate in Vault: {str(e)}",
                    code="VAULT_STORE_ERROR"
                )
            except VaultCertificateStorageError:
                raise
            except Exception as e:
                logger.error("Error storing certificate for device %s: %s", device_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate storage failed: {str(e)}",
                    code="STORAGE_ERROR"
                )

        logger.error("Vault token error persists after refresh for device %s: %s", device_id, last_error)
        raise VaultCertificateStorageError(
            f"Failed to store certificate in Vault after token refresh: {str(last_error)}",
            code="VAULT_STORE_ERROR"
        )

    def store_protected_update_certificate(
        self,
        job_id: str,
        certificate_pem: str,
        device_id: str,
        metadata: Dict = None
    ) -> Dict:
        """
        Store a Protected Update job certificate in Vault.

        On token-related VaultError the method fetches a fresh client and
        retries once, so callers never fail due to a single expired token.

        Args:
            job_id: Protected Update job ID
            certificate_pem: Signed certificate in PEM format
            device_id: Device identifier
            metadata: Additional metadata

        Returns:
            Dict with vault_cert_path and certificate metadata
        """
        vault_path = self._get_protected_update_cert_path(job_id)

        # Parse certificate for metadata (token-independent, do once)
        cert_metadata = self._parse_certificate_metadata(certificate_pem)
        cert_fingerprint = self._calculate_cert_fingerprint(certificate_pem)

        secret_data = {
            "certificate_pem": certificate_pem,
            "job_id": job_id,
            "device_id": device_id,
            "serial_number": cert_metadata.get('serial_number'),
            "subject_cn": cert_metadata.get('subject_cn'),
            "issuer_cn": cert_metadata.get('issuer_cn'),
            "valid_from": cert_metadata.get('valid_from'),
            "valid_until": cert_metadata.get('valid_until'),
            "fingerprint": cert_fingerprint,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        last_error: Optional[Exception] = None
        for attempt in range(2):  # try once, retry once on token error
            try:
                vault_client = self._get_vault_client()
                if not vault_client:
                    raise VaultCertificateStorageError(
                        "Vault client not available",
                        code="VAULT_UNAVAILABLE"
                    )

                vault_client.secrets.kv.v2.create_or_update_secret(
                    path=vault_path,
                    secret=secret_data,
                    mount_point=VAULT_CERT_MOUNT
                )

                logger.info(
                    "Stored Protected Update certificate in Vault for job: %s%s",
                    job_id,
                    f" (after token refresh)" if attempt > 0 else "",
                )

                return {
                    "vault_cert_path": f"{VAULT_CERT_MOUNT}/{vault_path}",
                    "cert_fingerprint": cert_fingerprint,
                    "serial_number": secret_data['serial_number'],
                    "subject_cn": secret_data['subject_cn'],
                    "issuer_cn": secret_data['issuer_cn'],
                    "valid_from": secret_data['valid_from'],
                    "valid_until": secret_data['valid_until'],
                    "stored_at": secret_data['stored_at']
                }

            except VaultError as e:
                last_error = e
                err_lower = str(e).lower()
                if attempt == 0 and ("permission denied" in err_lower or "invalid token" in err_lower or "403" in err_lower):
                    logger.warning(
                        "Vault token error storing cert for job %s, refreshing token and retrying: %s",
                        job_id, e,
                    )
                    continue  # retry with fresh client from get_vault()
                logger.error("Vault error storing Protected Update certificate for job %s: %s", job_id, e)
                raise VaultCertificateStorageError(
                    f"Failed to store certificate in Vault: {str(e)}",
                    code="VAULT_STORE_ERROR"
                )
            except VaultCertificateStorageError:
                raise
            except Exception as e:
                logger.error("Error storing Protected Update certificate for job %s: %s", job_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate storage failed: {str(e)}",
                    code="STORAGE_ERROR"
                )

        # Both attempts failed with token error
        logger.error("Vault token error persists after refresh for job %s: %s", job_id, last_error)
        raise VaultCertificateStorageError(
            f"Failed to store certificate in Vault after token refresh: {str(last_error)}",
            code="VAULT_STORE_ERROR"
        )

    def retrieve_certificate(
        self,
        device_id: str,
        organization_id: str = None,
        requester: Dict = None
    ) -> Optional[Dict]:
        """
        Retrieve a device certificate from Vault.

        On token-related VaultError the method fetches a fresh client and
        retries once.

        Args:
            device_id: Device identifier
            organization_id: Organization ID (optional)
            requester: User/system requesting (for audit)

        Returns:
            Dict with certificate_pem and metadata, or None if not found
        """
        vault_path = self._get_cert_path(device_id, organization_id)
        last_error: Optional[Exception] = None

        for attempt in range(2):
            try:
                vault_client = self._get_vault_client()
                if not vault_client:
                    raise VaultCertificateStorageError(
                        "Vault client not available",
                        code="VAULT_UNAVAILABLE"
                    )

                try:
                    response = vault_client.secrets.kv.v2.read_secret_version(
                        path=vault_path,
                        mount_point=VAULT_CERT_MOUNT
                    )
                except Exception as e:
                    if "secret not found" in str(e).lower() or "404" in str(e):
                        return None
                    raise

                if not response or 'data' not in response or 'data' not in response['data']:
                    return None

                secret_data = response['data']['data']

                if requester:
                    audit_log(
                        action=AuditAction.CERTIFICATE_VIEW,
                        user=requester,
                        resource_type='device_certificate',
                        resource_id=device_id,
                        details={
                            'vault_path': vault_path,
                            'organization_id': organization_id
                        }
                    )

                logger.info("Retrieved certificate from Vault for device: %s", device_id)

                return {
                    "certificate_pem": secret_data.get('certificate_pem'),
                    "ca_chain_pem": secret_data.get('ca_chain_pem', []),
                    "device_id": secret_data.get('device_id'),
                    "organization_id": secret_data.get('organization_id'),
                    "serial_number": secret_data.get('serial_number'),
                    "subject_cn": secret_data.get('subject_cn'),
                    "issuer_cn": secret_data.get('issuer_cn'),
                    "valid_from": secret_data.get('valid_from'),
                    "valid_until": secret_data.get('valid_until'),
                    "fingerprint": secret_data.get('fingerprint'),
                    "stored_at": secret_data.get('stored_at'),
                    "metadata": secret_data.get('metadata', {})
                }

            except VaultError as e:
                last_error = e
                err_lower = str(e).lower()
                if attempt == 0 and ("permission denied" in err_lower or "invalid token" in err_lower or "403" in err_lower):
                    logger.warning("Vault token error retrieving cert for device %s, retrying: %s", device_id, e)
                    continue
                logger.error("Vault error retrieving certificate for device %s: %s", device_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate retrieval failed: {str(e)}",
                    code="RETRIEVAL_ERROR"
                )
            except VaultCertificateStorageError:
                raise
            except Exception as e:
                logger.error("Error retrieving certificate for device %s: %s", device_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate retrieval failed: {str(e)}",
                    code="RETRIEVAL_ERROR"
                )

        logger.error("Vault token error persists after refresh for device %s: %s", device_id, last_error)
        raise VaultCertificateStorageError(
            f"Certificate retrieval failed after token refresh: {str(last_error)}",
            code="RETRIEVAL_ERROR"
        )

    def retrieve_protected_update_certificate(
        self,
        job_id: str,
        requester: Dict = None
    ) -> Optional[Dict]:
        """
        Retrieve a Protected Update job certificate from Vault.

        On token-related VaultError the method fetches a fresh client and
        retries once.

        Args:
            job_id: Protected Update job ID
            requester: User/system requesting (for audit)

        Returns:
            Dict with certificate_pem and metadata, or None if not found
        """
        vault_path = self._get_protected_update_cert_path(job_id)
        last_error: Optional[Exception] = None

        for attempt in range(2):
            try:
                vault_client = self._get_vault_client()
                if not vault_client:
                    raise VaultCertificateStorageError(
                        "Vault client not available",
                        code="VAULT_UNAVAILABLE"
                    )

                try:
                    response = vault_client.secrets.kv.v2.read_secret_version(
                        path=vault_path,
                        mount_point=VAULT_CERT_MOUNT
                    )
                except Exception as e:
                    if "secret not found" in str(e).lower() or "404" in str(e):
                        return None
                    raise

                if not response or 'data' not in response or 'data' not in response['data']:
                    return None

                secret_data = response['data']['data']

                logger.info("Retrieved Protected Update certificate from Vault for job: %s", job_id)

                return {
                    "certificate_pem": secret_data.get('certificate_pem'),
                    "job_id": secret_data.get('job_id'),
                    "device_id": secret_data.get('device_id'),
                    "serial_number": secret_data.get('serial_number'),
                    "subject_cn": secret_data.get('subject_cn'),
                    "issuer_cn": secret_data.get('issuer_cn'),
                    "valid_from": secret_data.get('valid_from'),
                    "valid_until": secret_data.get('valid_until'),
                    "fingerprint": secret_data.get('fingerprint'),
                    "stored_at": secret_data.get('stored_at'),
                    "metadata": secret_data.get('metadata', {})
                }

            except VaultError as e:
                last_error = e
                err_lower = str(e).lower()
                if attempt == 0 and ("permission denied" in err_lower or "invalid token" in err_lower or "403" in err_lower):
                    logger.warning("Vault token error retrieving cert for job %s, retrying: %s", job_id, e)
                    continue
                logger.error("Vault error retrieving Protected Update certificate for job %s: %s", job_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate retrieval failed: {str(e)}",
                    code="RETRIEVAL_ERROR"
                )
            except VaultCertificateStorageError:
                raise
            except Exception as e:
                logger.error("Error retrieving Protected Update certificate for job %s: %s", job_id, e)
                raise VaultCertificateStorageError(
                    f"Certificate retrieval failed: {str(e)}",
                    code="RETRIEVAL_ERROR"
                )

        logger.error("Vault token error persists after refresh for job %s: %s", job_id, last_error)
        raise VaultCertificateStorageError(
            f"Certificate retrieval failed after token refresh: {str(last_error)}",
            code="RETRIEVAL_ERROR"
        )

    def _parse_certificate_metadata(self, certificate_pem: str) -> Dict:
        """Parse certificate to extract metadata."""
        try:
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode(),
                default_backend()
            )

            subject_cn = None
            issuer_cn = None

            for attr in cert.subject:
                if attr.oid == x509.oid.NameOID.COMMON_NAME:
                    subject_cn = attr.value
                    break

            for attr in cert.issuer:
                if attr.oid == x509.oid.NameOID.COMMON_NAME:
                    issuer_cn = attr.value
                    break

            return {
                "serial_number": format(cert.serial_number, 'x'),
                "subject_cn": subject_cn,
                "issuer_cn": issuer_cn,
                "valid_from": cert.not_valid_before_utc.isoformat() if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before.isoformat(),
                "valid_until": cert.not_valid_after_utc.isoformat() if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after.isoformat()
            }

        except Exception as e:
            logger.warning(f"Could not parse certificate metadata: {e}")
            return {}

    def _calculate_cert_fingerprint(self, certificate_pem: str) -> str:
        """Calculate SHA256 fingerprint of certificate."""
        try:
            cert = x509.load_pem_x509_certificate(
                certificate_pem.encode(),
                default_backend()
            )
            cert_der = cert.public_bytes(encoding=x509.base.serialization.Encoding.DER)
            return hashlib.sha256(cert_der).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate certificate fingerprint: {e}")
            return hashlib.sha256(certificate_pem.encode()).hexdigest()


# Singleton instance
vault_certificate_storage_service = VaultCertificateStorageService()
