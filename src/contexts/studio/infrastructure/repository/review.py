from __future__ import annotations

from typing import TYPE_CHECKING

from src.contexts.studio.infrastructure.repository.common import (
    Document,
    DocumentRevision,
    Project,
    ProjectSnapshot,
    Review,
    ReviewDto,
    ReviewIssue,
    Session,
    SnapshotDocument,
    StudioDatabase,
    _review_dto,
    _word_count,
    cast,
    datetime,
    dump_json,
    new_id,
    select,
)

__all__ = ["ReviewRepositoryMixin"]


class ReviewRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

    def create_review(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        provider: str,
        model: str,
        now: datetime,
    ) -> ReviewDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            snapshot = ProjectSnapshot(
                id=new_id(),
                project_id=project.id,
                reason="review",
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
            review = Review(
                id=new_id(),
                project_id=project.id,
                snapshot_id=snapshot.id,
                provider=provider,
                model=model,
                summary="Editorial checks completed without modifying the manuscript.",
                created_at=now,
            )
            session.add(review)
            session.flush()
            content_pairs = self._snapshot_content(session, snapshot.id)
            for document, revision in content_pairs:
                if document.kind != "chapter":
                    continue
                words = _word_count(revision.content_markdown)
                if words < 250:
                    session.add(
                        ReviewIssue(
                            id=new_id(),
                            review_id=review.id,
                            document_id=document.id,
                            severity="warning",
                            code="thin_chapter",
                            message=f"{document.title} contains only {words} words.",
                            suggestion="Develop the scene turn, consequence, and sensory detail.",
                            evidence_json=dump_json({"word_count": words}),
                        )
                    )
                if not revision.content_markdown.strip():
                    session.add(
                        ReviewIssue(
                            id=new_id(),
                            review_id=review.id,
                            document_id=document.id,
                            severity="blocker",
                            code="empty_chapter",
                            message=f"{document.title} has no manuscript content.",
                            suggestion="Draft the chapter before exporting.",
                            evidence_json="{}",
                        )
                    )
            session.flush()
            return _review_dto(session, review)

    def _snapshot_content(
        self,
        session: Session,
        snapshot_id: str,
    ) -> list[tuple[Document, DocumentRevision]]:
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
        return [(row[0], row[1]) for row in rows]

    def list_reviews(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ReviewDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            reviews = session.scalars(
                select(Review)
                .where(Review.project_id == project.id)
                .order_by(Review.created_at.desc())
            ).all()
            return [_review_dto(session, review) for review in reviews]
