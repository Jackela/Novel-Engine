from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload

from src.contexts.studio.infrastructure.repository.common import (
    Document,
    DocumentDto,
    DocumentRevision,
    InvalidOperation,
    NotFound,
    Project,
    Session,
    SnapshotConflict,
    SnapshotDocument,
    StudioDatabase,
    _document_dto,
    _session,
    datetime,
    func,
    new_id,
    select,
    text,
)
from src.contexts.studio.infrastructure.repository.document_revisions import (
    DocumentRevisionRepositoryMixin,
)
from src.contexts.studio.infrastructure.repository.document_search import (
    DocumentSearchRepositoryMixin,
)

__all__ = ["DocumentRepositoryMixin"]


class DocumentRepositoryMixin(
    DocumentRevisionRepositoryMixin,
    DocumentSearchRepositoryMixin,
):
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

    def _document(
        self,
        session: Session,
        project: Project,
        document_id: str,
    ) -> Document:
        document = session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.project_id == project.id,
            )
        )
        if document is None:
            raise NotFound("Document not found.")
        return document

    def create_document(
        self,
        *,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
        kind: str,
        title: str,
        content_markdown: str,
        position: int,
        metadata_json: str,
        source: str,
        now: datetime,
        session: Session | None = None,
    ) -> DocumentDto:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            document = Document(
                id=new_id(),
                project_id=project.id,
                kind=kind,
                title=title,
                position=position,
                created_at=now,
                updated_at=now,
            )
            db_session.add(document)
            db_session.flush()
            revision = DocumentRevision(
                id=new_id(),
                document_id=document.id,
                parent_revision_id=None,
                revision_number=1,
                content_markdown=content_markdown,
                metadata_json=metadata_json,
                source=source,
                created_at=now,
            )
            db_session.add(revision)
            db_session.flush()
            document.current_revision_id = revision.id
            self._refresh_search(db_session, document, revision)
            project.updated_at = now
            db_session.flush()
            return _document_dto(document)

    def list_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> list[DocumentDto]:
        with _session(self.database, session) as db_session:
            self._project(db_session, project_id, owner_id, guest_session_id)
            documents = db_session.scalars(
                select(Document)
                .where(Document.project_id == project_id)
                .order_by(Document.kind, Document.position, Document.created_at)
                .options(selectinload(Document.revisions))
            ).all()
            return [_document_dto(document) for document in documents]

    def get_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> DocumentDto:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            document = self._document(db_session, project, document_id)
            return _document_dto(document)

    def delete_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        session: Session | None = None,
    ) -> None:
        with _session(self.database, session) as db_session:
            project = self._project(db_session, project_id, owner_id, guest_session_id)
            document = self._document(db_session, project, document_id)
            snapshot_reference = db_session.scalar(
                select(SnapshotDocument.id).where(
                    SnapshotDocument.document_id == document.id
                )
            )
            if snapshot_reference is not None:
                raise SnapshotConflict()
            db_session.execute(
                text("DELETE FROM document_search WHERE document_id = :document_id"),
                {"document_id": document.id},
            )
            db_session.delete(document)

    def next_document_position(
        self,
        project_id: str,
        kind: str,
        session: Session | None = None,
    ) -> int:
        with _session(self.database, session) as db_session:
            max_position = db_session.scalar(
                select(func.max(Document.position)).where(
                    Document.project_id == project_id,
                    Document.kind == kind,
                )
            )
            return (max_position or 0) + 1

    def save_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        content_markdown: str,
        base_revision_id: str | None,
        title: str | None,
        metadata_json: str,
        source: str,
        now: datetime,
    ) -> DocumentDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            document = self._document(session, project, document_id)
            if document.current_revision_id != base_revision_id:
                raise InvalidOperation(
                    "Document changed since the requested base revision."
                )
            current_revision = self._current_revision(session, document)
            if title is not None:
                document.title = title
            revision = DocumentRevision(
                id=new_id(),
                document_id=document.id,
                parent_revision_id=document.current_revision_id,
                revision_number=current_revision.revision_number + 1,
                content_markdown=content_markdown,
                metadata_json=metadata_json,
                source=source,
                created_at=now,
            )
            session.add(revision)
            session.flush()
            document.current_revision_id = revision.id
            document.updated_at = now
            project.updated_at = now
            self._refresh_search(session, document, revision)
            session.flush()
            return _document_dto(document)

    def reorder_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        document_ids: list[str],
        now: datetime,
    ) -> list[DocumentDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            documents = {
                document.id: document
                for document in session.scalars(
                    select(Document).where(Document.project_id == project.id)
                ).all()
            }
            if set(document_ids) != set(documents):
                raise InvalidOperation(
                    "Reorder must include every project document once."
                )
            for position, doc_id in enumerate(document_ids, start=1):
                documents[doc_id].position = position
                documents[doc_id].updated_at = now
            project.updated_at = now
            session.flush()
            return [_document_dto(documents[doc_id]) for doc_id in document_ids]
