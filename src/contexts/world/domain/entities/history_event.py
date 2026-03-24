"""History event domain entity."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List
from uuid import uuid4


class EventType(Enum):
    """Types of historical events."""

    WAR = auto()
    BATTLE = auto()
    TRADE = auto()
    DEATH = auto()
    BIRTH = auto()
    MARRIAGE = auto()
    ALLIANCE = auto()
    CORONATION = auto()
    DISASTER = auto()
    DISCOVERY = auto()
    REVOLUTION = auto()
    MIRACLE = auto()
    MAGICAL = auto()
    OTHER = auto()


class ImpactScope(Enum):
    """Scope of event impact."""

    GLOBAL = auto()
    REGIONAL = auto()
    LOCAL = auto()


@dataclass
class HistoryEvent:
    """Historical event that occurred in the world."""

    name: str
    event_type: EventType
    id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    location_ids: List[str] = field(default_factory=list)
    affected_location_ids: List[str] = field(default_factory=list)
    faction_ids: List[str] = field(default_factory=list)
    key_figures: List[str] = field(default_factory=list)
    impact_scope: ImpactScope = ImpactScope.LOCAL
    date: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
