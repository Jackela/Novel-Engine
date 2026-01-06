#!/usr/bin/env python3
"""
Tests for LayeredMemorySystem

Testing Coverage:
- Unit tests for all public methods (18 methods)
- Integration tests for cross-layer coordination
- Edge cases and error conditions
- Performance and consolidation tests
- Async operation handling
"""

import asyncio
from datetime import datetime, timedelta

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio  # codeql[py/unused-global-variable]

from src.core.data_models import MemoryItem, MemoryType
from src.database.context_db import ContextDatabase
from src.memory.layered_memory import (
    LayeredMemorySystem,
    MemoryPriority,
    MemoryQueryRequest,
    MemoryQueryResult,
)


class TestLayeredMemorySystem:
    """Unit tests for LayeredMemorySystem unified memory architecture."""

    @pytest_asyncio.fixture
    async def database(self):
        """Setup test database."""
        db = ContextDatabase(":memory:")
        await db.initialize()
        yield db
        await db.close()

    @pytest_asyncio.fixture
    async def layered_memory(self, database):
        """Setup test LayeredMemorySystem instance."""
        system = LayeredMemorySystem(
            agent_id="test_agent_001",
            database=database,
            working_capacity=7,
            episodic_max=100,
            semantic_max=500,
            emotional_max=50,
        )
        yield system

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory item for testing."""
        return MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="A significant event occurred at the main gate.",
            emotional_weight=7.0,
            relevance_score=0.8,
            participants=["Character A", "Character B"],
            location="Main Gate",
        )

    async def test_initialization(self, layered_memory):
        """Test LayeredMemorySystem initialization."""
        assert layered_memory.agent_id == "test_agent_001"
        assert layered_memory.working_memory is not None
        assert layered_memory.episodic_memory is not None
        assert layered_memory.semantic_memory is not None
        assert layered_memory.emotional_memory is not None
        assert layered_memory.total_queries == 0
        assert layered_memory.total_storage_operations == 0

    async def test_store_memory_success(self, layered_memory, sample_memory):
        """Test successful memory storage across layers."""
        result = await layered_memory.store_memory(sample_memory)

        assert result.success is True
        assert "stored_layers" in result.data
        assert len(result.data["stored_layers"]) > 0
        assert result.data["success_count"] > 0
        assert layered_memory.total_storage_operations == 1

    async def test_store_memory_episodic(self, layered_memory):
        """Test episodic memory storage."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event happened with character interaction.",
            emotional_weight=5.0,
            participants=["Character A"],
        )

        result = await layered_memory.store_memory(memory)

        assert result.success is True
        assert "episodic" in result.data["stored_layers"]
        assert "working" in result.data["stored_layers"]

    async def test_store_memory_semantic(self, layered_memory):
        """Test semantic memory storage."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The sky is blue.",
            relevance_score=0.9,
        )

        result = await layered_memory.store_memory(memory)

        assert result.success is True
        assert "semantic" in result.data["stored_layers"]
        assert "working" in result.data["stored_layers"]

    async def test_store_memory_emotional(self, layered_memory):
        """Test emotional memory storage."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content="Felt proud after victory.",
            emotional_weight=8.0,
            relevance_score=0.85,
        )

        result = await layered_memory.store_memory(memory)

        assert result.success is True
        assert "emotional" in result.data["stored_layers"]

    async def test_store_memory_force_layer(self, layered_memory, sample_memory):
        """Test forced layer storage."""
        result = await layered_memory.store_memory(sample_memory, force_layer="working")

        assert result.success is True
        assert result.data["stored_layers"] == ["working"]

    async def test_store_memory_cross_layer_linking(self, layered_memory):
        """Test cross-layer association creation."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event with emotional significance.",
            emotional_weight=7.0,
        )

        result = await layered_memory.store_memory(memory, cross_layer_linking=True)

        assert result.success is True
        assert len(result.data["stored_layers"]) > 1
        assert result.data["cross_layer_associations"] > 0

    async def test_query_memories_basic(self, layered_memory, sample_memory):
        """Test basic memory query."""
        await layered_memory.store_memory(sample_memory)

        query = MemoryQueryRequest(
            query_text="event gate",
            max_results=10,
            relevance_threshold=0.3,
        )

        result = await layered_memory.query_memories(query)

        assert result.success is True
        assert "query_result" in result.data
        query_result = result.data["query_result"]
        assert isinstance(query_result, MemoryQueryResult)
        assert layered_memory.total_queries == 1

    async def test_query_memories_with_temporal_range(self, layered_memory):
        """Test memory query with temporal filtering."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Recent event.",
            timestamp=datetime.now(),
        )
        await layered_memory.store_memory(memory)

        start_time = datetime.now() - timedelta(hours=1)
        end_time = datetime.now() + timedelta(hours=1)

        query = MemoryQueryRequest(
            query_text="event",
            temporal_range=(start_time, end_time),
            memory_types=[MemoryType.EPISODIC],
        )

        result = await layered_memory.query_memories(query)

        assert result.success is True
        query_result = result.data["query_result"]
        assert query_result.total_found >= 0

    async def test_query_memories_with_participants(self, layered_memory):
        """Test memory query with participant filtering."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Interaction with Character A.",
            participants=["Character A", "Character B"],
        )
        await layered_memory.store_memory(memory)

        query = MemoryQueryRequest(
            query_text="interaction",
            participants=["Character A"],
            relevance_threshold=0.1,
        )

        result = await layered_memory.query_memories(query)

        assert result.success is True

    async def test_query_memories_relevance_threshold(self, layered_memory):
        """Test relevance threshold filtering."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="Important knowledge fact.",
            relevance_score=0.9,
        )
        await layered_memory.store_memory(memory)

        high_threshold_query = MemoryQueryRequest(
            query_text="knowledge",
            relevance_threshold=0.95,
        )

        result = await layered_memory.query_memories(high_threshold_query)

        assert result.success is True

    async def test_query_memories_max_results(self, layered_memory):
        """Test max results limiting."""
        for i in range(10):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event number {i}",
            )
            await layered_memory.store_memory(memory)

        query = MemoryQueryRequest(
            query_text="event",
            max_results=5,
            relevance_threshold=0.0,
        )

        result = await layered_memory.query_memories(query)

        assert result.success is True
        query_result = result.data["query_result"]
        assert len(query_result.memories) <= 5

    async def test_consolidate_memories_full(self, layered_memory, sample_memory):
        """Test full memory consolidation."""
        await layered_memory.store_memory(sample_memory)

        result = await layered_memory.consolidate_memories(consolidation_type="full")

        assert result.success is True
        assert "consolidation_results" in result.data
        assert "consolidation_duration_ms" in result.data
        assert result.data["optimization_complete"] is True

    async def test_consolidate_memories_partial(self, layered_memory, sample_memory):
        """Test partial memory consolidation."""
        await layered_memory.store_memory(sample_memory)

        result = await layered_memory.consolidate_memories(consolidation_type="partial")

        assert result.success is True
        assert "consolidation_results" in result.data
        assert result.data["optimization_complete"] is False

    async def test_get_unified_statistics(self, layered_memory, sample_memory):
        """Test unified statistics retrieval."""
        await layered_memory.store_memory(sample_memory)

        stats = layered_memory.get_unified_statistics()

        assert stats["agent_id"] == "test_agent_001"
        assert "working_memory" in stats
        assert "episodic_memory" in stats
        assert "semantic_memory" in stats
        assert "coordination_stats" in stats
        assert "performance_metrics" in stats
        assert stats["coordination_stats"]["total_storage_operations"] >= 1

    async def test_determine_storage_layers_episodic(self, layered_memory):
        """Test storage layer determination for episodic memories."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="An event happened yesterday.",
        )

        layers = layered_memory._determine_storage_layers(memory, None)

        assert "working" in layers
        assert "episodic" in layers

    async def test_determine_storage_layers_semantic(self, layered_memory):
        """Test storage layer determination for semantic memories."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The capital is Paris.",
        )

        layers = layered_memory._determine_storage_layers(memory, None)

        assert "working" in layers
        assert "semantic" in layers

    async def test_determine_storage_layers_emotional(self, layered_memory):
        """Test storage layer determination for emotional memories."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content="Felt happy today.",
            emotional_weight=6.0,
        )

        layers = layered_memory._determine_storage_layers(memory, None)

        assert "working" in layers
        assert "emotional" in layers

    async def test_calculate_relevance(self, layered_memory):
        """Test relevance calculation."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Battle at the main gate with Commander Lex.",
            participants=["Commander Lex"],
            relevance_score=0.8,
        )

        query = MemoryQueryRequest(
            query_text="battle gate",
            participants=["Commander Lex"],
        )

        relevance = layered_memory._calculate_relevance(memory, query)

        assert 0.0 <= relevance <= 1.0
        assert relevance >= 0.5

    async def test_extract_query_terms(self, layered_memory):
        """Test query term extraction."""
        terms = layered_memory._extract_query_terms(
            "What happened during the battle yesterday?"
        )

        assert len(terms) > 0
        assert all(len(term) > 3 for term in terms)

    async def test_convert_facts_to_memories(self, layered_memory):
        """Test fact-to-memory conversion."""
        facts = ["The sky is blue", "Water is wet", "Fire is hot"]
        term = "science"

        memories = layered_memory._convert_facts_to_memories(facts, term)

        assert len(memories) == 3
        assert all(isinstance(m, MemoryItem) for m in memories)
        assert all(m.memory_type == MemoryType.SEMANTIC for m in memories)

    async def test_generate_insights(self, layered_memory):
        """Test insight generation from memories."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content="Event 1",
            ),
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content="Event 2",
            ),
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.SEMANTIC,
                content="Fact 1",
            ),
        ]

        insights = layered_memory._generate_insights(memories)

        assert len(insights) > 0
        assert any("episodic" in insight.lower() for insight in insights)

    async def test_update_performance_metrics(self, layered_memory):
        """Test performance metrics updating."""
        layered_memory.total_queries = 1
        layered_memory._update_performance_metrics(100.0, 5)

        assert layered_memory.performance_metrics["average_query_time"] > 0

    async def test_cross_layer_associations(self, layered_memory):
        """Test cross-layer association creation."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Event with emotional significance is a fact.",
            emotional_weight=7.0,
        )

        result = await layered_memory.store_memory(memory, cross_layer_linking=True)

        assert result.success is True
        associations = layered_memory._cross_layer_associations
        assert len(associations) >= 0

    async def test_optimize_cross_layer_associations(self, layered_memory):
        """Test cross-layer association optimization."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Test event.",
        )
        await layered_memory.store_memory(memory, cross_layer_linking=True)

        result = await layered_memory._optimize_cross_layer_associations()

        assert result is True

    async def test_multiple_memory_storage(self, layered_memory):
        """Test storing multiple memories."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Event {i}",
            )
            for i in range(5)
        ]

        for memory in memories:
            result = await layered_memory.store_memory(memory)
            assert result.success is True

        assert layered_memory.total_storage_operations == 5

    async def test_memory_query_with_no_results(self, layered_memory):
        """Test query returning no results."""
        query = MemoryQueryRequest(
            query_text="nonexistent content",
            relevance_threshold=0.99,
        )

        result = await layered_memory.query_memories(query)

        assert result.success is True
        query_result = result.data["query_result"]
        assert len(query_result.memories) == 0

    async def test_concurrent_storage_operations(self, layered_memory):
        """Test concurrent memory storage."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.EPISODIC,
                content=f"Concurrent event {i}",
            )
            for i in range(3)
        ]

        results = await asyncio.gather(
            *[layered_memory.store_memory(m) for m in memories]
        )

        assert all(r.success for r in results)
        assert layered_memory.total_storage_operations == 3


class TestMemoryPriority:
    """Unit tests for MemoryPriority enum."""

    @pytest.mark.unit
    def test_memory_priority_values(self):
        """Test MemoryPriority enum values."""
        assert MemoryPriority.CRITICAL.value == "critical"
        assert MemoryPriority.HIGH.value == "high"
        assert MemoryPriority.MEDIUM.value == "medium"
        assert MemoryPriority.LOW.value == "low"
        assert MemoryPriority.ARCHIVED.value == "archived"


class TestMemoryQueryRequest:
    """Unit tests for MemoryQueryRequest dataclass."""

    @pytest.mark.unit
    def test_memory_query_request_defaults(self):
        """Test MemoryQueryRequest default values."""
        query = MemoryQueryRequest(query_text="test query")

        assert query.query_text == "test query"
        assert query.memory_types == []
        assert query.temporal_range is None
        assert query.emotional_filters == {}
        assert query.participants == []
        assert query.relevance_threshold == 0.3
        assert query.max_results == 20
        assert query.include_working_memory is True
        assert query.include_emotional_context is True

    @pytest.mark.unit
    def test_memory_query_request_custom(self):
        """Test MemoryQueryRequest custom values."""
        start_time = datetime.now()
        end_time = datetime.now() + timedelta(hours=1)

        query = MemoryQueryRequest(
            query_text="custom query",
            memory_types=[MemoryType.EPISODIC, MemoryType.SEMANTIC],
            temporal_range=(start_time, end_time),
            emotional_filters={"valence": 0.8},
            participants=["Character A"],
            relevance_threshold=0.7,
            max_results=5,
            include_working_memory=False,
            include_emotional_context=False,
        )

        assert query.max_results == 5
        assert query.relevance_threshold == 0.7
        assert query.include_working_memory is False


class TestMemoryQueryResult:
    """Unit tests for MemoryQueryResult dataclass."""

    @pytest.mark.unit
    def test_memory_query_result_defaults(self):
        """Test MemoryQueryResult default values."""
        result = MemoryQueryResult()

        assert result.memories == []
        assert result.relevance_scores == []
        assert result.memory_sources == []
        assert result.total_found == 0
        assert result.query_duration_ms == 0.0
        assert result.emotional_context == {}
        assert result.working_memory_state == {}
        assert result.consolidated_insights == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


__all__ = [
    "TestLayeredMemorySystem",
    "TestMemoryPriority",
    "TestMemoryQueryRequest",
    "TestMemoryQueryResult",
]
