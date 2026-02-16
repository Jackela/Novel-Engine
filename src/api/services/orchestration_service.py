"""Orchestration Service - Business logic extracted from router."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Set

from src.api.schemas import (
    NarrativeData,
    OrchestrationStartRequest,
    OrchestrationStatusData,
    SimulationRequest,
)
from src.api.services.paths import get_characters_directory_path
from src.core.result import Err, Error, Ok

if TYPE_CHECKING:
    from src.core.result import _Error as ResultError
    from src.core.result import _Ok as ResultOk

logger = logging.getLogger(__name__)


class OrchestrationService:
    """Service layer for orchestration operations."""

    def __init__(self, api_service: Any = None):
        self.api_service = api_service

    async def get_status(
        self,
    ) -> ResultOk[OrchestrationStatusData] | ResultError[Error]:
        """
        Get current orchestration status.

        Returns:
            Result with status data on success, Error if service unavailable
        """
        if not self.api_service:
            return Err(
                Error(
                    code="SERVICE_UNAVAILABLE",
                    message="Orchestration service not available",
                    recoverable=True,
                )
            )

        status = await self.api_service.get_status()
        return Ok(OrchestrationStatusData(**status))

    async def start(
        self, request: Optional[OrchestrationStartRequest] = None
    ) -> ResultOk[dict[str, Any]] | ResultError[Error]:
        """
        Start orchestration with given parameters.

        Returns:
            Result with task info on success, Error if initialization fails
        """
        if not self.api_service:
            return Err(
                Error(
                    code="SERVICE_UNAVAILABLE",
                    message="Orchestration service not initialized",
                    recoverable=True,
                )
            )

        params = request or OrchestrationStartRequest()
        character_names = params.character_names or self._get_default_characters()
        total_turns = params.total_turns or 3

        sim_request = SimulationRequest(
            character_names=character_names, turns=total_turns
        )

        try:
            result = await self.api_service.start_simulation(sim_request)
            return Ok(
                {
                    "success": result.get("success", True),
                    "status": result.get("status", "started"),
                    "task_id": result.get("task_id"),
                    "message": result.get("message"),
                }
            )
        except ValueError as exc:
            logger.warning("Invalid orchestration request: %s", exc)
            return Err(
                Error(
                    code="INVALID_REQUEST",
                    message=str(exc),
                    recoverable=True,
                )
            )

    async def stop(self) -> ResultOk[dict[str, Any]] | ResultError[Error]:
        """
        Stop the current orchestration.

        Returns:
            Result with stop result on success, Error if service unavailable
        """
        if not self.api_service:
            return Err(
                Error(
                    code="SERVICE_UNAVAILABLE",
                    message="Service unavailable",
                    recoverable=True,
                )
            )
        result = await self.api_service.stop_simulation()
        return Ok(
            {
                "success": result.get("success", True),
                "message": result.get("message"),
            }
        )

    async def pause(self) -> ResultOk[dict[str, Any]] | ResultError[Error]:
        """
        Pause the current orchestration.

        Returns:
            Result with pause result on success, Error if service unavailable
        """
        if not self.api_service:
            return Err(
                Error(
                    code="SERVICE_UNAVAILABLE",
                    message="Service unavailable",
                    recoverable=True,
                )
            )
        result = await self.api_service.pause_simulation()
        return Ok(
            {
                "success": result.get("success", True),
                "message": result.get("message"),
            }
        )

    async def get_narrative(self) -> ResultOk[NarrativeData] | ResultError[Error]:
        """
        Get current narrative content.

        Returns:
            Result with narrative data on success, Error if service unavailable
        """
        if not self.api_service:
            return Err(
                Error(
                    code="SERVICE_UNAVAILABLE",
                    message="Orchestration service not available",
                    recoverable=True,
                )
            )

        narrative = await self.api_service.get_narrative()
        return Ok(
            NarrativeData(
                story=narrative.get("story", ""),
                participants=narrative.get("participants", []),
                turns_completed=narrative.get("turns_completed", 0),
                last_generated=narrative.get("last_generated"),
                has_content=bool(narrative.get("story", "")),
            )
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
