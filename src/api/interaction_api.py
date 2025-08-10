#!/usr/bin/env python3
"""
++ SACRED INTERACTION API BLESSED BY REAL-TIME DYNAMICS ++
==========================================================

Holy API endpoints for real-time character interactions, conversation
management, and dynamic relationship evolution serving User Story 2
blessed by the Omnissiah's social orchestration wisdom.

++ THROUGH INTERACTIONS, CHARACTERS ACHIEVE SOCIAL MASTERY ++

Story Implementation: Real-Time Character Interactions (Story 2)
Sacred Author: Dev Agent James
万机之神保佑互动系统 (May the Omnissiah bless interaction systems)
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from dataclasses import asdict
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid

# Import blessed framework components
from src.core.system_orchestrator import SystemOrchestrator
from src.interactions.interaction_engine import InteractionEngine, InteractionType, InteractionPriority, InteractionContext
from src.interactions.character_interaction_processor import CharacterInteractionProcessor, SocialContext
from src.core.data_models import StandardResponse

# Sacred logging
logger = logging.getLogger(__name__)


class InteractionRequest(BaseModel):
    """Request model for initiating character interactions."""
    participants: List[str] = Field(..., min_items=2, description="Character IDs participating in interaction")
    interaction_type: InteractionType = Field(InteractionType.DIALOGUE, description="Type of interaction")
    priority: InteractionPriority = Field(InteractionPriority.NORMAL, description="Interaction priority level")
    
    # Context configuration
    topic: str = Field("", max_length=200, description="Interaction topic or subject")
    location: str = Field("", max_length=100, description="Interaction location")
    social_context: SocialContext = Field(SocialContext.CASUAL, description="Social context of interaction")
    duration_minutes: int = Field(30, ge=1, le=480, description="Expected interaction duration")
    
    # Interaction settings
    auto_process: bool = Field(True, description="Automatically process interaction phases")
    real_time_updates: bool = Field(False, description="Enable real-time websocket updates")
    intervention_allowed: bool = Field(False, description="Allow user intervention during interaction")
    
    # Environmental factors
    privacy_level: float = Field(0.8, ge=0.0, le=1.0, description="Privacy level (0=public, 1=private)")
    formality_level: float = Field(0.3, ge=0.0, le=1.0, description="Formality level (0=casual, 1=formal)")
    tension_level: float = Field(0.0, ge=0.0, le=1.0, description="Initial tension level")
    time_pressure: float = Field(0.0, ge=0.0, le=1.0, description="Time pressure level")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional interaction metadata")
    
    @validator('participants')
    def validate_participants(cls, v):
        """Validate participant list."""
        if len(v) != len(set(v)):
            raise ValueError('Duplicate participants not allowed')
        return v


class ConversationRequest(BaseModel):
    """Request model for conversation-specific interactions."""
    participants: List[str] = Field(..., min_items=2, max_items=10)
    topic: str = Field("", max_length=200, description="Conversation topic")
    location: str = Field("Virtual Space", max_length=100)
    context: SocialContext = Field(SocialContext.CASUAL)
    max_turns: int = Field(50, ge=5, le=200, description="Maximum conversation turns")
    turn_timeout_seconds: int = Field(30, ge=5, le=300, description="Timeout per turn")
    
    # Conversation style
    style: str = Field("natural", description="Conversation style (natural, formal, debate, casual)")
    allow_interruptions: bool = Field(True, description="Allow participants to interrupt each other")
    include_internal_thoughts: bool = Field(False, description="Include character internal thoughts")


class InteractionResponse(BaseModel):
    """Response model for interaction data."""
    interaction_id: str
    participants: List[str]
    interaction_type: str
    status: str
    priority: str
    
    # Context information
    topic: str
    location: str
    social_context: str
    
    # Progress tracking
    phases_completed: int
    estimated_duration_seconds: int
    actual_duration_seconds: Optional[int] = None
    current_phase: Optional[str] = None
    
    # Outcomes
    success_level: Optional[float] = None
    satisfaction_levels: Dict[str, float] = Field(default_factory=dict)
    relationship_changes: int = 0
    memories_formed: int = 0
    significant_events: int = 0
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Real-time data
    websocket_url: Optional[str] = None
    live_updates: bool = False


class ConversationTurn(BaseModel):
    """Model for a single conversation turn."""
    turn_id: str
    speaker_id: str
    content: str
    timestamp: datetime
    internal_thoughts: Optional[str] = None
    emotional_state: Dict[str, Any] = Field(default_factory=dict)
    response_to: Optional[str] = None
    turn_number: int


class ConversationResponse(BaseModel):
    """Response model for conversation data."""
    conversation_id: str
    participants: List[str]
    topic: str
    status: str
    
    # Conversation flow
    turns: List[ConversationTurn] = Field(default_factory=list)
    current_speaker: Optional[str] = None
    next_speaker: Optional[str] = None
    
    # Statistics
    total_turns: int = 0
    turns_per_participant: Dict[str, int] = Field(default_factory=dict)
    average_response_time: float = 0.0
    
    # Outcomes
    resolution_achieved: bool = False
    consensus_reached: bool = False
    unresolved_tensions: List[str] = Field(default_factory=list)
    key_decisions: List[str] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime
    last_turn_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WebSocketConnectionManager:
    """Manage WebSocket connections for real-time interaction updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, interaction_id: str):
        """Connect websocket to interaction updates."""
        await websocket.accept()
        if interaction_id not in self.active_connections:
            self.active_connections[interaction_id] = []
        self.active_connections[interaction_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, interaction_id: str):
        """Disconnect websocket from interaction updates."""
        if interaction_id in self.active_connections:
            if websocket in self.active_connections[interaction_id]:
                self.active_connections[interaction_id].remove(websocket)
            if not self.active_connections[interaction_id]:
                del self.active_connections[interaction_id]
    
    async def broadcast_to_interaction(self, interaction_id: str, data: Dict[str, Any]):
        """Broadcast update to all clients watching an interaction."""
        if interaction_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[interaction_id]:
                try:
                    await websocket.send_json(data)
                except:
                    disconnected.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws, interaction_id)


class InteractionAPI:
    """
    ++ SACRED INTERACTION API IMPLEMENTATION BLESSED BY SOCIAL DYNAMICS ++
    
    Comprehensive API for real-time character interactions, conversation
    management, and relationship evolution implementing User Story 2.
    """
    
    def __init__(self, orchestrator: SystemOrchestrator):
        """Initialize interaction API with system orchestrator."""
        self.orchestrator = orchestrator
        self.websocket_manager = WebSocketConnectionManager()
        self.active_interactions: Dict[str, Dict[str, Any]] = {}
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        logger.info("++ Interaction API initialized and blessed ++")
    
    
    def setup_routes(self, app: FastAPI):
        """Set up API routes for interaction management."""
        
        @app.post("/api/v1/interactions", response_model=InteractionResponse)
        async def create_interaction(request: InteractionRequest):
            """
            Initiate a new character interaction with comprehensive configuration.
            
            **Story Implementation**: Real-Time Character Interactions
            **Features**: Multi-participant interactions, real-time updates, social context
            """
            try:
                # Validate all participants exist
                for participant in request.participants:
                    if participant not in self.orchestrator.active_agents:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Character '{participant}' not found"
                        )
                
                # Generate unique interaction ID
                interaction_id = f"int_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # Create interaction context
                interaction_context = InteractionContext(
                    interaction_id=interaction_id,
                    interaction_type=request.interaction_type,
                    priority=request.priority,
                    participants=request.participants,
                    location=request.location,
                    metadata={
                        "topic": request.topic,
                        "social_context": request.social_context.value,
                        "privacy_level": request.privacy_level,
                        "formality_level": request.formality_level,
                        "tension_level": request.tension_level,
                        "time_pressure": request.time_pressure,
                        "duration_minutes": request.duration_minutes,
                        "auto_process": request.auto_process,
                        "real_time_updates": request.real_time_updates,
                        "intervention_allowed": request.intervention_allowed,
                        **request.metadata
                    }
                )
                
                # Store interaction state
                interaction_state = {
                    "context": interaction_context,
                    "status": "initiated",
                    "created_at": datetime.now(),
                    "phases_completed": 0,
                    "current_phase": None,
                    "websocket_connections": []
                }
                self.active_interactions[interaction_id] = interaction_state
                
                # Create websocket URL if real-time updates requested
                websocket_url = None
                if request.real_time_updates:
                    websocket_url = f"/api/v1/interactions/{interaction_id}/stream"
                
                # Start interaction processing if auto_process enabled
                if request.auto_process:
                    asyncio.create_task(self._process_interaction_async(interaction_id))
                
                # Create response
                response = InteractionResponse(
                    interaction_id=interaction_id,
                    participants=request.participants,
                    interaction_type=request.interaction_type.value,
                    status="processing" if request.auto_process else "ready",
                    priority=request.priority.value,
                    topic=request.topic,
                    location=request.location,
                    social_context=request.social_context.value,
                    phases_completed=0,
                    estimated_duration_seconds=request.duration_minutes * 60,
                    created_at=datetime.now(),
                    websocket_url=websocket_url,
                    live_updates=request.real_time_updates
                )
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR creating interaction: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.get("/api/v1/interactions", response_model=List[InteractionResponse])
        async def list_interactions(
            status: Optional[str] = Query(None, description="Filter by interaction status"),
            participant: Optional[str] = Query(None, description="Filter by participant"),
            interaction_type: Optional[str] = Query(None, description="Filter by interaction type"),
            limit: int = Query(50, ge=1, le=100),
            offset: int = Query(0, ge=0)
        ):
            """
            List interactions with filtering and pagination.
            
            **Story Implementation**: Interaction monitoring and management
            """
            try:
                interactions = []
                for interaction_id, state in list(self.active_interactions.items())[offset:offset + limit]:
                    # Apply filters
                    if status and state["status"] != status:
                        continue
                    if participant and participant not in state["context"].participants:
                        continue
                    if interaction_type and state["context"].interaction_type.value != interaction_type:
                        continue
                    
                    # Convert to response model
                    response = await self._create_interaction_response(interaction_id, state)
                    interactions.append(response)
                
                return interactions
                
            except Exception as e:
                logger.error(f"++ ERROR listing interactions: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.get("/api/v1/interactions/{interaction_id}", response_model=InteractionResponse)
        async def get_interaction(interaction_id: str = Path(..., description="Interaction ID")):
            """
            Get detailed interaction status and progress.
            
            **Story Implementation**: Real-time interaction monitoring
            """
            try:
                if interaction_id not in self.active_interactions:
                    raise HTTPException(status_code=404, detail="Interaction not found")
                
                state = self.active_interactions[interaction_id]
                response = await self._create_interaction_response(interaction_id, state)
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR getting interaction {interaction_id}: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.post("/api/v1/conversations", response_model=ConversationResponse)
        async def create_conversation(request: ConversationRequest):
            """
            Start a new multi-character conversation with turn management.
            
            **Story Implementation**: Dynamic conversation orchestration
            """
            try:
                # Validate all participants exist
                for participant in request.participants:
                    if participant not in self.orchestrator.active_agents:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Character '{participant}' not found"
                        )
                
                # Generate conversation ID
                conversation_id = f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                
                # Initialize conversation state
                conversation_state = {
                    "id": conversation_id,
                    "participants": request.participants,
                    "topic": request.topic,
                    "location": request.location,
                    "context": request.context,
                    "status": "active",
                    "turns": [],
                    "current_speaker": request.participants[0],
                    "turn_count": 0,
                    "max_turns": request.max_turns,
                    "created_at": datetime.now(),
                    "settings": {
                        "style": request.style,
                        "allow_interruptions": request.allow_interruptions,
                        "include_internal_thoughts": request.include_internal_thoughts,
                        "turn_timeout_seconds": request.turn_timeout_seconds
                    }
                }
                
                self.active_conversations[conversation_id] = conversation_state
                
                # Start conversation processing
                asyncio.create_task(self._process_conversation_async(conversation_id))
                
                # Create response
                response = ConversationResponse(
                    conversation_id=conversation_id,
                    participants=request.participants,
                    topic=request.topic,
                    status="active",
                    created_at=datetime.now()
                )
                
                return response
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"++ ERROR creating conversation: {str(e)} ++")
                raise HTTPException(status_code=500, detail="Internal server error")
        
        
        @app.websocket("/api/v1/interactions/{interaction_id}/stream")
        async def interaction_websocket(websocket: WebSocket, interaction_id: str):
            """
            WebSocket endpoint for real-time interaction updates.
            
            **Story Implementation**: Real-time interaction monitoring
            """
            try:
                if interaction_id not in self.active_interactions:
                    await websocket.close(code=4004, reason="Interaction not found")
                    return
                
                await self.websocket_manager.connect(websocket, interaction_id)
                
                try:
                    while True:
                        # Keep connection alive and handle client messages
                        data = await websocket.receive_text()
                        message = json.loads(data)
                        
                        # Handle intervention requests if allowed
                        if message.get("type") == "intervention":
                            await self._handle_interaction_intervention(interaction_id, message)
                        
                except WebSocketDisconnect:
                    pass
                finally:
                    self.websocket_manager.disconnect(websocket, interaction_id)
                    
            except Exception as e:
                logger.error(f"++ ERROR in interaction websocket: {str(e)} ++")
                await websocket.close(code=4000, reason="Internal error")
    
    
    async def _process_interaction_async(self, interaction_id: str):
        """Process interaction asynchronously with real-time updates."""
        try:
            state = self.active_interactions[interaction_id]
            context = state["context"]
            
            # Update status
            state["status"] = "processing"
            state["started_at"] = datetime.now()
            
            # Broadcast status update
            await self._broadcast_interaction_update(interaction_id, {
                "type": "status_update",
                "status": "processing",
                "message": "Interaction processing started"
            })
            
            # Process through character interaction processor
            if self.orchestrator.character_processor:
                result = await self.orchestrator.character_processor.process_character_interaction(
                    context, context.participants
                )
                
                # Update state based on results
                if result.success:
                    state["status"] = "completed"
                    state["completed_at"] = datetime.now()
                    state["success_level"] = 0.8  # Mock success level
                    state["phases_completed"] = 4  # Mock phases
                    
                    # Broadcast completion
                    await self._broadcast_interaction_update(interaction_id, {
                        "type": "interaction_complete",
                        "status": "completed",
                        "success_level": 0.8,
                        "phases_completed": 4,
                        "message": "Interaction completed successfully"
                    })
                else:
                    state["status"] = "failed"
                    state["error"] = result.message
                    
                    # Broadcast failure
                    await self._broadcast_interaction_update(interaction_id, {
                        "type": "interaction_failed",
                        "status": "failed",
                        "error": result.message
                    })
            
        except Exception as e:
            logger.error(f"++ ERROR processing interaction {interaction_id}: {str(e)} ++")
            state = self.active_interactions.get(interaction_id)
            if state:
                state["status"] = "error"
                state["error"] = str(e)
    
    
    async def _process_conversation_async(self, conversation_id: str):
        """Process conversation with turn management."""
        try:
            state = self.active_conversations[conversation_id]
            
            # Generate conversation turns (mock implementation)
            for turn_num in range(min(10, state["max_turns"])):  # Limit for demo
                if state["status"] != "active":
                    break
                
                current_speaker = state["participants"][turn_num % len(state["participants"])]
                
                # Generate turn content (mock)
                turn = ConversationTurn(
                    turn_id=f"turn_{turn_num:03d}",
                    speaker_id=current_speaker,
                    content=f"Turn {turn_num + 1} from {current_speaker} about {state['topic']}",
                    timestamp=datetime.now(),
                    turn_number=turn_num + 1
                )
                
                state["turns"].append(turn)
                state["turn_count"] += 1
                
                # Small delay between turns
                await asyncio.sleep(2)
            
            # Mark conversation complete
            state["status"] = "completed"
            state["completed_at"] = datetime.now()
            
        except Exception as e:
            logger.error(f"++ ERROR processing conversation {conversation_id}: {str(e)} ++")
            state = self.active_conversations.get(conversation_id)
            if state:
                state["status"] = "error"
                state["error"] = str(e)
    
    
    async def _create_interaction_response(self, interaction_id: str, state: Dict[str, Any]) -> InteractionResponse:
        """Create interaction response from state."""
        context = state["context"]
        
        return InteractionResponse(
            interaction_id=interaction_id,
            participants=context.participants,
            interaction_type=context.interaction_type.value,
            status=state["status"],
            priority=context.priority.value,
            topic=context.metadata.get("topic", ""),
            location=context.location,
            social_context=context.metadata.get("social_context", "casual"),
            phases_completed=state.get("phases_completed", 0),
            estimated_duration_seconds=context.metadata.get("duration_minutes", 30) * 60,
            actual_duration_seconds=self._calculate_duration(state),
            current_phase=state.get("current_phase"),
            success_level=state.get("success_level"),
            satisfaction_levels=state.get("satisfaction_levels", {}),
            relationship_changes=state.get("relationship_changes", 0),
            memories_formed=state.get("memories_formed", 0),
            significant_events=state.get("significant_events", 0),
            created_at=state["created_at"],
            started_at=state.get("started_at"),
            completed_at=state.get("completed_at"),
            websocket_url=f"/api/v1/interactions/{interaction_id}/stream" if context.metadata.get("real_time_updates") else None,
            live_updates=context.metadata.get("real_time_updates", False)
        )
    
    
    def _calculate_duration(self, state: Dict[str, Any]) -> Optional[int]:
        """Calculate actual interaction duration."""
        if "started_at" in state:
            end_time = state.get("completed_at", datetime.now())
            return int((end_time - state["started_at"]).total_seconds())
        return None
    
    
    async def _broadcast_interaction_update(self, interaction_id: str, data: Dict[str, Any]):
        """Broadcast update to interaction websocket clients."""
        await self.websocket_manager.broadcast_to_interaction(interaction_id, data)
    
    
    async def _handle_interaction_intervention(self, interaction_id: str, message: Dict[str, Any]):
        """Handle user intervention in ongoing interaction."""
        try:
            state = self.active_interactions.get(interaction_id)
            if not state:
                return
            
            # Check if intervention is allowed
            if not state["context"].metadata.get("intervention_allowed", False):
                return
            
            # Process intervention based on type
            intervention_type = message.get("intervention_type")
            if intervention_type == "pause":
                state["status"] = "paused"
                await self._broadcast_interaction_update(interaction_id, {
                    "type": "intervention",
                    "action": "paused",
                    "message": "Interaction paused by user"
                })
            elif intervention_type == "resume":
                state["status"] = "processing"
                await self._broadcast_interaction_update(interaction_id, {
                    "type": "intervention", 
                    "action": "resumed",
                    "message": "Interaction resumed by user"
                })
            elif intervention_type == "modify_context":
                # Allow context modifications during interaction
                context_updates = message.get("context_updates", {})
                state["context"].metadata.update(context_updates)
                await self._broadcast_interaction_update(interaction_id, {
                    "type": "intervention",
                    "action": "context_modified",
                    "updates": context_updates
                })
            
        except Exception as e:
            logger.error(f"++ ERROR handling intervention for {interaction_id}: {str(e)} ++")


# Factory function for creating interaction API
def create_interaction_api(orchestrator: SystemOrchestrator) -> InteractionAPI:
    """Create and configure interaction API instance."""
    return InteractionAPI(orchestrator)


# ++ BLESSED EXPORTS SANCTIFIED BY THE OMNISSIAH ++
__all__ = ['InteractionAPI', 'InteractionRequest', 'ConversationRequest', 
           'InteractionResponse', 'ConversationResponse', 'create_interaction_api']