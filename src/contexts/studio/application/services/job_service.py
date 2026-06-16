from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    ExportFormat,
    InvalidOperation,
    JobDto,
    NotFound,
    Principal,
    StudioRepository,
    TextGenerationProviderError,
    _job_payload,
    _owner_scopes,
    _safe_load_json,
    cast,
    dump_json,
    logger,
    utcnow,
)

from .ai_service import AIService
from .export_service import ExportService
from .review_service import ReviewService

__all__ = ["JobService"]


class JobService:
    """Durable job execution, retry, and history."""

    def __init__(
        self,
        repository: StudioRepository,
        ai_service: AIService,
        review_service: ReviewService,
        export_service: ExportService,
    ) -> None:
        self._repository = repository
        self._ai_service = ai_service
        self._review_service = review_service
        self._export_service = export_service

    def list_jobs(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        jobs = self._repository.list_jobs(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return [_job_payload(job) for job in jobs]

    async def retry_job(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        original = self._repository.get_job(
            project_id,
            job_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        if original.status not in {"failed", "interrupted"}:
            raise InvalidOperation("Only failed or interrupted jobs may be retried.")
        now = utcnow()
        retry = self._repository.create_job(
            project_id=original.project_id,
            document_id=original.document_id,
            kind=original.kind,
            operation=original.operation,
            status="running",
            provider=original.provider,
            model=original.model,
            request_json=original.request_json,
            result_json="{}",
            error=None,
            retry_of_job_id=original.id,
            now=now,
        )
        self._repository.add_job_event(
            retry.id,
            status="running",
            details_json=dump_json({"retry_of": original.id}),
            now=now,
        )

        try:
            if retry.kind == "proposal":
                return await self._retry_ai_job(principal, retry)
            if retry.kind == "review":
                return await self._retry_review_job(principal, retry)
            if retry.kind == "export":
                return await self._retry_export_job(principal, retry)
            raise InvalidOperation(f"Unsupported job kind for retry: {retry.kind}")
        except (InvalidOperation, NotFound, TextGenerationProviderError) as exc:
            logger.exception(
                "job_retry_failed",
                extra={
                    "project_id": project_id,
                    "job_id": job_id,
                    "retry_job_id": retry.id,
                    "kind": retry.kind,
                },
            )
            return self._fail_retry(retry.id, str(exc))

    async def _retry_ai_job(
        self,
        principal: Principal,
        retry: JobDto,
    ) -> dict[str, Any]:
        request = cast(dict[str, Any], _safe_load_json(retry.request_json))
        base_revision_id = cast(str | None, request.get("base_revision_id"))
        instruction = str(request.get("instruction", ""))
        if not base_revision_id or retry.document_id is None:
            raise InvalidOperation("Original AI job is missing base_revision_id.")
        (
            proposal_markdown,
            generated_base_revision_id,
            prompt_tokens,
            completion_tokens,
        ) = await self._ai_service.generate_proposal(
            principal,
            retry.project_id,
            retry.document_id,
            operation=retry.operation,
            instruction=instruction,
            provider=retry.provider,
            model=retry.model,
        )
        now = utcnow()
        updated = self._repository.update_job(
            retry.id,
            status="completed",
            result_json=dump_json(
                {
                    "proposal_markdown": proposal_markdown,
                    "base_revision_id": generated_base_revision_id,
                    "accepted_revision_id": None,
                }
            ),
            finished_at=now,
            now=now,
        )
        self._repository.add_job_event(
            retry.id,
            status="completed",
            details_json=dump_json({"proposal_only": True}),
            now=now,
        )
        self._repository.add_usage_event(
            project_id=retry.project_id,
            job_id=retry.id,
            provider=retry.provider,
            model=retry.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            request_evidence_json=dump_json(
                {"operation": retry.operation, "base_revision_id": generated_base_revision_id}
            ),
            now=now,
        )
        return _job_payload(updated)

    async def _retry_review_job(
        self,
        principal: Principal,
        retry: JobDto,
    ) -> dict[str, Any]:
        review = self._review_service.review_project(
            principal,
            retry.project_id,
            provider=retry.provider or "deterministic",
            model=retry.model or "studio-review-v1",
        )
        now = utcnow()
        updated = self._repository.update_job(
            retry.id,
            status="completed",
            result_json=dump_json(
                {
                    "review_id": review["id"],
                    "snapshot_id": review["snapshot_id"],
                    "summary": review["summary"],
                }
            ),
            finished_at=now,
            now=now,
        )
        self._repository.add_job_event(
            retry.id,
            status="completed",
            details_json=dump_json({"review_id": review["id"]}),
            now=now,
        )
        return _job_payload(updated)

    async def _retry_export_job(
        self,
        principal: Principal,
        retry: JobDto,
    ) -> dict[str, Any]:
        export = self._export_service.export_project(
            principal,
            retry.project_id,
            export_format=cast(ExportFormat, retry.operation),
        )
        now = utcnow()
        updated = self._repository.update_job(
            retry.id,
            status="completed",
            result_json=dump_json(
                {
                    "export_id": export["id"],
                    "snapshot_id": export["snapshot_id"],
                    "format": export["format"],
                    "download_url": export["download_url"],
                }
            ),
            finished_at=now,
            now=now,
        )
        self._repository.add_job_event(
            retry.id,
            status="completed",
            details_json=dump_json({"export_id": export["id"]}),
            now=now,
        )
        return _job_payload(updated)

    def _fail_retry(self, retry_id: str, error_message: str) -> dict[str, Any]:
        now = utcnow()
        updated = self._repository.update_job(
            retry_id,
            status="failed",
            error=error_message,
            finished_at=now,
            now=now,
        )
        self._repository.add_job_event(
            retry_id,
            status="failed",
            details_json=dump_json({"error": error_message}),
            now=now,
        )
        return _job_payload(updated)
