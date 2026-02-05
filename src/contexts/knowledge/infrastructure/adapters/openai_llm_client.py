"""
OpenAI GPT LLM Client Adapter

Implements ILLMClient for OpenAI's GPT API.
Provides text generation capabilities for query rewriting and other knowledge services.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article V (SOLID): SRP - OpenAI API interaction only

Warzone 4: AI Brain - BRAIN-026A
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, AsyncIterator

import httpx
import structlog

from ...application.ports.i_llm_client import LLMRequest, LLMResponse, LLMError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Default model configuration
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000

# Supported OpenAI models
OPENAI_MODELS = {
    "gpt-4o": "GPT-4o (Omni multimodal)",
    "gpt-4o-mini": "GPT-4o Mini (compact multimodal)",
    "gpt-4-turbo": "GPT-4 Turbo",
    "gpt-4-turbo-preview": "GPT-4 Turbo Preview",
    "gpt-3.5-turbo": "GPT-3.5 Turbo",
    "gpt-3.5-turbo-16k": "GPT-3.5 Turbo 16K",
}


class OpenAILLMClient:
    """
    OpenAI API client for LLM text generation.

    Implements the ILLMClient protocol using OpenAI's GPT API.
    Designed for efficient text generation in knowledge services like
    query rewriting and entity extraction.

    Configuration via environment variables:
        - OPENAI_API_KEY: Required API authentication key
        - OPENAI_MODEL: Model name (default: gpt-4o-mini)
        - OPENAI_BASE_URL: Custom API base URL (for testing/proxies)

    Supported models:
        - gpt-4o: Latest multimodal model
        - gpt-4o-mini: Compact multimodal model
        - gpt-4-turbo: High-performance model
        - gpt-3.5-turbo: Fast cost-effective model

    Attributes:
        _model: OpenAI model identifier
        _api_key: OpenAI API authentication key
        _base_url: OpenAI API endpoint URL
        _timeout: HTTP request timeout in seconds

    Example (single turn):
        >>> client = OpenAILLMClient(model="gpt-4o-mini")
        >>> request = LLMRequest(
        ...     system_prompt="Rewrite queries for better search.",
        ...     user_prompt="protagonist motivation"
        ... )
        >>> response = await client.generate(request)
        >>> print(response.text)

    Example (streaming):
        >>> async for chunk in client.generate_stream(request):
        ...     print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        """
        Initialize the OpenAI LLM client.

        Args:
            model: OpenAI model name (defaults to OPENAI_MODEL env var or gpt-4o-mini)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            base_url: Custom API base URL (for testing/proxies)
            timeout: HTTP request timeout in seconds (default: 60)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self._model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._timeout = timeout

        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable or api_key parameter is required"
            )

        # OpenAI API base URL
        self._base_url = base_url or os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using the OpenAI API.

        Args:
            request: LLMRequest with system/user prompts and parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMError: If API call fails

        Example:
            >>> response = await client.generate(
            ...     LLMRequest(
            ...         system_prompt="You are a search expert.",
            ...         user_prompt="Rewrite: brave warrior",
            ...         temperature=0.5
            ...     )
            ... )
            >>> print(response.text)
        """
        log = logger.bind(model=self._model, temperature=request.temperature)

        # Build request body for OpenAI API
        request_body = self._build_request_body(request)

        log.debug(
            "openai_generate_start",
            prompt_length=len(request.user_prompt),
            has_system_prompt=bool(request.system_prompt),
        )

        try:
            response = await self._make_request(request_body)
            text, usage = self._extract_response_text(response)

            log.debug(
                "openai_generate_complete",
                response_length=len(text),
                usage=usage,
            )

            tokens_used = None
            input_tokens = None
            output_tokens = None

            if usage:
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                tokens_used = (input_tokens + output_tokens) or None

            return LLMResponse(
                text=text,
                model=str(self._model),
                tokens_used=tokens_used,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                raw_usage=usage,
            )

        except httpx.HTTPStatusError as e:
            log.error(
                "openai_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            error_message = self._format_http_error(e)
            raise LLMError(error_message) from e
        except httpx.RequestError as e:
            log.error("openai_request_failed", error=str(e))
            raise LLMError(f"OpenAI API request failed: {e}") from e
        except (KeyError, IndexError, TypeError) as e:
            log.error("openai_response_parse_failed", error=str(e))
            raise LLMError(f"Failed to parse OpenAI response: {e}") from e

    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate streaming text using the OpenAI API.

        Yields text chunks as they are generated by GPT.
        This provides a better user experience for long generations.

        OpenAI streaming format:
        - Server-Sent Events (SSE) with "data:" prefix
        - Each event is a JSON object with "choices" array
        - Text deltas are in choices[0].delta.content

        Args:
            request: LLMRequest with system/user prompts and parameters

        Yields:
            Text chunks as they are generated

        Raises:
            LLMError: If API call fails

        Example:
            >>> async for chunk in client.generate_stream(request):
            ...     print(chunk, end="", flush=True)
        """
        log = logger.bind(model=self._model, temperature=request.temperature)

        request_body = self._build_request_body(request)
        request_body["stream"] = True  # Enable streaming mode

        log.debug(
            "openai_stream_start",
            prompt_length=len(request.user_prompt),
            has_system_prompt=bool(request.system_prompt),
        )

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",  # type: ignore[dict-item]
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    str(self._base_url),
                    headers=headers,
                    json=request_body,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:].strip()  # Remove "data: " prefix

                        # Skip empty lines and event types
                        if not data_str or data_str == "[DONE]":
                            continue

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and data["choices"]:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue

        except httpx.HTTPStatusError as e:
            log.error(
                "openai_stream_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            error_message = self._format_http_error(e)
            raise LLMError(error_message) from e
        except httpx.RequestError as e:
            log.error("openai_stream_request_failed", error=str(e))
            raise LLMError(f"OpenAI API stream request failed: {e}") from e

    def _build_request_body(self, request: LLMRequest) -> dict:
        """
        Build request body for OpenAI API.

        OpenAI format:
        {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "System instructions"},
                {"role": "user", "content": "User prompt"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        Args:
            request: LLMRequest with system and user prompts

        Returns:
            Request body dict for OpenAI API
        """
        messages = []

        # Add system message if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })

        # Add user message
        messages.append({
            "role": "user",
            "content": request.user_prompt
        })

        return {
            "model": self._model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

    async def _make_request(self, request_body: dict) -> dict:
        """
        Make HTTP request to OpenAI API.

        Args:
            request_body: Request payload for the API

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: On HTTP errors (4xx, 5xx)
            httpx.RequestError: On network/connection errors
            LLMError: On API-specific errors
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",  # type: ignore[dict-item]
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                str(self._base_url),
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]

    def _format_http_error(self, error: httpx.HTTPStatusError) -> str:
        """
        Format HTTP error into a user-friendly message.

        Args:
            error: HTTPStatusError from the API call

        Returns:
            User-friendly error message
        """
        status = error.response.status_code

        if status == 401:
            return "OpenAI API authentication failed - check OPENAI_API_KEY"
        elif status == 429:
            return "OpenAI API rate limit exceeded"
        elif status == 400:
            return "OpenAI API bad request - check request format"
        elif status >= 500:
            return f"OpenAI API server error {status} - please retry"
        else:
            return f"OpenAI API error {status}: {error.response.text}"

    def _extract_response_text(self, response_json: dict) -> tuple[str, dict | None]:
        """
        Extract text content and usage from OpenAI API response.

        OpenAI response format:
        {
            "id": "chatcmpl-xxx",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Generated text here"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        Args:
            response_json: Parsed JSON response from OpenAI

        Returns:
            Tuple of (text content, usage dict or None)

        Raises:
            LLMError: If response structure is invalid
        """
        try:
            # Extract text from choices
            choices = response_json.get("choices", [])
            if not choices:
                raise LLMError("No choices in OpenAI response")

            message = choices[0].get("message", {})
            text = message.get("content", "")

            if not text:
                raise LLMError("Empty response from OpenAI API")

            # Extract usage information if available
            usage = response_json.get("usage")

            return text, usage

        except (KeyError, IndexError) as e:
            raise LLMError(f"Invalid OpenAI response structure: {e}") from e


__all__ = [
    "OpenAILLMClient",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "OPENAI_MODELS",
]
