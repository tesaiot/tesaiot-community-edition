# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Certificate Service Modular Bridge
=================================
Version: v2025.08
Module: Certificate Bridge
Purpose: Bridge between legacy and modular certificate implementations

This module provides the integration layer between the existing
certificate_service.py and the new modular certificate service.
It uses feature flags and parallel runner to ensure safe migration.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from flask import g

from .feature_flags import feature_flags
from .parallel_runner import parallel_runner
from ..modules.security.interfaces import CertificateRequest
from ..modules.security.services.certificate_service import ModularCertificateService
from ..core.di_container import container

logger = logging.getLogger(__name__)

# Register the modular service in DI container
container.register_singleton(ModularCertificateService, ModularCertificateService)


async def issue_device_certificate_modular(device_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modular implementation of certificate issuance.
    
    This function wraps the modular certificate service to match
    the legacy interface and return format.
    """
    try:
        # Get modular service from DI container
        cert_service = container.resolve(ModularCertificateService)
        
        # Create certificate request
        request = CertificateRequest(
            device_id=device_id,
            device_name=device_id,  # Use device_id as name if not available
            organization_id=user.get('organization_id', 'default'),
            common_name=device_id,
            validity_days=365
        )
        
        # Generate certificate
        certificate = await cert_service.generate_certificate(request)
        
        # Convert to legacy format
        return {
            'success': True,
            'certificate_id': certificate.serial_number,
            'device_id': certificate.device_id,
            'certificate': certificate.certificate_pem,
            'private_key': certificate.private_key_pem,
            'ca_chain': certificate.chain_pem,
            'fingerprint': certificate.fingerprint,
            'serial_number': certificate.serial_number,
            'subject': certificate.subject,
            'issuer': certificate.issuer,
            'not_before': certificate.not_before.isoformat(),
            'not_after': certificate.not_after.isoformat(),
            'algorithm': certificate.algorithm,
            'status': certificate.status
        }
        
    except Exception as e:
        logger.error(f"Modular certificate generation failed: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def issue_device_certificate_with_parallel(device_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper function that runs both legacy and modular implementations
    in parallel when the feature flag is enabled.
    
    This function is called from the existing certificate_service.py
    to enable gradual migration.
    """
    # Check feature flag
    from flask import has_request_context
    
    context = {
        'user_id': user.get('_id') or user.get('id'),
        'is_internal': user.get('is_internal', False),
        'ip': g.get('client_ip', '127.0.0.1') if has_request_context() else '127.0.0.1'
    }
    
    if not feature_flags.is_enabled('modular_certificates', context):
        # Feature disabled, return None to use legacy implementation
        return None
    
    try:
        # Import the legacy function to avoid circular imports
        from .certificate_service import issue_device_certificate as legacy_issue_certificate
        
        # Create async wrapper for legacy function
        async def legacy_wrapper():
            return legacy_issue_certificate(device_id, user)
        
        # Create async wrapper for modular function
        async def modular_wrapper():
            return await issue_device_certificate_modular(device_id, user)
        
        # Run in parallel
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            parallel_runner.run_parallel(
                module_name="security.certificates",
                function_name="issue_device_certificate",
                old_func=lambda: legacy_issue_certificate(device_id, user),
                new_func=lambda: loop.run_until_complete(issue_device_certificate_modular(device_id, user))
            )
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Parallel certificate generation failed: {str(e)}")
        feature_flags.record_error('modular_certificates')
        # Return None to fallback to legacy implementation
        return None


def get_certificate_info_with_parallel(device_id: str, user: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Wrapper for getting certificate info with parallel execution.
    """
    context = {
        'user_id': user.get('_id') if user else None,
        'is_internal': user.get('is_internal', False) if user else False,
        'ip': g.get('client_ip', '127.0.0.1')
    }
    
    if not feature_flags.is_enabled('modular_certificates', context):
        return None
    
    try:
        from .certificate_service import get_device_certificate_info as legacy_get_info
        
        async def modular_get_info():
            cert_service = container.resolve(ModularCertificateService)
            certificate = await cert_service.get_certificate(device_id)
            
            if not certificate:
                return {'exists': False, 'message': 'Certificate not found'}
            
            return {
                'exists': True,
                'certificate_id': certificate.serial_number,
                'device_id': certificate.device_id,
                'fingerprint': certificate.fingerprint,
                'serial_number': certificate.serial_number,
                'subject': certificate.subject,
                'issuer': certificate.issuer,
                'not_before': certificate.not_before.isoformat(),
                'not_after': certificate.not_after.isoformat(),
                'status': certificate.status,
                'algorithm': certificate.algorithm
            }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            parallel_runner.run_parallel(
                module_name="security.certificates",
                function_name="get_device_certificate_info",
                old_func=lambda: legacy_get_info(device_id, user),
                new_func=lambda: loop.run_until_complete(modular_get_info())
            )
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Parallel certificate info retrieval failed: {str(e)}")
        feature_flags.record_error('modular_certificates')
        return None


# Export functions
__all__ = [
    'issue_device_certificate_with_parallel',
    'get_certificate_info_with_parallel'
]