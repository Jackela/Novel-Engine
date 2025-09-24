"""
Test Shared Types and Schemas for Novel Engine
===============================================

Comprehensive test suite for the Pydantic model definitions in src.shared_types.
Tests ensure that all data structures provide proper validation, serialization,
and type safety for the Novel Engine system components.

Test Coverage:
- All Pydantic model validation rules
- Enum value validation
- Complex nested model structures
- Type conversion and serialization
- Custom validation logic
- Error handling for invalid data
- Model relationships and dependencies
- JSON serialization/deserialization
- Model registry functionality
"""

import json
from datetime import datetime

import pytest

# Import all shared types for comprehensive testing
try:
    from src.shared_types import (  # Enums; Spatial Types; Resource Types; Character Types; Action Types; Iron Laws Types; World Types; Fog of War Types; Turn Brief Types; Simulation Types; API Types; Performance Types; Consistency Types; Registry
        MODEL_REGISTRY,
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        APIResponse,
        Area,
        BoundingBox,
        CacheEntry,
        CharacterData,
        CharacterResources,
        CharacterState,
        CharacterStats,
        ConsistencyCheck,
        ContextualPrompt,
        EntityType,
        EnvironmentalCondition,
        Equipment,
        FilteredWorldView,
        FogOfWarChannel,
        FogOfWarFilter,
        InformationFragment,
        InformationSource,
        IronLawsReport,
        IronLawsViolation,
        KnowledgeFragment,
        PerformanceMetrics,
        Position,
        ProposedAction,
        ResourceValue,
        SimulationConfig,
        SimulationPhase,
        SimulationState,
        StateHash,
        SystemStatus,
        TurnBrief,
        TurnResult,
        ValidatedAction,
        ValidationResult,
        WorldEntity,
        WorldState,
    )

    SHARED_TYPES_AVAILABLE = True
except ImportError as e:
    SHARED_TYPES_AVAILABLE = False
    pytest.skip(f"Shared types not available: {e}", allow_module_level=True)


class TestEnumTypes:
    """Test enumeration types and their values."""

    def test_action_type_values(self):
        """Test ActionType enum contains expected values."""
        expected_actions = [
            "move",
            "attack",
            "defend",
            "communicate",
            "observe",
            "use_item",
            "special_ability",
            "wait",
            "retreat",
            "fortify",
        ]

        for action in expected_actions:
            assert hasattr(ActionType, action.upper())
            assert ActionType[action.upper()].value == action

    def test_entity_type_values(self):
        """Test EntityType enum contains expected values."""
        expected_entities = [
            "character",
            "object",
            "location",
            "event",
            "resource",
            "structure",
        ]

        for entity in expected_entities:
            assert hasattr(EntityType, entity.upper())
            assert EntityType[entity.upper()].value == entity

    def test_validation_result_values(self):
        """Test ValidationResult enum contains expected values."""
        expected_results = [
            "valid",
            "invalid",
            "requires_repair",
            "catastrophic_failure",
        ]

        for result in expected_results:
            assert hasattr(ValidationResult, result.upper())
            assert ValidationResult[result.upper()].value == result

    def test_fog_of_war_channel_values(self):
        """Test FogOfWarChannel enum contains expected values."""
        expected_channels = ["visual", "radio", "intel", "rumor", "sensor"]

        for channel in expected_channels:
            assert hasattr(FogOfWarChannel, channel.upper())
            assert FogOfWarChannel[channel.upper()].value == channel

    def test_simulation_phase_values(self):
        """Test SimulationPhase enum contains expected values."""
        expected_phases = [
            "initialization",
            "planning",
            "execution",
            "resolution",
            "cleanup",
            "completed",
        ]

        for phase in expected_phases:
            assert hasattr(SimulationPhase, phase.upper())
            assert SimulationPhase[phase.upper()].value == phase


class TestSpatialTypes:
    """Test spatial and coordinate types."""

    def test_position_creation_valid(self):
        """Test Position model with valid data."""
        position = Position(
            x=100.0, y=200.0, z=10.0, facing=270.0, accuracy=0.95
        )

        assert position.x == 100.0
        assert position.y == 200.0
        assert position.z == 10.0
        assert position.facing == 270.0
        assert position.accuracy == 0.95

    def test_position_defaults(self):
        """Test Position model with default values."""
        position = Position(x=50.0, y=75.0)

        assert position.x == 50.0
        assert position.y == 75.0
        assert position.z == 0.0
        assert position.facing is None
        assert position.accuracy == 1.0

    def test_position_facing_validation(self):
        """Test Position facing angle validation."""
        # Valid facing angles
        Position(x=0.0, y=0.0, facing=0.0)
        Position(x=0.0, y=0.0, facing=359.9)

        # Invalid facing angles should raise validation error
        with pytest.raises(ValueError):
            Position(x=0.0, y=0.0, facing=-1.0)

        with pytest.raises(ValueError):
            Position(x=0.0, y=0.0, facing=360.0)

    def test_position_accuracy_validation(self):
        """Test Position accuracy validation."""
        # Valid accuracy values
        Position(x=0.0, y=0.0, accuracy=0.0)
        Position(x=0.0, y=0.0, accuracy=1.0)
        Position(x=0.0, y=0.0, accuracy=0.5)

        # Invalid accuracy values
        with pytest.raises(ValueError):
            Position(x=0.0, y=0.0, accuracy=-0.1)

        with pytest.raises(ValueError):
            Position(x=0.0, y=0.0, accuracy=1.1)

    def test_bounding_box_valid(self):
        """Test BoundingBox with valid coordinates."""
        bbox = BoundingBox(min_x=0.0, min_y=0.0, max_x=100.0, max_y=200.0)

        assert bbox.min_x == 0.0
        assert bbox.min_y == 0.0
        assert bbox.max_x == 100.0
        assert bbox.max_y == 200.0

    def test_bounding_box_validation_errors(self):
        """Test BoundingBox coordinate validation."""
        # max_x must be greater than min_x
        with pytest.raises(
            ValueError, match="max_x must be greater than min_x"
        ):
            BoundingBox(min_x=10.0, min_y=0.0, max_x=5.0, max_y=10.0)

        # max_y must be greater than min_y
        with pytest.raises(
            ValueError, match="max_y must be greater than min_y"
        ):
            BoundingBox(min_x=0.0, min_y=10.0, max_x=10.0, max_y=5.0)

    def test_area_creation(self):
        """Test Area model creation."""
        bbox = BoundingBox(min_x=0.0, min_y=0.0, max_x=100.0, max_y=100.0)
        area = Area(
            name="Battlefield Alpha",
            bounds=bbox,
            area_type="battlefield",
            properties={"terrain": "urban", "cover": "high"},
        )

        assert area.name == "Battlefield Alpha"
        assert area.bounds == bbox
        assert area.area_type == "battlefield"
        assert area.properties["terrain"] == "urban"


class TestResourceTypes:
    """Test resource and equipment types."""

    def test_resource_value_valid(self):
        """Test ResourceValue with valid data."""
        resource = ResourceValue(
            current=75.0, maximum=100.0, regeneration_rate=5.0
        )

        assert resource.current == 75.0
        assert resource.maximum == 100.0
        assert resource.regeneration_rate == 5.0
        assert resource.percentage == 75.0

    def test_resource_value_validation(self):
        """Test ResourceValue validation rules."""
        # Current cannot be negative
        with pytest.raises(ValueError):
            ResourceValue(current=-10.0, maximum=100.0)

        # Maximum must be positive
        with pytest.raises(ValueError):
            ResourceValue(current=50.0, maximum=0.0)

        # Current cannot exceed maximum
        with pytest.raises(ValueError):
            ResourceValue(current=150.0, maximum=100.0)

    def test_resource_value_percentage_calculation(self):
        """Test percentage property calculation."""
        resource = ResourceValue(current=25.0, maximum=100.0)
        assert resource.percentage == 25.0

        resource = ResourceValue(current=0.0, maximum=100.0)
        assert resource.percentage == 0.0

        resource = ResourceValue(current=100.0, maximum=100.0)
        assert resource.percentage == 100.0

    def test_equipment_creation(self):
        """Test Equipment model creation."""
        equipment = Equipment(
            name="Lasgun",
            equipment_type="weapon",
            condition=0.85,
            properties={"damage": 15, "range": 150},
            quantity=1,
        )

        assert equipment.name == "Lasgun"
        assert equipment.equipment_type == "weapon"
        assert equipment.condition == 0.85
        assert equipment.properties["damage"] == 15
        assert equipment.quantity == 1

    def test_equipment_defaults(self):
        """Test Equipment model with default values."""
        equipment = Equipment(name="Basic Tool", equipment_type="utility")

        assert equipment.condition == 1.0
        assert equipment.properties == {}
        assert equipment.quantity == 1

    def test_equipment_validation(self):
        """Test Equipment validation rules."""
        # Condition must be between 0.0 and 1.0
        with pytest.raises(ValueError):
            Equipment(name="Broken", equipment_type="weapon", condition=-0.1)

        with pytest.raises(ValueError):
            Equipment(name="Perfect", equipment_type="weapon", condition=1.1)

        # Quantity cannot be negative
        with pytest.raises(ValueError):
            Equipment(name="Missing", equipment_type="weapon", quantity=-1)


class TestCharacterTypes:
    """Test character-related model types."""

    def test_character_stats_valid(self):
        """Test CharacterStats with valid values."""
        stats = CharacterStats(
            strength=7,
            dexterity=6,
            intelligence=5,
            willpower=9,
            perception=6,
            charisma=4,
        )

        assert stats.strength == 7
        assert stats.dexterity == 6
        assert stats.intelligence == 5
        assert stats.willpower == 9
        assert stats.perception == 6
        assert stats.charisma == 4

    def test_character_stats_validation(self):
        """Test CharacterStats validation rules."""
        # All stats must be between 1 and 10
        with pytest.raises(ValueError):
            CharacterStats(
                strength=0,  # Too low
                dexterity=5,
                intelligence=5,
                willpower=5,
                perception=5,
                charisma=5,
            )

        with pytest.raises(ValueError):
            CharacterStats(
                strength=5,
                dexterity=11,  # Too high
                intelligence=5,
                willpower=5,
                perception=5,
                charisma=5,
            )

    def test_character_resources_creation(self):
        """Test CharacterResources model creation."""
        health = ResourceValue(current=100.0, maximum=100.0)
        stamina = ResourceValue(
            current=80.0, maximum=100.0, regeneration_rate=10.0
        )
        morale = ResourceValue(current=90.0, maximum=100.0)

        resources = CharacterResources(
            health=health,
            stamina=stamina,
            morale=morale,
            ammo={"las_cell": 20, "frag_grenade": 3},
            special_resources={
                "faith": ResourceValue(current=50.0, maximum=50.0)
            },
        )

        assert resources.health.current == 100.0
        assert resources.stamina.current == 80.0
        assert resources.morale.current == 90.0
        assert resources.ammo["las_cell"] == 20
        assert resources.special_resources["faith"].current == 50.0

    def test_character_state_defaults(self):
        """Test CharacterState with default values."""
        state = CharacterState()

        assert state.conscious is True
        assert state.mobile is True
        assert state.combat_ready is True
        assert state.status_effects == []
        assert state.injuries == []
        assert state.fatigue_level == 0.0

    def test_character_state_validation(self):
        """Test CharacterState validation rules."""
        # Fatigue level must be between 0.0 and 1.0
        with pytest.raises(ValueError):
            CharacterState(fatigue_level=-0.1)

        with pytest.raises(ValueError):
            CharacterState(fatigue_level=1.1)

    def test_character_data_full_creation(self):
        """Test complete CharacterData model creation."""
        position = Position(x=100.0, y=150.0)
        stats = CharacterStats(
            strength=7,
            dexterity=6,
            intelligence=5,
            willpower=9,
            perception=6,
            charisma=4,
        )
        health = ResourceValue(current=100.0, maximum=100.0)
        stamina = ResourceValue(current=100.0, maximum=100.0)
        morale = ResourceValue(current=90.0, maximum=100.0)
        resources = CharacterResources(
            health=health, stamina=stamina, morale=morale
        )

        character = CharacterData(
            character_id="char_001",
            name="Brother Marcus",
            faction="Death Korps of Krieg",
            position=position,
            stats=stats,
            resources=resources,
            ai_personality={"aggression": 0.8, "loyalty": 1.0},
        )

        assert character.character_id == "char_001"
        assert character.name == "Brother Marcus"
        assert character.faction == "Death Korps of Krieg"
        assert character.position.x == 100.0
        assert character.stats.strength == 7
        assert character.resources.health.current == 100.0
        assert character.ai_personality["loyalty"] == 1.0


class TestActionTypes:
    """Test action-related model types."""

    def test_action_target_creation(self):
        """Test ActionTarget model creation."""
        position = Position(x=200.0, y=300.0)
        target = ActionTarget(
            entity_id="enemy_001",
            entity_type=EntityType.CHARACTER,
            position=position,
            properties={"visible": True},
        )

        assert target.entity_id == "enemy_001"
        assert target.entity_type == EntityType.CHARACTER
        assert target.position.x == 200.0
        assert target.properties["visible"] is True

    def test_action_parameters_defaults(self):
        """Test ActionParameters with default values."""
        params = ActionParameters()

        assert params.intensity == ActionIntensity.NORMAL
        assert params.duration == 1.0
        assert params.range == 1.0
        assert params.modifiers == {}
        assert params.resources_consumed == {}
        assert params.conditions == []

    def test_action_parameters_validation(self):
        """Test ActionParameters validation rules."""
        # Duration must be non-negative
        with pytest.raises(ValueError):
            ActionParameters(duration=-0.1)

        # Range must be non-negative
        with pytest.raises(ValueError):
            ActionParameters(range=-0.1)

        # Duration must be non-negative
        with pytest.raises(ValueError):
            ActionParameters(duration=-1.0)

    def test_proposed_action_creation(self):
        """Test ProposedAction model creation."""
        target = ActionTarget(
            entity_id="enemy_001", entity_type=EntityType.CHARACTER
        )
        params = ActionParameters(intensity=0.8)

        action = ProposedAction(
            character_id="char_001",
            action_type=ActionType.ATTACK,
            target=target,
            parameters=params,
            reasoning="Enemy is vulnerable and within range",
            confidence=0.9,
            alternatives=["defend", "move"],
        )

        assert action.character_id == "char_001"
        assert action.action_type == ActionType.ATTACK
        assert action.target.entity_id == "enemy_001"
        assert action.parameters.intensity == 0.8
        assert action.reasoning == "Enemy is vulnerable and within range"
        assert action.confidence == 0.9
        assert "defend" in action.alternatives
        assert len(action.action_id) > 0  # Should auto-generate UUID

    def test_proposed_action_confidence_validation(self):
        """Test ProposedAction confidence validation."""
        # Confidence must be between 0.0 and 1.0
        with pytest.raises(ValueError):
            ProposedAction(
                character_id="char_001",
                action_type=ActionType.WAIT,
                reasoning="Test",
                confidence=-0.1,
            )

        with pytest.raises(ValueError):
            ProposedAction(
                character_id="char_001",
                action_type=ActionType.WAIT,
                reasoning="Test",
                confidence=1.1,
            )

    def test_validated_action_creation(self):
        """Test ValidatedAction model creation."""
        target = ActionTarget(
            entity_id="enemy_001", entity_type=EntityType.CHARACTER
        )
        params = ActionParameters(intensity=0.8)

        validated_action = ValidatedAction(
            action_id="action_001",
            character_id="char_001",
            action_type=ActionType.ATTACK,
            target=target,
            parameters=params,
            validation_result=ValidationResult.VALID,
            validation_details={"checks_passed": 5},
            repairs_applied=["range_adjustment"],
            estimated_effects={"damage": 15, "chance": 0.85},
        )

        assert validated_action.action_id == "action_001"
        assert validated_action.validation_result == ValidationResult.VALID
        assert validated_action.validation_details["checks_passed"] == 5
        assert "range_adjustment" in validated_action.repairs_applied
        assert validated_action.estimated_effects["damage"] == 15


class TestIronLawsTypes:
    """Test Iron Laws validation model types."""

    def test_iron_laws_violation_creation(self):
        """Test IronLawsViolation model creation."""
        violation = IronLawsViolation(
            law_code="E001",
            law_name="Resource Conservation",
            severity="error",
            description="Action would result in negative health",
            affected_entities=["char_001"],
            suggested_repair="Reduce damage intensity",
        )

        assert violation.law_code == "E001"
        assert violation.law_name == "Resource Conservation"
        assert violation.severity == "error"
        assert (
            violation.description == "Action would result in negative health"
        )
        assert "char_001" in violation.affected_entities
        assert violation.suggested_repair == "Reduce damage intensity"

    def test_iron_laws_report_creation(self):
        """Test IronLawsReport model creation."""
        violation = IronLawsViolation(
            law_code="E002",
            law_name="Information Limit",
            severity="warning",
            description="Target not visible",
            affected_entities=["enemy_001"],
        )

        report = IronLawsReport(
            action_id="action_001",
            overall_result=ValidationResult.REQUIRES_REPAIR,
            violations=[violation],
            checks_performed=["E001", "E002", "E003", "E004", "E005"],
            repair_attempts=["visibility_check"],
        )

        assert report.action_id == "action_001"
        assert report.overall_result == ValidationResult.REQUIRES_REPAIR
        assert len(report.violations) == 1
        assert "E001" in report.checks_performed
        assert "visibility_check" in report.repair_attempts
        assert isinstance(report.timestamp, datetime)

    def test_iron_laws_report_properties(self):
        """Test IronLawsReport computed properties."""
        critical_violation = IronLawsViolation(
            law_code="E003",
            law_name="State Consistency",
            severity="critical",
            description="Catastrophic state violation",
        )

        warning_violation = IronLawsViolation(
            law_code="E004",
            law_name="Rule Adherence",
            severity="warning",
            description="Minor rule issue",
        )

        report = IronLawsReport(
            action_id="action_002",
            overall_result=ValidationResult.INVALID,
            violations=[critical_violation, warning_violation],
            checks_performed=["E003", "E004"],
        )

        # Test has_critical_violations property
        assert report.has_critical_violations is True

        # Test violation_count_by_severity property
        counts = report.violation_count_by_severity
        assert counts["critical"] == 1
        assert counts["warning"] == 1
        assert counts["error"] == 0


class TestWorldStateTypes:
    """Test world state and environment types."""

    def test_world_entity_creation(self):
        """Test WorldEntity model creation."""
        position = Position(x=150.0, y=250.0)
        entity = WorldEntity(
            entity_id="obj_001",
            entity_type=EntityType.OBJECT,
            name="Supply Cache",
            position=position,
            properties={"contents": "medical_supplies", "locked": False},
            visibility=0.8,
        )

        assert entity.entity_id == "obj_001"
        assert entity.entity_type == EntityType.OBJECT
        assert entity.name == "Supply Cache"
        assert entity.position.x == 150.0
        assert entity.properties["locked"] is False
        assert entity.visibility == 0.8
        assert isinstance(entity.last_updated, datetime)

    def test_environmental_condition_creation(self):
        """Test EnvironmentalCondition model creation."""
        bbox = BoundingBox(min_x=0.0, min_y=0.0, max_x=100.0, max_y=100.0)
        area = Area(name="Storm Zone", bounds=bbox, area_type="weather")

        condition = EnvironmentalCondition(
            condition_type="storm",
            severity=0.7,
            affected_area=area,
            duration_remaining=300.0,
            effects={"visibility": -0.5, "movement": -0.3},
        )

        assert condition.condition_type == "storm"
        assert condition.severity == 0.7
        assert condition.affected_area.name == "Storm Zone"
        assert condition.duration_remaining == 300.0
        assert condition.effects["visibility"] == -0.5

    def test_world_state_creation(self):
        """Test WorldState model creation."""
        entity = WorldEntity(
            entity_id="char_001",
            entity_type=EntityType.CHARACTER,
            name="Brother Marcus",
        )

        world_state = WorldState(
            turn_number=5,
            entities={"char_001": entity},
            global_properties={"time_of_day": "dawn", "weather": "clear"},
        )

        assert world_state.turn_number == 5
        assert "char_001" in world_state.entities
        assert world_state.entities["char_001"].name == "Brother Marcus"
        assert world_state.global_properties["weather"] == "clear"
        assert isinstance(world_state.timestamp, datetime)

    def test_world_state_utility_methods(self):
        """Test WorldState utility methods."""
        char_entity = WorldEntity(
            entity_id="char_001",
            entity_type=EntityType.CHARACTER,
            name="Marcus",
        )

        obj_entity = WorldEntity(
            entity_id="obj_001", entity_type=EntityType.OBJECT, name="Cache"
        )

        world_state = WorldState(
            turn_number=1,
            entities={"char_001": char_entity, "obj_001": obj_entity},
        )

        # Test get_entities_by_type
        characters = world_state.get_entities_by_type(EntityType.CHARACTER)
        assert len(characters) == 1
        assert characters[0].entity_id == "char_001"

        objects = world_state.get_entities_by_type(EntityType.OBJECT)
        assert len(objects) == 1
        assert objects[0].entity_id == "obj_001"


class TestFogOfWarTypes:
    """Test Fog of War and information filtering types."""

    def test_information_source_creation(self):
        """Test InformationSource model creation."""
        source = InformationSource(
            source_id="scout_001",
            source_type="reconnaissance",
            reliability=0.9,
            access_channels=[FogOfWarChannel.VISUAL, FogOfWarChannel.RADIO],
            range_modifiers={"visual": 1.2, "radio": 0.8},
        )

        assert source.source_id == "scout_001"
        assert source.source_type == "reconnaissance"
        assert source.reliability == 0.9
        assert FogOfWarChannel.VISUAL in source.access_channels
        assert source.range_modifiers["visual"] == 1.2

    def test_information_fragment_creation(self):
        """Test InformationFragment model creation."""
        source = InformationSource(
            source_id="observer_001",
            source_type="visual",
            reliability=0.85,
            access_channels=[FogOfWarChannel.VISUAL],
        )

        fragment = InformationFragment(
            entity_id="enemy_001",
            information_type="position",
            content={"x": 200.0, "y": 150.0},
            source=source,
            channel=FogOfWarChannel.VISUAL,
            accuracy=0.9,
            freshness=1.0,
        )

        assert fragment.entity_id == "enemy_001"
        assert fragment.information_type == "position"
        assert fragment.content["x"] == 200.0
        assert fragment.source.source_id == "observer_001"
        assert fragment.channel == FogOfWarChannel.VISUAL
        assert fragment.accuracy == 0.9
        assert len(fragment.fragment_id) > 0  # Auto-generated UUID

    def test_fog_of_war_filter_creation(self):
        """Test FogOfWarFilter model creation."""
        fog_filter = FogOfWarFilter(
            observer_id="char_001",
            visual_range=15.0,
            radio_range=75.0,
            intel_range=120.0,
            sensor_range=30.0,
            rumor_reliability=0.4,
            channel_preferences={
                FogOfWarChannel.VISUAL: 1.0,
                FogOfWarChannel.RADIO: 0.8,
                FogOfWarChannel.INTEL: 0.6,
            },
        )

        assert fog_filter.observer_id == "char_001"
        assert fog_filter.visual_range == 15.0
        assert fog_filter.radio_range == 75.0
        assert fog_filter.intel_range == 120.0
        assert fog_filter.rumor_reliability == 0.4
        assert fog_filter.channel_preferences[FogOfWarChannel.VISUAL] == 1.0

    def test_filtered_world_view_creation(self):
        """Test FilteredWorldView model creation."""
        entity = WorldEntity(
            entity_id="visible_001",
            entity_type=EntityType.CHARACTER,
            name="Visible Enemy",
        )

        source = InformationSource(
            source_id="eye_001",
            source_type="visual",
            reliability=1.0,
            access_channels=[FogOfWarChannel.VISUAL],
        )

        info = InformationFragment(
            entity_id="visible_001",
            information_type="status",
            content={"health": "wounded"},
            source=source,
            channel=FogOfWarChannel.VISUAL,
        )

        fog_filter = FogOfWarFilter(observer_id="char_001")

        filtered_view = FilteredWorldView(
            observer_id="char_001",
            base_world_state="world_state_001",
            visible_entities={"visible_001": entity},
            known_information=[info],
            uncertainty_markers=["fog_area_alpha"],
            filter_config=fog_filter,
        )

        assert filtered_view.observer_id == "char_001"
        assert filtered_view.base_world_state == "world_state_001"
        assert "visible_001" in filtered_view.visible_entities
        assert len(filtered_view.known_information) == 1
        assert "fog_area_alpha" in filtered_view.uncertainty_markers


class TestTurnBriefTypes:
    """Test Turn Brief and RAG injection types."""

    def test_knowledge_fragment_creation(self):
        """Test KnowledgeFragment model creation."""
        fragment = KnowledgeFragment(
            content="Imperial Guard tactics favor massed firepower and coordinated assaults",
            source="tactical_manual.pdf",
            relevance_score=0.85,
            knowledge_type="tactical_doctrine",
            tags=["imperial_guard", "tactics", "doctrine"],
        )

        assert "Imperial Guard tactics" in fragment.content
        assert fragment.source == "tactical_manual.pdf"
        assert fragment.relevance_score == 0.85
        assert fragment.knowledge_type == "tactical_doctrine"
        assert "tactics" in fragment.tags
        assert len(fragment.fragment_id) > 0  # Auto-generated UUID
        assert isinstance(fragment.last_accessed, datetime)

    def test_contextual_prompt_creation(self):
        """Test ContextualPrompt model creation."""
        knowledge = KnowledgeFragment(
            content="Cover provides defensive bonuses",
            source="rules.md",
            knowledge_type="rule",
        )

        prompt = ContextualPrompt(
            base_prompt="You are a tactical AI assistant",
            character_context="Playing as Death Korps Grenadier",
            world_context="Urban battlefield with heavy cover",
            injected_knowledge=[knowledge],
            fog_of_war_mask="Limited visibility due to smoke",
            prompt_tokens=1250,
        )

        assert prompt.base_prompt == "You are a tactical AI assistant"
        assert "Death Korps" in prompt.character_context
        assert "Urban battlefield" in prompt.world_context
        assert len(prompt.injected_knowledge) == 1
        assert "smoke" in prompt.fog_of_war_mask
        assert prompt.prompt_tokens == 1250

    def test_contextual_prompt_compilation(self):
        """Test ContextualPrompt compile_prompt method."""
        knowledge = KnowledgeFragment(
            content="Test knowledge piece",
            source="test.md",
            knowledge_type="rule",
        )

        prompt = ContextualPrompt(
            base_prompt="Base prompt text",
            character_context="Character info",
            world_context="World info",
            injected_knowledge=[knowledge],
            fog_of_war_mask="Information constraints",
        )

        compiled = prompt.compile_prompt()

        assert "Base prompt text" in compiled
        assert "Character info" in compiled
        assert "World info" in compiled
        assert "Test knowledge piece" in compiled
        assert "Information constraints" in compiled
        assert "## Character Context" in compiled
        assert "## World State" in compiled
        assert "## Relevant Knowledge" in compiled
        assert "## Information Constraints" in compiled

    def test_turn_brief_creation(self):
        """Test TurnBrief model creation."""
        Position(x=100.0, y=100.0)
        filter_config = FogOfWarFilter(observer_id="char_001")
        filtered_view = FilteredWorldView(
            observer_id="char_001",
            base_world_state="world_001",
            filter_config=filter_config,
        )

        prompt = ContextualPrompt(
            base_prompt="Make tactical decision",
            character_context="Imperial Guard soldier",
        )

        brief = TurnBrief(
            character_id="char_001",
            turn_number=3,
            filtered_world_view=filtered_view,
            available_actions=[
                ActionType.MOVE,
                ActionType.ATTACK,
                ActionType.DEFEND,
            ],
            contextual_prompt=prompt,
            tactical_situation="Enemy forces advancing from east",
            objectives=["Hold position", "Maintain communication"],
            constraints=["Limited ammunition", "Maintain radio discipline"],
            token_budget=5000,
        )

        assert brief.character_id == "char_001"
        assert brief.turn_number == 3
        assert brief.filtered_world_view.observer_id == "char_001"
        assert ActionType.ATTACK in brief.available_actions
        assert "advancing from east" in brief.tactical_situation
        assert "Hold position" in brief.objectives
        assert "Limited ammunition" in brief.constraints
        assert brief.token_budget == 5000
        assert isinstance(brief.timestamp, datetime)


class TestSimulationTypes:
    """Test simulation control and state types."""

    def test_simulation_config_defaults(self):
        """Test SimulationConfig with default values."""
        config = SimulationConfig()

        assert config.max_turns == 10
        assert config.turn_timeout == 30.0
        assert config.max_agents == 20
        assert config.iron_laws_enabled is True
        assert config.fog_of_war_enabled is True
        assert config.rag_injection_enabled is True
        assert config.performance_mode == "balanced"
        assert config.logging_level == "info"

    def test_simulation_config_validation(self):
        """Test SimulationConfig validation rules."""
        # max_turns must be between 1 and 100
        with pytest.raises(ValueError):
            SimulationConfig(max_turns=0)

        with pytest.raises(ValueError):
            SimulationConfig(max_turns=101)

        # turn_timeout must be positive
        with pytest.raises(ValueError):
            SimulationConfig(turn_timeout=0.0)

        # max_agents must be between 1 and 100
        with pytest.raises(ValueError):
            SimulationConfig(max_agents=0)

    def test_simulation_state_creation(self):
        """Test SimulationState model creation."""
        world_state = WorldState(turn_number=0)
        config = SimulationConfig(max_turns=5)

        sim_state = SimulationState(
            simulation_id="sim_001",
            current_turn=3,
            phase=SimulationPhase.EXECUTION,
            active_characters=["char_001", "char_002"],
            world_state=world_state,
            config=config,
            metrics={"actions_processed": 15, "average_turn_time": 2.5},
        )

        assert sim_state.simulation_id == "sim_001"
        assert sim_state.current_turn == 3
        assert sim_state.phase == SimulationPhase.EXECUTION
        assert "char_001" in sim_state.active_characters
        assert sim_state.world_state.turn_number == 0
        assert sim_state.config.max_turns == 5
        assert sim_state.metrics["actions_processed"] == 15
        assert isinstance(sim_state.start_time, datetime)

    def test_turn_result_creation(self):
        """Test TurnResult model creation."""
        target = ActionTarget(
            entity_id="enemy_001", entity_type=EntityType.CHARACTER
        )
        params = ActionParameters()
        validated_action = ValidatedAction(
            action_id="action_001",
            character_id="char_001",
            action_type=ActionType.ATTACK,
            target=target,
            parameters=params,
            validation_result=ValidationResult.VALID,
        )

        position = Position(x=110.0, y=120.0)
        stats = CharacterStats(
            strength=7,
            dexterity=6,
            intelligence=5,
            willpower=9,
            perception=6,
            charisma=4,
        )
        health = ResourceValue(current=85.0, maximum=100.0)
        stamina = ResourceValue(current=90.0, maximum=100.0)
        morale = ResourceValue(current=95.0, maximum=100.0)
        resources = CharacterResources(
            health=health, stamina=stamina, morale=morale
        )

        character = CharacterData(
            character_id="char_001",
            name="Updated Marcus",
            faction="Death Korps",
            position=position,
            stats=stats,
            resources=resources,
        )

        turn_result = TurnResult(
            turn_number=4,
            executed_actions=[validated_action],
            world_state_changes={"entities_moved": 2, "objects_destroyed": 1},
            character_updates={"char_001": character},
            events_generated=[
                "explosion_at_200_150",
                "radio_chatter_intercepted",
            ],
            performance_metrics={
                "execution_time_ms": 1250.0,
                "memory_mb": 45.2,
            },
            errors=["minor_path_finding_error"],
            warnings=["low_ammunition_warning"],
            duration_seconds=1.25,
        )

        assert turn_result.turn_number == 4
        assert len(turn_result.executed_actions) == 1
        assert turn_result.world_state_changes["entities_moved"] == 2
        assert "char_001" in turn_result.character_updates
        assert "explosion_at_200_150" in turn_result.events_generated
        assert turn_result.performance_metrics["execution_time_ms"] == 1250.0
        assert "minor_path_finding_error" in turn_result.errors
        assert turn_result.duration_seconds == 1.25


class TestAPITypes:
    """Test API response and status types."""

    def test_api_response_success(self):
        """Test APIResponse for successful operation."""
        response = APIResponse(
            success=True,
            message="Operation completed successfully",
            data={"result": "character_created", "id": "char_001"},
            warnings=["minor_validation_warning"],
        )

        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert response.data["result"] == "character_created"
        assert response.errors == []  # Default empty list
        assert "minor_validation_warning" in response.warnings
        assert isinstance(response.timestamp, datetime)

    def test_api_response_error(self):
        """Test APIResponse for failed operation."""
        response = APIResponse(
            success=False,
            message="Operation failed",
            errors=["validation_error", "database_error"],
            request_id="req_12345",
        )

        assert response.success is False
        assert response.message == "Operation failed"
        assert response.data is None  # Default None
        assert "validation_error" in response.errors
        assert response.warnings == []  # Default empty list
        assert response.request_id == "req_12345"

    def test_system_status_creation(self):
        """Test SystemStatus model creation."""
        status = SystemStatus(
            status="healthy",
            uptime_seconds=3600.0,
            active_simulations=2,
            memory_usage_mb=256.5,
            cpu_usage_percent=35.2,
            components={
                "api_server": "healthy",
                "database": "healthy",
                "cache": "degraded",
            },
        )

        assert status.system_name == "Novel Engine"  # Default value
        assert status.version == "1.0.0"  # Default value
        assert status.status == "healthy"
        assert status.uptime_seconds == 3600.0
        assert status.active_simulations == 2
        assert status.memory_usage_mb == 256.5
        assert status.cpu_usage_percent == 35.2
        assert status.components["cache"] == "degraded"

    def test_system_status_validation(self):
        """Test SystemStatus validation rules."""
        # uptime_seconds must be non-negative
        with pytest.raises(ValueError):
            SystemStatus(status="healthy", uptime_seconds=-1.0)

        # active_simulations must be non-negative
        with pytest.raises(ValueError):
            SystemStatus(
                status="healthy", uptime_seconds=100.0, active_simulations=-1
            )

        # cpu_usage_percent must be between 0 and 100
        with pytest.raises(ValueError):
            SystemStatus(
                status="healthy", uptime_seconds=100.0, cpu_usage_percent=101.0
            )


class TestPerformanceTypes:
    """Test performance and caching types."""

    def test_cache_entry_creation(self):
        """Test CacheEntry model creation."""
        cache_entry = CacheEntry(
            key="character_data_char_001",
            value={"name": "Marcus", "health": 100},
            access_count=5,
            ttl_seconds=3600.0,
            tags=["character", "simulation"],
        )

        assert cache_entry.key == "character_data_char_001"
        assert cache_entry.value["name"] == "Marcus"
        assert cache_entry.access_count == 5
        assert cache_entry.ttl_seconds == 3600.0
        assert "character" in cache_entry.tags
        assert isinstance(cache_entry.created_at, datetime)
        assert isinstance(cache_entry.last_accessed, datetime)

    def test_cache_entry_expiration(self):
        """Test CacheEntry expiration logic."""
        # Entry with no TTL should never expire
        entry_no_ttl = CacheEntry(key="persistent", value="data")
        assert entry_no_ttl.is_expired is False

        # Entry with TTL - mock would be needed for proper time-based testing
        CacheEntry(key="temp", value="data", ttl_seconds=0.001)
        # Note: In real test, would need to wait or mock datetime

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics model creation."""
        metrics = PerformanceMetrics(
            operation_name="character_decision_making",
            duration_ms=125.5,
            memory_delta_mb=2.3,
            tokens_consumed=450,
            cache_hits=3,
            cache_misses=1,
            error_count=0,
        )

        assert metrics.operation_name == "character_decision_making"
        assert metrics.duration_ms == 125.5
        assert metrics.memory_delta_mb == 2.3
        assert metrics.tokens_consumed == 450
        assert metrics.cache_hits == 3
        assert metrics.cache_misses == 1
        assert metrics.error_count == 0
        assert isinstance(metrics.timestamp, datetime)

    def test_performance_metrics_validation(self):
        """Test PerformanceMetrics validation rules."""
        # duration_ms must be non-negative
        with pytest.raises(ValueError):
            PerformanceMetrics(operation_name="test", duration_ms=-1.0)

        # tokens_consumed must be non-negative
        with pytest.raises(ValueError):
            PerformanceMetrics(
                operation_name="test", duration_ms=100.0, tokens_consumed=-10
            )


class TestConsistencyTypes:
    """Test state hashing and consistency check types."""

    def test_state_hash_creation(self):
        """Test StateHash model creation."""
        state_hash = StateHash(
            entity_id="char_001",
            hash_type="character",
            hash_value="a1b2c3d4e5f67890abcdef1234567890",
            fields_included=["position", "stats", "resources"],
            salt="random_salt_123",
        )

        assert state_hash.entity_id == "char_001"
        assert state_hash.hash_type == "character"
        assert state_hash.hash_value == "a1b2c3d4e5f67890abcdef1234567890"
        assert "position" in state_hash.fields_included
        assert state_hash.salt == "random_salt_123"
        assert isinstance(state_hash.timestamp, datetime)

    def test_state_hash_validation(self):
        """Test StateHash validation rules."""
        # Valid hexadecimal hash values
        StateHash(
            entity_id="test",
            hash_type="test",
            hash_value="abcdef1234567890abcdef1234567890",
            fields_included=["test"],
        )

        # Invalid hash value - too short
        with pytest.raises(ValueError):
            StateHash(
                entity_id="test",
                hash_type="test",
                hash_value="short",
                fields_included=["test"],
            )

        # Invalid hash value - non-hex characters
        with pytest.raises(ValueError):
            StateHash(
                entity_id="test",
                hash_type="test",
                hash_value="xyz123456789abcdef123456789abcdef",
                fields_included=["test"],
            )

    def test_consistency_check_creation(self):
        """Test ConsistencyCheck model creation."""
        consistency_check = ConsistencyCheck(
            entity_ids=["char_001", "world_state_001"],
            check_type="character_world_sync",
            is_consistent=False,
            inconsistencies=[
                "Character position not updated in world state",
                "Health value mismatch between character and world",
            ],
            confidence=0.95,
            remediation_suggestions=[
                "Update world state with character position",
                "Synchronize health values",
            ],
        )

        assert "char_001" in consistency_check.entity_ids
        assert consistency_check.check_type == "character_world_sync"
        assert consistency_check.is_consistent is False
        assert len(consistency_check.inconsistencies) == 2
        assert consistency_check.confidence == 0.95
        assert (
            "Update world state"
            in consistency_check.remediation_suggestions[0]
        )
        assert len(consistency_check.check_id) > 0  # Auto-generated UUID
        assert isinstance(consistency_check.timestamp, datetime)


class TestModelRegistry:
    """Test model registry functionality."""

    def test_model_registry_contains_expected_models(self):
        """Test that MODEL_REGISTRY contains expected model types."""
        expected_models = [
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

        for model_name in expected_models:
            assert model_name in MODEL_REGISTRY
            assert MODEL_REGISTRY[model_name] is not None

    def test_model_registry_types_are_pydantic_models(self):
        """Test that MODEL_REGISTRY contains actual Pydantic model classes."""
        from pydantic import BaseModel

        for model_name, model_class in MODEL_REGISTRY.items():
            # Verify each registry entry is a Pydantic model class
            assert issubclass(model_class, BaseModel)

    def test_model_creation_from_registry(self):
        """Test creating model instances from registry."""
        # Test CharacterData creation
        CharacterDataModel = MODEL_REGISTRY["character_data"]

        position = Position(x=0.0, y=0.0)
        stats = CharacterStats(
            strength=5,
            dexterity=5,
            intelligence=5,
            willpower=5,
            perception=5,
            charisma=5,
        )
        health = ResourceValue(current=100.0, maximum=100.0)
        stamina = ResourceValue(current=100.0, maximum=100.0)
        morale = ResourceValue(current=100.0, maximum=100.0)
        resources = CharacterResources(
            health=health, stamina=stamina, morale=morale
        )

        character = CharacterDataModel(
            character_id="test_char",
            name="Test Character",
            faction="Test Faction",
            position=position,
            stats=stats,
            resources=resources,
        )

        assert character.character_id == "test_char"
        assert character.name == "Test Character"
        assert isinstance(character, CharacterDataModel)


class TestJSONSerialization:
    """Test JSON serialization and deserialization of models."""

    def test_character_data_json_roundtrip(self):
        """Test CharacterData JSON serialization roundtrip."""
        position = Position(x=100.0, y=150.0, facing=270.0)
        stats = CharacterStats(
            strength=7,
            dexterity=6,
            intelligence=5,
            willpower=9,
            perception=6,
            charisma=4,
        )
        health = ResourceValue(current=85.0, maximum=100.0)
        stamina = ResourceValue(current=95.0, maximum=100.0)
        morale = ResourceValue(current=90.0, maximum=100.0)
        resources = CharacterResources(
            health=health, stamina=stamina, morale=morale
        )

        original = CharacterData(
            character_id="char_001",
            name="Brother Marcus",
            faction="Death Korps of Krieg",
            position=position,
            stats=stats,
            resources=resources,
        )

        # Serialize to JSON
        json_data = original.model_dump()
        json_string = json.dumps(
            json_data, default=str
        )  # Handle datetime serialization

        # Deserialize from JSON
        parsed_data = json.loads(json_string)
        reconstructed = CharacterData(**parsed_data)

        # Verify round-trip integrity
        assert reconstructed.character_id == original.character_id
        assert reconstructed.name == original.name
        assert reconstructed.faction == original.faction
        assert reconstructed.position.x == original.position.x
        assert reconstructed.stats.strength == original.stats.strength
        assert (
            reconstructed.resources.health.current
            == original.resources.health.current
        )

    def test_world_state_json_serialization(self):
        """Test WorldState JSON serialization."""
        entity = WorldEntity(
            entity_id="obj_001",
            entity_type=EntityType.OBJECT,
            name="Supply Cache",
        )

        world_state = WorldState(
            turn_number=5,
            entities={"obj_001": entity},
            global_properties={"weather": "storm", "visibility": 0.3},
        )

        # Serialize to JSON
        json_data = world_state.model_dump()

        # Verify serialization contains expected data
        assert json_data["turn_number"] == 5
        assert "obj_001" in json_data["entities"]
        assert json_data["entities"]["obj_001"]["name"] == "Supply Cache"
        assert json_data["global_properties"]["weather"] == "storm"

    def test_iron_laws_report_json_serialization(self):
        """Test IronLawsReport JSON serialization with nested models."""
        violation = IronLawsViolation(
            law_code="E001",
            law_name="Resource Conservation",
            severity="error",
            description="Negative resource result",
        )

        report = IronLawsReport(
            action_id="action_001",
            overall_result=ValidationResult.INVALID,
            violations=[violation],
            checks_performed=["E001", "E002", "E003", "E004", "E005"],
        )

        # Serialize to JSON
        json_data = report.model_dump()

        # Verify nested model serialization
        assert json_data["action_id"] == "action_001"
        assert json_data["overall_result"] == "invalid"
        assert len(json_data["violations"]) == 1
        assert json_data["violations"][0]["law_code"] == "E001"
        assert json_data["violations"][0]["severity"] == "error"
        assert "E001" in json_data["checks_performed"]


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
