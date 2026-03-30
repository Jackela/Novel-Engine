"""Shared helpers for the typed story workflow services."""

from __future__ import annotations

from typing import Any

from src.contexts.narrative.application.services.story_workflow_types import (
    StoryOutlineArtifact,
)


def character_names(character_bible: dict[str, Any]) -> list[str]:
    """Return normalized character names from a character bible."""
    characters = character_bible.get("characters", [])
    if not isinstance(characters, list):
        return []

    names: list[str] = []
    for character in characters:
        if not isinstance(character, dict):
            continue
        name = str(character.get("name", "")).strip()
        if name:
            names.append(name)
    return names


def character_profile(
    character_bible: dict[str, Any],
    focus_character: str,
) -> dict[str, Any]:
    """Return the character profile for a named focus character."""
    characters = character_bible.get("characters", [])
    if not isinstance(characters, list):
        return {}

    for character in characters:
        if not isinstance(character, dict):
            continue
        if str(character.get("name", "")).strip() == focus_character:
            return character
    return {}


def normalize_scene_type(scene_type: Any) -> str:
    """Map arbitrary scene labels into the canonical scene type set."""
    value = str(scene_type).strip().lower() or "narrative"
    valid_types = {
        "opening",
        "narrative",
        "dialogue",
        "action",
        "decision",
        "climax",
        "ending",
    }
    if value in valid_types:
        return value

    aliases: dict[str, str] = {
        "establishment": "opening",
        "setup": "opening",
        "introduction": "opening",
        "intro": "opening",
        "conversation": "dialogue",
        "interaction": "dialogue",
        "conflict": "action",
        "pressure": "action",
        "build-up": "narrative",
        "build": "narrative",
        "reveal": "climax",
        "twist": "climax",
        "resolution": "ending",
        "finale": "ending",
        "wrapup": "ending",
    }
    return aliases.get(value, "narrative")


def ensure_character_anchor(content: str, focus_character: str) -> str:
    """Ensure the focus character is materially present in scene text."""
    if not focus_character or focus_character.lower() in content.lower():
        return content
    return f"{content} {focus_character} anchors the chapter."


def ensure_motivation_anchor(content: str, focus_motivation: str) -> str:
    """Ensure the focus motivation is materially present in scene text."""
    if not focus_motivation or focus_motivation.lower() in content.lower():
        return content
    return f"{content} Their driving motive is to {focus_motivation}."


def ensure_relationship_anchor(
    content: str,
    source_character: str,
    target_character: str,
    relationship_status: str,
) -> str:
    """Ensure the chapter text exposes the active relationship state."""
    if not source_character or not target_character or not relationship_status:
        return content

    lowered = content.lower()
    if (
        source_character.lower() in lowered
        and target_character.lower() in lowered
        and relationship_status.lower() in lowered
    ):
        return content

    return (
        f"{content} Relationship status: {source_character} and "
        f"{target_character} are {relationship_status}."
    )


def ensure_hook(content: str, hook: str) -> str:
    """Ensure the intended hook is visible in the chapter ending."""
    if not hook:
        return content
    if hook.lower() in content.lower():
        return content
    if content.rstrip().endswith("?"):
        return content
    return f"{content} {hook}"


def ensure_payoff_anchor(content: str, previous_hook: str) -> str:
    """Ensure the chapter opening acknowledges the previous unresolved hook."""
    if not previous_hook:
        return content
    if previous_hook.lower() in content.lower():
        return content
    return f"{content} The chapter directly answers the previous hook: {previous_hook}"


def outline_chapter_for_number(
    outline: StoryOutlineArtifact | None,
    chapter_number: int,
) -> dict[str, Any]:
    """Return an outline chapter dict by chapter number."""
    if outline is None:
        raise ValueError(f"Outline chapter {chapter_number} not found")
    for chapter in outline.chapters:
        if chapter.chapter_number == chapter_number:
            return chapter.to_dict()
    raise ValueError(f"Outline chapter {chapter_number} not found")
