#!/usr/bin/env python3
"""
Tests for Conflict Resolution in Turn Orchestration.

This module contains comprehensive tests for conflict resolution logic
including state transition conflicts, compensation conflicts, and turn
lifecycle conflict detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from src.contexts.orchestration.domain.entities.turn import Turn, TurnState
from src.contexts.orchestration.domain.value_objects import (
    CompensationAction,
    CompensationType,
    PhaseResult,
    PhaseStatus,
    PhaseStatusEnum,
    PhaseType,
    TurnConfiguration,
    TurnId,
)


@pytest.fixture
def sample_turn():
    """Create a sample turn for testing."""
    return Turn.create(
        turn_id=TurnId.generate(),
        configuration=TurnConfiguration(participants=["agent_1"]),
        participants=["agent_1"],
    )


@pytest.fixture
def executing_turn():
    """Create a turn in executing state."""
    turn = Turn.create(
        turn_id=TurnId.generate(),
        configuration=TurnConfiguration(participants=["agent_1"]),
        participants=["agent_1"],
    )
    turn.start_planning()
    turn.start_execution()
    return turn


class TestTurnStateTransitionConflicts:
    """Test suite for turn state transition conflicts."""

    def test_valid_state_transition_created_to_planning(self, sample_turn):
        """Test valid transition from CREATED to PLANNING."""
        sample_turn.start_planning()
        
        assert sample_turn.state == TurnState.PLANNING

    def test_valid_state_transition_planning_to_executing(self, sample_turn):
        """Test valid transition from PLANNING to EXECUTING."""
        sample_turn.start_planning()
        sample_turn.start_execution()
        
        assert sample_turn.state == TurnState.EXECUTING

    def test_valid_state_transition_executing_to_completed(self, executing_turn):
        """Test valid transition from EXECUTING to COMPLETED."""
        # Complete all phases
        for phase_type in PhaseType.get_all_phases_ordered():
            executing_turn.phase_statuses[phase_type] = PhaseStatus.create_running(
                phase_type, datetime.now()
            )
            executing_turn.complete_phase(
                phase_type=phase_type,
                events_processed=1,
            )
        
        assert executing_turn.state == TurnState.COMPLETED

    def test_invalid_state_transition_created_to_executing(self, sample_turn):
        """Test invalid transition from CREATED directly to EXECUTING."""
        with pytest.raises(ValueError, match="Invalid state transition"):
            sample_turn.start_execution()

    def test_invalid_state_transition_executing_to_planning(self, executing_turn):
        """Test invalid transition from EXECUTING back to PLANNING."""
        with pytest.raises(ValueError, match="Invalid state transition"):
            executing_turn._validate_state_transition(TurnState.PLANNING)

    def test_invalid_state_transition_completed_to_any(self):
        """Test invalid transition from COMPLETED state."""
        turn = Turn.create(
            turn_id=TurnId.generate(),
            configuration=TurnConfiguration(participants=["agent_1"]),
            participants=["agent_1"],
        )
        turn.start_planning()
        turn.start_execution()
        # Complete all phases
        for phase_type in PhaseType.get_all_phases_ordered():
            turn.phase_statuses[phase_type] = PhaseStatus.create_running(
                phase_type, datetime.now()
            )
            turn.complete_phase(phase_type=phase_type, events_processed=1)
        
        # Try to transition from COMPLETED
        with pytest.raises(ValueError, match="Invalid state transition"):
            turn._validate_state_transition(TurnState.EXECUTING)

    def test_terminal_state_detection(self):
        """Test terminal state detection."""
        assert TurnState.COMPLETED.is_terminal() is True
        assert TurnState.FAILED.is_terminal() is True
        assert TurnState.CANCELLED.is_terminal() is True
        assert TurnState.CREATED.is_terminal() is False
        assert TurnState.PLANNING.is_terminal() is False
        assert TurnState.EXECUTING.is_terminal() is False

    def test_active_state_detection(self):
        """Test active state detection."""
        assert TurnState.PLANNING.is_active() is True
        assert TurnState.EXECUTING.is_active() is True
        assert TurnState.COMPENSATING.is_active() is True
        assert TurnState.CREATED.is_active() is False
        assert TurnState.COMPLETED.is_active() is False


class TestPhaseCompletionConflicts:
    """Test suite for phase completion conflicts."""

    def test_complete_phase_not_running(self, sample_turn):
        """Test completing a phase that is not running."""
        with pytest.raises(ValueError, match="is not running"):
            sample_turn.complete_phase(
                phase_type=PhaseType.WORLD_UPDATE,
                events_processed=1,
            )

    def test_complete_unknown_phase(self, executing_turn):
        """Test completing an unknown phase."""
        with pytest.raises(ValueError, match="Unknown phase type"):
            executing_turn.complete_phase(
                phase_type=MagicMock(),  # Invalid phase
                events_processed=1,
            )

    def test_fail_phase_not_running(self, sample_turn):
        """Test failing a phase that is not running."""
        with pytest.raises(ValueError, match="is not running"):
            sample_turn.fail_phase(
                phase_type=PhaseType.WORLD_UPDATE,
                error_message="Test error",
            )


class TestCompensationConflicts:
    """Test suite for compensation-related conflicts."""

    def test_initiate_compensation_without_rollback(self):
        """Test initiating compensation when rollback is disabled."""
        turn = Turn.create(
            turn_id=TurnId.generate(),
            configuration=TurnConfiguration(
                rollback_enabled=False,
                participants=["agent_1"]
            ),
            participants=["agent_1"],
        )
        turn.start_planning()
        turn.start_execution()
        
        # Fail a phase without rollback
        turn.phase_statuses[PhaseType.WORLD_UPDATE] = PhaseStatus.create_running(
            PhaseType.WORLD_UPDATE, datetime.now()
        )
        turn.fail_phase(
            phase_type=PhaseType.WORLD_UPDATE,
            error_message="Test error",
            can_compensate=False,  # Disable compensation
        )
        
        assert turn.state == TurnState.FAILED

    def test_complete_compensation_action_not_found(self, executing_turn):
        """Test completing a non-existent compensation action."""
        executing_turn.state = TurnState.COMPENSATING
        
        with pytest.raises(ValueError, match="Compensation action not found"):
            executing_turn.complete_compensation_action(
                action_id=uuid4(),
                results={},
            )

    def test_compensation_action_sequence(self, executing_turn):
        """Test proper sequencing of compensation actions."""
        # Start with a completed phase
        executing_turn.phase_statuses[PhaseType.WORLD_UPDATE] = PhaseStatus.create_running(
            PhaseType.WORLD_UPDATE, datetime.now()
        )
        executing_turn.complete_phase(
            phase_type=PhaseType.WORLD_UPDATE,
            events_processed=5,
        )
        
        # Move to next phase and fail it
        executing_turn.phase_statuses[PhaseType.SUBJECTIVE_BRIEF] = PhaseStatus.create_running(
            PhaseType.SUBJECTIVE_BRIEF, datetime.now()
        )
        executing_turn.fail_phase(
            phase_type=PhaseType.SUBJECTIVE_BRIEF,
            error_message="AI service unavailable",
        )
        
        assert executing_turn.state == TurnState.COMPENSATING
        assert len(executing_turn.compensation_actions) > 0


class TestConcurrentModificationConflicts:
    """Test suite for concurrent modification conflicts."""

    def test_version_increment_on_state_change(self, sample_turn):
        """Test version increment on state changes."""
        initial_version = sample_turn.version
        
        sample_turn.start_planning()
        
        assert sample_turn.version == initial_version + 1

    def test_version_increment_on_phase_complete(self, executing_turn):
        """Test version increment on phase completion."""
        executing_turn.phase_statuses[PhaseType.WORLD_UPDATE] = PhaseStatus.create_running(
            PhaseType.WORLD_UPDATE, datetime.now()
        )
        initial_version = executing_turn.version
        
        executing_turn.complete_phase(
            phase_type=PhaseType.WORLD_UPDATE,
            events_processed=1,
        )
        
        assert executing_turn.version == initial_version + 1

    def test_updated_at_timestamp_update(self, sample_turn):
        """Test updated_at timestamp is updated on changes."""
        initial_updated = sample_turn.updated_at
        
        sample_turn.start_planning()
        
        assert sample_turn.updated_at > initial_updated


class TestResourceLimitConflicts:
    """Test suite for resource limit conflicts."""

    def test_turn_overdue_detection(self, executing_turn):
        """Test overdue turn detection."""
        # Set started_at to past the max execution time
        executing_turn.started_at = datetime.now() - timedelta(
            milliseconds=executing_turn.configuration.max_execution_time_ms + 1000
        )
        
        assert executing_turn.is_overdue() is True

    def test_turn_not_overdue(self, executing_turn):
        """Test non-overdue turn detection."""
        executing_turn.started_at = datetime.now() - timedelta(seconds=1)
        
        assert executing_turn.is_overdue() is False

    def test_turn_not_overdue_terminal(self):
        """Test overdue detection for terminal state."""
        turn = Turn.create(
            turn_id=TurnId.generate(),
            configuration=TurnConfiguration(participants=["agent_1"]),
            participants=["agent_1"],
        )
        turn.start_planning()
        turn.start_execution()
        # Complete all phases
        for phase_type in PhaseType.get_all_phases_ordered():
            turn.phase_statuses[phase_type] = PhaseStatus.create_running(
                phase_type, datetime.now()
            )
            turn.complete_phase(phase_type=phase_type, events_processed=1)
        
        # Even with old started_at, completed turns are not overdue
        turn.started_at = datetime.now() - timedelta(hours=1)
        
        assert turn.is_overdue() is False


class TestPhaseOrderConflicts:
    """Test suite for phase ordering conflicts."""

    def test_get_next_phase_sequence(self):
        """Test getting next phase in sequence."""
        assert Turn._get_next_phase(None, PhaseType.WORLD_UPDATE) == PhaseType.SUBJECTIVE_BRIEF
        assert Turn._get_next_phase(None, PhaseType.SUBJECTIVE_BRIEF) == PhaseType.INTERACTION_ORCHESTRATION
        assert Turn._get_next_phase(None, PhaseType.NARRATIVE_INTEGRATION) is None

    def test_all_phases_complete_check(self, executing_turn):
        """Test checking if all phases are complete."""
        # Initially no phases completed
        assert executing_turn._are_all_phases_complete() is False
        
        # Complete all phases
        for phase_type in PhaseType.get_all_phases_ordered():
            executing_turn.phase_statuses[phase_type] = PhaseStatus.create_completed(
                phase_type, datetime.now()
            )
        
        assert executing_turn._are_all_phases_complete() is True

    def test_get_completed_phases(self, executing_turn):
        """Test getting list of completed phases."""
        # Complete one phase
        executing_turn.phase_statuses[PhaseType.WORLD_UPDATE] = PhaseStatus.create_completed(
            PhaseType.WORLD_UPDATE, datetime.now()
        )
        
        completed = executing_turn.get_completed_phases()
        
        assert PhaseType.WORLD_UPDATE in completed
        assert PhaseType.SUBJECTIVE_BRIEF not in completed

    def test_get_failed_phases(self, executing_turn):
        """Test getting list of failed phases."""
        executing_turn.phase_statuses[PhaseType.WORLD_UPDATE] = PhaseStatus.create_failed(
            PhaseType.WORLD_UPDATE, "Test failure"
        )
        
        failed = executing_turn.get_failed_phases()
        
        assert PhaseType.WORLD_UPDATE in failed


class TestConfigurationConflicts:
    """Test suite for configuration-related conflicts."""

    def test_configuration_participants_overlap(self):
        """Test configuration with overlapping participants."""
        with pytest.raises(ValueError, match="excluded_agents and required_agents cannot overlap"):
            TurnConfiguration(
                participants=["agent_1"],
                excluded_agents={"agent_1"},
                required_agents={"agent_1"},
            )

    def test_configuration_missing_required_agents(self):
        """Test configuration validation for missing required agents."""
        config = TurnConfiguration(
            participants=["agent_1"],
            required_agents={"agent_1", "agent_2"},
        )
        
        errors = config.validate_constraints()
        
        assert any("Missing required agents" in str(e) for e in errors)

    def test_configuration_phase_timeout_exceeds_max(self):
        """Test validation when phase timeouts exceed max execution time."""
        config = TurnConfiguration(
            max_execution_time_ms=1000,  # 1 second
            phase_timeouts={
                "world_update": 10000,  # 10 seconds - way over
                "subjective_brief": 10000,
            },
            participants=["agent_1"]
        )
        
        errors = config.validate_constraints()
        
        assert len(errors) > 0
        assert any("exceed" in str(e).lower() for e in errors)

    def test_configuration_ai_cost_exceeds_limit(self):
        """Test validation when estimated AI cost exceeds limit."""
        config = TurnConfiguration(
            ai_integration_enabled=True,
            max_ai_cost=Decimal("0.01"),  # Very low limit
            participants=["agent_1"] * 100,  # Many participants
        )
        
        errors = config.validate_constraints()
        
        assert len(errors) > 0


class TestAuditAndEventConflicts:
    """Test suite for audit trail and event generation conflicts."""

    def test_audit_trail_recorded(self, sample_turn):
        """Test that audit events are recorded."""
        initial_count = len(sample_turn.audit_trail)
        
        sample_turn.start_planning()
        
        assert len(sample_turn.audit_trail) > initial_count

    def test_domain_events_generated(self, sample_turn):
        """Test that domain events are generated."""
        sample_turn.start_planning()
        
        # Events should be generated
        assert len(sample_turn.events_generated) > 0

    def test_event_type_in_audit(self, sample_turn):
        """Test that event types are recorded in audit."""
        sample_turn.start_planning()
        
        event_types = [e["event_type"] for e in sample_turn.audit_trail]
        assert any("state_transition" in str(et) or "turn" in str(et) for et in event_types)


class TestCompensationTypeConflicts:
    """Test suite for compensation type conflicts."""

    def test_compensation_type_is_destructive(self):
        """Test detection of destructive compensation types."""
        assert CompensationType.ROLLBACK_WORLD_STATE.is_destructive() is True
        assert CompensationType.REMOVE_EVENTS.is_destructive() is True
        assert CompensationType.CANCEL_INTERACTIONS.is_destructive() is True
        assert CompensationType.LOG_FAILURE.is_destructive() is False
        assert CompensationType.NOTIFY_PARTICIPANTS.is_destructive() is False

    def test_compensation_type_requires_confirmation(self):
        """Test detection of confirmation-required compensation types."""
        assert CompensationType.ROLLBACK_WORLD_STATE.requires_confirmation() is True
        assert CompensationType.REMOVE_EVENTS.requires_confirmation() is True
        assert CompensationType.TRIGGER_MANUAL_REVIEW.requires_confirmation() is True
        assert CompensationType.LOG_FAILURE.requires_confirmation() is False

    def test_compensation_type_get_severity(self):
        """Test getting compensation type severity."""
        assert CompensationType.ROLLBACK_WORLD_STATE.get_severity() == "critical"
        assert CompensationType.REMOVE_EVENTS.get_severity() == "critical"
        assert CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS.get_severity() == "high"
        assert CompensationType.LOG_FAILURE.get_severity() == "low"

    def test_get_phase_compensations(self):
        """Test getting appropriate compensations for phases."""
        world_compensations = CompensationType.get_phase_compensations("world_update")
        
        assert CompensationType.ROLLBACK_WORLD_STATE in world_compensations
        assert CompensationType.LOG_FAILURE in world_compensations

    def test_get_phase_compensations_unknown(self):
        """Test getting compensations for unknown phase."""
        compensations = CompensationType.get_phase_compensations("unknown_phase")
        
        assert compensations == [CompensationType.LOG_FAILURE]
