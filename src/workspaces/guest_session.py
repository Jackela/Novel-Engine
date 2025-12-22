from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from .filesystem import FilesystemWorkspaceStore, _new_workspace_id, _validate_workspace_id


GUEST_SESSION_COOKIE_NAME = "guest_session"
GUEST_SESSION_TOKEN_TYPE = "guest"

DEFAULT_GUEST_TTL_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ttl_seconds() -> int:
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


@dataclass(frozen=True)
class GuestSessionResult:
    workspace_id: str
    created: bool


class GuestSessionManager:
    def __init__(
        self,
        workspace_store: FilesystemWorkspaceStore,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        cookie_name: str = GUEST_SESSION_COOKIE_NAME,
    ):
        self._workspace_store = workspace_store
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._cookie_name = cookie_name

    @property
    def cookie_name(self) -> str:
        return self._cookie_name

    def decode(self, token: str) -> Optional[str]:
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
        now = _utc_now()
        payload = {
            "token_type": GUEST_SESSION_TOKEN_TYPE,
            "workspace_id": _validate_workspace_id(workspace_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=_ttl_seconds())).timestamp()),
        }
        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return str(token)

    def resolve_or_create(self, token: Optional[str]) -> GuestSessionResult:
        if token:
            workspace_id = self.decode(token)
            if workspace_id:
                self._workspace_store.get_or_create(workspace_id)
                return GuestSessionResult(workspace_id=workspace_id, created=False)

        workspace_id = _new_workspace_id()
        self._workspace_store.get_or_create(workspace_id)
        return GuestSessionResult(workspace_id=workspace_id, created=True)

    def cookie_max_age_seconds(self) -> int:
        return _ttl_seconds()
