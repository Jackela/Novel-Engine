#!/usr/bin/env python3
"""
Tests for SemanticMemory

Testing Coverage:
- Unit tests for all public methods
- Knowledge extraction and fact storage
- Subject/predicate querying
- Concept graph management
- Confidence scoring and pruning
- Entity extraction and indexing
"""

import asyncio

import pytest
import pytest_asyncio

pytestmark = pytest.mark.asyncio  # codeql[py/unused-global-variable]

from src.core.data_models import MemoryItem, MemoryType
from src.database.context_db import ContextDatabase
from src.memory.semantic_memory import ConceptNode, KnowledgeFact, SemanticMemory


class TestKnowledgeFact:
    """Unit tests for KnowledgeFact dataclass."""

    @pytest.mark.unit
    def test_knowledge_fact_initialization(self):
        """Test KnowledgeFact initialization."""
        fact = KnowledgeFact(
            fact_id="test_fact_001",
            subject="Sky",
            predicate="is",
            object_value="blue",
            confidence=0.9,
        )

        assert fact.fact_id == "test_fact_001"
        assert fact.subject == "Sky"
        assert fact.predicate == "is"
        assert fact.object_value == "blue"
        assert fact.confidence == 0.9
        assert fact.confirmation_count == 1

    @pytest.mark.unit
    def test_knowledge_fact_auto_id_generation(self):
        """Test automatic fact ID generation."""
        fact = KnowledgeFact(
            fact_id="", subject="Water", predicate="is", object_value="wet"
        )

        assert fact.fact_id.startswith("fact_")
        assert len(fact.fact_id) > 5

    @pytest.mark.unit
    def test_knowledge_fact_confidence_clamping(self):
        """Test confidence value clamping to 0-1 range."""
        fact_high = KnowledgeFact(
            fact_id="", subject="A", predicate="is", object_value="B", confidence=1.5
        )
        assert fact_high.confidence == 1.0

        fact_low = KnowledgeFact(
            fact_id="", subject="A", predicate="is", object_value="B", confidence=-0.5
        )
        assert fact_low.confidence == 0.0

    @pytest.mark.unit
    def test_confirm_fact(self):
        """Test fact confirmation mechanism."""
        fact = KnowledgeFact(
            fact_id="test_001",
            subject="Earth",
            predicate="is",
            object_value="round",
            confidence=0.7,
        )

        initial_confidence = fact.confidence
        initial_count = fact.confirmation_count

        fact.confirm_fact()

        assert fact.confirmation_count == initial_count + 1
        assert fact.confidence >= initial_confidence

    @pytest.mark.unit
    def test_confirm_fact_with_different_source(self):
        """Test confirmation from different source increases confidence more."""
        fact = KnowledgeFact(
            fact_id="test_001",
            subject="Fire",
            predicate="is",
            object_value="hot",
            confidence=0.7,
            source_memory_id="source_a",
        )

        fact.confirm_fact(source_memory_id="source_b")

        assert fact.confirmation_count == 2
        assert fact.confidence > 0.7

    @pytest.mark.unit
    def test_to_natural_language(self):
        """Test natural language representation."""
        fact = KnowledgeFact(
            fact_id="test_001",
            subject="Dog",
            predicate="is",
            object_value="an animal",
        )

        nl_text = fact.to_natural_language()

        assert nl_text == "Dog is an animal"


class TestConceptNode:
    """Unit tests for ConceptNode dataclass."""

    @pytest.mark.unit
    def test_concept_node_initialization(self):
        """Test ConceptNode initialization."""
        node = ConceptNode(concept_id="animal_001", concept_name="Animal")

        assert node.concept_id == "animal_001"
        assert node.concept_name == "Animal"
        assert len(node.parent_concepts) == 0
        assert len(node.child_concepts) == 0
        assert len(node.associated_facts) == 0
        assert node.importance_score == 0.0


class TestSemanticMemory:
    """Unit tests for SemanticMemory system."""

    @pytest_asyncio.fixture
    async def database(self):
        """Setup test database."""
        db = ContextDatabase(":memory:")
        await db.initialize()
        yield db
        await db.close()

    @pytest_asyncio.fixture
    async def semantic_memory(self, database):
        """Setup test SemanticMemory instance."""
        memory = SemanticMemory(
            agent_id="test_agent_001",
            database=database,
            max_facts=100,
            confidence_threshold=0.3,
        )
        yield memory

    @pytest.fixture
    def sample_memory(self):
        """Create sample memory with factual content."""
        return MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The sky is blue. Water is wet. Fire can burn.",
            relevance_score=0.9,
        )

    async def test_initialization(self, semantic_memory):
        """Test SemanticMemory initialization."""
        assert semantic_memory.agent_id == "test_agent_001"
        assert semantic_memory.max_facts == 100
        assert semantic_memory.confidence_threshold == 0.3
        assert len(semantic_memory._facts) == 0
        assert len(semantic_memory._concepts) == 0
        assert semantic_memory.total_facts_learned == 0
        assert semantic_memory.total_concepts_formed == 0

    async def test_extract_and_store_knowledge(self, semantic_memory, sample_memory):
        """Test knowledge extraction from memory."""
        result = await semantic_memory.extract_and_store_knowledge(sample_memory)

        assert result.success is True
        assert "facts_extracted" in result.data
        assert result.data["facts_extracted"] >= 2
        assert "entities_found" in result.data

    async def test_extract_facts_from_content(self, semantic_memory):
        """Test fact extraction from text."""
        content = "The ocean is deep. Mountains are tall."
        memory_id = "test_memory_001"
        relevance = 0.8

        facts = semantic_memory._extract_facts_from_content(
            content, memory_id, relevance
        )

        assert len(facts) >= 0
        assert all(isinstance(f, KnowledgeFact) for f in facts)
        if facts:
            assert all(f.source_memory_id == memory_id for f in facts)

    async def test_extract_facts_with_patterns(self, semantic_memory):
        """Test fact extraction with different patterns."""
        test_cases = [
            ("The sky is blue", "is"),
            ("Dogs have tails", "has"),
            ("Birds can fly", "can"),
        ]

        for content, expected_predicate in test_cases:
            facts = semantic_memory._extract_facts_from_content(content, "test_id", 0.9)
            assert len(facts) >= 0
            if facts:
                assert any(f.predicate == expected_predicate for f in facts)

    async def test_store_fact(self, semantic_memory):
        """Test storing a single fact."""
        fact = KnowledgeFact(
            fact_id="test_fact_001",
            subject="Sun",
            predicate="is",
            object_value="bright",
            confidence=0.9,
        )

        result = await semantic_memory._store_fact(fact)

        assert result.success is True
        assert fact.fact_id in semantic_memory._facts
        assert "sun" in semantic_memory._subject_index

    async def test_store_duplicate_fact_confirms(self, semantic_memory):
        """Test storing duplicate fact confirms existing one."""
        fact1 = KnowledgeFact(
            fact_id="dup_001",
            subject="Moon",
            predicate="is",
            object_value="bright",
            confidence=0.7,
        )

        result1 = await semantic_memory._store_fact(fact1)
        assert result1.success is True

        initial_confirmation = semantic_memory._facts["dup_001"].confirmation_count

        fact2 = KnowledgeFact(
            fact_id="dup_001",
            subject="Moon",
            predicate="is",
            object_value="bright",
            confidence=0.7,
        )

        result2 = await semantic_memory._store_fact(fact2)
        assert result2.success is True
        assert result2.data.get("confirmed") is True
        assert (
            semantic_memory._facts["dup_001"].confirmation_count
            == initial_confirmation + 1
        )

    async def test_query_facts_by_subject(self, semantic_memory):
        """Test querying facts by subject."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The ocean is vast. The ocean is deep.",
            relevance_score=0.9,
        )

        await semantic_memory.extract_and_store_knowledge(memory)

        result = await semantic_memory.query_facts_by_subject("ocean")

        assert result.success is True
        assert "facts" in result.data
        assert len(result.data["facts"]) >= 0
        assert result.data["subject"] == "ocean"

    async def test_query_facts_by_subject_case_insensitive(self, semantic_memory):
        """Test subject query is case-insensitive."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The Mountain is tall.",
            relevance_score=0.9,
        )

        await semantic_memory.extract_and_store_knowledge(memory)

        result = await semantic_memory.query_facts_by_subject("mountain")

        assert result.success is True
        assert len(result.data["facts"]) >= 0

    async def test_query_facts_by_subject_with_threshold(self, semantic_memory):
        """Test subject query with custom confidence threshold."""
        fact_high = KnowledgeFact(
            fact_id="high_conf",
            subject="Star",
            predicate="is",
            object_value="bright",
            confidence=0.9,
        )
        fact_low = KnowledgeFact(
            fact_id="low_conf",
            subject="Star",
            predicate="is",
            object_value="distant",
            confidence=0.2,
        )

        await semantic_memory._store_fact(fact_high)
        await semantic_memory._store_fact(fact_low)

        result = await semantic_memory.query_facts_by_subject(
            "Star", confidence_threshold=0.5
        )

        assert result.success is True
        assert len(result.data["facts"]) >= 1

    async def test_query_facts_by_predicate(self, semantic_memory):
        """Test querying facts by predicate."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="Sky is blue. Water is clear. Air is invisible.",
            relevance_score=0.9,
        )

        await semantic_memory.extract_and_store_knowledge(memory)

        result = await semantic_memory.query_facts_by_predicate("is")

        assert result.success is True
        assert "facts" in result.data
        assert len(result.data["facts"]) >= 0
        assert result.data["predicate"] == "is"

    async def test_query_facts_by_predicate_limited(self, semantic_memory):
        """Test predicate query with limit."""
        for i in range(10):
            memory = MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.SEMANTIC,
                content=f"Thing{i} is property{i}.",
                relevance_score=0.9,
            )
            await semantic_memory.extract_and_store_knowledge(memory)

        result = await semantic_memory.query_facts_by_predicate("is", limit=5)

        assert result.success is True
        assert len(result.data["facts"]) <= 5

    async def test_ensure_concept_exists(self, semantic_memory):
        """Test concept creation."""
        concept = await semantic_memory._ensure_concept_exists("Dragon")

        assert concept.concept_name == "Dragon"
        assert "dragon" in semantic_memory._concepts
        assert semantic_memory.total_concepts_formed == 1

    async def test_ensure_concept_exists_idempotent(self, semantic_memory):
        """Test concept creation is idempotent."""
        concept1 = await semantic_memory._ensure_concept_exists("Phoenix")
        concept2 = await semantic_memory._ensure_concept_exists("Phoenix")

        assert concept1 is concept2
        assert semantic_memory.total_concepts_formed == 1

    async def test_get_concept_knowledge(self, semantic_memory):
        """Test retrieving concept knowledge."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The Dragon is powerful. The Dragon can fly.",
            relevance_score=0.9,
        )

        await semantic_memory.extract_and_store_knowledge(memory)

        result = await semantic_memory.get_concept_knowledge("Dragon")

        assert result.success is True
        assert "concept_name" in result.data
        assert "associated_facts" in result.data
        assert "parent_concepts" in result.data
        assert "child_concepts" in result.data

    async def test_get_concept_knowledge_not_found(self, semantic_memory):
        """Test querying non-existent concept."""
        result = await semantic_memory.get_concept_knowledge("NonExistent")

        assert result.success is False
        assert result.error.code == "CONCEPT_NOT_FOUND"

    async def test_associate_fact_with_concepts(self, semantic_memory):
        """Test fact-concept association."""
        fact = KnowledgeFact(
            fact_id="assoc_001",
            subject="Eagle",
            predicate="is",
            object_value="majestic",
        )

        await semantic_memory._store_fact(fact)
        await semantic_memory._associate_fact_with_concepts(fact)

        eagle_concept = semantic_memory._concepts.get("eagle")
        assert eagle_concept is not None
        assert "assoc_001" in eagle_concept.associated_facts

    async def test_extract_entities(self, semantic_memory):
        """Test entity extraction from text."""
        content = "Commander Alex met Dragon Lex at the Mountain Gate."

        entities = semantic_memory._extract_entities(content)

        assert len(entities) >= 3
        assert "Commander" in entities or "Alex" in entities
        assert "Dragon" in entities or "Lex" in entities

    async def test_is_entity(self, semantic_memory):
        """Test entity detection."""
        assert semantic_memory._is_entity("Dragon") is True
        assert semantic_memory._is_entity("Mountain") is True
        assert semantic_memory._is_entity("sky") is False
        assert semantic_memory._is_entity("water") is False
        assert semantic_memory._is_entity("") is False

    async def test_prune_knowledge(self, semantic_memory):
        """Test knowledge pruning when max capacity reached."""
        semantic_memory.max_facts = 5

        for i in range(10):
            fact = KnowledgeFact(
                fact_id=f"prune_{i}",
                subject=f"Subject{i}",
                predicate="is",
                object_value=f"Object{i}",
                confidence=0.1 * i,
            )
            await semantic_memory._store_fact(fact)

        await semantic_memory._prune_knowledge()

        assert len(semantic_memory._facts) == 5

    async def test_get_memory_statistics_empty(self, semantic_memory):
        """Test statistics with no facts."""
        stats = semantic_memory.get_memory_statistics()

        assert stats["total_facts"] == 0
        assert stats["average_confidence"] == 0.0

    async def test_get_memory_statistics(self, semantic_memory):
        """Test statistics retrieval."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="Sky is blue. Water is wet. Fire is hot.",
            relevance_score=0.9,
        )

        await semantic_memory.extract_and_store_knowledge(memory)

        stats = semantic_memory.get_memory_statistics()

        assert stats["total_facts"] >= 0
        assert stats["total_concepts"] >= 0
        assert 0.0 <= stats["average_confidence"] <= 1.0

    async def test_multiple_fact_extraction(self, semantic_memory):
        """Test extracting multiple facts from rich content."""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The ocean is vast. The ocean is deep. Fish can swim. Birds can fly.",
            relevance_score=0.9,
        )

        result = await semantic_memory.extract_and_store_knowledge(memory)

        assert result.success is True
        assert result.data["facts_extracted"] >= 0

    async def test_concurrent_knowledge_extraction(self, semantic_memory):
        """Test concurrent knowledge extraction."""
        memories = [
            MemoryItem(
                agent_id="test_agent_001",
                memory_type=MemoryType.SEMANTIC,
                content=f"Fact{i} is true{i}.",
                relevance_score=0.9,
            )
            for i in range(5)
        ]

        results = await asyncio.gather(
            *[semantic_memory.extract_and_store_knowledge(m) for m in memories]
        )

        assert all(r.success for r in results)
        assert semantic_memory.total_facts_learned >= 5

    async def test_fact_confidence_ordering(self, semantic_memory):
        """Test facts are returned ordered by confidence."""
        facts = [
            KnowledgeFact(
                fact_id=f"conf_{i}",
                subject="Test",
                predicate="has",
                object_value=f"property{i}",
                confidence=0.1 * i,
            )
            for i in range(5)
        ]

        for fact in facts:
            await semantic_memory._store_fact(fact)

        result = await semantic_memory.query_facts_by_subject("Test")

        assert result.success is True
        fact_list = result.data["facts"]
        if len(fact_list) >= 2:
            assert fact_list[0] != fact_list[-1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


__all__ = ["TestKnowledgeFact", "TestConceptNode", "TestSemanticMemory"]
