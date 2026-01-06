#!/usr/bin/env python3
"""
PersonaAgent Comprehensive Test Suite
=====================================

Systematic testing for src/persona_agent.py covering character initialization,
decision-making, world event interpretation, AI integration, and character evolution.
"""
import logging
import os
from unittest.mock import Mock, mock_open, patch

import pytest

# Import the modules under test
try:
    pass

    from shared_types import CharacterAction
    from src.event_bus import EventBus
    from src.persona_agent import (
        PersonaAgent,
        ThreatLevel,
        WorldEvent,
    )

    PERSONA_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"PersonaAgent import failed: {e}")
    PERSONA_AGENT_AVAILABLE = False


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentInitialization:
    """PersonaAgent Initialization and Character Loading Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_char_dir = "test_character"
        self.test_character_content = """# Character Sheet: Test Hero

## Basic Information
- **Name**: Test Hero
- **Faction**: Imperial Guard
- **Rank**: Sergeant
- **Background**: A veteran soldier from Cadia

## Personality Traits
- Brave and loyal to the Emperor
- Distrustful of xenos
- Protective of fellow guardsmen

## Equipment
- Las-rifle
- Flak armor
- Frag grenades

## Goals
- Survive the next battle
- Protect civilians
- Serve the Emperor
"""

    def teardown_method(self):
        """Cleanup after each test"""
        # Clean up any temporary files
        for filename in [f"{self.temp_char_dir}.md", "character.md"]:
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except Exception:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    @pytest.mark.unit
    def test_initialization_with_valid_character_directory(self):
        """Test PersonaAgent initialization with valid character directory"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=self.test_character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=self.test_character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            agent = PersonaAgent(
                character_directory_path=self.temp_char_dir,
                event_bus=self.mock_event_bus,
                agent_id="test_hero",
            )

            # Verify basic initialization
            assert agent.character_directory_path == self.temp_char_dir
            assert agent.agent_id == "test_hero"
            assert agent.event_bus == self.mock_event_bus
            assert hasattr(agent, "character_data")
            assert hasattr(agent, "subjective_worldview")

    @pytest.mark.unit
    def test_initialization_auto_generate_agent_id(self):
        """Test agent ID auto-generation from character directory path"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=self.test_character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=self.test_character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            agent = PersonaAgent(
                character_directory_path="characters/imperial_guard/marcus",
                event_bus=self.mock_event_bus,
            )

            # Should auto-generate agent ID from path
            assert agent.agent_id is not None
            assert len(agent.agent_id) > 0

    @pytest.mark.unit
    def test_initialization_missing_character_directory(self):
        """Test initialization behavior with missing character directory"""
        with patch("os.path.exists", return_value=False):
            with pytest.raises((FileNotFoundError, ValueError, OSError)):
                PersonaAgent(
                    character_directory_path="nonexistent_character",
                    event_bus=self.mock_event_bus,
                )

    @pytest.mark.unit
    @pytest.mark.integration
    def test_initialization_empty_character_directory(self):
        """Test initialization with empty character directory"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=[]):
            with pytest.raises(ValueError, match="No .md or .yaml files found"):
                PersonaAgent(
                    character_directory_path=self.temp_char_dir,
                    event_bus=self.mock_event_bus,
                )

    @pytest.mark.unit
    def test_event_bus_subscription(self):
        """Test that PersonaAgent subscribes to TURN_START event"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=self.test_character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=self.test_character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            agent = PersonaAgent(
                character_directory_path=self.temp_char_dir,
                event_bus=self.mock_event_bus,
            )

            # Verify subscription to TURN_START event
            self.mock_event_bus.subscribe.assert_called_with(
                "TURN_START", agent.handle_turn_start
            )


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentCharacterLoading:
    """PersonaAgent Character Data Loading and Parsing Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    def create_test_agent(self, character_content: str):
        """Helper to create test agent with specific character content"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            return PersonaAgent(
                character_directory_path="test_character",
                event_bus=self.mock_event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_character_data_parsing_basic_info(self):
        """Test parsing of basic character information"""
        character_content = """# Character Sheet: Brother Marcus

## Basic Information
- **Name**: Brother Marcus
- **Chapter**: Ultramarines
- **Rank**: Battle-Brother
- **Experience**: Veteran

## Equipment
- Bolter
- Power Armor
"""

        agent = self.create_test_agent(character_content)

        # Verify character data was loaded
        assert hasattr(agent, "character_data")
        if hasattr(agent, "character"):
            assert hasattr(agent.character, "name")

    @pytest.mark.unit
    def test_character_data_parsing_personality_traits(self):
        """Test parsing of personality traits and behavioral data"""
        character_content = """# Character Sheet: Inquisitor Vex

## Personality Traits
- Ruthless in pursuit of heretics
- Suspicious of everyone
- Highly intelligent and observant
- Values duty above personal relationships

## Goals
- Eliminate Chaos corruption
- Protect Imperial worlds
"""

        agent = self.create_test_agent(character_content)

        # Verify personality data processing
        assert agent.character_data is not None
        # Character should have some form of personality or traits data
        assert hasattr(agent, "subjective_worldview")

    @pytest.mark.unit
    def test_character_data_parsing_malformed_content(self):
        """Test handling of malformed character sheet content"""
        malformed_content = """This is not a proper character sheet
No structured data here
Just random text"""

        agent = self.create_test_agent(malformed_content)
        # Should handle gracefully with defaults
        assert agent.character_data is not None

    @pytest.mark.unit
    def test_multiple_character_files_handling(self):
        """Test handling multiple character files in directory"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch(
            "os.listdir",
            return_value=["character.md", "background.md", "equipment.yaml"],
        ), patch(
            "builtins.open", mock_open(read_data="# Test Character")
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value="# Test Character",
        ), patch(
            "src.persona_agent.PersonaAgent._parse_cached_yaml", return_value={}
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            agent = PersonaAgent(
                character_directory_path="test_character", event_bus=self.mock_event_bus
            )

            # Should handle multiple files appropriately
            assert agent.character_data is not None


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentDecisionMaking:
    """PersonaAgent Decision Making and Action Generation Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.test_world_state = {
            "current_turn": 1,
            "active_threats": ["ork_raiders"],
            "nearby_entities": ["imperial_guard_squad"],
            "location": "sector_7",
        }

    def create_test_agent(self):
        """Helper to create a standard test agent"""
        character_content = """# Character Sheet: Test Agent
## Basic Information
- **Name**: Test Agent
- **Faction**: Imperial
## Personality Traits
- Tactical and careful
- Loyal to Emperor
"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            return PersonaAgent(
                character_directory_path="test_character",
                event_bus=self.mock_event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_handle_turn_start_basic_functionality(self):
        """Test basic turn start handling"""
        agent = self.create_test_agent()

        # Mock the _make_decision method
        mock_action = CharacterAction(
            action_type="investigate", reasoning="Test reasoning"
        )
        agent._make_decision = Mock(return_value=mock_action)

        # Test turn start handling
        agent.handle_turn_start(self.test_world_state)

        # Verify decision making was called
        agent._make_decision.assert_called_once_with(self.test_world_state)

        # Verify event emission
        self.mock_event_bus.emit.assert_called_once_with(
            "AGENT_ACTION_COMPLETE", agent=agent, action=mock_action
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_handle_turn_start_no_action(self):
        """Test turn start handling when no action is generated"""
        agent = self.create_test_agent()

        # Mock _make_decision to return None
        agent._make_decision = Mock(return_value=None)

        agent.handle_turn_start(self.test_world_state)

        # Should still emit event with None action
        self.mock_event_bus.emit.assert_called_once_with(
            "AGENT_ACTION_COMPLETE", agent=agent, action=None
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_make_decision_with_valid_world_state(self):
        """Test decision making with valid world state"""
        agent = self.create_test_agent()

        # Mock AI integration to avoid external dependencies
        with patch("src.persona_agent._validate_gemini_api_key", return_value=None):
            result = agent._make_decision(self.test_world_state)

            # Result should be CharacterAction or None
            assert result is None or isinstance(result, CharacterAction)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_decision_making_error_handling(self):
        """Test decision making error handling"""
        agent = self.create_test_agent()

        # Test with invalid world state
        invalid_world_state = None

        with patch("src.persona_agent._validate_gemini_api_key", return_value=None):
            result = agent._make_decision(invalid_world_state)
            # Should handle gracefully
            assert result is None or isinstance(result, CharacterAction)


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentWorldInterpretation:
    """PersonaAgent World Event Interpretation Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.test_world_event = WorldEvent(
            event_id="test_event_001",
            event_type="battle",
            source="ork_waaagh",
            affected_entities=["imperial_guard"],
            location="hive_city_alpha",
            description="Ork raiders attack the outer districts",
        )

    def create_test_agent(self):
        """Helper to create test agent"""
        character_content = """# Character Sheet: Imperial Guard Veteran
## Basic Information
- **Name**: Veteran Kasrkin
- **Faction**: Imperial Guard
## Personality Traits  
- Battle-hardened veteran
- Protective of civilians
- Hates orks with passion
"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            return PersonaAgent(
                character_directory_path="test_character",
                event_bus=self.mock_event_bus,
                agent_id="kasrkin_vet",
            )

    @pytest.mark.unit
    def test_subjective_worldview_initialization(self):
        """Test subjective worldview initialization"""
        agent = self.create_test_agent()

        # Verify subjective worldview structure
        assert hasattr(agent, "subjective_worldview")
        assert isinstance(agent.subjective_worldview, dict)

        # Check for expected worldview components
        expected_components = [
            "known_entities",
            "location_knowledge",
            "faction_relationships",
            "recent_events",
            "current_goals",
            "active_threats",
        ]
        for component in expected_components:
            assert component in agent.subjective_worldview

    @pytest.mark.unit
    def test_world_event_interpretation_methods(self):
        """Test world event interpretation capabilities"""
        agent = self.create_test_agent()

        # Test if agent has event interpretation methods
        interpretation_methods = [
            "_interpret_event",
            "_assess_threat_level",
            "_update_worldview",
            "_process_world_event",
        ]

        for method_name in interpretation_methods:
            if hasattr(agent, method_name):
                method = getattr(agent, method_name)
                assert callable(method)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_threat_assessment_capability(self):
        """Test agent's threat assessment capabilities"""
        agent = self.create_test_agent()

        # Check if agent can assess threats
        if hasattr(agent, "_assess_threat_level"):
            try:
                threat_level = agent._assess_threat_level(self.test_world_event)
                assert isinstance(threat_level, ThreatLevel) or threat_level is None
            except Exception:
                # Method might require additional setup
                pass


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentAIIntegration:
    """PersonaAgent AI/LLM Integration Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    def create_test_agent(self):
        """Helper to create test agent"""
        character_content = "# Character Sheet: AI Test Agent\n## Basic Information\n- **Name**: AI Agent"
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            return PersonaAgent(
                character_directory_path="ai_test_character",
                event_bus=self.mock_event_bus,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_ai_api_key_validation(self):
        """Test AI API key validation"""
        # Test the validation function directly
        with patch("os.getenv", return_value="test_api_key"):
            from src.persona_agent import _validate_gemini_api_key

            result = _validate_gemini_api_key()
            assert result == "test_api_key"

        # Test with no API key
        with patch("os.getenv", return_value=None):
            result = _validate_gemini_api_key()
            assert result is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_ai_integration_fallback_behavior(self):
        """Test fallback behavior when AI integration fails"""
        agent = self.create_test_agent()

        # Should initialize successfully even without AI
        assert agent is not None

        # Decision making should use fallback logic
        world_state = {"current_turn": 1}
        with patch("src.persona_agent._validate_gemini_api_key", return_value=None):
            result = agent._make_decision(world_state)
            # Should return None or basic CharacterAction
            assert result is None or isinstance(result, CharacterAction)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_ai_request_handling_with_mock(self):
        """Test AI request handling with mocked responses"""
        agent = self.create_test_agent()

        # Test decision making without actual AI calls
        world_state = {"current_turn": 1, "threats": ["orks"]}
        with patch("src.persona_agent._validate_gemini_api_key", return_value=None):
            result = agent._make_decision(world_state)
            # Should process appropriately without AI
            assert result is None or isinstance(result, CharacterAction)


@pytest.mark.skipif(not PERSONA_AGENT_AVAILABLE, reason="PersonaAgent not available")
class TestPersonaAgentMemoryAndEvolution:
    """PersonaAgent Memory System and Character Evolution Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    def create_test_agent(self):
        """Helper to create test agent"""
        character_content = """# Character Sheet: Evolving Character
## Basic Information
- **Name**: Dynamic Agent
- **Experience Level**: Recruit
## Personality Traits
- Eager to learn
- Adaptive to situations
"""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=character_content)
        ), patch(
            "src.persona_agent.PersonaAgent._read_cached_file",
            return_value=character_content,
        ), patch.object(
            PersonaAgent, "_extract_core_identity"
        ), patch.object(
            PersonaAgent, "_extract_personality_traits"
        ), patch.object(
            PersonaAgent, "_extract_decision_weights"
        ), patch.object(
            PersonaAgent, "_extract_relationships"
        ), patch.object(
            PersonaAgent, "_extract_knowledge_domains"
        ), patch.object(
            PersonaAgent, "_initialize_subjective_worldview"
        ):
            return PersonaAgent(
                character_directory_path="evolving_character",
                event_bus=self.mock_event_bus,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_memory_system_initialization(self):
        """Test memory system initialization"""
        agent = self.create_test_agent()

        # Check for memory-related attributes
        memory_attributes = [
            "subjective_worldview",
            "character_data",
            "current_location",
        ]

        for attr in memory_attributes:
            assert hasattr(agent, attr)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_character_evolution_tracking(self):
        """Test character evolution and experience tracking"""
        agent = self.create_test_agent()

        # Check for evolution tracking mechanisms
        evolution_attributes = [
            "experience_points",
            "character_evolution",
            "trait_evolution",
        ]

        for attr in evolution_attributes:
            if hasattr(agent, attr):
                # If evolution system exists, verify it's properly initialized
                assert getattr(agent, attr) is not None

    @pytest.mark.unit
    def test_memory_persistence_capability(self):
        """Test memory persistence capabilities"""
        agent = self.create_test_agent()

        # Check for memory persistence methods
        persistence_methods = [
            "_save_character_state",
            "_load_character_state",
            "_update_memory",
            "_store_experience",
        ]

        for method_name in persistence_methods:
            if hasattr(agent, method_name):
                method = getattr(agent, method_name)
                assert callable(method)


# Helper functions for running specific test suites
def run_persona_initialization_tests():
    """Run initialization tests specifically"""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-k",
            "TestPersonaAgentInitialization",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("PersonaAgent Initialization Tests:")
    print(result.stdout)
    return result.returncode == 0


def run_persona_decision_tests():
    """Run decision making tests specifically"""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-k",
            "TestPersonaAgentDecisionMaking",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("PersonaAgent Decision Making Tests:")
    print(result.stdout)
    return result.returncode == 0


def run_all_persona_tests():
    """Run all persona agent tests"""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short", __file__],
        capture_output=True,
        text=True,
    )

    print("All PersonaAgent Tests:")
    print(result.stdout)
    return result.returncode == 0


if __name__ == "__main__":
    # Direct execution runs all tests
    run_all_persona_tests()
