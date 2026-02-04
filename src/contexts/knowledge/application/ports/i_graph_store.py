"""
IGraphStore Port Interface

Hexagonal architecture port defining the contract for graph storage operations.
This port enables knowledge graph operations using NetworkX.

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
- Article IV (SSOT): NetworkX/Neo4j as authoritative graph storage

Warzone 4: AI Brain - BRAIN-031A
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.contexts.knowledge.domain.models.entity import EntityType, RelationshipType


@dataclass(frozen=True, slots=True)
class GraphEntity:
    """
    An entity (node) in the knowledge graph.

    Why frozen:
        Immutable snapshot ensures graph entities cannot be modified
        after creation, preventing cache inconsistency.

    Attributes:
        name: Unique identifier/name for this entity
        entity_type: Type of entity (CHARACTER, LOCATION, etc.)
        aliases: Alternative names for this entity
        description: Text description of the entity
        metadata: Additional attributes (confidence, first_appearance, etc.)
    """

    name: str
    entity_type: EntityType
    aliases: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entity data."""
        if not self.name or not self.name.strip():
            raise ValueError("Entity name must not be empty")


@dataclass(frozen=True, slots=True)
class GraphRelationship:
    """
    A relationship (edge) between two entities in the knowledge graph.

    Why frozen:
        Immutable snapshot ensures relationships cannot be modified
        after creation.

    Attributes:
        source: Source entity name
        target: Target entity name
        relationship_type: Type of relationship
        context: Text providing context for this relationship
        strength: Confidence score 0.0-1.0
        metadata: Additional attributes (bidirectional, temporal_marker, etc.)
    """

    source: str
    target: str
    relationship_type: RelationshipType
    context: str = ""
    strength: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate relationship data."""
        if not self.source or not self.source.strip():
            raise ValueError("Source entity name must not be empty")
        if not self.target or not self.target.strip():
            raise ValueError("Target entity name must not be empty")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class GraphNeighbor:
    """
    A neighboring entity connected via a relationship.

    Attributes:
        entity: The neighboring entity
        relationship: The relationship connecting to this neighbor
        distance: Number of hops from the original entity
    """

    entity: GraphEntity
    relationship: GraphRelationship
    distance: int


@dataclass(frozen=True, slots=True)
class PathResult:
    """
    Result of a path finding operation.

    Attributes:
        path: List of entity names forming the path
        relationships: Relationships along the path
        length: Number of edges in the path
    """

    path: tuple[str, ...]
    relationships: tuple[GraphRelationship, ...]
    length: int


@dataclass(frozen=True)
class GraphStats:
    """
    Statistics about the graph.

    Attributes:
        node_count: Total number of entities/nodes
        edge_count: Total number of relationships/edges
        entity_type_counts: Count of entities by type
        relationship_type_counts: Count of relationships by type
    """

    node_count: int
    edge_count: int
    entity_type_counts: dict[str, int]
    relationship_type_counts: dict[str, int]


@dataclass(frozen=True)
class GraphAddResult:
    """
    Result of adding entities/relationships to the graph.

    Attributes:
        entities_added: Number of entities added
        relationships_added: Number of relationships added
        entities_skipped: Number of entities skipped (already existed)
        relationships_skipped: Number of relationships skipped (already existed)
    """

    entities_added: int
    relationships_added: int
    entities_skipped: int
    relationships_skipped: int


class IGraphStore(ABC):
    """
    Port for graph storage operations.

    This interface defines the contract for storing and querying
    knowledge graphs, enabling entity and relationship operations.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides NetworkX/Neo4j adapter implementation
    - Application use cases depend ONLY on this abstraction

    Methods:
        add_entity: Add an entity (node) to the graph
        add_relationship: Add a relationship (edge) between entities
        get_entity: Retrieve an entity by name
        get_neighbors: Get all entities connected to an entity
        find_path: Find shortest path between two entities
        find_path_multiple: Find paths between multiple entity pairs
        get_relationships: Get all relationships for an entity
        get_relationships_between: Get relationships between two specific entities
        clear: Remove all data from the graph
        get_stats: Get graph statistics

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
    async def add_entity(self, entity: GraphEntity) -> bool:
        """
        Add an entity (node) to the graph.

        Args:
            entity: GraphEntity to add

        Returns:
            True if entity was added, False if it already existed

        Raises:
            GraphStoreError: If add operation fails

        Why async:
            Graph operations can be slow with large graphs.
            Async prevents blocking the event loop.
        """

    @abstractmethod
    async def add_entities(self, entities: list[GraphEntity]) -> GraphAddResult:
        """
        Add multiple entities to the graph in batch.

        Args:
            entities: List of GraphEntity objects to add

        Returns:
            GraphAddResult with counts of added/skipped entities

        Raises:
            GraphStoreError: If batch add operation fails
        """

    @abstractmethod
    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """
        Add a relationship (edge) between two entities.

        If either entity doesn't exist, they will be created automatically.

        Args:
            relationship: GraphRelationship to add

        Returns:
            True if relationship was added, False if it already existed

        Raises:
            GraphStoreError: If add operation fails
        """

    @abstractmethod
    async def add_relationships(self, relationships: list[GraphRelationship]) -> GraphAddResult:
        """
        Add multiple relationships to the graph in batch.

        Args:
            relationships: List of GraphRelationship objects to add

        Returns:
            GraphAddResult with counts of added/skipped relationships

        Raises:
            GraphStoreError: If batch add operation fails
        """

    @abstractmethod
    async def get_entity(self, name: str) -> GraphEntity | None:
        """
        Retrieve an entity by name.

        Args:
            name: Entity name to look up

        Returns:
            GraphEntity if found, None otherwise

        Raises:
            GraphStoreError: If get operation fails
        """

    @abstractmethod
    async def get_neighbors(
        self,
        entity_name: str,
        max_depth: int = 1,
        relationship_types: list[RelationshipType] | None = None,
    ) -> list[GraphNeighbor]:
        """
        Get all entities connected to the given entity.

        Args:
            entity_name: Name of the entity to find neighbors for
            max_depth: Maximum number of hops to explore (default: 1)
            relationship_types: Optional filter for specific relationship types

        Returns:
            List of GraphNeighbor objects sorted by distance

        Raises:
            GraphStoreError: If entity not found or operation fails
        """

    @abstractmethod
    async def find_path(
        self,
        source: str,
        target: str,
        max_length: int | None = None,
    ) -> PathResult | None:
        """
        Find shortest path between two entities.

        Args:
            source: Source entity name
            target: Target entity name
            max_length: Maximum path length to search (default: unlimited)

        Returns:
            PathResult if path found, None otherwise

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def find_paths_multiple(
        self,
        source: str,
        targets: list[str],
        max_length: int | None = None,
    ) -> dict[str, PathResult | None]:
        """
        Find shortest paths from source to multiple targets.

        Args:
            source: Source entity name
            targets: List of target entity names
            max_length: Maximum path length to search (default: unlimited)

        Returns:
            Dict mapping target name to PathResult (or None if no path)

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def get_relationships(
        self,
        entity_name: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[GraphRelationship]:
        """
        Get all relationships for an entity.

        Args:
            entity_name: Name of the entity
            relationship_type: Optional filter for specific relationship type

        Returns:
            List of GraphRelationship objects

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def get_relationships_between(
        self,
        source: str,
        target: str,
    ) -> list[GraphRelationship]:
        """
        Get all relationships between two specific entities.

        Args:
            source: Source entity name
            target: Target entity name

        Returns:
            List of GraphRelationship objects (may be empty)

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def remove_entity(self, name: str) -> bool:
        """
        Remove an entity and all its relationships from the graph.

        Args:
            name: Entity name to remove

        Returns:
            True if entity was removed, False if not found

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def remove_relationship(
        self,
        source: str,
        target: str,
        relationship_type: RelationshipType,
    ) -> bool:
        """
        Remove a specific relationship from the graph.

        Args:
            source: Source entity name
            target: Target entity name
            relationship_type: Type of relationship to remove

        Returns:
            True if relationship was removed, False if not found

        Raises:
            GraphStoreError: If operation fails
        """

    @abstractmethod
    async def clear(self) -> None:
        """
        Remove all entities and relationships from the graph.

        Raises:
            GraphStoreError: If clear operation fails
        """

    @abstractmethod
    async def get_stats(self) -> GraphStats:
        """
        Get statistics about the graph.

        Returns:
            GraphStats with node/edge counts and type breakdowns

        Raises:
            GraphStoreError: If stats operation fails
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify the graph store connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """

    @abstractmethod
    async def entity_exists(self, name: str) -> bool:
        """
        Check if an entity exists in the graph.

        Args:
            name: Entity name to check

        Returns:
            True if entity exists, False otherwise
        """

    @abstractmethod
    async def get_all_entities(
        self,
        entity_type: EntityType | None = None,
        limit: int | None = None,
    ) -> list[GraphEntity]:
        """
        Get all entities from the graph.

        Args:
            entity_type: Optional filter for specific entity type
            limit: Optional maximum number of entities to return

        Returns:
            List of GraphEntity objects

        Raises:
            GraphStoreError: If operation fails
        """


class GraphStoreError(Exception):
    """Base exception for graph store operations."""

    def __init__(
        self,
        message: str,
        code: str = "GRAPH_STORE_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


__all__ = [
    "IGraphStore",
    "GraphEntity",
    "GraphRelationship",
    "GraphNeighbor",
    "PathResult",
    "GraphStats",
    "GraphAddResult",
    "GraphStoreError",
]
