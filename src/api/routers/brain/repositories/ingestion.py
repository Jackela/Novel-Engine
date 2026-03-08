"""
Ingestion Job Repository

In-memory store for async ingestion jobs.
OPT-005: Async Ingestion Job API
"""

from __future__ import annotations

import asyncio
import structlog
import uuid
from datetime import UTC, datetime
from typing import Any

from src.api.schemas import IngestionJobResponse, IngestionJobStatus

logger = structlog.get_logger(__name__)


class IngestionJob:
    """
    An async ingestion job.

    Attributes:
        job_id: Unique identifier for the job
        status: Current job status
        progress: Progress percentage (0-100)
        source_id: ID of the source being ingested
        source_type: Type of source
        content: Content to ingest
        tags: Optional tags
        extra_metadata: Optional additional metadata
        created_at: When the job was created
        started_at: When the job started processing
        completed_at: When the job completed
        error: Error message if job failed
        chunk_count: Number of chunks created
        entries_created: Number of entries created
    """

    def __init__(
        self,
        job_id: str,
        source_id: str,
        source_type: str,
        content: str,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.job_id = job_id
        self.status = IngestionJobStatus.PENDING
        self.progress = 0.0
        self.source_id = source_id
        self.source_type = source_type
        self.content = content
        self.tags = tags
        self.extra_metadata = extra_metadata
        self.created_at = datetime.now(UTC)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.error: str | None = None
        self.chunk_count: int | None = None
        self.entries_created: int | None = None

    def to_response(self) -> IngestionJobResponse:
        """Convert to API response model."""
        return IngestionJobResponse(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            source_id=self.source_id,
            source_type=self.source_type,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            error=self.error,
            chunk_count=self.chunk_count,
            entries_created=self.entries_created,
        )


class IngestionJobStore:
    """
    In-memory store for async ingestion jobs.

    Why:
        - Track job status across async operations
        - Allow clients to poll for status updates
        - Simple implementation for now; can be replaced with Redis/DB later
    """

    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        source_id: str,
        source_type: str,
        content: str,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> IngestionJob:
        """Create a new ingestion job."""
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            source_id=source_id,
            source_type=source_type,
            content=content,
            tags=tags,
            extra_metadata=extra_metadata,
        )

        async with self._lock:
            self._jobs[job_id] = job

        logger.info(
            "ingestion_job_created",
            job_id=job_id,
            source_id=source_id,
            source_type=source_type,
        )

        return job

    async def get_job(self, job_id: str) -> IngestionJob | None:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job(
        self,
        job_id: str,
        status: IngestionJobStatus | None = None,
        progress: float | None = None,
        error: str | None = None,
        chunk_count: int | None = None,
        entries_created: int | None = None,
    ) -> IngestionJob | None:
        """Update job status."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            if status is not None:
                job.status = status
                if status == IngestionJobStatus.RUNNING and job.started_at is None:
                    job.started_at = datetime.now(UTC)
                elif status in (
                    IngestionJobStatus.COMPLETED,
                    IngestionJobStatus.FAILED,
                    IngestionJobStatus.CANCELLED,
                ):
                    if job.completed_at is None:
                        job.completed_at = datetime.now(UTC)

            if progress is not None:
                job.progress = progress

            if error is not None:
                job.error = error

            if chunk_count is not None:
                job.chunk_count = chunk_count

            if entries_created is not None:
                job.entries_created = entries_created

            return job

    async def list_jobs(self, limit: int = 100) -> list[IngestionJob]:
        """List all jobs, most recent first."""
        async with self._lock:
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


__all__ = ["IngestionJob", "IngestionJobStore"]
