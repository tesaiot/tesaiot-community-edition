# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Key Provisioning Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import logging
import uuid
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from ..core.database import get_db, get_vault
from .audit_service import audit_log, AuditAction
from .websocket_service import websocket_service
import sys
sys.path.append('/app/audit')

from api.tolerance_methods.exception_handling import (
    with_error_handling, ErrorSeverity, ErrorCategory
)
from api.tolerance_methods.retry import (
    with_retry, RetryPolicy, CircuitBreaker
)
from api.tolerance_methods.validation import (
    validate_device_id, ValidationError
)

logger = logging.getLogger(__name__)

class KeyAlgorithm(str, Enum):
    """Supported key algorithms."""
    ECC_P256 = "ECC-P256"
    ECC_P384 = "ECC-P384" 
    RSA_2048 = "RSA-2048"
    RSA_3072 = "RSA-3072"
    RSA_4096 = "RSA-4096"

class KeyStatus(str, Enum):
    """Key lifecycle status."""
    PENDING = "pending"
    GENERATED = "generated"
    DISTRIBUTED = "distributed"
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    ROTATED = "rotated"

class DistributionMethod(str, Enum):
    """Key distribution methods."""
    SECURE_DOWNLOAD = "secure_download"
    ESCROW = "escrow"
    DIRECT_PUSH = "direct_push"
    OTA_UPDATE = "ota_update"

class RotationType(str, Enum):
    """Key rotation types."""
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    MANUAL = "manual"

class KeyProvisioningError(Exception):
    """Custom key provisioning error."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

# Circuit breakers for different service types
database_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
vault_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120)

@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Key generation failed. Please try again or contact support."
)
def generate_bulk_keys(devices: List[Dict], default_algorithm: str, 
                      session_name: str, metadata: Dict, user: Dict) -> Dict:
    """
    Generate bulk keys for multiple devices.
    
    Args:
        devices: List of device data
        default_algorithm: Default algorithm to use
        session_name: Name for the generation session
        metadata: Additional metadata
        user: Current user
        
    Returns:
        Session information with generation results
    """
    try:
        db = get_db()
        vault_client = get_vault()

        if db is None:
            raise KeyProvisioningError("Database connection not available")
        
        # Validate user permissions
        organization_id = user.get('organization_id')
        if not organization_id:
            raise KeyProvisioningError("User organization not found")
        
        # Create generation session
        session_id = str(uuid.uuid4())
        session_data = {
            'session_id': session_id,
            'session_name': session_name,
            'organization_id': organization_id,
            'initiated_by': user.get('email'),
            'initiated_at': datetime.now(),
            'status': 'in_progress',
            'total_devices': len(devices),
            'successful': 0,
            'failed': 0,
            'metadata': metadata,
            'default_algorithm': default_algorithm
        }
        
        db.key_generation_sessions.insert_one(session_data)
        
        # Send WebSocket notification for session start
        websocket_service.send_provisioning_notification(
            'key_generation_started',
            {
                'session_id': session_id,
                'session_name': session_name,
                'device_count': len(devices),
                'key_type': default_algorithm,
                'priority': 'medium'
            },
            recipient_ids=[user.get('id')]
        )
        
        # Process each device
        generated_keys = []
        errors = []
        
        for i, device_data in enumerate(devices):
            try:
                device_id = device_data['device_id']
                algorithm = device_data.get('algorithm', default_algorithm)
                device_type = device_data.get('device_type', 'sensor')
                
                # Validate device ID
                if not validate_device_id(device_id):
                    raise ValidationError(f"Invalid device ID format: {device_id}")
                
                # Send WebSocket notification for key generation start
                operation_id = f"key_gen_{device_id}_{session_id[:8]}"
                websocket_service.send_key_generation_status(
                    operation_id,
                    {
                        'status': 'started',
                        'device_id': device_id,
                        'key_type': algorithm,
                        'progress': 0
                    },
                    recipient_ids=[user.get('id')]
                )
                
                # Generate key pair
                key_info = _generate_key_pair(algorithm, device_id, organization_id)
                
                # Store in Vault if available
                vault_path = None
                if vault_client:
                    try:
                        vault_path = f"secret/keys/{organization_id}/{device_id}"
                        vault_data = {
                            'private_key': key_info['private_key_pem'],
                            'public_key': key_info['public_key_pem'],
                            'algorithm': algorithm,
                            'device_type': device_type,
                            'generated_at': datetime.now().isoformat(),
                            'session_id': session_id
                        }
                        vault_client.write(vault_path, **vault_data)
                        logger.info(f"Stored key for device {device_id} in Vault")
                    except Exception as e:
                        logger.warning(f"Failed to store key in Vault for {device_id}: {e}")
                        vault_path = None
                
                # Store key record in database
                key_record = {
                    'key_id': str(uuid.uuid4()),
                    'device_id': device_id,
                    'organization_id': organization_id,
                    'session_id': session_id,
                    'algorithm': algorithm,
                    'device_type': device_type,
                    'key_fingerprint': _calculate_key_fingerprint(key_info['public_key_pem']),
                    'status': KeyStatus.GENERATED,
                    'generated_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(days=365),  # Default 1 year
                    'vault_path': vault_path,
                    'distribution_status': 'pending',
                    'metadata': device_data.get('metadata', {})
                }
                
                # For security, only store public key in main database
                # Private key is stored in Vault or encrypted separately
                key_record['public_key_pem'] = key_info['public_key_pem']
                
                # Store encrypted private key if Vault is not available
                if not vault_path:
                    encryption_key = _derive_encryption_key(session_id, device_id)
                    encrypted_private_key = _encrypt_private_key(
                        key_info['private_key_pem'], encryption_key
                    )
                    key_record['encrypted_private_key'] = encrypted_private_key
                
                db.device_keys.insert_one(key_record)
                
                generated_keys.append({
                    'device_id': device_id,
                    'key_id': key_record['key_id'],
                    'algorithm': algorithm,
                    'fingerprint': key_record['key_fingerprint'],
                    'status': 'generated'
                })
                
                session_data['successful'] += 1
                
                # Send WebSocket notification for key generation completion
                websocket_service.send_key_generation_status(
                    operation_id,
                    {
                        'status': 'completed',
                        'device_id': device_id,
                        'key_type': algorithm,
                        'progress': 100,
                        'fingerprint': key_record['key_fingerprint']
                    },
                    recipient_ids=[user.get('id')]
                )
                
                # Audit log
                audit_log(
                    action=AuditAction.KEY_GENERATE,
                    user=user,
                    resource_type='device_key',
                    resource_id=device_id,
                    details={
                        'session_id': session_id,
                        'algorithm': algorithm,
                        'fingerprint': key_record['key_fingerprint']
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to generate key for device {device_data.get('device_id', 'unknown')}: {e}")
                errors.append({
                    'device_id': device_data.get('device_id', 'unknown'),
                    'error': str(e)
                })
                session_data['failed'] += 1
                
                # Send WebSocket notification for key generation failure
                if 'operation_id' in locals():
                    websocket_service.send_key_generation_status(
                        operation_id,
                        {
                            'status': 'failed',
                            'device_id': device_data.get('device_id', 'unknown'),
                            'key_type': algorithm if 'algorithm' in locals() else default_algorithm,
                            'error_message': str(e),
                            'progress': 0
                        },
                        recipient_ids=[user.get('id')]
                    )
            
            # Send progress update every 10 devices or if it's the last device
            if (i + 1) % 10 == 0 or i == len(devices) - 1:
                progress_percentage = int(((i + 1) / len(devices)) * 100)
                websocket_service.send_provisioning_progress(
                    session_id,
                    {
                        'progress': progress_percentage,
                        'current_device': i + 1,
                        'total_devices': len(devices),
                        'successful': session_data['successful'],
                        'failed': session_data['failed'],
                        'skipped': 0,
                        'status': 'processing'
                    },
                    recipient_ids=[user.get('id')]
                )
        
        # Update session status
        session_data['status'] = 'completed' if session_data['failed'] == 0 else 'partial'
        session_data['completed_at'] = datetime.now()
        session_data['generated_keys'] = generated_keys
        session_data['errors'] = errors
        
        db.key_generation_sessions.update_one(
            {'session_id': session_id},
            {'$set': session_data}
        )
        
        # Send completion notification
        if session_data['status'] == 'completed':
            websocket_service.send_provisioning_notification(
                'key_generation_completed',
                {
                    'session_id': session_id,
                    'session_name': session_name,
                    'key_type': default_algorithm,
                    'total_devices': session_data['total_devices'],
                    'successful': session_data['successful'],
                    'priority': 'high'
                },
                recipient_ids=[user.get('id')]
            )
        else:
            websocket_service.send_provisioning_notification(
                'key_generation_failed',
                {
                    'session_id': session_id,
                    'session_name': session_name,
                    'error_message': f"{session_data['failed']} devices failed key generation",
                    'total_devices': session_data['total_devices'],
                    'successful': session_data['successful'],
                    'failed': session_data['failed'],
                    'priority': 'high'
                },
                recipient_ids=[user.get('id')]
            )
        
        return {
            'session_id': session_id,
            'status': session_data['status'],
            'total_devices': session_data['total_devices'],
            'successful': session_data['successful'],
            'failed': session_data['failed'],
            'generated_keys': generated_keys,
            'errors': errors,
            'completed_at': session_data['completed_at'].isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in bulk key generation: {e}")
        raise KeyProvisioningError(f"Bulk key generation failed: {str(e)}")

def get_supported_algorithms() -> Dict:
    """
    Get list of supported key algorithms with their specifications.
    
    Returns:
        Dictionary of supported algorithms
    """
    return {
        'algorithms': [
            {
                'name': KeyAlgorithm.ECC_P256,
                'type': 'Elliptic Curve',
                'key_size': 256,
                'security_level': 128,
                'recommended_for': ['IoT sensors', 'low-power devices'],
                'performance': 'High',
                'key_generation_speed': 'Fast',
                'signature_speed': 'Fast',
                'memory_usage': 'Low'
            },
            {
                'name': KeyAlgorithm.ECC_P384,
                'type': 'Elliptic Curve',
                'key_size': 384,
                'security_level': 192,
                'recommended_for': ['Medium-power devices', 'gateways'],
                'performance': 'Medium-High',
                'key_generation_speed': 'Fast',
                'signature_speed': 'Fast',
                'memory_usage': 'Medium'
            },
            {
                'name': KeyAlgorithm.RSA_2048,
                'type': 'RSA',
                'key_size': 2048,
                'security_level': 112,
                'recommended_for': ['Legacy compatibility'],
                'performance': 'Medium',
                'key_generation_speed': 'Medium',
                'signature_speed': 'Medium',
                'memory_usage': 'Medium'
            },
            {
                'name': KeyAlgorithm.RSA_3072,
                'type': 'RSA',
                'key_size': 3072,
                'security_level': 128,
                'recommended_for': ['Gateways', 'servers'],
                'performance': 'Medium-Low',
                'key_generation_speed': 'Slow',
                'signature_speed': 'Slow',
                'memory_usage': 'High'
            },
            {
                'name': KeyAlgorithm.RSA_4096,
                'type': 'RSA',
                'key_size': 4096,
                'security_level': 152,
                'recommended_for': ['High-security applications'],
                'performance': 'Low',
                'key_generation_speed': 'Very Slow',
                'signature_speed': 'Very Slow',
                'memory_usage': 'Very High'
            }
        ],
        'recommendations': {
            'ultra_low_power': KeyAlgorithm.ECC_P256,
            'low_power': KeyAlgorithm.ECC_P256,
            'medium_power': KeyAlgorithm.ECC_P384,
            'high_power': KeyAlgorithm.RSA_3072,
            'maximum_security': KeyAlgorithm.RSA_4096
        },
        'default_by_device_type': {
            'sensor': KeyAlgorithm.ECC_P256,
            'actuator': KeyAlgorithm.ECC_P256,
            'gateway': KeyAlgorithm.RSA_3072,
            'edge_device': KeyAlgorithm.ECC_P384,
            'medical_device': KeyAlgorithm.RSA_3072,
            'industrial_device': KeyAlgorithm.RSA_3072
        }
    }

@database_circuit_breaker
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.EXTERNAL_SERVICE,
    user_message="Key distribution failed. Please try again."
)
def distribute_keys_to_devices(session_id: str, devices: List[str], 
                              distribution_method: str, expiry_hours: int, 
                              user: Dict) -> Dict:
    """
    Distribute keys to devices using specified method.
    
    Args:
        session_id: Key generation session ID
        devices: List of device IDs to distribute to
        distribution_method: Method for distribution
        expiry_hours: Hours until distribution expires
        user: Current user
        
    Returns:
        Distribution results
    """
    try:
        db = get_db()
        organization_id = user.get('organization_id')
        
        # Validate session
        session = db.key_generation_sessions.find_one({
            'session_id': session_id,
            'organization_id': organization_id
        })
        
        if not session:
            raise KeyProvisioningError("Session not found", "SESSION_NOT_FOUND")
        
        # Create distribution record
        distribution_id = str(uuid.uuid4())
        distribution_record = {
            'distribution_id': distribution_id,
            'session_id': session_id,
            'organization_id': organization_id,
            'method': distribution_method,
            'devices': devices,
            'initiated_by': user.get('email'),
            'initiated_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=expiry_hours),
            'status': 'pending',
            'download_links': []
        }
        
        if distribution_method == DistributionMethod.SECURE_DOWNLOAD:
            # Generate secure download links
            download_links = []
            for device_id in devices:
                key_record = db.device_keys.find_one({
                    'device_id': device_id,
                    'session_id': session_id,
                    'organization_id': organization_id
                })
                
                if key_record:
                    # Generate secure token
                    download_token = secrets.token_urlsafe(32)
                    download_link = {
                        'device_id': device_id,
                        'token': download_token,
                        'expires_at': datetime.now() + timedelta(hours=expiry_hours),
                        'download_count': 0,
                        'max_downloads': 3
                    }
                    download_links.append(download_link)
                    
                    # Store download token
                    db.key_download_tokens.insert_one({
                        'token': download_token,
                        'device_id': device_id,
                        'key_id': key_record['key_id'],
                        'distribution_id': distribution_id,
                        'expires_at': download_link['expires_at'],
                        'max_downloads': 3,
                        'download_count': 0,
                        'created_at': datetime.now()
                    })
            
            distribution_record['download_links'] = download_links
            
        elif distribution_method == DistributionMethod.ESCROW:
            # Implement key escrow logic
            for device_id in devices:
                key_record = db.device_keys.find_one({
                    'device_id': device_id,
                    'session_id': session_id,
                    'organization_id': organization_id
                })
                
                if key_record:
                    # Store in escrow system
                    escrow_record = {
                        'escrow_id': str(uuid.uuid4()),
                        'device_id': device_id,
                        'key_id': key_record['key_id'],
                        'organization_id': organization_id,
                        'escrowed_at': datetime.now(),
                        'status': 'escrowed',
                        'release_conditions': {
                            'requires_approval': True,
                            'authorized_users': [user.get('email')],
                            'expires_at': datetime.now() + timedelta(hours=expiry_hours)
                        }
                    }
                    
                    db.key_escrow.insert_one(escrow_record)
        
        # Store distribution record
        db.key_distributions.insert_one(distribution_record)
        
        # Update key records
        db.device_keys.update_many(
            {
                'device_id': {'$in': devices},
                'session_id': session_id,
                'organization_id': organization_id
            },
            {
                '$set': {
                    'distribution_status': 'distributed',
                    'distribution_method': distribution_method,
                    'distributed_at': datetime.now()
                }
            }
        )
        
        # Audit log
        audit_log(
            action=AuditAction.KEY_DISTRIBUTE,
            user=user,
            resource_type='key_distribution',
            resource_id=distribution_id,
            details={
                'session_id': session_id,
                'method': distribution_method,
                'device_count': len(devices),
                'expires_at': distribution_record['expires_at'].isoformat()
            }
        )
        
        return {
            'distribution_id': distribution_id,
            'method': distribution_method,
            'devices_count': len(devices),
            'status': 'initiated',
            'expires_at': distribution_record['expires_at'].isoformat(),
            'download_links': distribution_record.get('download_links', [])
        }
        
    except Exception as e:
        logger.error(f"Error in key distribution: {e}")
        raise KeyProvisioningError(f"Key distribution failed: {str(e)}")

def update_rotation_policy(policy_data: Dict, user: Dict) -> Dict:
    """
    Update key rotation policy.
    
    Args:
        policy_data: Rotation policy configuration
        user: Current user
        
    Returns:
        Updated policy information
    """
    try:
        db = get_db()
        organization_id = user.get('organization_id')
        
        # Prepare policy record
        policy_record = {
            'organization_id': organization_id,
            'enabled': policy_data.get('enabled', False),
            'rotation_type': policy_data.get('rotation_type', RotationType.TIME_BASED),
            'rotation_interval_days': policy_data.get('rotation_interval_days', 90),
            'auto_rotation': policy_data.get('auto_rotation', False),
            'pre_rotation_warning_days': policy_data.get('pre_rotation_warning_days', 7),
            'device_filters': policy_data.get('device_filters', {}),
            'retention_policy': {
                'keep_old_keys_days': policy_data.get('keep_old_keys_days', 30),
                'max_key_versions': policy_data.get('max_key_versions', 3)
            },
            'updated_by': user.get('email'),
            'updated_at': datetime.now()
        }
        
        # Upsert policy
        db.key_rotation_policies.update_one(
            {'organization_id': organization_id},
            {'$set': policy_record},
            upsert=True
        )
        
        # Schedule rotation jobs if auto-rotation is enabled
        if policy_record['enabled'] and policy_record['auto_rotation']:
            _schedule_rotation_jobs(organization_id, policy_record)
        
        # Audit log
        audit_log(
            action=AuditAction.KEY_POLICY_UPDATE,
            user=user,
            resource_type='rotation_policy',
            resource_id=organization_id,
            details={
                'enabled': policy_record['enabled'],
                'rotation_type': policy_record['rotation_type'],
                'interval_days': policy_record['rotation_interval_days']
            }
        )
        
        return {
            'status': 'updated',
            'policy': {
                'enabled': policy_record['enabled'],
                'rotation_type': policy_record['rotation_type'],
                'rotation_interval_days': policy_record['rotation_interval_days'],
                'auto_rotation': policy_record['auto_rotation']
            },
            'updated_at': policy_record['updated_at'].isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating rotation policy: {e}")
        raise KeyProvisioningError(f"Rotation policy update failed: {str(e)}")

def get_key_lifecycle_status(device_id: Optional[str] = None, 
                           session_id: Optional[str] = None,
                           status_filter: Optional[str] = None,
                           user: Dict = None) -> Dict:
    """
    Get key lifecycle monitoring status.
    
    Args:
        device_id: Specific device ID (optional)
        session_id: Specific session ID (optional)
        status_filter: Filter by status (optional)
        user: Current user
        
    Returns:
        Key lifecycle status information
    """
    try:
        db = get_db()
        organization_id = user.get('organization_id')
        
        # Build query
        query = {'organization_id': organization_id}
        if device_id:
            query['device_id'] = device_id
        if session_id:
            query['session_id'] = session_id
        if status_filter:
            query['status'] = status_filter
        
        # Get key records
        keys = list(db.device_keys.find(query).sort('generated_at', -1))
        
        # Process key status
        key_status = []
        for key_record in keys:
            current_time = datetime.now()
            expires_at = key_record.get('expires_at', current_time)
            
            # Determine current status
            status = key_record.get('status', KeyStatus.PENDING)
            if expires_at < current_time and status == KeyStatus.ACTIVE:
                status = KeyStatus.EXPIRED
            
            # Check for rotation needs
            rotation_needed = False
            days_to_expiry = (expires_at - current_time).days if expires_at > current_time else 0
            
            # Get rotation policy
            policy = db.key_rotation_policies.find_one({'organization_id': organization_id})
            if policy and policy.get('enabled'):
                warning_days = policy.get('pre_rotation_warning_days', 7)
                if days_to_expiry <= warning_days:
                    rotation_needed = True
            
            key_info = {
                'key_id': key_record.get('key_id'),
                'device_id': key_record.get('device_id'),
                'algorithm': key_record.get('algorithm'),
                'status': status,
                'generated_at': key_record.get('generated_at').isoformat() if key_record.get('generated_at') else None,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'days_to_expiry': days_to_expiry,
                'rotation_needed': rotation_needed,
                'distribution_status': key_record.get('distribution_status', 'pending'),
                'fingerprint': key_record.get('key_fingerprint')
            }
            
            key_status.append(key_info)
        
        # Summary statistics
        summary = {
            'total_keys': len(key_status),
            'by_status': {},
            'expiring_soon': 0,
            'rotation_needed': 0
        }
        
        for key_info in key_status:
            status = key_info['status']
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1
            
            if key_info['days_to_expiry'] <= 30:
                summary['expiring_soon'] += 1
            
            if key_info['rotation_needed']:
                summary['rotation_needed'] += 1
        
        return {
            'summary': summary,
            'keys': key_status,
            'query_params': {
                'device_id': device_id,
                'session_id': session_id,
                'status_filter': status_filter
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting key lifecycle status: {e}")
        raise KeyProvisioningError(f"Failed to get key status: {str(e)}")

def get_key_generation_session(session_id: str, user: Dict) -> Optional[Dict]:
    """
    Get key generation session details.
    
    Args:
        session_id: Session identifier
        user: Current user
        
    Returns:
        Session details or None if not found
    """
    try:
        db = get_db()
        organization_id = user.get('organization_id')
        
        session = db.key_generation_sessions.find_one({
            'session_id': session_id,
            'organization_id': organization_id
        })
        
        if not session:
            return None
        
        # Get key count by status
        key_counts = db.device_keys.aggregate([
            {
                '$match': {
                    'session_id': session_id,
                    'organization_id': organization_id
                }
            },
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ])
        
        status_counts = {item['_id']: item['count'] for item in key_counts}
        
        # Format response
        session_info = {
            'session_id': session['session_id'],
            'session_name': session.get('session_name'),
            'status': session.get('status'),
            'initiated_by': session.get('initiated_by'),
            'initiated_at': session.get('initiated_at').isoformat() if session.get('initiated_at') else None,
            'completed_at': session.get('completed_at').isoformat() if session.get('completed_at') else None,
            'total_devices': session.get('total_devices', 0),
            'successful': session.get('successful', 0),
            'failed': session.get('failed', 0),
            'default_algorithm': session.get('default_algorithm'),
            'metadata': session.get('metadata', {}),
            'key_status_counts': status_counts,
            'errors': session.get('errors', [])
        }
        
        return session_info
        
    except Exception as e:
        logger.error(f"Error getting key generation session: {e}")
        return None

def get_key_distribution_status(session_id: Optional[str] = None,
                               device_id: Optional[str] = None,
                               user: Dict = None) -> Dict:
    """
    Get key distribution status.
    
    Args:
        session_id: Session ID (optional)
        device_id: Device ID (optional)
        user: Current user
        
    Returns:
        Distribution status information
    """
    try:
        db = get_db()
        organization_id = user.get('organization_id')
        
        # Build query
        query = {'organization_id': organization_id}
        if session_id:
            query['session_id'] = session_id
        if device_id:
            query['devices'] = device_id
        
        # Get distribution records
        distributions = list(db.key_distributions.find(query).sort('initiated_at', -1))
        
        distribution_status = []
        for dist in distributions:
            dist_info = {
                'distribution_id': dist.get('distribution_id'),
                'session_id': dist.get('session_id'),
                'method': dist.get('method'),
                'status': dist.get('status'),
                'devices_count': len(dist.get('devices', [])),
                'initiated_by': dist.get('initiated_by'),
                'initiated_at': dist.get('initiated_at').isoformat() if dist.get('initiated_at') else None,
                'expires_at': dist.get('expires_at').isoformat() if dist.get('expires_at') else None
            }
            
            # Add download link info if applicable
            if dist.get('download_links'):
                active_links = 0
                expired_links = 0
                current_time = datetime.now()
                
                for link in dist['download_links']:
                    if link.get('expires_at', current_time) > current_time:
                        active_links += 1
                    else:
                        expired_links += 1
                
                dist_info['download_links'] = {
                    'total': len(dist['download_links']),
                    'active': active_links,
                    'expired': expired_links
                }
            
            distribution_status.append(dist_info)
        
        return {
            'distributions': distribution_status,
            'total_count': len(distribution_status),
            'query_params': {
                'session_id': session_id,
                'device_id': device_id
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting key distribution status: {e}")
        raise KeyProvisioningError(f"Failed to get distribution status: {str(e)}")

def _generate_key_pair(algorithm: str, device_id: str, organization_id: str) -> Dict:
    """
    Generate a key pair based on the specified algorithm.
    
    Args:
        algorithm: Key algorithm to use
        device_id: Device identifier
        organization_id: Organization ID
        
    Returns:
        Dictionary with private and public key PEM data
    """
    try:
        if algorithm == KeyAlgorithm.ECC_P256:
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        elif algorithm == KeyAlgorithm.ECC_P384:
            private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
        elif algorithm == KeyAlgorithm.RSA_2048:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        elif algorithm == KeyAlgorithm.RSA_3072:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=3072,
                backend=default_backend()
            )
        elif algorithm == KeyAlgorithm.RSA_4096:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
        else:
            raise KeyProvisioningError(f"Unsupported algorithm: {algorithm}")
        
        # Serialize keys to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        return {
            'private_key_pem': private_key_pem,
            'public_key_pem': public_key_pem,
            'algorithm': algorithm
        }
        
    except Exception as e:
        logger.error(f"Error generating key pair: {e}")
        raise KeyProvisioningError(f"Key pair generation failed: {str(e)}")

def _calculate_key_fingerprint(public_key_pem: str) -> str:
    """
    Calculate SHA-256 fingerprint of public key.
    
    Args:
        public_key_pem: Public key in PEM format
        
    Returns:
        Hex-encoded SHA-256 fingerprint
    """
    try:
        # Load public key
        public_key_bytes = public_key_pem.encode('utf-8')
        
        # Calculate SHA-256 hash
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(public_key_bytes)
        fingerprint = digest.finalize()
        
        # Return as hex string
        return fingerprint.hex()
        
    except Exception as e:
        logger.error(f"Error calculating key fingerprint: {e}")
        return ""

def _derive_encryption_key(session_id: str, device_id: str) -> bytes:
    """
    Derive encryption key for private key storage.
    
    Args:
        session_id: Session identifier
        device_id: Device identifier
        
    Returns:
        32-byte encryption key
    """
    # Use PBKDF2 to derive encryption key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=f"{session_id}:{device_id}".encode('utf-8'),
        iterations=100000,
        backend=default_backend()
    )
    
    # Use a combination of session_id and device_id as password
    password = f"{session_id}:{device_id}:tesa-iot".encode('utf-8')
    
    return kdf.derive(password)

def _encrypt_private_key(private_key_pem: str, encryption_key: bytes) -> str:
    """
    Encrypt private key for storage.
    
    Args:
        private_key_pem: Private key in PEM format
        encryption_key: 32-byte encryption key
        
    Returns:
        Base64-encoded encrypted private key
    """
    try:
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(encryption_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad private key data
        private_key_bytes = private_key_pem.encode('utf-8')
        padding_length = 16 - (len(private_key_bytes) % 16)
        padded_data = private_key_bytes + bytes([padding_length] * padding_length)
        
        # Encrypt
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Combine IV and encrypted data
        encrypted_blob = iv + encrypted_data
        
        # Return base64-encoded result
        return base64.b64encode(encrypted_blob).decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error encrypting private key: {e}")
        raise KeyProvisioningError(f"Private key encryption failed: {str(e)}")

def _schedule_rotation_jobs(organization_id: str, policy: Dict):
    """
    Schedule automatic key rotation jobs.
    
    Args:
        organization_id: Organization ID
        policy: Rotation policy configuration
    """
    try:
        db = get_db()
        
        # Create rotation schedule
        next_check = datetime.now() + timedelta(days=1)  # Check daily
        
        schedule_record = {
            'organization_id': organization_id,
            'rotation_type': policy['rotation_type'],
            'interval_days': policy['rotation_interval_days'],
            'next_check': next_check,
            'last_check': None,
            'enabled': True,
            'created_at': datetime.now()
        }
        
        # Upsert schedule
        db.key_rotation_schedules.update_one(
            {'organization_id': organization_id},
            {'$set': schedule_record},
            upsert=True
        )
        
        logger.info(f"Scheduled key rotation for organization {organization_id}")
        
    except Exception as e:
        logger.error(f"Error scheduling rotation jobs: {e}")