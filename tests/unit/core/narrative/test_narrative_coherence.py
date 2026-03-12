#!/usr/bin/env python3
"""Unit tests for src/core/narrative/narrative_coherence.py module."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.core.narrative.causal_graph import CausalGraph
from src.core.narrative.narrative_coherence import NarrativeCoherenceEngine
from src.core.narrative.types import CausalEdge, CausalNode, CausalRelationType


class TestNarrativeCoherenceEngineInit:
    """Tests for NarrativeCoherenceEngine initialization."""

    @pytest.mark.unit
    def test_init_without_llm_service(self):
        """Test initialization without LLM service."""
        causal_graph = CausalGraph()

        with patch("src.core.narrative.narrative_coherence.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm
            engine = NarrativeCoherenceEngine(causal_graph)

        assert engine.causal_graph == causal_graph
        assert engine.llm_service is not None
        assert engine.story_timeline == []
        assert engine.character_arcs == {}
        assert engine.plot_threads == {}
        assert engine.consistency_rules == []

    @pytest.mark.unit
    def test_init_with_llm_service(self):
        """Test initialization with provided LLM service."""
        causal_graph = CausalGraph()
        mock_llm = MagicMock()

        engine = NarrativeCoherenceEngine(causal_graph, llm_service=mock_llm)

        assert engine.llm_service == mock_llm


class TestNarrativeCoherenceEngineRegisterConsistencyRule:
    """Tests for register_consistency_rule method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_register_single_rule(self, engine):
        """Test registering a single consistency rule."""
        @pytest.mark.unit
        def test_rule(data):
            return True

        engine.register_consistency_rule(test_rule)

        assert len(engine.consistency_rules) == 1
        assert engine.consistency_rules[0] == test_rule

    @pytest.mark.unit
    def test_register_multiple_rules(self, engine):
        """Test registering multiple consistency rules."""
        def rule1(data):
            return True

        def rule2(data):
            return False

        engine.register_consistency_rule(rule1)
        engine.register_consistency_rule(rule2)

        assert len(engine.consistency_rules) == 2


class TestNarrativeCoherenceEngineGetRelevantContextEvents:
    """Tests for _get_relevant_context_events method."""

    @pytest.fixture
    def engine_with_events(self):
        """Create an engine with sample events."""
        causal_graph = CausalGraph()
        engine = NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

        now = datetime.now()

        # Create events at different times
        events = [
            CausalNode(
                node_id="event_1",
                event_type="type_1",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(hours=1),
            ),
            CausalNode(
                node_id="event_2",
                event_type="type_2",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=30),
            ),
            CausalNode(
                node_id="event_3",
                event_type="type_3",
                agent_id="agent_2",
                action_data={},
                timestamp=now - timedelta(minutes=15),
            ),
        ]

        with patch("src.core.narrative.narrative_coherence.logger"):
            for event in events:
                causal_graph.add_event(event)

            # Add causal relation
            causal_graph.add_causal_relation(
                CausalEdge(
                    source_id="event_1",
                    target_id="event_3",
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
            )

        return engine, events

    @pytest.mark.unit
    def test_get_relevant_events_time_window(self, engine_with_events):
        """Test getting relevant events within time window."""
        engine, events = engine_with_events
        target_event = events[2]  # event_3

        relevant = engine._get_relevant_context_events(target_event, time_window=timedelta(hours=2))

        # Should include events within time window
        assert len(relevant) >= 1

    @pytest.mark.unit
    def test_get_relevant_events_excludes_self(self, engine_with_events):
        """Test that target event is excluded from results."""
        engine, events = engine_with_events
        target_event = events[2]

        relevant = engine._get_relevant_context_events(target_event)

        event_ids = [e.node_id for e in relevant]
        assert target_event.node_id not in event_ids

    @pytest.mark.unit
    def test_get_relevant_events_sorted_by_time(self, engine_with_events):
        """Test that relevant events are sorted by timestamp."""
        engine, events = engine_with_events
        target_event = events[2]

        relevant = engine._get_relevant_context_events(target_event, time_window=timedelta(hours=2))

        # Check sorting
        for i in range(len(relevant) - 1):
            assert relevant[i].timestamp <= relevant[i + 1].timestamp


class TestNarrativeCoherenceEngineCheckEventConsistency:
    """Tests for _check_event_consistency method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_consistency_with_no_issues(self, engine):
        """Test consistency check with no issues."""
        now = datetime.now()
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            metadata={},
        )

        context = [
            CausalNode(
                node_id="context_1",
                event_type="context",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=5),
                location="loc_1",
            )
        ]

        result = await engine._check_event_consistency(event, context)

        assert result["consistent"] is True
        assert result["issues"] == []
        assert result["confidence"] == 1.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_temporal_inconsistency(self, engine):
        """Test detection of temporal inconsistency."""
        now = datetime.now()
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=now - timedelta(minutes=10),
        )

        context = [
            CausalNode(
                node_id="context_1",
                event_type="context",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=5),  # After event
            )
        ]

        result = await engine._check_event_consistency(event, context)

        assert result["consistent"] is False
        assert any("Temporal inconsistency" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_location_inconsistency(self, engine):
        """Test detection of location inconsistency."""
        now = datetime.now()
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={"type": "action"},
            timestamp=now,
            location="loc_2",  # Different from last known
        )

        context = [
            CausalNode(
                node_id="context_1",
                event_type="context",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=5),
                location="loc_1",
            )
        ]

        result = await engine._check_event_consistency(event, context)

        assert result["consistent"] is False
        assert any("Location inconsistency" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_location_inconsistency_move_action(self, engine):
        """Test that move action doesn't trigger location inconsistency."""
        now = datetime.now()
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={"type": "move"},  # Move action
            timestamp=now,
            location="loc_2",
        )

        context = [
            CausalNode(
                node_id="context_1",
                event_type="context",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=5),
                location="loc_1",
            )
        ]

        result = await engine._check_event_consistency(event, context)

        # Should not have location inconsistency for move action
        assert not any("Location inconsistency" in issue for issue in result["issues"])

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_missing_precondition(self, engine):
        """Test detection of missing preconditions."""
        now = datetime.now()
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            metadata={"requires": ["prerequisite_event"]},
        )

        context = [
            CausalNode(
                node_id="context_1",
                event_type="other_event",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=5),
            )
        ]

        result = await engine._check_event_consistency(event, context)

        assert result["consistent"] is False
        assert any("Missing precondition" in issue for issue in result["issues"])


class TestNarrativeCoherenceEngineEventSatisfiesCondition:
    """Tests for _event_satisfies_condition method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_condition_in_event_type(self, engine):
        """Test condition matching event type."""
        event = CausalNode(
            node_id="event_1",
            event_type="combat_battle",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        result = engine._event_satisfies_condition(event, "combat")

        assert result is True

    @pytest.mark.unit
    def test_condition_in_action_data(self, engine):
        """Test condition matching action data."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={"weapon": "sword", "target": "enemy"},
            timestamp=datetime.now(),
        )

        result = engine._event_satisfies_condition(event, "sword")

        assert result is True

    @pytest.mark.unit
    def test_condition_in_metadata_provides(self, engine):
        """Test condition matching metadata provides."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
            metadata={"provides": ["item_key", "clue"]},
        )

        result = engine._event_satisfies_condition(event, "item_key")

        assert result is True

    @pytest.mark.unit
    def test_condition_not_satisfied(self, engine):
        """Test when condition is not satisfied."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={"action": "run"},
            timestamp=datetime.now(),
        )

        result = engine._event_satisfies_condition(event, "jump")

        assert result is False


class TestNarrativeCoherenceEngineUpdateCharacterArc:
    """Tests for _update_character_arc method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_create_new_arc(self, engine):
        """Test creating a new character arc."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        engine._update_character_arc("agent_1", event)

        assert "agent_1" in engine.character_arcs
        arc = engine.character_arcs["agent_1"]
        assert arc["events"] == [
            {
                "event_id": "event_1",
                "timestamp": event.timestamp,
                "event_type": "test",
                "significance": 1.0,
            }
        ]
        assert arc["development_stages"] == []
        assert arc["personality_changes"] == []
        assert arc["relationships"] == {}
        assert arc["goals_evolution"] == []

    @pytest.mark.unit
    def test_add_to_existing_arc(self, engine):
        """Test adding event to existing character arc."""
        # Create initial arc
        event1 = CausalNode(
            node_id="event_1",
            event_type="type_1",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )
        engine._update_character_arc("agent_1", event1)

        # Add another event
        event2 = CausalNode(
            node_id="event_2",
            event_type="type_2",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
            narrative_weight=0.8,
        )
        engine._update_character_arc("agent_1", event2)

        arc = engine.character_arcs["agent_1"]
        assert len(arc["events"]) == 2
        assert arc["events"][1]["event_type"] == "type_2"
        assert arc["events"][1]["significance"] == 0.8

    @pytest.mark.unit
    def test_development_stage_added_every_five_events(self, engine):
        """Test that development stage is added every 5 events."""
        for i in range(5):
            event = CausalNode(
                node_id=f"event_{i}",
                event_type="type",
                agent_id="agent_1",
                action_data={},
                timestamp=datetime.now() + timedelta(minutes=i),
            )
            engine._update_character_arc("agent_1", event)

        arc = engine.character_arcs["agent_1"]
        assert len(arc["development_stages"]) == 1


class TestNarrativeCoherenceEngineAnalyzeCharacterDevelopmentStage:
    """Tests for _analyze_character_development_stage method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_empty_events_returns_none(self, engine):
        """Test that empty events list returns None."""
        result = engine._analyze_character_development_stage("agent_1", [])

        assert result is None

    @pytest.mark.unit
    def test_conflict_stage_detection(self, engine):
        """Test detection of conflict development stage."""
        now = datetime.now()
        events = [
            {"event_id": "e1", "timestamp": now, "event_type": "combat_attack"},
            {"event_id": "e2", "timestamp": now + timedelta(minutes=1), "event_type": "defend"},
        ]

        result = engine._analyze_character_development_stage("agent_1", events)

        assert result is not None
        assert result["stage_type"] == "conflict"

    @pytest.mark.unit
    def test_social_development_stage_detection(self, engine):
        """Test detection of social development stage."""
        now = datetime.now()
        events = [
            {"event_id": "e1", "timestamp": now, "event_type": "social_greeting"},
            {"event_id": "e2", "timestamp": now + timedelta(minutes=1), "event_type": "negotiate_deal"},
        ]

        result = engine._analyze_character_development_stage("agent_1", events)

        assert result is not None
        assert result["stage_type"] == "social_development"

    @pytest.mark.unit
    def test_learning_stage_detection(self, engine):
        """Test detection of learning development stage."""
        now = datetime.now()
        events = [
            {"event_id": "e1", "timestamp": now, "event_type": "discover_secret"},
            {"event_id": "e2", "timestamp": now + timedelta(minutes=1), "event_type": "learn_skill"},
        ]

        result = engine._analyze_character_development_stage("agent_1", events)

        assert result is not None
        assert result["stage_type"] == "learning"

    @pytest.mark.unit
    def test_exploration_stage_default(self, engine):
        """Test default exploration stage."""
        now = datetime.now()
        events = [
            {"event_id": "e1", "timestamp": now, "event_type": "walk"},
            {"event_id": "e2", "timestamp": now + timedelta(minutes=1), "event_type": "look_around"},
        ]

        result = engine._analyze_character_development_stage("agent_1", events)

        assert result is not None
        assert result["stage_type"] == "exploration"


class TestNarrativeCoherenceEngineIdentifyPlotThread:
    """Tests for _identify_plot_thread method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_identify_existing_thread_by_location(self, engine):
        """Test identifying existing thread by location."""
        now = datetime.now()

        # Create existing thread
        engine.plot_threads["thread_1"] = {
            "thread_id": "thread_1",
            "primary_location": "castle",
            "involved_agents": ["agent_1"],
            "related_event_types": ["combat"],
        }

        event = CausalNode(
            node_id="event_1",
            event_type="exploration",
            agent_id="agent_2",
            action_data={},
            timestamp=now,
            location="castle",
        )

        result = engine._identify_plot_thread(event, [])

        assert result == "thread_1"

    @pytest.mark.unit
    def test_identify_existing_thread_by_agent(self, engine):
        """Test identifying existing thread by agent."""
        now = datetime.now()

        engine.plot_threads["thread_1"] = {
            "thread_id": "thread_1",
            "primary_location": "village",
            "involved_agents": ["agent_1"],
            "related_event_types": ["combat"],
        }

        event = CausalNode(
            node_id="event_1",
            event_type="exploration",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="forest",
        )

        result = engine._identify_plot_thread(event, [])

        assert result == "thread_1"

    @pytest.mark.unit
    def test_create_new_thread_for_significant_event(self, engine):
        """Test creating new thread for significant event."""
        now = datetime.now()

        event = CausalNode(
            node_id="event_1",
            event_type="major_event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            location="castle",
            narrative_weight=0.8,  # Above threshold
        )

        result = engine._identify_plot_thread(event, [])

        assert result is not None
        assert result.startswith("thread_")
        assert result in engine.plot_threads

    @pytest.mark.unit
    def test_no_thread_for_minor_event(self, engine):
        """Test that minor events don't create new threads."""
        now = datetime.now()

        event = CausalNode(
            node_id="event_1",
            event_type="minor_event",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            narrative_weight=0.3,  # Below threshold
        )

        result = engine._identify_plot_thread(event, [])

        assert result is None


class TestNarrativeCoherenceEngineUpdatePlotThread:
    """Tests for _update_plot_thread method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine with a plot thread."""
        causal_graph = CausalGraph()
        engine = NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

        engine.plot_threads["thread_1"] = {
            "thread_id": "thread_1",
            "primary_location": "castle",
            "involved_agents": ["agent_1"],
            "related_event_types": ["combat"],
            "events": ["event_1"],
        }

        return engine

    @pytest.mark.unit
    def test_update_existing_thread(self, engine):
        """Test updating an existing plot thread."""
        event = CausalNode(
            node_id="event_2",
            event_type="exploration",
            agent_id="agent_2",
            action_data={},
            timestamp=datetime.now(),
        )

        engine._update_plot_thread("thread_1", event)

        thread = engine.plot_threads["thread_1"]
        assert "event_2" in thread["events"]
        assert "agent_2" in thread["involved_agents"]
        assert "exploration" in thread["related_event_types"]
        assert "last_update" in thread

    @pytest.mark.unit
    def test_update_nonexistent_thread(self, engine):
        """Test updating a non-existent thread does nothing."""
        event = CausalNode(
            node_id="event_2",
            event_type="exploration",
            agent_id="agent_2",
            action_data={},
            timestamp=datetime.now(),
        )

        # Should not raise exception
        engine._update_plot_thread("nonexistent", event)


class TestNarrativeCoherenceEngineCreateContextSummary:
    """Tests for _create_context_summary method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_empty_context(self, engine):
        """Test summary with empty context."""
        result = engine._create_context_summary([])

        assert result == "故事刚刚开始。"

    @pytest.mark.unit
    def test_context_summary(self, engine):
        """Test context summary generation."""
        now = datetime.now()
        events = [
            CausalNode(
                node_id="e1",
                event_type="arrive",
                agent_id="hero",
                action_data={},
                timestamp=now,
                location="village",
            ),
            CausalNode(
                node_id="e2",
                event_type="talk",
                agent_id="villager",
                action_data={},
                timestamp=now + timedelta(minutes=5),
                location="village",
            ),
        ]

        result = engine._create_context_summary(events)

        assert "hero" in result
        assert "villager" in result
        assert "village" in result


class TestNarrativeCoherenceEngineGenerateBasicNarrative:
    """Tests for _generate_basic_narrative method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_basic_narrative_generation(self, engine):
        """Test basic narrative generation."""
        event = CausalNode(
            node_id="event_1",
            event_type="combat",
            agent_id="hero",
            action_data={},
            timestamp=datetime.now(),
            location="battlefield",
        )

        result = engine._generate_basic_narrative(event)

        assert "hero" in result or "某个神秘人物" in result
        assert "combat" in result or "战斗" in result

    @pytest.mark.unit
    def test_narrative_consistency(self, engine):
        """Test that same event generates consistent narrative."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        result1 = engine._generate_basic_narrative(event)
        result2 = engine._generate_basic_narrative(event)

        assert result1 == result2


class TestNarrativeCoherenceEngineExtractCharacterDevelopment:
    """Tests for _extract_character_development method."""

    @pytest.fixture
    def engine(self):
        """Create a NarrativeCoherenceEngine instance."""
        causal_graph = CausalGraph()
        return NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

    @pytest.mark.unit
    def test_no_agent_returns_empty(self, engine):
        """Test that event without agent returns empty dict."""
        event = CausalNode(
            node_id="event_1",
            event_type="test",
            agent_id=None,
            action_data={},
            timestamp=datetime.now(),
        )

        result = engine._extract_character_development(event)

        assert result == {}

    @pytest.mark.unit
    def test_social_skills_development(self, engine):
        """Test detection of social skills development."""
        event = CausalNode(
            node_id="event_1",
            event_type="social_interaction",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        result = engine._extract_character_development(event)

        assert "social_skills" in result["growth_indicators"]

    @pytest.mark.unit
    def test_combat_experience_development(self, engine):
        """Test detection of combat experience development."""
        event = CausalNode(
            node_id="event_1",
            event_type="attack",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        result = engine._extract_character_development(event)

        assert "combat_experience" in result["growth_indicators"]

    @pytest.mark.unit
    def test_relationship_changes_with_participants(self, engine):
        """Test relationship change extraction with participants."""
        event = CausalNode(
            node_id="event_1",
            event_type="help",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
            location="village",
            participants=["agent_1", "agent_2", "agent_3"],
        )

        result = engine._extract_character_development(event)

        assert len(result["relationship_changes"]) == 2  # agent_2 and agent_3
        change = result["relationship_changes"][0]
        assert change["other_agent"] in ["agent_2", "agent_3"]


class TestNarrativeCoherenceEngineGetNarrativeTimeline:
    """Tests for get_narrative_timeline method."""

    @pytest.fixture
    def engine_with_timeline(self):
        """Create an engine with timeline entries."""
        causal_graph = CausalGraph()
        engine = NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

        now = datetime.now()

        # Add timeline entries
        engine.story_timeline = [
            {
                "event_id": "e1",
                "timestamp": now - timedelta(hours=2),
                "agent_id": "agent_1",
                "narrative_text": "First event",
            },
            {
                "event_id": "e2",
                "timestamp": now - timedelta(hours=1),
                "agent_id": "agent_2",
                "narrative_text": "Second event",
            },
            {
                "event_id": "e3",
                "timestamp": now,
                "agent_id": "agent_1",
                "narrative_text": "Third event",
            },
        ]

        return engine

    @pytest.mark.unit
    def test_get_full_timeline(self, engine_with_timeline):
        """Test getting full timeline."""
        result = engine_with_timeline.get_narrative_timeline()

        assert len(result) == 3

    @pytest.mark.unit
    def test_filter_by_start_time(self, engine_with_timeline):
        """Test filtering timeline by start time."""
        now = datetime.now()

        result = engine_with_timeline.get_narrative_timeline(start_time=now - timedelta(minutes=30))

        assert len(result) == 1
        assert result[0]["event_id"] == "e3"

    @pytest.mark.unit
    def test_filter_by_end_time(self, engine_with_timeline):
        """Test filtering timeline by end time."""
        now = datetime.now()

        result = engine_with_timeline.get_narrative_timeline(end_time=now - timedelta(minutes=30))

        assert len(result) == 2

    @pytest.mark.unit
    def test_filter_by_agent(self, engine_with_timeline):
        """Test filtering timeline by agent."""
        result = engine_with_timeline.get_narrative_timeline(agent_filter=["agent_1"])

        assert len(result) == 2
        assert all(entry["agent_id"] == "agent_1" for entry in result)

    @pytest.mark.unit
    def test_filter_by_multiple_agents(self, engine_with_timeline):
        """Test filtering timeline by multiple agents."""
        result = engine_with_timeline.get_narrative_timeline(agent_filter=["agent_1", "agent_2"])

        assert len(result) == 3


class TestNarrativeCoherenceEngineGetCoherenceReport:
    """Tests for get_coherence_report method."""

    @pytest.fixture
    def engine_with_data(self):
        """Create an engine with various data."""
        causal_graph = CausalGraph()
        engine = NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

        now = datetime.now()

        # Add timeline
        engine.story_timeline = [
            {"event_id": "e1", "timestamp": now - timedelta(hours=1)},
            {"event_id": "e2", "timestamp": now},
        ]

        # Add character arcs
        engine.character_arcs["agent_1"] = {"events": [{}, {}, {}]}
        engine.character_arcs["agent_2"] = {"events": [{}, {}]}

        # Add plot threads
        engine.plot_threads["thread_1"] = {"status": "active", "events": [{}, {}]}
        engine.plot_threads["thread_2"] = {"status": "resolved", "events": [{}]}

        # Add consistency rules
        def rule1(data):
            return True

        engine.consistency_rules.append(rule1)

        return engine

    @pytest.mark.unit
    def test_coherence_report_structure(self, engine_with_data):
        """Test coherence report structure."""
        report = engine_with_data.get_coherence_report()

        assert "total_events" in report
        assert "character_arcs" in report
        assert "plot_threads" in report
        assert "active_plot_threads" in report
        assert "consistency_rule_count" in report
        assert "timeline_span" in report
        assert "character_summary" in report
        assert "plot_thread_summary" in report

    @pytest.mark.unit
    def test_coherence_report_values(self, engine_with_data):
        """Test coherence report values."""
        report = engine_with_data.get_coherence_report()

        assert report["total_events"] == 2
        assert report["character_arcs"] == 2
        assert report["plot_threads"] == 2
        assert report["active_plot_threads"] == 1
        assert report["consistency_rule_count"] == 1
        assert report["character_summary"]["agent_1"] == 3
        assert report["character_summary"]["agent_2"] == 2
        assert report["plot_thread_summary"]["thread_1"] == 2
        assert report["plot_thread_summary"]["thread_2"] == 1

    @pytest.mark.unit
    def test_coherence_report_timeline_span(self, engine_with_data):
        """Test timeline span in coherence report."""
        report = engine_with_data.get_coherence_report()

        assert report["timeline_span"]["start"] is not None
        assert report["timeline_span"]["end"] is not None

    @pytest.mark.unit
    def test_coherence_report_empty_timeline(self):
        """Test coherence report with empty timeline."""
        causal_graph = CausalGraph()
        engine = NarrativeCoherenceEngine(causal_graph, llm_service=MagicMock())

        report = engine.get_coherence_report()

        assert report["total_events"] == 0
        assert report["timeline_span"]["start"] is None
        assert report["timeline_span"]["end"] is None
