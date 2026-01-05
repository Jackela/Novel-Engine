#!/usr/bin/env python3
"""
Dependency Injection Container & Service Registry
================================================

Enterprise-grade dependency injection container with service discovery,
lifecycle management, and configuration integration.
"""

import asyncio
import inspect
import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    get_type_hints,
)

from .config_manager import ConfigurationManager
from .error_handler import CentralizedErrorHandler, ErrorContext

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ServiceScope(Enum):
    """Service lifecycle scopes."""

    SINGLETON = "singleton"  # Single instance for entire application
    TRANSIENT = "transient"  # New instance for each request
    REQUEST = "request"  # Single instance per request/operation
    THREAD = "thread"  # Single instance per thread


class ServiceState(Enum):
    """Service lifecycle states."""

    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceDescriptor:
    """Service registration descriptor."""

    interface: Type
    implementation: Type
    scope: ServiceScope = ServiceScope.SINGLETON
    dependencies: List[Type] = field(default_factory=list)
    factory: Optional[Callable] = None
    configuration_section: Optional[str] = None
    initialize_method: str = "initialize"
    startup_method: str = "startup"
    shutdown_method: str = "shutdown"
    health_check_method: str = "health_check"
    tags: Set[str] = field(default_factory=set)
    priority: int = 0  # Higher priority services start first


@dataclass
class ServiceInstance:
    """Service instance tracking."""

    descriptor: ServiceDescriptor
    instance: Any
    state: ServiceState = ServiceState.UNINITIALIZED
    created_at: datetime = field(default_factory=datetime.now)
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"
    error_count: int = 0


class DependencyResolutionError(Exception):
    """Raised when dependency resolution fails."""


class ServiceContainer:
    """
    Enterprise dependency injection container with service discovery.

    Features:
    - Service registration and discovery
    - Automatic dependency injection
    - Service lifecycle management
    - Health monitoring
    - Configuration integration
    - Thread-safe operations
    """

    def __init__(
        self,
        config_manager: Optional[ConfigurationManager] = None,
        error_handler: Optional[CentralizedErrorHandler] = None,
    ):
        """Initialize service container."""
        self.config_manager = config_manager
        self.error_handler = error_handler

        # Service registry
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Dict[str, ServiceInstance]] = (
            {}
        )  # Type -> {scope_key: instance}
        self._singletons: Dict[Type, ServiceInstance] = {}

        # Lifecycle management
        self._initialization_order: List[Type] = []
        self._startup_order: List[Type] = []
        self._shutdown_order: List[Type] = []

        # Thread safety
        self._lock = threading.RLock()
        self._initializing: Set[Type] = set()

        # Service tags for grouping
        self._tags: Dict[str, Set[Type]] = {}

        # Health monitoring
        self._health_checks: Dict[Type, Callable] = {}
        self._last_health_check = datetime.now()

        logger.info("Service container initialized")

    def register_service(
        self,
        interface: Type[T],
        implementation: Type[T],
        scope: ServiceScope = ServiceScope.SINGLETON,
        factory: Optional[Callable[[], T]] = None,
        configuration_section: Optional[str] = None,
        dependencies: Optional[List[Type]] = None,
        tags: Optional[Set[str]] = None,
        priority: int = 0,
    ) -> "ServiceContainer":
        """
        Register a service with the container.

        Args:
            interface: Service interface/protocol
            implementation: Concrete implementation
            scope: Service lifecycle scope
            factory: Optional factory function
            configuration_section: Configuration section name
            dependencies: Explicit dependencies
            tags: Service tags for grouping
            priority: Initialization priority (higher first)

        Returns:
            Self for method chaining
        """
        with self._lock:
            # Auto-detect dependencies if not provided
            if dependencies is None:
                dependencies = self._analyze_dependencies(implementation)

            descriptor = ServiceDescriptor(
                interface=interface,
                implementation=implementation,
                scope=scope,
                dependencies=dependencies,
                factory=factory,
                configuration_section=configuration_section,
                tags=tags or set(),
                priority=priority,
            )

            self._services[interface] = descriptor

            # Update tag mappings
            for tag in descriptor.tags:
                if tag not in self._tags:
                    self._tags[tag] = set()
                self._tags[tag].add(interface)

            # Update initialization order
            self._update_initialization_order()

            logger.debug(
                f"Registered service: {interface.__name__} -> {implementation.__name__}"
            )

        return self

    def register_singleton(self, interface: Type[T], instance: T) -> "ServiceContainer":
        """Register a singleton instance directly."""
        with self._lock:
            service_instance = ServiceInstance(
                descriptor=ServiceDescriptor(
                    interface=interface,
                    implementation=type(instance),
                    scope=ServiceScope.SINGLETON,
                ),
                instance=instance,
                state=ServiceState.RUNNING,
            )

            self._singletons[interface] = service_instance

            logger.debug(f"Registered singleton: {interface.__name__}")

        return self

    def get_service(self, service_type: Type[T], context: Optional[str] = None) -> T:
        """
        Resolve and return service instance.

        Args:
            service_type: Service interface type
            context: Optional context for scoped services

        Returns:
            Service instance

        Raises:
            DependencyResolutionError: If service cannot be resolved
        """
        try:
            with self._lock:
                # Check if already resolved as singleton
                if service_type in self._singletons:
                    return self._singletons[service_type].instance

                # Check if service is registered
                if service_type not in self._services:
                    raise DependencyResolutionError(
                        f"Service not registered: {service_type.__name__}"
                    )

                descriptor = self._services[service_type]
                scope_key = self._get_scope_key(descriptor.scope, context)

                # Check existing instances for this scope
                if service_type in self._instances:
                    if scope_key in self._instances[service_type]:
                        existing_instance = self._instances[service_type][scope_key]
                        if existing_instance.state == ServiceState.RUNNING:
                            return existing_instance.instance

                # Create new instance
                return self._create_instance(service_type, descriptor, scope_key)

        except Exception as e:
            if self.error_handler:
                error_context = ErrorContext(
                    component="ServiceContainer",
                    operation="get_service",
                    metadata={"service_type": service_type.__name__},
                )
                asyncio.create_task(self.error_handler.handle_error(e, error_context))

            raise DependencyResolutionError(
                f"Failed to resolve service {service_type.__name__}: {e}"
            )

    def get_services_by_tag(self, tag: str) -> List[Any]:
        """Get all services with specified tag."""
        with self._lock:
            if tag not in self._tags:
                return []

            services = []
            for service_type in self._tags[tag]:
                try:
                    services.append(self.get_service(service_type))
                except DependencyResolutionError:
                    logger.warning(
                        f"Failed to resolve tagged service: {service_type.__name__}"
                    )

            return services

    async def initialize_all_services(self) -> None:
        """Initialize all registered services in dependency order."""
        logger.info("Initializing all services...")

        initialized_count = 0
        failed_services = []

        for service_type in self._initialization_order:
            try:
                await self._initialize_service(service_type)
                initialized_count += 1
                logger.debug(f"Initialized service: {service_type.__name__}")

            except Exception as e:
                failed_services.append((service_type, str(e)))
                logger.error(
                    f"Failed to initialize service {service_type.__name__}: {e}"
                )

        if failed_services:
            failure_details = "; ".join(
                [f"{svc.__name__}: {err}" for svc, err in failed_services]
            )
            raise RuntimeError(
                f"Service initialization failed for {len(failed_services)} services: {failure_details}"
            )

        logger.info(f"Successfully initialized {initialized_count} services")

    async def startup_all_services(self) -> None:
        """Start all initialized services."""
        logger.info("Starting all services...")

        started_count = 0
        for service_type in self._startup_order:
            try:
                await self._startup_service(service_type)
                started_count += 1

            except Exception as e:
                logger.error(f"Failed to start service {service_type.__name__}: {e}")

        logger.info(f"Started {started_count} services")

    async def shutdown_all_services(self) -> None:
        """Shutdown all services in reverse order."""
        logger.info("Shutting down all services...")

        shutdown_count = 0
        # Shutdown in reverse order
        for service_type in reversed(self._shutdown_order):
            try:
                await self._shutdown_service(service_type)
                shutdown_count += 1

            except Exception as e:
                logger.error(f"Failed to shutdown service {service_type.__name__}: {e}")

        logger.info(f"Shut down {shutdown_count} services")

    async def perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all services."""
        health_results = {}

        with self._lock:
            all_instances = []

            # Collect all instances
            all_instances.extend(self._singletons.values())
            for instances_dict in self._instances.values():
                all_instances.extend(instances_dict.values())

        for instance in all_instances:
            service_name = instance.descriptor.interface.__name__

            try:
                health_result = await self._check_service_health(instance)
                health_results[service_name] = health_result

                # Update instance health status
                instance.last_health_check = datetime.now()
                instance.health_status = (
                    "healthy" if health_result["healthy"] else "unhealthy"
                )

            except Exception as e:
                health_results[service_name] = {
                    "healthy": False,
                    "error": str(e),
                    "last_check": datetime.now().isoformat(),
                }
                instance.error_count += 1

        self._last_health_check = datetime.now()
        return health_results

    def get_service_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get complete service registry information."""
        with self._lock:
            registry = {}

            for service_type, descriptor in self._services.items():
                service_name = service_type.__name__

                # Get instance information
                instance_info = None
                if service_type in self._singletons:
                    instance = self._singletons[service_type]
                    instance_info = {
                        "state": instance.state.value,
                        "created_at": instance.created_at.isoformat(),
                        "health_status": instance.health_status,
                        "error_count": instance.error_count,
                    }

                registry[service_name] = {
                    "interface": service_type.__name__,
                    "implementation": descriptor.implementation.__name__,
                    "scope": descriptor.scope.value,
                    "dependencies": [dep.__name__ for dep in descriptor.dependencies],
                    "tags": list(descriptor.tags),
                    "priority": descriptor.priority,
                    "configuration_section": descriptor.configuration_section,
                    "instance": instance_info,
                }

            return registry

    def _analyze_dependencies(self, implementation: Type) -> List[Type]:
        """Analyze constructor dependencies using type hints."""
        dependencies = []

        try:
            # Get constructor signature
            init_signature = inspect.signature(implementation.__init__)
            type_hints = get_type_hints(implementation.__init__)

            for param_name, param in init_signature.parameters.items():
                if param_name == "self":
                    continue

                # Look for type hint
                if param_name in type_hints:
                    param_type = type_hints[param_name]

                    # Skip basic types and optionals
                    if not self._is_injectable_type(param_type):
                        continue

                    dependencies.append(param_type)

        except Exception as e:
            logger.debug(
                f"Could not analyze dependencies for {implementation.__name__}: {e}"
            )

        return dependencies

    def _is_injectable_type(self, type_hint: Type) -> bool:
        """Check if type is suitable for injection."""
        # Skip basic Python types
        basic_types = (str, int, float, bool, dict, list, set, tuple)
        if type_hint in basic_types:
            return False

        # Skip typing constructs
        if hasattr(type_hint, "__origin__"):
            return False

        # Must be a class
        return inspect.isclass(type_hint)

    def _get_scope_key(self, scope: ServiceScope, context: Optional[str]) -> str:
        """Generate scope key for service instance tracking."""
        if scope == ServiceScope.SINGLETON:
            return "singleton"
        elif scope == ServiceScope.TRANSIENT:
            return f"transient_{id(threading.current_thread())}"
        elif scope == ServiceScope.REQUEST:
            return context or "default_request"
        elif scope == ServiceScope.THREAD:
            return f"thread_{threading.current_thread().ident}"

        return "default"

    def _create_instance(
        self, service_type: Type, descriptor: ServiceDescriptor, scope_key: str
    ) -> Any:
        """Create new service instance with dependency injection."""
        if service_type in self._initializing:
            raise DependencyResolutionError(
                f"Circular dependency detected for {service_type.__name__}"
            )

        self._initializing.add(service_type)

        try:
            # Resolve dependencies
            dependencies = {}
            for dep_type in descriptor.dependencies:
                dependencies[dep_type] = self.get_service(dep_type)

            # Create instance
            if descriptor.factory:
                instance = descriptor.factory()
            else:
                # Use constructor injection
                instance = self._construct_with_dependencies(
                    descriptor.implementation, dependencies
                )

            # Apply configuration if specified
            if descriptor.configuration_section and self.config_manager:
                self._apply_configuration(instance, descriptor.configuration_section)

            # Create service instance wrapper
            service_instance = ServiceInstance(
                descriptor=descriptor, instance=instance, state=ServiceState.INITIALIZED
            )

            # Store instance
            if descriptor.scope == ServiceScope.SINGLETON:
                self._singletons[service_type] = service_instance
            else:
                if service_type not in self._instances:
                    self._instances[service_type] = {}
                self._instances[service_type][scope_key] = service_instance

            return instance

        finally:
            self._initializing.discard(service_type)

    def _construct_with_dependencies(
        self, implementation: Type, dependencies: Dict[Type, Any]
    ) -> Any:
        """Construct instance with dependency injection."""
        try:
            # Get constructor parameters
            init_signature = inspect.signature(implementation.__init__)
            type_hints = get_type_hints(implementation.__init__)

            # Build constructor arguments
            constructor_args = {}
            for param_name, param in init_signature.parameters.items():
                if param_name == "self":
                    continue

                # Match by type hint
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    if param_type in dependencies:
                        constructor_args[param_name] = dependencies[param_type]
                    elif param.default is not param.empty:
                        # Has default value, skip
                        continue
                    else:
                        # Required parameter without dependency
                        logger.warning(
                            f"No dependency found for required parameter {param_name} of type {param_type}"
                        )

            return implementation(**constructor_args)

        except Exception as e:
            logger.error(f"Failed to construct {implementation.__name__}: {e}")
            raise

    def _apply_configuration(self, instance: Any, config_section: str) -> None:
        """Apply configuration to service instance."""
        if not self.config_manager:
            return

        try:
            config_data = self.config_manager.get_section(config_section)

            # Apply configuration properties
            for key, value in config_data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

        except Exception as e:
            logger.warning(
                f"Failed to apply configuration to {type(instance).__name__}: {e}"
            )

    def _update_initialization_order(self) -> None:
        """Update service initialization order based on dependencies."""
        # Topological sort of services based on dependencies
        visited = set()
        temp_visited = set()
        order = []

        def visit(service_type: Type):
            if service_type in temp_visited:
                raise DependencyResolutionError(
                    f"Circular dependency involving {service_type.__name__}"
                )

            if service_type in visited:
                return

            temp_visited.add(service_type)

            if service_type in self._services:
                descriptor = self._services[service_type]
                for dep in descriptor.dependencies:
                    if dep in self._services:
                        visit(dep)

            temp_visited.remove(service_type)
            visited.add(service_type)
            order.append(service_type)

        # Visit all services
        for service_type in self._services.keys():
            if service_type not in visited:
                visit(service_type)

        # Sort by priority (higher priority first)
        self._initialization_order = sorted(
            order, key=lambda st: self._services[st].priority, reverse=True
        )

        # Startup and shutdown orders
        self._startup_order = self._initialization_order.copy()
        self._shutdown_order = self._initialization_order.copy()

    async def _initialize_service(self, service_type: Type) -> None:
        """Initialize a specific service."""
        instance = self.get_service(service_type)
        descriptor = self._services[service_type]

        # Find the service instance wrapper
        service_instance = None
        if service_type in self._singletons:
            service_instance = self._singletons[service_type]
        else:
            # Find first instance
            if service_type in self._instances:
                service_instance = next(iter(self._instances[service_type].values()))

        if service_instance and hasattr(instance, descriptor.initialize_method):
            service_instance.state = ServiceState.INITIALIZING

            try:
                init_method = getattr(instance, descriptor.initialize_method)

                if asyncio.iscoroutinefunction(init_method):
                    await init_method()
                else:
                    init_method()

                service_instance.state = ServiceState.INITIALIZED

            except Exception:
                service_instance.state = ServiceState.FAILED
                raise

    async def _startup_service(self, service_type: Type) -> None:
        """Start a specific service."""
        instance = self.get_service(service_type)
        descriptor = self._services[service_type]

        # Find the service instance wrapper
        service_instance = None
        if service_type in self._singletons:
            service_instance = self._singletons[service_type]
        else:
            if service_type in self._instances:
                service_instance = next(iter(self._instances[service_type].values()))

        if service_instance and hasattr(instance, descriptor.startup_method):
            service_instance.state = ServiceState.STARTING

            try:
                startup_method = getattr(instance, descriptor.startup_method)

                if asyncio.iscoroutinefunction(startup_method):
                    await startup_method()
                else:
                    startup_method()

                service_instance.state = ServiceState.RUNNING

            except Exception:
                service_instance.state = ServiceState.FAILED
                raise

    async def _shutdown_service(self, service_type: Type) -> None:
        """Shutdown a specific service."""
        try:
            instance = self.get_service(service_type)
            descriptor = self._services[service_type]

            # Find the service instance wrapper
            service_instance = None
            if service_type in self._singletons:
                service_instance = self._singletons[service_type]
            else:
                if service_type in self._instances:
                    service_instance = next(
                        iter(self._instances[service_type].values())
                    )

            if service_instance and hasattr(instance, descriptor.shutdown_method):
                service_instance.state = ServiceState.STOPPING

                try:
                    shutdown_method = getattr(instance, descriptor.shutdown_method)

                    if asyncio.iscoroutinefunction(shutdown_method):
                        await shutdown_method()
                    else:
                        shutdown_method()

                    service_instance.state = ServiceState.STOPPED

                except Exception:
                    service_instance.state = ServiceState.FAILED
                    raise

        except DependencyResolutionError:
            # Service not found or not initialized, skip
            pass

    async def _check_service_health(
        self, service_instance: ServiceInstance
    ) -> Dict[str, Any]:
        """Check health of a specific service."""
        instance = service_instance.instance
        descriptor = service_instance.descriptor

        health_result = {
            "healthy": True,
            "status": service_instance.state.value,
            "last_check": datetime.now().isoformat(),
            "error_count": service_instance.error_count,
        }

        # Call health check method if available
        if hasattr(instance, descriptor.health_check_method):
            try:
                health_method = getattr(instance, descriptor.health_check_method)

                if asyncio.iscoroutinefunction(health_method):
                    result = await health_method()
                else:
                    result = health_method()

                if isinstance(result, dict):
                    health_result.update(result)
                elif isinstance(result, bool):
                    health_result["healthy"] = result

            except Exception as e:
                health_result["healthy"] = False
                health_result["error"] = str(e)

        return health_result


# Global service container instance
_global_container: Optional[ServiceContainer] = None


def get_service_container() -> ServiceContainer:
    """Get global service container instance."""
    global _global_container
    if _global_container is None:
        _global_container = ServiceContainer()
    return _global_container


def register_service(
    interface: Type[T], implementation: Type[T], **kwargs
) -> ServiceContainer:
    """Register service with global container."""
    return get_service_container().register_service(interface, implementation, **kwargs)


def get_service(service_type: Type[T]) -> T:
    """Get service from global container."""
    return get_service_container().get_service(service_type)


@asynccontextmanager
async def service_container_context(container: ServiceContainer):
    """Context manager for service container lifecycle."""
    try:
        await container.initialize_all_services()
        await container.startup_all_services()
        yield container
    finally:
        await container.shutdown_all_services()
