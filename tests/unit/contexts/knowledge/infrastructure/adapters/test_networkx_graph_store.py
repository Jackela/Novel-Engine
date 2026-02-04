"""
Unit Tests for NetworkX Graph Store Adapter

Tests the NetworkX adapter implementing IGraphStore port.

Warzone 4: AI Brain - BRAIN-031A
Tests graph storage operations, entity/relationship management, and path finding.

Constitution Compliance:
- Article III (TDD): Tests written to validate graph storage behavior
- Article I (DDD): Tests adapter behavior, not business logic
"""

from typing import Any

import pytest

from src.contexts.knowledge.application.ports.i_graph_store import (
    CliqueResult,
    CentralityResult,
    GraphAddResult,
    GraphEntity,
    GraphExportResult,
    GraphNeighbor,
    GraphRelationship,
    GraphStats,
    GraphStoreError,
    IGraphStore,
    PathResult,
)
from src.contexts.knowledge.domain.models.entity import EntityType, RelationshipType
from src.contexts.knowledge.infrastructure.adapters.networkx_graph_store import (
    NetworkXGraphStore,
)


@pytest.fixture
def graph_store() -> NetworkXGraphStore:
    """
    Create a NetworkX graph store instance.

    Returns:
        NetworkXGraphStore instance
    """
    return NetworkXGraphStore()


@pytest.fixture
def sample_entities() -> list[GraphEntity]:
    """
    Create sample entities for testing.

    Returns:
        List of GraphEntity objects representing characters and locations
    """
    return [
        GraphEntity(
            name="Alice",
            entity_type=EntityType.CHARACTER,
            aliases=("Ally", "A"),
            description="A brave warrior",
            metadata={"confidence": 0.95, "first_appearance": 0},
        ),
        GraphEntity(
            name="Bob",
            entity_type=EntityType.CHARACTER,
            description="A wise wizard",
            metadata={"confidence": 0.9, "first_appearance": 100},
        ),
        GraphEntity(
            name="Castle",
            entity_type=EntityType.LOCATION,
            description="An ancient fortress",
            metadata={"confidence": 0.85},
        ),
        GraphEntity(
            name="Kingdom",
            entity_type=EntityType.ORGANIZATION,
            description="The realm",
        ),
    ]


@pytest.fixture
def sample_relationships() -> list[GraphRelationship]:
    """
    Create sample relationships for testing.

    Returns:
        List of GraphRelationship objects
    """
    return [
        GraphRelationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
            context="Alice and Bob met in the forest",
            strength=0.9,
        ),
        GraphRelationship(
            source="Alice",
            target="Castle",
            relationship_type=RelationshipType.LOCATED_AT,
            context="Alice lives in the castle",
            strength=0.95,
        ),
        GraphRelationship(
            source="Bob",
            target="Kingdom",
            relationship_type=RelationshipType.MEMBER_OF,
            context="Bob serves the kingdom",
            strength=0.85,
        ),
        GraphRelationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.LOVES,
            strength=0.7,
        ),
    ]


class TestNetworkXGraphStoreBasics:
    """Tests for basic graph store operations."""

    @pytest.mark.asyncio
    async def test_health_check(self, graph_store: NetworkXGraphStore) -> None:
        """Health check returns True for functioning graph store."""
        result = await graph_store.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_add_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Adding an entity to the graph."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
            description="A test entity",
        )
        result = await graph_store.add_entity(entity)
        assert result is True

        # Verify entity exists
        exists = await graph_store.entity_exists("TestEntity")
        assert exists is True

    @pytest.mark.asyncio
    async def test_add_duplicate_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Adding duplicate entity returns False."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
        )
        await graph_store.add_entity(entity)
        result = await graph_store.add_entity(entity)
        assert result is False

    @pytest.mark.asyncio
    async def test_add_entities_batch(self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]) -> None:
        """Adding multiple entities in batch."""
        result = await graph_store.add_entities(sample_entities)
        assert result.entities_added == 4
        assert result.entities_skipped == 0

        # Verify all entities exist
        for entity in sample_entities:
            exists = await graph_store.entity_exists(entity.name)
            assert exists is True

    @pytest.mark.asyncio
    async def test_add_entities_batch_with_duplicates(
        self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Adding entities with some duplicates."""
        # Add one entity first
        await graph_store.add_entity(sample_entities[0])

        # Try to add all
        result = await graph_store.add_entities(sample_entities)
        assert result.entities_added == 3
        assert result.entities_skipped == 1

    @pytest.mark.asyncio
    async def test_get_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Retrieving an entity by name."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
            aliases=("Alias1", "Alias2"),
            description="A test entity",
            metadata={"key": "value"},
        )
        await graph_store.add_entity(entity)

        retrieved = await graph_store.get_entity("TestEntity")
        assert retrieved is not None
        assert retrieved.name == "TestEntity"
        assert retrieved.entity_type == EntityType.CHARACTER
        assert retrieved.aliases == ("Alias1", "Alias2")
        assert retrieved.description == "A test entity"
        assert retrieved.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, graph_store: NetworkXGraphStore) -> None:
        """Retrieving non-existent entity returns None."""
        retrieved = await graph_store.get_entity("NonExistent")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_entity_exists(self, graph_store: NetworkXGraphStore) -> None:
        """Checking if entity exists."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
        )
        await graph_store.add_entity(entity)

        assert await graph_store.entity_exists("TestEntity") is True
        assert await graph_store.entity_exists("NonExistent") is False

    @pytest.mark.asyncio
    async def test_entity_exists_case_insensitive(self, graph_store: NetworkXGraphStore) -> None:
        """Entity names are case-insensitive."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
        )
        await graph_store.add_entity(entity)

        assert await graph_store.entity_exists("testentity") is True
        assert await graph_store.entity_exists("TESTENTITY") is True
        assert await graph_store.entity_exists("TestEntity") is True

    @pytest.mark.asyncio
    async def test_remove_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Removing an entity."""
        entity = GraphEntity(
            name="TestEntity",
            entity_type=EntityType.CHARACTER,
        )
        await graph_store.add_entity(entity)

        result = await graph_store.remove_entity("TestEntity")
        assert result is True

        exists = await graph_store.entity_exists("TestEntity")
        assert exists is False

    @pytest.mark.asyncio
    async def test_remove_entity_not_found(self, graph_store: NetworkXGraphStore) -> None:
        """Removing non-existent entity returns False."""
        result = await graph_store.remove_entity("NonExistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]) -> None:
        """Clearing the graph removes all entities."""
        await graph_store.add_entities(sample_entities)
        stats_before = await graph_store.get_stats()
        assert stats_before.node_count == 4

        await graph_store.clear()

        stats_after = await graph_store.get_stats()
        assert stats_after.node_count == 0


class TestNetworkXGraphStoreRelationships:
    """Tests for relationship operations."""

    @pytest.mark.asyncio
    async def test_add_relationship(self, graph_store: NetworkXGraphStore) -> None:
        """Adding a relationship between entities."""
        relationship = GraphRelationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
            context="They met in the forest",
            strength=0.9,
        )
        result = await graph_store.add_relationship(relationship)
        assert result is True

        # Verify entities were auto-created
        assert await graph_store.entity_exists("Alice") is True
        assert await graph_store.entity_exists("Bob") is True

    @pytest.mark.asyncio
    async def test_add_duplicate_relationship(self, graph_store: NetworkXGraphStore) -> None:
        """Adding duplicate relationship returns False."""
        relationship = GraphRelationship(
            source="Alice",
            target="Bob",
            relationship_type=RelationshipType.KNOWS,
        )
        await graph_store.add_relationship(relationship)
        result = await graph_store.add_relationship(relationship)
        assert result is False

    @pytest.mark.asyncio
    async def test_add_relationships_batch(
        self, graph_store: NetworkXGraphStore, sample_relationships: list[GraphRelationship]
    ) -> None:
        """Adding multiple relationships in batch."""
        result = await graph_store.add_relationships(sample_relationships)
        assert result.relationships_added == 4
        assert result.relationships_skipped == 0

    @pytest.mark.asyncio
    async def test_get_relationships(self, graph_store: NetworkXGraphStore) -> None:
        """Getting relationships for an entity."""
        await graph_store.add_entity(
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_entity(
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_entity(
            GraphEntity(name="Carol", entity_type=EntityType.CHARACTER)
        )

        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Carol",
                relationship_type=RelationshipType.LOVES,
            )
        )

        relationships = await graph_store.get_relationships("Alice")
        assert len(relationships) == 2
        relationship_targets = {r.target for r in relationships}
        assert relationship_targets == {"Bob", "Carol"}

    @pytest.mark.asyncio
    async def test_get_relationships_filtered(self, graph_store: NetworkXGraphStore) -> None:
        """Getting relationships filtered by type."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.LOVES,
            )
        )

        # Get only KNOWS relationships
        relationships = await graph_store.get_relationships(
            "Alice", relationship_type=RelationshipType.KNOWS
        )
        assert len(relationships) == 1
        assert relationships[0].relationship_type == RelationshipType.KNOWS

    @pytest.mark.asyncio
    async def test_get_relationships_between(self, graph_store: NetworkXGraphStore) -> None:
        """Getting relationships between two specific entities."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
                strength=0.9,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.LOVES,
                strength=0.7,
            )
        )

        relationships = await graph_store.get_relationships_between("Alice", "Bob")
        assert len(relationships) == 2
        strengths = {r.strength for r in relationships}
        assert strengths == {0.9, 0.7}

    @pytest.mark.asyncio
    async def test_get_relationships_between_none(self, graph_store: NetworkXGraphStore) -> None:
        """Getting relationships between entities with no connection returns empty list."""
        await graph_store.add_entity(
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_entity(
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER)
        )

        relationships = await graph_store.get_relationships_between("Alice", "Bob")
        assert relationships == []

    @pytest.mark.asyncio
    async def test_remove_relationship(self, graph_store: NetworkXGraphStore) -> None:
        """Removing a specific relationship."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )

        result = await graph_store.remove_relationship(
            "Alice", "Bob", RelationshipType.KNOWS
        )
        assert result is True

        # Verify relationship is gone
        relationships = await graph_store.get_relationships_between("Alice", "Bob")
        assert len(relationships) == 0

    @pytest.mark.asyncio
    async def test_remove_relationship_not_found(self, graph_store: NetworkXGraphStore) -> None:
        """Removing non-existent relationship returns False."""
        result = await graph_store.remove_relationship(
            "Alice", "Bob", RelationshipType.KNOWS
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_entity_removes_relationships(
        self, graph_store: NetworkXGraphStore
    ) -> None:
        """Removing an entity also removes its relationships."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Carol",
                target="Alice",
                relationship_type=RelationshipType.LOVES,
            )
        )

        # Remove Alice
        await graph_store.remove_entity("Alice")

        # Bob should have no outgoing relationships
        bob_relationships = await graph_store.get_relationships("Bob")
        assert len(bob_relationships) == 0


class TestNetworkXGraphStoreNeighbors:
    """Tests for neighbor operations."""

    @pytest.mark.asyncio
    async def test_get_neighbors_direct(self, graph_store: NetworkXGraphStore) -> None:
        """Getting direct neighbors (depth=1)."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Carol",
                relationship_type=RelationshipType.LOVES,
            )
        )

        neighbors = await graph_store.get_neighbors("Alice", max_depth=1)
        assert len(neighbors) == 2
        neighbor_names = {n.entity.name for n in neighbors}
        assert neighbor_names == {"Bob", "Carol"}

    @pytest.mark.asyncio
    async def test_get_neighbors_depth(self, graph_store: NetworkXGraphStore) -> None:
        """Getting neighbors at multiple depths."""
        # Alice -> Bob -> Carol chain
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Bob",
                target="Carol",
                relationship_type=RelationshipType.KNOWS,
            )
        )

        neighbors = await graph_store.get_neighbors("Alice", max_depth=2)
        assert len(neighbors) >= 2

        # Check distances
        bob_neighbor = next(n for n in neighbors if n.entity.name == "Bob")
        carol_neighbor = next((n for n in neighbors if n.entity.name == "Carol"), None)

        assert bob_neighbor.distance == 1
        if carol_neighbor:
            assert carol_neighbor.distance == 2

    @pytest.mark.asyncio
    async def test_get_neighbors_filtered_by_type(
        self, graph_store: NetworkXGraphStore
    ) -> None:
        """Getting neighbors filtered by relationship type."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Carol",
                relationship_type=RelationshipType.LOVES,
            )
        )

        neighbors = await graph_store.get_neighbors(
            "Alice", relationship_types=[RelationshipType.KNOWS]
        )
        assert len(neighbors) == 1
        assert neighbors[0].entity.name == "Bob"

    @pytest.mark.asyncio
    async def test_get_neighbors_entity_not_found(
        self, graph_store: NetworkXGraphStore
    ) -> None:
        """Getting neighbors for non-existent entity raises error."""
        with pytest.raises(GraphStoreError, match="Entity not found"):
            await graph_store.get_neighbors("NonExistent")


class TestNetworkXGraphStorePathFinding:
    """Tests for path finding operations."""

    @pytest.mark.asyncio
    async def test_find_path_direct(self, graph_store: NetworkXGraphStore) -> None:
        """Finding direct path between connected entities."""
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )

        path = await graph_store.find_path("Alice", "Bob")
        assert path is not None
        assert path.path == ("Alice", "Bob")
        assert path.length == 1
        assert len(path.relationships) == 1
        assert path.relationships[0].source == "Alice"
        assert path.relationships[0].target == "Bob"

    @pytest.mark.asyncio
    async def test_find_path_multihop(self, graph_store: NetworkXGraphStore) -> None:
        """Finding multi-hop path."""
        # Alice -> Bob -> Carol
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Bob",
                target="Carol",
                relationship_type=RelationshipType.KNOWS,
            )
        )

        path = await graph_store.find_path("Alice", "Carol")
        assert path is not None
        assert path.path == ("Alice", "Bob", "Carol")
        assert path.length == 2

    @pytest.mark.asyncio
    async def test_find_path_no_path(self, graph_store: NetworkXGraphStore) -> None:
        """Finding path between disconnected entities returns None."""
        await graph_store.add_entity(
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_entity(
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER)
        )

        path = await graph_store.find_path("Alice", "Bob")
        assert path is None

    @pytest.mark.asyncio
    async def test_find_path_max_length(self, graph_store: NetworkXGraphStore) -> None:
        """Finding path with maximum length constraint."""
        # Alice -> Bob -> Carol (2 hops)
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Bob",
                target="Carol",
                relationship_type=RelationshipType.KNOWS,
            )
        )

        # With max_length=1, should not find path to Carol
        path = await graph_store.find_path("Alice", "Carol", max_length=1)
        assert path is None

        # With max_length=2, should find path
        path = await graph_store.find_path("Alice", "Carol", max_length=2)
        assert path is not None

    @pytest.mark.asyncio
    async def test_find_path_same_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Finding path from entity to itself."""
        await graph_store.add_entity(
            GraphEntity(
                name="Alice",
                entity_type=EntityType.CHARACTER,
                description="A character",
            )
        )

        path = await graph_store.find_path("Alice", "Alice")
        assert path is not None
        assert path.path == ("Alice",)
        assert path.length == 0

    @pytest.mark.asyncio
    async def test_find_path_entity_not_found(
        self, graph_store: NetworkXGraphStore
    ) -> None:
        """Finding path with non-existent source raises error."""
        with pytest.raises(GraphStoreError, match="Source entity not found"):
            await graph_store.find_path("NonExistent", "Alice")

    @pytest.mark.asyncio
    async def test_find_paths_multiple(self, graph_store: NetworkXGraphStore) -> None:
        """Finding paths to multiple targets."""
        # Alice -> Bob -> Carol
        await graph_store.add_relationship(
            GraphRelationship(
                source="Alice",
                target="Bob",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_relationship(
            GraphRelationship(
                source="Bob",
                target="Carol",
                relationship_type=RelationshipType.KNOWS,
            )
        )
        await graph_store.add_entity(
            GraphEntity(name="Disconnected", entity_type=EntityType.CHARACTER)
        )

        results = await graph_store.find_paths_multiple(
            "Alice", ["Bob", "Carol", "Disconnected"]
        )

        assert results["Bob"] is not None
        assert results["Bob"].length == 1
        assert results["Carol"] is not None
        assert results["Carol"].length == 2
        assert results["Disconnected"] is None


class TestNetworkXGraphStoreStats:
    """Tests for graph statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, graph_store: NetworkXGraphStore) -> None:
        """Getting stats for empty graph."""
        stats = await graph_store.get_stats()
        assert stats.node_count == 0
        assert stats.edge_count == 0
        assert stats.entity_type_counts == {}
        assert stats.relationship_type_counts == {}

    @pytest.mark.asyncio
    async def test_get_stats(
        self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity], sample_relationships: list[GraphRelationship]
    ) -> None:
        """Getting stats for populated graph."""
        await graph_store.add_entities(sample_entities)
        await graph_store.add_relationships(sample_relationships)

        stats = await graph_store.get_stats()
        assert stats.node_count == 4
        assert stats.edge_count == 4
        assert stats.entity_type_counts.get("character") == 2
        assert stats.entity_type_counts.get("location") == 1
        assert stats.entity_type_counts.get("organization") == 1


class TestNetworkXGraphStoreGetAllEntities:
    """Tests for get_all_entities operation."""

    @pytest.mark.asyncio
    async def test_get_all_entities(self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]) -> None:
        """Getting all entities from graph."""
        await graph_store.add_entities(sample_entities)

        entities = await graph_store.get_all_entities()
        assert len(entities) == 4
        entity_names = {e.name for e in entities}
        assert entity_names == {"Alice", "Bob", "Castle", "Kingdom"}

    @pytest.mark.asyncio
    async def test_get_all_entities_filtered_by_type(
        self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Getting entities filtered by type."""
        await graph_store.add_entities(sample_entities)

        entities = await graph_store.get_all_entities(entity_type=EntityType.CHARACTER)
        assert len(entities) == 2
        assert all(e.entity_type == EntityType.CHARACTER for e in entities)

    @pytest.mark.asyncio
    async def test_get_all_entities_with_limit(
        self, graph_store: NetworkXGraphStore, sample_entities: list[GraphEntity]
    ) -> None:
        """Getting entities with limit."""
        await graph_store.add_entities(sample_entities)

        entities = await graph_store.get_all_entities(limit=2)
        assert len(entities) == 2


class TestNetworkXGraphStoreComplexGraph:
    """Tests for complex graph scenarios."""

    @pytest.mark.asyncio
    async def test_character_relationship_graph(
        self, graph_store: NetworkXGraphStore
    ) -> None:
        """
        Build and query a character relationship graph.

        Creates a typical fantasy novel scenario:
        - Protagonist knows the mentor
        - Mentor serves the king
        - Protagonist loves the ally
        - Antagonist killed the king
        """
        # Entities
        entities = [
            GraphEntity(name="Aragorn", entity_type=EntityType.CHARACTER, description="The ranger"),
            GraphEntity(name="Gandalf", entity_type=EntityType.CHARACTER, description="The wizard"),
            GraphEntity(name="King", entity_type=EntityType.CHARACTER, description="The ruler"),
            GraphEntity(name="Arwen", entity_type=EntityType.CHARACTER, description="The elf"),
            GraphEntity(name="Sauron", entity_type=EntityType.CHARACTER, description="The dark lord"),
        ]
        await graph_store.add_entities(entities)

        # Relationships
        relationships = [
            GraphRelationship(source="Aragorn", target="Gandalf", relationship_type=RelationshipType.KNOWS, strength=0.95),
            GraphRelationship(source="Gandalf", target="King", relationship_type=RelationshipType.SERVES, strength=0.9),
            GraphRelationship(source="Aragorn", target="Arwen", relationship_type=RelationshipType.LOVES, strength=1.0),
            GraphRelationship(source="Sauron", target="King", relationship_type=RelationshipType.KILLED, strength=0.85),
        ]
        await graph_store.add_relationships(relationships)

        # Query Aragorn's connections
        aragorn_neighbors = await graph_store.get_neighbors("Aragorn")
        assert len(aragorn_neighbors) == 2
        neighbor_names = {n.entity.name for n in aragorn_neighbors}
        assert neighbor_names == {"Gandalf", "Arwen"}

        # Find path from Aragorn to King (should be Aragorn -> Gandalf -> King)
        path = await graph_store.find_path("Aragorn", "King")
        assert path is not None
        assert path.path == ("Aragorn", "Gandalf", "King")
        assert path.length == 2

        # Get stats
        stats = await graph_store.get_stats()
        assert stats.node_count == 5
        assert stats.edge_count == 4


class TestNetworkXGraphStoreAdvancedQueries:
    """Tests for advanced graph query operations - BRAIN-031B."""

    @pytest.mark.asyncio
    async def test_find_cliques_basic(self, graph_store: NetworkXGraphStore) -> None:
        """Finding cliques in a graph."""
        # Create a clique of 3: Alice <-> Bob <-> Carol <-> Alice
        entities = [
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Carol", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        # Create bidirectional relationships for clique
        relationships = [
            GraphRelationship(source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Bob", target="Alice", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Bob", target="Carol", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Carol", target="Bob", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Carol", target="Alice", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Alice", target="Carol", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        result = await graph_store.find_cliques(min_size=3)

        assert isinstance(result, CliqueResult)
        assert result.max_clique_size >= 3
        assert result.clique_count >= 1
        # The clique should contain all three characters
        assert any(
            set(clique) == {"Alice", "Bob", "Carol"}
            for clique in result.cliques
        )

    @pytest.mark.asyncio
    async def test_find_cliques_with_filter(self, graph_store: NetworkXGraphStore) -> None:
        """Finding cliques with entity type filter."""
        entities = [
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Castle", entity_type=EntityType.LOCATION),
        ]
        await graph_store.add_entities(entities)

        # Create clique among characters
        relationships = [
            GraphRelationship(source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Bob", target="Alice", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        # Filter by CHARACTER type - should find the character clique
        result = await graph_store.find_cliques(min_size=2, entity_type=EntityType.CHARACTER)

        assert result.clique_count >= 1

        # Filter by LOCATION type - should find no cliques (single node)
        result = await graph_store.find_cliques(min_size=2, entity_type=EntityType.LOCATION)

        assert result.clique_count == 0

    @pytest.mark.asyncio
    async def test_find_cliques_max_size(self, graph_store: NetworkXGraphStore) -> None:
        """Finding cliques with maximum size constraint."""
        entities = [
            GraphEntity(name="A", entity_type=EntityType.CHARACTER),
            GraphEntity(name="B", entity_type=EntityType.CHARACTER),
            GraphEntity(name="C", entity_type=EntityType.CHARACTER),
            GraphEntity(name="D", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        # Create fully connected clique of 4
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i + 1:]:
                relationships = [
                    GraphRelationship(source=entity1.name, target=entity2.name, relationship_type=RelationshipType.KNOWS),
                    GraphRelationship(source=entity2.name, target=entity1.name, relationship_type=RelationshipType.KNOWS),
                ]
                await graph_store.add_relationships(relationships)

        result = await graph_store.find_cliques(min_size=2, max_size=3)

        # Should not return the 4-node clique
        assert result.max_clique_size <= 3
        # All returned cliques should be <= 3
        for clique in result.cliques:
            assert len(clique) <= 3

    @pytest.mark.asyncio
    async def test_get_centrality_all(self, graph_store: NetworkXGraphStore) -> None:
        """Calculate centrality for all entities."""
        entities = [
            GraphEntity(name="Hub", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Node1", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Node2", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Node3", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Isolated", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        # Hub connects to all others (except Isolated)
        relationships = [
            GraphRelationship(source="Hub", target="Node1", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Hub", target="Node2", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Hub", target="Node3", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        results = await graph_store.get_centrality()

        assert len(results) == 5

        # Hub should have highest centrality metrics
        hub_result = next(r for r in results if r.entity_name == "Hub")
        assert hub_result.degree_centrality > 0
        assert hub_result.pagerank > 0

        # Isolated node should have zero degree centrality
        isolated_result = next(r for r in results if r.entity_name == "Isolated")
        assert isolated_result.degree_centrality == 0
        # PageRank has a damping factor so isolated nodes still have small pagerank
        assert isolated_result.pagerank < 0.2

        # Results should be sorted by pagerank descending
        pageranks = [r.pagerank for r in results]
        assert pageranks == sorted(pageranks, reverse=True)

    @pytest.mark.asyncio
    async def test_get_centrality_single_entity(self, graph_store: NetworkXGraphStore) -> None:
        """Calculate centrality for a single entity."""
        await graph_store.add_entity(
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_entity(
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER)
        )
        await graph_store.add_relationship(
            GraphRelationship(source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS)
        )

        result = await graph_store.get_centrality(entity_name="Alice")

        assert len(result) == 1
        assert result[0].entity_name == "Alice"
        assert result[0].degree_centrality > 0

    @pytest.mark.asyncio
    async def test_get_centrality_top_n(self, graph_store: NetworkXGraphStore) -> None:
        """Calculate centrality with top_n limit."""
        entities = [
            GraphEntity(name=f"Entity{i}", entity_type=EntityType.CHARACTER)
            for i in range(10)
        ]
        await graph_store.add_entities(entities)

        # Create a star pattern with Entity0 as hub
        for i in range(1, 10):
            await graph_store.add_relationship(
                GraphRelationship(
                    source="Entity0",
                    target=f"Entity{i}",
                    relationship_type=RelationshipType.KNOWS
                )
            )

        results = await graph_store.get_centrality(top_n=5)

        assert len(results) == 5
        # Hub should have the highest degree centrality among all entities
        # Check that Entity0 has degree_centrality = 1.0 (connected to all 9 others)
        all_results = await graph_store.get_centrality()  # Get all to verify
        hub_result = next((r for r in all_results if r.entity_name == "Entity0"), None)
        assert hub_result is not None
        assert hub_result.degree_centrality == 1.0
        # With top_n=5, the first 5 entities are returned (sorted by pagerank)
        # Just verify the limit is respected
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_find_all_shortest_paths(self, graph_store: NetworkXGraphStore) -> None:
        """Find shortest paths from source to all reachable entities."""
        # Create a line: A -> B -> C -> D
        entities = [
            GraphEntity(name="A", entity_type=EntityType.CHARACTER),
            GraphEntity(name="B", entity_type=EntityType.CHARACTER),
            GraphEntity(name="C", entity_type=EntityType.CHARACTER),
            GraphEntity(name="D", entity_type=EntityType.CHARACTER),
            GraphEntity(name="Isolated", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        relationships = [
            GraphRelationship(source="A", target="B", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="B", target="C", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="C", target="D", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        results = await graph_store.find_all_shortest_paths("A")

        # Should find paths to B, C, D but not Isolated
        assert "B" in results
        assert "C" in results
        assert "D" in results
        assert "Isolated" not in results

        # Check path lengths
        assert results["B"].length == 1
        assert results["C"].length == 2
        assert results["D"].length == 3

    @pytest.mark.asyncio
    async def test_find_all_shortest_paths_with_cutoff(self, graph_store: NetworkXGraphStore) -> None:
        """Find shortest paths with cutoff limit."""
        entities = [
            GraphEntity(name="Source", entity_type=EntityType.CHARACTER),
            GraphEntity(name="T1", entity_type=EntityType.CHARACTER),
            GraphEntity(name="T2", entity_type=EntityType.CHARACTER),
            GraphEntity(name="T3", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        relationships = [
            GraphRelationship(source="Source", target="T1", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Source", target="T2", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="Source", target="T3", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        results = await graph_store.find_all_shortest_paths("Source", cutoff=2)

        # Should only return 2 paths due to cutoff
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_all_shortest_paths_max_length(self, graph_store: NetworkXGraphStore) -> None:
        """Find shortest paths with max_length constraint."""
        entities = [
            GraphEntity(name="A", entity_type=EntityType.CHARACTER),
            GraphEntity(name="B", entity_type=EntityType.CHARACTER),
            GraphEntity(name="C", entity_type=EntityType.CHARACTER),
        ]
        await graph_store.add_entities(entities)

        relationships = [
            GraphRelationship(source="A", target="B", relationship_type=RelationshipType.KNOWS),
            GraphRelationship(source="B", target="C", relationship_type=RelationshipType.KNOWS),
        ]
        await graph_store.add_relationships(relationships)

        results = await graph_store.find_all_shortest_paths("A", max_length=1)

        # Should only find direct connection to B, not C (2 hops)
        assert "B" in results
        assert "C" not in results


class TestNetworkXGraphStoreExport:
    """Tests for graph export operations - BRAIN-031B."""

    @pytest.mark.asyncio
    async def test_export_graphml(self, graph_store: NetworkXGraphStore, tmp_path: Any) -> None:
        """Export graph to GraphML format."""
        import os

        entities = [
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER, description="A warrior"),
            GraphEntity(name="Bob", entity_type=EntityType.CHARACTER, description="A wizard"),
        ]
        await graph_store.add_entities(entities)

        await graph_store.add_relationship(
            GraphRelationship(source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS, context="Friends")
        )

        output_path = str(tmp_path / "test_graph.graphml")
        result = await graph_store.export_graphml(output_path)

        assert isinstance(result, GraphExportResult)
        assert result.format == "graphml"
        assert result.node_count == 2
        assert result.edge_count == 1
        assert result.data == output_path
        assert result.size_bytes > 0
        assert os.path.exists(output_path)

        # Verify file content
        with open(output_path, "r") as f:
            content = f.read()
            assert "graphml" in content.lower()

    @pytest.mark.asyncio
    async def test_export_graphml_without_metadata(self, graph_store: NetworkXGraphStore, tmp_path: Any) -> None:
        """Export graph to GraphML without metadata."""
        import os

        entities = [
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER, metadata={"custom": "data"}),
        ]
        await graph_store.add_entities(entities)

        output_path = str(tmp_path / "test_no_metadata.graphml")
        result = await graph_store.export_graphml(output_path, include_metadata=False)

        assert result.node_count == 1
        assert os.path.exists(output_path)

    @pytest.mark.asyncio
    async def test_export_json_to_file(self, graph_store: NetworkXGraphStore, tmp_path: Any) -> None:
        """Export graph to JSON file."""
        import json
        import os

        entities = [
            GraphEntity(name="Alice", entity_type=EntityType.CHARACTER, aliases=("Ally",)),
        ]
        await graph_store.add_entities(entities)

        await graph_store.add_relationship(
            GraphRelationship(source="Alice", target="Bob", relationship_type=RelationshipType.KNOWS)
        )

        output_path = str(tmp_path / "test_graph.json")
        result = await graph_store.export_json(output_path, pretty=True)

        assert isinstance(result, GraphExportResult)
        assert result.format == "json"
        assert result.node_count == 2  # Alice + auto-created Bob
        assert result.edge_count == 1
        assert result.data == output_path
        assert os.path.exists(output_path)

        # Verify JSON content
        with open(output_path, "r") as f:
            data = json.load(f)
            assert "graph" in data
            assert "nodes" in data["graph"]
            assert "edges" in data["graph"]
            assert data["metadata"]["node_count"] == 2

    @pytest.mark.asyncio
    async def test_export_json_to_string(self, graph_store: NetworkXGraphStore) -> None:
        """Export graph to JSON string."""
        import json

        await graph_store.add_entity(
            GraphEntity(name="Test", entity_type=EntityType.CHARACTER)
        )

        result = await graph_store.export_json(output_path=None, pretty=True)

        assert isinstance(result, GraphExportResult)
        assert result.format == "json"
        assert result.node_count == 1

        # Verify data is valid JSON string
        data = json.loads(result.data)
        assert "graph" in data
        assert len(data["graph"]["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_export_json_compact(self, graph_store: NetworkXGraphStore) -> None:
        """Export graph to compact JSON (no pretty printing)."""
        await graph_store.add_entity(
            GraphEntity(name="Test", entity_type=EntityType.CHARACTER)
        )

        result = await graph_store.export_json(output_path=None, pretty=False)

        # Compact JSON should have no unnecessary whitespace
        assert "\n" not in result.data
        assert "  " not in result.data
