# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - MQTT Authentication Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




MQTT Webhook Authentication Service for EMQX Integration
Validates device certificates against Vault PKI in real-time
Implements Zero Trust Architecture for IoT device authentication
"""

import hmac
import logging
import os
from datetime import datetime

from ..core.database import get_db, get_vault

logger = logging.getLogger(__name__)

def _is_trustm_uid_format(client_id: str) -> bool:
    """
    Check if client_id is in Trust M UID format.

    Trust M UID format: 52+ character hex string (e.g., "CD16339301001C000500000A01BB820003004000AE801010712440")
    UUID format: 36 characters with dashes (e.g., "04284137-84be-4f86-8b91-d4d8fef51427")

    Returns True if client_id looks like a Trust M UID (long hex string without dashes).
    """
    if not client_id:
        return False

    # Trust M UIDs are typically 52+ hex characters without dashes
    # UUIDs are 36 characters with dashes in format 8-4-4-4-12
    if '-' in client_id:
        return False  # UUID format, not Trust M UID

    # Check if it's a long hex string (Trust M UID is typically 52 chars)
    if len(client_id) >= 40:
        try:
            int(client_id, 16)  # Try to parse as hex
            return True
        except ValueError:
            return False

    return False

def validate_mqtt_auth(webhook_data):
    """
    Validate MQTT authentication request from EMQX webhook.
    
    This implements the secure authentication flow:
    1. Device connects with certificate
    2. EMQX extracts certificate info
    3. EMQX calls webhook → API endpoint (this function)
    4. API validates with Vault PKI
    5. API returns accept/reject to EMQX
    6. EMQX allows/denies connection
    
    Args:
        webhook_data: Dictionary containing EMQX webhook payload
        
    Returns:
        dict: Authentication result with accept/reject decision
    """
    try:
        # Extract authentication data from EMQX webhook
        client_id = webhook_data.get('client_id', '')
        username = webhook_data.get('username', '')
        password = webhook_data.get('password', '')
        # Check for certificate in multiple possible fields
        peer_cert_pem = (
            webhook_data.get('peer_cert')
            or webhook_data.get('certificate')
            or webhook_data.get('cert_pem')
            or webhook_data.get('peer_cert_pem')
        )
        peer_cert = peer_cert_pem or ''
        if not peer_cert and (webhook_data.get('peer_cert_cn') or webhook_data.get('peer_cert_subject')):
            # If we have CN or subject, we have a certificate identifier even if PEM is missing
            peer_cert = webhook_data.get('peer_cert_subject', webhook_data.get('peer_cert_cn', ''))
        peer_cert_cn = webhook_data.get('peer_cert_cn', '')
        
        logger.info(f"MQTT auth request: client_id={client_id}, username={username}, cn={peer_cert_cn}, has_cert={bool(peer_cert)}, port={webhook_data.get('peerport', webhook_data.get('sockport', 'unknown'))}")
        
        # Step 1: Validate required fields
        if not client_id:
            logger.warning("Authentication failed: missing client_id")
            return _auth_reject("Missing client_id")
        
        # Step 1.5: Check for internal service accounts
        # These are trusted internal services that need to subscribe to device topics
        internal_service_patterns = [
            'mqtt-bridge',  # MQTT telemetry bridge (may have hostname suffix)
            'service-mqtt-bridge',  # EMQX may add service- prefix
            'grafana-mqtt',  # Grafana MQTT data source
            'analytics-service',  # Analytics service
            'tesa-protected-update-service',  # Protected update pipeline publisher
            'protected-update-service',
            'protected-update'
        ]

        is_internal_service = any(client_id.startswith(pattern) for pattern in internal_service_patterns)
        
        logger.info(f"Internal service check for {client_id}: {is_internal_service}")
        
        if is_internal_service:
            # FIXED: Always allow mqtt-bridge services for telemetry bridge functionality
            # Validate password for internal services  
            import os as os_module
            # Accept only credentials provided via environment. No hardcoded
            # fallbacks: if these are unset, internal-service auth fails closed.
            valid_passwords = [
                os_module.environ.get('MQTT_BRIDGE_PASSWORD'),  # Bridge service password
                os_module.environ.get('MQTT_PASSWORD'),  # MQTT_PASSWORD from .env
            ]

            protected_update_password = os_module.environ.get('PROTECTED_UPDATE_MQTT_PASSWORD')
            protected_update_username = os_module.environ.get('PROTECTED_UPDATE_MQTT_USERNAME')
            default_mqtt_password = os_module.environ.get('MQTT_PASSWORD')

            if client_id.startswith(('tesa-protected-update-service', 'protected-update')) or (
                protected_update_username and username == protected_update_username
            ):
                if protected_update_password:
                    valid_passwords.append(protected_update_password)
                if default_mqtt_password:
                    valid_passwords.append(default_mqtt_password)

            # Remove potential None values while preserving order
            valid_passwords = [pwd for pwd in valid_passwords if pwd]
            
            # Check if password matches any valid password
            if not password:
                logger.warning(f"Missing password for internal service: {client_id}")
                return _auth_reject("Authentication required for internal service")
            
            # Constant-time comparison against every candidate (no early
            # exit, no timing side channel from `in` substring/equality).
            password_ok = False
            for candidate in valid_passwords:
                if hmac.compare_digest(str(password), str(candidate)):
                    password_ok = True
            if not password_ok:
                logger.warning(f"Invalid password for internal service: {client_id}")
                return _auth_reject("Invalid credentials for internal service")
            
            logger.info(f"Internal service authenticated with valid credentials: {client_id}")
            return _auth_accept(f"Service account authenticated: {client_id}")

        # Step 2: Find device in database
        db = get_db()
        device = db.devices.find_one({'device_id': client_id})

        # Step 2.1: If not found by device_id, check if client_id is Trust M UID format
        # PSoC devices send Trust M UID as client_id (e.g., "CD16339301001C000500000A01BB820003004000AE801010712440")
        # But actual device_id in DB is a UUID (e.g., "04284137-84be-4f86-8b91-d4d8fef51427")
        # This fix prevents incorrect auto-registration when device exists but lookup fails
        if not device and _is_trustm_uid_format(client_id):
            logger.info(f"client_id '{client_id}' looks like Trust M UID, trying trustm_uid lookup...")
            device = db.devices.find_one({
                'trustm_uid': client_id,
                'status': {'$in': ['awaiting_first_connection', 'active']}
            })
            if device:
                logger.info(f"✓ Device found by trustm_uid: {client_id} -> device_id: {device.get('device_id')}")

        # Step 2.5: For Trust M devices, check for different identification methods
        if not device and peer_cert_cn:
            # Method 1: CN matches registered Trust M UID (e.g., hex string like "CD1633940100...")
            device = db.devices.find_one({'trustm_uid': peer_cert_cn})
            if device:
                logger.info(f"Device found by Trust M UID in CN: {peer_cert_cn} -> device_id: {device.get('device_id')}")

            # Method 2: Infineon factory certificate (CN = "InfineonIoTNode")
            # Use MQTT client_id as Trust M UID for pre-registered device lookup
            # NOTE: Removed 'peer_cert' requirement - EMQX doesn't always send cert_pem
            elif peer_cert_cn == "InfineonIoTNode":
                logger.info(f"Detected Infineon factory certificate for client_id: {client_id}")

                # Use client_id as Trust M UID (PSoC sends Trust M UID as client_id)
                trustm_uid = client_id

                if trustm_uid:
                    logger.info(f"Using client_id as Trust M UID: {trustm_uid}")

                    # Find pre-registered device by Trust M UID
                    device = db.devices.find_one({
                        'trustm_uid': trustm_uid,
                        'status': {'$in': ['awaiting_first_connection', 'active']}
                    })

                    if device:
                        logger.info(f"Found pre-registered Trust M device: {device.get('device_id')} (trustm_uid: {trustm_uid})")

                        # If this is first connection, activate the device
                        if device.get('status') == 'awaiting_first_connection':
                            logger.info(f"Activating pre-registered Trust M device: {device.get('device_id')}")

                            # Build update document
                            update_doc = {
                                'status': 'active',
                                'first_connected_at': datetime.now(),
                                'activated_at': datetime.now(),
                                'last_activity': datetime.now()
                            }

                            # Calculate certificate fingerprint if cert_pem is available
                            # NOTE: EMQX doesn't always send cert_pem in webhook
                            cert_fingerprint = None
                            if peer_cert:
                                import hashlib
                                cert_fingerprint = hashlib.sha256(peer_cert.encode()).hexdigest()
                                update_doc['factory_certificate'] = {
                                    'certificate': peer_cert,
                                    'fingerprint_sha256': cert_fingerprint,
                                    'serial': trustm_uid,
                                    'cn': peer_cert_cn,
                                    'issued_by': 'Infineon OPTIGA(TM) Trust M CA 300',
                                    'first_seen_at': datetime.now(),
                                    'active': True
                                }
                            else:
                                # No cert_pem available, store basic info only
                                logger.info(f"cert_pem not provided by EMQX, storing basic factory cert info")
                                update_doc['factory_certificate'] = {
                                    'serial': trustm_uid,
                                    'cn': peer_cert_cn,
                                    'issued_by': 'Infineon OPTIGA(TM) Trust M CA 300',
                                    'first_seen_at': datetime.now(),
                                    'active': True,
                                    'note': 'Full certificate not captured - EMQX did not provide cert_pem'
                                }

                            # Store factory certificate and activate
                            db.devices.update_one(
                                {'_id': device['_id']},
                                {'$set': update_doc}
                            )

                            # Reload device document with updated status
                            device = db.devices.find_one({'_id': device['_id']})

                            # Log activation
                            from .device_logs_service import device_logs_service
                            device_logs_service.add_device_log(
                                device_id=device.get('device_id'),
                                level='INFO',
                                message='Device activated via Infineon factory certificate',
                                log_type='security',
                                details={
                                    'trustm_uid': trustm_uid,
                                    'factory_cn': peer_cert_cn,
                                    'authentication_method': 'infineon_factory_certificate',
                                    'certificate_fingerprint': cert_fingerprint or 'not_captured'
                                },
                                source='mqtt_auth'
                            )

                            logger.info(f"✓ Trust M device activated successfully: {device.get('device_id')}")
                    else:
                        logger.warning(f"Trust M device not pre-registered: trustm_uid={trustm_uid}, client_id={client_id}")
                else:
                    logger.warning(f"Could not extract Trust M UID from Infineon factory certificate")

        if not device:
            # AUTO-REGISTRATION DISABLED (2026-01-17)
            # Security Policy: All devices MUST be pre-registered in the Platform before connecting
            # This prevents:
            # 1. Rogue devices from registering themselves
            # 2. Duplicate device records with incorrect IDs (e.g., Trust M UID as device_id)
            # 3. Unauthorized access to MQTT broker

            logger.warning(f"[SECURITY] Device not found and auto-registration is DISABLED: client_id={client_id}, cert_cn={peer_cert_cn}")

            # Log unauthorized device attempt for security audit
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=client_id,
                level='WARNING',
                message='Unregistered device attempted to connect - auto-registration disabled',
                log_type='security',
                details={
                    'client_id': client_id,
                    'cert_cn': peer_cert_cn,
                    'cert_subject': webhook_data.get('peer_cert_subject', ''),
                    'port': webhook_data.get('peerport', webhook_data.get('sockport', 1883)),
                    'policy': 'auto_registration_disabled',
                    'action': 'rejected'
                },
                source='mqtt_auth'
            )

            return _auth_reject(f"Device not registered. Please pre-register device in TESAIoT Platform first: {client_id}")
        
        # Step 3: Check device status
        device_status = device.get('status', 'inactive')
        if device_status not in ['active', 'online']:
            logger.warning(f"Authentication failed: device inactive: {client_id}")
            
            # Log inactive device attempt
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=client_id,
                level='WARNING',
                message=f'Authentication blocked - device status: {device_status}',
                log_type='security',
                details={
                    'current_status': device_status,
                    'port': webhook_data.get('peerport', webhook_data.get('sockport', 1883))
                },
                source='mqtt_auth'
            )
            
            return _auth_reject(f"Device not active: {device_status}")

        # Step 3.4: Defense-in-depth revocation gate (applies to ALL auth modes).
        # The broker's CRL (Vault pki-int) is the primary enforcement, but a
        # device whose certificate has been revoked must NEVER authenticate even
        # if the CRL has not yet refreshed. Fail CLOSED on revoked certs.
        if str(device.get('certificate_status', '')).lower() == 'revoked':
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=client_id,
                level='WARNING',
                message='Authentication blocked - certificate revoked',
                log_type='security',
                details={
                    'certificate_serial': device.get('certificate_serial'),
                    'revoked_at': str(device.get('certificate_revoked_at')),
                    'port': webhook_data.get('peerport', webhook_data.get('sockport', 8883))
                },
                source='mqtt_auth'
            )
            logger.warning(
                f"[SECURITY] Authentication denied - certificate revoked for device {client_id}"
            )
            return _auth_reject("Device certificate has been revoked")

        # Step 3.5: Determine authentication mode early
        auth_mode = (device.get('auth_mode') or 'mtls').lower()  # Default to mTLS for security
        is_trustm_mode = auth_mode == 'optiga_trust_mtls'
        logger.info(f"Device {client_id} authentication mode: {auth_mode}")
        
        # Step 4: Dual-mode authentication support based on auth_mode
        if auth_mode == 'server_tls':
            # Server-only TLS authentication (for devices like PSoC)
            logger.info(f"Device {client_id} configured for server-only TLS authentication")
            
            # Check if connection is on TLS port
            sockport = webhook_data.get('peerport', webhook_data.get('sockport', 1883))
            if sockport == 8883:
                logger.info(f"Device {client_id} connected on secure TLS port 8883")
            elif sockport == 1883:
                logger.warning(f"Device {client_id} with server_tls mode connected on non-TLS port 1883")
                # Allow it but log warning - some devices might not support TLS
            
            # Validate username/password
            if username and username != client_id:
                logger.warning(f"Username mismatch for server_tls auth: expected {client_id}, got {username}")
                return _auth_reject("Username must match client_id")
            
            # Check device password if configured
            # First check for hashed password (new secure method)
            if device.get('password_hash'):
                if not password:
                    logger.warning(f"Password required but not provided for device: {client_id}")
                    return _auth_reject("Password required for this device")
                
                # Verify hashed password
                try:
                    # Import SecurityUtils for password verification
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                    from security.security_utils import SecurityUtils
                    
                    if not SecurityUtils.verify_password(password, device['password_hash']):
                        logger.warning(f"Password authentication failed for device: {client_id}")
                        return _auth_reject("Invalid device credentials")
                    
                    logger.info(f"Password authentication successful for device: {client_id} (using hash)")
                except Exception as e:
                    logger.error(f"Failed to verify password hash, trying bcrypt: {e}")
                    # Try bcrypt verification as fallback
                    try:
                        import bcrypt
                        if not bcrypt.checkpw(password.encode('utf-8'), device['password_hash'].encode('utf-8')):
                            logger.warning(f"Password authentication failed for device: {client_id}")
                            return _auth_reject("Invalid device credentials")
                        logger.info(f"Password authentication successful for device: {client_id} (using bcrypt)")
                    except Exception as e2:
                        logger.error(f"Failed to verify password: {e2}")
                        return _auth_reject("Password verification error")
                        
            # Legacy plaintext password check (for backward compatibility)
            elif device.get('mqtt_password'):
                device_password = device['mqtt_password']
                if not password:
                    logger.warning(f"Password required but not provided for device: {client_id}")
                    return _auth_reject("Password required for this device")
                    
                if password != device_password:
                    logger.warning(f"Password authentication failed for device: {client_id}")
                    return _auth_reject("Invalid device credentials")
                    
                logger.info(f"Password authentication successful for device: {client_id} (legacy plaintext)")
                
                # Migrate to hashed password on successful authentication
                try:
                    logger.info(f"Migrating device {client_id} password to hash")
                    from .device_service import _migrate_password_to_hash
                    _migrate_password_to_hash(device['_id'], password)
                except Exception as e:
                    logger.warning(f"Failed to migrate password to hash: {e}")
            else:
                logger.info(f"No password configured for device: {client_id} - allowing connection")
            
            logger.info(f"Server-only TLS authentication successful for device: {client_id}")
            
        else:
            # mTLS authentication mode (default)
            logger.info(f"Device {client_id} configured for mTLS authentication")
            
            # Check if we have certificate CN/Subject from EMQX (Layer 1 already validated)
            # This is the PROPER Two-Layer Security: EMQX validates cert, we verify device
            if peer_cert_cn or webhook_data.get('peer_cert_subject'):
                # Option B: Certificate info in other fields (EMQX v5 format)
                # EMQX has ALREADY validated the certificate during TLS handshake (Layer 1)
                logger.info(f"Certificate info received - CN: {peer_cert_cn}, Subject: {webhook_data.get('peer_cert_subject')}")

                # Verify CN matches device ID pattern OR Trust M UID
                if peer_cert_cn and client_id:
                    cn_valid = False
                    auth_method = None

                    # Method 1: CN matches device_id (standard mTLS)
                    if client_id in peer_cert_cn or peer_cert_cn.startswith(client_id):
                        cn_valid = True
                        auth_method = 'device_id_match'

                    # Method 2: CN matches Trust M UID (Trust M factory certificate)
                    elif device.get('trustm_uid') and peer_cert_cn == device.get('trustm_uid'):
                        cn_valid = True
                        auth_method = 'trustm_uid_match'
                        logger.info(f"Trust M UID authentication: CN {peer_cert_cn} matches registered Trust M UID for device {client_id}")

                    # Method 3: Infineon factory certificate (CN = "InfineonIoTNode")
                    elif peer_cert_cn == "InfineonIoTNode" and device.get('trustm_uid'):
                        # For Infineon factory certificates:
                        # - CN is always "InfineonIoTNode" (not the device ID or Trust M UID)
                        # - client_id MUST match the registered Trust M UID
                        if client_id == device.get('trustm_uid'):
                            # Optionally verify fingerprint if factory cert was already stored
                            if device.get('factory_certificate', {}).get('active'):
                                if peer_cert:
                                    import hashlib
                                    cert_fingerprint = hashlib.sha256(peer_cert.encode()).hexdigest()
                                    stored_fingerprint = device.get('factory_certificate', {}).get('fingerprint_sha256')

                                    if cert_fingerprint == stored_fingerprint:
                                        cn_valid = True
                                        auth_method = 'infineon_factory_certificate_verified'
                                        logger.info(f"Infineon factory certificate authentication: fingerprint matches for device {client_id}")
                                    else:
                                        logger.warning(f"Infineon factory certificate fingerprint mismatch for device {client_id}")
                            else:
                                # First connection with factory certificate - trust it if client_id matches trustm_uid
                                cn_valid = True
                                auth_method = 'infineon_factory_certificate_first_connection'
                                logger.info(f"Infineon factory certificate first connection: client_id={client_id} matches registered trustm_uid")
                        else:
                            logger.warning(f"Infineon factory certificate: client_id={client_id} does not match trustm_uid={device.get('trustm_uid')}")

                    if cn_valid:
                        logger.info(f"mTLS authentication successful for device: {client_id} (CN: {peer_cert_cn}, method: {auth_method})")

                        # Log successful mTLS authentication
                        from .device_logs_service import device_logs_service
                        device_logs_service.add_device_log(
                            device_id=client_id,
                            level='INFO',
                            message='mTLS authentication successful (Two-Layer Security)',
                            log_type='security',
                            details={
                                'auth_mode': auth_mode,
                                'certificate_cn': peer_cert_cn,
                                'auth_method': auth_method,
                                'layer1_validation': 'EMQX TLS handshake',
                                'layer2_validation': 'Webhook CN verification',
                                'port': webhook_data.get('peerport', webhook_data.get('sockport', 8883))
                            },
                            source='mqtt_auth'
                        )
                    else:
                        logger.warning(f"Certificate CN mismatch: device {client_id}, CN: {peer_cert_cn}, Trust M UID: {device.get('trustm_uid')}")
                        return _auth_reject("Certificate CN does not match device ID or Trust M UID")
                else:
                    logger.info(f"mTLS authentication successful for device: {client_id} (certificate validated by EMQX)")
                    
            # Option A: Full certificate in peer_cert field (fallback for compatibility)
            elif peer_cert:
                # EMQX validated the certificate during TLS handshake
                logger.info(f"Certificate info received - CN: {peer_cert_cn}, Subject: {webhook_data.get('peer_cert_subject')}")

                # Verify CN matches device ID pattern OR Trust M UID
                if peer_cert_cn and client_id:
                    cn_valid = False
                    auth_method = None

                    # Method 1: CN matches device_id (standard mTLS)
                    if client_id in peer_cert_cn or peer_cert_cn.startswith(client_id):
                        cn_valid = True
                        auth_method = 'device_id_match'

                    # Method 2: CN matches Trust M UID (Trust M factory certificate)
                    elif device.get('trustm_uid') and peer_cert_cn == device.get('trustm_uid'):
                        cn_valid = True
                        auth_method = 'trustm_uid_match'
                        logger.info(f"Trust M UID authentication: CN {peer_cert_cn} matches registered Trust M UID for device {client_id}")

                    # Method 3: Infineon factory certificate (CN = "InfineonIoTNode")
                    elif peer_cert_cn == "InfineonIoTNode" and device.get('trustm_uid'):
                        # For Infineon factory certificates:
                        # - CN is always "InfineonIoTNode" (not the device ID or Trust M UID)
                        # - client_id MUST match the registered Trust M UID
                        if client_id == device.get('trustm_uid'):
                            # Optionally verify fingerprint if factory cert was already stored
                            if device.get('factory_certificate', {}).get('active'):
                                import hashlib
                                cert_fingerprint = hashlib.sha256(peer_cert.encode()).hexdigest()
                                stored_fingerprint = device.get('factory_certificate', {}).get('fingerprint_sha256')

                                if cert_fingerprint == stored_fingerprint:
                                    cn_valid = True
                                    auth_method = 'infineon_factory_certificate_verified'
                                    logger.info(f"Infineon factory certificate authentication: fingerprint matches for device {client_id}")
                                else:
                                    logger.warning(f"Infineon factory certificate fingerprint mismatch for device {client_id}")
                            else:
                                # First connection with factory certificate - trust it if client_id matches trustm_uid
                                cn_valid = True
                                auth_method = 'infineon_factory_certificate_first_connection'
                                logger.info(f"Infineon factory certificate first connection: client_id={client_id} matches registered trustm_uid")
                        else:
                            logger.warning(f"Infineon factory certificate: client_id={client_id} does not match trustm_uid={device.get('trustm_uid')}")

                    if cn_valid:
                        logger.info(f"mTLS authentication successful for device: {client_id} (CN: {peer_cert_cn}, method: {auth_method})")
                    else:
                        logger.warning(f"Certificate CN mismatch: device {client_id}, CN: {peer_cert_cn}, Trust M UID: {device.get('trustm_uid')}")
                        return _auth_reject("Certificate CN does not match device ID or Trust M UID")
                else:
                    logger.info(f"mTLS authentication successful for device: {client_id} (certificate validated by EMQX)")
                    
            # Option C: Connection on TLS port with pre-validated certificate
            elif webhook_data.get('tls_validated') and (webhook_data.get('peerport') == 8883 or webhook_data.get('sockport') == 8883):
                # EMQX has already validated the certificate during TLS handshake
                logger.info(f"TLS connection on port 8883 for device: {client_id} (certificate pre-validated by EMQX)")
                
            else:
                # Device requires mTLS but no certificate provided
                # Check for API key fallback (allows mTLS devices to connect via server-TLS in emergency)
                if password and device.get('api_key_hash'):
                    try:
                        from .api_key_security_service import APIKeySecurityService
                        if APIKeySecurityService.verify_api_key(password, device['api_key_hash']):
                            logger.info(f"mTLS device {client_id} authenticated via API key fallback (emergency server-TLS mode)")
                            # Log fallback authentication for audit
                            from .device_logs_service import device_logs_service
                            device_logs_service.add_device_log(
                                device_id=client_id,
                                level='WARNING',
                                message='Device authenticated via API key fallback (mTLS certificate not provided)',
                                log_type='security',
                                details={'auth_mode': auth_mode, 'fallback_method': 'api_key'}
                            )
                        else:
                            logger.warning(f"API key fallback authentication failed for device: {client_id}")
                            return _auth_reject("Invalid API key for fallback authentication")
                    except Exception as e:
                        logger.error(f"API key fallback verification failed: {e}")
                        return _auth_reject("API key verification error")
                else:
                    logger.warning(f"Authentication failed: device requires mTLS but no certificate provided: {client_id}")
                    return _auth_reject("Client certificate required for this device")
        
        # Step 5: Additional validation for mTLS mode
        if is_trustm_mode:
            trustm_result = _verify_trustm_certificate(peer_cert_pem, device)
            if not trustm_result.get('valid', False):
                reason = trustm_result.get('reason', 'TrustM certificate validation failed')
                logger.warning(f"TrustM validation failed for {client_id}: {reason}")
                return _auth_reject(reason)

        # For mTLS, username should match client_id OR device_id
        # For Infineon factory certificates: username = device_id, client_id = Trust M UID
        if auth_mode in ('mtls', 'optiga_trust_mtls') and username:
            # Allow username to be either client_id OR device_id
            if username != client_id and username != device.get('device_id'):
                logger.warning(f"Username mismatch in mTLS mode: expected {client_id} or {device.get('device_id')}, got {username}")
                return _auth_reject("Username must match client_id or device_id")
        
        # Step 6: Update device connection status
        _update_device_connection_status(device['_id'], 'connected')
        
        # Step 7: Log successful authentication
        _log_auth_event(device, 'success', 'Certificate and device validation passed')
        
        # Also log to device logs for UI visibility
        from .device_logs_service import device_logs_service
        device_logs_service.add_device_log(
            device_id=client_id,
            level='INFO',
            message='Device connected successfully',
            log_type='connection',
            details={
                'auth_mode': auth_mode,
                'protocol': webhook_data.get('protocol', 'mqtt'),
                'port': webhook_data.get('peerport', webhook_data.get('sockport', 1883)),
                'certificate_cn': webhook_data.get('peer_cert_cn', '') if auth_mode in ('mtls', 'optiga_trust_mtls') else None
            },
            source='mqtt_auth'
        )
        
        logger.info(f"Authentication successful: {client_id}")
        return _auth_accept(f"Device authenticated successfully: {client_id}")
        
    except Exception as e:
        logger.error(f"MQTT authentication error: {e}")
        return _auth_reject(f"Internal authentication error")


def _verify_trustm_certificate(peer_cert_pem, device):
    """Validate OPTIGA™ Trust M factory certificates and transitions."""
    try:
        factory_info = device.get('factory_certificate') or {}
        if not factory_info:
            return {'valid': True, 'reason': 'No factory certificate registered'}

        if not factory_info.get('active', True):
            # Factory certificate disabled; nothing to enforce
            return {'valid': True, 'reason': 'Factory certificate inactive'}

        if not peer_cert_pem or 'BEGIN CERTIFICATE' not in peer_cert_pem:
            logger.warning("TrustM device connected without PEM payload; falling back to broker TLS validation")
            return {'valid': True, 'reason': 'Certificate body unavailable'}

        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes

            cert_obj = x509.load_pem_x509_certificate(peer_cert_pem.encode('utf-8'), default_backend())
            fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
        except Exception as exc:
            logger.warning(f"Failed to parse TrustM certificate for device {device.get('device_id')}: {exc}")
            return {'valid': True, 'reason': 'Unable to calculate fingerprint'}

        db = get_db()
        stored_fp = factory_info.get('fingerprint_sha256')
        if fingerprint == stored_fp:
            logger.info(f"Factory certificate fingerprint matched for device {device.get('device_id')}")
            if db:
                db.devices.update_one(
                    {'_id': device['_id']},
                    {
                        '$set': {
                            'factory_certificate.last_seen_at': datetime.utcnow()
                        }
                    }
                )
                factory_info['last_seen_at'] = datetime.utcnow()
            return {'valid': True, 'reason': 'Factory certificate accepted'}

        logger.info(
            "Factory certificate fingerprint mismatch for device %s: stored=%s provided=%s",
            device.get('device_id'), stored_fp, fingerprint
        )

        # Certificate has changed; verify if Vault issued it (new TESAIoT certificate)
        vault_result = _validate_certificate_with_vault(peer_cert_pem, device)
        if vault_result.get('valid'):
            logger.info(f"Vault-issued certificate detected for device {device.get('device_id')}; disabling factory certificate")
            if db:
                db.devices.update_one(
                    {'_id': device['_id']},
                    {
                        '$set': {
                            'factory_certificate.active': False,
                            'factory_certificate.last_seen_at': datetime.utcnow()
                        }
                    }
                )
                factory_info['active'] = False
                factory_info['last_seen_at'] = datetime.utcnow()
            return {'valid': True, 'reason': vault_result.get('reason', 'Vault certificate accepted')}

        return vault_result

    except Exception as exc:
        logger.warning(f"TrustM certificate verification failed: {exc}")
        return {'valid': True, 'reason': 'TrustM validation error bypassed'}


def _validate_certificate_with_vault(peer_cert, device):
    """
    Validate device certificate against Vault PKI with enhanced validation.
    
    Args:
        peer_cert: PEM certificate from client
        device: Device document from database
        
    Returns:
        dict: Validation result with valid/invalid and reason
    """
    try:
        if not peer_cert:
            return {'valid': False, 'reason': 'No certificate provided'}
        
        vault_client = get_vault()
        
        if not vault_client:
            logger.warning("Vault PKI unavailable - falling back to stored certificate validation")
            return _validate_certificate_fallback(peer_cert, device)
        
        logger.info("Using Vault PKI validation for certificate authentication")
        
        # Get device certificate info from database
        device_cert_info = device.get('certificate_info', {})
        stored_serial = device.get('certificate_serial', '')
        
        # Enhanced certificate validation - basic format checks only
        cert_validation = _perform_certificate_checks(peer_cert, device)
        if not cert_validation['valid']:
            return cert_validation
        
        # Extract certificate details
        cert_serial = _extract_cert_serial(peer_cert)
        cert_cn = _extract_cert_cn(peer_cert)
        cert_expiry = _extract_cert_expiry(peer_cert)
        
        logger.info(f"Vault PKI validation - Certificate details: serial={cert_serial}, cn={cert_cn}, expires={cert_expiry}")
        
        # IMPORTANT: Skip DN validation entirely - we only care if Vault issued the certificate
        logger.info("Vault PKI validation - Skipping DN validation, checking if certificate was issued by Vault")
        
        # Check certificate expiration first
        if cert_expiry:
            try:
                from dateutil import parser
                expiry_date = parser.parse(cert_expiry)
                if expiry_date < datetime.now():
                    return {'valid': False, 'reason': 'Certificate has expired'}
                    
                # Warn if certificate expires soon (within 30 days)
                days_until_expiry = (expiry_date - datetime.now()).days
                if days_until_expiry <= 30:
                    logger.warning(f"Certificate for device {device.get('device_id')} expires in {days_until_expiry} days")
                    
            except Exception as e:
                logger.warning(f"Could not parse certificate expiry date: {e}")
        
        # Primary validation: Check if certificate exists in Vault PKI
        if cert_serial:
            try:
                # Try to read certificate from Vault using different potential mount paths
                vault_paths_to_try = [
                    f'pki/cert/{cert_serial}',
                    f'pki_int/cert/{cert_serial}',
                    f'pki-int/cert/{cert_serial}',
                    f'pki-root/cert/{cert_serial}',
                    f'pki_device/cert/{cert_serial}',
                    f'pki_iot/cert/{cert_serial}'
                ]
                
                cert_found_in_vault = False
                vault_cert_data = None
                
                for vault_path in vault_paths_to_try:
                    try:
                        logger.debug(f"Checking Vault path: {vault_path}")
                        cert_status = vault_client.read(vault_path)
                        
                        if cert_status and cert_status.get('data'):
                            logger.info(f"✓ Certificate {cert_serial} FOUND in Vault PKI at {vault_path}")
                            cert_found_in_vault = True
                            vault_cert_data = cert_status['data']
                            break
                    except Exception as path_error:
                        logger.debug(f"Certificate not found at {vault_path}: {path_error}")
                        continue
                
                if cert_found_in_vault:
                    logger.info(f"✓ Vault PKI validation SUCCESSFUL - Certificate {cert_serial} was issued by Vault")
                    
                    # Check if certificate is revoked
                    try:
                        # Check revocation status from certificate data
                        revocation_time = vault_cert_data.get('revocation_time', 0)
                        if revocation_time and revocation_time > 0:
                            logger.warning(f"Certificate {cert_serial} has been REVOKED")
                            return {'valid': False, 'reason': 'Certificate has been revoked', 'vault_validated': True}
                    except Exception as revoke_error:
                        logger.debug(f"Could not check revocation status: {revoke_error}")
                    
                    # Update device record with latest certificate info
                    db = get_db()
                    db.devices.update_one(
                        {'_id': device['_id']},
                        {
                            '$set': {
                                'certificate_serial': cert_serial,
                                'certificate_last_validated': datetime.now(),
                                'certificate_cn': cert_cn,
                                'certificate_expiry': cert_expiry,
                                'certificate_vault_validated': True
                            }
                        }
                    )
                    
                    # Certificate is valid - Vault confirmed it issued this certificate
                    return {
                        'valid': True, 
                        'reason': 'Certificate validated by Vault PKI',
                        'vault_validated': True
                    }
                else:
                    logger.warning(f"Certificate {cert_serial} NOT FOUND in Vault PKI - certificate may not have been issued by Vault")
                    
                    # Optional: Allow fallback to local validation if configured
                    allow_non_vault_certs = os.environ.get('ALLOW_NON_VAULT_CERTIFICATES', 'false').lower() == 'true'
                    if allow_non_vault_certs:
                        logger.info("Non-Vault certificates allowed by configuration - falling back to local validation")
                        return _validate_certificate_fallback(peer_cert, device)
                    else:
                        return {
                            'valid': False, 
                            'reason': 'Certificate not issued by Vault PKI',
                            'vault_validated': False
                        }
                
            except Exception as e:
                logger.error(f"Vault PKI validation error: {e}")
                # On Vault errors, we can optionally fall back to local validation
                logger.warning("Vault PKI validation failed - falling back to local validation")
                return _validate_certificate_fallback(peer_cert, device)
        else:
            logger.warning("Could not extract certificate serial number - cannot validate with Vault")
            return {'valid': False, 'reason': 'Could not extract certificate serial number'}
        
    except Exception as e:
        logger.error(f"Certificate validation error: {e}")
        return {'valid': False, 'reason': f'Certificate validation error: {str(e)}'}

def _validate_certificate_fallback(peer_cert, device):
    """
    Fallback certificate validation when Vault is unavailable.
    
    Args:
        peer_cert: PEM certificate from client
        device: Device document from database
        
    Returns:
        dict: Validation result
    """
    try:
        # Basic certificate format validation
        cert_validation = _perform_certificate_checks(peer_cert, device)
        if not cert_validation['valid']:
            return cert_validation
        
        # If we have a stored certificate, compare it directly
        stored_cert = device.get('certificate_info', {}).get('certificate', '')
        if stored_cert:
            # Remove whitespace and line endings for comparison
            peer_cert_clean = ''.join(peer_cert.split())
            stored_cert_clean = ''.join(stored_cert.split())
            
            if peer_cert_clean == stored_cert_clean:
                logger.info("Certificate validated against stored certificate")
                return {'valid': True, 'reason': 'Certificate matches stored certificate'}
            else:
                logger.warning("Certificate does not match stored certificate")
                return {'valid': False, 'reason': 'Certificate does not match stored certificate'}
        
        # If no stored certificate, validate basic certificate properties
        cert_serial = _extract_cert_serial(peer_cert)
        cert_cn = _extract_cert_cn(peer_cert)
        device_id = device.get('device_id', '')
        
        # Check if CN matches device ID (if CN contains device ID pattern)
        if cert_cn and device_id:
            if device_id in cert_cn or cert_cn in device_id:
                logger.info(f"Certificate CN validation passed: {cert_cn} matches device {device_id}")
                return {'valid': True, 'reason': 'Certificate CN validation passed'}
        
        # Default to allowing certificate if basic checks pass
        logger.info("Certificate passed basic validation checks")
        return {'valid': True, 'reason': 'Certificate passed basic validation'}
        
    except Exception as e:
        logger.error(f"Certificate fallback validation error: {e}")
        return {'valid': False, 'reason': f'Certificate validation failed: {str(e)}'}

def _perform_certificate_checks(peer_cert, device):
    """
    Perform basic certificate format and validity checks.
    
    Args:
        peer_cert: PEM certificate from client
        device: Device document from database
        
    Returns:
        dict: Validation result
    """
    try:
        if not peer_cert or not peer_cert.strip():
            return {'valid': False, 'reason': 'Empty certificate provided'}
        
        # Check PEM format
        if not peer_cert.strip().startswith('-----BEGIN CERTIFICATE-----'):
            return {'valid': False, 'reason': 'Invalid certificate format - must be PEM'}
        
        if not peer_cert.strip().endswith('-----END CERTIFICATE-----'):
            return {'valid': False, 'reason': 'Invalid certificate format - incomplete PEM'}
        
        # Try to parse certificate with OpenSSL
        try:
            import subprocess
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
                f.write(peer_cert)
                cert_file = f.name
            
            try:
                # Validate certificate format
                result = subprocess.run(
                    ['openssl', 'x509', '-in', cert_file, '-noout', '-text'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    return {'valid': False, 'reason': f'Certificate format validation failed: {result.stderr}'}
                
                logger.debug("Certificate format validation passed")
                return {'valid': True, 'reason': 'Certificate format is valid'}
                
            finally:
                try:
                    os.unlink(cert_file)
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"OpenSSL certificate validation failed: {e}")
            # Continue with basic validation if OpenSSL fails
        
        # Basic string validation passed
        return {'valid': True, 'reason': 'Basic certificate checks passed'}
        
    except Exception as e:
        logger.error(f"Certificate check error: {e}")
        return {'valid': False, 'reason': f'Certificate validation failed: {str(e)}'}

def _extract_cert_cn(cert_pem):
    """
    Extract Common Name (CN) from PEM certificate.
    
    Args:
        cert_pem: PEM formatted certificate
        
    Returns:
        str: Certificate common name
    """
    try:
        import subprocess
        import tempfile
        import os
        
        if not cert_pem or not cert_pem.strip():
            return ''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(cert_pem.strip())
            cert_file = f.name
        
        try:
            # Extract subject using openssl
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-noout', '-subject', '-nameopt', 'RFC2253'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output like "subject=CN=device-001.device.tesa.iot,O=BDH Corporation"
                subject_line = result.stdout.strip()
                if 'CN=' in subject_line:
                    cn_part = subject_line.split('CN=')[1].split(',')[0]
                    logger.info(f"Extracted certificate CN: {cn_part}")
                    return cn_part
            
            logger.warning(f"Failed to extract certificate CN: {result.stderr}")
            return ''
            
        finally:
            try:
                os.unlink(cert_file)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Certificate CN extraction error: {e}")
        return ''

def _extract_cert_expiry(cert_pem):
    """
    Extract expiration date from PEM certificate.
    
    Args:
        cert_pem: PEM formatted certificate
        
    Returns:
        str: Certificate expiration date in ISO format
    """
    try:
        import subprocess
        import tempfile
        import os
        
        if not cert_pem or not cert_pem.strip():
            return ''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(cert_pem.strip())
            cert_file = f.name
        
        try:
            # Extract expiration date using openssl
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-noout', '-enddate'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output like "notAfter=Dec 30 10:00:00 2025 GMT"
                enddate_line = result.stdout.strip()
                if 'notAfter=' in enddate_line:
                    date_str = enddate_line.split('notAfter=')[1]
                    
                    # Parse the date and convert to ISO format
                    from dateutil import parser
                    try:
                        parsed_date = parser.parse(date_str)
                        iso_date = parsed_date.isoformat()
                        logger.info(f"Extracted certificate expiry: {iso_date}")
                        return iso_date
                    except:
                        logger.warning(f"Could not parse certificate date: {date_str}")
            
            logger.warning(f"Failed to extract certificate expiry: {result.stderr}")
            return ''
            
        finally:
            try:
                os.unlink(cert_file)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Certificate expiry extraction error: {e}")
        return ''

def _extract_cert_serial(cert_pem):
    """
    Extract serial number from PEM certificate.
    
    Args:
        cert_pem: PEM formatted certificate
        
    Returns:
        str: Certificate serial number
    """
    try:
        import subprocess
        import tempfile
        import os
        
        if not cert_pem or not cert_pem.strip():
            logger.warning("Empty certificate provided for serial extraction")
            return ''
        
        # Clean up certificate format
        cert_clean = cert_pem.strip()
        if not cert_clean.startswith('-----BEGIN CERTIFICATE-----'):
            logger.warning("Certificate does not start with proper PEM header")
            return ''
        
        # Write certificate to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(cert_clean)
            cert_file = f.name
        
        try:
            # Extract serial using openssl
            result = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-noout', '-serial'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output like "serial=ABC123" or "serial=01:23:45:67:89:AB:CD:EF"
                serial_line = result.stdout.strip()
                if '=' in serial_line:
                    serial_raw = serial_line.split('=')[1]
                    # Handle both formats: with colons and without
                    # Remove colons and any spaces, convert to lowercase for consistency
                    serial = serial_raw.replace(':', '').replace(' ', '').lower().strip()
                    
                    # Ensure we have a valid hex serial
                    if serial and all(c in '0123456789abcdef' for c in serial):
                        logger.info(f"Extracted certificate serial: {serial}")
                        return serial
                    else:
                        logger.warning(f"Invalid serial format extracted: {serial_raw}")
            
            logger.debug(f"Primary serial extraction failed: {result.stderr}")
            
            # Try alternative method with different format
            result2 = subprocess.run(
                ['openssl', 'x509', '-in', cert_file, '-noout', '-text'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result2.returncode == 0:
                # Parse text output for serial number
                lines = result2.stdout.split('\n')
                for i, line in enumerate(lines):
                    if 'Serial Number:' in line:
                        # Extract hex serial from line like "Serial Number: 12:34:56:78"
                        # or from next line if serial is on separate line
                        serial_part = line.split('Serial Number:')[1].strip()
                        
                        # If serial_part is empty, check next line
                        if not serial_part and i + 1 < len(lines):
                            serial_part = lines[i + 1].strip()
                        
                        # Remove colons, spaces, and parens (some formats have decimal in parens)
                        serial_clean = serial_part.replace(':', '').replace(' ', '').replace('(', '').replace(')', '')
                        
                        # If it contains 'dec', extract just the hex part
                        if 'dec' in serial_clean:
                            serial_clean = serial_clean.split('dec')[0]
                        
                        # Convert to lowercase and validate hex
                        serial = serial_clean.lower().strip()
                        if serial and all(c in '0123456789abcdef' for c in serial):
                            logger.info(f"Extracted certificate serial (alt method): {serial}")
                            return serial
                        else:
                            logger.warning(f"Invalid serial format in alt method: {serial_part}")
            
            logger.warning("Could not extract certificate serial using any method")
            return ''
        
        finally:
            # Clean up temporary file
            try:
                os.unlink(cert_file)
            except:
                pass
        
    except Exception as e:
        logger.error(f"Certificate serial extraction error: {e}")
        return ''

def _detect_device_type_from_client_id(client_id):
    """
    Detect device type from client_id pattern using existing service.
    """
    try:
        from .auto_device_registration_service import auto_device_registration_service
        return auto_device_registration_service._detect_device_type(client_id)
    except Exception as e:
        logger.error(f"Error detecting device type for {client_id}: {e}")
        return 'sensor'  # Default fallback

def _determine_organization_for_device(client_id, cert_cn):
    """
    Determine organization for device based on client_id and certificate CN.
    Uses dynamic organization lookup without hardcoded values.
    """
    try:
        db = get_db()
        
        # Method 1: Certificate CN organization detection
        if cert_cn:
            orgs = list(db.organizations.find())
            for org in orgs:
                org_name = org.get('name', '').lower()
                if org_name in cert_cn.lower():
                    return str(org['_id'])
        
        # Method 2: Look for device in existing registrations (same device ID in different contexts)
        existing_device = db.devices.find_one({'device_id': {'$regex': f'^{client_id.split("-")[0]}', '$options': 'i'}})
        if existing_device:
            return existing_device.get('organization_id')
        
        # Method 3: Default to first available organization (system fallback)
        default_org = db.organizations.find_one({}, sort=[('created_at', 1)])
        if default_org:
            return str(default_org['_id'])
        
        return None
        
    except Exception as e:
        logger.error(f"Error determining organization for device {client_id}: {e}")
        return None

def _update_device_connection_status(device_id, status):
    """Update device connection status in database."""
    try:
        db = get_db()
        db.devices.update_one(
            {'_id': device_id},
            {
                '$set': {
                    'connection_status': status,
                    'last_connected': datetime.now(),
                    'last_activity': datetime.now(),
                    'last_seen': datetime.now()
                }
            }
        )
    except Exception as e:
        logger.error(f"Failed to update device status: {e}")

def _log_auth_event(device, result, details):
    """Log authentication event for audit trail."""
    try:
        db = get_db()
        db.mqtt_auth_log.insert_one({
            'device_id': device.get('device_id'),
            'device_name': device.get('name'),
            'organization_id': device.get('organization_id'),
            'auth_mode': device.get('auth_mode', 'mtls'),
            'timestamp': datetime.now(),
            'result': result,
            'details': details,
            'source': 'mqtt_webhook_auth'
        })
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")

def _auth_accept(reason="Authentication successful"):
    """Return VerneMQ webhook accept response."""
    return {
        'result': 'ok',
        'message': reason
    }

def _auth_reject(reason="Authentication failed"):
    """Return VerneMQ webhook reject response."""
    return {
        'result': 'error',
        'message': reason
    }

def handle_mqtt_disconnect(webhook_data):
    """
    Handle MQTT client disconnect webhook.
    
    Args:
        webhook_data: VerneMQ disconnect webhook payload
        
    Returns:
        dict: Response for VerneMQ
    """
    try:
        client_id = webhook_data.get('client_id', '')
        
        if client_id:
            db = get_db()
            device = db.devices.find_one({'device_id': client_id})
            
            if device:
                # Update connection status
                _update_device_connection_status(device['_id'], 'disconnected')
                
                # Log disconnect event
                _log_auth_event(device, 'disconnect', 'Client disconnected')
                
                # Also log to device logs for UI visibility
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=client_id,
                    level='INFO',
                    message='Device disconnected',
                    log_type='connection',
                    details={
                        'reason': webhook_data.get('reason', 'normal')
                    },
                    source='mqtt_auth'
                )
                
                logger.info(f"Device disconnected: {client_id}")
        
        return {'result': 'ok'}
        
    except Exception as e:
        logger.error(f"Disconnect handling error: {e}")
        return {'result': 'ok'}  # Don't block disconnect

def get_mqtt_auth_stats():
    """
    Get MQTT authentication statistics.
    
    Returns:
        dict: Authentication statistics
    """
    try:
        db = get_db()
        
        # Get stats from last 24 hours
        from datetime import timedelta
        since = datetime.now() - timedelta(hours=24)
        
        total_attempts = db.mqtt_auth_log.count_documents({
            'timestamp': {'$gte': since}
        })
        
        successful_auths = db.mqtt_auth_log.count_documents({
            'timestamp': {'$gte': since},
            'result': 'success'
        })
        
        failed_auths = db.mqtt_auth_log.count_documents({
            'timestamp': {'$gte': since},
            'result': {'$ne': 'success'}
        })
        
        # Currently connected devices
        connected_devices = db.devices.count_documents({
            'connection_status': 'connected'
        })
        
        return {
            'total_attempts_24h': total_attempts,
            'successful_auths_24h': successful_auths,
            'failed_auths_24h': failed_auths,
            'success_rate': (successful_auths / total_attempts * 100) if total_attempts > 0 else 0,
            'connected_devices': connected_devices,
            'last_updated': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting auth stats: {e}")
        return {
            'error': 'Failed to retrieve authentication statistics',
            'last_updated': datetime.now().isoformat()
        }
