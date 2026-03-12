#!/usr/bin/env python3
"""Unit tests for src/core/narrative/types.py module."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.core.narrative.types import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    CausalRelationType,
    EventPriority,
    NegotiationProposal,
    NegotiationResponse,
    NegotiationSession,
    NegotiationStatus,
)


class TestCausalRelationType:
    """Tests for CausalRelationType enum."""

    @pytest.mark.parametrize(
        "relation_type,expected_value",
        [
            (CausalRelationType.DIRECT_CAUSE, "direct_cause"),
            (CausalRelationType.INDIRECT_CAUSE, "indirect_cause"),
            (CausalRelationType.ENABLER, "enabler"),
            (CausalRelationType.CATALYST, "catalyst"),
            (CausalRelationType.INHIBITOR, "inhibitor"),
            (CausalRelationType.AMPLIFIER, "amplifier"),
            (CausalRelationType.CONTRADICTION, "contradiction"),
        ],
    )
    @pytest.mark.unit
    def test_causal_relation_type_values(self, relation_type, expected_value):
        """Test that enum values are correctly defined."""
        assert relation_type.value == expected_value

    @pytest.mark.unit
    def test_all_relation_types_present(self):
        """Test that all expected relation types are defined."""
        expected_types = {
            "DIRECT_CAUSE",
            "INDIRECT_CAUSE",
            "ENABLER",
            "CATALYST",
            "INHIBITOR",
            "AMPLIFIER",
            "CONTRADICTION",
        }
        actual_types = {t.name for t in CausalRelationType}
        assert actual_types == expected_types


class TestNegotiationStatus:
    """Tests for NegotiationStatus enum."""

    @pytest.mark.parametrize(
        "status,expected_value",
        [
            (NegotiationStatus.INITIATED, "initiated"),
            (NegotiationStatus.IN_PROGRESS, "in_progress"),
            (NegotiationStatus.DEADLOCK, "deadlock"),
            (NegotiationStatus.RESOLVED, "resolved"),
            (NegotiationStatus.FAILED, "failed"),
            (NegotiationStatus.TIMEOUT, "timeout"),
        ],
    )
    @pytest.mark.unit
    def test_negotiation_status_values(self, status, expected_value):
        """Test that enum values are correctly defined."""
        assert status.value == expected_value


class TestEventPriority:
    """Tests for EventPriority enum."""

    @pytest.mark.parametrize(
        "priority,expected_value",
        [
            (EventPriority.CRITICAL, 1),
            (EventPriority.HIGH, 2),
            (EventPriority.MEDIUM, 3),
            (EventPriority.LOW, 4),
            (EventPriority.TRIVIAL, 5),
        ],
    )
    @pytest.mark.unit
    def test_event_priority_values(self, priority, expected_value):
        """Test that priority values are correctly ordered."""
        assert priority.value == expected_value

    @pytest.mark.unit
    def test_priority_ordering(self):
        """Test that priorities are correctly ordered from highest to lowest."""
        assert EventPriority.CRITICAL.value < EventPriority.HIGH.value
        assert EventPriority.HIGH.value < EventPriority.MEDIUM.value
        assert EventPriority.MEDIUM.value < EventPriority.LOW.value
        assert EventPriority.LOW.value < EventPriority.TRIVIAL.value


class TestCausalNode:
    """Tests for CausalNode dataclass."""

    @pytest.mark.unit
    def test_causal_node_creation(self):
        """Test basic CausalNode creation."""
        timestamp = datetime.now()
        node = CausalNode(
            node_id="test_node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={"key": "value"},
            timestamp=timestamp,
            location="test_location",
            participants=["agent_1", "agent_2"],
            confidence=0.8,
            narrative_weight=0.9,
            metadata={"custom": "data"},
        )

        assert node.node_id == "test_node_1"
        assert node.event_type == "test_event"
        assert node.agent_id == "agent_1"
        assert node.action_data == {"key": "value"}
        assert node.timestamp == timestamp
        assert node.location == "test_location"
        assert node.participants == ["agent_1", "agent_2"]
        assert node.confidence == 0.8
        assert node.narrative_weight == 0.9
        assert node.metadata == {"custom": "data"}

    @pytest.mark.unit
    def test_causal_node_defaults(self):
        """Test CausalNode default values."""
        timestamp = datetime.now()
        node = CausalNode(
            node_id="test_node",
            event_type="test_event",
            agent_id=None,
            action_data={},
            timestamp=timestamp,
        )

        assert node.location is None
        assert node.participants == []
        assert node.confidence == 1.0
        assert node.narrative_weight == 1.0
        assert node.metadata == {}

    @pytest.mark.unit
    def test_causal_node_hash_and_eq(self):
        """Test CausalNode hashing and equality."""
        timestamp = datetime.now()
        node1 = CausalNode(
            node_id="node_1",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )
        node2 = CausalNode(
            node_id="node_1",
            event_type="different_event",
            agent_id="agent_2",
            action_data={"different": "data"},
            timestamp=timestamp,
        )
        node3 = CausalNode(
            node_id="node_2",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )

        # Same node_id should be equal
        assert node1 == node2
        assert hash(node1) == hash(node2)

        # Different node_id should not be equal
        assert node1 != node3
        assert hash(node1) != hash(node3)

    @pytest.mark.unit
    def test_causal_node_eq_with_non_causal_node(self):
        """Test CausalNode equality with non-CausalNode object."""
        timestamp = datetime.now()
        node = CausalNode(
            node_id="node_1",
            event_type="event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )

        assert node != "not_a_node"
        assert node != 123
        assert node != {"node_id": "node_1"}

    @pytest.mark.unit
    def test_causal_node_to_dict(self):
        """Test CausalNode to_dict method."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={"action": "test"},
            timestamp=timestamp,
            location="loc_1",
            participants=["agent_1", "agent_2"],
            confidence=0.85,
            narrative_weight=0.9,
            metadata={"key": "value"},
        )

        result = node.to_dict()

        assert result["node_id"] == "node_1"
        assert result["event_type"] == "test_event"
        assert result["agent_id"] == "agent_1"
        assert result["action_data"] == {"action": "test"}
        assert result["timestamp"] == "2024-01-15T10:30:00"
        assert result["location"] == "loc_1"
        assert result["participants"] == ["agent_1", "agent_2"]
        assert result["confidence"] == 0.85
        assert result["narrative_weight"] == 0.9
        assert result["metadata"] == {"key": "value"}


class TestCausalEdge:
    """Tests for CausalEdge dataclass."""

    @pytest.mark.unit
    def test_causal_edge_creation(self):
        """Test basic CausalEdge creation."""
        delay = timedelta(seconds=300)
        edge = CausalEdge(
            source_id="node_1",
            target_id="node_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
            delay=delay,
            conditions=["condition_1", "condition_2"],
            metadata={"key": "value"},
        )

        assert edge.source_id == "node_1"
        assert edge.target_id == "node_2"
        assert edge.relation_type == CausalRelationType.DIRECT_CAUSE
        assert edge.strength == 0.8
        assert edge.confidence == 0.9
        assert edge.delay == delay
        assert edge.conditions == ["condition_1", "condition_2"]
        assert edge.metadata == {"key": "value"}

    @pytest.mark.unit
    def test_causal_edge_defaults(self):
        """Test CausalEdge default values."""
        edge = CausalEdge(
            source_id="node_1",
            target_id="node_2",
            relation_type=CausalRelationType.INDIRECT_CAUSE,
            strength=0.5,
            confidence=0.7,
        )

        assert edge.delay == timedelta(0)
        assert edge.conditions == []
        assert edge.metadata == {}

    @pytest.mark.unit
    def test_causal_edge_to_dict(self):
        """Test CausalEdge to_dict method."""
        delay = timedelta(seconds=150)
        edge = CausalEdge(
            source_id="node_1",
            target_id="node_2",
            relation_type=CausalRelationType.CATALYST,
            strength=0.75,
            confidence=0.85,
            delay=delay,
            conditions=["cond_1"],
            metadata={"meta": "data"},
        )

        result = edge.to_dict()

        assert result["source_id"] == "node_1"
        assert result["target_id"] == "node_2"
        assert result["relation_type"] == "catalyst"
        assert result["strength"] == 0.75
        assert result["confidence"] == 0.85
        assert result["delay_seconds"] == 150.0
        assert result["conditions"] == ["cond_1"]
        assert result["metadata"] == {"meta": "data"}


class TestCausalGraph:
    """Tests for CausalGraph class."""

    @pytest.fixture
    def causal_graph(self):
        """Create a fresh CausalGraph instance."""
        return CausalGraph()

    @pytest.fixture
    def sample_node(self):
        """Create a sample CausalNode."""
        return CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={"action": "test"},
            timestamp=datetime.now(),
            location="loc_1",
        )

    @pytest.mark.unit
    def test_causal_graph_init(self, causal_graph):
        """Test CausalGraph initialization."""
        assert causal_graph.graph is not None
        assert causal_graph.nodes == {}
        assert causal_graph.edges == {}
        assert causal_graph.temporal_index == {}
        assert causal_graph.agent_index == {}
        assert causal_graph.location_index == {}

    @pytest.mark.unit
    def test_add_event(self, causal_graph, sample_node):
        """Test adding an event to the causal graph."""
        with patch("src.core.narrative.types.logger"):
            result = causal_graph.add_event(sample_node)

        assert result == "node_1"
        assert "node_1" in causal_graph.nodes
        assert causal_graph.nodes["node_1"] == sample_node
        assert "node_1" in causal_graph.graph.nodes()

    @pytest.mark.unit
    def test_add_event_updates_indices(self, causal_graph):
        """Test that add_event updates all indices."""
        timestamp = datetime(2024, 1, 15, 10, 0, 0)
        node = CausalNode(
            node_id="node_1",
            event_type="test_event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
            location="loc_1",
        )

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(node)

        assert timestamp in causal_graph.temporal_index
        assert "node_1" in causal_graph.temporal_index[timestamp]
        assert "agent_1" in causal_graph.agent_index
        assert "node_1" in causal_graph.agent_index["agent_1"]
        assert "loc_1" in causal_graph.location_index
        assert "node_1" in causal_graph.location_index["loc_1"]

    @pytest.mark.unit
    def test_add_causal_relation_success(self, causal_graph):
        """Test successfully adding a causal relation."""
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
        edge = CausalEdge(
            source_id="node_1",
            target_id="node_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(node1)
            causal_graph.add_event(node2)
            result = causal_graph.add_causal_relation(edge)

        assert result is True
        assert ("node_1", "node_2") in causal_graph.edges
        assert causal_graph.graph.has_edge("node_1", "node_2")

    @pytest.mark.unit
    def test_add_causal_relation_missing_nodes(self, causal_graph):
        """Test adding a causal relation with missing nodes."""
        edge = CausalEdge(
            source_id="nonexistent_1",
            target_id="nonexistent_2",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.types.logger") as mock_logger:
            result = causal_graph.add_causal_relation(edge)
            mock_logger.warning.assert_called_once()

        assert result is False

    @pytest.mark.unit
    def test_find_causal_chain(self, causal_graph):
        """Test finding causal chains."""
        timestamp = datetime.now()

        # Create a chain: node1 -> node2 -> node3
        nodes = []
        for i in range(3):
            node = CausalNode(
                node_id=f"node_{i+1}",
                event_type=f"event_{i+1}",
                agent_id="agent_1",
                action_data={},
                timestamp=timestamp + timedelta(minutes=i),
            )
            nodes.append(node)
            with patch("src.core.narrative.types.logger"):
                causal_graph.add_event(node)

        # Add edges
        edges = [
            CausalEdge(
                source_id="node_1",
                target_id="node_2",
                relation_type=CausalRelationType.DIRECT_CAUSE,
                strength=0.8,
                confidence=0.9,
            ),
            CausalEdge(
                source_id="node_2",
                target_id="node_3",
                relation_type=CausalRelationType.DIRECT_CAUSE,
                strength=0.7,
                confidence=0.8,
            ),
        ]

        with patch("src.core.narrative.types.logger"):
            for edge in edges:
                causal_graph.add_causal_relation(edge)

        chains = causal_graph.find_causal_chain("node_1", max_depth=3)

        assert len(chains) > 0
        assert ["node_1", "node_2"] in chains
        assert ["node_1", "node_2", "node_3"] in chains

    @pytest.mark.unit
    def test_find_causal_chain_max_depth(self, causal_graph):
        """Test that max_depth limits the chain search."""
        timestamp = datetime.now()

        # Create a longer chain
        for i in range(5):
            node = CausalNode(
                node_id=f"node_{i+1}",
                event_type=f"event_{i+1}",
                agent_id="agent_1",
                action_data={},
                timestamp=timestamp + timedelta(minutes=i),
            )
            with patch("src.core.narrative.types.logger"):
                causal_graph.add_event(node)

            if i > 0:
                edge = CausalEdge(
                    source_id=f"node_{i}",
                    target_id=f"node_{i+1}",
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
                with patch("src.core.narrative.types.logger"):
                    causal_graph.add_causal_relation(edge)

        chains = causal_graph.find_causal_chain("node_1", max_depth=2)

        # Should not find chains longer than max_depth
        for chain in chains:
            assert len(chain) <= 3  # max_depth + 1 (start node)

    @pytest.mark.unit
    def test_get_influential_events(self, causal_graph):
        """Test getting influential events."""
        now = datetime.now()

        # Create events with different timestamps and weights
        for i in range(5):
            node = CausalNode(
                node_id=f"node_{i+1}",
                event_type=f"event_{i+1}",
                agent_id="agent_1",
                action_data={},
                timestamp=now - timedelta(minutes=i * 10),
                confidence=0.9,
                narrative_weight=1.0 + i * 0.2,
            )
            with patch("src.core.narrative.types.logger"):
                causal_graph.add_event(node)

            # Add outgoing edges to increase influence
            if i < 4:
                edge = CausalEdge(
                    source_id=f"node_{i+1}",
                    target_id=f"node_{i+2}",
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
                with patch("src.core.narrative.types.logger"):
                    causal_graph.add_causal_relation(edge)

        influential = causal_graph.get_influential_events(time_window=timedelta(hours=1))

        # Should return events sorted by influence
        assert isinstance(influential, list)

    @pytest.mark.unit
    def test_detect_narrative_patterns_conflict_nodes(self, causal_graph):
        """Test detecting conflict nodes in narrative patterns."""
        timestamp = datetime.now()

        # Create a node with conflicting inputs
        target_node = CausalNode(
            node_id="target_node",
            event_type="conflict_event",
            agent_id="agent_3",
            action_data={},
            timestamp=timestamp + timedelta(minutes=10),
        )

        source_nodes = []
        for i in range(2):
            node = CausalNode(
                node_id=f"source_{i+1}",
                event_type=f"event_{i+1}",
                agent_id=f"agent_{i+1}",
                action_data={},
                timestamp=timestamp + timedelta(minutes=i),
            )
            source_nodes.append(node)

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(target_node)
            for node in source_nodes:
                causal_graph.add_event(node)

            # Add conflicting edges
            causal_graph.add_causal_relation(
                CausalEdge(
                    source_id="source_1",
                    target_id="target_node",
                    relation_type=CausalRelationType.DIRECT_CAUSE,
                    strength=0.8,
                    confidence=0.9,
                )
            )
            causal_graph.add_causal_relation(
                CausalEdge(
                    source_id="source_2",
                    target_id="target_node",
                    relation_type=CausalRelationType.CONTRADICTION,
                    strength=0.8,
                    confidence=0.9,
                )
            )

        patterns = causal_graph.detect_narrative_patterns()

        assert "conflict_nodes" in patterns
        assert "target_node" in patterns["conflict_nodes"]

    @pytest.mark.unit
    def test_detect_narrative_patterns_catalyst_events(self, causal_graph):
        """Test detecting catalyst events."""
        timestamp = datetime.now()

        # Create nodes with catalyst relation
        node1 = CausalNode(
            node_id="catalyst_node",
            event_type="catalyst_event",
            agent_id="agent_1",
            action_data={},
            timestamp=timestamp,
        )
        node2 = CausalNode(
            node_id="target_node",
            event_type="target_event",
            agent_id="agent_2",
            action_data={},
            timestamp=timestamp + timedelta(minutes=5),
        )

        edge = CausalEdge(
            source_id="catalyst_node",
            target_id="target_node",
            relation_type=CausalRelationType.CATALYST,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(node1)
            causal_graph.add_event(node2)
            causal_graph.add_causal_relation(edge)

        patterns = causal_graph.detect_narrative_patterns()

        assert "catalyst_events" in patterns
        assert "catalyst_node" in patterns["catalyst_events"]

    @pytest.mark.unit
    def test_detect_narrative_patterns_convergence_points(self, causal_graph):
        """Test detecting convergence points."""
        timestamp = datetime.now()

        # Create a node with 3+ inputs from different agents
        target_node = CausalNode(
            node_id="convergence_node",
            event_type="convergence_event",
            agent_id="agent_4",
            action_data={},
            timestamp=timestamp + timedelta(minutes=10),
        )

        source_nodes = []
        for i in range(3):
            node = CausalNode(
                node_id=f"converge_source_{i+1}",
                event_type=f"event_{i+1}",
                agent_id=f"agent_{i+1}",
                action_data={},
                timestamp=timestamp + timedelta(minutes=i),
            )
            source_nodes.append(node)

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(target_node)
            for node in source_nodes:
                causal_graph.add_event(node)
                causal_graph.add_causal_relation(
                    CausalEdge(
                        source_id=node.node_id,
                        target_id="convergence_node",
                        relation_type=CausalRelationType.DIRECT_CAUSE,
                        strength=0.8,
                        confidence=0.9,
                    )
                )

        patterns = causal_graph.detect_narrative_patterns()

        assert "convergence_points" in patterns
        assert "convergence_node" in patterns["convergence_points"]

    @pytest.mark.unit
    def test_predict_next_events(self, causal_graph):
        """Test predicting next events."""
        now = datetime.now()

        # Create events with causal relations
        node1 = CausalNode(
            node_id="current_event",
            event_type="current",
            agent_id="agent_1",
            action_data={},
            timestamp=now,
            confidence=0.9,
            narrative_weight=1.0,
        )
        node2 = CausalNode(
            node_id="next_event",
            event_type="next",
            agent_id="agent_1",
            action_data={},
            timestamp=now + timedelta(minutes=5),
            confidence=0.8,
            narrative_weight=0.9,
        )

        edge = CausalEdge(
            source_id="current_event",
            target_id="next_event",
            relation_type=CausalRelationType.DIRECT_CAUSE,
            strength=0.8,
            confidence=0.9,
        )

        with patch("src.core.narrative.types.logger"):
            causal_graph.add_event(node1)
            causal_graph.add_event(node2)
            causal_graph.add_causal_relation(edge)

        predictions = causal_graph.predict_next_events({})

        assert isinstance(predictions, list)


class TestNegotiationProposal:
    """Tests for NegotiationProposal dataclass."""

    @pytest.mark.unit
    def test_negotiation_proposal_creation(self):
        """Test basic NegotiationProposal creation."""
        timestamp = datetime.now()
        expires = timestamp + timedelta(minutes=30)

        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="action",
            content={"action": "test"},
            target_agents=["agent_2", "agent_3"],
            requirements=["req_1", "req_2"],
            benefits_offered={"gold": 100},
            timestamp=timestamp,
            expires_at=expires,
        )

        assert proposal.proposal_id == "prop_1"
        assert proposal.proposer_id == "agent_1"
        assert proposal.proposal_type == "action"
        assert proposal.content == {"action": "test"}
        assert proposal.target_agents == ["agent_2", "agent_3"]
        assert proposal.requirements == ["req_1", "req_2"]
        assert proposal.benefits_offered == {"gold": 100}
        assert proposal.timestamp == timestamp
        assert proposal.expires_at == expires

    @pytest.mark.unit
    def test_negotiation_proposal_defaults(self):
        """Test NegotiationProposal default values."""
        proposal = NegotiationProposal(
            proposal_id="prop_1",
            proposer_id="agent_1",
            proposal_type="cooperation",
            content={},
            target_agents=["agent_2"],
        )

        assert proposal.requirements == []
        assert proposal.benefits_offered == {}
        assert proposal.timestamp is not None
        assert proposal.expires_at is None


class TestNegotiationResponse:
    """Tests for NegotiationResponse dataclass."""

    @pytest.mark.unit
    def test_negotiation_response_creation(self):
        """Test basic NegotiationResponse creation."""
        timestamp = datetime.now()

        response = NegotiationResponse(
            response_id="resp_1",
            proposal_id="prop_1",
            responder_id="agent_2",
            response_type="accept",
            content={"reason": "agreed"},
            counter_proposal={"type": "counter"},
            conditions=["cond_1"],
            timestamp=timestamp,
        )

        assert response.response_id == "resp_1"
        assert response.proposal_id == "prop_1"
        assert response.responder_id == "agent_2"
        assert response.response_type == "accept"
        assert response.content == {"reason": "agreed"}
        assert response.counter_proposal == {"type": "counter"}
        assert response.conditions == ["cond_1"]
        assert response.timestamp == timestamp

    @pytest.mark.unit
    def test_negotiation_response_defaults(self):
        """Test NegotiationResponse default values."""
        response = NegotiationResponse(
            response_id="resp_1",
            proposal_id="prop_1",
            responder_id="agent_2",
            response_type="reject",
            content={},
        )

        assert response.counter_proposal is None
        assert response.conditions == []
        assert response.timestamp is not None


class TestNegotiationSession:
    """Tests for NegotiationSession dataclass."""

    @pytest.mark.unit
    def test_negotiation_session_creation(self):
        """Test basic NegotiationSession creation."""
        timestamp = datetime.now()

        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1", "agent_2"],
            topic="test_topic",
            status=NegotiationStatus.INITIATED,
            proposals=[],
            responses=[],
            created_at=timestamp,
            updated_at=timestamp,
            resolution=None,
            timeout_minutes=45,
        )

        assert session.session_id == "session_1"
        assert session.participants == ["agent_1", "agent_2"]
        assert session.topic == "test_topic"
        assert session.status == NegotiationStatus.INITIATED
        assert session.proposals == []
        assert session.responses == []
        assert session.created_at == timestamp
        assert session.updated_at == timestamp
        assert session.resolution is None
        assert session.timeout_minutes == 45

    @pytest.mark.unit
    def test_negotiation_session_defaults(self):
        """Test NegotiationSession default values."""
        session = NegotiationSession(
            session_id="session_1",
            participants=["agent_1"],
            topic="topic",
            status=NegotiationStatus.IN_PROGRESS,
        )

        assert session.proposals == []
        assert session.responses == []
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.resolution is None
        assert session.timeout_minutes == 30
