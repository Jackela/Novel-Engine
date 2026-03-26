"""World snapshot domain entity."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass
class WorldSnapshot:
    """Snapshot of world state at a specific point in time."""

    world_id: str
    tick_number: int
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    state_data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
