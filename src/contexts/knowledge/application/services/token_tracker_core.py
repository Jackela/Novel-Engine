"""
Token Tracker Core

Core token tracking functionality.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, TypeVar

import structlog

from ...domain.models.model_registry import LLMProvider
from ...domain.models.token_usage import TokenUsage, TokenUsageStats
from ..ports.i_token_usage_repository import (
    ITokenUsageRepository,
    TokenUsageSummary,
)
from .model_registry import ModelLookupResult, ModelRegistry
from .token_counter import TokenCounter
from .token_tracker_config import TokenTrackerConfig
from .tracking_context import TrackingContext

logger = structlog.get_logger()
T = TypeVar("T")


class TokenTrackerCore:
    """
    Core service for tracking LLM token usage and costs.

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
            loop = asyncio.get_running_loop()
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
    ) -> Any:
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
        resolve_result = self._model_registry.resolve_model(model_ref)
        lookup_result: ModelLookupResult
        if resolve_result.is_error:
            # Use defaults if resolution fails
            lookup_result = ModelLookupResult(
                provider=LLMProvider.OPENAI,
                model_name=model_ref,
                model_definition=None,
            )
        else:
            maybe_lookup = resolve_result.unwrap()
            if maybe_lookup is None:
                lookup_result = ModelLookupResult(
                    provider=LLMProvider.OPENAI,
                    model_name=model_ref,
                    model_definition=None,
                )
            else:
                lookup_result = maybe_lookup

        model_def = lookup_result.model_definition

        # Pre-count input tokens if prompt provided
        input_tokens: int | None = None
        if prompt and self._config.count_input_tokens:
            count_result = self._token_counter.count(
                prompt,
                model=model_def.model_name if model_def else model_ref,
            )
            if count_result.is_ok:
                count_res = count_result.unwrap()
                if count_res is not None:
                    input_tokens = count_res.token_count

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
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
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
        from .token_tracker_decorator import create_llm_tracker_decorator

        return create_llm_tracker_decorator(
            tracker=self,
            model_ref=model_ref,
            workspace_id=workspace_id,
            user_id=user_id,
            metadata=metadata,
        )

    async def get_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        provider: str | None = None,
        model_name: str | None = None,
        workspace_id: str | None = None,
    ) -> TokenUsageSummary:
        """
        Get usage summary for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            provider: Optional provider filter
            model_name: Optional model filter
            workspace_id: Optional workspace filter

        Returns:
            TokenUsageStats with aggregated metrics
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
