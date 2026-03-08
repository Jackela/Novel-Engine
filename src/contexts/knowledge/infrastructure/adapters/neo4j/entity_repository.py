"""Entity Repository Module.

Manages entity (node) operations in Neo4j.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from src.contexts.knowledge.application.ports.i_graph_store import (
    GraphEntity,
    GraphStoreError,
)
from src.contexts.knowledge.domain.models.entity import EntityType

from .query_builder import QueryBuilder

if TYPE_CHECKING:
    from .connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)


class EntityRepository:
    """Repository for entity operations."""

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """Initialize with connection manager.

        Args:
            connection_manager: Neo4j connection manager
        """
        self._connection = connection_manager
        self._query = QueryBuilder()

    async def add(self, entity: GraphEntity) -> bool:
        """Add an entity to the graph.

        Args:
            entity: GraphEntity to add

        Returns:
            True if entity was added, False if it already existed
        """
        normalized_name = self._query.normalize_name(entity.name)

        # Check if entity already exists
        query, params = self._query.check_entity_exists(normalized_name)
        driver = self._connection.get_driver()

        with driver.session(database=self._connection._database) as session:
            result = session.run(query, params)
            record = result.single()

            if record and record["count"] > 0:
                logger.debug(f"Entity already exists: {entity.name}")
                return False

        try:
            # Build entity properties
            properties = {
                "normalized_name": normalized_name,
                "name": entity.name,
                "entity_type": self._query.entity_type_to_str(entity.entity_type),
                "aliases": list(entity.aliases),
                "description": entity.description,
            }
            properties.update(entity.metadata)

            # Create entity
            entity_type_label = self._query.entity_type_to_str(entity.entity_type)
            query, params = self._query.create_entity(properties, entity_type_label)

            with driver.session(database=self._connection._database) as session:
                session.run(query, params)

            logger.debug(f"Added entity: {entity.name} ({entity.entity_type})")
            return True

        except Exception as e:
            raise GraphStoreError(
                f"Failed to add entity {entity.name}",
                code="ADD_ENTITY_FAILED",
                details={"error": str(e), "entity": entity.name},
            ) from e

    async def get(self, name: str) -> Optional[GraphEntity]:
        """Get an entity by name.

        Args:
            name: Entity name to look up

        Returns:
            GraphEntity if found, None otherwise
        """
        normalized_name = self._query.normalize_name(name)
        query, params = self._query.get_entity(normalized_name)

        driver = self._connection.get_driver()

        with driver.session(database=self._connection._database) as session:
            result = session.run(query, params)
            record = result.single()

            if not record:
                return None

            try:
                node = record["n"]
                entity_type_str = node.get("entity_type", "unknown")
                entity_type = self._query.str_to_entity_type(entity_type_str)

                # Extract metadata
                known_fields = {
                    "normalized_name",
                    "name",
                    "entity_type",
                    "aliases",
                    "description",
                }
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

    async def exists(self, name: str) -> bool:
        """Check if an entity exists.

        Args:
            name: Entity name to check

        Returns:
            True if entity exists
        """
        normalized_name = self._query.normalize_name(name)
        query, params = self._query.check_entity_exists(normalized_name)

        driver = self._connection.get_driver()

        with driver.session(database=self._connection._database) as session:
            result = session.run(query, params)
            record = result.single()
            return record is not None and record["count"] > 0

    async def remove(self, name: str) -> bool:
        """Remove an entity and its relationships.

        Args:
            name: Entity name to remove

        Returns:
            True if entity was removed
        """
        normalized_name = self._query.normalize_name(name)
        query, params = self._query.delete_entity(normalized_name)

        driver = self._connection.get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)
                record = result.single()

                if record and record["count"] > 0:
                    logger.debug(f"Removed entity: {name}")
                    return True

                return False

        except Exception as e:
            raise GraphStoreError(
                f"Failed to remove entity {name}",
                code="REMOVE_ENTITY_FAILED",
                details={"error": str(e), "entity": name},
            ) from e

    async def get_all(
        self, entity_type: Optional[EntityType] = None, limit: Optional[int] = None
    ) -> List[GraphEntity]:
        """Get all entities.

        Args:
            entity_type: Optional filter for entity type
            limit: Optional maximum number to return

        Returns:
            List of GraphEntity objects
        """
        query, params = self._query.get_all_entities(entity_type, limit)

        driver = self._connection.get_driver()

        try:
            with driver.session(database=self._connection._database) as session:
                result = session.run(query, params)

                entities: List[GraphEntity] = []
                for record in result:
                    node = record["n"]
                    entity_type_str = node.get("entity_type", "unknown")
                    entity = self._query.str_to_entity_type(entity_type_str)

                    known_fields = {
                        "normalized_name",
                        "name",
                        "entity_type",
                        "aliases",
                        "description",
                    }
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


__all__ = ["EntityRepository"]
