"""
Interaction Engine Core - Data Models and Types
===============================================

Core data models, enums, and type definitions for the interaction engine system.
"""

from .types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)

__all__ = [
    "InteractionType",
    "InteractionPriority",
    "InteractionContext",
    "InteractionPhase",
    "InteractionOutcome",
    "InteractionEngineConfig",
]
