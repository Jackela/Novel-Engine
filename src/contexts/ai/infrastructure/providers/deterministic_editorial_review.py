from __future__ import annotations

from typing import Any

from src.contexts.ai.application.ports.text_generation_port import TextGenerationTask

_REVIEW_CODES = (
    "agency_attribution",
    "causal_continuity",
    "reader_pull",
    "closure_spacing",
    "promise_trust",
    "voice_stability",
)


def build_editorial_review_payload(task: TextGenerationTask) -> dict[str, Any]:
    chapters = task.metadata.get("chapters", [])
    dimensions = task.metadata.get("dimensions", [])
    title = str(task.metadata.get("title", "Untitled Story")).strip()
    chapter_items = chapters if isinstance(chapters, list) and chapters else []

    first = _chapter_at(chapter_items, title, 0)
    middle = _chapter_at(chapter_items, title, len(chapter_items) // 2)
    last = _chapter_at(chapter_items, title, max(0, len(chapter_items) - 1))
    evidence_by_code = {
        "agency_attribution": str(first.get("opening", title)),
        "causal_continuity": str(middle.get("middle", title)),
        "reader_pull": str(last.get("ending", title)),
        "closure_spacing": " / ".join(
            str(dict(item).get("ending", "")).strip()
            for item in chapter_items[-3:]
            if isinstance(item, dict)
        )
        or str(last.get("ending", title)),
        "promise_trust": _first_promise_text(task.metadata)
        or str(middle.get("opening", title)),
        "voice_stability": str(first.get("middle", first.get("opening", title))),
    }
    location_by_code = {
        "agency_attribution": str(first.get("location", "manuscript")),
        "causal_continuity": str(middle.get("location", "manuscript")),
        "reader_pull": str(last.get("location", "manuscript")),
        "closure_spacing": "manuscript",
        "promise_trust": "manuscript",
        "voice_stability": "manuscript",
    }
    labels = {
        str(item.get("code")): str(item.get("label"))
        for item in dimensions
        if isinstance(item, dict)
    }
    suggestions = []
    for code in _REVIEW_CODES:
        label = labels.get(code, code.replace("_", " "))
        evidence = _shorten(evidence_by_code[code])
        location = location_by_code[code]
        suggestions.append(
            {
                "code": code,
                "message": (
                    f"In {title}, the {label} pass should inspect {location} "
                    f"around: {evidence}"
                ),
                "location": location,
                "suggestion": (
                    f"Revise {location} so {label} is carried by a visible prose beat."
                ),
                "evidence": evidence_by_code[code],
                "details": {
                    "dimension": label,
                    "source": "deterministic-editorial",
                },
            }
        )
    return {"suggestions": suggestions}


def _chapter_at(
    chapter_items: list[Any],
    title: str,
    index: int,
) -> dict[str, Any]:
    if not chapter_items:
        return _fallback_chapter(title)
    item = chapter_items[min(index, len(chapter_items) - 1)]
    if isinstance(item, dict):
        return dict(item)
    return _fallback_chapter(title)


def _fallback_chapter(title: str) -> dict[str, str]:
    return {
        "filename": "manuscript",
        "location": "manuscript",
        "opening": title,
        "middle": title,
        "ending": title,
    }


def _first_promise_text(metadata: dict[str, Any]) -> str:
    sidecars = metadata.get("sidecars", {})
    if not isinstance(sidecars, dict):
        return ""
    for sidecar in sidecars.values():
        if not isinstance(sidecar, dict):
            continue
        promises = sidecar.get("promises", [])
        if not isinstance(promises, list):
            continue
        for promise in promises:
            if isinstance(promise, dict):
                text = str(promise.get("text", "")).strip()
            else:
                text = str(promise).strip()
            if text:
                return text
    return ""


def _shorten(text: str, limit: int = 96) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
