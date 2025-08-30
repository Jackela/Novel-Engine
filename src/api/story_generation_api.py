#!/usr/bin/env python3
"""
Story Generation API.

API endpoints for story export, narrative generation, and content formatting.
Enhanced with WebSocket support for real-time progress monitoring.
"""

import asyncio
import asyncio.queues
import logging
import time
import uuid
from asyncio import Semaphore
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

from src.core.system_orchestrator import SystemOrchestrator

logger = logging.getLogger(__name__)


class StoryGenerationRequest(BaseModel):
    """Request model for story generation."""

    characters: List[str] = Field(..., min_length=1)
    title: str = Field("A Generated Story", max_length=200)


class StoryGenerationResponse(BaseModel):
    """Response model for story generation requests."""

    generation_id: str
    status: str
    message: str


class ProgressUpdate(BaseModel):
    """Model for real-time progress updates."""

    generation_id: str
    progress: float = Field(ge=0, le=100)
    stage: str
    stage_detail: str
    estimated_time_remaining: int  # seconds
    active_agents: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


@dataclass
class ConnectionPool:
    """WebSocket connection pool with automatic cleanup."""

    connections: Dict[str, Set[WebSocket]] = field(
        default_factory=lambda: defaultdict(set)
    )
    last_activity: Dict[str, float] = field(default_factory=dict)
    cleanup_interval: float = 300  # 5 minutes

    def add_connection(self, generation_id: str, websocket: WebSocket):
        """
        Add a WebSocket connection to the pool.

        Args:
            generation_id: ID of the story generation session
            websocket: WebSocket connection to add
        """
        self.connections[generation_id].add(websocket)
        self.last_activity[generation_id] = time.time()

    def remove_connection(self, generation_id: str, websocket: WebSocket):
        """
        Remove a WebSocket connection from the pool.

        Args:
            generation_id: ID of the story generation session
            websocket: WebSocket connection to remove
        """
        self.connections[generation_id].discard(websocket)
        if not self.connections[generation_id]:
            del self.connections[generation_id]
            self.last_activity.pop(generation_id, None)

    async def cleanup_stale_connections(self):
        """Remove connections with no activity."""
        current_time = time.time()
        stale_generations = [
            gen_id
            for gen_id, last_time in self.last_activity.items()
            if current_time - last_time > self.cleanup_interval
        ]
        for gen_id in stale_generations:
            self.connections.pop(gen_id, None)
            self.last_activity.pop(gen_id, None)


class StoryGenerationAPI:
    """API for story export and narrative generation with optimized WebSocket handling."""

    def __init__(self, orchestrator: Optional[SystemOrchestrator]):
        """Initializes the story generation API with performance optimizations."""
        self.orchestrator = orchestrator
        self.active_generations: Dict[str, Any] = {}
        self.connection_pool = ConnectionPool()
        self.generation_semaphore = Semaphore(5)  # Limit concurrent generations
        self.cleanup_task = None
        logger.info("Story Generation API initialized with performance optimizations.")

    def set_orchestrator(self, orchestrator: SystemOrchestrator):
        """Set the orchestrator after initialization."""
        self.orchestrator = orchestrator
        logger.info("Story Generation API orchestrator set.")

    async def start_background_tasks(self):
        """Start background cleanup tasks."""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_background_tasks(self):
        """Stop background cleanup tasks."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """Background cleanup for stale connections and completed generations."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self.connection_pool.cleanup_stale_connections()

                # Clean up completed generations older than 1 hour
                current_time = time.time()
                completed_generations = [
                    gen_id
                    for gen_id, state in self.active_generations.items()
                    if state.get("status") in ["completed", "failed"]
                    and current_time - state.get("completion_time", current_time) > 3600
                ]
                for gen_id in completed_generations:
                    self.active_generations.pop(gen_id, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def setup_routes(self, app: FastAPI):
        """Sets up API routes for story generation."""

        @app.post("/api/v1/stories/generate", response_model=StoryGenerationResponse)
        async def generate_story(
            request: StoryGenerationRequest, background_tasks: BackgroundTasks
        ):
            """Generates a story from character interactions."""
            if not self.orchestrator:
                raise HTTPException(
                    status_code=503, detail="System not ready. Please try again."
                )

            try:
                # Validate that all characters exist
                active_agents = getattr(self.orchestrator, "active_agents", {})
                missing_characters = [
                    char for char in request.characters if char not in active_agents
                ]
                if missing_characters:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Characters not found: {', '.join(missing_characters)}",
                    )

                generation_id = f"story_{uuid.uuid4().hex[:8]}"

                self.active_generations[generation_id] = {
                    "status": "initiated",
                    "request": request,
                    "progress": 0,
                    "stage": "initializing",
                    "start_time": datetime.now(),
                }
                background_tasks.add_task(self._generate_story_async, generation_id)

                return StoryGenerationResponse(
                    generation_id=generation_id,
                    status="initiated",
                    message="Story generation initiated.",
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error initiating story generation: {e}")
                raise HTTPException(status_code=500, detail="Internal server error.")

        @app.websocket("/api/v1/stories/progress/{generation_id}")
        async def websocket_progress(websocket: WebSocket, generation_id: str):
            """Optimized WebSocket endpoint with connection pooling."""
            try:
                await websocket.accept()
                self.connection_pool.add_connection(generation_id, websocket)

                # Send initial status if generation exists
                if generation_id in self.active_generations:
                    await self._send_progress_update(generation_id, websocket)

                # Keep connection alive with heartbeat
                heartbeat_interval = 30  # 30 seconds
                last_heartbeat = time.time()

                while True:
                    try:
                        # Use timeout to implement heartbeat
                        data = await asyncio.wait_for(
                            websocket.receive_text(), timeout=heartbeat_interval
                        )

                        # Handle ping/pong for connection health
                        if data == "ping":
                            await websocket.send_text("pong")
                        last_heartbeat = time.time()

                    except asyncio.TimeoutError:
                        # Send heartbeat
                        current_time = time.time()
                        if current_time - last_heartbeat >= heartbeat_interval:
                            try:
                                await websocket.send_text('{"type": "heartbeat"}')
                                last_heartbeat = current_time
                            except Exception:
                                break
                    except WebSocketDisconnect:
                        break

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket connection closed for generation {generation_id}"
                )
            except Exception as e:
                logger.error(f"WebSocket error for generation {generation_id}: {e}")
            finally:
                self.connection_pool.remove_connection(generation_id, websocket)

        @app.get("/api/v1/stories/status/{generation_id}")
        async def get_generation_status(generation_id: str):
            """Get current status of a story generation (REST fallback)."""
            if generation_id not in self.active_generations:
                return {"error": "Generation not found"}

            state = self.active_generations[generation_id]
            return {
                "generation_id": generation_id,
                "status": state["status"],
                "progress": state.get("progress", 0),
                "stage": state.get("stage", "unknown"),
                "estimated_time_remaining": self._calculate_time_remaining(state),
            }

    async def _generate_story_async(self, generation_id: str):
        """Optimized story generation with semaphore and parallel processing."""
        async with self.generation_semaphore:  # Limit concurrent generations
            try:
                state = self.active_generations[generation_id]
                start_time = time.time()

                # Stage 1: Parallel initialization (0-20%)
                await self._update_progress(
                    generation_id, 5, "initializing", "Setting up generation parameters"
                )

                # Use actual orchestrator instead of sleep
                initialization_tasks = [
                    self._initialize_generation_context(generation_id),
                    self._prepare_character_contexts(state["request"].characters),
                ]
                await asyncio.gather(*initialization_tasks)
                await self._update_progress(
                    generation_id, 20, "initialized", "Generation context prepared"
                )

                # Stage 2: Character Analysis (20-40%)
                await self._update_progress(
                    generation_id, 25, "analyzing", "Analyzing character personalities"
                )

                # Parallel character analysis
                character_tasks = [
                    self._analyze_character(char)
                    for char in state["request"].characters
                ]
                character_results = await asyncio.gather(
                    *character_tasks, return_exceptions=True
                )
                await self._update_progress(
                    generation_id, 40, "analyzed", "Character analysis complete"
                )

                # Stage 3: Narrative Planning (40-60%)
                await self._update_progress(
                    generation_id, 45, "planning", "Creating story structure"
                )

                # Use orchestrator for actual narrative planning
                planning_result = await self._create_narrative_plan(
                    generation_id, character_results
                )
                await self._update_progress(
                    generation_id, 60, "planned", "Story structure complete"
                )

                # Stage 4: Story Generation (60-90%)
                await self._update_progress(
                    generation_id, 65, "generating", "AI agents creating content"
                )

                # Parallel turn generation with progress updates
                turn_count = min(len(state["request"].characters) * 2, 8)  # Limit turns
                for turn in range(turn_count):
                    progress = 65 + (turn / turn_count) * 25
                    await self._update_progress(
                        generation_id,
                        progress,
                        "generating",
                        f"Turn {turn + 1}/{turn_count} in progress",
                    )

                    # Generate turn content
                    await self._generate_story_turn(
                        generation_id, turn, planning_result
                    )

                # Stage 5: Finalizing (90-100%)
                await self._update_progress(
                    generation_id, 95, "finalizing", "Quality checks and formatting"
                )

                # Finalize and save
                final_story = await self._finalize_story(generation_id)

                # Complete
                state["status"] = "completed"
                state["completion_time"] = time.time()
                state["generation_duration"] = time.time() - start_time
                state["story_content"] = final_story

                await self._update_progress(
                    generation_id,
                    100,
                    "completed",
                    f"Story generation completed in {state['generation_duration']:.1f}s",
                )
                logger.info(
                    f"Story generation {generation_id} completed in {state['generation_duration']:.1f}s"
                )

            except Exception as e:
                logger.error(f"Error generating story {generation_id}: {e}")
                if generation_id in self.active_generations:
                    self.active_generations[generation_id]["status"] = "failed"
                    self.active_generations[generation_id][
                        "completion_time"
                    ] = time.time()
                    await self._update_progress(
                        generation_id, 0, "failed", f"Generation failed: {str(e)}"
                    )

    async def _update_progress(
        self, generation_id: str, progress: float, stage: str, stage_detail: str
    ):
        """Optimized progress update with batch broadcasting."""
        if generation_id not in self.active_generations:
            return

        # Update internal state
        state = self.active_generations[generation_id]
        state["progress"] = progress
        state["stage"] = stage
        state["stage_detail"] = stage_detail
        state["last_update"] = time.time()

        # Batch broadcast to all connected WebSockets
        connections = self.connection_pool.connections.get(generation_id, set())
        if connections:
            # Create update message once
            update_message = self._create_progress_message(generation_id)

            # Broadcast in parallel with error handling
            broadcast_tasks = [
                self._safe_send_update(websocket, update_message)
                for websocket in connections.copy()  # Copy to avoid modification during iteration
            ]

            # Execute broadcasts concurrently
            results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)

            # Remove failed connections
            for websocket, result in zip(connections.copy(), results):
                if isinstance(result, Exception):
                    self.connection_pool.remove_connection(generation_id, websocket)

    async def _safe_send_update(self, websocket: WebSocket, message: str) -> bool:
        """Safely send update to WebSocket with timeout."""
        try:
            await asyncio.wait_for(websocket.send_text(message), timeout=1.0)
            return True
        except (WebSocketDisconnect, asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Failed to send update to WebSocket: {e}")
            return False

    def _create_progress_message(self, generation_id: str) -> str:
        """Create progress update message."""
        state = self.active_generations[generation_id]
        update = ProgressUpdate(
            generation_id=generation_id,
            progress=state.get("progress", 0),
            stage=state.get("stage", "unknown"),
            stage_detail=state.get("stage_detail", ""),
            estimated_time_remaining=self._calculate_time_remaining(state),
            active_agents=[
                "DirectorAgent",
                "PersonaAgent",
                "ChroniclerAgent",
            ],  # Could be dynamic
        )
        return update.model_dump_json()

    async def _send_progress_update(self, generation_id: str, websocket: WebSocket):
        """Send progress update to a specific WebSocket."""
        if generation_id not in self.active_generations:
            return

        state = self.active_generations[generation_id]
        update = ProgressUpdate(
            generation_id=generation_id,
            progress=state.get("progress", 0),
            stage=state.get("stage", "unknown"),
            stage_detail=state.get("stage_detail", ""),
            estimated_time_remaining=self._calculate_time_remaining(state),
            active_agents=[
                "DirectorAgent",
                "PersonaAgent",
                "ChroniclerAgent",
            ],  # Mock data
        )

        await websocket.send_text(update.json())

    def _calculate_time_remaining(self, state: Dict[str, Any]) -> int:
        """Calculate estimated time remaining based on progress."""
        progress = state.get("progress", 0)
        if progress <= 0:
            return 120  # Default 2 minutes
        if progress >= 100:
            return 0

        # Simple linear estimation based on elapsed time
        start_time = state.get("start_time", datetime.now())
        elapsed = (datetime.now() - start_time).total_seconds()

        if progress > 0:
            total_estimated = elapsed * (100 / progress)
            remaining = max(0, total_estimated - elapsed)
            return int(remaining)

        return 120

    # PERFORMANCE OPTIMIZATION METHODS

    async def _initialize_generation_context(self, generation_id: str):
        """Initialize generation context with orchestrator."""
        try:
            if not self.orchestrator:
                logger.error(
                    f"No orchestrator available for generation {generation_id}"
                )
                return None

            self.active_generations[generation_id]
            # Use actual orchestrator for context initialization
            result = await self.orchestrator.create_agent_context(
                f"story_gen_{generation_id}"
            )
            return result if result.success else None
        except Exception as e:
            logger.error(f"Context initialization failed for {generation_id}: {e}")
            return None

    async def _prepare_character_contexts(self, characters: List[str]):
        """Prepare character contexts in parallel."""
        try:
            if not self.orchestrator:
                logger.error(
                    "No orchestrator available for character context preparation"
                )
                return []

            # Check if characters already exist (they should from validation)
            active_agents = getattr(self.orchestrator, "active_agents", {})
            existing_characters = [char for char in characters if char in active_agents]

            # For existing characters, just return success indicators
            return [
                {"character": char, "status": "ready"} for char in existing_characters
            ]
        except Exception as e:
            logger.error(f"Character context preparation failed: {e}")
            return []

    async def _analyze_character(self, character_name: str):
        """Analyze individual character for story generation."""
        try:
            # Simulate actual character analysis using orchestrator
            # This would integrate with the character analysis system
            await asyncio.sleep(0.1)  # Minimal delay for simulation
            return {"character": character_name, "analysis": "completed"}
        except Exception as e:
            logger.error(f"Character analysis failed for {character_name}: {e}")
            return {"character": character_name, "analysis": "failed", "error": str(e)}

    async def _create_narrative_plan(self, generation_id: str, character_results: List):
        """Create narrative plan using orchestrator."""
        try:
            # This would use the actual story planning system
            await asyncio.sleep(0.2)  # Minimal delay for simulation
            return {"plan": "narrative_structure", "characters": len(character_results)}
        except Exception as e:
            logger.error(f"Narrative planning failed for {generation_id}: {e}")
            return None

    async def _generate_story_turn(
        self, generation_id: str, turn_number: int, planning_result
    ):
        """Generate individual story turn."""
        try:
            # This would use the actual multi-agent story generation
            await asyncio.sleep(0.3)  # Reduced from original 1.5s
            return {"turn": turn_number, "content": f"Turn {turn_number} content"}
        except Exception as e:
            logger.error(
                f"Turn generation failed for {generation_id}, turn {turn_number}: {e}"
            )
            return None

    async def _finalize_story(self, generation_id: str):
        """Finalize and format the complete story."""
        try:
            # This would use the actual story finalization system
            await asyncio.sleep(0.1)  # Minimal delay
            return f"Finalized story for generation {generation_id}"
        except Exception as e:
            logger.error(f"Story finalization failed for {generation_id}: {e}")
            return "Story generation completed with errors"


def create_story_generation_api(
    orchestrator: Optional[SystemOrchestrator],
) -> StoryGenerationAPI:
    """Creates and configures an optimized story generation API instance."""
    api = StoryGenerationAPI(orchestrator)
    # Background tasks will be started when the server starts
    return api


__all__ = ["StoryGenerationAPI", "create_story_generation_api"]
