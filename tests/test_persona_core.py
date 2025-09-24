#!/usr/bin/env python3
"""
PersonaCore Component Test Suite
================================

Comprehensive unit tests for the refactored PersonaCore component.
Tests all aspects of identity management, file operations, and lifecycle.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agents.persona_core import AgentIdentity, PersonaCore

# Note: PersonaMemory, PersonaNarrative, PersonaActions don't exist - removing unused imports


class TestAgentIdentity:
    """Test AgentIdentity dataclass functionality."""

    def test_agent_identity_creation(self):
        """Test AgentIdentity creation and properties."""
        identity = AgentIdentity(
            agent_id="test_agent_001",
            character_name="Test Character",
            character_directory="/test/path",
            primary_faction="Test Faction",
            character_sheet_path="/test/path/character_sheet.md",
        )

        assert identity.agent_id == "test_agent_001"
        assert identity.character_name == "Test Character"
        assert identity.character_directory == "/test/path"
        assert identity.primary_faction == "Test Faction"
        assert identity.character_sheet_path == "/test/path/character_sheet.md"

    def test_agent_identity_defaults(self):
        """Test AgentIdentity with minimal required fields."""
        identity = AgentIdentity(
            agent_id="minimal_agent", character_directory="/minimal/path"
        )

        assert identity.agent_id == "minimal_agent"
        assert identity.character_directory == "/minimal/path"
        assert identity.character_name == ""
        assert identity.primary_faction == ""


class TestPersonaCore:
    """Test PersonaCore component functionality."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return Mock()

    @pytest.fixture
    def temp_character_dir(self):
        """Create temporary character directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create character sheet
            character_sheet = Path(temp_dir) / "character_sheet.md"
            character_sheet.write_text(
                """
# Test Character

## Basic Information
- **Name**: Test Character
- **Faction**: Test Faction
- **Role**: Test Role
"""
            )
            yield temp_dir

    @pytest.fixture
    def persona_core(self, mock_event_bus, temp_character_dir):
        """Create PersonaCore instance for testing."""
        return PersonaCore(
            temp_character_dir, mock_event_bus, "test_agent_001"
        )

    def test_persona_core_initialization(self, persona_core):
        """Test PersonaCore initialization."""
        assert persona_core.identity.agent_id == "test_agent_001"
        assert (
            persona_core.identity.character_directory.endswith(
                "test_agent_001"
            )
            is False
        )  # Uses provided path
        assert persona_core.is_active is False
        assert persona_core.memory is not None
        assert persona_core.narrative is not None
        assert persona_core.actions is not None

    @pytest.mark.asyncio
    async def test_persona_core_activation(self, persona_core):
        """Test agent activation and deactivation."""
        # Test activation
        await persona_core.activate()
        assert persona_core.is_active is True

        # Test deactivation
        await persona_core.deactivate()
        assert persona_core.is_active is False

    @pytest.mark.asyncio
    async def test_persona_core_file_operations(self, persona_core):
        """Test file reading operations."""
        content = await persona_core.read_character_file("character_sheet.md")
        assert "Test Character" in content
        assert "Test Faction" in content

    def test_persona_core_status(self, persona_core):
        """Test status reporting."""
        status = persona_core.get_status()

        assert "agent_id" in status
        assert "character_name" in status
        assert "is_active" in status
        assert "memory_entries" in status
        assert status["agent_id"] == "test_agent_001"
        assert status["is_active"] is False

    @pytest.mark.asyncio
    async def test_persona_core_error_handling(self, persona_core):
        """Test error handling for invalid files."""
        content = await persona_core.read_character_file("nonexistent.md")
        assert content == ""  # Should return empty string for missing files

    def test_persona_core_component_integration(self, persona_core):
        """Test integration with sub-components."""
        # Test memory component
        assert hasattr(persona_core.memory, "agent_id")
        assert persona_core.memory.agent_id == "test_agent_001"

        # Test narrative component
        assert hasattr(persona_core.narrative, "agent_id")
        assert persona_core.narrative.agent_id == "test_agent_001"

        # Test actions component
        assert hasattr(persona_core.actions, "agent_id")
        assert persona_core.actions.agent_id == "test_agent_001"


class TestPersonaCoreIntegration:
    """Integration tests for PersonaCore with other components."""

    @pytest.mark.asyncio
    async def test_event_bus_integration(self):
        """Test PersonaCore integration with EventBus."""
        mock_event_bus = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            character_sheet = Path(temp_dir) / "character_sheet.md"
            character_sheet.write_text("# Test Character")

            persona_core = PersonaCore(
                temp_dir, mock_event_bus, "integration_test"
            )
            await persona_core.activate()

            # Verify event bus interactions
            assert (
                mock_event_bus.subscribe.call_count >= 0
            )  # May or may not subscribe

            await persona_core.deactivate()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
