"""Shared helpers for the typed story workflow services."""

from __future__ import annotations

import re
from typing import Any

from src.contexts.narrative.application.services.story_workflow_types import (
    StoryOutlineArtifact,
)


def _iter_character_entries(character_bible: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    def append_entry(candidate: Any) -> None:
        if not isinstance(candidate, dict):
            return
        name = str(candidate.get("name", "")).strip()
        if not name or name in seen_names:
            return
        seen_names.add(name)
        entries.append(candidate)

    def append_entries(candidate: Any) -> None:
        if isinstance(candidate, dict):
            append_entry(candidate)
            return
        if isinstance(candidate, list):
            for item in candidate:
                append_entry(item)

    append_entries(character_bible.get("characters"))
    for key in (
        "protagonist",
        "antagonist",
        "deuteragonist",
        "love_interest",
        "mentor",
        "supporting",
        "key_supporting",
        "supporting_cast",
        "allies",
        "villains",
        "cast",
    ):
        append_entries(character_bible.get(key))

    if entries:
        return entries

    for value in character_bible.values():
        append_entries(value)
    return entries


def _character_names_from_keys(
    character_bible: dict[str, Any],
    *keys: str,
) -> list[str]:
    names: list[str] = []
    seen_names: set[str] = set()

    for key in keys:
        value = character_bible.get(key)
        candidates = value if isinstance(value, list) else [value]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            name = str(candidate.get("name", "")).strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            names.append(name)
    return names


def character_names(character_bible: dict[str, Any]) -> list[str]:
    """Return normalized character names from a character bible."""
    return [
        str(character.get("name", "")).strip()
        for character in _iter_character_entries(character_bible)
    ]


def protagonist_name(character_bible: dict[str, Any]) -> str:
    """Return the canonical protagonist name if one is explicitly present."""
    protagonists = _character_names_from_keys(character_bible, "protagonist")
    return protagonists[0] if protagonists else ""


def antagonist_names(character_bible: dict[str, Any]) -> list[str]:
    """Return explicitly marked antagonists to avoid using them as ally targets."""
    return _character_names_from_keys(character_bible, "antagonist", "villains")


def pov_character_names(character_bible: dict[str, Any]) -> list[str]:
    """Return the preferred POV cast, excluding pure antagonist slots when possible."""
    pov_names = _character_names_from_keys(
        character_bible,
        "protagonist",
        "deuteragonist",
        "love_interest",
        "mentor",
        "supporting",
        "key_supporting",
        "supporting_cast",
        "allies",
        "cast",
    )
    if pov_names:
        return pov_names

    blocked = set(antagonist_names(character_bible))
    fallback_names = character_names(character_bible)
    filtered = [name for name in fallback_names if name not in blocked]
    return filtered or fallback_names


def character_profile(
    character_bible: dict[str, Any],
    focus_character: str,
) -> dict[str, Any]:
    """Return the character profile for a named focus character."""
    normalized_focus = focus_character.strip()
    if not normalized_focus:
        return {}

    for character in _iter_character_entries(character_bible):
        if str(character.get("name", "")).strip() == normalized_focus:
            return character
    return {}


def extract_world_rules(world_bible: dict[str, Any]) -> list[str]:
    """Return normalized world-rule strings from varied provider payload shapes."""
    rules: list[str] = []
    seen_rules: set[str] = set()

    def add_rule(rule: str) -> None:
        normalized = " ".join(rule.split())
        if not normalized:
            return
        if normalized in seen_rules:
            return
        seen_rules.add(normalized)
        rules.append(normalized)

    def add_from_value(value: Any) -> None:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return
            numbered_parts = [
                " ".join(part.split())
                for part in re.split(r"(?:^|\s)(?:\d+\.)\s*", text)
                if part and part.strip()
            ]
            if len(numbered_parts) > 1:
                for part in numbered_parts:
                    add_rule(part)
                return
            line_parts = [
                " ".join(part.split())
                for part in re.split(r"[\r\n]+|(?:\s*[;-]\s+)", text)
                if part and part.strip()
            ]
            if len(line_parts) > 1:
                for part in line_parts:
                    add_rule(part)
                return
            add_rule(text)
            return

        if isinstance(value, list):
            for item in value:
                add_from_value(item)
            return

        if not isinstance(value, dict):
            return

        for key in ("core_rules", "rules", "limitations", "constraints"):
            if key in value:
                add_from_value(value[key])
        for key, nested_value in value.items():
            normalized_key = str(key).strip().lower()
            if any(
                token in normalized_key
                for token in ("rule", "law", "constraint", "limit")
            ):
                add_from_value(nested_value)
        cost = value.get("cost")
        if isinstance(cost, str) and cost.strip():
            add_rule(f"Cost: {cost.strip()}")

    for key in (
        "core_rules",
        "rules_of_magic",
        "rules",
        "limitations",
        "constraints",
    ):
        if key in world_bible:
            add_from_value(world_bible[key])
    for key, value in world_bible.items():
        normalized_key = str(key).strip().lower()
        if any(token in normalized_key for token in ("rule", "law", "constraint", "limit")):
            add_from_value(value)

    magic_system = world_bible.get("magic_system")
    if isinstance(magic_system, dict):
        add_from_value(magic_system)

    return rules


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
