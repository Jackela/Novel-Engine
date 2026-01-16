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
from .negotiation_party import (
    AuthorityLevel,
    CommunicationPreference,
    NegotiationCapability,
    NegotiationParty,
    NegotiationStyle,
    PartyPreferences,
    PartyRole,
)
from .negotiation_status import (
    NegotiationOutcome,
    NegotiationPhase,
    NegotiationStatus,
    TerminationReason,
)
from .proposal_response import (
    ConfidenceLevel,
    ProposalResponse,
    ResponseReason,
    ResponseType,
    TermResponse,
)
from .proposal_terms import (
    ProposalPriority,
    ProposalTerms,
    ProposalType,
    TermCondition,
    TermType,
)

__all__ = [
    # Core Identity
    "InteractionId",
    # Status Management
    "NegotiationStatus",
    "NegotiationPhase",
    "NegotiationOutcome",
    "TerminationReason",
    # Proposal Terms
    "ProposalTerms",
    "TermCondition",
    "ProposalType",
    "TermType",
    "ProposalPriority",
    # Negotiation Parties
    "NegotiationParty",
    "NegotiationCapability",
    "PartyPreferences",
    "PartyRole",
    "AuthorityLevel",
    "NegotiationStyle",
    "CommunicationPreference",
    # Proposal Responses
    "ProposalResponse",
    "TermResponse",
    "ResponseType",
    "ResponseReason",
    "ConfidenceLevel",
]

__version__ = "1.0.0"
