#!/usr/bin/env python3
"""
System Orchestrator for Novel Engine
===================================

Unified system orchestrator that coordinates all components
of the dynamic context engineering framework and provides comprehensive
API for intelligent agent interactions.

Architecture Reference: Dynamic Context Engineering - Master Orchestrator
Development Phase: System Integration (S001)
Author: Novel Engine Development Team
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import data models
from src.core.data_models import (
    CharacterState,
    DynamicContext,
    ErrorInfo,
    MemoryItem,
    MemoryType,
    StandardResponse,
)
from src.core.emergent_narrative import EmergentNarrativeEngine

# Import core narrative engines
from src.core.subjective_reality import SubjectiveRealityEngine

# Import database access
from src.database.context_db import ContextDatabase
from src.interactions.character_interaction_processor import (
    CharacterInteractionProcessor,
)
from src.interactions.dynamic_equipment_system import DynamicEquipmentSystem
from src.interactions.interaction_engine import (
    InteractionContext,
    InteractionEngine,
    InteractionType,
)

# Import all subsystems
from src.memory.layered_memory import LayeredMemorySystem
from src.memory.memory_query_engine import MemoryQueryEngine
from src.templates.character_template_manager import (
    CharacterTemplateManager,
)
from src.templates.dynamic_template_engine import (
    DynamicTemplateEngine,
    TemplateContext,
)

# Comprehensive logging and monitoring
logger = logging.getLogger(__name__)


class OrchestratorMode(Enum):
    """Orchestrator Operational Modes"""

    AUTONOMOUS = "autonomous"  # Full autonomous operation
    INTERACTIVE = "interactive"  # Human-guided interactions
    SIMULATION = "simulation"  # Simulation mode for testing
    DEVELOPMENT = "development"  # Development and debugging mode
    PRODUCTION = "production"  # Production deployment mode


class SystemHealth(Enum):
    """System Health Status States"""

    OPTIMAL = "optimal"  # All systems functioning perfectly
    DEGRADED = "degraded"  # Some systems experiencing issues
    CRITICAL = "critical"  # Critical systems failing
    EMERGENCY = "emergency"  # Emergency shutdown required
    MAINTENANCE = "maintenance"  # Scheduled maintenance mode


@dataclass
class OrchestratorConfig:
    """
    Orchestrator Configuration Parameters

    Comprehensive configuration for system orchestrator with performance
    tuning, operational modes, and system integration parameters.
    """

    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10
    memory_cleanup_interval: int = 3600  # seconds
    template_cache_size: int = 100
    interaction_queue_size: int = 50
    equipment_maintenance_interval: int = 1800  # seconds
    relationship_decay_interval: int = 86400  # seconds (daily)
    health_check_interval: int = 300  # seconds
    auto_save_interval: int = 600  # seconds
    debug_logging: bool = False
    enable_metrics: bool = True
    enable_auto_backup: bool = True
    backup_interval: int = 7200  # seconds
    max_memory_items_per_agent: int = 10000
    max_interaction_history: int = 1000
    enable_cross_system_validation: bool = True
    performance_monitoring: bool = True


@dataclass
class SystemMetrics:
    """
    System Performance Metrics

    Comprehensive system performance and health metrics for monitoring
    and optimization of the dynamic context engineering framework.
    """

    timestamp: datetime = field(default_factory=datetime.now)
    active_agents: int = 0
    total_memory_items: int = 0
    active_interactions: int = 0
    template_cache_hits: float = 0.0
    average_response_time: float = 0.0
    system_health: SystemHealth = SystemHealth.OPTIMAL
    database_connections: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    error_rate: float = 0.0
    last_backup: Optional[datetime] = None
    uptime_seconds: int = 0
    operations_per_minute: float = 0.0
    relationship_count: int = 0
    equipment_count: int = 0


class SystemOrchestrator:
    """
    System Orchestrator - Unified Coordination

    Holy master orchestrator that coordinates all subsystems of the dynamic
    context engineering framework, providing unified API, system health monitoring,
    performance optimization, and comprehensive agent lifecycle management
    enhanced by the System's integrative wisdom.

    CAPABILITIES:
    - Unified system lifecycle management
    - Cross-system data consistency and validation
    - Performance monitoring and optimization
    - Automatic system health checks and recovery
    - Comprehensive agent state management
    - Dynamic context orchestration and evolution
    - Intelligent resource allocation and load balancing
    - Real-time system metrics and diagnostics
    - Automated backup and recovery systems
    - Development and production mode support
    """

    def __init__(
        self,
        database_path: str = "data/context_engineering.db",
        config: Optional[OrchestratorConfig] = None,
        event_bus=None,
        database=None,
    ):
        """
        System Initialization with Comprehensive Integration

        Initialize the system orchestrator with all enhanced subsystems
        and comprehensive monitoring capabilities.
        """
        self.config = config or OrchestratorConfig()
        self.database_path = database_path
        self.startup_time = datetime.now()
        self.system_health = SystemHealth.OPTIMAL
        self.active_agents: Dict[str, datetime] = {}
        self.operation_count = 0
        self.error_count = 0

        # Initialize enhanced database (use provided database or create new one)
        self.database = (
            database if database is not None else ContextDatabase(database_path)
        )

        # Initialize event bus (use provided or create default)
        self.event_bus = event_bus

        # Initialize core systems (will be set up in startup)
        self.memory_system: Optional[LayeredMemorySystem] = None
        self.memory_query_engine: Optional[MemoryQueryEngine] = None
        self.template_engine: Optional[DynamicTemplateEngine] = None
        self.character_manager: Optional[CharacterTemplateManager] = None
        self.interaction_engine: Optional[InteractionEngine] = None
        self.equipment_system: Optional[DynamicEquipmentSystem] = None
        self.character_processor: Optional[CharacterInteractionProcessor] = None

        # Initialize narrative engines (will be set up in startup)
        self.subjective_reality_engine: Optional[SubjectiveRealityEngine] = None
        self.emergent_narrative_engine: Optional[EmergentNarrativeEngine] = None

        # System monitoring
        self.metrics_history: List[SystemMetrics] = []
        self.last_health_check = datetime.now()
        self.last_cleanup = datetime.now()
        self.last_backup = None

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_requested = False

        logger.info("System Orchestrator initialized and ready")

    async def startup(self) -> StandardResponse:
        """
        System Startup with Comprehensive Initialization

        Initialize all subsystems, establish connections, and begin
        background monitoring and maintenance tasks.
        """
        try:
            logger.info("Initiating System Orchestrator startup sequence")

            # Initialize database and verify schema
            startup_result = await self.database.initialize_standard_temple()
            if not startup_result.success:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="DATABASE_INIT_FAILED",
                        message="Database initialization failed",
                        details={
                            "database_error": str(
                                startup_result.error.message
                                if startup_result.error
                                else "Unknown error"
                            )
                        },
                    ),
                )

            # Initialize memory systems
            self.memory_system = LayeredMemorySystem(
                "system_orchestrator", self.database
            )
            self.memory_query_engine = MemoryQueryEngine(
                self.database, self.memory_system
            )

            # Initialize template systems
            self.template_engine = DynamicTemplateEngine(
                template_directory=str(Path("src/templates")),
                query_engine=self.memory_query_engine,
            )
            self.character_manager = CharacterTemplateManager(
                self.database, self.template_engine
            )

            # Initialize interaction systems
            # Import context renderer for interaction engine
            from src.templates.context_renderer import ContextRenderer

            context_renderer = ContextRenderer(
                self.template_engine, self.memory_query_engine
            )

            self.interaction_engine = InteractionEngine(
                memory_system=self.memory_system,
                template_manager=self.character_manager,
                context_renderer=context_renderer,
                database=self.database,
            )
            self.equipment_system = DynamicEquipmentSystem(
                database=self.database,
                equipment_templates_dir="src/templates/equipment",
            )
            self.character_processor = CharacterInteractionProcessor(
                self.database,
                self.interaction_engine,
                self.equipment_system,
                self.memory_system,
                self.template_engine,
                self.character_manager,
            )

            # Initialize narrative engines
            logger.info("Initializing narrative engines")
            self.subjective_reality_engine = SubjectiveRealityEngine()
            self.emergent_narrative_engine = EmergentNarrativeEngine()

            # Initialize narrative engines
            await self.subjective_reality_engine.initialize()
            await self.emergent_narrative_engine.initialize()

            logger.info("Narrative engines initialized successfully")

            # Start background tasks
            await self._start_background_tasks()

            # Perform initial health check
            health_result = await self._perform_health_check()

            # Update system health
            self.system_health = health_result.get(
                "system_health", SystemHealth.OPTIMAL
            )

            logger.info("System Orchestrator startup completed successfully")

            return StandardResponse(
                success=True,
                data={
                    "startup_time": self.startup_time,
                    "system_health": self.system_health.value,
                    "active_subsystems": 7,
                    "configuration": {
                        "mode": self.config.mode.value,
                        "max_concurrent_agents": self.config.max_concurrent_agents,
                        "debug_logging": self.config.debug_logging,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Critical error during startup: {str(e)}")
            self.system_health = SystemHealth.CRITICAL
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="ORCHESTRATOR_STARTUP_FAILED",
                    message="System orchestrator startup failed",
                    details={"exception": str(e)},
                ),
            )

    async def shutdown(self) -> StandardResponse:
        """
        System Shutdown with Graceful Termination

        Gracefully shutdown all systems, save state, and cleanup resources.
        """
        try:
            logger.info("Initiating System Orchestrator shutdown sequence")
            self._shutdown_requested = True

            # Stop background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            # Save final system state
            await self._save_system_state()

            # Perform final backup if enabled
            if self.config.enable_auto_backup:
                await self._perform_backup()

            # Shutdown narrative engines
            if self.subjective_reality_engine and hasattr(
                self.subjective_reality_engine, "cleanup"
            ):
                await self.subjective_reality_engine.cleanup()
            if self.emergent_narrative_engine and hasattr(
                self.emergent_narrative_engine, "cleanup"
            ):
                await self.emergent_narrative_engine.cleanup()

            # Shutdown database connections
            if self.database:
                await self.database.close_standard_temple()

            logger.info("System Orchestrator shutdown completed successfully")

            return StandardResponse(
                success=True,
                data={
                    "shutdown_time": datetime.now(),
                    "uptime_seconds": (
                        datetime.now() - self.startup_time
                    ).total_seconds(),
                    "total_operations": self.operation_count,
                    "final_health": self.system_health.value,
                },
            )

        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="ORCHESTRATOR_SHUTDOWN_ERROR",
                    message="System orchestrator shutdown failed",
                    details={"exception": str(e)},
                ),
            )

    async def create_agent_context(
        self, agent_id: str, initial_state: Optional[CharacterState] = None
    ) -> StandardResponse:
        """
        Agent Context Creation with Comprehensive Initialization

        Create a new agent with full context initialization including memory,
        character state, and system registration.
        """
        try:
            if agent_id in self.active_agents:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="AGENT_ALREADY_EXISTS",
                        message="Agent already exists",
                        details={"agent_id": agent_id},
                    ),
                )

            # Create character state if not provided
            if initial_state is None:
                initial_state = CharacterState(
                    agent_id=agent_id, name=agent_id, current_status="active"
                )

            # Register agent in database first to avoid foreign key constraint issues
            agent_registration = await self.database.register_enhanced_agent(
                agent_id=agent_id,
                character_name=(
                    initial_state.base_identity.name if initial_state else agent_id
                ),
                faction_data=(
                    [initial_state.base_identity.faction]
                    if initial_state
                    else ["Unknown"]
                ),
                personality_traits=(
                    initial_state.base_identity.personality_traits
                    if initial_state
                    else ["default"]
                ),
                core_beliefs=(
                    initial_state.base_identity.core_beliefs
                    if initial_state
                    else ["adaptive"]
                ),
            )

            if not agent_registration.success:
                logger.warning(
                    f"Agent registration failed for {agent_id}: {agent_registration.error.message if agent_registration.error else 'Unknown'}"
                )

            # Initialize agent memory system
            agent_memory = LayeredMemorySystem(agent_id, self.database)

            # Create initial memory items
            welcome_memory = MemoryItem(
                memory_id=f"init_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                agent_id=agent_id,
                memory_type=MemoryType.EPISODIC,
                content=f"Agent {agent_id} initialized in dynamic context engineering framework",
                emotional_weight=0.3,
                relevance_score=0.5,
                tags=["initialization", "system", "framework"],
            )

            await agent_memory.store_memory(welcome_memory)

            # Register agent in character manager - create a basic persona
            from src.templates.character_template_manager import (
                CharacterArchetype,
                CharacterPersona,
            )

            basic_persona = CharacterPersona(
                persona_id=agent_id,
                character_name=agent_id,
                character_archetype=CharacterArchetype.SURVIVOR,
                trait_profiles={},
                interaction_preferences={},
                current_emotional_range={},
            )
            character_result = await self.character_manager.create_persona(
                basic_persona
            )

            if not character_result.success:
                logger.warning(
                    f"Character template creation failed for {agent_id}: {character_result.message}"
                )

            # Register agent as active
            self.active_agents[agent_id] = datetime.now()

            self.operation_count += 1
            logger.info(f"Agent context created successfully for {agent_id}")

            return StandardResponse(
                success=True,
                data={
                    "agent_id": agent_id,
                    "initial_state": initial_state,
                    "memory_initialized": True,
                    "character_template": character_result.success,
                    "creation_time": datetime.now(),
                },
            )

        except Exception as e:
            logger.error(f"Error creating agent context for {agent_id}: {str(e)}")
            self.error_count += 1
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="AGENT_CONTEXT_CREATION_FAILED",
                    message="Agent context creation failed",
                    details={"agent_id": agent_id, "exception": str(e)},
                ),
            )

    async def process_dynamic_context(
        self, context: DynamicContext
    ) -> StandardResponse:
        """
        Dynamic Context Processing with Comprehensive Orchestration

        Process a dynamic context through all relevant subsystems with
        cross-system coordination and state synchronization.
        """
        try:
            self.operation_count += 1

            # Validate agent exists
            if context.agent_id not in self.active_agents:
                agent_result = await self.create_agent_context(
                    context.agent_id, context.character_state
                )
                if not agent_result.success:
                    return agent_result

            # Update agent activity
            self.active_agents[context.agent_id] = datetime.now()

            # Process memory context if present
            memory_results = []
            if context.memory_context:
                for memory_item in context.memory_context:
                    memory_result = await self.memory_system.store_memory(memory_item)
                    memory_results.append(memory_result.success)

            # Process character state updates
            character_update_result = None
            if context.character_state:
                character_update_result = await self._update_character_state(
                    context.agent_id, context.character_state
                )

            # Process environmental context if present
            environmental_result = None
            if context.environmental_context:
                environmental_result = await self._process_environmental_context(
                    context.agent_id, context.environmental_context
                )

            # Generate dynamic response using templates
            template_context = TemplateContext(
                agent_id=context.agent_id,
                character_state=context.character_state,
                context_variables={
                    "processed_memories": len(memory_results),
                    "successful_memories": sum(memory_results),
                    "has_environmental_context": context.environmental_context
                    is not None,
                    "processing_timestamp": context.timestamp,
                },
            )

            template_result = await self.template_engine.render_template(
                "dynamic_context_response", template_context
            )

            logger.info(
                f"Dynamic context processed successfully for {context.agent_id}"
            )

            return StandardResponse(
                success=True,
                data={
                    "agent_id": context.agent_id,
                    "memories_processed": len(memory_results),
                    "memories_successful": sum(memory_results),
                    "character_updated": (
                        character_update_result.success
                        if character_update_result
                        else False
                    ),
                    "environmental_processed": (
                        environmental_result.success if environmental_result else False
                    ),
                    "template_generated": template_result.success,
                    "processing_time": datetime.now(),
                },
            )

        except Exception as e:
            logger.error(f"Error processing dynamic context: {str(e)}")
            self.error_count += 1
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="DYNAMIC_CONTEXT_PROCESSING_FAILED",
                    message="Dynamic context processing failed",
                    details={"agent_id": context.agent_id, "exception": str(e)},
                ),
            )

    async def orchestrate_multi_agent_interaction(
        self,
        participants: List[str],
        interaction_type: InteractionType = InteractionType.DIALOGUE,
        context: Optional[Dict[str, Any]] = None,
    ) -> StandardResponse:
        """
        Multi-Agent Interaction Orchestration

        Orchestrate complex multi-agent interactions with full system integration,
        relationship dynamics, and comprehensive state management.
        """
        try:
            # Validate all participants exist
            missing_agents = [
                agent for agent in participants if agent not in self.active_agents
            ]
            if missing_agents:
                # Create missing agents
                for agent_id in missing_agents:
                    create_result = await self.create_agent_context(agent_id)
                    if not create_result.success:
                        return create_result

            # Create interaction context
            interaction_context = InteractionContext(
                interaction_id=f"multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(participants)}p",
                interaction_type=interaction_type,
                participants=participants,
                metadata=context or {},
            )

            # Process through character interaction processor
            interaction_result = (
                await self.character_processor.process_character_interaction(
                    interaction_context, participants
                )
            )

            if interaction_result.success:
                # Update agent activity for all participants
                current_time = datetime.now()
                for participant in participants:
                    self.active_agents[participant] = current_time

                # Record interaction in emergent narrative engine
                await self._record_narrative_event(
                    interaction_context, interaction_result
                )

                # Log successful interaction
                logger.info(
                    f"Multi-agent interaction orchestrated successfully: {interaction_context.interaction_id}"
                )

            self.operation_count += 1
            return interaction_result

        except Exception as e:
            logger.error(f"Error in multi-agent interaction orchestration: {str(e)}")
            self.error_count += 1
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="MULTI_AGENT_INTERACTION_FAILED",
                    message="Multi-agent interaction failed",
                    details={"participants": participants, "exception": str(e)},
                ),
            )

    async def get_system_metrics(self) -> StandardResponse:
        """
        System Metrics Retrieval with Comprehensive Monitoring

        Retrieve comprehensive system performance and health metrics.
        """
        try:
            uptime = (datetime.now() - self.startup_time).total_seconds()
            operations_per_minute = (
                (self.operation_count / max(uptime / 60, 1)) if uptime > 0 else 0
            )
            error_rate = (
                (self.error_count / max(self.operation_count, 1))
                if self.operation_count > 0
                else 0
            )

            metrics = SystemMetrics(
                active_agents=len(self.active_agents),
                total_memory_items=await self._count_memory_items(),
                active_interactions=await self._count_active_interactions(),
                system_health=self.system_health,
                uptime_seconds=int(uptime),
                operations_per_minute=operations_per_minute,
                error_rate=error_rate,
                last_backup=self.last_backup,
                relationship_count=await self._count_relationships(),
                equipment_count=await self._count_equipment(),
            )

            self.metrics_history.append(metrics)

            # Keep only last 1000 metrics entries
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]

            return StandardResponse(
                success=True,
                data={
                    "current_metrics": metrics,
                    "metrics_history_count": len(self.metrics_history),
                    "system_configuration": {
                        "mode": self.config.mode.value,
                        "max_concurrent_agents": self.config.max_concurrent_agents,
                        "debug_logging": self.config.debug_logging,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error retrieving system metrics: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="METRICS_RETRIEVAL_FAILED",
                    message="Metrics retrieval failed",
                    details={"exception": str(e)},
                ),
            )

    # PRIVATE METHODS FOR INTERNAL OPERATIONS

    async def _start_background_tasks(self):
        """Start all background monitoring and maintenance tasks."""
        if self.config.enable_metrics:
            health_check_task = asyncio.create_task(self._health_check_loop())
            self._background_tasks.append(health_check_task)

        memory_cleanup_task = asyncio.create_task(self._memory_cleanup_loop())
        self._background_tasks.append(memory_cleanup_task)

        if self.config.enable_auto_backup:
            backup_task = asyncio.create_task(self._backup_loop())
            self._background_tasks.append(backup_task)

        logger.info(f"Started {len(self._background_tasks)} background tasks")

    async def _health_check_loop(self):
        """Background health check monitoring loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                if self._shutdown_requested:
                    break

                health_result = await self._perform_health_check()
                self.system_health = health_result.get(
                    "system_health", SystemHealth.OPTIMAL
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")
                self.system_health = SystemHealth.DEGRADED

    async def _memory_cleanup_loop(self):
        """Background memory cleanup and maintenance loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.memory_cleanup_interval)
                if self._shutdown_requested:
                    break

                await self._perform_memory_cleanup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory cleanup loop: {str(e)}")

    async def _backup_loop(self):
        """Background backup loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(self.config.backup_interval)
                if self._shutdown_requested:
                    break

                await self._perform_backup()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {str(e)}")

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check."""
        health_status = SystemHealth.OPTIMAL

        try:
            # Check database connectivity
            db_health = await self.database.health_check()
            if not db_health.get("healthy", False):
                health_status = SystemHealth.DEGRADED

            # Check memory system health
            active_agent_count = len(self.active_agents)
            if active_agent_count > self.config.max_concurrent_agents:
                health_status = SystemHealth.DEGRADED

            # Check error rate
            error_rate = (
                (self.error_count / max(self.operation_count, 1))
                if self.operation_count > 0
                else 0
            )
            if error_rate > 0.1:  # More than 10% error rate
                health_status = SystemHealth.CRITICAL
            elif error_rate > 0.05:  # More than 5% error rate
                health_status = SystemHealth.DEGRADED

            self.last_health_check = datetime.now()

            return {
                "system_health": health_status,
                "database_healthy": db_health.get("healthy", False),
                "active_agents": active_agent_count,
                "error_rate": error_rate,
                "check_time": self.last_health_check,
            }

        except Exception as e:
            logger.error(f"Error during health check: {str(e)}")
            return {"system_health": SystemHealth.CRITICAL, "error": str(e)}

    async def _perform_memory_cleanup(self):
        """Perform memory cleanup and optimization."""
        try:
            # Clean up inactive agents (inactive for more than 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            inactive_agents = [
                agent_id
                for agent_id, last_activity in self.active_agents.items()
                if last_activity < cutoff_time
            ]

            for agent_id in inactive_agents:
                # Archive agent data and remove from active list
                del self.active_agents[agent_id]
                logger.debug(f"Cleaned up inactive agent: {agent_id}")

            self.last_cleanup = datetime.now()
            logger.info(
                f"Memory cleanup completed, removed {len(inactive_agents)} inactive agents"
            )

        except Exception as e:
            logger.error(f"Error during memory cleanup: {str(e)}")

    async def _perform_backup(self):
        """Perform system state backup."""
        try:
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "active_agents": list(self.active_agents.keys()),
                "operation_count": self.operation_count,
                "system_health": self.system_health.value,
                "configuration": {
                    "mode": self.config.mode.value,
                    "max_concurrent_agents": self.config.max_concurrent_agents,
                },
            }

            backup_path = (
                Path("data")
                / "backups"
                / f"system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            with open(backup_path, "w") as f:
                json.dump(backup_data, f, indent=2)

            self.last_backup = datetime.now()
            logger.info(f"System backup completed: {backup_path}")

        except Exception as e:
            logger.error(f"Error during backup: {str(e)}")

    async def _save_system_state(self):
        """Save current system state to database."""
        try:
            state_data = {
                "shutdown_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.startup_time).total_seconds(),
                "total_operations": self.operation_count,
                "total_errors": self.error_count,
                "final_health": self.system_health.value,
                "active_agents_count": len(self.active_agents),
            }

            async with self.database.get_enhanced_connection() as conn:
                await conn.execute(
                    """INSERT OR REPLACE INTO system_state 
                       (state_id, state_data, timestamp) VALUES (?, ?, ?)""",
                    ("orchestrator_shutdown", json.dumps(state_data), datetime.now()),
                )
                await conn.commit()

            logger.info("System state saved successfully")

        except Exception as e:
            logger.error(f"ERROR saving system state: {str(e)}")

    async def _update_character_state(
        self, agent_id: str, character_state: CharacterState
    ) -> StandardResponse:
        """Update character state across relevant systems."""
        try:
            # Update in character manager
            update_result = await self.character_manager.update_character_state(
                agent_id, character_state
            )

            # Store state change as memory
            state_memory = MemoryItem(
                memory_id=f"state_update_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                agent_id=agent_id,
                memory_type=MemoryType.SEMANTIC,
                content="Character state updated: active",
                relevance_score=0.6,
                tags=["character_state", "system_update"],
            )

            await self.memory_system.store_memory(state_memory)

            return update_result

        except Exception as e:
            logger.error(f"ERROR updating character state for {agent_id}: {str(e)}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CHARACTER_STATE_UPDATE_FAILED",
                    message="Character state update failed",
                ),
            )

    async def _process_environmental_context(
        self, agent_id: str, env_context
    ) -> StandardResponse:
        """Process environmental context updates."""
        try:
            # Store environmental context as memory
            env_memory = MemoryItem(
                memory_id=f"env_context_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                agent_id=agent_id,
                memory_type=MemoryType.EPISODIC,
                content="Environmental context: unknown",
                relevance_score=0.5,
                tags=["environmental", "context_update"],
            )

            return await self.memory_system.store_memory(env_memory)

        except Exception as e:
            logger.error(
                f"ERROR processing environmental context for {agent_id}: {str(e)}"
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="ENVIRONMENTAL_CONTEXT_FAILED",
                    message="Environmental context processing failed",
                ),
            )

    async def _record_narrative_event(
        self,
        interaction_context: InteractionContext,
        interaction_result: StandardResponse,
    ) -> None:
        """Record interaction as narrative event in EmergentNarrativeEngine."""
        try:
            if not self.emergent_narrative_engine or not interaction_result.success:
                return

            # Create narrative event from interaction
            event_data = {
                "event_id": interaction_context.interaction_id,
                "event_type": (
                    interaction_context.interaction_type.value
                    if hasattr(interaction_context.interaction_type, "value")
                    else str(interaction_context.interaction_type)
                ),
                "participants": interaction_context.participants,
                "timestamp": datetime.now().isoformat(),
                "interaction_data": (
                    interaction_result.data if interaction_result.data else {}
                ),
                "metadata": interaction_context.metadata or {},
            }

            # Record event in causal graph
            await self.emergent_narrative_engine.causal_graph.add_event(event_data)

            # Check for causal relationships between participants
            for participant in interaction_context.participants:
                await self._analyze_agent_causal_relationships(participant, event_data)

            logger.debug(
                f"Recorded narrative event: {interaction_context.interaction_id}"
            )

        except Exception as e:
            logger.error(f"Failed to record narrative event: {e}")

    async def _analyze_agent_causal_relationships(
        self, agent_id: str, event_data: Dict[str, Any]
    ) -> None:
        """Analyze and record causal relationships for agent actions."""
        try:
            if not self.emergent_narrative_engine:
                return

            # Get recent events for this agent
            recent_events = (
                await self.emergent_narrative_engine.get_agent_recent_events(
                    agent_id, hours=1
                )
            )

            # Analyze potential causal relationships
            if len(recent_events) > 1:
                await self.emergent_narrative_engine.analyze_event_causality(
                    recent_events[-1], event_data
                )

        except Exception as e:
            logger.error(f"Failed to analyze causal relationships for {agent_id}: {e}")

    async def _count_memory_items(self) -> int:
        """Count total memory items in the system."""
        try:
            async with self.database.get_enhanced_connection() as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM memories")
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0

    async def _count_active_interactions(self) -> int:
        """Count active interactions."""
        return len(getattr(self.interaction_engine, "active_interactions", {}))

    async def _count_relationships(self) -> int:
        """Count relationships tracked by character processor."""
        return len(getattr(self.character_processor, "relationships", {}))

    async def _count_equipment(self) -> int:
        """Count total equipment items."""
        try:
            async with self.database.get_enhanced_connection() as conn:
                cursor = await conn.execute("SELECT COUNT(*) FROM equipment")
                result = await cursor.fetchone()
                return result[0] if result else 0
        except Exception:
            return 0


# Exported classes and functions
__all__ = [
    "SystemOrchestrator",
    "OrchestratorMode",
    "SystemHealth",
    "OrchestratorConfig",
    "SystemMetrics",
]
