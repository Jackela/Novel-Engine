from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from src.contexts.studio.application.ports.studio_repository_sections import (
    DocumentDto,
    ExportDto,
    JobDto,
    ReviewDto,
    RevisionDto,
    SnapshotDto,
    StudioRepositoryCorePort,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    JobEventDto as JobEventDto,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    OwnerDto as OwnerDto,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    ProjectDto as ProjectDto,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    ReviewIssueDto as ReviewIssueDto,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    SessionDto as SessionDto,
)
from src.contexts.studio.application.ports.studio_repository_sections import (
    SnapshotDocumentDto as SnapshotDocumentDto,
)


@runtime_checkable
class StudioRepository(StudioRepositoryCorePort, Protocol):
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
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[tuple[DocumentDto, RevisionDto]]:
        """Return the document/revision pairs captured by a visible snapshot."""
        ...

    def snapshot_revision_map(
        self,
        snapshot_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> dict[str, str]:
        """Return ``{document_id: revision_id}`` for a visible snapshot."""
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
