#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Negotiation Status Value Objects

Test suite covering negotiation phases, outcomes, status transitions, validation logic,
and state management in the Interaction Context domain layer.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from contexts.interactions.domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    NegotiationStatus,
    TerminationReason,
)


class TestNegotiationEnums:
    """Test suite for negotiation enumeration types."""

    def test_negotiation_phase_values(self):
        """Test NegotiationPhase enum values."""
        assert NegotiationPhase.INITIATION.value == "initiation"
        assert NegotiationPhase.PREPARATION.value == "preparation"
        assert NegotiationPhase.OPENING.value == "opening"
        assert NegotiationPhase.BARGAINING.value == "bargaining"
        assert NegotiationPhase.CLOSING.value == "closing"
        assert NegotiationPhase.IMPLEMENTATION.value == "implementation"
        assert NegotiationPhase.TERMINATED.value == "terminated"

    def test_negotiation_outcome_values(self):
        """Test NegotiationOutcome enum values."""
        assert NegotiationOutcome.PENDING.value == "pending"
        assert NegotiationOutcome.AGREEMENT_REACHED.value == "agreement_reached"
        assert NegotiationOutcome.PARTIAL_AGREEMENT.value == "partial_agreement"
        assert NegotiationOutcome.STALEMATE.value == "stalemate"
        assert NegotiationOutcome.WALKAWAY.value == "walkaway"
        assert NegotiationOutcome.TIMEOUT.value == "timeout"
        assert NegotiationOutcome.CANCELLED.value == "cancelled"

    def test_termination_reason_values(self):
        """Test TerminationReason enum values."""
        assert TerminationReason.MUTUAL_AGREEMENT.value == "mutual_agreement"
        assert TerminationReason.UNILATERAL_WITHDRAWAL.value == "unilateral_withdrawal"
        assert TerminationReason.TIMEOUT_EXCEEDED.value == "timeout_exceeded"
        assert (
            TerminationReason.IRRECONCILABLE_DIFFERENCES.value
            == "irreconcilable_differences"
        )
        assert TerminationReason.EXTERNAL_INTERVENTION.value == "external_intervention"
        assert TerminationReason.VIOLATION_OF_TERMS.value == "violation_of_terms"
        assert TerminationReason.FORCE_MAJEURE.value == "force_majeure"


class TestNegotiationStatusCreation:
    """Test suite for NegotiationStatus creation and basic functionality."""

    def test_minimal_status_creation(self):
        """Test creating NegotiationStatus with minimal required fields."""
        now = datetime.now(timezone.utc)

        status = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        assert status.phase == NegotiationPhase.INITIATION
        assert status.outcome == NegotiationOutcome.PENDING
        assert status.started_at == now
        assert status.last_activity_at == now
        assert status.expected_completion_at is None
        assert status.actual_completion_at is None
        assert status.termination_reason is None

    def test_full_status_creation(self):
        """Test creating NegotiationStatus with all optional fields."""
        now = datetime.now(timezone.utc)
        expected = now + timedelta(days=7)
        actual = now + timedelta(days=5)

        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=actual,
            expected_completion_at=expected,
            actual_completion_at=actual,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        assert status.phase == NegotiationPhase.TERMINATED
        assert status.outcome == NegotiationOutcome.AGREEMENT_REACHED
        assert status.started_at == now
        assert status.last_activity_at == actual
        assert status.expected_completion_at == expected
        assert status.actual_completion_at == actual
        assert status.termination_reason == TerminationReason.MUTUAL_AGREEMENT

    def test_frozen_dataclass_immutability(self):
        """Test that NegotiationStatus is immutable (frozen dataclass)."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            status.phase = NegotiationPhase.PREPARATION


class TestNegotiationStatusValidation:
    """Test suite for NegotiationStatus validation logic."""

    def test_timezone_validation_started_at(self):
        """Test validation fails with naive datetime for started_at."""
        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)  # No timezone
        aware_datetime = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="started_at must be timezone-aware"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=naive_datetime,
                last_activity_at=aware_datetime,
            )

    def test_timezone_validation_last_activity_at(self):
        """Test validation fails with naive datetime for last_activity_at."""
        aware_datetime = datetime.now(timezone.utc)
        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)  # No timezone

        with pytest.raises(ValueError, match="last_activity_at must be timezone-aware"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=aware_datetime,
                last_activity_at=naive_datetime,
            )

    def test_timezone_validation_expected_completion_at(self):
        """Test validation fails with naive datetime for expected_completion_at."""
        aware_datetime = datetime.now(timezone.utc)
        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)  # No timezone

        with pytest.raises(
            ValueError, match="expected_completion_at must be timezone-aware"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=aware_datetime,
                last_activity_at=aware_datetime,
                expected_completion_at=naive_datetime,
            )

    def test_timezone_validation_actual_completion_at(self):
        """Test validation fails with naive datetime for actual_completion_at."""
        aware_datetime = datetime.now(timezone.utc)
        naive_datetime = datetime(2023, 1, 1, 12, 0, 0)  # No timezone

        with pytest.raises(
            ValueError, match="actual_completion_at must be timezone-aware"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=aware_datetime,
                last_activity_at=aware_datetime,
                actual_completion_at=naive_datetime,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )

    def test_started_at_after_last_activity_validation(self):
        """Test validation fails when started_at is after last_activity_at."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        with pytest.raises(
            ValueError, match="started_at cannot be later than last_activity_at"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=earlier,
            )

    def test_started_at_after_expected_completion_validation(self):
        """Test validation fails when started_at is after expected_completion_at."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        with pytest.raises(
            ValueError, match="started_at cannot be later than expected_completion_at"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=now,
                expected_completion_at=earlier,
            )

    def test_started_at_after_actual_completion_validation(self):
        """Test validation fails when started_at is after actual_completion_at."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        with pytest.raises(
            ValueError, match="started_at cannot be later than actual_completion_at"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=earlier,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )

    def test_terminated_phase_with_pending_outcome_validation(self):
        """Test validation fails for terminated phase with pending outcome."""
        now = datetime.now(timezone.utc)

        with pytest.raises(
            ValueError, match="Terminated negotiations cannot have pending outcome"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=now,
            )

    def test_terminated_phase_without_termination_reason_validation(self):
        """Test validation fails for terminated phase without termination reason."""
        now = datetime.now(timezone.utc)

        with pytest.raises(
            ValueError, match="Terminated negotiations must have a termination reason"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=now,
            )

    def test_terminated_phase_without_actual_completion_validation(self):
        """Test validation fails for terminated phase without actual completion time."""
        now = datetime.now(timezone.utc)

        with pytest.raises(
            ValueError, match="Terminated negotiations must have actual completion time"
        ):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )

    def test_agreement_outcome_phase_consistency_validation(self):
        """Test validation for agreement outcomes in inappropriate phases."""
        now = datetime.now(timezone.utc)

        # Agreement reached should be in closing or implementation phase
        with pytest.raises(ValueError, match="inconsistent with phase"):
            NegotiationStatus(
                phase=NegotiationPhase.OPENING,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
            )

    def test_partial_agreement_outcome_phase_consistency_validation(self):
        """Test validation for partial agreement outcomes in inappropriate phases."""
        now = datetime.now(timezone.utc)

        # Partial agreement should be in closing or implementation phase
        with pytest.raises(ValueError, match="inconsistent with phase"):
            NegotiationStatus(
                phase=NegotiationPhase.BARGAINING,
                outcome=NegotiationOutcome.PARTIAL_AGREEMENT,
                started_at=now,
                last_activity_at=now,
            )


class TestNegotiationStatusFactoryMethods:
    """Test suite for NegotiationStatus factory methods."""

    def test_create_initial_default_time(self):
        """Test creating initial status with default timestamp."""
        with patch(
            "contexts.interactions.domain.value_objects.negotiation_status.datetime"
        ) as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now

            status = NegotiationStatus.create_initial()

            assert status.phase == NegotiationPhase.INITIATION
            assert status.outcome == NegotiationOutcome.PENDING
            assert status.started_at == mock_now
            assert status.last_activity_at == mock_now
            assert status.expected_completion_at is None
            assert status.actual_completion_at is None
            assert status.termination_reason is None

    def test_create_initial_specific_time(self):
        """Test creating initial status with specific timestamp."""
        specific_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        status = NegotiationStatus.create_initial(started_at=specific_time)

        assert status.phase == NegotiationPhase.INITIATION
        assert status.outcome == NegotiationOutcome.PENDING
        assert status.started_at == specific_time
        assert status.last_activity_at == specific_time

    def test_create_initial_with_expected_completion(self):
        """Test creating initial status with expected completion time."""
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        expected_completion = start_time + timedelta(days=7)

        status = NegotiationStatus.create_initial(
            started_at=start_time, expected_completion_at=expected_completion
        )

        assert status.started_at == start_time
        assert status.expected_completion_at == expected_completion


class TestNegotiationStatusPhaseTransitions:
    """Test suite for phase transition logic."""

    def test_valid_phase_transitions(self):
        """Test all valid phase transitions."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        # Valid transitions from INITIATION
        assert status._is_valid_phase_transition(
            NegotiationPhase.INITIATION, NegotiationPhase.PREPARATION
        )
        assert status._is_valid_phase_transition(
            NegotiationPhase.INITIATION, NegotiationPhase.TERMINATED
        )

        # Valid transitions from PREPARATION
        assert status._is_valid_phase_transition(
            NegotiationPhase.PREPARATION, NegotiationPhase.OPENING
        )
        assert status._is_valid_phase_transition(
            NegotiationPhase.PREPARATION, NegotiationPhase.TERMINATED
        )

        # Valid transitions from OPENING
        assert status._is_valid_phase_transition(
            NegotiationPhase.OPENING, NegotiationPhase.BARGAINING
        )
        assert status._is_valid_phase_transition(
            NegotiationPhase.OPENING, NegotiationPhase.TERMINATED
        )

        # Valid transitions from BARGAINING
        assert status._is_valid_phase_transition(
            NegotiationPhase.BARGAINING, NegotiationPhase.CLOSING
        )
        assert status._is_valid_phase_transition(
            NegotiationPhase.BARGAINING, NegotiationPhase.TERMINATED
        )

        # Valid transitions from CLOSING
        assert status._is_valid_phase_transition(
            NegotiationPhase.CLOSING, NegotiationPhase.IMPLEMENTATION
        )
        assert status._is_valid_phase_transition(
            NegotiationPhase.CLOSING, NegotiationPhase.TERMINATED
        )

        # Valid transitions from IMPLEMENTATION
        assert status._is_valid_phase_transition(
            NegotiationPhase.IMPLEMENTATION, NegotiationPhase.TERMINATED
        )

        # No valid transitions from TERMINATED
        assert not status._is_valid_phase_transition(
            NegotiationPhase.TERMINATED, NegotiationPhase.INITIATION
        )

    def test_invalid_phase_transitions(self):
        """Test invalid phase transitions."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        # Cannot skip phases
        assert not status._is_valid_phase_transition(
            NegotiationPhase.INITIATION, NegotiationPhase.BARGAINING
        )
        assert not status._is_valid_phase_transition(
            NegotiationPhase.PREPARATION, NegotiationPhase.CLOSING
        )

        # Cannot go backwards
        assert not status._is_valid_phase_transition(
            NegotiationPhase.BARGAINING, NegotiationPhase.OPENING
        )
        assert not status._is_valid_phase_transition(
            NegotiationPhase.CLOSING, NegotiationPhase.BARGAINING
        )

        # Cannot transition from terminal state
        assert not status._is_valid_phase_transition(
            NegotiationPhase.TERMINATED, NegotiationPhase.IMPLEMENTATION
        )

    def test_advance_to_phase_success(self):
        """Test successful phase advancement."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        activity_time = now + timedelta(hours=1)
        new_status = status.advance_to_phase(
            NegotiationPhase.PREPARATION, activity_time
        )

        assert new_status.phase == NegotiationPhase.PREPARATION
        assert new_status.outcome == NegotiationOutcome.PENDING  # Unchanged
        assert new_status.started_at == now  # Unchanged
        assert new_status.last_activity_at == activity_time
        assert (
            new_status.expected_completion_at == status.expected_completion_at
        )  # Unchanged

    def test_advance_to_phase_default_time(self):
        """Test phase advancement with default activity time."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        with patch(
            "contexts.interactions.domain.value_objects.negotiation_status.datetime"
        ) as mock_datetime:
            mock_now = now + timedelta(hours=1)
            mock_datetime.now.return_value = mock_now

            new_status = status.advance_to_phase(NegotiationPhase.PREPARATION)

            assert new_status.phase == NegotiationPhase.PREPARATION
            assert new_status.last_activity_at == mock_now

    def test_advance_to_phase_invalid_transition(self):
        """Test phase advancement with invalid transition."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        with pytest.raises(
            ValueError, match="Invalid phase transition from initiation to bargaining"
        ):
            status.advance_to_phase(NegotiationPhase.BARGAINING)


class TestNegotiationStatusCompletion:
    """Test suite for negotiation completion logic."""

    def test_complete_with_outcome_success(self):
        """Test successful negotiation completion."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        completion_time = now + timedelta(days=5)
        completed_status = status.complete_with_outcome(
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            completion_time=completion_time,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        assert completed_status.phase == NegotiationPhase.TERMINATED
        assert completed_status.outcome == NegotiationOutcome.AGREEMENT_REACHED
        assert completed_status.started_at == now  # Unchanged
        assert completed_status.last_activity_at == completion_time
        assert completed_status.actual_completion_at == completion_time
        assert completed_status.termination_reason == TerminationReason.MUTUAL_AGREEMENT

    def test_complete_with_outcome_default_time(self):
        """Test completion with default completion time."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        with patch(
            "contexts.interactions.domain.value_objects.negotiation_status.datetime"
        ) as mock_datetime:
            mock_completion = now + timedelta(days=5)
            mock_datetime.now.return_value = mock_completion

            completed_status = status.complete_with_outcome(
                outcome=NegotiationOutcome.STALEMATE,
                termination_reason=TerminationReason.IRRECONCILABLE_DIFFERENCES,
            )

            assert completed_status.actual_completion_at == mock_completion
            assert completed_status.last_activity_at == mock_completion

    def test_complete_different_outcomes(self):
        """Test completion with different outcome types."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        outcomes_reasons = [
            (NegotiationOutcome.AGREEMENT_REACHED, TerminationReason.MUTUAL_AGREEMENT),
            (NegotiationOutcome.PARTIAL_AGREEMENT, TerminationReason.MUTUAL_AGREEMENT),
            (
                NegotiationOutcome.STALEMATE,
                TerminationReason.IRRECONCILABLE_DIFFERENCES,
            ),
            (NegotiationOutcome.WALKAWAY, TerminationReason.UNILATERAL_WITHDRAWAL),
            (NegotiationOutcome.TIMEOUT, TerminationReason.TIMEOUT_EXCEEDED),
            (NegotiationOutcome.CANCELLED, TerminationReason.EXTERNAL_INTERVENTION),
        ]

        for outcome, reason in outcomes_reasons:
            completed_status = status.complete_with_outcome(
                outcome=outcome,
                completion_time=now + timedelta(hours=1),
                termination_reason=reason,
            )

            assert completed_status.outcome == outcome
            assert completed_status.termination_reason == reason
            assert completed_status.phase == NegotiationPhase.TERMINATED


class TestNegotiationStatusActivityUpdate:
    """Test suite for activity timestamp updates."""

    def test_update_last_activity_specific_time(self):
        """Test updating last activity with specific timestamp."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        activity_time = now + timedelta(hours=2)
        updated_status = status.update_last_activity(activity_time)

        # Only last_activity_at should change
        assert updated_status.phase == status.phase
        assert updated_status.outcome == status.outcome
        assert updated_status.started_at == status.started_at
        assert updated_status.last_activity_at == activity_time
        assert updated_status.expected_completion_at == status.expected_completion_at
        assert updated_status.actual_completion_at == status.actual_completion_at
        assert updated_status.termination_reason == status.termination_reason

    def test_update_last_activity_default_time(self):
        """Test updating last activity with default timestamp."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        with patch(
            "contexts.interactions.domain.value_objects.negotiation_status.datetime"
        ) as mock_datetime:
            mock_activity_time = now + timedelta(hours=3)
            mock_datetime.now.return_value = mock_activity_time

            updated_status = status.update_last_activity()

            assert updated_status.last_activity_at == mock_activity_time


class TestNegotiationStatusProperties:
    """Test suite for NegotiationStatus properties."""

    def test_is_active_property(self):
        """Test is_active property for different phases."""
        now = datetime.now(timezone.utc)

        # Active phases
        active_phases = [
            NegotiationPhase.INITIATION,
            NegotiationPhase.PREPARATION,
            NegotiationPhase.OPENING,
            NegotiationPhase.BARGAINING,
            NegotiationPhase.CLOSING,
            NegotiationPhase.IMPLEMENTATION,
        ]

        for phase in active_phases:
            status = NegotiationStatus(
                phase=phase,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=now,
            )
            assert status.is_active, f"Phase {phase.value} should be active"

        # Terminated phase is not active
        terminated_status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=now,
            actual_completion_at=now,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        assert not terminated_status.is_active

    def test_is_completed_property(self):
        """Test is_completed property for different outcomes."""
        now = datetime.now(timezone.utc)

        # Pending outcome is not completed
        pending_status = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )
        assert not pending_status.is_completed

        # All other outcomes are completed
        completed_outcomes = [
            NegotiationOutcome.AGREEMENT_REACHED,
            NegotiationOutcome.PARTIAL_AGREEMENT,
            NegotiationOutcome.STALEMATE,
            NegotiationOutcome.WALKAWAY,
            NegotiationOutcome.TIMEOUT,
            NegotiationOutcome.CANCELLED,
        ]

        for outcome in completed_outcomes:
            status = NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=outcome,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=now,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )
            assert status.is_completed, f"Outcome {outcome.value} should be completed"

    def test_duration_property(self):
        """Test duration property calculation."""
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        completion_time = datetime(
            2023, 1, 1, 15, 30, 0, tzinfo=timezone.utc
        )  # 3.5 hours later

        # Status with actual completion
        completed_status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=start_time,
            last_activity_at=completion_time,
            actual_completion_at=completion_time,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        expected_duration = int((completion_time - start_time).total_seconds())
        assert completed_status.duration == expected_duration
        assert completed_status.duration == 3.5 * 3600  # 3.5 hours in seconds

        # Status without completion has no duration
        active_status = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=start_time,
            last_activity_at=completion_time,
        )
        assert active_status.duration is None

    def test_time_since_last_activity_property(self):
        """Test time_since_last_activity property calculation."""
        # Mock current time for consistent testing
        mock_current_time = datetime(2023, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        last_activity = datetime(
            2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )  # 3 hours ago

        status = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=last_activity,
            last_activity_at=last_activity,
        )

        with patch(
            "contexts.interactions.domain.value_objects.negotiation_status.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = mock_current_time

            time_since_activity = status.time_since_last_activity
            expected_seconds = int((mock_current_time - last_activity).total_seconds())

            assert time_since_activity == expected_seconds
            assert time_since_activity == 3 * 3600  # 3 hours in seconds


class TestNegotiationStatusEquality:
    """Test suite for NegotiationStatus equality comparison."""

    def test_equality_same_values(self):
        """Test equality with identical values."""
        now = datetime.now(timezone.utc)
        expected = now + timedelta(days=1)
        actual = now + timedelta(hours=20)

        status1 = NegotiationStatus(
            phase=NegotiationPhase.CLOSING,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=actual,
            expected_completion_at=expected,
            actual_completion_at=actual,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        status2 = NegotiationStatus(
            phase=NegotiationPhase.CLOSING,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=actual,
            expected_completion_at=expected,
            actual_completion_at=actual,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        assert status1 == status2
        assert not (status1 != status2)

    def test_equality_different_phases(self):
        """Test inequality with different phases."""
        now = datetime.now(timezone.utc)

        status1 = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        status2 = NegotiationStatus(
            phase=NegotiationPhase.CLOSING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        assert status1 != status2
        assert not (status1 == status2)

    def test_equality_different_timestamps(self):
        """Test inequality with different timestamps."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        status1 = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        status2 = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=earlier,
            last_activity_at=earlier,
        )

        assert status1 != status2

    def test_equality_with_non_negotiation_status(self):
        """Test equality comparison with non-NegotiationStatus objects."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        # Should not be equal to other types
        assert status != "string"
        assert status != 123
        assert status is not None
        assert status != {}
        assert status != []
        assert not (status == "string")


class TestNegotiationStatusStringRepresentation:
    """Test suite for NegotiationStatus string representation."""

    def test_str_representation(self):
        """Test string representation of NegotiationStatus."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        str_repr = str(status)
        assert str_repr == "NegotiationStatus(phase=bargaining, outcome=pending)"
        assert isinstance(str_repr, str)

    def test_str_representation_completed(self):
        """Test string representation of completed negotiation."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=now,
            actual_completion_at=now,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        str_repr = str(status)
        assert (
            str_repr == "NegotiationStatus(phase=terminated, outcome=agreement_reached)"
        )


class TestNegotiationStatusEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_same_start_and_activity_time(self):
        """Test status with identical start and activity times."""
        now = datetime.now(timezone.utc)

        status = NegotiationStatus(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )

        assert status.started_at == status.last_activity_at
        assert status.duration is None
        assert status.is_active
        assert not status.is_completed

    def test_immediate_completion(self):
        """Test negotiation completed immediately after start."""
        now = datetime.now(timezone.utc)

        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.CANCELLED,
            started_at=now,
            last_activity_at=now,
            actual_completion_at=now,
            termination_reason=TerminationReason.EXTERNAL_INTERVENTION,
        )

        assert status.duration == 0
        assert not status.is_active
        assert status.is_completed

    def test_very_long_negotiation(self):
        """Test negotiation with very long duration."""
        start_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        completion_time = datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )  # 1 year later

        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=start_time,
            last_activity_at=completion_time,
            actual_completion_at=completion_time,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )

        expected_duration = 365 * 24 * 3600  # 1 year in seconds
        assert status.duration == expected_duration

    def test_microsecond_precision_timestamps(self):
        """Test negotiation status with microsecond-precision timestamps."""
        start_time = datetime(2023, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
        activity_time = datetime(2023, 1, 1, 12, 0, 0, 789012, tzinfo=timezone.utc)

        status = NegotiationStatus(
            phase=NegotiationPhase.OPENING,
            outcome=NegotiationOutcome.PENDING,
            started_at=start_time,
            last_activity_at=activity_time,
        )

        assert status.started_at.microsecond == 123456
        assert status.last_activity_at.microsecond == 789012

    def test_phase_transition_edge_cases(self):
        """Test edge cases in phase transition validation."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus.create_initial(started_at=now)

        # Same phase "transition" should be invalid
        assert not status._is_valid_phase_transition(
            NegotiationPhase.INITIATION, NegotiationPhase.INITIATION
        )

        # Direct to terminated from any phase should be valid
        for phase in [
            NegotiationPhase.INITIATION,
            NegotiationPhase.PREPARATION,
            NegotiationPhase.OPENING,
            NegotiationPhase.BARGAINING,
            NegotiationPhase.CLOSING,
            NegotiationPhase.IMPLEMENTATION,
        ]:
            assert status._is_valid_phase_transition(phase, NegotiationPhase.TERMINATED)

    def test_outcome_phase_consistency_edge_cases(self):
        """Test edge cases in outcome-phase consistency validation."""
        now = datetime.now(timezone.utc)

        # Agreement in closing phase should be valid
        status_closing = NegotiationStatus(
            phase=NegotiationPhase.CLOSING,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=now,
        )
        # Should not raise exception
        assert status_closing.phase == NegotiationPhase.CLOSING

        # Agreement in implementation phase should be valid
        status_implementation = NegotiationStatus(
            phase=NegotiationPhase.IMPLEMENTATION,
            outcome=NegotiationOutcome.PARTIAL_AGREEMENT,
            started_at=now,
            last_activity_at=now,
        )
        # Should not raise exception
        assert status_implementation.phase == NegotiationPhase.IMPLEMENTATION
