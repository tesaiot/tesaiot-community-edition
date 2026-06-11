# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Vault Integration Service
Week 3 Day 1 - Vault Agent Configuration and PKI CA Management
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.




Version: v2025.08-Week3-Day1
Module: Vault Integration Service
Build: 2025-08-05 12:00:00 UTC
Status: PRODUCTION READY
Compliance: ETSI EN 303 645, ISO/IEC 27402

Enhanced Vault integration service with Vault Agent support,
PKI management, and comprehensive security features.
"""

import os
from typing import Dict, Any
from datetime import datetime
import hvac
import requests
from cryptography import x509

from api.core.exceptions import VaultError, PKIError
from api.core.logging import get_logger

logger = get_logger(__name__)

class VaultIntegrationService:
    """Enhanced Vault Integration Service with PKI and Vault Agent support"""
    
    def __init__(self):
        self.vault_addr = os.getenv('VAULT_ADDR', 'https://127.0.0.1:8200')
        self.vault_namespace = os.getenv('VAULT_NAMESPACE', 'admin/tesa-iot')
        self.vault_agent_addr = os.getenv('VAULT_AGENT_ADDR', 'http://127.0.0.1:8100')
        self.vault_token = os.getenv('VAULT_TOKEN')
        
        # PKI mount points
        self.root_pki_mount = os.getenv('VAULT_ROOT_PKI_MOUNT', 'pki')
        self.intermediate_pki_mount = os.getenv('VAULT_INTERMEDIATE_PKI_MOUNT', 'pki_int')
        
        # Connection timeout and retry settings
        self.connection_timeout = 30
        self.max_retries = 3
        self.retry_delay = 1
        
        self._client = None
        self._agent_client = None
        self._last_health_check = None
        self._health_check_interval = 300  # 5 minutes
    
    @property
    def client(self) -> hvac.Client:
        """Get Vault client with connection validation"""
        if not self._client or not self._is_client_healthy():
            self._initialize_client()
        return self._client
    
    @property
    def agent_client(self) -> hvac.Client:
        """Get Vault Agent client for proxied requests"""
        if not self._agent_client or not self._is_agent_healthy():
            self._initialize_agent_client()
        return self._agent_client
    
    def _initialize_client(self):
        """Initialize direct Vault client"""
        try:
            self._client = hvac.Client(
                url=self.vault_addr,
                namespace=self.vault_namespace,
                timeout=self.connection_timeout
            )
            
            # Authenticate with token if available
            if self.vault_token:
                self._client.token = self.vault_token
            
            # Verify authentication
            if not self._client.is_authenticated():
                raise VaultError("Failed to authenticate with Vault")
            
            logger.info("Direct Vault client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {str(e)}")
            raise VaultError(f"Vault client initialization failed: {str(e)}")
    
    def _initialize_agent_client(self):
        """Initialize Vault Agent client for proxied requests"""
        try:
            self._agent_client = hvac.Client(
                url=self.vault_agent_addr,
                timeout=self.connection_timeout
            )
            
            # Vault Agent handles authentication automatically
            logger.info("Vault Agent client initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Vault Agent client: {str(e)}")
            # Fall back to direct client if agent is not available
            self._agent_client = None
    
    def _is_client_healthy(self) -> bool:
        """Check if direct Vault client is healthy"""
        try:
            if not self._client:
                return False
            
            # Skip frequent health checks
            if self._last_health_check and \
               (datetime.now() - self._last_health_check).seconds < self._health_check_interval:
                return True
            
            # Perform health check
            health = self._client.sys.read_health_status()
            self._last_health_check = datetime.now()
            
            return health.get('initialized', False) and not health.get('sealed', True)
            
        except Exception as e:
            logger.debug(f"Vault client health check failed: {str(e)}")
            return False
    
    def _is_agent_healthy(self) -> bool:
        """Check if Vault Agent is healthy"""
        try:
            if not self._agent_client:
                return False
            
            # Simple health check via agent proxy
            response = requests.get(
                f"{self.vault_agent_addr}/v1/sys/health",
                timeout=5
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"Vault Agent health check failed: {str(e)}")
            return False
    
    def get_preferred_client(self) -> hvac.Client:
        """Get preferred client (Agent if available, otherwise direct)"""
        if self._is_agent_healthy():
            logger.debug("Using Vault Agent client")
            return self.agent_client
        else:
            logger.debug("Using direct Vault client")
            return self.client
    
    def is_authenticated(self) -> bool:
        """Check if any client is authenticated"""
        try:
            # Try agent first
            if self._is_agent_healthy():
                return True
            
            # Fall back to direct client
            return self.client.is_authenticated()
            
        except Exception as e:
            logger.error(f"Authentication check failed: {str(e)}")
            return False
    
    def get_vault_status(self) -> Dict[str, Any]:
        """Get comprehensive Vault status"""
        status = {
            'vault_server': {
                'address': self.vault_addr,
                'healthy': False,
                'authenticated': False,
                'sealed': True,
                'initialized': False,
                'version': 'unknown'
            },
            'vault_agent': {
                'address': self.vault_agent_addr,
                'healthy': False,
                'available': False
            },
            'pki_mounts': {
                'root': {'mounted': False, 'healthy': False},
                'intermediate': {'mounted': False, 'healthy': False}
            },
            'preferred_client': 'none',
            'last_check': datetime.utcnow().isoformat()
        }
        
        # Check Vault server
        try:
            health = self.client.sys.read_health_status()
            status['vault_server'].update({
                'healthy': True,
                'authenticated': self.client.is_authenticated(),
                'sealed': health.get('sealed', True),
                'initialized': health.get('initialized', False),
                'version': health.get('version', 'unknown')
            })
        except Exception as e:
            logger.debug(f"Vault server check failed: {str(e)}")
        
        # Check Vault Agent
        try:
            if self._is_agent_healthy():
                status['vault_agent'].update({
                    'healthy': True,
                    'available': True
                })
                status['preferred_client'] = 'agent'
        except Exception as e:
            logger.debug(f"Vault Agent check failed: {str(e)}")
        
        # Set preferred client
        if status['preferred_client'] == 'none' and status['vault_server']['healthy']:
            status['preferred_client'] = 'direct'
        
        # Check PKI mounts
        try:
            client = self.get_preferred_client()
            mounts = client.sys.list_auth_methods()
            
            if f"{self.root_pki_mount}/" in mounts:
                status['pki_mounts']['root']['mounted'] = True
                try:
                    client.secrets.pki.read_ca_certificate(mount_point=self.root_pki_mount)
                    status['pki_mounts']['root']['healthy'] = True
                except:
                    pass
            
            if f"{self.intermediate_pki_mount}/" in mounts:
                status['pki_mounts']['intermediate']['mounted'] = True
                try:
                    client.secrets.pki.read_ca_certificate(mount_point=self.intermediate_pki_mount)
                    status['pki_mounts']['intermediate']['healthy'] = True
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"PKI mount check failed: {str(e)}")
        
        return status
    
    def setup_pki_infrastructure(self) -> Dict[str, Any]:
        """Setup PKI infrastructure if not already configured"""
        try:
            client = self.get_preferred_client()
            setup_results = {
                'root_ca': {'status': 'checking', 'message': ''},
                'intermediate_ca': {'status': 'checking', 'message': ''},
                'roles': {'status': 'checking', 'message': ''}
            }
            
            # Enable PKI secrets engines if not already enabled
            try:
                mounts = client.sys.list_auth_methods()
                
                if f"{self.root_pki_mount}/" not in mounts:
                    client.sys.enable_secrets_engine(
                        backend_type='pki',
                        path=self.root_pki_mount,
                        config={'max_lease_ttl': '87600h'}  # 10 years
                    )
                    setup_results['root_ca']['message'] = 'PKI mount enabled'
                
                if f"{self.intermediate_pki_mount}/" not in mounts:
                    client.sys.enable_secrets_engine(
                        backend_type='pki',
                        path=self.intermediate_pki_mount,
                        config={'max_lease_ttl': '43800h'}  # 5 years
                    )
                    setup_results['intermediate_ca']['message'] = 'Intermediate PKI mount enabled'
                    
            except Exception as e:
                logger.error(f"Failed to enable PKI mounts: {str(e)}")
                raise PKIError(f"PKI mount setup failed: {str(e)}")
            
            # Check if root CA exists
            try:
                root_ca = client.secrets.pki.read_ca_certificate(mount_point=self.root_pki_mount)
                if root_ca:
                    setup_results['root_ca']['status'] = 'exists'
                    setup_results['root_ca']['message'] = 'Root CA already configured'
                else:
                    raise Exception("Root CA not found")
                    
            except Exception:
                # Generate root CA
                try:
                    root_ca_response = client.secrets.pki.generate_root(
                        type_name='internal',
                        common_name='TESA IoT Platform Root CA',
                        mount_point=self.root_pki_mount,
                        ttl='87600h',
                        key_type='rsa',
                        key_bits=4096,
                        exclude_cn_from_sans=True
                    )
                    
                    setup_results['root_ca']['status'] = 'created'
                    setup_results['root_ca']['message'] = 'Root CA generated successfully'
                    
                    # Configure CA URLs
                    client.secrets.pki.set_urls(
                        issuing_certificates=[f"{self.vault_addr}/v1/{self.root_pki_mount}/ca"],
                        crl_distribution_points=[f"{self.vault_addr}/v1/{self.root_pki_mount}/crl"],
                        mount_point=self.root_pki_mount
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to generate root CA: {str(e)}")
                    setup_results['root_ca']['status'] = 'failed'
                    setup_results['root_ca']['message'] = f'Root CA generation failed: {str(e)}'
            
            # Check if intermediate CA exists
            try:
                int_ca = client.secrets.pki.read_ca_certificate(mount_point=self.intermediate_pki_mount)
                if int_ca:
                    setup_results['intermediate_ca']['status'] = 'exists'
                    setup_results['intermediate_ca']['message'] = 'Intermediate CA already configured'
                else:
                    raise Exception("Intermediate CA not found")
                    
            except Exception:
                # Generate intermediate CA
                try:
                    # Generate intermediate CSR
                    int_csr_response = client.secrets.pki.generate_intermediate(
                        type_name='internal',
                        common_name='TESA IoT Platform Intermediate CA',
                        mount_point=self.intermediate_pki_mount,
                        key_type='rsa',
                        key_bits=2048,
                        exclude_cn_from_sans=True
                    )
                    
                    if 'data' not in int_csr_response or 'csr' not in int_csr_response['data']:
                        raise Exception("Failed to generate intermediate CSR")
                    
                    csr = int_csr_response['data']['csr']
                    
                    # Sign intermediate CSR with root CA
                    signed_cert_response = client.secrets.pki.sign_intermediate(
                        csr=csr,
                        common_name='TESA IoT Platform Intermediate CA',
                        mount_point=self.root_pki_mount,
                        ttl='43800h',
                        exclude_cn_from_sans=True
                    )
                    
                    if 'data' not in signed_cert_response or 'certificate' not in signed_cert_response['data']:
                        raise Exception("Failed to sign intermediate certificate")
                    
                    signed_cert = signed_cert_response['data']['certificate']
                    ca_chain = signed_cert_response['data'].get('ca_chain', [])
                    
                    # Set intermediate certificate
                    client.secrets.pki.set_signed_intermediate(
                        certificate=signed_cert,
                        mount_point=self.intermediate_pki_mount
                    )
                    
                    setup_results['intermediate_ca']['status'] = 'created'
                    setup_results['intermediate_ca']['message'] = 'Intermediate CA generated and signed successfully'
                    
                    # Configure intermediate CA URLs
                    client.secrets.pki.set_urls(
                        issuing_certificates=[f"{self.vault_addr}/v1/{self.intermediate_pki_mount}/ca"],
                        crl_distribution_points=[f"{self.vault_addr}/v1/{self.intermediate_pki_mount}/crl"],
                        mount_point=self.intermediate_pki_mount
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to generate intermediate CA: {str(e)}")
                    setup_results['intermediate_ca']['status'] = 'failed'
                    setup_results['intermediate_ca']['message'] = f'Intermediate CA generation failed: {str(e)}'
            
            # Setup default roles
            try:
                default_roles = [
                    {
                        'name': 'server-cert',
                        'config': {
                            'allowed_domains': ['*.tesa-iot.local', 'localhost'],
                            'allow_subdomains': True,
                            'allow_bare_domains': True,
                            'allow_localhost': True,
                            'allow_ip_sans': True,
                            'max_ttl': '720h',
                            'key_type': 'rsa',
                            'key_bits': 2048,
                            'server_flag': True,
                            'client_flag': False
                        }
                    },
                    {
                        'name': 'client-cert',
                        'config': {
                            'allowed_domains': ['*.tesa-iot.local'],
                            'allow_subdomains': True,
                            'max_ttl': '720h',
                            'key_type': 'rsa',
                            'key_bits': 2048,
                            'server_flag': False,
                            'client_flag': True
                        }
                    },
                    {
                        'name': 'device-cert',
                        'config': {
                            'allowed_domains': ['device-*.tesa-iot.local'],
                            'allow_subdomains': False,
                            'allow_any_name': True,
                            'max_ttl': '8760h',  # 1 year
                            'key_type': 'rsa',
                            'key_bits': 2048,
                            'server_flag': False,
                            'client_flag': True
                        }
                    }
                ]
                
                created_roles = []
                for role in default_roles:
                    try:
                        client.secrets.pki.create_or_update_role(
                            name=role['name'],
                            mount_point=self.intermediate_pki_mount,
                            **role['config']
                        )
                        created_roles.append(role['name'])
                    except Exception as e:
                        logger.warning(f"Failed to create role {role['name']}: {str(e)}")
                
                setup_results['roles']['status'] = 'created'
                setup_results['roles']['message'] = f'Created {len(created_roles)} default roles: {", ".join(created_roles)}'
                
            except Exception as e:
                logger.error(f"Failed to setup default roles: {str(e)}")
                setup_results['roles']['status'] = 'failed'
                setup_results['roles']['message'] = f'Role setup failed: {str(e)}'
            
            return setup_results
            
        except Exception as e:
            logger.error(f"PKI infrastructure setup failed: {str(e)}")
            raise PKIError(f"PKI infrastructure setup failed: {str(e)}")
    
    def get_certificate_chain(self, include_root: bool = True) -> Dict[str, str]:
        """Get the complete certificate chain"""
        try:
            client = self.get_preferred_client()
            chain = {}
            
            # Get root CA certificate
            try:
                root_ca_response = client.secrets.pki.read_ca_certificate(
                    mount_point=self.root_pki_mount,
                    format='pem'
                )
                if root_ca_response and 'data' in root_ca_response:
                    chain['root_ca'] = root_ca_response['data']['certificate']
            except Exception as e:
                logger.warning(f"Failed to get root CA certificate: {str(e)}")
            
            # Get intermediate CA certificate
            try:
                int_ca_response = client.secrets.pki.read_ca_certificate(
                    mount_point=self.intermediate_pki_mount,
                    format='pem'
                )
                if int_ca_response and 'data' in int_ca_response:
                    chain['intermediate_ca'] = int_ca_response['data']['certificate']
            except Exception as e:
                logger.warning(f"Failed to get intermediate CA certificate: {str(e)}")
            
            # Create combined chain
            if include_root and 'root_ca' in chain and 'intermediate_ca' in chain:
                chain['full_chain'] = chain['intermediate_ca'] + '\n' + chain['root_ca']
            elif 'intermediate_ca' in chain:
                chain['ca_chain'] = chain['intermediate_ca']
            
            return chain
            
        except Exception as e:
            logger.error(f"Failed to get certificate chain: {str(e)}")
            raise PKIError(f"Certificate chain retrieval failed: {str(e)}")
    
    def validate_certificate_health(self) -> Dict[str, Any]:
        """Validate PKI certificate health"""
        try:
            client = self.get_preferred_client()
            health = {
                'overall_status': 'healthy',
                'root_ca': {'status': 'unknown', 'expires_in_days': 0, 'issues': []},
                'intermediate_ca': {'status': 'unknown', 'expires_in_days': 0, 'issues': []},
                'certificate_count': 0,
                'expiring_certificates': [],
                'revoked_certificates': [],
                'recommendations': []
            }
            
            now = datetime.utcnow()
            
            # Check root CA
            try:
                root_ca_data = client.secrets.pki.read_ca_certificate(
                    mount_point=self.root_pki_mount
                )
                if root_ca_data and 'data' in root_ca_data:
                    cert_pem = root_ca_data['data']['certificate']
                    cert = x509.load_pem_x509_certificate(cert_pem.encode())
                    
                    expires_in = (cert.not_valid_after - now).days
                    health['root_ca']['expires_in_days'] = expires_in
                    
                    if expires_in < 30:
                        health['root_ca']['status'] = 'critical'
                        health['root_ca']['issues'].append('Expires within 30 days')
                        health['overall_status'] = 'critical'
                    elif expires_in < 90:
                        health['root_ca']['status'] = 'warning'
                        health['root_ca']['issues'].append('Expires within 90 days')
                        if health['overall_status'] == 'healthy':
                            health['overall_status'] = 'warning'
                    else:
                        health['root_ca']['status'] = 'healthy'
                        
            except Exception as e:
                health['root_ca']['status'] = 'error'
                health['root_ca']['issues'].append(f'Cannot read certificate: {str(e)}')
                health['overall_status'] = 'critical'
            
            # Check intermediate CA
            try:
                int_ca_data = client.secrets.pki.read_ca_certificate(
                    mount_point=self.intermediate_pki_mount
                )
                if int_ca_data and 'data' in int_ca_data:
                    cert_pem = int_ca_data['data']['certificate']
                    cert = x509.load_pem_x509_certificate(cert_pem.encode())
                    
                    expires_in = (cert.not_valid_after - now).days
                    health['intermediate_ca']['expires_in_days'] = expires_in
                    
                    if expires_in < 30:
                        health['intermediate_ca']['status'] = 'critical'
                        health['intermediate_ca']['issues'].append('Expires within 30 days')
                        health['overall_status'] = 'critical'
                    elif expires_in < 90:
                        health['intermediate_ca']['status'] = 'warning'
                        health['intermediate_ca']['issues'].append('Expires within 90 days')
                        if health['overall_status'] == 'healthy':
                            health['overall_status'] = 'warning'
                    else:
                        health['intermediate_ca']['status'] = 'healthy'
                        
            except Exception as e:
                health['intermediate_ca']['status'] = 'error'
                health['intermediate_ca']['issues'].append(f'Cannot read certificate: {str(e)}')
                health['overall_status'] = 'critical'
            
            # Check issued certificates
            try:
                cert_list = client.secrets.pki.list_certificates(
                    mount_point=self.intermediate_pki_mount
                )
                
                if cert_list and 'data' in cert_list and 'keys' in cert_list['data']:
                    health['certificate_count'] = len(cert_list['data']['keys'])
                    
                    for serial in cert_list['data']['keys']:
                        try:
                            cert_data = client.secrets.pki.read_certificate(
                                serial=serial,
                                mount_point=self.intermediate_pki_mount
                            )
                            
                            if cert_data and 'data' in cert_data:
                                cert_pem = cert_data['data']['certificate']
                                cert = x509.load_pem_x509_certificate(cert_pem.encode())
                                
                                expires_in = (cert.not_valid_after - now).days
                                
                                if expires_in <= 30:
                                    common_name = 'Unknown'
                                    try:
                                        common_name = cert.subject.get_attributes_for_oid(
                                            x509.NameOID.COMMON_NAME
                                        )[0].value
                                    except:
                                        pass
                                    
                                    health['expiring_certificates'].append({
                                        'serial': serial,
                                        'common_name': common_name,
                                        'expires_in_days': expires_in
                                    })
                                    
                        except Exception as e:
                            logger.debug(f"Error checking certificate {serial}: {str(e)}")
                            continue
                            
            except Exception as e:
                logger.warning(f"Failed to check issued certificates: {str(e)}")
            
            # Generate recommendations
            if health['expiring_certificates']:
                health['recommendations'].append(
                    f"Renew {len(health['expiring_certificates'])} certificates expiring within 30 days"
                )
            
            if health['root_ca']['expires_in_days'] < 90:
                health['recommendations'].append("Plan root CA rotation")
            
            if health['intermediate_ca']['expires_in_days'] < 90:
                health['recommendations'].append("Plan intermediate CA renewal")
            
            return health
            
        except Exception as e:
            logger.error(f"Certificate health validation failed: {str(e)}")
            raise PKIError(f"Certificate health validation failed: {str(e)}")
    
    def rotate_intermediate_ca(self) -> Dict[str, Any]:
        """Rotate intermediate CA certificate"""
        try:
            client = self.get_preferred_client()
            
            logger.info("Starting intermediate CA rotation")
            
            # Generate new intermediate CSR
            int_csr_response = client.secrets.pki.generate_intermediate(
                type_name='internal',
                common_name='TESA IoT Platform Intermediate CA',
                mount_point=self.intermediate_pki_mount,
                key_type='rsa',
                key_bits=2048,
                exclude_cn_from_sans=True
            )
            
            if 'data' not in int_csr_response or 'csr' not in int_csr_response['data']:
                raise PKIError("Failed to generate new intermediate CSR")
            
            csr = int_csr_response['data']['csr']
            
            # Sign new intermediate CSR with root CA
            signed_cert_response = client.secrets.pki.sign_intermediate(
                csr=csr,
                common_name='TESA IoT Platform Intermediate CA',
                mount_point=self.root_pki_mount,
                ttl='43800h',
                exclude_cn_from_sans=True
            )
            
            if 'data' not in signed_cert_response or 'certificate' not in signed_cert_response['data']:
                raise PKIError("Failed to sign new intermediate certificate")
            
            signed_cert = signed_cert_response['data']['certificate']
            
            # Set new intermediate certificate
            client.secrets.pki.set_signed_intermediate(
                certificate=signed_cert,
                mount_point=self.intermediate_pki_mount
            )
            
            # Reconfigure URLs
            client.secrets.pki.set_urls(
                issuing_certificates=[f"{self.vault_addr}/v1/{self.intermediate_pki_mount}/ca"],
                crl_distribution_points=[f"{self.vault_addr}/v1/{self.intermediate_pki_mount}/crl"],
                mount_point=self.intermediate_pki_mount
            )
            
            result = {
                'status': 'success',
                'message': 'Intermediate CA rotated successfully',
                'new_certificate': signed_cert,
                'rotation_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info("Intermediate CA rotation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Intermediate CA rotation failed: {str(e)}")
            raise PKIError(f"Intermediate CA rotation failed: {str(e)}")
    
    def cleanup_expired_certificates(self) -> Dict[str, Any]:
        """Clean up expired certificates from Vault storage"""
        try:
            client = self.get_preferred_client()
            
            # This operation should be performed carefully in production
            # For now, we'll just identify expired certificates
            
            expired_certs = []
            now = datetime.utcnow()
            
            cert_list = client.secrets.pki.list_certificates(
                mount_point=self.intermediate_pki_mount
            )
            
            if cert_list and 'data' in cert_list and 'keys' in cert_list['data']:
                for serial in cert_list['data']['keys']:
                    try:
                        cert_data = client.secrets.pki.read_certificate(
                            serial=serial,
                            mount_point=self.intermediate_pki_mount
                        )
                        
                        if cert_data and 'data' in cert_data:
                            cert_pem = cert_data['data']['certificate']
                            cert = x509.load_pem_x509_certificate(cert_pem.encode())
                            
                            if now > cert.not_valid_after:
                                expired_certs.append({
                                    'serial': serial,
                                    'expired_date': cert.not_valid_after.isoformat()
                                })
                                
                    except Exception as e:
                        logger.debug(f"Error checking certificate {serial}: {str(e)}")
                        continue
            
            # In production, you might want to actually clean these up
            # For safety, we're just reporting them
            
            result = {
                'expired_certificates_found': len(expired_certs),
                'expired_certificates': expired_certs,
                'cleanup_performed': False,
                'message': f'Found {len(expired_certs)} expired certificates (cleanup not performed for safety)'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Certificate cleanup failed: {str(e)}")
            raise PKIError(f"Certificate cleanup failed: {str(e)}")
    
    def backup_pki_configuration(self) -> Dict[str, Any]:
        """Backup PKI configuration and certificates"""
        try:
            client = self.get_preferred_client()
            
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'vault_version': 'unknown',
                'root_ca': None,
                'intermediate_ca': None,
                'roles': [],
                'configuration': {}
            }
            
            # Get Vault version
            try:
                health = client.sys.read_health_status()
                backup_data['vault_version'] = health.get('version', 'unknown')
            except:
                pass
            
            # Backup root CA
            try:
                root_ca_data = client.secrets.pki.read_ca_certificate(
                    mount_point=self.root_pki_mount
                )
                if root_ca_data and 'data' in root_ca_data:
                    backup_data['root_ca'] = root_ca_data['data']['certificate']
            except Exception as e:
                logger.warning(f"Failed to backup root CA: {str(e)}")
            
            # Backup intermediate CA
            try:
                int_ca_data = client.secrets.pki.read_ca_certificate(
                    mount_point=self.intermediate_pki_mount
                )
                if int_ca_data and 'data' in int_ca_data:
                    backup_data['intermediate_ca'] = int_ca_data['data']['certificate']
            except Exception as e:
                logger.warning(f"Failed to backup intermediate CA: {str(e)}")
            
            # Backup roles
            try:
                roles_list = client.secrets.pki.list_roles(
                    mount_point=self.intermediate_pki_mount
                )
                
                if roles_list and 'data' in roles_list and 'keys' in roles_list['data']:
                    for role_name in roles_list['data']['keys']:
                        try:
                            role_data = client.secrets.pki.read_role(
                                name=role_name,
                                mount_point=self.intermediate_pki_mount
                            )
                            if role_data and 'data' in role_data:
                                backup_data['roles'].append({
                                    'name': role_name,
                                    'config': role_data['data']
                                })
                        except Exception as e:
                            logger.warning(f"Failed to backup role {role_name}: {str(e)}")
                            
            except Exception as e:
                logger.warning(f"Failed to backup roles: {str(e)}")
            
            # Backup URLs configuration
            try:
                root_urls = client.secrets.pki.read_urls(mount_point=self.root_pki_mount)
                int_urls = client.secrets.pki.read_urls(mount_point=self.intermediate_pki_mount)
                
                backup_data['configuration'] = {
                    'root_urls': root_urls.get('data', {}) if root_urls else {},
                    'intermediate_urls': int_urls.get('data', {}) if int_urls else {}
                }
            except Exception as e:
                logger.warning(f"Failed to backup URL configuration: {str(e)}")
            
            return backup_data
            
        except Exception as e:
            logger.error(f"PKI backup failed: {str(e)}")
            raise PKIError(f"PKI backup failed: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        # Cleanup connections if needed
        pass