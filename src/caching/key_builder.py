"""Helpers for building normalized cache keys."""

from __future__ import annotations

import hashlib
from typing import Any, Dict

_BUCKET_TEMPERATURE = 0.1
_BUCKET_TOP_P = 0.05
_BUCKET_TOKENS = 100


def _bucket(value: float, size: float) -> float:
    return round(max(0.0, value) / size) * size


def _bucket_tokens(value: int) -> int:
    if value <= 0:
        return 0
    return int(round(value / _BUCKET_TOKENS) * _BUCKET_TOKENS)


def build_exact(params: Dict[str, Any], prompt: str) -> str:
    """Build an exact-cache key incorporating prompt hash and config buckets."""

    norm = _normalize_params(params)
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    ordered = [
        norm.get("character_id", ""),
        norm.get("session_id", ""),
        norm.get("model_name", ""),
        norm.get("provider", ""),
        norm.get("template_id", ""),
        norm.get("template_version", ""),
        f"temp:{norm.get('temperature_bucket', 0)}",
        f"top_p:{norm.get('top_p_bucket', 0)}",
        f"max:{norm.get('max_tokens_bucket', 0)}",
        prompt_hash,
    ]
    return "|".join(ordered)


def build_semantic_bucket(params: Dict[str, Any]) -> str:
    """Semantic buckets omit the prompt hash but keep configuration boundaries."""

    norm = _normalize_params(params)
    ordered = [
        norm.get("character_id", ""),
        norm.get("model_name", ""),
        norm.get("template_id", ""),
        norm.get("template_version", ""),
        norm.get("index_version", ""),
        norm.get("locale", ""),
        f"temp:{norm.get('temperature_bucket', 0)}",
        f"top_p:{norm.get('top_p_bucket', 0)}",
        f"max:{norm.get('max_tokens_bucket', 0)}",
    ]
    return "|".join(ordered)


def _normalize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    model = (params.get("model_name") or "unknown").lower()
    template_id = params.get("prompt_template_id") or params.get("template_id") or ""
    template_version = (
        params.get("prompt_template_version") or params.get("template_version") or ""
    )
    normalized = {
        "character_id": params.get("character_id", ""),
        "session_id": params.get("session_id", ""),
        "model_name": model,
        "provider": (params.get("provider") or "").lower(),
        "template_id": template_id,
        "template_version": str(template_version),
        "index_version": str(params.get("index_version", "")),
        "locale": (params.get("locale") or "global").lower(),
        "temperature_bucket": _bucket(
            float(params.get("temperature", 0.0)), _BUCKET_TEMPERATURE
        ),
        "top_p_bucket": _bucket(float(params.get("top_p", 0.0)), _BUCKET_TOP_P),
        "max_tokens_bucket": _bucket_tokens(int(params.get("max_tokens", 0))),
    }
    return normalized
