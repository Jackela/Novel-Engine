"""Canonical in-memory runtime state for guest sessions and orchestration."""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.shared.infrastructure.config.settings import get_settings

_STEP_BLUEPRINT: tuple[tuple[str, str], ...] = (
    ("world-sync", "World sync"),
    ("briefing", "Character briefing"),
    ("simulation", "Turn simulation"),
    ("broadcast", "Signal fan-out"),
)

_DEFAULT_CHARACTERS: tuple[str, ...] = ("aria", "pilot", "scientist")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_workspace_id(workspace_id: str | None) -> str | None:
    if workspace_id is None:
        return None
    normalized = workspace_id.strip()
    return normalized or None


def _build_steps(
    status: str,
    current_turn: int,
    total_turns: int,
    active_characters: list[str],
) -> list[dict[str, Any]]:
    total_steps = len(_STEP_BLUEPRINT)
    running_index: int | None
    if status == "completed":
        running_index = total_steps - 1
        completed_steps = total_steps
    else:
        running_index = 0 if status == "running" else None
        if total_turns <= 0:
            completed_steps = 0
        else:
            completed_steps = min(
                total_steps,
                int((current_turn / total_turns) * total_steps),
            )

    if active_characters:
        completed_steps = min(completed_steps, total_steps)

    steps: list[dict[str, Any]] = []
    for index, (step_id, name) in enumerate(_STEP_BLUEPRINT):
        if status == "completed" or index < completed_steps:
            step_status = "completed"
            progress = 100
        elif running_index is not None and index == running_index and status == "running":
            progress = 100 if total_turns <= 0 else max(
                10, min(100, int((current_turn / total_turns) * 100))
            )
            step_status = "running"
        else:
            step_status = "pending"
            progress = 0

        steps.append(
            {
                "id": step_id,
                "name": name,
                "status": step_status,
                "progress": progress,
            }
        )

    return steps


@dataclass(slots=True)
class GuestSession:
    """Canonical guest workspace session."""

    workspace_id: str
    session_id: str
    is_new_session: bool
    created_at: str


class CanonicalRuntimeService:
    """Manage canonical guest sessions, orchestration, and realtime events."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._settings = get_settings()
        self._base_dir = base_dir or self._settings.base_dir
        self._sessions: dict[str, GuestSession] = {}
        self._orchestrations: dict[str, dict[str, Any]] = {}
        self._recent_events: dict[str, deque[dict[str, Any]]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._background_tasks: dict[str, asyncio.Task[None]] = {}
        self._active_workspace_id: str | None = None

    def reset(self) -> None:
        """Reset in-memory state for tests or application reconfiguration."""
        for task in self._background_tasks.values():
            task.cancel()

        self._background_tasks.clear()
        self._sessions.clear()
        self._orchestrations.clear()
        self._recent_events.clear()
        self._subscribers.clear()
        self._active_workspace_id = None

    async def shutdown(self) -> None:
        """Cancel any running orchestration jobs and clear transient state."""
        tasks = list(self._background_tasks.values())
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._background_tasks.clear()
        self._recent_events.clear()
        self._subscribers.clear()

    def list_available_characters(self) -> list[str]:
        """Return the source-backed character directory names."""
        characters_dir = self._base_dir / "characters"
        if not characters_dir.exists():
            return list(_DEFAULT_CHARACTERS)

        names = sorted(
            path.name
            for path in characters_dir.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        return names or list(_DEFAULT_CHARACTERS)

    async def create_or_resume_guest_session(
        self,
        workspace_id: str | None = None,
    ) -> GuestSession:
        """Create or resume a canonical guest workspace session."""
        normalized_workspace_id = _normalize_workspace_id(workspace_id)
        if normalized_workspace_id is None:
            normalized_workspace_id = f"guest-{uuid4().hex[:12]}"

        session = self._sessions.get(normalized_workspace_id)
        if session is None:
            session = GuestSession(
                workspace_id=normalized_workspace_id,
                session_id=f"session-{uuid4().hex[:12]}",
                is_new_session=True,
                created_at=_timestamp(),
            )
            self._sessions[normalized_workspace_id] = session
        else:
            session.is_new_session = False

        self._active_workspace_id = normalized_workspace_id
        self._ensure_orchestration_state(normalized_workspace_id)
        return session

    async def get_snapshot(self, workspace_id: str | None = None) -> dict[str, Any]:
        """Return the canonical orchestration snapshot for a workspace."""
        resolved_workspace_id = await self._resolve_workspace_id(
            workspace_id, create_if_missing=True
        )
        state = self._ensure_orchestration_state(resolved_workspace_id)
        return self._serialize_orchestration_state(state)

    async def get_dashboard_status(
        self,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the dashboard summary for a workspace."""
        resolved_workspace_id = await self._resolve_workspace_id(
            workspace_id, create_if_missing=True
        )
        state = self._ensure_orchestration_state(resolved_workspace_id)
        snapshot = self._serialize_orchestration_state(state)
        active_characters = snapshot["active_characters"]
        workspace_events = list(self._recent_events_for_workspace(resolved_workspace_id))
        recent_event_count = len(workspace_events)

        if snapshot["status"] == "running":
            headline = "Orchestration running"
            summary = "The canonical runtime is actively simulating turn execution."
            status = "healthy"
        elif snapshot["status"] == "paused":
            headline = "Orchestration paused"
            summary = "The runtime is paused and can resume without losing state."
            status = "degraded"
        elif snapshot["status"] == "completed":
            headline = "Run completed"
            summary = "The latest orchestration cycle has completed successfully."
            status = "healthy"
        else:
            headline = "Ready to start"
            summary = "Guest session is ready for orchestration."
            status = "degraded"

        return {
            "status": status,
            "mode": "remote",
            "workspaceId": resolved_workspace_id,
            "headline": headline,
            "summary": summary,
            "activeCharacters": len(active_characters),
            "activeSignals": recent_event_count,
            "recent_events": workspace_events,
            "runtime": snapshot,
        }

    async def start_orchestration(
        self,
        character_names: list[str],
        total_turns: int,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Start a canonical orchestration run."""
        session = await self.create_or_resume_guest_session(workspace_id)
        available_characters = self.list_available_characters()
        selected_characters = [name for name in character_names if name in available_characters]

        if character_names and not selected_characters:
            raise ValueError("No valid character names were provided")
        if not selected_characters:
            selected_characters = available_characters[:3]

        if not selected_characters:
            raise ValueError("No available characters were found")
        if total_turns <= 0:
            raise ValueError("total_turns must be greater than zero")

        existing_task = self._background_tasks.pop(session.workspace_id, None)
        if existing_task is not None:
            existing_task.cancel()

        state = self._ensure_orchestration_state(session.workspace_id)
        state.update(
            {
                "status": "running",
                "current_turn": 0,
                "total_turns": total_turns,
                "queue_length": len(selected_characters),
                "average_processing_time": 1.2,
                "active_characters": selected_characters,
                "available_characters": available_characters,
                "updated_at": _timestamp(),
                "started_at": _timestamp(),
                "paused_at": None,
                "steps": _build_steps(
                    "running", 0, total_turns, selected_characters
                ),
            }
        )

        await self._publish_event(
            self._build_event(
                workspace_id=session.workspace_id,
                event_type="orchestration",
                title="Orchestration started",
                description="Canonical runtime orchestration has started.",
                data=self._serialize_orchestration_state(state),
            )
        )

        task = asyncio.create_task(self._run_orchestration(session.workspace_id))
        self._background_tasks[session.workspace_id] = task

        def _drop_finished_task(
            _completed: asyncio.Task[None],
            workspace_id: str = session.workspace_id,
        ) -> None:
            self._background_tasks.pop(workspace_id, None)

        task.add_done_callback(_drop_finished_task)
        return self._serialize_orchestration_state(state)

    async def pause_orchestration(
        self,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Pause the active orchestration run."""
        resolved_workspace_id = await self._resolve_workspace_id(
            workspace_id, create_if_missing=False
        )
        state = self._ensure_orchestration_state(resolved_workspace_id)

        if state["status"] == "running":
            state["status"] = "paused"
            state["paused_at"] = _timestamp()
            state["updated_at"] = _timestamp()
            task = self._background_tasks.pop(resolved_workspace_id, None)
            if task is not None:
                task.cancel()
            await self._publish_event(
                self._build_event(
                    workspace_id=resolved_workspace_id,
                    event_type="system",
                    title="Orchestration paused",
                    description="Canonical runtime orchestration is paused.",
                    data=self._serialize_orchestration_state(state),
                )
            )

        return self._serialize_orchestration_state(state)

    async def stop_orchestration(
        self,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Stop the active orchestration run."""
        resolved_workspace_id = await self._resolve_workspace_id(
            workspace_id, create_if_missing=False
        )
        state = self._ensure_orchestration_state(resolved_workspace_id)

        task = self._background_tasks.pop(resolved_workspace_id, None)
        if task is not None:
            task.cancel()

        state.update(
            {
                "status": "idle",
                "current_turn": 0,
                "queue_length": 0,
                "average_processing_time": 0.0,
                "updated_at": _timestamp(),
                "paused_at": None,
                "steps": _build_steps(
                    "idle",
                    0,
                    state.get("total_turns", 0),
                    state.get("active_characters", []),
                ),
            }
        )

        await self._publish_event(
            self._build_event(
                workspace_id=resolved_workspace_id,
                event_type="system",
                title="Orchestration stopped",
                description="Canonical runtime orchestration was stopped.",
                data=self._serialize_orchestration_state(state),
            )
        )
        return self._serialize_orchestration_state(state)

    async def register_subscriber(
        self,
        workspace_id: str,
    ) -> asyncio.Queue[dict[str, Any]]:
        """Register an SSE subscriber for realtime dashboard events."""
        subscriber: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers_for_workspace(workspace_id).add(subscriber)
        return subscriber

    def unregister_subscriber(
        self,
        workspace_id: str,
        subscriber: asyncio.Queue[dict[str, Any]],
    ) -> None:
        """Remove a subscriber from the realtime fan-out set."""
        subscribers = self._subscribers.get(workspace_id)
        if subscribers is None:
            return
        subscribers.discard(subscriber)
        if not subscribers:
            self._subscribers.pop(workspace_id, None)

    async def _resolve_workspace_id(
        self,
        workspace_id: str | None,
        *,
        create_if_missing: bool,
    ) -> str:
        normalized = _normalize_workspace_id(workspace_id)
        if normalized is not None:
            return normalized

        if self._active_workspace_id is not None:
            return self._active_workspace_id

        if self._sessions:
            return next(reversed(self._sessions))

        if create_if_missing:
            session = await self.create_or_resume_guest_session(None)
            return session.workspace_id

        return f"guest-{uuid4().hex[:12]}"

    def _ensure_orchestration_state(self, workspace_id: str) -> dict[str, Any]:
        state = self._orchestrations.get(workspace_id)
        if state is None:
            state = {
                "workspace_id": workspace_id,
                "status": "idle",
                "current_turn": 0,
                "total_turns": 0,
                "queue_length": 0,
                "average_processing_time": 0.0,
                "active_characters": [],
                "available_characters": self.list_available_characters(),
                "steps": _build_steps("idle", 0, 0, []),
                "started_at": None,
                "paused_at": None,
                "updated_at": _timestamp(),
            }
            self._orchestrations[workspace_id] = state
        return state

    def _recent_events_for_workspace(
        self,
        workspace_id: str,
    ) -> deque[dict[str, Any]]:
        """Return the bounded recent-event buffer for a workspace."""
        recent_events = self._recent_events.get(workspace_id)
        if recent_events is None:
            recent_events = deque(maxlen=50)
            self._recent_events[workspace_id] = recent_events
        return recent_events

    def _subscribers_for_workspace(
        self,
        workspace_id: str,
    ) -> set[asyncio.Queue[dict[str, Any]]]:
        """Return the subscriber set for a workspace."""
        subscribers = self._subscribers.get(workspace_id)
        if subscribers is None:
            subscribers = set()
            self._subscribers[workspace_id] = subscribers
        return subscribers

    def _serialize_orchestration_state(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": state["status"],
            "current_turn": state["current_turn"],
            "total_turns": state["total_turns"],
            "queue_length": state["queue_length"],
            "average_processing_time": state["average_processing_time"],
            "steps": state["steps"],
            "workspace_id": state["workspace_id"],
            "active_characters": list(state["active_characters"]),
            "available_characters": list(state["available_characters"]),
            "updated_at": state["updated_at"],
        }

    async def _run_orchestration(self, workspace_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(1.2)
                state = self._orchestrations.get(workspace_id)
                if state is None:
                    return
                if state["status"] != "running":
                    return

                current_turn = int(state["current_turn"])
                total_turns = int(state["total_turns"])
                if current_turn >= total_turns:
                    state["status"] = "completed"
                    state["updated_at"] = _timestamp()
                    state["steps"] = _build_steps(
                        "completed",
                        current_turn,
                        total_turns,
                        list(state["active_characters"]),
                    )
                    await self._publish_event(
                        self._build_event(
                            workspace_id=workspace_id,
                            event_type="orchestration",
                            title="Orchestration completed",
                            description="Canonical runtime orchestration completed.",
                            data=self._serialize_orchestration_state(state),
                        )
                    )
                    return

                state["current_turn"] = current_turn + 1
                state["updated_at"] = _timestamp()
                state["steps"] = _build_steps(
                    "running",
                    state["current_turn"],
                    total_turns,
                    list(state["active_characters"]),
                )
                await self._publish_event(
                    self._build_event(
                        workspace_id=workspace_id,
                        event_type="orchestration",
                        title=f"Turn {state['current_turn']} completed",
                        description=(
                            "Canonical runtime processed one orchestration turn."
                        ),
                        data=self._serialize_orchestration_state(state),
                    )
                )

                if state["current_turn"] >= total_turns:
                    state["status"] = "completed"
                    state["updated_at"] = _timestamp()
                    state["steps"] = _build_steps(
                        "completed",
                        state["current_turn"],
                        total_turns,
                        list(state["active_characters"]),
                    )
                    await self._publish_event(
                        self._build_event(
                            workspace_id=workspace_id,
                            event_type="orchestration",
                            title="Orchestration completed",
                            description="Canonical runtime orchestration completed.",
                            data=self._serialize_orchestration_state(state),
                        )
                    )
                    return
        except asyncio.CancelledError:  # pragma: no cover - background shutdown path
            return

    def _build_event(
        self,
        *,
        workspace_id: str,
        event_type: str,
        title: str,
        description: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": f"event-{uuid4().hex[:12]}",
            "type": event_type,
            "title": title,
            "description": description,
            "timestamp": _timestamp(),
            "workspace_id": workspace_id,
            "data": data,
        }

    async def _publish_event(self, event: dict[str, Any]) -> None:
        workspace_id = str(event.get("workspace_id", "")).strip()
        if not workspace_id:
            return

        self._recent_events_for_workspace(workspace_id).append(event)
        for subscriber in tuple(self._subscribers.get(workspace_id, set())):
            try:
                subscriber.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - unbounded queue in practice
                continue


runtime_store = CanonicalRuntimeService()

__all__ = ["CanonicalRuntimeService", "GuestSession", "runtime_store"]
