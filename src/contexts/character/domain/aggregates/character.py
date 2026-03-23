"""
Character Aggregate Root

The Character is the main aggregate root for the character context.
It manages attributes, skills, inventory, and relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from src.contexts.character.domain.types import (
    AttributeName,
    Attributes,
    CharacterStatus,
    ItemType,
    RelationshipType,
    SkillCategory,
)
from src.shared.domain.base.aggregate import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Relationship:
    """Value object representing a relationship between characters."""

    target_character_id: UUID
    relationship_type: RelationshipType
    strength: int = field(default=0)
    description: Optional[str] = None
    is_mutual: bool = field(default=False)

    def __post_init__(self) -> None:
        if not (0 <= self.strength <= 100):
            raise ValueError("Relationship strength must be between 0 and 100")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_character_id": str(self.target_character_id),
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "description": self.description,
            "is_mutual": self.is_mutual,
        }


@dataclass(kw_only=True, eq=False)
class Skill:
    """Value object representing a character skill."""

    name: str
    category: SkillCategory
    level: int = field(default=1)
    max_level: int = field(default=100)
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not (1 <= self.level <= self.max_level):
            raise ValueError(f"Skill level must be between 1 and {self.max_level}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "level": self.level,
            "max_level": self.max_level,
            "description": self.description,
        }


@dataclass(kw_only=True, eq=False)
class Item:
    """Value object representing an inventory item."""

    id: UUID = field(default_factory=uuid4)
    name: str
    item_type: ItemType
    quantity: int = field(default=1)
    description: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    is_equipped: bool = field(default=False)

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("Item quantity cannot be negative")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "name": self.name,
            "item_type": self.item_type,
            "quantity": self.quantity,
            "description": self.description,
            "properties": self.properties,
            "is_equipped": self.is_equipped,
        }


@dataclass(kw_only=True, eq=False)
class Character(AggregateRoot):
    """
    Character aggregate root for the character context.

    AI注意:
    - Characters have attributes, skills, inventory, and relationships
    - Attributes range from 1-100
    - Maximum 20 skills per character
    - Maximum 100 items in inventory
    """

    name: str
    description: Optional[str] = None
    status: CharacterStatus = field(default="active")

    # Core attributes
    attributes: Attributes = field(
        default_factory=lambda: {
            "strength": 10,
            "intelligence": 10,
            "charisma": 10,
            "dexterity": 10,
            "constitution": 10,
            "wisdom": 10,
            "luck": 10,
        }
    )

    # Skills and inventory
    skills: List[Skill] = field(default_factory=list)
    inventory: List[Item] = field(default_factory=list)

    # Relationships with other characters
    relationships: List[Relationship] = field(default_factory=list)

    # Honcho memory system integration
    honcho_workspace_id: Optional[str] = field(default=None)
    honcho_peer_id: Optional[str] = field(default=None)
    active_session_id: Optional[str] = field(default=None)

    # Additional metadata
    level: int = field(default=1)
    experience: int = field(default=0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate character invariants."""
        super().__post_init__()

        if not self.name or len(self.name.strip()) == 0:
            raise ValueError("Character name cannot be empty")

        if len(self.name) > 100:
            raise ValueError("Character name cannot exceed 100 characters")

        # Validate attributes
        for attr_name, value in self.attributes.items():
            if not (1 <= value <= 100):
                raise ValueError(
                    f"Attribute '{attr_name}' must be between 1 and 100, got {value}"
                )

        if self.level < 1:
            raise ValueError("Character level must be at least 1")

        if self.experience < 0:
            raise ValueError("Experience cannot be negative")

    @property
    def total_attribute_points(self) -> int:
        """Calculate total attribute points."""
        return sum(self.attributes.values())

    @property
    def average_attribute(self) -> float:
        """Calculate average attribute value."""
        if not self.attributes:
            return 0.0
        return self.total_attribute_points / len(self.attributes)

    @property
    def inventory_weight(self) -> int:
        """Calculate total inventory item count."""
        return sum(item.quantity for item in self.inventory)

    def get_attribute(self, name: AttributeName) -> int:
        """Get attribute value by name."""
        return self.attributes.get(name, 0)

    def set_attribute(self, name: AttributeName, value: int) -> None:
        """Set attribute value."""
        if not (1 <= value <= 100):
            raise ValueError("Attribute value must be between 1 and 100")
        self.attributes[name] = value
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def add_skill(self, skill: Skill) -> None:
        """
        Add a skill to the character.

        Raises:
            ValueError: If maximum skills reached or skill already exists
        """
        if len(self.skills) >= 20:
            raise ValueError("Character cannot have more than 20 skills")

        if any(s.name == skill.name for s in self.skills):
            raise ValueError(f"Skill '{skill.name}' already exists")

        self.skills.append(skill)
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def remove_skill(self, skill_name: str) -> None:
        """Remove a skill by name."""
        self.skills = [s for s in self.skills if s.name != skill_name]
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def add_item(self, item: Item) -> None:
        """
        Add an item to inventory.

        Raises:
            ValueError: If inventory is full
        """
        if len(self.inventory) >= 100:
            raise ValueError("Inventory is full (max 100 items)")

        # Check if item already exists (same ID)
        if any(i.id == item.id for i in self.inventory):
            raise ValueError("Item already exists in inventory")

        self.inventory.append(item)
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def remove_item(self, item_id: UUID) -> None:
        """Remove an item from inventory by ID."""
        self.inventory = [i for i in self.inventory if i.id != item_id]
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def equip_item(self, item_id: UUID) -> None:
        """
        Equip an item.

        Raises:
            ValueError: If item not found or not equipable
        """
        for item in self.inventory:
            if item.id == item_id:
                if item.item_type not in ("weapon", "armor"):
                    raise ValueError("Only weapons and armor can be equipped")
                item.is_equipped = True
                self.updated_at = datetime.utcnow()
                self.increment_version()
                return

        raise ValueError(f"Item {item_id} not found in inventory")

    def unequip_item(self, item_id: UUID) -> None:
        """Unequip an item."""
        for item in self.inventory:
            if item.id == item_id:
                item.is_equipped = False
                self.updated_at = datetime.utcnow()
                self.increment_version()
                return

    def add_relationship(
        self,
        target_character_id: UUID,
        relationship_type: RelationshipType,
        strength: int = 50,
        description: Optional[str] = None,
    ) -> Relationship:
        """
        Add or update a relationship with another character.

        Returns:
            The created or updated relationship
        """
        # Check if relationship already exists
        for rel in self.relationships:
            if rel.target_character_id == target_character_id:
                # Update existing relationship
                self.relationships.remove(rel)
                break

        relationship = Relationship(
            target_character_id=target_character_id,
            relationship_type=relationship_type,
            strength=strength,
            description=description,
        )

        self.relationships.append(relationship)
        self.updated_at = datetime.utcnow()
        self.increment_version()

        return relationship

    def remove_relationship(self, target_character_id: UUID) -> None:
        """Remove a relationship."""
        self.relationships = [
            r
            for r in self.relationships
            if r.target_character_id != target_character_id
        ]
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def get_relationship(self, target_character_id: UUID) -> Optional[Relationship]:
        """Get relationship with another character."""
        for rel in self.relationships:
            if rel.target_character_id == target_character_id:
                return rel
        return None

    def gain_experience(self, amount: int) -> bool:
        """
        Add experience points and check for level up.

        Returns:
            True if character leveled up
        """
        if amount < 0:
            raise ValueError("Experience gain cannot be negative")

        self.experience += amount
        leveled_up = False

        # Simple level up formula: level^2 * 100 XP needed per level
        while self.experience >= self._xp_for_next_level():
            self.experience -= self._xp_for_next_level()
            self.level += 1
            leveled_up = True

        if leveled_up:
            self.updated_at = datetime.utcnow()
            self.increment_version()

        return leveled_up

    def _xp_for_next_level(self) -> int:
        """Calculate XP needed for next level."""
        return (self.level**2) * 100

    def update_status(self, status: CharacterStatus) -> None:
        """Update character status."""
        self.status = status
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def update_description(self, description: str) -> None:
        """Update character description."""
        self.description = description
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def set_honcho_session(
        self,
        workspace_id: str,
        peer_id: str,
        session_id: str,
    ) -> None:
        """Set Honcho session information for this character.

        Args:
            workspace_id: The Honcho workspace ID for the story.
            peer_id: The Honcho peer ID for this character.
            session_id: The active session ID within the workspace.
        """
        self.honcho_workspace_id = workspace_id
        self.honcho_peer_id = peer_id
        self.active_session_id = session_id
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def clear_honcho_session(self) -> None:
        """Clear Honcho session information."""
        self.honcho_workspace_id = None
        self.honcho_peer_id = None
        self.active_session_id = None
        self.updated_at = datetime.utcnow()
        self.increment_version()

    def to_dict(self) -> Dict[str, Any]:
        """Convert character to dictionary for serialization."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "level": self.level,
            "experience": self.experience,
            "attributes": self.attributes,
            "skills": [s.to_dict() for s in self.skills],
            "inventory": [i.to_dict() for i in self.inventory],
            "relationships": [r.to_dict() for r in self.relationships],
            "honcho_workspace_id": self.honcho_workspace_id,
            "honcho_peer_id": self.honcho_peer_id,
            "active_session_id": self.active_session_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }
