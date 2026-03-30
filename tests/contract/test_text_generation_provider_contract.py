"""Contracts for structured text generation providers."""

# mypy: disable-error-code=misc

from __future__ import annotations

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from tests.text_generation_contract_support import (
    assert_structured_contract_result,
    build_contract_cases,
    resolve_dashscope_credentials,
)


async def _exercise_contract(provider: TextGenerationProvider, *, strict: bool) -> None:
    cases = build_contract_cases()
    for case in cases:
        result = await provider.generate_structured(case[1])
        assert_structured_contract_result(
            result,
            case,
            provider_name="dashscope" if not strict else "mock",
            model_name=(
                "qwen3.5-flash" if not strict else "deterministic-story-v1"
            ),
            strict=strict,
        )


@pytest.mark.asyncio
async def test_deterministic_provider_matches_structured_contract() -> None:
    provider = DeterministicTextGenerationProvider()
    await _exercise_contract(provider, strict=True)


@pytest.mark.requires_dashscope
@pytest.mark.asyncio
async def test_dashscope_provider_live_matches_structured_contract() -> None:
    api_key, api_base = resolve_dashscope_credentials()
    provider = DashScopeTextGenerationProvider(
        api_key=api_key,
        api_base=api_base,
        model="qwen3.5-flash",
        transport_mode="multimodal_generation",
        timeout=60,
    )
    await _exercise_contract(provider, strict=False)
