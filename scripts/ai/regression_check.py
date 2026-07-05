#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

from scripts.ai.regression_diff import DiffDetails, parse_diff

DEFAULT_MAX_FILES: Final = 5
GUARDRAIL_FILE: Final = "scripts/ai/regression_check.py"
SAFETY_KEYWORDS: Final = (
    "raise",
    "validate",
    "sanitize",
    "escape",
    "auth",
    "permission",
)
FORBIDDEN_PREFIXES: Final = (
    "alembic/versions/",
    ".env",
    "config/env/",
    "data/",
)


@dataclass(frozen=True, slots=True)
class DangerPattern:
    regex: Pattern[str]
    description: str


DANGEROUS_PATTERNS: Final = (
    DangerPattern(
        re.compile(r"^\+.*except\s+(?:Exception|BaseException)\b"), "broad except"
    ),
    DangerPattern(re.compile(r"^\+\s*except\s*:"), "bare except"),
    DangerPattern(
        re.compile(r"^\+.*(?:f['\"].*\b(?:SELECT|INSERT|UPDATE|DELETE|MATCH)\b)"),
        "SQL/FTS5 f-string",
    ),
    DangerPattern(
        re.compile(r"^\+.*\b(?:SELECT|INSERT|UPDATE|DELETE|MATCH)\b.*\+"),
        "SQL/FTS5 string concatenation",
    ),
    DangerPattern(re.compile(r"^\+.*sk-[a-zA-Z0-9]{20,}"), "possible OpenAI key"),
    DangerPattern(
        re.compile(
            r"^\+.*\b(?:password|api_key|secret_key|token)\s*=\s*['\"][^'\"]+['\"]",
            re.IGNORECASE,
        ),
        "hardcoded secret-like value",
    ),
    DangerPattern(re.compile(r"^\+.*#\s*type:\s*ignore"), "type ignore suppression"),
    DangerPattern(re.compile(r"^\+.*#\s*pyright:\s*ignore"), "pyright suppression"),
    DangerPattern(
        re.compile(r"^\+.*#\s*(?:noqa|nosec)\b"), "lint/security suppression"
    ),
    DangerPattern(
        re.compile(r"^\+.*(?:\bas\s+any\b|:\s*any\b|<any>)"), "TypeScript any escape"
    ),
    DangerPattern(
        re.compile(r"^\+.*(?:dangerouslySetInnerHTML|innerHTML\s*=|eval\()"),
        "unsafe DOM/code execution",
    ),
)

GUARDRAIL_WEAKENING_PATTERNS: Final = (
    DangerPattern(
        re.compile(r"^\+\s*return\s+\[\]\s*(?:#.*)?$"),
        "guardrail short-circuit",
    ),
)


def _project_root() -> Path:
    override = os.getenv("REGRESSION_CHECK_PROJECT_ROOT")
    if override is not None:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT: Final = _project_root()


def build_diff_command(base_ref: str | None, head_ref: str | None) -> list[str]:
    if base_ref is None and head_ref is None:
        return ["git", "diff", "--no-color"]
    if base_ref is None or head_ref is None:
        raise ValueError("--base-ref and --head-ref must be provided together")
    return ["git", "diff", "--no-color", f"{base_ref}...{head_ref}"]


def run_git_diff(base_ref: str | None = None, head_ref: str | None = None) -> str:
    result = subprocess.run(
        build_diff_command(base_ref, head_ref),
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout


def check_deleted_safety_lines(diff: DiffDetails) -> list[str]:
    issues: list[str] = []
    moved_line_bodies = _added_line_bodies(diff)
    for filename, lines in diff.deletions.items():
        for line in lines:
            issue = _deleted_safety_issue(filename, line, moved_line_bodies)
            if issue is not None:
                issues.append(issue)
    return issues


def _added_line_bodies(diff: DiffDetails) -> set[str]:
    return {
        _diff_line_body(line)
        for lines in diff.additions.values()
        for line in lines
        if _contains_safety_keyword(line)
    }


def _diff_line_body(line: str) -> str:
    return line[1:].strip() if line[:1] in {"+", "-"} else line.strip()


def _contains_safety_keyword(line: str) -> bool:
    return any(re.search(rf"\b{keyword}\b", line) for keyword in SAFETY_KEYWORDS)


def _deleted_safety_issue(
    filename: str,
    line: str,
    moved_line_bodies: set[str],
) -> str | None:
    if _is_self_definition_line(filename, line):
        return None
    if _diff_line_body(line) in moved_line_bodies:
        return None
    for keyword in SAFETY_KEYWORDS:
        if re.search(rf"\b{keyword}\b", line):
            return f"[{filename}] Deleted safety keyword '{keyword}': {line}"
    return None


def check_deleted_files(diff: DiffDetails) -> list[str]:
    issues: list[str] = []
    for filename in sorted(diff.deleted_files):
        if filename.startswith("tests/"):
            issues.append(f"[{filename}] Deleted test file")
        if filename.startswith(FORBIDDEN_PREFIXES):
            issues.append(f"[{filename}] Deleted forbidden-zone file")
    return issues


def check_dangerous_additions(diff: DiffDetails) -> list[str]:
    issues: list[str] = []
    for filename, lines in diff.additions.items():
        for line in lines:
            issue = _dangerous_addition_issue(filename, line)
            if issue is not None:
                issues.append(issue)
    return issues


def check_guardrail_self_modification(diff: DiffDetails) -> list[str]:
    issues: list[str] = []
    for line in diff.additions.get(GUARDRAIL_FILE, []):
        if _is_self_definition_line(GUARDRAIL_FILE, line):
            continue
        for pattern in GUARDRAIL_WEAKENING_PATTERNS:
            if pattern.regex.search(line):
                issues.append(f"[{GUARDRAIL_FILE}] {pattern.description}: {line}")
                break
    return issues


def _dangerous_addition_issue(filename: str, line: str) -> str | None:
    if _is_self_definition_line(filename, line):
        return None
    for pattern in DANGEROUS_PATTERNS:
        if pattern.regex.search(line):
            return f"[{filename}] {pattern.description}: {line}"
    return None


def _is_self_definition_line(filename: str, line: str) -> bool:
    return filename == GUARDRAIL_FILE and any(
        token in line for token in ("SAFETY_KEYWORDS", "DangerPattern(", "re.compile(")
    )


def check_file_scope(
    diff: DiffDetails, *, max_files: int, skip_file_count: bool
) -> list[str]:
    changed_files = diff.changed_files()
    issues: list[str] = []
    if not skip_file_count and len(changed_files) > max_files:
        issues.append(
            f"AI changed {len(changed_files)} files. Consider splitting into smaller tasks."
        )
    for filename in sorted(changed_files):
        if filename.startswith(FORBIDDEN_PREFIXES):
            issues.append(f"AI modified forbidden zone: {filename}")
    return issues


def find_regressions(
    diff: DiffDetails,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    skip_file_count: bool = False,
) -> list[str]:
    issues: list[str] = []
    issues.extend(check_deleted_safety_lines(diff))
    issues.extend(check_deleted_files(diff))
    issues.extend(check_guardrail_self_modification(diff))
    issues.extend(check_dangerous_additions(diff))
    issues.extend(
        check_file_scope(diff, max_files=max_files, skip_file_count=skip_file_count)
    )
    return issues


def write_line(message: str, *, stderr: bool = False) -> None:
    stream = sys.stderr if stderr else sys.stdout
    stream.write(f"{message}\n")


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check diffs for AI regression risks.")
    parser.add_argument("--base-ref", help="Base git ref for PR diff checks.")
    parser.add_argument("--head-ref", help="Head git ref for PR diff checks.")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--skip-file-count", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    diff_text = run_git_diff(base_ref=args.base_ref, head_ref=args.head_ref)
    if not diff_text.strip():
        write_line("No diff found. Did you forget to make changes?")
        return 0

    issues = find_regressions(
        parse_diff(diff_text),
        max_files=args.max_files,
        skip_file_count=args.skip_file_count,
    )
    if not issues:
        write_line(
            "[PASS] Regression check passed. No obvious AI anti-patterns detected."
        )
        return 0

    write_line("[WARN] Regression check found potential issues:\n", stderr=True)
    for issue in issues:
        write_line(f"  - {issue}", stderr=True)
    write_line(f"\nTotal issues: {len(issues)}", stderr=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
