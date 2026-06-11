# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Device Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import uuid
import time
import hashlib
import json
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from pymongo.errors import (
    PyMongoError, ConnectionFailure, ServerSelectionTimeoutError,
    WriteError
)

from ..core.database import get_db, get_redis
from ..core.rbac import RBAC
from .audit_service import audit_log, audit_data_access, AuditAction
from ..utils.data_fixes import fix_telemetry_data
from .telemetry_cache_service import telemetry_cache_service, invalidate_telemetry_cache_on_ingest
import sys
import os
sys.path.append('/app/audit')

from api.tolerance_methods.exception_handling import (
    with_error_handling, ErrorSeverity, ErrorCategory
)
from api.tolerance_methods.retry import (
    with_retry, RetryPolicy, CircuitBreaker
)
from api.tolerance_methods.validation import (
    validate_device_id, sanitize_string, ValidationError
)

logger = logging.getLogger(__name__)

# Circuit breakers for database operations
database_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def _get_unit_for_metric(metric_name: str) -> str:
    """Get unit for metric based on metric name"""
    unit_mapping = {
        'temperature': '°C',
        'humidity': '%',
        'pressure': 'hPa',
        'voltage': 'V',
        'current': 'A',
        'power': 'W',
        'rssi': 'dBm',
        'battery': '%',
        'light': 'lux',
        'sound': 'dB'
    }
    
    for key, unit in unit_mapping.items():
        if key.lower() in metric_name.lower():
            return unit
            
    return ''

@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.DATABASE,
    user_message="Unable to retrieve devices. Please try again.",
    return_on_error=[]
)
def get_devices_for_user(user):
    """
    Get devices list filtered by user's organization.
    
    Args:
        user: Current user object
        
    Returns:
        list: List of devices
    """
    db = get_db()
    if db is None:
        raise ConnectionFailure("Database connection not available")
        
    # SECURITY: Platform admins can NEVER access customer device data
    if RBAC.is_platform_admin(user):
        logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to access device data - DENIED")
        # Platform admins see NO customer devices
        devices = []
    else:
        # Regular users only see devices from their organization
        user_org_id = user.get('organization_id', '')
        user_org_name = user.get('organization', '') or user.get('organization_name', '')
        
        # Find the organization to get both ObjectId and string ID
        org_filter = {}
        if user_org_id:
            try:
                # Try to use as ObjectId if it's a valid 24-char hex string
                if len(user_org_id) == 24 and all(c in '0123456789abcdef' for c in user_org_id.lower()):
                    org_filter = {'_id': ObjectId(user_org_id)}
                else:
                    # Use as string organization_id
                    org_filter = {'organization_id': user_org_id}
            except:
                # Fallback to string organization_id
                org_filter = {'organization_id': user_org_id}
        elif user_org_name:
            org_filter = {'name': user_org_name}
        
        devices = []
        if org_filter:
            org = db.organizations.find_one(org_filter)
            if org:
                org_object_id = str(org['_id'])
                org_string_id = org.get('organization_id', '')
                
                # Search devices by both ObjectId and string organization_id
                # SECURITY: Only filter by organization_id, not organization name
                # to prevent cross-organization data leakage
                # ADMIN UX: Exclude service devices to prevent confusion
                
                # Build base filter
                base_conditions = [
                    {
                        '$or': [
                            {'organization_id': org_object_id},
                            {'organization_id': org_string_id},
                            {'organization': org_object_id}  # Check organization field with string ID
                        ]
                        # Note: org_object_id is already a string from str(org['_id'])
                    },
                    {
                        # Exclude service devices from Device Management UI
                        '$or': [
                            {'type': {'$ne': 'service'}},
                            {'type': {'$exists': False}}
                        ]
                    }
                ]
                
                # Visibility policy update: org_user can view all org devices
                # Actions remain gated by backend (self-service endpoints check ownership)
                
                device_filter = {'$and': base_conditions}
                
                devices = list(db.devices.find(device_filter))
                
                logger.info(f"Found {len(devices)} devices for org: {org.get('name')} (ObjectId: {org_object_id}, StringId: {org_string_id})")
            else:
                logger.warning(f"Organization not found for user: {user.get('email')}")
    
    # Cache organizations for efficient lookup
    organizations = {}
    for org in db.organizations.find():
        # Map both ObjectId and organization_id to the name
        organizations[str(org['_id'])] = org.get('name', str(org['_id']))
        if 'organization_id' in org and org['organization_id']:
            organizations[org['organization_id']] = org.get('name', str(org['_id']))
    
    # Format response
    result = []
    for device in devices:
        # Format location as string
        location = device.get('location', {})
        location_str = ''
        if isinstance(location, dict):
            if 'address' in location:
                location_str = location['address']
            elif 'lat' in location and 'lng' in location:
                location_str = f"Lat: {location['lat']:.4f}, Lng: {location['lng']:.4f}"
        elif isinstance(location, str):
            location_str = location
        
        # Resolve organization name - check both organization_id and organization fields
        org_id = device.get('organization_id', '')
        if not org_id and device.get('organization'):
            # If no organization_id, check organization field
            org_field = device.get('organization')
            if isinstance(org_field, ObjectId):
                org_id = str(org_field)
            else:
                org_id = str(org_field) if org_field else ''
        org_name = organizations.get(org_id, 'Unknown Organization')
        
        device_data = {
            '_id': str(device['_id']),
            'device_id': device.get('device_id', ''),
            'name': device.get('name', ''),
            'type': device.get('type', ''),
            'status': device.get('status', 'inactive'),
            'organization_id': org_id,
            'organization': org_name,
            'location': location_str,
            'location_details': location,
            'metadata': device.get('metadata', {}),
            'certificate_status': device.get('certificate_status', 'none'),
            'certificate_algorithm': device.get('certificate_algorithm', device.get('metadata', {}).get('certificate_algorithm', '')),
            'last_seen': device.get('last_seen'),  # Return None if not set
            'created_at': device.get('created_at', ''),
            'created_by': device.get('created_by', device.get('owner_email', '')),
            'firmware_version': device.get('firmware_version', ''),
            'telemetrySchema': device.get('telemetrySchema', None),
            'actuatorSchema': device.get('actuatorSchema', None),
            'tags': device.get('tags', []),
            # Include all raw metadata including industry fields
            'manufacturer': device.get('metadata', {}).get('manufacturer', ''),
            'model': device.get('metadata', {}).get('model', ''),
            'protocol': device.get('metadata', {}).get('protocol', 'mqtts'),
            'network_type': device.get('metadata', {}).get('network_type', 'wifi'),
            # Device public key fields
            'device_public_key': device.get('device_public_key', None),
            'key_encryption_enabled': device.get('key_encryption_enabled', False),
            'key_registration_status': device.get('key_registration_status', 'not_registered'),
            'device_public_key_uploaded': device.get('device_public_key_uploaded', False),
            # Include auth_mode field
            'auth_mode': device.get('auth_mode', device.get('auth_type', 'mtls')),
            # Include API key status (but not the key itself for security)
            'has_api_key': bool(device.get('api_key') or device.get('https_api_key')),
            'consumer_name': device.get('consumer_name', device.get('https_consumer_name', '')),
            # CRITICAL: Include CSR fields for frontend detection
            'certificate_generation_method': device.get('certificate_generation_method'),
            'generation_method': device.get('generation_method'),
            'csr_provided': device.get('csr_provided'),
            # CRITICAL: Include Trust M UID for Trust M device detection
            'trustm_uid': device.get('trustm_uid'),
            'trust_m_uid': device.get('trust_m_uid') or device.get('trustm_uid')  # Alias for UI compatibility
        }
        
        # Add certificate_info with proper field mapping if certificate exists
        if device.get('certificate_serial'):
            certificate_info = {
                'status': device.get('certificate_status', 'unknown'),
                'serial': device.get('certificate_serial'),
                'serialNumber': device.get('certificate_serial'),  # UI expects serialNumber field
                'algorithm': device.get('certificate_algorithm', device.get('metadata', {}).get('certificate_algorithm', ''))
            }
            
            # Map issued_at to validFrom (certificate start date)
            if device.get('certificate_issued_at'):
                certificate_info['validFrom'] = device.get('certificate_issued_at')
                certificate_info['issued_at'] = device.get('certificate_issued_at')
            
            # Map expires_at to validTo (certificate end date)
            if device.get('certificate_expires_at'):
                certificate_info['validTo'] = device.get('certificate_expires_at')
                certificate_info['expires_at'] = device.get('certificate_expires_at')
            
            device_data['certificate_info'] = certificate_info
            
            # Also add the raw fields for backward compatibility
            device_data['certificate_serial'] = device.get('certificate_serial')
            device_data['certificate_issued_at'] = device.get('certificate_issued_at')
            device_data['certificate_expires_at'] = device.get('certificate_expires_at')
        
        result.append(device_data)
    
    # Audit log the device list access
    audit_data_access(
        user=user,
        collection='devices',
        query={'organization_id': user.get('organization_id', '')},
        record_count=len(result),
        operation='list'
    )
    
    return result

# Input validation for device creation
def validate_device_input(data):
    """Validate device input data."""
    errors = []
    
    if not data.get('name', '').strip():
        errors.append("Device name is required")
    
    if 'device_id' in data and data['device_id']:
        if not validate_device_id(data['device_id']):
            errors.append("Invalid device ID format")
    
    if errors:
        raise ValidationError(f"Invalid device data: {'; '.join(errors)}")
    
    # Sanitize string inputs
    if 'name' in data:
        data['name'] = sanitize_string(data['name'])
    
    return data

@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.DATABASE,
    user_message="Failed to create device. Please try again."
)
def create_device(data, user):
    """
    Create a new device.
    
    Args:
        data: Device data
        user: Current user
        
    Returns:
        dict: Created device
    """
    # Debug logging for encryption issue
    logger.info(f"[ENCRYPTION DEBUG] Creating device with data keys: {list(data.keys())}")
    logger.info(f"[ENCRYPTION DEBUG] auth_type in data: {'auth_type' in data}")
    logger.info(f"[ENCRYPTION DEBUG] data.get('auth_type'): {data.get('auth_type')}")
    logger.info(f"[ENCRYPTION DEBUG] data.get('auth_type', 'certificate'): {data.get('auth_type', 'certificate')}")
    
    # Validate input data
    data = validate_device_input(data)
    
    db = get_db()
    if db is None:
        raise ConnectionFailure("Database connection not available")
    
    # Generate device ID as UUID if not provided (simplified approach)
    device_id = data.get('device_id') or str(uuid.uuid4())
    
    # Generate MQTT password for server_tls devices
    mqtt_password = None
    password_hash = None
    auth_mode = data.get('auth_mode', data.get('auth_type', 'mtls')).lower()
    if auth_mode in ('server_tls', 'api_key'):
        try:
            # Import path relative to the api module
            import sys
            import os
            # Add parent directory to path to import security module
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from security.security_utils import SecurityUtils
            mqtt_password = SecurityUtils.generate_secure_password(length=32)
            # Hash the password immediately
            password_hash = SecurityUtils.hash_password(mqtt_password)
            logger.info(f"Generated and hashed secure MQTT password for server_tls device {device_id}")
        except Exception as e:
            logger.error(f"Failed to generate MQTT password for device {device_id}: {e}")
            # Try alternative password generation
            try:
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                mqtt_password = ''.join(secrets.choice(alphabet) for _ in range(32))
                # Hash using simple bcrypt as fallback
                import bcrypt
                password_hash = bcrypt.hashpw(mqtt_password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                logger.info(f"Generated MQTT password using fallback method for device {device_id}")
            except Exception as e2:
                logger.error(f"Fallback password generation also failed: {e2}")
                raise Exception("Failed to generate secure password for device")
    
    # Generate API key for ALL devices to enable unified HTTPS access through APISIX
    https_api_key = None
    https_consumer_name = None
    protocols = data.get('metadata', {}).get('protocol', data.get('metadata', {}).get('protocols', []))
    if isinstance(protocols, str):
        protocols = [protocols.lower()]
    else:
        protocols = [p.lower() for p in protocols]
    
    # Generate API key for ALL devices (unified access through APISIX)
    # This ensures both mTLS and server-TLS devices can access HTTPS endpoints
    try:
        from .device_auth_service import device_auth_service
        
        # Generate API key with device-specific format
        device_type = data.get('type', 'sensor')
        rate_limit = 1000 if device_type == 'sensor' else 5000
        organization_id = user.get('organization_id', '')
        
        # Create device consumer in APISIX (using singleton instance)
        api_key_result = device_auth_service.create_device_consumer(
            device_id=device_id,
            device_type=device_type,
            organization_id=organization_id,
            rate_limit=rate_limit
        )
        
        if api_key_result.get('success'):
            https_api_key = api_key_result.get('api_key')
            https_consumer_name = api_key_result.get('consumer_name')
            logger.info(f"Generated API key for device {device_id}: {https_api_key[:20]}... (auth_mode: {auth_mode})")
        else:
            error_msg = api_key_result.get('error', 'Unknown error')
            logger.error(f"Failed to create device consumer: {error_msg}")
            # For HTTPS-only devices, this is critical
            if 'https' in protocols and 'mqtt' not in protocols:
                raise Exception(f"Failed to generate API key for HTTPS-only device: {error_msg}")
            # For other devices, log warning but continue (they can still use MQTT)
            else:
                logger.warning(f"Device {device_id} created without API key - MQTT access still available")
    except ImportError as e:
        logger.error(f"Failed to import device_auth_service: {e}")
        if 'https' in protocols and 'mqtt' not in protocols:
            raise Exception("Device auth service not available for HTTPS-only device")
    except Exception as e:
        logger.error(f"Failed to generate API key for device {device_id}: {e}")
        if 'https' in protocols and 'mqtt' not in protocols:
            raise Exception(f"Failed to generate API key for HTTPS-only device: {e}")
    
    # Prepare metadata - ensure certificate_algorithm is preserved
    metadata = data.get('metadata', {})

    factory_uid = data.get('factory_uid') or metadata.get('factory_uid')
    factory_certificate_pem = data.get('factory_certificate_pem') or metadata.get('factory_certificate_pem')
    sanitized_factory_uid = None
    if factory_uid:
        try:
            sanitized_factory_uid = sanitize_string(factory_uid, 128)
            if not validate_device_id(sanitized_factory_uid):
                logger.info(
                    "Factory UID does not match TESAIoT device ID format; keeping platform-generated device_id"
                )
        except Exception as uid_error:
            sanitized_factory_uid = None
            logger.warning(f"Failed to sanitize factory UID '{factory_uid}': {uid_error}")

    # ========== Trust M UID Duplicate Check ==========
    # Check for duplicate Trust M UIDs to prevent multiple devices using the same hardware identifier
    # Support both 'trustm_uid' and 'trust_m_uid' field names
    trustm_uid = data.get('trustm_uid') or data.get('trust_m_uid')
    organization_id = user.get('organization_id', '')

    # ========== Auto-set auth_mode for Trust M devices ==========
    # If Trust M UID is provided, automatically set auth_mode to optiga_trust_mtls
    if trustm_uid and isinstance(trustm_uid, str) and trustm_uid.strip():
        current_auth_mode = data.get('auth_mode', data.get('auth_type', '')).lower()
        if current_auth_mode not in ('optiga_trust_mtls',):
            logger.info(f"Trust M UID provided - auto-setting auth_mode to 'optiga_trust_mtls' (was: '{current_auth_mode}')")
            data['auth_mode'] = 'optiga_trust_mtls'

    # Check trustm_uid uniqueness (54 hex characters from OID 0xE0C2)
    if trustm_uid and isinstance(trustm_uid, str) and trustm_uid.strip():
        trustm_uid_clean = trustm_uid.strip()
        existing_device = db.devices.find_one({
            'trustm_uid': trustm_uid_clean,
            'organization_id': organization_id
        }, {'device_id': 1, 'name': 1})

        if existing_device:
            existing_name = existing_device.get('name', 'Unknown')
            existing_id = existing_device.get('device_id', 'Unknown')
            error_msg = f"Trust M UID '{trustm_uid_clean[:16]}...' is already registered to device '{existing_name}' (ID: {existing_id}). Each Trust M chip must be unique per organization."
            logger.warning(f"[DUPLICATE_UID] {error_msg}")
            raise ValueError(error_msg)

        logger.info(f"Trust M UID '{trustm_uid_clean[:16]}...' is unique - proceeding with device creation")

    # Check factory_uid uniqueness (metadata field)
    if sanitized_factory_uid:
        existing_device = db.devices.find_one({
            'metadata.factory_uid': sanitized_factory_uid,
            'organization_id': organization_id
        }, {'device_id': 1, 'name': 1})

        if existing_device:
            existing_name = existing_device.get('name', 'Unknown')
            existing_id = existing_device.get('device_id', 'Unknown')
            error_msg = f"Factory UID '{sanitized_factory_uid[:16]}...' is already registered to device '{existing_name}' (ID: {existing_id}). Each Factory UID must be unique per organization."
            logger.warning(f"[DUPLICATE_UID] {error_msg}")
            raise ValueError(error_msg)

        logger.info(f"Factory UID '{sanitized_factory_uid[:16]}...' is unique - proceeding with device creation")
    # ========== End Trust M UID Duplicate Check ==========

    # If certificate_algorithm is provided at the top level, include it in metadata
    if 'certificate_algorithm' in data and data['certificate_algorithm']:
        metadata['certificate_algorithm'] = data['certificate_algorithm']
    
    # Handle CSR device fields - check multiple possible field names
    certificate_csr = data.get('certificate_csr') or data.get('csr') or data.get('csr_content')
    is_csr_device = bool(certificate_csr) or data.get('csr_provided', False)
    
    # Handle certificate options for CSR support
    certificate_options = data.get('certificate_options', {})
    if certificate_options:
        # Store certificate generation method and CSR if provided
        metadata['certificate_generation_method'] = certificate_options.get('generation_method', 'auto-generate')
        if certificate_options.get('generation_method') == 'csr' and certificate_options.get('csr_content'):
            metadata['pending_csr'] = True  # Flag that CSR needs to be processed
            is_csr_device = True
            certificate_csr = certificate_options.get('csr_content')
    
    # If this is a CSR device, ensure all metadata is properly set
    if is_csr_device:
        metadata['certificate_generation_method'] = 'upload-csr'
        # Set additional CSR fields at root level for consistency
    
    # Include industry data in metadata
    if 'industry' in data:
        metadata['industry'] = data['industry']
    if 'industrySpecificData' in data:
        metadata['industrySpecificData'] = data['industrySpecificData']
    
    # Debug encryption calculation
    # Handle both auth_mode and auth_type for compatibility
    # Frontend sends auth_mode with values "server_tls" or "mtls"
    # We need to save both auth_mode (for MQTT) and auth_type (for backward compatibility)
    auth_mode_value = data.get('auth_mode', data.get('auth_type', 'mtls')).lower()
    factory_profile = None
    factory_certificate_info = None

    # Map auth_mode to auth_type for backward compatibility
    if auth_mode_value == 'server_tls':
        auth_type_value = 'api_key'  # server_tls uses password auth, not certificates
    elif auth_mode_value == 'mtls':
        auth_type_value = 'certificate'  # mtls requires certificates
    elif auth_mode_value == 'optiga_trust_mtls':
        auth_type_value = 'certificate'
        factory_profile = 'infineon_optiga_trust_m'
    elif auth_mode_value == 'api_key':
        auth_type_value = 'api_key'
    else:
        # Handle legacy auth_type values
        auth_type_value = auth_mode_value
        # Map legacy auth_type to auth_mode
        if auth_type_value == 'certificate':
            auth_mode_value = 'mtls'  # Default to mtls for certificate auth
        elif auth_type_value == 'api_key':
            auth_mode_value = 'server_tls'  # api_key maps to server_tls

    if sanitized_factory_uid:
        metadata['factory_uid'] = sanitized_factory_uid

    if factory_profile:
        metadata['secure_element'] = factory_profile
        metadata['protected_update_enabled'] = True
        metadata['factory_trust_anchor'] = 'infineon_optiga_trust_m_ca'
        if 'factory_certificate_pem' in metadata:
            metadata.pop('factory_certificate_pem', None)
    
    key_encryption_enabled_value = auth_type_value == 'certificate'
    logger.info(f"[ENCRYPTION DEBUG] Before device dict creation:")
    logger.info(f"[ENCRYPTION DEBUG]   auth_mode_value: {auth_mode_value}")
    logger.info(f"[ENCRYPTION DEBUG]   auth_type_value: {auth_type_value}")
    logger.info(f"[ENCRYPTION DEBUG]   key_encryption_enabled_value: {key_encryption_enabled_value}")
    
    # Determine certificate status based on auth mode
    if auth_mode_value == 'server_tls':
        # Server-TLS devices only need CA cert, not device certificates
        certificate_status = 'ca_only'
    else:
        # mTLS devices need full certificates
        certificate_status = 'pending'
    
    # Extract certificate TTL configuration if provided
    certificate_ttl_config = None
    if 'certificateTTL' in data and data['certificateTTL']:
        certificate_ttl_config = {
            'days': data['certificateTTL'].get('days', 90),  # Default to 90 days
            'justification': data['certificateTTL'].get('justification'),
            'requires_approval': data['certificateTTL'].get('requiresApproval', False),
            'security_score': data['certificateTTL'].get('securityScore', 8),
            'risk_level': data['certificateTTL'].get('riskLevel', 'low'),
            'auto_renewal_enabled': True,
            'renewal_threshold_days': 5
        }
        logger.info(f"Certificate TTL configured for device {device_id}: {certificate_ttl_config['days']} days")

    if factory_profile and factory_certificate_pem:
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import hashes

            normalized_pem = factory_certificate_pem.strip()
            cert_obj = x509.load_pem_x509_certificate(normalized_pem.encode('utf-8'), default_backend())
            fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
            factory_certificate_info = {
                'pem': normalized_pem,
                'fingerprint_sha256': fingerprint,
                'subject': cert_obj.subject.rfc4514_string(),
                'issuer': cert_obj.issuer.rfc4514_string(),
                'serial_number': format(cert_obj.serial_number, 'X'),
                'not_before': cert_obj.not_valid_before.isoformat(),
                'not_after': cert_obj.not_valid_after.isoformat(),
                'active': True,
                'last_seen_at': None
            }
            logger.info(f"Attached factory certificate fingerprint for device {device_id}: {fingerprint}")
        except Exception as cert_error:
            factory_certificate_info = None
            logger.warning(f"Failed to parse factory certificate for device {device_id}: {cert_error}")
    
    device = {
        '_id': ObjectId(),
        'device_id': device_id,
        'name': data.get('name', ''),
        'type': data.get('type', 'sensor'),
        'status': 'active',
        'organization_id': user.get('organization_id', ''),
        'location': data.get('location', {}),
        'metadata': metadata,
        'certificate_status': certificate_status,
        'certificate_algorithm': data.get('certificate_algorithm', '') if auth_mode_value != 'server_tls' else '',  # Only for mTLS
        'certificate_ttl': certificate_ttl_config,  # Certificate TTL configuration
        'created_at': datetime.now(),
        'created_by': str(user.get('_id')) if user.get('_id') else user.get('email'),
        'auth_mode': auth_mode_value,  # Save the exact auth_mode value from frontend
        'auth_type': auth_type_value,  # Keep for backward compatibility
        'telemetrySchema': data.get('telemetrySchema', None),
        'actuatorSchema': data.get('actuatorSchema', None),
        'tags': data.get('tags', []),  # Include tags from device creation
        'last_seen': None,  # Initially null, will be set when device first connects
        # Device public key fields - set encryption enabled by default for certificate auth
        'device_public_key': None,  # Will be populated when key is registered
        'key_encryption_enabled': key_encryption_enabled_value,  # Use pre-calculated value
        'key_registration_status': 'pending_auto_generation' if key_encryption_enabled_value else 'not_registered',
        'device_public_key_uploaded': False,  # Initially false, will be set to true when key is registered
        # Trust M UID field (54 hex characters from hardware coprocessor OID 0xE0C2)
        # Support both field names for compatibility
        'trustm_uid': data.get('trustm_uid') or data.get('trust_m_uid'),  # Optional: Infineon OPTIGA Trust M unique identifier
        'trust_m_uid': data.get('trust_m_uid') or data.get('trustm_uid')  # Alias for license_service compatibility
    }

    if factory_profile:
        device['trust_profile'] = factory_profile
        if sanitized_factory_uid:
            device['metadata']['factory_uid'] = sanitized_factory_uid
        if factory_certificate_info:
            device['factory_certificate'] = factory_certificate_info

    # Remove sensitive factory fields from request payload copy
    data.pop('factory_certificate_pem', None)
    data.pop('factory_uid', None)
    
    # Add CSR-specific fields if this is a CSR device
    if is_csr_device:
        device['csr_provided'] = True
        device['generation_method'] = 'upload-csr'
        device['certificate_generation_method'] = 'upload-csr'
        if certificate_csr:
            device['certificate_csr'] = certificate_csr
    
    # Add MQTT password for server_tls devices
    if mqtt_password and password_hash:
        # Store the hash, not the plaintext
        device['password_hash'] = password_hash
        device['password_algorithm'] = 'argon2id' if 'argon2' in password_hash else 'bcrypt'
        device['password_created_at'] = datetime.utcnow()
        
        # Keep plaintext temporarily ONLY for the creation response
        device['mqtt_password'] = mqtt_password
        logger.info(f"Storing hashed MQTT password for server_tls device {device_id} (plaintext will be available only during creation)")
        # Note: The plaintext password is only returned during device creation for security reasons
    
    # Add API key for all devices that have one generated
    if https_api_key:
        device['https_api_key'] = https_api_key
        device['https_consumer_name'] = https_consumer_name
        device['api_key'] = https_api_key  # Store as both https_api_key and api_key for compatibility
        device['consumer_name'] = https_consumer_name
        logger.info(f"Storing API key for device {device_id} (auth_mode: {auth_mode_value}, key will be available only during creation)")
    
    # Store device in database
    db.devices.insert_one(device)
    
    # Remove the password hash from the response object (keep plaintext for creation response only)
    if 'password_hash' in device:
        del device['password_hash']
    
    # Debug what was actually inserted
    logger.info(f"[ENCRYPTION DEBUG] Device inserted with:")
    logger.info(f"[ENCRYPTION DEBUG]   auth_mode: {device['auth_mode']}")
    logger.info(f"[ENCRYPTION DEBUG]   auth_type: {device['auth_type']}")
    logger.info(f"[ENCRYPTION DEBUG]   key_encryption_enabled: {device['key_encryption_enabled']}")
    logger.info(f"[ENCRYPTION DEBUG]   key_registration_status: {device['key_registration_status']}")
    logger.info(f"[ENCRYPTION DEBUG]   password_algorithm: {device.get('password_algorithm', 'N/A')}")
    
    # Log MQTT password generation for server_tls devices
    if mqtt_password:
        try:
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=device_id,
                level='INFO',
                message='MQTT password generated for server_tls authentication',
                log_type='security',
                details={
                    'auth_mode': 'server_tls',
                    'password_length': 32,
                    'password_stored': True
                },
                source='device_creation'
            )
        except Exception as e:
            logger.warning(f"Failed to log MQTT password generation: {e}")
    
    # API key was already stored in device record above
    # Ensure it's in the response object for the creation response
    if https_api_key:
        device['api_key'] = https_api_key
        device['consumer_name'] = https_consumer_name
        device['https_api_key'] = https_api_key  # Also include as https_api_key for clarity
        logger.info(f"API key included in device creation response for {device_id}")
    
    # Register device in TimescaleDB registry (if integration enabled)
    try:
        from .telemetry_timescale_integration import get_telemetry_timescale_integration
        integration = get_telemetry_timescale_integration()
        if integration and integration.enabled:
            integration.register_device(
                device_id=device_id,
                organization_id=device['organization_id'],
                device_type=device.get('type', 'sensor')
            )
    except Exception as e:
        logger.debug(f"Timescale registration skipped: {e}")

    # Log certificate issuance to audit trail with error handling
    try:
        db.certificate_issuance_log.insert_one({
            'organization_id': device['organization_id'],
            'device_id': device_id,
            'device_name': device['name'],
            'serial_number': f"PENDING-{device['_id']}",
            'timestamp': datetime.now(),
            'performed_by': user.get('email'),
            'valid_until': None,
            'details': 'Device created - certificate pending issuance'
        })
    except PyMongoError as e:
        logger.warning(f"Failed to log certificate issuance for device {device_id}: {e}")
        # Continue - this is not critical for device creation
    
    device['_id'] = str(device['_id'])
    device['created_at'] = device['created_at'].isoformat()
    # auth_mode is already in the device object, no need to map
    
    # GDPR audit log for device creation with error handling
    try:
        audit_log(
            action=AuditAction.DEVICE_CREATE,
            user=user,
            resource_type='device',
            resource_id=device_id,
            details={
                'device_name': device['name'],
                'device_type': device['type'],
                'organization_id': device['organization_id']
            }
        )
    except Exception as e:
        logger.warning(f"Failed to create audit log for device {device_id}: {e}")
        # Continue - audit failure should not prevent device creation
    
    # Process CSR if this is a CSR device - MUST be done before encryption keys
    if is_csr_device and certificate_csr:
        try:
            from .certificate_service import sign_device_csr
            logger.info(f"Processing CSR for device {device_id}")
            
            # Sign the CSR automatically with default 365 days validity
            csr_result = sign_device_csr(
                device_id=device_id,
                csr_content=certificate_csr,
                validity_days=365,
                user=user
            )
            
            if csr_result.get('status') == 'success':
                logger.info(f"Successfully signed CSR for device {device_id}")
                # Update device with certificate info
                device['certificate_status'] = 'valid'
                device['certificate_serial'] = csr_result.get('serial')
                # The certificate_service already updated the database
            else:
                logger.error(f"Failed to sign CSR for device {device_id}: {csr_result.get('error')}")
                # Keep certificate_status as pending
        except Exception as e:
            logger.error(f"Error processing CSR for device {device_id}: {e}")
            # Don't fail device creation, but log the issue
            try:
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=device_id,
                    level='ERROR',
                    message=f'CSR signing failed: {str(e)}',
                    log_type='certificate',
                    details={'error': str(e)},
                    source='device_creation'
                )
            except Exception:
                pass
    
    # Automatically generate encryption keys for certificate-authenticated devices
    if auth_type_value == 'certificate' or auth_mode_value in ['server_tls', 'mtls']:
        try:
            from .key_encryption_service import generate_automatic_encryption_keys
            
            # Generate encryption keys automatically
            key_generation_result = generate_automatic_encryption_keys(
                device_id=device_id,
                device_type=device.get('type', 'sensor'),
                organization_id=device['organization_id'],
                user=user,
                device_capabilities=device.get('metadata', {}).get('capabilities', {})
            )
            
            if key_generation_result.get('status') == 'success':
                logger.info(f"Automatically generated encryption keys for device {device_id}: {key_generation_result.get('key_algorithm')} (tier: {key_generation_result.get('encryption_tier')})")
                
                # The key_encryption_service already updated the database, so we just need to update the response object
                # Fetch the updated device from database to get the latest state
                updated_device = db.devices.find_one({'device_id': device_id})
                if updated_device:
                    # Update the device object with the latest encryption info for the response
                    device['key_encryption_enabled'] = updated_device.get('key_encryption_enabled', True)
                    device['key_registration_status'] = updated_device.get('key_registration_status', 'auto_generated')
                    device['encryption_tier'] = updated_device.get('encryption_tier')
                    device['device_public_key'] = key_generation_result.get('fingerprint')  # Just the fingerprint for response
                
            elif key_generation_result.get('status') == 'already_exists':
                logger.info(f"Device {device_id} already has encryption keys")
            else:
                logger.warning(f"Failed to generate automatic encryption keys for device {device_id}: {key_generation_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error during automatic key generation for device {device_id}: {e}")
            # Don't fail device creation if key generation fails
            try:
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=device_id,
                    level='WARNING',
                    message=f'Automatic encryption key generation failed: {str(e)}',
                    log_type='security',
                    details={'error': str(e), 'auth_type': device.get('auth_type')},
                    source='device_creation'
                )
            except Exception:
                pass  # Ignore logging errors
    
    return device

def update_device(device_id, data, user):
    """
    Update device information.
    
    Args:
        device_id: Device identifier (can be device_id or MongoDB ObjectId)
        data: Update data
        user: Current user
        
    Returns:
        bool: True if successful
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            db = get_db()
            if db is None:
                raise ConnectionFailure("Database connection not available")
            
            # SECURITY: Platform admins cannot update customer devices
            if RBAC.is_platform_admin(user):
                logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to update device {device_id} - DENIED")
                return False
            
            # Build query - try both device_id and ObjectId
            org_id = user.get('organization_id')
            
            # First try by device_id
            query = {
                'device_id': device_id,
                'organization_id': org_id
            }
            
            # Check if device exists
            device = db.devices.find_one(query)
            
            # If not found by device_id, try by ObjectId
            if not device and ObjectId.is_valid(device_id):
                query = {
                    '_id': ObjectId(device_id),
                    'organization_id': org_id
                }
                device = db.devices.find_one(query)
            
            if not device:
                logger.warning(f"Device not found or access denied: {device_id} for user {user.get('email')}")
                return False
            
            # Check ownership for org_user role
            user_role = user.get('role', '')
            if user_role == 'org_user':
                # org_user can only update their own devices
                user_id = str(user.get('_id')) if user.get('_id') else user.get('email')
                device_creator = device.get('created_by', '')
                device_owner = device.get('owner_id', device.get('owner_email', ''))
                
                # Check if user owns the device
                if not (device_creator == user_id or 
                        device_creator == user.get('email') or
                        device_owner == user_id or
                        device_owner == user.get('email')):
                    logger.warning(f"org_user {user.get('email')} attempted to update device {device_id} owned by {device_creator} - DENIED")
                    return False
            
            # Build update data
            # SECURITY: Never update mqtt_password field - it's only set during device creation
            update_data = {'updated_at': datetime.now()}
            
            if 'name' in data:
                update_data['name'] = data['name']
            if 'type' in data:
                update_data['type'] = data['type']
            if 'location' in data:
                update_data['location'] = data['location']
            if 'metadata' in data:
                # Merge with existing metadata to preserve fields
                if device and 'metadata' in device:
                    # Start with existing metadata
                    merged_metadata = device['metadata'].copy()
                    # Update with new metadata
                    merged_metadata.update(data['metadata'])
                    update_data['metadata'] = merged_metadata
                else:
                    update_data['metadata'] = data['metadata']

                # ========== Trust M UID Duplicate Check on Update ==========
                # Check if factory_uid is being updated and ensure uniqueness
                new_factory_uid = data['metadata'].get('factory_uid')
                old_factory_uid = device.get('metadata', {}).get('factory_uid') if device else None

                if new_factory_uid and new_factory_uid != old_factory_uid:
                    # Check if this factory_uid is already used by another device
                    existing_device = db.devices.find_one({
                        'metadata.factory_uid': new_factory_uid,
                        'organization_id': org_id,
                        '_id': {'$ne': device['_id']}  # Exclude current device
                    }, {'device_id': 1, 'name': 1})

                    if existing_device:
                        existing_name = existing_device.get('name', 'Unknown')
                        existing_id = existing_device.get('device_id', 'Unknown')
                        error_msg = f"Factory UID '{new_factory_uid[:16]}...' is already registered to device '{existing_name}' (ID: {existing_id}). Each Factory UID must be unique."
                        logger.warning(f"[DUPLICATE_UID_UPDATE] {error_msg}")
                        raise ValueError(error_msg)
                # ========== End Trust M UID Duplicate Check ==========

                # Also preserve certificate_algorithm in metadata if provided at top level
                if 'certificate_algorithm' in data and data['certificate_algorithm']:
                    update_data['metadata']['certificate_algorithm'] = data['certificate_algorithm']
                
                # Handle industry fields from metadata
                if 'industry' in data['metadata']:
                    update_data['metadata']['industry'] = data['metadata']['industry']
                if 'industrySpecificData' in data['metadata']:
                    update_data['metadata']['industrySpecificData'] = data['metadata']['industrySpecificData']
            if 'certificate_algorithm' in data:
                update_data['certificate_algorithm'] = data['certificate_algorithm']
                # Also update in metadata for backward compatibility
                if 'metadata' not in update_data:
                    update_data['metadata'] = {}
                update_data['metadata']['certificate_algorithm'] = data['certificate_algorithm']
            if 'telemetrySchema' in data:
                update_data['telemetrySchema'] = data['telemetrySchema']
            if 'actuatorSchema' in data:
                update_data['actuatorSchema'] = data['actuatorSchema']
            if 'tags' in data:
                # Ensure tags is a list
                if isinstance(data['tags'], list):
                    update_data['tags'] = data['tags']
                else:
                    update_data['tags'] = []
            # Handle Trust M UID update (support both field names)
            trustm_uid_new = data.get('trustm_uid') or data.get('trust_m_uid')
            if trustm_uid_new and isinstance(trustm_uid_new, str) and trustm_uid_new.strip():
                trustm_uid_clean = trustm_uid_new.strip()
                update_data['trustm_uid'] = trustm_uid_clean
                update_data['trust_m_uid'] = trustm_uid_clean

                # Auto-set auth_mode to optiga_trust_mtls if Trust M UID is provided
                current_auth_mode = device.get('auth_mode', '')
                if current_auth_mode != 'optiga_trust_mtls':
                    logger.info(f"Trust M UID update - auto-setting auth_mode to 'optiga_trust_mtls' for device {device_id}")
                    data['auth_mode'] = 'optiga_trust_mtls'  # This will be processed below
                    update_data['trust_profile'] = 'optiga_trust_m'
                    if 'metadata' not in update_data:
                        update_data['metadata'] = device.get('metadata', {}).copy()
                    update_data['metadata']['secure_element'] = 'infineon_optiga_trust_m'
                    update_data['metadata']['protected_update_enabled'] = True

            # Handle auth_mode field
            if 'auth_mode' in data:
                auth_mode = data['auth_mode']
                update_data['auth_mode'] = auth_mode  # Save exact auth_mode value
                
                # Map to auth_type for backward compatibility
                if auth_mode == 'server_tls':
                    update_data['auth_type'] = 'api_key'
                    update_data['key_encryption_enabled'] = False
                    update_data['key_registration_status'] = 'not_registered'
                elif auth_mode == 'mtls':
                    update_data['auth_type'] = 'certificate'
                    update_data['key_encryption_enabled'] = True
                    if not device.get('key_registration_status'):
                        update_data['key_registration_status'] = 'pending_auto_generation'
                elif auth_mode == 'api_key':
                    update_data['auth_type'] = 'api_key'
                    update_data['key_encryption_enabled'] = False
                    update_data['key_registration_status'] = 'not_registered'
                else:
                    # Handle legacy values
                    update_data['auth_type'] = auth_mode
                    update_data['key_encryption_enabled'] = False
                    update_data['key_registration_status'] = 'not_registered'
            
            # Handle public key related fields (only allow updating encryption status, not the key itself)
            if 'key_encryption_enabled' in data:
                # Only update if device has a public key
                if device.get('device_public_key'):
                    update_data['key_encryption_enabled'] = bool(data['key_encryption_enabled'])
            
            # Update the device using its _id
            result = db.devices.update_one({'_id': device['_id']}, {'$set': update_data})
            
            success = result.modified_count > 0
            
            # GDPR audit log for device update with error handling
            if success:
                try:
                    audit_log(
                        action=AuditAction.DEVICE_UPDATE,
                        user=user,
                        resource_type='device',
                        resource_id=device_id,
                        details={
                            'updated_fields': list(update_data.keys())
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to create audit log for device update {device_id}: {e}")
                    # Continue - audit failure should not affect the update result
            
            return success
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            logger.error(f"Failed to update device after {max_retries} attempts: database connection failed")
            return False
            
        except WriteError as e:
            logger.error(f"Database write error updating device {device_id}: {e}")
            return False
            
        except PyMongoError as e:
            logger.error(f"Database error updating device {device_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error updating device {device_id}: {e}")
            return False

def reset_device_password(device_id, reset_by, reason='Password reset requested', notify=True):
    """
    Reset the password for a server-TLS authenticated device.
    
    Args:
        device_id: Device identifier
        reset_by: Email/username of user initiating reset
        reason: Reason for password reset (for audit)
        notify: Whether to send notification
        
    Returns:
        dict: Contains reset_token and expires_at, or None on failure
    """
    try:
        db = get_db()
        redis = get_redis()
        
        # Get device
        device = db.devices.find_one({'device_id': device_id})
        if not device:
            logger.error(f"Device not found for password reset: {device_id}")
            return None
        
        # Verify auth mode
        auth_mode = device.get('auth_mode') or device.get('auth_type', '')
        if auth_mode != 'server_tls':
            logger.error(f"Invalid auth mode for password reset: {auth_mode}")
            return None
        
        # Generate new password and hash it
        try:
            # Try to use SecurityUtils first
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from security.security_utils import SecurityUtils
            new_password = SecurityUtils.generate_secure_password(length=32)
            password_hash = SecurityUtils.hash_password(new_password)
            password_algorithm = 'argon2id'
            logger.info(f"Generated and hashed new password for device {device_id}")
        except Exception as e:
            logger.warning(f"Failed to use SecurityUtils, falling back to bcrypt: {e}")
            # Fallback to simple generation and bcrypt
            try:
                import secrets
                import string
                import bcrypt
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                new_password = ''.join(secrets.choice(alphabet) for _ in range(32))
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                password_algorithm = 'bcrypt'
            except Exception as e2:
                logger.error(f"Failed to generate new password: {e2}")
                return None
        
        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store password in Redis with token (5 minute expiry)
        token_key = f"password_reset_token:{reset_token}"
        redis.setex(
            token_key,
            300,  # 5 minutes
            json.dumps({
                'device_id': device_id,
                'password': new_password,
                'created_at': datetime.utcnow().isoformat(),
                'reset_by': reset_by,
                'viewed': False
            })
        )
        
        # Update device with new password hash
        update_result = db.devices.update_one(
            {'device_id': device_id},
            {
                '$set': {
                    'password_hash': password_hash,
                    'password_algorithm': password_algorithm,
                    'password_updated_at': datetime.utcnow(),
                    'password_reset_at': datetime.utcnow(),
                    'password_reset_by': reset_by,
                    'password_reset_count': device.get('password_reset_count', 0) + 1,
                    'updated_at': datetime.utcnow()
                },
                '$unset': {
                    'mqtt_password': ""  # Remove any legacy plaintext password
                }
            }
        )
        
        if update_result.modified_count == 0:
            logger.error(f"Failed to update password for device: {device_id}")
            redis.delete(token_key)
            return None
        
        # Log audit event
        db.device_password_audit.insert_one({
            'device_id': device_id,
            'action': 'password_reset',
            'reset_by': reset_by,
            'reason': reason,
            'timestamp': datetime.utcnow(),
            'organization_id': device.get('organization_id'),
            'device_name': device.get('name'),
            'reset_token': reset_token
        })
        
        # Send notification if requested
        if notify:
            try:
                # TODO: Implement notification service
                logger.info(f"Password reset notification would be sent for device {device_id}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
        
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        return {
            'reset_token': reset_token,
            'expires_at': expires_at.isoformat() + 'Z',
            'device_id': device_id
        }
        
    except Exception as e:
        logger.error(f"Error resetting password for device {device_id}: {e}")
        return None

def retrieve_reset_password(device_id, token, user_id, organization_id):
    """
    Retrieve the reset password using a one-time token.
    
    Args:
        device_id: Device identifier
        token: Reset token
        user_id: User retrieving the password
        organization_id: User's organization
        
    Returns:
        dict: Contains password and metadata, or None if invalid/expired
    """
    try:
        db = get_db()
        redis = get_redis()
        
        # Get token data
        token_key = f"password_reset_token:{token}"
        token_data = redis.get(token_key)
        
        if not token_data:
            logger.warning(f"Invalid or expired token: {token}")
            return None
        
        # Parse token data
        data = json.loads(token_data)
        
        # Verify device_id matches
        if data['device_id'] != device_id:
            logger.warning(f"Token device mismatch: expected {device_id}, got {data['device_id']}")
            return None
        
        # Verify organization access
        device = db.devices.find_one({
            'device_id': device_id,
            'organization_id': organization_id
        })
        
        if not device:
            logger.warning(f"Device not found or access denied: {device_id}")
            return None
        
        # Check if already viewed
        if data.get('viewed', False):
            logger.warning(f"Token already used: {token}")
            redis.delete(token_key)
            return None
        
        # Mark as viewed and delete token (one-time use)
        redis.delete(token_key)
        
        # Log password view
        db.device_password_audit.insert_one({
            'device_id': device_id,
            'action': 'password_viewed',
            'viewed_by': user_id,
            'timestamp': datetime.utcnow(),
            'organization_id': organization_id,
            'reset_token': token
        })
        
        # Calculate expiry
        created_at = datetime.fromisoformat(data['created_at'])
        expires_at = created_at + timedelta(minutes=5)
        
        return {
            'password': data['password'],
            'created_at': data['created_at'],
            'expires_at': expires_at.isoformat() + 'Z',
            'reset_by': data['reset_by']
        }
        
    except Exception as e:
        logger.error(f"Error retrieving password for device {device_id}: {e}")
        return None

def _migrate_password_to_hash(device_id, password):
    """
    Internal function to migrate plaintext password to hash.
    Called during authentication when legacy password is detected.
    
    Args:
        device_id: MongoDB ObjectId or device_id string
        password: The plaintext password to hash
    """
    try:
        db = get_db()
        
        # Hash the password
        try:
            import sys
            import os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from security.security_utils import SecurityUtils
            password_hash = SecurityUtils.hash_password(password)
            password_algorithm = 'argon2id'
        except Exception as e:
            logger.warning(f"Failed to use SecurityUtils for migration, using bcrypt: {e}")
            import bcrypt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            password_algorithm = 'bcrypt'
        
        # Update device with hash and remove plaintext
        result = db.devices.update_one(
            {'_id': device_id} if hasattr(device_id, '__str__') else {'device_id': device_id},
            {
                '$set': {
                    'password_hash': password_hash,
                    'password_algorithm': password_algorithm,
                    'password_migrated': True,
                    'password_migrated_at': datetime.utcnow()
                },
                '$unset': {
                    'mqtt_password': ""
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Successfully migrated password to {password_algorithm} hash for device")
        else:
            logger.warning(f"No changes made during password migration")
            
    except Exception as e:
        logger.error(f"Error migrating password to hash: {e}")

def delete_device(device_id, user):
    """
    Delete a device.
    
    Args:
        device_id: Device identifier (can be device_id or MongoDB ObjectId)
        user: Current user
        
    Returns:
        bool: True if successful
    """
    try:
        db = get_db()
        
        # Check organization access
        # SECURITY: Platform admins can NEVER delete customer devices
        if RBAC.is_platform_admin(user):
            logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to delete device {device_id} - DENIED")
            return False
        
        # Build query - try both device_id and ObjectId
        org_id = user.get('organization_id')
        
        # First try by device_id
        query = {
            'device_id': device_id,
            'organization_id': org_id
        }
        
        # Get device info before deletion for audit
        device = db.devices.find_one(query)
        
        # If not found by device_id, try by ObjectId
        if not device and ObjectId.is_valid(device_id):
            query = {
                '_id': ObjectId(device_id),
                'organization_id': org_id
            }
            device = db.devices.find_one(query)
        
        if not device:
            logger.warning(f"Device not found or access denied: {device_id} for user {user.get('email')}")
            return False
        
        # Check ownership for org_user role
        user_role = user.get('role', '')
        if user_role == 'org_user':
            # org_user can only delete their own devices
            user_id = str(user.get('_id')) if user.get('_id') else user.get('email')
            device_creator = device.get('created_by', '')
            device_owner = device.get('owner_id', device.get('owner_email', ''))
            
            # Check if user owns the device
            if not (device_creator == user_id or 
                    device_creator == user.get('email') or
                    device_owner == user_id or
                    device_owner == user.get('email')):
                logger.warning(f"org_user {user.get('email')} attempted to delete device {device_id} owned by {device_creator} - DENIED")
                return False
        
        # Delete the device
        result = db.devices.delete_one({'_id': device['_id']})
        
        # Also delete related telemetry
        if result.deleted_count > 0:
            # Use the actual device_id from the device record for telemetry deletion
            actual_device_id = device.get('device_id')
            if actual_device_id:
                db.telemetry.delete_many({'device_id': actual_device_id})
            
            # GDPR audit log for device deletion
            audit_log(
                action=AuditAction.DEVICE_DELETE,
                user=user,
                resource_type='device',
                resource_id=device_id,
                details={
                    'device_name': device.get('name', '') if device else 'Unknown',
                    'device_type': device.get('type', '') if device else 'Unknown'
                }
            )
        
        return result.deleted_count > 0
        
    except Exception as e:
        logger.error(f"Error deleting device: {e}")
        raise

def update_device_status(device_id, status, user):
    """
    Update device status.
    
    Args:
        device_id: Device identifier
        status: New status
        user: Current user
        
    Returns:
        tuple: (success, message)
    """
    try:
        valid_statuses = ['active', 'inactive', 'maintenance', 'decommissioned']
        if status not in valid_statuses:
            return False, f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
        
        db = get_db()
        
        # Build update query
        query = {'device_id': device_id}
        
        # Check organization access
        if user.get('role') != 'super_admin':
            query['organization_id'] = user.get('organization_id')
        
        result = db.devices.update_one(
            query,
            {'$set': {
                'status': status,
                'status_updated_at': datetime.now(),
                'updated_at': datetime.now()
            }}
        )
        
        if result.modified_count == 0:
            return False, 'Device not found or access denied'
        
        return True, 'Success'
        
    except Exception as e:
        logger.error(f"Error updating device status: {e}")
        raise

def get_device_telemetry(device_id, user, limit=100):
    """
    Get device telemetry data with Redis caching.
    
    Args:
        device_id: Device identifier
        user: Current user
        limit: Maximum records
        
    Returns:
        list: Telemetry data or None if not found
    """
    # Try to get from cache first
    try:
        cached_data = telemetry_cache_service.get_telemetry_from_cache(device_id, limit)
        if cached_data is not None:
            logger.debug(f"Returning cached telemetry for device {device_id}")
            return cached_data
    except Exception as e:
        logger.warning(f"Cache retrieval failed, falling back to database: {e}")
    
    # Cache miss or error - proceed with database query
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            db = get_db()
            if db is None:
                raise ConnectionFailure("Database connection not available")
            
            # Check device exists and user has access
            # SECURITY: Platform admins can NEVER access customer telemetry
            if RBAC.is_platform_admin(user):
                logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to access telemetry for device {device_id} - DENIED")
                return None
            
            query = {'device_id': device_id}
            query['organization_id'] = user.get('organization_id')
            
            device = db.devices.find_one(query)
            
            if not device and ObjectId.is_valid(device_id):
                query = {'_id': ObjectId(device_id)}
                query['organization_id'] = user.get('organization_id')
                device = db.devices.find_one(query)
            
            if not device:
                return None
            
            # Get actual device_id for telemetry lookup
            actual_device_id = device.get('device_id', device_id)
            
            # SECURITY: Get telemetry with organization filter
            # Include organization_id in telemetry query for defense in depth
            telemetry_query = {'device_id': actual_device_id}
            if not RBAC.is_platform_admin(user):
                telemetry_query['organization_id'] = user.get('organization_id')
            
            telemetry = list(db.telemetry.find(
                telemetry_query,
                limit=limit
            ).sort('timestamp', -1))
            
            # Format response using the telemetry data formatter
            result = fix_telemetry_data(telemetry)
            
            # Cache the result if we got data
            if result and isinstance(result, list):
                try:
                    telemetry_cache_service.set_telemetry_cache(device_id, result, limit)
                except Exception as e:
                    logger.warning(f"Failed to cache telemetry data: {e}")
            
            return result
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            logger.error(f"Failed to get telemetry after {max_retries} attempts: database connection failed")
            return []  # Return empty list instead of None
            
        except PyMongoError as e:
            logger.error(f"Database error getting telemetry for device {device_id}: {e}")
            return []  # Return empty list for graceful degradation
            
        except Exception as e:
            logger.error(f"Unexpected error getting telemetry for device {device_id}: {e}")
            return []  # Return empty list to prevent UI crash

class TelemetryIngestResult:
    """Outcome of ingest_device_telemetry().

    Truthiness mirrors the legacy bool contract so existing callers that test
    ``if not result`` keep working: a falsy result means the request failed
    (device not found / access denied / primary-store error) and should map to
    404/500. A truthy result means the primary (MongoDB) write succeeded.

    ``timeseries_stored`` separately reports whether the SECONDARY TimescaleDB
    time-series write persisted. It can be False even on an otherwise successful
    ingest, so the caller can surface a warning instead of falsely claiming the
    time-series write succeeded. ``None`` means the time-series path was not
    reached (e.g. the primary write failed first).
    """

    __slots__ = ('ingested', 'timeseries_stored')

    def __init__(self, ingested: bool, timeseries_stored=None):
        self.ingested = bool(ingested)
        self.timeseries_stored = timeseries_stored

    def __bool__(self):
        return self.ingested


def ingest_device_telemetry(device_id, data, user):
    """
    Ingest telemetry data for a device.

    Args:
        device_id: Device identifier
        data: Telemetry data
        user: Current user

    Returns:
        TelemetryIngestResult: truthy when the primary (MongoDB) write
        succeeded. ``.timeseries_stored`` reports whether the secondary
        TimescaleDB time-series write persisted (False/None on failure) so the
        caller can surface it honestly to the client. The object is falsy when
        the device was not found, access was denied, or the primary write
        failed, preserving the legacy ``if not result`` -> 404/500 contract.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            db = get_db()
            if db is None:
                raise ConnectionFailure("Database connection not available")
            
            # Verify device exists and user has access
            query = {'device_id': device_id}
            if user.get('role') != 'super_admin':
                query['organization_id'] = user.get('organization_id')
            
            device = db.devices.find_one(query)
            if not device:
                return TelemetryIngestResult(False)
            
            # Validate telemetry data if schema exists
            telemetry_data = data.get('data', {})
            telemetry_schema = device.get('telemetrySchema')
            
            if telemetry_schema and telemetry_schema.get('properties'):
                # Check for schema violations
                required_fields = telemetry_schema.get('required', [])
                missing_fields = [field for field in required_fields if field not in telemetry_data]
                
                if missing_fields:
                    # Log schema validation error
                    from .device_logs_service import device_logs_service
                    device_logs_service.add_device_log(
                        device_id=device_id,
                        level='ERROR',
                        message=f"Telemetry schema validation failed: missing required fields",
                        log_type='telemetry',
                        details={'missing_fields': missing_fields, 'received_fields': list(telemetry_data.keys())},
                        source='api'
                    )
            
            # SECURITY: Store telemetry with organization_id for proper isolation
            telemetry = {
                'device_id': device_id,
                'organization_id': device.get('organization_id', ''),  # Critical for GDPR compliance
                'timestamp': datetime.now(),
                'data': telemetry_data,
                'metadata': data.get('metadata', {})
            }
            
            db.telemetry.insert_one(telemetry)

            # Sync to TimescaleDB (secondary time-series analytics store) using the
            # SAME shared contract as controllers/telemetry.py so behaviour and log
            # severity are consistent across ingestion paths. MongoDB above is the
            # primary store and already succeeded; the helper NEVER raises and
            # returns False on failure, logging at ERROR internally. We capture the
            # outcome so the caller can report it honestly instead of silently
            # claiming the time-series write succeeded.
            timescale_stored = False
            try:
                from ..controllers.telemetry import store_telemetry_timeseries

                timescale_stored = bool(store_telemetry_timeseries(
                    device_id,
                    telemetry['timestamp'],
                    telemetry_data,
                    data.get('metadata', {}),
                    device.get('organization_id', ''),
                ))
                if not timescale_stored:
                    # ERROR (not WARNING): alerting keyed on ERROR must catch this
                    # path too, identical to controllers/telemetry.py.
                    logger.error(
                        f"TimescaleDB time-series write FAILED for device {device_id} "
                        f"(primary MongoDB store already succeeded); sample is NOT "
                        f"available for time-series analytics.",
                        exc_info=True,
                    )
                else:
                    logger.debug(f"Synced telemetry to TimescaleDB for device {device_id}")
            except Exception as e:
                timescale_stored = False
                logger.error(
                    f"Failed to sync telemetry to TimescaleDB for device {device_id} "
                    f"(primary MongoDB store already succeeded): {e}",
                    exc_info=True,
                )

            # Update device last_seen
            db.devices.update_one(
                {'device_id': device_id},
                # Store timezone-aware UTC to avoid client TZ drift
                {'$set': {'last_seen': datetime.now(timezone.utc)}}
            )
            
            # Invalidate telemetry cache for this device
            try:
                invalidate_telemetry_cache_on_ingest(device_id)
                logger.debug(f"Invalidated telemetry cache for device {device_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate telemetry cache: {e}")
            
            # Log successful telemetry ingestion
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=device_id,
                level='INFO',
                message='Telemetry data ingested successfully',
                log_type='telemetry',
                details={
                    'payload_size': f"{len(str(telemetry_data))} bytes",
                    'fields': list(telemetry_data.keys())[:5]  # First 5 fields
                },
                source='api'
            )

            return TelemetryIngestResult(True, timeseries_stored=timescale_stored)

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Database connection error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            logger.error(f"Failed to ingest telemetry after {max_retries} attempts: database connection failed")
            return TelemetryIngestResult(False)

        except WriteError as e:
            logger.error(f"Database write error ingesting telemetry for device {device_id}: {e}")
            # Try to log the error
            try:
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=device_id,
                    level='ERROR',
                    message=f"Failed to ingest telemetry: database write error",
                    log_type='telemetry',
                    details={'error': str(e)},
                    source='api'
                )
            except Exception:
                pass  # Ignore logging errors
            return TelemetryIngestResult(False)

        except PyMongoError as e:
            logger.error(f"Database error ingesting telemetry for device {device_id}: {e}")
            return TelemetryIngestResult(False)

        except Exception as e:
            logger.error(f"Unexpected error ingesting telemetry for device {device_id}: {e}")
            # Try to log the error
            try:
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=device_id,
                    level='ERROR',
                    message=f"Failed to ingest telemetry: {str(e)}",
                    log_type='telemetry',
                    details={'error': str(e)},
                    source='api'
                )
            except Exception:
                pass  # Ignore logging errors
            return TelemetryIngestResult(False)

def renew_device_certificate(device_id, user):
    """
    Renew device certificate via Vault PKI (PKI-backed, no placeholders).
    Always normalizes CN to DEVICE_ID; SANs handled by PKI layer.

    Returns a dict with certificate summary, or None if device not found/access denied.
    """
    try:
        db = get_db()
        if db is None:
            raise RuntimeError('Database unavailable')

        # Access-checked device lookup
        query = {'device_id': device_id}
        if user.get('role') != 'super_admin':
            query['organization_id'] = user.get('organization_id')
        device = db.devices.find_one(query)
        if not device:
            return None

        # Choose algorithm (default ECC P‑256)
        algo = (device.get('certificate_algorithm') or 'ecc-p256').lower()

        # Use PKI Provisioning service to issue a new certificate
        from ..services.pki_provisioning_service import PKIProvisioningService
        from ..core.database import get_vault

        pki = PKIProvisioningService()
        result = pki.generate_device_certificate(
            device_data={
                'device_id': device_id,
                'organization_id': device.get('organization_id'),
                'certificate_algorithm': algo,
                'certificate_validity_days': 365,
            },
            user=user,
            vault_client=get_vault()
        )

        serial = result.get('serial_number') or result.get('serial')
        issued_at = result.get('issued_at')
        expires_at = result.get('expires_at')
        old_serial = device.get('certificate_serial')

        # Normalize algorithm to standard format (ECC-P256, RSA-2048, etc.)
        _algo_raw = algo or 'ECC-P256'
        _algo_upper = _algo_raw.upper().strip()
        if _algo_upper in ('ECC-P256', 'ECC_P256', 'ECCP256', 'ECC-256', 'ECC256'):
            _norm_algo = 'ECC-P256'
        elif _algo_upper in ('RSA-2048', 'RSA2048'):
            _norm_algo = 'RSA-2048'
        elif _algo_upper in ('RSA-4096', 'RSA4096'):
            _norm_algo = 'RSA-4096'
        else:
            _norm_algo = _algo_raw

        # Determine provisioning method based on device HSM capability
        has_hsm = bool(
            device.get('factory_uid') or
            device.get('trust_m_uid') or
            device.get('hsm_enabled')
        )
        provisioning_method = 'hsm_csr' if has_hsm else 'sw_csr'

        # Update summary fields on device record including certificate_info
        now = datetime.now()
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {
                'certificate_serial': serial,
                'certificate_status': 'valid',
                'certificate_issued_at': issued_at,
                'certificate_expires_at': expires_at,
                'certificate_algorithm': _norm_algo,
                'last_certificate_renewal': now,
                'certificate_info': {
                    'serial_number': serial,
                    'key_algorithm': _norm_algo,
                    'issued_at': issued_at,
                    'expires_at': expires_at,
                    'issued_via': provisioning_method,
                    'issuer': 'Trust M + Vault CA' if has_hsm else 'TESAIoT Vault CA',
                    'subject': f"CN={device.get('name', device_id)}"
                }
            }}
        )

        # Audit history with complete schema matching Protected Update records
        action = 'renewed' if old_serial else 'issued'
        issued_by = 'Trust M + Vault CA' if has_hsm else 'TESAIoT Vault CA'
        db.certificate_renewal_history.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device_id,
            'device_name': device.get('name'),
            'action': action,
            'method': 'csr',
            'provisioning_method': provisioning_method,
            'renewal_date': now,
            'timestamp': now,
            'serial_number': serial,
            'old_serial': old_serial,
            'new_serial': serial,
            'algorithm': _norm_algo,
            'validity_days': 365,
            'issued_by': issued_by,
            'initiated_by': user.get('email'),
            'trigger': 'manual',
            'status': 'completed',
            'reason': 'PKI-backed certificate renewal'
        })

        return {
            'deviceId': device_id,
            'serialNumber': serial,
            'validFrom': issued_at,
            'validTo': expires_at,
            'status': 'active',
            'algorithm': algo
        }

    except Exception as e:
        logger.error(f"Error renewing certificate (PKI-backed): {e}")
        raise

class CertificateRevocationError(Exception):
    """Raised when certificate revocation cannot be enforced end-to-end.

    Carries an HTTP-friendly status so the controller can fail CLOSED with an
    accurate response instead of silently degrading to a MongoDB-only flag flip.
    """

    def __init__(self, message, code='REVOCATION_FAILED', status_code=502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _normalize_cert_serial(serial):
    """Normalize a certificate serial to Vault's colon-separated lowercase hex.

    Vault's pki(-int)/revoke endpoint expects the serial in
    'xx:xx:xx:...' form. Accepts '0x...', bare hex, or already-colon'd input.
    Returns None when the input is empty/unusable so callers can fail CLOSED.
    """
    if not serial or not isinstance(serial, str):
        return None
    s = serial.strip().lower()
    if not s or s in ('unknown', 'none', 'null'):
        return None
    if ':' in s:
        return s
    if s.startswith('0x'):
        s = s[2:]
    if s and all(c in '0123456789abcdef' for c in s):
        if len(s) % 2:
            s = '0' + s
        return ':'.join(s[i:i + 2] for i in range(0, len(s), 2))
    # Unrecognized format: return as-is, let Vault validate/reject it.
    return s


def _revoke_serial_in_vault(serial_number):
    """Revoke a certificate serial in Vault's intermediate PKI (pki-int).

    Raises CertificateRevocationError if Vault is unavailable or the revoke
    call fails, so the caller can fail CLOSED. On success Vault adds the serial
    to the CRL published at pki-int/crl (consumed by the EMQX mTLS listener).
    """
    from ..core.database import get_vault

    normalized = _normalize_cert_serial(serial_number)
    if not normalized:
        raise CertificateRevocationError(
            'Device has no usable certificate serial to revoke in Vault PKI',
            code='NO_SERIAL',
            status_code=409,
        )

    try:
        vault_client = get_vault()
    except Exception as e:
        raise CertificateRevocationError(
            f'Vault client unavailable for revocation: {e}',
            code='VAULT_UNAVAILABLE',
            status_code=503,
        )

    if vault_client is None:
        raise CertificateRevocationError(
            'Vault client unavailable for revocation',
            code='VAULT_UNAVAILABLE',
            status_code=503,
        )

    # Allow the intermediate PKI mount to be overridden, but default to the
    # mount the platform actually issues device certs from (pki-int).
    pki_mount = os.environ.get('VAULT_PKI_INT_MOUNT', 'pki-int').strip('/')

    try:
        vault_client.write(
            f'{pki_mount}/revoke',
            serial_number=normalized,
        )
        logger.info(
            f"Certificate serial {normalized} revoked in Vault PKI ({pki_mount})"
        )
    except Exception as e:
        # Vault returns an error if the serial is already revoked; treat that
        # as success (idempotent) but fail CLOSED on every other error.
        msg = str(e).lower()
        if 'already revoked' in msg or 'already_revoked' in msg:
            logger.info(
                f"Certificate serial {normalized} was already revoked in Vault PKI"
            )
            return normalized
        raise CertificateRevocationError(
            f'Vault PKI revoke failed for serial {normalized}: {e}',
            code='VAULT_REVOKE_FAILED',
            status_code=502,
        )

    # Force the CRL to be rebuilt immediately so revocation takes effect at the
    # next CRL refresh on the broker/proxy (best-effort: the serial is already
    # in Vault's revoked set even if rotate fails).
    try:
        vault_client.read(f'{pki_mount}/crl/rotate')
    except Exception as rotate_err:
        logger.warning(
            f"Vault CRL rotate after revoke returned: {rotate_err} "
            f"(serial {normalized} is still revoked; CRL will refresh on schedule)"
        )

    return normalized


def revoke_device_certificate(device_id, reason, user):
    """
    Revoke device certificate.

    Revocation is enforced END-TO-END and fails CLOSED:
      1. The certificate serial is revoked in Vault's intermediate PKI
         (pki-int/revoke). If Vault revocation fails, the whole operation is
         aborted and the MongoDB status is NOT changed, so the platform never
         reports a cert as "revoked" while it can still connect.
      2. Only after Vault confirms revocation is the device's certificate
         status flipped in MongoDB (defense-in-depth for the EMQX auth webhook).

    Args:
        device_id: Device identifier
        reason: Revocation reason
        user: Current user

    Returns:
        bool: True if successful
        None: Device not found / access denied

    Raises:
        CertificateRevocationError: if Vault revocation cannot be enforced.
    """
    try:
        db = get_db()

        # Find device with access check
        query = {
            '$or': [
                {'device_id': device_id},
                {'certificate_serial': device_id}
            ]
        }

        if ObjectId.is_valid(device_id):
            query['$or'].append({'_id': ObjectId(device_id)})

        # Add organization filter for non-super admins
        if user.get('role') != 'super_admin':
            query['organization_id'] = user.get('organization_id')

        device = db.devices.find_one(query)
        if not device:
            return None

        serial_number = device.get('certificate_serial')

        # Step 1: Enforce revocation in Vault PKI FIRST (fail CLOSED).
        # This adds the serial to Vault's CRL so the broker/proxy reject it.
        revoked_serial = _revoke_serial_in_vault(serial_number)

        # Step 2: Only now update MongoDB status (defense-in-depth for the
        # EMQX auth webhook, which also denies devices flagged 'revoked').
        db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {
                'certificate_status': 'revoked',
                'certificate_revoked_at': datetime.now(),
                'certificate_revoked_by': user.get('email'),
                'certificate_revoke_reason': reason,
                'certificate_revoked_in_vault': True
            }}
        )

        # Log to audit trail
        db.certificate_revocation_log.insert_one({
            'organization_id': device.get('organization_id'),
            'device_id': device.get('device_id'),
            'device_name': device.get('name'),
            'serial_number': revoked_serial or serial_number or 'Unknown',
            'revoked_at': datetime.now(),
            'revoked_by': user.get('email'),
            'reason': reason,
            'vault_revoked': True,
            'details': f'Certificate revoked via API (Vault PKI + CRL): {reason}'
        })

        return True

    except CertificateRevocationError:
        # Propagate so the controller can return an accurate fail-CLOSED status.
        raise
    except Exception as e:
        logger.error(f"Error revoking certificate: {e}")
        raise


def validate_public_key(public_key_pem):
    """
    Validate a public key in PEM format.
    
    Args:
        public_key_pem: Public key in PEM format
        
    Returns:
        tuple: (is_valid, error_message, key_info)
    """
    try:
        # Check if it's a valid PEM format
        if not public_key_pem or not isinstance(public_key_pem, str):
            return False, "Public key must be a non-empty string", None
        
        # Basic PEM format validation
        if not public_key_pem.startswith('-----BEGIN'):
            return False, "Invalid PEM format: missing BEGIN header", None
        
        if not public_key_pem.strip().endswith('-----'):
            return False, "Invalid PEM format: missing END footer", None
        
        # Detect key type and algorithm
        key_type = None
        algorithm = None
        
        if 'RSA PUBLIC KEY' in public_key_pem:
            key_type = 'RSA'
            algorithm = 'RSA'
        elif 'EC PUBLIC KEY' in public_key_pem or 'PUBLIC KEY' in public_key_pem:
            # Could be EC or generic public key format
            if 'prime256v1' in public_key_pem or 'P-256' in public_key_pem:
                key_type = 'EC'
                algorithm = 'ECDSA-P256'
            elif 'secp384r1' in public_key_pem or 'P-384' in public_key_pem:
                key_type = 'EC'
                algorithm = 'ECDSA-P384'
            else:
                # Try to detect from key content
                key_type = 'RSA' if 'RSA' in public_key_pem else 'EC'
                algorithm = 'RSA' if key_type == 'RSA' else 'ECDSA'
        
        # Calculate fingerprint
        # Remove PEM headers/footers and whitespace
        key_data = public_key_pem.strip()
        key_data = key_data.replace('-----BEGIN PUBLIC KEY-----', '')
        key_data = key_data.replace('-----END PUBLIC KEY-----', '')
        key_data = key_data.replace('-----BEGIN RSA PUBLIC KEY-----', '')
        key_data = key_data.replace('-----END RSA PUBLIC KEY-----', '')
        key_data = key_data.replace('-----BEGIN EC PUBLIC KEY-----', '')
        key_data = key_data.replace('-----END EC PUBLIC KEY-----', '')
        key_data = key_data.replace('\n', '').replace('\r', '').replace(' ', '')
        
        # Calculate SHA256 fingerprint
        fingerprint = hashlib.sha256(key_data.encode()).hexdigest()
        
        key_info = {
            'type': key_type,
            'algorithm': algorithm,
            'fingerprint': fingerprint,
            'length': len(key_data)
        }
        
        return True, None, key_info
        
    except Exception as e:
        logger.error(f"Error validating public key: {e}")
        return False, f"Validation error: {str(e)}", None


@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.DATABASE,
    user_message="Failed to register device public key. Please try again."
)
def register_device_public_key(device_id, public_key_pem, user, enable_encryption=False):
    """
    Register a public key for a device.
    
    Args:
        device_id: Device identifier
        public_key_pem: Public key in PEM format
        user: Current user
        enable_encryption: Whether to enable key-based encryption
        
    Returns:
        dict: Registration result with status and details
    """
    try:
        db = get_db()
        if db is None:
            raise ConnectionFailure("Database connection not available")
        
        # Validate the public key
        is_valid, error_msg, key_info = validate_public_key(public_key_pem)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg
            }
        
        # Find device with access check
        query = {'device_id': device_id}
        
        # SECURITY: Platform admins cannot register keys for customer devices
        if RBAC.is_platform_admin(user):
            logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to register key for device {device_id} - DENIED")
            return {
                'success': False,
                'error': 'Access denied'
            }
        
        query['organization_id'] = user.get('organization_id')
        
        device = db.devices.find_one(query)
        
        # Also try by ObjectId if not found
        if not device and ObjectId.is_valid(device_id):
            query = {
                '_id': ObjectId(device_id),
                'organization_id': user.get('organization_id')
            }
            device = db.devices.find_one(query)
        
        if not device:
            return {
                'success': False,
                'error': 'Device not found or access denied'
            }
        
        # Check if key is already registered (by fingerprint)
        existing_device = db.devices.find_one({
            'device_public_key.fingerprint': key_info['fingerprint'],
            '_id': {'$ne': device['_id']}  # Not the same device
        })
        
        if existing_device:
            logger.warning(f"Public key fingerprint already registered for device {existing_device.get('device_id')}")
            return {
                'success': False,
                'error': 'This public key is already registered to another device'
            }
        
        # Prepare public key data
        device_public_key = {
            'key': public_key_pem,
            'algorithm': key_info['algorithm'],
            'fingerprint': key_info['fingerprint'],
            'registered_at': datetime.now(),
            'registered_by': user.get('email')
        }
        
        # Update device with public key
        update_data = {
            'device_public_key': device_public_key,
            'key_encryption_enabled': enable_encryption,
            'key_registration_status': 'registered',
            'updated_at': datetime.now()
        }
        
        result = db.devices.update_one(
            {'_id': device['_id']},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            # Audit log
            audit_log(
                action=AuditAction.DEVICE_UPDATE,
                user=user,
                resource_type='device',
                resource_id=device_id,
                details={
                    'action': 'public_key_registered',
                    'key_algorithm': key_info['algorithm'],
                    'key_fingerprint': key_info['fingerprint'],
                    'encryption_enabled': enable_encryption
                }
            )
            
            # Log to device logs
            try:
                from .device_logs_service import device_logs_service
                device_logs_service.add_device_log(
                    device_id=device.get('device_id'),
                    level='INFO',
                    message='Device public key registered successfully',
                    log_type='security',
                    details={
                        'algorithm': key_info['algorithm'],
                        'fingerprint': key_info['fingerprint'],
                        'encryption_enabled': enable_encryption
                    },
                    source='api'
                )
            except Exception as e:
                logger.warning(f"Failed to log key registration: {e}")
            
            return {
                'success': True,
                'device_id': device.get('device_id'),
                'key_fingerprint': key_info['fingerprint'],
                'algorithm': key_info['algorithm'],
                'encryption_enabled': enable_encryption,
                'registered_at': device_public_key['registered_at'].isoformat()
            }
        else:
            return {
                'success': False,
                'error': 'Failed to update device'
            }
            
    except Exception as e:
        logger.error(f"Error registering device public key: {e}")
        return {
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }


@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.LOW,
    category=ErrorCategory.DATABASE,
    user_message="Unable to retrieve device public key.",
    return_on_error=None
)
def get_device_public_key(device_id, user):
    """
    Get the public key for a device.
    
    Args:
        device_id: Device identifier
        user: Current user
        
    Returns:
        dict: Public key information or None
    """
    try:
        db = get_db()
        if db is None:
            raise ConnectionFailure("Database connection not available")
        
        # SECURITY: Platform admins cannot access customer device keys
        if RBAC.is_platform_admin(user):
            logger.warning(f"[SECURITY] Platform admin {user.get('email')} attempted to access public key for device {device_id} - DENIED")
            return None
        
        # Find device with access check
        query = {'device_id': device_id, 'organization_id': user.get('organization_id')}
        device = db.devices.find_one(query)
        
        # Also try by ObjectId if not found
        if not device and ObjectId.is_valid(device_id):
            query = {
                '_id': ObjectId(device_id),
                'organization_id': user.get('organization_id')
            }
            device = db.devices.find_one(query)
        
        if not device:
            return None
        
        # Check if device has a public key
        if not device.get('device_public_key'):
            return {
                'device_id': device.get('device_id'),
                'has_public_key': False,
                'key_registration_status': device.get('key_registration_status', 'not_registered')
            }
        
        # Return public key info (without the actual key for security)
        public_key_info = device['device_public_key']
        return {
            'device_id': device.get('device_id'),
            'has_public_key': True,
            'algorithm': public_key_info.get('algorithm'),
            'fingerprint': public_key_info.get('fingerprint'),
            'registered_at': public_key_info.get('registered_at').isoformat() if public_key_info.get('registered_at') else None,
            'registered_by': public_key_info.get('registered_by'),
            'key_encryption_enabled': device.get('key_encryption_enabled', False),
            'key_registration_status': device.get('key_registration_status', 'registered')
        }
        
    except Exception as e:
        logger.error(f"Error retrieving device public key: {e}")
        return None


def update_device_encryption_status(device_id, enable_encryption, user):
    """
    Update device encryption status.
    
    Args:
        device_id: Device identifier
        enable_encryption: Whether to enable encryption
        user: Current user
        
    Returns:
        tuple: (success, message)
    """
    try:
        db = get_db()
        
        # Find device with access check
        query = {'device_id': device_id}
        if user.get('role') != 'super_admin':
            query['organization_id'] = user.get('organization_id')
        
        device = db.devices.find_one(query)
        if not device:
            return False, 'Device not found or access denied'
        
        # Check if device has a public key
        if not device.get('device_public_key'):
            return False, 'Device does not have a registered public key'
        
        # Update encryption status
        result = db.devices.update_one(
            {'_id': device['_id']},
            {'$set': {
                'key_encryption_enabled': enable_encryption,
                'updated_at': datetime.now()
            }}
        )
        
        if result.modified_count > 0:
            # Audit log
            audit_log(
                action=AuditAction.DEVICE_UPDATE,
                user=user,
                resource_type='device',
                resource_id=device_id,
                details={
                    'action': 'encryption_status_updated',
                    'encryption_enabled': enable_encryption
                }
            )
            
            return True, 'Encryption status updated successfully'
        else:
            return False, 'No changes made'
            
    except Exception as e:
        logger.error(f"Error updating device encryption status: {e}")
        return False, f'Update failed: {str(e)}'


# Device service is a module with functions, not a class
# No service instance needed as functions are imported directly
