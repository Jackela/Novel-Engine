from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
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
]


@dataclass
class OwnerDto:
    id: str
    username: str
    password_hash: str
    created_at: datetime


@dataclass
class SessionDto:
    id: str
    kind: str
    owner_id: str | None
    token_hash: str
    csrf_token: str | None
    created_at: datetime
    expires_at: datetime | None
    last_seen_at: datetime


@dataclass
class RevisionDto:
    id: str
    document_id: str
    parent_revision_id: str | None
    revision_number: int
    content_markdown: str
    metadata_json: str
    source: str
    created_at: datetime


@dataclass
class DocumentDto:
    id: str
    project_id: str
    kind: str
    title: str
    position: int
    current_revision_id: str | None
    created_at: datetime
    updated_at: datetime
    current_revision: RevisionDto | None = None


@dataclass
class SnapshotDocumentDto:
    document_id: str
    revision_id: str
    position: int


@dataclass
class SnapshotDto:
    id: str
    project_id: str
    reason: str
    created_at: datetime
    documents: list[SnapshotDocumentDto] = field(default_factory=list)


@dataclass
class ReviewIssueDto:
    id: str
    document_id: str | None
    severity: str
    code: str
    message: str
    suggestion: str
    evidence_json: str


@dataclass
class ReviewDto:
    id: str
    project_id: str
    snapshot_id: str
    provider: str
    model: str
    summary: str
    created_at: datetime
    issues: list[ReviewIssueDto] = field(default_factory=list)


@dataclass
class ExportDto:
    id: str
    project_id: str
    snapshot_id: str
    format: str
    relative_path: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime


@dataclass
class JobEventDto:
    id: str
    job_id: str
    status: str
    details_json: str
    created_at: datetime


@dataclass
class JobDto:
    id: str
    project_id: str
    document_id: str | None
    kind: str
    operation: str
    status: str
    provider: str
    model: str
    request_json: str
    result_json: str
    error: str | None
    retry_of_job_id: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    events: list[JobEventDto] = field(default_factory=list)


@dataclass
class ProjectDto:
    id: str
    owner_id: str | None
    guest_session_id: str | None
    title: str
    description: str
    settings_json: str
    import_hash: str | None
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentDto] | None = None
