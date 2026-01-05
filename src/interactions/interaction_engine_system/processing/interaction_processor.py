"""
Interaction Processor
====================

Core interaction processing engine with phase management, orchestration, and context handling.
Coordinates interaction execution through structured phases with validation and monitoring.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionOutcome,
    InteractionPhase,
    InteractionType,
)

# Import enhanced core systems used in responses
try:
    from src.core.data_models import ErrorInfo, StandardResponse
except ImportError:
    # Fallback for testing
    class StandardResponse:
        def __init__(self, success=True, data=None, error=None, metadata=None):
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}

        def get(self, key, default=None):
            return getattr(self, key, default)

        def __getitem__(self, key):
            return getattr(self, key)

    class ErrorInfo:
        def __init__(self, code="", message="", recoverable=True):
            self.code = code
            self.message = message
            self.recoverable = recoverable

__all__ = ["InteractionProcessor"]


class InteractionProcessor:
    """
    Core Interaction Processing and Phase Management System

    Responsibilities:
    - Execute interaction processing through structured phases
    - Coordinate phase transitions and dependencies
    - Monitor processing progress and performance
    - Handle phase validation and error recovery
    - Manage processing timeouts and resource allocation
    """

    def __init__(
        self,
        config: InteractionEngineConfig,
        memory_manager: Optional[Any] = None,
        character_manager: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize interaction processor.

        Args:
            config: Interaction engine configuration
            memory_manager: Optional memory manager instance
            character_manager: Optional character manager instance
            logger: Optional logger instance
        """
        self.config = config
        self.memory_manager = memory_manager
        self.character_manager = character_manager
        self.logger = logger or logging.getLogger(__name__)

        # Processing state
        self.active_interactions = {}
        self.phase_processors = {}
        self.processing_stats = {
            "total_processed": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "average_processing_time": 0.0,
        }

        # Thread pool for parallel processing
        self.executor = (
            ThreadPoolExecutor(max_workers=self.config.max_concurrent_interactions)
            if self.config.enable_parallel_processing
            else None
        )

        # Phase type definitions
        self._standard_phases = {
            "initialization": {
                "description": "Initialize interaction context and participants",
                "required": True,
                "timeout": 30.0,
            },
            "validation": {
                "description": "Validate context and prerequisites",
                "required": True,
                "timeout": 15.0,
            },
            "preparation": {
                "description": "Prepare resources and participant states",
                "required": False,
                "timeout": 60.0,
            },
            "execution": {
                "description": "Execute main interaction processing",
                "required": True,
                "timeout": self.config.phase_timeout_seconds,
            },
            "state_update": {
                "description": "Update participant and environment states",
                "required": True,
                "timeout": 30.0,
            },
            "memory_processing": {
                "description": "Generate and store memory items",
                "required": self.config.memory_integration_enabled,
                "timeout": 45.0,
            },
            "finalization": {
                "description": "Finalize interaction and cleanup",
                "required": True,
                "timeout": 15.0,
            },
        }

        self.logger.info("Interaction processor initialized")

    async def process_interaction(
        self, context: InteractionContext
    ) -> InteractionOutcome:
        """
        Process a complete interaction through all phases.

        Args:
            context: Interaction context to process

        Returns:
            InteractionOutcome with complete processing results
        """
        start_time = datetime.now()
        processing_id = f"{context.interaction_id}_{int(start_time.timestamp())}"

        try:
            self.logger.info(
                f"Starting interaction processing: {context.interaction_id}"
            )
            self.active_interactions[processing_id] = {
                "context": context,
                "start_time": start_time,
                "current_phase": None,
                "status": "active",
            }

            # Generate processing phases
            phases = self._generate_processing_phases(context)

            # Initialize outcome
            outcome = InteractionOutcome(
                interaction_id=context.interaction_id,
                context=context,
                completion_time=start_time,
            )

            # Process phases sequentially
            for phase in phases:
                phase_result = await self._process_phase(processing_id, phase, outcome)

                if not phase_result.success:
                    # Handle phase failure
                    outcome.success = False
                    outcome.failed_phases.append(phase.phase_id)
                    outcome.errors.append(
                        f"Phase {phase.phase_id} failed: {phase_result.error.message if phase_result.error else 'Unknown error'}"
                    )

                    # Check if failure is recoverable
                    if not phase_result.error or not phase_result.error.recoverable:
                        self.logger.error(
                            f"Non-recoverable failure in phase {phase.phase_id}"
                        )
                        break

                    # Attempt recovery
                    if not await self._attempt_phase_recovery(
                        processing_id, phase, outcome
                    ):
                        outcome.success = False
                        break
                else:
                    outcome.completed_phases.append(phase.phase_id)

            # Calculate processing metrics
            end_time = datetime.now()
            outcome.completion_time = end_time
            outcome.processing_duration = (end_time - start_time).total_seconds()

            # Update processing statistics
            self._update_processing_stats(outcome)

            # Cleanup
            self.active_interactions.pop(processing_id, None)

            self.logger.info(
                f"Interaction processing completed: {context.interaction_id} (success: {outcome.success})"
            )
            return outcome

        except Exception as e:
            self.logger.error(f"Critical error in interaction processing: {e}")

            # Create error outcome
            outcome = InteractionOutcome(
                interaction_id=context.interaction_id,
                context=context,
                success=False,
                completion_time=datetime.now(),
                processing_duration=(datetime.now() - start_time).total_seconds(),
                errors=[f"Critical processing error: {str(e)}"],
            )

            # Cleanup
            self.active_interactions.pop(processing_id, None)

            return outcome

    async def process_interaction_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """
        Process a single interaction phase.

        Args:
            context: Interaction context
            phase: Phase to process

        Returns:
            StandardResponse with phase processing results
        """
        try:
            self.logger.debug(f"Processing phase: {phase.phase_id}")

            # Validate phase prerequisites
            if phase.prerequisites:
                prereq_result = await self._validate_phase_prerequisites(context, phase)
                if not prereq_result.success:
                    return prereq_result

            # Execute phase processing
            phase_result = await self._execute_phase_processing(context, phase)

            if phase_result.success:
                # Update phase completion status
                phase.completion_status = "completed"
                self.logger.debug(f"Phase {phase.phase_id} completed successfully")
            else:
                phase.completion_status = "failed"
                self.logger.warning(
                    f"Phase {phase.phase_id} failed: {phase_result.error}"
                )

            return phase_result

        except Exception as e:
            self.logger.error(f"Error processing phase {phase.phase_id}: {e}")
            phase.completion_status = "failed"

            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PHASE_PROCESSING_ERROR",
                    message=f"Phase processing failed: {str(e)}",
                    recoverable=True,
                ),
            )

    def get_processing_status(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current processing status for an interaction.

        Args:
            interaction_id: ID of interaction to check

        Returns:
            Dict with processing status or None if not found
        """
        for processing_id, info in self.active_interactions.items():
            if info["context"].interaction_id == interaction_id:
                return {
                    "processing_id": processing_id,
                    "start_time": info["start_time"],
                    "current_phase": info["current_phase"],
                    "status": info["status"],
                    "duration": (datetime.now() - info["start_time"]).total_seconds(),
                }

        return None

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        Get processing performance statistics.

        Returns:
            Dict with processing statistics
        """
        return {
            **self.processing_stats,
            "active_interactions": len(self.active_interactions),
            "phase_processors": list(self.phase_processors.keys()),
        }

    async def cancel_interaction(self, interaction_id: str) -> bool:
        """
        Cancel an active interaction processing.

        Args:
            interaction_id: ID of interaction to cancel

        Returns:
            True if cancellation successful, False otherwise
        """
        for processing_id, info in self.active_interactions.items():
            if info["context"].interaction_id == interaction_id:
                try:
                    info["status"] = "cancelled"
                    self.logger.info(f"Interaction cancelled: {interaction_id}")
                    return True
                except Exception as e:
                    self.logger.error(
                        f"Error cancelling interaction {interaction_id}: {e}"
                    )
                    return False

        return False

    # Private processing methods

    def _generate_processing_phases(
        self, context: InteractionContext
    ) -> List[InteractionPhase]:
        """Generate standard processing phases for interaction context."""
        phases = []
        sequence_order = 0

        for phase_name, phase_info in self._standard_phases.items():
            # Skip optional phases based on configuration
            if not phase_info["required"]:
                if (
                    phase_name == "memory_processing"
                    and not self.config.memory_integration_enabled
                ):
                    continue

            phase = InteractionPhase(
                phase_id=f"{context.interaction_id}_{phase_name}",
                phase_name=phase_name,
                description=phase_info["description"],
                sequence_order=sequence_order,
                expected_duration=phase_info["timeout"],
                completion_status="pending",
            )

            # Add context-specific objectives
            if phase_name == "execution":
                phase.objectives = self._generate_execution_objectives(context)
            elif phase_name == "state_update":
                phase.objectives = [
                    "Update participant states",
                    "Apply environment changes",
                ]
            elif phase_name == "memory_processing":
                phase.objectives = ["Generate memories", "Update relationships"]

            phases.append(phase)
            sequence_order += 1

        return phases

    async def _process_phase(
        self, processing_id: str, phase: InteractionPhase, outcome: InteractionOutcome
    ) -> StandardResponse:
        """Process a single phase with timeout and monitoring."""
        try:
            # Update processing state
            if processing_id in self.active_interactions:
                self.active_interactions[processing_id][
                    "current_phase"
                ] = phase.phase_name

            # Set phase to active
            phase.completion_status = "active"

            # Process phase with timeout
            timeout = phase.expected_duration or self.config.phase_timeout_seconds

            try:
                phase_result = await asyncio.wait_for(
                    self.process_interaction_phase(outcome.context, phase),
                    timeout=timeout,
                )

                return phase_result

            except asyncio.TimeoutError:
                self.logger.warning(
                    f"Phase {phase.phase_id} timed out after {timeout} seconds"
                )
                phase.completion_status = "failed"

                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="PHASE_TIMEOUT",
                        message=f"Phase timed out after {timeout} seconds",
                        recoverable=True,
                    ),
                )

        except Exception as e:
            self.logger.error(f"Error in phase processing: {e}")
            phase.completion_status = "failed"

            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PHASE_ERROR",
                    message=f"Phase processing error: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _execute_phase_processing(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Execute the actual phase processing logic."""
        try:
            phase_name = phase.phase_name

            if phase_name == "initialization":
                return await self._process_initialization_phase(context, phase)
            elif phase_name == "validation":
                return await self._process_validation_phase(context, phase)
            elif phase_name == "preparation":
                return await self._process_preparation_phase(context, phase)
            elif phase_name == "execution":
                return await self._process_execution_phase(context, phase)
            elif phase_name == "state_update":
                return await self._process_state_update_phase(context, phase)
            elif phase_name == "memory_processing":
                return await self._process_memory_phase(context, phase)
            elif phase_name == "finalization":
                return await self._process_finalization_phase(context, phase)
            else:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="UNKNOWN_PHASE",
                        message=f"Unknown phase type: {phase_name}",
                        recoverable=False,
                    ),
                )

        except Exception as e:
            self.logger.error(f"Phase execution failed: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PHASE_EXECUTION_ERROR",
                    message=f"Phase execution failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _validate_phase_prerequisites(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Validate phase prerequisites."""
        try:
            for prerequisite in phase.prerequisites:
                # Simple prerequisite validation - extend as needed
                if prerequisite.startswith("phase_"):
                    # Check if required phase was completed
                    prerequisite.replace("phase_", "")
                    # In real implementation, track completed phases
                    continue
                elif prerequisite.startswith("resource_"):
                    # Check resource availability
                    continue
                elif prerequisite.startswith("state_"):
                    # Check participant state requirements
                    continue

            return StandardResponse(
                success=True, data={"prerequisites_validated": len(phase.prerequisites)}
            )

        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="PREREQUISITE_VALIDATION_FAILED",
                    message=f"Prerequisite validation failed: {str(e)}",
                    recoverable=True,
                ),
            )

    async def _attempt_phase_recovery(
        self, processing_id: str, phase: InteractionPhase, outcome: InteractionOutcome
    ) -> bool:
        """Attempt to recover from phase failure."""
        try:
            self.logger.info(f"Attempting recovery for phase: {phase.phase_id}")

            # Simple recovery strategies
            if phase.phase_name in ["preparation", "memory_processing"]:
                # These phases can often be retried
                retry_result = await self._process_phase(processing_id, phase, outcome)
                if retry_result.success:
                    self.logger.info(f"Phase recovery successful: {phase.phase_id}")
                    return True

            # More complex recovery logic would go here
            return False

        except Exception as e:
            self.logger.error(f"Phase recovery failed: {e}")
            return False

    def _generate_execution_objectives(self, context: InteractionContext) -> List[str]:
        """Generate context-specific execution objectives."""
        objectives = []

        if context.interaction_type == InteractionType.DIALOGUE:
            objectives = ["Generate dialogue content", "Process conversational flow"]
        elif context.interaction_type == InteractionType.COMBAT:
            objectives = ["Process combat actions", "Calculate damage and effects"]
        elif context.interaction_type == InteractionType.COOPERATION:
            objectives = ["Coordinate collaborative actions", "Track shared objectives"]
        elif context.interaction_type == InteractionType.NEGOTIATION:
            objectives = ["Process negotiation terms", "Track agreement progress"]
        else:
            objectives = ["Execute interaction-specific processing"]

        return objectives

    def _update_processing_stats(self, outcome: InteractionOutcome):
        """Update processing performance statistics."""
        self.processing_stats["total_processed"] += 1

        if outcome.success:
            self.processing_stats["successful_interactions"] += 1
        else:
            self.processing_stats["failed_interactions"] += 1

        # Update average processing time
        total_time = (
            self.processing_stats["average_processing_time"]
            * (self.processing_stats["total_processed"] - 1)
        ) + outcome.processing_duration

        self.processing_stats["average_processing_time"] = (
            total_time / self.processing_stats["total_processed"]
        )

    # Phase processing implementations

    async def _process_initialization_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process initialization phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "initialization", "initialized": True},
                metadata={"blessing": "initialization_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "INIT_FAILED", f"Initialization failed: {str(e)}", True
                ),
            )

    async def _process_validation_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process validation phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "validation", "validated": True},
                metadata={"blessing": "validation_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "VALIDATION_FAILED", f"Validation failed: {str(e)}", True
                ),
            )

    async def _process_preparation_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process preparation phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "preparation", "prepared": True},
                metadata={"blessing": "preparation_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo("PREP_FAILED", f"Preparation failed: {str(e)}", True),
            )

    async def _process_execution_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process main execution phase."""
        try:
            # This would contain the main interaction processing logic
            execution_data = {
                "phase": "execution",
                "interaction_type": context.interaction_type.value,
                "participants": context.participants,
                "executed": True,
            }

            return StandardResponse(
                success=True,
                data=execution_data,
                metadata={"blessing": "execution_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "EXECUTION_FAILED", f"Execution failed: {str(e)}", True
                ),
            )

    async def _process_state_update_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process state update phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "state_update", "states_updated": True},
                metadata={"blessing": "state_update_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "STATE_UPDATE_FAILED", f"State update failed: {str(e)}", True
                ),
            )

    async def _process_memory_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process memory generation phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "memory_processing", "memories_generated": True},
                metadata={"blessing": "memory_processing_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "MEMORY_FAILED", f"Memory processing failed: {str(e)}", True
                ),
            )

    async def _process_finalization_phase(
        self, context: InteractionContext, phase: InteractionPhase
    ) -> StandardResponse:
        """Process finalization phase."""
        try:
            return StandardResponse(
                success=True,
                data={"phase": "finalization", "finalized": True},
                metadata={"blessing": "finalization_complete"},
            )
        except Exception as e:
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    "FINALIZATION_FAILED", f"Finalization failed: {str(e)}", True
                ),
            )

    def __del__(self):
        """Cleanup resources on destruction."""
        if self.executor:
            self.executor.shutdown(wait=True)
