#!/usr/bin/env python3
"""
Perception Range Value Object

This module implements value objects for managing perception ranges,
visibility calculations, and awareness zones in the subjective context.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class PerceptionType(Enum):
    """Types of perception available to entities."""

    VISUAL = "visual"
    AUDITORY = "auditory"
    TACTILE = "tactile"
    MAGICAL = "magical"
    PSYCHIC = "psychic"
    THERMAL = "thermal"
    VIBRATIONAL = "vibrational"


class VisibilityLevel(Enum):
    """Levels of visibility for perceived objects."""

    CLEAR = "clear"
    PARTIAL = "partial"
    OBSCURED = "obscured"
    HIDDEN = "hidden"
    INVISIBLE = "invisible"


@dataclass(frozen=True)
class PerceptionRange:
    """
    Value object representing the range and effectiveness of an entity's perception.

    This encapsulates the various sensory capabilities and their effective ranges,
    allowing for complex perception calculations in the fog of war system.
    """

    perception_type: PerceptionType
    base_range: float  # Base range in game units
    effective_range: float  # Current effective range (after modifiers)
    accuracy_modifier: float  # Perception accuracy (0.0-1.0)
    environmental_modifiers: Dict[str, float]  # Environmental effects on perception

    def __post_init__(self):
        """Validate perception range parameters."""
        if self.base_range < 0:
            raise ValueError("Base range cannot be negative")

        if self.effective_range < 0:
            raise ValueError("Effective range cannot be negative")

        if not 0.0 <= self.accuracy_modifier <= 1.0:
            raise ValueError("Accuracy modifier must be between 0.0 and 1.0")

        if self.environmental_modifiers:
            for modifier_name, value in self.environmental_modifiers.items():
                if not isinstance(modifier_name, str) or not modifier_name.strip():
                    raise ValueError(
                        "Environmental modifier names must be non-empty strings"
                    )
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"Environmental modifier '{modifier_name}' must be numeric"
                    )

    def calculate_visibility_at_distance(self, distance: float) -> VisibilityLevel:
        """Calculate visibility level at a specific distance."""
        if distance <= 0:
            return VisibilityLevel.CLEAR

        if distance > self.effective_range:
            return VisibilityLevel.INVISIBLE

        # Apply distance degradation
        distance_factor = distance / self.effective_range
        visibility_score = (1.0 - distance_factor) * self.accuracy_modifier

        # Apply environmental modifiers
        for modifier_value in self.environmental_modifiers.values():
            visibility_score *= modifier_value

        # Convert score to visibility level
        # Adjusted thresholds to be less strict - perfect conditions at 50% range should be PARTIAL
        if visibility_score >= 0.7:
            return VisibilityLevel.CLEAR
        elif visibility_score >= 0.5:
            return VisibilityLevel.PARTIAL
        elif visibility_score >= 0.3:
            return VisibilityLevel.OBSCURED
        elif visibility_score > 0.0:
            return VisibilityLevel.HIDDEN
        else:
            return VisibilityLevel.INVISIBLE

    def is_within_range(self, distance: float) -> bool:
        """Check if a distance is within perception range."""
        return distance <= self.effective_range

    def apply_environmental_modifier(
        self, modifier_name: str, modifier_value: float
    ) -> "PerceptionRange":
        """Create a new PerceptionRange with an additional environmental modifier."""
        new_modifiers = dict(self.environmental_modifiers)
        new_modifiers[modifier_name] = modifier_value

        return PerceptionRange(
            perception_type=self.perception_type,
            base_range=self.base_range,
            effective_range=self.effective_range,
            accuracy_modifier=self.accuracy_modifier,
            environmental_modifiers=new_modifiers,
        )


@dataclass(frozen=True)
class PerceptionCapabilities:
    """
    Value object representing the complete perception capabilities of an entity.

    This aggregates multiple perception ranges and provides methods for
    comprehensive awareness calculations.
    """

    perception_ranges: Dict[PerceptionType, PerceptionRange]
    passive_awareness_bonus: float = 0.0  # General awareness bonus
    focused_perception_multiplier: float = 1.5  # When actively focusing

    def __post_init__(self):
        """Validate perception capabilities."""
        if not self.perception_ranges:
            raise ValueError("Entity must have at least one perception range")

        for perception_type, perception_range in self.perception_ranges.items():
            if not isinstance(perception_type, PerceptionType):
                raise ValueError(f"Invalid perception type: {perception_type}")
            if not isinstance(perception_range, PerceptionRange):
                raise ValueError(f"Invalid perception range for {perception_type}")
            if perception_range.perception_type != perception_type:
                raise ValueError(
                    f"Perception range type mismatch for {perception_type}"
                )

        if self.passive_awareness_bonus < 0:
            raise ValueError("Passive awareness bonus cannot be negative")

        if self.focused_perception_multiplier <= 0:
            raise ValueError("Focused perception multiplier must be positive")

    def get_best_visibility_at_distance(
        self, distance: float, focused_perception: Optional[PerceptionType] = None
    ) -> VisibilityLevel:
        """Get the best visibility level achievable at a given distance."""
        best_visibility = VisibilityLevel.INVISIBLE

        for perception_type, perception_range in self.perception_ranges.items():
            # Apply focus modifier if this perception is being focused on
            effective_range = perception_range.effective_range
            if focused_perception == perception_type:
                effective_range *= self.focused_perception_multiplier

            # Create temporary range with potentially modified effective range
            temp_range = PerceptionRange(
                perception_type=perception_range.perception_type,
                base_range=perception_range.base_range,
                effective_range=effective_range,
                accuracy_modifier=perception_range.accuracy_modifier,
                environmental_modifiers=perception_range.environmental_modifiers,
            )

            visibility = temp_range.calculate_visibility_at_distance(distance)

            # Choose the best visibility level
            visibility_order = [
                VisibilityLevel.CLEAR,
                VisibilityLevel.PARTIAL,
                VisibilityLevel.OBSCURED,
                VisibilityLevel.HIDDEN,
                VisibilityLevel.INVISIBLE,
            ]

            if visibility_order.index(visibility) < visibility_order.index(
                best_visibility
            ):
                best_visibility = visibility

        return best_visibility

    def get_maximum_range(self) -> float:
        """Get the maximum perception range across all senses."""
        if not self.perception_ranges:
            return 0.0

        return max(pr.effective_range for pr in self.perception_ranges.values())

    def has_perception_type(self, perception_type: PerceptionType) -> bool:
        """Check if entity has a specific perception type."""
        return perception_type in self.perception_ranges

    def get_perception_types(self) -> List[PerceptionType]:
        """Get all available perception types."""
        return list(self.perception_ranges.keys())
