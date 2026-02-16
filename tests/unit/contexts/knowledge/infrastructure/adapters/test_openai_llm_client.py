"""
Unit tests for OpenAI LLM Client Adapter

Tests the OpenAILLMClient implementation of ILLMClient for OpenAI's GPT API.

Warzone 4: AI Brain - BRAIN-026A
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import pytest

from src.contexts.knowledge.application.ports.i_llm_client import (
    LLMError,
    LLMRequest,
    LLMResponse,
)
from src.contexts.knowledge.infrastructure.adapters.openai_llm_client import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    OPENAI_MODELS,
    OpenAILLMClient,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_api_key() -> str:
    """Fixture providing a mock API key."""
    return "test-openai-api-key-12345"


@pytest.fixture
def openai_client(mock_api_key: str) -> OpenAILLMClient:
    """Fixture providing an OpenAILLMClient instance for testing."""
    return OpenAILLMClient(api_key=mock_api_key)


@pytest.fixture
def sample_openai_response() -> dict:
    """Fixture providing a sample OpenAI API response."""
    return {
        "id": "chatcmpl-123abc",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a generated response from GPT-4.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


@pytest.fixture
def sample_openai_response_no_usage() -> dict:
    """Fixture providing an OpenAI API response without usage info."""
    return {
        "id": "chatcmpl-456def",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Response without usage tracking.",
                },
                "finish_reason": "stop",
            }
        ],
    }


class TestOpenAILLMClientInit:
    """Tests for OpenAILLMClient initialization."""

    def test_init_with_api_key(self, mock_api_key: str) -> None:
        """Test initialization with explicit API key."""
        client = OpenAILLMClient(api_key=mock_api_key)
        assert client._api_key == mock_api_key
        assert client._model == DEFAULT_MODEL
        assert client._timeout == 60
        assert urlparse(client._base_url).hostname == "api.openai.com"

    def test_init_with_custom_model(self, mock_api_key: str) -> None:
        """Test initialization with custom model."""
        client = OpenAILLMClient(
            api_key=mock_api_key,
            model="gpt-4o",
        )
        assert client._model == "gpt-4o"

    def test_init_with_custom_timeout(self, mock_api_key: str) -> None:
        """Test initialization with custom timeout."""
        client = OpenAILLMClient(api_key=mock_api_key, timeout=120)
        assert client._timeout == 120

    def test_init_with_custom_base_url(self, mock_api_key: str) -> None:
        """Test initialization with custom base URL."""
        client = OpenAILLMClient(
            api_key=mock_api_key,
            base_url="https://custom.api.com/v1/chat/completions",
        )
        assert client._base_url == "https://custom.api.com/v1/chat/completions"

    def test_init_without_api_key_raises_error(self) -> None:
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAILLMClient()

    def test_init_from_env_var(self) -> None:
        """Test initialization from environment variable."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "env-api-key-123"},
        ):
            client = OpenAILLMClient()
            assert client._api_key == "env-api-key-123"

    def test_init_model_from_env_var(self) -> None:
        """Test model selection from environment variable."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_MODEL": "gpt-4o",
            },
        ):
            client = OpenAILLMClient()
            assert client._model == "gpt-4o"

    def test_base_url_from_env_var(self) -> None:
        """Test base URL from environment variable."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "test-key",
                "OPENAI_BASE_URL": "https://proxy.example.com/v1/chat/completions",
            },
        ):
            client = OpenAILLMClient()
            assert client._base_url == "https://proxy.example.com/v1/chat/completions"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        assert DEFAULT_MODEL == "gpt-4o-mini"
        assert DEFAULT_TEMPERATURE == 0.7
        assert DEFAULT_MAX_TOKENS == 1000

    def test_openai_models_dict(self) -> None:
        """Test OPENAI_MODELS contains expected models."""
        assert "gpt-4o" in OPENAI_MODELS
        assert "gpt-4o-mini" in OPENAI_MODELS
        assert "gpt-4-turbo" in OPENAI_MODELS
        assert "gpt-3.5-turbo" in OPENAI_MODELS


class TestBuildRequestBody:
    """Tests for _build_request_body method."""

    def test_build_request_with_system_prompt(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test building request body with system prompt."""
        request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello, GPT!",
            temperature=0.5,
            max_tokens=500,
        )

        body = openai_client._build_request_body(request)

        assert body["model"] == openai_client._model
        assert body["temperature"] == 0.5
        assert body["max_tokens"] == 500
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][0]["content"] == "You are a helpful assistant."
        assert body["messages"][1]["role"] == "user"
        assert body["messages"][1]["content"] == "Hello, GPT!"

    def test_build_request_without_system_prompt(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test building request body without system prompt."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Just user prompt.",
        )

        body = openai_client._build_request_body(request)

        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Just user prompt."

    def test_build_request_with_default_params(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test building request with default parameters."""
        request = LLMRequest(
            system_prompt="System",
            user_prompt="User",
        )

        body = openai_client._build_request_body(request)

        assert body["temperature"] == DEFAULT_TEMPERATURE
        assert body["max_tokens"] == DEFAULT_MAX_TOKENS


class TestExtractResponseText:
    """Tests for _extract_response_text method."""

    def test_extract_text_from_valid_response(
        self,
        openai_client: OpenAILLMClient,
        sample_openai_response: dict,
    ) -> None:
        """Test extracting text from valid OpenAI response."""
        text, usage = openai_client._extract_response_text(sample_openai_response)

        assert text == "This is a generated response from GPT-4."
        assert usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    def test_extract_text_without_usage(
        self,
        openai_client: OpenAILLMClient,
        sample_openai_response_no_usage: dict,
    ) -> None:
        """Test extracting text when usage info is missing."""
        text, usage = openai_client._extract_response_text(
            sample_openai_response_no_usage
        )

        assert text == "Response without usage tracking."
        assert usage is None

    def test_extract_text_missing_choices_raises_error(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test that missing choices raises LLMError."""
        invalid_response = {
            "id": "chatcmpl_error",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [],
        }

        with pytest.raises(LLMError, match="No choices"):
            openai_client._extract_response_text(invalid_response)

    def test_extract_empty_content_raises_error(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test that empty content raises LLMError."""
        empty_response = {
            "id": "chatcmpl_empty",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": ""},
                }
            ],
        }

        with pytest.raises(LLMError, match="Empty response"):
            openai_client._extract_response_text(empty_response)


class TestFormatHttpError:
    """Tests for _format_http_error method."""

    @pytest.mark.asyncio
    async def test_format_401_error(self, openai_client: OpenAILLMClient) -> None:
        """Test formatting 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = MagicMock()
        error.response = mock_response

        message = openai_client._format_http_error(error)
        assert "authentication failed" in message.lower()

    @pytest.mark.asyncio
    async def test_format_429_error(self, openai_client: OpenAILLMClient) -> None:
        """Test formatting 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit"

        error = MagicMock()
        error.response = mock_response

        message = openai_client._format_http_error(error)
        assert "rate limit" in message.lower()

    @pytest.mark.asyncio
    async def test_format_500_error(self, openai_client: OpenAILLMClient) -> None:
        """Test formatting 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        error = MagicMock()
        error.response = mock_response

        message = openai_client._format_http_error(error)
        assert "server error" in message.lower()

    @pytest.mark.asyncio
    async def test_format_unknown_error(self, openai_client: OpenAILLMClient) -> None:
        """Test formatting unknown error code."""
        mock_response = MagicMock()
        mock_response.status_code = 418
        mock_response.text = "I'm a teapot"

        error = MagicMock()
        error.response = mock_response

        message = openai_client._format_http_error(error)
        assert "418" in message


class TestGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        openai_client: OpenAILLMClient,
        sample_openai_response: dict,
    ) -> None:
        """Test successful text generation."""
        request = LLMRequest(
            system_prompt="You are a test assistant.",
            user_prompt="Say hello",
            temperature=0.5,
            max_tokens=100,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_openai_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await openai_client.generate(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "This is a generated response from GPT-4."
            assert response.model == openai_client._model
            assert response.tokens_used == 30  # 10 + 20

    @pytest.mark.asyncio
    async def test_generate_without_usage(
        self,
        openai_client: OpenAILLMClient,
        sample_openai_response_no_usage: dict,
    ) -> None:
        """Test generation when usage info is not returned."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_openai_response_no_usage
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await openai_client.generate(request)

            assert response.text == "Response without usage tracking."
            assert response.tokens_used is None

    @pytest.mark.asyncio
    async def test_generate_401_error(self, openai_client: OpenAILLMClient) -> None:
        """Test generation with 401 authentication error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            from httpx import HTTPStatusError

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            error = HTTPStatusError(
                "Authentication failed",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="authentication failed"):
                await openai_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_429_error(self, openai_client: OpenAILLMClient) -> None:
        """Test generation with 429 rate limit error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            from httpx import HTTPStatusError

            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            error = HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="rate limit"):
                await openai_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_network_error(self, openai_client: OpenAILLMClient) -> None:
        """Test generation with network error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            from httpx import RequestError

            error = RequestError("Network connection failed")
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="request failed"):
                await openai_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_invalid_response_structure(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test generation with invalid response structure."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "structure"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="No choices"):
                await openai_client.generate(request)


class TestGenerateStream:
    """Tests for the generate_stream method."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test successful streaming text generation."""
        request = LLMRequest(
            system_prompt="You are a test assistant.",
            user_prompt="Say hello",
            temperature=0.5,
            max_tokens=100,
        )

        # Mock streaming response with SSE events
        stream_events = [
            'data: {"choices":[{"delta":{"role":"assistant"}}],"index":0}',
            'data: {"choices":[{"delta":{"content":"Hello"}}],"index":0}',
            'data: {"choices":[{"delta":{"content":" world"}}],"index":0}',
            "data: [DONE]",
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def aiter_lines():
            for event in stream_events:
                yield event

        mock_response.aiter_lines = aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Collect all chunks
            chunks = []
            async for chunk in openai_client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_generate_stream_handles_empty_lines(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test that streaming handles empty lines gracefully."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        stream_events = [
            "",
            'data: {"choices":[{"delta":{"content":"Response"}}],"index":0}',
            "data: [DONE]",
            "",  # Extra empty line at end
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def aiter_lines():
            for event in stream_events:
                yield event

        mock_response.aiter_lines = aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            chunks = []
            async for chunk in openai_client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Response"]

    @pytest.mark.asyncio
    async def test_generate_stream_401_error(
        self, openai_client: OpenAILLMClient
    ) -> None:
        """Test streaming with 401 authentication error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        error = HTTPStatusError(
            "Authentication failed",
            request=MagicMock(),
            response=mock_response,
        )

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.side_effect = error
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="authentication failed"):
                chunks = []
                async for chunk in openai_client.generate_stream(request):
                    chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_generate_stream_network_error(
        self, openai_client: OpenAILLMClient
    ) -> None:
        """Test streaming with network error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        from httpx import RequestError

        error = RequestError("Network connection failed")

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.side_effect = error
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="request failed"):
                chunks = []
                async for chunk in openai_client.generate_stream(request):
                    chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_generate_stream_handles_malformed_json(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test that streaming handles malformed JSON gracefully."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        stream_events = [
            'data: {"choices":[{"delta":{"content":"Valid"}}],"index":0}',
            "data: {invalid json here",  # Malformed JSON - should be skipped
            'data: {"choices":[{"delta":{"content":" text"}}],"index":0}',
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        async def aiter_lines():
            for event in stream_events:
                yield event

        mock_response.aiter_lines = aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            chunks = []
            async for chunk in openai_client.generate_stream(request):
                chunks.append(chunk)

            # Should collect valid chunks and skip malformed JSON
            assert chunks == ["Valid", " text"]


class TestOpenAILLMClientIntegration:
    """Integration-style tests for OpenAILLMClient."""

    def test_openai_models_supported(self) -> None:
        """Test that all expected OpenAI models are defined."""
        expected_models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ]
        for model in expected_models:
            assert model in OPENAI_MODELS

    def test_openai_implements_illm_client_protocol(
        self,
        openai_client: OpenAILLMClient,
    ) -> None:
        """Test that OpenAILLMClient can be used as ILLMClient."""
        # Protocol check - verify the interface is implemented
        assert hasattr(openai_client, "generate")
        assert callable(openai_client.generate)

        # Verify generate method has correct signature
        import inspect

        sig = inspect.signature(openai_client.generate)
        assert "request" in sig.parameters
