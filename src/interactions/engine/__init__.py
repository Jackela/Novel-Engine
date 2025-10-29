#!/usr/bin/env python3
"""
Interaction Engine System

Modern modular interaction processing system.
"""

from src.interactions.interaction_engine_system.core.types import (
    InteractionContext,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)

from .interaction_engine import InteractionEngine

__all__ = [
    'InteractionEngine',
    'InteractionType',
    'InteractionPriority',
    'InteractionContext',
    'InteractionPhase',
    'InteractionOutcome',
]
