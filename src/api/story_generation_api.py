#!/usr/bin/env python3
"""
Story Generation API.

API endpoints for story export, narrative generation, and content formatting.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
import uuid

from src.core.system_orchestrator import SystemOrchestrator

logger = logging.getLogger(__name__)

class StoryGenerationRequest(BaseModel):
    """Request model for story generation."""
    characters: List[str] = Field(..., min_items=1)
    title: str = Field("A Generated Story", max_length=200)

class StoryGenerationResponse(BaseModel):
    """Response model for story generation requests."""
    generation_id: str
    status: str
    message: str

class StoryGenerationAPI:
    """API for story export and narrative generation."""
    
    def __init__(self, orchestrator: SystemOrchestrator):
        """Initializes the story generation API."""
        self.orchestrator = orchestrator
        self.active_generations: Dict[str, Any] = {}
        logger.info("Story Generation API initialized.")
    
    def setup_routes(self, app: FastAPI):
        """Sets up API routes for story generation."""
        
        @app.post("/api/v1/stories/generate", response_model=StoryGenerationResponse)
        async def generate_story(request: StoryGenerationRequest, background_tasks: BackgroundTasks):
            """Generates a story from character interactions."""
            generation_id = f"story_{uuid.uuid4().hex[:8]}"
            
            self.active_generations[generation_id] = {"status": "initiated", "request": request}
            background_tasks.add_task(self._generate_story_async, generation_id)
            
            return StoryGenerationResponse(
                generation_id=generation_id,
                status="initiated",
                message="Story generation initiated."
            )

    async def _generate_story_async(self, generation_id: str):
        """Generates a story asynchronously."""
        try:
            state = self.active_generations[generation_id]
            state["status"] = "processing"
            # Simulate story generation
            await asyncio.sleep(10)
            state["status"] = "completed"
            logger.info(f"Story generation {generation_id} completed.")
        except Exception as e:
            logger.error(f"Error generating story {generation_id}: {e}")
            if generation_id in self.active_generations:
                self.active_generations[generation_id]["status"] = "failed"

def create_story_generation_api(orchestrator: SystemOrchestrator) -> StoryGenerationAPI:
    """Creates and configures a story generation API instance."""
    return StoryGenerationAPI(orchestrator)

__all__ = ['StoryGenerationAPI', 'create_story_generation_api']