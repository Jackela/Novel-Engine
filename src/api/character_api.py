#!/usr/bin/env python3
"""
Character API.

API endpoints for character creation, customization, and management.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from src.core.system_orchestrator import SystemOrchestrator
from src.core.data_models import CharacterState, EmotionalState
from src.templates.character_template_manager import CharacterArchetype

logger = logging.getLogger(__name__)


class CharacterCreationRequest(BaseModel):
    """Request model for character creation."""
    agent_id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    background_summary: str = Field("", max_length=1000)
    personality_traits: str = Field("", max_length=500)
    archetype: Optional[CharacterArchetype] = None
    current_mood: int = Field(5, ge=1, le=10)
    dominant_emotion: str = "neutral"
    energy_level: int = Field(5, ge=1, le=10)
    stress_level: int = Field(5, ge=1, le=10)
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: str = ""
    inventory: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('agent_id')
    def validate_agent_id(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Agent ID must be alphanumeric with hyphens or underscores.')
        return v.lower()
    
    @validator('skills')
    def validate_skills(cls, v):
        for skill, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f'Skill {skill} must be between 0.0 and 1.0.')
        return v

class CharacterUpdateRequest(BaseModel):
    """Request model for character updates."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    background_summary: Optional[str] = Field(None, max_length=1000)
    personality_traits: Optional[str] = Field(None, max_length=500)
    skills: Optional[Dict[str, float]] = None

class CharacterResponse(BaseModel):
    """Response model for character data."""
    agent_id: str
    name: str
    current_status: str
    created_at: datetime
    last_updated: datetime

class CharacterListResponse(BaseModel):
    """Response model for character listings."""
    characters: List[CharacterResponse]

class CharacterAPI:
    """API for character creation, customization, and management."""
    
    def __init__(self, orchestrator: SystemOrchestrator):
        """Initializes the character API."""
        self.orchestrator = orchestrator
        self.app = FastAPI(title="Character API")
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._setup_routes()
        logger.info("Character API initialized.")
    
    def _setup_routes(self):
        """Sets up API routes."""
        
        @self.app.post("/api/v1/characters", response_model=dict)
        async def create_character(request: CharacterCreationRequest):
            """Creates a new character."""
            try:
                emotional_state = EmotionalState(
                    current_mood=request.current_mood,
                    dominant_emotion=request.dominant_emotion,
                )
                character_state = CharacterState(
                    agent_id=request.agent_id,
                    name=request.name,
                    background_summary=request.background_summary,
                    personality_traits=request.personality_traits,
                    emotional_state=emotional_state,
                    skills=request.skills,
                )
                
                result = await self.orchestrator.create_agent_context(
                    request.agent_id, character_state
                )
                
                if result.success:
                    return {"message": "Character created successfully."}
                else:
                    raise HTTPException(status_code=400, detail=result.message)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            except Exception as e:
                logger.error(f"Error creating character: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

def create_character_api(orchestrator: SystemOrchestrator) -> CharacterAPI:
    """Creates and configures a character API instance."""
    return CharacterAPI(orchestrator)

__all__ = ['CharacterAPI', 'create_character_api']