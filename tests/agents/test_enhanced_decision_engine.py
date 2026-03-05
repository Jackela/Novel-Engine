#!/usr/bin/env python3
"""
Test suite for EnhancedDecisionEngine module.

Tests context-driven decision making and enhanced action evaluation.
"""

from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.agents.enhanced_decision_engine import EnhancedDecisionEngine


class TestEnhancedDecisionEngineInitialization:
    """Test EnhancedDecisionEngine initialization."""

    @pytest.fixture
    def mock_agent_core(self):
        """Create a mock agent core."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}
        return core

    def test_initialization(self, mock_agent_core):
        """Test basic initialization."""
        engine = EnhancedDecisionEngine(agent_core=mock_agent_core)

        assert engine.core == mock_agent_core
        assert engine.context_modifier_enabled is True
        assert "objective_alignment" in engine.modifier_weights

    def test_modifier_weights_sum(self, mock_agent_core):
        """Test that modifier weights sum to approximately 1.0."""
        engine = EnhancedDecisionEngine(agent_core=mock_agent_core)

        total = sum(engine.modifier_weights.values())
        assert 0.99 <= total <= 1.01  # Allow for floating point errors


class TestEnhancedDecisionEngineContextModifiers:
    """Test context modifier methods."""

    @pytest.fixture
    def engine_with_context(self):
        """Create engine with character data context."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {
            "enhanced_context": Mock(),
            "active_objectives": {
                "defend_base": {
                    "priority": 0.9,
                    "tier": "core",
                },
            },
            "behavioral_triggers": {
                "enemy_present": {
                    "conditions": ["enemy nearby"],
                    "response": "aggressive",
                },
            },
            "enhanced_relationships": {
                "ally": {"trust_level": 75},
            },
            "emotional_drives": {
                "security": {"weight": 0.8},
            },
            "formative_events": {
                "childhood": {
                    "trigger_phrases": ["danger"],
                    "decision_influence": "encourages caution",
                },
            },
        }
        return EnhancedDecisionEngine(agent_core=core)

    def test_apply_context_modifiers(self, engine_with_context):
        """Test applying context modifiers."""
        action: Dict[str, Any] = {"action_type": "defend", "target_character": "ally"}
        situation: Dict[str, Any] = {"location": "Station"}

        score = engine_with_context._apply_context_modifiers(0.5, action, situation)

        assert isinstance(score, float)
        assert 0.1 <= score <= 3.0

    def test_get_objective_alignment_modifier(self, engine_with_context):
        """Test objective alignment modifier."""
        action = {"action_type": "defend"}
        objectives = {
            "defend_base": {"priority": 0.9, "tier": "core"},
        }

        modifier = engine_with_context._get_objective_alignment_modifier(
            action, objectives
        )

        assert isinstance(modifier, float)
        assert modifier >= 1.0

    def test_get_objective_alignment_modifier_no_match(self, engine_with_context):
        """Test modifier with no matching objectives."""
        action = {"action_type": "explore"}
        objectives = {
            "defend_base": {"priority": 0.9, "tier": "core"},
        }

        modifier = engine_with_context._get_objective_alignment_modifier(
            action, objectives
        )

        assert modifier == 1.0  # No change

    def test_get_behavioral_trigger_modifier(self, engine_with_context):
        """Test behavioral trigger modifier."""
        action = {"action_type": "attack"}
        situation = {"condition": "enemy nearby"}
        triggers = {
            "danger": {
                "conditions": ["enemy"],
                "response": "aggressive",
            },
        }

        modifier = engine_with_context._get_behavioral_trigger_modifier(
            action, situation, triggers
        )

        assert isinstance(modifier, float)

    def test_get_relationship_modifier(self, engine_with_context):
        """Test relationship modifier."""
        action = {"action_type": "cooperate", "target_character": "ally"}
        relationships = {
            "ally": {"trust_level": 75},
        }

        modifier = engine_with_context._get_relationship_modifier(action, relationships)

        assert isinstance(modifier, float)
        assert modifier > 1.0  # Boosted by trust

    def test_get_relationship_modifier_attack(self, engine_with_context):
        """Test relationship modifier for attack action."""
        action = {"action_type": "attack", "target_character": "ally"}
        relationships = {
            "ally": {"trust_level": 75},
        }

        modifier = engine_with_context._get_relationship_modifier(action, relationships)

        assert isinstance(modifier, float)

    def test_get_relationship_modifier_no_target(self, engine_with_context):
        """Test modifier without target character."""
        action = {"action_type": "observe"}
        relationships = {"ally": {"trust_level": 75}}

        modifier = engine_with_context._get_relationship_modifier(action, relationships)

        assert modifier == 1.0

    def test_get_emotional_drive_modifier(self, engine_with_context):
        """Test emotional drive modifier."""
        action = {"action_type": "defend"}
        drives = {
            "security": {"weight": 0.9},
        }

        modifier = engine_with_context._get_emotional_drive_modifier(action, drives)

        assert isinstance(modifier, float)

    def test_get_memory_influence_modifier(self, engine_with_context):
        """Test memory influence modifier."""
        action = {"action_type": "wait"}
        situation = {"context": "danger"}
        events = {
            "trauma": {
                "trigger_phrases": ["danger"],
                "decision_influence": "encourages caution",
            },
        }

        modifier = engine_with_context._get_memory_influence_modifier(
            action, situation, events
        )

        assert isinstance(modifier, float)


class TestEnhancedDecisionEngineMatching:
    """Test context matching methods."""

    @pytest.fixture
    def engine(self):
        """Create EnhancedDecisionEngine."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_data = {}
        return EnhancedDecisionEngine(agent_core=core)

    def test_condition_matches_situation(self, engine):
        """Test condition matching."""
        condition = "enemy, danger"
        situation = {"status": "enemy nearby", "threat": "high danger"}

        matches = engine._condition_matches_situation(condition, situation)

        assert matches is True

    def test_condition_no_match(self, engine):
        """Test condition not matching."""
        condition = "peaceful"
        situation = {"status": "combat", "threat": "high"}

        matches = engine._condition_matches_situation(condition, situation)

        assert matches is False

    def test_phrase_matches_context(self, engine):
        """Test phrase matching context."""
        phrase = "danger, threat"
        action = {"type": "defend"}
        situation = {"description": "high danger zone"}

        matches = engine._phrase_matches_context(phrase, action, situation)

        assert matches is True


class TestEnhancedDecisionEngineEvaluation:
    """Test enhanced evaluation methods."""

    @pytest.fixture
    def engine(self):
        """Create EnhancedDecisionEngine."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_data = {}
        return EnhancedDecisionEngine(agent_core=core)

    def test_evaluate_action_option_no_context(self, engine):
        """Test evaluation without enhanced context."""
        action = {"action_type": "observe"}
        situation = {"location": "Station"}

        score = engine._evaluate_action_option(action, situation)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_evaluate_action_option_with_context(self, engine):
        """Test evaluation with enhanced context."""
        engine.core.character_data = {
            "enhanced_context": Mock(),
            "active_objectives": {"obj": {"priority": 0.5, "tier": "tactical"}},
        }
        action = {"action_type": "objective_related"}
        situation = {"location": "Station"}

        score = engine._evaluate_action_option(action, situation)

        assert isinstance(score, float)


class TestEnhancedDecisionEngineSummary:
    """Test summary generation."""

    @pytest.fixture
    def engine(self):
        """Create EnhancedDecisionEngine."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_data = {
            "enhanced_context": Mock(),
            "active_objectives": {"obj1": {}},
            "behavioral_triggers": {"trigger1": {}},
            "enhanced_relationships": {"rel1": {}},
            "emotional_drives": {"drive1": {}},
            "formative_events": {"event1": {}},
        }
        return EnhancedDecisionEngine(agent_core=core)

    def test_get_context_decision_summary(self, engine):
        """Test getting decision summary."""
        action = {"action_type": "observe", "target_character": "ally"}
        situation = {"location": "Station"}

        summary = engine.get_context_decision_summary(action, situation)

        assert summary["context_available"] is True
        assert "modifiers_applied" in summary
        assert summary["active_objectives_count"] == 1

    def test_get_context_decision_summary_no_context(self, engine):
        """Test summary without context."""
        engine.core.character_data = {}

        action = {"action_type": "observe"}
        situation = {}

        summary = engine.get_context_decision_summary(action, situation)

        assert summary["context_available"] is False


class TestEnhancedDecisionEngineEdgeCases:
    """Test edge cases."""

    def test_modifier_calculation_with_error(self):
        """Test modifier calculation with error."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_data = {"enhanced_context": Mock()}
        engine = EnhancedDecisionEngine(agent_core=core)

        # Corrupt data to cause error
        core.character_data["active_objectives"] = None

        score = engine._apply_context_modifiers(0.5, {"action_type": "test"}, {})

        assert isinstance(score, float)

    def test_context_modifiers_disabled(self):
        """Test with modifiers disabled."""
        core = Mock()
        core.agent_id = "test_agent"
        core.character_data = {"enhanced_context": Mock()}
        engine = EnhancedDecisionEngine(agent_core=core)
        engine.context_modifier_enabled = False

        action = {"action_type": "observe"}
        situation = {}

        score = engine._evaluate_action_option(action, situation)

        # Should fall back to base evaluation
        assert isinstance(score, float)


class TestEnhancedDecisionEngineIntegration:
    """Integration tests."""

    def test_full_evaluation_flow(self):
        """Test full evaluation with context."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Base"
        core.character_data = {
            "enhanced_context": Mock(),
            "active_objectives": {
                "defend_base": {"priority": 0.9, "tier": "core"},
            },
            "behavioral_triggers": {
                "combat": {"conditions": ["enemy"], "response": "aggressive"},
            },
            "enhanced_relationships": {
                "commander": {"trust_level": 90},
            },
            "emotional_drives": {
                "duty": {"weight": 0.9},
            },
            "formative_events": {
                "training": {"trigger_phrases": ["command"], "decision_influence": "follow orders"},
            },
        }

        engine = EnhancedDecisionEngine(agent_core=core)

        action = {"action_type": "defend", "target_character": "commander"}
        situation = {"location": "Base", "enemy": "present"}

        score = engine._evaluate_action_option(action, situation)

        assert isinstance(score, float)

        summary = engine.get_context_decision_summary(action, situation)
        assert summary["context_available"] is True
        assert len(summary["modifiers_applied"]) > 0
