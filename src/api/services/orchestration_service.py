"""Orchestration Service - Business logic extracted from router."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, List, Optional, Set

from src.api.schemas import (
    NarrativeData,
    NarrativeResponse,
    OrchestrationStartRequest,
    OrchestrationStartResponse,
    OrchestrationStatusData,
    OrchestrationStatusResponse,
    OrchestrationStopResponse,
    SimulationRequest,
)
from src.api.services.paths import get_characters_directory_path

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Service layer for orchestration operations."""

    def __init__(self, api_service: Any = None):
        self.api_service = api_service

    async def get_status(self) -> OrchestrationStatusResponse:
        """Get current orchestration status."""
        if not self.api_service:
            return OrchestrationStatusResponse(
                success=False,
                message="Orchestration service not available",
                data=OrchestrationStatusData(status="error"),
            )

        status = await self.api_service.get_status()
        return OrchestrationStatusResponse(
            success=True,
            data=OrchestrationStatusData(**status),
        )

    async def start(
        self, request: Optional[OrchestrationStartRequest] = None
    ) -> OrchestrationStartResponse:
        """Start orchestration with given parameters."""
        if not self.api_service:
            return OrchestrationStartResponse(
                success=False,
                status="error",
                message="Orchestration service not initialized",
            )

        params = request or OrchestrationStartRequest()
        character_names = params.character_names or self._get_default_characters()
        total_turns = params.total_turns or 3

        sim_request = SimulationRequest(
            character_names=character_names, turns=total_turns
        )

        try:
            result = await self.api_service.start_simulation(sim_request)
            return OrchestrationStartResponse(
                success=result.get("success", True),
                status=result.get("status", "started"),
                task_id=result.get("task_id"),
                message=result.get("message"),
            )
        except ValueError as exc:
            logger.warning("Invalid orchestration request: %s", exc)
            return OrchestrationStartResponse(
                success=False,
                status="error",
                message="Invalid orchestration request.",
            )

    async def stop(self) -> OrchestrationStopResponse:
        """Stop the current orchestration."""
        if not self.api_service:
            return OrchestrationStopResponse(
                success=False, message="Service unavailable"
            )
        result = await self.api_service.stop_simulation()
        return OrchestrationStopResponse(
            success=result.get("success", True),
            message=result.get("message"),
        )

    async def pause(self) -> OrchestrationStopResponse:
        """Pause the current orchestration."""
        if not self.api_service:
            return OrchestrationStopResponse(
                success=False, message="Service unavailable"
            )
        result = await self.api_service.pause_simulation()
        return OrchestrationStopResponse(
            success=result.get("success", True),
            message=result.get("message"),
        )

    async def get_narrative(self) -> NarrativeResponse:
        """Get current narrative content."""
        if not self.api_service:
            return NarrativeResponse(
                success=False,
                data=NarrativeData(
                    story="",
                    participants=[],
                    turns_completed=0,
                    has_content=False,
                ),
            )

        narrative = await self.api_service.get_narrative()
        return NarrativeResponse(
            success=True,
            data=NarrativeData(
                story=narrative.get("story", ""),
                participants=narrative.get("participants", []),
                turns_completed=narrative.get("turns_completed", 0),
                last_generated=narrative.get("last_generated"),
                has_content=bool(narrative.get("story", "")),
            ),
        )

    def _get_default_characters(self) -> List[str]:
        """Discover available characters from filesystem."""
        try:
            characters_path = get_characters_directory_path()
            available: Set[str] = set()
            p = Path(characters_path)
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        available.add(item.name)
            return sorted(list(available))[:3] or ["pilot", "scientist", "engineer"]
        except Exception as exc:
            logger.warning("Failed to fetch characters: %s", exc)
            return ["pilot", "scientist", "engineer"]
