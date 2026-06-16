from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    DocumentDto,
    InvalidOperation,
    JobDto,
    NotFound,
    Principal,
    RevisionDto,
    StudioRepository,
    TextGenerationProviderError,
    TextGenerationProviderFactory,
    TextGenerationProviderName,
    _job_payload,
    _owner_scopes,
    _sanitize_chapter_markdown,
    _word_count,
    cast,
    datetime,
    dump_json,
    load_json,
    logger,
    utcnow,
)
from src.contexts.studio.application.services.document_service import DocumentService

__all__ = ["AIService"]


class AIService:
    """AI-driven manuscript proposals."""

    def __init__(
        self,
        repository: StudioRepository,
        ai_provider_factory: TextGenerationProviderFactory,
    ) -> None:
        self._repository = repository
        self._ai_provider_factory = ai_provider_factory

    def _load_revision(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> tuple[DocumentDto, RevisionDto]:
        owner_id, guest_session_id = _owner_scopes(principal)
        document = self._repository.get_document(
            project_id,
            document_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        revision = document.current_revision
        if revision is None:
            raise InvalidOperation("Document has no current revision.")
        return document, revision

    async def _generate_proposal_text(
        self,
        revision: RevisionDto,
        *,
        operation: str,
        instruction: str,
        provider: str,
        model: str,
    ) -> str:
        from src.contexts.ai.application.ports.text_generation_port import (
            TextGenerationTask,
        )

        task = TextGenerationTask(
            step=operation,
            system_prompt=(
                "You are a novel-writing assistant. Produce the next revision of the "
                "attached manuscript as markdown. Return JSON with a single "
                "'chapter_markdown' string."
            ),
            user_prompt=(
                f"Operation: {operation}\n"
                f"Instruction: {instruction.strip()}\n\n"
                "Current manuscript:\n\n"
                f"{revision.content_markdown}"
            ),
            response_schema={"chapter_markdown": {"type": "string"}},
            metadata={
                "operation": operation,
                "document_id": revision.document_id,
                "base_revision_id": revision.id,
            },
        )
        generation_provider = self._ai_provider_factory(
            cast(TextGenerationProviderName, provider),
            model,
        )
        try:
            result = await generation_provider.generate_structured(task)
            proposal_markdown = result.content.get("chapter_markdown") or result.raw_text
            return _sanitize_chapter_markdown(str(proposal_markdown))
        finally:
            close = getattr(generation_provider, "aclose", None)
            if close is not None:
                await close()

    async def generate_proposal(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        operation: str,
        instruction: str,
        provider: str,
        model: str,
    ) -> tuple[str, str]:
        """Generate a proposal and return ``(proposal_markdown, base_revision_id)``."""
        _document, revision = self._load_revision(principal, project_id, document_id)
        proposal = await self._generate_proposal_text(
            revision,
            operation=operation,
            instruction=instruction,
            provider=provider,
            model=model,
        )
        return proposal, revision.id

    async def create_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        operation: str,
        instruction: str,
        provider: str = "mock",
        model: str = "studio-copilot-v1",
    ) -> dict[str, Any]:
        _document, revision = self._load_revision(principal, project_id, document_id)
        now = utcnow()
        try:
            proposal_markdown = _sanitize_chapter_markdown(
                await self._generate_proposal_text(
                    revision,
                    operation=operation,
                    instruction=instruction,
                    provider=provider,
                    model=model,
                )
            )
        except TextGenerationProviderError as exc:
            logger.exception(
                "ai_proposal_failed",
                extra={
                    "project_id": project_id,
                    "document_id": document_id,
                    "operation": operation,
                    "provider": provider,
                    "model": model,
                },
            )
            return self._persist_failed_ai_job(
                project_id=project_id,
                document_id=document_id,
                operation=operation,
                provider=provider,
                model=model,
                instruction=instruction,
                base_revision_id=revision.id,
                error=str(exc),
                now=now,
            )
        return self._persist_completed_ai_job(
            project_id=project_id,
            document_id=document_id,
            operation=operation,
            provider=provider,
            model=model,
            instruction=instruction,
            base_revision_id=revision.id,
            proposal_markdown=proposal_markdown,
            now=now,
        )

    def _persist_failed_ai_job(
        self,
        *,
        project_id: str,
        document_id: str,
        operation: str,
        provider: str,
        model: str,
        instruction: str,
        base_revision_id: str,
        error: str,
        now: datetime,
    ) -> dict[str, Any]:
        job = self._create_ai_job(
            project_id=project_id,
            document_id=document_id,
            operation=operation,
            provider=provider,
            model=model,
            instruction=instruction,
            base_revision_id=base_revision_id,
            status="failed",
            proposal_markdown="",
            error=error,
            event_details={"error": error},
            now=now,
        )
        return _job_payload(job)

    def _persist_completed_ai_job(
        self,
        *,
        project_id: str,
        document_id: str,
        operation: str,
        provider: str,
        model: str,
        instruction: str,
        base_revision_id: str,
        proposal_markdown: str,
        now: datetime,
    ) -> dict[str, Any]:
        job = self._create_ai_job(
            project_id=project_id,
            document_id=document_id,
            operation=operation,
            provider=provider,
            model=model,
            instruction=instruction,
            base_revision_id=base_revision_id,
            status="completed",
            proposal_markdown=proposal_markdown,
            error=None,
            event_details={"proposal_only": True},
            now=now,
        )
        self._repository.add_usage_event(
            project_id=project_id,
            job_id=job.id,
            provider=provider,
            model=model,
            prompt_tokens=_word_count(instruction),
            completion_tokens=_word_count(proposal_markdown),
            request_evidence_json=dump_json(
                {"operation": operation, "base_revision_id": base_revision_id}
            ),
            now=now,
        )
        return _job_payload(job)

    def _create_ai_job(
        self,
        *,
        project_id: str,
        document_id: str,
        operation: str,
        provider: str,
        model: str,
        instruction: str,
        base_revision_id: str,
        status: str,
        proposal_markdown: str,
        error: str | None,
        event_details: dict[str, Any],
        now: datetime,
    ) -> JobDto:
        job = self._repository.create_job(
            project_id=project_id,
            document_id=document_id,
            kind="proposal",
            operation=operation,
            status=status,
            provider=provider,
            model=model,
            request_json=self._proposal_request_json(
                operation=operation,
                instruction=instruction,
                base_revision_id=base_revision_id,
            ),
            result_json=self._proposal_result_json(
                base_revision_id=base_revision_id,
                proposal_markdown=proposal_markdown,
            ),
            error=error,
            retry_of_job_id=None,
            now=now,
        )
        self._repository.add_job_event(
            job.id,
            status=status,
            details_json=dump_json(event_details),
            now=now,
        )
        return job

    @staticmethod
    def _proposal_request_json(
        *,
        operation: str,
        instruction: str,
        base_revision_id: str,
    ) -> str:
        return dump_json(
            {
                "operation": operation,
                "instruction": instruction,
                "base_revision_id": base_revision_id,
            }
        )

    @staticmethod
    def _proposal_result_json(
        *,
        base_revision_id: str,
        proposal_markdown: str,
    ) -> str:
        return dump_json(
            {
                "proposal_markdown": proposal_markdown,
                "base_revision_id": base_revision_id,
                "accepted_revision_id": None,
            }
        )

    def accept_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        job = self._repository.get_job(
            project_id,
            job_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        if job.kind != "proposal" or job.document_id is None:
            raise NotFound("AI proposal not found.")
        result = cast(dict[str, Any], load_json(job.result_json))
        request = cast(dict[str, Any], load_json(job.request_json))
        if result.get("accepted_revision_id"):
            return _job_payload(job)
        document_id = job.document_id
        proposal = str(result.get("proposal_markdown", ""))
        base_revision_id = cast(str | None, request.get("base_revision_id"))

        document_service = DocumentService(self._repository)
        saved = document_service.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=proposal,
            base_revision_id=base_revision_id,
            metadata={"ai_job_id": job_id},
            source="ai-accepted",
        )

        result["accepted_revision_id"] = saved["current_revision_id"]
        updated = self._repository.update_job(
            job_id,
            status=job.status,
            result_json=dump_json(result),
            now=utcnow(),
        )
        return _job_payload(updated)
