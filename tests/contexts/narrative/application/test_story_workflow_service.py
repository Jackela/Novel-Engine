"""Tests for the story workflow application service."""

# mypy: disable-error-code=misc

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
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
from src.shared.application.result import Failure


class FailingSemanticReviewProvider:
    """Force semantic review to fail so review stage cannot silently pass."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        raise TextGenerationProviderError(f"semantic review unavailable for step {task.step}")


class DraftFailureAndSemanticWarningProvider(DeterministicTextGenerationProvider):
    """Inject a draft validation failure and a warning-only semantic review payload."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "chapter_scenes" and int(task.metadata.get("chapter_number", 0)) == 2:
            draft_payload: dict[str, Any] = {
                "scenes": [
                    {
                        "scene_type": "narrative",
                        "title": "Broken scene",
                        "content": "",
                    }
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="draft-failure-v1",
                raw_text=json.dumps(draft_payload, ensure_ascii=False),
                content=draft_payload,
            )

        if task.step == "semantic_review":
            semantic_payload: dict[str, Any] = {
                "semantic_score": 92,
                "reader_pull_score": 91,
                "plot_clarity_score": 90,
                "ooc_risk_score": 8,
                "summary": "Reader pull is healthy but a warning remains in the serial rhythm.",
                "repair_suggestions": [
                    "Reinforce the last-turn escalation before chapter endings.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The serial rhythm softens in the middle segment.",
                        "location": "story",
                        "suggestion": "Add a sharper chapter-end reveal.",
                        "details": {},
                    }
                ],
            }
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="semantic-warning-v1",
                raw_text=json.dumps(semantic_payload, ensure_ascii=False),
                content=semantic_payload,
            )

        return await super().generate_structured(task)


class NestedSceneShapeProvider(DeterministicTextGenerationProvider):
    """Return a real-provider-shaped draft payload that nests scenes under `type`."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "chapter_scenes" and int(task.metadata.get("chapter_number", 0)) == 2:
            nested_scene_payload: dict[str, Any] = {
                "scenes": [
                    {
                        "type": [
                            {
                                "scene_type": "opening",
                                "title": "Recovered opening",
                                "content": "The archivist opens the sealed ledger and finds the first clue.",
                            },
                            {
                                "type": "ending",
                                "title": "Recovered ending",
                                "content": "A new oath is written into the margin before the door closes.",
                            },
                        ]
                    }
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="nested-scene-shape-v1",
                raw_text=json.dumps(nested_scene_payload, ensure_ascii=False),
                content=nested_scene_payload,
            )

        return await super().generate_structured(task)


class AlternateBlueprintShapeProvider(DeterministicTextGenerationProvider):
    """Return a real-provider-shaped blueprint payload with nested character sections."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "bible":
            alternate_blueprint_payload: dict[str, Any] = {
                "world_bible": {
                    "setting_name": "The City of Mnemosyne",
                    "magic_system": {
                        "name": "Ink-Blood Resonance",
                        "cost": "Using memory magic requires blood-ink or rare memory ink.",
                    },
                    "rules_of_magic": (
                        "1. An erased oath creates a ghost proportional to its weight. "
                        "2. A ghost can only be exorcised by rewriting its original truth. "
                        "3. If a ruler is fully erased, their districts begin to dissolve."
                    ),
                },
                "character_bible": {
                    "protagonist": {
                        "name": "Lin Yuan",
                        "motivation": "save his sister from erasure",
                    },
                    "antagonist": {
                        "name": "High Scribe Vane",
                        "motivation": "purge the city of debt and memory",
                    },
                    "key_supporting": [
                        {
                            "name": "Echo",
                            "motivation": "recover the truth of his death",
                        },
                        {
                            "name": "Madam Qiao",
                            "motivation": "profit from memory ink without losing control",
                        },
                    ],
                },
                "premise_summary": "A debt archivist fights erasure ghosts to recover the city's memory.",
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="alternate-blueprint-shape-v1",
                raw_text=json.dumps(alternate_blueprint_payload, ensure_ascii=False),
                content=alternate_blueprint_payload,
            )

        return await super().generate_structured(task)


class SingleDigitHookStrengthProvider(DeterministicTextGenerationProvider):
    """Return outline hook strengths in a 0-10 scale to verify normalization."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "outline":
            outline_payload: dict[str, Any] = {
                "chapters": [
                    {
                        "chapter_number": 1,
                        "title": "Chapter One",
                        "summary": "A courier finds the living map.",
                        "hook": "The border moves while she watches.",
                        "promise": "Explain the living map.",
                        "pacing_phase": "opening",
                        "narrative_strand": "quest",
                        "chapter_objective": "Start the quest.",
                        "primary_strand": "quest",
                        "secondary_strand": "mystery",
                        "promised_payoff": "The map responds to blood.",
                        "hook_strength": 6,
                    },
                    {
                        "chapter_number": 2,
                        "title": "Chapter Two",
                        "summary": "The map reveals the first betrayal.",
                        "hook": "A trusted name vanishes from the page.",
                        "promise": "Raise the cost of the map.",
                        "pacing_phase": "rising",
                        "narrative_strand": "quest",
                        "chapter_objective": "Escalate the threat.",
                        "primary_strand": "quest",
                        "secondary_strand": "betrayal",
                        "promised_payoff": "The betrayal reaches the capital.",
                        "hook_strength": 7,
                    },
                    {
                        "chapter_number": 3,
                        "title": "Chapter Three",
                        "summary": "The courier chooses who to save.",
                        "hook": "The city gate opens to the wrong army.",
                        "promise": "Force a hard choice.",
                        "pacing_phase": "climax",
                        "narrative_strand": "quest",
                        "chapter_objective": "Close the first arc.",
                        "primary_strand": "quest",
                        "secondary_strand": "sacrifice",
                        "promised_payoff": "The map costs a future.",
                        "hook_strength": 8,
                    },
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="single-digit-hook-strength-v1",
                raw_text=json.dumps(outline_payload, ensure_ascii=False),
                content=outline_payload,
            )

        return await super().generate_structured(task)


class RevisionIssueRecordingProvider(DeterministicTextGenerationProvider):
    """Capture which issue codes reach the revision step."""

    def __init__(self) -> None:
        super().__init__()
        self.revision_issue_codes: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "revision":
            raw_issues = task.metadata.get("issues", [])
            if isinstance(raw_issues, list):
                self.revision_issue_codes = [
                    str(item.get("code", ""))
                    for item in raw_issues
                    if isinstance(item, dict) and str(item.get("code", "")).strip()
                ]
            revision_payload = {
                "revision_notes": [
                    "Repair the semantic issue that blocks publication.",
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="mock",
                model="revision-issue-recorder-v1",
                raw_text=json.dumps(revision_payload, ensure_ascii=False),
                content=revision_payload,
            )

        return await super().generate_structured(task)


class SemanticWarningOnlyProvider:
    """Return a semantic warning payload that should flow into revision."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        semantic_payload: dict[str, Any] = {
            "semantic_score": 88,
            "reader_pull_score": 70,
            "plot_clarity_score": 76,
            "ooc_risk_score": 12,
            "summary": "The relationship arc needs explicit repair before release.",
            "repair_suggestions": [
                "Resolve the stalled relationship arc.",
            ],
            "issues": [
                {
                    "code": "relationship_progression_stall",
                    "severity": "warning",
                    "message": "Relationship progression stalls in the back half.",
                    "location": "story",
                    "suggestion": "Advance the relationship state before publishing.",
                }
            ],
        }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="semantic-warning-only-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class SemanticBlockerProvider:
    """Return a blocker-level semantic payload that must still block publish."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        semantic_payload: dict[str, Any] = {
            "semantic_score": 90,
            "reader_pull_score": 88,
            "plot_clarity_score": 86,
            "ooc_risk_score": 10,
            "summary": "A blocker remains in the serial promise chain.",
            "repair_suggestions": [
                "Resolve the broken serial promise before release.",
            ],
            "issues": [
                {
                    "code": "promise_break",
                    "severity": "blocker",
                    "message": "The central promise is broken.",
                    "location": "story",
                    "suggestion": "Pay off the promised reveal before publishing.",
                }
            ],
        }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="semantic-blocker-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


def build_story_service(
    *,
    text_generation_provider: DeterministicTextGenerationProvider | None = None,
    review_generation_provider: TextGenerationProvider | None = None,
) -> tuple[StoryWorkflowService, InMemoryStoryRepository]:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=text_generation_provider or DeterministicTextGenerationProvider(),
        review_generation_provider=review_generation_provider,
        default_target_chapters=3,
    )
    return service, repository


@pytest.fixture
def story_service() -> tuple[StoryWorkflowService, InMemoryStoryRepository]:
    return build_story_service()


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
    assert artifact["workspace"]["workflow"]["run_state"]["mode"] == "pipeline"
    assert artifact["blueprint"]["world_bible"]
    assert artifact["blueprint"]["provider"] == "mock"
    assert artifact["outline"]["chapters"]
    assert artifact["outline"]["chapters"][0]["primary_strand"] in {
        "quest",
        "fire",
        "constellation",
    }
    assert artifact["outline"]["chapters"][0]["chapter_objective"]
    assert artifact["outline"]["chapters"][0]["promised_payoff"]
    assert isinstance(artifact["outline"]["chapters"][0]["hook_strength"], int)
    assert artifact["final_review"]["ready_for_publish"] is True
    assert artifact["final_review"]["structural_gate_passed"] is True
    assert artifact["final_review"]["semantic_gate_passed"] is True
    assert artifact["final_review"]["publish_gate_passed"] is True
    assert artifact["final_review"]["structural_review"] is not None
    assert artifact["final_review"]["semantic_review"] is not None
    assert artifact["final_review"]["structural_review"]["metrics"]["continuity_score"] >= 85
    assert artifact["final_review"]["semantic_review"]["metrics"]["reader_pull_score"] >= 78
    assert artifact["workspace"]["memory"]["story_promises"]
    assert artifact["workspace"]["memory"]["promise_ledger"]
    assert artifact["workspace"]["memory"]["pacing_ledger"]
    assert artifact["workspace"]["memory"]["strand_ledger"]
    assert artifact["workspace"]["hybrid_review"]["semantic_review"]["ready_for_publish"] is True
    assert artifact["workspace"]["hybrid_review"]["publish_gate_passed"] is True

    stored_story = await repository.get_by_id(UUID(artifact["story"]["id"]))
    assert stored_story is not None
    assert stored_story.chapter_count == 3


@pytest.mark.asyncio
async def test_alternate_blueprint_shape_populates_memory_and_relationship_metadata() -> None:
    service, repository = build_story_service(
        text_generation_provider=AlternateBlueprintShapeProvider()
    )

    create_result = await service.create_story(
        title="Alternate Blueprint Shape Story",
        genre="fantasy",
        author_id="author-shape",
        premise="A debt archivist discovers erased oaths become ghosts.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    blueprint_result = await service.generate_blueprint(story_id)
    assert blueprint_result.is_ok
    workspace_memory = blueprint_result.value["workspace"]["memory"]
    assert workspace_memory["active_characters"] == [
        "Lin Yuan",
        "High Scribe Vane",
        "Echo",
        "Madam Qiao",
    ]
    assert workspace_memory["world_rules"]
    assert any(
        "erased oath creates a ghost" in str(rule.get("rule", "")).lower()
        for rule in workspace_memory["world_rules"]
    )

    await service.generate_outline(story_id)
    draft_result = await service.draft_story(story_id, target_chapters=3)
    assert draft_result.is_ok

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    assert stored_story.chapters[0].metadata["focus_character"] == "Lin Yuan"
    assert stored_story.chapters[0].metadata["relationship_target"] == "Echo"
    assert stored_story.chapters[0].metadata["relationship_status"]


@pytest.mark.asyncio
async def test_single_digit_hook_strength_is_normalized_to_percentage_scale() -> None:
    service, _repository = build_story_service(
        text_generation_provider=SingleDigitHookStrengthProvider()
    )

    create_result = await service.create_story(
        title="Hook Strength Story",
        genre="fantasy",
        author_id="author-hook",
        premise="A courier follows a living border.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    outline_result = await service.generate_outline(story_id)
    assert outline_result.is_ok
    assert outline_result.value["outline"]["chapters"][0]["hook_strength"] == 60
    assert outline_result.value["outline"]["chapters"][1]["hook_strength"] == 70


@pytest.mark.asyncio
async def test_revise_story_includes_semantic_issues_in_revision_input() -> None:
    provider = RevisionIssueRecordingProvider()
    service, _repository = build_story_service(
        text_generation_provider=provider,
        review_generation_provider=SemanticWarningOnlyProvider(),
    )

    create_result = await service.create_story(
        title="Semantic Revision Story",
        genre="fantasy",
        author_id="author-semantic-revise",
        premise="A city map redraws every promise at midnight.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok
    assert review_result.value["report"]["semantic_gate_passed"] is False

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert "relationship_progression_stall" in provider.revision_issue_codes


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
    assert review_report["structural_review"]["metrics"]["continuity_score"] < 100

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["revision_notes"]
    assert revise_result.value["workspace"]["review"]["ready_for_publish"] is True

    final_review = await service.review_story(story_id)
    assert final_review.is_ok
    assert final_review.value["report"]["ready_for_publish"] is True


@pytest.mark.asyncio
async def test_review_story_returns_hybrid_review_and_semantic_artifacts(
    story_service: tuple[StoryWorkflowService, InMemoryStoryRepository],
) -> None:
    service, _repository = story_service

    create_result = await service.create_story(
        title="Hybrid Review Story",
        genre="fantasy",
        author_id="author-hybrid",
        premise="A border courier discovers every promise to the city has a cost.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok

    workspace = review_result.value["workspace"]
    report = review_result.value["report"]
    assert report["structural_review"] is not None
    assert report["semantic_review"] is not None
    assert workspace["structural_review"]["artifact_id"] == report["structural_review"]["artifact_id"]
    assert workspace["semantic_review"]["artifact_id"] == report["semantic_review"]["artifact_id"]
    assert workspace["hybrid_review"]["artifact_id"] == report["artifact_id"]

    artifact_kinds = {entry["kind"] for entry in workspace["artifact_history"]}
    assert {"review", "semantic_review", "hybrid_review"}.issubset(artifact_kinds)
    assert workspace["memory"]["story_promises"]
    assert workspace["memory"]["promise_ledger"]
    assert workspace["memory"]["pacing_ledger"]
    assert workspace["memory"]["strand_ledger"]


@pytest.mark.asyncio
async def test_draft_failure_preserves_previous_chapters_and_records_failure_artifact() -> None:
    service, repository = build_story_service(
        text_generation_provider=DraftFailureAndSemanticWarningProvider(),
    )

    create_result = await service.create_story(
        title="Failure Story",
        genre="fantasy",
        author_id="author-failure",
        premise="A courier discovers a map that tears when a promise is broken.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)

    draft_result = await service.draft_story(story_id, target_chapters=3)
    assert draft_result.is_err
    assert isinstance(draft_result, Failure)
    assert draft_result.code == "DRAFT_VALIDATION_ERROR"
    assert "Scene content cannot be empty" in draft_result.error

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    assert stored_story.chapter_count == 1

    workspace_result = await service.get_story_workspace(story_id)
    assert workspace_result.is_ok
    workspace = workspace_result.value["workspace"]
    run_id = workspace["workflow"]["current_run_id"] or workspace["workflow"]["run_state"]["run_id"]

    artifact_kinds = {entry["kind"] for entry in workspace["artifact_history"]}
    assert "draft_failure" in artifact_kinds

    run_result = await service.get_story_run(story_id, run_id)
    assert run_result.is_ok
    run_payload = run_result.value
    assert run_payload["failed_stage"] == "draft"
    assert run_payload["failure_code"] == "DRAFT_VALIDATION_ERROR"
    assert "Scene content cannot be empty" in run_payload["failure_message"]
    assert run_payload["manuscript_preserved"] is True
    assert run_payload["failure_snapshot"] is not None
    assert run_payload["failure_snapshot"]["snapshot_type"] == "run_failed"
    assert run_payload["failure_snapshot"]["failure_details"]["manuscript_preserved"] is True
    assert any(entry["kind"] == "draft_failure" for entry in run_payload["failure_artifacts"])
    draft_failure_artifact = next(
        entry for entry in run_payload["failure_artifacts"] if entry["kind"] == "draft_failure"
    )
    assert draft_failure_artifact["payload"]["validation_errors"]
    assert draft_failure_artifact["payload"]["raw_payload"]
    assert draft_failure_artifact["payload"]["normalized_payload"]


@pytest.mark.asyncio
async def test_semantic_warning_with_passing_metrics_does_not_block_publish() -> None:
    service, _repository = build_story_service(
        review_generation_provider=DraftFailureAndSemanticWarningProvider(),
    )

    create_result = await service.create_story(
        title="Warning Story",
        genre="romance",
        author_id="author-warning",
        premise="Two correspondents trade notes across a city that reorders itself.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok
    report = review_result.value["report"]
    assert report["structural_gate_passed"] is True
    assert report["semantic_gate_passed"] is True
    assert report["publish_gate_passed"] is True
    assert any(issue["severity"] == "warning" for issue in report["issues"])

    publish_result = await service.publish_story(story_id)
    assert publish_result.is_ok
    assert publish_result.value["story"]["status"] == "active"
    assert publish_result.value["report"]["publish_gate_passed"] is True
    assert publish_result.value["report"]["semantic_gate_passed"] is True


@pytest.mark.asyncio
async def test_semantic_blocker_still_blocks_publish() -> None:
    service, _repository = build_story_service(
        review_generation_provider=SemanticBlockerProvider(),
    )

    create_result = await service.create_story(
        title="Semantic Blocker Story",
        genre="romance",
        author_id="author-blocker",
        premise="Two correspondents trade notes across a city that reorders itself.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    review_result = await service.review_story(story_id)
    assert review_result.is_ok
    report = review_result.value["report"]
    assert report["semantic_gate_passed"] is False
    assert report["publish_gate_passed"] is False

    publish_result = await service.publish_story(story_id)
    assert publish_result.is_err
    assert isinstance(publish_result, Failure)
    assert publish_result.code == "QUALITY_GATE_FAILED"
    assert publish_result.details is not None
    assert publish_result.details["report"]["semantic_gate_passed"] is False


@pytest.mark.asyncio
async def test_semantic_review_provider_failure_fails_review_stage() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=DeterministicTextGenerationProvider(),
        review_generation_provider=FailingSemanticReviewProvider(),
        default_target_chapters=3,
    )

    create_result = await service.create_story(
        title="Semantic Failure Story",
        genre="fantasy",
        author_id="author-semantic-failure",
        premise="A courier marks every oath on a living map.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=3)

    review_result = await service.review_story(story_id)
    assert review_result.is_err
    assert isinstance(review_result, Failure)
    assert review_result.code == "GENERATION_ERROR"
    assert "semantic review unavailable" in review_result.error


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
    assert publish_result.details is not None
    assert publish_result.details["report"]["ready_for_publish"] is False
    assert publish_result.details["report"]["publish_gate_passed"] is False


@pytest.mark.asyncio
async def test_draft_story_normalizes_nested_scene_shape_from_provider() -> None:
    service, repository = build_story_service(
        text_generation_provider=NestedSceneShapeProvider()
    )

    create_result = await service.create_story(
        title="Nested Scene Story",
        genre="fantasy",
        author_id="author-nested-shape",
        premise="An archivist finds that oaths can hide inside malformed records.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)

    draft_result = await service.draft_story(story_id, target_chapters=3)

    assert draft_result.is_ok
    drafted_story = draft_result.value["story"]
    assert drafted_story["chapter_count"] == 3

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    second_chapter = stored_story.chapters[1]
    assert second_chapter.scenes[0].scene_type == "opening"
    assert second_chapter.scenes[0].content
    assert second_chapter.scenes[-1].scene_type == "ending"
    assert second_chapter.scenes[-1].content


@pytest.mark.asyncio
async def test_legacy_generation_metadata_is_migrated_into_state_repository() -> None:
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
        default_target_chapters=3,
    )

    create_result = await service.create_story(
        title="Legacy Story",
        genre="fantasy",
        author_id="author-legacy",
        premise="A city map keeps moving and only one courier remembers the old roads.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    stored_story.metadata["current_run_id"] = "legacy-run"
    stored_story.metadata["run_history"] = [
        {
            "run_id": "legacy-run",
            "mode": "manual",
            "status": "completed",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00",
            "published": False,
            "stages": [],
        }
    ]
    stored_story.metadata["run_events"] = [
        {
            "event_id": "legacy-event",
            "run_id": "legacy-run",
            "event_type": "run_completed",
            "timestamp": "2024-01-01T00:01:00",
            "stage_name": None,
            "details": {},
        }
    ]
    stored_story.metadata["artifact_history"] = [
        {
            "artifact_id": "legacy-artifact",
            "kind": "review",
            "version": 1,
            "generated_at": "2024-01-01T00:01:00",
            "source_run_id": "legacy-run",
            "source_stage": "review",
            "source_provider": "system",
            "source_model": "continuity-review-v1",
            "parent_artifact_ids": [],
            "payload": {"quality_score": 88},
        }
    ]
    await repository.save(stored_story)

    ctx = service._context_from_story(stored_story)
    assert ctx.workflow.current_run_id == "legacy-run"
    assert len(ctx.run_history) == 1
    assert len(ctx.run_events) == 1
    assert len(ctx.artifact_history) == 1

    await ctx.save()

    migrated_state = await generation_state_repository.get_by_story_id(story_id)
    assert migrated_state is not None
    assert migrated_state.current_run_id == "legacy-run"

    migrated_runs = await generation_run_repository.get_by_story_id(story_id)
    assert migrated_runs is not None
    assert len(migrated_runs.runs) == 1
    assert len(migrated_runs.events) == 1

    migrated_artifacts = await story_artifact_repository.get_by_story_id(story_id)
    assert migrated_artifacts is not None
    assert len(migrated_artifacts.artifacts) == 1

    migrated_story = await repository.get_by_id(UUID(story_id))
    assert migrated_story is not None
    assert "run_history" not in migrated_story.metadata
    assert "run_events" not in migrated_story.metadata
    assert "artifact_history" not in migrated_story.metadata
    assert "current_run_id" not in migrated_story.metadata
