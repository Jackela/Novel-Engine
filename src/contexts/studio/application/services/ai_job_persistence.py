from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.contexts.studio.application.service_common import (
    JobDto,
    StudioRepository,
    _job_payload,
    _word_count,
    dump_json,
)


def resolved_token_count(value: int | None, text: str) -> int:
    return value if value is not None else _word_count(text)


@dataclass(frozen=True, slots=True)
class AIProposalJobInput:
    project_id: str
    document_id: str
    operation: str
    provider: str
    model: str
    instruction: str
    base_revision_id: str
    now: datetime


@dataclass(frozen=True, slots=True)
class AIProposalJobResult:
    proposal_markdown: str
    prompt_tokens: int | None
    completion_tokens: int | None


@dataclass(frozen=True, slots=True)
class _AIJobState:
    status: str
    proposal_markdown: str
    error: str | None
    event_details: dict[str, Any]


class AIJobPersistence:
    def __init__(self, repository: StudioRepository) -> None:
        self._repository = repository

    def persist_failed(
        self,
        request: AIProposalJobInput,
        *,
        error: str,
    ) -> dict[str, Any]:
        job = self._create_job(
            request,
            _AIJobState(
                status="failed",
                proposal_markdown="",
                error=error,
                event_details={"error": error},
            ),
        )
        return _job_payload(job)

    def persist_completed(
        self,
        request: AIProposalJobInput,
        result: AIProposalJobResult,
    ) -> dict[str, Any]:
        job = self._create_job(
            request,
            _AIJobState(
                status="completed",
                proposal_markdown=result.proposal_markdown,
                error=None,
                event_details={"proposal_only": True},
            ),
        )
        self._repository.add_usage_event(
            project_id=request.project_id,
            job_id=job.id,
            provider=request.provider,
            model=request.model,
            prompt_tokens=resolved_token_count(
                result.prompt_tokens,
                request.instruction,
            ),
            completion_tokens=resolved_token_count(
                result.completion_tokens,
                result.proposal_markdown,
            ),
            request_evidence_json=dump_json(
                {
                    "operation": request.operation,
                    "base_revision_id": request.base_revision_id,
                }
            ),
            now=request.now,
        )
        return _job_payload(job)

    def _create_job(
        self,
        request: AIProposalJobInput,
        state: _AIJobState,
    ) -> JobDto:
        job = self._repository.create_job(
            project_id=request.project_id,
            document_id=request.document_id,
            kind="proposal",
            operation=request.operation,
            status=state.status,
            provider=request.provider,
            model=request.model,
            request_json=self._proposal_request_json(request),
            result_json=self._proposal_result_json(request, state.proposal_markdown),
            error=state.error,
            retry_of_job_id=None,
            now=request.now,
        )
        self._repository.add_job_event(
            job.id,
            status=state.status,
            details_json=dump_json(state.event_details),
            now=request.now,
        )
        return job

    @staticmethod
    def _proposal_request_json(request: AIProposalJobInput) -> str:
        return dump_json(
            {
                "operation": request.operation,
                "instruction": request.instruction,
                "base_revision_id": request.base_revision_id,
            }
        )

    @staticmethod
    def _proposal_result_json(
        request: AIProposalJobInput,
        proposal_markdown: str,
    ) -> str:
        return dump_json(
            {
                "proposal_markdown": proposal_markdown,
                "base_revision_id": request.base_revision_id,
                "accepted_revision_id": None,
            }
        )
