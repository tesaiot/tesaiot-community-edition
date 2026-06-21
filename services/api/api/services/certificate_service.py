# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import logging
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from dateutil import parser
from bson import ObjectId
from pymongo.errors import (
    PyMongoError, ConnectionFailure, WriteError
)
from hvac.exceptions import VaultError, InvalidRequest, Forbidden
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend

from ..core.database import get_db, get_vault
from ..core.rbac import RBAC
from .audit_service import audit_log, audit_security_violation, AuditAction
from .notification_service import (
    send_email_notification,
    send_webhook_notification,
    send_certificate_expiry_notification
)
from .notification_acl_service import notification_acl_service
from .auto_device_registration_service import auto_device_registration_service
from .key_encryption_service import encrypt_private_key_for_device, get_encryption_tier_for_device
# Local certificate generator will be imported conditionally if needed
import sys
sys.path.append('/app/audit')

from api.tolerance_methods.exception_handling import (
    with_error_handling, ErrorSeverity, ErrorCategory
)
from api.tolerance_methods.retry import (
    with_retry, RetryPolicy, CircuitBreaker, with_timeout
)
from api.tolerance_methods.validation import (
    validate_device_id, sanitize_string, ValidationError
)

logger = logging.getLogger(__name__)

# Import cryptography modules for CSR handling
from cryptography.hazmat.primitives import serialization

# Circuit breakers for different service types
database_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
vault_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120)
external_api_circuit_breaker = CircuitBreaker(failure_threshold=4, timeout=180)

def _public_key_algorithm_name(public_key):
    """Return a readable algorithm name for a certificate public key."""
    try:
        if isinstance(public_key, rsa.RSAPublicKey):
            return f"RSA-{public_key.key_size}"
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            return f"EC-{public_key.curve.name}"
    except Exception:  # pragma: no cover
        pass
    return public_key.__class__.__name__


def _fetch_trust_anchor_pem(anchor_path: str) -> Optional[str]:
    """Retrieve a trust anchor certificate PEM from Vault KV."""
    try:
        vault = get_vault()
        if not vault:
            logger.warning("Vault unavailable while fetching trust anchor %s", anchor_path)
            return None

        secret = vault.secrets.kv.v2.read_secret_version(path=anchor_path)
        data = (secret or {}).get('data', {}).get('data', {})
        for key in ('pem', 'certificate', 'ca', 'ca_pem', 'bundle'):
            value = data.get(key)
            if value:
                return value.strip()
    except Exception as exc:  # pragma: no cover - trust anchor retrieval should not fail hard
        logger.warning(f"Failed to fetch trust anchor at {anchor_path}: {exc}")

    # Fallback to on-disk template copies when Vault entry is unavailable.
    fallback_candidates = []
    env_fallback = os.getenv('TRUSTM_FACTORY_CA_FALLBACK')
    if env_fallback:
        fallback_candidates.append(env_fallback)

    # Prefer repository-relative path during unit tests / local runs
    fallback_candidates.append(
        os.path.join(os.getcwd(), 'scripts', 'templates', 'trust-anchors', 'infineon-optiga-trust-m-ca.pem')
    )
    # Runtime path inside the container image
    fallback_candidates.append('/app/scripts/templates/trust-anchors/infineon-optiga-trust-m-ca.pem')

    for candidate in fallback_candidates:
        if not candidate:
            continue
        try:
            if os.path.exists(candidate):
                with open(candidate, 'r', encoding='utf-8') as fh:
                    content = fh.read().strip()
                    if content and 'BEGIN CERTIFICATE' in content:
                        logger.debug("Loaded Trust M anchor from fallback path %s", candidate)
                        return content
        except Exception as fallback_error:  # pragma: no cover - log and continue
            logger.debug("Failed reading fallback trust anchor %s: %s", candidate, fallback_error)
    return None


def get_ca_chain_metadata():
    """Return metadata for the platform CA chain (intermediate + root)."""
    now = datetime.now(timezone.utc)
    chain_entries = []

    def add_cert(pem: str, label: str, source: str):
        if not pem:
            return
        try:
            cert = x509.load_pem_x509_certificate(pem.encode('utf-8'), default_backend())
            not_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
            not_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
            chain_entries.append({
                'label': label,
                'source': source,
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': format(cert.serial_number, 'X'),
                'signature_algorithm': getattr(cert.signature_hash_algorithm, 'name', 'unknown'),
                'public_key_algorithm': _public_key_algorithm_name(cert.public_key()),
                'not_before': not_before.isoformat(),
                'not_after': not_after.isoformat(),
                'days_remaining': (not_after - now).days,
            })
        except Exception as exc:  # pragma: no cover - log for observability
            logger.warning(f"Failed to parse {label} certificate for CA metadata: {exc}")

    use_local_ca = os.getenv('USE_LOCAL_CA', 'false').lower() == 'true'
    if use_local_ca:
        try:
            from .local_certificate_generator import create_local_certificate_generator

            generator = create_local_certificate_generator()
            if getattr(generator, 'intermediate_cert', None):
                add_cert(
                    generator.intermediate_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8'),
                    'Intermediate CA',
                    'local_ca'
                )
            if getattr(generator, 'ca_cert', None):
                add_cert(
                    generator.ca_cert.public_bytes(serialization.Encoding.PEM).decode('utf-8'),
                    'Root CA',
                    'local_ca'
                )
        except Exception as exc:
            logger.warning(f"Failed to load CA metadata from local generator: {exc}")

    if not chain_entries:
        vault = get_vault()
        if vault:
            try:
                intermediate = vault.read('pki-int/cert/ca') or {}
                intermediate_cert = intermediate.get('data', {}).get('certificate')
                if intermediate_cert:
                    add_cert(intermediate_cert, 'Intermediate CA', 'vault')

                root = vault.read('pki-root/cert/ca') or {}
                root_cert = root.get('data', {}).get('certificate')
                if root_cert:
                    add_cert(root_cert, 'Root CA', 'vault')
            except Exception as exc:
                logger.warning(f"Failed to load CA metadata from Vault: {exc}")

    if not chain_entries:
        fallback_paths = [
            '/opt/emqx/etc/certs/chain/ca-chain.crt',
            '/app/certs/chain/ca-chain.crt',
            '/usr/local/tesa/certs/ca-chain.crt',
            './config/certificates/certs/emqx/chain/ca-chain.crt',
            './certs/ca-chain.crt',
        ]
        for path in fallback_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        pem_blob = f.read()
                    blocks = [
                        f"{chunk.strip()}\n-----END CERTIFICATE-----\n"
                        for chunk in pem_blob.split('-----END CERTIFICATE-----')
                        if chunk.strip()
                    ]
                    for idx, pem in enumerate(blocks):
                        label = 'Intermediate CA' if idx == 0 else 'Root CA'
                        add_cert(pem, label, 'filesystem')
                    break
            except Exception as exc:
                logger.warning(f"Failed to read CA chain from {path}: {exc}")

    return {
        'generated_at': now.isoformat(),
        'entries': chain_entries,
    }

# -----------------------------
# Helper: Generate mqtt_client_config.h content for bundles
# -----------------------------
def _build_mqtt_client_config_header(device_id: str,
                                     username: str,
                                     auth_mode: str,
                                     ca_pem: str,
                                     cert_pem: Optional[str],
                                     key_pem: Optional[str],
                                     algorithm_label: str = 'ECC P-256') -> str:
    """Create a PSoC-style mqtt_client_config.h populated for this device.

    If key_pem is None (CSR devices), the CLIENT_PRIVATE_KEY section is omitted
    and a CSR notice is included.
    """
    broker_host = os.getenv('TESA_MQTT_DOMAIN', 'localhost')
    port = 8883
    pub = f"device/{device_id}/telemetry"
    sub = f"device/{device_id}/commands"
    pub_sensor = f"device/{device_id}/telemetry/sensor"

    # Build PEM macro blocks (trim to avoid trailing whitespace issues)
    def pem_to_define(name: str, pem_text: Optional[str]) -> str:
        if not pem_text:
            return ''
        # Ensure string escaped newlines and quotes
        lines = [l for l in pem_text.strip().split('\n') if l]
        joined = "\n\" \\\n".join([f"{line}" for line in lines])
        return (
            f"#define {name} \\\n\"" + joined + "\\n\"\n"
        )

    root_ca_define = pem_to_define('ROOT_CA_CERTIFICATE', ca_pem)
    client_cert_define = pem_to_define('CLIENT_CERTIFICATE', cert_pem)
    client_key_define = pem_to_define('CLIENT_PRIVATE_KEY', key_pem) if key_pem else ''

    csr_notice = '' if key_pem else (
        '\n/* CSR Certificate: Private key was not generated by the platform.\\n'
        ' * Keep your device private key secure and embed it manually if needed. */\n'
    )

    header = f"""/******************************************************************************
* TESA IoT Platform Configuration - MUTUAL TLS (mTLS)
* Device ID: {device_id}
* Generated: {datetime.utcnow().isoformat()}Z
*
* Algorithm: {algorithm_label}
******************************************************************************/

#ifndef MQTT_CLIENT_CONFIG_H_
#define MQTT_CLIENT_CONFIG_H_

#include "cy_mqtt_api.h"

/* MQTT connection */
#define MQTT_BROKER_ADDRESS               "{broker_host}"
#define MQTT_PORT                         {port}
#define MQTT_SECURE_CONNECTION            ( 1 )

/* Credentials */
#define MQTT_USERNAME                     "{username}"
#define MQTT_PASSWORD                     ""  /* Empty for mTLS */

/* Topics */
#define MQTT_PUB_TOPIC                    "{pub}"
#define MQTT_SUB_TOPIC                    "{sub}"
#define MQTT_PUB_TOPIC_SENSOR             "{pub_sensor}"

/* Client ID */
#define MQTT_CLIENT_IDENTIFIER            "{device_id}"

/* CA / Certificate / Key */
{root_ca_define}
{client_cert_define}
{client_key_define}
{csr_notice}

#endif /* MQTT_CLIENT_CONFIG_H_ */
"""
    return header

def _mqtt_broker_endpoint(auth_mode: str = '') -> tuple:
    """Resolve the device-facing MQTT broker (host, port) from deployment env.

    Domain-agnostic: derived from TESA_PUBLIC_MQTT_HOST / TESA_MQTT_DOMAIN and
    the published TLS/mTLS ports, defaulting to localhost so a fresh install
    still produces a valid header. Never hardcode the production domain here.
    """
    host = (os.getenv('TESA_PUBLIC_MQTT_HOST')
            or os.getenv('TESA_MQTT_DOMAIN')
            or os.getenv('DOMAIN')
            or 'localhost')
    mode = (auth_mode or '').lower()
    if mode in ('server_tls', 'server-tls', 'servertls'):
        port = os.getenv('TESA_PUBLIC_MQTT_TLS_PORT', '8884')
    else:
        port = os.getenv('TESA_PUBLIC_MQTT_MTLS_PORT', '8883')
    return host, port


def _ingest_base_url() -> str:
    """Resolve the HTTPS telemetry-ingest base URL from deployment env."""
    return (os.getenv('TESA_PUBLIC_INGEST_BASE_URL')
            or os.getenv('TESA_PUBLIC_API_BASE_URL')
            or 'https://localhost:9444')


# Full template-based generator matching tutorial header layout
def _build_mqtt_client_config_header_full(device_id: str,
                                          username: str,
                                          auth_mode: str,
                                          ca_pem: str,
                                          cert_pem: Optional[str],
                                          key_pem: Optional[str],
                                          algorithm_label: str = 'ECC P-256') -> str:
    """Render mqtt_client_config.h using canonical templates in /app/scripts/templates.
    Falls back to a minimal header if templates are unavailable.
    """
    template_filename = 'mqtt_client_config_mtls.h.template'
    mode = (auth_mode or '').lower()
    if mode in ('server_tls', 'server-tls', 'servertls'):
        template_filename = 'mqtt_client_config_server_tls.h.template'
    template_path = f"/app/scripts/templates/{template_filename}"

    def format_cert_for_c(pem_text: Optional[str]) -> str:
        if not pem_text:
            return ''
        lines = pem_text.strip().splitlines()
        escaped = []
        for line in lines:
            esc = line.replace('"', '\\"')
            escaped.append(f'"{esc}\\n"')
        return ' \\\n'.join(escaped)

    # Clean CA PEM content if it includes comments before the first cert block
    ca_clean = ca_pem
    try:
        if ca_pem and '-----BEGIN CERTIFICATE-----' in ca_pem:
            idx = ca_pem.find('-----BEGIN CERTIFICATE-----')
            if idx >= 0:
                ca_clean = ca_pem[idx:]
    except Exception:
        pass

    ca_block = format_cert_for_c(ca_clean)
    cert_block = format_cert_for_c(cert_pem) if cert_pem else ''
    key_block = format_cert_for_c(key_pem) if key_pem else ''

    try:
        with open(template_path, 'r') as f:
            template = f.read()
        out = template
        generation_ts = datetime.now(timezone.utc).isoformat()
        broker_host, broker_port = _mqtt_broker_endpoint(auth_mode)
        out = out.replace('{{DEVICE_ID}}', device_id)
        out = out.replace('{{MQTT_USERNAME}}', username)
        out = out.replace('{{GENERATION_DATE}}', generation_ts)
        out = out.replace('{{ALGORITHM_LABEL}}', algorithm_label)
        out = out.replace('{{MQTT_BROKER_HOST}}', broker_host)
        out = out.replace('{{MQTT_BROKER_PORT}}', str(broker_port))
        out = out.replace('{{CA_CERTIFICATE}}', ca_block)
        out = out.replace('{{CLIENT_CERTIFICATE}}', cert_block)
        out = out.replace('{{CLIENT_PRIVATE_KEY}}', key_block)
        return out
    except Exception:
        # Minimal fallback
        return (
            f"/* Minimal header fallback */\n#define MQTT_USERNAME \"{username}\"\n#define MQTT_CLIENT_IDENTIFIER \"{device_id}\"\n"
            f"#define ROOT_CA_CERTIFICATE \\n{ca_block}\n"
            f"#define CLIENT_CERTIFICATE \\n{cert_block}\n" +
            (f"#define CLIENT_PRIVATE_KEY \\n{key_block}\n" if key_block else '')
        )

# -----------------------------
# Helper: Normalize modular results to legacy shape and optionally persist
# -----------------------------
def _normalize_cert_info_response(device_id: str, modular_result: dict) -> Optional[dict]:
    """Normalize modular certificate info result to legacy response shape.

    Returns dict with keys: exists, certificate{...}, download_urls{...}
    """
    try:
        if not modular_result:
            return None
        # modular info shape example:
        # { exists: True, serial_number, not_before, not_after, algorithm, ... }
        if modular_result.get('exists') is True:
            issued_at = modular_result.get('not_before') or modular_result.get('issued_at')
            expires_at = modular_result.get('not_after') or modular_result.get('expires_at')
            serial = (modular_result.get('serial_number') or
                      modular_result.get('certificate_id') or
                      modular_result.get('fingerprint'))
            key_algo = modular_result.get('algorithm') or modular_result.get('key_algorithm')

            cert_info = {
                'serial_number': serial,
                'serialNumber': serial,
                'serial': serial,
                'status': modular_result.get('status', 'valid'),
                'key_algorithm': key_algo,
                'algorithm': key_algo,
                'device_type': modular_result.get('device_type', 'sensor'),
                'issued_at': issued_at,
                'expires_at': expires_at,
                'validFrom': issued_at,
                'validTo': expires_at,
                'issuer': modular_result.get('issuer'),
                'subject': modular_result.get('subject')
            }

            device_real_id = device_id
            return {
                'exists': True,
                'certificate': cert_info,
                'download_urls': {
                    'ca_chain': f'/api/v1/devices/{device_real_id}/certificate/download/ca-chain',
                    'device_cert': f'/api/v1/devices/{device_real_id}/certificate/download/device-cert',
                    'device_key': f'/api/v1/devices/{device_real_id}/certificate/download/device-key',
                    'bundle': f'/api/v1/devices/{device_real_id}/certificate/download/bundle'
                }
            }
        return None
    except Exception:
        return None


def _persist_modular_issuance(device_id: str, user: dict, modular_result: dict) -> Optional[dict]:
    """Persist modular issuance outputs to DB and return legacy-shaped response.

    modular_result example keys: success, certificate, private_key, ca_chain,
    serial_number, not_before, not_after, algorithm, issuer, subject
    """
    try:
        if not modular_result or not modular_result.get('success'):
            return None

        db = get_db()
        if db is None:
            return None

        # Locate device
        device = None
        if ObjectId.is_valid(device_id) and len(device_id) == 24:
            device = db.devices.find_one({'_id': ObjectId(device_id)})
        if not device:
            device = db.devices.find_one({'device_id': device_id})
        if not device:
            return None

        device_real_id = device.get('device_id', str(device.get('_id')))

        issued_at = modular_result.get('not_before') or datetime.now().isoformat()
        expires_at = modular_result.get('not_after') or (datetime.now() + timedelta(days=365)).isoformat()
        serial = modular_result.get('serial_number') or modular_result.get('certificate_id')
        key_algo = modular_result.get('algorithm')

        _prov, _issued_by = _detect_provisioning_method(device)
        cert_info = {
            'serial_number': serial,
            'serialNumber': serial,
            'serial': serial,
            'status': modular_result.get('status', 'valid'),
            'key_algorithm': _normalize_algorithm(key_algo),
            'algorithm': _normalize_algorithm(key_algo),
            'device_type': device.get('type', 'sensor'),
            'issued_at': issued_at,
            'expires_at': expires_at,
            'validFrom': issued_at,
            'validTo': expires_at,
            'issuer': modular_result.get('issuer'),
            'subject': modular_result.get('subject'),
            'issued_via': _prov,
            'validity_days': 365,
        }

        # Determine certificate status (respect server_tls)
        cert_status = 'ca_only' if device.get('auth_mode') == 'server_tls' else 'valid'

        update_data = {
            'certificate_status': cert_status,
            'certificate_info': cert_info,
            'certificate_issued_at': issued_at,
            'certificate_expires_at': expires_at,
            'certificate_serial': serial,
            'certificate_algorithm': _normalize_algorithm(key_algo),
            'certificate': modular_result.get('certificate', ''),
            'certificate_chain': modular_result.get('ca_chain', []),
            'private_key': modular_result.get('private_key', ''),
        }

        try:
            db.devices.update_one({'_id': device['_id']}, {'$set': update_data})
        except Exception:
            # Do not fail issuance on persistence problems
            pass

        # Build legacy-shaped response
        return {
            'message': 'Certificate issued successfully',
            'certificate': cert_info,
            'download_urls': {
                'ca_chain': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/ca-chain",
                'device_cert': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/device-cert",
                'device_key': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/device-key",
                'bundle': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/bundle"
            }
        }
    except Exception:
        return None

# [MODULARIZE:START] - CertificateInfoService# Description: Certificate information retrieval and validation
# Dependencies: pymongo, hvac, cryptography
# Estimated Size: 150 lines
# Priority: HIGH
@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.DATABASE,
    user_message="Unable to retrieve certificate information. Please try again.",
    return_on_error={'exists': False, 'message': 'Service temporarily unavailable'}
)
def get_device_certificate_info(device_id, user=None):
    """
    Get device certificate information with organization validation and error handling.
    
    Args:
        device_id: Device identifier
        user: Current user for ACL check
        
    Returns:
        dict: Certificate info or None if not found
    """
    # Check if modular implementation should be used
    from .certificate_modular_bridge import get_certificate_info_with_parallel
    modular_result = get_certificate_info_with_parallel(device_id, user)
    if modular_result is not None:
        # Normalize modular response to legacy shape
        normalized = _normalize_cert_info_response(device_id, modular_result)
        if normalized is not None:
            return normalized
    
    # Validate device_id input
    if not validate_device_id(device_id):
        raise ValidationError("Invalid device ID format")
    
    db = get_db()
    if db is None:
        raise ConnectionFailure("Database connection not available")
    
    # SECURITY: Build query with organization filter
    device_query = {}
    if ObjectId.is_valid(device_id) and len(device_id) == 24:
        device_query['_id'] = ObjectId(device_id)
    else:
        device_query['device_id'] = device_id
            
    # Apply organization filter for non-platform admin users
    if user and not RBAC.is_platform_admin(user):
        device_query['organization_id'] = user.get('organization_id', '')
            
    device = db.devices.find_one(device_query)
            
    if not device:
        if user:
            logger.warning(f"Access denied: {user.get('email')} tried to access cert info for device {device_id}")
        return None
            
    # Check if certificate exists in normalized location
    if device.get('certificate_info'):
        cert_info = device['certificate_info']
        device_real_id = device.get('device_id', str(device['_id']))
        
        return {
            'exists': True,
            'certificate': cert_info,
            'download_urls': {
                'ca_chain': f'/api/v1/devices/{device_real_id}/certificate/download/ca-chain',
                'device_cert': f'/api/v1/devices/{device_real_id}/certificate/download/device-cert',
                'device_key': f'/api/v1/devices/{device_real_id}/certificate/download/device-key',
                'bundle': f'/api/v1/devices/{device_real_id}/certificate/download/bundle'
            }
        }
    
    # Fallback: some paths store fields directly on device document
    legacy_serial = device.get('certificate_serial')
    legacy_issued = device.get('certificate_issued_at')
    legacy_expires = device.get('certificate_expires_at')
    legacy_pem = device.get('certificate')
    
    if legacy_serial or legacy_issued or legacy_expires or legacy_pem:
        device_real_id = device.get('device_id', str(device['_id']))
        # Map algorithm from stored value if available
        stored_alg = device.get('certificate_algorithm')
        alg_map = {
            'ecc-p256': 'ECC P-256',
            'ecc-p384': 'ECC P-384',
            'rsa-3072': 'RSA 3072',
            'rsa-4096': 'RSA 4096',
            'ECC P-256': 'ECC P-256',
            'ECC P-384': 'ECC P-384',
            'RSA 3072': 'RSA 3072',
            'RSA 4096': 'RSA 4096'
        }
        key_algorithm = alg_map.get(stored_alg, stored_alg or None)

        # If we still don't know, attempt to derive from certificate PEM
        if not key_algorithm and legacy_pem:
            try:
                cert_obj = x509.load_pem_x509_certificate(legacy_pem.encode('utf-8'), default_backend())
                pub = cert_obj.public_key()
                if hasattr(pub, 'key_size') and isinstance(pub.key_size, int):
                    # RSA path
                    if pub.key_size >= 4096:
                        key_algorithm = 'RSA 4096'
                    elif pub.key_size >= 3072:
                        key_algorithm = 'RSA 3072'
                    else:
                        key_algorithm = f'RSA {pub.key_size}'
                else:
                    # ECC path
                    # cryptography exposes curve name via public_numbers().curve.name
                    try:
                        curve_name = pub.curve.name  # type: ignore[attr-defined]
                    except Exception:
                        curve_name = ''
                    cn = (curve_name or '').lower()
                    if '384' in cn:
                        key_algorithm = 'ECC P-384'
                    else:
                        key_algorithm = 'ECC P-256'
            except Exception as e:
                logger.debug(f"Failed to derive algorithm from PEM for device {device_real_id}: {e}")
                key_algorithm = 'ECC P-256'
        cert_info = {
            'serial_number': legacy_serial or 'UNKNOWN',
            'serialNumber': legacy_serial or 'UNKNOWN',
            'serial': legacy_serial or 'UNKNOWN',
            'status': device.get('certificate_status', 'valid'),
            'key_algorithm': key_algorithm,
            'algorithm': key_algorithm,
            'device_type': device.get('type', 'sensor'),
            'issued_at': legacy_issued or datetime.now().isoformat(),
            'expires_at': legacy_expires or (datetime.now() + timedelta(days=365)).isoformat(),
            'validFrom': legacy_issued or datetime.now().isoformat(),
            'validTo': legacy_expires or (datetime.now() + timedelta(days=365)).isoformat(),
            'issuer': device.get('certificate_issuer'),
            'subject': device.get('certificate_subject')
        }
        return {
            'exists': True,
            'certificate': cert_info,
            'download_urls': {
                'ca_chain': f'/api/v1/devices/{device_real_id}/certificate/download/ca-chain',
                'device_cert': f'/api/v1/devices/{device_real_id}/certificate/download/device-cert',
                'device_key': f'/api/v1/devices/{device_real_id}/certificate/download/device-key',
                'bundle': f'/api/v1/devices/{device_real_id}/certificate/download/bundle'
            }
        }
            
    return {
        'exists': False,
        'message': 'No certificate issued yet'
    }

# Input validation for certificate operations
def validate_certificate_input(device_id, additional_data=None):
    """Validate certificate operation input."""
    if not validate_device_id(device_id):
        raise ValidationError("Invalid device ID format")
    
    if additional_data:
        # Sanitize any string inputs
        for key, value in additional_data.items():
            if isinstance(value, str):
                additional_data[key] = sanitize_string(value)
    
    return device_id, additional_data
# [MODULARIZE:END] - CertificateInfoService

# [MODULARIZE:START] - CertificateIssuanceService# Description: Certificate issuance and generation via Vault PKI
# Dependencies: hvac, cryptography, auto_device_registration_service
# Estimated Size: 450 lines
# Priority: HIGH
@vault_circuit_breaker
@with_timeout(timeout_seconds=45)
@with_retry(max_retries=3, delay=2.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Certificate issuance failed. Please try again or contact support."
)
def issue_device_certificate(device_id, user):
    """
    Issue a new certificate for device using Vault PKI with comprehensive error handling.
    
    Args:
        device_id: Device identifier
        user: Current user
        
    Returns:
        dict: Certificate info or error
    """
    # Check if modular implementation should be used
    from .certificate_modular_bridge import issue_device_certificate_with_parallel
    modular_result = issue_device_certificate_with_parallel(device_id, user)
    if modular_result is not None:
        # If modular path succeeded, persist and return legacy-shaped response
        persisted = _persist_modular_issuance(device_id, user, modular_result)
        if persisted is not None:
            return persisted
        # If modular path returned an error payload, surface it
        if isinstance(modular_result, dict) and modular_result.get('success') is False:
            return {'error': 'Certificate generation failed', 'details': modular_result.get('error', 'Unknown error')}
        # Otherwise continue with legacy flow
    
    # Validate input
    device_id, _ = validate_certificate_input(device_id)
    
    db = get_db()
    if db is None:
        raise ConnectionFailure("Database connection not available")
        
    vault_client = get_vault()
    if not vault_client:
        # Fallback to local certificate generation when Vault is not available
        logger.warning("Vault PKI not available, using local certificate generation")
        from .local_certificate_generator import LocalCertificateGenerator
        local_gen = LocalCertificateGenerator()
        # Set a flag to use local generation later
        use_local_generation = True
    else:
        use_local_generation = False
    
    # Find device with retry logic to handle race conditions
    device = None
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries):
        if ObjectId.is_valid(device_id) and len(device_id) == 24:
            device = db.devices.find_one({'_id': ObjectId(device_id)})
        
        if not device:
            device = db.devices.find_one({'device_id': device_id})
        
        if device:
            logger.info(f"Device {device_id} found on attempt {attempt + 1}")
            break
        
        if attempt < max_retries - 1:
            logger.warning(f"Device {device_id} not found, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
            import time
            time.sleep(retry_delay)
            
    # AUTO-REGISTRATION: If device doesn't exist, attempt automatic registration
    if not device:
        logger.info(f"Device {device_id} not found, attempting automatic registration")
        
        # Extract device type and certificate algorithm from request or use defaults
        device_type = 'sensor'  # Default device type
        certificate_algorithm = None
        metadata = {}
        
        # Try to detect device type from device_id pattern
        device_id_lower = device_id.lower()
        if 'gateway' in device_id_lower or 'gw' in device_id_lower:
            device_type = 'gateway'
            certificate_algorithm = 'rsa-3072'  # Gateways typically use RSA
        elif 'psoc' in device_id_lower:
            device_type = 'edge_device'
            certificate_algorithm = 'ecc-p256'  # PSoC devices typically use ECC
        elif 'rpi' in device_id_lower or 'raspberry' in device_id_lower:
            device_type = 'gateway'
            certificate_algorithm = 'rsa-3072'
        elif 'env' in device_id_lower or 'environment' in device_id_lower:
            device_type = 'environmental_sensor'
            certificate_algorithm = 'ecc-p256'
        elif 'nav' in device_id_lower or 'navigation' in device_id_lower:
            device_type = 'navigation_device'
            certificate_algorithm = 'ecc-p256'
        elif 'health' in device_id_lower or 'medical' in device_id_lower:
            device_type = 'medical_device'
            certificate_algorithm = 'rsa-3072'  # Medical devices often need RSA for compliance
        else:
            # Default: small sensor device
            device_type = 'sensor'
            certificate_algorithm = 'ecc-p256'
        
        # Attempt automatic registration with timeout
        try:
            # Add timeout for auto-registration to prevent hanging
            success, message, registered_device = auto_device_registration_service.auto_register_device(
                device_id=device_id,
                device_type=device_type,
                organization_id=user.get('organization_id', ''),
                user=user,
                certificate_algorithm=certificate_algorithm,
                metadata=metadata
            )
            logger.info(f"Auto-registration call completed: success={success}, message={message}")
        except Exception as e:
            logger.error(f"Auto-registration exception: {e}")
            return {
                'error': 'Device not found and auto-registration encountered an error',
                'details': str(e),
                'device_id': device_id
            }
        
        if success and registered_device:
            device = registered_device
            logger.info(f"Successfully auto-registered device {device_id} as {device_type}")
        else:
            logger.warning(f"Auto-registration failed for device {device_id}: {message}")
            return {
                'error': 'Device not found and auto-registration failed',
                'details': message,
                'device_id': device_id,
                'auto_registration_attempted': True
            }
    
    # Continue with existing certificate issuance logic
    if not device:
        return None
    
    # Check organization access
    user_role = user.get('role', '')
    is_admin = user_role in ['super_admin', 'admin', 'organization_admin']
    
    if (not is_admin and 
        device.get('organization_id') != user.get('organization_id')):
        return {'error': 'Access denied'}
    
    # Get device info
    device_type = device.get('type', 'sensor')
    device_real_id = device.get('device_id', str(device['_id']))
    metadata = device.get('metadata', {})
    # Check both top-level and metadata for certificate_algorithm
    cert_algorithm = (device.get('certificate_algorithm') or 
                     metadata.get('certificate_algorithm') or 
                     metadata.get('certificateType'))

    # Additional fallback: infer from device name if available
    if not cert_algorithm:
        try:
            name_text = (device.get('name') or '').lower()
            if 'ecc384' in name_text or 'p-384' in name_text or 'ecc p-384' in name_text:
                cert_algorithm = 'ecc-p384'
            elif 'ecc256' in name_text or 'p-256' in name_text or 'ecc p-256' in name_text:
                cert_algorithm = 'ecc-p256'
            elif 'rsa4096' in name_text or 'rsa 4096' in name_text:
                cert_algorithm = 'rsa-4096'
            elif 'rsa' in name_text or 'rsa3072' in name_text or 'rsa 3072' in name_text:
                cert_algorithm = 'rsa-3072'
        except Exception:
            pass
    
    # Map UI values to internal values
    algorithm_mapping = {
        'ECC256': 'ecc-p256',
        'ECC384': 'ecc-p384',
        'RSA3072': 'rsa-3072',
        'RSA4096': 'rsa-4096',
        # Keep existing mappings for backward compatibility
        'ecc-p256': 'ecc-p256',
        'ecc-p384': 'ecc-p384',
        'rsa-3072': 'rsa-3072',
        'rsa-4096': 'rsa-4096'
    }
    
    # Normalize the algorithm value
    if cert_algorithm and cert_algorithm in algorithm_mapping:
        cert_algorithm = algorithm_mapping[cert_algorithm]
    
    # Determine key algorithm
    if cert_algorithm == 'ecc-p256':
        key_type = 'ec'
        key_bits = 256
        key_algorithm = 'ECC P-256'
    elif cert_algorithm == 'ecc-p384':
        key_type = 'ec'
        key_bits = 384
        key_algorithm = 'ECC P-384'
    elif cert_algorithm == 'rsa-3072':
        key_type = 'rsa'
        key_bits = 3072
        key_algorithm = 'RSA 3072'
    elif cert_algorithm == 'rsa-4096':
        key_type = 'rsa'
        key_bits = 4096
        key_algorithm = 'RSA 4096'
    else:
        # Auto-determine based on device type
        if device_type in ['sensor', 'actuator', 'air_quality', 'temperature_sensor']:
            key_type = 'ec'
            key_bits = 256
            key_algorithm = 'ECC P-256'
        else:
            key_type = 'rsa'
            key_bits = 3072
            key_algorithm = 'RSA 3072'
    
    # Check if we should use local certificate generation
    # Use local CA if explicitly set OR if Vault is not available
    use_local_ca = (os.environ.get('USE_LOCAL_CERTIFICATE_GENERATOR', 'false').lower() == 'true' or 
                    use_local_generation)
    
    if use_local_ca:
        # Use local certificate generator when Vault is not available
        logger.info(f"Using local certificate generator for device {device_real_id}")
        
        try:
            # If local_gen was already created above, use it
            if 'local_gen' not in locals():
                from .local_certificate_generator import LocalCertificateGenerator
                local_gen = LocalCertificateGenerator()
            
            # Get organization details for DN fields
            organization_name = "TESA IoT Device"
            locality = None
            state_province = None
            
            if device.get('organization_id'):
                org = db.organizations.find_one({'organization_id': device.get('organization_id')})
                if org:
                    organization_name = org.get('name', 'TESA IoT Device')
                    # Extract location info if available
                    if org.get('address'):
                        locality = org['address'].get('city')
                        state_province = org['address'].get('state')
            
            # Map key_type and key_bits to algorithm format expected by local generator
            if key_type == 'RSA':
                algorithm = f"RSA-{key_bits}"
            elif key_type == 'EC':
                # Map EC curves
                curve_map = {
                    256: 'EC-P256',
                    384: 'EC-P384',
                    521: 'EC-P521'
                }
                algorithm = curve_map.get(key_bits, 'EC-P256')
            else:
                algorithm = 'RSA-2048'  # Default
            
            # Prepare additional subject attributes
            additional_attrs = {}
            if locality:
                additional_attrs['L'] = locality
            if state_province:
                additional_attrs['ST'] = state_province
            
            # Generate certificate with full DN
            cert_pem, key_pem, ca_chain_pem = local_gen.generate_device_certificate(
                device_id=device_real_id,
                organization=organization_name,
                algorithm=algorithm,
                validity_days=365,
                additional_subject_attrs=additional_attrs if additional_attrs else None
            )
            
            # Parse the generated certificate to extract details
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            cert_obj = x509.load_pem_x509_certificate(cert_pem, default_backend())
            
            # Create cert_data dictionary matching expected format
            cert_data = {
                'certificate': cert_pem.decode('utf-8'),
                'private_key': key_pem.decode('utf-8'),
                'ca_chain': ca_chain_pem.decode('utf-8'),
                'serial_number': str(cert_obj.serial_number),
                'issuer_dn': cert_obj.issuer.rfc4514_string(),
                'subject_dn': cert_obj.subject.rfc4514_string(),
                'valid_from': cert_obj.not_valid_before.isoformat(),
                'valid_until': cert_obj.not_valid_after.isoformat(),
                'issuing_ca': cert_obj.issuer.rfc4514_string()
            }
            
            logger.info(f"Local certificate issued for {device_real_id}, serial: {cert_data.get('serial_number')}")
            # Continue to the common certificate processing code below
            
        except Exception as e:
            logger.error(f"Local certificate generation failed: {e}")
            return {'error': 'Certificate generation failed', 'details': f'Local generation error: {str(e)}'}
            
    else:
        # Use Vault PKI (original logic)
        # Generate certificate via Vault with comprehensive error handling
        if not vault_client:
            return {'error': 'Certificate service unavailable', 'details': 'Vault PKI is not configured'}
        
        # Validate Vault client authentication
        try:
            if not vault_client.is_authenticated():
                logger.error("Vault client not authenticated")
                return {'error': 'Certificate service authentication failed', 'details': 'Vault authentication invalid'}
        except VaultError as e:
            logger.error(f"Vault authentication check failed: {e}")
            return {'error': 'Certificate service authentication check failed', 'details': str(e)}
    
        # Debug logging
        logger.info(f"Vault client available: {vault_client is not None}")
        logger.info(f"Vault client authenticated: {vault_client.is_authenticated() if vault_client else False}")
        if hasattr(vault_client, 'token') and vault_client.token:
            logger.info(f"Vault token prefix: {vault_client.token[:20]}...")
        
        # Vault certificate issuance with timeout and retry
        vault_retries = 2
        for vault_attempt in range(vault_retries):
            try:
                # Select an /issue/-capable PKI role. The generic 'device-cert'
                # and 'csr-signing' roles are key_type=any, which Vault permits
                # only for /sign/ (CSR-supplied key), never /issue/ (Vault-
                # generated key) -- issuing against them fails with "role key
                # type 'any' not allowed for issuing certificates". Community
                # Edition issues EC P-256 client certificates for devices, which
                # the dedicated 'iot-device-ecc' role provides.
                role_name = 'iot-device-ecc'
                key_type, key_bits = 'ec', 256

                # Log the device type and algorithm for debugging
                logger.info(f"Device type: {device_type}, Algorithm: {key_type}, Bits: {key_bits}, Using role: {role_name}")
            
                
                # Best practice: use exact DEVICE_ID as CN for universal matching with MQTT clientId.
                # Provide SANs for future-proofing (DNS and URI), but primary auth uses CN == clientId.
                common_name = f"{device_real_id}"
                alt_dns = [
                    f"{device_real_id}.sensor.tesa.iot",
                    f"{device_real_id}.device.tesa.iot",
                    f"{device_real_id}.gateway.tesa.iot",
                ]
                uri_sans = [f"urn:tesa:iot:device:{device_real_id}"]
    
                
                logger.info(f"Requesting certificate from Vault PKI: role={role_name}, cn={common_name} (vault attempt {vault_attempt + 1})")
            
                # Issue certificate from INTERMEDIATE PKI for proper chain
                # Using pki-int mount to align with EMQX expectations
                resp = vault_client.write(
                    f'pki-int/issue/{role_name}',
                    common_name=common_name,
                    alt_names=",".join(alt_dns),
                    uri_sans=",".join(uri_sans),
                    exclude_cn_from_sans=True,
                    ttl='720h',  # 30 days
                    key_type=key_type,
                    key_bits=key_bits,
                    ou='IoT Devices',
                    organization='TESA IoT Device'
                )
            
                
                if not resp or 'data' not in resp:
                    raise VaultError("Invalid response from Vault PKI")
                
                cert_data = resp['data']
                if not cert_data.get('certificate') or not cert_data.get('private_key'):
                    raise VaultError("Incomplete certificate data from Vault")
            
                
                logger.info(f"Certificate issued for {device_real_id}, serial: {cert_data.get('serial_number')}")
                break  # Success, exit vault retry loop
            
            except (VaultError, InvalidRequest, Forbidden) as e:
                logger.warning(f"Vault certificate issuance attempt {vault_attempt + 1}/{vault_retries} failed: {e}")
                if vault_attempt < vault_retries - 1:
                    import time
                    time.sleep(1 * (vault_attempt + 1))
                    continue
                else:
                    logger.error(f"Failed to issue certificate via Vault after {vault_retries} attempts")
                    return {'error': 'Certificate generation failed', 'details': f'Vault PKI error: {str(e)}'}
                
            except Exception as e:
                logger.error(f"Unexpected error during certificate issuance: {e}")
                return {'error': 'Certificate generation failed', 'details': f'Unexpected error: {str(e)}'}
    
    # Parse the certificate to extract actual issuer and subject
    try:
        cert_pem = cert_data.get('certificate', '')
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        
        # Extract actual issuer and subject from certificate
        issuer_dn = cert.issuer.rfc4514_string()
        subject_dn = cert.subject.rfc4514_string()
        
        # Use actual certificate dates
        if use_local_ca and cert_data.get('not_valid_before'):
            # Local generator provides exact dates
            issued_at = cert_data['not_valid_before']
            expires_at = cert_data['not_valid_after']
        else:
            # Vault or fallback
            issued_at = datetime.now()  # Certificate just issued
            expires_at = cert.not_valid_after
        
    except Exception as e:
        logger.warning(f"Failed to parse certificate for metadata extraction: {e}")
        # Fallback to default values
        if use_local_ca:
            # Use the DN from local generator if available
            issuer_dn = cert_data.get('issuer_dn', 'CN=Local CA,O=TESA IoT Platform,C=TH')
            subject_dn = cert_data.get('subject_dn', f"CN={device_real_id}.device.tesa.iot")
        else:
            issuer_dn = 'CN=TESAIoT Intermediate CA,OU=PKI,O=TESA IoT Platform,C=TH'
            subject_dn = f"CN={device_real_id}.iot.tesa.or.th"
        issued_at = datetime.now()
        expires_at = issued_at + timedelta(days=365)
    
    # Prepare certificate info
    _prov, _issued_by = _detect_provisioning_method(device)
    cert_info = {
        'serial_number': cert_data.get('serial_number'),
        'serialNumber': cert_data.get('serial_number'),  # UI expects this field
        'serial': cert_data.get('serial_number'),  # Also include for backward compatibility
        'status': 'valid',
        'key_algorithm': _normalize_algorithm(key_algorithm),
        'algorithm': _normalize_algorithm(key_algorithm),  # UI expects this field name
        'device_type': device_type,
        'issued_at': issued_at.isoformat(),
        'expires_at': expires_at.isoformat(),
        'validFrom': issued_at.isoformat(),  # UI expects this field
        'validTo': expires_at.isoformat(),  # UI expects this field
        'issuer': issuer_dn,
        'subject': subject_dn,
        'issued_via': _prov,
        'validity_days': 365,
    }
    
    # Update device with certificate info - with error handling
    # Check if device is server_tls - they should keep 'ca_only' status
    if device.get('auth_mode') == 'server_tls':
        certificate_status = 'ca_only'
    else:
        certificate_status = 'valid'
    
    update_data = {
        'certificate_status': certificate_status,
        'certificate_info': cert_info,
        'certificate_issued_at': issued_at,
        'certificate_expires_at': expires_at,
        'certificate_serial': cert_data.get('serial_number'),
        'certificate': cert_data.get('certificate', ''),
        'certificate_chain': cert_data.get('ca_chain', []),
        'private_key': cert_data.get('private_key', ''),
        'certificate_algorithm': _normalize_algorithm(cert_algorithm if cert_algorithm else ('ecc-p256' if key_type == 'ec' else 'rsa-3072'))
    }
    
    # Also ensure it's in metadata
    update_data['metadata.certificate_algorithm'] = update_data['certificate_algorithm']
    
    try:
        result = db.devices.update_one(
            {'_id': device['_id']},
            {'$set': update_data}
        )
        if result.modified_count == 0:
            logger.warning(f"Device update for certificate failed - no documents modified for device {device_real_id}")
    except WriteError as e:
        logger.error(f"Failed to update device with certificate info: {e}")
        return {'error': 'Failed to save certificate to device', 'details': str(e)}
    
    # Log to audit trail with error handling
    try:
        db.certificate_issuance_log.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device_real_id,
            'device_name': device.get('name'),
            'serial_number': cert_data.get('serial_number'),
            'timestamp': datetime.now(),
            'performed_by': user.get('email'),
            'valid_until': expires_at,
            'details': f'Certificate issued successfully - {key_algorithm}'
        })
    except PyMongoError as e:
        logger.warning(f"Failed to log certificate issuance to audit trail: {e}")
        # Continue - this is not critical for certificate issuance
    
    # GDPR audit log with error handling
    try:
        audit_log(
            action=AuditAction.CERTIFICATE_ISSUE,
            user=user,
            resource_type='certificate',
            resource_id=device_real_id,
            details={
                'serial_number': cert_data.get('serial_number'),
                'algorithm': key_algorithm,
                'valid_until': expires_at.isoformat() if expires_at else None
            }
        )
    except Exception as e:
        logger.warning(f"Failed to create GDPR audit log for certificate issuance: {e}")
        # Continue - audit failure should not prevent certificate issuance

    # Fire device certificate notification (best-effort)
    try:
        org_id = device.get('organization_id')
        if org_id:
            notification_acl_service.create_device_certificate_notification(
                event='certificate_issued',
                device=device,
                organization_id=str(org_id),
                actor=user,
                priority='medium',
                metadata={
                    'serial_number': cert_data.get('serial_number'),
                    'algorithm': key_algorithm,
                    'expires_at': expires_at.isoformat() if expires_at else None,
                },
            )
    except Exception as notify_error:
        logger.warning(f"Notification dispatch failed for certificate issuance: {notify_error}")

    return {
        'message': 'Certificate issued successfully',
        'certificate': cert_info,
        'download_urls': {
            'ca_chain': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/ca-chain",
            'device_cert': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/device-cert",
            'device_key': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/device-key",
            'bundle': f"/api/v1/certificates/devices/{device_real_id}/certificate/download/bundle"
        }
    }
# [MODULARIZE:END] - CertificateIssuanceService

# [MODULARIZE:START] - CertificateListService# Description: Certificate listing and filtering operations
# Dependencies: pymongo, hvac
# Estimated Size: 100 lines
# Priority: MEDIUM
def _normalize_algorithm(algo):
    """Normalize certificate algorithm name to standard format."""
    if not algo:
        return 'ECC-P256'
    upper = algo.upper().strip()
    if upper in ('ECC-P256', 'ECC_P256', 'ECCP256'):
        return 'ECC-P256'
    if upper in ('ECC-256', 'ECC256'):
        return 'ECC-P256'
    if upper in ('RSA-2048', 'RSA2048'):
        return 'RSA-2048'
    if upper in ('RSA-4096', 'RSA4096'):
        return 'RSA-4096'
    return algo


def _detect_provisioning_method(device):
    """Detect provisioning method from device HSM capabilities.
    Returns (provisioning_method, issued_by_label) tuple."""
    has_hsm = bool(
        device.get('factory_uid') or
        device.get('trust_m_uid') or
        device.get('hsm_enabled') or
        (device.get('metadata') or {}).get('optiga_trust_m') or
        (device.get('metadata') or {}).get('trust_m_uid')
    )
    if has_hsm:
        return 'hsm_csr', 'Trust M + Vault CA'
    return 'sw_csr', 'TESAIoT Vault CA'


@vault_circuit_breaker
@with_timeout(timeout_seconds=45)
@with_retry(max_retries=3, delay=2.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Certificate signing failed. Please try again or contact support."
)
def get_certificates_list(user, filters=None):
    """
    Get list of certificates for authorized devices.

    Args:
        user: User making the request
        filters: Optional filters (status, org_id, etc.)

    Returns:
        List of certificate information
    """
    try:
        db = get_db()
        devices_collection = db['devices']
        
        # Build query based on user permissions
        query = {}
        
        # Filter by organization for non-admins
        if not RBAC.is_platform_admin(user):
            query['organization_id'] = user.get('organization_id')
            
        # Apply additional filters
        if filters:
            if 'status' in filters:
                query['certificate_status'] = filters['status']
            if 'device_id' in filters:
                query['device_id'] = filters['device_id']
                
        # Get devices with certificates
        devices = list(devices_collection.find(
            query,
            {
                'device_id': 1,
                'name': 1,
                'organization_id': 1,
                'certificate_info': 1,
                'certificate_status': 1,
                'device_public_key': 1,
                'created_at': 1,
                'updated_at': 1,
                # HSM detection fields for provisioning_method
                'factory_uid': 1,
                'trust_m_uid': 1,
                'hsm_enabled': 1
            }
        ))
        
        # Format certificate list
        certificates = []
        for device in devices:
            # Check for certificate by looking for certificate_serial instead of certificate_info
            if device.get('certificate_serial') or device.get('certificate_info'):
                cert_info_data = device.get('certificate_info', {}) or {}

                # Determine provisioning method:
                # 1. First check certificate_info.issued_via (from Protected Update)
                # 2. Fall back to HSM detection
                issued_via = cert_info_data.get('issued_via')
                if issued_via == 'hsm_protected_update':
                    provisioning_method = 'hsm_protected_update'
                elif issued_via == 'hsm_csr':
                    provisioning_method = 'hsm_csr'
                elif issued_via == 'sw_csr':
                    provisioning_method = 'sw_csr'
                else:
                    # Fall back to HSM field detection
                    has_hsm = bool(
                        device.get('factory_uid') or
                        device.get('trust_m_uid') or
                        device.get('hsm_enabled')
                    )
                    provisioning_method = 'hsm_csr' if has_hsm else 'sw_csr'

                cert_info = {
                    'device_id': device['device_id'],
                    'device_name': device.get('name', 'Unknown'),
                    'organization_id': device.get('organization_id'),
                    'status': device.get('certificate_status', 'unknown'),
                    'has_public_key': bool(device.get('device_public_key')),
                    'created_at': device.get('created_at'),
                    'updated_at': device.get('updated_at'),
                    # Provisioning method: sw_csr, hsm_csr, or hsm_protected_update
                    'provisioning_method': provisioning_method
                }

                # Add certificate details if available
                if isinstance(cert_info_data, dict) and cert_info_data:
                    # Support both old and new field naming conventions:
                    # Old: serial_number, key_algorithm, expires_at
                    # New: serial, algorithm, expiry_date
                    serial = cert_info_data.get('serial_number') or cert_info_data.get('serial')
                    algorithm = cert_info_data.get('key_algorithm') or cert_info_data.get('algorithm')
                    expires_at = cert_info_data.get('expires_at') or cert_info_data.get('expiry_date')
                    issued_at = cert_info_data.get('issued_at')

                    cert_info.update({
                        'serialNumber': serial,
                        'algorithm': _normalize_algorithm(algorithm),
                        'validFrom': issued_at,
                        'validTo': expires_at,
                        'issuer': cert_info_data.get('issuer'),
                        'subject': cert_info_data.get('subject'),
                        # Also keep the original field names for backward compatibility
                        'expires_at': expires_at,
                        'issued_at': issued_at
                    })
                # If certificate_info doesn't exist but certificate_serial does, build from individual fields
                elif device.get('certificate_serial'):
                    cert_info.update({
                        'serialNumber': device.get('certificate_serial'),
                        'algorithm': _normalize_algorithm(device.get('certificate_algorithm', 'RSA-2048')),
                        'validFrom': device.get('certificate_issued_at'),
                        'validTo': device.get('certificate_expires_at'),
                        'issuer': device.get('certificate_issuer', 'TESA IoT Platform CA'),
                        'subject': device.get('certificate_subject', f"CN={device.get('name', 'Unknown')}"),
                        # Also keep the original field names for backward compatibility
                        'expires_at': device.get('certificate_expires_at'),
                        'issued_at': device.get('certificate_issued_at')
                    })
                    
                certificates.append(cert_info)
                
        return certificates
        
    except Exception as e:
        print(f"Error getting certificates list: {str(e)}")
        return []
# [MODULARIZE:END] - CertificateListService


# [MODULARIZE:START] - CertificateDownloadService# Description: Certificate file download and packaging
# Dependencies: zipfile, cryptography, key_encryption_service
# Estimated Size: 300 lines
# Priority: HIGH
@vault_circuit_breaker
@with_timeout(timeout_seconds=30)
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Certificate signing failed. Please try again or contact support."
)
def download_certificate_file(device_id, file_type, user, skip_audit=False, auto_encrypt=False):
    """
    Download certificate files - returns stored certificates from database.
    
    Args:
        device_id: Device identifier
        file_type: Type of file to download
        user: Current user
        skip_audit: Skip audit logging (used when encryption will add its own audit)
        auto_encrypt: Auto-encrypt private key using device public key
        
    Returns:
        File content or error tuple
    """
    try:
        db = get_db()
        vault_client = get_vault()
        
        # SECURITY: Build query with organization filter upfront
        user_role = user.get('role', '')
        user_org_id = user.get('organization_id', '')
        organization_id = user_org_id  # Store for use in auto-encryption
        
        # Build device query with organization validation
        device_query = {}
        if ObjectId.is_valid(device_id):
            device_query['_id'] = ObjectId(device_id)
        else:
            device_query['device_id'] = device_id
        
        # Apply organization filter for non-platform admin users
        if not RBAC.is_platform_admin(user):
            device_query['organization_id'] = user_org_id
        
        # Find device with organization filter
        device = db.devices.find_one(device_query)
        
        if not device:
            # Don't reveal if device exists in other org
            logger.warning(f"Access denied: {user.get('email')} tried to download cert for device {device_id}")
            return ({'error': 'Device not found'}, 404)
        
        # Special handling for CA chain - available for all devices regardless of certificate status
        if file_type == 'ca-chain':
            # BEST PRACTICE: Self-healing CA chain management
            # Primary path defined in core configuration
            primary_ca_path = '/app/scripts/ca/tesaiot-ca-chain.pem'
            
            # Check if CA chain exists and is valid
            ca_chain_valid = False
            if os.path.exists(primary_ca_path):
                try:
                    with open(primary_ca_path, 'r') as f:
                        content = f.read()
                        if "BEGIN CERTIFICATE" in content and "END CERTIFICATE" in content:
                            ca_chain_valid = True
                except Exception as e:
                    logger.warning(f"CA chain file exists but may be invalid: {e}")
            
            # SELF-HEALING: If CA chain is missing or invalid, regenerate it
            if not ca_chain_valid:
                logger.warning("CA chain missing or invalid, triggering regeneration...")
                try:
                    # Import and run the CA chain initialization
                    from .database_init_service import DatabaseInitService
                    
                    # Create a temporary instance to regenerate CA chain
                    init_service = DatabaseInitService(db)
                    if init_service._initialize_ca_chain():
                        logger.info("CA chain successfully regenerated")
                        ca_chain_valid = True
                    else:
                        logger.error("Failed to regenerate CA chain")
                except Exception as e:
                    logger.error(f"Error during CA chain regeneration: {e}")
            
            # Try alternative paths if primary still doesn't exist
            fixed_ca_chain_path = primary_ca_path
            if not ca_chain_valid:
                # Fallback to environment variable or other paths
                ca_chain_paths = [
                    os.environ.get('CA_CHAIN_PATH'),  # Environment variable
                    '/app/pki/hierarchical/root-ca/certs/tesa-iot-ca-bundle.crt',  # Alternative Docker path
                ]
                
                for path in ca_chain_paths:
                    if path and os.path.exists(path):
                        fixed_ca_chain_path = path
                        logger.info(f"Using fallback CA chain path: {path}")
                        break
            
            try:
                # Read the fixed CA chain file
                with open(fixed_ca_chain_path, 'r') as f:
                    ca_chain_content = f.read().strip()
                
                if ca_chain_content:
                    content = f"""# TESA IoT Platform CA Certificate Chain
# ==========================================
# This certificate chain includes the CA hierarchy
# used by the platform for all device certificates.
# 
# Installation Instructions:
# -------------------------
# 
# For Linux/Raspberry Pi:
#   sudo cp {device_id}-ca-chain.pem /usr/local/share/ca-certificates/tesa-iot-ca.crt
#   sudo update-ca-certificates
# 
# For PSoC Edge/Embedded Devices:
#   Include this certificate in your firmware's trust store
#   Configure TLS to use this as the CA certificate file
# 
# For Python MQTT Clients:
#   client.tls_set(ca_certs='{device_id}-ca-chain.pem')
# 
# For Arduino/ESP32:
#   client.setCACert(ca_cert);  // Where ca_cert contains this certificate
# 
# MQTT Broker Connection:
# ----------------------
# Host: <your-broker-host>  (e.g. mqtts.tesaiot.dev)
# Port: 8883 (Secure MQTT)

{ca_chain_content}"""
                    logger.info(f"Using fixed CA chain from {fixed_ca_chain_path}")
                    
                    # Log the download
                    if not skip_audit:
                        audit_log(
                            action=AuditAction.CERTIFICATE_DOWNLOAD,
                            user=user,
                            resource_type='certificate',
                            resource_id=device_id,
                            details={
                                'file_type': file_type,
                                'device_name': device.get('name', ''),
                                'ca_chain_source': fixed_ca_chain_path
                            }
                        )
            except Exception as e:
                logger.error(f"Failed to read fixed CA chain file: {e}")
                # Return error if we can't read the fixed CA chain
                return ({'error': 'CA certificate chain unavailable. Could not read fixed CA chain file.'}, 503)
            
            # If still no content, return error
            if not content:
                return ({'error': 'CA certificate not available. Please contact support.'}, 404)
            
            filename = f"{device_id}-ca-chain.pem"
            return (content, filename)
        
        # For other file types, check if device has stored certificates
        # Support both direct certificate field and certificate_info.certificate (for CSR devices)
        # Determine device auth mode for downstream bundle logic
        device_auth_mode = str(device.get('auth_mode', 'mtls')).lower()
        metadata = device.get('metadata') or {}
        trust_profile = device.get('trust_profile') or metadata.get('trust_profile')
        secure_element = metadata.get('secure_element') or metadata.get('secureElement')

        is_trustm_mode = device_auth_mode in (
            'optiga_trust_mtls',
            'trustm_mtls',
            'optiga_trustm',
        )

        if not is_trustm_mode:
            if secure_element == 'infineon_optiga_trust_m':
                is_trustm_mode = True
            elif trust_profile == 'infineon_optiga_trust_m':
                is_trustm_mode = True
            elif metadata.get('factory_uid') and metadata.get('protected_update_enabled'):
                is_trustm_mode = True
            elif device.get('trustm_uid'):  # Device with Trust M UID is Trust M device
                is_trustm_mode = True

        cert_info = device.get('certificate_info', {})
        has_cert_in_info = cert_info and cert_info.get('certificate')
        has_direct_cert = device.get('certificate')
        
        # CSR devices won't have private_key, so check certificate availability differently
        is_csr_device = (
            device.get('generation_method') in ['external_csr', 'user_csr', 'upload_csr'] or
            cert_info.get('generation_method') == 'external_csr' or
            cert_info.get('csr_info') is not None
        )
        
        if not has_cert_in_info and not has_direct_cert:
            # No stored cert on device record; attempt fallbacks below before failing
            logger.warning(f"Device {device_id} has no stored certificate on device record; attempting fallback sources")
        
        # For non-CSR devices, also check private key
        if not is_csr_device and not is_trustm_mode and not device.get('private_key'):
            logger.warning(f"Device {device_id} has no private key")
            return ({'error': 'Certificate not found. Please generate certificate first.'}, 404)
        
        # Get stored certificate data - check both locations, normalize to PEM string
        def _extract_pem(val):
            """
            Extract a PEM string from various shapes (dict/str/bytes).
            Strictly return a PEM-looking value (contains BEGIN CERTIFICATE)
            or an empty string to force fallbacks — do NOT return JSON metadata.
            """
            def _to_text(x):
                return x.decode('utf-8') if isinstance(x, bytes) else x
            
            pem = ''
            if isinstance(val, dict):
                for k in ('certificate_pem', 'certificate', 'pem', 'content'):
                    v = val.get(k)
                    if isinstance(v, (str, bytes)) and v:
                        txt = _to_text(v)
                        if '-----BEGIN CERTIFICATE-----' in txt:
                            pem = txt
                            break
                # If no PEM-like content found, return empty to trigger DB fallback
                return pem
            if isinstance(val, (str, bytes)):
                txt = _to_text(val)
                if '-----BEGIN CERTIFICATE-----' in txt:
                    return txt
                return ''
            return ''

        # Get stored certificate data - check both locations
        stored_cert = _extract_pem(device.get('certificate', '')) or _extract_pem(cert_info.get('certificate', ''))
        
        # For CSR devices, also check the csr_certificates collection as fallback
        if not stored_cert and is_csr_device:
            csr_cert = db.csr_certificates.find_one({
                'device_id': device_id
            })
            if csr_cert:
                stored_cert = _extract_pem(csr_cert.get('certificate', ''))
                logger.info(f"Found certificate for CSR device {device_id} in csr_certificates collection")
        
        stored_key = _extract_pem(device.get('private_key', '')) if not is_csr_device else None
        raw_chain = device.get('certificate_chain', []) or cert_info.get('ca_chain', [])
        # Normalize chain values to strings
        stored_chain = []
        if isinstance(raw_chain, list):
            for item in raw_chain:
                stored_chain.append(_extract_pem(item))
        else:
            stored_chain = _extract_pem(raw_chain)

        # Fallback: pull latest from device_certificates if not present on device record
        if (not stored_cert or (not stored_key and not is_csr_device) or not stored_chain):
            try:
                latest = db.device_certificates.find_one(
                    {'device_id': device_id},
                    sort=[('issued_at', -1)]
                )
                if latest:
                    if not stored_cert:
                        stored_cert = _extract_pem(latest.get('certificate_pem', '')) or _extract_pem(latest.get('certificate', ''))
                    if not stored_chain:
                        chain_val = latest.get('ca_chain')
                        if isinstance(chain_val, list):
                            stored_chain = [_extract_pem(x) for x in chain_val]
                        elif isinstance(chain_val, str):
                            stored_chain = [chain_val]
                    if not is_csr_device and not stored_key:
                        stored_key = _extract_pem(latest.get('private_key_pem', stored_key))
            except Exception as e:
                logger.debug(f"device_certificates lookup failed for {device_id}: {e}")
        
        # Update download count
        db.devices.update_one(
            {'_id': device['_id']},
            {'$inc': {'certificate_download_count': 1}}
        )
        
        # GDPR audit log for certificate download
        audit_log(
            action=AuditAction.CERTIFICATE_DOWNLOAD,
            user=user,
            resource_type='certificate',
            resource_id=device_id,
            details={
                'file_type': file_type,
                'device_name': device.get('name', '')
            }
        )
        
        # Return certificate files based on type (with policy gates)
        try:
            pol = (db.org_policies.find_one({'organization_id': organization_id}) or {}).get('certificate', {}) if (db and organization_id) else {}
        except Exception:
            pol = {}
        require_csr_pol = pol.get('require_csr', os.environ.get('REQUIRE_CSR', 'true').lower() in ('1','true','yes'))
        allow_svr_keygen_pol = pol.get('allow_server_side_key_gen', os.environ.get('ALLOW_SERVER_SIDE_KEY_GEN','false').lower() in ('1','true','yes'))
        retain_key_at_rest_pol = pol.get('retain_private_key_at_rest', os.environ.get('RETAIN_PRIVATE_KEY_AT_REST','false').lower() in ('1','true','yes'))
        if file_type == 'device-cert':
            if not stored_cert:
                return ({'error': 'Certificate not available'}, 404)
            filename = f"{device_id}-certificate.pem"
            return (stored_cert, filename)
            
        elif file_type == 'device-key':
            # Disallow private key download when server-side keygen not permitted or retention disabled
            if not allow_svr_keygen_pol or not retain_key_at_rest_pol:
                return ({'error': 'DOWNLOAD_FORBIDDEN', 'message': 'Private key download disabled by policy. Use CSR or one-time encrypted delivery.'}, 403)
            if not stored_key:
                return ({'error': 'Private key not available'}, 404)

            # Check if auto-encryption is requested
            if auto_encrypt:
                # Prefer registered device public key; if missing, derive from certificate or private key
                device_public_key = device.get('device_public_key', {})
                public_key_pem = device_public_key.get('key') if isinstance(device_public_key, dict) else None
                if not public_key_pem:
                    try:
                        # Derive from device certificate first
                        from cryptography.hazmat.primitives import serialization
                        from cryptography import x509
                        from cryptography.hazmat.backends import default_backend as _backend
                        if stored_cert and 'BEGIN CERTIFICATE' in stored_cert:
                            cert_obj = x509.load_pem_x509_certificate(stored_cert.encode('utf-8'), _backend())
                            public_key_pem = cert_obj.public_key().public_bytes(
                                serialization.Encoding.PEM,
                                serialization.PublicFormat.SubjectPublicKeyInfo
                            ).decode('utf-8')
                        elif stored_key and 'BEGIN' in stored_key:
                            # Derive pub from private key as last resort
                            key_obj = serialization.load_pem_private_key(stored_key.encode('utf-8'), password=None, backend=_backend())
                            public_key_pem = key_obj.public_key().public_bytes(
                                serialization.Encoding.PEM,
                                serialization.PublicFormat.SubjectPublicKeyInfo
                            ).decode('utf-8')
                    except Exception as _e:
                        logger.debug(f"Could not derive public key for auto-encrypt: {_e}")

                if not public_key_pem:
                    logger.warning(f"Auto-encryption requested but device {device_id} has no public key available")
                    return ({'error': 'Auto-encryption requested but device has no public key available'}, 400)

                try:
                    # Determine encryption tier
                    device_type = device.get('type', 'sensor')
                    device_capabilities = device.get('capabilities', {})
                    encryption_tier = get_encryption_tier_for_device(device_type, device_capabilities)

                    # Encrypt the private key using the device's public key
                    encrypted_payload = encrypt_private_key_for_device(
                        private_key_pem=stored_key,
                        device_public_key_pem=public_key_pem,
                        device_id=device_id,
                        encryption_tier=encryption_tier,
                        metadata={
                            'device_name': device.get('name', ''),
                            'organization_id': organization_id,
                            'encrypted_by': user.get('email', 'system'),
                            'encryption_trigger': 'auto_encrypt_download'
                        }
                    )

                    # Create JSON response with encrypted data
                    encrypted_json = {
                        'device_id': device_id,
                        'encryption_method': 'hybrid-rsa-aes',
                        'auto_encrypted': True,
                        **encrypted_payload
                    }

                    # Convert to JSON string
                    content = json.dumps(encrypted_json, indent=2)
                    filename = f"{device_id}-private-key-encrypted.json"

                    # Log auto-encryption event if not skipping audit
                    if not skip_audit:
                        audit_log(
                            action=AuditAction.CERTIFICATE_DOWNLOAD,
                            user=user,
                            resource_type='certificate',
                            resource_id=device_id,
                            details={
                                'file_type': file_type,
                                'device_name': device.get('name', ''),
                                'auto_encrypted': True,
                                'encryption_method': 'hybrid-rsa-aes',
                                'encryption_tier': encryption_tier
                            }
                        )

                    logger.info(f"Auto-encrypted private key for device {device_id} using tier {encryption_tier}")
                    return (content, filename)

                except Exception as e:
                    logger.error(f"Failed to auto-encrypt private key for device {device_id}: {e}")
                    return ({'error': 'Auto-encryption failed', 'details': str(e)}, 500)
            else:
                # Non-encrypted download
                filename = f"{device_id}-private-key.pem"
                return (stored_key, filename)
            
        elif file_type in ('trustm-starter-bundle', 'trustm-starter'):
            if not is_trustm_mode:
                logger.warning(
                    "Trust M starter bundle request denied: device_id=%s auth_mode=%s secure_element=%s trust_profile=%s metadata_keys=%s",
                    device_id,
                    device_auth_mode,
                    secure_element,
                    trust_profile,
                    list(metadata.keys())
                )
                return ({'error': 'Device is not configured for OPTIGA Trust M'}, 400)

            from io import BytesIO
            import zipfile

            trustm_ca_pem = _fetch_trust_anchor_pem('tesa-trust-anchors/infineon-optiga-trust-m-ca')
            factory_cert_info = device.get('factory_certificate') or {}
            factory_cert_pem = factory_cert_info.get('pem')
            # Trust M UID: check device.trustm_uid first, then metadata.factory_uid, then factory_certificate.uid
            factory_uid = device.get('trustm_uid') or (device.get('metadata') or {}).get('factory_uid') or factory_cert_info.get('uid')

            # Optionally fetch TESAIoT CA chain for reference
            ca_chain_content = ''
            try:
                if vault_client:
                    root_ca = ''
                    int_ca = ''
                    for path in ('pki-int/cert/ca', 'pki_int/cert/ca'):
                        try:
                            resp = vault_client.read(path)
                            if resp and 'data' in resp:
                                int_ca = resp['data'].get('certificate', '') or int_ca
                        except Exception:
                            continue
                    for path in ('pki-root/cert/ca', 'pki/cert/ca'):
                        try:
                            resp = vault_client.read(path)
                            if resp and 'data' in resp:
                                root_ca = resp['data'].get('certificate', '') or root_ca
                        except Exception:
                            continue
                    combined = f"{int_ca}\n{root_ca}".strip()
                    if combined and 'BEGIN CERTIFICATE' in combined:
                        ca_chain_content = combined
            except Exception as chain_error:
                logger.debug(f"Unable to retrieve TESAIoT CA chain for Trust M starter bundle: {chain_error}")

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                starter_meta = {
                    'device_id': device_id,
                    'device_name': device.get('name'),
                    'trustm_uid': device.get('trustm_uid'),  # Trust M UID (27-byte hex from OID 0xE0C2)
                    'factory_uid': factory_uid,  # Unified UID field (trustm_uid or metadata.factory_uid)
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'factory_certificate_fingerprint': factory_cert_info.get('fingerprint_sha256'),
                    'factory_certificate_subject': factory_cert_info.get('subject'),
                    'factory_certificate_issuer': factory_cert_info.get('issuer'),
                }
                zip_file.writestr('factory_metadata.json', json.dumps(starter_meta, indent=2))

                if trustm_ca_pem:
                    zip_file.writestr('infineon-optiga-trust-m-ca.pem', trustm_ca_pem)
                if ca_chain_content:
                    zip_file.writestr('tesaiot-ca-chain.pem', ca_chain_content)
                if factory_cert_pem:
                    zip_file.writestr(f"{device_id}-factory-certificate.pem", factory_cert_pem)

                # Generate Trust M-specific mqtt_client_config.h header
                try:
                    template_path = '/app/scripts/templates/mqtt_client_config_trustm.h.template'
                    with open(template_path, 'r', encoding='utf-8') as template_file:
                        template_content = template_file.read()

                    def _format_cert_for_c(cert_pem: str) -> str:
                        if not cert_pem:
                            return ''
                        lines = cert_pem.strip().splitlines()
                        formatted = []
                        for line in lines:
                            escaped = line.replace('"', '\\"')
                            formatted.append(f'"{escaped}\\n"')
                        return ' \\\n'.join(formatted)

                    generation_ts = datetime.now(timezone.utc).isoformat()
                    trustm_host, trustm_port = _mqtt_broker_endpoint('mtls')
                    header_content = template_content.replace('{{DEVICE_ID}}', device_id)
                    header_content = header_content.replace('{{MQTT_USERNAME}}', device.get('device_id', device_id))
                    header_content = header_content.replace('{{GENERATION_DATE}}', generation_ts)
                    header_content = header_content.replace('{{MQTT_BROKER_HOST}}', trustm_host)
                    header_content = header_content.replace('{{MQTT_BROKER_PORT}}', str(trustm_port))
                    # Replace Trust M UID placeholder with actual UID
                    header_content = header_content.replace('{{TRUSTM_UID}}', factory_uid or device_id)

                    ca_chain_formatted = _format_cert_for_c(ca_chain_content)
                    if not ca_chain_formatted:
                        ca_chain_formatted = '""'

                    factory_anchor_formatted = _format_cert_for_c(trustm_ca_pem or '')
                    if not factory_anchor_formatted:
                        factory_anchor_formatted = '""'

                    header_content = header_content.replace('{{CA_CERTIFICATE}}', ca_chain_formatted)
                    # Factory bundle has no device cert/key yet (the Trust M secure
                    # element holds the key; the operational cert is issued later),
                    # so blank these placeholders rather than leaking them.
                    header_content = header_content.replace('{{CLIENT_CERTIFICATE}}', '""')
                    header_content = header_content.replace('{{CLIENT_PRIVATE_KEY}}', '""')
                    header_content = header_content.replace('{{FACTORY_CA_CERTIFICATE}}', factory_anchor_formatted)
                    # Defence-in-depth: never let an unfilled {{PLACEHOLDER}} reach
                    # the device header.
                    import re as _re
                    header_content = _re.sub(r'\{\{[A-Z_]+\}\}', '""', header_content)
                    zip_file.writestr('mqtt_client_config.h', header_content)
                except Exception as header_error:
                    logger.warning(f"Failed to generate Trust M starter header for {device_id}: {header_error}")

                # Generate HTTPS client configuration header
                try:
                    https_template_path = '/app/scripts/templates/https_client_config.h.template'
                    with open(https_template_path, 'r', encoding='utf-8') as https_template_file:
                        https_content = https_template_file.read()

                    https_content = https_content.replace('{{DEVICE_ID}}', device_id)
                    https_content = https_content.replace('{{GENERATION_DATE}}', datetime.now(timezone.utc).isoformat())
                    https_content = https_content.replace('{{INGEST_BASE_URL}}', _ingest_base_url())
                    zip_file.writestr('https_client_config.h', https_content)
                except Exception as https_error:
                    logger.warning(f"Failed to generate HTTPS config for {device_id}: {https_error}")

                # Auto-generated telemetry code (data_telemetry.c/.h)
                try:
                    from .telemetry_code_generator import add_telemetry_files_to_zip
                    add_telemetry_files_to_zip(zip_file, device, folder_prefix='telemetry')
                except Exception as telemetry_error:
                    logger.warning(f"Failed to generate telemetry code for {device_id}: {telemetry_error}")

                trustm_readme = f"""OPTIGA™ Trust M Starter Bundle
==================================

Device ID: {device_id}
Factory UID: {factory_uid or 'N/A'}
Generated: {datetime.now(timezone.utc).isoformat()}

Contents:
- factory_metadata.json              → UID and fingerprint summary
- infineon-optiga-trust-m-ca.pem     → Factory trust anchor (store in OID 0xE0E8)
- {device_id}-factory-certificate.pem → Factory device certificate (optional OID 0xE0E9)
- tesaiot-ca-chain.pem               → TESAIoT Root/Intermediate CA chain
- mqtt_client_config.h               → Preconfigured MQTT header for factory boot
- https_client_config.h              → HTTPS API endpoint configuration
- telemetry/                         → Auto-generated C code for telemetry
  - data_telemetry.h                 → Struct and function prototypes
  - data_telemetry.c                 → JSON serialization implementation
  - README.md                        → Usage documentation

Workflow:
1. Load the factory anchor into OID 0xE0E8 and optional factory cert into OID 0xE0E9.
2. Boot the device; the first TLS handshake uses the factory certificate.
3. Trigger a Protected Update job in TESAIoT to install TESAIoT credentials into OID 0xE0E1.
4. After the job reports status=applied, disable factory credential access.

Need help? https://tesaiot.github.io/developer-hub
"""
                zip_file.writestr('TRUSTM_README.txt', trustm_readme)

            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            ts = datetime.now().isoformat().replace(':', '-').split('.')[0]
            filename = f"{device_id}-trustm-starter-bundle-{ts}.zip"
            return (content, filename)

        elif file_type == 'bundle':
            # Create ZIP bundle with all certificates
            if not stored_cert and not is_trustm_mode:
                return ({'error': 'Certificate not available for bundle'}, 404)
            # Create ZIP bundle with all certificates
            if not stored_cert:
                return ({'error': 'Certificate not available for bundle'}, 404)
            
            # Create ZIP in memory
            import zipfile
            from io import BytesIO
            
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add device certificate when available (Trust M first boot may not have one yet)
                if stored_cert:
                    zip_file.writestr(f"{device_id}-certificate.pem", stored_cert)
                
                # Add CA chain with instructions
                ca_content = ""
                # First, try to read CA chain from Vault (most reliable)
                try:
                    if vault_client:
                        root_ca = ''
                        int_ca = ''
                        # Try both hyphen/underscore mounts for compatibility
                        for path in ('pki-int/cert/ca', 'pki_int/cert/ca'):
                            try:
                                r = vault_client.read(path)
                                if r and 'data' in r:
                                    int_ca = r['data'].get('certificate', '') or int_ca
                            except Exception:
                                continue
                        for path in ('pki-root/cert/ca', 'pki/cert/ca'):
                            try:
                                r = vault_client.read(path)
                                if r and 'data' in r:
                                    root_ca = r['data'].get('certificate', '') or root_ca
                            except Exception:
                                continue
                        chain = f"{int_ca}\n{root_ca}".strip()
                        if chain and 'BEGIN CERTIFICATE' in chain:
                            ca_content = chain
                except Exception:
                    # Continue to file fallbacks below
                    pass

                # If Vault not available or failed, try fixed file paths
                ca_chain_paths = [
                    os.environ.get('CA_CHAIN_PATH'),  # Environment variable
                    '/app/pki/hierarchical/root-ca/certs/tesa-iot-ca-bundle.crt',  # Docker container path
                    '/app/pki/hierarchical/root-ca/certs/ca-bundle.crt',  # Alternative Docker path
                    '/app/scripts/ca/tesaiot-ca-chain.pem',  # Legacy Docker path
                    os.path.join(os.path.dirname(__file__), '../../../../pki/hierarchical/root-ca/certs/tesa-iot-ca-bundle.crt'),  # Relative path
                    os.path.join(os.path.dirname(__file__), '../../../../config/certificates/poc2-mqtt/ca-chain.crt'),  # Legacy relative path
                    '/media/psf/BDH/TESA_IoT_Platform/lastest_portable_TESA_IoT_Platform/production-repo/pki/hierarchical/root-ca/certs/tesa-iot-ca-bundle.crt',  # Development path
                    '/media/psf/BDH/TESA_IoT_Platform/lastest_portable_TESA_IoT_Platform/production-repo/config/certificates/poc2-mqtt/ca-chain.crt'  # Legacy development path
                ]
                
                # Filter out None values and find the first existing file
                fixed_ca_chain_path = None
                for path in ca_chain_paths:
                    if path and os.path.exists(path):
                        fixed_ca_chain_path = path
                        break
                
                if not ca_content and fixed_ca_chain_path:
                    try:
                        with open(fixed_ca_chain_path, 'r') as f:
                            ca_chain_content = f.read().strip()
                        if ca_chain_content:
                            ca_content = f"""# TESA IoT Platform CA Certificate Chain
# ==========================================
# This certificate chain includes the CA hierarchy
# used by the platform for all device certificates.
# 
# Installation Instructions:
# -------------------------
# 
# For Linux/Raspberry Pi:
#   sudo cp {device_id}-ca-chain.pem /usr/local/share/ca-certificates/tesa-iot-ca.crt
#   sudo update-ca-certificates
# 
# For PSoC Edge/Embedded Devices:
#   Include this certificate in your firmware's trust store
#   Configure TLS to use this as the CA certificate file
# 
# For Python MQTT Clients:
#   client.tls_set(ca_certs='{device_id}-ca-chain.pem')

# Intermediate CA Certificate
{ca_chain_content}"""
                            logger.info(f"Using fixed CA chain from {fixed_ca_chain_path} for bundle")
                    except Exception as e:
                        logger.error(f"Failed to read fixed CA chain file for bundle: {e}")
                        # Don't include CA chain if we can't read the file
                
                # Always include CA certificate if available
                if ca_content:
                    # Write both simple and device-specific filenames for convenience/back-compat
                    zip_file.writestr("ca-chain.pem", ca_content)
                    zip_file.writestr(f"{device_id}-ca-chain.pem", ca_content)
                
                # Add private key with security notice only if policy allows retention
                if stored_key and retain_key_at_rest_pol:
                    security_notice = f"""SECURITY NOTICE - PRIVATE KEY
=====================================

Device: {device_id}
Created: {datetime.now().isoformat()}

KEEP THIS FILE SECURE!
This private key is required for device authentication.
Do not share or expose this key.

=====================================

{stored_key}"""
                    zip_file.writestr(f"{device_id}-private-key.pem", security_notice)
                else:
                    # No retained key or CSR device: include guidance file instead of key
                    guidance = (
                        "PRIVATE KEY NOT INCLUDED\n"
                        "=========================\n\n"
                        "This device is configured without key retention at rest or no key is available.\n"
                        "If your organization policy enables one-time encrypted key delivery, download\n"
                        "the key via the UI using the 'Device Private Key' action (auto-encrypted JSON).\n"
                    )
                    try:
                        zip_file.writestr("PRIVATE_KEY_README.txt", guidance)
                    except Exception:
                        pass

                # Add mqtt_client_config.h pre-filled for this device
                try:
                    # Derive algorithm label from certificate_info or device field
                    algo_label = None
                    if isinstance(cert_info, dict):
                        algo_label = cert_info.get('key_algorithm') or cert_info.get('algorithm')
                    if not algo_label:
                        device_alg = device.get('certificate_algorithm')
                        alg_map = {
                            'ecc-p256': 'ECC P-256',
                            'ecc-p384': 'ECC P-384',
                            'rsa-3072': 'RSA 3072',
                            'rsa-4096': 'RSA 4096'
                        }
                        algo_label = alg_map.get(device_alg, 'ECC P-256')

                    # Extract pure CA PEM for header (best available source)
                    ca_pem_for_header = ''
                    # 1) From bundled ca_content if present
                    if ca_content:
                        try:
                            start = ca_content.find('-----BEGIN CERTIFICATE-----')
                            ca_pem_for_header = ca_content[start:] if start != -1 else ca_content
                        except Exception:
                            ca_pem_for_header = ca_content
                    # 2) From device.certificate_chain stored in DB
                    if not ca_pem_for_header:
                        chain = device.get('certificate_chain')
                        if isinstance(chain, str) and 'BEGIN CERTIFICATE' in chain:
                            ca_pem_for_header = chain
                        elif isinstance(chain, list) and chain:
                            ca_pem_for_header = '\n'.join(chain)
                    # 3) From primary CA path as last resort
                    if not ca_pem_for_header:
                        try:
                            with open('/app/scripts/ca/tesaiot-ca-chain.pem', 'r') as f:
                                ca_pem_for_header = f.read()
                        except Exception:
                            pass

                    username = device.get('device_id', device_id)
                    auth_mode = device.get('auth_mode', 'mtls')
                    header_text = _build_mqtt_client_config_header_full(
                        device_id=device_id,
                        username=username,
                        auth_mode=auth_mode,
                        ca_pem=ca_pem_for_header,
                        cert_pem=stored_cert,
                        key_pem=stored_key if stored_key else None,
                        algorithm_label=algo_label
                    )
                    zip_file.writestr("mqtt_client_config.h", header_text)
                except Exception as e:
                    logger.warning(f"Failed to add mqtt_client_config.h to bundle for {device_id}: {e}")

                # Generate HTTPS client configuration header
                try:
                    https_template_path = '/app/scripts/templates/https_client_config.h.template'
                    with open(https_template_path, 'r', encoding='utf-8') as https_template_file:
                        https_content = https_template_file.read()

                    https_content = https_content.replace('{{DEVICE_ID}}', device_id)
                    https_content = https_content.replace('{{GENERATION_DATE}}', datetime.now(timezone.utc).isoformat())
                    https_content = https_content.replace('{{INGEST_BASE_URL}}', _ingest_base_url())
                    zip_file.writestr('https_client_config.h', https_content)
                except Exception as https_error:
                    logger.warning(f"Failed to generate HTTPS config for bundle {device_id}: {https_error}")

                # Prepare README contents section (align with key retention policy)
                contents_lines = [
                    f"- {device_id}-certificate.pem : Device certificate (for mTLS mode)",
                    f"- {device_id}-ca-chain.pem    : CA certificate chain (REQUIRED for all devices)",
                ]
                if stored_key and retain_key_at_rest_pol:
                    contents_lines.append(f"- {device_id}-private-key.pem : Device private key (KEEP SECURE! - included only when policy allows)")
                else:
                    contents_lines.append("- PRIVATE_KEY_README.txt    : Private key is not included by policy; use one-time encrypted download via UI if allowed")
                contents_lines.extend([
                    "- mqtt_client_config.h        : Pre-configured header file for PSoC Edge devices",
                    "- https_client_config.h       : HTTPS API configuration for REST endpoints",
                    "- README.txt                  : This file",
                ])

                # Add comprehensive README
                readme_content = f"""TESA IoT Platform - Device Certificate Bundle
=============================================

Device ID: {device_id}
Device Name: {device.get('name', 'Unknown')}
Generated: {datetime.now().isoformat()}
Certificate Algorithm: {device.get('certificate_info', {}).get('key_algorithm', 'Unknown')}

Contents:
{chr(10).join(contents_lines)}

==========================================
AUTHENTICATION MODES
==========================================

1. MUTUAL TLS (mTLS) - Highest Security
   - Uses all three files: CA cert, device cert, and private key
   - Two-way authentication between device and server
   - Recommended for: Linux devices, Raspberry Pi, gateways

2. SERVER-ONLY TLS - Resource Constrained Devices
   - Uses only CA certificate file
   - One-way authentication (server to device)
   - Recommended for: PSoC Edge, Arduino, ESP32
   - Configure device with auth_mode: "server_tls" in platform

==========================================
QUICK START GUIDE
==========================================

For PSoC Edge Devices:
----------------------
1. Replace your mqtt_client_config.h with the provided mqtt_client_config.h file
   OR
2. Copy the certificate definitions from the provided file to your existing config
   - The file is pre-configured with your device ID and formatted certificates
   - Supports both server-only TLS and mutual TLS modes

For Python/Raspberry Pi (mTLS):
-------------------------------
import paho.mqtt.client as mqtt
client = mqtt.Client(client_id="{device_id}")
client.username_pw_set("{device_id}", "")
client.tls_set(
    ca_certs="{device_id}-ca-chain.pem",
    certfile="{device_id}-certificate.pem",
    keyfile="{device_id}-private-key.pem"
)
client.connect("your-server.com", 8883)

For Python/Raspberry Pi (Server-only TLS):
------------------------------------------
import paho.mqtt.client as mqtt
client = mqtt.Client(client_id="{device_id}")
client.username_pw_set("{device_id}", "")
client.tls_set(ca_certs="{device_id}-ca-chain.pem")
client.connect("your-server.com", 8883)

==========================================
MQTT CONNECTION DETAILS
==========================================
Broker: your-server.com
Port: 8883 (Secure MQTT with TLS)
Username: {device_id}
Password: (leave empty or use device-specific password if configured)
Topics:
  - Telemetry: device/{device_id}/telemetry
  - Commands: device/{device_id}/commands

==========================================
SECURITY NOTES
==========================================
- ALWAYS use secure MQTT (port 8883) with TLS
- NEVER use plain MQTT (port 1883) in production
- Keep private key secure and never share it
- The CA certificate can be shared with all your devices
- Certificates expire after 1 year - plan for renewal

==========================================
TROUBLESHOOTING
==========================================
1. Certificate Verification Failed:
   - Ensure system time is correct
   - Install CA certificate in system trust store
   - For testing only: client.tls_insecure_set(True)

2. Connection Refused:
   - Check firewall allows port 8883
   - Verify device is registered and active
   - Check auth_mode setting matches certificate usage

3. Authentication Failed:
   - Username must match device_id
   - For mTLS: ensure all 3 files are used
   - For server-TLS: ensure auth_mode is set correctly

For support: contact your platform administrator
Documentation: https://tesaiot.github.io/developer-hub
"""
                zip_file.writestr("README.txt", readme_content)
                
                # Generate mqtt_client_config.h based on device auth mode
                device_auth_mode = str(device.get('auth_mode', 'mutual_tls')).lower()
                is_trustm_mode = device_auth_mode in (
                    'optiga_trust_mtls',
                    'trustm_mtls',
                    'optiga_trustm',
                )

                try:
                    # Determine template based on auth mode
                    if device_auth_mode == 'server_tls':
                        template_filename = 'mqtt_client_config_server_tls.h.template'
                    elif is_trustm_mode:
                        template_filename = 'mqtt_client_config_trustm.h.template'
                    else:
                        # Default to mTLS for 'mutual_tls', 'mtls', or any other value
                        template_filename = 'mqtt_client_config_mtls.h.template'
                    
                    # Load the appropriate template
                    template_path = f"/app/scripts/templates/{template_filename}"
                    with open(template_path, 'r') as template_file:
                        template_content = template_file.read()
                    
                    # Format certificates for C code (escape newlines and quotes)
                    def format_cert_for_c(cert_pem):
                        """Format PEM certificate for C header file."""
                        if not cert_pem or not cert_pem.strip():
                            return '""'  # Return empty C string for empty input
                        lines = cert_pem.strip().splitlines()
                        formatted_lines = []
                        for line in lines:
                            # Escape any quotes in the line and add C string formatting
                            escaped_line = line.replace('"', '\\"')
                            formatted_lines.append(f'"{escaped_line}\\n"')
                        return ' \\\n'.join(formatted_lines)
                    
                    # Prepare CA certificate
                    ca_cert_formatted = ""
                    if ca_content:
                        # Extract just the certificate part (remove comments)
                        ca_lines = ca_content.splitlines()
                        ca_cert_lines = []
                        in_cert = False
                        for line in ca_lines:
                            if '-----BEGIN CERTIFICATE-----' in line:
                                in_cert = True
                            if in_cert:
                                ca_cert_lines.append(line)
                            if '-----END CERTIFICATE-----' in line:
                                in_cert = False
                        ca_cert_pem = '\n'.join(ca_cert_lines)
                        ca_cert_formatted = format_cert_for_c(ca_cert_pem)
                    
                    # Format device certificate
                    device_cert_formatted = format_cert_for_c(stored_cert) if stored_cert else ""
                    
                    # Format private key with type detection comment
                    device_key_formatted = ""
                    if stored_key:
                        # Format the key without inline comment - template already has comments
                        device_key_formatted = format_cert_for_c(stored_key)

                    trustm_ca_formatted = ""
                    trustm_ca_pem = None
                    if is_trustm_mode:
                        trustm_ca_pem = _fetch_trust_anchor_pem('tesa-trust-anchors/infineon-optiga-trust-m-ca')
                        if trustm_ca_pem:
                            trustm_ca_formatted = format_cert_for_c(trustm_ca_pem)
                        else:
                            logger.warning("TrustM bundle requested but Infineon trust anchor not found in Vault")

                    # Replace template placeholders
                    username = device.get('device_id', device_id)
                    generation_ts = datetime.now(timezone.utc).isoformat()

                    # Get Trust M UID if available (for Trust M templates)
                    trustm_uid = device.get('trustm_uid', device_id)

                    bundle_host, bundle_port = _mqtt_broker_endpoint(device_auth_mode)
                    mqtt_config_content = template_content.replace('{{DEVICE_ID}}', device_id)
                    mqtt_config_content = mqtt_config_content.replace('{{TRUSTM_UID}}', trustm_uid)
                    mqtt_config_content = mqtt_config_content.replace('{{MQTT_USERNAME}}', username)
                    mqtt_config_content = mqtt_config_content.replace('{{GENERATION_DATE}}', generation_ts)
                    mqtt_config_content = mqtt_config_content.replace('{{ALGORITHM_LABEL}}', device.get('key_algorithm') or device.get('algorithm') or 'ECC P-256')
                    mqtt_config_content = mqtt_config_content.replace('{{MQTT_BROKER_HOST}}', bundle_host)
                    mqtt_config_content = mqtt_config_content.replace('{{MQTT_BROKER_PORT}}', str(bundle_port))
                    mqtt_config_content = mqtt_config_content.replace('{{CA_CERTIFICATE}}', ca_cert_formatted)
                    mqtt_config_content = mqtt_config_content.replace('{{CLIENT_CERTIFICATE}}', device_cert_formatted)

                    # Handle CLIENT_PRIVATE_KEY replacement based on mode
                    if is_trustm_mode and not device_key_formatted:
                        # Trust M mode without private key: remove the entire #define block
                        import re
                        # Remove CLIENT_PRIVATE_KEY definition including comment and define
                        mqtt_config_content = re.sub(
                            r'/\* TESAIoT-issued client private key[^*]*\*/\s*#define CLIENT_PRIVATE_KEY\s+\\\s*\{\{CLIENT_PRIVATE_KEY\}\}',
                            '',
                            mqtt_config_content
                        )
                    else:
                        # For mTLS or when key exists: replace with formatted key (or "" if empty)
                        mqtt_config_content = mqtt_config_content.replace('{{CLIENT_PRIVATE_KEY}}', device_key_formatted)

                    if '{{FACTORY_CA_CERTIFICATE}}' in mqtt_config_content:
                        mqtt_config_content = mqtt_config_content.replace('{{FACTORY_CA_CERTIFICATE}}', trustm_ca_formatted)

                    # Defence-in-depth: never let an unfilled {{PLACEHOLDER}} reach
                    # the device header (e.g. a placeholder absent from the chosen
                    # auth-mode template).
                    import re as _re
                    mqtt_config_content = _re.sub(r'\{\{[A-Z_]+\}\}', '""', mqtt_config_content)

                    # Add mqtt_client_config.h to ZIP
                    zip_file.writestr("mqtt_client_config.h", mqtt_config_content)

                    logger.info(f"Generated mqtt_client_config.h for device {device_id} with auth mode {device_auth_mode}")

                except Exception as e:
                    logger.warning(f"Failed to generate mqtt_client_config.h for device {device_id}: {e}")
                    # Continue without the config file - don't fail the entire bundle

                # Generate HTTPS client configuration header (separate file for clarity)
                try:
                    https_template_path = '/app/scripts/templates/https_client_config.h.template'
                    with open(https_template_path, 'r', encoding='utf-8') as https_template_file:
                        https_content = https_template_file.read()

                    https_content = https_content.replace('{{DEVICE_ID}}', device_id)
                    https_content = https_content.replace('{{GENERATION_DATE}}', datetime.now(timezone.utc).isoformat())
                    https_content = https_content.replace('{{INGEST_BASE_URL}}', _ingest_base_url())
                    zip_file.writestr('https_client_config.h', https_content)
                    logger.info(f"Generated https_client_config.h for device {device_id}")
                except Exception as https_error:
                    logger.warning(f"Failed to generate HTTPS config for {device_id}: {https_error}")

                if is_trustm_mode:
                    trustm_readme = """OPTIGA™ Trust M Factory Provisioning
=====================================

This bundle is tailored for the Infineon OPTIGA™ Trust M secure element.

Files included:
- mqtt_client_config.h              → drop in your PSoC Edge project
- https_client_config.h             → HTTPS API configuration for REST endpoints
- infineon-optiga-trust-m-ca.pem    → factory trust anchor (OID 0xE0E8)
- {device_id}-factory-certificate.pem → factory certificate (optional)

First boot flow:
1. Device connects using the factory certificate signed by Infineon.
2. TESAIoT accepts the fingerprinted factory certificate and records the connection.
3. Trigger a Protected Update job to rotate onto the TESAIoT-issued certificate.
4. Once the job reports status=applied, factory certificate access is disabled automatically.

Recommended OID mapping:
- Trust Anchor (E0E8)          → infineon-optiga-trust-m-ca.pem
- Factory Certificate (E0E9)   → {device_id}-factory-certificate.pem
- TESAIoT Certificate (E0E1)   → Applied via protected update service

Need help? https://tesaiot.github.io/developer-hub
""".replace('{device_id}', device_id)
                    zip_file.writestr("TRUSTM_README.txt", trustm_readme)
                    if trustm_ca_pem:
                        zip_file.writestr("infineon-optiga-trust-m-ca.pem", trustm_ca_pem)
                    factory_cert = (device.get('factory_certificate') or {}).get('pem')
                    if factory_cert:
                        zip_file.writestr(f"{device_id}-factory-certificate.pem", factory_cert)
            
            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            # Align naming with UI expectation and HTTPS bundle: include protocol/auth marker and timestamp
            ts = datetime.now().isoformat().replace(':', '-').split('.')[0]
            if is_trustm_mode:
                filename = f"{device_id}-mqtts-mtls-trustm-bundle-{ts}.zip"
            else:
                filename = f"{device_id}-mqtts-mtls-bundle-{ts}.zip"
            return (content, filename)

        
        elif file_type == 'https-mtls-bundle':
            # HTTPS-focused bundle with mTLS configs and samples (minimal, safe)
            if not stored_cert:
                return ({'error': 'Certificate not available for bundle'}, 404)

            import zipfile
            from io import BytesIO

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Device certificate
                zip_file.writestr(f"{device_id}-certificate.pem", stored_cert)

                # CA chain (prefer stored_chain if present)
                ca_content = ""
                try:
                    if stored_chain:
                        if isinstance(stored_chain, list):
                            ca_content = "\n".join([str(x) for x in stored_chain if x])
                        elif isinstance(stored_chain, str):
                            ca_content = stored_chain
                except Exception:
                    ca_content = ""
                if ca_content:
                    zip_file.writestr(f"{device_id}-ca-chain.pem", ca_content)

                # Private key, policy-aware
                if stored_key and retain_key_at_rest_pol:
                    zip_file.writestr(f"{device_id}-private-key.pem", stored_key)
                else:
                    notice = (
                        "Private key not included due to policy or CSR workflow.\n"
                        "If your organization enables one-time encrypted delivery, use the UI\n"
                        "to download the encrypted key (Device Private Key).\n"
                    )
                    zip_file.writestr("PRIVATE_KEY_README.txt", notice)

                # Endpoints descriptor (avoid local 'os' binding inside function)
                from os import getenv as _getenv
                api_base = _getenv('TESA_PUBLIC_API_BASE_URL', 'https://localhost')
                ingest_base = _getenv('TESA_PUBLIC_INGEST_BASE_URL', f"{api_base}:9444")
                endpoints = json.dumps({
                    # Standardize to public SAN to avoid hostname mismatch
                    'ingest_base_url': ingest_base,
                    'api_base_url': api_base,
                    'tls': {'require_mtls': True, 'alpn': ['h2', 'http/1.1']}
                }, indent=2)
                zip_file.writestr("endpoints.json", endpoints)

                # README
                readme = (
                    f"TESA IoT — HTTPS + mTLS Bundle\n"
                    f"Device: {device_id}\n"
                    f"Generated: {datetime.now().isoformat()}\n\n"
                    "Includes:\n"
                    f"- {device_id}-certificate.pem\n"
                    f"- {device_id}-ca-chain.pem (if available)\n"
                    f"- {device_id}-private-key.pem (if policy allows)\n"
                    "- endpoints.json\n\n"
                    "For support: contact your platform administrator\n"
                    "Documentation: https://tesaiot.github.io/developer-hub\n"
                )
                zip_file.writestr("README.txt", readme)

            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            filename = f"{device_id}-https-mtls-bundle.zip"
            return (content, filename)
        
        elif file_type == 'mqtt-quic-bundle':
            # Preview/stub bundle for MQTT over QUIC (staging-only enablement)
            if not stored_cert:
                return ({'error': 'Certificate not available for bundle'}, 404)

            import zipfile
            from io import BytesIO

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Device certificate
                zip_file.writestr(f"{device_id}-certificate.pem", stored_cert)

                # CA chain if available
                ca_content = ""
                try:
                    if stored_chain:
                        if isinstance(stored_chain, list):
                            ca_content = "\n".join([str(x) for x in stored_chain if x])
                        elif isinstance(stored_chain, str):
                            ca_content = stored_chain
                except Exception:
                    ca_content = ""
                if ca_content:
                    zip_file.writestr(f"{device_id}-ca-chain.pem", ca_content)

                # Private key policy
                if stored_key and retain_key_at_rest_pol:
                    zip_file.writestr(f"{device_id}-private-key.pem", stored_key)
                else:
                    zip_file.writestr("PRIVATE_KEY_README.txt",
                        "Private key not included due to policy or CSR workflow.\n"
                        "Use encrypted key download in UI if policy allows.\n")

                # QUIC endpoints (stub for staging) — env-driven, no baked-in host
                from os import getenv as _q_getenv
                quic_host = _q_getenv('TESA_PUBLIC_MQTT_HOST', _q_getenv('TESA_MQTT_DOMAIN', 'localhost'))
                endpoints_quic = json.dumps({
                    'quic': {
                        'host': quic_host,
                        'port': 443,
                        'alpn': ['mqtt', 'h3'],
                        'note': 'Preview only: enable on staging when broker QUIC listener is ready.'
                    }
                }, indent=2)
                zip_file.writestr("endpoints-quic.json", endpoints_quic)

                # README
                readme = (
                    f"TESA IoT — MQTT QUIC + mTLS (Preview)\n"
                    f"Device: {device_id}\n\n"
                    "This bundle is intended for early client testing on staging.\n"
                    "Broker QUIC listener must be enabled before use.\n"
                )
                zip_file.writestr("README.txt", readme)

            zip_buffer.seek(0)
            content = zip_buffer.getvalue()
            filename = f"{device_id}-mqtt-quic-bundle.zip"
            return (content, filename)
        else:
            return ({'error': 'Invalid file type'}, 400)
    
    except Exception as e:
        logger.error(f"Error downloading certificate: {e}")
        return ({'error': 'Download failed', 'details': str(e)}, 500)
# [MODULARIZE:END] - CertificateDownloadService

# [MODULARIZE:START] - PublicKeyManagementService# Description: Device public key extraction and management
# Dependencies: cryptography, pymongo
# Estimated Size: 100 lines
# Priority: MEDIUM
def get_device_public_key(device_id, include_history=False, user=None):
    """
    Get device public key in various formats.
    
    Args:
        device_id: Device identifier
        include_history: Whether to include key rotation history
        user: Current user object
        
    Returns:
        Dict with public key info or None if not found
    """
    try:
        db = get_db()
        
        # Get device info
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            logger.error(f"Device not found: {device_id}")
            return None
            
        # Check organization access
        if user and user.get('organization_id') != device.get('organization_id'):
            logger.warning(f"User from org {user.get('organization_id')} attempted to access device from org {device.get('organization_id')}")
            return None
            
        # Check if device has public key
        if not device.get('device_public_key'):
            logger.info(f"No public key registered for device {device_id}")
            return None
            
        # Build response
        result = {
            'device_id': device_id,
            'public_key': device['device_public_key'].get('key', '') if isinstance(device.get('device_public_key'), dict) else device.get('device_public_key', ''),
            'key_encryption_enabled': device.get('key_encryption_enabled', False),
            'registered_at': device.get('public_key_registered_at', device.get('created_at'))
        }
        
        # Add algorithm and fingerprint if available
        if isinstance(device.get('device_public_key'), dict):
            result['algorithm'] = device['device_public_key'].get('algorithm')
            result['fingerprint'] = device['device_public_key'].get('fingerprint')
        
        # Add metadata if available (fallback to legacy fields)
        if device.get('public_key_algorithm') and 'algorithm' not in result:
            result['algorithm'] = device['public_key_algorithm']
        if device.get('public_key_type'):
            result['key_type'] = device['public_key_type']
        if device.get('public_key_fingerprint') and 'fingerprint' not in result:
            result['fingerprint'] = device['public_key_fingerprint']
            
        # Add history if requested
        if include_history:
            history = db.device_key_history.find(
                {'device_id': device_id},
                {'_id': 0}
            ).sort('registered_at', -1).limit(10)
            result['history'] = list(history)
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting device public key: {e}")
        return None
# [MODULARIZE:END] - PublicKeyManagementService

# [MODULARIZE:START] - CertificateAlertService# Description: Certificate expiry alerts and notifications
# Dependencies: notification_service, pymongo
# Estimated Size: 200 lines
# Priority: MEDIUM
def get_alert_settings(user):
    """Get certificate alert settings for organization."""
    try:
        db = get_db()
        org_id = user.get('organization_id', 'default')
        
        settings = db.certificate_alerts.find_one({'organization_id': org_id})
        
        if not settings:
            settings = {
                'enabled': True,
                'thresholds': {
                    'days_90': True,
                    'days_60': True,
                    'days_30': True,
                    'days_7': True
                },
                'notifications': {
                    'email': {'enabled': False, 'recipients': []},
                    'webhook': {'enabled': False, 'url': '', 'headers': {}}
                },
                'schedule': {
                    'check_interval': 'daily',
                    'last_check': None,
                    'next_check': None
                }
            }
        
        settings.pop('_id', None)
        settings.pop('organization_id', None)
        return settings
        
    except Exception as e:
        logger.error(f"Error getting alert settings: {e}")
        raise

def update_alert_settings(data, user):
    """Update certificate alert settings."""
    try:
        db = get_db()
        org_id = user.get('organization_id', 'default')
        
        data['organization_id'] = org_id
        data['updated_at'] = datetime.now()
        data['updated_by'] = user.get('email')
        
        db.certificate_alerts.update_one(
            {'organization_id': org_id},
            {'$set': data},
            upsert=True
        )
        
        logger.info(f"Alert settings updated for org {org_id}")
        
    except Exception as e:
        logger.error(f"Error updating alert settings: {e}")
        raise

def check_expiring_certificates():
    """Check for expiring certificates and send alerts."""
    try:
        db = get_db()
        
        # Get all enabled alert settings
        alert_settings = list(db.certificate_alerts.find({'enabled': True}))
        alerts_sent = 0
        
        for settings in alert_settings:
            org_id = settings['organization_id']
            devices = list(db.devices.find({'organization_id': org_id}))
            
            for device in devices:
                if not device.get('certificate_info'):
                    continue
                
                cert_info = device['certificate_info']
                expiry_str = cert_info.get('expires_at') or cert_info.get('expiration')
                if not expiry_str:
                    continue
                
                # Parse expiry date
                if isinstance(expiry_str, str):
                    expiry_date = parser.parse(expiry_str)
                else:
                    expiry_date = expiry_str
                
                days_to_expiry = (expiry_date - datetime.now()).days
                
                # Check thresholds
                alert_needed = False
                threshold_triggered = None
                
                thresholds = settings.get('thresholds', {})
                if days_to_expiry <= 7 and thresholds.get('days_7'):
                    alert_needed = True
                    threshold_triggered = 7
                elif days_to_expiry <= 30 and thresholds.get('days_30'):
                    alert_needed = True
                    threshold_triggered = 30
                elif days_to_expiry <= 60 and thresholds.get('days_60'):
                    alert_needed = True
                    threshold_triggered = 60
                elif days_to_expiry <= 90 and thresholds.get('days_90'):
                    alert_needed = True
                    threshold_triggered = 90
                
                if alert_needed:
                    # Check if already sent
                    alert_key = f"{device['device_id']}_{threshold_triggered}"
                    existing_alert = db.certificate_alert_history.find_one({
                        'alert_key': alert_key,
                        'sent_at': {'$gte': datetime.now() - timedelta(days=threshold_triggered)}
                    })
                    if existing_alert is not None:
                        continue
                    
                    # Send notifications
                    notifications = settings.get('notifications', {})
                    
                    email_config = notifications.get('email', {})
                    recipients = email_config.get('recipients', [])
                    email_enabled = email_config.get('enabled', False)

                    send_certificate_expiry_notification(
                        device,
                        days_to_expiry,
                        recipients if email_enabled else None,
                        send_email=email_enabled
                    )
                    
                    # Webhook notification
                    if notifications.get('webhook', {}).get('enabled'):
                        webhook_url = notifications['webhook'].get('url')
                        if webhook_url:
                            payload = {
                                'alert_type': 'certificate_expiry',
                                'device_id': device.get('device_id'),
                                'device_name': device.get('name'),
                                'days_to_expiry': days_to_expiry,
                                'threshold': threshold_triggered,
                                'serial_number': cert_info.get('serial_number')
                            }
                            send_webhook_notification(webhook_url, payload)
                    
                    # Record alert
                    db.certificate_alert_history.insert_one({
                        'alert_key': alert_key,
                        'organization_id': org_id,
                        'device_id': device['device_id'],
                        'threshold_days': threshold_triggered,
                        'days_to_expiry': days_to_expiry,
                        'sent_at': datetime.now()
                    })
                    
                    alerts_sent += 1
        
        # Update last check time
        db.certificate_alerts.update_many(
            {'enabled': True},
            {'$set': {
                'schedule.last_check': datetime.now(),
                'schedule.next_check': datetime.now() + timedelta(hours=24)
            }}
        )
        
        return alerts_sent
        
    except Exception as e:
        logger.error(f"Error checking expiring certificates: {e}")
        raise
# [MODULARIZE:END] - CertificateAlertService

# [MODULARIZE:START] - CertificateAutoRenewalService# Description: Automated certificate renewal management
# Dependencies: pymongo, audit_service
# Estimated Size: 250 lines
# Priority: MEDIUM
def get_auto_renewal_settings(user):
    """Get auto-renewal settings for organization."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        settings = db.certificate_auto_renewal.find_one({'organization_id': org_id})
        
        if not settings:
            settings = {
                'enabled': False,
                'threshold': 30,
                'excluded_devices': [],
                'require_approval': False,
                'max_retries': 3,
                'vault_role': 'device-cert-role',
                'template': 'default'
            }
        else:
            settings.pop('_id', None)
            settings.pop('organization_id', None)
        
        return settings
        
    except Exception as e:
        logger.error(f"Error getting auto-renewal settings: {e}")
        raise

def update_auto_renewal_settings(data, user):
    """Update auto-renewal settings."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        data['organization_id'] = org_id
        data['updated_at'] = datetime.now()
        data['updated_by'] = user.get('email')
        
        db.certificate_auto_renewal.replace_one(
            {'organization_id': org_id},
            data,
            upsert=True
        )
        
        logger.info(f"Auto-renewal settings updated for org {org_id}")
        
    except Exception as e:
        logger.error(f"Error updating auto-renewal settings: {e}")
        raise

def trigger_certificate_renewal(user):
    """Manually trigger certificate renewal check."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        # Get settings
        settings = db.certificate_auto_renewal.find_one({'organization_id': org_id})
        
        if not settings or not settings.get('enabled'):
            return {'error': 'Auto-renewal is not enabled'}
        
        threshold_days = settings.get('threshold', 30)
        excluded_devices = settings.get('excluded_devices', [])
        require_approval = settings.get('require_approval', False)
        
        # Find candidates
        renewal_candidates = []
        devices = db.devices.find({'organization_id': org_id})
        
        for device in devices:
            if device.get('device_id') in excluded_devices:
                continue
            
            cert_info = device.get('certificate_info', {})
            expiry_str = cert_info.get('expires_at') or cert_info.get('expiration')
            if expiry_str:
                if isinstance(expiry_str, str):
                    expiry_date = parser.parse(expiry_str)
                else:
                    expiry_date = expiry_str
                
                days_to_expiry = (expiry_date - datetime.now()).days
                
                if 0 < days_to_expiry <= threshold_days:
                    renewal_candidates.append({
                        'device_id': device['device_id'],
                        'device_name': device.get('name'),
                        'days_to_expiry': days_to_expiry,
                        'current_serial': cert_info.get('serial_number')
                    })
        
        # Process renewals
        renewals_initiated = 0
        renewal_results = []
        
        for candidate in renewal_candidates:
            try:
                if require_approval:
                    # Create approval request
                    db.certificate_approval_requests.insert_one({
                        'organization_id': org_id,
                        'device_id': candidate['device_id'],
                        'device_name': candidate['device_name'],
                        'days_to_expiry': candidate['days_to_expiry'],
                        'requested_at': datetime.now(),
                        'requested_by': 'auto-renewal',
                        'status': 'pending'
                    })
                    
                    renewal_results.append({
                        'device_id': candidate['device_id'],
                        'status': 'pending_approval'
                    })
                else:
                    # Initiate renewal
                    renewal_results.append({
                        'device_id': candidate['device_id'],
                        'status': 'renewal_initiated'
                    })
                    renewals_initiated += 1
                    
                    # Log renewal with complete schema
                    _prov, _issued_by = _detect_provisioning_method(
                        db.devices.find_one({'device_id': candidate['device_id']}) or {}
                    )
                    db.certificate_renewal_history.insert_one({
                        'organization_id': org_id,
                        'device_id': candidate['device_id'],
                        'device_name': candidate.get('device_name'),
                        'action': 'renewal_initiated',
                        'method': 'csr',
                        'provisioning_method': _prov,
                        'renewal_date': datetime.now(),
                        'timestamp': datetime.now(),
                        'initiated_at': datetime.now(),
                        'initiated_by': user.get('email'),
                        'trigger': 'manual',
                        'days_to_expiry': candidate['days_to_expiry'],
                        'old_serial': candidate['current_serial'],
                        'algorithm': 'ECC-P256',
                        'validity_days': 365,
                        'issued_by': _issued_by,
                        'status': 'initiated'
                    })
                    
            except Exception as e:
                logger.error(f"Failed to renew {candidate['device_id']}: {e}")
                renewal_results.append({
                    'device_id': candidate['device_id'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        return {
            'message': 'Auto-renewal check completed',
            'candidates_found': len(renewal_candidates),
            'renewals_initiated': renewals_initiated,
            'require_approval': require_approval,
            'results': renewal_results,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering renewal: {e}")
        raise

def send_test_notification(notification_type, data):
    """Send test notification to verify configuration."""
    try:
        if notification_type == 'email':
            recipients = data.get('recipients', [])
            if not recipients:
                return False, 'Email recipients required'
            
            subject = "[TESA IoT] Test Notification"
            body = f"""This is a test notification from TESA IoT Platform.

If you received this email, your SMTP configuration is working correctly.

Configuration Details:
- SMTP Host: {os.environ.get('SMTP_HOST', 'Not configured')}
- SMTP Port: {os.environ.get('SMTP_PORT', 'Not configured')}
- SMTP TLS: {os.environ.get('SMTP_TLS', 'true')}

This is an automated test message.
"""
            
            success = send_email_notification(recipients[0], subject, body)
            
            if success:
                return True, f'Test email sent to {recipients}'
            else:
                return False, 'Failed to send test email'
                
        elif notification_type == 'webhook':
            webhook_url = data.get('webhook_url')
            if not webhook_url:
                return False, 'Webhook URL required'
            
            test_payload = {
                'test': True,
                'alert_type': 'test_notification',
                'message': 'This is a test webhook from TESA IoT Platform',
                'timestamp': datetime.now().isoformat()
            }
            
            success = send_webhook_notification(webhook_url, test_payload)
            
            if success:
                return True, f'Test webhook sent to {webhook_url}'
            else:
                return False, 'Failed to send test webhook'
        else:
            return False, 'Invalid notification type'
            
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return False, str(e)
# [MODULARIZE:END] - CertificateAutoRenewalService

# [MODULARIZE:START] - CertificateAuditService# Description: Certificate audit trail and compliance logging
# Dependencies: pymongo, datetime
# Estimated Size: 150 lines
# Priority: HIGH
def get_audit_trail(user, start_date=None, end_date=None):
    """Get certificate audit trail events."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        # Build query
        query = {'organization_id': org_id}
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter['$gte'] = datetime.fromisoformat(start_date)
            if end_date:
                date_filter['$lte'] = datetime.fromisoformat(end_date)
            query['timestamp'] = date_filter
        
        audit_events = []
        
        # Get issuance events
        for event in db.certificate_issuance_log.find(query).sort('timestamp', -1).limit(1000):
            audit_events.append({
                'id': str(event.get('_id', '')),
                'timestamp': event.get('timestamp', datetime.now()).isoformat(),
                'action': 'issued',
                'device_id': event.get('device_id'),
                'device_name': event.get('device_name'),
                'serial_number': event.get('serial_number'),
                'performed_by': event.get('performed_by', 'System'),
                'valid_until': event.get('valid_until').isoformat() if event.get('valid_until') else None,
                'details': event.get('details', 'Certificate issued')
            })
        
        # Get renewal events
        for event in db.certificate_renewal_history.find(query).sort('initiated_at', -1).limit(1000):
            audit_events.append({
                'id': str(event.get('_id', '')),
                'timestamp': event.get('initiated_at', datetime.now()).isoformat(),
                'action': 'renewed',
                'device_id': event.get('device_id'),
                'device_name': event.get('device_name'),
                'serial_number': event.get('new_serial', event.get('old_serial')),
                'old_serial': event.get('old_serial'),
                'performed_by': event.get('initiated_by', 'System'),
                'details': event.get('details', f"Status: {event.get('status', 'completed')}")
            })
        
        # Get revocation events
        for event in db.certificate_revocation_log.find(query).sort('revoked_at', -1).limit(1000):
            audit_events.append({
                'id': str(event.get('_id', '')),
                'timestamp': event.get('revoked_at', datetime.now()).isoformat(),
                'action': 'revoked',
                'device_id': event.get('device_id'),
                'device_name': event.get('device_name'),
                'serial_number': event.get('serial_number'),
                'performed_by': event.get('revoked_by', 'System'),
                'reason': event.get('reason', 'Manual revocation'),
                'details': event.get('details', 'Certificate revoked')
            })
        
        # Sort by timestamp
        audit_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit to 500 most recent
        return audit_events[:500]
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}")
        raise

def export_audit_trail(user):
    """Export complete audit trail for organization."""
    try:
        audit_events = get_audit_trail(user)  # Get all events
        
        return {
            'export_date': datetime.now().isoformat(),
            'organization_id': user.get('organization_id'),
            'exported_by': user.get('email'),
            'total_events': len(audit_events),
            'events': audit_events
        }
        
    except Exception as e:
        logger.error(f"Error exporting audit trail: {e}")
        raise
# [MODULARIZE:END] - CertificateAuditService

# [MODULARIZE:START] - BulkOperationsService# Description: Bulk certificate operations (revoke, renew, export)
# Dependencies: pymongo, audit_service
# Estimated Size: 200 lines
# Priority: MEDIUM
def perform_bulk_operation(operation, certificate_ids, user):
    """Perform bulk operations on certificates."""
    try:
        db = get_db()
        results = {
            'operation': operation,
            'total': len(certificate_ids),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for cert_id in certificate_ids:
            try:
                if operation == 'renew':
                    # Implement renewal logic
                    device = db.devices.find_one({'_id': ObjectId(cert_id)})
                    if device:
                        # Log renewal request with complete schema
                        _prov, _issued_by = _detect_provisioning_method(device)
                        db.certificate_renewal_history.insert_one({
                            'organization_id': device.get('organization_id'),
                            'device_id': device.get('device_id'),
                            'device_name': device.get('name'),
                            'action': 'renewal_initiated',
                            'method': 'csr',
                            'provisioning_method': _prov,
                            'renewal_date': datetime.now(),
                            'timestamp': datetime.now(),
                            'initiated_at': datetime.now(),
                            'initiated_by': user.get('email'),
                            'trigger': 'bulk_operation',
                            'old_serial': device.get('certificate_serial'),
                            'algorithm': _normalize_algorithm(device.get('certificate_algorithm')),
                            'validity_days': 365,
                            'issued_by': _issued_by,
                            'status': 'pending'
                        })
                        results['successful'] += 1
                        results['details'].append({
                            'id': cert_id,
                            'status': 'renewal_initiated'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'id': cert_id,
                            'status': 'failed',
                            'error': 'Device not found'
                        })
                        
                elif operation == 'revoke':
                    # Implement revocation logic
                    device = db.devices.find_one({'_id': ObjectId(cert_id)})
                    if device:
                        db.devices.update_one(
                            {'_id': device['_id']},
                            {'$set': {
                                'certificate_status': 'revoked',
                                'certificate_revoked_at': datetime.now(),
                                'certificate_revoked_by': user.get('email')
                            }}
                        )
                        
                        # Log revocation
                        db.certificate_revocation_log.insert_one({
                            'organization_id': device.get('organization_id'),
                            'device_id': device.get('device_id'),
                            'device_name': device.get('name'),
                            'serial_number': device.get('certificate_serial', 'Unknown'),
                            'revoked_at': datetime.now(),
                            'revoked_by': user.get('email'),
                            'reason': 'Bulk revocation',
                            'details': 'Revoked via bulk operation'
                        })
                        
                        results['successful'] += 1
                        results['details'].append({
                            'id': cert_id,
                            'status': 'revoked'
                        })
                    else:
                        results['failed'] += 1
                        results['details'].append({
                            'id': cert_id,
                            'status': 'failed',
                            'error': 'Device not found'
                        })
                        
                elif operation == 'export':
                    # Export operation would be handled differently
                    results['successful'] += 1
                    results['details'].append({
                        'id': cert_id,
                        'status': 'exported'
                    })
                    
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'id': cert_id,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
        
    except Exception as e:
        logger.error(f"Error performing bulk operation: {e}")
        raise
# [MODULARIZE:END] - BulkOperationsService

# [MODULARIZE:START] - CertificateAnalyticsService# Description: Certificate usage analytics and reporting
# Dependencies: pymongo, datetime
# Estimated Size: 150 lines
# Priority: LOW
def get_certificate_analytics(user):
    """Get certificate analytics data."""
    try:
        db = get_db()
        org_query = {}
        
        if user.get('role') != 'super_admin':
            org_query = {'organization_id': user.get('organization_id')}
        
        # Total certificates
        total_certificates = db.devices.count_documents({
            **org_query,
            'certificate_status': {'$exists': True}
        })
        
        # Valid certificates
        valid_certificates = db.devices.count_documents({
            **org_query,
            'certificate_status': 'valid'
        })
        
        # Expiring soon (30 days)
        expiring_soon = 0
        devices = db.devices.find({
            **org_query,
            'certificate_expires_at': {'$exists': True}
        })
        
        for device in devices:
            expires_at = device.get('certificate_expires_at')
            if expires_at:
                if isinstance(expires_at, str):
                    expires_at = parser.parse(expires_at)
                days_to_expiry = (expires_at - datetime.now()).days
                if 0 < days_to_expiry <= 30:
                    expiring_soon += 1
        
        # Get issuance trend (last 7 days)
        issuance_trend = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            
            count = db.certificate_issuance_log.count_documents({
                **org_query,
                'timestamp': {'$gte': start, '$lt': end}
            })
            
            issuance_trend.append({
                'date': start.strftime('%Y-%m-%d'),
                'count': count
            })
        
        issuance_trend.reverse()
        
        # Algorithm distribution
        algorithm_dist = []
        for alg in ['RSA 3072', 'ECC P-256', 'RSA 4096']:
            count = db.devices.count_documents({
                **org_query,
                'certificate_info.key_algorithm': alg
            })
            if count > 0:
                algorithm_dist.append({
                    'algorithm': alg,
                    'count': count
                })
        
        return {
            'total_certificates': total_certificates,
            'valid_certificates': valid_certificates,
            'revoked_certificates': db.devices.count_documents({
                **org_query,
                'certificate_status': 'revoked'
            }),
            'expiring_soon': expiring_soon,
            'issuance_trend': issuance_trend,
            'algorithm_distribution': algorithm_dist,
            'renewal_success_rate': 95.5,  # Placeholder
            'average_validity_days': 365,
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting certificate analytics: {e}")
        raise
# [MODULARIZE:END] - CertificateAnalyticsService

# [MODULARIZE:START] - ACMEIntegrationService# Description: ACME protocol integration for automated certificates
# Dependencies: pymongo, audit_service
# Estimated Size: 300 lines
# Priority: MEDIUM
def get_acme_settings(user):
    """Get ACME protocol settings."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        settings = db.acme_settings.find_one({'organization_id': org_id})
        
        if not settings:
            settings = {
                'enabled': False,
                'server': 'https://acme-v02.api.letsencrypt.org/directory',
                'email': '',
                'key_type': 'rsa',
                'key_size': 2048,
                'auto_renewal': True,
                'renewal_days': 30,
                'dns_provider': 'manual',
                'dns_credentials': {}
            }
        else:
            settings.pop('_id', None)
            settings.pop('organization_id', None)
        
        return settings
        
    except Exception as e:
        logger.error(f"Error getting ACME settings: {e}")
        raise

def update_acme_settings(data, user):
    """Update ACME protocol settings."""
    try:
        db = get_db()
        org_id = user.get('organization_id')
        
        data['organization_id'] = org_id
        data['updated_at'] = datetime.now()
        data['updated_by'] = user.get('email')
        
        db.acme_settings.replace_one(
            {'organization_id': org_id},
            data,
            upsert=True
        )
        
        logger.info(f"ACME settings updated for org {org_id}")
        
    except Exception as e:
        logger.error(f"Error updating ACME settings: {e}")
        raise

def get_acme_certificates(user):
    """Get list of ACME-managed certificates."""
    try:
        db = get_db()
        org_query = {}
        
        if user.get('role') != 'super_admin':
            org_query = {'organization_id': user.get('organization_id')}
        
        # Get devices with ACME certificates
        devices = db.devices.find({
            **org_query,
            'certificate_info.issuer': {'$regex': 'Let\'s Encrypt', '$options': 'i'}
        })
        
        certificates = []
        for device in devices:
            cert_info = device.get('certificate_info', {})
            certificates.append({
                'id': str(device['_id']),
                'device_id': device.get('device_id'),
                'device_name': device.get('name'),
                'domain': cert_info.get('subject', '').split('CN=')[1].split(',')[0] if 'CN=' in cert_info.get('subject', '') else '',
                'status': device.get('certificate_status', 'unknown'),
                'issued_at': cert_info.get('issued_at'),
                'expires_at': cert_info.get('expires_at'),
                'auto_renewal': True,
                'last_renewal': device.get('last_certificate_renewal')
            })
        
        return certificates
        
    except Exception as e:
        logger.error(f"Error getting ACME certificates: {e}")
        raise

def renew_acme_certificate(certificate_id, user):
    """Manually trigger ACME certificate renewal."""
    try:
        db = get_db()
        
        # Find device
        device = db.devices.find_one({'_id': ObjectId(certificate_id)})
        
        if not device:
            return {'error': 'Certificate not found'}
        
        # Check organization access
        if (user.get('role') != 'super_admin' and 
            device.get('organization_id') != user.get('organization_id')):
            return {'error': 'Access denied'}
        
        # Log renewal request with complete schema
        db.certificate_renewal_history.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device.get('device_id'),
            'device_name': device.get('name'),
            'action': 'renewal_initiated',
            'method': 'acme',
            'provisioning_method': 'sw_csr',
            'renewal_date': datetime.now(),
            'timestamp': datetime.now(),
            'initiated_at': datetime.now(),
            'initiated_by': user.get('email'),
            'trigger': 'manual_acme',
            'old_serial': device.get('certificate_serial'),
            'algorithm': _normalize_algorithm(device.get('certificate_algorithm')),
            'validity_days': 365,
            'issued_by': 'TESAIoT Vault CA',
            'status': 'pending',
            'details': 'ACME renewal initiated'
        })
        
        # In production, this would trigger actual ACME renewal process
        
        return {
            'message': 'ACME renewal initiated',
            'device_id': device.get('device_id'),
            'status': 'pending'
        }
        
    except Exception as e:
        logger.error(f"Error renewing ACME certificate: {e}")
        raise
# [MODULARIZE:END] - ACMEIntegrationService


# Certificate service is a module with functions, not a class
# No service instance needed as functions are imported directly

# [MODULARIZE:START] - CSRValidationService# Description: Certificate Signing Request validation and processing
# Dependencies: cryptography, pymongo
# Estimated Size: 250 lines
# Priority: HIGH
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.VALIDATION,
    user_message="CSR validation failed. Please check the format and try again.",
    return_on_error={'isValid': False, 'message': 'CSR validation error', 'error': 'VALIDATION_ERROR'}
)
def validate_external_csr(csr_content, user):
    """
    Validate an external Certificate Signing Request (CSR).
    
    Args:
        csr_content: CSR in PEM format (string)
        user: Current user for audit logging
        
    Returns:
        dict: Validation result with CSR details
    """
    try:
        # Input validation
        if not csr_content:
            return {
                'isValid': False,
                'message': 'CSR content is required',
                'error': 'MISSING_CSR'
            }
        
        # Size limit (10KB)
        if len(csr_content) > 10240:
            return {
                'isValid': False,
                'message': 'CSR content exceeds maximum size of 10KB',
                'error': 'CONTENT_TOO_LARGE'
            }
        
        # Clean CSR content
        csr_pem = csr_content.strip()
        
        # Check PEM format
        if not csr_pem.startswith('-----BEGIN CERTIFICATE REQUEST-----'):
            # Try to add PEM headers if missing
            if csr_pem.replace('\n', '').replace(' ', '').isalnum():
                csr_pem = f"-----BEGIN CERTIFICATE REQUEST-----\n{csr_pem}\n-----END CERTIFICATE REQUEST-----"
            else:
                return {
                    'isValid': False,
                    'message': 'Invalid CSR format. Expected PEM format.',
                    'error': 'FORMAT_ERROR'
                }
        
        # Parse CSR
        try:
            csr = x509.load_pem_x509_csr(csr_pem.encode(), default_backend())
        except Exception as e:
            logger.error(f"CSR parsing error: {e}")
            return {
                'isValid': False,
                'message': 'Failed to parse CSR. Please check the format.',
                'error': 'FORMAT_ERROR'
            }
        
        # Verify CSR signature
        if not csr.is_signature_valid:
            return {
                'isValid': False,
                'message': 'CSR signature verification failed',
                'error': 'INVALID_SIGNATURE'
            }
        
        # Extract public key info
        public_key = csr.public_key()
        key_info = {}
        
        if isinstance(public_key, rsa.RSAPublicKey):
            key_size = public_key.key_size
            key_info = {
                'keyAlgorithm': 'RSA',
                'keySize': key_size
            }
            
            # Validate RSA key size (minimum 2048 bits)
            if key_size < 2048:
                return {
                    'isValid': False,
                    'message': f'RSA key size {key_size} is below minimum requirement of 2048 bits.',
                    'error': 'INVALID_KEY_SIZE'
                }
                
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            curve = public_key.curve
            curve_name = curve.name
            
            # Map curve to key size
            curve_sizes = {
                'secp256r1': 256,  # P-256
                'secp384r1': 384,  # P-384
                'secp521r1': 521   # P-521
            }
            
            if curve_name not in curve_sizes:
                return {
                    'isValid': False,
                    'message': f'Unsupported ECC curve: {curve_name}',
                    'error': 'UNSUPPORTED_ALGORITHM'
                }
            
            key_info = {
                'keyAlgorithm': 'ECC',
                'keySize': curve_sizes[curve_name],
                'curve': curve_name
            }
        else:
            return {
                'isValid': False,
                'message': 'Unsupported key algorithm',
                'error': 'UNSUPPORTED_ALGORITHM'
            }
        
        # Extract subject information
        subject_data = {}
        for attribute in csr.subject:
            oid = attribute.oid
            value = sanitize_string(attribute.value)
            
            if oid == NameOID.COMMON_NAME:
                subject_data['CN'] = value
            elif oid == NameOID.ORGANIZATION_NAME:
                subject_data['O'] = value
            elif oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                subject_data['OU'] = value
            elif oid == NameOID.COUNTRY_NAME:
                subject_data['C'] = value
            elif oid == NameOID.STATE_OR_PROVINCE_NAME:
                subject_data['ST'] = value
            elif oid == NameOID.LOCALITY_NAME:
                subject_data['L'] = value
        
        # Require Common Name
        if 'CN' not in subject_data:
            return {
                'isValid': False,
                'message': 'Common Name (CN) is required in CSR subject',
                'error': 'MISSING_REQUIRED_FIELD'
            }
        
        # Extract signature algorithm
        signature_algo = csr.signature_algorithm_oid._name
        
        # Validate signature algorithm
        allowed_sig_algos = [
            'sha256WithRSAEncryption',
            'sha384WithRSAEncryption', 
            'sha512WithRSAEncryption',
            'ecdsa-with-SHA256',
            'ecdsa-with-SHA384',
            'ecdsa-with-SHA512'
        ]
        
        if signature_algo not in allowed_sig_algos:
            return {
                'isValid': False,
                'message': f'Unsupported signature algorithm: {signature_algo}',
                'error': 'UNSUPPORTED_ALGORITHM'
            }
        
        # Extract extensions
        extensions_data = {}
        try:
            for ext in csr.extensions:
                if ext.oid == ExtensionOID.SUBJECT_ALTERNATIVE_NAME:
                    san_values = []
                    for san in ext.value:
                        if isinstance(san, x509.DNSName):
                            san_values.append(san.value)
                        elif isinstance(san, x509.IPAddress):
                            san_values.append(str(san.value))
                    extensions_data['subjectAltName'] = san_values
        except Exception as e:
            logger.debug(f"Error extracting extensions: {e}")
        
        # Prepare response
        response = {
            'isValid': True,
            'message': 'CSR validated successfully',
            'details': {
                'subject': subject_data,
                'keyAlgorithm': key_info['keyAlgorithm'],
                'keySize': key_info['keySize'],
                'signatureAlgorithm': signature_algo,
                'extensions': extensions_data
            }
        }
        
        if 'curve' in key_info:
            response['details']['curve'] = key_info['curve']
        
        # Audit log successful validation
        audit_log(
            user=user,
            action=AuditAction.CERTIFICATE_CSR_VALIDATED,
            resource_type='certificate',
            resource_id=subject_data.get('CN', 'unknown'),
            details={
                'key_algorithm': key_info['keyAlgorithm'],
                'key_size': key_info['keySize'],
                'subject': subject_data
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"CSR validation error: {e}")
        return {
            'isValid': False,
            'message': 'An error occurred during CSR validation',
            'error': 'VALIDATION_ERROR'
        }


def determine_pki_role_for_csr(device_type, key_algorithm, key_size, curve=None):
    """
    Determine the appropriate Vault PKI role based on device and CSR characteristics.
    
    Args:
        device_type: Type of device (sensor, gateway, medical, industrial, edge)
        key_algorithm: RSA or ECC
        key_size: Key size in bits
        
    Returns:
        str: PKI role name
    """
    # Special device types with specific roles
    special_types = {
        'medical': 'iot-medical-device',      # 30-day certificates
        'industrial': 'iot-industrial-sensor', # 7-day certificates  
        'edge': 'iot-edge-ai'                 # ML-capable edge devices
    }
    
    if device_type in special_types:
        return special_types[device_type]
    
    # Gateway devices
    if device_type == 'gateway':
        if key_algorithm == 'RSA':
            return 'iot-gateway-rsa'
        else:
            return 'iot-gateway-ecc'
    
    # Standard devices based on key type and size
    if key_algorithm == 'RSA':
        if key_size >= 4096:
            return 'iot-device-rsa-4096'
        else:
            return 'iot-device-rsa'
    else:  # ECC
        # Prefer explicit curve match to avoid library naming differences
        curve_l = (curve or '').lower() if curve else ''
        if key_size >= 384 or curve_l in ('secp384r1', 'prime384v1', 'p-384', 'nistp384'):
            return 'iot-device-ecc-p384'
        elif device_type == 'sensor':
            return 'iot-sensor-ecc'
        else:
            return 'iot-device-ecc'


@vault_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Failed to sign certificate request. Please try again.",
    return_on_error=None
)
def sign_device_csr(device_id, csr_content, validity_days, user, revoke_old=False, alt_names=None):
    """
    Sign a Certificate Signing Request (CSR) for a device using Vault PKI.
    
    This function implements the complete CSR signing workflow:
    1. Validates the CSR
    2. Verifies device access
    3. Signs CSR with appropriate PKI role
    4. Stores certificate in database
    5. Records audit trail
    
    Args:
        device_id: Device identifier
        csr_content: CSR in PEM format
        validity_days: Certificate validity period (1-1095 days)
        user: Current user for authorization
        
    Returns:
        dict: Result with certificate info and download URLs
    """
    try:
        # Step 1: Validate the CSR
        validation_result = validate_external_csr(csr_content, user)
        if not validation_result['isValid']:
            return {
                'error': validation_result['message'],
                'error_code': validation_result.get('error', 'VALIDATION_ERROR')
            }
        
        csr_details = validation_result['details']
        
        # Step 2: Validate device ID
        if not validate_device_id(device_id):
            return {'error': 'Invalid device ID format'}
        
        # Step 3: Get database connection
        db = get_db()
        if db is None:
            raise ConnectionFailure("Database connection not available")
        
        # Step 4: Find device with organization check
        device_query = {}
        if ObjectId.is_valid(device_id) and len(device_id) == 24:
            device_query['_id'] = ObjectId(device_id)
        else:
            device_query['device_id'] = device_id
        
        # Apply organization filter for non-platform admin users
        if user and not RBAC.is_platform_admin(user):
            device_query['organization_id'] = user.get('organization_id')
        
        device = db.devices.find_one(device_query)
        
        if not device:
            audit_security_violation(
                user=user,
                violation_type="CSR_SIGNING_ACCESS_DENIED",
                target_resource=f"device/{device_id}",
                details={
                    'device_id': device_id,
                    'reason': 'Device not found or access denied'
                }
            )
            return {'error': 'Device not found or access denied'}
        
        # Step 5: Certificate presence check (allow renew/replace via CSR)
        # Previous behavior blocked CSR signing when a valid certificate already existed.
        # For enterprise lifecycle, we allow a CSR-based renewal/replace and record it.
        has_cert = bool(device.get('certificate_info', {}).get('certificate'))
        cert_status = device.get('certificate_status', 'unknown')
        old_cert_serial = device.get('certificate_serial') if has_cert else None
        if has_cert and cert_status not in ('revoked', 'expired'):
            try:
                _prov, _issued_by = _detect_provisioning_method(device)
                db.certificate_renewal_history.insert_one({
                    'organization_id': device.get('organization_id'),
                    'device_id': device.get('device_id'),
                    'device_name': device.get('name'),
                    'action': 'renewal_initiated',
                    'method': 'csr',
                    'provisioning_method': _prov,
                    'renewal_date': datetime.now(),
                    'timestamp': datetime.now(),
                    'old_certificate_serial': old_cert_serial,
                    'old_serial': old_cert_serial,
                    'requested_by': (user or {}).get('email'),
                    'initiated_at': datetime.now(),
                    'algorithm': _normalize_algorithm(device.get('certificate_algorithm')),
                    'validity_days': 365,
                    'issued_by': _issued_by,
                    'status': 'initiated',
                    'note': 'CSR renew/replace initiated: existing certificate will be superseded'
                })
            except Exception:
                # Non-fatal: continue even if history logging fails
                pass
            # Do not block; proceed to sign a new certificate which will overwrite summary fields
        
        # Step 6: Validate validity days
        validity_days = int(validity_days) if validity_days else 365
        if validity_days < 1 or validity_days > 1095:  # Max 3 years
            return {'error': 'Validity days must be between 1 and 1095'}
        
        # Step 7: Calculate CSR hash for tracking
        csr_hash = hashlib.sha256(csr_content.encode()).hexdigest()
        
        # Step 8: Determine PKI role based on device type and key info
        device_type = device.get('type', 'sensor')
        pki_role = determine_pki_role_for_csr(
            device_type,
            csr_details['keyAlgorithm'],
            csr_details['keySize'],
            csr_details.get('curve')
        )
        # Prefer unified device role where available
        preferred_device_role = 'tesa-device'
        
        # If CSR subject CN is not a hostname (e.g., looks like an email),
        # prefer a permissive CSR-signing role if available.
        import os
        subject_cn = (csr_details.get('subject') or {}).get('CN', '')
        pki_role_preferred = None
        if subject_cn and '@' in subject_cn:
            # Prefer environment-configured CSR role if provided
            pki_role_preferred = os.getenv('VAULT_ROLE_CSR_SIGNING', 'csr-signing')
        
        # Step 9: Get Vault client
        vault = get_vault()
        if vault is None:
            raise VaultError("Vault connection not available")
        
        # Optionally ensure a permissive CSR role exists when CN looks like email
        try:
            if pki_role_preferred:
                # Configure or update the CSR role to allow any CN without hostname enforcement
                role_path = f'pki-int/roles/{pki_role_preferred}'
                logger.info(f"Auto-configuring CSR role at {role_path} for email CN support")
                # ============================================================
                # SECURITY INVARIANT - why allow_any_name=True is acceptable:
                # Device IDs are UUIDs, which cannot be expressed via Vault's
                # allowed_domains/allow_subdomains hostname patterns, so
                # allow_any_name must stay True and enforce_hostnames False
                # for issuance to work at all. The compensating control is the
                # platform-side CN override: use_csr_common_name=False and
                # use_csr_sans=False mean the CN/SANs in the client-supplied
                # CSR are IGNORED, and the signing call below always passes
                # common_name=device_id (server-derived, never client input)
                # with exclude_cn_from_sans. A client therefore cannot mint a
                # certificate for an arbitrary identity through this role.
                # DO NOT set use_csr_common_name/use_csr_sans to True here
                # without replacing allow_any_name with a strict allowlist.
                # Additionally: client-auth only (server_flag=False) and no IP
                # SANs, so the cert can't be repurposed as a server cert.
                # ============================================================
                vault.write(
                    role_path,
                    allow_any_name=True,
                    enforce_hostnames=False,
                    allow_ip_sans=False,
                    key_type='any',
                    key_bits=0,
                    server_flag=False,
                    client_flag=True,
                    use_csr_sans=False,
                    use_csr_common_name=False,
                    max_ttl=f"{max(int(validity_days or 365),1)*24}h"
                )
        except Exception as e:
            logger.warning(f"Unable to auto-configure CSR role '{pki_role_preferred}': {e}")
        
        # Step 10: Sign CSR with Vault (override CN to device_id; SAN optional)
        try:
            # Clean CSR content
            csr_pem = csr_content.strip()
            
            # Sign the CSR using intermediate PKI mount (try both hyphen/underscore)
            def _vault_sign(role_name: str):
                last_err = None
                for path in (f'pki-int/sign/{role_name}', f'pki_int/sign/{role_name}'):
                    try:
                        params = {
                            'csr': csr_pem,
                            'ttl': f"{validity_days * 24}h",
                            'format': 'pem',
                            'common_name': device_id,
                            'exclude_cn_from_sans': True,
                        }
                        # DEBUG: Log parameters sent to Vault
                        logger.warning(f"[CSR SIGN DEBUG] Vault sign params: role={role_name}, common_name={device_id}, path={path}")
                        try:
                            # ================================================================
                            # SAN (Subject Alternative Name) Handling for Device Certificates
                            # ================================================================
                            # FIX (2026-01-31): Remove automatic *.tesaiot.dev SAN for device certs
                            #
                            # Problem: Adding SAN increases certificate size by ~50-100 bytes
                            # Device certificate with SAN: ~690 bytes
                            # Device certificate without SAN: ~580-620 bytes
                            # OPTIGA Trust M MAX_PAYLOAD_SIZE: 640 bytes
                            # → Certificates > 640 bytes cause Error 0x8007 (payload too large)
                            #
                            # Solution: Only add SAN if explicitly requested via alt_names parameter
                            # - Device certificates (CSR workflow): No SAN needed, CN = device_id
                            # - Server certificates: Pass alt_names explicitly if SAN required
                            #
                            # Impact: RPi/Linux and MCU clients unaffected - they use CN for mTLS
                            # ================================================================
                            if alt_names and isinstance(alt_names, (list, tuple)):
                                _alt = []
                                for v in alt_names:
                                    if not isinstance(v, str):
                                        continue
                                    sv = v.strip()
                                    # Allow optional leading '*' for wildcard plus alnum, dash, dot, colon
                                    import re
                                    if re.fullmatch(r'\*?[A-Za-z0-9:\.-]{1,253}', sv):
                                        _alt.append(sv)
                                # Normalize to DNS-only entries without the 'DNS:' prefix
                                dns_only = [s.replace('DNS:', '') for s in _alt]
                                # Deduplicate while preserving order
                                dedup = []
                                for name in dns_only:
                                    if name and (name not in dedup):
                                        dedup.append(name)
                                if dedup:
                                    params['alt_names'] = ','.join(dedup)
                            # If no alt_names provided, don't add any SAN (device cert default)
                        except Exception:
                            pass
                        return vault.write(path, **params)
                    except Exception as e:
                        last_err = e
                        continue
                if last_err:
                    raise VaultError(str(last_err))
            
            # For CSR-based signing, prioritize 'csr-signing' role which has use_csr_common_name=False
            # This ensures CN is always overridden with device_id regardless of CSR content
            primary_role = pki_role_preferred or pki_role
            role_candidates = []
            for role_name in (
                'csr-signing',         # CSR workflow: use csr-signing role first (overrides CN)
                primary_role,
                preferred_device_role,
                pki_role,
                'iot-device-ecc',
            ):
                if role_name and role_name not in role_candidates:
                    role_candidates.append(role_name)

            sign_response = None
            last_error = None
            for role_name in role_candidates:
                try:
                    sign_response = _vault_sign(role_name)
                    if sign_response and 'data' in sign_response:
                        pki_role = role_name  # Record role actually used
                        break
                except VaultError as err:
                    last_error = err
                    logger.warning(
                        f"Vault CSR signing attempt failed for role '{role_name}': {err}"
                    )
                    continue

            if not sign_response or 'data' not in sign_response:
                if last_error:
                    raise last_error
                raise VaultError("Invalid response from Vault PKI")

            cert_data = sign_response['data']
            certificate = cert_data.get('certificate')
            ca_chain = cert_data.get('ca_chain', [])
            serial_number = cert_data.get('serial_number')

            if not certificate:
                raise VaultError("No certificate returned from Vault")
            
        except VaultError as e:
            logger.error(f"Vault CSR signing error: {e}")
            raise
        
        # Step 11: Parse the signed certificate for metadata
        try:
            cert = x509.load_pem_x509_certificate(certificate.encode(), default_backend())
            
            _raw_algo = f"{csr_details['keyAlgorithm']}-{csr_details['keySize']}"
            _norm_algo = _normalize_algorithm(_raw_algo)
            _prov, _issued_by = _detect_provisioning_method(device)

            cert_info = {
                'certificate': certificate,
                'ca_chain': '\n'.join(ca_chain) if ca_chain else '',
                'serial_number': serial_number,
                'serialNumber': serial_number,  # UI expects this field
                'serial': serial_number,  # Also for backward compatibility
                'issued_at': datetime.now(),
                'expires_at': cert.not_valid_after,
                'validFrom': datetime.now().isoformat(),  # UI expects this field
                'validTo': cert.not_valid_after.isoformat(),  # UI expects this field
                'issuer': cert.issuer.rfc4514_string(),
                'subject': cert.subject.rfc4514_string(),
                'key_algorithm': _norm_algo,
                'algorithm': _norm_algo,  # UI expects this field name
                'status': 'valid',
                'generation_method': 'external_csr',
                'issued_via': _prov,
                'validity_days': validity_days,
                'csr_info': {
                    'csr_hash': f"SHA256:{csr_hash}",
                    'submitted_at': datetime.now(),
                    'submitted_by': user.get('email'),
                    'key_type': csr_details['keyAlgorithm'],
                    'key_size': csr_details['keySize'],
                    'subject_fields': csr_details['subject'],
                    'validated_at': datetime.now()
                }
            }
            
            # No private key for CSR-based certificates
            cert_info['private_key'] = None
            
        except Exception as e:
            logger.error(f"Certificate parsing error: {e}")
            return {'error': 'Failed to parse signed certificate'}
        
        # Step 12: Extract Trust M UID from CSR if present
        # Trust M UIDs are typically long hex strings (e.g., "CD1633940100...")
        trustm_uid_update = {}
        if subject_cn and len(subject_cn) >= 16 and all(c in '0123456789ABCDEFabcdef' for c in subject_cn):
            # This looks like a Trust M UID (hex string)
            trustm_uid_update['trustm_uid'] = subject_cn
            logger.info(f"Detected Trust M UID in CSR subject CN: {subject_cn}")

        # Step 13: Update device document
        update_result = db.devices.update_one(
            {'_id': device['_id']},
            {
                '$set': {
                    # Full certificate info blob (includes issuer/subject and metadata)
                    'certificate_info': cert_info,
                    'certificate_serial': serial_number,
                    # Denormalized summary fields for UI compatibility
                    'certificate_status': 'valid',
                    'certificate_issued_at': cert_info['issued_at'],
                    'certificate_expires_at': cert_info['expires_at'],
                    'certificate_algorithm': _normalize_algorithm(cert_info.get('key_algorithm') or cert_info.get('algorithm')),
                    'certificate_generation_method': 'upload-csr',
                    'generation_method': 'external_csr',
                    'csr_provided': True,
                    # UI expects a concise certificate object
                    'certificate': {
                        'status': 'valid',
                        'serialNumber': serial_number,
                        'serial_number': serial_number,
                        'algorithm': _normalize_algorithm(cert_info.get('key_algorithm') or cert_info.get('algorithm')),
                        # Provide both camelCase and snake_case for UI flexibility
                        'issuedAt': cert_info['issued_at'],
                        'issued_at': cert_info['issued_at'],
                        'expiresAt': cert_info['expires_at'],
                        'expires_at': cert_info['expires_at'],
                        'validFrom': cert_info.get('validFrom') or datetime.now().isoformat(),
                        'validTo': cert_info.get('validTo') or cert_info['expires_at'].isoformat() if hasattr(cert_info['expires_at'], 'isoformat') else cert_info['expires_at']
                    },
                    'last_updated': datetime.now(),
                    **trustm_uid_update  # Add trustm_uid if detected
                }
            }
        )
        
        if update_result.modified_count != 1:
            logger.error(f"Failed to update device {device_id} with certificate")
            return {'error': 'Failed to store certificate'}
        
        # Step 13: Record certificate issuance
        db.certificate_issuance_log.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device.get('device_id'),
            'device_name': device.get('name'),
            'serial_number': serial_number,
            'issued_at': cert_info['issued_at'],
            'expires_at': cert_info['expires_at'],
            'issued_by': user.get('email'),
            'issuance_method': 'external_csr',
            'pki_role_used': pki_role,
            'key_algorithm': cert_info['key_algorithm'],
            'validity_days': validity_days,
            'csr_hash': csr_hash
        })

        # Step 13b: Record in certificate_renewal_history for Reports UI
        # This collection is used by /api/v1/certificates/rotation-history endpoint
        try:
            action = 'renewed' if old_cert_serial else 'issued'

            # Detect if device has OPTIGA Trust M (HSM) for provisioning_method badge
            # Trust M devices have factory_uid or metadata.optiga_trust_m
            has_hsm = bool(
                device.get('factory_uid') or
                (device.get('metadata') or {}).get('optiga_trust_m') or
                (device.get('metadata') or {}).get('trust_m_uid')
            )
            # Provisioning method values:
            # - sw_csr: 📜 CSR-Signed (Software PKI, no HSM)
            # - hsm_csr: 🔐 CSR-Signed (HSM) - CSR with OPTIGA Trust M key
            # - hsm_protected_update: 🛡️ Protected Update (HSM) - set by Protected Update worker
            provisioning_method = 'hsm_csr' if has_hsm else 'sw_csr'

            # Issued By naming convention:
            # - SW-CSR: "TESAIoT Vault CA" (software PKI only)
            # - HSM-CSR: "Trust M + Vault CA" (OPTIGA Trust M + TESAIoT Vault CA)
            issued_by_label = 'Trust M + Vault CA' if provisioning_method == 'hsm_csr' else 'TESAIoT Vault CA'

            db.certificate_renewal_history.insert_one({
                'device_id': device.get('device_id'),
                'device_name': device.get('name'),
                'organization_id': device.get('organization_id'),
                'action': action,
                'method': 'csr',
                'provisioning_method': provisioning_method,  # NEW: SW vs HSM badge
                'renewal_date': datetime.now(),
                'timestamp': datetime.now(),
                'serial_number': serial_number,
                'old_serial': old_cert_serial,
                'new_serial': serial_number,
                'algorithm': _normalize_algorithm(cert_info.get('key_algorithm') or cert_info.get('algorithm')),
                'validity_days': validity_days,
                'issued_by': issued_by_label,
                'reason': 'CSR-based certificate signing',
                'pki_role': pki_role
            })
            logger.info(f"Recorded certificate {action} history for device {device.get('device_id')} (provisioning: {provisioning_method})")
        except Exception as hist_err:
            # Non-fatal: continue even if history logging fails
            logger.warning(f"Failed to record certificate history: {hist_err}")

        # Optional: Auto-revoke previous certificate (policy or request-driven)
        from ..services.device_service import (
            _revoke_serial_in_vault,
            CertificateRevocationError,
        )
        try:
            should_revoke = False
            # Honor explicit request flag if controller passed it via kwargs
            if 'revoke_old' in locals() and bool(revoke_old):
                should_revoke = True
            else:
                pol = None
                try:
                    pol = db.org_policies.find_one({'organization_id': device.get('organization_id')}) if db is not None else None
                except Exception:
                    pol = None
                if pol and isinstance(pol.get('certificate'), dict) and pol['certificate'].get('auto_revoke_on_renew'):
                    should_revoke = True
                # Environment fallback
                import os as _os
                if not should_revoke and _os.getenv('AUTO_REVOKE_ON_RENEW', '').lower() in ('1', 'true', 'yes'):
                    should_revoke = True

            if should_revoke and old_cert_serial:
                # Fail CLOSED: revoke the superseded serial directly in Vault's
                # intermediate PKI (pki-int/revoke) so it lands on the CRL the
                # broker enforces. Do NOT go through
                # PKIProvisioningService.revoke_device_certificate, which gates
                # the Vault revoke on issued_via=='vault_pki' and could leave the
                # old serial connectable. If Vault revocation cannot be enforced,
                # abort the renewal so a superseded cert can never remain valid.
                try:
                    _revoke_serial_in_vault(old_cert_serial)
                    logger.info(
                        f"Auto-revoked superseded certificate serial {old_cert_serial} "
                        f"in Vault PKI after CSR renew for {device.get('device_id')}"
                    )
                except CertificateRevocationError:
                    # Propagate so the renewal fails CLOSED rather than leaving
                    # the old, still-valid certificate revocable only in MongoDB.
                    logger.error(
                        f"Auto-revoke after CSR renew FAILED to revoke superseded "
                        f"serial {old_cert_serial} in Vault PKI for "
                        f"{device.get('device_id')}; aborting renewal (fail-closed)"
                    )
                    raise
        except CertificateRevocationError:
            # Hard-fail the renewal: a superseded cert must not survive in Vault.
            raise
        
        # Step 14: Audit log
        audit_log(
            user=user,
            action=AuditAction.CERTIFICATE_CSR_SIGNED,
            resource_type='certificate',
            resource_id=device.get('device_id'),
            details={
                'serial_number': serial_number,
                'validity_days': validity_days,
                'pki_role': pki_role,
                'key_algorithm': cert_info['key_algorithm'],
                'device_type': device_type
            }
        )
        
        # Step 15: Prepare response
        return {
            'message': 'Certificate signed successfully',
            'certificate': {
                'serial_number': serial_number,
                'serialNumber': serial_number,  # UI expects this field
                'serial': serial_number,  # Also for backward compatibility
                'status': 'valid',
                'key_algorithm': cert_info['key_algorithm'],
                'algorithm': cert_info['key_algorithm'],  # UI expects this field name
                'device_type': device_type,
                'issued_at': cert_info['issued_at'].isoformat(),
                'expires_at': cert_info['expires_at'].isoformat(),
                'validFrom': cert_info['issued_at'].isoformat(),  # UI expects this field
                'validTo': cert_info['expires_at'].isoformat(),  # UI expects this field
                'issuer': cert_info['issuer'],
                'subject': cert_info['subject']
            },
            'download_urls': {
                'ca_chain': f"/api/v1/certificates/devices/{device.get('device_id')}/certificate/download/ca-chain",
                'device_cert': f"/api/v1/certificates/devices/{device.get('device_id')}/certificate/download/device-cert",
                'bundle': f"/api/v1/certificates/devices/{device.get('device_id')}/certificate/download/bundle"
            }
        }
        
    except Exception as e:
        logger.error(f"CSR signing error for device {device_id}: {e}")
        return {'error': 'An error occurred while signing the CSR'}
# [MODULARIZE:END] - CSRValidationService


# ============================================================================
# Internal Service CSR Signing (Platform-Level Access)
# ============================================================================

def sign_device_csr_internal(device_id, csr_content, validity_days, requesting_service, correlation_id=None):
    """
    Sign a CSR for any device (internal platform service use only).

    This function is designed for internal platform services like MQTT Bridge
    that need to sign CSRs for devices across ALL organizations.

    Key differences from sign_device_csr():
    - NO organization filter (platform-level access)
    - NO user parameter (service-to-service call)
    - Audit trail records requesting_service instead of user

    Args:
        device_id: Device identifier
        csr_content: CSR in PEM format
        validity_days: Certificate validity period (1-1095 days)
        requesting_service: Name of the internal service requesting the signing
        correlation_id: Optional tracking ID for request correlation

    Returns:
        dict: Result with certificate PEM, serial number, and expiry
    """
    try:
        # Step 1: Validate the CSR (no user context needed)
        validation_result = validate_external_csr(csr_content, user=None)
        if not validation_result['isValid']:
            return {
                'error': validation_result['message'],
                'error_code': validation_result.get('error', 'VALIDATION_ERROR')
            }

        csr_details = validation_result['details']

        # Step 2: Validate device ID
        if not validate_device_id(device_id):
            return {'error': 'Invalid device ID format'}

        # Step 3: Get database connection
        db = get_db()
        if db is None:
            raise ConnectionFailure("Database connection not available")

        # Step 4: Find device WITHOUT organization filter (platform-level access)
        device_query = {}
        if ObjectId.is_valid(device_id) and len(device_id) == 24:
            device_query['_id'] = ObjectId(device_id)
        else:
            device_query['device_id'] = device_id

        # NO organization filter - internal services have platform-level access
        device = db.devices.find_one(device_query)

        if not device:
            logger.warning(f"Internal CSR signing: Device {device_id} not found (service: {requesting_service})")
            return {'error': 'Device not found'}

        # Step 5: Log the internal service request
        logger.info(
            f"Internal CSR signing for device {device_id} "
            f"(org: {device.get('organization_id')}, service: {requesting_service}, "
            f"correlation_id: {correlation_id})"
        )

        # Step 6: Certificate presence check
        has_cert = bool(device.get('certificate_info', {}).get('certificate'))
        cert_status = device.get('certificate_status', 'unknown')
        old_cert_serial = device.get('certificate_serial') if has_cert else None
        if has_cert and cert_status not in ('revoked', 'expired'):
            try:
                db.certificate_renewal_history.insert_one({
                    'organization_id': device.get('organization_id'),
                    'device_id': device.get('device_id'),
                    'device_name': device.get('name'),
                    'action': 'renewal_initiated',
                    'method': 'csr',
                    'provisioning_method': 'hsm_csr',
                    'renewal_date': datetime.now(),
                    'timestamp': datetime.now(),
                    'old_certificate_serial': old_cert_serial,
                    'old_serial': old_cert_serial,
                    'requested_by': f"service:{requesting_service}",
                    'initiated_at': datetime.now(),
                    'correlation_id': correlation_id,
                    'algorithm': _normalize_algorithm(device.get('certificate_algorithm')),
                    'validity_days': 365,
                    'issued_by': 'Trust M + Vault CA',
                    'status': 'initiated',
                    'note': 'Internal service CSR renew: existing certificate will be superseded'
                })
            except Exception:
                pass

        # Step 7: Validate validity days
        validity_days = int(validity_days) if validity_days else 365
        if validity_days < 1 or validity_days > 1095:
            return {'error': 'Validity days must be between 1 and 1095'}

        # Step 8: Calculate CSR hash
        csr_hash = hashlib.sha256(csr_content.encode()).hexdigest()

        # Step 9: Determine PKI role
        device_type = device.get('type', 'sensor')
        pki_role = determine_pki_role_for_csr(
            device_type,
            csr_details['keyAlgorithm'],
            csr_details['keySize'],
            csr_details.get('curve')
        )

        # Step 10: Get Vault client
        vault = get_vault()
        if vault is None:
            raise VaultError("Vault connection not available")

        # Step 11: Configure CSR role if needed
        subject_cn = (csr_details.get('subject') or {}).get('CN', '')
        pki_role_preferred = None
        if subject_cn and ('@' in subject_cn or len(subject_cn) >= 16):
            pki_role_preferred = os.getenv('VAULT_ROLE_CSR_SIGNING', 'csr-signing')

        if pki_role_preferred:
            try:
                role_path = f'pki-int/roles/{pki_role_preferred}'
                vault.write(
                    role_path,
                    allow_any_name=True,
                    enforce_hostnames=False,
                    key_type='any',
                    key_bits=0,
                    server_flag=False,
                    client_flag=True,
                    use_csr_sans=False,
                    use_csr_common_name=False,
                    max_ttl=f"{max(int(validity_days or 365),1)*24}h"
                )
            except Exception as e:
                logger.warning(f"Unable to auto-configure CSR role: {e}")

        # Step 12: Sign CSR with Vault
        csr_pem = csr_content.strip()

        def _vault_sign_internal(role_name: str):
            last_err = None
            for path in (f'pki-int/sign/{role_name}', f'pki_int/sign/{role_name}'):
                try:
                    params = {
                        'csr': csr_pem,
                        'ttl': f"{validity_days * 24}h",
                        'format': 'pem',
                        'common_name': device_id,
                        'exclude_cn_from_sans': True,
                    }
                    return vault.write(path, **params)
                except Exception as e:
                    last_err = e
                    continue
            if last_err:
                raise VaultError(str(last_err))

        primary_role = pki_role_preferred or pki_role
        role_candidates = [r for r in (
            primary_role,
            'tesa-device',
            pki_role,
            'iot-device-ecc',
            'csr-signing',
        ) if r]
        # Remove duplicates while preserving order
        role_candidates = list(dict.fromkeys(role_candidates))

        sign_response = None
        last_error = None
        for role_name in role_candidates:
            try:
                sign_response = _vault_sign_internal(role_name)
                if sign_response and 'data' in sign_response:
                    pki_role = role_name
                    break
            except VaultError as err:
                last_error = err
                logger.warning(f"Internal CSR signing attempt failed for role '{role_name}': {err}")
                continue

        if not sign_response or 'data' not in sign_response:
            if last_error:
                raise last_error
            raise VaultError("Invalid response from Vault PKI")

        cert_data = sign_response['data']
        certificate = cert_data.get('certificate')
        ca_chain = cert_data.get('ca_chain', [])
        serial_number = cert_data.get('serial_number')

        if not certificate:
            raise VaultError("No certificate returned from Vault")

        # Step 13: Parse signed certificate
        cert = x509.load_pem_x509_certificate(certificate.encode(), default_backend())

        _raw_algo = f"{csr_details['keyAlgorithm']}-{csr_details['keySize']}"
        _norm_algo = _normalize_algorithm(_raw_algo)

        cert_info = {
            'certificate': certificate,
            'ca_chain': '\n'.join(ca_chain) if ca_chain else '',
            'serial_number': serial_number,
            'serialNumber': serial_number,
            'serial': serial_number,
            'issued_at': datetime.now(),
            'expires_at': cert.not_valid_after,
            'validFrom': datetime.now().isoformat(),
            'validTo': cert.not_valid_after.isoformat(),
            'issuer': cert.issuer.rfc4514_string(),
            'subject': cert.subject.rfc4514_string(),
            'key_algorithm': _norm_algo,
            'algorithm': _norm_algo,
            'status': 'valid',
            'generation_method': 'internal_service_csr',
            'issued_via': 'hsm_csr',
            'validity_days': validity_days,
            'csr_info': {
                'csr_hash': f"SHA256:{csr_hash}",
                'submitted_at': datetime.now(),
                'submitted_by': f"service:{requesting_service}",
                'key_type': csr_details['keyAlgorithm'],
                'key_size': csr_details['keySize'],
                'subject_fields': csr_details['subject'],
                'validated_at': datetime.now(),
                'correlation_id': correlation_id
            }
        }
        cert_info['private_key'] = None

        # Step 14: Extract Trust M UID if present
        trustm_uid_update = {}
        if subject_cn and len(subject_cn) >= 16 and all(c in '0123456789ABCDEFabcdef' for c in subject_cn):
            trustm_uid_update['trustm_uid'] = subject_cn
            logger.info(f"Internal CSR: Detected Trust M UID in subject CN: {subject_cn}")

        # Step 15: Update device document
        update_result = db.devices.update_one(
            {'_id': device['_id']},
            {
                '$set': {
                    'certificate_info': cert_info,
                    'certificate_serial': serial_number,
                    'certificate_status': 'valid',
                    'certificate_issued_at': cert_info['issued_at'],
                    'certificate_expires_at': cert_info['expires_at'],
                    'certificate_algorithm': _normalize_algorithm(cert_info.get('key_algorithm')),
                    'certificate_generation_method': 'internal-csr',
                    'generation_method': 'internal_service_csr',
                    'csr_provided': True,
                    'certificate': {
                        'status': 'valid',
                        'serialNumber': serial_number,
                        'serial_number': serial_number,
                        'algorithm': _normalize_algorithm(cert_info.get('key_algorithm')),
                        'issuedAt': cert_info['issued_at'],
                        'issued_at': cert_info['issued_at'],
                        'expiresAt': cert_info['expires_at'],
                        'expires_at': cert_info['expires_at'],
                        'validFrom': cert_info.get('validFrom'),
                        'validTo': cert_info.get('validTo')
                    },
                    'last_updated': datetime.now(),
                    **trustm_uid_update
                }
            }
        )

        if update_result.modified_count != 1:
            logger.error(f"Internal CSR: Failed to update device {device_id} with certificate")
            return {'error': 'Failed to store certificate'}

        # Step 16: Record certificate issuance
        db.certificate_issuance_log.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device.get('device_id'),
            'device_name': device.get('name'),
            'serial_number': serial_number,
            'issued_at': cert_info['issued_at'],
            'expires_at': cert_info['expires_at'],
            'issued_by': 'TESAIoT Vault CA',
            'issuance_method': 'internal_service_csr',
            'pki_role_used': pki_role,
            'key_algorithm': cert_info['key_algorithm'],
            'validity_days': validity_days,
            'csr_hash': csr_hash,
            'correlation_id': correlation_id
        })

        # Step 17: Record renewal history
        try:
            action = 'renewed' if old_cert_serial else 'issued'
            db.certificate_renewal_history.insert_one({
                'device_id': device.get('device_id'),
                'device_name': device.get('name'),
                'organization_id': device.get('organization_id'),
                'action': action,
                'method': '🔐 HSM-Secured',
                'provisioning_method': 'hsm_csr',  # Internal service uses HSM
                'renewal_date': datetime.now(),
                'timestamp': datetime.now(),
                'serial_number': serial_number,
                'old_serial': old_cert_serial,
                'new_serial': serial_number,
                'algorithm': _normalize_algorithm(cert_info.get('key_algorithm')),
                'validity_days': validity_days,
                'issued_by': 'Trust M + Vault CA',  # HSM-CSR: OPTIGA Trust M with TESAIoT Vault CA signing
                'reason': 'Internal service CSR signing',
                'pki_role': pki_role,
                'correlation_id': correlation_id
            })
        except Exception as hist_err:
            logger.warning(f"Failed to record certificate history: {hist_err}")

        # Step 18: Audit log for internal service
        try:
            audit_log(
                user={'email': f"service:{requesting_service}", 'role': 'internal_service'},
                action=AuditAction.CERTIFICATE_CSR_SIGNED,
                resource_type='certificate',
                resource_id=device.get('device_id'),
                details={
                    'serial_number': serial_number,
                    'validity_days': validity_days,
                    'pki_role': pki_role,
                    'key_algorithm': cert_info['key_algorithm'],
                    'device_type': device_type,
                    'requesting_service': requesting_service,
                    'correlation_id': correlation_id,
                    'method': 'internal_service_auth'
                }
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit log: {audit_err}")

        logger.info(
            f"Internal CSR signing successful: device={device_id}, "
            f"serial={serial_number}, service={requesting_service}"
        )

        # Step 19: Return certificate info
        return {
            'message': 'Certificate signed successfully (internal service)',
            'certificate': certificate,
            'serial_number': serial_number,
            'expires_at': cert_info['expires_at'].isoformat(),
            'issued_at': cert_info['issued_at'].isoformat(),
            'issuer': cert_info['issuer'],
            'subject': cert_info['subject'],
            'key_algorithm': cert_info['key_algorithm'],
            'pki_role': pki_role,
            'ca_chain': cert_info.get('ca_chain', '')
        }

    except VaultError as e:
        logger.error(f"Internal CSR signing Vault error for device {device_id}: {e}")
        return {'error': f'Vault error: {str(e)}'}
    except Exception as e:
        logger.exception(f"Internal CSR signing error for device {device_id}: {e}")
        return {'error': f'Internal error: {str(e)}'}
