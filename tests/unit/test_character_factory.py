#!/usr/bin/env python3
"""
Character Factory Unit Test Suite
Testing character creation, loading, and validation core functionality
"""

import os
from unittest.mock import Mock, patch

import pytest

# Import modules under test

pytestmark = pytest.mark.unit

try:
    from src.config.character_factory import CharacterFactory
    from src.core.event_bus import EventBus

    CHARACTER_FACTORY_AVAILABLE = True
except ImportError:
    CHARACTER_FACTORY_AVAILABLE = False


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactory:
    """Character Factory Core Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_factory_initialization_success(self):
        """Test factory initialization - success case"""
        event_bus = Mock(spec=EventBus)
        factory = CharacterFactory(event_bus)

        assert factory.event_bus == event_bus
        assert hasattr(factory, "event_bus")
        assert hasattr(factory, "base_character_path")

    @pytest.mark.unit
    @pytest.mark.unit
    def test_create_character_empty_name(self):
        """Test character creation with empty name raises ValueError"""
        factory = CharacterFactory(self.mock_event_bus)

        with pytest.raises(ValueError, match="Character name cannot be empty"):
            factory.create_character("")

        with pytest.raises(ValueError, match="Character name cannot be empty"):
            factory.create_character("   ")

    @pytest.mark.unit
    def test_create_character_not_found(self, tmp_path):
        """Test character creation - character not found"""
        # Create factory with temporary path
        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with pytest.raises(FileNotFoundError, match="Character directory not found"):
            factory.create_character("nonexistent_character")

    @pytest.mark.unit
    def test_create_character_path_is_file_not_directory(self, tmp_path):
        """Test character creation when path exists but is a file not directory"""
        # Create a file instead of directory
        char_file = tmp_path / "testchar"
        char_file.write_text("not a directory")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with pytest.raises(FileNotFoundError, match="not a directory"):
            factory.create_character("testchar")

    @pytest.mark.unit
    def test_create_character_success(self, tmp_path):
        """Test successful character creation"""
        # Create character directory
        char_dir = tmp_path / "testchar"
        char_dir.mkdir()

        # Create minimal character files
        (char_dir / "character_testchar.md").write_text("# Test Character\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        # Mock PersonaAgent to avoid actual initialization
        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            mock_agent = Mock()
            mock_agent.agent_id = "testchar_1"
            mock_persona.return_value = mock_agent

            agent = factory.create_character("testchar")

            assert agent is not None
            assert agent.agent_id == "testchar_1"
            mock_persona.assert_called_once()
            # Verify it was called with the correct directory path
            call_args = mock_persona.call_args
            assert str(char_dir) in str(call_args[0][0])

    @pytest.mark.unit
    def test_create_character_with_agent_id(self, tmp_path):
        """Test character creation with custom agent_id"""
        char_dir = tmp_path / "testchar"
        char_dir.mkdir()
        (char_dir / "character_testchar.md").write_text("# Test\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            mock_agent = Mock()
            mock_agent.agent_id = "custom_id"
            mock_persona.return_value = mock_agent

            agent = factory.create_character("testchar", agent_id="custom_id")

            assert agent is not None
            # Verify agent_id was passed
            call_args = mock_persona.call_args
            assert call_args[1]["agent_id"] == "custom_id"

    @pytest.mark.unit
    def test_character_factory_persona_creation_error(self, tmp_path):
        """Test error handling when PersonaAgent creation fails"""
        char_dir = tmp_path / "testchar"
        char_dir.mkdir()
        (char_dir / "character_testchar.md").write_text("# Test\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            # Simulate PersonaAgent initialization failure
            mock_persona.side_effect = Exception("Persona creation failed")

            with pytest.raises(Exception, match="Persona creation failed"):
                factory.create_character("testchar")

    @pytest.mark.unit
    def test_list_available_characters(self, tmp_path):
        """Test listing available characters"""
        # Create multiple character directories
        (tmp_path / "char1").mkdir()
        (tmp_path / "char2").mkdir()
        (tmp_path / "char3").mkdir()
        # Create a file (should be ignored)
        (tmp_path / "notachar.txt").write_text("ignore")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        characters = factory.list_available_characters()

        assert len(characters) == 3
        assert "char1" in characters
        assert "char2" in characters
        assert "char3" in characters
        assert "notachar.txt" not in characters

    @pytest.mark.unit
    def test_list_available_characters_no_directory(self, tmp_path):
        """Test listing characters when base directory doesn't exist"""
        nonexistent = tmp_path / "nonexistent"

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(nonexistent)
        )

        with pytest.raises(
            FileNotFoundError, match="Character base directory not found"
        ):
            factory.list_available_characters()

    @pytest.mark.unit
    def test_multiple_character_creation(self, tmp_path):
        """Test creating multiple characters"""
        # Create multiple character directories
        for i in range(3):
            char_dir = tmp_path / f"char{i}"
            char_dir.mkdir()
            (char_dir / f"character_char{i}.md").write_text(f"# Char {i}\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            agents = []
            for i in range(3):
                mock_agent = Mock()
                mock_agent.agent_id = f"char{i}_agent"
                mock_persona.return_value = mock_agent

                agent = factory.create_character(f"char{i}")
                agents.append(agent)

            assert len(agents) == 3
            assert mock_persona.call_count == 3


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactoryConfiguration:
    """Character Factory Configuration Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_factory_with_different_event_buses(self):
        """Test factory with different event bus instances"""
        bus1 = Mock(spec=EventBus)
        bus2 = Mock(spec=EventBus)

        factory1 = CharacterFactory(bus1)
        factory2 = CharacterFactory(bus2)

        assert factory1.event_bus == bus1
        assert factory2.event_bus == bus2
        assert factory1.event_bus != factory2.event_bus

    @pytest.mark.unit
    def test_factory_with_custom_base_path(self, tmp_path):
        """Test factory initialization with custom base path"""
        custom_path = tmp_path / "custom_characters"
        custom_path.mkdir()

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(custom_path)
        )

        assert str(custom_path) in factory.base_character_path

    @pytest.mark.unit
    def test_factory_path_resolution(self, tmp_path):
        """Test character path resolution"""
        char_dir = tmp_path / "testchar"
        char_dir.mkdir()
        (char_dir / "character_testchar.md").write_text("# Test\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        # Verify the factory correctly resolves paths
        expected_path = os.path.join(str(tmp_path), "testchar")

        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            mock_agent = Mock()
            mock_persona.return_value = mock_agent

            factory.create_character("testchar")

            # Verify PersonaAgent was called with correct path
            call_args = mock_persona.call_args
            actual_path = call_args[0][0]
            assert os.path.normpath(actual_path) == os.path.normpath(expected_path)


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactoryPerformance:
    """Character Factory Performance Tests"""

    def setup_method(self):
        """Setup for each test method"""
        self.mock_event_bus = Mock(spec=EventBus)

    @pytest.mark.performance
    @pytest.mark.unit
    @pytest.mark.unit
    def test_character_creation_performance(self, tmp_path):
        """Test character creation performance"""
        import time

        # Create test character directory
        char_dir = tmp_path / "testchar"
        char_dir.mkdir()
        (char_dir / "character_testchar.md").write_text("# Test\n")

        factory = CharacterFactory(
            self.mock_event_bus, base_character_path=str(tmp_path)
        )

        with patch("src.config.character_factory.PersonaAgent") as mock_persona:
            mock_agent = Mock()
            mock_persona.return_value = mock_agent

            start_time = time.time()

            # Create 5 characters
            for i in range(5):
                agent = factory.create_character("testchar")
                assert agent is not None

            end_time = time.time()
            creation_time = end_time - start_time

            # Each character creation should complete quickly (mock is fast)
            assert creation_time < 1.0
            assert creation_time / 5 < 0.5  # Average per character


# Helper functions for running tests
def run_character_factory_tests():
    """Helper function to run all character factory tests"""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-m",
            "unit or performance",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("Character Factory Test Results:")
    print(result.stdout)
    if result.stderr:
        print("Error Output:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # Direct execution runs all tests
    run_character_factory_tests()
