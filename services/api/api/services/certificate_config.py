# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Certificate Configuration Management
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


This module provides configuration management for certificate generation services.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


def _public_mqtt_host() -> str:
    """Public MQTT broker host advertised to devices in certificate bundles.

    Domain-agnostic self-host: derived from the wired .env vars so a custom
    DOMAIN (e.g. iot.acme.com) propagates without hand-editing. Falls back
    through TESA_MQTT_DOMAIN -> TESA_PUBLIC_MQTT_HOST -> DOMAIN -> localhost.
    """
    return (
        os.getenv("TESA_MQTT_DOMAIN")
        or os.getenv("TESA_PUBLIC_MQTT_HOST")
        or os.getenv("DOMAIN", "localhost")
    )


def _email_domain() -> str:
    """Certificate/device email domain, derived from the install's DOMAIN.

    Prefers the host of EMAIL_FROM_ADDRESS (e.g. noreply@iot.acme.com ->
    iot.acme.com) when set, otherwise the configured DOMAIN.
    """
    from_addr = os.getenv("EMAIL_FROM_ADDRESS", "")
    if "@" in from_addr:
        host = from_addr.rsplit("@", 1)[1].strip()
        if host:
            return host
    return os.getenv("DOMAIN", "localhost")


@dataclass
class MQTTBrokerConfig:
    """MQTT Broker configuration for certificate bundles."""
    host: str = field(default_factory=_public_mqtt_host)
    port: int = 8883
    keepalive: int = 60
    qos: int = 1
    retain: int = 0
    buffer_size: int = 1024
    max_topic_length: int = 128
    max_payload_size: int = 512
    use_tls: bool = True
    use_mutual_tls: bool = True
    tls_version: str = "TLS1_2"
    cipher_suites: str = "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
    verify_server_cert: bool = True
    check_cert_expiry: bool = True


@dataclass
class CertificatePolicy:
    """Certificate generation policy configuration."""
    default_algorithm: str = "RSA-2048"
    supported_algorithms: List[str] = None
    default_validity_days: int = 365
    max_validity_days: int = 3650
    min_validity_days: int = 1
    require_san: bool = True
    default_key_usage: Dict[str, bool] = None
    default_extended_key_usage: List[str] = None
    
    def __post_init__(self):
        if self.supported_algorithms is None:
            self.supported_algorithms = [
                'RSA-2048', 'RSA-4096', 'EC-P256', 'EC-P384', 'EC-P521'
            ]
        
        if self.default_key_usage is None:
            self.default_key_usage = {
                'digital_signature': True,
                'key_encipherment': True,
                'key_agreement': False,
                'content_commitment': False,
                'data_encipherment': False,
                'cert_sign': False,
                'crl_sign': False,
                'encipher_only': False,
                'decipher_only': False
            }
        
        if self.default_extended_key_usage is None:
            self.default_extended_key_usage = ['clientAuth']


@dataclass
class OrganizationConfig:
    """Organization-specific certificate configuration."""
    name: str = "TESA IoT Platform"
    country: str = "TH"
    state: str = "Bangkok"
    locality: str = "Bangkok"
    organizational_unit: str = "IoT Devices"
    email_domain: str = field(default_factory=_email_domain)


@dataclass
class CertificateGeneratorConfig:
    """Complete configuration for the certificate generator."""
    ca_path: str = "/app/config/certificates/poc2-mqtt"
    use_local_ca: bool = True
    enable_vault_fallback: bool = False
    organization: OrganizationConfig = None
    policy: CertificatePolicy = None
    mqtt_broker: MQTTBrokerConfig = None
    bundle_format: str = "zip"
    enable_audit_logging: bool = True
    enable_certificate_monitoring: bool = True
    
    def __post_init__(self):
        if self.organization is None:
            self.organization = OrganizationConfig()
        if self.policy is None:
            self.policy = CertificatePolicy()
        if self.mqtt_broker is None:
            self.mqtt_broker = MQTTBrokerConfig()


class CertificateConfigManager:
    """Configuration manager for certificate generation services."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file
        self.config = CertificateGeneratorConfig()
        
        # Load configuration from file or environment
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables."""
        # Load from file if specified
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                self._apply_config_data(config_data)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading config file {self.config_file}: {e}")
        
        # Override with environment variables
        self._load_from_environment()
    
    def _apply_config_data(self, config_data: Dict[str, Any]) -> None:
        """Apply configuration data from dictionary."""
        if 'ca_path' in config_data:
            self.config.ca_path = config_data['ca_path']
        
        if 'use_local_ca' in config_data:
            self.config.use_local_ca = config_data['use_local_ca']
        
        if 'organization' in config_data:
            org_data = config_data['organization']
            for key, value in org_data.items():
                if hasattr(self.config.organization, key):
                    setattr(self.config.organization, key, value)
        
        if 'policy' in config_data:
            policy_data = config_data['policy']
            for key, value in policy_data.items():
                if hasattr(self.config.policy, key):
                    setattr(self.config.policy, key, value)
        
        if 'mqtt_broker' in config_data:
            broker_data = config_data['mqtt_broker']
            for key, value in broker_data.items():
                if hasattr(self.config.mqtt_broker, key):
                    setattr(self.config.mqtt_broker, key, value)
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            'CERT_CA_PATH': ('ca_path', str),
            'CERT_USE_LOCAL_CA': ('use_local_ca', lambda x: x.lower() == 'true'),
            'CERT_ENABLE_VAULT_FALLBACK': ('enable_vault_fallback', lambda x: x.lower() == 'true'),
            'CERT_BUNDLE_FORMAT': ('bundle_format', str),
            
            # Organization
            'CERT_ORG_NAME': ('organization.name', str),
            'CERT_ORG_COUNTRY': ('organization.country', str),
            'CERT_ORG_STATE': ('organization.state', str),
            'CERT_ORG_LOCALITY': ('organization.locality', str),
            'CERT_ORG_UNIT': ('organization.organizational_unit', str),
            'CERT_ORG_EMAIL_DOMAIN': ('organization.email_domain', str),
            
            # Policy
            'CERT_DEFAULT_ALGORITHM': ('policy.default_algorithm', str),
            'CERT_DEFAULT_VALIDITY_DAYS': ('policy.default_validity_days', int),
            'CERT_MAX_VALIDITY_DAYS': ('policy.max_validity_days', int),
            'CERT_MIN_VALIDITY_DAYS': ('policy.min_validity_days', int),
            
            # MQTT Broker
            'MQTT_BROKER_HOST': ('mqtt_broker.host', str),
            'MQTT_BROKER_PORT': ('mqtt_broker.port', int),
            'MQTT_KEEPALIVE': ('mqtt_broker.keepalive', int),
            'MQTT_QOS': ('mqtt_broker.qos', int),
            'MQTT_BUFFER_SIZE': ('mqtt_broker.buffer_size', int),
            'MQTT_TLS_VERSION': ('mqtt_broker.tls_version', str),
            'MQTT_CIPHER_SUITES': ('mqtt_broker.cipher_suites', str),
        }
        
        for env_var, (config_path, converter) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    converted_value = converter(value)
                    self._set_nested_config(config_path, converted_value)
                    logger.debug(f"Set {config_path} = {converted_value} from {env_var}")
                except Exception as e:
                    logger.warning(f"Error converting environment variable {env_var}: {e}")
    
    def _set_nested_config(self, path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        parts = path.split('.')
        obj = self.config
        
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        setattr(obj, parts[-1], value)
    
    def get_config(self) -> CertificateGeneratorConfig:
        """Get the current configuration."""
        return self.config
    
    def get_mqtt_config_dict(self) -> Dict[str, Any]:
        """Get MQTT configuration as dictionary."""
        return asdict(self.config.mqtt_broker)
    
    def get_organization_subject_attrs(self) -> Dict[str, str]:
        """Get organization attributes for certificate subject."""
        org = self.config.organization
        return {
            'C': org.country,
            'ST': org.state,
            'L': org.locality,
            'O': org.name,
            'OU': org.organizational_unit
        }
    
    def validate_algorithm(self, algorithm: str) -> bool:
        """Validate if an algorithm is supported."""
        return algorithm in self.config.policy.supported_algorithms
    
    def validate_validity_days(self, days: int) -> bool:
        """Validate certificate validity period."""
        return (self.config.policy.min_validity_days <= 
                days <= 
                self.config.policy.max_validity_days)
    
    def get_default_san_entries(self, device_id: str) -> List[str]:
        """Get default SAN entries for a device."""
        return [
            device_id,
            f"{device_id}.local",
            f"{device_id}.{self.config.organization.email_domain}"
        ]
    
    def get_device_email(self, device_id: str) -> str:
        """Get device email address."""
        return f"{device_id}@{self.config.organization.email_domain}"
    
    def save_configuration(self, output_file: str) -> None:
        """Save current configuration to file."""
        try:
            config_dict = asdict(self.config)
            with open(output_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving configuration to {output_file}: {e}")
            raise
    
    def create_sample_config(self, output_file: str) -> None:
        """Create a sample configuration file."""
        sample_config = {
            "ca_path": "/app/config/certificates/poc2-mqtt",
            "use_local_ca": True,
            "enable_vault_fallback": False,
            "bundle_format": "zip",
            "organization": {
                "name": "TESA IoT Platform",
                "country": "TH",
                "state": "Bangkok",
                "locality": "Bangkok",
                "organizational_unit": "IoT Devices",
                "email_domain": _email_domain()
            },
            "policy": {
                "default_algorithm": "RSA-2048",
                "supported_algorithms": [
                    "RSA-2048", "RSA-4096", "EC-P256", "EC-P384", "EC-P521"
                ],
                "default_validity_days": 365,
                "max_validity_days": 3650,
                "min_validity_days": 1,
                "require_san": True,
                "default_key_usage": {
                    "digital_signature": True,
                    "key_encipherment": True,
                    "key_agreement": False,
                    "content_commitment": False,
                    "data_encipherment": False,
                    "cert_sign": False,
                    "crl_sign": False,
                    "encipher_only": False,
                    "decipher_only": False
                },
                "default_extended_key_usage": ["clientAuth"]
            },
            "mqtt_broker": {
                "host": _public_mqtt_host(),
                "port": 8883,
                "keepalive": 60,
                "qos": 1,
                "retain": 0,
                "buffer_size": 1024,
                "max_topic_length": 128,
                "max_payload_size": 512,
                "use_tls": True,
                "use_mutual_tls": True,
                "tls_version": "TLS1_2",
                "cipher_suites": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                "verify_server_cert": True,
                "check_cert_expiry": True
            }
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(sample_config, f, indent=2)
            logger.info(f"Sample configuration created at {output_file}")
        except Exception as e:
            logger.error(f"Error creating sample configuration: {e}")
            raise


# Global configuration manager instance
_config_manager = None


def get_certificate_config() -> CertificateConfigManager:
    """Get or create the global certificate configuration manager."""
    global _config_manager
    
    if _config_manager is None:
        config_file = os.environ.get('CERT_CONFIG_FILE')
        _config_manager = CertificateConfigManager(config_file)
    
    return _config_manager


# Convenience functions
def get_config() -> CertificateGeneratorConfig:
    """Get the current certificate generator configuration."""
    return get_certificate_config().get_config()


def get_mqtt_config() -> Dict[str, Any]:
    """Get MQTT broker configuration."""
    return get_certificate_config().get_mqtt_config_dict()


# Example usage
if __name__ == "__main__":
    # Create sample configuration
    config_manager = CertificateConfigManager()
    config_manager.create_sample_config("sample_cert_config.json")
    
    # Display current configuration
    config = config_manager.get_config()
    print(f"CA Path: {config.ca_path}")
    print(f"Use Local CA: {config.use_local_ca}")
    print(f"Default Algorithm: {config.policy.default_algorithm}")
    print(f"MQTT Broker: {config.mqtt_broker.host}:{config.mqtt_broker.port}")
    print(f"Organization: {config.organization.name}")