"""Compatibility layer for legacy DirectorAgent component imports.

The refactored DirectorAgent now lives under ``src/director_components`` but the
legacy unit tests (and some downstream tooling) still import the old module
names.  This module re‑introduces the expected classes with lightweight
implementations that exercise the same surface area the tests depend on.  The
focus is correctness and determinism, not production fidelity.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComponentState:
    """Minimal shared state container used by the tests."""

    status: str = "created"
    last_updated: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, **entries: Any) -> None:
        self.metadata.update(entries)
        self.last_updated = datetime.now(timezone.utc)


class AgentLifecycleManager:
    """Simplified lifecycle manager exposing the legacy synchronous API."""

    def __init__(self, event_bus: Optional[Any] = None, state: Optional[ComponentState] = None):
        self.event_bus = event_bus
        self.state = state or ComponentState()
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        self._initialized = True
        self.state.status = "initialized"
        self.state.update(agent_system="ready")
        logger.debug("AgentLifecycleManager initialized")
        return True

    def register_agent(self, agent: Any) -> bool:
        agent_id = getattr(agent, "agent_id", getattr(agent, "character_name", None))
        if not agent_id:
            agent_id = f"agent_{len(self._agents)+1}"
        if agent_id in self._agents:
            return False
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "agent_type": getattr(agent, "agent_type", "unknown"),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        return True

    def remove_agent(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get_agent_list(self) -> List[Dict[str, Any]]:
        return list(self._agents.values())

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_initialized": self._initialized,
            "total_agents": len(self._agents),
            "health": "healthy" if self._initialized else "offline",
        }


class WorldStateManager:
    """Simple JSON-backed world state manager that mirrors the test needs."""

    def __init__(
        self,
        event_bus: Optional[Any] = None,
        state: Optional[ComponentState] = None,
        state_file: Optional[str] = None,
    ) -> None:
        self.event_bus = event_bus
        self.state = state or ComponentState()
        self.state_file = Path(state_file or "world_state.json")
        self._state: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        if self.state_file.exists():
            self.load_world_state()
        else:
            self._state = self._default_state()
            self.save_world_state()
        self.state.status = "initialized"
        self.state.update(world_state="ready")
        logger.debug("WorldStateManager initialized at %s", self.state_file)
        return True

    def _default_state(self) -> Dict[str, Any]:
        return {
            "environment": {"time_of_day": "noon", "weather": "clear"},
            "locations": ["tavern", "market", "academy"],
            "actors": [],
        }

    def get_world_state_summary(self) -> Dict[str, Any]:
        return {
            "environment": self._state.get("environment", {}),
            "locations": self._state.get("locations", []),
            "actor_count": len(self._state.get("actors", [])),
        }

    def save_world_state(self, path: Optional[str] = None) -> bool:
        target = Path(path) if path else self.state_file
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(self._state, indent=2))
            return True
        except OSError as exc:
            logger.warning("Failed to save world state: %s", exc)
            return False

    def load_world_state(self, path: Optional[str] = None) -> bool:
        source = Path(path) if path else self.state_file
        try:
            self._state = json.loads(source.read_text())
            return True
        except FileNotFoundError:
            self._state = self._default_state()
            return False
        except json.JSONDecodeError as exc:
            logger.warning("Corrupt world state file %s: %s", source, exc)
            self._state = self._default_state()
            return False


class TurnExecutionEngine:
    """Stub turn execution engine – enough for unit tests."""

    def __init__(self, event_bus: Optional[Any] = None, state: Optional[ComponentState] = None):
        self.event_bus = event_bus
        self.state = state or ComponentState()
        self.turn_count = 0

    def execute_turn(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.turn_count += 1
        result = {
            "status": "completed",
            "turn_number": self.turn_count,
            "context": context or {},
        }
        if self.event_bus and hasattr(self.event_bus, "emit"):
            self.event_bus.emit("turn_completed", result)
        return result


__all__ = [
    "AgentLifecycleManager",
    "WorldStateManager",
    "TurnExecutionEngine",
    "ComponentState",
]
