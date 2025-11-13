#!/usr/bin/env python3
"""
Thin compatibility layer that re-exports the canonical shared types from
``src.shared_types`` so legacy modules can continue importing from
``src.core.types.shared_types``.
"""

from __future__ import annotations

from src.shared_types import (  # noqa: F401
    ActionPriority,
    ActionType,
    CharacterAction,
    CharacterData,
    ProposedAction,
)

__all__ = [
    "ActionPriority",
    "ActionType",
    "CharacterAction",
    "CharacterData",
    "ProposedAction",
]

