# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
TESA IoT Platform API - Services Module
=======================================
Version: Dynamic (read from VERSION.txt)
Module: Business Logic Services
Build: 2025-06-08 10:55:00 UTC

Service layer for business logic and external integrations.
"""

# Import all in-scope services for easy access.
# Out-of-scope services (GDPR, OTA, incidents, security analytics) have been
# removed from the Community Edition.
from .user_service import *
from .device_service import *
from .certificate_service import *
from .notification_service import *
from .vault_service import *
from . import organization_service

# Import new modularized services
from .base_service import BaseService
from .stats_service import StatsService
from .security_analytics_service import SecurityAnalyticsService

# Import key encryption service
from .key_encryption_service import (
    encrypt_private_key_for_device,
    decrypt_private_key,
    get_encryption_tier_for_device,
    store_device_public_key,
    generate_automatic_encryption_keys,
    EncryptionTier,
    KeyAlgorithm,
    EncryptionMethod,
    KeyEncryptionError
)

# Import enhanced device log service (Device Logs Improvement Feature)
from .enhanced_device_log_service import (
    EnhancedDeviceLogService,
    enhanced_device_log_service,
    log_security_event,
    log_mqtt_event,
    log_csr_event
)

# Import CSR workflow service (Device Logs Improvement Feature)
from .csr_workflow_service import (
    CSRWorkflowService,
    csr_workflow_service
)

# Explicit re-exports. The star imports above and the named imports below are
# intentionally re-exported from this package aggregator; listing them in
# __all__ makes the public surface explicit and satisfies F401.
__all__ = [
    # Submodule re-export
    "organization_service",
    # Modularized services
    "BaseService",
    "StatsService",
    "SecurityAnalyticsService",
    # Key encryption service
    "encrypt_private_key_for_device",
    "decrypt_private_key",
    "get_encryption_tier_for_device",
    "store_device_public_key",
    "generate_automatic_encryption_keys",
    "EncryptionTier",
    "KeyAlgorithm",
    "EncryptionMethod",
    "KeyEncryptionError",
    # Enhanced device log service
    "EnhancedDeviceLogService",
    "enhanced_device_log_service",
    "log_security_event",
    "log_mqtt_event",
    "log_csr_event",
    # CSR workflow service
    "CSRWorkflowService",
    "csr_workflow_service",
]