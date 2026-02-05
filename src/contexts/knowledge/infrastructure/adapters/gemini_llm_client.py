"""
Gemini LLM Client Adapter

Implements ILLMClient for Google's Gemini API.
Provides text generation capabilities for query rewriting and other knowledge services.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article V (SOLID): SRP - Gemini API interaction only

Warzone 4: AI Brain - BRAIN-009A, BRAIN-025A
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
import structlog

from ...application.ports.i_llm_client import LLMRequest, LLMResponse, LLMError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Default model configuration
DEFAULT_MODEL = "gemini-2.0-flash-exp"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000

# Supported Gemini models
GEMINI_MODELS = {
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.0-flash-exp": "Gemini 2.0 Flash Experimental",
    "gemini-2.0-flash-thinking-exp": "Gemini 2.0 Flash Thinking Experimental",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "gemini-1.5-flash": "Gemini 1.5 Flash",
    "gemini-1.5-flash-8b": "Gemini 1.5 Flash (8B)",
}


class ChatMessage:
    """
    A chat message in Gemini's format.

    Gemini uses a specific chat history format with role and content.
    Valid roles are "user" and "model".

    Attributes:
        role: Message role ("user" or "model")
        content: Text content of the message
    """

    def __init__(self, role: str, content: str):
        """
        Initialize a chat message.

        Args:
            role: Message role ("user" or "model")
            content: Text content of the message

        Raises:
            ValueError: If role is not "user" or "model"
        """
        if role not in ("user", "model"):
            raise ValueError(f"Role must be 'user' or 'model', got '{role}'")
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        """Convert to Gemini API format."""
        return {"role": self.role, "parts": [{"text": self.content}]}


class GeminiLLMClient:
    """
    Gemini API client for LLM text generation.

    Implements the ILLMClient protocol using Google's Gemini API.
    Designed for efficient text generation in knowledge services like
    query rewriting and entity extraction.

    Configuration via environment variables:
        - GEMINI_API_KEY: Required API authentication key
        - GEMINI_MODEL: Model name (default: gemini-2.0-flash-exp)

    Supported models:
        - gemini-2.5-pro: Latest Pro model
        - gemini-2.5-flash: Latest Flash model
        - gemini-2.0-flash-exp: Experimental Flash
        - gemini-1.5-pro: Previous generation Pro
        - gemini-1.5-flash: Previous generation Flash

    Attributes:
        _model: Gemini model identifier
        _api_key: Gemini API authentication key
        _base_url: Gemini API endpoint URL
        _timeout: HTTP request timeout in seconds

    Example (single turn):
        >>> client = GeminiLLMClient(model="gemini-2.5-pro")
        >>> request = LLMRequest(
        ...     system_prompt="Rewrite queries for better search.",
        ...     user_prompt="protagonist motivation"
        ... )
        >>> response = await client.generate(request)
        >>> print(response.text)

    Example (multi-turn with chat history):
        >>> history = [
        ...     ChatMessage("user", "What is the capital of France?"),
        ...     ChatMessage("model", "The capital of France is Paris."),
        ... ]
        >>> request = LLMRequest(
        ...     system_prompt="You are helpful.",
        ...     user_prompt="And what's the population?",
        ... )
        >>> response = await client.generate(request, chat_history=history)
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 60,
    ):
        """
        Initialize the Gemini LLM client.

        Args:
            model: Gemini model name (defaults to GEMINI_MODEL env var or gemini-2.0-flash-exp)
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            base_url: Custom API base URL (for testing/proxies)
            timeout: HTTP request timeout in seconds (default: 60)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self._model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._timeout = timeout

        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable or api_key parameter is required"
            )

        # Build base URL for the specific model
        # Gemini API format: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
        if base_url:
            self._base_url = base_url
        else:
            # Use v1beta for latest models
            self._base_url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model}:generateContent"
            )

    def generate(
        self,
        request: LLMRequest,
        chat_history: list[ChatMessage] | None = None,
    ) -> LLMResponse:
        """
        Generate text using the Gemini API.

        Args:
            request: LLMRequest with system/user prompts and parameters
            chat_history: Optional list of ChatMessage for multi-turn conversations

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
        import asyncio

        async def _generate_async() -> LLMResponse:
            log = logger.bind(model=self._model, temperature=request.temperature)

            # Build contents array with chat history
            contents = self._build_contents(request, chat_history)

            # Build request body
            request_body = {
                "contents": contents,
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                },
            }

            # Add system instruction if provided (Gemini API supports this)
            if request.system_prompt:
                request_body["systemInstruction"] = {
                    "parts": [{"text": request.system_prompt}]
                }

            log.debug(
                "gemini_generate_start",
                prompt_length=len(request.user_prompt),
                has_system_prompt=bool(request.system_prompt),
                chat_history_length=len(chat_history) if chat_history else 0,
            )

            try:
                response = await self._make_request(request_body)
                text, usage = self._extract_response_text(response)

                log.debug(
                    "gemini_generate_complete",
                    response_length=len(text),
                    usage=usage,
                )

                tokens_used = None
                input_tokens = None
                output_tokens = None

                if usage:
                    input_tokens = usage.get("promptTokenCount", 0)
                    output_tokens = usage.get("candidatesTokenCount", 0)
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
                    "gemini_http_error",
                    status_code=e.response.status_code,
                    error=str(e),
                )
                error_message = self._format_http_error(e)
                raise LLMError(error_message) from e
            except httpx.RequestError as e:
                log.error("gemini_request_failed", error=str(e))
                raise LLMError(f"Gemini API request failed: {e}") from e
            except (KeyError, IndexError, TypeError) as e:
                log.error("gemini_response_parse_failed", error=str(e))
                raise LLMError(f"Failed to parse Gemini response: {e}") from e

        try:
            # Try to get the running event loop
            asyncio.get_running_loop()
            # If we're in an async context (running loop exists), we need to run differently
            import concurrent.futures

            # Create a thread to run the async function
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _generate_async(),
                )
                return future.result()
        except RuntimeError:
            # No running event loop, use asyncio.run() directly
            return asyncio.run(_generate_async())

    def _build_contents(
        self,
        request: LLMRequest,
        chat_history: list[ChatMessage] | None = None,
    ) -> list[dict]:
        """
        Build contents array for Gemini API.

        Gemini API format uses an array of content objects with role and parts.

        Args:
            request: LLMRequest with system and user prompts
            chat_history: Optional list of previous messages

        Returns:
            Contents array for Gemini API
        """
        contents = []

        # Add chat history if provided
        if chat_history:
            for msg in chat_history:
                contents.append(msg.to_dict())

        # Add current user message
        contents.append({
            "role": "user",
            "parts": [{"text": request.user_prompt}],
        })

        return contents

    async def _make_request(self, request_body: dict) -> dict:
        """
        Make HTTP request to Gemini API.

        Args:
            request_body: Request payload for the API

        Returns:
            Parsed JSON response

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            httpx.RequestError: On network/connection errors
            LLMError: On API-specific errors
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,  # type: ignore[dict-item]
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._base_url,
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
            return "Gemini API bad request - check request format"
        elif status == 401:
            return "Gemini API authentication failed - check GEMINI_API_KEY"
        elif status == 403:
            return "Gemini API permission denied - check API key permissions"
        elif status == 429:
            return "Gemini API rate limit exceeded"
        elif status >= 500:
            return f"Gemini API server error {status} - please retry"
        else:
            return f"Gemini API error {status}: {error.response.text}"

    def _extract_response_text(self, response_json: dict) -> tuple[str, dict | None]:
        """
        Extract text content and usage from Gemini API response.

        Gemini response format:
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Generated text here"}]
                    },
                    "finishReason": "STOP"
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30
            }
        }

        Args:
            response_json: Parsed JSON response from Gemini

        Returns:
            Tuple of (text content, usage dict or None)

        Raises:
            LLMError: If response structure is invalid
        """
        try:
            # Extract text from candidates
            candidates = response_json.get("candidates", [])
            if not candidates:
                raise LLMError("No candidates in Gemini response")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                raise LLMError("No parts in candidate content")

            text = parts[0].get("text", "")
            if not text:
                raise LLMError("Empty text in Gemini response")

            # Extract usage metadata if available
            usage = response_json.get("usageMetadata")

            return text, usage

        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"Invalid Gemini response structure: {e}") from e


class MockLLMClient:
    """
    Mock LLM client for testing.

    Returns deterministic responses based on input prompts.
    Used for unit testing without requiring actual API calls.

    Example:
        >>> client = MockLLMClient(responses={"test": "mock response"})
        >>> response = await client.generate(
        ...     LLMRequest(system_prompt="", user_prompt="test")
        ... )
        >>> assert response.text == "mock response"
    """

    def __init__(self, responses: dict[str, str] | None = None):
        """
        Initialize the mock client.

        Args:
            responses: Mapping of prompt substrings to responses.
                If a prompt contains the key, return the corresponding value.
        """
        self._responses = responses or {}
        self._call_count = 0
        self._last_request: LLMRequest | None = None

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a mock response.

        Args:
            request: LLMRequest (ignored except for response matching)

        Returns:
            LLMResponse with mock text

        Example:
            >>> client = MockLLMClient(responses={"test": "matched!"})
            >>> response = await client.generate(
            ...     LLMRequest(system_prompt="", user_prompt="this is a test")
            ... )
            >>> assert "matched!" in response.text
        """
        self._call_count += 1
        self._last_request = request

        combined = f"{request.system_prompt} {request.user_prompt}".lower()

        # Find matching response
        for key, response in self._responses.items():
            if key.lower() in combined:
                return LLMResponse(
                    text=response,
                    model="mock-model",
                    tokens_used=None,
                    input_tokens=None,
                    output_tokens=None,
                    raw_usage=None,
                )

        # Default mock response based on prompt content
        if "rewrite" in combined and "query" in combined:
            return LLMResponse(
                text='["alternative query", "related search"]',
                model="mock-model",
                tokens_used=None,
                input_tokens=None,
                output_tokens=None,
                raw_usage=None,
            )
        elif "expand" in combined:
            return LLMResponse(
                text="expanded version of the prompt",
                model="mock-model",
                tokens_used=None,
                input_tokens=None,
                output_tokens=None,
                raw_usage=None,
            )
        else:
            return LLMResponse(
                text="mock response",
                model="mock-model",
                tokens_used=None,
                input_tokens=None,
                output_tokens=None,
                raw_usage=None,
            )

    @property
    def call_count(self) -> int:
        """Get number of times generate() was called."""
        return self._call_count

    @property
    def last_request(self) -> LLMRequest | None:
        """Get the last request received."""
        return self._last_request

    def reset(self) -> None:
        """Reset call counter and last request."""
        self._call_count = 0
        self._last_request = None


__all__ = [
    "GeminiLLMClient",
    "ChatMessage",
    "MockLLMClient",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
    "GEMINI_MODELS",
]
