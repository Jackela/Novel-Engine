#!/usr/bin/env python3
"""In-Memory FactionIntent Repository Implementation.

This module provides an in-memory implementation of FactionIntentRepository
suitable for testing, development, and lightweight deployments.

Why in-memory first: Enables rapid iteration and testing without database
setup. The repository interface ensures we can swap to PostgreSQL later
without changing domain or application code.
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional

import structlog

from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.contexts.world.domain.ports.faction_intent_repository import (
    FactionIntentRepository,
)

logger = structlog.get_logger()


class InMemoryFactionIntentRepository(FactionIntentRepository):
    """In-memory implementation of FactionIntentRepository.

    Stores intents in dictionaries indexed by intent_id and faction_id.
    Enforces constraints:
        - Maximum 10 active intents per faction
        - Auto-expiry for old intents (7 in-game days)

    Thread Safety:
        This implementation IS thread-safe. All operations are protected
        by a reentrant lock (RLock) to ensure safe concurrent access.

    Attributes:
        _intents: Dictionary mapping intent_id to FactionIntent
        _faction_intents: Dictionary mapping faction_id to set of intent_ids
        _lock: Reentrant lock for thread-safe access
    """

    MAX_ACTIVE_INTENTS = 10

    def __init__(self) -> None:
        """Initialize the repository with empty storage and thread lock."""
        self._intents: Dict[str, FactionIntent] = {}
        self._faction_intents: Dict[str, set[str]] = {}
        self._lock = threading.RLock()
        logger.debug("in_memory_faction_intent_repository_initialized")

    def save(self, intent: FactionIntent) -> None:
        """Persist a faction intent.

        If an intent with the same intent_id exists, it will be updated.
        Otherwise, a new intent is created. Enforces max active intents.

        Args:
            intent: The FactionIntent to persist
        """
        with self._lock:
            is_new = intent.id not in self._intents
            self._intents[intent.id] = intent

            # Update faction index
            if intent.faction_id not in self._faction_intents:
                self._faction_intents[intent.faction_id] = set()
            self._faction_intents[intent.faction_id].add(intent.id)

            # Enforce max active intents constraint
            if is_new and intent.status == IntentStatus.PROPOSED:
                self._enforce_max_active(intent.faction_id)

            logger.debug(
                "intent_saved",
                intent_id=intent.id,
                faction_id=intent.faction_id,
                action_type=intent.action_type.value,
                status=intent.status.value,
                is_new=is_new,
            )

    def save_batch(self, intents: List[FactionIntent]) -> None:
        """Persist multiple faction intents in a single operation.

        This implementation uses a single lock acquisition for all intents,
        which is more efficient than individual save() calls with lock overhead.
        Enforces max active intents constraint after all saves complete.

        Args:
            intents: List of FactionIntent objects to persist
        """
        if not intents:
            return

        with self._lock:
            faction_ids: set[str] = set()

            for intent in intents:
                is_new = intent.id not in self._intents
                self._intents[intent.id] = intent

                # Update faction index
                if intent.faction_id not in self._faction_intents:
                    self._faction_intents[intent.faction_id] = set()
                self._faction_intents[intent.faction_id].add(intent.id)
                faction_ids.add(intent.faction_id)

                logger.debug(
                    "intent_saved_in_batch",
                    intent_id=intent.id,
                    faction_id=intent.faction_id,
                    action_type=intent.action_type.value,
                    status=intent.status.value,
                    is_new=is_new,
                )

            # Enforce max active intents for all affected factions
            for faction_id in faction_ids:
                self._enforce_max_active(faction_id)

            logger.info(
                "intents_batch_saved",
                count=len(intents),
                factions_affected=list(faction_ids),
            )

    def _enforce_max_active(self, faction_id: str) -> None:
        """Enforce maximum active intents constraint.

        If faction has more than MAX_ACTIVE_INTENTS active (PROPOSED) intents,
        removes the oldest ones to maintain the limit.

        Args:
            faction_id: ID of the faction to check
        """
        active_intents = [
            self._intents[iid]
            for iid in self._faction_intents.get(faction_id, set())
            if iid in self._intents
            and self._intents[iid].status == IntentStatus.PROPOSED
        ]

        if len(active_intents) > self.MAX_ACTIVE_INTENTS:
            # Sort by creation time ascending (oldest first)
            active_intents.sort(key=lambda i: i.created_at)

            # Remove oldest intents beyond the limit
            to_remove = active_intents[: len(active_intents) - self.MAX_ACTIVE_INTENTS]
            for intent in to_remove:
                intent.reject()  # Mark as rejected instead of deleting
                logger.info(
                    "intent_auto_rejected",
                    intent_id=intent.id,
                    faction_id=faction_id,
                    reason="max_active_exceeded",
                )

    def find_by_id(self, intent_id: str) -> Optional[FactionIntent]:
        """Retrieve a specific intent by its ID.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            FactionIntent if found, None otherwise
        """
        with self._lock:
            return self._intents.get(intent_id)

    def find_by_faction(
        self,
        faction_id: str,
        status: Optional[IntentStatus] = None,
    ) -> List[FactionIntent]:
        """Retrieve all intents for a specific faction.

        Args:
            faction_id: ID of the faction
            status: Optional filter by status (PROPOSED, SELECTED, etc.)

        Returns:
            List of FactionIntent objects for the faction, sorted by
            priority (descending) then by creation time (descending)
        """
        with self._lock:
            intent_ids = self._faction_intents.get(faction_id, set())
            intents = [self._intents[iid] for iid in intent_ids if iid in self._intents]

            # Filter by status if provided
            if status:
                intents = [i for i in intents if i.status == status]

            # Sort by priority descending, then creation time descending
            intents.sort(key=lambda i: (-i.priority, -i.created_at.timestamp()))
            return intents

    def find_active(self, faction_id: str) -> List[FactionIntent]:
        """Retrieve all active (PROPOSED or SELECTED) intents for a faction.

        Active intents are those that have not yet reached a terminal state
        (EXECUTED or REJECTED). This is a convenience method.

        Args:
            faction_id: ID of the faction

        Returns:
            List of active FactionIntent objects (max 10)
        """
        with self._lock:
            intent_ids = self._faction_intents.get(faction_id, set())
            intents = [
                self._intents[iid]
                for iid in intent_ids
                if iid in self._intents and self._intents[iid].is_active
            ]

            # Sort by priority (ascending, 1 = highest), then creation time (descending)
            intents.sort(key=lambda i: (i.priority, -i.created_at.timestamp()))
            return intents[: self.MAX_ACTIVE_INTENTS]

    def delete(self, intent_id: str) -> bool:
        """Remove an intent from the repository.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if intent was deleted, False if it didn't exist
        """
        with self._lock:
            intent = self._intents.get(intent_id)
            if intent is None:
                return False

            del self._intents[intent_id]

            # Remove from faction index
            if intent.faction_id in self._faction_intents:
                self._faction_intents[intent.faction_id].discard(intent_id)
                if not self._faction_intents[intent.faction_id]:
                    del self._faction_intents[intent.faction_id]

            logger.debug("intent_deleted", intent_id=intent_id)
            return True

    def delete_by_faction(self, faction_id: str) -> int:
        """Remove all intents for a specific faction.

        Args:
            faction_id: ID of the faction

        Returns:
            Number of intents deleted
        """
        with self._lock:
            intent_ids = list(self._faction_intents.get(faction_id, set()))
            count = 0

            for intent_id in intent_ids:
                if intent_id in self._intents:
                    del self._intents[intent_id]
                    count += 1

            if faction_id in self._faction_intents:
                del self._faction_intents[faction_id]

            logger.debug(
                "intents_deleted_by_faction",
                faction_id=faction_id,
                count=count,
            )
            return count

    def count_active(self, faction_id: str) -> int:
        """Count the number of active intents for a faction.

        Args:
            faction_id: ID of the faction

        Returns:
            Number of active intents
        """
        with self._lock:
            intent_ids = self._faction_intents.get(faction_id, set())
            return sum(
                1
                for iid in intent_ids
                if iid in self._intents
                and self._intents[iid].status == IntentStatus.PROPOSED
            )

    def mark_selected(self, intent_id: str) -> bool:
        """Mark an intent as selected for execution.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found
        """
        with self._lock:
            intent = self._intents.get(intent_id)
            if intent is None:
                return False

            try:
                intent.select()
                logger.info(
                    "intent_marked_selected",
                    intent_id=intent_id,
                    faction_id=intent.faction_id,
                )
                return True
            except ValueError as e:
                logger.warning(
                    "intent_select_failed",
                    intent_id=intent_id,
                    error=str(e),
                )
                return False

    def mark_executed(self, intent_id: str) -> bool:
        """Mark an intent as executed.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found
        """
        with self._lock:
            intent = self._intents.get(intent_id)
            if intent is None:
                return False

            try:
                intent.execute()
                logger.info(
                    "intent_marked_executed",
                    intent_id=intent_id,
                    faction_id=intent.faction_id,
                )
                return True
            except ValueError as e:
                logger.warning(
                    "intent_execute_failed",
                    intent_id=intent_id,
                    error=str(e),
                )
                return False

    def mark_rejected(self, intent_id: str) -> bool:
        """Mark an intent as rejected.

        Args:
            intent_id: Unique identifier for the intent

        Returns:
            True if marked successfully, False if intent not found or
            already in a terminal state
        """
        with self._lock:
            intent = self._intents.get(intent_id)
            if intent is None:
                return False

            try:
                intent.reject()
                logger.info(
                    "intent_marked_rejected",
                    intent_id=intent_id,
                    faction_id=intent.faction_id,
                )
                return True
            except ValueError as e:
                logger.warning(
                    "intent_reject_failed",
                    intent_id=intent_id,
                    error=str(e),
                )
                return False

    def find_by_action_type(
        self,
        faction_id: str,
        action_type: ActionType,
    ) -> List[FactionIntent]:
        """Retrieve intents for a faction filtered by action type.

        Args:
            faction_id: ID of the faction
            action_type: The action type to filter by (EXPAND, ATTACK, etc.)

        Returns:
            List of matching FactionIntent objects
        """
        with self._lock:
            intent_ids = self._faction_intents.get(faction_id, set())
            intents = [
                self._intents[iid]
                for iid in intent_ids
                if iid in self._intents
                and self._intents[iid].action_type == action_type
            ]

            # Sort by priority descending, then creation time descending
            intents.sort(key=lambda i: (-i.priority, -i.created_at.timestamp()))
            return intents

    def expire_old_intents(self, faction_id: str, max_age_days: int = 7) -> int:
        """Expire intents older than the specified age.

        Note: This implementation uses real time (datetime.now) for expiry
        since we don't have access to game time. In a production system,
        this would accept current_game_day as a parameter.

        Args:
            faction_id: ID of the faction
            max_age_days: Maximum age in days before expiry (default 7)

        Returns:
            Number of intents expired
        """
        with self._lock:
            intent_ids = self._faction_intents.get(faction_id, set())
            now = datetime.now()
            expired_count = 0

            for iid in intent_ids:
                if iid not in self._intents:
                    continue

                intent = self._intents[iid]
                if intent.status != IntentStatus.PROPOSED:
                    continue

                age_days = (now - intent.created_at).days
                if age_days > max_age_days:
                    try:
                        intent.reject()
                        expired_count += 1
                        logger.info(
                            "intent_expired",
                            intent_id=iid,
                            faction_id=faction_id,
                            age_days=age_days,
                        )
                    except ValueError:
                        pass  # Already in terminal state

            return expired_count

    def clear(self) -> None:
        """Clear all intents from the repository.

        This is a utility method primarily used for testing.
        """
        with self._lock:
            self._intents.clear()
            self._faction_intents.clear()
            logger.debug("all_intents_cleared")

    def find_by_faction_paginated(
        self,
        faction_id: str,
        status: Optional[IntentStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[FactionIntent], int, bool]:
        """Retrieve paginated intents for a faction.

        Args:
            faction_id: ID of the faction
            status: Optional filter by status
            limit: Maximum number of intents to return (default 20, max 100)
            offset: Number of intents to skip

        Returns:
            Tuple of (intents list, total count, has_more flag)
        """
        with self._lock:
            all_intents = self.find_by_faction(faction_id, status)
            total = len(all_intents)

            # Apply pagination
            paginated = all_intents[offset : offset + limit]
            has_more = offset + limit < total

            return paginated, total, has_more
