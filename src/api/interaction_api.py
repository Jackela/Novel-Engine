#!/usr/bin/env python3
"""
Interaction API.

API endpoints for real-time character interactions, conversation management,
and dynamic relationship evolution.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel, Field, field_validator

from src.core.system_orchestrator import SystemOrchestrator
from src.interactions.engine.models.interaction_models import (
    InteractionContext,
    InteractionPriority,
    InteractionType,
)

logger = logging.getLogger(__name__)


class InteractionRequest(BaseModel):
    """Request model for initiating character interactions."""

    participants: List[str] = Field(..., min_length=2)
    interaction_type: InteractionType = InteractionType.DIALOGUE
    priority: InteractionPriority = InteractionPriority.NORMAL
    topic: str = Field("", max_length=200)

    @field_validator("participants")
    @classmethod
    def validate_participants(cls, v):
        """
        Validate that all participants are unique.

        Args:
            v: List of participant IDs

        Returns:
            Validated participants list

        Raises:
            ValueError: If duplicate participants are found
        """
        if len(v) != len(set(v)):
            raise ValueError("Duplicate participants not allowed")
        return v


class InteractionResponse(BaseModel):
    """Response model for interaction data."""

    interaction_id: str
    status: str
    created_at: datetime


class WebSocketConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, interaction_id: str):
        """
        Connect a WebSocket to an interaction.

        Args:
            websocket: The WebSocket connection to add
            interaction_id: ID of the interaction to join
        """
        await websocket.accept()
        if interaction_id not in self.active_connections:
            self.active_connections[interaction_id] = []
        self.active_connections[interaction_id].append(websocket)

    def disconnect(self, websocket: WebSocket, interaction_id: str):
        """
        Disconnect a WebSocket from an interaction.

        Args:
            websocket: The WebSocket connection to remove
            interaction_id: ID of the interaction to leave
        """
        if interaction_id in self.active_connections:
            self.active_connections[interaction_id].remove(websocket)
            if not self.active_connections[interaction_id]:
                del self.active_connections[interaction_id]


class InteractionAPI:
    """API for real-time character interactions and conversation management."""

    def __init__(self, orchestrator: Optional[SystemOrchestrator]):
        """Initializes the interaction API."""
        self.orchestrator = orchestrator
        self.websocket_manager = WebSocketConnectionManager()
        self.active_interactions: Dict[str, Any] = {}
        logger.info("Interaction API initialized.")

    def set_orchestrator(self, orchestrator: SystemOrchestrator):
        """Set the orchestrator after initialization."""
        self.orchestrator = orchestrator
        logger.info("Interaction API orchestrator set.")

    def setup_routes(self, app: FastAPI):
        """Sets up API routes for interaction management."""

        @app.post("/api/v1/interactions", response_model=InteractionResponse)
        async def create_interaction(request: InteractionRequest):
            """Initiates a new character interaction."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            try:
                # Validate that all participants exist
                active_agents = getattr(self.orchestrator, "active_agents", {})
                missing_participants = [
                    p for p in request.participants if p not in active_agents
                ]
                if missing_participants:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Participants not found: {', '.join(missing_participants)}",
                    )

                interaction_id = f"int_{uuid.uuid4().hex[:8]}"

                interaction_context = InteractionContext(
                    interaction_id=interaction_id,
                    interaction_type=request.interaction_type,
                    priority=request.priority,
                    participants=request.participants,
                    metadata={"topic": request.topic},
                )

                self.active_interactions[interaction_id] = {
                    "context": interaction_context,
                    "status": "initiated",
                    "created_at": datetime.now(),
                }

                asyncio.create_task(self._process_interaction_async(interaction_id))

                return InteractionResponse(
                    interaction_id=interaction_id,
                    status="initiated",
                    created_at=datetime.now(),
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating interaction: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

        @app.get("/api/v1/interactions", response_model=dict)
        async def list_interactions():
            """List all active interactions."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            try:
                interactions = []
                for interaction_id, data in self.active_interactions.items():
                    interactions.append(
                        {
                            "interaction_id": interaction_id,
                            "status": data["status"],
                            "participants": data["context"].participants,
                            "interaction_type": data["context"].interaction_type.value,
                            "created_at": data.get(
                                "created_at", datetime.now()
                            ).isoformat(),
                        }
                    )

                return {"interactions": interactions, "total": len(interactions)}
            except Exception as e:
                logger.error(f"Error listing interactions: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

        @app.get("/api/v1/interactions/{interaction_id}", response_model=dict)
        async def get_interaction(interaction_id: str):
            """Get detailed interaction information."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            try:
                if interaction_id not in self.active_interactions:
                    raise HTTPException(status_code=404, detail="Interaction not found")

                data = self.active_interactions[interaction_id]
                return {
                    "interaction_id": interaction_id,
                    "status": data["status"],
                    "context": {
                        "participants": data["context"].participants,
                        "interaction_type": data["context"].interaction_type.value,
                        "priority": data["context"].priority.value,
                        "metadata": data["context"].metadata,
                    },
                    "created_at": data.get("created_at", datetime.now()).isoformat(),
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting interaction {interaction_id}: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

    async def _process_interaction_async(self, interaction_id: str):
        """Processes an interaction asynchronously."""
        try:
            if not self.orchestrator:
                logger.error(
                    f"No orchestrator available for interaction {interaction_id}"
                )
                if interaction_id in self.active_interactions:
                    self.active_interactions[interaction_id]["status"] = "error"
                return

            state = self.active_interactions[interaction_id]
            state["status"] = "processing"

            # Use orchestrator to process the interaction
            state["context"]
            try:
                # For now, simulate interaction processing
                # In the future, this would use the actual interaction engine
                await asyncio.sleep(2)  # Reduced simulation time

                # Simulate successful interaction
                state["status"] = "completed"
                state["completed_at"] = datetime.now()

                logger.info(f"Interaction {interaction_id} completed successfully")
            except Exception as process_error:
                logger.error(
                    f"Interaction processing failed for {interaction_id}: {process_error}"
                )
                state["status"] = "failed"
                state["error"] = str(process_error)

        except Exception as e:
            logger.error(f"Error processing interaction {interaction_id}: {e}")
            if interaction_id in self.active_interactions:
                self.active_interactions[interaction_id]["status"] = "error"


def create_interaction_api(
    orchestrator: Optional[SystemOrchestrator],
) -> InteractionAPI:
    """Creates and configures an interaction API instance."""
    return InteractionAPI(orchestrator)


__all__ = ["InteractionAPI", "create_interaction_api"]
