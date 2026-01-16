from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.caching.global_chunk_cache import chunk_cache

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])


def _ensure_state(app) -> None:
    if getattr(app.state, "sse_event_queues", None) is None:
        app.state.sse_event_queues = {}
    if getattr(app.state, "sse_event_id_counter", None) is None:
        app.state.sse_event_id_counter = 0
    if getattr(app.state, "active_sse_connections", None) is None:
        app.state.active_sse_connections = 0


def create_sse_event(
    app,
    *,
    event_type: str,
    title: str,
    description: str,
    severity: str = "low",
    character_name: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_state(app)
    app.state.sse_event_id_counter += 1
    event_id = app.state.sse_event_id_counter
    event_data: Dict[str, Any] = {
        "id": f"evt-{event_id}",
        "type": event_type,
        "title": title,
        "description": description,
        "timestamp": int(time.time() * 1000),
        "severity": severity,
    }
    if character_name:
        event_data["characterName"] = character_name
    return event_data


def _safe_sse_put(queue: asyncio.Queue, data: Dict[str, Any], client_id: str) -> None:
    try:
        queue.put_nowait(data)
    except asyncio.QueueFull:
        logger.warning("SSE queue full for client %s, dropping event", client_id)


def broadcast_sse_event(app, event_data: Dict[str, Any]) -> None:
    _ensure_state(app)
    queues: dict[str, asyncio.Queue] = app.state.sse_event_queues
    logger.info("Broadcasting SSE event to %d clients", len(queues))

    loop = getattr(app.state, "main_loop", None)
    if loop is None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("No event loop available for SSE broadcast")
            return

    for client_id, queue in list(queues.items()):
        if hasattr(loop, "is_running") and loop.is_running():
            loop.call_soon_threadsafe(_safe_sse_put, queue, event_data, client_id)
        else:
            _safe_sse_put(queue, event_data, client_id)


def _resolve_event_interval(interval_seconds: Optional[float]) -> float:
    default_interval = 2.0
    if interval_seconds is None:
        return default_interval
    try:
        interval_value = float(interval_seconds)
    except (TypeError, ValueError):
        return default_interval
    return max(0.01, min(interval_value, 10.0))


async def event_generator(
    app,
    client_id: str,
    limit: Optional[int] = None,
    interval_seconds: Optional[float] = None,
):
    _ensure_state(app)

    queues: dict[str, asyncio.Queue] = app.state.sse_event_queues
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    queues[client_id] = client_queue
    events_sent = 0
    simulated_index = 0
    event_interval_seconds = _resolve_event_interval(interval_seconds)

    try:
        yield "retry: 3000\n\n"

        logger.info("SSE client connected: %s", client_id)
        app.state.active_sse_connections += 1

        connect_event = create_sse_event(
            app,
            event_type="system",
            title="Connected",
            description="Real-time event stream connected",
            severity="low",
        )
        yield f"id: {connect_event['id']}\n"
        yield f"data: {json.dumps(connect_event)}\n\n"
        events_sent += 1
        last_emit_time = time.monotonic()
        if limit is not None and events_sent >= limit:
            return

        while True:
            try:
                try:
                    event_data = await asyncio.wait_for(
                        client_queue.get(), timeout=event_interval_seconds
                    )
                except asyncio.TimeoutError:
                    elapsed = time.monotonic() - last_emit_time
                    if elapsed < event_interval_seconds:
                        await asyncio.sleep(event_interval_seconds - elapsed)
                    simulated_index += 1
                    event_types = ["character", "story", "system", "interaction"]
                    severities = ["low", "medium", "high"]
                    event_type = event_types[simulated_index % len(event_types)]
                    severity = severities[simulated_index % len(severities)]
                    character_name = (
                        f"Character-{simulated_index}"
                        if event_type == "character"
                        else None
                    )
                    event_data = create_sse_event(
                        app,
                        event_type=event_type,
                        title=f"Event {simulated_index}",
                        description=(
                            f"Simulated dashboard event #{simulated_index}"
                        ),
                        severity=severity,
                        character_name=character_name,
                    )

                yield f"id: {event_data['id']}\n"
                yield f"data: {json.dumps(event_data)}\n\n"
                events_sent += 1
                last_emit_time = time.monotonic()
                if limit is not None and events_sent >= limit:
                    break

            except asyncio.CancelledError:
                logger.info("SSE client disconnected: %s", client_id)
                break

            except Exception:
                logger.exception("SSE event generation error.")
                error_event = create_sse_event(
                    app,
                    event_type="system",
                    title="Stream Error",
                    description="Internal error while streaming events.",
                    severity="high",
                )
                yield f"id: {error_event['id']}\n"
                yield f"data: {json.dumps(error_event)}\n\n"
                events_sent += 1
                if limit is not None and events_sent >= limit:
                    break
    finally:
        app.state.active_sse_connections = max(0, app.state.active_sse_connections - 1)
        queues.pop(client_id, None)
        logger.info("SSE client %s cleaned up", client_id)


@router.get("/events/stream")
async def stream_events(
    request: Request,
    limit: Optional[int] = None,
    interval: Optional[float] = None,
):
    client_id = secrets.token_hex(8)

    return StreamingResponse(
        event_generator(
            request.app,
            client_id,
            limit=limit,
            interval_seconds=interval,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class EmitEventRequest(BaseModel):
    type: str = Field(
        default="system",
        description="Event type: character, story, system, interaction",
    )

    title: str = Field(description="Event title")

    description: str = Field(description="Event description")

    severity: str = Field(
        default="low", description="Event severity: low, medium, high"
    )

    character_name: Optional[str] = Field(
        default=None, description="Character name for character events"
    )


@router.post("/events/emit")
async def emit_dashboard_event(request: Request, payload: EmitEventRequest):
    event_data = create_sse_event(
        request.app,
        event_type=payload.type,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        character_name=payload.character_name,
    )

    broadcast_sse_event(request.app, event_data)

    _ensure_state(request.app)

    return {
        "success": True,
        "message": "Event broadcast to all connected clients",
        "event_id": event_data["id"],
        "connected_clients": request.app.state.active_sse_connections,
    }


@router.get("/events/stats")
async def get_sse_stats(request: Request):
    _ensure_state(request.app)

    return {
        "connected_clients": request.app.state.active_sse_connections,
        "total_events_sent": request.app.state.sse_event_id_counter,
        "active_queues": len(request.app.state.sse_event_queues),
    }


@router.get("/analytics/metrics")
async def get_analytics_metrics(request: Request):
    api_service = getattr(request.app.state, "api_service", None)
    orch_data: Dict[str, Any] = {}
    if api_service:
        try:
            orch_data = await api_service.get_status()
        except Exception:
            orch_data = {}

    cache_metrics_raw: Dict[str, Any] = {}
    try:
        if chunk_cache:
            if hasattr(chunk_cache, "get_metrics"):
                cache_metrics_raw = chunk_cache.get_metrics()
            elif hasattr(chunk_cache, "_cache"):
                cache_metrics_raw = {
                    "cache_size": (
                        len(chunk_cache._cache)
                        if hasattr(chunk_cache._cache, "__len__")
                        else 0
                    ),
                    "cache_semantic_hits": 0,
                    "cache_exact_hits": 0,
                }
    except Exception:
        cache_metrics_raw = {}

    total_turns = orch_data.get("total_turns", 0)
    current_turn = orch_data.get("current_turn", 0)
    status = orch_data.get("status", "idle")

    completed_steps = sum(
        1 for step in orch_data.get("steps", []) if step.get("status") == "completed"
    )
    total_steps = len(orch_data.get("steps", []))
    story_quality = (completed_steps / total_steps * 10) if total_steps > 0 else 8.0

    _ensure_state(request.app)
    active_clients = request.app.state.active_sse_connections
    total_events = request.app.state.sse_event_id_counter
    engagement = min(100, 70 + active_clients * 10 + min(total_events, 30))

    cache_hits = cache_metrics_raw.get(
        "cache_semantic_hits", 0
    ) + cache_metrics_raw.get("cache_exact_hits", 0)
    cache_size = cache_metrics_raw.get("cache_size", 0)
    coherence = (
        min(100, 85 + (cache_hits / max(1, cache_size)) * 15) if cache_size > 0 else 90
    )

    complexity = min(10, 6 + (total_steps * 0.3) + (current_turn * 0.1))
    data_points = cache_size + total_events + total_turns

    return {
        "success": True,
        "data": {
            "story_quality": round(story_quality, 1),
            "engagement": round(engagement, 0),
            "coherence": round(coherence, 0),
            "complexity": round(complexity, 1),
            "data_points": data_points,
            "metrics_tracked": 5,
            "status": status,
            "last_updated": datetime.now(UTC).isoformat(),
        },
    }
