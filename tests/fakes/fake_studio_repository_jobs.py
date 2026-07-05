from __future__ import annotations

from datetime import datetime

from src.contexts.studio.application.ports.studio_repository import (
    JobDto,
    JobEventDto,
    ProjectDto,
)
from src.contexts.studio.domain.exceptions import InvalidOperation, NotFound
from src.contexts.studio.domain.types import JOB_KINDS
from src.contexts.studio.domain.utils import new_id

UsageEvent = dict[str, str | int | datetime | None]


class FakeStudioRepositoryJobsMixin:
    _jobs: dict[str, JobDto]
    _job_events: dict[str, list[JobEventDto]]
    _usage_events: list[UsageEvent]

    def _get_visible_project(
        self,
        project_id: str,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ProjectDto:
        raise NotImplementedError

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
        job = JobDto(
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
            events=[],
        )
        self._jobs[job.id] = job
        return job

    def get_job(
        self,
        project_id: str,
        job_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> JobDto:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        job = self._jobs.get(job_id)
        if job is None or job.project_id != project_id:
            raise NotFound("Job not found.")
        return job

    def list_jobs(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[JobDto]:
        self._get_visible_project(project_id, owner_id, guest_session_id)
        jobs = [job for job in self._jobs.values() if job.project_id == project_id]
        jobs.sort(key=lambda job: job.created_at, reverse=True)
        return jobs

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
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFound("Job not found.")
        updated = JobDto(
            id=job.id,
            project_id=job.project_id,
            document_id=job.document_id,
            kind=job.kind,
            operation=job.operation,
            status=status,
            provider=job.provider,
            model=job.model,
            request_json=job.request_json,
            result_json=result_json if result_json is not None else job.result_json,
            error=error if error is not None else job.error,
            retry_of_job_id=job.retry_of_job_id,
            created_at=job.created_at,
            updated_at=now if now is not None else job.updated_at,
            started_at=job.started_at,
            finished_at=finished_at if finished_at is not None else job.finished_at,
            events=job.events,
        )
        self._jobs[job_id] = updated
        return updated

    def add_job_event(
        self,
        job_id: str,
        *,
        status: str,
        details_json: str,
        now: datetime,
    ) -> None:
        event = JobEventDto(
            id=new_id(),
            job_id=job_id,
            status=status,
            details_json=details_json,
            created_at=now,
        )
        self._job_events.setdefault(job_id, []).append(event)
        job = self._jobs.get(job_id)
        if job is not None:
            self._jobs[job_id] = self._replace_job_events(job, self._job_events[job_id])

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
        self._usage_events.append(
            {
                "project_id": project_id,
                "job_id": job_id,
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "request_evidence_json": request_evidence_json,
                "created_at": now,
            }
        )

    def _replace_job_events(
        self,
        job: JobDto,
        events: list[JobEventDto],
    ) -> JobDto:
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
            events=list(events),
        )
