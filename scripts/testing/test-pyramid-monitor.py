#!/usr/bin/env python3
"""
Test Pyramid Monitor
====================

Automated test pyramid monitoring system that tracks test distribution
and reports against ideal targets.

Features:
- Counts tests by marker (unit/integration/e2e)
- Calculates percentages
- Compares against targets (70/20/10)
- Generates reports in multiple formats
- Tracks trends over time
- Detects tests missing pyramid markers

Usage:
    python test-pyramid-monitor.py                    # Console report
    python test-pyramid-monitor.py --format json      # JSON output
    python test-pyramid-monitor.py --format html      # HTML report
    python test-pyramid-monitor.py --format markdown  # Markdown report
    python test-pyramid-monitor.py --save-history     # Save historical data
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class TestPyramidMonitor:
    """Monitor and analyze test pyramid distribution."""

    # Ideal test distribution targets
    TARGETS = {
        "unit": 70.0,
        "integration": 20.0,
        "e2e": 10.0,
    }

    def __init__(self, project_root: Path = None):
        """Initialize monitor."""
        self.project_root = project_root or Path.cwd()
        self.history_dir = self.project_root / ".pyramid-history"
        self.tests_data: Dict[str, List[str]] = defaultdict(list)
        self.missing_markers: List[str] = []
        self.total_tests = 0

    def collect_tests(self) -> bool:
        """Collect tests using pytest and categorize by marker."""
        print("Collecting tests...", file=sys.stderr)

        try:
            # Run pytest to collect test information
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--collect-only",
                    "-q",
                    "--markers",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode not in [0, 1, 5]:  # 5 = no tests collected
                print(f"Error collecting tests: {result.stderr}", file=sys.stderr)
                return False

            # Parse output to get test counts
            self._parse_pytest_output(result.stdout)

            return True

        except subprocess.TimeoutExpired:
            print("Error: Test collection timed out", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return False

    def _parse_pytest_output(self, output: str) -> None:
        """Parse pytest output to categorize tests."""
        # More efficient single-pass collection using pytest's JSON report plugin
        try:
            import os
            import tempfile

            # Use a temp file for collecting test data
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as tmp:
                tmp_path = tmp.name

            try:
                # Single pytest call with verbose output to get markers
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "--collect-only",
                        "-v",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=self.project_root,
                )

                # Parse the output - count totals first
                self.total_tests = self._extract_test_count(result.stdout)

                # Now count by marker using separate quick calls
                for marker in ["unit", "integration", "e2e"]:
                    marker_result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "pytest",
                            "--collect-only",
                            "-q",
                            "-m",
                            marker,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=90,
                        cwd=self.project_root,
                    )
                    count = self._extract_test_count(marker_result.stdout)
                    if count > 0:
                        self.tests_data[marker] = [f"test_{i}" for i in range(count)]

                # Calculate tests without pyramid markers
                categorized = sum(len(tests) for tests in self.tests_data.values())
                missing_count = self.total_tests - categorized
                if missing_count > 0:
                    self.missing_markers = [
                        f"test_missing_{i}" for i in range(missing_count)
                    ]

            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except subprocess.TimeoutExpired:
            print(f"Warning: Test collection timed out", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Could not parse detailed test info: {e}", file=sys.stderr)

    def _extract_test_count(self, output: str) -> int:
        """Extract test count from pytest output."""
        # Look for pattern like "2771 tests collected"
        for line in output.split("\n"):
            if "test" in line.lower() and "collected" in line.lower():
                try:
                    # Extract number from line
                    words = line.split()
                    for word in words:
                        if word.isdigit():
                            return int(word)
                except ValueError:
                    continue
        return 0

    def calculate_distribution(self) -> Dict[str, float]:
        """Calculate percentage distribution of tests."""
        if self.total_tests == 0:
            return {marker: 0.0 for marker in self.TARGETS}

        distribution = {}
        for marker in self.TARGETS:
            count = len(self.tests_data[marker])
            distribution[marker] = (count / self.total_tests) * 100

        return distribution

    def calculate_score(self, distribution: Dict[str, float]) -> float:
        """
        Calculate pyramid score (0-10).

        Perfect pyramid = 10.0
        Deduct points for deviation from targets
        """
        score = 10.0

        for marker, target in self.TARGETS.items():
            actual = distribution[marker]
            deviation = abs(actual - target)

            # Deduct 0.1 point per 1% deviation
            penalty = deviation * 0.1
            score -= penalty

        # Bonus penalty for missing markers
        if self.missing_markers:
            missing_pct = (len(self.missing_markers) / self.total_tests) * 100
            score -= missing_pct * 0.2  # 0.2 point per 1% missing

        return max(0.0, min(10.0, score))

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
            count = len(self.tests_data[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            # Create progress bar
            bar_length = 50
            filled = int((pct / 100) * bar_length)
            bar = "█" * filled + " " * (bar_length - filled)

            # Format delta with color indicator
            delta_str = f"{delta:+.1f}%" if delta != 0 else " 0.0%"

            lines.append(
                f"  {marker.capitalize():14} {count:5,} ({pct:5.1f}%)  "
                f"[Target: {target:4.0f}%]  {bar[:20]}  {delta_str}"
            )

        lines.append("")
        lines.append(f"TOTAL: {self.total_tests:,} tests")
        lines.append("")

        # Missing markers section
        if self.missing_markers:
            lines.append(
                f"MISSING MARKERS: {len(self.missing_markers)} tests need classification"
            )
            lines.append("")

        # Recommendations
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
            "total_tests": self.total_tests,
            "distribution": {
                marker: {
                    "count": len(self.tests_data[marker]),
                    "percentage": round(pct, 2),
                    "target": self.TARGETS[marker],
                    "delta": round(pct - self.TARGETS[marker], 2),
                }
                for marker, pct in distribution.items()
            },
            "missing_markers": len(self.missing_markers),
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
            count = len(self.tests_data[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            lines.append(
                f"| {marker.capitalize()} | {count:,} | {pct:.1f}% | {target:.0f}% | {delta:+.1f}% |"
            )

        lines.append("")
        lines.append(f"**Total:** {self.total_tests:,} tests")
        lines.append("")

        if self.missing_markers:
            lines.append(
                f"**Missing Markers:** {len(self.missing_markers)} tests need classification"
            )
            lines.append("")

        lines.append("## Recommendations")
        lines.append("")
        recommendations = self._generate_recommendations(distribution)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)

    def generate_html_report(self, distribution: Dict[str, float], score: float) -> str:
        """Generate HTML report."""
        # Read template if it exists, otherwise use inline template
        template_path = (
            self.project_root / "scripts/testing/pyramid-report-template.html"
        )

        if template_path.exists():
            with open(template_path, "r") as f:
                template = f.read()
        else:
            template = self._get_inline_html_template()

        # Prepare data for template
        rows = []
        for marker in ["unit", "integration", "e2e"]:
            count = len(self.tests_data[marker])
            pct = distribution[marker]
            target = self.TARGETS[marker]
            delta = pct - target

            rows.append(
                f"<tr>"
                f"<td>{marker.capitalize()}</td>"
                f"<td>{count:,}</td>"
                f"<td>{pct:.1f}%</td>"
                f"<td>{target:.0f}%</td>"
                f"<td style='color: {'red' if delta < 0 else 'green'};'>{delta:+.1f}%</td>"
                f"</tr>"
            )

        recommendations = self._generate_recommendations(distribution)
        rec_html = "".join(f"<li>{rec}</li>" for rec in recommendations)

        # Replace placeholders
        html = template.replace(
            "{{TIMESTAMP}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        html = html.replace("{{SCORE}}", f"{score:.1f}")
        html = html.replace("{{TOTAL}}", f"{self.total_tests:,}")
        html = html.replace("{{ROWS}}", "\n".join(rows))
        html = html.replace("{{MISSING}}", str(len(self.missing_markers)))
        html = html.replace("{{RECOMMENDATIONS}}", rec_html)
        html = html.replace("{{UNIT_PCT}}", f"{distribution['unit']:.1f}")
        html = html.replace("{{INTEGRATION_PCT}}", f"{distribution['integration']:.1f}")
        html = html.replace("{{E2E_PCT}}", f"{distribution['e2e']:.1f}")

        return html

    def _get_inline_html_template(self) -> str:
        """Get inline HTML template."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Test Pyramid Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .score { font-size: 24px; font-weight: bold; color: #2c3e50; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .recommendations { background: #fff3cd; padding: 15px; border-radius: 5px; }
        .pyramid { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Pyramid Report</h1>
        <p><strong>Date:</strong> {{TIMESTAMP}}</p>
        <p class="score">Score: {{SCORE}}/10.0</p>
    </div>

    <h2>Distribution</h2>
    <table>
        <tr>
            <th>Type</th>
            <th>Count</th>
            <th>Percentage</th>
            <th>Target</th>
            <th>Delta</th>
        </tr>
        {{ROWS}}
    </table>
    <p><strong>Total:</strong> {{TOTAL}} tests</p>
    <p><strong>Missing Markers:</strong> {{MISSING}} tests</p>

    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {{RECOMMENDATIONS}}
        </ul>
    </div>

    <div class="pyramid">
        <h2>Pyramid Visualization</h2>
        <svg width="400" height="300" viewBox="0 0 400 300">
            <!-- E2E (top) -->
            <polygon points="150,50 250,50 200,100" fill="#FF6B6B" opacity="0.7"/>
            <text x="200" y="80" text-anchor="middle" fill="white">E2E ({{E2E_PCT}}%)</text>

            <!-- Integration (middle) -->
            <polygon points="100,100 300,100 250,180 150,180" fill="#4ECDC4" opacity="0.7"/>
            <text x="200" y="145" text-anchor="middle" fill="white">Integration ({{INTEGRATION_PCT}}%)</text>

            <!-- Unit (bottom) -->
            <polygon points="50,180 350,180 300,250 100,250" fill="#95E1D3" opacity="0.7"/>
            <text x="200" y="220" text-anchor="middle" fill="white">Unit ({{UNIT_PCT}}%)</text>
        </svg>
    </div>
</body>
</html>"""

    def _generate_recommendations(self, distribution: Dict[str, float]) -> List[str]:
        """Generate recommendations based on distribution."""
        recommendations = []

        # Check for missing markers
        if self.missing_markers:
            recommendations.append(
                f"Classify {len(self.missing_markers)} tests without pyramid markers "
                f"(unit/integration/e2e)"
            )

        # Check each category
        for marker, target in self.TARGETS.items():
            actual = distribution[marker]
            delta = actual - target

            if abs(delta) > 5:  # More than 5% off target
                if delta > 0:
                    # Over-represented
                    recommendations.append(
                        f"Consider moving {marker} tests to other categories "
                        f"(currently {delta:+.1f}% above target)"
                    )
                else:
                    # Under-represented
                    recommendations.append(
                        f"Add more {marker} tests "
                        f"(currently {abs(delta):.1f}% below target)"
                    )

        # Specific recommendations
        if distribution["unit"] < 60:
            recommendations.append(
                "Unit test coverage is low. Consider splitting integration tests into units."
            )

        if distribution["e2e"] > 15:
            recommendations.append(
                "Too many E2E tests. E2E tests should be selective and focus on critical paths."
            )

        if not recommendations:
            recommendations.append(
                "Test pyramid looks good! Keep up the excellent work."
            )

        return recommendations

    def save_history(self, distribution: Dict[str, float], score: float) -> None:
        """Save historical data."""
        self.history_dir.mkdir(exist_ok=True)

        data = {
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "total_tests": self.total_tests,
            "distribution": {
                marker: {
                    "count": len(self.tests_data[marker]),
                    "percentage": pct,
                }
                for marker, pct in distribution.items()
            },
            "missing_markers": len(self.missing_markers),
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
        description="Monitor test pyramid distribution",
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
        help="Save historical data to .pyramid-history/",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    # Create monitor
    monitor = TestPyramidMonitor()

    # Collect tests
    if not monitor.collect_tests():
        sys.exit(1)

    # Calculate distribution and score
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

    # Output report
    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(report)

    # Save history if requested
    if args.save_history:
        monitor.save_history(distribution, score)

    # Exit with non-zero if score is low
    if score < 5.0:
        sys.exit(1)


if __name__ == "__main__":
    main()
