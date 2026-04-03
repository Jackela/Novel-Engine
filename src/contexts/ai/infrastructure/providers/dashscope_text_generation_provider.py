"""DashScope native provider for structured text generation."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)

DEFAULT_DASHSCOPE_API_BASE = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_DASHSCOPE_RESPONSES_API_BASE = (
    "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1"
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
    if parsed.path == "/api/v2/apps/protocols/compatible-mode/v1":
        return base_url
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            "/api/v2/apps/protocols/compatible-mode/v1",
            "",
            "",
        )
    )


def _build_system_content(task: TextGenerationTask) -> str:
    schema_text = json.dumps(task.response_schema, ensure_ascii=False)
    return (
        f"{task.system_prompt}\n"
        "Return valid JSON only. "
        f"Output schema: {schema_text}"
    )


def _build_user_content(task: TextGenerationTask) -> str:
    metadata_text = json.dumps(task.metadata, ensure_ascii=False)
    return (
        f"{task.user_prompt}\n"
        f"Task step: {task.step}\n"
        f"Metadata: {metadata_text}"
    )


def _coerce_value_to_schema(
    value: Any,
    schema: dict[str, Any] | None,
    *,
    key: str | None = None,
) -> Any:
    if not isinstance(schema, dict):
        return value

    expected_type = schema.get("type")
    if expected_type == "object":
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            if key == "character_bible":
                return {"characters": value}
            return {"items": value}
        if value is None or value == "":
            return {}
        return {"value": value}

    if expected_type == "array":
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [value]

    if expected_type == "string":
        return str(value).strip()

    if expected_type == "integer":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    return value


def _coerce_payload_to_schema(
    payload: dict[str, Any],
    response_schema: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(payload)
    for key, schema in response_schema.items():
        if key not in normalized:
            continue
        normalized[key] = _coerce_value_to_schema(normalized[key], schema, key=key)
    return normalized


class _DashScopeTransport(Protocol):
    @property
    def mode(self) -> DashScopeTransportMode:
        ...

    def normalize_api_base(self, api_base: str | None) -> str:
        ...

    def endpoint_path(self) -> str:
        ...

    def build_request_payload(
        self,
        *,
        model: str,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        ...

    def extract_response_text(self, data: dict[str, Any]) -> str:
        ...


@dataclass(frozen=True, slots=True)
class _DashScopeGenerationTransport:
    mode: DashScopeTransportMode = "text_generation"

    def normalize_api_base(self, api_base: str | None) -> str:
        return _normalize_generation_base(api_base)

    def endpoint_path(self) -> str:
        return DEFAULT_DASHSCOPE_TEXT_ENDPOINT

    def build_request_payload(
        self,
        *,
        model: str,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "input": {
                "messages": [
                    {"role": "system", "content": _build_system_content(task)},
                    {"role": "user", "content": _build_user_content(task)},
                ],
            },
            "parameters": {
                "temperature": task.temperature,
                "enable_thinking": False,
                "result_format": "message",
            },
        }

    def extract_response_text(self, data: dict[str, Any]) -> str:
        return DashScopeTextGenerationProvider._extract_generation_response_text(data)


@dataclass(frozen=True, slots=True)
class _DashScopeMultimodalGenerationTransport:
    mode: DashScopeTransportMode = "multimodal_generation"

    def normalize_api_base(self, api_base: str | None) -> str:
        return _normalize_generation_base(api_base)

    def endpoint_path(self) -> str:
        return DEFAULT_DASHSCOPE_MULTIMODAL_ENDPOINT

    def build_request_payload(
        self,
        *,
        model: str,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "system",
                        "content": [{"text": _build_system_content(task)}],
                    },
                    {
                        "role": "user",
                        "content": [{"text": _build_user_content(task)}],
                    },
                ],
            },
            "parameters": {
                "temperature": task.temperature,
                "enable_thinking": False,
            },
        }

    def extract_response_text(self, data: dict[str, Any]) -> str:
        return DashScopeTextGenerationProvider._extract_generation_response_text(data)


@dataclass(frozen=True, slots=True)
class _DashScopeResponsesTransport:
    mode: DashScopeTransportMode = "responses"

    def normalize_api_base(self, api_base: str | None) -> str:
        return _normalize_responses_base(api_base)

    def endpoint_path(self) -> str:
        return DEFAULT_DASHSCOPE_RESPONSES_ENDPOINT

    def build_request_payload(
        self,
        *,
        model: str,
        task: TextGenerationTask,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "input": (
                f"System:\n{_build_system_content(task)}\n\n"
                f"User:\n{_build_user_content(task)}"
            ),
            "temperature": task.temperature,
        }

    def extract_response_text(self, data: dict[str, Any]) -> str:
        return DashScopeTextGenerationProvider._extract_responses_text(data)


class DashScopeTextGenerationProvider(TextGenerationProvider):
    """Structured generation provider backed by DashScope native generation API."""

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-flash",
        api_base: str | None = None,
        transport_mode: DashScopeTransportMode = "multimodal_generation",
        timeout: int = 30,
        retry_attempts: int = 2,
        retry_delay: float = 0.5,
    ) -> None:
        if not api_key:
            raise ValueError("DashScope API key is required")
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._transport = self._resolve_transport(transport_mode)
        self._timeout = timeout
        self._retry_attempts = max(1, retry_attempts)
        self._retry_delay = max(0.0, retry_delay)
        self._client: httpx.AsyncClient | None = None

    @property
    def transport_mode(self) -> DashScopeTransportMode:
        return self._transport.mode

    @staticmethod
    def _resolve_transport(mode: DashScopeTransportMode) -> _DashScopeTransport:
        if mode == "text_generation":
            return _DashScopeGenerationTransport()
        if mode == "multimodal_generation":
            return _DashScopeMultimodalGenerationTransport()
        return _DashScopeResponsesTransport()

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            base_url = self._transport.normalize_api_base(self._api_base)
            self._client = httpx.AsyncClient(
                base_url=base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _build_request_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        return self._transport.build_request_payload(model=self._model, task=task)

    def _endpoint_path(self) -> str:
        return self._transport.endpoint_path()

    def _timeout_for_step(self, task: TextGenerationTask) -> float:
        timeout_floors = {
            "bible": 60.0,
            "outline": 180.0,
            "chapter_scenes": 180.0,
            "semantic_review": 180.0,
            "revision": 180.0,
        }
        return max(float(self._timeout), timeout_floors.get(task.step, float(self._timeout)))

    @staticmethod
    def _extract_content_text(message: dict[str, Any]) -> str:
        content = message.get("content", "")
        if isinstance(content, str):
            return content or "{}"
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text)
            if text_parts:
                return "".join(text_parts)
        return "{}"

    @classmethod
    def _extract_generation_response_text(cls, data: dict[str, Any]) -> str:
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
            return cls._extract_content_text(message)

        text = output.get("text")
        if isinstance(text, str) and text.strip():
            return text

        raise TextGenerationProviderError(
            "DashScope response missing structured message content"
        )

    @staticmethod
    def _extract_responses_text(data: dict[str, Any]) -> str:
        output = data.get("output")
        if not isinstance(output, list):
            raise TextGenerationProviderError("DashScope responses output is invalid")

        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            text_parts: list[str] = []
            for entry in content:
                if not isinstance(entry, dict):
                    continue
                text = entry.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text)
            if text_parts:
                return "".join(text_parts)

        raise TextGenerationProviderError(
            "DashScope responses output missing message text"
        )

    @staticmethod
    def _parse_json_object(raw_text: str) -> dict[str, Any]:
        candidates: list[str] = []
        stripped = raw_text.strip()
        if stripped:
            candidates.append(stripped)

        if stripped.startswith("```") and stripped.endswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3:
                candidates.append("\n".join(lines[1:-1]).strip())

        object_start = stripped.find("{")
        object_end = stripped.rfind("}")
        if object_start != -1 and object_end > object_start:
            candidates.append(stripped[object_start : object_end + 1].strip())

        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise TextGenerationProviderError("DashScope response is not a JSON object")

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        client = self._get_client()
        effective_timeout = self._timeout_for_step(task)
        last_error: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                response = await client.post(
                    self._endpoint_path(),
                    json=self._build_request_payload(task),
                    timeout=effective_timeout,
                )
                response.raise_for_status()
                data = response.json()
                content_text = self._transport.extract_response_text(data)
                parsed = _coerce_payload_to_schema(
                    self._parse_json_object(content_text),
                    task.response_schema,
                )
                return TextGenerationResult(
                    step=task.step,
                    provider="dashscope",
                    model=self._model,
                    raw_text=json.dumps(parsed, ensure_ascii=False),
                    content=parsed,
                )
            except httpx.HTTPStatusError as exc:
                response_text = exc.response.text.strip()
                last_error = TextGenerationProviderError(
                    f"DashScope generation failed for step '{task.step}': "
                    f"{exc.response.status_code} {response_text}"
                )
            except httpx.TimeoutException:
                last_error = TextGenerationProviderError(
                    f"DashScope generation failed for step '{task.step}': "
                    f"timed out after {int(effective_timeout)}s"
                )
            except json.JSONDecodeError:
                last_error = TextGenerationProviderError(
                    f"DashScope generation failed for step '{task.step}': invalid JSON"
                )
            except TextGenerationProviderError as exc:
                last_error = exc
            except Exception as exc:
                last_error = TextGenerationProviderError(
                    f"DashScope generation failed for step '{task.step}': {exc}"
                )

            if attempt < self._retry_attempts and self._should_retry(last_error):
                await asyncio.sleep(self._retry_delay)
                continue
            break

        if last_error is None:
            raise TextGenerationProviderError(
                f"DashScope generation failed for step '{task.step}': unknown error"
            )
        raise last_error

    @staticmethod
    def _should_retry(error: Exception) -> bool:
        if isinstance(error, TextGenerationProviderError):
            message = str(error).lower()
            if "invalid json" in message or "not a json object" in message:
                return True
            if "timed out after" in message:
                return True
            if " 429 " in message or " 500 " in message or " 502 " in message:
                return True
            if " 503 " in message or " 504 " in message:
                return True
        return False
