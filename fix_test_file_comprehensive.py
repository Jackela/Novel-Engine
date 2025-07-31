#!/usr/bin/env python3
"""Comprehensive fix for test_persona_agent.py to use directory-based character loading"""

import re
import tempfile
import os

def fix_test_file_comprehensive():
    # Read the original content
    with open('test_persona_agent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create a proper fixed version
    fixed_content = '''#!/usr/bin/env python3
"""
Comprehensive Unit Tests for PersonaAgent Class
============================================

This test suite validates the PersonaAgent implementation using pytest framework.
Tests cover initialization, character context loading, method functionality, and error handling.

Test Requirements:
- Import Test: Verify PersonaAgent class can be imported correctly
- Initialization Test: Test PersonaAgent can be initialized with character directory
- Character Context Loading: Test load_character_context() method properly loads character data
- Method Functionality: Verify placeholder methods work without errors
- Error Handling: Test error conditions and edge cases

Usage:
    pytest test_persona_agent.py -v
"""

import pytest
import os
import tempfile
import json
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock

# Import the PersonaAgent class and related components
from persona_agent import (
    PersonaAgent,
    ThreatLevel,
    ActionPriority,
    CharacterAction,
    WorldEvent,
    SubjectiveInterpretation,
    create_character_from_template,
    analyze_agent_compatibility
)


def create_test_character_directory():
    """Create a temporary directory with multiple test character .md files."""
    temp_dir = tempfile.mkdtemp(prefix="test_character_")
    
    # Primary character file
    character_file = os.path.join(temp_dir, "character.md")
    with open(character_file, 'w', encoding='utf-8') as f:
        f.write("""name: Test Subject 01
factions: [Imperium]
personality_traits: [Cautious]

# Character Sheet: Test Subject 01

## Core Identity
- **Name**: Test Subject 01
- **Faction**: Imperium
- **Rank**: Soldier

## Psychological Profile
### Personality Traits
- **Cautious**: Carefully considers actions
- **Loyal**: Devoted to the Imperium
""")
    
    # Additional lore file
    lore_file = os.path.join(temp_dir, "background.md")
    with open(lore_file, 'w', encoding='utf-8') as f:
        f.write("""# Background Information

Test Subject 01 was recruited from the hive world of Necromunda.
Training records indicate exceptional marksmanship and tactical awareness.

## Combat History
- Participated in 3 minor engagements
- Demonstrated competence under fire
""")
    
    # Faction information file
    faction_file = os.path.join(temp_dir, "faction_data.md")
    with open(faction_file, 'w', encoding='utf-8') as f:
        f.write("""# Imperial Guard Data

## Organization
The Imperial Guard represents humanity's primary military force.

## Doctrine
- Hold the line at all costs
- The Emperor protects
""")
    
    return temp_dir


class TestPersonaAgentImport:
    """Test suite for verifying PersonaAgent import functionality."""
    
    def test_persona_agent_import(self):
        """Test that PersonaAgent class can be imported correctly."""
        # Verify the class exists and is importable
        assert PersonaAgent is not None
        assert callable(PersonaAgent)
    
    def test_enum_imports(self):
        """Test that required enums can be imported correctly."""
        assert ThreatLevel is not None
        assert ActionPriority is not None
        
        # Verify enum values
        assert ThreatLevel.NEGLIGIBLE.value == "negligible"
        assert ThreatLevel.LOW.value == "low"
        assert ThreatLevel.HIGH.value == "high"
        assert ThreatLevel.CRITICAL.value == "critical"
        
        assert ActionPriority.CRITICAL.value == "critical"
        assert ActionPriority.HIGH.value == "high"
        assert ActionPriority.NORMAL.value == "normal"
        assert ActionPriority.LOW.value == "low"
    
    def test_dataclass_imports(self):
        """Test that required dataclasses can be imported correctly."""
        assert CharacterAction is not None
        assert WorldEvent is not None
        assert SubjectiveInterpretation is not None


class TestPersonaAgentInitialization:
    """Test suite for PersonaAgent initialization functionality."""
    
    def test_initialization_with_test_character(self):
        """Test PersonaAgent can be initialized with test character directory."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Verify basic initialization
            assert agent is not None
            assert agent.character_directory_path == test_character_dir
            assert agent.agent_id is not None
            assert isinstance(agent.character_data, dict)
            assert isinstance(agent.subjective_worldview, dict)
            # Verify full context was loaded
            assert 'full_context' in agent.character_data
            assert len(agent.character_data['full_context']) > 0
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_agent_id_derivation(self):
        """Test that agent ID is correctly derived from directory path."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Agent ID should be derived from directory name
            expected_id = os.path.basename(os.path.normpath(test_character_dir)).lower()
            assert agent.agent_id == expected_id
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_initialization_with_custom_agent_id(self):
        """Test PersonaAgent initialization with custom agent ID."""
        test_character_dir = create_test_character_directory()
        custom_id = "custom_test_agent"
        
        try:
            agent = PersonaAgent(test_character_dir, agent_id=custom_id)
            
            assert agent.agent_id == custom_id
            assert agent.character_directory_path == test_character_dir
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_initialization_properties(self):
        """Test that all required properties are initialized."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Verify all properties are initialized
            assert hasattr(agent, 'character_directory_path')
            assert hasattr(agent, 'agent_id')
            assert hasattr(agent, 'character_data')
            assert hasattr(agent, 'subjective_worldview')
            assert hasattr(agent, 'current_location')
            assert hasattr(agent, 'current_status')
            assert hasattr(agent, 'morale_level')
            assert hasattr(agent, 'decision_weights')
            assert hasattr(agent, 'short_term_memory')
            assert hasattr(agent, 'long_term_memory')
            assert hasattr(agent, 'personality_traits')
            assert hasattr(agent, 'behavioral_modifiers')
            assert hasattr(agent, 'relationships')
            assert hasattr(agent, 'communication_style')
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)


class TestCharacterSheetLoading:
    """Test suite for character context loading functionality."""
    
    def test_load_character_context_basic(self):
        """Test that load_character_context() method loads without errors."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # The method should have been called during initialization
            # Verify that character data was loaded
            assert agent.character_data is not None
            assert isinstance(agent.character_data, dict)
            assert 'full_context' in agent.character_data
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_character_name_loading(self):
        """Test that character name 'Test Subject 01' is loaded correctly."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Based on the test character files content
            assert isinstance(agent.character_data, dict)
            
            # The name should be parsed from the concatenated content
            name = agent.character_data.get('name')
            # The name should be loaded from our test data
            assert name == 'Test Subject 01'
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_faction_loading(self):
        """Test that faction 'Imperium' is loaded correctly."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Based on the test character files content
            factions = agent.character_data.get('factions')
            # The faction should be loaded from our test data
            assert factions == ['Imperium']
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_personality_traits_loading(self):
        """Test that personality trait 'Cautious' is loaded correctly."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Based on the test character files content
            traits = agent.character_data.get('personality_traits')
            # The traits should be loaded from our test data
            assert traits == ['Cautious']
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_load_character_context_explicit_call(self):
        """Test explicit call to load_character_context() method."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Clear the character data to test explicit loading
            agent.character_data = {}
            
            # Explicitly call the load method
            agent.load_character_context()
            
            # Verify that data was loaded
            assert isinstance(agent.character_data, dict)
            assert 'full_context' in agent.character_data
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)
    
    def test_directory_not_found_error(self):
        """Test proper error handling when character directory doesn't exist."""
        non_existent_path = "definitely_does_not_exist_dir"
        
        with pytest.raises((FileNotFoundError, ValueError)):
            PersonaAgent(non_existent_path)


# Pytest fixtures for common test setup
@pytest.fixture(autouse=True)
def mock_gemini_api():
    """Automatically mock Gemini API for all tests in this module."""
    with patch('persona_agent._make_gemini_api_request') as mock_api:
        mock_api.return_value = "ACTION: observe\\nTARGET: none\\nREASONING: Standard mock response for testing"
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'AIza_test_key_for_mocking'}):
            yield mock_api


@pytest.fixture
def basic_agent():
    """Fixture providing a basic PersonaAgent for testing."""
    test_character_dir = create_test_character_directory()
    agent = PersonaAgent(test_character_dir)
    # Store reference for cleanup
    agent._test_dir = test_character_dir
    yield agent
    # Cleanup
    if hasattr(agent, '_test_dir'):
        shutil.rmtree(agent._test_dir, ignore_errors=True)


# Basic test framework
class TestMethodFunctionality:
    """Test suite for PersonaAgent method functionality."""
    
    def test_decision_loop_basic(self):
        """Test that decision_loop() method executes without errors."""
        test_character_dir = create_test_character_directory()
        
        try:
            agent = PersonaAgent(test_character_dir)
            
            # Create test world state update
            world_state_update = {
                "current_time": datetime.now().isoformat(),
                "events": [],
                "threat_level": "low"
            }
            
            # Test decision loop
            action = agent.decision_loop(world_state_update)
            
            # Verify action is returned (might be None for placeholder implementation)
            # The method should not raise exceptions
            assert action is None or isinstance(action, CharacterAction)
        finally:
            shutil.rmtree(test_character_dir, ignore_errors=True)


class TestWithFixtures:
    """Tests using pytest fixtures."""
    
    def test_agent_fixture(self, basic_agent):
        """Test using the basic_agent fixture."""
        assert isinstance(basic_agent, PersonaAgent)
        # The agent ID will be based on the temp directory name
        assert basic_agent.agent_id is not None
    
    def test_decision_with_fixture(self, basic_agent):
        """Test decision-making using fixtures."""
        world_state_update = {
            "current_time": datetime.now().isoformat(),
            "events": [],
            "threat_level": "low"
        }
        action = basic_agent.decision_loop(world_state_update)
        assert action is None or isinstance(action, CharacterAction)


if __name__ == "__main__":
    # Run tests when script is executed directly
    pytest.main([__file__, "-v"])
'''
    
    # Write the fixed content
    with open('test_persona_agent.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("Completely rewrote test_persona_agent.py with directory-based testing")

if __name__ == "__main__":
    fix_test_file_comprehensive()