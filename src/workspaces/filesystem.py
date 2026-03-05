from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, cast

from .interfaces import CharacterStore, Workspace, WorkspaceStore

_WORKSPACE_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_RESOURCE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def _utc_now() -> datetime:
    """Get current UTC datetime.
    
    Returns:
        Current time in UTC timezone
    """
    return datetime.now(timezone.utc)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Atomically write bytes to a file using a temp file and rename.
    
    Ensures data integrity by writing to a temporary file first, then
    renaming it to the target path. This prevents partial writes in case
    of crashes or errors during write operations.
    
    Args:
        path: Target file path
        data: Bytes to write
        
    Note:
        Uses fsync where available for durability guarantees
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp.", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                # Best-effort: some filesystems or environments may not support fsync.
                logger.debug("fsync not supported for %s", path, exc_info=True)
        os.replace(tmp_path, path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Atomically write JSON data to a file.
    
    Serializes the payload to JSON with consistent formatting and
    writes atomically using _atomic_write_bytes.
    
    Args:
        path: Target file path
        payload: Dictionary to serialize as JSON
    """
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True).encode(
        "utf-8"
    )
    _atomic_write_bytes(path, data)


def _read_json(path: Path) -> Dict[str, Any]:
    """Read and parse JSON from a file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Parsed JSON as a dictionary
        
    Raises:
        ValueError: If the JSON is not a valid dictionary
        FileNotFoundError: If the file doesn't exist
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid JSON document")
    return cast(Dict[str, Any], payload)


def _validate_workspace_id(workspace_id: str) -> str:
    """Validate and normalize a workspace ID.
    
    Args:
        workspace_id: Raw workspace identifier
        
    Returns:
        Normalized (lowercase, trimmed) workspace ID
        
    Raises:
        ValueError: If the ID doesn't match the expected format (32 hex chars)
    """
    value = (workspace_id or "").strip().lower()
    if not _WORKSPACE_ID_RE.fullmatch(value):
        raise ValueError("Invalid workspace id")
    return value


def _new_workspace_id() -> str:
    """Generate a new unique workspace ID.
    
    Returns:
        32-character hexadecimal UUID string
    """
    return uuid.uuid4().hex


def _validate_resource_id(resource_id: str, resource_name: str) -> str:
    """Validate a resource ID to prevent path traversal attacks.
    
    Args:
        resource_id: Raw resource identifier
        resource_name: Name of the resource type for error messages
        
    Returns:
        Normalized (trimmed) resource ID
        
    Raises:
        ValueError: If the ID contains path separators, parent references,
                   or doesn't match the allowed character pattern
    """
    value = (resource_id or "").strip()
    if "/" in value or "\\" in value:
        raise ValueError(f"Invalid {resource_name} id")
    if value in {".", ".."} or ".." in value:
        raise ValueError(f"Invalid {resource_name} id")
    if not _RESOURCE_ID_RE.fullmatch(value):
        raise ValueError(f"Invalid {resource_name} id")
    return value


@dataclass(frozen=True)
class WorkspaceManifest:
    """Metadata manifest for a workspace.
    
    Tracks schema version and timestamps for workspace lifecycle management.
    Manifests are stored as JSON in the workspace root directory.
    
    Attributes:
        schemaVersion: Version of the workspace schema for migrations
        createdAt: ISO8601 timestamp of workspace creation
        lastAccessedAt: ISO8601 timestamp of last access
        
    Example:
        >>> manifest = WorkspaceManifest.create()
        >>> manifest.schemaVersion
        1
    """
    schemaVersion: int
    createdAt: str
    lastAccessedAt: str

    @staticmethod
    def create(now: Optional[datetime] = None) -> "WorkspaceManifest":
        """Create a new manifest with current timestamps.
        
        Args:
            now: Optional datetime to use (defaults to current UTC time)
            
        Returns:
            New WorkspaceManifest with synchronized created/updated times
        """
        now_dt = now or _utc_now()
        iso = now_dt.isoformat()
        return WorkspaceManifest(
            schemaVersion=SCHEMA_VERSION, createdAt=iso, lastAccessedAt=iso
        )

    def touch(self, now: Optional[datetime] = None) -> "WorkspaceManifest":
        """Update the lastAccessedAt timestamp.
        
        Args:
            now: Optional datetime to use (defaults to current UTC time)
            
        Returns:
            New WorkspaceManifest with updated access time (immutable update)
        """
        iso = (now or _utc_now()).isoformat()
        return WorkspaceManifest(
            schemaVersion=self.schemaVersion,
            createdAt=self.createdAt,
            lastAccessedAt=iso,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the manifest
        """
        return {
            "schemaVersion": self.schemaVersion,
            "createdAt": self.createdAt,
            "lastAccessedAt": self.lastAccessedAt,
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "WorkspaceManifest":
        """Create manifest from a dictionary (JSON deserialization).
        
        Args:
            payload: Dictionary containing manifest data
            
        Returns:
            WorkspaceManifest with values from the dictionary
        """
        schema_version = int(payload.get("schemaVersion", SCHEMA_VERSION))
        created_at = str(payload.get("createdAt", _utc_now().isoformat()))
        last_accessed = str(payload.get("lastAccessedAt", created_at))
        return WorkspaceManifest(
            schemaVersion=schema_version,
            createdAt=created_at,
            lastAccessedAt=last_accessed,
        )


class FilesystemWorkspaceStore(WorkspaceStore):
    """Filesystem-based implementation of WorkspaceStore.
    
    Stores workspaces as directories on the local filesystem with the following
    structure:
        {base_dir}/{workspace_id}/
            manifest.json
            characters/
            runs/
            narratives/
            exports/
    """
    
    def __init__(self, base_dir: Path) -> None:
        """Initialize the filesystem workspace store.
        
        Args:
            base_dir: Root directory for all workspaces
        """
        self._base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        """Get the base directory for all workspaces.
        
        Returns:
            Root path where workspaces are stored
        """
        return self._base_dir

    def create(self) -> Workspace:
        """Create a new workspace with a generated ID.
        
        Returns:
            Newly created workspace
        """
        workspace_id = _new_workspace_id()
        return self.get_or_create(workspace_id)

    def get_or_create(self, workspace_id: str) -> Workspace:
        """Get or create a workspace, initializing its directory structure.
        
        Args:
            workspace_id: ID of the workspace to get or create
            
        Returns:
            The workspace instance
        """
        normalized = _validate_workspace_id(workspace_id)
        root = self._base_dir / normalized
        root.mkdir(parents=True, exist_ok=True)
        (root / "characters").mkdir(exist_ok=True)
        (root / "runs").mkdir(exist_ok=True)
        (root / "narratives").mkdir(exist_ok=True)
        (root / "exports").mkdir(exist_ok=True)

        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = WorkspaceManifest.from_dict(_read_json(manifest_path))
            except Exception:
                manifest = WorkspaceManifest.create()
        else:
            manifest = WorkspaceManifest.create()

        manifest = manifest.touch()
        _atomic_write_json(manifest_path, manifest.to_dict())
        return Workspace(id=normalized, root=root)

    def export_zip(self, workspace_id: str) -> bytes:
        """Export a workspace as a ZIP archive.
        
        Creates a ZIP containing all files in the workspace directory,
        preserving the directory structure.
        
        Args:
            workspace_id: ID of the workspace to export
            
        Returns:
            ZIP file contents as bytes
        """
        workspace = self.get_or_create(workspace_id)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in workspace.root.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(workspace.root)
                zf.write(path, arcname=str(PurePosixPath(*rel.parts)))
        return buffer.getvalue()

    def import_zip(self, zip_bytes: bytes) -> Workspace:
        """Import a workspace from a ZIP archive.
        
        Creates a new workspace and extracts the ZIP contents into it.
        If extraction fails, the workspace is cleaned up.
        
        Args:
            zip_bytes: ZIP file contents as bytes
            
        Returns:
            The imported workspace
            
        Raises:
            ValueError: If ZIP contains unsafe paths
        """
        workspace = self.create()
        try:
            _safe_extract_zip_bytes(zip_bytes, workspace.root)
            # Touch manifest so lastAccessedAt is current even after import.
            self.get_or_create(workspace.id)
            return workspace
        except Exception:
            shutil.rmtree(workspace.root, ignore_errors=True)
            raise


class FilesystemCharacterStore(CharacterStore):
    """Filesystem-based implementation of CharacterStore.
    
    Stores characters as individual JSON files within workspace directories:
        {workspace}/characters/{character_id}.json
    """
    
    def __init__(self, workspace_store: FilesystemWorkspaceStore) -> None:
        """Initialize the character store.
        
        Args:
            workspace_store: Workspace store for resolving workspace paths
        """
        self._workspace_store = workspace_store

    def list_ids(self, workspace_id: str) -> List[str]:
        """List all character IDs in a workspace.
        
        Args:
            workspace_id: ID of the workspace
            
        Returns:
            Sorted list of character IDs (filenames without .json extension)
        """
        workspace = self._workspace_store.get_or_create(workspace_id)
        characters_dir = workspace.root / "characters"
        ids: List[str] = []
        for entry in characters_dir.glob("*.json"):
            if entry.is_file():
                ids.append(entry.stem)
        return sorted(ids)

    def get(self, workspace_id: str, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character data by ID.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: ID of the character to retrieve
            
        Returns:
            Character data dictionary, or None if not found or corrupted
        """
        workspace = self._workspace_store.get_or_create(workspace_id)
        char_id = _validate_resource_id(character_id, "character")
        path = workspace.root / "characters" / f"{char_id}.json"
        if not path.exists():
            return None
        try:
            payload = _read_json(path)
        except Exception:
            # Corruption recovery: surface as missing rather than returning partial data.
            return None
        payload.setdefault("id", char_id)
        return payload

    def create(
        self, workspace_id: str, character_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new character.
        
        Args:
            workspace_id: ID of the workspace for the character
            character_id: Unique ID for the new character
            payload: Character data to store
            
        Returns:
            The stored character data with metadata
            
        Raises:
            FileExistsError: If character already exists
        """
        workspace = self._workspace_store.get_or_create(workspace_id)
        char_id = _validate_resource_id(character_id, "character")
        path = workspace.root / "characters" / f"{char_id}.json"
        if path.exists():
            raise FileExistsError("Character already exists")

        record = dict(payload)
        record["id"] = char_id
        record.setdefault("createdAt", _utc_now().isoformat())
        record.setdefault("updatedAt", record["createdAt"])
        _atomic_write_json(path, record)
        return record

    def update(
        self, workspace_id: str, character_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing character.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: ID of the character to update
            updates: Dictionary of fields to update (None values ignored)
            
        Returns:
            The updated character data
            
        Raises:
            FileNotFoundError: If character doesn't exist
        """
        workspace = self._workspace_store.get_or_create(workspace_id)
        char_id = _validate_resource_id(character_id, "character")
        path = workspace.root / "characters" / f"{char_id}.json"
        current = _read_json(path) if path.exists() else None
        if not isinstance(current, dict):
            raise FileNotFoundError("Character not found")

        merged = dict(current)
        for key, value in updates.items():
            if value is None:
                continue
            merged[key] = value
        merged["id"] = char_id
        merged["updatedAt"] = _utc_now().isoformat()
        _atomic_write_json(path, merged)
        return merged

    def delete(self, workspace_id: str, character_id: str) -> None:
        """Delete a character.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: ID of the character to delete
        """
        workspace = self._workspace_store.get_or_create(workspace_id)
        char_id = _validate_resource_id(character_id, "character")
        path = workspace.root / "characters" / f"{char_id}.json"
        if path.exists():
            path.unlink()


def _safe_extract_zip_bytes(zip_bytes: bytes, destination_dir: Path) -> None:
    """Safely extract ZIP bytes to a directory, preventing path traversal.
    
    Validates all ZIP entries before extraction to prevent:
    - Absolute path attacks
    - Directory traversal (../)
    - Drive letter attacks (C:)
    
    Args:
        zip_bytes: ZIP file contents as bytes
        destination_dir: Directory to extract files into
        
    Raises:
        ValueError: If ZIP contains unsafe paths
    """
    destination_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            member_path = PurePosixPath(member.filename)
            if member_path.is_absolute():
                raise ValueError("Unsafe zip entry: absolute path")
            if ".." in member_path.parts:
                raise ValueError("Unsafe zip entry: traversal")
            if any(":" in part for part in member_path.parts):
                raise ValueError("Unsafe zip entry: drive specifier")

            target_path = destination_dir.joinpath(*member_path.parts)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src:
                data = src.read()
            _atomic_write_bytes(target_path, data)
