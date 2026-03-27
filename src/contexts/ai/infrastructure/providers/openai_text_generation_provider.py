"""OpenAI adapter for structured text generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)

if TYPE_CHECKING:
    import openai


class OpenAITextGenerationProvider(TextGenerationProvider):
    """Structured generation provider backed by OpenAI chat completions."""

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
        self._client: openai.AsyncOpenAI | None = None

    def _get_client(self) -> "openai.AsyncOpenAI":
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise TextGenerationProviderError(
                    "openai package is required for OpenAITextGenerationProvider. "
                    "Install it with: pip install openai"
                ) from exc

            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._api_base,
                timeout=self._timeout,
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
            response = await client.chat.completions.create(
                model=self._model,
                temperature=task.temperature,
                response_format={"type": "json_object"},
                messages=[
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
            )
            content_text = response.choices[0].message.content or "{}"
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
        except TextGenerationProviderError:
            raise
        except Exception as exc:
            raise TextGenerationProviderError(
                f"OpenAI generation failed for step '{task.step}': {exc}"
            ) from exc

