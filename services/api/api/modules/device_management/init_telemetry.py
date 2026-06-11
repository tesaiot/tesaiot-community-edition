# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Telemetry Service Initialization Module

This module handles the initialization of the telemetry service
with proper configuration and dependency injection.
"""

import os
import logging
from typing import Optional

from .services.telemetry_service import TelemetryService

logger = logging.getLogger(__name__)


def get_telemetry_config():
    """Get telemetry configuration from environment variables"""
    return {
        "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "mongodb_url": os.getenv("MONGODB_URL", "mongodb://localhost:27017/tesa_iot"),
        "buffer_size": int(os.getenv("TELEMETRY_BUFFER_SIZE", "1000")),
        "batch_size": int(os.getenv("TELEMETRY_BATCH_SIZE", "500")),
        "flush_interval_seconds": int(os.getenv("TELEMETRY_FLUSH_INTERVAL", "10")),
        "max_workers": int(os.getenv("TELEMETRY_MAX_WORKERS", "4"))
    }


async def initialize_telemetry_service() -> TelemetryService:
    """Initialize and configure the telemetry service"""
    try:
        config = get_telemetry_config()
        
        logger.info(f"Initializing telemetry service with config: {config}")
        
        # Create service instance
        service = TelemetryService(
            redis_url=config["redis_url"],
            mongodb_url=config["mongodb_url"],
            buffer_size=config["buffer_size"],
            batch_size=config["batch_size"],
            flush_interval_seconds=config["flush_interval_seconds"],
            max_workers=config["max_workers"]
        )
        
        # Initialize connections and start background tasks
        await service.initialize()
        
        logger.info("Telemetry service initialized successfully")
        
        return service
        
    except Exception as e:
        logger.error(f"Failed to initialize telemetry service: {str(e)}")
        raise


# Global telemetry service instance
_telemetry_service: Optional[TelemetryService] = None


async def get_telemetry_service() -> TelemetryService:
    """Get or create telemetry service instance"""
    global _telemetry_service
    
    if _telemetry_service is None:
        _telemetry_service = await initialize_telemetry_service()
    
    return _telemetry_service


async def shutdown_telemetry_service():
    """Gracefully shutdown telemetry service"""
    global _telemetry_service
    
    if _telemetry_service:
        logger.info("Shutting down telemetry service...")
        await _telemetry_service.shutdown()
        _telemetry_service = None
        logger.info("Telemetry service shutdown complete")