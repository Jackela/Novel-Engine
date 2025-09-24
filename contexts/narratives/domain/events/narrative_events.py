#!/usr/bin/env python3
"""
Narrative Domain Events

This module defines domain events for the Narrative bounded context,
representing significant occurrences in narrative development and management.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..value_objects.narrative_id import NarrativeId


@dataclass(frozen=True)
class NarrativeEvent:
    """
    Base class for all narrative domain events.

    Provides common structure and metadata for all events
    occurring within the Narrative bounded context.
    """

    event_id: str
    narrative_id: NarrativeId
    occurred_at: datetime
    event_version: int = 1
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        if self.occurred_at is None:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))


# Narrative Arc Events


@dataclass(frozen=True)
class NarrativeArcCreated(NarrativeEvent):
    """
    Event raised when a new narrative arc is created.
    """

    arc_name: str = ""
    arc_type: str = ""
    expected_length: Optional[int] = None
    target_themes: Optional[List[str]] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.target_themes is None:
            object.__setattr__(self, "target_themes", [])


@dataclass(frozen=True)
class NarrativeArcUpdated(NarrativeEvent):
    """
    Event raised when narrative arc properties are updated.
    """

    updated_fields: Dict[str, Any] = None
    previous_values: Dict[str, Any] = None
    update_reason: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.updated_fields is None:
            object.__setattr__(self, "updated_fields", {})
        if self.previous_values is None:
            object.__setattr__(self, "previous_values", {})


@dataclass(frozen=True)
class NarrativeArcCompleted(NarrativeEvent):
    """
    Event raised when a narrative arc reaches completion.
    """

    completion_type: str = "natural"  # natural, forced, abandoned
    final_length: int = 0
    themes_resolved: List[str] = None
    plot_points_count: int = 0

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.themes_resolved is None:
            object.__setattr__(self, "themes_resolved", [])


# Plot Point Events


@dataclass(frozen=True)
class PlotPointAdded(NarrativeEvent):
    """
    Event raised when a plot point is added to a narrative arc.
    """

    plot_point_id: str = ""
    plot_point_type: str = ""
    sequence_order: int = 0
    importance_level: str = ""
    character_ids: List[UUID] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.character_ids is None:
            object.__setattr__(self, "character_ids", [])


@dataclass(frozen=True)
class PlotPointUpdated(NarrativeEvent):
    """
    Event raised when a plot point is modified.
    """

    plot_point_id: str = ""
    updated_fields: Dict[str, Any] = None
    previous_values: Dict[str, Any] = None
    impact_on_narrative: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.updated_fields is None:
            object.__setattr__(self, "updated_fields", {})
        if self.previous_values is None:
            object.__setattr__(self, "previous_values", {})


@dataclass(frozen=True)
class PlotPointRemoved(NarrativeEvent):
    """
    Event raised when a plot point is removed from narrative arc.
    """

    plot_point_id: str = ""
    removal_reason: str = ""
    sequence_adjustments: Dict[
        str, int
    ] = None  # Other plot points that need resequencing

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.sequence_adjustments is None:
            object.__setattr__(self, "sequence_adjustments", {})


# Theme Events


@dataclass(frozen=True)
class ThemeIntroduced(NarrativeEvent):
    """
    Event raised when a new theme is introduced to the narrative.
    """

    theme_id: str = ""
    theme_type: str = ""
    theme_name: str = ""
    intensity_level: str = ""
    introduction_sequence: int = 0
    symbolic_elements: List[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.symbolic_elements is None:
            object.__setattr__(self, "symbolic_elements", [])


@dataclass(frozen=True)
class ThemeIntensityChanged(NarrativeEvent):
    """
    Event raised when theme intensity is adjusted.
    """

    theme_id: str = ""
    previous_intensity: str = ""
    new_intensity: str = ""
    affected_sequences: List[int] = None
    intensity_change_reason: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.affected_sequences is None:
            object.__setattr__(self, "affected_sequences", [])


@dataclass(frozen=True)
class ThemeResolved(NarrativeEvent):
    """
    Event raised when a theme reaches resolution in the narrative.
    """

    theme_id: str = ""
    resolution_type: str = (
        "complete"  # complete, partial, open-ended, subverted
    )
    resolution_sequence: int = 0
    narrative_impact: str = ""
    related_plot_points: List[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.related_plot_points is None:
            object.__setattr__(self, "related_plot_points", [])


# Causal Events


@dataclass(frozen=True)
class CausalLinkEstablished(NarrativeEvent):
    """
    Event raised when a cause-and-effect relationship is established.
    """

    cause_node_id: str = ""
    effect_node_id: str = ""
    relationship_type: str = ""
    relationship_strength: str = ""
    causal_certainty: float = 0.0
    established_by: str = "system"  # system, user, inference


@dataclass(frozen=True)
class CausalLinkRemoved(NarrativeEvent):
    """
    Event raised when a causal relationship is removed.
    """

    cause_node_id: str = ""
    effect_node_id: str = ""
    previous_relationship_type: str = ""
    removal_reason: str = ""
    impact_on_graph: str = ""


# Flow and Pacing Events


@dataclass(frozen=True)
class NarrativeFlowChanged(NarrativeEvent):
    """
    Event raised when narrative flow is modified.
    """

    affected_sequence_range: List[int] = None  # [start, end]
    flow_change_type: str = (
        "restructure"  # restructure, reorder, insert, delete
    )
    previous_flow_state: Dict[str, Any] = None
    new_flow_state: Dict[str, Any] = None
    change_rationale: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.affected_sequence_range is None:
            object.__setattr__(self, "affected_sequence_range", [0, 0])
        if self.previous_flow_state is None:
            object.__setattr__(self, "previous_flow_state", {})
        if self.new_flow_state is None:
            object.__setattr__(self, "new_flow_state", {})
        if len(self.affected_sequence_range) != 2:
            raise ValueError(
                "affected_sequence_range must contain exactly 2 elements [start, end]"
            )


@dataclass(frozen=True)
class PacingAdjusted(NarrativeEvent):
    """
    Event raised when story pacing is adjusted.
    """

    pacing_segment_id: str = ""
    previous_pacing_type: str = ""
    new_pacing_type: str = ""
    previous_intensity: str = ""
    new_intensity: str = ""
    affected_sequences: List[int] = None
    adjustment_reason: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.affected_sequences is None:
            object.__setattr__(self, "affected_sequences", [])


# Context Events


@dataclass(frozen=True)
class ContextUpdated(NarrativeEvent):
    """
    Event raised when narrative context is updated.
    """

    context_id: str = ""
    context_type: str = ""
    updated_fields: Dict[str, Any] = None
    previous_values: Dict[str, Any] = None
    affected_characters: List[UUID] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.updated_fields is None:
            object.__setattr__(self, "updated_fields", {})
        if self.previous_values is None:
            object.__setattr__(self, "previous_values", {})
        if self.affected_characters is None:
            object.__setattr__(self, "affected_characters", [])


@dataclass(frozen=True)
class ContextActivated(NarrativeEvent):
    """
    Event raised when a narrative context becomes active.
    """

    context_id: str = ""
    context_type: str = ""
    activation_sequence: int = 0
    activation_trigger: str = "manual"  # manual, conditional, scheduled
    affected_scope: str = ""
    prerequisites_met: bool = True


@dataclass(frozen=True)
class ContextDeactivated(NarrativeEvent):
    """
    Event raised when a narrative context is deactivated.
    """

    context_id: str = ""
    context_type: str = ""
    deactivation_sequence: int = 0
    deactivation_reason: str = ""
    final_impact_summary: str = ""


# Additional specialized events for complex narrative operations


@dataclass(frozen=True)
class NarrativeConsistencyViolated(NarrativeEvent):
    """
    Event raised when a narrative consistency issue is detected.
    """

    violation_type: str = ""
    involved_elements: List[str] = None
    severity_level: str = "minor"  # minor, moderate, major, critical
    auto_fixable: bool = False
    suggested_resolution: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.involved_elements is None:
            object.__setattr__(self, "involved_elements", [])


@dataclass(frozen=True)
class NarrativeGoalAchieved(NarrativeEvent):
    """
    Event raised when a narrative goal is achieved.
    """

    goal_type: str = ""
    goal_description: str = ""
    achievement_sequence: int = 0
    contributing_elements: List[str] = None
    achievement_method: str = ""

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        super().__post_init__()
        if self.contributing_elements is None:
            object.__setattr__(self, "contributing_elements", [])
