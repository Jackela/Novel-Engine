"""Live smoke for Qwen3.5-Flash via the canonical DashScope provider."""

# mypy: disable-error-code=misc

from __future__ import annotations

import pytest

from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_generation_run_repository import (
    InMemoryGenerationRunRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_artifact_repository import (
    InMemoryStoryArtifactRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_generation_state_repository import (
    InMemoryStoryGenerationStateRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from tests.text_generation_contract_support import resolve_dashscope_credentials


@pytest.mark.requires_dashscope
@pytest.mark.asyncio
async def test_qwen35_flash_smoke_generates_blueprint_outline_chapter_and_semantic_review() -> None:
    api_key, api_base = resolve_dashscope_credentials()
    provider = DashScopeTextGenerationProvider(
        api_key=api_key,
        model="qwen3.5-flash",
        api_base=api_base,
        transport_mode="multimodal_generation",
        timeout=60,
    )
    service = StoryWorkflowService(
        story_repository=InMemoryStoryRepository(),
        generation_state_repository=InMemoryStoryGenerationStateRepository(),
        generation_run_repository=InMemoryGenerationRunRepository(),
        story_artifact_repository=InMemoryStoryArtifactRepository(),
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
    assert blueprint["provider"] == "dashscope"
    assert blueprint["model"] == "qwen3.5-flash"
    assert blueprint["world_bible"]
    assert blueprint["character_bible"]

    outline_result = await service.generate_outline(story_id)
    assert outline_result.is_ok
    outline = outline_result.value["outline"]
    assert outline["provider"] == "dashscope"
    assert outline["model"] == "qwen3.5-flash"
    assert outline["chapters"]
    assert outline["chapters"][0]["hook"]

    draft_result = await service.draft_story(story_id, target_chapters=1)
    assert draft_result.is_ok
    drafted_story = draft_result.value["story"]
    assert drafted_story["chapter_count"] == 1
    assert drafted_story["chapters"][0]["scenes"]

    review_result = await service.review_story(story_id)
    assert review_result.is_ok
    report = review_result.value["report"]
    assert report["structural_review"] is not None
    assert report["semantic_review"] is not None
    assert report["semantic_review"]["source_provider"] == "dashscope"
    assert report["semantic_review"]["source_model"] == "qwen3.5-flash"
