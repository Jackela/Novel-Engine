"""Chapter-level regression corpus for continuity, motive drift, timeline conflicts, hooks, and publish gates."""

# mypy: disable-error-code=misc

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from src.shared.application.result import Failure

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "narrative"
    / "chapter_regression_corpus.json"
)


def _load_regression_cases() -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))


@pytest.fixture
def story_service() -> tuple[StoryWorkflowService, InMemoryStoryRepository]:
    repository = InMemoryStoryRepository()
    provider = DeterministicTextGenerationProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        text_generation_provider=provider,
        default_target_chapters=4,
    )
    return service, repository


async def _draft_story(
    service: StoryWorkflowService,
    repository: InMemoryStoryRepository,
) -> str:
    create_result = await service.create_story(
        title="Regression Corpus Story",
        genre="fantasy",
        author_id="corpus-author",
        premise="A courier learns the kingdom's border map is rewriting itself.",
        target_chapters=4,
    )
    story_id = cast(str, create_result.value["story"]["id"])
    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=4)
    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    assert stored_story.chapter_count == 4
    return story_id


def _apply_regression_mutation(story: Story, case: dict[str, Any]) -> None:
    chapter_number = int(case["chapter_number"])
    if chapter_number < 1 or chapter_number > len(story.chapters):
        raise ValueError(f"chapter_number {chapter_number} is out of range")

    chapter = story.chapters[chapter_number - 1]
    mutation = case["mutation"]
    kind = str(mutation["kind"])

    if kind == "timeline_day":
        chapter.metadata["timeline_day"] = int(mutation["timeline_day"])
        return

    if kind == "all_scenes":
        scene_text = str(mutation["scene_text"])
        current_scene_text = str(mutation["current_scene_text"])
        for scene in chapter.scenes:
            scene.update_content(scene_text)
        if chapter.current_scene is not None:
            chapter.current_scene.update_content(current_scene_text)
        return

    if kind == "current_scene":
        current_scene = chapter.current_scene
        if current_scene is None:
            raise ValueError("current_scene mutation requires an existing scene")
        current_scene.update_content(str(mutation["current_scene_text"]))
        return

    if kind == "clear_scenes":
        chapter.scenes.clear()
        return

    raise ValueError(f"Unsupported regression mutation kind: {kind}")


@pytest.mark.parametrize("case", _load_regression_cases(), ids=lambda case: case["name"])
@pytest.mark.asyncio
async def test_story_regression_corpus_detects_and_repairs(
    case: dict[str, Any],
    story_service: tuple[StoryWorkflowService, InMemoryStoryRepository],
) -> None:
    service, repository = story_service
    story_id = await _draft_story(service, repository)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    _apply_regression_mutation(stored_story, case)
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    report_before = review_before.value["report"]

    issue_codes_before = {issue["code"] for issue in report_before["issues"]}
    issue_severities_before = {
        issue["code"]: issue["severity"] for issue in report_before["issues"]
    }
    assert case["expected_issue_code"] in issue_codes_before
    assert issue_severities_before[case["expected_issue_code"]] == case[
        "expected_severity"
    ]

    if case["block_publish_before_revision"]:
        assert report_before["ready_for_publish"] is False
        publish_before = await service.publish_story(story_id)
        assert publish_before.is_err
        assert isinstance(publish_before, Failure)
        assert publish_before.code == "QUALITY_GATE_FAILED"

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["revision_notes"]

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    report_after = review_after.value["report"]
    assert case["expected_issue_code"] not in {
        issue["code"] for issue in report_after["issues"]
    }
    assert report_after["ready_for_publish"] is True

    publish_after = await service.publish_story(story_id)
    assert publish_after.is_ok
    assert publish_after.value["story"]["status"] == "active"
