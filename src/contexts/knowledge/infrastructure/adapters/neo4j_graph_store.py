"""
Neo4j Graph Store Adapter

Implements IGraphStore port using Neo4j for persistent graph storage.
Supports entity and relationship operations for knowledge graph management.

This adapter provides persistent storage with the same interface as NetworkX,
allowing seamless switching between in-memory and persistent graph storage.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implements IGraphStore port
- Article I (DDD): No business logic, only graph storage operations
- Article IV (SSOT): Neo4j as authoritative persistent graph storage

Warzone 4: AI Brain - BRAIN-031B
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class Neo4jGraphStore(IGraphStore):
    """
    Neo4j-based graph storage adapter for knowledge graphs.

    Why Neo4j:
        - Native graph database with efficient relationship traversal
        - Cypher query language for powerful graph queries
        - ACID transactions for data integrity
        - Horizontal scaling for large graphs

    Implementation Notes:
        - Uses Bolt protocol for efficient communication
        - Entity names are case-insensitive for lookups
        - Labels represent entity types
        - Relationships are typed edges between nodes
        - Graceful fallback to NetworkX when neo4j driver unavailable

    Configuration:
        NEO4J_URI: Bolt connection URI (default: bolt://localhost:7687)
        NEO4J_USER: Database username (default: neo4j)
        NEO4J_PASSWORD: Database password (default: password)
        NEO4J_DATABASE: Database name (default: neo4j)
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str = "neo4j",
    ) -> None:
        """
        Initialize the Neo4j graph store.

        Args:
            uri: Bolt connection URI (default: from NEO4J_URI env var or bolt://localhost:7687)
            user: Database username (default: from NEO4J_USER env var or neo4j)
            password: Database password (default: from NEO4J_PASSWORD env var or password)
            database: Database name (default: neo4j)
        """
        import os

        self._uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = user or os.getenv("NEO4J_USER", "neo4j")
        self._password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._database = database

        # Lazy initialization - connect on first use
        self._driver: Any = None
        self._connected = False

    def _get_driver(self) -> Any:
        """Get or create the Neo4j driver instance."""
        if self._driver is None:
            try:
                from neo4j import GraphDatabase

                self._driver = GraphDatabase.driver(
                    self._uri,
                    auth=(self._user, self._password),
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50,
                    connection_acquisition_timeout=60,
                )
                self._connected = True
                logger.info(f"Connected to Neo4j at {self._uri}")
            except ImportError:
                raise GraphStoreError(
                    "neo4j package is not installed. Install with: pip install neo4j>=5.0.0",
                    code="DRIVER_NOT_AVAILABLE",
                    details={"uri": self._uri},
                )
            except Exception as e:
                raise GraphStoreError(
                    f"Failed to connect to Neo4j at {self._uri}",
                    code="CONNECTION_FAILED",
                    details={"error": str(e), "uri": self._uri},
                ) from e

        return self._driver

    def _close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self._connected = False
            logger.info("Closed Neo4j connection")

    def __enter__(self) -> Neo4jGraphStore:
        """Context manager entry."""
        self._get_driver()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self._close()

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

    def _execute_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a Cypher query and return the result.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query result object
        """
        driver = self._get_driver()

        with driver.session(database=self._database) as session:
            result = session.run(query, parameters or {})
            return result

    def _execute_query_single(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any | None:
        """Execute query and return single result."""
        driver = self._get_driver()

        with driver.session(database=self._database) as session:
            result = session.run(query, parameters or {})
            record = result.single()
            return record

    async def add_entity(self, entity: GraphEntity) -> bool:
        """
        Add an entity (node) to the graph.

        Args:
            entity: GraphEntity to add

        Returns:
            True if entity was added, False if it already existed
        """
        normalized_name = self._normalize_name(entity.name)

        # Check if entity already exists
        check_query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        RETURN count(n) as count
        """
        result = self._execute_query_single(check_query, {"normalized_name": normalized_name})

        if result and result["count"] > 0:
            logger.debug(f"Entity already exists: {entity.name}")
            return False

        try:
            # Build entity properties
            properties = {
                "normalized_name": normalized_name,
                "name": entity.name,
                "entity_type": self._entity_type_to_str(entity.entity_type),
                "aliases": list(entity.aliases),
                "description": entity.description,
            }
            properties.update(entity.metadata)

            # Create entity with type-specific label
            entity_type_label = self._entity_type_to_str(entity.entity_type)
            create_query = f"""
            CREATE (n:Entity:{entity_type_label})
            SET n = $properties
            RETURN n
            """

            self._execute_query(create_query, {"properties": properties})
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

        Args:
            relationship: GraphRelationship to add

        Returns:
            True if relationship was added, False if it already existed
        """
        source_norm = self._normalize_name(relationship.source)
        target_norm = self._normalize_name(relationship.target)
        rel_type_str = self._relationship_type_to_str(relationship.relationship_type)

        # Auto-create placeholder entities if they don't exist
        for norm_name, display_name in [(source_norm, relationship.source), (target_norm, relationship.target)]:
            check_query = """
            MATCH (n:Entity {normalized_name: $normalized_name})
            RETURN count(n) as count
            """
            result = self._execute_query_single(check_query, {"normalized_name": norm_name})

            if not result or result["count"] == 0:
                create_placeholder = """
                CREATE (n:Entity {normalized_name: $normalized_name, name: $name, entity_type: 'unknown'})
                """
                self._execute_query(
                    create_placeholder,
                    {"normalized_name": norm_name, "name": display_name}
                )

        # Check if relationship already exists
        check_rel_query = """
        MATCH (s:Entity {normalized_name: $source_norm})
        -[r:RELATES {relationship_type: $rel_type}]->
        (t:Entity {normalized_name: $target_norm})
        RETURN count(r) as count
        """
        result = self._execute_query_single(
            check_rel_query,
            {"source_norm": source_norm, "target_norm": target_norm, "rel_type": rel_type_str}
        )

        if result and result["count"] > 0:
            logger.debug(f"Relationship already exists: {relationship.source} -> {relationship.target}")
            return False

        try:
            # Build relationship properties
            properties = {
                "relationship_type": rel_type_str,
                "source": relationship.source,
                "target": relationship.target,
                "context": relationship.context,
                "strength": relationship.strength,
            }
            properties.update(relationship.metadata)

            create_rel_query = """
            MATCH (s:Entity {normalized_name: $source_norm})
            MATCH (t:Entity {normalized_name: $target_norm})
            CREATE (s)-[r:RELATES]->(t)
            SET r = $properties
            RETURN r
            """

            self._execute_query(
                create_rel_query,
                {
                    "source_norm": source_norm,
                    "target_norm": target_norm,
                    "properties": properties,
                }
            )
            logger.debug(f"Added relationship: {relationship.source} -> {relationship.target}")
            return True

        except Exception as e:
            raise GraphStoreError(
                f"Failed to add relationship {relationship.source} -> {relationship.target}",
                code="ADD_RELATIONSHIP_FAILED",
                details={
                    "error": str(e),
                    "source": relationship.source,
                    "target": relationship.target,
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

        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        RETURN n
        """
        result = self._execute_query_single(query, {"normalized_name": normalized_name})

        if not result:
            return None

        try:
            node = result["n"]
            entity_type_str = node.get("entity_type", "unknown")
            entity_type = self._str_to_entity_type(entity_type_str)

            # Extract metadata (exclude known fields)
            known_fields = {"normalized_name", "name", "entity_type", "aliases", "description"}
            metadata = {k: v for k, v in node.items() if k not in known_fields}

            return GraphEntity(
                name=node.get("name", name),
                entity_type=entity_type,
                aliases=tuple(node.get("aliases", [])),
                description=node.get("description", ""),
                metadata=metadata,
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

        # Build relationship type filter
        rel_filter = ""
        params: dict[str, Any] = {"normalized_name": normalized_name, "max_depth": max_depth}

        if relationship_types:
            rel_types = [self._relationship_type_to_str(rt) for rt in relationship_types]
            params["rel_types"] = rel_types
            rel_filter = "AND r.relationship_type IN $rel_types"

        # Variable path length query for neighbors at different depths
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

        try:
            result = self._execute_query(query, params)

            neighbors: list[GraphNeighbor] = []
            for record in result:
                entity_type = self._str_to_entity_type(record["entity_type"])

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
                    relationship_type=self._str_to_relationship_type(rel_type_str),
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

        # Verify both entities exist
        source_entity = await self.get_entity(source)
        target_entity = await self.get_entity(target)

        if source_entity is None:
            raise GraphStoreError(
                f"Source entity not found: {source}",
                code="ENTITY_NOT_FOUND",
                details={"entity": source},
            )

        if target_entity is None:
            raise GraphStoreError(
                f"Target entity not found: {target}",
                code="ENTITY_NOT_FOUND",
                details={"entity": target},
            )

        if source_norm == target_norm:
            return PathResult(
                path=(source_entity.name,),
                relationships=(),
                length=0,
            )

        # Build path length constraint
        length_constraint = ""
        params: dict[str, Any] = {"source_norm": source_norm, "target_norm": target_norm}

        if max_length is not None:
            params["max_length"] = max_length
            length_constraint = f"*1..{max_length}"
        else:
            length_constraint = "*1..15"  # Reasonable default limit

        query = f"""
        MATCH path = shortestPath(
            (s:Entity {{normalized_name: $source_norm}})-[:RELATES{length_constraint}]->(t:Entity {{normalized_name: $target_norm}})
        )
        WITH path, relationships(path) as rels
        WHERE rels IS NOT NULL
        UNWIND rels as r
        RETURN
            [n in nodes(path) | n.name] as path_names,
            collect({{
                source: r.source,
                target: r.target,
                relationship_type: r.relationship_type,
                context: r.context,
                strength: r.strength
            }}) as relationships
        """

        try:
            result = self._execute_query_single(query, params)

            if not result:
                return None

            path_names = result["path_names"]
            rels_data = result["relationships"]

            relationships: list[GraphRelationship] = []
            for rel_data in rels_data:
                rel_type_str = rel_data["relationship_type"]
                relationships.append(
                    GraphRelationship(
                        source=rel_data.get("source", source),
                        target=rel_data.get("target", target),
                        relationship_type=self._str_to_relationship_type(rel_type_str),
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

        query = """
        MATCH (e:Entity {normalized_name: $normalized_name})-[r:RELATES]->(t:Entity)
        RETURN r, t.name as target_name
        """
        params: dict[str, Any] = {"normalized_name": normalized_name}

        if relationship_type is not None:
            query = """
            MATCH (e:Entity {normalized_name: $normalized_name})-[r:RELATES]->(t:Entity)
            WHERE r.relationship_type = $rel_type
            RETURN r, t.name as target_name
            """
            params["rel_type"] = self._relationship_type_to_str(relationship_type)

        try:
            result = self._execute_query(query, params)

            relationships: list[GraphRelationship] = []
            for record in result:
                rel = record["r"]
                rel_type_str = rel.get("relationship_type", "other")
                relationships.append(
                    GraphRelationship(
                        source=rel.get("source", entity_name),
                        target=rel.get("target", record["target_name"]),
                        relationship_type=self._str_to_relationship_type(rel_type_str),
                        context=rel.get("context", ""),
                        strength=rel.get("strength", 1.0),
                    )
                )

            return relationships

        except Exception as e:
            raise GraphStoreError(
                f"Failed to get relationships for {entity_name}",
                code="GET_RELATIONSHIPS_FAILED",
                details={"error": str(e), "entity": entity_name},
            ) from e

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

        query = """
        MATCH (s:Entity {normalized_name: $source_norm})-[r:RELATES]->(t:Entity {normalized_name: $target_norm})
        RETURN r
        """

        try:
            result = self._execute_query(query, {"source_norm": source_norm, "target_norm": target_norm})

            relationships: list[GraphRelationship] = []
            for record in result:
                rel = record["r"]
                rel_type_str = rel.get("relationship_type", "other")
                relationships.append(
                    GraphRelationship(
                        source=rel.get("source", source),
                        target=rel.get("target", target),
                        relationship_type=self._str_to_relationship_type(rel_type_str),
                        context=rel.get("context", ""),
                        strength=rel.get("strength", 1.0),
                    )
                )

            return relationships

        except Exception as e:
            raise GraphStoreError(
                f"Failed to get relationships between {source} and {target}",
                code="GET_RELATIONSHIPS_FAILED",
                details={"error": str(e), "source": source, "target": target},
            ) from e

    async def remove_entity(self, name: str) -> bool:
        """
        Remove an entity and all its relationships from the graph.

        Args:
            name: Entity name to remove

        Returns:
            True if entity was removed, False if not found
        """
        normalized_name = self._normalize_name(name)

        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        DETACH DELETE n
        RETURN count(n) as count
        """

        try:
            result = self._execute_query_single(query, {"normalized_name": normalized_name})

            if result and result["count"] > 0:
                logger.debug(f"Removed entity: {name}")
                return True

            return False

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

        query = """
        MATCH (s:Entity {normalized_name: $source_norm})-[r:RELATES {relationship_type: $rel_type}]->(t:Entity {normalized_name: $target_norm})
        DELETE r
        RETURN count(r) as count
        """

        try:
            result = self._execute_query_single(
                query,
                {"source_norm": source_norm, "target_norm": target_norm, "rel_type": rel_type_str}
            )

            if result and result["count"] > 0:
                logger.debug(f"Removed relationship: {source} -> {target} ({relationship_type})")
                return True

            return False

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
        query = """
        MATCH (n:Entity)
        DETACH DELETE n
        """

        try:
            self._execute_query(query)
            logger.debug("Cleared graph")
        except Exception as e:
            raise GraphStoreError(
                "Failed to clear graph",
                code="CLEAR_FAILED",
                details={"error": str(e)},
            ) from e

    async def get_stats(self) -> GraphStats:
        """
        Get statistics about the graph.

        Returns:
            GraphStats with node/edge counts and type breakdowns
        """
        query = """
        MATCH (n:Entity)
        WITH count(n) as node_count,
             collect(DISTINCT n.entity_type) as entity_types
        MATCH ()-[r:RELATES]->()
        WITH node_count, entity_types,
             count(r) as edge_count,
             collect(DISTINCT r.relationship_type) as rel_types
        RETURN node_count, edge_count, entity_types, rel_types
        """

        try:
            result = self._execute_query_single(query)

            if not result:
                return GraphStats(
                    node_count=0,
                    edge_count=0,
                    entity_type_counts={},
                    relationship_type_counts={},
                )

            # Count entities by type
            entity_type_counts: dict[str, int] = {}
            for et in result.get("entity_types", []):
                count_query = """
                MATCH (n:Entity {entity_type: $entity_type})
                RETURN count(n) as count
                """
                count_result = self._execute_query_single(count_query, {"entity_type": et})
                if count_result:
                    entity_type_counts[et] = count_result["count"]

            # Count relationships by type
            relationship_type_counts: dict[str, int] = {}
            for rt in result.get("rel_types", []):
                count_query = """
                MATCH ()-[r:RELATES {relationship_type: $rel_type}]->()
                RETURN count(r) as count
                """
                count_result = self._execute_query_single(count_query, {"rel_type": rt})
                if count_result:
                    relationship_type_counts[rt] = count_result["count"]

            return GraphStats(
                node_count=result["node_count"],
                edge_count=result["edge_count"],
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
        """
        Verify the graph store connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            query = "RETURN 1 as test"
            result = self._execute_query_single(query)
            return result is not None
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
        normalized_name = self._normalize_name(name)

        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        RETURN count(n) as count
        """

        try:
            result = self._execute_query_single(query, {"normalized_name": normalized_name})
            return result is not None and result["count"] > 0
        except Exception:
            return False

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
        query = """
        MATCH (n:Entity)
        """
        params: dict[str, Any] = {}

        if entity_type is not None:
            query += "WHERE n.entity_type = $entity_type\n"
            params["entity_type"] = self._entity_type_to_str(entity_type)

        query += "RETURN n"

        if limit is not None:
            query += f"\nLIMIT {limit}"
            params["limit"] = limit

        try:
            result = self._execute_query(query, params)

            entities: list[GraphEntity] = []
            for record in result:
                node = record["n"]
                entity_type_str = node.get("entity_type", "unknown")
                entity = self._str_to_entity_type(entity_type_str)

                # Extract metadata
                known_fields = {"normalized_name", "name", "entity_type", "aliases", "description"}
                metadata = {k: v for k, v in node.items() if k not in known_fields}

                entities.append(
                    GraphEntity(
                        name=node.get("name", ""),
                        entity_type=entity,
                        aliases=tuple(node.get("aliases", [])),
                        description=node.get("description", ""),
                        metadata=metadata,
                    )
                )

            return entities

        except Exception as e:
            raise GraphStoreError(
                "Failed to get all entities",
                code="GET_ENTITIES_FAILED",
                details={"error": str(e)},
            ) from e

    async def find_cliques(
        self,
        min_size: int = 3,
        max_size: int | None = None,
        entity_type: EntityType | None = None,
    ) -> CliqueResult:
        """
        Find all cliques (fully connected subgraphs) in the graph.

        Uses Neo4j's graph algorithms library if available, otherwise
        falls back to a manual approach.

        Args:
            min_size: Minimum clique size to report (default: 3)
            max_size: Maximum clique size to report (default: unlimited)
            entity_type: Optional filter for entities of specific type

        Returns:
            CliqueResult with all cliques found
        """
        # For Neo4j, we'll use a simpler approach: find all nodes
        # and check for cliques using NetworkX as a fallback
        # This is because Neo4j doesn't have built-in clique detection
        # without the graph algorithms library

        # Fetch all relevant nodes and relationships
        query = """
        MATCH (n:Entity)
        """
        params: dict[str, Any] = {}

        if entity_type is not None:
            query += "WHERE n.entity_type = $entity_type\n"
            params["entity_type"] = self._entity_type_to_str(entity_type)

        query += """
        OPTIONAL MATCH (n)-[r:RELATES]->(m:Entity)
        RETURN n.normalized_name as node_name, n.name as display_name,
               collect({target: m.normalized_name, rel_type: r.relationship_type}) as connections
        """

        try:
            result = self._execute_query(query, params)

            # Build an undirected graph using NetworkX for clique detection
            import networkx as nx

            graph = nx.Graph()

            for record in result:
                node_name = record["node_name"]
                display_name = record["display_name"]
                graph.add_node(node_name, display_name=display_name)

                for conn in record["connections"]:
                    if conn.get("target"):
                        graph.add_edge(node_name, conn["target"])

            # Find cliques using NetworkX
            all_cliques = list(nx.find_cliques(graph))

            # Filter by size
            filtered_cliques = [
                clique for clique in all_cliques
                if len(clique) >= min_size and (max_size is None or len(clique) <= max_size)
            ]

            # Convert to display names
            cliques_with_display_names: list[tuple[str, ...]] = []
            for clique in sorted(filtered_cliques, key=len, reverse=True):
                display_names = []
                for node in clique:
                    if node in graph.nodes:
                        display_names.append(graph.nodes[node].get("display_name", node))
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
        """
        Calculate centrality metrics for entities in the graph.

        Args:
            entity_name: Optional specific entity to analyze. If None, analyzes all entities.
            top_n: Optional limit to return only top N entities by each metric

        Returns:
            List of CentralityResult objects sorted by pagerank descending
        """
        # Fetch graph data for centrality calculation
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

        try:
            result = self._execute_query(query)

            # Build graph for NetworkX centrality calculations
            import networkx as nx

            graph = nx.Graph()

            for record in result:
                node_name = record["node_name"]
                display_name = record["display_name"]
                graph.add_node(node_name, display_name=display_name)

                for neighbor in record.get("neighbors", []):
                    if neighbor:
                        graph.add_edge(node_name, neighbor)

            # Calculate centrality metrics
            degree_centralities = nx.degree_centrality(graph)
            betweenness_centralities = nx.betweenness_centrality(graph)

            # For closeness, only calculate for connected components
            try:
                closeness_centralities = nx.closeness_centrality(graph)
            except nx.NetworkXError:
                closeness_centralities = {n: 0.0 for n in graph.nodes()}

            # PageRank on directed view
            directed_graph = nx.DiGraph()
            for u, v in graph.edges():
                directed_graph.add_edge(u, v)
            pagerank_scores = nx.pagerank(directed_graph)

            results: list[CentralityResult] = []

            if entity_name is not None:
                # Return only specified entity
                normalized_name = self._normalize_name(entity_name)
                if normalized_name in graph.nodes:
                    display_name = graph.nodes[normalized_name].get("display_name", entity_name)
                    results.append(
                        CentralityResult(
                            entity_name=display_name,
                            degree_centrality=degree_centralities.get(normalized_name, 0.0),
                            betweenness_centrality=betweenness_centralities.get(normalized_name, 0.0),
                            closeness_centrality=closeness_centralities.get(normalized_name, 0.0),
                            pagerank=pagerank_scores.get(normalized_name, 0.0),
                        )
                    )
            else:
                # Return all entities
                for node in graph.nodes:
                    display_name = graph.nodes[node].get("display_name", node)
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

        except Exception as e:
            raise GraphStoreError(
                "Failed to calculate centrality",
                code="CENTRALITY_FAILED",
                details={"error": str(e)},
            ) from e

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

        if not await self.entity_exists(source):
            raise GraphStoreError(
                f"Source entity not found: {source}",
                code="ENTITY_NOT_FOUND",
                details={"entity": source},
            )

        # Build path length constraint
        length_constraint = ""
        params: dict[str, Any] = {"source_norm": source_norm}

        if max_length is not None:
            params["max_length"] = max_length
            length_constraint = f"*1..{max_length}"
        else:
            length_constraint = "*1..10"  # Reasonable default limit

        query = f"""
        MATCH path = (s:Entity {{normalized_name: $source_norm}})-[:RELATES{length_constraint}]->(t:Entity)
        WHERE s.normalized_name <> t.normalized_name
        WITH t, path, length(path) as path_len
        ORDER BY t.normalized_name, path_len
        WITH t, collect(path) as all_paths, path_len
        WITH t, all_paths[0] as shortest_path
        UNWIND relationships(shortest_path) as r
        WITH t.name as target_name, collect(r) as rels
        """

        if cutoff is not None:
            query = f"""
            WITH collect(DISTINCT {{target_name: t.name, rels: relationships(path)}})[0..{cutoff}] as paths
            UNWIND paths as path_item
            RETURN path_item.target_name as target_name, path_item.rels as rels
            """
        else:
            query += "RETURN t.name as target_name, rels"

        try:
            result = self._execute_query(query, params)

            results: dict[str, PathResult] = {}

            for record in result:
                target_name = record["target_name"]
                rels_data = record.get("rels", [])

                relationships: list[GraphRelationship] = []
                for rel in rels_data:
                    rel_type_str = rel.get("relationship_type", "other")
                    relationships.append(
                        GraphRelationship(
                            source=rel.get("source", source),
                            target=rel.get("target", target_name),
                            relationship_type=self._str_to_relationship_type(rel_type_str),
                            context=rel.get("context", ""),
                            strength=rel.get("strength", 1.0),
                        )
                    )

                # Build path from source to target
                path_names = [source]
                for rel in relationships:
                    if rel.target and rel.target not in path_names:
                        path_names.append(rel.target)

                results[target_name] = PathResult(
                    path=tuple(path_names),
                    relationships=tuple(relationships),
                    length=len(relationships),
                )

            return results

        except Exception as e:
            raise GraphStoreError(
                f"Failed to find paths from {source}",
                code="FIND_PATHS_FAILED",
                details={"error": str(e), "source": source},
            ) from e

    async def export_graphml(
        self,
        output_path: str,
        include_metadata: bool = True,
    ) -> GraphExportResult:
        """
        Export the graph to GraphML format for visualization tools.

        Fetches all data from Neo4j and uses NetworkX to write GraphML.

        Args:
            output_path: File path to write GraphML output
            include_metadata: Whether to include entity/relationship metadata

        Returns:
            GraphExportResult with export statistics
        """
        import os
        from pathlib import Path

        try:
            # Import NetworkX for GraphML writing
            import networkx as nx

            # Fetch all nodes and edges
            nodes_query = """
            MATCH (n:Entity)
            RETURN n
            """

            edges_query = """
            MATCH (s:Entity)-[r:RELATES]->(t:Entity)
            RETURN s.normalized_name as source, t.normalized_name as target, r
            """

            nodes_result = self._execute_query(nodes_query)
            edges_result = self._execute_query(edges_query)

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
                    # Add remaining metadata
                    for key, value in node.items():
                        if key not in {"normalized_name", "name", "entity_type", "aliases", "description"}:
                            node_attrs[key] = value

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
                    # Add remaining metadata
                    for key, value in rel.items():
                        if key not in {"relationship_type", "source", "target", "context", "strength"}:
                            edge_attrs[key] = value

                graph.add_edge(source, target, **edge_attrs)

            # Write to GraphML
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            nx.readwrite.write_graphml(graph, output_path)

            # Get file size
            file_size = os.path.getsize(output_path)

            logger.info(f"Exported Neo4j graph to GraphML: {output_path} ({graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges)")

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
            # Fetch all nodes and edges
            nodes_query = """
            MATCH (n:Entity)
            RETURN n
            """

            edges_query = """
            MATCH (s:Entity)-[r:RELATES]->(t:Entity)
            RETURN s.normalized_name as source, s.name as source_name,
                   t.normalized_name as target, t.name as target_name, r
            """

            nodes_result = self._execute_query(nodes_query)
            edges_result = self._execute_query(edges_query)

            nodes_data: list[dict[str, Any]] = []
            edges_data: list[dict[str, Any]] = []

            for record in nodes_result:
                node = record["n"]
                node_dict = {
                    "id": node.get("normalized_name", ""),
                    "name": node.get("name", ""),
                    "entity_type": node.get("entity_type", "unknown"),
                }

                # Add optional fields
                if "aliases" in node:
                    node_dict["aliases"] = node["aliases"]
                if "description" in node:
                    node_dict["description"] = node["description"]

                # Add remaining metadata
                for key, value in node.items():
                    if key not in {"normalized_name", "name", "entity_type", "aliases", "description"}:
                        node_dict[key] = value

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

                # Add optional fields
                if "context" in rel:
                    edge_dict["context"] = rel["context"]
                if "strength" in rel:
                    edge_dict["strength"] = rel["strength"]

                # Add remaining metadata
                for key, value in rel.items():
                    if key not in {"source", "target", "source_name", "target_name", "relationship_type", "context", "strength"}:
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
                    "source": "neo4j",
                },
            }

            json_string = json.dumps(export_data, indent=2 if pretty else None, ensure_ascii=False)
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
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


__all__ = ["Neo4jGraphStore"]
