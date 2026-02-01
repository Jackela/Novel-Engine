#!/usr/bin/env python3
"""Unit tests for the Relationship domain entity.

Tests cover:
- Relationship creation and validation
- RelationshipType and EntityType enums
- Business rule enforcement
- State transitions (activate/deactivate)
- Factory methods
"""

import pytest

from src.contexts.world.domain.entities.relationship import (
    EntityType,
    Relationship,
    RelationshipType,
)


class TestRelationshipType:
    """Tests for RelationshipType enum behavior."""

    def test_bidirectional_types(self):
        """Test which relationship types are bidirectional."""
        bidirectional = [
            RelationshipType.FAMILY,
            RelationshipType.ENEMY,
            RelationshipType.ALLY,
            RelationshipType.ROMANTIC,
            RelationshipType.RIVAL,
            RelationshipType.HISTORICAL,
            RelationshipType.NEUTRAL,
        ]
        for rel_type in bidirectional:
            assert rel_type.is_bidirectional(), f"{rel_type} should be bidirectional"

    def test_directional_types(self):
        """Test which relationship types are directional."""
        directional = [
            RelationshipType.MENTOR,
            RelationshipType.MEMBER_OF,
            RelationshipType.LOCATED_IN,
            RelationshipType.OWNS,
            RelationshipType.CREATED,
        ]
        for rel_type in directional:
            assert not rel_type.is_bidirectional(), f"{rel_type} should be directional"

    def test_inverse_types(self):
        """Test inverse relationship type mapping."""
        # Bidirectional types return themselves
        assert RelationshipType.ALLY.get_inverse() == RelationshipType.ALLY
        assert RelationshipType.ENEMY.get_inverse() == RelationshipType.ENEMY

        # Directional types return their inverse
        assert RelationshipType.MENTOR.get_inverse() == RelationshipType.MENTOR


class TestEntityType:
    """Tests for EntityType enum."""

    def test_entity_type_values(self):
        """Verify all entity types have correct string values."""
        assert EntityType.CHARACTER.value == "character"
        assert EntityType.FACTION.value == "faction"
        assert EntityType.LOCATION.value == "location"
        assert EntityType.ITEM.value == "item"
        assert EntityType.EVENT.value == "event"


class TestRelationshipCreation:
    """Tests for Relationship entity creation."""

    def test_create_basic_relationship(self):
        """Test creating a basic relationship between characters."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            relationship_type=RelationshipType.ALLY,
            description="Close friends",
            strength=80,
        )

        assert rel.source_id == "char-001"
        assert rel.target_id == "char-002"
        assert rel.source_type == EntityType.CHARACTER
        assert rel.target_type == EntityType.CHARACTER
        assert rel.relationship_type == RelationshipType.ALLY
        assert rel.description == "Close friends"
        assert rel.strength == 80
        assert rel.is_active is True

    def test_create_relationship_with_defaults(self):
        """Test relationship creation with default values."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
        )

        assert rel.relationship_type == RelationshipType.NEUTRAL
        assert rel.strength == 50
        assert rel.description == ""
        assert rel.is_active is True
        assert rel.metadata == {}


class TestRelationshipValidation:
    """Tests for Relationship validation rules."""

    def test_empty_source_id_fails(self):
        """Empty source_id should fail validation."""
        with pytest.raises(ValueError, match="Source ID cannot be empty"):
            Relationship(
                source_id="",
                source_type=EntityType.CHARACTER,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
            )

    def test_empty_target_id_fails(self):
        """Empty target_id should fail validation."""
        with pytest.raises(ValueError, match="Target ID cannot be empty"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="",
                target_type=EntityType.CHARACTER,
            )

    def test_same_source_target_fails(self):
        """Source and target cannot be the same entity."""
        with pytest.raises(ValueError, match="Source and target cannot be the same"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="char-001",
                target_type=EntityType.CHARACTER,
            )

    def test_strength_below_zero_fails(self):
        """Strength below 0 should fail validation."""
        with pytest.raises(ValueError, match="Strength must be between 0 and 100"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
                strength=-10,
            )

    def test_strength_above_100_fails(self):
        """Strength above 100 should fail validation."""
        with pytest.raises(ValueError, match="Strength must be between 0 and 100"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
                strength=150,
            )


class TestRelationshipTypeCompatibility:
    """Tests for relationship type and entity type compatibility validation."""

    def test_family_requires_characters(self):
        """FAMILY relationships should be between characters."""
        with pytest.raises(ValueError, match="FAMILY"):
            Relationship(
                source_id="faction-001",
                source_type=EntityType.FACTION,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
                relationship_type=RelationshipType.FAMILY,
            )

    def test_romantic_requires_characters(self):
        """ROMANTIC relationships must be between characters."""
        with pytest.raises(ValueError, match="ROMANTIC"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="location-001",
                target_type=EntityType.LOCATION,
                relationship_type=RelationshipType.ROMANTIC,
            )

    def test_member_of_target_must_be_faction_or_location(self):
        """MEMBER_OF target should be FACTION or LOCATION."""
        with pytest.raises(ValueError, match="MEMBER_OF"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="item-001",
                target_type=EntityType.ITEM,
                relationship_type=RelationshipType.MEMBER_OF,
            )

    def test_located_in_target_must_be_location(self):
        """LOCATED_IN target must be LOCATION."""
        with pytest.raises(ValueError, match="LOCATED_IN"):
            Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="faction-001",
                target_type=EntityType.FACTION,
                relationship_type=RelationshipType.LOCATED_IN,
            )

    def test_valid_member_of_relationship(self):
        """Valid MEMBER_OF relationship should succeed."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="faction-001",
            target_type=EntityType.FACTION,
            relationship_type=RelationshipType.MEMBER_OF,
        )
        assert rel.relationship_type == RelationshipType.MEMBER_OF

    def test_valid_located_in_relationship(self):
        """Valid LOCATED_IN relationship should succeed."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="location-001",
            target_type=EntityType.LOCATION,
            relationship_type=RelationshipType.LOCATED_IN,
        )
        assert rel.relationship_type == RelationshipType.LOCATED_IN


class TestRelationshipMethods:
    """Tests for Relationship entity methods."""

    def test_update_strength(self):
        """Test updating relationship strength."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            strength=50,
        )
        initial_version = rel.version

        rel.update_strength(75)

        assert rel.strength == 75
        assert rel.version > initial_version

    def test_update_strength_invalid_range(self):
        """Test that invalid strength values are rejected."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
        )

        with pytest.raises(ValueError, match="Strength must be between 0 and 100"):
            rel.update_strength(101)

        with pytest.raises(ValueError, match="Strength must be between 0 and 100"):
            rel.update_strength(-1)

    def test_deactivate(self):
        """Test deactivating a relationship."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
        )
        assert rel.is_active is True

        rel.deactivate()

        assert rel.is_active is False

    def test_activate(self):
        """Test activating a relationship."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            is_active=False,
        )

        rel.activate()

        assert rel.is_active is True

    def test_update_description(self):
        """Test updating relationship description."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            description="Old description",
        )

        rel.update_description("  New description  ")

        assert rel.description == "New description"

    def test_change_type(self):
        """Test changing relationship type."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            relationship_type=RelationshipType.ALLY,
        )

        rel.change_type(RelationshipType.ENEMY)

        assert rel.relationship_type == RelationshipType.ENEMY

    def test_change_type_revalidates(self):
        """Test that changing type revalidates compatibility."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="location-001",
            target_type=EntityType.LOCATION,
            relationship_type=RelationshipType.LOCATED_IN,
        )

        # This should fail because ROMANTIC requires CHARACTER targets
        with pytest.raises(ValueError, match="ROMANTIC"):
            rel.change_type(RelationshipType.ROMANTIC)


class TestRelationshipQueries:
    """Tests for relationship query helper methods."""

    def test_is_positive(self):
        """Test positive relationship detection."""
        positive_types = [
            RelationshipType.FAMILY,
            RelationshipType.ALLY,
            RelationshipType.MENTOR,
            RelationshipType.ROMANTIC,
        ]

        for rel_type in positive_types:
            rel = Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
                relationship_type=rel_type,
            )
            assert rel.is_positive(), f"{rel_type} should be positive"

    def test_is_negative(self):
        """Test negative relationship detection."""
        negative_types = [
            RelationshipType.ENEMY,
            RelationshipType.RIVAL,
        ]

        for rel_type in negative_types:
            rel = Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="char-002",
                target_type=EntityType.CHARACTER,
                relationship_type=rel_type,
            )
            assert rel.is_negative(), f"{rel_type} should be negative"

    def test_is_structural(self):
        """Test structural relationship detection."""
        structural_types = [
            (RelationshipType.MEMBER_OF, EntityType.FACTION),
            (RelationshipType.LOCATED_IN, EntityType.LOCATION),
        ]

        for rel_type, target_type in structural_types:
            rel = Relationship(
                source_id="char-001",
                source_type=EntityType.CHARACTER,
                target_id="target-001",
                target_type=target_type,
                relationship_type=rel_type,
            )
            assert rel.is_structural(), f"{rel_type} should be structural"

    def test_involves_entity(self):
        """Test entity involvement check."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
        )

        assert rel.involves_entity("char-001")
        assert rel.involves_entity("char-002")
        assert not rel.involves_entity("char-003")

    def test_get_other_entity(self):
        """Test getting the other entity in a relationship."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
        )

        assert rel.get_other_entity("char-001") == "char-002"
        assert rel.get_other_entity("char-002") == "char-001"
        assert rel.get_other_entity("char-003") is None


class TestRelationshipSerialization:
    """Tests for relationship serialization."""

    def test_to_dict(self):
        """Test converting relationship to dictionary."""
        rel = Relationship(
            source_id="char-001",
            source_type=EntityType.CHARACTER,
            target_id="char-002",
            target_type=EntityType.CHARACTER,
            relationship_type=RelationshipType.ALLY,
            description="Best friends",
            strength=90,
        )

        data = rel.to_dict()

        assert data["source_id"] == "char-001"
        assert data["source_type"] == "character"
        assert data["target_id"] == "char-002"
        assert data["target_type"] == "character"
        assert data["relationship_type"] == "ally"
        assert data["description"] == "Best friends"
        assert data["strength"] == 90
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data


class TestRelationshipFactoryMethods:
    """Tests for Relationship factory methods."""

    def test_create_character_relationship(self):
        """Test factory for character-to-character relationships."""
        rel = Relationship.create_character_relationship(
            source_id="char-001",
            target_id="char-002",
            relationship_type=RelationshipType.ALLY,
            description="Battle companions",
            strength=85,
        )

        assert rel.source_type == EntityType.CHARACTER
        assert rel.target_type == EntityType.CHARACTER
        assert rel.relationship_type == RelationshipType.ALLY
        assert rel.strength == 85

    def test_create_membership(self):
        """Test factory for membership relationships."""
        rel = Relationship.create_membership(
            member_id="char-001",
            member_type=EntityType.CHARACTER,
            faction_id="guild-001",
            description="Senior member",
            strength=80,
        )

        assert rel.source_id == "char-001"
        assert rel.source_type == EntityType.CHARACTER
        assert rel.target_id == "guild-001"
        assert rel.target_type == EntityType.FACTION
        assert rel.relationship_type == RelationshipType.MEMBER_OF
        assert rel.strength == 80

    def test_create_location_relationship(self):
        """Test factory for location relationships."""
        rel = Relationship.create_location_relationship(
            entity_id="char-001",
            entity_type=EntityType.CHARACTER,
            location_id="tavern-001",
            description="Regular patron",
        )

        assert rel.source_id == "char-001"
        assert rel.target_id == "tavern-001"
        assert rel.target_type == EntityType.LOCATION
        assert rel.relationship_type == RelationshipType.LOCATED_IN
        assert rel.strength == 100  # Binary relationship
