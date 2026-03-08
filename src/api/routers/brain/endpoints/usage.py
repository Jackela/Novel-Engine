"""
Token Usage Analytics Endpoints

BRAIN-035A: Token usage analytics endpoints
BRAIN-035B: Real-time streaming, CSV export, model pricing
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import structlog
from datetime import UTC, datetime, timedelta
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.routers.brain.dependencies import (
    get_token_usage_repository,
    get_usage_broadcaster_dep,
)
from src.api.routers.brain.repositories.token_usage import InMemoryTokenUsageRepository
from src.api.routers.brain.services.usage_broadcaster import RealtimeUsageBroadcaster

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["brain-settings"])


class ModelPricingResponse(BaseModel):
    """
    Model pricing information response.

    Attributes:
        provider: LLM provider name
        model_name: Model identifier
        display_name: Human-readable model name
        cost_per_1m_input_tokens: Cost per 1M input tokens in USD
        cost_per_1m_output_tokens: Cost per 1M output tokens in USD
        max_context_tokens: Maximum input context window
        max_output_tokens: Maximum output tokens
        deprecated: Whether model is deprecated
    """

    provider: str
    model_name: str
    display_name: str
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float
    max_context_tokens: int
    max_output_tokens: int
    deprecated: bool = False


@router.get("/usage/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> dict:
    """
    Get token usage summary for the specified time period.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        Aggregated usage summary including tokens, costs, and request counts
    """
    try:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        summary = await repository.get_summary(start_time, end_time)
        return summary

    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/usage/daily")
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365, description="Number of days to return"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> list[dict]:
    """
    Get daily usage statistics over time.

    Args:
        days: Number of days to return (default: 30)

    Returns:
        List of daily stats with tokens, costs, and request counts
    """
    try:
        daily_stats = await repository.get_daily_stats(days)
        return daily_stats

    except Exception as e:
        logger.error(f"Failed to get daily usage: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/usage/by-model")
async def get_usage_by_model(
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> list[dict]:
    """
    Get usage breakdown by model.

    Returns:
        List of models with total tokens, costs, and request counts
    """
    try:
        model_breakdown = await repository.get_model_breakdown()
        return model_breakdown

    except Exception as e:
        logger.error(f"Failed to get usage by model: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/usage/export")
async def export_usage_csv(
    days: int = Query(30, ge=1, le=365, description="Number of days to export"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> Response:
    """
    Export usage data as CSV file.

    BRAIN-035B-03: CSV Export for usage analytics

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        CSV file with usage data including timestamp, model, tokens, and cost
    """
    try:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Get usage data
        usages = await repository.get_usages(start_time, end_time)

        # Build CSV content
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Timestamp",
                "Provider",
                "Model",
                "Input Tokens",
                "Output Tokens",
                "Total Tokens",
                "Input Cost",
                "Output Cost",
                "Total Cost",
                "Latency (ms)",
                "Success",
            ]
        )

        # Write data rows
        for usage in usages:
            writer.writerow(
                [
                    usage["timestamp"],
                    usage["provider"],
                    usage["model_name"],
                    usage["input_tokens"],
                    usage["output_tokens"],
                    usage["total_tokens"],
                    usage.get("input_cost", "0"),
                    usage.get("output_cost", "0"),
                    usage.get("total_cost", "0"),
                    usage.get("latency_ms", 0),
                    usage.get("success", True),
                ]
            )

        # Create response with CSV file
        csv_content = output.getvalue()
        filename = f"usage_export_{end_time.strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        logger.error(f"Failed to export usage CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/usage/stream")
async def stream_realtime_usage(
    broadcaster: RealtimeUsageBroadcaster = Depends(get_usage_broadcaster_dep),
) -> StreamingResponse:
    """
    Stream real-time token usage events via SSE.

    BRAIN-035B-04: Real-time Usage Counter

    Returns Server-Sent Events stream with:
        - session_start: New generation session started
        - token_update: Live token count updates
        - session_complete: Generation finished
        - session_state: Current state of active sessions

    Example:
        ```javascript
        const eventSource = new EventSource('/api/brain/usage/stream');
        eventSource.onmessage = (e) => {
            const event = JSON.parse(e.data);
            console.log(event.type, event);
        };
        ```
    """

    async def _sse_generator() -> AsyncIterator[str]:
        """Generate SSE events for real-time usage."""
        try:
            async for event in broadcaster.subscribe():
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            logger.debug("SSE stream cancelled")
        except Exception:
            logger.exception("SSE stream error")
            yield (
                "data: "
                + json.dumps({"type": "error", "message": "Internal server error"})
                + "\n\n"
            )

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/models", response_model=list[ModelPricingResponse])
async def get_model_pricing(
    include_deprecated: bool = Query(False, description="Include deprecated models"),
    provider: str | None = Query(None, description="Filter by provider"),
) -> list[ModelPricingResponse]:
    """
    Get model pricing information from the ModelRegistry.

    Returns:
        List of models with pricing data grouped by provider

    Raises:
        500: If retrieval fails
    """
    try:
        from src.contexts.knowledge.application.services.model_registry import (
            DEFAULT_MODELS,
            LLMProvider,
        )

        models: list[ModelPricingResponse] = []

        # Provider filter
        provider_filter = None
        if provider:
            try:
                provider_filter = LLMProvider(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {provider}. Must be one of: {[p.value for p in LLMProvider]}",
                )

        for llm_provider, model_list in DEFAULT_MODELS.items():
            if provider_filter and llm_provider != provider_filter:
                continue

            for model_def in model_list:
                if not include_deprecated and model_def.deprecated:
                    continue

                models.append(
                    ModelPricingResponse(
                        provider=model_def.provider.value,
                        model_name=model_def.model_name,
                        display_name=model_def.display_name,
                        cost_per_1m_input_tokens=model_def.cost_per_1m_input_tokens,
                        cost_per_1m_output_tokens=model_def.cost_per_1m_output_tokens,
                        max_context_tokens=model_def.max_context_tokens,
                        max_output_tokens=model_def.max_output_tokens,
                        deprecated=model_def.deprecated,
                    )
                )

        # Sort by provider, then by cost (descending for comparison)
        models.sort(key=lambda m: (m.provider, -m.cost_per_1m_output_tokens))

        return models

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
