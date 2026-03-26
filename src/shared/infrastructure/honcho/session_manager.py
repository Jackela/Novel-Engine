"""Honcho session manager."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, cast

from .errors import HonchoClientError, HonchoErrorDetails

if TYPE_CHECKING:
    from honcho import Honcho
    from honcho.types import Session


class HonchoSessionManager:
    """Manages session operations."""

    def __init__(
        self, get_client: Callable[..., Any], classify_error: Callable[..., Any]
    ) -> None:
        """Initialize the session manager.

        Args:
            get_client: Function to get the Honcho client.
            classify_error: Function to classify errors.
        """
        self._get_client = get_client
        self._classify_error = classify_error

    async def create_session(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Session":
        """Create a new session for a peer.

        Args:
            workspace_id: Workspace identifier.
            peer_id: Peer identifier (character).
            session_id: Optional custom session ID.
            metadata: Optional session metadata.

        Returns:
            Session instance.

        Raises:
            HonchoClientError: If session creation fails.
        """
        client: Honcho = await self._get_client()

        try:
            session = await client.sessions.create(
                workspace_id=workspace_id,
                peer_id=peer_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            return session
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to create session for peer {peer_id}: {e}",
                details=HonchoErrorDetails(
                    operation="create_session",
                    entity_id=session_id or "auto-generated",
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={"workspace_id": workspace_id, "peer_id": peer_id},
                ),
            ) from e

    async def get_session_context(
        self,
        workspace_id: str,
        session_id: str,
        tokens: int = 4000,
        summarize: bool = False,
    ) -> list[dict[str, Any]]:
        """Get session context for LLM consumption.

        Retrieves relevant messages and summaries up to a token limit.

        Args:
            workspace_id: Workspace identifier.
            session_id: Session identifier.
            tokens: Maximum tokens to return.
            summarize: Whether to include session summary.

        Returns:
            List of context messages suitable for LLM prompt.

        Raises:
            HonchoClientError: If getting session context fails.
        """
        client: Honcho = await self._get_client()

        try:
            context = await client.sessions.context(
                workspace_id=workspace_id,
                session_id=session_id,
                tokens=tokens,
                summarize=summarize,
            )
            context_data = context.to_openai() if hasattr(context, "to_openai") else []
            return cast(list[dict[str, Any]], context_data)
        except (ConnectionError, TimeoutError) as e:
            raise HonchoClientError(
                f"Failed to get session context for {session_id}: {e}",
                details=HonchoErrorDetails(
                    operation="get_session_context",
                    entity_id=session_id,
                    error_code=self._classify_error(e),
                    original_exception=e,
                    context={
                        "workspace_id": workspace_id,
                        "tokens": tokens,
                        "summarize": summarize,
                    },
                ),
            ) from e
