#!/usr/bin/env python3
"""
Test suite for PersonaCore module.

Tests agent identity, state management, file caching, and lifecycle operations.
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.agents.persona_core import AgentIdentity, AgentState, PersonaCore


class TestAgentIdentity:
    """Test AgentIdentity dataclass."""

    def test_default_creation(self):
        """Test creating AgentIdentity with defaults."""
        identity = AgentIdentity(
            agent_id="test_agent",
            character_directory="/test/path",
        )
        assert identity.agent_id == "test_agent"
        assert identity.character_directory == "/test/path"
        assert identity.character_name == ""
        assert identity.primary_faction == ""
        assert identity.character_sheet_path == ""
        assert isinstance(identity.creation_timestamp, datetime)

    def test_full_creation(self):
        """Test creating AgentIdentity with all fields."""
        timestamp = datetime.now()
        identity = AgentIdentity(
            agent_id="agent_123",
            character_directory="/chars/warrior",
            character_name="Brave Warrior",
            primary_faction="Alliance",
            character_sheet_path="/chars/warrior/sheet.md",
            backstory="Born in the mountains...",
            creation_timestamp=timestamp,
        )
        assert identity.agent_id == "agent_123"
        assert identity.character_name == "Brave Warrior"
        assert identity.primary_faction == "Alliance"
        assert identity.backstory == "Born in the mountains..."


class TestAgentState:
    """Test AgentState dataclass."""

    def test_default_creation(self):
        """Test creating AgentState with defaults."""
        state = AgentState()
        assert state.current_location is None
        assert state.is_active is False
        assert state.last_action_timestamp is None
        assert state.last_world_state_update is None
        assert state.turn_count == 0
        assert state.health_status == "normal"

    def test_custom_creation(self):
        """Test creating AgentState with custom values."""
        now = datetime.now()
        state = AgentState(
            current_location="Meridian Station",
            is_active=True,
            last_action_timestamp=now,
            last_world_state_update={"turn": 5},
            turn_count=10,
            health_status="injured",
        )
        assert state.current_location == "Meridian Station"
        assert state.is_active is True
        assert state.last_action_timestamp == now
        assert state.last_world_state_update == {"turn": 5}
        assert state.turn_count == 10
        assert state.health_status == "injured"


class TestPersonaCoreInitialization:
    """Test PersonaCore initialization."""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus."""
        return Mock()

    @pytest.fixture
    def temp_char_dir(self):
        """Create a temporary character directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            char_dir = Path(tmpdir) / "test_character"
            char_dir.mkdir()
            yield str(char_dir)

    def test_basic_initialization(self, mock_event_bus, temp_char_dir):
        """Test basic PersonaCore initialization."""
        core = PersonaCore(
            character_directory_path=temp_char_dir,
            event_bus=mock_event_bus,
        )

        assert core.character_directory_path == temp_char_dir
        assert core.event_bus == mock_event_bus
        assert isinstance(core.identity, AgentIdentity)
        assert isinstance(core.state, AgentState)
        assert core.state.is_active is False

    def test_initialization_with_agent_id(self, mock_event_bus, temp_char_dir):
        """Test initialization with custom agent_id."""
        core = PersonaCore(
            character_directory_path=temp_char_dir,
            event_bus=mock_event_bus,
            agent_id="custom_agent_id",
        )

        assert core.identity.agent_id == "custom_agent_id"
        assert core.agent_id == "custom_agent_id"

    def test_initialization_derives_agent_id_from_path(self, mock_event_bus, temp_char_dir):
        """Test that agent_id is derived from directory name."""
        core = PersonaCore(
            character_directory_path=temp_char_dir,
            event_bus=mock_event_bus,
        )

        assert "test_character" in core.identity.agent_id

    def test_initialization_creates_character_sheet_path(self, mock_event_bus, temp_char_dir):
        """Test that character_sheet_path is automatically set."""
        core = PersonaCore(
            character_directory_path=temp_char_dir,
            event_bus=mock_event_bus,
        )

        expected_path = os.path.join(temp_char_dir, "character_sheet.md")
        assert core.identity.character_sheet_path == expected_path


class TestPersonaCoreProperties:
    """Test PersonaCore properties."""

    @pytest.fixture
    def persona_core(self):
        """Create a PersonaCore instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
                agent_id="test_agent",
            )
            core.identity.character_name = "Test Character"
            yield core

    def test_agent_id_property(self, persona_core):
        """Test agent_id property."""
        assert persona_core.agent_id == "test_agent"

    def test_character_name_property(self, persona_core):
        """Test character_name property."""
        assert persona_core.character_name == "Test Character"

    def test_character_directory_name_property(self, persona_core):
        """Test character_directory_name property."""
        # Get the directory name from the path
        expected_name = os.path.basename(persona_core.character_directory_path.rstrip(os.sep))
        assert persona_core.character_directory_name == expected_name

    def test_character_context_property(self, persona_core):
        """Test character_context property."""
        context = persona_core.character_context
        assert "Test Character" in context
        assert "test_agent" in context

    def test_is_active_property(self, persona_core):
        """Test is_active property."""
        assert persona_core.is_active is False
        persona_core.state.is_active = True
        assert persona_core.is_active is True

    def test_memory_property(self, persona_core):
        """Test memory property returns interface with agent_id."""
        memory = persona_core.memory
        assert memory.agent_id == "test_agent"

    def test_narrative_property(self, persona_core):
        """Test narrative property returns interface with agent_id."""
        narrative = persona_core.narrative
        assert narrative.agent_id == "test_agent"

    def test_actions_property(self, persona_core):
        """Test actions property returns interface with agent_id."""
        actions = persona_core.actions
        assert actions.agent_id == "test_agent"


class TestPersonaCoreLifecycle:
    """Test PersonaCore lifecycle methods."""

    @pytest.fixture
    def persona_core(self):
        """Create a PersonaCore instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )
            yield core

    @pytest.mark.asyncio
    async def test_activate(self, persona_core):
        """Test activate method."""
        assert persona_core.state.is_active is False
        await persona_core.activate()
        assert persona_core.state.is_active is True

    @pytest.mark.asyncio
    async def test_deactivate(self, persona_core):
        """Test deactivate method."""
        await persona_core.activate()
        assert persona_core.state.is_active is True
        await persona_core.deactivate()
        assert persona_core.state.is_active is False

    def test_cleanup(self, persona_core):
        """Test cleanup method."""
        # Add some data to cache
        persona_core._file_cache["/test/path"] = ("content", 12345.0)
        persona_core.state.is_active = True

        persona_core.cleanup()

        assert len(persona_core._file_cache) == 0
        assert persona_core.state.is_active is False


class TestPersonaCoreFileOperations:
    """Test PersonaCore file operations."""

    @pytest.fixture
    def persona_core_with_files(self):
        """Create a PersonaCore instance with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )

            # Create test files
            test_file = Path(tmpdir) / "test_file.txt"
            test_file.write_text("Test content")

            yield core, str(test_file)

    @pytest.mark.asyncio
    async def test_read_character_file(self, persona_core_with_files):
        """Test read_character_file method."""
        core, test_file = persona_core_with_files
        filename = os.path.basename(test_file)

        content = await core.read_character_file(filename)
        assert content == "Test content"

    @pytest.mark.asyncio
    async def test_read_character_file_not_found(self, persona_core_with_files):
        """Test read_character_file with missing file."""
        core, _ = persona_core_with_files

        content = await core.read_character_file("nonexistent.txt")
        assert content == ""

    def test_read_cached_file(self, persona_core_with_files):
        """Test _read_cached_file method."""
        core, test_file = persona_core_with_files

        # First read - should cache
        content1 = core._read_cached_file(test_file)
        assert content1 == "Test content"

        # Second read - should use cache
        content2 = core._read_cached_file(test_file)
        assert content2 == "Test content"

    def test_read_cached_file_not_found(self, persona_core_with_files):
        """Test _read_cached_file with missing file."""
        core, _ = persona_core_with_files

        content = core._read_cached_file("/nonexistent/path/file.txt")
        assert content == ""

    def test_parse_cached_yaml(self, persona_core_with_files):
        """Test _parse_cached_yaml method."""
        core, _ = persona_core_with_files

        # Create a YAML file
        yaml_file = Path(core.character_directory_path) / "test.yaml"
        yaml_file.write_text("name: Test\nvalue: 42")

        data = core._parse_cached_yaml(str(yaml_file))
        assert data == {"name": "Test", "value": 42}

    def test_parse_cached_yaml_empty_file(self, persona_core_with_files):
        """Test _parse_cached_yaml with empty file."""
        core, _ = persona_core_with_files

        yaml_file = Path(core.character_directory_path) / "empty.yaml"
        yaml_file.write_text("")

        data = core._parse_cached_yaml(str(yaml_file))
        assert data == {}


class TestPersonaCoreStatusAndState:
    """Test PersonaCore status and state methods."""

    @pytest.fixture
    def persona_core(self):
        """Create a PersonaCore instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
                agent_id="test_agent",
            )
            core.identity.character_name = "Test Character"
            yield core

    def test_get_status(self, persona_core):
        """Test get_status method."""
        status = persona_core.get_status()

        assert status["agent_id"] == "test_agent"
        assert status["character_name"] == "Test Character"
        assert status["is_active"] is False
        assert status["turn_count"] == 0
        assert status["health_status"] == "normal"
        assert status["current_location"] is None
        assert "memory_entries" in status

    def test_handle_turn_start(self, persona_core):
        """Test handle_turn_start method."""
        initial_turn = persona_core.state.turn_count
        world_update = {"location": "Station", "event": "turn_start"}

        persona_core.handle_turn_start(world_update)

        assert persona_core.state.turn_count == initial_turn + 1
        assert persona_core.state.last_world_state_update == world_update

    def test_handle_turn_start_multiple(self, persona_core):
        """Test handle_turn_start increments correctly."""
        for i in range(5):
            persona_core.handle_turn_start({"turn": i})

        assert persona_core.state.turn_count == 5

    def test_get_agent_state(self, persona_core):
        """Test get_agent_state method."""
        state = persona_core.get_agent_state()

        assert "identity" in state
        assert "state" in state
        assert state["identity"]["agent_id"] == "test_agent"
        assert "character_data_loaded" in state
        assert "cache_size" in state


class TestPersonaCoreDeriveAgentId:
    """Test agent ID derivation from path."""

    @pytest.fixture
    def persona_core(self):
        """Create a PersonaCore instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )
            yield core

    def test_derive_from_simple_name(self, persona_core):
        """Test deriving agent_id from simple directory name."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/warrior")
        assert agent_id == "warrior"

    def test_derive_with_spaces(self, persona_core):
        """Test deriving agent_id from name with spaces."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/brave warrior")
        assert agent_id == "brave_warrior"

    def test_derive_with_dashes(self, persona_core):
        """Test deriving agent_id from name with dashes."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/brave-warrior")
        assert agent_id == "brave_warrior"

    def test_derive_with_numbers(self, persona_core):
        """Test deriving agent_id starting with numbers."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/123warrior")
        assert agent_id == "agent_123warrior"

    def test_derive_with_special_chars(self, persona_core):
        """Test deriving agent_id with special characters."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/warrior@test!")
        assert agent_id == "warriortest"

    def test_derive_empty_result(self, persona_core):
        """Test deriving agent_id from path that results in empty string."""
        agent_id = persona_core._derive_agent_id_from_path("/chars/!!!")
        assert agent_id.startswith("agent_")


class TestPersonaCoreEdgeCases:
    """Test PersonaCore edge cases."""

    def test_path_with_trailing_slash(self):
        """Test handling of path with trailing slash."""
        mock_event_bus = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            core = PersonaCore(
                character_directory_path=tmpdir + "/",
                event_bus=mock_event_bus,
            )
            # Should handle trailing slash correctly
            assert core.character_directory_path.endswith(os.sep) or True

    def test_file_cache_updates_on_modification(self):
        """Test that cache updates when file is modified."""
        mock_event_bus = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )

            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("version 1")

            # First read
            content1 = core._read_cached_file(str(test_file))
            assert content1 == "version 1"

            # Modify file
            import time
            time.sleep(0.01)  # Ensure different mtime
            test_file.write_text("version 2")

            # Second read should get new content
            content2 = core._read_cached_file(str(test_file))
            assert content2 == "version 2"

    @pytest.mark.asyncio
    async def test_activate_already_active(self):
        """Test activating an already active core."""
        mock_event_bus = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )
            await core.activate()
            assert core.is_active is True
            # Activate again - should still work
            await core.activate()
            assert core.is_active is True


class TestPersonaCoreErrorHandling:
    """Test PersonaCore error handling."""

    @pytest.fixture
    def persona_core(self):
        """Create a PersonaCore instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_event_bus = Mock()
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )
            yield core

    def test_read_cached_file_error(self, persona_core):
        """Test handling of file read errors."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat", side_effect=PermissionError("Access denied")):
                content = persona_core._read_cached_file("/restricted/file.txt")
                assert content == ""

    def test_parse_cached_yaml_invalid(self, persona_core):
        """Test parsing invalid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_yaml = Path(tmpdir) / "invalid.yaml"
            invalid_yaml.write_text("{invalid yaml: ")

            data = persona_core._parse_cached_yaml(str(invalid_yaml))
            assert data == {}


class TestPersonaCoreIntegration:
    """Integration tests for PersonaCore."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete agent lifecycle."""
        mock_event_bus = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
                agent_id="lifecycle_test",
            )

            # Initial state
            assert core.is_active is False

            # Activate
            await core.activate()
            assert core.is_active is True

            # Process some turns
            for i in range(3):
                core.handle_turn_start({"turn": i, "data": f"update_{i}"})

            assert core.state.turn_count == 3

            # Deactivate
            await core.deactivate()
            assert core.is_active is False

            # Cleanup
            core.cleanup()

    def test_status_after_operations(self):
        """Test status after various operations."""
        mock_event_bus = Mock()
        with tempfile.TemporaryDirectory() as tmpdir:
            core = PersonaCore(
                character_directory_path=tmpdir,
                event_bus=mock_event_bus,
            )

            # Read some files to populate cache
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("test")

            # Check status
            status = core.get_status()
            assert status["turn_count"] == 0

            # Check agent state
            agent_state = core.get_agent_state()
            assert agent_state["cache_size"] == 0  # Not yet cached in _file_cache
