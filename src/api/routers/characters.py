from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
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
from src.api.services.paths import get_characters_directory_path
from src.config.character_factory import CharacterFactory
from src.core.event_bus import EventBus

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


def _require_public_character_id(value: str) -> str:
    raw_value = (value or "").strip().replace("\\", "/")
    safe_value = os.path.basename(raw_value)
    if (
        not safe_value
        or safe_value in {".", ".."}
        or safe_value != raw_value
        or not _CHARACTER_DIRNAME_RE.fullmatch(safe_value)
    ):
        raise HTTPException(status_code=400, detail="Invalid character_id")
    return safe_value


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


def _display_name_from_id(character_id: str) -> str:
    return " ".join(
        segment.capitalize()
        for segment in character_id.replace("-", " ").replace("_", " ").split()
    )


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None


def _infer_character_type_from_record(record: Dict[str, Any]) -> str:
    metadata = record.get("metadata") or {}
    structured = record.get("structured_data") or {}
    for key in ("role", "type"):
        candidate = metadata.get(key) or structured.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return metadata.get("classification") or structured.get("classification") or "npc"


def _gather_filesystem_character_info(
    character_id: str, characters_path: str
) -> Tuple[str, str, str, datetime]:
    safe_character_id = _require_public_character_id(character_id)
    base_dir = Path(characters_path).resolve()
    character_dir = next(
        (
            item
            for item in base_dir.iterdir()
            if item.is_dir() and item.name == safe_character_id
        ),
        None,
    )
    if character_dir is None:
        raise HTTPException(status_code=404, detail="Character not found")

    character_file = character_dir / f"character_{character_dir.name}.md"
    stats_file = character_dir / "stats.yaml"

    updated_ts: Optional[float] = None
    if character_dir.is_dir():
        updated_ts = max(updated_ts or 0.0, character_dir.stat().st_mtime)

    display_name = _display_name_from_id(character_dir.name)
    status = "active"
    type_value = "npc"

    if character_file.exists():
        updated_ts = max(updated_ts or 0.0, character_file.stat().st_mtime)
        try:
            with character_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    trimmed = line.strip()
                    if trimmed.startswith("# "):
                        display_name = trimmed[2:].strip() or display_name
                        if updated_ts is None:
                            updated_ts = character_file.stat().st_mtime
                        break
        except Exception:
            logger.debug("Failed to parse character markdown.", exc_info=True)

    if stats_file.exists():
        updated_ts = max(updated_ts or 0.0, stats_file.stat().st_mtime)
        try:
            import yaml

            with stats_file.open("r", encoding="utf-8") as fh:
                stats_payload = yaml.safe_load(fh)
                if isinstance(stats_payload, dict):
                    metadata = stats_payload.get("metadata", {}) or {}
                    structured = stats_payload.get("structured_data", {}) or {}
                    if isinstance(metadata, dict):
                        status_candidate = metadata.get(
                            "current_status"
                        ) or metadata.get("status")
                        if (
                            isinstance(status_candidate, str)
                            and status_candidate.strip()
                        ):
                            status = status_candidate.strip()
                        type_candidate = metadata.get("role") or metadata.get("type")
                        if isinstance(type_candidate, str) and type_candidate.strip():
                            type_value = type_candidate.strip().lower()
                    if isinstance(structured, dict):
                        type_candidate = structured.get("role") or structured.get(
                            "type"
                        )
                        if isinstance(type_candidate, str) and type_candidate.strip():
                            type_value = type_candidate.strip().lower()
        except Exception:
            logger.debug("Failed to parse stats.", exc_info=True)

    updated_dt = datetime.fromtimestamp(
        updated_ts or datetime.now(timezone.utc).timestamp(), tz=timezone.utc
    )
    return display_name, status.lower(), type_value, updated_dt


def _summarize_public_character(
    character_id: str, characters_path: str
) -> Tuple[CharacterSummary, datetime]:
    name, status, category, updated_dt = _gather_filesystem_character_info(
        character_id, characters_path
    )
    summary = CharacterSummary(
        id=character_id,
        agent_id=character_id,
        name=name,
        status=status,
        type=category,
        updated_at=updated_dt.isoformat(),
        workspace_id=None,
    )
    return summary, updated_dt


def _summarize_workspace_character(
    record: Dict[str, Any], workspace_id: str
) -> Tuple[CharacterSummary, datetime]:
    char_id = str(
        record.get("id")
        or record.get("character_id")
        or record.get("character_name")
        or ""
    ).strip()
    if not char_id:
        raise ValueError("Workspace record missing character identifier")

    name = str(
        record.get("name")
        or record.get("character_name")
        or _display_name_from_id(char_id)
    )
    status = str(
        record.get("current_status") or record.get("status") or "active"
    ).lower()
    type_value = _infer_character_type_from_record(record)

    updated_iso = str(record.get("updatedAt") or record.get("createdAt") or "")
    updated_dt = _parse_iso_datetime(updated_iso) or datetime.now(timezone.utc)

    summary = CharacterSummary(
        id=char_id,
        agent_id=char_id,
        name=name,
        status=status,
        type=type_value,
        updated_at=updated_dt.isoformat(),
        workspace_id=workspace_id,
    )
    return summary, updated_dt


def _build_characters_etag(summaries: List[CharacterSummary]) -> str:
    payload = [
        {
            "id": summary.id,
            "updated_at": summary.updated_at,
            "workspace_id": summary.workspace_id,
        }
        for summary in summaries
    ]
    serialized = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _set_cache_headers(
    response: Response, etag: str, latest: Optional[datetime]
) -> None:
    response.headers["ETag"] = f'"{etag}"'
    if latest:
        try:
            response.headers["Last-Modified"] = format_datetime(latest, usegmt=True)
        except Exception:
            response.headers["Last-Modified"] = format_datetime(latest)


def _build_entity_etag(identifier: str, updated: datetime) -> str:
    payload = f"{identifier}:{updated.isoformat()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _apply_entity_cache_headers(
    response: Response, identifier: str, updated: datetime
) -> None:
    etag = _build_entity_etag(identifier, updated)
    _set_cache_headers(response, etag, updated)


def _etag_matches(request_etag: str, current_etag: str) -> bool:
    tokens = [token.strip().strip('"') for token in request_etag.split(",")]
    return current_etag in tokens


def _is_not_modified(request: Request, etag: str, latest: Optional[datetime]) -> bool:
    client_etag = request.headers.get("if-none-match")
    if client_etag and _etag_matches(client_etag, etag):
        return True

    client_since = request.headers.get("if-modified-since")
    if client_since and latest:
        since_dt = _parse_iso_datetime(client_since)
        if since_dt and since_dt >= latest:
            return True

    return False


async def _get_public_character_entries() -> List[Tuple[datetime, CharacterSummary]]:
    try:
        characters_path = get_characters_directory_path()
        logger.info("Loading public characters from: %s", characters_path)

        os.makedirs(characters_path, exist_ok=True)

        entries: List[Tuple[datetime, CharacterSummary]] = []
        for item in os.listdir(characters_path):
            item_path = os.path.join(characters_path, item)
            if not os.path.isdir(item_path):
                continue
            if not _CHARACTER_DIRNAME_RE.fullmatch(item):
                continue
            summary, timestamp = _summarize_public_character(item, characters_path)
            entries.append((timestamp, summary))
        return entries
    except FileNotFoundError as exc:
        logger.error("Characters directory missing: %s", exc)
        raise HTTPException(status_code=404, detail="Characters directory not found.")
    except PermissionError as exc:
        logger.error("Permission denied reading characters: %s", exc)
        raise HTTPException(
            status_code=500, detail="Permission denied accessing characters directory."
        )
    except Exception as exc:
        logger.error("Unexpected error loading characters: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve characters: {exc}"
        )


@router.get("/characters", response_model=CharactersListResponse)
async def get_characters_api(
    request: Request,
    response: Response,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharactersListResponse:
    """Retrieves a list of available characters (default + workspace)."""

    public_entries = await _get_public_character_entries()
    workspace_entries: List[Tuple[datetime, CharacterSummary]] = []

    store = getattr(request.app.state, "workspace_character_store", None)
    if workspace_id and store:
        try:
            for char_id in store.list_ids(workspace_id):
                record = store.get(workspace_id, char_id)
                if record:
                    try:
                        summary, timestamp = _summarize_workspace_character(
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

    etag = _build_characters_etag(sorted_summaries)
    _set_cache_headers(response, etag, latest_timestamp)

    if _is_not_modified(request, etag, latest_timestamp):
        return Response(status_code=304)

    return CharactersListResponse(characters=sorted_summaries)


@router.get("/characters/{character_id}", response_model=CharacterDetailResponse)
async def get_character_detail_api(
    character_id: str,
    request: Request,
    response: Response,
    workspace_id: Optional[str] = Depends(get_optional_workspace_id),
) -> CharacterDetailResponse:
    """Retrieves detailed information about a specific character (supports workspace)."""

    store = getattr(request.app.state, "workspace_character_store", None)

    if workspace_id and store:
        try:
            record = store.get(workspace_id, character_id)

        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err

        if record:
            try:
                _, timestamp = _summarize_workspace_character(record, workspace_id)
                _apply_entity_cache_headers(response, character_id, timestamp)
            except ValueError:
                logger.warning(
                    "Malformed workspace character record, skipping cache headers"
                )
            return _workspace_record_to_character_detail(record)

    event_bus = getattr(request.app.state, "event_bus", None)
    characters_path = get_characters_directory_path()
    safe_character_id = _require_public_character_id(character_id)
    _, _, _, updated_dt = _gather_filesystem_character_info(
        safe_character_id, characters_path
    )
    _apply_entity_cache_headers(response, safe_character_id, updated_dt)
    return await get_character_detail(safe_character_id, event_bus)


@router.post("/characters", response_model=CharacterDetailResponse, status_code=201)
async def create_workspace_character(
    request: Request,
    response: Response,
    payload: WorkspaceCharacterCreateRequest,
    workspace_id: str = Depends(require_workspace_id),
) -> CharacterDetailResponse:
    """Creates a new character in the current workspace."""

    store = getattr(request.app.state, "workspace_character_store", None)

    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")

    requested_id = payload.agent_id
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
    """Updates a character in the workspace."""

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
    """Deletes a character from the workspace."""

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


async def get_character_enhanced(character_id: str) -> Dict[str, Any]:
    """Return an enhanced/fantasy context for a character."""

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


@router.get("/characters/{character_id}/enhanced")
async def get_character_enhanced_api(character_id: str) -> Dict[str, Any]:
    """Retrieves enhanced character context."""

    return await get_character_enhanced(character_id)


async def get_character_detail(
    character_id: str, event_bus: Optional[EventBus] = None
) -> CharacterDetailResponse:
    """Retrieve character details from the filesystem for the public catalog."""

    characters_path = get_characters_directory_path()
    safe_character_id = _require_public_character_id(character_id)

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
                    character_data["skills"] = _normalize_numeric_map(
                        stats.get("skills", {})
                    )
                    character_data["relationships"] = _normalize_numeric_map(
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


def _normalize_numeric_map(raw: Any) -> Dict[str, float]:
    """Ensure relationship/skill maps only contain numeric values."""

    result: Dict[str, float] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            result[str(key)] = _to_float(value)
    return result


def _to_float(value: Any) -> float:
    """Convert arbitrary input to float; fallback to 0.0 when conversion fails."""

    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _workspace_record_to_character_detail(
    record: Dict[str, Any],
) -> CharacterDetailResponse:
    """Convert a workspace record into the API response model."""

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

