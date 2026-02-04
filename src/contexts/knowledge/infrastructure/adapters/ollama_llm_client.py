"""
Ollama LLM Client Adapter

Implements ILLMClient for Ollama's local LLM API.
Provides text generation capabilities for local model inference.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article V (SOLID): SRP - Ollama API interaction only

Warzone 4: AI Brain - BRAIN-027A
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
DEFAULT_MODEL = "llama3.2"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# Default Ollama base URL
DEFAULT_BASE_URL = "http://localhost:11434"

# Supported Ollama models
OLLAMA_MODELS = {
    "llama3.2": "Llama 3.2 (70B parameters)",
    "llama3.1": "Llama 3.1 (8B parameters)",
    "llama3": "Llama 3 (Meta Llama 3)",
    "llama3:latest": "Llama 3 Latest",
    "mistral": "Mistral 7B",
    "mistral:latest": "Mistral Latest",
    "phi3": "Phi-3 (3.8B parameters)",
    "phi3:latest": "Phi-3 Latest",
    "gemma2:2b": "Gemma 2 2B",
    "gemma2:9b": "Gemma 2 9B",
    "qwen2.5:3b": "Qwen2.5 3B",
    "qwen2.5:7b": "Qwen2.5 7B",
}


class OllamaLLMClient:
    """
    Ollama API client for local LLM text generation.

    Implements the ILLMClient protocol using Ollama's local API.
    Designed for local inference with models like Llama 3, Mistral, and Phi-3.

    Configuration via environment variables:
        - OLLAMA_API_KEY: Optional API key (if Ollama requires auth)
        - OLLAMA_MODEL: Model name (default: llama3.2)
        - OLLAMA_BASE_URL: API base URL (default: http://localhost:11434)

    Supported models:
        - llama3.2: Meta Llama 3.2 (70B)
        - llama3.1: Meta Llama 3.1 (8B)
        - mistral: Mistral 7B
        - phi3: Microsoft Phi-3
        - And more (see OLLAMA_MODELS)

    Attributes:
        _model: Ollama model identifier
        _api_key: Ollama API authentication key (optional)
        _base_url: Ollama API endpoint URL
        _timeout: HTTP request timeout in seconds

    Example:
        >>> client = OllamaLLMClient(model="llama3.2")
        >>> request = LLMRequest(
        ...     system_prompt="You are a helpful assistant.",
        ...     user_prompt="What is 2+2?"
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
        timeout: int = 120,  # Longer timeout for local inference
    ):
        """
        Initialize the Ollama LLM client.

        Args:
            model: Ollama model name (defaults to OLLAMA_MODEL env var or llama3.2)
            api_key: Ollama API key (optional, defaults to OLLAMA_API_KEY env var)
            base_url: Custom API base URL (default: http://localhost:11434)
            timeout: HTTP request timeout in seconds (default: 120 for local inference)

        Raises:
            ValueError: If base URL is not provided and not in environment
        """
        self._model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("OLLAMA_API_KEY", "")
        self._timeout = timeout

        # Ollama base URL - required
        self._base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", DEFAULT_BASE_URL
        )

        # Normalize base URL (remove trailing slash)
        if self._base_url:
            self._base_url = self._base_url.rstrip("/")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using the Ollama API.

        Args:
            request: LLMRequest with system/user prompts and parameters

        Returns:
            LLMResponse with generated text and metadata

        Raises:
            LLMError: If API call fails

        Example:
            >>> response = await client.generate(
            ...     LLMRequest(
            ...         system_prompt="You are helpful.",
            ...         user_prompt="What is 2+2?",
            ...         temperature=0.5
            ...     )
            ... )
            >>> print(response.text)
        """
        log = logger.bind(model=self._model, temperature=request.temperature)

        # Build request body for Ollama API
        request_body = self._build_request_body(request)

        log.debug(
            "ollama_generate_start",
            prompt_length=len(request.user_prompt),
            has_system_prompt=bool(request.system_prompt),
        )

        try:
            response = await self._make_request(request_body)
            text, usage = self._extract_response_text(response)

            log.debug(
                "ollama_generate_complete",
                response_length=len(text),
                usage=usage,
            )

            tokens_used = None
            if usage:
                tokens_used = (
                    usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
                ) or None

            return LLMResponse(
                text=text,
                model=str(self._model),
                tokens_used=tokens_used,
            )

        except httpx.HTTPStatusError as e:
            log.error(
                "ollama_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            error_message = self._format_http_error(e)
            raise LLMError(error_message) from e
        except httpx.RequestError as e:
            log.error("ollama_request_failed", error=str(e))
            raise LLMError(f"Ollama API request failed: {e}") from e
        except (KeyError, IndexError, TypeError) as e:
            log.error("ollama_response_parse_failed", error=str(e))
            raise LLMError(f"Failed to parse Ollama response: {e}") from e

    async def generate_stream(
        self, request: LLMRequest
    ) -> AsyncIterator[str]:
        """
        Generate streaming text using the Ollama API.

        Ollama streaming format:
        - Line-by-line JSON responses
        - Each line is a complete JSON object with "response" field
        - Text is in response field

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
            "ollama_stream_start",
            prompt_length=len(request.user_prompt),
            has_system_prompt=bool(request.system_prompt),
        )

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/generate",
                    headers=headers,
                    json=request_body,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            if "response" in data:
                                content = data["response"]
                                # Handle streaming response format
                                if isinstance(content, str):
                                    yield content
                                elif isinstance(content, list) and content:
                                    # Some Ollama versions return array of content parts
                                    for part in content:
                                        if isinstance(part, dict) and "content" in part:
                                            yield part["content"]
                                        elif isinstance(part, str):
                                            yield part
                        except json.JSONDecodeError:
                            log.warning("ollama_stream_parse_error", line=line[:100])
                            continue

        except httpx.HTTPStatusError as e:
            log.error(
                "ollama_stream_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            error_message = self._format_http_error(e)
            raise LLMError(error_message) from e
        except httpx.RequestError as e:
            log.error("ollama_stream_request_failed", error=str(e))
            raise LLMError(f"Ollama API stream request failed: {e}") from e

    async def check_connection(self) -> dict:
        """
        Check if Ollama server is accessible and list available models.

        Returns:
            Dictionary with connection status and available models

        Raises:
            LLMError: If connection check fails
        """
        log = logger.bind(base_url=self._base_url)

        try:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"  # type: ignore[dict-item]

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base_url}/api/tags",
                    headers=headers,
                )

                response.raise_for_status()
                data = response.json()

                models = data.get("models", [])

                log.info(
                    "ollama_connection_success",
                    model_count=len(models),
                )

                return {
                    "status": "connected",
                    "base_url": self._base_url,
                    "model_count": len(models),
                    "available_models": [m.get("name", m.get("model", "")) for m in models],
                }

        except httpx.HTTPStatusError as e:
            log.error("ollama_connection_http_error", status_code=e.response.status_code)
            if e.response.status_code == 404:
                raise LLMError("Ollama API not found - check if Ollama is running") from e
            else:
                raise LLMError(f"Ollama connection error {e.response.status_code}") from e
        except httpx.RequestError as e:
            log.error("ollama_connection_failed", error=str(e))
            raise LLMError(f"Cannot connect to Ollama at {self._base_url}: {e}") from e

    def _build_request_body(self, request: LLMRequest) -> dict:
        """
        Build request body for Ollama API.

        Ollama format:
        {
            "model": "llama3.2",
            "prompt": "User prompt here",
            "system": "System instructions here",  // Optional
            "stream": false,
            "options": {
                "temperature": 0.7,
                "num_predict": 1000
            }
        }

        Args:
            request: LLMRequest with system and user prompts

        Returns:
            Request body dict for Ollama API
        """
        body = {
            "model": self._model,
            "prompt": request.user_prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }

        # Add system prompt if provided
        if request.system_prompt:
            body["system"] = request.system_prompt

        return body

    async def _make_request(self, request_body: dict) -> dict:
        """
        Make HTTP request to Ollama API.

        Args:
            request_body: Request payload for the API

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            httpx.RequestError: On network/connection errors
            LLMError: On API-specific errors
        """
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/generate",
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

        if status == 400:
            return "Ollama API bad request - check request format"
        elif status == 404:
            return "Ollama API endpoint not found - check Ollama version"
        elif status >= 500:
            return f"Ollama API server error {status} - check Ollama logs"
        else:
            return f"Ollama API error {status}: {error.response.text}"

    def _extract_response_text(self, response_json: dict) -> tuple[str, dict | None]:
        """
        Extract text content and usage from Ollama API response.

        Ollama response format (non-streaming):
        {
            "model": "llama3.2",
            "created_at": "2024-01-01T00:00:00.000Z",
            "response": "Generated text here",
            "done": true,
            "context": [],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20
            }
        }

        Args:
            response_json: Parsed JSON response from Ollama

        Returns:
            Tuple of (text content, usage dict or None)

        Raises:
            LLMError: If response structure is invalid
        """
        try:
            # Ollama puts text in "response" field
            text = response_json.get("response", "")

            if not text:
                raise LLMError("Empty response from Ollama API")

            # Extract usage information if available
            usage = response_json.get("usage")

            return text, usage

        except (KeyError, TypeError) as e:
            raise LLMError(f"Invalid Ollama response structure: {e}") from e


__all__ = [
    "OllamaLLMClient",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "OLLAMA_MODELS",
]
