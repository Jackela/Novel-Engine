#!/usr/bin/env python3
"""
Retry and Fallback Policy Service for AI Gateway

Provides intelligent retry mechanisms, circuit breaker patterns, and
fallback strategies to ensure resilient LLM operations across providers.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

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
    retryable_reasons: List[RetryReason] = None
    reason_specific_delays: Dict[RetryReason, float] = None
    reason_specific_max_attempts: Dict[RetryReason, int] = None

    def __post_init__(self):
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
                RetryReason.RATE_LIMITED: 30.0,  # Rate limits often have longer backoff
                RetryReason.TIMEOUT: 5.0,
                RetryReason.SERVER_ERROR: 2.0,
                RetryReason.NETWORK_ERROR: 1.0,
            }

        if self.reason_specific_max_attempts is None:
            self.reason_specific_max_attempts = {
                RetryReason.RATE_LIMITED: 5,  # More attempts for rate limits
                RetryReason.AUTHENTICATION_ERROR: 1,  # Don't retry auth errors
                RetryReason.QUOTA_EXCEEDED: 1,  # Don't retry quota exceeded
            }

    def is_retryable(self, reason: RetryReason) -> bool:
        """Check if reason is retryable."""
        return reason in self.retryable_reasons

    def get_max_attempts(self, reason: RetryReason) -> int:
        """Get max attempts for specific reason."""
        return self.reason_specific_max_attempts.get(reason, self.max_attempts)

    def calculate_delay(self, attempt: int, reason: RetryReason) -> float:
        """
        Calculate delay for retry attempt.

        Uses exponential backoff with jitter and reason-specific overrides.
        """
        base_delay = self.reason_specific_delays.get(reason, self.initial_delay_seconds)

        # Exponential backoff
        delay = base_delay * (self.exponential_base ** (attempt - 1))
        delay = min(delay, self.max_delay_seconds)

        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_factor * random.random()
        delay += jitter

        return delay


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

    def should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to half-open."""
        if not self.is_open:
            return False

        if not self.last_failure_time:
            return True

        elapsed = datetime.now() - self.last_failure_time
        return elapsed.total_seconds() >= self.timeout_seconds

    def record_success(self) -> None:
        """Record successful operation."""
        self.success_count += 1
        self.last_success_time = datetime.now()

        if self.is_half_open and self.success_count >= self.success_threshold:
            self.state = "CLOSED"
            self.failure_count = 0
            self.success_count = 0

    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.is_closed and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
        elif self.is_half_open:
            self.state = "OPEN"
            self.success_count = 0

    def attempt_reset(self) -> None:
        """Attempt to reset circuit to half-open."""
        if self.should_attempt_reset():
            self.state = "HALF_OPEN"
            self.success_count = 0


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
    attempts: List[RetryAttempt]
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
        pass

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
        pass

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
        pass


class ExponentialBackoffRetry(IRetryPolicy):
    """
    Exponential backoff retry policy with circuit breaker.

    Implements intelligent retry logic with exponential backoff,
    jitter, circuit breaker pattern, and comprehensive tracking.
    """

    def __init__(
        self,
        default_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize retry policy.

        Args:
            default_config: Default retry configuration
            circuit_breaker_config: Circuit breaker settings
        """
        self._default_config = default_config or RetryConfig()
        self._provider_configs: Dict[str, RetryConfig] = {}
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._lock = asyncio.Lock()

        # Circuit breaker defaults
        self._cb_config = circuit_breaker_config or {
            "failure_threshold": 5,
            "success_threshold": 2,
            "timeout_seconds": 60,
        }

    async def execute_with_retry_async(
        self,
        operation: Callable[[], Awaitable[LLMResponse]],
        request: LLMRequest,
        provider_id: ProviderId,
    ) -> RetryResult:
        """Execute operation with comprehensive retry logic."""
        provider_key = provider_id.provider_name
        config = await self._get_config_async(provider_key)
        circuit_breaker = await self._get_circuit_breaker_async(provider_key)

        start_time = time.time()
        attempts: List[RetryAttempt] = []

        # Check circuit breaker before starting
        if circuit_breaker.is_open:
            if not circuit_breaker.should_attempt_reset():
                return RetryResult(
                    success=False,
                    final_response=None,
                    total_attempts=0,
                    total_time_seconds=0.0,
                    attempts=[],
                    circuit_breaker_opened=True,
                )
            else:
                circuit_breaker.attempt_reset()

        for attempt_num in range(1, config.max_attempts + 1):
            time.time()

            try:
                # Execute operation
                response = await operation()

                # Check if response indicates success
                if response.status == LLMResponseStatus.SUCCESS:
                    # Record successful attempt
                    circuit_breaker.record_success()

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        timestamp=datetime.now(),
                        reason=RetryReason.UNKNOWN_ERROR,  # No error
                        delay_seconds=0.0,
                        success=True,
                        response_status=response.status,
                    )
                    attempts.append(attempt)

                    return RetryResult(
                        success=True,
                        final_response=response,
                        total_attempts=attempt_num,
                        total_time_seconds=time.time() - start_time,
                        attempts=attempts,
                    )

                # Check if should retry
                should_retry, retry_reason = await self.should_retry_async(
                    response, attempt_num, provider_id
                )

                if not should_retry or attempt_num >= config.get_max_attempts(retry_reason):
                    # Record final failure
                    circuit_breaker.record_failure()

                    attempt = RetryAttempt(
                        attempt_number=attempt_num,
                        timestamp=datetime.now(),
                        reason=retry_reason,
                        delay_seconds=0.0,
                        success=False,
                        error_message=response.error_details,
                        response_status=response.status,
                    )
                    attempts.append(attempt)

                    return RetryResult(
                        success=False,
                        final_response=response,
                        total_attempts=attempt_num,
                        total_time_seconds=time.time() - start_time,
                        attempts=attempts,
                    )

                # Calculate delay for retry
                delay = config.calculate_delay(attempt_num, retry_reason)

                # Record retry attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    reason=retry_reason,
                    delay_seconds=delay,
                    success=False,
                    error_message=response.error_details,
                    response_status=response.status,
                )
                attempts.append(attempt)

                # Wait before retry
                await asyncio.sleep(delay)

            except Exception as e:
                # Handle operation exceptions
                circuit_breaker.record_failure()

                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now(),
                    reason=RetryReason.NETWORK_ERROR,
                    delay_seconds=0.0,
                    success=False,
                    error_message=str(e),
                )
                attempts.append(attempt)

                # Don't retry on exceptions for now
                break

        # All retries exhausted
        return RetryResult(
            success=False,
            final_response=attempts[-1].response_status if attempts else None,
            total_attempts=len(attempts),
            total_time_seconds=time.time() - start_time,
            attempts=attempts,
        )

    async def should_retry_async(
        self, response: LLMResponse, attempt: int, provider_id: ProviderId
    ) -> Tuple[bool, RetryReason]:
        """Determine retry eligibility based on response and configuration."""
        provider_key = provider_id.provider_name
        config = await self._get_config_async(provider_key)

        # Map response status to retry reason
        retry_reason = RetryReason.from_response_status(response.status)

        # Check if reason is retryable
        if not config.is_retryable(retry_reason):
            return False, retry_reason

        # Check attempt limits
        max_attempts = config.get_max_attempts(retry_reason)
        if attempt >= max_attempts:
            return False, retry_reason

        # Check circuit breaker
        circuit_breaker = await self._get_circuit_breaker_async(provider_key)
        if circuit_breaker.is_open and not circuit_breaker.should_attempt_reset():
            return False, retry_reason

        return True, retry_reason

    async def get_circuit_breaker_status_async(
        self, provider_id: ProviderId
    ) -> CircuitBreakerState:
        """Get current circuit breaker status."""
        provider_key = provider_id.provider_name
        return await self._get_circuit_breaker_async(provider_key)

    async def update_config_async(self, provider_id: ProviderId, config: RetryConfig) -> None:
        """
        Update retry configuration for specific provider.

        Args:
            provider_id: Provider identifier
            config: New retry configuration
        """
        provider_key = provider_id.provider_name
        async with self._lock:
            self._provider_configs[provider_key] = config

    async def reset_circuit_breaker_async(self, provider_id: ProviderId) -> None:
        """
        Manually reset circuit breaker for provider.

        Args:
            provider_id: Provider identifier
        """
        provider_key = provider_id.provider_name
        async with self._lock:
            if provider_key in self._circuit_breakers:
                self._circuit_breakers[provider_key] = CircuitBreakerState(**self._cb_config)

    async def _get_config_async(self, provider_key: str) -> RetryConfig:
        """Get retry configuration for provider."""
        async with self._lock:
            return self._provider_configs.get(provider_key, self._default_config)

    async def _get_circuit_breaker_async(self, provider_key: str) -> CircuitBreakerState:
        """Get or create circuit breaker for provider."""
        async with self._lock:
            if provider_key not in self._circuit_breakers:
                self._circuit_breakers[provider_key] = CircuitBreakerState(**self._cb_config)

            return self._circuit_breakers[provider_key]
