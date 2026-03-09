#!/usr/bin/env python3
"""
Unit tests for DiplomacyMatrix Aggregate

Comprehensive test suite for the DiplomacyMatrix aggregate covering
relation management, status queries, and serialization.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()

# Import the aggregate we're testing
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus


class TestDiplomacyMatrixAggregate:
    """Test suite for DiplomacyMatrix aggregate."""

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_matrix_creation_with_world_id(self):
        """Test matrix creation with world ID."""
        matrix = DiplomacyMatrix(world_id="world-123")

        assert matrix.world_id == "world-123"
        assert matrix.relations == {}
        assert matrix.faction_ids == set()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_matrix_auto_generates_id(self):
        """Test that matrix auto-generates ID."""
        matrix = DiplomacyMatrix(world_id="world-1")

        assert matrix.id is not None
        assert len(matrix.id) > 0

    # ==================== Set Status Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_status_creates_relation(self):
        """Test setting status creates a relation."""
        matrix = DiplomacyMatrix(world_id="world-1")

        result = matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)

        assert result.is_ok
        assert matrix.has_relation("faction-a", "faction-b")
        assert matrix.get_status("faction-a", "faction-b") == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_status_is_symmetric(self):
        """Test that (A, B) and (B, A) return same status."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("faction-a", "faction-b", DiplomaticStatus.FRIENDLY)

        # Order shouldn't matter
        assert matrix.get_status("faction-a", "faction-b") == DiplomaticStatus.FRIENDLY
        assert matrix.get_status("faction-b", "faction-a") == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_status_tracks_factions(self):
        """Test that setting status tracks both factions."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("faction-a", "faction-b", DiplomaticStatus.NEUTRAL)

        assert "faction-a" in matrix.faction_ids
        assert "faction-b" in matrix.faction_ids
        assert matrix.get_faction_count() == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_status_self_relation_fails(self):
        """Test that setting self-relation returns error."""
        matrix = DiplomacyMatrix(world_id="world-1")

        result = matrix.set_status("faction-a", "faction-a", DiplomaticStatus.ALLIED)

        assert result.is_error
        assert "itself" in str(result.error).lower()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_status_updates_existing(self):
        """Test that setting status updates existing relation."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)
        matrix.set_status("faction-a", "faction-b", DiplomaticStatus.AT_WAR)

        assert matrix.get_status("faction-a", "faction-b") == DiplomaticStatus.AT_WAR

    # ==================== Get Status Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_status_nonexistent_returns_none(self):
        """Test that getting nonexistent status returns None."""
        matrix = DiplomacyMatrix(world_id="world-1")

        status = matrix.get_status("faction-a", "faction-b")

        assert status is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_status_after_multiple_relations(self):
        """Test getting status after multiple relations set."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        matrix.set_status("a", "c", DiplomaticStatus.AT_WAR)
        matrix.set_status("b", "c", DiplomaticStatus.NEUTRAL)

        assert matrix.get_status("a", "b") == DiplomaticStatus.ALLIED
        assert matrix.get_status("a", "c") == DiplomaticStatus.AT_WAR
        assert matrix.get_status("b", "c") == DiplomaticStatus.NEUTRAL

    # ==================== Get Allies Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_allies_returns_allied_factions(self):
        """Test that get_allies returns only ALLIED factions."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        matrix.set_status("a", "c", DiplomaticStatus.FRIENDLY)  # Not allied
        matrix.set_status("a", "d", DiplomaticStatus.ALLIED)

        allies = matrix.get_allies("a")

        assert len(allies) == 2
        assert "b" in allies
        assert "d" in allies
        assert "c" not in allies

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_allies_empty_if_none(self):
        """Test get_allies returns empty list if no allies."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.HOSTILE)
        matrix.set_status("a", "c", DiplomaticStatus.NEUTRAL)

        allies = matrix.get_allies("a")

        assert allies == []

    # ==================== Get Enemies Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_enemies_returns_hostile_and_at_war(self):
        """Test that get_enemies returns HOSTILE and AT_WAR factions."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.HOSTILE)
        matrix.set_status("a", "c", DiplomaticStatus.AT_WAR)
        matrix.set_status("a", "d", DiplomaticStatus.COLD)  # Not enemy

        enemies = matrix.get_enemies("a")

        assert len(enemies) == 2
        assert "b" in enemies
        assert "c" in enemies
        assert "d" not in enemies

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_enemies_empty_if_none(self):
        """Test get_enemies returns empty list if no enemies."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        matrix.set_status("a", "c", DiplomaticStatus.FRIENDLY)

        enemies = matrix.get_enemies("a")

        assert enemies == []

    # ==================== Get Neutral Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_neutral_returns_neutral_factions(self):
        """Test that get_neutral returns only NEUTRAL factions."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.NEUTRAL)
        matrix.set_status("a", "c", DiplomaticStatus.COLD)  # Not neutral
        matrix.set_status("a", "d", DiplomaticStatus.NEUTRAL)

        neutral = matrix.get_neutral("a")

        assert len(neutral) == 2
        assert "b" in neutral
        assert "d" in neutral

    # ==================== To Matrix Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_matrix_creates_nested_dict(self):
        """Test that to_matrix creates nested dictionary."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        matrix.set_status("a", "c", DiplomaticStatus.AT_WAR)

        result = matrix.to_matrix()

        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert result["a"]["b"] == "allied"
        assert result["b"]["a"] == "allied"
        assert result["a"]["c"] == "at_war"
        assert result["c"]["a"] == "at_war"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_matrix_self_relation_is_dash(self):
        """Test that self-relations in matrix are '-'."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)

        result = matrix.to_matrix()

        assert result["a"]["a"] == "-"
        assert result["b"]["b"] == "-"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_matrix_unrelated_factions_default_neutral(self):
        """Test that unrelated factions default to NEUTRAL."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.register_faction("a")
        matrix.register_faction("b")

        result = matrix.to_matrix()

        assert result["a"]["b"] == "neutral"
        assert result["b"]["a"] == "neutral"

    # ==================== Register/Remove Faction Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_register_faction_adds_to_set(self):
        """Test registering a faction adds it to the set."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.register_faction("faction-a")

        assert "faction-a" in matrix.faction_ids
        assert matrix.get_faction_count() == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_register_faction_idempotent(self):
        """Test registering same faction twice is idempotent."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.register_faction("faction-a")
        matrix.register_faction("faction-a")

        assert matrix.get_faction_count() == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_faction_removes_all_relations(self):
        """Test removing a faction removes all its relations."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        matrix.set_status("a", "c", DiplomaticStatus.AT_WAR)
        matrix.set_status("b", "c", DiplomaticStatus.NEUTRAL)

        removed = matrix.remove_faction("a")

        assert removed == 2  # a-b and a-c relations removed
        assert "a" not in matrix.faction_ids
        assert not matrix.has_relation("a", "b")
        assert not matrix.has_relation("a", "c")
        assert matrix.has_relation("b", "c")  # b-c relation preserved

    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_nonexistent_faction_returns_zero(self):
        """Test removing nonexistent faction returns 0."""
        matrix = DiplomacyMatrix(world_id="world-1")

        removed = matrix.remove_faction("nonexistent")

        assert removed == 0

    # ==================== Get Factions By Status Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_factions_by_status_filters_correctly(self):
        """Test get_factions_by_status filters by specific status."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.COLD)
        matrix.set_status("a", "c", DiplomaticStatus.COLD)
        matrix.set_status("a", "d", DiplomaticStatus.HOSTILE)

        cold_factions = matrix.get_factions_by_status("a", DiplomaticStatus.COLD)

        assert len(cold_factions) == 2
        assert "b" in cold_factions
        assert "c" in cold_factions

    # ==================== Has Relation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_relation_true_when_exists(self):
        """Test has_relation returns True for existing relation."""
        matrix = DiplomacyMatrix(world_id="world-1")

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)

        assert matrix.has_relation("a", "b") is True
        assert matrix.has_relation("b", "a") is True  # Symmetric

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_relation_false_when_missing(self):
        """Test has_relation returns False for missing relation."""
        matrix = DiplomacyMatrix(world_id="world-1")

        assert matrix.has_relation("a", "b") is False

    # ==================== Count Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_relation_count(self):
        """Test get_relation_count returns correct count."""
        matrix = DiplomacyMatrix(world_id="world-1")

        assert matrix.get_relation_count() == 0

        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)
        assert matrix.get_relation_count() == 1

        matrix.set_status("a", "c", DiplomaticStatus.AT_WAR)
        assert matrix.get_relation_count() == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_faction_count(self):
        """Test get_faction_count returns correct count."""
        matrix = DiplomacyMatrix(world_id="world-1")

        assert matrix.get_faction_count() == 0

        matrix.register_faction("a")
        assert matrix.get_faction_count() == 1

        matrix.register_faction("b")
        assert matrix.get_faction_count() == 2

    # ==================== Serialization Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict(self):
        """Test conversion to dictionary."""
        matrix = DiplomacyMatrix(world_id="world-1")
        matrix.set_status("a", "b", DiplomaticStatus.ALLIED)

        data = matrix.to_dict()

        assert data["world_id"] == "world-1"
        assert "a|b" in data["relations"]
        assert data["relations"]["a|b"] == "allied"
        assert "a" in data["faction_ids"]
        assert "b" in data["faction_ids"]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "id": "matrix-123",
            "world_id": "world-1",
            "relations": {"a|b": "allied", "a|c": "at_war"},
            "faction_ids": ["a", "b", "c"],
            "version": 1,
        }

        matrix = DiplomacyMatrix.from_dict(data)

        assert matrix.world_id == "world-1"
        assert matrix.get_status("a", "b") == DiplomaticStatus.ALLIED
        assert matrix.get_status("a", "c") == DiplomaticStatus.AT_WAR
        assert matrix.get_faction_count() == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_serialization_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = DiplomacyMatrix(world_id="world-1")
        original.set_status("a", "b", DiplomaticStatus.ALLIED)
        original.set_status("b", "c", DiplomaticStatus.AT_WAR)

        data = original.to_dict()
        restored = DiplomacyMatrix.from_dict(data)

        assert restored.world_id == original.world_id
        assert restored.get_status("a", "b") == DiplomaticStatus.ALLIED
        assert restored.get_status("b", "c") == DiplomaticStatus.AT_WAR
        assert restored.get_faction_count() == original.get_faction_count()

    # ==================== Equality Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_by_identity(self):
        """Test equality is based on identity, not content."""
        matrix1 = DiplomacyMatrix(id="same-id", world_id="world-1")
        matrix2 = DiplomacyMatrix(id="same-id", world_id="world-2")  # Different world

        assert matrix1 == matrix2  # Same ID means equal

    @pytest.mark.unit
    @pytest.mark.fast
    def test_inequality_by_different_id(self):
        """Test inequality with different IDs."""
        matrix1 = DiplomacyMatrix(world_id="world-1")
        matrix2 = DiplomacyMatrix(world_id="world-1")

        assert matrix1 != matrix2

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_empty_world_id_fails(self):
        """Test validation fails for empty world_id."""
        with pytest.raises(ValueError) as exc_info:
            DiplomacyMatrix(world_id="")

        assert "World ID" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_validation_relation_with_unknown_faction(self):
        """Test validation warns about relations with unknown factions."""
        # Create a matrix and manually inject an invalid relation
        matrix = DiplomacyMatrix.__new__(DiplomacyMatrix)
        matrix.id = "test-id"
        matrix.world_id = "world-1"
        matrix.relations = {("unknown", "also-unknown"): DiplomaticStatus.ALLIED}
        matrix.faction_ids = set()  # Empty - doesn't contain the factions
        matrix.version = 1

        # Validation should catch the unknown factions
        from datetime import datetime

        matrix.created_at = datetime.now()
        matrix.updated_at = datetime.now()

        with pytest.raises(ValueError) as exc_info:
            matrix.validate()

        assert "Unknown faction" in str(exc_info.value)
