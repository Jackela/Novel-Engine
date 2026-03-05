#!/usr/bin/env python3
"""
Tests for Outcome Calculator (NegotiationStatus, NegotiationOutcome, etc.).

This module contains comprehensive tests for outcome calculation and status
management in negotiation sessions.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from src.contexts.interactions.domain.value_objects.negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    NegotiationStatus,
    TerminationReason,
)
from src.contexts.interactions.domain.value_objects.proposal_response import (
    ConfidenceLevel,
    ProposalResponse,
    ResponseReason,
    ResponseType,
    TermResponse,
)


class TestNegotiationPhase:
    """Test suite for NegotiationPhase enumeration."""

    def test_phase_values(self):
        """Test phase enumeration values."""
        assert NegotiationPhase.INITIATION.value == "initiation"
        assert NegotiationPhase.PREPARATION.value == "preparation"
        assert NegotiationPhase.OPENING.value == "opening"
        assert NegotiationPhase.BARGAINING.value == "bargaining"
        assert NegotiationPhase.CLOSING.value == "closing"
        assert NegotiationPhase.IMPLEMENTATION.value == "implementation"
        assert NegotiationPhase.TERMINATED.value == "terminated"


class TestNegotiationOutcome:
    """Test suite for NegotiationOutcome enumeration."""

    def test_outcome_values(self):
        """Test outcome enumeration values."""
        assert NegotiationOutcome.PENDING.value == "pending"
        assert NegotiationOutcome.AGREEMENT_REACHED.value == "agreement_reached"
        assert NegotiationOutcome.PARTIAL_AGREEMENT.value == "partial_agreement"
        assert NegotiationOutcome.STALEMATE.value == "stalemate"
        assert NegotiationOutcome.WALKAWAY.value == "walkaway"
        assert NegotiationOutcome.TIMEOUT.value == "timeout"
        assert NegotiationOutcome.CANCELLED.value == "cancelled"


class TestTerminationReason:
    """Test suite for TerminationReason enumeration."""

    def test_reason_values(self):
        """Test termination reason enumeration values."""
        assert TerminationReason.MUTUAL_AGREEMENT.value == "mutual_agreement"
        assert TerminationReason.UNILATERAL_WITHDRAWAL.value == "unilateral_withdrawal"
        assert TerminationReason.TIMEOUT_EXCEEDED.value == "timeout_exceeded"
        assert TerminationReason.IRRECONCILABLE_DIFFERENCES.value == "irreconcilable_differences"
        assert TerminationReason.EXTERNAL_INTERVENTION.value == "external_intervention"
        assert TerminationReason.VIOLATION_OF_TERMS.value == "violation_of_terms"
        assert TerminationReason.FORCE_MAJEURE.value == "force_majeure"


class TestNegotiationStatusCreation:
    """Test suite for NegotiationStatus creation."""

    def test_create_initial(self):
        """Test creating initial negotiation status."""
        status = NegotiationStatus.create_initial()
        
        assert status.phase == NegotiationPhase.INITIATION
        assert status.outcome == NegotiationOutcome.PENDING
        assert status.started_at is not None
        assert status.last_activity_at == status.started_at

    def test_create_initial_with_times(self):
        """Test creating initial status with specific times."""
        started_at = datetime.now(timezone.utc)
        expected_completion = started_at + timedelta(hours=48)
        
        status = NegotiationStatus.create_initial(
            started_at=started_at,
            expected_completion_at=expected_completion,
        )
        
        assert status.started_at == started_at
        assert status.expected_completion_at == expected_completion

    def test_create_full_status(self):
        """Test creating full negotiation status."""
        now = datetime.now(timezone.utc)
        completed_at = now + timedelta(hours=2)
        
        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=completed_at,
            expected_completion_at=now + timedelta(hours=3),
            actual_completion_at=completed_at,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        
        assert status.phase == NegotiationPhase.TERMINATED
        assert status.outcome == NegotiationOutcome.AGREEMENT_REACHED
        assert status.termination_reason == TerminationReason.MUTUAL_AGREEMENT


class TestNegotiationStatusValidation:
    """Test suite for NegotiationStatus validation."""

    def test_validation_naive_started_at(self):
        """Test validation with naive started_at."""
        with pytest.raises(ValueError, match="timezone-aware"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=datetime.now(),  # Naive
                last_activity_at=datetime.now(timezone.utc),
            )

    def test_validation_naive_last_activity(self):
        """Test validation with naive last_activity_at."""
        with pytest.raises(ValueError, match="timezone-aware"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(),  # Naive
            )

    def test_validation_started_after_last_activity(self):
        """Test validation when started_at is after last_activity_at."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="started_at cannot be later"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=now + timedelta(hours=1),
                last_activity_at=now,
            )

    def test_validation_started_after_expected_completion(self):
        """Test validation when started_at is after expected_completion."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="started_at cannot be later"):
            NegotiationStatus(
                phase=NegotiationPhase.INITIATION,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=now,
                expected_completion_at=now - timedelta(hours=1),
            )

    def test_validation_terminated_without_outcome(self):
        """Test validation for terminated without proper outcome."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="cannot have pending outcome"):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.PENDING,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=now,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )

    def test_validation_terminated_without_reason(self):
        """Test validation for terminated without termination reason."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="must have a termination reason"):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=now,
                termination_reason=None,
            )

    def test_validation_terminated_without_completion_time(self):
        """Test validation for terminated without completion time."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="must have actual completion time"):
            NegotiationStatus(
                phase=NegotiationPhase.TERMINATED,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=None,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )

    def test_validation_agreement_without_closing_phase(self):
        """Test validation for agreement reached without closing phase."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="inconsistent with phase"):
            NegotiationStatus(
                phase=NegotiationPhase.BARGAINING,
                outcome=NegotiationOutcome.AGREEMENT_REACHED,
                started_at=now,
                last_activity_at=now,
                actual_completion_at=now,
                termination_reason=TerminationReason.MUTUAL_AGREEMENT,
            )


class TestNegotiationStatusTransitions:
    """Test suite for NegotiationStatus phase transitions."""

    def test_advance_to_phase_valid(self):
        """Test valid phase advancement."""
        status = NegotiationStatus.create_initial()
        new_status = status.advance_to_phase(NegotiationPhase.PREPARATION)
        
        assert new_status.phase == NegotiationPhase.PREPARATION
        assert status.phase == NegotiationPhase.INITIATION  # Original unchanged

    def test_advance_to_phase_invalid(self):
        """Test invalid phase advancement."""
        status = NegotiationStatus.create_initial()
        
        with pytest.raises(ValueError, match="Invalid phase transition"):
            status.advance_to_phase(NegotiationPhase.CLOSING)

    def test_advance_to_phase_with_time(self):
        """Test phase advancement with specific time."""
        status = NegotiationStatus.create_initial()
        new_time = datetime.now(timezone.utc)
        
        new_status = status.advance_to_phase(
            NegotiationPhase.PREPARATION,
            activity_time=new_time
        )
        
        assert new_status.last_activity_at == new_time

    def test_complete_with_outcome(self):
        """Test completing negotiation with outcome."""
        status = NegotiationStatus.create_initial()
        completed = status.complete_with_outcome(
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        
        assert completed.phase == NegotiationPhase.TERMINATED
        assert completed.outcome == NegotiationOutcome.AGREEMENT_REACHED
        assert completed.termination_reason == TerminationReason.MUTUAL_AGREEMENT
        assert completed.actual_completion_at is not None

    def test_update_last_activity(self):
        """Test updating last activity timestamp."""
        status = NegotiationStatus.create_initial()
        new_time = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        updated = status.update_last_activity(new_time)
        
        assert updated.last_activity_at == new_time
        assert updated.phase == status.phase  # Phase unchanged

    def test_update_last_activity_default_time(self):
        """Test updating last activity with default time."""
        status = NegotiationStatus.create_initial()
        
        updated = status.update_last_activity()
        
        assert updated.last_activity_at >= status.last_activity_at


class TestNegotiationStatusQueries:
    """Test suite for NegotiationStatus query methods."""

    def test_is_active_true(self):
        """Test active status detection (true)."""
        status = NegotiationStatus.create_initial()
        
        assert status.is_active is True

    def test_is_active_false(self):
        """Test active status detection (false)."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=now,
            actual_completion_at=now,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        
        assert status.is_active is False

    def test_is_completed_true(self):
        """Test completed status detection (true)."""
        now = datetime.now(timezone.utc)
        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=now,
            actual_completion_at=now,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        
        assert status.is_completed is True

    def test_is_completed_false(self):
        """Test completed status detection (false)."""
        status = NegotiationStatus.create_initial()
        
        assert status.is_completed is False

    def test_duration_completed(self):
        """Test getting duration for completed negotiation."""
        now = datetime.now(timezone.utc)
        completed_at = now + timedelta(hours=2)
        
        status = NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=NegotiationOutcome.AGREEMENT_REACHED,
            started_at=now,
            last_activity_at=completed_at,
            actual_completion_at=completed_at,
            termination_reason=TerminationReason.MUTUAL_AGREEMENT,
        )
        
        assert status.duration == 7200  # 2 hours in seconds

    def test_duration_in_progress(self):
        """Test getting duration for in-progress negotiation."""
        status = NegotiationStatus.create_initial()
        
        assert status.duration is None

    def test_time_since_last_activity(self):
        """Test getting time since last activity."""
        now = datetime.now(timezone.utc)
        last_activity = now - timedelta(minutes=30)
        
        status = NegotiationStatus(
            phase=NegotiationPhase.OPENING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now - timedelta(hours=1),
            last_activity_at=last_activity,
        )
        
        # Should be approximately 30 minutes (1800 seconds)
        assert 1700 <= status.time_since_last_activity <= 1900


class TestNegotiationStatusEquality:
    """Test suite for NegotiationStatus equality."""

    def test_equality_same(self):
        """Test equality of identical statuses."""
        now = datetime.now(timezone.utc)
        
        status1 = NegotiationStatus(
            phase=NegotiationPhase.OPENING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )
        
        status2 = NegotiationStatus(
            phase=NegotiationPhase.OPENING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )
        
        assert status1 == status2

    def test_equality_different(self):
        """Test inequality of different statuses."""
        now = datetime.now(timezone.utc)
        
        status1 = NegotiationStatus(
            phase=NegotiationPhase.OPENING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )
        
        status2 = NegotiationStatus(
            phase=NegotiationPhase.BARGAINING,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
        )
        
        assert status1 != status2

    def test_equality_different_type(self):
        """Test equality with different type."""
        status = NegotiationStatus.create_initial()
        
        assert status != "not a status"

    def test_str(self):
        """Test string representation."""
        status = NegotiationStatus.create_initial()
        
        str_repr = str(status)
        
        assert "NegotiationStatus" in str_repr
        assert "initiation" in str_repr
        assert "pending" in str_repr


class TestResponseType:
    """Test suite for ResponseType enumeration."""

    def test_response_type_values(self):
        """Test response type enumeration values."""
        assert ResponseType.ACCEPT.value == "accept"
        assert ResponseType.REJECT.value == "reject"
        assert ResponseType.COUNTER_PROPOSAL.value == "counter_proposal"
        assert ResponseType.REQUEST_CLARIFICATION.value == "request_clarification"
        assert ResponseType.REQUEST_MODIFICATION.value == "request_modification"
        assert ResponseType.CONDITIONAL_ACCEPT.value == "conditional_accept"
        assert ResponseType.PARTIAL_ACCEPT.value == "partial_accept"
        assert ResponseType.DEFER.value == "defer"
        assert ResponseType.WITHDRAW.value == "withdraw"


class TestResponseReason:
    """Test suite for ResponseReason enumeration."""

    def test_response_reason_values(self):
        """Test response reason enumeration values."""
        assert ResponseReason.TERMS_ACCEPTABLE.value == "terms_acceptable"
        assert ResponseReason.TERMS_UNACCEPTABLE.value == "terms_unacceptable"
        assert ResponseReason.INSUFFICIENT_AUTHORITY.value == "insufficient_authority"


class TestConfidenceLevel:
    """Test suite for ConfidenceLevel enumeration."""

    def test_confidence_level_values(self):
        """Test confidence level enumeration values."""
        assert ConfidenceLevel.VERY_HIGH.value == "very_high"
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MODERATE.value == "moderate"
        assert ConfidenceLevel.LOW.value == "low"
        assert ConfidenceLevel.VERY_LOW.value == "very_low"
        assert ConfidenceLevel.UNCERTAIN.value == "uncertain"


class TestTermResponse:
    """Test suite for TermResponse."""

    def test_create_term_response(self):
        """Test creating a term response."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.ACCEPT,
            reason=ResponseReason.TERMS_ACCEPTABLE,
            comments="This works for us",
            confidence_level=ConfidenceLevel.HIGH,
        )
        
        assert response.term_id == "term_1"
        assert response.response_type == ResponseType.ACCEPT
        assert response.reason == ResponseReason.TERMS_ACCEPTABLE
        assert response.comments == "This works for us"
        assert response.confidence_level == ConfidenceLevel.HIGH

    def test_validation_empty_term_id(self):
        """Test validation with empty term ID."""
        with pytest.raises(ValueError, match="term_id cannot be empty"):
            TermResponse(
                term_id="",
                response_type=ResponseType.ACCEPT,
            )

    def test_validation_request_modification_without_suggestion(self):
        """Test validation for REQUEST_MODIFICATION without suggestion."""
        with pytest.raises(ValueError, match="suggested_modification"):
            TermResponse(
                term_id="term_1",
                response_type=ResponseType.REQUEST_MODIFICATION,
            )

    def test_validation_reject_without_comments(self):
        """Test validation for REJECT without comments."""
        with pytest.raises(ValueError, match="comments"):
            TermResponse(
                term_id="term_1",
                response_type=ResponseType.REJECT,
            )

    def test_is_acceptance_true(self):
        """Test acceptance detection (true)."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.ACCEPT,
        )
        
        assert response.is_acceptance() is True

    def test_is_acceptance_conditional(self):
        """Test acceptance detection for conditional accept."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.CONDITIONAL_ACCEPT,
        )
        
        assert response.is_acceptance() is True

    def test_is_acceptance_false(self):
        """Test acceptance detection (false)."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.REJECT,
            comments="Cannot accept",
        )
        
        assert response.is_acceptance() is False

    def test_is_rejection_true(self):
        """Test rejection detection (true)."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.REJECT,
            comments="Cannot accept",
        )
        
        assert response.is_rejection() is True

    def test_requires_follow_up_true(self):
        """Test follow-up requirement detection (true)."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.REQUEST_CLARIFICATION,
            comments="Need more info",
        )
        
        assert response.requires_follow_up() is True

    def test_requires_follow_up_false(self):
        """Test follow-up requirement detection (false)."""
        response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.ACCEPT,
        )
        
        assert response.requires_follow_up() is False


class TestProposalResponse:
    """Test suite for ProposalResponse."""

    def test_create_proposal_response(self):
        """Test creating a proposal response."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT)
            ],
        )
        
        assert response.response_id is not None
        assert response.overall_response == ResponseType.ACCEPT
        assert len(response.term_responses) == 1

    def test_validation_naive_timestamp(self):
        """Test validation with naive timestamp."""
        with pytest.raises(ValueError, match="timezone-aware"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.ACCEPT,
                term_responses=[],
                response_timestamp=datetime.now(),  # Naive
            )

    def test_validation_expires_before_response(self):
        """Test validation when expires is before response."""
        now = datetime.now(timezone.utc)
        
        with pytest.raises(ValueError, match="expires_at must be after"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.ACCEPT,
                term_responses=[],
                response_timestamp=now,
                expires_at=now - timedelta(hours=1),
            )

    def test_validation_duplicate_term_ids(self):
        """Test validation with duplicate term IDs."""
        with pytest.raises(ValueError, match="unique term IDs"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.ACCEPT,
                term_responses=[
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                ],
            )

    def test_validation_inconsistent_accept(self):
        """Test validation for inconsistent ACCEPT overall."""
        with pytest.raises(ValueError, match="ACCEPT overall response requires all terms"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.ACCEPT,
                term_responses=[
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                    TermResponse(
                        term_id="term_2",
                        response_type=ResponseType.REJECT,
                        comments="No",
                    ),
                ],
            )

    def test_validation_inconsistent_reject(self):
        """Test validation for inconsistent REJECT overall."""
        with pytest.raises(ValueError, match="REJECT overall response requires at least one term"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.REJECT,
                term_responses=[
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                ],
            )

    def test_validation_partial_accept(self):
        """Test validation for PARTIAL_ACCEPT."""
        with pytest.raises(ValueError, match="PARTIAL_ACCEPT requires some but not all"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.PARTIAL_ACCEPT,
                term_responses=[
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                    TermResponse(term_id="term_2", response_type=ResponseType.ACCEPT),
                ],
            )

    def test_validation_conditional_accept_without_conditions(self):
        """Test validation for CONDITIONAL_ACCEPT without conditions."""
        with pytest.raises(ValueError, match="Conditional acceptance must include conditions"):
            ProposalResponse(
                response_id=uuid4(),
                proposal_id=uuid4(),
                responding_party_id=uuid4(),
                overall_response=ResponseType.CONDITIONAL_ACCEPT,
                term_responses=[
                    TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                ],
                conditions=[],
            )

    def test_get_term_response(self):
        """Test getting term response by ID."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.ACCEPT),
            ],
        )
        
        term_response = response.get_term_response("term_2")
        
        assert term_response is not None
        assert term_response.term_id == "term_2"

    def test_get_accepted_terms(self):
        """Test getting accepted terms."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.PARTIAL_ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        accepted = response.get_accepted_terms()
        
        assert len(accepted) == 1
        assert accepted[0].term_id == "term_1"

    def test_get_rejected_terms(self):
        """Test getting rejected terms."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.PARTIAL_ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        rejected = response.get_rejected_terms()
        
        assert len(rejected) == 1
        assert rejected[0].term_id == "term_2"

    def test_is_complete_acceptance_true(self):
        """Test complete acceptance detection (true)."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
            ],
        )
        
        assert response.is_complete_acceptance() is True

    def test_is_complete_rejection_true(self):
        """Test complete rejection detection (true)."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.REJECT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        assert response.is_complete_rejection() is True

    def test_get_acceptance_percentage(self):
        """Test acceptance percentage calculation."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.PARTIAL_ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_3", response_type=ResponseType.REJECT, comments="No"),
                TermResponse(term_id="term_4", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        percentage = response.get_acceptance_percentage()
        
        assert percentage == 50.0

    def test_get_response_summary(self):
        """Test getting response summary."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.PARTIAL_ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        summary = response.get_response_summary()
        
        assert summary["total_terms"] == 2
        assert summary["accepted_terms"] == 1
        assert summary["rejected_terms"] == 1
        assert summary["acceptance_percentage"] == 50.0

    def test_is_expired_true(self):
        """Test expired response detection (true)."""
        now = datetime.now(timezone.utc)
        
        response = ProposalResponse(
            response_id=uuid4(),
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT)
            ],
            response_timestamp=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        
        assert response.is_expired() is True

    def test_age_in_seconds(self):
        """Test age calculation."""
        now = datetime.now(timezone.utc)
        
        response = ProposalResponse(
            response_id=uuid4(),
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT)
            ],
            response_timestamp=now - timedelta(minutes=5),
        )
        
        age = response.age_in_seconds
        
        assert 290 <= age <= 310  # Approximately 5 minutes

    def test_time_until_expiry(self):
        """Test time until expiry calculation."""
        now = datetime.now(timezone.utc)
        
        response = ProposalResponse(
            response_id=uuid4(),
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT)
            ],
            response_timestamp=now,
            expires_at=now + timedelta(hours=2),
        )
        
        time_remaining = response.time_until_expiry
        
        assert 7100 <= time_remaining <= 7300  # Approximately 2 hours

    def test_with_updated_term_response(self):
        """Test updating term response."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT)
            ],
        )
        
        new_term_response = TermResponse(
            term_id="term_1",
            response_type=ResponseType.CONDITIONAL_ACCEPT,
        )
        
        updated = response.with_updated_term_response("term_1", new_term_response)
        
        assert updated.get_term_response("term_1").response_type == ResponseType.CONDITIONAL_ACCEPT

    def test_with_updated_overall_response(self):
        """Test updating overall response."""
        response = ProposalResponse.create(
            proposal_id=uuid4(),
            responding_party_id=uuid4(),
            overall_response=ResponseType.PARTIAL_ACCEPT,
            term_responses=[
                TermResponse(term_id="term_1", response_type=ResponseType.ACCEPT),
                TermResponse(term_id="term_2", response_type=ResponseType.REJECT, comments="No"),
            ],
        )
        
        # Update to REJECT - must have rejected terms already
        updated = response.with_updated_overall_response(
            overall_response=ResponseType.REJECT,
            overall_reason=ResponseReason.TERMS_UNACCEPTABLE,
        )
        
        assert updated.overall_response == ResponseType.REJECT
        assert updated.overall_reason == ResponseReason.TERMS_UNACCEPTABLE
