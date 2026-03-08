"""Relationship Repository Module.

Manages relationship (edge) operations in Neo4j.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import structlog

from src.contexts.knowledge.application.ports.i_graph_store import (
    GraphRelationship,
    GraphStoreError,
)
from src.contexts.knowledge.domain.models.entity import RelationshipType

from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from .connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class RelationshipRepository:
    """Repository for relationship operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """Initialize with connection manager.

        Args:
            connection_manager: Neo4j connection manager
        """
        self._connection = connection_manager
        self._query = QueryBuilder()

    async def add(self, relationship: GraphRelationship) -> bool:
        """Add a relationship between two entities.

        Args:
            relationship: GraphRelationship to add

        Returns:
            True if relationship was added, False if it already existed
        """
        source_norm = self._query.normalize_name(relationship.source)
        target_norm = self._query.normalize_name(relationship.target)
        rel_type_str = self._query.relationship_type_to_str(
            relationship.relationship_type
        )

        driver = self._connection.get_driver()

        # Auto-create placeholder entities if they don't exist
        for norm_name, display_name in [
            (source_norm, relationship.source),
            (target_norm, relationship.target),
        ]:
            query, params = self._query.check_entity_exists(norm_name)
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)
                record = result.single()

                if not record or record["count"] == 0:
                    create_query = """
                    CREATE (n:Entity {normalized_name: $normalized_name, name: $name, entity_type: 'unknown'})
                    """
                    session.run(
                        create_query,
                        {"normalized_name": norm_name, "name": display_name},
                    )

        # Check if relationship already exists
        query, params = self._query.check_relationship_exists(
            source_norm, target_norm, rel_type_str
        )
        with driver.session(database=self._connection._database) as session:
            result = session.run(query, params)
            record = result.single()

            if record and record["count"] > 0:
                logger.debug(
                    f"Relationship already exists: {relationship.source} -> {relationship.target}"
                )
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

            query, params = self._query.create_relationship(
                source_norm, target_norm, properties
            )

            with driver.session(database=self._connection._database) as session:
                session.run(query, params)

            logger.debug(
                f"Added relationship: {relationship.source} -> {relationship.target}"
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
                },
            ) from e

    async def get_for_entity(
        self, entity_name: str, relationship_type: Optional[RelationshipType] = None
    ) -> List[GraphRelationship]:
        """Get all relationships for an entity.

        Args:
            entity_name: Name of the entity
            relationship_type: Optional filter for type

        Returns:
            List of GraphRelationship objects
        """
        rel_type_str = None
        if relationship_type is not None:
            rel_type_str = self._query.relationship_type_to_str(relationship_type)

        query, params = self._query.get_relationships(entity_name, rel_type_str)

        driver = self._connection.get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)

                relationships: List[GraphRelationship] = []
                for record in result:
                    rel = record["r"]
                    rel_type_str = rel.get("relationship_type", "other")
                    relationships.append(
                        GraphRelationship(
                            source=rel.get("source", entity_name),
                            target=rel.get("target", record["target_name"]),
                            relationship_type=self._query.str_to_relationship_type(
                                rel_type_str
                            ),
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

    async def get_between(
        self, source: str, target: str
    ) -> List[GraphRelationship]:
        """Get all relationships between two entities.

        Args:
            source: Source entity name
            target: Target entity name

        Returns:
            List of GraphRelationship objects
        """
        source_norm = self._query.normalize_name(source)
        target_norm = self._query.normalize_name(target)

        query, params = self._query.get_relationships_between(source_norm, target_norm)

        driver = self._connection.get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)

                relationships: List[GraphRelationship] = []
                for record in result:
                    rel = record["r"]
                    rel_type_str = rel.get("relationship_type", "other")
                    relationships.append(
                        GraphRelationship(
                            source=rel.get("source", source),
                            target=rel.get("target", target),
                            relationship_type=self._query.str_to_relationship_type(
                                rel_type_str
                            ),
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

    async def remove(
        self, source: str, target: str, relationship_type: RelationshipType
    ) -> bool:
        """Remove a specific relationship.

        Args:
            source: Source entity name
            target: Target entity name
            relationship_type: Type of relationship

        Returns:
            True if relationship was removed
        """
        source_norm = self._query.normalize_name(source)
        target_norm = self._query.normalize_name(target)
        rel_type_str = self._query.relationship_type_to_str(relationship_type)

        query, params = self._query.delete_relationship(
            source_norm, target_norm, rel_type_str
        )

        driver = self._connection.get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)
                record = result.single()

                if record and record["count"] > 0:
                    logger.debug(
                        f"Removed relationship: {source} -> {target} ({relationship_type})"
                    )
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


__all__ = ["RelationshipRepository"]
