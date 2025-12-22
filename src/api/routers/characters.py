from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile

from src.api.deps import require_workspace_id
from src.api.schemas import (
    CharacterDetailResponse,
    CharactersListResponse,
    WorkspaceCharacterCreateRequest,
    WorkspaceCharacterUpdateRequest,
)
from src.api.services.paths import get_characters_directory_path
from src.config.character_factory import CharacterFactory
from src.event_bus import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["characters"])

_CHARACTER_ID_SLUG_RE = re.compile(r"[^a-z0-9_-]+")
_CHARACTER_DIRNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _normalize_character_id(value: str) -> str:
    raw_value = (value or "").strip().replace("\\", "/")
    raw_value = os.path.basename(raw_value)
    normalized = _CHARACTER_ID_SLUG_RE.sub("_", raw_value.lower()).strip("_")
    if not normalized or normalized in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid character name")
    return normalized


def _structured_defaults(
    name: str,
    specialization: str = "Unknown",
    faction: str = "Independent",
) -> Dict[str, Any]:
    return {
        "stats": {
            "character": {
                "name": name,
                "specialization": specialization,
                "faction": faction,
            }
        },
        "combat_stats": {},
        "equipment": {"items": []},
    }


async def get_characters() -> CharactersListResponse:
    """Retrieves a list of available characters."""
    try:
        characters_path = get_characters_directory_path()
        logger.info("Looking for characters in: %s", characters_path)

        if not os.path.isdir(characters_path):
            logger.warning("Characters directory not found at: %s", characters_path)
            os.makedirs(characters_path, exist_ok=True)

        characters: Set[str] = set()
        if os.path.isdir(characters_path):
            for item in os.listdir(characters_path):
                item_path = os.path.join(characters_path, item)
                if os.path.isdir(item_path):
                    characters.add(item)
                    logger.debug("Found character directory: %s", item)

        sorted_characters = sorted(characters)
        logger.info("Found %d characters: %s", len(sorted_characters), sorted_characters)
        return CharactersListResponse(characters=sorted_characters)
    except FileNotFoundError as exc:
        logger.error("File not found error: %s", exc)
        raise HTTPException(status_code=404, detail="Characters directory not found.")
    except PermissionError as exc:
        logger.error("Permission error accessing characters: %s", exc)
        raise HTTPException(
            status_code=500, detail="Permission denied accessing characters directory."
        )
    except Exception as exc:
        logger.error("Unexpected error retrieving characters: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve characters: {exc}")


@router.get("/characters", response_model=CharactersListResponse)
async def get_characters_endpoint() -> CharactersListResponse:
    return await get_characters()


@router.post("/characters", response_model=CharacterDetailResponse)
async def create_character(
    name: str = Form(...),
    description: str = Form(...),
    faction: Optional[str] = Form("Independent"),
    role: Optional[str] = Form("Unknown"),
    stats: Optional[str] = Form(None),
    equipment: Optional[str] = Form(None),
    files: List[UploadFile] = File(None),
) -> CharacterDetailResponse:
    """Creates a new character."""
    try:
        characters_path = get_characters_directory_path()
        os.makedirs(characters_path, exist_ok=True)

        try:
            stats_data = json.loads(stats) if stats else {}
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid stats JSON: {exc}") from exc

        try:
            equipment_data = json.loads(equipment) if equipment else []
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid equipment JSON: {exc}") from exc

        character_id = uuid.uuid4().hex
        character_path = os.path.join(characters_path, character_id)
        while os.path.exists(character_path):
            character_id = uuid.uuid4().hex
            character_path = os.path.join(characters_path, character_id)

        os.makedirs(character_path, exist_ok=False)

        profile_content = f"""# {name}

## Overview
**Role:** {role}
**Faction:** {faction}

{description}

## Stats
{json.dumps(stats_data, indent=2)}

## Equipment
{json.dumps(equipment_data, indent=2)}
"""
        markdown_filename = f"character_{character_id}.md"
        with open(os.path.join(character_path, markdown_filename), "w", encoding="utf-8") as handle:
            handle.write(profile_content)

        if files:
            uploads_dir = os.path.join(character_path, "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            for file in files:
                upload_id = uuid.uuid4().hex
                file_path = os.path.join(uploads_dir, f"upload_{upload_id}.bin")
                with open(file_path, "wb") as handle:
                    content = await file.read()
                    handle.write(content)

        logger.info("Created character")

        return CharacterDetailResponse(
            character_id=character_id,
            character_name=character_id,
            name=name,
            background_summary=description,
            personality_traits="Unknown",
            current_status="Active",
            narrative_context="Newly created character",
            skills=stats_data,
            inventory=[item.get("name", "Unknown") for item in equipment_data],
            metadata={"role": role, "faction": faction},
            structured_data={
                "stats": {
                    "character": {"name": name, "faction": faction, "specialization": role}
                },
                "combat_stats": stats_data,
                "equipment": {"items": equipment_data},
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create character: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create character: {exc}")


@router.get("/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail(character_id: str) -> CharacterDetailResponse:
    """Retrieves detailed information about a specific character."""
    try:
        raw_character_id = (character_id or "").strip()
        safe_character_id = os.path.basename(raw_character_id)
        if (
            not safe_character_id
            or safe_character_id in {".", ".."}
            or safe_character_id != raw_character_id
            or not _CHARACTER_DIRNAME_RE.fullmatch(safe_character_id)
        ):
            raise HTTPException(status_code=400, detail="Invalid character_id")

        try:
            event_bus = EventBus()
            character_factory = CharacterFactory(event_bus)
            agent = character_factory.create_character(safe_character_id)
            character = agent.character

            structured = getattr(character, "structured_data", None)
            if not structured:
                structured = _structured_defaults(
                    getattr(character, "name", character_id),
                    getattr(character, "specialization", "Unknown"),
                    getattr(character, "faction", "Independent"),
                )

            return CharacterDetailResponse(
                character_id=safe_character_id,
                character_name=safe_character_id,
                name=character.name,
                background_summary=getattr(character, "background_summary", "No background available"),
                personality_traits=getattr(
                    character,
                    "personality_traits",
                    "No personality traits available",
                ),
                current_status=getattr(character, "current_status", "Unknown"),
                narrative_context=getattr(character, "narrative_context", "No narrative context"),
                skills=getattr(character, "skills", {}),
                relationships=getattr(character, "relationships", {}),
                current_location=getattr(character, "current_location", "Unknown"),
                inventory=getattr(character, "inventory", []),
                metadata=getattr(character, "metadata", {}),
                structured_data=structured,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Character '{safe_character_id}' not found")
        except Exception:
            logger.error("Error loading character", exc_info=True)
            structured = _structured_defaults(safe_character_id.replace("_", " ").title(), "Unknown")
            return CharacterDetailResponse(
                character_id=safe_character_id,
                character_name=safe_character_id,
                name=safe_character_id.replace("_", " ").title(),
                background_summary="Character data could not be loaded",
                personality_traits="Unknown",
                current_status="Data unavailable",
                narrative_context="Character files could not be parsed",
                structured_data=structured,
            )

    except HTTPException:
        raise
    except Exception:
        logger.error("Unexpected error retrieving character", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve character details")


@router.get("/characters/{character_id}/enhanced")
async def get_character_enhanced(character_id: str) -> Dict[str, Any]:
    """Retrieves enhanced character context and analysis data."""
    try:
        raw_character_id = (character_id or "").strip()
        safe_character_id = os.path.basename(raw_character_id)
        if (
            not safe_character_id
            or safe_character_id in {".", ".."}
            or safe_character_id != raw_character_id
            or not _CHARACTER_DIRNAME_RE.fullmatch(safe_character_id)
        ):
            raise HTTPException(status_code=400, detail="Invalid character_id")

        event_bus = EventBus()
        character_factory = CharacterFactory(event_bus)
        try:
            agent = character_factory.create_character(safe_character_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Character not found")

        character_data = getattr(agent, "character_data", {}) or {}
        hybrid = character_data.get("hybrid_context", {}) if isinstance(character_data, dict) else {}
        enhanced_context = (
            hybrid.get("markdown_content")
            or getattr(agent, "character_context", "")
            or getattr(agent.character, "narrative_context", "")
            or ""
        )

        psychological_profile = (
            character_data.get("psychological_profile", {}) if isinstance(character_data, dict) else {}
        )

        tactical_analysis = {
            "combat_stats": character_data.get("combat_stats", {}) if isinstance(character_data, dict) else {},
            "decision_weights": character_data.get("decision_weights", {}) if isinstance(character_data, dict) else {},
            "relationship_scores": character_data.get("relationship_scores", {}) if isinstance(character_data, dict) else {},
        }

        return {
            "character_id": safe_character_id,
            "enhanced_context": enhanced_context,
            "psychological_profile": psychological_profile,
            "tactical_analysis": tactical_analysis,
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("Error retrieving enhanced character", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve enhanced character details")


def _get_optional_workspace_id(request: Request) -> Optional[str]:
    manager = getattr(request.app.state, "guest_session_manager", None)
    store = getattr(request.app.state, "workspace_store", None)
    if not manager or not store:
        return None
    token = request.cookies.get(manager.cookie_name)
    if not token:
        return None
    workspace_id = manager.decode(token)
    if not workspace_id:
        return None
    store.get_or_create(workspace_id)
    return workspace_id


def _workspace_record_to_character_detail(record: Dict[str, Any]) -> CharacterDetailResponse:
    char_id = str(record.get("id") or "")
    char_name = str(record.get("name") or char_id)
    inventory = record.get("inventory")
    if not isinstance(inventory, list):
        inventory = []
    skills = record.get("skills")
    if not isinstance(skills, dict):
        skills = {}
    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        relationships = {}
    metadata = record.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    structured_data = record.get("structured_data")
    if not isinstance(structured_data, dict):
        structured_data = {}

    return CharacterDetailResponse(
        character_id=char_id,
        character_name=char_name,
        name=char_name,
        background_summary=str(record.get("background_summary") or ""),
        personality_traits=str(record.get("personality_traits") or ""),
        current_status=str(record.get("current_status") or "active"),
        narrative_context=str(record.get("narrative_context") or ""),
        skills=skills,
        relationships=relationships,
        current_location=str(record.get("current_location") or ""),
        inventory=inventory,
        metadata=metadata,
        structured_data=structured_data,
    )


@router.get("/api/characters", response_model=CharactersListResponse)
async def get_characters_api(request: Request) -> CharactersListResponse:
    defaults = (await get_characters()).characters
    workspace_id = _get_optional_workspace_id(request)
    workspace_chars: List[str] = []
    store = getattr(request.app.state, "workspace_character_store", None)
    if workspace_id and store:
        try:
            workspace_chars = store.list_ids(workspace_id)
        except Exception:
            workspace_chars = []
    return CharactersListResponse(characters=sorted({*defaults, *workspace_chars}))


@router.get("/api/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail_api(character_id: str, request: Request) -> CharacterDetailResponse:
    workspace_id = _get_optional_workspace_id(request)
    store = getattr(request.app.state, "workspace_character_store", None)
    if workspace_id and store:
        try:
            record = store.get(workspace_id, character_id)
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        if record:
            return _workspace_record_to_character_detail(record)
    return await get_character_detail(character_id)


@router.post("/api/characters", response_model=CharacterDetailResponse, status_code=201)
async def create_workspace_character(
    request: Request,
    response: Response,
    payload: WorkspaceCharacterCreateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterDetailResponse:
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    requested_id = payload.agent_id or _normalize_character_id(payload.name)
    character_id = _normalize_character_id(requested_id)

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

    candidate = character_id
    suffix = 2
    while store.get(workspace_id, candidate):
        candidate = f"{character_id}_{suffix}"
        suffix += 1
    character_id = candidate

    try:
        record = store.create(workspace_id, character_id, record_payload)
    except FileExistsError as err:
        raise HTTPException(status_code=409, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return _workspace_record_to_character_detail(record)


@router.put("/api/characters/{character_id}", response_model=CharacterDetailResponse)
async def update_workspace_character(
    character_id: str,
    request: Request,
    response: Response,
    updates: WorkspaceCharacterUpdateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterDetailResponse:
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")
    try:
        record = store.update(workspace_id, character_id, updates.dict(exclude_unset=True))
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return _workspace_record_to_character_detail(record)


@router.delete("/api/characters/{character_id}", status_code=204, response_class=Response)
async def delete_workspace_character(
    character_id: str,
    request: Request,
    response: Response,
    workspace_id: str = Depends(require_workspace_id),
) -> Response:
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")
    try:
        store.delete(workspace_id, character_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    return Response(status_code=204)


@router.get("/api/characters/{character_id}/enhanced")
async def get_character_enhanced_api(character_id: str) -> Dict[str, Any]:
    return await get_character_enhanced(character_id)
