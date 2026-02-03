#!/usr/bin/env python3
"""Relationship Repository Interface.

This module defines the abstract repository interface for Relationship entities.
Following DDD principles, the domain layer defines the contract while the
infrastructure layer provides concrete implementations.

Why a separate repository: Relationships are frequent queries in knowledge
graphs. A dedicated repository enables optimized queries by entity, type,
and relationship characteristics without coupling to WorldState aggregates.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.relationship import EntityType, Relationship, RelationshipType


class IRelationshipRepository(ABC):
    """Abstract repository interface for Relationship entities.

    This interface defines the contract for persisting and querying
    Relationship entities. The design optimizes for graph-like queries
    that are common in World Knowledge Graph operations.

    Thread Safety:
        Implementations should be thread-safe for concurrent access.
    """

    # Basic CRUD Operations

    @abstractmethod
    async def save(self, relationship: Relationship) -> Relationship:
        """Save a Relationship to persistent storage.

        Handles both create and update operations based on whether
        the relationship already exists.

        Args:
            relationship: The Relationship to save.

        Returns:
            The saved Relationship (may include generated IDs).

        Raises:
            RepositoryException: If save operation fails.
        """

    @abstractmethod
    async def get_by_id(self, relationship_id: str) -> Optional[Relationship]:
        """Retrieve a Relationship by its unique identifier.

        Args:
            relationship_id: Unique identifier for the relationship.

        Returns:
            Relationship if found, None otherwise.
        """

    @abstractmethod
    async def delete(self, relationship_id: str) -> bool:
        """Delete a Relationship from persistent storage.

        Args:
            relationship_id: Unique identifier for the relationship.

        Returns:
            True if deletion was successful, False if not found.
        """

    @abstractmethod
    async def exists(self, relationship_id: str) -> bool:
        """Check if a Relationship exists in storage.

        Args:
            relationship_id: Unique identifier for the relationship.

        Returns:
            True if relationship exists, False otherwise.
        """

    # Entity-centric Queries

    @abstractmethod
    async def find_by_entity(
        self,
        entity_id: str,
        entity_type: Optional[EntityType] = None,
        include_inactive: bool = False,
    ) -> List[Relationship]:
        """Find all relationships involving a specific entity.

        This is the primary query method for building relationship graphs.
        Returns relationships where the entity is either source or target.

        Args:
            entity_id: ID of the entity to find relationships for.
            entity_type: Optional filter by entity type.
            include_inactive: Whether to include inactive (historical) relationships.

        Returns:
            List of Relationships involving the entity.
        """

    @abstractmethod
    async def find_by_source(
        self,
        source_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships where the entity is the source.

        Useful for directional queries like "who does X mentor?"

        Args:
            source_id: ID of the source entity.
            relationship_type: Optional filter by relationship type.

        Returns:
            List of Relationships with the specified source.
        """

    @abstractmethod
    async def find_by_target(
        self,
        target_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships where the entity is the target.

        Useful for directional queries like "who are X's members?"

        Args:
            target_id: ID of the target entity.
            relationship_type: Optional filter by relationship type.

        Returns:
            List of Relationships with the specified target.
        """

    @abstractmethod
    async def find_between(
        self,
        entity_a_id: str,
        entity_b_id: str,
    ) -> List[Relationship]:
        """Find all relationships between two specific entities.

        Checks both directions (A->B and B->A).

        Args:
            entity_a_id: ID of the first entity.
            entity_b_id: ID of the second entity.

        Returns:
            List of Relationships connecting the two entities.
        """

    # Type-based Queries

    @abstractmethod
    async def find_by_type(
        self,
        relationship_type: RelationshipType,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """Find relationships by type.

        Useful for queries like "show all enemies" or "show all family ties."

        Args:
            relationship_type: Type of relationships to find.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Relationships of the specified type.
        """

    @abstractmethod
    async def find_by_entity_types(
        self,
        source_type: EntityType,
        target_type: EntityType,
        relationship_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """Find relationships between specific entity type pairs.

        Useful for queries like "find all character-to-faction memberships."

        Args:
            source_type: Type of source entity.
            target_type: Type of target entity.
            relationship_type: Optional filter by relationship type.

        Returns:
            List of matching Relationships.
        """

    # Strength-based Queries

    @abstractmethod
    async def find_strong_relationships(
        self,
        entity_id: str,
        min_strength: int = 75,
    ) -> List[Relationship]:
        """Find strong relationships for an entity.

        Useful for finding an entity's most significant connections.

        Args:
            entity_id: ID of the entity.
            min_strength: Minimum strength threshold (default 75).

        Returns:
            List of Relationships meeting the strength threshold.
        """

    # Utility Methods

    @abstractmethod
    async def count_by_entity(self, entity_id: str) -> int:
        """Count relationships for an entity.

        Args:
            entity_id: ID of the entity.

        Returns:
            Number of relationships involving the entity.
        """

    @abstractmethod
    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Relationship]:
        """Get all relationships with pagination.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of Relationships.
        """


class RelationshipRepositoryException(Exception):
    """Base exception for relationship repository operations."""


class RelationshipNotFoundException(RelationshipRepositoryException):
    """Raised when a requested relationship is not found."""

    def __init__(self, relationship_id: str):
        super().__init__(f"Relationship not found: {relationship_id}")
        self.relationship_id = relationship_id


class DuplicateRelationshipException(RelationshipRepositoryException):
    """Raised when attempting to create a duplicate relationship."""

    def __init__(self, source_id: str, target_id: str, relationship_type: str):
        super().__init__(
            f"Relationship already exists: {source_id} -> {target_id} ({relationship_type})"
        )
        self.source_id = source_id
        self.target_id = target_id
        self.relationship_type = relationship_type
