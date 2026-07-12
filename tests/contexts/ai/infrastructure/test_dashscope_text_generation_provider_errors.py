from __future__ import annotations

import json

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from tests.contexts.ai.infrastructure.test_dashscope_text_generation_provider import (
    DASHSCOPE_API_KEY,
    AsyncPostClient,
    ProviderResponse,
    dashscope_success_response,
    make_task,
)


@pytest.mark.asyncio
async def test_dashscope_provider_maps_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: AsyncPostClient(
            [ProviderResponse(status_code=500, text="upstream failed")]
        ),
    )

    with pytest.raises(TextGenerationProviderError, match="500 upstream failed"):
        await provider.generate_structured(make_task())


@pytest.mark.asyncio
async def test_dashscope_provider_maps_json_decode_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: AsyncPostClient(
            [
                ProviderResponse(
                    {"output": {}},
                    json_error=json.JSONDecodeError("bad json", "not-json", 0),
                )
            ]
        ),
    )

    with pytest.raises(TextGenerationProviderError, match="invalid JSON"):
        await provider.generate_structured(make_task())


@pytest.mark.asyncio
async def test_dashscope_provider_maps_non_json_object_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: AsyncPostClient([dashscope_success_response("[1, 2]")]),
    )

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        await provider.generate_structured(make_task())


@pytest.mark.asyncio
async def test_dashscope_provider_uses_chapter_text_fallback_for_non_object_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = DashScopeTextGenerationProvider(
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: AsyncPostClient(
            [
                dashscope_success_response(
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
        make_task(
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
        api_key=DASHSCOPE_API_KEY, retry_attempts=1
    )
    monkeypatch.setattr(
        provider,
        "_get_client",
        lambda: AsyncPostClient([dashscope_success_response("[1, 2]")]),
    )

    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        await provider.generate_structured(
            make_task(
                "chapter_draft",
                response_schema={
                    "chapter_markdown": {"type": "string"},
                    "sidecar_metadata": {"type": "object"},
                },
            )
        )
