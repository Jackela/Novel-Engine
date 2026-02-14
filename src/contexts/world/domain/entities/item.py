#!/usr/bin/env python3
"""Item Domain Entity.

This module defines the Item entity which represents objects, artifacts,
and possessions in the world. Items can be owned by characters and
contribute to the narrative through equipment, consumables, and key items.

Why Items matter: Items create tangible connections between characters
and the world. A family heirloom, a magical sword, or a simple key can
drive entire plot arcs and define character motivations.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Item, ItemType, ItemRarity
    >>> sword = Item(
    ...     name="Excalibur",
    ...     item_type=ItemType.WEAPON,
    ...     description="The legendary sword of King Arthur",
    ...     rarity=ItemRarity.LEGENDARY
    ... )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .entity import Entity


class ItemType(Enum):
    """Classification of item types.

    Defines the functional category of an item, which affects
    how it can be used and displayed in the UI.

    Attributes:
        WEAPON: Combat equipment for dealing damage.
        ARMOR: Protective equipment that reduces damage.
        CONSUMABLE: Single-use items like potions or scrolls.
        KEY_ITEM: Plot-critical items that cannot be discarded.
        MISC: General items without special function.
    """

    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    KEY_ITEM = "key_item"
    MISC = "misc"


class ItemRarity(Enum):
    """Rarity classification for items.

    Determines visual styling and narrative significance.
    Rarer items typically have stronger effects and deeper lore.

    Attributes:
        COMMON: Everyday objects, easily found.
        UNCOMMON: Notable items with minor enhancements.
        RARE: Valuable items with significant properties.
        LEGENDARY: Unique artifacts with world-changing potential.
    """

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    LEGENDARY = "legendary"


@dataclass(eq=False)
class Item(Entity):
    """Item Entity.

    Represents a physical or magical object in the world. Items can be
    owned by characters, stored in locations, or exist as part of the
    world's lore without a specific owner.

    Why track items: Items serve multiple narrative purposes:
    - Character development through possessions
    - Plot devices (keys, maps, artifacts)
    - World-building through cultural objects
    - Gameplay mechanics if applicable

    Attributes:
        name: Display name of the item.
        item_type: Functional category (WEAPON, ARMOR, etc.).
        description: Detailed description including history and properties.
        rarity: How rare/valuable the item is.
        weight: Physical weight (optional, for encumbrance systems).
        value: Monetary or trade value (optional).
        is_equippable: Whether the item can be equipped/worn.
        is_consumable: Whether the item is destroyed on use.
        effects: List of effects when used or equipped.
        lore: Extended backstory or historical context.
        metadata: Additional flexible data for specific use cases.
    """

    name: str = ""
    item_type: ItemType = ItemType.MISC
    description: str = ""
    rarity: ItemRarity = ItemRarity.COMMON
    weight: Optional[float] = None
    value: Optional[int] = None
    is_equippable: bool = False
    is_consumable: bool = False
    effects: List[str] = field(default_factory=list)
    lore: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        """Equality comparison based on entity identity (inherited from Entity)."""
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate Item-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("Item name cannot be empty")

        if len(self.name) > 200:
            errors.append("Item name cannot exceed 200 characters")

        if self.weight is not None and self.weight < 0:
            errors.append("Item weight cannot be negative")

        if self.value is not None and self.value < 0:
            errors.append("Item value cannot be negative")

        # Validate type-specific rules
        errors.extend(self._validate_type_rules())

        return errors

    def _validate_type_rules(self) -> List[str]:
        """Validate rules specific to item type."""
        errors = []

        # Consumables should be marked as consumable
        if self.item_type == ItemType.CONSUMABLE and not self.is_consumable:
            # Auto-correct rather than error - consumable type implies is_consumable
            self.is_consumable = True

        # Weapons and armor should be equippable
        if (
            self.item_type in (ItemType.WEAPON, ItemType.ARMOR)
            and not self.is_equippable
        ):
            # Auto-correct - equipment should be equippable
            self.is_equippable = True

        # Key items should not be consumable
        if self.item_type == ItemType.KEY_ITEM and self.is_consumable:
            errors.append("Key items cannot be consumable")

        return errors

    def update_name(self, name: str) -> None:
        """Update the item's name.

        Args:
            name: New name for the item.

        Raises:
            ValueError: If name is empty or too long.
        """
        if not name or not name.strip():
            raise ValueError("Item name cannot be empty")
        if len(name) > 200:
            raise ValueError("Item name cannot exceed 200 characters")

        self.name = name.strip()
        self.touch()

    def update_description(self, description: str) -> None:
        """Update the item's description.

        Args:
            description: New description text.
        """
        self.description = description.strip()
        self.touch()

    def update_lore(self, lore: str) -> None:
        """Update the item's lore/backstory.

        Args:
            lore: Extended backstory text.
        """
        self.lore = lore.strip()
        self.touch()

    def set_rarity(self, rarity: ItemRarity) -> None:
        """Change the item's rarity level.

        Args:
            rarity: New rarity classification.
        """
        self.rarity = rarity
        self.touch()

    def add_effect(self, effect: str) -> None:
        """Add an effect to the item.

        Args:
            effect: Description of the effect.
        """
        if effect and effect.strip():
            self.effects.append(effect.strip())
            self.touch()

    def remove_effect(self, effect: str) -> bool:
        """Remove an effect from the item.

        Args:
            effect: Effect to remove.

        Returns:
            True if effect was found and removed.
        """
        effect_stripped = effect.strip()
        if effect_stripped in self.effects:
            self.effects.remove(effect_stripped)
            self.touch()
            return True
        return False

    def is_valuable(self) -> bool:
        """Check if this item is considered valuable (rare or legendary)."""
        return self.rarity in (ItemRarity.RARE, ItemRarity.LEGENDARY)

    def is_equipment(self) -> bool:
        """Check if this item is equipment (weapon or armor)."""
        return self.item_type in (ItemType.WEAPON, ItemType.ARMOR)

    def is_key_item(self) -> bool:
        """Check if this is a key/plot item."""
        return self.item_type == ItemType.KEY_ITEM

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert Item-specific data to dictionary."""
        return {
            "name": self.name,
            "item_type": self.item_type.value,
            "description": self.description,
            "rarity": self.rarity.value,
            "weight": self.weight,
            "value": self.value,
            "is_equippable": self.is_equippable,
            "is_consumable": self.is_consumable,
            "effects": self.effects.copy(),
            "lore": self.lore,
            "metadata": self.metadata,
        }

    @classmethod
    def create_weapon(
        cls,
        name: str,
        description: str = "",
        rarity: ItemRarity = ItemRarity.COMMON,
        effects: Optional[List[str]] = None,
    ) -> "Item":
        """Factory method for creating weapon items.

        Args:
            name: Weapon name.
            description: Weapon description.
            rarity: Weapon rarity.
            effects: Optional list of effects.

        Returns:
            A new weapon Item.
        """
        return cls(
            name=name,
            item_type=ItemType.WEAPON,
            description=description,
            rarity=rarity,
            is_equippable=True,
            effects=effects or [],
        )

    @classmethod
    def create_armor(
        cls,
        name: str,
        description: str = "",
        rarity: ItemRarity = ItemRarity.COMMON,
        effects: Optional[List[str]] = None,
    ) -> "Item":
        """Factory method for creating armor items.

        Args:
            name: Armor name.
            description: Armor description.
            rarity: Armor rarity.
            effects: Optional list of effects.

        Returns:
            A new armor Item.
        """
        return cls(
            name=name,
            item_type=ItemType.ARMOR,
            description=description,
            rarity=rarity,
            is_equippable=True,
            effects=effects or [],
        )

    @classmethod
    def create_consumable(
        cls,
        name: str,
        description: str = "",
        effects: Optional[List[str]] = None,
    ) -> "Item":
        """Factory method for creating consumable items.

        Args:
            name: Consumable name.
            description: Consumable description.
            effects: Effects when consumed.

        Returns:
            A new consumable Item.
        """
        return cls(
            name=name,
            item_type=ItemType.CONSUMABLE,
            description=description,
            rarity=ItemRarity.COMMON,
            is_consumable=True,
            effects=effects or [],
        )

    @classmethod
    def create_key_item(
        cls,
        name: str,
        description: str = "",
        lore: str = "",
    ) -> "Item":
        """Factory method for creating key/plot items.

        Args:
            name: Key item name.
            description: Key item description.
            lore: Extended backstory.

        Returns:
            A new key Item.
        """
        return cls(
            name=name,
            item_type=ItemType.KEY_ITEM,
            description=description,
            rarity=ItemRarity.RARE,  # Key items are at least rare
            lore=lore,
        )
