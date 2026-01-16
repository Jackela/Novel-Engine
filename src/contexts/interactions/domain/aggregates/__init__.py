#!/usr/bin/env python3
"""
Aggregates Package for Interaction Domain

This package contains aggregate roots that encapsulate complex business
logic and maintain consistency boundaries within the Interaction bounded context.

Key Aggregates:
- NegotiationSession: Main aggregate for managing negotiations between parties
"""

from .negotiation_session import NegotiationSession

__all__ = ["NegotiationSession"]

__version__ = "1.0.0"
