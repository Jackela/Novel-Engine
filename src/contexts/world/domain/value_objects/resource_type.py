"""Resource type enumeration for world economy.

This module defines the types of resources that exist in the game world.
Resources are the foundation of the economic simulation system.

Typical usage example:
    >>> from src.contexts.world.domain.value_objects import ResourceType
    >>> gold = ResourceType.GOLD
    >>> food = ResourceType.FOOD
"""

from __future__ import annotations

from enum import Enum


class ResourceType(str, Enum):
    """Classification of resource types in the world economy.

    Each resource type represents a distinct category of economic good
    or strategic asset that factions can accumulate, trade, and consume.

    Attributes:
        GOLD: Universal currency for trade and transactions.
        FOOD: Essential for population sustenance and growth.
        MANA: Magical energy resource for spellcasting.
        IRON: Primary material for weapons and infrastructure.
        WOOD: Construction material and fuel source.
        POPULATION: Demographic resource representing available labor.
        KNOWLEDGE: Intellectual capital for technological advancement.
        MILITARY: Trained personnel and equipment for warfare.
        TRADE_GOODS: Commercial products for export and import.
        CULTURAL_INFLUENCE: Soft power for diplomacy and culture.
    """

    GOLD = "gold"
    FOOD = "food"
    MANA = "mana"
    IRON = "iron"
    WOOD = "wood"
    POPULATION = "population"
    KNOWLEDGE = "knowledge"
    MILITARY = "military"
    TRADE_GOODS = "trade_goods"
    CULTURAL_INFLUENCE = "cultural_influence"

    def is_strategic(self) -> bool:
        """Check if this resource type is strategic (military/knowledge).

        Strategic resources directly impact military power or technological
        advancement capabilities.

        Returns:
            True if the resource is strategic, False otherwise.
        """
        return self in (
            ResourceType.MILITARY,
            ResourceType.KNOWLEDGE,
            ResourceType.MANA,
        )

    def is_consumable(self) -> bool:
        """Check if this resource type is regularly consumed.

        Consumable resources deplete over time through normal operations
        and require ongoing production or acquisition.

        Returns:
            True if the resource is consumable, False otherwise.
        """
        return self in (
            ResourceType.FOOD,
            ResourceType.MANA,
            ResourceType.MILITARY,
        )

    def is_tradeable(self) -> bool:
        """Check if this resource type can be traded between factions.

        Tradeable resources can be exchanged through diplomatic agreements
        or market transactions.

        Returns:
            True if the resource can be traded, False otherwise.
        """
        return self in (
            ResourceType.GOLD,
            ResourceType.FOOD,
            ResourceType.IRON,
            ResourceType.WOOD,
            ResourceType.TRADE_GOODS,
            ResourceType.MANA,
        )
