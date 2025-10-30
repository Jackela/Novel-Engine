"""
Agent State Manager
===================

Manages PersonaAgent state tracking, persistence, and updates.
Handles current location, status, morale, and dynamic state changes.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    """Represents the current state of a PersonaAgent."""

    agent_id: str
    current_location: Optional[str] = None
    current_status: str = "active"  # active, injured, unconscious, dead, resting
    morale_level: float = 1.0  # -1.0 (broken) to 1.0 (fanatic)
    health_status: str = "healthy"  # healthy, injured, critical, dead
    last_action: Optional[str] = None
    last_action_timestamp: Optional[str] = None
    active_goals: List[str] = field(default_factory=list)
    current_priorities: Dict[str, float] = field(default_factory=dict)
    temporary_modifiers: Dict[str, Any] = field(default_factory=dict)
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentStateManager:
    """
    Manages agent state persistence and updates.

    Responsibilities:
    - Track current agent status and location
    - Manage morale and health status
    - Handle state transitions and validation
    - Provide state persistence and loading
    - Maintain state history for analysis
    """

    def __init__(self, agent_id: str, logger: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger(__name__)

        # Initialize state
        self._state = AgentState(agent_id=agent_id)

        # State validation rules
        self._valid_statuses = {
            "active",
            "injured",
            "unconscious",
            "dead",
            "resting",
            "stunned",
            "incapacitated",
            "fleeing",
            "hiding",
        }

        self._valid_health_statuses = {
            "healthy",
            "injured",
            "critical",
            "dead",
            "recovering",
        }

        # State change callbacks
        self._state_change_callbacks: List[callable] = []

    async def update_state(self, state_updates: Dict[str, Any]) -> None:
        """
        Update agent state with validation and history tracking.

        Args:
            state_updates: Dictionary of state updates to apply
        """
        try:
            old_state = asdict(self._state)

            # Apply updates with validation
            for key, value in state_updates.items():
                if hasattr(self._state, key):
                    # Validate specific fields
                    if key == "current_status" and value not in self._valid_statuses:
                        self.logger.warning(
                            f"Invalid status '{value}', using current status"
                        )
                        continue

                    if (
                        key == "health_status"
                        and value not in self._valid_health_statuses
                    ):
                        self.logger.warning(
                            f"Invalid health status '{value}', using current status"
                        )
                        continue

                    if key == "morale_level":
                        # Clamp morale to valid range
                        value = max(-1.0, min(1.0, float(value)))

                    # Update the state
                    setattr(self._state, key, value)

                    self.logger.debug(f"Updated {key}: {old_state.get(key)} -> {value}")
                else:
                    self.logger.warning(f"Unknown state field: {key}")

            # Update timestamp
            self._state.last_updated = datetime.now().isoformat()

            # Record state change in history
            await self._record_state_change(
                old_state, asdict(self._state), state_updates
            )

            # Notify callbacks
            await self._notify_state_change(state_updates)

            self.logger.info(f"Agent {self.agent_id} state updated successfully")

        except Exception as e:
            self.logger.error(f"Failed to update agent state: {e}")
            raise

    async def get_state(self) -> Dict[str, Any]:
        """
        Get current agent state.

        Returns:
            Dict containing current agent state
        """
        return asdict(self._state)

    async def save_state(self, file_path: str) -> bool:
        """
        Save agent state to file.

        Args:
            file_path: Path to save state file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            state_data = {
                "agent_id": self.agent_id,
                "state": asdict(self._state),
                "saved_at": datetime.now().isoformat(),
                "version": "1.0",
            }

            save_path = Path(file_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Agent state saved to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save agent state: {e}")
            return False

    async def load_state(self, file_path: str) -> bool:
        """
        Load agent state from file.

        Args:
            file_path: Path to state file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            load_path = Path(file_path)

            if not load_path.exists():
                self.logger.warning(f"State file not found: {file_path}")
                return False

            with open(load_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Validate loaded data
            if state_data.get("agent_id") != self.agent_id:
                self.logger.error(
                    f"Agent ID mismatch: expected {self.agent_id}, got {state_data.get('agent_id')}"
                )
                return False

            if "state" not in state_data:
                self.logger.error("Invalid state file format")
                return False

            # Load state
            loaded_state = state_data["state"]
            self._state = AgentState(**loaded_state)

            self.logger.info(f"Agent state loaded from {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load agent state: {e}")
            return False

    def get_current_location(self) -> Optional[str]:
        """Get agent's current location."""
        return self._state.current_location

    def get_current_status(self) -> str:
        """Get agent's current status."""
        return self._state.current_status

    def get_morale_level(self) -> float:
        """Get agent's morale level."""
        return self._state.morale_level

    def get_health_status(self) -> str:
        """Get agent's health status."""
        return self._state.health_status

    def is_active(self) -> bool:
        """Check if agent is currently active."""
        return (
            self._state.current_status == "active"
            and self._state.health_status != "dead"
        )

    def is_incapacitated(self) -> bool:
        """Check if agent is incapacitated."""
        incapacitated_statuses = {"unconscious", "dead", "incapacitated"}
        return self._state.current_status in incapacitated_statuses

    async def set_location(self, location: str) -> None:
        """Set agent's current location."""
        await self.update_state({"current_location": location})

    async def set_status(self, status: str) -> None:
        """Set agent's current status."""
        await self.update_state({"current_status": status})

    async def adjust_morale(self, adjustment: float, reason: str = "") -> None:
        """
        Adjust agent's morale level.

        Args:
            adjustment: Morale adjustment (-1.0 to 1.0)
            reason: Reason for adjustment
        """
        new_morale = max(-1.0, min(1.0, self._state.morale_level + adjustment))

        await self.update_state(
            {
                "morale_level": new_morale,
                "temporary_modifiers": {
                    **self._state.temporary_modifiers,
                    "last_morale_change": {
                        "adjustment": adjustment,
                        "reason": reason,
                        "timestamp": datetime.now().isoformat(),
                    },
                },
            }
        )

        self.logger.info(
            f"Morale adjusted by {adjustment:+.2f} ({reason}): {new_morale:.2f}"
        )

    async def set_health_status(self, health_status: str) -> None:
        """Set agent's health status."""
        await self.update_state({"health_status": health_status})

        # Auto-update status based on health
        if health_status == "dead":
            await self.update_state({"current_status": "dead"})
        elif health_status == "critical":
            await self.update_state({"current_status": "incapacitated"})

    async def record_action(self, action_description: str) -> None:
        """Record agent's last action."""
        await self.update_state(
            {
                "last_action": action_description,
                "last_action_timestamp": datetime.now().isoformat(),
            }
        )

    async def add_goal(self, goal: str) -> None:
        """Add a goal to active goals."""
        if goal not in self._state.active_goals:
            new_goals = self._state.active_goals + [goal]
            await self.update_state({"active_goals": new_goals})

    async def remove_goal(self, goal: str) -> None:
        """Remove a goal from active goals."""
        if goal in self._state.active_goals:
            new_goals = [g for g in self._state.active_goals if g != goal]
            await self.update_state({"active_goals": new_goals})

    async def set_priority(self, priority_name: str, priority_value: float) -> None:
        """Set a priority value."""
        new_priorities = {
            **self._state.current_priorities,
            priority_name: priority_value,
        }
        await self.update_state({"current_priorities": new_priorities})

    async def add_temporary_modifier(
        self, modifier_name: str, modifier_data: Any, duration: Optional[int] = None
    ) -> None:
        """Add a temporary modifier."""
        modifier_info = {"data": modifier_data, "added_at": datetime.now().isoformat()}

        if duration:
            modifier_info["expires_at"] = datetime.now().timestamp() + duration

        new_modifiers = {
            **self._state.temporary_modifiers,
            modifier_name: modifier_info,
        }
        await self.update_state({"temporary_modifiers": new_modifiers})

    async def clean_expired_modifiers(self) -> None:
        """Remove expired temporary modifiers."""
        current_time = datetime.now().timestamp()
        active_modifiers = {}

        for name, modifier in self._state.temporary_modifiers.items():
            expires_at = modifier.get("expires_at")
            if expires_at is None or expires_at > current_time:
                active_modifiers[name] = modifier

        if len(active_modifiers) != len(self._state.temporary_modifiers):
            await self.update_state({"temporary_modifiers": active_modifiers})
            self.logger.debug("Cleaned expired temporary modifiers")

    def register_state_change_callback(self, callback: callable) -> None:
        """Register callback for state changes."""
        self._state_change_callbacks.append(callback)

    async def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of current agent state."""
        return {
            "agent_id": self.agent_id,
            "location": self._state.current_location,
            "status": self._state.current_status,
            "health": self._state.health_status,
            "morale": round(self._state.morale_level, 2),
            "is_active": self.is_active(),
            "active_goals": len(self._state.active_goals),
            "last_action": self._state.last_action,
            "last_updated": self._state.last_updated,
        }

    async def _record_state_change(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> None:
        """Record state change in history."""
        try:
            change_record = {
                "timestamp": datetime.now().isoformat(),
                "updates": updates,
                "old_values": {key: old_state.get(key) for key in updates.keys()},
                "new_values": {key: new_state.get(key) for key in updates.keys()},
            }

            # Limit history size
            self._state.state_history.append(change_record)
            if len(self._state.state_history) > 100:  # Keep last 100 changes
                self._state.state_history = self._state.state_history[-100:]

        except Exception as e:
            self.logger.debug(f"Failed to record state change: {e}")

    async def _notify_state_change(self, updates: Dict[str, Any]) -> None:
        """Notify registered callbacks of state changes."""
        for callback in self._state_change_callbacks:
            try:
                if callable(callback):
                    if hasattr(callback, "__call__") and hasattr(callback, "__code__"):
                        # Check if callback is async
                        import inspect

                        if inspect.iscoroutinefunction(callback):
                            await callback(self.agent_id, updates)
                        else:
                            callback(self.agent_id, updates)
            except Exception as e:
                self.logger.warning(f"State change callback failed: {e}")

    def get_state_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent state change history."""
        return self._state.state_history[-limit:] if self._state.state_history else []
