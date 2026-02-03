#!/usr/bin/env python3
"""
Character Router Service

Why this module exists:
    The characters router contained significant business logic for filesystem
    access, character summarization, and data transformation. This service
    extracts that logic to keep routers focused on HTTP concerns.

Key patterns:
    - Filesystem character discovery uses directory scanning + markdown/yaml parsing
    - Character summaries are lightweight DTOs for list views
    - Public characters live in a shared directory; workspace characters are stored
    - Display names are inferred from slugs when not explicitly defined

Gotchas:
    - stats.yaml may be missing or malformed; always wrap in try/except
    - Character files follow the pattern: character_{id}.md
    - Updated timestamps are the max of directory + file modification times
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from src.api.schemas import CharacterSummary
from src.api.services.paths import get_characters_directory_path

logger = logging.getLogger(__name__)

_CHARACTER_ID_SLUG_RE = re.compile(r"[^a-z0-9_-]+")
_CHARACTER_DIRNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _normalize_character_id(value: str) -> str:
    """
    Normalize a character name to a safe ID format.

    Why: User-provided names must be sanitized for filesystem safety.

    Args:
        value: Raw character name or ID

    Returns:
        Normalized, filesystem-safe character ID

    Raises:
        HTTPException: If the normalized ID is invalid
    """
    raw_value = (value or "").strip().replace("\\", "/")
    raw_value = os.path.basename(raw_value)
    normalized = _CHARACTER_ID_SLUG_RE.sub("_", raw_value.lower()).strip("_")
    if not normalized or normalized in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid character name")
    return normalized


def _require_public_character_id(value: str) -> str:
    """
    Validate that a character ID is safe for public character lookup.

    Why: Prevents path traversal when accessing public characters.

    Args:
        value: Character ID to validate

    Returns:
        Safe, validated character ID

    Raises:
        HTTPException: If the ID is invalid
    """
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


def _display_name_from_id(character_id: str) -> str:
    """
    Infer a display name from a character ID slug.

    Why: Public characters may not have explicit names in their files.

    Args:
        character_id: Character ID (e.g., "elara_shadowbane")

    Returns:
        Display name (e.g., "Elara Shadowbane")
    """
    return " ".join(
        segment.capitalize()
        for segment in character_id.replace("-", " ").replace("_", " ").split()
    )


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Parse an ISO datetime string, supporting HTTP-date format.

    Why: Workspace records may store timestamps in multiple formats.

    Args:
        value: ISO datetime string or HTTP-date

    Returns:
        Parsed datetime with UTC timezone, or None
    """
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
    """
    Infer character type from a workspace record.

    Why: Workspace records may not have a consistent type field structure.

    Args:
        record: Workspace character record dictionary

    Returns:
        Character type (e.g., "npc", "player", "companion")
    """
    metadata = record.get("metadata") or {}
    structured = record.get("structured_data") or {}
    for key in ("role", "type"):
        candidate = metadata.get(key) or structured.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
    return metadata.get("classification") or structured.get("classification") or "npc"


def _normalize_numeric_map(raw: Any) -> Dict[str, float]:
    """
    Ensure relationship/skill maps only contain numeric values.

    Why: YAML parsing may load numbers as strings; normalize for consistency.

    Args:
        raw: Raw value from YAML (dict or other)

    Returns:
        Dictionary with all values as floats
    """
    result: Dict[str, float] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            result[str(key)] = _to_float(value)
    return result


def _to_float(value: Any) -> float:
    """
    Convert arbitrary input to float; fallback to 0.0 when conversion fails.

    Why: Defensive handling of malformed numeric data from YAML.

    Args:
        value: Any value to convert

    Returns:
        Float value, or 0.0 if conversion fails
    """
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class CharacterRouterService:
    """
    Service for character router business logic.

    This service handles filesystem access, character summarization,
    and data transformation for the characters API endpoints.
    """

    def __init__(self, characters_path: Optional[str] = None):
        """
        Initialize the service.

        Args:
            characters_path: Optional path to characters directory.
                If not provided, uses the default from get_characters_directory_path().
        """
        self._characters_path = characters_path
        self.logger = logger.getChild(self.__class__.__name__)

    @property
    def characters_path(self) -> str:
        """Get the characters directory path, using default if not set."""
        if self._characters_path is None:
            self._characters_path = get_characters_directory_path()
        return self._characters_path

    def gather_filesystem_character_info(
        self, character_id: str
    ) -> Tuple[str, str, str, datetime]:
        """
        Gather character information from the filesystem.

        Why: Extracts file reading/parsing logic from the router.

        Args:
            character_id: Character ID to look up

        Returns:
            Tuple of (display_name, status, type, updated_datetime)

        Raises:
            HTTPException: If character not found
        """
        safe_character_id = _require_public_character_id(character_id)
        base_dir = Path(self.characters_path).resolve()
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
                self.logger.debug("Failed to parse character markdown.", exc_info=True)

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
                self.logger.debug("Failed to parse stats.", exc_info=True)

        updated_dt = datetime.fromtimestamp(
            updated_ts or datetime.now(timezone.utc).timestamp(), tz=timezone.utc
        )
        return display_name, status.lower(), type_value, updated_dt

    def summarize_public_character(
        self, character_id: str
    ) -> Tuple[CharacterSummary, datetime]:
        """
        Create a character summary from filesystem data.

        Why: Lightweight representation for list views.

        Args:
            character_id: Character ID to summarize

        Returns:
            Tuple of (CharacterSummary, updated_datetime)
        """
        name, status, category, updated_dt = self.gather_filesystem_character_info(
            character_id
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

    def summarize_workspace_character(
        self, record: Dict[str, Any], workspace_id: str
    ) -> Tuple[CharacterSummary, datetime]:
        """
        Create a character summary from workspace record data.

        Why: Workspace records have a different structure than filesystem records.

        Args:
            record: Workspace character record
            workspace_id: Workspace identifier

        Returns:
            Tuple of (CharacterSummary, updated_datetime)

        Raises:
            ValueError: If record is missing required identifiers
        """
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

    async def get_public_character_entries(
        self,
    ) -> List[Tuple[datetime, CharacterSummary]]:
        """
        Scan the characters directory and return all public character summaries.

        Why: Bulk loading for the character list endpoint.

        Returns:
            List of tuples (updated_datetime, CharacterSummary)

        Raises:
            HTTPException: If directory is missing or inaccessible
        """
        try:
            os.makedirs(self.characters_path, exist_ok=True)

            entries: List[Tuple[datetime, CharacterSummary]] = []
            for item in os.listdir(self.characters_path):
                item_path = os.path.join(self.characters_path, item)
                if not os.path.isdir(item_path):
                    continue
                if not _CHARACTER_DIRNAME_RE.fullmatch(item):
                    continue
                summary, timestamp = self.summarize_public_character(item)
                entries.append((timestamp, summary))
            return entries
        except FileNotFoundError as exc:
            self.logger.error("Characters directory missing: %s", exc)
            raise HTTPException(status_code=404, detail="Characters directory not found.")
        except PermissionError as exc:
            self.logger.error("Permission denied reading characters: %s", exc)
            raise HTTPException(
                status_code=500, detail="Permission denied accessing characters directory."
            )
        except Exception as exc:
            self.logger.error("Unexpected error loading characters: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve characters: {exc}"
            )

    def normalize_character_id(self, value: str) -> str:
        """
        Normalize a character name for workspace storage.

        Args:
            value: Raw character name

        Returns:
            Normalized character ID

        Raises:
            HTTPException: If the normalized ID is invalid
        """
        return _normalize_character_id(value)

    def normalize_numeric_map(self, raw: Any) -> Dict[str, float]:
        """
        Ensure a map only contains numeric values.

        Args:
            raw: Raw map value

        Returns:
            Map with all values as floats
        """
        return _normalize_numeric_map(raw)
