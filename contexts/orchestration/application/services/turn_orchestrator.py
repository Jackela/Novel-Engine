#!/usr/bin/env python3
"""
Turn Orchestrator Service

Main orchestration service that coordinates the complete 5-phase turn pipeline
with saga patterns, comprehensive error handling, and performance monitoring.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from ...domain.entities import Turn
from ...domain.services import (
    EnhancedPerformanceTracker,
    PipelineOrchestrator,
    SagaCoordinator,
)
from ...domain.value_objects import (
    CompensationAction,
    PhaseType,
    TurnConfiguration,
    TurnId,
)
from ...infrastructure.monitoring import (
    NovelEngineTracingConfig,
    initialize_tracing,
)
from ...infrastructure.pipeline_phases import (
    BasePhaseImplementation,
    EventIntegrationPhase,
    InteractionOrchestrationPhase,
    NarrativeIntegrationPhase,
    PhaseExecutionContext,
    PhaseResult,
    SubjectiveBriefPhase,
    WorldUpdatePhase,
)

logger = logging.getLogger(__name__)


class TurnExecutionResult:
    """Comprehensive result of turn execution with all phase details."""

    def __init__(
        self,
        turn_id: TurnId,
        success: bool,
        execution_time_ms: float,
        phases_completed: List[PhaseType],
        phase_results: Dict[PhaseType, PhaseResult],
        compensation_actions: List[CompensationAction],
        performance_metrics: Dict[str, float],
        error_details: Optional[Dict[str, Any]] = None,
    ):
        self.turn_id = turn_id
        self.success = success
        self.execution_time_ms = execution_time_ms
        self.phases_completed = phases_completed
        self.phase_results = phase_results
        self.compensation_actions = compensation_actions
        self.performance_metrics = performance_metrics
        self.error_details = error_details
        self.completed_at = datetime.now()


class TurnOrchestrator:
    """
    Main turn orchestrator service implementing the complete 5-phase pipeline:

    1. World Update Phase - Update world state and advance time
    2. Subjective Brief Phase - Generate AI-powered agent perceptions
    3. Interaction Orchestration Phase - Coordinate agent interactions
    4. Event Integration Phase - Integrate interaction results into world
    5. Narrative Integration Phase - Create narrative content with AI

    Features:
    - Saga pattern with compensation for reliability
    - Comprehensive error handling and recovery
    - Performance monitoring and optimization
    - Configurable execution parameters
    - Cross-context integration with Novel Engine
    """

    def __init__(self, prometheus_collector=None):
        self.saga_coordinator = SagaCoordinator()
        self.pipeline_orchestrator = PipelineOrchestrator()

        # Initialize enhanced performance tracker with Prometheus integration
        self.performance_tracker = EnhancedPerformanceTracker(prometheus_collector)

        # Initialize distributed tracing
        tracing_config = NovelEngineTracingConfig(
            service_name="novel-engine-orchestration",
            service_version="2.0.0",
            environment="development",
            sampling_rate=0.5,  # 50% sampling for development
            enable_console_exporter=True,  # Enable console output for debugging
        )
        self.tracer = initialize_tracing(tracing_config)

        # Phase implementations
        self.phase_implementations: Dict[PhaseType, BasePhaseImplementation] = {
            PhaseType.WORLD_UPDATE: WorldUpdatePhase(),
            PhaseType.SUBJECTIVE_BRIEF: SubjectiveBriefPhase(),
            PhaseType.INTERACTION_ORCHESTRATION: InteractionOrchestrationPhase(),
            PhaseType.EVENT_INTEGRATION: EventIntegrationPhase(),
            PhaseType.NARRATIVE_INTEGRATION: NarrativeIntegrationPhase(),
        }

        # Configuration
        self.max_concurrent_turns = 3
        self.default_turn_timeout_ms = 120000  # 2 minutes
        self.saga_enabled = True
        self.performance_monitoring_enabled = True

    async def execute_turn(
        self,
        participants: List[str],
        configuration: Optional[TurnConfiguration] = None,
        turn_id: Optional[TurnId] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> TurnExecutionResult:
        """
        Execute complete turn pipeline with saga coordination and distributed tracing.

        Args:
            participants: List of participant agent IDs
            configuration: Turn configuration (uses defaults if None)
            turn_id: Optional turn ID (generates new if None)
            user_context: Optional user context for security tracing

        Returns:
            TurnExecutionResult with comprehensive execution details

        Raises:
            TurnExecutionError: If turn execution fails critically
        """
        # Initialize turn execution
        if not turn_id:
            turn_id = TurnId.generate()

        if not configuration:
            configuration = TurnConfiguration.create_default()

        logger.info(f"Starting turn execution for turn_id={turn_id}, participants={participants}")

        # Create turn entity
        turn = Turn.create(turn_id=turn_id, configuration=configuration, participants=participants)

        # Start root span for complete turn execution flow (M10 requirement)
        turn_span = None
        if self.tracer:
            turn_span = self.tracer.start_turn_span(
                turn_id=turn_id.turn_uuid,
                participants=participants,
                configuration={
                    "ai_integration_enabled": configuration.ai_integration_enabled,
                    "narrative_analysis_depth": configuration.narrative_analysis_depth,
                    "max_execution_time_ms": configuration.max_execution_time_ms,
                },
                user_context=user_context,
            )
            logger.debug(f"Started distributed tracing root span for turn {turn_id}")

        execution_start = datetime.now()
        phase_results: Dict[PhaseType, PhaseResult] = {}
        compensation_actions: List[CompensationAction] = []
        phases_completed: List[PhaseType] = []

        try:
            # Start performance monitoring
            if self.performance_monitoring_enabled:
                self.performance_tracker.start_turn_monitoring(turn_id)

            # Execute pipeline phases in sequence
            pipeline_phases = [
                PhaseType.WORLD_UPDATE,
                PhaseType.SUBJECTIVE_BRIEF,
                PhaseType.INTERACTION_ORCHESTRATION,
                PhaseType.EVENT_INTEGRATION,
                PhaseType.NARRATIVE_INTEGRATION,
            ]

            for phase_type in pipeline_phases:
                try:
                    logger.debug(f"Starting phase {phase_type.value} for turn {turn_id}")

                    # Execute phase with distributed tracing
                    phase_result = await self._execute_phase(
                        turn, phase_type, phase_results, turn_span
                    )

                    phase_results[phase_type] = phase_result
                    phases_completed.append(phase_type)

                    # Update turn state
                    turn.mark_phase_completed(phase_type, phase_result.success)

                    if not phase_result.success:
                        logger.warning(f"Phase {phase_type.value} failed for turn {turn_id}")

                        # Execute saga compensation if enabled
                        if self.saga_enabled:
                            compensation_result = await self._execute_saga_compensation(
                                turn, phases_completed, phase_results
                            )
                            compensation_actions.extend(compensation_result.compensation_actions)

                        # Fail fast or continue based on configuration
                        if configuration.fail_fast_on_phase_failure:
                            break

                    logger.debug(f"Completed phase {phase_type.value} for turn {turn_id}")

                except Exception as e:
                    logger.error(f"Phase {phase_type.value} exception for turn {turn_id}: {e}")

                    # Record phase failure
                    phase_results[phase_type] = self._create_phase_failure_result(
                        phase_type, str(e), turn
                    )

                    # Execute compensation
                    if self.saga_enabled:
                        compensation_result = await self._execute_saga_compensation(
                            turn, phases_completed, phase_results
                        )
                        compensation_actions.extend(compensation_result.compensation_actions)

                    if configuration.fail_fast_on_phase_failure:
                        break

            # Calculate execution metrics
            execution_time_ms = (datetime.now() - execution_start).total_seconds() * 1000

            # Determine overall success
            successful_phases = len([r for r in phase_results.values() if r.success])
            overall_success = successful_phases == len(pipeline_phases) and len(
                phases_completed
            ) == len(pipeline_phases)

            # Finalize turn state
            if overall_success:
                turn.mark_completed()
                logger.info(f"Turn {turn_id} completed successfully in {execution_time_ms:.1f}ms")
            else:
                turn.mark_failed(f"Completed {successful_phases}/{len(pipeline_phases)} phases")
                logger.warning(
                    f"Turn {turn_id} completed with failures in {execution_time_ms:.1f}ms"
                )

            # Gather performance metrics
            performance_metrics = await self._gather_performance_metrics(
                turn_id, phase_results, execution_time_ms
            )

            # Record turn execution results in distributed tracing span
            if self.tracer and turn_span:
                total_ai_cost = sum(
                    [
                        result.ai_usage.get("total_cost", 0) if result.ai_usage else 0
                        for result in phase_results.values()
                    ]
                )

                self.tracer.record_turn_result(
                    span=turn_span,
                    success=overall_success,
                    execution_time_seconds=execution_time_ms / 1000.0,
                    total_ai_cost=float(total_ai_cost),
                    phases_completed=[phase.value for phase in phases_completed],
                    error_details=None,
                )

                # Close the root span
                turn_span.end()
                logger.debug(f"Completed distributed tracing root span for turn {turn_id}")

            return TurnExecutionResult(
                turn_id=turn_id,
                success=overall_success,
                execution_time_ms=execution_time_ms,
                phases_completed=phases_completed,
                phase_results=phase_results,
                compensation_actions=compensation_actions,
                performance_metrics=performance_metrics,
            )

        except Exception as e:
            logger.error(f"Critical turn execution error for turn {turn_id}: {e}")

            # Record error in distributed tracing span
            if self.tracer and turn_span:
                execution_time_ms = (datetime.now() - execution_start).total_seconds() * 1000
                total_ai_cost = sum(
                    [
                        result.ai_usage.get("total_cost", 0) if result.ai_usage else 0
                        for result in phase_results.values()
                    ]
                )

                self.tracer.record_turn_result(
                    span=turn_span,
                    success=False,
                    execution_time_seconds=execution_time_ms / 1000.0,
                    total_ai_cost=float(total_ai_cost),
                    phases_completed=[phase.value for phase in phases_completed],
                    error_details=f"Critical error: {str(e)}",
                )

                # Close the root span with error
                turn_span.end()
                logger.debug(f"Completed distributed tracing root span for failed turn {turn_id}")

            # Emergency compensation
            if self.saga_enabled and phases_completed:
                try:
                    compensation_result = await self._execute_saga_compensation(
                        turn, phases_completed, phase_results
                    )
                    compensation_actions.extend(compensation_result.compensation_actions)
                except Exception as comp_error:
                    logger.error(f"Emergency compensation failed for turn {turn_id}: {comp_error}")

            # Create failure result
            execution_time_ms = (datetime.now() - execution_start).total_seconds() * 1000
            performance_metrics = await self._gather_performance_metrics(
                turn_id, phase_results, execution_time_ms
            )

            return TurnExecutionResult(
                turn_id=turn_id,
                success=False,
                execution_time_ms=execution_time_ms,
                phases_completed=phases_completed,
                phase_results=phase_results,
                compensation_actions=compensation_actions,
                performance_metrics=performance_metrics,
                error_details={
                    "critical_error": str(e),
                    "error_type": type(e).__name__,
                    "phases_completed": len(phases_completed),
                    "compensation_actions": len(compensation_actions),
                },
            )

        finally:
            # Stop performance monitoring
            if self.performance_monitoring_enabled:
                self.performance_tracker.stop_turn_monitoring(turn_id)

    async def _execute_phase(
        self,
        turn: Turn,
        phase_type: PhaseType,
        previous_results: Dict[PhaseType, PhaseResult],
        parent_span=None,
    ) -> PhaseResult:
        """
        Execute a single pipeline phase with comprehensive monitoring and distributed tracing.

        Args:
            turn: Turn entity
            phase_type: Phase to execute
            previous_results: Results from previous phases
            parent_span: Parent tracing span (root turn span)

        Returns:
            PhaseResult from phase execution
        """
        phase_implementation = self.phase_implementations[phase_type]

        # Start phase-level span as child of root turn span
        phase_span = None
        if self.tracer and parent_span:
            phase_order = list(self.phase_implementations.keys()).index(phase_type) + 1
            phase_span = self.tracer.start_phase_span(
                phase_name=phase_type.value,
                turn_id=turn.turn_id.turn_uuid,
                phase_order=phase_order,
                parent_span=parent_span,
            )

        # Create phase execution context
        context = PhaseExecutionContext(
            turn_id=turn.turn_id.turn_uuid,
            phase_type=phase_type,
            configuration=turn.configuration,
            participants=turn.participants,
            execution_metadata={
                "previous_phase_results": self._extract_phase_metadata(previous_results),
                "turn_state": turn.state.value,
                "execution_start": datetime.now().isoformat(),
            },
        )

        # Execute phase with timeout
        try:
            phase_result = await asyncio.wait_for(
                phase_implementation.execute(context),
                timeout=turn.configuration.get_phase_timeout(phase_type.value) / 1000.0,
            )

            # Record phase execution metrics
            self._record_phase_metrics(turn.turn_id, phase_type, phase_result, context)

            # Record phase results in distributed tracing span
            if self.tracer and phase_span:
                self.tracer.record_phase_result(
                    span=phase_span,
                    success=phase_result.success,
                    events_processed=phase_result.events_processed,
                    events_generated=len(phase_result.events_generated),
                    ai_cost=(
                        float(phase_result.ai_usage.get("total_cost", 0))
                        if phase_result.ai_usage
                        else 0.0
                    ),
                    ai_requests=(
                        phase_result.ai_usage.get("request_count", 0)
                        if phase_result.ai_usage
                        else 0
                    ),
                    error_details=None,
                )
                phase_span.end()

            return phase_result

        except asyncio.TimeoutError:
            logger.warning(f"Phase {phase_type.value} timed out for turn {turn.turn_id}")
            timeout_result = self._create_phase_timeout_result(phase_type, turn)

            # Record timeout in distributed tracing span
            if self.tracer and phase_span:
                self.tracer.record_phase_result(
                    span=phase_span,
                    success=False,
                    events_processed=0,
                    events_generated=0,
                    ai_cost=0.0,
                    ai_requests=0,
                    error_details="Phase execution timed out",
                )
                phase_span.end()

            return timeout_result

        except Exception as e:
            logger.error(f"Phase {phase_type.value} failed for turn {turn.turn_id}: {e}")
            failure_result = self._create_phase_failure_result(phase_type, str(e), turn)

            # Record failure in distributed tracing span
            if self.tracer and phase_span:
                self.tracer.record_phase_result(
                    span=phase_span,
                    success=False,
                    events_processed=0,
                    events_generated=0,
                    ai_cost=0.0,
                    ai_requests=0,
                    error_details=str(e),
                )
                phase_span.end()

            return failure_result

    async def _execute_saga_compensation(
        self,
        turn: Turn,
        completed_phases: List[PhaseType],
        phase_results: Dict[PhaseType, PhaseResult],
    ) -> Any:  # Returns saga compensation result
        """
        Execute saga compensation for failed turn.

        Args:
            turn: Turn entity
            completed_phases: List of completed phases
            phase_results: Phase execution results

        Returns:
            Saga compensation result
        """
        logger.info(f"Executing saga compensation for turn {turn.turn_id}")

        # Plan compensation actions
        compensation_plan = await self.saga_coordinator.plan_compensation(
            turn_id=turn.turn_id,
            completed_phases=completed_phases,
            phase_results=phase_results,
            rollback_strategy="selective",  # Could be 'complete' for full rollback
        )

        # Execute compensation
        compensation_result = await self.saga_coordinator.execute_compensation(
            compensation_plan=compensation_plan
        )

        # Record compensation in turn
        for action in compensation_result.compensation_actions:
            turn.add_compensation_action(action)

        logger.info(
            f"Saga compensation completed for turn {turn.turn_id}: "
            f"{len(compensation_result.compensation_actions)} actions executed"
        )

        return compensation_result

    async def _gather_performance_metrics(
        self,
        turn_id: TurnId,
        phase_results: Dict[PhaseType, PhaseResult],
        total_execution_time_ms: float,
    ) -> Dict[str, float]:
        """
        Gather comprehensive performance metrics for turn execution.

        Args:
            turn_id: Turn identifier
            phase_results: Phase execution results
            total_execution_time_ms: Total execution time

        Returns:
            Dictionary of performance metrics
        """
        metrics = {
            "total_execution_time_ms": total_execution_time_ms,
            "phases_executed": float(len(phase_results)),
            "successful_phases": float(len([r for r in phase_results.values() if r.success])),
            "failed_phases": float(len([r for r in phase_results.values() if not r.success])),
        }

        # Add phase-specific metrics
        total_events_processed = 0
        total_events_generated = 0
        total_ai_cost = Decimal("0.00")

        for phase_type, result in phase_results.items():
            phase_prefix = phase_type.value

            # Basic phase metrics
            metrics[f"{phase_prefix}_success"] = 1.0 if result.success else 0.0
            metrics[f"{phase_prefix}_execution_time_ms"] = result.performance_metrics.get(
                "execution_time_ms", 0.0
            )
            metrics[f"{phase_prefix}_events_processed"] = float(result.events_processed)
            metrics[f"{phase_prefix}_events_generated"] = float(len(result.events_generated))

            # Aggregate metrics
            total_events_processed += result.events_processed
            total_events_generated += len(result.events_generated)

            # AI usage metrics
            if result.ai_usage:
                ai_cost = result.ai_usage.get("total_cost", 0)
                metrics[f"{phase_prefix}_ai_cost"] = float(ai_cost)
                total_ai_cost += Decimal(str(ai_cost))

        # Aggregate metrics
        metrics["total_events_processed"] = float(total_events_processed)
        metrics["total_events_generated"] = float(total_events_generated)
        metrics["total_ai_cost"] = float(total_ai_cost)

        # Performance ratios
        if total_execution_time_ms > 0:
            metrics["events_per_second"] = (total_events_processed / total_execution_time_ms) * 1000
            metrics["cost_per_second"] = float(total_ai_cost) / (total_execution_time_ms / 1000)

        # Add system performance metrics if available
        if self.performance_monitoring_enabled:
            system_metrics = self.performance_tracker.get_turn_metrics(turn_id)
            metrics.update(system_metrics)

        return metrics

    def _extract_phase_metadata(
        self, phase_results: Dict[PhaseType, PhaseResult]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract metadata from previous phase results for context."""
        metadata = {}

        for phase_type, result in phase_results.items():
            metadata[phase_type.value] = {
                "success": result.success,
                "events_processed": result.events_processed,
                "events_generated": len(result.events_generated),
                "artifacts_created": result.artifacts_created,
                "metadata": result.metadata,
            }

            # Include specific result data based on phase type
            if phase_type == PhaseType.INTERACTION_ORCHESTRATION:
                # Extract interaction session results for event integration
                if "interaction_summary" in result.metadata:
                    metadata[phase_type.value]["session_results"] = result.metadata[
                        "interaction_summary"
                    ]

        return metadata

    def _record_phase_metrics(
        self,
        turn_id: TurnId,
        phase_type: PhaseType,
        phase_result: PhaseResult,
        context: PhaseExecutionContext,
    ) -> None:
        """Record detailed metrics for phase execution."""
        if self.performance_monitoring_enabled:
            self.performance_tracker.record_phase_metrics(
                turn_id=turn_id,
                phase_type=phase_type,
                execution_time_ms=context.get_execution_time_ms(),
                success=phase_result.success,
                events_processed=phase_result.events_processed,
                events_generated=len(phase_result.events_generated),
                ai_cost=(
                    phase_result.ai_usage.get("total_cost", 0) if phase_result.ai_usage else 0
                ),
            )

    def _create_phase_failure_result(
        self, phase_type: PhaseType, error_message: str, turn: Turn
    ) -> PhaseResult:
        """Create standardized phase failure result."""
        return PhaseResult(
            success=False,
            events_processed=0,
            events_generated=[],
            artifacts_created=[],
            error_details={
                "phase": phase_type.value,
                "error_message": error_message,
                "turn_id": str(turn.turn_id),
                "timestamp": datetime.now().isoformat(),
                "participants": turn.participants,
            },
        )

    def _create_phase_timeout_result(self, phase_type: PhaseType, turn: Turn) -> PhaseResult:
        """Create standardized phase timeout result."""
        timeout_ms = turn.configuration.get_phase_timeout(phase_type.value)

        return PhaseResult(
            success=False,
            events_processed=0,
            events_generated=[],
            artifacts_created=[],
            error_details={
                "phase": phase_type.value,
                "error_type": "timeout",
                "timeout_ms": timeout_ms,
                "turn_id": str(turn.turn_id),
                "timestamp": datetime.now().isoformat(),
                "participants": turn.participants,
            },
        )

    # Additional utility methods for turn management

    async def validate_turn_preconditions(
        self, participants: List[str], configuration: TurnConfiguration
    ) -> Tuple[bool, List[str]]:
        """
        Validate preconditions for turn execution.

        Args:
            participants: Participant agent IDs
            configuration: Turn configuration

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        errors = []

        # Validate participants
        if not participants:
            errors.append("At least one participant is required")
        elif len(participants) > configuration.max_participants:
            errors.append(
                f"Too many participants: {len(participants)} > {configuration.max_participants}"
            )

        # Validate configuration
        if configuration.world_time_advance <= 0:
            errors.append("World time advance must be positive")

        if configuration.ai_integration_enabled and configuration.max_ai_cost:
            if configuration.max_ai_cost <= 0:
                errors.append("AI cost limit must be positive when specified")

        # Validate timeouts
        for phase_type in PhaseType:
            timeout = configuration.get_phase_timeout(phase_type.value)
            if timeout <= 0:
                errors.append(f"Phase timeout for {phase_type.value} must be positive")

        return len(errors) == 0, errors

    async def get_turn_status(self, turn_id: TurnId) -> Optional[Dict[str, Any]]:
        """
        Get current status of a turn execution.

        Args:
            turn_id: Turn identifier

        Returns:
            Turn status information or None if not found
        """
        # In a real implementation, this would query turn state storage
        # For now, return basic status from performance tracker
        if self.performance_monitoring_enabled:
            return self.performance_tracker.get_turn_status(turn_id)

        return None

    async def cleanup_turn_resources(self, turn_id: TurnId) -> None:
        """
        Clean up resources associated with a turn.

        Args:
            turn_id: Turn identifier
        """
        logger.debug(f"Cleaning up resources for turn {turn_id}")

        if self.performance_monitoring_enabled:
            self.performance_tracker.cleanup_turn_data(turn_id)

        # Additional cleanup would go here (temp files, cached data, etc.)

    def get_orchestrator_health(self) -> Dict[str, Any]:
        """
        Get health status of the turn orchestrator.

        Returns:
            Health status information
        """
        return {
            "status": "healthy",
            "phase_implementations": len(self.phase_implementations),
            "saga_enabled": self.saga_enabled,
            "performance_monitoring_enabled": self.performance_monitoring_enabled,
            "max_concurrent_turns": self.max_concurrent_turns,
            "active_turns": (
                self.performance_tracker.get_active_turn_count()
                if self.performance_monitoring_enabled
                else 0
            ),
        }
