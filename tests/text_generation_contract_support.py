"""Shared structured contract helpers for text generation provider tests."""

from __future__ import annotations

import json
from typing import Any, Final

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings

DASHSCOPE_DEFAULT_BASE: Final[str] = "https://dashscope.aliyuncs.com/api/v1"
CONTRACT_STORY_TITLE: Final[str] = "Contract Story"
CONTRACT_STORY_GENRE: Final[str] = "fantasy"
CONTRACT_STORY_PREMISE: Final[str] = (
    "A courier discovers the map of a kingdom that is rewriting itself."
)

TextGenerationContractCase = tuple[str, TextGenerationTask]


def _chapter_response_schema() -> dict[str, Any]:
    return {
        "chapter_markdown": {"type": "string"},
        "sidecar_metadata": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "characters": {"type": "array"},
                "promises": {"type": "array"},
            },
        },
    }


def build_contract_cases() -> list[TextGenerationContractCase]:
    """Build the canonical structured tasks used across provider tests."""
    draft_task = TextGenerationTask(
        step="chapter_draft",
        system_prompt=(
            "You draft complete fiction chapters. Return JSON with chapter_markdown "
            "and sidecar_metadata."
        ),
        user_prompt=(
            f"Story title: {CONTRACT_STORY_TITLE}\n"
            f"Genre: {CONTRACT_STORY_GENRE}\n"
            f"Premise: {CONTRACT_STORY_PREMISE}\n"
            "Chapter number: 1"
        ),
        response_schema=_chapter_response_schema(),
        temperature=0.6,
        metadata={
            "title": CONTRACT_STORY_TITLE,
            "genre": CONTRACT_STORY_GENRE,
            "premise": CONTRACT_STORY_PREMISE,
            "tone": "commercial web fiction",
            "chapter_number": 1,
            "previous_summaries": [],
            "unresolved_promises": [],
            "character_state": [],
        },
    )
    revision_task = TextGenerationTask(
        step="chapter_revision",
        system_prompt=(
            "You revise complete fiction chapters. Return JSON with "
            "chapter_markdown and sidecar_metadata."
        ),
        user_prompt=(
            f"Story title: {CONTRACT_STORY_TITLE}\n"
            "Chapter number: 1\n"
            "Current chapter: A thin scene needs a stronger emotional turn.\n"
            "Brief: rewrite the complete chapter as natural prose."
        ),
        response_schema=_chapter_response_schema(),
        temperature=0.45,
        metadata={
            "title": CONTRACT_STORY_TITLE,
            "genre": CONTRACT_STORY_GENRE,
            "premise": CONTRACT_STORY_PREMISE,
            "chapter_number": 1,
            "current_summary": "A thin scene needs a stronger emotional turn.",
            "revision_issues": [
                {
                    "code": "thin_chapter",
                    "severity": "warning",
                    "location": "chapter-001",
                }
            ],
        },
    )
    return [
        ("chapter_draft", draft_task),
        ("chapter_revision", revision_task),
    ]


def resolve_dashscope_credentials() -> tuple[str, str]:
    """Resolve DashScope credentials for secret-gated live tests."""
    settings = NovelEngineSettings()
    api_key = settings.llm.dashscope_api_key
    if not api_key:
        pytest.skip(
            "Set ENABLE_DASHSCOPE_TESTS=1 and provide DASHSCOPE_API_KEY in your "
            "environment or .env.local to run DashScope live tests."
        )

    api_base = settings.llm.resolved_api_base("dashscope") or DASHSCOPE_DEFAULT_BASE
    return api_key, api_base


def assert_structured_contract_result(
    result: TextGenerationResult,
    case: TextGenerationContractCase,
    *,
    provider_name: str,
    model_name: str,
    strict: bool,
) -> None:
    """Assert the shared structured contract across providers."""
    step, task = case
    assert result.step == task.step == step
    assert result.provider == provider_name
    assert result.model == model_name
    assert result.raw_text.strip()

    raw_payload = json.loads(result.raw_text)
    assert isinstance(raw_payload, dict)
    assert raw_payload == result.content
    assert isinstance(result.content, dict)
    _assert_chapter_payload(result.content, strict=strict)


def _assert_chapter_payload(payload: dict[str, Any], *, strict: bool) -> None:
    markdown = payload.get("chapter_markdown")
    sidecar = payload.get("sidecar_metadata")
    assert isinstance(markdown, str)
    assert markdown.strip()
    assert isinstance(sidecar, dict)

    summary = sidecar.get("summary")
    assert isinstance(summary, str)
    assert summary.strip()

    if strict:
        assert markdown.lstrip().startswith("# Chapter")
        characters = sidecar.get("characters")
        promises = sidecar.get("promises")
        assert isinstance(characters, list)
        assert characters
        assert isinstance(promises, list)
