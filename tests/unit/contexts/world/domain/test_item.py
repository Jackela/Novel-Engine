#!/usr/bin/env python3
"""Unit tests for the Item domain entity.

Tests cover:
- Item creation and validation
- ItemType and ItemRarity enums
- Business rule enforcement
- Factory methods
- Item operations (update, effects management)
"""

import pytest

from src.contexts.world.domain.entities.item import (
    Item,
    ItemRarity,
    ItemType,
)


class TestItemType:
    """Tests for ItemType enum behavior."""

    def test_item_type_values(self):
        """Verify all item types have correct string values."""
        assert ItemType.WEAPON.value == "weapon"
        assert ItemType.ARMOR.value == "armor"
        assert ItemType.CONSUMABLE.value == "consumable"
        assert ItemType.KEY_ITEM.value == "key_item"
        assert ItemType.MISC.value == "misc"

    def test_item_type_count(self):
        """Verify we have the expected number of item types."""
        assert len(ItemType) == 5


class TestItemRarity:
    """Tests for ItemRarity enum."""

    def test_rarity_values(self):
        """Verify all rarities have correct string values."""
        assert ItemRarity.COMMON.value == "common"
        assert ItemRarity.UNCOMMON.value == "uncommon"
        assert ItemRarity.RARE.value == "rare"
        assert ItemRarity.LEGENDARY.value == "legendary"

    def test_rarity_count(self):
        """Verify we have the expected number of rarities."""
        assert len(ItemRarity) == 4


class TestItemCreation:
    """Tests for Item entity creation."""

    def test_create_basic_item(self):
        """Test creating a basic item."""
        item = Item(
            name="Iron Sword",
            item_type=ItemType.WEAPON,
            description="A sturdy iron sword",
            rarity=ItemRarity.COMMON,
        )

        assert item.name == "Iron Sword"
        assert item.item_type == ItemType.WEAPON
        assert item.description == "A sturdy iron sword"
        assert item.rarity == ItemRarity.COMMON
        assert item.is_equippable is True  # Auto-set for weapons
        assert item.is_consumable is False
        assert item.effects == []

    def test_create_item_with_defaults(self):
        """Test item creation with default values."""
        item = Item(name="Rock")

        assert item.name == "Rock"
        assert item.item_type == ItemType.MISC
        assert item.rarity == ItemRarity.COMMON
        assert item.is_equippable is False
        assert item.is_consumable is False

    def test_create_item_with_all_fields(self):
        """Test item creation with all optional fields."""
        item = Item(
            name="Excalibur",
            item_type=ItemType.WEAPON,
            description="The legendary sword of King Arthur",
            rarity=ItemRarity.LEGENDARY,
            weight=3.5,
            value=10000,
            is_equippable=True,
            is_consumable=False,
            effects=["Deals holy damage", "+10 attack power"],
            lore="Forged by the Lady of the Lake",
        )

        assert item.name == "Excalibur"
        assert item.weight == 3.5
        assert item.value == 10000
        assert len(item.effects) == 2
        assert "Deals holy damage" in item.effects
        assert item.lore == "Forged by the Lady of the Lake"


class TestItemValidation:
    """Tests for Item validation rules."""

    def test_empty_name_fails(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValueError, match="Item name cannot be empty"):
            Item(name="")

    def test_whitespace_only_name_fails(self):
        """Test that whitespace-only name is rejected."""
        with pytest.raises(ValueError, match="Item name cannot be empty"):
            Item(name="   ")

    def test_name_too_long_fails(self):
        """Test that overly long name is rejected."""
        with pytest.raises(ValueError, match="Item name cannot exceed 200 characters"):
            Item(name="A" * 201)

    def test_negative_weight_fails(self):
        """Test that negative weight is rejected."""
        with pytest.raises(ValueError, match="Item weight cannot be negative"):
            Item(name="Test", weight=-1.0)

    def test_negative_value_fails(self):
        """Test that negative value is rejected."""
        with pytest.raises(ValueError, match="Item value cannot be negative"):
            Item(name="Test", value=-100)

    def test_key_item_cannot_be_consumable(self):
        """Test that key items cannot be marked as consumable."""
        with pytest.raises(ValueError, match="Key items cannot be consumable"):
            Item(
                name="Ancient Key",
                item_type=ItemType.KEY_ITEM,
                is_consumable=True,
            )

    def test_weapon_auto_equippable(self):
        """Test that weapons are automatically marked as equippable."""
        item = Item(
            name="Sword",
            item_type=ItemType.WEAPON,
            is_equippable=False,  # Intentionally false
        )
        assert item.is_equippable is True  # Auto-corrected

    def test_armor_auto_equippable(self):
        """Test that armor is automatically marked as equippable."""
        item = Item(
            name="Shield",
            item_type=ItemType.ARMOR,
            is_equippable=False,
        )
        assert item.is_equippable is True

    def test_consumable_type_auto_consumable(self):
        """Test that consumable items are automatically marked as consumable."""
        item = Item(
            name="Health Potion",
            item_type=ItemType.CONSUMABLE,
            is_consumable=False,  # Intentionally false
        )
        assert item.is_consumable is True


class TestItemOperations:
    """Tests for Item methods."""

    def test_update_name(self):
        """Test updating item name."""
        item = Item(name="Old Name")
        old_version = item.version

        item.update_name("New Name")

        assert item.name == "New Name"
        assert item.version == old_version + 1

    def test_update_name_strips_whitespace(self):
        """Test that update_name strips whitespace."""
        item = Item(name="Test")
        item.update_name("  Trimmed Name  ")
        assert item.name == "Trimmed Name"

    def test_update_name_empty_fails(self):
        """Test that empty name update is rejected."""
        item = Item(name="Test")
        with pytest.raises(ValueError, match="Item name cannot be empty"):
            item.update_name("")

    def test_update_description(self):
        """Test updating item description."""
        item = Item(name="Test")
        item.update_description("A new description")
        assert item.description == "A new description"

    def test_update_lore(self):
        """Test updating item lore."""
        item = Item(name="Test")
        item.update_lore("Ancient artifact from forgotten times")
        assert item.lore == "Ancient artifact from forgotten times"

    def test_set_rarity(self):
        """Test changing item rarity."""
        item = Item(name="Test", rarity=ItemRarity.COMMON)
        item.set_rarity(ItemRarity.LEGENDARY)
        assert item.rarity == ItemRarity.LEGENDARY

    def test_add_effect(self):
        """Test adding an effect."""
        item = Item(name="Test")
        item.add_effect("Poison damage")
        assert "Poison damage" in item.effects

    def test_add_empty_effect_ignored(self):
        """Test that empty effects are ignored."""
        item = Item(name="Test")
        item.add_effect("")
        item.add_effect("   ")
        assert len(item.effects) == 0

    def test_remove_effect(self):
        """Test removing an effect."""
        item = Item(name="Test", effects=["Effect A", "Effect B"])
        result = item.remove_effect("Effect A")
        assert result is True
        assert "Effect A" not in item.effects
        assert "Effect B" in item.effects

    def test_remove_nonexistent_effect(self):
        """Test removing effect that doesn't exist."""
        item = Item(name="Test", effects=["Effect A"])
        result = item.remove_effect("Nonexistent")
        assert result is False


class TestItemQueryMethods:
    """Tests for Item query/status methods."""

    def test_is_valuable(self):
        """Test is_valuable method."""
        common = Item(name="Rock", rarity=ItemRarity.COMMON)
        uncommon = Item(name="Silver Ring", rarity=ItemRarity.UNCOMMON)
        rare = Item(name="Magic Staff", rarity=ItemRarity.RARE)
        legendary = Item(name="Excalibur", rarity=ItemRarity.LEGENDARY)

        assert common.is_valuable() is False
        assert uncommon.is_valuable() is False
        assert rare.is_valuable() is True
        assert legendary.is_valuable() is True

    def test_is_equipment(self):
        """Test is_equipment method."""
        weapon = Item(name="Sword", item_type=ItemType.WEAPON)
        armor = Item(name="Helmet", item_type=ItemType.ARMOR)
        consumable = Item(name="Potion", item_type=ItemType.CONSUMABLE)
        misc = Item(name="Rock", item_type=ItemType.MISC)

        assert weapon.is_equipment() is True
        assert armor.is_equipment() is True
        assert consumable.is_equipment() is False
        assert misc.is_equipment() is False

    def test_is_key_item(self):
        """Test is_key_item method."""
        key = Item(name="Ancient Key", item_type=ItemType.KEY_ITEM)
        misc = Item(name="Rock", item_type=ItemType.MISC)

        assert key.is_key_item() is True
        assert misc.is_key_item() is False


class TestItemFactoryMethods:
    """Tests for Item factory methods."""

    def test_create_weapon(self):
        """Test weapon factory method."""
        weapon = Item.create_weapon(
            name="Broadsword",
            description="A heavy sword",
            rarity=ItemRarity.UNCOMMON,
            effects=["Cleave attack"],
        )

        assert weapon.name == "Broadsword"
        assert weapon.item_type == ItemType.WEAPON
        assert weapon.is_equippable is True
        assert "Cleave attack" in weapon.effects

    def test_create_armor(self):
        """Test armor factory method."""
        armor = Item.create_armor(
            name="Iron Helmet",
            description="Basic head protection",
            rarity=ItemRarity.COMMON,
        )

        assert armor.name == "Iron Helmet"
        assert armor.item_type == ItemType.ARMOR
        assert armor.is_equippable is True

    def test_create_consumable(self):
        """Test consumable factory method."""
        potion = Item.create_consumable(
            name="Health Potion",
            description="Restores 50 HP",
            effects=["Restore 50 HP"],
        )

        assert potion.name == "Health Potion"
        assert potion.item_type == ItemType.CONSUMABLE
        assert potion.is_consumable is True
        assert "Restore 50 HP" in potion.effects

    def test_create_key_item(self):
        """Test key item factory method."""
        key = Item.create_key_item(
            name="Dungeon Key",
            description="Opens the dungeon door",
            lore="Crafted by the ancient dwarves",
        )

        assert key.name == "Dungeon Key"
        assert key.item_type == ItemType.KEY_ITEM
        assert key.rarity == ItemRarity.RARE  # Key items are at least rare
        assert key.lore == "Crafted by the ancient dwarves"


class TestItemSerialization:
    """Tests for Item serialization methods."""

    def test_to_dict_specific(self):
        """Test _to_dict_specific returns correct data."""
        item = Item(
            name="Test Item",
            item_type=ItemType.WEAPON,
            description="A test item",
            rarity=ItemRarity.RARE,
            weight=2.5,
            value=500,
            is_equippable=True,
            effects=["Effect 1"],
            lore="Some lore",
        )

        result = item._to_dict_specific()

        assert result["name"] == "Test Item"
        assert result["item_type"] == "weapon"
        assert result["rarity"] == "rare"
        assert result["weight"] == 2.5
        assert result["value"] == 500
        assert result["is_equippable"] is True
        assert "Effect 1" in result["effects"]
        assert result["lore"] == "Some lore"

    def test_to_dict_includes_base_entity_fields(self):
        """Test to_dict includes base Entity fields."""
        item = Item(name="Test")
        result = item.to_dict()

        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert "version" in result
        assert result["entity_type"] == "Item"
