#!/usr/bin/env python3
"""
Retry and Fallback Policy Port for AI Gateway

Defines the abstract interface for retry mechanisms and circuit breakers.
Infrastructure adapters implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

from ...domain.services.llm_provider import LLMRequest, LLMResponse, LLMResponseStatus
from ...domain.value_objects.common import ProviderId


class RetryReason(Enum):
    """
    Enumeration of reasons for retrying requests.

    Used for determining appropriate retry strategies and
    tracking retry patterns for optimization.
    """

    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN_ERROR = "unknown_error"

    @classmethod
    def from_response_status(cls, status: LLMResponseStatus) -> "RetryReason":
        """Map response status to retry reason."""
        mapping = {
            LLMResponseStatus.RATE_LIMITED: cls.RATE_LIMITED,
            LLMResponseStatus.TIMEOUT: cls.TIMEOUT,
            LLMResponseStatus.MODEL_UNAVAILABLE: cls.MODEL_UNAVAILABLE,
            LLMResponseStatus.QUOTA_EXCEEDED: cls.QUOTA_EXCEEDED,
            LLMResponseStatus.FAILED: cls.SERVER_ERROR,
            LLMResponseStatus.INVALID_REQUEST: cls.UNKNOWN_ERROR,
        }
        return mapping.get(status, cls.UNKNOWN_ERROR)


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Defines retry limits, delays, and conditions for different
    types of failures and operations.
    """

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1

    # Specific configurations for different reasons
    retryable_reasons: Optional[List[RetryReason]] = None
    reason_specific_delays: Optional[Dict[RetryReason, float]] = None
    reason_specific_max_attempts: Optional[Dict[RetryReason, int]] = None

    def __post_init__(self) -> None:
        """Initialize defaults for optional fields."""
        if self.retryable_reasons is None:
            self.retryable_reasons = [
                RetryReason.RATE_LIMITED,
                RetryReason.TIMEOUT,
                RetryReason.SERVER_ERROR,
                RetryReason.NETWORK_ERROR,
            ]

        if self.reason_specific_delays is None:
            self.reason_specific_delays = {
                RetryReason.RATE_LIMITED: 30.0,
                RetryReason.TIMEOUT: 5.0,
                RetryReason.SERVER_ERROR: 2.0,
                RetryReason.NETWORK_ERROR: 1.0,
            }

        if self.reason_specific_max_attempts is None:
            self.reason_specific_max_attempts = {
                RetryReason.RATE_LIMITED: 5,
                RetryReason.AUTHENTICATION_ERROR: 1,
                RetryReason.QUOTA_EXCEEDED: 1,
            }

    def is_retryable(self, reason: RetryReason) -> bool:
        """Check if reason is retryable."""
        return self.retryable_reasons is not None and reason in self.retryable_reasons

    def get_max_attempts(self, reason: RetryReason) -> int:
        """Get max attempts for specific reason."""
        if self.reason_specific_max_attempts is None:
            return self.max_attempts
        return self.reason_specific_max_attempts.get(reason, self.max_attempts)


@dataclass
class CircuitBreakerState:
    """
    State tracking for circuit breaker pattern.

    Monitors failure rates and automatically opens/closes
    the circuit to prevent cascading failures.
    """

    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    # Configuration
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == "OPEN"

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self.state == "HALF_OPEN"

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self.state == "CLOSED"


@dataclass
class RetryAttempt:
    """
    Record of a retry attempt with context and results.
    """

    attempt_number: int
    timestamp: datetime
    reason: RetryReason
    delay_seconds: float
    success: bool
    error_message: Optional[str] = None
    response_status: Optional[LLMResponseStatus] = None


@dataclass
class RetryResult:
    """
    Result of retry operation with comprehensive details.
    """

    success: bool
    final_response: Optional[LLMResponse]
    total_attempts: int
    total_time_seconds: float
    attempts: List[RetryAttempt] = field(default_factory=list)
    circuit_breaker_opened: bool = False
    fallback_used: bool = False
    fallback_provider: Optional[ProviderId] = None


class IRetryPolicy(ABC):
    """
    Abstract interface for retry policy service.

    Provides retry mechanisms, circuit breaker patterns, and
    fallback strategies for resilient LLM operations.
    """

    @abstractmethod
    async def execute_with_retry_async(
        self,
        operation: Callable[[], Awaitable[LLMResponse]],
        request: LLMRequest,
        provider_id: ProviderId,
    ) -> RetryResult:
        """
        Execute operation with retry logic.

        Args:
            operation: Async operation to execute with retries
            request: Original LLM request
            provider_id: Provider identifier for circuit breaker tracking

        Returns:
            Retry result with final response and attempt details
        """

    @abstractmethod
    async def should_retry_async(
        self, response: LLMResponse, attempt: int, provider_id: ProviderId
    ) -> Tuple[bool, RetryReason]:
        """
        Determine if operation should be retried.

        Args:
            response: Response from failed operation
            attempt: Current attempt number
            provider_id: Provider identifier

        Returns:
            Tuple of (should_retry, retry_reason)
        """

    @abstractmethod
    async def get_circuit_breaker_status_async(
        self, provider_id: ProviderId
    ) -> CircuitBreakerState:
        """
        Get current circuit breaker status for provider.

        Args:
            provider_id: Provider identifier

        Returns:
            Current circuit breaker state
        """
