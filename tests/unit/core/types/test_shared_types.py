#!/usr/bin/env python3
"""
Unit tests for src/core/types/shared_types.py module.

Tests cover:
- Enum classes and their values
- Pydantic model instantiation
- Field validation
- Model serialization/deserialization
- Edge cases and error conditions
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID
import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from src.core.types.shared_types import (
    # Enums
    ActionPriority,
    ActionType,
    ActionIntensity,
    EntityType,
    ValidationResult,
    FogOfWarChannel,
    SimulationPhase,
    # Type aliases
    CharacterId,
    UserId,
    KnowledgeEntryId,
    # Models
    Position,
    BoundingBox,
    Area,
    ResourceValue,
    Equipment,
    CharacterStats,
    CharacterResources,
    CharacterState,
    CharacterData,
    ActionTarget,
    ActionParameters,
    ProposedAction,
    ValidatedAction,
    IronLawsViolation,
    IronLawsReport,
    WorldEntity,
    EnvironmentalCondition,
    WorldState,
    InformationSource,
    InformationFragment,
    FogOfWarFilter,
    FilteredWorldView,
    KnowledgeFragment,
    ContextualPrompt,
    TurnBrief,
    SimulationConfig,
    SimulationState,
    TurnResult,
    APIResponse,
    SystemStatus,
    CacheEntry,
    PerformanceMetrics,
    StateHash,
    ConsistencyCheck,
    CharacterAction,
    # Registry
    MODEL_REGISTRY,
)


class TestEnums:
    """Tests for enum class definitions."""

    def test_action_priority_values(self):
        """Test ActionPriority enum values."""
        assert ActionPriority.LOW.value == "low"
        assert ActionPriority.MEDIUM.value == "medium"
        assert ActionPriority.NORMAL.value == "normal"
        assert ActionPriority.HIGH.value == "high"
        assert ActionPriority.CRITICAL.value == "critical"

    def test_action_type_values(self):
        """Test ActionType enum values."""
        assert ActionType.MOVE.value == "move"
        assert ActionType.ATTACK.value == "attack"
        assert ActionType.DEFEND.value == "defend"
        assert ActionType.COMMUNICATE.value == "communicate"
        assert ActionType.OBSERVE.value == "observe"
        assert ActionType.USE_ITEM.value == "use_item"
        assert ActionType.SPECIAL_ABILITY.value == "special_ability"
        assert ActionType.WAIT.value == "wait"
        assert ActionType.RETREAT.value == "retreat"
        assert ActionType.FORTIFY.value == "fortify"
        assert ActionType.INVESTIGATE.value == "investigate"
        assert ActionType.INTERACT.value == "interact"
        assert ActionType.OTHER.value == "other"

    def test_action_intensity_values(self):
        """Test ActionIntensity enum values."""
        assert ActionIntensity.LOW.value == "low"
        assert ActionIntensity.NORMAL.value == "normal"
        assert ActionIntensity.HIGH.value == "high"
        assert ActionIntensity.EXTREME.value == "extreme"

    def test_entity_type_values(self):
        """Test EntityType enum values."""
        assert EntityType.CHARACTER.value == "character"
        assert EntityType.OBJECT.value == "object"
        assert EntityType.LOCATION.value == "location"
        assert EntityType.EVENT.value == "event"
        assert EntityType.RESOURCE.value == "resource"
        assert EntityType.STRUCTURE.value == "structure"

    def test_validation_result_values(self):
        """Test ValidationResult enum values."""
        assert ValidationResult.VALID.value == "valid"
        assert ValidationResult.INVALID.value == "invalid"
        assert ValidationResult.REQUIRES_REPAIR.value == "requires_repair"
        assert ValidationResult.CATASTROPHIC_FAILURE.value == "catastrophic_failure"

    def test_fog_of_war_channel_values(self):
        """Test FogOfWarChannel enum values."""
        assert FogOfWarChannel.VISUAL.value == "visual"
        assert FogOfWarChannel.RADIO.value == "radio"
        assert FogOfWarChannel.INTEL.value == "intel"
        assert FogOfWarChannel.RUMOR.value == "rumor"
        assert FogOfWarChannel.SENSOR.value == "sensor"

    def test_simulation_phase_values(self):
        """Test SimulationPhase enum values."""
        assert SimulationPhase.INITIALIZATION.value == "initialization"
        assert SimulationPhase.PLANNING.value == "planning"
        assert SimulationPhase.EXECUTION.value == "execution"
        assert SimulationPhase.RESOLUTION.value == "resolution"
        assert SimulationPhase.CLEANUP.value == "cleanup"
        assert SimulationPhase.COMPLETED.value == "completed"


class TestTypeAliases:
    """Tests for type alias definitions."""

    def test_character_id_is_str(self):
        """Test CharacterId type alias."""
        assert CharacterId is str

    def test_user_id_is_str(self):
        """Test UserId type alias."""
        assert UserId is str

    def test_knowledge_entry_id_is_str(self):
        """Test KnowledgeEntryId type alias."""
        assert KnowledgeEntryId is str


class TestPosition:
    """Tests for Position model."""

    def test_basic_instantiation(self):
        """Test basic Position creation."""
        pos = Position(x=1.0, y=2.0)
        assert pos.x == 1.0
        assert pos.y == 2.0
        assert pos.z == 0.0  # Default
        assert pos.facing is None  # Default
        assert pos.accuracy == 1.0  # Default

    def test_full_instantiation(self):
        """Test Position with all fields."""
        pos = Position(x=1.0, y=2.0, z=3.0, facing=45.0, accuracy=0.95)
        assert pos.x == 1.0
        assert pos.y == 2.0
        assert pos.z == 3.0
        assert pos.facing == 45.0
        assert pos.accuracy == 0.95

    def test_facing_validation_valid(self):
        """Test facing validation with valid values."""
        pos = Position(x=0, y=0, facing=0)
        assert pos.facing == 0
        pos = Position(x=0, y=0, facing=359.9)
        assert pos.facing == 359.9
        pos = Position(x=0, y=0, facing=None)
        assert pos.facing is None

    def test_facing_validation_invalid(self):
        """Test facing validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            Position(x=0, y=0, facing=-1)
        assert "facing must be between 0 and 360 degrees" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Position(x=0, y=0, facing=360)
        assert "facing must be between 0 and 360 degrees" in str(exc_info.value)

    def test_accuracy_validation_valid(self):
        """Test accuracy validation with valid values."""
        pos = Position(x=0, y=0, accuracy=0)
        assert pos.accuracy == 0
        pos = Position(x=0, y=0, accuracy=1)
        assert pos.accuracy == 1
        pos = Position(x=0, y=0, accuracy=0.5)
        assert pos.accuracy == 0.5

    def test_accuracy_validation_invalid(self):
        """Test accuracy validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            Position(x=0, y=0, accuracy=-0.1)
        assert "accuracy must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Position(x=0, y=0, accuracy=1.1)
        assert "accuracy must be between 0 and 1" in str(exc_info.value)

    def test_serialization(self):
        """Test Position serialization."""
        pos = Position(x=1.0, y=2.0, z=3.0, facing=45.0, accuracy=0.95)
        data = pos.model_dump()
        assert data["x"] == 1.0
        assert data["y"] == 2.0
        assert data["z"] == 3.0
        assert data["facing"] == 45.0
        assert data["accuracy"] == 0.95


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_basic_instantiation(self):
        """Test basic BoundingBox creation."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        assert bbox.min_x == 0
        assert bbox.min_y == 0
        assert bbox.max_x == 10
        assert bbox.max_y == 10

    def test_validation_invalid_bounds_x(self):
        """Test validation when max_x <= min_x."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_x=10, min_y=0, max_x=10, max_y=10)
        assert "max_x must be greater than min_x" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_x=10, min_y=0, max_x=5, max_y=10)
        assert "max_x must be greater than min_x" in str(exc_info.value)

    def test_validation_invalid_bounds_y(self):
        """Test validation when max_y <= min_y."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_x=0, min_y=10, max_x=10, max_y=10)
        assert "max_y must be greater than min_y" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_x=0, min_y=10, max_x=10, max_y=5)
        assert "max_y must be greater than min_y" in str(exc_info.value)


class TestArea:
    """Tests for Area model."""

    def test_basic_instantiation(self):
        """Test basic Area creation."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        assert area.name == "TestArea"
        assert area.bounds == bbox
        assert area.area_type == "room"
        assert area.properties == {}  # Default

    def test_with_properties(self):
        """Test Area with custom properties."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        props = {"temperature": 20, "lighting": "bright"}
        area = Area(name="TestArea", bounds=bbox, area_type="room", properties=props)
        assert area.properties == props


class TestResourceValue:
    """Tests for ResourceValue model."""

    def test_basic_instantiation(self):
        """Test basic ResourceValue creation."""
        resource = ResourceValue(current=50, maximum=100)
        assert resource.current == 50
        assert resource.maximum == 100
        assert resource.minimum == 0.0  # Default
        assert resource.regeneration_rate == 0.0  # Default

    def test_full_instantiation(self):
        """Test ResourceValue with all fields."""
        resource = ResourceValue(current=75, maximum=100, minimum=10, regeneration_rate=5.0)
        assert resource.current == 75
        assert resource.maximum == 100
        assert resource.minimum == 10
        assert resource.regeneration_rate == 5.0

    def test_validation_negative_maximum(self):
        """Test validation with non-positive maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=50, maximum=0)
        assert "maximum must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=50, maximum=-10)
        assert "maximum must be positive" in str(exc_info.value)

    def test_validation_current_below_minimum(self):
        """Test validation when current < minimum."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=5, maximum=100, minimum=10)
        assert "current cannot be below minimum" in str(exc_info.value)

    def test_validation_current_above_maximum(self):
        """Test validation when current > maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=150, maximum=100)
        assert "current cannot exceed maximum" in str(exc_info.value)

    def test_validation_minimum_exceeds_maximum(self):
        """Test validation when minimum > maximum (caught by current < minimum check)."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=50, maximum=50, minimum=60)
        # Validation order may vary, but it should fail validation
        assert "current cannot be below minimum" in str(exc_info.value)

    def test_percentage_property(self):
        """Test percentage property calculation."""
        resource = ResourceValue(current=50, maximum=100)
        assert resource.percentage == 50.0

        resource = ResourceValue(current=25, maximum=100)
        assert resource.percentage == 25.0

        resource = ResourceValue(current=0, maximum=100)
        assert resource.percentage == 0.0

    def test_percentage_property_zero_maximum(self):
        """Test percentage property with zero maximum (edge case)."""
        resource = ResourceValue(current=0, maximum=1)
        assert resource.percentage == 0.0


class TestEquipment:
    """Tests for Equipment model."""

    def test_basic_instantiation(self):
        """Test basic Equipment creation."""
        equip = Equipment(name="Sword", equipment_type="weapon")
        assert equip.name == "Sword"
        assert equip.equipment_type == "weapon"
        assert equip.condition == 1.0  # Default
        assert equip.properties == {}  # Default
        assert equip.quantity == 1  # Default

    def test_condition_validation_valid(self):
        """Test condition validation with valid values."""
        equip = Equipment(name="Sword", equipment_type="weapon", condition=0.5)
        assert equip.condition == 0.5
        equip = Equipment(name="Sword", equipment_type="weapon", condition=0)
        assert equip.condition == 0
        equip = Equipment(name="Sword", equipment_type="weapon", condition=1)
        assert equip.condition == 1

    def test_condition_validation_invalid(self):
        """Test condition validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            Equipment(name="Sword", equipment_type="weapon", condition=-0.1)
        assert "condition must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            Equipment(name="Sword", equipment_type="weapon", condition=1.1)
        assert "condition must be between 0 and 1" in str(exc_info.value)

    def test_quantity_validation_valid(self):
        """Test quantity validation with valid values."""
        equip = Equipment(name="Arrow", equipment_type="ammo", quantity=10)
        assert equip.quantity == 10
        equip = Equipment(name="Arrow", equipment_type="ammo", quantity=0)
        assert equip.quantity == 0

    def test_quantity_validation_invalid(self):
        """Test quantity validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            Equipment(name="Arrow", equipment_type="ammo", quantity=-1)
        assert "quantity cannot be negative" in str(exc_info.value)


class TestCharacterStats:
    """Tests for CharacterStats model."""

    def test_basic_instantiation(self):
        """Test basic CharacterStats creation."""
        stats = CharacterStats(
            strength=5,
            dexterity=6,
            intelligence=7,
            willpower=5,
            perception=6,
            charisma=7,
        )
        assert stats.strength == 5
        assert stats.dexterity == 6
        assert stats.intelligence == 7
        assert stats.willpower == 5
        assert stats.perception == 6
        assert stats.charisma == 7

    @pytest.mark.parametrize("stat_name", [
        "strength", "dexterity", "intelligence",
        "willpower", "perception", "charisma"
    ])
    def test_stat_validation_valid(self, stat_name):
        """Test stat validation with valid values."""
        stats_data = {
            "strength": 5, "dexterity": 5, "intelligence": 5,
            "willpower": 5, "perception": 5, "charisma": 5,
        }
        stats_data[stat_name] = 1  # Minimum
        stats = CharacterStats(**stats_data)
        assert getattr(stats, stat_name) == 1

        stats_data[stat_name] = 10  # Maximum
        stats = CharacterStats(**stats_data)
        assert getattr(stats, stat_name) == 10

    @pytest.mark.parametrize("stat_name", [
        "strength", "dexterity", "intelligence",
        "willpower", "perception", "charisma"
    ])
    def test_stat_validation_invalid(self, stat_name):
        """Test stat validation with invalid values."""
        stats_data = {
            "strength": 5, "dexterity": 5, "intelligence": 5,
            "willpower": 5, "perception": 5, "charisma": 5,
        }
        stats_data[stat_name] = 0  # Too low
        with pytest.raises(ValidationError) as exc_info:
            CharacterStats(**stats_data)
        assert "stats must be between 1 and 10" in str(exc_info.value)

        stats_data[stat_name] = 11  # Too high
        with pytest.raises(ValidationError) as exc_info:
            CharacterStats(**stats_data)
        assert "stats must be between 1 and 10" in str(exc_info.value)


class TestCharacterState:
    """Tests for CharacterState model."""

    def test_basic_instantiation(self):
        """Test basic CharacterState creation."""
        state = CharacterState()
        assert state.conscious is True  # Default
        assert state.mobile is True  # Default
        assert state.combat_ready is True  # Default
        assert state.status_effects == []  # Default
        assert state.injuries == []  # Default
        assert state.fatigue_level == 0.0  # Default

    def test_fatigue_validation_valid(self):
        """Test fatigue_level validation with valid values."""
        state = CharacterState(fatigue_level=0.5)
        assert state.fatigue_level == 0.5
        state = CharacterState(fatigue_level=0)
        assert state.fatigue_level == 0
        state = CharacterState(fatigue_level=1)
        assert state.fatigue_level == 1

    def test_fatigue_validation_invalid(self):
        """Test fatigue_level validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterState(fatigue_level=-0.1)
        assert "fatigue_level must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CharacterState(fatigue_level=1.1)
        assert "fatigue_level must be between 0 and 1" in str(exc_info.value)


class TestCharacterResources:
    """Tests for CharacterResources model."""

    def test_basic_instantiation(self):
        """Test basic CharacterResources creation."""
        health = ResourceValue(current=100, maximum=100)
        stamina = ResourceValue(current=50, maximum=50)
        morale = ResourceValue(current=75, maximum=100)
        resources = CharacterResources(health=health, stamina=stamina, morale=morale)
        assert resources.health == health
        assert resources.stamina == stamina
        assert resources.morale == morale
        assert resources.ammo == {}  # Default
        assert resources.special_resources == {}  # Default

    def test_with_ammo_and_special(self):
        """Test CharacterResources with ammo and special resources."""
        health = ResourceValue(current=100, maximum=100)
        stamina = ResourceValue(current=50, maximum=50)
        morale = ResourceValue(current=75, maximum=100)
        ammo = {"arrows": 50, "bullets": 30}
        special = {"mana": ResourceValue(current=50, maximum=100)}
        resources = CharacterResources(
            health=health, stamina=stamina, morale=morale,
            ammo=ammo, special_resources=special
        )
        assert resources.ammo == ammo
        assert resources.special_resources == special


class TestActionParameters:
    """Tests for ActionParameters model."""

    def test_basic_instantiation(self):
        """Test basic ActionParameters creation."""
        params = ActionParameters()
        assert params.intensity == ActionIntensity.NORMAL  # Default
        assert params.duration == 1.0  # Default
        assert params.range == 1.0  # Default
        assert params.modifiers == {}  # Default
        assert params.resources_consumed == {}  # Default
        assert params.conditions == []  # Default

    def test_intensity_as_float(self):
        """Test ActionParameters with float intensity."""
        params = ActionParameters(intensity=0.5)
        assert params.intensity == 0.5

    def test_duration_validation_valid(self):
        """Test duration validation with valid values."""
        params = ActionParameters(duration=0)
        assert params.duration == 0
        params = ActionParameters(duration=5.5)
        assert params.duration == 5.5

    def test_duration_validation_invalid(self):
        """Test duration validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ActionParameters(duration=-1)
        assert "value must be non-negative" in str(exc_info.value)

    def test_range_validation_valid(self):
        """Test range validation with valid values."""
        params = ActionParameters(range=0)
        assert params.range == 0
        params = ActionParameters(range=10.5)
        assert params.range == 10.5

    def test_range_validation_invalid(self):
        """Test range validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ActionParameters(range=-0.5)
        assert "value must be non-negative" in str(exc_info.value)


class TestProposedAction:
    """Tests for ProposedAction model."""

    def test_basic_instantiation(self):
        """Test basic ProposedAction creation."""
        action = ProposedAction(character_id="char_001", action_type=ActionType.MOVE)
        assert action.character_id == "char_001"
        assert action.action_type == ActionType.MOVE
        assert action.action_id is not None  # Auto-generated
        assert isinstance(action.action_id, str)
        assert action.target is None  # Default
        assert action.confidence == 0.5  # Default

    def test_confidence_validation_valid(self):
        """Test confidence validation with valid values."""
        action = ProposedAction(
            character_id="char_001", action_type=ActionType.MOVE, confidence=0.75
        )
        assert action.confidence == 0.75
        action = ProposedAction(
            character_id="char_001", action_type=ActionType.MOVE, confidence=0
        )
        assert action.confidence == 0
        action = ProposedAction(
            character_id="char_001", action_type=ActionType.MOVE, confidence=1
        )
        assert action.confidence == 1

    def test_confidence_validation_invalid(self):
        """Test confidence validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ProposedAction(
                character_id="char_001", action_type=ActionType.MOVE, confidence=-0.1
            )
        assert "confidence must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ProposedAction(
                character_id="char_001", action_type=ActionType.MOVE, confidence=1.1
            )
        assert "confidence must be between 0 and 1" in str(exc_info.value)


class TestIronLawsReport:
    """Tests for IronLawsReport model."""

    def test_basic_instantiation(self):
        """Test basic IronLawsReport creation."""
        report = IronLawsReport(action_id="action_001", overall_result=ValidationResult.VALID)
        assert report.action_id == "action_001"
        assert report.overall_result == ValidationResult.VALID
        assert report.violations == []  # Default
        assert report.checks_performed == []  # Default
        assert report.timestamp is not None

    def test_has_critical_violations_property(self):
        """Test has_critical_violations property."""
        report = IronLawsReport(action_id="action_001", overall_result=ValidationResult.VALID)
        assert report.has_critical_violations is False

        violation = IronLawsViolation(
            law_code="L001", law_name="Test Law", severity="critical", description="Test"
        )
        report = IronLawsReport(
            action_id="action_001",
            overall_result=ValidationResult.INVALID,
            violations=[violation]
        )
        assert report.has_critical_violations is True

    def test_violation_count_by_severity_property(self):
        """Test violation_count_by_severity property."""
        violations = [
            IronLawsViolation(law_code="L001", law_name="Law1", severity="critical", description="D1"),
            IronLawsViolation(law_code="L002", law_name="Law2", severity="error", description="D2"),
            IronLawsViolation(law_code="L003", law_name="Law3", severity="error", description="D3"),
            IronLawsViolation(law_code="L004", law_name="Law4", severity="warning", description="D4"),
        ]
        report = IronLawsReport(
            action_id="action_001",
            overall_result=ValidationResult.INVALID,
            violations=violations
        )
        counts = report.violation_count_by_severity
        assert counts["critical"] == 1
        assert counts["error"] == 2
        assert counts["warning"] == 1


class TestWorldState:
    """Tests for WorldState model."""

    def test_basic_instantiation(self):
        """Test basic WorldState creation."""
        world = WorldState(turn_number=1)
        assert world.turn_number == 1
        assert world.entities == {}  # Default
        assert world.global_properties == {}  # Default
        assert world.environmental_conditions == []  # Default
        assert world.timestamp is not None

    def test_turn_number_validation_valid(self):
        """Test turn_number validation with valid values."""
        world = WorldState(turn_number=0)
        assert world.turn_number == 0
        world = WorldState(turn_number=100)
        assert world.turn_number == 100

    def test_turn_number_validation_invalid(self):
        """Test turn_number validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            WorldState(turn_number=-1)
        assert "turn_number must be non-negative" in str(exc_info.value)

    def test_get_entities_by_type(self):
        """Test get_entities_by_type method."""
        entity1 = WorldEntity(entity_id="e1", entity_type=EntityType.CHARACTER, name="Hero")
        entity2 = WorldEntity(entity_id="e2", entity_type=EntityType.CHARACTER, name="Villain")
        entity3 = WorldEntity(entity_id="e3", entity_type=EntityType.OBJECT, name="Sword")
        world = WorldState(
            turn_number=1,
            entities={"e1": entity1, "e2": entity2, "e3": entity3}
        )
        characters = world.get_entities_by_type(EntityType.CHARACTER)
        assert len(characters) == 2
        assert all(e.entity_type == EntityType.CHARACTER for e in characters)
        objects = world.get_entities_by_type(EntityType.OBJECT)
        assert len(objects) == 1
        assert objects[0].entity_id == "e3"


class TestEnvironmentalCondition:
    """Tests for EnvironmentalCondition model."""

    def test_basic_instantiation(self):
        """Test basic EnvironmentalCondition creation."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        condition = EnvironmentalCondition(
            condition_type="fire",
            severity=0.7,
            affected_area=area,
            duration_remaining=60.0
        )
        assert condition.condition_type == "fire"
        assert condition.severity == 0.7
        assert condition.affected_area == area
        assert condition.duration_remaining == 60.0
        assert condition.effects == {}  # Default

    def test_severity_validation_valid(self):
        """Test severity validation with valid values."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        condition = EnvironmentalCondition(
            condition_type="fire", severity=0, affected_area=area, duration_remaining=60.0
        )
        assert condition.severity == 0
        condition = EnvironmentalCondition(
            condition_type="fire", severity=1, affected_area=area, duration_remaining=60.0
        )
        assert condition.severity == 1

    def test_severity_validation_invalid(self):
        """Test severity validation with invalid values."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalCondition(
                condition_type="fire", severity=-0.1, affected_area=area, duration_remaining=60.0
            )
        assert "severity must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalCondition(
                condition_type="fire", severity=1.1, affected_area=area, duration_remaining=60.0
            )
        assert "severity must be between 0 and 1" in str(exc_info.value)


class TestContextualPrompt:
    """Tests for ContextualPrompt model."""

    def test_basic_instantiation(self):
        """Test basic ContextualPrompt creation."""
        prompt = ContextualPrompt(base_prompt="You are a hero.")
        assert prompt.base_prompt == "You are a hero."
        assert prompt.character_context is None  # Default
        assert prompt.world_context is None  # Default
        assert prompt.injected_knowledge == []  # Default
        assert prompt.fog_of_war_mask is None  # Default
        assert prompt.prompt_tokens == 0  # Default

    def test_compile_prompt_basic(self):
        """Test compile_prompt with base only."""
        prompt = ContextualPrompt(base_prompt="Base prompt.")
        assert prompt.compile_prompt() == "Base prompt."

    def test_compile_prompt_with_character_context(self):
        """Test compile_prompt with character context."""
        prompt = ContextualPrompt(
            base_prompt="Base prompt.",
            character_context="You are strong."
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "Character Context" in result
        assert "You are strong." in result

    def test_compile_prompt_with_world_context(self):
        """Test compile_prompt with world context."""
        prompt = ContextualPrompt(
            base_prompt="Base prompt.",
            world_context="The world is dark."
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "World State" in result
        assert "The world is dark." in result

    def test_compile_prompt_with_knowledge(self):
        """Test compile_prompt with injected knowledge."""
        knowledge = [
            KnowledgeFragment(content="Dragons are dangerous.", source="lore", knowledge_type="fact"),
            KnowledgeFragment(content="Swords are sharp.", source="guide", knowledge_type="tip"),
        ]
        prompt = ContextualPrompt(
            base_prompt="Base prompt.",
            injected_knowledge=knowledge
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "Relevant Knowledge" in result
        assert "Dragons are dangerous." in result
        assert "Swords are sharp." in result

    def test_compile_prompt_with_fog_of_war(self):
        """Test compile_prompt with fog of war mask."""
        prompt = ContextualPrompt(
            base_prompt="Base prompt.",
            fog_of_war_mask="Limited visibility."
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "Information Constraints" in result
        assert "Limited visibility." in result

    def test_compile_prompt_full(self):
        """Test compile_prompt with all sections."""
        knowledge = [KnowledgeFragment(content="Test knowledge.", source="test", knowledge_type="test")]
        prompt = ContextualPrompt(
            base_prompt="Base prompt.",
            character_context="Character info.",
            world_context="World info.",
            injected_knowledge=knowledge,
            fog_of_war_mask="Fog info."
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "Character Context" in result
        assert "Character info." in result
        assert "World State" in result
        assert "World info." in result
        assert "Relevant Knowledge" in result
        assert "Test knowledge." in result
        assert "Information Constraints" in result
        assert "Fog info." in result


class TestSimulationConfig:
    """Tests for SimulationConfig model."""

    def test_default_values(self):
        """Test SimulationConfig default values."""
        config = SimulationConfig()
        assert config.max_turns == 10
        assert config.turn_timeout == 30.0
        assert config.max_agents == 20
        assert config.iron_laws_enabled is True
        assert config.fog_of_war_enabled is True
        assert config.rag_injection_enabled is True
        assert config.performance_mode == "balanced"
        assert config.logging_level == "info"

    def test_max_turns_validation_valid(self):
        """Test max_turns validation with valid values."""
        config = SimulationConfig(max_turns=1)
        assert config.max_turns == 1
        config = SimulationConfig(max_turns=100)
        assert config.max_turns == 100

    def test_max_turns_validation_invalid(self):
        """Test max_turns validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(max_turns=0)
        assert "max_turns must be between 1 and 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(max_turns=101)
        assert "max_turns must be between 1 and 100" in str(exc_info.value)

    def test_turn_timeout_validation_valid(self):
        """Test turn_timeout validation with valid values."""
        config = SimulationConfig(turn_timeout=0.1)
        assert config.turn_timeout == 0.1
        config = SimulationConfig(turn_timeout=60.0)
        assert config.turn_timeout == 60.0

    def test_turn_timeout_validation_invalid(self):
        """Test turn_timeout validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(turn_timeout=0)
        assert "turn_timeout must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(turn_timeout=-1)
        assert "turn_timeout must be positive" in str(exc_info.value)

    def test_max_agents_validation_valid(self):
        """Test max_agents validation with valid values."""
        config = SimulationConfig(max_agents=1)
        assert config.max_agents == 1
        config = SimulationConfig(max_agents=100)
        assert config.max_agents == 100

    def test_max_agents_validation_invalid(self):
        """Test max_agents validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(max_agents=0)
        assert "max_agents must be between 1 and 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(max_agents=101)
        assert "max_agents must be between 1 and 100" in str(exc_info.value)


class TestSystemStatus:
    """Tests for SystemStatus model."""

    def test_basic_instantiation(self):
        """Test basic SystemStatus creation."""
        status = SystemStatus(
            status="running",
            uptime_seconds=3600,
            active_simulations=5,
            memory_usage_mb=512.5,
            cpu_usage_percent=25.5
        )
        assert status.system_name == "Novel Engine"  # Default
        assert status.version == "1.0.0"  # Default
        assert status.status == "running"
        assert status.uptime_seconds == 3600
        assert status.active_simulations == 5
        assert status.memory_usage_mb == 512.5
        assert status.cpu_usage_percent == 25.5
        assert status.components == {}  # Default

    def test_uptime_validation_valid(self):
        """Test uptime_seconds validation with valid values."""
        status = SystemStatus(
            status="running", uptime_seconds=0, active_simulations=0,
            memory_usage_mb=0, cpu_usage_percent=0
        )
        assert status.uptime_seconds == 0

    def test_uptime_validation_invalid(self):
        """Test uptime_seconds validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=-1, active_simulations=0,
                memory_usage_mb=0, cpu_usage_percent=0
            )
        assert "value must be non-negative" in str(exc_info.value)

    def test_active_simulations_validation_valid(self):
        """Test active_simulations validation with valid values."""
        status = SystemStatus(
            status="running", uptime_seconds=0, active_simulations=0,
            memory_usage_mb=0, cpu_usage_percent=0
        )
        assert status.active_simulations == 0

    def test_active_simulations_validation_invalid(self):
        """Test active_simulations validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=0, active_simulations=-1,
                memory_usage_mb=0, cpu_usage_percent=0
            )
        assert "active_simulations must be non-negative" in str(exc_info.value)

    def test_cpu_usage_validation_valid(self):
        """Test cpu_usage_percent validation with valid values."""
        status = SystemStatus(
            status="running", uptime_seconds=0, active_simulations=0,
            memory_usage_mb=0, cpu_usage_percent=0
        )
        assert status.cpu_usage_percent == 0
        status = SystemStatus(
            status="running", uptime_seconds=0, active_simulations=0,
            memory_usage_mb=0, cpu_usage_percent=100
        )
        assert status.cpu_usage_percent == 100

    def test_cpu_usage_validation_invalid(self):
        """Test cpu_usage_percent validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=0, active_simulations=0,
                memory_usage_mb=0, cpu_usage_percent=-0.1
            )
        assert "cpu_usage_percent must be between 0 and 100" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=0, active_simulations=0,
                memory_usage_mb=0, cpu_usage_percent=100.1
            )
        assert "cpu_usage_percent must be between 0 and 100" in str(exc_info.value)


class TestCacheEntry:
    """Tests for CacheEntry model."""

    def test_basic_instantiation(self):
        """Test basic CacheEntry creation."""
        entry = CacheEntry(key="test_key", value="test_value")
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0  # Default
        assert entry.ttl_seconds is None  # Default
        assert entry.tags == []  # Default
        assert entry.created_at is not None
        assert entry.last_accessed is not None

    def test_is_expired_no_ttl(self):
        """Test is_expired with no TTL."""
        entry = CacheEntry(key="test_key", value="test_value")
        assert entry.is_expired is False

    def test_is_expired_not_expired(self):
        """Test is_expired when not expired."""
        entry = CacheEntry(key="test_key", value="test_value", ttl_seconds=3600)
        assert entry.is_expired is False

    def test_is_expired_expired(self):
        """Test is_expired when expired."""
        entry = CacheEntry(key="test_key", value="test_value", ttl_seconds=0.001)
        import time
        time.sleep(0.01)
        assert entry.is_expired is True


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics model."""

    def test_basic_instantiation(self):
        """Test basic PerformanceMetrics creation."""
        metrics = PerformanceMetrics(operation_name="test_op", duration_ms=100.5)
        assert metrics.operation_name == "test_op"
        assert metrics.duration_ms == 100.5
        assert metrics.memory_delta_mb == 0.0  # Default
        assert metrics.tokens_consumed == 0  # Default
        assert metrics.cache_hits == 0  # Default
        assert metrics.cache_misses == 0  # Default
        assert metrics.error_count == 0  # Default
        assert metrics.timestamp is not None

    def test_duration_validation_valid(self):
        """Test duration_ms validation with valid values."""
        metrics = PerformanceMetrics(operation_name="test_op", duration_ms=0)
        assert metrics.duration_ms == 0

    def test_duration_validation_invalid(self):
        """Test duration_ms validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            PerformanceMetrics(operation_name="test_op", duration_ms=-1)
        assert "duration_ms must be non-negative" in str(exc_info.value)

    def test_tokens_consumed_validation_valid(self):
        """Test tokens_consumed validation with valid values."""
        metrics = PerformanceMetrics(operation_name="test_op", duration_ms=100, tokens_consumed=0)
        assert metrics.tokens_consumed == 0

    def test_tokens_consumed_validation_invalid(self):
        """Test tokens_consumed validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            PerformanceMetrics(operation_name="test_op", duration_ms=100, tokens_consumed=-1)
        assert "tokens_consumed must be non-negative" in str(exc_info.value)


class TestStateHash:
    """Tests for StateHash model."""

    def test_basic_instantiation(self):
        """Test basic StateHash creation."""
        state_hash = StateHash(
            entity_id="entity_001",
            hash_type="sha256",
            hash_value="a" * 32,
            fields_included=["field1", "field2"]
        )
        assert state_hash.entity_id == "entity_001"
        assert state_hash.hash_type == "sha256"
        assert state_hash.hash_value == "a" * 32
        assert state_hash.fields_included == ["field1", "field2"]
        assert state_hash.salt is None  # Default
        assert state_hash.timestamp is not None

    def test_hash_value_validation_valid(self):
        """Test hash_value validation with valid values."""
        state_hash = StateHash(
            entity_id="entity_001", hash_type="sha256",
            hash_value="a" * 32, fields_included=["field1"]
        )
        assert len(state_hash.hash_value) >= 32

        state_hash = StateHash(
            entity_id="entity_001", hash_type="sha256",
            hash_value="ABCDEF" * 6 + "1234", fields_included=["field1"]
        )
        assert state_hash.hash_value == "ABCDEF" * 6 + "1234"

    def test_hash_value_validation_too_short(self):
        """Test hash_value validation with too short value."""
        with pytest.raises(ValidationError) as exc_info:
            StateHash(
                entity_id="entity_001", hash_type="sha256",
                hash_value="a" * 31, fields_included=["field1"]
            )
        assert "hash_value must be at least 32 hex characters" in str(exc_info.value)

    def test_hash_value_validation_invalid_chars(self):
        """Test hash_value validation with non-hex characters."""
        with pytest.raises(ValidationError) as exc_info:
            StateHash(
                entity_id="entity_001", hash_type="sha256",
                hash_value="g" * 32, fields_included=["field1"]
            )
        assert "hash_value must be hexadecimal" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            StateHash(
                entity_id="entity_001", hash_type="sha256",
                hash_value="a" * 31 + "!", fields_included=["field1"]
            )
        assert "hash_value must be hexadecimal" in str(exc_info.value)


class TestConsistencyCheck:
    """Tests for ConsistencyCheck model."""

    def test_basic_instantiation(self):
        """Test basic ConsistencyCheck creation."""
        check = ConsistencyCheck(
            entity_ids=["e1", "e2"],
            check_type="state",
            is_consistent=True
        )
        assert check.entity_ids == ["e1", "e2"]
        assert check.check_type == "state"
        assert check.is_consistent is True
        assert check.check_id is not None  # Auto-generated
        assert check.inconsistencies == []  # Default
        assert check.confidence == 1.0  # Default
        assert check.remediation_suggestions == []  # Default

    def test_confidence_validation_valid(self):
        """Test confidence validation with valid values."""
        check = ConsistencyCheck(
            entity_ids=["e1"], check_type="test", is_consistent=True, confidence=0.5
        )
        assert check.confidence == 0.5
        check = ConsistencyCheck(
            entity_ids=["e1"], check_type="test", is_consistent=True, confidence=0
        )
        assert check.confidence == 0
        check = ConsistencyCheck(
            entity_ids=["e1"], check_type="test", is_consistent=True, confidence=1
        )
        assert check.confidence == 1

    def test_confidence_validation_invalid(self):
        """Test confidence validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ConsistencyCheck(
                entity_ids=["e1"], check_type="test", is_consistent=True, confidence=-0.1
            )
        assert "confidence must be between 0 and 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ConsistencyCheck(
                entity_ids=["e1"], check_type="test", is_consistent=True, confidence=1.1
            )
        assert "confidence must be between 0 and 1" in str(exc_info.value)


class TestCharacterAction:
    """Tests for CharacterAction model."""

    def test_basic_instantiation(self):
        """Test basic CharacterAction creation."""
        action = CharacterAction(action_type="move")
        assert action.action_type == "move"
        assert action.agent_id is None  # Default
        assert action.target is None  # Default
        assert action.priority == ActionPriority.NORMAL  # Default
        assert action.reasoning is None  # Default
        assert action.parameters == {}  # Default

    def test_action_type_validation_valid(self):
        """Test action_type validation with valid values."""
        action = CharacterAction(action_type="attack")
        assert action.action_type == "attack"
        action = CharacterAction(action_type="Move")
        assert action.action_type == "Move"

    def test_action_type_validation_invalid(self):
        """Test action_type validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterAction(action_type="")
        assert "action_type cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            CharacterAction(action_type="   ")
        assert "action_type cannot be empty" in str(exc_info.value)

    def test_priority_validation_with_enum(self):
        """Test priority validation with enum value."""
        action = CharacterAction(action_type="move", priority=ActionPriority.HIGH)
        assert action.priority == ActionPriority.HIGH

    def test_priority_validation_with_string(self):
        """Test priority validation with string value (lowercase)."""
        action = CharacterAction(action_type="move", priority="high")
        assert action.priority == ActionPriority.HIGH
        action = CharacterAction(action_type="move", priority="critical")
        assert action.priority == ActionPriority.CRITICAL


class TestModelRegistry:
    """Tests for MODEL_REGISTRY."""

    def test_registry_contains_expected_models(self):
        """Test MODEL_REGISTRY contains expected model entries."""
        expected_keys = [
            "character_data",
            "world_state",
            "proposed_action",
            "validated_action",
            "iron_laws_report",
            "turn_brief",
            "simulation_state",
            "turn_result",
            "api_response",
        ]
        for key in expected_keys:
            assert key in MODEL_REGISTRY

    def test_registry_models_are_callable(self):
        """Test MODEL_REGISTRY values are callable model classes."""
        for key, model_class in MODEL_REGISTRY.items():
            assert callable(model_class)
            assert hasattr(model_class, "model_validate")
            assert hasattr(model_class, "model_dump")

    def test_character_data_model(self):
        """Test character_data model can be instantiated."""
        model_class = MODEL_REGISTRY["character_data"]
        position = Position(x=0, y=0)
        stats = CharacterStats(
            strength=5, dexterity=5, intelligence=5,
            willpower=5, perception=5, charisma=5
        )
        resources = CharacterResources(
            health=ResourceValue(current=100, maximum=100),
            stamina=ResourceValue(current=50, maximum=50),
            morale=ResourceValue(current=75, maximum=100)
        )
        character = model_class(
            character_id="char_001",
            name="Test Character",
            faction="allies",
            position=position,
            stats=stats,
            resources=resources
        )
        assert character.character_id == "char_001"
        assert character.name == "Test Character"


class TestSerialization:
    """Tests for model serialization and deserialization."""

    def test_position_roundtrip(self):
        """Test Position serialization roundtrip."""
        original = Position(x=1.0, y=2.0, z=3.0, facing=45.0, accuracy=0.95)
        data = original.model_dump()
        restored = Position(**data)
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.z == original.z
        assert restored.facing == original.facing
        assert restored.accuracy == original.accuracy

    def test_resource_value_roundtrip(self):
        """Test ResourceValue serialization roundtrip."""
        original = ResourceValue(current=50, maximum=100, minimum=10, regeneration_rate=5.0)
        data = original.model_dump()
        restored = ResourceValue(**data)
        assert restored.current == original.current
        assert restored.maximum == original.maximum
        assert restored.minimum == original.minimum
        assert restored.regeneration_rate == original.regeneration_rate

    def test_json_serialization(self):
        """Test JSON serialization."""
        import json
        pos = Position(x=1.0, y=2.0)
        data = pos.model_dump()
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        restored = Position(**restored_data)
        assert restored.x == pos.x
        assert restored.y == pos.y


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string_values(self):
        """Test models with empty string values."""
        with pytest.raises(ValidationError):
            CharacterAction(action_type="")

    def test_unicode_values(self):
        """Test models with unicode values."""
        pos = Position(x=1.0, y=2.0)
        character = CharacterData(
            character_id="char_001",
            name="测试角色 🎮",
            faction="盟友 🛡️",
            position=pos,
            stats=CharacterStats(
                strength=5, dexterity=5, intelligence=5,
                willpower=5, perception=5, charisma=5
            ),
            resources=CharacterResources(
                health=ResourceValue(current=100, maximum=100),
                stamina=ResourceValue(current=50, maximum=50),
                morale=ResourceValue(current=75, maximum=100)
            )
        )
        assert character.name == "测试角色 🎮"
        assert character.faction == "盟友 🛡️"

    def test_nested_model_creation(self):
        """Test deeply nested model creation."""
        world = WorldState(
            turn_number=1,
            entities={
                "e1": WorldEntity(
                    entity_id="e1",
                    entity_type=EntityType.CHARACTER,
                    name="Hero",
                    position=Position(x=0, y=0),
                    properties={"health": 100}
                )
            },
            environmental_conditions=[
                EnvironmentalCondition(
                    condition_type="rain",
                    severity=0.5,
                    affected_area=Area(
                        name="Field",
                        bounds=BoundingBox(min_x=0, min_y=0, max_x=100, max_y=100),
                        area_type="outdoor"
                    ),
                    duration_remaining=300.0
                )
            ]
        )
        assert world.turn_number == 1
        assert "e1" in world.entities
        assert len(world.environmental_conditions) == 1
