"""Compatibility module for legacy DirectorAgent extended components."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class _LogStats:
    total_entries: int = 0
    info_entries: int = 0
    warning_entries: int = 0
    error_entries: int = 0
    current_entries: int = 0


class CampaignLoggingService:
    def __init__(
        self,
        event_bus: Optional[Any] = None,
        state: Optional[Any] = None,
        log_file: Optional[str] = None,
    ) -> None:
        self.event_bus = event_bus
        self.state = state
        self.log_file = Path(log_file or "campaign.log")
        self._stats = _LogStats()
        self._initialized = False

    async def initialize(self) -> bool:
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.log_file.exists():
                self.log_file.write_text("# Campaign Log\n", encoding="utf-8")
            self._initialized = True
            return True
        except OSError as exc:
            logger.error("Failed to initialize campaign logging: %s", exc)
            return False

    def log_event(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self._initialized:
            raise RuntimeError("CampaignLoggingService not initialized")
        metadata = metadata or {}
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "metadata": metadata,
        }
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        self._stats.total_entries += 1
        self._stats.current_entries += 1

    def get_log_statistics(self) -> Dict[str, int]:
        return {
            "total_entries": self._stats.total_entries,
            "current_entries": self._stats.current_entries,
        }

    async def cleanup(self) -> None:
        await asyncio.sleep(0)  # keep signature async
        self._initialized = False


class ConfigurationService:
    def __init__(self, event_bus: Optional[Any] = None, state: Optional[Any] = None, base_config: Optional[Dict[str, Any]] = None):
        self.event_bus = event_bus
        self.state = state
        self._config = base_config or {
            "simulation": {"max_agents": 10, "max_turns": 3},
            "logging": {"level": "INFO"},
        }
        self._initialized = False

    async def initialize(self) -> bool:
        self._initialized = True
        return True

    def load_configuration(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._config))

    def get_config_value(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def update_config(self, updates: Dict[str, Any]) -> bool:
        self._config.update(updates)
        return True


class SystemErrorHandler:
    def __init__(self, event_bus: Optional[Any] = None, state: Optional[Any] = None):
        self.event_bus = event_bus
        self.state = state
        self._recoveries: Dict[Type[BaseException], Callable[[BaseException, Dict[str, Any]], bool]] = {}
        self._stats = {"total_errors": 0, "recoveries": 0}

    async def initialize(self) -> bool:
        return True

    def handle_error(self, error: BaseException, context: Optional[Dict[str, Any]] = None) -> bool:
        self._stats["total_errors"] += 1
        context = context or {}
        handler = self._recoveries.get(type(error))
        if handler:
            try:
                if handler(error, context):
                    self._stats["recoveries"] += 1
                    return True
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Recovery handler failed: %s", exc)
        return False

    def register_error_recovery(self, exc_type: Type[BaseException], handler: Callable[[BaseException, Dict[str, Any]], bool]) -> None:
        self._recoveries[exc_type] = handler

    def get_error_statistics(self) -> Dict[str, int]:
        return dict(self._stats)


class NarrativeOrchestrator:
    def __init__(self, event_bus: Optional[Any] = None, state: Optional[Any] = None):
        self.event_bus = event_bus
        self.state = state

    def generate_context(self, agent_id: str) -> Dict[str, Any]:
        return {"agent_id": agent_id, "summary": "Generated narrative context"}


__all__ = [
    "CampaignLoggingService",
    "ConfigurationService",
    "SystemErrorHandler",
    "NarrativeOrchestrator",
]
