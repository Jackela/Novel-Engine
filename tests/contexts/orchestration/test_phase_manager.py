#!/usr/bin/env python3
"""
Tests for Phase Management (PhaseType, PhaseStatus, PhaseStatusEnum).

This module contains comprehensive tests for phase status management
including state transitions, validation, and utility methods.
"""

from datetime import datetime, timedelta

import pytest

from src.contexts.orchestration.domain.value_objects.phase_status import (
    PhaseStatus,
    PhaseStatusEnum,
    PhaseType,
)

pytestmark = pytest.mark.unit


class TestPhaseType:
    """Test suite for PhaseType enumeration."""

    def test_phase_type_values(self):
        """Test phase type enumeration values."""
        assert PhaseType.WORLD_UPDATE.value == "world_update"
        assert PhaseType.SUBJECTIVE_BRIEF.value == "subjective_brief"
        assert PhaseType.INTERACTION_ORCHESTRATION.value == "interaction_orchestration"
        assert PhaseType.EVENT_INTEGRATION.value == "event_integration"
        assert PhaseType.NARRATIVE_INTEGRATION.value == "narrative_integration"

    def test_phase_type_str(self):
        """Test phase type string representation."""
        assert str(PhaseType.WORLD_UPDATE) == "world_update"

    def test_get_display_name(self):
        """Test getting human-readable display names."""
        assert PhaseType.WORLD_UPDATE.get_display_name() == "World State Update"
        assert (
            PhaseType.SUBJECTIVE_BRIEF.get_display_name()
            == "Subjective Brief Generation"
        )
        assert (
            PhaseType.INTERACTION_ORCHESTRATION.get_display_name()
            == "Interaction Orchestration"
        )
        assert PhaseType.EVENT_INTEGRATION.get_display_name() == "Event Integration"
        assert (
            PhaseType.NARRATIVE_INTEGRATION.get_display_name()
            == "Narrative Integration"
        )

    def test_get_phase_order(self):
        """Test phase ordering."""
        assert PhaseType.WORLD_UPDATE.get_phase_order() == 1
        assert PhaseType.SUBJECTIVE_BRIEF.get_phase_order() == 2
        assert PhaseType.INTERACTION_ORCHESTRATION.get_phase_order() == 3
        assert PhaseType.EVENT_INTEGRATION.get_phase_order() == 4
        assert PhaseType.NARRATIVE_INTEGRATION.get_phase_order() == 5

    def test_get_next_phase(self):
        """Test getting next phase in sequence."""
        assert PhaseType.WORLD_UPDATE.get_next_phase() == PhaseType.SUBJECTIVE_BRIEF
        assert (
            PhaseType.SUBJECTIVE_BRIEF.get_next_phase()
            == PhaseType.INTERACTION_ORCHESTRATION
        )
        assert (
            PhaseType.INTERACTION_ORCHESTRATION.get_next_phase()
            == PhaseType.EVENT_INTEGRATION
        )
        assert (
            PhaseType.EVENT_INTEGRATION.get_next_phase()
            == PhaseType.NARRATIVE_INTEGRATION
        )
        assert PhaseType.NARRATIVE_INTEGRATION.get_next_phase() is None

    def test_get_previous_phase(self):
        """Test getting previous phase in sequence."""
        assert PhaseType.WORLD_UPDATE.get_previous_phase() is None
        assert PhaseType.SUBJECTIVE_BRIEF.get_previous_phase() == PhaseType.WORLD_UPDATE
        assert (
            PhaseType.INTERACTION_ORCHESTRATION.get_previous_phase()
            == PhaseType.SUBJECTIVE_BRIEF
        )
        assert (
            PhaseType.EVENT_INTEGRATION.get_previous_phase()
            == PhaseType.INTERACTION_ORCHESTRATION
        )
        assert (
            PhaseType.NARRATIVE_INTEGRATION.get_previous_phase()
            == PhaseType.EVENT_INTEGRATION
        )

    def test_get_all_phases_ordered(self):
        """Test getting all phases in order."""
        phases = PhaseType.get_all_phases_ordered()

        assert len(phases) == 5
        assert phases[0] == PhaseType.WORLD_UPDATE
        assert phases[1] == PhaseType.SUBJECTIVE_BRIEF
        assert phases[2] == PhaseType.INTERACTION_ORCHESTRATION
        assert phases[3] == PhaseType.EVENT_INTEGRATION
        assert phases[4] == PhaseType.NARRATIVE_INTEGRATION


class TestPhaseStatusEnum:
    """Test suite for PhaseStatusEnum enumeration."""

    def test_status_values(self):
        """Test status enumeration values."""
        assert PhaseStatusEnum.PENDING.value == "pending"
        assert PhaseStatusEnum.RUNNING.value == "running"
        assert PhaseStatusEnum.COMPLETED.value == "completed"
        assert PhaseStatusEnum.FAILED.value == "failed"
        assert PhaseStatusEnum.COMPENSATING.value == "compensating"
        assert PhaseStatusEnum.COMPENSATED.value == "compensated"
        assert PhaseStatusEnum.SKIPPED.value == "skipped"

    def test_status_str(self):
        """Test status string representation."""
        assert str(PhaseStatusEnum.PENDING) == "pending"

    def test_is_terminal(self):
        """Test terminal status detection."""
        assert PhaseStatusEnum.COMPLETED.is_terminal() is True
        assert PhaseStatusEnum.FAILED.is_terminal() is True
        assert PhaseStatusEnum.COMPENSATED.is_terminal() is True
        assert PhaseStatusEnum.SKIPPED.is_terminal() is True
        assert PhaseStatusEnum.PENDING.is_terminal() is False
        assert PhaseStatusEnum.RUNNING.is_terminal() is False
        assert PhaseStatusEnum.COMPENSATING.is_terminal() is False

    def test_is_active(self):
        """Test active status detection."""
        assert PhaseStatusEnum.RUNNING.is_active() is True
        assert PhaseStatusEnum.COMPENSATING.is_active() is True
        assert PhaseStatusEnum.PENDING.is_active() is False
        assert PhaseStatusEnum.COMPLETED.is_active() is False
        assert PhaseStatusEnum.FAILED.is_active() is False

    def test_is_successful(self):
        """Test successful status detection."""
        assert PhaseStatusEnum.COMPLETED.is_successful() is True
        assert PhaseStatusEnum.PENDING.is_successful() is False
        assert PhaseStatusEnum.FAILED.is_successful() is False

    def test_is_failure(self):
        """Test failure status detection."""
        assert PhaseStatusEnum.FAILED.is_failure() is True
        assert PhaseStatusEnum.COMPENSATED.is_failure() is True
        assert PhaseStatusEnum.COMPLETED.is_failure() is False
        assert PhaseStatusEnum.PENDING.is_failure() is False

    def test_can_transition_to_valid(self):
        """Test valid status transitions."""
        # PENDING can go to RUNNING or SKIPPED
        assert (
            PhaseStatusEnum.PENDING.can_transition_to(PhaseStatusEnum.RUNNING) is True
        )
        assert (
            PhaseStatusEnum.PENDING.can_transition_to(PhaseStatusEnum.SKIPPED) is True
        )

        # RUNNING can go to COMPLETED or FAILED
        assert (
            PhaseStatusEnum.RUNNING.can_transition_to(PhaseStatusEnum.COMPLETED) is True
        )
        assert PhaseStatusEnum.RUNNING.can_transition_to(PhaseStatusEnum.FAILED) is True

        # COMPLETED can go to COMPENSATING
        assert (
            PhaseStatusEnum.COMPLETED.can_transition_to(PhaseStatusEnum.COMPENSATING)
            is True
        )

        # FAILED can go to COMPENSATING or COMPENSATED
        assert (
            PhaseStatusEnum.FAILED.can_transition_to(PhaseStatusEnum.COMPENSATING)
            is True
        )
        assert (
            PhaseStatusEnum.FAILED.can_transition_to(PhaseStatusEnum.COMPENSATED)
            is True
        )

    def test_can_transition_to_invalid(self):
        """Test invalid status transitions."""
        # PENDING cannot go directly to COMPLETED
        assert (
            PhaseStatusEnum.PENDING.can_transition_to(PhaseStatusEnum.COMPLETED)
            is False
        )

        # COMPLETED cannot go back to RUNNING
        assert (
            PhaseStatusEnum.COMPLETED.can_transition_to(PhaseStatusEnum.RUNNING)
            is False
        )

        # TERMINAL states cannot transition
        assert (
            PhaseStatusEnum.COMPENSATED.can_transition_to(PhaseStatusEnum.PENDING)
            is False
        )
        assert (
            PhaseStatusEnum.SKIPPED.can_transition_to(PhaseStatusEnum.RUNNING) is False
        )


class TestPhaseStatusCreation:
    """Test suite for PhaseStatus creation."""

    def test_create_pending(self):
        """Test creating pending phase status."""
        status = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        assert status.phase_type == PhaseType.WORLD_UPDATE
        assert status.status == PhaseStatusEnum.PENDING
        assert status.progress_percentage == 0
        assert status.events_processed == 0

    def test_create_running(self):
        """Test creating running phase status."""
        started_at = datetime.now()
        status = PhaseStatus.create_running(PhaseType.SUBJECTIVE_BRIEF, started_at)

        assert status.phase_type == PhaseType.SUBJECTIVE_BRIEF
        assert status.status == PhaseStatusEnum.RUNNING
        assert status.started_at == started_at

    def test_create_running_default_time(self):
        """Test creating running phase status with default time."""
        status = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)

        assert status.status == PhaseStatusEnum.RUNNING
        assert status.started_at is not None

    def test_create_completed(self):
        """Test creating completed phase status."""
        started_at = datetime.now()
        status = PhaseStatus.create_completed(
            phase_type=PhaseType.EVENT_INTEGRATION,
            started_at=started_at,
            events_processed=42,
            metadata={"test": "data"},
        )

        assert status.phase_type == PhaseType.EVENT_INTEGRATION
        assert status.status == PhaseStatusEnum.COMPLETED
        assert status.progress_percentage == 100
        assert status.events_processed == 42
        assert status.completed_at is not None
        assert status.metadata == {"test": "data"}

    def test_create_failed(self):
        """Test creating failed phase status."""
        status = PhaseStatus.create_failed(
            phase_type=PhaseType.NARRATIVE_INTEGRATION,
            error_message="Test failure",
            progress_percentage=50,
        )

        assert status.phase_type == PhaseType.NARRATIVE_INTEGRATION
        assert status.status == PhaseStatusEnum.FAILED
        assert status.error_message == "Test failure"
        assert status.progress_percentage == 50
        assert status.completed_at is not None


class TestPhaseStatusValidation:
    """Test suite for PhaseStatus validation."""

    def test_validation_progress_percentage_range(self):
        """Test progress percentage range validation."""
        with pytest.raises(ValueError, match="progress_percentage must be between"):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.PENDING,
                progress_percentage=-1,
            )

    def test_validation_progress_percentage_max(self):
        """Test progress percentage maximum validation."""
        with pytest.raises(ValueError, match="progress_percentage must be between"):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.PENDING,
                progress_percentage=101,
            )

    def test_validation_events_processed_negative(self):
        """Test negative events processed validation."""
        with pytest.raises(ValueError, match="events_processed cannot be negative"):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.PENDING,
                events_processed=-1,
            )

    def test_validation_completed_without_timestamp(self):
        """Test completed status requires timestamp."""
        with pytest.raises(
            ValueError, match="Completed phases must have completion timestamp"
        ):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.COMPLETED,
                progress_percentage=100,
            )

    def test_validation_completed_without_full_progress(self):
        """Test completed status requires 100% progress."""
        with pytest.raises(
            ValueError, match="Completed phases must have 100% progress"
        ):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.COMPLETED,
                progress_percentage=90,
                completed_at=datetime.now(),
            )

    def test_validation_failed_without_error_message(self):
        """Test failed status requires error message."""
        with pytest.raises(ValueError, match="Failed phases must have error message"):
            PhaseStatus(
                phase_type=PhaseType.WORLD_UPDATE,
                status=PhaseStatusEnum.FAILED,
                completed_at=datetime.now(),
            )

    def test_duration_calculation(self):
        """Test automatic duration calculation."""
        started_at = datetime.now()
        completed_at = started_at + timedelta(seconds=5)

        status = PhaseStatus(
            phase_type=PhaseType.WORLD_UPDATE,
            status=PhaseStatusEnum.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            progress_percentage=100,
        )

        assert status.duration_ms == 5000


class TestPhaseStatusTransitions:
    """Test suite for PhaseStatus transitions."""

    def test_transition_to_running(self):
        """Test transition to running state."""
        pending = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)
        running = pending.transition_to(PhaseStatusEnum.RUNNING)

        assert running.status == PhaseStatusEnum.RUNNING
        assert running.started_at is not None

    def test_transition_to_completed(self):
        """Test transition to completed state."""
        running = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)
        completed = running.transition_to(
            PhaseStatusEnum.COMPLETED,
            events_processed=10,
        )

        assert completed.status == PhaseStatusEnum.COMPLETED
        assert completed.progress_percentage == 100
        assert completed.completed_at is not None

    def test_transition_to_failed(self):
        """Test transition to failed state."""
        running = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)
        failed = running.transition_to(
            PhaseStatusEnum.FAILED,
            error_message="Test error",
            progress_percentage=50,
        )

        assert failed.status == PhaseStatusEnum.FAILED
        assert failed.error_message == "Test error"
        assert failed.completed_at is not None

    def test_invalid_transition(self):
        """Test invalid status transition raises error."""
        pending = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        with pytest.raises(ValueError, match="Invalid status transition"):
            pending.transition_to(PhaseStatusEnum.COMPLETED)

    def test_transition_preserves_fields(self):
        """Test that transitions preserve existing fields."""
        started_at = datetime.now()
        running = PhaseStatus.create_running(PhaseType.WORLD_UPDATE, started_at)
        completed = running.transition_to(
            PhaseStatusEnum.COMPLETED,
            events_processed=42,
        )

        assert completed.started_at == started_at
        assert completed.phase_type == PhaseType.WORLD_UPDATE


class TestPhaseStatusUpdates:
    """Test suite for PhaseStatus updates."""

    def test_update_progress(self):
        """Test updating progress without changing status."""
        running = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)
        updated = running.update_progress(
            progress_percentage=50,
            events_processed=25,
            metadata={"checkpoint": "halfway"},
        )

        assert updated.status == PhaseStatusEnum.RUNNING
        assert updated.progress_percentage == 50
        assert updated.events_processed == 25
        assert updated.metadata == {"checkpoint": "halfway"}

    def test_update_progress_no_events(self):
        """Test updating progress without events."""
        running = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)
        updated = running.update_progress(progress_percentage=75)

        assert updated.progress_percentage == 75


class TestPhaseStatusQueries:
    """Test suite for PhaseStatus query methods."""

    def test_get_execution_time_completed(self):
        """Test getting execution time for completed phase."""
        started_at = datetime.now()
        completed_at = started_at + timedelta(seconds=10)

        status = PhaseStatus(
            phase_type=PhaseType.WORLD_UPDATE,
            status=PhaseStatusEnum.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            progress_percentage=100,
        )

        execution_time = status.get_execution_time()

        assert execution_time is not None
        assert execution_time.total_seconds() == 10

    def test_get_execution_time_running(self):
        """Test getting execution time for running phase."""
        started_at = datetime.now() - timedelta(seconds=5)

        status = PhaseStatus.create_running(PhaseType.WORLD_UPDATE, started_at)

        execution_time = status.get_execution_time()

        assert execution_time is not None
        assert execution_time.total_seconds() >= 5

    def test_get_execution_time_pending(self):
        """Test getting execution time for pending phase."""
        pending = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        execution_time = pending.get_execution_time()

        assert execution_time is None

    def test_is_overdue_true(self):
        """Test overdue detection (true case)."""
        started_at = datetime.now() - timedelta(seconds=100)

        status = PhaseStatus.create_running(PhaseType.WORLD_UPDATE, started_at)

        assert status.is_overdue(timeout_seconds=50) is True

    def test_is_overdue_false(self):
        """Test overdue detection (false case)."""
        started_at = datetime.now() - timedelta(seconds=10)

        status = PhaseStatus.create_running(PhaseType.WORLD_UPDATE, started_at)

        assert status.is_overdue(timeout_seconds=50) is False

    def test_is_overdue_terminal(self):
        """Test overdue detection for terminal status."""
        status = PhaseStatus.create_completed(
            PhaseType.WORLD_UPDATE,
            datetime.now(),
        )

        assert status.is_overdue(timeout_seconds=1) is False


class TestPhaseStatusDisplay:
    """Test suite for PhaseStatus display methods."""

    def test_get_display_summary_successful(self):
        """Test display summary for successful phase."""
        started_at = datetime.now()
        completed_at = started_at + timedelta(milliseconds=1500)

        status = PhaseStatus(
            phase_type=PhaseType.WORLD_UPDATE,
            status=PhaseStatusEnum.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=1500,
            progress_percentage=100,
            events_processed=42,
        )

        summary = status.get_display_summary()

        assert "World State Update" in summary
        assert "Completed" in summary
        assert "1500ms" in summary
        assert "42 events" in summary

    def test_get_display_summary_failed(self):
        """Test display summary for failed phase."""
        status = PhaseStatus.create_failed(
            PhaseType.WORLD_UPDATE,
            error_message="Database connection failed",
        )

        summary = status.get_display_summary()

        assert "World State Update" in summary
        assert "Failed" in summary
        assert "Database connection failed" in summary

    def test_get_display_summary_running(self):
        """Test display summary for running phase."""
        status = PhaseStatus.create_running(PhaseType.WORLD_UPDATE)
        updated = status.update_progress(progress_percentage=75)

        summary = updated.get_display_summary()

        assert "World State Update" in summary
        assert "Running" in summary
        assert "75%" in summary

    def test_str(self):
        """Test string representation."""
        status = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        assert str(status) == "world_update:pending"

    def test_repr(self):
        """Test detailed representation."""
        status = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        repr_str = repr(status)

        assert "PhaseStatus" in repr_str
        assert "world_update" in repr_str
        assert "pending" in repr_str


class TestPhaseStatusImmutability:
    """Test suite for PhaseStatus immutability."""

    def test_fields_immutable(self):
        """Test that phase status fields are immutable."""
        status = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)

        with pytest.raises(AttributeError):
            status.status = PhaseStatusEnum.RUNNING

    def test_new_instance_on_transition(self):
        """Test that transitions create new instances."""
        pending = PhaseStatus.create_pending(PhaseType.WORLD_UPDATE)
        running = pending.transition_to(PhaseStatusEnum.RUNNING)

        assert pending is not running
        assert pending.status == PhaseStatusEnum.PENDING
        assert running.status == PhaseStatusEnum.RUNNING
