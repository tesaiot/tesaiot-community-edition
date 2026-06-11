# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform - API Key Security Service

Security rule: API keys are never stored in plaintext — only salted
SHA-256 hashes are persisted, and keys are shown to the user exactly once.

This service provides:
- SHA-256 hashing for API keys with salt
- Verification of API keys against stored hashes
- Generation of new API keys with proper format
- Migration utilities for legacy plaintext keys

Security Model:
- API keys are hashed using SHA-256 with unique salt per key
- Only the hash and prefix are stored in MongoDB
- Plaintext keys are NEVER stored after initial generation
- Prefix allows key identification without exposing the secret
"""

import hashlib
import secrets
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Key format constants
DEVICE_KEY_PREFIX = "tesa_dak"  # Device Access Key
ORG_KEY_PREFIX = "tesaiot_org"  # Organization API Key
HASH_ALGORITHM = "sha256"
SALT_LENGTH = 16  # bytes


class APIKeySecurityService:
    """Service for secure API key management."""

    @staticmethod
    def generate_device_api_key(device_id: str) -> Tuple[str, str, str]:
        """
        Generate a new device API key.

        Args:
            device_id: Device identifier

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
            - full_key: The complete API key (show to user ONCE)
            - key_hash: Hash to store in database
            - key_prefix: Prefix for identification
        """
        # Generate random secret part
        secret_part = secrets.token_hex(16)

        # Create full key with prefix
        short_device_id = device_id[:8] if len(device_id) >= 8 else device_id
        full_key = f"{DEVICE_KEY_PREFIX}_{short_device_id}_{secret_part}"

        # Generate hash
        key_hash = APIKeySecurityService.hash_api_key(full_key)

        # Create prefix for identification
        key_prefix = f"{DEVICE_KEY_PREFIX}_{short_device_id}"

        logger.info(f"Generated new device API key for {device_id[:8]}...")

        return full_key, key_hash, key_prefix

    @staticmethod
    def generate_org_api_key(org_id: str, key_name: str = "") -> Tuple[str, str, str]:
        """
        Generate a new organization API key.

        Args:
            org_id: Organization identifier
            key_name: Optional name for the key

        Returns:
            Tuple of (full_key, key_hash, key_prefix)
        """
        # Generate random secret part
        secret_part = secrets.token_hex(24)

        # Create full key with prefix
        short_org_id = org_id[:8] if len(org_id) >= 8 else org_id
        full_key = f"{ORG_KEY_PREFIX}_{short_org_id}_{secret_part}"

        # Generate hash
        key_hash = APIKeySecurityService.hash_api_key(full_key)

        # Create prefix for identification
        key_prefix = f"{ORG_KEY_PREFIX}_{short_org_id}"

        logger.info(f"Generated new org API key for {org_id}")

        return full_key, key_hash, key_prefix

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key using SHA-256 with salt.

        Format: "sha256:{salt_hex}:{hash_hex}"

        Args:
            api_key: The plaintext API key

        Returns:
            str: Formatted hash string
        """
        # Generate random salt
        salt = secrets.token_bytes(SALT_LENGTH)

        # Create hash
        key_bytes = api_key.encode('utf-8')
        hash_input = salt + key_bytes
        hash_result = hashlib.sha256(hash_input).hexdigest()

        # Format: algorithm:salt:hash
        return f"{HASH_ALGORITHM}:{salt.hex()}:{hash_result}"

    @staticmethod
    def verify_api_key(api_key: str, stored_hash: str) -> bool:
        """
        Verify an API key against a stored hash.

        Args:
            api_key: The plaintext API key to verify
            stored_hash: The stored hash string (format: "sha256:salt:hash")

        Returns:
            bool: True if key matches hash
        """
        try:
            # Parse stored hash
            parts = stored_hash.split(':')
            if len(parts) != 3:
                logger.warning("Invalid hash format")
                return False

            algorithm, salt_hex, expected_hash = parts

            if algorithm != HASH_ALGORITHM:
                logger.warning(f"Unknown hash algorithm: {algorithm}")
                return False

            # Recreate hash with same salt
            salt = bytes.fromhex(salt_hex)
            key_bytes = api_key.encode('utf-8')
            hash_input = salt + key_bytes
            actual_hash = hashlib.sha256(hash_input).hexdigest()

            # Constant-time comparison to prevent timing attacks
            return secrets.compare_digest(actual_hash, expected_hash)

        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return False

    @staticmethod
    def extract_prefix(api_key: str) -> str:
        """
        Extract the prefix from an API key.

        Args:
            api_key: Full API key

        Returns:
            str: Key prefix (e.g., "tesa_dak_2605168a")
        """
        parts = api_key.split('_')
        if len(parts) >= 3:
            # Return first 3 parts: prefix_type_id
            return '_'.join(parts[:3])
        return api_key[:20] if len(api_key) > 20 else api_key

    @staticmethod
    def is_plaintext_device_key(api_key: str) -> bool:
        """Check if an API key is a plaintext device key."""
        return api_key.startswith(DEVICE_KEY_PREFIX + "_")

    @staticmethod
    def is_plaintext_org_key(api_key: str) -> bool:
        """Check if an API key is a plaintext org key."""
        return api_key.startswith(ORG_KEY_PREFIX + "_")

    @staticmethod
    def is_hashed_key(value: str) -> bool:
        """Check if a value is a hashed key (not plaintext)."""
        return value.startswith(f"{HASH_ALGORITHM}:")


# Singleton instance
api_key_security_service = APIKeySecurityService()
