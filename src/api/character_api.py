#!/usr/bin/env python3
"""
Character API.

API endpoints for character creation, customization, and management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field, field_validator

from src.core.data_models import CharacterState, EmotionalState
from src.core.system_orchestrator import SystemOrchestrator
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

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v):
        """
        Validate agent ID format.

        Args:
            v: The agent ID value to validate

        Returns:
            Lowercase version of the valid agent ID

        Raises:
            ValueError: If agent ID contains invalid characters
        """
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Agent ID must be alphanumeric with hyphens or underscores."
            )
        return v.lower()

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v):
        """
        Validate skill values are within acceptable range.

        Args:
            v: Dictionary of skill names to values

        Returns:
            Validated skills dictionary

        Raises:
            ValueError: If any skill value is outside the 0.0-1.0 range
        """
        for skill, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"Skill {skill} must be between 0.0 and 1.0.")
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

    def __init__(self, orchestrator: Optional[SystemOrchestrator]):
        """Initializes the character API."""
        self.orchestrator = orchestrator
        logger.info("Character API initialized.")

    def set_orchestrator(self, orchestrator: SystemOrchestrator):
        """Set the orchestrator after initialization."""
        self.orchestrator = orchestrator
        logger.info("Character API orchestrator set.")

    def setup_routes(self, app: FastAPI):
        """Sets up API routes."""

        @app.post("/api/v1/characters", response_model=dict)
        async def create_character(request: CharacterCreationRequest):
            """Creates a new character."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503,
                    detail="System not ready. Please try again.",
                )

            try:
                # Convert string to EmotionalState enum
                emotional_state = (
                    EmotionalState.CALM
                )  # Default emotional state
                if hasattr(EmotionalState, request.dominant_emotion.upper()):
                    emotional_state = getattr(
                        EmotionalState, request.dominant_emotion.upper()
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
                    return {
                        "message": "Character created successfully.",
                        "agent_id": request.agent_id,
                        "name": request.name,
                        "created_at": datetime.now().isoformat(),
                    }
                else:
                    error_message = (
                        result.error.message
                        if result.error
                        else "Unknown error"
                    )
                    raise HTTPException(status_code=400, detail=error_message)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            except Exception as e:
                logger.error(f"Error creating character: {e}")
                raise HTTPException(
                    status_code=500, detail="Internal server error."
                )

        @app.get("/api/v1/characters", response_model=CharacterListResponse)
        async def list_characters():
            """List all characters."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503,
                    detail="System not ready. Please try again.",
                )

            try:
                # Get active agents from orchestrator
                active_agents = getattr(self.orchestrator, "active_agents", {})
                characters = []

                for agent_id, last_activity in active_agents.items():
                    characters.append(
                        CharacterResponse(
                            agent_id=agent_id,
                            name=agent_id,  # In the future, get actual name from database
                            current_status="active",
                            created_at=last_activity,
                            last_updated=last_activity,
                        )
                    )

                return CharacterListResponse(characters=characters)
            except Exception as e:
                logger.error(f"Error listing characters: {e}")
                raise HTTPException(
                    status_code=500, detail="Internal server error."
                )

        @app.get("/api/v1/characters/{character_id}", response_model=dict)
        async def get_character(
            character_id: str = Path(..., description="Character ID")
        ):
            """Get detailed character information."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503,
                    detail="System not ready. Please try again.",
                )

            try:
                # Check if character exists in active agents
                active_agents = getattr(self.orchestrator, "active_agents", {})
                if character_id not in active_agents:
                    raise HTTPException(
                        status_code=404, detail="Character not found"
                    )

                # Get character information from orchestrator
                # For now, return basic information
                return {
                    "agent_id": character_id,
                    "name": character_id,
                    "current_status": "active",
                    "last_activity": active_agents[character_id].isoformat(),
                    "created_at": active_agents[character_id].isoformat(),
                    "metadata": {"active": True, "system_managed": True},
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting character {character_id}: {e}")
                raise HTTPException(
                    status_code=500, detail="Internal server error."
                )

        @app.put("/api/v1/characters/{character_id}", response_model=dict)
        async def update_character(
            character_id: str, request: CharacterUpdateRequest
        ):
            """Update character information."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503,
                    detail="System not ready. Please try again.",
                )

            try:
                # Check if character exists
                active_agents = getattr(self.orchestrator, "active_agents", {})
                if character_id not in active_agents:
                    raise HTTPException(
                        status_code=404, detail="Character not found"
                    )

                # For now, just acknowledge the update
                # In the future, this would update the character state in the
                # database
                updates = {}
                if request.name:
                    updates["name"] = request.name
                if request.background_summary:
                    updates["background_summary"] = request.background_summary
                if request.personality_traits:
                    updates["personality_traits"] = request.personality_traits
                if request.skills:
                    updates["skills"] = request.skills

                return {
                    "message": "Character updated successfully.",
                    "agent_id": character_id,
                    "updates": updates,
                    "updated_at": datetime.now().isoformat(),
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error updating character {character_id}: {e}")
                raise HTTPException(
                    status_code=500, detail="Internal server error."
                )


def create_character_api(
    orchestrator: Optional[SystemOrchestrator],
) -> CharacterAPI:
    """Creates and configures a character API instance."""
    return CharacterAPI(orchestrator)


__all__ = ["CharacterAPI", "create_character_api"]
