#!/usr/bin/env python3
"""
Traditional System Coordinator
===============================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Manages traditional Novel Engine system orchestration.

Responsibilities:
- Initialize and manage SystemOrchestrator
- Coordinate traditional system startup
- Coordinate traditional system shutdown
- Provide traditional system status and metrics

This class follows the Single Responsibility Principle by focusing solely on
traditional system coordination, separate from integration orchestration.
"""

import logging
from typing import Optional

from src.core.data_models import ErrorInfo, StandardResponse
from src.core.system_orchestrator import OrchestratorConfig, SystemOrchestrator

logger = logging.getLogger(__name__)


class TraditionalSystemCoordinator:
    """
    Coordinates traditional Novel Engine system orchestration.

    This class encapsulates all traditional system management logic, providing
    a clean interface for initialization, startup, shutdown, and status retrieval.
    """

    def __init__(
        self,
        database_path: str = "data/context_engineering.db",
        orchestrator_config: Optional[OrchestratorConfig] = None,
    ):
        """
        Initialize the traditional system coordinator.

        Args:
            database_path: Path to the system database
            orchestrator_config: Optional configuration for SystemOrchestrator
        """
        self.database_path = database_path
        self.orchestrator_config = orchestrator_config

        # Initialize traditional system orchestrator
        self.system_orchestrator = SystemOrchestrator(
            database_path, orchestrator_config
        )

        logger.info("Traditional System Coordinator initialized successfully")

    # ===================================================================
    # Traditional System Lifecycle Methods
    # ===================================================================

    async def startup_traditional_systems(self) -> StandardResponse:
        """
        Start traditional system orchestrator.

        Returns:
            StandardResponse: Result of traditional system startup
        """
        traditional_result = await self.system_orchestrator.startup()

        if not traditional_result.success:
            error_msg = (
                traditional_result.error.message
                if traditional_result.error
                else "Unknown"
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="TRADITIONAL_STARTUP_FAILED",
                    message="Traditional system startup failed",
                    details={"traditional_error": error_msg},
                ),
            )

        return traditional_result

    async def shutdown_traditional_systems(self) -> StandardResponse:
        """
        Shutdown traditional system orchestrator.

        Returns:
            StandardResponse: Result of traditional system shutdown
        """
        return await self.system_orchestrator.shutdown()

    async def get_traditional_system_metrics(self) -> StandardResponse:
        """
        Get traditional system metrics and status.

        Returns:
            StandardResponse: Traditional system metrics
        """
        return await self.system_orchestrator.get_system_metrics()


__all__ = ["TraditionalSystemCoordinator"]
