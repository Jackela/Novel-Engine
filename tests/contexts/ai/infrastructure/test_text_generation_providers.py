"""Mocked text-generation provider resilience tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.provider_factory import (
    create_text_generation_provider,
)
from src.contexts.ai.infrastructure.providers.unconfigured_text_generation_provider import (
    UnconfiguredTextGenerationProvider,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings


def _task(
    step: str = "bible",
    response_schema: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> TextGenerationTask:
    return TextGenerationTask(
        step=step,
        system_prompt="system",
        user_prompt="user",
        response_schema=response_schema or {"ok": {"type": "boolean"}},
        metadata=metadata or {},
    )


@pytest.mark.asyncio
async def test_deterministic_provider_covers_supported_steps() -> None:
    provider = DeterministicTextGenerationProvider()
    cases = [
        _task(
            "chapter_draft",
            metadata={
                "title": "Contract Story",
                "premise": "A map changes at dawn.",
                "genre": "fantasy",
                "tone": "urgent",
                "chapter_number": 1,
            },
        ),
        _task("chapter_revision", metadata={"chapter_number": 1}),
        _task("unknown", metadata={"source": "fallback"}),
    ]

    results = [await provider.generate_structured(case) for case in cases]

    assert all(isinstance(result, TextGenerationResult) for result in results)
    assert results[0].content["chapter_markdown"].startswith("# Chapter 1")
    assert results[0].content["sidecar_metadata"]["characters"] == ["Mira", "Tomas"]
    assert (
        results[1]
        .content["chapter_markdown"]
        .startswith("# Chapter 1: The Debt in the Rain")
    )
    assert results[2].content == {
        "result": "ok",
        "step": "unknown",
        "echo": {"source": "fallback"},
    }


def test_provider_factory_default_mock_without_key_is_usable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = create_text_generation_provider(NovelEngineSettings())

    assert isinstance(provider, DeterministicTextGenerationProvider)


def test_provider_factory_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    settings = NovelEngineSettings()

    with pytest.raises(ValueError, match="Unsupported text generation provider"):
        create_text_generation_provider(settings, provider_name=cast(Any, "bogus"))


def test_provider_factory_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    settings = NovelEngineSettings()

    provider = create_text_generation_provider(
        settings,
        provider_name="mock",
        model_name="test-model",
    )
    result = asyncio.run(provider.generate_structured(_task()))

    assert result.model == "test-model"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing output"),
        ({"output": {"choices": [1]}}, "choice is not an object"),
        ({"output": {"choices": [{"message": "text"}]}}, "message is not an object"),
        ({"output": {}}, "missing structured message content"),
    ],
)
def test_dashscope_generation_response_shape_errors(
    payload: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(TextGenerationProviderError, match=message):
        DashScopeTextGenerationProvider._extract_generation_response_text(payload)


def test_dashscope_extracts_generation_content_list_and_text_fallback() -> None:
    content_list = DashScopeTextGenerationProvider._extract_generation_response_text(
        {
            "output": {
                "choices": [{"message": {"content": [{"text": "a"}, {"text": "b"}]}}]
            }
        }
    )
    text_fallback = DashScopeTextGenerationProvider._extract_generation_response_text(
        {"output": {"text": '{"ok": true}'}}
    )

    assert content_list == "ab"
    assert text_fallback == '{"ok": true}'


def test_dashscope_responses_text_extraction_and_errors() -> None:
    text = DashScopeTextGenerationProvider._extract_responses_text(
        {
            "output": [
                {"type": "ignored"},
                {"type": "message", "content": [{"text": "hello"}, {"text": " world"}]},
            ]
        }
    )

    assert text == "hello world"
    with pytest.raises(TextGenerationProviderError, match="output is invalid"):
        DashScopeTextGenerationProvider._extract_responses_text({"output": {}})
    with pytest.raises(TextGenerationProviderError, match="missing message text"):
        DashScopeTextGenerationProvider._extract_responses_text({"output": []})


def test_dashscope_parse_json_nested_string_and_invalid_value() -> None:
    assert DashScopeTextGenerationProvider._parse_json_object('"{\\"ok\\": true}"') == {
        "ok": True
    }

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        DashScopeTextGenerationProvider._parse_json_object("[]")


def test_dashscope_parse_json_merges_objects_from_array_wrapper() -> None:
    parsed = DashScopeTextGenerationProvider._parse_json_object(
        '["{\\"chapter_markdown\\": \\"# Chapter 1\\"}", '
        '"{\\"sidecar_metadata\\": {\\"summary\\": \\"A bell rings.\\"}}"]'
    )

    assert parsed == {
        "chapter_markdown": "# Chapter 1",
        "sidecar_metadata": {"summary": "A bell rings."},
    }


def test_dashscope_retry_policy_boundaries() -> None:
    assert DashScopeTextGenerationProvider._should_retry(
        TextGenerationProviderError("invalid json")
    )
    assert DashScopeTextGenerationProvider._should_retry(
        TextGenerationProviderError("timed out after 30s")
    )
    assert DashScopeTextGenerationProvider._should_retry(
        TextGenerationProviderError("provider returned 429 too many requests")
    )
    assert not DashScopeTextGenerationProvider._should_retry(RuntimeError("boom"))


@pytest.mark.asyncio
async def test_unconfigured_provider_reports_missing_credentials() -> None:
    provider = UnconfiguredTextGenerationProvider(
        provider_name="dashscope",
        model="qwen3.5-flash",
        message="DASHSCOPE_API_KEY is required",
    )

    with pytest.raises(TextGenerationProviderError, match="DASHSCOPE_API_KEY"):
        await provider.generate_structured(_task())
