from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload

from src.contexts.studio.infrastructure.models import JobEvent
from src.contexts.studio.infrastructure.repository.common import (
    JOB_KINDS,
    InvalidOperation,
    Job,
    JobDto,
    NotFound,
    Project,
    Session,
    StudioDatabase,
    UsageEvent,
    _job_dto,
    datetime,
    new_id,
    select,
)

__all__ = ["JobRepositoryMixin"]


class JobRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

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
                .options(selectinload(Job.events))
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
