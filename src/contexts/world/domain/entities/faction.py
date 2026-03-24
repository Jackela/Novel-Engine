"""Faction domain entity."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Faction:
    """Faction entity representing a group or organization in the world."""

    name: str
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    world_id: Optional[str] = None
    leader_id: Optional[str] = None
    member_ids: List[str] = field(default_factory=list)
    territory_ids: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
