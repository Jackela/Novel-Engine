#!/usr/bin/env python3
"""
Rate Limiting Service Port for AI Gateway

Defines the abstract interface for rate limiting LLM operations.
Infrastructure adapters implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ...domain.value_objects.common import ProviderId


@dataclass
class RateLimitConfig:
    """
    Configuration for rate limiting policies.

    Defines limits and windows for different types of rate limiting
    including requests per minute, tokens per minute, and burst capacity.
    """

    requests_per_minute: int = 60
    tokens_per_minute: int = 10000
    burst_requests: int = 10
    burst_tokens: int = 2000
    window_seconds: int = 60

    def __post_init__(self) -> None:
        """Validate rate limit configuration."""
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.tokens_per_minute <= 0:
            raise ValueError("tokens_per_minute must be positive")
        if self.burst_requests <= 0:
            raise ValueError("burst_requests must be positive")
        if self.burst_tokens <= 0:
            raise ValueError("burst_tokens must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class RateLimitResult:
    """
    Result of rate limit check.

    Indicates whether request is allowed and provides details
    about current usage and time until reset.
    """

    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: Optional[int] = None
    current_requests: int = 0
    current_tokens: int = 0
    remaining_requests: int = 0
    remaining_tokens: int = 0
    reset_time: Optional[datetime] = None

    @property
    def is_rate_limited(self) -> bool:
        """Check if request was rate limited."""
        return not self.allowed


class IRateLimiter(ABC):
    """
    Abstract interface for rate limiting service.

    Provides rate limiting functionality to prevent quota exhaustion
    and ensure fair resource allocation across AI Gateway operations.
    """

    @abstractmethod
    async def check_rate_limit_async(
        self,
        provider_id: ProviderId,
        estimated_tokens: int,
        client_id: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check if request is allowed under rate limits.

        Args:
            provider_id: LLM provider identifier
            estimated_tokens: Estimated tokens for request
            client_id: Optional client identifier for per-client limits

        Returns:
            Rate limit check result
        """

    @abstractmethod
    async def record_request_async(
        self,
        provider_id: ProviderId,
        actual_tokens: int,
        client_id: Optional[str] = None,
    ) -> None:
        """
        Record completed request for rate limit tracking.

        Args:
            provider_id: LLM provider identifier
            actual_tokens: Actual tokens consumed
            client_id: Optional client identifier
        """

    @abstractmethod
    async def get_limits_async(self, provider_id: ProviderId) -> RateLimitConfig:
        """
        Get current rate limit configuration for provider.

        Args:
            provider_id: LLM provider identifier

        Returns:
            Current rate limit configuration
        """

    @abstractmethod
    async def update_limits_async(
        self, provider_id: ProviderId, config: RateLimitConfig
    ) -> None:
        """
        Update rate limit configuration for provider.

        Args:
            provider_id: LLM provider identifier
            config: New rate limit configuration
        """
