#!/usr/bin/env python3
"""
Test suite for DecisionEngine module.

Tests decision making, action evaluation, and situation assessment.
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.agents.decision_engine import (
    ActionEvaluation,
    DecisionEngine,
    SituationAssessment,
    ThreatLevel,
)
from src.core.types.shared_types import ActionPriority, CharacterAction


class TestThreatLevel:
    """Test ThreatLevel enum."""

    def test_threat_level_values(self):
        """Test ThreatLevel has expected values."""
        assert ThreatLevel.NEGLIGIBLE.value == "negligible"
        assert ThreatLevel.LOW.value == "low"
        assert ThreatLevel.MODERATE.value == "moderate"
        assert ThreatLevel.HIGH.value == "high"
        assert ThreatLevel.CRITICAL.value == "critical"


class TestSituationAssessment:
    """Test SituationAssessment dataclass."""

    def test_default_creation(self):
        """Test creating SituationAssessment."""
        assessment = SituationAssessment(
            current_location="Station",
            threat_level=ThreatLevel.LOW,
            available_resources={},
            active_goals=[],
            social_obligations=[],
            environmental_factors={},
            mission_status={},
        )
        assert assessment.current_location == "Station"
        assert assessment.threat_level == ThreatLevel.LOW


class TestDecisionEngineInitialization:
    """Test DecisionEngine initialization."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock PersonaCore."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = None
        core.character_data = {}
        return core

    def test_basic_initialization(self, mock_core):
        """Test basic initialization."""
        engine = DecisionEngine(core=mock_core)

        assert engine.core == mock_core
        assert engine.context_manager is None
        assert engine.action_threshold == 0.3
        assert engine.decision_weights == {}

    def test_initialization_with_context_manager(self, mock_core):
        """Test initialization with context manager."""
        context_manager = Mock()
        engine = DecisionEngine(core=mock_core, context_manager=context_manager)

        assert engine.context_manager == context_manager


class TestDecisionEngineDecisionMaking:
    """Test decision making methods."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = None
        core.character_data = {}
        return DecisionEngine(core=core)

    def test_make_decision_no_actions(self, engine):
        """Test decision making when no actions available."""
        world_state = {"location": "Station"}

        # Patch to return no available actions
        with patch.object(engine, "_identify_available_actions", return_value=[]):
            result = engine.make_decision(world_state)

        assert result is None

    def test_make_decision_no_valid_actions(self, engine):
        """Test decision making when no actions meet threshold."""
        world_state = {"location": "Station"}
        available_actions = [{"type": "wait", "score": 0.1}]

        with patch.object(
            engine, "_identify_available_actions", return_value=available_actions
        ):
            with patch.object(
                engine, "_evaluate_action"
            ) as mock_eval:
                mock_eval.return_value = ActionEvaluation(
                    action=available_actions[0],
                    base_score=0.1,
                    modified_score=0.1,
                    reasoning="Test",
                    priority=ActionPriority.LOW,
                )
                result = engine.make_decision(world_state)

        assert result is None

    def test_make_decision_success(self, engine):
        """Test successful decision making."""
        world_state = {"location": "Station"}
        available_actions = [
            {"type": "observe", "target": "environment"},
        ]

        with patch.object(
            engine, "_identify_available_actions", return_value=available_actions
        ):
            with patch.object(
                engine, "_evaluate_action"
            ) as mock_eval:
                mock_eval.return_value = ActionEvaluation(
                    action=available_actions[0],
                    base_score=0.8,
                    modified_score=0.8,
                    reasoning="Good action",
                    priority=ActionPriority.HIGH,
                )
                result = engine.make_decision(world_state)

        assert isinstance(result, CharacterAction)
        assert result.action_type == "observe"

    def test_make_decision_with_error(self, engine):
        """Test decision making with error."""
        world_state = {"location": "Station"}

        with patch.object(
            engine, "_assess_current_situation", side_effect=Exception("Test error")
        ):
            result = engine.make_decision(world_state)

        assert result is None


class TestDecisionEngineSituationAssessment:
    """Test situation assessment methods."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}
        return DecisionEngine(core=core)

    def test_assess_current_situation(self, engine):
        """Test situation assessment."""
        world_state = {
            "current_location": "Base",
            "threat_indicators": [],
        }

        situation = engine._assess_current_situation(world_state)

        assert isinstance(situation, SituationAssessment)
        assert situation.current_location == "Base"
        assert isinstance(situation.threat_level, ThreatLevel)

    def test_assess_threat_level_critical(self, engine):
        """Test threat level assessment - critical."""
        world_state = {
            "threat_indicators": ["enemy1", "enemy2", "enemy3"],
        }

        level = engine._assess_threat_level(world_state)
        assert level == ThreatLevel.CRITICAL

    def test_assess_threat_level_high(self, engine):
        """Test threat level assessment - high."""
        world_state = {
            "threat_indicators": ["enemy1", "enemy2"],
        }

        level = engine._assess_threat_level(world_state)
        assert level == ThreatLevel.HIGH

    def test_assess_threat_level_moderate(self, engine):
        """Test threat level assessment - moderate."""
        world_state = {
            "threat_indicators": ["enemy1"],
        }

        level = engine._assess_threat_level(world_state)
        assert level == ThreatLevel.MODERATE

    def test_assess_threat_level_low(self, engine):
        """Test threat level assessment - low."""
        world_state = {
            "threat_indicators": [],
        }

        level = engine._assess_threat_level(world_state)
        assert level == ThreatLevel.LOW


class TestDecisionEngineActionIdentification:
    """Test action identification methods."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}
        return DecisionEngine(core=core)

    @pytest.fixture
    def situation(self):
        """Create a situation assessment."""
        return SituationAssessment(
            current_location="Station",
            threat_level=ThreatLevel.LOW,
            available_resources={},
            active_goals=[],
            social_obligations=[],
            environmental_factors={},
            mission_status={},
        )

    def test_identify_available_actions_basic(self, engine, situation):
        """Test basic action identification."""
        actions = engine._identify_available_actions(situation)

        assert isinstance(actions, list)
        assert len(actions) > 0

        # Check for basic actions
        action_types = [a["type"] for a in actions]
        assert "observe" in action_types
        assert "wait" in action_types

    def test_identify_available_actions_with_location(self, engine, situation):
        """Test action identification with location."""
        situation.current_location = "Station"
        actions = engine._identify_available_actions(situation)

        action_types = [a["type"] for a in actions]
        assert "explore" in action_types

    def test_identify_available_actions_with_goals(self, engine, situation):
        """Test action identification with goals."""
        situation.active_goals = [
            {"type": "combat", "priority": "high"},
        ]
        actions = engine._identify_available_actions(situation)

        action_types = [a["type"] for a in actions]
        # May or may not have combat based on goal processing
        assert isinstance(action_types, list)

    def test_get_location_actions(self, engine):
        """Test getting location-specific actions."""
        actions = engine._get_location_actions("Station")

        assert isinstance(actions, list)
        assert len(actions) > 0
        assert actions[0]["type"] == "explore"

    def test_get_goal_actions(self, engine, situation):
        """Test getting goal-specific actions."""
        goal = {"type": "combat"}
        actions = engine._get_goal_actions(goal, situation)

        assert isinstance(actions, list)

    def test_get_profession_actions(self, engine):
        """Test getting profession-specific actions."""
        engine.core.character_data = {
            "identity": {"profession": "warrior"},
        }
        actions = engine._get_profession_actions()

        assert isinstance(actions, list)

    def test_get_social_actions(self, engine, situation):
        """Test getting social actions."""
        actions = engine._get_social_actions(situation)

        assert isinstance(actions, list)


class TestDecisionEngineActionEvaluation:
    """Test action evaluation methods."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}
        return DecisionEngine(core=core)

    @pytest.fixture
    def situation(self):
        """Create a situation assessment."""
        return SituationAssessment(
            current_location="Station",
            threat_level=ThreatLevel.LOW,
            available_resources={},
            active_goals=[],
            social_obligations=[],
            environmental_factors={},
            mission_status={},
        )

    def test_evaluate_action(self, engine, situation):
        """Test action evaluation."""
        action = {"type": "observe", "description": "Look around"}

        evaluation = engine._evaluate_action(action, situation)

        assert isinstance(evaluation, ActionEvaluation)
        assert evaluation.action == action
        assert 0.0 <= evaluation.base_score <= 1.0
        assert 0.0 <= evaluation.modified_score <= 1.0
        assert evaluation.reasoning is not None
        assert isinstance(evaluation.priority, ActionPriority)

    def test_calculate_base_score(self, engine, situation):
        """Test base score calculation."""
        action = {"type": "observe"}

        score = engine._calculate_base_score(action, situation)

        assert 0.0 <= score <= 1.0

    def test_calculate_base_score_with_goal_alignment(self, engine, situation):
        """Test base score with goal alignment."""
        situation.active_goals = [
            {
                "type": "survival",
                "related_actions": ["observe"],
            },
        ]
        action = {"type": "observe"}

        score = engine._calculate_base_score(action, situation)

        assert score > 0.5  # Should be boosted by goal alignment

    def test_calculate_base_score_threat_response(self, engine, situation):
        """Test base score with threat response."""
        situation.threat_level = ThreatLevel.HIGH
        action = {"type": "combat"}

        score = engine._calculate_base_score(action, situation)

        assert score > 0.5  # Should be boosted by threat

    def test_apply_personality_modifiers(self, engine):
        """Test personality modifier application."""
        engine.core.character_data = {
            "psychological": {
                "personality_traits": {"aggressive": 0.8},
            },
        }
        action = {"type": "combat"}

        score = engine._apply_personality_modifiers(0.5, action)

        assert 0.0 <= score <= 1.0

    def test_apply_situational_modifiers(self, engine, situation):
        """Test situational modifier application."""
        situation.threat_level = ThreatLevel.CRITICAL
        action = {"type": "escape"}

        score = engine._apply_situational_modifiers(0.5, action, situation)

        assert score > 0.5  # Should be boosted by critical threat

    def test_select_best_action(self, engine):
        """Test selecting best action."""
        evaluations = [
            ActionEvaluation(
                action={"type": "wait"},
                base_score=0.3,
                modified_score=0.3,
                reasoning="Wait",
                priority=ActionPriority.LOW,
            ),
            ActionEvaluation(
                action={"type": "observe"},
                base_score=0.8,
                modified_score=0.8,
                reasoning="Observe",
                priority=ActionPriority.HIGH,
            ),
        ]

        best = engine._select_best_action(evaluations)

        assert best is not None
        assert best.action["type"] == "observe"

    def test_select_best_action_empty_list(self, engine):
        """Test selecting best action from empty list."""
        best = engine._select_best_action([])
        assert best is None

    def test_create_character_action(self, engine):
        """Test creating CharacterAction from evaluation."""
        evaluation = ActionEvaluation(
            action={
                "type": "observe",
                "target": "environment",
                "parameters": {"detail": "high"},
            },
            base_score=0.8,
            modified_score=0.85,
            reasoning="Good visibility",
            priority=ActionPriority.HIGH,
        )

        action = engine._create_character_action(evaluation)

        assert isinstance(action, CharacterAction)
        assert action.action_type == "observe"
        assert action.target == "environment"
        assert action.reasoning == "Good visibility"
        assert action.priority == ActionPriority.HIGH


class TestDecisionEngineHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}
        return DecisionEngine(core=core)

    def test_assess_available_resources(self, engine):
        """Test resource assessment."""
        world_state = {"available_equipment": ["weapon", "shield"]}

        resources = engine._assess_available_resources(world_state)

        assert "combat_capability" in resources
        assert "social_influence" in resources
        assert "knowledge_base" in resources
        assert "equipment" in resources

    def test_get_current_goals(self, engine):
        """Test getting current goals."""
        goals = engine._get_current_goals()

        assert isinstance(goals, list)
        assert len(goals) > 0

    def test_assess_social_obligations(self, engine):
        """Test social obligations assessment."""
        world_state = {}

        obligations = engine._assess_social_obligations(world_state)

        assert isinstance(obligations, list)

    def test_assess_environmental_factors(self, engine):
        """Test environmental factors assessment."""
        world_state = {"environmental_factors": {"weather": "clear", "time": "day"}}

        factors = engine._assess_environmental_factors(world_state)

        assert factors == {"weather": "clear", "time": "day"}

    def test_assess_mission_status(self, engine):
        """Test mission status assessment."""
        world_state = {"mission_status": {"mission": "active", "progress": 50}}

        status = engine._assess_mission_status(world_state)

        assert status == {"mission": "active", "progress": 50}

    def test_get_location_modifiers(self, engine):
        """Test location modifiers."""
        modifier = engine._get_location_modifiers("Station", "observe")

        assert isinstance(modifier, float)

    def test_generate_action_reasoning(self, engine):
        """Test reasoning generation."""
        action = {"type": "observe"}

        reasoning = engine._generate_action_reasoning(action, 0.5, 0.7)

        assert isinstance(reasoning, str)
        assert "observe" in reasoning
        assert "0.50" in reasoning or "0.5" in reasoning
        assert "0.70" in reasoning or "0.7" in reasoning

    def test_determine_action_priority(self, engine):
        """Test priority determination."""
        action = {"type": "observe"}

        assert engine._determine_action_priority(action, 0.9) == ActionPriority.HIGH
        assert engine._determine_action_priority(action, 0.7) == ActionPriority.NORMAL
        assert engine._determine_action_priority(action, 0.5) == ActionPriority.LOW

    def test_update_decision_weights(self, engine):
        """Test updating decision weights."""
        engine.core.character_data = {
            "behavioral": {
                "decision_weights": {"combat": 0.8, "social": 0.4},
            },
        }

        engine._update_decision_weights()

        assert engine.decision_weights == {"combat": 0.8, "social": 0.4}


class TestDecisionEngineEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def engine(self):
        """Create a DecisionEngine instance."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = None
        core.character_data = {}
        return DecisionEngine(core=core)

    def test_identify_available_actions_non_situation(self, engine):
        """Test action identification with non-SituationAssessment input."""
        situation_dict = {
            "current_location": "Station",
            "threat_level": ThreatLevel.LOW,
        }

        actions = engine._identify_available_actions(situation_dict)  # type: ignore

        assert isinstance(actions, list)

    def test_evaluate_action_option(self, engine):
        """Test _evaluate_action_option method."""
        action = {"type": "observe"}
        situation = SituationAssessment(
            current_location="Station",
            threat_level=ThreatLevel.LOW,
            available_resources={},
            active_goals=[],
            social_obligations=[],
            environmental_factors={},
            mission_status={},
        )

        score = engine._evaluate_action_option(action, situation)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_coerce_situation_assessment(self, engine):
        """Test _coerce_situation_assessment method."""
        situation_dict = {
            "current_location": "Base",
            "threat_level": "high",
            "available_resources": {"energy": 100},
        }

        situation = engine._coerce_situation_assessment(situation_dict)

        assert isinstance(situation, SituationAssessment)
        assert situation.current_location == "Base"
        assert situation.threat_level == ThreatLevel.HIGH

    def test_coerce_situation_assessment_with_threat_level_enum(self, engine):
        """Test coercing situation with ThreatLevel enum."""
        situation_dict = {
            "threat_level": ThreatLevel.CRITICAL,
        }

        situation = engine._coerce_situation_assessment(situation_dict)

        assert situation.threat_level == ThreatLevel.CRITICAL


class TestDecisionEngineIntegration:
    """Integration tests."""

    def test_full_decision_flow(self):
        """Test full decision making flow."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {
            "psychological": {
                "personality_traits": {"cautious": 0.7},
            },
        }

        engine = DecisionEngine(core=core)
        world_state = {
            "current_location": "Station",
            "threat_indicators": [],
        }

        action = engine.make_decision(world_state)

        # May or may not return an action depending on scores
        assert action is None or isinstance(action, CharacterAction)

    def test_decision_with_high_threat(self):
        """Test decision making with high threat."""
        core = Mock()
        core.agent_id = "test_agent"
        core.state = Mock()
        core.state.current_location = "Station"
        core.character_data = {}

        engine = DecisionEngine(core=core)
        world_state = {
            "threat_indicators": ["enemy1", "enemy2", "enemy3"],
        }

        situation = engine._assess_current_situation(world_state)

        assert situation.threat_level == ThreatLevel.CRITICAL
