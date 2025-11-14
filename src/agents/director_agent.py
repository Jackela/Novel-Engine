#!/usr/bin/env python3
"""
DirectorAgent Backward-Compatible Entry Point.

Allows instantiation without explicitly passing EventBus/log paths (legacy behavior)
while delegating the actual functionality to the integrated implementation.
"""

import os
from pathlib import Path
from typing import Any, Optional

from src.agents.director_agent_integrated import DirectorAgent as _DirectorAgentImpl
from src.event_bus import EventBus


def _default_campaign_log_path() -> str:
    root = Path.cwd()
    candidate = root / "campaign_log.md"
    return str(candidate)


_UNSET: Any = object()


class DirectorAgent(_DirectorAgentImpl):
    """Compatibility wrapper exposing the legacy constructor signature."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = _UNSET,
        world_state_file_path: Optional[str] = None,
        campaign_log_path: Optional[str] = None,
        campaign_brief_path: Optional[str] = None,
    ):
        if event_bus is _UNSET:
            event_bus = EventBus()
        elif event_bus is None:
            raise ValueError("DirectorAgent requires a valid EventBus instance")
        resolved_log_path = campaign_log_path or _default_campaign_log_path()
        os.makedirs(os.path.dirname(resolved_log_path) or ".", exist_ok=True)
        super().__init__(
            event_bus,
            world_state_file_path,
            resolved_log_path,
            campaign_brief_path,
        )

    @property
    def campaign_log_file(self) -> str:
        """Legacy alias expected by integration tests."""
        base = getattr(self, "base", None)
        if base and hasattr(base, "campaign_log_path"):
            return base.campaign_log_path
        return _default_campaign_log_path()


__all__ = ["DirectorAgent"]
