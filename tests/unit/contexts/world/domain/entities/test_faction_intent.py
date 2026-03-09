#!/usr/bin/env python3
"""
Unit tests for FactionIntent Entity

Comprehensive test suite for the FactionIntent entity covering
validation, properties, serialization, status transitions, and business rules.
"""

from datetime import datetime
from uuid import uuid4

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.domain.entities.faction_intent import (
    DEFENSIVE_ACTIONS,
    OFFENSIVE_ACTIONS,
    VALID_STATUS_TRANSITIONS,
    ActionType,
    FactionIntent,
    IntentStatus,
    IntentType,  # Backward compatibility alias
)


class TestActionTypeEnum:
    """Test suite for ActionType enum."""

    @pytest.mark.unit
    def test_action_type_values(self):
        """Test all expected ActionType values exist."""
        assert ActionType.EXPAND.value == "expand"
        assert ActionType.ATTACK.value == "attack"
        assert ActionType.TRADE.value == "trade"
        assert ActionType.SABOTAGE.value == "sabotage"
        assert ActionType.STABILIZE.value == "stabilize"

    @pytest.mark.unit
    def test_action_type_count(self):
        """Test that we have exactly 5 action types."""
        assert len(ActionType) == 5

    @pytest.mark.unit
    def test_offensive_actions_set(self):
        """Test offensive actions constant set."""
        assert OFFENSIVE_ACTIONS == {ActionType.ATTACK, ActionType.SABOTAGE}

    @pytest.mark.unit
    def test_defensive_actions_set(self):
        """Test defensive actions constant set."""
        assert DEFENSIVE_ACTIONS == {ActionType.STABILIZE}

    @pytest.mark.unit
    def test_intent_type_is_alias_for_action_type(self):
        """Test that IntentType is an alias for ActionType (backward compatibility)."""
        assert IntentType is ActionType


class TestIntentStatusEnum:
    """Test suite for IntentStatus enum."""

    @pytest.mark.unit
    def test_status_values(self):
        """Test all expected IntentStatus values exist."""
        assert IntentStatus.PROPOSED.value == "proposed"
        assert IntentStatus.SELECTED.value == "selected"
        assert IntentStatus.EXECUTED.value == "executed"
        assert IntentStatus.REJECTED.value == "rejected"

    @pytest.mark.unit
    def test_status_count(self):
        """Test that we have exactly 4 status values."""
        assert len(IntentStatus) == 4

    @pytest.mark.unit
    def test_valid_status_transitions(self):
        """Test the valid status transitions."""
        assert VALID_STATUS_TRANSITIONS[IntentStatus.PROPOSED] == {
            IntentStatus.SELECTED,
            IntentStatus.REJECTED,
        }
        assert VALID_STATUS_TRANSITIONS[IntentStatus.SELECTED] == {
            IntentStatus.EXECUTED,
            IntentStatus.REJECTED,
        }
        assert VALID_STATUS_TRANSITIONS[IntentStatus.EXECUTED] == set()
        assert VALID_STATUS_TRANSITIONS[IntentStatus.REJECTED] == set()


class TestFactionIntentCreation:
    """Test suite for FactionIntent creation."""

    @pytest.fixture
    def valid_intent_data(self) -> dict:
        """Create valid intent data for testing."""
        return {
            "faction_id": str(uuid4()),
            "action_type": ActionType.EXPAND,
            "target_id": str(uuid4()),
            "priority": 1,
            "rationale": "Expand territory into the eastern plains",
        }

    @pytest.mark.unit
    def test_create_intent_with_all_fields(self, valid_intent_data: dict):
        """Test creating an intent with all fields specified."""
        intent = FactionIntent(**valid_intent_data)

        assert intent.faction_id == valid_intent_data["faction_id"]
        assert intent.action_type == ActionType.EXPAND
        assert intent.target_id == valid_intent_data["target_id"]
        assert intent.priority == 1
        assert intent.rationale == "Expand territory into the eastern plains"
        assert intent.id is not None
        assert intent.status == IntentStatus.PROPOSED
        assert intent.created_at is not None

    @pytest.mark.unit
    def test_create_intent_with_defaults(self):
        """Test creating an intent with minimal required fields."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Focus on internal affairs",
        )

        assert intent.faction_id == "faction-123"
        assert intent.action_type == ActionType.STABILIZE  # Default
        assert intent.target_id is None  # Optional
        assert intent.priority == 2  # Default (medium)
        assert intent.rationale == "Focus on internal affairs"
        assert intent.status == IntentStatus.PROPOSED  # Default

    @pytest.mark.unit
    def test_auto_generated_id(self):
        """Test that id is auto-generated as UUID."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )

        # Should be a valid UUID string
        assert isinstance(intent.id, str)
        assert len(intent.id) == 36  # UUID format

    @pytest.mark.unit
    def test_auto_generated_created_at(self):
        """Test that created_at is auto-generated."""
        before = datetime.now()
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        after = datetime.now()

        assert before <= intent.created_at <= after


class TestFactionIntentValidation:
    """Test suite for FactionIntent validation."""

    @pytest.mark.unit
    def test_validation_empty_faction_id(self):
        """Test that empty faction_id fails validation."""
        with pytest.raises(ValueError, match="Faction ID cannot be empty"):
            FactionIntent(
                faction_id="",
                rationale="Test rationale",
            )

    @pytest.mark.unit
    def test_validation_empty_rationale(self):
        """Test that empty rationale fails validation."""
        with pytest.raises(ValueError, match="Rationale cannot be empty"):
            FactionIntent(
                faction_id="faction-123",
                rationale="",
            )

    @pytest.mark.unit
    def test_validation_whitespace_rationale(self):
        """Test that whitespace-only rationale fails validation."""
        with pytest.raises(ValueError, match="Rationale cannot be empty"):
            FactionIntent(
                faction_id="faction-123",
                rationale="   ",
            )

    @pytest.mark.unit
    def test_validation_priority_below_range(self):
        """Test that priority below 1 fails validation."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 3"):
            FactionIntent(
                faction_id="faction-123",
                rationale="Test rationale",
                priority=0,
            )

    @pytest.mark.unit
    def test_validation_priority_above_range(self):
        """Test that priority above 3 fails validation."""
        with pytest.raises(ValueError, match="Priority must be between 1 and 3"):
            FactionIntent(
                faction_id="faction-123",
                rationale="Test rationale",
                priority=4,
            )

    @pytest.mark.unit
    def test_valid_priority_boundaries(self):
        """Test that priority boundaries 1 and 3 are valid."""
        intent_min = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
            priority=1,
        )
        intent_max = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
            priority=3,
        )

        assert intent_min.priority == 1
        assert intent_max.priority == 3


class TestFactionIntentStatusTransitions:
    """Test suite for FactionIntent status transitions."""

    @pytest.mark.unit
    def test_select_from_proposed(self):
        """Test selecting an intent from PROPOSED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        assert intent.status == IntentStatus.PROPOSED

        intent.select()
        assert intent.status == IntentStatus.SELECTED

    @pytest.mark.unit
    def test_execute_from_selected(self):
        """Test executing an intent from SELECTED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.select()
        intent.execute()

        assert intent.status == IntentStatus.EXECUTED

    @pytest.mark.unit
    def test_reject_from_proposed(self):
        """Test rejecting an intent from PROPOSED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.reject()

        assert intent.status == IntentStatus.REJECTED

    @pytest.mark.unit
    def test_reject_from_selected(self):
        """Test rejecting an intent from SELECTED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.select()
        intent.reject()

        assert intent.status == IntentStatus.REJECTED

    @pytest.mark.unit
    def test_cannot_execute_from_proposed(self):
        """Test that EXECUTED from PROPOSED is invalid."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )

        with pytest.raises(
            ValueError, match="Cannot transition from proposed to executed"
        ):
            intent.execute()

    @pytest.mark.unit
    def test_cannot_transition_from_executed(self):
        """Test that EXECUTED is a terminal state."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.select()
        intent.execute()

        with pytest.raises(ValueError, match="Cannot transition from executed"):
            intent.reject()

    @pytest.mark.unit
    def test_cannot_transition_from_rejected(self):
        """Test that REJECTED is a terminal state."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.reject()

        with pytest.raises(ValueError, match="Cannot transition from rejected"):
            intent.select()


class TestFactionIntentProperties:
    """Test suite for FactionIntent properties."""

    @pytest.mark.unit
    def test_is_offensive_for_attack(self):
        """Test is_offensive returns True for ATTACK."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.ATTACK,
            target_id="enemy-456",
            rationale="Attack the enemy",
        )
        assert intent.is_offensive is True
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_is_offensive_for_sabotage(self):
        """Test is_offensive returns True for SABOTAGE."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.SABOTAGE,
            target_id="rival-456",
            rationale="Sabotage the rival",
        )
        assert intent.is_offensive is True
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_is_defensive_for_stabilize(self):
        """Test is_defensive returns True for STABILIZE."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.STABILIZE,
            rationale="Fortify our borders",
        )
        assert intent.is_defensive is True
        assert intent.is_offensive is False

    @pytest.mark.unit
    def test_expand_is_offensive_legacy(self):
        """Test EXPAND is considered offensive (legacy behavior)."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.EXPAND,
            rationale="Expand territory",
        )
        # EXPAND is in OFFENSIVE_INTENTS for backward compatibility
        assert intent.is_offensive is True
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_neither_offensive_nor_defensive_for_trade(self):
        """Test TRADE is neither offensive nor defensive."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.TRADE,
            rationale="Establish trade routes",
        )
        assert intent.is_offensive is False
        assert intent.is_defensive is False

    @pytest.mark.unit
    def test_is_terminal_for_executed(self):
        """Test is_terminal returns True for EXECUTED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.select()
        intent.execute()

        assert intent.is_terminal is True
        assert intent.is_active is False

    @pytest.mark.unit
    def test_is_terminal_for_rejected(self):
        """Test is_terminal returns True for REJECTED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.reject()

        assert intent.is_terminal is True
        assert intent.is_active is False

    @pytest.mark.unit
    def test_is_active_for_proposed(self):
        """Test is_active returns True for PROPOSED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )

        assert intent.is_active is True
        assert intent.is_terminal is False

    @pytest.mark.unit
    def test_is_active_for_selected(self):
        """Test is_active returns True for SELECTED status."""
        intent = FactionIntent(
            faction_id="faction-123",
            rationale="Test rationale",
        )
        intent.select()

        assert intent.is_active is True
        assert intent.is_terminal is False


class TestFactionIntentSerialization:
    """Test suite for FactionIntent serialization."""

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict returns correct dictionary."""
        created_at = datetime(2026, 2, 28, 12, 0, 0)
        intent = FactionIntent(
            id="intent-123",
            faction_id="faction-456",
            action_type=ActionType.ATTACK,
            target_id="enemy-789",
            priority=1,
            rationale="Attack the enemy stronghold",
            created_at=created_at,
        )

        result = intent.to_dict()

        assert result["id"] == "intent-123"
        assert result["faction_id"] == "faction-456"
        assert result["action_type"] == "attack"
        assert result["target_id"] == "enemy-789"
        assert result["priority"] == 1
        assert result["rationale"] == "Attack the enemy stronghold"
        assert result["status"] == "proposed"
        assert result["created_at"] == "2026-02-28T12:00:00"
        assert result["is_offensive"] is True
        assert result["is_defensive"] is False

    @pytest.mark.unit
    def test_to_dict_with_none_target(self):
        """Test to_dict handles None target_id."""
        intent = FactionIntent(
            faction_id="faction-123",
            action_type=ActionType.STABILIZE,
            rationale="Internal focus",
        )

        result = intent.to_dict()
        assert result["target_id"] is None

    @pytest.mark.unit
    def test_from_dict_with_all_fields(self):
        """Test from_dict creates intent from complete dictionary."""
        data = {
            "id": "intent-123",
            "faction_id": "faction-456",
            "action_type": "expand",
            "target_id": "location-789",
            "priority": 1,
            "rationale": "Expand territory",
            "status": "proposed",
            "created_at": "2026-02-28T12:00:00",
        }

        intent = FactionIntent.from_dict(data)

        assert intent.id == "intent-123"
        assert intent.faction_id == "faction-456"
        assert intent.action_type == ActionType.EXPAND
        assert intent.target_id == "location-789"
        assert intent.priority == 1
        assert intent.rationale == "Expand territory"
        assert intent.status == IntentStatus.PROPOSED
        assert intent.created_at == datetime(2026, 2, 28, 12, 0, 0)

    @pytest.mark.unit
    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing fields."""
        data = {
            "faction_id": "faction-123",
            "rationale": "Test rationale",
        }

        intent = FactionIntent.from_dict(data)

        assert intent.faction_id == "faction-123"
        assert intent.rationale == "Test rationale"
        assert intent.action_type == ActionType.STABILIZE
        assert intent.target_id is None
        assert intent.priority == 2
        assert intent.status == IntentStatus.PROPOSED

    @pytest.mark.unit
    def test_from_dict_case_insensitive_action_type(self):
        """Test from_dict handles case-insensitive action_type."""
        data = {
            "faction_id": "faction-123",
            "action_type": "ATTACK",
            "rationale": "Attack enemy",
        }

        intent = FactionIntent.from_dict(data)
        assert intent.action_type == ActionType.ATTACK

    @pytest.mark.unit
    def test_from_dict_with_action_type_enum(self):
        """Test from_dict handles ActionType enum directly."""
        data = {
            "faction_id": "faction-123",
            "action_type": ActionType.SABOTAGE,
            "rationale": "Sabotage enemy",
        }

        intent = FactionIntent.from_dict(data)
        assert intent.action_type == ActionType.SABOTAGE

    @pytest.mark.unit
    def test_from_dict_with_status_enum(self):
        """Test from_dict handles IntentStatus enum directly."""
        data = {
            "faction_id": "faction-123",
            "action_type": ActionType.EXPAND,
            "rationale": "Expand territory",
            "status": IntentStatus.SELECTED,
        }

        intent = FactionIntent.from_dict(data)
        assert intent.status == IntentStatus.SELECTED

    @pytest.mark.unit
    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves all data."""
        original = FactionIntent(
            id="intent-123",
            faction_id="faction-456",
            action_type=ActionType.TRADE,
            target_id="trade-partner-789",
            priority=2,
            rationale="Establish trade routes",
            status=IntentStatus.SELECTED,
            created_at=datetime(2026, 2, 28, 12, 0, 0),
        )

        data = original.to_dict()
        restored = FactionIntent.from_dict(data)

        assert restored.id == original.id
        assert restored.faction_id == original.faction_id
        assert restored.action_type == original.action_type
        assert restored.target_id == original.target_id
        assert restored.priority == original.priority
        assert restored.rationale == original.rationale
        assert restored.status == original.status
        assert restored.created_at == original.created_at


class TestFactionIntentStringRepresentation:
    """Test suite for FactionIntent string representations."""

    @pytest.mark.unit
    def test_str_representation(self):
        """Test __str__ returns expected format."""
        intent = FactionIntent(
            id="intent-12345678",
            faction_id="faction-abcdefgh",
            action_type=ActionType.ATTACK,
            priority=1,
            rationale="Attack enemy",
        )

        result = str(intent)

        assert "FactionIntent" in result
        assert "attack" in result
        assert "priority=1" in result
        assert "status=proposed" in result
        assert "faction" in result

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test __repr__ returns expected format."""
        intent = FactionIntent(
            id="intent-12345678",
            faction_id="faction-abcdefgh",
            action_type=ActionType.EXPAND,
            priority=2,
            rationale="Expand territory",
        )

        result = repr(intent)

        assert "FactionIntent" in result
        assert "expand" in result
        assert "priority=2" in result
        assert "status=proposed" in result
        assert "id" in result
