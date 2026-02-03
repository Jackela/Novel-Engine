#!/usr/bin/env python3
"""
Retry and Fallback Policy Adapter for AI Gateway

Provides intelligent retry mechanisms, circuit breaker patterns, and
fallback strategies to ensure resilient LLM operations across providers.
"""

import asyncio
import random
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from ...application.ports.retry_policy_port import (
    CircuitBreakerState,
    IRetryPolicy,
    RetryAttempt,
    RetryConfig,
    RetryReason,
    RetryResult,
)
from ...domain.services.llm_provider import LLMRequest, LLMResponse, LLMResponseStatus
from ...domain.value_objects.common import ProviderId


class MutableCircuitBreakerState:
    """
    Mutable state tracking for circuit breaker pattern.

    This adapter-specific implementation provides state mutation methods
    that the immutable port-level CircuitBreakerState doesn't have.
    """

    def __init__(
        self,
        state: str = "CLOSED",
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ):
        self.state = state
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds

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

    def to_circuit_breaker_state(self) -> CircuitBreakerState:
        """Convert to immutable CircuitBreakerState for port interface."""
        return CircuitBreakerState(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            last_failure_time=self.last_failure_time,
            last_success_time=self.last_success_time,
            failure_threshold=self.failure_threshold,
            success_threshold=self.success_threshold,
            timeout_seconds=self.timeout_seconds,
        )


class RetryConfigHelper:
    """Helper for calculating retry behavior from RetryConfig."""

    @staticmethod
    def calculate_delay(config: RetryConfig, attempt: int, reason: RetryReason) -> float:
        """Calculate delay for retry attempt using exponential backoff with jitter."""
        if config.reason_specific_delays:
            base_delay = config.reason_specific_delays.get(
                reason, config.initial_delay_seconds
            )
        else:
            base_delay = config.initial_delay_seconds

        # Exponential backoff
        delay = base_delay * (config.exponential_base ** (attempt - 1))
        delay = min(delay, config.max_delay_seconds)

        # Add jitter to prevent thundering herd
        jitter = delay * config.jitter_factor * random.random()
        delay += jitter

        return delay


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
        self._circuit_breakers: Dict[str, MutableCircuitBreakerState] = {}
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

                if not should_retry or attempt_num >= config.get_max_attempts(
                    retry_reason
                ):
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

    async def update_config_async(
        self, provider_id: ProviderId, config: RetryConfig
    ) -> None:
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
                self._circuit_breakers[provider_key] = CircuitBreakerState(
                    **self._cb_config
                )

    async def _get_config_async(self, provider_key: str) -> RetryConfig:
        """Get retry configuration for provider."""
        async with self._lock:
            return self._provider_configs.get(provider_key, self._default_config)

    async def _get_circuit_breaker_async(
        self, provider_key: str
    ) -> CircuitBreakerState:
        """Get or create circuit breaker for provider."""
        async with self._lock:
            if provider_key not in self._circuit_breakers:
                self._circuit_breakers[provider_key] = CircuitBreakerState(
                    **self._cb_config
                )

            return self._circuit_breakers[provider_key]
