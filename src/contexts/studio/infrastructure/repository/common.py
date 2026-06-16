"""SQLAlchemy implementation of the Studio repository port."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
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
from src.contexts.studio.infrastructure.database import StudioDatabase, UnitOfWork
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
    SessionRecord,
    UsageEvent,
)


@contextmanager
def _session(
    database: StudioDatabase,
    session: Session | None = None,
) -> Iterator[Session]:
    """Yield a shared session or a fresh transactional session."""
    if session is not None:
        yield session
        return
    with database.session() as new_session:
        yield new_session


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
    del session
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
            for item in snapshot.snapshot_documents
        ],
    )


def _review_dto(session: Session, review: Review) -> ReviewDto:
    del session
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
            for issue in review.issues
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
    del session
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
        events=[_job_event_dto(event) for event in job.events],
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

__all__ = [
    "Any",
    "cast",
    "datetime",
    "func",
    "select",
    "text",
    "Session",
    "UnitOfWork",
    "_session",
    "DocumentDto",
    "ExportDto",
    "JobDto",
    "JobEventDto",
    "OwnerDto",
    "ProjectDto",
    "ReviewDto",
    "ReviewIssueDto",
    "RevisionDto",
    "SessionDto",
    "SnapshotDocumentDto",
    "SnapshotDto",
    "InvalidOperation",
    "NotFound",
    "JOB_KINDS",
    "_word_count",
    "dump_json",
    "new_id",
    "utcnow",
    "StudioDatabase",
    "Document",
    "DocumentRevision",
    "Export",
    "Job",
    "Owner",
    "Project",
    "ProjectSnapshot",
    "Review",
    "SessionRecord",
    "UsageEvent",
    "_owner_dto",
    "_session_dto",
    "_revision_dto",
    "_document_dto",
    "_snapshot_dto",
    "_review_dto",
    "_job_event_dto",
    "_job_dto",
    "_export_dto",
]
