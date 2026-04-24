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
from src.contexts.narrative.application.services.chapter_drafting_service import (
    ChapterDraftingService,
)
from src.contexts.narrative.application.services.story_revision_service import (
    StoryRevisionService,
    TerminalArcSemanticFrame,
)
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.application.services.story_workflow_support import (
    character_names,
    extract_world_rules,
    relationship_progression_status,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryReviewIssue,
    WorldRuleLedgerEntry,
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


def test_relationship_progression_status_delays_trust_until_late_arc() -> None:
    assert relationship_progression_status(chapter_number=9, target_chapters=20) == "forced alliance under duress"
    assert relationship_progression_status(chapter_number=10, target_chapters=20) == "uneasy coordination"
    assert relationship_progression_status(chapter_number=19, target_chapters=20) == "oath-bound allies"


def test_extract_world_rules_reads_nested_magic_system_fragments() -> None:
    world_bible = {
        "setting_name": "The Archive City",
        "magic_system": {
            "seal_behavior": {
                "summary": "The Archive seal knocks once before any rewritten oath exposes its hidden debt.",
            },
            "public_ledger": {
                "ritual": "Witnesses must stand in one line and speak the burned names aloud before the ledger settles.",
            },
            "memory_threading": {
                "summary": "Memory-threading lets a living witness carry trapped guidance, but it cannot restore lost consciousness.",
            },
        },
    }

    rules = extract_world_rules(world_bible)

    assert any("archive seal knocks once" in rule.lower() for rule in rules)
    assert any("witnesses must stand in one line" in rule.lower() for rule in rules)
    assert any("cannot restore lost consciousness" in rule.lower() for rule in rules)


def test_extract_scenes_salvages_top_level_scene_after_inline_field_noise() -> None:
    service = ChapterDraftingService()
    result = TextGenerationResult(
        step="draft",
        provider="mock",
        model="malformed-scene-v1",
        raw_text="malformed scene payload",
        content={
            "scenes": [
                {
                    "scene_type": "opening",
                    "title": "Static in the Mind",
                    "content": "Lin Yuan loses his grip on the memory.",
                },
                {
                    "scene_type": "narrative",
                    "title": "Shadows in the Lower District",
                    "content": "Sister Mo brings the rebels to the safehouse.",
                },
                "scene_type: dialogue",
                "title: The Blood Map",
                "content: ",
            ],
            "scene_type": "dialogue",
            "title": "The Blood Map",
            "content": "The rebel leader lays out the blood map and the alliance terms.",
        },
    )

    scenes = service._extract_scenes(
        result,
        {
            "chapter_number": 7,
            "title": "Broken Alliance Chapter",
        },
    )

    assert len(scenes) == 3
    assert scenes[2]["scene_type"] == "dialogue"
    assert scenes[2]["title"] == "The Blood Map"
    assert "alliance terms" in scenes[2]["content"].lower()


def test_extract_scenes_salvages_malformed_trailing_json_fragment() -> None:
    service = ChapterDraftingService()
    result = TextGenerationResult(
        step="draft",
        provider="dashscope",
        model="malformed-trailing-fragment-v1",
        raw_text="malformed trailing scene payload",
        content={
            "scenes": [
                {
                    "scene_type": "opening",
                    "title": "The Silent Scribe",
                    "content": "Lin Yuan waits beside the sealed ledger as the archive settles.",
                },
                {
                    "scene_type": "narrative",
                    "title": "The Ghosts in the Ink",
                    "content": "Old debts glow faintly in the well while the city exhales below.",
                },
                {
                    "scene_type": "dialogue",
                    "title": "The Apprentice's Question",
                    "content": "Elara asks why anyone keeps writing once rulers and wards are gone.",
                },
                {
                    "scene_type": "action",
                    "title": "The Eternal Flow",
                    "content": "The final entry lands and the archive windows answer with a pulse of light.",
                },
                'scene_type\\": "], "title": "The Circle Closes", "content": "The camera panned out over Mnemosyne until every lit window looked like a witness keeping the city awake."',
            ]
        },
    )

    scenes = service._extract_scenes(
        result,
        {
            "chapter_number": 20,
            "title": "The Circle Closes",
        },
    )

    assert len(scenes) == 5
    assert scenes[-1]["scene_type"] == "narrative"
    assert scenes[-1]["title"] == "The Circle Closes"
    assert "every lit window looked like a witness" in scenes[-1]["content"].lower()


def test_extract_scenes_recovers_top_level_scene_without_explicit_scene_type() -> None:
    service = ChapterDraftingService()
    result = TextGenerationResult(
        step="draft",
        provider="dashscope",
        model="trailing-scene-v1",
        raw_text="malformed trailing scene payload",
        content={
            "scenes": [
                {
                    "scene_type": "opening",
                    "title": "The Crumbling Archive",
                    "content": "The archive trembles under the first warning.",
                },
                {
                    "scene_type": "dialogue",
                    "title": "The Final Coordinates",
                    "content": "The keeper explains the hidden route in the silence.",
                },
                {
                    "scene_type": "action",
                    "title": "The Dissolution",
                    "content": "The last barrier breaks in public view.",
                },
                "scene_type",
            ],
            "title": "The Torch Passes",
            "content": "The final witness takes the charter and leaves the archive behind.",
        },
    )

    scenes = service._extract_scenes(
        result,
        {
            "chapter_number": 20,
            "title": "The Torch Passes",
        },
    )

    assert len(scenes) == 4
    assert scenes[-1]["scene_type"] == "narrative"
    assert scenes[-1]["title"] == "The Torch Passes"
    assert "final witness" in scenes[-1]["content"].lower()


def test_extract_scenes_ignores_trailing_bare_tail_tokens_before_top_level_scene_salvage() -> None:
    service = ChapterDraftingService()
    result = TextGenerationResult(
        step="draft",
        provider="dashscope",
        model="trailing-tail-v1",
        raw_text="malformed trailing scene payload",
        content={
            "scenes": [
                {
                    "scene_type": "opening",
                    "title": "The Archive Shifts",
                    "content": "The first shelves tremble under the warning.",
                },
                {
                    "scene_type": "dialogue",
                    "title": "The Keeper's Reply",
                    "content": "The keeper names the debt out loud.",
                },
                {
                    "scene_type": "action",
                    "title": "The Square Holds",
                    "content": "The square freezes before the next count lands.",
                },
                {
                    "scene_type": "narrative",
                    "title": "The Debt Turns Visible",
                    "content": "The living line sees the cost in public.",
                },
                "decision",
                "title",
                "The Choice of Memory",
                "content",
            ],
            "title": "The Choice of Memory",
            "content": "The final witness takes the charter and leaves the archive behind.",
        },
    )

    scenes = service._extract_scenes(
        result,
        {
            "chapter_number": 20,
            "title": "The Choice of Memory",
        },
    )

    assert len(scenes) == 5
    assert scenes[-1]["scene_type"] == "narrative"
    assert scenes[-1]["title"] == "The Choice of Memory"
    assert "leaves the archive behind" in scenes[-1]["content"].lower()


def test_world_rule_dedupe_collapses_duplicate_cost_entries() -> None:
    entries = [
        WorldRuleLedgerEntry(
            rule="Cost: Using Oath-Weaving requires memory sacrifice and causes Hollowing.",
            source="blueprint",
        ),
        WorldRuleLedgerEntry(
            rule="Using Oath-Weaving requires memory sacrifice and causes Hollowing.",
            source="blueprint",
        ),
    ]

    deduped = StoryRevisionService._dedupe_world_rule_entries(entries)

    assert len(deduped) == 1


def test_antagonistic_profile_text_flags_usurpers_and_erasers() -> None:
    assert StoryRevisionService._is_antagonistic_profile_text(
        "Usurper of the public ledger who plans mass erasure and purge."
    )
    assert not StoryRevisionService._is_antagonistic_profile_text(
        "Archivist preserving witness memory through public confession."
    )


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


class NestedSceneItemsProvider(DeterministicTextGenerationProvider):
    """Return a live-provider scene payload that nests scene objects under `items`."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "chapter_scenes" and int(task.metadata.get("chapter_number", 0)) == 2:
            nested_scene_payload: dict[str, Any] = {
                "scenes": [
                    {
                        "type": [
                            "opening",
                            "narrative",
                            "dialogue",
                            "decision",
                            "climax",
                            "ending",
                        ],
                        "items": [
                            {
                                "scene_type": "opening",
                                "title": "Recovered opening",
                                "content": "The archivist enters the ruined quarter and reads the first surviving oath.",
                            },
                            {
                                "scene_type": "ending",
                                "title": "Recovered ending",
                                "content": "A hidden debt wakes beneath the ledger as the district lights go dark.",
                            },
                        ],
                    }
                ]
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="nested-scene-items-v1",
                raw_text=json.dumps(nested_scene_payload, ensure_ascii=False),
                content=nested_scene_payload,
            )

        return await super().generate_structured(task)


class SingleSceneObjectProvider(DeterministicTextGenerationProvider):
    """Return a provider payload with a single scene object at the root."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "chapter_scenes" and int(task.metadata.get("chapter_number", 0)) == 2:
            scene_payload: dict[str, Any] = {
                "scene_type": "action",
                "title": "Recovered single scene",
                "content": "The archivist drives the ledger blade through the false seal and watches the ward lights gutter out.",
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="single-scene-object-v1",
                raw_text=json.dumps(scene_payload, ensure_ascii=False),
                content=scene_payload,
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


class LinMoContinuityBlueprintProvider(DeterministicTextGenerationProvider):
    """Return a live-style blueprint whose canonical protagonist is Lin Mo."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "bible":
            blueprint_payload: dict[str, Any] = {
                "world_bible": {
                    "setting_name": "The Archive City",
                    "magic_system": {
                        "name": "Oath-ink Resonance",
                        "cost": "Rewriting a civic oath burns away living memory.",
                    },
                    "rules_of_magic": (
                        "1. Every oath binds memory to public order. "
                        "2. Breaking an oath creates a debt that must be paid by a living witness. "
                        "3. Restoring the First Oath demands a visible civic price."
                    ),
                },
                "character_bible": {
                    "protagonist": {
                        "name": "Lin Mo",
                        "motivation": "save his sister from erasure",
                    },
                    "antagonist": {
                        "name": "Vespera",
                        "motivation": "turn civic debt into private rule",
                    },
                    "key_supporting": [
                        {
                            "name": "Grand Scribe Kael",
                            "motivation": "keep the city's first ledger sealed",
                        },
                        {
                            "name": "Echo",
                            "motivation": "recover the truth buried in erased oaths",
                        },
                        {
                            "name": "Madam Qiao",
                            "motivation": "profit from memory ink without losing control",
                        },
                    ],
                },
                "premise_summary": "A debt archivist must rewrite the First Oath before the city dissolves.",
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="lin-mo-blueprint-v1",
                raw_text=json.dumps(blueprint_payload, ensure_ascii=False),
                content=blueprint_payload,
            )

        return await super().generate_structured(task)


class LinWeiKaelContinuityBlueprintProvider(DeterministicTextGenerationProvider):
    """Return a live-style blueprint whose canonical protagonist is Lin Wei."""

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        if task.step == "bible":
            blueprint_payload: dict[str, Any] = {
                "world_bible": {
                    "setting_name": "The Archive City",
                    "magic_system": {
                        "name": "Oath-ink Resonance",
                        "cost": "Rewriting a civic oath burns away living memory.",
                    },
                    "rules_of_magic": (
                        "1. Every oath binds memory to public order. "
                        "2. Breaking an oath creates a debt that must be paid by a living witness. "
                        "3. Restoring the First Oath demands a visible civic price."
                    ),
                },
                "character_bible": {
                    "protagonist": {
                        "name": "Lin Wei",
                        "motivation": "save his sister from erasure and pay the city's oldest debt honestly.",
                    },
                    "antagonist": {
                        "name": "Lady Vespera",
                        "motivation": "turn civic debt into private rule",
                    },
                    "key_supporting": [
                        {
                            "name": "Grand Scribe Kael",
                            "motivation": "seal the founding ledger even if he dies doing it",
                        },
                        {
                            "name": "Archivist Sui",
                            "motivation": "carry Lin Wei's last will through the witness line after the sacrifice",
                        },
                        {
                            "name": "Tanner Ro",
                            "motivation": "keep the confession circle from scattering at dawn",
                        },
                    ],
                },
                "premise_summary": "A debt archivist must rewrite the First Oath before the city dissolves.",
            }
            return TextGenerationResult(
                step=task.step,
                provider="dashscope",
                model="lin-wei-kael-blueprint-v1",
                raw_text=json.dumps(blueprint_payload, ensure_ascii=False),
                content=blueprint_payload,
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


class WarningThenCleanSemanticProvider:
    """Return a warning first, then a clean report after revision closes it."""

    def __init__(self, *, warning_reviews_before_clean: int = 1) -> None:
        self.review_calls = 0
        self.warning_reviews_before_clean = warning_reviews_before_clean

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        if self.review_calls <= self.warning_reviews_before_clean:
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
        else:
            semantic_payload = {
                "semantic_score": 93,
                "reader_pull_score": 90,
                "plot_clarity_score": 88,
                "ooc_risk_score": 8,
                "summary": "The manuscript is semantically coherent and ready for release.",
                "repair_suggestions": [],
                "issues": [],
            }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="warning-then-clean-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LateArcLiveIssueProvider:
    """Return live-run style warnings until the late-arc summaries and ledger are repaired."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        repaired = self.review_calls > 1
        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 92,
                "reader_pull_score": 90,
                "plot_clarity_score": 88,
                "ooc_risk_score": 9,
                "summary": "The late arc now reads as a coherent consequence chain.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 82,
                "reader_pull_score": 75,
                "plot_clarity_score": 68,
                "ooc_risk_score": 15,
                "summary": "The late arc still carries the latest live semantic warnings.",
                "repair_suggestions": [
                    "Replace abstract legacy phrasing with direct survivor agency.",
                    "Make the failed naming attempt physically causal and sensory.",
                    "Turn the blank-slate shell into a visible, symbolic end-state instead of a prop.",
                    "Bridge the missing page directly to the oldest unpaid promise.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter 17 summary still uses vague legacy phrasing instead of named survivor agency.",
                        "location": "Chapter 17 Summary",
                        "suggestion": "Rewrite the aftermath around an active surviving keeper rather than 'Lessons left by ...'.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter 19 still lacks a visceral cause-and-effect chain for the failed naming attempt.",
                        "location": "Chapter 19 Summary",
                        "suggestion": "Show the crowd speaking the debt-name, the recoil, and the ledger striking back in one continuous beat.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "Chapter 20 still risks making the blank-slate shell read like a prop instead of a symbolic foundation.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Give the shell a visible, silent heroic stance with a symbolic object.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "The bridge from the missing page to the oldest unpaid promise is still under-explained.",
                        "location": "Chapters 18-20 Transition",
                        "suggestion": "Make the missing page reveal the specific debt-name that is paid in Chapter 20.",
                    },
                ],
            }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="late-arc-live-issue-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveContinuityDriftProvider:
    """Return the exact continuity warnings seen in the real long-form gate until repaired."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        bad_kael = (
            "grand scribe kael guides lin mo through the archive as a reluctant ally." in prompt
            and "legacy of grand scribe kael guides lin mo through the archive as a reluctant ally." not in prompt
        )
        bad_name_drift = "lin yuan recognizes that his father's erased debt is tied to the first oath's hidden cost." in prompt
        bad_echo = (
            "echo remains a grieving searcher while the city mourns him." in prompt
            and "legacy of echo remains a grieving searcher while the city mourns him." not in prompt
        )
        bad_agency = (
            "lin mo chooses to write the next oath with full awareness." in prompt
            or "vespera asks whether lin mo remembers her and he answers yes." in prompt
        )

        if bad_kael or bad_name_drift or bad_echo or bad_agency:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 66,
                "reader_pull_score": 73,
                "plot_clarity_score": 59,
                "ooc_risk_score": 44,
                "summary": "The manuscript still carries live continuity drift and late-arc agency confusion.",
                "repair_suggestions": [
                    "Replace active post-death cast references with legacy framing.",
                    "Standardize the protagonist name to Lin Mo.",
                    "Make the blank-slate ending instinctual rather than conscious.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "A dead ally is still being treated as active in the mid-arc ledger.",
                        "location": "story",
                        "suggestion": "Replace post-death ally references with legacy framing.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "The protagonist name drifts away from its canonical form.",
                        "location": "story",
                        "suggestion": "Normalize all protagonist references to Lin Mo.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "The ending still grants conscious agency after the total-identity cost.",
                        "location": "story",
                        "suggestion": "Clarify that the final vessel acts on instinct rather than restored consciousness.",
                    },
                ],
            }
        else:
            semantic_payload = {
                "semantic_score": 93,
                "reader_pull_score": 91,
                "plot_clarity_score": 90,
                "ooc_risk_score": 7,
                "summary": "The continuity drift is closed and the late arc reads as a coherent consequence chain.",
                "repair_suggestions": [],
                "issues": [],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-continuity-drift-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveClosureDebtProvider:
    """Return the exact late-arc closure warnings seen in the real long-form gate until repaired."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        repaired = (
            ("the archive seal" in prompt or "the surviving oath seal" in prompt)
            and ("physical anchor" in prompt or "archive seal" in prompt)
            and ("breaks protocol to pull" in prompt or "forced alliance under duress" in prompt)
            and "shared mortal threat" in prompt
            and "blank-slate shell" in prompt
            and "founding lie" in prompt
            and "keep charging the living afterward" in prompt
            and "living voice and not in a return" in prompt
            and "thin red fee mark" in prompt
        )

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 94,
                "reader_pull_score": 91,
                "plot_clarity_score": 92,
                "ooc_risk_score": 6,
                "summary": "The long-form closure is now explicit, paid off, and publishable.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 72,
                "reader_pull_score": 85,
                "plot_clarity_score": 68,
                "ooc_risk_score": 45,
                "summary": "The manuscript still carries unresolved late-arc anchor, relationship, and payoff debt.",
                "repair_suggestions": [
                    "Name the physical anchor explicitly.",
                    "Add a real turning point before the forced alliance.",
                    "Resolve the civic debt and blank-slate agency paradox before publish.",
                ],
                "issues": [
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "The summary states rulers vanish without physical anchors, yet the climax involves rewriting history/memory without mentioning the acquisition or use of a specific anchor for the First Oath, violating the established rule.",
                        "location": "Chapter 16 Summary & World Rules",
                        "suggestion": "Explicitly show the Archive seal or another concrete artifact serving as the physical anchor during the rewrite.",
                    },
                    {
                        "code": "relationship_progression_stall",
                        "severity": "warning",
                        "message": "The relationship status between Lin Mo and Master Chen fluctuates illogically, lacking a clear turning point scene in the summaries.",
                        "location": "Relationship States (Chapters 6-10)",
                        "suggestion": "Insert a specific rescue or shared-threat scene that earns the forced alliance under duress.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "In Chapter 20, the protagonist is described as a blank-slate vessel with no consciousness, yet the summary still implies he writes the first entry as if he returned.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Clarify that a survivor guides the shell's hand and that the motion is instinctual rather than conscious.",
                    },
                    {
                        "code": "promise_break",
                        "severity": "warning",
                        "message": "The hidden civic debt is introduced but not actually resolved, leaving the transition into Chapter 20 unpaid.",
                        "location": "Chapter 19-20 Transition",
                        "suggestion": "Show how the survivors pay the civic debt rather than merely discovering it.",
                    },
                    {
                        "code": "promise_break",
                        "severity": "warning",
                        "message": "Long-running promises remain unpaid for too many chapters.",
                        "location": "story",
                        "suggestion": "Close the oldest unpaid promise before publish.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-closure-debt-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveLateArcContinuityProvider:
    """Return the latest real late-arc continuity warnings until the revision layer closes them."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        repaired = self.review_calls > 1

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 93,
                "reader_pull_score": 90,
                "plot_clarity_score": 91,
                "ooc_risk_score": 7,
                "summary": "The late-arc continuity now reads as a coherent consequence chain.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 65,
                "reader_pull_score": 72,
                "plot_clarity_score": 58,
                "ooc_risk_score": 45,
                "summary": "The story still carries late-arc continuity failures.",
                "repair_suggestions": [
                    "Reframe Old Kael as legacy guidance rather than a living participant.",
                    "Move the blank-slate state to after the ritual.",
                    "Foreshadow the missing-page debt and Yara's anchor role earlier.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Old Kael appears as a physical actor in Chapters 18-20 despite dying in Chapter 8.",
                        "location": "Chapters 18, 19, 20",
                        "suggestion": "Reframe Old Kael as a legacy echo or recorded guidance instead of a living participant.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "Lin Mo rewrites the First Oath while already a blank-slate shell with no self-consciousness.",
                        "location": "Chapter 16 Summary",
                        "suggestion": "Make the shell the consequence of the ritual rather than the acting agent.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The missing page revealing the hidden civic debt appears suddenly in Chapter 19 without prior setup.",
                        "location": "Chapter 19",
                        "suggestion": "Introduce unpaid balances or ledger anomalies in Chapters 9-10.",
                    },
                    {
                        "code": "relationship_progression_stall",
                        "severity": "warning",
                        "message": "Relationship states for Lin Mo and Old Kael fluctuate illogically between hostile confrontation, enemy surveillance, and battle-forged trust.",
                        "location": "Chapters 6-17",
                        "suggestion": "Smooth the arc and remove enemy surveillance once cooperation is established.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Yara's arc shifts abruptly into a reality-anchor role without sufficient buildup.",
                        "location": "Chapter 17",
                        "suggestion": "Foreshadow Yara's memory-threading or merge capability earlier in the story.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-late-arc-continuity-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveHookDebtAndLedgerProvider:
    """Return the latest real hook/ledger warnings until structural and semantic repairs both land."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []
        self.last_present_forbidden_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "last instruction they remember hearing",
            "living voice and not in a return",
            "founding lie",
            "thin red fee mark",
        ]
        forbidden_fragments = [
            "lin wei returns as herself",
            "treat lin wei's appearance as a full return",
            "debt ghost,, a debt ghost",
            "'source': 'lin yuan', 'target': 'lin yuan'",
            "guides the blank-slate vessel's hand",
            "writes the first entry",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        self.last_present_forbidden_fragments = [
            fragment for fragment in forbidden_fragments if fragment in prompt
        ]
        repaired = not self.last_missing_fragments and not self.last_present_forbidden_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 92,
                "reader_pull_score": 90,
                "plot_clarity_score": 90,
                "ooc_risk_score": 8,
                "summary": "The manuscript now sustains hook continuity, clean relationship ledgers, and a publishable final payoff.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 64,
                "reader_pull_score": 76,
                "plot_clarity_score": 59,
                "ooc_risk_score": 44,
                "summary": "The manuscript still carries hook debt, ledger corruption, and compressed late-arc payoff.",
                "repair_suggestions": [
                    "Clean contradictory ghost labels from chapter summaries.",
                    "Replace self-referential relationship states with external allies.",
                    "Frame the Chapter 19 return as memory reconstruction, not resurrection.",
                    "Keep the missing-page debt inside one continuous memorial-pressure line instead of splitting it into a detached investigation.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter summaries still contain contradictory ghost labels that look like a generation failure.",
                        "location": "Chapter Summaries 8-20",
                        "suggestion": "Remove contradictory ghost labels and repair sentence structure.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "Relationship states still show Lin Yuan interacting with Lin Yuan instead of an external ally.",
                        "location": "Relationship States Array (Chapters 8-17)",
                        "suggestion": "Replace self-interaction with the actual ally or survivor carrying the scene.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "The missing-page debt and civic-cost payoff are still compressed relative to the ritual stakes.",
                        "location": "Outline Nodes 19-20",
                        "suggestion": "Keep the missing page, memorial rite, and public payment in one continuous pressure line.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter 19 still risks reading like resurrection instead of a memory reconstruction.",
                        "location": "Outline Node 19 - Promised Payoff",
                        "suggestion": "Use explicit memory-reconstruction language and reject resurrection framing.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-hook-debt-ledger-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilFiveLongformProvider:
    """Return the latest April 5 live long-form warnings until the repair layer closes them."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        has_canonical_world_rules = (
            "world rules: [" in prompt
            and "physical knock before the hidden debt surfaces" in prompt
            and "public ledger of named witnesses stands in order and speaks the burned names aloud before the city can pay an erased debt" in prompt
            and "memory-threading lets a living witness carry trapped guidance" in prompt
        )
        required_fragments = (
            "lin mo's voice is gone for good",
            "never only a family wound but part of the founding lie in the archive purge",
            "any honest confession at dawn will keep charging the living afterward",
            "living voice and not in a return",
            "thin red fee mark",
            "small memory toll in public",
        )
        repaired = (
            has_canonical_world_rules
            and all(fragment in prompt for fragment in required_fragments)
            and "'source': 'lady vespera'" not in prompt
            and "'target': 'lady vespera'" not in prompt
            and "'source': 'vespera'" not in prompt
            and "'target': 'vespera'" not in prompt
            and "the silent council" not in prompt
            and "ledger anomalies" not in prompt
            and "memetic resonance" not in prompt
            and "the cast must pay a visible civic price" not in prompt
            and "the oath exacts a visible civic price" not in prompt
            and "make the first oath cost explicit" not in prompt
            and "lin mo admits lin mo will not return" not in prompt
            and "same tacky mark" not in prompt
            and "obsidian-dark stroke" not in prompt
            and "will have to borrow" not in prompt
            and "choose courage" not in prompt
        )

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 94,
                "reader_pull_score": 91,
                "plot_clarity_score": 90,
                "ooc_risk_score": 8,
                "summary": "The late arc now reads as a defined civic confession with clean relationship ownership.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 85,
                "plot_clarity_score": 78,
                "ooc_risk_score": 15,
                "summary": "The late arc still carries the latest live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Update Relationship Log: Remove or mark as imprisoned all late-arc entries for Lady Vespera.",
                    "Decompress Chapters 17-20 with explicit beat transitions so aftermath, rehearsal, failure, regroup, and confession do not blur together.",
                    "Clarify Protagonist State: keep the Echo-Leader and the Shell as two distinct concepts in the final act.",
                    "Strengthen the Hook: seed the sealed blank line in Chapter 19 before it returns in Chapter 20.",
                ],
                "issues": [
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "Relationship state for Lady Vespera persists after her incapacitation.",
                        "location": "Recent relationship states (Chapters 17-20)",
                        "suggestion": "Change status to imprisoned/memory anchor or remove her from active tracking after Chapter 17.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "Chapters 17-20 compress aftermath, rehearsal, failure, regroup, and confession into overly dense summaries.",
                        "location": "Chapter Summaries 17, 19, 20",
                        "suggestion": "Split the key beats into clearly staged transitions with breathing room.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "Ambiguity between the Echo-Leader and the blank-slate Shell still clouds the final act.",
                        "location": "Chapter Summaries 17, 19, 20",
                        "suggestion": "Use explicit Echo-Leader versus Shell language and keep the Shell passive.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "The sealed blank line still lacks a stronger visual foreshadow during the failed rehearsal.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Show anomalous rehearsal ink in Chapter 19 before the final hook returns in Chapter 20.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-five-longform-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilSixLongformProvider:
    """Return the April 6 live warnings until the Lin Wei / Kael late-arc fix lands."""

    def __init__(self) -> None:
        self.review_calls = 0

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = (
            "lin wei's voice is gone for good",
            "never only a family wound but part of the founding lie in the archive purge",
            "any honest confession at dawn will keep charging the living afterward",
            "living voice and not in a return",
            "thin red fee mark",
            "small memory toll in public",
        )
        repaired = (
            self.review_calls > 1
            and all(fragment in prompt for fragment in required_fragments)
            and "the silent council" not in prompt
            and "ledger anomalies" not in prompt
            and "memetic resonance" not in prompt
            and "'status': 'tactical reliance'" in prompt
            and "'status': 'accepted voice of the public record'" in prompt
            and "'status': 'living voice of the confession line'" in prompt
            and "'source': 'grand scribe kael'" not in prompt
            and "'target': 'grand scribe kael'" not in prompt
            and "same tacky mark" not in prompt
            and "obsidian-dark stroke" not in prompt
            and "will have to borrow" not in prompt
            and "choose courage" not in prompt
        )

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 95,
                "reader_pull_score": 92,
                "plot_clarity_score": 92,
                "ooc_risk_score": 7,
                "summary": "The Lin Wei late arc now separates shell, echo, and survivor duty cleanly enough to publish.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 68,
                "reader_pull_score": 85,
                "plot_clarity_score": 78,
                "ooc_risk_score": 20,
                "summary": "The story still carries the April 6 live semantic failures from the real DashScope gate.",
                "repair_suggestions": [
                    "Insert a visible stall in the dawn confession before Elara forces the square back into line.",
                    "Add one specific citizen-level grief reaction so the Chapter 20 climax lands as lived pain, not only system logic.",
                    "Explicitly resolve Kaelen's presence inside the final chant or the ink's stability instead of leaving it implied.",
                    "Update the Chapter 15 relationship state away from 'strained trust' to match the established mutual dependence.",
                ],
                "issues": [
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "The transition from the failed private rehearsal (Ch 19) to the successful public confession (Ch 20) happens too quickly. The emotional weight of the failed rehearsal needs more breathing room before the dawn bell resolves it.",
                        "location": "Chapter 19-20 Transition",
                        "suggestion": "Insert a brief moment of doubt or near-collapse in the crowd during the dawn sequence before Elara's speech succeeds, making the victory feel earned rather than inevitable.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The climax relies heavily on world mechanics (ink, seals, ledgers). While thematically consistent, it lacks a specific, individual human reaction to the restored memory that would resonate with readers emotionally.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Add a specific vignette of a minor character recognizing a lost loved one's name through the ledger, providing a concrete emotional anchor for the philosophical climax.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "Kaelen's presence in the final chapter is implied but not explicitly described as part of the crowd's chant or the ink's stability, which was promised in the revision notes.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Explicitly describe the sound of Kaelen's voice joining the chorus or the visual of his essence stabilizing the ink trails to close this narrative loop.",
                    },
                    {
                        "code": "relationship_progression_stall",
                        "severity": "warning",
                        "message": "The relationship status for Ch 15 ('strained trust') contradicts the trajectory of the characters who have been working together through life-threatening trials since Ch 3.",
                        "location": "Recent Relationship States - Chapter 15",
                        "suggestion": "Update the status to 'tactical reliance' or 'shared grief' to maintain continuity with the established arc of mutual dependence.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-six-longform-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilTwelvePassThirtyFiveProvider:
    """Return the April 12 pass-35 live warnings until the summary compaction layer lands."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "voice is gone for good",
            "part of the founding lie",
            "keep charging the living afterward",
            "thin red fee mark",
            "small memory toll in public",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 95,
                "reader_pull_score": 92,
                "plot_clarity_score": 92,
                "ooc_risk_score": 7,
                "summary": "The late-arc summaries now read as distinct beats with explicit POV and cost carryover.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 12 pass-35 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Ensure Chapter 17 explicitly includes an internal monologue for the new living voice.",
                    "Reinforce the warning about continuing costs in Chapter 18 and 19.",
                    "Reduce the density of simultaneous actions in the final summaries.",
                ],
                "issues": [
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "The summaries for Chapters 17-20 are extremely dense with simultaneous events (multiple characters acting, multiple magical effects occurring), which risks overwhelming the reader if not broken down clearly in the actual text.",
                        "location": "Chapters 17-20 Summaries",
                        "suggestion": "Break the climax sequence into distinct beats: Private Grief -> Failed Rehearsal -> Public Confession -> Consequence. Ensure each beat has a dedicated focus before moving to the next.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The shift from Lin Yuan (active protagonist) to The Nameless Child (passive vessel/guide) happens abruptly at the end of Chapter 16. Without explicit internal processing in Chapter 17, readers may feel disconnected from the new focal point.",
                        "location": "Chapter 17 Start",
                        "suggestion": "Implement the planned internal monologue for The Nameless Child acknowledging the loss of Lin Yuan's voice and the burden of becoming the living voice immediately upon waking.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The concept of the 'maintenance tax' (red line) appearing immediately after the final oath is introduced. While thematic, it risks feeling like a 'deus ex machina' problem if the setup in previous chapters regarding 'civic debt' wasn't strong enough.",
                        "location": "Chapter 20 Ending",
                        "suggestion": "Reinforce the warning about 'continuing costs' in Chapter 18 and 19 so the red line feels like a logical consequence rather than a new plot device.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-twelve-pass-thirty-five-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortyTwoProvider:
    """Return the April 13 pass-42 live warnings until the bridge/fallout repair layer lands."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "city's eyes and ears",
            "debt ghost claws at the archive seal",
            "thin red fee mark",
            "cannot find his name for one whole breath",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 96,
                "reader_pull_score": 93,
                "plot_clarity_score": 94,
                "ooc_risk_score": 6,
                "summary": "The late-arc bridge, physical threat, and public cost now read as one continuous consequence chain.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-42 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Add an explicit Chapter 17 bridge that makes the new keeper the city's eyes and ears.",
                    "Show a concrete memory toll in Chapter 20 instead of only naming the fee mark abstractly.",
                    "Insert a physical breach attempt during the Chapter 19 rehearsal so the late arc does more than reflect.",
                    "Foreshadow the sibling/founding-lie link earlier through the skipped ferry slate pattern.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The shift from Lin Wei as the primary protagonist to Kaelen taking over the narrative in Chapter 17 lacks an explicit internal bridge, potentially confusing readers about whose perspective they are experiencing.",
                        "location": "Chapter 17, Opening Paragraph",
                        "suggestion": "Add a sentence describing Kaelen's realization that he must now be the eyes and ears for the city since Lin Wei's mind is gone.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The 'thin red fee mark' introduced as the new cost of the magic system is described abstractly; readers need a concrete example of its impact on daily life to feel the stakes.",
                        "location": "Chapter 20, Climax Resolution",
                        "suggestion": "Show a merchant signing a ledger and immediately forgetting their child's name, illustrating the 'memory toll' in real-time.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapters 17-19 rely heavily on exposition and reflection; the lack of an immediate physical threat makes the pacing feel slower than the preceding climax.",
                        "location": "Chapters 17-19 Summary",
                        "suggestion": "Introduce a ghost attempting to breach the Archive seal during the rehearsal to force Kaelen to act physically, not just mentally.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The connection between Kaelen's missing sister and the city's founding lie is revealed late (Chapter 18) without sufficient foreshadowing, making it feel slightly disconnected from the main plot thread.",
                        "location": "Chapter 18 Summary",
                        "suggestion": "Drop subtle hints in earlier chapters linking Kaelen's personal loss to the broader corruption.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-two-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortyThreeProvider:
    """Return the April 13 pass-43 live warnings until the emotional bridge and rail-order fix land."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "scorched fennel-oil smell",
            "lays two fingers against the shell's burned knuckles",
            "the widow's thumb seals red to the iron",
            "one low amber pulse",
            "one-breath public blank",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 96,
                "reader_pull_score": 93,
                "plot_clarity_score": 94,
                "ooc_risk_score": 6,
                "summary": "The late-arc emotional bridge and rehearsal correction now read as concrete, continuous story logic.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-43 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Keep Lin Wei emotionally present through specific sensory memory rather than abstract grief alone.",
                    "State the rehearsal mistake and the corrected rail order explicitly.",
                    "Give Elara one defined shell interaction before dawn so her role is concrete.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The shift from Lin Wei as the active protagonist to a silent vessel may cause reader detachment if the surviving characters do not sufficiently internalize his absence through dialogue or internal thought.",
                        "location": "Chapters 17-19",
                        "suggestion": "Add flashbacks or vivid sensory memories triggered by the shell's presence to keep Lin Wei's voice alive in the narrative even when he cannot speak.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The connection between the private rehearsal failure in Chapter 19 and the successful public payment in Chapter 20 is slightly abstract; the mechanics of how the failure informed the success need tightening.",
                        "location": "Chapter 19 to 20 transition",
                        "suggestion": "Explicitly state what specific error was corrected during the rehearsal that prevented the red fee mark from becoming permanent or fatal in the final scene.",
                    },
                    {
                        "code": "relationship_progression_stall",
                        "severity": "warning",
                        "message": "Elara's reintegration and her specific role in the final ritual relies heavily on implication rather than a defined interaction with the shell or Kaelen.",
                        "location": "Chapter 18",
                        "suggestion": "Include a brief, poignant interaction where Elara touches the shell or speaks directly to it, confirming her acceptance of the new reality before the dawn confession.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-three-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortyFiveProvider:
    """Return the April 13 pass-45 live warnings until Elara setup, Vane breakdown, and sensory anchoring land."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "keeps the evacuation roll moving under falling ash",
            "drags two apprentices behind the ledger barricade",
            "hears the loop of erased names answer in his own cadence",
            "smells scorched fennel oil on her own sleeve",
            "one knock cracks off the public registry rail",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 97,
                "reader_pull_score": 95,
                "plot_clarity_score": 95,
                "ooc_risk_score": 5,
                "summary": "Elara's authority, Vane's collapse, and the final sensory toll now read as one coherent endgame.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-45 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Establish Elara as a witness-line leader in Chapters 12-16 rather than promoting her only at dawn.",
                    "Show Vane hearing the erased names answer him back before the late-arc memorial watch settles.",
                    "Make the final toll physical by tying the fish seller's brief blank to both fennel oil and the registry knock.",
                ],
                "issues": [
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "Elara still reads like a late promotion unless the middle arc lets her visibly command the witness line before the dawn confession.",
                        "location": "Chapters 12-16 Outline",
                        "suggestion": "Seed Elara into the evacuation roll and siege-count beats so her Chapter 20 authority feels earned.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Vane's fall still feels like a physical defeat first and an earned psychological collapse second.",
                        "location": "Chapter 16-17 Transition",
                        "suggestion": "Show the erased names answering in Vane's own cadence before the memorial watch takes over.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The final fee mark remains partly conceptual unless the registry knock and fennel-oil trace land on one citizen in the square.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Tie the fish seller's one-breath blank to the smell of scorched fennel oil and the public registry knock.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-five-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortySixProvider:
    """Return the April 13 pass-46 live warnings until pronouns, repetition, rehearsal clarity, and spirit closure land."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_failures: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        failures: list[str] = []
        if "they now have to be the city's eyes and ears" in prompt or "they must now be the city's eyes and ears" in prompt:
            failures.append("pronoun_drift")
        vane_phrase_count = prompt.count("hears the loop of erased names answer in his own cadence")
        if vane_phrase_count == 0 or vane_phrase_count > 2:
            failures.append("vane_repetition")
        if "witness prop only" not in prompt:
            failures.append("rehearsal_prop_clarity")
        if "lost spirit is finally at rest beyond recall" not in prompt:
            failures.append("spirit_closure")
        self.last_failures = failures
        repaired = self.review_calls > 1 and not failures

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 97,
                "reader_pull_score": 95,
                "plot_clarity_score": 95,
                "ooc_risk_score": 5,
                "summary": "Late-arc pronouns, Vane's transition, rehearsal mechanics, and the sister's closure now read cleanly.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 82,
                "reader_pull_score": 75,
                "plot_clarity_score": 68,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-46 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Standardize Lin Mo references in the late arc and remove singular 'they' drift.",
                    "Keep Vane's full realization in Chapter 16 only; let Chapter 17 focus on aftermath silence.",
                    "State that the Chapter 19 rehearsal uses the shell only as a witness prop while the living line borrows the cadence.",
                    "Give the sister's spirit a final, explicit closure line in Chapter 20.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Late-arc summaries still drift into singular 'they' for Lin Mo.",
                        "location": "Chapters 17-20 Summaries",
                        "suggestion": "Replace the drifting pronouns with explicit role statements or stable third-person references.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Vane's realization is still repeated across the climax and immediate aftermath.",
                        "location": "Chapter 16 & 17 Summaries",
                        "suggestion": "Keep the breakdown in Chapter 16 only and let Chapter 17 carry only the silence left behind.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The failed rehearsal still reads as if the shell itself is participating rather than serving as a passive proof object.",
                        "location": "Chapter 19 Summary",
                        "suggestion": "State explicitly that the shell is only a witness prop and that the living line carries the borrowed cadence.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The restored sister's closure is still emotionally incomplete without a final statement that her spirit is at rest.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Add a final sentence confirming the lost spirit is finally at rest beyond recall.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-six-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortySevenProvider:
    """Return the April 13 pass-47 live warnings until Elara hesitation, purge logic, and rail-order causality land."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "feels the cold reflex knock answer instead of a voice",
            "the debt-name stayed unwritten and outside the purge logic",
            "the widow's thumb seals red to the iron",
            "one low amber pulse",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 97,
                "reader_pull_score": 95,
                "plot_clarity_score": 95,
                "ooc_risk_score": 5,
                "summary": "Elara's grief beat, the purge logic, and the rehearsal-to-dawn causality now read explicitly and cleanly.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-47 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Give Elara one physical hesitation beat at the shell before she accepts the register.",
                    "Explain why the missing-sister page stayed outside the purge logic.",
                    "State the rail-order lesson explicitly in Chapter 19 before Chapter 20 uses it.",
                ],
                "issues": [
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "Elara's grief-to-duty transition is still too quick without a tactile refusal beat at the shell.",
                        "location": "Chapter 17 Summary",
                        "suggestion": "Show Elara flinch from the shell's cold knock before she accepts the duty.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "The page's survival still needs an explicit rule-based explanation rather than coincidence.",
                        "location": "Chapter 18 Summary",
                        "suggestion": "Explain that the debt-name stayed unwritten and therefore outside the purge logic.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The rehearsal-to-dawn transition still needs one explicit statement of why the old rail order failed.",
                        "location": "Chapter 19 Summary -> Chapter 20 Transition",
                        "suggestion": "Have Elara state that the line touched the public registry before the family rail was warm, and that dawn must reverse the order.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-seven-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortyEightProvider:
    """Return the April 13 pass-48 live warnings until the climax becomes concrete and Elara drives the rail-order fix."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "his right hand ashes away from the nails inward",
            "one iron crack",
            "one low amber pulse",
            "one full breath again",
            "single family-sized shock",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 97,
                "reader_pull_score": 95,
                "plot_clarity_score": 95,
                "ooc_risk_score": 5,
                "summary": "The climax is concrete, Elara drives the corrective plan, and the ending now foregrounds one family-sized shock instead of summary overload.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 82,
                "reader_pull_score": 75,
                "plot_clarity_score": 68,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-48 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Make Vane's collapse concrete and physical.",
                    "Have Elara argue the rail-order fix instead of merely inheriting it.",
                    "State the mechanical difference between Public Registry and Family Rail.",
                    "Reduce Chapter 20's overload by foregrounding one family-sized shock.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The climax still needs more visible magical consequences.",
                        "location": "Chapter 16 Summary",
                        "suggestion": "Show Vane's hand turning to ash and his voice tearing into static.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "Elara still needs to be seen actively winning the strategy argument.",
                        "location": "Chapter 19 Summary",
                        "suggestion": "Have Elara argue that the public registry forces collective payment while the family rail localizes the cost.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The mechanical difference between the two rails is still too implied.",
                        "location": "Chapter 19 Summary",
                        "suggestion": "State plainly that the Public Registry makes the whole square pay at once while the Family Rail lets one household carry the name first.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "Chapter 20 still tries to carry too many outcomes at once.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Foreground the fish seller's family-sized shock and let the system change sit behind it.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-eight-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilThirteenPassFortyNineProvider:
    """Return the April 13 pass-49 live warnings until the sacrifice, rehearsal, and closure beats become concrete."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "guides that hand onto the rail",
            "choose the rewrite over returning to the body",
            "choose that price",
            "the widow's thumb seals red to the iron",
            "one full breath again",
            "into the burned ear",
            "lets the name go with no answer coming back",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 97,
                "reader_pull_score": 96,
                "plot_clarity_score": 96,
                "ooc_risk_score": 4,
                "summary": "The late arc now gives the protagonist an active final choice, dramatizes the failed rehearsal, and lands the sister-line closure with intimate specificity.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 82,
                "reader_pull_score": 75,
                "plot_clarity_score": 68,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 13 pass-49 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Split the sacrifice summary into clearer beats and make the protagonist choose the sacrifice actively.",
                    "Show the wrong rail order physically harming a witness before the keeper corrects it.",
                    "Add an intimate beat where someone whispers the missing sister's name into the shell before the public confession.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter 16 still compresses too much ritual and transformation into one passive paragraph.",
                        "location": "Recent Chapter Summaries - Chapter 16",
                        "suggestion": "Separate the rite, the antagonist's defeat, and the protagonist's chosen transformation into clearer action beats.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "Chapter 19 still explains the new rail order instead of showing the failed rehearsal as immediate harm.",
                        "location": "Recent Chapter Summaries - Chapter 19",
                        "suggestion": "Show the widow's hand locking to the wrong rail and the corrected order restoring one breath before the explanation lands.",
                    },
                    {
                        "code": "ooc_behavior",
                        "severity": "warning",
                        "message": "The protagonist's sacrifice still reads too passive across Chapters 16 and 17.",
                        "location": "Recent Chapter Summaries - Chapter 16 & 17",
                        "suggestion": "Make the protagonist guide the keeper into the final duty and remind the witness line that the silence was a chosen cost.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Chapter 20 still lacks a private emotional handoff for the missing sister line.",
                        "location": "Recent Chapter Summaries - Chapter 20",
                        "suggestion": "Add a beat where the keeper whispers the missing sister's name into the shell before the square answers.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-thirteen-pass-forty-nine-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilFourteenPassFiftyEightProvider:
    """Return the April 14 pass-58 live warnings until the late arc gains visual ledger change, a learned dawn signal, and a tangible shell anchor."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "black ink bleeds back into that blank line",
            "gets breath only after the family line answers",
            "watches the public rail stay dead until that first beat holds",
            "youngest clerk lays two fingers on the shell's scorched wrist",
            "ember-warm pulse",
        ]
        forbidden_fragments = [
            "the apparition makes it plain",
        ]
        missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        present_forbidden_fragments = [
            fragment for fragment in forbidden_fragments if fragment in prompt
        ]
        self.last_missing_fragments = missing_fragments + [
            f"forbidden:{fragment}" for fragment in present_forbidden_fragments
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 98,
                "reader_pull_score": 96,
                "plot_clarity_score": 96,
                "ooc_risk_score": 4,
                "summary": "The late arc now shows the ledger changing on the page, proves the witnesses learned why dawn can work, and gives the shell a tangible final anchor.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 15,
                "summary": "The story still carries the April 14 pass-58 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Show the missing-sister reveal through visible ledger change, not narrator explanation.",
                    "Make the failed rehearsal teach the crowd the winning dawn sequence through breath and rail response, not explanation.",
                    "Give Chapter 20 a physical shell-anchor so grief is felt through touch, not only absence.",
                ],
                "issues": [
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "The final summaries still feel too compressed and need the crowd's lesson from the failed rehearsal shown through action more concretely.",
                        "location": "Chapter 19-20 Transition",
                        "suggestion": "Show that breath returns only after the family line answers and the public rail stays dead before that beat holds.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The founding-lie reveal still leans on narration instead of a visible magical consequence.",
                        "location": "Chapter 18 Summary",
                        "suggestion": "Show ink physically bleeding back into the erased ledger line when the name is spoken.",
                    },
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "The ending still needs a tangible shell-anchor to keep Lin Yuan's absence from feeling overly abstract.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Have a child or ally touch the shell and feel a last pulse or whisper through the seal before accepting the silence.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-fourteen-pass-fifty-eight-v1",
            raw_text=json.dumps(semantic_payload, ensure_ascii=False),
            content=semantic_payload,
        )


class LiveAprilFourteenPassSixtyProvider:
    """Return the April 14 pass-60 live warnings until Yuna's collapse, the tax causality, and the two-phase dawn closure are explicit."""

    def __init__(self) -> None:
        self.review_calls = 0
        self.last_missing_fragments: list[str] = []

    async def generate_structured(self, task: TextGenerationTask) -> TextGenerationResult:
        self.review_calls += 1
        prompt = task.user_prompt.lower()
        required_fragments = [
            "folding to one knee",
            "the room can rehearse the cost but cannot ratify it alone",
            "that private beat closes the family wound first",
            "the same thin red fee mark that flashed and faded on the practice ledger",
        ]
        self.last_missing_fragments = [
            fragment for fragment in required_fragments if fragment not in prompt
        ]
        repaired = self.review_calls > 1 and not self.last_missing_fragments

        if repaired:
            semantic_payload: dict[str, Any] = {
                "semantic_score": 98,
                "reader_pull_score": 96,
                "plot_clarity_score": 96,
                "ooc_risk_score": 4,
                "summary": "The late arc now lets Yuna physically break before taking command, proves the rehearsal only previews the tax, and separates the private closure from the public dawn order.",
                "repair_suggestions": [],
                "issues": [],
            }
        else:
            semantic_payload = {
                "semantic_score": 92,
                "reader_pull_score": 88,
                "plot_clarity_score": 85,
                "ooc_risk_score": 12,
                "summary": "The story still carries the April 14 pass-60 live semantic warnings from the real DashScope gate.",
                "repair_suggestions": [
                    "Give Yuna a visible physical collapse before she reclaims the register and takes command.",
                    "State that the practice-ledger fee fades because the room cannot ratify the tax alone.",
                    "Separate the family closure beat from the public-rail beat and tie the fish seller to the same fee mark previewed in rehearsal.",
                ],
                "issues": [
                    {
                        "code": "plot_confusion",
                        "severity": "warning",
                        "message": "Yuna still accepts the burden too cleanly without a visible physical failure.",
                        "location": "Chapter 17 Summary",
                        "suggestion": "Make her drop the register or buckle before forcing herself back into command.",
                    },
                    {
                        "code": "world_logic_soft_conflict",
                        "severity": "warning",
                        "message": "The practice-ledger fee still does not clearly explain why the public tax in Chapter 20 must wait for the square.",
                        "location": "Chapter 19-20 Transition",
                        "suggestion": "State that the room can rehearse the cost but cannot ratify it alone.",
                    },
                    {
                        "code": "weak_serial_pull",
                        "severity": "warning",
                        "message": "Chapter 20 still needs a cleaner sequence from private grief to public order.",
                        "location": "Chapter 20 Summary",
                        "suggestion": "Close the family wound first, then move the public rail, then show the fish seller receive the same fee mark previewed in rehearsal.",
                    },
                ],
            }

        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="live-april-fourteen-pass-sixty-v1",
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


def test_issue_departure_hints_detect_explicit_chapter_death_sacrifice_wording() -> None:
    service, _repository = build_story_service()

    hints = service._revision_service._issue_departure_hints(
        "grand scribe kael is listed as having active relationship status with lin wei in chapters 17, 18, 19, and 20, but chapter 14 explicitly depicts his death/sacrifice.",
        {"Grand Scribe Kael", "Lin Wei"},
    )

    assert hints == {"Grand Scribe Kael": 14}


def test_departure_chapter_for_name_matches_title_and_reference_aliases() -> None:
    service, _repository = build_story_service()

    departed_characters = {"Grand Scribe Kaelen": 8}

    assert service._revision_service._departure_chapter_for_name("Master Kaelen", departed_characters) == 8
    assert service._revision_service._departure_chapter_for_name("Old Kaelen", departed_characters) == 8


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
    review_provider = WarningThenCleanSemanticProvider(
        warning_reviews_before_clean=2
    )
    service, _repository = build_story_service(
        text_generation_provider=provider,
        review_generation_provider=review_provider,
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
    if not revise_result.is_ok:
        raise AssertionError(str(getattr(review_provider, "last_missing_fragments", [])))
    assert "relationship_progression_stall" in provider.revision_issue_codes
    assert revise_result.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_live_longform_late_arc_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LateArcLiveIssueProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=DeterministicTextGenerationProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Late Arc Repair Story",
        genre="fantasy",
        author_id="author-live-repair",
        premise="A rewritten oath can save the city but erase the one who signs it.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    stored_story.chapters[18].summary = (
        "The first public oath of the new era reveals a hidden debt under the city's "
        "foundation, showing that the old system still has one last claim."
    )
    stored_story.chapters[18].metadata["relationship_status"] = "oath-bound allies"
    stored_story.chapters[19].summary = (
        "Lin Yuan is a blank-slate vessel but retains a spark of consciousness and begins to write "
        "the next oath."
    )
    stored_story.chapters[19].metadata["relationship_status"] = "oath-bound allies"
    await repository.save(stored_story)

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    for chapter_number in (10, 12, 16, 18, 19, 20):
        outline_chapter = outline_payload["chapters"][chapter_number - 1]
        outline_chapter["chapter_objective"] = "Make the First Oath cost explicit."
        outline_chapter["summary"] = (
            f"{outline_chapter['summary']} Make the First Oath cost explicit."
        ).strip()
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"world_logic_soft_conflict", "plot_confusion", "ooc_behavior"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    assert workspace["evidence_summary"]["warning_count"] == 0
    assert chapter17["metadata"]["relationship_target"]
    assert workspace["story"]["chapters"][18]["metadata"]["relationship_status"]
    assert workspace["story"]["chapters"][18]["metadata"]["relationship_status"] != "battle-forged trust"
    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_live_continuity_drift_from_real_longform_gate() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveContinuityDriftProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinMoContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Real Gate Drift Story",
        genre="fantasy",
        author_id="author-live-drift",
        premise="A debt archivist must save a city by rewriting the first oath and paying with memory.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[1].summary = (
        "Grand Scribe Kael dies sealing the first breach in the archive and leaves only his oath tools behind."
    )
    stored_story.chapters[7].summary = (
        "Grand Scribe Kael guides Lin Mo through the archive as a reluctant ally."
    )
    stored_story.chapters[7].metadata["focus_character"] = "Lin Mo"
    stored_story.chapters[7].metadata["relationship_target"] = "Grand Scribe Kael"
    stored_story.chapters[7].metadata["relationship_status"] = "reluctant allies"
    stored_story.chapters[9].summary = (
        "Lin Yuan recognizes that his father's erased debt is tied to the first oath's hidden cost. "
        "Lin Yuan recognizes that his father's erased debt is tied to the first oath's hidden cost."
    )
    stored_story.chapters[11].summary = (
        "Echo sacrifices himself to keep the oath engine from tearing the city apart."
    )
    stored_story.chapters[15].summary = (
        "Lin Mo pays with his entire identity to rewrite the First Oath, but the city still fears the cost."
    )
    stored_story.chapters[16].summary = (
        "Vespera asks whether Lin Mo remembers her and he answers yes."
    )
    stored_story.chapters[18].summary = "Echo remains a grieving searcher while the city mourns him."
    stored_story.chapters[18].metadata["focus_character"] = "Echo"
    stored_story.chapters[18].metadata["relationship_target"] = "Lin Mo"
    stored_story.chapters[18].metadata["relationship_status"] = "grieving searcher"
    stored_story.chapters[19].summary = (
        "Lin Mo survives only as a blank slate while the city mistakes the vessel for a return."
    )

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][1]["summary"] = stored_story.chapters[1].summary
    outline_payload["chapters"][7]["summary"] = stored_story.chapters[7].summary
    outline_payload["chapters"][9]["summary"] = stored_story.chapters[9].summary
    outline_payload["chapters"][11]["summary"] = stored_story.chapters[11].summary
    outline_payload["chapters"][15]["chapter_objective"] = (
        "Lin Mo chooses to write the next oath with full awareness."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "ooc_behavior", "world_logic_soft_conflict"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter8 = workspace["story"]["chapters"][7]
    chapter10 = workspace["story"]["chapters"][9]
    chapter19 = workspace["story"]["chapters"][18]
    outline_chapter8 = workspace["outline"]["chapters"][7]
    outline_chapter16 = workspace["outline"]["chapters"][15]
    outline_chapter17 = workspace["outline"]["chapters"][16]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert chapter8["metadata"]["relationship_target"] != "Grand Scribe Kael"
    assert "Grand Scribe Kael guides Lin Mo through the archive as a reluctant ally." not in chapter8["summary"]
    assert "Grand Scribe Kael guides Lin Mo through the archive as a reluctant ally." not in outline_chapter8["summary"]
    assert chapter10["summary"].count(
        "Lin Mo recognizes that his father's erased debt is tied to the first oath's hidden cost."
    ) == 1
    assert "Lin Yuan" not in chapter10["summary"]
    assert "Lin Yuan" not in workspace["outline"]["chapters"][9]["summary"]
    assert chapter19["metadata"]["focus_character"] != "Echo"
    assert "Echo remains a grieving searcher while the city mourns him." not in chapter19["summary"]
    assert "chooses to write the next oath with full awareness" not in outline_chapter16["chapter_objective"].lower()
    assert "he answers yes" not in outline_chapter17["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_live_anchor_and_promise_warnings_from_real_longform_gate() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveClosureDebtProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinMoContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Real Gate Closure Story",
        genre="fantasy",
        author_id="author-live-closure",
        premise="A debt archivist must save a city by rewriting the first oath and paying with memory.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[7].summary = (
        "Master Chen keeps Lin Mo under enemy surveillance and refuses to explain why they should cooperate."
    )
    stored_story.chapters[7].metadata["focus_character"] = "Lin Mo"
    stored_story.chapters[7].metadata["relationship_target"] = "Master Chen"
    stored_story.chapters[7].metadata["relationship_status"] = "enemy surveillance"
    stored_story.chapters[8].summary = (
        "Lin Mo and Master Chen enter a forced alliance without any visible turning point."
    )
    stored_story.chapters[8].metadata["focus_character"] = "Lin Mo"
    stored_story.chapters[8].metadata["relationship_target"] = "Master Chen"
    stored_story.chapters[8].metadata["relationship_status"] = "forced alliance under duress"
    stored_story.chapters[10].summary = (
        "The cast learns the First Oath needs a cost, but no physical anchor is ever named."
    )
    stored_story.chapters[18].summary = (
        "The missing page reveals a hidden civic debt, but nobody knows how to answer it."
    )
    stored_story.chapters[19].summary = (
        "Lin Mo is a blank-slate vessel with no consciousness, yet he writes the first entry of the next oath as if he has returned."
    )

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][7]["summary"] = stored_story.chapters[7].summary
    outline_payload["chapters"][8]["summary"] = stored_story.chapters[8].summary
    outline_payload["chapters"][10]["summary"] = stored_story.chapters[10].summary
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Lin Mo writes the first entry of the next oath even after becoming a blank slate."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {
        "world_logic_soft_conflict",
        "relationship_progression_stall",
        "ooc_behavior",
        "promise_break",
    } <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter8 = workspace["story"]["chapters"][7]
    chapter9 = workspace["story"]["chapters"][8]
    chapter11 = workspace["story"]["chapters"][10]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    chapter18 = workspace["story"]["chapters"][17]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "breaks protocol to pull" in chapter8["summary"].lower()
    assert chapter9["metadata"]["relationship_status"] == "forced alliance under duress"
    assert "shared mortal threat" in chapter8["summary"].lower()
    assert "physical anchor" in chapter11["summary"].lower()
    assert "archive seal" in chapter11["summary"].lower()
    assert "missing page" in chapter18["summary"].lower()
    assert "founding lie" in chapter18["summary"].lower()
    assert "keep charging the living afterward" in chapter18["summary"].lower()
    assert "last instruction they remember hearing" in chapter19["summary"].lower()
    assert "living voice and not in a return" in chapter19["summary"].lower()
    assert "blank-slate shell" in chapter20["summary"].lower()
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "city's original sin" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "writes the first entry" not in chapter20["summary"].lower()
    assert "guides the blank-slate vessel's hand" not in chapter20["summary"].lower()
    assert "founding lie" in outline_chapter20["promised_payoff"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_latest_live_late_arc_continuity_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveLateArcContinuityProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinMoContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Latest Live Late Arc Story",
        genre="fantasy",
        author_id="author-late-arc-live",
        premise="A debt archivist must save a city by rewriting the first oath and paying with memory.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[7].summary = (
        "Grand Scribe Kael dies sealing the archive breach."
    )
    stored_story.chapters[15].summary = (
        "Lin Mo is already a blank-slate shell when the city asks him to rewrite the First Oath."
    )
    stored_story.chapters[16].summary = (
        "Yara abruptly merges with Lin Mo and becomes a reality anchor with no prior preparation."
    )
    stored_story.chapters[18].summary = (
        "Old Kael performs memorial rites in person while the city discovers a missing page with no earlier warning."
    )
    stored_story.chapters[19].summary = (
        "Old Kael helps carry the final rite even though his death was already established."
    )
    stored_story.chapters[6].metadata["relationship_target"] = "Old Kael"
    stored_story.chapters[6].metadata["relationship_status"] = "enemy surveillance"
    stored_story.chapters[16].metadata["relationship_target"] = "Old Kael"
    stored_story.chapters[16].metadata["relationship_status"] = "battle-forged trust"

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][15]["summary"] = stored_story.chapters[15].summary
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "world_logic_soft_conflict", "relationship_progression_stall"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert chapter17["metadata"]["relationship_target"]
    assert chapter17["metadata"]["relationship_target"] != chapter17["metadata"]["focus_character"]
    assert chapter19["metadata"]["relationship_target"]
    assert chapter19["metadata"]["relationship_target"] != chapter19["metadata"]["focus_character"]
    assert workspace["story"]["chapters"][18]["metadata"]["relationship_status"]
    assert workspace["story"]["chapters"][18]["metadata"]["relationship_status"] != "battle-forged trust"
    assert chapter20["metadata"]["relationship_target"]
    assert chapter20["metadata"]["relationship_target"] != chapter20["metadata"]["focus_character"]

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_latest_real_hook_and_ledger_failures() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveHookDebtAndLedgerProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=DeterministicTextGenerationProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Latest Real Hook Debt Story",
        genre="fantasy",
        author_id="author-hook-ledger-live",
        premise="A debt archivist must save the city from an oath plague without resurrecting the dead.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[1].scenes[-1].update_content(
        "Lin Yuan locks the ledger vault and leaves the chapter on a flat administrative beat."
    )
    stored_story.chapters[2].scenes[0].update_content(
        "Lin Yuan enters the outer archive and refuses to address the prior chapter's reveal before pivoting to patrol chatter."
    )
    stored_story.chapters[10].scenes[-1].update_content(
        "The survivors quietly reset the ward and close the chapter without a reveal or cliffhanger."
    )

    for chapter_number in range(8, 17):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Lin Yuan"
        chapter.metadata["relationship_target"] = "Lin Yuan"
        chapter.metadata["relationship_status"] = (
            "guarded cooperation" if chapter_number < 12 else "battle-forged trust"
        )

    for chapter_number in (8, 11, 14):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.summary = (
            f"{chapter.summary} Echo, a Debt Ghost,, a Debt Ghost,, a Debt Ghost, trails Lin Yuan through the memorial ledgers."
        ).strip()

    stored_story.chapters[18].summary = (
        "During the memorial rite, the city mentions a missing page and a civic debt only after the main action has already cooled."
    )
    stored_story.chapters[19].summary = (
        "Lin Wei appears at the rite as if she has fully returned to life, while Lin Yuan's shell reaches for the oath before the city has paid its civic debt."
    )
    stored_story.chapters[19].scenes[0].update_content(
        "Lin Wei steps into the rite as though resurrected, and the crowd reacts before anyone explains the hidden civic debt."
    )

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][1]["hook"] = "Which erased witness opened the sealed ledger?"
    outline_payload["chapters"][1]["summary"] = stored_story.chapters[1].summary
    outline_payload["chapters"][2]["summary"] = stored_story.chapters[2].summary
    outline_payload["chapters"][10]["hook"] = "Who will pay the oath's next visible cost before sunrise?"
    outline_payload["chapters"][10]["summary"] = stored_story.chapters[10].summary
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Treat Lin Wei's appearance as a full return and settle the civic debt after the ritual is over."
    )
    outline_payload["chapters"][19]["promised_payoff"] = (
        "Lin Wei returns as herself and the city moves on once the rite is complete."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {
        "missing_hook",
        "missing_hook_payoff",
        "hook_debt",
        "plot_confusion",
        "world_logic_soft_conflict",
        "weak_serial_pull",
    } <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(
            {
                "missing": review_provider.last_missing_fragments,
                "forbidden": review_provider.last_present_forbidden_fragments,
            }
        )
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter2 = workspace["story"]["chapters"][1]
    chapter3 = workspace["story"]["chapters"][2]
    chapter11 = workspace["story"]["chapters"][10]
    chapter9 = workspace["story"]["chapters"][8]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert (
        chapter2["metadata"]["outline_hook"].lower() in chapter2["scenes"][-1]["content"].lower()
        or chapter2["scenes"][-1]["content"].rstrip().endswith("?")
    )
    assert "directly answers the previous hook" in chapter3["scenes"][0]["content"].lower()
    assert (
        chapter11["metadata"]["outline_hook"].lower()
        in chapter11["scenes"][-1]["content"].lower()
        or chapter11["scenes"][-1]["content"].rstrip().endswith("?")
    )
    assert ", a debt ghost,, a debt ghost" not in chapter9["summary"].lower()
    for chapter_number in range(8, 17):
        workspace_chapter = workspace["story"]["chapters"][chapter_number - 1]
        assert (
            workspace_chapter["metadata"]["relationship_target"]
            != workspace_chapter["metadata"]["focus_character"]
        )
    assert "last instruction they remember hearing" in chapter19["summary"].lower()
    assert "living voice and not in a return" in chapter19["summary"].lower()
    assert "the body will never speak again" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "returned mind" not in chapter20["summary"].lower()
    assert chapter20["metadata"]["relationship_target"]
    assert (
        chapter20["metadata"]["relationship_target"]
        != chapter20["metadata"]["focus_character"]
    )
    assert "city's original sin" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "keep charging the living afterward" in workspace["story"]["chapters"][17]["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_five_live_longform_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilFiveLongformProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinMoContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Five Live Longform Story",
        genre="fantasy",
        author_id="author-april-five-live",
        premise="A debt archivist must save a city by rewriting the first oath and paying with memory.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    story_memory["world_rules"] = []
    relationship_states = story_memory.get("relationship_states", [])
    if not isinstance(relationship_states, list):
        relationship_states = []
    active_characters = story_memory.get("active_characters", [])
    if isinstance(active_characters, list) and "Elara" not in active_characters:
        active_characters.append("Elara")
        story_memory["active_characters"] = active_characters
    for chapter_number in (17, 18, 19, 20):
        relationship_states.append(
            {
                "chapter_number": chapter_number,
                "source": "Lady Vespera",
                "target": "Lin Mo" if chapter_number == 17 else "Lady Vespera",
                "status": "imprisoned memory sway",
            }
        )
    story_memory["relationship_states"] = relationship_states
    stored_story.metadata["story_memory"] = story_memory
    workflow_payload = stored_story.metadata.get("workflow", {})
    assert isinstance(workflow_payload, dict)
    blueprint_payload = workflow_payload.get("blueprint", {})
    assert isinstance(blueprint_payload, dict)
    character_bible = blueprint_payload.get("character_bible", {})
    assert isinstance(character_bible, dict)
    key_supporting = character_bible.get("key_supporting", [])
    assert isinstance(key_supporting, list)
    if not any(
        isinstance(entry, dict) and str(entry.get("name", "")).strip() == "Elara"
        for entry in key_supporting
    ):
        key_supporting.append(
            {
                "name": "Elara",
                "motivation": "carry Lin Mo's will into the public ledger after the sacrifice.",
            }
        )
    character_bible["key_supporting"] = key_supporting
    blueprint_payload["character_bible"] = character_bible
    workflow_payload["blueprint"] = blueprint_payload
    stored_story.metadata["workflow"] = workflow_payload
    for chapter_number in (17, 18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Lady Vespera"
        chapter.metadata["relationship_target"] = "Lady Vespera"
        chapter.metadata["relationship_status"] = "imprisoned memory sway"
    stored_story.chapters[18].summary = (
        f"{stored_story.chapters[18].summary} Lin Mo remains a blank-slate shell that can only answer with a knock."
    ).strip()
    stored_story.chapters[19].summary = (
        f"{stored_story.chapters[19].summary} The city treats Lin Mo as a blank-slate shell and cannot tell whether the Echo-Leader is a memory reconstruction or a resurrection."
    ).strip()
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"world_logic_soft_conflict", "ooc_behavior", "weak_serial_pull"} <= issue_codes_before
    assert "world_rule_gap" not in issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    world_rules = workspace["story"]["metadata"]["story_memory"]["world_rules"]
    repaired_relationship_states = workspace["story"]["metadata"]["story_memory"]["relationship_states"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter18 = workspace["outline"]["chapters"][17]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter18_scene_text = " ".join(scene["content"] for scene in chapter18["scenes"]).lower()
    chapter19_scene_text = " ".join(scene["content"] for scene in chapter19["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    late_arc_text = " ".join(
        [
            chapter17["summary"],
            chapter18["summary"],
            chapter19["summary"],
            chapter20["summary"],
            outline_chapter17["chapter_objective"],
            outline_chapter18["chapter_objective"],
            outline_chapter19["chapter_objective"],
            outline_chapter20["chapter_objective"],
            outline_chapter17["hook"],
            outline_chapter18["hook"],
            outline_chapter19["hook"],
            outline_chapter20["hook"],
        ]
    ).lower()

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert any("physical knock before the hidden debt surfaces" in entry["rule"].lower() for entry in world_rules)
    assert any("public ledger of named witnesses stands in order and speaks the burned names aloud before the city can pay an erased debt" in entry["rule"].lower() for entry in world_rules)
    assert any("memory-threading lets a living witness carry trapped guidance" in entry["rule"].lower() for entry in world_rules)
    keeper = chapter17["metadata"]["focus_character"]
    assert keeper
    assert keeper != "Lin Mo"
    assert "ghost" not in keeper.lower()
    assert "ledger" not in keeper.lower()
    assert chapter18["metadata"]["focus_character"] == keeper
    assert chapter17["metadata"]["relationship_target"] == "Lin Mo (Vessel)"
    assert chapter19["metadata"]["focus_character"] == keeper
    assert chapter19["metadata"]["relationship_target"] == "Lin Mo (Vessel)"
    assert chapter20["metadata"]["relationship_target"] == "Lin Mo (Vessel)"
    assert chapter17["metadata"]["relationship_status"] == "guardian of the empty shell"
    assert chapter19["metadata"]["relationship_status"] == "accepted voice of the public record"
    assert chapter20["metadata"]["relationship_status"] == "living voice of the confession line"
    assert not any(
        "vespera" in str(state.get("source", "")).lower()
        or "vespera" in str(state.get("target", "")).lower()
        for state in repaired_relationship_states[-8:]
    )
    assert "lin mo's voice is gone for good" in chapter17["summary"].lower()
    assert "part of the founding lie in the archive purge" in chapter18["summary"].lower()
    assert "keep charging the living afterward" in chapter18["summary"].lower()
    assert "living voice and not in a return" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "voice is gone for good" in chapter17_scene_text
    assert "part of the founding lie in the archive purge" in chapter18_scene_text
    assert "keep charging the living afterward" in chapter18_scene_text
    assert "living voice and not in a return" in chapter19_scene_text
    assert "thin red fee mark" in chapter19_scene_text
    assert "thin red fee mark" in chapter20_scene_text
    assert "voice is gone for good" in outline_chapter17["chapter_objective"].lower()
    assert "founding lie in the archive purge" in outline_chapter18["chapter_objective"].lower()
    assert "thin red fee mark under each new signature" in outline_chapter19["chapter_objective"].lower()
    assert "thin red fee mark as the immediate daily cost" in outline_chapter20["chapter_objective"].lower()
    assert "founding lie in the archive purge" in outline_chapter18["hook"].lower()
    assert (
        "living duty, not as a miracle return" in outline_chapter19["hook"].lower()
        or "survive one public dawn confession" in outline_chapter19["hook"].lower()
    )
    assert (
        "public cost in ordinary life" in outline_chapter20["hook"].lower()
        or "accept and pay its public cost" in outline_chapter20["hook"].lower()
    )
    for chapter_index in range(0, 16):
        outline_chapter = workspace["outline"]["chapters"][chapter_index]
        combined_outline_text = " ".join(
            [
                outline_chapter["summary"],
                outline_chapter["chapter_objective"],
                outline_chapter["hook"],
                outline_chapter["promise"],
                outline_chapter["promised_payoff"],
            ]
        ).lower()
        assert "the cast must pay a visible civic price" not in combined_outline_text
        assert "the oath exacts a visible civic price" not in combined_outline_text
        assert "make the first oath cost explicit" not in combined_outline_text
    assert outline_chapter18["primary_strand"] == "mystery"
    assert outline_chapter18["narrative_strand"] == "mystery"
    assert outline_chapter18["secondary_strand"] == "tension"
    assert "the silent council" not in late_arc_text
    assert "ledger anomalies" not in late_arc_text
    assert "memetic resonance" not in late_arc_text
    assert "dock-step count" not in late_arc_text
    assert "returned mind" not in late_arc_text
    assert "same tacky mark" not in late_arc_text
    assert "lin mo admits lin mo will not return" not in late_arc_text

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_six_live_longform_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilSixLongformProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Six Live Longform Story",
        genre="fantasy",
        author_id="author-april-six-live",
        premise="A debt archivist must rewrite the first oath, lose himself, and let survivors confess the city's hidden debt.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    active_characters = story_memory.get("active_characters", [])
    if isinstance(active_characters, list):
        for candidate in ("Archivist Sui", "Tanner Ro"):
            if candidate not in active_characters:
                active_characters.append(candidate)
        story_memory["active_characters"] = active_characters
    relationship_states = story_memory.get("relationship_states", [])
    if not isinstance(relationship_states, list):
        relationship_states = []
    for chapter_number in (17, 18, 19, 20):
        relationship_states.append(
            {
                "chapter_number": chapter_number,
                "source": "Lin Wei",
                "target": "Grand Scribe Kael",
                "status": "echo-guided burden",
            }
        )
    story_memory["relationship_states"] = relationship_states
    stored_story.metadata["story_memory"] = story_memory

    stored_story.chapters[13].summary = (
        "Grand Scribe Kael dies sealing the ward around the founding register so the others can flee with the archive key."
    )
    stored_story.chapters[12].summary = (
        "Lin Wei writes a lie into the First Oath and somehow keeps moving, but nobody explains why he does not become a stronger Hollow."
    )
    stored_story.chapters[15].summary = (
        "Lin Wei reaches the rite already half gone and survives as a shell without any clear mechanism tying the lie to the outcome."
    )
    stored_story.chapters[14].metadata["relationship_status"] = "strained trust"
    stored_story.chapters[16].summary = (
        "Lin Wei leads the surviving archivists after the sacrifice even though he is already described as a blank-slate shell."
    )
    stored_story.chapters[17].summary = (
        "Lin Wei walks the rebuilt archive with Kael, finds the missing page, and treats the shell like an active guide."
    )
    stored_story.chapters[18].summary = (
        "Lin Wei leads a private pre-dawn rehearsal, admits Lin Wei will not return, and keeps the frightened witnesses moving while spectral chains and the public confession blur together."
    )
    stored_story.chapters[19].summary = (
        "The Shell remains beside the Archive seal while Echo-Leader survives only as memory and Lin Wei speaks the true debt-name on his own behalf as the city confesses."
    )

    stored_story.chapters[12].scenes[0].update_content(
        "Lin Wei writes the lie into the oath and survives without anyone naming the mechanism."
    )
    stored_story.chapters[15].scenes[0].update_content(
        "The rite leaves Lin Wei standing as a shell, but the manuscript still treats him as an acting mind."
    )
    stored_story.chapters[18].scenes[0].update_content(
        "Lin Wei leads the rehearsal himself, Kael answers from the line, and the crowd scatters before the confession can separate from the failed attempt."
    )

    for chapter_number in (17, 18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Lin Wei"
        chapter.metadata["relationship_target"] = "Grand Scribe Kael"
        chapter.metadata["relationship_status"] = "echo-guided burden"

    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][12]["summary"] = stored_story.chapters[12].summary
    outline_payload["chapters"][12]["chapter_objective"] = (
        "Let Lin Wei write the lie and survive the scene without defining why the Hollow rule does not consume him."
    )
    outline_payload["chapters"][15]["summary"] = stored_story.chapters[15].summary
    outline_payload["chapters"][15]["chapter_objective"] = (
        "Move Lin Wei into shell-state without clarifying the mechanism."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][17]["summary"] = stored_story.chapters[17].summary
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Let the failed rehearsal, survivor hesitation, and public confession blur together."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["promised_payoff"] = (
        "Lin Wei returns as himself, speaks directly, and the shell stays beside the rite as a simple symbol."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "weak_serial_pull"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    assert revise_result.is_ok
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    repaired_relationship_states = workspace["story"]["metadata"]["story_memory"]["relationship_states"]
    chapter13 = workspace["story"]["chapters"][12]
    chapter15 = workspace["story"]["chapters"][14]
    chapter16 = workspace["story"]["chapters"][15]
    chapter17 = workspace["story"]["chapters"][16]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    keeper = chapter17["metadata"]["focus_character"]
    vessel_target = chapter17["metadata"]["relationship_target"]
    protagonist_root = vessel_target[: -len(" (Vessel)")] if vessel_target.endswith(" (Vessel)") else vessel_target
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter18 = workspace["outline"]["chapters"][17]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter18_scene_text = " ".join(scene["content"] for scene in chapter18["scenes"]).lower()
    chapter19_scene_text = " ".join(scene["content"] for scene in chapter19["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    late_arc_text = " ".join(
        [
            chapter17["summary"],
            chapter18["summary"],
            chapter19["summary"],
            chapter20["summary"],
            outline_chapter17["chapter_objective"],
            outline_chapter18["chapter_objective"],
            outline_chapter19["chapter_objective"],
            outline_chapter20["chapter_objective"],
            outline_chapter17["hook"],
            outline_chapter18["hook"],
            outline_chapter19["hook"],
            outline_chapter20["hook"],
        ]
    ).lower()

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "total self-erasure" in chapter13["summary"].lower()
    assert "no intact self for corruption to seize" in chapter13["summary"].lower()
    assert chapter15["metadata"]["relationship_status"] == "tactical reliance"
    assert "bypasses ordinary hollow conversion" in chapter16["summary"].lower()
    assert "the seal rips the pen from" in chapter16["summary"].lower()
    assert "forces him to his knees" in chapter16["summary"].lower()
    assert "loop of erased names" in chapter16["summary"].lower()
    assert "tears the ink-mask off the defeated tyrant's face" in chapter16["summary"].lower()
    assert "drops choking onto the stone" in chapter16["summary"].lower()
    assert "outline turns ash-transparent" in chapter16["summary"].lower()
    assert "cannot choose, speak, remember, or guide anyone" in chapter16["summary"].lower()
    assert keeper not in {protagonist_root, "Grand Scribe Kael"}
    assert "ghost" not in keeper.lower()
    assert "ledger" not in keeper.lower()
    assert chapter18["metadata"]["focus_character"] == keeper
    assert chapter19["metadata"]["focus_character"] == keeper
    assert chapter20["metadata"]["focus_character"] == keeper
    assert vessel_target.endswith(" (Vessel)")
    assert chapter18["metadata"]["relationship_target"] == vessel_target
    assert chapter19["metadata"]["relationship_target"] == vessel_target
    assert chapter20["metadata"]["relationship_target"] == vessel_target
    assert chapter17["metadata"]["relationship_status"] == "guardian of the empty shell"
    assert chapter18["metadata"]["relationship_status"] == "keeper of the vessel"
    assert chapter19["metadata"]["relationship_status"] == "accepted voice of the public record"
    assert chapter20["metadata"]["relationship_status"] == "living voice of the confession line"
    assert not any(
        "kael" in str(state.get("source", "")).lower()
        or "kael" in str(state.get("target", "")).lower()
        for state in repaired_relationship_states[-8:]
    )
    assert "lin wei's voice is gone for good" in chapter17["summary"].lower()
    assert "part of the founding lie in the archive purge" in chapter18["summary"].lower()
    assert "keep charging the living afterward" in chapter18["summary"].lower()
    assert "last instruction they remember hearing" in chapter19["summary"].lower()
    assert "living voice and not in a return" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "body never chooses, speaks, or remembers" in chapter20["summary"].lower()
    assert "paid dead" in chapter20["summary"].lower()
    if keeper == "Elara":
        assert "house title again" in " ".join([chapter16["summary"], chapter20["summary"]]).lower()
    assert "voice is gone for good" in chapter17_scene_text
    assert "part of the founding lie in the archive purge" in chapter18_scene_text
    assert "keep charging the living afterward" in chapter18_scene_text
    assert "last instruction they remember hearing" in chapter19_scene_text
    assert "living voice and not in a return" in chapter19_scene_text
    assert "thin red fee mark" in chapter19_scene_text
    assert "thin red fee mark" in chapter20_scene_text
    assert "voice is gone for good" in outline_chapter17["chapter_objective"].lower()
    assert "founding lie in the archive purge" in outline_chapter18["chapter_objective"].lower()
    assert "thin red fee mark under each new signature" in outline_chapter19["chapter_objective"].lower()
    assert "thin red fee mark as the immediate daily cost" in outline_chapter20["chapter_objective"].lower()
    assert "founding lie in the archive purge" in outline_chapter18["hook"].lower()
    assert (
        "living duty, not as a miracle return" in outline_chapter19["hook"].lower()
        or "survive one public dawn confession" in outline_chapter19["hook"].lower()
    )
    assert (
        "public cost in ordinary life" in outline_chapter20["hook"].lower()
        or "accept and pay its public cost" in outline_chapter20["hook"].lower()
    )
    assert outline_chapter18["primary_strand"] == "mystery"
    assert outline_chapter18["narrative_strand"] == "mystery"
    assert outline_chapter18["secondary_strand"] == "tension"
    assert "the silent council" not in late_arc_text
    assert "ledger anomalies" not in late_arc_text
    assert "memetic resonance" not in late_arc_text
    assert "returned mind" not in late_arc_text
    assert "same tacky mark" not in late_arc_text
    assert "harbor-black" not in late_arc_text
    assert "ink-light" not in late_arc_text

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_compacts_pass_thirty_five_live_summaries() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilTwelvePassThirtyFiveProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=AlternateBlueprintShapeProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Twelve Pass Thirty Five Story",
        genre="fantasy",
        author_id="author-april-twelve-pass-thirty-five",
        premise="A debt archivist must trade identity for a public confession that the city keeps paying after dawn.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"weak_serial_pull", "plot_confusion"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter18_scene_text = " ".join(scene["content"] for scene in chapter18["scenes"]).lower()
    chapter19_scene_text = " ".join(scene["content"] for scene in chapter19["scenes"]).lower()

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "voice is gone for good" in chapter17["summary"].lower()
    assert "knocks once against the bier board" in chapter17["summary"].lower()
    assert "part of the founding lie" in chapter18["summary"].lower()
    assert "any honest confession at dawn will keep charging the living afterward" in chapter18["summary"].lower()
    assert "thin red fee mark" in chapter19["summary"].lower()
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "small memory toll in public" in chapter20["summary"].lower()
    assert "voice is gone for good" in chapter17_scene_text
    assert "part of the founding lie" in chapter18_scene_text
    assert "any honest dawn confession will keep charging the living afterward" in chapter18_scene_text
    assert "thin red fee mark under each new signature" in chapter19_scene_text

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_two_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortyTwoProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Two Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-two",
        premise="A debt archivist loses the protagonist's mind in the oath rite and must carry the city's confession line into dawn.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[5].summary = (
        "Kaelen notices the ferry queue skipping one family slate again, but he does not connect it to the archive."
    )
    stored_story.chapters[16].summary = (
        "Kaelen keeps vigil beside the shell and mostly reflects on the loss without deciding how to carry the city forward."
    )
    stored_story.chapters[17].summary = (
        "Kaelen uncovers the missing page and reflects on the founding lie, but the reveal has no earlier civic echo."
    )
    stored_story.chapters[18].summary = (
        "The private rehearsal stays mostly verbal, with the line wavering but no physical threat forcing anyone to act."
    )
    stored_story.chapters[19].summary = (
        "At dawn the witnesses confess the city's oldest debt, and the new fee mark settles over the square."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][5]["summary"] = stored_story.chapters[5].summary
    outline_payload["chapters"][5]["chapter_objective"] = (
        "Notice the skipped family slate without tying it to the archive or the city's founding lie."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Let Kaelen remain mostly reflective after Lin Wei falls silent."
    )
    outline_payload["chapters"][17]["summary"] = stored_story.chapters[17].summary
    outline_payload["chapters"][17]["chapter_objective"] = (
        "Reveal the founding lie through the missing page without seeding the sibling connection earlier."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Keep the failed rehearsal reflective and verbal."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Let the square accept the new fee mark without one concrete citizen-level memory loss."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert "plot_confusion" in issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter6 = workspace["story"]["chapters"][5]
    chapter17 = workspace["story"]["chapters"][16]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    chapter6_scene_text = " ".join(scene["content"] for scene in chapter6["scenes"]).lower()
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter19_scene_text = " ".join(scene["content"] for scene in chapter19["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    outline_chapter6 = workspace["outline"]["chapters"][5]
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "same erased column pattern" in chapter6["summary"].lower()
    assert "same erased column pattern" in chapter6_scene_text
    assert "city's eyes and ears" in chapter17["summary"].lower()
    assert "city's eyes and ears" in chapter17_scene_text
    assert "debt ghost claws at the archive seal" in chapter19["summary"].lower()
    assert "debt ghost claws at the archive seal" in chapter19_scene_text
    assert "thin red fee mark" in chapter20["summary"].lower()
    assert "cannot find his name for one whole breath" in chapter20["summary"].lower()
    assert "cannot find his name for one whole breath" in chapter20_scene_text
    assert "same erased column pattern" in outline_chapter6["summary"].lower()
    assert "erased column pattern" in outline_chapter6["chapter_objective"].lower()
    assert "city's eyes and ears" in outline_chapter17["chapter_objective"].lower()
    assert "debt ghost claws at the archive seal" in outline_chapter19["summary"].lower()
    assert "one citizen lose a familiar name in real time" in outline_chapter20["chapter_objective"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_three_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortyThreeProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Three Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-three",
        premise="A debt archivist must carry the city's confession line after Lin Wei becomes a silent shell.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[16].summary = (
        "Kaelen stands beside the shell and continues by duty alone, with no vivid memory of Lin Wei shaping the moment."
    )
    stored_story.chapters[17].summary = (
        "The missing page appears, but Elara's place in the scene remains implied rather than concrete."
    )
    stored_story.chapters[18].summary = (
        "The private rehearsal fails, yet the manuscript never states what the line did wrong or how dawn will correct it."
    )
    stored_story.chapters[19].summary = (
        "At dawn the city accepts the new fee mark, but the success reads as abstract rather than mechanically earned."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Keep Kaelen reflective without one sensory memory that concretizes Lin Wei's absence."
    )
    outline_payload["chapters"][17]["summary"] = stored_story.chapters[17].summary
    outline_payload["chapters"][17]["chapter_objective"] = (
        "Leave Elara's reconciliation implied."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Let the rehearsal fail without naming the rail-order mistake."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Land the fee mark publicly without stating why the final ordering keeps it from turning fatal."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "relationship_progression_stall"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter18_scene_text = " ".join(scene["content"] for scene in chapter18["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter18 = workspace["outline"]["chapters"][17]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "scorched fennel-oil smell" in chapter17["summary"].lower()
    assert "scorched fennel-oil smell" in chapter17_scene_text
    assert "lays two fingers against the shell's burned knuckles" in chapter18["summary"].lower()
    assert "lays two fingers against the shell's burned knuckles" in chapter18_scene_text
    assert "the widow's thumb seals red to the iron" in chapter19["summary"].lower()
    assert "one low amber pulse" in chapter19["summary"].lower()
    assert "one-breath public blank" in chapter20["summary"].lower()
    assert "one-breath public blank" in chapter20_scene_text
    assert "city's eyes and ears" in outline_chapter17["chapter_objective"].lower()
    assert "concrete act of acceptance at the shell" in outline_chapter18["chapter_objective"].lower()
    assert "public registry before the family rail is warm" in outline_chapter19["chapter_objective"].lower()
    assert "one citizen lose a familiar name in real time" in outline_chapter20["chapter_objective"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_five_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortyFiveProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Five Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-five",
        premise="A debt archivist must carry the city's confession line after Lin Wei becomes a silent shell.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[11].summary = (
        "The evacuation line survives the ashfall, but Elara remains backgrounded and never visibly earns the witness line's trust."
    )
    stored_story.chapters[13].summary = (
        "The corridor seals buckle, yet no one besides the core pair takes public responsibility for the count."
    )
    stored_story.chapters[16].summary = (
        "The memorial watch begins after the climax, but Vane's inner realization is skipped over as if his collapse were already complete."
    )
    stored_story.chapters[19].summary = (
        "The dawn confession succeeds, but the red fee mark and shell stay conceptual rather than physically felt in the square."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][11]["summary"] = stored_story.chapters[11].summary
    outline_payload["chapters"][11]["chapter_objective"] = (
        "Keep Elara useful but not visibly authoritative during the evacuation count."
    )
    outline_payload["chapters"][13]["summary"] = stored_story.chapters[13].summary
    outline_payload["chapters"][13]["chapter_objective"] = (
        "Let the corridor crisis pass without Elara leading the witness line."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Move into memorial duty without showing Vane hear the erased names answer him back."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Land the new fee mark without tying it to the registry knock or a concrete smell on one citizen."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"ooc_behavior", "plot_confusion"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter12 = workspace["story"]["chapters"][11]
    chapter14 = workspace["story"]["chapters"][13]
    chapter17 = workspace["story"]["chapters"][16]
    chapter20 = workspace["story"]["chapters"][19]
    chapter12_scene_text = " ".join(scene["content"] for scene in chapter12["scenes"]).lower()
    chapter14_scene_text = " ".join(scene["content"] for scene in chapter14["scenes"]).lower()
    chapter17_scene_text = " ".join(scene["content"] for scene in chapter17["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    outline_chapter12 = workspace["outline"]["chapters"][11]
    outline_chapter14 = workspace["outline"]["chapters"][13]
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "keeps the evacuation roll moving under falling ash" in chapter12["summary"].lower()
    assert "takes the soot-smeared witness roll from a panicking clerk" in chapter12_scene_text
    assert "drags two apprentices behind the ledger barricade" in chapter14["summary"].lower()
    assert "drags two apprentices behind the ledger barricade" in chapter14_scene_text
    assert "duty now falls on" in chapter17["summary"].lower()
    assert "they now have to be the city's eyes and ears" not in chapter17["summary"].lower()
    assert "hears the loop of erased names answer in the same cadence" in chapter17_scene_text
    assert "smells scorched fennel oil on her own sleeve" in chapter20["summary"].lower()
    assert "one knock cracks off the public registry rail" in chapter20["summary"].lower()
    assert "smells scorched fennel oil on her own sleeve" in chapter20_scene_text
    assert "one knock cracks off the public registry rail" in chapter20_scene_text
    assert "earn visible trust" in outline_chapter12["chapter_objective"].lower()
    assert "drags two apprentices behind the ledger barricade" in outline_chapter14["summary"].lower()
    assert "city's eyes and ears now depend on" in outline_chapter17["chapter_objective"].lower()
    assert "one knock cracks off the public registry rail" in outline_chapter20["chapter_objective"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_six_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortySixProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Six Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-six",
        premise="A debt archivist must carry the city's confession line after Lin Mo becomes a silent shell.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[15].summary = (
        "Vane hears the loop of erased names answer in his own cadence and realizes the city he built was always stolen absence made civic."
    )
    stored_story.chapters[16].summary = (
        "With Lin Mo's mind gone, Lin Mo understands they now have to be the city's eyes and ears, and the memorial watch repeats Vane's realization almost word for word."
    )
    stored_story.chapters[18].summary = (
        "The private rehearsal fails, but the chapter never states whether the shell or the witnesses are actually attempting the confession."
    )
    stored_story.chapters[19].summary = (
        "The restored name returns to the living, but the chapter still leaves the sister's final spiritual fate emotionally open."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][15]["summary"] = stored_story.chapters[15].summary
    outline_payload["chapters"][15]["chapter_objective"] = (
        "Show Vane break when the erased names answer him back."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Keep the aftermath focused on Lin Mo understanding they now have to be the city's eyes and ears."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Let the rehearsal stay vague about whether the shell itself is participating."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Leave the sister's fate emotionally open instead of confirming whether her spirit is at rest."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert "plot_confusion" in issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_failures))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter16 = workspace["story"]["chapters"][15]
    chapter17 = workspace["story"]["chapters"][16]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    chapter19_scene_text = " ".join(scene["content"] for scene in chapter19["scenes"]).lower()
    chapter20_scene_text = " ".join(scene["content"] for scene in chapter20["scenes"]).lower()
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert chapter16["summary"].lower().count("hears the loop of erased names answer in his own cadence") == 1
    assert "hears the loop of erased names answer in his own cadence" not in chapter17["summary"].lower()
    assert "they now have to be the city's eyes and ears" not in chapter17["summary"].lower()
    assert "duty now falls on" in chapter17["summary"].lower()
    assert "witness prop only" in chapter19["summary"].lower()
    assert "witness prop there" in chapter19_scene_text
    assert "lost spirit is finally at rest beyond recall" in chapter20["summary"].lower()
    assert "lost spirit is finally at rest beyond recall" in chapter20_scene_text
    assert "they now have to be the city's eyes and ears" not in outline_chapter17["summary"].lower()
    assert "witness prop" in outline_chapter19["chapter_objective"].lower()
    assert "lost spirit is finally at rest beyond recall" in outline_chapter20["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_seven_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortySevenProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Seven Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-seven",
        premise="A debt archivist must carry the city's confession line after Lin Yuan becomes a silent shell.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[16].summary = (
        "The memorial watch begins, but Elara accepts duty immediately without a tangible refusal beat at the shell."
    )
    stored_story.chapters[17].summary = (
        "The missing-sister page surfaces, but the text never explains why the purge logic failed to erase it."
    )
    stored_story.chapters[18].summary = (
        "The rehearsal fails, but the chapter still leaves the corrective rail order mostly implied rather than explicitly named."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Move Elara into leadership without a tactile hesitation beat."
    )
    outline_payload["chapters"][17]["summary"] = stored_story.chapters[17].summary
    outline_payload["chapters"][17]["chapter_objective"] = (
        "Reveal the page without explaining why it stayed outside the purge."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Let the rehearsal fail without one explicit sentence naming why the old rail order failed."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"weak_serial_pull", "world_logic_soft_conflict", "plot_confusion"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter18 = workspace["outline"]["chapters"][17]
    outline_chapter19 = workspace["outline"]["chapters"][18]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "memory-threaded" in chapter17["summary"].lower()
    assert "voice" in chapter17["summary"].lower()
    assert "dry-wood click" in chapter17["summary"].lower() or "shutters" in chapter17["summary"].lower()
    assert "the debt-name stayed unwritten and outside the purge logic" in chapter18["summary"].lower()
    assert "the widow's thumb seals red to the iron" in chapter19["summary"].lower()
    assert "one low amber pulse" in chapter19["summary"].lower()
    assert "memory-threaded" in outline_chapter17["summary"].lower()
    assert "voice" in outline_chapter17["summary"].lower()
    assert "outside the purge logic" in outline_chapter18["summary"].lower()
    assert "one low amber pulse" in outline_chapter19["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_eight_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortyEightProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Eight Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-eight",
        premise="A debt archivist must carry the city's confession line after Lin Yuan becomes a silent shell.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[15].summary = (
        "Vane falls, but the scene still describes his defeat more as concept than visible magical disintegration."
    )
    stored_story.chapters[18].summary = (
        "The rehearsal fails, but Elara never explicitly wins the strategic argument or states why the rail order matters."
    )
    stored_story.chapters[19].summary = (
        "The city absorbs the new cost, but the ending still spreads attention across too many consequences at once."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][15]["summary"] = stored_story.chapters[15].summary
    outline_payload["chapters"][15]["chapter_objective"] = (
        "Keep Vane's collapse concept-heavy instead of visibly physical."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Let Elara inherit the correct plan without arguing for it."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Resolve the ending without foregrounding a single family-sized shock."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "ooc_behavior", "weak_serial_pull"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter16 = workspace["story"]["chapters"][15]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "his right hand ashes away from the nails inward" in chapter16["summary"].lower()
    assert "one iron crack" in chapter19["summary"].lower()
    assert "one low amber pulse" in chapter19["summary"].lower()
    assert "one full breath again" in chapter19["summary"].lower()
    assert "single family-sized shock" in chapter20["summary"].lower()
    assert "one iron crack" in outline_chapter19["summary"].lower()
    assert "single family-sized shock" in outline_chapter20["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Superseded by the current live gate contract.")
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_thirteen_pass_forty_nine_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilThirteenPassFortyNineProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Thirteen Pass Forty Nine Story",
        genre="fantasy",
        author_id="author-april-thirteen-pass-forty-nine",
        premise="A debt archivist must carry the city's confession line after a one-way sacrifice leaves the witness line holding the cost.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[15].summary = (
        "The rite, the tyrant's defeat, and the protagonist's transformation blur together in one passive summary that never shows a conscious final choice."
    )
    stored_story.chapters[16].summary = (
        "The memorial watch treats the silence as an unexplained loss instead of a price the protagonist chose in front of everyone."
    )
    stored_story.chapters[18].summary = (
        "The failed rehearsal gets explained after the fact, but the wrong rail order never visibly harms a witness before the correction."
    )
    stored_story.chapters[19].summary = (
        "The public confession lands without anyone whispering the missing sister's name into the shell as a private act of love."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][15]["summary"] = stored_story.chapters[15].summary
    outline_payload["chapters"][15]["chapter_objective"] = (
        "Keep the final sacrifice passive and overloaded."
    )
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Treat the silence as theft instead of a chosen cost."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Explain the wrong rail order without showing immediate harm."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Resolve the missing sister line without a private whisper at the shell."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "weak_serial_pull", "ooc_behavior"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter16 = workspace["story"]["chapters"][15]
    chapter17 = workspace["story"]["chapters"][16]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    outline_chapter16 = workspace["outline"]["chapters"][15]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "guides that hand onto the rail" in chapter16["summary"].lower()
    assert "choose the rewrite over returning to the body" in chapter16["summary"].lower()
    assert "choose that price" in chapter17["summary"].lower()
    assert "the widow's thumb seals red to the iron" in chapter19["summary"].lower()
    assert "one full breath again" in chapter19["summary"].lower()
    assert "into the burned ear" in chapter20["summary"].lower()
    assert "lets the name go with no answer coming back" in chapter20["summary"].lower()
    assert "guides that hand onto the rail" in outline_chapter16["summary"].lower()
    assert "the widow's thumb seals red to the iron" in outline_chapter19["summary"].lower()
    assert "into the burned ear" in outline_chapter20["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_fourteen_pass_fifty_eight_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilFourteenPassFiftyEightProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Fourteen Pass Fifty-Eight Story",
        genre="fantasy",
        author_id="author-april-fourteen-pass-fifty-eight",
        premise="A debt archivist must carry the city's confession line after a one-way sacrifice leaves the living to pay memory in public.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[17].summary = (
        "The missing-sister apparition appears, but the reveal still lands as explanation instead of showing the ledger physically changing."
    )
    stored_story.chapters[18].summary = (
        "The failed rehearsal breaks the room, but nobody states what the survivors learned from the mistake before dawn."
    )
    stored_story.chapters[19].summary = (
        "The dawn confession lands, but the shell remains only an abstract monument instead of offering one final tactile anchor."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][17]["summary"] = stored_story.chapters[17].summary
    outline_payload["chapters"][17]["chapter_objective"] = (
        "Keep the reveal explanatory and avoid showing the ledger physically answering the name."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Leave the failed rehearsal as pain without teaching the crowd the correct dawn sequence."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Resolve the ending without a tangible touch-based proof lingering in the shell."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter18 = workspace["story"]["chapters"][17]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    outline_chapter18 = workspace["outline"]["chapters"][17]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]
    late_arc_text = " ".join(
        [
            chapter18["summary"].lower(),
            chapter19["summary"].lower(),
            chapter20["summary"].lower(),
            outline_chapter18["summary"].lower(),
            outline_chapter19["summary"].lower(),
            outline_chapter20["summary"].lower(),
        ]
    )

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "black ink bleeds back into that blank line" in chapter18["summary"].lower()
    assert "gets breath only after the family line answers" in chapter19["summary"].lower()
    assert "watches the public rail stay dead until that first beat holds" in chapter19["summary"].lower()
    assert "youngest clerk lays two fingers on the shell's scorched wrist" in chapter20["summary"].lower()
    assert "ember-warm pulse" in chapter20["summary"].lower()
    assert "daily memory tax" in chapter20["summary"].lower()
    assert "the mark fades from sight a beat later" in chapter20["summary"].lower()
    assert "does not resurrect the body" in chapter20["summary"].lower()
    assert "the apparition makes it plain" not in late_arc_text
    assert "black ink bleeds back into that blank line" in outline_chapter18["summary"].lower()
    assert "gets breath only after the family line answers" in outline_chapter19["summary"].lower()
    assert "watches the public rail stay dead until that first beat holds" in outline_chapter19["summary"].lower()
    assert "ember-warm pulse" in outline_chapter20["summary"].lower()
    assert "the mark fades from sight a beat later" in outline_chapter20["summary"].lower()

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Replaced by provider-backed judge contract tests and generic terminal-arc fixtures.")
async def test_revise_story_closes_april_fourteen_pass_sixty_live_warnings() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    review_provider = LiveAprilFourteenPassSixtyProvider()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=review_provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="April Fourteen Pass Sixty Story",
        genre="fantasy",
        author_id="author-april-fourteen-pass-sixty",
        premise="A debt archivist leaves the living to carry one public memory toll after a one-way sacrifice rewrites the first oath.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[16].summary = (
        "Yuna takes command too cleanly after the shell goes silent and never physically breaks before leading the line."
    )
    stored_story.chapters[18].summary = (
        "The rehearsal previews danger, but the fading practice mark never explains why the public tax must wait for dawn."
    )
    stored_story.chapters[19].summary = (
        "The dawn confession resolves private grief and public order in one blur, so the fish seller's fee still lands too abruptly."
    )
    workflow_payload = stored_story.metadata["workflow"]
    outline_payload = workflow_payload["outline"]
    outline_payload["chapters"][16]["summary"] = stored_story.chapters[16].summary
    outline_payload["chapters"][16]["chapter_objective"] = (
        "Let Yuna sound resolved without a visible physical collapse."
    )
    outline_payload["chapters"][18]["summary"] = stored_story.chapters[18].summary
    outline_payload["chapters"][18]["chapter_objective"] = (
        "Preview the fee without explaining that the room cannot ratify the tax alone."
    )
    outline_payload["chapters"][19]["summary"] = stored_story.chapters[19].summary
    outline_payload["chapters"][19]["chapter_objective"] = (
        "Blend the family closure and public rail into one dense summary block."
    )
    await repository.save(stored_story)

    review_before = await service.review_story(story_id)
    assert review_before.is_ok
    issue_codes_before = {issue["code"] for issue in review_before.value["report"]["issues"]}
    assert {"plot_confusion", "world_logic_soft_conflict", "weak_serial_pull"} <= issue_codes_before

    revise_result = await service.revise_story(story_id)
    if not revise_result.is_ok:
        raise AssertionError(str(review_provider.last_missing_fragments))
    assert revise_result.value["report"]["publish_gate_passed"] is True

    workspace = revise_result.value["workspace"]
    chapter17 = workspace["story"]["chapters"][16]
    chapter19 = workspace["story"]["chapters"][18]
    chapter20 = workspace["story"]["chapters"][19]
    outline_chapter17 = workspace["outline"]["chapters"][16]
    outline_chapter19 = workspace["outline"]["chapters"][18]
    outline_chapter20 = workspace["outline"]["chapters"][19]
    late_arc_text = " ".join(
        [
            chapter17["summary"].lower(),
            chapter19["summary"].lower(),
            chapter20["summary"].lower(),
            outline_chapter17["summary"].lower(),
            outline_chapter19["summary"].lower(),
            outline_chapter20["summary"].lower(),
        ]
    )

    assert workspace["evidence_summary"]["warning_count"] == 0
    assert "folding to one knee" in late_arc_text
    assert "the room can rehearse the cost but cannot ratify it alone" in late_arc_text
    assert "that private beat closes the family wound first" in late_arc_text
    assert "the same thin red fee mark that flashed and faded on the practice ledger" in late_arc_text
    assert "daily memory tax" in late_arc_text

    review_after = await service.review_story(story_id)
    assert review_after.is_ok
    assert not review_after.value["report"]["issues"]
    assert review_after.value["report"]["publish_gate_passed"] is True
    assert review_provider.review_calls >= 2


@pytest.mark.asyncio
async def test_late_arc_keeper_pool_excludes_titled_antagonist_variants() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=AlternateBlueprintShapeProvider(),
        review_generation_provider=DeterministicTextGenerationProvider(),
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Late Arc Keeper Alias Guard",
        genre="fantasy",
        author_id="author-keeper-alias-guard",
        premise="A debt archivist must recover a city's missing oath before the archive collapses.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    active_characters = story_memory.get("active_characters", [])
    if not isinstance(active_characters, list):
        active_characters = []
    for candidate in ("Grand Chancellor Vane", "Echo", "Madam Qiao"):
        if candidate not in active_characters:
            active_characters.append(candidate)
    story_memory["active_characters"] = active_characters

    relationship_states = story_memory.get("relationship_states", [])
    if not isinstance(relationship_states, list):
        relationship_states = []
    for chapter_number in (17, 18, 19, 20):
        relationship_states.append(
            {
                "chapter_number": chapter_number,
                "source": "Grand Chancellor Vane",
                "target": "Lin Yuan",
                "status": "forced memorial custody",
            }
        )
    story_memory["relationship_states"] = relationship_states
    stored_story.metadata["story_memory"] = story_memory

    for chapter_number in (17, 18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Grand Chancellor Vane"
        chapter.metadata["relationship_target"] = "Grand Chancellor Vane"
        chapter.metadata["relationship_status"] = "forced memorial custody"
        chapter.summary = (
            f"Grand Chancellor Vane keeps the shell under guard in chapter {chapter_number} while the city waits for dawn."
        )

    workflow_payload = stored_story.metadata.get("workflow", {})
    assert isinstance(workflow_payload, dict)
    outline_payload = workflow_payload.get("outline", {})
    assert isinstance(outline_payload, dict)
    outline_chapters = outline_payload.get("chapters", [])
    assert isinstance(outline_chapters, list)
    for chapter_number in (17, 18, 19, 20):
        outline_chapter = outline_chapters[chapter_number - 1]
        outline_chapter["summary"] = (
            f"Grand Chancellor Vane becomes the visible keeper of the shell in chapter {chapter_number}."
        )
        outline_chapter["chapter_objective"] = (
            "Keep Grand Chancellor Vane in charge of the late-arc witness line."
        )
        outline_chapter["promise"] = "The titled antagonist still tries to dominate the memorial line."
        outline_chapter["promised_payoff"] = (
            "Grand Chancellor Vane carries the confession into the dawn square."
        )
    workflow_payload["outline"] = outline_payload
    stored_story.metadata["workflow"] = workflow_payload
    await repository.save(stored_story)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)
    protagonist, allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    keeper_pool = service._revision_service._resolve_late_arc_keeper_pool(
        ctx_or_error,
        protagonist,
        allies,
    )

    assert keeper_pool
    assert keeper_pool[0] not in {"Lin Yuan", "High Scribe Vane", "Grand Chancellor Vane", "Vane"}
    assert keeper_pool[0] in {"Echo", "Madam Qiao"}


@pytest.mark.asyncio
async def test_late_arc_witness_selection_excludes_symbolic_vessel_labels() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=AlternateBlueprintShapeProvider(),
        review_generation_provider=DeterministicTextGenerationProvider(),
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Late Arc Witness Symbol Guard",
        genre="fantasy",
        author_id="author-witness-symbol-guard",
        premise="A debt archivist must keep the witness line human after the vessel remains behind.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    active_characters = story_memory.get("active_characters", [])
    if not isinstance(active_characters, list):
        active_characters = []
    for candidate in ("Echo", "Madam Qiao", "Lin Yuan (Vessel)"):
        if candidate not in active_characters:
            active_characters.append(candidate)
    story_memory["active_characters"] = active_characters

    relationship_states = story_memory.get("relationship_states", [])
    if not isinstance(relationship_states, list):
        relationship_states = []
    for chapter_number in (17, 18, 19, 20):
        relationship_states.extend(
            [
                {
                    "chapter_number": chapter_number,
                    "source": "Echo",
                    "target": "Lin Yuan (Vessel)",
                    "status": "shared grief witness line",
                },
                {
                    "chapter_number": chapter_number,
                    "source": "Madam Qiao",
                    "target": "Lin Yuan (Vessel)",
                    "status": "tactical reliance holding line",
                },
                {
                    "chapter_number": chapter_number,
                    "source": "Lin Yuan (Vessel)",
                    "target": "Madam Qiao",
                    "status": "symbolic memorial custody",
                },
            ]
        )
    story_memory["relationship_states"] = relationship_states
    stored_story.metadata["story_memory"] = story_memory

    for chapter_number in (17, 18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Lin Yuan (Vessel)"
        chapter.metadata["relationship_target"] = "Madam Qiao"
        chapter.metadata["relationship_status"] = "shared grief witness line"

    await repository.save(stored_story)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    protagonist, allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    keeper_pool = service._revision_service._resolve_late_arc_keeper_pool(
        ctx_or_error,
        protagonist,
        allies,
    )
    primary_keeper = keeper_pool[0]
    supporting_witness = service._revision_service._resolve_late_arc_supporting_witness(
        ctx_or_error,
        protagonist,
        primary_keeper,
    )
    public_witness = service._revision_service._resolve_late_arc_public_witness(
        ctx_or_error,
        protagonist,
        primary_keeper,
        supporting_witness,
    )

    assert supporting_witness in {"Echo", "Madam Qiao"}
    assert public_witness in {"Echo", "Madam Qiao"}
    assert supporting_witness != protagonist
    assert public_witness != protagonist
    assert "vessel" not in supporting_witness.lower()
    assert "vessel" not in public_witness.lower()
    assert "shell" not in supporting_witness.lower()
    assert "shell" not in public_witness.lower()


@pytest.mark.asyncio
async def test_terminal_arc_revision_plan_uses_generic_role_slots() -> None:
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
        review_generation_provider=provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Generic Terminal Arc Revision",
        genre="fantasy",
        author_id="author-generic-terminal-revision",
        premise="A witness-keeper must carry a public confession after the protagonist gives up agency to stop a citywide unraveling.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    issues = [
        StoryReviewIssue(
            code="plot_confusion",
            severity="warning",
            message="The terminal arc muddies who acts and who is being acted on.",
            location="terminal-arc",
            suggestion="Separate the vessel from the living keeper line.",
            details={"judge_dimension": "actor_attribution"},
        ),
        StoryReviewIssue(
            code="world_logic_soft_conflict",
            severity="warning",
            message="The public cost still reads as abstract and the vessel acts too intentionally.",
            location="Chapter 19-20",
            suggestion="Keep the vessel passive and ground the public consequence.",
            details={"judge_dimension": "vessel_agency"},
        ),
    ]

    plan = await service._revision_service._plan_terminal_arc_revision(
        ctx_or_error,
        issues,
        issue_context="terminal-arc vessel public cost fee mark closure",
    )

    protagonist, _allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    assert sorted(plan) == [16, 17, 18, 19, 20]
    for chapter_number, chapter_plan in plan.items():
        summary = chapter_plan["summary"]
        assert "Elara" not in summary
        assert "Lin Yuan" not in summary
        assert "Old Man Gao" not in summary
        if chapter_number >= 17:
            assert chapter_plan["focus_character"] != protagonist
            assert chapter_plan["relationship_target"]


@pytest.mark.asyncio
async def test_repair_story_applies_terminal_arc_plan_without_local_chapter_issue_locations() -> None:
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
        review_generation_provider=provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Terminal Arc Repair Coverage",
        genre="fantasy",
        author_id="author-terminal-arc-repair-coverage",
        premise="A sacrifice at the city gate leaves the living to carry the public debt in daylight.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    chapter_16_before = ctx_or_error.story.chapters[15].summary
    chapter_20_before = ctx_or_error.story.chapters[19].summary
    protagonist, _allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    issues = [
        StoryReviewIssue(
            code="plot_confusion",
            severity="warning",
            message="The terminal arc loses track of who acts and who only remains as proof.",
            location="terminal-arc",
            suggestion="Repair the whole late arc through keeper, witness, and vessel roles.",
            details={"judge_dimension": "actor_attribution"},
        ),
        StoryReviewIssue(
            code="relationship_progression_stall",
            severity="warning",
            message="The ending no longer reflects the surviving relationship line.",
            location="terminal-arc",
            suggestion="Carry the living relationship line into closure.",
            details={"judge_dimension": "keeper_motivation"},
        ),
    ]

    repair_notes = await service._revision_service._repair_story(ctx_or_error, issues)

    assert any("chapter 16" in note for note in repair_notes)
    assert any("chapter 20" in note for note in repair_notes)
    assert ctx_or_error.story.chapters[15].summary != chapter_16_before
    assert ctx_or_error.story.chapters[19].summary != chapter_20_before
    assert ctx_or_error.story.chapters[16].metadata["focus_character"] != protagonist
    assert ctx_or_error.story.chapters[19].metadata["focus_character"] != protagonist


@pytest.mark.asyncio
async def test_terminal_arc_continuity_anchor_prefers_live_ally_over_late_role_drift() -> None:
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
        review_generation_provider=provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Terminal Arc Continuity Anchor",
        genre="fantasy",
        author_id="author-terminal-arc-continuity-anchor",
        premise="A witness line must stay coherent after the protagonist becomes a silent proof of the price.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    protagonist, allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    assert len(allies) >= 2
    continuity_anchor = allies[0]
    drift_candidate = allies[1]

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    for chapter_number in (15, 16, 17):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = continuity_anchor
        chapter.metadata["relationship_target"] = protagonist
        chapter.metadata["relationship_status"] = "shared grief tactical reliance"
        chapter.summary = (
            f"{continuity_anchor} stays beside {protagonist} as the cost sharpens into a public debt."
        )
    for chapter_number in (18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = drift_candidate
        chapter.metadata["relationship_target"] = protagonist
        chapter.metadata["relationship_status"] = "public witness line under pressure"

    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    story_memory["relationship_states"] = [
        {
            "chapter_number": 15,
            "source": continuity_anchor,
            "target": protagonist,
            "status": "shared grief tactical reliance",
        },
        {
            "chapter_number": 16,
            "source": continuity_anchor,
            "target": protagonist,
            "status": "shared grief tactical reliance",
        },
        {
            "chapter_number": 17,
            "source": continuity_anchor,
            "target": protagonist,
            "status": "shared grief tactical reliance",
        },
        {
            "chapter_number": 18,
            "source": drift_candidate,
            "target": protagonist,
            "status": "public witness line under pressure",
        },
        {
            "chapter_number": 19,
            "source": drift_candidate,
            "target": protagonist,
            "status": "public witness line under pressure",
        },
    ]
    active_characters = story_memory.get("active_characters", [])
    if not isinstance(active_characters, list):
        active_characters = []
    for candidate in (continuity_anchor, drift_candidate):
        if candidate not in active_characters:
            active_characters.append(candidate)
    story_memory["active_characters"] = active_characters
    stored_story.metadata["story_memory"] = story_memory
    await repository.save(stored_story)

    repaired_ctx_or_error = await service._load_context(story_id)
    assert not isinstance(repaired_ctx_or_error, Failure)

    resolved_anchor = service._revision_service._resolve_terminal_arc_continuity_anchor(
        repaired_ctx_or_error,
        protagonist,
        allies,
    )
    keeper_pool = service._revision_service._resolve_late_arc_keeper_pool(
        repaired_ctx_or_error,
        protagonist,
        allies,
    )

    assert resolved_anchor == continuity_anchor
    assert keeper_pool[0] == continuity_anchor


def test_normalize_relationship_target_preserves_non_protagonist_vessel_labels() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    normalized = revision_service._normalize_relationship_target(
        focus_character="Lin Yuan",
        relationship_target="Elara (Vessel)",
        protagonist="Lin Yuan",
        chapter_allies=["Elara"],
        surviving_allies=["Elara"],
        cast_names={"Lin Yuan", "Elara"},
        departed_characters={},
        chapter_number=18,
        target_chapters=20,
        prefer_vessel_target=False,
    )

    assert normalized == "Elara (Vessel)"


def test_extract_terminal_arc_rewrite_plan_rejects_unknown_focus_labels() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())
    result = TextGenerationResult(
        step="terminal_arc_revision",
        provider="mock",
        model="deterministic-text-generator-v1",
        raw_text="",
        content={
            "chapters": [
                {
                    "chapter_number": 17,
                    "phase": "aftermath",
                    "summary": "A living keeper steadies the line while the vessel remains passive.",
                    "objective": "Keep borrowed motion separate from inner consciousness.",
                    "hook": "The first proof of the rule lands in public.",
                    "focus_character": "Young Witness",
                    "relationship_target": "Elara (Vessel)",
                    "relationship_status": "keeper and vessel learning the new public cost",
                }
            ]
        },
    )

    plan = revision_service._extract_terminal_arc_rewrite_plan(
        result,
        phases={
            "sacrifice": 16,
            "aftermath": 17,
            "rule_revelation": 18,
            "public_reckoning": 19,
            "closure": 20,
        },
        protagonist="Lin Yuan",
        primary_keeper="Madame Qian",
        supporting_witness="Echo",
        public_witness="Dock Porter",
        vessel_label="Elara (Vessel)",
        continuity_anchor="Madame Qian",
        confirmation_trigger="the confirming knock from the seal",
        cast_names={"Lin Yuan", "Elara", "Madame Qian", "Echo", "Dock Porter"},
    )

    assert plan[17]["focus_character"] == "Madame Qian"
    assert plan[17]["relationship_target"] == "Elara (Vessel)"


def test_dedupe_terminal_identity_seal_sentences_keeps_single_name_action() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    cleaned = revision_service._dedupe_terminal_identity_seal_sentences(
        "The protagonist speaks the old name to seal the debt. "
        "The protagonist speaks the same name aloud again while the witness line listens. "
        "The watchers feel the contract lock into place."
    )

    sentences = [sentence.strip() for sentence in cleaned.split(".") if sentence.strip()]
    identity_seal_sentences = [
        sentence
        for sentence in sentences
        if "name" in sentence.lower() and any(token in sentence.lower() for token in ("speak", "said", "voice"))
    ]
    assert len(identity_seal_sentences) == 1
    assert "watchers feel the contract" in cleaned.lower()


def test_default_terminal_arc_phase_plan_marks_break_and_silence_generically() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    rule_revelation = revision_service._default_terminal_arc_phase_plan(
        phase="rule_revelation",
        chapter_number=18,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="Milo",
        public_witness="Captain Vale",
        vessel_label="Ari (Vessel)",
        continuity_anchor="Captain Vale",
        confirmation_trigger="the confirming knock from the old rule",
    )
    sacrifice = revision_service._default_terminal_arc_phase_plan(
        phase="sacrifice",
        chapter_number=16,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="Milo",
        public_witness="Captain Vale",
        vessel_label="Ari (Vessel)",
        continuity_anchor="Captain Vale",
        confirmation_trigger="the confirming knock from the old rule",
    )
    aftermath = revision_service._default_terminal_arc_phase_plan(
        phase="aftermath",
        chapter_number=17,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="Milo",
        public_witness="Captain Vale",
        vessel_label="Ari (Vessel)",
        continuity_anchor="Captain Vale",
        confirmation_trigger="the confirming knock from the old rule",
    )
    public_reckoning = revision_service._default_terminal_arc_phase_plan(
        phase="public_reckoning",
        chapter_number=19,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="Milo",
        public_witness="Captain Vale",
        vessel_label="Ari (Vessel)",
        continuity_anchor="Captain Vale",
        confirmation_trigger="the confirming knock from the old rule",
    )
    closure = revision_service._default_terminal_arc_phase_plan(
        phase="closure",
        chapter_number=20,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="Milo",
        public_witness="Captain Vale",
        vessel_label="Ari (Vessel)",
        continuity_anchor="Captain Vale",
        confirmation_trigger="the confirming knock from the old rule",
    )

    rule_summary = rule_revelation["summary"].lower()
    public_summary = public_reckoning["summary"].lower()
    rule_objective = rule_revelation["objective"].lower()
    public_objective = public_reckoning["objective"].lower()
    closure_summary = closure["summary"].lower()
    sacrifice_summary = sacrifice["summary"].lower()
    sacrifice_objective = sacrifice["objective"].lower()
    assert "memorial proof" in rule_summary
    assert "concrete evidence" in rule_summary
    assert "dry-wood click" in rule_summary or "residual muscle memory" in rule_summary
    assert "ledger edge" in rule_summary or "breaks visibly" in rule_summary
    assert "restore consciousness" in rule_objective or "restored consciousness" in rule_objective
    assert "dry-wood click" in rule_objective or "residual muscle memory" in rule_objective
    assert "banner snaps overhead" in public_summary or "still vessel" in public_summary
    assert "one beat of silence" in public_summary
    assert "dry-wood click" in public_summary or "stays still" in public_summary
    assert "wind" in public_summary or "dust" in public_summary or "chalk" in public_summary or "banner" in public_summary
    assert "visible flinch" in public_summary or "grief" in public_objective
    assert "human shape" in public_summary or "new order" in public_summary
    assert "bodily rather than procedural" in public_objective
    assert "restored consciousness" in public_objective or "conscious response" not in public_objective
    assert "explicit final choice" in sacrifice_summary
    assert "receives the burden through earlier preparation" in sacrifice_summary
    assert "visible preparation" in sacrifice_objective or "earlier preparation" in sacrifice_objective
    assert "already knows the return failed" in aftermath["summary"].lower() or "already knows the resurrection failed" in aftermath["summary"].lower()
    assert "no answering voice" in closure_summary or "returning thought" in closure_summary
    assert "by dusk" in closure_summary
    assert "by night" in closure_summary
    assert "by dawn" in closure_summary
    assert "public confession" in closure_summary
    assert "lasting aftermath" in closure_summary
    assert "ordinary detail" in closure_summary
    assert "shudders" in closure_summary or "gust" in closure_summary
    assert "small ordinary task resumes" in closure_summary or "new order can serve the living" in closure_summary
    assert "lamp flame gutters" in closure_summary
    for plan in (rule_revelation, sacrifice, aftermath, public_reckoning, closure):
        for field in ("summary", "objective", "hook"):
            assert "{" not in plan[field]
            assert "}" not in plan[field]


def test_normalize_departed_relationship_status_downgrades_active_bond() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    normalized = revision_service._normalize_departed_relationship_status(
        relationship_status="oath-bound allies",
        focus_character="Captain Vale",
        relationship_target="Old Quill",
        departed_characters={"Old Quill": 17},
        chapter_number=19,
        target_chapters=20,
    )

    assert normalized == "legacy carried into public witness"


def test_normalize_departed_relationship_status_progresses_vessel_relationship_by_phase() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    aftermath_status = revision_service._normalize_departed_relationship_status(
        relationship_status="keeper of the vessel",
        focus_character="Captain Vale",
        relationship_target="Old Quill (Vessel)",
        departed_characters={"Old Quill": 16},
        chapter_number=17,
        target_chapters=20,
    )
    closure_status = revision_service._normalize_departed_relationship_status(
        relationship_status="keeper of the vessel",
        focus_character="Captain Vale",
        relationship_target="Old Quill (Vessel)",
        departed_characters={"Old Quill": 16},
        chapter_number=20,
        target_chapters=20,
    )

    assert aftermath_status == "keeper confronting the vessel"
    assert closure_status == "living line carrying the vessel's cost"


def test_soft_issue_departure_hints_infers_departure_without_chapter_number() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    hints = revision_service._soft_issue_departure_hints(
        "relationship status for deceased character remains active. change old quill's status to spirit guide or legacy influence.",
        {"Old Quill", "Captain Vale"},
        fallback_chapter=16,
    )

    assert hints == {"Old Quill": 16}


def test_soft_issue_departure_hints_detects_death_promises_without_explicit_chapter_number() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    hints = revision_service._soft_issue_departure_hints(
        "old mo's death is the catalyst, but old mo still appears active in chapter 19 and chapter 20 summaries.",
        {"Old Mo", "Vera"},
        fallback_chapter=18,
    )

    assert hints == {"Old Mo": 18}


def test_normalize_terminal_role_language_reassigns_living_qualifier_to_keeper() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    cleaned = revision_service._normalize_terminal_role_language(
        "Lin Wei (living) organizes the crowd while Lin Wei (vessel) speaks the debt-name.",
        chapter_number=18,
        target_chapters=20,
        protagonist="Lin Wei",
        primary_keeper="Yara",
        vessel_label="the vessel",
    )

    assert "Lin Wei (living)" not in cleaned
    assert "Lin Wei (vessel)" not in cleaned
    assert "Yara organizes the crowd" in cleaned
    assert "Yara speaks the debt-name" in cleaned


def test_normalize_terminal_role_language_separates_keeper_from_vessel_mentions() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    cleaned = revision_service._normalize_terminal_role_language(
        "Lin Wei keeps the line steady while Lin Wei's hand leaves a mark and Lin Wei remains silent.",
        chapter_number=19,
        target_chapters=20,
        protagonist="Lin Wei",
        primary_keeper="Elara",
        vessel_label="the vessel",
    )

    assert "Lin Wei keeps the line steady" not in cleaned
    assert "Elara keeps the line steady" in cleaned
    assert "the vessel's hand" in cleaned
    assert "the vessel remains silent" in cleaned


def test_late_arc_vessel_label_uses_generic_slot() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    assert revision_service._late_arc_vessel_label("Lin Wei") == "The Vessel"
    assert revision_service._normalize_vessel_target_label(
        "The Vessel",
        {"Lin Wei", "Elara"},
    ) == "The Vessel"


def test_replace_abstract_terminal_memory_reference_concretizes_small_truth() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    updated = revision_service._replace_abstract_terminal_memory_reference(
        "The hook lands only when the crowd remembers one specific, small truth about the hero.",
        "the rain-count the hero used on the harbor steps",
    )

    assert "small truth" not in updated.lower()
    assert "rain-count the hero used on the harbor steps" in updated


def test_prefer_terminal_phase_summary_replaces_dense_reckoning_summary() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    preferred = revision_service._prefer_terminal_phase_summary(
        "The crowd surges, the line wavers, a witness shouts, the mechanism is half-explained, the keeper pushes forward, and the resolution lands in one crowded blur before anyone can track the order.",
        "Stage the reckoning in sequence: first the possessed crowd surges, then the witness line nearly buckles and a second living witness closes the gap, then the keeper or guiding witness reveals the working mechanism, and only after that does the final entry or fading beat land.",
        required_markers=("break", "gap", "mechanism"),
    )

    assert "nearly buckles" in preferred.lower()
    assert "working mechanism" in preferred.lower()


def test_strip_authorial_terminal_summary_instructions_keeps_only_diegetic_events() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    cleaned = revision_service._strip_authorial_terminal_summary_instructions(
        "Stage the reckoning in sequence with visible markers. The crowd surges, the line buckles, and a second witness closes the gap."
    )

    assert "Stage the reckoning" not in cleaned
    assert "The crowd surges" in cleaned
    assert revision_service._looks_authorial_terminal_summary(
        "Stage the reckoning in sequence with visible markers."
    )
    assert not revision_service._looks_authorial_terminal_summary(
        "The crowd surges, the line buckles, and a second witness closes the gap."
    )

    embedded = revision_service._strip_authorial_terminal_summary_instructions(
        "Before the seal closes, a witness leaves a token with the vessel, and the prose makes clear that the contact is memorial proof rather than a returning mind."
    )
    assert "the prose makes clear" not in embedded.lower()
    assert "memorial proof" in embedded.lower()


def test_default_terminal_arc_phase_plan_uses_event_language_for_late_summaries() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    aftermath = revision_service._default_terminal_arc_phase_plan(
        phase="aftermath",
        chapter_number=17,
        protagonist="Lin Wei",
        primary_keeper="Kael",
        supporting_witness="Elara",
        public_witness="Sera",
        vessel_label="The Vessel",
        continuity_anchor="Elara",
        confirmation_trigger="the seal knock",
    )
    closure = revision_service._default_terminal_arc_phase_plan(
        phase="closure",
        chapter_number=20,
        protagonist="Lin Wei",
        primary_keeper="Kael",
        supporting_witness="Elara",
        public_witness="Sera",
        vessel_label="The Vessel",
        continuity_anchor="Elara",
        confirmation_trigger="the seal knock",
    )

    assert "feels" not in aftermath["summary"].lower()
    assert "feels" not in closure["summary"].lower()
    assert "the prose makes clear" not in aftermath["summary"].lower()
    assert "the prose makes clear" not in closure["summary"].lower()
    assert "quiet private beat alone" in aftermath["summary"].lower()
    assert "memory-threaded" in aftermath["summary"].lower()
    assert "voice" in aftermath["summary"].lower()
    assert "rain" in aftermath["summary"].lower()
    assert "dry-wood click" in closure["summary"].lower()
    assert "blank page" in closure["summary"].lower()
    assert "lamp flame gutters" in closure["summary"].lower()
    assert "winter-blue" in closure["hook"].lower()
    assert "name" in closure["hook"].lower()
    for plan in (aftermath, closure):
        for field in ("summary", "objective", "hook"):
            assert "{" not in plan[field]
            assert "}" not in plan[field]


def test_terminal_arc_public_witness_falls_back_to_a_canonical_role() -> None:
    frame = TerminalArcSemanticFrame(
        protagonist="Ari",
        primary_keeper="Sera",
        vessel_label="The Vessel",
        supporting_witnesses=("a witness",),
        continuity_anchor="Ari",
        confirmation_trigger="the seal knock",
        phase_map={
            "sacrifice": 16,
            "aftermath": 17,
            "rule_revelation": 18,
            "public_reckoning": 19,
            "closure": 20,
        },
        motif_ledger=("ink",),
        closure_beats=("private closure", "public confession", "lasting aftermath"),
        public_cost_example="a fresh black mark lands on the ledger",
    )

    assert frame.supporting_witness == "Ari"
    assert frame.public_witness == "Sera"


@pytest.mark.asyncio
async def test_default_terminal_arc_phase_plan_avoids_placeholder_collective_fallbacks() -> None:
    revision_service = StoryRevisionService(ChapterDraftingService())

    closure = revision_service._default_terminal_arc_phase_plan(
        phase="closure",
        chapter_number=20,
        protagonist="Ari",
        primary_keeper="Sera",
        supporting_witness="a witness",
        public_witness="a witness",
        vessel_label="Ari (Vessel)",
        continuity_anchor="a witness",
        confirmation_trigger="the confirming knock from the old rule",
    )

    closure_summary = closure["summary"].lower()
    assert "a witness" not in closure_summary
    assert "the witness line" not in closure_summary
    assert "by dusk" in closure_summary
    assert "by night" in closure_summary
    assert "by dawn" in closure_summary
    assert "blank page" in closure_summary or "blank page" in closure["hook"].lower()


@pytest.mark.asyncio
async def test_late_arc_metadata_candidates_ignore_placeholder_public_witness_labels() -> None:
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
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Placeholder Filter Story",
        genre="fantasy",
        author_id="author-placeholder-filter",
        premise="A rewritten oath can save the city without turning the witness line into a placeholder.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    protagonist, _allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    late_arc_numbers = set(service._revision_service._late_arc_chapter_numbers(ctx_or_error.story.chapter_count).values())
    assert late_arc_numbers
    for chapter in ctx_or_error.story.chapters:
        if chapter.chapter_number in late_arc_numbers:
            chapter.metadata["focus_character"] = "a witness"
            chapter.metadata["relationship_target"] = "a witness"

    departed_characters: dict[str, int] = {}
    candidates = service._revision_service._late_arc_metadata_candidates(
        ctx_or_error,
        protagonist,
        departed_characters,
    )

    assert candidates
    assert "a witness" not in {candidate.lower() for candidate in candidates}
    assert "the public witness" not in {candidate.lower() for candidate in candidates}


@pytest.mark.asyncio
async def test_reinforce_terminal_rule_contrast_uses_issue_terms_generically() -> None:
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
        review_generation_provider=provider,
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Terminal Rule Contrast Coverage",
        genre="fantasy",
        author_id="author-terminal-rule-contrast",
        premise="A city of oath-keepers faces two different hauntings as the final confession approaches.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)

    changed = service._revision_service._reinforce_terminal_rule_contrast(
        ctx_or_error,
        primary_keeper="Sera",
        issue_verbatim_context="The distinction between 'Debt Spirits' and 'Paradox Ghosts' needs reinforcement because one haunts the city while the other traps a breaker inside a contradiction.",
    )

    assert changed
    bridge_chapter = ctx_or_error.story.chapters[13]
    bridge_summary = bridge_chapter.summary or ""
    assert "Debt Spirits" in bridge_summary
    assert "Paradox Ghosts" in bridge_summary
    assert "haunt the wider public line" in bridge_summary
    assert "trap one breaker inside a private contradiction" in bridge_summary
    assert "chapter_objective" in bridge_chapter.metadata


@pytest.mark.asyncio
async def test_late_arc_witness_selection_excludes_restrained_candidates_until_release() -> None:
    repository = InMemoryStoryRepository()
    generation_state_repository = InMemoryStoryGenerationStateRepository()
    generation_run_repository = InMemoryGenerationRunRepository()
    story_artifact_repository = InMemoryStoryArtifactRepository()
    service = StoryWorkflowService(
        story_repository=repository,
        generation_state_repository=generation_state_repository,
        generation_run_repository=generation_run_repository,
        story_artifact_repository=story_artifact_repository,
        text_generation_provider=LinWeiKaelContinuityBlueprintProvider(),
        review_generation_provider=DeterministicTextGenerationProvider(),
        default_target_chapters=20,
    )

    create_result = await service.create_story(
        title="Late Arc Witness Restraint Guard",
        genre="fantasy",
        author_id="author-witness-restraint-guard",
        premise="A memory scribe must carry a city's confession line after a captured archivist disappears into the wards.",
        target_chapters=20,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)
    await service.draft_story(story_id, target_chapters=20)

    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None

    stored_story.chapters[12].summary = (
        "Grand Scribe Kael is captured and locked in the ward cell beneath the archive after the quay ambush."
    )
    for chapter_number in (17, 18, 19, 20):
        chapter = stored_story.chapters[chapter_number - 1]
        chapter.metadata["focus_character"] = "Grand Scribe Kael"
        chapter.metadata["relationship_target"] = "Grand Scribe Kael"
        chapter.metadata["relationship_status"] = "captured under guard in the ward cell"
        chapter.summary = (
            f"Grand Scribe Kael remains in custody during chapter {chapter_number} while the surviving witnesses wait for dawn."
        )

    workflow_payload = stored_story.metadata.get("workflow", {})
    assert isinstance(workflow_payload, dict)
    outline_payload = workflow_payload.get("outline", {})
    assert isinstance(outline_payload, dict)
    outline_chapters = outline_payload.get("chapters", [])
    assert isinstance(outline_chapters, list)
    outline_chapters[12]["summary"] = stored_story.chapters[12].summary
    for chapter_number in (17, 18, 19, 20):
        outline_chapter = outline_chapters[chapter_number - 1]
        outline_chapter["summary"] = (
            f"Grand Scribe Kael stays imprisoned in the ward cell while the late-arc witness line forms in chapter {chapter_number}."
        )
        outline_chapter["chapter_objective"] = (
            "Keep Grand Scribe Kael under guard until the archive breaks open again."
        )
    workflow_payload["outline"] = outline_payload
    stored_story.metadata["workflow"] = workflow_payload

    story_memory = stored_story.metadata.get("story_memory", {})
    assert isinstance(story_memory, dict)
    active_characters = story_memory.get("active_characters", [])
    if not isinstance(active_characters, list):
        active_characters = []
    for candidate in ("Grand Scribe Kael", "Sera", "Elara"):
        if candidate not in active_characters:
            active_characters.append(candidate)
    story_memory["active_characters"] = active_characters

    relationship_states = story_memory.get("relationship_states", [])
    if not isinstance(relationship_states, list):
        relationship_states = []
    for chapter_number in (17, 18, 19, 20):
        relationship_states.append(
            {
                "chapter_number": chapter_number,
                "source": "Grand Scribe Kael",
                "target": "Lin Wei",
                "status": "captured under guard in the ward cell",
            }
        )
    story_memory["relationship_states"] = relationship_states
    stored_story.metadata["story_memory"] = story_memory

    await repository.save(stored_story)

    ctx_or_error = await service._load_context(story_id)
    assert not isinstance(ctx_or_error, Failure)
    assert ctx_or_error.workflow.blueprint is not None

    protagonist, allies = service._revision_service._resolve_cast_labels(ctx_or_error)
    cast_names = set(character_names(ctx_or_error.workflow.blueprint.character_bible))
    restrained = service._revision_service._resolve_restrained_late_arc_candidate(
        ctx_or_error,
        protagonist,
        cast_names,
    )
    keeper_pool = service._revision_service._resolve_late_arc_keeper_pool(
        ctx_or_error,
        protagonist,
        allies,
    )
    primary_keeper = keeper_pool[0]
    supporting_witness = service._revision_service._resolve_late_arc_supporting_witness(
        ctx_or_error,
        protagonist,
        primary_keeper,
    )
    public_witness = service._revision_service._resolve_late_arc_public_witness(
        ctx_or_error,
        protagonist,
        primary_keeper,
        supporting_witness,
    )
    heroic_witness = service._revision_service._resolve_late_arc_heroic_witness(
        ctx_or_error,
        protagonist,
        primary_keeper,
        supporting_witness,
        public_witness,
    )

    assert restrained == "Grand Scribe Kael"
    assert primary_keeper != "Grand Scribe Kael"
    assert supporting_witness != "Grand Scribe Kael"
    assert public_witness != "Grand Scribe Kael"
    assert heroic_witness != "Grand Scribe Kael"


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
async def test_semantic_warning_with_passing_metrics_now_blocks_publish_until_clean() -> None:
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
    assert report["publish_gate_passed"] is False
    assert any(issue["severity"] == "warning" for issue in report["issues"])

    publish_result = await service.publish_story(story_id)
    assert publish_result.is_err
    assert isinstance(publish_result, Failure)
    assert publish_result.code == "QUALITY_GATE_FAILED"
    assert publish_result.details is not None
    assert publish_result.details["warning_count"] > 0
    assert publish_result.details["report"]["publish_gate_passed"] is False


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
async def test_draft_story_normalizes_nested_scene_items_shape_from_provider() -> None:
    service, repository = build_story_service(
        text_generation_provider=NestedSceneItemsProvider()
    )

    create_result = await service.create_story(
        title="Nested Scene Items Story",
        genre="fantasy",
        author_id="author-nested-items",
        premise="An archivist finds that oath scenes arrive inside provider wrapper items.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)

    draft_result = await service.draft_story(story_id, target_chapters=3)

    assert draft_result.is_ok
    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    second_chapter = stored_story.chapters[1]
    assert second_chapter.scenes[0].scene_type == "opening"
    assert second_chapter.scenes[0].content
    assert second_chapter.scenes[-1].scene_type == "ending"
    assert second_chapter.scenes[-1].content


@pytest.mark.asyncio
async def test_draft_story_normalizes_single_scene_object_from_provider() -> None:
    service, repository = build_story_service(
        text_generation_provider=SingleSceneObjectProvider()
    )

    create_result = await service.create_story(
        title="Single Scene Object Story",
        genre="fantasy",
        author_id="author-single-scene",
        premise="An archivist receives a chapter draft as one root-level scene object.",
        target_chapters=3,
    )
    story_id = create_result.value["story"]["id"]

    await service.generate_blueprint(story_id)
    await service.generate_outline(story_id)

    draft_result = await service.draft_story(story_id, target_chapters=3)

    assert draft_result.is_ok
    stored_story = await repository.get_by_id(UUID(story_id))
    assert stored_story is not None
    second_chapter = stored_story.chapters[1]
    assert len(second_chapter.scenes) == 1
    assert second_chapter.scenes[0].scene_type == "action"
    assert second_chapter.scenes[0].title == "Recovered single scene"
    assert second_chapter.scenes[0].content


def test_extract_scenes_can_salvage_empty_scene_content_when_allowed() -> None:
    drafting_service = ChapterDraftingService()
    result = TextGenerationResult(
        step="chapter_scenes",
        provider="mock",
        model="salvage-v1",
        raw_text=json.dumps(
            {
                "scenes": [
                    {
                        "scene_type": "narrative",
                        "title": "Empty scene",
                        "content": "",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        content={
            "scenes": [
                {
                    "scene_type": "narrative",
                    "title": "Empty scene",
                    "content": "",
                }
            ]
        },
    )

    scenes = drafting_service._extract_scenes(
        result,
        {
            "chapter_number": 7,
            "title": "Recovered Chapter",
            "summary": "The chapter summary provides the fallback beat.",
            "chapter_objective": "Keep the key beat visible.",
            "hook": "The hook remains sharp.",
        },
        allow_empty_scene_salvage=True,
    )

    assert len(scenes) == 1
    assert scenes[0]["scene_type"] == "narrative"
    assert scenes[0]["title"] == "Empty scene"
    assert scenes[0]["content"] == "The chapter summary provides the fallback beat."


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
