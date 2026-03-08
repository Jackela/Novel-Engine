"""Tests for JSON event parser."""

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.infrastructure.parsers.json_event_parser import JSONEventParser


class TestJSONEventParser:
    """Test suite for JSONEventParser."""

    def test_parse_valid_json_with_wrapper(self):
        """Test parsing valid JSON with events wrapper."""
        json_content = """{
            "events": [
                {
                    "name": "War Event",
                    "description": "A major battle",
                    "event_type": "war",
                    "significance": "major",
                    "outcome": "negative",
                    "date_description": "Year 100"
                },
                {
                    "name": "Discovery Event",
                    "description": "Found something",
                    "event_type": "discovery",
                    "significance": "minor",
                    "outcome": "positive",
                    "date_description": "Year 101"
                }
            ]
        }"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        assert len(result.events) == 2
        assert len(result.errors) == 0

    def test_parse_valid_json_array(self):
        """Test parsing valid JSON array directly."""
        json_content = """[
            {
                "name": "War Event",
                "description": "A major battle",
                "event_type": "war",
                "significance": "major",
                "outcome": "negative",
                "date_description": "Year 100"
            }
        ]"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        assert len(result.events) == 1

    def test_parse_single_event_object(self):
        """Test parsing a single event object."""
        json_content = """{
            "name": "War Event",
            "description": "A major battle",
            "event_type": "war",
            "significance": "major",
            "outcome": "negative",
            "date_description": "Year 100"
        }"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        assert len(result.events) == 1
        assert result.events[0]["name"] == "War Event"

    def test_parse_missing_required_field(self):
        """Test parsing JSON with missing required field."""
        json_content = """{
            "events": [
                {
                    "description": "A major battle",
                    "event_type": "war",
                    "significance": "major",
                    "outcome": "negative",
                    "date_description": "Year 100"
                }
            ]
        }"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is False
        assert len(result.errors) > 0
        assert result.errors[0]["field"] == "name"

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        json_content = "{ invalid json"

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is False
        assert len(result.errors) > 0

    def test_parse_list_fields(self):
        """Test that list fields are correctly parsed."""
        json_content = """{
            "events": [
                {
                    "name": "War Event",
                    "description": "A major battle",
                    "event_type": "war",
                    "significance": "major",
                    "outcome": "negative",
                    "date_description": "Year 100",
                    "location_ids": ["loc1", "loc2", "loc3"],
                    "faction_ids": ["fac1"],
                    "is_secret": true
                }
            ]
        }"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        event = result.events[0]
        assert event["location_ids"] == ["loc1", "loc2", "loc3"]
        assert event["faction_ids"] == ["fac1"]
        assert event["is_secret"] is True

    def test_parse_with_semicolon_separated_lists(self):
        """Test parsing JSON with semicolon-separated list strings."""
        json_content = """{
            "events": [
                {
                    "name": "War Event",
                    "description": "A major battle",
                    "event_type": "war",
                    "significance": "major",
                    "outcome": "negative",
                    "date_description": "Year 100",
                    "location_ids": "loc1;loc2;loc3"
                }
            ]
        }"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        assert result.events[0]["location_ids"] == ["loc1", "loc2", "loc3"]

    def test_parse_empty_events(self):
        """Test parsing JSON with empty events array."""
        json_content = """{"events": []}"""

        parser = JSONEventParser()
        result = parser.parse(json_content)

        assert result.success is True
        assert len(result.events) == 0
