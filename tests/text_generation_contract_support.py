"""Shared structured contract helpers for text generation provider tests."""

from __future__ import annotations

import json
from typing import Any, Final, cast

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings

DASHSCOPE_DEFAULT_BASE: Final[str] = (
    "https://dashscope.aliyuncs.com/api/v1"
)
CONTRACT_STORY_ID: Final[str] = "contract-story"
CONTRACT_STORY_TITLE: Final[str] = "Contract Story"
CONTRACT_STORY_GENRE: Final[str] = "fantasy"
CONTRACT_STORY_PREMISE: Final[str] = (
    "A courier discovers the map of a kingdom that is rewriting itself."
)
CONTRACT_TARGET_CHAPTERS: Final[int] = 3
CONTRACT_FOCUS_CHARACTER: Final[str] = "Ari"
CONTRACT_FOCUS_MOTIVATION: Final[str] = "protect family"

TextGenerationContractCase = tuple[str, TextGenerationTask]


def build_contract_cases() -> list[TextGenerationContractCase]:
    """Build the canonical structured tasks used across provider contract tests."""
    character_names = ["Ari", "Lian", "Kade"]
    return [
        (
            "bible",
            TextGenerationTask(
                step="bible",
                system_prompt=(
                    "You design durable long-form Chinese web novels. Return a compact "
                    "world bible and character bible that can support many chapters."
                ),
                user_prompt=(
                    f"Story title: {CONTRACT_STORY_TITLE}\n"
                    f"Genre: {CONTRACT_STORY_GENRE}\n"
                    f"Premise: {CONTRACT_STORY_PREMISE}\n"
                    f"Target chapters: {CONTRACT_TARGET_CHAPTERS}\n"
                    "Tone: commercial web fiction"
                ),
                response_schema={
                    "world_bible": {"type": "object"},
                    "character_bible": {"type": "object"},
                    "premise_summary": {"type": "string"},
                },
                temperature=0.35,
                metadata={
                    "story_id": CONTRACT_STORY_ID,
                    "title": CONTRACT_STORY_TITLE,
                    "genre": CONTRACT_STORY_GENRE,
                    "author_id": "contract-author",
                    "premise": CONTRACT_STORY_PREMISE,
                    "tone": "commercial web fiction",
                    "target_chapters": CONTRACT_TARGET_CHAPTERS,
                },
            ),
        ),
        (
            "outline",
            TextGenerationTask(
                step="outline",
                system_prompt=(
                    "You design long-form Chinese web fiction outlines. Return a chapter "
                    "list with stable hooks, rising tension, and coherent pacing."
                ),
                user_prompt=(
                    f"Story title: {CONTRACT_STORY_TITLE}\n"
                    f"Premise: {CONTRACT_STORY_PREMISE}\n"
                    "World bible: {'setting': 'Contract realm'}\n"
                    "Character bible: {'characters': []}\n"
                    f"Target chapters: {CONTRACT_TARGET_CHAPTERS}\n"
                    "Tone: commercial web fiction"
                ),
                response_schema={
                    "chapters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chapter_number": {"type": "integer"},
                                "title": {"type": "string"},
                                "summary": {"type": "string"},
                                "hook": {"type": "string"},
                            },
                        },
                    }
                },
                temperature=0.4,
                metadata={
                    "story_id": CONTRACT_STORY_ID,
                    "target_chapters": CONTRACT_TARGET_CHAPTERS,
                    "chapter_count": 0,
                    "character_names": character_names,
                },
            ),
        ),
        (
            "chapter_scenes",
            TextGenerationTask(
                step="chapter_scenes",
                system_prompt=(
                    "You write coherent chapter scenes for a long-form Chinese web novel. "
                    "Keep the pacing commercial, the continuity stable, and the hook strong. "
                    "Use scene_type values from: opening, narrative, dialogue, action, "
                    "decision, climax, ending."
                ),
                user_prompt=(
                    f"Story title: {CONTRACT_STORY_TITLE}\n"
                    "Chapter number: 1\n"
                    "Chapter title: Chapter 1: Escalation\n"
                    "Chapter summary: Day 1: pressure rises and alliances shift.\n"
                    "Chapter hook: Who triggered the hidden trap at the end of chapter 1?\n"
                    f"Focus character: {CONTRACT_FOCUS_CHARACTER}\n"
                    f"Focus motivation: {CONTRACT_FOCUS_MOTIVATION}\n"
                    f"Premise: {CONTRACT_STORY_PREMISE}"
                ),
                response_schema={
                    "scenes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scene_type": {"type": "string"},
                                "title": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    }
                },
                temperature=0.5,
                metadata={
                    "story_id": CONTRACT_STORY_ID,
                    "chapter_number": 1,
                    "chapter_title": "Chapter 1: Escalation",
                    "focus_character": CONTRACT_FOCUS_CHARACTER,
                    "focus_motivation": CONTRACT_FOCUS_MOTIVATION,
                    "outline_hook": "Who triggered the hidden trap at the end of chapter 1?",
                    "previous_summary": "The border map shifted before the courier's eyes.",
                },
            ),
        ),
        (
            "revision",
            TextGenerationTask(
                step="revision",
                system_prompt=(
                    "You repair story structure, continuity, pacing, and hooks. "
                    "Return concise revision notes."
                ),
                user_prompt=(
                    f"Story title: {CONTRACT_STORY_TITLE}\n"
                    "Review issues: [{'code': 'flat_scene_stack', 'severity': 'high'}]\n"
                    "Revision target: strengthen continuity, pacing, and hooks."
                ),
                response_schema={
                    "revision_notes": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                temperature=0.2,
                metadata={
                    "story_id": CONTRACT_STORY_ID,
                    "issue_count": 1,
                    "issues": [
                        {
                            "code": "flat_scene_stack",
                            "severity": "high",
                            "location": "chapter-1",
                        }
                    ],
                    "chapter_count": CONTRACT_TARGET_CHAPTERS,
                },
            ),
        ),
    ]


def resolve_dashscope_credentials() -> tuple[str, str]:
    """Resolve DashScope credentials for secret-gated live tests."""
    settings = NovelEngineSettings()
    api_key = settings.llm.dashscope_api_key
    if not api_key:
        pytest.skip(
            "Set ENABLE_DASHSCOPE_TESTS=1 and provide DASHSCOPE_API_KEY in your "
            "environment or .env.local to run DashScope live tests."
        )

    api_base = settings.llm.resolved_api_base("dashscope") or DASHSCOPE_DEFAULT_BASE
    return cast(str, api_key), api_base


def assert_structured_contract_result(
    result: TextGenerationResult,
    case: TextGenerationContractCase,
    *,
    provider_name: str,
    model_name: str,
    strict: bool,
) -> None:
    """Assert the shared structured contract across providers."""
    step, task = case
    assert result.step == task.step == step
    assert result.provider == provider_name
    assert result.model == model_name
    assert result.raw_text.strip()

    raw_payload = json.loads(result.raw_text)
    assert isinstance(raw_payload, dict)
    assert raw_payload == result.content
    assert isinstance(result.content, dict)

    if step == "bible":
        _assert_bible_payload(result.content, strict=strict)
        return

    if step == "outline":
        _assert_outline_payload(
            result.content,
            target_chapters=int(task.metadata["target_chapters"]),
            strict=strict,
        )
        return

    if step == "chapter_scenes":
        _assert_scene_payload(result.content, strict=strict)
        return

    if step == "revision":
        _assert_revision_payload(result.content)
        return

    raise AssertionError(f"Unsupported contract step: {step}")


def _assert_bible_payload(payload: dict[str, Any], *, strict: bool) -> None:
    world_bible = payload.get("world_bible")
    character_bible = payload.get("character_bible")
    premise_summary = payload.get("premise_summary")

    assert isinstance(world_bible, dict)
    assert isinstance(character_bible, dict)
    assert isinstance(premise_summary, str)
    assert premise_summary.strip()
    assert world_bible
    assert character_bible

    if strict:
        setting = world_bible.get("setting")
        core_rules = world_bible.get("core_rules")
        characters = character_bible.get("characters")

        assert isinstance(setting, str)
        assert setting.strip()
        assert isinstance(core_rules, list)
        assert core_rules
        assert all(isinstance(rule, str) and rule.strip() for rule in core_rules)
        assert isinstance(characters, list)
        assert len(characters) >= 3

        first_character = characters[0]
        assert isinstance(first_character, dict)
        assert isinstance(first_character.get("name"), str)
        assert str(first_character["name"]).strip()
        assert isinstance(first_character.get("core_trait"), str)
        assert str(first_character["core_trait"]).strip()
        assert isinstance(first_character.get("motivation"), str)
        assert str(first_character["motivation"]).strip()
        return

    assert any(
        isinstance(value, str) and value.strip()
        or isinstance(value, list)
        and len(value) > 0
        or isinstance(value, dict)
        and len(value) > 0
        for value in world_bible.values()
    )
    assert any(
        isinstance(value, dict)
        and isinstance(value.get("name"), str)
        and str(value["name"]).strip()
        or isinstance(value, list)
        and any(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and str(item["name"]).strip()
            for item in value
        )
        for value in character_bible.values()
    )


def _assert_outline_payload(
    payload: dict[str, Any],
    *,
    target_chapters: int,
    strict: bool,
) -> None:
    chapters = payload.get("chapters")
    assert isinstance(chapters, list)
    assert chapters

    first_chapter = chapters[0]
    assert isinstance(first_chapter, dict)

    chapter_number = first_chapter.get("chapter_number")
    title = first_chapter.get("title")
    summary = first_chapter.get("summary")
    hook = first_chapter.get("hook")

    assert isinstance(chapter_number, int)
    assert chapter_number >= 1
    assert isinstance(title, str)
    assert title.strip()
    assert isinstance(summary, str)
    assert summary.strip()
    assert isinstance(hook, str)
    assert hook.strip()

    if strict:
        assert len(chapters) == target_chapters
        assert all(isinstance(chapter, dict) for chapter in chapters)


def _assert_scene_payload(payload: dict[str, Any], *, strict: bool) -> None:
    scenes = payload.get("scenes")
    assert isinstance(scenes, list)
    assert scenes

    first_scene = scenes[0]
    assert isinstance(first_scene, dict)

    scene_type = first_scene.get("scene_type")
    title = first_scene.get("title")
    content = first_scene.get("content")

    assert isinstance(scene_type, str)
    assert scene_type.strip()
    assert isinstance(title, str)
    assert title.strip()
    assert isinstance(content, str)
    assert content.strip()

    if strict:
        assert len(scenes) >= 3


def _assert_revision_payload(payload: dict[str, Any]) -> None:
    revision_notes = payload.get("revision_notes")
    assert isinstance(revision_notes, list)
    assert revision_notes
    assert all(isinstance(note, str) and note.strip() for note in revision_notes)
