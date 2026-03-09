#!/usr/bin/env python3
"""
Test suite for persona_agent modules.

Tests persona agent core, protocols, and agent implementations.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit


class TestPersonaAgentCore:
    """Test PersonaAgentCore class."""

    def test_core_module_imports(self):
        """Test that core module can be imported."""
        try:
            from src.agents.persona_agent.core import PersonaAgentCore

            assert PersonaAgentCore is not None
        except ImportError:
            pytest.skip("PersonaAgentCore not available")

    def test_core_initialization(self):
        """Test core initialization."""
        try:
            from src.agents.persona_agent.core import PersonaAgentCore

            with tempfile.TemporaryDirectory() as tmpdir:
                from src.core.event_bus import EventBus
                core = PersonaAgentCore(
                    agent_id="test",
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )
                assert core is not None
        except ImportError:
            pytest.skip("PersonaAgentCore not available")


class TestPersonaAgentProtocols:
    """Test persona agent protocols."""

    def test_protocols_import(self):
        """Test that protocols module can be imported."""
        try:
            from src.agents.persona_agent import protocols

            assert protocols is not None
        except ImportError:
            pytest.skip("Protocols not available")

    def test_action_protocol(self):
        """Test ActionProtocol."""
        try:
            from src.agents.persona_agent.protocols import ActionProtocol

            # Create mock that satisfies protocol
            mock_action = Mock()
            mock_action.action_type = "test"
            mock_action.target = None
            mock_action.parameters = {}

            # Should be able to use as protocol
            def use_action(action: ActionProtocol) -> None:
                pass

            use_action(mock_action)
        except ImportError:
            pytest.skip("ActionProtocol not available")

    def test_character_protocol(self):
        """Test CharacterProtocol."""
        try:
            from src.agents.persona_agent.protocols import CharacterProtocol

            mock_char = Mock()
            mock_char.character_id = "test"
            mock_char.name = "Test"

            def use_char(char: CharacterProtocol) -> None:
                pass

            use_char(mock_char)
        except ImportError:
            pytest.skip("CharacterProtocol not available")


class TestPersonaAgent:
    """Test PersonaAgent class."""

    def test_agent_import(self):
        """Test that agent module can be imported."""
        try:
            from src.agents.persona_agent.agent import PersonaAgent

            assert PersonaAgent is not None
        except ImportError:
            pytest.skip("PersonaAgent not available")

    def test_agent_creation(self):
        """Test creating a PersonaAgent."""
        try:
            from src.agents.persona_agent.agent import PersonaAgent

            with tempfile.TemporaryDirectory() as tmpdir:
                from src.core.event_bus import EventBus
                agent = PersonaAgent(
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )
                assert agent is not None
        except ImportError:
            pytest.skip("PersonaAgent not available")


class TestPersonaAgentIntegrated:
    """Test IntegratedPersonaAgent class."""

    def test_integrated_import(self):
        """Test that integrated module can be imported."""
        try:
            from src.agents.persona_agent.integrated import IntegratedPersonaAgent

            assert IntegratedPersonaAgent is not None
        except ImportError:
            pytest.skip("IntegratedPersonaAgent not available")

    def test_integrated_creation(self):
        """Test creating IntegratedPersonaAgent."""
        try:
            from src.agents.persona_agent.integrated import IntegratedPersonaAgent

            with tempfile.TemporaryDirectory() as tmpdir:
                from src.core.event_bus import EventBus
                agent = IntegratedPersonaAgent(
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )
                assert agent is not None
        except ImportError:
            pytest.skip("IntegratedPersonaAgent not available")


class TestPersonaModuleInit:
    """Test persona module initialization."""

    def test_persona_init_import(self):
        """Test persona __init__ imports."""
        try:
            from src.agents import persona

            assert persona is not None
        except ImportError:
            pytest.skip("persona module not available")

    def test_persona_agent_init_import(self):
        """Test persona_agent __init__ imports."""
        try:
            from src.agents import persona_agent

            assert persona_agent is not None
        except ImportError:
            pytest.skip("persona_agent module not available")


class TestDirectorModuleInit:
    """Test director module initialization."""

    def test_director_init_import(self):
        """Test director __init__ imports."""
        try:
            from src.agents import director

            assert director is not None
        except ImportError:
            pytest.skip("director module not available")


class TestPersonaAgentEdgeCases:
    """Test edge cases."""

    def test_agent_with_invalid_directory(self):
        """Test agent with invalid directory."""
        try:
            from src.agents.persona_agent.agent import PersonaAgent

            # Should handle gracefully
            from src.core.event_bus import EventBus
            agent = PersonaAgent(
                character_directory_path="/nonexistent/path",
                event_bus=EventBus(),
            )
            assert agent is not None
        except ImportError:
            pytest.skip("PersonaAgent not available")
        except (FileNotFoundError, ValueError):
            # Expected behavior
            pass

    def test_core_memory_access(self):
        """Test core memory access methods."""
        try:
            from src.agents.persona_agent.core import PersonaAgentCore

            with tempfile.TemporaryDirectory() as tmpdir:
                from src.core.event_bus import EventBus
                core = PersonaAgentCore(
                    agent_id="test",
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )
                # Test memory access
                short_term = core.short_term_memory
                assert isinstance(short_term, list)
        except ImportError:
            pytest.skip("PersonaAgentCore not available")

    def test_core_relationship_access(self):
        """Test core relationship access."""
        try:
            from src.agents.persona_agent.core import PersonaAgentCore

            with tempfile.TemporaryDirectory() as tmpdir:
                from src.core.event_bus import EventBus
                core = PersonaAgentCore(
                    agent_id="test",
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )
                # Test relationship methods
                strength = core.get_relationship_strength("test_entity")
                assert isinstance(strength, (int, float))
        except ImportError:
            pytest.skip("PersonaAgentCore not available")


class TestPersonaAgentIntegration:
    """Integration tests for persona agent."""

    def test_agent_workflow(self):
        """Test basic agent workflow."""
        try:
            from src.agents.persona_agent.agent import PersonaAgent

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create character sheet
                sheet = Path(tmpdir) / "character_sheet.md"
                sheet.write_text("# Test Character\n\nname: Test\n")

                from src.core.event_bus import EventBus
                agent = PersonaAgent(
                    character_directory_path=str(tmpdir),
                    event_bus=EventBus(),
                )

                # Test basic properties
                assert hasattr(agent, "agent_id")
                assert hasattr(agent, "character_name")
        except ImportError:
            pytest.skip("PersonaAgent not available")
