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

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from src.core.types.shared_types import (
    # Registry
    MODEL_REGISTRY,
    ActionIntensity,
    ActionParameters,
    # Enums
    ActionPriority,
    ActionType,
    Area,
    BoundingBox,
    CacheEntry,
    CharacterAction,
    # Type aliases
    CharacterId,
    CharacterResources,
    CharacterState,
    CharacterStats,
    ConsistencyCheck,
    ContextualPrompt,
    EntityType,
    EnvironmentalCondition,
    Equipment,
    FogOfWarChannel,
    IronLawsReport,
    IronLawsViolation,
    KnowledgeEntryId,
    PerformanceMetrics,
    # Models
    Position,
    ProposedAction,
    ResourceValue,
    SimulationConfig,
    SimulationPhase,
    StateHash,
    SystemStatus,
    UserId,
    ValidationResult,
    WorldEntity,
    WorldState,
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
        assert pos.z == 0.0
        assert pos.facing is None
        assert pos.accuracy == 1.0

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

    def test_validation_invalid_bounds_y(self):
        """Test validation when max_y <= min_y."""
        with pytest.raises(ValidationError) as exc_info:
            BoundingBox(min_x=0, min_y=10, max_x=10, max_y=10)
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
        assert area.properties == {}


class TestResourceValue:
    """Tests for ResourceValue model."""

    def test_basic_instantiation(self):
        """Test basic ResourceValue creation."""
        resource = ResourceValue(current=50, maximum=100)
        assert resource.current == 50
        assert resource.maximum == 100
        assert resource.minimum == 0.0
        assert resource.regeneration_rate == 0.0

    def test_validation_negative_maximum(self):
        """Test validation with non-positive maximum."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceValue(current=50, maximum=0)
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

    def test_percentage_property(self):
        """Test percentage property calculation."""
        resource = ResourceValue(current=50, maximum=100)
        assert resource.percentage == 50.0

        resource = ResourceValue(current=0, maximum=100)
        assert resource.percentage == 0.0


class TestEquipment:
    """Tests for Equipment model."""

    def test_basic_instantiation(self):
        """Test basic Equipment creation."""
        equip = Equipment(name="Sword", equipment_type="weapon")
        assert equip.name == "Sword"
        assert equip.equipment_type == "weapon"
        assert equip.condition == 1.0
        assert equip.quantity == 1

    def test_condition_validation_invalid(self):
        """Test condition validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            Equipment(name="Sword", equipment_type="weapon", condition=-0.1)
        assert "condition must be between 0 and 1" in str(exc_info.value)

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
            strength=5, dexterity=6, intelligence=7,
            willpower=5, perception=6, charisma=7,
        )
        assert stats.strength == 5
        assert stats.dexterity == 6

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
        stats_data[stat_name] = 0
        with pytest.raises(ValidationError) as exc_info:
            CharacterStats(**stats_data)
        assert "stats must be between 1 and 10" in str(exc_info.value)


class TestCharacterState:
    """Tests for CharacterState model."""

    def test_basic_instantiation(self):
        """Test basic CharacterState creation."""
        state = CharacterState()
        assert state.conscious is True
        assert state.mobile is True
        assert state.fatigue_level == 0.0

    def test_fatigue_validation_invalid(self):
        """Test fatigue_level validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterState(fatigue_level=-0.1)
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


class TestActionParameters:
    """Tests for ActionParameters model."""

    def test_basic_instantiation(self):
        """Test basic ActionParameters creation."""
        params = ActionParameters()
        assert params.intensity.value == "normal"
        assert params.duration == 1.0
        assert params.range == 1.0

    def test_duration_validation_invalid(self):
        """Test duration validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ActionParameters(duration=-1)
        assert "value must be non-negative" in str(exc_info.value)


class TestProposedAction:
    """Tests for ProposedAction model."""

    def test_basic_instantiation(self):
        """Test basic ProposedAction creation."""
        action = ProposedAction(character_id="char_001", action_type=ActionType.MOVE)
        assert action.character_id == "char_001"
        assert action.action_type == ActionType.MOVE
        assert action.action_id is not None
        assert action.confidence == 0.5

    def test_confidence_validation_invalid(self):
        """Test confidence validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ProposedAction(character_id="char_001", action_type=ActionType.MOVE, confidence=-0.1)
        assert "confidence must be between 0 and 1" in str(exc_info.value)


class TestIronLawsReport:
    """Tests for IronLawsReport model."""

    def test_basic_instantiation(self):
        """Test basic IronLawsReport creation."""
        report = IronLawsReport(action_id="action_001", overall_result=ValidationResult.VALID)
        assert report.action_id == "action_001"
        assert report.overall_result == ValidationResult.VALID
        assert report.violations == []

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


class TestWorldState:
    """Tests for WorldState model."""

    def test_basic_instantiation(self):
        """Test basic WorldState creation."""
        world = WorldState(turn_number=1)
        assert world.turn_number == 1
        assert world.entities == {}

    def test_turn_number_validation_invalid(self):
        """Test turn_number validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            WorldState(turn_number=-1)
        assert "turn_number must be non-negative" in str(exc_info.value)

    def test_get_entities_by_type(self):
        """Test get_entities_by_type method."""
        entity1 = WorldEntity(entity_id="e1", entity_type=EntityType.CHARACTER, name="Hero")
        entity2 = WorldEntity(entity_id="e2", entity_type=EntityType.OBJECT, name="Sword")
        world = WorldState(turn_number=1, entities={"e1": entity1, "e2": entity2})
        characters = world.get_entities_by_type(EntityType.CHARACTER)
        assert len(characters) == 1
        assert characters[0].entity_id == "e1"


class TestEnvironmentalCondition:
    """Tests for EnvironmentalCondition model."""

    def test_basic_instantiation(self):
        """Test basic EnvironmentalCondition creation."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        condition = EnvironmentalCondition(
            condition_type="fire", severity=0.7, affected_area=area, duration_remaining=60.0
        )
        assert condition.condition_type == "fire"
        assert condition.severity == 0.7

    def test_severity_validation_invalid(self):
        """Test severity validation with invalid values."""
        bbox = BoundingBox(min_x=0, min_y=0, max_x=10, max_y=10)
        area = Area(name="TestArea", bounds=bbox, area_type="room")
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentalCondition(
                condition_type="fire", severity=-0.1, affected_area=area, duration_remaining=60.0
            )
        assert "severity must be between 0 and 1" in str(exc_info.value)


class TestContextualPrompt:
    """Tests for ContextualPrompt model."""

    def test_basic_instantiation(self):
        """Test basic ContextualPrompt creation."""
        prompt = ContextualPrompt(base_prompt="You are a hero.")
        assert prompt.base_prompt == "You are a hero."
        assert prompt.prompt_tokens == 0

    def test_compile_prompt_basic(self):
        """Test compile_prompt with base only."""
        prompt = ContextualPrompt(base_prompt="Base prompt.")
        assert prompt.compile_prompt() == "Base prompt."

    def test_compile_prompt_with_character_context(self):
        """Test compile_prompt with character context."""
        prompt = ContextualPrompt(
            base_prompt="Base prompt.", character_context="You are strong."
        )
        result = prompt.compile_prompt()
        assert "Base prompt." in result
        assert "Character Context" in result


class TestSimulationConfig:
    """Tests for SimulationConfig model."""

    def test_default_values(self):
        """Test SimulationConfig default values."""
        config = SimulationConfig()
        assert config.max_turns == 10
        assert config.turn_timeout == 30.0
        assert config.max_agents == 20

    def test_max_turns_validation_invalid(self):
        """Test max_turns validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(max_turns=0)
        assert "max_turns must be between 1 and 100" in str(exc_info.value)

    def test_turn_timeout_validation_invalid(self):
        """Test turn_timeout validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SimulationConfig(turn_timeout=0)
        assert "turn_timeout must be positive" in str(exc_info.value)


class TestSystemStatus:
    """Tests for SystemStatus model."""

    def test_basic_instantiation(self):
        """Test basic SystemStatus creation."""
        status = SystemStatus(
            status="running", uptime_seconds=3600, active_simulations=5,
            memory_usage_mb=512.5, cpu_usage_percent=25.5
        )
        assert status.status == "running"
        assert status.uptime_seconds == 3600

    def test_uptime_validation_invalid(self):
        """Test uptime_seconds validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=-1, active_simulations=0,
                memory_usage_mb=0, cpu_usage_percent=0
            )
        assert "value must be non-negative" in str(exc_info.value)

    def test_cpu_usage_validation_invalid(self):
        """Test cpu_usage_percent validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            SystemStatus(
                status="running", uptime_seconds=0, active_simulations=0,
                memory_usage_mb=0, cpu_usage_percent=-0.1
            )
        assert "cpu_usage_percent must be between 0 and 100" in str(exc_info.value)


class TestCacheEntry:
    """Tests for CacheEntry model."""

    def test_basic_instantiation(self):
        """Test basic CacheEntry creation."""
        entry = CacheEntry(key="test_key", value="test_value")
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0

    def test_is_expired_no_ttl(self):
        """Test is_expired with no TTL."""
        entry = CacheEntry(key="test_key", value="test_value")
        assert entry.is_expired is False


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics model."""

    def test_basic_instantiation(self):
        """Test basic PerformanceMetrics creation."""
        metrics = PerformanceMetrics(operation_name="test_op", duration_ms=100.5)
        assert metrics.operation_name == "test_op"
        assert metrics.duration_ms == 100.5

    def test_duration_validation_invalid(self):
        """Test duration_ms validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            PerformanceMetrics(operation_name="test_op", duration_ms=-1)
        assert "duration_ms must be non-negative" in str(exc_info.value)


class TestStateHash:
    """Tests for StateHash model."""

    def test_basic_instantiation(self):
        """Test basic StateHash creation."""
        state_hash = StateHash(
            entity_id="entity_001", hash_type="sha256",
            hash_value="a" * 32, fields_included=["field1"]
        )
        assert state_hash.entity_id == "entity_001"
        assert state_hash.hash_value == "a" * 32

    def test_hash_value_validation_too_short(self):
        """Test hash_value validation with too short value."""
        with pytest.raises(ValidationError) as exc_info:
            StateHash(
                entity_id="entity_001", hash_type="sha256",
                hash_value="a" * 31, fields_included=["field1"]
            )
        assert "hash_value must be at least 32 hex characters" in str(exc_info.value)


class TestConsistencyCheck:
    """Tests for ConsistencyCheck model."""

    def test_basic_instantiation(self):
        """Test basic ConsistencyCheck creation."""
        check = ConsistencyCheck(entity_ids=["e1"], check_type="state", is_consistent=True)
        assert check.entity_ids == ["e1"]
        assert check.is_consistent is True

    def test_confidence_validation_invalid(self):
        """Test confidence validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            ConsistencyCheck(
                entity_ids=["e1"], check_type="test", is_consistent=True, confidence=-0.1
            )
        assert "confidence must be between 0 and 1" in str(exc_info.value)


class TestCharacterAction:
    """Tests for CharacterAction model."""

    def test_basic_instantiation(self):
        """Test basic CharacterAction creation."""
        action = CharacterAction(action_type="move")
        assert action.action_type == "move"
        assert action.priority == ActionPriority.NORMAL

    def test_action_type_validation_invalid(self):
        """Test action_type validation with invalid values."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterAction(action_type="")
        assert "action_type cannot be empty" in str(exc_info.value)


class TestModelRegistry:
    """Tests for MODEL_REGISTRY."""

    def test_registry_contains_expected_models(self):
        """Test MODEL_REGISTRY contains expected model entries."""
        expected_keys = [
            "character_data", "world_state", "proposed_action",
            "validated_action", "iron_laws_report",
        ]
        for key in expected_keys:
            assert key in MODEL_REGISTRY

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
            character_id="char_001", name="Test Character", faction="allies",
            position=position, stats=stats, resources=resources
        )
        assert character.character_id == "char_001"
