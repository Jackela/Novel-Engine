from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    Principal,
    StudioRepository,
    _owner_scopes,
    _snapshot_payload,
    utcnow,
)

__all__ = ["SnapshotService"]


class SnapshotService:
    """Project snapshot creation and inspection."""

    def __init__(self, repository: StudioRepository) -> None:
        self._repository = repository

    def create_snapshot(
        self,
        principal: Principal,
        project_id: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        snapshot = self._repository.create_snapshot(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            reason=reason,
            now=utcnow(),
        )
        return _snapshot_payload(snapshot)

    def list_snapshots(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        snapshots = self._repository.list_snapshots(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return [_snapshot_payload(snapshot) for snapshot in snapshots]
