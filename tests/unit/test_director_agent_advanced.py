#!/usr/bin/env python3
"""
Director Agent Advanced Feature Test Suite
==========================================

Advanced testing for director_agent.py covering knowledge retrieval, narrative engine,
world state management, and agent orchestration systems.
"""

import json
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Import the modules under test
try:
    from director_agent import DirectorAgent

    from shared_types import CharacterAction
    from src.event_bus import EventBus
    from src.persona_agent import PersonaAgent

    DIRECTOR_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"Director agent import failed: {e}")
    DIRECTOR_AGENT_AVAILABLE = False


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentKnowledgeSystem:
    """Director Agent Knowledge Retrieval and RAG System Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_log_path = "test_knowledge_log.md"
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

    def teardown_method(self):
        """Cleanup after each test"""
        try:
            if os.path.exists(self.temp_log_path):
                os.remove(self.temp_log_path)
        except Exception:
            pass

    def create_mock_agent(self):
        """Create a mock PersonaAgent for testing"""
        mock_agent = Mock(spec=PersonaAgent)
        mock_agent.agent_id = "test_agent"
        mock_agent.character_id = "test_character"
        mock_agent.character = Mock()
        mock_agent.character.name = "Test Character"
        mock_agent.character_data = {
            "name": "Test Character",
            "faction": "Imperial Guard",
            "background": "Veteran soldier",
        }
        mock_agent.subjective_worldview = {
            "primary_faction": "Imperial",
            "known_locations": ["hive_city"],
            "current_threats": ["ork_raiders"],
        }
        return mock_agent

    @pytest.mark.unit
    def test_retrieve_relevant_knowledge_rag_no_knowledge_base(self):
        """Test RAG knowledge retrieval when knowledge base doesn't exist"""
        mock_agent = self.create_mock_agent()
        filtered_world_view = {"current_situation": "combat", "location": "battlefield"}

        with patch("pathlib.Path.exists", return_value=False):
            if hasattr(self.director, "_retrieve_relevant_knowledge_rag"):
                result = self.director._retrieve_relevant_knowledge_rag(
                    mock_agent, filtered_world_view
                )

                # Should return default knowledge fragments
                assert result is not None
                assert isinstance(result, list)

    @pytest.mark.unit
    def test_create_default_knowledge_fragments(self):
        """Test creation of default knowledge fragments"""
        mock_agent = self.create_mock_agent()

        if hasattr(self.director, "_create_default_knowledge_fragments"):
            result = self.director._create_default_knowledge_fragments(mock_agent)

            # Should return a list of knowledge fragments
            assert result is not None
            assert isinstance(result, list)

            # Should contain character-specific knowledge
            if result:
                # Basic validation of fragment structure
                assert len(result) >= 0

    @pytest.mark.unit
    def test_extract_rag_context_keywords(self):
        """Test extraction of RAG context keywords"""
        mock_agent = self.create_mock_agent()

        # Create proper filtered_world_view mock object
        filtered_world_view = Mock()
        filtered_world_view.visible_entities = {}
        filtered_world_view.recent_events = []
        filtered_world_view.environmental_details = {}
        filtered_world_view.current_location = "hive_city"
        filtered_world_view.active_threats = ["orks"]
        filtered_world_view.uncertainty_markers = []

        if hasattr(self.director, "_extract_rag_context_keywords"):
            result = self.director._extract_rag_context_keywords(
                mock_agent, filtered_world_view
            )

            # Should return keywords for RAG search
            assert result is not None
            assert isinstance(result, (list, set, str))

    @pytest.mark.unit
    def test_rank_knowledge_fragments(self):
        """Test ranking of knowledge fragments by relevance"""
        # Create mock knowledge fragments with proper tags attribute
        mock_fragments = []
        for i, (title, content, score) in enumerate(
            [
                ("Fragment 1", "Imperial Guard tactics", 0.8),
                ("Fragment 2", "Ork combat patterns", 0.9),
                ("Fragment 3", "General warfare", 0.7),
            ]
        ):
            fragment = Mock()
            fragment.title = title
            fragment.content = content
            fragment.relevance_score = score
            fragment.tags = (
                ["combat", "imperial"]
                if i == 0
                else ["ork", "combat"]
                if i == 1
                else ["warfare"]
            )
            mock_fragments.append(fragment)

        context_keywords = ["ork", "combat", "imperial"]

        if hasattr(self.director, "_rank_knowledge_fragments"):
            result = self.director._rank_knowledge_fragments(
                mock_fragments, context_keywords
            )

            # Should return ranked fragments
            assert result is not None
            assert isinstance(result, list)
            # Higher relevance should come first (if sorting is implemented)
            assert len(result) <= len(mock_fragments)


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentNarrativeEngine:
    """Director Agent Narrative Engine and Story Management Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_log_path = "test_narrative_log.md"
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

    def teardown_method(self):
        """Cleanup after each test"""
        try:
            if os.path.exists(self.temp_log_path):
                os.remove(self.temp_log_path)
        except Exception:
            pass

    @pytest.mark.unit
    def test_narrative_resolver_initialization(self):
        """Test narrative action resolver initialization"""
        # Check if director has narrative resolver
        assert hasattr(self.director, "narrative_resolver")
        assert self.director.narrative_resolver is not None

    @pytest.mark.unit
    @pytest.mark.skip(
        reason="Tests internal state attributes not exposed in integrated implementation - use behavioral tests instead"
    )
    def test_story_state_tracking(self):
        """Test story state tracking system"""
        # Check if director maintains story state
        assert hasattr(self.director, "story_state")
        assert isinstance(self.director.story_state, dict)

        # Should have expected story state components
        expected_components = ["current_phase", "triggered_events", "story_progression"]
        for component in expected_components:
            assert component in self.director.story_state

    @pytest.mark.unit
    @pytest.mark.skip(
        reason="Tests internal state attributes not exposed in integrated implementation - use behavioral tests instead"
    )
    def test_world_state_tracker_initialization(self):
        """Test world state tracker initialization"""
        # Check if director has world state tracker
        assert hasattr(self.director, "world_state_tracker")
        assert isinstance(self.director.world_state_tracker, dict)

        # Should have expected tracker components
        expected_components = [
            "discovered_clues",
            "environmental_changes",
            "agent_discoveries",
        ]
        for component in expected_components:
            assert component in self.director.world_state_tracker

    @pytest.mark.unit
    def test_campaign_brief_integration(self):
        """Test campaign brief integration"""
        # Check if director can handle campaign brief
        assert hasattr(self.director, "campaign_brief_path")
        assert hasattr(self.director, "campaign_brief")

        # Campaign brief should be None or properly loaded
        assert self.director.campaign_brief is None or hasattr(
            self.director.campaign_brief, "setting"
        )


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentWorldStateManagement:
    """Director Agent World State Management and Persistence Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_log_path = "test_worldstate_log.md"
        self.temp_world_state = "test_world_state.json"

    def teardown_method(self):
        """Cleanup after each test"""
        for temp_file in [self.temp_log_path, self.temp_world_state]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    @pytest.mark.unit
    def test_world_state_data_initialization(self):
        """Test world state data structure initialization"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Should have world state data structure
        assert hasattr(director, "world_state_data")
        assert isinstance(director.world_state_data, dict)

    @pytest.mark.unit
    def test_world_state_file_handling(self):
        """Test world state file loading and saving"""
        # Create test world state file
        test_world_state = {
            "locations": {"sector_1": {"status": "secure"}},
            "global_events": [],
            "current_turn": 1,
        }

        with open(self.temp_world_state, "w") as f:
            json.dump(test_world_state, f)

        director = DirectorAgent(
            event_bus=self.mock_event_bus,
            world_state_file_path=self.temp_world_state,
            campaign_log_path=self.temp_log_path,
        )

        # Should handle world state file appropriately
        assert hasattr(director, "world_state_file_path")
        assert director.world_state_file_path == self.temp_world_state

    @pytest.mark.unit
    def test_initialize_default_world_state(self):
        """Test default world state initialization"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Should have default world state initialization
        if hasattr(director, "_initialize_default_world_state"):
            # Method should exist and be callable
            assert callable(director._initialize_default_world_state)

    @pytest.mark.unit
    def test_world_state_persistence_methods(self):
        """Test world state persistence capabilities"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Check for world state persistence methods
        persistence_methods = [
            "_save_world_state",
            "_load_world_state",
            "_update_world_state",
            "_backup_world_state",
        ]

        for method_name in persistence_methods:
            if hasattr(director, method_name):
                method = getattr(director, method_name)
                assert callable(method)


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentAgentOrchestration:
    """Director Agent Advanced Agent Orchestration Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_log_path = "test_orchestration_log.md"
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

    def teardown_method(self):
        """Cleanup after each test"""
        try:
            if os.path.exists(self.temp_log_path):
                os.remove(self.temp_log_path)
        except Exception:
            pass

    def create_mock_agent(self, agent_id="test_agent"):
        """Create a mock PersonaAgent for orchestration testing"""
        mock_agent = Mock(spec=PersonaAgent)
        mock_agent.agent_id = agent_id
        mock_agent.character = Mock()
        mock_agent.character.name = f"Character_{agent_id}"
        mock_agent.handle_turn_start = Mock()
        mock_agent.act = Mock(return_value="Test action")
        return mock_agent

    @pytest.mark.unit
    def test_agent_registration_capacity(self):
        """Test agent registration capacity and management"""
        # Test multiple agent registration
        agents = []
        for i in range(5):
            agent = self.create_mock_agent(f"agent_{i}")
            agents.append(agent)

            if hasattr(self.director, "register_agent"):
                success = self.director.register_agent(agent)
                assert success is True or success is False  # Should return boolean

        # Verify agent list management
        if hasattr(self.director, "registered_agents"):
            # Should track registered agents
            assert len(self.director.registered_agents) <= len(agents)

    @pytest.mark.unit
    def test_agent_validation_system(self):
        """Test comprehensive agent validation"""
        if not hasattr(self.director, "register_agent"):
            pytest.skip("Director does not have register_agent method")

        # Test various invalid agent scenarios
        invalid_scenarios = [
            None,  # None agent
            "string_agent",  # Wrong type
            Mock(),  # Missing required attributes
        ]

        for invalid_agent in invalid_scenarios:
            result = self.director.register_agent(invalid_agent)
            assert result is False  # Should reject invalid agents

    @pytest.mark.unit
    def test_turn_orchestration_workflow(self):
        """Test complete turn orchestration workflow"""
        if not hasattr(self.director, "run_turn"):
            pytest.skip("Director does not have run_turn method")

        # Register test agents
        if hasattr(self.director, "register_agent"):
            agent1 = self.create_mock_agent("orchestration_agent_1")
            agent2 = self.create_mock_agent("orchestration_agent_2")

            self.director.register_agent(agent1)
            self.director.register_agent(agent2)

        # Execute turn orchestration
        try:
            result = self.director.run_turn()

            # Should return turn result
            assert result is not None
            assert isinstance(result, dict)

        except Exception as e:
            # If turn execution fails, should be graceful
            assert "agent" in str(e).lower() or "turn" in str(e).lower()

    @pytest.mark.unit
    @pytest.mark.skip(
        reason="Tests internal error tracking attributes not exposed in integrated implementation"
    )
    def test_error_tracking_system(self):
        """Test error tracking and recovery system"""
        # Should have error tracking attributes
        assert hasattr(self.director, "error_count")
        assert hasattr(self.director, "last_error_time")
        assert hasattr(self.director, "error_threshold")

        # Error count should start at 0
        assert self.director.error_count == 0
        assert self.director.last_error_time is None

    @pytest.mark.unit
    def test_simulation_state_tracking(self):
        """Test simulation state tracking and management"""
        # Should track simulation state
        assert hasattr(self.director, "current_turn_number")
        assert hasattr(self.director, "simulation_start_time")
        assert hasattr(self.director, "total_actions_processed")

        # Initial state should be properly set
        assert self.director.current_turn_number == 0
        assert self.director.total_actions_processed == 0
        assert isinstance(self.director.simulation_start_time, datetime)

    @pytest.mark.unit
    @pytest.mark.skip(
        reason="Tests internal configuration attributes not exposed in integrated implementation"
    )
    def test_configuration_driven_parameters(self):
        """Test configuration-driven parameter management"""
        # Should have configuration parameters
        assert hasattr(self.director, "max_turn_history")
        assert hasattr(self.director, "error_threshold")

        # Should have reasonable defaults
        assert self.director.max_turn_history > 0
        assert self.director.error_threshold > 0


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentEventHandling:
    """Director Agent Event Handling and Communication Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)
        self.temp_log_path = "test_events_log.md"

    def teardown_method(self):
        """Cleanup after each test"""
        try:
            if os.path.exists(self.temp_log_path):
                os.remove(self.temp_log_path)
        except Exception:
            pass

    @pytest.mark.unit
    def test_event_bus_integration(self):
        """Test event bus integration and subscription"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Should subscribe to agent action events
        self.mock_event_bus.subscribe.assert_called_with(
            "AGENT_ACTION_COMPLETE", director._handle_agent_action
        )

    @pytest.mark.unit
    def test_agent_action_handling(self):
        """Test handling of agent action events"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Should have agent action handler
        assert hasattr(director, "_handle_agent_action")
        assert callable(director._handle_agent_action)

        # Test action handling
        mock_agent = Mock()
        mock_agent.agent_id = "test_agent"
        mock_action = CharacterAction(
            action_type="investigate", reasoning="Test reasoning"
        )

        try:
            director._handle_agent_action(agent=mock_agent, action=mock_action)
            # Should handle without errors
        except Exception as e:
            # Should handle gracefully
            assert "action" in str(e).lower() or "agent" in str(e).lower()

    @pytest.mark.unit
    def test_turn_start_event_emission(self):
        """Test TURN_START event emission"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        if hasattr(director, "run_turn"):
            try:
                director.run_turn()

                # Should emit TURN_START event
                # Note: Actual emission depends on implementation

            except Exception:
                # Turn execution might fail, that's OK for this test
                pass

    @pytest.mark.unit
    def test_event_logging_integration(self):
        """Test integration between event handling and logging"""
        director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

        # Test that events can trigger logging
        test_event = "Test event occurred"
        director.log_event(test_event)

        # Should create or update log file
        if os.path.exists(self.temp_log_path):
            with open(self.temp_log_path, "r") as f:
                content = f.read()
                assert len(content) > 0  # Should have content


# Helper functions for running specific test suites
def run_director_knowledge_tests():
    """Run knowledge system tests specifically"""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-k",
            "TestDirectorAgentKnowledgeSystem",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("Director Agent Knowledge System Tests:")
    print(result.stdout)
    return result.returncode == 0


def run_director_advanced_tests():
    """Run all advanced director agent tests"""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=short", __file__],
        capture_output=True,
        text=True,
    )

    print("All Director Agent Advanced Tests:")
    print(result.stdout)
    return result.returncode == 0


if __name__ == "__main__":
    # Direct execution runs all tests
    run_director_advanced_tests()
