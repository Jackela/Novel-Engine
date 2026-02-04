"""
Unit tests for Claude LLM Client Adapter

Tests the ClaudeLLMClient implementation of ILLMClient for Anthropic's Claude API.

Warzone 4: AI Brain - BRAIN-024A
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.knowledge.application.ports.i_llm_client import (
    LLMRequest,
    LLMResponse,
    LLMError,
)
from src.contexts.knowledge.infrastructure.adapters.claude_llm_client import (
    ClaudeLLMClient,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    CLAUDE_MODELS,
)


@pytest.fixture
def mock_api_key() -> str:
    """Fixture providing a mock API key."""
    return "test-anthropic-api-key-12345"


@pytest.fixture
def claude_client(mock_api_key: str) -> ClaudeLLMClient:
    """Fixture providing a ClaudeLLMClient instance for testing."""
    return ClaudeLLMClient(api_key=mock_api_key)


@pytest.fixture
def sample_claude_response() -> dict:
    """Fixture providing a sample Claude API response."""
    return {
        "id": "msg_123abc",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "This is a generated response from Claude.",
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 25,
        },
    }


@pytest.fixture
def sample_claude_response_no_usage() -> dict:
    """Fixture providing a Claude API response without usage info."""
    return {
        "id": "msg_456def",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "Response without usage tracking.",
            }
        ],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
    }


class TestClaudeLLMClientInit:
    """Tests for ClaudeLLMClient initialization."""

    def test_init_with_api_key(self, mock_api_key: str) -> None:
        """Test initialization with explicit API key."""
        # Clear any existing env vars to get default base URL
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": mock_api_key}, clear=False):
            # Remove ANTHROPIC_BASE_URL if it exists
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            client = ClaudeLLMClient(api_key=mock_api_key)
            assert client._api_key == mock_api_key
            assert client._model == DEFAULT_MODEL
            assert client._timeout == 60
            assert client._base_url == "https://api.anthropic.com/v1/messages"

    def test_init_with_custom_model(self, mock_api_key: str) -> None:
        """Test initialization with custom model."""
        client = ClaudeLLMClient(
            api_key=mock_api_key,
            model="claude-3-opus-20240229",
        )
        assert client._model == "claude-3-opus-20240229"

    def test_init_with_custom_timeout(self, mock_api_key: str) -> None:
        """Test initialization with custom timeout."""
        client = ClaudeLLMClient(api_key=mock_api_key, timeout=120)
        assert client._timeout == 120

    def test_init_with_custom_base_url(self, mock_api_key: str) -> None:
        """Test initialization with custom base URL."""
        client = ClaudeLLMClient(
            api_key=mock_api_key,
            base_url="https://custom.api.com/v1/messages",
        )
        assert client._base_url == "https://custom.api.com/v1/messages"

    def test_init_without_api_key_raises_error(self) -> None:
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                ClaudeLLMClient()

    def test_init_from_env_var(self) -> None:
        """Test initialization from environment variable."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "env-api-key-123"},
        ):
            client = ClaudeLLMClient()
            assert client._api_key == "env-api-key-123"

    def test_init_model_from_env_var(self) -> None:
        """Test model selection from environment variable."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "ANTHROPIC_MODEL": "claude-3-opus-20240229",
            },
        ):
            client = ClaudeLLMClient()
            assert client._model == "claude-3-opus-20240229"

    def test_base_url_from_env_var(self) -> None:
        """Test base URL from environment variable."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "ANTHROPIC_BASE_URL": "https://proxy.example.com/v1/messages",
            },
        ):
            client = ClaudeLLMClient()
            assert client._base_url == "https://proxy.example.com/v1/messages"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        assert DEFAULT_MODEL == "claude-3-5-sonnet-20241022"
        assert DEFAULT_TEMPERATURE == 0.7
        assert DEFAULT_MAX_TOKENS == 1000

    def test_claude_models_dict(self) -> None:
        """Test CLAUDE_MODELS contains expected models."""
        assert "claude-3-5-sonnet-20241022" in CLAUDE_MODELS
        assert "claude-3-5-haiku-20241022" in CLAUDE_MODELS
        assert "claude-3-opus-20240229" in CLAUDE_MODELS
        assert "claude-3-sonnet-20240229" in CLAUDE_MODELS
        assert "claude-3-haiku-20240307" in CLAUDE_MODELS


class TestBuildRequestBody:
    """Tests for _build_request_body method."""

    def test_build_request_with_system_prompt(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test building request body with system prompt."""
        request = LLMRequest(
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello, Claude!",
            temperature=0.5,
            max_tokens=500,
        )

        body = claude_client._build_request_body(request)

        assert body["model"] == claude_client._model
        assert body["temperature"] == 0.5
        assert body["max_tokens"] == 500
        assert body["system"] == "You are a helpful assistant."
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Hello, Claude!"

    def test_build_request_without_system_prompt(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test building request body without system prompt."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Just user prompt.",
        )

        body = claude_client._build_request_body(request)

        assert "system" not in body
        assert body["messages"][0]["content"] == "Just user prompt."

    def test_build_request_with_default_params(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test building request with default parameters."""
        request = LLMRequest(
            system_prompt="System",
            user_prompt="User",
        )

        body = claude_client._build_request_body(request)

        assert body["temperature"] == DEFAULT_TEMPERATURE
        assert body["max_tokens"] == DEFAULT_MAX_TOKENS


class TestExtractResponseText:
    """Tests for _extract_response_text method."""

    def test_extract_text_from_valid_response(
        self,
        claude_client: ClaudeLLMClient,
        sample_claude_response: dict,
    ) -> None:
        """Test extracting text from valid Claude response."""
        text, usage = claude_client._extract_response_text(sample_claude_response)

        assert text == "This is a generated response from Claude."
        assert usage == {"input_tokens": 10, "output_tokens": 25}

    def test_extract_text_without_usage(
        self,
        claude_client: ClaudeLLMClient,
        sample_claude_response_no_usage: dict,
    ) -> None:
        """Test extracting text when usage info is missing."""
        text, usage = claude_client._extract_response_text(
            sample_claude_response_no_usage
        )

        assert text == "Response without usage tracking."
        assert usage is None

    def test_extract_text_from_multi_block_response(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test extracting text from response with multiple content blocks."""
        response = {
            "id": "msg_789",
            "type": "message",
            "content": [
                {"type": "text", "text": "First part. "},
                {"type": "text", "text": "Second part."},
            ],
            "model": "claude-3-5-sonnet-20241022",
        }

        text, usage = claude_client._extract_response_text(response)

        assert text == "First part. Second part."

    def test_extract_text_missing_content_key_raises_error(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test that missing content key raises LLMError."""
        invalid_response = {
            "id": "msg_error",
            "type": "message",
            "model": "claude-3-5-sonnet-20241022",
        }

        with pytest.raises(LLMError, match="Invalid Claude response"):
            claude_client._extract_response_text(invalid_response)

    def test_extract_empty_content_raises_error(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test that empty content raises LLMError."""
        empty_response = {
            "id": "msg_empty",
            "type": "message",
            "content": [],
            "model": "claude-3-5-sonnet-20241022",
        }

        with pytest.raises(LLMError, match="Empty response"):
            claude_client._extract_response_text(empty_response)


class TestFormatHttpError:
    """Tests for _format_http_error method."""

    @pytest.mark.asyncio
    async def test_format_401_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test formatting 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = MagicMock()
        error.response = mock_response

        message = claude_client._format_http_error(error)
        assert "authentication failed" in message.lower()

    @pytest.mark.asyncio
    async def test_format_429_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test formatting 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit"

        error = MagicMock()
        error.response = mock_response

        message = claude_client._format_http_error(error)
        assert "rate limit" in message.lower()

    @pytest.mark.asyncio
    async def test_format_500_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test formatting 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        error = MagicMock()
        error.response = mock_response

        message = claude_client._format_http_error(error)
        assert "server error" in message.lower()

    @pytest.mark.asyncio
    async def test_format_unknown_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test formatting unknown error code."""
        mock_response = MagicMock()
        mock_response.status_code = 418
        mock_response.text = "I'm a teapot"

        error = MagicMock()
        error.response = mock_response

        message = claude_client._format_http_error(error)
        assert "418" in message


class TestGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        claude_client: ClaudeLLMClient,
        sample_claude_response: dict,
    ) -> None:
        """Test successful text generation."""
        request = LLMRequest(
            system_prompt="You are a test assistant.",
            user_prompt="Say hello",
            temperature=0.5,
            max_tokens=100,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_claude_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await claude_client.generate(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "This is a generated response from Claude."
            assert response.model == claude_client._model
            assert response.tokens_used == 35  # 10 + 25

            # Verify the request was made correctly
            call_args = mock_client.post.call_args
            assert call_args is not None
            assert "json" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_generate_without_usage(
        self,
        claude_client: ClaudeLLMClient,
        sample_claude_response_no_usage: dict,
    ) -> None:
        """Test generation when usage info is not returned."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_claude_response_no_usage
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = await claude_client.generate(request)

            assert response.text == "Response without usage tracking."
            assert response.tokens_used is None

    @pytest.mark.asyncio
    async def test_generate_401_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test generation with 401 authentication error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            # Create proper HTTPStatusError
            from httpx import HTTPStatusError

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            error = HTTPStatusError(
                "Authentication failed",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="authentication failed"):
                await claude_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_429_error(self, claude_client: ClaudeLLMClient) -> None:
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
                await claude_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_network_error(self, claude_client: ClaudeLLMClient) -> None:
        """Test generation with network error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            from httpx import RequestError

            error = RequestError("Network connection failed")
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="request failed"):
                await claude_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_invalid_response_structure(
        self,
        claude_client: ClaudeLLMClient,
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

            with pytest.raises(LLMError, match="Invalid Claude response"):
                await claude_client.generate(request)


class TestGenerateStream:
    """Tests for the generate_stream method - BRAIN-024B."""

    @pytest.mark.asyncio
    async def test_generate_stream_success(
        self,
        claude_client: ClaudeLLMClient,
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
            'data: {"type":"message_start","message":{"id":"msg_123","role":"assistant"}}',
            'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hello"}}',
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" world"}}',
            'data: {"type":"content_block_stop","index":0}',
            'data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":2}}',
            'data: {"type":"message_stop"}',
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        # Create an async iterator for the stream
        async def aiter_lines():
            for event in stream_events:
                yield event

        mock_response.aiter_lines = aiter_lines

        # Create a mock stream context manager
        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Collect all chunks
            chunks = []
            async for chunk in claude_client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_generate_stream_handles_empty_lines(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test that streaming handles empty lines gracefully."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        stream_events = [
            "",
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Response"}}',
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
            async for chunk in claude_client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Response"]

    @pytest.mark.asyncio
    async def test_generate_stream_401_error(self, claude_client: ClaudeLLMClient) -> None:
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
                async for chunk in claude_client.generate_stream(request):
                    chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_generate_stream_network_error(self, claude_client: ClaudeLLMClient) -> None:
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
                async for chunk in claude_client.generate_stream(request):
                    chunks.append(chunk)

    @pytest.mark.asyncio
    async def test_generate_stream_handles_malformed_json(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test that streaming handles malformed JSON gracefully."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        stream_events = [
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Valid"}}',
            'data: {invalid json here',  # Malformed JSON - should be skipped
            'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" text"}}',
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
            async for chunk in claude_client.generate_stream(request):
                chunks.append(chunk)

            # Should collect valid chunks and skip malformed JSON
            assert chunks == ["Valid", " text"]


class TestClaudeLLMClientIntegration:
    """Integration-style tests for ClaudeLLMClient."""

    def test_claude_models_supported(self) -> None:
        """Test that all expected Claude models are defined."""
        expected_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ]
        for model in expected_models:
            assert model in CLAUDE_MODELS

    def test_claude_implements_illm_client_protocol(
        self,
        claude_client: ClaudeLLMClient,
    ) -> None:
        """Test that ClaudeLLMClient can be used as ILLMClient."""
        from src.contexts.knowledge.application.ports.i_llm_client import ILLMClient

        # Protocol check - verify the interface is implemented
        assert hasattr(claude_client, "generate")
        assert callable(claude_client.generate)

        # Verify generate method has correct signature
        import inspect
        sig = inspect.signature(claude_client.generate)
        assert 'request' in sig.parameters
