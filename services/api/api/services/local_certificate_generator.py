# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Local Certificate Generator Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.


This module provides local certificate generation capabilities using POC2 MQTT CA certificates.
It generates device certificates signed by the intermediate CA with proper issuer DN.
"""

import os
import io
import json
import zipfile
import logging
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional, Union, List
from pathlib import Path
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class LocalCertificateGenerator:
    """Local certificate generator using POC2 MQTT CA infrastructure."""
    
    def __init__(self, ca_path: str = "/app/config/certificates/poc2-mqtt"):
        """
        Initialize the local certificate generator.
        
        Args:
            ca_path: Path to the POC2 MQTT CA certificates directory
        """
        self.ca_path = Path(ca_path)
        self.ca_cert = None
        self.intermediate_cert = None
        self.intermediate_key = None
        self.ca_chain = None
        
        # Load CA certificates and keys
        self._load_ca_certificates()
        
        # Certificate validity periods
        self.default_validity_days = 365
        self.max_validity_days = 3650  # 10 years
        
        # Supported algorithms
        self.supported_algorithms = {
            'RSA-2048': {'type': 'rsa', 'key_size': 2048},
            'RSA-3072': {'type': 'rsa', 'key_size': 3072},
            'RSA-4096': {'type': 'rsa', 'key_size': 4096},
            'EC-P256': {'type': 'ec', 'curve': ec.SECP256R1()},
            'EC-P384': {'type': 'ec', 'curve': ec.SECP384R1()},
            'EC-P521': {'type': 'ec', 'curve': ec.SECP521R1()}
        }
    
    def _load_ca_certificates(self) -> None:
        """Load CA certificates and keys from the POC2 MQTT directory."""
        try:
            # Load root CA certificate
            ca_cert_path = self.ca_path / "ca.crt"
            with open(ca_cert_path, 'rb') as f:
                self.ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            logger.info(f"Loaded root CA certificate from {ca_cert_path}")
            
            # Load intermediate CA certificate
            intermediate_cert_path = self.ca_path / "intermediate.crt"
            with open(intermediate_cert_path, 'rb') as f:
                self.intermediate_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
            logger.info(f"Loaded intermediate CA certificate from {intermediate_cert_path}")
            
            # Load intermediate CA private key
            intermediate_key_path = self.ca_path / "intermediate.key"
            with open(intermediate_key_path, 'rb') as f:
                self.intermediate_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
            logger.info(f"Loaded intermediate CA private key from {intermediate_key_path}")
            
            # Load CA chain
            ca_chain_path = self.ca_path / "ca-chain.crt"
            if ca_chain_path.exists():
                with open(ca_chain_path, 'rb') as f:
                    self.ca_chain = f.read()
            else:
                # Create chain from individual certificates
                self.ca_chain = (
                    self.intermediate_cert.public_bytes(serialization.Encoding.PEM) +
                    self.ca_cert.public_bytes(serialization.Encoding.PEM)
                )
            logger.info("CA certificate chain loaded successfully")
            
        except FileNotFoundError as e:
            logger.error(f"CA certificate file not found: {e}")
            raise ValueError(f"CA certificate file not found: {e}")
        except Exception as e:
            logger.error(f"Error loading CA certificates: {e}")
            raise ValueError(f"Failed to load CA certificates: {e}")
    
    def _generate_private_key(self, algorithm: str) -> Union[rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey]:
        """
        Generate a private key based on the specified algorithm.
        
        Args:
            algorithm: Algorithm identifier (e.g., 'RSA-2048', 'RSA-3072', 'EC-P256')
            
        Returns:
            Private key object
        """
        if algorithm not in self.supported_algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        algo_config = self.supported_algorithms[algorithm]
        
        if algo_config['type'] == 'rsa':
            return rsa.generate_private_key(
                public_exponent=65537,
                key_size=algo_config['key_size'],
                backend=default_backend()
            )
        elif algo_config['type'] == 'ec':
            return ec.generate_private_key(
                curve=algo_config['curve'],
                backend=default_backend()
            )
        else:
            raise ValueError(f"Unknown algorithm type: {algo_config['type']}")
    
    def _build_subject(self, device_id: str, organization: str, 
                      additional_attrs: Optional[Dict[str, str]] = None) -> x509.Name:
        """
        Build X.509 subject with proper DN structure.
        
        Args:
            device_id: Device identifier
            organization: Organization name
            additional_attrs: Additional subject attributes
            
        Returns:
            X.509 Name object
        """
        # Base subject attributes matching POC2 structure
        subject_attrs = [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "TH"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Bangkok"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Bangkok"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Devices"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_id)
        ]
        
        # Add any additional attributes
        if additional_attrs:
            oid_mapping = {
                'email': NameOID.EMAIL_ADDRESS,
                'serialNumber': NameOID.SERIAL_NUMBER,
                'surname': NameOID.SURNAME,
                'givenName': NameOID.GIVEN_NAME,
                'title': NameOID.TITLE
            }
            
            for attr_name, attr_value in additional_attrs.items():
                if attr_name in oid_mapping:
                    subject_attrs.append(
                        x509.NameAttribute(oid_mapping[attr_name], attr_value)
                    )
        
        return x509.Name(subject_attrs)
    
    def generate_device_certificate(
        self,
        device_id: str,
        organization: str = "TESA IoT Platform",
        algorithm: str = "RSA-2048",
        validity_days: int = 365,
        san_entries: Optional[List[str]] = None,
        key_usage: Optional[Dict[str, bool]] = None,
        extended_key_usage: Optional[List[str]] = None,
        additional_subject_attrs: Optional[Dict[str, str]] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """
        Generate a device certificate signed by the intermediate CA.
        
        Args:
            device_id: Unique device identifier
            organization: Organization name for the certificate
            algorithm: Key algorithm ('RSA-2048', 'RSA-3072', 'RSA-4096', 'EC-P256', etc.)
            validity_days: Certificate validity period in days
            san_entries: Subject Alternative Name entries
            key_usage: Key usage flags
            extended_key_usage: Extended key usage OIDs
            additional_subject_attrs: Additional subject attributes
            
        Returns:
            Tuple of (certificate_pem, private_key_pem, ca_chain_pem)
        """
        try:
            # Validate inputs
            if not device_id:
                raise ValueError("Device ID is required")
            
            if validity_days > self.max_validity_days:
                raise ValueError(f"Validity period exceeds maximum of {self.max_validity_days} days")
            
            # Generate private key
            private_key = self._generate_private_key(algorithm)
            
            # Build subject
            subject = self._build_subject(device_id, organization, additional_subject_attrs)
            
            # Create certificate builder
            builder = x509.CertificateBuilder()
            builder = builder.subject_name(subject)
            builder = builder.issuer_name(self.intermediate_cert.subject)
            
            # Set validity period
            not_before = datetime.now(timezone.utc)
            not_after = not_before + timedelta(days=validity_days)
            builder = builder.not_valid_before(not_before)
            builder = builder.not_valid_after(not_after)
            
            # Set serial number (generate unique serial)
            serial_bytes = hashlib.sha256(
                f"{device_id}-{not_before.isoformat()}".encode()
            ).digest()[:16]
            serial_number = int.from_bytes(serial_bytes, 'big')
            builder = builder.serial_number(serial_number)
            
            # Set public key
            builder = builder.public_key(private_key.public_key())
            
            # Add basic constraints (not a CA)
            builder = builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
            
            # Add key usage
            if key_usage is None:
                key_usage = {
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
            
            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=key_usage.get('digital_signature', True),
                    key_encipherment=key_usage.get('key_encipherment', True),
                    key_agreement=key_usage.get('key_agreement', False),
                    content_commitment=key_usage.get('content_commitment', False),
                    data_encipherment=key_usage.get('data_encipherment', False),
                    key_cert_sign=key_usage.get('cert_sign', False),
                    crl_sign=key_usage.get('crl_sign', False),
                    encipher_only=key_usage.get('encipher_only', False),
                    decipher_only=key_usage.get('decipher_only', False)
                ),
                critical=True
            )
            
            # Add extended key usage
            if extended_key_usage is None:
                extended_key_usage = ['clientAuth']
            
            eku_oids = {
                'serverAuth': ExtendedKeyUsageOID.SERVER_AUTH,
                'clientAuth': ExtendedKeyUsageOID.CLIENT_AUTH,
                'codeSigning': ExtendedKeyUsageOID.CODE_SIGNING,
                'emailProtection': ExtendedKeyUsageOID.EMAIL_PROTECTION,
                'timeStamping': ExtendedKeyUsageOID.TIME_STAMPING,
                'ocspSigning': ExtendedKeyUsageOID.OCSP_SIGNING
            }
            
            eku_list = []
            for usage in extended_key_usage:
                if usage in eku_oids:
                    eku_list.append(eku_oids[usage])
            
            if eku_list:
                builder = builder.add_extension(
                    x509.ExtendedKeyUsage(eku_list),
                    critical=True
                )
            
            # Add Subject Alternative Names
            san_list = []
            if san_entries:
                for san in san_entries:
                    if '@' in san:  # Email address
                        san_list.append(x509.RFC822Name(san))
                    elif san.replace('.', '').replace(':', '').isdigit():  # IP address
                        san_list.append(x509.IPAddress(san))
                    else:  # DNS name
                        san_list.append(x509.DNSName(san))
            else:
                # Default to device ID as DNS name
                san_list.append(x509.DNSName(device_id))
            
            if san_list:
                builder = builder.add_extension(
                    x509.SubjectAlternativeName(san_list),
                    critical=False
                )
            
            # Add Subject Key Identifier
            builder = builder.add_extension(
                x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
                critical=False
            )
            
            # Add Authority Key Identifier
            builder = builder.add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    self.intermediate_cert.public_key()
                ),
                critical=False
            )
            
            # Sign the certificate
            certificate = builder.sign(
                private_key=self.intermediate_key,
                algorithm=hashes.SHA256(),
                backend=default_backend()
            )
            
            # Serialize certificate and private key
            cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
            
            # Serialize private key (no encryption for device usage)
            key_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            logger.info(f"Generated certificate for device {device_id} with algorithm {algorithm}")
            
            return cert_pem, key_pem, self.ca_chain
            
        except Exception as e:
            logger.error(f"Error generating device certificate: {e}")
            raise
    
    def generate_mqtt_client_config(
        self,
        device_id: str,
        broker_host: Optional[str] = None,
        broker_port: int = 8883,
        environment: str = "production",
        additional_config: Optional[Dict[str, any]] = None
    ) -> str:
        """
        Generate mqtt_client_config.h file content for the device.
        
        Args:
            device_id: Device identifier
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            environment: Deployment environment
            additional_config: Additional configuration parameters
            
        Returns:
            Generated mqtt_client_config.h content
        """
        # Env-driven broker host (no baked-in production domain)
        if not broker_host:
            broker_host = os.getenv('TESA_MQTT_DOMAIN', os.getenv('TESA_PUBLIC_MQTT_HOST', 'localhost'))
        # Default configuration
        config = {
            'device_id': device_id,
            'environment': environment,
            'broker_host': broker_host,
            'broker_port': broker_port,
            'keepalive': 60,
            'qos': 1,
            'retain': 0,
            'buffer_size': 1024,
            'max_topic_length': 128,
            'max_payload_size': 512,
            'use_tls': 1,
            'use_mutual_tls': 1,
            'tls_version': 'TLS1_2',
            'cipher_suites': 'TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256'
        }
        
        # Merge with additional configuration
        if additional_config:
            config.update(additional_config)
        
        # Generate the header file content
        content = f"""/*
 * MQTT Client Configuration
 * Generated for device: {device_id}
 * Environment: {environment}
 * Generated at: {datetime.now(timezone.utc).isoformat()}
 */

#ifndef MQTT_CLIENT_CONFIG_H
#define MQTT_CLIENT_CONFIG_H

/* MQTT Broker Settings */
#define MQTT_BROKER_HOST     "{config['broker_host']}"
#define MQTT_BROKER_PORT     {config['broker_port']}
#define MQTT_USE_TLS         {config['use_tls']}
#define MQTT_USE_MUTUAL_TLS  {config['use_mutual_tls']}

/* Device Credentials */
#define DEVICE_ID            "{device_id}"
#define MQTT_CLIENT_ID       "{device_id}"

/* MQTT Topics */
#define TELEMETRY_TOPIC      "telemetry/{device_id}"
#define COMMAND_TOPIC        "commands/{device_id}"
#define STATUS_TOPIC         "status/{device_id}"
#define CONFIG_TOPIC         "config/{device_id}"
#define OTA_TOPIC            "ota/{device_id}"

/* TLS Configuration */
#define TLS_VERSION          "{config['tls_version']}"
#define TLS_CIPHER_SUITES    "{config['cipher_suites']}"

/* Certificate paths (update based on your file system) */
#define CA_CERT_PATH         "certificates/ca-chain.crt"
#define CLIENT_CERT_PATH     "certificates/device.crt"
#define CLIENT_KEY_PATH      "certificates/device.key"

/* Connection Parameters */
#define MQTT_KEEPALIVE       {config['keepalive']}  // seconds
#define MQTT_QOS             {config['qos']}
#define MQTT_RETAIN          {config['retain']}
#define MQTT_CLEAN_SESSION   1
#define MQTT_CONNECT_TIMEOUT 30  // seconds

/* Buffer Sizes */
#define MQTT_BUFFER_SIZE     {config['buffer_size']}
#define MAX_TOPIC_LENGTH     {config['max_topic_length']}
#define MAX_PAYLOAD_SIZE     {config['max_payload_size']}

/* Retry Configuration */
#define MAX_RECONNECT_ATTEMPTS  5
#define RECONNECT_DELAY_MS      1000
#define RECONNECT_MAX_DELAY_MS  30000

/* Security Features */
#define ENABLE_CERT_VALIDATION  1
#define VERIFY_SERVER_CERT      1
#define CHECK_CERT_EXPIRY       1

/* Debug Options */
#ifdef DEBUG
  #define MQTT_DEBUG_ENABLED    1
  #define LOG_LEVEL             "DEBUG"
#else
  #define MQTT_DEBUG_ENABLED    0
  #define LOG_LEVEL             "INFO"
#endif

#endif // MQTT_CLIENT_CONFIG_H
"""
        return content
    
    def create_certificate_bundle(
        self,
        device_id: str,
        organization: str = "TESA IoT Platform",
        algorithm: str = "RSA-2048",
        validity_days: int = 365,
        broker_config: Optional[Dict[str, any]] = None,
        include_config: bool = True,
        bundle_format: str = "zip"
    ) -> bytes:
        """
        Create a complete certificate bundle for a device.
        
        Args:
            device_id: Device identifier
            organization: Organization name
            algorithm: Key algorithm
            validity_days: Certificate validity period
            broker_config: MQTT broker configuration
            include_config: Include mqtt_client_config.h
            bundle_format: Bundle format ('zip' or 'tar')
            
        Returns:
            Bundle file content as bytes
        """
        try:
            # Generate device certificate
            cert_pem, key_pem, ca_chain_pem = self.generate_device_certificate(
                device_id=device_id,
                organization=organization,
                algorithm=algorithm,
                validity_days=validity_days
            )
            
            # Create bundle
            if bundle_format == "zip":
                bundle_buffer = io.BytesIO()
                with zipfile.ZipFile(bundle_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    # Add certificates
                    zf.writestr(f"{device_id}/certificates/device.crt", cert_pem)
                    zf.writestr(f"{device_id}/certificates/device.key", key_pem)
                    zf.writestr(f"{device_id}/certificates/ca-chain.crt", ca_chain_pem)
                    
                    # Add individual CA certificates for compatibility
                    zf.writestr(f"{device_id}/certificates/ca.crt", 
                              self.ca_cert.public_bytes(serialization.Encoding.PEM))
                    zf.writestr(f"{device_id}/certificates/intermediate.crt",
                              self.intermediate_cert.public_bytes(serialization.Encoding.PEM))
                    
                    # Add configuration file
                    if include_config:
                        config_content = self.generate_mqtt_client_config(
                            device_id=device_id,
                            **(broker_config or {})
                        )
                        zf.writestr(f"{device_id}/mqtt_client_config.h", config_content)
                    
                    # Add README
                    readme_content = self._generate_bundle_readme(device_id, algorithm, validity_days)
                    zf.writestr(f"{device_id}/README.md", readme_content)
                    
                    # Add certificate info JSON
                    cert_info = self._get_certificate_info(cert_pem)
                    zf.writestr(f"{device_id}/certificate_info.json", 
                              json.dumps(cert_info, indent=2, default=str))
                
                bundle_buffer.seek(0)
                return bundle_buffer.read()
            
            else:
                raise ValueError(f"Unsupported bundle format: {bundle_format}")
                
        except Exception as e:
            logger.error(f"Error creating certificate bundle: {e}")
            raise
    
    def _get_certificate_info(self, cert_pem: bytes) -> Dict[str, any]:
        """Extract certificate information for documentation."""
        cert = x509.load_pem_x509_certificate(cert_pem, default_backend())
        
        return {
            'serial_number': str(cert.serial_number),
            'subject': {attr.oid._name: attr.value for attr in cert.subject},
            'issuer': {attr.oid._name: attr.value for attr in cert.issuer},
            'not_before': cert.not_valid_before_utc.isoformat(),
            'not_after': cert.not_valid_after_utc.isoformat(),
            'signature_algorithm': cert.signature_algorithm_oid._name,
            'key_algorithm': self._get_key_algorithm_info(cert.public_key()),
            'extensions': self._get_extension_info(cert)
        }
    
    def _get_key_algorithm_info(self, public_key) -> Dict[str, any]:
        """Get information about the key algorithm."""
        if isinstance(public_key, rsa.RSAPublicKey):
            return {
                'type': 'RSA',
                'key_size': public_key.key_size
            }
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            return {
                'type': 'EC',
                'curve': public_key.curve.name
            }
        else:
            return {'type': 'Unknown'}
    
    def _get_extension_info(self, cert: x509.Certificate) -> Dict[str, any]:
        """Extract extension information from certificate."""
        extensions = {}
        
        for ext in cert.extensions:
            try:
                if isinstance(ext.value, x509.BasicConstraints):
                    extensions['basic_constraints'] = {
                        'ca': ext.value.ca,
                        'path_length': ext.value.path_length
                    }
                elif isinstance(ext.value, x509.KeyUsage):
                    extensions['key_usage'] = {
                        'digital_signature': ext.value.digital_signature,
                        'key_encipherment': ext.value.key_encipherment,
                        'key_agreement': ext.value.key_agreement
                    }
                elif isinstance(ext.value, x509.ExtendedKeyUsage):
                    extensions['extended_key_usage'] = [
                        oid._name for oid in ext.value
                    ]
                elif isinstance(ext.value, x509.SubjectAlternativeName):
                    extensions['subject_alternative_names'] = [
                        str(san) for san in ext.value
                    ]
            except Exception:
                pass
        
        return extensions
    
    def _generate_bundle_readme(self, device_id: str, algorithm: str, validity_days: int) -> str:
        """Generate README content for the certificate bundle."""
        return f"""# Device Certificate Bundle for {device_id}

## Contents

This bundle contains all necessary files for MQTT TLS authentication:

- `certificates/device.crt` - Device certificate
- `certificates/device.key` - Device private key
- `certificates/ca-chain.crt` - Complete CA certificate chain
- `certificates/ca.crt` - Root CA certificate
- `certificates/intermediate.crt` - Intermediate CA certificate
- `mqtt_client_config.h` - MQTT client configuration header
- `certificate_info.json` - Certificate details and metadata

## Certificate Details

- **Device ID**: {device_id}
- **Algorithm**: {algorithm}
- **Validity**: {validity_days} days
- **Issued By**: TESA IoT Platform Intermediate CA

## Usage

1. Copy the certificates directory to your device
2. Include mqtt_client_config.h in your project
3. Update certificate paths in the configuration if needed
4. Ensure proper file permissions (private key should be readable only by the application)

## Security Notes

- Keep the private key (device.key) secure and never share it
- The private key is not encrypted - consider encrypting it for production use
- Verify certificate expiration dates regularly
- Use secure channels when transferring these files

## MQTT Connection

The device should connect using:
- Client ID: {device_id}
- TLS/SSL enabled with mutual authentication
- CA chain for server verification
- Client certificate and key for device authentication

Generated at: {datetime.now(timezone.utc).isoformat()}
"""
    
    def verify_certificate_chain(self, device_cert_pem: bytes) -> bool:
        """
        Verify that a device certificate was issued by our CA chain.
        
        Args:
            device_cert_pem: Device certificate in PEM format
            
        Returns:
            True if certificate chain is valid
        """
        try:
            # Load the device certificate
            device_cert = x509.load_pem_x509_certificate(device_cert_pem, default_backend())
            
            # Check if issuer matches our intermediate CA
            if device_cert.issuer != self.intermediate_cert.subject:
                logger.error("Certificate issuer does not match intermediate CA")
                return False
            
            # Verify the signature
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.exceptions import InvalidSignature
            
            try:
                self.intermediate_cert.public_key().verify(
                    device_cert.signature,
                    device_cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    device_cert.signature_hash_algorithm
                )
                logger.info("Certificate signature verification successful")
                return True
            except InvalidSignature:
                logger.error("Certificate signature verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying certificate chain: {e}")
            return False


# Factory function for creating generator instances
def create_local_certificate_generator(ca_path: Optional[str] = None) -> LocalCertificateGenerator:
    """
    Create a LocalCertificateGenerator instance.
    
    Args:
        ca_path: Optional path to CA certificates directory
        
    Returns:
        LocalCertificateGenerator instance
    """
    if ca_path is None:
        # Try multiple possible paths
        possible_paths = [
            "/app/config/certificates/poc2-mqtt",
            "/config/certificates/poc2-mqtt",
            "./config/certificates/poc2-mqtt",
            os.environ.get("CA_CERT_PATH", "")
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                ca_path = path
                break
        
        if not ca_path:
            raise ValueError("Could not find CA certificates directory")
    
    return LocalCertificateGenerator(ca_path)


# Example usage and testing
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create generator instance
        generator = create_local_certificate_generator()
        
        # Generate a test certificate
        device_id = "test-device-001"
        cert_pem, key_pem, ca_chain = generator.generate_device_certificate(
            device_id=device_id,
            organization="TESA IoT Test",
            algorithm="RSA-2048",
            validity_days=365
        )
        
        print(f"Generated certificate for {device_id}")
        print(f"Certificate size: {len(cert_pem)} bytes")
        print(f"Private key size: {len(key_pem)} bytes")
        print(f"CA chain size: {len(ca_chain)} bytes")
        
        # Verify the certificate
        if generator.verify_certificate_chain(cert_pem):
            print("Certificate chain verification: PASSED")
        else:
            print("Certificate chain verification: FAILED")
        
        # Generate a certificate bundle
        bundle = generator.create_certificate_bundle(
            device_id=device_id,
            organization="TESA IoT Test",
            algorithm="EC-P256",
            validity_days=730,
            broker_config={
                'broker_host': 'mqtt.tesaiot.local',
                'broker_port': 8883
            }
        )
        
        print(f"Generated certificate bundle: {len(bundle)} bytes")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise