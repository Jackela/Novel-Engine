#!/usr/bin/env python3
"""
SQLAlchemy Models Package for Interaction Infrastructure

This package contains SQLAlchemy ORM models that map domain entities
to database tables for the Interaction bounded context.

Key Models:
- NegotiationSessionModel: Main aggregate root persistence model
- Value object converters and custom types for complex domain objects
"""

from .interaction_value_object_converters import (
    InteractionIdType,
    NegotiationPartyType,
    NegotiationStatusType,
    ProposalResponseType,
    ProposalTermsType,
)
from .negotiation_session_model import NegotiationSessionModel

__all__ = [
    "NegotiationSessionModel",
    "InteractionIdType",
    "NegotiationStatusType",
    "NegotiationPartyType",
    "ProposalTermsType",
    "ProposalResponseType",
]

__version__ = "1.0.0"
