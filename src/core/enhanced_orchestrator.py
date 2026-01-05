#!/usr/bin/env python3
"""
Enhanced System Orchestrator
===========================

Next-generation system orchestrator with dependency injection, event-driven architecture,
and enterprise-grade resource management.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from src.interactions.interaction_engine import InteractionEngine

# Import subsystem interfaces
from src.memory.layered_memory import LayeredMemorySystem
from src.templates.dynamic_template_engine import DynamicTemplateEngine

from .config_manager import ConfigurationManager
from .database_manager import DatabaseConfig, DatabaseManager, DatabaseType
from .error_handler import CentralizedErrorHandler
from .event_bus import Event, EventBus, EventHandler, EventPriority
from .narrative import EmergentNarrativeEngine

# Import new architectural components
from .service_container import (
    ServiceContainer,
    ServiceScope,
)
from .subjective_reality import SubjectiveRealityEngine

# Import existing core components
from .system_orchestrator import (
    OrchestratorConfig,
    OrchestratorMode,
    SystemHealth,
    SystemOrchestrator,
)

logger = logging.getLogger(__name__)


class EnhancedOrchestratorMode(Enum):
    """Enhanced orchestrator operational modes."""

    DEVELOPMENT = "development"  # Development with all debugging features
    STAGING = "staging"  # Pre-production testing environment
    PRODUCTION = "production"  # Production deployment
    DISASTER_RECOVERY = "disaster_recovery"  # Emergency recovery mode
    MAINTENANCE = "maintenance"  # Maintenance mode with limited functionality


@dataclass
class EnhancedOrchestratorConfig:
    """Enhanced orchestrator configuration."""

    mode: EnhancedOrchestratorMode = EnhancedOrchestratorMode.DEVELOPMENT

    # Core system configuration
    max_concurrent_agents: int = 50
    enable_event_sourcing: bool = True
    enable_performance_monitoring: bool = True
    enable_health_monitoring: bool = True

    # Database configuration
    database_type: DatabaseType = DatabaseType.SQLITE
    database_connection_string: str = "data/enhanced_novel_engine.db"
    database_min_pool_size: int = 5
    database_max_pool_size: int = 50

    # Event system configuration
    event_processing_workers: int = 4
    max_event_queue_size: int = 10000
    event_retry_attempts: int = 3

    # Service configuration
    service_startup_timeout: float = 30.0
    service_shutdown_timeout: float = 15.0
    enable_service_discovery: bool = True

    # Monitoring configuration
    health_check_interval: float = 60.0
    metrics_collection_interval: float = 30.0
    performance_alert_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "error_rate": 5.0,
            "response_time": 2.0,
        }
    )

    # Debug configuration
    debug_logging: bool = True
    enable_request_tracing: bool = True
    log_level: str = "INFO"


class SystemStartupEvent:
    """System startup event payload."""

    def __init__(self, orchestrator_id: str, mode: str, timestamp: datetime):
        self.orchestrator_id = orchestrator_id
        self.mode = mode
        self.timestamp = timestamp


class SystemShutdownEvent:
    """System shutdown event payload."""

    def __init__(
        self, orchestrator_id: str, uptime_seconds: float, timestamp: datetime
    ):
        self.orchestrator_id = orchestrator_id
        self.uptime_seconds = uptime_seconds
        self.timestamp = timestamp


class SystemHealthEvent:
    """System health status change event."""

    def __init__(
        self, previous_health: str, current_health: str, details: Dict[str, Any]
    ):
        self.previous_health = previous_health
        self.current_health = current_health
        self.details = details


class SystemMetricsEvent:
    """System performance metrics event."""

    def __init__(self, metrics: Dict[str, Any], timestamp: datetime):
        self.metrics = metrics
        self.timestamp = timestamp


class HealthMonitoringHandler(EventHandler):
    """Health monitoring event handler."""

    def __init__(self, orchestrator: "EnhancedSystemOrchestrator"):
        self.orchestrator = orchestrator

    async def handle(self, event: Event) -> bool:
        """Handle health-related events."""
        try:
            if event.event_type == "system.health.changed":
                payload = event.payload
                logger.info(
                    f"Health status changed: {payload.previous_health} -> {payload.current_health}"
                )

                # Take action based on health status
                if payload.current_health == "critical":
                    await self.orchestrator._handle_critical_health_event(payload)
                elif payload.current_health == "degraded":
                    await self.orchestrator._handle_degraded_health_event(payload)

                return True

        except Exception as e:
            logger.error(f"Health monitoring handler error: {e}")
            return False


class PerformanceMonitoringHandler(EventHandler):
    """Performance monitoring event handler."""

    def __init__(self, orchestrator: "EnhancedSystemOrchestrator"):
        self.orchestrator = orchestrator

    async def handle(self, event: Event) -> bool:
        """Handle performance metrics events."""
        try:
            if event.event_type == "system.metrics.collected":
                payload = event.payload

                # Check performance thresholds
                await self.orchestrator._check_performance_thresholds(payload.metrics)

                return True

        except Exception as e:
            logger.error(f"Performance monitoring handler error: {e}")
            return False


class EnhancedSystemOrchestrator:
    """
    Enhanced system orchestrator with enterprise-grade architecture.

    Features:
    - Dependency injection container
    - Event-driven architecture
    - Database connection pooling
    - Comprehensive health monitoring
    - Performance metrics and alerting
    - Service lifecycle management
    - Configuration management integration
    - Error handling and recovery
    """

    def __init__(self, config: Optional[EnhancedOrchestratorConfig] = None):
        """Initialize enhanced system orchestrator."""
        self.config = config or EnhancedOrchestratorConfig()
        self.orchestrator_id = (
            f"orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.startup_time = datetime.now()

        # Core architectural components
        self.config_manager: Optional[ConfigurationManager] = None
        self.error_handler: Optional[CentralizedErrorHandler] = None
        self.service_container: Optional[ServiceContainer] = None
        self.event_bus: Optional[EventBus] = None
        self.database_manager: Optional[DatabaseManager] = None

        # Legacy orchestrator for compatibility
        self.legacy_orchestrator: Optional[SystemOrchestrator] = None

        # System state
        self.current_health = SystemHealth.OPTIMAL
        self.is_initialized = False
        self.is_running = False
        self.shutdown_requested = False

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []

        # Performance metrics
        self._system_metrics = {
            "startup_time": self.startup_time,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "active_agents": 0,
            "average_response_time": 0.0,
            "peak_memory_usage": 0.0,
            "cpu_usage": 0.0,
        }

        logger.info(f"Enhanced orchestrator initialized: {self.orchestrator_id}")

    async def startup(self) -> Dict[str, Any]:
        """
        Start enhanced system orchestrator with full initialization.

        Returns:
            Dict containing startup results and system information
        """
        if self.is_initialized:
            return {"success": True, "message": "Already initialized"}

        try:
            logger.info("=== Enhanced System Orchestrator Startup ===")
            startup_start = datetime.now()

            # Initialize core architectural components
            await self._initialize_core_components()

            # Register core services
            await self._register_core_services()

            # Initialize service container
            await self._initialize_services()

            # Initialize legacy orchestrator for compatibility
            await self._initialize_legacy_orchestrator()

            # Start background tasks
            await self._start_background_tasks()

            # Publish startup event
            await self._publish_startup_event()

            # Perform initial health check
            await self._perform_initial_health_check()

            self.is_initialized = True
            self.is_running = True

            startup_duration = (datetime.now() - startup_start).total_seconds()

            startup_result = {
                "success": True,
                "orchestrator_id": self.orchestrator_id,
                "startup_duration": startup_duration,
                "mode": self.config.mode.value,
                "services_initialized": (
                    len(self.service_container._services)
                    if self.service_container
                    else 0
                ),
                "database_pools": (
                    len(self.database_manager._pools) if self.database_manager else 0
                ),
                "health_status": self.current_health.value,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"Enhanced orchestrator startup completed in {startup_duration:.2f}s"
            )
            return startup_result

        except Exception as e:
            logger.error(f"Enhanced orchestrator startup failed: {e}")
            self.current_health = SystemHealth.CRITICAL

            # Try to cleanup partial initialization
            try:
                await self.shutdown()
            except Exception:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def shutdown(self) -> Dict[str, Any]:
        """
        Gracefully shutdown enhanced system orchestrator.

        Returns:
            Dict containing shutdown results
        """
        if not self.is_running:
            return {"success": True, "message": "Already shutdown"}

        try:
            logger.info("=== Enhanced System Orchestrator Shutdown ===")
            shutdown_start = datetime.now()

            self.shutdown_requested = True
            self.is_running = False

            # Publish shutdown event
            uptime = (datetime.now() - self.startup_time).total_seconds()
            await self._publish_shutdown_event(uptime)

            # Stop background tasks
            await self._stop_background_tasks()

            # Shutdown legacy orchestrator
            if self.legacy_orchestrator:
                await self.legacy_orchestrator.shutdown()

            # Shutdown services
            if self.service_container:
                await self.service_container.shutdown_all_services()

            # Close database connections
            if self.database_manager:
                await self.database_manager.close_all_pools()

            # Stop event bus
            if self.event_bus:
                await self.event_bus.stop()

            shutdown_duration = (datetime.now() - shutdown_start).total_seconds()

            shutdown_result = {
                "success": True,
                "orchestrator_id": self.orchestrator_id,
                "shutdown_duration": shutdown_duration,
                "uptime_seconds": uptime,
                "total_requests": self._system_metrics["total_requests"],
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"Enhanced orchestrator shutdown completed in {shutdown_duration:.2f}s"
            )
            return shutdown_result

        except Exception as e:
            logger.error(f"Enhanced orchestrator shutdown failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def _initialize_core_components(self) -> None:
        """Initialize core architectural components."""
        logger.info("Initializing core components...")

        # Configuration manager
        self.config_manager = ConfigurationManager()
        logger.debug("Configuration manager initialized")

        # Error handler
        self.error_handler = CentralizedErrorHandler()
        logger.debug("Error handler initialized")

        # Service container
        self.service_container = ServiceContainer(
            self.config_manager, self.error_handler
        )
        logger.debug("Service container initialized")

        # Event bus
        self.event_bus = EventBus(
            self.error_handler, enable_event_store=self.config.enable_event_sourcing
        )
        await self.event_bus.start()
        logger.debug("Event bus initialized")

        # Database manager
        self.database_manager = DatabaseManager(self.config_manager, self.error_handler)

        # Create database config from orchestrator config
        db_config = DatabaseConfig(
            database_type=self.config.database_type,
            connection_string=self.config.database_connection_string,
            min_pool_size=self.config.database_min_pool_size,
            max_pool_size=self.config.database_max_pool_size,
        )

        await self.database_manager.add_pool("default", db_config)
        logger.debug("Database manager initialized")

    async def _register_core_services(self) -> None:
        """Register core services with dependency injection container."""
        logger.info("Registering core services...")

        # Register core components as singletons
        self.service_container.register_singleton(
            ConfigurationManager, self.config_manager
        )
        self.service_container.register_singleton(
            CentralizedErrorHandler, self.error_handler
        )
        self.service_container.register_singleton(EventBus, self.event_bus)
        self.service_container.register_singleton(
            DatabaseManager, self.database_manager
        )

        # Register enhanced orchestrator as singleton
        self.service_container.register_singleton(EnhancedSystemOrchestrator, self)

        # Register narrative engines
        self.service_container.register_service(
            SubjectiveRealityEngine,
            SubjectiveRealityEngine,
            scope=ServiceScope.SINGLETON,
            priority=100,
            tags={"narrative", "engine"},
        )

        self.service_container.register_service(
            EmergentNarrativeEngine,
            EmergentNarrativeEngine,
            scope=ServiceScope.SINGLETON,
            priority=100,
            tags={"narrative", "engine"},
        )

        # Register memory systems
        self.service_container.register_service(
            LayeredMemorySystem,
            LayeredMemorySystem,
            scope=ServiceScope.SINGLETON,
            priority=90,
            tags={"memory", "core"},
        )

        # Register template engine
        self.service_container.register_service(
            DynamicTemplateEngine,
            DynamicTemplateEngine,
            scope=ServiceScope.SINGLETON,
            priority=80,
            tags={"templates", "core"},
        )

        # Register interaction engine
        self.service_container.register_service(
            InteractionEngine,
            InteractionEngine,
            scope=ServiceScope.SINGLETON,
            priority=70,
            tags={"interaction", "core"},
        )

        logger.debug(f"Registered {len(self.service_container._services)} services")

    async def _initialize_services(self) -> None:
        """Initialize all registered services."""
        logger.info("Initializing services...")

        # Initialize and start all services
        await self.service_container.initialize_all_services()
        await self.service_container.startup_all_services()

        logger.debug("All services initialized and started")

    async def _initialize_legacy_orchestrator(self) -> None:
        """Initialize legacy orchestrator for backward compatibility."""
        logger.info("Initializing legacy orchestrator...")

        # Create legacy config
        legacy_config = OrchestratorConfig(
            mode=(
                OrchestratorMode.PRODUCTION
                if self.config.mode == EnhancedOrchestratorMode.PRODUCTION
                else OrchestratorMode.DEVELOPMENT
            ),
            max_concurrent_agents=self.config.max_concurrent_agents,
            debug_logging=self.config.debug_logging,
        )

        # Initialize legacy orchestrator with shared database
        self.legacy_orchestrator = SystemOrchestrator(
            database_path=self.config.database_connection_string,
            config=legacy_config,
            event_bus=self.event_bus,
            database=self.database_manager,
        )

        # Start legacy orchestrator
        startup_result = await self.legacy_orchestrator.startup()
        if not startup_result.success:
            raise RuntimeError(
                f"Legacy orchestrator startup failed: {startup_result.error}"
            )

        logger.debug("Legacy orchestrator initialized")

    async def _start_background_tasks(self) -> None:
        """Start background monitoring and maintenance tasks."""
        logger.info("Starting background tasks...")

        # Register event handlers
        health_handler = HealthMonitoringHandler(self)
        performance_handler = PerformanceMonitoringHandler(self)

        self.event_bus.subscribe("system.health.changed", health_handler, priority=100)
        self.event_bus.subscribe(
            "system.metrics.collected", performance_handler, priority=100
        )

        # Start health monitoring task
        if self.config.enable_health_monitoring:
            health_task = asyncio.create_task(self._health_monitoring_loop())
            self._background_tasks.append(health_task)

        # Start performance monitoring task
        if self.config.enable_performance_monitoring:
            perf_task = asyncio.create_task(self._performance_monitoring_loop())
            self._background_tasks.append(perf_task)

        # Start service health check task
        service_health_task = asyncio.create_task(self._service_health_check_loop())
        self._background_tasks.append(service_health_task)

        logger.debug(f"Started {len(self._background_tasks)} background tasks")

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        logger.info("Stopping background tasks...")

        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        logger.debug("Background tasks stopped")

    async def _publish_startup_event(self) -> None:
        """Publish system startup event."""
        startup_event = Event(
            event_type="system.startup",
            payload=SystemStartupEvent(
                orchestrator_id=self.orchestrator_id,
                mode=self.config.mode.value,
                timestamp=datetime.now(),
            ),
            metadata={
                "priority": EventPriority.SYSTEM,
                "source": "enhanced_orchestrator",
            },
        )

        await self.event_bus.publish(startup_event)

    async def _publish_shutdown_event(self, uptime_seconds: float) -> None:
        """Publish system shutdown event."""
        shutdown_event = Event(
            event_type="system.shutdown",
            payload=SystemShutdownEvent(
                orchestrator_id=self.orchestrator_id,
                uptime_seconds=uptime_seconds,
                timestamp=datetime.now(),
            ),
            metadata={
                "priority": EventPriority.SYSTEM,
                "source": "enhanced_orchestrator",
            },
        )

        await self.event_bus.publish(shutdown_event)

    async def _perform_initial_health_check(self) -> None:
        """Perform initial comprehensive health check."""
        logger.info("Performing initial health check...")

        try:
            # Check database health
            db_health = await self.database_manager.health_check()

            # Check service health
            service_health = await self.service_container.perform_health_checks()

            # Check legacy orchestrator health
            legacy_metrics = await self.legacy_orchestrator.get_system_metrics()

            # Determine overall health
            all_healthy = (
                all(pool["healthy"] for pool in db_health.values())
                and all(result["healthy"] for result in service_health.values())
                and legacy_metrics.success
            )

            self.current_health = (
                SystemHealth.OPTIMAL if all_healthy else SystemHealth.DEGRADED
            )

            logger.info(f"Initial health check completed: {self.current_health.value}")

        except Exception as e:
            logger.error(f"Initial health check failed: {e}")
            self.current_health = SystemHealth.CRITICAL

    async def _health_monitoring_loop(self) -> None:
        """Background health monitoring loop."""
        while not self.shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)

                if self.shutdown_requested:
                    break

                # Perform health checks
                previous_health = self.current_health
                await self._check_system_health()

                # Publish health change event if status changed
                if self.current_health != previous_health:
                    health_event = Event(
                        event_type="system.health.changed",
                        payload=SystemHealthEvent(
                            previous_health=previous_health.value,
                            current_health=self.current_health.value,
                            details={},
                        ),
                    )
                    await self.event_bus.publish(health_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring loop error: {e}")

    async def _performance_monitoring_loop(self) -> None:
        """Background performance monitoring loop."""
        while not self.shutdown_requested:
            try:
                await asyncio.sleep(self.config.metrics_collection_interval)

                if self.shutdown_requested:
                    break

                # Collect performance metrics
                await self._collect_performance_metrics()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")

    async def _service_health_check_loop(self) -> None:
        """Background service health check loop."""
        while not self.shutdown_requested:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                if self.shutdown_requested:
                    break

                # Perform service health checks
                health_results = await self.service_container.perform_health_checks()

                # Log any unhealthy services
                for service_name, health_result in health_results.items():
                    if not health_result.get("healthy", False):
                        logger.warning(
                            f"Service {service_name} is unhealthy: {health_result}"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Service health check loop error: {e}")

    async def _check_system_health(self) -> None:
        """Check overall system health."""
        try:
            # Check database health
            db_health = await self.database_manager.health_check()
            db_healthy = all(pool["healthy"] for pool in db_health.values())

            # Check service health
            service_health = await self.service_container.perform_health_checks()
            services_healthy = all(
                result["healthy"] for result in service_health.values()
            )

            # Check event bus health
            event_stats = self.event_bus.get_statistics()
            event_healthy = (
                event_stats["processing_stats"]["error_rate"] < 0.1
            )  # Less than 10% error rate

            # Determine overall health
            if not db_healthy or not services_healthy or not event_healthy:
                if not db_healthy:
                    self.current_health = SystemHealth.CRITICAL
                else:
                    self.current_health = SystemHealth.DEGRADED
            else:
                self.current_health = SystemHealth.OPTIMAL

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            self.current_health = SystemHealth.CRITICAL

    async def _collect_performance_metrics(self) -> None:
        """Collect system performance metrics."""
        try:
            # Update system metrics
            uptime = (datetime.now() - self.startup_time).total_seconds()

            # Get database metrics
            db_metrics = self.database_manager.get_pool_metrics()

            # Get service metrics
            service_registry = self.service_container.get_service_registry()

            # Get event bus metrics
            event_stats = self.event_bus.get_statistics()

            # Get legacy orchestrator metrics
            legacy_metrics = await self.legacy_orchestrator.get_system_metrics()

            comprehensive_metrics = {
                "uptime_seconds": uptime,
                "orchestrator_id": self.orchestrator_id,
                "health_status": self.current_health.value,
                "database_metrics": db_metrics,
                "service_count": len(service_registry),
                "event_bus_stats": event_stats,
                "legacy_orchestrator": (
                    legacy_metrics.data if legacy_metrics.success else None
                ),
                "timestamp": datetime.now().isoformat(),
            }

            # Publish metrics event
            metrics_event = Event(
                event_type="system.metrics.collected",
                payload=SystemMetricsEvent(
                    metrics=comprehensive_metrics, timestamp=datetime.now()
                ),
            )
            await self.event_bus.publish(metrics_event)

        except Exception as e:
            logger.error(f"Performance metrics collection failed: {e}")

    async def _check_performance_thresholds(self, metrics: Dict[str, Any]) -> None:
        """Check performance metrics against configured thresholds."""
        thresholds = self.config.performance_alert_thresholds

        # Check error rate
        event_stats = metrics.get("event_bus_stats", {})
        processing_stats = event_stats.get("processing_stats", {})
        error_rate = (
            processing_stats.get("error_rate", 0.0) * 100
        )  # Convert to percentage

        if error_rate > thresholds.get("error_rate", 5.0):
            logger.warning(f"High error rate detected: {error_rate:.2f}%")

    async def _handle_critical_health_event(
        self, health_event: SystemHealthEvent
    ) -> None:
        """Handle critical health status."""
        logger.critical(f"System health critical: {health_event.details}")

        # In a real implementation, this might trigger:
        # - Automatic failover
        # - Emergency notifications
        # - Service restart attempts
        # - Graceful degradation

    async def _handle_degraded_health_event(
        self, health_event: SystemHealthEvent
    ) -> None:
        """Handle degraded health status."""
        logger.warning(f"System health degraded: {health_event.details}")

        # In a real implementation, this might trigger:
        # - Performance optimization
        # - Resource cleanup
        # - Load balancing adjustments

    def get_service(self, service_type: Type) -> Any:
        """Get service instance from container."""
        return self.service_container.get_service(service_type)

    async def publish_event(self, event_type: str, payload: Any, **metadata) -> None:
        """Publish event through event bus."""
        event = Event(event_type=event_type, payload=payload, metadata=metadata)
        await self.event_bus.publish(event)

    async def get_database_connection(self, pool_name: str = "default"):
        """Get database connection from pool."""
        return await self.database_manager.get_connection(pool_name)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        uptime = (datetime.now() - self.startup_time).total_seconds()

        return {
            "orchestrator_id": self.orchestrator_id,
            "mode": self.config.mode.value,
            "health_status": self.current_health.value,
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "uptime_seconds": uptime,
            "startup_time": self.startup_time.isoformat(),
            "service_count": (
                len(self.service_container._services) if self.service_container else 0
            ),
            "database_pools": (
                len(self.database_manager._pools) if self.database_manager else 0
            ),
            "event_processing": (
                self.event_bus.get_statistics() if self.event_bus else {}
            ),
            "background_tasks": len(self._background_tasks),
            "total_requests": self._system_metrics["total_requests"],
            "timestamp": datetime.now().isoformat(),
        }

    # Legacy compatibility methods
    async def create_agent_context(self, agent_id: str, initial_state=None):
        """Create agent context (legacy compatibility)."""
        if self.legacy_orchestrator:
            return await self.legacy_orchestrator.create_agent_context(
                agent_id, initial_state
            )
        else:
            raise RuntimeError("Legacy orchestrator not initialized")

    async def process_dynamic_context(self, context):
        """Process dynamic context (legacy compatibility)."""
        if self.legacy_orchestrator:
            return await self.legacy_orchestrator.process_dynamic_context(context)
        else:
            raise RuntimeError("Legacy orchestrator not initialized")

    async def orchestrate_multi_agent_interaction(
        self, participants: List[str], **kwargs
    ):
        """Orchestrate multi-agent interaction (legacy compatibility)."""
        if self.legacy_orchestrator:
            return await self.legacy_orchestrator.orchestrate_multi_agent_interaction(
                participants, **kwargs
            )
        else:
            raise RuntimeError("Legacy orchestrator not initialized")

    # Enhanced properties for legacy compatibility
    @property
    def subjective_reality_engine(self):
        """Get subjective reality engine (legacy compatibility)."""
        try:
            return self.get_service(SubjectiveRealityEngine)
        except Exception:
            return (
                self.legacy_orchestrator.subjective_reality_engine
                if self.legacy_orchestrator
                else None
            )

    @property
    def emergent_narrative_engine(self):
        """Get emergent narrative engine (legacy compatibility)."""
        try:
            return self.get_service(EmergentNarrativeEngine)
        except Exception:
            return (
                self.legacy_orchestrator.emergent_narrative_engine
                if self.legacy_orchestrator
                else None
            )
