#!/usr/bin/env python3
"""
MyPy Error Fixer Script

This script fixes common MyPy error patterns in the Novel-Engine codebase.
Focuses on:
1. no-untyped-def: Add argument type annotations
2. assignment: Add variable type annotations (partial)
3. attr-defined: Fix some import/forward reference issues
"""

import re
import sys
from pathlib import Path

# Configuration
SRC_DIR = Path("/mnt/d/Code/Novel-Engine/src")
DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv

# Track changes
files_modified = 0
fixes_by_pattern = {}


def count_fix(pattern_name: str) -> None:
    """Track fixes by pattern."""
    fixes_by_pattern[pattern_name] = fixes_by_pattern.get(pattern_name, 0) + 1


def fix_file(filepath: Path) -> bool:
    """
    Fix MyPy errors in a single file.
    Returns True if file was modified.
    """
    global files_modified
    content = filepath.read_text()
    original_content = content

    # Pattern 1: Fix _dict_to_hashable(values) -> _dict_to_hashable(values: Any)
    if "def _dict_to_hashable(values)" in content:
        content = content.replace(
            "def _dict_to_hashable(values)", "def _dict_to_hashable(values: Any)"
        )
        count_fix("_dict_to_hashable")

    # Pattern 2: Fix __eq__(self, other) -> __eq__(self, other: Any)
    # Careful: only fix if it doesn't already have a type
    content = re.sub(
        r"def __eq__\(self, other\)(?!\s*:)",  # Match if not already typed
        "def __eq__(self, other: Any)",
        content,
    )
    if (
        "def __eq__(self, other: Any)" in content
        and "def __eq__(self, other)" in original_content
    ):
        count_fix("__eq__ other: Any")

    # Pattern 3: Fix **kwargs without type in method signatures
    # Pattern: def method(self, **kwargs): -> def method(self, **kwargs: Any):
    content = re.sub(
        r"(\s)def ([a-z_][a-z0-9_]*)\(([^)]*),?\s*\*\*kwargs\)(?!\s*:)",
        r"\1def \2(\3, **kwargs: Any)",
        content,
    )

    # Pattern 4: Fix default=None without type
    # Pattern: default=None -> default: Any = None
    content = re.sub(r"([a-z_][a-z0-9_]*)=None(?=\))", r"\1: Any = None", content)

    # Pattern 5: Fix other=anything without type
    # Pattern: def method(self, other): -> def method(self, other: Any):
    # But skip if it already has type annotation
    content = re.sub(
        r"def ([a-z_][a-z0-9_]*)\(self, other\)(?!\s*:)(?!\s*->)",
        r"def \1(self, other: Any)",
        content,
    )

    # Pattern 6: Fix cls methods without return type
    content = re.sub(
        r"^(\s+)def ([a-z_][a-z0-9_]*)\(cls\)(?!\s*:\s*\n)(?!\s*->)",
        r"\1def \2(cls) -> None:",
        content,
        flags=re.MULTILINE,
    )

    # Write back if changed
    if content != original_content:
        if not DRY_RUN:
            filepath.write_text(content)
        files_modified += 1
        if VERBOSE:
            print(f"  Modified: {filepath}")
        return True
    return False


def process_directory(directory: Path) -> None:
    """Process all Python files in directory recursively."""
    for filepath in directory.rglob("*.py"):
        # Skip certain directories
        if any(part.startswith(".") for part in filepath.parts):
            continue
        if "__pycache__" in str(filepath):
            continue
        if "test" in str(filepath).lower() and "testing" not in str(filepath).lower():
            continue

        try:
            fix_file(filepath)
        except Exception as e:
            print(f"  Error in {filepath}: {e}")


def main():
    print("=" * 60)
    print("MyPy Error Fixer")
    print("=" * 60)
    if DRY_RUN:
        print("DRY RUN MODE - No changes will be made")

    print(f"\nProcessing Python files in {SRC_DIR}...")

    process_directory(SRC_DIR)

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Files modified: {files_modified}")
    print("\n  Fixes by pattern:")
    for pattern, count in sorted(fixes_by_pattern.items(), key=lambda x: -x[1]):
        print(f"    - {pattern}: {count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
