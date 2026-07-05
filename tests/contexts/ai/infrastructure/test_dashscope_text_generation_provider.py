from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)

_DASHSCOPE_API_KEY = "dashscope-key"


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


def _dashscope_success_response(
    content: str,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> _ProviderResponse:
    data: dict[str, Any] = {
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
    if prompt_tokens is not None and completion_tokens is not None:
        data["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
    return _ProviderResponse(data)


def test_dashscope_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="DashScope API key"):
        DashScopeTextGenerationProvider(api_key="")


@pytest.mark.asyncio
async def test_dashscope_provider_generates_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
    fake_client = _AsyncPostClient(
        [
            _dashscope_success_response(
                '{"items": "single", "count": "2"}',
                prompt_tokens=12,
                completion_tokens=7,
            )
        ]
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
    assert result.prompt_tokens == 12
    assert result.completion_tokens == 7
    assert fake_client.calls[0][0] == (provider._endpoint_path(),)
    assert fake_client.calls[0][1]["timeout"] == 30.0


@pytest.mark.asyncio
async def test_dashscope_provider_coerces_nested_sidecar_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
    fake_client = _AsyncPostClient(
        [
            _dashscope_success_response(
                json.dumps(
                    {
                        "chapter_markdown": "# Chapter 1\n\nA courier waits.",
                        "sidecar_metadata": {
                            "summary": ["A courier waits."],
                            "characters": "Mira",
                            "promises": None,
                        },
                    }
                )
            )
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(
        _task(
            step="chapter_draft",
            response_schema={
                "chapter_markdown": {"type": "string"},
                "sidecar_metadata": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "characters": {"type": "array"},
                        "promises": {"type": "array"},
                    },
                },
            },
        )
    )

    assert result.content["sidecar_metadata"] == {
        "summary": "A courier waits.",
        "characters": ["Mira"],
        "promises": [],
    }


@pytest.mark.asyncio
async def test_dashscope_provider_retries_timeout_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY,
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
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
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
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
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
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([_dashscope_success_response("[1, 2]")]),
    )

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_dashscope_provider_uses_chapter_text_fallback_for_non_object_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient(
            [
                _dashscope_success_response(
                    json.dumps(
                        [
                            "# Chapter 1: The Bell Debt",
                            "Mira follows the sound into the counting room.",
                        ]
                    )
                )
            ]
        ),
    )

    result = await provider.generate_structured(
        _task(
            "chapter_draft",
            response_schema={
                "chapter_markdown": {"type": "string"},
                "sidecar_metadata": {"type": "object"},
            },
        )
    )

    assert result.content == {
        "chapter_markdown": (
            "# Chapter 1: The Bell Debt\n\n"
            "Mira follows the sound into the counting room."
        )
    }


@pytest.mark.asyncio
async def test_dashscope_provider_rejects_non_text_chapter_array(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=_DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([_dashscope_success_response("[1, 2]")]),
    )

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        await provider.generate_structured(
            _task(
                "chapter_draft",
                response_schema={
                    "chapter_markdown": {"type": "string"},
                    "sidecar_metadata": {"type": "object"},
                },
            )
        )
