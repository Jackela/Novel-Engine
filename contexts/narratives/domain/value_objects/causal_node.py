#!/usr/bin/env python3
"""
Causal Node Value Object

This module defines value objects for representing cause-and-effect relationships
and causal structures within narrative systems.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional
from uuid import UUID


class CausalRelationType(Enum):
    """Types of causal relationships between narrative events."""

    DIRECT_CAUSE = "direct_cause"  # A directly causes B
    INDIRECT_CAUSE = "indirect_cause"  # A causes C which causes B
    NECESSARY_CONDITION = "necessary_condition"  # A must happen for B to occur
    SUFFICIENT_CONDITION = "sufficient_condition"  # A alone is enough to cause B
    CONTRIBUTING_FACTOR = "contributing_factor"  # A increases likelihood of B
    PREVENTING_FACTOR = "preventing_factor"  # A decreases likelihood of B
    CATALYST = "catalyst"  # A accelerates B but doesn't cause it
    INHIBITOR = "inhibitor"  # A slows down or delays B
    TRIGGER = "trigger"  # A activates dormant potential for B
    ENABLING_CONDITION = "enabling_condition"  # A makes B possible
    COINCIDENTAL = "coincidental"  # A and B occur together but aren't causal
    FEEDBACK_LOOP = "feedback_loop"  # A causes B which reinforces A


class CausalStrength(Enum):
    """Strength of causal relationships."""

    ABSOLUTE = "absolute"  # 100% certainty
    VERY_STRONG = "very_strong"  # 90-99% certainty
    STRONG = "strong"  # 70-89% certainty
    MODERATE = "moderate"  # 50-69% certainty
    WEAK = "weak"  # 30-49% certainty
    VERY_WEAK = "very_weak"  # 10-29% certainty
    NEGLIGIBLE = "negligible"  # 1-9% certainty


@dataclass(frozen=True)
class CausalNode:
    """
    Represents a node in a causal graph with cause-and-effect relationships.

    Causal nodes are immutable value objects that capture events, actions,
    or states within a narrative and their causal connections to other elements.
    """

    node_id: str
    event_id: Optional[str] = None  # Reference to specific narrative event
    plot_point_id: Optional[str] = None  # Reference to plot point
    character_id: Optional[UUID] = None  # Character involved in this causal node

    # Node description
    title: str = ""
    description: str = ""
    node_type: str = "event"  # event, action, state, condition, etc.

    # Causal relationships
    direct_causes: FrozenSet[str] = None  # Node IDs that directly cause this node
    direct_effects: FrozenSet[str] = None  # Node IDs directly caused by this node
    indirect_causes: FrozenSet[str] = None  # Node IDs that indirectly cause this node
    indirect_effects: FrozenSet[str] = None  # Node IDs indirectly caused by this node

    # Relationship metadata
    causal_relationships: Dict[str, Dict[str, Any]] = None  # Detailed relationship info

    # Temporal context
    sequence_order: Optional[int] = None
    temporal_delay: Optional[int] = None  # Time units between cause and effect
    duration: Optional[int] = None  # How long this node's effects last

    # Causal properties
    is_root_cause: bool = False  # No preceding causes
    is_terminal_effect: bool = False  # No subsequent effects
    is_branch_point: bool = False  # Multiple possible outcomes
    is_convergence_point: bool = False  # Multiple causes converge here

    # Probability and certainty
    occurrence_probability: Decimal = Decimal("1.0")  # 0-1, likelihood of occurring
    causal_certainty: Decimal = Decimal("0.8")  # 0-1, confidence in causal links

    # Impact and importance
    narrative_importance: Decimal = Decimal("5.0")  # 1-10 scale
    character_impact_level: Decimal = Decimal("5.0")  # 1-10 scale
    story_arc_impact: Decimal = Decimal("5.0")  # 1-10 scale

    # Conditions and constraints
    prerequisite_conditions: FrozenSet[str] = None  # Conditions required for this node
    blocking_conditions: FrozenSet[str] = None  # Conditions that prevent this node

    # Metadata
    tags: FrozenSet[str] = None
    narrative_context: str = ""
    creation_timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), compare=False
    )
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values and validate constraints."""
        # Convert mutable collections to immutable for hashability
        if self.direct_causes is None:
            object.__setattr__(self, "direct_causes", frozenset())
        elif isinstance(self.direct_causes, set):
            object.__setattr__(self, "direct_causes", frozenset(self.direct_causes))

        if self.direct_effects is None:
            object.__setattr__(self, "direct_effects", frozenset())
        elif isinstance(self.direct_effects, set):
            object.__setattr__(self, "direct_effects", frozenset(self.direct_effects))

        if self.indirect_causes is None:
            object.__setattr__(self, "indirect_causes", frozenset())
        elif isinstance(self.indirect_causes, set):
            object.__setattr__(self, "indirect_causes", frozenset(self.indirect_causes))

        if self.indirect_effects is None:
            object.__setattr__(self, "indirect_effects", frozenset())
        elif isinstance(self.indirect_effects, set):
            object.__setattr__(
                self, "indirect_effects", frozenset(self.indirect_effects)
            )

        if self.causal_relationships is None:
            object.__setattr__(self, "causal_relationships", {})

        if self.prerequisite_conditions is None:
            object.__setattr__(self, "prerequisite_conditions", frozenset())
        elif isinstance(self.prerequisite_conditions, set):
            object.__setattr__(
                self, "prerequisite_conditions", frozenset(self.prerequisite_conditions)
            )

        if self.blocking_conditions is None:
            object.__setattr__(self, "blocking_conditions", frozenset())
        elif isinstance(self.blocking_conditions, set):
            object.__setattr__(
                self, "blocking_conditions", frozenset(self.blocking_conditions)
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
        if not self.node_id or not self.node_id.strip():
            raise ValueError("Causal node ID cannot be empty")

        # Check for empty or whitespace-only title and description
        title_empty = not self.title or not self.title.strip()
        description_empty = not self.description or not self.description.strip()
        if title_empty and description_empty:
            raise ValueError("Causal node must have either title or description")

        # Validate probability values (0-1)
        if not (Decimal("0") <= self.occurrence_probability <= Decimal("1")):
            raise ValueError("Occurrence probability must be between 0 and 1")

        if not (Decimal("0") <= self.causal_certainty <= Decimal("1")):
            raise ValueError("Causal certainty must be between 0 and 1")

        # Validate impact values (1-10)
        for impact_name, impact_value in [
            ("narrative_importance", self.narrative_importance),
            ("character_impact_level", self.character_impact_level),
            ("story_arc_impact", self.story_arc_impact),
        ]:
            if not (Decimal("1") <= impact_value <= Decimal("10")):
                raise ValueError(f"{impact_name} must be between 1 and 10")

        # Validate sequence order
        if self.sequence_order is not None and self.sequence_order < 0:
            raise ValueError("Sequence order must be non-negative")

        # Validate durations
        if self.temporal_delay is not None and self.temporal_delay < 0:
            raise ValueError("Temporal delay must be non-negative")

        if self.duration is not None and self.duration <= 0:
            raise ValueError("Duration must be positive")

        # String length constraints
        if len(self.node_id) > 100:
            raise ValueError("Node ID too long (max 100 characters)")

        if len(self.title) > 200:
            raise ValueError("Node title too long (max 200 characters)")

        if len(self.description) > 1000:
            raise ValueError("Node description too long (max 1000 characters)")

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
                items.append((key, value))
            return frozenset(items)

        return (
            self.node_id,
            self.event_id,
            self.plot_point_id,
            self.character_id,
            self.title,
            self.description,
            self.node_type,
            self.direct_causes,
            self.direct_effects,
            self.indirect_causes,
            self.indirect_effects,
            _dict_to_hashable(self.causal_relationships),
            self.sequence_order,
            self.temporal_delay,
            self.duration,
            self.is_root_cause,
            self.is_terminal_effect,
            self.is_branch_point,
            self.is_convergence_point,
            self.occurrence_probability,
            self.causal_certainty,
            self.narrative_importance,
            self.character_impact_level,
            self.story_arc_impact,
            self.prerequisite_conditions,
            self.blocking_conditions,
            self.tags,
            self.narrative_context,
            _dict_to_hashable(self.metadata),
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, CausalNode):
            return NotImplemented
        return self._hash_components() == other._hash_components()

    def __hash__(self) -> int:
        """Custom hash implementation for frozen dataclass with Dict fields."""
        return hash(self._hash_components())

    @property
    def total_causes(self) -> int:
        """Total number of direct and indirect causes."""
        return len(self.direct_causes) + len(self.indirect_causes)

    @property
    def total_effects(self) -> int:
        """Total number of direct and indirect effects."""
        return len(self.direct_effects) + len(self.indirect_effects)

    @property
    def has_causes(self) -> bool:
        """Check if this node has any causal predecessors."""
        return bool(self.direct_causes or self.indirect_causes)

    @property
    def has_effects(self) -> bool:
        """Check if this node has any causal consequences."""
        return bool(self.direct_effects or self.indirect_effects)

    @property
    def is_isolated(self) -> bool:
        """Check if this node has no causal connections."""
        return not (self.has_causes or self.has_effects)

    @property
    def causal_complexity_score(self) -> Decimal:
        """
        Calculate the causal complexity of this node.

        Based on number of relationships and their types.
        """
        base_complexity = Decimal(str(self.total_causes + self.total_effects))

        # Add complexity for special node types
        complexity_bonus = Decimal("0")
        if self.is_branch_point:
            complexity_bonus += Decimal("2")
        if self.is_convergence_point:
            complexity_bonus += Decimal("2")
        if self.is_root_cause:
            complexity_bonus += Decimal("1")
        if self.is_terminal_effect:
            complexity_bonus += Decimal("1")

        # Add complexity for conditions
        complexity_bonus += Decimal(
            str(len(self.prerequisite_conditions) + len(self.blocking_conditions))
        ) * Decimal("0.5")

        return base_complexity + complexity_bonus

    @property
    def overall_impact_score(self) -> Decimal:
        """
        Calculate overall impact score combining all impact dimensions.
        """
        return (
            (self.narrative_importance * Decimal("0.4"))
            + (self.character_impact_level * Decimal("0.3"))
            + (self.story_arc_impact * Decimal("0.3"))
        )

    def causes_node(self, node_id: str) -> bool:
        """Check if this node causes another node (directly or indirectly)."""
        return node_id in self.direct_effects or node_id in self.indirect_effects

    def caused_by_node(self, node_id: str) -> bool:
        """Check if this node is caused by another node (directly or indirectly)."""
        return node_id in self.direct_causes or node_id in self.indirect_causes

    def directly_causes_node(self, node_id: str) -> bool:
        """Check if this node directly causes another node."""
        return node_id in self.direct_effects

    def directly_caused_by_node(self, node_id: str) -> bool:
        """Check if this node is directly caused by another node."""
        return node_id in self.direct_causes

    def get_relationship_info(self, other_node_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about relationship with another node."""
        return self.causal_relationships.get(other_node_id)

    def get_relationship_type(self, other_node_id: str) -> Optional[CausalRelationType]:
        """Get the type of relationship with another node."""
        rel_info = self.get_relationship_info(other_node_id)
        if rel_info and "relationship_type" in rel_info:
            return CausalRelationType(rel_info["relationship_type"])
        return None

    def get_relationship_strength(self, other_node_id: str) -> Optional[CausalStrength]:
        """Get the strength of relationship with another node."""
        rel_info = self.get_relationship_info(other_node_id)
        if rel_info and "strength" in rel_info:
            return CausalStrength(rel_info["strength"])
        return None

    def has_prerequisite_condition(self, condition: str) -> bool:
        """Check if this node has a specific prerequisite condition."""
        return condition in self.prerequisite_conditions

    def has_blocking_condition(self, condition: str) -> bool:
        """Check if this node has a specific blocking condition."""
        return condition in self.blocking_conditions

    def get_causal_context(self) -> Dict[str, Any]:
        """
        Get contextual information about this causal node.

        Returns:
            Dictionary containing causal context for analysis
        """
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "title": self.title,
            "sequence_order": self.sequence_order,
            "is_root_cause": self.is_root_cause,
            "is_terminal_effect": self.is_terminal_effect,
            "is_branch_point": self.is_branch_point,
            "is_convergence_point": self.is_convergence_point,
            "total_causes": self.total_causes,
            "total_effects": self.total_effects,
            "causal_complexity": float(self.causal_complexity_score),
            "overall_impact": float(self.overall_impact_score),
            "occurrence_probability": float(self.occurrence_probability),
            "causal_certainty": float(self.causal_certainty),
            "has_prerequisites": bool(self.prerequisite_conditions),
            "has_blocking_conditions": bool(self.blocking_conditions),
            "is_isolated": self.is_isolated,
        }

    def with_additional_cause(
        self,
        cause_node_id: str,
        relationship_type: CausalRelationType = CausalRelationType.DIRECT_CAUSE,
        strength: CausalStrength = CausalStrength.MODERATE,
    ) -> "CausalNode":
        """
        Create a new CausalNode with an additional cause relationship.

        Args:
            cause_node_id: ID of the causing node
            relationship_type: Type of causal relationship
            strength: Strength of the relationship

        Returns:
            New CausalNode instance with added cause
        """
        # Create updated frozensets using union operation
        if relationship_type == CausalRelationType.DIRECT_CAUSE:
            updated_direct_causes = self.direct_causes | {cause_node_id}
        else:
            updated_direct_causes = self.direct_causes

        updated_relationships = self.causal_relationships.copy()
        updated_relationships[cause_node_id] = {
            "relationship_type": relationship_type.value,
            "strength": strength.value,
            "direction": "incoming",
        }

        return CausalNode(
            node_id=self.node_id,
            event_id=self.event_id,
            plot_point_id=self.plot_point_id,
            character_id=self.character_id,
            title=self.title,
            description=self.description,
            node_type=self.node_type,
            direct_causes=updated_direct_causes,
            direct_effects=self.direct_effects,
            indirect_causes=self.indirect_causes,
            indirect_effects=self.indirect_effects,
            causal_relationships=updated_relationships,
            sequence_order=self.sequence_order,
            temporal_delay=self.temporal_delay,
            duration=self.duration,
            is_root_cause=False,  # No longer root cause if it has causes
            is_terminal_effect=self.is_terminal_effect,
            is_branch_point=self.is_branch_point,
            is_convergence_point=len(updated_direct_causes) > 1,
            occurrence_probability=self.occurrence_probability,
            causal_certainty=self.causal_certainty,
            narrative_importance=self.narrative_importance,
            character_impact_level=self.character_impact_level,
            story_arc_impact=self.story_arc_impact,
            prerequisite_conditions=self.prerequisite_conditions,
            blocking_conditions=self.blocking_conditions,
            tags=self.tags,
            narrative_context=self.narrative_context,
            creation_timestamp=self.creation_timestamp,
            metadata=self.metadata.copy(),
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"CausalNode('{self.title or self.node_id}', causes={self.total_causes}, effects={self.total_effects})"

    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return (
            f"CausalNode(id='{self.node_id}', "
            f"type='{self.node_type}', "
            f"title='{self.title}', "
            f"causes={self.total_causes}, "
            f"effects={self.total_effects})"
        )
