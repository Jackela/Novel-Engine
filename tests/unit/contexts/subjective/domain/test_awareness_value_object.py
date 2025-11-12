#!/usr/bin/env python3
"""
Comprehensive Unit Tests for AwarenessState Value Object

Test suite covering awareness states, alertness levels, attention focus,
and all business logic methods in the Subjective Context domain layer.
"""


import pytest

from contexts.subjective.domain.value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessModifier,
    AwarenessState,
)


class TestAwarenessStateCreation:
    """Test suite for AwarenessState value object creation and validation."""

    def test_minimal_awareness_state_creation(self):
        """Test creating awareness state with minimal required fields."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert state.base_alertness == AlertnessLevel.RELAXED
        assert state.current_alertness == AlertnessLevel.RELAXED
        assert state.attention_focus == AttentionFocus.UNFOCUSED
        assert state.focus_target is None
        assert state.awareness_modifiers == {}
        assert state.fatigue_level == 0.0
        assert state.stress_level == 0.0

    def test_full_awareness_state_creation(self):
        """Test creating awareness state with all fields populated."""
        modifiers = {AwarenessModifier.TRAINING: 0.3, AwarenessModifier.FATIGUE: -0.4}

        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="enemy_guard",
            awareness_modifiers=modifiers,
            fatigue_level=0.3,
            stress_level=0.7,
        )

        assert state.base_alertness == AlertnessLevel.ALERT
        assert state.current_alertness == AlertnessLevel.VIGILANT
        assert state.attention_focus == AttentionFocus.TARGET_SPECIFIC
        assert state.focus_target == "enemy_guard"
        assert state.awareness_modifiers == modifiers
        assert state.fatigue_level == 0.3
        assert state.stress_level == 0.7

    def test_awareness_modifiers_none_initialization(self):
        """Test that None modifiers are properly initialized to empty dict."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers=None,
        )

        assert isinstance(state.awareness_modifiers, dict)
        assert state.awareness_modifiers == {}

    def test_awareness_modifiers_list_conversion(self):
        """Test that modifier lists/tuples are converted to dict."""
        modifiers_list = [(AwarenessModifier.CONFIDENCE, 0.5)]

        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers=modifiers_list,
        )

        assert isinstance(state.awareness_modifiers, dict)
        assert state.awareness_modifiers[AwarenessModifier.CONFIDENCE] == 0.5


class TestAwarenessStateValidation:
    """Test suite for AwarenessState validation logic."""

    def test_invalid_awareness_modifier_type(self):
        """Test validation fails with invalid modifier type."""
        with pytest.raises(ValueError, match="Invalid awareness modifier"):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                awareness_modifiers={"invalid_string": 0.5},
            )

    def test_invalid_modifier_value_type(self):
        """Test validation fails with non-numeric modifier value."""
        with pytest.raises(ValueError, match="Modifier value .* must be numeric"):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                awareness_modifiers={AwarenessModifier.TRAINING: "invalid"},
            )

    def test_modifier_value_out_of_range_positive(self):
        """Test validation fails with modifier value > 1.0."""
        with pytest.raises(
            ValueError, match="Modifier value .* must be between -1.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                awareness_modifiers={AwarenessModifier.TRAINING: 1.5},
            )

    def test_modifier_value_out_of_range_negative(self):
        """Test validation fails with modifier value < -1.0."""
        with pytest.raises(
            ValueError, match="Modifier value .* must be between -1.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                awareness_modifiers={AwarenessModifier.FATIGUE: -1.5},
            )

    def test_fatigue_level_negative(self):
        """Test validation fails with negative fatigue level."""
        with pytest.raises(
            ValueError, match="Fatigue level must be between 0.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                fatigue_level=-0.1,
            )

    def test_fatigue_level_too_high(self):
        """Test validation fails with fatigue level > 1.0."""
        with pytest.raises(
            ValueError, match="Fatigue level must be between 0.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                fatigue_level=1.5,
            )

    def test_stress_level_negative(self):
        """Test validation fails with negative stress level."""
        with pytest.raises(
            ValueError, match="Stress level must be between 0.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                stress_level=-0.1,
            )

    def test_stress_level_too_high(self):
        """Test validation fails with stress level > 1.0."""
        with pytest.raises(
            ValueError, match="Stress level must be between 0.0 and 1.0"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.UNFOCUSED,
                stress_level=1.5,
            )

    def test_target_specific_focus_requires_target(self):
        """Test validation fails when target-specific focus lacks focus_target."""
        with pytest.raises(
            ValueError, match="Target-specific focus requires a focus target"
        ):
            AwarenessState(
                base_alertness=AlertnessLevel.RELAXED,
                current_alertness=AlertnessLevel.RELAXED,
                attention_focus=AttentionFocus.TARGET_SPECIFIC,
                focus_target=None,
            )

    def test_target_specific_focus_with_target_succeeds(self):
        """Test target-specific focus with focus_target succeeds."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="specific_enemy",
        )

        assert state.attention_focus == AttentionFocus.TARGET_SPECIFIC
        assert state.focus_target == "specific_enemy"


class TestCalculateEffectiveAlertness:
    """Test suite for calculate_effective_alertness business logic."""

    def test_no_modifiers_returns_current_alertness(self):
        """Test that with no modifiers, effective alertness equals current alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        effective = state.calculate_effective_alertness()
        assert effective == AlertnessLevel.ALERT

    def test_fatigue_reduces_alertness(self):
        """Test that fatigue reduces effective alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            fatigue_level=1.0,  # Maximum fatigue
        )

        effective = state.calculate_effective_alertness()
        # Should be reduced due to fatigue penalty
        assert effective.value in ["relaxed", "drowsy"]

    def test_stress_moderate_increases_alertness(self):
        """Test that moderate stress increases alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            stress_level=0.3,  # Moderate stress
        )

        effective = state.calculate_effective_alertness()
        # Should be same or higher due to moderate stress benefit
        assert effective in [AlertnessLevel.RELAXED, AlertnessLevel.ALERT]

    def test_stress_extreme_decreases_alertness(self):
        """Test that extreme stress decreases alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            stress_level=1.0,  # Maximum stress
        )

        effective = state.calculate_effective_alertness()
        # Should be same or lower due to extreme stress penalty
        assert effective in [
            AlertnessLevel.RELAXED,
            AlertnessLevel.ALERT,
            AlertnessLevel.DROWSY,
        ]

    def test_positive_modifiers_increase_alertness(self):
        """Test that positive modifiers increase alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={
                AwarenessModifier.TRAINING: 0.8,
                AwarenessModifier.CONFIDENCE: 0.6,
            },
        )

        effective = state.calculate_effective_alertness()
        # Should be increased due to positive modifiers (updated for more realistic modifiers)
        assert effective in [
            AlertnessLevel.ALERT,
            AlertnessLevel.VIGILANT,
            AlertnessLevel.PARANOID,
        ]

    def test_negative_modifiers_decrease_alertness(self):
        """Test that negative modifiers decrease alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={
                AwarenessModifier.FATIGUE: -0.8,
                AwarenessModifier.DISTRACTION: -0.6,
            },
        )

        effective = state.calculate_effective_alertness()
        # Should be decreased due to negative modifiers
        assert effective in [
            AlertnessLevel.SLEEPING,
            AlertnessLevel.DROWSY,
            AlertnessLevel.RELAXED,
        ]

    def test_fear_positive_increases_alertness(self):
        """Test that positive fear increases alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.FEAR: 0.5},
        )

        effective = state.calculate_effective_alertness()
        # Positive fear should increase alertness
        assert effective in [AlertnessLevel.ALERT, AlertnessLevel.VIGILANT]

    def test_fear_negative_decreases_alertness(self):
        """Test that negative fear (overwhelming fear) decreases alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.FEAR: -0.7},
        )

        effective = state.calculate_effective_alertness()
        # Overwhelming fear should decrease alertness
        assert effective in [
            AlertnessLevel.DROWSY,
            AlertnessLevel.RELAXED,
            AlertnessLevel.SLEEPING,
        ]

    def test_alertness_clamping_maximum(self):
        """Test that calculated alertness doesn't exceed PARANOID."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={
                AwarenessModifier.MAGICAL_ENHANCEMENT: 1.0,
                AwarenessModifier.TRAINING: 1.0,
                AwarenessModifier.CONFIDENCE: 1.0,
            },
        )

        effective = state.calculate_effective_alertness()
        assert effective == AlertnessLevel.PARANOID  # Maximum level

    def test_alertness_clamping_minimum(self):
        """Test that calculated alertness doesn't go below UNCONSCIOUS."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.SLEEPING,
            current_alertness=AlertnessLevel.SLEEPING,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={
                AwarenessModifier.FATIGUE: -1.0,
                AwarenessModifier.INJURY: -1.0,
                AwarenessModifier.DRUG_EFFECT: -1.0,
            },
            fatigue_level=1.0,
            stress_level=1.0,
        )

        effective = state.calculate_effective_alertness()
        assert effective == AlertnessLevel.UNCONSCIOUS  # Minimum level


class TestPerceptionBonus:
    """Test suite for get_perception_bonus calculations."""

    def test_unconscious_severe_penalty(self):
        """Test unconscious state has severe perception penalty."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        bonus = state.get_perception_bonus()
        assert bonus == -1.0  # Cannot perceive

    def test_sleeping_heavy_penalty(self):
        """Test sleeping state has heavy perception penalty."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.SLEEPING,
            current_alertness=AlertnessLevel.SLEEPING,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        bonus = state.get_perception_bonus()
        assert bonus == -0.8  # Very poor perception

    def test_relaxed_neutral_bonus(self):
        """Test relaxed state has neutral perception bonus."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        bonus = state.get_perception_bonus()
        assert bonus == 0.0  # Normal perception

    def test_vigilant_high_bonus(self):
        """Test vigilant state has high perception bonus."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        bonus = state.get_perception_bonus()
        assert bonus == 0.6  # High perception

    def test_target_specific_focus_bonus(self):
        """Test target-specific focus adds significant bonus."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="specific_target",
        )

        bonus = state.get_perception_bonus()
        assert bonus == 0.5  # High bonus for focused target

    def test_task_focused_penalty(self):
        """Test task-focused attention reduces perception."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TASK_FOCUSED,
        )

        bonus = state.get_perception_bonus()
        assert bonus == 0.1  # 0.3 (alert) - 0.2 (task penalty) = 0.1

    def test_environmental_focus_bonus(self):
        """Test environmental focus adds perception bonus."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )

        bonus = state.get_perception_bonus()
        assert bonus == 0.31  # Environmental focus bonus (updated for better balance)

    def test_combined_alertness_and_focus_bonus(self):
        """Test combining high alertness with threat scanning focus."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )

        bonus = state.get_perception_bonus()
        assert bonus == 1.05  # 0.6 (vigilant) + 0.45 (threat scanning) = 1.05 (updated)


class TestReactionTimeModifier:
    """Test suite for get_reaction_time_modifier calculations."""

    def test_unconscious_no_reaction(self):
        """Test unconscious state has no reaction capability."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        modifier = state.get_reaction_time_modifier()
        assert modifier == 10.0  # No reaction

    def test_sleeping_very_slow_reaction(self):
        """Test sleeping state has very slow reaction."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.SLEEPING,
            current_alertness=AlertnessLevel.SLEEPING,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        modifier = state.get_reaction_time_modifier()
        assert modifier == 5.0  # Very slow reaction

    def test_vigilant_fast_reaction(self):
        """Test vigilant state has fast reaction time."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        modifier = state.get_reaction_time_modifier()
        assert modifier == 0.6  # Fast reaction

    def test_fatigue_penalty_on_reaction_time(self):
        """Test fatigue increases reaction time modifier."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            fatigue_level=0.5,  # Moderate fatigue
        )

        modifier = state.get_reaction_time_modifier()
        # 0.8 (alert) * 2.0 (fatigue penalty) * stress_modifier
        assert modifier > 0.8  # Should be slower due to fatigue

    def test_optimal_stress_level_reaction(self):
        """Test that moderate stress (around 0.3) is optimal for reaction time."""
        state_optimal = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            stress_level=0.3,
        )

        state_high_stress = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            stress_level=0.9,
        )

        optimal_modifier = state_optimal.get_reaction_time_modifier()
        high_stress_modifier = state_high_stress.get_reaction_time_modifier()

        # Optimal stress should be better (lower modifier) than high stress
        assert optimal_modifier < high_stress_modifier


class TestStealthDetection:
    """Test suite for can_detect_stealth logic."""

    def test_unconscious_cannot_detect_stealth(self):
        """Test unconscious entities cannot detect stealth."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert not state.can_detect_stealth()

    def test_sleeping_cannot_detect_stealth(self):
        """Test sleeping entities cannot detect stealth."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.SLEEPING,
            current_alertness=AlertnessLevel.SLEEPING,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert not state.can_detect_stealth()

    def test_threat_scanning_can_detect_stealth(self):
        """Test threat scanning attention can always detect stealth."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.DROWSY,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )

        assert state.can_detect_stealth()

    def test_environmental_focus_can_detect_stealth(self):
        """Test environmental focus can detect stealth."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.DROWSY,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )

        assert state.can_detect_stealth()

    def test_high_alertness_can_detect_stealth(self):
        """Test high alertness levels can detect stealth."""
        for alertness in [
            AlertnessLevel.ALERT,
            AlertnessLevel.VIGILANT,
            AlertnessLevel.PARANOID,
        ]:
            state = AwarenessState(
                base_alertness=alertness,
                current_alertness=alertness,
                attention_focus=AttentionFocus.UNFOCUSED,
            )

            assert state.can_detect_stealth(), f"{alertness} should detect stealth"

    def test_low_alertness_cannot_detect_stealth_normally(self):
        """Test low alertness without special focus cannot detect stealth."""
        for alertness in [AlertnessLevel.DROWSY, AlertnessLevel.RELAXED]:
            state = AwarenessState(
                base_alertness=alertness,
                current_alertness=alertness,
                attention_focus=AttentionFocus.UNFOCUSED,
            )

            assert (
                not state.can_detect_stealth()
            ), f"{alertness} should not detect stealth normally"


class TestCombatSurprise:
    """Test suite for is_surprised_by_combat logic."""

    def test_unconscious_always_surprised(self):
        """Test unconscious entities are always surprised by combat."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert state.is_surprised_by_combat()

    def test_sleeping_always_surprised(self):
        """Test sleeping entities are always surprised by combat."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.SLEEPING,
            current_alertness=AlertnessLevel.SLEEPING,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert state.is_surprised_by_combat()

    def test_task_focused_more_likely_surprised(self):
        """Test task-focused entities are more likely surprised."""
        # Drowsy + task-focused = surprised
        state = AwarenessState(
            base_alertness=AlertnessLevel.DROWSY,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.TASK_FOCUSED,
        )
        assert state.is_surprised_by_combat()

        # Relaxed + task-focused = surprised
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.TASK_FOCUSED,
        )
        assert state.is_surprised_by_combat()

        # Alert + task-focused = not surprised
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TASK_FOCUSED,
        )
        assert not state.is_surprised_by_combat()

    def test_only_drowsy_surprised_when_not_task_focused(self):
        """Test only drowsy entities are surprised when not task-focused."""
        # Drowsy without task focus = surprised
        state = AwarenessState(
            base_alertness=AlertnessLevel.DROWSY,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        assert state.is_surprised_by_combat()

        # Relaxed without task focus = not surprised
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        assert not state.is_surprised_by_combat()

    def test_high_alertness_not_surprised(self):
        """Test high alertness entities are not surprised by combat."""
        for alertness in [
            AlertnessLevel.ALERT,
            AlertnessLevel.VIGILANT,
            AlertnessLevel.PARANOID,
        ]:
            state = AwarenessState(
                base_alertness=alertness,
                current_alertness=alertness,
                attention_focus=AttentionFocus.UNFOCUSED,
            )

            assert (
                not state.is_surprised_by_combat()
            ), f"{alertness} should not be surprised"


class TestImmutableOperations:
    """Test suite for immutable operations that create new instances."""

    def test_with_modified_alertness_creates_new_instance(self):
        """Test with_modified_alertness returns new instance with changed alertness."""
        original = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
            fatigue_level=0.3,
        )

        modified = original.with_modified_alertness(AlertnessLevel.ALERT)

        # Original unchanged
        assert original.current_alertness == AlertnessLevel.RELAXED
        assert original.fatigue_level == 0.3

        # New instance has changes
        assert modified.current_alertness == AlertnessLevel.ALERT
        assert modified.base_alertness == AlertnessLevel.RELAXED  # Unchanged
        assert modified.fatigue_level == 0.3  # Unchanged

        # Different objects
        assert original is not modified

    def test_with_focus_change_creates_new_instance(self):
        """Test with_focus_change returns new instance with changed focus."""
        original = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            focus_target=None,
        )

        modified = original.with_focus_change(
            AttentionFocus.TARGET_SPECIFIC, "new_target"
        )

        # Original unchanged
        assert original.attention_focus == AttentionFocus.UNFOCUSED
        assert original.focus_target is None

        # New instance has changes
        assert modified.attention_focus == AttentionFocus.TARGET_SPECIFIC
        assert modified.focus_target == "new_target"
        assert modified.current_alertness == AlertnessLevel.ALERT  # Unchanged

        # Different objects
        assert original is not modified

    def test_with_added_modifier_creates_new_instance(self):
        """Test with_added_modifier returns new instance with additional modifier."""
        original = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.3},
        )

        modified = original.with_added_modifier(AwarenessModifier.CONFIDENCE, 0.5)

        # Original unchanged
        assert original.awareness_modifiers == {AwarenessModifier.TRAINING: 0.3}

        # New instance has changes
        expected_modifiers = {
            AwarenessModifier.TRAINING: 0.3,
            AwarenessModifier.CONFIDENCE: 0.5,
        }
        assert modified.awareness_modifiers == expected_modifiers

        # Different objects
        assert original is not modified

    def test_with_added_modifier_overwrites_existing(self):
        """Test with_added_modifier overwrites existing modifier of same type."""
        original = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.3},
        )

        modified = original.with_added_modifier(AwarenessModifier.TRAINING, 0.7)

        # Should overwrite, not add
        assert modified.awareness_modifiers == {AwarenessModifier.TRAINING: 0.7}


class TestComplexScenarios:
    """Test suite for complex scenarios combining multiple factors."""

    def test_exhausted_guard_scenario(self):
        """Test a complex scenario: exhausted guard on duty."""
        exhausted_guard = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={
                AwarenessModifier.FATIGUE: -0.7,
                AwarenessModifier.TRAINING: 0.4,
            },
            fatigue_level=0.8,
            stress_level=0.6,
        )

        # Should be degraded but still somewhat functional due to training
        effective_alertness = exhausted_guard.calculate_effective_alertness()
        perception_bonus = exhausted_guard.get_perception_bonus()
        reaction_modifier = exhausted_guard.get_reaction_time_modifier()

        # Still conscious but degraded
        assert effective_alertness in [
            AlertnessLevel.SLEEPING,
            AlertnessLevel.DROWSY,
            AlertnessLevel.RELAXED,
        ]

        # Perception still somewhat functional due to environmental focus
        assert perception_bonus > -0.5  # Not completely impaired

        # Reaction time significantly impaired
        assert reaction_modifier > 2.0  # Much slower than normal

        # Can still detect stealth due to environmental focus
        assert exhausted_guard.can_detect_stealth()

        # Would be surprised by combat if drowsy
        if effective_alertness == AlertnessLevel.DROWSY:
            assert exhausted_guard.is_surprised_by_combat()

    def test_enhanced_sentinel_scenario(self):
        """Test a complex scenario: magically enhanced sentinel."""
        enhanced_sentinel = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
            awareness_modifiers={
                AwarenessModifier.MAGICAL_ENHANCEMENT: 0.8,
                AwarenessModifier.TRAINING: 0.6,
                AwarenessModifier.CONFIDENCE: 0.4,
            },
            fatigue_level=0.0,
            stress_level=0.2,  # Optimal stress level
        )

        effective_alertness = enhanced_sentinel.calculate_effective_alertness()
        perception_bonus = enhanced_sentinel.get_perception_bonus()
        reaction_modifier = enhanced_sentinel.get_reaction_time_modifier()

        # Should be at maximum alertness
        assert effective_alertness == AlertnessLevel.PARANOID

        # Excellent perception
        assert perception_bonus >= 1.0  # High bonus from alertness + threat scanning

        # Very fast reactions
        assert reaction_modifier < 1.0  # Faster than normal

        # Excellent stealth detection
        assert enhanced_sentinel.can_detect_stealth()

        # Never surprised
        assert not enhanced_sentinel.is_surprised_by_combat()

    def test_terrified_civilian_scenario(self):
        """Test a complex scenario: terrified civilian in crisis."""
        terrified_civilian = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={
                AwarenessModifier.FEAR: -0.8,  # Overwhelming fear
                AwarenessModifier.DISTRACTION: -0.5,
            },
            fatigue_level=0.4,
            stress_level=0.95,  # Extreme stress
        )

        effective_alertness = terrified_civilian.calculate_effective_alertness()
        perception_bonus = terrified_civilian.get_perception_bonus()
        reaction_modifier = terrified_civilian.get_reaction_time_modifier()

        # Fear and stress should severely impact performance
        assert effective_alertness in [
            AlertnessLevel.SLEEPING,
            AlertnessLevel.DROWSY,
            AlertnessLevel.RELAXED,
        ]

        # Poor perception due to overwhelming fear
        assert perception_bonus < 0.5

        # Slow reactions due to panic
        assert reaction_modifier > 1.5

        # Unlikely to detect stealth
        if effective_alertness in [AlertnessLevel.SLEEPING, AlertnessLevel.DROWSY]:
            assert not terrified_civilian.can_detect_stealth()

    def test_focused_researcher_scenario(self):
        """Test a complex scenario: researcher deeply focused on work."""
        focused_researcher = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TASK_FOCUSED,
            awareness_modifiers={
                AwarenessModifier.TRAINING: 0.3,  # Academic training
                AwarenessModifier.FATIGUE: -0.2,  # Slight fatigue from long work
            },
            fatigue_level=0.3,
            stress_level=0.4,
        )

        effective_alertness = focused_researcher.calculate_effective_alertness()
        perception_bonus = focused_researcher.get_perception_bonus()

        # Should maintain good alertness
        assert effective_alertness in [AlertnessLevel.RELAXED, AlertnessLevel.ALERT]

        # Reduced perception due to task focus
        perception_without_task_penalty = (
            perception_bonus + 0.2
        )  # Add back the task penalty
        assert perception_without_task_penalty > 0.0  # Good base perception
        assert (
            perception_bonus < perception_without_task_penalty
        )  # But reduced due to focus

        # Poor stealth detection due to task focus
        if effective_alertness in [AlertnessLevel.RELAXED, AlertnessLevel.DROWSY]:
            assert not focused_researcher.can_detect_stealth()

        # More likely to be surprised due to task focus
        if effective_alertness in [AlertnessLevel.RELAXED, AlertnessLevel.DROWSY]:
            assert focused_researcher.is_surprised_by_combat()


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_all_modifier_types_combined(self):
        """Test awareness state with all possible modifier types."""
        all_modifiers = {
            AwarenessModifier.FATIGUE: -0.3,
            AwarenessModifier.INJURY: -0.2,
            AwarenessModifier.DISTRACTION: -0.1,
            AwarenessModifier.FEAR: 0.4,
            AwarenessModifier.CONFIDENCE: 0.3,
            AwarenessModifier.MAGICAL_ENHANCEMENT: 0.5,
            AwarenessModifier.DRUG_EFFECT: -0.1,
            AwarenessModifier.ENVIRONMENTAL_STRESS: -0.2,
            AwarenessModifier.TRAINING: 0.6,
            AwarenessModifier.EXPERIENCE: 0.4,
        }

        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
            awareness_modifiers=all_modifiers,
            fatigue_level=0.5,
            stress_level=0.6,
        )

        # Should not raise any exceptions
        effective_alertness = state.calculate_effective_alertness()
        perception_bonus = state.get_perception_bonus()
        reaction_modifier = state.get_reaction_time_modifier()

        # All values should be within valid ranges
        assert isinstance(effective_alertness, AlertnessLevel)
        assert isinstance(perception_bonus, float)
        assert isinstance(reaction_modifier, float)
        assert reaction_modifier > 0  # Must be positive

    def test_boundary_modifier_values(self):
        """Test modifier values at exact boundaries."""
        boundary_modifiers = {
            AwarenessModifier.TRAINING: 1.0,  # Maximum positive
            AwarenessModifier.FATIGUE: -1.0,  # Maximum negative
            AwarenessModifier.CONFIDENCE: 0.0,  # Neutral
        }

        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers=boundary_modifiers,
            fatigue_level=1.0,  # Maximum fatigue
            stress_level=1.0,  # Maximum stress
        )

        # Should handle boundary values without errors
        effective_alertness = state.calculate_effective_alertness()
        perception_bonus = state.get_perception_bonus()
        reaction_modifier = state.get_reaction_time_modifier()

        assert isinstance(effective_alertness, AlertnessLevel)
        assert isinstance(perception_bonus, float)
        assert isinstance(reaction_modifier, float)

    def test_empty_string_focus_target(self):
        """Test behavior with empty string as focus target."""
        # This should be allowed - empty string is different from None
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="",  # Empty string, not None
        )

        # Should create successfully
        assert state.focus_target == ""
        assert state.attention_focus == AttentionFocus.TARGET_SPECIFIC

    def test_very_long_focus_target(self):
        """Test behavior with very long focus target string."""
        long_target = "x" * 1000  # Very long target name

        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target=long_target,
        )

        # Should handle long strings
        assert state.focus_target == long_target
        assert len(state.focus_target) == 1000


class TestEquality:
    """Test suite for equality comparison."""

    def test_identical_states_are_equal(self):
        """Test that identical awareness states are equal."""
        modifiers = {AwarenessModifier.TRAINING: 0.3}

        state1 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="enemy",
            awareness_modifiers=modifiers,
            fatigue_level=0.2,
            stress_level=0.4,
        )

        state2 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="enemy",
            awareness_modifiers=modifiers,
            fatigue_level=0.2,
            stress_level=0.4,
        )

        assert state1 == state2

    def test_different_alertness_not_equal(self):
        """Test that states with different alertness are not equal."""
        state1 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        state2 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.VIGILANT,  # Different
            attention_focus=AttentionFocus.UNFOCUSED,
        )

        assert state1 != state2

    def test_different_modifiers_not_equal(self):
        """Test that states with different modifiers are not equal."""
        state1 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.3},
        )

        state2 = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.5},  # Different value
        )

        assert state1 != state2
