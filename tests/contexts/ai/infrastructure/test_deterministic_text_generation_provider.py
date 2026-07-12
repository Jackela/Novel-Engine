from __future__ import annotations

import asyncio
import json

from src.contexts.ai.application.ports.text_generation_port import TextGenerationTask
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)


def editorial_task(metadata: dict[str, object]) -> TextGenerationTask:
    return TextGenerationTask(
        step="editorial_review",
        system_prompt="system",
        user_prompt="user",
        response_schema={"suggestions": {"type": "array"}},
        metadata=metadata,
    )


def generate_editorial(metadata: dict[str, object]) -> dict[str, object]:
    provider = DeterministicTextGenerationProvider()
    result = asyncio.run(provider.generate_structured(editorial_task(metadata)))
    assert json.loads(result.raw_text) == result.content
    return result.content


def suggestions_by_code(content: dict[str, object]) -> dict[str, dict[object, object]]:
    suggestions = content["suggestions"]
    assert isinstance(suggestions, list)
    return {
        str(item["code"]): item
        for item in suggestions
        if isinstance(item, dict) and "code" in item
    }


def test_editorial_review_uses_chapter_evidence_labels_and_sidecar_promises() -> None:
    # Given
    long_opening = " ".join(["agency pressure"] * 16)
    metadata: dict[str, object] = {
        "title": "Clockwork Harbor",
        "chapters": [
            {
                "filename": "chapter-1.md",
                "location": "Chapter 1",
                "opening": long_opening,
                "middle": "Mira chooses the harder witness.",
                "ending": "The first door opens.",
            },
            "interlude without parsed beats",
            {
                "filename": "chapter-3.md",
                "location": "Chapter 3",
                "opening": "A later opening",
                "middle": "A later middle",
                "ending": "The final door stays unresolved.",
            },
        ],
        "dimensions": [
            {"code": "agency_attribution", "label": "agency attribution"},
            {"code": "promise_trust", "label": "promise trust"},
        ],
        "sidecars": {
            "chapter-1": {
                "promises": [{"text": "The ledger debt must be paid publicly."}]
            }
        },
    }

    # When
    content = generate_editorial(metadata)

    # Then
    suggestions = suggestions_by_code(content)
    assert set(suggestions) == {
        "agency_attribution",
        "causal_continuity",
        "reader_pull",
        "closure_spacing",
        "promise_trust",
        "voice_stability",
    }
    assert suggestions["agency_attribution"]["evidence"] == long_opening
    assert "agency pressure agency pressure" in str(
        suggestions["agency_attribution"]["message"]
    )
    assert str(suggestions["agency_attribution"]["message"]).endswith("...")
    assert suggestions["causal_continuity"]["evidence"] == "Clockwork Harbor"
    assert (
        suggestions["closure_spacing"]["evidence"]
        == "The first door opens. / The final door stays unresolved."
    )
    assert (
        suggestions["promise_trust"]["evidence"]
        == "The ledger debt must be paid publicly."
    )
    assert suggestions["promise_trust"]["details"] == {
        "dimension": "promise trust",
        "source": "deterministic-editorial",
    }


def test_editorial_review_falls_back_for_empty_chapters_and_string_promises() -> None:
    # Given
    metadata: dict[str, object] = {
        "title": "Empty Manuscript",
        "chapters": [],
        "dimensions": [{"code": "voice_stability", "label": "voice stability"}],
        "sidecars": {"outline": {"promises": ["Keep the lighthouse visible."]}},
    }

    # When
    content = generate_editorial(metadata)

    # Then
    suggestions = suggestions_by_code(content)
    assert suggestions["agency_attribution"]["location"] == "manuscript"
    assert suggestions["agency_attribution"]["evidence"] == "Empty Manuscript"
    assert suggestions["promise_trust"]["evidence"] == "Keep the lighthouse visible."
    assert "voice stability" in str(suggestions["voice_stability"]["message"])
