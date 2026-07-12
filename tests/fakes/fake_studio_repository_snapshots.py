from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ProjectDto,
    RevisionDto,
    SnapshotDocumentDto,
    SnapshotDto,
)
from src.contexts.studio.domain.exceptions import NotFound
from src.contexts.studio.domain.utils import new_id


class FakeStudioRepositorySnapshotsMixin:
    _documents: dict[str, DocumentDto]
    _revisions: dict[str, RevisionDto]
    _snapshots: dict[str, SnapshotDto]
    _snapshot_documents: dict[str, list[SnapshotDocumentDto]]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        raise NotImplementedError

    def create_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        reason: str,
        now: datetime,
    ) -> SnapshotDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshot_id = new_id()
        items = self._snapshot_items(project_id)
        snapshot = SnapshotDto(
            id=snapshot_id,
            project_id=project_id,
            reason=reason,
            created_at=now,
            documents=items,
        )
        self._snapshots[snapshot_id] = snapshot
        self._snapshot_documents[snapshot_id] = items
        return snapshot

    def list_snapshots(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[SnapshotDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshots = [
            snapshot
            for snapshot in self._snapshots.values()
            if snapshot.project_id == project_id
        ]
        snapshots.sort(key=lambda snapshot: snapshot.created_at, reverse=True)
        return snapshots

    def get_latest_export_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> SnapshotDto | None:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        snapshots = [
            snapshot
            for snapshot in self._snapshots.values()
            if snapshot.project_id == project_id and snapshot.reason == "export"
        ]
        if not snapshots:
            return None
        snapshots.sort(key=lambda snapshot: snapshot.created_at, reverse=True)
        return snapshots[0]

    def snapshot_content(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise NotFound("Snapshot not found.")
        self._get_visible_project(snapshot.project_id, owner_id, guest_session_id)
        return self._snapshot_content_pairs(snapshot_id)

    def snapshot_revision_map(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> dict[str, str]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise NotFound("Snapshot not found.")
        self._get_visible_project(snapshot.project_id, owner_id, guest_session_id)
        return {
            item.document_id: item.revision_id
            for item in self._snapshot_documents.get(snapshot_id, [])
        }

    def _snapshot_items(self, project_id: str) -> list[SnapshotDocumentDto]:
        documents = [
            document
            for document in self._documents.values()
            if document.project_id == project_id
        ]
        documents.sort(key=lambda document: (document.position, document.created_at))
        items: list[SnapshotDocumentDto] = []
        for document in documents:
            revision_id = document.current_revision_id
            if revision_id is None:
                continue
            items.append(
                SnapshotDocumentDto(
                    document_id=document.id,
                    revision_id=revision_id,
                    position=document.position,
                )
            )
        return items

    def _snapshot_content_pairs(
        self, snapshot_id: str
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        pairs = []
        for item in self._snapshot_documents.get(snapshot_id, []):
            document = self._documents.get(item.document_id)
            revision = self._revisions.get(item.revision_id)
            if document is not None and revision is not None:
                pairs.append((document, revision))
        return pairs
