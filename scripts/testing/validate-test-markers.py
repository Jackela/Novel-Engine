#!/usr/bin/env python3
"""
Test Marker Validation Script
==============================

Validates that test files have proper pyramid markers (unit, integration, e2e).

This script is designed to run as a pre-commit hook to ensure all tests
are properly categorized before committing.

Exit codes:
    0 - All tests have proper markers
    1 - Found tests without pyramid markers
    2 - Script error or invalid usage

Usage:
    python validate-test-markers.py [files...]
    python validate-test-markers.py --all
    python validate-test-markers.py tests/test_example.py tests/test_another.py
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class TestMarkerValidator:
    """Validates test markers in test files."""

    PYRAMID_MARKERS = {"unit", "integration", "e2e"}

    def __init__(self, project_root: Path = None):
        """Initialize validator."""
        self.project_root = project_root or Path.cwd()
        self.violations: Dict[str, List[str]] = {}
        self.total_tests_checked = 0
        self.total_violations = 0

    def validate_file(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a single test file.

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        if not file_path.exists():
            return False, [f"File not found: {file_path}"]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return False, [f"Error reading file: {e}"]

        violations = []
        lines = content.split("\n")

        # Check for module-level pytestmark
        module_markers = set()
        for line in lines:
            # Match: pytestmark = pytest.mark.unit (or [pytest.mark.unit, ...])
            if "pytestmark" in line and "pytest.mark." in line:
                for marker in self.PYRAMID_MARKERS:
                    if f"pytest.mark.{marker}" in line:
                        module_markers.add(marker)
            # Stop looking after class definitions start
            if line.startswith("class "):
                break

        # Track test functions and their markers
        current_class = None
        class_markers = set()
        pending_markers = set()

        for i, line in enumerate(lines, 1):
            # Check for class definition
            class_match = re.match(r"^class (Test\w+)", line)
            if class_match:
                current_class = class_match.group(1)
                class_markers = set()
                pending_markers = set()

                # Look back for class-level markers
                for j in range(max(0, i - 11), i):
                    marker_line = lines[j - 1] if j > 0 else ""
                    for marker in self.PYRAMID_MARKERS:
                        if f"@pytest.mark.{marker}" in marker_line:
                            class_markers.add(marker)
                continue

            # Check for function-level markers
            if line.strip().startswith("@pytest.mark."):
                for marker in self.PYRAMID_MARKERS:
                    if f"@pytest.mark.{marker}" in line:
                        pending_markers.add(marker)

            # Check for test function definition
            test_match = re.match(r"^    def (test_\w+)", line)
            if test_match:
                test_name = test_match.group(1)
                self.total_tests_checked += 1

                # Check if test has pyramid marker (function-level, class-level, or module-level)
                effective_markers = pending_markers | class_markers | module_markers

                if not effective_markers:
                    location = (
                        f"{current_class}::{test_name}" if current_class else test_name
                    )
                    violations.append(
                        f"Line {i}: {location} - Missing pyramid marker "
                        f"(needs @pytest.mark.unit, @pytest.mark.integration, or @pytest.mark.e2e)"
                    )
                    self.total_violations += 1

                # Reset function-level markers
                pending_markers = set()

        return len(violations) == 0, violations

    def validate_files(self, files: List[Path]) -> bool:
        """
        Validate multiple files.

        Returns:
            True if all files valid, False otherwise
        """
        all_valid = True

        for file_path in files:
            is_valid, violations = self.validate_file(file_path)

            if not is_valid:
                all_valid = False
                rel_path = (
                    file_path.relative_to(self.project_root)
                    if file_path.is_relative_to(self.project_root)
                    else file_path
                )
                self.violations[str(rel_path)] = violations

        return all_valid

    def find_all_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            return []

        return list(tests_dir.rglob("test_*.py"))

    def print_report(self, verbose: bool = True) -> None:
        """Print validation report."""
        if not self.violations:
            print("✓ All tests have proper pyramid markers!", file=sys.stderr)
            print(f"  Validated {self.total_tests_checked} tests", file=sys.stderr)
            return

        print("✗ Test marker validation FAILED", file=sys.stderr)
        print(
            f"  Found {self.total_violations} tests without pyramid markers\n",
            file=sys.stderr,
        )

        if verbose:
            for file_path, violations in sorted(self.violations.items()):
                print(f"\n{file_path}:", file=sys.stderr)
                for violation in violations:
                    print(f"  {violation}", file=sys.stderr)

            print("\n" + "=" * 80, file=sys.stderr)
            print("How to fix:", file=sys.stderr)
            print("  Add one of these markers before your test:", file=sys.stderr)
            print(
                "    @pytest.mark.unit       - Fast, isolated unit tests",
                file=sys.stderr,
            )
            print(
                "    @pytest.mark.integration - Tests with external dependencies",
                file=sys.stderr,
            )
            print(
                "    @pytest.mark.e2e        - End-to-end workflow tests",
                file=sys.stderr,
            )
            print(
                "\n  You can also add markers at the class level to apply to all tests.",
                file=sys.stderr,
            )
            print("=" * 80, file=sys.stderr)
        else:
            print(f"  {len(self.violations)} file(s) with violations", file=sys.stderr)
            print("  Run with --verbose for details", file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate test markers in test files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate specific files
  validate-test-markers.py tests/test_example.py

  # Validate all test files
  validate-test-markers.py --all

  # Use in pre-commit (automatic file detection)
  validate-test-markers.py tests/test_modified.py

Bypass in commit message:
  If you need to bypass this check temporarily, include [skip-marker-check]
  in your commit message. Use this sparingly and only with justification.
        """,
    )

    parser.add_argument(
        "files",
        nargs="*",
        help="Test files to validate (default: changed files from pre-commit)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all test files in the project",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed violation information",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress output (only use exit code)",
    )

    args = parser.parse_args()

    validator = TestMarkerValidator()

    # Determine files to validate
    if args.all:
        files = validator.find_all_test_files()
        if not files:
            print("No test files found", file=sys.stderr)
            return 0
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        # No files specified and not --all
        parser.print_help()
        return 2

    # Filter to only test files
    test_files = [f for f in files if f.name.startswith("test_") and f.suffix == ".py"]

    if not test_files:
        # No test files to validate
        return 0

    # Validate
    is_valid = validator.validate_files(test_files)

    # Print report
    if not args.quiet:
        validator.print_report(verbose=args.verbose)

    # Exit code
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
