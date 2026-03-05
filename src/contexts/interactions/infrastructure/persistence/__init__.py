#!/usr/bin/env python3
"""
Infrastructure Persistence Package for Interaction Domain

This package contains persistence-related components including SQLAlchemy
models and database configuration for the Interaction bounded context.

Key Components:
- Models: SQLAlchemy ORM models and custom types
- Database configuration and session management
"""

# models module may not exist during type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import (
        InteractionIdType,
        NegotiationPartyType,
        NegotiationSessionModel,
        NegotiationStatusType,
        ProposalResponseType,
        ProposalTermsType,
    )
else:
    try:
        from .models import (
            InteractionIdType,
            NegotiationPartyType,
            NegotiationSessionModel,
            NegotiationStatusType,
            ProposalResponseType,
            ProposalTermsType,
        )
    except ImportError:
        # Fallback for when models module doesn't exist yet
        InteractionIdType = None  # type: ignore[misc]
        NegotiationPartyType = None  # type: ignore[misc]
        NegotiationSessionModel = None  # type: ignore[misc]
        NegotiationStatusType = None  # type: ignore[misc]
        ProposalResponseType = None  # type: ignore[misc]
        ProposalTermsType = None  # type: ignore[misc]

__all__ = [
    # Re-export everything from models
    "NegotiationSessionModel",
    "InteractionIdType",
    "NegotiationStatusType",
    "NegotiationPartyType",
    "ProposalTermsType",
    "ProposalResponseType",
]

__version__ = "1.0.0"
