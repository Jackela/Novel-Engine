#!/usr/bin/env python3
"""
Term Guard - IP Cleaning and Content Filtering Tool
==================================================

Automated tool for identifying and cleaning potential intellectual property
violations from generated content. Part of the Novel Engine's legal
safeguards system to ensure compliance with copyright restrictions.

This tool provides:
1. Multi-layered content analysis and filtering
2. Configurable term detection and replacement
3. Context-aware IP violation identification
4. Safe content generation assistance
5. Compliance reporting and audit trails

The Term Guard operates as a content sanitization pipeline that can be
integrated into the content generation workflow to provide real-time
IP protection and compliance validation.

Architecture Reference:
- docs/ADRs/ADR-004-ip-protection.md - IP protection strategy
- docs/LEGAL.md - Legal compliance requirements
- settings.yaml - IP filtering configuration

Development Phase: Work Order PR-04 - IP Cleaning Tool Implementation
"""

import argparse
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# Configure logging for the Term Guard system
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ViolationType(str, Enum):
    """Types of IP violations that can be detected."""

    TRADEMARK = "trademark"
    CHARACTER_NAME = "character_name"
    LOCATION_NAME = "location_name"
    FACTION_NAME = "faction_name"
    TERMINOLOGY = "terminology"
    COPYRIGHTED_PHRASE = "copyrighted_phrase"
    PROPER_NOUN = "proper_noun"


class FilterAction(str, Enum):
    """Actions to take when IP violations are detected."""

    REMOVE = "remove"
    REPLACE = "replace"
    GENERIC = "generic"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class IPViolation:
    """Represents a detected intellectual property violation."""

    term: str
    violation_type: ViolationType
    context: str
    position: Tuple[int, int]  # start, end positions
    confidence: float
    suggested_replacement: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class FilterRule:
    """Rule for detecting and handling IP violations."""

    pattern: str
    violation_type: ViolationType
    action: FilterAction
    replacement: Optional[str] = None
    confidence_threshold: float = 0.8
    case_sensitive: bool = False
    word_boundary: bool = True
    exceptions: List[str] = field(default_factory=list)


@dataclass
class CleaningReport:
    """Report of content cleaning operations performed."""

    original_length: int
    cleaned_length: int
    violations_found: List[IPViolation]
    actions_taken: List[str]
    confidence_score: float
    timestamp: datetime = field(default_factory=datetime.now)
    safe_for_use: bool = True


class TermGuard:
    """
    Main IP cleaning and content filtering system.

    Provides comprehensive content analysis and cleaning capabilities
    with configurable rules and multi-layered filtering approach.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the Term Guard system.

        Args:
            config_path: Path to configuration file, defaults to settings.yaml
        """
        self.config_path = config_path or Path("settings.yaml")
        self.filter_rules: List[FilterRule] = []
        self.whitelist_terms: Set[str] = set()
        self.replacement_dict: Dict[str, str] = {}

        # Load configuration and initialize filtering rules
        self._load_configuration()
        self._initialize_default_rules()

        logger.info(
            f"🛡️ Term Guard initialized with {len(self.filter_rules)} filter rules"
        )

    def _load_configuration(self):
        """Load filtering configuration from settings file."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                # Extract IP filtering configuration
                ip_config = config.get("ip_filtering", {})

                # Load custom filter rules
                for rule_data in ip_config.get("custom_rules", []):
                    rule = FilterRule(
                        pattern=rule_data["pattern"],
                        violation_type=ViolationType(rule_data["type"]),
                        action=FilterAction(rule_data["action"]),
                        replacement=rule_data.get("replacement"),
                        confidence_threshold=rule_data.get("confidence", 0.8),
                        case_sensitive=rule_data.get("case_sensitive", False),
                        word_boundary=rule_data.get("word_boundary", True),
                        exceptions=rule_data.get("exceptions", []),
                    )
                    self.filter_rules.append(rule)

                # Load whitelist terms
                self.whitelist_terms.update(ip_config.get("whitelist", []))

                # Load replacement dictionary
                self.replacement_dict.update(ip_config.get("replacements", {}))

                logger.info(f"✅ Loaded configuration from {self.config_path}")
            else:
                logger.warning(
                    f"⚠️ Configuration file {self.config_path} not found, using defaults"
                )

        except Exception as e:
            logger.error(f"❌ Error loading configuration: {e}")

    def _initialize_default_rules(self):
        """Initialize default IP filtering rules for common violations."""

        # Novel Engine specific terms (example patterns)
        default_rules = [
            # Character names
            FilterRule(
                pattern=r"\b(Primarch|Space Marine|Adeptus|Astartes|Commissar)\b",
                violation_type=ViolationType.CHARACTER_NAME,
                action=FilterAction.REPLACE,
                replacement="Imperial Warrior",
                confidence_threshold=0.9,
            ),
            # Faction names
            FilterRule(
                pattern=r"\b(Imperium of Man|Chaos|Tyranids|Eldar|Orks|Tau Empire)\b",
                violation_type=ViolationType.FACTION_NAME,
                action=FilterAction.GENERIC,
                confidence_threshold=0.85,
            ),
            # Location names
            FilterRule(
                pattern=r"\b(Terra|Holy Terra|Cadia|Macragge|Ultramar)\b",
                violation_type=ViolationType.LOCATION_NAME,
                action=FilterAction.REPLACE,
                replacement="The Capital World",
                confidence_threshold=0.8,
            ),
            # Trademarked terminology
            FilterRule(
                pattern=r"\b(Novel Engine|Games Workshop|Black Library)\b",
                violation_type=ViolationType.TRADEMARK,
                action=FilterAction.BLOCK,
                confidence_threshold=0.95,
            ),
            # Generic copyrighted phrases
            FilterRule(
                pattern=r"In the grim darkness of the far future",
                violation_type=ViolationType.COPYRIGHTED_PHRASE,
                action=FilterAction.REPLACE,
                replacement="In a dark and distant future",
                confidence_threshold=0.99,
            ),
        ]

        # Only add default rules if no custom rules loaded
        if not self.filter_rules:
            self.filter_rules.extend(default_rules)
            logger.info("📋 Loaded default IP filtering rules")

    def analyze_content(self, content: str) -> List[IPViolation]:
        """
        Analyze content for potential IP violations.

        Args:
            content: Text content to analyze

        Returns:
            List of detected IP violations
        """
        violations = []

        for rule in self.filter_rules:
            # Skip if term is whitelisted
            if any(
                whitelist_term.lower() in content.lower()
                for whitelist_term in rule.exceptions
            ):
                continue

            # Compile regex pattern
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            if rule.word_boundary:
                pattern = rf"\b{rule.pattern}\b"
            else:
                pattern = rule.pattern

            try:
                matches = re.finditer(pattern, content, flags)

                for match in matches:
                    # Skip whitelisted terms
                    matched_term = match.group(0)
                    if matched_term.lower() in [
                        term.lower() for term in self.whitelist_terms
                    ]:
                        continue

                    # Extract context around the match
                    start, end = match.span()
                    context_start = max(0, start - 50)
                    context_end = min(len(content), end + 50)
                    context = content[context_start:context_end]

                    # Create violation record
                    violation = IPViolation(
                        term=matched_term,
                        violation_type=rule.violation_type,
                        context=context,
                        position=(start, end),
                        confidence=rule.confidence_threshold,
                        suggested_replacement=rule.replacement,
                    )

                    violations.append(violation)

            except re.error as e:
                logger.warning(f"⚠️ Invalid regex pattern '{rule.pattern}': {e}")

        logger.info(
            f"🔍 Analyzed content: found {len(violations)} potential violations"
        )
        return violations

    def clean_content(
        self, content: str, apply_fixes: bool = True
    ) -> Tuple[str, CleaningReport]:
        """
        Clean content by removing or replacing IP violations.

        Args:
            content: Original content to clean
            apply_fixes: Whether to apply automatic fixes

        Returns:
            Tuple of (cleaned_content, cleaning_report)
        """
        original_content = content
        violations = self.analyze_content(content)
        actions_taken = []

        if apply_fixes:
            # Sort violations by position (reverse order to maintain indices)
            violations.sort(key=lambda v: v.position[0], reverse=True)

            for violation in violations:
                start, end = violation.position

                # Get the rule for this violation
                matching_rule = self._find_matching_rule(violation)
                if not matching_rule:
                    continue

                if matching_rule.action == FilterAction.REMOVE:
                    content = content[:start] + content[end:]
                    actions_taken.append(f"Removed '{violation.term}'")

                elif (
                    matching_rule.action == FilterAction.REPLACE
                    and matching_rule.replacement
                ):
                    content = (
                        content[:start] + matching_rule.replacement + content[end:]
                    )
                    actions_taken.append(
                        f"Replaced '{violation.term}' with '{matching_rule.replacement}'"
                    )

                elif matching_rule.action == FilterAction.GENERIC:
                    generic_replacement = self._generate_generic_replacement(violation)
                    content = content[:start] + generic_replacement + content[end:]
                    actions_taken.append(
                        f"Genericized '{violation.term}' to '{generic_replacement}'"
                    )

                elif matching_rule.action == FilterAction.BLOCK:
                    # For blocking, we replace with safe placeholder
                    content = content[:start] + "[CONTENT_FILTERED]" + content[end:]
                    actions_taken.append(f"Blocked '{violation.term}'")

                elif matching_rule.action == FilterAction.WARN:
                    actions_taken.append(
                        f"Warning: '{violation.term}' flagged for review"
                    )

        # Calculate overall confidence score
        if violations:
            confidence_score = sum(v.confidence for v in violations) / len(violations)
        else:
            confidence_score = 1.0

        # Determine if content is safe for use
        critical_violations = [v for v in violations if v.confidence > 0.9]
        safe_for_use = len(critical_violations) == 0

        # Generate cleaning report
        report = CleaningReport(
            original_length=len(original_content),
            cleaned_length=len(content),
            violations_found=violations,
            actions_taken=actions_taken,
            confidence_score=confidence_score,
            safe_for_use=safe_for_use,
        )

        logger.info(
            f"🧹 Cleaned content: {len(violations)} violations processed, "
            f"{len(actions_taken)} actions taken"
        )

        return content, report

    def _find_matching_rule(self, violation: IPViolation) -> Optional[FilterRule]:
        """Find the filter rule that matched a given violation."""
        for rule in self.filter_rules:
            if rule.violation_type == violation.violation_type:
                # Additional pattern matching if needed
                flags = 0 if rule.case_sensitive else re.IGNORECASE
                if re.search(rule.pattern, violation.term, flags):
                    return rule
        return None

    def _generate_generic_replacement(self, violation: IPViolation) -> str:
        """Generate a generic replacement for IP violations."""
        generic_map = {
            ViolationType.CHARACTER_NAME: "Character",
            ViolationType.FACTION_NAME: "Faction",
            ViolationType.LOCATION_NAME: "Location",
            ViolationType.TERMINOLOGY: "Term",
            ViolationType.PROPER_NOUN: "Entity",
        }

        base_replacement = generic_map.get(violation.violation_type, "Entity")

        # Add some variety with hash-based selection
        term_hash = hashlib.md5(violation.term.encode()).hexdigest()
        suffix_num = int(term_hash[:2], 16) % 100

        return f"{base_replacement}_{suffix_num:02d}"

    def generate_compliance_report(
        self, reports: List[CleaningReport]
    ) -> Dict[str, Any]:
        """
        Generate compliance report from multiple cleaning operations.

        Args:
            reports: List of cleaning reports to analyze

        Returns:
            Comprehensive compliance analysis
        """
        if not reports:
            return {"status": "no_data", "message": "No cleaning reports provided"}

        total_violations = sum(len(r.violations_found) for r in reports)
        total_actions = sum(len(r.actions_taken) for r in reports)
        avg_confidence = sum(r.confidence_score for r in reports) / len(reports)

        violation_types = {}
        for report in reports:
            for violation in report.violations_found:
                vtype = violation.violation_type.value
                violation_types[vtype] = violation_types.get(vtype, 0) + 1

        safe_percentage = (
            sum(1 for r in reports if r.safe_for_use) / len(reports)
        ) * 100

        compliance_report = {
            "summary": {
                "total_documents_processed": len(reports),
                "total_violations_found": total_violations,
                "total_actions_taken": total_actions,
                "average_confidence_score": round(avg_confidence, 3),
                "safe_content_percentage": round(safe_percentage, 1),
            },
            "violation_breakdown": violation_types,
            "recommendations": self._generate_compliance_recommendations(reports),
            "generated_at": datetime.now().isoformat(),
        }

        return compliance_report

    def _generate_compliance_recommendations(
        self, reports: List[CleaningReport]
    ) -> List[str]:
        """Generate compliance recommendations based on analysis."""
        recommendations = []

        total_violations = sum(len(r.violations_found) for r in reports)
        if total_violations > 10:
            recommendations.append(
                "High violation count detected - consider reviewing content generation parameters"
            )

        critical_violations = sum(
            1 for r in reports for v in r.violations_found if v.confidence > 0.9
        )
        if critical_violations > 0:
            recommendations.append(
                f"{critical_violations} critical violations found - manual review recommended"
            )

        unsafe_content = sum(1 for r in reports if not r.safe_for_use)
        if unsafe_content > 0:
            recommendations.append(
                f"{unsafe_content} documents flagged as unsafe - additional filtering required"
            )

        if not recommendations:
            recommendations.append(
                "Content analysis shows good compliance - continue current practices"
            )

        return recommendations


def main():
    """Command-line interface for the Term Guard tool."""
    parser = argparse.ArgumentParser(description="Novel Engine IP Cleaning Tool")
    parser.add_argument("--input", "-i", type=Path, help="Input file to analyze")
    parser.add_argument(
        "--output", "-o", type=Path, help="Output file for cleaned content"
    )
    parser.add_argument("--config", "-c", type=Path, help="Configuration file path")
    parser.add_argument(
        "--analyze-only", action="store_true", help="Only analyze, don't clean"
    )
    parser.add_argument("--report", "-r", type=Path, help="Generate compliance report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize Term Guard
    term_guard = TermGuard(config_path=args.config)

    if args.input:
        # Process input file
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                content = f.read()

            if args.analyze_only:
                violations = term_guard.analyze_content(content)
                print("\n🔍 Analysis Results:")
                print(f"Found {len(violations)} potential IP violations")

                for i, violation in enumerate(violations, 1):
                    print(
                        f"\n{i}. {violation.violation_type.value.title()}: '{violation.term}'"
                    )
                    print(f"   Context: ...{violation.context}...")
                    print(f"   Confidence: {violation.confidence:.2f}")
                    if violation.suggested_replacement:
                        print(f"   Suggested: '{violation.suggested_replacement}'")
            else:
                cleaned_content, report = term_guard.clean_content(content)

                print("\n🧹 Cleaning Results:")
                print(f"Original length: {report.original_length} characters")
                print(f"Cleaned length: {report.cleaned_length} characters")
                print(f"Violations found: {len(report.violations_found)}")
                print(f"Actions taken: {len(report.actions_taken)}")
                print(f"Safe for use: {'✅' if report.safe_for_use else '❌'}")

                if args.output:
                    with open(args.output, "w", encoding="utf-8") as f:
                        f.write(cleaned_content)
                    print(f"✅ Cleaned content saved to {args.output}")

                if args.report:
                    compliance_report = term_guard.generate_compliance_report([report])
                    with open(args.report, "w", encoding="utf-8") as f:
                        json.dump(compliance_report, f, indent=2)
                    print(f"📊 Compliance report saved to {args.report}")

        except FileNotFoundError:
            print(f"❌ Error: Input file '{args.input}' not found")
            return 1
        except Exception as e:
            print(f"❌ Error processing file: {e}")
            return 1
    else:
        # Interactive mode
        print("🛡️ Term Guard - IP Cleaning Tool")
        print("Enter text content to analyze (press Ctrl+D when finished):")
        print("-" * 50)

        try:
            import sys

            content = sys.stdin.read()

            cleaned_content, report = term_guard.clean_content(content)

            print("\n" + "=" * 50)
            print("🧹 CLEANING RESULTS")
            print("=" * 50)
            print(f"Violations found: {len(report.violations_found)}")
            print(f"Actions taken: {len(report.actions_taken)}")
            print(f"Safe for use: {'✅' if report.safe_for_use else '❌'}")

            if report.actions_taken:
                print("\nActions performed:")
                for action in report.actions_taken:
                    print(f"  • {action}")

            print("\nCleaned content:")
            print("-" * 30)
            print(cleaned_content)
            print("-" * 30)

        except KeyboardInterrupt:
            print("\n👋 Term Guard session ended")

    return 0


if __name__ == "__main__":
    exit(main())
