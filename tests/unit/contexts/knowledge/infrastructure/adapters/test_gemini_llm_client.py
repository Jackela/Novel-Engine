"""
Unit tests for Gemini LLM Client Adapter

Tests the GeminiLLMClient implementation of ILLMClient for Google's Gemini API.

Warzone 4: AI Brain - BRAIN-025A
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.contexts.knowledge.application.ports.i_llm_client import (
    LLMRequest,
    LLMResponse,
    LLMError,
)
from src.contexts.knowledge.infrastructure.adapters.gemini_llm_client import (
    GeminiLLMClient,
    ChatMessage,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    GEMINI_MODELS,
)


@pytest.fixture
def mock_api_key() -> str:
    """Fixture providing a mock API key."""
    return "test-gemini-api-key-12345"


@pytest.fixture
def gemini_client(mock_api_key: str) -> GeminiLLMClient:
    """Fixture providing a GeminiLLMClient instance for testing."""
    return GeminiLLMClient(api_key=mock_api_key)


@pytest.fixture
def sample_gemini_response() -> dict:
    """Fixture providing a sample Gemini API response."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "This is a generated response from Gemini."}]
                },
                "finishReason": "STOP",
                "index": 0,
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 20,
            "totalTokenCount": 30,
        },
    }


@pytest.fixture
def sample_gemini_response_no_usage() -> dict:
    """Fixture providing a Gemini API response without usage info."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Response without usage tracking."}]
                },
                "finishReason": "STOP",
                "index": 0,
            }
        ],
    }


class TestChatMessage:
    """Tests for ChatMessage class."""

    def test_chat_message_user_role(self) -> None:
        """Test creating a user message."""
        msg = ChatMessage("user", "Hello there!")
        assert msg.role == "user"
        assert msg.content == "Hello there!"

    def test_chat_message_model_role(self) -> None:
        """Test creating a model message."""
        msg = ChatMessage("model", "Hi, how can I help?")
        assert msg.role == "model"
        assert msg.content == "Hi, how can I help?"

    def test_chat_message_invalid_role_raises_error(self) -> None:
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Role must be 'user' or 'model'"):
            ChatMessage("system", "System message")

    def test_chat_message_to_dict(self) -> None:
        """Test converting chat message to dict."""
        msg = ChatMessage("user", "Test message")
        expected = {"role": "user", "parts": [{"text": "Test message"}]}
        assert msg.to_dict() == expected


class TestGeminiLLMClientInit:
    """Tests for GeminiLLMClient initialization."""

    def test_init_with_api_key(self, mock_api_key: str) -> None:
        """Test initialization with explicit API key."""
        client = GeminiLLMClient(api_key=mock_api_key)
        assert client._api_key == mock_api_key
        assert client._model == DEFAULT_MODEL
        assert client._timeout == 60
        assert "v1beta/models" in client._base_url

    def test_init_with_custom_model(self, mock_api_key: str) -> None:
        """Test initialization with custom model."""
        client = GeminiLLMClient(
            api_key=mock_api_key,
            model="gemini-2.5-pro",
        )
        assert client._model == "gemini-2.5-pro"

    def test_init_with_custom_timeout(self, mock_api_key: str) -> None:
        """Test initialization with custom timeout."""
        client = GeminiLLMClient(api_key=mock_api_key, timeout=120)
        assert client._timeout == 120

    def test_init_with_custom_base_url(self, mock_api_key: str) -> None:
        """Test initialization with custom base URL."""
        client = GeminiLLMClient(
            api_key=mock_api_key,
            base_url="https://custom.api.com/v1/models/test:generateContent",
        )
        assert client._base_url == "https://custom.api.com/v1/models/test:generateContent"

    def test_init_without_api_key_raises_error(self) -> None:
        """Test that initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiLLMClient()

    def test_init_from_env_var(self) -> None:
        """Test initialization from environment variable."""
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "env-api-key-123"},
        ):
            client = GeminiLLMClient()
            assert client._api_key == "env-api-key-123"

    def test_init_model_from_env_var(self) -> None:
        """Test model selection from environment variable."""
        with patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "GEMINI_MODEL": "gemini-2.5-pro",
            },
        ):
            client = GeminiLLMClient()
            assert client._model == "gemini-2.5-pro"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        assert DEFAULT_MODEL == "gemini-2.0-flash-exp"
        assert DEFAULT_TEMPERATURE == 0.7
        assert DEFAULT_MAX_TOKENS == 1000

    def test_gemini_models_dict(self) -> None:
        """Test GEMINI_MODELS contains expected models."""
        assert "gemini-2.5-pro" in GEMINI_MODELS
        assert "gemini-2.5-flash" in GEMINI_MODELS
        assert "gemini-2.0-flash-exp" in GEMINI_MODELS
        assert "gemini-1.5-pro" in GEMINI_MODELS
        assert "gemini-1.5-flash" in GEMINI_MODELS


class TestBuildContents:
    """Tests for _build_contents method."""

    def test_build_contents_without_history(
        self,
        gemini_client: GeminiLLMClient,
    ) -> None:
        """Test building contents without chat history."""
        request = LLMRequest(
            system_prompt="You are helpful.",
            user_prompt="Hello!",
        )

        contents = gemini_client._build_contents(request)

        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello!"

    def test_build_contents_with_history(
        self,
        gemini_client: GeminiLLMClient,
    ) -> None:
        """Test building contents with chat history."""
        history = [
            ChatMessage("user", "What is 2+2?"),
            ChatMessage("model", "2+2 equals 4."),
        ]
        request = LLMRequest(
            system_prompt="",
            user_prompt="And what is 3+3?",
        )

        contents = gemini_client._build_contents(request, history)

        assert len(contents) == 3
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "What is 2+2?"
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["text"] == "2+2 equals 4."
        assert contents[2]["role"] == "user"
        assert contents[2]["parts"][0]["text"] == "And what is 3+3?"


class TestExtractResponseText:
    """Tests for _extract_response_text method."""

    def test_extract_text_from_valid_response(
        self,
        gemini_client: GeminiLLMClient,
        sample_gemini_response: dict,
    ) -> None:
        """Test extracting text from valid Gemini response."""
        text, usage = gemini_client._extract_response_text(sample_gemini_response)

        assert text == "This is a generated response from Gemini."
        assert usage == {
            "promptTokenCount": 10,
            "candidatesTokenCount": 20,
            "totalTokenCount": 30,
        }

    def test_extract_text_without_usage(
        self,
        gemini_client: GeminiLLMClient,
        sample_gemini_response_no_usage: dict,
    ) -> None:
        """Test extracting text when usage info is missing."""
        text, usage = gemini_client._extract_response_text(
            sample_gemini_response_no_usage
        )

        assert text == "Response without usage tracking."
        assert usage is None

    def test_extract_text_missing_candidates_raises_error(
        self,
        gemini_client: GeminiLLMClient,
    ) -> None:
        """Test that missing candidates raises LLMError."""
        invalid_response = {"candidates": []}

        with pytest.raises(LLMError, match="No candidates"):
            gemini_client._extract_response_text(invalid_response)

    def test_extract_empty_content_raises_error(
        self,
        gemini_client: GeminiLLMClient,
    ) -> None:
        """Test that empty content raises LLMError."""
        empty_response = {
            "candidates": [
                {
                    "content": {"parts": []},
                    "finishReason": "STOP",
                }
            ]
        }

        with pytest.raises(LLMError, match="No parts"):
            gemini_client._extract_response_text(empty_response)


class TestFormatHttpError:
    """Tests for _format_http_error method."""

    @pytest.mark.asyncio
    async def test_format_400_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test formatting 400 bad request error."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        error = MagicMock()
        error.response = mock_response

        message = gemini_client._format_http_error(error)
        assert "bad request" in message.lower()

    @pytest.mark.asyncio
    async def test_format_401_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test formatting 401 authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        error = MagicMock()
        error.response = mock_response

        message = gemini_client._format_http_error(error)
        assert "authentication failed" in message.lower()

    @pytest.mark.asyncio
    async def test_format_403_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test formatting 403 permission error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        error = MagicMock()
        error.response = mock_response

        message = gemini_client._format_http_error(error)
        assert "permission denied" in message.lower()

    @pytest.mark.asyncio
    async def test_format_429_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test formatting 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit"

        error = MagicMock()
        error.response = mock_response

        message = gemini_client._format_http_error(error)
        assert "rate limit" in message.lower()

    @pytest.mark.asyncio
    async def test_format_500_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test formatting 500 server error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"

        error = MagicMock()
        error.response = mock_response

        message = gemini_client._format_http_error(error)
        assert "server error" in message.lower()


class TestGenerate:
    """Tests for the generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        gemini_client: GeminiLLMClient,
        sample_gemini_response: dict,
    ) -> None:
        """Test successful text generation."""
        request = LLMRequest(
            system_prompt="You are a test assistant.",
            user_prompt="Say hello",
            temperature=0.5,
            max_tokens=100,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_gemini_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = gemini_client.generate(request)

            assert isinstance(response, LLMResponse)
            assert response.text == "This is a generated response from Gemini."
            assert response.model == gemini_client._model
            assert response.tokens_used == 30  # 10 + 20

    @pytest.mark.asyncio
    async def test_generate_without_usage(
        self,
        gemini_client: GeminiLLMClient,
        sample_gemini_response_no_usage: dict,
    ) -> None:
        """Test generation when usage info is not returned."""
        request = LLMRequest(
            system_prompt="",
            user_prompt="Test",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_gemini_response_no_usage
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = gemini_client.generate(request)

            assert response.text == "Response without usage tracking."
            assert response.tokens_used is None

    @pytest.mark.asyncio
    async def test_generate_with_chat_history(
        self,
        gemini_client: GeminiLLMClient,
        sample_gemini_response: dict,
    ) -> None:
        """Test generation with chat history."""
        history = [
            ChatMessage("user", "What is 2+2?"),
            ChatMessage("model", "2+2 equals 4."),
        ]
        request = LLMRequest(
            system_prompt="You are helpful.",
            user_prompt="And 3+3?",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = sample_gemini_response
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            response = gemini_client.generate(request, chat_history=history)

            assert isinstance(response, LLMResponse)
            # Verify the request was made with history
            call_args = mock_client.post.call_args
            contents = call_args.kwargs["json"]["contents"]
            assert len(contents) == 3

    @pytest.mark.asyncio
    async def test_generate_401_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test generation with 401 authentication error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            error = httpx.HTTPStatusError(
                "Authentication failed",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="authentication failed"):
                gemini_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_429_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test generation with 429 rate limit error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            error = httpx.HTTPStatusError(
                "Rate limit",
                request=MagicMock(),
                response=mock_response,
            )
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="rate limit"):
                gemini_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_network_error(self, gemini_client: GeminiLLMClient) -> None:
        """Test generation with network error."""
        request = LLMRequest(system_prompt="", user_prompt="Test")

        with patch("httpx.AsyncClient") as mock_client_class:
            error = httpx.RequestError("Network connection failed")
            mock_client = AsyncMock()
            mock_client.post.side_effect = error
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(LLMError, match="request failed"):
                gemini_client.generate(request)

    @pytest.mark.asyncio
    async def test_generate_invalid_response_structure(
        self,
        gemini_client: GeminiLLMClient,
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

            with pytest.raises(LLMError, match="No candidates"):
                gemini_client.generate(request)


class TestGeminiLLMClientIntegration:
    """Integration-style tests for GeminiLLMClient."""

    def test_gemini_models_supported(self) -> None:
        """Test that all expected Gemini models are defined."""
        expected_models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        for model in expected_models:
            assert model in GEMINI_MODELS

    def test_gemini_implements_illm_client_protocol(
        self,
        gemini_client: GeminiLLMClient,
    ) -> None:
        """Test that GeminiLLMClient can be used as ILLMClient."""

        # Protocol check - verify the interface is implemented
        assert hasattr(gemini_client, "generate")
        assert callable(gemini_client.generate)

        # Verify generate method has correct signature
        import inspect
        sig = inspect.signature(gemini_client.generate)
        assert 'request' in sig.parameters
