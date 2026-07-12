from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_json import (
    parse_json_object as parse_json_object,
)

DEFAULT_DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
_COMPATIBLE_MODE_SEGMENTS = ("api", "v2", "apps", "protocols", "compatible-mode", "v1")
_COMPATIBLE_MODE_PATH = "/" + "/".join(_COMPATIBLE_MODE_SEGMENTS)
DEFAULT_DASHSCOPE_RESPONSES_API_BASE = (
    "https://dashscope.aliyuncs.com" + _COMPATIBLE_MODE_PATH
)
DEFAULT_DASHSCOPE_TEXT_ENDPOINT = "/services/aigc/text-generation/generation"
DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT = (
    "/services/aigc/multimodal-generation/generation"
)
DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT = "/responses"
DashScopeTransportMode = Literal[
    "text_generation",
    "multimodal_generation",
    "responses",
]


def _normalize_generation_base(api_base: str | None) -> str:
    base_url = (api_base or DEFAULT_DASHSCOPE_API_BASE).rstrip("/")
    parsed = urlsplit(base_url)
    if "compatible-mode" not in parsed.path:
        return base_url
    return urlunsplit((parsed.scheme, parsed.netloc, "/api/v1", "", ""))


def _normalize_responses_base(api_base: str | None) -> str:
    base_url = (api_base or DEFAULT_DASHSCOPE_RESPONSES_API_BASE).rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.path == _COMPATIBLE_MODE_PATH:
        return base_url
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            _COMPATIBLE_MODE_PATH,
            "",
            "",
        )
    )


def _build_system_content(task: TextGenerationTask) -> str:
    schema_text = json.dumps(task.response_schema, ensure_ascii=False)
    return f"{task.system_prompt}\nReturn valid JSON only. Output schema: {schema_text}"


def _build_user_content(task: TextGenerationTask) -> str:
    metadata_text = json.dumps(task.metadata, ensure_ascii=False)
    return f"{task.user_prompt}\nTask step: {task.step}\nMetadata: {metadata_text}"


@dataclass(frozen=True, slots=True)
class DashScopeTransport:
    mode: DashScopeTransportMode
    endpoint: str
    responses_api: bool = False
    multimodal_content: bool = False

    def normalize_api_base(self, api_base: str | None) -> str:
        if self.responses_api:
            return _normalize_responses_base(api_base)
        return _normalize_generation_base(api_base)

    def endpoint_path(self) -> str:
        return self.endpoint

    def build_request_payload(
        self,
        *,
        model: str,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        if self.responses_api:
            return {
                "model": model,
                "input": (
                    f"System:\n{_build_system_content(task)}\n\n"
                    f"User:\n{_build_user_content(task)}"
                ),
                "temperature": task.temperature,
            }
        return {
            "model": model,
            "input": {"messages": self._messages_for(task)},
            "parameters": {
                "temperature": task.temperature,
                "enable_thinking": False,
                "result_format": "message",
                "response_format": {"type": "json_object"},
            },
        }

    def _messages_for(self, task: TextGenerationTask) -> list[dict[str, Any]]:
        system_content = _build_system_content(task)
        user_content = _build_user_content(task)
        if self.multimodal_content:
            return [
                {"role": "system", "content": [{"text": system_content}]},
                {"role": "user", "content": [{"text": user_content}]},
            ]
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def extract_response_text(self, data: dict[str, Any]) -> str:
        if self.responses_api:
            return extract_responses_text(data)
        return extract_generation_response_text(data)


_RESPONSES_TRANSPORT = DashScopeTransport(
    mode="responses",
    endpoint=DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT,
    responses_api=True,
)
_TRANSPORTS: dict[DashScopeTransportMode, DashScopeTransport] = {
    "text_generation": DashScopeTransport(
        mode="text_generation",
        endpoint=DEFAULT_DASHSCOPE_TEXT_ENDPOINT,
    ),
    "multimodal_generation": DashScopeTransport(
        mode="multimodal_generation",
        endpoint=DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT,
        multimodal_content=True,
    ),
    "responses": _RESPONSES_TRANSPORT,
}


def resolve_transport(mode: DashScopeTransportMode) -> DashScopeTransport:
    return _TRANSPORTS.get(mode, _RESPONSES_TRANSPORT)


def extract_generation_response_text(data: dict[str, Any]) -> str:
    output = data.get("output")
    if not isinstance(output, dict):
        raise TextGenerationProviderError("DashScope response missing output")
    choices = output.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise TextGenerationProviderError(
                "DashScope response choice is not an object"
            )
        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise TextGenerationProviderError(
                "DashScope response message is not an object"
            )
        return _extract_content_text(message)
    text = output.get("text")
    if isinstance(text, str) and text.strip():
        return text
    raise TextGenerationProviderError(
        "DashScope response missing structured message content"
    )


def _extract_content_text(message: dict[str, Any]) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content or "{}"
    if isinstance(content, list):
        text_parts = [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and item["text"].strip()
        ]
        if text_parts:
            return "".join(text_parts)
    return "{}"


def extract_responses_text(data: dict[str, Any]) -> str:
    output = data.get("output")
    if not isinstance(output, list):
        raise TextGenerationProviderError("DashScope responses output is invalid")
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        text_parts = [
            entry["text"]
            for entry in content
            if isinstance(entry, dict)
            and isinstance(entry.get("text"), str)
            and entry["text"].strip()
        ]
        if text_parts:
            return "".join(text_parts)
    raise TextGenerationProviderError("DashScope responses output missing message text")


def extract_usage_tokens(data: dict[str, Any]) -> tuple[int | None, int | None]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None, None
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    return (
        int(prompt_tokens) if isinstance(prompt_tokens, int) else None,
        int(completion_tokens) if isinstance(completion_tokens, int) else None,
    )
