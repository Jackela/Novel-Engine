#!/usr/bin/env python3
"""
Domain Services Package for Interaction Domain

This package contains domain services that encapsulate complex business
logic that doesn't naturally belong to any single entity or value object
within the Interaction bounded context.

Key Services:
- NegotiationService: Core negotiation orchestration and rule enforcement
"""

from .negotiation_service import NegotiationService

__all__ = ["NegotiationService"]

__version__ = "1.0.0"
