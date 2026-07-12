from __future__ import annotations

from typing import Any

import httpx
import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.openai_compatible_text_generation_provider import (
    OpenAICompatibleTextGenerationProvider,
)

_OPENAI_API_KEY = "openai-key"


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
    ) -> None:
        self._data = data or {}
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


def _openai_success_response(
    content: str,
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
) -> _ProviderResponse:
    data: dict[str, Any] = {
        "choices": [
            {
                "message": {
                    "content": content,
                }
            }
        ]
    }
    if prompt_tokens is not None and completion_tokens is not None:
        data["usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
    return _ProviderResponse(data)


def test_openai_provider_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAICompatibleTextGenerationProvider(api_key="")


@pytest.mark.asyncio
async def test_openai_compatible_provider_generates_structured_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(api_key=_OPENAI_API_KEY)
    fake_client = _AsyncPostClient(
        [_openai_success_response('{"ok": true}', prompt_tokens=9, completion_tokens=3)]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(_task())

    assert result.provider == "openai_compatible"
    assert result.content == {"ok": True}
    assert result.prompt_tokens == 9
    assert result.completion_tokens == 3
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
    provider = OpenAICompatibleTextGenerationProvider(api_key=_OPENAI_API_KEY)
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
    status_provider = OpenAICompatibleTextGenerationProvider(
        api_key=_OPENAI_API_KEY,
        retry_attempts=1,
    )
    monkeypatch.setattr(
        status_provider,
        "_get_client",
        lambda: _AsyncPostClient([_ProviderResponse(status_code=401, text="nope")]),
    )

    with pytest.raises(TextGenerationProviderError, match="401 nope"):
        await status_provider.generate_structured(_task())

    json_provider = OpenAICompatibleTextGenerationProvider(
        api_key=_OPENAI_API_KEY,
        retry_attempts=1,
    )
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
    provider = OpenAICompatibleTextGenerationProvider(
        api_key=_OPENAI_API_KEY,
        retry_attempts=1,
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: _AsyncPostClient([httpx.ReadTimeout("slow")]),
    )

    with pytest.raises(TextGenerationProviderError, match="slow"):
        await provider.generate_structured(_task())


@pytest.mark.asyncio
async def test_openai_compatible_provider_retries_retriable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(
        api_key=_OPENAI_API_KEY,
        retry_attempts=3,
        retry_delay=0.0,
    )
    fake_client = _AsyncPostClient(
        [
            _ProviderResponse(status_code=500, text="boom"),
            _ProviderResponse(status_code=502, text="retry"),
            _openai_success_response('{"ok": true}'),
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    result = await provider.generate_structured(_task())

    assert result.content == {"ok": True}
    assert len(fake_client.calls) == 3


@pytest.mark.asyncio
async def test_openai_compatible_provider_exhausts_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OpenAICompatibleTextGenerationProvider(
        api_key=_OPENAI_API_KEY,
        retry_attempts=2,
        retry_delay=0.0,
    )
    fake_client = _AsyncPostClient(
        [
            _ProviderResponse(status_code=500, text="first"),
            _ProviderResponse(status_code=500, text="second"),
        ]
    )
    monkeypatch.setattr(provider, "_get_client", lambda: fake_client)

    with pytest.raises(TextGenerationProviderError, match="500"):
        await provider.generate_structured(_task())

    assert len(fake_client.calls) == 2
