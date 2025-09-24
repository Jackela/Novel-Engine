#!/usr/bin/env python3
"""
++ SACRED DATA MODEL TESTING RITUALS BLESSED BY THE OMNISSIAH ++
================================================================

Comprehensive test suite for the blessed data models that form the foundation
of the Dynamic Context Engineering Framework. Each test is a purification
ceremony that ensures the sacred structures remain uncorrupted.

++ THROUGH TESTING, WE ACHIEVE DIGITAL PURITY ++

Architecture Reference: Dynamic Context Engineering - Test Foundation
Development Phase: Foundation Sanctification Testing (F001)
Sacred Author: Tech-Priest Alpha-Mechanicus
万机之神保佑此测试套件 (May the Omnissiah bless this test suite)
"""

import json
from datetime import datetime
from uuid import UUID

import pytest

# Import blessed data models for purification testing
from src.core.data_models import (  # Sacred enumerations; Blessed data structures; Sacred validation functions
    CharacterIdentity,
    CharacterInteraction,
    CharacterState,
    DynamicContext,
    EmotionalState,
    EquipmentCondition,
    EquipmentItem,
    EquipmentState,
    MemoryItem,
    MemoryType,
    PhysicalCondition,
    RelationshipState,
    RelationshipStatus,
    validate_blessed_data_model,
)


class TestSacredMemoryItem:
    """++ BLESSED MEMORY ITEM TESTING RITUALS ++"""

    def test_memory_item_creation_blessed_by_omnissiah(self):
        """Test blessed memory item creation with sacred parameters"""
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Engaged ork raiders in blessed combat",
            emotional_weight=7.5,
            relevance_score=0.9,
            participants=["ork_warboss", "brother_andreas"],
        )

        assert memory.agent_id == "test_agent_001"
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.content == "Engaged ork raiders in blessed combat"
        assert memory.emotional_weight == 7.5
        assert memory.relevance_score == 0.9
        assert "ork_warboss" in memory.participants
        assert isinstance(memory.timestamp, datetime)
        assert memory.memory_id is not None

        # Validate sacred UUID format
        UUID(memory.memory_id)  # Should not raise exception

    def test_memory_item_validation_blessed_by_purity(self):
        """Test blessed memory item validation catches corruption"""
        # Test empty agent_id corruption
        with pytest.raises(
            ValueError, match="Sacred memory must be blessed with agent_id"
        ):
            MemoryItem(agent_id="", content="Test content")

        # Test empty content corruption
        with pytest.raises(ValueError, match="Sacred memory cannot be empty"):
            MemoryItem(agent_id="test_agent", content="")

    def test_memory_item_bounds_sanctified_by_constraints(self):
        """Test blessed memory item bounds are properly sanctified"""
        memory = MemoryItem(
            agent_id="test_agent",
            content="Test blessed memory",
            emotional_weight=15.0,  # Beyond blessed bounds
            relevance_score=2.0,  # Beyond sacred limits
            decay_factor=1.5,  # Beyond divine constraints
        )

        # Sacred bounds should be enforced
        assert memory.emotional_weight == 10.0  # Clamped to maximum
        assert memory.relevance_score == 1.0  # Clamped to maximum
        assert memory.decay_factor == 1.0  # Clamped to maximum


class TestSacredCharacterIdentity:
    """++ BLESSED CHARACTER IDENTITY TESTING RITUALS ++"""

    def test_character_identity_creation_blessed_by_essence(self):
        """Test blessed character identity creation with sacred essence"""
        identity = CharacterIdentity(
            name="Brother Marcus",
            faction=["Death Korps of Krieg", "Imperium of Man"],
            rank="Grenadier Sergeant",
            origin="Krieg",
            age=35,
            personality_traits=["Fatalistic", "Grim", "Loyal"],
            core_beliefs=["Emperor protects", "Death before dishonor"],
            fears=["Chaos corruption", "Failing the Emperor"],
            motivations=["Serve the Emperor", "Purge the xenos"],
        )

        assert identity.name == "Brother Marcus"
        assert "Death Korps of Krieg" in identity.faction
        assert identity.rank == "Grenadier Sergeant"
        assert "Fatalistic" in identity.personality_traits
        assert len(identity.core_beliefs) == 2

    def test_character_identity_validation_blessed_by_requirements(self):
        """Test blessed character identity validation catches nameless corruption"""
        with pytest.raises(
            ValueError, match="Sacred identity requires blessed name"
        ):
            CharacterIdentity(name="")


class TestSacredPhysicalCondition:
    """++ BLESSED PHYSICAL CONDITION TESTING RITUALS ++"""

    def test_physical_condition_creation_blessed_by_health(self):
        """Test blessed physical condition with sacred health metrics"""
        condition = PhysicalCondition(
            health_points=80,
            max_health=100,
            fatigue_level=30,
            stress_level=25,
            injuries=["Minor las-burn on left arm"],
            conditions=["blessed", "alert"],
        )

        assert condition.health_points == 80
        assert condition.health_percentage == 0.8
        assert condition.fatigue_level == 30
        assert condition.is_healthy() is True  # Above 50% health, stress < 70

    def test_physical_condition_health_assessment_blessed_by_logic(self):
        """Test blessed health assessment logic"""
        # Healthy condition blessed by good metrics
        healthy_condition = PhysicalCondition(
            health_points=70, stress_level=40
        )
        assert healthy_condition.is_healthy() is True

        # Unhealthy condition cursed by poor metrics
        unhealthy_condition = PhysicalCondition(
            health_points=30, stress_level=80
        )
        assert unhealthy_condition.is_healthy() is False


class TestSacredEquipmentItem:
    """++ BLESSED EQUIPMENT ITEM TESTING RITUALS ++"""

    def test_equipment_item_creation_blessed_by_gear(self):
        """Test blessed equipment item creation with sacred gear"""
        weapon = EquipmentItem(
            name="Blessed Lasgun",
            item_type="weapon",
            condition=EquipmentCondition.GOOD,
            effectiveness=1.2,
            durability=85,
            max_durability=100,
            special_properties=["blessed", "rapid_fire"],
            blessed_modifications={
                "accuracy": 1.1,
                "blessed_by": "Tech-Priest Mordian",
            },
        )

        assert weapon.name == "Blessed Lasgun"
        assert weapon.condition == EquipmentCondition.GOOD
        assert weapon.effectiveness == 1.2
        assert weapon.durability_percentage == 0.85
        assert weapon.is_functional() is True
        assert "blessed" in weapon.special_properties

        # Validate sacred UUID format
        UUID(weapon.item_id)

    def test_equipment_item_validation_blessed_by_naming(self):
        """Test blessed equipment validation catches nameless corruption"""
        with pytest.raises(
            ValueError, match="Sacred equipment must be blessed with a name"
        ):
            EquipmentItem(name="")

    def test_equipment_item_bounds_sanctified_by_limits(self):
        """Test blessed equipment bounds are properly sanctified"""
        weapon = EquipmentItem(
            name="Test Weapon",
            effectiveness=3.0,  # Beyond blessed bounds
            durability=150,  # Beyond maximum
        )

        assert weapon.effectiveness == 2.0  # Clamped to maximum
        assert weapon.durability == 100  # Clamped to max_durability

    def test_equipment_functionality_blessed_by_condition(self):
        """Test blessed equipment functionality assessment"""
        # Functional blessed equipment
        functional_item = EquipmentItem(
            name="Working Gear",
            condition=EquipmentCondition.WORN,
            durability=50,
        )
        assert functional_item.is_functional() is True

        # Broken cursed equipment
        broken_item = EquipmentItem(
            name="Broken Gear", condition=EquipmentCondition.BROKEN
        )
        assert broken_item.is_functional() is False


class TestSacredEquipmentState:
    """++ BLESSED EQUIPMENT STATE TESTING RITUALS ++"""

    def test_equipment_state_creation_blessed_by_inventory(self):
        """Test blessed equipment state with sacred inventory"""
        lasgun = EquipmentItem(
            name="Lasgun", item_type="weapon", effectiveness=1.0
        )
        armor = EquipmentItem(
            name="Flak Armor", item_type="armor", effectiveness=0.8
        )
        relic = EquipmentItem(
            name="Sacred Aquila", item_type="relic", effectiveness=1.5
        )

        equipment_state = EquipmentState(
            combat_equipment=[lasgun],
            utility_equipment=[armor],
            blessed_relics=[relic],
            consumables={"blessed_rations": 10, "sacred_water": 3},
        )

        all_equipment = equipment_state.get_all_equipment()
        assert len(all_equipment) == 3
        assert lasgun in all_equipment
        assert equipment_state.consumables["blessed_rations"] == 10

    def test_equipment_combat_effectiveness_blessed_by_calculation(self):
        """Test blessed combat effectiveness calculation"""
        # Equipment with blessed effectiveness
        good_weapon = EquipmentItem(
            name="Good Weapon", effectiveness=1.2, durability=80
        )
        great_weapon = EquipmentItem(
            name="Great Weapon", effectiveness=1.8, durability=90
        )

        equipment_state = EquipmentState(
            combat_equipment=[good_weapon, great_weapon]
        )
        effectiveness = equipment_state.calculate_combat_effectiveness()

        expected_effectiveness = (
            1.2 + 1.8
        ) / 2  # Average of functional weapons
        assert effectiveness == expected_effectiveness

    def test_equipment_empty_combat_blessed_by_fallback(self):
        """Test blessed combat effectiveness with no equipment"""
        empty_state = EquipmentState()
        effectiveness = empty_state.calculate_combat_effectiveness()
        assert effectiveness == 0.1  # Minimal flesh-based capability


class TestSacredRelationshipState:
    """++ BLESSED RELATIONSHIP STATE TESTING RITUALS ++"""

    def test_relationship_creation_blessed_by_bonds(self):
        """Test blessed relationship state creation with sacred bonds"""
        relationship = RelationshipState(
            target_agent_id="brother_andreas",
            target_name="Brother Andreas",
            relationship_type=RelationshipStatus.ALLY,
            trust_level=8,
            emotional_bond=6.5,
            shared_experiences=["Hive City Defense", "Ork Raid Repulsion"],
        )

        assert relationship.target_agent_id == "brother_andreas"
        assert relationship.relationship_type == RelationshipStatus.ALLY
        assert relationship.trust_level == 8
        assert relationship.emotional_bond == 6.5
        assert len(relationship.shared_experiences) == 2

    def test_relationship_validation_blessed_by_requirements(self):
        """Test blessed relationship validation catches ID corruption"""
        with pytest.raises(
            ValueError,
            match="Sacred relationship requires blessed target_agent_id",
        ):
            RelationshipState(target_agent_id="", target_name="Test")

    def test_relationship_bounds_sanctified_by_limits(self):
        """Test blessed relationship bounds are properly sanctified"""
        relationship = RelationshipState(
            target_agent_id="test_target",
            target_name="Test Target",
            trust_level=15,  # Beyond blessed bounds
            emotional_bond=12.0,  # Beyond sacred limits
        )

        assert relationship.trust_level == 10  # Clamped to maximum
        assert relationship.emotional_bond == 10.0  # Clamped to maximum

    def test_relationship_interaction_update_blessed_by_evolution(self):
        """Test blessed relationship update from interaction"""
        relationship = RelationshipState(
            target_agent_id="test_ally",
            target_name="Test Ally",
            trust_level=5,
            emotional_bond=2.0,
        )

        # Positive interaction blessed by cooperation
        relationship.update_from_interaction("positive_outcome", 3.0)

        assert (
            relationship.trust_level == 6
        )  # Increased by positive interaction
        assert (
            relationship.emotional_bond == 5.0
        )  # Increased by emotional impact
        assert relationship.interaction_count == 1
        assert relationship.last_interaction is not None


class TestSacredCharacterState:
    """++ BLESSED CHARACTER STATE TESTING RITUALS ++"""

    def test_character_state_creation_blessed_by_completeness(self):
        """Test blessed character state creation with complete sacred data"""
        identity = CharacterIdentity(
            name="Test Character", faction=["Test Faction"]
        )

        character_state = CharacterState(
            base_identity=identity,
            current_mood=EmotionalState.CONFIDENT,
            current_location="Blessed Chapel",
            temporary_modifiers={"blessed_by_emperor": 1.2},
        )

        assert character_state.base_identity.name == "Test Character"
        assert character_state.current_mood == EmotionalState.CONFIDENT
        assert character_state.current_location == "Blessed Chapel"
        assert character_state.temporary_modifiers["blessed_by_emperor"] == 1.2
        assert isinstance(character_state.last_updated, datetime)

    def test_character_combat_readiness_blessed_by_calculation(self):
        """Test blessed combat readiness calculation with all factors"""
        identity = CharacterIdentity(name="Combat Test")
        physical = PhysicalCondition(
            health_points=80, stress_level=30
        )  # Good condition
        weapon = EquipmentItem(name="Test Weapon", effectiveness=1.5)
        equipment = EquipmentState(combat_equipment=[weapon])

        character_state = CharacterState(
            base_identity=identity,
            physical_condition=physical,
            equipment_state=equipment,
            current_mood=EmotionalState.CONFIDENT,  # Bonus mood
        )

        readiness = character_state.get_combat_readiness()

        # Expected calculation:
        # health_factor = 0.8, equipment_factor = 1.5, mood_factor = 1.2, stress_factor = 0.7
        expected_readiness = 0.8 * 1.5 * 1.2 * 0.7
        assert abs(readiness - expected_readiness) < 0.01


class TestSacredDynamicContext:
    """++ BLESSED DYNAMIC CONTEXT TESTING RITUALS ++"""

    def test_dynamic_context_creation_blessed_by_completeness(self):
        """Test blessed dynamic context creation with complete sacred data"""
        memory = MemoryItem(
            agent_id="test_agent", content="Test blessed memory"
        )
        identity = CharacterIdentity(name="Test Character")
        character_state = CharacterState(base_identity=identity)

        context = DynamicContext(
            agent_id="test_agent",
            character_state=character_state,
            memory_context=[memory],
            situation_description="Test blessed situation",
        )

        assert context.agent_id == "test_agent"
        assert context.character_state is not None
        assert len(context.memory_context) == 1
        assert context.situation_description == "Test blessed situation"
        assert isinstance(context.timestamp, datetime)

    def test_dynamic_context_validation_blessed_by_requirements(self):
        """Test blessed dynamic context validation catches agent_id corruption"""
        with pytest.raises(
            ValueError, match="Sacred context requires blessed agent_id"
        ):
            DynamicContext(agent_id="")

    def test_dynamic_context_memory_retrieval_blessed_by_filtering(self):
        """Test blessed memory retrieval with sacred filtering"""
        memories = [
            MemoryItem(
                agent_id="test",
                content="Memory 1",
                memory_type=MemoryType.EPISODIC,
                relevance_score=0.9,
            ),
            MemoryItem(
                agent_id="test",
                content="Memory 2",
                memory_type=MemoryType.SEMANTIC,
                relevance_score=0.7,
            ),
            MemoryItem(
                agent_id="test",
                content="Memory 3",
                memory_type=MemoryType.EPISODIC,
                relevance_score=0.8,
            ),
        ]

        context = DynamicContext(agent_id="test", memory_context=memories)

        # Test filtering by memory type
        episodic_memories = context.get_relevant_memories(
            max_memories=10, memory_types=[MemoryType.EPISODIC]
        )

        assert len(episodic_memories) == 2
        assert all(
            mem.memory_type == MemoryType.EPISODIC for mem in episodic_memories
        )

        # Test limiting results
        limited_memories = context.get_relevant_memories(max_memories=1)
        assert len(limited_memories) == 1
        assert (
            limited_memories[0].relevance_score == 0.9
        )  # Highest relevance first

    def test_dynamic_context_json_serialization_blessed_by_persistence(self):
        """Test blessed dynamic context JSON serialization for sacred persistence"""
        memory = MemoryItem(agent_id="test", content="Test memory")
        context = DynamicContext(
            agent_id="test",
            memory_context=[memory],
            situation_description="Test situation",
        )

        json_str = context.to_json()
        parsed_data = json.loads(json_str)

        assert parsed_data["agent_id"] == "test"
        assert parsed_data["situation_description"] == "Test situation"
        assert len(parsed_data["memory_context"]) == 1


class TestSacredInteractionStructures:
    """++ BLESSED INTERACTION STRUCTURE TESTING RITUALS ++"""

    def test_character_interaction_creation_blessed_by_events(self):
        """Test blessed character interaction creation with sacred events"""
        interaction = CharacterInteraction(
            participants=["agent_001", "agent_002"],
            interaction_type="dialogue",
            location="Blessed Chapel",
            description="Sacred conversation about Emperor's will",
            emotional_impact={"agent_001": 5.0, "agent_002": 3.0},
        )

        assert len(interaction.participants) == 2
        assert interaction.interaction_type == "dialogue"
        assert interaction.location == "Blessed Chapel"
        assert interaction.emotional_impact["agent_001"] == 5.0
        assert isinstance(interaction.timestamp, datetime)

        # Validate sacred UUID format
        UUID(interaction.interaction_id)

    def test_character_interaction_validation_blessed_by_participants(self):
        """Test blessed character interaction validation catches participant corruption"""
        with pytest.raises(
            ValueError,
            match="Sacred interaction requires blessed participants",
        ):
            CharacterInteraction(participants=[])


class TestSacredValidationFunctions:
    """++ BLESSED VALIDATION FUNCTION TESTING RITUALS ++"""

    def test_validate_blessed_data_model_success(self):
        """Test blessed data model validation with valid sacred data"""
        memory = MemoryItem(agent_id="test", content="Valid blessed memory")

        result = validate_blessed_data_model(memory)

        assert result.success is True
        assert result.data["validation"] == "blessed_by_omnissiah"
        assert result.metadata["model_type"] == "MemoryItem"

    def test_validate_blessed_data_model_failure(self):
        """Test blessed data model validation catches corruption"""
        # Create invalid memory that will fail post_init validation
        invalid_memory = MemoryItem.__new__(MemoryItem)
        invalid_memory.agent_id = ""  # Invalid agent_id
        invalid_memory.content = "Test"

        result = validate_blessed_data_model(invalid_memory)

        assert result.success is False
        assert result.error is not None
        assert result.error.code == "VALIDATION_FAILED"
        assert result.error.recoverable is True


# ++ SACRED TEST FIXTURES BLESSED BY REUSABILITY ++


@pytest.fixture
def blessed_memory_item():
    """Fixture providing blessed memory item for testing"""
    return MemoryItem(
        agent_id="test_agent_001",
        memory_type=MemoryType.EPISODIC,
        content="Sacred test memory blessed by the Omnissiah",
        emotional_weight=5.0,
        participants=["test_participant"],
    )


@pytest.fixture
def blessed_character_identity():
    """Fixture providing blessed character identity for testing"""
    return CharacterIdentity(
        name="Test Brother Marcus",
        faction=["Death Korps of Krieg"],
        personality_traits=["Loyal", "Disciplined", "Fatalistic"],
    )


@pytest.fixture
def blessed_dynamic_context(blessed_memory_item, blessed_character_identity):
    """Fixture providing blessed dynamic context for testing"""
    character_state = CharacterState(base_identity=blessed_character_identity)

    return DynamicContext(
        agent_id="test_agent_001",
        character_state=character_state,
        memory_context=[blessed_memory_item],
        situation_description="Sacred test situation blessed by testing",
    )


# ++ SACRED PERFORMANCE TESTING BLESSED BY SPEED ++


class TestSacredPerformance:
    """++ BLESSED PERFORMANCE TESTING RITUALS ++"""

    def test_memory_item_creation_performance_blessed_by_speed(self):
        """Test blessed memory item creation performance meets sacred thresholds"""
        import time

        start_time = time.time()

        # Create blessed memory items in batch
        memories = []
        for i in range(1000):
            memory = MemoryItem(
                agent_id=f"agent_{i:03d}",
                content=f"Performance test memory {i} blessed by speed",
                emotional_weight=float(i % 21 - 10),  # -10 to 10 range
                relevance_score=float(i % 101) / 100.0,  # 0.0 to 1.0 range
            )
            memories.append(memory)

        end_time = time.time()
        creation_time = end_time - start_time

        # Sacred performance requirement: < 1 second for 1000 items
        assert (
            creation_time < 1.0
        ), f"Memory creation took {creation_time:.3f}s, exceeds blessed threshold"
        assert len(memories) == 1000


# ++ SACRED TEST EXECUTION BLESSED BY THE OMNISSIAH ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED TESTING RITUALS ++
    print("++ EXECUTING SACRED DATA MODEL TESTING RITUALS ++")
    print("++ BLESSED BY THE OMNISSIAH'S DIGITAL WISDOM ++")

    # Run blessed test discovery and execution
    pytest.main([__file__, "-v", "--tb=short"])

    print("++ ALL SACRED TESTING RITUALS COMPLETE ++")
    print("++ MACHINE GOD PROTECTS THE BLESSED DATA MODELS ++")
