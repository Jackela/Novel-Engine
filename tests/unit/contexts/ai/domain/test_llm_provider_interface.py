#!/usr/bin/env python3
"""
Comprehensive Unit Tests for LLM Provider Interface

Test suite covering LLMRequest, LLMResponse, error hierarchy, and abstract provider interface
in the AI Gateway Context domain layer.
"""

import asyncio
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

import pytest
from contexts.ai.domain.services.llm_provider import (
    ILLMProvider,
    InvalidRequestError,
    LLMProviderError,
    LLMRequest,
    LLMRequestType,
    LLMResponse,
    LLMResponseStatus,
    ModelUnavailableError,
    QuotaExceededError,
    RateLimitError,
)
from contexts.ai.domain.value_objects.common import (
    ModelCapability,
    ModelId,
    ProviderId,
    TokenBudget,
)


class TestLLMRequestTypeEnum:
    """Test suite for LLMRequestType enum."""

    def test_all_request_types_exist(self):
        """Test that all expected request types are defined."""
        expected_types = {
            "COMPLETION",
            "CHAT",
            "CONVERSATION",
            "SUMMARIZATION",
            "TRANSLATION",
            "CODE_GENERATION",
            "ANALYSIS",
            "EMBEDDING",
            "FUNCTION_CALL",
        }

        actual_types = {item.name for item in LLMRequestType}
        assert actual_types == expected_types

    def test_request_type_string_values(self):
        """Test that request type enum values have correct string representations."""
        assert LLMRequestType.COMPLETION.value == "completion"
        assert LLMRequestType.CHAT.value == "chat"
        assert LLMRequestType.CONVERSATION.value == "conversation"
        assert LLMRequestType.SUMMARIZATION.value == "summarization"
        assert LLMRequestType.TRANSLATION.value == "translation"
        assert LLMRequestType.CODE_GENERATION.value == "code_generation"
        assert LLMRequestType.ANALYSIS.value == "analysis"
        assert LLMRequestType.EMBEDDING.value == "embedding"
        assert LLMRequestType.FUNCTION_CALL.value == "function_call"

    def test_request_type_str_method(self):
        """Test that __str__ method returns the value."""
        assert str(LLMRequestType.COMPLETION) == "completion"
        assert str(LLMRequestType.FUNCTION_CALL) == "function_call"

    def test_request_type_uniqueness(self):
        """Test that all request type values are unique."""
        values = [item.value for item in LLMRequestType]
        assert len(values) == len(set(values))


class TestLLMResponseStatusEnum:
    """Test suite for LLMResponseStatus enum."""

    def test_all_response_statuses_exist(self):
        """Test that all expected response statuses are defined."""
        expected_statuses = {
            "SUCCESS",
            "PARTIAL_SUCCESS",
            "FAILED",
            "RATE_LIMITED",
            "QUOTA_EXCEEDED",
            "MODEL_UNAVAILABLE",
            "INVALID_REQUEST",
            "TIMEOUT",
        }

        actual_statuses = {item.name for item in LLMResponseStatus}
        assert actual_statuses == expected_statuses

    def test_response_status_string_values(self):
        """Test that response status enum values have correct string representations."""
        assert LLMResponseStatus.SUCCESS.value == "success"
        assert LLMResponseStatus.PARTIAL_SUCCESS.value == "partial_success"
        assert LLMResponseStatus.FAILED.value == "failed"
        assert LLMResponseStatus.RATE_LIMITED.value == "rate_limited"
        assert LLMResponseStatus.QUOTA_EXCEEDED.value == "quota_exceeded"
        assert LLMResponseStatus.MODEL_UNAVAILABLE.value == "model_unavailable"
        assert LLMResponseStatus.INVALID_REQUEST.value == "invalid_request"
        assert LLMResponseStatus.TIMEOUT.value == "timeout"

    def test_response_status_str_method(self):
        """Test that __str__ method returns the value."""
        assert str(LLMResponseStatus.SUCCESS) == "success"
        assert str(LLMResponseStatus.RATE_LIMITED) == "rate_limited"


class TestLLMRequestCreation:
    """Test suite for LLM request creation and validation."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)
        self.request_id = uuid4()

    def test_basic_request_creation(self):
        """Test basic LLM request creation with required parameters."""
        request = LLMRequest(
            request_id=self.request_id,
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt",
        )

        assert request.request_id == self.request_id
        assert request.request_type == LLMRequestType.COMPLETION
        assert request.model_id == self.model_id
        assert request.prompt == "Test prompt"
        assert request.system_prompt is None
        assert request.parameters == {}
        assert request.max_tokens is None
        assert request.temperature == 0.7
        assert request.top_p == 1.0
        assert request.presence_penalty == 0.0
        assert request.frequency_penalty == 0.0
        assert request.stop_sequences == []
        assert request.functions is None
        assert request.timeout_seconds == 30
        assert request.stream is False
        assert request.metadata == {}

    def test_request_creation_with_all_parameters(self):
        """Test request creation with all optional parameters."""
        parameters = {"custom_param": "value"}
        stop_sequences = ["STOP", "END"]
        functions = [{"name": "test_function", "parameters": {}}]
        metadata = {"source": "test", "priority": "high"}

        request = LLMRequest(
            request_id=self.request_id,
            request_type=LLMRequestType.CHAT,
            model_id=self.model_id,
            prompt="Test prompt",
            system_prompt="System instruction",
            parameters=parameters,
            max_tokens=1000,
            temperature=0.5,
            top_p=0.9,
            presence_penalty=0.1,
            frequency_penalty=-0.1,
            stop_sequences=stop_sequences,
            functions=functions,
            timeout_seconds=60,
            stream=True,
            metadata=metadata,
        )

        assert request.system_prompt == "System instruction"
        assert request.parameters == parameters
        assert request.max_tokens == 1000
        assert request.temperature == 0.5
        assert request.top_p == 0.9
        assert request.presence_penalty == 0.1
        assert request.frequency_penalty == -0.1
        assert request.stop_sequences == stop_sequences
        assert request.functions == functions
        assert request.timeout_seconds == 60
        assert request.stream is True
        assert request.metadata == metadata

    def test_request_validation_invalid_request_id(self):
        """Test request validation with invalid request ID."""
        with pytest.raises(ValueError, match="request_id must be a UUID"):
            LLMRequest(
                request_id="not-a-uuid",
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
            )

    def test_request_validation_invalid_request_type(self):
        """Test request validation with invalid request type."""
        with pytest.raises(
            ValueError, match="request_type must be a LLMRequestType enum"
        ):
            LLMRequest(
                request_id=self.request_id,
                request_type="completion",  # String instead of enum
                model_id=self.model_id,
                prompt="Test prompt",
            )

    def test_request_validation_invalid_model_id(self):
        """Test request validation with invalid model ID."""
        with pytest.raises(ValueError, match="model_id must be a ModelId instance"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id="gpt-4",  # String instead of ModelId
                prompt="Test prompt",
            )

    def test_request_validation_empty_prompt(self):
        """Test request validation with empty prompt."""
        with pytest.raises(
            ValueError, match="prompt is required and must be a non-empty string"
        ):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="",
            )

    def test_request_validation_invalid_temperature(self):
        """Test request validation with invalid temperature values."""
        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                temperature=-0.1,
            )

        with pytest.raises(ValueError, match="temperature must be between 0.0 and 2.0"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                temperature=2.1,
            )

    def test_request_validation_invalid_top_p(self):
        """Test request validation with invalid top_p values."""
        with pytest.raises(ValueError, match="top_p must be between 0.0 and 1.0"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                top_p=-0.1,
            )

        with pytest.raises(ValueError, match="top_p must be between 0.0 and 1.0"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                top_p=1.1,
            )

    def test_request_validation_invalid_penalties(self):
        """Test request validation with invalid penalty values."""
        with pytest.raises(
            ValueError, match="presence_penalty must be between -2.0 and 2.0"
        ):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                presence_penalty=-2.1,
            )

        with pytest.raises(
            ValueError, match="frequency_penalty must be between -2.0 and 2.0"
        ):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                frequency_penalty=2.1,
            )

    def test_request_validation_invalid_max_tokens(self):
        """Test request validation with invalid max_tokens values."""
        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                max_tokens=0,
            )

        with pytest.raises(ValueError, match="max_tokens must be a positive integer"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                max_tokens=-100,
            )

    def test_request_validation_max_tokens_exceeds_model_limit(self):
        """Test request validation when max_tokens exceeds model limits."""
        with pytest.raises(ValueError, match="max_tokens .* exceeds model limit"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                max_tokens=self.model_id.max_output_tokens + 1,
            )

    def test_request_validation_invalid_timeout(self):
        """Test request validation with invalid timeout values."""
        with pytest.raises(
            ValueError, match="timeout_seconds must be a positive integer"
        ):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                timeout_seconds=0,
            )

    def test_request_validation_duplicate_stop_sequences(self):
        """Test request validation with duplicate stop sequences."""
        with pytest.raises(ValueError, match="stop_sequences must be unique"):
            LLMRequest(
                request_id=self.request_id,
                request_type=LLMRequestType.COMPLETION,
                model_id=self.model_id,
                prompt="Test prompt",
                stop_sequences=["STOP", "END", "STOP"],  # Duplicate "STOP"
            )


class TestLLMRequestFactoryMethods:
    """Test suite for LLM request factory methods."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)

    def test_create_chat_request_basic(self):
        """Test creating chat request with basic parameters."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        request = LLMRequest.create_chat_request(
            model_id=self.model_id, messages=messages
        )

        assert request.request_type == LLMRequestType.CHAT
        assert request.model_id == self.model_id
        assert "user: Hello" in request.prompt
        assert "assistant: Hi there!" in request.prompt
        assert request.system_prompt is None
        assert request.max_tokens is None
        assert request.temperature == 0.7
        assert request.metadata["messages"] == messages
        assert request.metadata["format"] == "chat"

    def test_create_chat_request_with_system_prompt(self):
        """Test creating chat request with system prompt."""
        messages = [{"role": "user", "content": "Hello"}]
        system_prompt = "You are a helpful assistant"

        request = LLMRequest.create_chat_request(
            model_id=self.model_id, messages=messages, system_prompt=system_prompt
        )

        assert request.system_prompt == system_prompt
        assert request.metadata["messages"] == messages

    def test_create_chat_request_with_custom_metadata(self):
        """Test creating chat request with custom metadata."""
        messages = [{"role": "user", "content": "Hello"}]
        custom_metadata = {"source": "test", "priority": "high"}

        request = LLMRequest.create_chat_request(
            model_id=self.model_id, messages=messages, metadata=custom_metadata
        )

        # Custom metadata should be merged with defaults
        assert request.metadata["messages"] == messages
        assert request.metadata["format"] == "chat"
        assert request.metadata["source"] == "test"
        assert request.metadata["priority"] == "high"

    def test_create_completion_request_basic(self):
        """Test creating completion request with basic parameters."""
        prompt = "Complete this text:"

        request = LLMRequest.create_completion_request(
            model_id=self.model_id, prompt=prompt
        )

        assert request.request_type == LLMRequestType.COMPLETION
        assert request.model_id == self.model_id
        assert request.prompt == prompt
        assert request.system_prompt is None
        assert request.max_tokens is None
        assert request.temperature == 0.7
        assert request.metadata["format"] == "completion"

    def test_create_completion_request_with_parameters(self):
        """Test creating completion request with custom parameters."""
        prompt = "Complete this text:"
        max_tokens = 500
        temperature = 0.9
        custom_metadata = {"source": "test"}

        request = LLMRequest.create_completion_request(
            model_id=self.model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata=custom_metadata,
        )

        assert request.max_tokens == max_tokens
        assert request.temperature == temperature
        assert request.metadata["format"] == "completion"
        assert request.metadata["source"] == "test"


class TestLLMRequestBusinessMethods:
    """Test suite for LLM request business methods."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)
        self.request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt with some text content",
            system_prompt="System instruction",
        )

    def test_estimate_input_tokens(self):
        """Test token estimation for input text."""
        # Rough approximation: 1 token ≈ 4 characters
        expected_tokens = (
            len(self.request.prompt) + len(self.request.system_prompt)
        ) // 4

        estimated_tokens = self.request.estimate_input_tokens()

        assert estimated_tokens == expected_tokens
        assert estimated_tokens > 0

    def test_estimate_input_tokens_no_system_prompt(self):
        """Test token estimation with no system prompt."""
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt",
        )

        expected_tokens = len(request.prompt) // 4
        estimated_tokens = request.estimate_input_tokens()

        assert estimated_tokens == expected_tokens

    def test_get_effective_max_tokens_with_limit(self):
        """Test getting effective max tokens with specified limit."""
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt",
            max_tokens=1000,
        )

        effective_max = request.get_effective_max_tokens()

        assert effective_max == 1000
        assert effective_max <= self.model_id.max_output_tokens

    def test_get_effective_max_tokens_no_limit(self):
        """Test getting effective max tokens without specified limit."""
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt",
        )

        effective_max = request.get_effective_max_tokens()

        assert effective_max == self.model_id.max_output_tokens

    def test_get_effective_max_tokens_exceeds_model_limit(self):
        """Test effective max tokens when requested exceeds model limit."""
        # This should not happen due to validation, but test the method logic
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt="Test prompt",
            max_tokens=2000,  # Less than model limit for this test
        )

        effective_max = request.get_effective_max_tokens()
        expected = min(2000, self.model_id.max_output_tokens)

        assert effective_max == expected

    def test_is_compatible_with_model_compatible(self):
        """Test model compatibility check for compatible request."""
        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.CONVERSATION,  # Supported by model
            model_id=self.model_id,
            prompt="Short prompt",
        )

        is_compatible = request.is_compatible_with_model()

        assert is_compatible is True

    def test_is_compatible_with_model_unsupported_capability(self):
        """Test model compatibility check for unsupported capability."""
        # Create model without EMBEDDING capability
        provider_id = ProviderId.create_openai()
        limited_model = ModelId(
            model_name="gpt-3.5-turbo",
            provider_id=provider_id,
            capabilities={ModelCapability.TEXT_GENERATION},  # No EMBEDDING
            max_context_tokens=4096,
            max_output_tokens=1024,
        )

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.EMBEDDING,  # Not supported
            model_id=limited_model,
            prompt="Test prompt",
        )

        is_compatible = request.is_compatible_with_model()

        assert is_compatible is False

    def test_is_compatible_with_model_context_too_large(self):
        """Test model compatibility check for oversized context."""
        # Create a very long prompt that exceeds context limits
        long_prompt = "x" * (
            self.model_id.max_context_tokens * 4
        )  # Much longer than context allows

        request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=self.model_id,
            prompt=long_prompt,
        )

        is_compatible = request.is_compatible_with_model()

        assert is_compatible is False


class TestLLMResponseCreation:
    """Test suite for LLM response creation and validation."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)
        self.request_id = uuid4()
        self.response_id = uuid4()

    def test_basic_response_creation(self):
        """Test basic LLM response creation with required parameters."""
        response = LLMResponse(
            request_id=self.request_id,
            response_id=self.response_id,
            status=LLMResponseStatus.SUCCESS,
            content="Generated response content",
        )

        assert response.request_id == self.request_id
        assert response.response_id == self.response_id
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Generated response content"
        assert response.finish_reason is None
        assert response.model_id is None
        assert response.usage_stats == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        assert response.cost_estimate == Decimal("0.00")
        assert response.metadata == {}
        assert response.error_details is None
        assert response.provider_response == {}

    def test_response_creation_with_all_parameters(self):
        """Test response creation with all optional parameters."""
        usage_stats = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        cost_estimate = Decimal("0.05")
        metadata = {"generation_time": 1.5, "model_version": "gpt-4-0314"}
        provider_response = {"id": "chatcmpl-123", "object": "chat.completion"}

        response = LLMResponse(
            request_id=self.request_id,
            response_id=self.response_id,
            status=LLMResponseStatus.SUCCESS,
            content="Generated response content",
            finish_reason="stop",
            model_id=self.model_id,
            usage_stats=usage_stats,
            cost_estimate=cost_estimate,
            metadata=metadata,
            error_details=None,
            provider_response=provider_response,
        )

        assert response.finish_reason == "stop"
        assert response.model_id == self.model_id
        assert response.usage_stats == usage_stats
        assert response.cost_estimate == cost_estimate
        assert response.metadata == metadata
        assert response.provider_response == provider_response

    def test_response_validation_invalid_request_id(self):
        """Test response validation with invalid request ID."""
        with pytest.raises(ValueError, match="request_id must be a UUID"):
            LLMResponse(
                request_id="not-a-uuid",
                response_id=self.response_id,
                status=LLMResponseStatus.SUCCESS,
                content="Test content",
            )

    def test_response_validation_invalid_response_id(self):
        """Test response validation with invalid response ID."""
        with pytest.raises(ValueError, match="response_id must be a UUID"):
            LLMResponse(
                request_id=self.request_id,
                response_id="not-a-uuid",
                status=LLMResponseStatus.SUCCESS,
                content="Test content",
            )

    def test_response_validation_invalid_status(self):
        """Test response validation with invalid status."""
        with pytest.raises(ValueError, match="status must be a LLMResponseStatus enum"):
            LLMResponse(
                request_id=self.request_id,
                response_id=self.response_id,
                status="success",  # String instead of enum
                content="Test content",
            )

    def test_response_validation_successful_without_content(self):
        """Test response validation for successful response without content."""
        with pytest.raises(ValueError, match="Successful responses must have content"):
            LLMResponse(
                request_id=self.request_id,
                response_id=self.response_id,
                status=LLMResponseStatus.SUCCESS,
                content=None,  # No content for successful response
            )

    def test_response_validation_failed_without_error_details(self):
        """Test response validation for failed response without error details."""
        with pytest.raises(
            ValueError, match="Failed responses must have error_details"
        ):
            LLMResponse(
                request_id=self.request_id,
                response_id=self.response_id,
                status=LLMResponseStatus.FAILED,
                error_details=None,  # No error details for failed response
            )

    def test_response_validation_invalid_usage_stats(self):
        """Test response validation with invalid usage stats."""
        with pytest.raises(
            ValueError, match="usage_stats.*must be a non-negative integer"
        ):
            LLMResponse(
                request_id=self.request_id,
                response_id=self.response_id,
                status=LLMResponseStatus.SUCCESS,
                content="Test content",
                usage_stats={
                    "input_tokens": -10,
                    "output_tokens": 50,
                    "total_tokens": 40,
                },
            )

    def test_response_validation_invalid_cost_estimate(self):
        """Test response validation with invalid cost estimate."""
        with pytest.raises(
            ValueError, match="cost_estimate must be a non-negative Decimal"
        ):
            LLMResponse(
                request_id=self.request_id,
                response_id=self.response_id,
                status=LLMResponseStatus.SUCCESS,
                content="Test content",
                cost_estimate=Decimal("-1.00"),  # Negative cost
            )


class TestLLMResponseFactoryMethods:
    """Test suite for LLM response factory methods."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(provider_id)
        self.request_id = uuid4()

    def test_create_success_response(self):
        """Test creating successful response using factory method."""
        content = "Generated response content"
        input_tokens = 100
        output_tokens = 50

        response = LLMResponse.create_success(
            request_id=self.request_id,
            content=content,
            model_id=self.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        assert response.request_id == self.request_id
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == content
        assert response.model_id == self.model_id
        assert response.finish_reason == "stop"
        assert response.usage_stats["input_tokens"] == input_tokens
        assert response.usage_stats["output_tokens"] == output_tokens
        assert response.usage_stats["total_tokens"] == input_tokens + output_tokens
        assert response.cost_estimate == self.model_id.estimate_cost(
            input_tokens, output_tokens
        )

    def test_create_success_response_custom_finish_reason(self):
        """Test creating successful response with custom finish reason."""
        content = "Generated content"
        input_tokens = 50
        output_tokens = 100
        finish_reason = "length"

        response = LLMResponse.create_success(
            request_id=self.request_id,
            content=content,
            model_id=self.model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
        )

        assert response.finish_reason == finish_reason
        assert response.status == LLMResponseStatus.SUCCESS

    def test_create_error_response(self):
        """Test creating error response using factory method."""
        error_status = LLMResponseStatus.RATE_LIMITED
        error_details = "Rate limit exceeded. Try again in 60 seconds."

        response = LLMResponse.create_error(
            request_id=self.request_id, status=error_status, error_details=error_details
        )

        assert response.request_id == self.request_id
        assert response.status == error_status
        assert response.error_details == error_details
        assert response.content is None
        assert response.model_id is None
        assert response.usage_stats == {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    def test_create_error_response_with_model(self):
        """Test creating error response with model information."""
        error_status = LLMResponseStatus.MODEL_UNAVAILABLE
        error_details = "The requested model is temporarily unavailable."

        response = LLMResponse.create_error(
            request_id=self.request_id,
            status=error_status,
            error_details=error_details,
            model_id=self.model_id,
        )

        assert response.model_id == self.model_id
        assert response.status == error_status
        assert response.error_details == error_details


class TestLLMResponseBusinessMethods:
    """Test suite for LLM response business methods."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        model_id = ModelId.create_gpt4(provider_id)
        self.request_id = uuid4()

        self.success_response = LLMResponse.create_success(
            request_id=self.request_id,
            content="Generated content",
            model_id=model_id,
            input_tokens=100,
            output_tokens=50,
        )

        self.error_response = LLMResponse.create_error(
            request_id=self.request_id,
            status=LLMResponseStatus.FAILED,
            error_details="Generation failed",
        )

    def test_is_successful_for_success_status(self):
        """Test is_successful method for successful responses."""
        assert self.success_response.is_successful() is True

    def test_is_successful_for_partial_success_status(self):
        """Test is_successful method for partial success responses."""
        partial_response = LLMResponse(
            request_id=self.request_id,
            response_id=uuid4(),
            status=LLMResponseStatus.PARTIAL_SUCCESS,
            content="Partial content",
        )

        assert partial_response.is_successful() is True

    def test_is_successful_for_error_status(self):
        """Test is_successful method for error responses."""
        assert self.error_response.is_successful() is False

    def test_get_total_tokens(self):
        """Test getting total token usage."""
        total_tokens = self.success_response.get_total_tokens()

        assert total_tokens == 150  # 100 input + 50 output
        assert total_tokens == self.success_response.usage_stats["total_tokens"]

    def test_get_input_tokens(self):
        """Test getting input token usage."""
        input_tokens = self.success_response.get_input_tokens()

        assert input_tokens == 100
        assert input_tokens == self.success_response.usage_stats["input_tokens"]

    def test_get_output_tokens(self):
        """Test getting output token usage."""
        output_tokens = self.success_response.get_output_tokens()

        assert output_tokens == 50
        assert output_tokens == self.success_response.usage_stats["output_tokens"]

    def test_token_methods_with_empty_stats(self):
        """Test token methods when usage stats are empty."""
        empty_response = LLMResponse(
            request_id=self.request_id,
            response_id=uuid4(),
            status=LLMResponseStatus.FAILED,
            error_details="Failed",
            usage_stats={},  # Empty stats
        )

        assert empty_response.get_total_tokens() == 0
        assert empty_response.get_input_tokens() == 0
        assert empty_response.get_output_tokens() == 0


class TestLLMProviderErrorHierarchy:
    """Test suite for LLM provider error hierarchy."""

    def test_base_llm_provider_error(self):
        """Test base LLMProviderError exception."""
        provider_id = ProviderId.create_openai()
        error_code = "API_ERROR"
        retry_after = 60
        message = "API request failed"

        error = LLMProviderError(
            message=message,
            provider_id=provider_id,
            error_code=error_code,
            retry_after=retry_after,
        )

        assert str(error) == message
        assert error.provider_id == provider_id
        assert error.error_code == error_code
        assert error.retry_after == retry_after

    def test_base_error_without_optional_parameters(self):
        """Test base error without optional parameters."""
        message = "Simple error"

        error = LLMProviderError(message)

        assert str(error) == message
        assert error.provider_id is None
        assert error.error_code is None
        assert error.retry_after is None

    def test_rate_limit_error(self):
        """Test RateLimitError specific exception."""
        provider_id = ProviderId.create_openai()
        message = "Rate limit exceeded"
        retry_after = 120

        error = RateLimitError(
            message=message, provider_id=provider_id, retry_after=retry_after
        )

        assert isinstance(error, LLMProviderError)
        assert isinstance(error, RateLimitError)
        assert str(error) == message
        assert error.provider_id == provider_id
        assert error.retry_after == retry_after

    def test_quota_exceeded_error(self):
        """Test QuotaExceededError specific exception."""
        provider_id = ProviderId.create_openai()
        message = "Monthly quota exceeded"

        error = QuotaExceededError(
            message=message, provider_id=provider_id, error_code="QUOTA_EXCEEDED"
        )

        assert isinstance(error, LLMProviderError)
        assert isinstance(error, QuotaExceededError)
        assert str(error) == message
        assert error.error_code == "QUOTA_EXCEEDED"

    def test_model_unavailable_error(self):
        """Test ModelUnavailableError specific exception."""
        message = "Model is temporarily unavailable"

        error = ModelUnavailableError(message)

        assert isinstance(error, LLMProviderError)
        assert isinstance(error, ModelUnavailableError)
        assert str(error) == message

    def test_invalid_request_error(self):
        """Test InvalidRequestError specific exception."""
        message = "Invalid request parameters"
        error_code = "INVALID_PARAMS"

        error = InvalidRequestError(message=message, error_code=error_code)

        assert isinstance(error, LLMProviderError)
        assert isinstance(error, InvalidRequestError)
        assert str(error) == message
        assert error.error_code == error_code


class MockLLMProvider(ILLMProvider):
    """Mock LLM provider for testing abstract interface."""

    def __init__(self, provider_id: ProviderId, supported_models: List[ModelId]):
        self._provider_id = provider_id
        self._supported_models = supported_models
        self._available = True

    @property
    def provider_id(self) -> ProviderId:
        return self._provider_id

    @property
    def supported_models(self) -> List[ModelId]:
        return self._supported_models

    @property
    def is_available(self) -> bool:
        return self._available

    async def generate_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        return LLMResponse.create_success(
            request_id=request.request_id,
            content="Mock generated content",
            model_id=request.model_id,
            input_tokens=10,
            output_tokens=5,
        )

    async def generate_stream_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> AsyncIterator[str]:
        chunks = ["Mock ", "streaming ", "content"]
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.01)  # Simulate streaming delay

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimation

    def validate_request(self, request: LLMRequest) -> bool:
        return request.is_compatible_with_model()

    def get_model_info(self, model_name: str) -> Optional[ModelId]:
        for model in self._supported_models:
            if model.model_name == model_name:
                return model
        return None

    async def health_check_async(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self._available else "unhealthy",
            "response_time_ms": 150,
            "rate_limit_remaining": 1000,
            "models_available": len(self._supported_models),
            "last_error": None,
            "quota_utilization": 0.45,
        }


class TestILLMProviderInterface:
    """Test suite for ILLMProvider abstract interface."""

    def setup_method(self):
        """Set up test dependencies."""
        self.provider_id = ProviderId.create_openai()
        self.model_id = ModelId.create_gpt4(self.provider_id)
        self.provider = MockLLMProvider(self.provider_id, [self.model_id])
        self.request = LLMRequest.create_completion_request(
            model_id=self.model_id, prompt="Test prompt"
        )

    def test_provider_properties(self):
        """Test provider basic properties."""
        assert self.provider.provider_id == self.provider_id
        assert self.provider.supported_models == [self.model_id]
        assert self.provider.is_available is True

    @pytest.mark.asyncio
    async def test_generate_async(self):
        """Test asynchronous generation method."""
        response = await self.provider.generate_async(self.request)

        assert isinstance(response, LLMResponse)
        assert response.request_id == self.request.request_id
        assert response.status == LLMResponseStatus.SUCCESS
        assert response.content == "Mock generated content"
        assert response.model_id == self.model_id

    def test_generate_sync_wrapper(self):
        """Test synchronous generation wrapper."""
        response = self.provider.generate(self.request)

        assert isinstance(response, LLMResponse)
        assert response.request_id == self.request.request_id
        assert response.status == LLMResponseStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_generate_stream_async(self):
        """Test asynchronous streaming generation."""
        chunks = []
        async for chunk in self.provider.generate_stream_async(self.request):
            chunks.append(chunk)

        assert chunks == ["Mock ", "streaming ", "content"]

    def test_estimate_tokens(self):
        """Test token estimation method."""
        text = "This is a test text for token estimation"
        estimated = self.provider.estimate_tokens(text)

        expected = len(text) // 4  # Mock implementation
        assert estimated == expected

    def test_validate_request_valid(self):
        """Test request validation for valid request."""
        is_valid = self.provider.validate_request(self.request)

        assert is_valid is True

    def test_validate_request_invalid(self):
        """Test request validation for invalid request."""
        # Create request with incompatible model capability
        invalid_request = LLMRequest(
            request_id=uuid4(),
            request_type=LLMRequestType.EMBEDDING,  # Not supported by our mock model
            model_id=self.model_id,
            prompt="Test prompt",
        )

        is_valid = self.provider.validate_request(invalid_request)

        assert is_valid is False

    def test_get_model_info_existing(self):
        """Test getting model info for existing model."""
        model_info = self.provider.get_model_info(self.model_id.model_name)

        assert model_info == self.model_id

    def test_get_model_info_non_existing(self):
        """Test getting model info for non-existing model."""
        model_info = self.provider.get_model_info("non-existing-model")

        assert model_info is None

    @pytest.mark.asyncio
    async def test_health_check_async(self):
        """Test asynchronous health check."""
        health = await self.provider.health_check_async()

        assert health["status"] == "healthy"
        assert health["response_time_ms"] == 150
        assert health["models_available"] == 1
        assert health["quota_utilization"] == 0.45

    def test_health_check_sync_wrapper(self):
        """Test synchronous health check wrapper."""
        health = self.provider.health_check()

        assert health["status"] == "healthy"
        assert isinstance(health, dict)

    def test_supports_streaming_default(self):
        """Test default streaming support."""
        assert self.provider.supports_streaming() is True

    def test_supports_function_calling(self):
        """Test function calling support detection."""
        # Our mock model supports function calling via capabilities
        supports_functions = self.provider.supports_function_calling()

        # Check if any supported model has FUNCTION_CALLING capability
        expected = any(
            ModelCapability.FUNCTION_CALLING in model.capabilities
            for model in self.provider.supported_models
        )

        assert supports_functions == expected

    def test_get_rate_limits_default(self):
        """Test default rate limits."""
        rate_limits = self.provider.get_rate_limits()

        assert rate_limits["requests_per_minute"] == 60
        assert rate_limits["tokens_per_minute"] == 10000

    def test_get_pricing_info(self):
        """Test getting pricing information."""
        pricing = self.provider.get_pricing_info(self.model_id)

        assert pricing["input_token_cost"] == self.model_id.cost_per_input_token
        assert pricing["output_token_cost"] == self.model_id.cost_per_output_token
        assert pricing["currency"] == "USD"

    def test_string_representation(self):
        """Test string representations of provider."""
        str_repr = str(self.provider)
        repr_repr = repr(self.provider)

        assert self.provider_id.provider_name in str_repr
        assert "MockLLMProvider" in repr_repr
        assert str(self.provider_id) in repr_repr


class TestILLMProviderWithBudget:
    """Test suite for ILLMProvider with TokenBudget integration."""

    def setup_method(self):
        """Set up test dependencies."""
        provider_id = ProviderId.create_openai()
        model_id = ModelId.create_gpt4(provider_id)
        self.provider = MockLLMProvider(provider_id, [model_id])
        self.request = LLMRequest.create_completion_request(
            model_id=model_id, prompt="Test prompt"
        )
        self.budget = TokenBudget.create_daily_budget(
            "test-budget", 1000, Decimal("10.00")
        )

    @pytest.mark.asyncio
    async def test_generate_async_with_budget(self):
        """Test async generation with token budget."""
        response = await self.provider.generate_async(self.request, self.budget)

        assert isinstance(response, LLMResponse)
        assert response.status == LLMResponseStatus.SUCCESS
        # Budget enforcement would be handled by the implementation

    @pytest.mark.asyncio
    async def test_generate_stream_async_with_budget(self):
        """Test async streaming with token budget."""
        chunks = []
        async for chunk in self.provider.generate_stream_async(
            self.request, self.budget
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Budget enforcement would be handled by the implementation
