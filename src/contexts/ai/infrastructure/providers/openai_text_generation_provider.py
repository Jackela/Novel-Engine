"""OpenAI adapter for structured text generation."""

from __future__ import annotations

import json

import httpx

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)


class OpenAITextGenerationProvider(TextGenerationProvider):
    """Structured generation provider backed by OpenAI-compatible chat completions."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        api_base: str | None = None,
        timeout: int = 30,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._timeout = timeout
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

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        schema_text = json.dumps(task.response_schema, ensure_ascii=False)
        metadata_text = json.dumps(task.metadata, ensure_ascii=False)
        client = self._get_client()

        try:
            response = await client.post(
                "/chat/completions",
                json={
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
                },
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices")
            if not isinstance(choices, list) or not choices:
                raise TextGenerationProviderError(
                    "OpenAI response missing choices"
                )

            first_choice = choices[0]
            if not isinstance(first_choice, dict):
                raise TextGenerationProviderError(
                    "OpenAI response choice is not an object"
                )

            message = first_choice.get("message", {})
            if not isinstance(message, dict):
                raise TextGenerationProviderError(
                    "OpenAI response message is not an object"
                )

            content_text = str(message.get("content", "") or "{}")
            parsed = json.loads(content_text)
            if not isinstance(parsed, dict):
                raise TextGenerationProviderError(
                    "OpenAI response is not a JSON object"
                )
            return TextGenerationResult(
                step=task.step,
                provider="openai",
                model=self._model,
                raw_text=content_text,
                content=parsed,
            )
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text.strip()
            raise TextGenerationProviderError(
                f"OpenAI generation failed for step '{task.step}': "
                f"{exc.response.status_code} {response_text}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise TextGenerationProviderError(
                f"OpenAI generation failed for step '{task.step}': invalid JSON"
            ) from exc
        except TextGenerationProviderError:
            raise
        except Exception as exc:
            raise TextGenerationProviderError(
                f"OpenAI generation failed for step '{task.step}': {exc}"
            ) from exc
