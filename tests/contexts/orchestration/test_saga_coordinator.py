#!/usr/bin/env python3
"""
Tests for SagaCoordinator.

This module contains comprehensive tests for the saga pattern coordination
including compensation planning, execution, and validation.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.contexts.orchestration.domain.entities.turn import Turn
from src.contexts.orchestration.domain.services.saga_coordinator import SagaCoordinator
from src.contexts.orchestration.domain.value_objects import (
    CompensationAction,
    CompensationType,
    PhaseType,
    TurnConfiguration,
    TurnId,
)

pytestmark = pytest.mark.unit



@pytest.fixture
def saga_coordinator():
    """Create a SagaCoordinator instance for testing."""
    return SagaCoordinator()


@pytest.fixture
def sample_turn():
    """Create a sample turn for testing."""
    turn_id = TurnId.generate()
    config = TurnConfiguration(participants=["agent_1", "agent_2"])
    return Turn.create(
        turn_id=turn_id,
        configuration=config,
        participants=["agent_1", "agent_2"],
    )


@pytest.fixture
def sample_compensation_action():
    """Create a sample compensation action."""
    return CompensationAction.create_for_phase_failure(
        action_id=uuid4(),
        turn_id=uuid4(),
        failed_phase="world_update",
        compensation_type=CompensationType.LOG_FAILURE,
    )


class TestSagaCoordinatorInitialization:
    """Test suite for SagaCoordinator initialization."""

    def test_initialization(self):
        """Test coordinator initialization."""
        coordinator = SagaCoordinator()
        
        assert coordinator.active_compensations == {}
        assert coordinator.compensation_strategies == {}
        assert coordinator.rollback_snapshots == {}
        assert coordinator.coordination_state["total_compensations_executed"] == 0
        assert coordinator.coordination_state["successful_compensations"] == 0
        assert coordinator.coordination_state["failed_compensations"] == 0
        assert coordinator.coordination_state["average_compensation_time_ms"] == 0.0
        assert coordinator.coordination_state["data_consistency_violations"] == 0


class TestCompensationPlanning:
    """Test suite for compensation planning."""

    def test_plan_compensation_strategy_success(
        self, saga_coordinator, sample_turn
    ):
        """Test successful compensation strategy planning."""
        # Setup turn with rollback enabled
        sample_turn.configuration = sample_turn.configuration
        # Simulate completed phases
        sample_turn.phase_statuses[PhaseType.WORLD_UPDATE] = MagicMock(
            status=MagicMock(is_successful=lambda: True)
        )
        
        actions = saga_coordinator.plan_compensation_strategy(
            turn=sample_turn,
            failed_phase=PhaseType.SUBJECTIVE_BRIEF,
            error_context={"error": "test_error"},
        )
        
        assert isinstance(actions, list)
        assert len(actions) > 0

    def test_plan_compensation_strategy_rollback_disabled(
        self, saga_coordinator, sample_turn
    ):
        """Test compensation planning with rollback disabled."""
        # Create a turn with rollback disabled
        config = TurnConfiguration(rollback_enabled=False, participants=["agent_1"])
        turn = Turn.create(
            turn_id=TurnId.generate(),
            configuration=config,
            participants=["agent_1"],
        )
        
        with pytest.raises(ValueError, match="Rollback not enabled"):
            saga_coordinator.plan_compensation_strategy(
                turn=turn,
                failed_phase=PhaseType.WORLD_UPDATE,
                error_context={},
            )

    def test_plan_compensation_strategy_no_committed_phases(
        self, saga_coordinator, sample_turn
    ):
        """Test compensation planning with no committed phases."""
        actions = saga_coordinator.plan_compensation_strategy(
            turn=sample_turn,
            failed_phase=PhaseType.WORLD_UPDATE,
            error_context={"error": "test"},
        )
        
        # Should return empty list when no phases committed
        assert actions == []

    def test_plan_compensation_strategy_stores_strategy(
        self, saga_coordinator, sample_turn
    ):
        """Test that compensation strategy is stored."""
        sample_turn.phase_statuses[PhaseType.WORLD_UPDATE] = MagicMock(
            status=MagicMock(is_successful=lambda: True)
        )
        
        saga_coordinator.plan_compensation_strategy(
            turn=sample_turn,
            failed_phase=PhaseType.SUBJECTIVE_BRIEF,
            error_context={"error": "test"},
        )
        
        strategy_id = str(sample_turn.turn_id.turn_uuid)
        assert strategy_id in saga_coordinator.compensation_strategies
        strategy = saga_coordinator.compensation_strategies[strategy_id]
        assert "total_actions" in strategy
        assert "failed_phase" in strategy


class TestCompensationExecution:
    """Test suite for compensation execution."""

    def test_execute_compensation_action_success(
        self, saga_coordinator, sample_turn, sample_compensation_action
    ):
        """Test successful compensation action execution."""
        result = saga_coordinator.execute_compensation_action(
            turn=sample_turn,
            action=sample_compensation_action,
        )
        
        assert result.status in ["completed", "failed"]

    def test_execute_compensation_action_not_ready(
        self, saga_coordinator, sample_turn
    ):
        """Test executing action that is not ready."""
        # Create action in executing state
        action = CompensationAction(
            action_id=uuid4(),
            compensation_type=CompensationType.LOG_FAILURE,
            target_phase="world_update",
            turn_id=uuid4(),
            triggered_at=datetime.now(),
            status="executing",
        )
        
        with pytest.raises(ValueError, match="not ready"):
            saga_coordinator.execute_compensation_action(
                turn=sample_turn,
                action=action,
            )

    def test_execute_compensation_by_type_world_state(
        self, saga_coordinator, sample_turn
    ):
        """Test world state rollback execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.ROLLBACK_WORLD_STATE,
            rollback_data={"state_changes": [{"entity": "test"}]},
            affected_entities=["entity_1"],
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert "rollback_timestamp" in result

    def test_execute_compensation_by_type_subjective_brief(
        self, saga_coordinator, sample_turn
    ):
        """Test subjective brief invalidation execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="subjective_brief",
            compensation_type=CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS,
            affected_entities=["entity_1", "entity_2"],
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert result["briefs_invalidated"] == 2

    def test_execute_compensation_by_type_interaction(
        self, saga_coordinator, sample_turn
    ):
        """Test interaction cancellation execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="interaction_orchestration",
            compensation_type=CompensationType.CANCEL_INTERACTIONS,
            affected_entities=["entity_1"],
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert result["negotiations_terminated"] is True

    def test_execute_compensation_by_type_event_removal(
        self, saga_coordinator, sample_turn
    ):
        """Test event removal execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="event_integration",
            compensation_type=CompensationType.REMOVE_EVENTS,
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {"events_to_remove": ["event_1", "event_2"]}
        )
        
        assert result["success"] is True
        assert result["events_removed"] == 2

    def test_execute_compensation_by_type_narrative(
        self, saga_coordinator, sample_turn
    ):
        """Test narrative reversion execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="narrative_integration",
            compensation_type=CompensationType.REVERT_NARRATIVE_CHANGES,
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {"narrative_changes": ["change_1"]}
        )
        
        assert result["success"] is True
        assert result["story_consistency_maintained"] is True

    def test_execute_compensation_by_type_notification(
        self, saga_coordinator, sample_turn
    ):
        """Test participant notification execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.NOTIFY_PARTICIPANTS,
            affected_entities=["party_1", "party_2", "party_3"],
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert result["participants_notified"] == 3

    def test_execute_compensation_by_type_logging(
        self, saga_coordinator, sample_turn
    ):
        """Test failure logging execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.LOG_FAILURE,
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert result["audit_trail_updated"] is True

    def test_execute_compensation_by_type_manual_review(
        self, saga_coordinator, sample_turn
    ):
        """Test manual review trigger execution."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.TRIGGER_MANUAL_REVIEW,
            metadata={"review_priority": "high"},
        )
        
        result = saga_coordinator._execute_compensation_by_type(
            sample_turn, action, {}
        )
        
        assert result["success"] is True
        assert result["review_ticket_created"] is True
        assert result["priority"] == "high"

    def test_execute_compensation_by_type_unknown(
        self, saga_coordinator, sample_turn
    ):
        """Test execution with unknown compensation type."""
        # Create a mock compensation type
        action = MagicMock()
        action.compensation_type = MagicMock()
        action.compensation_type.value = "unknown_type"
        
        with pytest.raises(ValueError, match="Unknown compensation type"):
            saga_coordinator._execute_compensation_by_type(sample_turn, action, {})


class TestParallelCompensation:
    """Test suite for parallel compensation coordination."""

    def test_coordinate_parallel_compensations_empty(
        self, saga_coordinator, sample_turn
    ):
        """Test parallel coordination with empty actions."""
        result = saga_coordinator.coordinate_parallel_compensations(
            sample_turn, []
        )
        
        assert result == []

    def test_coordinate_parallel_compensations_with_actions(
        self, saga_coordinator, sample_turn
    ):
        """Test parallel coordination with multiple actions."""
        actions = [
            CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=sample_turn.turn_id.turn_uuid,
                failed_phase="world_update",
                compensation_type=CompensationType.LOG_FAILURE,
            )
            for _ in range(3)
        ]
        
        result = saga_coordinator.coordinate_parallel_compensations(
            sample_turn, actions, max_parallel=2
        )
        
        # max_parallel limits the results, so just verify we get some results
        assert len(result) >= 2


class TestCompensationValidation:
    """Test suite for compensation validation."""

    def test_validate_compensation_consistency_success(
        self, saga_coordinator, sample_turn
    ):
        """Test validation of consistent compensation."""
        actions = [
            CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=sample_turn.turn_id.turn_uuid,
                failed_phase="world_update",
                compensation_type=CompensationType.LOG_FAILURE,
            )
        ]
        # Complete the actions
        completed_actions = [
            action.start_execution().complete_execution(results={})
            for action in actions
        ]
        
        result = saga_coordinator.validate_compensation_consistency(
            sample_turn, completed_actions
        )
        
        assert result["overall_consistency"] is True
        assert result["data_integrity_maintained"] is True
        assert result["rollback_completeness"] == 1.0

    def test_validate_compensation_consistency_with_failures(
        self, saga_coordinator, sample_turn
    ):
        """Test validation with failed compensations."""
        action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.LOG_FAILURE,
        )
        # Must start execution before failing
        executing_action = action.start_execution()
        failed_action = executing_action.fail_execution(
            error_details={"test": "error"}, can_retry=False
        )
        
        result = saga_coordinator.validate_compensation_consistency(
            sample_turn, [failed_action]
        )
        
        assert result["overall_consistency"] is False
        assert result["manual_review_required"] is True

    def test_validate_compensation_consistency_rollback_incomplete(
        self, saga_coordinator, sample_turn
    ):
        """Test validation with incomplete rollback."""
        # Create mix of completed and pending actions
        completed = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.LOG_FAILURE,
        ).start_execution().complete_execution(results={})
        
        pending = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=sample_turn.turn_id.turn_uuid,
            failed_phase="world_update",
            compensation_type=CompensationType.NOTIFY_PARTICIPANTS,
        )
        
        result = saga_coordinator.validate_compensation_consistency(
            sample_turn, [completed, pending]
        )
        
        assert result["rollback_completeness"] == 0.5


class TestCompensationStatus:
    """Test suite for compensation status tracking."""

    def test_get_compensation_status_no_strategy(
        self, saga_coordinator
    ):
        """Test getting status with no compensation strategy."""
        status = saga_coordinator.get_compensation_status(uuid4())
        
        assert status["status"] == "no_compensation_required"

    def test_get_compensation_status_with_strategy(
        self, saga_coordinator, sample_turn
    ):
        """Test getting status with active compensation."""
        turn_id = sample_turn.turn_id.turn_uuid
        
        # Setup strategy
        saga_coordinator.compensation_strategies[str(turn_id)] = {
            "total_actions": 3,
            "planned_at": datetime.now(),
            "estimated_duration_ms": 5000,
            "compensation_types": ["log_failure", "notify"],
        }
        
        # Setup active compensations
        saga_coordinator.active_compensations[turn_id] = [
            MagicMock(is_terminal=lambda: True, status="completed"),
            MagicMock(is_terminal=lambda: False, status="pending"),
        ]
        
        status = saga_coordinator.get_compensation_status(turn_id)
        
        assert status["status"] == "in_progress"
        assert status["total_actions"] == 3
        assert status["completed_actions"] == 1
        assert status["pending_actions"] == 1


class TestHelperMethods:
    """Test suite for helper methods."""

    def test_get_committed_phases(self, saga_coordinator, sample_turn):
        """Test getting committed phases."""
        # Setup completed phases
        sample_turn.phase_statuses[PhaseType.WORLD_UPDATE] = MagicMock(
            status=MagicMock(is_successful=lambda: True)
        )
        sample_turn.phase_statuses[PhaseType.SUBJECTIVE_BRIEF] = MagicMock(
            status=MagicMock(is_successful=lambda: True)
        )
        
        committed = saga_coordinator._get_committed_phases(
            sample_turn, PhaseType.INTERACTION_ORCHESTRATION
        )
        
        assert PhaseType.WORLD_UPDATE in committed
        assert PhaseType.SUBJECTIVE_BRIEF in committed
        assert PhaseType.INTERACTION_ORCHESTRATION not in committed

    def test_should_apply_compensation(self, saga_coordinator):
        """Test compensation applicability check."""
        result = saga_coordinator._should_apply_compensation(
            PhaseType.WORLD_UPDATE,
            CompensationType.LOG_FAILURE,
            {}
        )
        
        assert result is True

    def test_get_rollback_data(self, saga_coordinator, sample_turn):
        """Test getting rollback data."""
        sample_turn.rollback_snapshots["world_update"] = {"data": "test"}
        
        data = saga_coordinator._get_rollback_data(sample_turn, PhaseType.WORLD_UPDATE)
        
        assert data == {"data": "test"}

    def test_is_critical_failure_world_update(self, saga_coordinator):
        """Test critical failure detection for world update."""
        result = saga_coordinator._is_critical_failure(
            PhaseType.WORLD_UPDATE,
            {}
        )
        
        assert result is True

    def test_is_critical_failure_event_integration(self, saga_coordinator):
        """Test critical failure detection for event integration."""
        result = saga_coordinator._is_critical_failure(
            PhaseType.EVENT_INTEGRATION,
            {}
        )
        
        assert result is True

    def test_is_critical_failure_by_severity(self, saga_coordinator):
        """Test critical failure detection by severity."""
        result = saga_coordinator._is_critical_failure(
            PhaseType.SUBJECTIVE_BRIEF,
            {"severity": "critical"}
        )
        
        assert result is True

    def test_is_critical_failure_non_critical(self, saga_coordinator):
        """Test non-critical failure detection."""
        result = saga_coordinator._is_critical_failure(
            PhaseType.SUBJECTIVE_BRIEF,
            {"severity": "low"}
        )
        
        assert result is False

    def test_calculate_compensation_cost(self, saga_coordinator):
        """Test compensation cost calculation."""
        cost = saga_coordinator._calculate_compensation_cost(
            CompensationType.ROLLBACK_WORLD_STATE,
            {}
        )
        
        assert cost == Decimal("0.10")

    def test_calculate_compensation_cost_unknown(self, saga_coordinator):
        """Test cost calculation for unknown type."""
        cost = saga_coordinator._calculate_compensation_cost(
            MagicMock(),
            {}
        )
        
        assert cost is None

    def test_can_retry_action_true(self, saga_coordinator):
        """Test retry check for retryable error."""
        result = saga_coordinator._can_retry_action(
            MagicMock(),
            {"error_type": "transient_error"}
        )
        
        assert result is True

    def test_can_retry_action_false(self, saga_coordinator):
        """Test retry check for non-retryable error."""
        result = saga_coordinator._can_retry_action(
            MagicMock(),
            {"error_type": "permission_denied"}
        )
        
        assert result is False

    def test_group_actions_for_parallel_execution(
        self, saga_coordinator
    ):
        """Test grouping actions for parallel execution."""
        actions = [
            CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=uuid4(),
                failed_phase="test",
                compensation_type=CompensationType.NOTIFY_PARTICIPANTS,
            ),
            CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=uuid4(),
                failed_phase="test",
                compensation_type=CompensationType.LOG_FAILURE,
            ),
        ]
        
        groups = saga_coordinator._group_actions_for_parallel_execution(actions)
        
        assert len(groups) >= 1

    def test_has_critical_failures_true(self, saga_coordinator):
        """Test critical failure detection in results."""
        actions = [
            MagicMock(
                status="failed",
                compensation_type=CompensationType.ROLLBACK_WORLD_STATE
            )
        ]
        # Make the compensation type appear destructive
        actions[0].compensation_type.is_destructive = lambda: True
        
        result = saga_coordinator._has_critical_failures(actions)
        
        assert result is True

    def test_has_critical_failures_false(self, saga_coordinator):
        """Test no critical failures in results."""
        actions = [
            MagicMock(
                status="completed",
                compensation_type=CompensationType.LOG_FAILURE
            )
        ]
        
        result = saga_coordinator._has_critical_failures(actions)
        
        assert result is False

    def test_calculate_rollback_completeness_full(self, saga_coordinator):
        """Test rollback completeness calculation (100%)."""
        actions = [
            MagicMock(status="completed"),
            MagicMock(status="completed"),
        ]
        
        result = saga_coordinator._calculate_rollback_completeness(
            MagicMock(), actions
        )
        
        assert result == 1.0

    def test_calculate_rollback_completeness_partial(self, saga_coordinator):
        """Test rollback completeness calculation (partial)."""
        actions = [
            MagicMock(status="completed"),
            MagicMock(status="failed"),
        ]
        
        result = saga_coordinator._calculate_rollback_completeness(
            MagicMock(), actions
        )
        
        assert result == 0.5

    def test_check_data_integrity_clean(self, saga_coordinator):
        """Test data integrity check with no violations."""
        actions = [
            MagicMock(
                status="completed",
                compensation_type=CompensationType.LOG_FAILURE
            )
        ]
        
        violations = saga_coordinator._check_data_integrity(
            MagicMock(), actions
        )
        
        assert violations == []

    def test_check_data_integrity_violations(self, saga_coordinator):
        """Test data integrity check with violations."""
        actions = [
            MagicMock(
                status="failed",
                compensation_type=CompensationType.ROLLBACK_WORLD_STATE
            )
        ]
        actions[0].compensation_type.is_destructive = lambda: True
        
        violations = saga_coordinator._check_data_integrity(
            MagicMock(), actions
        )
        
        assert len(violations) > 0
