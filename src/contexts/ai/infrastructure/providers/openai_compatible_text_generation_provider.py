"""OpenAI-compatible adapter for structured text generation."""

from __future__ import annotations

import asyncio
import json

import httpx

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationProviderName,
    TextGenerationResult,
    TextGenerationTask,
)


class OpenAICompatibleTextGenerationProvider(TextGenerationProvider):
    """Structured generation provider backed by OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        api_base: str | None = None,
        timeout: int = 30,
        provider_name: TextGenerationProviderName = "openai_compatible",
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required for OpenAI-compatible providers")
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._timeout = timeout
        self._provider_name = provider_name
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            base_url = (self._api_base or "https://api.openai.com/v1").rstrip("/")
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

    def _timeout_for_step(self, task: TextGenerationTask) -> int:
        """Return a longer timeout for heavy generation steps."""
        if task.step in {"chapter_draft", "chapter_revision"}:
            return max(self._timeout, 180)
        return self._timeout

    @staticmethod
    def _should_retry(error: TextGenerationProviderError) -> bool:
        """Decide whether a failed request is worth retrying."""
        message = str(error).lower()
        return (
            "invalid json" in message
            or "timed out" in message
            or " 429 " in message
            or " 500 " in message
            or " 502 " in message
            or " 503 " in message
            or " 504 " in message
        )

    def _build_request_payload(self, task: TextGenerationTask) -> dict[str, object]:
        schema_text = json.dumps(task.response_schema, ensure_ascii=False)
        metadata_text = json.dumps(task.metadata, ensure_ascii=False)
        return {
            "model": self._model,
            "temperature": task.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{task.system_prompt}\n"
                        "Return valid JSON only. "
                        f"Output schema: {schema_text}"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{task.user_prompt}\n"
                        f"Task step: {task.step}\n"
                        f"Metadata: {metadata_text}"
                    ),
                },
            ],
        }

    async def _generate_once(
        self,
        client: httpx.AsyncClient,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        """Perform a single OpenAI-compatible chat-completion request."""
        response = await client.post(
            "/chat/completions",
            json=self._build_request_payload(task),
            timeout=self._timeout_for_step(task),
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise TextGenerationProviderError(
                "OpenAI-compatible response missing choices"
            )

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise TextGenerationProviderError(
                "OpenAI-compatible response choice is not an object"
            )

        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise TextGenerationProviderError(
                "OpenAI-compatible response message is not an object"
            )

        content_text = str(message.get("content", "") or "{}")
        parsed = json.loads(content_text)
        if not isinstance(parsed, dict):
            raise TextGenerationProviderError(
                "OpenAI-compatible response is not a JSON object"
            )
        return TextGenerationResult(
            step=task.step,
            provider=self._provider_name,
            model=self._model,
            raw_text=json.dumps(parsed, ensure_ascii=False),
            content=parsed,
        )

    def _coerce_generation_error(
        self,
        exc: Exception,
        task: TextGenerationTask,
    ) -> TextGenerationProviderError:
        """Normalize transport and parsing failures into provider errors."""
        if isinstance(exc, TextGenerationProviderError):
            return exc
        if isinstance(exc, httpx.HTTPStatusError):
            response_text = exc.response.text.strip()
            return TextGenerationProviderError(
                f"OpenAI-compatible generation failed for step '{task.step}': "
                f"{exc.response.status_code} {response_text}"
            )
        if isinstance(exc, json.JSONDecodeError):
            return TextGenerationProviderError(
                f"OpenAI-compatible generation failed for step '{task.step}': invalid JSON"
            )
        return TextGenerationProviderError(
            f"OpenAI-compatible generation failed for step '{task.step}': {exc}"
        )

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        client = self._get_client()
        last_error: TextGenerationProviderError | None = None

        for attempt in range(1, self._retry_attempts + 1):
            try:
                return await self._generate_once(client, task)
            except (
                httpx.HTTPStatusError,
                httpx.TimeoutException,
                json.JSONDecodeError,
                TextGenerationProviderError,
                httpx.RequestError,
            ) as exc:
                last_error = self._coerce_generation_error(exc, task)

            if attempt < self._retry_attempts and self._should_retry(last_error):
                await asyncio.sleep(self._retry_delay)
                continue
            break

        if last_error is None:
            raise TextGenerationProviderError(
                f"OpenAI-compatible generation failed for step '{task.step}'"
            )
        raise last_error
