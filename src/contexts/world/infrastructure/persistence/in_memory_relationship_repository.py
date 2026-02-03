#!/usr/bin/env python3
"""In-Memory Relationship Repository Implementation.

This module provides an in-memory implementation of IRelationshipRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

from typing import Dict, List, Optional

from src.contexts.world.domain.entities.relationship import (
    EntityType,
    Relationship,
    RelationshipType,
)
from src.contexts.world.domain.repositories.relationship_repository import (
    IRelationshipRepository,
)


class InMemoryRelationshipRepository(IRelationshipRepository):
    """In-memory implementation of IRelationshipRepository.

    Stores relationships in a dictionary indexed by ID, with additional
    indexes for efficient entity-based lookups.

    Thread Safety:
        This implementation is NOT thread-safe. For concurrent access,
        use locking or switch to a thread-safe implementation.
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage."""
        self._relationships: Dict[str, Relationship] = {}
        # Index: entity_id -> set of relationship_ids
        self._entity_index: Dict[str, set] = {}

    def _index_relationship(self, relationship: Relationship) -> None:
        """Add relationship to entity indexes.

        Args:
            relationship: The relationship to index.
        """
        for entity_id in (relationship.source_id, relationship.target_id):
            if entity_id not in self._entity_index:
                self._entity_index[entity_id] = set()
            self._entity_index[entity_id].add(relationship.id)

    def _unindex_relationship(self, relationship: Relationship) -> None:
        """Remove relationship from entity indexes.

        Args:
            relationship: The relationship to unindex.
        """
        for entity_id in (relationship.source_id, relationship.target_id):
            if entity_id in self._entity_index:
                self._entity_index[entity_id].discard(relationship.id)
                if not self._entity_index[entity_id]:
                    del self._entity_index[entity_id]

    async def save(self, relationship: Relationship) -> Relationship:
        """Save a Relationship to storage.

        Args:
            relationship: The Relationship to save.

        Returns:
            The saved Relationship.
        """
        existing = self._relationships.get(relationship.id)
        if existing:
            # Update: unindex old, index new
            self._unindex_relationship(existing)

        self._relationships[relationship.id] = relationship
        self._index_relationship(relationship)
        return relationship

    async def get_by_id(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a Relationship by ID.

        Args:
            relationship_id: Unique identifier.

        Returns:
            Relationship if found, None otherwise.
        """
        return self._relationships.get(relationship_id)

    async def delete(self, relationship_id: str) -> bool:
        """Delete a Relationship.

        Args:
            relationship_id: Unique identifier.

        Returns:
            True if deleted, False if not found.
        """
        relationship = self._relationships.get(relationship_id)
        if relationship:
            self._unindex_relationship(relationship)
            del self._relationships[relationship_id]
            return True
        return False

    async def exists(self, relationship_id: str) -> bool:
        """Check if a Relationship exists.

        Args:
            relationship_id: Unique identifier.

        Returns:
            True if exists.
        """
        return relationship_id in self._relationships

    async def find_by_entity(
        self,
        entity_id: str,
        entity_type: Optional[EntityType] = None,
        include_inactive: bool = False,
    ) -> List[Relationship]:
        """Find relationships involving an entity.

        Args:
            entity_id: ID of the entity.
            entity_type: Optional type filter.
            include_inactive: Include inactive relationships.

        Returns:
            List of matching Relationships.
        """
        relationship_ids = self._entity_index.get(entity_id, set())
        results = []

        for rel_id in relationship_ids:
            rel = self._relationships.get(rel_id)
            if not rel:
                continue

            # Filter inactive
            if not include_inactive and not rel.is_active:
                continue

            # Filter by entity type if specified
            if entity_type:
                if rel.source_id == entity_id and rel.source_type != entity_type:
                    continue
                if rel.target_id == entity_id and rel.target_type != entity_type:
                    continue

            results.append(rel)

        return results

    async def find_by_source(
        self,
        source_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships by source entity.

        Args:
            source_id: ID of source entity.
            relationship_type: Optional type filter.

        Returns:
            List of matching Relationships.
        """
        results = []
        for rel in self._relationships.values():
            if rel.source_id != source_id:
                continue
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            if rel.is_active:
                results.append(rel)
        return results

    async def find_by_target(
        self,
        target_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships by target entity.

        Args:
            target_id: ID of target entity.
            relationship_type: Optional type filter.

        Returns:
            List of matching Relationships.
        """
        results = []
        for rel in self._relationships.values():
            if rel.target_id != target_id:
                continue
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            if rel.is_active:
                results.append(rel)
        return results

    async def find_between(
        self,
        entity_a_id: str,
        entity_b_id: str,
    ) -> List[Relationship]:
        """Find relationships between two entities.

        Args:
            entity_a_id: First entity ID.
            entity_b_id: Second entity ID.

        Returns:
            List of Relationships connecting the entities.
        """
        results = []
        for rel in self._relationships.values():
            if (rel.source_id == entity_a_id and rel.target_id == entity_b_id) or (
                rel.source_id == entity_b_id and rel.target_id == entity_a_id
            ):
                if rel.is_active:
                    results.append(rel)
        return results

    async def find_by_type(
        self,
        relationship_type: RelationshipType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """Find relationships by type.

        Args:
            relationship_type: Type to filter by.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of matching Relationships.
        """
        results = [
            rel
            for rel in self._relationships.values()
            if rel.relationship_type == relationship_type and rel.is_active
        ]
        return results[offset : offset + limit]

    async def find_by_entity_types(
        self,
        source_type: EntityType,
        target_type: EntityType,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships between entity type pairs.

        Args:
            source_type: Source entity type.
            target_type: Target entity type.
            relationship_type: Optional relationship type filter.

        Returns:
            List of matching Relationships.
        """
        results = []
        for rel in self._relationships.values():
            if rel.source_type != source_type or rel.target_type != target_type:
                continue
            if relationship_type and rel.relationship_type != relationship_type:
                continue
            if rel.is_active:
                results.append(rel)
        return results

    async def find_strong_relationships(
        self,
        entity_id: str,
        min_strength: int = 75,
    ) -> List[Relationship]:
        """Find strong relationships for an entity.

        Args:
            entity_id: Entity ID.
            min_strength: Minimum strength threshold.

        Returns:
            List of strong Relationships.
        """
        relationships = await self.find_by_entity(entity_id, include_inactive=False)
        return [rel for rel in relationships if rel.strength >= min_strength]

    async def count_by_entity(self, entity_id: str) -> int:
        """Count relationships for an entity.

        Args:
            entity_id: Entity ID.

        Returns:
            Count of relationships.
        """
        relationships = await self.find_by_entity(entity_id, include_inactive=False)
        return len(relationships)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """Get all relationships with pagination.

        Args:
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            List of Relationships.
        """
        all_relationships = list(self._relationships.values())
        return all_relationships[offset : offset + limit]

    # Utility methods for testing

    def clear(self) -> None:
        """Clear all data from the repository."""
        self._relationships.clear()
        self._entity_index.clear()

    def count_all(self) -> int:
        """Get total count of relationships."""
        return len(self._relationships)
