#!/usr/bin/env python3
"""
Negotiation Session Repository Interface

This module defines the repository interface for NegotiationSession aggregates,
following the Repository pattern for domain-driven design.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..aggregates.negotiation_session import NegotiationSession
from ..value_objects.interaction_id import InteractionId


class NegotiationSessionRepository(ABC):
    """
    Abstract repository interface for NegotiationSession aggregates.

    Defines the contract for persistence operations while keeping the
    domain layer independent of infrastructure concerns.
    """

    @abstractmethod
    async def save(self, session: NegotiationSession) -> None:
        """
        Save or update a negotiation session.

        Args:
            session: The NegotiationSession aggregate to persist
        """
        pass

    @abstractmethod
    async def get_by_id(self, session_id: InteractionId) -> Optional[NegotiationSession]:
        """
        Retrieve a negotiation session by its unique identifier.

        Args:
            session_id: The unique identifier for the session

        Returns:
            The NegotiationSession if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_filters(
        self,
        filters: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> List[NegotiationSession]:
        """
        Find negotiation sessions matching the specified filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Field to order results by
            order_direction: Sort direction (asc/desc)

        Returns:
            List of matching NegotiationSession objects
        """
        pass

    @abstractmethod
    async def find_by_created_by(self, created_by: UUID) -> List[NegotiationSession]:
        """
        Find all negotiation sessions created by a specific user.

        Args:
            created_by: UUID of the user who created the sessions

        Returns:
            List of NegotiationSession objects created by the user
        """
        pass

    @abstractmethod
    async def find_by_participant(self, participant_id: UUID) -> List[NegotiationSession]:
        """
        Find all negotiation sessions where the specified entity is a participant.

        Args:
            participant_id: UUID of the participating entity

        Returns:
            List of NegotiationSession objects with the participant
        """
        pass

    @abstractmethod
    async def find_active_sessions(self) -> List[NegotiationSession]:
        """
        Find all currently active negotiation sessions.

        Returns:
            List of active NegotiationSession objects
        """
        pass

    @abstractmethod
    async def find_sessions_by_status(
        self, phase: Optional[str] = None, outcome: Optional[str] = None
    ) -> List[NegotiationSession]:
        """
        Find negotiation sessions by their status.

        Args:
            phase: Optional phase filter
            outcome: Optional outcome filter

        Returns:
            List of matching NegotiationSession objects
        """
        pass

    @abstractmethod
    async def find_sessions_by_domain(self, domain: str) -> List[NegotiationSession]:
        """
        Find negotiation sessions in a specific domain.

        Args:
            domain: The negotiation domain to filter by

        Returns:
            List of NegotiationSession objects in the domain
        """
        pass

    @abstractmethod
    async def find_sessions_by_type(self, session_type: str) -> List[NegotiationSession]:
        """
        Find negotiation sessions of a specific type.

        Args:
            session_type: The session type to filter by

        Returns:
            List of NegotiationSession objects of the specified type
        """
        pass

    @abstractmethod
    async def find_sessions_requiring_attention(
        self, hours_until_timeout: int = 24
    ) -> List[NegotiationSession]:
        """
        Find sessions that require attention (approaching timeout, stalled, etc.).

        Args:
            hours_until_timeout: Hours before timeout to consider "requiring attention"

        Returns:
            List of NegotiationSession objects requiring attention
        """
        pass

    @abstractmethod
    async def count_sessions_by_criteria(self, filters: Dict[str, Any]) -> int:
        """
        Count negotiation sessions matching the specified criteria.

        Args:
            filters: Dictionary of filter criteria

        Returns:
            Number of sessions matching the criteria
        """
        pass

    @abstractmethod
    async def delete(self, session_id: InteractionId) -> bool:
        """
        Delete a negotiation session.

        Args:
            session_id: The unique identifier for the session to delete

        Returns:
            True if the session was deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, session_id: InteractionId) -> bool:
        """
        Check if a negotiation session exists.

        Args:
            session_id: The unique identifier for the session

        Returns:
            True if the session exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_session_statistics(self) -> Dict[str, Any]:
        """
        Get statistical information about negotiation sessions.

        Returns:
            Dictionary containing session statistics
        """
        pass

    @abstractmethod
    async def find_sessions_by_date_range(
        self, start_date, end_date, date_field: str = "created_at"
    ) -> List[NegotiationSession]:
        """
        Find sessions within a specific date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range
            date_field: Field to filter by (created_at, updated_at, etc.)

        Returns:
            List of NegotiationSession objects within the date range
        """
        pass

    @abstractmethod
    async def batch_update_sessions(self, session_updates: List[Dict[str, Any]]) -> List[str]:
        """
        Perform batch updates on multiple sessions.

        Args:
            session_updates: List of update operations with session IDs and changes

        Returns:
            List of session IDs that were successfully updated
        """
        pass
