#!/usr/bin/env python3
"""
Unit tests for FactionIntent Entity

Comprehensive test suite for the FactionIntent entity covering
validation, properties, serialization, and business rules.
"""

from datetime import datetime
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.domain.entities.faction_intent import (
    DEFENSIVE_INTENTS,
    OFFENSIVE_INTENTS,
    FactionIntent,
    IntentType,
)


class TestIntentTypeEnum:
    """Test suite for IntentType enum."""

    @pytest.mark.unit
    def test_intent_type_values(self):
        """Test all expected IntentType values exist."""
        assert IntentType.EXPAND.value == "expand"
        assert IntentType.ATTACK.value == "attack"
        assert IntentType.DEFEND.value == "defend"
        assert IntentType.ALLY.value == "ally"
        assert IntentType.TRADE.value == "trade"
        assert IntentType.RECOVER.value == "recover"
        assert IntentType.CONSOLIDATE.value == "consolidate"

    @pytest.mark.unit
    def test_intent_type_count(self):
        """Test that we have exactly 7 intent types."""
        assert len(IntentType) == 7

    @pytest.mark.unit
    def test_offensive_intents_set(self):
        """Test offensive intents constant set."""
        assert OFFENSIVE_INTENTS == {IntentType.ATTACK, IntentType.EXPAND}

    @pytest.mark.unit
    def test_defensive_intents_set(self):
        """Test defensive intents constant set."""
        assert DEFENSIVE_INTENTS == {IntentType.DEFEND, IntentType.CONSOLIDATE}


class TestFactionIntentCreation:
    """Test suite for FactionIntent creation."""

    @pytest.fixture
    def valid_intent_data(self) -> dict:
        """Create valid intent data for testing."""
        return {
            "faction_id": str(uuid4()),
            "intent_type": IntentType.EXPAND,
            "target_id": str(uuid4()),
            "priority": 5,
            "narrative": "Expand territory into the eastern plains",
        }

    @pytest.mark.unit
    def test_create_intent_with_all_fields(self, valid_intent_data: dict):
        """Test creating an intent with all fields specified."""
        intent = FactionIntent(**valid_intent_data)

        assert intent.faction_id == valid_intent_data["faction_id"]
        assert intent.intent_type == IntentType.EXPAND
        assert intent.target_id == valid_intent_data["target_id"]
        assert intent.priority == 5
        assert intent.narrative == "Expand territory into the eastern plains"
        assert intent.intent_id is not None
        assert intent.created_at is not None

    @pytest.mark.unit
    def test_create_intent_with_defaults(self):
        """Test creating an intent with minimal required fields."""
        intent = FactionIntent(
            faction_id="faction-123",
            narrative="Focus on internal affairs",
        )

        assert intent.faction_id == "faction-123"
        assert intent.intent_type == IntentType.CONSOLIDATE  # Default
        assert intent.target_id is None  # Optional
        assert intent.priority == 1  # Default
        assert intent.narrative == "Focus on internal affairs"

    @pytest.mark.unit
    def test_auto_generated_intent_id(self):
        """Test that intent_id is auto-generated as UUID."""
        intent = FactionIntent(
            faction_id="faction-123",
            narrative="Test narrative",
        )

        # Should be a valid UUID string
        uuid_obj = uuid4()
        assert isinstance(intent.intent_id, str)
        assert len(intent.intent_id) == 36  # UUID format

    @pytest.mark.unit
    def test_auto_generated_created_at(self):
        """Test that created_at is auto-generated."""
        before = datetime.now()
        intent = FactionIntent(
            faction_id="faction-123",
            narrative="Test narrative",
        )
        after = datetime.now()

        assert before <= intent.created_at <= after

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self, valid_intent_data: dict):
        """Test that FactionIntent is immutable (frozen=True)."""
        intent = FactionIntent(**valid_intent_data)

        with pytest.raises(AttributeError):
            intent.priority = 10  # type: ignore

        with pytest.raises(AttributeError):
            intent.narrative = "Changed"  # type: ignore


class TestFactionIntentValidation:
    """Test suite for FactionIntent validation."""

    @pytest.mark.unit
    def test_validation_empty_faction_id(self):
        """Test that empty faction_id fails validation."""
        with pytest.raises(ValueError, match="Faction ID cannot be empty"):
            FactionIntent(
                faction_id="",
                narrative="Test narrative",
            )

    @pytest.mark.unit
    def test_validation_empty_narrative(self):
        """Test that empty narrative fails validation."""
        with pytest.raises(ValueError, match="Narrative cannot be empty"):
            FactionIntent(
                faction_id="faction-123",
                narrative="",
            )

    @pytest.mark.unit
    def test_validation_whitespace_narrative(self):
        """Test that whitespace-only narrative fails validation."""
        with pytest.raises(ValueError, match="Narrative cannot be empty"):
            FactionIntent(
                faction_id="faction-123",
                narrative="   ",
            )

    @pytest.mark.unit
    def test_validation_priority_below_range(self):
        """Test that priority below 1 fails validation."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            FactionIntent(
                faction_id="faction-123",
                narrative="Test narrative",
                priority=0,
            )

    @pytest.mark.unit
    def test_validation_priority_above_range(self):
        """Test that priority above 10 fails validation."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
            FactionIntent(
                faction_id="faction-123",
                narrative="Test narrative",
                priority=11,
            )

    @pytest.mark.unit
    def test_valid_priority_boundaries(self):
        """Test that priority boundaries 1 and 10 are valid."""
        intent_min = FactionIntent(
            faction_id="faction-123",
            narrative="Test narrative",
            priority=1,
        )
        intent_max = FactionIntent(
            faction_id="faction-123",
            narrative="Test narrative",
            priority=10,
        )

        assert intent_min.priority == 1
        assert intent_max.priority == 10


class TestFactionIntentProperties:
    """Test suite for FactionIntent properties."""

    @pytest.mark.unit
    def test_is_offensive_for_attack(self):
        """Test is_offensive returns True for ATTACK."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.ATTACK,
            target_id="enemy-456",
            narrative="Attack the enemy",
        )
        assert intent.is_offensive is True
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_is_offensive_for_expand(self):
        """Test is_offensive returns True for EXPAND."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.EXPAND,
            target_id="location-789",
            narrative="Expand into new territory",
        )
        assert intent.is_offensive is True
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_is_defensive_for_defend(self):
        """Test is_defensive returns True for DEFEND."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.DEFEND,
            narrative="Fortify our borders",
        )
        assert intent.is_defensive is True
        assert intent.is_offensive is False

    @pytest.mark.unit
    def test_is_defensive_for_consolidate(self):
        """Test is_defensive returns True for CONSOLIDATE."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.CONSOLIDATE,
            narrative="Focus on internal affairs",
        )
        assert intent.is_defensive is True
        assert intent.is_offensive is False

    @pytest.mark.unit
    def test_neither_offensive_nor_defensive_for_ally(self):
        """Test ALLY is neither offensive nor defensive."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.ALLY,
            target_id="potential-ally-456",
            narrative="Seek alliance",
        )
        assert intent.is_offensive is False
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_neither_offensive_nor_defensive_for_trade(self):
        """Test TRADE is neither offensive nor defensive."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.TRADE,
            target_id="trade-partner-789",
            narrative="Establish trade routes",
        )
        assert intent.is_offensive is False
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_neither_offensive_nor_defensive_for_recover(self):
        """Test RECOVER is neither offensive nor defensive."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.RECOVER,
            narrative="Recover economic stability",
        )
        assert intent.is_offensive is False
        assert intent.is_defensive is False


class TestFactionIntentSerialization:
    """Test suite for FactionIntent serialization."""

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict returns correct dictionary."""
        created_at = datetime(2026, 2, 17, 12, 0, 0)
        intent = FactionIntent(
            intent_id="intent-123",
            faction_id="faction-456",
            intent_type=IntentType.ATTACK,
            target_id="enemy-789",
            priority=7,
            narrative="Attack the enemy stronghold",
            created_at=created_at,
        )

        result = intent.to_dict()

        assert result["intent_id"] == "intent-123"
        assert result["faction_id"] == "faction-456"
        assert result["intent_type"] == "attack"
        assert result["target_id"] == "enemy-789"
        assert result["priority"] == 7
        assert result["narrative"] == "Attack the enemy stronghold"
        assert result["created_at"] == "2026-02-17T12:00:00"
        assert result["is_offensive"] is True
        assert result["is_defensive"] is False

    @pytest.mark.unit
    def test_to_dict_with_none_target(self):
        """Test to_dict handles None target_id."""
        intent = FactionIntent(
            faction_id="faction-123",
            intent_type=IntentType.CONSOLIDATE,
            narrative="Internal focus",
        )

        result = intent.to_dict()
        assert result["target_id"] is None

    @pytest.mark.unit
    def test_from_dict_with_all_fields(self):
        """Test from_dict creates intent from complete dictionary."""
        data = {
            "intent_id": "intent-123",
            "faction_id": "faction-456",
            "intent_type": "expand",
            "target_id": "location-789",
            "priority": 5,
            "narrative": "Expand territory",
            "created_at": "2026-02-17T12:00:00",
        }

        intent = FactionIntent.from_dict(data)

        assert intent.intent_id == "intent-123"
        assert intent.faction_id == "faction-456"
        assert intent.intent_type == IntentType.EXPAND
        assert intent.target_id == "location-789"
        assert intent.priority == 5
        assert intent.narrative == "Expand territory"
        assert intent.created_at == datetime(2026, 2, 17, 12, 0, 0)

    @pytest.mark.unit
    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing fields."""
        data = {
            "faction_id": "faction-123",
            "narrative": "Test narrative",
        }

        intent = FactionIntent.from_dict(data)

        assert intent.faction_id == "faction-123"
        assert intent.narrative == "Test narrative"
        assert intent.intent_type == IntentType.CONSOLIDATE
        assert intent.target_id is None
        assert intent.priority == 1

    @pytest.mark.unit
    def test_from_dict_case_insensitive_intent_type(self):
        """Test from_dict handles case-insensitive intent_type."""
        data = {
            "faction_id": "faction-123",
            "intent_type": "ATTACK",
            "narrative": "Attack enemy",
        }

        intent = FactionIntent.from_dict(data)
        assert intent.intent_type == IntentType.ATTACK

    @pytest.mark.unit
    def test_from_dict_with_intent_type_enum(self):
        """Test from_dict handles IntentType enum directly."""
        data = {
            "faction_id": "faction-123",
            "intent_type": IntentType.DEFEND,
            "narrative": "Defend borders",
        }

        intent = FactionIntent.from_dict(data)
        assert intent.intent_type == IntentType.DEFEND

    @pytest.mark.unit
    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves all data."""
        original = FactionIntent(
            intent_id="intent-123",
            faction_id="faction-456",
            intent_type=IntentType.ALLY,
            target_id="potential-ally-789",
            priority=6,
            narrative="Form alliance with neighbor",
            created_at=datetime(2026, 2, 17, 12, 0, 0),
        )

        data = original.to_dict()
        restored = FactionIntent.from_dict(data)

        assert restored.intent_id == original.intent_id
        assert restored.faction_id == original.faction_id
        assert restored.intent_type == original.intent_type
        assert restored.target_id == original.target_id
        assert restored.priority == original.priority
        assert restored.narrative == original.narrative
        assert restored.created_at == original.created_at


class TestFactionIntentStringRepresentation:
    """Test suite for FactionIntent string representations."""

    @pytest.mark.unit
    def test_str_representation(self):
        """Test __str__ returns expected format."""
        intent = FactionIntent(
            intent_id="intent-12345678",
            faction_id="faction-abcdefgh",
            intent_type=IntentType.ATTACK,
            priority=7,
            narrative="Attack enemy",
        )

        result = str(intent)

        assert "FactionIntent" in result
        assert "attack" in result
        assert "priority=7" in result
        assert "faction" in result

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test __repr__ returns expected format."""
        intent = FactionIntent(
            intent_id="intent-12345678",
            faction_id="faction-abcdefgh",
            intent_type=IntentType.EXPAND,
            priority=5,
            narrative="Expand territory",
        )

        result = repr(intent)

        assert "FactionIntent" in result
        assert "expand" in result
        assert "priority=5" in result
        assert "intent_id" in result


class TestFactionIntentEquality:
    """Test suite for FactionIntent equality (frozen dataclass)."""

    @pytest.mark.unit
    def test_equality_same_values(self):
        """Test intents with same values are equal."""
        # For frozen dataclass, equality compares all fields
        # So we need to create the same object twice with same timestamp
        created_at = datetime(2026, 2, 17, 12, 0, 0)
        intent_id = str(uuid4())
        faction_id = str(uuid4())

        intent1 = FactionIntent(
            intent_id=intent_id,
            faction_id=faction_id,
            narrative="Test",
            created_at=created_at,
        )

        intent2 = FactionIntent(
            intent_id=intent_id,
            faction_id=faction_id,
            narrative="Test",
            created_at=created_at,
        )

        assert intent1 == intent2

    @pytest.mark.unit
    def test_inequality_different_id(self):
        """Test intents with different IDs are not equal."""
        intent1 = FactionIntent(
            faction_id="faction-123",
            narrative="Test 1",
        )

        intent2 = FactionIntent(
            faction_id="faction-123",
            narrative="Test 1",
        )

        assert intent1 != intent2

    @pytest.mark.unit
    def test_hash_consistency(self):
        """Test that identical intents have same hash."""
        # For frozen dataclass, hash is based on all fields
        created_at = datetime(2026, 2, 17, 12, 0, 0)
        intent_id = str(uuid4())
        faction_id = str(uuid4())

        intent1 = FactionIntent(
            intent_id=intent_id,
            faction_id=faction_id,
            narrative="Test",
            created_at=created_at,
        )

        intent2 = FactionIntent(
            intent_id=intent_id,
            faction_id=faction_id,
            narrative="Test",
            created_at=created_at,
        )

        assert hash(intent1) == hash(intent2)

    @pytest.mark.unit
    def test_can_be_used_in_set(self):
        """Test that frozen intents can be used in sets."""
        intent_id = str(uuid4())
        intent = FactionIntent(
            intent_id=intent_id,
            faction_id="faction-123",
            narrative="Test",
        )

        # Should not raise TypeError
        intent_set = {intent}
        assert intent in intent_set

    @pytest.mark.unit
    def test_can_be_used_as_dict_key(self):
        """Test that frozen intents can be used as dict keys."""
        intent_id = str(uuid4())
        intent = FactionIntent(
            intent_id=intent_id,
            faction_id="faction-123",
            narrative="Test",
        )

        # Should not raise TypeError
        intent_dict = {intent: "value"}
        assert intent_dict[intent] == "value"
