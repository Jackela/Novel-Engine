"""WorldState domain aggregate."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class WorldState:
    """WorldState aggregate representing the current state of a world."""

    id: str = field(default_factory=lambda: str(uuid4()))
    story_id: Optional[str] = None
    version: int = 1
    calendar: Any = None
    factions: Dict[str, Any] = field(default_factory=dict)
    locations: Dict[str, Any] = field(default_factory=dict)
    events: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_deleted: bool = False
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

    def get_domain_events(self) -> List[Any]:
        """Get pending domain events."""
        return []

    def clear_domain_events(self) -> None:
        """Clear pending domain events."""
        pass
