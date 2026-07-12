from __future__ import annotations

from typing import TYPE_CHECKING

from src.contexts.studio.infrastructure.repository.common import (
    Document,
    DocumentRevision,
    InvalidOperation,
    NotFound,
    Project,
    RevisionDto,
    Session,
    StudioDatabase,
    _revision_dto,
    select,
)

__all__ = ["DocumentRevisionRepositoryMixin"]


class DocumentRevisionRepositoryMixin:
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
        ) -> Document: ...

    def _current_revision(
        self,
        session: Session,
        document: Document,
    ) -> DocumentRevision:
        if document.current_revision_id is None:
            raise InvalidOperation("Document has no current revision.")
        revision = session.get(DocumentRevision, document.current_revision_id)
        if revision is None:
            raise InvalidOperation("Document revision chain is invalid.")
        return revision

    def get_revision(
        self,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> RevisionDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            document = self._document(session, project, document_id)
            revision = session.scalar(
                select(DocumentRevision).where(
                    DocumentRevision.id == revision_id,
                    DocumentRevision.document_id == document.id,
                )
            )
            if revision is None:
                raise NotFound("Revision not found.")
            return _revision_dto(revision)

    def list_revisions(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[RevisionDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            document = self._document(session, project, document_id)
            revisions = session.scalars(
                select(DocumentRevision)
                .where(DocumentRevision.document_id == document.id)
                .order_by(DocumentRevision.revision_number.desc())
            ).all()
            return [_revision_dto(revision) for revision in revisions]
