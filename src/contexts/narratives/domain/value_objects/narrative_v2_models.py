"""
Foundational value objects for the narrative engine V2 data model.

These classes provide strongly typed, immutable representations of the
story arc, narrative guidance, and pacing adjustments that the upgraded
engine relies on for orchestration decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

try:  # Prefer the new src layout when available
    from src.contexts.narratives.domain.value_objects.plot_point import PlotPointType
except ModuleNotFoundError:  # pragma: no cover - fallback for legacy layout
    from contexts.narratives.domain.value_objects.plot_point import (  # type: ignore[import-not-found]
        PlotPointType,
    )


class StoryArcPhase(str, Enum):
    """
    Classic five-act structure enumeration for narrative progression.

    The enum exposes helper properties that surface canonical guidance
    about each phase's position, tension, and pacing expectations.
    """

    EXPOSITION = "exposition"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"

    @property
    def typical_position_ratio(self) -> Tuple[float, float]:
        """
        Return the canonical (start, end) ratio of this phase within a story.

        The values are expressed as floats in the inclusive range [0.0, 1.0].
        """

        return _STORY_ARC_POSITION_MAP[self]

    @property
    def typical_tension_range(self) -> Tuple[Decimal, Decimal]:
        """
        Return the recommended tension range for this phase on a 0-10 scale.
        """

        return _STORY_ARC_TENSION_MAP[self]

    @property
    def typical_pacing_intensity(self) -> str:
        """
        Return the qualitative pacing guidance associated with this phase.
        """

        return _STORY_ARC_PACING_MAP[self]


_STORY_ARC_POSITION_MAP: Dict[StoryArcPhase, Tuple[float, float]] = {
    StoryArcPhase.EXPOSITION: (0.0, 0.15),
    StoryArcPhase.RISING_ACTION: (0.15, 0.70),
    StoryArcPhase.CLIMAX: (0.70, 0.80),
    StoryArcPhase.FALLING_ACTION: (0.80, 0.95),
    StoryArcPhase.RESOLUTION: (0.95, 1.0),
}

_STORY_ARC_TENSION_MAP: Dict[StoryArcPhase, Tuple[Decimal, Decimal]] = {
    StoryArcPhase.EXPOSITION: (Decimal("2.0"), Decimal("4.0")),
    StoryArcPhase.RISING_ACTION: (Decimal("4.0"), Decimal("8.0")),
    StoryArcPhase.CLIMAX: (Decimal("8.0"), Decimal("10.0")),
    StoryArcPhase.FALLING_ACTION: (Decimal("5.0"), Decimal("7.0")),
    StoryArcPhase.RESOLUTION: (Decimal("2.0"), Decimal("4.0")),
}

_STORY_ARC_PACING_MAP: Dict[StoryArcPhase, str] = {
    StoryArcPhase.EXPOSITION: "moderate",
    StoryArcPhase.RISING_ACTION: "brisk",
    StoryArcPhase.CLIMAX: "fast",
    StoryArcPhase.FALLING_ACTION: "moderate",
    StoryArcPhase.RESOLUTION: "slow",
}


class StoryArcState(BaseModel):
    """
    Immutable snapshot describing the current position inside the story arc.

    The model aggregates position metrics, pacing insight, and metadata that
    downstream services use to reason about future narrative turns.
    """

    model_config = ConfigDict(frozen=True)

    # Current position
    current_phase: StoryArcPhase
    phase_progress: Decimal
    overall_progress: Decimal

    # Arc identification
    arc_id: str
    turn_number: int
    sequence_number: int

    # Progression metrics
    turns_in_current_phase: int
    estimated_turns_remaining_in_phase: Optional[int] = None
    estimated_total_turns: Optional[int] = None

    # Narrative state
    current_tension_level: Decimal
    active_plot_thread_count: int
    unresolved_conflict_count: int
    primary_theme_focus: Optional[str] = None

    # Phase transition
    ready_for_phase_transition: bool = False
    next_phase: Optional[StoryArcPhase] = None
    transition_requirements: List[str] = Field(default_factory=list)

    # Metadata
    state_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    previous_phase: Optional[StoryArcPhase] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_progress_values(self) -> "StoryArcState":
        """Enforce numeric constraints that preserve arc integrity."""

        if not (Decimal("0") <= self.phase_progress <= Decimal("1")):
            raise ValueError("phase_progress must be within [0, 1]")

        if not (Decimal("0") <= self.overall_progress <= Decimal("1")):
            raise ValueError("overall_progress must be within [0, 1]")

        if not (Decimal("0") <= self.current_tension_level <= Decimal("10")):
            raise ValueError("current_tension_level must be within [0, 10]")

        if self.turn_number < 0 or self.sequence_number < 0:
            raise ValueError("turn_number and sequence_number must be non-negative")

        if self.turns_in_current_phase < 0:
            raise ValueError("turns_in_current_phase must be non-negative")

        if self.estimated_turns_remaining_in_phase is not None and (
            self.estimated_turns_remaining_in_phase < 0
        ):
            raise ValueError(
                "estimated_turns_remaining_in_phase must be non-negative when set"
            )

        if self.estimated_total_turns is not None and self.estimated_total_turns <= 0:
            raise ValueError("estimated_total_turns must be positive when set")

        if self.active_plot_thread_count < 0:
            raise ValueError("active_plot_thread_count must be non-negative")

        if self.unresolved_conflict_count < 0:
            raise ValueError("unresolved_conflict_count must be non-negative")

        if any(not req for req in self.transition_requirements):
            raise ValueError("transition_requirements cannot contain empty values")

        return self

    @property
    def is_phase_complete(self) -> bool:
        """
        Determine whether the current phase is ready to transition.
        """

        return (
            self.phase_progress >= Decimal("0.95") and self.ready_for_phase_transition
        )

    @property
    def phase_position_description(self) -> str:
        """
        Provide a human-readable description of progress inside the phase.
        """

        progress = float(self.phase_progress)

        if progress < 0.25:
            return "beginning"
        if progress < 0.5:
            return "early"
        if progress < 0.75:
            return "middle"
        if progress < 0.95:
            return "late"
        return "concluding"

    def to_context_dict(self) -> Dict[str, Any]:
        """
        Convert the state into a lightweight dictionary for prompt contexts.
        """

        return {
            "current_phase": self.current_phase.value,
            "phase_position": self.phase_position_description,
            "phase_progress": float(self.phase_progress),
            "overall_progress": float(self.overall_progress),
            "turn_number": self.turn_number,
            "sequence_number": self.sequence_number,
            "current_tension": float(self.current_tension_level),
            "active_plot_threads": self.active_plot_thread_count,
            "unresolved_conflicts": self.unresolved_conflict_count,
            "approaching_transition": self.phase_progress > Decimal("0.8"),
            "ready_for_transition": self.ready_for_phase_transition,
        }


class NarrativeGuidance(BaseModel):
    """
    Immutable guidance structure for directing a single narrative turn.

    Encapsulates turn-level objectives, content mix recommendations, and
    pacing directives that a DirectorAgent can consume.
    """

    model_config = ConfigDict(frozen=True)

    # Identification
    guidance_id: str
    turn_number: int
    arc_state: StoryArcState

    # Primary objectives
    primary_narrative_goal: str
    secondary_narrative_goals: List[str] = Field(default_factory=list)

    # Plot and pacing
    suggested_plot_point_type: Optional[PlotPointType] = None
    target_tension_level: Decimal = Decimal("5.0")
    recommended_pacing_intensity: str = "moderate"

    # Content guidance
    themes_to_emphasize: List[str] = Field(default_factory=list)
    character_development_focus: List[str] = Field(default_factory=list)
    suggested_setting_type: Optional[str] = None

    # Style and tone
    narrative_tone: str = "balanced"
    dialogue_ratio: Decimal = Decimal("0.3")
    action_ratio: Decimal = Decimal("0.4")
    reflection_ratio: Decimal = Decimal("0.3")

    # Constraints and requirements
    must_include_elements: List[str] = Field(default_factory=list)
    should_avoid_elements: List[str] = Field(default_factory=list)

    # Opportunities
    narrative_opportunities: List[Dict[str, Any]] = Field(default_factory=list)

    # Phase transition
    is_transition_turn: bool = False
    transition_guidance: Optional[str] = None

    # Metadata
    created_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_ratios(self) -> "NarrativeGuidance":
        """Ensure recommended content ratios remain within valid bounds."""

        for name, ratio in (
            ("dialogue_ratio", self.dialogue_ratio),
            ("action_ratio", self.action_ratio),
            ("reflection_ratio", self.reflection_ratio),
        ):
            if not (Decimal("0") <= ratio <= Decimal("1")):
                raise ValueError(f"{name} must be within [0, 1]")

        total = self.dialogue_ratio + self.action_ratio + self.reflection_ratio
        if total > Decimal("1.05"):
            raise ValueError(
                "Combined content ratios should not exceed 1.05 to maintain balance"
            )

        if not self.primary_narrative_goal.strip():
            raise ValueError("primary_narrative_goal cannot be empty")

        if any(not goal for goal in self.secondary_narrative_goals):
            raise ValueError("secondary_narrative_goals cannot contain empty values")

        return self

    def to_director_context(self) -> Dict[str, Any]:
        """
        Generate a serialisable context payload for director prompts.
        """

        return {
            "narrative_goal": self.primary_narrative_goal,
            "secondary_goals": self.secondary_narrative_goals,
            "target_tension": float(self.target_tension_level),
            "pacing": self.recommended_pacing_intensity,
            "tone": self.narrative_tone,
            "content_mix": {
                "dialogue": float(self.dialogue_ratio),
                "action": float(self.action_ratio),
                "reflection": float(self.reflection_ratio),
            },
            "themes_focus": self.themes_to_emphasize,
            "character_focus": self.character_development_focus,
            "required_elements": self.must_include_elements,
            "avoid_elements": self.should_avoid_elements,
            "opportunities": self.narrative_opportunities,
            "is_transition": self.is_transition_turn,
            "transition_note": self.transition_guidance,
        }


class PacingAdjustment(BaseModel):
    """
    Immutable representation of a real-time pacing adjustment directive.

    Provides levers for intensity, content mix, and temporal shifts that
    adaptive pacing controllers can apply to the current or next turn.
    """

    model_config = ConfigDict(frozen=True)

    adjustment_id: str
    turn_number: int

    # Intensity adjustments
    intensity_modifier: Decimal
    tension_target: Decimal
    speed_modifier: Decimal = Decimal("1.0")

    # Content adjustments
    dialogue_adjustment: Decimal = Decimal("0")
    action_adjustment: Decimal = Decimal("0")
    reflection_adjustment: Decimal = Decimal("0")

    # Temporal adjustments
    scene_break_recommended: bool = False
    time_jump_recommended: bool = False

    # Reasoning
    adjustment_reason: str = ""
    triggered_by: str = ""

    # Metadata
    created_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_adjustments(self) -> "PacingAdjustment":
        """Validate that pacing modifiers remain inside guardrails."""

        if not (Decimal("-3") <= self.intensity_modifier <= Decimal("3")):
            raise ValueError("intensity_modifier must be within [-3, 3]")

        if not (Decimal("0") <= self.tension_target <= Decimal("10")):
            raise ValueError("tension_target must be within [0, 10]")

        if not (Decimal("0.1") <= self.speed_modifier <= Decimal("3.0")):
            raise ValueError("speed_modifier must be within [0.1, 3.0]")

        for name, value in (
            ("dialogue_adjustment", self.dialogue_adjustment),
            ("action_adjustment", self.action_adjustment),
            ("reflection_adjustment", self.reflection_adjustment),
        ):
            if not (Decimal("-0.3") <= value <= Decimal("0.3")):
                raise ValueError(f"{name} must be within [-0.3, 0.3]")

        if self.turn_number < 0:
            raise ValueError("turn_number must be non-negative")

        return self
