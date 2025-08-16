#!/usr/bin/env python3
"""
DirectorAgent Unit Tests
========================

Comprehensive pytest test suite for the DirectorAgent class using pytest.
Tests cover all core functionality including agent registration, campaign logging,
turn management, and integration with PersonaAgent instances.

This test file includes:
- Mock PersonaAgent implementation for isolated testing
- DirectorAgent initialization and configuration tests
- Agent registration and validation tests
- Campaign logging functionality tests
- Core turn processing and coordination tests
- Error handling and edge case scenarios
- Integration tests with actual PersonaAgent instances

Architecture Reference: Architecture_Blueprint.md Section 2.1 DirectorAgent
Development Phase: Phase 2 - DirectorAgent MVP (Weeks 6-8)
"""

import pytest
import os
import tempfile
import shutil
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Import the PersonaAgent-related classes that DirectorAgent will use
from src.persona_agent import PersonaAgent, ThreatLevel
from shared_types import CharacterAction, ActionPriority
# Import the actual DirectorAgent implementation
from director_agent import DirectorAgent

# Global fixture to mock Gemini API for all tests in this module
@pytest.fixture(autouse=True)
def mock_gemini_api_global():
    """Automatically mock Gemini API for all director agent tests."""
    with patch('persona_agent._make_gemini_api_request') as mock_api:
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Director agent test mock response"
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_director'}):
            yield mock_api


# Mock PersonaAgent class for testing DirectorAgent functionality
class MockPersonaAgent(PersonaAgent):
    """
    Simple mock PersonaAgent for testing DirectorAgent functionality.
    
    This mock provides a configurable agent that can simulate different
    behaviors and return values for testing various DirectorAgent scenarios.
    """
    
    def __init__(self, agent_id: str, name: str = "Test Agent", faction: str = "Test Faction"):
        """
        Initialize a mock PersonaAgent with basic properties.
        
        Args:
            agent_id: Unique identifier for this agent
            name: Character name for logging purposes
            faction: Character's faction affiliation
        """
        # Create a minimal character sheet content for the parent class
        import tempfile
        import os
        
        # Create temporary character sheet
        character_sheet_content = f"""# Character Sheet: {name}

## Core Identity
- **Faction**: {faction}
- **Rank/Role**: Test Agent
- **Age**: 25
- **Origin**: Test World

## Psychological Profile

### Personality Traits
- **Dutiful**: Follows orders without question

### Mental State
- **Alert**: Ready for action

## Capabilities
- **Test Skills**: Basic testing capabilities
"""
        
        # Create temporary directory for character files
        temp_dir = tempfile.mkdtemp()
        character_file_path = os.path.join(temp_dir, f"{name.lower().replace(' ', '_')}.md")
        
        # Write character sheet to file in temp directory
        with open(character_file_path, 'w', encoding='utf-8') as f:
            f.write(character_sheet_content)
        
        try:
            # Initialize parent PersonaAgent with temporary directory
            super().__init__(temp_dir, agent_id)
        finally:
            # Clean up temporary directory and files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Override with mock-specific properties
        self.name = name
        self.faction = faction
        
        # Configurable return values for testing
        self.decision_loop_return = "action:do_nothing"
        self.should_raise_exception = False
        self.exception_to_raise = Exception("Mock agent error")
        
        # Track method calls for testing
        self.decision_loop_calls = []
        self.update_memory_calls = []
        
        # Update character data to match mock values
        self.character_data.update({
            'name': self.name,
            'faction': self.faction
        })
        
        self.subjective_worldview.update({
            'primary_faction': self.faction,
            'current_goals': []
        })
    
    def decision_loop(self, world_state_update: Dict[str, Any]) -> Optional[CharacterAction]:
        """
        Mock decision loop that returns configurable actions.
        
        Args:
            world_state_update: World state information (logged but not used)
            
        Returns:
            CharacterAction or None based on configuration
        """
        self.decision_loop_calls.append(world_state_update)
        
        if self.should_raise_exception:
            raise self.exception_to_raise
        
        # Return different actions based on configuration
        if self.decision_loop_return == "action:do_nothing":
            return None
        elif self.decision_loop_return == "action:observe":
            return CharacterAction(
                action_type="observe",
                reasoning=f"{self.name} observes the situation carefully",
                priority=ActionPriority.NORMAL
            )
        elif self.decision_loop_return == "action:attack":
            return CharacterAction(
                action_type="attack",
                target="enemy_unit",
                reasoning=f"{self.name} attacks the enemy",
                priority=ActionPriority.HIGH
            )
        else:
            return None
    
    def update_memory(self, new_log: Dict[str, Any]) -> None:
        """Mock memory update method."""
        self.update_memory_calls.append(new_log)
    
    def get_character_state(self) -> Dict[str, Any]:
        """Mock character state retrieval."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'faction': self.faction,
            'location': self.current_location,
            'status': self.current_status,
            'morale': self.morale_level
        }
    
    def configure_return_value(self, return_value: str):
        """Configure what the decision_loop method should return."""
        self.decision_loop_return = return_value
    
    def configure_exception(self, should_raise: bool, exception: Exception = None):
        """Configure whether decision_loop should raise an exception."""
        self.should_raise_exception = should_raise
        if exception:
            self.exception_to_raise = exception


# Mock DirectorAgent implementation has been removed - now using real DirectorAgent from director_agent.py


# Test fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_agent():
    """Create a mock PersonaAgent for testing."""
    return MockPersonaAgent("test_agent_001", "Test Character", "Imperial Guard")


@pytest.fixture
def multiple_mock_agents():
    """Create multiple mock PersonaAgents for testing."""
    return [
        MockPersonaAgent("agent_001", "Brother Marcus", "Space Marines"),
        MockPersonaAgent("agent_002", "Commissar Vex", "Imperial Guard"),
        MockPersonaAgent("agent_003", "Tech-Adept Kron", "Adeptus Mechanicus")
    ]


@pytest.fixture
def director_agent():
    """Create a DirectorAgent instance for testing."""
    return DirectorAgent()


@pytest.fixture
def director_with_worldstate(temp_dir):
    """Create a DirectorAgent with a world state file."""
    world_state_file = os.path.join(temp_dir, "world_state.json")
    
    # Create test world state file
    test_world_state = {
        "locations": {
            "hive_city_alpha": {
                "threat_level": "moderate",
                "population": 1000000,
                "faction_control": "imperium"
            }
        },
        "global_events": [
            {
                "id": "event_001",
                "type": "ork_raid",
                "description": "Ork raiders detected in outer sectors"
            }
        ]
    }
    
    with open(world_state_file, 'w') as f:
        json.dump(test_world_state, f)
    
    return DirectorAgent(world_state_file)


class TestDirectorAgentInitialization:
    """Test DirectorAgent initialization and configuration."""
    
    def test_initialization_without_world_state(self):
        """Test DirectorAgent can be initialized without world state file."""
        director = DirectorAgent()
        
        assert director.world_state_file_path is None
        assert director.registered_agents == []
        assert director.campaign_log_path == "campaign_log.md"
        assert director.current_turn_number == 0
        assert isinstance(director.world_state_data, dict)
        assert 'factions' in director.world_state_data  # Should have default world state
    
    def test_initialization_with_world_state_file(self, director_with_worldstate):
        """Test DirectorAgent initialization with world state file."""
        director = director_with_worldstate
        
        assert director.world_state_file_path is not None
        assert director.registered_agents == []
        assert "locations" in director.world_state_data
        assert "hive_city_alpha" in director.world_state_data["locations"]
    
    def test_initialization_with_nonexistent_world_state(self, temp_dir):
        """Test initialization with non-existent world state file."""
        nonexistent_file = os.path.join(temp_dir, "nonexistent.json")
        director = DirectorAgent(nonexistent_file)
        
        assert director.world_state_file_path == nonexistent_file
        assert isinstance(director.world_state_data, dict)
        assert 'factions' in director.world_state_data  # Should fall back to default world state
    
    def test_agents_list_empty_on_initialization(self, director_agent):
        """Test that agents list is empty on initialization."""
        assert len(director_agent.registered_agents) == 0
        assert isinstance(director_agent.registered_agents, list)
    
    def test_campaign_log_file_path_set_correctly(self, director_agent):
        """Test that campaign log file path is set correctly."""
        assert director_agent.campaign_log_path == "campaign_log.md"


class TestAgentRegistration:
    """Test agent registration functionality."""
    
    def test_register_single_agent(self, director_agent, mock_agent):
        """Test registering a single mock agent."""
        result = director_agent.register_agent(mock_agent)
        
        assert result is True
        assert len(director_agent.registered_agents) == 1
        assert director_agent.registered_agents[0] == mock_agent
    
    def test_register_multiple_agents(self, director_agent, multiple_mock_agents):
        """Test registering multiple agents."""
        for agent in multiple_mock_agents:
            result = director_agent.register_agent(agent)
            assert result is True
        
        assert len(director_agent.registered_agents) == 3
        agent_ids = [agent.agent_id for agent in director_agent.registered_agents]
        assert "agent_001" in agent_ids
        assert "agent_002" in agent_ids
        assert "agent_003" in agent_ids
    
    def test_register_duplicate_agent_id(self, director_agent, mock_agent):
        """Test that duplicate agent IDs are rejected."""
        # Register first agent
        result1 = director_agent.register_agent(mock_agent)
        assert result1 is True
        
        # Try to register agent with same ID
        duplicate_agent = MockPersonaAgent("test_agent_001", "Duplicate", "Chaos")
        result2 = director_agent.register_agent(duplicate_agent)
        
        assert result2 is False
        assert len(director_agent.registered_agents) == 1
    
    def test_register_invalid_agent_object(self, director_agent):
        """Test error handling for invalid agent objects."""
        # Test with object that has agent_id but decision_loop is not a method
        class InvalidAgent:
            def __init__(self):
                self.agent_id = "invalid_001"
                self.decision_loop = "not_a_method"  # String instead of method
        
        invalid_agent = InvalidAgent()
        result = director_agent.register_agent(invalid_agent)
        assert result is False
        assert len(director_agent.registered_agents) == 0
    
    def test_register_agent_without_agent_id(self, director_agent):
        """Test registration of agent without agent_id attribute."""
        class InvalidAgent:
            def __init__(self):
                # Missing agent_id attribute
                pass
            
            def decision_loop(self, world_state_update):
                return None
        
        invalid_agent = InvalidAgent()
        result = director_agent.register_agent(invalid_agent)
        assert result is False
        assert len(director_agent.registered_agents) == 0


class TestCampaignLogging:
    """Test campaign logging functionality."""
    
    def test_log_event_creates_campaign_log_file(self, temp_dir):
        """Test that DirectorAgent creates campaign_log.md during initialization."""
        # Create a fresh DirectorAgent in temp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            director = DirectorAgent()
            
            # Log an event to the initialized campaign log
            director.log_event("Test event occurred")
            
            # Check that file was created
            campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
            assert os.path.exists(campaign_log_path)
            
            # Check file contents
            with open(campaign_log_path, 'r') as f:
                content = f.read()
                assert "# Campaign Log" in content
                assert "Test event occurred" in content
        finally:
            os.chdir(original_cwd)
    
    def test_log_event_appends_to_existing_file(self, director_agent, temp_dir):
        """Test that events are appended correctly to existing log file."""
        # Set up temp log file
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Log first event
        director_agent.log_event("First event")
        
        # Log second event
        director_agent.log_event("Second event")
        
        # Check that both events are in the file
        with open(director_agent.campaign_log_path, 'r') as f:
            content = f.read()
            assert "First event" in content
            assert "Second event" in content
            assert "First event" in content and "Second event" in content  # Two test events
    
    def test_log_event_with_timestamps(self, director_agent, temp_dir):
        """Test that log events include timestamps."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        director_agent.log_event("Timestamped event")
        
        with open(director_agent.campaign_log_path, 'r') as f:
            content = f.read()
            # Check for timestamp pattern (basic check)
            assert "**" in content  # Timestamp should be in bold
            assert "Timestamped event" in content
            assert "Timestamped event" in content
    
    def test_multiple_event_logging(self, director_agent, temp_dir):
        """Test logging multiple events with different types."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        events = [
            ("Battle begins in sector 7", "combat"),
            ("Diplomatic contact established", "diplomacy"),
            ("Supply cache discovered", "discovery")
        ]
        
        for description, event_type in events:
            director_agent.log_event(description)
        
        with open(director_agent.campaign_log_path, 'r') as f:
            content = f.read()
            assert "Battle begins in sector 7" in content
            assert "Diplomatic contact established" in content
            assert "Supply cache discovered" in content
    
    def test_log_event_file_error_handling(self, director_agent):
        """Test handling of file system errors during logging."""
        # Set an invalid file path (directory that doesn't exist)
        director_agent.campaign_log_path = "/nonexistent/directory/campaign_log.md"
        
        # This should not raise an exception, but should handle the error gracefully
        try:
            director_agent.log_event("Test event")
            # If we get here, the method handled the error gracefully
            assert True
        except Exception:
            # If an exception is raised, it's a test failure
            pytest.fail("log_event should handle file errors gracefully")


class TestCoreRunTurn:
    """Test the core run_turn functionality."""
    
    def test_run_turn_with_two_agents(self, director_agent, temp_dir):
        """Test run_turn with two mock agents and verify campaign log entries."""
        # Set up temp log file
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create and register two mock agents
        agent1 = MockPersonaAgent("agent_001", "Agent One", "Imperial Guard")
        agent2 = MockPersonaAgent("agent_002", "Agent Two", "Space Marines")
        
        agent1.configure_return_value("action:observe")
        agent2.configure_return_value("action:attack")
        
        director_agent.register_agent(agent1)
        director_agent.register_agent(agent2)
        
        # Run one turn
        results = director_agent.run_turn()
        
        # Verify results
        assert results['turn_number'] == 1
        assert len(results['participating_agents']) == 2
        assert results['total_actions'] == 2
        assert len(results['errors']) == 0
        
        # Verify campaign log contains action entries
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "Agent One (agent_001) decided to observe" in log_content
            assert "Agent Two (agent_002) decided to attack" in log_content
            assert "TURN 1 BEGINS" in log_content
            assert "TURN 1 COMPLETED" in log_content
    
    def test_run_turn_agents_decision_loop_called(self, director_agent, temp_dir):
        """Test that both agents' decision_loop methods are called."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create mock agents
        agent1 = MockPersonaAgent("agent_001", "Test Agent 1", "Faction A")
        agent2 = MockPersonaAgent("agent_002", "Test Agent 2", "Faction B")
        
        director_agent.register_agent(agent1)
        director_agent.register_agent(agent2)
        
        # Run turn
        director_agent.run_turn()
        
        # Verify decision_loop was called on both agents
        assert len(agent1.decision_loop_calls) == 1
        assert len(agent2.decision_loop_calls) == 1
        
        # Verify world state update was passed
        world_update = agent1.decision_loop_calls[0]
        assert 'turn_number' in world_update
        assert world_update['turn_number'] == 1
    
    def test_run_turn_log_format_and_content(self, director_agent, temp_dir):
        """Test that campaign log format and content are correct."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create agent with specific action
        agent = MockPersonaAgent("agent_001", "Test Hero", "Imperial Guard")
        agent.configure_return_value("action:observe")
        director_agent.register_agent(agent)
        
        # Run turn
        director_agent.run_turn()
        
        # Read and verify log format
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            
            # Check for required elements
            assert "# Campaign Log" in log_content
            assert "TURN 1 BEGINS" in log_content
            assert "Test Hero" in log_content  # Character name should appear
            assert "TURN 1 COMPLETED" in log_content
            assert "Test Hero (agent_001)" in log_content
            assert "observes the situation" in log_content
    
    def test_run_turn_with_no_registered_agents(self, director_agent, temp_dir):
        """Test run_turn with no registered agents."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Run turn with no agents
        results = director_agent.run_turn()
        
        # Verify results
        assert results['turn_number'] == 1
        assert len(results['participating_agents']) == 0
        assert results['total_actions'] == 0
        assert len(results['errors']) == 0
        
        # Verify basic turn logging still occurs
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "TURN 1 BEGINS" in log_content
            assert "TURN 1 COMPLETED" in log_content
    
    def test_run_turn_with_agent_exception(self, director_agent, temp_dir):
        """Test run_turn when an agent raises an exception."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create agents, one that raises exception
        good_agent = MockPersonaAgent("good_agent", "Good Agent", "Imperial")
        bad_agent = MockPersonaAgent("bad_agent", "Bad Agent", "Chaos")
        
        good_agent.configure_return_value("action:observe")
        bad_agent.configure_exception(True, Exception("Agent malfunction"))
        
        director_agent.register_agent(good_agent)
        director_agent.register_agent(bad_agent)
        
        # Run turn
        results = director_agent.run_turn()
        
        # Verify results handle error gracefully
        assert results['turn_number'] == 1
        assert len(results['participating_agents']) == 1  # Only good agent processed
        assert results['total_actions'] == 1     # Only good agent acted
        assert len(results['errors']) == 1
        assert results['errors'][0]['error_message'] == "Agent malfunction"
        assert results['errors'][0]['agent_id'] == "bad_agent"
        
        # Verify error logged
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "**ERROR:**" in log_content
            assert "Agent malfunction" in log_content
            assert "Good Agent (good_agent) decided to observe" in log_content


class TestAdvancedScenarios:
    """Test advanced scenarios and edge cases."""
    
    def test_multiple_turns_and_log_accumulation(self, director_agent, temp_dir):
        """Test multiple turns and verify log accumulation."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        agent = MockPersonaAgent("agent_001", "Persistent Agent", "Imperial")
        agent.configure_return_value("action:observe")
        director_agent.register_agent(agent)
        
        # Run multiple turns
        for i in range(3):
            results = director_agent.run_turn()
            assert results['turn_number'] == i + 1
        
        # Verify log contains all turns
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "TURN 1 BEGINS" in log_content
            assert "TURN 2 BEGINS" in log_content
            assert "TURN 3 BEGINS" in log_content
            # Agent name appears 4 times (once for registration + once per turn)
            assert log_content.count("Persistent Agent (agent_001)") == 4
    
    def test_agent_registration_validation_edge_cases(self, director_agent):
        """Test edge cases in agent registration validation."""
        # Test with None
        result = director_agent.register_agent(None)
        assert result is False
        
        # Test with empty object
        empty_obj = object()
        result = director_agent.register_agent(empty_obj)
        assert result is False
        
        # Test with object that has agent_id but no decision_loop method
        class PartialAgent:
            def __init__(self):
                self.agent_id = "partial_001"
                # No decision_loop method defined
        
        partial_obj = PartialAgent()
        result = director_agent.register_agent(partial_obj)
        assert result is False
        
        # Test with object that has decision_loop but it's not callable
        class PartialAgent2:
            def __init__(self):
                self.agent_id = "partial_002"
                self.decision_loop = "not_callable"  # String, not function
        
        partial_obj2 = PartialAgent2()
        result = director_agent.register_agent(partial_obj2)
        assert result is False
    
    def test_campaign_log_permissions_error_handling(self, director_agent):
        """Test handling of campaign log file permissions issues."""
        # Set campaign log to a read-only location (this is OS-dependent)
        # For now, we'll simulate by setting to a location that would cause issues
        director_agent.campaign_log_file = "/root/readonly/campaign_log.md"
        
        # This should not crash the application
        try:
            director_agent.log_event("Test event")
            # If we get here, the method handled the error gracefully
        except PermissionError:
            # If this specific error is raised, that's also acceptable
            pass
        except Exception as e:
            # Other exceptions should not occur
            pytest.fail(f"Unexpected exception: {e}")
    
    def test_run_turn_with_mixed_agent_behaviors(self, director_agent, temp_dir):
        """Test run_turn with agents having different behaviors."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create agents with different behaviors
        observer = MockPersonaAgent("observer", "Observer", "Imperial")
        attacker = MockPersonaAgent("attacker", "Attacker", "Space Marines")
        waiter = MockPersonaAgent("waiter", "Waiter", "Tau")
        
        observer.configure_return_value("action:observe")
        attacker.configure_return_value("action:attack")
        waiter.configure_return_value("action:do_nothing")
        
        for agent in [observer, attacker, waiter]:
            director_agent.register_agent(agent)
        
        # Run turn
        results = director_agent.run_turn()
        
        # Verify results
        assert len(results['participating_agents']) == 3
        assert results['total_actions'] == 2  # Observer and Attacker act, Waiter does nothing
        
        # Verify log content
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "Observer (observer) decided to observe" in log_content
            assert "Attacker (attacker) decided to attack" in log_content
            assert "Waiter (waiter) chose to wait and observe" in log_content


class TestIntegrationWithPersonaAgent:
    """Test integration with actual PersonaAgent instances."""
    
    def test_integration_with_real_persona_agent(self, director_agent, temp_dir):
        """Test DirectorAgent integration with actual PersonaAgent instances."""
        # Create a character directory structure for testing
        character_dir_path = os.path.join(temp_dir, "test_character")
        os.makedirs(character_dir_path, exist_ok=True)
        
        # Create the character sheet file in the directory
        character_sheet_path = os.path.join(character_dir_path, "test_character.md")
        
        # Create a minimal character sheet for testing
        character_sheet_content = """# Character Sheet: Test Integration Character

## Core Identity
- **Faction**: Imperial Guard
- **Rank/Role**: Guardsman
- **Age**: 25
- **Origin**: Cadia

## Psychological Profile

### Personality Traits
- **Loyal**: Unwavering loyalty to the Emperor
- **Disciplined**: Follows orders without question
- **Courageous**: Faces danger with determination

### Mental State
- **Battle-Ready**: Prepared for combat at all times
- **Alert**: Constantly scanning for threats

## Knowledge Domains
- **Military Tactics**: Basic infantry tactics and procedures
- **Imperial Doctrine**: Knowledge of Imperial faith and customs

## Social Network
- **Commissar**: Respectful fear and loyalty
- **Squad Members**: Brotherhood and mutual trust

## Capabilities
- **Combat Skills**: Las-rifle proficiency, close combat training
- **Survival Skills**: Field survival and basic medical aid

## Behavioral Configuration

### Decision Making Weights
- **Self-Preservation**: 6
- **Faction Loyalty**: 9
- **Mission Success**: 8
- **Personal Relationships**: 7

### Response Patterns
- **Under Fire**: Seek cover and return fire
- **Orders Received**: Acknowledge and execute immediately
- **Threat Detected**: Alert others and prepare for action
"""
        
        with open(character_sheet_path, 'w') as f:
            f.write(character_sheet_content)
        
        # Create memory.log and stats.yaml files
        memory_log_path = os.path.join(character_dir_path, "memory.log")
        with open(memory_log_path, 'w') as f:
            f.write("[2025-07-27 20:00:00] Test agent initialized for integration test\n")
        
        stats_yaml_path = os.path.join(character_dir_path, "stats.yaml")
        with open(stats_yaml_path, 'w') as f:
            f.write("""character_name: "Test Integration Character"
faction: "Imperial Guard"
health: 100
morale: 85
""")
        
        # Set up campaign log
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create actual PersonaAgent using the character directory
        real_agent = PersonaAgent(character_dir_path, "integration_test_agent")
        
        # Register with DirectorAgent
        success = director_agent.register_agent(real_agent)
        assert success is True
        
        # Run a turn
        results = director_agent.run_turn()
        
        # Verify basic functionality
        assert len(results['participating_agents']) == 1
        assert len(results['errors']) == 0
        
        # Verify log was created and contains agent information
        assert os.path.exists(director_agent.campaign_log_path)
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            assert "integration_test_agent" in log_content
    
    def test_communication_between_components(self, director_agent, temp_dir):
        """Test communication between DirectorAgent and PersonaAgent works correctly."""
        # This is a placeholder for more complex integration tests
        # that would verify proper data flow between components
        
        # Use MockPersonaAgent which properly inherits from PersonaAgent
        mock_persona_like = MockPersonaAgent("persona_like_001", "Persona-Like Agent", "Test Faction")
        mock_persona_like.configure_return_value("action:do_nothing")
        
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Register and run
        success = director_agent.register_agent(mock_persona_like)
        assert success is True
        
        results = director_agent.run_turn()
        assert len(results['participating_agents']) == 1
        
        # Verify decision_loop was called with proper world state update
        assert len(mock_persona_like.decision_loop_calls) == 1
        call_args = mock_persona_like.decision_loop_calls[0]
        assert 'turn_number' in call_args
        assert 'world_state' in call_args
    
    def test_complete_simulation_cycle(self, director_agent, temp_dir):
        """Test a complete simulation cycle with multiple agents and turns."""
        director_agent.campaign_log_path = os.path.join(temp_dir, "campaign_log.md")
        
        # Create a small squad of mock agents
        squad = [
            MockPersonaAgent("squad_leader", "Sergeant Rex", "Imperial Guard"),
            MockPersonaAgent("heavy_weapons", "Gunner Kahl", "Imperial Guard"),
            MockPersonaAgent("medic", "Doc Stim", "Imperial Guard")
        ]
        
        # Configure different behaviors
        squad[0].configure_return_value("action:observe")  # Leader observes
        squad[1].configure_return_value("action:attack")   # Gunner attacks
        squad[2].configure_return_value("action:do_nothing")  # Medic waits
        
        # Register all agents
        for agent in squad:
            success = director_agent.register_agent(agent)
            assert success is True
        
        # Run simulation for several turns
        turn_results = []
        for turn in range(3):
            results = director_agent.run_turn()
            turn_results.append(results)
        
        # Verify overall simulation results
        assert len(turn_results) == 3
        for i, results in enumerate(turn_results):
            assert results['turn_number'] == i + 1
            assert len(results['participating_agents']) == 3
            assert results['total_actions'] == 2  # Leader and Gunner act each turn
        
        # Verify complete campaign log
        with open(director_agent.campaign_log_path, 'r') as f:
            log_content = f.read()
            
            # Check that all turns are logged
            for i in range(1, 4):
                assert f"TURN {i} BEGINS" in log_content
                assert f"TURN {i} COMPLETED" in log_content
            
            # Check that all agents appear in logs
            assert "Sergeant Rex" in log_content
            assert "Gunner Kahl" in log_content
            assert "Doc Stim" in log_content
            
            # Verify action patterns - check agent ID appearances (registration + 3 turns each)
            assert log_content.count("squad_leader") == 4   # Leader ID appears once for registration + once per turn
            assert log_content.count("heavy_weapons") == 4  # Gunner ID appears once for registration + once per turn  
            assert log_content.count("medic") == 4          # Medic ID appears once for registration + once per turn
            assert log_content.count("decided to observe") == 3     # Leader's specific observe actions (3 turns)
            assert log_content.count("decided to attack") == 3       # Gunner's attack actions (3 turns)
            assert log_content.count("chose to wait and observe") == 3  # Medic's wait actions (3 turns)


# Additional test utilities and helpers
class TestTestUtilities:
    """Test the test utilities and mock classes."""
    
    def test_mock_persona_agent_configuration(self):
        """Test that MockPersonaAgent can be configured correctly."""
        mock = MockPersonaAgent("test_id", "Test Name", "Test Faction")
        
        # Test initial state
        assert mock.agent_id == "test_id"
        assert mock.name == "Test Name"
        assert mock.faction == "Test Faction"
        assert mock.decision_loop_return == "action:do_nothing"
        assert mock.should_raise_exception is False
        
        # Test configuration methods
        mock.configure_return_value("action:attack")
        assert mock.decision_loop_return == "action:attack"
        
        mock.configure_exception(True, ValueError("Test error"))
        assert mock.should_raise_exception is True
        assert isinstance(mock.exception_to_raise, ValueError)
    
    def test_mock_persona_agent_decision_loop_tracking(self):
        """Test that MockPersonaAgent tracks decision_loop calls."""
        mock = MockPersonaAgent("tracker", "Tracker", "Test")
        
        # Initially no calls
        assert len(mock.decision_loop_calls) == 0
        
        # Make some calls
        world_update1 = {"turn": 1}
        world_update2 = {"turn": 2}
        
        mock.decision_loop(world_update1)
        mock.decision_loop(world_update2)
        
        # Verify calls were tracked
        assert len(mock.decision_loop_calls) == 2
        assert mock.decision_loop_calls[0] == world_update1
        assert mock.decision_loop_calls[1] == world_update2


# Test runner configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])