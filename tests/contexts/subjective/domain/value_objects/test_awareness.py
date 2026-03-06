#!/usr/bin/env python3
"""
Awareness Value Object Tests

Tests for AwarenessState, AlertnessLevel, AttentionFocus, and AwarenessModifier.
Covers unit tests, integration tests, and boundary tests.
"""

from typing import Dict

import pytest

from src.contexts.subjective.domain.value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessModifier,
    AwarenessState,
)
pytestmark = pytest.mark.unit



# ============================================================================
# Unit Tests (15 tests)
# ============================================================================


@pytest.mark.unit
class TestAlertnessLevel:
    """Unit tests for AlertnessLevel enum."""

    def test_alertness_level_values(self):
        """Test alertness level enum values."""
        assert AlertnessLevel.UNCONSCIOUS.value == "unconscious"
        assert AlertnessLevel.SLEEPING.value == "sleeping"
        assert AlertnessLevel.DROWSY.value == "drowsy"
        assert AlertnessLevel.RELAXED.value == "relaxed"
        assert AlertnessLevel.ALERT.value == "alert"
        assert AlertnessLevel.VIGILANT.value == "vigilant"
        assert AlertnessLevel.PARANOID.value == "paranoid"


@pytest.mark.unit
class TestAttentionFocus:
    """Unit tests for AttentionFocus enum."""

    def test_attention_focus_values(self):
        """Test attention focus enum values."""
        assert AttentionFocus.UNFOCUSED.value == "unfocused"
        assert AttentionFocus.ENVIRONMENTAL.value == "environmental"
        assert AttentionFocus.TARGET_SPECIFIC.value == "target_specific"
        assert AttentionFocus.TASK_FOCUSED.value == "task_focused"
        assert AttentionFocus.THREAT_SCANNING.value == "threat_scanning"
        assert AttentionFocus.STEALTH_MODE.value == "stealth_mode"


@pytest.mark.unit
class TestAwarenessModifier:
    """Unit tests for AwarenessModifier enum."""

    def test_awareness_modifier_values(self):
        """Test awareness modifier enum values."""
        assert AwarenessModifier.FATIGUE.value == "fatigue"
        assert AwarenessModifier.INJURY.value == "injury"
        assert AwarenessModifier.DISTRACTION.value == "distraction"
        assert AwarenessModifier.FEAR.value == "fear"
        assert AwarenessModifier.CONFIDENCE.value == "confidence"
        assert AwarenessModifier.MAGICAL_ENHANCEMENT.value == "magical_enhancement"
        assert AwarenessModifier.DRUG_EFFECT.value == "drug_effect"
        assert AwarenessModifier.ENVIRONMENTAL_STRESS.value == "environmental_stress"
        assert AwarenessModifier.TRAINING.value == "training"
        assert AwarenessModifier.EXPERIENCE.value == "experience"


@pytest.mark.unit
class TestAwarenessState:
    """Unit tests for AwarenessState."""

    def test_create_basic_state(self):
        """Test creating basic awareness state."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )
        assert state.base_alertness == AlertnessLevel.ALERT
        assert state.current_alertness == AlertnessLevel.ALERT
        assert state.attention_focus == AttentionFocus.ENVIRONMENTAL

    def test_state_with_target(self):
        """Test state with focus target."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.TARGET_SPECIFIC,
            focus_target="enemy_1",
        )
        assert state.focus_target == "enemy_1"

    def test_state_with_modifiers(self):
        """Test state with awareness modifiers."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
            awareness_modifiers={
                AwarenessModifier.TRAINING: 0.5,
                AwarenessModifier.FATIGUE: -0.3,
            },
        )
        assert AwarenessModifier.TRAINING in state.awareness_modifiers
        assert state.awareness_modifiers[AwarenessModifier.TRAINING] == 0.5

    def test_state_with_fatigue(self):
        """Test state with fatigue level."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            fatigue_level=0.5,
        )
        assert state.fatigue_level == 0.5

    def test_state_with_stress(self):
        """Test state with stress level."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            stress_level=0.3,
        )
        assert state.stress_level == 0.3

    def test_calculate_effective_alertness_no_change(self):
        """Test effective alertness with no modifiers."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )
        effective = state.calculate_effective_alertness()
        assert effective == AlertnessLevel.ALERT

    def test_calculate_effective_alertness_with_positive_modifier(self):
        """Test effective alertness with positive modifier."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.8},
        )
        effective = state.calculate_effective_alertness()
        # Training should increase alertness
        assert effective in [AlertnessLevel.VIGILANT, AlertnessLevel.PARANOID]

    def test_calculate_effective_alertness_with_negative_modifier(self):
        """Test effective alertness with negative modifier."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={AwarenessModifier.FATIGUE: 0.8},
        )
        effective = state.calculate_effective_alertness()
        # Fatigue should decrease alertness
        assert effective in [AlertnessLevel.RELAXED, AlertnessLevel.DROWSY, AlertnessLevel.SLEEPING]

    def test_get_perception_bonus(self):
        """Test perception bonus calculation."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )
        bonus = state.get_perception_bonus()
        # Vigilant + threat scanning should give high bonus
        assert bonus > 0

    def test_get_reaction_time_modifier(self):
        """Test reaction time modifier calculation."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )
        modifier = state.get_reaction_time_modifier()
        # Vigilant should have fast reaction time (modifier < 1.0)
        assert modifier < 1.0

    def test_can_detect_stealth(self):
        """Test stealth detection capability."""
        vigilant_state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )
        assert vigilant_state.can_detect_stealth()

    def test_cannot_detect_stealth_when_unconscious(self):
        """Test stealth detection when unconscious."""
        unconscious_state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        assert not unconscious_state.can_detect_stealth()

    def test_is_surprised_by_combat(self):
        """Test combat surprise check."""
        drowsy_state = AwarenessState(
            base_alertness=AlertnessLevel.DROWSY,
            current_alertness=AlertnessLevel.DROWSY,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        assert drowsy_state.is_surprised_by_combat()

    def test_not_surprised_when_vigilant(self):
        """Test not surprised when vigilant."""
        vigilant_state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )
        assert not vigilant_state.is_surprised_by_combat()


# ============================================================================
# Integration Tests (8 tests)
# ============================================================================


@pytest.mark.integration
class TestAwarenessStateIntegration:
    """Integration tests for awareness state."""

    def test_state_with_modified_alertness(self):
        """Test state with modified alertness."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )
        
        new_state = state.with_modified_alertness(AlertnessLevel.ALERT)
        assert new_state.current_alertness == AlertnessLevel.ALERT
        assert new_state.base_alertness == AlertnessLevel.RELAXED  # Unchanged

    def test_state_with_focus_change(self):
        """Test state with focus change."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
        )
        
        new_state = state.with_focus_change(
            AttentionFocus.TARGET_SPECIFIC,
            new_target="target_1",
        )
        assert new_state.attention_focus == AttentionFocus.TARGET_SPECIFIC
        assert new_state.focus_target == "target_1"

    def test_state_with_added_modifier(self):
        """Test state with added modifier."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.5},
        )
        
        new_state = state.with_added_modifier(AwarenessModifier.FEAR, 0.3)
        assert AwarenessModifier.TRAINING in new_state.awareness_modifiers
        assert AwarenessModifier.FEAR in new_state.awareness_modifiers
        assert new_state.awareness_modifiers[AwarenessModifier.FEAR] == 0.3

    def test_full_state_modification_flow(self):
        """Test full state modification flow."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.RELAXED,
            current_alertness=AlertnessLevel.RELAXED,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        
        # Modify alertness
        state = state.with_modified_alertness(AlertnessLevel.ALERT)
        
        # Change focus
        state = state.with_focus_change(AttentionFocus.THREAT_SCANNING)
        
        # Add modifier
        state = state.with_added_modifier(AwarenessModifier.TRAINING, 0.5)
        
        assert state.current_alertness == AlertnessLevel.ALERT
        assert state.attention_focus == AttentionFocus.THREAT_SCANNING
        assert AwarenessModifier.TRAINING in state.awareness_modifiers


@pytest.mark.integration
class TestAwarenessBehaviorIntegration:
    """Integration tests for awareness behavior."""

    def test_fatigue_affects_perception(self):
        """Test that fatigue affects perception bonus."""
        fresh_state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            fatigue_level=0.0,
        )
        
        tired_state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            fatigue_level=0.8,
        )
        
        fresh_bonus = fresh_state.get_perception_bonus()
        tired_bonus = tired_state.get_perception_bonus()
        
        assert fresh_bonus > tired_bonus

    def test_focus_affects_perception(self):
        """Test that focus type affects perception bonus."""
        unfocused_state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        
        scanning_state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
        )
        
        unfocused_bonus = unfocused_state.get_perception_bonus()
        scanning_bonus = scanning_state.get_perception_bonus()
        
        assert scanning_bonus > unfocused_bonus


# ============================================================================
# Boundary Tests (7 tests)
# ============================================================================


@pytest.mark.unit
class TestAwarenessBoundaryConditions:
    """Boundary tests for awareness state."""

    def test_zero_fatigue(self):
        """Test with zero fatigue."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            fatigue_level=0.0,
        )
        assert state.fatigue_level == 0.0

    def test_maximum_fatigue(self):
        """Test with maximum fatigue."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            fatigue_level=1.0,
        )
        assert state.fatigue_level == 1.0

    def test_zero_stress(self):
        """Test with zero stress."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            stress_level=0.0,
        )
        assert state.stress_level == 0.0

    def test_maximum_stress(self):
        """Test with maximum stress."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            stress_level=1.0,
        )
        assert state.stress_level == 1.0

    def test_modifier_at_minimum(self):
        """Test modifier at minimum value."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={AwarenessModifier.FATIGUE: -1.0},
        )
        assert state.awareness_modifiers[AwarenessModifier.FATIGUE] == -1.0

    def test_modifier_at_maximum(self):
        """Test modifier at maximum value."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={AwarenessModifier.TRAINING: 1.0},
        )
        assert state.awareness_modifiers[AwarenessModifier.TRAINING] == 1.0

    def test_empty_modifiers(self):
        """Test with empty modifiers dict."""
        state = AwarenessState(
            base_alertness=AlertnessLevel.ALERT,
            current_alertness=AlertnessLevel.ALERT,
            attention_focus=AttentionFocus.ENVIRONMENTAL,
            awareness_modifiers={},
        )
        assert state.awareness_modifiers == {}


# Total: 15 unit + 8 integration + 7 boundary = 30 tests for awareness
