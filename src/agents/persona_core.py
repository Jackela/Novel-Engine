#!/usr/bin/env python3
"""
PersonaAgent Core Infrastructure
===============================

Core agent infrastructure extracted from the massive PersonaAgent class.
Handles basic agent identity, lifecycle, and fundamental properties.

Part of Wave 6.2 PersonaAgent Decomposition Strategy.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Core systems integration
from src.core.error_handler import (
    get_error_handler,
)
from src.core.logging_system import (
    LogContext,
    get_logger,
)
from src.events.event_bus import EventBus

# Import shared types

logger = logging.getLogger(__name__)


@dataclass
class AgentIdentity:
    """Core agent identity information."""

    agent_id: str
    character_name: str
    character_directory: str
    primary_faction: str
    character_sheet_path: str
    backstory: str = ""
    creation_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentState:
    """Current state tracking for the agent."""

    current_location: Optional[str] = None
    is_active: bool = True
    last_action_timestamp: Optional[datetime] = None
    last_world_state_update: Optional[Dict[str, Any]] = None
    turn_count: int = 0
    health_status: str = "normal"


class PersonaCore:
    """
    Core agent infrastructure providing basic identity and lifecycle management.

    Responsibilities:
    - Agent identity and basic properties
    - File system operations (character sheets, caching)
    - State management and tracking
    - Initialization and cleanup
    """

    def __init__(
        self,
        character_directory_path: str,
        event_bus: "EventBus",
        agent_id: Optional[str] = None,
    ):
        """
        Initialize core agent infrastructure.

        Args:
            character_directory_path: Path to character directory
            event_bus: Event bus for communication
            agent_id: Optional agent ID override
        """
        self.character_directory_path = character_directory_path
        self.event_bus = event_bus

        # Initialize agent identity
        self.identity = AgentIdentity(
            agent_id=agent_id
            or self._derive_agent_id_from_path(character_directory_path),
            character_name="",  # Will be loaded from character sheet
            character_directory=character_directory_path,
            primary_faction="",  # Will be loaded from character sheet
            character_sheet_path=str(
                Path(character_directory_path) / "character_sheet.md"
            ),
        )

        # Initialize agent state
        self.state = AgentState()

        # Core character data
        self.character_data: Dict[str, Any] = {}

        # File caching for performance
        self._file_cache: Dict[str, Tuple[str, float]] = {}  # path -> (content, mtime)

        logger.info(f"PersonaCore initialized for agent: {self.identity.agent_id}")

        # Initialize core systems
        self.logger = get_logger(f"{self.__class__.__name__}_{id(self)}")
        self.error_handler = get_error_handler()

        # Create logging context
        self.log_context = LogContext(
            component=self.__class__.__name__,
            session_id=getattr(self, "session_id", None),
            metadata={"component_id": id(self)},
        )

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self.identity.agent_id

    @property
    def character_name(self) -> str:
        """Get character name."""
        return self.identity.character_name

    @property
    def character_directory_name(self) -> str:
        """Get character directory name."""
        return os.path.basename(self.character_directory_path.rstrip(os.sep))

    @property
    def character_context(self) -> str:
        """Get character context string for debugging."""
        return f"{self.character_name} ({self.agent_id}) from {self.character_directory_name}"

    def _derive_agent_id_from_path(self, path: str) -> str:
        """
        Derive agent ID from character directory path.

        Args:
            path: Character directory path

        Returns:
            str: Agent ID derived from path
        """
        directory_name = os.path.basename(path.rstrip(os.sep))

        # Clean directory name for use as agent ID
        agent_id = directory_name.lower().replace(" ", "_").replace("-", "_")

        # Remove non-alphanumeric characters except underscores
        agent_id = "".join(char for char in agent_id if char.isalnum() or char == "_")

        # Ensure agent ID doesn't start with a number
        if agent_id and agent_id[0].isdigit():
            agent_id = f"agent_{agent_id}"

        # Fallback if agent_id is empty
        if not agent_id:
            agent_id = f"agent_{hash(path) % 10000}"

        return agent_id

    def _read_cached_file(self, file_path: str) -> str:
        """
        Read file with caching to avoid repeated disk I/O.

        Args:
            file_path: Path to file to read

        Returns:
            str: File contents
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                logger.warning(f"File not found: {file_path}")
                return ""

            current_mtime = path_obj.stat().st_mtime

            # Check cache
            if file_path in self._file_cache:
                cached_content, cached_mtime = self._file_cache[file_path]
                if current_mtime == cached_mtime:
                    return cached_content

            # Read and cache file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self._file_cache[file_path] = (content, current_mtime)
            return content

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return ""

    def _parse_cached_yaml(self, file_path: str) -> Dict[str, Any]:
        """
        Parse YAML file with caching.

        Args:
            file_path: Path to YAML file

        Returns:
            Dict: Parsed YAML data
        """
        try:
            import yaml

            content = self._read_cached_file(file_path)
            if not content:
                return {}

            return yaml.safe_load(content) or {}

        except Exception as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            return {}

    def handle_turn_start(self, world_state_update: Dict[str, Any]) -> None:
        """
        Handle the start of a new turn.

        Args:
            world_state_update: Updated world state information
        """
        self.state.turn_count += 1
        self.state.last_world_state_update = world_state_update.copy()

        logger.debug(f"Agent {self.agent_id} starting turn {self.state.turn_count}")

    def get_agent_state(self) -> Dict[str, Any]:
        """
        Get current agent state for debugging and monitoring.

        Returns:
            Dict: Agent state information
        """
        return {
            "identity": {
                "agent_id": self.identity.agent_id,
                "character_name": self.identity.character_name,
                "primary_faction": self.identity.primary_faction,
                "directory": self.identity.character_directory,
            },
            "state": {
                "current_location": self.state.current_location,
                "is_active": self.state.is_active,
                "turn_count": self.state.turn_count,
                "health_status": self.state.health_status,
                "last_action": (
                    self.state.last_action_timestamp.isoformat()
                    if self.state.last_action_timestamp
                    else None
                ),
            },
            "character_data_loaded": bool(self.character_data),
            "cache_size": len(self._file_cache),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        self._file_cache.clear()
        self.state.is_active = False
        logger.info(
            f"PersonaCore cleanup completed for agent: {self.identity.agent_id}"
        )
