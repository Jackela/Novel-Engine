#!/usr/bin/env python3
"""
Pipeline Orchestrator Domain Service

Coordinates turn pipeline execution across all phases with
intelligent scheduling, resource management, and failure handling.
"""

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Tuple
from uuid import UUID

from ..entities import Turn
from ..value_objects import PhaseType


class PipelineOrchestrator:
    """
    Domain service orchestrating turn pipeline execution.

    Manages phase sequencing, resource allocation, timeout handling,
    and coordination with external systems for complete turn execution.

    Responsibilities:
    - Execute pipeline phases in correct order
    - Manage phase timeouts and resource limits
    - Coordinate with external context services
    - Handle phase failures and recovery
    - Track execution progress and metrics
    """

    def __init__(self):
        """Initialize pipeline orchestrator."""
        self.active_executions: Dict[UUID, Dict[str, Any]] = {}
        self.phase_handlers: Dict[PhaseType, Callable] = {}
        self.execution_metrics: Dict[str, Any] = {
            "total_turns_executed": 0,
            "successful_turns": 0,
            "failed_turns": 0,
            "average_execution_time_ms": 0.0,
            "phase_success_rates": {},
            "resource_utilization": {},
        }
        self.resource_limits: Dict[str, Any] = {
            "max_concurrent_turns": 5,
            "max_memory_mb": 1024,
            "max_cpu_percentage": 80.0,
            "max_ai_cost_per_hour": 50.0,
        }

    def orchestrate_turn_execution(
        self,
        turn: Turn,
        phase_handlers: Dict[PhaseType, Callable],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """
        Orchestrate complete turn execution through all pipeline phases.

        Args:
            turn: Turn to execute
            phase_handlers: Mapping of phase types to handler functions
            progress_callback: Optional callback for progress updates

        Returns:
            True if turn completed successfully, False otherwise

        Raises:
            ValueError: If orchestration fails
        """
        if turn.state.is_terminal():
            raise ValueError(f"Turn {turn.turn_id} is already terminal")

        # Register turn for active execution
        execution_id = turn.turn_id.turn_uuid
        self.active_executions[execution_id] = {
            "turn": turn,
            "started_at": datetime.now(),
            "current_phase": None,
            "phase_handlers": phase_handlers,
            "progress_callback": progress_callback,
            "resource_usage": {"memory_mb": 0, "cpu_time_ms": 0, "ai_cost": 0.0},
        }

        try:
            # Start turn planning
            if not self._execute_planning_phase(turn):
                return False

            # Start turn execution
            if not self._execute_pipeline_phases(turn, phase_handlers, progress_callback):
                return False

            # Complete turn successfully
            self._complete_turn_execution(execution_id, success=True)
            return True

        except Exception as e:
            # Handle execution failure
            self._handle_execution_failure(execution_id, str(e))
            return False

        finally:
            # Clean up active execution
            self.active_executions.pop(execution_id, None)

    def execute_single_phase(
        self,
        turn: Turn,
        phase_type: PhaseType,
        phase_handler: Callable,
        timeout_override: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute single pipeline phase with monitoring and error handling.

        Args:
            turn: Turn being executed
            phase_type: Type of phase to execute
            phase_handler: Handler function for the phase
            timeout_override: Optional timeout override in milliseconds

        Returns:
            Tuple of (success, phase_results)
        """
        phase_timeout = timeout_override or turn.configuration.get_phase_timeout(phase_type.value)

        # Prepare phase execution context
        phase_context = self._prepare_phase_context(turn, phase_type)

        # Start phase execution tracking
        execution_start = datetime.now()

        try:
            # Execute phase with timeout monitoring
            phase_results = self._execute_phase_with_timeout(
                turn, phase_type, phase_handler, phase_context, phase_timeout
            )

            # Validate phase results
            if not self._validate_phase_results(phase_type, phase_results):
                raise ValueError(f"Phase {phase_type} produced invalid results")

            # Update turn with successful phase completion
            events_processed = phase_results.get("events_processed", 0)
            events_generated = phase_results.get("events_generated", [])
            artifacts_created = phase_results.get("artifacts_created", [])
            performance_metrics = phase_results.get("performance_metrics", {})
            ai_usage = phase_results.get("ai_usage")

            turn.complete_phase(
                phase_type=phase_type,
                events_processed=events_processed,
                events_generated=events_generated,
                artifacts_created=artifacts_created,
                performance_metrics=performance_metrics,
                ai_usage=ai_usage,
                metadata=phase_results.get("metadata", {}),
            )

            # Update orchestrator metrics
            execution_time = (datetime.now() - execution_start).total_seconds() * 1000
            self._update_phase_metrics(phase_type, execution_time, success=True)

            return True, phase_results

        except Exception as e:
            # Handle phase failure
            error_message = str(e)
            error_details = {
                "error_type": type(e).__name__,
                "phase_context": phase_context,
                "execution_time_ms": (datetime.now() - execution_start).total_seconds() * 1000,
            }

            # Update turn with phase failure
            turn.fail_phase(
                phase_type=phase_type,
                error_message=error_message,
                error_details=error_details,
                can_compensate=turn.configuration.rollback_enabled,
            )

            # Update orchestrator metrics
            execution_time = (datetime.now() - execution_start).total_seconds() * 1000
            self._update_phase_metrics(phase_type, execution_time, success=False)

            return False, {"error": error_message, "error_details": error_details}

    def monitor_execution_progress(self, turn_id: UUID) -> Dict[str, Any]:
        """
        Monitor progress of active turn execution.

        Args:
            turn_id: Turn identifier to monitor

        Returns:
            Progress information and metrics
        """
        execution = self.active_executions.get(turn_id)

        if not execution:
            return {"status": "not_found"}

        turn = execution["turn"]
        started_at = execution["started_at"]
        current_time = datetime.now()

        # Calculate progress metrics
        completed_phases = len(turn.get_completed_phases())
        total_phases = len(PhaseType.get_all_phases_ordered())
        progress_percentage = (completed_phases / total_phases) * 100

        execution_time = current_time - started_at
        remaining_time = self._estimate_remaining_time(turn)

        return {
            "status": "executing",
            "turn_id": str(turn_id),
            "current_phase": turn.current_phase.value if turn.current_phase else None,
            "progress_percentage": progress_percentage,
            "completed_phases": completed_phases,
            "total_phases": total_phases,
            "execution_time_seconds": execution_time.total_seconds(),
            "estimated_remaining_seconds": (
                remaining_time.total_seconds() if remaining_time else None
            ),
            "resource_usage": execution["resource_usage"],
            "is_overdue": turn.is_overdue(),
        }

    def get_orchestration_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive orchestration performance metrics.

        Returns:
            Detailed metrics and statistics
        """
        return {
            "execution_summary": {
                "total_turns_executed": self.execution_metrics["total_turns_executed"],
                "successful_turns": self.execution_metrics["successful_turns"],
                "failed_turns": self.execution_metrics["failed_turns"],
                "success_rate": (
                    self.execution_metrics["successful_turns"]
                    / max(1, self.execution_metrics["total_turns_executed"])
                ),
                "average_execution_time_ms": self.execution_metrics["average_execution_time_ms"],
            },
            "phase_performance": self.execution_metrics["phase_success_rates"],
            "resource_utilization": self.execution_metrics["resource_utilization"],
            "active_executions": len(self.active_executions),
            "resource_limits": self.resource_limits,
            "timestamp": datetime.now().isoformat(),
        }

    def adjust_resource_limits(
        self,
        max_concurrent_turns: Optional[int] = None,
        max_memory_mb: Optional[int] = None,
        max_cpu_percentage: Optional[float] = None,
        max_ai_cost_per_hour: Optional[float] = None,
    ) -> None:
        """
        Adjust orchestration resource limits.

        Args:
            max_concurrent_turns: Maximum concurrent turn executions
            max_memory_mb: Maximum memory usage in MB
            max_cpu_percentage: Maximum CPU usage percentage
            max_ai_cost_per_hour: Maximum AI cost per hour
        """
        if max_concurrent_turns is not None:
            self.resource_limits["max_concurrent_turns"] = max_concurrent_turns

        if max_memory_mb is not None:
            self.resource_limits["max_memory_mb"] = max_memory_mb

        if max_cpu_percentage is not None:
            self.resource_limits["max_cpu_percentage"] = max_cpu_percentage

        if max_ai_cost_per_hour is not None:
            self.resource_limits["max_ai_cost_per_hour"] = max_ai_cost_per_hour

    # Private helper methods

    def _execute_planning_phase(self, turn: Turn) -> bool:
        """Execute turn planning phase."""
        try:
            turn.start_planning()

            # Validate configuration
            config_errors = turn.configuration.validate_constraints()
            if config_errors:
                raise ValueError(f"Configuration validation failed: {config_errors}")

            return True

        except Exception:
            # Planning failed
            turn.state = turn.TurnState.FAILED
            turn.completed_at = datetime.now()
            return False

    def _execute_pipeline_phases(
        self,
        turn: Turn,
        phase_handlers: Dict[PhaseType, Callable],
        progress_callback: Optional[Callable],
    ) -> bool:
        """Execute all pipeline phases in sequence."""
        # Start turn execution
        turn.start_execution()

        # Execute each phase in order
        for phase_type in PhaseType.get_all_phases_ordered():
            if not turn.configuration.is_phase_enabled(phase_type.value):
                # Skip disabled phase
                continue

            phase_handler = phase_handlers.get(phase_type)
            if not phase_handler:
                raise ValueError(f"No handler provided for phase {phase_type}")

            # Execute phase
            success, phase_results = self.execute_single_phase(turn, phase_type, phase_handler)

            # Call progress callback if provided
            if progress_callback:
                progress_callback(turn, phase_type, success, phase_results)

            # Check if phase failed
            if not success:
                # Phase failure will trigger compensation if enabled
                return False

            # Check resource limits
            if not self._check_resource_limits(turn):
                raise ValueError("Resource limits exceeded")

        return True

    def _prepare_phase_context(self, turn: Turn, phase_type: PhaseType) -> Dict[str, Any]:
        """Prepare execution context for phase."""
        return {
            "turn_id": turn.turn_id.turn_uuid,
            "phase_type": phase_type.value,
            "configuration": turn.configuration.__dict__,
            "participants": turn.configuration.participants,
            "ai_integration_enabled": turn.configuration.should_use_ai_for_phase(phase_type.value),
            "timeout_ms": turn.configuration.get_phase_timeout(phase_type.value),
            "previous_phases": [p.value for p in turn.get_completed_phases()],
            "rollback_snapshots": turn.rollback_snapshots,
            "metadata": {
                "execution_started_at": datetime.now().isoformat(),
                "orchestrator_version": "1.0.0",
            },
        }

    def _execute_phase_with_timeout(
        self,
        turn: Turn,
        phase_type: PhaseType,
        phase_handler: Callable,
        phase_context: Dict[str, Any],
        timeout_ms: int,
    ) -> Dict[str, Any]:
        """Execute phase with timeout monitoring."""
        # In a real implementation, this would use async/await or threading
        # with proper timeout handling. For now, we'll simulate the execution.

        start_time = datetime.now()

        try:
            # Call the phase handler
            results = phase_handler(phase_context)

            # Check if execution exceeded timeout
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            if execution_time > timeout_ms:
                raise TimeoutError(f"Phase {phase_type} exceeded timeout of {timeout_ms}ms")

            # Add execution metadata
            results["execution_time_ms"] = execution_time
            results["timeout_exceeded"] = False

            return results

        except TimeoutError:
            raise
        except Exception as e:
            # Wrap other exceptions with context
            raise RuntimeError(f"Phase {phase_type} execution failed: {e}") from e

    def _validate_phase_results(self, phase_type: PhaseType, results: Dict[str, Any]) -> bool:
        """Validate phase execution results."""
        if not isinstance(results, dict):
            return False

        # Check for required result fields
        required_fields = {"success", "events_processed"}
        if not all(field in results for field in required_fields):
            return False

        # Validate result values
        if not isinstance(results.get("success"), bool):
            return False

        if not isinstance(results.get("events_processed"), int) or results["events_processed"] < 0:
            return False

        # Phase-specific validation
        if phase_type in {PhaseType.SUBJECTIVE_BRIEF, PhaseType.NARRATIVE_INTEGRATION}:
            # AI-enabled phases should have AI usage data
            if results.get("ai_usage") and not isinstance(results["ai_usage"], dict):
                return False

        return True

    def _estimate_remaining_time(self, turn: Turn) -> Optional[timedelta]:
        """Estimate remaining execution time for turn."""
        if not turn.started_at:
            return None

        completed_phases = len(turn.get_completed_phases())
        total_phases = len(PhaseType.get_all_phases_ordered())

        if completed_phases == 0:
            return timedelta(milliseconds=turn.configuration.max_execution_time_ms)

        # Calculate average time per phase so far
        elapsed_time = datetime.now() - turn.started_at
        avg_time_per_phase = elapsed_time / completed_phases

        remaining_phases = total_phases - completed_phases
        return avg_time_per_phase * remaining_phases

    def _check_resource_limits(self, turn: Turn) -> bool:
        """Check if current execution is within resource limits."""
        # Check concurrent executions
        if len(self.active_executions) > self.resource_limits["max_concurrent_turns"]:
            return False

        # Check memory usage (would integrate with actual memory monitoring)
        # For now, we'll simulate based on turn complexity
        estimated_memory = len(turn.configuration.participants) * 10  # MB per participant
        if estimated_memory > self.resource_limits["max_memory_mb"]:
            return False

        return True

    def _update_phase_metrics(
        self, phase_type: PhaseType, execution_time_ms: float, success: bool
    ) -> None:
        """Update phase execution metrics."""
        phase_key = phase_type.value

        if phase_key not in self.execution_metrics["phase_success_rates"]:
            self.execution_metrics["phase_success_rates"][phase_key] = {
                "total_executions": 0,
                "successful_executions": 0,
                "average_time_ms": 0.0,
            }

        phase_metrics = self.execution_metrics["phase_success_rates"][phase_key]

        # Update execution counts
        phase_metrics["total_executions"] += 1
        if success:
            phase_metrics["successful_executions"] += 1

        # Update average execution time
        total_executions = phase_metrics["total_executions"]
        current_avg = phase_metrics["average_time_ms"]
        phase_metrics["average_time_ms"] = (
            current_avg * (total_executions - 1) + execution_time_ms
        ) / total_executions

    def _complete_turn_execution(self, execution_id: UUID, success: bool) -> None:
        """Complete turn execution and update metrics."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return

        # Update execution metrics
        self.execution_metrics["total_turns_executed"] += 1
        if success:
            self.execution_metrics["successful_turns"] += 1
        else:
            self.execution_metrics["failed_turns"] += 1

        # Update average execution time
        execution_time = (datetime.now() - execution["started_at"]).total_seconds() * 1000
        total_turns = self.execution_metrics["total_turns_executed"]
        current_avg = self.execution_metrics["average_execution_time_ms"]

        self.execution_metrics["average_execution_time_ms"] = (
            current_avg * (total_turns - 1) + execution_time
        ) / total_turns

    def _handle_execution_failure(self, execution_id: UUID, error_message: str) -> None:
        """Handle turn execution failure."""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return

        turn = execution["turn"]

        # Ensure turn is marked as failed if not already
        if not turn.state.is_terminal():
            turn.state = turn.TurnState.FAILED
            turn.completed_at = datetime.now()

        # Complete execution tracking
        self._complete_turn_execution(execution_id, success=False)
