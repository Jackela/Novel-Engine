import unittest
from unittest.mock import Mock

from shared_types import CharacterAction
from src.agents.director_agent import DirectorAgent
from src.event_bus import EventBus
from src.persona_agent import PersonaAgent


class TestDirectorAgent(unittest.TestCase):

    def setUp(self):
        self.event_bus = Mock(spec=EventBus)
        self.director = DirectorAgent(event_bus=self.event_bus)

    def test_initialization(self):
        """Test that the DirectorAgent initializes correctly and subscribes to events."""
        self.assertEqual(self.director.event_bus, self.event_bus)
        self.event_bus.subscribe.assert_called_once_with(
            "AGENT_ACTION_COMPLETE", self.director._bus_agent_action_handler
        )

    def test_run_turn_emits_event(self):
        """Test that run_turn emits a TURN_START event."""
        # Register a mock agent to prevent the method from exiting early
        mock_agent = Mock(spec=PersonaAgent)
        mock_agent.handle_turn_start = Mock()
        mock_agent.agent_id = "test_agent"
        mock_agent.character_data = {}
        mock_agent.subjective_worldview = {}
        self.director.register_agent(mock_agent)

        self.director.run_turn()
        self.event_bus.emit.assert_called_once_with(
            "TURN_START", world_state_update=unittest.mock.ANY
        )

    def test_handle_agent_action(self):
        """Test that _handle_agent_action correctly processes an agent's action."""
        # Create a mock agent and action
        mock_agent = Mock(spec=PersonaAgent)
        mock_agent.agent_id = "test_agent"
        mock_agent.character_data = {"name": "Test Agent"}

        mock_action = Mock(spec=CharacterAction)
        mock_action.action_type = "test_action"
        mock_action.reasoning = "Test reasoning"

        # Mock the log_event method to prevent file I/O
        self.director.log_event = Mock()

        # Call the handler
        self.director._handle_agent_action(mock_agent, mock_action)

        # Assert that the action was logged
        self.director.log_event.assert_called_once()
        self.assertEqual(self.director.total_actions_processed, 1)

    def test_handle_agent_action_with_no_action(self):
        """Test that _handle_agent_action handles cases where the agent does nothing."""
        mock_agent = Mock(spec=PersonaAgent)
        mock_agent.agent_id = "test_agent"
        mock_agent.character_data = {"name": "Test Agent"}

        self.director.log_event = Mock()
        self.director._handle_agent_action(mock_agent, None)
        self.director.log_event.assert_called_once()
        self.assertEqual(self.director.total_actions_processed, 0)


if __name__ == "__main__":
    unittest.main()
