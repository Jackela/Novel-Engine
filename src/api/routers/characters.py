from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)

from src.api.deps import get_optional_workspace_id, require_workspace_id
from src.api.schemas import (
    CharacterDetailResponse,
    CharactersListResponse,
    CharacterSummary,
    WorkspaceCharacterCreateRequest,
    WorkspaceCharacterUpdateRequest,
)
from src.api.services.character_router_service import CharacterRouterService
from src.api.services.http_cache_service import HttpCacheService
from src.api.services.paths import get_characters_directory_path
from src.config.character_factory import CharacterFactory
from src.core.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["characters"])


async def get_character_detail(
    character_id: str, event_bus: Optional[EventBus] = None
) -> CharacterDetailResponse:
    """
    Retrieve character details from the filesystem for the public catalog.

    Why: Separated from route handler for testability and reusability.

    Args:
        character_id: Safe character ID
        event_bus: Optional event bus for CharacterFactory

    Returns:
        Character detail response

    Raises:
        HTTPException: If character not found
    """
    characters_path = get_characters_directory_path()
    service = CharacterRouterService(characters_path)
    safe_character_id = character_id

    base_dir = Path(characters_path).resolve()
    if not base_dir.is_dir():
        raise HTTPException(
            status_code=404, detail=f"Character '{safe_character_id}' not found"
        )

    character_dir = next(
        (
            item
            for item in base_dir.iterdir()
            if item.is_dir() and item.name == safe_character_id
        ),
        None,
    )
    if character_dir is None:
        raise HTTPException(
            status_code=404, detail=f"Character '{safe_character_id}' not found"
        )

    character_file = character_dir / f"character_{character_dir.name}.md"
    stats_file = character_dir / "stats.yaml"

    character_name = safe_character_id
    display_name = safe_character_id.replace("_", " ").title()

    character_data = {
        "agent_id": safe_character_id,
        "character_id": safe_character_id,
        "character_name": character_name,
        "name": display_name,
        "background_summary": "Character loaded from file system",
        "personality_traits": "Based on character files",
        "current_status": "active",
        "narrative_context": "File-based character definition",
        "skills": {},
        "relationships": {},
        "current_location": "Unknown",
        "inventory": [],
        "metadata": {"source": "file_system"},
        "structured_data": {},
    }

    if os.path.exists(character_file):
        try:
            with open(character_file, "r", encoding="utf-8") as fh:
                content = fh.read()
                cleaned_content = content.strip()
                if cleaned_content:
                    character_data["narrative_context"] = cleaned_content
                for line in content.splitlines():
                    if line.startswith("# "):
                        character_data["name"] = line[2:].strip()
                        character_data["background_summary"] = line[2:].strip()
                    elif "background" in line.lower() or "summary" in line.lower():
                        character_data["background_summary"] = line.strip()
        except Exception:
            logger.warning("Could not parse character markdown file", exc_info=True)

    if os.path.exists(stats_file):
        try:
            import yaml

            with open(stats_file, "r", encoding="utf-8") as fh:
                stats = yaml.safe_load(fh)
                if isinstance(stats, dict):
                    character_data["skills"] = service.normalize_numeric_map(
                        stats.get("skills", {})
                    )
                    character_data["relationships"] = service.normalize_numeric_map(
                        stats.get("relationships", {})
                    )
                    character_data["metadata"].update(stats.get("metadata", {}))
                    character_data["structured_data"].update(
                        stats.get("structured_data", {})
                    )
                    character_data["structured_data"]["stats"] = stats
        except Exception:
            logger.warning("Could not parse character stats file", exc_info=True)

    try:
        bus = event_bus or EventBus()
        factory = CharacterFactory(bus)
        factory.create_character(safe_character_id)
    except Exception:
        logger.warning("CharacterFactory failed to load character.", exc_info=True)
        character_data["background_summary"] = (
            f"Character {safe_character_id} could not be loaded"
        )

    return CharacterDetailResponse(**character_data)


def _workspace_record_to_character_detail(
    record: Dict[str, Any],
) -> CharacterDetailResponse:
    """
    Convert a workspace record into the API response model.

    Why: Workspace records have a different structure than filesystem records.

    Args:
        record: Workspace character record

    Returns:
        Character detail response
    """
    character_name = record.get("name") or record.get("id") or ""
    return CharacterDetailResponse(
        agent_id=str(record.get("id", "")),
        character_id=str(record.get("id", "")),
        character_name=character_name,
        name=character_name,
        background_summary=record.get("background_summary", ""),
        personality_traits=record.get("personality_traits", ""),
        current_status=record.get("current_status", ""),
        narrative_context=record.get("narrative_context", ""),
        skills=record.get("skills") or {},
        relationships=record.get("relationships") or {},
        current_location=record.get("current_location", ""),
        inventory=record.get("inventory") or [],
        metadata=record.get("metadata") or {},
        structured_data=record.get("structured_data") or {},
    )


async def get_character_enhanced(character_id: str) -> Dict[str, Any]:
    """
    Return an enhanced/fantasy context for a character.

    Why: Special endpoint for enriched character context.
    """
    safe_id = (character_id or "").strip()
    display_name = safe_id.replace("_", " ").title()
    return {
        "character_id": safe_id,
        "enhanced_context": f"{display_name} is poised for a multi-layered tactical narrative.",
        "psychological_profile": {
            "stability": 0.85,
            "confidence": 0.92,
            "notes": "Methodical and resilient under pressure.",
        },
        "tactical_analysis": {
            "summary": "Standard patrol readiness.",
            "priority": "low",
        },
    }


async def _get_public_character_entries(
    service: Optional[CharacterRouterService] = None,
) -> List[Tuple[datetime, CharacterSummary]]:
    """
    Fetch public character entries via a patchable helper.

    Why: Error-handling tests patch this function to simulate database failures,
    and the indirection keeps that seam stable without changing route logic.
    """
    service = service or CharacterRouterService()
    return await service.get_public_character_entries()


# ==================== Route Handlers ====================


@router.get("/characters", response_model=CharactersListResponse)
async def get_characters_api(
    request: Request,
    response: Response,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharactersListResponse:
    """
    Retrieves a list of available characters (default + workspace).

    Why: Merges public and workspace characters into a single list.
    """
    characters_path = get_characters_directory_path()
    service = CharacterRouterService(characters_path)
    cache_service = HttpCacheService()

    public_entries = await _get_public_character_entries(service)
    workspace_entries: List[Tuple[datetime, CharacterSummary]] = []

    store = getattr(request.app.state, "workspace_character_store", None)
    if workspace_id and store:
        try:
            for char_id in store.list_ids(workspace_id):
                record = store.get(workspace_id, char_id)
                if record:
                    try:
                        summary, timestamp = service.summarize_workspace_character(
                            record, workspace_id
                        )
                        workspace_entries.append((timestamp, summary))
                    except ValueError:
                        logger.warning("Skipping malformed workspace character record.")
        except Exception:
            logger.warning("Failed to load workspace characters.", exc_info=True)

    merged: Dict[str, Tuple[datetime, CharacterSummary]] = {}
    for entry in public_entries:
        merged[entry[1].id] = entry
    for entry in workspace_entries:
        merged[entry[1].id] = entry

    sorted_entries = sorted(merged.values(), key=lambda pair: pair[0], reverse=True)
    sorted_summaries = [summary for _, summary in sorted_entries]
    latest_timestamp = max((timestamp for timestamp, _ in sorted_entries), default=None)

    etag = cache_service.build_collection_etag(sorted_summaries)
    cache_service.set_cache_headers(response, etag, latest_timestamp)

    if cache_service.is_not_modified(request, etag, latest_timestamp):
        return Response(status_code=304)

    return CharactersListResponse(characters=sorted_summaries)


@router.get("/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail_api(
    character_id: str,
    request: Request,
    response: Response,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterDetailResponse:
    """
    Retrieves detailed information about a specific character (supports workspace).

    Why: Check workspace first, then fall back to public catalog.
    """
    service = CharacterRouterService()
    cache_service = HttpCacheService()

    store = getattr(request.app.state, "workspace_character_store", None)

    if workspace_id and store:
        try:
            record = store.get(workspace_id, character_id)

        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        if record:
            try:
                _, timestamp = service.summarize_workspace_character(
                    record, workspace_id
                )
                etag = cache_service.build_etag(character_id, timestamp)
                cache_service.set_cache_headers(response, etag, timestamp)
            except ValueError:
                logger.warning(
                    "Malformed workspace character record, skipping cache headers"
                )
            return _workspace_record_to_character_detail(record)

    event_bus = getattr(request.app.state, "event_bus", None)
    safe_character_id = character_id
    _, _, _, updated_dt = service.gather_filesystem_character_info(safe_character_id)
    etag = cache_service.build_etag(safe_character_id, updated_dt)
    cache_service.set_cache_headers(response, etag, updated_dt)
    return await get_character_detail(safe_character_id, event_bus)


@router.post("/characters", response_model=CharacterDetailResponse, status_code=201)
async def create_workspace_character(
    request: Request,
    response: Response,
    payload: WorkspaceCharacterCreateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterDetailResponse:
    """
    Creates a new character in the current workspace.

    Why: Workspace characters are user-defined and stored separately from public catalog.
    """
    service = CharacterRouterService()

    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    requested_id = payload.agent_id
    character_id = service.normalize_character_id(requested_id)

    record_payload: Dict[str, Any] = {
        "name": payload.name.strip(),
        "background_summary": payload.background_summary.strip(),
        "personality_traits": payload.personality_traits.strip(),
        "skills": payload.skills or {},
        "relationships": payload.relationships or {},
        "current_location": payload.current_location or "",
        "inventory": payload.inventory or [],
        "metadata": payload.metadata or {},
        "structured_data": payload.structured_data or {},
        "current_status": "active",
        "narrative_context": "",
    }

    if store.get(workspace_id, character_id):
        raise HTTPException(
            status_code=409,
            detail=f"Character '{character_id}' already exists",
        )

    try:
        record = store.create(workspace_id, character_id, record_payload)

    except FileExistsError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is not None:
        try:
            orchestrator.active_agents[character_id] = datetime.now()
        except Exception:
            logger.debug(
                "Failed to register character with orchestrator.",
                exc_info=True,
            )

    return _workspace_record_to_character_detail(record)


@router.put("/characters/{character_id}", response_model=CharacterDetailResponse)
async def update_workspace_character(
    character_id: str,
    request: Request,
    response: Response,
    updates: WorkspaceCharacterUpdateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterDetailResponse:
    """
    Updates a character in the workspace.

    Why: Allows modification of user-defined character properties.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    try:
        record = store.update(
            workspace_id, character_id, updates.dict(exclude_unset=True)
        )

    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return _workspace_record_to_character_detail(record)


@router.delete("/characters/{character_id}", status_code=204, response_class=Response)
async def delete_workspace_character(
    character_id: str,
    request: Request,
    response: Response,
    workspace_id: str = Depends(require_workspace_id),
) -> Response:
    """
    Deletes a character from the workspace.

    Why: Removes user-defined characters; also unregisters from orchestrator if present.
    """
    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    try:
        store.delete(workspace_id, character_id)

    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is not None:
        try:
            orchestrator.active_agents.pop(character_id, None)
        except Exception:
            logger.debug(
                "Failed to unregister character from orchestrator.",
                exc_info=True,
            )

    return Response(status_code=204)


@router.get("/characters/{character_id}/enhanced")
async def get_character_enhanced_api(character_id: str) -> Dict[str, Any]:
    """
    Retrieves enhanced character context.

    Why: Provides enriched context for narrative generation.
    """
    return await get_character_enhanced(character_id)
