import os
import shutil
import sys
import unittest
from unittest.mock import patch

import pytest
import yaml

# HACK: Force project root onto path to fix persistent import issue
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared_types import CharacterAction
from src.agents.persona_agent.protocols import ThreatLevel
from src.event_bus import EventBus
from src.persona_agent import PersonaAgent


class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        """Set up a test character and a PersonaAgent instance."""
        self.test_dir = "tests/temp_test_character"
        os.makedirs(self.test_dir, exist_ok=True)

        # Create dummy character files
        with open(os.path.join(self.test_dir, "character_sheet.md"), "w") as f:
            f.write(
                """
# Character Sheet: Test Character

## Core Identity
**Name**: Test Character
**Faction**: Imperium

## Psychological Profile
**Personality Traits**:
**Aggressive**: Strong
**Cautious**: Weak

## Behavioral Configuration
**Decision-Making Weights**:
**self_preservation**: 0.3
**faction_loyalty**: 0.9
"""
            )
        with open(os.path.join(self.test_dir, "personality.yaml"), "w") as f:
            yaml.dump({"personality_traits": {"aggressive": 0.8, "cautious": 0.2}}, f)

        self.event_bus = EventBus()
        self.agent = PersonaAgent(
            character_directory_path=self.test_dir, event_bus=self.event_bus
        )

    def tearDown(self):
        """Clean up the test character directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    @patch("src.persona_agent._make_gemini_api_request")
    @pytest.mark.integration
    def test_llm_decision_making_returns_action(self, mock_gemini_request):
        """Test _llm_enhanced_decision_making returns a CharacterAction for a valid response."""
        # Arrange
        mock_response = "ACTION: 2\nTARGET: enemy_forces\nREASONING: A decisive strike is necessary."
        mock_gemini_request.return_value = mock_response

        world_state = {"recent_events": [], "entity_updates": {}}
        situation_assessment = {"threat_level": ThreatLevel.HIGH}
        available_actions = [{"type": "observe"}, {"type": "attack"}]

        # Act
        with patch(
            "src.persona_agent._validate_gemini_api_key", return_value="fake_key"
        ):
            action = self.agent._llm_enhanced_decision_making(
                world_state, situation_assessment, available_actions
            )

        # Assert
        self.assertIsInstance(action, CharacterAction)
        self.assertEqual(action.action_type, "attack")
        self.assertEqual(action.target, "enemy_forces")
        self.assertEqual(
            action.reasoning, "[LLM-Guided] A decisive strike is necessary."
        )
        mock_gemini_request.assert_called_once()

    @patch("src.persona_agent.PersonaAgent._call_llm")
    @pytest.mark.integration
    def test_llm_decision_making_handles_invalid_response(self, mock_call_llm):
        """Test _llm_enhanced_decision_making returns None for an invalid LLM response."""
        # Arrange
        mock_call_llm.return_value = "This is not a valid action response."

        world_state = {"recent_events": [], "entity_updates": {}}
        situation_assessment = {"threat_level": ThreatLevel.MODERATE}
        available_actions = [{"type": "observe"}, {"type": "move"}]

        # Act
        action = self.agent._llm_enhanced_decision_making(
            world_state, situation_assessment, available_actions
        )

        # Assert
        self.assertIsNone(action)
        mock_call_llm.assert_called_once()

    @patch("src.persona_agent._validate_gemini_api_key", return_value=None)
    @patch("src.persona_agent._generate_fallback_response")
    @pytest.mark.integration
    def test_llm_uses_fallback_when_no_api_key(self, mock_fallback, mock_validate_key):
        """Test the agent uses the fallback mechanism when the API key is not available."""
        # Arrange
        fallback_response = (
            "ACTION: 1\nTARGET: hostile_forces\nREASONING: Fallback response."
        )
        mock_fallback.return_value = fallback_response

        world_state = {"recent_events": [], "entity_updates": {}}
        situation_assessment = {"threat_level": ThreatLevel.HIGH}
        available_actions = [{"type": "attack"}, {"type": "retreat"}]

        # Act
        action = self.agent._llm_enhanced_decision_making(
            world_state, situation_assessment, available_actions
        )

        # Assert
        self.assertIsInstance(action, CharacterAction)
        self.assertEqual(action.action_type, "attack")
        self.assertEqual(action.target, "hostile_forces")
        self.assertEqual(action.reasoning, "[LLM-Guided] Fallback response.")
        mock_validate_key.assert_called_once()
        mock_fallback.assert_called_once()

    @patch("src.persona_agent._make_gemini_api_request")
    @pytest.mark.integration
    def test_llm_decision_making_handles_api_failure_and_uses_fallback(
        self, mock_gemini_request
    ):
        """Test the agent uses fallback logic when the Gemini API call fails."""
        # Arrange
        mock_gemini_request.return_value = None  # Simulate API failure

        world_state = {"recent_events": [], "entity_updates": {}}
        situation_assessment = {"threat_level": ThreatLevel.HIGH}
        available_actions = [{"type": "attack"}, {"type": "retreat"}]

        # Act
        with patch(
            "src.persona_agent._validate_gemini_api_key", return_value="fake_key"
        ):
            with patch(
                "src.persona_agent._generate_fallback_response"
            ) as mock_fallback:
                fallback_response = "ACTION: 1\nTARGET: hostile_forces\nREASONING: Fallback response from API failure."
                mock_fallback.return_value = fallback_response

                action = self.agent._llm_enhanced_decision_making(
                    world_state, situation_assessment, available_actions
                )

                # Assert
                self.assertIsInstance(action, CharacterAction)
                self.assertEqual(action.action_type, "attack")
                self.assertEqual(
                    action.reasoning, "[LLM-Guided] Fallback response from API failure."
                )
                mock_fallback.assert_called_once()

        mock_gemini_request.assert_called_once()

    @patch("src.persona_agent._make_gemini_api_request")
    @pytest.mark.integration
    def test_llm_decision_making_handles_observe_action(self, mock_gemini_request):
        """Test _llm_enhanced_decision_making returns None when LLM chooses to observe."""
        # Arrange
        mock_response = "ACTION: 1\nTARGET: none\nREASONING: I need more information."
        mock_gemini_request.return_value = mock_response

        world_state = {"recent_events": [], "entity_updates": {}}
        situation_assessment = {"threat_level": ThreatLevel.LOW}
        available_actions = [{"type": "observe"}, {"type": "move"}]

        # Act
        with patch(
            "src.persona_agent._validate_gemini_api_key", return_value="fake_key"
        ):
            action = self.agent._llm_enhanced_decision_making(
                world_state, situation_assessment, available_actions
            )

        # Assert
        self.assertIsNone(action)
        mock_gemini_request.assert_called_once()


if __name__ == "__main__":
    unittest.main()
