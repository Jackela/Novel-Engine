"""
Gemini LLM Client Adapter

Implements ILLMClient for Google's Gemini API.
Provides text generation capabilities for query rewriting and other knowledge services.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article V (SOLID): SRP - Gemini API interaction only

Warzone 4: AI Brain - BRAIN-009A
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import requests
import structlog

from ...application.ports.i_llm_client import LLMRequest, LLMResponse, LLMError

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Default model configuration
DEFAULT_MODEL = "gemini-2.0-flash"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000


class GeminiLLMClient:
    """
    Gemini API client for LLM text generation.

    Implements the ILLMClient protocol using Google's Gemini API.
    Designed for efficient text generation in knowledge services like
    query rewriting and entity extraction.

    Configuration via environment variables:
        - GEMINI_API_KEY: Required API authentication key
        - GEMINI_MODEL: Model name (default: gemini-2.0-flash)

    Attributes:
        _model: Gemini model identifier
        _api_key: Gemini API authentication key
        _base_url: Gemini API endpoint URL

    Example:
        >>> client = GeminiLLMClient(model="gemini-2.0-flash")
        >>> request = LLMRequest(
        ...     system_prompt="Rewrite queries for better search.",
        ...     user_prompt="protagonist motivation"
        ... )
        >>> response = await client.generate(request)
        >>> print(response.text)
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize the Gemini LLM client.

        Args:
            model: Gemini model name (defaults to GEMINI_MODEL env var or gemini-2.0-flash)
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            base_url: Custom API base URL (for testing/proxies)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self._model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")

        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable or api_key parameter is required"
            )

        self._base_url = base_url or (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model}:generateContent"
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate text using the Gemini API.

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

        # Combine system and user prompts
        combined_prompt = self._build_combined_prompt(request)

        # Build request body
        request_body = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }

        log.debug(
            "gemini_generate_start",
            prompt_length=len(combined_prompt),
        )

        try:
            response = await self._make_request(request_body)
            text = self._extract_response_text(response)

            log.debug(
                "gemini_generate_complete",
                response_length=len(text),
            )

            return LLMResponse(
                text=text,
                model=self._model,
                tokens_used=None,  # Gemini doesn't return token count in basic API
            )

        except requests.RequestException as e:
            log.error("gemini_request_failed", error=str(e))
            raise LLMError(f"Gemini API request failed: {e}") from e
        except (KeyError, IndexError, TypeError) as e:
            log.error("gemini_response_parse_failed", error=str(e))
            raise LLMError(f"Failed to parse Gemini response: {e}") from e

    def _build_combined_prompt(self, request: LLMRequest) -> str:
        """
        Build combined prompt from system and user prompts.

        Gemini doesn't have separate system/user message separation,
        so we combine them with clear delimiters.

        Args:
            request: LLMRequest with system and user prompts

        Returns:
            Combined prompt string
        """
        if request.system_prompt and request.user_prompt:
            return f"SYSTEM INSTRUCTIONS:\n{request.system_prompt}\n\nUSER REQUEST:\n{request.user_prompt}"
        elif request.system_prompt:
            return request.system_prompt
        else:
            return request.user_prompt

    async def _make_request(self, request_body: dict) -> dict:
        """
        Make HTTP request to Gemini API.

        Args:
            request_body: Request payload for the API

        Returns:
            Parsed JSON response

        Raises:
            requests.RequestException: On HTTP errors
            LLMError: On API-specific errors
        """
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        # Use synchronous requests for now (can be upgraded to httpx later)
        response = requests.post(
            self._base_url,
            headers=headers,
            json=request_body,
            timeout=60,
        )

        # Handle specific error codes
        if response.status_code == 401:
            raise LLMError("Gemini API authentication failed - check GEMINI_API_KEY")
        elif response.status_code == 429:
            raise LLMError("Gemini API rate limit exceeded")
        elif response.status_code != 200:
            raise LLMError(f"Gemini API error {response.status_code}: {response.text}")

        return response.json()

    def _extract_response_text(self, response_json: dict) -> str:
        """
        Extract text content from Gemini API response.

        Args:
            response_json: Parsed JSON response from Gemini

        Returns:
            Extracted text content

        Raises:
            LLMError: If response structure is invalid
        """
        try:
            return response_json["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Invalid Gemini response structure: {e}")


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
                )

        # Default mock response based on prompt content
        if "rewrite" in combined and "query" in combined:
            return LLMResponse(
                text='["alternative query", "related search"]',
                model="mock-model",
                tokens_used=None,
            )
        elif "expand" in combined:
            return LLMResponse(
                text="expanded version of the prompt",
                model="mock-model",
                tokens_used=None,
            )
        else:
            return LLMResponse(
                text="mock response",
                model="mock-model",
                tokens_used=None,
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
    "MockLLMClient",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_MAX_TOKENS",
]
