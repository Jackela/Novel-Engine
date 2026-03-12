#!/usr/bin/env python3
"""Unit tests for src/core/narrative/causal_graph.py module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.core.narrative.causal_graph import CausalGraph
from src.core.narrative.types import CausalEdge, CausalNode, CausalRelationType


class TestCausalGraphInit:
    """Tests for CausalGraph initialization."""

    @pytest.mark.unit
    def test_init_creates_empty_graph(self):
        """Test that initialization creates an empty graph structure."""
        graph = CausalGraph()

        assert graph.graph is not None
        assert graph.nodes == {}
        assert graph.edges == {}
        assert graph.temporal_index == {}
        assert graph.agent_index == {}
        assert graph.location_index == {}


class TestCausalGraphAddEvent:
    """Tests for CausalGraph.add_event method."""

    @pytest.fixture
    def causal_graph(self):
        """Create a fresh CausalGraph instance."""
        return CausalGraph()

    @pytest.mark.unit
    def test_add_event_basic(self, causal_graph):
        """Test adding a basic event."""
        timestamp = datetime.now()
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={"action": "test"},
            timestamp=timestamp,
        )

        with patch("src.core.narrative.causal_graph.logger") as mock_logger:
            result = causal_graph.add_event(node)

        assert result == "node_1"
        assert "node_1" in causal_graph.nodes
        assert causal_graph.nodes["node_1"] == node
        assert causal_graph.graph.has_node("node_1")
        mock_logger.debug.assert_called_once()

    @pytest.mark.unit
    def test_add_event_updates_temporal_index(self, causal_graph):
        """Test that add_event updates temporal index."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )

        with patch("src.core.narrative.causal_graph.logger"):
            causal_graph.add_event(node)

        assert timestamp in causal_graph.temporal_index
        assert causal_graph.temporal_index[timestamp] == ["node_1"]

    @pytest.mark.unit
    def test_add_event_updates_agent_index(self, causal_graph):
        """Test that add_event updates agent index."""
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
        )

        with patch("src.core.narrative.causal_graph.logger"):
            causal_graph.add_event(node)

        assert "agent_1" in causal_graph.agent_index
        assert "node_1" in causal_graph.agent_index["agent_1"]

    @pytest.mark.unit
    def test_add_event_updates_location_index(self, causal_graph):
        """Test that add_event updates location index."""
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
            location="test_location",
        )

        with patch("src.core.narrative.causal_graph.logger"):
            causal_graph.add_event(node)

        assert "test_location" in causal_graph.location_index
        assert "node_1" in causal_graph.location_index["test_location"]

    @pytest.mark.unit
    def test_add_event_without_agent(self, causal_graph):
        """Test adding an event without an agent_id."""
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id=None,
            action_data={},
            timestamp=datetime.now(),
        )

        with patch("src.core.narrative.causal_graph.logger"):
            result = causal_graph.add_event(node)

        assert result == "node_1"
        # Agent index should not be updated
        assert causal_graph.agent_index == {}

    @pytest.mark.unit
    def test_add_event_without_location(self, causal_graph):
        """Test adding an event without a location."""
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={},
            timestamp=datetime.now(),
            location=None,
        )

        with patch("src.core.narrative.causal_graph.logger"):
            result = causal_graph.add_event(node)

        assert result == "node_1"
        # Location index should not be updated
        assert causal_graph.location_index == {}

    @pytest.mark.unit
    def test_add_multiple_events_same_timestamp(self, causal_graph):
        """Test adding multiple events with the same timestamp."""
        timestamp = datetime.now()

        nodes = [
            CausalNode(
                node_id=f"node_{i}",
                event_type=f"event_{i}",
                agent_id=f"agent_{i}",
                action_data={},
                timestamp=timestamp,
            )
            for i in range(3)
        ]

        with patch("src.core.narrative.causal_graph.logger"):
            for node in nodes:
                causal_graph.add_event(node)

        assert len(causal_graph.temporal_index[timestamp]) == 3
        assert set(causal_graph.temporal_index[timestamp]) == {"node_0", "node_1", "node_2"}


class TestCausalGraphAddCausalRelation:
    """Tests for CausalGraph.add_causal_relation method."""

    @pytest.fixture
    def causal_graph(self):
        """Create a fresh CausalGraph instance with nodes."""
        graph = CausalGraph()
        timestamp = datetime.now()

        node1 = CausalNode(
            node_id="node_1",
            event_type="event_1",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )
        node2 = CausalNode(
            node_id="node_2",
            event_type="event_2",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp + timedelta(minutes=5),
        )

        with patch("src.core.narrative.causal_graph.logger"):
            graph.add_event(node1)
            graph.add_event(node2)

        return graph

    @pytest.mark.unit
    def test_add_causal_relation_success(self, causal_graph):
        """Test successfully adding a causal relation."""
        edge = CausalEdge(
            source_id="node_1",
            target_id="node_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.causal_graph.logger") as mock_logger:
            result = causal_graph.add_causal_relation(edge)

        assert result is True
        assert ("node_1", "node_2") in causal_graph.edges
        assert causal_graph.edges[("node_1", "node_2")] == edge
        assert causal_graph.graph.has_edge("node_1", "node_2")
        mock_logger.debug.assert_called_once()

    @pytest.mark.unit
    def test_add_causal_relation_source_not_found(self, causal_graph):
        """Test adding relation with missing source node."""
        edge = CausalEdge(
            source_id="nonexistent",
            target_id="node_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.causal_graph.logger") as mock_logger:
            result = causal_graph.add_causal_relation(edge)
            mock_logger.warning.assert_called_once()

        assert result is False

    @pytest.mark.unit
    def test_add_causal_relation_target_not_found(self, causal_graph):
        """Test adding relation with missing target node."""
        edge = CausalEdge(
            source_id="node_1",
            target_id="nonexistent",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.causal_graph.logger") as mock_logger:
            result = causal_graph.add_causal_relation(edge)
            mock_logger.warning.assert_called_once()

        assert result is False

    @pytest.mark.unit
    def test_add_causal_relation_both_missing(self, causal_graph):
        """Test adding relation with both nodes missing."""
        edge = CausalEdge(
            source_id="missing_1",
            target_id="missing_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.causal_graph.logger"):
            result = causal_graph.add_causal_relation(edge)

        assert result is False


class TestCausalGraphFindCausalChain:
    """Tests for CausalGraph.find_causal_chain method."""

    @pytest.fixture
    def chain_graph(self):
        """Create a CausalGraph with a causal chain."""
        graph = CausalGraph()
        timestamp = datetime.now()

        # Create chain: A -> B -> C -> D
        nodes = [
            CausalNode(
                node_id=node_id,
                event_type=f"event_{node_id}",
                agent_id="agent_1",
                action_data={},
                timestamp=timestamp + timedelta(minutes=i),
            )
            for i, node_id in enumerate(["A", "B", "C", "D"])
        ]

        with patch("src.core.narrative.causal_graph.logger"):
            for node in nodes:
                graph.add_event(node)

            # Add edges
            for i in range(len(nodes) - 1):
                edge = CausalEdge(
                    source_id=nodes[i].node_id,
                    target_id=nodes[i + 1].node_id,
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
                graph.add_causal_relation(edge)

        return graph

    @pytest.mark.unit
    def test_find_causal_chain_basic(self, chain_graph):
        """Test finding basic causal chains."""
        chains = chain_graph.find_causal_chain("A", max_depth=5)

        # Should find chains: [A,B], [A,B,C], [A,B,C,D]
        assert len(chains) == 3
        assert ["A", "B"] in chains
        assert ["A", "B", "C"] in chains
        assert ["A", "B", "C", "D"] in chains

    @pytest.mark.unit
    def test_find_causal_chain_max_depth(self, chain_graph):
        """Test that max_depth limits chain length."""
        chains = chain_graph.find_causal_chain("A", max_depth=2)

        # Should only find [A,B] and [A,B,C]
        assert len(chains) == 2
        assert all(len(chain) <= 3 for chain in chains)  # max_depth + 1

    @pytest.mark.unit
    def test_find_causal_chain_depth_zero(self, chain_graph):
        """Test with depth=0 returns empty list."""
        chains = chain_graph.find_causal_chain("A", max_depth=0)

        assert chains == []

    @pytest.mark.unit
    def test_find_causal_chain_leaf_node(self, chain_graph):
        """Test finding chains from a leaf node."""
        chains = chain_graph.find_causal_chain("D", max_depth=5)

        # D has no successors, so no chains
        assert chains == []

    @pytest.mark.unit
    def test_find_causal_chain_nonexistent_node(self, chain_graph):
        """Test finding chains from a non-existent node raises exception."""
        # The implementation raises NetworkXError for non-existent nodes
        with pytest.raises(Exception):
            chain_graph.find_causal_chain("nonexistent", max_depth=5)

    @pytest.mark.unit
    def test_find_causal_chain_with_branching(self):
        """Test finding chains with branching structure."""
        graph = CausalGraph()
        timestamp = datetime.now()

        # Create branching structure: A -> B -> C, A -> D -> E
        nodes_data = [
            ("A", timestamp),
            ("B", timestamp + timedelta(minutes=1)),
            ("C", timestamp + timedelta(minutes=2)),
            ("D", timestamp + timedelta(minutes=1)),
            ("E", timestamp + timedelta(minutes=2)),
        ]

        with patch("src.core.narrative.causal_graph.logger"):
            for node_id, ts in nodes_data:
                node = CausalNode(
                    node_id=node_id,
                    event_type=f"event_{node_id}",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=ts,
                )
                graph.add_event(node)

            # Add edges
            edges = [
                ("A", "B"),
                ("B", "C"),
                ("A", "D"),
                ("D", "E"),
            ]
            for source, target in edges:
                edge = CausalEdge(
                    source_id=source,
                    target_id=target,
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
                graph.add_causal_relation(edge)

        chains = graph.find_causal_chain("A", max_depth=3)

        # Should find: [A,B], [A,B,C], [A,D], [A,D,E]
        assert len(chains) == 4
        assert ["A", "B"] in chains
        assert ["A", "B", "C"] in chains
        assert ["A", "D"] in chains
        assert ["A", "D", "E"] in chains


class TestCausalGraphGetInfluentialEvents:
    """Tests for CausalGraph.get_influential_events method."""

    @pytest.fixture
    def influential_graph(self):
        """Create a CausalGraph with events of varying influence."""
        graph = CausalGraph()
        now = datetime.now()

        with patch("src.core.narrative.causal_graph.logger"):
            # Create events with different properties
            events = [
                # High influence: many outgoing edges
                CausalNode(
                    node_id="high_influence",
                    event_type="event",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now - timedelta(minutes=5),
                    confidence=1.0,
                    narrative_weight=1.0,
                ),
                # Medium influence
                CausalNode(
                    node_id="medium_influence",
                    event_type="event",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now - timedelta(minutes=4),
                    confidence=0.8,
                    narrative_weight=0.9,
                ),
                # Low influence
                CausalNode(
                    node_id="low_influence",
                    event_type="event",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now - timedelta(minutes=3),
                    confidence=0.5,
                    narrative_weight=0.5,
                ),
                # Old event (outside time window)
                CausalNode(
                    node_id="old_event",
                    event_type="event",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now - timedelta(hours=2),
                    confidence=1.0,
                    narrative_weight=1.0,
                ),
            ]

            for event in events:
                graph.add_event(event)

            # Add edges to create influence
            edges = [
                ("high_influence", "medium_influence"),
                ("high_influence", "low_influence"),
                ("medium_influence", "low_influence"),
            ]
            for source, target in edges:
                edge = CausalEdge(
                    source_id=source,
                    target_id=target,
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
                graph.add_causal_relation(edge)

        return graph

    @pytest.mark.unit
    def test_get_influential_events_basic(self, influential_graph):
        """Test getting influential events."""
        influential = influential_graph.get_influential_events(
            time_window=timedelta(hours=1)
        )

        # Should return list of events
        assert isinstance(influential, list)

    @pytest.mark.unit
    def test_get_influential_events_time_window(self, influential_graph):
        """Test that time window filters events."""
        # Use 10 minute window to exclude old_event
        influential = influential_graph.get_influential_events(
            time_window=timedelta(minutes=10)
        )

        # Should not include old_event
        node_ids = [node.node_id for node in influential]
        assert "old_event" not in node_ids

    @pytest.mark.unit
    def test_get_influential_events_sorted(self, influential_graph):
        """Test that events are sorted by influence."""
        influential = influential_graph.get_influential_events(
            time_window=timedelta(hours=1)
        )

        if len(influential) > 1:
            # Check that events are sorted by narrative_weight * confidence
            influences = [node.narrative_weight * node.confidence for node in influential]
            assert influences == sorted(influences, reverse=True)


class TestCausalGraphDetectNarrativePatterns:
    """Tests for CausalGraph.detect_narrative_patterns method."""

    @pytest.fixture
    def pattern_graph(self):
        """Create a CausalGraph with various narrative patterns."""
        graph = CausalGraph()
        timestamp = datetime.now()

        with patch("src.core.narrative.causal_graph.logger"):
            # Create nodes for different patterns
            nodes = [
                # Conflict node with multiple inputs including contradiction
                CausalNode(
                    node_id="conflict_node",
                    event_type="conflict",
                    agent_id="agent_c",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=10),
                ),
                # Catalyst source
                CausalNode(
                    node_id="catalyst_source",
                    event_type="catalyst",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=timestamp,
                ),
                # Convergence node
                CausalNode(
                    node_id="convergence_node",
                    event_type="convergence",
                    agent_id="agent_4",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=15),
                ),
                # Regular nodes
                CausalNode(
                    node_id="source_a",
                    event_type="event_a",
                    agent_id="agent_a",
                    action_data={},
                    timestamp=timestamp,
                ),
                CausalNode(
                    node_id="source_b",
                    event_type="event_b",
                    agent_id="agent_b",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=1),
                ),
                # Convergence sources (3 different agents)
                CausalNode(
                    node_id="conv_1",
                    event_type="conv_1",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=5),
                ),
                CausalNode(
                    node_id="conv_2",
                    event_type="conv_2",
                    agent_id="agent_2",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=6),
                ),
                CausalNode(
                    node_id="conv_3",
                    event_type="conv_3",
                    agent_id="agent_3",
                    action_data={},
                    timestamp=timestamp + timedelta(minutes=7),
                ),
            ]

            for node in nodes:
                graph.add_event(node)

        return graph

    @pytest.mark.unit
    def test_detect_patterns_returns_expected_keys(self, pattern_graph):
        """Test that detect_narrative_patterns returns expected keys."""
        patterns = pattern_graph.detect_narrative_patterns()

        expected_keys = [
            "conflict_nodes",
            "resolution_nodes",
            "catalyst_events",
            "parallel_storylines",
            "convergence_points",
        ]
        for key in expected_keys:
            assert key in patterns

    @pytest.mark.unit
    def test_detect_conflict_nodes(self, pattern_graph):
        """Test detection of conflict nodes."""
        # Add conflicting edges
        with patch("src.core.narrative.causal_graph.logger"):
            pattern_graph.add_causal_relation(
                CausalEdge(
                    source_id="source_a",
                    target_id="conflict_node",
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
            )
            pattern_graph.add_causal_relation(
                CausalEdge(
                    source_id="source_b",
                    target_id="conflict_node",
                    relation_type=CausalRelationType.CONTRADICTION,
                    strength=0.8,
                    confidence=0.9,
                )
            )

        patterns = pattern_graph.detect_narrative_patterns()

        assert "conflict_node" in patterns["conflict_nodes"]

    @pytest.mark.unit
    def test_detect_catalyst_events(self, pattern_graph):
        """Test detection of catalyst events."""
        # Add catalyst edge
        with patch("src.core.narrative.causal_graph.logger"):
            pattern_graph.add_causal_relation(
                CausalEdge(
                    source_id="catalyst_source",
                    target_id="source_a",
                    relation_type=CausalRelationType.CATALYST,
                    strength=0.8,
                    confidence=0.9,
                )
            )

        patterns = pattern_graph.detect_narrative_patterns()

        assert "catalyst_source" in patterns["catalyst_events"]

    @pytest.mark.unit
    def test_detect_convergence_points(self, pattern_graph):
        """Test detection of convergence points."""
        # Add 3+ edges from different agents to convergence_node
        with patch("src.core.narrative.causal_graph.logger"):
            for source_id in ["conv_1", "conv_2", "conv_3"]:
                pattern_graph.add_causal_relation(
                    CausalEdge(
                        source_id=source_id,
                        target_id="convergence_node",
                        relation_type=CausalRelationType.DIRECT_CAUSE,
                        strength=0.8,
                        confidence=0.9,
                    )
                )

        patterns = pattern_graph.detect_narrative_patterns()

        assert "convergence_node" in patterns["convergence_points"]


class TestCausalGraphPredictNextEvents:
    """Tests for CausalGraph.predict_next_events method."""

    @pytest.fixture
    def prediction_graph(self):
        """Create a CausalGraph suitable for event prediction."""
        graph = CausalGraph()
        now = datetime.now()

        with patch("src.core.narrative.causal_graph.logger"):
            # Create events with causal relations
            nodes = [
                CausalNode(
                    node_id="current",
                    event_type="current_event",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now,
                    confidence=0.9,
                    narrative_weight=1.0,
                ),
                CausalNode(
                    node_id="next_1",
                    event_type="next_event_1",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now + timedelta(minutes=5),
                    confidence=0.8,
                    narrative_weight=0.9,
                ),
                CausalNode(
                    node_id="next_2",
                    event_type="next_event_2",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=now + timedelta(minutes=10),
                    confidence=0.7,
                    narrative_weight=0.8,
                ),
            ]

            for node in nodes:
                graph.add_event(node)

            # Add causal edges
            edges = [
                ("current", "next_1", CausalRelationType.DIRECT_CAUSE, 0.9, 0.9),
                ("current", "next_2", CausalRelationType.INDIRECT_CAUSE, 0.7, 0.8),
            ]
            for source, target, rel_type, strength, confidence in edges:
                graph.add_causal_relation(
                    CausalEdge(
                        source_id=source,
                        target_id=target,
                        relation_type=rel_type,
                        strength=strength,
                        confidence=confidence,
                    )
                )

        return graph

    @pytest.mark.unit
    def test_predict_next_events_returns_list(self, prediction_graph):
        """Test that predict_next_events returns a list."""
        predictions = prediction_graph.predict_next_events({})

        assert isinstance(predictions, list)

    @pytest.mark.unit
    def test_predict_next_events_structure(self, prediction_graph):
        """Test the structure of predicted events."""
        predictions = prediction_graph.predict_next_events({})

        for prediction in predictions:
            assert "event_type" in prediction
            assert "probability" in prediction
            assert "trigger_event" in prediction
            assert "expected_delay" in prediction
            assert "conditions" in prediction

    @pytest.mark.unit
    def test_predict_next_events_sorted_by_probability(self, prediction_graph):
        """Test that predictions are sorted by probability."""
        predictions = prediction_graph.predict_next_events({})

        if len(predictions) > 1:
            probabilities = [p["probability"] for p in predictions]
            assert probabilities == sorted(probabilities, reverse=True)

    @pytest.mark.unit
    def test_predict_next_events_max_ten(self, prediction_graph):
        """Test that at most 10 predictions are returned."""
        # Add more events to potentially exceed 10
        with patch("src.core.narrative.causal_graph.logger"):
            for i in range(15):
                node = CausalNode(
                    node_id=f"extra_{i}",
                    event_type=f"extra_event_{i}",
                    agent_id="agent_1",
                    action_data={},
                    timestamp=datetime.now() + timedelta(minutes=i + 1),
                )
                prediction_graph.add_event(node)
                prediction_graph.add_causal_relation(
                    CausalEdge(
                        source_id="current",
                        target_id=f"extra_{i}",
                        relation_type=CausalRelationType.DIRECT_CAUSE,
                        strength=0.8,
                        confidence=0.9,
                    )
                )

        predictions = prediction_graph.predict_next_events({})

        assert len(predictions) <= 10
