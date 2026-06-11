# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - Key Encryption Service
Copyright (C) 2024-2025 Wiroon Sriborrirux, Founder, BDH Corporation.



"""

import os
import logging
import secrets
import json
import base64
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pymongo.errors import ConnectionFailure

from ..core.database import get_db
from .audit_service import audit_log, AuditAction
import sys
sys.path.append('/app/audit')

from api.tolerance_methods.exception_handling import (
    with_error_handling, ErrorSeverity, ErrorCategory
)
from api.tolerance_methods.retry import (
    with_retry, RetryPolicy, CircuitBreaker
)

logger = logging.getLogger(__name__)

# System actor email for audit records when no real user is in context.
# Derived from the deployment's bootstrap admin, never a baked-in domain.
_SYSTEM_ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@localhost')

class EncryptionTier(str, Enum):
    """4-tier encryption architecture."""
    TIER_1_ULTRA_LOW = "tier_1_ultra_low"    # Ultra-low power sensors
    TIER_2_LOW_POWER = "tier_2_low_power"    # Low-power devices
    TIER_3_MEDIUM_POWER = "tier_3_medium"    # Medium-power gateways
    TIER_4_HIGH_POWER = "tier_4_high"        # High-power edge/cloud

class KeyAlgorithm(str, Enum):
    """Supported key algorithms."""
    ECC_P256 = "ECC-P256"
    ECC_P384 = "ECC-P384"
    RSA_2048 = "RSA-2048"
    RSA_3072 = "RSA-3072"
    RSA_4096 = "RSA-4096"

class EncryptionMethod(str, Enum):
    """Encryption methods per tier."""
    AES_128_GCM = "AES-128-GCM"
    AES_256_GCM = "AES-256-GCM"
    CHACHA20_POLY1305 = "ChaCha20-Poly1305"
    AES_256_CBC_HMAC = "AES-256-CBC-HMAC"

class KeyEncryptionError(Exception):
    """Custom key encryption error."""
    def __init__(self, message: str, code: str = None, details: Dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

# Circuit breakers for different service types
database_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
encryption_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

# Tier-based encryption configurations
TIER_ENCRYPTION_CONFIG = {
    EncryptionTier.TIER_1_ULTRA_LOW: {
        "data_encryption": EncryptionMethod.AES_128_GCM,
        "key_size": 128,
        "nonce_size": 96,
        "tag_size": 128,
        "kdf_iterations": 10000,
        "supported_device_keys": [KeyAlgorithm.ECC_P256],
        "max_payload_size": 4096  # 4KB max
    },
    EncryptionTier.TIER_2_LOW_POWER: {
        "data_encryption": EncryptionMethod.AES_256_GCM,
        "key_size": 256,
        "nonce_size": 96,
        "tag_size": 128,
        "kdf_iterations": 50000,
        "supported_device_keys": [KeyAlgorithm.ECC_P256, KeyAlgorithm.ECC_P384],
        "max_payload_size": 16384  # 16KB max
    },
    EncryptionTier.TIER_3_MEDIUM_POWER: {
        "data_encryption": EncryptionMethod.AES_256_GCM,
        "key_size": 256,
        "nonce_size": 128,
        "tag_size": 128,
        "kdf_iterations": 100000,
        "supported_device_keys": [KeyAlgorithm.RSA_2048, KeyAlgorithm.RSA_3072, KeyAlgorithm.ECC_P384],
        "max_payload_size": 1048576  # 1MB max
    },
    EncryptionTier.TIER_4_HIGH_POWER: {
        "data_encryption": EncryptionMethod.AES_256_GCM,
        "key_size": 256,
        "nonce_size": 128,
        "tag_size": 128,
        "kdf_iterations": 200000,
        "supported_device_keys": [KeyAlgorithm.RSA_3072, KeyAlgorithm.RSA_4096],
        "max_payload_size": 10485760  # 10MB max
    }
}

@encryption_circuit_breaker
@with_retry(max_retries=3, delay=0.5, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.AUTHENTICATION,
    user_message="Private key encryption failed. Please try again."
)
def encrypt_private_key_for_device(
    private_key_pem: str,
    device_public_key_pem: str,
    device_id: str,
    encryption_tier: EncryptionTier,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Encrypt a private key for secure transmission to a device using RSA-OAEP + AES-256-GCM.
    
    This implements a hybrid encryption scheme:
    1. Generate a random AES key (DEK - Data Encryption Key)
    2. Encrypt the private key with AES-GCM
    3. Encrypt the AES key with the device's public key using RSA-OAEP or ECDH
    4. Return the encrypted payload with metadata
    
    Args:
        private_key_pem: The private key to encrypt (PEM format)
        device_public_key_pem: The device's public key (PEM format)
        device_id: Device identifier for audit purposes
        encryption_tier: The encryption tier for the device
        metadata: Optional metadata to include
        
    Returns:
        Dict containing:
        - encrypted_key: Base64-encoded encrypted AES key
        - encrypted_data: Base64-encoded encrypted private key
        - nonce: Base64-encoded nonce/IV
        - tag: Base64-encoded authentication tag
        - algorithm: The encryption algorithm used
        - tier: The encryption tier
        - metadata: Additional metadata
    """
    try:
        # Validate tier configuration
        if encryption_tier not in TIER_ENCRYPTION_CONFIG:
            raise KeyEncryptionError(f"Invalid encryption tier: {encryption_tier}")
        
        tier_config = TIER_ENCRYPTION_CONFIG[encryption_tier]
        
        # Load device public key
        device_public_key = serialization.load_pem_public_key(
            device_public_key_pem.encode('utf-8'),
            backend=default_backend()
        )
        
        # Determine key type and validate against tier
        if isinstance(device_public_key, rsa.RSAPublicKey):
            key_algorithm = _get_rsa_algorithm(device_public_key)
        elif isinstance(device_public_key, ec.EllipticCurvePublicKey):
            key_algorithm = _get_ecc_algorithm(device_public_key)
        else:
            raise KeyEncryptionError("Unsupported public key type")
        
        if key_algorithm not in tier_config["supported_device_keys"]:
            raise KeyEncryptionError(
                f"Key algorithm {key_algorithm} not supported for tier {encryption_tier}"
            )
        
        # Generate DEK (Data Encryption Key) based on tier
        key_size_bytes = tier_config["key_size"] // 8
        dek = secrets.token_bytes(key_size_bytes)
        
        # Generate nonce for GCM
        nonce_size_bytes = tier_config["nonce_size"] // 8
        nonce = secrets.token_bytes(nonce_size_bytes)
        
        # Encrypt private key with AES-GCM
        if tier_config["data_encryption"] in [EncryptionMethod.AES_128_GCM, EncryptionMethod.AES_256_GCM]:
            aesgcm = AESGCM(dek)
            
            # Add metadata as additional authenticated data (AAD)
            aad = json.dumps({
                "device_id": device_id,
                "timestamp": datetime.utcnow().isoformat(),
                "tier": encryption_tier,
                "algorithm": tier_config["data_encryption"],
                **(metadata or {})
            }).encode('utf-8')
            
            # Encrypt the private key
            ciphertext = aesgcm.encrypt(nonce, private_key_pem.encode('utf-8'), aad)
            
            # GCM mode includes the tag in the ciphertext
            encrypted_data = ciphertext[:-16]  # Everything except last 16 bytes
            tag = ciphertext[-16:]  # Last 16 bytes are the tag
        else:
            raise KeyEncryptionError(f"Unsupported encryption method: {tier_config['data_encryption']}")
        
        # Encrypt DEK with device public key
        if isinstance(device_public_key, rsa.RSAPublicKey):
            # Use RSA-OAEP with SHA-256
            encrypted_dek = device_public_key.encrypt(
                dek,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        elif isinstance(device_public_key, ec.EllipticCurvePublicKey):
            # Use ECDH for ECC keys
            encrypted_dek = _encrypt_with_ecdh(dek, device_public_key, device_id)
        else:
            raise KeyEncryptionError("Unsupported key type for DEK encryption")
        
        # Prepare response
        result = {
            "encrypted_key": base64.b64encode(encrypted_dek).decode('utf-8'),
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "algorithm": tier_config["data_encryption"],
            "key_algorithm": key_algorithm,
            "tier": encryption_tier,
            "aad": base64.b64encode(aad).decode('utf-8'),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "device_id": device_id,
                "key_size": tier_config["key_size"],
                "max_payload_size": tier_config["max_payload_size"],
                **(metadata or {})
            }
        }
        
        # Store encryption record for audit
        _store_encryption_record(device_id, encryption_tier, key_algorithm, result)
        
        logger.info(f"Successfully encrypted private key for device {device_id} using tier {encryption_tier}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error encrypting private key for device {device_id}: {e}")
        raise KeyEncryptionError(f"Private key encryption failed: {str(e)}")

@encryption_circuit_breaker
@with_retry(max_retries=3, delay=0.5, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.HIGH,
    category=ErrorCategory.AUTHENTICATION,
    user_message="Private key decryption failed. Please check the encrypted data."
)
def decrypt_private_key(
    encrypted_payload: Dict[str, str],
    device_private_key_pem: str,
    device_id: str
) -> str:
    """
    Decrypt a private key that was encrypted for a device.
    
    This reverses the hybrid encryption:
    1. Decrypt the AES key using the device's private key
    2. Decrypt the private key using AES-GCM
    3. Verify the authentication tag
    4. Return the decrypted private key
    
    Args:
        encrypted_payload: The encrypted payload from encrypt_private_key_for_device
        device_private_key_pem: The device's private key (PEM format)
        device_id: Device identifier for verification
        
    Returns:
        The decrypted private key in PEM format
    """
    try:
        # Extract components from payload
        encrypted_dek = base64.b64decode(encrypted_payload["encrypted_key"])
        encrypted_data = base64.b64decode(encrypted_payload["encrypted_data"])
        nonce = base64.b64decode(encrypted_payload["nonce"])
        tag = base64.b64decode(encrypted_payload["tag"])
        aad = base64.b64decode(encrypted_payload["aad"])
        algorithm = encrypted_payload["algorithm"]
        key_algorithm = encrypted_payload.get("key_algorithm")
        
        # Load device private key
        device_private_key = serialization.load_pem_private_key(
            device_private_key_pem.encode('utf-8'),
            password=None,
            backend=default_backend()
        )
        
        # Decrypt DEK
        if isinstance(device_private_key, rsa.RSAPrivateKey):
            # Use RSA-OAEP with SHA-256
            dek = device_private_key.decrypt(
                encrypted_dek,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        elif isinstance(device_private_key, ec.EllipticCurvePrivateKey):
            # Use ECDH for ECC keys
            dek = _decrypt_with_ecdh(encrypted_dek, device_private_key, device_id)
        else:
            raise KeyEncryptionError("Unsupported key type for DEK decryption")
        
        # Decrypt private key with AES-GCM
        if algorithm in ["AES-128-GCM", "AES-256-GCM"]:
            aesgcm = AESGCM(dek)
            
            # Reconstruct ciphertext with tag
            ciphertext = encrypted_data + tag
            
            # Decrypt and verify
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
            
            private_key_pem = plaintext.decode('utf-8')
        else:
            raise KeyEncryptionError(f"Unsupported decryption algorithm: {algorithm}")
        
        # Verify the decrypted key is valid PEM
        try:
            serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
        except Exception:
            raise KeyEncryptionError("Decrypted data is not a valid private key")
        
        # Log successful decryption
        _log_decryption_event(device_id, key_algorithm, algorithm)
        
        logger.info(f"Successfully decrypted private key for device {device_id}")
        
        return private_key_pem
        
    except Exception as e:
        logger.error(f"Error decrypting private key for device {device_id}: {e}")
        raise KeyEncryptionError(f"Private key decryption failed: {str(e)}")

def get_encryption_tier_for_device(device_type: str, capabilities: Dict = None) -> EncryptionTier:
    """
    Determine the appropriate encryption tier for a device based on its type and capabilities.
    
    Args:
        device_type: The type of device (sensor, gateway, edge_device, etc.)
        capabilities: Optional device capabilities (cpu, memory, power_source, etc.)
        
    Returns:
        The appropriate encryption tier
    """
    # Default mappings based on device type
    device_tier_mapping = {
        # Tier 1: Ultra-low power
        "sensor": EncryptionTier.TIER_1_ULTRA_LOW,
        "temperature_sensor": EncryptionTier.TIER_1_ULTRA_LOW,
        "humidity_sensor": EncryptionTier.TIER_1_ULTRA_LOW,
        "motion_sensor": EncryptionTier.TIER_1_ULTRA_LOW,
        
        # Tier 2: Low power
        "actuator": EncryptionTier.TIER_2_LOW_POWER,
        "smart_lock": EncryptionTier.TIER_2_LOW_POWER,
        "smart_light": EncryptionTier.TIER_2_LOW_POWER,
        
        # Tier 3: Medium power
        "gateway": EncryptionTier.TIER_3_MEDIUM_POWER,
        "hub": EncryptionTier.TIER_3_MEDIUM_POWER,
        "industrial_controller": EncryptionTier.TIER_3_MEDIUM_POWER,
        
        # Tier 4: High power
        "edge_device": EncryptionTier.TIER_4_HIGH_POWER,
        "edge_server": EncryptionTier.TIER_4_HIGH_POWER,
        "ai_processor": EncryptionTier.TIER_4_HIGH_POWER,
    }
    
    # Start with device type mapping
    tier = device_tier_mapping.get(device_type.lower(), EncryptionTier.TIER_2_LOW_POWER)
    
    # Adjust based on capabilities if provided
    if capabilities:
        # Check power source
        power_source = capabilities.get("power_source", "").lower()
        if power_source in ["battery", "solar", "energy_harvesting"]:
            # Downgrade tier for battery-powered devices
            if tier == EncryptionTier.TIER_3_MEDIUM_POWER:
                tier = EncryptionTier.TIER_2_LOW_POWER
            elif tier == EncryptionTier.TIER_2_LOW_POWER:
                tier = EncryptionTier.TIER_1_ULTRA_LOW
        
        # Check CPU/memory constraints
        cpu_mhz = capabilities.get("cpu_mhz", 0)
        memory_mb = capabilities.get("memory_mb", 0)
        
        if cpu_mhz > 0 and cpu_mhz < 100:  # Very low power CPU
            tier = EncryptionTier.TIER_1_ULTRA_LOW
        elif cpu_mhz >= 1000 and memory_mb >= 1024:  # High-performance device
            tier = EncryptionTier.TIER_4_HIGH_POWER
    
    return tier

@database_circuit_breaker
def store_device_public_key(
    device_id: str,
    public_key_pem: str,
    key_algorithm: str,
    organization_id: str,
    user: Dict,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Store or update a device's public key in the database.
    
    Args:
        device_id: Device identifier
        public_key_pem: Public key in PEM format
        key_algorithm: Algorithm of the key (RSA-2048, ECC-P256, etc.)
        organization_id: Organization ID
        user: User performing the action
        metadata: Optional metadata
        
    Returns:
        Status information
    """
    try:
        db = get_db()
        
        # Validate device exists and belongs to organization
        device = db.devices.find_one({
            "device_id": device_id,
            "organization_id": organization_id
        })
        
        if not device:
            raise KeyEncryptionError(f"Device {device_id} not found or access denied")
        
        # Calculate key fingerprint
        fingerprint = _calculate_key_fingerprint(public_key_pem)
        
        # Prepare key record
        key_record = {
            "device_id": device_id,
            "organization_id": organization_id,
            "public_key_pem": public_key_pem,
            "key_algorithm": key_algorithm,
            "fingerprint": fingerprint,
            "registered_at": datetime.utcnow(),
            "registered_by": user.get("email") if isinstance(user, dict) else _SYSTEM_ADMIN_EMAIL,
            "status": "active",
            "metadata": metadata or {},
            "encryption_tier": get_encryption_tier_for_device(
                device.get("type", "sensor"),
                device.get("capabilities", {})
            )
        }
        
        # Update device record with consistent object structure
        device_public_key = {
            "key": public_key_pem,
            "algorithm": key_algorithm,
            "fingerprint": fingerprint,
            "status": "registered",
            "uploaded_at": datetime.utcnow(),
            "registered_by": user.get("email") if isinstance(user, dict) else _SYSTEM_ADMIN_EMAIL,
            "auto_generated": False
        }
        
        db.devices.update_one(
            {"device_id": device_id},
            {
                "$set": {
                    "device_public_key": device_public_key,
                    "key_algorithm": key_algorithm,
                    "key_fingerprint": fingerprint,
                    "key_encryption_enabled": True,
                    "key_registration_status": "registered",
                    "device_public_key_uploaded": True,  # Set flag to indicate public key exists
                    "key_registered_at": datetime.utcnow()
                }
            }
        )
        
        # Store in device_public_keys collection
        db.device_public_keys.update_one(
            {"device_id": device_id},
            {"$set": key_record},
            upsert=True
        )
        
        # Audit log
        audit_log(
            action=AuditAction.DEVICE_KEY_REGISTER,
            user=user,
            resource_type="device_public_key",
            resource_id=device_id,
            details={
                "key_algorithm": key_algorithm,
                "fingerprint": fingerprint,
                "encryption_tier": key_record["encryption_tier"]
            }
        )
        
        logger.info(f"Stored public key for device {device_id} with fingerprint {fingerprint}")
        
        return {
            "status": "success",
            "device_id": device_id,
            "fingerprint": fingerprint,
            "algorithm": key_algorithm,
            "encryption_tier": key_record["encryption_tier"],
            "registered_at": key_record["registered_at"].isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error storing device public key: {e}")
        raise KeyEncryptionError(f"Failed to store device public key: {str(e)}")

def _get_rsa_algorithm(public_key: rsa.RSAPublicKey) -> str:
    """Determine RSA algorithm from key size."""
    key_size = public_key.key_size
    if key_size == 2048:
        return KeyAlgorithm.RSA_2048
    elif key_size == 3072:
        return KeyAlgorithm.RSA_3072
    elif key_size == 4096:
        return KeyAlgorithm.RSA_4096
    else:
        raise KeyEncryptionError(f"Unsupported RSA key size: {key_size}")

def _get_ecc_algorithm(public_key: ec.EllipticCurvePublicKey) -> str:
    """Determine ECC algorithm from curve."""
    curve_name = public_key.curve.name
    if curve_name == "secp256r1":
        return KeyAlgorithm.ECC_P256
    elif curve_name == "secp384r1":
        return KeyAlgorithm.ECC_P384
    else:
        raise KeyEncryptionError(f"Unsupported ECC curve: {curve_name}")

def _encrypt_with_ecdh(dek: bytes, device_public_key: ec.EllipticCurvePublicKey, device_id: str) -> bytes:
    """
    Encrypt DEK using ECDH key agreement.
    
    For ECC keys, we use ECDH to derive a shared secret, then use HKDF to derive
    an encryption key, and finally encrypt the DEK with AES-GCM.
    """
    # Generate ephemeral key pair
    ephemeral_private_key = ec.generate_private_key(device_public_key.curve, default_backend())
    ephemeral_public_key = ephemeral_private_key.public_key()
    
    # Perform ECDH
    shared_secret = ephemeral_private_key.exchange(ec.ECDH(), device_public_key)
    
    # Derive encryption key using HKDF
    info = f"TESA-IoT-KEK-{device_id}".encode('utf-8')
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256-bit key
        salt=None,
        info=info,
        backend=default_backend()
    )
    kek = hkdf.derive(shared_secret)
    
    # Encrypt DEK with derived key
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(kek)
    encrypted_dek = aesgcm.encrypt(nonce, dek, None)
    
    # Serialize ephemeral public key
    ephemeral_public_key_bytes = ephemeral_public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    
    # Return ephemeral public key + nonce + encrypted DEK
    return ephemeral_public_key_bytes + nonce + encrypted_dek

def _decrypt_with_ecdh(encrypted_blob: bytes, device_private_key: ec.EllipticCurvePrivateKey, device_id: str) -> bytes:
    """Decrypt DEK using ECDH key agreement."""
    curve = device_private_key.curve
    
    # Extract components
    if isinstance(curve, ec.SECP256R1):
        point_size = 65  # 1 + 2 * 32
    elif isinstance(curve, ec.SECP384R1):
        point_size = 97  # 1 + 2 * 48
    else:
        raise KeyEncryptionError(f"Unsupported curve: {curve.name}")
    
    ephemeral_public_key_bytes = encrypted_blob[:point_size]
    nonce = encrypted_blob[point_size:point_size + 12]
    encrypted_dek = encrypted_blob[point_size + 12:]
    
    # Reconstruct ephemeral public key
    ephemeral_public_key = ec.EllipticCurvePublicKey.from_encoded_point(curve, ephemeral_public_key_bytes)
    
    # Perform ECDH
    shared_secret = device_private_key.exchange(ec.ECDH(), ephemeral_public_key)
    
    # Derive decryption key using HKDF
    info = f"TESA-IoT-KEK-{device_id}".encode('utf-8')
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=info,
        backend=default_backend()
    )
    kek = hkdf.derive(shared_secret)
    
    # Decrypt DEK
    aesgcm = AESGCM(kek)
    dek = aesgcm.decrypt(nonce, encrypted_dek, None)
    
    return dek

def _calculate_key_fingerprint(public_key_pem: str) -> str:
    """Calculate SHA-256 fingerprint of public key."""
    try:
        public_key_bytes = public_key_pem.encode('utf-8')
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(public_key_bytes)
        fingerprint = digest.finalize()
        return fingerprint.hex()
    except Exception as e:
        logger.error(f"Error calculating key fingerprint: {e}")
        return ""

def _store_encryption_record(device_id: str, tier: str, algorithm: str, result: Dict) -> None:
    """Store encryption event for audit trail."""
    try:
        db = get_db()
        if db:
            db.key_encryption_audit.insert_one({
                "device_id": device_id,
                "timestamp": datetime.utcnow(),
                "encryption_tier": tier,
                "key_algorithm": algorithm,
                "data_algorithm": result["algorithm"],
                "operation": "encrypt",
                "success": True
            })
    except Exception as e:
        logger.warning(f"Failed to store encryption audit record: {e}")

def _log_decryption_event(device_id: str, key_algorithm: str, data_algorithm: str) -> None:
    """Log decryption event for audit trail."""
    try:
        db = get_db()
        if db:
            db.key_encryption_audit.insert_one({
                "device_id": device_id,
                "timestamp": datetime.utcnow(),
                "key_algorithm": key_algorithm,
                "data_algorithm": data_algorithm,
                "operation": "decrypt",
                "success": True
            })
    except Exception as e:
        logger.warning(f"Failed to log decryption audit event: {e}")

@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.AUTHENTICATION,
    user_message="Failed to generate automatic encryption keys."
)
def generate_automatic_encryption_keys(
    device_id: str,
    device_type: str,
    organization_id: str,
    user: Dict,
    device_capabilities: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Automatically generate encryption keys for a device when it's created or gets a certificate.
    
    This function:
    1. Determines appropriate encryption tier based on device type and capabilities
    2. Generates a key pair suitable for the encryption tier
    3. Stores the public key in the device record
    4. Enables encryption for the device
    5. Returns information about the generated keys
    
    Args:
        device_id: Device identifier
        device_type: Type of device (sensor, gateway, etc.)
        organization_id: Organization ID
        user: User performing the action
        device_capabilities: Optional device capabilities info
        
    Returns:
        Dict containing generation status and key information
    """
    try:
        # Handle case where user might be passed as a list
        if isinstance(user, list):
            logger.warning(f"User parameter passed as list for device {device_id}, using first element")
            if user:
                user = user[0]
            else:
                user = {"email": _SYSTEM_ADMIN_EMAIL, "role": "system"}
        
        # Debug logging
        logger.info(f"User type in generate_automatic_encryption_keys: {type(user)}, value: {user}")
        db = get_db()
        if db is None:
            raise ConnectionFailure("Database connection not available")
        
        # Get device information
        device = db.devices.find_one({
            "device_id": device_id,
            "organization_id": organization_id
        })
        
        if not device:
            raise KeyEncryptionError(f"Device {device_id} not found")
        
        # Check if device already has encryption keys
        if device.get('key_encryption_enabled') and device.get('device_public_key'):
            logger.info(f"Device {device_id} already has encryption keys enabled")
            return {
                "status": "already_exists",
                "device_id": device_id,
                "encryption_enabled": True,
                "message": "Device already has encryption keys"
            }
        
        # Determine encryption tier
        encryption_tier = get_encryption_tier_for_device(
            device_type, 
            device_capabilities or device.get('capabilities', {})
        )
        
        # Get tier configuration
        tier_config = TIER_ENCRYPTION_CONFIG[encryption_tier]
        supported_algorithms = tier_config["supported_device_keys"]
        
        # Select best algorithm for the tier
        if KeyAlgorithm.ECC_P256 in supported_algorithms:
            key_algorithm = KeyAlgorithm.ECC_P256
        elif KeyAlgorithm.RSA_2048 in supported_algorithms:
            key_algorithm = KeyAlgorithm.RSA_2048
        else:
            key_algorithm = supported_algorithms[0]  # Use first available
        
        # Generate key pair
        if key_algorithm in [KeyAlgorithm.ECC_P256, KeyAlgorithm.ECC_P384]:
            # Generate ECC key pair
            if key_algorithm == KeyAlgorithm.ECC_P256:
                curve = ec.SECP256R1()
            else:
                curve = ec.SECP384R1()
            
            private_key = ec.generate_private_key(curve, default_backend())
            public_key = private_key.public_key()
            
        else:
            # Generate RSA key pair
            key_size = int(key_algorithm.split('-')[1])
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            public_key = private_key.public_key()
        
        # Serialize keys to PEM format
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Calculate fingerprint
        fingerprint = _calculate_key_fingerprint(public_key_pem)
        
        # Store public key in device record
        device_public_key = {
            "key": public_key_pem,
            "algorithm": key_algorithm,
            "fingerprint": fingerprint,
            "registered_at": datetime.utcnow(),
            "registered_by": user.get("email") if isinstance(user, dict) else _SYSTEM_ADMIN_EMAIL,
            "auto_generated": True
        }
        
        # Update device with key information
        update_data = {
            "device_public_key": device_public_key,
            "key_encryption_enabled": True,
            "key_registration_status": "auto_generated",
            "device_public_key_uploaded": True,  # Set flag to indicate public key exists
            "encryption_tier": encryption_tier,
            "updated_at": datetime.utcnow()
        }
        
        result = db.devices.update_one(
            {"device_id": device_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise KeyEncryptionError("Failed to update device with encryption keys")
        
        # Store in device_public_keys collection for tracking
        key_record = {
            "device_id": device_id,
            "organization_id": organization_id,
            "public_key_pem": public_key_pem,
            "key_algorithm": key_algorithm,
            "fingerprint": fingerprint,
            "registered_at": datetime.utcnow(),
            "registered_by": user.get("email") if isinstance(user, dict) else _SYSTEM_ADMIN_EMAIL,
            "status": "active",
            "auto_generated": True,
            "encryption_tier": encryption_tier,
            "metadata": {
                "device_type": device_type,
                "generation_trigger": "auto_device_creation"
            }
        }
        
        db.device_public_keys.update_one(
            {"device_id": device_id},
            {"$set": key_record},
            upsert=True
        )
        
        # Audit log
        audit_log(
            action=AuditAction.DEVICE_KEY_REGISTER,
            user=user if isinstance(user, dict) else {"email": _SYSTEM_ADMIN_EMAIL, "role": "system"},
            resource_type="device_encryption_keys",
            resource_id=device_id,
            details={
                "key_algorithm": key_algorithm,
                "fingerprint": fingerprint,
                "encryption_tier": encryption_tier,
                "auto_generated": True,
                "device_type": device_type
            }
        )
        
        # Log to device logs
        try:
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=device_id,
                level='INFO',
                message='Automatic encryption keys generated and enabled',
                log_type='security',
                details={
                    'algorithm': key_algorithm,
                    'fingerprint': fingerprint,
                    'encryption_tier': encryption_tier,
                    'auto_generated': True
                },
                source='auto_provisioning'
            )
        except Exception as e:
            logger.warning(f"Failed to log key generation: {e}")
        
        logger.info(f"Automatically generated encryption keys for device {device_id} using {key_algorithm} (tier: {encryption_tier})")
        
        return {
            "status": "success",
            "device_id": device_id,
            "key_algorithm": key_algorithm,
            "fingerprint": fingerprint,
            "encryption_tier": encryption_tier,
            "encryption_enabled": True,
            "auto_generated": True,
            "registered_at": device_public_key["registered_at"].isoformat(),
            "message": "Encryption keys automatically generated and enabled"
        }
        
    except Exception as e:
        logger.error(f"Error generating automatic encryption keys for device {device_id}: {e}")
        
        # Try to log the error to device logs
        try:
            from .device_logs_service import device_logs_service
            device_logs_service.add_device_log(
                device_id=device_id,
                level='ERROR',
                message=f'Failed to generate automatic encryption keys: {str(e)}',
                log_type='security',
                details={'error': str(e)},
                source='auto_provisioning'
            )
        except Exception:
            pass  # Ignore logging errors
        
        return {
            "status": "error",
            "device_id": device_id,
            "error": str(e),
            "message": "Failed to generate automatic encryption keys"
        }

@database_circuit_breaker
@with_retry(max_retries=3, delay=1.0, backoff_policy=RetryPolicy.EXPONENTIAL_BACKOFF)
@with_error_handling(
    severity=ErrorSeverity.MEDIUM,
    category=ErrorCategory.AUTHENTICATION,
    user_message="Failed to perform bulk encryption key generation."
)
async def perform_bulk_encryption_key_generation(
    batch_devices: list,
    job_id: str,
    user: Dict[str, Any],
    organization_id: str,
    options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Perform bulk encryption key generation for a batch of devices.
    
    Args:
        batch_devices: List of devices to process
        job_id: Bulk job ID for tracking
        user: User performing the action
        organization_id: Organization ID
        options: Processing options
        
    Returns:
        Dict with batch results
    """
    db = get_db()
    if db is None:
        raise ConnectionFailure("Database connection not available")
    
    batch_results = {
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    for device in batch_devices:
        device_id = device.get('device_id')
        device_type = device.get('device_type', 'sensor')
        
        try:
            # Check if device already has encryption keys
            if device.get('key_encryption_enabled') and device.get('device_public_key'):
                logger.info(f"Device {device_id} already has encryption keys, skipping")
                batch_results["skipped"] += 1
                
                # Log skip to job logs
                db.certificate_bulk_job_logs.insert_one({
                    "job_id": job_id,
                    "device_id": device_id,
                    "timestamp": datetime.utcnow(),
                    "level": "INFO",
                    "message": "Device already has encryption keys",
                    "operation": "key_generation_skip"
                })
                continue
            
            # Generate encryption keys
            result = await generate_automatic_encryption_keys(
                device_id=device_id,
                device_type=device_type,
                organization_id=organization_id,
                user=user,
                device_capabilities=device.get('capabilities', {})
            )
            
            if result["status"] == "success":
                batch_results["successful"] += 1
                
                # Log success
                db.certificate_bulk_job_logs.insert_one({
                    "job_id": job_id,
                    "device_id": device_id,
                    "timestamp": datetime.utcnow(),
                    "level": "INFO",
                    "message": f"Encryption keys generated successfully ({result['key_algorithm']})",
                    "operation": "key_generation_success",
                    "details": {
                        "algorithm": result['key_algorithm'],
                        "fingerprint": result['fingerprint'],
                        "encryption_tier": result['encryption_tier']
                    }
                })
            else:
                batch_results["failed"] += 1
                batch_results["errors"].append({
                    "device_id": device_id,
                    "error": result.get("error", "Unknown error")
                })
                
                # Log failure
                db.certificate_bulk_job_logs.insert_one({
                    "job_id": job_id,
                    "device_id": device_id,
                    "timestamp": datetime.utcnow(),
                    "level": "ERROR",
                    "message": f"Failed to generate encryption keys: {result.get('error')}",
                    "operation": "key_generation_failed"
                })
                
        except Exception as e:
            logger.error(f"Error generating keys for device {device_id}: {e}")
            batch_results["failed"] += 1
            batch_results["errors"].append({
                "device_id": device_id,
                "error": str(e)
            })
            
            # Log error
            db.certificate_bulk_job_logs.insert_one({
                "job_id": job_id,
                "device_id": device_id,
                "timestamp": datetime.utcnow(),
                "level": "ERROR",
                "message": f"Exception during key generation: {str(e)}",
                "operation": "key_generation_error"
            })
    
    return batch_results

# Export public interface
__all__ = [
    'encrypt_private_key_for_device',
    'decrypt_private_key',
    'get_encryption_tier_for_device',
    'store_device_public_key',
    'generate_automatic_encryption_keys',
    'perform_bulk_encryption_key_generation',
    'EncryptionTier',
    'KeyAlgorithm',
    'EncryptionMethod',
    'KeyEncryptionError'
]