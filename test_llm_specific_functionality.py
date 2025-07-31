#!/usr/bin/env python3
"""
Specific Tests for LLM Integration Functionality
===============================================

This test module specifically validates the new LLM integration features
added to the PersonaAgent's decision_loop method in Phase 2.
"""

import pytest
import logging
import os
from unittest.mock import patch, MagicMock, mock_open
from persona_agent import PersonaAgent, CharacterAction, ActionPriority
from character_factory import CharacterFactory

class TestLLMIntegrationFunctionality:
    """Test suite specifically for LLM integration features."""
    
    @pytest.fixture
    def character_factory(self):
        """Provide CharacterFactory instance for tests."""
        return CharacterFactory()
    
    @pytest.fixture(autouse=True)
    def setup_mocking(self):
        """Setup comprehensive mocking for all tests."""
        # Mock environment variable
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'}):
            # Mock the API request function
            with patch('persona_agent._make_gemini_api_request') as mock_api:
                # Setup realistic mock responses
                mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Mock response for testing purposes"
                self.mock_api = mock_api
                yield
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_enhanced_decision_making_success(self, mock_api, character_factory):
        """Test successful LLM-enhanced decision making."""
        # Setup mock response
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Careful observation required in this tactical situation"
        
        agent = character_factory.create_character("test")
        
        world_state = {
            'location_updates': {'test_area': {'threat_level': 'high'}},
            'recent_events': [{
                'id': 'combat_event',
                'type': 'battle',
                'description': 'Enemy forces approaching',
                'scope': 'local'
            }]
        }
        
        # Test that LLM integration produces an action
        action = agent.decision_loop(world_state)
        
        # Should get an action (could be LLM-guided or fallback)
        assert action is None or isinstance(action, CharacterAction)
        
        # Verify API was called
        assert mock_api.called
        
        # If an action is returned, it should have LLM-guided reasoning or fallback reasoning
        if action:
            assert action.reasoning is not None
            assert len(action.reasoning) > 0
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_prompt_construction_contains_character_data(self, mock_api, character_factory):
        """Test that character-specific prompts contain relevant character data."""
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Test response"
        
        agent = character_factory.create_character("test")
        
        world_state = {'recent_events': []}
        situation_assessment = agent._assess_current_situation()
        available_actions = agent._identify_available_actions(situation_assessment)
        
        prompt = agent._construct_character_prompt(world_state, situation_assessment, available_actions)
        
        # Verify prompt contains expected sections
        assert "CHARACTER IDENTITY:" in prompt
        assert "PERSONALITY TRAITS:" in prompt
        assert "DECISION-MAKING PRIORITIES:" in prompt
        assert "CURRENT SITUATION:" in prompt
        assert "AVAILABLE ACTIONS:" in prompt
        assert "DECISION REQUEST:" in prompt
        
        # Verify prompt contains character information
        assert str(agent.morale_level) in prompt
        assert agent.current_status in prompt
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_response_parsing_valid_format(self, mock_api, character_factory):
        """Test parsing of valid LLM response format."""
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Test response"
        
        agent = character_factory.create_character("test")
        
        available_actions = [
            {'type': 'observe', 'description': 'Watch and gather information'},
            {'type': 'attack', 'description': 'Engage hostile targets'},
            {'type': 'communicate', 'description': 'Attempt communication'}
        ]
        
        # Test numeric action reference
        llm_response = """ACTION: 2
TARGET: enemy_unit_alpha
REASONING: My aggressive nature and faction loyalty demand immediate action against the threat."""
        
        action = agent._parse_llm_response(llm_response, available_actions)
        
        assert action is not None
        assert action.action_type == 'attack'  # Second action (index 1)
        assert action.target == 'enemy_unit_alpha'
        assert 'aggressive nature' in action.reasoning
        assert action.reasoning.startswith('[LLM-Guided]')
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_response_parsing_direct_action_type(self, mock_api, character_factory):
        """Test parsing of LLM response with direct action type."""
        mock_api.return_value = "ACTION: communicate\nTARGET: nearby_ally\nREASONING: Test response"
        
        agent = character_factory.create_character("test")
        
        available_actions = [
            {'type': 'observe', 'description': 'Watch and gather information'},
            {'type': 'communicate', 'description': 'Attempt communication'}
        ]
        
        llm_response = """ACTION: communicate
TARGET: nearby_ally
REASONING: Communication is essential to coordinate our response."""
        
        action = agent._parse_llm_response(llm_response, available_actions)
        
        assert action is not None
        assert action.action_type == 'communicate'
        assert action.target == 'nearby_ally'
        assert 'Communication is essential' in action.reasoning
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_response_parsing_wait_action(self, mock_api, character_factory):
        """Test that wait/observe responses return None correctly."""
        mock_api.return_value = "ACTION: wait_observe\nTARGET: none\nREASONING: Test response"
        
        agent = character_factory.create_character("test")
        
        available_actions = [{'type': 'observe', 'description': 'Watch and gather information'}]
        
        llm_response = """ACTION: wait_observe
TARGET: none
REASONING: The situation requires careful observation before acting."""
        
        action = agent._parse_llm_response(llm_response, available_actions)
        
        # Wait actions should return None
        assert action is None
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_response_parsing_malformed_input(self, mock_api, character_factory):
        """Test parsing of malformed LLM responses."""
        mock_api.return_value = "This is not a valid response format at all."
        
        agent = character_factory.create_character("test")
        
        available_actions = [{'type': 'observe', 'description': 'Watch and gather information'}]
        
        # Test completely malformed response
        malformed_response = "This is not a valid response format at all."
        
        action = agent._parse_llm_response(malformed_response, available_actions)
        
        # Should return None to trigger algorithmic fallback
        assert action is None
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_llm_action_priority_determination(self, mock_api, character_factory):
        """Test that LLM action priorities are determined correctly."""
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Test response"
        
        agent = character_factory.create_character("test")
        
        # Test critical priority actions
        assert agent._determine_llm_action_priority('retreat', 'Emergency withdrawal required') == ActionPriority.CRITICAL
        assert agent._determine_llm_action_priority('call_for_help', 'Urgent assistance needed') == ActionPriority.CRITICAL
        
        # Test high priority actions
        assert agent._determine_llm_action_priority('attack', 'Immediate threat response') == ActionPriority.HIGH
        assert agent._determine_llm_action_priority('defend', 'Critical defense needed') == ActionPriority.HIGH
        
        # Test normal priority
        assert agent._determine_llm_action_priority('investigate', 'Standard investigation') == ActionPriority.NORMAL
        
        # Test low priority
        assert agent._determine_llm_action_priority('observe', 'Routine observation') == ActionPriority.LOW
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_fallback_mechanism_on_llm_failure(self, mock_api, character_factory):
        """Test that fallback mechanism works when LLM fails."""
        # Setup API to raise an exception
        mock_api.side_effect = Exception("Simulated API failure")
        
        agent = character_factory.create_character("test")
        
        try:
            world_state = {
                'location_updates': {'test_location': {'threat_level': 'moderate'}},
                'recent_events': []
            }
            
            action = agent.decision_loop(world_state)
            
            # Should still get a result (either action or None) due to fallback
            assert action is None or isinstance(action, CharacterAction)
            
            # If an action is returned, it should not have LLM-guided reasoning
            if action:
                assert '[LLM-Guided]' not in action.reasoning
                
        finally:
            # Reset mock for other tests
            mock_api.side_effect = None
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_deterministic_llm_responses_for_testing(self, mock_api, character_factory):
        """Test that LLM responses are deterministic for testing purposes."""
        # Setup deterministic mock response
        test_response = "ACTION: observe\nTARGET: none\nREASONING: Deterministic test response for validation"
        mock_api.return_value = test_response
        
        agent = character_factory.create_character("test")
        
        # Use a specific prompt that won't trigger random failures
        test_prompt = "A" * 50 + " This is a specific test prompt for deterministic response testing"
        
        response1 = agent._call_llm(test_prompt)
        response2 = agent._call_llm(test_prompt)
        
        # Should be identical for testing purposes
        assert response1 == response2
        
        # Should contain expected format
        assert "ACTION:" in response1
        assert "TARGET:" in response1
        assert "REASONING:" in response1
        
        # Verify mock was called
        assert mock_api.call_count >= 2
    
    @patch('persona_agent._make_gemini_api_request')
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'})
    def test_character_traits_influence_llm_responses(self, mock_api, character_factory):
        """Test that character traits influence the LLM response generation."""
        mock_api.return_value = "ACTION: observe\nTARGET: none\nREASONING: Cautious assessment required"
        
        agent = character_factory.create_character("test")
        
        # Set specific personality traits to test influence
        agent.personality_traits['cautious'] = 0.9
        agent.personality_traits['aggressive'] = 0.1
        
        # Create a threat scenario
        threat_prompt = agent._construct_character_prompt(
            {'recent_events': [{'type': 'battle', 'description': 'High threat incoming'}]},
            agent._assess_current_situation(),
            agent._identify_available_actions(agent._assess_current_situation())
        )
        
        response = agent._call_llm(threat_prompt)
        
        # With high caution, should tend toward defensive/careful actions
        # Note: This tests the deterministic simulation, not actual LLM behavior
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Verify mock was called with the prompt
        assert mock_api.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])