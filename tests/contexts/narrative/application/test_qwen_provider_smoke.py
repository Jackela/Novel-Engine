"""Live smoke for Qwen3.5-Flash via the OpenAI-compatible DashScope endpoint."""

# mypy: disable-error-code=misc

from __future__ import annotations

import os
from typing import cast

import pytest

from src.contexts.ai.infrastructure.providers.openai_text_generation_provider import (
    OpenAITextGenerationProvider,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)


def _resolve_live_credentials() -> tuple[str, str]:
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key:
        pytest.skip(
            "Set DASHSCOPE_API_KEY or LLM_API_KEY, plus ENABLE_OPENAI_TESTS=1, "
            "to run the live Qwen3.5-Flash smoke."
        )

    api_base = (
        os.getenv("DASHSCOPE_API_BASE")
        or os.getenv("LLM_API_BASE")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    return cast(str, api_key), api_base


@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_qwen35_flash_smoke_generates_blueprint_outline_and_chapter() -> None:
    api_key, api_base = _resolve_live_credentials()
    provider = OpenAITextGenerationProvider(
        api_key=api_key,
        model="qwen3.5-flash",
        api_base=api_base,
        timeout=60,
    )
    service = StoryWorkflowService(
        story_repository=InMemoryStoryRepository(),
        text_generation_provider=provider,
        default_target_chapters=1,
    )

    create_result = await service.create_story(
        title="Live Smoke Story",
        genre="fantasy",
        author_id="live-smoke-author",
        premise="A courier discovers the map of a kingdom that is rewriting itself.",
        target_chapters=1,
    )
    assert create_result.is_ok
    story_id = create_result.value["story"]["id"]

    blueprint_result = await service.generate_blueprint(story_id)
    assert blueprint_result.is_ok
    blueprint = blueprint_result.value["blueprint"]
    assert blueprint["provider"] == "openai"
    assert blueprint["model"] == "qwen3.5-flash"
    assert blueprint["world_bible"]
    assert blueprint["character_bible"]

    outline_result = await service.generate_outline(story_id)
    assert outline_result.is_ok
    outline = outline_result.value["outline"]
    assert outline["provider"] == "openai"
    assert outline["model"] == "qwen3.5-flash"
    assert outline["chapters"]
    assert outline["chapters"][0]["hook"]

    draft_result = await service.draft_story(story_id, target_chapters=1)
    assert draft_result.is_ok
    drafted_story = draft_result.value["story"]
    assert drafted_story["chapter_count"] == 1
    assert drafted_story["chapters"][0]["scenes"]
