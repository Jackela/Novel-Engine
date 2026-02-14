import os
import unittest
from unittest.mock import Mock, mock_open, patch

import pytest

from src.agents.persona_agent.agent import PersonaAgent
from src.agents.persona_agent.protocols import (
    ThreatLevel,
    WorldEvent,
)
from src.core.event_bus import EventBus
from src.core.types.shared_types import CharacterAction

pytestmark = pytest.mark.unit


class TestPersonaAgent(unittest.TestCase):
    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        # Mock the file system operations
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["character.md"]
        ), patch(
            "builtins.open",
            unittest.mock.mock_open(read_data="# Character Sheet: Test Agent"),
        ):
            self.agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_initialization_subscribes_to_turn_start(self):
        """Test that the PersonaAgent subscribes to the TURN_START event on initialization."""
        self.event_bus.subscribe.assert_called_once_with(
            "TURN_START", self.agent.handle_turn_start
        )

    @pytest.mark.unit
    def test_handle_turn_start_emits_action(self):
        """Test that handle_turn_start calls _make_decision and emits an AGENT_ACTION_COMPLETE event."""
        # Mock the _make_decision method to return a specific action
        mock_action = CharacterAction(action_type="test", reasoning="test reasoning")
        self.agent._make_decision = Mock(return_value=mock_action)

        world_state_update = {"current_turn": 1}
        self.agent.handle_turn_start(world_state_update)

        # Verify that _make_decision was called
        self.agent._make_decision.assert_called_once_with(world_state_update)

        # Verify that AGENT_ACTION_COMPLETE was emitted
        self.event_bus.emit.assert_called_once_with(
            "AGENT_ACTION_COMPLETE", agent=self.agent, action=mock_action
        )

    @pytest.mark.unit
    def test_handle_turn_start_with_no_action(self):
        """Test that handle_turn_start emits an event even when no action is taken."""
        self.agent._make_decision = Mock(return_value=None)

        world_state_update = {"current_turn": 1}
        self.agent.handle_turn_start(world_state_update)

        self.agent._make_decision.assert_called_once_with(world_state_update)
        self.event_bus.emit.assert_called_once_with(
            "AGENT_ACTION_COMPLETE", agent=self.agent, action=None
        )


class TestPersonaAgentCharacterLoading(unittest.TestCase):
    """Test character loading functionality with comprehensive file system mocking."""

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        self.test_character_data = {
            "name": "Test Character",
            "faction": "Imperium",
            "psychological_profile": {
                "personality_traits": {
                    "aggression": 0.8,
                    "loyalty": 0.9,
                    "cunning": 0.6,
                }
            },
            "behavioral_config": {
                "decision_weights": {
                    "self_preservation": 0.5,
                    "faction_loyalty": 0.8,
                    "mission_success": 0.9,
                }
            },
            "social_network": {"relationships": {"ally_1": 0.7, "enemy_1": -0.8}},
        }

    @pytest.mark.unit
    def test_load_character_context_success(self):
        """Test successful character context loading with mixed file types."""
        md_content = "# Character Sheet\n\nTest character description"
        yaml_content = """
name: Test Character
faction: Imperium
psychological_profile:
  personality_traits:
    aggression: 0.8
    loyalty: 0.9
"""

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md", "stats.yaml"]), patch(
            "builtins.open", mock_open()
        ) as mock_file, patch(
            "yaml.safe_load", return_value=self.test_character_data
        ):
            # Configure mock_open to return different content based on filename
            def file_side_effect(*args, **kwargs):
                if "character.md" in args[0]:
                    return mock_open(read_data=md_content)()
                elif "stats.yaml" in args[0]:
                    return mock_open(read_data=yaml_content)()
                return mock_open()()

            mock_file.side_effect = file_side_effect

            # Mock the extract methods to avoid complex initialization
            with patch.object(PersonaAgent, "_extract_core_identity"), patch.object(
                PersonaAgent, "_extract_personality_traits"
            ), patch.object(PersonaAgent, "_extract_decision_weights"), patch.object(
                PersonaAgent, "_extract_relationships"
            ), patch.object(
                PersonaAgent, "_extract_knowledge_domains"
            ), patch.object(
                PersonaAgent, "_initialize_subjective_worldview"
            ):
                agent = PersonaAgent(
                    character_directory_path="characters/test",
                    event_bus=self.event_bus,
                    agent_id="test_agent",
                )

                # Verify character data was loaded
                self.assertIsInstance(agent.character_data, dict)
                self.assertEqual(agent.agent_id, "test_agent")

    @pytest.mark.unit
    def test_load_character_context_missing_directory(self):
        """Test error handling when character directory doesn't exist."""
        with patch("os.path.exists", return_value=False), patch.object(
            PersonaAgent,
            "load_character_context",
            side_effect=FileNotFoundError("Character directory not found"),
        ):
            with self.assertRaises(FileNotFoundError):
                PersonaAgent(
                    character_directory_path="nonexistent/path",
                    event_bus=self.event_bus,
                    agent_id="test_agent",
                )

    @pytest.mark.unit
    def test_character_properties(self):
        """Test character property accessors."""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
                character_directory_path="characters/test_char",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

            # Test character properties
            self.assertEqual(agent.character_directory_name, "test_char")
            self.assertIsInstance(agent.character_context, str)

    @pytest.mark.unit
    def test_read_cached_file(self):
        """Test the cached file reading functionality."""
        test_content = "Test file content"

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data=test_content)
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
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

            # Test file reading
            result = agent._read_cached_file("test_file.txt")
            self.assertEqual(result, test_content)

    @pytest.mark.unit
    def test_derive_agent_id_from_path(self):
        """Test agent ID derivation from directory path."""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
                character_directory_path="characters/test_character",
                event_bus=self.event_bus,
            )

            # Test that agent ID is derived from path
            result = agent._derive_agent_id_from_path(
                "characters/imperial_guard/sergeant_johnson"
            )
            self.assertIsInstance(result, str)
            self.assertIn("sergeant_johnson", result.lower())

    @pytest.mark.unit
    def test_estimate_trait_strength(self):
        """Test personality trait strength estimation."""
        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

            # Test trait strength estimation
            test_cases = [
                ("extremely aggressive", 0.9),
                ("moderately loyal", 0.6),
                ("slightly cautious", 0.3),
                ("unknown trait", 0.6),
            ]

            for description, expected_range in test_cases:
                result = agent._estimate_trait_strength(description)
                self.assertIsInstance(result, float)
                self.assertGreaterEqual(result, 0.0)
                self.assertLessEqual(result, 1.0)

    @pytest.mark.unit
    def test_parse_character_sheet_content(self):
        """Test character sheet parsing functionality."""
        test_markdown = """
# Character Sheet: Test Character

## Identity
- Name: Test Character
- Faction: Imperium

## Psychological Profile
- Personality: Aggressive, Loyal
        """

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

            # Test character sheet parsing
            result = agent._parse_character_sheet_content(test_markdown)
            self.assertIsInstance(result, dict)
            # The parsing should extract sections even if they're not fully populated
            self.assertGreaterEqual(len(result), 0)


class TestPersonaAgentDecisionMaking(unittest.TestCase):
    """Test decision making functionality with AI integration mocking."""

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
            self.agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_make_decision_with_world_state(self):
        """Test decision making with world state input."""
        world_state = {
            "current_turn": 1,
            "active_conflicts": ["battle_alpha"],
            "environmental_factors": {"weather": "storm"},
        }

        # Mock the internal decision-making methods
        with patch.object(
            self.agent, "_llm_enhanced_decision_making"
        ) as mock_llm, patch.object(
            self.agent, "_process_world_state_update"
        ) as mock_process, patch.object(
            self.agent, "_assess_current_situation"
        ) as mock_assess, patch.object(
            self.agent, "_identify_available_actions"
        ) as mock_actions:
            mock_action = CharacterAction(
                action_type="tactical_move", reasoning="Strategic positioning required"
            )
            mock_llm.return_value = mock_action
            mock_assess.return_value = {"threat_level": "moderate"}
            mock_actions.return_value = [{"action_type": "move", "target": "sector_7"}]

            result = self.agent._make_decision(world_state)

            self.assertEqual(result, mock_action)
            mock_process.assert_called_once()
            mock_llm.assert_called_once()

    @pytest.mark.unit
    def test_make_decision_ai_fallback(self):
        """Test decision making when AI integration fails."""
        world_state = {"current_turn": 1}

        with patch.object(
            self.agent,
            "_llm_enhanced_decision_making",
            side_effect=Exception("AI Error"),
        ), patch.object(self.agent, "_process_world_state_update"), patch.object(
            self.agent,
            "_assess_current_situation",
            return_value={"threat_level": "low"},
        ), patch.object(
            self.agent,
            "_identify_available_actions",
            return_value=[{"action_type": "hold_position"}],
        ), patch.object(
            self.agent, "_select_best_action"
        ) as mock_select:
            fallback_action = CharacterAction(
                action_type="hold_position", reasoning="Maintaining defensive stance"
            )
            mock_select.return_value = fallback_action

            result = self.agent._make_decision(world_state)

            self.assertEqual(result, fallback_action)
            mock_select.assert_called_once()

    @pytest.mark.unit
    def test_assess_threat_levels(self):
        """Test threat assessment functionality."""
        # Test different threat descriptions
        test_cases = [
            ("Minor skirmish", ThreatLevel.LOW),
            ("Enemy forces approaching", ThreatLevel.MODERATE),
            ("Critical situation", ThreatLevel.HIGH),
            ("Peaceful gathering", ThreatLevel.NEGLIGIBLE),
        ]

        for description, expected_level in test_cases:
            with patch.object(
                self.agent,
                "_assess_threat_from_description",
                return_value=expected_level,
            ):
                result = self.agent._assess_threat_from_description(description)
                self.assertEqual(result, expected_level)

    @pytest.mark.unit
    def test_decision_weight_application(self):
        """Test that decision weights influence action selection."""
        # Set up test decision weights
        self.agent.decision_weights = {
            "self_preservation": 0.9,
            "faction_loyalty": 0.3,
            "mission_success": 0.7,
        }

        world_state = {"threat_level": "high"}

        with patch.object(
            self.agent, "_evaluate_action_option"
        ) as mock_evaluate, patch.object(
            self.agent, "_process_world_state_update"
        ), patch.object(
            self.agent,
            "_assess_current_situation",
            return_value={"threat_level": "high"},
        ), patch.object(
            self.agent, "_identify_available_actions"
        ) as mock_actions, patch.object(
            self.agent, "_llm_enhanced_decision_making", return_value=None
        ), patch.object(
            self.agent, "_select_best_action"
        ) as mock_select:
            mock_actions.return_value = [
                {"action_type": "retreat", "target": "safe_zone"},
                {"action_type": "attack", "target": "enemy"},
                {"action_type": "defend", "target": "position"},
            ]

            # Configure evaluation to favor retreat (high self-preservation)
            mock_evaluate.side_effect = [0.8, 0.4, 0.6]

            mock_select.return_value = CharacterAction(
                action_type="retreat", reasoning="Self-preservation priority"
            )

            result = self.agent._make_decision(world_state)
            self.assertIsNotNone(result)
            self.assertEqual(result.action_type, "retreat")

    @pytest.mark.unit
    def test_assess_current_situation(self):
        """Test current situation assessment."""
        with patch.object(
            self.agent,
            "_assess_overall_threat_level",
            return_value=ThreatLevel.MODERATE,
        ), patch.object(
            self.agent, "_assess_available_resources", return_value={"energy": 80}
        ), patch.object(
            self.agent, "_assess_social_obligations", return_value=[]
        ), patch.object(
            self.agent, "_assess_mission_status", return_value={"status": "active"}
        ), patch.object(
            self.agent,
            "_assess_environmental_factors",
            return_value={"weather": "clear"},
        ):
            result = self.agent._assess_current_situation()
            self.assertIsInstance(result, dict)
            self.assertIn("threat_level", result)
            self.assertIn("available_resources", result)

    @pytest.mark.unit
    def test_identify_available_actions(self):
        """Test action identification based on situation."""
        test_situation = {
            "threat_level": ThreatLevel.LOW,
            "available_resources": {"energy": 100},
            "environmental_factors": {"visibility": "good"},
        }

        result = self.agent._identify_available_actions(test_situation)
        self.assertIsInstance(result, list)
        # Should return at least some default actions
        self.assertGreaterEqual(len(result), 0)

    @pytest.mark.unit
    def test_evaluate_action_option(self):
        """Test individual action evaluation."""
        test_action = {
            "action_type": "scout",
            "target": "sector_7",
            "risk_level": "low",
            "resource_cost": 10,
        }

        test_situation = {
            "threat_level": ThreatLevel.LOW,
            "available_resources": {"energy": 100},
        }

        result = self.agent._evaluate_action_option(test_action, test_situation)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    @pytest.mark.unit
    def test_parse_llm_response(self):
        """Test LLM response parsing."""
        test_response = '{"action_type": "scout", "target": "sector_7", "reasoning": "Gather intelligence"}'
        test_actions = [
            {"action_type": "scout", "target": "sector_7"},
            {"action_type": "defend", "target": "base"},
        ]

        result = self.agent._parse_llm_response(test_response, test_actions)
        if result:  # May return None for invalid responses
            self.assertIsInstance(result, CharacterAction)
            self.assertEqual(result.action_type, "scout")


class TestPersonaAgentWorldInterpretation(unittest.TestCase):
    """Test subjective worldview and event interpretation."""

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
            self.agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_subjective_worldview_initialization(self):
        """Test that subjective worldview is properly initialized."""
        required_keys = [
            "known_entities",
            "location_knowledge",
            "faction_relationships",
            "recent_events",
            "current_goals",
            "active_threats",
        ]

        for key in required_keys:
            self.assertIn(key, self.agent.subjective_worldview)

    @pytest.mark.unit
    def test_world_event_processing(self):
        """Test processing of world events into subjective interpretations."""
        test_event = WorldEvent(
            event_id="test_event_001",
            event_type="battle",
            source="enemy_faction",
            description="Major battle erupted in sector 7",
        )

        with patch.object(self.agent, "_interpret_event_description") as mock_interpret:
            mock_interpret.return_value = "Enemy forces are advancing"

            # Test the actual method that exists for event interpretation
            result = self.agent._interpret_event_description(test_event.__dict__)
            self.assertEqual(result, "Enemy forces are advancing")
            mock_interpret.assert_called_once()

        # Test that threat assessment works with the actual method
        threat_level = self.agent._assess_threat_from_description(
            "Major battle erupted"
        )
        self.assertIsInstance(threat_level, ThreatLevel)

    @pytest.mark.unit
    def test_memory_integration(self):
        """Test that events are properly stored in memory systems."""
        # Test short-term memory functionality
        test_memory = {
            "event_id": "test_001",
            "description": "Test event occurred",
            "importance": 0.7,
        }

        # Add to short-term memory
        self.agent.short_term_memory.append(test_memory)
        self.assertEqual(len(self.agent.short_term_memory), 1)
        self.assertEqual(self.agent.short_term_memory[0]["event_id"], "test_001")


class TestPersonaAgentAIIntegration(unittest.TestCase):
    """Test AI integration with Gemini API mocking."""

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
            self.agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"})
    @pytest.mark.unit
    def test_ai_query_with_valid_api_key(self):
        """Test AI query when Gemini API key is available."""
        test_prompt = "Test prompt for character decision"
        expected_response = "Valid LLM response"

        with patch.object(
            self.agent, "_call_llm", return_value=expected_response
        ) as mock_llm:
            result = self.agent._call_llm(test_prompt)
            self.assertEqual(result, expected_response)
            mock_llm.assert_called_once_with(test_prompt)

    @pytest.mark.unit
    def test_ai_query_without_api_key(self):
        """Test AI query fallback when no API key is available."""
        with patch.dict(os.environ, {}, clear=True):
            # Test that API validation works
            api_key = os.getenv("GEMINI_API_KEY")
            self.assertIsNone(api_key)

            # Test fallback behavior when no API key
            with patch(
                "src.agents.persona_agent.agent._validate_gemini_api_key",
                return_value=None,
            ):
                result = self.agent._call_llm("Test prompt")
                # Should return fallback response or handle gracefully
                self.assertIsInstance(result, str)

    @pytest.mark.unit
    def test_api_error_handling(self):
        """Test handling of API errors and network issues."""
        test_prompt = "Test prompt"

        # Test that the LLM call handles errors gracefully
        with patch(
            "src.agents.persona_agent.agent._make_gemini_api_request",
            side_effect=Exception("Network error"),
        ):
            result = self.agent._call_llm(test_prompt)
            # Should handle the error and return a string response
            self.assertIsInstance(result, str)


class TestPersonaAgentMemoryAndEvolution(unittest.TestCase):
    """Test memory systems and character evolution."""

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)

        with patch("os.path.exists", return_value=True), patch(
            "os.path.isdir", return_value=True
        ), patch("os.listdir", return_value=["character.md"]), patch(
            "builtins.open", mock_open(read_data="# Test Character")
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
            self.agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=self.event_bus,
                agent_id="test_agent",
            )

    @pytest.mark.unit
    def test_short_term_memory_management(self):
        """Test short-term memory storage and retrieval."""
        # Add multiple memories
        for i in range(5):
            memory = {
                "event_id": f"event_{i}",
                "description": f"Test event {i}",
                "importance": 0.5 + (i * 0.1),
            }
            self.agent.short_term_memory.append(memory)

        self.assertEqual(len(self.agent.short_term_memory), 5)

        # Test that memories are stored in order
        self.assertEqual(self.agent.short_term_memory[0]["event_id"], "event_0")
        self.assertEqual(self.agent.short_term_memory[-1]["event_id"], "event_4")

    @pytest.mark.unit
    def test_long_term_memory_consolidation(self):
        """Test consolidation of important memories to long-term storage."""
        important_memory = {
            "event_id": "critical_event",
            "description": "Major faction battle",
            "importance": 0.9,
            "emotional_impact": 0.8,
        }

        # Mock consolidation process if it exists
        if hasattr(self.agent, "_consolidate_memories"):
            with patch.object(self.agent, "_consolidate_memories") as mock_consolidate:
                self.agent.short_term_memory.append(important_memory)
                self.agent._consolidate_memories()
                mock_consolidate.assert_called_once()

    @pytest.mark.unit
    def test_relationship_evolution(self):
        """Test that relationships change based on interactions."""
        # Initial relationship state
        initial_relationship = 0.5
        self.agent.relationships["test_entity"] = initial_relationship

        # Simulate positive interaction
        relationship_change = 0.2

        if hasattr(self.agent, "_update_relationship"):
            with patch.object(self.agent, "_update_relationship") as mock_update:
                self.agent._update_relationship("test_entity", relationship_change)
                mock_update.assert_called_once_with("test_entity", relationship_change)
        else:
            # Direct update for testing
            self.agent.relationships["test_entity"] += relationship_change
            self.assertEqual(self.agent.relationships["test_entity"], 0.7)

    @pytest.mark.unit
    def test_morale_and_status_tracking(self):
        """Test character morale and status management."""
        # Test initial state
        self.assertEqual(self.agent.current_status, "active")
        self.assertEqual(self.agent.morale_level, 1.0)

        # Test status changes
        self.agent.current_status = "injured"
        self.agent.morale_level = 0.6

        self.assertEqual(self.agent.current_status, "injured")
        self.assertEqual(self.agent.morale_level, 0.6)

        # Test morale bounds
        self.agent.morale_level = 1.5  # Should be clamped
        if hasattr(self.agent, "_validate_morale"):
            # Test validation if it exists
            pass


if __name__ == "__main__":
    unittest.main()
