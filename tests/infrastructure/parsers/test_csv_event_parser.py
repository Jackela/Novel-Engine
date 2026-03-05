"""Tests for CSV event parser."""

import pytest

from src.contexts.world.infrastructure.parsers.csv_event_parser import CSVEventParser


class TestCSVEventParser:
    """Test suite for CSVEventParser."""

    def test_parse_valid_csv(self):
        """Test parsing a valid CSV with multiple events."""
        csv_content = """name,description,event_type,significance,outcome,date_description,location_ids,faction_ids,key_figures,causes,consequences,is_secret,narrative_importance
War,Battle description,war,major,negative,Year 100,loc1;loc2,fac1;fac2,King,Dispute,Peace,false,75
Discovery,Found something,discovery,minor,positive,Year 101,loc3,fac3,Explorer,,,true,50"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        assert result.success is True
        assert len(result.events) == 2
        assert len(result.errors) == 0

        # Check first event
        event = result.events[0]
        assert event["name"] == "War"
        assert event["event_type"] == "war"
        assert event["location_ids"] == ["loc1", "loc2"]
        assert event["is_secret"] is False
        assert event["narrative_importance"] == 75

    def test_parse_missing_required_field(self):
        """Test parsing CSV with missing required field."""
        csv_content = """name,description,event_type,significance,outcome,date_description
,Battle description,war,major,negative,Year 100"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        assert result.success is False
        assert len(result.errors) > 0
        assert result.errors[0]["field"] == "name"

    def test_parse_invalid_enum_value(self):
        """Test parsing CSV with invalid enum value."""
        csv_content = """name,description,event_type,significance,outcome,date_description
War,Battle description,invalid_type,major,negative,Year 100"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        assert result.success is False
        assert any(e["field"] == "event_type" for e in result.errors)

    def test_parse_empty_csv(self):
        """Test parsing empty CSV content."""
        parser = CSVEventParser()
        result = parser.parse("")

        assert result.success is False
        assert len(result.errors) > 0

    def test_parse_list_fields(self):
        """Test that list fields are correctly parsed."""
        csv_content = """name,description,event_type,significance,outcome,date_description,location_ids,faction_ids,key_figures,causes,consequences
War,Battle,war,major,negative,Year 100,loc1;loc2;loc3,fac1;fac2,King;Queen,Cause1;Cause2,Result1;Result2"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        assert result.success is True
        event = result.events[0]
        assert event["location_ids"] == ["loc1", "loc2", "loc3"]
        assert event["faction_ids"] == ["fac1", "fac2"]
        assert event["key_figures"] == ["King", "Queen"]
        assert event["causes"] == ["Cause1", "Cause2"]
        assert event["consequences"] == ["Result1", "Result2"]

    def test_parse_boolean_field(self):
        """Test that boolean fields are correctly parsed."""
        csv_content = """name,description,event_type,significance,outcome,date_description,is_secret
War,Battle,war,major,negative,Year 100,true
Discovery,Find,discovery,minor,positive,Year 101,false
Battle,Fight,battle,major,mixed,Year 102,1"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        assert result.success is True
        assert result.events[0]["is_secret"] is True
        assert result.events[1]["is_secret"] is False
        assert result.events[2]["is_secret"] is True

    def test_parse_narrative_importance(self):
        """Test narrative importance field parsing."""
        csv_content = """name,description,event_type,significance,outcome,date_description,narrative_importance
War,Battle,war,major,negative,Year 100,75
Discovery,Find,discovery,minor,positive,Year 101,invalid"""

        parser = CSVEventParser()
        result = parser.parse(csv_content)

        # First event should succeed
        assert result.events[0]["narrative_importance"] == 75
        # Second event should have error
        assert any(e["field"] == "narrative_importance" for e in result.errors)
