"""Tests for the story workflow application service."""

# mypy: disable-error-code=misc

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from src.shared.application.result import Failure


@pytest.fixture
def story_service() -> tuple[StoryWorkflowService, InMemoryStoryRepository]:
    repository = InMemoryStoryRepository()
    provider = DeterministicTextGenerationProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        text_generation_provider=provider,
        default_target_chapters=3,
    )
    return service, repository


@pytest.mark.asyncio
async def test_full_pipeline_generates_publishable_story(
    story_service: tuple[StoryWorkflowService, InMemoryStoryRepository],
) -> None:
    service, repository = story_service

    result = await service.run_pipeline(
        title="Pipeline Story",
        genre="fantasy",
        author_id="author-1",
        premise="A courier finds a map that rewrites the kingdom's borders.",
        target_chapters=3,
        publish=True,
    )

    assert result.is_ok
    artifact = result.value
    assert artifact["published"] is True
    assert artifact["story"]["chapter_count"] == 3
    assert artifact["story"]["status"] == "active"
    assert artifact["blueprint"]["world_bible"]
    assert artifact["outline"]["chapters"]
    assert artifact["final_review"]["ready_for_publish"] is True

    stored_story = await repository.get_by_id(UUID(artifact["story"]["id"]))
    assert stored_story is not None
    assert stored_story.chapter_count == 3


@pytest.mark.asyncio
async def test_review_detects_broken_story_and_revise_repairs_it(
    story_service: tuple[StoryWorkflowService, InMemoryStoryRepository],
) -> None:
    service, repository = story_service

    create_result = await service.create_story(
        title="Repair Story",
        genre="mystery",
        author_id="author-2",
        premise="A harbor murder hides a larger conspiracy.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    stored_story.chapters[0].scenes.clear()
    await repository.save(stored_story)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok
    review_report = review_result.value["report"]
    assert review_report["ready_for_publish"] is False
    assert any(issue["code"] == "empty_chapter" for issue in review_report["issues"])

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["revision_notes"]

    final_review = await service.review_story(story_id)
    assert final_review.is_ok
    assert final_review.value["report"]["ready_for_publish"] is True


@pytest.mark.asyncio
async def test_publish_rejects_incomplete_story(
    story_service: tuple[StoryWorkflowService, InMemoryStoryRepository],
) -> None:
    service, _repository = story_service

    create_result = await service.create_story(
        title="Blocked Story",
        genre="drama",
        author_id="author-3",
        premise="An actor inherits a theater that records every lie.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)

    publish_result = await service.publish_story(story_id)
    assert publish_result.is_err
    assert isinstance(publish_result, Failure)
    assert publish_result.code == "QUALITY_GATE_FAILED"
