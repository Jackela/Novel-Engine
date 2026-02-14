"""
Tests for Ollama LLM Client Adapter

Unit tests for OllamaLLMClient covering:
- Client initialization
- Text generation
- Streaming responses
- Connection checking
- Error handling
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, RequestError, Response

from src.contexts.knowledge.application.ports.i_llm_client import (
    LLMError,
    LLMRequest,
)
from src.contexts.knowledge.infrastructure.adapters.ollama_llm_client import (
    DEFAULT_MODEL,
    OLLAMA_MODELS,
    OllamaLLMClient,
)

pytestmark = pytest.mark.unit


class TestOllamaLLMClientInit:
    """Tests for OllamaLLMClient initialization."""

    def test_init_with_defaults(self) -> None:
        """Test client initialization with default values."""
        with patch.dict("os.environ", {}, clear=True):
            client = OllamaLLMClient()

        assert client._model == DEFAULT_MODEL
        assert client._base_url == "http://localhost:11434"
        assert client._timeout == 120

    def test_init_with_custom_model(self) -> None:
        """Test client initialization with custom model."""
        client = OllamaLLMClient(model="mistral")

        assert client._model == "mistral"

    def test_init_with_custom_base_url(self) -> None:
        """Test client initialization with custom base URL."""
        client = OllamaLLMClient(base_url="http://ollama.local:8080")

        assert client._base_url == "http://ollama.local:8080"

    def test_base_url_trailing_slash_removed(self) -> None:
        """Test that trailing slash is removed from base URL."""
        client = OllamaLLMClient(base_url="http://localhost:11434/")

        assert client._base_url == "http://localhost:11434"

    def test_init_with_api_key(self) -> None:
        """Test client initialization with API key."""
        client = OllamaLLMClient(api_key="test-key")

        assert client._api_key == "test-key"

    def test_init_with_timeout(self) -> None:
        """Test client initialization with custom timeout."""
        client = OllamaLLMClient(timeout=300)

        assert client._timeout == 300


class TestGenerate:
    """Tests for the generate method."""

    async def test_generate_basic(self) -> None:
        """Test basic text generation."""
        client = OllamaLLMClient(model="llama3.2")

        mock_response = {
            "model": "llama3.2",
            "response": "This is a test response",
            "done": True,
        }

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.return_value = mock_http_response
            mock_http_response.json.return_value = mock_response

            request = LLMRequest(
                system_prompt="You are helpful.",
                user_prompt="What is 2+2?",
            )

            response = await client.generate(request)

            assert response.text == "This is a test response"
            assert response.model == "llama3.2"
            mock_client.post.assert_called_once()

    async def test_generate_with_usage(self) -> None:
        """Test text generation with usage information."""
        client = OllamaLLMClient(model="llama3.2")

        mock_response = {
            "model": "llama3.2",
            "response": "The answer is 4",
            "done": True,
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        }

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.return_value = mock_http_response
            mock_http_response.json.return_value = mock_response

            request = LLMRequest(
                system_prompt="",
                user_prompt="What is 2+2?",
            )

            response = await client.generate(request)

            assert response.text == "The answer is 4"
            assert response.tokens_used == 15

    async def test_generate_with_temperature(self) -> None:
        """Test text generation with custom temperature."""
        client = OllamaLLMClient(model="llama3.2")

        mock_response = {
            "model": "llama3.2",
            "response": "Response",
            "done": True,
        }

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.return_value = mock_http_response
            mock_http_response.json.return_value = mock_response

            request = LLMRequest(
                system_prompt="",
                user_prompt="Test",
                temperature=0.3,
            )

            await client.generate(request)

            # Verify request body includes temperature
            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            assert request_body["options"]["temperature"] == 0.3

    async def test_generate_with_max_tokens(self) -> None:
        """Test text generation with max tokens limit."""
        client = OllamaLLMClient(model="llama3.2")

        mock_response = {
            "model": "llama3.2",
            "response": "Response",
            "done": True,
        }

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.return_value = mock_http_response
            mock_http_response.json.return_value = mock_response

            request = LLMRequest(
                system_prompt="",
                user_prompt="Test",
                max_tokens=500,
            )

            await client.generate(request)

            # Verify request body includes max tokens
            call_args = mock_client.post.call_args
            request_body = call_args[1]["json"]
            assert request_body["options"]["num_predict"] == 500

    async def test_generate_http_error(self) -> None:
        """Test HTTP error handling."""
        client = OllamaLLMClient(model="llama3.2")

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 500
        mock_http_response.text = "Internal server error"

        error = HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_http_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.side_effect = error

            request = LLMRequest(system_prompt="", user_prompt="Test")

            with pytest.raises(LLMError) as exc_info:
                await client.generate(request)

            assert "Ollama API server error" in str(exc_info.value)

    async def test_generate_request_error(self) -> None:
        """Test network request error handling."""
        client = OllamaLLMClient(model="llama3.2")

        error = RequestError("Connection failed")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.side_effect = error

            request = LLMRequest(system_prompt="", user_prompt="Test")

            with pytest.raises(LLMError) as exc_info:
                await client.generate(request)

            assert "Ollama API request failed" in str(exc_info.value)

    async def test_generate_empty_response(self) -> None:
        """Test handling of empty response."""
        client = OllamaLLMClient(model="llama3.2")

        mock_response = {"model": "llama3.2", "response": "", "done": True}

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.post.return_value = mock_http_response
            mock_http_response.json.return_value = mock_response

            request = LLMRequest(system_prompt="", user_prompt="Test")

            with pytest.raises(LLMError) as exc_info:
                await client.generate(request)

            assert "Empty response" in str(exc_info.value)


class TestGenerateStream:
    """Tests for the generate_stream method."""

    async def test_generate_stream_basic(self) -> None:
        """Test basic streaming generation."""
        client = OllamaLLMClient(model="llama3.2")

        # Ollama sends line-by-line JSON
        lines = [
            json.dumps({"response": "Hello ", "done": False}),
            json.dumps({"response": "world!", "done": True}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            request = LLMRequest(system_prompt="", user_prompt="Say hello")

            chunks = []
            async for chunk in client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Hello ", "world!"]

    async def test_generate_stream_ignores_empty_lines(self) -> None:
        """Test that empty lines are ignored in streaming."""
        client = OllamaLLMClient(model="llama3.2")

        lines = [
            "",  # Empty line
            json.dumps({"response": "Text", "done": False}),
            "",  # Another empty line
            "\n",  # Whitespace
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            request = LLMRequest(system_prompt="", user_prompt="Test")

            chunks = []
            async for chunk in client.generate_stream(request):
                chunks.append(chunk)

            assert chunks == ["Text"]

    async def test_generate_stream_handles_invalid_json(self) -> None:
        """Test that invalid JSON is logged but doesn't break stream."""
        client = OllamaLLMClient(model="llama3.2")

        lines = [
            json.dumps({"response": "Valid ", "done": False}),
            "invalid json",
            json.dumps({"response": "text", "done": True}),
        ]

        async def mock_aiter_lines():
            for line in lines:
                yield line

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.return_value = mock_response
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            request = LLMRequest(system_prompt="", user_prompt="Test")

            chunks = []
            async for chunk in client.generate_stream(request):
                chunks.append(chunk)

            # Should skip invalid JSON and continue
            assert chunks == ["Valid ", "text"]

    async def test_generate_stream_http_error(self) -> None:
        """Test HTTP error handling in streaming."""
        client = OllamaLLMClient(model="llama3.2")

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 500
        mock_http_response.text = "Internal server error"

        error = HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_http_response
        )

        mock_stream_context = AsyncMock()
        mock_stream_context.__aenter__.side_effect = error
        mock_stream_context.__aexit__.return_value = None

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.stream = MagicMock(return_value=mock_stream_context)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            request = LLMRequest(system_prompt="", user_prompt="Test")

            with pytest.raises(LLMError):
                async for _ in client.generate_stream(request):
                    pass


class TestCheckConnection:
    """Tests for the check_connection method."""

    async def test_check_connection_success(self) -> None:
        """Test successful connection check."""
        client = OllamaLLMClient()

        mock_response_data = {
            "models": [
                {"name": "llama3.2"},
                {"name": "mistral"},
                {"name": "phi3"},
            ]
        }

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.get.return_value = mock_http_response

            result = await client.check_connection()

            assert result["status"] == "connected"
            assert result["base_url"] == "http://localhost:11434"
            assert result["model_count"] == 3
            assert result["available_models"] == ["llama3.2", "mistral", "phi3"]

    async def test_check_connection_404_error(self) -> None:
        """Test connection check with 404 error."""
        client = OllamaLLMClient()

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 404

        error = HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_http_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.get.side_effect = error

            with pytest.raises(LLMError) as exc_info:
                await client.check_connection()

            assert "Ollama API not found" in str(exc_info.value)

    async def test_check_connection_request_error(self) -> None:
        """Test connection check with network error."""
        client = OllamaLLMClient()

        error = RequestError("Connection refused")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_client.get.side_effect = error

            with pytest.raises(LLMError) as exc_info:
                await client.check_connection()

            assert "Cannot connect to Ollama" in str(exc_info.value)


class TestBuildRequestBody:
    """Tests for the _build_request_body method."""

    def test_build_request_body_basic(self) -> None:
        """Test building basic request body."""
        client = OllamaLLMClient(model="llama3.2")

        request = LLMRequest(
            system_prompt="",
            user_prompt="Test prompt",
            temperature=0.5,
            max_tokens=1000,
        )

        body = client._build_request_body(request)

        assert body["model"] == "llama3.2"
        assert body["prompt"] == "Test prompt"
        assert body["stream"] is False
        assert body["options"]["temperature"] == 0.5
        assert body["options"]["num_predict"] == 1000
        assert "system" not in body

    def test_build_request_body_with_system(self) -> None:
        """Test building request body with system prompt."""
        client = OllamaLLMClient(model="llama3.2")

        request = LLMRequest(
            system_prompt="You are helpful.",
            user_prompt="Test prompt",
        )

        body = client._build_request_body(request)

        assert body["system"] == "You are helpful."


class TestExtractResponseText:
    """Tests for the _extract_response_text method."""

    def test_extract_response_text_success(self) -> None:
        """Test successful text extraction."""
        client = OllamaLLMClient(model="llama3.2")

        response_json = {
            "model": "llama3.2",
            "response": "Generated text",
            "done": True,
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        text, usage = client._extract_response_text(response_json)

        assert text == "Generated text"
        assert usage == {"prompt_tokens": 10, "completion_tokens": 5}

    def test_extract_response_text_no_usage(self) -> None:
        """Test text extraction without usage info."""
        client = OllamaLLMClient(model="llama3.2")

        response_json = {
            "model": "llama3.2",
            "response": "Generated text",
            "done": True,
        }

        text, usage = client._extract_response_text(response_json)

        assert text == "Generated text"
        assert usage is None

    def test_extract_response_text_empty(self) -> None:
        """Test handling of empty response text."""
        client = OllamaLLMClient(model="llama3.2")

        response_json = {
            "model": "llama3.2",
            "response": "",
            "done": True,
        }

        with pytest.raises(LLMError) as exc_info:
            client._extract_response_text(response_json)

        assert "Empty response" in str(exc_info.value)


class TestFormatHttpError:
    """Tests for the _format_http_error method."""

    def test_format_400_error(self) -> None:
        """Test formatting 400 error."""
        client = OllamaLLMClient(model="llama3.2")

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 400

        error = HTTPStatusError(
            "Bad request", request=MagicMock(), response=mock_http_response
        )

        message = client._format_http_error(error)

        assert "bad request" in message.lower()

    def test_format_404_error(self) -> None:
        """Test formatting 404 error."""
        client = OllamaLLMClient(model="llama3.2")

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 404

        error = HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_http_response
        )

        message = client._format_http_error(error)

        assert "not found" in message.lower()

    def test_format_500_error(self) -> None:
        """Test formatting 500 error."""
        client = OllamaLLMClient(model="llama3.2")

        mock_http_response = MagicMock(spec=Response)
        mock_http_response.status_code = 500

        error = HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_http_response
        )

        message = client._format_http_error(error)

        assert "server error" in message.lower()


class TestSupportedModels:
    """Tests for supported models configuration."""

    def test_ollama_models_dict(self) -> None:
        """Test that OLLAMA_MODELS has expected entries."""
        assert "llama3.2" in OLLAMA_MODELS
        assert "llama3.1" in OLLAMA_MODELS
        assert "mistral" in OLLAMA_MODELS
        assert "phi3" in OLLAMA_MODELS

    def test_default_model_is_supported(self) -> None:
        """Test that DEFAULT_MODEL is in OLLAMA_MODELS."""
        assert DEFAULT_MODEL in OLLAMA_MODELS
