# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Security Module Interfaces for TESA IoT Platform
===============================================
Version: v2025.08
Module: Security Interfaces
Purpose: Define contracts for security-related services

This module defines the interfaces (abstract base classes) for all
security-related services including certificates, authentication,
and authorization. These interfaces enable loose coupling and
support the gradual modularization of the platform.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass

# Data Transfer Objects (DTOs)
@dataclass
class Certificate:
    """Certificate data transfer object."""
    device_id: str
    certificate_pem: str
    private_key_pem: Optional[str]
    chain_pem: Optional[str]
    fingerprint: str
    serial_number: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime
    status: str
    algorithm: str
    created_at: datetime
    updated_at: datetime

@dataclass
class CertificateRequest:
    """Certificate request data transfer object."""
    device_id: str
    device_name: str
    organization_id: str
    common_name: str
    country: Optional[str] = None
    state: Optional[str] = None
    locality: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    key_size: int = 2048
    validity_days: int = 365

@dataclass
class CertificateRevocation:
    """Certificate revocation data transfer object."""
    certificate_id: str
    reason: str
    revoked_at: datetime
    revoked_by: str

# Interfaces
class ICertificateService(ABC):
    """
    Interface for certificate management operations.
    Handles device certificate lifecycle including issuance,
    renewal, revocation, and validation.
    """
    
    @abstractmethod
    async def generate_certificate(
        self, 
        request: CertificateRequest
    ) -> Certificate:
        """
        Generate a new certificate for a device.
        
        Args:
            request: Certificate request details
            
        Returns:
            Generated certificate
            
        Raises:
            CertificateGenerationError: If generation fails
        """
        pass
    
    @abstractmethod
    async def get_certificate(
        self, 
        device_id: str
    ) -> Optional[Certificate]:
        """
        Get certificate for a specific device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Certificate if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def revoke_certificate(
        self, 
        device_id: str, 
        reason: str, 
        user_id: str
    ) -> CertificateRevocation:
        """
        Revoke a device certificate.
        
        Args:
            device_id: Device identifier
            reason: Revocation reason
            user_id: User performing the revocation
            
        Returns:
            Revocation details
            
        Raises:
            CertificateNotFoundError: If certificate not found
        """
        pass
    
    @abstractmethod
    async def renew_certificate(
        self, 
        device_id: str, 
        validity_days: int = 365
    ) -> Certificate:
        """
        Renew an existing certificate.
        
        Args:
            device_id: Device identifier
            validity_days: New certificate validity period
            
        Returns:
            Renewed certificate
            
        Raises:
            CertificateRenewalError: If renewal fails
        """
        pass
    
    @abstractmethod
    async def validate_certificate(
        self, 
        certificate_pem: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a certificate.
        
        Args:
            certificate_pem: Certificate in PEM format
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    @abstractmethod
    async def list_certificates(
        self, 
        organization_id: str, 
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Certificate], int]:
        """
        List certificates for an organization.
        
        Args:
            organization_id: Organization identifier
            status: Filter by status (active, revoked, expired)
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            Tuple of (certificates, total_count)
        """
        pass
    
    @abstractmethod
    async def get_certificate_chain(
        self, 
        device_id: str
    ) -> Optional[str]:
        """
        Get the full certificate chain for a device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Certificate chain in PEM format if found
        """
        pass
    
    @abstractmethod
    async def bulk_revoke_certificates(
        self, 
        device_ids: List[str], 
        reason: str, 
        user_id: str
    ) -> List[CertificateRevocation]:
        """
        Bulk revoke multiple certificates.
        
        Args:
            device_ids: List of device identifiers
            reason: Revocation reason
            user_id: User performing the revocation
            
        Returns:
            List of revocation details
        """
        pass

class IAuthenticationService(ABC):
    """
    Interface for authentication operations.
    Handles user and device authentication.
    """
    
    @abstractmethod
    async def authenticate_user(
        self, 
        username: str, 
        password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user with credentials.
        
        Args:
            username: User's username or email
            password: User's password
            
        Returns:
            User details and tokens if successful, None otherwise
        """
        pass
    
    @abstractmethod
    async def authenticate_device(
        self, 
        device_id: str, 
        certificate: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate a device using certificate or API key.
        
        Args:
            device_id: Device identifier
            certificate: Device certificate (optional)
            api_key: Device API key (optional)
            
        Returns:
            Device details if authenticated, None otherwise
        """
        pass
    
    @abstractmethod
    async def validate_token(
        self, 
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate an authentication token.
        
        Args:
            token: JWT or session token
            
        Returns:
            Token claims if valid, None otherwise
        """
        pass
    
    @abstractmethod
    async def refresh_token(
        self, 
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh an authentication token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens if successful, None otherwise
        """
        pass
    
    @abstractmethod
    async def revoke_token(
        self, 
        token: str
    ) -> bool:
        """
        Revoke an authentication token.
        
        Args:
            token: Token to revoke
            
        Returns:
            True if revoked successfully
        """
        pass

class IAuthorizationService(ABC):
    """
    Interface for authorization operations.
    Handles role-based access control (RBAC).
    """
    
    @abstractmethod
    async def check_permission(
        self, 
        user_id: str, 
        resource: str, 
        action: str
    ) -> bool:
        """
        Check if a user has permission for an action.
        
        Args:
            user_id: User identifier
            resource: Resource being accessed
            action: Action being performed
            
        Returns:
            True if authorized, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_user_roles(
        self, 
        user_id: str
    ) -> List[str]:
        """
        Get roles assigned to a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of role names
        """
        pass
    
    @abstractmethod
    async def assign_role(
        self, 
        user_id: str, 
        role: str
    ) -> bool:
        """
        Assign a role to a user.
        
        Args:
            user_id: User identifier
            role: Role name
            
        Returns:
            True if assigned successfully
        """
        pass
    
    @abstractmethod
    async def revoke_role(
        self, 
        user_id: str, 
        role: str
    ) -> bool:
        """
        Revoke a role from a user.
        
        Args:
            user_id: User identifier
            role: Role name
            
        Returns:
            True if revoked successfully
        """
        pass
    
    @abstractmethod
    async def get_role_permissions(
        self, 
        role: str
    ) -> List[Dict[str, str]]:
        """
        Get permissions for a role.
        
        Args:
            role: Role name
            
        Returns:
            List of permissions (resource, action pairs)
        """
        pass

# Exception classes
class CertificateGenerationError(Exception):
    """Raised when certificate generation fails."""
    pass

class CertificateNotFoundError(Exception):
    """Raised when certificate is not found."""
    pass

class CertificateRenewalError(Exception):
    """Raised when certificate renewal fails."""
    pass

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass

# Module exports
__all__ = [
    # DTOs
    'Certificate',
    'CertificateRequest',
    'CertificateRevocation',
    # Interfaces
    'ICertificateService',
    'IAuthenticationService',
    'IAuthorizationService',
    # Exceptions
    'CertificateGenerationError',
    'CertificateNotFoundError',
    'CertificateRenewalError',
    'AuthenticationError',
    'AuthorizationError'
]