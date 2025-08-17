#!/usr/bin/env python3
"""
Interaction API.

API endpoints for real-time character interactions, conversation management,
and dynamic relationship evolution.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import uuid

from src.core.system_orchestrator import SystemOrchestrator
from src.interactions.interaction_engine import InteractionType, InteractionPriority, InteractionContext
from src.interactions.character_interaction_processor import SocialContext

logger = logging.getLogger(__name__)

class InteractionRequest(BaseModel):
    """Request model for initiating character interactions."""
    participants: List[str] = Field(..., min_length=2)
    interaction_type: InteractionType = InteractionType.DIALOGUE
    priority: InteractionPriority = InteractionPriority.NORMAL
    topic: str = Field("", max_length=200)
    
    @field_validator('participants')
    @classmethod
    def validate_participants(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('Duplicate participants not allowed')
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
        await websocket.accept()
        if interaction_id not in self.active_connections:
            self.active_connections[interaction_id] = []
        self.active_connections[interaction_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, interaction_id: str):
        if interaction_id in self.active_connections:
            self.active_connections[interaction_id].remove(websocket)
            if not self.active_connections[interaction_id]:
                del self.active_connections[interaction_id]

class InteractionAPI:
    """API for real-time character interactions and conversation management."""
    
    def __init__(self, orchestrator: SystemOrchestrator):
        """Initializes the interaction API."""
        self.orchestrator = orchestrator
        self.websocket_manager = WebSocketConnectionManager()
        self.active_interactions: Dict[str, Any] = {}
        logger.info("Interaction API initialized.")
    
    def setup_routes(self, app: FastAPI):
        """Sets up API routes for interaction management."""
        
        @app.post("/api/v1/interactions", response_model=InteractionResponse)
        async def create_interaction(request: InteractionRequest):
            """Initiates a new character interaction."""
            try:
                interaction_id = f"int_{uuid.uuid4().hex[:8]}"
                
                interaction_context = InteractionContext(
                    interaction_id=interaction_id,
                    interaction_type=request.interaction_type,
                    priority=request.priority,
                    participants=request.participants,
                    metadata={"topic": request.topic}
                )
                
                self.active_interactions[interaction_id] = {"context": interaction_context, "status": "initiated"}
                
                asyncio.create_task(self._process_interaction_async(interaction_id))
                
                return InteractionResponse(
                    interaction_id=interaction_id,
                    status="initiated",
                    created_at=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error creating interaction: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

    async def _process_interaction_async(self, interaction_id: str):
        """Processes an interaction asynchronously."""
        try:
            state = self.active_interactions[interaction_id]
            state["status"] = "processing"
            # Simulate work
            await asyncio.sleep(5)
            state["status"] = "completed"
        except Exception as e:
            logger.error(f"Error processing interaction {interaction_id}: {e}")
            if interaction_id in self.active_interactions:
                self.active_interactions[interaction_id]["status"] = "error"

def create_interaction_api(orchestrator: SystemOrchestrator) -> InteractionAPI:
    """Creates and configures an interaction API instance."""
    return InteractionAPI(orchestrator)

__all__ = ['InteractionAPI', 'create_interaction_api']