"""
Value objects for the narrative engine V2 domain model.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StoryArcPhase(str, Enum):
    """
    Represents the key phases of a standard story arc structure.
    """

    EXPOSITION = "EXPOSITION"
    RISING_ACTION = "RISING_ACTION"
    CLIMAX = "CLIMAX"
    FALLING_ACTION = "FALLING_ACTION"
    RESOLUTION = "RESOLUTION"


class StoryArcState(BaseModel):
    """
    Immutable snapshot of the story arc state at a specific point in time.
    """

    model_config = ConfigDict(frozen=True)

    arc_id: str
    current_phase: StoryArcPhase

    # Progress metrics
    phase_progress: Decimal = Field(default_factory=lambda: Decimal("0.0"))
    turns_in_current_phase: int = 0
    turn_number: int = 0
    current_tension_level: Decimal = Field(default_factory=lambda: Decimal("0.0"))

    # Transition logic
    ready_for_phase_transition: bool = False
    next_phase: Optional[StoryArcPhase] = None
    transition_requirements: List[Any] = Field(default_factory=list)
    previous_phase: Optional[StoryArcPhase] = None

    # Metadata
    state_timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def is_phase_complete(self) -> bool:
        """Helper to check if the phase is marked ready for transition."""
        return self.ready_for_phase_transition


class NarrativeGuidance(BaseModel):
    """
    Value object capturing AI-generated guidance for the current narrative turn.
    """

    model_config = ConfigDict(frozen=True)

    guidance_id: str
    turn_number: int
    arc_state: StoryArcState

    primary_narrative_goal: str
    target_tension_level: Optional[Decimal] = None
    secondary_narrative_goals: List[str] = Field(default_factory=list)


class PacingAdjustment(BaseModel):
    """
    Value object capturing pacing modifications for the current turn.
    """

    model_config = ConfigDict(frozen=True)

    adjustment_id: str
    turn_number: int

    intensity_modifier: Decimal
    tension_target: Decimal
    speed_modifier: Decimal

    adjustment_reason: str
    triggered_by: str
