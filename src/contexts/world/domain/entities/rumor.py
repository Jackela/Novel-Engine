"""Rumor domain entity."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Set
from uuid import uuid4


class RumorOrigin(Enum):
    """Origin type for rumors."""

    EVENT = auto()
    NPC = auto()
    PLAYER = auto()
    UNKNOWN = auto()


TRUTH_DECAY_PER_HOP: int = 10


@dataclass
class Rumor:
    """Rumor entity representing gossip or information spreading through the world."""

    content: str
    truth_value: int
    origin_type: RumorOrigin
    origin_location_id: str
    current_locations: Set[str] = field(default_factory=set)
    created_date: Any = field(default=None)
    spread_count: int = 0
    source_event_id: Optional[str] = None
    rumor_id: str = field(default_factory=lambda: str(uuid4()))

    @property
    def is_dead(self) -> bool:
        """Check if rumor has died (truth value reached 0)."""
        return self.truth_value <= 0

    def spread_to(self, location_id: str) -> "Rumor":
        """Spread rumor to a new location with truth decay."""
        if location_id in self.current_locations:
            return self

        new_truth = max(0, self.truth_value - TRUTH_DECAY_PER_HOP)
        new_locations = self.current_locations | {location_id}

        return Rumor(
            rumor_id=self.rumor_id,
            content=self.content,
            truth_value=new_truth,
            origin_type=self.origin_type,
            source_event_id=self.source_event_id,
            origin_location_id=self.origin_location_id,
            current_locations=new_locations,
            created_date=self.created_date,
            spread_count=self.spread_count + 1,
        )
