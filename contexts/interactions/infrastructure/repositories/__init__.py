#!/usr/bin/env python3
"""
Infrastructure Repositories Package for Interaction Domain

This package contains concrete implementations of repository interfaces
for the Interaction bounded context using various persistence technologies.

Key Repositories:
- SQLAlchemyNegotiationSessionRepository: SQLAlchemy-based repository implementation
"""

from .sqlalchemy_negotiation_session_repository import (
    SQLAlchemyNegotiationSessionRepository,
)

__all__ = ["SQLAlchemyNegotiationSessionRepository"]

__version__ = "1.0.0"
