#!/usr/bin/env python3
"""
Test Speed Analysis and Reporting Tool

This script analyzes pytest test execution times and generates a comprehensive
speed distribution report. It categorizes tests into:
- Fast: < 100ms
- Medium: 100ms - 1000ms (1s)
- Slow: > 1000ms (1s)

Usage:
    python scripts/testing/test-speed-report.py [test_path]

Example:
    python scripts/testing/test-speed-report.py tests/unit/
    python scripts/testing/test-speed-report.py tests/integration/
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


class TestSpeedAnalyzer:
    """Analyzes test execution speeds and generates reports."""

    # Speed thresholds in seconds
    FAST_THRESHOLD = 0.1  # 100ms
    MEDIUM_THRESHOLD = 1.0  # 1000ms (1s)

    def __init__(self, test_path: str = "tests/"):
        self.test_path = test_path
        self.test_timings: Dict[str, float] = {}
        self.categorized_tests: Dict[str, List[Tuple[str, float]]] = {
            "fast": [],
            "medium": [],
            "slow": [],
        }

    def run_tests_with_timing(self) -> bool:
        """Run pytest with timing output and capture results."""
        print(f"Running tests in {self.test_path}...")
        print("This may take several minutes...\n")

        cmd = [
            "python",
            "-m",
            "pytest",
            self.test_path,
            "-m", "unit",  # Only analyze unit tests for speed (fast subset)
            "--durations=0",  # Show all test durations
            "-v",
            "--tb=no",  # No traceback on failures
            "--no-cov",  # Disable coverage for faster execution
            "-q",
        ]

        # Set PYTHONPATH for CI environments
        env = os.environ.copy()
        cwd = os.getcwd()
        pythonpath = f"{cwd}:{cwd}/src"
        if "PYTHONPATH" in env:
            pythonpath = f"{pythonpath}:{env['PYTHONPATH']}"
        env["PYTHONPATH"] = pythonpath
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "0"

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300, env=env  # 5 min timeout
            )

            # Parse timing output from both stdout and stderr
            output = result.stdout + result.stderr
            self._parse_timing_output(output)

            return len(self.test_timings) > 0

        except subprocess.TimeoutExpired:
            print("ERROR: Test execution timed out after 10 minutes")
            return False
        except Exception as e:
            print(f"ERROR: Failed to run tests: {e}")
            return False

    def _parse_timing_output(self, output: str) -> None:
        """Parse pytest duration output to extract test timings."""
        # Pattern: "0.12s call     tests/unit/module/test_file.py::test_name"
        duration_pattern = re.compile(
            r"(\d+\.\d+)s\s+(call|setup|teardown)\s+(tests/[^\s]+)"
        )

        test_phases: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"call": 0.0, "setup": 0.0, "teardown": 0.0}
        )

        for match in duration_pattern.finditer(output):
            duration_str, phase, test_name = match.groups()
            duration = float(duration_str)
            test_phases[test_name][phase] = duration

        # Sum up all phases for each test
        for test_name, phases in test_phases.items():
            total_time = sum(phases.values())
            self.test_timings[test_name] = total_time

    def categorize_tests(self) -> None:
        """Categorize tests by speed."""
        for test_name, duration in self.test_timings.items():
            if duration < self.FAST_THRESHOLD:
                self.categorized_tests["fast"].append((test_name, duration))
            elif duration < self.MEDIUM_THRESHOLD:
                self.categorized_tests["medium"].append((test_name, duration))
            else:
                self.categorized_tests["slow"].append((test_name, duration))

        # Sort each category by duration (slowest first)
        for category in self.categorized_tests:
            self.categorized_tests[category].sort(key=lambda x: x[1], reverse=True)

    def generate_report(self) -> str:
        """Generate a comprehensive speed distribution report."""
        total_tests = len(self.test_timings)
        if total_tests == 0:
            return "No test timing data available."

        fast_count = len(self.categorized_tests["fast"])
        medium_count = len(self.categorized_tests["medium"])
        slow_count = len(self.categorized_tests["slow"])

        fast_pct = (fast_count / total_tests) * 100
        medium_pct = (medium_count / total_tests) * 100
        slow_pct = (slow_count / total_tests) * 100

        report = [
            "=" * 80,
            "TEST SPEED DISTRIBUTION REPORT",
            "=" * 80,
            f"\nTest Path: {self.test_path}",
            f"Total Tests Analyzed: {total_tests}",
            f"\nSpeed Thresholds:",
            f"  - Fast:   < {self.FAST_THRESHOLD * 1000:.0f}ms",
            f"  - Medium: {self.FAST_THRESHOLD * 1000:.0f}ms - {self.MEDIUM_THRESHOLD * 1000:.0f}ms",
            f"  - Slow:   > {self.MEDIUM_THRESHOLD * 1000:.0f}ms",
            f"\n{'Category':<10} {'Count':<10} {'Percentage':<12} {'Visual'}",
            "-" * 80,
            f"{'Fast':<10} {fast_count:<10} {fast_pct:>5.1f}%       {'█' * int(fast_pct / 2)}",
            f"{'Medium':<10} {medium_count:<10} {medium_pct:>5.1f}%       {'█' * int(medium_pct / 2)}",
            f"{'Slow':<10} {slow_count:<10} {slow_pct:>5.1f}%       {'█' * int(slow_pct / 2)}",
            "-" * 80,
        ]

        # Add top slowest tests in each category
        report.append("\nTop 10 Slowest Tests by Category:")
        report.append("=" * 80)

        for category in ["slow", "medium", "fast"]:
            tests = self.categorized_tests[category][:10]
            if tests:
                report.append(f"\n{category.upper()} Tests (showing up to 10):")
                for test_name, duration in tests:
                    report.append(f"  {duration:>6.3f}s  {test_name}")

        # Calculate average durations
        avg_fast = sum(d for _, d in self.categorized_tests["fast"]) / max(
            fast_count, 1
        )
        avg_medium = sum(d for _, d in self.categorized_tests["medium"]) / max(
            medium_count, 1
        )
        avg_slow = sum(d for _, d in self.categorized_tests["slow"]) / max(
            slow_count, 1
        )

        report.append("\n" + "=" * 80)
        report.append("STATISTICS:")
        report.append(f"  Average Fast Test Duration:   {avg_fast * 1000:>6.1f}ms")
        report.append(f"  Average Medium Test Duration: {avg_medium * 1000:>6.1f}ms")
        report.append(f"  Average Slow Test Duration:   {avg_slow:>6.3f}s")
        report.append("=" * 80)

        return "\n".join(report)

    def save_json_report(self, output_file: str = "test-speed-report.json") -> None:
        """Save detailed report as JSON for programmatic use."""
        data = {
            "test_path": self.test_path,
            "total_tests": len(self.test_timings),
            "thresholds": {
                "fast_ms": self.FAST_THRESHOLD * 1000,
                "medium_ms": self.MEDIUM_THRESHOLD * 1000,
            },
            "distribution": {
                "fast": {
                    "count": len(self.categorized_tests["fast"]),
                    "percentage": (
                        len(self.categorized_tests["fast"]) / len(self.test_timings)
                    )
                    * 100,
                    "tests": [
                        {"name": name, "duration_s": duration}
                        for name, duration in self.categorized_tests["fast"]
                    ],
                },
                "medium": {
                    "count": len(self.categorized_tests["medium"]),
                    "percentage": (
                        len(self.categorized_tests["medium"]) / len(self.test_timings)
                    )
                    * 100,
                    "tests": [
                        {"name": name, "duration_s": duration}
                        for name, duration in self.categorized_tests["medium"]
                    ],
                },
                "slow": {
                    "count": len(self.categorized_tests["slow"]),
                    "percentage": (
                        len(self.categorized_tests["slow"]) / len(self.test_timings)
                    )
                    * 100,
                    "tests": [
                        {"name": name, "duration_s": duration}
                        for name, duration in self.categorized_tests["slow"]
                    ],
                },
            },
        }

        output_path = Path(output_file)
        output_path.write_text(json.dumps(data, indent=2))
        print(f"\nDetailed JSON report saved to: {output_path.absolute()}")

    def get_test_files_by_category(self) -> Dict[str, set]:
        """Get unique test files grouped by speed category."""
        files_by_category = {"fast": set(), "medium": set(), "slow": set()}

        for category, tests in self.categorized_tests.items():
            for test_name, _ in tests:
                # Extract file path (everything before ::)
                if "::" in test_name:
                    file_path = test_name.split("::")[0]
                    files_by_category[category].add(file_path)

        return files_by_category


def main():
    """Main entry point."""
    test_path = sys.argv[1] if len(sys.argv) > 1 else "tests/"

    analyzer = TestSpeedAnalyzer(test_path)

    print("Test Speed Analysis Tool")
    print("=" * 80)

    if not analyzer.run_tests_with_timing():
        print("Failed to collect test timing data.")
        sys.exit(1)

    analyzer.categorize_tests()

    # Print report
    print(analyzer.generate_report())

    # Save JSON report
    analyzer.save_json_report("test-speed-report.json")

    # Show files that need markers
    print("\n" + "=" * 80)
    print("FILES NEEDING SPEED MARKERS:")
    print("=" * 80)

    files_by_category = analyzer.get_test_files_by_category()

    for category in ["fast", "medium", "slow"]:
        files = files_by_category[category]
        if files:
            print(f"\n{category.upper()} Files ({len(files)}):")
            for file_path in sorted(files):
                print(f"  - {file_path}")


if __name__ == "__main__":
    main()
