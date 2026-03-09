"""Query Builder Module.

Builds Cypher queries with proper parameter binding.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.contexts.knowledge.domain.models.entity import EntityType, RelationshipType


class QueryBuilder:
    """Builds Cypher queries for graph operations."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize entity name for consistent storage."""
        return name.lower().strip()

    @staticmethod
    def entity_type_to_str(entity_type: EntityType | str) -> str:
        """Convert EntityType to string."""
        if isinstance(entity_type, str):
            return entity_type
        return entity_type.value  # type: ignore[unreachable]

    @staticmethod
    def str_to_entity_type(value: str) -> EntityType:
        """Convert string to EntityType."""
        try:
            return EntityType(value)
        except ValueError:
            return EntityType.CHARACTER

    @staticmethod
    def relationship_type_to_str(relationship_type: RelationshipType | str) -> str:
        """Convert RelationshipType to string."""
        if isinstance(relationship_type, str):
            return relationship_type
        return relationship_type.value  # type: ignore[unreachable]

    @staticmethod
    def str_to_relationship_type(value: str) -> RelationshipType:
        """Convert string to RelationshipType."""
        try:
            return RelationshipType(value)
        except ValueError:
            return RelationshipType.OTHER

    # Entity queries
    @staticmethod
    def check_entity_exists(normalized_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to check if entity exists."""
        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        RETURN count(n) as count
        """
        return query, {"normalized_name": normalized_name}

    @staticmethod
    def create_entity(
        properties: Dict[str, Any], entity_type_label: str
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to create entity."""
        query = f"""
        CREATE (n:Entity:{entity_type_label})
        SET n = $properties
        RETURN n
        """
        return query, {"properties": properties}

    @staticmethod
    def get_entity(normalized_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to get entity by name."""
        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        RETURN n
        """
        return query, {"normalized_name": normalized_name}

    @staticmethod
    def delete_entity(normalized_name: str) -> tuple[str, Dict[str, Any]]:
        """Build query to delete entity."""
        query = """
        MATCH (n:Entity {normalized_name: $normalized_name})
        DETACH DELETE n
        RETURN count(n) as count
        """
        return query, {"normalized_name": normalized_name}

    @staticmethod
    def get_all_entities(
        entity_type: Optional[EntityType] = None, limit: Optional[int] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to get all entities."""
        params: Dict[str, Any] = {}
        query = "MATCH (n:Entity)"

        if entity_type is not None:
            query += " WHERE n.entity_type = $entity_type"
            params["entity_type"] = QueryBuilder.entity_type_to_str(entity_type)

        query += " RETURN n"

        if limit is not None:
            query += f" LIMIT {limit}"

        return query, params

    # Relationship queries
    @staticmethod
    def check_relationship_exists(
        source_norm: str, target_norm: str, rel_type: str
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to check if relationship exists."""
        query = """
        MATCH (s:Entity {normalized_name: $source_norm})
        -[r:RELATES {relationship_type: $rel_type}]->
        (t:Entity {normalized_name: $target_norm})
        RETURN count(r) as count
        """
        return query, {
            "source_norm": source_norm,
            "target_norm": target_norm,
            "rel_type": rel_type,
        }

    @staticmethod
    def create_relationship(
        source_norm: str, target_norm: str, properties: Dict[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to create relationship."""
        query = """
        MATCH (s:Entity {normalized_name: $source_norm})
        MATCH (t:Entity {normalized_name: $target_norm})
        CREATE (s)-[r:RELATES]->(t)
        SET r = $properties
        RETURN r
        """
        return query, {
            "source_norm": source_norm,
            "target_norm": target_norm,
            "properties": properties,
        }

    @staticmethod
    def get_relationships(
        entity_name: str, rel_type: Optional[str] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to get relationships for an entity."""
        params: Dict[str, Any] = {
            "normalized_name": QueryBuilder.normalize_name(entity_name)
        }

        if rel_type is not None:
            query = """
            MATCH (e:Entity {normalized_name: $normalized_name})-[r:RELATES]->(t:Entity)
            WHERE r.relationship_type = $rel_type
            RETURN r, t.name as target_name
            """
            params["rel_type"] = rel_type
        else:
            query = """
            MATCH (e:Entity {normalized_name: $normalized_name})-[r:RELATES]->(t:Entity)
            RETURN r, t.name as target_name
            """

        return query, params

    @staticmethod
    def get_relationships_between(
        source_norm: str, target_norm: str
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to get relationships between two entities."""
        query = """
        MATCH (s:Entity {normalized_name: $source_norm})-[r:RELATES]->(t:Entity {normalized_name: $target_norm})
        RETURN r
        """
        return query, {"source_norm": source_norm, "target_norm": target_norm}

    @staticmethod
    def delete_relationship(
        source_norm: str, target_norm: str, rel_type: str
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to delete relationship."""
        query = """
        MATCH (s:Entity {normalized_name: $source_norm})-[r:RELATES {relationship_type: $rel_type}]->(t:Entity {normalized_name: $target_norm})
        DELETE r
        RETURN count(r) as count
        """
        return query, {
            "source_norm": source_norm,
            "target_norm": target_norm,
            "rel_type": rel_type,
        }

    # Path queries
    @staticmethod
    def find_path(
        source_norm: str, target_norm: str, max_length: Optional[int] = None
    ) -> tuple[str, Dict[str, Any]]:
        """Build query to find path between entities."""
        params: Dict[str, Any] = {
            "source_norm": source_norm,
            "target_norm": target_norm,
        }

        if max_length is not None:
            length_constraint = f"*1..{max_length}"
        else:
            length_constraint = "*1..15"

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

        return query, params

    # Stats queries
    @staticmethod
    def get_stats() -> tuple[str, Dict[str, Any]]:
        """Build query to get graph statistics."""
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
        return query, {}

    @staticmethod
    def count_entities_by_type(entity_type: str) -> tuple[str, Dict[str, Any]]:
        """Build query to count entities by type."""
        query = """
        MATCH (n:Entity {entity_type: $entity_type})
        RETURN count(n) as count
        """
        return query, {"entity_type": entity_type}

    @staticmethod
    def count_relationships_by_type(rel_type: str) -> tuple[str, Dict[str, Any]]:
        """Build query to count relationships by type."""
        query = """
        MATCH ()-[r:RELATES {relationship_type: $rel_type}]->()
        RETURN count(r) as count
        """
        return query, {"rel_type": rel_type}


__all__ = ["QueryBuilder"]
