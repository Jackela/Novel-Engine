"""Repository port for the Studio application layer.

This module defines the abstract contract that the application services use
to persist and query Studio aggregates. Concrete implementations live in the
infrastructure layer and may use SQLAlchemy, an in-memory store, or any other
storage backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class OwnerDto:
    """Data transfer object for a local owner account."""

    id: str
    username: str
    password_hash: str
    created_at: datetime


@dataclass
class SessionDto:
    """Data transfer object for an authenticated session."""

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
    """Data transfer object for a document revision."""

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
    """Data transfer object for a project document."""

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
    """Data transfer object for a document pinned in a snapshot."""

    document_id: str
    revision_id: str
    position: int


@dataclass
class SnapshotDto:
    """Data transfer object for a project snapshot."""

    id: str
    project_id: str
    reason: str
    created_at: datetime
    documents: list[SnapshotDocumentDto] = field(default_factory=list)


@dataclass
class ReviewIssueDto:
    """Data transfer object for an issue raised by a review."""

    id: str
    document_id: str | None
    severity: str
    code: str
    message: str
    suggestion: str
    evidence_json: str


@dataclass
class ReviewDto:
    """Data transfer object for a project review run."""

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
    """Data transfer object for a generated export artifact."""

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
    """Data transfer object for a job lifecycle event."""

    id: str
    job_id: str
    status: str
    details_json: str
    created_at: datetime


@dataclass
class JobDto:
    """Data transfer object for a durable background job."""

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
    """Data transfer object for a novel project."""

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


@runtime_checkable
class StudioRepository(Protocol):
    """Abstract port for all Studio persistence operations.

    Implementations are responsible for translating between aggregate DTOs and
    their concrete storage representation. The ``database`` attribute is exposed
    so that application diagnostics (health checks, CLI tools) can reach the
    underlying infrastructure without the application layer importing it.
    """

    database: Any

    # ------------------------------------------------------------------
    # Owner and authentication
    # ------------------------------------------------------------------
    def owner_exists(self) -> bool:
        """Return whether at least one owner has been configured."""
        ...

    def get_owner_by_username(self, username: str) -> OwnerDto | None:
        """Look up an owner by username."""
        ...

    def get_first_owner(self) -> OwnerDto | None:
        """Return the oldest configured owner, or ``None`` if none exist."""
        ...

    def create_owner(self, username: str, password_hash: str) -> OwnerDto:
        """Create the first local owner account."""
        ...

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
        """Persist a new session record."""
        ...

    def get_session_by_token_hash(self, token_hash: str) -> SessionDto | None:
        """Fetch a session by the hash of its bearer token."""
        ...

    def delete_session(self, session_id: str) -> None:
        """Delete a session record by id."""
        ...

    def delete_expired_guest_sessions(self, now: datetime) -> int:
        """Delete all guest sessions that have expired; return the count."""
        ...

    def update_session_last_seen(self, session_id: str, last_seen_at: datetime) -> None:
        """Update the last seen timestamp for a session."""
        ...

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
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
        """Create and persist a new project.

        When ``create_seed`` is true the project is created together with an
        initial ``chapter`` document so that authors have somewhere to start.
        """
        ...

    def list_projects(
        self,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ProjectDto]:
        """List projects visible to the principal, newest first."""
        ...

    def get_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        """Fetch a project visible to the principal.

        Raises a ``LookupError`` when the project is not visible.
        """
        ...

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
        """Update a project's mutable fields."""
        ...

    def delete_project(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        """Delete a visible project and all dependent Studio records."""
        ...

    def find_project_by_import_hash(self, import_hash: str) -> ProjectDto | None:
        """Look up a project by its legacy import hash."""
        ...

    def set_project_import_hash(self, project_id: str, import_hash: str) -> None:
        """Assign an import hash to an existing project."""
        ...

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
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
        """Create a document together with its first revision."""
        ...

    def list_documents(self, project_id: str) -> list[DocumentDto]:
        """List all documents in a project ordered for presentation."""
        ...

    def get_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> DocumentDto:
        """Fetch a document visible to the principal."""
        ...

    def delete_document(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> None:
        """Delete a visible document and all dependent document records."""
        ...

    def next_document_position(self, project_id: str, kind: str) -> int:
        """Return the next available position for a document kind."""
        ...

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
        """Save a new revision of a document.

        Raises ``ValueError`` when the base revision no longer matches the
        current revision.
        """
        ...

    def get_revision(
        self,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> RevisionDto:
        """Fetch a single revision visible to the principal."""
        ...

    def list_revisions(
        self,
        project_id: str,
        document_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[RevisionDto]:
        """List revisions for a document, newest first."""
        ...

    def reorder_documents(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
        document_ids: list[str],
        now: datetime,
    ) -> list[DocumentDto]:
        """Reorder all documents in a project."""
        ...

    def search_documents(
        self,
        project_id: str,
        query: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[dict[str, Any]]:
        """Full-text search within a project using the backend search index."""
        ...

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
        """Create a snapshot of all current document revisions."""
        ...

    def list_snapshots(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[SnapshotDto]:
        """List snapshots for a project."""
        ...

    def get_latest_export_snapshot(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> SnapshotDto | None:
        """Return the most recent export snapshot for a project, if any."""
        ...

    def snapshot_content(
        self,
        snapshot_id: str,
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        """Return the document/revision pairs captured by a snapshot."""
        ...

    def snapshot_revision_map(self, snapshot_id: str) -> dict[str, str]:
        """Return ``{document_id: revision_id}`` for a snapshot."""
        ...

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
        """Run a review, snapshot the project, and record issues."""
        ...

    def list_reviews(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ReviewDto]:
        """List reviews for a project."""
        ...

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
        """Persist an export record."""
        ...

    def list_exports(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ExportDto]:
        """List exports for a project."""
        ...

    def get_export(
        self,
        project_id: str,
        export_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ExportDto:
        """Fetch an export record visible to the principal."""
        ...

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
        """Persist a new job record."""
        ...

    def get_job(
        self,
        project_id: str,
        job_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> JobDto:
        """Fetch a job visible to the principal."""
        ...

    def list_jobs(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[JobDto]:
        """List jobs for a project."""
        ...

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
        """Update a job's status and optional result/error fields."""
        ...

    def add_job_event(
        self,
        job_id: str,
        *,
        status: str,
        details_json: str,
        now: datetime,
    ) -> None:
        """Append a lifecycle event to a job."""
        ...

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
        """Record a usage event for a completed generation."""
        ...
