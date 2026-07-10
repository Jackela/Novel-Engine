from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)

DASHSCOPE_API_KEY = "dashscope-key"


def make_task(
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


class ProviderResponse:
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


class AsyncPostClient:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def post(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def dashscope_success_response(
    content: str,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> ProviderResponse:
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
    return ProviderResponse(data)


def test_dashscope_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="DashScope API key"):
        DashScopeTextGenerationProvider(api_key="")


@pytest.mark.asyncio
async def test_dashscope_provider_generates_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    fake_client = AsyncPostClient(
        [
            dashscope_success_response(
                '{"items": "single", "count": "2"}',
                prompt_tokens=12,
                completion_tokens=7,
            )
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(
        make_task(
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
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    fake_client = AsyncPostClient(
        [
            dashscope_success_response(
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
        make_task(
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
        api_key=DASHSCOPE_API_KEY,
        retry_attempts=2,
        retry_delay=0,
    )
    fake_client = AsyncPostClient(
        [
            httpx.ReadTimeout("slow"),
            dashscope_success_response('{"ok": true}'),
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(make_task())

    assert result.content == {"ok": True}
    assert len(fake_client.calls) == 2
