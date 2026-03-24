"""Location domain entity."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Location:
    """Location entity representing a place in the world."""

    name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    parent_id: Optional[str] = None
    world_id: Optional[str] = None
    coordinates: Optional[Any] = None
    location_type: str = "generic"
    metadata: Dict[str, Any] = field(default_factory=dict)
    connected_location_ids: List[str] = field(default_factory=list)
