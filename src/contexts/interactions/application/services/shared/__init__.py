#!/usr/bin/env python3
"""Shared utilities for interaction services."""

from .errors import (
    CompatibilityError,
    ConflictError,
    InteractionError,
    NegotiationError,
    OutcomeError,
    ProposalError,
    SessionError,
    ValidationError,
)
from .results import InteractionResult

__all__ = [
    "InteractionError",
    "NegotiationError",
    "ProposalError",
    "OutcomeError",
    "CompatibilityError",
    "ConflictError",
    "SessionError",
    "ValidationError",
    "InteractionResult",
]
