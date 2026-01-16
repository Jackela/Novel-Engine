#!/usr/bin/env python3
"""
Plot Point Value Object

This module defines value objects related to plot points and story progression,
representing key moments and transitions in narrative structure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Set
from uuid import UUID


class PlotPointType(Enum):
    """Types of plot points in narrative structure."""

    INCITING_INCIDENT = "inciting_incident"
    RISING_ACTION = "rising_action"
    CLIMAX = "climax"
    FALLING_ACTION = "falling_action"
    RESOLUTION = "resolution"
    TURNING_POINT = "turning_point"
    REVELATION = "revelation"
    CRISIS = "crisis"
    SETBACK = "setback"
    TRIUMPH = "triumph"
    COMPLICATION = "complication"
    DISCOVERY = "discovery"
    CONFRONTATION = "confrontation"
    RECONCILIATION = "reconciliation"
    SACRIFICE = "sacrifice"
    TRANSFORMATION = "transformation"


class PlotPointImportance(Enum):
    """Relative importance levels for plot points."""

    CRITICAL = "critical"  # Essential to main story
    MAJOR = "major"  # Important for story progression
    MODERATE = "moderate"  # Contributes to character/subplot development
    MINOR = "minor"  # Flavor or background detail
    SUPPLEMENTAL = "supplemental"  # Optional content


@dataclass(frozen=True)
class PlotPoint:
    """
    Represents a key moment or transition in narrative structure.

    Plot points are immutable value objects that capture important
    moments in a story, including their context, significance, and
    relationships to other narrative elements.
    """

    plot_point_id: str
    plot_point_type: PlotPointType
    importance: PlotPointImportance
    title: str
    description: str

    # Timing and sequence
    sequence_order: int
    estimated_duration: Optional[int] = None  # In narrative time units

    # Story context
    involved_characters: FrozenSet[UUID] = None
    affected_themes: FrozenSet[str] = None
    location_context: Optional[str] = None

    # Emotional and dramatic context
    emotional_intensity: Decimal = Decimal("5.0")  # 0-10 scale
    dramatic_tension: Decimal = Decimal("5.0")  # 0-10 scale
    story_significance: Decimal = Decimal("5.0")  # 0-10 scale

    # Cause and effect
    prerequisite_events: List[str] = None
    triggered_consequences: List[str] = None

    # Narrative mechanics
    reveals_information: bool = False
    changes_character_relationships: bool = False
    advances_main_plot: bool = True
    advances_subplot: bool = False

    # Metadata
    tags: FrozenSet[str] = None
    narrative_notes: str = ""
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), compare=False
    )
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values and validate constraints."""
        # Convert mutable collections to immutable for hashability
        if self.involved_characters is None:
            object.__setattr__(self, "involved_characters", frozenset())
        elif isinstance(self.involved_characters, set):
            object.__setattr__(
                self, "involved_characters", frozenset(self.involved_characters)
            )

        if self.affected_themes is None:
            object.__setattr__(self, "affected_themes", frozenset())
        elif isinstance(self.affected_themes, set):
            object.__setattr__(self, "affected_themes", frozenset(self.affected_themes))

        if self.prerequisite_events is None:
            object.__setattr__(self, "prerequisite_events", [])

        if self.triggered_consequences is None:
            object.__setattr__(self, "triggered_consequences", [])

        if self.tags is None:
            object.__setattr__(self, "tags", frozenset())
        elif isinstance(self.tags, set):
            object.__setattr__(self, "tags", frozenset(self.tags))

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate constraints
        self._validate_constraints()

    def _validate_constraints(self):
        """Validate business rules and constraints."""
        if not self.title or not self.title.strip():
            raise ValueError("Plot point title cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Plot point description cannot be empty")

        if self.sequence_order < 0:
            raise ValueError("Sequence order must be non-negative")

        if self.estimated_duration is not None and self.estimated_duration <= 0:
            raise ValueError("Estimated duration must be positive if specified")

        # Validate intensity values (0-10 scale)
        for intensity_name, intensity_value in [
            ("emotional_intensity", self.emotional_intensity),
            ("dramatic_tension", self.dramatic_tension),
            ("story_significance", self.story_significance),
        ]:
            if not (Decimal("0") <= intensity_value <= Decimal("10")):
                raise ValueError(f"{intensity_name} must be between 0 and 10")

        if len(self.plot_point_id) > 100:
            raise ValueError("Plot point ID too long (max 100 characters)")

        if len(self.title) > 200:
            raise ValueError("Plot point title too long (max 200 characters)")

        if len(self.description) > 2000:
            raise ValueError("Plot point description too long (max 2000 characters)")

    def _hash_components(self) -> tuple:
        def _dict_to_hashable(values):
            if not values:
                return frozenset()
            items = []
            for key, value in sorted(values.items()):
                if isinstance(value, dict):
                    value = _dict_to_hashable(value)
                elif isinstance(value, list):
                    value = tuple(value)
                elif isinstance(value, Decimal):
                    value = float(value)
                items.append((key, value))
            return frozenset(items)

        return (
            self.plot_point_id,
            self.plot_point_type,
            self.importance,
            self.title,
            self.description,
            self.sequence_order,
            self.estimated_duration,
            self.involved_characters,
            self.affected_themes,
            self.location_context,
            self.emotional_intensity,
            self.dramatic_tension,
            self.story_significance,
            tuple(self.prerequisite_events) if self.prerequisite_events else (),
            tuple(self.triggered_consequences)
            if self.triggered_consequences
            else (),
            self.reveals_information,
            self.changes_character_relationships,
            self.advances_main_plot,
            self.advances_subplot,
            self.tags,
            self.narrative_notes,
            _dict_to_hashable(self.metadata),
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, PlotPoint):
            return NotImplemented
        return self._hash_components() == other._hash_components()

    def __hash__(self) -> int:
        """Custom hash implementation for frozen dataclass with Dict and List fields."""
        return hash(self._hash_components())

    @property
    def is_major_plot_point(self) -> bool:
        """Check if this is a major plot point."""
        return self.importance in [
            PlotPointImportance.CRITICAL,
            PlotPointImportance.MAJOR,
        ]

    @property
    def is_climactic(self) -> bool:
        """Check if this is a climactic plot point."""
        return self.plot_point_type == PlotPointType.CLIMAX

    @property
    def is_turning_point(self) -> bool:
        """Check if this plot point represents a major turning point."""
        turning_point_types = {
            PlotPointType.CLIMAX,
            PlotPointType.TURNING_POINT,
            PlotPointType.REVELATION,
            PlotPointType.CRISIS,
            PlotPointType.TRANSFORMATION,
        }
        return self.plot_point_type in turning_point_types

    @property
    def has_prerequisites(self) -> bool:
        """Check if this plot point has prerequisite events."""
        return bool(self.prerequisite_events)

    @property
    def has_consequences(self) -> bool:
        """Check if this plot point triggers consequences."""
        return bool(self.triggered_consequences)

    @property
    def affects_characters(self) -> bool:
        """Check if this plot point affects characters."""
        return bool(self.involved_characters)

    @property
    def overall_impact_score(self) -> Decimal:
        """
        Calculate an overall impact score for this plot point.

        Combines importance, dramatic tension, and story significance
        into a single metric for ranking and comparison.
        """
        # Weight importance heavily
        importance_weight = {
            PlotPointImportance.CRITICAL: Decimal("1.0"),
            PlotPointImportance.MAJOR: Decimal("0.8"),
            PlotPointImportance.MODERATE: Decimal("0.6"),
            PlotPointImportance.MINOR: Decimal("0.4"),
            PlotPointImportance.SUPPLEMENTAL: Decimal("0.2"),
        }

        base_score = (
            (self.dramatic_tension * Decimal("0.4"))
            + (self.story_significance * Decimal("0.4"))
            + (self.emotional_intensity * Decimal("0.2"))
        )

        return base_score * importance_weight[self.importance]

    def involves_character(self, character_id: UUID) -> bool:
        """Check if this plot point involves a specific character."""
        return character_id in self.involved_characters

    def affects_theme(self, theme: str) -> bool:
        """Check if this plot point affects a specific theme."""
        return theme in self.affected_themes

    def has_tag(self, tag: str) -> bool:
        """Check if this plot point has a specific tag."""
        return tag in self.tags

    def get_narrative_context(self) -> Dict[str, Any]:
        """
        Get contextual information about this plot point.

        Returns:
            Dictionary containing context information for narrative analysis
        """
        return {
            "plot_point_id": self.plot_point_id,
            "type": self.plot_point_type.value,
            "importance": self.importance.value,
            "sequence_order": self.sequence_order,
            "is_major": self.is_major_plot_point,
            "is_turning_point": self.is_turning_point,
            "overall_impact": float(self.overall_impact_score),
            "character_count": len(self.involved_characters),
            "theme_count": len(self.affected_themes),
            "has_prerequisites": self.has_prerequisites,
            "has_consequences": self.has_consequences,
            "reveals_information": self.reveals_information,
            "changes_relationships": self.changes_character_relationships,
        }

    def with_updated_intensity(
        self,
        emotional_intensity: Optional[Decimal] = None,
        dramatic_tension: Optional[Decimal] = None,
        story_significance: Optional[Decimal] = None,
    ) -> "PlotPoint":
        """
        Create a new PlotPoint with updated intensity values.

        Args:
            emotional_intensity: New emotional intensity (0-10)
            dramatic_tension: New dramatic tension (0-10)
            story_significance: New story significance (0-10)

        Returns:
            New PlotPoint instance with updated intensities
        """
        return PlotPoint(
            plot_point_id=self.plot_point_id,
            plot_point_type=self.plot_point_type,
            importance=self.importance,
            title=self.title,
            description=self.description,
            sequence_order=self.sequence_order,
            estimated_duration=self.estimated_duration,
            involved_characters=self.involved_characters.copy(),
            affected_themes=self.affected_themes.copy(),
            location_context=self.location_context,
            emotional_intensity=emotional_intensity or self.emotional_intensity,
            dramatic_tension=dramatic_tension or self.dramatic_tension,
            story_significance=story_significance or self.story_significance,
            prerequisite_events=self.prerequisite_events.copy(),
            triggered_consequences=self.triggered_consequences.copy(),
            reveals_information=self.reveals_information,
            changes_character_relationships=self.changes_character_relationships,
            advances_main_plot=self.advances_main_plot,
            advances_subplot=self.advances_subplot,
            tags=self.tags.copy(),
            narrative_notes=self.narrative_notes,
            creation_timestamp=self.creation_timestamp,
            metadata=self.metadata.copy(),
        )

    def with_additional_characters(self, character_ids: Set[UUID]) -> "PlotPoint":
        """
        Create a new PlotPoint with additional involved characters.

        Args:
            character_ids: Set of character UUIDs to add

        Returns:
            New PlotPoint instance with added characters
        """
        updated_characters = self.involved_characters.union(character_ids)

        return PlotPoint(
            plot_point_id=self.plot_point_id,
            plot_point_type=self.plot_point_type,
            importance=self.importance,
            title=self.title,
            description=self.description,
            sequence_order=self.sequence_order,
            estimated_duration=self.estimated_duration,
            involved_characters=updated_characters,
            affected_themes=self.affected_themes,
            location_context=self.location_context,
            emotional_intensity=self.emotional_intensity,
            dramatic_tension=self.dramatic_tension,
            story_significance=self.story_significance,
            prerequisite_events=self.prerequisite_events.copy(),
            triggered_consequences=self.triggered_consequences.copy(),
            reveals_information=self.reveals_information,
            changes_character_relationships=self.changes_character_relationships,
            advances_main_plot=self.advances_main_plot,
            advances_subplot=self.advances_subplot,
            tags=self.tags,
            narrative_notes=self.narrative_notes,
            creation_timestamp=self.creation_timestamp,
            metadata=self.metadata.copy(),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"PlotPoint('{self.title}', {self.plot_point_type.value}, seq={self.sequence_order})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"PlotPoint(id='{self.plot_point_id}', "
            f"type={self.plot_point_type.value}, "
            f"importance={self.importance.value}, "
            f"title='{self.title}', "
            f"sequence_order={self.sequence_order})"
        )
