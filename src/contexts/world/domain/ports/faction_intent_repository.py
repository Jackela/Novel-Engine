#!/usr/bin/env python3
"""
FactionIntent Repository Port

This module defines the repository port (interface) for FactionIntent persistence.
Following Hexagonal Architecture, this port defines the contract that
infrastructure implementations must fulfill, keeping the domain layer
pure and independent of persistence details.

The FactionIntentRepository follows the Repository Pattern, providing an
abstraction for storing and retrieving FactionIntent entities.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)


class FactionIntentRepository(ABC):
    """
    Abstract repository port for FactionIntent persistence.

    This interface defines the contract for intent storage operations.
    Implementations can use different storage backends (in-memory, database, etc.)
    while the domain layer remains decoupled from infrastructure concerns.

    Key constraints enforced by implementations:
        - Maximum 10 active (non-terminated) intents per faction
        - Auto-expiry for old intents (7 in-game days)
        - Status tracking (PROPOSED, SELECTED, EXECUTED, REJECTED)
    """

    @abstractmethod
    def save(self, intent: FactionIntent) -> None:
        """
        Persist a faction intent.

        If an intent with the same id exists, it will be updated.
        Otherwise, a new intent is created.

        Args:
            intent: The FactionIntent to persist

        Example:
            >>> intent = FactionIntent(
            ...     faction_id="faction-1",
            ...     action_type=ActionType.EXPAND,
            ...     rationale="Expand into new territory"
            ... )
            >>> repository.save(intent)
        """
        pass

    @abstractmethod
    def save_batch(self, intents: List[FactionIntent]) -> None:
        """
        Persist multiple faction intents in a single operation.

        This is more efficient than calling save() multiple times,
        especially for database implementations that can batch inserts.

        Args:
            intents: List of FactionIntent objects to persist

        Example:
            >>> intents = [
            ...     FactionIntent(faction_id="f1", action_type=ActionType.EXPAND, ...),
            ...     FactionIntent(faction_id="f1", action_type=ActionType.TRADE, ...),
            ... ]
            >>> repository.save_batch(intents)
        """
        pass

    @abstractmethod
    def find_by_id(self, intent_id: str) -> Optional[FactionIntent]:
        """
        Retrieve a specific intent by its ID.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            FactionIntent if found, None otherwise

        Example:
            >>> intent = repository.find_by_id("intent-uuid")
            >>> if intent:
            ...     print(intent.rationale)
        """
        pass

    @abstractmethod
    def find_by_faction(
        self,
        faction_id: str,
        status: Optional[IntentStatus] = None,
    ) -> List[FactionIntent]:
        """
        Retrieve all intents for a specific faction.

        Args:
            faction_id: ID of the faction
            status: Optional filter by status (PROPOSED, SELECTED, EXECUTED, REJECTED)

        Returns:
            List of FactionIntent objects for the faction, sorted by
            priority (ascending, 1 = highest) then by creation time (descending)

        Example:
            >>> intents = repository.find_by_faction("faction-1")
            >>> proposed = repository.find_by_faction("faction-1", status=IntentStatus.PROPOSED)
        """
        pass

    @abstractmethod
    def find_active(self, faction_id: str) -> List[FactionIntent]:
        """
        Retrieve all active (PROPOSED or SELECTED) intents for a faction.

        Active intents are those that have not yet reached a terminal state
        (EXECUTED or REJECTED). This is a convenience method.

        Implementations enforce the max 10 active intents constraint.

        Args:
            faction_id: ID of the faction

        Returns:
            List of active FactionIntent objects (max 10)

        Example:
            >>> active_intents = repository.find_active("faction-1")
            >>> if len(active_intents) >= 10:
            ...     print("At capacity, need to select or expire")
        """
        pass

    @abstractmethod
    def delete(self, intent_id: str) -> bool:
        """
        Remove an intent from the repository.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if intent was deleted, False if it didn't exist

        Example:
            >>> deleted = repository.delete("intent-uuid")
            >>> if deleted:
            ...     print("Intent removed")
        """
        pass

    @abstractmethod
    def delete_by_faction(self, faction_id: str) -> int:
        """
        Remove all intents for a specific faction.

        Args:
            faction_id: ID of the faction

        Returns:
            Number of intents deleted

        Example:
            >>> count = repository.delete_by_faction("faction-1")
            >>> print(f"Removed {count} intents")
        """
        pass

    @abstractmethod
    def count_active(self, faction_id: str) -> int:
        """
        Count the number of active intents for a faction.

        Args:
            faction_id: ID of the faction

        Returns:
            Number of active intents (PROPOSED or SELECTED status)

        Example:
            >>> if repository.count_active("faction-1") < 10:
            ...     # Can generate more intents
            ...     pass
        """
        pass

    @abstractmethod
    def mark_selected(self, intent_id: str) -> bool:
        """
        Mark an intent as selected for execution.

        This updates the intent's status to SELECTED. Typically,
        only one intent per faction should be SELECTED at a time.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found or
            not in PROPOSED status

        Example:
            >>> success = repository.mark_selected("intent-uuid")
        """
        pass

    @abstractmethod
    def mark_executed(self, intent_id: str) -> bool:
        """
        Mark an intent as executed.

        This updates the intent's status to EXECUTED, indicating
        the action has been carried out.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found or
            not in SELECTED status

        Example:
            >>> success = repository.mark_executed("intent-uuid")
        """
        pass

    @abstractmethod
    def mark_rejected(self, intent_id: str) -> bool:
        """
        Mark an intent as rejected.

        This updates the intent's status to REJECTED, indicating
        the intent was discarded without execution.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found or
            already in a terminal state

        Example:
            >>> success = repository.mark_rejected("intent-uuid")
        """
        pass

    @abstractmethod
    def expire_old_intents(self, faction_id: str, max_age_days: int = 7) -> int:
        """
        Expire intents older than the specified age.

        This marks intents as REJECTED if they have been in PROPOSED
        status for longer than max_age_days.

        Args:
            faction_id: ID of the faction
            max_age_days: Maximum age in days before expiry (default 7)

        Returns:
            Number of intents expired

        Note:
            This method requires access to game time to calculate age.
            Implementations may use a time service or accept current_day.

        Example:
            >>> expired = repository.expire_old_intents("faction-1", max_age_days=7)
            >>> print(f"Expired {expired} old intents")
        """
        pass

    @abstractmethod
    def find_by_action_type(
        self,
        faction_id: str,
        action_type: ActionType,
    ) -> List[FactionIntent]:
        """
        Retrieve intents for a faction filtered by action type.

        Args:
            faction_id: ID of the faction
            action_type: The action type to filter by (EXPAND, ATTACK, etc.)

        Returns:
            List of matching FactionIntent objects

        Example:
            >>> attack_intents = repository.find_by_action_type(
            ...     "faction-1", ActionType.ATTACK
            ... )
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all intents from the repository.

        This is a utility method primarily used for testing.
        """
        pass

    @abstractmethod
    def find_by_faction_paginated(
        self,
        faction_id: str,
        status: Optional["IntentStatus"] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List["FactionIntent"], int, bool]:
        """
        Retrieve paginated intents for a faction.

        This method supports pagination for large intent histories,
        returning a subset of results along with total count and
        a flag indicating if more results exist.

        Args:
            faction_id: ID of the faction
            status: Optional filter by status (PROPOSED, SELECTED, EXECUTED, REJECTED)
            limit: Maximum number of intents to return (default 20, max 100)
            offset: Number of intents to skip for pagination

        Returns:
            Tuple of (list of intents, total count, has_more flag)

        Example:
            >>> intents, total, has_more = repository.find_by_faction_paginated(
            ...     "faction-1", limit=10, offset=0
            ... )
            >>> if has_more:
            ...     # Fetch next page
            ...     next_page, _, _ = repository.find_by_faction_paginated(
            ...         "faction-1", limit=10, offset=10
            ...     )
        """
        pass

    def can_add_intent(self, faction_id: str) -> bool:
        """
        Check if a faction can add a new active intent.

        Enforces the maximum 10 active intents per faction constraint.

        Args:
            faction_id: ID of the faction

        Returns:
            True if the faction can add a new intent, False otherwise

        Example:
            >>> if repository.can_add_intent("faction-1"):
            ...     repository.save(new_intent)
        """
        return self.count_active(faction_id) < 10
