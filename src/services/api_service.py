import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from src.agents.chronicler_agent import ChroniclerAgent
from src.agents.director_agent import DirectorAgent
from src.api.schemas import SimulationRequest

# Import legacy components for backward compatibility until fully replaced
from src.config.character_factory import CharacterFactory
from src.core.system_orchestrator import SystemOrchestrator
from src.event_bus import EventBus

logger = logging.getLogger(__name__)


class ApiOrchestrationService:
    """
    Service layer bridging the REST API (Imperative Shell) and the System Orchestrator (Functional Core).
    Manages the lifecycle of orchestration sessions requested via API.
    """

    def __init__(
        self,
        orchestrator: SystemOrchestrator,
        event_bus: EventBus,
        character_factory: Optional[CharacterFactory] = None,
    ):
        self.core = orchestrator
        self.event_bus = event_bus
        self.character_factory = character_factory or CharacterFactory(event_bus)
        self._orchestration_active = False
        self._orchestration_active = False
        self._stop_flag = False
        self._current_task: Optional[asyncio.Task] = None

        # Internal state tracking - replicating the legacy _orchestration_state for compatible API responses
        self._state = {
            "current_turn": 0,
            "total_turns": 0,
            "queue_length": 0,
            "average_processing_time": 0.0,
            "status": "idle",
            "steps": [],
            "last_updated": None,
        }
        self._narrative = {
            "story": "",
            "log_path": "",
            "participants": [],
            "turns_completed": 0,
            "last_generated": None,
        }

    async def start_simulation(self, request: SimulationRequest) -> Dict[str, Any]:
        """Start a new simulation in the background."""
        if self._orchestration_active:
            raise ValueError("Simulation already running")

        self._orchestration_active = True
        self._stop_flag = False
        self._state["status"] = "running"
        self._state["total_turns"] = request.turns or 3

        # Launch background task
        self._current_task = asyncio.create_task(
            self._run_orchestration_loop(request.character_names, request.turns or 3)
        )

        return {"success": True, "status": "started", "task_id": str(uuid.uuid4())}

    async def stop_simulation(self) -> Dict[str, Any]:
        """Stop the current simulation."""
        if not self._orchestration_active:
            return {"success": False, "message": "No simulation running"}

        self._stop_flag = True
        # Wait for task to finish if needed, or just let it pick up the flag
        self._state["status"] = "stopping"
        return {"success": True, "status": "stopping"}

    async def pause_simulation(self) -> Dict[str, Any]:
        """Pause the current simulation."""
        if not self._orchestration_active:
            return {"success": False, "message": "No simulation running"}

        if self._state["status"] == "paused":
            return {"success": False, "message": "Simulation is already paused"}

        self._state["status"] = "paused"
        logger.info("Simulation paused")
        return {"success": True, "status": "paused", "message": "Simulation paused successfully"}

    async def get_status(self) -> Dict[str, Any]:
        """Get current orchestration status."""
        return self._state

    async def get_narrative(self) -> Dict[str, Any]:
        """Get generated narrative."""
        return self._narrative

    async def _run_orchestration_loop(
        self, character_names: List[str], total_turns: int
    ):
        """
        Main orchestration loop.
        Refactored from api_server.py to use async/await and proper service isolation.
        """
        logger.info(f"Starting orchestration service loop: {character_names}")

        try:
            # 1. Initialize Components
            # Use injected factory (allows mocking)
            agents = []

            # 2. Create Agents
            for name in character_names:
                try:
                    agent = self.character_factory.create_character(name)
                    agents.append(agent)
                    await self._broadcast_sse(
                        "character", f"Agent Created: {name}", f"Initialized {name}", "low"
                    )
                except FileNotFoundError:
                    logger.error(f"Character '{name}' not found in characters directory")
                    await self._broadcast_sse(
                        "system", f"Character Not Found: {name}", f"Skipping '{name}' - file not found", "high"
                    )
                    continue
                except Exception as e:
                    logger.error(f"Failed to create agent '{name}': {e}", exc_info=True)
                    await self._broadcast_sse(
                        "system", f"Agent Creation Failed: {name}", str(e), "high"
                    )
                    continue

            # Check if we have at least one agent
            if not agents:
                raise ValueError("No valid agents could be created. Please check character names and character files.")

            # 3. Setup Director
            log_path = f"logs/orchestration_{uuid.uuid4().hex[:8]}.md"
            import os

            os.makedirs("logs", exist_ok=True)

            # NOTE: DirectorAgent is still synchronous in parts, need to wrap or expect blocking
            # Ideally we would use self.core.orchestrate_multi_agent_interaction here
            # But to maintain exact behavior of the legacy code, we use DirectorAgent for now
            # wrapping it to not block the event loop
            director = DirectorAgent(self.event_bus, campaign_log_path=log_path)
            for agent in agents:
                director.register_agent(agent)

            self._state["queue_length"] = len(agents)
            self._narrative["participants"] = character_names
            self._narrative["log_path"] = log_path

            await self._broadcast_sse(
                "system",
                "Orchestration Started",
                "Beginning story generation",
                "medium",
            )

            # 4. Turn Loop
            turn_times = []
            for turn_num in range(1, total_turns + 1):
                # Check for stop flag
                if self._stop_flag:
                    logger.info("Orchestration stopped by user request")
                    break

                # Check for pause - wait while paused
                while self._state["status"] == "paused":
                    await asyncio.sleep(0.5)
                    # Allow stopping even when paused
                    if self._stop_flag:
                        logger.info("Orchestration stopped during pause")
                        break

                # Resume if we broke out of pause
                if self._stop_flag:
                    break

                # Resume running status if coming out of pause
                if self._state["status"] == "paused":
                    self._state["status"] = "running"

                turn_start_time = time.time()
                self._state["current_turn"] = turn_num

                await self._broadcast_sse(
                    "story",
                    f"Turn {turn_num}/{total_turns}",
                    f"Processing turn {turn_num}",
                    "low",
                )

                # Run turn (offload to thread if blocking)
                await asyncio.to_thread(director.run_turn)

                duration = time.time() - turn_start_time
                turn_times.append(duration)
                self._state["average_processing_time"] = sum(turn_times) / len(
                    turn_times
                )
                self._narrative["turns_completed"] = turn_num

                await self._broadcast_sse(
                    "story",
                    f"Turn {turn_num} Completed",
                    f"Finished in {duration:.2f}s",
                    "low",
                )

            # 5. Finalize
            self._state["status"] = "completed" if not self._stop_flag else "stopped"

            await self._broadcast_sse(
                "story", "Generating Narrative", "Finalizing story...", "medium"
            )

            # Generate Narrative
            chronicler = ChroniclerAgent(
                self.event_bus, character_names=character_names
            )
            story = await asyncio.to_thread(chronicler.transcribe_log, log_path)

            self._narrative["story"] = story
            self._narrative["last_generated"] = datetime.now(UTC).isoformat()

            await self._broadcast_sse(
                "story", "Narrative Complete", "Story generation finished", "high"
            )

        except Exception as e:
            logger.error(f"Orchestration loop error: {e}", exc_info=True)
            self._state["status"] = "error"
            await self._broadcast_sse("system", "Orchestration Error", str(e), "high")
        finally:
            self._orchestration_active = False

    async def _broadcast_sse(
        self, event_type: str, title: str, description: str, severity: str
    ):
        """Helper to emit SSE events via EventBus."""
        if self.event_bus:
            # Publish to the topic that api_server.py's bridge subscribes to
            await self.event_bus.publish(
                "dashboard_event",
                type=event_type,
                title=title,
                description=description,
                severity=severity,
            )
        else:
            logger.warning(f"No EventBus available to broadcast: {title}")
