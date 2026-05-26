"""Mocked text-generation provider resilience tests."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

import httpx
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
from src.contexts.ai.infrastructure.providers.openai_compatible_text_generation_provider import (
    OpenAICompatibleTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.provider_factory import (
    create_text_generation_provider,
)
from src.contexts.ai.infrastructure.providers.unconfigured_text_generation_provider import (
    UnconfiguredTextGenerationProvider,
)
from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
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


class _ProviderResponse:
    def __init__(
        self,
        data: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
        text: str = "",
        json_error: Exception | None = None,
    ) -> None:
        self._data = data or {}
        self._json_error = json_error
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "https://provider.test/generate")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = httpx.Response(
                self.status_code,
                text=self.text,
                request=self.request,
            )
            raise httpx.HTTPStatusError(
                "provider error",
                request=self.request,
                response=response,
            )

    def json(self) -> dict[str, Any]:
        if self._json_error is not None:
            raise self._json_error
        return self._data


class _AsyncPostClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def post(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _dashscope_success_response(content: str) -> _ProviderResponse:
    return _ProviderResponse(
        {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": content,
                        }
                    }
                ]
            }
        }
    )


def _openai_success_response(content: str) -> _ProviderResponse:
    return _ProviderResponse(
        {
            "choices": [
                {
                    "message": {
                        "content": content,
                    }
                }
            ]
        }
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
    assert results[1].content["chapter_markdown"].startswith(
        "# Chapter 1: The Debt in the Rain"
    )
    assert results[2].content == {
        "result": "ok",
        "step": "unknown",
        "echo": {"source": "fallback"},
    }


def test_provider_factory_default_dashscope_without_key_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    provider = create_text_generation_provider(NovelEngineSettings())

    assert isinstance(provider, UnconfiguredTextGenerationProvider)


def test_provider_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAICompatibleTextGenerationProvider(api_key="")


def test_dashscope_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="DashScope API key"):
        DashScopeTextGenerationProvider(api_key="")


@pytest.mark.asyncio
async def test_dashscope_provider_generates_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(api_key="dashscope-key", retry_attempts=1)
    fake_client = _AsyncPostClient(
        [_dashscope_success_response('{"items": "single", "count": "2"}')]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(
        _task(
            response_schema={
                "items": {"type": "array"},
                "count": {"type": "integer"},
            }
        )
    )

    assert result.provider == "dashscope"
    assert result.content == {"items": ["single"], "count": 2}
    assert fake_client.calls[0][0] == (provider._endpoint_path(),)
    assert fake_client.calls[0][1]["timeout"] == 30.0


@pytest.mark.asyncio
async def test_dashscope_provider_retries_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key="dashscope-key",
        retry_attempts=2,
        retry_delay=0,
    )
    fake_client = _AsyncPostClient(
        [
            httpx.ReadTimeout("slow"),
            _dashscope_success_response('{"ok": true}'),
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(_task())

    assert result.content == {"ok": True}
    assert len(fake_client.calls) == 2


@pytest.mark.asyncio
async def test_dashscope_provider_maps_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(api_key="dashscope-key", retry_attempts=1)
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient(
            [_ProviderResponse(status_code=500, text="upstream failed")]
        ),
    )

    with pytest.raises(TextGenerationProviderError, match="500 upstream failed"):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_dashscope_provider_maps_json_decode_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(api_key="dashscope-key", retry_attempts=1)
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient(
            [
                _ProviderResponse(
                    {"output": {}},
                    json_error=json.JSONDecodeError("bad json", "not-json", 0),
                )
            ]
        ),
    )

    with pytest.raises(TextGenerationProviderError, match="invalid JSON"):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_dashscope_provider_maps_non_json_object_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(api_key="dashscope-key", retry_attempts=1)
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([_dashscope_success_response("[1, 2]")]),
    )

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        await provider.generate_structured(_task())


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
        {"output": {"choices": [{"message": {"content": [{"text": "a"}, {"text": "b"}]}}]}}
    )
    text_fallback = DashScopeTextGenerationProvider._extract_generation_response_text(
        {"output": {"text": "{\"ok\": true}"}}
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
async def test_openai_compatible_provider_generates_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(api_key="openai-key")
    fake_client = _AsyncPostClient([_openai_success_response('{"ok": true}')])
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(_task())

    assert result.provider == "openai_compatible"
    assert result.content == {"ok": True}
    assert fake_client.calls[0][0] == ("/chat/completions",)
    payload = fake_client.calls[0][1]["json"]
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "missing choices"),
        ({"choices": [1]}, "choice is not an object"),
        ({"choices": [{"message": "text"}]}, "message is not an object"),
        ({"choices": [{"message": {"content": "[1]"}}]}, "not a JSON object"),
    ],
)
@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_shape_errors(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    message: str,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(api_key="openai-key")
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([_ProviderResponse(payload)]),
    )

    with pytest.raises(TextGenerationProviderError, match=message):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_http_and_json_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_provider = OpenAICompatibleTextGenerationProvider(api_key="openai-key")
    monkeypatch.setattr(
        status_provider,
        "_get_client",
        lambda: _AsyncPostClient([_ProviderResponse(status_code=401, text="nope")]),
    )

    with pytest.raises(TextGenerationProviderError, match="401 nope"):
        await status_provider.generate_structured(_task())

    json_provider = OpenAICompatibleTextGenerationProvider(api_key="openai-key")
    monkeypatch.setattr(
        json_provider,
        "_get_client",
        lambda: _AsyncPostClient([_openai_success_response("not-json")]),
    )

    with pytest.raises(TextGenerationProviderError, match="invalid JSON"):
        await json_provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_openai_compatible_provider_maps_transport_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(api_key="openai-key")
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([httpx.ReadTimeout("slow")]),
    )

    with pytest.raises(TextGenerationProviderError, match="slow"):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_unconfigured_provider_error_trips_circuit_breaker() -> None:
    provider = UnconfiguredTextGenerationProvider(
        provider_name="dashscope",
        model="qwen3.5-flash",
        message="DASHSCOPE_API_KEY is required",
    )
    breaker = CircuitBreaker(
        "ai-provider",
        CircuitBreakerConfig(failure_threshold=1),
        expected_exception=TextGenerationProviderError,
    )

    async def _call_provider() -> None:
        await provider.generate_structured(_task())

    with pytest.raises(TextGenerationProviderError):
        await breaker.call(_call_provider)
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(_call_provider)
