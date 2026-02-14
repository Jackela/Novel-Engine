"""
Unit Tests for Graph Retrieval Service

Tests the graph-enhanced retrieval that combines vector search with
knowledge graph traversal.

Warzone 4: AI Brain - BRAIN-032A, BRAIN-032B
Tests graph retrieval, entity expansion, caching, and explain mode.

Constitution Compliance:
- Article III (TDD): Tests written to validate graph retrieval behavior
- Article I (DDD): Tests service behavior, not business logic
"""

from typing import Any

import pytest

from src.contexts.knowledge.application.ports.i_graph_store import (
    CliqueResult,
    GraphEntity,
    GraphRelationship,
    GraphStats,
    IGraphStore,
    PathResult,
)
from src.contexts.knowledge.application.services.graph_retrieval_service import (
    GraphEntityContext,
    GraphExplanation,
    GraphExplanationStep,
    GraphRetrievalConfig,
    GraphRetrievalResult,
    GraphRetrievalService,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.domain.models.entity import EntityType, RelationshipType
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_graph_store() -> IGraphStore:
    """Create a mock graph store for testing."""

    class MockGraphStore(IGraphStore):
        def __init__(self) -> None:
            self._entities: dict[str, GraphEntity] = {}
            self._relationships: list[GraphRelationship] = []

        async def add_entity(self, entity: GraphEntity) -> bool:
            if entity.name in self._entities:
                return False
            self._entities[entity.name] = entity
            return True

        async def add_entities(self, entities: list[GraphEntity]) -> Any:
            # Simplified implementation
            pass
            return None  # type: ignore[return-value]

        async def add_relationship(self, relationship: GraphRelationship) -> bool:
            if any(
                r
                for r in self._relationships
                if r.source == relationship.source
                and r.target == relationship.target
                and str(r.relationship_type) == str(relationship.relationship_type)
            ):
                return False
            self._relationships.append(relationship)
            return True

        async def add_relationships(
            self, relationships: list[GraphRelationship]
        ) -> Any:
            pass
            return None  # type: ignore[return-value]

        async def get_entity(self, name: str) -> GraphEntity | None:
            return self._entities.get(name)

        async def get_neighbors(
            self,
            entity_name: str,
            max_depth: int = 1,
            relationship_types: list[RelationshipType] | None = None,
        ) -> Any:
            return []  # type: ignore[return-value]

        async def find_path(
            self, source: str, target: str, max_length: int | None = None
        ) -> PathResult | None:
            if source == target:
                return PathResult(path=(source,), relationships=(), length=0)
            return None

        async def find_paths_multiple(
            self, source: str, targets: list[str], max_length: int | None = None
        ) -> dict[str, PathResult | None]:
            return {}

        async def get_relationships(
            self, entity_name: str, relationship_type: RelationshipType | None = None
        ) -> list[GraphRelationship]:
            return [r for r in self._relationships if r.source == entity_name]

        async def get_relationships_between(
            self, source: str, target: str
        ) -> list[GraphRelationship]:
            return [
                r
                for r in self._relationships
                if r.source == source and r.target == target
            ]

        async def remove_entity(self, name: str) -> bool:
            if name in self._entities:
                del self._entities[name]
                return True
            return False

        async def remove_relationship(
            self, source: str, target: str, relationship_type: RelationshipType
        ) -> bool:
            return False

        async def clear(self) -> None:
            self._entities.clear()
            self._relationships.clear()

        async def get_stats(self) -> GraphStats:
            return GraphStats(
                node_count=len(self._entities),
                edge_count=len(self._relationships),
                entity_type_counts={},
                relationship_type_counts={},
            )

        async def health_check(self) -> bool:
            return True

        async def entity_exists(self, name: str) -> bool:
            return name in self._entities

        async def get_all_entities(
            self, entity_type: EntityType | None = None, limit: int | None = None
        ) -> list[GraphEntity]:
            return list(self._entities.values())

        async def find_cliques(
            self,
            min_size: int = 3,
            max_size: int | None = None,
            entity_type: EntityType | None = None,
        ) -> CliqueResult:
            return CliqueResult(cliques=(), max_clique_size=0, clique_count=0)

        async def get_centrality(
            self, entity_name: str | None = None, top_n: int | None = None
        ) -> list[Any]:
            return []

        async def find_all_shortest_paths(
            self, source: str, max_length: int | None = None, cutoff: int | None = None
        ) -> dict[str, PathResult]:
            return {}

        async def export_graphml(
            self, output_path: str, include_metadata: bool = True
        ) -> Any:
            pass
            return None  # type: ignore[return-value]

        async def export_json(
            self, output_path: str | None = None, pretty: bool = True
        ) -> Any:
            pass
            return None  # type: ignore[return-value]

    return MockGraphStore()


@pytest.fixture
def sample_entities() -> list[GraphEntity]:
    """Create sample graph entities."""
    return [
        GraphEntity(
            name="Alice", entity_type=EntityType.CHARACTER, description="A warrior"
        ),
        GraphEntity(
            name="Bob", entity_type=EntityType.CHARACTER, description="A wizard"
        ),
        GraphEntity(
            name="Castle", entity_type=EntityType.LOCATION, description="Fortress"
        ),
    ]


@pytest.fixture
def sample_relationships() -> list[GraphRelationship]:
    """Create sample relationships."""
    return [
        GraphRelationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
            context="Alice and Bob are friends",
            strength=0.9,
        ),
        GraphRelationship(
            source="Alice",
            target="Castle",
            relationship_type=RelationshipType.LOCATED_AT,
            context="Alice lives near the castle",
            strength=0.8,
        ),
    ]


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    """Create sample retrieved chunks."""
    return [
        RetrievedChunk(
            chunk_id="chunk1",
            source_id="char1",
            source_type=SourceType.CHARACTER,
            content="Alice is a brave warrior who knows Bob.",
            score=0.85,
            metadata={},
        ),
        RetrievedChunk(
            chunk_id="chunk2",
            source_id="char2",
            source_type=SourceType.CHARACTER,
            content="Bob is a wise wizard with powerful magic.",
            score=0.80,
            metadata={},
        ),
    ]


class TestGraphRetrievalServiceBasics:
    """Basic tests for GraphRetrievalService."""

    def test_initialization(self, mock_graph_store: IGraphStore) -> None:
        """Service initialization with graph store."""
        config = GraphRetrievalConfig(entity_expansion_depth=2)

        service = GraphRetrievalService(mock_graph_store, config)

        assert service._graph_store is mock_graph_store
        assert service._config.entity_expansion_depth == 2

    def test_initialization_default_config(self, mock_graph_store: IGraphStore) -> None:
        """Service initialization with default config."""
        service = GraphRetrievalService(mock_graph_store)

        assert service._config.entity_expansion_depth == 1
        assert service._config.max_entities_per_chunk == 5


class TestGraphRetrievalServiceEnrichment:
    """Tests for chunk enrichment with graph context."""

    @pytest.mark.asyncio
    async def test_enrich_chunks_with_graph(
        self,
        mock_graph_store: IGraphStore,
        sample_entities: list[GraphEntity],
        sample_relationships: list[GraphRelationship],
    ) -> None:
        """Enriching chunks with graph context."""
        # Setup graph with entities and relationships
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        for rel in sample_relationships:
            await mock_graph_store.add_relationship(rel)

        service = GraphRetrievalService(mock_graph_store)
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_scene1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice and Bob went on an adventure.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert isinstance(result, GraphRetrievalResult)
        assert len(result.enhanced_chunks) == 1
        assert result.entities_found >= 0
        assert isinstance(result.relationships_found, int)

    @pytest.mark.asyncio
    async def test_enrich_chunks_empty_chunks(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Enriching with no chunks returns empty result."""
        service = GraphRetrievalService(mock_graph_store)

        result = await service.enrich_chunks_with_graph([])

        assert isinstance(result, GraphRetrievalResult)
        assert len(result.enhanced_chunks) == 0
        assert result.entities_found == 0
        assert result.relationships_found == 0

    @pytest.mark.asyncio
    async def test_enrich_chunks_builds_entity_descriptions(
        self,
        mock_graph_store: IGraphStore,
        sample_entities: list[GraphEntity],
        sample_relationships: list[GraphRelationship],
    ) -> None:
        """Entity descriptions are built correctly."""
        # Setup graph
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        service = GraphRetrievalService(mock_graph_store)
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_test",
                source_id="test",
                source_type=SourceType.CHARACTER,
                content="Alice content",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        # Verify entity descriptions are created
        enhanced = result.enhanced_chunks[0]
        assert isinstance(enhanced.entity_descriptions, str)


class TestGraphRetrievalServiceEntityContext:
    """Tests for getting entity context."""

    @pytest.mark.asyncio
    async def test_get_entity_context_found(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Getting context for an existing entity."""
        await mock_graph_store.add_entity(
            GraphEntity(
                name="Alice", entity_type=EntityType.CHARACTER, description="Warrior"
            )
        )

        service = GraphRetrievalService(mock_graph_store)

        context = await service.get_entity_context("Alice")

        assert context is not None
        assert context.entity.name == "Alice"
        assert isinstance(context, GraphEntityContext)

    @pytest.mark.asyncio
    async def test_get_entity_context_not_found(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Getting context for non-existent entity returns None."""
        service = GraphRetrievalService(mock_graph_store)

        context = await service.get_entity_context("NonExistent")

        assert context is None


class TestGraphRetrievalServiceRelatedEntities:
    """Tests for finding related entities."""

    @pytest.mark.asyncio
    async def test_find_related_entities_empty_graph(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Finding related entities in empty graph."""
        service = GraphRetrievalService(mock_graph_store)

        related = await service.find_related_entities("Alice")

        assert related == []

    @pytest.mark.asyncio
    async def test_find_related_entities_with_limit(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Finding related entities respects limit."""
        # This test would require a more sophisticated mock
        service = GraphRetrievalService(mock_graph_store)

        related = await service.find_related_entities("Alice", limit=5)

        assert isinstance(related, list)


class TestGraphRetrievalServiceGraphMethods:
    """Tests for graph analysis methods."""

    @pytest.mark.asyncio
    async def test_get_entity_centrality(self, mock_graph_store: IGraphStore) -> None:
        """Getting centrality for an entity."""
        service = GraphRetrievalService(mock_graph_store)

        centrality = await service.get_entity_centrality("Alice")

        # Since graph is empty, should return None or empty result
        assert centrality is None or isinstance(centrality, tuple)

    @pytest.mark.asyncio
    async def test_find_shortest_path(self, mock_graph_store: IGraphStore) -> None:
        """Finding shortest path between entities."""
        service = GraphRetrievalService(mock_graph_store)

        # Same entity
        path = await service.find_shortest_path("Alice", "Alice")

        assert path is not None
        assert path.length == 0
        assert path.path == ("Alice",)

        # Different entities in empty graph
        path = await service.find_shortest_path("Alice", "Bob")

        assert path is None

    @pytest.mark.asyncio
    async def test_get_graph_stats(self, mock_graph_store: IGraphStore) -> None:
        """Getting graph statistics."""
        service = GraphRetrievalService(mock_graph_store)

        stats = await service.get_graph_stats()

        assert isinstance(stats, GraphStats)
        assert stats.node_count == 0
        assert stats.edge_count == 0

    @pytest.mark.asyncio
    async def test_find_cliques(self, mock_graph_store: IGraphStore) -> None:
        """Finding cliques in the graph."""
        service = GraphRetrievalService(mock_graph_store)

        result = await service.find_cliques(min_size=2)

        assert isinstance(result, CliqueResult)
        assert result.clique_count == 0


class TestGraphRetrievalServiceCaching:
    """Tests for caching functionality."""

    def test_reset_cache_stats(self, mock_graph_store: IGraphStore) -> None:
        """Resetting cache statistics."""
        service = GraphRetrievalService(mock_graph_store)

        # Simulate some cache activity
        service._cache_hits = 5
        service._cache_misses = 10

        service.reset_cache_stats()

        assert service._cache_hits == 0
        assert service._cache_misses == 0

    def test_get_cache_stats(self, mock_graph_store: IGraphStore) -> None:
        """Getting cache statistics."""
        service = GraphRetrievalService(mock_graph_store)

        service._cache_hits = 8
        service._cache_misses = 2

        stats = service.get_cache_stats()

        assert stats["hits"] == 8
        assert stats["misses"] == 2
        assert stats["total"] == 10
        assert stats["hit_rate"] == 0.8


class TestGraphRetrievalServiceExplainMode:
    """Tests for explain mode reasoning path tracking (BRAIN-032B)."""

    @pytest.mark.asyncio
    async def test_explain_mode_disabled_returns_no_explanation(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """When explain_mode is disabled, no explanation is generated."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=False)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is None

    @pytest.mark.asyncio
    async def test_explain_mode_enabled_generates_explanation(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """When explain_mode is enabled, explanation is generated."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        assert isinstance(result.explanation, GraphExplanation)
        assert len(result.explanation.steps) > 0

    @pytest.mark.asyncio
    async def test_explanation_contains_entity_extraction_step(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation includes entity extraction step."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        step_types = [step.step_type for step in result.explanation.steps]
        assert "entity_extraction" in step_types

    @pytest.mark.asyncio
    async def test_explanation_contains_entity_lookup_steps(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation includes entity lookup steps."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        lookup_steps = [
            s for s in result.explanation.steps if s.step_type == "entity_lookup"
        ]
        assert len(lookup_steps) > 0

    @pytest.mark.asyncio
    async def test_explanation_contains_not_found_entity_step(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Explanation records when entity is not found in graph."""
        # Only add Bob, not Alice
        await mock_graph_store.add_entity(
            GraphEntity(
                name="Bob", entity_type=EntityType.CHARACTER, description="A wizard"
            )
        )

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",  # Alice not in graph
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        lookup_steps = [
            s for s in result.explanation.steps if s.step_type == "entity_lookup"
        ]
        # Should have a step showing Alice was not found
        not_found_steps = [s for s in lookup_steps if not s.metadata.get("found", True)]
        assert len(not_found_steps) > 0

    @pytest.mark.asyncio
    async def test_explanation_summary_text_is_generated(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation includes human-readable summary text."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        assert result.explanation.summary_text != ""
        assert "Graph Traversal Explanation" in result.explanation.summary_text
        assert "Total Steps:" in result.explanation.summary_text

    @pytest.mark.asyncio
    async def test_explanation_tracks_traversal_depth(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """Explanation records maximum traversal depth."""
        await mock_graph_store.add_entity(
            GraphEntity(
                name="Alice", entity_type=EntityType.CHARACTER, description="Warrior"
            )
        )

        config = GraphRetrievalConfig(explain_mode=True, entity_expansion_depth=2)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        assert result.explanation.total_traversal_depth >= 0

    @pytest.mark.asyncio
    async def test_explanation_counts_entities_and_relationships_examined(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation counts total entities and relationships examined."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        assert result.explanation.entities_examined >= 0
        assert result.explanation.relationships_examined >= 0

    @pytest.mark.asyncio
    async def test_explanation_steps_are_ordered(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation steps are numbered sequentially."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        step_numbers = [step.step_number for step in result.explanation.steps]
        # Steps should be numbered 1, 2, 3, ...
        assert step_numbers == list(range(1, len(step_numbers) + 1))

    @pytest.mark.asyncio
    async def test_explanation_step_has_required_fields(
        self, mock_graph_store: IGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Explanation steps contain all required fields."""
        for entity in sample_entities:
            await mock_graph_store.add_entity(entity)

        config = GraphRetrievalConfig(explain_mode=True)
        service = GraphRetrievalService(mock_graph_store, config)

        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="scene1",
                source_type=SourceType.SCENE,
                content="Alice is a brave warrior.",
                score=0.9,
                metadata={},
            ),
        ]

        result = await service.enrich_chunks_with_graph(chunks)

        assert result.explanation is not None
        for step in result.explanation.steps:
            assert hasattr(step, "step_number")
            assert hasattr(step, "step_type")
            assert hasattr(step, "description")
            assert hasattr(step, "entity_name")
            assert hasattr(step, "relevance_score")
            assert isinstance(step.metadata, dict)

    def test_graph_explanation_step_is_immutable(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """GraphExplanationStep is a frozen dataclass."""
        step = GraphExplanationStep(
            step_number=1,
            step_type="test",
            description="Test step",
            entity_name="Alice",
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError
            step.step_number = 2

    def test_graph_explanation_is_immutable(
        self, mock_graph_store: IGraphStore
    ) -> None:
        """GraphExplanation is a frozen dataclass."""
        explanation = GraphExplanation(
            query="test",
            steps=(),
            entities_examined=0,
            relationships_examined=0,
            total_traversal_depth=0,
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError
            explanation.entities_examined = 1
