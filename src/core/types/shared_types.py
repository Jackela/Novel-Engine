#!/usr/bin/env python3
"""
Shared Type Definitions.

This module defines shared data structures and enums used across the narrative engine
to avoid circular import issues. It intentionally stays lightweight so it can be
imported early in the bootstrap process without pulling in heavy dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

try:  # Prefer richer schema when available
    from src.shared_types import CharacterData  # type: ignore
except Exception:  # pragma: no cover - fallback for minimal environments

    @dataclass
    class CharacterData:  # type: ignore
        """Minimal placeholder used when the full schema package is unavailable."""

        name: str = "Unknown"
        summary: str = ""
        personality_traits: str = ""
        current_status: str = ""
        narrative_context: str = ""


class ActionPriority(Enum):
    """Enumeration for action priority levels in character decision-making."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(Enum):
    """Enumeration for types of actions characters can take."""

    DIALOGUE = "dialogue"
    MOVEMENT = "movement"
    INTERACTION = "interaction"
    INVESTIGATION = "investigation"
    COMBAT = "combat"
    SOCIAL = "social"
    THINKING = "thinking"
    PLANNING = "planning"
    OTHER = "other"


@dataclass
class CharacterAction:
    """
    Represents an action that a character agent has decided to take.

    This data structure encapsulates all the information needed to process
    and log a character's decision.
    """

    action_type: str
    target: Optional[str] = None
    priority: ActionPriority = ActionPriority.NORMAL
    reasoning: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validates the action after initialization."""
        if not self.action_type:
            raise ValueError("action_type cannot be empty")

        if not isinstance(self.priority, ActionPriority):
            if isinstance(self.priority, str):
                try:
                    self.priority = ActionPriority(self.priority.lower())
                except ValueError:
                    self.priority = ActionPriority.NORMAL


@dataclass
class ProposedAction:
    """
    Represents a proposed action that can be evaluated and potentially executed.

    Used in decision-making processes where actions are considered before execution.
    """

    action_type: ActionType
    description: str
    target: Optional[str] = None
    priority: ActionPriority = ActionPriority.NORMAL
    confidence: float = 0.5
    reasoning: Optional[str] = None
    expected_outcome: Optional[str] = None
    risks: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validates the proposed action after initialization."""
        if not self.description:
            raise ValueError("description cannot be empty")

        if not isinstance(self.action_type, ActionType):
            if isinstance(self.action_type, str):
                try:
                    self.action_type = ActionType(self.action_type.lower())
                except ValueError:
                    self.action_type = ActionType.OTHER

        if not isinstance(self.priority, ActionPriority):
            if isinstance(self.priority, str):
                try:
                    self.priority = ActionPriority(self.priority.lower())
                except ValueError:
                    self.priority = ActionPriority.NORMAL

        # Validate confidence score
        if not 0.0 <= self.confidence <= 1.0:
            self.confidence = max(0.0, min(1.0, self.confidence))


__all__ = [
    "ActionPriority",
    "ActionType",
    "CharacterAction",
    "CharacterData",
    "ProposedAction",
]
