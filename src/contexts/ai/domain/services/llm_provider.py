#!/usr/bin/env python3
"""
LLM Provider Abstract Interface

This module defines the abstract interface that all Large Language Model (LLM)
providers must implement. It establishes a standard contract for AI integration,
ensuring consistency, interoperability, and testability across different
LLM vendors and implementations.

Key Components:
- ILLMProvider: Abstract base class defining the provider contract
- LLMRequest: Request structure for LLM operations
- LLMResponse: Response structure from LLM operations
- LLMError: Exception hierarchy for error handling

The interface supports various LLM operations including text generation,
conversation management, token estimation, and provider-specific features.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID, uuid4

from ..value_objects.common import ModelCapability, ModelId, ProviderId, TokenBudget


class LLMRequestType(Enum):
    """
    Enumeration of LLM request types.

    Categorizes different types of AI operations for routing,
    processing, and optimization purposes.
    """

    COMPLETION = "completion"
    CHAT = "chat"
    CONVERSATION = "conversation"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CODE_GENERATION = "code_generation"
    ANALYSIS = "analysis"
    EMBEDDING = "embedding"
    FUNCTION_CALL = "function_call"

    def __str__(self) -> str:
        return self.value


class LLMResponseStatus(Enum):
    """
    Enumeration of LLM response statuses.

    Indicates the outcome of LLM operations for proper
    error handling and workflow management.
    """

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_REQUEST = "invalid_request"
    TIMEOUT = "timeout"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LLMRequest:
    """
    Immutable request object for LLM operations.

    Encapsulates all parameters and context needed for LLM processing,
    providing type safety, validation, and standardization across
    different providers and request types.

    Attributes:
        request_id: Unique identifier for request tracking
        request_type: Type of LLM operation
        model_id: Target model for processing
        prompt: Main prompt text or conversation context
        system_prompt: System/instruction prompt
        parameters: Model-specific parameters
        max_tokens: Maximum tokens in response
        temperature: Randomness/creativity setting (0.0-2.0)
        top_p: Nucleus sampling parameter
        presence_penalty: Penalty for repeated content
        frequency_penalty: Penalty for frequent tokens
        stop_sequences: Sequences that stop generation
        functions: Available functions for function calling
        timeout_seconds: Request timeout
        stream: Whether to stream response
        metadata: Additional request context

    Business Rules:
        - Prompt must not be empty for text generation
        - Temperature must be between 0.0 and 2.0
        - Max tokens must be positive and within model limits
        - Stop sequences must be unique
        - Function definitions must be valid JSON schema
    """

    request_id: UUID
    request_type: LLMRequestType
    model_id: ModelId
    prompt: str
    system_prompt: Optional[str] = None
    parameters: Dict[str, Any] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    stop_sequences: List[str] = None
    functions: Optional[List[Dict[str, Any]]] = None
    timeout_seconds: int = 30
    stream: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate LLM request parameters and constraints."""
        # Initialize collections if None
        if self.parameters is None:
            object.__setattr__(self, "parameters", {})

        if self.stop_sequences is None:
            object.__setattr__(self, "stop_sequences", [])

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate required fields
        if not isinstance(self.request_id, UUID):
            raise ValueError("request_id must be a UUID")

        if not isinstance(self.request_type, LLMRequestType):
            raise ValueError("request_type must be a LLMRequestType enum")

        if not isinstance(self.model_id, ModelId):
            raise ValueError("model_id must be a ModelId instance")

        if not self.prompt or not isinstance(self.prompt, str):
            raise ValueError("prompt is required and must be a non-empty string")

        # Validate numeric parameters
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")

        if not (0.0 <= self.top_p <= 1.0):
            raise ValueError("top_p must be between 0.0 and 1.0")

        if not (-2.0 <= self.presence_penalty <= 2.0):
            raise ValueError("presence_penalty must be between -2.0 and 2.0")

        if not (-2.0 <= self.frequency_penalty <= 2.0):
            raise ValueError("frequency_penalty must be between -2.0 and 2.0")

        # Validate max_tokens against model limits
        if self.max_tokens is not None:
            if not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
                raise ValueError("max_tokens must be a positive integer")

            if self.max_tokens > self.model_id.max_output_tokens:
                raise ValueError(
                    f"max_tokens ({self.max_tokens}) exceeds model limit ({self.model_id.max_output_tokens})"
                )

        # Validate timeout
        if not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer")

        # Validate stop sequences are unique
        if len(self.stop_sequences) != len(set(self.stop_sequences)):
            raise ValueError("stop_sequences must be unique")

    @classmethod
    def create_chat_request(
        cls,
        model_id: ModelId,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "LLMRequest":
        """Factory method for chat/conversation requests."""
        # Convert messages to prompt format (simplified)
        prompt = "\n".join(
            [f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages]
        )

        # Merge default metadata with custom metadata
        default_metadata = {"messages": messages, "format": "chat"}
        if metadata:
            default_metadata.update(metadata)

        return cls(
            request_id=uuid4(),
            request_type=LLMRequestType.CHAT,
            model_id=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata=default_metadata,
        )

    @classmethod
    def create_completion_request(
        cls,
        model_id: ModelId,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "LLMRequest":
        """Factory method for text completion requests."""
        # Merge default metadata with custom metadata
        default_metadata = {"format": "completion"}
        if metadata:
            default_metadata.update(metadata)

        return cls(
            request_id=uuid4(),
            request_type=LLMRequestType.COMPLETION,
            model_id=model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            metadata=default_metadata,
        )

    def estimate_input_tokens(self) -> int:
        """Estimate input token count (rough approximation)."""
        # Simplified token estimation - 1 token ≈ 4 characters
        prompt_chars = len(self.prompt)
        system_chars = len(self.system_prompt) if self.system_prompt else 0
        return (prompt_chars + system_chars) // 4

    def get_effective_max_tokens(self) -> int:
        """Get effective max tokens considering model limits."""
        if self.max_tokens is None:
            return self.model_id.max_output_tokens
        return min(self.max_tokens, self.model_id.max_output_tokens)

    def is_compatible_with_model(self) -> bool:
        """Check if request is compatible with target model."""
        # Check if model supports the request type capability
        capability_map = {
            LLMRequestType.COMPLETION: ModelCapability.TEXT_GENERATION,
            LLMRequestType.CHAT: ModelCapability.CONVERSATION,
            LLMRequestType.CONVERSATION: ModelCapability.CONVERSATION,
            LLMRequestType.CODE_GENERATION: ModelCapability.CODE_GENERATION,
            LLMRequestType.ANALYSIS: ModelCapability.ANALYSIS,
            LLMRequestType.SUMMARIZATION: ModelCapability.SUMMARIZATION,
            LLMRequestType.TRANSLATION: ModelCapability.TRANSLATION,
            LLMRequestType.FUNCTION_CALL: ModelCapability.FUNCTION_CALLING,
            LLMRequestType.EMBEDDING: ModelCapability.EMBEDDING,
        }

        required_capability = capability_map.get(self.request_type)
        if required_capability and not self.model_id.supports_capability(
            required_capability
        ):
            return False

        # Check context size
        estimated_input_tokens = self.estimate_input_tokens()
        effective_max_output = self.get_effective_max_tokens()

        return self.model_id.can_handle_context(
            estimated_input_tokens + effective_max_output
        )


@dataclass(frozen=True)
class LLMResponse:
    """
    Immutable response object from LLM operations.

    Contains the complete response from LLM processing including
    generated content, usage statistics, metadata, and status information
    for proper handling and billing.

    Attributes:
        request_id: Original request identifier
        response_id: Unique response identifier
        status: Response status indicator
        content: Generated text content
        finish_reason: Reason generation stopped
        model_id: Model that generated response
        usage_stats: Token usage and timing statistics
        cost_estimate: Estimated cost for the operation
        metadata: Additional response metadata
        error_details: Error information if failed
        provider_response: Raw provider response data

    Business Rules:
        - Successful responses must have content
        - Failed responses must have error details
        - Usage stats must be non-negative
        - Cost estimates must be non-negative
    """

    request_id: UUID
    response_id: UUID
    status: LLMResponseStatus
    content: Optional[str] = None
    finish_reason: Optional[str] = None
    model_id: Optional[ModelId] = None
    usage_stats: Dict[str, int] = None
    cost_estimate: Decimal = None
    metadata: Dict[str, Any] = None
    error_details: Optional[str] = None
    provider_response: Dict[str, Any] = None

    def __post_init__(self):
        """Validate LLM response structure and constraints."""
        # Initialize collections if None
        if self.usage_stats is None:
            object.__setattr__(
                self,
                "usage_stats",
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )

        if self.cost_estimate is None:
            object.__setattr__(self, "cost_estimate", Decimal("0.00"))

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        if self.provider_response is None:
            object.__setattr__(self, "provider_response", {})

        # Validate UUIDs
        if not isinstance(self.request_id, UUID):
            raise ValueError("request_id must be a UUID")

        if not isinstance(self.response_id, UUID):
            raise ValueError("response_id must be a UUID")

        # Validate status
        if not isinstance(self.status, LLMResponseStatus):
            raise ValueError("status must be a LLMResponseStatus enum")

        # Validate business rules based on status
        if self.status == LLMResponseStatus.SUCCESS:
            if not self.content:
                raise ValueError("Successful responses must have content")

        if self.status in {LLMResponseStatus.FAILED, LLMResponseStatus.INVALID_REQUEST}:
            if not self.error_details:
                raise ValueError("Failed responses must have error_details")

        # Validate usage stats are non-negative
        for key, value in self.usage_stats.items():
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"usage_stats[{key}] must be a non-negative integer")

        # Validate cost estimate is non-negative
        if not isinstance(self.cost_estimate, Decimal) or self.cost_estimate < 0:
            raise ValueError("cost_estimate must be a non-negative Decimal")

    @classmethod
    def create_success(
        cls,
        request_id: UUID,
        content: str,
        model_id: ModelId,
        input_tokens: int,
        output_tokens: int,
        finish_reason: str = "stop",
    ) -> "LLMResponse":
        """Factory method for successful responses."""
        cost_estimate = model_id.estimate_cost(input_tokens, output_tokens)

        return cls(
            request_id=request_id,
            response_id=uuid4(),
            status=LLMResponseStatus.SUCCESS,
            content=content,
            finish_reason=finish_reason,
            model_id=model_id,
            usage_stats={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
            cost_estimate=cost_estimate,
        )

    @classmethod
    def create_error(
        cls,
        request_id: UUID,
        status: LLMResponseStatus,
        error_details: str,
        model_id: Optional[ModelId] = None,
    ) -> "LLMResponse":
        """Factory method for error responses."""
        return cls(
            request_id=request_id,
            response_id=uuid4(),
            status=status,
            error_details=error_details,
            model_id=model_id,
        )

    def is_successful(self) -> bool:
        """Check if response indicates success."""
        return self.status in {
            LLMResponseStatus.SUCCESS,
            LLMResponseStatus.PARTIAL_SUCCESS,
        }

    def get_total_tokens(self) -> int:
        """Get total token usage."""
        return self.usage_stats.get("total_tokens", 0)

    def get_input_tokens(self) -> int:
        """Get input token usage."""
        return self.usage_stats.get("input_tokens", 0)

    def get_output_tokens(self) -> int:
        """Get output token usage."""
        return self.usage_stats.get("output_tokens", 0)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(
        self,
        message: str,
        provider_id: Optional[ProviderId] = None,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.provider_id = provider_id
        self.error_code = error_code
        self.retry_after = retry_after


class RateLimitError(LLMProviderError):
    """Exception for rate limiting errors."""


class QuotaExceededError(LLMProviderError):
    """Exception for quota exceeded errors."""


class ModelUnavailableError(LLMProviderError):
    """Exception for model unavailability."""


class InvalidRequestError(LLMProviderError):
    """Exception for invalid request parameters."""


class ILLMProvider(ABC):
    """
    Abstract interface for Large Language Model providers.

    Defines the standard contract that all LLM provider implementations
    must follow. Ensures consistency, interoperability, and testability
    across different AI service vendors and custom implementations.

    This interface supports:
    - Synchronous and asynchronous text generation
    - Model capability discovery and validation
    - Token estimation and budget management
    - Streaming responses for real-time applications
    - Provider health monitoring and diagnostics
    - Error handling and retry strategies

    All implementations must handle:
    - Authentication and API key management
    - Rate limiting and quota enforcement
    - Request/response serialization
    - Error mapping to standard exceptions
    - Logging and observability

    Business Rules:
    - All methods must be thread-safe
    - Providers must validate requests before processing
    - Token budgets must be enforced strictly
    - Errors must be mapped to standard exception types
    - Async methods should support cancellation
    """

    @property
    @abstractmethod
    def provider_id(self) -> ProviderId:
        """Get the provider identifier."""

    @property
    @abstractmethod
    def supported_models(self) -> List[ModelId]:
        """Get list of models supported by this provider."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is currently available."""

    @abstractmethod
    async def generate_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        """
        Generate response asynchronously.

        Process LLM request and return structured response with usage statistics,
        cost estimation, and error handling. Enforces token budget constraints
        and implements proper retry logic.

        Args:
            request: Structured LLM request with all parameters
            budget: Optional token budget for enforcement

        Returns:
            LLM response with content, usage stats, and metadata

        Raises:
            RateLimitError: When rate limits are exceeded
            QuotaExceededError: When token/cost quotas are exceeded
            ModelUnavailableError: When requested model is unavailable
            InvalidRequestError: When request parameters are invalid
            LLMProviderError: For other provider-specific errors

        Business Rules:
        - Must validate request compatibility with model
        - Must check and enforce token budget constraints
        - Must implement exponential backoff for retries
        - Must track usage statistics accurately
        - Must handle streaming vs non-streaming requests
        """

    def generate(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        """
        Generate response synchronously.

        Synchronous wrapper around async generate method for compatibility
        with non-async codebases.

        Args:
            request: Structured LLM request
            budget: Optional token budget for enforcement

        Returns:
            LLM response with content and metadata
        """
        # Default implementation using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.generate_async(request, budget))
        finally:
            loop.close()

    @abstractmethod
    async def generate_stream_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> AsyncIterator[str]:
        """
        Generate streaming response asynchronously.

        Provides real-time token generation for interactive applications.
        Yields partial content as it's generated, enabling responsive UX.

        Args:
            request: LLM request with stream=True
            budget: Optional token budget for enforcement

        Yields:
            Partial content strings as they're generated

        Raises:
            Same exceptions as generate_async

        Business Rules:
        - Must yield content incrementally as received
        - Must handle partial token scenarios
        - Must provide final usage statistics
        - Must support cancellation/interruption
        """

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.

        Provides reasonably accurate token estimation for budget planning
        and request validation. Implementation should use provider-specific
        tokenization logic when available.

        Args:
            text: Text to analyze for tokens

        Returns:
            Estimated token count

        Business Rules:
        - Should be conservative (slightly overestimate)
        - Must handle different languages and encodings
        - Should account for special tokens
        """

    @abstractmethod
    def validate_request(self, request: LLMRequest) -> bool:
        """
        Validate request compatibility and parameters.

        Performs comprehensive validation of request parameters against
        provider capabilities, model limits, and business rules.

        Args:
            request: LLM request to validate

        Returns:
            True if request is valid, False otherwise

        Business Rules:
        - Must check model availability
        - Must validate parameter ranges
        - Must verify capability requirements
        - Should provide detailed error information
        """

    @abstractmethod
    def get_model_info(self, model_name: str) -> Optional[ModelId]:
        """
        Get detailed information about specific model.

        Args:
            model_name: Name of the model to query

        Returns:
            ModelId with capabilities and limits, or None if not found
        """

    @abstractmethod
    async def health_check_async(self) -> Dict[str, Any]:
        """
        Perform provider health check.

        Verifies provider availability, API connectivity, and service status.
        Used for monitoring, load balancing, and failover decisions.

        Returns:
            Health status information with metrics

        Example Return:
        {
            "status": "healthy",
            "response_time_ms": 150,
            "rate_limit_remaining": 1000,
            "models_available": 5,
            "last_error": None,
            "quota_utilization": 0.45
        }
        """

    def health_check(self) -> Dict[str, Any]:
        """Synchronous health check wrapper."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.health_check_async())
        finally:
            loop.close()

    # Optional methods with default implementations

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming responses."""
        return True

    def supports_function_calling(self) -> bool:
        """Check if provider supports function calling."""
        return any(
            model.supports_capability(ModelCapability.FUNCTION_CALLING)
            for model in self.supported_models
        )

    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get current rate limits for the provider.

        Returns:
            Dictionary with rate limit information

        Example:
        {
            "requests_per_minute": 60,
            "tokens_per_minute": 10000,
            "requests_per_day": 1000
        }
        """
        return {"requests_per_minute": 60, "tokens_per_minute": 10000}

    def get_pricing_info(self, model_id: ModelId) -> Dict[str, Decimal]:
        """
        Get pricing information for specific model.

        Args:
            model_id: Model to get pricing for

        Returns:
            Dictionary with pricing details
        """
        return {
            "input_token_cost": model_id.cost_per_input_token,
            "output_token_cost": model_id.cost_per_output_token,
            "currency": "USD",
        }

    def __str__(self) -> str:
        return f"LLMProvider[{self.provider_id.provider_name}]"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider_id={self.provider_id})"
