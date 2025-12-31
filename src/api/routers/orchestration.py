from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import SimulationRequest
from src.api.services.paths import get_characters_directory_path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["orchestration"])


@router.get("/api/orchestration/status")
async def get_orchestration_status(request: Request) -> Dict[str, Any]:
    api_service = getattr(request.app.state, "api_service", None)
    if not api_service:
        return {
            "success": False,
            "message": "Orchestration service not available",
            "data": {"status": "error"},
        }

    status = await api_service.get_status()
    return {"success": True, "data": status}


@router.post("/api/orchestration/start")
async def start_orchestration(
    request: Request, payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    api_service = getattr(request.app.state, "api_service", None)
    if not api_service:
        raise HTTPException(
            status_code=503, detail="Orchestration service not initialized"
        )

    params = payload or {}
    total_turns = params.get("total_turns", 3)
    character_names = params.get("character_names")

    if not character_names:
        try:
            characters_path = get_characters_directory_path()
            available_chars: Set[str] = set()
            p = Path(characters_path)
            if p.exists():
                for item in p.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        available_chars.add(item.name)
            character_names = sorted(list(available_chars))[:3]
            if not character_names:
                character_names = ["pilot", "scientist", "engineer"]
        except Exception as exc:
            logger.warning("Failed to fetch characters, using defaults: %s", exc)
            character_names = ["pilot", "scientist", "engineer"]

    sim_request = SimulationRequest(character_names=character_names, turns=total_turns)

    try:
        result = await api_service.start_simulation(sim_request)
        return result
    except ValueError:
        return {
            "success": False,
            "message": "Invalid orchestration request.",
            "data": await api_service.get_status(),
        }
    except Exception:
        logger.exception("Failed to start orchestration.")
        raise HTTPException(status_code=500, detail="Failed to start orchestration.")


@router.post("/api/orchestration/stop")
async def stop_orchestration(request: Request) -> Dict[str, Any]:
    api_service = getattr(request.app.state, "api_service", None)
    if not api_service:
        return {"success": False, "message": "Service unavailable"}
    return await api_service.stop_simulation()


@router.get("/api/orchestration/narrative")
async def get_narrative(request: Request) -> Dict[str, Any]:
    api_service = getattr(request.app.state, "api_service", None)
    if not api_service:
        return {"success": False, "data": {}}

    narrative = await api_service.get_narrative()
    return {
        "success": True,
        "data": {
            "story": narrative.get("story", ""),
            "participants": narrative.get("participants", []),
            "turns_completed": narrative.get("turns_completed", 0),
            "last_generated": narrative.get("last_generated"),
            "has_content": bool(narrative.get("story", "")),
        },
    }
