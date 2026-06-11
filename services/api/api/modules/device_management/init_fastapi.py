# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Device Management Module - FastAPI Initialization
Initializes the Device Management module for FastAPI applications

TESA IoT Platform
Copyright (C) 2024-2025 Wiroon Sriborrirux
"""

import logging
import asyncio
from fastapi import FastAPI

from .init_pooling import init_device_management_pooling, shutdown_device_management_pooling
from .init_event_streaming import initialize_event_streaming, shutdown_event_streaming
from .routes import device_management_router
from .services.device_service import ModularDeviceService
from .services.template_service import TemplateService
from .services.telemetry_service import telemetry_service
from .services.telemetry_analytics_service import telemetry_analytics_service
from .services.websocket_service import websocket_service
from .services.event_streaming_service import event_streaming_service
from .services.bulk_operations_service import BulkOperationsService, set_bulk_operations_service
from .repositories.device_repository import DeviceRepository
from .repositories.device_cache_repository import DeviceCacheRepository
from .repositories.template_repository import TemplateRepository
from .repositories.telemetry_analytics_repository import telemetry_analytics_repository
from .validators.device_validator import DeviceValidator

logger = logging.getLogger(__name__)


async def init_device_management_fastapi(app: FastAPI, mongodb_uri: str = None, mongodb_db_name: str = "tesa_iot"):
    """
    Initialize Device Management module for FastAPI with all features including event streaming
    
    Args:
        app: FastAPI application instance
        mongodb_uri: MongoDB connection URI
        mongodb_db_name: MongoDB database name
    """
    try:
        logger.info("Initializing Device Management module for FastAPI...")
        
        # Initialize connection pooling
        logger.info("Initializing connection pooling...")
        pooling_success = await init_device_management_pooling()
        
        if not pooling_success:
            logger.warning("Failed to initialize connection pooling, using standard connections")
        else:
            logger.info("Connection pooling initialized successfully")
        
        # Get database instance
        from motor.motor_asyncio import AsyncIOMotorClient
        db_client = AsyncIOMotorClient(mongodb_uri or 'mongodb://localhost:27017')
        db = db_client[mongodb_db_name]
        
        # Create repository instances
        repository = DeviceRepository()
        cache_repository = DeviceCacheRepository()
        template_repository = TemplateRepository(db)
        validator = DeviceValidator()
        
        # Create device service
        device_service = ModularDeviceService(
            repository=repository,
            cache_repository=cache_repository,
            validator=validator
        )
        
        # Create template service
        template_service = TemplateService(
            template_repository=template_repository,
            device_service=device_service
        )
        
        # Initialize template repository indexes
        await template_service.initialize()
        
        # Initialize telemetry services
        await telemetry_service.initialize()
        await telemetry_analytics_service.initialize()
        await telemetry_analytics_repository.initialize()
        
        # Initialize event streaming services
        await initialize_event_streaming(
            heartbeat_interval=30,
            heartbeat_timeout=60,
            max_message_size=1024 * 1024,  # 1MB
            rate_limit_per_minute=100,
            event_retention_hours=24
        )
        
        # Create and initialize bulk operations service
        bulk_operations_service = BulkOperationsService(
            device_service=device_service,
            repository=repository,
            cache_repository=cache_repository,
            validator=validator,
            max_workers=4,
            operation_timeout=3600
        )
        
        # Link bulk operations service to device service
        device_service._bulk_operations_service = bulk_operations_service
        
        # Store services in app state
        app.state.device_service = device_service
        app.state.bulk_operations_service = bulk_operations_service
        app.state.template_service = template_service
        app.state.telemetry_service = telemetry_service
        app.state.telemetry_analytics_service = telemetry_analytics_service
        app.state.websocket_service = websocket_service
        app.state.event_streaming_service = event_streaming_service
        
        # Set global bulk operations service
        set_bulk_operations_service(bulk_operations_service)
        
        # Include routers
        app.include_router(device_management_router, prefix="/api/v1")
        
        logger.info("Device Management module initialized successfully with all features")
        
        # Start background tasks
        asyncio.create_task(_periodic_cleanup(bulk_operations_service))
        
        # Register shutdown handlers
        @app.on_event("shutdown")
        async def shutdown_services():
            """Shutdown all services on app shutdown"""
            logger.info("Shutting down Device Management services...")
            
            # Shutdown event streaming
            await shutdown_event_streaming()
            
            # Shutdown telemetry services
            await telemetry_service.shutdown()
            await telemetry_analytics_service.shutdown()
            
            # Shutdown connection pooling
            await shutdown_device_management_pooling()
            
            logger.info("Device Management services shut down successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing Device Management module: {e}")
        raise


async def _periodic_cleanup(bulk_operations_service: BulkOperationsService):
    """Periodic cleanup task for old bulk operations"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await bulk_operations_service.cleanup_old_operations(retention_hours=24)
            logger.debug("Completed periodic cleanup of bulk operations")
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")


# Export initialization function
__all__ = ["init_device_management_fastapi"]