"""Provider factory contracts for explicit multi-provider selection."""

from __future__ import annotations

import asyncio

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
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
from src.shared.infrastructure.config.settings import NovelEngineSettings


def test_factory_honors_explicit_mock_provider_in_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    settings = NovelEngineSettings()

    provider = create_text_generation_provider(settings)
    assert isinstance(provider, DeterministicTextGenerationProvider)


def test_factory_returns_explicit_unconfigured_dashscope_provider_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "compat-key-should-not-be-used")

    settings = NovelEngineSettings()
    provider = create_text_generation_provider(settings)

    assert isinstance(provider, UnconfiguredTextGenerationProvider)
    with pytest.raises(TextGenerationProviderError, match="DASHSCOPE_API_KEY"):
        asyncio.run(
            provider.generate_structured(
                TextGenerationTask(
                    step="bible",
                    system_prompt="system",
                    user_prompt="user",
                    response_schema={"ok": {"type": "boolean"}},
                )
            )
        )


def test_factory_builds_openai_compatible_provider_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "compat-key")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "gpt-4o-mini")

    settings = NovelEngineSettings()

    provider = create_text_generation_provider(settings)
    assert isinstance(provider, OpenAICompatibleTextGenerationProvider)


def test_factory_builds_dashscope_provider_when_explicitly_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("LLM_PROVIDER", "dashscope")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-key")
    monkeypatch.setenv("DASHSCOPE_MODEL", "qwen3.5-flash")
    monkeypatch.setenv("DASHSCOPE_TRANSPORT_MODE", "multimodal_generation")

    settings = NovelEngineSettings()

    provider = create_text_generation_provider(settings)
    assert isinstance(provider, DashScopeTextGenerationProvider)
    assert provider.transport_mode == "multimodal_generation"


def test_dashscope_provider_normalizes_compatible_mode_base() -> None:
    provider = DashScopeTextGenerationProvider(
        api_key="dashscope-key",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    client = provider._get_client()
    assert str(client.base_url) == "https://dashscope.aliyuncs.com/api/v1/"


def test_dashscope_qwen35_uses_multimodal_native_payload() -> None:
    provider = DashScopeTextGenerationProvider(
        api_key="dashscope-key",
        model="qwen3.5-flash",
    )
    task = TextGenerationTask(
        step="bible",
        system_prompt="system",
        user_prompt="user",
        response_schema={"ok": {"type": "boolean"}},
        temperature=0.2,
        metadata={},
    )

    payload = provider._build_request_payload(task)
    assert provider._endpoint_path() == "/services/aigc/multimodal-generation/generation"
    assert provider.transport_mode == "multimodal_generation"
    assert payload["input"]["messages"][0]["content"] == [
        {"text": "system\nReturn valid JSON only. Output schema: {\"ok\": {\"type\": \"boolean\"}}"}
    ]
    assert payload["parameters"]["enable_thinking"] is False
    assert "result_format" not in payload["parameters"]


def test_dashscope_responses_transport_normalizes_base_and_payload() -> None:
    provider = DashScopeTextGenerationProvider(
        api_key="dashscope-key",
        model="qwen3.5-flash",
        api_base="https://dashscope.aliyuncs.com/api/v1",
        transport_mode="responses",
    )
    task = TextGenerationTask(
        step="bible",
        system_prompt="system",
        user_prompt="user",
        response_schema={"ok": {"type": "boolean"}},
        temperature=0.2,
        metadata={},
    )

    client = provider._get_client()
    payload = provider._build_request_payload(task)

    assert provider.transport_mode == "responses"
    assert str(client.base_url) == (
        "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1/"
    )
    assert provider._endpoint_path() == "/responses"
    assert isinstance(payload["input"], str)


def test_dashscope_provider_extracts_json_from_code_fence() -> None:
    parsed = DashScopeTextGenerationProvider._parse_json_object(
        "```json\n{\n  \"ok\": true\n}\n```"
    )

    assert parsed == {"ok": True}
