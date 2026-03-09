"""Unit tests for CharacterRouterService.

Tests cover filesystem operations, character summarization, and data
transformation for the character router service.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.schemas import CharacterSummary
from src.api.services.character_router_service import (
    CharacterRouterService,
    _display_name_from_id,
    _normalize_character_id,
    _normalize_numeric_map,
    _parse_iso_datetime,
    _require_public_character_id,
    _to_float,
)

pytestmark = pytest.mark.unit


class TestDisplayNameFromId:
    """Tests for _display_name_from_id function."""

    def test_converts_underscore_to_space(self):
        """Converts underscores to spaces."""
        result = _display_name_from_id("elara_shadowbane")
        assert result == "Elara Shadowbane"

    def test_converts_hyphen_to_space(self):
        """Converts hyphens to spaces."""
        result = _display_name_from_id("elara-shadowbane")
        assert result == "Elara Shadowbane"

    def test_capitalizes_each_word(self):
        """Capitalizes each word."""
        result = _display_name_from_id("test_character_name")
        assert result == "Test Character Name"


class TestNormalizeCharacterId:
    """Tests for _normalize_character_id function."""

    def test_removes_special_characters(self):
        """Removes special characters from ID."""
        result = _normalize_character_id("Test@Character!")
        assert result == "test_character_"

    def test_converts_to_lowercase(self):
        """Converts ID to lowercase."""
        result = _normalize_character_id("TEST_CHARACTER")
        assert result == "test_character"

    def test_removes_path_traversal(self):
        """Removes path traversal attempts."""
        result = _normalize_character_id("../etc/passwd")
        assert result == "etc_passwd"

    def test_raises_on_empty_result(self):
        """Raises HTTPException when result is empty."""
        with pytest.raises(HTTPException) as exc_info:
            _normalize_character_id("!!!")
        assert exc_info.value.status_code == 400


class TestRequirePublicCharacterId:
    """Tests for _require_public_character_id function."""

    def test_returns_valid_id(self):
        """Returns valid character ID."""
        result = _require_public_character_id("valid_character_id")
        assert result == "valid_character_id"

    def test_raises_on_path_traversal(self):
        """Raises HTTPException on path traversal attempt."""
        with pytest.raises(HTTPException) as exc_info:
            _require_public_character_id("../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_raises_on_invalid_characters(self):
        """Raises HTTPException on invalid characters."""
        with pytest.raises(HTTPException) as exc_info:
            _require_public_character_id("invalid@id")
        assert exc_info.value.status_code == 400

    def test_raises_on_dotdot(self):
        """Raises HTTPException on '..' input."""
        with pytest.raises(HTTPException) as exc_info:
            _require_public_character_id("..")
        assert exc_info.value.status_code == 400


class TestParseIsoDatetime:
    """Tests for _parse_iso_datetime function."""

    def test_parses_iso_datetime(self):
        """Parses ISO datetime string."""
        result = _parse_iso_datetime("2024-01-15T10:30:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_adds_utc_timezone_when_missing(self):
        """Adds UTC timezone when missing."""
        result = _parse_iso_datetime("2024-01-15T10:30:00")
        assert result.tzinfo is not None

    def test_returns_none_for_empty_string(self):
        """Returns None for empty string."""
        result = _parse_iso_datetime("")
        assert result is None

    def test_returns_none_for_invalid_format(self):
        """Returns None for invalid datetime format."""
        result = _parse_iso_datetime("not-a-datetime")
        assert result is None


class TestToFloat:
    """Tests for _to_float function."""

    def test_converts_int_to_float(self):
        """Converts int to float."""
        result = _to_float(42)
        assert result == 42.0
        assert isinstance(result, float)

    def test_converts_string_to_float(self):
        """Converts string to float."""
        result = _to_float("3.14")
        assert result == 3.14

    def test_returns_zero_on_invalid(self):
        """Returns 0.0 on invalid conversion."""
        result = _to_float("not-a-number")
        assert result == 0.0

    def test_returns_zero_on_none(self):
        """Returns 0.0 on None input."""
        result = _to_float(None)
        assert result == 0.0


class TestNormalizeNumericMap:
    """Tests for _normalize_numeric_map function."""

    def test_converts_dict_values_to_float(self):
        """Converts dictionary values to float."""
        result = _normalize_numeric_map({"a": 1, "b": "2.5"})
        assert result == {"a": 1.0, "b": 2.5}

    def test_returns_empty_dict_for_non_dict(self):
        """Returns empty dict for non-dict input."""
        result = _normalize_numeric_map("not-a-dict")
        assert result == {}

    def test_handles_nested_strings(self):
        """Handles string values that represent numbers."""
        result = _normalize_numeric_map({"value": "10"})
        assert result == {"value": 10.0}


@pytest.fixture
def character_service(tmp_path):
    """Create a character service with a temporary characters directory."""
    return CharacterRouterService(characters_path=str(tmp_path / "characters"))


@pytest.fixture
def mock_character_dir(tmp_path):
    """Create a mock character directory structure."""
    char_dir = tmp_path / "characters" / "test_character"
    char_dir.mkdir(parents=True)

    # Create character markdown file
    char_file = char_dir / "character_test_character.md"
    char_file.write_text("# Test Character\n\nA test character description.")

    return char_dir


class TestCharacterRouterServiceGatherInfo:
    """Tests for gather_filesystem_character_info methods."""

    def test_gather_info_returns_tuple_for_existing_character(
        self, character_service, mock_character_dir, tmp_path
    ):
        """Returns info tuple for existing character."""
        service = CharacterRouterService(characters_path=str(tmp_path / "characters"))

        name, status, char_type, updated = service.gather_filesystem_character_info(
            "test_character"
        )

        assert name == "Test Character"
        assert isinstance(updated, datetime)

    def test_gather_info_raises_http_exception_for_missing_character(
        self, character_service
    ):
        """Raises HTTPException for missing character."""
        with pytest.raises(HTTPException) as exc_info:
            character_service.gather_filesystem_character_info("nonexistent")
        assert exc_info.value.status_code == 404

    def test_gather_info_result_returns_error_for_missing_character(
        self, character_service
    ):
        """gather_filesystem_character_info_result returns error for missing."""
        result = character_service.gather_filesystem_character_info_result(
            "nonexistent"
        )

        assert result.is_error
        assert "not found" in result.error.message.lower()


class TestCharacterRouterServiceSummarizePublic:
    """Tests for summarize_public_character methods."""

    def test_summarize_public_returns_summary_and_timestamp(
        self, character_service, mock_character_dir, tmp_path
    ):
        """Returns CharacterSummary and timestamp."""
        service = CharacterRouterService(characters_path=str(tmp_path / "characters"))

        summary, updated = service.summarize_public_character("test_character")

        assert isinstance(summary, CharacterSummary)
        assert summary.id == "test_character"
        assert summary.name == "Test Character"
        assert isinstance(updated, datetime)

    def test_summarize_public_result_returns_error_for_invalid_id(
        self, character_service
    ):
        """summarize_public_character_result returns error for invalid ID."""
        result = character_service.summarize_public_character_result("../invalid")

        assert result.is_error


class TestCharacterRouterServiceSummarizeWorkspace:
    """Tests for summarize_workspace_character methods."""

    def test_summarize_workspace_returns_summary_and_timestamp(
        self, character_service
    ):
        """Returns CharacterSummary and timestamp from workspace record."""
        record = {
            "id": "workspace-char-001",
            "name": "Workspace Character",
            "current_status": "active",
            "metadata": {"role": "protagonist"},
            "updatedAt": "2024-01-15T10:30:00Z",
        }

        summary, updated = character_service.summarize_workspace_character(
            record, "workspace-001"
        )

        assert isinstance(summary, CharacterSummary)
        assert summary.id == "workspace-char-001"
        assert summary.name == "Workspace Character"
        assert summary.workspace_id == "workspace-001"

    def test_summarize_workspace_raises_on_missing_id(self, character_service):
        """Raises ValueError when record has no ID."""
        record = {"name": "No ID Character"}

        with pytest.raises(ValueError):
            character_service.summarize_workspace_character(record, "workspace-001")

    def test_summarize_workspace_result_returns_error_for_missing_id(
        self, character_service
    ):
        """summarize_workspace_character_result returns error for missing ID."""
        record = {"name": "No ID Character"}

        result = character_service.summarize_workspace_character_result(
            record, "workspace-001"
        )

        assert result.is_error
        assert "missing" in result.error.message.lower()


class TestCharacterRouterServiceGetPublicEntries:
    """Tests for get_public_character_entries methods."""

    async def test_get_public_entries_returns_list(
        self, character_service, mock_character_dir, tmp_path
    ):
        """Returns list of character entries."""
        service = CharacterRouterService(characters_path=str(tmp_path / "characters"))

        result = await service.get_public_character_entries()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], tuple)
        assert isinstance(result[0][1], CharacterSummary)

    async def test_get_public_entries_result_returns_error_for_missing_dir(
        self, character_service, tmp_path
    ):
        """Returns error for missing characters directory."""
        nonexistent_path = str(tmp_path / "nonexistent" / "characters")
        service = CharacterRouterService(characters_path=nonexistent_path)

        result = await service.get_public_character_entries_result()

        assert result.is_error


class TestCharacterRouterServiceNormalizeMethods:
    """Tests for normalize methods."""

    def test_normalize_character_id_delegates_to_function(
        self, character_service
    ):
        """normalize_character_id delegates to _normalize_character_id."""
        result = character_service.normalize_character_id("Test Character!")

        assert result == "test_character_"

    def test_normalize_numeric_map_delegates_to_function(
        self, character_service
    ):
        """normalize_numeric_map delegates to _normalize_numeric_map."""
        result = character_service.normalize_numeric_map({"a": 1, "b": "2"})

        assert result == {"a": 1.0, "b": 2.0}


class TestCharacterRouterServiceCharactersPath:
    """Tests for characters_path property."""

    def test_characters_path_uses_default_when_not_set(self, tmp_path):
        """Uses default path when not explicitly set."""
        with patch(
            "src.api.services.character_router_service.get_characters_directory_path"
        ) as mock_get_path:
            mock_get_path.return_value = str(tmp_path / "default_characters")
            service = CharacterRouterService()

            path = service.characters_path

            assert path == str(tmp_path / "default_characters")

    def test_characters_path_uses_explicit_path_when_set(self, tmp_path):
        """Uses explicit path when provided in constructor."""
        explicit_path = str(tmp_path / "explicit_characters")
        service = CharacterRouterService(characters_path=explicit_path)

        path = service.characters_path

        assert path == explicit_path


class TestCharacterRouterServiceYamlParsing:
    """Tests for YAML stats file parsing."""

    def test_parses_stats_yaml_correctly(self, character_service, tmp_path):
        """Parses stats.yaml file correctly."""
        char_dir = tmp_path / "characters" / "yaml_char"
        char_dir.mkdir(parents=True)

        # Create character file
        char_file = char_dir / "character_yaml_char.md"
        char_file.write_text("# YAML Character")

        # Create stats.yaml file
        stats_file = char_dir / "stats.yaml"
        stats_file.write_text("""
metadata:
  current_status: inactive
  role: antagonist
structured_data:
  role: villain
""")

        service = CharacterRouterService(characters_path=str(tmp_path / "characters"))
        name, status, char_type, updated = service.gather_filesystem_character_info(
            "yaml_char"
        )

        assert status == "inactive"
        assert char_type == "antagonist"

    def test_handles_missing_stats_yaml(self, character_service, tmp_path):
        """Handles missing stats.yaml gracefully."""
        char_dir = tmp_path / "characters" / "no_stats_char"
        char_dir.mkdir(parents=True)

        char_file = char_dir / "character_no_stats_char.md"
        char_file.write_text("# No Stats Character")

        service = CharacterRouterService(characters_path=str(tmp_path / "characters"))
        name, status, char_type, updated = service.gather_filesystem_character_info(
            "no_stats_char"
        )

        # Should use defaults
        assert status == "active"
        assert char_type == "npc"
