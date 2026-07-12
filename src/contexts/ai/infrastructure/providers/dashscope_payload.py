from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
)
from src.contexts.ai.infrastructure.providers.dashscope_json import parse_json_object

SchemaCoercer = Callable[[Any, dict[str, Any], str | None], Any]


def _coerce_object_value(value: Any, schema: dict[str, Any], key: str | None) -> Any:
    if isinstance(value, dict):
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return value
        normalized = dict(value)
        for nested_key, nested_schema in properties.items():
            if nested_key in normalized:
                normalized[nested_key] = _coerce_value_to_schema(
                    normalized[nested_key],
                    nested_schema,
                    key=str(nested_key),
                )
        return normalized
    if isinstance(value, list):
        return {"characters": value} if key == "character_bible" else {"items": value}
    if value is None or value == "":
        return {}
    return {"value": value}


def _coerce_array_value(value: Any, _schema: dict[str, Any], _key: str | None) -> Any:
    if isinstance(value, list):
        return value
    return [] if value is None else [value]


def _coerce_string_value(value: Any, _schema: dict[str, Any], _key: str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return " ".join(
            str(item).strip() for item in value if str(item).strip()
        ).strip()
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False).strip()
    return str(value).strip()


def _coerce_integer_value(value: Any, _schema: dict[str, Any], _key: str | None) -> Any:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


_SCHEMA_COERCERS: dict[str, SchemaCoercer] = {
    "object": _coerce_object_value,
    "array": _coerce_array_value,
    "string": _coerce_string_value,
    "integer": _coerce_integer_value,
}


def _coerce_value_to_schema(
    value: Any,
    schema: dict[str, Any] | None,
    *,
    key: str | None = None,
) -> Any:
    if not isinstance(schema, dict):
        return value
    coercer = _SCHEMA_COERCERS.get(str(schema.get("type")))
    return coercer(value, schema, key) if coercer is not None else value


def coerce_payload_to_schema(
    payload: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(payload)
    for key, schema in response_schema.items():
        if key in normalized:
            normalized[key] = _coerce_value_to_schema(normalized[key], schema, key=key)
    return normalized


def _parse_json_like_value(candidate: str) -> Any | None:
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def fallback_payload_from_non_object_response(
    raw_text: str,
    response_schema: dict[str, Any],
) -> dict[str, Any] | None:
    chapter_schema = response_schema.get("chapter_markdown")
    if not isinstance(chapter_schema, dict) or chapter_schema.get("type") != "string":
        return None
    parsed = _parse_json_like_value(raw_text.strip())
    if isinstance(parsed, str):
        markdown = parsed.strip()
    elif isinstance(parsed, list):
        markdown = "\n\n".join(
            item.strip() for item in parsed if isinstance(item, str) and item.strip()
        ).strip()
    else:
        markdown = raw_text.strip()
    if not markdown:
        return None
    return {"chapter_markdown": markdown}


def payload_from_response_text(
    content_text: str,
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    try:
        return parse_json_object(content_text)
    except TextGenerationProviderError as exc:
        fallback_payload = fallback_payload_from_non_object_response(
            content_text,
            response_schema,
        )
        if fallback_payload is None:
            raise exc
        return fallback_payload
