"""
Budget Alert Repository Port

Warzone 4: AI Brain - BRAIN-034B
Defines the interface for budget alert persistence.

Constitution Compliance:
- Article II (Hexagonal): Application port defining repository contract
- Article V (SOLID): Dependency Inversion - services depend on this abstraction
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...domain.models.budget_alert import (
        BudgetAlertState,
        AlertTriggeredEvent,
    )


class IBudgetAlertRepository(ABC):
    """
    Repository interface for budget alert persistence.

    Why port not repository:
        Defines the contract that infrastructure adapters must implement.
        Application layer depends on this abstraction, not concrete implementations.

    Implementations must:
        - Store alert configurations efficiently
        - Support querying by workspace, user, provider, model
        - Persist alert state tracking
        - Handle concurrent writes safely
    """

    @abstractmethod
    async def save_alert(self, alert_state: BudgetAlertState) -> None:
        """
        Save or update an alert state.

        Args:
            alert_state: Alert state to save

        Raises:
            RepositoryError: If save fails
        """

    @abstractmethod
    async def get_alert(self, alert_id: str) -> BudgetAlertState | None:
        """
        Retrieve an alert state by ID.

        Args:
            alert_id: UUID of the alert state

        Returns:
            BudgetAlertState if found, None otherwise
        """

    @abstractmethod
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

    @abstractmethod
    async def delete_alert(self, alert_id: str) -> bool:
        """
        Delete an alert state.

        Args:
            alert_id: UUID of the alert to delete

        Returns:
            True if deleted, False if not found
        """

    @abstractmethod
    async def log_triggered_event(self, event: AlertTriggeredEvent) -> None:
        """
        Log a triggered alert event for auditing.

        Args:
            event: The triggered alert event

        Raises:
            RepositoryError: If logging fails
        """

    @abstractmethod
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


class RepositoryError(Exception):
    """Base exception for repository errors."""

    pass


__all__ = [
    "IBudgetAlertRepository",
    "RepositoryError",
]
