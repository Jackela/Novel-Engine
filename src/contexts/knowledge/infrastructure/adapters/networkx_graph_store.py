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
    CentralityResult,
    CliqueResult,
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

if TYPE_CHECKING:
    pass

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
            self._graph.add_node(
                source_norm, name=relationship.source, entity_type="unknown"
            )
        if not self._graph.has_node(target_norm):
            self._graph.add_node(
                target_norm, name=relationship.target, entity_type="unknown"
            )

        # Check if this exact relationship already exists
        rel_type_str = self._relationship_type_to_str(relationship.relationship_type)
        edge_key = (source_norm, target_norm, rel_type_str)
        if self._graph.has_edge(*edge_key[:2], key=edge_key[2]):
            logger.debug(
                f"Relationship already exists: {relationship.source} -> {relationship.target} ({relationship.relationship_type})"
            )
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
            logger.debug(
                f"Added relationship: {relationship.source} -> {relationship.target} ({relationship.relationship_type})"
            )
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

    async def add_relationships(
        self, relationships: list[GraphRelationship]
    ) -> GraphAddResult:
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
                metadata={
                    k: v
                    for k, v in node_data.items()
                    if k not in {"name", "entity_type", "aliases", "description"}
                },
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
            {self._relationship_type_to_str(rt) for rt in relationship_types}
            if relationship_types
            else None
        )

        # BFS to find neighbors at each depth
        # Queue stores: (node_name, distance, incoming_edge_data)
        from collections import deque

        queue: deque[tuple[str, int, dict[str, Any] | None]] = deque(
            [(normalized_name, 0, None)]
        )

        while queue:
            current_node, distance, incoming_edge = queue.popleft()

            if distance >= max_depth:
                continue

            # Get all outgoing edges from current node
            if not self._graph.has_node(current_node):
                continue

            for _, target, key, edge_data in self._graph.out_edges(
                current_node, keys=True, data=True
            ):
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
                    source=edge_data.get(
                        "source", entity_name if distance == 0 else ""
                    ),
                    target=edge_data.get("target", entity.name),
                    relationship_type=self._str_to_relationship_type(rel_type_str),
                    context=edge_data.get("context", ""),
                    strength=edge_data.get("strength", 1.0),
                    metadata={
                        k: v
                        for k, v in edge_data.items()
                        if k
                        not in {
                            "source",
                            "target",
                            "relationship_type",
                            "context",
                            "strength",
                        }
                    },
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
                    path_nodes = nx.bidirectional_shortest_path(
                        self._graph, source_norm, target_norm
                    )
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
                        source=edge_data.get(
                            "source", from_entity.get("name", from_node)
                        ),
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
        rel_type_filter = (
            self._relationship_type_to_str(relationship_type)
            if relationship_type
            else None
        )

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
                            target=edge_data.get(
                                "target", target_data.get("name", target)
                            ),
                            relationship_type=self._str_to_relationship_type(
                                rel_type_str
                            ),
                            context=edge_data.get("context", ""),
                            strength=edge_data.get("strength", 1.0),
                            metadata={
                                k: v
                                for k, v in edge_data.items()
                                if k
                                not in {
                                    "source",
                                    "target",
                                    "relationship_type",
                                    "context",
                                    "strength",
                                }
                            },
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
                    metadata={
                        k: v
                        for k, v in edge_data.items()
                        if k
                        not in {
                            "source",
                            "target",
                            "relationship_type",
                            "context",
                            "strength",
                        }
                    },
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
            logger.debug(
                f"Removed relationship: {source} -> {target} ({relationship_type})"
            )
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
            relationship_type_counts[rel_type] = (
                relationship_type_counts.get(rel_type, 0) + 1
            )

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
        return self._graph.has_node(self._normalize_name(name))  # type: ignore[no-any-return]

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
                metadata={
                    k: v
                    for k, v in node_data.items()
                    if k not in {"name", "entity_type", "aliases", "description"}
                },
            )
            entities.append(entity)

            if limit is not None and len(entities) >= limit:
                break

        return entities

    async def find_cliques(
        self,
        min_size: int = 3,
        max_size: int | None = None,
        entity_type: EntityType | None = None,
    ) -> CliqueResult:
        """
        Find all cliques (fully connected subgraphs) in the graph.

        Uses an undirected view of the graph for clique detection since
        cliques are traditionally defined on undirected graphs.

        Args:
            min_size: Minimum clique size to report (default: 3)
            max_size: Maximum clique size to report (default: unlimited)
            entity_type: Optional filter for entities of specific type

        Returns:
            CliqueResult with all cliques found
        """
        # Filter by entity type if specified
        working_graph = self._graph

        if entity_type is not None:
            entity_type_str = self._entity_type_to_str(entity_type)
            nodes_to_keep = [
                n
                for n, d in self._graph.nodes(data=True)
                if d.get("entity_type") == entity_type_str
            ]
            working_graph = self._graph.subgraph(nodes_to_keep).copy()

        # Convert to undirected for clique detection
        undirected_graph = working_graph.to_undirected()

        # Find all cliques
        all_cliques = list(nx.find_cliques(undirected_graph))

        # Filter by size
        filtered_cliques = [
            clique
            for clique in all_cliques
            if len(clique) >= min_size and (max_size is None or len(clique) <= max_size)
        ]

        # Convert normalized names back to display names and sort by size
        cliques_with_display_names: list[tuple[str, ...]] = []
        for clique in sorted(filtered_cliques, key=len, reverse=True):
            display_names = []
            for node in clique:
                node_data = self._graph.nodes[node]
                display_names.append(node_data.get("name", node))
            cliques_with_display_names.append(tuple(display_names))

        max_clique_size = max((len(c) for c in filtered_cliques), default=0)

        return CliqueResult(
            cliques=tuple(cliques_with_display_names),
            max_clique_size=max_clique_size,
            clique_count=len(cliques_with_display_names),
        )

    async def get_centrality(
        self,
        entity_name: str | None = None,
        top_n: int | None = None,
    ) -> list[CentralityResult]:
        """
        Calculate centrality metrics for entities in the graph.

        Args:
            entity_name: Optional specific entity to analyze. If None, analyzes all entities.
            top_n: Optional limit to return only top N entities by each metric

        Returns:
            List of CentralityResult objects sorted by pagerank descending
        """
        if entity_name is not None:
            # Analyze single entity
            normalized_name = self._normalize_name(entity_name)
            if not self._graph.has_node(normalized_name):
                return []

            nodes_to_analyze = [normalized_name]
        else:
            nodes_to_analyze = list(self._graph.nodes())

        if not nodes_to_analyze:
            return []

        # Calculate centrality metrics
        # Use undirected graph for closeness/degree as it's more meaningful
        undirected_graph = self._graph.to_undirected()

        # Degree centrality
        degree_centralities = nx.degree_centrality(undirected_graph)

        # Betweenness centrality
        betweenness_centralities = nx.betweenness_centrality(undirected_graph)

        # Closeness centrality
        closeness_centralities = nx.closeness_centrality(undirected_graph)

        # PageRank (works on directed graph)
        pagerank_scores = nx.pagerank(self._graph)

        results: list[CentralityResult] = []
        for node in nodes_to_analyze:
            node_data = self._graph.nodes[node]
            display_name = node_data.get("name", node)

            results.append(
                CentralityResult(
                    entity_name=display_name,
                    degree_centrality=degree_centralities.get(node, 0.0),
                    betweenness_centrality=betweenness_centralities.get(node, 0.0),
                    closeness_centrality=closeness_centralities.get(node, 0.0),
                    pagerank=pagerank_scores.get(node, 0.0),
                )
            )

        # Sort by pagerank descending
        results.sort(key=lambda r: r.pagerank, reverse=True)

        # Apply top_n limit if specified
        if top_n is not None:
            results = results[:top_n]

        return results

    async def find_all_shortest_paths(
        self,
        source: str,
        max_length: int | None = None,
        cutoff: int | None = None,
    ) -> dict[str, PathResult]:
        """
        Find shortest paths from source to all reachable entities.

        Args:
            source: Source entity name
            max_length: Maximum path length to search (default: unlimited)
            cutoff: Stop searching after finding this many paths

        Returns:
            Dict mapping target entity name to PathResult
        """
        source_norm = self._normalize_name(source)

        if not self._graph.has_node(source_norm):
            raise GraphStoreError(
                f"Source entity not found: {source}",
                code="ENTITY_NOT_FOUND",
                details={"entity": source},
            )

        results: dict[str, PathResult] = {}
        count = 0

        # Use single_source_shortest_path_length to efficiently find reachable nodes
        try:
            # Get path lengths from source to all reachable nodes
            path_lengths = nx.single_source_shortest_path_length(
                self._graph, source_norm, cutoff=max_length
            )

            for target in path_lengths:
                if target == source_norm:
                    continue

                if cutoff is not None and count >= cutoff:
                    break

                # Find the actual path
                try:
                    path_nodes = nx.shortest_path(self._graph, source_norm, target)

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
                            continue

                        from_entity = self._graph.nodes[from_node]
                        to_entity = self._graph.nodes[to_node]

                        rel_type_str = edge_data.get("relationship_type", "other")
                        relationships.append(
                            GraphRelationship(
                                source=edge_data.get(
                                    "source", from_entity.get("name", from_node)
                                ),
                                target=edge_data.get(
                                    "target", to_entity.get("name", to_node)
                                ),
                                relationship_type=self._str_to_relationship_type(
                                    rel_type_str
                                ),
                                context=edge_data.get("context", ""),
                                strength=edge_data.get("strength", 1.0),
                            )
                        )

                    # Convert normalized names to display names
                    display_names = []
                    for node in path_nodes:
                        node_data = self._graph.nodes[node]
                        display_names.append(node_data.get("name", node))

                    target_display = display_names[-1]
                    results[target_display] = PathResult(
                        path=tuple(display_names),
                        relationships=tuple(relationships),
                        length=len(relationships),
                    )
                    count += 1

                except nx.NetworkXNoPath:
                    continue

        except Exception as e:
            raise GraphStoreError(
                f"Failed to find paths from {source}",
                code="FIND_PATHS_FAILED",
                details={"error": str(e), "source": source},
            ) from e

        return results

    async def export_graphml(
        self,
        output_path: str,
        include_metadata: bool = True,
    ) -> GraphExportResult:
        """
        Export the graph to GraphML format for visualization tools.

        Args:
            output_path: File path to write GraphML output
            include_metadata: Whether to include entity/relationship metadata

        Returns:
            GraphExportResult with export statistics
        """
        import os
        from pathlib import Path

        try:
            # Create parent directory if it doesn't exist
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare graph for export
            export_graph = self._graph.copy()

            # Convert lists to strings (GraphML doesn't support list types)
            for node, node_data in export_graph.nodes(data=True):
                for key, value in list(node_data.items()):
                    if isinstance(value, list):
                        node_data[key] = ",".join(str(v) for v in value)

            if not include_metadata:
                # Strip metadata, keeping only essential attributes
                for node, node_data in export_graph.nodes(data=True):
                    keep_keys = {"name", "entity_type"}
                    keys_to_remove = list(set(node_data.keys()) - keep_keys)
                    for key in keys_to_remove:
                        del node_data[key]

                for _, _, edge_data in export_graph.edges(data=True):
                    keep_keys = {"relationship_type", "source", "target"}
                    keys_to_remove = list(set(edge_data.keys()) - keep_keys)
                    for key in keys_to_remove:
                        del edge_data[key]

            # Convert enums to strings for GraphML compatibility
            for node, node_data in export_graph.nodes(data=True):
                # Ensure entity_type is a string
                if "entity_type" in node_data:
                    entity_type_value = node_data["entity_type"]
                    if isinstance(entity_type_value, EntityType):
                        node_data["entity_type"] = entity_type_value.value

            for _, _, edge_data in export_graph.edges(data=True):
                # Ensure relationship_type is a string
                if "relationship_type" in edge_data:
                    rel_type_value = edge_data["relationship_type"]
                    if isinstance(rel_type_value, RelationshipType):
                        edge_data["relationship_type"] = rel_type_value.value

            # Write to GraphML
            nx.readwrite.write_graphml(export_graph, output_path)

            # Get file size
            file_size = os.path.getsize(output_path)

            logger.info(
                f"Exported graph to GraphML: {output_path} ({export_graph.number_of_nodes()} nodes, {export_graph.number_of_edges()} edges)"
            )

            return GraphExportResult(
                format="graphml",
                node_count=export_graph.number_of_nodes(),
                edge_count=export_graph.number_of_edges(),
                data=output_path,
                size_bytes=file_size,
            )

        except Exception as e:
            raise GraphStoreError(
                f"Failed to export graph to GraphML: {output_path}",
                code="EXPORT_FAILED",
                details={"error": str(e), "output_path": output_path},
            ) from e

    async def export_json(
        self,
        output_path: str | None = None,
        pretty: bool = True,
    ) -> GraphExportResult:
        """
        Export the graph to JSON format.

        Args:
            output_path: File path to write JSON output (if None, returns JSON string in data field)
            pretty: Whether to format JSON with indentation

        Returns:
            GraphExportResult with export statistics
        """
        import json
        from pathlib import Path

        try:
            # Build export structure
            nodes_data: list[dict[str, Any]] = []
            edges_data: list[dict[str, Any]] = []

            for node, node_data in self._graph.nodes(data=True):
                node_dict = {
                    "id": node,
                    "name": node_data.get("name", node),
                    "entity_type": self._entity_type_to_str(
                        node_data.get("entity_type", "unknown")
                    ),
                }

                # Add optional fields if present
                if "aliases" in node_data:
                    node_dict["aliases"] = node_data["aliases"]
                if "description" in node_data:
                    node_dict["description"] = node_data["description"]

                # Add remaining metadata
                for key, value in node_data.items():
                    if key not in {
                        "id",
                        "name",
                        "entity_type",
                        "aliases",
                        "description",
                    }:
                        node_dict[key] = value

                nodes_data.append(node_dict)

            for source, target, edge_data in self._graph.edges(data=True):
                edge_dict = {
                    "source": source,
                    "target": target,
                    "source_name": edge_data.get("source", source),
                    "target_name": edge_data.get("target", target),
                    "relationship_type": self._relationship_type_to_str(
                        edge_data.get("relationship_type", "other")
                    ),
                }

                # Add optional fields if present
                if "context" in edge_data:
                    edge_dict["context"] = edge_data["context"]
                if "strength" in edge_data:
                    edge_dict["strength"] = edge_data["strength"]

                # Add remaining metadata
                for key, value in edge_data.items():
                    if key not in {
                        "source",
                        "target",
                        "source_name",
                        "target_name",
                        "relationship_type",
                        "context",
                        "strength",
                    }:
                        edge_dict[key] = value

                edges_data.append(edge_dict)

            export_data = {
                "graph": {
                    "nodes": nodes_data,
                    "edges": edges_data,
                },
                "metadata": {
                    "node_count": len(nodes_data),
                    "edge_count": len(edges_data),
                    "export_timestamp": self._get_timestamp(),
                },
            }

            # Serialize to JSON
            json_string = json.dumps(
                export_data, indent=2 if pretty else None, ensure_ascii=False
            )
            data_size = len(json_string.encode("utf-8"))

            # Write to file if path provided
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(json_string, encoding="utf-8")
                logger.info(
                    f"Exported graph to JSON: {output_path} ({len(nodes_data)} nodes, {len(edges_data)} edges)"
                )

                return GraphExportResult(
                    format="json",
                    node_count=len(nodes_data),
                    edge_count=len(edges_data),
                    data=output_path,
                    size_bytes=data_size,
                )
            else:
                return GraphExportResult(
                    format="json",
                    node_count=len(nodes_data),
                    edge_count=len(edges_data),
                    data=json_string,
                    size_bytes=data_size,
                )

        except Exception as e:
            raise GraphStoreError(
                f"Failed to export graph to JSON: {output_path or 'string'}",
                code="EXPORT_FAILED",
                details={"error": str(e), "output_path": output_path},
            ) from e

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


__all__ = ["NetworkXGraphStore"]
