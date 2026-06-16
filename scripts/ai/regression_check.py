#!/usr/bin/env python3
"""Regression check after AI modifies code.

Run this after any AI-assisted change to detect common anti-patterns
introduced by AI: deleted safety code, bare except, hardcoded secrets,
SQL/FTS5 string concatenation, etc.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAFETY_KEYWORDS = ["raise", "validate", "sanitize", "escape", "auth", "permission"]
DANGEROUS_PATTERNS = [
    (r"^\+.*except\s+Exception\s*:", "bare except Exception"),
    (r'^\+.*f".*\b(SELECT|INSERT|UPDATE|DELETE|MATCH)\b', "SQL/FTS5 f-string"),
    (r"^\+.*sk-[a-zA-Z0-9]{20,}", "possible OpenAI key"),
    (r"^\+.*password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password"),
    (r"^\+.*SECRET_KEY\s*=\s*['\"][^'\"]+['\"]", "hardcoded secret key"),
]
FORBIDDEN_PREFIXES = {
    "alembic/versions/",
    ".env",
    "config/env/",
    "data/",
}


def run_git_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "--no-color"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def parse_diff(diff: str) -> tuple[dict[str, list[str]], dict[str, list[str]], set[str]]:
    """Parse diff into per-file additions, deletions, and entirely-deleted files."""
    additions: dict[str, list[str]] = {}
    deletions: dict[str, list[str]] = {}
    deleted_files: set[str] = set()

    current_file: str | None = None
    is_deleted = False

    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            # Reset for new file
            current_file = None
            is_deleted = False
            parts = line.split()
            if len(parts) >= 4:
                # parts[3] is b/<filename>; remove prefix to get current file.
                current_file = parts[3].removeprefix("b/")
        elif line == "deleted file mode 100644" or line == "deleted file mode 100755":
            is_deleted = True
            if current_file:
                deleted_files.add(current_file)
                current_file = None
        elif line.startswith("--- a/"):
            # old file path; nothing to do
            pass
        elif line.startswith("+++ /dev/null"):
            # File was deleted entirely.
            is_deleted = True
            if current_file:
                deleted_files.add(current_file)
                current_file = None
        elif line.startswith("+++ b/"):
            # New file path; current_file already known from diff --git line
            pass
        elif current_file and line.startswith("+") and not line.startswith("+++"):
            additions.setdefault(current_file, []).append(line)
        elif current_file and line.startswith("-") and not line.startswith("---"):
            deletions.setdefault(current_file, []).append(line)

    return additions, deletions, deleted_files


def check_deleted_safety_lines(
    deletions: dict[str, list[str]], deleted_files: set[str]
) -> list[str]:
    issues: list[str] = []
    for filename, lines in deletions.items():
        if filename in deleted_files:
            # Dead code removal is expected; do not flag every deleted line.
            continue
        if filename.startswith("tests/"):
            # Test deletions are usually fine.
            continue
        for line in lines:
            for keyword in SAFETY_KEYWORDS:
                if re.search(rf"\b{keyword}\b", line):
                    issues.append(f"[{filename}] Deleted safety keyword '{keyword}': {line}")
                    break
    return issues


def check_dangerous_additions(additions: dict[str, list[str]]) -> list[str]:
    issues: list[str] = []
    for filename, lines in additions.items():
        for line in lines:
            for pattern, description in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"[{filename}] {description}: {line}")
                    break
    return issues


def check_file_count(additions: dict[str, list[str]], deletions: dict[str, list[str]]) -> list[str]:
    changed_files = set(additions) | set(deletions)
    issues: list[str] = []
    if len(changed_files) > 5:
        issues.append(
            f"AI changed {len(changed_files)} files. Consider splitting into smaller tasks."
        )
    for f in changed_files:
        for prefix in FORBIDDEN_PREFIXES:
            if f.startswith(prefix):
                issues.append(f"AI modified forbidden zone: {f}")
    return issues


def main() -> int:
    diff = run_git_diff()
    if not diff.strip():
        print("No diff found. Did you forget to make changes?")
        return 0

    additions, deletions, deleted_files = parse_diff(diff)

    all_issues: list[str] = []
    all_issues.extend(check_deleted_safety_lines(deletions, deleted_files))
    all_issues.extend(check_dangerous_additions(additions))
    all_issues.extend(check_file_count(additions, deletions))

    if not all_issues:
        print("[PASS] Regression check passed. No obvious AI anti-patterns detected.")
        return 0

    print("[WARN] Regression check found potential issues:\n")
    for issue in all_issues:
        print(f"  - {issue}")
    print(f"\nTotal issues: {len(all_issues)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
