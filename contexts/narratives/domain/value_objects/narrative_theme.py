#!/usr/bin/env python3
"""
Narrative Theme Value Object

This module defines value objects for representing themes, motifs, and
thematic elements within narrative structures.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Set


class ThemeType(Enum):
    """Categories of narrative themes."""

    UNIVERSAL = "universal"  # Love, death, redemption, etc.
    SOCIAL = "social"  # Justice, inequality, power, etc.
    PHILOSOPHICAL = "philosophical"  # Truth, meaning, existence, etc.
    PSYCHOLOGICAL = "psychological"  # Identity, growth, trauma, etc.
    CULTURAL = "cultural"  # Tradition, change, heritage, etc.
    MORAL = "moral"  # Good vs evil, sacrifice, honor, etc.
    POLITICAL = "political"  # Freedom, oppression, revolution, etc.
    SPIRITUAL = "spiritual"  # Faith, transcendence, destiny, etc.
    ENVIRONMENTAL = "environmental"  # Nature, survival, harmony, etc.
    TECHNOLOGICAL = "technological"  # Progress, AI, human-machine, etc.
    FAMILY = "family"  # Legacy, belonging, conflict, etc.
    COMING_OF_AGE = "coming_of_age"  # Growth, responsibility, maturation, etc.


class ThemeIntensity(Enum):
    """Intensity levels for theme presence in narrative."""

    SUBTLE = "subtle"  # Background presence
    MODERATE = "moderate"  # Clearly present but not dominant
    PROMINENT = "prominent"  # Major theme with significant focus
    CENTRAL = "central"  # Core theme driving the narrative
    OVERWHELMING = "overwhelming"  # Dominates all other elements


@dataclass(frozen=True)
class NarrativeTheme:
    """
    Represents a thematic element within a narrative.

    Themes are immutable value objects that capture the underlying
    meanings, messages, and motifs that run through a story.
    """

    theme_id: str
    theme_type: ThemeType
    intensity: ThemeIntensity
    name: str
    description: str

    # Thematic details
    symbolic_elements: Set[str] = None
    related_motifs: Set[str] = None
    character_archetypes: Set[str] = None

    # Narrative presence
    introduction_sequence: Optional[int] = None
    resolution_sequence: Optional[int] = None
    peak_intensity_sequence: Optional[int] = None

    # Thematic development
    development_trajectory: str = ""  # How theme evolves
    conflicts_with_themes: Set[str] = None
    reinforces_themes: Set[str] = None

    # Emotional and moral dimensions
    moral_complexity: Decimal = Decimal("5.0")  # 1-10, higher = more complex
    emotional_resonance: Decimal = Decimal(
        "5.0"
    )  # 1-10, expected emotional impact
    universal_appeal: Decimal = Decimal(
        "5.0"
    )  # 1-10, cross-cultural relevance

    # Expression methods
    expressed_through_dialogue: bool = False
    expressed_through_action: bool = True
    expressed_through_symbolism: bool = False
    expressed_through_setting: bool = False
    expressed_through_character_arc: bool = True

    # Metadata
    cultural_context: Optional[str] = None
    historical_context: Optional[str] = None
    target_audience_relevance: Dict[str, Decimal] = None
    tags: Set[str] = None
    creation_timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values and validate constraints."""
        # Set default values for mutable fields
        if self.symbolic_elements is None:
            object.__setattr__(self, "symbolic_elements", set())

        if self.related_motifs is None:
            object.__setattr__(self, "related_motifs", set())

        if self.character_archetypes is None:
            object.__setattr__(self, "character_archetypes", set())

        if self.conflicts_with_themes is None:
            object.__setattr__(self, "conflicts_with_themes", set())

        if self.reinforces_themes is None:
            object.__setattr__(self, "reinforces_themes", set())

        if self.target_audience_relevance is None:
            object.__setattr__(self, "target_audience_relevance", {})

        if self.tags is None:
            object.__setattr__(self, "tags", set())

        if self.creation_timestamp is None:
            object.__setattr__(
                self, "creation_timestamp", datetime.now(timezone.utc)
            )

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate constraints
        self._validate_constraints()

    def _validate_constraints(self):
        """Validate business rules and constraints."""
        if not self.name or not self.name.strip():
            raise ValueError("Theme name cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Theme description cannot be empty")

        # Validate sequence numbers
        for seq_name, seq_value in [
            ("introduction_sequence", self.introduction_sequence),
            ("resolution_sequence", self.resolution_sequence),
            ("peak_intensity_sequence", self.peak_intensity_sequence),
        ]:
            if seq_value is not None and seq_value < 0:
                raise ValueError(f"{seq_name} must be non-negative")

        # Validate decimal values (1-10 scale)
        for value_name, value in [
            ("moral_complexity", self.moral_complexity),
            ("emotional_resonance", self.emotional_resonance),
            ("universal_appeal", self.universal_appeal),
        ]:
            if not (Decimal("1") <= value <= Decimal("10")):
                raise ValueError(f"{value_name} must be between 1 and 10")

        # Validate target audience relevance values
        for audience, relevance in self.target_audience_relevance.items():
            if not (Decimal("0") <= relevance <= Decimal("10")):
                raise ValueError(
                    f"Audience relevance for '{audience}' must be between 0 and 10"
                )

        # String length constraints
        if len(self.theme_id) > 100:
            raise ValueError("Theme ID too long (max 100 characters)")

        if len(self.name) > 200:
            raise ValueError("Theme name too long (max 200 characters)")

        if len(self.description) > 1000:
            raise ValueError(
                "Theme description too long (max 1000 characters)"
            )

    @property
    def is_major_theme(self) -> bool:
        """Check if this is a major theme."""
        return self.intensity in [
            ThemeIntensity.PROMINENT,
            ThemeIntensity.CENTRAL,
            ThemeIntensity.OVERWHELMING,
        ]

    @property
    def is_central_theme(self) -> bool:
        """Check if this is a central theme."""
        return self.intensity == ThemeIntensity.CENTRAL

    @property
    def has_symbolic_representation(self) -> bool:
        """Check if theme is expressed through symbolism."""
        return bool(self.symbolic_elements) or self.expressed_through_symbolism

    @property
    def has_character_expression(self) -> bool:
        """Check if theme is expressed through character development."""
        return self.expressed_through_character_arc or bool(
            self.character_archetypes
        )

    @property
    def spans_full_narrative(self) -> bool:
        """Check if theme spans the full narrative arc."""
        return (
            self.introduction_sequence is not None
            and self.resolution_sequence is not None
        )

    @property
    def thematic_complexity_score(self) -> Decimal:
        """
        Calculate overall thematic complexity score.

        Combines moral complexity, expression methods, and relationships
        with other themes.
        """
        base_complexity = self.moral_complexity

        # Add complexity for multiple expression methods
        expression_methods = sum(
            [
                self.expressed_through_dialogue,
                self.expressed_through_action,
                self.expressed_through_symbolism,
                self.expressed_through_setting,
                self.expressed_through_character_arc,
            ]
        )
        expression_bonus = Decimal(str(expression_methods * 0.5))

        # Add complexity for thematic relationships
        relationship_bonus = Decimal(
            str(
                (len(self.conflicts_with_themes) + len(self.reinforces_themes))
                * 0.3
            )
        )

        # Cap at 10
        return min(
            Decimal("10"),
            base_complexity + expression_bonus + relationship_bonus,
        )

    @property
    def narrative_impact_score(self) -> Decimal:
        """
        Calculate the overall narrative impact of this theme.

        Combines intensity, emotional resonance, and complexity.
        """
        intensity_weight = {
            ThemeIntensity.SUBTLE: Decimal("0.2"),
            ThemeIntensity.MODERATE: Decimal("0.4"),
            ThemeIntensity.PROMINENT: Decimal("0.6"),
            ThemeIntensity.CENTRAL: Decimal("0.8"),
            ThemeIntensity.OVERWHELMING: Decimal("1.0"),
        }

        base_score = (
            (self.emotional_resonance * Decimal("0.4"))
            + (self.universal_appeal * Decimal("0.3"))
            + (self.thematic_complexity_score * Decimal("0.3"))
        )

        return base_score * intensity_weight[self.intensity]

    def conflicts_with_theme(self, theme_id: str) -> bool:
        """Check if this theme conflicts with another theme."""
        return theme_id in self.conflicts_with_themes

    def reinforces_theme(self, theme_id: str) -> bool:
        """Check if this theme reinforces another theme."""
        return theme_id in self.reinforces_themes

    def has_symbolic_element(self, symbol: str) -> bool:
        """Check if theme includes a specific symbolic element."""
        return symbol in self.symbolic_elements

    def has_related_motif(self, motif: str) -> bool:
        """Check if theme is related to a specific motif."""
        return motif in self.related_motifs

    def uses_archetype(self, archetype: str) -> bool:
        """Check if theme uses a specific character archetype."""
        return archetype in self.character_archetypes

    def get_audience_relevance(self, audience: str) -> Decimal:
        """Get relevance score for a specific audience."""
        return self.target_audience_relevance.get(audience, Decimal("5.0"))

    def get_thematic_context(self) -> Dict[str, Any]:
        """
        Get contextual information about this theme.

        Returns:
            Dictionary containing theme context for narrative analysis
        """
        return {
            "theme_id": self.theme_id,
            "type": self.theme_type.value,
            "intensity": self.intensity.value,
            "name": self.name,
            "is_major": self.is_major_theme,
            "is_central": self.is_central_theme,
            "complexity_score": float(self.thematic_complexity_score),
            "impact_score": float(self.narrative_impact_score),
            "spans_full_narrative": self.spans_full_narrative,
            "has_symbolic_representation": self.has_symbolic_representation,
            "expression_methods": {
                "dialogue": self.expressed_through_dialogue,
                "action": self.expressed_through_action,
                "symbolism": self.expressed_through_symbolism,
                "setting": self.expressed_through_setting,
                "character_arc": self.expressed_through_character_arc,
            },
            "relationship_counts": {
                "conflicts": len(self.conflicts_with_themes),
                "reinforces": len(self.reinforces_themes),
                "symbolic_elements": len(self.symbolic_elements),
                "motifs": len(self.related_motifs),
                "archetypes": len(self.character_archetypes),
            },
        }

    def with_updated_intensity(
        self, new_intensity: ThemeIntensity
    ) -> "NarrativeTheme":
        """
        Create a new NarrativeTheme with updated intensity.

        Args:
            new_intensity: New theme intensity level

        Returns:
            New NarrativeTheme instance with updated intensity
        """
        return NarrativeTheme(
            theme_id=self.theme_id,
            theme_type=self.theme_type,
            intensity=new_intensity,
            name=self.name,
            description=self.description,
            symbolic_elements=self.symbolic_elements.copy(),
            related_motifs=self.related_motifs.copy(),
            character_archetypes=self.character_archetypes.copy(),
            introduction_sequence=self.introduction_sequence,
            resolution_sequence=self.resolution_sequence,
            peak_intensity_sequence=self.peak_intensity_sequence,
            development_trajectory=self.development_trajectory,
            conflicts_with_themes=self.conflicts_with_themes.copy(),
            reinforces_themes=self.reinforces_themes.copy(),
            moral_complexity=self.moral_complexity,
            emotional_resonance=self.emotional_resonance,
            universal_appeal=self.universal_appeal,
            expressed_through_dialogue=self.expressed_through_dialogue,
            expressed_through_action=self.expressed_through_action,
            expressed_through_symbolism=self.expressed_through_symbolism,
            expressed_through_setting=self.expressed_through_setting,
            expressed_through_character_arc=self.expressed_through_character_arc,
            cultural_context=self.cultural_context,
            historical_context=self.historical_context,
            target_audience_relevance=self.target_audience_relevance.copy(),
            tags=self.tags.copy(),
            creation_timestamp=self.creation_timestamp,
            metadata=self.metadata.copy(),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"NarrativeTheme('{self.name}', {self.theme_type.value}, {self.intensity.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"NarrativeTheme(id='{self.theme_id}', "
            f"type={self.theme_type.value}, "
            f"intensity={self.intensity.value}, "
            f"name='{self.name}')"
        )
