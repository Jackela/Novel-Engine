"""
Test Term Guard IP Cleaning Tool
===============================

Comprehensive test suite for the Term Guard IP cleaning and content filtering system.
Tests ensure proper detection, cleaning, and compliance reporting functionality.

Test Coverage:
- IP violation detection accuracy
- Content cleaning and replacement logic
- Filter rule configuration and application
- Compliance reporting and analysis
- Command-line interface functionality
- Integration with Novel Engine settings
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

# Import the Term Guard system
try:
    from scripts.term_guard import (
        CleaningReport,
        FilterAction,
        FilterRule,
        IPViolation,
        TermGuard,
        ViolationType,
    )

    TERM_GUARD_AVAILABLE = True
except ImportError as e:
    TERM_GUARD_AVAILABLE = False
    pytest.skip(f"Term Guard not available: {e}", allow_module_level=True)


class TestFilterRule:
    """Test FilterRule data structure and validation."""

    def test_filter_rule_creation(self):
        """Test creating filter rules with valid parameters."""
        rule = FilterRule(
            pattern=r"\bVanguard Paladin\b",
            violation_type=ViolationType.CHARACTER_NAME,
            action=FilterAction.REPLACE,
            replacement="Alliance Paladin",
            confidence_threshold=0.9,
        )

        assert rule.pattern == r"\bVanguard Paladin\b"
        assert rule.violation_type == ViolationType.CHARACTER_NAME
        assert rule.action == FilterAction.REPLACE
        assert rule.replacement == "Alliance Paladin"
        assert rule.confidence_threshold == 0.9
        assert rule.case_sensitive is False  # default
        assert rule.word_boundary is True  # default

    def test_filter_rule_defaults(self):
        """Test filter rule default values."""
        rule = FilterRule(
            pattern="test",
            violation_type=ViolationType.TERMINOLOGY,
            action=FilterAction.WARN,
        )

        assert rule.confidence_threshold == 0.8
        assert rule.case_sensitive is False
        assert rule.word_boundary is True
        assert rule.exceptions == []


class TestIPViolation:
    """Test IPViolation data structure."""

    def test_ip_violation_creation(self):
        """Test creating IP violation records."""
        violation = IPViolation(
            term="Vanguard Paladin",
            violation_type=ViolationType.CHARACTER_NAME,
            context="The Vanguard Paladin advanced through the ruins",
            position=(4, 15),
            confidence=0.9,
            suggested_replacement="Alliance Paladin",
        )

        assert violation.term == "Vanguard Paladin"
        assert violation.violation_type == ViolationType.CHARACTER_NAME
        assert violation.context == "The Vanguard Paladin advanced through the ruins"
        assert violation.position == (4, 15)
        assert violation.confidence == 0.9
        assert violation.suggested_replacement == "Alliance Paladin"
        assert violation.severity == "medium"  # default


class TestTermGuard:
    """Test main Term Guard functionality."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary configuration file for testing."""
        config_data = {
            "ip_filtering": {
                "enable": True,
                "confidence_threshold": 0.8,
                "whitelist": ["Alliance Network", "Guard"],
                "replacements": {
                    "Vanguard Paladin": "Alliance Network Marine",
                    "Commandant": "Officer",
                },
                "custom_rules": [
                    {
                        "pattern": r"\bVanguard Paladin\b",
                        "type": "character_name",
                        "action": "replace",
                        "replacement": "Alliance Network Marine",
                        "confidence": 0.9,
                        "case_sensitive": False,
                        "word_boundary": True,
                    },
                    {
                        "pattern": r"\blegacy franchise\b",
                        "type": "trademark",
                        "action": "block",
                        "confidence": 0.95,
                        "case_sensitive": False,
                        "word_boundary": True,
                    },
                ],
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_term_guard_initialization(self, temp_config):
        """Test Term Guard initialization with configuration."""
        guard = TermGuard(config_path=temp_config)

        assert len(guard.filter_rules) >= 2  # At least our custom rules
        assert "Alliance Network" in guard.whitelist_terms
        assert "Guard" in guard.whitelist_terms
        assert guard.replacement_dict["Vanguard Paladin"] == "Alliance Network Marine"
        assert guard.replacement_dict["Commandant"] == "Officer"

    def test_term_guard_default_initialization(self):
        """Test Term Guard initialization with defaults."""
        with patch("pathlib.Path.exists", return_value=False):
            guard = TermGuard(config_path=Path("nonexistent.yaml"))

        # Should have default rules loaded
        assert len(guard.filter_rules) > 0
        assert any(
            rule.violation_type == ViolationType.CHARACTER_NAME
            for rule in guard.filter_rules
        )

    def test_analyze_content_basic(self, temp_config):
        """Test basic content analysis functionality."""
        guard = TermGuard(config_path=temp_config)

        content = (
            "The Vanguard Paladin fought valiantly against the legacy franchise forces."
        )
        violations = guard.analyze_content(content)

        # Should detect both Vanguard Paladin and legacy franchise
        assert len(violations) >= 2

        # Check Vanguard Paladin detection
        space_marine_violations = [
            v for v in violations if v.term == "Vanguard Paladin"
        ]
        assert len(space_marine_violations) == 1
        assert space_marine_violations[0].violation_type == ViolationType.CHARACTER_NAME

        # Check legacy franchise detection
        legacy_violations = [v for v in violations if v.term == "legacy franchise"]
        assert len(legacy_violations) == 1
        assert legacy_violations[0].violation_type == ViolationType.TRADEMARK

    def test_analyze_content_whitelist(self, temp_config):
        """Test content analysis respects whitelist."""
        guard = TermGuard(config_path=temp_config)

        content = "The Alliance Guard defended their position."
        violations = guard.analyze_content(content)

        # Should not detect whitelisted terms
        violation_terms = [v.term for v in violations]
        assert "Alliance Network" not in violation_terms
        assert "Guard" not in violation_terms

    def test_clean_content_replace(self, temp_config):
        """Test content cleaning with replacement action."""
        guard = TermGuard(config_path=temp_config)

        content = "The Vanguard Paladin advanced through the battlefield."
        cleaned_content, report = guard.clean_content(content)

        assert "Vanguard Paladin" not in cleaned_content
        assert "Alliance Network Marine" in cleaned_content
        assert len(report.violations_found) >= 1
        assert len(report.actions_taken) >= 1
        assert (
            "Replaced 'Vanguard Paladin' with 'Alliance Network Marine'"
            in report.actions_taken
        )

    def test_clean_content_block(self, temp_config):
        """Test content cleaning with block action."""
        guard = TermGuard(config_path=temp_config)

        content = "This is based on legacy franchise 40,000 universe."
        cleaned_content, report = guard.clean_content(content)

        assert "legacy franchise" not in cleaned_content
        assert "[CONTENT_FILTERED]" in cleaned_content
        assert len(report.violations_found) >= 1
        assert any(
            "Blocked 'legacy franchise'" in action for action in report.actions_taken
        )

    def test_clean_content_analyze_only(self, temp_config):
        """Test content analysis without applying fixes."""
        guard = TermGuard(config_path=temp_config)

        content = "The Vanguard Paladin fought against legacy franchise enemies."
        cleaned_content, report = guard.clean_content(content, apply_fixes=False)

        # Content should be unchanged
        assert cleaned_content == content
        assert len(report.violations_found) >= 2
        assert len(report.actions_taken) == 0  # No fixes applied

    def test_generic_replacement_generation(self, temp_config):
        """Test generic replacement generation."""
        guard = TermGuard(config_path=temp_config)

        # Create a violation that would trigger generic replacement
        violation = IPViolation(
            term="TestFaction",
            violation_type=ViolationType.FACTION_NAME,
            context="The TestFaction army marched forward",
            position=(4, 15),
            confidence=0.8,
        )

        replacement = guard._generate_generic_replacement(violation)

        assert replacement.startswith("Faction_")
        assert len(replacement) > len("Faction_")

    def test_compliance_report_generation(self, temp_config):
        """Test compliance report generation."""
        guard = TermGuard(config_path=temp_config)

        # Create sample cleaning reports
        violation1 = IPViolation(
            term="Vanguard Paladin",
            violation_type=ViolationType.CHARACTER_NAME,
            context="context",
            position=(0, 12),
            confidence=0.9,
        )

        violation2 = IPViolation(
            term="legacy franchise",
            violation_type=ViolationType.TRADEMARK,
            context="context",
            position=(0, 9),
            confidence=0.95,
        )

        reports = [
            CleaningReport(
                original_length=100,
                cleaned_length=95,
                violations_found=[violation1],
                actions_taken=["Replaced 'Vanguard Paladin'"],
                confidence_score=0.9,
                safe_for_use=True,
            ),
            CleaningReport(
                original_length=80,
                cleaned_length=70,
                violations_found=[violation2],
                actions_taken=["Blocked 'legacy franchise'"],
                confidence_score=0.95,
                safe_for_use=False,  # Blocked content
            ),
        ]

        compliance_report = guard.generate_compliance_report(reports)

        assert compliance_report["summary"]["total_documents_processed"] == 2
        assert compliance_report["summary"]["total_violations_found"] == 2
        assert compliance_report["summary"]["total_actions_taken"] == 2
        assert (
            compliance_report["summary"]["safe_content_percentage"] == 50.0
        )  # 1 of 2 safe

        assert "character_name" in compliance_report["violation_breakdown"]
        assert "trademark" in compliance_report["violation_breakdown"]
        assert len(compliance_report["recommendations"]) > 0

    def test_compliance_report_empty(self, temp_config):
        """Test compliance report with no data."""
        guard = TermGuard(config_path=temp_config)

        compliance_report = guard.generate_compliance_report([])

        assert compliance_report["status"] == "no_data"
        assert "message" in compliance_report


class TestTermGuardIntegration:
    """Test Term Guard integration scenarios."""

    def test_complex_content_cleaning(self):
        """Test cleaning complex content with multiple violation types."""
        # Use default configuration for this test
        guard = TermGuard()

        content = """
        In the grim darkness of the far future, the Vanguard Paladins of the First Vanguard Circle Chapter
        defended Terra against Entropy forces. The Commandant ordered his men to hold the line
        with their Pulse Rifles and Mag Cannons. The First Mentor would be proud.
        """

        cleaned_content, report = guard.clean_content(content)

        # Should detect and clean multiple violations
        assert len(report.violations_found) > 0
        assert len(report.actions_taken) > 0

        # Check that high-confidence violations were addressed
        high_confidence_violations = [
            v for v in report.violations_found if v.confidence > 0.9
        ]
        if high_confidence_violations:
            # Ensure critical violations were handled
            assert not report.safe_for_use or len(high_confidence_violations) == 0

    def test_configuration_error_handling(self):
        """Test Term Guard handles configuration errors gracefully."""
        # Test with invalid configuration file
        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "builtins.open", mock_open(read_data="invalid: yaml: content: [")
            ):
                guard = TermGuard(config_path=Path("invalid.yaml"))

                # Should still initialize with default rules
                assert len(guard.filter_rules) > 0

    def test_regex_error_handling(self):
        """Test handling of invalid regex patterns."""
        # Create Term Guard with invalid regex pattern
        guard = TermGuard()

        # Add invalid regex rule
        invalid_rule = FilterRule(
            pattern=r"[invalid_regex",  # Unclosed bracket
            violation_type=ViolationType.TERMINOLOGY,
            action=FilterAction.WARN,
            confidence_threshold=0.8,
        )
        guard.filter_rules.append(invalid_rule)

        content = "Test content with some text"
        violations = guard.analyze_content(content)

        # Should not crash, invalid regex should be skipped
        assert isinstance(violations, list)


class TestTermGuardCLI:
    """Test Term Guard command-line interface."""

    @pytest.fixture
    def temp_input_file(self):
        """Create temporary input file for CLI testing."""
        content = "The Vanguard Paladin fought against the legacy franchise enemies in the grim darkness."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        yield temp_path
        temp_path.unlink()

    def test_cli_analyze_only(self, temp_input_file, capsys):
        """Test CLI analyze-only mode."""
        from scripts.term_guard import main

        # Mock command line arguments
        with patch(
            "sys.argv",
            ["term_guard.py", "--input", str(temp_input_file), "--analyze-only"],
        ):
            result = main()

        assert result == 0  # Success

        captured = capsys.readouterr()
        assert "Analysis Results" in captured.out
        assert "potential IP violations" in captured.out

    def test_cli_clean_with_output(self, temp_input_file, tmp_path):
        """Test CLI cleaning with output file."""
        from scripts.term_guard import main

        output_file = tmp_path / "cleaned_output.txt"

        with patch(
            "sys.argv",
            [
                "term_guard.py",
                "--input",
                str(temp_input_file),
                "--output",
                str(output_file),
            ],
        ):
            result = main()

        assert result == 0  # Success
        assert output_file.exists()

        # Verify output file contains cleaned content
        cleaned_content = output_file.read_text(encoding="utf-8")
        assert len(cleaned_content) > 0

    def test_cli_compliance_report(self, temp_input_file, tmp_path):
        """Test CLI compliance report generation."""
        from scripts.term_guard import main

        report_file = tmp_path / "compliance_report.json"

        with patch(
            "sys.argv",
            [
                "term_guard.py",
                "--input",
                str(temp_input_file),
                "--report",
                str(report_file),
            ],
        ):
            result = main()

        assert result == 0  # Success
        assert report_file.exists()

        # Verify report file contains valid JSON
        report_data = json.loads(report_file.read_text(encoding="utf-8"))
        assert "summary" in report_data
        assert "violation_breakdown" in report_data
        assert "recommendations" in report_data

    def test_cli_file_not_found(self, capsys):
        """Test CLI behavior with non-existent input file."""
        from scripts.term_guard import main

        with patch("sys.argv", ["term_guard.py", "--input", "nonexistent_file.txt"]):
            result = main()

        assert result == 1  # Error

        captured = capsys.readouterr()
        assert "Error: Input file" in captured.out
        assert "not found" in captured.out
