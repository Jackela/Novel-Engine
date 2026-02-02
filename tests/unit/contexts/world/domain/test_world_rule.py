#!/usr/bin/env python3
"""Unit tests for the WorldRule domain entity.

Tests cover:
- WorldRule creation and validation
- Business rule enforcement
- Factory methods
- Exception management operations
- Severity-based helpers
"""

import pytest

from src.contexts.world.domain.entities.world_rule import WorldRule

pytestmark = pytest.mark.unit


class TestWorldRuleCreation:
    """Tests for WorldRule entity creation."""

    def test_create_basic_rule(self):
        """Test creating a basic world rule."""
        rule = WorldRule(
            name="Law of Gravity",
            description="Objects fall towards the ground.",
            consequence="Characters fall when unsupported.",
        )

        assert rule.name == "Law of Gravity"
        assert rule.description == "Objects fall towards the ground."
        assert rule.consequence == "Characters fall when unsupported."
        assert rule.exceptions == []
        assert rule.category == ""
        assert rule.severity == 50

    def test_create_rule_with_defaults(self):
        """Test rule creation with default values."""
        rule = WorldRule(name="Test Rule")

        assert rule.name == "Test Rule"
        assert rule.description == ""
        assert rule.consequence == ""
        assert rule.exceptions == []
        assert rule.category == ""
        assert rule.severity == 50
        assert rule.related_rule_ids == []

    def test_create_rule_with_all_fields(self):
        """Test rule creation with all optional fields."""
        rule = WorldRule(
            name="Magic Costs Stamina",
            description="All magic use drains physical energy.",
            consequence="Caster becomes exhausted after casting.",
            exceptions=["Divine magic is exempt", "Artifacts bypass this"],
            category="magic",
            severity=80,
            related_rule_ids=["rule-001", "rule-002"],
        )

        assert rule.name == "Magic Costs Stamina"
        assert rule.description == "All magic use drains physical energy."
        assert rule.consequence == "Caster becomes exhausted after casting."
        assert rule.exceptions == ["Divine magic is exempt", "Artifacts bypass this"]
        assert rule.category == "magic"
        assert rule.severity == 80
        assert rule.related_rule_ids == ["rule-001", "rule-002"]

    def test_rule_has_entity_fields(self):
        """Test that rule inherits Entity fields."""
        rule = WorldRule(name="Test")

        assert rule.id is not None
        assert rule.created_at is not None
        assert rule.updated_at is not None
        assert rule.version == 1


class TestWorldRuleValidation:
    """Tests for WorldRule validation rules."""

    def test_empty_name_fails(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorldRule(name="")

    def test_whitespace_only_name_fails(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorldRule(name="   ")

    def test_name_too_long_fails(self):
        """Test that name exceeding 200 chars raises ValueError."""
        long_name = "x" * 201
        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            WorldRule(name=long_name)

    def test_name_at_limit_succeeds(self):
        """Test that name at exactly 200 chars succeeds."""
        name = "x" * 200
        rule = WorldRule(name=name)
        assert len(rule.name) == 200

    def test_description_too_long_fails(self):
        """Test that description exceeding 5000 chars raises ValueError."""
        long_desc = "x" * 5001
        with pytest.raises(ValueError, match="description cannot exceed 5000"):
            WorldRule(name="Test", description=long_desc)

    def test_consequence_too_long_fails(self):
        """Test that consequence exceeding 2000 chars raises ValueError."""
        long_consequence = "x" * 2001
        with pytest.raises(ValueError, match="consequence cannot exceed 2000"):
            WorldRule(name="Test", consequence=long_consequence)

    def test_too_many_exceptions_fails(self):
        """Test that more than 20 exceptions raises ValueError."""
        exceptions = [f"exception{i}" for i in range(21)]
        with pytest.raises(ValueError, match="more than 20 exceptions"):
            WorldRule(name="Test", exceptions=exceptions)

    def test_max_exceptions_succeeds(self):
        """Test that exactly 20 exceptions succeeds."""
        exceptions = [f"exception{i}" for i in range(20)]
        rule = WorldRule(name="Test", exceptions=exceptions)
        assert len(rule.exceptions) == 20

    def test_empty_exception_fails(self):
        """Test that empty string in exceptions raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            WorldRule(name="Test", exceptions=["valid", ""])

    def test_exception_too_long_fails(self):
        """Test that exception over 500 chars raises ValueError."""
        long_exception = "x" * 501
        with pytest.raises(ValueError, match="exceeds 500 character limit"):
            WorldRule(name="Test", exceptions=[long_exception])

    def test_severity_out_of_range_low_fails(self):
        """Test that severity below 0 raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            WorldRule(name="Test", severity=-1)

    def test_severity_out_of_range_high_fails(self):
        """Test that severity above 100 raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            WorldRule(name="Test", severity=101)

    def test_severity_at_limits_succeeds(self):
        """Test that severity at 0 and 100 succeeds."""
        rule_low = WorldRule(name="Flexible", severity=0)
        rule_high = WorldRule(name="Absolute", severity=100)

        assert rule_low.severity == 0
        assert rule_high.severity == 100

    def test_category_too_long_fails(self):
        """Test that category over 50 chars raises ValueError."""
        long_category = "x" * 51
        with pytest.raises(ValueError, match="Category cannot exceed 50"):
            WorldRule(name="Test", category=long_category)


class TestWorldRuleExceptionOperations:
    """Tests for exception management operations."""

    def test_add_exception(self):
        """Test adding an exception."""
        rule = WorldRule(name="Test")
        result = rule.add_exception("Divine magic is exempt")

        assert result is True
        assert "Divine magic is exempt" in rule.exceptions
        assert rule.version > 1  # Version incremented

    def test_add_exception_strips_whitespace(self):
        """Test that exceptions are trimmed."""
        rule = WorldRule(name="Test")
        rule.add_exception("  Divine magic is exempt  ")

        assert "Divine magic is exempt" in rule.exceptions

    def test_add_duplicate_exception_fails(self):
        """Test that adding duplicate exception returns False."""
        rule = WorldRule(name="Test", exceptions=["Divine magic is exempt"])
        result = rule.add_exception("Divine magic is exempt")

        assert result is False
        assert rule.exceptions.count("Divine magic is exempt") == 1

    def test_add_duplicate_exception_case_insensitive(self):
        """Test that duplicate detection is case-insensitive."""
        rule = WorldRule(name="Test", exceptions=["Divine magic is exempt"])
        result = rule.add_exception("DIVINE MAGIC IS EXEMPT")

        assert result is False

    def test_add_empty_exception_fails(self):
        """Test that adding empty exception returns False."""
        rule = WorldRule(name="Test")
        result = rule.add_exception("")

        assert result is False
        assert len(rule.exceptions) == 0

    def test_add_exception_exceeds_limit_raises(self):
        """Test that adding exception beyond 20 limit raises ValueError."""
        exceptions = [f"exception{i}" for i in range(20)]
        rule = WorldRule(name="Test", exceptions=exceptions)

        with pytest.raises(ValueError, match="Cannot add more than 20"):
            rule.add_exception("exception20")

    def test_add_exception_too_long_raises(self):
        """Test that exception over 500 chars raises ValueError."""
        rule = WorldRule(name="Test")
        long_exception = "x" * 501

        with pytest.raises(ValueError, match="cannot exceed 500 characters"):
            rule.add_exception(long_exception)

    def test_remove_exception(self):
        """Test removing an exception."""
        rule = WorldRule(name="Test", exceptions=["Divine magic", "Artifacts"])
        result = rule.remove_exception("Divine magic")

        assert result is True
        assert "Divine magic" not in rule.exceptions
        assert "Artifacts" in rule.exceptions

    def test_remove_exception_case_insensitive(self):
        """Test that exception removal is case-insensitive."""
        rule = WorldRule(name="Test", exceptions=["Divine magic"])
        result = rule.remove_exception("DIVINE MAGIC")

        assert result is True
        assert len(rule.exceptions) == 0

    def test_remove_nonexistent_exception_fails(self):
        """Test that removing nonexistent exception returns False."""
        rule = WorldRule(name="Test", exceptions=["Divine magic"])
        result = rule.remove_exception("Artifacts")

        assert result is False
        assert "Divine magic" in rule.exceptions

    def test_has_exception(self):
        """Test checking for exception existence."""
        rule = WorldRule(name="Test", exceptions=["Divine magic", "Artifacts"])

        assert rule.has_exception("Divine magic") is True
        assert rule.has_exception("DIVINE MAGIC") is True  # Case-insensitive
        assert rule.has_exception("nonexistent") is False


class TestWorldRuleUpdateOperations:
    """Tests for update operations."""

    def test_update_name(self):
        """Test updating name."""
        rule = WorldRule(name="Old Name")
        rule.update_name("New Name")

        assert rule.name == "New Name"
        assert rule.version > 1

    def test_update_name_strips_whitespace(self):
        """Test that name update strips whitespace."""
        rule = WorldRule(name="Old")
        rule.update_name("  New  ")

        assert rule.name == "New"

    def test_update_name_empty_fails(self):
        """Test that empty name update raises ValueError."""
        rule = WorldRule(name="Test")

        with pytest.raises(ValueError, match="cannot be empty"):
            rule.update_name("")

    def test_update_description(self):
        """Test updating description."""
        rule = WorldRule(name="Test", description="Old description")
        rule.update_description("New description")

        assert rule.description == "New description"
        assert rule.version > 1

    def test_update_description_too_long_fails(self):
        """Test that description update over 5000 chars raises ValueError."""
        rule = WorldRule(name="Test")
        long_desc = "x" * 5001

        with pytest.raises(ValueError, match="cannot exceed 5000"):
            rule.update_description(long_desc)

    def test_update_consequence(self):
        """Test updating consequence."""
        rule = WorldRule(name="Test", consequence="Old consequence")
        rule.update_consequence("New consequence")

        assert rule.consequence == "New consequence"
        assert rule.version > 1

    def test_update_consequence_too_long_fails(self):
        """Test that consequence update over 2000 chars raises ValueError."""
        rule = WorldRule(name="Test")
        long_consequence = "x" * 2001

        with pytest.raises(ValueError, match="cannot exceed 2000"):
            rule.update_consequence(long_consequence)

    def test_set_category(self):
        """Test setting category."""
        rule = WorldRule(name="Test", category="old")
        rule.set_category("magic")

        assert rule.category == "magic"
        assert rule.version > 1

    def test_set_category_lowercases(self):
        """Test that category is lowercased."""
        rule = WorldRule(name="Test")
        rule.set_category("MAGIC")

        assert rule.category == "magic"

    def test_set_category_too_long_fails(self):
        """Test that category over 50 chars raises ValueError."""
        rule = WorldRule(name="Test")
        long_category = "x" * 51

        with pytest.raises(ValueError, match="cannot exceed 50"):
            rule.set_category(long_category)

    def test_set_severity(self):
        """Test setting severity."""
        rule = WorldRule(name="Test", severity=50)
        rule.set_severity(90)

        assert rule.severity == 90
        assert rule.version > 1

    def test_set_severity_out_of_range_fails(self):
        """Test that severity out of range raises ValueError."""
        rule = WorldRule(name="Test")

        with pytest.raises(ValueError, match="between 0 and 100"):
            rule.set_severity(101)

        with pytest.raises(ValueError, match="between 0 and 100"):
            rule.set_severity(-1)


class TestWorldRuleRelatedRules:
    """Tests for related rule management."""

    def test_add_related_rule(self):
        """Test adding a related rule reference."""
        rule = WorldRule(name="Test")
        result = rule.add_related_rule("related-001")

        assert result is True
        assert "related-001" in rule.related_rule_ids

    def test_add_duplicate_related_rule_fails(self):
        """Test that adding duplicate related rule returns False."""
        rule = WorldRule(name="Test", related_rule_ids=["related-001"])
        result = rule.add_related_rule("related-001")

        assert result is False
        assert rule.related_rule_ids.count("related-001") == 1

    def test_add_self_reference_fails(self):
        """Test that self-reference returns False."""
        rule = WorldRule(name="Test")
        result = rule.add_related_rule(rule.id)

        assert result is False

    def test_remove_related_rule(self):
        """Test removing a related rule reference."""
        rule = WorldRule(name="Test", related_rule_ids=["related-001"])
        result = rule.remove_related_rule("related-001")

        assert result is True
        assert "related-001" not in rule.related_rule_ids


class TestWorldRuleSeverityHelpers:
    """Tests for severity-based helper methods."""

    def test_is_absolute_true(self):
        """Test is_absolute returns True for severity >= 90."""
        rule = WorldRule(name="Test", severity=90)
        assert rule.is_absolute() is True

        rule2 = WorldRule(name="Test2", severity=100)
        assert rule2.is_absolute() is True

    def test_is_absolute_false(self):
        """Test is_absolute returns False for severity < 90."""
        rule = WorldRule(name="Test", severity=89)
        assert rule.is_absolute() is False

    def test_is_flexible_true(self):
        """Test is_flexible returns True for severity < 30."""
        rule = WorldRule(name="Test", severity=29)
        assert rule.is_flexible() is True

        rule2 = WorldRule(name="Test2", severity=0)
        assert rule2.is_flexible() is True

    def test_is_flexible_false(self):
        """Test is_flexible returns False for severity >= 30."""
        rule = WorldRule(name="Test", severity=30)
        assert rule.is_flexible() is False

    def test_is_magic_rule(self):
        """Test is_magic_rule helper."""
        rule = WorldRule(name="Test", category="magic")
        assert rule.is_magic_rule() is True

        rule2 = WorldRule(name="Test2", category="physics")
        assert rule2.is_magic_rule() is False

    def test_is_physics_rule(self):
        """Test is_physics_rule helper."""
        rule = WorldRule(name="Test", category="physics")
        assert rule.is_physics_rule() is True

        rule2 = WorldRule(name="Test2", category="magic")
        assert rule2.is_physics_rule() is False


class TestWorldRuleGetSummary:
    """Tests for get_summary method."""

    def test_get_summary_short_consequence(self):
        """Test summary with short consequence."""
        rule = WorldRule(
            name="Magic Cost",
            consequence="Drains stamina"
        )

        summary = rule.get_summary()
        assert summary == "Magic Cost: Drains stamina"

    def test_get_summary_long_consequence_truncated(self):
        """Test summary truncates long consequence."""
        long_consequence = "x" * 150
        rule = WorldRule(
            name="Long Rule",
            consequence=long_consequence
        )

        summary = rule.get_summary()
        assert len(summary) < len(rule.name) + len(long_consequence) + 5
        assert summary.endswith("...")

    def test_get_summary_no_consequence(self):
        """Test summary with no consequence."""
        rule = WorldRule(name="Empty Rule")

        summary = rule.get_summary()
        assert "No consequence defined" in summary


class TestWorldRuleFactoryMethods:
    """Tests for factory methods."""

    def test_create_magic_rule(self):
        """Test factory for magic rules."""
        rule = WorldRule.create_magic_rule(
            name="Magic Costs Stamina",
            description="All magic drains energy.",
            consequence="Exhaustion after casting.",
            exceptions=["Divine magic is exempt"],
        )

        assert rule.name == "Magic Costs Stamina"
        assert rule.category == "magic"
        assert rule.severity == 75  # Default magic severity
        assert rule.exceptions == ["Divine magic is exempt"]

    def test_create_physics_rule(self):
        """Test factory for physics rules."""
        rule = WorldRule.create_physics_rule(
            name="Law of Gravity",
            description="Objects fall towards ground.",
            consequence="Characters fall when unsupported.",
        )

        assert rule.name == "Law of Gravity"
        assert rule.category == "physics"
        assert rule.severity == 100  # Absolute physics

    def test_create_social_rule(self):
        """Test factory for social rules."""
        rule = WorldRule.create_social_rule(
            name="Royal Protocol",
            description="Bow before the king.",
            consequence="Social disgrace if violated.",
        )

        assert rule.name == "Royal Protocol"
        assert rule.category == "social"
        assert rule.severity == 40  # Flexible social rules


class TestWorldRuleSerialization:
    """Tests for serialization methods."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        rule = WorldRule(
            name="Magic Costs Stamina",
            description="All magic drains energy.",
            consequence="Exhaustion after casting.",
            exceptions=["Divine magic"],
            category="magic",
            severity=75,
        )

        data = rule.to_dict()

        assert data["name"] == "Magic Costs Stamina"
        assert data["description"] == "All magic drains energy."
        assert data["consequence"] == "Exhaustion after casting."
        assert data["exceptions"] == ["Divine magic"]
        assert data["category"] == "magic"
        assert data["severity"] == 75
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "version" in data
