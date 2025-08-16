import unittest
from unittest.mock import Mock, patch
from src.persona_agent import PersonaAgent
from src.event_bus import EventBus
from shared_types import CharacterAction

class TestPersonaAgent(unittest.TestCase):

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        # Mock the file system operations
        with patch('os.path.isdir', return_value=True), \
             patch('os.listdir', return_value=['character.md']), \
             patch('builtins.open', unittest.mock.mock_open(read_data='# Character Sheet: Test Agent')):
            self.agent = PersonaAgent(character_directory_path='characters/test', event_bus=self.event_bus, agent_id='test_agent')

    def test_initialization_subscribes_to_turn_start(self):
        """Test that the PersonaAgent subscribes to the TURN_START event on initialization."""
        self.event_bus.subscribe.assert_called_once_with("TURN_START", self.agent.handle_turn_start)

    def test_handle_turn_start_emits_action(self):
        """Test that handle_turn_start calls _make_decision and emits an AGENT_ACTION_COMPLETE event."""
        # Mock the _make_decision method to return a specific action
        mock_action = CharacterAction(action_type="test", reasoning="test reasoning")
        self.agent._make_decision = Mock(return_value=mock_action)

        world_state_update = {'current_turn': 1}
        self.agent.handle_turn_start(world_state_update)

        # Verify that _make_decision was called
        self.agent._make_decision.assert_called_once_with(world_state_update)

        # Verify that AGENT_ACTION_COMPLETE was emitted
        self.event_bus.emit.assert_called_once_with("AGENT_ACTION_COMPLETE", agent=self.agent, action=mock_action)

    def test_handle_turn_start_with_no_action(self):
        """Test that handle_turn_start emits an event even when no action is taken."""
        self.agent._make_decision = Mock(return_value=None)

        world_state_update = {'current_turn': 1}
        self.agent.handle_turn_start(world_state_update)

        self.agent._make_decision.assert_called_once_with(world_state_update)
        self.event_bus.emit.assert_called_once_with("AGENT_ACTION_COMPLETE", agent=self.agent, action=None)

if __name__ == '__main__':
    unittest.main()
