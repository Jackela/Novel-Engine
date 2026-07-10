from __future__ import annotations

import json
from typing import Any

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
)

MIN_FENCED_BLOCK_LINES = 3


def parse_json_object(raw_text: str) -> dict[str, Any]:
    candidates: list[str] = []
    stripped = raw_text.strip()
    if stripped:
        candidates.append(stripped)
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= MIN_FENCED_BLOCK_LINES:
            candidates.append("\n".join(lines[1:-1]).strip())
    candidates.extend(_extract_balanced_fragments(stripped, opening="{", closing="}"))
    candidates.extend(_extract_balanced_fragments(stripped, opening="[", closing="]"))
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        parsed = _parse_json_like_value(candidate)
        if parsed is None:
            continue
        normalized = _coerce_parsed_object_candidate(parsed)
        if normalized is not None:
            return normalized
    raise TextGenerationProviderError("DashScope response is not a JSON object")


def _extract_balanced_fragments(
    text: str,
    *,
    opening: str,
    closing: str,
) -> list[str]:
    fragments: list[str] = []
    depth = 0
    start = -1
    in_string = False
    delimiter = ""
    escaped = False
    for index, character in enumerate(text):
        if in_string:
            escaped, in_string = _consume_string_character(
                character,
                escaped=escaped,
                in_string=in_string,
                delimiter=delimiter,
            )
            continue
        if character in {'"', "'"}:
            in_string = True
            delimiter = character
            continue
        if character == opening:
            if depth == 0:
                start = index
            depth += 1
            continue
        if character == closing and depth:
            depth -= 1
            if depth == 0 and start != -1:
                fragments.append(text[start : index + 1].strip())
                start = -1
    return fragments


def _consume_string_character(
    character: str,
    *,
    escaped: bool,
    in_string: bool,
    delimiter: str,
) -> tuple[bool, bool]:
    if escaped:
        return False, in_string
    if character == "\\":
        return True, in_string
    if character == delimiter:
        return False, False
    return False, in_string


def _parse_json_like_value(candidate: str) -> Any | None:
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def _coerce_parsed_object_candidate(parsed: Any) -> dict[str, Any] | None:
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, str):
        nested = _parse_json_like_value(parsed.strip())
        if nested is None or nested == parsed:
            return None
        return _coerce_parsed_object_candidate(nested)
    if isinstance(parsed, list):
        objects = [
            normalized
            for item in parsed
            if (normalized := _coerce_parsed_object_candidate(item)) is not None
        ]
        if not objects:
            return None
        merged: dict[str, Any] = {}
        for item in objects:
            merged.update(item)
        return merged
    return None
