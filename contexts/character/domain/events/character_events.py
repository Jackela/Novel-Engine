#!/usr/bin/env python3
"""
Character Domain Events

This module implements domain events for the Character bounded context,
providing a way to communicate character state changes to other parts
of the system in a decoupled manner.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4

from ..value_objects.character_id import CharacterID


@dataclass(frozen=True)
class CharacterEvent(ABC):
    """
    Base class for all character domain events.
    
    Domain events represent something interesting that happened in the
    character domain that other bounded contexts might care about.
    """
    
    event_id: str
    character_id: CharacterID
    occurred_at: datetime
    
    def __post_init__(self):
        """Validate event data."""
        if not self.event_id:
            raise ValueError("Event ID cannot be empty")
        
        if not self.character_id:
            raise ValueError("Character ID cannot be empty")
    
    @abstractmethod
    def get_event_type(self) -> str:
        """Get the type of this event."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        pass


@dataclass(frozen=True)
class CharacterCreated(CharacterEvent):
    """
    Event raised when a new character is created.
    
    This event signals that a new character aggregate has been created
    and is now available in the system.
    """
    
    character_name: str
    character_class: str
    level: int
    created_at: datetime
    
    def __post_init__(self):
        """Validate character creation event."""
        super().__post_init__()
        
        if not self.character_name or not self.character_name.strip():
            raise ValueError("Character name cannot be empty")
        
        if not self.character_class or not self.character_class.strip():
            raise ValueError("Character class cannot be empty")
        
        if self.level < 1:
            raise ValueError("Character level must be at least 1")
    
    def get_event_type(self) -> str:
        """Get the type of this event."""
        return "character.created"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "character_id": str(self.character_id),
            "character_name": self.character_name,
            "character_class": self.character_class,
            "level": self.level,
            "created_at": self.created_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }
    
    @classmethod
    def create(cls, character_id: CharacterID, character_name: str, 
               character_class: str, level: int, created_at: datetime) -> 'CharacterCreated':
        """Factory method to create a CharacterCreated event."""
        return cls(
            event_id=str(uuid4()),
            character_id=character_id,
            occurred_at=datetime.now(),
            character_name=character_name,
            character_class=character_class,
            level=level,
            created_at=created_at
        )


@dataclass(frozen=True)
class CharacterUpdated(CharacterEvent):
    """
    Event raised when character data is updated.
    
    This event provides information about what fields were updated
    and version information for optimistic concurrency control.
    """
    
    updated_fields: List[str]
    old_version: int
    new_version: int
    updated_at: datetime
    
    def __post_init__(self):
        """Validate character update event."""
        super().__post_init__()
        
        if not self.updated_fields:
            raise ValueError("Updated fields cannot be empty")
        
        if self.old_version < 1:
            raise ValueError("Old version must be at least 1")
        
        if self.new_version <= self.old_version:
            raise ValueError("New version must be greater than old version")
    
    def get_event_type(self) -> str:
        """Get the type of this event."""
        return "character.updated"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "character_id": str(self.character_id),
            "updated_fields": self.updated_fields,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "updated_at": self.updated_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }
    
    @classmethod
    def create(cls, character_id: CharacterID, updated_fields: List[str],
               old_version: int, new_version: int, updated_at: datetime) -> 'CharacterUpdated':
        """Factory method to create a CharacterUpdated event."""
        return cls(
            event_id=str(uuid4()),
            character_id=character_id,
            occurred_at=datetime.now(),
            updated_fields=updated_fields,
            old_version=old_version,
            new_version=new_version,
            updated_at=updated_at
        )


@dataclass(frozen=True)
class CharacterStatsChanged(CharacterEvent):
    """
    Event raised when character statistics change.
    
    This event is specifically for stat changes like health, mana, etc.
    that other systems might need to react to immediately.
    """
    
    old_health: int
    new_health: int
    old_mana: int
    new_mana: int
    changed_at: datetime
    
    def __post_init__(self):
        """Validate character stats change event."""
        super().__post_init__()
        
        if self.old_health < 0 or self.new_health < 0:
            raise ValueError("Health values cannot be negative")
        
        if self.old_mana < 0 or self.new_mana < 0:
            raise ValueError("Mana values cannot be negative")
    
    def get_event_type(self) -> str:
        """Get the type of this event."""
        return "character.stats_changed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "character_id": str(self.character_id),
            "old_health": self.old_health,
            "new_health": self.new_health,
            "old_mana": self.old_mana,
            "new_mana": self.new_mana,
            "health_changed": self.new_health != self.old_health,
            "mana_changed": self.new_mana != self.old_mana,
            "health_delta": self.new_health - self.old_health,
            "mana_delta": self.new_mana - self.old_mana,
            "changed_at": self.changed_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }
    
    @classmethod
    def create(cls, character_id: CharacterID, old_health: int, new_health: int,
               old_mana: int, new_mana: int, changed_at: datetime) -> 'CharacterStatsChanged':
        """Factory method to create a CharacterStatsChanged event."""
        return cls(
            event_id=str(uuid4()),
            character_id=character_id,
            occurred_at=datetime.now(),
            old_health=old_health,
            new_health=new_health,
            old_mana=old_mana,
            new_mana=new_mana,
            changed_at=changed_at
        )
    
    def is_damage_taken(self) -> bool:
        """Check if this event represents damage taken."""
        return self.new_health < self.old_health
    
    def is_healing(self) -> bool:
        """Check if this event represents healing."""
        return self.new_health > self.old_health
    
    def is_mana_consumed(self) -> bool:
        """Check if this event represents mana consumption."""
        return self.new_mana < self.old_mana
    
    def is_mana_restored(self) -> bool:
        """Check if this event represents mana restoration."""
        return self.new_mana > self.old_mana
    
    def get_damage_amount(self) -> int:
        """Get the amount of damage taken (0 if no damage)."""
        return max(0, self.old_health - self.new_health)
    
    def get_healing_amount(self) -> int:
        """Get the amount of healing received (0 if no healing)."""
        return max(0, self.new_health - self.old_health)


@dataclass(frozen=True)
class CharacterLeveledUp(CharacterEvent):
    """
    Event raised when a character gains a level.
    
    This is a special case of character update that other systems
    might want to handle differently.
    """
    
    old_level: int
    new_level: int
    new_health: int
    new_mana: int
    skill_points_gained: int
    leveled_up_at: datetime
    
    def __post_init__(self):
        """Validate character level up event."""
        super().__post_init__()
        
        if self.old_level < 1 or self.new_level < 1:
            raise ValueError("Levels must be at least 1")
        
        if self.new_level <= self.old_level:
            raise ValueError("New level must be greater than old level")
        
        if self.skill_points_gained < 0:
            raise ValueError("Skill points gained cannot be negative")
    
    def get_event_type(self) -> str:
        """Get the type of this event."""
        return "character.leveled_up"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "character_id": str(self.character_id),
            "old_level": self.old_level,
            "new_level": self.new_level,
            "new_health": self.new_health,
            "new_mana": self.new_mana,
            "skill_points_gained": self.skill_points_gained,
            "levels_gained": self.new_level - self.old_level,
            "leveled_up_at": self.leveled_up_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }
    
    @classmethod
    def create(cls, character_id: CharacterID, old_level: int, new_level: int,
               new_health: int, new_mana: int, skill_points_gained: int,
               leveled_up_at: datetime) -> 'CharacterLeveledUp':
        """Factory method to create a CharacterLeveledUp event."""
        return cls(
            event_id=str(uuid4()),
            character_id=character_id,
            occurred_at=datetime.now(),
            old_level=old_level,
            new_level=new_level,
            new_health=new_health,
            new_mana=new_mana,
            skill_points_gained=skill_points_gained,
            leveled_up_at=leveled_up_at
        )
    
    def get_levels_gained(self) -> int:
        """Get the number of levels gained."""
        return self.new_level - self.old_level


@dataclass(frozen=True)
class CharacterDeleted(CharacterEvent):
    """
    Event raised when a character is deleted from the system.
    
    This event allows other systems to clean up related data.
    """
    
    character_name: str
    final_level: int
    deleted_at: datetime
    reason: str
    
    def __post_init__(self):
        """Validate character deletion event."""
        super().__post_init__()
        
        if not self.character_name or not self.character_name.strip():
            raise ValueError("Character name cannot be empty")
        
        if self.final_level < 1:
            raise ValueError("Final level must be at least 1")
        
        if not self.reason or not self.reason.strip():
            raise ValueError("Deletion reason cannot be empty")
    
    def get_event_type(self) -> str:
        """Get the type of this event."""
        return "character.deleted"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.get_event_type(),
            "character_id": str(self.character_id),
            "character_name": self.character_name,
            "final_level": self.final_level,
            "reason": self.reason,
            "deleted_at": self.deleted_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }
    
    @classmethod
    def create(cls, character_id: CharacterID, character_name: str,
               final_level: int, reason: str, deleted_at: datetime) -> 'CharacterDeleted':
        """Factory method to create a CharacterDeleted event."""
        return cls(
            event_id=str(uuid4()),
            character_id=character_id,
            occurred_at=datetime.now(),
            character_name=character_name,
            final_level=final_level,
            deleted_at=deleted_at,
            reason=reason
        )