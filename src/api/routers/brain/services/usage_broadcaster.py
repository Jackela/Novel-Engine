"""
Usage Broadcaster Service

Real-time token usage streaming via SSE.
BRAIN-035B-04: Real-time Usage Counter
"""

from __future__ import annotations

import asyncio
import json
import structlog
from datetime import UTC, datetime
from typing import AsyncIterator

logger = structlog.get_logger(__name__)


class RealtimeUsageBroadcaster:
    """
    Broadcasts real-time token usage events to connected clients.

    Why:
        - Enables live token counting during LLM generation
        - Supports multiple concurrent clients via fan-out pattern
        - Session-based tracking isolates users' active generations

    Attributes:
        _active_sessions: Dict of session_id -> current usage tracking
        _subscribers: Dict of queue -> set of session_ids to watch
        _lock: Async lock for thread-safe operations
    """

    def __init__(self) -> None:
        self._active_sessions: dict[str, dict] = {}
        self._subscribers: dict[asyncio.Queue, set[str]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start_session(
        self,
        session_id: str,
        provider: str,
        model_name: str,
    ) -> None:
        """Start tracking a new generation session."""
        async with self._lock:
            self._active_sessions[session_id] = {
                "provider": provider,
                "model_name": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "start_time": datetime.now(UTC).isoformat(),
                "is_complete": False,
            }
            # Broadcast session start
            await self._broadcast_to_all(
                {
                    "type": "session_start",
                    "session_id": session_id,
                    "provider": provider,
                    "model_name": model_name,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

    async def update_session(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Update a session with new token usage."""
        async with self._lock:
            if session_id not in self._active_sessions:
                return

            session = self._active_sessions[session_id]
            session["input_tokens"] = input_tokens
            session["output_tokens"] = output_tokens
            session["total_tokens"] = input_tokens + output_tokens
            session["cost"] = cost

            # Broadcast update
            await self._broadcast_to_all(
                {
                    "type": "token_update",
                    "session_id": session_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost": cost,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

    async def complete_session(self, session_id: str) -> None:
        """Mark a session as complete."""
        async with self._lock:
            if session_id not in self._active_sessions:
                return

            self._active_sessions[session_id]["is_complete"] = True
            session = self._active_sessions[session_id]

            # Broadcast completion
            await self._broadcast_to_all(
                {
                    "type": "session_complete",
                    "session_id": session_id,
                    **session,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

            # Remove session after a delay
            asyncio.create_task(self._cleanup_session(session_id))

    async def _cleanup_session(self, session_id: str) -> None:
        """Remove a session after a delay."""
        await asyncio.sleep(60)  # Keep for 1 minute after completion
        async with self._lock:
            self._active_sessions.pop(session_id, None)

    async def _broadcast_to_all(self, event: dict) -> None:
        """Broadcast an event to all subscribers."""
        for queue in list(self._subscribers.keys()):
            try:
                await queue.put(event)
            except Exception:
                # Remove dead queue
                self._subscribers.pop(queue, None)

    async def subscribe(self) -> AsyncIterator[dict]:
        """Subscribe to real-time usage events."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[queue] = set()

            # Send current state
            for session_id, session in self._active_sessions.items():
                await queue.put(
                    {
                        "type": "session_state",
                        "session_id": session_id,
                        **session,
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.pop(queue, None)


# Global broadcaster instance
_usage_broadcaster = RealtimeUsageBroadcaster()


def get_usage_broadcaster() -> RealtimeUsageBroadcaster:
    """Get the global usage broadcaster instance."""
    return _usage_broadcaster


__all__ = ["RealtimeUsageBroadcaster", "get_usage_broadcaster"]
