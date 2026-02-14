"""
In-Memory Budget Alert Repository

Warzone 4: AI Brain - BRAIN-034B
In-memory implementation of IBudgetAlertRepository for testing.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.models.budget_alert import (
        AlertTriggeredEvent,
        BudgetAlertState,
    )


class InMemoryBudgetAlertRepository:
    """
    In-memory implementation of budget alert repository.

    Why:
        - Provides fast, in-memory storage for testing
        - No external dependencies
        - Thread-safe for basic operations

    Not suitable for production - use a database-backed implementation.
    """

    def __init__(self) -> None:
        """Initialize the in-memory repository."""
        self._alerts: dict[str, BudgetAlertState] = {}
        self._events: list[AlertTriggeredEvent] = []

    async def save_alert(self, alert_state: BudgetAlertState) -> None:
        """
        Save or update an alert state.

        Args:
            alert_state: Alert state to save
        """
        self._alerts[alert_state.id] = alert_state

    async def get_alert(self, alert_id: str) -> BudgetAlertState | None:
        """
        Retrieve an alert state by ID.

        Args:
            alert_id: UUID of the alert state

        Returns:
            BudgetAlertState if found, None otherwise
        """
        return self._alerts.get(alert_id)

    async def get_all_alerts(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
        enabled_only: bool = True,
    ) -> list[BudgetAlertState]:
        """
        Get all alert states matching the filters.

        Args:
            workspace_id: Optional workspace filter
            user_id: Optional user filter
            enabled_only: Only return enabled alerts

        Returns:
            List of matching alert states
        """
        results = list(self._alerts.values())

        if workspace_id is not None:
            results = [
                a for a in results if a.config.workspace_id in (workspace_id, None)
            ]
        if user_id is not None:
            results = [a for a in results if a.config.user_id in (user_id, None)]
        if enabled_only:
            results = [a for a in results if a.config.enabled]

        return results

    async def delete_alert(self, alert_id: str) -> bool:
        """
        Delete an alert state.

        Args:
            alert_id: UUID of the alert to delete

        Returns:
            True if deleted, False if not found
        """
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            return True
        return False

    async def log_triggered_event(self, event: AlertTriggeredEvent) -> None:
        """
        Log a triggered alert event for auditing.

        Args:
            event: The triggered alert event
        """
        self._events.append(event)

    async def get_triggered_events(
        self,
        workspace_id: str | None = None,
        user_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AlertTriggeredEvent]:
        """
        Get triggered alert events matching filters.

        Args:
            workspace_id: Optional workspace filter
            user_id: Optional user filter
            start_time: Optional start of time range
            end_time: Optional end of time range
            limit: Maximum results to return

        Returns:
            List of triggered alert events
        """
        results = list(self._events)

        if workspace_id is not None:
            results = [e for e in results if e.workspace_id == workspace_id]
        if user_id is not None:
            results = [e for e in results if e.user_id == user_id]
        if start_time is not None:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time is not None:
            results = [e for e in results if e.timestamp <= end_time]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    def clear(self) -> None:
        """Clear all stored alerts and events (useful for testing)."""
        self._alerts.clear()
        self._events.clear()

    @property
    def alert_count(self) -> int:
        """Get the number of stored alerts."""
        return len(self._alerts)

    @property
    def event_count(self) -> int:
        """Get the number of stored events."""
        return len(self._events)


__all__ = [
    "InMemoryBudgetAlertRepository",
]
