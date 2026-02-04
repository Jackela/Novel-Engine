"""
NetworkX Graph Store Adapter

Implements IGraphStore port using NetworkX for in-memory graph storage.
Supports entity and relationship operations for knowledge graph management.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implements IGraphStore port
- Article I (DDD): No business logic, only graph storage operations
- Article IV (SSOT): NetworkX as authoritative graph storage

Warzone 4: AI Brain - BRAIN-031A
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import networkx as nx

from src.contexts.knowledge.application.ports.i_graph_store import (
    GraphAddResult,
    GraphEntity,
    GraphNeighbor,
    GraphRelationship,
    GraphStats,
    GraphStoreError,
    IGraphStore,
    PathResult,
)
from src.contexts.knowledge.domain.models.entity import EntityType, RelationshipType

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class NetworkXGraphStore(IGraphStore):
    """
    NetworkX-based graph storage adapter for knowledge graphs.

    Why NetworkX:
        - Pure Python, no external database dependencies
        - Rich graph algorithms (shortest path, centrality, cliques)
        - Efficient in-memory operations for moderate-sized graphs
        - Easy to test and debug

    Implementation Notes:
        - Uses MultiDiGraph for directed multi-graph (parallel edges supported)
        - Entity names are case-insensitive for lookups
        - Node attributes store entity data
        - Edge attributes store relationship data
    """

    def __init__(self) -> None:
        """
        Initialize the NetworkX graph store.

        Creates an empty MultiDiGraph for storing entities and relationships.
        """
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()

    def _normalize_name(self, name: str) -> str:
        """
        Normalize entity name for consistent storage.

        Args:
            name: Entity name to normalize

        Returns:
            Normalized (lowercase, stripped) name
        """
        return name.lower().strip()

    @staticmethod
    def _entity_type_to_str(entity_type: EntityType | str) -> str:
        """Convert EntityType to string for storage."""
        if isinstance(entity_type, str):
            return entity_type
        return entity_type.value  # type: ignore[unreachable]

    @staticmethod
    def _str_to_entity_type(value: str) -> EntityType:
        """Convert string to EntityType enum."""
        try:
            return EntityType(value)
        except ValueError:
            return EntityType.CHARACTER  # Default fallback

    @staticmethod
    def _relationship_type_to_str(relationship_type: RelationshipType | str) -> str:
        """Convert RelationshipType to string for storage."""
        if isinstance(relationship_type, str):
            return relationship_type
        return relationship_type.value  # type: ignore[unreachable]

    @staticmethod
    def _str_to_relationship_type(value: str) -> RelationshipType:
        """Convert string to RelationshipType enum."""
        try:
            return RelationshipType(value)
        except ValueError:
            return RelationshipType.OTHER  # Default fallback

    async def add_entity(self, entity: GraphEntity) -> bool:
        """
        Add an entity (node) to the graph.

        Args:
            entity: GraphEntity to add

        Returns:
            True if entity was added, False if it already existed
        """
        normalized_name = self._normalize_name(entity.name)

        if self._graph.has_node(normalized_name):
            logger.debug(f"Entity already exists: {entity.name}")
            return False

        try:
            self._graph.add_node(
                normalized_name,
                name=entity.name,
                entity_type=self._entity_type_to_str(entity.entity_type),
                aliases=list(entity.aliases),
                description=entity.description,
                **entity.metadata,
            )
            logger.debug(f"Added entity: {entity.name} ({entity.entity_type})")
            return True
        except Exception as e:
            raise GraphStoreError(
                f"Failed to add entity {entity.name}",
                code="ADD_ENTITY_FAILED",
                details={"error": str(e), "entity": entity.name},
            ) from e

    async def add_entities(self, entities: list[GraphEntity]) -> GraphAddResult:
        """
        Add multiple entities to the graph in batch.

        Args:
            entities: List of GraphEntity objects to add

        Returns:
            GraphAddResult with counts of added/skipped entities
        """
        entities_added = 0
        entities_skipped = 0

        for entity in entities:
            if await self.add_entity(entity):
                entities_added += 1
            else:
                entities_skipped += 1

        return GraphAddResult(
            entities_added=entities_added,
            relationships_added=0,
            entities_skipped=entities_skipped,
            relationships_skipped=0,
        )

    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """
        Add a relationship (edge) between two entities.

        If either entity doesn't exist, they will be created automatically
        as placeholder entities with minimal data.

        Args:
            relationship: GraphRelationship to add

        Returns:
            True if relationship was added, False if it already existed
        """
        source_norm = self._normalize_name(relationship.source)
        target_norm = self._normalize_name(relationship.target)

        # Auto-create placeholder entities if they don't exist
        if not self._graph.has_node(source_norm):
            self._graph.add_node(source_norm, name=relationship.source, entity_type="unknown")
        if not self._graph.has_node(target_norm):
            self._graph.add_node(target_norm, name=relationship.target, entity_type="unknown")

        # Check if this exact relationship already exists
        rel_type_str = self._relationship_type_to_str(relationship.relationship_type)
        edge_key = (source_norm, target_norm, rel_type_str)
        if self._graph.has_edge(*edge_key[:2], key=edge_key[2]):
            logger.debug(f"Relationship already exists: {relationship.source} -> {relationship.target} ({relationship.relationship_type})")
            return False

        try:
            self._graph.add_edge(
                source_norm,
                target_norm,
                key=rel_type_str,
                relationship_type=rel_type_str,
                source=relationship.source,
                target=relationship.target,
                context=relationship.context,
                strength=relationship.strength,
                **relationship.metadata,
            )
            logger.debug(f"Added relationship: {relationship.source} -> {relationship.target} ({relationship.relationship_type})")
            return True
        except Exception as e:
            raise GraphStoreError(
                f"Failed to add relationship {relationship.source} -> {relationship.target}",
                code="ADD_RELATIONSHIP_FAILED",
                details={
                    "error": str(e),
                    "source": relationship.source,
                    "target": relationship.target,
                    "type": str(relationship.relationship_type),
                },
            ) from e

    async def add_relationships(self, relationships: list[GraphRelationship]) -> GraphAddResult:
        """
        Add multiple relationships to the graph in batch.

        Args:
            relationships: List of GraphRelationship objects to add

        Returns:
            GraphAddResult with counts of added/skipped relationships
        """
        relationships_added = 0
        relationships_skipped = 0

        for relationship in relationships:
            if await self.add_relationship(relationship):
                relationships_added += 1
            else:
                relationships_skipped += 1

        return GraphAddResult(
            entities_added=0,
            relationships_added=relationships_added,
            entities_skipped=0,
            relationships_skipped=relationships_skipped,
        )

    async def get_entity(self, name: str) -> GraphEntity | None:
        """
        Retrieve an entity by name.

        Args:
            name: Entity name to look up

        Returns:
            GraphEntity if found, None otherwise
        """
        normalized_name = self._normalize_name(name)

        if not self._graph.has_node(normalized_name):
            return None

        try:
            node_data = self._graph.nodes[normalized_name]
            entity_type_str = node_data.get("entity_type", "unknown")
            entity_type = self._str_to_entity_type(entity_type_str)

            return GraphEntity(
                name=node_data.get("name", name),
                entity_type=entity_type,
                aliases=tuple(node_data.get("aliases", [])),
                description=node_data.get("description", ""),
                metadata={k: v for k, v in node_data.items()
                         if k not in {"name", "entity_type", "aliases", "description"}},
            )
        except Exception as e:
            raise GraphStoreError(
                f"Failed to get entity {name}",
                code="GET_ENTITY_FAILED",
                details={"error": str(e), "entity": name},
            ) from e

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
        """
        normalized_name = self._normalize_name(entity_name)

        if not self._graph.has_node(normalized_name):
            raise GraphStoreError(
                f"Entity not found: {entity_name}",
                code="ENTITY_NOT_FOUND",
                details={"entity": entity_name},
            )

        neighbors: list[GraphNeighbor] = []
        visited: set[str] = set([normalized_name])

        # Filter for specific relationship types if provided
        rel_type_filter: set[str] | None = (
            {self._relationship_type_to_str(rt) for rt in relationship_types} if relationship_types else None
        )

        # BFS to find neighbors at each depth
        # Queue stores: (node_name, distance, incoming_edge_data)
        from collections import deque
        queue: deque[tuple[str, int, dict[str, Any] | None]] = deque([(normalized_name, 0, None)])

        while queue:
            current_node, distance, incoming_edge = queue.popleft()

            if distance >= max_depth:
                continue

            # Get all outgoing edges from current node
            if not self._graph.has_node(current_node):
                continue

            for _, target, key, edge_data in self._graph.out_edges(current_node, keys=True, data=True):
                if target in visited:
                    continue

                # Filter by relationship type if specified
                if rel_type_filter and key not in rel_type_filter:
                    continue

                # Get neighbor entity data
                node_data = self._graph.nodes[target]
                entity_type_str = node_data.get("entity_type", "unknown")
                entity = GraphEntity(
                    name=node_data.get("name", target),
                    entity_type=self._str_to_entity_type(entity_type_str),
                    aliases=tuple(node_data.get("aliases", [])),
                    description=node_data.get("description", ""),
                )

                # Build relationship object from the edge data
                rel_type_str = edge_data.get("relationship_type", "other")
                relationship = GraphRelationship(
                    source=edge_data.get("source", entity_name if distance == 0 else ""),
                    target=edge_data.get("target", entity.name),
                    relationship_type=self._str_to_relationship_type(rel_type_str),
                    context=edge_data.get("context", ""),
                    strength=edge_data.get("strength", 1.0),
                    metadata={k: v for k, v in edge_data.items()
                             if k not in {"source", "target", "relationship_type", "context", "strength"}},
                )

                neighbors.append(
                    GraphNeighbor(
                        entity=entity,
                        relationship=relationship,
                        distance=distance + 1,
                    )
                )

                visited.add(target)
                queue.append((target, distance + 1, edge_data))

        # Sort by distance, then by strength (descending)
        neighbors.sort(key=lambda n: (n.distance, -n.relationship.strength))
        return neighbors

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
        """
        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target)

        if not self._graph.has_node(source_norm):
            raise GraphStoreError(
                f"Source entity not found: {source}",
                code="ENTITY_NOT_FOUND",
                details={"entity": source},
            )

        if not self._graph.has_node(target_norm):
            raise GraphStoreError(
                f"Target entity not found: {target}",
                code="ENTITY_NOT_FOUND",
                details={"entity": target},
            )

        try:
            if source_norm == target_norm:
                # Same entity - trivial path
                entity = await self.get_entity(source)
                if entity:
                    return PathResult(
                        path=(entity.name,),
                        relationships=(),
                        length=0,
                    )
                return None

            # Use bidirectional Dijkstra for efficiency
            path_nodes: list[str] | None = None

            if max_length is None:
                try:
                    path_nodes = nx.bidirectional_shortest_path(self._graph, source_norm, target_norm)
                except nx.NetworkXNoPath:
                    return None
            else:
                # BFS with depth limit
                try:
                    path_nodes = nx.bidirectional_shortest_path(
                        self._graph, source_norm, target_norm
                    )
                    if path_nodes and len(path_nodes) - 1 > max_length:
                        return None
                except nx.NetworkXNoPath:
                    return None

            if not path_nodes or len(path_nodes) < 2:
                return None

            # Build relationships along the path
            relationships: list[GraphRelationship] = []
            for i in range(len(path_nodes) - 1):
                from_node = path_nodes[i]
                to_node = path_nodes[i + 1]

                edge_data = None
                if self._graph.has_edge(from_node, to_node):
                    edges = self._graph.get_edge_data(from_node, to_node)
                    if edges:
                        edge_data = next(iter(edges.values()))

                if edge_data is None:
                    # Should not happen if path is valid
                    continue

                from_entity = self._graph.nodes[from_node]
                to_entity = self._graph.nodes[to_node]

                rel_type_str = edge_data.get("relationship_type", "other")
                relationships.append(
                    GraphRelationship(
                        source=edge_data.get("source", from_entity.get("name", from_node)),
                        target=edge_data.get("target", to_entity.get("name", to_node)),
                        relationship_type=self._str_to_relationship_type(rel_type_str),
                        context=edge_data.get("context", ""),
                        strength=edge_data.get("strength", 1.0),
                    )
                )

            # Convert normalized names back to display names
            display_names = []
            for node in path_nodes:
                node_data = self._graph.nodes[node]
                display_names.append(node_data.get("name", node))

            return PathResult(
                path=tuple(display_names),
                relationships=tuple(relationships),
                length=len(relationships),
            )

        except GraphStoreError:
            raise
        except Exception as e:
            raise GraphStoreError(
                f"Failed to find path from {source} to {target}",
                code="FIND_PATH_FAILED",
                details={"error": str(e), "source": source, "target": target},
            ) from e

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
        """
        results: dict[str, PathResult | None] = {}

        for target in targets:
            try:
                path_result = await self.find_path(source, target, max_length)
                results[target] = path_result
            except GraphStoreError:
                results[target] = None

        return results

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
        """
        normalized_name = self._normalize_name(entity_name)

        if not self._graph.has_node(normalized_name):
            return []

        relationships: list[GraphRelationship] = []
        rel_type_filter = self._relationship_type_to_str(relationship_type) if relationship_type else None

        # Get outgoing edges
        if self._graph.has_node(normalized_name):
            for _, target, key, edge_data in self._graph.out_edges(
                normalized_name, keys=True, data=True
            ):
                if relationship_type is None or key == rel_type_filter:
                    target_data = self._graph.nodes[target]
                    rel_type_str = edge_data.get("relationship_type", "other")
                    relationships.append(
                        GraphRelationship(
                            source=edge_data.get("source", entity_name),
                            target=edge_data.get("target", target_data.get("name", target)),
                            relationship_type=self._str_to_relationship_type(rel_type_str),
                            context=edge_data.get("context", ""),
                            strength=edge_data.get("strength", 1.0),
                            metadata={k: v for k, v in edge_data.items()
                                     if k not in {"source", "target", "relationship_type", "context", "strength"}},
                        )
                    )

        return relationships

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
        """
        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target)

        if not self._graph.has_edge(source_norm, target_norm):
            return []

        relationships: list[GraphRelationship] = []
        edges = self._graph.get_edge_data(source_norm, target_norm)

        if edges is None:
            return []

        for edge_data in edges.values():
            rel_type_str = edge_data.get("relationship_type", "other")
            relationships.append(
                GraphRelationship(
                    source=edge_data.get("source", source),
                    target=edge_data.get("target", target),
                    relationship_type=self._str_to_relationship_type(rel_type_str),
                    context=edge_data.get("context", ""),
                    strength=edge_data.get("strength", 1.0),
                    metadata={k: v for k, v in edge_data.items()
                             if k not in {"source", "target", "relationship_type", "context", "strength"}},
                )
            )

        return relationships

    async def remove_entity(self, name: str) -> bool:
        """
        Remove an entity and all its relationships from the graph.

        Args:
            name: Entity name to remove

        Returns:
            True if entity was removed, False if not found
        """
        normalized_name = self._normalize_name(name)

        if not self._graph.has_node(normalized_name):
            return False

        try:
            self._graph.remove_node(normalized_name)
            logger.debug(f"Removed entity: {name}")
            return True
        except Exception as e:
            raise GraphStoreError(
                f"Failed to remove entity {name}",
                code="REMOVE_ENTITY_FAILED",
                details={"error": str(e), "entity": name},
            ) from e

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
        """
        source_norm = self._normalize_name(source)
        target_norm = self._normalize_name(target)
        rel_type_str = self._relationship_type_to_str(relationship_type)

        if not self._graph.has_edge(source_norm, target_norm, key=rel_type_str):
            return False

        try:
            self._graph.remove_edge(source_norm, target_norm, key=rel_type_str)
            logger.debug(f"Removed relationship: {source} -> {target} ({relationship_type})")
            return True
        except Exception as e:
            raise GraphStoreError(
                f"Failed to remove relationship {source} -> {target} ({relationship_type})",
                code="REMOVE_RELATIONSHIP_FAILED",
                details={
                    "error": str(e),
                    "source": source,
                    "target": target,
                    "type": rel_type_str,
                },
            ) from e

    async def clear(self) -> None:
        """
        Remove all entities and relationships from the graph.
        """
        self._graph.clear()
        logger.debug("Cleared graph")

    async def get_stats(self) -> GraphStats:
        """
        Get statistics about the graph.

        Returns:
            GraphStats with node/edge counts and type breakdowns
        """
        entity_type_counts: dict[str, int] = {}
        relationship_type_counts: dict[str, int] = {}

        # Count entities by type
        for node, node_data in self._graph.nodes(data=True):
            entity_type = node_data.get("entity_type", "unknown")
            entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

        # Count relationships by type
        for _, _, edge_data in self._graph.edges(data=True):
            rel_type = edge_data.get("relationship_type", "other")
            relationship_type_counts[rel_type] = relationship_type_counts.get(rel_type, 0) + 1

        return GraphStats(
            node_count=self._graph.number_of_nodes(),
            edge_count=self._graph.number_of_edges(),
            entity_type_counts=entity_type_counts,
            relationship_type_counts=relationship_type_counts,
        )

    async def health_check(self) -> bool:
        """
        Verify the graph store connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            # NetworkX in-memory graph is always "healthy"
            # Just verify the graph object exists
            return self._graph is not None  # type: ignore[no-any-return]
        except Exception:
            return False

    async def entity_exists(self, name: str) -> bool:
        """
        Check if an entity exists in the graph.

        Args:
            name: Entity name to check

        Returns:
            True if entity exists, False otherwise
        """
        return self._graph.has_node(self._normalize_name(name))

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
        """
        entities: list[GraphEntity] = []

        for node, node_data in self._graph.nodes(data=True):
            # Filter by entity type if specified
            if entity_type is not None:
                node_entity_type = node_data.get("entity_type", "")
                if self._entity_type_to_str(entity_type) != node_entity_type:
                    continue

            entity_type_str = node_data.get("entity_type", "unknown")
            entity = GraphEntity(
                name=node_data.get("name", node),
                entity_type=self._str_to_entity_type(entity_type_str),
                aliases=tuple(node_data.get("aliases", [])),
                description=node_data.get("description", ""),
                metadata={k: v for k, v in node_data.items()
                         if k not in {"name", "entity_type", "aliases", "description"}},
            )
            entities.append(entity)

            if limit is not None and len(entities) >= limit:
                break

        return entities


__all__ = ["NetworkXGraphStore"]
