# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Controller
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import logging
import json
import base64
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, g, Response
from bson import ObjectId
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..core.auth import require_auth, require_role
from ..core.database import get_db, get_vault
from ..core.rbac import Permission, require_permission
from ..services.audit_service import audit_log, AuditAction
from ..services.certificate_service import (
    get_device_certificate_info,
    issue_device_certificate,
    get_certificates_list,
    download_certificate_file,
    get_alert_settings,
    update_alert_settings,
    check_expiring_certificates,
    get_auto_renewal_settings,
    update_auto_renewal_settings,
    trigger_certificate_renewal,
    send_test_notification,
    get_audit_trail,
    export_audit_trail,
    perform_bulk_operation,
    get_certificate_analytics,
    get_acme_settings,
    update_acme_settings,
    get_acme_certificates,
    renew_acme_certificate,
    get_ca_chain_metadata
)
from ..services.notification_acl_service import notification_acl_service
from ..services.key_provisioning_service import (
    generate_bulk_keys,
    get_supported_algorithms,
    distribute_keys_to_devices,
    update_rotation_policy,
    get_key_lifecycle_status,
    get_key_generation_session,
    get_key_distribution_status
)
from ..services.key_escrow_service import key_escrow_service
from ..services.vault_key_service import vault_key_service
from ..utils.data_fixes import fix_certificate_data
from ..services.certificate_service import validate_external_csr, sign_device_csr, ValidationError

logger = logging.getLogger(__name__)


def _normalize_serial(serial):
    """Normalize certificate serial to colon-separated lowercase hex format.

    Converts various serial formats to consistent 'xx:xx:xx:...' format:
    - '0xb5f30d05815e9f21' -> 'b5:f3:0d:05:81:5e:9f:21'
    - 'b5f30d05815e9f21'   -> 'b5:f3:0d:05:81:5e:9f:21'
    - 'B5:F3:0D:05:81:5E:9F:21' -> 'b5:f3:0d:05:81:5e:9f:21'
    - Already formatted     -> returned as-is (lowercased)
    """
    if not serial or not isinstance(serial, str):
        return serial
    s = serial.strip().lower()
    # Already colon-separated
    if ':' in s:
        return s
    # Remove 0x prefix
    if s.startswith('0x'):
        s = s[2:]
    # If it's a pure hex string without colons, add colons every 2 chars
    if all(c in '0123456789abcdef' for c in s) and len(s) >= 4:
        if len(s) % 2:
            s = '0' + s
        return ':'.join(s[i:i+2] for i in range(0, len(s), 2))
    return serial


def encrypt_certificate_content(content, password, algorithm='aes-256-cbc', is_binary=False):
    """
    Encrypt certificate content using specified algorithm.
    
    Args:
        content: Content to encrypt (bytes or string)
        password: Password for encryption
        algorithm: Encryption algorithm (aes-256-cbc or aes-256-gcm)
        is_binary: Whether content is binary
        
    Returns:
        tuple: (encrypted_content, metadata)
    """
    try:
        # Convert content to bytes if necessary
        if not isinstance(content, bytes):
            content = content.encode('utf-8')
        
        # Generate salt for key derivation
        salt = os.urandom(16)
        
        # Derive key from password using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(password.encode('utf-8'))
        
        if algorithm == 'aes-256-cbc':
            # Generate IV for CBC mode
            iv = os.urandom(16)
            
            # Pad the content for CBC mode
            padder = padding.PKCS7(128).padder()
            padded_content = padder.update(content) + padder.finalize()
            
            # Encrypt using AES-256-CBC
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(padded_content) + encryptor.finalize()
            
            # Combine salt + iv + encrypted data
            encrypted_content = salt + iv + encrypted_data
            
            metadata = {
                'algorithm': 'aes-256-cbc',
                'key_derivation': 'pbkdf2-sha256',
                'iterations': 100000,
                'salt_length': 16,
                'iv_length': 16
            }
            
        elif algorithm == 'aes-256-gcm':
            # Generate nonce for GCM mode
            nonce = os.urandom(12)
            
            # Encrypt using AES-256-GCM
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(nonce),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            encrypted_data = encryptor.update(content) + encryptor.finalize()
            
            # Get authentication tag
            tag = encryptor.tag
            
            # Combine salt + nonce + tag + encrypted data
            encrypted_content = salt + nonce + tag + encrypted_data
            
            metadata = {
                'algorithm': 'aes-256-gcm',
                'key_derivation': 'pbkdf2-sha256',
                'iterations': 100000,
                'salt_length': 16,
                'nonce_length': 12,
                'tag_length': 16
            }
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Base64 encode for safe transport
        encrypted_b64 = base64.b64encode(encrypted_content).decode('utf-8')
        
        return encrypted_b64, metadata
        
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        raise

# Create blueprint
certificates_bp = Blueprint('certificates', __name__)

# Device-specific certificate endpoints
@certificates_bp.route('/devices/<device_id>/certificate', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_device_certificate(device_id):
    """
    Get device certificate information.
    
    Args:
        device_id: Device identifier
        
    Returns:
        200: Certificate info if exists
        404: Device not found
    """
    try:
        cert_info = get_device_certificate_info(device_id, g.current_user)
        
        if not cert_info:
            return jsonify({'error': 'Device not found'}), 404
        
        return jsonify(cert_info), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate info: {e}")
        return jsonify({'error': 'Failed to retrieve certificate info'}), 500

@certificates_bp.route('/devices/<device_id>/certificate', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def issue_certificate(device_id):
    """
    Issue a new certificate for device.
    
    Args:
        device_id: Device identifier
        
    Returns:
        200: Certificate issued successfully
        404: Device not found
        500: Certificate generation failed
    """
    try:
        # Optional client-specified algorithm; persist before issuance so services can use it
        try:
            payload = request.get_json(silent=True) or {}
            algo = payload.get('algorithm')
            if algo:
                db = get_db()
                if db is not None:
                    # Scope by organization for non-platform admins
                    query = {'device_id': device_id}
                    if g.current_user.get('role') not in ['super_admin', 'platform_admin']:
                        query['organization_id'] = g.current_user.get('organization_id')
                    device = db.devices.find_one(query)
                    if not device and ObjectId.is_valid(device_id):
                        query = {'_id': ObjectId(device_id)}
                        if g.current_user.get('role') not in ['super_admin', 'platform_admin']:
                            query['organization_id'] = g.current_user.get('organization_id')
                        device = db.devices.find_one(query)
                    if device:
                        norm = str(algo).lower().replace('_', '-')
                        db.devices.update_one({'_id': device['_id']}, {'$set': {
                            'certificate_algorithm': norm,
                            'metadata.certificate_algorithm': norm
                        }})
        except Exception as e_set:
            logger.warning(f"Failed to persist requested algorithm for {device_id}: {e_set}")

        # Policy gate: default CSR-first; allow auto-generate only if policy permits
        try:
            from ..core.database import get_db
            db = get_db()
            org_id = (g.current_user or {}).get('organization_id')
            pol = (db.org_policies.find_one({'organization_id': org_id}) or {}).get('certificate', {}) if (db and org_id) else {}
            require_csr = pol.get('require_csr', os.environ.get('REQUIRE_CSR', 'true').lower() in ('1','true','yes'))
            allow_server_side_key_gen = pol.get('allow_server_side_key_gen', os.environ.get('ALLOW_SERVER_SIDE_KEY_GEN','false').lower() in ('1','true','yes'))
            retain_private_key_at_rest = pol.get('retain_private_key_at_rest', os.environ.get('RETAIN_PRIVATE_KEY_AT_REST','false').lower() in ('1','true','yes'))
            if require_csr and not allow_server_side_key_gen:
                return jsonify({'error': 'AUTO_GEN_DISABLED', 'message': 'Auto-generate is disabled by policy. Please use CSR (Upload & Sign).'}), 403
            if allow_server_side_key_gen and not retain_private_key_at_rest:
                # Ephemeral one-time delivery is not implemented here; disallow to avoid at-rest key retention
                return jsonify({'error': 'PRIVATE_KEY_RETENTION_DISABLED', 'message': 'Server-side key generation is disallowed by policy (no key-at-rest). Use CSR.'}), 403
        except Exception as _pol_e:
            logger.warning(f"Policy evaluation failed for issue_certificate: {_pol_e}")

        # Prefer legacy implementation first
        result = issue_device_certificate(device_id, g.current_user)
        if result:
            if isinstance(result, dict) and 'error' in result:
                # Fall through to compatibility path below
                raise Exception(result.get('error'))
            return jsonify(result), 200
    except Exception as e_legacy:
        logger.warning(f"Legacy issue_device_certificate failed for {device_id}: {e_legacy}. Falling back to renew flow")
        try:
            # Enforce PKI-backed issuance on fallback as well (no placeholders)
            from ..services.pki_provisioning_service import PKIProvisioningService
            from ..core.database import get_db, get_vault

            db = get_db()
            if db is None:
                raise RuntimeError('Database unavailable')
            device = db.devices.find_one({'device_id': device_id})
            if not device:
                return jsonify({'error': 'Device not found or access denied'}), 404

            organization_id = device.get('organization_id') or g.current_user.get('organization_id')
            pki = PKIProvisioningService()
            cert_result = pki.generate_device_certificate(
                device_data={
                    'device_id': device_id,
                    'organization_id': organization_id,
                    'certificate_algorithm': (device or {}).get('certificate_algorithm', 'EC-P256'),
                    'certificate_validity_days': 365,
                },
                user=g.current_user,
                vault_client=get_vault()
            )
            response = {
                'message': 'Certificate generated successfully',
                'deviceId': device_id,
                'certificate': {
                    'serial_number': cert_result.get('serial_number'),
                    'issued_at': cert_result.get('issued_at'),
                    'expires_at': cert_result.get('expires_at'),
                    'status': cert_result.get('status', 'valid')
                },
                'download_urls': {
                    'bundle': f"/api/v1/certificates/devices/{device_id}/certificate/download/bundle",
                    'zip': f"/api/v1/certificates/devices/{device_id}/certificate/download/zip",
                    'device_cert': f"/api/v1/certificates/devices/{device_id}/certificate/download/device-cert",
                    'device_key': f"/api/v1/certificates/devices/{device_id}/certificate/download/device-key",
                    'ca_chain': f"/api/v1/certificates/devices/{device_id}/certificate/download/ca-chain"
                }
            }
            return jsonify(response), 200
        except Exception as e_fallback:
            logger.error(f"PKI-backed fallback failed for {device_id}: {e_fallback}")
            return jsonify({'error': 'Failed to issue certificate', 'details': str(e_fallback)}), 500

@certificates_bp.route('/devices/<device_id>/certificate/sign-csr', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def sign_device_csr_endpoint(device_id):
    """
    Sign a Certificate Signing Request (CSR) for a device.
    
    Args:
        device_id: Device identifier
        
    Request JSON:
        {
            "csr": "PEM-encoded CSR string",
            "validity_days": 365  # Optional, defaults to 365
        }
    
    Returns:
        200: Certificate signed successfully
        400: Invalid CSR or parameters
        403: Access denied
        404: Device not found
        500: Signing failed
    """
    try:
        # Tolerant JSON parsing
        data = request.get_json(silent=True) or {}

        # Accept CSR in several common keys or raw text
        csr_content = (data.get('csr') or data.get('csrContent') or data.get('csr_content') or '').strip()
        if not csr_content:
            try:
                raw = request.get_data(as_text=True) or ''
                if 'BEGIN CERTIFICATE REQUEST' in raw:
                    csr_content = raw.strip()
            except Exception:
                pass

        # Check if CSR is required: only mandatory if device has NO Trust M UID
        if not csr_content:
            from database import get_database
            db = get_database()
            device = db.devices.find_one({'device_id': device_id})

            # If device has Trust M UID, CSR is optional (will use factory cert workflow)
            if device and device.get('trustm_uid'):
                # Device with Trust M UID - skip CSR signing, will use factory cert
                return jsonify({
                    'success': True,
                    'message': 'Device will auto-activate with factory certificate',
                    'workflow': 'trust_m_factory_cert',
                    'trustm_uid': device.get('trustm_uid'),
                    'next_steps': [
                        'Device will connect with factory certificate (CN=InfineonIoTNode)',
                        'Platform will auto-activate device on first connection',
                        'Device will generate CSR and send via MQTT later',
                        'Platform certificate will be delivered via Protected Update'
                    ]
                }), 200

            # No Trust M UID - CSR is required
            return jsonify({
                'error': 'MISSING_CSR',
                'message': 'CSR content is required when using upload method'
            }), 400

        # Accept numeric or string for validity_days and normalize
        validity_days_raw = data.get('validity_days', data.get('validityDays', 365))
        try:
            validity_days = int(validity_days_raw)
        except Exception:
            return jsonify({
                'error': 'INVALID_VALIDITY',
                'message': 'Validity must be an integer number of days'
            }), 400
        revoke_old = bool(data.get('revokeOld') or data.get('revoke_old') or False)

        # Validate parameters
        if validity_days < 1 or validity_days > 1095:  # Max 3 years
            return jsonify({
                'error': 'INVALID_VALIDITY',
                'message': 'Validity must be between 1 and 1095 days'
            }), 400

        # Call service function to sign CSR
        # Optional SANs from request (array of strings), sanitized in service layer
        alt_names = data.get('altNames') or data.get('alt_names') or data.get('subjectAltNames') or []

        result = sign_device_csr(
            device_id=device_id,
            csr_content=csr_content,
            validity_days=validity_days,
            user=g.current_user,
            revoke_old=revoke_old,
            alt_names=alt_names
        )
        
        # Check for errors in the result
        if result and 'error' in result:
            error_code = result.get('error_code', 'UNKNOWN_ERROR')
            status_code = 400
            if error_code == 'ACCESS_DENIED' or 'access denied' in result['error'].lower():
                status_code = 403
            elif error_code == 'NOT_FOUND' or 'not found' in result['error'].lower():
                status_code = 404
            return jsonify(result), status_code
        
        return jsonify(result), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    except PermissionError as e:
        return jsonify({
            'error': 'ACCESS_DENIED',
            'message': str(e)
        }), 403
    except ValueError as e:
        return jsonify({
            'error': 'INVALID_REQUEST',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error signing CSR for device {device_id}: {e}")
        return jsonify({
            'error': 'SIGNING_FAILED',
            'message': 'Failed to sign certificate',
            'details': str(e)
        }), 500

@certificates_bp.route('/devices/<device_id>/certificate/download/<file_type>', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def download_certificate(device_id, file_type):
    """
    Download device certificate files with optional encryption.
    
    Args:
        device_id: Device identifier
        file_type: Type of file (device-cert, device-key, ca-chain, bundle)
        
    Query Parameters:
        encrypted: Whether to encrypt the download with password (true/false, default: false)
        password: Password for encryption (required if encrypted=true)
        algorithm: Encryption algorithm (aes-256-cbc, default)
        auto_encrypt: Auto-encrypt using device's public key (true/false, default: false)
        
    Returns:
        200: File download (plain or encrypted)
        400: Invalid file type or missing encryption parameters
        404: Device not found
        500: Download failed
    """
    try:
        bundle_like_types = {'bundle', 'trustm-starter-bundle'}

        # Check for encryption parameters
        encrypted = request.args.get('encrypted', 'false').lower() == 'true'
        password = request.args.get('password')
        algorithm = request.args.get('algorithm', 'aes-256-cbc')
        auto_encrypt = request.args.get('auto_encrypt', 'false').lower() == 'true'
        
        # Policy-aware enforcement for one-time encrypted key delivery
        try:
            db = get_db()
            device = db.devices.find_one({'device_id': device_id}) if db is not None else None
            org_id = device.get('organization_id') if device else None
            pol = (db.org_policies.find_one({'organization_id': org_id}) or {}).get('certificate', {}) if (db is not None and org_id) else {}
            one_time_encrypted = bool(pol.get('one_time_encrypted_key_delivery', os.environ.get('ONE_TIME_ENCRYPTED_KEY_DELIVERY', 'true').lower() in ('1','true','yes')))
        except Exception:
            one_time_encrypted = os.environ.get('ONE_TIME_ENCRYPTED_KEY_DELIVERY', 'true').lower() in ('1','true','yes')

        def _notify_download_event(filename_hint: str = '', priority_level: str = 'medium'):
            try:
                if not device:
                    return
                org_id = device.get('organization_id')
                if not org_id:
                    return
                notification_acl_service.create_device_certificate_notification(
                    event='certificate_downloaded',
                    device=device,
                    organization_id=str(org_id),
                    actor=g.current_user,
                    priority=priority_level,
                    metadata={
                        'file_type': file_type,
                        'filename': filename_hint,
                    },
                )
            except Exception as notify_error:
                logger.debug(f"Notification dispatch skipped for certificate download: {notify_error}")

        # Validate encryption parameters
        if encrypted and auto_encrypt:
            return jsonify({
                'error': 'INVALID_REQUEST',
                'message': 'Cannot use both password encryption and auto-encryption simultaneously'
            }), 400
            
        if encrypted:
            if not password:
                return jsonify({
                    'error': 'MISSING_PASSWORD',
                    'message': 'Password is required for encrypted downloads'
                }), 400
            
            if algorithm not in ['aes-256-cbc', 'aes-256-gcm']:
                return jsonify({
                    'error': 'INVALID_ALGORITHM',
                    'message': 'Supported algorithms: aes-256-cbc, aes-256-gcm'
                }), 400
        
        if auto_encrypt and file_type != 'device-key':
            return jsonify({
                'error': 'INVALID_REQUEST',
                'message': 'Auto-encryption is only supported for device-key file type'
            }), 400

        # If policy requires one-time encrypted delivery, force auto-encrypt on device-key downloads
        if file_type == 'device-key' and one_time_encrypted:
            auto_encrypt = True
        
        # Check device public key availability for auto-encryption
        if auto_encrypt:
            db = get_db()
            device = db.devices.find_one({'device_id': device_id})
            
            if not device:
                return jsonify({
                    'error': 'DEVICE_NOT_FOUND',
                    'message': 'Device not found'
                }), 404
            
            # Check if device has public key for encryption
            device_public_key = device.get('device_public_key', {})
            has_public_key = device_public_key and device_public_key.get('key')
            
            if not has_public_key and one_time_encrypted and file_type == 'device-key':
                # Policy requires one-time encrypted delivery but no public key available; block plain download
                return jsonify({
                    'error': 'ONE_TIME_ENCRYPTION_REQUIRED',
                    'message': 'Organization policy requires one-time encrypted key delivery. Register a device public key to enable encrypted download.'
                }), 400
            
            logger.info(f"Auto-encrypted download requested for device {device_id}, public key available")
        
        # Log encrypted download attempt
        if encrypted:
            logger.info(f"Encrypted download requested for device {device_id}, file_type: {file_type}, algorithm: {algorithm}")
        
        # Skip audit logging in service if encryption will be applied (to avoid duplicate logs)
        skip_audit = encrypted or auto_encrypt
        result = download_certificate_file(device_id, file_type, g.current_user, skip_audit=skip_audit, auto_encrypt=auto_encrypt)
        
        # Check if it's already a Response object (for bundle)
        if isinstance(result, Response):
            # For bundle files that are already Response objects
            if encrypted:
                # Extract content from Response for encryption
                content = result.data
                filename = result.headers.get('Content-Disposition', '').split('filename=')[-1].strip()
                
                # Encrypt the bundle
                try:
                    encrypted_content, encryption_metadata = encrypt_certificate_content(
                        content, password, algorithm, is_binary=True
                    )
                    
                    # Add audit log for encrypted download
                    audit_log(
                        action=AuditAction.CERTIFICATE_DOWNLOAD,
                        user=g.current_user,
                        resource_type='certificate',
                        resource_id=device_id,
                        details={
                            'file_type': file_type,
                            'algorithm': algorithm,
                            'encrypted': True,
                            'encryption_method': 'password-based'
                        }
                    )
                    
                    # Return encrypted bundle as JSON
                    # Remove existing extension and add .json
                    base_filename = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    
                    # Create JSON response with encrypted data
                    encrypted_json = {
                        'encrypted_data': encrypted_content,
                        'algorithm': algorithm,
                        **encryption_metadata
                    }
                    
                    response = Response(
                        json.dumps(encrypted_json),
                        mimetype='application/json',
                        headers={
                            'Content-Disposition': f'attachment; filename={base_filename}.json',
                            'Content-Type': 'application/json',
                            'X-Encryption-Algorithm': algorithm,
                            'X-Key-Encrypted': 'true'
                        }
                    )
                    _notify_download_event(f'{base_filename}.json', priority_level='medium')
                    return response
                except Exception as e:
                    logger.error(f"Error encrypting bundle: {e}")
                    return jsonify({
                        'error': 'ENCRYPTION_FAILED',
                        'message': 'Failed to encrypt certificate bundle',
                        'details': str(e)
                    }), 500
            else:
                # Non-encrypted bundle - add X-Key-Encrypted header
                result.headers['X-Key-Encrypted'] = 'false'
            priority_hint = 'medium' if file_type in {'device-key', 'bundle', 'trustm-starter-bundle'} else 'low'
            _notify_download_event(result.headers.get('Content-Disposition', ''), priority_level=priority_hint)
            return result
            
        # Check if it's an error response (tuple with dict and status code)
        if isinstance(result, tuple) and len(result) == 2:
            # Check if second element is a status code (int)
            if isinstance(result[1], int) and result[1] >= 400:
                logger.warning(
                    "Certificate download failed",
                    extra={
                        'device_id': device_id,
                        'file_type': file_type,
                        'status_code': result[1],
                        'error': result[0]
                    }
                )
                return jsonify(result[0]), result[1]
            # Otherwise it's a successful file response (content, filename)
            else:
                content, filename = result
                
                # Check if auto-encryption occurred (filename indicates encryption)
                is_auto_encrypted = filename.endswith('-encrypted.json') or filename.endswith('-encrypted.pem')
                
                # If auto-encrypted, return the encrypted content directly
                if is_auto_encrypted:
                    # Auto-encryption already applied by service
                    # Determine content type based on file extension
                    if filename.endswith('.json'):
                        content_type = 'application/json'
                    else:
                        content_type = 'text/plain'
                    
                    response = Response(
                        content,
                        mimetype=content_type,
                        headers={
                            'Content-Disposition': f'attachment; filename={filename}',
                            'Content-Type': content_type,
                            'X-Auto-Encrypted': 'true',
                            'X-Encryption-Method': 'hybrid-rsa-aes',
                            'X-Key-Encrypted': 'true'
                        }
                    )
                    
                    # Add audit log for auto-encrypted download
                    audit_log(
                        action=AuditAction.CERTIFICATE_DOWNLOAD,
                        user=g.current_user,
                        resource_type='certificate',
                        resource_id=device_id,
                        details={
                            'file_type': file_type,
                            'encrypted': True,
                            'encryption_method': 'auto-hybrid',
                            'auto_encrypted': True
                        }
                    )
                    _notify_download_event(filename, priority_level='medium')
                    return response
                
                # Check if manual encryption is requested
                elif encrypted:
                    # Encrypt the content
                    try:
                        # Determine if content is binary (for bundles)
                        is_binary = file_type in bundle_like_types
                        
                        encrypted_content, encryption_metadata = encrypt_certificate_content(
                            content, password, algorithm, is_binary=is_binary
                        )
                        
                        # Add audit log for encrypted download
                        audit_log(
                            action=AuditAction.CERTIFICATE_DOWNLOAD,
                            user=g.current_user,
                            resource_type='certificate',
                            resource_id=device_id,
                            details={
                                'file_type': file_type,
                                'algorithm': algorithm,
                                'encrypted': True,
                                'encryption_method': 'password-based'
                            }
                        )
                        
                        # Return encrypted file as JSON
                        # Remove existing extension and add .json
                        base_filename = filename.rsplit('.', 1)[0] if '.' in filename else filename
                        
                        # Create JSON response with encrypted data
                        encrypted_json = {
                            'encrypted_data': encrypted_content,
                            'algorithm': algorithm,
                            **encryption_metadata
                        }
                        
                        response = Response(
                            json.dumps(encrypted_json),
                            mimetype='application/json',
                            headers={
                                'Content-Disposition': f'attachment; filename={base_filename}.json',
                                'Content-Type': 'application/json',
                                'X-Encryption-Algorithm': algorithm,
                                'X-Key-Encrypted': 'true'
                            }
                        )
                        _notify_download_event(f'{base_filename}.json', priority_level='medium')
                        return response
                    except Exception as e:
                        logger.error(f"Error encrypting certificate: {e}")
                        return jsonify({
                            'error': 'ENCRYPTION_FAILED',
                            'message': 'Failed to encrypt certificate',
                            'details': str(e)
                        }), 500
                else:
                    # Non-encrypted download - add audit log
                    audit_log(
                        action=AuditAction.CERTIFICATE_DOWNLOAD,
                        user=g.current_user,
                        resource_type='certificate',
                        resource_id=device_id,
                        details={
                            'file_type': file_type,
                            'encrypted': False
                        }
                    )
                    
                    # Check file type based on extension and file_type
                    if file_type in bundle_like_types:
                        # For ZIP files
                        response = Response(content, mimetype='application/zip')
                        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                        response.headers['Content-Type'] = 'application/zip'
                        response.headers['X-Key-Encrypted'] = 'false'
                        response.headers['X-Bundle-Type'] = 'trustm-starter' if file_type == 'trustm-starter-bundle' else 'standard'
                    elif filename.endswith('.json'):
                        # For JSON files (encrypted keys)
                        response = Response(content, mimetype='application/json')
                        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                        response.headers['Content-Type'] = 'application/json'
                        response.headers['X-Key-Encrypted'] = 'true'
                        response.headers['X-Encryption-Method'] = 'hybrid-rsa-aes'
                    else:
                        # For PEM files
                        response = Response(content, mimetype='application/x-pem-file')
                        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
                        response.headers['Content-Type'] = 'application/x-pem-file'
                        response.headers['X-Key-Encrypted'] = 'false'
                    priority_hint = 'medium' if file_type in {'device-key', 'bundle', 'trustm-starter-bundle'} else 'low'
                    _notify_download_event(filename, priority_level=priority_hint)
                return response
        
        # If not a tuple or Response, something went wrong
        return jsonify({'error': 'Invalid response from certificate service'}), 500
        
    except Exception as e:
        logger.error(f"Error downloading certificate: {e}")
        return jsonify({'error': 'Failed to download certificate'}), 500

# General certificate endpoints
@certificates_bp.route('/', methods=['GET'])
@certificates_bp.route('/list', methods=['GET'])  # Add alias for compatibility
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_certificates():
    """
    Get list of all certificates filtered by organization.
    
    Returns:
        200: List of certificates
        500: Server error
    """
    try:
        certificates = get_certificates_list(g.current_user)
        
        # Apply data fixes
        certificates = [fix_certificate_data(cert) for cert in certificates]
        
        return jsonify(certificates), 200
        
    except Exception as e:
        logger.error(f"Error getting certificates: {e}")
        return jsonify({'error': 'Failed to retrieve certificates'}), 500

# CSR validation endpoint
@certificates_bp.route('/validate-csr', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def validate_csr():
    """
    Validate an external Certificate Signing Request (CSR).
    
    Request JSON:
        {
            "csr": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----"
        }
    
    Returns:
        200: CSR validation successful with details
        400: Invalid CSR format or content
        500: Server error
    """
    try:
        data = request.get_json()
        
        if not data or 'csr' not in data:
            return jsonify({
                'isValid': False,
                'message': 'CSR content is required',
                'error': 'MISSING_CSR'
            }), 400
        
        csr_content = data.get('csr', '').strip()
        
        # Basic format check
        if not csr_content:
            return jsonify({
                'isValid': False,
                'message': 'CSR content cannot be empty',
                'error': 'EMPTY_CSR'
            }), 400
        
        # Validate CSR using the service function
        result = validate_external_csr(csr_content, g.current_user)
        
        if result['isValid']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error validating CSR: {e}")
        return jsonify({
            'isValid': False,
            'message': 'Failed to validate CSR',
            'error': 'VALIDATION_ERROR',
            'details': str(e)
        }), 500

# Alert settings endpoints
@certificates_bp.route('/alerts', methods=['GET', 'POST'])
@require_auth
def manage_alerts():
    """
    Manage certificate expiration alert settings.
    
    GET: Returns current alert settings
    POST: Updates alert settings
    
    Returns:
        200: Success
        400: Invalid data
        500: Server error
    """
    if request.method == 'GET':
        try:
            settings = get_alert_settings(g.current_user)
            return jsonify(settings), 200
        except Exception as e:
            logger.error(f"Error getting alert settings: {e}")
            return jsonify({'error': 'Failed to retrieve settings'}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            
            if not isinstance(data, dict):
                return jsonify({'error': 'Invalid data format'}), 400
            
            update_alert_settings(data, g.current_user)
            
            return jsonify({'message': 'Alert settings updated successfully'}), 200
            
        except Exception as e:
            logger.error(f"Error updating alert settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500

@certificates_bp.route('/check-alerts', methods=['POST'])
@require_auth
@require_role(['admin', 'super_admin'])
def check_alerts():
    """
    Manually trigger certificate expiration alerts check.
    
    Returns:
        200: Check completed
        403: Insufficient permissions
        500: Server error
    """
    try:
        alerts_sent = check_expiring_certificates()
        
        return jsonify({
            'message': 'Alert check completed',
            'alerts_sent': alerts_sent,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        return jsonify({'error': 'Failed to check alerts', 'details': str(e)}), 500

# Auto-renewal endpoints
@certificates_bp.route('/auto-renewal', methods=['GET', 'POST'])
@require_auth
def manage_auto_renewal():
    """
    Manage certificate auto-renewal settings.
    
    GET: Returns current auto-renewal configuration
    POST: Updates auto-renewal settings
    
    Returns:
        200: Success
        400: Invalid data
        500: Server error
    """
    if request.method == 'GET':
        try:
            settings = get_auto_renewal_settings(g.current_user)
            return jsonify(settings), 200
        except Exception as e:
            logger.error(f"Error getting auto-renewal settings: {e}")
            return jsonify({'error': 'Failed to retrieve settings'}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            
            # Validate threshold
            threshold = data.get('threshold', 30)
            if threshold < 7:
                return jsonify({'error': 'Threshold must be at least 7 days'}), 400
            if threshold > 90:
                return jsonify({'error': 'Threshold cannot exceed 90 days'}), 400
            
            update_auto_renewal_settings(data, g.current_user)
            
            return jsonify({
                'message': 'Auto-renewal settings updated successfully',
                'enabled': data.get('enabled'),
                'threshold': threshold
            }), 200
            
        except Exception as e:
            logger.error(f"Error updating auto-renewal settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500

@certificates_bp.route('/auto-renewal/trigger', methods=['POST'])
@require_auth
def trigger_renewal():
    """
    Manually trigger certificate auto-renewal check.
    
    Returns:
        200: Renewal check completed
        400: Auto-renewal not enabled
        500: Server error
    """
    try:
        result = trigger_certificate_renewal(g.current_user)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error triggering renewal: {e}")
        return jsonify({'error': 'Failed to trigger renewal', 'details': str(e)}), 500

@certificates_bp.route('/test-notification', methods=['POST'])
@require_auth
def test_notification():
    """
    Test email and webhook notification configuration.
    
    Request JSON:
        {
            "type": "email|webhook",
            "recipients": ["email@example.com"],  // for email
            "webhook_url": "https://..."          // for webhook
        }
    
    Returns:
        200: Test successful
        400: Invalid request
        500: Test failed
    """
    try:
        data = request.get_json()
        notification_type = data.get('type', 'email')
        
        success, message = send_test_notification(notification_type, data)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 500
            
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return jsonify({'error': 'Failed to send test notification', 'details': str(e)}), 500

# Audit trail endpoints
@certificates_bp.route('/audit-trail', methods=['GET'])
@require_auth
def get_audit_trail_endpoint():
    """
    Get certificate audit trail for all certificate operations.
    
    Query Parameters:
        start_date: ISO format start date
        end_date: ISO format end date
        
    Returns:
        200: Audit trail events
        500: Server error
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        events = get_audit_trail(g.current_user, start_date, end_date)
        
        return jsonify(events), 200
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}")
        return jsonify({'error': 'Failed to retrieve audit trail', 'details': str(e)}), 500

@certificates_bp.route('/audit-trail/export', methods=['GET'])
@require_auth
def export_audit_trail_endpoint():
    """
    Export complete certificate audit trail as JSON.
    
    Returns:
        200: Export data
        500: Server error
    """
    try:
        export_data = export_audit_trail(g.current_user)
        
        return jsonify(export_data), 200
        
    except Exception as e:
        logger.error(f"Error exporting audit trail: {e}")
        return jsonify({'error': 'Failed to export audit trail', 'details': str(e)}), 500

# Bulk operations endpoint
@certificates_bp.route('/bulk', methods=['POST'])
@require_auth
@require_role(['admin', 'super_admin'])
def bulk_operation():
    """
    Perform bulk operations on multiple certificates.
    
    Request JSON:
        {
            "operation": "renew|revoke|export",
            "certificate_ids": ["id1", "id2", ...]
        }
    
    Returns:
        200: Operation completed
        400: Invalid request
        403: Insufficient permissions
        500: Operation failed
    """
    try:
        data = request.get_json()
        
        operation = data.get('operation')
        certificate_ids = data.get('certificate_ids', [])
        
        if not operation or not certificate_ids:
            return jsonify({'error': 'Operation and certificate_ids required'}), 400
        
        if operation not in ['renew', 'revoke', 'export']:
            return jsonify({'error': 'Invalid operation'}), 400
        
        result = perform_bulk_operation(operation, certificate_ids, g.current_user)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error performing bulk operation: {e}")
        return jsonify({'error': 'Bulk operation failed', 'details': str(e)}), 500

# Certificate analytics endpoint
@certificates_bp.route('/analytics', methods=['GET'])
@require_auth
def get_analytics():
    """
    Get certificate analytics data.
    
    Returns:
        200: Analytics data
        500: Server error
    """
    try:
        analytics = get_certificate_analytics(g.current_user)
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Error getting certificate analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500

# ACME protocol endpoints
@certificates_bp.route('/acme/settings', methods=['GET', 'POST'])
@require_auth
@require_role(['admin', 'super_admin', 'platform_admin', 'organization_admin'])
def manage_acme_settings():
    """
    Manage ACME protocol settings.
    
    GET: Returns current ACME configuration
    POST: Updates ACME settings
    
    Returns:
        200: Success
        403: Insufficient permissions
        500: Server error
    """
    if request.method == 'GET':
        try:
            settings = get_acme_settings(g.current_user)
            return jsonify(settings), 200
        except Exception as e:
            logger.error(f"Error getting ACME settings: {e}")
            return jsonify({'error': 'Failed to retrieve settings'}), 500
    
    else:  # POST
        try:
            data = request.get_json()
            
            update_acme_settings(data, g.current_user)
            
            return jsonify({'message': 'ACME settings updated successfully'}), 200
            
        except Exception as e:
            logger.error(f"Error updating ACME settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500

@certificates_bp.route('/acme/certificates', methods=['GET'])
@require_auth
def get_acme_certs():
    """
    Get list of ACME-managed certificates.
    
    Returns:
        200: List of ACME certificates
        500: Server error
    """
    try:
        certificates = get_acme_certificates(g.current_user)
        
        return jsonify(certificates), 200
        
    except Exception as e:
        logger.error(f"Error getting ACME certificates: {e}")
        return jsonify({'error': 'Failed to retrieve certificates'}), 500

@certificates_bp.route('/acme/renew', methods=['POST'])
@require_auth
@require_role(['admin', 'super_admin'])
def renew_acme_cert():
    """
    Manually renew ACME certificate.
    
    Request JSON:
        {
            "certificate_id": "cert_id"
        }
    
    Returns:
        200: Renewal initiated
        400: Invalid request
        403: Insufficient permissions
        500: Renewal failed
    """
    try:
        data = request.get_json()
        certificate_id = data.get('certificate_id')
        
        if not certificate_id:
            return jsonify({'error': 'certificate_id required'}), 400
        
        result = renew_acme_certificate(certificate_id, g.current_user)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error renewing ACME certificate: {e}")
        return jsonify({'error': 'Failed to renew certificate', 'details': str(e)}), 500

# --- Policy Endpoints (Phase 1/2) ---
@certificates_bp.route('/policies/renewal-threshold', methods=['GET'])
@require_auth
def get_renewal_threshold():
    """Return effective early renewal threshold in days for current organization.

    Order of precedence: org policy > env EARLY_RENEWAL_THRESHOLD_DAYS > 60
    """
    try:
        from ..core.database import get_db
        db = get_db()
        org_id = (g.current_user or {}).get('organization_id')
        source = 'default'
        threshold = 60
        device_type = request.args.get('device_type')
        # Env
        try:
            threshold = int(os.environ.get('EARLY_RENEWAL_THRESHOLD_DAYS', str(threshold)))
            source = 'env'
        except Exception:
            pass
        # Org policy
        if db is not None and org_id:
            pol = db.org_policies.find_one({'organization_id': org_id})
            cert_pol = pol and pol.get('certificate', {})
            # device-type override
            if device_type and isinstance(cert_pol.get('per_device_type'), dict):
                dt = cert_pol['per_device_type'].get(device_type)
                if isinstance(dt, dict) and isinstance(dt.get('early_renewal_threshold_days'), int):
                    threshold = dt['early_renewal_threshold_days']
                    source = f'org:{device_type}'
            if source in ['env', 'default']:
                days = cert_pol and cert_pol.get('early_renewal_threshold_days')
                if isinstance(days, int) and days > 0:
                    threshold = days
                    source = 'org'
        return jsonify({'threshold_days': threshold, 'source': source}), 200
    except Exception as e:
        logger.error(f"Error reading renewal threshold: {e}")
        return jsonify({'threshold_days': 60, 'source': 'default'}), 200

@certificates_bp.route('/policies/certificates', methods=['GET'])
@require_auth
def get_org_certificate_policy():
    """Return organization-level certificate policy."""
    try:
        from ..core.database import get_db
        db = get_db()
        org_id = (g.current_user or {}).get('organization_id')
        # Track effective source per field where useful for UI
        sources = {
            'allow_bundle_include_password': 'default',
            'allow_bundle_include_api_key': 'default',
        }

        policy = {
            'early_renewal_threshold_days': int(os.environ.get('EARLY_RENEWAL_THRESHOLD_DAYS', '60')),
            'default_validity_days': int(os.environ.get('DEFAULT_CERT_VALIDITY_DAYS', '365')),
            'allowed_algorithms': ['ecc-p256', 'ecc-p384', 'rsa-3072'],
            'per_device_type': {},
            'auto_revoke_on_renew': os.environ.get('AUTO_REVOKE_ON_RENEW', 'false').lower() in ('1','true','yes'),
            # New security gates (defaults favor CSR in production)
            'require_csr': os.environ.get('REQUIRE_CSR', 'true').lower() in ('1','true','yes'),
            'allow_server_side_key_gen': os.environ.get('ALLOW_SERVER_SIDE_KEY_GEN', 'false').lower() in ('1','true','yes'),
            'one_time_encrypted_key_delivery': os.environ.get('ONE_TIME_ENCRYPTED_KEY_DELIVERY', 'true').lower() in ('1','true','yes'),
            'retain_private_key_at_rest': os.environ.get('RETAIN_PRIVATE_KEY_AT_REST', 'false').lower() in ('1','true','yes'),
            # Bundle inclusion policy (org-level): default deny
            'allow_bundle_include_password': os.environ.get('ALLOW_BUNDLE_INCLUDE_PASSWORD', 'false').lower() in ('1','true','yes'),
            'allow_bundle_include_api_key': os.environ.get('ALLOW_BUNDLE_INCLUDE_API_KEY', 'false').lower() in ('1','true','yes')
        }

        # Mark env source when explicitly provided
        if 'ALLOW_BUNDLE_INCLUDE_PASSWORD' in os.environ:
            sources['allow_bundle_include_password'] = 'env'
        if 'ALLOW_BUNDLE_INCLUDE_API_KEY' in os.environ:
            sources['allow_bundle_include_api_key'] = 'env'
        if db is not None and org_id:
            pol = db.org_policies.find_one({'organization_id': org_id})
            if pol and isinstance(pol.get('certificate'), dict):
                cp = pol['certificate']
                policy['early_renewal_threshold_days'] = cp.get('early_renewal_threshold_days', policy['early_renewal_threshold_days'])
                policy['default_validity_days'] = cp.get('default_validity_days', policy['default_validity_days'])
                if isinstance(cp.get('allowed_algorithms'), list):
                    policy['allowed_algorithms'] = cp['allowed_algorithms']
                if isinstance(cp.get('per_device_type'), dict):
                    policy['per_device_type'] = cp['per_device_type']
                if 'auto_revoke_on_renew' in cp:
                    policy['auto_revoke_on_renew'] = bool(cp.get('auto_revoke_on_renew'))
                if 'require_csr' in cp:
                    policy['require_csr'] = bool(cp.get('require_csr'))
                if 'allow_server_side_key_gen' in cp:
                    policy['allow_server_side_key_gen'] = bool(cp.get('allow_server_side_key_gen'))
                if 'one_time_encrypted_key_delivery' in cp:
                    policy['one_time_encrypted_key_delivery'] = bool(cp.get('one_time_encrypted_key_delivery'))
                if 'retain_private_key_at_rest' in cp:
                    policy['retain_private_key_at_rest'] = bool(cp.get('retain_private_key_at_rest'))
                if 'allow_bundle_include_password' in cp:
                    policy['allow_bundle_include_password'] = bool(cp.get('allow_bundle_include_password'))
                    sources['allow_bundle_include_password'] = 'org'
                if 'allow_bundle_include_api_key' in cp:
                    policy['allow_bundle_include_api_key'] = bool(cp.get('allow_bundle_include_api_key'))
                    sources['allow_bundle_include_api_key'] = 'org'
        return jsonify({'policy': policy, 'sources': sources}), 200
    except Exception as e:
        logger.error(f"Error getting certificate policy: {e}")
        return jsonify({'error': 'Failed to get policy'}), 500

@certificates_bp.route('/policies/certificates', methods=['PUT'])
@require_auth
@require_role(['org_admin', 'organization_admin', 'admin', 'super_admin'])
def update_org_certificate_policy():
    """Update organization-level certificate policy (Phase 2)."""
    try:
        data = request.get_json() or {}
        # Validate and build update payload
        update_doc = {}
        threshold = data.get('early_renewal_threshold_days')
        if threshold is not None:
            if not isinstance(threshold, int) or threshold <= 0 or threshold > 3650:
                return jsonify({'error': 'Invalid threshold'}), 400
            update_doc['certificate.early_renewal_threshold_days'] = threshold
        default_validity_days = data.get('default_validity_days')
        if default_validity_days is not None:
            if not isinstance(default_validity_days, int) or default_validity_days <= 0 or default_validity_days > 3650:
                return jsonify({'error': 'Invalid default_validity_days'}), 400
            update_doc['certificate.default_validity_days'] = default_validity_days
        allowed_algorithms = data.get('allowed_algorithms')
        if allowed_algorithms is not None:
            if not (isinstance(allowed_algorithms, list) and all(isinstance(a, str) for a in allowed_algorithms)):
                return jsonify({'error': 'Invalid allowed_algorithms'}), 400
            update_doc['certificate.allowed_algorithms'] = allowed_algorithms
        per_device_type = data.get('per_device_type')
        if per_device_type is not None:
            if not isinstance(per_device_type, dict):
                return jsonify({'error': 'per_device_type must be object'}), 400
            for k, v in per_device_type.items():
                if not isinstance(v, dict):
                    return jsonify({'error': f'per_device_type.{k} must be object'}), 400
                if 'early_renewal_threshold_days' in v and not isinstance(v['early_renewal_threshold_days'], int):
                    return jsonify({'error': f'per_device_type.{k}.early_renewal_threshold_days must be int'}), 400
                if 'default_validity_days' in v and not isinstance(v['default_validity_days'], int):
                    return jsonify({'error': f'per_device_type.{k}.default_validity_days must be int'}), 400
                if 'allowed_algorithms' in v:
                    if not (isinstance(v['allowed_algorithms'], list) and all(isinstance(a, str) for a in v['allowed_algorithms'])):
                        return jsonify({'error': f'per_device_type.{k}.allowed_algorithms must be string[]'}), 400
            update_doc['certificate.per_device_type'] = per_device_type
        # New security gates (booleans)
        for fld in ['require_csr','allow_server_side_key_gen','one_time_encrypted_key_delivery','retain_private_key_at_rest','auto_revoke_on_renew',
                    'allow_bundle_include_password','allow_bundle_include_api_key']:
            if fld in data:
                if not isinstance(data[fld], bool):
                    return jsonify({'error': f'{fld} must be boolean'}), 400
        from ..core.database import get_db
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database unavailable'}), 500
        org_id = (g.current_user or {}).get('organization_id')
        if not org_id:
            return jsonify({'error': 'Organization not found'}), 400
        # Optional toggles
        if 'auto_revoke_on_renew' in data:
            update_doc['certificate.auto_revoke_on_renew'] = bool(data['auto_revoke_on_renew'])
        if 'require_csr' in data:
            update_doc['certificate.require_csr'] = bool(data['require_csr'])
        if 'allow_server_side_key_gen' in data:
            update_doc['certificate.allow_server_side_key_gen'] = bool(data['allow_server_side_key_gen'])
        if 'one_time_encrypted_key_delivery' in data:
            update_doc['certificate.one_time_encrypted_key_delivery'] = bool(data['one_time_encrypted_key_delivery'])
        if 'retain_private_key_at_rest' in data:
            update_doc['certificate.retain_private_key_at_rest'] = bool(data['retain_private_key_at_rest'])
        if 'allow_bundle_include_password' in data:
            update_doc['certificate.allow_bundle_include_password'] = bool(data['allow_bundle_include_password'])
        if 'allow_bundle_include_api_key' in data:
            update_doc['certificate.allow_bundle_include_api_key'] = bool(data['allow_bundle_include_api_key'])

        set_doc = {'organization_id': org_id}
        set_doc.update(update_doc)
        db.org_policies.update_one(
            {'organization_id': org_id},
            {'$set': set_doc},
            upsert=True
        )
        audit_log(
            action=AuditAction.KEY_POLICY_UPDATE,
            user=g.current_user,
            resource_type='organization',
            resource_id=org_id,
            details={'policy_update': update_doc}
        )
        pol = db.org_policies.find_one({'organization_id': org_id}) or {}
        return jsonify({'status': 'ok', 'policy': pol.get('certificate', {})}), 200
    except Exception as e:
        logger.error(f"Error updating certificate policy: {e}")
        return jsonify({'error': 'Failed to update policy'}), 500

@certificates_bp.route('/audit/early-renewals', methods=['GET'])
@require_auth
def list_early_renewals():
    """Admin-only: list early-renewal audit entries (days_remaining > threshold)."""
    try:
        from ..core.database import get_db
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database unavailable'}), 500
        # Authorization: only organization-level admins can view
        role = (g.current_user or {}).get('role', '')
        if role not in ['org_admin', 'organization_admin', 'admin', 'super_admin']:
            return jsonify({'error': 'Access denied'}), 403
        org_id = (g.current_user or {}).get('organization_id')
        # Filters
        from dateutil import parser as dtparser
        start = request.args.get('start')
        end = request.args.get('end')
        q = {'action': 'certificate.issue', 'details.early_renewal': True}
        if org_id and role != 'super_admin':
            q['organization_id'] = org_id
        if start:
            try:
                q['timestamp'] = q.get('timestamp', {})
                q['timestamp']['$gte'] = dtparser.parse(start)
            except Exception:
                pass
        if end:
            try:
                q['timestamp'] = q.get('timestamp', {})
                q['timestamp']['$lte'] = dtparser.parse(end)
            except Exception:
                pass
        items = list(db.audit_logs.find(q).sort('timestamp', -1).limit(500))
        # Normalize ObjectIds
        for it in items:
            it['id'] = str(it.pop('_id')) if it.get('_id') else None
        return jsonify({'items': items, 'count': len(items)}), 200
    except Exception as e:
        logger.error(f"Error listing early renewals: {e}")
        return jsonify({'error': 'Failed to list early renewals'}), 500

# Key Provisioning endpoints
@certificates_bp.route('/keys/generate', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def generate_bulk_keys_endpoint():
    """
    Generate bulk keys for multiple devices.
    
    Request JSON:
        {
            "devices": [
                {
                    "device_id": "device_001",
                    "algorithm": "ECC-P256",
                    "device_type": "sensor"
                }
            ],
            "algorithm": "ECC-P256",  # Default algorithm if not specified per device
            "session_name": "Batch_2025_01",
            "metadata": {}
        }
    
    Returns:
        200: Key generation session created
        400: Invalid request
        500: Generation failed
    """
    try:
        data = request.get_json()
        
        if not data or 'devices' not in data:
            return jsonify({'error': 'Devices list is required'}), 400
        
        devices = data['devices']
        if not isinstance(devices, list) or len(devices) == 0:
            return jsonify({'error': 'At least one device required'}), 400
        
        if len(devices) > 1000:
            return jsonify({'error': 'Maximum 1000 devices per batch'}), 400
        
        # Validate device data
        for device in devices:
            if not device.get('device_id'):
                return jsonify({'error': 'device_id is required for all devices'}), 400
        
        result = generate_bulk_keys(
            devices=devices,
            default_algorithm=data.get('algorithm', 'ECC-P256'),
            session_name=data.get('session_name', f'Batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}'),
            metadata=data.get('metadata', {}),
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error generating bulk keys: {e}")
        return jsonify({'error': 'Failed to generate keys', 'details': str(e)}), 500

@certificates_bp.route('/keys/algorithms', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_supported_algorithms_endpoint():
    """
    Get list of supported key algorithms.
    
    Returns:
        200: List of supported algorithms
        500: Server error
    """
    try:
        algorithms = get_supported_algorithms()
        return jsonify(algorithms), 200
        
    except Exception as e:
        logger.error(f"Error getting supported algorithms: {e}")
        return jsonify({'error': 'Failed to retrieve algorithms'}), 500

@certificates_bp.route('/keys/distribute', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def distribute_keys_endpoint():
    """
    Distribute keys to devices.
    
    Request JSON:
        {
            "session_id": "session_123",
            "devices": ["device_001", "device_002"],
            "distribution_method": "secure_download",
            "expiry_hours": 24
        }
    
    Returns:
        200: Distribution initiated
        400: Invalid request
        500: Distribution failed
    """
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'session_id is required'}), 400
        
        session_id = data['session_id']
        devices = data.get('devices', [])
        distribution_method = data.get('distribution_method', 'secure_download')
        expiry_hours = data.get('expiry_hours', 24)
        
        if distribution_method not in ['secure_download', 'escrow', 'direct_push']:
            return jsonify({'error': 'Invalid distribution method'}), 400
        
        result = distribute_keys_to_devices(
            session_id=session_id,
            devices=devices,
            distribution_method=distribution_method,
            expiry_hours=expiry_hours,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error distributing keys: {e}")
        return jsonify({'error': 'Failed to distribute keys', 'details': str(e)}), 500

@certificates_bp.route('/keys/rotation-policy', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_rotation_policy_endpoint():
    """
    Get current key rotation policy for the organization.
    
    Returns:
        200: Current rotation policy
        404: No policy found
        500: Server error
    """
    try:
        db = get_db()
        organization_id = g.current_user.get('organization_id')
        
        # Get rotation policy for the organization
        policy = db.key_rotation_policies.find_one(
            {'organization_id': organization_id},
            {'_id': 0}  # Exclude MongoDB _id from response
        )
        
        if not policy:
            # Return default policy if none exists
            return jsonify({
                'enabled': False,
                'rotation_type': 'time_based',
                'rotation_interval_days': 90,
                'auto_rotation': False,
                'pre_rotation_warning_days': 7,
                'device_filters': {
                    'device_types': [],
                    'organizations': []
                },
                'created_at': None,
                'updated_at': None
            }), 200
        
        return jsonify(policy), 200
        
    except Exception as e:
        logger.error(f"Error getting rotation policy: {e}")
        return jsonify({'error': 'Failed to get rotation policy', 'details': str(e)}), 500

@certificates_bp.route('/keys/rotation-policy', methods=['PUT'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def update_rotation_policy_endpoint():
    """
    Update key rotation policy.
    
    Request JSON:
        {
            "enabled": true,
            "rotation_type": "time_based",
            "rotation_interval_days": 90,
            "auto_rotation": true,
            "pre_rotation_warning_days": 7,
            "device_filters": {
                "device_types": ["sensor", "gateway"],
                "organizations": ["org_123"]
            }
        }
    
    Returns:
        200: Policy updated
        400: Invalid request
        500: Update failed
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Policy data is required'}), 400
        
        # Validate rotation type
        rotation_type = data.get('rotation_type', 'time_based')
        if rotation_type not in ['time_based', 'event_based', 'manual']:
            return jsonify({'error': 'Invalid rotation type'}), 400
        
        # Validate rotation interval
        rotation_interval = data.get('rotation_interval_days', 90)
        if rotation_interval < 1 or rotation_interval > 365:
            return jsonify({'error': 'Rotation interval must be between 1 and 365 days'}), 400
        
        result = update_rotation_policy(
            policy_data=data,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error updating rotation policy: {e}")
        return jsonify({'error': 'Failed to update rotation policy', 'details': str(e)}), 500

@certificates_bp.route('/keys/status', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_key_lifecycle_status_endpoint():
    """
    Get key lifecycle monitoring status.
    
    Query Parameters:
        device_id: Specific device ID (optional)
        session_id: Specific session ID (optional)
        status: Filter by status (optional)
        
    Returns:
        200: Key lifecycle status
        500: Server error
    """
    try:
        device_id = request.args.get('device_id')
        session_id = request.args.get('session_id')
        status_filter = request.args.get('status')
        
        result = get_key_lifecycle_status(
            device_id=device_id,
            session_id=session_id,
            status_filter=status_filter,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting key lifecycle status: {e}")
        return jsonify({'error': 'Failed to retrieve key status', 'details': str(e)}), 500

@certificates_bp.route('/keys/sessions/<session_id>', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_key_generation_session_endpoint(session_id):
    """
    Get key generation session details.
    
    Args:
        session_id: Session identifier
        
    Returns:
        200: Session details
        404: Session not found
        500: Server error
    """
    try:
        result = get_key_generation_session(
            session_id=session_id,
            user=g.current_user
        )
        
        if not result:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting key generation session: {e}")
        return jsonify({'error': 'Failed to retrieve session', 'details': str(e)}), 500

@certificates_bp.route('/keys/distribution/status', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_key_distribution_status_endpoint():
    """
    Get key distribution status.
    
    Query Parameters:
        session_id: Session ID (optional)
        device_id: Device ID (optional)
        
    Returns:
        200: Distribution status
        500: Server error
    """
    try:
        session_id = request.args.get('session_id')
        device_id = request.args.get('device_id')
        
        result = get_key_distribution_status(
            session_id=session_id,
            device_id=device_id,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting key distribution status: {e}")
        return jsonify({'error': 'Failed to retrieve distribution status', 'details': str(e)}), 500

# Key Download and Escrow endpoints
@certificates_bp.route('/keys/download/<token>', methods=['GET'])
def download_key_with_token(token):
    """
    Download key using secure token.
    
    Args:
        token: Secure download token
        
    Returns:
        200: Key file download
        400: Invalid token
        404: Token not found or expired
        500: Download failed
    """
    try:
        db = get_db()
        
        # Find download token
        token_record = db.key_download_tokens.find_one({
            'token': token,
            'expires_at': {'$gt': datetime.now()}
        })
        
        if not token_record:
            return jsonify({'error': 'Invalid or expired token'}), 404
        
        # Check download limits
        if token_record['download_count'] >= token_record['max_downloads']:
            return jsonify({'error': 'Download limit exceeded'}), 400
        
        # Get key data
        key_record = db.device_keys.find_one({'key_id': token_record['key_id']})
        
        if not key_record:
            return jsonify({'error': 'Key not found'}), 404
        
        # Get key from Vault if available
        key_data = None
        if key_record.get('vault_path'):
            try:
                key_data = vault_key_service.retrieve_key_from_vault(
                    key_record['vault_path'],
                    {'email': 'download_service', 'role': 'system'}
                )
            except Exception as e:
                logger.warning(f"Failed to retrieve key from Vault: {e}")
        
        # Update download count
        db.key_download_tokens.update_one(
            {'token': token},
            {
                '$inc': {'download_count': 1},
                '$set': {'last_downloaded_at': datetime.now()},
                '$push': {
                    'download_history': {
                        'timestamp': datetime.now(),
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'success': True
                    }
                }
            }
        )
        
        # Create key bundle
        device_id = key_record['device_id']
        algorithm = key_record['algorithm']
        
        if key_data and key_data.get('private_key_pem'):
            # Full key bundle with private key
            key_bundle = {
                'device_id': device_id,
                'algorithm': algorithm,
                'generated_at': key_record['generated_at'].isoformat(),
                'expires_at': key_record['expires_at'].isoformat(),
                'private_key': key_data['private_key_pem'],
                'public_key': key_data['public_key_pem'],
                'fingerprint': key_record['key_fingerprint']
            }
        else:
            # Public key only bundle
            key_bundle = {
                'device_id': device_id,
                'algorithm': algorithm,
                'generated_at': key_record['generated_at'].isoformat(),
                'expires_at': key_record['expires_at'].isoformat(),
                'public_key': key_record['public_key_pem'],
                'fingerprint': key_record['key_fingerprint'],
                'note': 'Private key requires additional authorization'
            }
        
        # Return as JSON file download
        response = Response(
            json.dumps(key_bundle, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={device_id}-key-bundle.json',
                'Content-Type': 'application/json'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading key: {e}")
        return jsonify({'error': 'Failed to download key', 'details': str(e)}), 500

@certificates_bp.route('/keys/escrow', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def escrow_key_endpoint():
    """
    Escrow a key with specific release conditions.
    
    Request JSON:
        {
            "device_id": "device_001",
            "key_id": "key_123",
            "escrow_conditions": {
                "requires_approval": true,
                "authorized_users": ["admin@example.com"],
                "expiry_hours": 168,
                "release_reason_required": true
            }
        }
    
    Returns:
        200: Key escrowed successfully
        400: Invalid request
        404: Key not found
        500: Escrow failed
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        device_id = data.get('device_id')
        key_id = data.get('key_id')
        escrow_conditions = data.get('escrow_conditions', {})
        
        if not device_id or not key_id:
            return jsonify({'error': 'device_id and key_id are required'}), 400
        
        result = key_escrow_service.escrow_key(
            device_id=device_id,
            key_id=key_id,
            organization_id=g.current_user.get('organization_id'),
            escrow_conditions=escrow_conditions,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error escrowing key: {e}")
        return jsonify({'error': 'Failed to escrow key', 'details': str(e)}), 500

@certificates_bp.route('/keys/escrow/<escrow_id>/release', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def release_escrowed_key_endpoint(escrow_id):
    """
    Release an escrowed key.
    
    Args:
        escrow_id: Escrow identifier
        
    Request JSON:
        {
            "release_token": "secure_token_here",
            "release_reason": "Maintenance required"
        }
    
    Returns:
        200: Key released successfully
        400: Invalid request
        403: Not authorized
        404: Escrow not found
        500: Release failed
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        release_token = data.get('release_token')
        release_reason = data.get('release_reason', '')
        
        if not release_token:
            return jsonify({'error': 'release_token is required'}), 400
        
        result = key_escrow_service.release_escrowed_key(
            escrow_id=escrow_id,
            release_token=release_token,
            release_reason=release_reason,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error releasing escrowed key: {e}")
        return jsonify({'error': 'Failed to release key', 'details': str(e)}), 500

@certificates_bp.route('/keys/escrow/<escrow_id>', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_escrow_status_endpoint(escrow_id):
    """
    Get escrow status information.
    
    Args:
        escrow_id: Escrow identifier
        
    Returns:
        200: Escrow status
        404: Escrow not found
        403: Not authorized
        500: Server error
    """
    try:
        result = key_escrow_service.get_escrow_status(
            escrow_id=escrow_id,
            user=g.current_user
        )
        
        if not result:
            return jsonify({'error': 'Escrow not found'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting escrow status: {e}")
        return jsonify({'error': 'Failed to get escrow status', 'details': str(e)}), 500

@certificates_bp.route('/keys/escrow', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def list_escrows_endpoint():
    """
    List escrows for the current organization.
    
    Query Parameters:
        status: Filter by status (optional)
        
    Returns:
        200: List of escrows
        500: Server error
    """
    try:
        status_filter = request.args.get('status')
        
        result = key_escrow_service.list_organization_escrows(
            organization_id=g.current_user.get('organization_id'),
            user=g.current_user,
            status_filter=status_filter
        )
        
        return jsonify({'escrows': result}), 200
        
    except Exception as e:
        logger.error(f"Error listing escrows: {e}")
        return jsonify({'error': 'Failed to list escrows', 'details': str(e)}), 500

# Note: Public Key Registration endpoints have been moved to the devices controller
# for better organization and proper URL routing (/api/v1/devices/{device_id}/public-key)

@certificates_bp.route('/bulk/regenerate', methods=['POST'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def bulk_certificate_regeneration_endpoint():
    """
    Enhanced bulk certificate regeneration with automatic encryption key generation.
    
    Request JSON:
        {
            "filters": {
                "organization_id": "org_123",
                "device_type": ["sensor", "gateway"],
                "tags": ["production"],
                "expiring_within_days": 30,
                "certificate_status": "valid"
            },
            "options": {
                "validity_days": 365,
                "key_algorithm": "RSA-2048",
                "enable_encryption": true,
                "batch_size": 100,
                "parallel_workers": 4
            }
        }
    
    Returns:
        200: Bulk job created successfully
        400: Invalid request
        403: Not authorized
        500: Server error
    """
    try:
        from ..services.certificate_service import (
            perform_enhanced_bulk_certificate_regeneration
        )
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        device_filters = data.get('filters', {})
        options = data.get('options', {})
        
        # Add organization filter for non-super admins
        if g.current_user.get('role') != 'super_admin':
            device_filters['organization_id'] = g.current_user.get('organization_id')
        
        # Create bulk job
        result = perform_enhanced_bulk_certificate_regeneration(
            device_filters=device_filters,
            options=options,
            user=g.current_user
        )
        
        return jsonify(result), 200
        
    except PermissionError as e:
        return jsonify({'error': str(e)}), 403
    except Exception as e:
        logger.error(f"Error creating bulk certificate regeneration job: {e}")
        return jsonify({'error': 'Failed to create bulk job', 'details': str(e)}), 500

@certificates_bp.route('/bulk/jobs/<job_id>', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_bulk_job_status_endpoint(job_id):
    """
    Get the status of a bulk certificate regeneration job.
    
    Args:
        job_id: The job ID to check
        
    Returns:
        200: Job status information
        404: Job not found
        403: Not authorized
        500: Server error
    """
    try:
        from ..services.certificate_service import get_bulk_job_status
        
        result = get_bulk_job_status(job_id, g.current_user)
        
        if result.get('error') == 'Job not found':
            return jsonify(result), 404
        elif result.get('error') == 'Access denied':
            return jsonify(result), 403
        elif result.get('error'):
            return jsonify(result), 500
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting bulk job status: {e}")
        return jsonify({'error': 'Failed to get job status', 'details': str(e)}), 500

@certificates_bp.route('/bulk/jobs/<job_id>', methods=['DELETE'])
@require_auth
@require_permission(Permission.CERTIFICATE_CREATE)
def cancel_bulk_job_endpoint(job_id):
    """
    Cancel a running bulk certificate regeneration job.
    
    Args:
        job_id: The job ID to cancel
        
    Returns:
        200: Job cancelled successfully
        404: Job not found
        403: Not authorized
        400: Job cannot be cancelled
        500: Server error
    """
    try:
        from ..services.certificate_service import cancel_bulk_job
        
        result = cancel_bulk_job(job_id, g.current_user)
        
        if result.get('error') == 'Job not found':
            return jsonify(result), 404
        elif result.get('error') == 'Access denied':
            return jsonify(result), 403
        elif result.get('error'):
            return jsonify(result), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error cancelling bulk job: {e}")
        return jsonify({'error': 'Failed to cancel job', 'details': str(e)}), 500

@certificates_bp.route('/bulk/jobs', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def list_bulk_jobs_endpoint():
    """
    List bulk certificate regeneration jobs for the organization.
    
    Query Parameters:
        status: Filter by status (initializing, queued, processing, completed, failed, cancelled)
        limit: Maximum number of results (default: 20)
        skip: Number of results to skip (default: 0)
        
    Returns:
        200: List of bulk jobs
        500: Server error
    """
    try:
        from ..core.database import get_db
        
        db = get_db()
        
        # Parse query parameters
        status_filter = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        skip = int(request.args.get('skip', 0))
        
        # Build query
        query = {}
        if g.current_user.get('role') != 'super_admin':
            query['organization_id'] = g.current_user.get('organization_id')
        
        if status_filter:
            query['status'] = status_filter
        
        # Get jobs
        jobs_cursor = db.certificate_bulk_jobs.find(query).sort('created_at', -1).skip(skip).limit(limit)
        jobs = []
        
        for job in jobs_cursor:
            jobs.append({
                'job_id': job['_id'],
                'type': job.get('type'),
                'status': job.get('status'),
                'created_at': job.get('created_at'),
                'created_by': job.get('created_by'),
                'statistics': job.get('statistics', {}),
                'filters': job.get('filters', {}),
                'options': job.get('options', {})
            })
        
        # Get total count
        total_count = db.certificate_bulk_jobs.count_documents(query)
        
        return jsonify({
            'jobs': jobs,
            'total': total_count,
            'limit': limit,
            'skip': skip
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing bulk jobs: {e}")
        return jsonify({'error': 'Failed to list jobs', 'details': str(e)}), 500

@certificates_bp.route('/ca', methods=['GET'])
@require_auth
def get_ca_information():
    """Get CA certificate information and status."""
    try:
        from ..services.local_certificate_generator import create_local_certificate_generator
        
        ca_info = {
            'ca_available': False,
            'ca_type': 'unknown',
            'ca_subject': None,
            'ca_issuer': None,
            'ca_valid_from': None,
            'ca_valid_to': None,
            'ca_fingerprint': None,
            'ca_serial': None
        }
        
        # Check if using local CA
        use_local_ca = os.getenv('USE_LOCAL_CA', 'false').lower() == 'true'
        
        if use_local_ca:
            generator = create_local_certificate_generator()
            if generator and hasattr(generator, 'ca_certificate'):
                try:
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    
                    ca_cert = x509.load_pem_x509_certificate(
                        generator.ca_certificate.encode('utf-8'),
                        default_backend()
                    )
                    
                    ca_info.update({
                        'ca_available': True,
                        'ca_type': 'local',
                        'ca_subject': ca_cert.subject.rfc4514_string(),
                        'ca_issuer': ca_cert.issuer.rfc4514_string(),
                        'ca_valid_from': ca_cert.not_valid_before.isoformat(),
                        'ca_valid_to': ca_cert.not_valid_after.isoformat(),
                        'ca_fingerprint': ca_cert.fingerprint(hashes.SHA256()).hex(),
                        'ca_serial': str(ca_cert.serial_number)
                    })
                except Exception as parse_error:
                    logger.error(f"Error parsing local CA certificate: {parse_error}")
        
        # Try Vault if local CA not available
        if not ca_info['ca_available']:
            vault = get_vault()
            if vault:
                try:
                    ca_cert_response = vault.read('pki-int/cert/ca')
                    if ca_cert_response and 'data' in ca_cert_response:
                        ca_info.update({
                            'ca_available': True,
                            'ca_type': 'vault',
                            'ca_subject': 'Vault PKI CA',
                            'ca_issuer': 'HashiCorp Vault'
                        })
                except Exception as vault_error:
                    logger.error(f"Error checking Vault CA: {vault_error}")
        
        return jsonify(ca_info), 200
        
    except Exception as e:
        logger.error(f"Error getting CA information: {e}")
        return jsonify({'error': 'Failed to get CA information'}), 500

@certificates_bp.route('/pending', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_pending_certificates():
    """Get pending certificate requests."""
    try:
        db = get_db()
        
        # Build query for pending certificates
        query = {
            'status': {'$in': ['pending', 'requested', 'processing']}
        }
        
        # Add organization filter for non-super-admin users
        if g.current_user.get('role') != 'super_admin':
            query['organization_id'] = g.current_user.get('organization_id')
        
        # Get pending certificates
        pending_certs = list(db.device_certificates.find(query).sort('requested_at', -1))
        
        # Format response
        certificates = []
        for cert in pending_certs:
            certificates.append({
                'certificate_id': str(cert.get('_id')),
                'device_id': cert.get('device_id'),
                'device_name': cert.get('device_name'),
                'status': cert.get('status'),
                'requested_at': cert.get('requested_at'),
                'requested_by': cert.get('requested_by'),
                'certificate_type': cert.get('certificate_type', 'device'),
                'algorithm': cert.get('algorithm'),
                'key_size': cert.get('key_size'),
                'valid_days': cert.get('valid_days'),
                'organization_id': cert.get('organization_id')
            })
        
        return jsonify({
            'pending_certificates': certificates,
            'total': len(certificates),
            'organization_id': g.current_user.get('organization_id')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting pending certificates: {e}")
        return jsonify({'error': 'Failed to get pending certificates'}), 500

@certificates_bp.route('/ca-chain', methods=['GET'])
@require_auth
def download_ca_chain():
    """
    Download the CA certificate chain for Server-TLS authentication.
    
    Returns:
        200: CA certificate chain file
        500: Server error
    """
    try:
        from ..services.local_certificate_generator import create_local_certificate_generator
        from pathlib import Path
        
        # Check if using local CA
        use_local_ca = os.getenv('USE_LOCAL_CA', 'false').lower() == 'true'
        
        if use_local_ca:
            # Get CA chain from local certificate generator
            generator = create_local_certificate_generator()
            if generator and hasattr(generator, 'ca_chain'):
                ca_chain_content = generator.ca_chain
                
                # Return as downloadable file
                response = Response(
                    ca_chain_content,
                    mimetype='application/x-pem-file',
                    headers={
                        'Content-Disposition': 'attachment; filename=tesa-ca-chain.pem',
                        'Content-Type': 'application/x-pem-file'
                    }
                )
                
                # Log the download
                audit_log(
                    user=g.current_user,
                    action=AuditAction.CERTIFICATE_DOWNLOAD,
                    resource_type='ca_certificate',
                    resource_id='ca-chain',
                    details={'type': 'ca_chain', 'source': 'local_ca'}
                )
                
                return response
        
        # If not using local CA, try to get from Vault
        vault = get_vault()
        if vault:
            try:
                # Read CA certificate from Vault
                ca_cert_response = vault.read('pki-int/cert/ca')
                if ca_cert_response and 'data' in ca_cert_response:
                    ca_chain_content = ca_cert_response['data'].get('certificate', '')
                    
                    # Return as downloadable file
                    response = Response(
                        ca_chain_content.encode('utf-8'),
                        mimetype='application/x-pem-file',
                        headers={
                            'Content-Disposition': 'attachment; filename=tesa-ca-chain.pem',
                            'Content-Type': 'application/x-pem-file'
                        }
                    )
                    
                    # Log the download
                    audit_log(
                        user=g.current_user,
                        action=AuditAction.CERTIFICATE_DOWNLOAD,
                        resource_type='ca_certificate',
                        resource_id='ca-chain',
                        details={'type': 'ca_chain', 'source': 'vault'}
                    )
                    
                    return response
            except Exception as vault_error:
                logger.error(f"Error getting CA from Vault: {vault_error}")
        
        # Fallback: Try to read from file system
        ca_paths = [
            Path('/usr/local/tesa/certs/ca-chain.crt'),
            Path('/app/certs/ca-chain.crt'),
            Path('./certs/ca-chain.crt')
        ]
        
        for ca_path in ca_paths:
            if ca_path.exists():
                with open(ca_path, 'rb') as f:
                    ca_chain_content = f.read()
                
                response = Response(
                    ca_chain_content,
                    mimetype='application/x-pem-file',
                    headers={
                        'Content-Disposition': 'attachment; filename=tesa-ca-chain.pem',
                        'Content-Type': 'application/x-pem-file'
                    }
                )
                
                # Log the download
                audit_log(
                    user=g.current_user,
                    action=AuditAction.CERTIFICATE_DOWNLOAD,
                    resource_type='ca_certificate',
                    resource_id='ca-chain',
                    details={'type': 'ca_chain', 'source': 'filesystem', 'path': str(ca_path)}
                )
                
                return response
        
        return jsonify({'error': 'CA certificate chain not found'}), 404
        
    except Exception as e:
        logger.error(f"Error downloading CA chain: {e}")
        return jsonify({'error': 'Failed to download CA certificate chain', 'details': str(e)}), 500


@certificates_bp.route('/ca-chain/health', methods=['GET'])
@require_auth
def get_ca_chain_health():
    """Return CA chain metadata. Restricted to platform administrators."""
    user_role = g.current_user.get('role')
    if user_role not in ('platform_admin', 'super_admin'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        metadata = get_ca_chain_metadata()
        return jsonify(metadata)
    except Exception as exc:
        logger.error(f"Error fetching CA chain metadata: {exc}")
        return jsonify({'error': 'Failed to fetch CA chain metadata'}), 500

@certificates_bp.route('/public/ca-certificate', methods=['GET'])
def download_public_ca_certificate():
    """
    Download the CA certificate for Server-TLS authentication.
    This is a public endpoint that doesn't require authentication.
    
    Returns:
        200: CA certificate file
        404: CA certificate not found
        500: Server error
    """
    try:
        from pathlib import Path
        
        # Primary path: The actual CA chain used by EMQX for Server-TLS
        ca_chain_path = Path('/opt/emqx/etc/certs/chain/ca-chain.crt')
        
        # Fallback paths in order of preference
        fallback_paths = [
            Path('/app/certs/chain/ca-chain.crt'),
            Path('/usr/local/tesa/certs/ca-chain.crt'),
            Path('./config/certificates/certs/emqx/chain/ca-chain.crt'),
            Path('./certs/ca-chain.crt')
        ]
        
        # Try primary path first
        ca_content = None
        used_path = None
        
        if ca_chain_path.exists():
            with open(ca_chain_path, 'rb') as f:
                ca_content = f.read()
            used_path = ca_chain_path
        else:
            # Try fallback paths
            for path in fallback_paths:
                if path.exists():
                    with open(path, 'rb') as f:
                        ca_content = f.read()
                    used_path = path
                    break
        
        if ca_content:
            # Log the public download (no user info since it's public)
            logger.info(f"Public CA certificate downloaded from {used_path}")
            
            # Return CA certificate with appropriate headers
            response = Response(
                ca_content,
                mimetype='application/x-pem-file',
                headers={
                    'Content-Disposition': 'attachment; filename=tesa-iot-ca-certificate.pem',
                    'Content-Type': 'application/x-pem-file',
                    'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                    'X-Certificate-Type': 'CA-Certificate',
                    'X-Certificate-Usage': 'Server-TLS-Authentication'
                }
            )
            
            return response
        
        # If no CA certificate found
        logger.error("CA certificate not found in any expected location")
        return jsonify({
            'error': 'CA certificate not found',
            'message': 'The CA certificate required for Server-TLS authentication is not available'
        }), 404
        
    except Exception as e:
        logger.error(f"Error downloading public CA certificate: {e}")
        return jsonify({
            'error': 'Failed to download CA certificate',
            'message': 'An error occurred while retrieving the CA certificate'
        }), 500


# Certificate TTL validation endpoints

# TTL constraints (in days)
TTL_MIN_DAYS = 1
TTL_MAX_DAYS = 1095  # 3 years
TTL_REQUIRES_JUSTIFICATION = 365  # 1 year
TTL_REQUIRES_APPROVAL = 730  # 2 years
TTL_RECOMMENDED = 90  # Industry standard

def calculate_ttl_security_score(ttl_days):
    """Calculate security score (1-10) based on TTL."""
    if ttl_days <= 30:
        return 10
    elif ttl_days <= 90:
        return 8
    elif ttl_days <= 180:
        return 6
    elif ttl_days <= 365:
        return 4
    elif ttl_days <= 730:
        return 2
    else:
        return 1

def get_ttl_risk_level(ttl_days):
    """Determine risk level based on TTL."""
    if ttl_days <= 7:
        return 'none'  # Development/testing
    elif ttl_days <= 90:
        return 'low'
    elif ttl_days <= 365:
        return 'medium'
    elif ttl_days <= 1095:
        return 'high'
    else:
        return 'critical'

def check_ttl_compliance(ttl_days):
    """Check compliance with various security standards."""
    return {
        'iso_27001': ttl_days <= 365,
        'etsi_en_303_645': ttl_days <= 365,
        'nist_recommended': ttl_days <= 90,
        'ca_browser_forum': ttl_days <= 398,
        'industry_best_practice': ttl_days <= 90
    }

@certificates_bp.route('/validate-ttl', methods=['POST'])
@require_auth
def validate_certificate_ttl():
    """
    Validate certificate TTL based on security policies.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ttl_days = data.get('ttl_days')
        if ttl_days is None:
            return jsonify({'error': 'ttl_days is required'}), 400
        
        try:
            ttl_days = int(ttl_days)
        except (TypeError, ValueError):
            return jsonify({'error': 'ttl_days must be an integer'}), 400
        
        device_type = data.get('device_type', 'unknown')
        deployment_context = data.get('deployment_context', 'unknown')
        justification = data.get('justification', '')
        
        # Validation result
        result = {
            'valid': False,
            'ttl_days': ttl_days,
            'requires_justification': False,
            'requires_approval': False,
            'security_score': 0,
            'risk_level': 'unknown',
            'compliance': {},
            'warnings': [],
            'recommendations': [],
            'errors': []
        }
        
        # Validate TTL range
        if ttl_days < TTL_MIN_DAYS:
            result['errors'].append(f'TTL must be at least {TTL_MIN_DAYS} day')
            return jsonify(result), 400
        
        if ttl_days > TTL_MAX_DAYS:
            result['errors'].append(f'TTL exceeds maximum allowed ({TTL_MAX_DAYS} days)')
            result['recommendations'].append('Consider implementing certificate rotation instead')
            return jsonify(result), 400
        
        # Calculate metrics
        result['security_score'] = calculate_ttl_security_score(ttl_days)
        result['risk_level'] = get_ttl_risk_level(ttl_days)
        result['compliance'] = check_ttl_compliance(ttl_days)
        
        # Check if justification is required
        if ttl_days > TTL_REQUIRES_JUSTIFICATION:
            result['requires_justification'] = True
            if len(justification) < 100:
                result['warnings'].append('Justification required for TTL > 365 days (minimum 100 characters)')
        
        # Check if approval is required
        if ttl_days > TTL_REQUIRES_APPROVAL:
            result['requires_approval'] = True
            result['warnings'].append('Approval required from security team for TTL > 730 days')
        
        # Add warnings based on TTL
        if ttl_days > 365:
            result['warnings'].append('AWS, Azure, and Google Cloud recommend against certificates > 1 year')
            result['warnings'].append('Consider automatic certificate rotation for better security')
        elif ttl_days > 90:
            result['recommendations'].append(f'Industry standard is moving to {TTL_RECOMMENDED} days')
        
        # Add recommendations based on device type
        if device_type == 'sensor' and ttl_days > 90:
            result['recommendations'].append('IoT sensors typically use 30-90 day certificates')
        elif device_type == 'gateway' and ttl_days < 30:
            result['recommendations'].append('Gateways can typically use 90-day certificates')
        
        # Add deployment context recommendations
        if deployment_context == 'data_center' and ttl_days > 30:
            result['recommendations'].append('Data center devices with reliable connectivity can use 30-day certificates')
        elif deployment_context == 'remote' and ttl_days < 365:
            result['recommendations'].append('Remote devices may benefit from longer TTL to reduce maintenance')
        
        # Mark as valid if within allowed range
        result['valid'] = True
        
        # Log validation
        audit_log(
            user=g.current_user,
            action=AuditAction.CERTIFICATE_VALIDATE,
            resource_type='certificate_ttl',
            resource_id=str(ttl_days),
            details={
                'ttl_days': ttl_days,
                'risk_level': result['risk_level'],
                'security_score': result['security_score']
            }
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error validating certificate TTL: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@certificates_bp.route('/ttl-policies', methods=['GET'])
@require_auth
def get_ttl_policies():
    """Get organization's certificate TTL policies."""
    try:
        # Get organization-specific policies if available
        db = get_db()
        org_id = g.current_user.get('organization_id')
        
        # Try to get organization-specific policies
        if org_id:
            org_policies = db.certificate_policies.find_one({'organization_id': org_id})
            if org_policies:
                return jsonify({
                    'min_ttl_days': org_policies.get('min_ttl_days', TTL_MIN_DAYS),
                    'max_ttl_days': org_policies.get('max_ttl_days', TTL_MAX_DAYS),
                    'default_ttl_days': org_policies.get('default_ttl_days', TTL_RECOMMENDED),
                    'requires_justification_days': org_policies.get('requires_justification_days', TTL_REQUIRES_JUSTIFICATION),
                    'requires_approval_days': org_policies.get('requires_approval_days', TTL_REQUIRES_APPROVAL),
                    'auto_renewal_enabled': org_policies.get('auto_renewal_enabled', True),
                    'renewal_threshold_days': org_policies.get('renewal_threshold_days', 5)
                }), 200
        
        # Return default policies
        policies = {
            'min_ttl_days': TTL_MIN_DAYS,
            'max_ttl_days': TTL_MAX_DAYS,
            'default_ttl_days': TTL_RECOMMENDED,
            'requires_justification_days': TTL_REQUIRES_JUSTIFICATION,
            'requires_approval_days': TTL_REQUIRES_APPROVAL,
            'auto_renewal_enabled': True,
            'renewal_threshold_days': 5,
            'presets': [
                {
                    'value': 7,
                    'label': 'Development',
                    'description': 'For testing only',
                    'risk_level': 'none'
                },
                {
                    'value': 30,
                    'label': 'High Security',
                    'description': 'For critical infrastructure',
                    'risk_level': 'low'
                },
                {
                    'value': 90,
                    'label': 'Standard',
                    'description': 'Industry recommended',
                    'risk_level': 'low'
                },
                {
                    'value': 365,
                    'label': 'Remote Deployment',
                    'description': 'For devices with limited connectivity',
                    'risk_level': 'medium'
                }
            ],
            'industry_trends': {
                'current_standard': 398,
                'future_2025': 90,
                'future_2029': 47
            }
        }
        
        return jsonify(policies), 200
        
    except Exception as e:
        logger.error(f"Error getting TTL policies: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Certificate Rotation History Endpoints (Added 2026-01-05)
# ============================================================================

@certificates_bp.route('/rotation-history', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_certificate_rotation_history():
    """
    Get certificate rotation history for all devices in the organization.
    Used by the Reports tab in Certificate Management UI.

    Query Parameters:
        start: Start date (ISO format)
        end: End date (ISO format)
        device_id: Filter by specific device (optional)
        device_type: Filter by device type (optional)
        action: Filter by action type (renewed, revoked, issued) (optional)
        limit: Maximum number of records (default: 100, max: 500)
        offset: Pagination offset (default: 0)

    Returns:
        200: List of rotation history events
        500: Server error
    """
    try:
        db = get_db()

        # Get query parameters
        start_date = request.args.get('start')
        end_date = request.args.get('end')
        device_id = request.args.get('device_id')
        device_type = request.args.get('device_type')
        action_filter = request.args.get('action')
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))

        # Build query
        query = {}

        # Organization filter
        org_id = g.current_user.get('organization_id')
        if org_id and g.current_user.get('role') not in ['super_admin', 'platform_admin']:
            # Get all device_ids for this organization
            org_devices = list(db.devices.find({'organization_id': org_id}, {'device_id': 1}))
            org_device_ids = [d['device_id'] for d in org_devices]
            query['device_id'] = {'$in': org_device_ids}

        # Date range filter
        if start_date or end_date:
            date_query = {}
            if start_date:
                try:
                    date_query['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except:
                    pass
            if end_date:
                try:
                    date_query['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except:
                    pass
            if date_query:
                query['renewal_date'] = date_query

        # Device ID filter
        if device_id:
            query['device_id'] = device_id

        # Action filter - filter by 'action' field (issued, renewed, revoked)
        # Note: 'method' field stores how the cert was created (csr, api, etc.)
        if action_filter:
            query['action'] = action_filter

        # Get total count
        total_count = db.certificate_renewal_history.count_documents(query)

        # Get history records
        history_cursor = db.certificate_renewal_history.find(query).sort(
            'renewal_date', -1
        ).skip(offset).limit(limit)

        history_list = []

        # Get device names for enrichment
        device_names = {}

        for record in history_cursor:
            record_id = str(record.get('_id', ''))
            device_id_val = record.get('device_id', '')

            # Get device name if not cached
            if device_id_val and device_id_val not in device_names:
                device = db.devices.find_one({'device_id': device_id_val}, {'name': 1, 'device_type': 1})
                if device:
                    device_names[device_id_val] = {
                        'name': device.get('name', device_id_val),
                        'type': device.get('device_type', 'sensor')
                    }
                else:
                    device_names[device_id_val] = {'name': device_id_val, 'type': 'unknown'}

            # Apply device_type filter if specified
            if device_type and device_names.get(device_id_val, {}).get('type') != device_type:
                continue

            # Format timestamp with timezone awareness
            # Pipeline-generated records (hsm_protected_update, hsm_csr) store in UTC
            # Software CSR workflows (sw_csr) store in server local time (Asia/Bangkok +7)
            renewal_date = record.get('renewal_date')
            provisioning_method = record.get('provisioning_method')
            if renewal_date:
                if renewal_date.tzinfo is not None:
                    # Already timezone-aware, convert to UTC
                    ts_str = renewal_date.astimezone(timezone.utc).isoformat()
                elif provisioning_method in ('hsm_protected_update', 'hsm_csr'):
                    # Pipeline records (both PU and CSR) store timestamps in UTC
                    ts_str = renewal_date.replace(tzinfo=timezone.utc).isoformat()
                else:
                    # Software CSR/SW workflows store in server local time (Bangkok +7)
                    # Convert to UTC by subtracting 7 hours offset
                    utc_dt = renewal_date - timedelta(hours=7)
                    ts_str = utc_dt.replace(tzinfo=timezone.utc).isoformat()
            else:
                ts_str = None

            history_list.append({
                'id': record_id,
                'device_id': device_id_val,
                'device_name': device_names.get(device_id_val, {}).get('name', device_id_val),
                'device_type': device_names.get(device_id_val, {}).get('type', 'unknown'),
                # Use 'action' field (issued, renewed, revoked) not 'method' (csr, api, etc.)
                'action': record.get('action') or record.get('method', 'renewal'),
                'timestamp': ts_str,
                'serial_number': _normalize_serial(record.get('serial_number') or record.get('new_serial') or record.get('old_serial')),
                'old_serial': _normalize_serial(record.get('old_serial') or record.get('old_certificate_serial')),
                'new_serial': _normalize_serial(record.get('new_serial') or record.get('new_certificate_serial')),
                'algorithm': record.get('algorithm'),
                'validity_days': record.get('validity_days'),
                'issued_by': record.get('issued_by') or record.get('initiated_by', 'system'),
                'reason': record.get('reason', ''),
                'status': record.get('status', 'completed'),
                # Provisioning method: sw_csr, hsm_csr, or hsm_protected_update
                'provisioning_method': provisioning_method
            })

        # Sort by UTC-normalized timestamp (descending) - MongoDB sort doesn't account for timezone
        # ISO 8601 format sorts correctly lexicographically when all timestamps have timezone
        history_list.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

        return jsonify({
            'success': True,
            'items': history_list,
            'total': total_count,
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        logger.error(f"Error getting rotation history: {str(e)}")
        return jsonify({'error': 'Failed to retrieve rotation history'}), 500


@certificates_bp.route('/devices/<device_id>/history', methods=['GET'])
@require_auth
@require_permission(Permission.CERTIFICATE_VIEW)
def get_device_certificate_history(device_id):
    """
    Get certificate history for a specific device.
    Used by the expandable row in Certificate Management UI.

    Args:
        device_id: Device identifier

    Query Parameters:
        limit: Maximum number of records (default: 10, max: 50)

    Returns:
        200: Certificate history for the device
        404: Device not found
        500: Server error
    """
    try:
        db = get_db()
        limit = min(int(request.args.get('limit', 10)), 50)

        # Verify device exists and user has access
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404

        # Check organization access
        org_id = g.current_user.get('organization_id')
        if org_id and g.current_user.get('role') not in ['super_admin', 'platform_admin']:
            if device.get('organization_id') != org_id:
                return jsonify({
                    'success': False,
                    'error': 'Access denied'
                }), 403

        # Get certificate history - use aggregation to sort by multiple timestamp fields
        # Old records have 'initiated_at', newer records have 'renewal_date' or 'timestamp'
        history_cursor = db.certificate_renewal_history.aggregate([
            {'$match': {'device_id': device_id}},
            {'$addFields': {
                'sort_timestamp': {
                    '$ifNull': ['$renewal_date', {'$ifNull': ['$timestamp', '$initiated_at']}]
                }
            }},
            {'$sort': {'sort_timestamp': -1}},
            {'$limit': limit}
        ])

        history_list = []
        for idx, record in enumerate(history_cursor):
            is_current = idx == 0  # First record is the most recent (current)

            # Handle different field naming conventions in historical records
            # Newer records use: serial_number, new_serial, old_serial
            # Some records may use: new_certificate_serial, old_certificate_serial
            serial = record.get('serial_number') or record.get('new_serial') or record.get('new_certificate_serial') or record.get('old_certificate_serial', '-')
            # Use renewal_date, timestamp, or initiated_at - whichever is available
            timestamp = record.get('renewal_date') or record.get('timestamp') or record.get('initiated_at')
            issued_by = record.get('issued_by') or record.get('requested_by') or record.get('initiated_by', 'system')

            # Format timestamp with timezone awareness
            # All timestamps are normalized to UTC for consistent sorting and display
            # Protected Update (hsm_protected_update) stores timestamps in UTC
            # CSR workflows store timestamps in server local time (Asia/Bangkok +7)
            provisioning_method = record.get('provisioning_method')
            if timestamp:
                if timestamp.tzinfo is not None:
                    # Already timezone-aware, convert to UTC
                    ts_str = timestamp.astimezone(timezone.utc).isoformat()
                elif provisioning_method == 'hsm_protected_update':
                    # Protected Update stores in UTC - mark as UTC
                    ts_str = timestamp.replace(tzinfo=timezone.utc).isoformat()
                else:
                    # CSR/SW workflows store in server local time (Bangkok +7)
                    # Convert to UTC by subtracting 7 hours offset
                    utc_dt = timestamp - timedelta(hours=7)
                    ts_str = utc_dt.replace(tzinfo=timezone.utc).isoformat()
            else:
                ts_str = None

            expires_at = record.get('expires_at')
            expires_str = expires_at.isoformat() if expires_at else None

            history_list.append({
                'id': str(record.get('_id', '')),
                'serial_number': _normalize_serial(serial),
                'timestamp': ts_str,  # Frontend expects 'timestamp'
                'issued_at': ts_str,  # Keep for compatibility
                'expires_at': expires_str,
                'validity_days': record.get('validity_days'),
                'action': record.get('action') or record.get('method', 'renewal'),
                'issued_by': issued_by,  # Frontend expects 'issued_by'
                'initiated_by': issued_by,  # Keep for compatibility
                'status': 'current' if is_current else record.get('status', 'rotated'),
                'reason': record.get('reason', ''),
                'algorithm': record.get('algorithm'),
                'old_serial': _normalize_serial(record.get('old_serial')),
                'new_serial': _normalize_serial(record.get('new_serial')),
                # Provisioning method: sw_csr, hsm_csr, or hsm_protected_update
                'provisioning_method': record.get('provisioning_method')
            })

        # Sort by UTC-normalized timestamp (descending) - MongoDB sort doesn't account for timezone
        # ISO 8601 format sorts correctly lexicographically when all timestamps have timezone
        history_list.sort(key=lambda x: x.get('timestamp') or '', reverse=True)

        # Get current certificate info from device
        # Handle both datetime objects and ISO string values for date fields
        issued_at_raw = device.get('certificate_issued_at')
        expires_at_raw = device.get('certificate_expires_at')
        current_cert = {
            'serial_number': device.get('certificate_serial'),
            'issued_at': issued_at_raw.isoformat() if hasattr(issued_at_raw, 'isoformat') else issued_at_raw,
            'expires_at': expires_at_raw.isoformat() if hasattr(expires_at_raw, 'isoformat') else expires_at_raw,
            'status': device.get('certificate_status', 'unknown'),
            'algorithm': device.get('certificate_algorithm', 'ECC-256')
        }

        return jsonify({
            'success': True,
            'device_id': device_id,
            'device_name': device.get('name', device_id),
            'current_certificate': current_cert,
            'history': history_list,
            'total_rotations': len(history_list)
        }), 200

    except Exception as e:
        logger.error(f"Error getting device certificate history for {device_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve certificate history'}), 500
