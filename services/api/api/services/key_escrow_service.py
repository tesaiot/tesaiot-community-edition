# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Key Escrow Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import logging
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum

from ..core.database import get_db
from .audit_service import audit_log, AuditAction
from .vault_key_service import vault_key_service
from .notification_service import send_email_notification

logger = logging.getLogger(__name__)

class EscrowStatus(str, Enum):
    """Escrow status enumeration."""
    PENDING = "pending"
    ESCROWED = "escrowed"
    RELEASED = "released"
    EXPIRED = "expired"
    REVOKED = "revoked"

class EscrowError(Exception):
    """Custom escrow error."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

class KeyEscrowService:
    """Service for managing key escrow and secure distribution."""
    
    def __init__(self):
        self.db = None
        
    def get_db(self):
        """Get database connection with lazy initialization."""
        if not self.db:
            self.db = get_db()
        return self.db
    
    def escrow_key(self, device_id: str, key_id: str, organization_id: str,
                   escrow_conditions: Dict, user: Dict) -> Dict:
        """
        Escrow a key with specified conditions.
        
        Args:
            device_id: Device identifier
            key_id: Key identifier
            organization_id: Organization ID
            escrow_conditions: Escrow release conditions
            user: User performing escrow
            
        Returns:
            Escrow information
        """
        try:
            db = self.get_db()
            
            # Validate key exists
            key_record = db.device_keys.find_one({
                'key_id': key_id,
                'device_id': device_id,
                'organization_id': organization_id
            })
            
            if not key_record:
                raise EscrowError("Key not found", "KEY_NOT_FOUND")
            
            # Create escrow record
            escrow_id = str(uuid.uuid4())
            escrow_record = {
                'escrow_id': escrow_id,
                'device_id': device_id,
                'key_id': key_id,
                'organization_id': organization_id,
                'escrowed_at': datetime.now(),
                'escrowed_by': user.get('email'),
                'status': EscrowStatus.ESCROWED,
                'release_conditions': {
                    'requires_approval': escrow_conditions.get('requires_approval', True),
                    'authorized_users': escrow_conditions.get('authorized_users', [user.get('email')]),
                    'expires_at': datetime.now() + timedelta(
                        hours=escrow_conditions.get('expiry_hours', 168)  # 7 days default
                    ),
                    'release_reason_required': escrow_conditions.get('release_reason_required', True),
                    'multi_approval_required': escrow_conditions.get('multi_approval_required', False),
                    'approval_threshold': escrow_conditions.get('approval_threshold', 1)
                },
                'access_log': [],
                'release_history': [],
                'metadata': escrow_conditions.get('metadata', {})
            }
            
            # Generate secure escrow tokens
            escrow_tokens = self._generate_escrow_tokens(escrow_id, escrow_conditions)
            escrow_record['escrow_tokens'] = escrow_tokens
            
            # Store escrow record
            db.key_escrow.insert_one(escrow_record)
            
            # Update key status
            db.device_keys.update_one(
                {'key_id': key_id},
                {
                    '$set': {
                        'escrow_status': 'escrowed',
                        'escrow_id': escrow_id,
                        'escrowed_at': datetime.now()
                    }
                }
            )
            
            # Send notification to authorized users
            self._notify_escrow_users(escrow_record)
            
            # Audit log
            audit_log(
                action=AuditAction.KEY_ESCROW,
                user=user,
                resource_type='key_escrow',
                resource_id=escrow_id,
                details={
                    'device_id': device_id,
                    'key_id': key_id,
                    'expires_at': escrow_record['release_conditions']['expires_at'].isoformat(),
                    'authorized_users': escrow_record['release_conditions']['authorized_users']
                }
            )
            
            logger.info(f"Escrowed key {key_id} for device {device_id}")
            
            return {
                'escrow_id': escrow_id,
                'status': EscrowStatus.ESCROWED,
                'expires_at': escrow_record['release_conditions']['expires_at'].isoformat(),
                'access_tokens': [token['token'] for token in escrow_tokens],
                'authorized_users': escrow_record['release_conditions']['authorized_users']
            }
            
        except Exception as e:
            logger.error(f"Error escrowing key: {e}")
            raise EscrowError(f"Key escrow failed: {str(e)}")
    
    def release_escrowed_key(self, escrow_id: str, release_token: str,
                           release_reason: str, user: Dict) -> Dict:
        """
        Release an escrowed key.
        
        Args:
            escrow_id: Escrow identifier
            release_token: Release token
            release_reason: Reason for release
            user: User requesting release
            
        Returns:
            Key data if release is authorized
        """
        try:
            db = self.get_db()
            
            # Find escrow record
            escrow_record = db.key_escrow.find_one({'escrow_id': escrow_id})
            
            if not escrow_record:
                raise EscrowError("Escrow not found", "ESCROW_NOT_FOUND")
            
            # Check escrow status
            if escrow_record['status'] != EscrowStatus.ESCROWED:
                raise EscrowError("Escrow not in escrowed status", "INVALID_STATUS")
            
            # Check expiration
            expires_at = escrow_record['release_conditions']['expires_at']
            if expires_at < datetime.now():
                # Mark as expired
                db.key_escrow.update_one(
                    {'escrow_id': escrow_id},
                    {'$set': {'status': EscrowStatus.EXPIRED}}
                )
                raise EscrowError("Escrow has expired", "ESCROW_EXPIRED")
            
            # Validate release token
            valid_token = self._validate_release_token(escrow_record, release_token, user)
            if not valid_token:
                raise EscrowError("Invalid release token", "INVALID_TOKEN")
            
            # Check authorization
            authorized_users = escrow_record['release_conditions']['authorized_users']
            if user.get('email') not in authorized_users:
                raise EscrowError("User not authorized for release", "UNAUTHORIZED")
            
            # Check if approval is required
            if escrow_record['release_conditions']['requires_approval']:
                # Handle multi-approval logic
                if escrow_record['release_conditions'].get('multi_approval_required'):
                    approval_count = len(escrow_record.get('approvals', []))
                    threshold = escrow_record['release_conditions'].get('approval_threshold', 1)
                    
                    if approval_count < threshold:
                        # Add approval but don't release yet
                        approval_record = {
                            'approved_by': user.get('email'),
                            'approved_at': datetime.now(),
                            'reason': release_reason,
                            'ip_address': user.get('ip_address', 'unknown')
                        }
                        
                        db.key_escrow.update_one(
                            {'escrow_id': escrow_id},
                            {'$push': {'approvals': approval_record}}
                        )
                        
                        return {
                            'status': 'approval_recorded',
                            'approvals_needed': threshold - (approval_count + 1),
                            'approved_by': user.get('email')
                        }
            
            # Get the actual key data
            key_data = self._get_key_for_release(escrow_record)
            
            # Record release
            release_record = {
                'released_by': user.get('email'),
                'released_at': datetime.now(),
                'reason': release_reason,
                'ip_address': user.get('ip_address', 'unknown'),
                'token_used': release_token[:8] + '...'  # Partial token for audit
            }
            
            # Update escrow status
            db.key_escrow.update_one(
                {'escrow_id': escrow_id},
                {
                    '$set': {
                        'status': EscrowStatus.RELEASED,
                        'released_at': datetime.now()
                    },
                    '$push': {'release_history': release_record}
                }
            )
            
            # Update key status
            db.device_keys.update_one(
                {'key_id': escrow_record['key_id']},
                {
                    '$set': {
                        'escrow_status': 'released',
                        'released_at': datetime.now()
                    }
                }
            )
            
            # Log access
            access_record = {
                'accessed_by': user.get('email'),
                'accessed_at': datetime.now(),
                'action': 'release',
                'ip_address': user.get('ip_address', 'unknown')
            }
            
            db.key_escrow.update_one(
                {'escrow_id': escrow_id},
                {'$push': {'access_log': access_record}}
            )
            
            # Audit log
            audit_log(
                action=AuditAction.KEY_RELEASE,
                user=user,
                resource_type='key_escrow',
                resource_id=escrow_id,
                details={
                    'device_id': escrow_record['device_id'],
                    'key_id': escrow_record['key_id'],
                    'reason': release_reason
                }
            )
            
            logger.info(f"Released escrowed key {escrow_record['key_id']} for device {escrow_record['device_id']}")
            
            return {
                'status': 'released',
                'key_data': key_data,
                'released_at': datetime.now().isoformat(),
                'device_id': escrow_record['device_id']
            }
            
        except Exception as e:
            logger.error(f"Error releasing escrowed key: {e}")
            raise EscrowError(f"Key release failed: {str(e)}")
    
    def get_escrow_status(self, escrow_id: str, user: Dict) -> Optional[Dict]:
        """
        Get escrow status information.
        
        Args:
            escrow_id: Escrow identifier
            user: User requesting status
            
        Returns:
            Escrow status information or None if not found
        """
        try:
            db = self.get_db()
            
            escrow_record = db.key_escrow.find_one({'escrow_id': escrow_id})
            
            if not escrow_record:
                return None
            
            # Check if user is authorized to view
            authorized_users = escrow_record['release_conditions']['authorized_users']
            if user.get('email') not in authorized_users and user.get('role') not in ['admin', 'super_admin']:
                raise EscrowError("Not authorized to view escrow status", "UNAUTHORIZED")
            
            # Log access
            access_record = {
                'accessed_by': user.get('email'),
                'accessed_at': datetime.now(),
                'action': 'view',
                'ip_address': user.get('ip_address', 'unknown')
            }
            
            db.key_escrow.update_one(
                {'escrow_id': escrow_id},
                {'$push': {'access_log': access_record}}
            )
            
            # Check if expired
            current_time = datetime.now()
            expires_at = escrow_record['release_conditions']['expires_at']
            is_expired = expires_at < current_time
            
            if is_expired and escrow_record['status'] == EscrowStatus.ESCROWED:
                # Update status to expired
                db.key_escrow.update_one(
                    {'escrow_id': escrow_id},
                    {'$set': {'status': EscrowStatus.EXPIRED}}
                )
                escrow_record['status'] = EscrowStatus.EXPIRED
            
            return {
                'escrow_id': escrow_id,
                'device_id': escrow_record['device_id'],
                'key_id': escrow_record['key_id'],
                'status': escrow_record['status'],
                'escrowed_at': escrow_record['escrowed_at'].isoformat(),
                'escrowed_by': escrow_record['escrowed_by'],
                'expires_at': expires_at.isoformat(),
                'is_expired': is_expired,
                'authorized_users': authorized_users,
                'requires_approval': escrow_record['release_conditions']['requires_approval'],
                'multi_approval_required': escrow_record['release_conditions'].get('multi_approval_required', False),
                'approval_threshold': escrow_record['release_conditions'].get('approval_threshold', 1),
                'current_approvals': len(escrow_record.get('approvals', [])),
                'access_count': len(escrow_record.get('access_log', [])),
                'release_count': len(escrow_record.get('release_history', []))
            }
            
        except Exception as e:
            logger.error(f"Error getting escrow status: {e}")
            raise EscrowError(f"Failed to get escrow status: {str(e)}")
    
    def list_organization_escrows(self, organization_id: str, user: Dict,
                                status_filter: Optional[str] = None) -> List[Dict]:
        """
        List escrows for an organization.
        
        Args:
            organization_id: Organization ID
            user: User requesting list
            status_filter: Optional status filter
            
        Returns:
            List of escrow records
        """
        try:
            db = self.get_db()
            
            # Build query
            query = {'organization_id': organization_id}
            if status_filter:
                query['status'] = status_filter
            
            # For non-admin users, only show escrows they're authorized for
            if user.get('role') not in ['admin', 'super_admin']:
                query['release_conditions.authorized_users'] = user.get('email')
            
            escrows = list(db.key_escrow.find(query).sort('escrowed_at', -1))
            
            escrow_list = []
            for escrow in escrows:
                escrow_info = {
                    'escrow_id': escrow['escrow_id'],
                    'device_id': escrow['device_id'],
                    'key_id': escrow['key_id'],
                    'status': escrow['status'],
                    'escrowed_at': escrow['escrowed_at'].isoformat(),
                    'escrowed_by': escrow['escrowed_by'],
                    'expires_at': escrow['release_conditions']['expires_at'].isoformat(),
                    'requires_approval': escrow['release_conditions']['requires_approval'],
                    'authorized_users_count': len(escrow['release_conditions']['authorized_users']),
                    'access_count': len(escrow.get('access_log', [])),
                    'is_authorized': user.get('email') in escrow['release_conditions']['authorized_users']
                }
                escrow_list.append(escrow_info)
            
            return escrow_list
            
        except Exception as e:
            logger.error(f"Error listing escrows: {e}")
            raise EscrowError(f"Failed to list escrows: {str(e)}")
    
    def _generate_escrow_tokens(self, escrow_id: str, conditions: Dict) -> List[Dict]:
        """
        Generate secure tokens for escrow access.
        
        Args:
            escrow_id: Escrow identifier
            conditions: Escrow conditions
            
        Returns:
            List of token records
        """
        tokens = []
        authorized_users = conditions.get('authorized_users', [])
        
        for user_email in authorized_users:
            token = secrets.token_urlsafe(32)
            token_record = {
                'token': token,
                'user_email': user_email,
                'created_at': datetime.now(),
                'expires_at': conditions.get('expires_at', datetime.now() + timedelta(days=7)),
                'used': False,
                'use_count': 0,
                'max_uses': 1
            }
            tokens.append(token_record)
        
        return tokens
    
    def _validate_release_token(self, escrow_record: Dict, token: str, user: Dict) -> bool:
        """
        Validate a release token.
        
        Args:
            escrow_record: Escrow record
            token: Token to validate
            user: User attempting to use token
            
        Returns:
            True if token is valid
        """
        escrow_tokens = escrow_record.get('escrow_tokens', [])
        user_email = user.get('email')
        
        for token_record in escrow_tokens:
            if (token_record['token'] == token and 
                token_record['user_email'] == user_email and
                not token_record['used'] and
                token_record['expires_at'] > datetime.now()):
                
                # Mark token as used
                db = self.get_db()
                db.key_escrow.update_one(
                    {
                        'escrow_id': escrow_record['escrow_id'],
                        'escrow_tokens.token': token
                    },
                    {
                        '$set': {
                            'escrow_tokens.$.used': True,
                            'escrow_tokens.$.used_at': datetime.now()
                        },
                        '$inc': {'escrow_tokens.$.use_count': 1}
                    }
                )
                
                return True
        
        return False
    
    def _get_key_for_release(self, escrow_record: Dict) -> Dict:
        """
        Get key data for release from escrow.
        
        Args:
            escrow_record: Escrow record
            
        Returns:
            Key data
        """
        db = self.get_db()
        
        key_record = db.device_keys.find_one({'key_id': escrow_record['key_id']})
        
        if not key_record:
            raise EscrowError("Key not found", "KEY_NOT_FOUND")
        
        # Get key from Vault if stored there
        if key_record.get('vault_path'):
            try:
                vault_key_data = vault_key_service.retrieve_key_from_vault(
                    key_record['vault_path'],
                    {'email': 'escrow_service', 'role': 'system'}
                )
                if vault_key_data:
                    return {
                        'private_key_pem': vault_key_data['private_key_pem'],
                        'public_key_pem': vault_key_data['public_key_pem'],
                        'algorithm': vault_key_data['algorithm'],
                        'source': 'vault'
                    }
            except Exception as e:
                logger.warning(f"Failed to retrieve key from Vault: {e}")
        
        # Fallback to encrypted key in database
        if key_record.get('encrypted_private_key'):
            # In production, implement proper key decryption
            # For now, return public key only for security
            return {
                'public_key_pem': key_record.get('public_key_pem'),
                'algorithm': key_record.get('algorithm'),
                'source': 'database',
                'note': 'Private key requires additional decryption'
            }
        
        raise EscrowError("Key data not accessible", "KEY_DATA_UNAVAILABLE")
    
    def _notify_escrow_users(self, escrow_record: Dict):
        """
        Send notifications to authorized users about key escrow.
        
        Args:
            escrow_record: Escrow record
        """
        try:
            authorized_users = escrow_record['release_conditions']['authorized_users']
            device_id = escrow_record['device_id']
            escrow_id = escrow_record['escrow_id']
            expires_at = escrow_record['release_conditions']['expires_at']
            
            subject = f"[TESA IoT] Key Escrowed - Device {device_id}"
            body = f"""
A device key has been placed in escrow and requires your authorization for release.

Device ID: {device_id}
Escrow ID: {escrow_id}
Escrowed At: {escrow_record['escrowed_at'].isoformat()}
Expires At: {expires_at.isoformat()}

To release this key, you will need to:
1. Access the TESA IoT Platform
2. Navigate to Key Management > Escrow
3. Use your authorization token to release the key

This escrow will expire automatically if not released before the expiration time.

If you have any questions, please contact your system administrator.

Best regards,
TESA IoT Platform
"""
            
            for user_email in authorized_users:
                try:
                    send_email_notification(user_email, subject, body)
                except Exception as e:
                    logger.warning(f"Failed to send escrow notification to {user_email}: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending escrow notifications: {e}")

# Create service instance
key_escrow_service = KeyEscrowService()