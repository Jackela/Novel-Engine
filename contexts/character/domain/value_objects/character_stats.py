#!/usr/bin/env python3
"""
Character Stats Value Object

This module implements character statistics and attributes including core
ability scores, health/mana, derived stats, and combat modifiers.

Follows P3 Sprint 3 patterns for type safety and validation.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Union

if TYPE_CHECKING:
    from ...infrastructure.character_domain_types import (
        ensure_float,
        ensure_int,
    )


class AbilityScore(Enum):
    """Core ability scores for characters."""

    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


@dataclass(frozen=True)
class CoreAbilities:
    """Value object representing the six core ability scores."""

    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    def __post_init__(self):
        """Validate ability scores with type safety."""
        from ...infrastructure.character_domain_types import (
            CharacterTypeGuards,
        )

        abilities = [
            ("strength", self.strength),
            ("dexterity", self.dexterity),
            ("constitution", self.constitution),
            ("intelligence", self.intelligence),
            ("wisdom", self.wisdom),
            ("charisma", self.charisma),
        ]

        for name, ability in abilities:
            if not CharacterTypeGuards.is_valid_ability_score(ability):
                raise ValueError(
                    f"Ability score '{name}' must be between 1 and 30, got {ability}"
                )

    def get_ability_score(self, ability: AbilityScore) -> int:
        """Get the score for a specific ability."""
        ability_map = {
            AbilityScore.STRENGTH: self.strength,
            AbilityScore.DEXTERITY: self.dexterity,
            AbilityScore.CONSTITUTION: self.constitution,
            AbilityScore.INTELLIGENCE: self.intelligence,
            AbilityScore.WISDOM: self.wisdom,
            AbilityScore.CHARISMA: self.charisma,
        }
        return ability_map[ability]

    def get_ability_modifier(self, ability: AbilityScore) -> int:
        """Calculate the modifier for an ability score."""
        score = self.get_ability_score(ability)
        return math.floor((score - 10) / 2)

    def get_all_modifiers(self) -> Dict[str, int]:
        """Get all ability modifiers as a dictionary."""
        return {
            ability.value: self.get_ability_modifier(ability)
            for ability in AbilityScore
        }

    def is_exceptional_ability(self, ability: AbilityScore) -> bool:
        """Check if an ability score is exceptional (18+)."""
        return self.get_ability_score(ability) >= 18

    def get_strongest_ability(self) -> AbilityScore:
        """Get the character's highest ability score."""
        scores = [
            (ability, self.get_ability_score(ability))
            for ability in AbilityScore
        ]
        return max(scores, key=lambda x: x[1])[0]

    def get_weakest_ability(self) -> AbilityScore:
        """Get the character's lowest ability score."""
        scores = [
            (ability, self.get_ability_score(ability))
            for ability in AbilityScore
        ]
        return min(scores, key=lambda x: x[1])[0]


@dataclass(frozen=True)
class VitalStats:
    """Value object representing health, mana, and other vital statistics."""

    max_health: int
    current_health: int
    max_mana: int
    current_mana: int
    max_stamina: int
    current_stamina: int
    armor_class: int
    speed: int  # Movement speed in feet/meters

    def __post_init__(self):
        """Validate vital statistics with type safety."""
        from ...infrastructure.character_domain_types import (
            CharacterTypeGuards,
        )

        if self.max_health <= 0:
            raise ValueError("Max health must be positive")

        if not CharacterTypeGuards.is_valid_health(self.current_health):
            raise ValueError(
                f"Current health must be non-negative, got {self.current_health}"
            )

        if not 0 <= self.current_health <= self.max_health:
            raise ValueError("Current health must be between 0 and max health")

        if self.max_mana < 0:
            raise ValueError("Max mana cannot be negative")

        if not 0 <= self.current_mana <= self.max_mana:
            raise ValueError("Current mana must be between 0 and max mana")

        if self.max_stamina < 0:
            raise ValueError("Max stamina cannot be negative")

        if not 0 <= self.current_stamina <= self.max_stamina:
            raise ValueError(
                "Current stamina must be between 0 and max stamina"
            )

        if not 0 <= self.armor_class <= 50:
            raise ValueError("Armor class must be between 0 and 50")

        if not 0 <= self.speed <= 200:
            raise ValueError("Speed must be between 0 and 200")

    def is_alive(self) -> bool:
        """Check if character is alive (health > 0)."""
        return self.current_health > 0

    def is_unconscious(self) -> bool:
        """Check if character is unconscious (health = 0)."""
        return self.current_health == 0

    def health_percentage(self) -> float:
        """Get current health as a percentage of max health."""
        return self.current_health / self.max_health

    def mana_percentage(self) -> float:
        """Get current mana as a percentage of max mana."""
        if self.max_mana == 0:
            return 1.0
        return self.current_mana / self.max_mana

    def stamina_percentage(self) -> float:
        """Get current stamina as a percentage of max stamina."""
        if self.max_stamina == 0:
            return 1.0
        return self.current_stamina / self.max_stamina

    def is_healthy(self) -> bool:
        """Check if character is at full health."""
        return self.current_health == self.max_health

    def is_wounded(self) -> bool:
        """Check if character is wounded (health < 50%)."""
        return self.health_percentage() < 0.5

    def is_critically_wounded(self) -> bool:
        """Check if character is critically wounded (health < 25%)."""
        return self.health_percentage() < 0.25

    def get_condition_summary(self) -> str:
        """Get a text summary of the character's condition."""
        health_pct = self.health_percentage()

        if health_pct == 1.0:
            return "Perfect Health"
        elif health_pct > 0.75:
            return "Lightly Wounded"
        elif health_pct > 0.5:
            return "Moderately Wounded"
        elif health_pct > 0.25:
            return "Heavily Wounded"
        elif health_pct > 0:
            return "Critically Wounded"
        else:
            return "Unconscious"


@dataclass(frozen=True)
class CombatStats:
    """Value object representing combat-related statistics."""

    base_attack_bonus: int
    initiative_modifier: int
    damage_reduction: int
    spell_resistance: int
    critical_hit_chance: float  # 0.0 to 1.0
    critical_damage_multiplier: float

    def __post_init__(self):
        """Validate combat statistics."""
        if not -10 <= self.base_attack_bonus <= 30:
            raise ValueError("Base attack bonus must be between -10 and 30")

        if not -10 <= self.initiative_modifier <= 20:
            raise ValueError("Initiative modifier must be between -10 and 20")

        if not 0 <= self.damage_reduction <= 50:
            raise ValueError("Damage reduction must be between 0 and 50")

        if not 0 <= self.spell_resistance <= 50:
            raise ValueError("Spell resistance must be between 0 and 50")

        if not 0.0 <= self.critical_hit_chance <= 1.0:
            raise ValueError("Critical hit chance must be between 0.0 and 1.0")

        if not 1.0 <= self.critical_damage_multiplier <= 10.0:
            raise ValueError(
                "Critical damage multiplier must be between 1.0 and 10.0"
            )

    def has_spell_resistance(self) -> bool:
        """Check if character has spell resistance."""
        return self.spell_resistance > 0

    def has_damage_reduction(self) -> bool:
        """Check if character has damage reduction."""
        return self.damage_reduction > 0

    def is_fast(self) -> bool:
        """Check if character has good initiative (positive modifier)."""
        return self.initiative_modifier > 0

    def get_combat_summary(self) -> Dict[str, str]:
        """Get a summary of combat capabilities."""
        return {
            "attack_skill": (
                "Expert"
                if self.base_attack_bonus > 15
                else (
                    "Skilled"
                    if self.base_attack_bonus > 10
                    else "Average"
                    if self.base_attack_bonus > 5
                    else "Novice"
                )
            ),
            "initiative": (
                "Fast"
                if self.initiative_modifier > 3
                else "Average"
                if self.initiative_modifier > -1
                else "Slow"
            ),
            "durability": (
                "Tough"
                if self.damage_reduction > 5
                else "Average"
                if self.damage_reduction > 0
                else "Fragile"
            ),
            "magic_resistance": (
                "High"
                if self.spell_resistance > 15
                else "Some"
                if self.spell_resistance > 0
                else "None"
            ),
        }


@dataclass(frozen=True)
class CharacterStats:
    """
    Complete character statistics value object.

    Encapsulates all numeric attributes that define a character's capabilities
    and current state. This is immutable and represents a snapshot in time.
    """

    core_abilities: CoreAbilities
    vital_stats: VitalStats
    combat_stats: CombatStats
    experience_points: int
    skill_points: int

    def __post_init__(self):
        """Validate character statistics with type safety."""
        if self.experience_points < 0:
            raise ValueError("Experience points cannot be negative")

        if self.skill_points < 0:
            raise ValueError("Skill points cannot be negative")

        if self.experience_points > 10_000_000:
            raise ValueError("Experience points cannot exceed 10 million")

        if self.skill_points > 1000:
            raise ValueError("Skill points cannot exceed 1000")

        # Validate that all nested value objects are properly initialized
        if not isinstance(self.core_abilities, CoreAbilities):
            raise TypeError("core_abilities must be a CoreAbilities instance")

        if not isinstance(self.vital_stats, VitalStats):
            raise TypeError("vital_stats must be a VitalStats instance")

        if not isinstance(self.combat_stats, CombatStats):
            raise TypeError("combat_stats must be a CombatStats instance")

    def get_ability_modifier(self, ability: AbilityScore) -> int:
        """Get the modifier for an ability score."""
        return self.core_abilities.get_ability_modifier(ability)

    def is_alive(self) -> bool:
        """Check if character is alive."""
        return self.vital_stats.is_alive()

    def can_cast_spells(self) -> bool:
        """Check if character has mana to cast spells."""
        return self.vital_stats.current_mana > 0

    def get_overall_power_level(self) -> str:
        """Get a general assessment of the character's power level."""
        # Simple power assessment based on multiple factors
        ability_total = sum(
            [
                self.core_abilities.strength,
                self.core_abilities.dexterity,
                self.core_abilities.constitution,
                self.core_abilities.intelligence,
                self.core_abilities.wisdom,
                self.core_abilities.charisma,
            ]
        )

        avg_ability = ability_total / 6
        health_factor = self.vital_stats.max_health / 100
        combat_factor = (self.combat_stats.base_attack_bonus + 10) / 20

        power_score = (avg_ability / 15) + health_factor + combat_factor

        if power_score > 3.0:
            return "Legendary"
        elif power_score > 2.5:
            return "Heroic"
        elif power_score > 2.0:
            return "Elite"
        elif power_score > 1.5:
            return "Skilled"
        elif power_score > 1.2:
            return "Average"
        else:
            return "Novice"

    def needs_rest(self) -> bool:
        """Check if character needs rest (low health/mana/stamina)."""
        return (
            self.vital_stats.health_percentage() < 0.3
            or self.vital_stats.mana_percentage() < 0.2
            or self.vital_stats.stamina_percentage() < 0.2
        )

    def get_stats_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of character statistics."""
        return {
            "power_level": self.get_overall_power_level(),
            "condition": self.vital_stats.get_condition_summary(),
            "strongest_ability": self.core_abilities.get_strongest_ability().value,
            "weakest_ability": self.core_abilities.get_weakest_ability().value,
            "combat_capabilities": self.combat_stats.get_combat_summary(),
            "experience_points": self.experience_points,
            "skill_points": self.skill_points,
            "needs_rest": self.needs_rest(),
        }

    @classmethod
    def create_with_validation(
        cls,
        strength: Union[int, str],
        dexterity: Union[int, str],
        constitution: Union[int, str],
        intelligence: Union[int, str],
        wisdom: Union[int, str],
        charisma: Union[int, str],
        **kwargs: Any,
    ) -> "CharacterStats":
        """Factory method to create CharacterStats with type validation."""
        from ...infrastructure.character_domain_types import ValueObjectFactory

        return ValueObjectFactory.create_character_stats_with_validation(
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=intelligence,
            wisdom=wisdom,
            charisma=charisma,
            **kwargs,
        )
