#!/usr/bin/env python3
"""
Rate Limiting Service for AI Gateway

Provides intelligent rate limiting to prevent API quota exhaustion and
ensure fair resource allocation across different consumers and operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import asyncio
import time
from collections import deque

from ...domain.value_objects.common import ProviderId, TokenBudget


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
    
    def __post_init__(self):
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


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    
    Provides smooth rate limiting with burst capacity using the
    token bucket algorithm. Thread-safe and suitable for async usage.
    """
    
    def __init__(
        self,
        capacity: int,
        refill_rate: float,
        initial_tokens: Optional[int] = None
    ):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens in bucket
            refill_rate: Tokens added per second
            initial_tokens: Initial token count (defaults to capacity)
        """
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._tokens = initial_tokens if initial_tokens is not None else capacity
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume_async(self, tokens: int) -> bool:
        """
        Attempt to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        async with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False
    
    async def peek_async(self) -> float:
        """Get current token count without consuming."""
        async with self._lock:
            self._refill()
            return self._tokens
    
    async def time_until_tokens_async(self, tokens: int) -> float:
        """
        Calculate time until specified tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Seconds until tokens are available (0 if already available)
        """
        async with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                return 0.0
            
            tokens_needed = tokens - self._tokens
            return tokens_needed / self._refill_rate
    
    def _refill(self) -> None:
        """Refill bucket based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        
        if elapsed > 0:
            tokens_to_add = elapsed * self._refill_rate
            self._tokens = min(self._capacity, self._tokens + tokens_to_add)
            self._last_refill = now


class SlidingWindowCounter:
    """
    Sliding window counter for request tracking.
    
    Maintains precise counts over sliding time windows using
    a deque-based approach for memory efficiency.
    """
    
    def __init__(self, window_seconds: int = 60):
        """
        Initialize sliding window counter.
        
        Args:
            window_seconds: Size of sliding window in seconds
        """
        self._window_seconds = window_seconds
        self._requests: deque = deque()
        self._lock = asyncio.Lock()
    
    async def add_request_async(self, tokens: int = 1) -> None:
        """Add request to window."""
        async with self._lock:
            now = time.time()
            self._requests.append((now, tokens))
            self._cleanup_expired()
    
    async def get_count_async(self) -> Tuple[int, int]:
        """
        Get current request and token counts in window.
        
        Returns:
            Tuple of (request_count, token_count)
        """
        async with self._lock:
            self._cleanup_expired()
            
            request_count = len(self._requests)
            token_count = sum(tokens for _, tokens in self._requests)
            
            return request_count, token_count
    
    async def time_until_space_async(
        self, 
        max_requests: int, 
        max_tokens: int
    ) -> float:
        """
        Calculate time until there's space for new request.
        
        Args:
            max_requests: Maximum requests in window
            max_tokens: Maximum tokens in window
            
        Returns:
            Seconds until space is available (0 if space available now)
        """
        async with self._lock:
            self._cleanup_expired()
            
            if not self._requests:
                return 0.0
            
            current_requests = len(self._requests)
            current_tokens = sum(tokens for _, tokens in self._requests)
            
            if current_requests < max_requests and current_tokens < max_tokens:
                return 0.0
            
            # Find oldest request that needs to expire to make space
            oldest_time = self._requests[0][0]
            return max(0.0, oldest_time + self._window_seconds - time.time())
    
    def _cleanup_expired(self) -> None:
        """Remove requests outside the sliding window."""
        now = time.time()
        cutoff = now - self._window_seconds
        
        while self._requests and self._requests[0][0] < cutoff:
            self._requests.popleft()


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
        client_id: Optional[str] = None
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
        pass
    
    @abstractmethod
    async def record_request_async(
        self,
        provider_id: ProviderId,
        actual_tokens: int,
        client_id: Optional[str] = None
    ) -> None:
        """
        Record completed request for rate limit tracking.
        
        Args:
            provider_id: LLM provider identifier
            actual_tokens: Actual tokens consumed
            client_id: Optional client identifier
        """
        pass
    
    @abstractmethod
    async def get_limits_async(self, provider_id: ProviderId) -> RateLimitConfig:
        """
        Get current rate limit configuration for provider.
        
        Args:
            provider_id: LLM provider identifier
            
        Returns:
            Current rate limit configuration
        """
        pass
    
    @abstractmethod
    async def update_limits_async(
        self,
        provider_id: ProviderId,
        config: RateLimitConfig
    ) -> None:
        """
        Update rate limit configuration for provider.
        
        Args:
            provider_id: LLM provider identifier  
            config: New rate limit configuration
        """
        pass


class TokenBucketRateLimiter(IRateLimiter):
    """
    Token bucket based rate limiter implementation.
    
    Combines token bucket algorithm for smooth rate limiting with
    sliding window counters for precise limit enforcement.
    """
    
    def __init__(self, default_config: Optional[RateLimitConfig] = None):
        """
        Initialize token bucket rate limiter.
        
        Args:
            default_config: Default rate limit configuration
        """
        self._default_config = default_config or RateLimitConfig()
        self._provider_configs: Dict[str, RateLimitConfig] = {}
        self._provider_buckets: Dict[str, Tuple[TokenBucket, TokenBucket]] = {}
        self._provider_windows: Dict[str, SlidingWindowCounter] = {}
        self._client_windows: Dict[str, SlidingWindowCounter] = {}
        self._lock = asyncio.Lock()
    
    async def check_rate_limit_async(
        self,
        provider_id: ProviderId,
        estimated_tokens: int,
        client_id: Optional[str] = None
    ) -> RateLimitResult:
        """Check rate limits using token buckets and sliding windows."""
        provider_key = provider_id.provider_name
        config = await self._get_config_async(provider_key)
        
        # Get or create buckets and windows
        request_bucket, token_bucket = await self._get_buckets_async(provider_key, config)
        provider_window = await self._get_provider_window_async(provider_key)
        
        # Check token bucket limits (burst capacity)
        can_consume_request = await request_bucket.consume_async(1)
        can_consume_tokens = await token_bucket.consume_async(estimated_tokens)
        
        if not can_consume_request:
            retry_after = await request_bucket.time_until_tokens_async(1)
            return RateLimitResult(
                allowed=False,
                reason="Request rate limit exceeded (burst)",
                retry_after_seconds=int(retry_after) + 1
            )
        
        if not can_consume_tokens:
            retry_after = await token_bucket.time_until_tokens_async(estimated_tokens)
            return RateLimitResult(
                allowed=False,
                reason="Token rate limit exceeded (burst)",
                retry_after_seconds=int(retry_after) + 1
            )
        
        # Check sliding window limits (sustained rate)
        current_requests, current_tokens = await provider_window.get_count_async()
        
        if current_requests >= config.requests_per_minute:
            retry_after = await provider_window.time_until_space_async(
                config.requests_per_minute - 1, 
                config.tokens_per_minute
            )
            return RateLimitResult(
                allowed=False,
                reason="Request rate limit exceeded (sustained)",
                retry_after_seconds=int(retry_after) + 1,
                current_requests=current_requests
            )
        
        if current_tokens + estimated_tokens > config.tokens_per_minute:
            retry_after = await provider_window.time_until_space_async(
                config.requests_per_minute,
                config.tokens_per_minute - estimated_tokens
            )
            return RateLimitResult(
                allowed=False,
                reason="Token rate limit exceeded (sustained)",
                retry_after_seconds=int(retry_after) + 1,
                current_tokens=current_tokens
            )
        
        # Request is allowed
        return RateLimitResult(
            allowed=True,
            current_requests=current_requests + 1,
            current_tokens=current_tokens + estimated_tokens,
            remaining_requests=max(0, config.requests_per_minute - current_requests - 1),
            remaining_tokens=max(0, config.tokens_per_minute - current_tokens - estimated_tokens),
            reset_time=datetime.now() + timedelta(seconds=config.window_seconds)
        )
    
    async def record_request_async(
        self,
        provider_id: ProviderId,
        actual_tokens: int,
        client_id: Optional[str] = None
    ) -> None:
        """Record completed request in sliding windows."""
        provider_key = provider_id.provider_name
        
        # Record in provider window
        provider_window = await self._get_provider_window_async(provider_key)
        await provider_window.add_request_async(actual_tokens)
        
        # Record in client window if specified
        if client_id:
            client_window = await self._get_client_window_async(client_id)
            await client_window.add_request_async(actual_tokens)
    
    async def get_limits_async(self, provider_id: ProviderId) -> RateLimitConfig:
        """Get rate limit configuration for provider."""
        provider_key = provider_id.provider_name
        return await self._get_config_async(provider_key)
    
    async def update_limits_async(
        self,
        provider_id: ProviderId,
        config: RateLimitConfig
    ) -> None:
        """Update rate limit configuration and recreate buckets."""
        provider_key = provider_id.provider_name
        
        async with self._lock:
            self._provider_configs[provider_key] = config
            
            # Recreate buckets with new configuration
            if provider_key in self._provider_buckets:
                del self._provider_buckets[provider_key]
    
    async def _get_config_async(self, provider_key: str) -> RateLimitConfig:
        """Get configuration for provider."""
        async with self._lock:
            return self._provider_configs.get(provider_key, self._default_config)
    
    async def _get_buckets_async(
        self, 
        provider_key: str, 
        config: RateLimitConfig
    ) -> Tuple[TokenBucket, TokenBucket]:
        """Get or create token buckets for provider."""
        async with self._lock:
            if provider_key not in self._provider_buckets:
                request_bucket = TokenBucket(
                    capacity=config.burst_requests,
                    refill_rate=config.requests_per_minute / 60.0
                )
                
                token_bucket = TokenBucket(
                    capacity=config.burst_tokens,
                    refill_rate=config.tokens_per_minute / 60.0
                )
                
                self._provider_buckets[provider_key] = (request_bucket, token_bucket)
            
            return self._provider_buckets[provider_key]
    
    async def _get_provider_window_async(self, provider_key: str) -> SlidingWindowCounter:
        """Get or create sliding window for provider."""
        async with self._lock:
            if provider_key not in self._provider_windows:
                config = await self._get_config_async(provider_key)
                self._provider_windows[provider_key] = SlidingWindowCounter(config.window_seconds)
            
            return self._provider_windows[provider_key]
    
    async def _get_client_window_async(self, client_id: str) -> SlidingWindowCounter:
        """Get or create sliding window for client."""
        async with self._lock:
            if client_id not in self._client_windows:
                self._client_windows[client_id] = SlidingWindowCounter(60)  # 1 minute window
            
            return self._client_windows[client_id]