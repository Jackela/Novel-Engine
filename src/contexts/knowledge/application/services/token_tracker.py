"""
Token Tracker Service

Warzone 4: AI Brain - BRAIN-034A
Middleware/decorator for tracking LLM token usage and costs.

Constitution Compliance:
- Article II (Hexagonal): Application service with no infrastructure dependencies
- Article V (SOLID): SRP - token tracking and cost calculation only

Usage:
    >>> tracker = TokenTracker(repository, model_registry)
    >>> # As decorator
    >>> @tracker.track_llm_call()
    >>> async def generate_text(prompt: str) -> str:
    >>>     # LLM call here
    >>>     return response
    >>>
    >>> # As context manager
    >>> async with tracker.track_call("gpt-4o", user_id="user-123") as ctx:
    >>>     result = await llm_client.generate(request)
    >>>     ctx.record_result(result)
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, TypeVar

import structlog

from ...application.ports.i_token_usage_repository import ITokenUsageRepository
from ...domain.models.model_registry import LLMProvider
from ...domain.models.token_usage import TokenUsage, TokenUsageStats

# Need LLMResponse at runtime for decorator isinstance checks
from ..services.model_registry import ModelRegistry
from ..services.token_counter import TokenCounter

logger = structlog.get_logger()


T = TypeVar("T")


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class TrackingContext:
    """
    Context for tracking a single LLM call.

    Attributes:
        provider: LLM provider being used
        model_name: Model name being used
        workspace_id: Optional workspace identifier
        user_id: Optional user identifier
        request_id: Optional request identifier for correlation
        metadata: Additional metadata to attach to the usage record
        start_time: Call start timestamp
        input_tokens: Pre-counted input tokens (if available)
        token_counter: TokenCounter instance for estimation
        _usage: The recorded usage (set after recording)
    """

    provider: str | LLMProvider
    model_name: str
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=_utcnow)
    input_tokens: int | None = None
    token_counter: TokenCounter = field(default_factory=TokenCounter)
    _usage: TokenUsage | None = field(default=None, init=False, repr=False)

    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds() * 1000

    def record_success(
        self,
        input_tokens: int | None = None,
        output_tokens: int = 0,
        cost_per_1m_input: float = 0.0,
        cost_per_1m_output: float = 0.0,
        response_text: str | None = None,
    ) -> TokenUsage:
        """
        Record a successful LLM call.

        Args:
            input_tokens: Actual input tokens (uses pre-counted or estimates if None)
            output_tokens: Actual output tokens
            cost_per_1m_input: Cost per 1M input tokens
            cost_per_1m_output: Cost per 1M output tokens
            response_text: Response text (for token estimation if needed)

        Returns:
            TokenUsage record
        """
        # Determine input tokens
        if input_tokens is not None:
            final_input_tokens = input_tokens
        elif self.input_tokens is not None:
            final_input_tokens = self.input_tokens
        elif response_text is not None:
            # Estimate from combined text
            prompt_length = len(str(self.metadata.get("prompt", "")))
            final_input_tokens = self.token_counter.count(
                response_text[:prompt_length] if prompt_length > 0 else ""
            ).token_count
        else:
            final_input_tokens = 0

        # Estimate output tokens from response text if not provided
        if output_tokens == 0 and response_text is not None:
            output_tokens = self.token_counter.count(response_text).token_count

        latency_ms = self.elapsed_ms

        # Normalize provider to string
        if isinstance(self.provider, str):
            provider_str = self.provider
        else:
            provider_str = str(self.provider)  # type: ignore[arg-type]

        self._usage = TokenUsage.create(
            provider=provider_str,
            model_name=self.model_name,
            input_tokens=final_input_tokens,
            output_tokens=output_tokens,
            cost_per_1m_input=cost_per_1m_input,
            cost_per_1m_output=cost_per_1m_output,
            latency_ms=latency_ms,
            success=True,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            request_id=self.request_id,
            metadata=self.metadata,
            timestamp=self.start_time,
        )

        return self._usage

    def record_failure(
        self,
        error_message: str,
        input_tokens: int | None = None,
        cost_per_1m_input: float = 0.0,
        cost_per_1m_output: float = 0.0,
    ) -> TokenUsage:
        """
        Record a failed LLM call.

        Args:
            error_message: Error description
            input_tokens: Actual input tokens (uses pre-counted or estimates if None)
            cost_per_1m_input: Cost per 1M input tokens
            cost_per_1m_output: Cost per 1M output tokens

        Returns:
            TokenUsage record
        """
        # Determine input tokens
        if input_tokens is not None:
            final_input_tokens = input_tokens
        elif self.input_tokens is not None:
            final_input_tokens = self.input_tokens
        else:
            final_input_tokens = 0

        latency_ms = self.elapsed_ms

        # Normalize provider to string
        if isinstance(self.provider, str):
            provider_str = self.provider
        else:
            provider_str = str(self.provider)  # type: ignore[arg-type]

        self._usage = TokenUsage.create(
            provider=provider_str,
            model_name=self.model_name,
            input_tokens=final_input_tokens,
            output_tokens=0,
            cost_per_1m_input=cost_per_1m_input,
            cost_per_1m_output=cost_per_1m_output,
            latency_ms=latency_ms,
            success=False,
            error_message=error_message,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            request_id=self.request_id,
            metadata=self.metadata,
            timestamp=self.start_time,
        )

        return self._usage

    @property
    def usage(self) -> TokenUsage | None:
        """Get the recorded usage, if any."""
        return self._usage


@dataclass
class TokenTrackerConfig:
    """
    Configuration for TokenTracker.

    Attributes:
        enabled: Whether tracking is enabled
        count_input_tokens: Whether to count input tokens when not provided
        estimate_missing_tokens: Whether to estimate tokens when API doesn't return them
        batch_size: Number of records to batch before saving
        flush_interval_seconds: Interval for auto-flushing batched records
        track_individual_calls: Track individual calls (vs. only aggregates)
    """

    enabled: bool = True
    count_input_tokens: bool = True
    estimate_missing_tokens: bool = True
    batch_size: int = 100
    flush_interval_seconds: float = 10.0
    track_individual_calls: bool = True


class TokenTracker:
    """
    Service for tracking LLM token usage and costs.

    Why:
        - Centralizes token usage tracking across all LLM calls
        - Provides accurate cost calculation using model pricing
        - Enables usage analytics and budget monitoring
        - Supports per-workspace and per-user tracking

    Features:
        - Decorator for automatic tracking
        - Context manager for manual tracking
        - Token estimation when APIs don't return counts
        - Batch writes for efficiency
        - Graceful degradation (tracking failures don't break LLM calls)

    Example (decorator):
        >>> tracker = TokenTracker(repository, model_registry)
        >>>
        >>> @tracker.track_llm_call(provider="openai", model_name="gpt-4o")
        >>> async def generate_story(scene: str) -> str:
        >>>     return await llm_client.generate(scene)

    Example (context manager):
        >>> async with tracker.track_call("gpt-4o") as ctx:
        >>>     response = await llm_client.generate(request)
        >>>     ctx.record_success(
        >>>         input_tokens=response.usage.prompt_tokens,
        >>>         output_tokens=response.usage.completion_tokens,
        >>>     )
    """

    def __init__(
        self,
        repository: ITokenUsageRepository,
        model_registry: ModelRegistry,
        config: TokenTrackerConfig | None = None,
    ) -> None:
        """
        Initialize the token tracker.

        Args:
            repository: Repository for persisting usage records
            model_registry: Model registry for pricing information
            config: Optional tracker configuration
        """
        self._repository = repository
        self._model_registry = model_registry
        self._config = config or TokenTrackerConfig()
        self._token_counter = TokenCounter()
        self._pending_records: list[TokenUsage] = []
        self._flush_task: asyncio.Task[None] | None = None
        self._flush_lock = asyncio.Lock()

        # Start background flush task if batching is enabled
        if self._config.batch_size > 1 and self._config.flush_interval_seconds > 0:
            self._start_flush_task()

        logger.info(
            "token_tracker_initialized",
            enabled=self._config.enabled,
            batch_size=self._config.batch_size,
            track_individual=self._config.track_individual_calls,
        )

    def _start_flush_task(self) -> None:
        """Start background task to periodically flush pending records."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError as exc:
            logger.warning(
                "token_tracker_flush_not_started",
                reason="no_event_loop",
                error=str(exc),
            )
            return

        if loop.is_closed():
            logger.warning(
                "token_tracker_flush_not_started",
                reason="event_loop_closed",
            )
            return

        async def flush_loop() -> None:
            while True:
                try:
                    await asyncio.sleep(self._config.flush_interval_seconds)
                    await self._flush_pending()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning("token_tracker_flush_failed", error=str(e))

        self._flush_task = loop.create_task(flush_loop())

    async def _flush_pending(self) -> None:
        """Flush pending records to repository."""
        if not self._pending_records:
            return

        async with self._flush_lock:
            if not self._pending_records:
                return

            records = self._pending_records.copy()
            self._pending_records.clear()

        try:
            await self._repository.save_batch(records)
            logger.debug("token_tracker_flushed", count=len(records))
        except Exception as e:
            logger.error("token_tracker_save_failed", count=len(records), error=str(e))
            # Re-add to pending on failure
            self._pending_records.extend(records)

    async def record(self, usage: TokenUsage) -> None:
        """
        Record a token usage event.

        Args:
            usage: TokenUsage record to save
        """
        if not self._config.enabled:
            return

        if self._config.batch_size > 1:
            self._pending_records.append(usage)

            if len(self._pending_records) >= self._config.batch_size:
                await self._flush_pending()
        else:
            try:
                await self._repository.save(usage)
            except Exception as e:
                logger.warning(
                    "token_tracker_record_failed", usage_id=usage.id, error=str(e)
                )

    async def shutdown(self) -> None:
        """
        Shutdown the tracker and flush pending records.

        Should be called before application exit.
        """
        # Cancel background task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush remaining records
        await self._flush_pending()

        logger.info("token_tracker_shutdown")

    @asynccontextmanager
    async def track_call(
        self,
        model_ref: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        prompt: str | None = None,
    ):
        """
        Context manager for tracking an LLM call.

        Args:
            model_ref: Model reference (alias or provider:model)
            workspace_id: Optional workspace identifier
            user_id: Optional user identifier
            request_id: Optional request identifier
            metadata: Additional metadata
            prompt: Optional prompt text for input token estimation

        Yields:
            TrackingContext for recording results

        Example:
            >>> async with tracker.track_call("gpt-4o", prompt="Write a story") as ctx:
            >>>     response = await llm_client.generate(request)
            >>>     ctx.record_success(
            >>>         input_tokens=response.usage.prompt_tokens,
            >>>         output_tokens=response.usage.completion_tokens,
            >>>     )
        """
        # Resolve model reference
        lookup_result = self._model_registry.resolve_model(model_ref)
        model_def = lookup_result.model_definition

        # Pre-count input tokens if prompt provided
        input_tokens = None
        if prompt and self._config.count_input_tokens:
            input_tokens = self._token_counter.count(
                prompt,
                model=model_def.model_name if model_def else model_ref,
            ).token_count

        # Create tracking context
        ctx = TrackingContext(
            provider=lookup_result.provider,
            model_name=lookup_result.model_name,
            workspace_id=workspace_id,
            user_id=user_id,
            request_id=request_id,
            metadata=metadata or {},
            input_tokens=input_tokens,
        )

        try:
            yield ctx
        finally:
            # Record usage if it was set
            if ctx.usage and self._config.track_individual_calls:
                await self.record(ctx.usage)

    def track_llm_call(
        self,
        model_ref: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Decorator for automatic tracking of LLM calls.

        Args:
            model_ref: Model reference (if None, inferred from function args)
            workspace_id: Optional workspace identifier
            user_id: Optional user identifier
            metadata: Additional metadata

        The decorated function should:
            - Be an async function
            - Accept LLMRequest as first argument or have 'request' parameter
            - Return LLMResponse

        Example:
            >>> @tracker.track_llm_call(model_ref="gpt-4o")
            >>> async def generate_scene(request: LLMRequest) -> LLMResponse:
            >>>     return await llm_client.generate(request)
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self._config.enabled:
                    return await func(*args, **kwargs)

                start_time = time.monotonic()

                # Try to extract model_ref from arguments
                actual_model_ref = model_ref
                if actual_model_ref is None:
                    # Check for 'request' parameter
                    request = kwargs.get("request")
                    if request is None and args:
                        request = args[0]
                    if hasattr(request, "model"):
                        actual_model_ref = request.model

                # Try to extract workspace_id and user_id
                actual_workspace_id = workspace_id or kwargs.get("workspace_id")
                actual_user_id = user_id or kwargs.get("user_id")

                try:
                    result = await func(*args, **kwargs)
                    latency_ms = (time.monotonic() - start_time) * 1000

                    # Extract token usage from result
                    input_tokens = 0
                    output_tokens = 0

                    if hasattr(result, "tokens_used") and result.tokens_used:
                        # LLMResponse has combined tokens
                        input_tokens = (
                            getattr(result, "input_tokens", 0)
                            or result.tokens_used // 2
                        )
                        output_tokens = (
                            getattr(result, "output_tokens", 0)
                            or result.tokens_used - input_tokens
                        )
                    elif hasattr(result, "usage"):
                        usage = result.usage
                        if isinstance(usage, dict):
                            input_tokens = usage.get("prompt_tokens", 0) or usage.get(
                                "input_tokens", 0
                            )
                            output_tokens = usage.get(
                                "completion_tokens", 0
                            ) or usage.get("output_tokens", 0)

                    # Get model pricing
                    cost_per_1m_input = 0.0
                    cost_per_1m_output = 0.0
                    if actual_model_ref:
                        lookup_result = self._model_registry.resolve_model(
                            actual_model_ref
                        )
                        model_def = lookup_result.model_definition
                        if model_def:
                            cost_per_1m_input = model_def.cost_per_1m_input_tokens
                            cost_per_1m_output = model_def.cost_per_1m_output_tokens

                        # Create usage record (we're already inside if actual_model_ref)
                        provider_str = lookup_result.provider.value
                        model_name_str = lookup_result.model_name

                        usage = TokenUsage.create(
                            provider=provider_str,
                            model_name=model_name_str,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cost_per_1m_input=cost_per_1m_input,
                            cost_per_1m_output=cost_per_1m_output,
                            latency_ms=latency_ms,
                            success=True,
                            workspace_id=actual_workspace_id,
                            user_id=actual_user_id,
                            metadata=metadata or {},
                        )

                        if self._config.track_individual_calls:
                            await self.record(usage)

                    return result

                except Exception as e:
                    latency_ms = (time.monotonic() - start_time) * 1000

                    # Record failure
                    if actual_model_ref and self._config.track_individual_calls:
                        lookup_result = self._model_registry.resolve_model(
                            actual_model_ref
                        )
                        model_def = lookup_result.model_definition

                        cost_per_1m_input = (
                            model_def.cost_per_1m_input_tokens if model_def else 0.0
                        )
                        cost_per_1m_output = (
                            model_def.cost_per_1m_output_tokens if model_def else 0.0
                        )

                        usage = TokenUsage.create(
                            provider=lookup_result.provider.value,
                            model_name=lookup_result.model_name,
                            input_tokens=0,
                            output_tokens=0,
                            cost_per_1m_input=cost_per_1m_input,
                            cost_per_1m_output=cost_per_1m_output,
                            latency_ms=latency_ms,
                            success=False,
                            error_message=str(e),
                            workspace_id=actual_workspace_id,
                            user_id=actual_user_id,
                            metadata=metadata or {},
                        )

                        await self.record(usage)

                    raise

            return wrapper

        return decorator

    async def get_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        provider: str | None = None,
        model_name: str | None = None,
        workspace_id: str | None = None,
    ):
        """
        Get usage summary for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            provider: Optional provider filter
            model_name: Optional model filter
            workspace_id: Optional workspace filter

        Returns:
            TokenUsageSummary with aggregated metrics
        """
        return await self._repository.get_summary(
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            model_name=model_name,
            workspace_id=workspace_id,
        )

    async def get_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        provider: str | None = None,
        model_name: str | None = None,
        workspace_id: str | None = None,
    ) -> TokenUsageStats:
        """
        Get detailed statistics for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            provider: Optional provider filter
            model_name: Optional model filter
            workspace_id: Optional workspace filter

        Returns:
            TokenUsageStats with detailed metrics
        """
        return await self._repository.get_stats(
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            model_name=model_name,
            workspace_id=workspace_id,
        )


# Type alias for backward compatibility
TokenAwareConfig = TokenTrackerConfig


def create_token_tracker(
    repository: ITokenUsageRepository,
    model_registry: ModelRegistry,
    config: TokenTrackerConfig | None = None,
) -> TokenTracker:
    """
    Factory function to create a configured TokenTracker.

    Args:
        repository: Repository for persisting usage records
        model_registry: Model registry for pricing information
        config: Optional tracker configuration

    Returns:
        Configured TokenTracker instance
    """
    return TokenTracker(
        repository=repository,
        model_registry=model_registry,
        config=config or TokenTrackerConfig(),
    )


__all__ = [
    "TokenTracker",
    "TrackingContext",
    "TokenTrackerConfig",
    "TokenAwareConfig",
    "create_token_tracker",
]
