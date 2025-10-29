#!/usr/bin/env python3
"""
Shared Types - Backward Compatibility Interface

This module maintains backward compatibility by importing and exposing the
shared types from core types module.
"""

# Direct import from core types to avoid circular imports
from src.core.types.shared_types import (
    ActionPriority,
    ActionType,
    CharacterAction,
)

__all__ = [
    "ActionPriority",
    "ActionType",
    "CharacterAction",
]
