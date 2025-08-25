"""
Interaction Engine Core - Data Models and Types
===============================================

Core data models, enums, and type definitions for the interaction engine system.
"""

from .types import (
    InteractionType, InteractionPriority, InteractionContext,
    InteractionPhase, InteractionOutcome, InteractionEngineConfig
)

__all__ = [
    'InteractionType', 'InteractionPriority', 'InteractionContext',
    'InteractionPhase', 'InteractionOutcome', 'InteractionEngineConfig'
]