# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 TESAIoT Platform contributors.
#
# Originally derived from the TESAIoT Secure IoT Platform; relicensed under the
# Apache License, Version 2.0 by the copyright owner. See the NOTICE file in the
# distribution root for details.

"""
Dependency Injection Container for TESA IoT Platform
==================================================
Version: v2025.08
Module: Core DI Container
Purpose: Enable modular architecture with dependency injection

This module implements a lightweight dependency injection container
to support the safe modularization of the TESA IoT Platform.
It follows the Dependency Inversion Principle and enables easy
testing and gradual service extraction.
"""

from typing import Dict, Type, TypeVar, Callable, Any, Union
import inspect
import logging
import threading
from functools import wraps

T = TypeVar('T')

class DIContainer:
    """
    Lightweight dependency injection container for Python.
    
    Supports:
    - Singleton and transient lifetimes
    - Interface-based registration
    - Automatic dependency resolution
    - Thread-safe operations
    - Lazy initialization
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._interfaces: Dict[Type, Type] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def register_singleton(
        self, 
        interface: Type[T], 
        implementation: Union[Type[T], Callable[[], T], T]
    ) -> None:
        """
        Register a singleton service.
        
        Args:
            interface: The interface or base class
            implementation: The implementation class, factory, or instance
        """
        with self._lock:
            if isinstance(implementation, type):
                # Register class for lazy instantiation
                self._factories[interface] = lambda: self._create_instance(implementation)
            elif callable(implementation):
                # Register factory function
                self._factories[interface] = implementation
            else:
                # Register pre-created instance
                self._singletons[interface] = implementation
            
            self.logger.debug(f"Registered singleton: {interface.__name__}")
    
    def register_transient(
        self, 
        interface: Type[T], 
        implementation: Union[Type[T], Callable[[], T]]
    ) -> None:
        """
        Register a transient (per-request) service.
        
        Args:
            interface: The interface or base class
            implementation: The implementation class or factory
        """
        with self._lock:
            if isinstance(implementation, type):
                self._services[interface] = lambda: self._create_instance(implementation)
            else:
                self._services[interface] = implementation
            
            self.logger.debug(f"Registered transient: {interface.__name__}")
    
    def register_interface(self, interface: Type, implementation: Type) -> None:
        """
        Register an interface-to-implementation mapping.
        
        Args:
            interface: The interface (ABC)
            implementation: The concrete implementation
        """
        with self._lock:
            self._interfaces[interface] = implementation
            self.logger.debug(f"Registered interface mapping: {interface.__name__} -> {implementation.__name__}")
    
    def resolve(self, service_type: Type[T]) -> T:
        """
        Resolve a service by its type.
        
        Args:
            service_type: The type to resolve
            
        Returns:
            The resolved service instance
            
        Raises:
            ValueError: If the service is not registered
        """
        with self._lock:
            # Check if it's an interface mapping
            if service_type in self._interfaces:
                actual_type = self._interfaces[service_type]
                return self.resolve(actual_type)
            
            # Check for singleton instance
            if service_type in self._singletons:
                return self._singletons[service_type]
            
            # Check for singleton factory
            if service_type in self._factories:
                if service_type not in self._singletons:
                    self._singletons[service_type] = self._factories[service_type]()
                return self._singletons[service_type]
            
            # Check for transient service
            if service_type in self._services:
                return self._services[service_type]()
            
            # Try to auto-resolve if it's a concrete class
            if inspect.isclass(service_type) and not inspect.isabstract(service_type):
                return self._create_instance(service_type)
            
            raise ValueError(f"Service {service_type.__name__} is not registered")
    
    def _create_instance(self, cls: Type[T]) -> T:
        """
        Create an instance of a class, resolving its dependencies.
        
        Args:
            cls: The class to instantiate
            
        Returns:
            The created instance
        """
        # Get constructor parameters
        sig = inspect.signature(cls.__init__)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Get type annotation
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    params[param_name] = param.default
                continue
            
            # Try to resolve the dependency
            try:
                params[param_name] = self.resolve(param_type)
            except ValueError:
                if param.default != inspect.Parameter.empty:
                    params[param_name] = param.default
                else:
                    self.logger.warning(f"Cannot resolve parameter {param_name} of type {param_type} for {cls.__name__}")
        
        return cls(**params)
    
    def clear(self) -> None:
        """Clear all registrations."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()
            self._interfaces.clear()

# Global container instance
container = DIContainer()

def inject(func: Callable) -> Callable:
    """
    Decorator to inject dependencies into function parameters.
    
    Example:
        @inject
        def my_function(device_service: IDeviceService):
            return device_service.get_all_devices()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(func)
        new_kwargs = kwargs.copy()
        
        for param_name, param in sig.parameters.items():
            if param_name in kwargs:
                continue
            
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                continue
            
            try:
                new_kwargs[param_name] = container.resolve(param_type)
            except ValueError:
                pass
        
        return func(*args, **new_kwargs)
    
    return wrapper

class Injectable:
    """
    Base class for injectable services.
    Provides lifecycle hooks and dependency resolution.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def on_created(self) -> None:
        """Called after the service is created."""
        pass
    
    def on_resolved(self) -> None:
        """Called after all dependencies are resolved."""
        pass

def register_modular_services(app):
    """
    Register all modular services for the TESA IoT Platform.
    This function will be called during app initialization.
    
    Args:
        app: Flask application instance
    """
    # Community Edition: Protected Update (OTA) and the Analytics/Rust-bridge
    # modules are out of scope and have been removed. Only the in-scope core
    # services plus the Dashboard (telemetry) and Device Management modules are
    # registered here.
    from ..services.feature_flags import FeatureFlagService
    from ..services.parallel_runner import ParallelRunner

    # Register core services
    container.register_singleton(FeatureFlagService, FeatureFlagService)
    container.register_singleton(ParallelRunner, ParallelRunner)

    # Dashboard Module Services Registration
    try:
        from ..modules.dashboard.interfaces import (
            IDashboardUtilitiesService,
            IDashboardStatsService,
            IDashboardAnalyticsService,
            IDashboardRepository
        )
        from ..modules.dashboard.services.dashboard_utilities import DashboardUtilitiesService
        from ..modules.dashboard.services.dashboard_stats_service import ModularDashboardStatsService
        from ..modules.dashboard.services.dashboard_analytics_service import DashboardAnalyticsService
        from ..modules.dashboard.repositories.dashboard_stats_repository import DashboardStatsRepository
        from ..services.feature_flags import FeatureFlagService
        from ..core.database import db_manager
        
        # Register dashboard utilities service
        container.register_singleton(
            IDashboardUtilitiesService,
            lambda: DashboardUtilitiesService(
                db_session=db_manager.postgres_pool,
                redis_client=db_manager.redis_client
            )
        )
        
        # Register dashboard repository with database dependencies
        container.register_singleton(
            IDashboardRepository,
            lambda: DashboardStatsRepository(
                db_session=db_manager.mongo_db,
                cache_service=db_manager.redis_client
            )
        )
        
        # Register dashboard stats service with its dependencies
        container.register_singleton(
            IDashboardStatsService,
            lambda: ModularDashboardStatsService(
                repository=container.resolve(IDashboardRepository),
                cache_service=db_manager.redis_client,
                utilities_service=container.resolve(IDashboardUtilitiesService)
            )
        )
        
        # Register dashboard analytics service
        container.register_singleton(
            IDashboardAnalyticsService,
            lambda: DashboardAnalyticsService(
                repository=container.resolve(IDashboardRepository),
                cache_service=db_manager.redis_client,
                utilities_service=container.resolve(IDashboardUtilitiesService)
            )
        )
        
        # System monitoring dashboard (psutil-based) and predictive analytics are
        # out of scope for the Community Edition.

        container.logger.info("Dashboard module services registered successfully")
        
    except Exception as e:
        container.logger.error(f"Failed to register Dashboard module services: {str(e)}")
        # Continue with initialization even if Dashboard module fails
        # This ensures backward compatibility
    
    # Device Management Module Services Registration
    try:
        from ..modules.device_management.interfaces.device_interfaces import (
            IDeviceService,
            IDeviceRepository,
            IDeviceValidator,
            IDeviceCacheRepository
        )
        from ..modules.device_management.services.device_service import ModularDeviceService
        from ..modules.device_management.repositories.device_repository import DeviceRepository
        from ..modules.device_management.repositories.device_cache_repository import DeviceCacheRepository
        from ..modules.device_management.validators.device_validator import DeviceValidator
        from ..core.database import db_manager
        
        # Register device validator
        container.register_singleton(IDeviceValidator, DeviceValidator)
        
        # Register device cache repository
        container.register_singleton(
            IDeviceCacheRepository,
            lambda: DeviceCacheRepository(
                redis_client=db_manager.redis_client,
                default_ttl=300
            )
        )
        
        # Register device repository
        container.register_singleton(
            IDeviceRepository,
            lambda: DeviceRepository(
                collection_name="devices"
            )
        )
        
        # Register device service with its dependencies
        container.register_singleton(
            IDeviceService,
            lambda: ModularDeviceService(
                repository=container.resolve(IDeviceRepository),
                cache_repository=container.resolve(IDeviceCacheRepository),
                validator=container.resolve(IDeviceValidator),
                cache_ttl=300
            )
        )
        
        container.logger.info("Device Management module services registered successfully")

    except Exception as e:
        container.logger.error(f"Failed to register Device Management module services: {str(e)}")
        # Continue with initialization even if Device Management module fails
        # This ensures backward compatibility
    
    container.logger.info("Modular services registered successfully")

# Module exports
__all__ = [
    'DIContainer',
    'container',
    'inject',
    'Injectable',
    'register_modular_services'
]
