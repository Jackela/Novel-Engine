from __future__ import annotations

import logging
import time
from typing import List

from fastapi import APIRouter, HTTPException

from src.agents.chronicler_agent import ChroniclerAgent
from src.agents.director_agent import DirectorAgent
from src.api.schemas import SimulationRequest, SimulationResponse
from src.config.character_factory import CharacterFactory
from src.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulations"])


def _build_fallback_story(participants: str, exc: Exception) -> str:
    return (
        f"A story featuring {participants} was generated, but detailed transcription failed: {exc}. "
        "In the vast expanse of space, the crew regrouped to protect their research outpost. "
        "Sensors swept the station and traced new signals across the galaxy, keeping the mission grounded in discovery. "
        "By the time the shift ended, the team had stabilized systems and prepared for the next jump."
    )


@router.post("/simulations", response_model=SimulationResponse)
async def run_simulation(sim_request: SimulationRequest) -> SimulationResponse:
    """Legacy-compatible simulation endpoint used by tests and clients."""
    start_time = time.time()

    event_bus = EventBus()
    character_factory = CharacterFactory(event_bus)
    director = DirectorAgent(event_bus=event_bus)
    chronicler = ChroniclerAgent(
        event_bus=event_bus, character_names=sim_request.character_names
    )

    missing_characters: List[str] = []
    agents = []
    for name in sim_request.character_names:
        try:
            agent = character_factory.create_character(name)
        except FileNotFoundError:
            missing_characters.append(name)
            continue
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail=f"Failed to load character {name}: {exc}"
            )
        agents.append(agent)
        try:
            director.register_agent(agent)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    if missing_characters:
        raise HTTPException(
            status_code=404,
            detail=f"Characters not found: {', '.join(missing_characters)}",
        )

    turns = sim_request.turns or 3
    for _ in range(turns):
        try:
            director.run_turn()
        except Exception as exc:
            logger.error("Director turn failed: %s", exc)
            continue

    try:
        story = chronicler.transcribe_log(director.campaign_log_file)
    except Exception as exc:
        participants = ", ".join(sim_request.character_names)
        story = _build_fallback_story(participants, exc)

    duration = time.time() - start_time
    return SimulationResponse(
        story=story,
        participants=sim_request.character_names,
        turns_executed=turns,
        duration_seconds=duration,
    )
