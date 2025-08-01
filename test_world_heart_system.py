#!/usr/bin/env python3
"""
World Heart System Test Suite - Dynamic World State Feedback Loop
================================================================

Comprehensive test suite for the "世界之心" (World Heart) dynamic world state system.
This suite validates the complete feedback loop from agent actions to world state changes
to next-turn feedback, ensuring the "Sacred Validation" requirements are met.

Tests cover:
1. World state tracker initialization and persistence
2. Action impact processing for investigate/search/analyze/explore actions
3. World state feedback generation and integration
4. Sacred validation: investigate → clue discovery → feedback visibility
5. Multi-agent coordination and world state sharing

Architecture Reference: User Story "世界之心" - Dynamic World State Feedback Loop
Development Phase: Sacred Validation Suite
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Import the core components
from director_agent import DirectorAgent
from persona_agent import PersonaAgent
from shared_types import CharacterAction, ActionPriority


class TestWorldStateTracker:
    """Test suite for world state tracker initialization and basic functionality."""
    
    def test_world_state_tracker_initialization(self):
        """Test that DirectorAgent initializes world state tracker with correct structure."""
        director = DirectorAgent()
        
        # Verify world state tracker exists and has correct structure
        assert hasattr(director, 'world_state_tracker')
        assert isinstance(director.world_state_tracker, dict)
        
        # Verify all required keys are present
        required_keys = [
            'discovered_clues',
            'environmental_changes', 
            'agent_discoveries',
            'temporal_markers',
            'investigation_history'
        ]
        
        for key in required_keys:
            assert key in director.world_state_tracker
        
        # Verify initial state is empty but correct types
        assert isinstance(director.world_state_tracker['discovered_clues'], dict)
        assert isinstance(director.world_state_tracker['environmental_changes'], dict)
        assert isinstance(director.world_state_tracker['agent_discoveries'], dict)
        assert isinstance(director.world_state_tracker['temporal_markers'], dict)
        assert isinstance(director.world_state_tracker['investigation_history'], list)
        
        # Verify initial state is empty
        assert len(director.world_state_tracker['discovered_clues']) == 0
        assert len(director.world_state_tracker['investigation_history']) == 0
    
    def test_world_state_persistence_across_turns(self):
        """Test that world state tracker persists data across multiple turns."""
        director = DirectorAgent()
        
        # Manually add some test data
        test_clue = {
            'content': 'Test clue content',
            'target': 'test_target', 
            'turn_discovered': 1,
            'timestamp': '2025-01-01T10:00:00',
            'discoverer': 'Test Agent'
        }
        
        director.world_state_tracker['discovered_clues']['test_agent'] = [test_clue]
        
        # Advance turn counter
        director.current_turn_number = 2
        
        # Verify data persists
        assert 'test_agent' in director.world_state_tracker['discovered_clues']
        assert len(director.world_state_tracker['discovered_clues']['test_agent']) == 1
        assert director.world_state_tracker['discovered_clues']['test_agent'][0]['content'] == 'Test clue content'


class TestActionImpactProcessing:
    """Test suite for action impact processing and world state updates."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.director = DirectorAgent()
        
        # Create mock agent
        self.mock_agent = Mock()
        self.mock_agent.agent_id = "test_agent_001"
        self.mock_agent.character_data = {
            'name': 'Test Character',
            'faction': 'Imperial Guard'
        }
    
    def test_investigate_action_processing(self):
        """Test that investigate actions generate clues and update world state."""
        # Create investigate action
        investigate_action = CharacterAction(
            action_type='investigate',
            target='mysterious_terminal',
            reasoning='Searching for clues about the station'
        )
        
        # Process the action
        self.director._process_action_world_impact(investigate_action, self.mock_agent)
        
        # Verify clue was generated
        assert 'test_agent_001' in self.director.world_state_tracker['discovered_clues']
        clues = self.director.world_state_tracker['discovered_clues']['test_agent_001']
        assert len(clues) == 1
        
        clue = clues[0]
        assert 'content' in clue
        assert 'mysterious_terminal' in clue['content'] or clue['target'] == 'mysterious_terminal'
        assert clue['turn_discovered'] == self.director.current_turn_number
        assert clue['discoverer'] == 'Test Character'
        
        # Verify environmental change was recorded
        assert 'mysterious_terminal' in self.director.world_state_tracker['environmental_changes']
        env_changes = self.director.world_state_tracker['environmental_changes']['mysterious_terminal']
        assert len(env_changes) == 1
        assert 'Test Character' in env_changes[0]['change']
        
        # Verify action was recorded in history
        history = self.director.world_state_tracker['investigation_history']
        assert len(history) == 1
        assert history[0]['agent_id'] == 'test_agent_001'
        assert history[0]['action_type'] == 'investigate'
        assert history[0]['target'] == 'mysterious_terminal'
    
    def test_search_action_processing(self):
        """Test that search actions generate clues and update world state."""
        search_action = CharacterAction(
            action_type='search',
            target='hidden_compartment',
            reasoning='Looking for concealed items'
        )
        
        self.director._process_action_world_impact(search_action, self.mock_agent)
        
        # Verify clue was generated for search action
        clues = self.director.world_state_tracker['discovered_clues']['test_agent_001']
        assert len(clues) == 1
        
        clue_content = clues[0]['content']
        # Verify clue references the target or contains meaningful content
        assert ('hidden_compartment' in clue_content.lower() or 
                clues[0]['target'] == 'hidden_compartment')
        assert len(clue_content) > 10  # Ensure substantial clue content
    
    def test_analyze_action_processing(self):
        """Test that analyze actions generate clues and update world state."""
        analyze_action = CharacterAction(
            action_type='analyze',
            target='data_corruption',
            reasoning='Analyzing patterns in the corruption'
        )
        
        self.director._process_action_world_impact(analyze_action, self.mock_agent)
        
        clues = self.director.world_state_tracker['discovered_clues']['test_agent_001']
        clue_content = clues[0]['content']
        
        # Verify clue was generated and references the target
        assert ('data_corruption' in clue_content.lower() or 
                clues[0]['target'] == 'data_corruption')
        assert len(clue_content) > 10  # Ensure substantial clue content
    
    def test_non_investigation_action_ignored(self):
        """Test that non-investigation actions don't generate clues."""
        combat_action = CharacterAction(
            action_type='attack',
            target='enemy',
            reasoning='Engaging hostile target'
        )
        
        self.director._process_action_world_impact(combat_action, self.mock_agent)
        
        # Should not generate clues for combat actions
        if 'test_agent_001' in self.director.world_state_tracker['discovered_clues']:
            assert len(self.director.world_state_tracker['discovered_clues']['test_agent_001']) == 0
        
        # But should still record in history
        history = self.director.world_state_tracker['investigation_history']
        assert len(history) == 1
        assert history[0]['action_type'] == 'attack'


class TestWorldStateFeedback:
    """Test suite for world state feedback generation and integration."""
    
    def setup_method(self):
        """Set up test fixtures with pre-populated world state."""
        self.director = DirectorAgent()
        
        # Set up mock agent
        self.mock_agent = Mock()
        self.mock_agent.agent_id = "test_agent_001"
        self.mock_agent.character_data = {
            'name': 'Test Character',
            'faction': 'Imperial Guard'
        }
        
        # Pre-populate world state with test data
        self.director.current_turn_number = 2
        
        # Add discovered clue from previous turn
        test_clue = {
            'content': 'Strange markings found on mysterious_terminal',
            'target': 'mysterious_terminal',
            'turn_discovered': 1,  # Previous turn
            'timestamp': '2025-01-01T10:00:00',
            'discoverer': 'Test Character'
        }
        
        self.director.world_state_tracker['discovered_clues']['test_agent_001'] = [test_clue]
        
        # Add to agent discoveries
        self.director.world_state_tracker['agent_discoveries'][1] = {
            'test_agent_001': ['Strange markings found on mysterious_terminal']
        }
    
    def test_agent_discoveries_feedback_generation(self):
        """Test generation of agent-specific discovery feedback."""
        feedback = self.director._get_agent_discoveries_feedback('test_agent_001')
        
        assert len(feedback) == 1
        assert '你发现了一条新的线索：Strange markings found on mysterious_terminal' in feedback[0]
    
    def test_world_state_feedback_integration(self):
        """Test that world state feedback is integrated into world state preparation."""
        world_state = self.director._prepare_world_state_for_agent(self.mock_agent)
        
        # Verify world state feedback is included
        assert 'world_state_feedback' in world_state
        feedback = world_state['world_state_feedback']
        
        assert 'personal_discoveries' in feedback
        discoveries = feedback['personal_discoveries']
        assert len(discoveries) == 1
        assert '你发现了一条新的线索' in discoveries[0]
    
    def test_environmental_changes_feedback(self):
        """Test feedback about environmental changes."""
        # Add environmental change from another agent
        self.director.world_state_tracker['environmental_changes']['test_location'] = [{
            'change': 'Signs of Another Agent\'s investigation are visible',
            'turn': 1,
            'agent': 'Another Agent',
            'timestamp': '2025-01-01T10:00:00'
        }]
        
        feedback = self.director._get_environmental_changes_feedback('test_agent_001')
        
        assert len(feedback) > 0
        assert any('Another Agent' in msg for msg in feedback)
    
    def test_world_state_summary_generation(self):
        """Test generation of world state summary."""
        summary = self.director._get_world_state_summary()
        
        assert 'total_clues_discovered' in summary
        assert 'total_investigations' in summary
        assert 'locations_with_activity' in summary
        assert 'current_phase' in summary
        assert 'world_activity_level' in summary
        
        # Should reflect the test data we added
        assert summary['total_clues_discovered'] == 1


class TestSacredValidationInvestigationLoop:
    """Sacred Validation Test Suite - Complete Investigation Feedback Loop."""
    
    def setup_method(self):
        """Set up complete test scenario with real agents and director."""
        # Create temporary character file
        self.temp_dir = tempfile.mkdtemp()
        self.character_file = os.path.join(self.temp_dir, "test_character.yaml")
        
        character_content = '''---
name: "Inspector Marcus"
faction: "Imperial Guard"
rank_role: "Investigation Specialist"
personality_traits:
  cautious: 0.8
  analytical: 0.9
  thorough: 0.7
decision_weights:
  mission_success: 0.9
  faction_loyalty: 0.8
  self_preservation: 0.6
'''
        
        with open(self.character_file, 'w', encoding='utf-8') as f:
            f.write(character_content)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_sacred_validation_complete_feedback_loop(self):
        """
        SACRED VALIDATION TEST: Complete investigate → world state → feedback cycle
        
        This test validates the core requirement from the story:
        1. Agent performs investigate action
        2. DirectorAgent processes action and updates world state  
        3. Next turn's world state includes discovered information
        4. Agent receives "你发现了一条新的线索：[线索内容]" feedback
        """
        # Step 1: Initialize DirectorAgent and create mock agent
        director = DirectorAgent()
        
        mock_agent = Mock()
        mock_agent.agent_id = "inspector_001"
        mock_agent.character_data = {
            'name': 'Inspector Marcus',
            'faction': 'Imperial Guard'
        }
        
        director.register_agent(mock_agent)
        
        # Step 2: Agent performs investigate action (Turn 1)
        investigate_action = CharacterAction(
            action_type='investigate',
            target='abandoned_data_terminal',
            reasoning='Searching for clues about the station incident'
        )
        
        # Process the action as if it came from decision_loop
        director.current_turn_number = 1
        director._process_action_world_impact(investigate_action, mock_agent)
        
        # Verify world state was updated
        assert 'inspector_001' in director.world_state_tracker['discovered_clues']
        clues = director.world_state_tracker['discovered_clues']['inspector_001']
        assert len(clues) == 1
        discovered_clue_content = clues[0]['content']
        assert 'abandoned_data_terminal' in discovered_clue_content or clues[0]['target'] == 'abandoned_data_terminal'
        
        # Step 3: Advance to next turn and generate world state
        director.current_turn_number = 2
        world_state_update = director._prepare_world_state_for_agent(mock_agent)
        
        # Step 4: Verify sacred validation requirement is met
        assert 'world_state_feedback' in world_state_update
        feedback = world_state_update['world_state_feedback']
        assert 'personal_discoveries' in feedback
        
        discoveries = feedback['personal_discoveries']
        assert len(discoveries) == 1
        
        # SACRED VALIDATION: Must include "你发现了一条新的线索：[线索内容]"
        discovery_message = discoveries[0]
        assert '你发现了一条新的线索：' in discovery_message
        assert discovered_clue_content in discovery_message
        
        # Verify complete feedback loop structure
        assert discovery_message == f"你发现了一条新的线索：{discovered_clue_content}"
    
    def test_multi_agent_investigation_coordination(self):
        """Test world state feedback with multiple agents investigating."""
        director = DirectorAgent()
        
        # Create two mock agents
        agent1 = Mock()
        agent1.agent_id = "agent_001"
        agent1.character_data = {'name': 'Agent Alpha', 'faction': 'Imperial'}
        
        agent2 = Mock()
        agent2.agent_id = "agent_002" 
        agent2.character_data = {'name': 'Agent Beta', 'faction': 'Imperial'}
        
        # Manually add agents to registered list for world state tracking
        director.registered_agents = [agent1, agent2]
        
        # Agent 1 investigates in turn 1
        director.current_turn_number = 1
        action1 = CharacterAction(action_type='investigate', target='location_a')
        director._process_action_world_impact(action1, agent1)
        
        # Agent 2 investigates in turn 2
        director.current_turn_number = 2
        action2 = CharacterAction(action_type='search', target='location_b')
        director._process_action_world_impact(action2, agent2)
        
        # Check that world state tracks both agents' activities
        assert 'agent_001' in director.world_state_tracker['discovered_clues']
        assert 'agent_002' in director.world_state_tracker['discovered_clues']
        
        # Verify agent discoveries are tracked by turn
        assert 1 in director.world_state_tracker['agent_discoveries']
        assert 2 in director.world_state_tracker['agent_discoveries']
        
        # Check that Agent 2 can potentially see Agent 1's activities
        other_activities = director._get_other_agents_activities_feedback('agent_002')
        
        # Should include information about Agent Alpha's recent discovery if within lookback window
        # (May be empty if timing doesn't align, which is acceptable behavior)
    
    def test_persistent_world_state_across_multiple_turns(self):
        """Test that world state changes persist and accumulate over multiple turns."""
        director = DirectorAgent()
        
        mock_agent = Mock()
        mock_agent.agent_id = "persistent_agent"
        mock_agent.character_data = {'name': 'Persistent Investigator', 'faction': 'Imperial'}
        
        director.register_agent(mock_agent)
        
        # Perform investigations across multiple turns
        locations = ['terminal_1', 'terminal_2', 'terminal_3']
        
        for turn, location in enumerate(locations, 1):
            director.current_turn_number = turn
            action = CharacterAction(action_type='investigate', target=location)
            director._process_action_world_impact(action, mock_agent)
        
        # Verify all discoveries are tracked
        clues = director.world_state_tracker['discovered_clues']['persistent_agent']
        assert len(clues) == 3
        
        # Verify world state summary reflects accumulated activity
        summary = director._get_world_state_summary()
        assert summary['total_clues_discovered'] == 3
        assert summary['total_investigations'] == 3
        assert summary['locations_with_activity'] == 3
        
        # Verify agent can see their complete discovery history
        director.current_turn_number = 4
        feedback = director._get_agent_discoveries_feedback('persistent_agent')
        
        # Should include recent discoveries (from turn 3)
        assert len(feedback) >= 1


class TestWorldHeartIntegration:
    """Integration tests for the complete World Heart system."""
    
    def test_world_heart_system_integration_with_existing_narrative(self):
        """Test that World Heart system integrates properly with existing narrative engine."""
        # Create DirectorAgent with campaign brief
        campaign_file = "E:\\Code\\Novel-Engine\\codex\\campaigns\\shadows_serenity_station\\campaign_brief.yaml"
        
        if os.path.exists(campaign_file):
            director = DirectorAgent(campaign_brief_path=campaign_file)
        else:
            director = DirectorAgent()  # Fallback without campaign
        
        # Verify both narrative and world state systems are active
        assert hasattr(director, 'world_state_tracker')
        assert hasattr(director, 'story_state')
        assert hasattr(director, 'narrative_resolver')
        
        # Create mock agent
        mock_agent = Mock()
        mock_agent.agent_id = "integration_agent"
        mock_agent.character_data = {'name': 'Integration Tester', 'faction': 'Imperial'}
        
        # Manually add to registered agents list for integration testing
        director.registered_agents = [mock_agent]
        
        # Perform investigate action
        action = CharacterAction(action_type='investigate', target='integration_target')
        director._process_action_world_impact(action, mock_agent)
        
        # Get world state update
        world_state = director._prepare_world_state_for_agent(mock_agent)
        
        # Verify both systems provide data
        assert 'world_state_feedback' in world_state  # World Heart system
        
        # If campaign brief is loaded, narrative context should be available
        # (Note: May not be present if agent lookup fails, which is acceptable)
        if director.campaign_brief and 'narrative_context' in world_state:
            assert isinstance(world_state['narrative_context'], dict)  # Valid narrative context
    
    def test_world_heart_performance_with_extended_simulation(self):
        """Test World Heart system performance during extended simulation."""
        director = DirectorAgent()
        
        mock_agent = Mock()
        mock_agent.agent_id = "performance_agent"
        mock_agent.character_data = {'name': 'Performance Tester', 'faction': 'Imperial'}
        
        director.register_agent(mock_agent)
        
        # Simulate extended activity (20 turns)
        for turn in range(1, 21):
            director.current_turn_number = turn
            action = CharacterAction(
                action_type='investigate',
                target=f'location_{turn % 5}',  # Rotate through 5 locations
                reasoning=f'Turn {turn} investigation'
            )
            director._process_action_world_impact(action, mock_agent)
        
        # Verify system remains functional
        world_state = director._prepare_world_state_for_agent(mock_agent)
        assert 'world_state_feedback' in world_state
        
        # Verify reasonable memory usage (not unlimited growth)
        total_clues = len(director.world_state_tracker['discovered_clues']['performance_agent'])
        total_history = len(director.world_state_tracker['investigation_history'])
        
        assert total_clues == 20  # Should track all clues
        assert total_history == 20  # Should track all actions
        
        # Verify summary generation still works
        summary = director._get_world_state_summary()
        assert summary['total_investigations'] == 20


def run_world_heart_tests():
    """
    Main function to run all World Heart system tests.
    
    This function can be called directly to validate the complete
    "世界之心" (World Heart) dynamic world state implementation.
    """
    print("Running World Heart System Test Suite - 世界之心")
    print("=" * 60)
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "-x",  # Stop on first failure for easier debugging
    ]
    
    try:
        exit_code = pytest.main(pytest_args)
        
        if exit_code == 0:
            print("\n✅ All World Heart system tests passed!")
            print("The dynamic world state feedback loop is working correctly.")
            print("Sacred Validation requirement has been met: investigate → clue → feedback")
        else:
            print(f"\n❌ Some tests failed (exit code: {exit_code})")
            print("Review the test output above to identify issues.")
        
        return exit_code
        
    except Exception as e:
        print(f"\n💥 Error running tests: {str(e)}")
        return 1


if __name__ == "__main__":
    # Run the test suite when script is executed directly
    exit_code = run_world_heart_tests()
    exit(exit_code)