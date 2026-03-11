# mypy: ignore-errors

"""
Modular Interaction Engine - Main Facade
========================================

Unified interface for the modular interaction engine system maintaining
backward compatibility while providing enhanced enterprise-grade functionality.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, cast

import structlog

# Import modular components
from .core.types import (
    InteractionEngineConfig,
    InteractionOutcome,
)
from .processing.interaction_processor import InteractionProcessor
from .queue_management.queue_manager import QueueManager
from .state_management.state_manager import StateManager
from .type_processors.interaction_type_processors import InteractionTypeProcessorManager
from .validation.interaction_validator import InteractionValidator

# Import enhanced core systems used in responses
try:
    from src.core.data_models import ErrorInfo, StandardResponse
except ImportError:
    # Fallback for testing
    class StandardResponse:  # type: ignore[no-redef]
        def __init__(
            self,
            success: bool = True,
            data: Any = None,
            error: Any = None,
            metadata: Any = None,
        ) -> None:
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}

        def get(self, key: Any, default: Any = None) -> Any:
            return getattr(self, key, default)

        def __getitem__(self, key: Any) -> Any:
            return getattr(self, key)

    class ErrorInfo:  # type: ignore[no-redef]
        def __init__(
            self, code: str = "", message: str = "", recoverable: bool = True
        ) -> None:
            self.code = code
            self.message = message
            self.recoverable = recoverable


__all__ = [
    "InteractionEngine",
    "create_interaction_engine",
    "create_performance_optimized_config",
]


class InteractionEngine:
    """
    Modular Interaction Engine - Main Facade

    Enterprise-grade interaction processing engine with comprehensive
    character interaction capabilities, state management, and extensible
    architecture.

    Features:
    - Multi-type interaction processing (dialogue, combat, cooperation, etc.)
    - Comprehensive validation and prerequisite checking
    - Advanced state management and memory integration
    - Priority-based queue management and scheduling
    - Performance monitoring and detailed logging
    - Backward compatibility with original interface
    """

    def __init__(
        self,
        config: Any = None,
        memory_manager: Any = None,
        character_manager: Any = None,
        equipment_manager: Any = None,
        logger: Any = None,
    ) -> None:
        """Initialize modular interaction engine."""
        self.config = config or InteractionEngineConfig()
        self.memory_manager = memory_manager
        self.character_manager = character_manager
        self.equipment_manager = equipment_manager
        self.logger = logger or structlog.get_logger(__name__)

        # Initialize modular components
        self.validator = InteractionValidator(self.config, self.logger)
        self.processor = InteractionProcessor(
            self.config, self.memory_manager, self.character_manager, self.logger
        )
        self.type_processors = InteractionTypeProcessorManager(self.config, self.logger)
        self.state_manager = StateManager(
            self.config, self.memory_manager, self.character_manager, self.logger
        )
        self.queue_manager = QueueManager(self.config, self.logger)

        # Engine state
        self.is_initialized = False
        self.processing_active = False

        # Statistics tracking
        self.engine_stats = {
            "total_interactions_processed": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "average_processing_time": 0.0,
            "startup_time": datetime.now(),
            "uptime_seconds": 0.0,
        }

        # Initialize engine
        asyncio.create_task(self._initialize_engine())

        self.logger.info("Modular interaction engine initialized")

    async def _initialize_engine(self) -> None:
        """Initialize engine components."""
        try:
            # Start queue processing
            await self.queue_manager.start_queue_processing()

            self.is_initialized = True
            self.processing_active = True

            self.logger.info("Interaction engine initialization completed")

        except Exception as e:
            self.logger.error(f"Engine initialization failed: {e}")

    async def process_interaction(
        self, context: Any, async_processing: bool = False
    ) -> Any:
        """Process a complete interaction through the modular engine."""
        try:
            if not self.is_initialized:
                await self._initialize_engine()

            self.logger.info(f"Processing interaction: {context.interaction_id}")

            if async_processing:
                return await self._queue_interaction(context)
            else:
                return await self._process_interaction_sync(context)

        except Exception as e:
            self.logger.error(f"Interaction processing failed: {e}")
            return InteractionOutcome(
                interaction_id=context.interaction_id,
                context=context,
                success=False,
                errors=[f"Processing failed: {str(e)}"],
            )

    async def _process_interaction_sync(self, context: Any) -> Any:
        """Process interaction synchronously through all phases."""
        processing_start = datetime.now()

        try:
            # Phase 1: Validation
            validation_result = await self.validator.validate_interaction_context(
                context
            )
            if not validation_result.success:
                return InteractionOutcome(
                    interaction_id=context.interaction_id,
                    context=context,
                    success=False,
                    errors=[
                        f"Validation failed: {validation_result.error.message if validation_result.error else 'Unknown error'}"
                    ],
                )

            # Phase 2: Type-specific processing
            type_processing_result = await self.type_processors.process_interaction(
                context
            )
            if not type_processing_result.success:
                return InteractionOutcome(
                    interaction_id=context.interaction_id,
                    context=context,
                    success=False,
                    errors=[
                        f"Type processing failed: {type_processing_result.error.message if type_processing_result.error else 'Unknown error'}"
                    ],
                )

            # Phase 3: State updates
            if (
                hasattr(self.config, "memory_integration_enabled")
                and self.config.memory_integration_enabled
            ):
                state_result = await self.state_manager.update_interaction_states(
                    context, type_processing_result.data or {}
                )
                if not state_result.success:
                    self.logger.warning(f"State update failed: {state_result.error}")

            # Create successful outcome
            processing_time = (datetime.now() - processing_start).total_seconds()

            outcome = InteractionOutcome(
                interaction_id=context.interaction_id,
                context=context,
                success=True,
                processing_duration=processing_time,
                interaction_content=type_processing_result.data or {},
                completed_phases=["validation", "processing", "state_update"],
            )

            # Update engine statistics
            self._update_engine_stats(True, processing_time)

            self.logger.info(
                f"Interaction completed successfully: {context.interaction_id} ({processing_time:.2f}s)"
            )

            return outcome

        except Exception as e:
            processing_time = (datetime.now() - processing_start).total_seconds()
            self._update_engine_stats(False, processing_time)

            self.logger.error(f"Synchronous processing failed: {e}")

            return InteractionOutcome(
                interaction_id=context.interaction_id,
                context=context,
                success=False,
                processing_duration=processing_time,
                errors=[f"Processing exception: {str(e)}"],
            )

    async def _queue_interaction(self, context: Any) -> Any:
        """Queue interaction for asynchronous processing."""
        try:
            return await self.queue_manager.queue_interaction(context)
        except Exception as e:
            self.logger.error(f"Failed to queue interaction: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUEUE_FAILED",
                    message=f"Failed to queue interaction: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_engine_status(self) -> Dict[str, Any]:
        """Get comprehensive engine status."""
        current_time = datetime.now()
        startup_time = cast(datetime, self.engine_stats.get("startup_time", current_time))
        uptime = (current_time - startup_time).total_seconds()

        return {
            "engine_status": {
                "initialized": self.is_initialized,
                "processing_active": self.processing_active,
                "uptime_seconds": uptime,
                **self.engine_stats,
            },
            "queue_status": self.queue_manager.get_queue_status(),
            "processor_statistics": self.type_processors.get_processor_statistics(),
            "state_manager_stats": self.state_manager.get_state_statistics(),
            "supported_interaction_types": [
                t.value for t in self.type_processors.get_supported_types()
            ],
        }

    async def shutdown_engine(self) -> StandardResponse:
        """Gracefully shutdown the engine."""
        try:
            self.logger.info("Shutting down interaction engine")

            # Stop queue processing
            await self.queue_manager.stop_queue_processing()

            # Clear any pending operations
            await self.queue_manager.clear_queue()

            self.processing_active = False
            self.is_initialized = False

            return StandardResponse(
                success=True,
                data={"status": "shutdown_complete"},
                metadata={"blessing": "engine_shutdown"},
            )

        except Exception as e:
            self.logger.error(f"Engine shutdown failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="SHUTDOWN_FAILED",
                    message=f"Engine shutdown failed: {str(e)}",
                    recoverable=False,
                ),
            )

    def validate_interaction_context(self, context: Any) -> Any:
        """Validate interaction context without processing."""
        try:
            return asyncio.run(self.validator.validate_interaction_context(context))
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="VALIDATION_ERROR",
                    message=f"Context validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def calculate_interaction_risk(self, context: Any) -> Any:
        """Calculate risk assessment for interaction."""
        try:
            return self.validator.calculate_risk_assessment(context)
        except Exception as e:
            return {"risk_score": 0.5, "risk_level": "Unknown", "error": str(e)}

    def _update_engine_stats(self, success: bool, processing_time: float) -> None:
        """Update engine processing statistics."""
        # Get current values with proper types
        total_processed: int = cast(int, self.engine_stats["total_interactions_processed"]) + 1
        successful: int = cast(int, self.engine_stats["successful_interactions"])
        failed: int = cast(int, self.engine_stats["failed_interactions"])
        current_avg: float = cast(float, self.engine_stats["average_processing_time"])

        self.engine_stats["total_interactions_processed"] = total_processed

        if success:
            self.engine_stats["successful_interactions"] = successful + 1
        else:
            self.engine_stats["failed_interactions"] = failed + 1

        # Update average processing time
        self.engine_stats["average_processing_time"] = (
            (current_avg * (total_processed - 1)) + processing_time
        ) / total_processed


def create_interaction_engine(
    config: Any = None,
    memory_manager: Any = None,
    character_manager: Any = None,
    equipment_manager: Any = None,
) -> Any:
    """Factory function to create interaction engine with optimal defaults."""
    if config is None:
        config = InteractionEngineConfig(
            max_concurrent_interactions=3,
            enable_parallel_processing=True,
            memory_integration_enabled=True,
            auto_generate_memories=True,
            performance_monitoring=True,
            detailed_logging=True,
        )

    return InteractionEngine(
        config=config,
        memory_manager=memory_manager,
        character_manager=character_manager,
        equipment_manager=equipment_manager,
    )


def create_performance_optimized_config() -> InteractionEngineConfig:
    """Create performance-optimized configuration."""
    return InteractionEngineConfig(
        max_concurrent_interactions=5,
        default_timeout_seconds=180.0,
        enable_parallel_processing=True,
        max_queue_size=200,
        priority_processing=True,
        auto_queue_cleanup=True,
        performance_monitoring=True,
        detailed_logging=False,
        memory_integration_enabled=True,
        auto_generate_memories=True,
    )
