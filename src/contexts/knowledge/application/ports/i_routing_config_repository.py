"""
Routing Configuration Repository Port

Repository interface for workspace routing configuration.

Constitution Compliance:
- Article II (Hexagonal): Port interface for infrastructure adapters
- Article I (DDD): Repository pattern for domain persistence

Warzone 4: AI Brain - BRAIN-028B
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ...domain.models.routing_config import WorkspaceRoutingConfig

if TYPE_CHECKING:
    pass


class RoutingConfigNotFoundError(Exception):
    """Raised when a routing configuration is not found."""

    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        super().__init__(
            f"Routing configuration not found for workspace: {workspace_id}"
        )


class RoutingConfigRepositoryError(Exception):
    """Raised when a repository operation fails."""


class IRoutingConfigRepository(ABC):
    """
    Repository interface for routing configuration persistence.

    Why:
        - Abstracts persistence layer from application logic
        - Enables testing with mock implementations
        - Supports multiple storage backends (memory, database, file)

    The repository provides:
    1. CRUD operations for workspace routing configs
    2. Global configuration management
    3. Version tracking for audit trail
    """

    @abstractmethod
    async def get_config(
        self, workspace_id: str, fallback_to_global: bool = True
    ) -> WorkspaceRoutingConfig:
        """
        Get routing configuration for a workspace.

        Args:
            workspace_id: Workspace identifier (empty for global config)
            fallback_to_global: If True, return global config when workspace config not found

        Returns:
            WorkspaceRoutingConfig for the workspace

        Raises:
            RoutingConfigNotFoundError: If config not found and fallback is False
            RoutingConfigRepositoryError: If retrieval fails
        """
        raise NotImplementedError

    @abstractmethod
    async def save_config(self, config: WorkspaceRoutingConfig) -> str:
        """
        Save or update routing configuration.

        Args:
            config: Configuration to save

        Returns:
            The workspace_id of the saved config

        Raises:
            RoutingConfigRepositoryError: If save fails
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_config(self, workspace_id: str) -> bool:
        """
        Delete routing configuration for a workspace.

        Args:
            workspace_id: Workspace identifier

        Returns:
            True if deleted, False if not found

        Raises:
            RoutingConfigRepositoryError: If delete fails
        """
        raise NotImplementedError

    @abstractmethod
    async def list_configs(self) -> list[WorkspaceRoutingConfig]:
        """
        List all routing configurations.

        Returns:
            List of all workspace configurations (excluding global)

        Raises:
            RoutingConfigRepositoryError: If listing fails
        """
        raise NotImplementedError

    @abstractmethod
    async def get_global_config(self) -> WorkspaceRoutingConfig:
        """
        Get the global routing configuration.

        Returns:
            Global WorkspaceRoutingConfig

        Raises:
            RoutingConfigNotFoundError: If global config not found
            RoutingConfigRepositoryError: If retrieval fails
        """
        raise NotImplementedError

    @abstractmethod
    async def save_global_config(self, config: WorkspaceRoutingConfig) -> str:
        """
        Save the global routing configuration.

        Args:
            config: Global configuration to save

        Returns:
            The string "global"

        Raises:
            RoutingConfigRepositoryError: If save fails
        """
        raise NotImplementedError

    @abstractmethod
    async def reset_to_defaults(self, workspace_id: str) -> WorkspaceRoutingConfig:
        """
        Reset a workspace configuration to defaults.

        Args:
            workspace_id: Workspace identifier (empty for global)

        Returns:
            New default configuration

        Raises:
            RoutingConfigRepositoryError: If reset fails
        """
        raise NotImplementedError


__all__ = [
    "IRoutingConfigRepository",
    "RoutingConfigNotFoundError",
    "RoutingConfigRepositoryError",
]
