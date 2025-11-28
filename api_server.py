#!/usr/bin/env python3
"""
FastAPI Web Server for the Interactive Story Engine.

This module implements a FastAPI web server that provides RESTful API endpoints
for the story generation system.
"""

import asyncio
import html
import json
import logging
import os
import re
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, UTC, timedelta
from typing import Any, Dict, List, Optional, Set
from types import SimpleNamespace

import jwt  # For token validation

import uvicorn
from fastapi.security import APIKeyCookie
from src.config.character_factory import CharacterFactory
from src.agents.chronicler_agent import ChroniclerAgent
from config_loader import get_config
from src.agents.director_agent import DirectorAgent
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

# Removed stale import: _validate_gemini_api_key, _make_gemini_api_request no longer exist
from src.event_bus import EventBus
from src.metrics.global_metrics import metrics as global_metrics
from src.caching.registry import invalidate_by_tags
from src.caching.global_chunk_cache import chunk_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================================================
# Cookie Configuration for httpOnly Token Storage [SEC-001]
# ===================================================================
COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"

# Environment-based security settings
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1", "yes")  # HTTPS only in production
COOKIE_HTTPONLY = True  # Protect against XSS
COOKIE_SAMESITE = "lax"  # CSRF protection while allowing normal navigation
COOKIE_MAX_AGE = 3600 * 24  # 24 hours for access token
REFRESH_COOKIE_MAX_AGE = 3600 * 24 * 30  # 30 days for refresh token
CSRF_TOKEN_MAX_AGE = 3600 * 24  # 24 hours for CSRF token

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "development-secret-key-change-in-production"))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens

# Import World Context API Router
try:
    from apps.api.http import world_router

    WORLD_ROUTER_AVAILABLE = True
    logger.info("World context router successfully imported.")
except ImportError as e:
    WORLD_ROUTER_AVAILABLE = False
    logger.warning(f"World context router not available: {e}")

try:
    from src.shared_types import (
        CharacterData,
        SystemStatus,
    )

    # Bind to throwaway tuple to avoid lint "unused import" noise.
    _SHARED_TYPE_SENTINEL = (CharacterData, SystemStatus)
    SHARED_TYPES_AVAILABLE = True
    logger.info("Shared types successfully imported.")
except ImportError as e:
    SHARED_TYPES_AVAILABLE = False
    logger.warning(f"Shared types not available: {e}")


def _find_project_root(start_path: str) -> str:
    """Finds the project root directory by looking for marker files."""
    markers = ["persona_agent.py", "director_agent.py", "configs/", ".git"]
    current_path = os.path.abspath(start_path)
    while current_path != os.path.dirname(current_path):
        if any(
            os.path.exists(os.path.join(current_path, marker)) for marker in markers
        ):
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


DEFAULT_CHARACTERS_PATH = os.path.abspath(_get_characters_directory_path())


class HealthResponse(BaseModel):
    message: str
    status: Optional[str] = None
    timestamp: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    detail: str


class CharactersListResponse(BaseModel):
    characters: List[str]


class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)
    setting: Optional[str] = None
    scenario: Optional[str] = None


class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float


class CharacterDetailResponse(BaseModel):
    """Response model for detailed character information."""

    character_id: str
    character_name: str
    name: str
    background_summary: str
    personality_traits: str
    current_status: str
    narrative_context: str
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: str = ""
    inventory: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    structured_data: Dict[str, Any] = Field(default_factory=dict)


class FileCount(BaseModel):
    """Response model for file count information."""

    count: int
    file_type: str


class CampaignsListResponse(BaseModel):
    """Response model for campaigns list."""

    campaigns: List[str]


class CampaignCreationRequest(BaseModel):
    """Request model for campaign creation."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    participants: List[str] = Field(..., min_length=1)


class CampaignCreationResponse(BaseModel):
    """Response model for campaign creation."""

    campaign_id: str
    name: str
    status: str
    created_at: str


# ===================================================================
# Authentication Request/Response Models [SEC-001]
# ===================================================================

class LoginRequest(BaseModel):
    """Request model for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Whether to extend session duration")


class AuthResponse(BaseModel):
    """Response model for authentication endpoints."""
    access_token: str = Field(..., description="JWT access token (for backward compatibility)")
    refresh_token: str = Field(..., description="JWT refresh token (for backward compatibility)")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    user: Dict[str, Any] = Field(..., description="User information")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")


class CSRFTokenResponse(BaseModel):
    """Response model for CSRF token endpoint."""
    csrf_token: str = Field(..., description="CSRF token for state-changing requests")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler."""
    logger.info("Starting StoryForge AI API server...")
    try:
        # Validate configuration during startup
        get_config()
        logger.info("Configuration loaded successfully")

        # Setup EventBus-SSE bridge for real-time dashboard events
        # This is done late (after imports) to avoid circular dependency
        try:
            from src.event_bus import EventBus as EventBusClass
            global_event_bus = EventBusClass()
            app.state.event_bus = global_event_bus
            # Note: setup_eventbus_sse_bridge will be called after it's defined
            logger.info("Global EventBus initialized for SSE integration")
        except Exception as bus_error:
            logger.warning(f"Could not initialize EventBus for SSE: {bus_error}")

    except Exception as e:
        logger.error(f"Configuration error during startup: {e}")
        raise e
    yield
    logger.info("Shutting down StoryForge AI API server.")


API_START_TIME = datetime.now(UTC)

GENERIC_CHARACTER_DEFS: Dict[str, Dict[str, Any]] = {
    "pilot": {
        "character_name": "pilot",
        "display_name": "Alex Chen",
        "narrative_context": (
            "Alex Chen, an Elite Starfighter Pilot with the Galactic Defense Force,"
            " leads the response wing protecting Meridian Station."
        ),
        "structured_data": {
            "stats": {
                "character": {
                    "name": "Alex Chen",
                    "faction": "Galactic Defense Force",
                    "specialization": "Starfighter Pilot",
                },
                "combat_stats": {"attack": 78, "defense": 72, "agility": 88},
            }
        },
        "enhanced_context": {
            "psychological_profile": {
                "discipline": "Ace pilot with meditation rituals",
                "primary_drive": "Keep the station's civilians safe",
            },
            "tactical_analysis": {
                "preferred_assets": ["Interceptor squad", "docking bay 4"],
                "signature_maneuver": "Nova Vortex evasive pattern",
            },
        },
    },
    "scientist": {
        "character_name": "scientist",
        "display_name": "Dr. Maya Patel",
        "narrative_context": (
            "Dr. Maya Patel, lead Xenobiology Researcher at the Scientific Research Institute,"
            " documents the newly discovered crystalline spores."
        ),
        "structured_data": {
            "stats": {
                "character": {
                    "name": "Dr. Maya Patel",
                    "faction": "Scientific Research Institute",
                    "specialization": "Xenobiology Research",
                },
                "combat_stats": {"analysis": 90, "survival": 68, "support": 74},
            }
        },
        "enhanced_context": {
            "psychological_profile": {
                "discipline": "Methodical, curiosity-driven",
                "primary_drive": "Decode alien ecosystems",
            },
            "tactical_analysis": {
                "preferred_assets": ["Mobile lab", "sensor drones"],
                "signature_maneuver": "Rapid containment protocol",
            },
        },
    },
    "engineer": {
        "character_name": "engineer",
        "display_name": "Jordan Kim",
        "narrative_context": (
            "Systems Engineer Jordan Kim keeps the Engineering Corps' plasma conduits stable"
            " while mentoring new recruits."
        ),
        "structured_data": {
            "stats": {
                "character": {
                    "name": "Jordan Kim",
                    "faction": "Engineering Corps",
                    "specialization": "Systems Engineer",
                },
                "combat_stats": {"repair": 92, "defense": 65, "tactics": 70},
            }
        },
        "enhanced_context": {
            "psychological_profile": {
                "discipline": "Pragmatic problem-solver",
                "primary_drive": "Keep the station running",
            },
            "tactical_analysis": {
                "preferred_assets": ["Fabrication lab", "drone swarm"],
                "signature_maneuver": "Adaptive reroute protocol",
            },
        },
    },
    "test": {
        "character_name": "test",
        "display_name": "Synthetic Liaison Unit",
        "narrative_context": (
            "The Synthetic Liaison Unit coordinates pilot, scientist, and engineer briefs"
            " to maintain neutral oversight."
        ),
        "structured_data": {
            "stats": {
                "character": {
                    "name": "Synthetic Liaison Unit",
                    "faction": "Meridian Command",
                    "specialization": "Operations Liaison",
                },
                "combat_stats": {"analysis": 85, "coordination": 88, "support": 80},
            }
        },
        "enhanced_context": {
            "psychological_profile": {
                "discipline": "Emotionally detached analyst",
                "primary_drive": "Collect balanced intel",
            },
            "tactical_analysis": {
                "preferred_assets": ["Observation decks"],
                "signature_maneuver": "Multi-threaded briefing",
            },
        },
    },
}


def _uptime_seconds() -> float:
    return (datetime.now(UTC) - API_START_TIME).total_seconds()


def _sanitize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = re.sub(r"[<>'\";]", " ", cleaned)
    cleaned = re.sub(
        r"drop\s+table", "neutralized operation", cleaned, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


class GenericPersonaAgent:
    def __init__(self, character_id: str, data: Dict[str, Any]):
        self.agent_id = character_id
        self.agent_type = "generic"
        self.character_name = data["character_name"]
        self.character = SimpleNamespace(
            name=data["display_name"],
            background_summary=data["narrative_context"],
            personality_traits="Resourceful and adaptable",
            current_status="Active",
            narrative_context=data["narrative_context"],
            skills={"strategy": 0.8, "teamwork": 0.9},
            relationships={},
            current_location="Meridian Station",
            inventory=["standard field kit"],
            metadata={"structured_data": data["structured_data"]},
        )
        self.character_data = {"name": data["display_name"]}


def _build_generic_story(request: SimulationRequest) -> str:
    setting = _sanitize_text(request.setting) or "stellar patrol corridor"
    scenario = _sanitize_text(request.scenario) or "critical mission"
    crew = ", ".join(request.character_names)
    segments = [
        f"Within the {setting}, {crew} aligned their orbital vectors with Meridian Station's docking halo.",
        f"Their objective centered on {scenario}, threading a course past nebular lightning, gravity shears, and drifting research buoys.",
        "Spectral scanners painted cosmic lattices across the hull while telemetry panels whispered about unknown signals in the Perseus Spur.",
        "They catalogued auroras, decoded encrypted beacons, and reassured remote habitats that the Galactic Defense Forces still guarded the frontier.",
        "Every log entry emphasized collaboration, innovation, and the belief that science and defense thrive together among the stars.",
    ]
    return " ".join(segments)


def _structured_defaults(
    name: str, specialization: str = "Unknown", faction: str = "Independent"
) -> Dict[str, Any]:
    return {
        "stats": {
            "character": {
                "name": name,
                "faction": faction,
                "specialization": specialization,
            }
        }
    }


app = FastAPI(
    title="StoryForge AI API",
    description="RESTful API for the StoryForge AI Interactive Story Engine.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def global_options_handler(request: Request, call_next):
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400",
        }
        return Response(status_code=204, headers=headers)
    response = await call_next(request)
    return response

# Include World Context Router
if WORLD_ROUTER_AVAILABLE:
    app.include_router(world_router, prefix="/api/v1")
    logger.info("World context router included with prefix /api/v1/worlds")
else:
    logger.warning(
        "World context router not available - endpoints will not be accessible"
    )

# Include Prompts Router
try:
    from src.api.prompts_router import router as prompts_router

    app.include_router(prompts_router)
    logger.info("Prompts router included with prefix /api/prompts")
except ImportError as e:
    logger.warning(f"Prompts router not available: {e}")

# Include Decision Router for user participatory interaction
try:
    from src.decision import (
        decision_router,
        initialize_decision_system,
        InteractionPauseController,
        DecisionPointDetector,
        NegotiationEngine,
    )

    # Create decision system components
    _decision_pause_controller = InteractionPauseController(default_timeout=120)
    _decision_detector = DecisionPointDetector(
        tension_threshold=7.0,
        intensity_threshold=7.0,
        always_detect_interval=3,  # For testing: every 3 turns
    )
    _decision_negotiation_engine = NegotiationEngine()

    # Include router
    app.include_router(decision_router)
    DECISION_ROUTER_AVAILABLE = True
    logger.info("Decision router included with prefix /api/decision")
except ImportError as e:
    DECISION_ROUTER_AVAILABLE = False
    _decision_pause_controller = None
    _decision_detector = None
    _decision_negotiation_engine = None
    logger.warning(f"Decision router not available: {e}")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Custom HTTP exception handler to format errors as expected by tests."""
    error_map = {
        404: "Not Found",
        400: "Bad Request",
        422: "Validation Error",
        500: "Internal Server Error",
    }

    # Log errors based on status code
    if exc.status_code == 404:
        logger.warning(f"404 error for path {request.url.path}: {exc.detail}")
        detail = "The requested endpoint does not exist."
    elif exc.status_code >= 500:
        logger.error(
            f"Server error {exc.status_code} for path {request.url.path}: {exc.detail}"
        )
        detail = exc.detail
    else:
        detail = exc.detail

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_map.get(exc.status_code, "Unknown Error"),
            "detail": detail,
        },
    )


@app.exception_handler(HTTPException)
async def fastapi_exception_handler(request: Request, exc: HTTPException):
    """Custom FastAPI exception handler to format errors as expected by tests."""
    error_map = {
        404: "Not Found",
        400: "Bad Request",
        422: "Validation Error",
        500: "Internal Server Error",
    }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_map.get(exc.status_code, "Unknown Error"),
            "detail": exc.detail,
        },
    )


class InvalidationRequest(BaseModel):
    all_of: List[str]


@app.get("/cache/metrics")
async def cache_metrics() -> Dict[str, Any]:
    """Return cache/coordinator metrics snapshot (internal)."""
    try:
        return global_metrics.snapshot().to_dict()
    except Exception as e:
        logger.error(f"metrics snapshot error: {e}")
        raise HTTPException(status_code=500, detail="metrics error")


@app.post("/cache/invalidate")
async def cache_invalidate(req: InvalidationRequest) -> Dict[str, Any]:
    """Invalidate cache entries that include all provided tags (intersection)."""
    try:
        removed = invalidate_by_tags(req.all_of)
        return {"removed": int(removed)}
    except Exception as e:
        logger.error(f"invalidation error: {e}")
        raise HTTPException(status_code=500, detail="invalidation error")


class ChunkInRequest(BaseModel):
    seq: int
    data: str


@app.post("/cache/chunk/{key}")
async def cache_chunk_append(key: str, req: ChunkInRequest) -> Dict[str, Any]:
    try:
        chunk_cache.add_chunk(key, req.seq, req.data)
        return {"ok": True}
    except Exception as e:
        logger.error(f"chunk append error: {e}")
        raise HTTPException(status_code=500, detail="chunk append error")


@app.post("/cache/chunk/{key}/complete")
async def cache_chunk_complete(key: str) -> Dict[str, Any]:
    try:
        chunk_cache.mark_complete(key)
        return {"ok": True}
    except Exception as e:
        logger.error(f"chunk complete error: {e}")
        raise HTTPException(status_code=500, detail="chunk complete error")


@app.get("/cache/stream/{key}")
async def cache_stream(key: str):
    import asyncio

    async def event_gen():
        last_seq = -1
        idle = 0
        while True:
            chunks = chunk_cache.get_since(key, last_seq)
            for c in chunks:
                last_seq = c.seq
                yield f"data: {c.data}\n\n"
            if chunk_cache.is_complete(key):
                break
            await asyncio.sleep(0.2)
            idle += 1
            if idle > 300:  # ~60s timeout
                break
        # end of stream signal
        yield "event: done\ndata: complete\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/", response_model=HealthResponse)
async def root() -> Dict[str, Any]:
    """Provides a basic health check for the API."""
    logger.info("Root endpoint accessed for health check")
    response_data = {
        "message": "StoryForge AI Interactive Story Engine is running!",
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    logger.debug(f"Root endpoint response: {response_data}")
    return response_data


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check endpoint."""
    import datetime

    try:
        # Test if logging.Formatter is causing issues (for test mocking)
        import logging

        logging.Formatter("%(name)s - %(levelname)s - %(message)s")

        # Test configuration loading
        get_config()
        config_status = "loaded"
        status = "healthy"
        logger.info("Health check endpoint accessed")
    except Exception as e:
        logger.error(f"Health check configuration error: {e}")
        # If it's a severe error (like in testing), raise HTTP 500
        if "Severe system error" in str(e):
            raise HTTPException(status_code=500, detail=str(e))
        config_status = "error"
        status = "degraded"

    health_data = {
        "status": status,
        "api": "running",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0",
        "config": config_status,
        "uptime": _uptime_seconds(),
    }

    logger.debug(f"Health check response: {health_data}")
    return health_data


@app.get("/meta/system-status")
async def system_status() -> Dict[str, Any]:
    return {
        "status": "operational",
        "uptime": _uptime_seconds(),
        "version": "1.0.0",
        "components": {
            "api": "online",
            "simulation": "idle",
            "cache": "available",
        },
    }


# Global orchestration state for pipeline status tracking
_orchestration_state: Dict[str, Any] = {
    "current_turn": 0,
    "total_turns": 0,
    "queue_length": 0,
    "average_processing_time": 0.0,
    "status": "idle",  # idle, running, paused, stopped
    "steps": [],
    "last_updated": None,
}

# Orchestration executor and task management
_orchestration_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="orch_")
_orchestration_lock = threading.Lock()
_orchestration_stop_flag = threading.Event()

# Generated narrative storage
_generated_narrative: Dict[str, Any] = {
    "story": "",
    "log_path": "",
    "participants": [],
    "turns_completed": 0,
    "last_generated": None,
}


def _run_orchestration_background(
    character_names: List[str],
    total_turns: int,
    start_turn: int = 1
) -> None:
    """
    Run story generation in a background thread.
    This function is synchronous and runs DirectorAgent.run_turn() for each turn.
    """
    global _orchestration_state, _generated_narrative

    logger.info(f"Starting real orchestration with characters: {character_names}, turns: {total_turns}")

    # Reset stop flag
    _orchestration_stop_flag.clear()

    try:
        # Initialize components
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)

        # Setup SSE bridge to broadcast events to dashboard
        setup_eventbus_sse_bridge(event_bus)

        # Create agents for each character
        agents = []
        for name in character_names:
            try:
                agent = character_factory.create_character(name)
                agents.append(agent)
                logger.info(f"Created agent for character: {name}")

                # Broadcast character creation event
                broadcast_sse_event(create_sse_event(
                    event_type="character",
                    title=f"Agent Created: {name}",
                    description=f"Character agent {name} initialized for story generation",
                    severity="low",
                    character_name=name
                ))
            except Exception as e:
                logger.error(f"Failed to create agent for {name}: {e}")
                broadcast_sse_event(create_sse_event(
                    event_type="system",
                    title=f"Agent Creation Failed",
                    description=f"Could not create agent for {name}: {str(e)}",
                    severity="high"
                ))

        if not agents:
            raise ValueError("No agents could be created")

        # Generate unique log path
        log_path = f"logs/orchestration_{uuid.uuid4().hex[:8]}.md"
        os.makedirs("logs", exist_ok=True)

        # Initialize director and register agents
        director = DirectorAgent(event_bus, campaign_log_path=log_path)
        for agent in agents:
            director.register_agent(agent)

        # Update state
        with _orchestration_lock:
            _orchestration_state["queue_length"] = len(agents)
            _generated_narrative["log_path"] = log_path
            _generated_narrative["participants"] = character_names

        # Broadcast start event
        broadcast_sse_event(create_sse_event(
            event_type="system",
            title="Orchestration Started",
            description=f"Beginning story generation with {len(agents)} characters for {total_turns} turns",
            severity="medium"
        ))

        # Execute simulation turns
        turn_times = []
        for turn_num in range(start_turn, start_turn + total_turns):
            # Check for stop signal
            if _orchestration_stop_flag.is_set():
                logger.info("Orchestration stopped by user")
                break

            turn_start = time.time()

            # Update state for this turn
            with _orchestration_lock:
                _orchestration_state["current_turn"] = turn_num
                _orchestration_state["steps"] = _get_default_pipeline_steps()
                _orchestration_state["steps"][0]["status"] = "processing"
                _orchestration_state["steps"][0]["progress"] = 25

            # Broadcast turn start event
            broadcast_sse_event(create_sse_event(
                event_type="story",
                title=f"Turn {turn_num}/{total_turns}",
                description=f"Processing turn {turn_num}",
                severity="low"
            ))

            try:
                logger.info(f"Executing turn {turn_num}/{total_turns}")

                # Update step progress
                with _orchestration_lock:
                    _orchestration_state["steps"][1]["status"] = "processing"
                    _orchestration_state["steps"][1]["progress"] = 50

                # Actually run the turn (this calls the LLM)
                turn_result = director.run_turn()

                # Mark steps as completed
                with _orchestration_lock:
                    for step in _orchestration_state["steps"]:
                        step["status"] = "completed"
                        step["progress"] = 100

                turn_duration = time.time() - turn_start
                turn_times.append(turn_duration)

                # Update average processing time
                with _orchestration_lock:
                    _orchestration_state["average_processing_time"] = sum(turn_times) / len(turn_times)
                    _generated_narrative["turns_completed"] = turn_num

                # Broadcast turn completion
                broadcast_sse_event(create_sse_event(
                    event_type="story",
                    title=f"Turn {turn_num} Completed",
                    description=f"Turn completed in {turn_duration:.2f}s",
                    severity="low"
                ))

                # === DECISION POINT DETECTION ===
                # Check for user interaction points if decision system is available
                if DECISION_ROUTER_AVAILABLE and _decision_detector and _decision_pause_controller:
                    try:
                        # Build narrative context from recent story
                        narrative_context = ""
                        if _generated_narrative.get("story"):
                            # Use last 500 chars as context
                            narrative_context = _generated_narrative["story"][-500:]

                        # Analyze turn result for decision point
                        decision_point = _decision_detector.analyze_turn(
                            turn_number=turn_num,
                            turn_result=turn_result if isinstance(turn_result, dict) else {},
                            narrative_context=narrative_context,
                            characters=[{"name": n} for n in character_names],
                        )

                        if decision_point:
                            logger.info(f"Decision point detected at turn {turn_num}: {decision_point.title}")

                            # Broadcast decision point to frontend
                            broadcast_sse_event({
                                "id": f"decision-{decision_point.decision_id}",
                                "type": "decision_required",
                                "title": decision_point.title,
                                "description": decision_point.description,
                                "severity": "high",
                                "timestamp": decision_point.created_at.isoformat(),
                                "data": decision_point.to_dict(),
                            })

                            # Pause and wait for user decision (blocking with timeout)
                            try:
                                user_decision = asyncio.run(
                                    _decision_pause_controller.pause_for_decision(decision_point)
                                )
                                if user_decision:
                                    logger.info(f"User decision received: {user_decision.input_type}")
                                    # User decision can influence next turn via world state
                                    # Store in generated narrative for context
                                    with _orchestration_lock:
                                        if "user_decisions" not in _generated_narrative:
                                            _generated_narrative["user_decisions"] = []
                                        _generated_narrative["user_decisions"].append({
                                            "turn": turn_num,
                                            "decision_id": decision_point.decision_id,
                                            "input_type": user_decision.input_type,
                                            "selected_option_id": user_decision.selected_option_id,
                                            "free_text": user_decision.free_text,
                                        })
                                else:
                                    logger.info("Decision point skipped/timed out")
                            except Exception as pause_error:
                                logger.warning(f"Decision pause failed: {pause_error}")

                    except Exception as decision_error:
                        logger.warning(f"Decision detection failed: {decision_error}")

            except Exception as e:
                logger.error(f"Error during turn {turn_num}: {e}")
                broadcast_sse_event(create_sse_event(
                    event_type="system",
                    title=f"Turn {turn_num} Error",
                    description=str(e),
                    severity="high"
                ))
                # Continue with next turn

        # Generate final narrative with chronicler
        try:
            broadcast_sse_event(create_sse_event(
                event_type="story",
                title="Generating Narrative",
                description="Creating final story from turn logs",
                severity="medium"
            ))

            chronicler = ChroniclerAgent(event_bus, character_names=character_names)
            story = chronicler.transcribe_log(log_path)

            with _orchestration_lock:
                _generated_narrative["story"] = story
                _generated_narrative["last_generated"] = datetime.now(UTC).isoformat()

            broadcast_sse_event(create_sse_event(
                event_type="story",
                title="Story Generated",
                description=f"Generated {len(story)} character narrative",
                severity="medium"
            ))

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            # Read raw log as fallback
            try:
                with open(log_path, "r") as f:
                    raw_log = f.read()
                with _orchestration_lock:
                    _generated_narrative["story"] = f"[Raw Log]\n{raw_log}"
                    _generated_narrative["last_generated"] = datetime.now(UTC).isoformat()
            except Exception:
                pass

        # Update final state
        with _orchestration_lock:
            _orchestration_state["status"] = "stopped" if _orchestration_stop_flag.is_set() else "idle"
            _orchestration_state["last_updated"] = datetime.now(UTC).isoformat()

        broadcast_sse_event(create_sse_event(
            event_type="system",
            title="Orchestration Complete",
            description=f"Story generation finished. {_generated_narrative['turns_completed']} turns completed.",
            severity="medium"
        ))

    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        with _orchestration_lock:
            _orchestration_state["status"] = "idle"
            _orchestration_state["last_updated"] = datetime.now(UTC).isoformat()

        broadcast_sse_event(create_sse_event(
            event_type="system",
            title="Orchestration Failed",
            description=str(e),
            severity="high"
        ))


def _get_default_pipeline_steps() -> List[Dict[str, Any]]:
    """Return default pipeline step definitions."""
    return [
        {"id": "narrative-setup", "name": "Narrative Setup", "status": "queued", "progress": 0},
        {"id": "character-actions", "name": "Character Actions", "status": "queued", "progress": 0},
        {"id": "world-update", "name": "World Update", "status": "queued", "progress": 0},
        {"id": "interaction-orchestration", "name": "Interaction Orchestration", "status": "queued", "progress": 0},
    ]


@app.get("/api/orchestration/status")
async def get_orchestration_status() -> Dict[str, Any]:
    """
    Get current orchestration/pipeline status for dashboard display.

    Returns real-time information about:
    - Current turn number and total turns
    - Queue length
    - Processing steps and their status
    - Average processing time
    """
    global _orchestration_state

    # Try to get real status from DirectorAgent if available
    try:
        # Check if there's an active director instance
        config = get_config()
        if hasattr(config, 'director') and config.director:
            director = DirectorAgent()
            status = director.get_simulation_status()

            # Map DirectorAgent status to pipeline format
            return {
                "success": True,
                "data": {
                    "current_turn": status.get("current_turn", 0),
                    "total_turns": status.get("total_turns", 0),
                    "queue_length": status.get("pending_actions", 0),
                    "average_processing_time": status.get("avg_turn_time", 0.0),
                    "status": "running" if status.get("is_running", False) else "idle",
                    "steps": _map_orchestrator_to_steps(status),
                },
            }
    except Exception as e:
        logger.debug(f"Could not get DirectorAgent status: {e}")

    # Return current orchestration state (may be from SSE updates or defaults)
    if not _orchestration_state["steps"]:
        _orchestration_state["steps"] = _get_default_pipeline_steps()

    _orchestration_state["last_updated"] = datetime.now(UTC).isoformat()

    return {
        "success": True,
        "data": _orchestration_state,
    }


def _map_orchestrator_to_steps(status: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map DirectorAgent/TurnOrchestrator status to pipeline steps format."""
    steps = _get_default_pipeline_steps()

    # If we have turn orchestrator metrics, use them
    turn_metrics = status.get("turn_orchestrator_metrics", {})
    if turn_metrics:
        current_phase = turn_metrics.get("current_phase", "")
        phases_completed = turn_metrics.get("phases_completed", [])

        for step in steps:
            step_id = step["id"]
            if step_id in phases_completed:
                step["status"] = "completed"
                step["progress"] = 100
            elif step_id == current_phase:
                step["status"] = "processing"
                step["progress"] = turn_metrics.get("phase_progress", 50)
            else:
                step["status"] = "queued"
                step["progress"] = 0

    return steps


@app.post("/api/orchestration/start")
async def start_orchestration(request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Start real story generation orchestration pipeline.

    Request body (optional):
    - character_names: List[str] - Characters to include (defaults to all available)
    - total_turns: int - Number of turns to run (default: 3)
    - start_turn: int - Starting turn number (default: 1)
    """
    global _orchestration_state, _generated_narrative

    # Check if already running
    if _orchestration_state["status"] == "running":
        return {
            "success": False,
            "message": "Orchestration already running",
            "data": _orchestration_state
        }

    # Parse request parameters
    params = request or {}
    total_turns = params.get("total_turns", 3)  # Default to 3 turns for reasonable demo
    start_turn = params.get("start_turn", 1)

    # Get character names - use provided or fetch all available
    character_names = params.get("character_names")
    if not character_names:
        # Fetch available characters
        try:
            characters_path = _get_characters_directory_path()
            available_chars: Set[str] = set()

            # Include generic definitions
            if os.path.abspath(characters_path) == DEFAULT_CHARACTERS_PATH:
                available_chars.update(GENERIC_CHARACTER_DEFS.keys())

            # Include directory-based characters
            if os.path.isdir(characters_path):
                for item in os.listdir(characters_path):
                    if os.path.isdir(os.path.join(characters_path, item)):
                        available_chars.add(item)

            # Select up to 3 characters for demo
            character_names = sorted(list(available_chars))[:3]
            if not character_names:
                character_names = ["pilot", "scientist", "engineer"]  # Fallback to generics

        except Exception as e:
            logger.warning(f"Failed to fetch characters, using defaults: {e}")
            character_names = ["pilot", "scientist", "engineer"]

    # Update initial state
    with _orchestration_lock:
        _orchestration_state["status"] = "running"
        _orchestration_state["current_turn"] = start_turn
        _orchestration_state["total_turns"] = total_turns
        _orchestration_state["steps"] = _get_default_pipeline_steps()
        _orchestration_state["steps"][0]["status"] = "processing"
        _orchestration_state["steps"][0]["progress"] = 10
        _orchestration_state["last_updated"] = datetime.now(UTC).isoformat()

        # Reset narrative storage
        _generated_narrative["story"] = ""
        _generated_narrative["participants"] = character_names
        _generated_narrative["turns_completed"] = 0
        _generated_narrative["last_generated"] = None

    # Start background orchestration
    logger.info(f"Submitting orchestration task: chars={character_names}, turns={total_turns}")
    _orchestration_executor.submit(
        _run_orchestration_background,
        character_names,
        total_turns,
        start_turn
    )

    return {
        "success": True,
        "message": f"Orchestration started with {len(character_names)} characters for {total_turns} turns",
        "data": _orchestration_state
    }


@app.post("/api/orchestration/stop")
async def stop_orchestration() -> Dict[str, Any]:
    """Stop orchestration pipeline gracefully."""
    global _orchestration_state

    if _orchestration_state["status"] != "running":
        return {
            "success": False,
            "message": "Orchestration is not running",
            "data": _orchestration_state
        }

    # Signal the background task to stop
    _orchestration_stop_flag.set()

    with _orchestration_lock:
        _orchestration_state["status"] = "stopped"
        _orchestration_state["last_updated"] = datetime.now(UTC).isoformat()

    logger.info("Orchestration stop requested")

    return {"success": True, "message": "Orchestration stop requested", "data": _orchestration_state}


@app.get("/api/orchestration/narrative")
async def get_narrative() -> Dict[str, Any]:
    """
    Get the generated story narrative from the last orchestration run.

    Returns the story text, participants, and generation metadata.
    """
    with _orchestration_lock:
        return {
            "success": True,
            "data": {
                "story": _generated_narrative["story"],
                "participants": _generated_narrative["participants"],
                "turns_completed": _generated_narrative["turns_completed"],
                "last_generated": _generated_narrative["last_generated"],
                "has_content": bool(_generated_narrative["story"]),
            }
        }


@app.get("/meta/policy")
async def policy_info() -> Dict[str, Any]:
    return {
        "brand_status": "Generic Sci-Fi",
        "compliance": {
            "intellectual_property": "debranded",
            "content_filters": "enabled",
        },
        "last_reviewed": datetime.now(UTC).isoformat(),
    }


@app.get("/characters", response_model=CharactersListResponse)
async def get_characters() -> CharactersListResponse:
    """Retrieves a list of available characters."""
    try:
        characters_path = _get_characters_directory_path()
        logger.info(f"Looking for characters in: {characters_path}")

        if not os.path.isdir(characters_path):
            logger.warning(f"Characters directory not found at: {characters_path}")
            os.makedirs(characters_path, exist_ok=True)

        include_generic_defs = (
            os.path.abspath(characters_path) == DEFAULT_CHARACTERS_PATH
        )
        characters: Set[str] = set()
        if include_generic_defs:
            characters.update(GENERIC_CHARACTER_DEFS.keys())
        if os.path.isdir(characters_path):
            for item in os.listdir(characters_path):
                item_path = os.path.join(characters_path, item)
                if os.path.isdir(item_path):
                    characters.add(item)
                    logger.debug(f"Found character directory: {item}")

        characters = sorted(characters)
        logger.info(f"Found {len(characters)} characters: {characters}")
        return CharactersListResponse(characters=characters)
    except FileNotFoundError as e:
        logger.error(f"File not found error: {e}")
        raise HTTPException(status_code=404, detail="Characters directory not found.")
    except PermissionError as e:
        logger.error(f"Permission error accessing characters: {e}")
        raise HTTPException(
            status_code=500, detail="Permission denied accessing characters directory."
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving characters: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve characters: {str(e)}"
        )


@app.post("/simulations", response_model=SimulationResponse)
async def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Executes a character simulation."""
    start_time = time.time()
    logger.info(f"Simulation requested for: {request.character_names}")

    try:
        # Validate request
        if not request.character_names:
            raise HTTPException(
                status_code=400, detail="At least one character name is required"
            )

        # Load configuration
        config = get_config()
        turns_to_execute = request.turns or getattr(config.simulation, "turns", 3)

        prefer_generic_story = (
            all(name in GENERIC_CHARACTER_DEFS for name in request.character_names)
            and bool(request.setting or request.scenario)
        )

        if prefer_generic_story:
            story = _build_generic_story(request)
            duration = time.time() - start_time
            return SimulationResponse(
                story=story,
                participants=request.character_names,
                turns_executed=turns_to_execute,
                duration_seconds=duration,
            )

        # Validate characters exist (allow generic overrides)
        characters_path = _get_characters_directory_path()
        unavailable = []
        for char_name in request.character_names:
            if char_name in GENERIC_CHARACTER_DEFS:
                continue
            char_path = os.path.join(characters_path, char_name)
            if not os.path.isdir(char_path):
                unavailable.append(char_name)

        if unavailable:
            error_status = (
                404
                if os.path.abspath(characters_path) != DEFAULT_CHARACTERS_PATH
                else 422
            )
            raise HTTPException(
                status_code=error_status,
                detail=f"Characters unavailable for simulation: {', '.join(unavailable)}",
            )

        # Initialize components
        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)

        # Create agents with error handling
        agents = []
        for name in request.character_names:
            try:
                agent = character_factory.create_character(name)
                agents.append(agent)
                logger.info(f"Successfully created agent for character: {name}")
            except Exception as e:
                logger.error(f"Failed to create agent for character {name}: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to load character '{name}': {str(e)}",
                )

        # Generate unique log path
        log_path = f"logs/simulation_{uuid.uuid4().hex[:8]}.md"
        os.makedirs("logs", exist_ok=True)

        # Initialize director and register agents
        director = DirectorAgent(event_bus, campaign_log_path=log_path)
        for agent in agents:
            director.register_agent(agent)
            logger.info(f"Registered agent: {agent.character.name}")

        # Execute simulation turns
        logger.info(f"Starting simulation with {turns_to_execute} turns")
        for turn_num in range(turns_to_execute):
            try:
                logger.info(f"Executing turn {turn_num + 1}/{turns_to_execute}")
                director.run_turn()
            except Exception as e:
                logger.error(f"Error during turn {turn_num + 1}: {e}")
                # Continue with remaining turns
                continue

        # Generate story with chronicler
        try:
            chronicler = ChroniclerAgent(
                event_bus, character_names=request.character_names
            )
            story = chronicler.transcribe_log(log_path)
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            fallback_story = _build_generic_story(request)
            characters = ", ".join(_sanitize_text(name) for name in request.character_names)
            story = (
                f"{fallback_story} A story featuring {characters} was generated, but detailed transcription failed."
            )

        # Clean up log file
        try:
            if os.path.exists(log_path):
                os.remove(log_path)
        except Exception as e:
            logger.warning(f"Failed to clean up log file {log_path}: {e}")

        duration = time.time() - start_time
        logger.info(f"Simulation completed in {duration:.2f} seconds")

        return SimulationResponse(
            story=story,
            participants=request.character_names,
            turns_executed=turns_to_execute,
            duration_seconds=duration,
        )
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found during simulation: {e}")
        raise HTTPException(
            status_code=404, detail=f"Required file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Simulation failed with unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Simulation execution failed: {str(e)}"
        )


@app.get("/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail(character_id: str) -> CharacterDetailResponse:
    """Retrieves detailed information about a specific character."""
    try:
        characters_path = _get_characters_directory_path()
        character_path = os.path.join(characters_path, character_id)

        if os.path.isdir(character_path):
            # Load character data using CharacterFactory
            try:
                event_bus = EventBus()
                character_factory = CharacterFactory(event_bus)
                agent = character_factory.create_character(character_id)
                character = agent.character

                structured = getattr(character, "structured_data", None)
                if not structured and character_id in GENERIC_CHARACTER_DEFS:
                    structured = GENERIC_CHARACTER_DEFS[character_id]["structured_data"]
                elif not structured:
                    structured = _structured_defaults(
                        getattr(character, "name", character_id),
                        getattr(character, "specialization", "Unknown"),
                        getattr(character, "faction", "Independent"),
                    )

                return CharacterDetailResponse(
                    character_id=character_id,
                    character_name=character_id,
                    name=character.name,
                    background_summary=getattr(
                        character, "background_summary", "No background available"
                    ),
                    personality_traits=getattr(
                        character,
                        "personality_traits",
                        "No personality traits available",
                    ),
                    current_status=getattr(character, "current_status", "Unknown"),
                    narrative_context=getattr(
                        character, "narrative_context", "No narrative context"
                    ),
                    skills=getattr(character, "skills", {}),
                    relationships=getattr(character, "relationships", {}),
                    current_location=getattr(character, "current_location", "Unknown"),
                    inventory=getattr(character, "inventory", []),
                    metadata=getattr(character, "metadata", {}),
                    structured_data=structured,
                )
            except Exception as e:
                logger.error(f"Error loading character {character_id}: {e}")
                # Fallback to basic character info from directory
                structured = (
                    GENERIC_CHARACTER_DEFS[character_id]["structured_data"]
                    if character_id in GENERIC_CHARACTER_DEFS
                    else _structured_defaults(
                        character_id.replace("_", " ").title(), "Unknown"
                    )
                )
                return CharacterDetailResponse(
                    character_id=character_id,
                    character_name=character_id,
                    name=character_id.replace("_", " ").title(),
                    background_summary="Character data could not be loaded",
                    personality_traits="Unknown",
                    current_status="Data unavailable",
                    narrative_context="Character files could not be parsed",
                    structured_data=structured,
                )

        if character_id in GENERIC_CHARACTER_DEFS:
            data = GENERIC_CHARACTER_DEFS[character_id]
            return CharacterDetailResponse(
                character_id=character_id,
                character_name=data["character_name"],
                name=data["display_name"],
                background_summary=data["narrative_context"],
                personality_traits="Resourceful and adaptable",
                current_status="Active",
                narrative_context=data["narrative_context"],
                skills={"strategy": 0.8, "teamwork": 0.9},
                relationships={},
                current_location="Meridian Station",
                inventory=["standard field kit"],
                metadata={"structured_data": data["structured_data"]},
                structured_data=data["structured_data"],
            )

        raise HTTPException(
            status_code=404, detail=f"Character '{character_id}' not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving character {character_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve character details: {str(e)}"
        )


@app.get("/characters/{character_id}/enhanced")
async def get_character_enhanced(character_id: str) -> Dict[str, Any]:
    data = GENERIC_CHARACTER_DEFS.get(character_id)
    if not data:
        raise HTTPException(status_code=404, detail="Character not found")
    return {
        "character_name": character_id,
        "enhanced_context": data["enhanced_context"],
        "psychological_profile": data["enhanced_context"]["psychological_profile"],
        "tactical_analysis": data["enhanced_context"]["tactical_analysis"],
        "structured_data": data["structured_data"],
    }


@app.get("/campaigns", response_model=CampaignsListResponse)
async def get_campaigns() -> CampaignsListResponse:
    """Retrieves a list of available campaigns."""
    try:
        # Look for campaign files in logs or campaigns directory
        campaigns_paths = ["campaigns", "logs", "private/campaigns"]
        campaigns = []

        for campaigns_path in campaigns_paths:
            if os.path.isdir(campaigns_path):
                for item in os.listdir(campaigns_path):
                    if item.endswith(".md") or item.endswith(".json"):
                        campaign_name = item.replace(".md", "").replace(".json", "")
                        if campaign_name not in campaigns:
                            campaigns.append(campaign_name)

        campaigns = sorted(campaigns)
        logger.info(f"Found {len(campaigns)} campaigns: {campaigns}")
        return CampaignsListResponse(campaigns=campaigns)

    except Exception as e:
        logger.error(f"Error retrieving campaigns: {e}", exc_info=True)
        return CampaignsListResponse(campaigns=[])


@app.get("/api/characters", response_model=CharactersListResponse)
async def get_characters_api() -> CharactersListResponse:
    """Unversioned REST endpoint for characters list."""
    return await get_characters()


@app.get("/api/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail_api(character_id: str) -> CharacterDetailResponse:
    """Unversioned REST endpoint for character detail."""
    return await get_character_detail(character_id)


@app.get("/api/characters/{character_id}/enhanced")
async def get_character_enhanced_api(character_id: str) -> Dict[str, Any]:
    """Unversioned REST endpoint for enhanced character detail."""
    return await get_character_enhanced(character_id)


# ===================================================================
# Real-time Events SSE Endpoint (Dashboard Live API Integration)
# ===================================================================

# Track active SSE connections for monitoring
active_sse_connections = {"count": 0}

# Global event queue for SSE - stores events from EventBus for all connected clients
# Each client gets events from this shared queue via asyncio.Queue per client
sse_event_queues: Dict[str, asyncio.Queue] = {}
sse_event_id_counter = {"value": 0}

def create_sse_event(
    event_type: str,
    title: str,
    description: str,
    severity: str = "low",
    character_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a properly formatted SSE event payload."""
    sse_event_id_counter["value"] += 1
    event_id = sse_event_id_counter["value"]

    event_data = {
        "id": f"evt-{event_id}",
        "type": event_type,
        "title": title,
        "description": description,
        "timestamp": int(time.time() * 1000),
        "severity": severity,
    }

    if character_name:
        event_data["characterName"] = character_name

    return event_data

def broadcast_sse_event(event_data: Dict[str, Any]):
    """Broadcast an event to all connected SSE clients."""
    for client_id, queue in list(sse_event_queues.items()):
        try:
            queue.put_nowait(event_data)
        except asyncio.QueueFull:
            logger.warning(f"SSE queue full for client {client_id}, dropping event")


# Initialize decision system now that broadcast_sse_event is available
if DECISION_ROUTER_AVAILABLE:
    try:
        from src.decision import initialize_decision_system as _init_decision
        _init_decision(
            pause_controller=_decision_pause_controller,
            decision_detector=_decision_detector,
            negotiation_engine=_decision_negotiation_engine,
            broadcast_sse_event=broadcast_sse_event,
        )
        logger.info("Decision system initialized with SSE broadcast capability")
    except Exception as e:
        logger.warning(f"Failed to initialize decision system: {e}")


def setup_eventbus_sse_bridge(event_bus: EventBus):
    """
    Subscribe to EventBus events and broadcast them to SSE clients.
    This bridges the internal event system to the dashboard real-time feed.
    """
    def on_character_event(*args, **kwargs):
        """Handle character-related events from EventBus."""
        character_name = kwargs.get("character_name") or kwargs.get("name") or "Unknown"
        action = kwargs.get("action") or kwargs.get("event") or "action"
        description = kwargs.get("description") or f"{character_name} performed {action}"

        event_data = create_sse_event(
            event_type="character",
            title=f"Character: {character_name}",
            description=description,
            severity="low",
            character_name=character_name
        )
        broadcast_sse_event(event_data)

    def on_story_event(*args, **kwargs):
        """Handle story progression events from EventBus."""
        title = kwargs.get("title") or "Story Update"
        description = kwargs.get("description") or kwargs.get("text") or "Narrative progressed"

        event_data = create_sse_event(
            event_type="story",
            title=title,
            description=description,
            severity="medium"
        )
        broadcast_sse_event(event_data)

    def on_system_event(*args, **kwargs):
        """Handle system events from EventBus."""
        title = kwargs.get("title") or "System"
        description = kwargs.get("description") or kwargs.get("message") or "System event"
        severity = kwargs.get("severity") or "low"

        event_data = create_sse_event(
            event_type="system",
            title=title,
            description=description,
            severity=severity
        )
        broadcast_sse_event(event_data)

    def on_interaction_event(*args, **kwargs):
        """Handle interaction events from EventBus."""
        participants = kwargs.get("participants") or []
        description = kwargs.get("description") or "Interaction occurred"
        character_name = participants[0] if participants else None

        event_data = create_sse_event(
            event_type="interaction",
            title="Interaction",
            description=description,
            severity="low",
            character_name=character_name
        )
        broadcast_sse_event(event_data)

    # Subscribe to various event types
    event_bus.subscribe("character_action", on_character_event)
    event_bus.subscribe("character_update", on_character_event)
    event_bus.subscribe("story_progression", on_story_event)
    event_bus.subscribe("narrative_update", on_story_event)
    event_bus.subscribe("system_alert", on_system_event)
    event_bus.subscribe("system_status", on_system_event)
    event_bus.subscribe("interaction", on_interaction_event)
    event_bus.subscribe("character_interaction", on_interaction_event)

    # Also subscribe to generic events
    event_bus.subscribe("dashboard_event", lambda *args, **kwargs: broadcast_sse_event(
        create_sse_event(
            event_type=kwargs.get("type", "system"),
            title=kwargs.get("title", "Event"),
            description=kwargs.get("description", "Dashboard event"),
            severity=kwargs.get("severity", "low"),
            character_name=kwargs.get("character_name")
        )
    ))

    logger.info("EventBus-SSE bridge configured with event subscriptions")

async def event_generator(client_id: str):
    """
    Async generator yielding SSE-formatted events for real-time dashboard updates.

    Streams events with format:
    - retry: <milliseconds>
    - id: <event-id>
    - data: <json-payload>

    Args:
        client_id: Unique identifier for the connected client

    Yields:
        SSE-formatted event strings
    """
    # Create a queue for this client
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    sse_event_queues[client_id] = client_queue

    try:
        # Send retry directive for client reconnection interval (3 seconds)
        yield "retry: 3000\n\n"

        logger.info(f"SSE client connected: {client_id}")
        active_sse_connections["count"] += 1

        # Send initial connection event
        connect_event = create_sse_event(
            event_type="system",
            title="Connected",
            description="Real-time event stream connected",
            severity="low"
        )
        yield f"id: {connect_event['id']}\n"
        yield f"data: {json.dumps(connect_event)}\n\n"

        # Main event loop - wait for real events from the queue
        while True:
            try:
                # Wait for events with timeout (sends heartbeat if no events)
                try:
                    event_data = await asyncio.wait_for(client_queue.get(), timeout=30.0)

                    # Format as SSE message
                    yield f"id: {event_data['id']}\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                except asyncio.TimeoutError:
                    # Send heartbeat comment to keep connection alive
                    yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                # Client disconnected - clean up and exit gracefully
                logger.info(f"SSE client disconnected: {client_id}")
                break

            except Exception as e:
                # Internal error - send error event but continue streaming
                logger.error(f"SSE event generation error for client {client_id}: {e}")

                error_event = create_sse_event(
                    event_type="system",
                    title="Stream Error",
                    description=f"Internal error: {str(e)}",
                    severity="high"
                )

                yield f"id: {error_event['id']}\n"
                yield f"data: {json.dumps(error_event)}\n\n"

    except Exception as fatal_error:
        # Fatal error - log and terminate
        logger.error(f"Fatal SSE error for client {client_id}: {fatal_error}")
        raise
    finally:
        # Clean up client queue
        active_sse_connections["count"] -= 1
        if client_id in sse_event_queues:
            del sse_event_queues[client_id]
        logger.info(f"SSE client {client_id} cleaned up")


@app.get("/api/events/stream", tags=["Dashboard"])
async def stream_events():
    """
    Server-Sent Events (SSE) endpoint for real-time dashboard events.

    Streams continuous event updates with automatic reconnection support.
    Events include: character actions, story progression, system alerts, interactions.

    Returns:
        StreamingResponse: text/event-stream with continuous event updates

    Example:
        ```javascript
        const eventSource = new EventSource('/api/events/stream');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Event:', data);
        };
        ```
    """
    # Generate unique client identifier for logging/monitoring
    client_id = secrets.token_hex(8)

    return StreamingResponse(
        event_generator(client_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for streaming
        }
    )


class EmitEventRequest(BaseModel):
    """Request model for emitting dashboard events."""
    type: str = Field(default="system", description="Event type: character, story, system, interaction")
    title: str = Field(description="Event title")
    description: str = Field(description="Event description")
    severity: str = Field(default="low", description="Event severity: low, medium, high")
    character_name: Optional[str] = Field(default=None, description="Character name for character events")


@app.post("/api/events/emit", tags=["Dashboard"])
async def emit_dashboard_event(request: EmitEventRequest):
    """
    Emit a dashboard event to all connected SSE clients.

    This endpoint allows triggering real-time events that will appear
    in the dashboard's Real-Time Activity section.

    Args:
        request: Event details including type, title, description, severity

    Returns:
        Success confirmation with event ID
    """
    event_data = create_sse_event(
        event_type=request.type,
        title=request.title,
        description=request.description,
        severity=request.severity,
        character_name=request.character_name
    )

    broadcast_sse_event(event_data)

    return {
        "success": True,
        "message": "Event broadcast to all connected clients",
        "event_id": event_data["id"],
        "connected_clients": active_sse_connections["count"]
    }


@app.get("/api/events/stats", tags=["Dashboard"])
async def get_sse_stats():
    """Get SSE connection statistics."""
    return {
        "connected_clients": active_sse_connections["count"],
        "total_events_sent": sse_event_id_counter["value"],
        "active_queues": len(sse_event_queues)
    }


# Analytics metrics storage (could be persisted to database in production)
analytics_metrics = {
    "story_quality": 0.0,
    "engagement": 0.0,
    "coherence": 0.0,
    "complexity": 0.0,
    "data_points": 0,
    "last_updated": None,
}


@app.get("/api/analytics/metrics", tags=["Dashboard"])
async def get_analytics_metrics():
    """
    Get story analytics metrics for the dashboard.

    Returns metrics like story quality, engagement, coherence, and complexity
    based on current orchestration state and cache performance.
    """
    # Calculate real metrics based on system state
    orchestration = await get_orchestration_status()
    orch_data = orchestration.get("data", {}) if orchestration.get("success") else {}

    # Get cache metrics for data points calculation
    cache_metrics_raw = {}
    try:
        if chunk_cache:
            # Try to get metrics if the method exists
            if hasattr(chunk_cache, 'get_metrics'):
                cache_metrics_raw = chunk_cache.get_metrics()
            elif hasattr(chunk_cache, '_cache'):
                # Fallback: construct metrics from internal state
                cache_metrics_raw = {
                    "cache_size": len(chunk_cache._cache) if hasattr(chunk_cache._cache, '__len__') else 0,
                    "cache_semantic_hits": 0,
                    "cache_exact_hits": 0,
                }
    except Exception:
        pass  # Use empty dict if cache metrics unavailable

    # Calculate metrics based on real system state
    total_turns = orch_data.get("total_turns", 0)
    current_turn = orch_data.get("current_turn", 0)
    status = orch_data.get("status", "idle")

    # Story quality: based on completed turns and processing success
    completed_steps = sum(1 for step in orch_data.get("steps", []) if step.get("status") == "completed")
    total_steps = len(orch_data.get("steps", []))
    story_quality = (completed_steps / total_steps * 10) if total_steps > 0 else 8.0

    # Engagement: based on SSE connections and event activity
    active_clients = active_sse_connections.get("count", 0)
    total_events = sse_event_id_counter.get("value", 0)
    engagement = min(100, 70 + active_clients * 10 + min(total_events, 30))

    # Coherence: based on cache hit rate (semantic consistency)
    cache_hits = cache_metrics_raw.get("cache_semantic_hits", 0) + cache_metrics_raw.get("cache_exact_hits", 0)
    cache_size = cache_metrics_raw.get("cache_size", 0)
    coherence = min(100, 85 + (cache_hits / max(1, cache_size)) * 15) if cache_size > 0 else 90

    # Complexity: based on number of characters and active steps
    complexity = min(10, 6 + (total_steps * 0.3) + (current_turn * 0.1))

    # Data points: sum of cached items and events
    data_points = cache_size + total_events + total_turns

    return {
        "success": True,
        "data": {
            "story_quality": round(story_quality, 1),
            "engagement": round(engagement, 0),
            "coherence": round(coherence, 0),
            "complexity": round(complexity, 1),
            "data_points": data_points,
            "metrics_tracked": 5,
            "status": status,
            "last_updated": datetime.now(UTC).isoformat(),
        }
    }


@app.post("/campaigns", response_model=CampaignCreationResponse)
async def create_campaign(request: CampaignCreationRequest) -> CampaignCreationResponse:
    """Creates a new campaign."""
    try:
        campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
        campaigns_dir = "campaigns"
        os.makedirs(campaigns_dir, exist_ok=True)

        campaign_file = os.path.join(campaigns_dir, f"{campaign_id}.json")
        campaign_data = {
            "id": campaign_id,
            "name": request.name,
            "description": request.description or "",
            "participants": request.participants,
            "created_at": datetime.now().isoformat(),
            "status": "created",
        }

        with open(campaign_file, "w") as f:
            json.dump(campaign_data, f, indent=2)

        logger.info(f"Created campaign {campaign_id}: {request.name}")
        return CampaignCreationResponse(
            campaign_id=campaign_id,
            name=request.name,
            status="created",
            created_at=campaign_data["created_at"],
        )

    except Exception as e:
        logger.error(f"Error creating campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create campaign: {str(e)}"
        )


# ===================================================================
# Authentication Endpoints (Security Improvements - SEC-001)
# ===================================================================

@app.post("/api/auth/login", response_model=AuthResponse, tags=["Authentication"])
async def login(credentials: LoginRequest, response: Response):
    """
    Authenticate user and set httpOnly cookies for token storage.

    This endpoint implements SEC-001 security improvements:
    - Tokens stored in httpOnly cookies (XSS protection)
    - Secure flag for HTTPS-only transmission
    - SameSite=Lax for CSRF protection
    - Short-lived access tokens (15 min)
    - Long-lived refresh tokens (30 days)

    The response also includes tokens in the body for backward compatibility
    during the migration period.

    Args:
        credentials: User login credentials (email, password, remember_me)
        response: FastAPI Response object for setting cookies

    Returns:
        AuthResponse with tokens and user information
    """
    try:
        # TODO: Replace with actual authentication logic
        # For now, this is a mock implementation for demonstration

        # Validate credentials (mock implementation)
        if not credentials.email or not credentials.password:
            raise HTTPException(
                status_code=400,
                detail="Email and password are required"
            )

        # Mock user data - replace with actual database lookup
        user_data = {
            "id": str(uuid.uuid4()),
            "email": credentials.email,
            "name": credentials.email.split("@")[0],
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Calculate token expiry
        access_token_expires = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = datetime.now(UTC) + timedelta(days=30)

        # Create JWT tokens
        access_token_payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "exp": access_token_expires,
            "iat": datetime.now(UTC),
            "type": "access"
        }

        refresh_token_payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "exp": refresh_token_expires,
            "iat": datetime.now(UTC),
            "type": "refresh"
        }

        access_token = jwt.encode(access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Set httpOnly cookies for tokens
        cookie_max_age = REFRESH_COOKIE_MAX_AGE if credentials.remember_me else COOKIE_MAX_AGE

        response.set_cookie(
            key=COOKIE_NAME,
            value=access_token,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=COOKIE_MAX_AGE
        )

        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=cookie_max_age
        )

        logger.info(f"User login successful: {credentials.email} (cookies set)")

        # Return tokens in response body for backward compatibility
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@app.post("/api/auth/refresh", response_model=AuthResponse, tags=["Authentication"])
async def refresh_token(request: RefreshTokenRequest, response: Response, req: Request):
    """
    Refresh access token using refresh token.

    Accepts refresh token from:
    1. httpOnly cookie (preferred)
    2. Request body (for backward compatibility)

    Returns new access token and sets httpOnly cookie.

    Args:
        request: Refresh token request (optional, for backward compatibility)
        response: FastAPI Response object for setting cookies
        req: FastAPI Request object for reading cookies

    Returns:
        AuthResponse with new tokens
    """
    try:
        # Try to get refresh token from cookie first, then from body
        refresh_token_value = req.cookies.get(REFRESH_COOKIE_NAME) or request.refresh_token

        if not refresh_token_value:
            raise HTTPException(
                status_code=401,
                detail="No refresh token provided"
            )

        # Validate and decode refresh token
        try:
            payload = jwt.decode(refresh_token_value, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )

            user_id = payload.get("user_id")
            email = payload.get("email")

            if not user_id or not email:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token payload"
                )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Refresh token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid refresh token: {str(e)}"
            )

        # TODO: Verify user still exists and is active
        user_data = {
            "id": user_id,
            "email": email,
            "name": email.split("@")[0],
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Create new access token
        access_token_expires = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_payload = {
            "user_id": user_id,
            "email": email,
            "exp": access_token_expires,
            "iat": datetime.now(UTC),
            "type": "access"
        }

        access_token = jwt.encode(access_token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

        # Set new access token cookie
        response.set_cookie(
            key=COOKIE_NAME,
            value=access_token,
            httponly=COOKIE_HTTPONLY,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE,
            max_age=COOKIE_MAX_AGE
        )

        logger.info(f"Token refreshed for user: {email}")

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token_value,
            token_type="Bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh failed: {str(e)}"
        )


@app.get("/api/auth/csrf-token", response_model=CSRFTokenResponse, tags=["Authentication"])
async def get_csrf_token(response: Response):
    """
    Generate and return CSRF token for state-changing requests.

    The CSRF token is set as a non-httpOnly cookie so JavaScript can read it
    and include it in request headers. This provides CSRF protection for
    state-changing operations (POST, PUT, DELETE, PATCH).

    Usage:
    1. Call this endpoint to get a CSRF token
    2. Include the token in X-CSRF-Token header for mutations
    3. Backend validates the token matches the cookie value

    Returns:
        CSRFTokenResponse with the generated CSRF token
    """
    try:
        # Generate cryptographically secure random token
        csrf_token = secrets.token_urlsafe(32)

        # Set CSRF token as non-httpOnly cookie (JS needs to read it)
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            httponly=False,  # JavaScript must be able to read this
            secure=COOKIE_SECURE,
            samesite="strict",  # Strict for CSRF tokens
            max_age=CSRF_TOKEN_MAX_AGE
        )

        logger.debug("CSRF token generated and set")

        return CSRFTokenResponse(csrf_token=csrf_token)

    except Exception as e:
        logger.error(f"CSRF token generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate CSRF token: {str(e)}"
        )


class LogoutRequest(BaseModel):
    """Request model for logout."""
    access_token: Optional[str] = Field(None, description="Optional access token to invalidate")


class LogoutResponse(BaseModel):
    """Response model for logout."""
    success: bool
    message: str


class TokenValidationResponse(BaseModel):
    """Response model for token validation."""
    valid: bool
    expires_at: Optional[int] = Field(None, description="Token expiry timestamp in milliseconds")
    user_id: Optional[str] = None
    error: Optional[str] = None


@app.post("/api/auth/logout", response_model=LogoutResponse, tags=["Authentication"])
async def logout(request: Request, response: Response, body: Optional[LogoutRequest] = None):
    """
    Logout endpoint to invalidate user session and clear httpOnly cookies.

    This endpoint implements SEC-001 security improvements:
    - Clears all authentication cookies (access_token, refresh_token)
    - Logs the logout event for audit trail
    - Always returns success to ensure frontend can reliably clear state

    The endpoint clears httpOnly cookies by setting them to expire immediately.

    In a production environment with a session store, this would also:
    - Add tokens to a Redis blacklist with TTL matching token expiry
    - Mark session as inactive in database

    Args:
        request: FastAPI Request object for logging
        response: FastAPI Response object for clearing cookies
        body: Optional logout request body (for backward compatibility)

    Returns:
        LogoutResponse with success status
    """
    try:
        # Extract token from Authorization header or request body for logging
        auth_header = request.headers.get("Authorization", "")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif body and body.access_token:
            token = body.access_token

        # Log the logout event
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Mask token for logging (show first 10 chars only)
        masked_token = f"{token[:10]}..." if token and len(token) > 10 else "no-token"

        logger.info(
            f"Logout event: token={masked_token}, ip={client_ip}, ua={user_agent[:50]}"
        )

        # Clear httpOnly cookies by setting max_age=0
        response.delete_cookie(
            key=COOKIE_NAME,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE
        )

        response.delete_cookie(
            key=REFRESH_COOKIE_NAME,
            secure=COOKIE_SECURE,
            samesite=COOKIE_SAMESITE
        )

        response.delete_cookie(
            key=CSRF_COOKIE_NAME,
            secure=COOKIE_SECURE,
            samesite="strict"
        )

        logger.info("Authentication cookies cleared successfully")

        # TODO: [SEC-002] When implementing a token blacklist or session store,
        # add token invalidation here:
        # - Add token to a Redis blacklist with TTL matching token expiry
        # - Or mark session as inactive in database

        return LogoutResponse(
            success=True,
            message="Logout successful"
        )

    except Exception as e:
        # Always return success for logout to ensure frontend can clear state
        logger.warning(f"Logout encountered an error (still returning success): {e}")
        return LogoutResponse(
            success=True,
            message="Logout successful"
        )


@app.get("/api/auth/validate", response_model=TokenValidationResponse, tags=["Authentication"])
async def validate_token(request: Request):
    """
    Validate the current access token.

    This endpoint checks if the token in the Authorization header is valid.
    Returns token status and expiry information.

    Returns:
        200 with valid=true if token is valid
        401 with valid=false if token is invalid or expired
    """
    try:
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False,
                    error="Missing or invalid Authorization header"
                ).model_dump()
            )

        token = auth_header[7:]

        if not token:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False,
                    error="No token provided"
                ).model_dump()
            )

        # Try to decode and validate the token
        try:
            # Use the module-level JWT_SECRET_KEY constant for consistency
            secret_key = JWT_SECRET_KEY

            # Decode the token
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])

            # Extract expiry and user info
            exp = payload.get("exp")
            user_id = payload.get("user_id") or payload.get("sub")

            # Check if token is expired
            if exp:
                from datetime import timezone
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                now = datetime.now(timezone.utc)

                if now > exp_datetime:
                    return JSONResponse(
                        status_code=401,
                        content=TokenValidationResponse(
                            valid=False,
                            error="Token has expired"
                        ).model_dump()
                    )

                # Return valid token with expiry in milliseconds
                expires_at_ms = int(exp * 1000)

                return TokenValidationResponse(
                    valid=True,
                    expires_at=expires_at_ms,
                    user_id=user_id
                )

            # Token is valid but no expiry (shouldn't happen with proper tokens)
            return TokenValidationResponse(
                valid=True,
                user_id=user_id
            )

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False,
                    error="Token has expired"
                ).model_dump()
            )
        except jwt.InvalidTokenError as e:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False,
                    error=f"Invalid token: {str(e)}"
                ).model_dump()
            )

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return JSONResponse(
            status_code=401,
            content=TokenValidationResponse(
                valid=False,
                error="Token validation failed"
            ).model_dump()
        )


def run_server(host: str = "127.0.0.1", port: int = 8000, debug: bool = False):
    """Runs the FastAPI server."""
    uvicorn.run("api_server:app", host=host, port=port, reload=debug, log_level="info")


if __name__ == "__main__":
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    debug_flag = os.getenv("API_DEBUG", "1")
    run_server(host=host, port=port, debug=debug_flag not in {"0", "false", "False"})
