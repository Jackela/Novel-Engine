"""24-chapter regression corpus for continuity, motive drift, timeline conflicts, hooks, and publish gates."""

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
from src.contexts.narrative.domain.entities.chapter import Chapter
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
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    provider = DeterministicTextGenerationProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=provider,
        default_target_chapters=12,
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
        target_chapters=24,
    )
    story_id = cast(str, create_result.value["story"]["id"])
    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=24)
    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    assert stored_story.chapter_count == 24
    return story_id


def _resolve_chapter(story: Story, chapter_number: int) -> Chapter:
    if chapter_number < 1 or chapter_number > len(story.chapters):
        raise ValueError(f"chapter_number {chapter_number} is out of range")
    return story.chapters[chapter_number - 1]


def _apply_chapter_mutation(story: Story, chapter_number: int, mutation: dict[str, Any]) -> None:
    chapter = _resolve_chapter(story, chapter_number)
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

    if kind == "opening_scene":
        if not chapter.scenes:
            raise ValueError("opening_scene mutation requires an existing scene")
        chapter.scenes[0].update_content(str(mutation["content"]))
        return

    if kind == "clear_scenes":
        chapter.scenes.clear()
        return

    if kind == "trim_scenes":
        keep = int(mutation["keep"])
        if keep < 0:
            raise ValueError("trim_scenes keep must be non-negative")
        del chapter.scenes[keep:]
        return

    if kind == "flatten_scene_types":
        scene_type = str(mutation["scene_type"])
        for scene in chapter.scenes:
            scene.scene_type = cast(Any, scene_type)
        return

    if kind == "focus_character":
        chapter.metadata["focus_character"] = str(mutation["focus_character"])
        return

    if kind == "clear_focus_character":
        chapter.metadata["focus_character"] = ""
        return

    if kind == "relationship_target":
        chapter.metadata["relationship_target"] = str(mutation["relationship_target"])
        return

    if kind == "relationship_status":
        chapter.metadata["relationship_status"] = str(mutation["relationship_status"])
        return

    raise ValueError(f"Unsupported regression mutation kind: {kind}")


def _apply_regression_mutation(story: Story, case: dict[str, Any]) -> None:
    mutations = case.get("mutations")
    if isinstance(mutations, list) and mutations:
        for mutation in mutations:
            if not isinstance(mutation, dict):
                raise ValueError("Each regression mutation must be an object")
            _apply_chapter_mutation(story, int(mutation["chapter_number"]), mutation)
        return

    mutation = case.get("mutation")
    if not isinstance(mutation, dict):
        raise ValueError("Regression case must define a mutation or mutations")
    _apply_chapter_mutation(story, int(case["chapter_number"]), mutation)


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
    structural_before = report_before["structural_review"]
    assert structural_before is not None

    issue_codes_before = {issue["code"] for issue in structural_before["issues"]}
    issue_severities_before = {
        issue["code"]: issue["severity"] for issue in structural_before["issues"]
    }
    assert case["expected_issue_code"] in issue_codes_before
    assert issue_severities_before[case["expected_issue_code"]] == case[
        "expected_severity"
    ]

    if case["block_publish_before_revision"]:
        assert report_before["ready_for_publish"] is False
        assert any(
            issue["severity"] == "blocker" for issue in structural_before["issues"]
        ) or any(
            issue["severity"] == "warning" for issue in report_before["issues"]
        )

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["revision_notes"]

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    report_after = review_after.value["report"]
    structural_after = report_after["structural_review"]
    assert structural_after is not None
    assert case["expected_issue_code"] not in {
        issue["code"] for issue in structural_after["issues"]
    }
    assert report_after["ready_for_publish"] is True

    publish_after = await service.publish_story(story_id)
    assert publish_after.is_ok
    assert publish_after.value["story"]["status"] == "active"
