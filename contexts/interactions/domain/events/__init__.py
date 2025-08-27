#!/usr/bin/env python3
"""
Events Package for Interaction Domain

This package contains domain events that represent significant business
occurrences within the Interaction bounded context.

Key Events:
- NegotiationSessionCreated: Session initialization events
- PartyJoinedNegotiation/PartyLeftNegotiation: Participant lifecycle events
- ProposalSubmitted/ProposalResponseReceived: Proposal lifecycle events
- NegotiationPhaseAdvanced: Phase transition events
- NegotiationCompleted/NegotiationTerminated: Session completion events
"""

from .interaction_events import (
    InteractionDomainEvent,
    NegotiationSessionCreated,
    PartyJoinedNegotiation,
    PartyLeftNegotiation,
    ProposalSubmitted,
    ProposalWithdrawn,
    ProposalExpired,
    ProposalResponseReceived,
    CounterProposalSubmitted,
    NegotiationPhaseAdvanced,
    NegotiationCompleted,
    NegotiationTerminated,
    SessionTimeoutWarning,
    ConflictDetected,
    DeadlockDetected,
    BreakthroughAchieved,
    NegotiationMetricsUpdated,
    PartyCapabilityUpdated,
    CommunicationStyleConflict,
    CulturalConsiderationTriggered,
    EVENT_TYPE_MAPPING
)

__all__ = [
    # Base Event
    'InteractionDomainEvent',
    
    # Session Lifecycle Events
    'NegotiationSessionCreated',
    'PartyJoinedNegotiation',
    'PartyLeftNegotiation',
    
    # Proposal Events
    'ProposalSubmitted',
    'ProposalWithdrawn',
    'ProposalExpired',
    'ProposalResponseReceived',
    'CounterProposalSubmitted',
    
    # Phase and Completion Events
    'NegotiationPhaseAdvanced',
    'NegotiationCompleted',
    'NegotiationTerminated',
    
    # System Events
    'SessionTimeoutWarning',
    'ConflictDetected',
    'DeadlockDetected',
    'BreakthroughAchieved',
    'NegotiationMetricsUpdated',
    
    # Party Events
    'PartyCapabilityUpdated',
    'CommunicationStyleConflict',
    'CulturalConsiderationTriggered',
    
    # Utilities
    'EVENT_TYPE_MAPPING'
]

__version__ = "1.0.0"
