#!/usr/bin/env python3
"""
Infrastructure Package for Interaction Domain

This package provides infrastructure implementations for the Interaction
bounded context, including persistence, external service integrations,
and other infrastructure concerns.

Key Components:
- Persistence: SQLAlchemy models and database operations
- Repositories: Concrete repository implementations
- External integrations and adapters
"""

# Import key infrastructure components
from .persistence import (
    NegotiationSessionModel,
    InteractionIdType,
    NegotiationStatusType,
    NegotiationPartyType,
    ProposalTermsType,
    ProposalResponseType
)

from .repositories import SQLAlchemyNegotiationSessionRepository

__all__ = [
    # Persistence models and types
    'NegotiationSessionModel',
    'InteractionIdType',
    'NegotiationStatusType',
    'NegotiationPartyType',
    'ProposalTermsType',
    'ProposalResponseType',
    
    # Repository implementations
    'SQLAlchemyNegotiationSessionRepository'
]

__version__ = "1.0.0"
