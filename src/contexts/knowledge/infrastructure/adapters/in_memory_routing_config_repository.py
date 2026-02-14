"""
In-Memory Routing Configuration Repository Adapter

In-memory storage for routing configuration.
Suitable for development and testing.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing port
- Article I (DDD): Repository pattern implementation

Warzone 4: AI Brain - BRAIN-028B
"""

from __future__ import annotations

import asyncio

import structlog

from ...application.ports.i_routing_config_repository import (
    IRoutingConfigRepository,
    RoutingConfigNotFoundError,
)
from ...domain.models.routing_config import RoutingScope, WorkspaceRoutingConfig

logger = structlog.get_logger()


class InMemoryRoutingConfigRepository(IRoutingConfigRepository):
    """
    In-memory repository for routing configuration.

    Why:
        - Fast access for development and testing
        - No external dependencies
        - Thread-safe with asyncio locks

    Storage:
        - Global config stored under workspace_id=""
        - Workspace configs stored under their workspace_id
    """

    def __init__(self) -> None:
        """Initialize the repository with empty storage and a lock."""
        self._storage: dict[str, WorkspaceRoutingConfig] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure global config exists."""
        if not self._initialized:
            global_config = WorkspaceRoutingConfig.create_global()
            self._storage[""] = global_config
            self._initialized = True
            logger.info("routing_config_repository_initialized")

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
        await self._ensure_initialized()

        async with self._lock:
            config = self._storage.get(workspace_id)

            if config is None and fallback_to_global and workspace_id != "":
                # Return global config as fallback
                config = self._storage.get("")
                if config:
                    logger.debug(
                        "routing_config_fallback_to_global",
                        workspace_id=workspace_id,
                    )
                    return config

            if config is None:
                raise RoutingConfigNotFoundError(workspace_id)

            return config

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
        await self._ensure_initialized()

        async with self._lock:
            workspace_id = config.workspace_id
            existing = self._storage.get(workspace_id)

            if existing:
                # Preserve created_at and version
                config = WorkspaceRoutingConfig(
                    workspace_id=config.workspace_id,
                    scope=config.scope,
                    task_rules=config.task_rules,
                    constraints=config.constraints,
                    circuit_breaker_rules=config.circuit_breaker_rules,
                    enable_circuit_breaker=config.enable_circuit_breaker,
                    enable_fallback=config.enable_fallback,
                    created_at=existing.created_at,
                    updated_at=config.updated_at,
                    version=existing.version + 1,
                )

            self._storage[workspace_id] = config

            logger.info(
                "routing_config_saved",
                workspace_id=workspace_id or "global",
                version=config.version,
            )

            return workspace_id

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
        async with self._lock:
            if workspace_id in self._storage:
                del self._storage[workspace_id]
                logger.info("routing_config_deleted", workspace_id=workspace_id)
                return True
            return False

    async def list_configs(self) -> list[WorkspaceRoutingConfig]:
        """
        List all routing configurations.

        Returns:
            List of all workspace configurations (excluding global)

        Raises:
            RoutingConfigRepositoryError: If listing fails
        """
        await self._ensure_initialized()

        async with self._lock:
            return [
                config
                for wid, config in self._storage.items()
                if wid != "" and config.scope == RoutingScope.WORKSPACE
            ]

    async def get_global_config(self) -> WorkspaceRoutingConfig:
        """
        Get the global routing configuration.

        Returns:
            Global WorkspaceRoutingConfig

        Raises:
            RoutingConfigNotFoundError: If global config not found
            RoutingConfigRepositoryError: If retrieval fails
        """
        await self._ensure_initialized()

        async with self._lock:
            config = self._storage.get("")
            if config is None:
                raise RoutingConfigNotFoundError("global")
            return config

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
        # Force scope to global
        global_config = WorkspaceRoutingConfig(
            workspace_id="",
            scope=RoutingScope.GLOBAL,
            task_rules=config.task_rules,
            constraints=config.constraints,
            circuit_breaker_rules=config.circuit_breaker_rules,
            enable_circuit_breaker=config.enable_circuit_breaker,
            enable_fallback=config.enable_fallback,
            created_at=config.created_at,
            updated_at=config.updated_at,
            version=config.version,
        )

        return await self.save_config(global_config)

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
        async with self._lock:
            if workspace_id == "":
                new_config = WorkspaceRoutingConfig.create_global()
                self._storage[""] = new_config
                self._initialized = True
            else:
                new_config = WorkspaceRoutingConfig.create_workspace(workspace_id)
                self._storage[workspace_id] = new_config

            logger.info("routing_config_reset", workspace_id=workspace_id or "global")

            return new_config


__all__ = ["InMemoryRoutingConfigRepository"]
