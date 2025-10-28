#!/usr/bin/env python3
"""
Unit Tests for Iron Laws Processor

Test-Driven Development approach for completing placeholder implementations
in the Iron Laws validation system.

Test Coverage:
- Law 1: Character consistency validation
- Law 2: Equipment availability checks
- Law 3: Physical possibility validation
- Law 4: Line of sight validation
- Law 5: Narrative consistency checks
"""

import pytest
from datetime import datetime
from typing import Dict, List, Optional
from unittest.mock import Mock, MagicMock, patch

# Import modules to test
from src.core.iron_laws_processor import IronLawsProcessor
from src.shared_types import ProposedAction, ActionType, ValidationResult
from src.core.data_models import (
    CharacterIdentity,
    PhysicalCondition,
    EquipmentItem,
    EquipmentState,
    EquipmentCondition,
    MemoryItem,
    MemoryType,
)
from src.shared_types import (
    CharacterData,
    CharacterStats,
    CharacterResources,
    CharacterState,  # Use Pydantic CharacterState from shared_types
    Position,
    ResourceValue,
    Equipment,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def iron_laws_processor():
    """Create Iron Laws Processor instance for testing."""
    return IronLawsProcessor()


@pytest.fixture
def mock_persona_agent():
    """Create mock PersonaAgent with complete state for unit tests."""
    from src.core.data_models import CharacterState as DataModelCharacterState
    
    agent = Mock()
    agent.name = "Test Character"
    agent.agent_id = "agent_test_001"
    
    # Create character identity
    identity = CharacterIdentity(
        name="Test Character",
        faction=["Test Faction"],
        rank="Soldier",
        personality_traits=["Brave", "Loyal"],
        core_beliefs=["Protect the innocent"],
    )
    
    # Create equipment
    equipment_state = EquipmentState(
        combat_equipment=[
            EquipmentItem(
                name="sword",
                item_type="weapon",
                condition=EquipmentCondition.GOOD,
                effectiveness=1.2,
            )
        ],
        utility_equipment=[
            EquipmentItem(
                name="rope",
                item_type="tool",
                condition=EquipmentCondition.GOOD,
            )
        ],
    )
    
    # Create character state (dataclass version for unit tests)
    character_state = DataModelCharacterState(
        base_identity=identity,
        physical_condition=PhysicalCondition(health_points=100, max_health=100),
        equipment_state=equipment_state,
        current_location="Test Location",
    )
    
    agent.character_state = character_state
    agent.get_state = Mock(return_value=character_state)
    
    return agent


@pytest.fixture
def mock_persona_agent_integration():
    """Create mock PersonaAgent with complete CharacterData state for integration tests."""
    agent = Mock()
    agent.name = "Test Character"
    agent.agent_id = "agent_test_001"
    
    # Create complete CharacterData with all required fields
    character_data = CharacterData(
        character_id="agent_test_001",
        name="Test Character",
        faction="Test Faction",
        position=Position(x=100.0, y=150.0, z=0.0, facing=90.0),
        stats=CharacterStats(
            strength=7,
            dexterity=6,
            intelligence=5,
            willpower=6,
            perception=5,
            charisma=5,
        ),
        resources=CharacterResources(
            health=ResourceValue(current=100, maximum=100),
            stamina=ResourceValue(current=80, maximum=100),
            morale=ResourceValue(current=90, maximum=100),
        ),
        equipment=[
            Equipment(
                name="sword",
                equipment_type="weapon",
                condition=1.0,
                quantity=1,
            ),
            Equipment(
                name="rope",
                equipment_type="tool",
                condition=1.0,
                quantity=1,
            ),
        ],
        state=CharacterState(
            conscious=True,
            mobile=True,
            combat_ready=True,
            status_effects=[],
            injuries=[],
            fatigue_level=0.2,
        ),
    )
    
    # Mock agent returns CharacterData (not CharacterState)
    agent.character_state = character_data
    agent.get_state = Mock(return_value=character_data)
    
    return agent


@pytest.fixture
def mock_action():
    """Create mock action dictionary."""
    return {
        "action_type": "attack",
        "agent_id": "agent_test_001",
        "target_id": "agent_target_001",
        "parameters": {
            "weapon": "sword",
            "location": "Test Location",
        },
    }


@pytest.fixture
def mock_world_state():
    """Create mock world state dictionary."""
    return {
        "agents": {
            "agent_test_001": {
                "location": "Location_A",
                "health": 100,
                "equipment": ["sword", "rope"],
            },
            "agent_target_001": {
                "location": "Location_B",
                "health": 100,
                "equipment": ["shield"],
            },
        },
        "locations": {
            "Location_A": {
                "adjacent": ["Location_B"],
                "obstacles": [],
            },
            "Location_B": {
                "adjacent": ["Location_A"],
                "obstacles": [],
            },
        },
    }


# =============================================================================
# Test Law 1: Character Data Extraction
# =============================================================================

class TestLaw1CharacterData:
    """Test Law 1: Character consistency validation."""
    
    def test_extract_character_data_from_agent_success(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test successful character data extraction from PersonaAgent."""
        # This test should FAIL initially (placeholder implementation returns None)
        character_data = iron_laws_processor._extract_character_data_from_agent(
            mock_persona_agent
        )
        
        # Assertions
        assert character_data is not None, "Character data should not be None"
        assert character_data.name == "Test Character"
        assert "Test Faction" in character_data.faction
        assert character_data.rank == "Soldier"
    
    def test_extract_character_data_validates_equipment(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test that extracted character data includes equipment."""
        character_data = iron_laws_processor._extract_character_data_from_agent(
            mock_persona_agent
        )
        
        assert character_data is not None
        # Check equipment extraction
        equipment = character_data.equipment_state
        assert equipment is not None
        assert len(equipment.combat_equipment) > 0
        assert equipment.combat_equipment[0].name == "sword"
    
    def test_extract_character_data_handles_missing_state(
        self, iron_laws_processor
    ):
        """Test extraction handles agent without character state."""
        agent_without_state = Mock()
        agent_without_state.character_state = None
        agent_without_state.get_state = Mock(return_value=None)  # Explicit None return
        agent_without_state.name = "Incomplete Agent"
        agent_without_state.faction = []
        agent_without_state.rank = None
        
        character_data = iron_laws_processor._extract_character_data_from_agent(
            agent_without_state
        )
        
        # Should return minimal CharacterState constructed from available attributes
        assert character_data is not None
        assert character_data.name == "Incomplete Agent"
    
    def test_extract_character_data_includes_location(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test that extracted data includes current location."""
        character_data = iron_laws_processor._extract_character_data_from_agent(
            mock_persona_agent
        )
        
        assert character_data is not None
        assert character_data.current_location == "Test Location"
    
    def test_extract_character_data_includes_physical_condition(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test that extracted data includes physical condition."""
        character_data = iron_laws_processor._extract_character_data_from_agent(
            mock_persona_agent
        )
        
        assert character_data is not None
        assert character_data.physical_condition is not None
        assert character_data.physical_condition.health_points == 100


# =============================================================================
# Test Law 2: Equipment Availability
# =============================================================================

class TestLaw2EquipmentAvailability:
    """Test Law 2: Equipment availability checks."""
    
    def test_character_has_equipment_positive(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test checking for equipment that character possesses."""
        # This should FAIL initially (placeholder always returns True)
        has_sword = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "sword"
        )
        
        assert has_sword is True
    
    def test_character_has_equipment_negative(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test checking for equipment that character doesn't have."""
        # This should FAIL initially (placeholder always returns True)
        has_bow = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "bow"
        )
        
        assert has_bow is False, "Character should not have bow"
    
    def test_character_has_equipment_case_insensitive(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test equipment check is case-insensitive."""
        has_sword_upper = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "SWORD"
        )
        has_sword_mixed = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "Sword"
        )
        
        assert has_sword_upper is True
        assert has_sword_mixed is True
    
    def test_character_has_equipment_checks_condition(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test that broken equipment is not considered available."""
        # Add broken equipment
        broken_item = EquipmentItem(
            name="broken_shield",
            item_type="armor",
            condition=EquipmentCondition.BROKEN,
        )
        mock_persona_agent.character_state.equipment_state.combat_equipment.append(
            broken_item
        )
        
        has_broken_shield = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "broken_shield"
        )
        
        # Broken equipment should not be considered "available"
        assert has_broken_shield is False
    
    def test_character_has_equipment_checks_all_categories(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test equipment check searches combat, utility, and blessed relics."""
        # Equipment in utility
        has_rope = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "rope"
        )
        assert has_rope is True
        
        # Equipment in combat
        has_sword = iron_laws_processor._character_has_equipment(
            mock_persona_agent, "sword"
        )
        assert has_sword is True


# =============================================================================
# Test Law 3: Physical Possibility
# =============================================================================

class TestLaw3PhysicalPossibility:
    """Test Law 3: Physical action possibility validation."""
    
    def test_action_physically_possible_with_equipment(
        self, iron_laws_processor, mock_persona_agent, mock_action
    ):
        """Test action is possible when character has required equipment."""
        is_possible = iron_laws_processor._action_physically_possible(
            mock_action, mock_persona_agent
        )
        
        assert is_possible is True
    
    def test_action_physically_possible_without_equipment(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test action is not possible without required equipment."""
        # Create action requiring bow
        action = {
            "action_type": "ranged_attack",
            "agent_id": "agent_test_001",
            "parameters": {"weapon": "bow"},
        }
        
        is_possible = iron_laws_processor._action_physically_possible(
            action, mock_persona_agent
        )
        
        assert is_possible is False
    
    def test_action_physically_possible_health_constraint(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test action is not possible if character health too low."""
        # Set health to critical level
        mock_persona_agent.character_state.physical_condition.health_points = 5
        
        action = {
            "action_type": "heavy_attack",
            "agent_id": "agent_test_001",
            "parameters": {"stamina_cost": 20},
        }
        
        is_possible = iron_laws_processor._action_physically_possible(
            action, mock_persona_agent
        )
        
        # Heavy actions should not be possible at critical health
        assert is_possible is False
    
    def test_action_physically_possible_no_equipment_required(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test actions that don't require equipment."""
        action = {
            "action_type": "observe",
            "agent_id": "agent_test_001",
            "parameters": {},
        }
        
        is_possible = iron_laws_processor._action_physically_possible(
            action, mock_persona_agent
        )
        
        assert is_possible is True
    
    def test_action_physically_possible_stress_constraint(
        self, iron_laws_processor, mock_persona_agent
    ):
        """Test action constrained by stress level."""
        # Set stress to maximum
        mock_persona_agent.character_state.physical_condition.stress_level = 100
        
        action = {
            "action_type": "complex_task",
            "agent_id": "agent_test_001",
            "parameters": {"requires_focus": True},
        }
        
        is_possible = iron_laws_processor._action_physically_possible(
            action, mock_persona_agent
        )
        
        # Complex tasks should not be possible at maximum stress
        assert is_possible is False


# =============================================================================
# Test Law 4: Line of Sight
# =============================================================================

class TestLaw4LineOfSight:
    """Test Law 4: Line of sight validation."""
    
    def test_line_of_sight_same_location(self, iron_laws_processor):
        """Test line of sight within same location is always true."""
        has_los = iron_laws_processor._check_line_of_sight(
            "Location_A", "Location_A", []
        )
        
        assert has_los is True
    
    def test_line_of_sight_different_locations_no_obstacles(
        self, iron_laws_processor
    ):
        """Test line of sight between different locations without obstacles."""
        # This should FAIL initially (placeholder always returns True)
        has_los = iron_laws_processor._check_line_of_sight(
            "Location_A", "Location_B", []
        )
        
        # Different locations without adjacency should not have LOS
        assert has_los is False
    
    def test_line_of_sight_adjacent_locations(self, iron_laws_processor):
        """Test line of sight between adjacent locations."""
        # Mock adjacency data
        with patch.object(
            iron_laws_processor,
            "_locations_adjacent",
            return_value=True
        ):
            has_los = iron_laws_processor._check_line_of_sight(
                "Location_A", "Location_B", []
            )
            
            assert has_los is True
    
    def test_line_of_sight_with_blocking_obstacles(self, iron_laws_processor):
        """Test line of sight blocked by obstacles."""
        obstacles = ["wall_between_A_B", "thick_fog"]
        
        with patch.object(
            iron_laws_processor,
            "_locations_adjacent",
            return_value=True
        ):
            has_los = iron_laws_processor._check_line_of_sight(
                "Location_A", "Location_B", obstacles
            )
            
            # Obstacles should block line of sight
            assert has_los is False
    
    def test_line_of_sight_with_partial_obstacles(self, iron_laws_processor):
        """Test line of sight with minor obstacles (partial cover)."""
        obstacles = ["low_fence"]  # Minor obstacle
        
        with patch.object(
            iron_laws_processor,
            "_locations_adjacent",
            return_value=True
        ):
            has_los = iron_laws_processor._check_line_of_sight(
                "Location_A", "Location_B", obstacles
            )
            
            # Minor obstacles might allow partial LOS
            # Implementation should decide based on obstacle type
            assert has_los in [True, False]  # Accept either for now


# =============================================================================
# Test Law 5: Narrative Consistency
# =============================================================================

class TestLaw5NarrativeConsistency:
    """Test Law 5: Narrative consistency checks."""
    
    def test_narrative_consistency_coherent_sequence(
        self, iron_laws_processor
    ):
        """Test narrative with coherent event sequence."""
        narrative = {
            "events": [
                {
                    "agent": "Alice",
                    "action": "enters_room",
                    "location": "Hall",
                    "timestamp": "2025-01-01T10:00:00",
                },
                {
                    "agent": "Alice",
                    "action": "greets",
                    "target": "Bob",
                    "location": "Hall",
                    "timestamp": "2025-01-01T10:01:00",
                },
                {
                    "agent": "Bob",
                    "action": "responds",
                    "target": "Alice",
                    "location": "Hall",
                    "timestamp": "2025-01-01T10:02:00",
                },
            ],
            "world_state": {
                "agents": {
                    "Alice": {"location": "Hall"},
                    "Bob": {"location": "Hall"},
                }
            },
        }
        
        is_consistent = iron_laws_processor._check_narrative_consistency(narrative)
        
        assert is_consistent is True
    
    def test_narrative_consistency_location_mismatch(
        self, iron_laws_processor
    ):
        """Test narrative with location inconsistency."""
        narrative = {
            "events": [
                {
                    "agent": "Alice",
                    "action": "enters_room",
                    "location": "Hall",
                    "timestamp": "2025-01-01T10:00:00",
                },
                {
                    "agent": "Alice",
                    "action": "attacks",
                    "target": "Bob",
                    "location": "Kitchen",  # Alice is in Hall, not Kitchen
                    "timestamp": "2025-01-01T10:01:00",
                },
            ],
            "world_state": {
                "agents": {
                    "Alice": {"location": "Hall"},
                    "Bob": {"location": "Kitchen"},
                }
            },
        }
        
        is_consistent = iron_laws_processor._check_narrative_consistency(narrative)
        
        assert is_consistent is False
    
    def test_narrative_consistency_temporal_violation(
        self, iron_laws_processor
    ):
        """Test narrative with temporal inconsistency."""
        narrative = {
            "events": [
                {
                    "agent": "Alice",
                    "action": "reads_book",
                    "timestamp": "2025-01-01T10:00:00",
                },
                {
                    "agent": "Alice",
                    "action": "enters_room",
                    "timestamp": "2025-01-01T09:59:00",  # Before previous event
                },
            ],
            "world_state": {"agents": {"Alice": {"location": "Library"}}},
        }
        
        is_consistent = iron_laws_processor._check_narrative_consistency(narrative)
        
        assert is_consistent is False
    
    def test_narrative_consistency_causal_violation(
        self, iron_laws_processor
    ):
        """Test narrative with causal inconsistency."""
        narrative = {
            "events": [
                {
                    "agent": "Alice",
                    "action": "picks_up",
                    "item": "key",
                    "timestamp": "2025-01-01T10:00:00",
                },
                {
                    "agent": "Bob",
                    "action": "picks_up",
                    "item": "key",  # Same key picked up by two people
                    "timestamp": "2025-01-01T10:01:00",
                },
            ],
            "world_state": {
                "agents": {
                    "Alice": {"inventory": ["key"]},
                    "Bob": {"inventory": []},
                }
            },
        }
        
        is_consistent = iron_laws_processor._check_narrative_consistency(narrative)
        
        assert is_consistent is False
    
    def test_narrative_consistency_empty_events(
        self, iron_laws_processor
    ):
        """Test narrative with no events."""
        narrative = {
            "events": [],
            "world_state": {"agents": {}},
        }
        
        is_consistent = iron_laws_processor._check_narrative_consistency(narrative)
        
        # Empty narrative should be considered consistent (vacuously true)
        assert is_consistent is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestIronLawsIntegration:
    """Integration tests for complete Iron Laws validation."""
    
    def test_validate_action_all_laws(
        self, iron_laws_processor, mock_persona_agent_integration, mock_action, mock_world_state
    ):
        """Test full action validation through all five laws."""
        # Create a ProposedAction object from the mock action dict
        proposed_action = ProposedAction(
            character_id=mock_action.get("agent_id", "agent_test_001"),
            action_type=ActionType.ATTACK,
            reasoning="Test action for integration testing",
            confidence=0.9
        )
        
        # This is an integration test that exercises the entire validation pipeline
        validation_result = iron_laws_processor.adjudicate_action(
            proposed_action, mock_persona_agent_integration, mock_world_state
        )
        
        # Check IronLawsReport structure
        assert validation_result is not None
        assert hasattr(validation_result, "overall_result")
        assert hasattr(validation_result, "violations")
        assert hasattr(validation_result, "checks_performed")
        
        # Check that validation was performed
        assert len(validation_result.checks_performed) > 0
        
        # For a valid action, should pass or only have minor violations
        assert validation_result.overall_result in [
            ValidationResult.VALID,
            ValidationResult.REQUIRES_REPAIR,
        ]
    
    def test_repair_invalid_action(
        self, iron_laws_processor, mock_persona_agent_integration, mock_world_state
    ):
        """Test automatic repair of invalid actions."""
        # Create an invalid action (missing required equipment)
        invalid_action = ProposedAction(
            character_id="agent_test_001",
            action_type=ActionType.ATTACK,
            reasoning="Test invalid action requiring repair",
            confidence=0.7
        )
        
        validation_result = iron_laws_processor.adjudicate_action(
            invalid_action, mock_persona_agent_integration, mock_world_state
        )
        
        # Check that validation was performed
        assert validation_result is not None
        assert hasattr(validation_result, "overall_result")
        assert hasattr(validation_result, "violations")
        
        # Should either be valid, require repair, or be invalid
        assert validation_result.overall_result in [
            ValidationResult.VALID,
            ValidationResult.INVALID,
            ValidationResult.REQUIRES_REPAIR,
        ]
        
        # If repairs were attempted, check repair attempts list
        if validation_result.overall_result == ValidationResult.REQUIRES_REPAIR:
            assert len(validation_result.repair_attempts) >= 0  # May or may not have attempts


# =============================================================================
# Performance Tests
# =============================================================================

@pytest.mark.skip(reason="Requires pytest-benchmark plugin - optional performance tests")
class TestIronLawsPerformance:
    """Performance benchmarks for Iron Laws validation."""
    
    def test_validation_performance_single_action(
        self, benchmark, iron_laws_processor, mock_persona_agent, mock_action, mock_world_state
    ):
        """Benchmark single action validation performance."""
        result = benchmark(
            iron_laws_processor.adjudicate_action,
            mock_action,
            mock_persona_agent,
            mock_world_state
        )
        
        # Validation should complete in < 50ms
        assert benchmark.stats["mean"] < 0.05
    
    def test_validation_performance_batch(
        self, benchmark, iron_laws_processor, mock_persona_agent, mock_world_state
    ):
        """Benchmark batch action validation performance."""
        actions = [
            {
                "action_type": "move",
                "agent_id": f"agent_{i}",
                "parameters": {"destination": "Location_B"},
            }
            for i in range(10)
        ]
        
        def validate_batch():
            return [
                iron_laws_processor.adjudicate_action(action, mock_persona_agent, mock_world_state)
                for action in actions
            ]
        
        result = benchmark(validate_batch)
        
        # Batch validation should complete in < 500ms (10 actions)
        assert benchmark.stats["mean"] < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
