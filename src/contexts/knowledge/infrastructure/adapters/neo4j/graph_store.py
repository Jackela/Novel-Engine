"""Neo4j Graph Store Adapter.

Implements IGraphStore port using Neo4j for persistent graph storage.
Supports entity and relationship operations for knowledge graph management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

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

from .connection_manager import ConnectionManager
from .entity_repository import EntityRepository
from .query_builder import QueryBuilder
from .relationship_repository import RelationshipRepository

logger = structlog.get_logger(__name__)


class Neo4jGraphStore(IGraphStore):
    """Neo4j-based graph storage adapter for knowledge graphs."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str = "neo4j",
    ) -> None:
        """Initialize the Neo4j graph store.

        Args:
            uri: Bolt connection URI
            user: Database username
            password: Database password
            database: Database name
        """
        self._connection = ConnectionManager(uri, user, password, database)
        self._entity_repo = EntityRepository(self._connection)
        self._relationship_repo = RelationshipRepository(self._connection)
        self._query = QueryBuilder()

    def _get_driver(self) -> Any:
        """Get Neo4j driver instance."""
        return self._connection.get_driver()

    def _close(self) -> None:
        """Close the Neo4j driver connection."""
        self._connection.close()

    def __enter__(self) -> Neo4jGraphStore:
        """Context manager entry."""
        self._connection.get_driver()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self._connection.close()

    # Entity operations - delegate to EntityRepository
    async def add_entity(self, entity: GraphEntity) -> bool:
        """Add an entity to the graph."""
        return await self._entity_repo.add(entity)

    async def add_entities(self, entities: list[GraphEntity]) -> GraphAddResult:
        """Add multiple entities in batch."""
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

    async def get_entity(self, name: str) -> GraphEntity | None:
        """Get an entity by name."""
        return await self._entity_repo.get(name)

    async def remove_entity(self, name: str) -> bool:
        """Remove an entity and its relationships."""
        return await self._entity_repo.remove(name)

    async def entity_exists(self, name: str) -> bool:
        """Check if an entity exists."""
        return await self._entity_repo.exists(name)

    async def get_all_entities(
        self,
        entity_type: EntityType | None = None,
        limit: int | None = None,
    ) -> list[GraphEntity]:
        """Get all entities."""
        return await self._entity_repo.get_all(entity_type, limit)

    # Relationship operations - delegate to RelationshipRepository
    async def add_relationship(self, relationship: GraphRelationship) -> bool:
        """Add a relationship between two entities."""
        return await self._relationship_repo.add(relationship)

    async def add_relationships(
        self, relationships: list[GraphRelationship]
    ) -> GraphAddResult:
        """Add multiple relationships in batch."""
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

    async def get_relationships(
        self,
        entity_name: str,
        relationship_type: RelationshipType | None = None,
    ) -> list[GraphRelationship]:
        """Get all relationships for an entity."""
        return await self._relationship_repo.get_for_entity(
            entity_name, relationship_type
        )

    async def get_relationships_between(
        self,
        source: str,
        target: str,
    ) -> list[GraphRelationship]:
        """Get all relationships between two specific entities."""
        return await self._relationship_repo.get_between(source, target)

    async def remove_relationship(
        self,
        source: str,
        target: str,
        relationship_type: RelationshipType,
    ) -> bool:
        """Remove a specific relationship."""
        return await self._relationship_repo.remove(source, target, relationship_type)

    # Path operations
    async def find_path(
        self,
        source: str,
        target: str,
        max_length: int | None = None,
    ) -> PathResult | None:
        """Find shortest path between two entities."""
        source_norm = self._query.normalize_name(source)
        target_norm = self._query.normalize_name(target)

        # Verify entities exist
        if not await self.entity_exists(source):
            raise GraphStoreError(
                f"Source entity not found: {source}",
                code="ENTITY_NOT_FOUND",
                details={"entity": source},
            )

        if not await self.entity_exists(target):
            raise GraphStoreError(
                f"Target entity not found: {target}",
                code="ENTITY_NOT_FOUND",
                details={"entity": target},
            )

        if source_norm == target_norm:
            return PathResult(
                path=(source,),
                relationships=(),
                length=0,
            )

        query, params = self._query.find_path(source_norm, target_norm, max_length)

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)
                record = result.single()

                if not record:
                    return None

                path_names = record["path_names"]
                rels_data = record["relationships"]

                relationships: list[GraphRelationship] = []
                for rel_data in rels_data:
                    rel_type_str = rel_data["relationship_type"]
                    relationships.append(
                        GraphRelationship(
                            source=rel_data.get("source", source),
                            target=rel_data.get("target", target),
                            relationship_type=self._query.str_to_relationship_type(
                                rel_type_str
                            ),
                            context=rel_data.get("context", ""),
                            strength=rel_data.get("strength", 1.0),
                        )
                    )

                return PathResult(
                    path=tuple(path_names),
                    relationships=tuple(relationships),
                    length=len(relationships),
                )

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
        """Find shortest paths from source to multiple targets."""
        results: dict[str, PathResult | None] = {}

        for target in targets:
            try:
                path_result = await self.find_path(source, target, max_length)
                results[target] = path_result
            except GraphStoreError:
                results[target] = None

        return results

    # Neighbor operations
    async def get_neighbors(
        self,
        entity_name: str,
        max_depth: int = 1,
        relationship_types: list[RelationshipType] | None = None,
    ) -> list[GraphNeighbor]:
        """Get all entities connected to the given entity."""
        normalized_name = self._query.normalize_name(entity_name)

        # Build relationship type filter
        rel_filter = ""
        params: dict[str, Any] = {
            "normalized_name": normalized_name,
            "max_depth": max_depth,
        }

        if relationship_types:
            rel_types = [
                self._query.relationship_type_to_str(rt) for rt in relationship_types
            ]
            params["rel_types"] = rel_types
            rel_filter = "AND r.relationship_type IN $rel_types"

        query = f"""
        MATCH path = (start:Entity {{normalized_name: $normalized_name}})-[:RELATES*1..{max_depth}]-(neighbor:Entity)
        WITH start, neighbor, relationships(path) as rels
        UNWIND rels as r
        WITH start, neighbor, r
        WHERE r.relationship_type IS NOT NULL {rel_filter}
        RETURN DISTINCT
            neighbor.normalized_name as neighbor_norm,
            neighbor.name as name,
            neighbor.entity_type as entity_type,
            neighbor.aliases as aliases,
            neighbor.description as description,
            r.relationship_type as relationship_type,
            r.source as source,
            r.target as target,
            r.context as context,
            r.strength as strength,
            length(shortestPath((start)-[*]-(neighbor))) as distance
        ORDER BY distance, strength DESC
        """

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)

                neighbors: list[GraphNeighbor] = []
                seen = set()

                for record in result:
                    neighbor_name = record["name"]
                    if neighbor_name in seen:
                        continue
                    seen.add(neighbor_name)

                    entity_type = self._query.str_to_entity_type(record["entity_type"])

                    entity = GraphEntity(
                        name=record["name"],
                        entity_type=entity_type,
                        aliases=tuple(record.get("aliases", [])),
                        description=record.get("description", ""),
                    )

                    rel_type_str = record["relationship_type"]
                    relationship = GraphRelationship(
                        source=record.get("source", entity_name),
                        target=record.get("target", record["name"]),
                        relationship_type=self._query.str_to_relationship_type(
                            rel_type_str
                        ),
                        context=record.get("context", ""),
                        strength=record.get("strength", 1.0),
                    )

                    neighbors.append(
                        GraphNeighbor(
                            entity=entity,
                            relationship=relationship,
                            distance=record["distance"],
                        )
                    )

                return neighbors

        except Exception as e:
            raise GraphStoreError(
                f"Failed to get neighbors for {entity_name}",
                code="GET_NEIGHBORS_FAILED",
                details={"error": str(e), "entity": entity_name},
            ) from e

    # Graph operations
    async def clear(self) -> None:
        """Remove all entities and relationships."""
        query = "MATCH (n:Entity) DETACH DELETE n"

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                session.run(query)
                logger.debug("Cleared graph")
        except Exception as e:
            raise GraphStoreError(
                "Failed to clear graph",
                code="CLEAR_FAILED",
                details={"error": str(e)},
            ) from e

    async def get_stats(self) -> GraphStats:
        """Get statistics about the graph."""
        query, params = self._query.get_stats()

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)
                record = result.single()

                if not record:
                    return GraphStats(
                        node_count=0,
                        edge_count=0,
                        entity_type_counts={},
                        relationship_type_counts={},
                    )

                # Count entities by type
                entity_type_counts: dict[str, int] = {}
                for et in record.get("entity_types", []):
                    count_query, count_params = self._query.count_entities_by_type(et)
                    count_result = session.run(count_query, count_params)
                    count_record = count_result.single()
                    if count_record:
                        entity_type_counts[et] = count_record["count"]

                # Count relationships by type
                relationship_type_counts: dict[str, int] = {}
                for rt in record.get("rel_types", []):
                    count_query, count_params = self._query.count_relationships_by_type(
                        rt
                    )
                    count_result = session.run(count_query, count_params)
                    count_record = count_result.single()
                    if count_record:
                        relationship_type_counts[rt] = count_record["count"]

                return GraphStats(
                    node_count=record["node_count"],
                    edge_count=record["edge_count"],
                    entity_type_counts=entity_type_counts,
                    relationship_type_counts=relationship_type_counts,
                )

        except Exception as e:
            raise GraphStoreError(
                "Failed to get graph stats",
                code="GET_STATS_FAILED",
                details={"error": str(e)},
            ) from e

    async def health_check(self) -> bool:
        """Verify the graph store connection is healthy."""
        return self._connection.health_check()

    # Analysis operations using NetworkX
    async def find_cliques(
        self,
        min_size: int = 3,
        max_size: int | None = None,
        entity_type: EntityType | None = None,
    ) -> CliqueResult:
        """Find all cliques in the graph."""
        try:
            import networkx as nx
        except ImportError:
            raise GraphStoreError(
                "networkx package is required for clique detection",
                code="LIBRARY_NOT_AVAILABLE",
            )

        # Fetch all relevant nodes and relationships
        query = """
        MATCH (n:Entity)
        """
        params: dict[str, Any] = {}

        if entity_type is not None:
            query += "WHERE n.entity_type = $entity_type\n"
            params["entity_type"] = self._query.entity_type_to_str(entity_type)

        query += """
        OPTIONAL MATCH (n)-[r:RELATES]->(m:Entity)
        RETURN n.normalized_name as node_name, n.name as display_name,
               collect({target: m.normalized_name, rel_type: r.relationship_type}) as connections
        """

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)

                graph = nx.Graph()

                for record in result:
                    node_name = record["node_name"]
                    display_name = record["display_name"]
                    graph.add_node(node_name, display_name=display_name)

                    for conn in record["connections"]:
                        if conn.get("target"):
                            graph.add_edge(node_name, conn["target"])

                # Find cliques
                all_cliques = list(nx.find_cliques(graph))

                # Filter by size
                filtered_cliques = [
                    clique
                    for clique in all_cliques
                    if len(clique) >= min_size
                    and (max_size is None or len(clique) <= max_size)
                ]

                # Convert to display names
                cliques_with_display_names: list[tuple[str, ...]] = []
                for clique in sorted(filtered_cliques, key=len, reverse=True):
                    display_names: list[str] = []
                    for node in clique:
                        if node in graph.nodes:
                            display_names.append(
                                graph.nodes[node].get("display_name", node)
                            )
                        else:
                            display_names.append(node)
                    cliques_with_display_names.append(tuple(display_names))

                max_clique_size = max((len(c) for c in filtered_cliques), default=0)

                return CliqueResult(
                    cliques=tuple(cliques_with_display_names),
                    max_clique_size=max_clique_size,
                    clique_count=len(cliques_with_display_names),
                )

        except Exception as e:
            raise GraphStoreError(
                "Failed to find cliques",
                code="FIND_CLIQUES_FAILED",
                details={"error": str(e)},
            ) from e

    async def get_centrality(
        self,
        entity_name: str | None = None,
        top_n: int | None = None,
    ) -> list[CentralityResult]:
        """Calculate centrality metrics for entities."""
        try:
            import networkx as nx
        except ImportError:
            raise GraphStoreError(
                "networkx package is required for centrality calculation",
                code="LIBRARY_NOT_AVAILABLE",
            )

        # Fetch graph data
        query = """
        MATCH (n:Entity)
        WITH collect(n) as nodes
        UNWIND nodes as n
        OPTIONAL MATCH (n)-[r_out:RELATES]->(m:Entity)
        OPTIONAL MATCH (o:Entity)-[r_in:RELATES]->(n)
        RETURN n.normalized_name as node_name, n.name as display_name,
               count(DISTINCT m) as out_degree,
               count(DISTINCT o) as in_degree,
               collect(DISTINCT m.normalized_name) as neighbors
        """

        driver = self._get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query)

                graph = nx.Graph()

                for record in result:
                    node_name = record["node_name"]
                    display_name = record["display_name"]
                    graph.add_node(node_name, display_name=display_name)

                    for neighbor in record.get("neighbors", []):
                        if neighbor:
                            graph.add_edge(node_name, neighbor)

                # Calculate centrality
                degree_centralities = nx.degree_centrality(graph)
                betweenness_centralities = nx.betweenness_centrality(graph)

                try:
                    closeness_centralities = nx.closeness_centrality(graph)
                except nx.NetworkXError:
                    closeness_centralities = {n: 0.0 for n in graph.nodes()}

                # PageRank
                directed_graph = nx.DiGraph()
                for u, v in graph.edges():
                    directed_graph.add_edge(u, v)
                pagerank_scores = nx.pagerank(directed_graph)

                results: list[CentralityResult] = []

                if entity_name is not None:
                    normalized_name = self._query.normalize_name(entity_name)
                    if normalized_name in graph.nodes:
                        display_name = graph.nodes[normalized_name].get(
                            "display_name", entity_name
                        )
                        results.append(
                            CentralityResult(
                                entity_name=display_name,
                                degree_centrality=degree_centralities.get(
                                    normalized_name, 0.0
                                ),
                                betweenness_centrality=betweenness_centralities.get(
                                    normalized_name, 0.0
                                ),
                                closeness_centrality=closeness_centralities.get(
                                    normalized_name, 0.0
                                ),
                                pagerank=pagerank_scores.get(normalized_name, 0.0),
                            )
                        )
                else:
                    for node in graph.nodes:
                        display_name = graph.nodes[node].get("display_name", node)
                        results.append(
                            CentralityResult(
                                entity_name=display_name,
                                degree_centrality=degree_centralities.get(node, 0.0),
                                betweenness_centrality=betweenness_centralities.get(
                                    node, 0.0
                                ),
                                closeness_centrality=closeness_centralities.get(
                                    node, 0.0
                                ),
                                pagerank=pagerank_scores.get(node, 0.0),
                            )
                        )

                # Sort by pagerank descending
                results.sort(key=lambda r: r.pagerank, reverse=True)

                # Apply top_n limit if specified
                if top_n is not None:
                    results = results[:top_n]

                return results

        except Exception as e:
            raise GraphStoreError(
                "Failed to calculate centrality",
                code="CENTRALITY_FAILED",
                details={"error": str(e)},
            ) from e

    # Export operations
    async def export_graphml(
        self,
        output_path: str,
        include_metadata: bool = True,
    ) -> GraphExportResult:
        """Export the graph to GraphML format."""
        try:
            import networkx as nx
        except ImportError:
            raise GraphStoreError(
                "networkx package is required for GraphML export",
                code="LIBRARY_NOT_AVAILABLE",
            )

        from pathlib import Path

        try:
            # Fetch all nodes and edges
            nodes_query = "MATCH (n:Entity) RETURN n"
            edges_query = """
            MATCH (s:Entity)-[r:RELATES]->(t:Entity)
            RETURN s.normalized_name as source, t.normalized_name as target, r
            """

            driver = self._get_driver()

            with driver.session(database=self._connection._database) as session:
                nodes_result = session.run(nodes_query)
                edges_result = session.run(edges_query)

                # Build NetworkX graph
                graph = nx.MultiDiGraph()

                for record in nodes_result:
                    node = record["n"]
                    normalized_name = node.get("normalized_name", "")

                    node_attrs = {
                        "name": node.get("name", normalized_name),
                        "entity_type": node.get("entity_type", "unknown"),
                    }

                    if include_metadata:
                        node_attrs["aliases"] = node.get("aliases", [])
                        node_attrs["description"] = node.get("description", "")

                    graph.add_node(normalized_name, **node_attrs)

                for record in edges_result:
                    source = record["source"]
                    target = record["target"]
                    rel = record["r"]

                    edge_attrs = {
                        "relationship_type": rel.get("relationship_type", "other"),
                    }

                    if include_metadata:
                        edge_attrs["source"] = rel.get("source", source)
                        edge_attrs["target"] = rel.get("target", target)
                        edge_attrs["context"] = rel.get("context", "")
                        edge_attrs["strength"] = rel.get("strength", 1.0)

                    graph.add_edge(source, target, **edge_attrs)

                # Write to GraphML
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                nx.readwrite.write_graphml(graph, output_path)

                # Get file size
                import os

                file_size = os.path.getsize(output_path)

                logger.info(
                    f"Exported Neo4j graph to GraphML: {output_path} "
                    f"({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)"
                )

                return GraphExportResult(
                    format="graphml",
                    node_count=graph.number_of_nodes(),
                    edge_count=graph.number_of_edges(),
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
        """Export the graph to JSON format."""
        import json
        from pathlib import Path

        try:
            # Fetch all nodes and edges
            nodes_query = "MATCH (n:Entity) RETURN n"
            edges_query = """
            MATCH (s:Entity)-[r:RELATES]->(t:Entity)
            RETURN s.normalized_name as source, s.name as source_name,
                   t.normalized_name as target, t.name as target_name, r
            """

            driver = self._get_driver()

            with driver.session(database=self._connection._database) as session:
                nodes_result = session.run(nodes_query)
                edges_result = session.run(edges_query)

                nodes_data: list[dict[str, Any]] = []
                edges_data: list[dict[str, Any]] = []

                for record in nodes_result:
                    node = record["n"]
                    node_dict = {
                        "id": node.get("normalized_name", ""),
                        "name": node.get("name", ""),
                        "entity_type": node.get("entity_type", "unknown"),
                    }

                    if "aliases" in node:
                        node_dict["aliases"] = node["aliases"]
                    if "description" in node:
                        node_dict["description"] = node["description"]

                    nodes_data.append(node_dict)

                for record in edges_result:
                    rel = record["r"]
                    edge_dict = {
                        "source": record["source"],
                        "target": record["target"],
                        "source_name": rel.get("source", record["source_name"]),
                        "target_name": rel.get("target", record["target_name"]),
                        "relationship_type": rel.get("relationship_type", "other"),
                    }

                    if "context" in rel:
                        edge_dict["context"] = rel["context"]
                    if "strength" in rel:
                        edge_dict["strength"] = rel["strength"]

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
                        "source": "neo4j",
                    },
                }

                json_string = json.dumps(
                    export_data, indent=2 if pretty else None, ensure_ascii=False
                )
                data_size = len(json_string.encode("utf-8"))

                if output_path:
                    output_file = Path(output_path)
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_text(json_string, encoding="utf-8")
                    logger.info(f"Exported Neo4j graph to JSON: {output_path}")

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
        return datetime.now(timezone.utc).isoformat()


__all__ = ["Neo4jGraphStore"]
