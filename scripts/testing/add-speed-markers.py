#!/usr/bin/env python3
"""
Automatically add speed markers to test files based on measured execution times.

This script:
1. Runs tests with timing measurements
2. Analyzes test speeds
3. Automatically adds @pytest.mark.fast/medium/slow decorators to test files

Usage:
    python scripts/testing/add-speed-markers.py [--test-path tests/unit/] [--dry-run]
"""

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set


class SpeedMarkerAdder:
    """Automatically adds speed markers to test files."""

    FAST_THRESHOLD = 0.1  # 100ms
    MEDIUM_THRESHOLD = 1.0  # 1s

    def __init__(self, test_path: str = "tests/", dry_run: bool = False):
        self.test_path = test_path
        self.dry_run = dry_run
        self.test_timings: Dict[str, float] = {}
        self.file_test_speeds: Dict[str, Dict[str, Set[str]]] = defaultdict(
            lambda: {"fast": set(), "medium": set(), "slow": set()}
        )

    def measure_test_speeds(self) -> bool:
        """Run tests and capture timing data."""
        print(f"Measuring test speeds in {self.test_path}...")

        cmd = [
            "python",
            "-m",
            "pytest",
            self.test_path,
            "--durations=0",
            "-v",
            "--tb=no",
            "--no-cov",
            "-q",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            output = result.stdout + result.stderr
            self._parse_timing_output(output)
            return len(self.test_timings) > 0
        except Exception as e:
            print(f"ERROR: {e}")
            return False

    def _parse_timing_output(self, output: str) -> None:
        """Parse pytest duration output."""
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

        for test_name, phases in test_phases.items():
            total_time = sum(phases.values())
            self.test_timings[test_name] = total_time

    def categorize_tests_by_file(self) -> None:
        """Group tests by file and speed category."""
        for test_path, duration in self.test_timings.items():
            if "::" not in test_path:
                continue

            file_path, test_name = test_path.split("::", 1)

            if duration < self.FAST_THRESHOLD:
                category = "fast"
            elif duration < self.MEDIUM_THRESHOLD:
                category = "medium"
            else:
                category = "slow"

            self.file_test_speeds[file_path][category].add(test_name)

    def add_markers_to_file(self, file_path: str) -> int:
        """Add speed markers to a single test file."""
        path = Path(file_path)
        if not path.exists():
            print(f"  WARNING: File not found: {file_path}")
            return 0

        content = path.read_text()
        original_content = content
        modifications = 0

        speeds = self.file_test_speeds[file_path]

        for category in ["slow", "medium", "fast"]:
            for test_name in speeds[category]:
                # Extract just the test function name
                if "::" in test_name:
                    test_func = test_name.split("::")[-1]
                else:
                    test_func = test_name

                # Look for test definitions
                patterns = [
                    # Pattern 1: async def test_
                    rf"([ \t]*)(@pytest\.mark\.\w+\s+)*(\s*)async def {re.escape(test_func)}\(",
                    # Pattern 2: def test_
                    rf"([ \t]*)(@pytest\.mark\.\w+\s+)*(\s*)def {re.escape(test_func)}\(",
                ]

                for pattern in patterns:
                    matches = list(re.finditer(pattern, content, re.MULTILINE))
                    for match in matches:
                        # Check if marker already exists
                        before_def = content[: match.start()]
                        last_lines = before_def.split("\n")[-5:]  # Check last 5 lines

                        has_marker = any(
                            f"@pytest.mark.{category}" in line for line in last_lines
                        )

                        if not has_marker:
                            indent = match.group(1)
                            marker = f"{indent}@pytest.mark.{category}\n"

                            # Find the right position to insert (after other markers, before def)
                            insert_pos = match.start()

                            # If there are existing markers, add after them
                            if "@pytest.mark" in before_def:
                                # Find the last marker before this test
                                marker_pattern = rf"^{indent}@pytest\.mark\.\w+.*$"
                                marker_matches = list(
                                    re.finditer(
                                        marker_pattern,
                                        before_def.split("\n")[-10:],
                                        re.MULTILINE,
                                    )
                                )
                                if marker_matches:
                                    # Insert after the last marker
                                    pass

                            content = content[:insert_pos] + marker + content[insert_pos:]
                            modifications += 1
                            break

        if modifications > 0 and content != original_content:
            if self.dry_run:
                print(f"  [DRY RUN] Would modify {file_path}: {modifications} markers")
            else:
                path.write_text(content)
                print(f"  Modified {file_path}: Added {modifications} markers")

        return modifications

    def process_all_files(self) -> int:
        """Process all test files and add markers."""
        print("\nAdding speed markers to test files...")
        print("=" * 80)

        total_modifications = 0

        for file_path in sorted(self.file_test_speeds.keys()):
            mods = self.add_markers_to_file(file_path)
            total_modifications += mods

        return total_modifications

    def generate_summary(self) -> str:
        """Generate summary of categorized tests."""
        total_tests = len(self.test_timings)
        if total_tests == 0:
            return "No tests found."

        fast_count = sum(
            len(speeds["fast"]) for speeds in self.file_test_speeds.values()
        )
        medium_count = sum(
            len(speeds["medium"]) for speeds in self.file_test_speeds.values()
        )
        slow_count = sum(
            len(speeds["slow"]) for speeds in self.file_test_speeds.values()
        )

        summary = [
            "=" * 80,
            "SPEED MARKER SUMMARY",
            "=" * 80,
            f"Total tests analyzed: {total_tests}",
            f"  Fast (< 100ms):        {fast_count} ({fast_count/total_tests*100:.1f}%)",
            f"  Medium (100ms-1s):     {medium_count} ({medium_count/total_tests*100:.1f}%)",
            f"  Slow (> 1s):           {slow_count} ({slow_count/total_tests*100:.1f}%)",
            f"\nFiles to be updated: {len(self.file_test_speeds)}",
            "=" * 80,
        ]

        return "\n".join(summary)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add speed markers to test files based on measurements"
    )
    parser.add_argument(
        "--test-path", default="tests/", help="Path to tests directory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    args = parser.parse_args()

    adder = SpeedMarkerAdder(test_path=args.test_path, dry_run=args.dry_run)

    print("Speed Marker Auto-Addition Tool")
    print("=" * 80)

    if not adder.measure_test_speeds():
        print("Failed to measure test speeds.")
        return 1

    adder.categorize_tests_by_file()

    print(adder.generate_summary())

    total_mods = adder.process_all_files()

    print("\n" + "=" * 80)
    if args.dry_run:
        print(f"DRY RUN: Would add {total_mods} speed markers")
    else:
        print(f"Successfully added {total_mods} speed markers")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
