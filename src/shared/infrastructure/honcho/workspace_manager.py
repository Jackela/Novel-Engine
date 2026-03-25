"""Honcho workspace manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from .errors import HonchoClientError, HonchoErrorDetails

if TYPE_CHECKING:
    from honcho import Honcho
    from honcho.types import Peer, Workspace


class HonchoWorkspaceManager:
    """Manages workspace operations."""

    def __init__(
        self, get_client: Callable[..., Any], classify_error: Callable[..., Any]
    ) -> None:
        """Initialize the workspace manager.

        Args:
            get_client: Function to get the Honcho client.
            classify_error: Function to classify errors.
        """
        self._get_client = get_client
        self._classify_error = classify_error

    async def get_or_create_workspace(
        self,
        workspace_id: str,
        name: str | None = None,
    ) -> "Workspace":
        """Get or create a workspace.

        Args:
            workspace_id: Unique workspace identifier.
            name: Optional human-readable name.

        Returns:
            Workspace instance.

        Raises:
            HonchoClientError: If workspace operations fail.
        """
        client: Honcho = await self._get_client()

        try:
            # Try to get existing workspace
            workspace = await client.workspaces.get(workspace_id)
            if workspace:
                return workspace
        except (ConnectionError, TimeoutError, HonchoClientError):
            # Workspace doesn't exist or connection issue, continue to create
            pass

        # Create new workspace
        try:
            workspace = await client.workspaces.create(
                workspace_id=workspace_id,
                name=name or workspace_id,
            )
            return workspace
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create workspace {workspace_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_workspace",
                    entity_id=workspace_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                ),
            ) from e

    async def get_or_create_peer(
        self,
        workspace_id: str,
        peer_id: str,
        name: str | None = None,
    ) -> "Peer":
        """Get or create a peer within a workspace.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Unique peer identifier (e.g., character ID).
            name: Optional human-readable name.

        Returns:
            Peer instance.

        Raises:
            HonchoClientError: If peer operations fail.
        """
        client: Honcho = await self._get_client()

        try:
            peer = await client.peers.get(workspace_id, peer_id)
            if peer:
                return peer
        except (ConnectionError, TimeoutError, HonchoClientError):
            # Peer doesn't exist or connection issue, continue to create
            pass

        try:
            peer = await client.peers.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                name=name or peer_id,
            )
            return peer
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_peer",
                    entity_id=peer_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                ),
            ) from e
