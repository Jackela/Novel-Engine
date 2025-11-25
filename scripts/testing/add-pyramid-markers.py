#!/usr/bin/env python3
"""
Automatically add pyramid markers to test files based on file location and naming.

This script:
1. Scans test files for unmarked tests
2. Determines appropriate marker based on file location and naming patterns
3. Adds @pytest.mark.unit/integration/e2e decorators to test files

Classification Rules:
- tests/unit/* -> @pytest.mark.unit
- tests/integration/* -> @pytest.mark.integration
- tests/e2e/* -> @pytest.mark.e2e
- *_integration*.py -> @pytest.mark.integration
- *_comprehensive*.py -> @pytest.mark.integration
- test_llm_*.py -> @pytest.mark.integration
- test_api_*.py -> @pytest.mark.integration
- tests/api/* -> @pytest.mark.integration
- Default (tests/ root) -> @pytest.mark.unit

Usage:
    python scripts/testing/add-pyramid-markers.py [--dry-run] [--verbose]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class PyramidMarkerAdder:
    """Automatically adds pyramid markers to test files."""

    PYRAMID_MARKERS = {"unit", "integration", "e2e"}

    # File path patterns for integration tests
    INTEGRATION_PATH_PATTERNS = [
        r"tests/integration/",
        r"tests/api/",
    ]

    # Filename patterns for integration tests
    INTEGRATION_NAME_PATTERNS = [
        r"_integration",
        r"_comprehensive",
        r"^test_llm_",
        r"^test_api_",
    ]

    # File path patterns for e2e tests
    E2E_PATH_PATTERNS = [
        r"tests/e2e/",
    ]

    def __init__(
        self, project_root: Path = None, dry_run: bool = False, verbose: bool = False
    ):
        """Initialize marker adder."""
        self.project_root = project_root or Path.cwd()
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            "files_scanned": 0,
            "files_modified": 0,
            "markers_added": 0,
            "tests_already_marked": 0,
        }

    def determine_marker(self, file_path: Path) -> str:
        """Determine the appropriate pyramid marker for a file."""
        path_str = str(file_path).replace("\\", "/")
        filename = file_path.name

        # Check e2e patterns first (most specific)
        for pattern in self.E2E_PATH_PATTERNS:
            if re.search(pattern, path_str):
                return "e2e"

        # Check integration path patterns
        for pattern in self.INTEGRATION_PATH_PATTERNS:
            if re.search(pattern, path_str):
                return "integration"

        # Check integration filename patterns
        for pattern in self.INTEGRATION_NAME_PATTERNS:
            if re.search(pattern, filename):
                return "integration"

        # Check unit path pattern
        if re.search(r"tests/unit/", path_str):
            return "unit"

        # Default to unit for all other tests
        return "unit"

    def has_pyramid_marker(
        self, lines: List[str], line_idx: int, class_markers: Set[str]
    ) -> bool:
        """Check if a test function has a pyramid marker."""
        # Check class-level markers first
        if class_markers & self.PYRAMID_MARKERS:
            return True

        # Look back from the function definition for function-level markers
        for i in range(max(0, line_idx - 10), line_idx):
            line = lines[i]
            for marker in self.PYRAMID_MARKERS:
                if f"@pytest.mark.{marker}" in line:
                    return True
            # Stop looking back if we hit another function/class definition
            if re.match(r"^    def \w+|^class \w+", line):
                break

        return False

    def find_unmarked_tests(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """
        Find all unmarked test functions in a file.

        Returns:
            List of (line_number, test_name, class_name or None)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  ERROR reading {file_path}: {e}")
            return []

        lines = content.split("\n")
        unmarked_tests = []
        current_class = None
        class_markers: Set[str] = set()

        for i, line in enumerate(lines):
            # Check for class definition
            class_match = re.match(r"^class (Test\w+)", line)
            if class_match:
                current_class = class_match.group(1)
                class_markers = set()

                # Look back for class-level markers
                for j in range(max(0, i - 10), i):
                    marker_line = lines[j]
                    for marker in self.PYRAMID_MARKERS:
                        if f"@pytest.mark.{marker}" in marker_line:
                            class_markers.add(marker)
                continue

            # Check for test function definition (indented = in class, not indented = standalone)
            test_match = re.match(r"^(    )?def (test_\w+)", line)
            if test_match:
                indent = test_match.group(1)
                test_name = test_match.group(2)

                # Use class markers if in a class
                effective_class_markers = class_markers if indent else set()

                if not self.has_pyramid_marker(lines, i, effective_class_markers):
                    unmarked_tests.append(
                        (i, test_name, current_class if indent else None)
                    )
                else:
                    self.stats["tests_already_marked"] += 1

        return unmarked_tests

    def add_marker_to_file(self, file_path: Path, marker: str) -> int:
        """
        Add pyramid marker to all unmarked tests in a file.

        Returns:
            Number of markers added
        """
        unmarked_tests = self.find_unmarked_tests(file_path)
        if not unmarked_tests:
            return 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"  ERROR reading {file_path}: {e}")
            return 0

        # Group tests by class
        tests_by_class: Dict[str, List[Tuple[int, str]]] = {}
        for line_idx, test_name, class_name in unmarked_tests:
            key = class_name or "__standalone__"
            if key not in tests_by_class:
                tests_by_class[key] = []
            tests_by_class[key].append((line_idx, test_name))

        markers_added = 0
        lines_to_insert: Dict[int, str] = {}

        for class_name, tests in tests_by_class.items():
            if class_name == "__standalone__":
                # Add marker to each standalone function
                for line_idx, test_name in tests:
                    # Find the actual def line and add marker before it
                    lines_to_insert[line_idx] = f"@pytest.mark.{marker}\n"
                    markers_added += 1
            else:
                # For class methods, we can add at class level if all tests need it
                # But for simplicity, add to each function
                for line_idx, test_name in tests:
                    lines_to_insert[line_idx] = f"    @pytest.mark.{marker}\n"
                    markers_added += 1

        if markers_added == 0:
            return 0

        # Insert markers (in reverse order to preserve line numbers)
        for line_idx in sorted(lines_to_insert.keys(), reverse=True):
            marker_line = lines_to_insert[line_idx]
            lines.insert(line_idx, marker_line)

        if self.dry_run:
            if self.verbose:
                print(
                    f"  [DRY RUN] Would add {markers_added} @pytest.mark.{marker} to {file_path}"
                )
                for line_idx, test_name, class_name in unmarked_tests:
                    loc = f"{class_name}::{test_name}" if class_name else test_name
                    print(f"    - Line {line_idx + 1}: {loc}")
        else:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                if self.verbose:
                    print(
                        f"  Added {markers_added} @pytest.mark.{marker} to {file_path}"
                    )
            except Exception as e:
                print(f"  ERROR writing {file_path}: {e}")
                return 0

        return markers_added

    def find_all_test_files(self) -> List[Path]:
        """Find all test files in the project."""
        tests_dir = self.project_root / "tests"
        if not tests_dir.exists():
            return []

        return list(tests_dir.rglob("test_*.py"))

    def process_all_files(self) -> None:
        """Process all test files and add markers."""
        print("Pyramid Marker Auto-Addition Tool")
        print("=" * 80)

        test_files = self.find_all_test_files()
        self.stats["files_scanned"] = len(test_files)

        print(f"Found {len(test_files)} test files to process\n")

        # Group files by marker type for reporting
        files_by_marker: Dict[str, List[Path]] = {
            "unit": [],
            "integration": [],
            "e2e": [],
        }

        for file_path in sorted(test_files):
            marker = self.determine_marker(file_path)
            markers_added = self.add_marker_to_file(file_path, marker)

            if markers_added > 0:
                self.stats["files_modified"] += 1
                self.stats["markers_added"] += markers_added
                files_by_marker[marker].append(file_path)

        self._print_summary(files_by_marker)

    def _print_summary(self, files_by_marker: Dict[str, List[Path]]) -> None:
        """Print summary of changes."""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Files scanned:       {self.stats['files_scanned']}")
        print(f"Files modified:      {self.stats['files_modified']}")
        print(f"Markers added:       {self.stats['markers_added']}")
        print(f"Already marked:      {self.stats['tests_already_marked']}")
        print()
        print("Markers added by type:")
        for marker, files in files_by_marker.items():
            if files:
                print(f"  @pytest.mark.{marker}: {len(files)} files")

        if self.dry_run:
            print("\n[DRY RUN] No files were modified")
        print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add pyramid markers to test files based on location and naming"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information about changes",
    )

    args = parser.parse_args()

    adder = PyramidMarkerAdder(dry_run=args.dry_run, verbose=args.verbose)
    adder.process_all_files()

    return 0


if __name__ == "__main__":
    sys.exit(main())
