"""Unit tests for ContextAssembler service.

Tests verify:
1. Graph pruning within hop distance
2. Token budget enforcement
3. Node prioritization
4. Edge cases (empty graph, disconnected nodes)

DEV-001: Narrative Engine Context Builder
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from src.contexts.story.application.services.context_assembler import (
    ContextAssembler,
    ContextAssemblerInput,
    SimpleTokenCounter,
    WorldNode,
    create_context_assembler,
)


@pytest.fixture
def simple_counter() -> SimpleTokenCounter:
    """Create a simple token counter for testing."""
    return SimpleTokenCounter()


@pytest.fixture
def assembler(simple_counter: SimpleTokenCounter) -> ContextAssembler:
    """Create a context assembler with simple counter."""
    return ContextAssembler(token_counter=simple_counter)


@pytest.fixture
def sample_world_graph():
    """Create a sample world graph for testing.

    Graph structure:
        char-001 (hero) -- loc-001 (castle) -- char-002 (mentor)
             |                  |
        event-001         faction-001
             |
        loc-002 (forest) -- char-003 (villain)
    """
    if not NETWORKX_AVAILABLE:
        pytest.skip("NetworkX not available")

    G = nx.Graph()

    # Add nodes
    G.add_node(
        "char-001",
        type="character",
        name="Hero Aldric",
        description="A brave warrior seeking justice.",
    )
    G.add_node(
        "char-002",
        type="character",
        name="Mentor Suri",
        description="An elder sage with ancient wisdom.",
    )
    G.add_node(
        "char-003",
        type="character",
        name="Villain Kael",
        description="A cunning adversary.",
    )
    G.add_node(
        "loc-001",
        type="location",
        name="Silver Castle",
        description="The seat of the kingdom's power.",
    )
    G.add_node(
        "loc-002",
        type="location",
        name="Dark Forest",
        description="A treacherous woodland.",
    )
    G.add_node(
        "event-001",
        type="event",
        name="The Great Battle",
        description="A pivotal conflict that changed everything.",
    )
    G.add_node(
        "faction-001",
        type="faction",
        name="Silver Knights",
        description="Defenders of the realm.",
        alignment="lawful_good",
    )

    # Add edges
    G.add_edge("char-001", "loc-001")  # Hero is at castle
    G.add_edge("char-001", "event-001")  # Hero participated in event
    G.add_edge("char-001", "loc-002")  # Hero traveled to forest
    G.add_edge("loc-001", "char-002")  # Mentor is at castle
    G.add_edge("loc-001", "faction-001")  # Faction HQ at castle
    G.add_edge("loc-002", "char-003")  # Villain is in forest

    return G


class TestSimpleTokenCounter:
    """Tests for SimpleTokenCounter."""

    def test_count_empty_string(self, simple_counter: SimpleTokenCounter):
        """Empty string should return 1 (minimum)."""
        assert simple_counter.count("") == 1

    def test_count_short_text(self, simple_counter: SimpleTokenCounter):
        """Short text should return reasonable estimate."""
        # "Hello world" is 11 chars, ~3 tokens at 4 chars/token
        result = simple_counter.count("Hello world")
        assert result >= 2
        assert result <= 5

    def test_count_long_text(self, simple_counter: SimpleTokenCounter):
        """Long text should scale proportionally."""
        short = simple_counter.count("Hello")
        long = simple_counter.count("Hello " * 100)
        assert long > short * 50  # Should be roughly linear


@pytest.mark.skipif(not NETWORKX_AVAILABLE, reason="NetworkX not available")
class TestContextAssemblerGraphPruning:
    """Tests for graph pruning functionality."""

    def test_finds_direct_neighbors(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should find nodes directly connected to active character."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=1,
        )

        result = assembler.assemble(sample_world_graph, input)

        # char-001 connects to: loc-001, event-001, loc-002
        assert "char-001" in result.included_nodes
        assert "loc-001" in result.included_nodes
        assert "event-001" in result.included_nodes
        assert "loc-002" in result.included_nodes
        # char-002 is 2 hops away (char-001 -> loc-001 -> char-002)
        assert "char-002" not in result.included_nodes

    def test_finds_two_hop_neighbors(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should find nodes within 2 hops of active character."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Should include 2-hop neighbors now
        assert "char-002" in result.included_nodes  # loc-001 -> char-002
        assert "faction-001" in result.included_nodes  # loc-001 -> faction-001
        assert "char-003" in result.included_nodes  # loc-002 -> char-003

    def test_multiple_active_characters(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should find nodes near any active character."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001", "char-003"],
            max_tokens=10000,
            hop_distance=1,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Both characters and their neighbors
        assert "char-001" in result.included_nodes
        assert "char-003" in result.included_nodes
        assert "loc-001" in result.included_nodes  # Near char-001
        assert "loc-002" in result.included_nodes  # Near both

    def test_nonexistent_character_graceful(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should handle nonexistent character ID gracefully."""
        input = ContextAssemblerInput(
            active_character_ids=["nonexistent-char"],
            max_tokens=10000,
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Should return valid result with no nodes
        assert result.included_nodes == []
        assert "No relevant context" in result.context_text


@pytest.mark.skipif(not NETWORKX_AVAILABLE, reason="NetworkX not available")
class TestContextAssemblerTokenBudget:
    """Tests for token budget enforcement."""

    def test_respects_token_budget(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should truncate context to fit within token budget."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=100,  # Very small budget
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Token count should be within budget
        assert result.token_count <= 100
        # Should be marked as truncated
        assert result.truncated is True
        # Should still include some nodes
        assert len(result.included_nodes) > 0

    def test_large_budget_no_truncation(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Should include all nodes when budget is large."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=100000,
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Should not be truncated
        assert result.truncated is False
        # Should include all relevant nodes
        assert len(result.included_nodes) >= 6


@pytest.mark.skipif(not NETWORKX_AVAILABLE, reason="NetworkX not available")
class TestContextAssemblerPrioritization:
    """Tests for node prioritization."""

    def test_active_characters_first(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Active characters should appear first in context."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # The character section should come before other sections
        # or active character should be early in the output
        assert "Hero Aldric" in result.context_text
        aldric_pos = result.context_text.find("Hero Aldric")
        # Should be in the first half of the context
        assert aldric_pos < len(result.context_text) / 2

    def test_locations_prioritized_for_setting(
        self, assembler: ContextAssembler, sample_world_graph
    ):
        """Locations should be prioritized after characters."""
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=2,
        )

        result = assembler.assemble(sample_world_graph, input)

        # Context should include location descriptions
        assert (
            "Silver Castle" in result.context_text
            or "Dark Forest" in result.context_text
        )


class TestContextAssemblerEdgeCases:
    """Tests for edge cases."""

    def test_empty_graph(self, assembler: ContextAssembler):
        """Should handle empty graph gracefully."""
        if not NETWORKX_AVAILABLE:
            pytest.skip("NetworkX not available")

        G = nx.Graph()
        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=2,
        )

        result = assembler.assemble(G, input)

        assert result.included_nodes == []
        assert result.truncated is False

    def test_disconnected_nodes(self, assembler: ContextAssembler):
        """Should handle disconnected nodes correctly."""
        if not NETWORKX_AVAILABLE:
            pytest.skip("NetworkX not available")

        G = nx.Graph()
        G.add_node("char-001", type="character", name="Hero", description="The hero")
        G.add_node(
            "char-002", type="character", name="Isolated", description="Disconnected"
        )
        # No edges between them

        input = ContextAssemblerInput(
            active_character_ids=["char-001"],
            max_tokens=10000,
            hop_distance=10,  # Large hop distance
        )

        result = assembler.assemble(G, input)

        # Should only include char-001
        assert "char-001" in result.included_nodes
        assert "char-002" not in result.included_nodes


class TestFactoryFunction:
    """Tests for create_context_assembler factory."""

    def test_creates_with_simple_counter(self):
        """Should create assembler with simple counter when tiktoken disabled."""
        assembler = create_context_assembler(use_tiktoken=False)
        assert assembler is not None
        # Should be able to assemble context
        if NETWORKX_AVAILABLE:
            G = nx.Graph()
            G.add_node("char-001", type="character", name="Test", description="Test")
            input = ContextAssemblerInput(
                active_character_ids=["char-001"],
                max_tokens=1000,
                hop_distance=1,
            )
            result = assembler.assemble(G, input)
            assert result.context_text is not None


class TestWorldNode:
    """Tests for WorldNode dataclass."""

    def test_world_node_immutable(self):
        """WorldNode should be immutable (frozen)."""
        node = WorldNode(
            id="test-001",
            node_type="character",
            name="Test",
            description="Description",
        )

        with pytest.raises(AttributeError):
            node.name = "New Name"  # type: ignore

    def test_world_node_defaults(self):
        """WorldNode should have sensible defaults."""
        node = WorldNode(
            id="test-001",
            node_type="character",
            name="Test",
        )

        assert node.description == ""
        assert node.metadata == {}
