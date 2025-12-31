#!/usr/bin/env python3
"""
Narrative Context Value Object

This module defines the NarrativeContext value object which encapsulates
contextual information about narrative elements and their relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional
from uuid import UUID


class ContextScope(Enum):
    """Scope of narrative context."""

    GLOBAL = "global"  # Affects entire narrative
    ARC = "arc"  # Limited to story arc
    CHAPTER = "chapter"  # Chapter-level context
    SCENE = "scene"  # Scene-level context
    MOMENT = "moment"  # Single moment context


class ContextType(Enum):
    """Types of narrative context."""

    SETTING = "setting"  # Physical/temporal location
    CULTURAL = "cultural"  # Cultural background
    HISTORICAL = "historical"  # Historical period
    SOCIAL = "social"  # Social dynamics
    POLITICAL = "political"  # Political situation
    ECONOMIC = "economic"  # Economic conditions
    TECHNOLOGICAL = "technological"  # Technology level
    MAGICAL = "magical"  # Magical/supernatural elements
    EMOTIONAL = "emotional"  # Emotional atmosphere
    THEMATIC = "thematic"  # Thematic context
    INTERPERSONAL = "interpersonal"  # Character relationships
    ENVIRONMENTAL = "environmental"  # Environmental conditions


@dataclass(frozen=True)
class NarrativeContext:
    """
    Represents contextual information for narrative elements.

    Narrative context provides background information, constraints,
    and environmental factors that influence story development.
    """

    context_id: str
    context_type: ContextType
    scope: ContextScope
    name: str
    description: str

    # Temporal information
    applies_from_sequence: Optional[int] = None
    applies_to_sequence: Optional[int] = None
    is_persistent: bool = True

    # Spatial information
    locations: FrozenSet[str] = None
    affected_regions: FrozenSet[str] = None
    geographical_scope: Optional[str] = None

    # Character context
    affected_characters: FrozenSet[UUID] = None
    character_knowledge_required: FrozenSet[
        UUID
    ] = None  # Characters who must know this context
    character_reactions: Dict[UUID, str] = None  # Expected character reactions

    # Contextual details
    key_facts: List[str] = None
    implicit_knowledge: List[str] = None  # Things everyone in context knows
    hidden_information: List[str] = None  # Information not generally known

    # Influence and constraints
    narrative_constraints: List[str] = None  # What this context prevents/requires
    behavioral_influences: List[str] = None  # How this affects character behavior
    plot_implications: List[str] = None  # Plot consequences of this context

    # Atmospheric elements
    mood_influences: Dict[str, Decimal] = None  # Mood effects (emotion -> strength)
    tension_modifiers: Dict[str, Decimal] = None  # Tension effects (type -> modifier)
    pacing_effects: Dict[str, Decimal] = None  # Pacing influences (aspect -> effect)

    # Relationship to other contexts
    prerequisite_contexts: FrozenSet[str] = None  # Required preceding contexts
    conflicting_contexts: FrozenSet[str] = None  # Mutually exclusive contexts
    reinforcing_contexts: FrozenSet[str] = None  # Contexts that strengthen this one

    # Importance and priority
    narrative_importance: Decimal = Decimal("5.0")  # 1-10, how critical this context is
    visibility_level: Decimal = Decimal("5.0")  # 1-10, how obvious to characters
    complexity_level: Decimal = Decimal("5.0")  # 1-10, how complex to understand

    # Dynamic properties
    evolution_rate: Decimal = Decimal("0.0")  # How quickly context changes (0-1)
    stability: Decimal = Decimal("1.0")  # How stable context is (0-1)

    # Metadata
    tags: FrozenSet[str] = None
    source_material: Optional[str] = None
    research_notes: str = ""
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), compare=False
    )
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values and validate constraints."""
        # Convert mutable collections to immutable for hashability
        if self.locations is None:
            object.__setattr__(self, "locations", frozenset())
        elif isinstance(self.locations, set):
            object.__setattr__(self, "locations", frozenset(self.locations))

        if self.affected_regions is None:
            object.__setattr__(self, "affected_regions", frozenset())
        elif isinstance(self.affected_regions, set):
            object.__setattr__(
                self, "affected_regions", frozenset(self.affected_regions)
            )

        if self.affected_characters is None:
            object.__setattr__(self, "affected_characters", frozenset())
        elif isinstance(self.affected_characters, set):
            object.__setattr__(
                self, "affected_characters", frozenset(self.affected_characters)
            )

        if self.character_knowledge_required is None:
            object.__setattr__(self, "character_knowledge_required", frozenset())
        elif isinstance(self.character_knowledge_required, set):
            object.__setattr__(
                self,
                "character_knowledge_required",
                frozenset(self.character_knowledge_required),
            )

        if self.character_reactions is None:
            object.__setattr__(self, "character_reactions", {})

        if self.key_facts is None:
            object.__setattr__(self, "key_facts", [])

        if self.implicit_knowledge is None:
            object.__setattr__(self, "implicit_knowledge", [])

        if self.hidden_information is None:
            object.__setattr__(self, "hidden_information", [])

        if self.narrative_constraints is None:
            object.__setattr__(self, "narrative_constraints", [])

        if self.behavioral_influences is None:
            object.__setattr__(self, "behavioral_influences", [])

        if self.plot_implications is None:
            object.__setattr__(self, "plot_implications", [])

        if self.mood_influences is None:
            object.__setattr__(self, "mood_influences", {})

        if self.tension_modifiers is None:
            object.__setattr__(self, "tension_modifiers", {})

        if self.pacing_effects is None:
            object.__setattr__(self, "pacing_effects", {})

        if self.prerequisite_contexts is None:
            object.__setattr__(self, "prerequisite_contexts", frozenset())
        elif isinstance(self.prerequisite_contexts, set):
            object.__setattr__(
                self, "prerequisite_contexts", frozenset(self.prerequisite_contexts)
            )

        if self.conflicting_contexts is None:
            object.__setattr__(self, "conflicting_contexts", frozenset())
        elif isinstance(self.conflicting_contexts, set):
            object.__setattr__(
                self, "conflicting_contexts", frozenset(self.conflicting_contexts)
            )

        if self.reinforcing_contexts is None:
            object.__setattr__(self, "reinforcing_contexts", frozenset())
        elif isinstance(self.reinforcing_contexts, set):
            object.__setattr__(
                self, "reinforcing_contexts", frozenset(self.reinforcing_contexts)
            )

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
        if not self.context_id or not self.context_id.strip():
            raise ValueError("Context ID cannot be empty")

        if not self.name or not self.name.strip():
            raise ValueError("Context name cannot be empty")

        if not self.description or not self.description.strip():
            raise ValueError("Context description cannot be empty")

        # Validate sequence ranges
        if (
            self.applies_from_sequence is not None
            and self.applies_to_sequence is not None
            and self.applies_from_sequence > self.applies_to_sequence
        ):
            raise ValueError("From sequence must be before or equal to to sequence")

        # Validate decimal values
        for value_name, value in [
            ("narrative_importance", self.narrative_importance),
            ("visibility_level", self.visibility_level),
            ("complexity_level", self.complexity_level),
        ]:
            if not (Decimal("1") <= value <= Decimal("10")):
                raise ValueError(f"{value_name} must be between 1 and 10")

        for rate_name, rate_value in [
            ("evolution_rate", self.evolution_rate),
            ("stability", self.stability),
        ]:
            if not (Decimal("0") <= rate_value <= Decimal("1")):
                raise ValueError(f"{rate_name} must be between 0 and 1")

        # Validate influence values
        for influence_dict in [
            self.mood_influences,
            self.tension_modifiers,
            self.pacing_effects,
        ]:
            for key, value in influence_dict.items():
                if not (-Decimal("10") <= value <= Decimal("10")):
                    raise ValueError(
                        f"Influence values must be between -10 and 10, got {value} for {key}"
                    )

        # String length constraints
        if len(self.context_id) > 100:
            raise ValueError("Context ID too long (max 100 characters)")

        if len(self.name) > 200:
            raise ValueError("Context name too long (max 200 characters)")

        if len(self.description) > 2000:
            raise ValueError("Context description too long (max 2000 characters)")

    def __hash__(self) -> int:
        """Custom hash implementation for frozen dataclass with Dict fields."""

        def _dict_to_hashable(d):
            if not d:
                return frozenset()
            items = []
            for k, v in sorted(d.items(), key=lambda x: (str(x[0]), str(x[1]))):
                # Convert UUID keys to strings for hashing
                k_hash = str(k) if isinstance(k, UUID) else k
                if isinstance(v, dict):
                    v = _dict_to_hashable(v)
                elif isinstance(v, list):
                    v = tuple(v)
                elif isinstance(v, Decimal):
                    v = float(v)
                items.append((k_hash, v))
            return frozenset(items)

        return hash(
            (
                self.context_id,
                self.context_type,
                self.scope,
                self.name,
                self.description,
                self.applies_from_sequence,
                self.applies_to_sequence,
                self.is_persistent,
                self.locations,
                self.affected_regions,
                self.geographical_scope,
                self.affected_characters,
                self.character_knowledge_required,
                _dict_to_hashable(self.character_reactions),
                tuple(self.key_facts) if self.key_facts else (),
                tuple(self.implicit_knowledge) if self.implicit_knowledge else (),
                tuple(self.hidden_information) if self.hidden_information else (),
                tuple(self.narrative_constraints) if self.narrative_constraints else (),
                tuple(self.behavioral_influences) if self.behavioral_influences else (),
                tuple(self.plot_implications) if self.plot_implications else (),
                _dict_to_hashable(self.mood_influences),
                _dict_to_hashable(self.tension_modifiers),
                _dict_to_hashable(self.pacing_effects),
                self.prerequisite_contexts,
                self.conflicting_contexts,
                self.reinforcing_contexts,
                self.narrative_importance,
                self.visibility_level,
                self.complexity_level,
                self.evolution_rate,
                self.stability,
                self.tags,
                self.source_material,
                self.research_notes,
                _dict_to_hashable(self.metadata),
            )
        )

    @property
    def has_sequence_range(self) -> bool:
        """Check if context has a defined sequence range."""
        return (
            self.applies_from_sequence is not None
            or self.applies_to_sequence is not None
        )

    @property
    def is_temporal_context(self) -> bool:
        """Check if context is temporally bounded."""
        return not self.is_persistent and self.has_sequence_range

    @property
    def affects_characters(self) -> bool:
        """Check if context affects specific characters."""
        return bool(self.affected_characters)

    @property
    def has_hidden_information(self) -> bool:
        """Check if context contains hidden information."""
        return bool(self.hidden_information)

    @property
    def has_narrative_constraints(self) -> bool:
        """Check if context imposes narrative constraints."""
        return bool(self.narrative_constraints)

    @property
    def influences_mood(self) -> bool:
        """Check if context influences mood."""
        return bool(self.mood_influences)

    @property
    def influences_pacing(self) -> bool:
        """Check if context influences pacing."""
        return bool(self.pacing_effects)

    @property
    def has_prerequisites(self) -> bool:
        """Check if context has prerequisite contexts."""
        return bool(self.prerequisite_contexts)

    @property
    def has_conflicts(self) -> bool:
        """Check if context conflicts with other contexts."""
        return bool(self.conflicting_contexts)

    @property
    def overall_influence_strength(self) -> Decimal:
        """
        Calculate overall strength of contextual influence.

        Based on importance, visibility, and number of influences.
        """
        base_strength = (
            self.narrative_importance * self.visibility_level / Decimal("10")
        )

        # Add strength from various influences
        influence_count = (
            len(self.mood_influences)
            + len(self.tension_modifiers)
            + len(self.pacing_effects)
            + len(self.behavioral_influences)
            + len(self.narrative_constraints)
        )

        influence_bonus = min(Decimal("3"), Decimal(str(influence_count * 0.2)))

        return min(Decimal("10"), base_strength + influence_bonus)

    @property
    def contextual_complexity_score(self) -> Decimal:
        """
        Calculate complexity score based on relationships and information.
        """
        base_complexity = self.complexity_level

        # Add complexity from relationships
        relationship_complexity = (
            len(self.prerequisite_contexts)
            + len(self.conflicting_contexts)
            + len(self.reinforcing_contexts)
        ) * Decimal("0.3")

        # Add complexity from information layers
        information_complexity = (
            len(self.key_facts)
            + len(self.implicit_knowledge)
            + len(self.hidden_information)
        ) * Decimal("0.1")

        return min(
            Decimal("10"),
            base_complexity + relationship_complexity + information_complexity,
        )

    def applies_at_sequence(self, sequence_number: int) -> bool:
        """Check if context applies at a specific sequence."""
        if not self.has_sequence_range:
            return self.is_persistent

        if (
            self.applies_from_sequence is not None
            and sequence_number < self.applies_from_sequence
        ):
            return False

        if (
            self.applies_to_sequence is not None
            and sequence_number > self.applies_to_sequence
        ):
            return False

        return True

    def affects_character(self, character_id: UUID) -> bool:
        """Check if context affects a specific character."""
        return character_id in self.affected_characters

    def character_knows_context(self, character_id: UUID) -> bool:
        """Check if a character is required to know this context."""
        return character_id in self.character_knowledge_required

    def get_character_reaction(self, character_id: UUID) -> Optional[str]:
        """Get expected character reaction to this context."""
        return self.character_reactions.get(character_id)

    def conflicts_with_context(self, context_id: str) -> bool:
        """Check if this context conflicts with another context."""
        return context_id in self.conflicting_contexts

    def reinforces_context(self, context_id: str) -> bool:
        """Check if this context reinforces another context."""
        return context_id in self.reinforcing_contexts

    def requires_context(self, context_id: str) -> bool:
        """Check if this context requires another context as prerequisite."""
        return context_id in self.prerequisite_contexts

    def get_mood_influence(self, mood_type: str) -> Decimal:
        """Get mood influence strength for a specific mood type."""
        return self.mood_influences.get(mood_type, Decimal("0"))

    def get_tension_modifier(self, tension_type: str) -> Decimal:
        """Get tension modifier for a specific tension type."""
        return self.tension_modifiers.get(tension_type, Decimal("0"))

    def get_pacing_effect(self, pacing_aspect: str) -> Decimal:
        """Get pacing effect for a specific pacing aspect."""
        return self.pacing_effects.get(pacing_aspect, Decimal("0"))

    def get_contextual_summary(self) -> Dict[str, Any]:
        """
        Get summary information about this narrative context.

        Returns:
            Dictionary containing context summary for analysis
        """
        return {
            "context_id": self.context_id,
            "type": self.context_type.value,
            "scope": self.scope.value,
            "name": self.name,
            "is_persistent": self.is_persistent,
            "has_sequence_range": self.has_sequence_range,
            "sequence_range": (
                [self.applies_from_sequence, self.applies_to_sequence]
                if self.has_sequence_range
                else None
            ),
            "affects_characters": self.affects_characters,
            "character_count": len(self.affected_characters),
            "location_count": len(self.locations),
            "influence_strength": float(self.overall_influence_strength),
            "complexity_score": float(self.contextual_complexity_score),
            "has_hidden_information": self.has_hidden_information,
            "has_constraints": self.has_narrative_constraints,
            "influences_mood": self.influences_mood,
            "influences_pacing": self.influences_pacing,
            "relationship_counts": {
                "prerequisites": len(self.prerequisite_contexts),
                "conflicts": len(self.conflicting_contexts),
                "reinforces": len(self.reinforcing_contexts),
            },
            "information_layers": {
                "key_facts": len(self.key_facts),
                "implicit_knowledge": len(self.implicit_knowledge),
                "hidden_information": len(self.hidden_information),
            },
        }

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"NarrativeContext('{self.name}', {self.context_type.value}, {self.scope.value})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"NarrativeContext(id='{self.context_id}', "
            f"type={self.context_type.value}, "
            f"scope={self.scope.value}, "
            f"name='{self.name}')"
        )
