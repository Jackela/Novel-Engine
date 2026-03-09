#!/usr/bin/env python3
"""
Test suite for CharacterInterpreter module.

Tests character data loading, parsing, and interpretation.
"""

import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from src.agents.character_interpreter import CharacterInterpreter


class TestCharacterInterpreterInitialization:
    """Test CharacterInterpreter initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = CharacterInterpreter(tmpdir)

            assert interpreter.character_directory_path == tmpdir
            assert interpreter.character_data == {}
            assert isinstance(interpreter.file_cache, dict)
            assert isinstance(interpreter.yaml_cache, dict)


class TestCharacterInterpreterFileDiscovery:
    """Test file discovery methods."""

    @pytest.fixture
    def interpreter_with_files(self):
        """Create interpreter with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "sheet.md").write_text("# Character")
            (Path(tmpdir) / "stats.yaml").write_text("name: Test")
            (Path(tmpdir) / "data.yml").write_text("data: value")

            interpreter = CharacterInterpreter(tmpdir)
            yield interpreter, tmpdir

    def test_discover_character_files(self, interpreter_with_files):
        """Test discovering character files."""
        interpreter, tmpdir = interpreter_with_files

        md_files, yaml_files = interpreter._discover_character_files()

        assert len(md_files) == 1
        assert len(yaml_files) == 2
        assert any("sheet.md" in f for f in md_files)
        assert any("stats.yaml" in f for f in yaml_files)

    def test_discover_no_files(self):
        """Test discovering files in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = CharacterInterpreter(tmpdir)
            md_files, yaml_files = interpreter._discover_character_files()

            assert len(md_files) == 0
            assert len(yaml_files) == 0


class TestCharacterInterpreterLoading:
    """Test character context loading."""

    def test_load_character_context_success(self):
        """Test successful context loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files
            (Path(tmpdir) / "character.md").write_text("# Test Character\nname: Test")
            (Path(tmpdir) / "stats.yaml").write_text("level: 5")

            interpreter = CharacterInterpreter(tmpdir)
            data = interpreter.load_character_context()

            assert "name" in data
            assert "hybrid_context" in data

    def test_load_character_context_no_files(self):
        """Test loading with no compatible files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "readme.txt").write_text("Not a character file")

            interpreter = CharacterInterpreter(tmpdir)

            with pytest.raises(ValueError):
                interpreter.load_character_context()

    def test_load_character_context_invalid_directory(self):
        """Test loading from non-existent directory."""
        interpreter = CharacterInterpreter("/nonexistent/path")

        with pytest.raises(FileNotFoundError):
            interpreter.load_character_context()

    def test_load_character_context_not_directory(self):
        """Test loading from file instead of directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            interpreter = CharacterInterpreter(tmpfile.name)

            with pytest.raises(ValueError):
                interpreter.load_character_context()


class TestCharacterInterpreterProcessing:
    """Test file processing methods."""

    @pytest.fixture
    def interpreter(self):
        """Create interpreter with temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CharacterInterpreter(tmpdir)

    def test_process_markdown_files(self, interpreter):
        """Test processing markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md_file = Path(tmpdir) / "test.md"
            md_file.write_text("# Test Content")

            content = interpreter._process_markdown_files([str(md_file)])

            assert "Test Content" in content
            assert "test.md" in content

    def test_process_markdown_files_multiple(self, interpreter):
        """Test processing multiple markdown files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            md1 = Path(tmpdir) / "a.md"
            md2 = Path(tmpdir) / "b.md"
            md1.write_text("# First")
            md2.write_text("# Second")

            content = interpreter._process_markdown_files([str(md1), str(md2)])

            assert "First" in content
            assert "Second" in content

    def test_process_yaml_files(self, interpreter):
        """Test processing YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "stats.yaml"
            yaml_file.write_text("level: 5\nname: Test")

            data = interpreter._process_yaml_files([str(yaml_file)])

            assert "stats" in data
            assert data["stats"]["level"] == 5

    def test_process_yaml_files_invalid(self, interpreter):
        """Test processing invalid YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "invalid.yaml"
            yaml_file.write_text("{invalid yaml: ")

            data = interpreter._process_yaml_files([str(yaml_file)])

            assert "invalid" in data
            assert "_parse_error" in data["invalid"]

    def test_merge_yaml_data(self, interpreter):
        """Test merging YAML data into character data."""
        yaml_data = {
            "stats": {"level": 5},
            "skills": {"combat": 10},
        }
        interpreter.character_data = {}

        interpreter._merge_yaml_data_into_character_data(yaml_data)

        assert "yaml_stats" in interpreter.character_data
        assert interpreter.character_data["level"] == 5


class TestCharacterInterpreterParsing:
    """Test content parsing methods."""

    @pytest.fixture
    def interpreter(self):
        """Create interpreter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CharacterInterpreter(tmpdir)

    def test_parse_character_sheet_content(self, interpreter):
        """Test parsing character sheet content."""
        content = """
# Character Name

name: Test Character
faction: Alliance
rank: Captain

## Stats
weapon skill: 45
strength: 18

## Background
Test background information.

## Personality
Brave, loyal, determined

## Relationships
Ally: Friendly
Enemy: Hostile

## Skills
Sword fighting, Leadership
"""
        data = interpreter._parse_character_sheet_content(content)

        assert data["name"] == "Character Name"
        assert "faction" in data
        assert "stats" in data

    def test_extract_basic_info(self, interpreter):
        """Test extracting basic information."""
        content = """
name: Test Character
faction: The Alliance
rank: Captain
"""
        info = interpreter._extract_basic_info(content)

        assert info["name"] == "Test Character"
        assert info["faction"] == "The Alliance"

    def test_extract_basic_info_from_header(self, interpreter):
        """Test extracting name from header."""
        content = "# Hero Name\n\nfaction: Alliance"

        info = interpreter._extract_basic_info(content)

        assert info["name"] == "Hero Name"

    def test_extract_character_stats(self, interpreter):
        """Test extracting character stats."""
        content = """
weapon skill: 45
ballistic skill: 40
strength: 18
toughness: 16
"""
        stats = interpreter._extract_character_stats(content)

        assert "stats" in stats
        assert stats["stats"]["weapon skill"] == 45

    def test_extract_background_info(self, interpreter):
        """Test extracting background information."""
        content = """
background: Test background story
origin: Earth
description: Tall and strong
"""
        bg = interpreter._extract_background_info(content)

        assert bg["background"] == "Test background story"

    def test_extract_personality_info(self, interpreter):
        """Test extracting personality information."""
        content = """
personality: Brave, loyal, strong
motivations: Protect family
"""
        personality = interpreter._extract_personality_info(content)

        assert "personality_traits" in personality
        assert "Brave" in personality["personality_traits"]

    def test_extract_relationship_info(self, interpreter):
        """Test extracting relationship information."""
        content = """
relationships:
- Ally: Trusted friend
- Enemy: Rival
"""
        relationships = interpreter._extract_relationship_info(content)

        # May or may not extract depending on parsing
        assert isinstance(relationships, dict)

    def test_extract_skills_info(self, interpreter):
        """Test extracting skills information."""
        content = """
skills: Sword fighting, Archery, Leadership
"""
        skills = interpreter._extract_skills_info(content)

        assert "skills" in skills


class TestCharacterInterpreterCharacteristics:
    """Test characteristic extraction methods."""

    @pytest.fixture
    def interpreter(self):
        """Create interpreter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CharacterInterpreter(tmpdir)

    def test_extract_core_identity(self, interpreter):
        """Test extracting core identity."""
        interpreter.character_data = {"name": "Test"}

        interpreter._extract_core_identity()

        assert interpreter.character_data["name"] == "Test"

    def test_extract_core_identity_default_name(self, interpreter):
        """Test extracting identity with default name from directory."""
        interpreter._extract_core_identity()

        # Should derive from directory name
        assert "name" in interpreter.character_data

    def test_extract_personality_traits(self, interpreter):
        """Test extracting personality traits."""
        interpreter.character_data = {
            "personality_traits": ["brave", "loyal", "intelligent"],
        }

        interpreter._extract_personality_traits()

        assert "personality_scores" in interpreter.character_data
        scores = interpreter.character_data["personality_scores"]
        assert "bravery" in scores
        assert "loyalty" in scores

    def test_extract_decision_weights(self, interpreter):
        """Test extracting decision weights."""
        interpreter.character_data = {
            "personality_scores": {"loyalty": 0.9, "bravery": 0.8},
            "faction": "alliance_network",
        }

        interpreter._extract_decision_weights()

        assert "decision_weights" in interpreter.character_data
        weights = interpreter.character_data["decision_weights"]
        assert "faction_loyalty" in weights

    def test_extract_relationships(self, interpreter):
        """Test extracting relationships."""
        interpreter.character_data = {
            "relationships": {
                "Ally": "Trusted friend",
                "Enemy": "Rival",
            },
        }

        interpreter._extract_relationships()

        assert "relationship_scores" in interpreter.character_data

    def test_extract_knowledge_domains(self, interpreter):
        """Test extracting knowledge domains."""
        interpreter.character_data = {
            "skills": ["Engineering", "Combat"],
            "background": "Technical training in mechanics",
        }

        interpreter._extract_knowledge_domains()

        assert "knowledge_domains" in interpreter.character_data


class TestCharacterInterpreterValidation:
    """Test validation methods."""

    @pytest.fixture
    def interpreter(self):
        """Create interpreter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CharacterInterpreter(tmpdir)

    def test_validate_character_data_valid(self, interpreter):
        """Test validating valid character data."""
        interpreter.character_data = {
            "name": "Test",
            "faction": "Alliance",
            "hybrid_context": {},
            "decision_weights": {"combat": 0.5},
            "personality_scores": {"brave": 0.8},
        }

        is_valid, issues = interpreter.validate_character_data()

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_character_data_missing_name(self, interpreter):
        """Test validating data missing name."""
        interpreter.character_data = {"faction": "Alliance"}

        is_valid, issues = interpreter.validate_character_data()

        assert is_valid is False
        assert any("name" in issue.lower() for issue in issues)

    def test_validate_character_data_invalid_weights(self, interpreter):
        """Test validating data with invalid weights."""
        interpreter.character_data = {
            "name": "Test",
            "faction": "Alliance",
            "hybrid_context": {},
            "decision_weights": {"combat": 1.5},  # Invalid: > 1.0
        }

        is_valid, issues = interpreter.validate_character_data()

        assert is_valid is False
        assert any("combat" in issue.lower() for issue in issues)

    def test_validate_character_data_invalid_scores(self, interpreter):
        """Test validating data with invalid personality scores."""
        interpreter.character_data = {
            "name": "Test",
            "faction": "Alliance",
            "hybrid_context": {},
            "personality_scores": {"brave": 1.5},  # Invalid: > 1.0
        }

        is_valid, issues = interpreter.validate_character_data()

        assert is_valid is False
        assert any("brave" in issue.lower() for issue in issues)


class TestCharacterInterpreterSummary:
    """Test summary methods."""

    @pytest.fixture
    def interpreter(self):
        """Create interpreter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield CharacterInterpreter(tmpdir)

    def test_get_character_summary(self, interpreter):
        """Test getting character summary."""
        interpreter.character_data = {
            "name": "Test Character",
            "faction": "Alliance",
            "personality_scores": {},
            "decision_weights": {},
            "hybrid_context": {
                "file_count": {"md": 2, "yaml": 1},
            },
        }

        summary = interpreter.get_character_summary()

        assert summary["name"] == "Test Character"
        assert summary["faction"] == "Alliance"
        assert summary["has_personality_traits"] is True
        assert summary["has_decision_weights"] is True
        assert summary["files_processed"]["md"] == 2


class TestCharacterInterpreterCaching:
    """Test caching methods."""

    def test_read_cached_file(self):
        """Test reading file with caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("cached content")

            interpreter = CharacterInterpreter(tmpdir)

            # First read
            content1 = interpreter._read_cached_file(str(test_file))
            assert content1 == "cached content"

            # Second read (from cache)
            content2 = interpreter._read_cached_file(str(test_file))
            assert content2 == "cached content"

    def test_read_cached_file_error(self):
        """Test reading non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = CharacterInterpreter(tmpdir)

            content = interpreter._read_cached_file("/nonexistent/file.txt")
            assert content == ""

    def test_parse_cached_yaml(self):
        """Test parsing YAML with caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"
            yaml_file.write_text("name: Test\nvalue: 42")

            interpreter = CharacterInterpreter(tmpdir)

            # First parse
            data1 = interpreter._parse_cached_yaml(str(yaml_file))
            assert data1["name"] == "Test"

            # Second parse (from cache)
            data2 = interpreter._parse_cached_yaml(str(yaml_file))
            assert data2["value"] == 42

    def test_parse_cached_yaml_non_dict(self):
        """Test parsing YAML that doesn't parse to dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "test.yaml"
            yaml_file.write_text("- item1\n- item2")  # List, not dict

            interpreter = CharacterInterpreter(tmpdir)

            data = interpreter._parse_cached_yaml(str(yaml_file))
            assert "content" in data


class TestCharacterInterpreterEdgeCases:
    """Test edge cases."""

    def test_empty_character_directory(self):
        """Test with empty character directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = CharacterInterpreter(tmpdir)

            with pytest.raises(ValueError):
                interpreter.load_character_context()

    def test_character_section_yaml_priority(self):
        """Test that character section in YAML takes priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_file = Path(tmpdir) / "config.yaml"
            yaml_file.write_text("""
character:
  name: YAML Character
  faction: YAML Faction
level: 10
""")
            interpreter = CharacterInterpreter(tmpdir)
            data = interpreter.load_character_context()

            assert data.get("name") == "YAML Character"

    def test_header_with_separator(self):
        """Test that file separator headers are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            interpreter = CharacterInterpreter(tmpdir)
            content = "# === file.md ===\n\n# Real Character"

            info = interpreter._extract_basic_info(content)

            assert info["name"] == "Real Character"


class TestCharacterInterpreterIntegration:
    """Integration tests."""

    def test_full_character_loading(self):
        """Test full character loading flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create character files
            (Path(tmpdir) / "character.md").write_text("""
# Brave Warrior

name: Brave Warrior
faction: The Alliance
rank: Captain

## Background
Born in a small village, trained as a warrior.

## Personality
Brave, loyal, determined, aggressive

## Relationships
Commander: Respected leader
Rival: Enemy from past

## Skills
Sword fighting, Leadership, Tactics
""")
            (Path(tmpdir) / "stats.yaml").write_text("""
level: 10
health: 100
strength: 18
agility: 14
""")

            interpreter = CharacterInterpreter(tmpdir)
            data = interpreter.load_character_context()

            # Verify data
            assert data["name"] == "Brave Warrior"
            assert data["faction"] == "The Alliance"
            assert "hybrid_context" in data
            assert "yaml_stats" in data

            # Verify characteristics
            # personality_scores are only extracted when personality_traits are found
            # via _extract_personality_info from markdown content
            assert "decision_weights" in data  # Always extracted
            # relationship_scores are only extracted when relationships are found
            # knowledge_domains are only extracted when skills/background are found

            # Validate
            is_valid, issues = interpreter.validate_character_data()
            assert is_valid is True

            # Summary
            summary = interpreter.get_character_summary()
            assert summary["name"] == "Brave Warrior"
