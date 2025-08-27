#!/usr/bin/env python3
"""
Value Objects Package for Interaction Domain

This package contains immutable value objects that represent core concepts
within the Interaction bounded context. These value objects encapsulate
data and behavior while maintaining immutability following DDD principles.

Key Value Objects:
- InteractionId: Unique identification for interaction entities
- NegotiationStatus: Status tracking and phase management for negotiations
- ProposalTerms: Complete representation of proposal terms and conditions
- NegotiationParty: Participant representation with capabilities and preferences
- ProposalResponse: Response handling and analysis for proposals
"""

from .interaction_id import InteractionId
from .negotiation_status import (
    NegotiationStatus,
    NegotiationPhase,
    NegotiationOutcome,
    TerminationReason
)
from .proposal_terms import (
    ProposalTerms,
    TermCondition,
    ProposalType,
    TermType,
    ProposalPriority
)
from .negotiation_party import (
    NegotiationParty,
    NegotiationCapability,
    PartyPreferences,
    PartyRole,
    AuthorityLevel,
    NegotiationStyle,
    CommunicationPreference
)
from .proposal_response import (
    ProposalResponse,
    TermResponse,
    ResponseType,
    ResponseReason,
    ConfidenceLevel
)

__all__ = [
    # Core Identity
    'InteractionId',
    
    # Status Management
    'NegotiationStatus',
    'NegotiationPhase',
    'NegotiationOutcome',
    'TerminationReason',
    
    # Proposal Terms
    'ProposalTerms',
    'TermCondition',
    'ProposalType',
    'TermType',
    'ProposalPriority',
    
    # Negotiation Parties
    'NegotiationParty',
    'NegotiationCapability',
    'PartyPreferences',
    'PartyRole',
    'AuthorityLevel',
    'NegotiationStyle',
    'CommunicationPreference',
    
    # Proposal Responses
    'ProposalResponse',
    'TermResponse',
    'ResponseType',
    'ResponseReason',
    'ConfidenceLevel'
]

__version__ = "1.0.0"
