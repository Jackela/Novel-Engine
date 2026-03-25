"""Tests for the Character aggregate root.

This module contains comprehensive tests for the Character domain aggregate,
covering entity creation, attributes management, skills, inventory, relationships,
and domain events.
"""

from __future__ import annotations

from typing import Dict
from uuid import UUID, uuid4

import pytest

# Import directly from character.py since types.py doesn't exist
from src.contexts.character.domain.aggregates.character import (
    Character,
    Item,
    Relationship,
    Skill,
)

# Type definitions for testing
AttributeName = str  # e.g., "strength", "intelligence"
CharacterStatus = str  # "active", "inactive", etc.
ItemType = str  # "weapon", "armor", "consumable", etc.
RelationshipType = str  # "friend", "enemy", "ally", etc.
SkillCategory = str  # "combat", "magic", "social", etc.
Attributes = Dict[str, int]


@pytest.fixture
def valid_character() -> Character:
    """Create a valid character for testing."""
    return Character(name="Test Hero", description="A brave test hero")


@pytest.fixture
def valid_skill() -> Skill:
    """Create a valid skill for testing."""
    return Skill(
        name="Sword Fighting",
        category="combat",
        level=1,
        max_level=100,
        description="Proficiency with swords",
    )


@pytest.fixture
def valid_item() -> Item:
    """Create a valid item for testing."""
    return Item(
        name="Iron Sword",
        item_type="weapon",
        quantity=1,
        description="A sturdy iron sword",
    )


@pytest.fixture
def valid_relationship() -> Relationship:
    """Create a valid relationship for testing."""
    return Relationship(
        target_character_id=uuid4(),
        relationship_type="ally",
        strength=50,
        description="A trusted ally",
        is_mutual=True,
    )


class TestCharacter:
    """Test cases for Character aggregate root."""

    def test_create_character_with_valid_data(self) -> None:
        """Test character creation with valid data."""
        character = Character(
            name="Hero",
            description="A brave hero",
            level=1,
        )

        assert character.name == "Hero"
        assert character.description == "A brave hero"
        assert character.level == 1
        assert character.version == 0
        assert character.status == "active"
        assert isinstance(character.id, UUID)
        assert len(character.skills) == 0
        assert len(character.inventory) == 0
        assert len(character.relationships) == 0

    def test_create_character_with_minimal_data(self) -> None:
        """Test character creation with minimal required data."""
        character = Character(name="Hero")

        assert character.name == "Hero"
        assert character.description is None
        assert character.level == 1
        assert character.version == 0

    def test_create_character_with_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Character(name="")

    def test_create_character_with_whitespace_name_raises_error(self) -> None:
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Character(name="   ")

    def test_create_character_with_too_long_name_raises_error(self) -> None:
        """Test that name exceeding 100 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            Character(name="x" * 101)

    def test_create_character_with_custom_attributes(self) -> None:
        """Test character creation with custom attributes."""
        attributes = {
            "strength": 50,
            "intelligence": 60,
            "charisma": 40,
        }
        character = Character(name="Hero", attributes=attributes)

        assert character.attributes["strength"] == 50
        assert character.attributes["intelligence"] == 60
        assert character.attributes["charisma"] == 40

    def test_create_character_with_attribute_out_of_range_raises_error(
        self,
    ) -> None:
        """Test that attribute value outside 1-100 range raises ValueError."""
        with pytest.raises(ValueError, match="must be between 1 and 100"):
            Character(name="Hero", attributes={"strength": 150})

    def test_create_character_with_zero_attribute_raises_error(self) -> None:
        """Test that attribute value of 0 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 1 and 100"):
            Character(name="Hero", attributes={"strength": 0})

    def test_create_character_with_negative_level_raises_error(self) -> None:
        """Test that negative level raises ValueError."""
        with pytest.raises(ValueError, match="level must be at least 1"):
            Character(name="Hero", level=0)

    def test_create_character_with_negative_experience_raises_error(self) -> None:
        """Test that negative experience raises ValueError."""
        with pytest.raises(ValueError, match="Experience cannot be negative"):
            Character(name="Hero", experience=-1)


class TestCharacterAttributes:
    """Test cases for character attribute management."""

    def test_get_attribute(self, valid_character: Character) -> None:
        """Test getting attribute value."""
        value = valid_character.get_attribute("strength")
        assert value == 10  # Default value

    def test_get_nonexistent_attribute_returns_zero(
        self, valid_character: Character
    ) -> None:
        """Test getting non-existent attribute returns 0."""
        value = valid_character.get_attribute("nonexistent")
        assert value == 0

    def test_set_attribute_valid_range(self, valid_character: Character) -> None:
        """Test setting attribute within valid range."""
        valid_character.set_attribute("strength", 50)

        assert valid_character.attributes["strength"] == 50
        assert valid_character.version == 1  # Version should increment

    def test_set_attribute_at_boundary_values(self, valid_character: Character) -> None:
        """Test setting attribute at boundary values 1 and 100."""
        valid_character.set_attribute("strength", 1)
        assert valid_character.attributes["strength"] == 1

        valid_character.set_attribute("strength", 100)
        assert valid_character.attributes["strength"] == 100

    def test_set_attribute_below_range_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test setting attribute below 1 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 1 and 100"):
            valid_character.set_attribute("strength", 0)

    def test_set_attribute_above_range_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test setting attribute above 100 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 1 and 100"):
            valid_character.set_attribute("strength", 101)

    def test_total_attribute_points_property(self, valid_character: Character) -> None:
        """Test total_attribute_points property calculation."""
        total = valid_character.total_attribute_points
        expected = sum(valid_character.attributes.values())
        assert total == expected

    def test_average_attribute_property(self, valid_character: Character) -> None:
        """Test average_attribute property calculation."""
        avg = valid_character.average_attribute
        expected = sum(valid_character.attributes.values()) / len(
            valid_character.attributes
        )
        assert avg == expected

    def test_average_attribute_with_empty_attributes(self) -> None:
        """Test average_attribute with empty attributes."""
        character = Character(name="Hero", attributes={})
        assert character.average_attribute == 0.0


class TestCharacterSkills:
    """Test cases for character skill management."""

    def test_add_skill(self, valid_character: Character, valid_skill: Skill) -> None:
        """Test adding a skill to character."""
        valid_character.add_skill(valid_skill)

        assert len(valid_character.skills) == 1
        assert valid_character.skills[0].name == "Sword Fighting"
        assert valid_character.version == 1

    def test_add_multiple_skills(self, valid_character: Character) -> None:
        """Test adding multiple skills."""
        skill1 = Skill(name="Skill 1", category="combat")
        skill2 = Skill(name="Skill 2", category="magic")

        valid_character.add_skill(skill1)
        valid_character.add_skill(skill2)

        assert len(valid_character.skills) == 2
        assert valid_character.version == 2

    def test_add_duplicate_skill_raises_error(
        self, valid_character: Character, valid_skill: Skill
    ) -> None:
        """Test that adding duplicate skill name raises ValueError."""
        valid_character.add_skill(valid_skill)

        duplicate_skill = Skill(
            name="Sword Fighting",  # Same name
            category="magic",  # Different category
            level=5,
        )

        with pytest.raises(ValueError, match="already exists"):
            valid_character.add_skill(duplicate_skill)

    def test_add_skill_beyond_maximum_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test that adding more than 20 skills raises ValueError."""
        # Add 20 skills
        for i in range(20):
            skill = Skill(name=f"Skill {i}", category="combat")
            valid_character.add_skill(skill)

        assert len(valid_character.skills) == 20

        # 21st skill should fail
        extra_skill = Skill(name="Extra Skill", category="combat")
        with pytest.raises(ValueError, match="cannot have more than 20 skills"):
            valid_character.add_skill(extra_skill)

    def test_remove_skill(self, valid_character: Character, valid_skill: Skill) -> None:
        """Test removing a skill by name."""
        valid_character.add_skill(valid_skill)
        assert len(valid_character.skills) == 1

        valid_character.remove_skill("Sword Fighting")

        assert len(valid_character.skills) == 0
        assert valid_character.version == 2  # add + remove = 2 increments

    def test_remove_nonexistent_skill_does_nothing(
        self, valid_character: Character
    ) -> None:
        """Test removing non-existent skill does nothing."""
        valid_character.remove_skill("Nonexistent Skill")
        assert len(valid_character.skills) == 0


class TestCharacterInventory:
    """Test cases for character inventory management."""

    def test_add_item(self, valid_character: Character, valid_item: Item) -> None:
        """Test adding an item to inventory."""
        valid_character.add_item(valid_item)

        assert len(valid_character.inventory) == 1
        assert valid_character.inventory[0].name == "Iron Sword"
        assert valid_character.version == 1

    def test_add_item_with_duplicate_id_raises_error(
        self, valid_character: Character, valid_item: Item
    ) -> None:
        """Test that adding item with duplicate ID raises ValueError."""
        valid_character.add_item(valid_item)

        # Create item with same ID
        duplicate_item = Item(
            id=valid_item.id,
            name="Duplicate Sword",
            item_type="weapon",
        )

        with pytest.raises(ValueError, match="already exists"):
            valid_character.add_item(duplicate_item)

    def test_add_item_beyond_maximum_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test that adding more than 100 items raises ValueError."""
        # Add 100 items
        for i in range(100):
            item = Item(name=f"Item {i}", item_type="weapon")
            valid_character.add_item(item)

        assert len(valid_character.inventory) == 100

        # 101st item should fail
        extra_item = Item(name="Extra Item", item_type="weapon")
        with pytest.raises(ValueError, match="Inventory is full"):
            valid_character.add_item(extra_item)

    def test_remove_item(self, valid_character: Character, valid_item: Item) -> None:
        """Test removing an item by ID."""
        valid_character.add_item(valid_item)
        item_id = valid_item.id

        valid_character.remove_item(item_id)

        assert len(valid_character.inventory) == 0
        assert valid_character.version == 2

    def test_remove_nonexistent_item_does_nothing(
        self, valid_character: Character
    ) -> None:
        """Test removing non-existent item does nothing."""
        valid_character.remove_item(uuid4())
        assert len(valid_character.inventory) == 0

    def test_inventory_weight_property(self, valid_character: Character) -> None:
        """Test inventory_weight property calculation."""
        item1 = Item(name="Item 1", item_type="weapon", quantity=5)
        item2 = Item(name="Item 2", item_type="armor", quantity=3)

        valid_character.add_item(item1)
        valid_character.add_item(item2)

        assert valid_character.inventory_weight == 8

    def test_equip_item(self, valid_character: Character) -> None:
        """Test equipping an item."""
        item = Item(name="Sword", item_type="weapon")
        valid_character.add_item(item)

        valid_character.equip_item(item.id)

        assert valid_character.inventory[0].is_equipped is True
        assert valid_character.version == 2

    def test_equip_armor(self, valid_character: Character) -> None:
        """Test equipping armor."""
        item = Item(name="Shield", item_type="armor")
        valid_character.add_item(item)

        valid_character.equip_item(item.id)

        assert valid_character.inventory[0].is_equipped is True

    def test_equip_non_equipable_item_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test equipping non-weapon/armor raises ValueError."""
        item = Item(name="Potion", item_type="consumable")
        valid_character.add_item(item)

        with pytest.raises(ValueError, match="Only weapons and armor can be equipped"):
            valid_character.equip_item(item.id)

    def test_equip_nonexistent_item_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test equipping non-existent item raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            valid_character.equip_item(uuid4())

    def test_unequip_item(self, valid_character: Character) -> None:
        """Test unequipping an item."""
        item = Item(name="Sword", item_type="weapon", is_equipped=True)
        valid_character.add_item(item)

        valid_character.unequip_item(item.id)

        assert valid_character.inventory[0].is_equipped is False
        assert valid_character.version == 2

    def test_unequip_nonexistent_item_does_nothing(
        self, valid_character: Character
    ) -> None:
        """Test unequipping non-existent item does nothing."""
        valid_character.unequip_item(uuid4())  # Should not raise
        assert len(valid_character.inventory) == 0


class TestCharacterRelationships:
    """Test cases for character relationship management."""

    def test_add_relationship(self, valid_character: Character) -> None:
        """Test adding a relationship."""
        target_id = uuid4()
        relationship = valid_character.add_relationship(
            target_character_id=target_id,
            relationship_type="ally",
            strength=75,
            description="A close ally",
        )

        assert len(valid_character.relationships) == 1
        assert relationship.target_character_id == target_id
        assert relationship.relationship_type == "ally"
        assert relationship.strength == 75
        assert valid_character.version == 1

    def test_add_relationship_updates_existing(
        self, valid_character: Character
    ) -> None:
        """Test that adding relationship to same target updates existing."""
        target_id = uuid4()

        valid_character.add_relationship(
            target_character_id=target_id,
            relationship_type="ally",
            strength=50,
        )

        valid_character.add_relationship(
            target_character_id=target_id,
            relationship_type="friend",
            strength=80,
            description="Updated relationship",
        )

        assert len(valid_character.relationships) == 1
        assert valid_character.relationships[0].relationship_type == "friend"
        assert valid_character.relationships[0].strength == 80

    def test_remove_relationship(self, valid_character: Character) -> None:
        """Test removing a relationship."""
        target_id = uuid4()
        valid_character.add_relationship(target_id, "ally")

        valid_character.remove_relationship(target_id)

        assert len(valid_character.relationships) == 0
        assert valid_character.version == 2

    def test_get_relationship(self, valid_character: Character) -> None:
        """Test getting a relationship by target ID."""
        target_id = uuid4()
        valid_character.add_relationship(target_id, "ally", strength=60)

        relationship = valid_character.get_relationship(target_id)

        assert relationship is not None
        assert relationship.strength == 60

    def test_get_nonexistent_relationship_returns_none(
        self, valid_character: Character
    ) -> None:
        """Test getting non-existent relationship returns None."""
        relationship = valid_character.get_relationship(uuid4())
        assert relationship is None


class TestCharacterExperienceAndLeveling:
    """Test cases for character experience and leveling."""

    def test_gain_experience(self, valid_character: Character) -> None:
        """Test gaining experience points."""
        valid_character.gain_experience(100)

        # Experience is consumed when leveling up
        # Level 1 needs 100 XP, so with 100 XP, level up to 2 with 0 XP remaining
        assert valid_character.experience == 0
        assert valid_character.level == 2

    def test_gain_negative_experience_raises_error(
        self, valid_character: Character
    ) -> None:
        """Test that gaining negative experience raises ValueError."""
        with pytest.raises(ValueError, match="Experience gain cannot be negative"):
            valid_character.gain_experience(-50)

    def test_level_up(self, valid_character: Character) -> None:
        """Test character leveling up."""
        # Level 1 requires 100 XP (1^2 * 100)
        leveled_up = valid_character.gain_experience(150)

        assert leveled_up is True
        assert valid_character.level == 2
        assert valid_character.experience == 50  # 150 - 100
        assert valid_character.version == 1

    def test_multiple_level_ups(self, valid_character: Character) -> None:
        """Test multiple level ups from large XP gain."""
        # Level 1: 100 XP, Level 2: 400 XP, Level 3: 900 XP
        # Total needed: 100 + 400 = 500 XP for level 3
        leveled_up = valid_character.gain_experience(600)

        assert leveled_up is True
        assert valid_character.level == 3
        assert valid_character.experience == 100  # 600 - 500

    def test_no_level_up_with_small_xp(self, valid_character: Character) -> None:
        """Test no level up with small XP gain."""
        leveled_up = valid_character.gain_experience(50)

        assert leveled_up is False
        assert valid_character.level == 1
        assert valid_character.experience == 50

    def test_xp_for_next_level_calculation(self, valid_character: Character) -> None:
        """Test XP calculation for next level."""
        # At level 1, need 1^2 * 100 = 100 XP
        assert valid_character._xp_for_next_level() == 100

        valid_character.level = 5
        # At level 5, need 5^2 * 100 = 2500 XP
        assert valid_character._xp_for_next_level() == 2500


class TestCharacterStatusAndUpdates:
    """Test cases for character status and updates."""

    def test_update_status(self, valid_character: Character) -> None:
        """Test updating character status."""
        valid_character.update_status("inactive")

        assert valid_character.status == "inactive"
        assert valid_character.version == 1

    def test_update_description(self, valid_character: Character) -> None:
        """Test updating character description."""
        valid_character.update_description("Updated description")

        assert valid_character.description == "Updated description"
        assert valid_character.version == 1


class TestCharacterSerialization:
    """Test cases for character serialization."""

    def test_to_dict(self, valid_character: Character, valid_skill: Skill) -> None:
        """Test converting character to dictionary."""
        valid_character.add_skill(valid_skill)
        character_dict = valid_character.to_dict()

        assert character_dict["name"] == "Test Hero"
        assert character_dict["description"] == "A brave test hero"
        assert character_dict["level"] == 1
        assert character_dict["version"] == 1
        assert "id" in character_dict
        assert "skills" in character_dict
        assert len(character_dict["skills"]) == 1
        assert "inventory" in character_dict
        assert "relationships" in character_dict
        assert "attributes" in character_dict
        assert "created_at" in character_dict
        assert "updated_at" in character_dict


class TestSkill:
    """Test cases for Skill value object."""

    def test_create_skill_with_valid_data(self) -> None:
        """Test skill creation with valid data."""
        skill = Skill(
            name="Fireball",
            category="magic",
            level=5,
            max_level=50,
            description="Casts a fireball",
        )

        assert skill.name == "Fireball"
        assert skill.category == "magic"
        assert skill.level == 5
        assert skill.max_level == 50

    def test_create_skill_with_minimal_data(self) -> None:
        """Test skill creation with minimal data."""
        skill = Skill(name="Basic Skill", category="combat")

        assert skill.level == 1  # Default
        assert skill.max_level == 100  # Default
        assert skill.description is None

    def test_skill_level_out_of_range_raises_error(self) -> None:
        """Test that skill level outside range raises ValueError."""
        with pytest.raises(ValueError, match="Skill level must be between"):
            Skill(name="Invalid", category="combat", level=0)

        with pytest.raises(ValueError, match="Skill level must be between"):
            Skill(name="Invalid", category="combat", level=101)

    def test_skill_level_above_max_raises_error(self) -> None:
        """Test that skill level above max_level raises ValueError."""
        with pytest.raises(ValueError, match="Skill level must be between"):
            Skill(name="Invalid", category="combat", level=60, max_level=50)

    def test_skill_to_dict(self) -> None:
        """Test skill serialization."""
        skill = Skill(name="Test", category="combat", level=5)
        skill_dict = skill.to_dict()

        assert skill_dict["name"] == "Test"
        assert skill_dict["category"] == "combat"
        assert skill_dict["level"] == 5


class TestItem:
    """Test cases for Item value object."""

    def test_create_item_with_valid_data(self) -> None:
        """Test item creation with valid data."""
        item = Item(
            name="Magic Sword",
            item_type="weapon",
            quantity=2,
            description="A magical sword",
            properties={"damage": 10},
            is_equipped=True,
        )

        assert item.name == "Magic Sword"
        assert item.item_type == "weapon"
        assert item.quantity == 2
        assert item.is_equipped is True

    def test_create_item_generates_id(self) -> None:
        """Test that item auto-generates ID."""
        item = Item(name="Test Item", item_type="weapon")

        assert isinstance(item.id, UUID)

    def test_create_item_with_negative_quantity_raises_error(self) -> None:
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError, match="quantity cannot be negative"):
            Item(name="Invalid", item_type="weapon", quantity=-1)

    def test_item_to_dict(self) -> None:
        """Test item serialization."""
        item = Item(
            name="Test",
            item_type="armor",
            quantity=3,
            properties={"defense": 5},
        )
        item_dict = item.to_dict()

        assert item_dict["name"] == "Test"
        assert item_dict["item_type"] == "armor"
        assert item_dict["quantity"] == 3
        assert item_dict["properties"] == {"defense": 5}


class TestRelationship:
    """Test cases for Relationship value object."""

    def test_create_relationship_with_valid_data(self) -> None:
        """Test relationship creation with valid data."""
        target_id = uuid4()
        relationship = Relationship(
            target_character_id=target_id,
            relationship_type="enemy",
            strength=25,
            description="Bitter enemy",
            is_mutual=False,
        )

        assert relationship.target_character_id == target_id
        assert relationship.relationship_type == "enemy"
        assert relationship.strength == 25
        assert relationship.is_mutual is False

    def test_relationship_strength_out_of_range_raises_error(self) -> None:
        """Test that relationship strength outside 0-100 raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Relationship(
                target_character_id=uuid4(),
                relationship_type="ally",
                strength=-1,
            )

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Relationship(
                target_character_id=uuid4(),
                relationship_type="ally",
                strength=101,
            )

    def test_relationship_to_dict(self) -> None:
        """Test relationship serialization."""
        target_id = uuid4()
        relationship = Relationship(
            target_character_id=target_id,
            relationship_type="friend",
            strength=75,
        )
        rel_dict = relationship.to_dict()

        assert rel_dict["target_character_id"] == str(target_id)
        assert rel_dict["relationship_type"] == "friend"
        assert rel_dict["strength"] == 75


class TestCharacterInvariants:
    """Test cases for character invariant validation."""

    def test_validate_invariants_on_creation(self) -> None:
        """Test that invariants are validated on character creation."""
        # Valid character should not raise
        character = Character(name="Valid", level=1, experience=0)
        assert character is not None

    def test_all_attributes_within_range(self) -> None:
        """Test that all default attributes are within valid range."""
        character = Character(name="Test")

        for attr_name, value in character.attributes.items():
            assert 1 <= value <= 100, f"Attribute {attr_name} has invalid value {value}"

    def test_character_equality(self) -> None:
        """Test character equality based on ID."""
        char1 = Character(name="Char1")
        char2 = Character(name="Char2")

        # Different IDs should not be equal
        assert char1 != char2

    def test_character_hash(self) -> None:
        """Test character hash based on ID."""
        char1 = Character(name="Test")
        char2 = Character(name="Test")

        # Different IDs should have different hashes
        assert hash(char1) != hash(char2)
