#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
#
# How to run:
# 1. Install uv (if not installed): curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly: uv run scripts/qa/check_file_sizes.py
# 3. Or make executable and run: chmod +x scripts/qa/check_file_sizes.py && ./scripts/qa/check_file_sizes.py

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
MAX_CODE_LINES: Final = 300

CODE_SUFFIXES: Final = frozenset(
    {".py", ".pyi", ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
)
TYPESCRIPT_SUFFIXES: Final = frozenset(
    {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
)
SCAN_ROOTS: Final = (
    "src/",
    "tests/",
    "scripts/",
    "frontend/src/",
    "frontend/tests/",
    "frontend/scripts/",
)
SKIP_PARTS: Final = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".omo",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "dist",
        "node_modules",
        "playwright-report",
        "test-results",
    }
)
LEGACY_LIMITS: Final[dict[str, int]] = {}


@dataclass(frozen=True)
class FileSizeViolation:
    path: str
    code_lines: int
    limit: int

    def message(self) -> str:
        return f"{self.path}: {self.code_lines} code lines exceeds limit {self.limit}"


def tracked_and_new_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / raw_path for raw_path in result.stdout.splitlines()]


def in_scope(path: Path) -> bool:
    if not path.is_file() or path.suffix not in CODE_SUFFIXES:
        return False
    relative = path.relative_to(ROOT).as_posix()
    if not relative.startswith(SCAN_ROOTS):
        return False
    return not any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)


def is_code_line(line: str, suffix: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if suffix in {".py", ".pyi"} and stripped.startswith("#"):
        return False
    return not (suffix in TYPESCRIPT_SUFFIXES and stripped.startswith("//"))


def code_line_count(path: Path) -> int:
    lines = path.read_text(encoding="utf-8").splitlines()
    return sum(1 for line in lines if is_code_line(line, path.suffix))


def legacy_limit_violations() -> list[str]:
    violations: list[str] = []
    for relative_path, configured_limit in sorted(LEGACY_LIMITS.items()):
        path = ROOT / relative_path
        if not path.is_file():
            violations.append(f"{relative_path}: legacy baseline file is missing")
            continue

        current_count = code_line_count(path)
        if current_count <= MAX_CODE_LINES:
            violations.append(
                f"{relative_path}: stale legacy baseline; {current_count} code lines "
                f"is at or below default limit {MAX_CODE_LINES}"
            )
            continue
        if configured_limit != current_count:
            violations.append(
                f"{relative_path}: stale legacy baseline; configured limit "
                f"{configured_limit} differs from current count {current_count}"
            )
    return violations


def limit_for(relative_path: str) -> int:
    return LEGACY_LIMITS.get(relative_path, MAX_CODE_LINES)


def write_line(message: str, *, stderr: bool = False) -> None:
    stream = sys.stderr if stderr else sys.stdout
    stream.write(f"{message}\n")


def file_size_violations(files: list[Path]) -> list[FileSizeViolation]:
    violations: list[FileSizeViolation] = []
    for path in files:
        if not in_scope(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        code_lines = code_line_count(path)
        limit = limit_for(relative)
        if code_lines > limit:
            violations.append(
                FileSizeViolation(relative, code_lines=code_lines, limit=limit)
            )
    return violations


def main() -> int:
    invalid_legacy_baselines = legacy_limit_violations()
    if invalid_legacy_baselines:
        write_line("[file-size] invalid legacy baselines:", stderr=True)
        for failure in invalid_legacy_baselines:
            write_line(f"  {failure}", stderr=True)
        return 1

    files = tracked_and_new_files()
    violations = file_size_violations(files)
    if violations:
        write_line("[file-size] files over the allowed code-line budget:", stderr=True)
        for violation in violations:
            write_line(f"  {violation.message()}", stderr=True)
        write_line(
            "[file-size] split the file or, for an intentional legacy baseline change, "
            "update LEGACY_LIMITS with review evidence.",
            stderr=True,
        )
        return 1

    checked_count = sum(1 for path in files if in_scope(path))
    write_line(
        f"[file-size] clean: {checked_count} files checked; "
        f"new-file limit {MAX_CODE_LINES}; legacy baselines {len(LEGACY_LIMITS)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
