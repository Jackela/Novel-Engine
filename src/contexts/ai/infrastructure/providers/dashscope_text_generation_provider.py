"""DashScope native provider for structured text generation."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.dashscope_json import parse_json_object
from src.contexts.ai.infrastructure.providers.dashscope_payload import (
    coerce_payload_to_schema,
    fallback_payload_from_non_object_response,
    payload_from_response_text,
)
from src.contexts.ai.infrastructure.providers.dashscope_protocol import (
    DashScopeTransport,
    DashScopeTransportMode,
    extract_generation_response_text,
    extract_responses_text,
    extract_usage_tokens,
    resolve_transport,
)


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
    def _resolve_transport(mode: DashScopeTransportMode) -> DashScopeTransport:
        return resolve_transport(mode)

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

    async def aclose(self) -> None:
        """Close the lazily-created HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _build_request_payload(self, task: TextGenerationTask) -> dict[str, Any]:
        return self._transport.build_request_payload(model=self._model, task=task)

    def _endpoint_path(self) -> str:
        return self._transport.endpoint_path()

    def _timeout_for_step(self, task: TextGenerationTask) -> float:
        timeout_floors = {
            "chapter_draft": 180.0,
            "chapter_revision": 180.0,
        }
        return max(
            float(self._timeout), timeout_floors.get(task.step, float(self._timeout))
        )

    _extract_generation_response_text = staticmethod(extract_generation_response_text)
    _extract_responses_text = staticmethod(extract_responses_text)
    _extract_usage_tokens = staticmethod(extract_usage_tokens)
    _parse_json_object = staticmethod(parse_json_object)
    _fallback_payload_from_non_object_response = staticmethod(
        fallback_payload_from_non_object_response
    )

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        client = self._get_client()
        effective_timeout = self._timeout_for_step(task)
        last_error: Exception | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                return await self._generate_once(client, task, effective_timeout)
            except (
                httpx.HTTPStatusError,
                httpx.TimeoutException,
                json.JSONDecodeError,
                TextGenerationProviderError,
                httpx.RequestError,
            ) as exc:
                last_error = self._coerce_generation_error(
                    exc,
                    task=task,
                    effective_timeout=effective_timeout,
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

    async def _generate_once(
        self,
        client: httpx.AsyncClient,
        task: TextGenerationTask,
        effective_timeout: float,
    ) -> TextGenerationResult:
        response = await client.post(
            self._endpoint_path(),
            json=self._build_request_payload(task),
            timeout=effective_timeout,
        )
        response.raise_for_status()
        data = response.json()
        content_text = self._transport.extract_response_text(data)
        prompt_tokens, completion_tokens = extract_usage_tokens(data)
        payload = payload_from_response_text(content_text, task.response_schema)
        parsed = coerce_payload_to_schema(payload, task.response_schema)
        return TextGenerationResult(
            step=task.step,
            provider="dashscope",
            model=self._model,
            raw_text=json.dumps(parsed, ensure_ascii=False),
            content=parsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    @staticmethod
    def _coerce_generation_error(
        exc: Exception,
        *,
        task: TextGenerationTask,
        effective_timeout: float,
    ) -> TextGenerationProviderError:
        if isinstance(exc, httpx.HTTPStatusError):
            response_text = exc.response.text.strip()
            return TextGenerationProviderError(
                f"DashScope generation failed for step '{task.step}': "
                f"{exc.response.status_code} {response_text}"
            )
        if isinstance(exc, httpx.TimeoutException):
            return TextGenerationProviderError(
                f"DashScope generation failed for step '{task.step}': "
                f"timed out after {int(effective_timeout)}s"
            )
        if isinstance(exc, json.JSONDecodeError):
            return TextGenerationProviderError(
                f"DashScope generation failed for step '{task.step}': invalid JSON"
            )
        if isinstance(exc, TextGenerationProviderError):
            return exc
        return TextGenerationProviderError(
            f"DashScope generation failed for step '{task.step}': {exc}"
        )

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
