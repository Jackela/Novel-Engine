"""SQLAlchemy implementation of the Studio repository port."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.contexts.studio.application.ports.studio_repository import (
    DocumentDto,
    ExportDto,
    JobDto,
    JobEventDto,
    OwnerDto,
    ProjectDto,
    ReviewDto,
    ReviewIssueDto,
    RevisionDto,
    SessionDto,
    SnapshotDocumentDto,
    SnapshotDto,
)
from src.contexts.studio.domain.exceptions import InvalidOperation, NotFound
from src.contexts.studio.domain.types import JOB_KINDS
from src.contexts.studio.domain.utils import _word_count, dump_json, new_id, utcnow
from src.contexts.studio.infrastructure.database import StudioDatabase
from src.contexts.studio.infrastructure.models import (
    Document,
    DocumentRevision,
    Export,
    Job,
    JobEvent,
    Owner,
    Project,
    ProjectSnapshot,
    Review,
    ReviewIssue,
    SessionRecord,
    SnapshotDocument,
    UsageEvent,
)


def _owner_dto(owner: Owner) -> OwnerDto:
    return OwnerDto(
        id=owner.id,
        username=owner.username,
        password_hash=owner.password_hash,
        created_at=owner.created_at,
    )


def _session_dto(record: SessionRecord) -> SessionDto:
    return SessionDto(
        id=record.id,
        kind=record.kind,
        owner_id=record.owner_id,
        token_hash=record.token_hash,
        csrf_token=record.csrf_token,
        created_at=record.created_at,
        expires_at=record.expires_at,
        last_seen_at=record.last_seen_at,
    )


def _revision_dto(revision: DocumentRevision) -> RevisionDto:
    return RevisionDto(
        id=revision.id,
        document_id=revision.document_id,
        parent_revision_id=revision.parent_revision_id,
        revision_number=revision.revision_number,
        content_markdown=revision.content_markdown,
        metadata_json=revision.metadata_json,
        source=revision.source,
        created_at=revision.created_at,
    )


def _document_dto(document: Document) -> DocumentDto:
    current_revision = None
    if document.current_revision_id is not None:
        for revision in document.revisions:
            if revision.id == document.current_revision_id:
                current_revision = _revision_dto(revision)
                break
    return DocumentDto(
        id=document.id,
        project_id=document.project_id,
        kind=document.kind,
        title=document.title,
        position=document.position,
        current_revision_id=document.current_revision_id,
        created_at=document.created_at,
        updated_at=document.updated_at,
        current_revision=current_revision,
    )


def _snapshot_dto(session: Session, snapshot: ProjectSnapshot) -> SnapshotDto:
    documents = session.scalars(
        select(SnapshotDocument)
        .where(SnapshotDocument.snapshot_id == snapshot.id)
        .order_by(SnapshotDocument.position)
    ).all()
    return SnapshotDto(
        id=snapshot.id,
        project_id=snapshot.project_id,
        reason=snapshot.reason,
        created_at=snapshot.created_at,
        documents=[
            SnapshotDocumentDto(
                document_id=item.document_id,
                revision_id=item.revision_id,
                position=item.position,
            )
            for item in documents
        ],
    )


def _review_dto(session: Session, review: Review) -> ReviewDto:
    issues = session.scalars(
        select(ReviewIssue)
        .where(ReviewIssue.review_id == review.id)
        .order_by(ReviewIssue.severity, ReviewIssue.code)
    ).all()
    return ReviewDto(
        id=review.id,
        project_id=review.project_id,
        snapshot_id=review.snapshot_id,
        provider=review.provider,
        model=review.model,
        summary=review.summary,
        created_at=review.created_at,
        issues=[
            ReviewIssueDto(
                id=issue.id,
                document_id=issue.document_id,
                severity=issue.severity,
                code=issue.code,
                message=issue.message,
                suggestion=issue.suggestion,
                evidence_json=issue.evidence_json,
            )
            for issue in issues
        ],
    )


def _job_event_dto(event: JobEvent) -> JobEventDto:
    return JobEventDto(
        id=event.id,
        job_id=event.job_id,
        status=event.status,
        details_json=event.details_json,
        created_at=event.created_at,
    )


def _job_dto(session: Session, job: Job) -> JobDto:
    events = session.scalars(
        select(JobEvent)
        .where(JobEvent.job_id == job.id)
        .order_by(JobEvent.created_at)
    ).all()
    return JobDto(
        id=job.id,
        project_id=job.project_id,
        document_id=job.document_id,
        kind=job.kind,
        operation=job.operation,
        status=job.status,
        provider=job.provider,
        model=job.model,
        request_json=job.request_json,
        result_json=job.result_json,
        error=job.error,
        retry_of_job_id=job.retry_of_job_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        events=[_job_event_dto(event) for event in events],
    )


def _export_dto(item: Export) -> ExportDto:
    return ExportDto(
        id=item.id,
        project_id=item.project_id,
        snapshot_id=item.snapshot_id,
        format=item.format,
        relative_path=item.relative_path,
        size_bytes=item.size_bytes,
        checksum_sha256=item.checksum_sha256,
        created_at=item.created_at,
    )


class SqlAlchemyStudioRepository:
    """SQLAlchemy-backed implementation of ``StudioRepository``."""

    def __init__(self, database: StudioDatabase) -> None:
        self.database = database

    # ------------------------------------------------------------------
    # Owner and authentication
    # ------------------------------------------------------------------
    def owner_exists(self) -> bool:
        with self.database.session() as session:
            return (session.scalar(select(func.count()).select_from(Owner)) or 0) > 0

    def get_owner_by_username(self, username: str) -> OwnerDto | None:
        with self.database.session() as session:
            owner = session.scalar(select(Owner).where(Owner.username == username))
            return _owner_dto(owner) if owner is not None else None

    def get_first_owner(self) -> OwnerDto | None:
        with self.database.session() as session:
            owner = session.scalar(select(Owner).order_by(Owner.created_at))
            return _owner_dto(owner) if owner is not None else None

    def create_owner(self, username: str, password_hash: str) -> OwnerDto:
        with self.database.session() as session:
            owner = Owner(
                id=new_id(),
                username=username,
                password_hash=password_hash,
                created_at=utcnow(),
            )
            session.add(owner)
            session.flush()
            return _owner_dto(owner)

    def create_session(
        self,
        *,
        kind: str,
        owner_id: str | None,
        token_hash: str,
        csrf_token: str,
        expires_at: datetime | None,
        created_at: datetime,
        last_seen_at: datetime,
    ) -> SessionDto:
        with self.database.session() as session:
            record = SessionRecord(
                id=new_id(),
                kind=kind,
                owner_id=owner_id,
                token_hash=token_hash,
                csrf_token=csrf_token,
                created_at=created_at,
                expires_at=expires_at,
                last_seen_at=last_seen_at,
            )
            session.add(record)
            session.flush()
            return _session_dto(record)

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None:
        with self.database.session() as session:
            record = session.scalar(
                select(SessionRecord).where(SessionRecord.token_hash == token_hash)
            )
            return _session_dto(record) if record is not None else None

    def delete_session(self, session_id: str) -> None:
        with self.database.session() as session:
            record = session.get(SessionRecord, session_id)
            if record is not None:
                session.delete(record)

    def delete_expired_guest_sessions(self, now: datetime) -> int:
        with self.database.session() as session:
            expired = session.scalars(
                select(SessionRecord).where(
                    SessionRecord.kind == "guest",
                    SessionRecord.expires_at.is_not(None),
                    SessionRecord.expires_at <= now,
                )
            ).all()
            for record in expired:
                session.delete(record)
            return len(expired)

    def update_session_last_seen(self, session_id: str, last_seen_at: datetime) -> None:
        with self.database.session() as session:
            record = session.get(SessionRecord, session_id)
            if record is not None:
                record.last_seen_at = last_seen_at

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def _project(
        self,
        session: Session,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> Project:
        statement = select(Project).where(Project.id == project_id)
        statement = self._scope_projects(statement, owner_id, guest_session_id)
        project = session.scalar(statement)
        if project is None:
            raise NotFound("Project not found.")
        return cast(Project, project)

    @staticmethod
    def _scope_projects(
        statement: Any,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> Any:
        if owner_id:
            return statement.where(Project.owner_id == owner_id)
        return statement.where(Project.guest_session_id == guest_session_id)

    def create_project(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        title: str,
        description: str,
        settings_json: str,
        now: datetime,
        create_seed: bool = True,
    ) -> ProjectDto:
        with self.database.session() as session:
            project = Project(
                id=new_id(),
                owner_id=owner_id,
                guest_session_id=guest_session_id,
                title=title,
                description=description,
                settings_json=settings_json,
                created_at=now,
                updated_at=now,
            )
            session.add(project)
            session.flush()
            documents: list[DocumentDto] = []
            if create_seed:
                document = Document(
                    id=new_id(),
                    project_id=project.id,
                    kind="chapter",
                    title="Chapter 1",
                    position=1,
                    created_at=now,
                    updated_at=now,
                )
                session.add(document)
                session.flush()
                revision = DocumentRevision(
                    id=new_id(),
                    document_id=document.id,
                    parent_revision_id=None,
                    revision_number=1,
                    content_markdown="# Chapter 1\n\n",
                    metadata_json=dump_json({}),
                    source="author",
                    created_at=now,
                )
                session.add(revision)
                session.flush()
                document.current_revision_id = revision.id
                self._refresh_search(session, document, revision)
                documents.append(_document_dto(document))
            return ProjectDto(
                id=project.id,
                owner_id=project.owner_id,
                guest_session_id=project.guest_session_id,
                title=project.title,
                description=project.description,
                settings_json=project.settings_json,
                import_hash=project.import_hash,
                created_at=project.created_at,
                updated_at=project.updated_at,
                documents=documents,
            )

    def list_projects(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ProjectDto]:
        with self.database.session() as session:
            statement = select(Project).order_by(Project.updated_at.desc())
            statement = self._scope_projects(statement, owner_id, guest_session_id)
            projects = session.scalars(statement).all()
            return [
                ProjectDto(
                    id=project.id,
                    owner_id=project.owner_id,
                    guest_session_id=project.guest_session_id,
                    title=project.title,
                    description=project.description,
                    settings_json=project.settings_json,
                    import_hash=project.import_hash,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                    documents=None,
                )
                for project in projects
            ]

    def get_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            documents = session.scalars(
                select(Document)
                .where(Document.project_id == project.id)
                .order_by(Document.kind, Document.position, Document.created_at)
            ).all()
            return ProjectDto(
                id=project.id,
                owner_id=project.owner_id,
                guest_session_id=project.guest_session_id,
                title=project.title,
                description=project.description,
                settings_json=project.settings_json,
                import_hash=project.import_hash,
                created_at=project.created_at,
                updated_at=project.updated_at,
                documents=[_document_dto(document) for document in documents],
            )

    def update_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        title: str | None,
        description: str | None,
        settings_json: str | None,
        now: datetime,
    ) -> ProjectDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            if title is not None:
                project.title = title
            if description is not None:
                project.description = description
            if settings_json is not None:
                project.settings_json = settings_json
            project.updated_at = now
            documents = session.scalars(
                select(Document)
                .where(Document.project_id == project.id)
                .order_by(Document.kind, Document.position, Document.created_at)
            ).all()
            return ProjectDto(
                id=project.id,
                owner_id=project.owner_id,
                guest_session_id=project.guest_session_id,
                title=project.title,
                description=project.description,
                settings_json=project.settings_json,
                import_hash=project.import_hash,
                created_at=project.created_at,
                updated_at=project.updated_at,
                documents=[_document_dto(document) for document in documents],
            )

    def find_project_by_import_hash(self, import_hash: str) -> ProjectDto | None:
        with self.database.session() as session:
            project = session.scalar(
                select(Project).where(Project.import_hash == import_hash)
            )
            if project is None:
                return None
            return ProjectDto(
                id=project.id,
                owner_id=project.owner_id,
                guest_session_id=project.guest_session_id,
                title=project.title,
                description=project.description,
                settings_json=project.settings_json,
                import_hash=project.import_hash,
                created_at=project.created_at,
                updated_at=project.updated_at,
                documents=None,
            )

    def set_project_import_hash(self, project_id: str, import_hash: str) -> None:
        with self.database.session() as session:
            project = session.get(Project, project_id)
            if project is not None:
                project.import_hash = import_hash

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
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
    ) -> DocumentDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            document = Document(
                id=new_id(),
                project_id=project.id,
                kind=kind,
                title=title,
                position=position,
                created_at=now,
                updated_at=now,
            )
            session.add(document)
            session.flush()
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
            session.add(revision)
            session.flush()
            document.current_revision_id = revision.id
            self._refresh_search(session, document, revision)
            project.updated_at = now
            session.flush()
            return _document_dto(document)

    def list_documents(self, project_id: str) -> list[DocumentDto]:
        with self.database.session() as session:
            documents = session.scalars(
                select(Document)
                .where(Document.project_id == project_id)
                .order_by(Document.kind, Document.position, Document.created_at)
            ).all()
            return [_document_dto(document) for document in documents]

    def get_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> DocumentDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            document = self._document(session, project, document_id)
            return _document_dto(document)

    def next_document_position(self, project_id: str, kind: str) -> int:
        with self.database.session() as session:
            max_position = session.scalar(
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
                raise InvalidOperation("Document changed since the requested base revision.")
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
                raise InvalidOperation("Reorder must include every project document once.")
            for position, doc_id in enumerate(document_ids, start=1):
                documents[doc_id].position = position
                documents[doc_id].updated_at = now
            project.updated_at = now
            session.flush()
            return [
                _document_dto(documents[doc_id])
                for doc_id in document_ids
            ]

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

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
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
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        with self.database.session() as session:
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

    def snapshot_revision_map(self, snapshot_id: str) -> dict[str, str]:
        with self.database.session() as session:
            items = session.scalars(
                select(SnapshotDocument).where(SnapshotDocument.snapshot_id == snapshot_id)
            ).all()
            return {item.document_id: item.revision_id for item in items}

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def create_export(
        self,
        *,
        export_id: str,
        project_id: str,
        snapshot_id: str,
        export_format: str,
        relative_path: str,
        size_bytes: int,
        checksum_sha256: str,
        now: datetime,
    ) -> ExportDto:
        with self.database.session() as session:
            export = Export(
                id=export_id,
                project_id=project_id,
                snapshot_id=snapshot_id,
                format=export_format,
                relative_path=relative_path,
                size_bytes=size_bytes,
                checksum_sha256=checksum_sha256,
                created_at=now,
            )
            session.add(export)
            session.flush()
            return _export_dto(export)

    def list_exports(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ExportDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            exports = session.scalars(
                select(Export)
                .where(Export.project_id == project.id)
                .order_by(Export.created_at.desc())
            ).all()
            return [_export_dto(item) for item in exports]

    def get_export(
        self,
        project_id: str,
        export_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ExportDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            item = session.scalar(
                select(Export).where(
                    Export.id == export_id,
                    Export.project_id == project.id,
                )
            )
            if item is None:
                raise NotFound("Export not found.")
            return _export_dto(item)

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------
    def create_job(
        self,
        *,
        project_id: str,
        document_id: str | None,
        kind: str,
        operation: str,
        status: str,
        provider: str,
        model: str,
        request_json: str,
        result_json: str,
        error: str | None,
        retry_of_job_id: str | None,
        now: datetime,
    ) -> JobDto:
        if kind not in JOB_KINDS:
            raise InvalidOperation(f"Unsupported job kind: {kind}")
        with self.database.session() as session:
            job = Job(
                id=new_id(),
                project_id=project_id,
                document_id=document_id,
                kind=kind,
                operation=operation,
                status=status,
                provider=provider,
                model=model,
                request_json=request_json,
                result_json=result_json,
                error=error,
                retry_of_job_id=retry_of_job_id,
                created_at=now,
                updated_at=now,
                started_at=now,
                finished_at=now if status in {"completed", "failed"} else None,
            )
            session.add(job)
            session.flush()
            return _job_dto(session, job)

    def get_job(
        self,
        project_id: str,
        job_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> JobDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            job = session.scalar(
                select(Job).where(
                    Job.id == job_id,
                    Job.project_id == project.id,
                )
            )
            if job is None:
                raise NotFound("Job not found.")
            return _job_dto(session, job)

    def list_jobs(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[JobDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            jobs = session.scalars(
                select(Job)
                .where(Job.project_id == project.id)
                .order_by(Job.created_at.desc())
            ).all()
            return [_job_dto(session, job) for job in jobs]

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        result_json: str | None = None,
        error: str | None = None,
        finished_at: datetime | None = None,
        now: datetime | None = None,
    ) -> JobDto:
        with self.database.session() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise NotFound("Job not found.")
            job.status = status
            if result_json is not None:
                job.result_json = result_json
            if error is not None:
                job.error = error
            if finished_at is not None:
                job.finished_at = finished_at
            if now is not None:
                job.updated_at = now
            session.flush()
            return _job_dto(session, job)

    def add_job_event(
        self,
        job_id: str,
        *,
        status: str,
        details_json: str,
        now: datetime,
    ) -> None:
        with self.database.session() as session:
            session.add(
                JobEvent(
                    id=new_id(),
                    job_id=job_id,
                    status=status,
                    details_json=details_json,
                    created_at=now,
                )
            )

    def add_usage_event(
        self,
        *,
        project_id: str,
        job_id: str | None,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        request_evidence_json: str,
        now: datetime,
    ) -> None:
        with self.database.session() as session:
            session.add(
                UsageEvent(
                    id=new_id(),
                    project_id=project_id,
                    job_id=job_id,
                    provider=provider,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    request_evidence_json=request_evidence_json,
                    estimated_cost=None,
                    created_at=now,
                )
            )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------
