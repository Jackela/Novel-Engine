#!/usr/bin/env python3
"""
Test Pyramid Monitor (Fast Version)
====================================

Faster monitoring by parsing test files directly instead of running pytest multiple times.

Usage:
    python test-pyramid-monitor-fast.py                    # Console report
    python test-pyramid-monitor-fast.py --format json      # JSON output
    python test-pyramid-monitor-fast.py --format html      # HTML report
    python test-pyramid-monitor-fast.py --format markdown  # Markdown report
    python test-pyramid-monitor-fast.py --save-history     # Save historical data
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set


class FastTestPyramidMonitor:
    """Fast test pyramid monitor using file parsing."""

    TARGETS = {
        "unit": 70.0,
        "integration": 20.0,
        "e2e": 10.0,
    }

    def __init__(self, project_root: Path = None):
        """Initialize monitor."""
        self.project_root = project_root or Path.cwd()
        self.history_dir = self.project_root / ".pyramid-history"
        self.tests_by_marker: Dict[str, Set[str]] = {
            "unit": set(),
            "integration": set(),
            "e2e": set(),
        }
        self.all_tests: Set[str] = set()
        self.test_files_scanned = 0

    def collect_tests(self) -> bool:
        """Collect tests by scanning test files."""
        print("Scanning test files...", file=sys.stderr)

        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            print(f"Error: tests directory not found at {tests_dir}", file=sys.stderr)
            return False

        # Find all test files
        test_files = list(tests_dir.rglob("test_*.py"))
        self.test_files_scanned = len(test_files)

        print(f"Found {len(test_files)} test files", file=sys.stderr)

        # Parse each file
        for test_file in test_files:
            self._parse_test_file(test_file)

        print(f"Collected {len(self.all_tests)} tests total", file=sys.stderr)
        return True

    def _parse_test_file(self, file_path: Path) -> None:
        """Parse a test file to extract test functions and their markers."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find test functions
            test_pattern = re.compile(r"^    def (test_\w+)", re.MULTILINE)
            class_pattern = re.compile(r"^class (Test\w+)", re.MULTILINE)

            # Track class-level and function-level markers separately
            class_markers = set()
            function_markers = set()

            lines = content.split("\n")
            current_class = None

            for i, line in enumerate(lines):
                # Check for class markers
                class_match = class_pattern.match(line)
                if class_match:
                    current_class = class_match.group(1)
                    # Reset class markers for new class
                    class_markers = set()
                    function_markers = set()
                    # Look back for markers before class
                    for j in range(max(0, i - 10), i):
                        marker_match = re.search(
                            r"@pytest\.mark\.(unit|integration|e2e)", lines[j]
                        )
                        if marker_match:
                            class_markers.add(marker_match.group(1))

                # Check for test function markers
                if line.strip().startswith("@pytest.mark."):
                    marker_match = re.search(
                        r"@pytest\.mark\.(unit|integration|e2e)", line
                    )
                    if marker_match:
                        function_markers.add(marker_match.group(1))

                # Check for test function
                test_match = test_pattern.match(line)
                if test_match:
                    test_name = test_match.group(1)
                    test_id = f"{file_path.relative_to(self.project_root)}::{current_class or ''}{test_name}"

                    # Add to all tests
                    self.all_tests.add(test_id)

                    # Combine class and function markers
                    effective_markers = class_markers | function_markers

                    # Add to marker sets
                    if effective_markers:
                        for marker in effective_markers:
                            if marker in self.tests_by_marker:
                                self.tests_by_marker[marker].add(test_id)

                    # Reset only function-level markers (class markers persist)
                    function_markers = set()

        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)

    def calculate_distribution(self) -> Dict[str, float]:
        """Calculate percentage distribution."""
        total = len(self.all_tests)
        if total == 0:
            return {marker: 0.0 for marker in self.TARGETS}

        distribution = {}
        for marker in self.TARGETS:
            count = len(self.tests_by_marker[marker])
            distribution[marker] = (count / total) * 100

        return distribution

    def calculate_score(self, distribution: Dict[str, float]) -> float:
        """Calculate pyramid score (0-10)."""
        score = 10.0

        for marker, target in self.TARGETS.items():
            actual = distribution[marker]
            deviation = abs(actual - target)
            penalty = deviation * 0.1
            score -= penalty

        # Penalty for uncategorized tests
        categorized = sum(len(tests) for tests in self.tests_by_marker.values())
        uncategorized = len(self.all_tests) - categorized
        if uncategorized > 0 and len(self.all_tests) > 0:
            uncategorized_pct = (uncategorized / len(self.all_tests)) * 100
            score -= uncategorized_pct * 0.2

        return max(0.0, min(10.0, score))

    def get_missing_markers_count(self) -> int:
        """Get count of tests without pyramid markers."""
        categorized = set()
        for tests in self.tests_by_marker.values():
            categorized.update(tests)
        return len(self.all_tests - categorized)

    def generate_console_report(
        self, distribution: Dict[str, float], score: float
    ) -> str:
        """Generate ASCII console report."""
        lines = []
        lines.append("=" * 80)
        lines.append(" " * 25 + "TEST PYRAMID REPORT")
        lines.append("=" * 80)
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Score: {score:.1f}/10.0")
        lines.append("")
        lines.append("DISTRIBUTION:")

        for marker in ["unit", "integration", "e2e"]:
            count = len(self.tests_by_marker[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            # Create progress bar (20 chars max)
            bar_length = 20
            filled = int((pct / 100) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)

            delta_str = f"{delta:+.1f}%" if delta != 0 else " 0.0%"

            lines.append(
                f"  {marker.capitalize():14} {count:5,} ({pct:5.1f}%)  "
                f"[Target: {target:4.0f}%]  {bar}  {delta_str}"
            )

        lines.append("")
        lines.append(f"TOTAL: {len(self.all_tests):,} tests")
        lines.append("")

        missing = self.get_missing_markers_count()
        if missing > 0:
            lines.append(f"MISSING MARKERS: {missing} tests need classification")
            lines.append("")

        lines.append("RECOMMENDATIONS:")
        recommendations = self._generate_recommendations(distribution)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

        lines.append("=" * 80)
        return "\n".join(lines)

    def generate_json_report(self, distribution: Dict[str, float], score: float) -> str:
        """Generate JSON report."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "score": round(score, 2),
            "total_tests": len(self.all_tests),
            "test_files_scanned": self.test_files_scanned,
            "distribution": {
                marker: {
                    "count": len(self.tests_by_marker[marker]),
                    "percentage": round(pct, 2),
                    "target": self.TARGETS[marker],
                    "delta": round(pct - self.TARGETS[marker], 2),
                }
                for marker, pct in distribution.items()
            },
            "missing_markers": self.get_missing_markers_count(),
            "recommendations": self._generate_recommendations(distribution),
        }
        return json.dumps(data, indent=2)

    def generate_markdown_report(
        self, distribution: Dict[str, float], score: float
    ) -> str:
        """Generate Markdown report."""
        lines = []
        lines.append("# Test Pyramid Report")
        lines.append("")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Score:** {score:.1f}/10.0")
        lines.append("")
        lines.append("## Distribution")
        lines.append("")
        lines.append("| Type | Count | Percentage | Target | Delta |")
        lines.append("|------|-------|------------|--------|-------|")

        for marker in ["unit", "integration", "e2e"]:
            count = len(self.tests_by_marker[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            lines.append(
                f"| {marker.capitalize()} | {count:,} | {pct:.1f}% | {target:.0f}% | {delta:+.1f}% |"
            )

        lines.append("")
        lines.append(f"**Total:** {len(self.all_tests):,} tests")
        lines.append("")

        missing = self.get_missing_markers_count()
        if missing > 0:
            lines.append(f"**Missing Markers:** {missing} tests need classification")
            lines.append("")

        lines.append("## Recommendations")
        lines.append("")
        recommendations = self._generate_recommendations(distribution)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    def generate_html_report(self, distribution: Dict[str, float], score: float) -> str:
        """Generate HTML report using template."""
        template_path = (
            self.project_root / "scripts/testing/pyramid-report-template.html"
        )

        if template_path.exists():
            with open(template_path, "r") as f:
                template = f.read()
        else:
            # Use simple inline template
            return f"<html><body><h1>Test Pyramid Report</h1><p>Score: {score:.1f}/10.0</p></body></html>"

        # Prepare data
        rows = []
        for marker in ["unit", "integration", "e2e"]:
            count = len(self.tests_by_marker[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            delta_class = "positive" if delta >= 0 else "negative"
            rows.append(
                f"<tr>"
                f"<td>{marker.capitalize()}</td>"
                f"<td>{count:,}</td>"
                f"<td>{pct:.1f}%</td>"
                f"<td>{target:.0f}%</td>"
                f"<td class='{delta_class}'>{delta:+.1f}%</td>"
                f"</tr>"
            )

        recommendations = self._generate_recommendations(distribution)
        rec_html = "".join(f"<li>{rec}</li>" for rec in recommendations)

        # Replace placeholders
        html = template.replace(
            "{{TIMESTAMP}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        html = html.replace("{{SCORE}}", f"{score:.1f}")
        html = html.replace("{{TOTAL}}", f"{len(self.all_tests):,}")
        html = html.replace("{{ROWS}}", "\n".join(rows))
        html = html.replace("{{MISSING}}", str(self.get_missing_markers_count()))
        html = html.replace("{{RECOMMENDATIONS}}", rec_html)
        html = html.replace("{{UNIT_PCT}}", f"{distribution['unit']:.1f}")
        html = html.replace("{{INTEGRATION_PCT}}", f"{distribution['integration']:.1f}")
        html = html.replace("{{E2E_PCT}}", f"{distribution['e2e']:.1f}")

        return html

    def _generate_recommendations(self, distribution: Dict[str, float]) -> List[str]:
        """Generate recommendations."""
        recommendations = []

        missing = self.get_missing_markers_count()
        if missing > 0:
            recommendations.append(
                f"Add pyramid markers (unit/integration/e2e) to {missing} uncategorized tests"
            )

        for marker, target in self.TARGETS.items():
            actual = distribution[marker]
            delta = actual - target

            if abs(delta) > 5:
                if delta > 0:
                    recommendations.append(
                        f"Reduce {marker} tests or reclassify them "
                        f"(currently {delta:+.1f}% above target of {target}%)"
                    )
                else:
                    recommendations.append(
                        f"Add more {marker} tests "
                        f"(currently {abs(delta):.1f}% below target of {target}%)"
                    )

        if distribution["unit"] < 60:
            recommendations.append(
                "Unit test coverage is low - aim for 70% of total tests"
            )

        if distribution["e2e"] > 15:
            recommendations.append(
                "E2E tests are over-represented - keep them focused on critical paths"
            )

        if not recommendations:
            recommendations.append("Test pyramid looks excellent! Well done! 🎉")

        return recommendations

    def save_history(self, distribution: Dict[str, float], score: float) -> None:
        """Save historical data."""
        self.history_dir.mkdir(exist_ok=True)

        data = {
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "total_tests": len(self.all_tests),
            "distribution": {
                marker: {
                    "count": len(self.tests_by_marker[marker]),
                    "percentage": pct,
                }
                for marker, pct in distribution.items()
            },
            "missing_markers": self.get_missing_markers_count(),
        }

        # Save with date
        date_file = self.history_dir / f"{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(date_file, "w") as f:
            json.dump(data, f, indent=2)

        # Save as latest
        latest_file = self.history_dir / "latest.json"
        with open(latest_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"History saved to {date_file}", file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Fast test pyramid monitor (parses files directly)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--format",
        choices=["console", "json", "html", "markdown"],
        default="console",
        help="Output format (default: console)",
    )
    parser.add_argument(
        "--save-history",
        action="store_true",
        help="Save historical data",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    monitor = FastTestPyramidMonitor()

    if not monitor.collect_tests():
        sys.exit(1)

    distribution = monitor.calculate_distribution()
    score = monitor.calculate_score(distribution)

    # Generate report
    if args.format == "console":
        report = monitor.generate_console_report(distribution, score)
    elif args.format == "json":
        report = monitor.generate_json_report(distribution, score)
    elif args.format == "html":
        report = monitor.generate_html_report(distribution, score)
    elif args.format == "markdown":
        report = monitor.generate_markdown_report(distribution, score)
    else:
        report = monitor.generate_console_report(distribution, score)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Save history
    if args.save_history:
        monitor.save_history(distribution, score)

    # Exit code based on score
    if score < 5.0:
        sys.exit(1)


if __name__ == "__main__":
    main()
