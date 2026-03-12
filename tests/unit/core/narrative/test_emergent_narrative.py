#!/usr/bin/env python3
"""Unit tests for src/core/narrative/emergent_narrative.py module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.core.narrative.emergent_narrative import (
    EmergentNarrativeEngine,
    create_emergent_narrative_engine,
)
from src.core.narrative.types import CausalNode


class TestCreateEmergentNarrativeEngine:
    """Tests for create_emergent_narrative_engine factory function."""

    @pytest.mark.unit
    def test_factory_without_llm_service(self):
        """Test factory function without LLM service."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            engine = create_emergent_narrative_engine()

        assert isinstance(engine, EmergentNarrativeEngine)

    @pytest.mark.unit
    def test_factory_with_llm_service(self):
        """Test factory function with provided LLM service."""
        mock_llm = MagicMock()
        engine = create_emergent_narrative_engine(llm_service=mock_llm)

        assert isinstance(engine, EmergentNarrativeEngine)
        assert engine.llm_service == mock_llm


class TestEmergentNarrativeEngineInit:
    """Tests for EmergentNarrativeEngine initialization."""

    @pytest.mark.unit
    def test_init_creates_sub_engines(self):
        """Test that initialization creates sub-engines."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            engine = EmergentNarrativeEngine()

        assert engine.causal_graph is not None
        assert engine.negotiation_engine is not None
        assert engine.coherence_engine is not None
        assert engine.active_agents == set()
        assert engine.global_narrative_state == {}

    @pytest.mark.unit
    def test_init_registers_default_consistency_rules(self):
        """Test that default consistency rules are registered."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service") as mock_get_llm:
            mock_get_llm.return_value = MagicMock()
            engine = EmergentNarrativeEngine()

        assert len(engine.coherence_engine.consistency_rules) >= 2


class TestEmergentNarrativeEngineInitialize:
    """Tests for initialize method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialize_logs_info(self, engine):
        """Test that initialize logs info message."""
        with patch("src.core.narrative.emergent_narrative.logger") as mock_logger:
            await engine.initialize()

        mock_logger.info.assert_called()


class TestEmergentNarrativeEngineInitializeAgent:
    """Tests for initialize_agent method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialize_agent_success(self, engine):
        """Test successful agent initialization."""
        result = await engine.initialize_agent(
            agent_id="agent_1",
            negotiation_style={"cooperativeness": 0.8},
            priorities=["exploration"],
        )

        assert result is True
        assert "agent_1" in engine.active_agents
        assert "agent_1" in engine.negotiation_engine.agent_negotiation_profiles

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialize_agent_default_values(self, engine):
        """Test agent initialization with default values."""
        await engine.initialize_agent("agent_1")

        profile = engine.negotiation_engine.agent_negotiation_profiles["agent_1"]
        assert profile["style"]["cooperativeness"] == 0.5
        assert profile["priorities"] == ["survival", "mission_success"]


class TestEmergentNarrativeEngineCalculateCausalStrength:
    """Tests for _calculate_causal_strength method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_same_agent_increases_strength(self, engine):
        """Test that same agent increases causal strength."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        effect = CausalNode(
            node_id="effect",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now + timedelta(minutes=5),
        )

        strength = engine._calculate_causal_strength(cause, effect)

        assert strength >= 0.4  # Base for same agent

    @pytest.mark.unit
    def test_same_location_increases_strength(self, engine):
        """Test that same location increases causal strength."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="loc_1",
        )
        effect = CausalNode(
            node_id="effect",
            event_type="event",
            agent_id="agent_2",
            action_data={},
            timestamp=now + timedelta(minutes=5),
            location="loc_1",
        )

        strength = engine._calculate_causal_strength(cause, effect)

        assert strength >= 0.3  # Base for same location

    @pytest.mark.unit
    def test_participant_overlap_increases_strength(self, engine):
        """Test that participant overlap increases causal strength."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            participants=["agent_2", "agent_3"],
        )
        effect = CausalNode(
            node_id="effect",
            event_type="event",
            agent_id="agent_2",
            action_data={},
            timestamp=now + timedelta(minutes=5),
            participants=["agent_1", "agent_4"],
        )

        strength = engine._calculate_causal_strength(cause, effect)

        assert strength >= 0.2  # For 2 overlapping participants

    @pytest.mark.unit
    def test_temporal_proximity_increases_strength(self, engine):
        """Test that temporal proximity increases causal strength."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        effect = CausalNode(
            node_id="effect",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now + timedelta(minutes=10),  # Within 1 hour
        )

        strength = engine._calculate_causal_strength(cause, effect)

        # Should have time factor bonus
        assert strength > 0.4  # Base 0.4 for same agent plus time bonus

    @pytest.mark.unit
    def test_strength_capped_at_one(self, engine):
        """Test that strength is capped at 1.0."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="loc_1",
            participants=["agent_2", "agent_3", "agent_4", "agent_5"],
        )
        effect = CausalNode(
            node_id="effect",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now + timedelta(minutes=5),
            location="loc_1",
            participants=["agent_2", "agent_3", "agent_4", "agent_5"],
        )

        strength = engine._calculate_causal_strength(cause, effect)

        assert strength <= 1.0


class TestEmergentNarrativeEngineAreLogicallyRelated:
    """Tests for _are_logically_related method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.parametrize(
        "cause_type,effect_type,expected",
        [
            ("attack", "defend", True),
            ("question", "answer", True),
            ("offer", "accept", True),
            ("offer", "reject", True),
            ("move", "arrive", True),
            ("search", "discover", True),
            ("negotiate", "agree", True),
            ("negotiate", "disagree", True),
            ("random", "unrelated", False),
            ("walk", "fly", False),
        ],
    )
    @pytest.mark.unit
    def test_logical_pairs(self, engine, cause_type, effect_type, expected):
        """Test various logical pairs."""
        result = engine._are_logically_related(cause_type, effect_type)
        assert result == expected


class TestEmergentNarrativeEngineAreContradictoryEvents:
    """Tests for _are_contradictory_events method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.parametrize(
        "type1,type2,expected",
        [
            ("attack", "help", True),
            ("help", "attack", True),  # Order shouldn't matter
            ("accept", "reject", True),
            ("agree", "disagree", True),
            ("approach", "retreat", True),
            ("create", "destroy", True),
            ("walk", "run", False),
            ("eat", "sleep", False),
        ],
    )
    @pytest.mark.unit
    def test_contradictory_pairs(self, engine, type1, type2, expected):
        """Test various contradictory pairs."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type=type1,
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type=type2,
            agent_id="agent_2",
            action_data={},
            timestamp=now,
        )

        result = engine._are_contradictory_events(event1, event2)
        assert result == expected


class TestEmergentNarrativeEngineIsEnablingEvent:
    """Tests for _is_enabling_event method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.parametrize(
        "cause_type,effect_type,expected",
        [
            ("discover", "use", True),
            ("unlock", "enter", True),
            ("learn", "apply", True),
            ("prepare", "execute", True),
            ("plan", "implement", True),
            ("attack", "defend", False),
            ("walk", "talk", False),
        ],
    )
    @pytest.mark.unit
    def test_enabling_pairs(self, engine, cause_type, effect_type, expected):
        """Test various enabling pairs."""
        now = datetime.now()
        cause = CausalNode(
            node_id="cause",
            event_type=cause_type,
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        effect = CausalNode(
            node_id="effect",
            event_type=effect_type,
            agent_id="agent_1",
            action_data={},
            timestamp=now + timedelta(minutes=5),
        )

        result = engine._is_enabling_event(cause, effect)
        assert result == expected


class TestEmergentNarrativeEngineCalculateConflictScore:
    """Tests for _calculate_conflict_score method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_location_conflict(self, engine):
        """Test location conflict detection."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="loc_1",
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={},
            timestamp=now,
            location="loc_1",
        )

        score = engine._calculate_conflict_score(event1, event2)

        assert score >= 0.3  # Location conflict base

    @pytest.mark.unit
    def test_resource_conflict(self, engine):
        """Test resource conflict detection."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"resources": ["gold", "wood"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"resources": ["gold", "stone"]},
            timestamp=now,
        )

        score = engine._calculate_conflict_score(event1, event2)

        assert score >= 0.4  # Resource conflict base

    @pytest.mark.unit
    def test_goal_conflict(self, engine):
        """Test goal conflict detection."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )

        score = engine._calculate_conflict_score(event1, event2)

        assert score >= 0.5  # Goal conflict base

    @pytest.mark.unit
    def test_contradictory_events_conflict(self, engine):
        """Test contradictory events conflict detection."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="attack",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="help",
            agent_id="agent_2",
            action_data={},
            timestamp=now,
        )

        score = engine._calculate_conflict_score(event1, event2)

        assert score >= 0.6  # Contradictory base

    @pytest.mark.unit
    def test_conflict_score_capped(self, engine):
        """Test that conflict score is capped at 1.0."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="attack",
            agent_id="agent_1",
            action_data={"resources": ["gold"], "goals": ["win"]},
            timestamp=now,
            location="loc_1",
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="help",
            agent_id="agent_2",
            action_data={"resources": ["gold"], "goals": ["win"]},
            timestamp=now,
            location="loc_1",
        )

        score = engine._calculate_conflict_score(event1, event2)

        assert score <= 1.0


class TestEmergentNarrativeEngineCheckResourceConflict:
    """Tests for _check_resource_conflict method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_overlapping_resources(self, engine):
        """Test detection of overlapping resources."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"resources": ["gold", "wood"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"resources": ["gold", "stone"]},
            timestamp=now,
        )

        result = engine._check_resource_conflict(event1, event2)

        assert result is True

    @pytest.mark.unit
    def test_no_overlapping_resources(self, engine):
        """Test when resources don't overlap."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"resources": ["wood"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"resources": ["gold"]},
            timestamp=now,
        )

        result = engine._check_resource_conflict(event1, event2)

        assert result is False

    @pytest.mark.unit
    def test_empty_resources(self, engine):
        """Test with empty resources."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"resources": ["gold"]},
            timestamp=now,
        )

        result = engine._check_resource_conflict(event1, event2)

        assert result is False


class TestEmergentNarrativeEngineCheckGoalConflict:
    """Tests for _check_goal_conflict method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_same_goal_different_agents(self, engine):
        """Test goal conflict with same goal but different agents."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )

        result = engine._check_goal_conflict(event1, event2)

        assert result is True

    @pytest.mark.unit
    def test_same_goal_same_agent(self, engine):
        """Test no goal conflict with same agent."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )

        result = engine._check_goal_conflict(event1, event2)

        assert result is False

    @pytest.mark.unit
    def test_different_goals(self, engine):
        """Test no conflict with different goals."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["conquer_castle"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"goals": ["defend_village"]},
            timestamp=now,
        )

        result = engine._check_goal_conflict(event1, event2)

        assert result is False


class TestEmergentNarrativeEngineClassifyConflictType:
    """Tests for _classify_conflict_type method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_resource_competition(self, engine):
        """Test resource competition classification."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"resources": ["gold"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"resources": ["gold"]},
            timestamp=now,
        )

        result = engine._classify_conflict_type(event1, event2)

        assert result == "resource_competition"

    @pytest.mark.unit
    def test_goal_competition(self, engine):
        """Test goal competition classification."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={"goals": ["win"]},
            timestamp=now,
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={"goals": ["win"]},
            timestamp=now,
        )

        result = engine._classify_conflict_type(event1, event2)

        assert result == "goal_competition"

    @pytest.mark.unit
    def test_territorial_dispute(self, engine):
        """Test territorial dispute classification."""
        now = datetime.now()
        event1 = CausalNode(
            node_id="e1",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="loc_1",
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="event",
            agent_id="agent_2",
            action_data={},
            timestamp=now,
            location="loc_1",
        )

        result = engine._classify_conflict_type(event1, event2)

        assert result == "territorial_dispute"

    @pytest.mark.unit
    def test_direct_opposition(self, engine):
        """Test direct opposition classification."""
        now = datetime.now()
        # Direct opposition requires contradictory events, and resource/goal conflicts checked first
        # We need events that don't trigger those other checks
        event1 = CausalNode(
            node_id="e1",
            event_type="attack",
            agent_id="agent_1",
            action_data={},  # No resources or goals
            timestamp=now,
            location="loc_1",
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="help",
            agent_id="agent_2",
            action_data={},  # No resources or goals
            timestamp=now,
            location="loc_2",  # Different location to avoid territorial check
        )

        result = engine._classify_conflict_type(event1, event2)

        assert result == "direct_opposition"

    @pytest.mark.unit
    def test_general_conflict(self, engine):
        """Test general conflict classification."""
        now = datetime.now()
        # General conflict requires no other conflict types to be detected
        event1 = CausalNode(
            node_id="e1",
            event_type="walk",
            agent_id="agent_1",
            action_data={},  # No resources or goals
            timestamp=now,
            location="loc_1",
        )
        event2 = CausalNode(
            node_id="e2",
            event_type="run",
            agent_id="agent_2",
            action_data={},  # No resources or goals
            timestamp=now,
            location="loc_2",  # Different location
        )

        result = engine._classify_conflict_type(event1, event2)

        assert result == "general_conflict"


class TestEmergentNarrativeEngineSuggestConflictResolution:
    """Tests for _suggest_conflict_resolution method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine instance."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            return EmergentNarrativeEngine()

    @pytest.mark.unit
    def test_resource_sharing_strategy(self, engine):
        """Test resource sharing resolution strategy."""
        conflict = {"conflict_type": "resource_competition"}

        result = engine._suggest_conflict_resolution(conflict)

        assert result["type"] == "resource_sharing"
        assert "description" in result
        assert "benefits" in result

    @pytest.mark.unit
    def test_goal_differentiation_strategy(self, engine):
        """Test goal differentiation resolution strategy."""
        conflict = {"conflict_type": "goal_competition"}

        result = engine._suggest_conflict_resolution(conflict)

        assert result["type"] == "goal_differentiation"

    @pytest.mark.unit
    def test_space_coordination_strategy(self, engine):
        """Test space coordination resolution strategy."""
        conflict = {"conflict_type": "territorial_dispute"}

        result = engine._suggest_conflict_resolution(conflict)

        assert result["type"] == "space_coordination"

    @pytest.mark.unit
    def test_compromise_negotiation_strategy(self, engine):
        """Test compromise negotiation resolution strategy."""
        conflict = {"conflict_type": "direct_opposition"}

        result = engine._suggest_conflict_resolution(conflict)

        assert result["type"] == "compromise_negotiation"

    @pytest.mark.unit
    def test_mediated_discussion_strategy(self, engine):
        """Test mediated discussion resolution strategy (default)."""
        conflict = {"conflict_type": "unknown_type"}

        result = engine._suggest_conflict_resolution(conflict)

        assert result["type"] == "mediated_discussion"


class TestEmergentNarrativeEngineGetEngineStatus:
    """Tests for get_engine_status method."""

    @pytest.fixture
    def engine(self):
        """Create an EmergentNarrativeEngine with data."""
        with patch("src.core.narrative.emergent_narrative.get_llm_service"):
            engine = EmergentNarrativeEngine()

        # Add some data
        engine.active_agents = {"agent_1", "agent_2"}

        with patch("src.core.narrative.emergent_narrative.logger"):
            now = datetime.now()
            for i in range(3):
                node = CausalNode(
                    node_id=f"node_{i}",
                    event_type=f"event_{i}",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now + timedelta(minutes=i),
                )
                engine.causal_graph.add_event(node)

        return engine

    @pytest.mark.unit
    def test_status_structure(self, engine):
        """Test status report structure."""
        status = engine.get_engine_status()

        assert "active_agents" in status
        assert "total_events" in status
        assert "causal_relations" in status
        assert "active_negotiations" in status
        assert "plot_threads" in status
        assert "character_arcs" in status
        assert "story_timeline_length" in status
        assert "narrative_patterns" in status

    @pytest.mark.unit
    def test_status_values(self, engine):
        """Test status report values."""
        status = engine.get_engine_status()

        assert status["active_agents"] == 2
        assert status["total_events"] == 3
