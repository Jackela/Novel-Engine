"""Guest session management for anonymous workspace access.

Provides JWT-based session tokens that map to workspaces, enabling
anonymous users to have persistent workspace access without authentication.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from .filesystem import (
    FilesystemWorkspaceStore,
    _new_workspace_id,
    _validate_workspace_id,
)

GUEST_SESSION_COOKIE_NAME = "guest_session"
GUEST_SESSION_TOKEN_TYPE = "guest"

DEFAULT_GUEST_TTL_DAYS = 30
_COOKIE_VALUE_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


def _utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current time in UTC timezone
    """
    return datetime.now(timezone.utc)


def _ttl_seconds() -> int:
    """Get guest session TTL in seconds from environment.

    Reads GUEST_WORKSPACE_TTL_DAYS environment variable, defaulting
    to 30 days if not set or invalid.

    Returns:
        Session lifetime in seconds
    """
    raw = os.getenv("GUEST_WORKSPACE_TTL_DAYS")
    if not raw:
        return DEFAULT_GUEST_TTL_DAYS * 24 * 60 * 60
    try:
        days = int(raw)
        if days <= 0:
            raise ValueError
    except ValueError:
        days = DEFAULT_GUEST_TTL_DAYS
    return days * 24 * 60 * 60


def _assert_safe_cookie_value(token: str) -> str:
    """Validate that a token is safe to use as a cookie value.

    Args:
        token: JWT token string

    Returns:
        The validated token

    Raises:
        ValueError: If token contains unsafe characters
    """
    if not _COOKIE_VALUE_RE.fullmatch(token):
        raise ValueError("Unsafe guest session cookie value")
    return token


@dataclass(frozen=True)
class GuestSessionResult:
    """Result of resolving or creating a guest session.

    Attributes:
        workspace_id: ID of the workspace associated with the session
        created: True if a new workspace was created, False if existing
    """

    workspace_id: str
    created: bool


class GuestSessionManager:
    """Manages guest session tokens and workspace assignment.

    Uses JWT tokens to maintain anonymous sessions, mapping each token
    to a workspace. New visitors get new workspaces; returning visitors
    with valid tokens get their existing workspace.

    Attributes:
        cookie_name: Name of the HTTP cookie for the session token

    Example:
        >>> manager = GuestSessionManager(store, secret_key="secret")
        >>> result = manager.resolve_or_create(None)
        >>> token = manager.encode(result.workspace_id)
    """

    def __init__(
        self,
        workspace_store: FilesystemWorkspaceStore,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        cookie_name: str = GUEST_SESSION_COOKIE_NAME,
    ) -> None:
        """Initialize the guest session manager.

        Args:
            workspace_store: Store for creating/retrieving workspaces
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            cookie_name: Name for the session cookie
        """
        self._workspace_store = workspace_store
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._cookie_name = cookie_name

    @property
    def cookie_name(self) -> str:
        """Get the session cookie name.

        Returns:
            Cookie name string
        """
        return self._cookie_name

    def decode(self, token: str) -> Optional[str]:
        """Decode a session token to extract workspace ID.

        Args:
            token: JWT session token

        Returns:
            Workspace ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
        except Exception:
            return None
        if payload.get("token_type") != GUEST_SESSION_TOKEN_TYPE:
            return None
        workspace_id = payload.get("workspace_id")
        if not isinstance(workspace_id, str) or not workspace_id.strip():
            return None
        try:
            return _validate_workspace_id(workspace_id)
        except ValueError:
            return None

    def encode(self, workspace_id: str) -> str:
        """Encode a workspace ID into a session token.

        Args:
            workspace_id: Workspace ID to encode

        Returns:
            JWT token string safe for cookie storage
        """
        now = _utc_now()
        payload = {
            "token_type": GUEST_SESSION_TOKEN_TYPE,
            "workspace_id": _validate_workspace_id(workspace_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=_ttl_seconds())).timestamp()),
        }
        raw_token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        # Handle both bytes and str return types from jwt.encode (version dependent)
        token_str: str = raw_token.decode("utf-8") if isinstance(raw_token, bytes) else raw_token  # type: ignore[union-attr]
        return _assert_safe_cookie_value(token_str)

    def resolve_or_create(self, token: Optional[str]) -> GuestSessionResult:
        """Resolve a token to a workspace or create a new session.

        If a valid token is provided, returns the associated workspace.
        Otherwise, creates a new workspace and returns it.

        Args:
            token: Optional existing session token

        Returns:
            Result containing workspace ID and creation flag
        """
        if token:
            workspace_id = self.decode(token)
            if workspace_id:
                self._workspace_store.get_or_create(workspace_id)
                return GuestSessionResult(workspace_id=workspace_id, created=False)

        workspace_id = _new_workspace_id()
        self._workspace_store.get_or_create(workspace_id)
        return GuestSessionResult(workspace_id=workspace_id, created=True)

    def cookie_max_age_seconds(self) -> int:
        """Get the max-age for session cookies in seconds.

        Returns:
            Cookie lifetime in seconds
        """
        return _ttl_seconds()
