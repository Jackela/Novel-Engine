import pytest
import unittest
from unittest.mock import MagicMock, patch

from director_agent import DirectorAgent

from src.event_bus import EventBus
from src.persona_agent import PersonaAgent



pytestmark = pytest.mark.skip(reason="Skipped: imports temporary root-level files deleted in .gitignore cleanup")

class TestEventIntegration(unittest.TestCase):

    def test_full_turn_event_flow(self):
        """
        Tests the full event flow for a single turn, ensuring agents
        and the director communicate correctly through the event bus.
        """
        event_bus = EventBus()

        # Mock file system operations for agent creation
        with patch("os.path.isdir", return_value=True), patch(
            "os.listdir", return_value=["character.md"]
        ), patch(
            "builtins.open",
            unittest.mock.mock_open(read_data="# Character Sheet: Test Agent"),
        ):

            # Instantiate the agents and director with the real event bus
            director = DirectorAgent(event_bus=event_bus)
            agent = PersonaAgent(
                character_directory_path="characters/test",
                event_bus=event_bus,
                agent_id="test_agent",
            )

            # Mock the methods we want to spy on
            agent.handle_turn_start = MagicMock()
            director._handle_agent_action = MagicMock()

            # Re-subscribe the mocked methods
            event_bus.subscribe("TURN_START", agent.handle_turn_start)
            event_bus.subscribe("AGENT_ACTION_COMPLETE", director._handle_agent_action)

            # Register the agent
            director.register_agent(agent)

            # Run the turn
            director.run_turn()

            # Assert that the agent received the TURN_START event
            agent.handle_turn_start.assert_called_once()

            # To test the full loop, we need to manually call the agent's turn handling
            # because the event bus is synchronous in this test setup.
            # In a real async environment, this would happen automatically.
            world_state_update = director._prepare_world_state_for_turn()
            agent.handle_turn_start(world_state_update)

            # Now, check that the director received the action
            # This is a bit of a simplification, as we are not checking the action content
            director._handle_agent_action.assert_called_once()


if __name__ == "__main__":
    unittest.main()
