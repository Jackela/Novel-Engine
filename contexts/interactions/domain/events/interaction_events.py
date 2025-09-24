#!/usr/bin/env python3
"""
Interaction Domain Events

This module implements domain events for the Interaction bounded context,
representing significant business events that occur during negotiations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass(frozen=True)
class InteractionDomainEvent:
    """Base class for all interaction domain events."""

    session_id: UUID
    occurred_at: datetime
    event_id: UUID
    event_version: int = 1
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate base event data."""
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


@dataclass(frozen=True)
class NegotiationSessionCreated(InteractionDomainEvent):
    """Event fired when a new negotiation session is created."""

    session_name: str = ""
    session_type: str = ""
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    max_parties: int = 2
    session_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.session_context is None:
            object.__setattr__(self, "session_context", {})
        if not self.session_name.strip():
            raise ValueError("session_name cannot be empty")
        if not self.session_type.strip():
            raise ValueError("session_type cannot be empty")
        if self.max_parties < 2:
            raise ValueError("max_parties must be at least 2")


@dataclass(frozen=True)
class PartyJoinedNegotiation(InteractionDomainEvent):
    """Event fired when a party joins a negotiation session."""

    party_id: Optional[UUID] = None
    party_name: str = ""
    party_role: str = ""
    joined_at: Optional[datetime] = None
    authority_level: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.party_name.strip():
            raise ValueError("party_name cannot be empty")
        if not self.party_role.strip():
            raise ValueError("party_role cannot be empty")


@dataclass(frozen=True)
class PartyLeftNegotiation(InteractionDomainEvent):
    """Event fired when a party leaves a negotiation session."""

    party_id: Optional[UUID] = None
    party_name: str = ""
    left_at: Optional[datetime] = None
    reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.party_name.strip():
            raise ValueError("party_name cannot be empty")


@dataclass(frozen=True)
class ProposalSubmitted(InteractionDomainEvent):
    """Event fired when a proposal is submitted to a negotiation."""

    proposal_id: Optional[UUID] = None
    proposal_type: str = ""
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    terms_count: int = 0
    proposal_title: str = ""
    expires_at: Optional[datetime] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.proposal_type.strip():
            raise ValueError("proposal_type cannot be empty")
        if not self.proposal_title.strip():
            raise ValueError("proposal_title cannot be empty")
        if self.terms_count <= 0:
            raise ValueError("terms_count must be positive")
        if (
            self.expires_at
            and self.submitted_at
            and self.expires_at <= self.submitted_at
        ):
            raise ValueError("expires_at must be after submitted_at")


@dataclass(frozen=True)
class ProposalWithdrawn(InteractionDomainEvent):
    """Event fired when a proposal is withdrawn from a negotiation."""

    proposal_id: Optional[UUID] = None
    withdrawn_by: Optional[UUID] = None
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.withdrawn_at and self.withdrawn_at.tzinfo is None:
            raise ValueError("withdrawn_at must be timezone-aware")


@dataclass(frozen=True)
class ProposalExpired(InteractionDomainEvent):
    """Event fired when a proposal expires."""

    proposal_id: Optional[UUID] = None
    expired_at: Optional[datetime] = None
    original_expiry: Optional[datetime] = None
    received_responses: int = 0

    def __post_init__(self):
        super().__post_init__()
        if self.expired_at and self.expired_at.tzinfo is None:
            raise ValueError("expired_at must be timezone-aware")
        if self.received_responses < 0:
            raise ValueError("received_responses cannot be negative")


@dataclass(frozen=True)
class ProposalResponseReceived(InteractionDomainEvent):
    """Event fired when a response to a proposal is received."""

    proposal_id: Optional[UUID] = None
    responding_party_id: Optional[UUID] = None
    response_type: str = ""
    responded_at: Optional[datetime] = None
    acceptance_percentage: float = 0.0
    requires_follow_up: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not self.response_type.strip():
            raise ValueError("response_type cannot be empty")
        if not (0 <= self.acceptance_percentage <= 100):
            raise ValueError("acceptance_percentage must be between 0 and 100")


@dataclass(frozen=True)
class CounterProposalSubmitted(InteractionDomainEvent):
    """Event fired when a counter-proposal is submitted."""

    original_proposal_id: Optional[UUID] = None
    counter_proposal_id: Optional[UUID] = None
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    modified_terms: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.modified_terms is None:
            object.__setattr__(self, "modified_terms", [])
        if not self.modified_terms:
            raise ValueError(
                "modified_terms cannot be empty for counter-proposal"
            )


@dataclass(frozen=True)
class NegotiationPhaseAdvanced(InteractionDomainEvent):
    """Event fired when negotiation advances to a new phase."""

    from_phase: str = ""
    to_phase: str = ""
    advanced_at: Optional[datetime] = None
    forced: bool = False
    advancement_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.from_phase.strip():
            raise ValueError("from_phase cannot be empty")
        if not self.to_phase.strip():
            raise ValueError("to_phase cannot be empty")
        if self.from_phase == self.to_phase:
            raise ValueError("from_phase and to_phase must be different")


@dataclass(frozen=True)
class NegotiationCompleted(InteractionDomainEvent):
    """Event fired when a negotiation is successfully completed."""

    outcome: str = ""
    completed_at: Optional[datetime] = None
    final_proposals: Optional[List[UUID]] = None
    participating_parties: Optional[List[UUID]] = None
    session_duration: int = 0  # seconds
    agreement_terms: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.final_proposals is None:
            object.__setattr__(self, "final_proposals", [])
        if self.participating_parties is None:
            object.__setattr__(self, "participating_parties", [])
        if not self.outcome.strip():
            raise ValueError("outcome cannot be empty")
        if not self.final_proposals:
            raise ValueError("final_proposals cannot be empty")
        if self.participating_parties and len(self.participating_parties) < 2:
            raise ValueError(
                "participating_parties must have at least 2 parties"
            )
        if self.session_duration < 0:
            raise ValueError("session_duration cannot be negative")


@dataclass(frozen=True)
class NegotiationTerminated(InteractionDomainEvent):
    """Event fired when a negotiation is terminated without agreement."""

    outcome: str = ""
    termination_reason: str = ""
    terminated_by: Optional[UUID] = None
    terminated_at: Optional[datetime] = None
    session_duration: int = 0  # seconds
    partial_agreements: Optional[List[UUID]] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.outcome.strip():
            raise ValueError("outcome cannot be empty")
        if not self.termination_reason.strip():
            raise ValueError("termination_reason cannot be empty")
        if self.session_duration < 0:
            raise ValueError("session_duration cannot be negative")


@dataclass(frozen=True)
class SessionTimeoutWarning(InteractionDomainEvent):
    """Event fired when a session is approaching timeout."""

    warning_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    time_remaining: int = 0  # seconds
    warning_level: str = "standard"

    def __post_init__(self):
        super().__post_init__()
        if (
            self.expires_at
            and self.warning_at
            and self.expires_at <= self.warning_at
        ):
            raise ValueError("expires_at must be after warning_at")
        if self.time_remaining <= 0:
            raise ValueError("time_remaining must be positive")
        if not self.warning_level.strip():
            raise ValueError("warning_level cannot be empty")


@dataclass(frozen=True)
class ConflictDetected(InteractionDomainEvent):
    """Event fired when a conflict is detected during negotiation."""

    conflict_type: str = ""
    conflicting_parties: Optional[List[UUID]] = None
    conflict_description: str = ""
    detected_at: Optional[datetime] = None
    severity_level: str = "medium"
    auto_resolution_attempted: bool = False

    def __post_init__(self):
        super().__post_init__()
        if self.conflicting_parties is None:
            object.__setattr__(self, "conflicting_parties", [])
        if not self.conflict_type.strip():
            raise ValueError("conflict_type cannot be empty")
        if self.conflicting_parties and len(self.conflicting_parties) < 2:
            raise ValueError(
                "conflicting_parties must have at least 2 parties"
            )
        if not self.conflict_description.strip():
            raise ValueError("conflict_description cannot be empty")
        if not self.severity_level.strip():
            raise ValueError("severity_level cannot be empty")


@dataclass(frozen=True)
class DeadlockDetected(InteractionDomainEvent):
    """Event fired when a deadlock is detected in negotiation."""

    deadlock_type: str = ""
    affected_proposals: Optional[List[UUID]] = None
    detected_at: Optional[datetime] = None
    contributing_factors: Optional[List[str]] = None
    suggested_resolutions: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.affected_proposals is None:
            object.__setattr__(self, "affected_proposals", [])
        if self.contributing_factors is None:
            object.__setattr__(self, "contributing_factors", [])
        if not self.deadlock_type.strip():
            raise ValueError("deadlock_type cannot be empty")
        if not self.affected_proposals:
            raise ValueError("affected_proposals cannot be empty")
        if not self.contributing_factors:
            raise ValueError("contributing_factors cannot be empty")


@dataclass(frozen=True)
class BreakthroughAchieved(InteractionDomainEvent):
    """Event fired when a significant breakthrough occurs in negotiation."""

    breakthrough_type: str = ""
    achieved_at: Optional[datetime] = None
    key_proposal_id: Optional[UUID] = None
    breakthrough_description: str = ""
    contributing_parties: Optional[List[UUID]] = None
    impact_assessment: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.contributing_parties is None:
            object.__setattr__(self, "contributing_parties", [])
        if not self.breakthrough_type.strip():
            raise ValueError("breakthrough_type cannot be empty")
        if not self.breakthrough_description.strip():
            raise ValueError("breakthrough_description cannot be empty")
        if not self.contributing_parties:
            raise ValueError("contributing_parties cannot be empty")


@dataclass(frozen=True)
class NegotiationMetricsUpdated(InteractionDomainEvent):
    """Event fired when negotiation metrics are updated."""

    metrics_type: str = ""
    updated_at: Optional[datetime] = None
    current_metrics: Optional[Dict[str, Any]] = None
    previous_metrics: Optional[Dict[str, Any]] = None
    trend_analysis: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.current_metrics is None:
            object.__setattr__(self, "current_metrics", {})
        if not self.metrics_type.strip():
            raise ValueError("metrics_type cannot be empty")
        if not self.current_metrics:
            raise ValueError("current_metrics cannot be empty")


@dataclass(frozen=True)
class PartyCapabilityUpdated(InteractionDomainEvent):
    """Event fired when a party's negotiation capabilities are updated."""

    party_id: Optional[UUID] = None
    capability_name: str = ""
    old_proficiency: Optional[float] = None
    new_proficiency: float = 0.0
    updated_at: Optional[datetime] = None
    update_reason: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if not self.capability_name.strip():
            raise ValueError("capability_name cannot be empty")
        if not (0 <= self.new_proficiency <= 100):
            raise ValueError("new_proficiency must be between 0 and 100")
        if self.old_proficiency is not None and not (
            0 <= self.old_proficiency <= 100
        ):
            raise ValueError("old_proficiency must be between 0 and 100")


@dataclass(frozen=True)
class CommunicationStyleConflict(InteractionDomainEvent):
    """Event fired when communication style conflicts are detected."""

    conflicting_parties: Optional[List[UUID]] = None
    conflict_details: str = ""
    detected_at: Optional[datetime] = None
    communication_styles: Optional[Dict[UUID, str]] = None
    resolution_suggestions: Optional[List[str]] = None

    def __post_init__(self):
        super().__post_init__()
        if self.conflicting_parties is None:
            object.__setattr__(self, "conflicting_parties", [])
        if self.communication_styles is None:
            object.__setattr__(self, "communication_styles", {})
        if self.conflicting_parties and len(self.conflicting_parties) < 2:
            raise ValueError(
                "conflicting_parties must have at least 2 parties"
            )
        if not self.conflict_details.strip():
            raise ValueError("conflict_details cannot be empty")
        if self.communication_styles and len(self.communication_styles) < 2:
            raise ValueError(
                "communication_styles must include at least 2 parties"
            )


@dataclass(frozen=True)
class CulturalConsiderationTriggered(InteractionDomainEvent):
    """Event fired when cultural considerations affect negotiation."""

    triggered_by: Optional[UUID] = None
    cultural_factor: str = ""
    impact_description: str = ""
    triggered_at: Optional[datetime] = None
    affected_parties: Optional[List[UUID]] = None
    mitigation_applied: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if self.affected_parties is None:
            object.__setattr__(self, "affected_parties", [])
        if not self.cultural_factor.strip():
            raise ValueError("cultural_factor cannot be empty")
        if not self.impact_description.strip():
            raise ValueError("impact_description cannot be empty")
        if not self.affected_parties:
            raise ValueError("affected_parties cannot be empty")


# Event type mapping for deserialization
EVENT_TYPE_MAPPING = {
    "NegotiationSessionCreated": NegotiationSessionCreated,
    "PartyJoinedNegotiation": PartyJoinedNegotiation,
    "PartyLeftNegotiation": PartyLeftNegotiation,
    "ProposalSubmitted": ProposalSubmitted,
    "ProposalWithdrawn": ProposalWithdrawn,
    "ProposalExpired": ProposalExpired,
    "ProposalResponseReceived": ProposalResponseReceived,
    "CounterProposalSubmitted": CounterProposalSubmitted,
    "NegotiationPhaseAdvanced": NegotiationPhaseAdvanced,
    "NegotiationCompleted": NegotiationCompleted,
    "NegotiationTerminated": NegotiationTerminated,
    "SessionTimeoutWarning": SessionTimeoutWarning,
    "ConflictDetected": ConflictDetected,
    "DeadlockDetected": DeadlockDetected,
    "BreakthroughAchieved": BreakthroughAchieved,
    "NegotiationMetricsUpdated": NegotiationMetricsUpdated,
    "PartyCapabilityUpdated": PartyCapabilityUpdated,
    "CommunicationStyleConflict": CommunicationStyleConflict,
    "CulturalConsiderationTriggered": CulturalConsiderationTriggered,
}
