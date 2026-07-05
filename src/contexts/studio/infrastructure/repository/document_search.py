from __future__ import annotations

from typing import TYPE_CHECKING

from src.contexts.studio.infrastructure.repository.common import (
    Any,
    Document,
    DocumentRevision,
    Project,
    Session,
    StudioDatabase,
    text,
)

__all__ = ["DocumentSearchRepositoryMixin"]


class DocumentSearchRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

    def _refresh_search(
        self,
        session: Session,
        document: Document,
        revision: DocumentRevision,
    ) -> None:
        session.execute(
            text("DELETE FROM document_search WHERE document_id = :document_id"),
            {"document_id": document.id},
        )
        session.execute(
            text(
                "INSERT INTO document_search(document_id, project_id, title, content) "
                "VALUES (:document_id, :project_id, :title, :content)"
            ),
            {
                "document_id": document.id,
                "project_id": document.project_id,
                "title": document.title,
                "content": revision.content_markdown,
            },
        )

    def search_documents(
        self,
        project_id: str,
        query: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[dict[str, Any]]:
        with self.database.session() as session:
            self._project(session, project_id, owner_id, guest_session_id)
            rows = session.execute(
                text(
                    "SELECT document_id, title, snippet(document_search, 3, '', "
                    "'', ' … ', 16) AS excerpt "
                    "FROM document_search WHERE project_id = :project_id "
                    "AND document_search MATCH :query ORDER BY rank LIMIT 30"
                ),
                {"project_id": project_id, "query": query},
            ).mappings()
            return [dict(row) for row in rows]
