from __future__ import annotations

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
)
from src.contexts.ai.infrastructure.providers.dashscope_payload import (
    coerce_payload_to_schema,
    fallback_payload_from_non_object_response,
    payload_from_response_text,
)


def test_coerce_payload_to_schema_covers_scalar_wrapper_edges() -> None:
    # Given
    payload = {
        "character_bible": ["Mira"],
        "sidecar_metadata": ["summary"],
        "empty_sidecar": None,
        "raw_value": "visible",
        "title": {"text": "Harbor"},
        "rank": "unknown",
        "unchanged": "kept",
    }
    schema = {
        "character_bible": {"type": "object"},
        "sidecar_metadata": {"type": "object"},
        "empty_sidecar": {"type": "object"},
        "raw_value": {"type": "object"},
        "title": {"type": "string"},
        "rank": {"type": "integer"},
        "missing": {"type": "array"},
        "unchanged": {"type": "custom"},
    }

    # When
    result = coerce_payload_to_schema(payload, schema)

    # Then
    assert result == {
        "character_bible": {"characters": ["Mira"]},
        "sidecar_metadata": {"items": ["summary"]},
        "empty_sidecar": {},
        "raw_value": {"value": "visible"},
        "title": '{"text": "Harbor"}',
        "rank": "unknown",
        "unchanged": "kept",
    }


def test_fallback_payload_from_non_object_response_handles_rejections() -> None:
    # Given
    chapter_schema = {"chapter_markdown": {"type": "string"}}

    # When
    assert fallback_payload_from_non_object_response("[]", {}) is None
    assert fallback_payload_from_non_object_response("", chapter_schema) is None

    # Then
    assert fallback_payload_from_non_object_response(
        '"# Chapter 1"', chapter_schema
    ) == {"chapter_markdown": "# Chapter 1"}


def test_payload_from_response_text_reraises_without_chapter_fallback() -> None:
    # Given
    schema = {"items": {"type": "array"}}

    # When / Then
    with pytest.raises(TextGenerationProviderError, match="not a JSON object"):
        payload_from_response_text("[1, 2]", schema)
