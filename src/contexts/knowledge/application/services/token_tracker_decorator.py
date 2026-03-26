"""
Token Tracker Decorator

Decorator functionality for automatic token tracking.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

import structlog

from ...domain.models.token_usage import TokenUsage

if TYPE_CHECKING:
    from .token_tracker_config import TokenTrackerConfig
    from .token_tracker_core import TokenTrackerCore

logger = structlog.get_logger()
T = TypeVar("T")


def create_llm_tracker_decorator(
    tracker: "TokenTrackerCore",
    model_ref: str | None,
    workspace_id: str | None,
    user_id: str | None,
    metadata: dict[str, Any] | None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Create a decorator for automatic tracking of LLM calls.

    Args:
        tracker: The TokenTrackerCore instance.
        model_ref: Model reference (if None, inferred from function args).
        workspace_id: Optional workspace identifier.
        user_id: Optional user identifier.
        metadata: Additional metadata.

    Returns:
        Decorator function.
    """
    config: "TokenTrackerConfig" = tracker._config

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if not config.enabled:
                return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

            start_time = time.monotonic()

            # Try to extract model_ref from arguments
            actual_model_ref = model_ref
            if actual_model_ref is None:
                req = kwargs.get("request")
                if req is None and args:
                    req = args[0]
                if req is not None and hasattr(req, "model"):
                    actual_model_ref = req.model

            # Try to extract workspace_id and user_id
            actual_workspace_id = workspace_id or kwargs.get("workspace_id")
            actual_user_id = user_id or kwargs.get("user_id")

            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                latency_ms = (time.monotonic() - start_time) * 1000

                # Extract token usage from result
                input_tokens, output_tokens = _extract_token_usage(result)

                # Get model pricing and record usage
                if actual_model_ref:
                    await _record_successful_usage(
                        tracker=tracker,
                        model_ref=actual_model_ref,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                        workspace_id=actual_workspace_id,
                        user_id=actual_user_id,
                        metadata=metadata,
                    )

                return result  # type: ignore[no-any-return]

            except Exception as e:
                latency_ms = (time.monotonic() - start_time) * 1000

                # Record failure
                if actual_model_ref and config.track_individual_calls:
                    await _record_failed_usage(
                        tracker=tracker,
                        model_ref=actual_model_ref,
                        latency_ms=latency_ms,
                        error=e,
                        workspace_id=actual_workspace_id,
                        user_id=actual_user_id,
                        metadata=metadata,
                    )

                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def _extract_token_usage(result: Any) -> tuple[int, int]:
    """Extract token usage from result object."""
    input_tokens = 0
    output_tokens = 0

    if hasattr(result, "tokens_used") and result.tokens_used:
        input_tokens = getattr(result, "input_tokens", 0) or result.tokens_used // 2
        output_tokens = (
            getattr(result, "output_tokens", 0) or result.tokens_used - input_tokens
        )
    elif hasattr(result, "usage"):
        usage_attr = result.usage
        if isinstance(usage_attr, dict):
            input_tokens = usage_attr.get("prompt_tokens", 0) or usage_attr.get(
                "input_tokens", 0
            )
            output_tokens = usage_attr.get("completion_tokens", 0) or usage_attr.get(
                "output_tokens", 0
            )

    return input_tokens, output_tokens


async def _record_successful_usage(
    tracker: "TokenTrackerCore",
    model_ref: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    workspace_id: str | None,
    user_id: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    """Record successful LLM usage."""
    resolve_result = tracker._model_registry.resolve_model(model_ref)
    cost_per_1m_input = 0.0
    cost_per_1m_output = 0.0
    provider_str = "unknown"
    model_name_str = model_ref

    if resolve_result.is_ok:
        lookup_result = resolve_result.unwrap()
        if lookup_result is not None:
            model_def = lookup_result.model_definition
            if model_def:
                cost_per_1m_input = model_def.cost_per_1m_input_tokens
                cost_per_1m_output = model_def.cost_per_1m_output_tokens

            provider_str = (
                str(lookup_result.provider.value)
                if hasattr(lookup_result.provider, "value")
                else str(lookup_result.provider)
            )
            model_name_str = lookup_result.model_name

    usage_record = TokenUsage.create(
        provider=provider_str,
        model_name=model_name_str,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_per_1m_input=cost_per_1m_input,
        cost_per_1m_output=cost_per_1m_output,
        latency_ms=latency_ms,
        success=True,
        workspace_id=workspace_id,
        user_id=user_id,
        metadata=metadata or {},
    )

    if tracker._config.track_individual_calls:
        await tracker.record(usage_record)


async def _record_failed_usage(
    tracker: "TokenTrackerCore",
    model_ref: str,
    latency_ms: float,
    error: Exception,
    workspace_id: str | None,
    user_id: str | None,
    metadata: dict[str, Any] | None,
) -> None:
    """Record failed LLM usage."""
    resolve_result = tracker._model_registry.resolve_model(model_ref)
    cost_per_1m_input = 0.0
    cost_per_1m_output = 0.0
    provider_str = "unknown"
    model_name_str = model_ref

    if resolve_result.is_ok:
        lookup_result = resolve_result.unwrap()
        if lookup_result is not None:
            model_def = lookup_result.model_definition
            cost_per_1m_input = model_def.cost_per_1m_input_tokens if model_def else 0.0
            cost_per_1m_output = (
                model_def.cost_per_1m_output_tokens if model_def else 0.0
            )
            provider_str = (
                str(lookup_result.provider.value)
                if hasattr(lookup_result.provider, "value")
                else str(lookup_result.provider)
            )
            model_name_str = lookup_result.model_name

    usage_record = TokenUsage.create(
        provider=provider_str,
        model_name=model_name_str,
        input_tokens=0,
        output_tokens=0,
        cost_per_1m_input=cost_per_1m_input,
        cost_per_1m_output=cost_per_1m_output,
        latency_ms=latency_ms,
        success=False,
        error_message=str(error),
        workspace_id=workspace_id,
        user_id=user_id,
        metadata=metadata or {},
    )

    await tracker.record(usage_record)
