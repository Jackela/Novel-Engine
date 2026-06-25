from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload

from src.contexts.studio.infrastructure.models import SnapshotDocument
from src.contexts.studio.infrastructure.repository.common import (
    Document,
    DocumentDto,
    DocumentRevision,
    NotFound,
    Project,
    ProjectSnapshot,
    RevisionDto,
    Session,
    SnapshotDto,
    StudioDatabase,
    _document_dto,
    _revision_dto,
    _snapshot_dto,
    cast,
    datetime,
    new_id,
    select,
)

__all__ = ["SnapshotRepositoryMixin"]


class SnapshotRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

    def _verify_snapshot_access(
        self,
        session: Session,
        snapshot_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        """Raise NotFound if the snapshot belongs to an inaccessible project."""
        snapshot_project_id = session.scalar(
            select(ProjectSnapshot.project_id).where(ProjectSnapshot.id == snapshot_id)
        )
        if snapshot_project_id is None:
            raise NotFound("Snapshot not found.")
        self._project(session, snapshot_project_id, owner_id, guest_session_id)

    def create_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        reason: str,
        now: datetime,
    ) -> SnapshotDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            snapshot = ProjectSnapshot(
                id=new_id(),
                project_id=project.id,
                reason=reason,
                created_at=now,
            )
            session.add(snapshot)
            session.flush()
            documents = session.scalars(
                select(Document)
                .where(
                    Document.project_id == project.id,
                    Document.current_revision_id.is_not(None),
                )
                .order_by(Document.position, Document.created_at)
            ).all()
            for document in documents:
                session.add(
                    SnapshotDocument(
                        id=new_id(),
                        snapshot_id=snapshot.id,
                        document_id=document.id,
                        revision_id=cast(str, document.current_revision_id),
                        position=document.position,
                    )
                )
            session.flush()
            return _snapshot_dto(session, snapshot)

    def list_snapshots(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[SnapshotDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            snapshots = session.scalars(
                select(ProjectSnapshot)
                .where(ProjectSnapshot.project_id == project.id)
                .order_by(ProjectSnapshot.created_at.desc())
                .options(selectinload(ProjectSnapshot.snapshot_documents))
            ).all()
            return [_snapshot_dto(session, snapshot) for snapshot in snapshots]

    def get_latest_export_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> SnapshotDto | None:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            snapshot = session.scalar(
                select(ProjectSnapshot)
                .where(
                    ProjectSnapshot.project_id == project.id,
                    ProjectSnapshot.reason == "export",
                )
                .order_by(ProjectSnapshot.created_at.desc())
            )
            return _snapshot_dto(session, snapshot) if snapshot is not None else None

    def snapshot_content(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        with self.database.session() as session:
            self._verify_snapshot_access(
                session, snapshot_id, owner_id, guest_session_id
            )
            rows = session.execute(
                select(Document, DocumentRevision)
                .join(SnapshotDocument, SnapshotDocument.document_id == Document.id)
                .join(
                    DocumentRevision,
                    DocumentRevision.id == SnapshotDocument.revision_id,
                )
                .where(SnapshotDocument.snapshot_id == snapshot_id)
                .order_by(SnapshotDocument.position, Document.created_at)
            ).all()
            return [(_document_dto(row[0]), _revision_dto(row[1])) for row in rows]

    def snapshot_revision_map(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> dict[str, str]:
        with self.database.session() as session:
            self._verify_snapshot_access(
                session, snapshot_id, owner_id, guest_session_id
            )
            items = session.scalars(
                select(SnapshotDocument).where(
                    SnapshotDocument.snapshot_id == snapshot_id
                )
            ).all()
            return {item.document_id: item.revision_id for item in items}
