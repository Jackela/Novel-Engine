#!/usr/bin/env python3
"""
Negotiation Session Aggregate Root

This module implements the NegotiationSession aggregate root, which manages
the complete lifecycle of negotiations between parties in the Interaction
bounded context.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4

from ..events.interaction_events import (
    NegotiationSessionCreated,
    PartyJoinedNegotiation,
    PartyLeftNegotiation,
    ProposalSubmitted,
    ProposalResponseReceived,
    NegotiationPhaseAdvanced,
    NegotiationCompleted,
    NegotiationTerminated,
    SessionTimeoutWarning,
    ConflictDetected
)
from ..value_objects.interaction_id import InteractionId
from ..value_objects.negotiation_status import (
    NegotiationStatus,
    NegotiationPhase,
    NegotiationOutcome,
    TerminationReason
)
from ..value_objects.negotiation_party import NegotiationParty, PartyRole
from ..value_objects.proposal_terms import ProposalTerms, ProposalType
from ..value_objects.proposal_response import ProposalResponse, ResponseType


@dataclass
class NegotiationSession:
    """
    Aggregate root for managing negotiation sessions between parties.
    
    Encapsulates the complete negotiation lifecycle including party management,
    proposal handling, status tracking, and business rule enforcement.
    """
    
    # Identity (required fields without defaults)
    session_id: InteractionId
    session_name: str
    session_type: str
    status: NegotiationStatus
    created_at: datetime
    created_by: UUID
    
    # Optional/defaulted fields
    # Participants
    parties: Dict[UUID, NegotiationParty] = field(default_factory=dict)
    party_roles: Dict[UUID, PartyRole] = field(default_factory=dict)
    
    # Proposals and Responses
    active_proposals: Dict[UUID, ProposalTerms] = field(default_factory=dict)
    proposal_history: List[ProposalTerms] = field(default_factory=list)
    responses: Dict[UUID, List[ProposalResponse]] = field(default_factory=dict)
    
    # Session Configuration
    max_parties: int = 10
    session_timeout_hours: int = 72
    auto_advance_phases: bool = True
    require_unanimous_agreement: bool = False
    allow_partial_agreements: bool = True
    
    # Metadata and Context
    session_context: Dict[str, Any] = field(default_factory=dict)
    negotiation_domain: Optional[str] = None
    priority_level: str = "medium"
    confidentiality_level: str = "standard"
    
    # Event Tracking
    _domain_events: List[Any] = field(default_factory=list, init=False)
    _version: int = field(default=0, init=False)
    
    def __post_init__(self):
        """Initialize and validate negotiation session."""
        if not self.session_name.strip():
            raise ValueError("session_name cannot be empty")
        
        if not self.session_type.strip():
            raise ValueError("session_type cannot be empty")
        
        if self.max_parties < 2:
            raise ValueError("max_parties must be at least 2")
        
        if self.session_timeout_hours <= 0:
            raise ValueError("session_timeout_hours must be positive")
        
        # Ensure created_at is timezone-aware
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        
        # Add creation event
        self._add_domain_event(
            NegotiationSessionCreated(
                session_id=self.session_id.value,
                session_name=self.session_name,
                session_type=self.session_type,
                created_by=self.created_by,
                created_at=self.created_at,
                max_parties=self.max_parties,
                session_context=self.session_context
            )
        )
    
    @classmethod
    def create(cls, session_name: str, session_type: str, created_by: UUID,
               negotiation_domain: Optional[str] = None,
               max_parties: int = 10,
               session_timeout_hours: int = 72,
               session_context: Optional[Dict[str, Any]] = None) -> 'NegotiationSession':
        """Create a new negotiation session."""
        session_id = InteractionId.generate()
        now = datetime.now(timezone.utc)
        
        status = NegotiationStatus.create_initial(
            started_at=now,
            expected_completion_at=now + timedelta(hours=session_timeout_hours)
        )
        
        return cls(
            session_id=session_id,
            session_name=session_name,
            session_type=session_type,
            status=status,
            created_at=now,
            created_by=created_by,
            max_parties=max_parties,
            session_timeout_hours=session_timeout_hours,
            negotiation_domain=negotiation_domain,
            session_context=session_context or {}
        )
    
    def add_party(self, party: NegotiationParty) -> None:
        """Add a party to the negotiation session."""
        if party.party_id in self.parties:
            raise ValueError(f"Party {party.party_id} already in session")
        
        if len(self.parties) >= self.max_parties:
            raise ValueError(f"Session at maximum capacity ({self.max_parties} parties)")
        
        if not self.status.is_active:
            raise ValueError("Cannot add party to inactive negotiation session")
        
        # Check if party is compatible with existing parties
        for existing_party in self.parties.values():
            if not party.is_compatible_with(existing_party):
                raise ValueError(f"Party {party.party_name} incompatible with existing party {existing_party.party_name}")
        
        # Validate role constraints
        if party.role == PartyRole.MEDIATOR:
            existing_mediators = [p for p in self.parties.values() if p.role == PartyRole.MEDIATOR]
            if existing_mediators:
                raise ValueError("Session can only have one mediator")
        
        self.parties[party.party_id] = party
        self.party_roles[party.party_id] = party.role
        self.responses[party.party_id] = []
        
        # Update last activity
        self.status = self.status.update_last_activity()
        self._increment_version()
        
        self._add_domain_event(
            PartyJoinedNegotiation(
                session_id=self.session_id.value,
                party_id=party.party_id,
                party_name=party.party_name,
                party_role=party.role.value,
                joined_at=datetime.now(timezone.utc)
            )
        )
    
    def remove_party(self, party_id: UUID, reason: Optional[str] = None) -> None:
        """Remove a party from the negotiation session."""
        if party_id not in self.parties:
            raise ValueError(f"Party {party_id} not in session")
        
        party = self.parties[party_id]
        
        # Check if removal would invalidate session
        if len(self.parties) <= 2:
            raise ValueError("Cannot remove party: minimum 2 parties required")
        
        # Handle special roles
        if party.role == PartyRole.MEDIATOR:
            # Check if mediation is still needed
            remaining_parties = [p for pid, p in self.parties.items() if pid != party_id]
            if any(not p.is_decision_maker for p in remaining_parties):
                raise ValueError("Cannot remove mediator while non-decision makers remain")
        
        del self.parties[party_id]
        del self.party_roles[party_id]
        if party_id in self.responses:
            del self.responses[party_id]
        
        # Update status
        self.status = self.status.update_last_activity()
        self._increment_version()
        
        self._add_domain_event(
            PartyLeftNegotiation(
                session_id=self.session_id.value,
                party_id=party_id,
                party_name=party.party_name,
                left_at=datetime.now(timezone.utc),
                reason=reason
            )
        )
    
    def submit_proposal(self, proposal: ProposalTerms, submitted_by: UUID) -> None:
        """Submit a new proposal to the negotiation."""
        if submitted_by not in self.parties:
            raise ValueError(f"Party {submitted_by} not in session")
        
        submitting_party = self.parties[submitted_by]
        if not submitting_party.can_make_binding_decisions():
            raise ValueError("Party does not have authority to submit proposals")
        
        if not self.status.is_active:
            raise ValueError("Cannot submit proposal to inactive session")
        
        # Check phase appropriateness
        if self.status.phase not in [
            NegotiationPhase.OPENING,
            NegotiationPhase.BARGAINING,
            NegotiationPhase.CLOSING
        ]:
            raise ValueError(f"Cannot submit proposals in {self.status.phase.value} phase")
        
        # Validate proposal expiry
        if proposal.is_expired:
            raise ValueError("Cannot submit expired proposal")
        
        # Add to active proposals
        self.active_proposals[proposal.proposal_id] = proposal
        self.proposal_history.append(proposal)
        
        # Auto-advance phase if appropriate
        if self.auto_advance_phases and self.status.phase == NegotiationPhase.PREPARATION:
            self._advance_to_phase(NegotiationPhase.OPENING)
        
        # Update status
        self.status = self.status.update_last_activity()
        self._increment_version()
        
        self._add_domain_event(
            ProposalSubmitted(
                session_id=self.session_id.value,
                proposal_id=proposal.proposal_id,
                proposal_type=proposal.proposal_type.value,
                submitted_by=submitted_by,
                submitted_at=datetime.now(timezone.utc),
                terms_count=len(proposal.terms),
                proposal_title=proposal.title
            )
        )
    
    def submit_response(self, response: ProposalResponse) -> None:
        """Submit a response to a proposal."""
        if response.responding_party_id not in self.parties:
            raise ValueError(f"Responding party {response.responding_party_id} not in session")
        
        if response.proposal_id not in self.active_proposals:
            raise ValueError(f"Proposal {response.proposal_id} not found or no longer active")
        
        responding_party = self.parties[response.responding_party_id]
        if not responding_party.can_make_binding_decisions():
            raise ValueError("Party does not have authority to respond to proposals")
        
        if not self.status.is_active:
            raise ValueError("Cannot submit response to inactive session")
        
        # Check for duplicate responses
        existing_responses = self.responses.get(response.responding_party_id, [])
        for existing in existing_responses:
            if existing.proposal_id == response.proposal_id:
                raise ValueError("Party already responded to this proposal")
        
        # Add response
        self.responses[response.responding_party_id].append(response)
        
        # Update status
        self.status = self.status.update_last_activity()
        self._increment_version()
        
        self._add_domain_event(
            ProposalResponseReceived(
                session_id=self.session_id.value,
                proposal_id=response.proposal_id,
                responding_party_id=response.responding_party_id,
                response_type=response.overall_response.value,
                responded_at=response.response_timestamp,
                acceptance_percentage=response.get_acceptance_percentage()
            )
        )
        
        # Check for completion conditions
        self._check_completion_conditions(response.proposal_id)
    
    def advance_phase(self, target_phase: NegotiationPhase, forced: bool = False) -> None:
        """Manually advance negotiation to target phase."""
        if not forced and not self.auto_advance_phases:
            raise ValueError("Manual phase advancement not allowed when auto_advance_phases is False")
        
        if target_phase == self.status.phase:
            return  # Already in target phase
        
        self._advance_to_phase(target_phase, forced=forced)
    
    def terminate_negotiation(self, outcome: NegotiationOutcome,
                            termination_reason: TerminationReason,
                            terminated_by: UUID) -> None:
        """Terminate the negotiation with specified outcome."""
        if terminated_by not in self.parties:
            raise ValueError(f"Party {terminated_by} not in session")
        
        terminating_party = self.parties[terminated_by]
        
        # Check authority for termination
        if outcome in [NegotiationOutcome.AGREEMENT_REACHED, NegotiationOutcome.PARTIAL_AGREEMENT]:
            if not self._has_sufficient_agreement():
                raise ValueError("Insufficient agreement to complete with positive outcome")
        
        completion_time = datetime.now(timezone.utc)
        self.status = self.status.complete_with_outcome(
            outcome=outcome,
            completion_time=completion_time,
            termination_reason=termination_reason
        )
        
        self._increment_version()
        
        # Choose appropriate event
        if outcome in [NegotiationOutcome.AGREEMENT_REACHED, NegotiationOutcome.PARTIAL_AGREEMENT]:
            self._add_domain_event(
                NegotiationCompleted(
                    session_id=self.session_id.value,
                    outcome=outcome.value,
                    completed_at=completion_time,
                    final_proposals=list(self.active_proposals.keys()),
                    participating_parties=list(self.parties.keys()),
                    session_duration=self.status.duration or 0
                )
            )
        else:
            self._add_domain_event(
                NegotiationTerminated(
                    session_id=self.session_id.value,
                    outcome=outcome.value,
                    termination_reason=termination_reason.value,
                    terminated_by=terminated_by,
                    terminated_at=completion_time,
                    session_duration=self.status.duration or 0
                )
            )
    
    def get_proposal_responses(self, proposal_id: UUID) -> List[ProposalResponse]:
        """Get all responses for a specific proposal."""
        responses = []
        for party_responses in self.responses.values():
            for response in party_responses:
                if response.proposal_id == proposal_id:
                    responses.append(response)
        return responses
    
    def get_party_responses(self, party_id: UUID) -> List[ProposalResponse]:
        """Get all responses from a specific party."""
        return self.responses.get(party_id, [])
    
    def get_decision_makers(self) -> List[NegotiationParty]:
        """Get all parties that can make binding decisions."""
        return [party for party in self.parties.values() if party.is_decision_maker]
    
    def get_parties_by_role(self, role: PartyRole) -> List[NegotiationParty]:
        """Get all parties with specified role."""
        return [party for party in self.parties.values() if party.role == role]
    
    def is_timeout_approaching(self, warning_hours: int = 24) -> bool:
        """Check if session timeout is approaching."""
        if not self.status.expected_completion_at:
            return False
        
        now = datetime.now(timezone.utc)
        warning_time = self.status.expected_completion_at - timedelta(hours=warning_hours)
        return now >= warning_time and self.status.is_active
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary."""
        return {
            'session_id': str(self.session_id),
            'session_name': self.session_name,
            'session_type': self.session_type,
            'status': {
                'phase': self.status.phase.value,
                'outcome': self.status.outcome.value,
                'is_active': self.status.is_active,
                'duration': self.status.duration,
                'time_since_last_activity': self.status.time_since_last_activity
            },
            'parties': {
                'total_count': len(self.parties),
                'decision_makers': len(self.get_decision_makers()),
                'by_role': {role.value: len(self.get_parties_by_role(role)) for role in PartyRole}
            },
            'proposals': {
                'active_count': len(self.active_proposals),
                'total_submitted': len(self.proposal_history),
                'response_count': sum(len(responses) for responses in self.responses.values())
            },
            'configuration': {
                'max_parties': self.max_parties,
                'timeout_hours': self.session_timeout_hours,
                'auto_advance_phases': self.auto_advance_phases,
                'require_unanimous': self.require_unanimous_agreement
            }
        }
    
    def check_timeout(self) -> None:
        """Check and handle session timeout."""
        if not self.status.expected_completion_at or not self.status.is_active:
            return
        
        now = datetime.now(timezone.utc)
        
        # Check for timeout warning
        if self.is_timeout_approaching():
            self._add_domain_event(
                SessionTimeoutWarning(
                    session_id=self.session_id.value,
                    warning_at=now,
                    expires_at=self.status.expected_completion_at,
                    time_remaining=int((self.status.expected_completion_at - now).total_seconds())
                )
            )
        
        # Handle actual timeout
        if now > self.status.expected_completion_at:
            self.terminate_negotiation(
                outcome=NegotiationOutcome.TIMEOUT,
                termination_reason=TerminationReason.TIMEOUT_EXCEEDED,
                terminated_by=self.created_by
            )
    
    def _advance_to_phase(self, target_phase: NegotiationPhase, forced: bool = False) -> None:
        """Internal method to advance negotiation phase."""
        if not forced and not self._can_advance_to_phase(target_phase):
            raise ValueError(f"Cannot advance to phase {target_phase.value} - conditions not met")
        
        old_phase = self.status.phase
        self.status = self.status.advance_to_phase(target_phase)
        self._increment_version()
        
        self._add_domain_event(
            NegotiationPhaseAdvanced(
                session_id=self.session_id.value,
                from_phase=old_phase.value,
                to_phase=target_phase.value,
                advanced_at=datetime.now(timezone.utc),
                forced=forced
            )
        )
    
    def _can_advance_to_phase(self, target_phase: NegotiationPhase) -> bool:
        """Check if negotiation can advance to target phase."""
        current = self.status.phase
        
        # Phase-specific advancement logic
        if target_phase == NegotiationPhase.OPENING:
            return len(self.parties) >= 2
        
        elif target_phase == NegotiationPhase.BARGAINING:
            return len(self.active_proposals) > 0
        
        elif target_phase == NegotiationPhase.CLOSING:
            return any(self._has_responses_for_proposal(pid) for pid in self.active_proposals)
        
        elif target_phase == NegotiationPhase.IMPLEMENTATION:
            return self._has_sufficient_agreement()
        
        return True
    
    def _has_responses_for_proposal(self, proposal_id: UUID) -> bool:
        """Check if proposal has received responses."""
        responses = self.get_proposal_responses(proposal_id)
        decision_makers = self.get_decision_makers()
        
        # At least half of decision makers should respond
        return len(responses) >= len(decision_makers) // 2
    
    def _has_sufficient_agreement(self) -> bool:
        """Check if there's sufficient agreement to complete negotiation."""
        if not self.active_proposals:
            return False
        
        decision_makers = self.get_decision_makers()
        if not decision_makers:
            return False
        
        for proposal_id in self.active_proposals:
            responses = self.get_proposal_responses(proposal_id)
            acceptances = [r for r in responses if r.is_complete_acceptance()]
            
            if self.require_unanimous_agreement:
                if len(acceptances) == len(decision_makers):
                    return True
            else:
                # Majority acceptance
                if len(acceptances) > len(decision_makers) // 2:
                    return True
        
        return False
    
    def _check_completion_conditions(self, proposal_id: UUID) -> None:
        """Check if negotiation can be completed based on new response."""
        if not self._has_sufficient_agreement():
            return
        
        # Auto-complete if conditions are met
        if self.auto_advance_phases:
            try:
                if self.status.phase != NegotiationPhase.CLOSING:
                    self._advance_to_phase(NegotiationPhase.CLOSING)
                
                # Complete the negotiation
                outcome = NegotiationOutcome.AGREEMENT_REACHED
                if not self.require_unanimous_agreement:
                    # Check if it's partial agreement
                    decision_makers = self.get_decision_makers()
                    acceptances = len([r for r in self.get_proposal_responses(proposal_id) 
                                    if r.is_complete_acceptance()])
                    if acceptances < len(decision_makers):
                        outcome = NegotiationOutcome.PARTIAL_AGREEMENT
                
                self.terminate_negotiation(
                    outcome=outcome,
                    termination_reason=TerminationReason.MUTUAL_AGREEMENT,
                    terminated_by=self.created_by
                )
            except ValueError:
                # Conditions changed, continue negotiation
                pass
    
    def _add_domain_event(self, event: Any) -> None:
        """Add domain event to be published."""
        self._domain_events.append(event)
    
    def _increment_version(self) -> None:
        """Increment aggregate version for optimistic concurrency."""
        self._version += 1
    
    def get_uncommitted_events(self) -> List[Any]:
        """Get uncommitted domain events."""
        return self._domain_events.copy()
    
    def mark_events_as_committed(self) -> None:
        """Mark domain events as committed."""
        self._domain_events.clear()
    
    @property
    def version(self) -> int:
        """Get current aggregate version."""
        return self._version
    
    @property
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status.is_active
    
    @property
    def party_count(self) -> int:
        """Get current party count."""
        return len(self.parties)
    
    @property
    def proposal_count(self) -> int:
        """Get active proposal count."""
        return len(self.active_proposals)
    
    @property
    def total_responses(self) -> int:
        """Get total response count."""
        return sum(len(responses) for responses in self.responses.values())
    
    def __eq__(self, other: Any) -> bool:
        """Compare NegotiationSession instances for equality."""
        if not isinstance(other, NegotiationSession):
            return False
        return self.session_id == other.session_id
    
    def __str__(self) -> str:
        """Return string representation of negotiation session."""
        return (f"NegotiationSession(id={self.session_id}, name={self.session_name}, "
                f"phase={self.status.phase.value}, parties={len(self.parties)})")