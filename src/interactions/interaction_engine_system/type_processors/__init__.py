"""
Interaction Type Processors - Specialized Category Handlers
==========================================================

Specialized processors for different interaction types with category-specific logic.
"""

from .interaction_type_processors import (
    InteractionTypeProcessorManager,
    BaseInteractionProcessor,
    DialogueProcessor,
    CombatProcessor,
    CooperationProcessor
)

__all__ = [
    'InteractionTypeProcessorManager',
    'BaseInteractionProcessor',
    'DialogueProcessor',
    'CombatProcessor', 
    'CooperationProcessor'
]