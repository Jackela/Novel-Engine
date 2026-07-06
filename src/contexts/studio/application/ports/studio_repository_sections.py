from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


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


class StudioRepositoryCorePort(Protocol):
    def health_check(self) -> bool: ...

    def owner_exists(self) -> bool: ...

    def get_owner_by_username(self, username: str) -> OwnerDto | None: ...

    def get_first_owner(self) -> OwnerDto | None: ...

    def create_owner(self, username: str, password_hash: str) -> OwnerDto: ...

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
    ) -> SessionDto: ...

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None: ...

    def delete_session(self, session_id: str) -> None: ...

    def delete_expired_guest_sessions(self, now: datetime) -> int: ...

    def update_session_last_seen(
        self, session_id: str, last_seen_at: datetime
    ) -> None: ...

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
    ) -> ProjectDto: ...

    def list_projects(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ProjectDto]: ...

    def get_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto: ...

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
    ) -> ProjectDto: ...

    def delete_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None: ...

    def find_project_by_import_hash(
        self,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto | None: ...

    def set_project_import_hash(
        self,
        project_id: str,
        import_hash: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None: ...

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
    ) -> DocumentDto: ...

    def list_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[DocumentDto]: ...

    def get_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> DocumentDto: ...

    def delete_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None: ...

    def next_document_position(self, project_id: str, kind: str) -> int: ...

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
    ) -> DocumentDto: ...

    def get_revision(
        self,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> RevisionDto: ...

    def list_revisions(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[RevisionDto]: ...

    def reorder_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        document_ids: list[str],
        now: datetime,
    ) -> list[DocumentDto]: ...

    def search_documents(
        self,
        project_id: str,
        query: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[dict[str, Any]]: ...
