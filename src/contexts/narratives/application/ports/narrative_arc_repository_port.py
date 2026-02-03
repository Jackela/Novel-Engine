#!/usr/bin/env python3
"""
Narrative Arc Repository Port (Interface)

Defines the abstract interface for narrative arc persistence operations.
This port belongs to the application layer and is implemented by the
infrastructure layer.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from ...domain.aggregates.narrative_arc import NarrativeArc
from ...domain.value_objects.narrative_id import NarrativeId


class INarrativeArcRepository(ABC):
    """
    Abstract repository interface for narrative arc persistence operations.

    Defines the contract for narrative arc data access without specifying
    implementation details.
    """

    @abstractmethod
    def save(self, narrative_arc: NarrativeArc) -> None:
        """
        Save a narrative arc.

        Args:
            narrative_arc: NarrativeArc aggregate to save
        """

    @abstractmethod
    def get_by_id(self, arc_id: NarrativeId) -> Optional[NarrativeArc]:
        """
        Get a narrative arc by ID.

        Args:
            arc_id: NarrativeId to search for

        Returns:
            NarrativeArc if found, None otherwise
        """

    @abstractmethod
    def get_by_type(
        self,
        arc_type: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[NarrativeArc]:
        """
        Get narrative arcs by type.

        Args:
            arc_type: Type of narrative arc
            status: Optional status filter
            limit: Optional limit for results
            offset: Optional offset for pagination

        Returns:
            List of matching NarrativeArc objects
        """

    @abstractmethod
    def search(
        self,
        search_term: Optional[str] = None,
        arc_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        character_ids: Optional[List[UUID]] = None,
        theme_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
        min_complexity: Optional[Decimal] = None,
        max_complexity: Optional[Decimal] = None,
        min_completion: Optional[Decimal] = None,
        max_completion: Optional[Decimal] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        sort_by: Optional[str] = "updated_at",
        sort_order: str = "desc",
    ) -> Tuple[List[NarrativeArc], int]:
        """
        Search narrative arcs with various criteria.

        Returns:
            Tuple of (matching arcs, total count)
        """

    @abstractmethod
    def delete(self, arc_id: NarrativeId) -> bool:
        """
        Delete a narrative arc by ID.

        Args:
            arc_id: NarrativeId of arc to delete

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    def exists(self, arc_id: NarrativeId) -> bool:
        """
        Check if a narrative arc exists.

        Args:
            arc_id: NarrativeId to check

        Returns:
            True if exists, False otherwise
        """
