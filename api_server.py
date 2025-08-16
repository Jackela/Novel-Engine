#!/usr/bin/env python3
"""
FastAPI Web Server for the Interactive Story Engine.

This module implements a FastAPI web server that provides RESTful API endpoints
for the story generation system.
"""

import logging
import uvicorn
import os
import shutil
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, field_validator, Field
from typing import List as TypingList

from config_loader import get_config
from character_factory import CharacterFactory
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent
from src.persona_agent import _validate_gemini_api_key, _make_gemini_api_request

from src.constraints_loader import (
    get_character_name_constraints,
    get_character_description_constraints,
    validate_character_name,
    validate_character_description,
)
import time
import uuid
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from src.shared_types import (
        SystemStatus, CharacterData,
    )
    SHARED_TYPES_AVAILABLE = True
    logger.info("Shared types successfully imported.")
except ImportError as e:
    SHARED_TYPES_AVAILABLE = False
    logger.warning(f"Shared types not available: {e}")

def _find_project_root(start_path: str) -> str:
    """Finds the project root directory by looking for marker files."""
    markers = ['persona_agent.py', 'director_agent.py', 'config.yaml', '.git']
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):
        if any(os.path.exists(os.path.join(current_path, marker)) for marker in markers):
            return current_path
        current_path = os.path.dirname(current_path)
    return os.path.abspath(os.getcwd())

def _get_characters_directory_path() -> str:
    """Gets the absolute path to the characters directory."""
    base_character_path = "characters"
    if not os.path.isabs(base_character_path):
        project_root = _find_project_root(os.getcwd())
        return os.path.join(project_root, base_character_path)
    return base_character_path

class HealthResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    error: str
    detail: str

class CharactersListResponse(BaseModel):
    characters: List[str]

class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)

class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler."""
    logger.info("Starting StoryForge AI API server...")
    yield
    logger.info("Shutting down StoryForge AI API server.")

app = FastAPI(
    title="StoryForge AI API",
    description="RESTful API for the StoryForge AI Interactive Story Engine.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=HealthResponse)
async def root() -> Dict[str, str]:
    """Provides a basic health check for the API."""
    return {"message": "StoryForge AI Interactive Story Engine is running!"}

@app.get("/characters", response_model=CharactersListResponse)
async def get_characters() -> CharactersListResponse:
    """Retrieves a list of available characters."""
    try:
        characters_path = _get_characters_directory_path()
        if not os.path.isdir(characters_path):
            raise HTTPException(status_code=404, detail="Characters directory not found.")
        
        characters = sorted([d for d in os.listdir(characters_path) if os.path.isdir(os.path.join(characters_path, d))])
        return CharactersListResponse(characters=characters)
    except Exception as e:
        logger.error(f"Error retrieving characters: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve characters.")

@app.post("/simulations", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Executes a character simulation."""
    start_time = time.time()
    logger.info(f"Simulation requested for: {request.character_names}")

    try:
        config = get_config()
        turns_to_execute = request.turns or config.simulation.turns
        
        character_factory = CharacterFactory()
        agents = [character_factory.create_character(name) for name in request.character_names]

        log_path = f"simulation_{uuid.uuid4().hex[:8]}.md"
        director = DirectorAgent(campaign_log_path=log_path)
        for agent in agents:
            director.register_agent(agent)

        for _ in range(turns_to_execute):
            director.run_turn()

        chronicler = ChroniclerAgent(character_names=request.character_names)
        story = chronicler.transcribe_log(log_path)
        
        os.remove(log_path)

        return SimulationResponse(
            story=story,
            participants=request.character_names,
            turns_executed=turns_to_execute,
            duration_seconds=time.time() - start_time
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Character not found: {e}")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail="Simulation execution failed.")

def run_server(host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
    """Runs the FastAPI server."""
    uvicorn.run("api_server:app", host=host, port=port, reload=debug, log_level="info")

if __name__ == "__main__":
    run_server(host="127.0.0.1", port=8000, debug=True)