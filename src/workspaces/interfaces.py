"""Workspace interfaces and data models.

This module defines the abstract interfaces and data structures for workspace
management, including storage, character management, and run tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Workspace:
    """Represents a workspace with a unique ID and filesystem root.
    
    A workspace is an isolated environment for storing characters, runs,
    narratives, and exports. Each workspace has a unique identifier and
    a dedicated directory on the filesystem.
    
    Attributes:
        id: Unique identifier for the workspace (32-character hex string)
        root: Path to the workspace's root directory
        
    Example:
        >>> workspace = Workspace(id="abc123...", root=Path("/workspaces/abc123"))
        >>> str(workspace.root / "characters")
        '/workspaces/abc123/characters'
    """
    id: str
    root: Path


class WorkspaceStore(ABC):
    """Abstract interface for workspace storage operations.
    
    Implementations of this interface handle the creation, retrieval,
    and import/export of workspaces. This abstraction allows for different
    storage backends (filesystem, database, cloud, etc.).
    
    Example:
        >>> store = FilesystemWorkspaceStore(Path("/workspaces"))
        >>> workspace = store.create()
        >>> workspace.id  # Returns a new unique ID
    """
    
    @abstractmethod
    def create(self) -> Workspace:
        """Create a new workspace with a unique ID.
        
        Returns:
            A newly created Workspace instance
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def get_or_create(self, workspace_id: str) -> Workspace:
        """Get an existing workspace or create it if it doesn't exist.
        
        Args:
            workspace_id: Unique identifier for the workspace
            
        Returns:
            The existing or newly created Workspace
            
        Raises:
            ValueError: If the workspace_id is invalid
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def export_zip(self, workspace_id: str) -> bytes:
        """Export a workspace as a ZIP archive.
        
        Args:
            workspace_id: ID of the workspace to export
            
        Returns:
            ZIP archive contents as bytes
            
        Raises:
            FileNotFoundError: If the workspace doesn't exist
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def import_zip(self, zip_bytes: bytes) -> Workspace:
        """Import a workspace from a ZIP archive.
        
        Args:
            zip_bytes: ZIP archive contents as bytes
            
        Returns:
            The imported Workspace instance
            
        Raises:
            ValueError: If the ZIP is malformed or contains unsafe paths
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError


class CharacterStore(ABC):
    """Abstract interface for character storage within workspaces.
    
    Manages the lifecycle of character data including listing, retrieval,
    creation, updates, and deletion of character definitions.
    """
    
    @abstractmethod
    def list_ids(self, workspace_id: str) -> List[str]:
        """List all character IDs in a workspace.
        
        Args:
            workspace_id: ID of the workspace containing characters
            
        Returns:
            Sorted list of character identifiers
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, workspace_id: str, character_id: str) -> Optional[Dict[str, Any]]:
        """Get a character's data by ID.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: Unique identifier for the character
            
        Returns:
            Character data as a dictionary, or None if not found
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def create(
        self, workspace_id: str, character_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new character in the workspace.
        
        Args:
            workspace_id: ID of the workspace for the new character
            character_id: Unique identifier for the character
            payload: Character data to store
            
        Returns:
            The stored character data with metadata
            
        Raises:
            FileExistsError: If character already exists
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def update(
        self, workspace_id: str, character_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing character's data.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: Unique identifier for the character
            updates: Dictionary of fields to update (None values ignored)
            
        Returns:
            The updated character data
            
        Raises:
            FileNotFoundError: If character doesn't exist
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, workspace_id: str, character_id: str) -> None:
        """Delete a character from the workspace.
        
        Args:
            workspace_id: ID of the workspace containing the character
            character_id: Unique identifier for the character to delete
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError


class RunStore(ABC):
    """Abstract interface for run storage within workspaces.
    
    Manages the storage and retrieval of simulation run records.
    """
    
    @abstractmethod
    def list_ids(self, workspace_id: str) -> List[str]:
        """List all run IDs in a workspace.
        
        Args:
            workspace_id: ID of the workspace containing runs
            
        Returns:
            List of run identifiers
            
        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError
