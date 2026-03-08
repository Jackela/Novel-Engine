#!/usr/bin/env python3
"""
Test suite for CharacterContextManager module.

Tests character context loading, parsing, and management.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.agents.context_manager import CharacterContextManager


class TestCharacterContextManagerInitialization:
    """Test CharacterContextManager initialization."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock PersonaCore."""
        core = Mock()
        core.agent_id = "test_agent"
        core.identity = Mock()
        core.identity.character_sheet_path = "/test/sheet.md"
        core.identity.character_name = "Test Character"
        core.character_data = {}
        return core

    def test_initialization(self, mock_core):
        """Test basic initialization."""
        manager = CharacterContextManager(core=mock_core)

        assert manager.core == mock_core


class TestCharacterContextManagerLoading:
    """Test character context loading."""

    @pytest.fixture
    def manager_with_file(self):
        """Create a manager with a temporary character sheet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create character sheet
            sheet_path = Path(tmpdir) / "character_sheet.md"
            sheet_content = """
# Character Sheet

## Identity
- name: Test Warrior
- faction: Alliance
- rank: Captain

## Psychological
- traits: brave, loyal
- motivations: Protect the realm

## Behavioral
- decision_weights:
  - combat: 0.8
  - diplomacy: 0.4

## Capabilities
- skills: sword fighting, leadership
"""
            sheet_path.write_text(sheet_content)

            core = Mock()
            core.agent_id = "test_agent"
            core.identity = Mock()
            core.identity.character_sheet_path = str(sheet_path)
            core.identity.character_name = ""
            core.identity.primary_faction = ""
            core.identity.backstory = ""
            core.character_data = {}
            # Mock the _read_cached_file method to actually read the file
            core._read_cached_file = lambda path: Path(path).read_text()

            manager = CharacterContextManager(core=core)
            yield manager, core, str(sheet_path)

    def test_load_character_context(self, manager_with_file):
        """Test loading character context."""
        manager, core, _ = manager_with_file

        manager.load_character_context()

        assert "identity" in core.character_data
        assert core.character_data["identity"]["name"] == "Test Warrior"

    def test_load_character_context_file_not_found(self, manager_with_file):
        """Test loading when file doesn't exist."""
        manager, core, _ = manager_with_file
        core.identity.character_sheet_path = "/nonexistent/path.md"

        manager.load_character_context()

        # Should not raise, but log error
        assert core.character_data == {}


class TestCharacterContextManagerParsing:
    """Test content parsing methods."""

    @pytest.fixture
    def manager(self):
        """Create a CharacterContextManager."""
        core = Mock()
        core.agent_id = "test_agent"
        core.identity = Mock()
        core.identity.character_sheet_path = "/test/sheet.md"
        core.identity.character_name = ""
        core.identity.primary_faction = ""
        core.character_data = {}
        return CharacterContextManager(core=core)

    def test_parse_character_sheet_content(self, manager):
        """Test parsing character sheet content."""
        content = """
## Identity
- name: Warrior Test
- faction: Test Faction
- rank: General

## Psychological
- traits: brave: 0.8, cautious: 0.4
- motivations: glory, honor

## Behavioral
- decision_weights:
  - combat: 0.9
  - retreat: 0.2
"""
        data = manager._parse_character_sheet_content(content)

        assert "identity" in data
        assert data["identity"]["name"] == "Warrior Test"
        assert "psychological" in data
        assert "behavioral" in data

    def test_extract_section_identity(self, manager):
        """Test extracting identity section."""
        content = """
## Identity
- name: Test
- faction: Alliance

## Other
Some other content
"""
        section = manager._extract_section(content, "identity")

        assert section is not None
        assert "name: Test" in section

    def test_extract_section_not_found(self, manager):
        """Test extracting non-existent section."""
        content = "## Other\nSome content"

        section = manager._extract_section(content, "nonexistent")

        assert section is None

    def test_parse_identity_section(self, manager):
        """Test parsing identity section."""
        content = """
- name: Test Warrior
- faction: Alliance
- rank: Captain
- age: 30
- gender: Male
- homeworld: Earth
- profession: Soldier

backstory: Born to fight
"""
        identity = manager._parse_identity_section(content)

        assert identity["name"] == "Test Warrior"
        assert identity["faction"] == "Alliance"
        assert identity["rank"] == "Captain"

    def test_parse_psychological_section(self, manager):
        """Test parsing psychological section."""
        content = """
- personality_traits:
  - brave: 0.8
  - cautious: 0.3
- motivations:
  - Protect family
  - Seek glory
"""
        psych = manager._parse_psychological_section(content)

        assert "personality_traits" in psych
        assert "motivations" in psych

    def test_extract_weighted_items(self, manager):
        """Test extracting weighted items."""
        content = """
- brave: 0.8
- cautious: 0.3
- aggressive (0.7)
"""
        items = manager._extract_weighted_items(content)

        assert "brave" in items
        assert items["brave"] == 0.8
        assert "cautious" in items

    def test_extract_bullet_points(self, manager):
        """Test extracting bullet points."""
        content = """
Traits:
- Brave
- Loyal
- Strong

Motivations:
- Protect
- Conquer
"""
        points = manager._extract_bullet_points(content)

        assert "traits" in points
        assert "Brave" in points["traits"]
        assert "motivations" in points

    def test_parse_simple_field_format(self, manager):
        """Test parsing simple field format."""
        content = """
name: Test
value: 42
score: 3.14
"""
        data = manager._parse_simple_field_format(content)

        assert data["name"] == "Test"
        assert data["value"] == 42
        assert data["score"] == 3.14


class TestCharacterContextManagerExtraction:
    """Test extraction methods."""

    @pytest.fixture
    def manager(self):
        """Create a CharacterContextManager."""
        core = Mock()
        core.agent_id = "test_agent"
        core.identity = Mock()
        core.identity.character_name = ""
        core.identity.primary_faction = ""
        core.identity.backstory = ""
        core.character_data = {
            "identity": {
                "name": "Test Warrior",
                "faction": "Alliance",
                "backstory": "Born to fight",
            },
        }
        return CharacterContextManager(core=core)

    def test_extract_core_identity(self, manager):
        """Test extracting core identity."""
        manager._extract_core_identity()

        assert manager.core.identity.character_name == "Test Warrior"
        assert manager.core.identity.primary_faction == "Alliance"
        assert manager.core.identity.backstory == "Born to fight"

    def test_extract_core_identity_missing_fields(self, manager):
        """Test extracting core identity with missing fields."""
        manager.core.character_data = {}

        manager._extract_core_identity()

        # Should not raise error
        assert manager.core.identity.character_name == ""


class TestCharacterContextManagerSummary:
    """Test summary methods."""

    @pytest.fixture
    def manager(self):
        """Create a CharacterContextManager."""
        core = Mock()
        core.agent_id = "test_agent"
        core.identity = Mock()
        core.identity.character_name = "Test Warrior"
        core.identity.primary_faction = "Alliance"
        core.character_data = {
            "identity": {"name": "Test Warrior"},
            "psychological": {"traits": ["brave"]},
            "behavioral": {"weights": {"combat": 0.8}},
        }
        return CharacterContextManager(core=core)

    def test_get_character_summary(self, manager):
        """Test getting character summary."""
        summary = manager.get_character_summary()

        assert summary["character_name"] == "Test Warrior"
        assert summary["primary_faction"] == "Alliance"
        assert "sections_loaded" in summary
        assert summary["has_personality_traits"] is True
        assert summary["has_decision_weights"] is True


class TestCharacterContextManagerEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def manager(self):
        """Create a CharacterContextManager."""
        core = Mock()
        core.agent_id = "test_agent"
        core.identity = Mock()
        core.identity.character_sheet_path = "/test/sheet.md"
        core.character_data = {}
        return CharacterContextManager(core=core)

    def test_load_character_context_exception(self, manager):
        """Test loading with exception."""
        with patch.object(manager, "_parse_character_sheet_content", side_effect=Exception("Parse error")):
            manager.load_character_context()

        # Should not raise
        assert manager.core.character_data == {}

    def test_extract_section_multiple_patterns(self, manager):
        """Test extracting section with different header patterns."""
        # Single # header
        content1 = "# Identity\nContent here\n# Other"
        section1 = manager._extract_section(content1, "identity")
        assert section1 is not None

        # Double ## header
        content2 = "## Identity\nContent here\n## Other"
        section2 = manager._extract_section(content2, "identity")
        assert section2 is not None

    def test_parse_section_with_parser_error(self, manager):
        """Test parsing section that raises error."""
        content = "Invalid content"

        # Mock a parser method that raises exception
        with patch.object(manager, "_parse_identity_section", side_effect=Exception("Error")):
            result = manager._parse_character_sheet_content(content)

        # Should handle error gracefully
        assert isinstance(result, dict)

    def test_parse_simple_field_format_edge_cases(self, manager):
        """Test parsing fields with edge cases."""
        content = """
name: Test Value
number: 42
float: 3.14
not_a_number: abc123
"""
        data = manager._parse_simple_field_format(content)

        assert data["name"] == "Test Value"
        assert data["number"] == 42
        assert data["float"] == 3.14
        assert data["not_a_number"] == "abc123"


class TestCharacterContextManagerIntegration:
    """Integration tests."""

    def test_full_load_and_parse(self):
        """Test full loading and parsing flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create character sheet
            sheet_path = Path(tmpdir) / "character_sheet.md"
            sheet_content = """
# Test Character

## Identity
- name: Brave Warrior
- faction: The Alliance
- rank: Captain
- age: 35

## Psychological
- personality_traits:
  - brave: 0.9
  - loyal: 0.8
  - cautious: 0.3
- motivations:
  - Protect the innocent
  - Seek honor
- fears:
  - Losing comrades

## Behavioral
- decision_weights:
  - combat: 0.85
  - diplomacy: 0.4
  - retreat: 0.2

## Knowledge
- expertise:
  - Sword fighting
  - Tactics

## Capabilities
- skills: combat, leadership
- stats:
  - strength: 18
  - agility: 14
"""
            sheet_path.write_text(sheet_content)

            # Setup mock core
            core = Mock()
            core.agent_id = "test_agent"
            core.identity = Mock()
            core.identity.character_sheet_path = str(sheet_path)
            core.identity.character_name = ""
            core.identity.primary_faction = ""
            core.identity.backstory = ""
            core.character_data = {}
            # Mock the _read_cached_file method to actually read the file
            core._read_cached_file = lambda path: Path(path).read_text()

            manager = CharacterContextManager(core=core)
            manager.load_character_context()

            # Verify loaded data
            assert core.character_data["identity"]["name"] == "Brave Warrior"
            assert core.character_data["identity"]["faction"] == "The Alliance"
            assert "psychological" in core.character_data
            assert "behavioral" in core.character_data
            assert core.identity.character_name == "Brave Warrior"
            assert core.identity.primary_faction == "The Alliance"

            # Verify summary
            summary = manager.get_character_summary()
            assert summary["character_name"] == "Brave Warrior"
            assert "identity" in summary["sections_loaded"]
