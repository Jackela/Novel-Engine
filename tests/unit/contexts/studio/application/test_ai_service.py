"""Unit tests for AIService using the fake repository and a mock provider."""

from __future__ import annotations

import json
from typing import cast

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationProviderName,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.studio.application.ports.ai_provider import (
    TextGenerationProviderFactory,
)
from src.contexts.studio.application.service_common import Principal
from src.contexts.studio.application.services.ai_service import AIService
from src.contexts.studio.application.services.project_service import ProjectService
from tests.fakes.fake_studio_repository import FakeStudioRepository


class _FakeTextGenerationProvider(TextGenerationProvider):
    """Mock provider that returns deterministic proposal text."""

    def __init__(self, content: dict[str, str] | None = None) -> None:
        self._content = content or {"chapter_markdown": "# Proposed\n\nNew text."}

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="fake",
            raw_text=json.dumps(self._content, ensure_ascii=False),
            content=self._content,
        )


class _FailingTextGenerationProvider(TextGenerationProvider):
    """Mock provider that always raises a provider error."""

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        del task
        raise TextGenerationProviderError("provider failure")


def _fake_provider_factory(
    provider: TextGenerationProviderName,
    model: str,
) -> TextGenerationProvider:
    del provider, model
    return _FakeTextGenerationProvider()


def _failing_provider_factory(
    provider: TextGenerationProviderName,
    model: str,
) -> TextGenerationProvider:
    del provider, model
    return _FailingTextGenerationProvider()


def _guest(session_id: str) -> Principal:
    return Principal(
        session_id=session_id,
        kind="guest",
        owner_id=None,
        expires_at=None,
    )


async def test_create_ai_proposal_persists_completed_job(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="AI Test"
    )
    document = project["documents"][0]
    service = AIService(
        fake_repository, cast(TextGenerationProviderFactory, _fake_provider_factory)
    )

    result = await service.create_ai_proposal(
        principal,
        project["id"],
        document["id"],
        operation="continue",
        instruction="Make it longer.",
    )

    assert result["status"] == "completed"
    assert result["kind"] == "proposal"
    assert "New text" in result["result"]["proposal_markdown"]
    assert result["result"]["base_revision_id"] == document["current_revision_id"]


async def test_create_ai_proposal_persists_failed_job_on_provider_error(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="AI Failure Test"
    )
    document = project["documents"][0]
    service = AIService(
        fake_repository, cast(TextGenerationProviderFactory, _failing_provider_factory)
    )

    result = await service.create_ai_proposal(
        principal,
        project["id"],
        document["id"],
        operation="continue",
        instruction="Make it longer.",
    )

    assert result["status"] == "failed"
    assert result["error"] == "provider failure"
    assert result["result"]["proposal_markdown"] == ""


async def test_generate_proposal_returns_proposal_and_base_revision(
    fake_repository: FakeStudioRepository,
) -> None:
    principal = _guest("guest-session-1")
    project = ProjectService(fake_repository).create_project(
        principal, title="Generate Test"
    )
    document = project["documents"][0]
    service = AIService(
        fake_repository, cast(TextGenerationProviderFactory, _fake_provider_factory)
    )

    proposal, base_revision_id, prompt_tokens, completion_tokens = await service.generate_proposal(
        principal,
        project["id"],
        document["id"],
        operation="continue",
        instruction="Make it longer.",
        provider="mock",
        model="fake-model",
    )

    assert base_revision_id == document["current_revision_id"]
    assert "New text" in proposal
    assert prompt_tokens >= 0
    assert completion_tokens >= 0
