#!/usr/bin/env python3
"""
Shared Type Definitions
=======================

This module defines shared data structures and enums used across the narrative engine
to avoid circular import issues between modules.

Contains:
- CharacterAction class
- ActionPriority enum
- Other shared type definitions

Architecture Reference: Story 1.1 - Narrative Engine Foundation
Development Phase: Phase 1 - Shared Type Definitions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class ActionPriority(Enum):
    """Enumeration for action priority levels in character decision-making."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CharacterAction:
    """
    Represents an action that a character agent has decided to take.
    
    This data structure encapsulates all the information needed to process
    and log a character's decision, including the action type, target,
    reasoning, and associated parameters.
    """
    action_type: str
    target: Optional[str] = None
    priority: ActionPriority = ActionPriority.NORMAL
    reasoning: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate action after initialization."""
        if not self.action_type:
            raise ValueError("action_type cannot be empty")
        
        if not isinstance(self.priority, ActionPriority):
            # Try to convert string to ActionPriority if possible
            if isinstance(self.priority, str):
                try:
                    self.priority = ActionPriority(self.priority.lower())
                except ValueError:
                    self.priority = ActionPriority.NORMAL