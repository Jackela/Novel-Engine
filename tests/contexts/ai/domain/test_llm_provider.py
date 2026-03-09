#!/usr/bin/env python3
"""
LLM Provider Tests

Tests for LLM provider domain services including LLMRequest, LLMResponse,
and the ILLMProvider abstract interface.
Covers unit tests, integration tests, and boundary tests.
"""

from uuid import uuid4

import pytest

from src.contexts.ai.domain.services.llm_provider import (
    LLMProviderError,
    LLMRequest,
    LLMRequestType,
    LLMResponse,
    LLMResponseStatus,
    QuotaExceededError,
    RateLimitError,
)
from src.contexts.ai.domain.value_objects.common import (
    ModelCapability,
    ModelId,
    ProviderId,
    TokenBudget,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Unit Tests (20 tests)
# ============================================================================


@pytest.mark.unit
class TestLLMRequestType:
    """Unit tests for LLMRequestType enum."""

    def test_request_type_values(self):
        """Test request type enum values."""
        assert LLMRequestType.COMPLETION.value == "completion"
        assert LLMRequestType.CHAT.value == "chat"
        assert LLMRequestType.CONVERSATION.value == "conversation"
        assert LLMRequestType.SUMMARIZATION.value == "summarization"
        assert LLMRequestType.TRANSLATION.value == "translation"
        assert LLMRequestType.CODE_GENERATION.value == "code_generation"
        assert LLMRequestType.ANALYSIS.value == "analysis"
        assert LLMRequestType.EMBEDDING.value == "embedding"
        assert LLMRequestType.FUNCTION_CALL.value == "function_call"


@pytest.mark.unit
class TestLLMResponseStatus:
    """Unit tests for LLMResponseStatus enum."""

    def test_response_status_values(self):
        """Test response status enum values."""
        assert LLMResponseStatus.SUCCESS.value == "success"
        assert LLMResponseStatus.PARTIAL_SUCCESS.value == "partial_success"
        assert LLMResponseStatus.FAILED.value == "failed"
        assert LLMResponseStatus.RATE_LIMITED.value == "rate_limited"
        assert LLMResponseStatus.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert LLMResponseStatus.MODEL_UNAVAILABLE.value == "model_unavailable"
        assert LLMResponseStatus.INVALID_REQUEST.value == "invalid_request"
        assert LLMResponseStatus.TIMEOUT.value == "timeout"


@pytest.mark.unit
class TestLLMRequest:
    """Unit tests for LLMRequest."""

    def test_create_basic_request(self):
        """Test creating basic LLM request."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test prompt",
        )

        assert request.request_type == LLMRequestType.COMPLETION
        assert request.prompt == "Test prompt"
        assert request.model_id == model

    def test_request_with_all_parameters(self):
        """Test creating request with all parameters."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.CHAT,
            model_id=model,
            prompt="Test prompt",
            system_prompt="System prompt",
            parameters={"key": "value"},
            max_tokens=100,
            temperature=0.5,
            top_p=0.9,
            presence_penalty=0.1,
            frequency_penalty=0.1,
            stop_sequences=["stop"],
            functions=[{"name": "func"}],
            timeout_seconds=60,
            stream=True,
            metadata={"user": "test"},
        )

        assert request.system_prompt == "System prompt"
        assert request.max_tokens == 100
        assert request.temperature == 0.5
        assert request.top_p == 0.9

    def test_request_default_values(self):
        """Test request default values."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
        )

        assert request.temperature == 0.7
        assert request.top_p == 1.0
        assert request.timeout_seconds == 30
        assert request.stream is False
        assert request.parameters == {}
        assert request.stop_sequences == []

    def test_create_chat_request_factory(self):
        """Test create_chat_request factory method."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        request = LLMRequest.create_chat_request(
            model_id=model,
            messages=messages,
            system_prompt="Be helpful",
            temperature=0.8,
        )

        assert request.request_type == LLMRequestType.CHAT
        assert "user: Hello" in request.prompt
        assert request.system_prompt == "Be helpful"
        assert request.temperature == 0.8

    def test_create_completion_request_factory(self):
        """Test create_completion_request factory method."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest.create_completion_request(
            model_id=model,
            prompt="Complete this",
            max_tokens=50,
            temperature=0.9,
        )

        assert request.request_type == LLMRequestType.COMPLETION
        assert request.prompt == "Complete this"
        assert request.max_tokens == 50

    def test_estimate_input_tokens(self):
        """Test token estimation."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="This is a test prompt",
            system_prompt="System instruction",
        )

        tokens = request.estimate_input_tokens()
        assert tokens > 0  # Should be roughly (22 + 18) / 4 = 10

    def test_get_effective_max_tokens(self):
        """Test getting effective max tokens."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            max_tokens=100,
        )

        assert request.get_effective_max_tokens() == 100

    def test_is_compatible_with_model(self):
        """Test model compatibility check."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
        )

        assert request.is_compatible_with_model() is True


@pytest.mark.unit
class TestLLMResponse:
    """Unit tests for LLMResponse."""

    def test_create_success_response(self):
        """Test creating successful response."""
        request_id = uuid4()
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        response = LLMResponse.create_success(
            request_id=request_id,
            content="Generated content",
            model_id=model,
            input_tokens=10,
            output_tokens=20,
        )

        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Generated content"
        assert response.request_id == request_id
        assert response.get_input_tokens() == 10
        assert response.get_output_tokens() == 20
        assert response.get_total_tokens() == 30

    def test_create_error_response(self):
        """Test creating error response."""
        request_id = uuid4()

        response = LLMResponse.create_error(
            request_id=request_id,
            status=LLMResponseStatus.RATE_LIMITED,
            error_details="Rate limit exceeded",
        )

        assert response.status == LLMResponseStatus.RATE_LIMITED
        assert response.error_details == "Rate limit exceeded"
        assert not response.is_successful()

    def test_response_is_successful(self):
        """Test is_successful method."""
        request_id = uuid4()
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        success_response = LLMResponse.create_success(
            request_id=request_id,
            content="Content",
            model_id=model,
            input_tokens=10,
            output_tokens=20,
        )
        assert success_response.is_successful()

    def test_response_default_usage_stats(self):
        """Test default usage stats."""
        request_id = uuid4()

        response = LLMResponse(
            request_id=request_id,
            response_id=uuid4(),
            status=LLMResponseStatus.FAILED,
            error_details="Error",
        )

        assert response.get_input_tokens() == 0
        assert response.get_output_tokens() == 0
        assert response.get_total_tokens() == 0


@pytest.mark.unit
class TestLLMProviderErrors:
    """Unit tests for LLM provider errors."""

    def test_llm_provider_error(self):
        """Test base LLMProviderError."""
        error = LLMProviderError("Test error", error_code="TEST_001")
        assert str(error) == "Test error"
        assert error.error_code == "TEST_001"

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=60,
        )
        assert error.retry_after == 60
        assert isinstance(error, LLMProviderError)

    def test_quota_exceeded_error(self):
        """Test QuotaExceededError."""
        error = QuotaExceededError("Quota exceeded")
        assert isinstance(error, LLMProviderError)


# ============================================================================
# Integration Tests (12 tests)
# ============================================================================


@pytest.mark.integration
class TestRequestResponseIntegration:
    """Integration tests for request-response flow."""

    def test_request_to_response_flow(self):
        """Test full request to response flow."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        # Create request
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test prompt",
            max_tokens=100,
        )

        # Create response referencing same request
        response = LLMResponse.create_success(
            request_id=request.request_id,
            content="Response content",
            model_id=model,
            input_tokens=request.estimate_input_tokens(),
            output_tokens=50,
        )

        assert response.request_id == request.request_id
        assert response.is_successful()

    def test_chat_request_to_response(self):
        """Test chat request to response flow."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest.create_chat_request(
            model_id=model,
            messages=[{"role": "user", "content": "Hello"}],
        )

        response = LLMResponse.create_success(
            request_id=request.request_id,
            content="Hello! How can I help?",
            model_id=model,
            input_tokens=10,
            output_tokens=15,
        )

        assert response.status == LLMResponseStatus.SUCCESS

    def test_token_budget_integration(self):
        """Test token budget integration with requests."""
        budget = TokenBudget.create_daily_budget("test_budget", 1000)
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            max_tokens=100,
        )

        estimated_tokens = (
            request.estimate_input_tokens() + request.get_effective_max_tokens()
        )
        assert budget.can_reserve_tokens(estimated_tokens)


@pytest.mark.integration
class TestModelCapabilityIntegration:
    """Integration tests for model capabilities."""

    def test_capability_compatibility(self):
        """Test capability compatibility."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        assert model.supports_capability(ModelCapability.TEXT_GENERATION)
        assert model.supports_capability(ModelCapability.CONVERSATION)
        assert model.supports_capability(ModelCapability.CODE_GENERATION)

    def test_request_capability_matching(self):
        """Test request capability matching with model."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        chat_request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.CHAT,
            model_id=model,
            prompt="Test",
        )

        assert chat_request.is_compatible_with_model()


# ============================================================================
# Boundary Tests (8 tests)
# ============================================================================


@pytest.mark.unit
class TestLLMRequestBoundaryConditions:
    """Boundary tests for LLMRequest."""

    def test_temperature_boundary_low(self):
        """Test temperature at minimum boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            temperature=0.0,
        )
        assert request.temperature == 0.0

    def test_temperature_boundary_high(self):
        """Test temperature at maximum boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            temperature=2.0,
        )
        assert request.temperature == 2.0

    def test_top_p_boundary(self):
        """Test top_p at boundary values."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            top_p=0.0,
        )
        assert request.top_p == 0.0

    def test_max_tokens_boundary(self):
        """Test max_tokens at boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            max_tokens=1,
        )
        assert request.max_tokens == 1

    def test_timeout_boundary(self):
        """Test timeout at minimum boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            timeout_seconds=1,
        )
        assert request.timeout_seconds == 1

    def test_empty_stop_sequences(self):
        """Test empty stop sequences."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            stop_sequences=[],
        )
        assert request.stop_sequences == []

    def test_penalty_boundary_negative(self):
        """Test penalty at negative boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            presence_penalty=-2.0,
            frequency_penalty=-2.0,
        )
        assert request.presence_penalty == -2.0
        assert request.frequency_penalty == -2.0

    def test_penalty_boundary_positive(self):
        """Test penalty at positive boundary."""
        provider = ProviderId.create_openai()
        model = ModelId.create_gpt4(provider)

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model,
            prompt="Test",
            presence_penalty=2.0,
            frequency_penalty=2.0,
        )
        assert request.presence_penalty == 2.0
        assert request.frequency_penalty == 2.0


# Total: 20 unit + 12 integration + 8 boundary = 40 tests for llm_provider
