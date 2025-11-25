#!/usr/bin/env python3
"""
Unit tests for CharacterStats Value Object

Comprehensive test suite for the CharacterStats value object covering
ability scores, vital statistics, combat stats, and derived calculations.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

# Import the value objects we're testing
from contexts.character.domain.value_objects.character_stats import (
    AbilityScore,
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)


class TestCoreAbilities:
    """Test suite for CoreAbilities value object."""

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_core_abilities_creation_success(self):
        """Test successful core abilities creation."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        assert abilities.strength == 15
        assert abilities.dexterity == 14
        assert abilities.constitution == 16
        assert abilities.intelligence == 12
        assert abilities.wisdom == 13
        assert abilities.charisma == 11

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_core_abilities_validation_too_low(self):
        """Test validation fails for ability scores too low."""
        with pytest.raises(ValueError) as exc_info:
            CoreAbilities(
                strength=0,  # Too low
                dexterity=14,
                constitution=16,
                intelligence=12,
                wisdom=13,
                charisma=11,
            )
        assert "Ability scores must be between 1 and 30" in str(exc_info.value)

    @pytest.mark.unit
    def test_core_abilities_validation_too_high(self):
        """Test validation fails for ability scores too high."""
        with pytest.raises(ValueError) as exc_info:
            CoreAbilities(
                strength=15,
                dexterity=31,  # Too high
                constitution=16,
                intelligence=12,
                wisdom=13,
                charisma=11,
            )
        assert "Ability scores must be between 1 and 30" in str(exc_info.value)

    @pytest.mark.unit
    def test_core_abilities_boundary_values(self):
        """Test ability scores at boundary values."""
        # Minimum values
        min_abilities = CoreAbilities(
            strength=1,
            dexterity=1,
            constitution=1,
            intelligence=1,
            wisdom=1,
            charisma=1,
        )
        assert min_abilities.strength == 1

        # Maximum values
        max_abilities = CoreAbilities(
            strength=30,
            dexterity=30,
            constitution=30,
            intelligence=30,
            wisdom=30,
            charisma=30,
        )
        assert max_abilities.strength == 30

    # ==================== Method Tests ====================

    @pytest.mark.unit
    def test_get_ability_score(self):
        """Test getting specific ability scores."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        assert abilities.get_ability_score(AbilityScore.STRENGTH) == 15
        assert abilities.get_ability_score(AbilityScore.DEXTERITY) == 14
        assert abilities.get_ability_score(AbilityScore.CONSTITUTION) == 16
        assert abilities.get_ability_score(AbilityScore.INTELLIGENCE) == 12
        assert abilities.get_ability_score(AbilityScore.WISDOM) == 13
        assert abilities.get_ability_score(AbilityScore.CHARISMA) == 11

    @pytest.mark.unit
    def test_get_ability_modifier(self):
        """Test ability modifier calculations."""
        abilities = CoreAbilities(
            strength=15,  # Modifier: +2
            dexterity=8,  # Modifier: -1
            constitution=20,  # Modifier: +5
            intelligence=10,  # Modifier: +0
            wisdom=13,  # Modifier: +1
            charisma=6,  # Modifier: -2
        )

        assert abilities.get_ability_modifier(AbilityScore.STRENGTH) == 2
        assert abilities.get_ability_modifier(AbilityScore.DEXTERITY) == -1
        assert abilities.get_ability_modifier(AbilityScore.CONSTITUTION) == 5
        assert abilities.get_ability_modifier(AbilityScore.INTELLIGENCE) == 0
        assert abilities.get_ability_modifier(AbilityScore.WISDOM) == 1
        assert abilities.get_ability_modifier(AbilityScore.CHARISMA) == -2

    @pytest.mark.unit
    def test_get_ability_modifier_extreme_values(self):
        """Test ability modifier calculations for extreme values."""
        abilities = CoreAbilities(
            strength=1,  # Modifier: -5
            dexterity=30,  # Modifier: +10
            constitution=11,  # Modifier: +0
            intelligence=10,  # Modifier: +0
            wisdom=9,  # Modifier: -1
            charisma=18,  # Modifier: +4
        )

        assert abilities.get_ability_modifier(AbilityScore.STRENGTH) == -5
        assert abilities.get_ability_modifier(AbilityScore.DEXTERITY) == 10
        assert abilities.get_ability_modifier(AbilityScore.CONSTITUTION) == 0
        assert abilities.get_ability_modifier(AbilityScore.WISDOM) == -1
        assert abilities.get_ability_modifier(AbilityScore.CHARISMA) == 4

    @pytest.mark.unit
    def test_get_all_modifiers(self):
        """Test getting all ability modifiers as dictionary."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        modifiers = abilities.get_all_modifiers()

        assert modifiers["strength"] == 2
        assert modifiers["dexterity"] == 2
        assert modifiers["constitution"] == 3
        assert modifiers["intelligence"] == 1
        assert modifiers["wisdom"] == 1
        assert modifiers["charisma"] == 0

    @pytest.mark.unit
    def test_is_exceptional_ability(self):
        """Test exceptional ability detection (18+)."""
        abilities = CoreAbilities(
            strength=18,  # Exceptional
            dexterity=17,  # Not exceptional
            constitution=20,  # Exceptional
            intelligence=12,  # Not exceptional
            wisdom=13,  # Not exceptional
            charisma=11,  # Not exceptional
        )

        assert abilities.is_exceptional_ability(AbilityScore.STRENGTH) is True
        assert abilities.is_exceptional_ability(AbilityScore.DEXTERITY) is False
        assert abilities.is_exceptional_ability(AbilityScore.CONSTITUTION) is True
        assert abilities.is_exceptional_ability(AbilityScore.INTELLIGENCE) is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_strongest_ability(self):
        """Test finding strongest ability."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=20,  # Highest
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        assert abilities.get_strongest_ability() == AbilityScore.CONSTITUTION

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_weakest_ability(self):
        """Test finding weakest ability."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=8,  # Lowest
        )

        assert abilities.get_weakest_ability() == AbilityScore.CHARISMA

    @pytest.mark.unit
    def test_get_strongest_weakest_tie_handling(self):
        """Test handling of ties in strongest/weakest ability."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=15,
            constitution=15,  # Three-way tie for highest
            intelligence=10,
            wisdom=10,
            charisma=10,  # Three-way tie for lowest
        )

        # Should return one of the tied abilities
        strongest = abilities.get_strongest_ability()
        assert strongest in [
            AbilityScore.STRENGTH,
            AbilityScore.DEXTERITY,
            AbilityScore.CONSTITUTION,
        ]

        weakest = abilities.get_weakest_ability()
        assert weakest in [
            AbilityScore.INTELLIGENCE,
            AbilityScore.WISDOM,
            AbilityScore.CHARISMA,
        ]


class TestVitalStats:
    """Test suite for VitalStats value object."""

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_vital_stats_creation_success(self):
        """Test successful vital stats creation."""
        stats = VitalStats(
            max_health=50,
            current_health=45,
            max_mana=30,
            current_mana=25,
            max_stamina=40,
            current_stamina=35,
            armor_class=15,
            speed=30,
        )

        assert stats.max_health == 50
        assert stats.current_health == 45
        assert stats.max_mana == 30
        assert stats.current_mana == 25
        assert stats.max_stamina == 40
        assert stats.current_stamina == 35
        assert stats.armor_class == 15
        assert stats.speed == 30

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_vital_stats_validation_max_health_zero_fails(self):
        """Test validation fails for max health of zero."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=0,  # Invalid
                current_health=0,
                max_mana=10,
                current_mana=10,
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=30,
            )
        assert "Max health must be positive" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_current_health_exceeds_max_fails(self):
        """Test validation fails when current health exceeds max."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=60,  # Exceeds max
                max_mana=10,
                current_mana=10,
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=30,
            )
        assert "Current health must be between 0 and max health" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_current_health_negative_fails(self):
        """Test validation fails for negative current health."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=-1,  # Negative
                max_mana=10,
                current_mana=10,
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=30,
            )
        assert "Current health must be between 0 and max health" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_max_mana_negative_fails(self):
        """Test validation fails for negative max mana."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=50,
                max_mana=-1,  # Negative
                current_mana=0,
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=30,
            )
        assert "Max mana cannot be negative" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_current_mana_exceeds_max_fails(self):
        """Test validation fails when current mana exceeds max."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=50,
                max_mana=20,
                current_mana=25,  # Exceeds max
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=30,
            )
        assert "Current mana must be between 0 and max mana" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_armor_class_too_high_fails(self):
        """Test validation fails for armor class too high."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=50,
                max_mana=20,
                current_mana=20,
                max_stamina=20,
                current_stamina=20,
                armor_class=51,  # Too high
                speed=30,
            )
        assert "Armor class must be between 0 and 50" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_validation_speed_too_high_fails(self):
        """Test validation fails for speed too high."""
        with pytest.raises(ValueError) as exc_info:
            VitalStats(
                max_health=50,
                current_health=50,
                max_mana=20,
                current_mana=20,
                max_stamina=20,
                current_stamina=20,
                armor_class=10,
                speed=250,  # Too high
            )
        assert "Speed must be between 0 and 200" in str(exc_info.value)

    @pytest.mark.unit
    def test_vital_stats_boundary_values(self):
        """Test vital stats at boundary values."""
        # Test minimum values
        min_stats = VitalStats(
            max_health=1,  # Minimum positive
            current_health=0,  # Minimum (unconscious)
            max_mana=0,  # Minimum
            current_mana=0,  # Minimum
            max_stamina=0,  # Minimum
            current_stamina=0,  # Minimum
            armor_class=0,  # Minimum
            speed=0,  # Minimum
        )

        assert min_stats.max_health == 1
        assert min_stats.current_health == 0

        # Test maximum values
        max_stats = VitalStats(
            max_health=1000,  # High but valid
            current_health=1000,
            max_mana=500,  # High but valid
            current_mana=500,
            max_stamina=500,  # High but valid
            current_stamina=500,
            armor_class=50,  # Maximum
            speed=200,  # Maximum
        )

        assert max_stats.armor_class == 50
        assert max_stats.speed == 200

    # ==================== Status Methods Tests ====================

    @pytest.mark.unit
    def test_is_alive_with_health(self):
        """Test is_alive returns True when character has health."""
        stats = VitalStats(
            max_health=50,
            current_health=30,
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_alive() is True

    @pytest.mark.unit
    def test_is_alive_without_health(self):
        """Test is_alive returns False when character has no health."""
        stats = VitalStats(
            max_health=50,
            current_health=0,  # No health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_alive() is False

    @pytest.mark.unit
    def test_is_unconscious_at_zero_health(self):
        """Test is_unconscious returns True at zero health."""
        stats = VitalStats(
            max_health=50,
            current_health=0,  # Unconscious
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_unconscious() is True

    @pytest.mark.unit
    def test_is_unconscious_with_health(self):
        """Test is_unconscious returns False with health."""
        stats = VitalStats(
            max_health=50,
            current_health=1,  # Still alive
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_unconscious() is False

    @pytest.mark.unit
    def test_is_healthy_at_full_health(self):
        """Test is_healthy returns True at full health."""
        stats = VitalStats(
            max_health=50,
            current_health=50,  # Full health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_healthy() is True

    @pytest.mark.unit
    def test_is_healthy_not_at_full_health(self):
        """Test is_healthy returns False when not at full health."""
        stats = VitalStats(
            max_health=50,
            current_health=45,  # Not full health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_healthy() is False

    @pytest.mark.unit
    def test_is_wounded_below_half_health(self):
        """Test is_wounded returns True below 50% health."""
        stats = VitalStats(
            max_health=50,
            current_health=20,  # 40% health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_wounded() is True

    @pytest.mark.unit
    def test_is_wounded_above_half_health(self):
        """Test is_wounded returns False above 50% health."""
        stats = VitalStats(
            max_health=50,
            current_health=30,  # 60% health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_wounded() is False

    @pytest.mark.unit
    def test_is_critically_wounded_below_quarter_health(self):
        """Test is_critically_wounded returns True below 25% health."""
        stats = VitalStats(
            max_health=50,
            current_health=10,  # 20% health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_critically_wounded() is True

    @pytest.mark.unit
    def test_is_critically_wounded_above_quarter_health(self):
        """Test is_critically_wounded returns False above 25% health."""
        stats = VitalStats(
            max_health=50,
            current_health=15,  # 30% health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.is_critically_wounded() is False

    # ==================== Percentage Methods Tests ====================

    @pytest.mark.unit
    def test_health_percentage(self):
        """Test health percentage calculation."""
        stats = VitalStats(
            max_health=50,
            current_health=30,  # 60%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.health_percentage() == 0.6

    @pytest.mark.unit
    def test_mana_percentage_with_mana(self):
        """Test mana percentage calculation with mana."""
        stats = VitalStats(
            max_health=50,
            current_health=30,
            max_mana=20,
            current_mana=15,  # 75%
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.mana_percentage() == 0.75

    @pytest.mark.unit
    def test_mana_percentage_no_mana(self):
        """Test mana percentage returns 1.0 when max mana is 0."""
        stats = VitalStats(
            max_health=50,
            current_health=30,
            max_mana=0,
            current_mana=0,  # No mana system
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.mana_percentage() == 1.0

    @pytest.mark.unit
    def test_stamina_percentage_with_stamina(self):
        """Test stamina percentage calculation."""
        stats = VitalStats(
            max_health=50,
            current_health=30,
            max_mana=20,
            current_mana=15,
            max_stamina=40,
            current_stamina=20,  # 50%
            armor_class=12,
            speed=30,
        )

        assert stats.stamina_percentage() == 0.5

    @pytest.mark.unit
    def test_stamina_percentage_no_stamina(self):
        """Test stamina percentage returns 1.0 when max stamina is 0."""
        stats = VitalStats(
            max_health=50,
            current_health=30,
            max_mana=20,
            current_mana=15,
            max_stamina=0,
            current_stamina=0,  # No stamina system
            armor_class=12,
            speed=30,
        )

        assert stats.stamina_percentage() == 1.0

    # ==================== Condition Summary Tests ====================

    @pytest.mark.unit
    def test_get_condition_summary_perfect_health(self):
        """Test condition summary at perfect health."""
        stats = VitalStats(
            max_health=50,
            current_health=50,  # 100%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Perfect Health"

    @pytest.mark.unit
    def test_get_condition_summary_lightly_wounded(self):
        """Test condition summary when lightly wounded."""
        stats = VitalStats(
            max_health=50,
            current_health=40,  # 80%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Lightly Wounded"

    @pytest.mark.unit
    def test_get_condition_summary_moderately_wounded(self):
        """Test condition summary when moderately wounded."""
        stats = VitalStats(
            max_health=50,
            current_health=30,  # 60%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Moderately Wounded"

    @pytest.mark.unit
    def test_get_condition_summary_heavily_wounded(self):
        """Test condition summary when heavily wounded."""
        stats = VitalStats(
            max_health=50,
            current_health=20,  # 40%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Heavily Wounded"

    @pytest.mark.unit
    def test_get_condition_summary_critically_wounded(self):
        """Test condition summary when critically wounded."""
        stats = VitalStats(
            max_health=50,
            current_health=8,  # 16%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Critically Wounded"

    @pytest.mark.unit
    def test_get_condition_summary_unconscious(self):
        """Test condition summary when unconscious."""
        stats = VitalStats(
            max_health=50,
            current_health=0,  # 0%
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        assert stats.get_condition_summary() == "Unconscious"


class TestCombatStats:
    """Test suite for CombatStats value object."""

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_combat_stats_creation_success(self):
        """Test successful combat stats creation."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=3,
            spell_resistance=10,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.base_attack_bonus == 5
        assert stats.initiative_modifier == 2
        assert stats.damage_reduction == 3
        assert stats.spell_resistance == 10
        assert stats.critical_hit_chance == 0.15
        assert stats.critical_damage_multiplier == 2.5

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_combat_stats_validation_attack_bonus_too_low_fails(self):
        """Test validation fails for attack bonus too low."""
        with pytest.raises(ValueError) as exc_info:
            CombatStats(
                base_attack_bonus=-11,  # Too low
                initiative_modifier=2,
                damage_reduction=3,
                spell_resistance=10,
                critical_hit_chance=0.15,
                critical_damage_multiplier=2.5,
            )
        assert "Base attack bonus must be between -10 and 30" in str(exc_info.value)

    @pytest.mark.unit
    def test_combat_stats_validation_attack_bonus_too_high_fails(self):
        """Test validation fails for attack bonus too high."""
        with pytest.raises(ValueError) as exc_info:
            CombatStats(
                base_attack_bonus=31,  # Too high
                initiative_modifier=2,
                damage_reduction=3,
                spell_resistance=10,
                critical_hit_chance=0.15,
                critical_damage_multiplier=2.5,
            )
        assert "Base attack bonus must be between -10 and 30" in str(exc_info.value)

    @pytest.mark.unit
    def test_combat_stats_validation_initiative_modifier_too_low_fails(self):
        """Test validation fails for initiative modifier too low."""
        with pytest.raises(ValueError) as exc_info:
            CombatStats(
                base_attack_bonus=5,
                initiative_modifier=-11,  # Too low
                damage_reduction=3,
                spell_resistance=10,
                critical_hit_chance=0.15,
                critical_damage_multiplier=2.5,
            )
        assert "Initiative modifier must be between -10 and 20" in str(exc_info.value)

    @pytest.mark.unit
    def test_combat_stats_validation_critical_chance_too_high_fails(self):
        """Test validation fails for critical hit chance too high."""
        with pytest.raises(ValueError) as exc_info:
            CombatStats(
                base_attack_bonus=5,
                initiative_modifier=2,
                damage_reduction=3,
                spell_resistance=10,
                critical_hit_chance=1.5,  # Too high (>1.0)
                critical_damage_multiplier=2.5,
            )
        assert "Critical hit chance must be between 0.0 and 1.0" in str(exc_info.value)

    @pytest.mark.unit
    def test_combat_stats_validation_critical_multiplier_too_low_fails(self):
        """Test validation fails for critical damage multiplier too low."""
        with pytest.raises(ValueError) as exc_info:
            CombatStats(
                base_attack_bonus=5,
                initiative_modifier=2,
                damage_reduction=3,
                spell_resistance=10,
                critical_hit_chance=0.15,
                critical_damage_multiplier=0.5,  # Too low (<1.0)
            )
        assert "Critical damage multiplier must be between 1.0 and 10.0" in str(
            exc_info.value
        )

    @pytest.mark.unit
    def test_combat_stats_boundary_values(self):
        """Test combat stats at boundary values."""
        # Test minimum values
        min_stats = CombatStats(
            base_attack_bonus=-10,  # Minimum
            initiative_modifier=-10,  # Minimum
            damage_reduction=0,  # Minimum
            spell_resistance=0,  # Minimum
            critical_hit_chance=0.0,  # Minimum
            critical_damage_multiplier=1.0,  # Minimum
        )

        assert min_stats.base_attack_bonus == -10
        assert min_stats.critical_hit_chance == 0.0

        # Test maximum values
        max_stats = CombatStats(
            base_attack_bonus=30,  # Maximum
            initiative_modifier=20,  # Maximum
            damage_reduction=50,  # Maximum
            spell_resistance=50,  # Maximum
            critical_hit_chance=1.0,  # Maximum
            critical_damage_multiplier=10.0,  # Maximum
        )

        assert max_stats.base_attack_bonus == 30
        assert max_stats.critical_damage_multiplier == 10.0

    # ==================== Method Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_spell_resistance_with_resistance(self):
        """Test has_spell_resistance returns True with resistance."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=3,
            spell_resistance=10,  # Has resistance
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.has_spell_resistance() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_spell_resistance_without_resistance(self):
        """Test has_spell_resistance returns False without resistance."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=3,
            spell_resistance=0,  # No resistance
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.has_spell_resistance() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_damage_reduction_with_reduction(self):
        """Test has_damage_reduction returns True with reduction."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=5,  # Has reduction
            spell_resistance=0,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.has_damage_reduction() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_damage_reduction_without_reduction(self):
        """Test has_damage_reduction returns False without reduction."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=0,  # No reduction
            spell_resistance=0,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.has_damage_reduction() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_fast_positive_initiative(self):
        """Test is_fast returns True with positive initiative."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=3,  # Positive
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.is_fast() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_fast_zero_initiative(self):
        """Test is_fast returns False with zero initiative."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=0,  # Zero
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.is_fast() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_fast_negative_initiative(self):
        """Test is_fast returns False with negative initiative."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=-2,  # Negative
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        assert stats.is_fast() is False

    @pytest.mark.unit
    def test_get_combat_summary_expert_level(self):
        """Test combat summary for expert level character."""
        stats = CombatStats(
            base_attack_bonus=20,  # Expert
            initiative_modifier=5,  # Fast
            damage_reduction=8,  # Tough
            spell_resistance=20,  # High
            critical_hit_chance=0.15,
            critical_damage_multiplier=2.5,
        )

        summary = stats.get_combat_summary()

        assert summary["attack_skill"] == "Expert"
        assert summary["initiative"] == "Fast"
        assert summary["durability"] == "Tough"
        assert summary["magic_resistance"] == "High"

    @pytest.mark.unit
    def test_get_combat_summary_novice_level(self):
        """Test combat summary for novice level character."""
        stats = CombatStats(
            base_attack_bonus=2,  # Novice
            initiative_modifier=-2,  # Slow
            damage_reduction=0,  # Fragile
            spell_resistance=0,  # None
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

        summary = stats.get_combat_summary()

        assert summary["attack_skill"] == "Novice"
        assert summary["initiative"] == "Slow"
        assert summary["durability"] == "Fragile"
        assert summary["magic_resistance"] == "None"

    @pytest.mark.unit
    def test_get_combat_summary_average_level(self):
        """Test combat summary for average level character."""
        stats = CombatStats(
            base_attack_bonus=8,  # Average
            initiative_modifier=1,  # Average
            damage_reduction=2,  # Average
            spell_resistance=5,  # Some
            critical_hit_chance=0.1,
            critical_damage_multiplier=2.0,
        )

        summary = stats.get_combat_summary()

        assert summary["attack_skill"] == "Average"
        assert summary["initiative"] == "Average"
        assert summary["durability"] == "Average"
        assert summary["magic_resistance"] == "Some"


class TestCharacterStats:
    """Test suite for CharacterStats value object."""

    @pytest.fixture
    def sample_core_abilities(self) -> CoreAbilities:
        """Create sample core abilities for testing."""
        return CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

    @pytest.fixture
    def sample_vital_stats(self) -> VitalStats:
        """Create sample vital stats for testing."""
        return VitalStats(
            max_health=50,
            current_health=45,
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

    @pytest.fixture
    def sample_combat_stats(self) -> CombatStats:
        """Create sample combat stats for testing."""
        return CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=2,
            spell_resistance=8,
            critical_hit_chance=0.1,
            critical_damage_multiplier=2.0,
        )

    @pytest.fixture
    def sample_character_stats(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ) -> CharacterStats:
        """Create sample character stats for testing."""
        return CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1500,
            skill_points=25,
        )

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_character_stats_creation_success(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test successful character stats creation."""
        stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert stats.core_abilities == sample_core_abilities
        assert stats.vital_stats == sample_vital_stats
        assert stats.combat_stats == sample_combat_stats
        assert stats.experience_points == 1000
        assert stats.skill_points == 20

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_character_stats_validation_negative_experience_fails(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test validation fails for negative experience points."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStats(
                core_abilities=sample_core_abilities,
                vital_stats=sample_vital_stats,
                combat_stats=sample_combat_stats,
                experience_points=-1,  # Negative
                skill_points=20,
            )
        assert "Experience points cannot be negative" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_stats_validation_negative_skill_points_fails(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test validation fails for negative skill points."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStats(
                core_abilities=sample_core_abilities,
                vital_stats=sample_vital_stats,
                combat_stats=sample_combat_stats,
                experience_points=1000,
                skill_points=-1,  # Negative
            )
        assert "Skill points cannot be negative" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_stats_validation_experience_too_high_fails(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test validation fails for experience points too high."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStats(
                core_abilities=sample_core_abilities,
                vital_stats=sample_vital_stats,
                combat_stats=sample_combat_stats,
                experience_points=10_000_001,  # Too high
                skill_points=20,
            )
        assert "Experience points cannot exceed 10 million" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_stats_validation_skill_points_too_high_fails(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test validation fails for skill points too high."""
        with pytest.raises(ValueError) as exc_info:
            CharacterStats(
                core_abilities=sample_core_abilities,
                vital_stats=sample_vital_stats,
                combat_stats=sample_combat_stats,
                experience_points=1000,
                skill_points=1001,  # Too high
            )
        assert "Skill points cannot exceed 1000" in str(exc_info.value)

    @pytest.mark.unit
    def test_character_stats_boundary_values(
        self, sample_core_abilities, sample_vital_stats, sample_combat_stats
    ):
        """Test character stats at boundary values."""
        # Test minimum values
        min_stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=0,  # Minimum
            skill_points=0,  # Minimum
        )

        assert min_stats.experience_points == 0
        assert min_stats.skill_points == 0

        # Test maximum values
        max_stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=sample_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=10_000_000,  # Maximum
            skill_points=1000,  # Maximum
        )

        assert max_stats.experience_points == 10_000_000
        assert max_stats.skill_points == 1000

    # ==================== Method Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_ability_modifier(self, sample_character_stats):
        """Test getting ability modifier through character stats."""
        assert (
            sample_character_stats.get_ability_modifier(AbilityScore.STRENGTH) == 2
        )  # 15 -> +2
        assert (
            sample_character_stats.get_ability_modifier(AbilityScore.CONSTITUTION) == 3
        )  # 16 -> +3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_alive_when_alive(self, sample_character_stats):
        """Test is_alive returns True when character is alive."""
        assert sample_character_stats.is_alive() is True

    @pytest.mark.unit
    def test_is_alive_when_dead(self, sample_core_abilities, sample_combat_stats):
        """Test is_alive returns False when character is dead."""
        dead_vital_stats = VitalStats(
            max_health=50,
            current_health=0,  # Dead
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        dead_stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=dead_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert dead_stats.is_alive() is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_cast_spells_with_mana(self, sample_character_stats):
        """Test can_cast_spells returns True with mana."""
        assert sample_character_stats.can_cast_spells() is True

    @pytest.mark.unit
    def test_can_cast_spells_without_mana(
        self, sample_core_abilities, sample_combat_stats
    ):
        """Test can_cast_spells returns False without mana."""
        no_mana_vital_stats = VitalStats(
            max_health=50,
            current_health=45,
            max_mana=20,
            current_mana=0,  # No mana
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        no_mana_stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=no_mana_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert no_mana_stats.can_cast_spells() is False

    @pytest.mark.unit
    def test_get_overall_power_level_calculations(self):
        """Test overall power level calculations for different characters."""
        # Create a legendary character
        legendary_abilities = CoreAbilities(
            strength=25,
            dexterity=25,
            constitution=25,
            intelligence=25,
            wisdom=25,
            charisma=25,  # Average: 25
        )
        legendary_vital_stats = VitalStats(
            max_health=500,
            current_health=500,  # High health
            max_mana=200,
            current_mana=200,
            max_stamina=300,
            current_stamina=300,
            armor_class=25,
            speed=50,
        )
        legendary_combat_stats = CombatStats(
            base_attack_bonus=25,  # High attack
            initiative_modifier=10,
            damage_reduction=10,
            spell_resistance=30,
            critical_hit_chance=0.2,
            critical_damage_multiplier=3.0,
        )

        legendary_stats = CharacterStats(
            core_abilities=legendary_abilities,
            vital_stats=legendary_vital_stats,
            combat_stats=legendary_combat_stats,
            experience_points=5_000_000,
            skill_points=500,
        )

        assert legendary_stats.get_overall_power_level() == "Legendary"

        # Create a novice character
        novice_abilities = CoreAbilities(
            strength=8,
            dexterity=8,
            constitution=8,
            intelligence=8,
            wisdom=8,
            charisma=8,  # Average: 8
        )
        novice_vital_stats = VitalStats(
            max_health=20,
            current_health=20,  # Low health
            max_mana=5,
            current_mana=5,
            max_stamina=15,
            current_stamina=15,
            armor_class=8,
            speed=25,
        )
        novice_combat_stats = CombatStats(
            base_attack_bonus=-2,  # Low attack
            initiative_modifier=-1,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

        novice_stats = CharacterStats(
            core_abilities=novice_abilities,
            vital_stats=novice_vital_stats,
            combat_stats=novice_combat_stats,
            experience_points=0,
            skill_points=5,
        )

        assert novice_stats.get_overall_power_level() == "Novice"

    @pytest.mark.unit
    def test_needs_rest_low_health(self, sample_core_abilities, sample_combat_stats):
        """Test needs_rest returns True with low health."""
        low_health_vital_stats = VitalStats(
            max_health=50,
            current_health=10,  # 20% health
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=low_health_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert stats.needs_rest() is True

    @pytest.mark.unit
    def test_needs_rest_low_mana(self, sample_core_abilities, sample_combat_stats):
        """Test needs_rest returns True with low mana."""
        low_mana_vital_stats = VitalStats(
            max_health=50,
            current_health=45,
            max_mana=20,
            current_mana=2,  # 10% mana
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=low_mana_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert stats.needs_rest() is True

    @pytest.mark.unit
    def test_needs_rest_low_stamina(self, sample_core_abilities, sample_combat_stats):
        """Test needs_rest returns True with low stamina."""
        low_stamina_vital_stats = VitalStats(
            max_health=50,
            current_health=45,
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=4,  # 13% stamina
            armor_class=12,
            speed=30,
        )

        stats = CharacterStats(
            core_abilities=sample_core_abilities,
            vital_stats=low_stamina_vital_stats,
            combat_stats=sample_combat_stats,
            experience_points=1000,
            skill_points=20,
        )

        assert stats.needs_rest() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_needs_rest_good_condition(self, sample_character_stats):
        """Test needs_rest returns False in good condition."""
        assert sample_character_stats.needs_rest() is False

    @pytest.mark.unit
    def test_get_stats_summary(self, sample_character_stats):
        """Test comprehensive stats summary generation."""
        summary = sample_character_stats.get_stats_summary()

        assert "power_level" in summary
        assert "condition" in summary
        assert "strongest_ability" in summary
        assert "weakest_ability" in summary
        assert "combat_capabilities" in summary
        assert "experience_points" in summary
        assert "skill_points" in summary
        assert "needs_rest" in summary

        assert summary["experience_points"] == 1500
        assert summary["skill_points"] == 25
        assert summary["strongest_ability"] == "constitution"  # 16 is highest
        assert summary["weakest_ability"] == "charisma"  # 11 is lowest
        assert summary["needs_rest"] is False

    # ==================== Immutability Tests ====================

    @pytest.mark.unit
    def test_character_stats_immutability(self, sample_character_stats):
        """Test that character stats is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            sample_character_stats.experience_points = 2000

    @pytest.mark.unit
    def test_core_abilities_immutability(self):
        """Test that core abilities is immutable."""
        abilities = CoreAbilities(
            strength=15,
            dexterity=14,
            constitution=16,
            intelligence=12,
            wisdom=13,
            charisma=11,
        )

        with pytest.raises(AttributeError):
            abilities.strength = 20

    @pytest.mark.unit
    def test_vital_stats_immutability(self):
        """Test that vital stats is immutable."""
        stats = VitalStats(
            max_health=50,
            current_health=45,
            max_mana=20,
            current_mana=15,
            max_stamina=30,
            current_stamina=25,
            armor_class=12,
            speed=30,
        )

        with pytest.raises(AttributeError):
            stats.current_health = 50

    @pytest.mark.unit
    def test_combat_stats_immutability(self):
        """Test that combat stats is immutable."""
        stats = CombatStats(
            base_attack_bonus=5,
            initiative_modifier=2,
            damage_reduction=2,
            spell_resistance=8,
            critical_hit_chance=0.1,
            critical_damage_multiplier=2.0,
        )

        with pytest.raises(AttributeError):
            stats.base_attack_bonus = 10

    # ==================== Edge Cases and Integration Tests ====================

    @pytest.mark.unit
    def test_ability_modifier_calculation_precision(self):
        """Test ability modifier calculations maintain precision."""
        # Test edge cases in modifier calculation
        test_cases = [
            (1, -5),  # Minimum ability
            (8, -1),  # Just below average
            (9, -1),  # Just below average
            (10, 0),  # Average
            (11, 0),  # Just above average
            (12, 1),  # Above average
            (18, 4),  # Exceptional
            (30, 10),  # Maximum
        ]

        for ability_score, expected_modifier in test_cases:
            abilities = CoreAbilities(
                strength=ability_score,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
            )

            assert (
                abilities.get_ability_modifier(AbilityScore.STRENGTH)
                == expected_modifier
            )

    @pytest.mark.unit
    def test_character_stats_edge_case_combinations(self):
        """Test character stats with various edge case combinations."""
        # Test high-constitution, low-health character (magical effect scenario)
        high_con_abilities = CoreAbilities(
            strength=10,
            dexterity=10,
            constitution=25,  # Very high
            intelligence=10,
            wisdom=10,
            charisma=10,
        )

        low_health_vital_stats = VitalStats(
            max_health=30,  # Lower than expected for constitution
            current_health=5,  # Very low current health
            max_mana=0,  # No magic
            current_mana=0,
            max_stamina=50,  # High stamina from constitution
            current_stamina=50,
            armor_class=10,
            speed=30,
        )

        avg_combat_stats = CombatStats(
            base_attack_bonus=0,
            initiative_modifier=0,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

        edge_case_stats = CharacterStats(
            core_abilities=high_con_abilities,
            vital_stats=low_health_vital_stats,
            combat_stats=avg_combat_stats,
            experience_points=0,
            skill_points=0,
        )

        # Should still calculate correctly despite unusual combination
        assert (
            edge_case_stats.get_ability_modifier(AbilityScore.CONSTITUTION) == 7
        )  # 25 -> +7
        assert edge_case_stats.is_alive() is True  # Still has 5 health
        assert edge_case_stats.can_cast_spells() is False  # No mana
        assert edge_case_stats.needs_rest() is True  # Low health
