#!/usr/bin/env python3
"""
Infrastructure Persistence Package for Interaction Domain

This package contains persistence-related components including SQLAlchemy
models and database configuration for the Interaction bounded context.

Key Components:
- Models: SQLAlchemy ORM models and custom types
- Database configuration and session management
"""

from .models import (
    InteractionIdType,
    NegotiationPartyType,
    NegotiationSessionModel,
    NegotiationStatusType,
    ProposalResponseType,
    ProposalTermsType,
)

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
