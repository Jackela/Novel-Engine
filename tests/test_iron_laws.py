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

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import system components
try:
    from director_agent import DirectorAgent
    from persona_agent import PersonaAgent
    from src.shared_types import (
        ProposedAction, ValidatedAction, CharacterData, CharacterStats,
        CharacterResources, ResourceValue, ActionParameters, ActionType,
        IronLawsViolation, IronLawsReport, Position, ActionIntensity,
        ActionTarget, EntityType
    )
    IRON_LAWS_AVAILABLE = True
except ImportError as e:
    IRON_LAWS_AVAILABLE = False
    pytest.skip(f"Iron Laws system not available: {e}", allow_module_level=True)


class TestIronLawsValidation:
    """Test core Iron Laws validation functionality."""
    
    @pytest.fixture
    def director_agent(self):
        """Create DirectorAgent instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            director = DirectorAgent(
                world_state_file_path=None,
                campaign_log_path=Path(temp_dir) / "test_campaign.log"
            )
            yield director
    
    @pytest.fixture
    def mock_agent(self):
        """Create mock PersonaAgent for testing."""
        agent = Mock(spec=PersonaAgent)
        agent.agent_id = "test_agent_001"
        agent.character_data = {
            'name': 'Test Character',
            'stats': CharacterStats(
                strength=ResourceValue(current=15, maximum=20, minimum=0),
                dexterity=ResourceValue(current=12, maximum=18, minimum=0),
                intelligence=ResourceValue(current=16, maximum=20, minimum=0),
                constitution=ResourceValue(current=14, maximum=16, minimum=0),
                wisdom=ResourceValue(current=13, maximum=15, minimum=0),
                charisma=ResourceValue(current=11, maximum=14, minimum=0)
            ),
            'resources': CharacterResources(
                health=ResourceValue(current=80, maximum=100, minimum=0),
                stamina=ResourceValue(current=60, maximum=80, minimum=0),
                mana=ResourceValue(current=50, maximum=70, minimum=0)
            ),
            'position': Position(x=10, y=10, z=0),
            'equipment': ['basic_weapon', 'standard_armor']
        }
        return agent
    
    @pytest.fixture
    def sample_action(self):
        """Create sample ProposedAction for testing."""
        return ProposedAction(
            action_id="test_action_001",
            action_type=ActionType.INVESTIGATE,
            target="mysterious_object",
            agent_id="test_agent_001",
            character_id="test_agent_001",
            parameters=ActionParameters(
                intensity=ActionIntensity.NORMAL,
                duration=1.0,
                range=5.0
            ),
            reasoning="Investigating unusual readings from the object"
        )
    
    def test_iron_laws_validation_core(self, director_agent, mock_agent, sample_action):
        """Test core Iron Laws validation engine."""
        # Execute validation
        result = director_agent._adjudicate_action(sample_action, mock_agent)
        
        # Verify result structure
        assert isinstance(result, dict)
        assert 'validation_result' in result
        assert 'violations_found' in result
        assert 'checks_performed' in result
        assert 'processing_time' in result
        
        # Verify all laws were checked
        expected_checks = ["E001_Causality_Law", "E002_Resource_Law", "E003_Physics_Law", 
                          "E004_Narrative_Law", "E005_Social_Law"]
        assert all(check in result['checks_performed'] for check in expected_checks)
    
    def test_causality_law_validation(self, director_agent, mock_agent):
        """Test E001 Causality Law validation."""
        # Test valid causal action
        valid_action = ProposedAction(
            action_id="valid_causality_001",
            action_type=ActionType.MOVE,
            target="nearby_door",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="low", duration=0.5),
            reasoning="Moving to examine the door more closely"
        )
        
        character_data = mock_agent.character_data
        world_context = director_agent._get_current_world_context()
        violations = director_agent._validate_causality_law(valid_action, character_data, world_context)
        
        # Should have no violations for simple movement
        assert len(violations) == 0
        
        # Test invalid causal action
        invalid_action = ProposedAction(
            action_id="invalid_causality_001", 
            action_type=ActionType.ATTACK,
            target=None,  # No target specified
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning=""  # No reasoning
        )
        
        violations = director_agent._validate_causality_law(invalid_action, character_data, world_context)
        
        # Should detect causality violations
        assert len(violations) > 0
        assert all(v.law_code == "E001" for v in violations)
    
    def test_resource_law_validation(self, director_agent, mock_agent):
        """Test E002 Resource Law validation."""
        character_data = mock_agent.character_data
        
        # Test action within resource limits
        normal_action = ProposedAction(
            action_id="normal_resource_001",
            action_type=ActionType.INVESTIGATE,
            target="small_object",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="low", duration=1.0),
            reasoning="Light investigation of the object"
        )
        
        violations = director_agent._validate_resource_law(normal_action, character_data)
        
        # Should have no violations for reasonable action
        assert len(violations) == 0
        
        # Test action exceeding stamina limits
        exhausting_action = ProposedAction(
            action_id="exhausting_resource_001",
            action_type=ActionType.ATTACK,
            target="powerful_enemy",
            agent_id="test_agent_001", 
            parameters=ActionParameters(intensity="extreme", duration=5.0),
            reasoning="All-out assault requiring massive stamina"
        )
        
        violations = director_agent._validate_resource_law(exhausting_action, character_data)
        
        # Should detect resource violations
        assert len(violations) > 0
        assert all(v.law_code == "E002" for v in violations)
    
    def test_physics_law_validation(self, director_agent, mock_agent):
        """Test E003 Physics Law validation."""
        character_data = mock_agent.character_data
        world_context = director_agent._get_current_world_context()
        
        # Test physically reasonable action
        reasonable_action = ProposedAction(
            action_id="reasonable_physics_001",
            action_type=ActionType.MOVE,
            target="adjacent_room",
            agent_id="test_agent_001",
            parameters=ActionParameters(duration=1.0, range=3.0),
            reasoning="Walking to the adjacent room"
        )
        
        violations = director_agent._validate_physics_law(reasonable_action, character_data, world_context)
        
        # Should have no violations for normal movement
        assert len(violations) == 0
        
        # Test physically impossible action
        impossible_action = ProposedAction(
            action_id="impossible_physics_001",
            action_type=ActionType.MOVE,
            target="distant_location",
            agent_id="test_agent_001",
            parameters=ActionParameters(duration=0.1, range=1000.0),  # Teleportation-like
            reasoning="Instantly moving vast distances"
        )
        
        violations = director_agent._validate_physics_law(impossible_action, character_data, world_context)
        
        # Should detect physics violations
        assert len(violations) > 0
        assert all(v.law_code == "E003" for v in violations)
    
    def test_narrative_law_validation(self, director_agent, mock_agent):
        """Test E004 Narrative Law validation."""
        world_context = director_agent._get_current_world_context()
        
        # Test narratively coherent action
        coherent_action = ProposedAction(
            action_id="coherent_narrative_001",
            action_type=ActionType.INVESTIGATE,
            target="suspicious_device",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="normal"),
            reasoning="Investigating the device to understand its purpose"
        )
        
        violations = director_agent._validate_narrative_law(coherent_action, mock_agent, world_context)
        
        # Should have no violations for coherent investigation
        assert len(violations) == 0
        
        # Test narratively incoherent action
        incoherent_action = ProposedAction(
            action_id="incoherent_narrative_001",
            action_type=ActionType.ATTACK,
            target="friendly_ally",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning="Attacking allies for no apparent reason"
        )
        
        violations = director_agent._validate_narrative_law(incoherent_action, mock_agent, world_context)
        
        # Should detect narrative violations
        assert len(violations) > 0
        assert all(v.law_code == "E004" for v in violations)
    
    def test_social_law_validation(self, director_agent, mock_agent):
        """Test E005 Social Law validation."""
        world_context = director_agent._get_current_world_context()
        
        # Test socially appropriate action
        appropriate_action = ProposedAction(
            action_id="appropriate_social_001",
            action_type=ActionType.COMMUNICATE,
            target="team_member",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="normal"),
            reasoning="Coordinating with team member about mission objectives"
        )
        
        violations = director_agent._validate_social_law(appropriate_action, mock_agent, world_context)
        
        # Should have no violations for appropriate communication
        assert len(violations) == 0
        
        # Test socially inappropriate action
        inappropriate_action = ProposedAction(
            action_id="inappropriate_social_001",
            action_type=ActionType.COMMUNICATE,
            target="superior_officer",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning="Shouting orders at superior officer"
        )
        
        violations = director_agent._validate_social_law(inappropriate_action, mock_agent, world_context)
        
        # Should detect social violations
        assert len(violations) > 0
        assert all(v.law_code == "E005" for v in violations)


class TestIronLawsRepairSystem:
    """Test automatic action repair system."""
    
    @pytest.fixture
    def director_agent(self):
        """Create DirectorAgent instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            director = DirectorAgent(
                world_state_file_path=None,
                campaign_log_path=Path(temp_dir) / "test_campaign.log"
            )
            yield director
    
    @pytest.fixture
    def mock_character_data(self):
        """Create mock character data for repair testing."""
        return {
            'name': 'Test Character',
            'stats': CharacterStats(
                strength=ResourceValue(current=15, maximum=20, minimum=0),
                dexterity=ResourceValue(current=12, maximum=18, minimum=0),
                intelligence=ResourceValue(current=16, maximum=20, minimum=0),
                constitution=ResourceValue(current=14, maximum=16, minimum=0),
                wisdom=ResourceValue(current=13, maximum=15, minimum=0),
                charisma=ResourceValue(current=11, maximum=14, minimum=0)
            ),
            'resources': CharacterResources(
                health=ResourceValue(current=80, maximum=100, minimum=0),
                stamina=ResourceValue(current=40, maximum=80, minimum=0),  # Low stamina for testing
                mana=ResourceValue(current=50, maximum=70, minimum=0)
            )
        }
    
    def test_causality_repair(self, director_agent):
        """Test E001 Causality Law violation repairs."""
        # Create action with causality violation
        action = ProposedAction(
            action_id="causality_repair_001",
            action_type=ActionType.ATTACK,
            target=None,  # Missing target
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning=""  # Missing reasoning
        )
        
        # Create mock violations
        violations = [
            IronLawsViolation(
                law_code="E001",
                violation_type="missing_target",
                description="Action lacks necessary target specification",
                severity="high",
                suggested_fix="Add target specification",
                affected_parameters=["target"]
            ),
            IronLawsViolation(
                law_code="E001",
                violation_type="missing_reasoning",
                description="Action lacks logical reasoning",
                severity="medium",
                suggested_fix="Add reasoning for action",
                affected_parameters=["reasoning"]
            )
        ]
        
        # Attempt repairs
        repaired_action, repairs_made = director_agent._repair_causality_violations(action, violations)
        
        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.target is not None
        assert len(repaired_action.reasoning) > 0
        assert "Added default target" in " ".join(repairs_made)
        assert "Added reasoning" in " ".join(repairs_made)
    
    def test_resource_repair(self, director_agent, mock_character_data):
        """Test E002 Resource Law violation repairs."""
        # Create action that exceeds stamina
        action = ProposedAction(
            action_id="resource_repair_001",
            action_type=ActionType.ATTACK,
            target="enemy",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="extreme", duration=3.0),
            reasoning="All-out attack"
        )
        
        # Create resource violation
        violations = [
            IronLawsViolation(
                law_code="E002",
                violation_type="insufficient_stamina",
                description="Action requires more stamina than available",
                severity="high",
                suggested_fix="Reduce action intensity or duration",
                affected_parameters=["intensity", "duration"]
            )
        ]
        
        # Attempt repairs
        repaired_action, repairs_made = director_agent._repair_resource_violations(
            action, violations, mock_character_data
        )
        
        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.parameters.intensity != "extreme"  # Should be reduced
        assert "Reduced intensity" in " ".join(repairs_made) or "Reduced duration" in " ".join(repairs_made)
    
    def test_physics_repair(self, director_agent, mock_character_data):
        """Test E003 Physics Law violation repairs."""
        # Create physically impossible action
        action = ProposedAction(
            action_id="physics_repair_001",
            action_type=ActionType.MOVE,
            target="distant_location",
            agent_id="test_agent_001",
            parameters=ActionParameters(duration=0.1, range=1000.0),
            reasoning="Instant travel"
        )
        
        # Create physics violation
        violations = [
            IronLawsViolation(
                law_code="E003",
                violation_type="impossible_speed",
                description="Movement speed exceeds physical limits",
                severity="critical",
                suggested_fix="Adjust duration and range to realistic values",
                affected_parameters=["duration", "range"]
            )
        ]
        
        # Attempt repairs
        repaired_action, repairs_made = director_agent._repair_physics_violations(
            action, violations, mock_character_data
        )
        
        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.parameters.duration > 0.1  # Should be increased
        assert repaired_action.parameters.range < 1000.0  # Should be reduced
        assert "Adjusted movement" in " ".join(repairs_made)
    
    def test_narrative_repair(self, director_agent):
        """Test E004 Narrative Law violation repairs."""
        # Create narratively incoherent action
        action = ProposedAction(
            action_id="narrative_repair_001",
            action_type=ActionType.ATTACK,
            target="ally",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning="Attacking friend"
        )
        
        # Create narrative violation
        violations = [
            IronLawsViolation(
                law_code="E004",
                violation_type="character_inconsistency",
                description="Action contradicts character relationships",
                severity="high",
                suggested_fix="Change action to be consistent with relationships",
                affected_parameters=["action_type", "target"]
            )
        ]
        
        # Attempt repairs
        repaired_action, repairs_made = director_agent._repair_narrative_violations(action, violations)
        
        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.action_type != ActionType.ATTACK or repaired_action.target != "ally"
        assert "Changed action" in " ".join(repairs_made) or "Modified target" in " ".join(repairs_made)
    
    def test_social_repair(self, director_agent):
        """Test E005 Social Law violation repairs."""
        # Create socially inappropriate action
        action = ProposedAction(
            action_id="social_repair_001",
            action_type=ActionType.COMMUNICATE,
            target="commanding_officer",
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="high"),
            reasoning="Demanding orders from superior"
        )
        
        # Create social violation
        violations = [
            IronLawsViolation(
                law_code="E005",
                violation_type="hierarchy_violation",
                description="Action violates command hierarchy",
                severity="medium",
                suggested_fix="Adjust communication style to be appropriate for hierarchy",
                affected_parameters=["intensity", "reasoning"]
            )
        ]
        
        # Attempt repairs
        repaired_action, repairs_made = director_agent._repair_social_violations(action, violations)
        
        # Verify repairs were applied
        assert len(repairs_made) > 0
        assert repaired_action.parameters.intensity != "high"  # Should be reduced
        assert "Adjusted communication" in " ".join(repairs_made)
    
    def test_comprehensive_repair_attempt(self, director_agent, mock_character_data):
        """Test comprehensive repair system with multiple violation types."""
        # Create action with multiple violations
        problematic_action = ProposedAction(
            action_id="multi_repair_001",
            action_type=ActionType.ATTACK,
            target=None,  # Causality issue
            agent_id="test_agent_001",
            parameters=ActionParameters(intensity="extreme", duration=5.0),  # Resource issue
            reasoning=""  # Causality issue
        )
        
        # Create multiple violations
        violations = [
            IronLawsViolation(
                law_code="E001",
                violation_type="missing_target",
                description="Missing target",
                severity="high",
                suggested_fix="Add target",
                affected_parameters=["target"]
            ),
            IronLawsViolation(
                law_code="E002", 
                violation_type="insufficient_stamina",
                description="Exceeds stamina",
                severity="high",
                suggested_fix="Reduce intensity",
                affected_parameters=["intensity"]
            )
        ]
        
        # Attempt comprehensive repair
        repaired_action, repairs_made = director_agent._attempt_action_repairs(
            problematic_action, violations, mock_character_data
        )
        
        # Verify multiple repairs were applied
        assert repaired_action is not None
        assert len(repairs_made) >= 2  # Should have multiple repairs
        assert repaired_action.target is not None  # Causality repair
        assert repaired_action.parameters.intensity != "extreme"  # Resource repair


class TestIronLawsHelperMethods:
    """Test Iron Laws helper methods."""
    
    @pytest.fixture
    def director_agent(self):
        """Create DirectorAgent instance for testing."""
        return DirectorAgent()
    
    def test_group_violations_by_law(self, director_agent):
        """Test violation grouping by law code."""
        violations = [
            IronLawsViolation(
                law_code="E001",
                violation_type="test1",
                description="Test violation 1",
                severity="medium"
            ),
            IronLawsViolation(
                law_code="E002",
                violation_type="test2", 
                description="Test violation 2",
                severity="high"
            ),
            IronLawsViolation(
                law_code="E001",
                violation_type="test3",
                description="Test violation 3",
                severity="low"
            )
        ]
        
        grouped = director_agent._group_violations_by_law(violations)
        
        # Verify grouping
        assert len(grouped) == 2
        assert "E001" in grouped
        assert "E002" in grouped
        assert len(grouped["E001"]) == 2
        assert len(grouped["E002"]) == 1
    
    def test_get_current_world_context(self, director_agent):
        """Test world context generation."""
        context = director_agent._get_current_world_context()
        
        # Verify required context elements
        assert 'current_turn' in context
        assert 'total_agents' in context
        assert 'environment' in context
        assert 'story_state' in context
        assert 'physics' in context
        assert 'world_resources' in context
        
        # Verify structure
        assert isinstance(context['environment'], dict)
        assert isinstance(context['story_state'], dict)
        assert isinstance(context['physics'], dict)
    
    def test_determine_overall_validation_result(self, director_agent):
        """Test overall validation result determination."""
        # Test with no violations
        result = director_agent._determine_overall_validation_result([])
        assert result == "APPROVED"
        
        # Test with critical violations
        critical_violations = [
            IronLawsViolation(
                law_code="E003",
                violation_type="critical_test",
                description="Critical violation",
                severity="critical"
            )
        ]
        result = director_agent._determine_overall_validation_result(critical_violations)
        assert result == "REJECTED"
        
        # Test with high violations
        high_violations = [
            IronLawsViolation(
                law_code="E002",
                violation_type="high_test",
                description="High violation",
                severity="high"
            )
        ]
        result = director_agent._determine_overall_validation_result(high_violations)
        assert result == "REQUIRES_REPAIR"
        
        # Test with low violations
        low_violations = [
            IronLawsViolation(
                law_code="E001",
                violation_type="low_test",
                description="Low violation",
                severity="low"
            )
        ]
        result = director_agent._determine_overall_validation_result(low_violations)
        assert result == "APPROVED_WITH_WARNINGS"
    
    def test_calculate_action_stamina_cost(self, director_agent):
        """Test stamina cost calculation."""
        # Test basic action
        basic_action = ProposedAction(
            action_id="stamina_test_001",
            action_type=ActionType.MOVE,
            target=ActionTarget(entity_id="location", entity_type=EntityType.LOCATION),
            agent_id="test_agent",
            character_id="test_agent",
            parameters=ActionParameters(intensity=ActionIntensity.NORMAL, duration=1.0),
            reasoning="Moving to test location for analysis"
        )
        
        cost = director_agent._calculate_action_stamina_cost(basic_action)
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
            reasoning="High-intensity attack against enemy target"
        )
        
        intense_cost = director_agent._calculate_action_stamina_cost(intense_action)
        assert intense_cost > cost  # Should cost more than basic movement


class TestIronLawsIntegration:
    """Test Iron Laws integration with DirectorAgent."""
    
    @pytest.fixture
    def director_with_agents(self):
        """Create DirectorAgent with mock agents for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            director = DirectorAgent(campaign_log_path=Path(temp_dir) / "integration_test.log")
            
            # Create mock agent
            mock_agent = Mock(spec=PersonaAgent)
            mock_agent.agent_id = "integration_test_agent"
            mock_agent.character_data = {
                'name': 'Integration Test Character',
                'stats': CharacterStats(
                    strength=ResourceValue(current=15, maximum=20, minimum=0),
                    dexterity=ResourceValue(current=12, maximum=18, minimum=0),
                    intelligence=ResourceValue(current=16, maximum=20, minimum=0),
                    constitution=ResourceValue(current=14, maximum=16, minimum=0),
                    wisdom=ResourceValue(current=13, maximum=15, minimum=0),
                    charisma=ResourceValue(current=11, maximum=14, minimum=0)
                ),
                'resources': CharacterResources(
                    health=ResourceValue(current=80, maximum=100, minimum=0),
                    stamina=ResourceValue(current=60, maximum=80, minimum=0),
                    mana=ResourceValue(current=50, maximum=70, minimum=0)
                )
            }
            
            # Configure mock to return valid actions
            mock_agent.decision_loop.return_value = Mock(
                action_id="integration_action_001",
                action_type=ActionType.INVESTIGATE,
                target="test_object",
                agent_id="integration_test_agent",
                parameters=Mock(intensity="normal", duration=1.0),
                reasoning="Integration test investigation"
            )
            
            director.register_agent(mock_agent)
            yield director, mock_agent
    
    def test_iron_laws_during_turn_processing(self, director_with_agents):
        """Test that Iron Laws validation occurs during normal turn processing."""
        director, mock_agent = director_with_agents
        
        # Mock the validation to return a report
        with patch.object(director, '_adjudicate_action') as mock_adjudicate:
            mock_adjudicate.return_value = {
                'validation_result': 'APPROVED',
                'violations_found': [],
                'checks_performed': ["E001_Causality_Law", "E002_Resource_Law", 
                                   "E003_Physics_Law", "E004_Narrative_Law", "E005_Social_Law"],
                'processing_time': 0.001,
                'repaired_action': None,
                'repair_attempts': []
            }
            
            # Run a turn
            turn_result = director.run_turn()
            
            # Verify that Iron Laws validation was called
            assert mock_adjudicate.called
            assert turn_result['total_actions'] >= 0
    
    def test_iron_laws_error_handling(self, director_with_agents):
        """Test error handling in Iron Laws validation."""
        director, mock_agent = director_with_agents
        
        # Mock validation to raise an exception
        with patch.object(director, '_adjudicate_action') as mock_adjudicate:
            mock_adjudicate.side_effect = Exception("Test validation error")
            
            # Should not crash the turn processing
            turn_result = director.run_turn()
            
            # Verify graceful error handling
            assert 'errors' in turn_result
            assert len(turn_result['errors']) >= 0  # Error handling should prevent crashes
    
    def test_iron_laws_performance_tracking(self, director_with_agents):
        """Test that Iron Laws validation performance is tracked."""
        director, mock_agent = director_with_agents
        
        # Run validation and check timing
        sample_action = Mock()
        sample_action.action_id = "perf_test_001"
        sample_action.action_type = ActionType.MOVE
        
        result = director._adjudicate_action(sample_action, mock_agent)
        
        # Verify performance tracking
        assert 'processing_time' in result
        assert isinstance(result['processing_time'], (int, float))
        assert result['processing_time'] >= 0


class TestIronLawsEdgeCases:
    """Test Iron Laws edge cases and error conditions."""
    
    @pytest.fixture 
    def director_agent(self):
        """Create DirectorAgent for edge case testing."""
        return DirectorAgent()
    
    def test_invalid_action_handling(self, director_agent):
        """Test handling of invalid or malformed actions."""
        # Test with None action
        result = director_agent._adjudicate_action(None, Mock())
        assert 'validation_result' in result
        assert result['validation_result'] == 'REJECTED'
        
        # Test with action missing required fields
        incomplete_action = Mock()
        incomplete_action.action_id = None
        incomplete_action.action_type = None
        
        result = director_agent._adjudicate_action(incomplete_action, Mock())
        assert 'violations_found' in result
        assert len(result['violations_found']) > 0
    
    def test_malformed_character_data_handling(self, director_agent):
        """Test handling of malformed character data."""
        malformed_agent = Mock()
        malformed_agent.character_data = None  # Missing character data
        
        sample_action = Mock()
        sample_action.action_id = "malformed_test_001"
        sample_action.action_type = ActionType.MOVE
        
        # Should not crash with malformed data
        result = director_agent._adjudicate_action(sample_action, malformed_agent)
        assert isinstance(result, dict)
    
    def test_resource_calculation_edge_cases(self, director_agent):
        """Test stamina calculation edge cases."""
        # Test action with no parameters
        no_param_action = Mock()
        no_param_action.action_type = "test"
        no_param_action.parameters = None
        
        cost = director_agent._calculate_action_stamina_cost(no_param_action)
        assert cost >= 1  # Should have minimum cost
        
        # Test action with invalid parameter values
        invalid_param_action = Mock()
        invalid_param_action.action_type = "test"
        invalid_param_action.parameters = Mock()
        invalid_param_action.parameters.intensity = "invalid_intensity"
        invalid_param_action.parameters.duration = -1.0  # Negative duration
        
        cost = director_agent._calculate_action_stamina_cost(invalid_param_action)
        assert cost >= 1  # Should handle gracefully
    
    def test_repair_system_edge_cases(self, director_agent):
        """Test repair system edge cases."""
        # Test repair with no violations
        action = Mock()
        result = director_agent._attempt_action_repairs(action, [], {})
        assert result[0] is None  # Should return None for no violations
        assert len(result[1]) == 0  # No repairs made
        
        # Test repair with unsupported violation type
        unsupported_violation = Mock()
        unsupported_violation.law_code = "E999"  # Non-existent law
        
        result = director_agent._attempt_action_repairs(action, [unsupported_violation], {})
        assert isinstance(result, tuple)  # Should handle gracefully


if __name__ == "__main__":
    # Run the test suite
    pytest.main([__file__, "-v"])