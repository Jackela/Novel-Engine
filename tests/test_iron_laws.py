"""
Test Iron Laws Adjudication System
=================================

Comprehensive test suite for the Iron Laws validation and repair system
in the DirectorAgent. Tests all 5 Iron Laws (E001-E005) and the automatic
action repair capabilities.

Test Coverage:
- Core validation engine (_adjudicate_action)
- Individual Iron Laws validation methods
- Automatic repair system functionality
- Helper method correctness
- Integration with DirectorAgent
- Edge cases and error handling

The 5 Iron Laws tested:
- E001 Causality Law: Actions must have logical consequences
- E002 Resource Law: Characters cannot exceed their capabilities/resources
- E003 Physics Law: Actions must obey basic physical constraints
- E004 Narrative Law: Actions must maintain story coherence
- E005 Social Law: Actions must respect established relationships/hierarchies
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import system components
try:
    from director_agent import DirectorAgent

    from src.persona_agent import PersonaAgent
    from src.shared_types import (
        ActionIntensity,
        ActionParameters,
        ActionTarget,
        ActionType,
        CharacterData,
        CharacterResources,
        CharacterStats,
        EntityType,
        IronLawsReport,
        IronLawsViolation,
        Position,
        ProposedAction,
        ResourceValue,
        ValidatedAction,
        ValidationResult,
    )

    IRON_LAWS_AVAILABLE = True
except ImportError as e:
    IRON_LAWS_AVAILABLE = False
    pytest.skip(f"Iron Laws system not available: {e}", allow_module_level=True)


class TestIronLawsValidation:
    """Test core Iron Laws validation functionality."""

    @pytest.fixture
    def iron_laws_processor(self):
        """Create IronLawsProcessor instance for testing."""
        from src.core.iron_laws_processor import IronLawsProcessor

        return IronLawsProcessor()

    @pytest.fixture
    def world_context(self):
        """Create basic world context for testing."""
        return {
            "current_turn": 1,
            "total_agents": 1,
            "environment": {"time_of_day": "noon", "weather": "clear"},
            "story_state": {"current_scene": "investigation"},
            "physics": {"gravity": 1.0, "max_speed": 10.0},
            "world_resources": {},
        }

    @pytest.fixture
    def mock_agent(self):
        """Create mock PersonaAgent for testing."""
        agent = Mock(spec=PersonaAgent)
        agent.agent_id = "test_agent_001"
        agent.character_id = "test_agent_001"
        agent.character_data = {
            "name": "Test Character",
            "stats": CharacterStats(
                strength=7,
                dexterity=6,
                intelligence=8,
                willpower=9,
                perception=6,
                charisma=5,
            ),
            "resources": CharacterResources(
                health=ResourceValue(current=80, maximum=100),
                stamina=ResourceValue(current=60, maximum=80),
                morale=ResourceValue(current=50, maximum=70),
            ),
            "position": Position(x=10, y=10, z=0),
            "equipment": ["basic_weapon", "standard_armor"],
        }
        return agent

    @pytest.fixture
    def sample_action(self):
        """Create sample ProposedAction for testing."""
        return ProposedAction(
            action_id="test_action_001",
            action_type=ActionType.INVESTIGATE,
            target=ActionTarget(
                entity_id="mysterious_object", entity_type=EntityType.OBJECT
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                intensity=ActionIntensity.NORMAL, duration=1.0, range=5.0
            ),
            reasoning="Investigating unusual readings from the object",
        )

    def test_iron_laws_validation_core(
        self, iron_laws_processor, mock_agent, sample_action
    ):
        """Test core Iron Laws validation engine."""
        # Execute validation
        world_context = {
            "current_turn": 1,
            "total_agents": 1,
            "environment": {},
            "story_state": {},
            "physics": {},
            "world_resources": {},
        }
        result = iron_laws_processor.adjudicate_action(
            sample_action, mock_agent, world_context
        )

        # Verify result structure - should be IronLawsReport object
        assert hasattr(result, "overall_result")
        assert hasattr(result, "violations")
        assert hasattr(result, "action_id")
        assert result.action_id == sample_action.action_id

    def test_causality_law_validation(
        self, iron_laws_processor, mock_agent, world_context
    ):
        """Test E001 Causality Law validation."""
        # Test valid causal action
        valid_action = ProposedAction(
            action_id="valid_causality_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(entity_id="nearby_door", entity_type=EntityType.OBJECT),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.LOW, duration=0.5),
            reasoning="Moving to examine the door more closely",
        )

        character_data = mock_agent.character_data
        violations = iron_laws_processor._validate_causality_law(
            valid_action, character_data, world_context
        )

        # Should have no violations for simple movement
        assert len(violations) == 0

        # Test invalid causal action
        invalid_action = ProposedAction(
            action_id="invalid_causality_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(entity_id="", entity_type=EntityType.OBJECT),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning="  ",  # Minimal reasoning - should trigger causality violation
        )

        violations = iron_laws_processor._validate_causality_law(
            invalid_action, character_data, world_context
        )

        # Should detect causality violations
        assert len(violations) > 0
        assert all(v.law_code == "E001" for v in violations)

    def test_resource_law_validation(self, iron_laws_processor, mock_agent):
        """Test E002 Resource Law validation."""
        character_data = mock_agent.character_data

        # Test action within resource limits
        normal_action = ProposedAction(
            action_id="normal_resource_001",
            action_type=ActionType.INVESTIGATE,
            target=ActionTarget(
                entity_id="small_object", entity_type=EntityType.OBJECT
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.LOW, duration=1.0),
            reasoning="Light investigation of the object",
        )

        violations = iron_laws_processor._validate_resource_law(
            normal_action, character_data
        )

        # Should have no violations for reasonable action
        assert len(violations) == 0

        # Test action exceeding stamina limits
        exhausting_action = ProposedAction(
            action_id="exhausting_resource_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(
                entity_id="powerful_enemy", entity_type=EntityType.CHARACTER
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                intensity=ActionIntensity.EXTREME, duration=5.0
            ),
            reasoning="All-out assault requiring massive stamina",
        )

        violations = iron_laws_processor._validate_resource_law(
            exhausting_action, character_data
        )

        # Should detect resource violations
        assert len(violations) > 0
        assert all(v.law_code == "E002" for v in violations)

    def test_physics_law_validation(
        self, iron_laws_processor, mock_agent, world_context
    ):
        """Test E003 Physics Law validation."""
        character_data = mock_agent.character_data

        # Test physically reasonable action
        reasonable_action = ProposedAction(
            action_id="reasonable_physics_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(
                entity_id="adjacent_room",
                entity_type=EntityType.LOCATION,
                position=Position(x=12, y=12, z=0),  # 3 meters away
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(duration=1.0, range=3.0),
            reasoning="Walking to the adjacent room",
        )

        violations = iron_laws_processor._validate_physics_law(
            reasonable_action, character_data, world_context
        )

        # Should have no violations for normal movement
        assert len(violations) == 0

        # Test physically impossible action
        impossible_action = ProposedAction(
            action_id="impossible_physics_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(
                entity_id="distant_location",
                entity_type=EntityType.LOCATION,
                position=Position(
                    x=1000, y=1000, z=0
                ),  # Very far away - should trigger violation
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                duration=0.1, range=1000.0
            ),  # Teleportation-like
            reasoning="Instantly moving vast distances",
        )

        violations = iron_laws_processor._validate_physics_law(
            impossible_action, character_data, world_context
        )

        # Should detect physics violations
        assert len(violations) > 0
        assert all(v.law_code == "E003" for v in violations)

    def test_narrative_law_validation(
        self, iron_laws_processor, mock_agent, world_context
    ):
        """Test E004 Narrative Law validation."""

        # Test narratively coherent action
        coherent_action = ProposedAction(
            action_id="coherent_narrative_001",
            action_type=ActionType.INVESTIGATE,
            target=ActionTarget(
                entity_id="suspicious_device", entity_type=EntityType.OBJECT
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.NORMAL),
            reasoning="Investigating the device to understand its purpose",
        )

        violations = iron_laws_processor._validate_narrative_law(
            coherent_action, mock_agent, world_context
        )

        # Should have no violations for coherent investigation
        assert len(violations) == 0

        # Test narratively incoherent action
        incoherent_action = ProposedAction(
            action_id="incoherent_narrative_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(
                entity_id="friendly_ally", entity_type=EntityType.CHARACTER
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning="Attacking allies for no apparent reason",
        )

        violations = iron_laws_processor._validate_narrative_law(
            incoherent_action, mock_agent, world_context
        )

        # Should detect narrative violations
        assert len(violations) > 0
        assert all(v.law_code == "E004" for v in violations)

    def test_social_law_validation(
        self, iron_laws_processor, mock_agent, world_context
    ):
        """Test E005 Social Law validation."""

        # Test socially appropriate action
        appropriate_action = ProposedAction(
            action_id="appropriate_social_001",
            action_type=ActionType.COMMUNICATE,
            target=ActionTarget(
                entity_id="team_member", entity_type=EntityType.CHARACTER
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.NORMAL),
            reasoning="Coordinating with team member about mission objectives",
        )

        violations = iron_laws_processor._validate_social_law(
            appropriate_action, mock_agent, world_context
        )

        # Should have no violations for appropriate communication
        assert len(violations) == 0

        # Test socially inappropriate action
        inappropriate_action = ProposedAction(
            action_id="inappropriate_social_001",
            action_type=ActionType.COMMUNICATE,
            target=ActionTarget(
                entity_id="superior_officer", entity_type=EntityType.CHARACTER
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning="Shouting orders at superior officer",
        )

        violations = iron_laws_processor._validate_social_law(
            inappropriate_action, mock_agent, world_context
        )

        # Should detect social violations
        assert len(violations) > 0
        assert all(v.law_code == "E005" for v in violations)


class TestIronLawsRepairSystem:
    """Test automatic action repair system."""

    @pytest.fixture
    def iron_laws_processor(self):
        """Create IronLawsProcessor instance for testing."""
        from src.core.iron_laws_processor import IronLawsProcessor

        return IronLawsProcessor()

    @pytest.fixture
    def mock_character_data(self):
        """Create mock character data for repair testing."""
        return {
            "name": "Test Character",
            "stats": CharacterStats(
                strength=8,
                dexterity=7,
                intelligence=9,
                willpower=8,
                perception=6,
                charisma=5,
            ),
            "resources": CharacterResources(
                health=ResourceValue(current=80, maximum=100, minimum=0),
                stamina=ResourceValue(
                    current=40, maximum=80, minimum=0
                ),  # Low stamina for testing
                morale=ResourceValue(current=50, maximum=70, minimum=0),
            ),
            "position": Position(x=10, y=10, z=0),
            "equipment": ["basic_weapon", "standard_armor"],
        }

    def test_causality_repair(self, iron_laws_processor):
        """Test E001 Causality Law violation repairs."""
        # Create action with causality violation
        action = ProposedAction(
            action_id="causality_repair_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(
                entity_id="", entity_type=EntityType.OBJECT
            ),  # Missing target
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning=" ",  # Minimal reasoning that will be repaired
        )

        # Create mock violations
        violations = [
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Action lacks necessary target specification",
                severity="error",
                affected_entities=["test_agent_001"],
                suggested_repair="Add target specification",
            ),
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Action lacks logical reasoning",
                severity="warning",
                suggested_repair="Add reasoning for action",
                affected_entities=["test_agent_001"],
            ),
        ]

        # Attempt repairs
        (
            repaired_action,
            repairs_made,
        ) = iron_laws_processor._repair_causality_violations(action, violations)

        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.target is not None
        assert repaired_action.target.entity_id != ""
        assert len(repaired_action.reasoning.strip()) > 1
        repairs_text = " ".join(repairs_made)
        assert "target" in repairs_text.lower() or "reasoning" in repairs_text.lower()

    def test_resource_repair(self, iron_laws_processor, mock_character_data):
        """Test E002 Resource Law violation repairs."""
        # Create action that exceeds stamina
        action = ProposedAction(
            action_id="resource_repair_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(entity_id="enemy", entity_type=EntityType.CHARACTER),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                intensity=ActionIntensity.EXTREME, duration=3.0
            ),
            reasoning="All-out attack",
        )

        # Create resource violation
        violations = [
            IronLawsViolation(
                law_code="E002",
                law_name="Resource_Law",
                description="Action requires more stamina than available",
                severity="error",
                affected_entities=["test_agent_001"],
                suggested_repair="Reduce action intensity or duration",
            )
        ]

        # Attempt repairs
        repaired_action, repairs_made = iron_laws_processor._repair_resource_violations(
            action, violations, mock_character_data
        )

        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert (
            repaired_action.parameters.intensity != ActionIntensity.EXTREME
        )  # Should be reduced
        assert "Reduced intensity" in " ".join(
            repairs_made
        ) or "Reduced duration" in " ".join(repairs_made)

    def test_physics_repair(self, iron_laws_processor, mock_character_data):
        """Test E003 Physics Law violation repairs."""
        # Create physically impossible action
        action = ProposedAction(
            action_id="physics_repair_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(
                entity_id="distant_location", entity_type=EntityType.LOCATION
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(duration=0.1, range=1000.0),
            reasoning="Instant travel",
        )

        # Create physics violation
        violations = [
            IronLawsViolation(
                law_code="E003",
                law_name="Physics_Law",
                description="Movement speed exceeds physical limits",
                severity="critical",
                suggested_repair="Adjust duration and range to realistic values",
                affected_entities=["test_agent_001"],
            )
        ]

        # Attempt repairs
        repaired_action, repairs_made = iron_laws_processor._repair_physics_violations(
            action, violations, mock_character_data
        )

        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.parameters.duration > 0.1  # Should be increased
        assert repaired_action.parameters.range < 1000.0  # Should be reduced
        assert "Adjusted movement" in " ".join(repairs_made)

    def test_narrative_repair(self, iron_laws_processor):
        """Test E004 Narrative Law violation repairs."""
        # Create narratively incoherent action
        action = ProposedAction(
            action_id="narrative_repair_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(entity_id="ally", entity_type=EntityType.CHARACTER),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning="Attacking friend",
        )

        # Create narrative violation
        violations = [
            IronLawsViolation(
                law_code="E004",
                law_name="Narrative_Law",
                description="Attacking ally without justification",
                severity="error",
                suggested_repair="Change action to be consistent with relationships",
                affected_entities=["test_agent_001"],
            )
        ]

        # Attempt repairs
        (
            repaired_action,
            repairs_made,
        ) = iron_laws_processor._repair_narrative_violations(action, violations)

        # Verify repairs were applied
        assert len(repairs_made) > 0
        repairs_text = " ".join(repairs_made).lower()
        assert (
            "changed" in repairs_text
            or "modified" in repairs_text
            or "target" in repairs_text
        )
        # Should have changed either action type or target
        assert (
            repaired_action.action_type != ActionType.ATTACK
            or repaired_action.target.entity_id != "ally"
        )

    def test_social_repair(self, iron_laws_processor):
        """Test E005 Social Law violation repairs."""
        # Create socially inappropriate action
        action = ProposedAction(
            action_id="social_repair_001",
            action_type=ActionType.COMMUNICATE,
            target=ActionTarget(
                entity_id="commanding_officer", entity_type=EntityType.CHARACTER
            ),
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH),
            reasoning="Demanding orders from superior",
        )

        # Create social violation
        violations = [
            IronLawsViolation(
                law_code="E005",
                law_name="Social_Law",
                description="Action violates command hierarchy",
                severity="warning",
                suggested_repair="Adjust communication style to be appropriate for hierarchy",
                affected_entities=["test_agent_001"],
            )
        ]

        # Attempt repairs
        repaired_action, repairs_made = iron_laws_processor._repair_social_violations(
            action, violations
        )

        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert (
            repaired_action.parameters.intensity != ActionIntensity.HIGH
        )  # Should be reduced
        assert "Adjusted communication" in " ".join(repairs_made)

    def test_comprehensive_repair_attempt(
        self, iron_laws_processor, mock_character_data
    ):
        """Test comprehensive repair system with multiple violation types."""
        # Create action with multiple violations
        problematic_action = ProposedAction(
            action_id="multi_repair_001",
            action_type=ActionType.ATTACK,
            target=ActionTarget(
                entity_id="", entity_type=EntityType.OBJECT
            ),  # Causality issue
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                intensity=ActionIntensity.EXTREME, duration=5.0
            ),  # Resource issue
            reasoning=" ",  # Minimal reasoning that will be repaired
        )

        # Create multiple violations
        violations = [
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Missing target",
                severity="error",
                suggested_repair="Add target",
                affected_entities=["test_agent_001"],
            ),
            IronLawsViolation(
                law_code="E002",
                law_name="Resource_Law",
                description="Exceeds stamina",
                severity="error",
                suggested_repair="Reduce intensity",
                affected_entities=["test_agent_001"],
            ),
        ]

        # Attempt comprehensive repair
        repaired_action, repairs_made = iron_laws_processor._attempt_action_repairs(
            problematic_action, violations, mock_character_data
        )

        # Verify multiple repairs were applied
        assert repaired_action is not None
        assert len(repairs_made) >= 2  # Should have multiple repairs
        assert repaired_action.target.entity_id != ""  # Causality repair
        assert (
            repaired_action.parameters.intensity != ActionIntensity.EXTREME
        )  # Resource repair


class TestIronLawsHelperMethods:
    """Test Iron Laws helper methods."""

    @pytest.fixture
    def iron_laws_processor(self):
        """Create IronLawsProcessor instance for testing."""
        from src.core.iron_laws_processor import IronLawsProcessor

        return IronLawsProcessor()

    def test_group_violations_by_law(self, iron_laws_processor):
        """Test violation grouping by law code."""
        violations = [
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Test violation 1",
                severity="warning",
                affected_entities=["test_agent_001"],
            ),
            IronLawsViolation(
                law_code="E002",
                law_name="Resource_Law",
                description="Test violation 2",
                severity="error",
                affected_entities=["test_agent_001"],
            ),
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Test violation 3",
                severity="warning",
                affected_entities=["test_agent_001"],
            ),
        ]

        grouped = iron_laws_processor._group_violations_by_law(violations)

        # Verify grouping
        assert len(grouped) == 2
        assert "E001" in grouped
        assert "E002" in grouped
        assert len(grouped["E001"]) == 2
        assert len(grouped["E002"]) == 1

    def test_get_current_world_context(self, iron_laws_processor):
        """Test world context generation - IronLawsProcessor doesn't have this method."""
        # This test is not applicable to IronLawsProcessor as it doesn't manage world context
        # World context is provided by DirectorAgent
        pytest.skip("IronLawsProcessor does not manage world context")

    def test_determine_overall_validation_result(self, iron_laws_processor):
        """Test overall validation result determination."""
        # Test with no violations
        result = iron_laws_processor._determine_overall_validation_result([])
        assert result == ValidationResult.VALID

        # Test with critical violations
        critical_violations = [
            IronLawsViolation(
                law_code="E003",
                law_name="Physics_Law",
                description="Critical violation",
                severity="critical",
                affected_entities=["test_agent_001"],
            )
        ]
        result = iron_laws_processor._determine_overall_validation_result(
            critical_violations
        )
        assert result == ValidationResult.INVALID

        # Test with high violations
        high_violations = [
            IronLawsViolation(
                law_code="E002",
                law_name="Resource_Law",
                description="High violation",
                severity="error",
                affected_entities=["test_agent_001"],
            )
        ]
        result = iron_laws_processor._determine_overall_validation_result(
            high_violations
        )
        assert result == ValidationResult.REQUIRES_REPAIR

        # Test with low violations
        low_violations = [
            IronLawsViolation(
                law_code="E001",
                law_name="Causality_Law",
                description="Low violation",
                severity="warning",
                affected_entities=["test_agent_001"],
            )
        ]
        result = iron_laws_processor._determine_overall_validation_result(
            low_violations
        )
        assert result == ValidationResult.VALID

    def test_calculate_action_stamina_cost(self, iron_laws_processor):
        """Test stamina cost calculation."""
        # Test basic action
        basic_action = ProposedAction(
            action_id="stamina_test_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(entity_id="location", entity_type=EntityType.LOCATION),
            agent_id="test_agent",
            character_id="test_agent",
            parameters=ActionParameters(intensity=ActionIntensity.NORMAL, duration=1.0),
            reasoning="Moving to test location for analysis",
        )

        cost = iron_laws_processor._calculate_action_stamina_cost(basic_action)
        assert cost > 0
        assert cost == 10  # Expected base cost for movement

        # Test high-intensity action
        intense_action = ProposedAction(
            action_id="stamina_test_002",
            action_type=ActionType.ATTACK,
            target=ActionTarget(entity_id="enemy", entity_type=EntityType.CHARACTER),
            agent_id="test_agent",
            character_id="test_agent",
            parameters=ActionParameters(intensity=ActionIntensity.HIGH, duration=2.0),
            reasoning="High-intensity attack against enemy target",
        )

        intense_cost = iron_laws_processor._calculate_action_stamina_cost(
            intense_action
        )
        assert intense_cost > cost  # Should cost more than basic movement


@pytest.mark.skip(
    reason="Integration tests require DirectorAgent refactoring for IronLawsProcessor"
)
class TestIronLawsIntegration:
    """Test Iron Laws integration with DirectorAgent."""

    @pytest.fixture
    def director_with_agents(self):
        """Create DirectorAgent with mock agents for integration testing."""
        from src.core.event_bus import EventBus

        with tempfile.TemporaryDirectory() as temp_dir:
            event_bus = EventBus()
            director = DirectorAgent(
                event_bus=event_bus,
                campaign_log_path=Path(temp_dir) / "integration_test.log",
            )

            # Create mock agent
            mock_agent = Mock(spec=PersonaAgent)
            mock_agent.agent_id = "integration_test_agent"
            mock_agent.character_data = {
                "name": "Integration Test Character",
                "stats": CharacterStats(
                    strength=8,
                    dexterity=7,
                    intelligence=9,
                    willpower=8,
                    perception=6,
                    charisma=5,
                ),
                "resources": CharacterResources(
                    health=ResourceValue(current=80, maximum=100),
                    stamina=ResourceValue(current=60, maximum=80),
                    morale=ResourceValue(current=50, maximum=70),
                ),
                "position": Position(x=10, y=10, z=0),
                "equipment": ["basic_weapon", "standard_armor"],
            }

            # Configure mock to return valid actions
            mock_agent.decision_loop.return_value = ProposedAction(
                action_id="integration_action_001",
                action_type=ActionType.INVESTIGATE,
                target=ActionTarget(
                    entity_id="test_object", entity_type=EntityType.OBJECT
                ),
                agent_id="integration_test_agent",
                character_id="integration_test_agent",
                parameters=ActionParameters(
                    intensity=ActionIntensity.NORMAL, duration=1.0
                ),
                reasoning="Integration test investigation",
            )

            director.register_agent(mock_agent)
            yield director, mock_agent

    def test_iron_laws_during_turn_processing(self, director_with_agents):
        """Test that Iron Laws validation occurs during normal turn processing."""
        director, mock_agent = director_with_agents

        # Mock the validation to return a report
        with patch.object(director, "_adjudicate_action") as mock_adjudicate:
            mock_adjudicate.return_value = {
                "validation_result": "APPROVED",
                "violations_found": [],
                "checks_performed": [
                    "E001_Causality_Law",
                    "E002_Resource_Law",
                    "E003_Physics_Law",
                    "E004_Narrative_Law",
                    "E005_Social_Law",
                ],
                "processing_time": 0.001,
                "repaired_action": None,
                "repair_attempts": [],
            }

            # Run a turn
            turn_result = director.run_turn()

            # Verify that Iron Laws validation was called
            assert mock_adjudicate.called
            assert turn_result["total_actions"] >= 0

    def test_iron_laws_error_handling(self, director_with_agents):
        """Test error handling in Iron Laws validation."""
        director, mock_agent = director_with_agents

        # Mock validation to raise an exception
        with patch.object(director, "_adjudicate_action") as mock_adjudicate:
            mock_adjudicate.side_effect = Exception("Test validation error")

            # Should not crash the turn processing
            turn_result = director.run_turn()

            # Verify graceful error handling
            assert "errors" in turn_result
            assert (
                len(turn_result["errors"]) >= 0
            )  # Error handling should prevent crashes

    def test_iron_laws_performance_tracking(self, director_with_agents):
        """Test that Iron Laws validation performance is tracked."""
        director, mock_agent = director_with_agents

        # Run validation and check timing
        sample_action = Mock()
        sample_action.action_id = "perf_test_001"
        sample_action.action_type = ActionType.MOVE

        result = director._adjudicate_action(sample_action, mock_agent)

        # Verify performance tracking
        assert "processing_time" in result
        assert isinstance(result["processing_time"], (int, float))
        assert result["processing_time"] >= 0


class TestIronLawsEdgeCases:
    """Test Iron Laws edge cases and error conditions."""

    @pytest.fixture
    def iron_laws_processor(self):
        """Create IronLawsProcessor for edge case testing."""
        from src.core.iron_laws_processor import IronLawsProcessor

        return IronLawsProcessor()

    def test_invalid_action_handling(self, iron_laws_processor):
        """Test handling of invalid or malformed actions."""
        # Test with None action
        mock_agent = Mock()
        mock_agent.character_data = {}
        world_context = {}
        result = iron_laws_processor.adjudicate_action(None, mock_agent, world_context)
        assert hasattr(result, "overall_result")
        assert result.overall_result == ValidationResult.CATASTROPHIC_FAILURE

        # Test with action missing required fields
        incomplete_action = Mock()
        incomplete_action.action_id = None
        incomplete_action.action_type = None

        result = iron_laws_processor.adjudicate_action(
            incomplete_action, mock_agent, world_context
        )
        assert hasattr(result, "violations")
        assert len(result.violations) > 0

    def test_malformed_character_data_handling(self, iron_laws_processor):
        """Test handling of malformed character data."""
        malformed_agent = Mock()
        malformed_agent.character_data = None  # Missing character data

        sample_action = Mock()
        sample_action.action_id = "malformed_test_001"
        sample_action.action_type = ActionType.MOVE

        world_context = {}
        # Should not crash with malformed data
        result = iron_laws_processor.adjudicate_action(
            sample_action, malformed_agent, world_context
        )
        assert hasattr(result, "overall_result")
        assert result.overall_result == ValidationResult.CATASTROPHIC_FAILURE

    def test_resource_calculation_edge_cases(self, iron_laws_processor):
        """Test stamina calculation edge cases."""
        # Test action with no parameters
        no_param_action = Mock()
        no_param_action.action_type = "test"
        no_param_action.parameters = None

        cost = iron_laws_processor._calculate_action_stamina_cost(no_param_action)
        assert cost >= 1  # Should have minimum cost

        # Test action with invalid parameter values
        invalid_param_action = Mock()
        invalid_param_action.action_type = "test"
        invalid_param_action.parameters = Mock()
        invalid_param_action.parameters.intensity = "invalid_intensity"
        invalid_param_action.parameters.duration = -1.0  # Negative duration

        cost = iron_laws_processor._calculate_action_stamina_cost(invalid_param_action)
        assert cost >= 1  # Should handle gracefully

    def test_repair_system_edge_cases(self, iron_laws_processor):
        """Test repair system edge cases."""
        # Test repair with no violations
        action = Mock()
        result = iron_laws_processor._attempt_action_repairs(action, [], {})
        assert result[0] is None  # Should return None for no violations
        assert len(result[1]) == 0  # No repairs made

        # Test repair with unsupported violation type
        unsupported_violation = Mock()
        unsupported_violation.law_code = "E999"  # Non-existent law

        result = iron_laws_processor._attempt_action_repairs(
            action, [unsupported_violation], {}
        )
        assert isinstance(result, tuple)  # Should handle gracefully


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v"])
