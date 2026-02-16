#!/usr/bin/env python3
"""
Character Psychology Value Object (Big Five Model)

This module implements the CharacterPsychology value object, which quantifies
personality using the Big Five (OCEAN) psychological model. This model is
widely used in psychology research and provides a standardized way to
describe personality traits.

Why Big Five:
    The Big Five model is empirically validated and provides a comprehensive
    yet parsimonious framework for personality description. Each dimension
    captures a major axis of personality variation that is stable across
    cultures and time.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CharacterPsychology:
    """
    Value object representing character personality using the Big Five model.

    The Big Five (OCEAN) traits:
    - Openness: Appreciation for art, emotion, adventure, unusual ideas, curiosity
    - Conscientiousness: Self-discipline, act dutifully, aim for achievement
    - Extraversion: Energy, positive emotions, assertiveness, sociability
    - Agreeableness: Tendency to be compassionate and cooperative
    - Neuroticism: Tendency to experience unpleasant emotions easily

    All traits are scored 0-100 where:
    - 0-30: Low
    - 31-70: Average
    - 71-100: High

    This is immutable and self-validating following DDD value object principles.
    """

    openness: int
    conscientiousness: int
    extraversion: int
    agreeableness: int
    neuroticism: int

    def __post_init__(self) -> None:
        """Validate that all trait scores are within valid range (0-100)."""
        traits = {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

        for trait_name, value in traits.items():
            if not isinstance(value, int):
                raise TypeError(
                    f"{trait_name} must be an integer, got {type(value).__name__}"
                )
            if value < 0 or value > 100:
                raise ValueError(f"{trait_name} must be between 0 and 100, got {value}")

    def get_trait_level(self, trait_name: str) -> str:
        """
        Get the qualitative level for a trait.

        Args:
            trait_name: One of 'openness', 'conscientiousness', 'extraversion',
                       'agreeableness', 'neuroticism'

        Returns:
            'low', 'average', or 'high' based on the trait score

        Raises:
            ValueError: If trait_name is not valid
        """
        trait_map = {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

        if trait_name not in trait_map:
            raise ValueError(
                f"Invalid trait name: {trait_name}. "
                f"Valid traits: {list(trait_map.keys())}"
            )

        value = trait_map[trait_name]
        if value <= 30:
            return "low"
        elif value <= 70:
            return "average"
        else:
            return "high"

    def get_dominant_traits(self, threshold: int = 70) -> list[str]:
        """
        Get traits that score above a threshold.

        Why this matters: Dominant traits are most likely to influence
        character behavior and dialogue, making them useful for AI prompts.

        Args:
            threshold: Minimum score to be considered dominant (default 70)

        Returns:
            List of trait names scoring above threshold
        """
        traits = {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }
        return [name for name, value in traits.items() if value > threshold]

    def get_weak_traits(self, threshold: int = 30) -> list[str]:
        """
        Get traits that score below a threshold.

        Why this matters: Weak traits indicate areas where the character
        might struggle or behave differently from the norm.

        Args:
            threshold: Maximum score to be considered weak (default 30)

        Returns:
            List of trait names scoring below threshold
        """
        traits = {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }
        return [name for name, value in traits.items() if value < threshold]

    def to_dict(self) -> Dict[str, int]:
        """
        Convert psychology to dictionary format.

        Returns:
            Dict with trait names as keys and scores as values
        """
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    def get_personality_summary(self) -> str:
        """
        Get a human-readable summary of the personality.

        Returns:
            A brief description of dominant and weak traits
        """
        dominant = self.get_dominant_traits()
        weak = self.get_weak_traits()

        parts = []
        if dominant:
            parts.append(f"High in: {', '.join(dominant)}")
        if weak:
            parts.append(f"Low in: {', '.join(weak)}")

        if not parts:
            return "Balanced personality across all Big Five traits"

        return "; ".join(parts)

    @classmethod
    def create_balanced(cls) -> "CharacterPsychology":
        """
        Factory method to create a balanced personality (all traits at 50).

        Why provide this: A balanced personality is a good starting point
        for character creation before specific traits are adjusted.

        Returns:
            CharacterPsychology with all traits at 50
        """
        return cls(
            openness=50,
            conscientiousness=50,
            extraversion=50,
            agreeableness=50,
            neuroticism=50,
        )
