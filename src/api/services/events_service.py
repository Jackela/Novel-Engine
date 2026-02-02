"""Events Service - Business logic for SSE events and analytics."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Dict, Optional

from src.api.schemas import (
    AnalyticsMetricsData,
    AnalyticsMetricsResponse,
    SSEEventData,
    SSEStatsResponse,
)

logger = logging.getLogger(__name__)


class EventsService:
    """Service layer for SSE events and analytics operations."""

    def __init__(self, app: Any):
        self.app = app
        self._ensure_state()

    def _ensure_state(self) -> None:
        """Initialize SSE state on app if not present."""
        if getattr(self.app.state, "sse_event_queues", None) is None:
            self.app.state.sse_event_queues = {}
        if getattr(self.app.state, "sse_event_id_counter", None) is None:
            self.app.state.sse_event_id_counter = 0
        if getattr(self.app.state, "active_sse_connections", None) is None:
            self.app.state.active_sse_connections = 0

    def create_event(
        self,
        event_type: str,
        title: str,
        description: str,
        severity: str = "low",
        character_name: Optional[str] = None,
    ) -> SSEEventData:
        """Create a new SSE event."""
        self._ensure_state()
        self.app.state.sse_event_id_counter += 1
        event_id = self.app.state.sse_event_id_counter

        return SSEEventData(
            id=f"evt-{event_id}",
            type=event_type,
            title=title,
            description=description,
            timestamp=int(time.time() * 1000),
            severity=severity,
            characterName=character_name,
        )

    def broadcast_event(self, event_data: SSEEventData) -> None:
        """Broadcast event to all connected clients."""
        self._ensure_state()
        queues: dict[str, asyncio.Queue] = self.app.state.sse_event_queues
        logger.info("Broadcasting SSE event to %d clients", len(queues))

        loop = getattr(self.app.state, "main_loop", None)
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("No event loop available for SSE broadcast")
                return

        event_dict = event_data.model_dump()
        for client_id, queue in list(queues.items()):
            self._safe_put(queue, event_dict, client_id, loop)

    def _safe_put(
        self,
        queue: asyncio.Queue,
        data: Dict[str, Any],
        client_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Safely put data into queue."""

        def _put_nowait():
            try:
                queue.put_nowait(data)
            except asyncio.QueueFull:
                logger.warning("SSE queue full for client %s", client_id)

        if loop and hasattr(loop, "is_running") and loop.is_running():
            loop.call_soon_threadsafe(_put_nowait)
        else:
            _put_nowait()

    def get_stats(self) -> SSEStatsResponse:
        """Get SSE connection statistics."""
        self._ensure_state()
        return SSEStatsResponse(
            connected_clients=self.app.state.active_sse_connections,
            total_events_sent=self.app.state.sse_event_id_counter,
            active_queues=len(self.app.state.sse_event_queues),
        )

    async def get_analytics_metrics(
        self, api_service: Any = None
    ) -> AnalyticsMetricsResponse:
        """Calculate and return analytics metrics."""
        orch_data = await self._get_orchestration_data(api_service)
        cache_metrics = self._get_cache_metrics()

        metrics_data = self._calculate_metrics(orch_data, cache_metrics)
        return AnalyticsMetricsResponse(success=True, data=metrics_data)

    async def _get_orchestration_data(self, api_service: Any) -> Dict[str, Any]:
        """Get orchestration status data."""
        if not api_service:
            return {}
        try:
            return await api_service.get_status()
        except Exception:
            return {}

    def _get_cache_metrics(self) -> Dict[str, Any]:
        """Get cache metrics from chunk cache."""
        try:
            from src.caching.global_chunk_cache import chunk_cache

            if chunk_cache:
                if hasattr(chunk_cache, "get_metrics"):
                    return chunk_cache.get_metrics()
                elif hasattr(chunk_cache, "_cache"):
                    return {
                        "cache_size": (
                            len(chunk_cache._cache)
                            if hasattr(chunk_cache._cache, "__len__")
                            else 0
                        ),
                        "cache_semantic_hits": 0,
                        "cache_exact_hits": 0,
                    }
        except Exception:  # noqa: BLE001 - silently return empty dict on any error
            return {}
        return {}

    def _calculate_metrics(
        self, orch_data: Dict[str, Any], cache_metrics: Dict[str, Any]
    ) -> AnalyticsMetricsData:
        """Calculate metrics from orchestration and cache data."""
        self._ensure_state()

        total_turns = orch_data.get("total_turns", 0)
        current_turn = orch_data.get("current_turn", 0)
        status = orch_data.get("status", "idle")
        steps = orch_data.get("steps", [])

        completed_steps = sum(1 for s in steps if s.get("status") == "completed")
        total_steps = len(steps)
        story_quality = (completed_steps / total_steps * 10) if total_steps > 0 else 8.0

        active_clients = self.app.state.active_sse_connections
        total_events = self.app.state.sse_event_id_counter
        engagement = min(100, 70 + active_clients * 10 + min(total_events, 30))

        cache_hits = cache_metrics.get("cache_semantic_hits", 0) + cache_metrics.get(
            "cache_exact_hits", 0
        )
        cache_size = cache_metrics.get("cache_size", 0)
        coherence = (
            min(100, 85 + (cache_hits / max(1, cache_size)) * 15)
            if cache_size > 0
            else 90
        )

        complexity = min(10, 6 + (total_steps * 0.3) + (current_turn * 0.1))
        data_points = cache_size + total_events + total_turns

        return AnalyticsMetricsData(
            story_quality=round(story_quality, 1),
            engagement=round(engagement, 0),
            coherence=round(coherence, 0),
            complexity=round(complexity, 1),
            data_points=data_points,
            metrics_tracked=5,
            status=status,
            last_updated=datetime.now(UTC).isoformat(),
        )

    async def generate_events(
        self,
        client_id: str,
        limit: Optional[int] = None,
        interval_seconds: float = 2.0,
    ) -> AsyncGenerator[str, None]:
        """Generate SSE event stream."""
        self._ensure_state()

        queues = self.app.state.sse_event_queues
        client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        queues[client_id] = client_queue
        events_sent = 0
        simulated_index = 0

        try:
            yield "retry: 3000\n\n"

            logger.info("SSE client connected: %s", client_id)
            self.app.state.active_sse_connections += 1

            # Send connect event
            connect_event = self.create_event(
                event_type="system",
                title="Connected",
                description="Real-time event stream connected",
                severity="low",
            )
            for chunk in self._format_event(connect_event):
                yield chunk
            events_sent += 1
            last_emit_time = time.monotonic()

            if limit is not None and events_sent >= limit:
                return

            while True:
                try:
                    event_data = await self._wait_or_generate_event(
                        client_queue,
                        simulated_index,
                        interval_seconds,
                        last_emit_time,
                    )
                    if event_data is None:
                        simulated_index += 1
                        event_data = self._create_simulated_event(simulated_index)

                    for chunk in self._format_event_dict(event_data):
                        yield chunk
                    events_sent += 1
                    last_emit_time = time.monotonic()

                    if limit is not None and events_sent >= limit:
                        break

                except asyncio.CancelledError:
                    logger.info("SSE client disconnected: %s", client_id)
                    break
                except Exception:
                    logger.exception("SSE event generation error.")
                    error_event = self.create_event(
                        event_type="system",
                        title="Stream Error",
                        description="Internal error while streaming events.",
                        severity="high",
                    )
                    for chunk in self._format_event(error_event):
                        yield chunk
                    events_sent += 1
                    if limit is not None and events_sent >= limit:
                        break
        finally:
            self.app.state.active_sse_connections = max(
                0, self.app.state.active_sse_connections - 1
            )
            queues.pop(client_id, None)
            logger.info("SSE client %s cleaned up", client_id)

    async def _wait_or_generate_event(
        self,
        queue: asyncio.Queue,
        simulated_index: int,
        interval: float,
        last_emit_time: float,
    ) -> Optional[Dict[str, Any]]:
        """Wait for queue event or return None to generate simulated event."""
        try:
            return await asyncio.wait_for(queue.get(), timeout=interval)
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - last_emit_time
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
            return None

    def _create_simulated_event(self, index: int) -> Dict[str, Any]:
        """Create a simulated event for demo purposes."""
        event_types = ["character", "story", "system", "interaction"]
        severities = ["low", "medium", "high"]
        event_type = event_types[index % len(event_types)]
        severity = severities[index % len(severities)]
        character_name = f"Character-{index}" if event_type == "character" else None

        event = self.create_event(
            event_type=event_type,
            title=f"Event {index}",
            description=f"Simulated dashboard event #{index}",
            severity=severity,
            character_name=character_name,
        )
        return event.model_dump()

    def _format_event(self, event: SSEEventData) -> list[str]:
        """Format SSEEventData for SSE stream."""
        return [f"id: {event.id}\n", f"data: {event.model_dump_json()}\n\n"]

    def _format_event_dict(self, event_data: Dict[str, Any]) -> list[str]:
        """Format dict event for SSE stream."""
        return [f"id: {event_data['id']}\n", f"data: {json.dumps(event_data)}\n\n"]
