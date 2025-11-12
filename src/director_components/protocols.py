"""
Director Component Protocols
============================

Defines the interfaces and contracts for all DirectorAgent components.
Uses Python's Protocol for type safety and clear API definition.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol


class AgentManagerProtocol(Protocol):
    """Protocol for agent lifecycle management."""

    @abstractmethod
    async def register_agent(self, agent: Any) -> bool:
        """Register a new agent with the system."""
        ...

    @abstractmethod
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent from the system."""
        ...

    @abstractmethod
    async def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent by ID."""
        ...

    @abstractmethod
    async def list_agents(self) -> List[Any]:
        """List all registered agents."""
        ...

    @abstractmethod
    async def validate_agents(self) -> Dict[str, Any]:
        """Validate all registered agents."""
        ...


class TurnEngineProtocol(Protocol):
    """Protocol for turn execution management."""

    @abstractmethod
    async def execute_turn(
        self, turn_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a single simulation turn."""
        ...

    @abstractmethod
    async def prepare_turn_context(self, turn_number: int) -> Dict[str, Any]:
        """Prepare context for turn execution."""
        ...

    @abstractmethod
    async def finalize_turn(self, turn_result: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize turn and update state."""
        ...


class WorldStateProtocol(Protocol):
    """Protocol for world state management."""

    @abstractmethod
    async def get_world_state(self) -> Dict[str, Any]:
        """Get current world state."""
        ...

    @abstractmethod
    async def update_world_state(self, updates: Dict[str, Any]) -> None:
        """Update world state with new data."""
        ...

    @abstractmethod
    async def save_world_state(self) -> bool:
        """Persist world state to storage."""
        ...

    @abstractmethod
    async def load_world_state(self) -> bool:
        """Load world state from storage."""
        ...


class NarrativeProtocol(Protocol):
    """Protocol for narrative orchestration."""

    @abstractmethod
    async def generate_narrative_context(self, agent_id: str) -> Dict[str, Any]:
        """Generate narrative context for agent."""
        ...

    @abstractmethod
    async def process_narrative_events(
        self, events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process narrative events."""
        ...

    @abstractmethod
    async def update_story_state(self, updates: Dict[str, Any]) -> None:
        """Update story state."""
        ...


class LoggingProtocol(Protocol):
    """Protocol for campaign logging."""

    @abstractmethod
    async def log_event(self, event: Dict[str, Any]) -> None:
        """Log a single event."""
        ...

    @abstractmethod
    async def log_turn_summary(self, summary: Dict[str, Any]) -> None:
        """Log turn summary."""
        ...

    @abstractmethod
    async def get_log_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get log history."""
        ...


class ConfigProtocol(Protocol):
    """Protocol for configuration management."""

    @abstractmethod
    async def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        ...

    @abstractmethod
    async def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration."""
        ...

    @abstractmethod
    async def reload_config(self) -> bool:
        """Reload configuration from source."""
        ...


class ErrorHandlerProtocol(Protocol):
    """Protocol for system error handling."""

    @abstractmethod
    async def handle_error(
        self, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle system error."""
        ...

    @abstractmethod
    async def recover_from_error(self, error_context: Dict[str, Any]) -> bool:
        """Attempt error recovery."""
        ...

    @abstractmethod
    async def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        ...
