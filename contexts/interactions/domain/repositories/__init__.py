# \!/usr/bin/env python3
"""
Package __init__
"""

from .negotiation_session_repository import NegotiationSessionRepository

# Create a default instance for dependency injection
negotiation_session_repository = (
    None  # Will be injected by infrastructure layer
)

__all__ = ["NegotiationSessionRepository", "negotiation_session_repository"]
