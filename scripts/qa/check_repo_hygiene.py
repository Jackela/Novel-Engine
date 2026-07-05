from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]

SKIP_PATHS: Final = frozenset(
    {
        "docs/api/openapi.current.json",
        "pnpm-lock.yaml",
        "uv.lock",
        "scripts/qa/check_repo_hygiene.py",
        "scripts/qa/check_ssot.py",
        ".github/pull_request_template.md",
    }
)
SKIP_PARTS: Final = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "artifacts",
        "coverage",
        "dist",
        "htmlcov",
        "node_modules",
        "playwright-report",
        "test-results",
    }
)


@dataclass(frozen=True, slots=True)
class ForbiddenPattern:
    name: str
    regex: Pattern[str]


@dataclass(frozen=True, slots=True)
class AllowRule:
    path_regex: Pattern[str]
    line_regex: Pattern[str]


FORBIDDEN_PATTERNS: Final = (
    ForbiddenPattern(
        "internal_api_versioning",
        re.compile(
            r"/api/v(?:1|2)(?:/|$)|/api/versions|"
            r"x-api-version|x-supported-versions",
            re.IGNORECASE,
        ),
    ),
    ForbiddenPattern(
        "removed_product_surface",
        re.compile(
            r"/api/workspaces|StoryForge|Honcho|Chroma|"
            r"RPG Character|Knowledge API|local-first CLI",
            re.IGNORECASE,
        ),
    ),
    ForbiddenPattern(
        "compatibility_residue",
        re.compile(
            r"legacy import path|compatibility export|backward compatibility|"
            r"legacy session|legacy slot",
            re.IGNORECASE,
        ),
    ),
)
ALLOW_RULES: Final = (
    AllowRule(
        re.compile(
            r"^(?:"
            r"src/contexts/ai/infrastructure/providers/"
            r"dashscope_text_generation_provider\.py|"
            r"tests/contexts/ai/infrastructure/test_provider_factory\.py"
            r")$"
        ),
        re.compile(r"/api/v(?:1|2)(?:/|$)"),
    ),
)
API_SURFACE_FORBIDDEN: Final = (
    ForbiddenPattern(
        "api_private_payload_surface",
        re.compile(r"\braw_model_output\b|\bchapter_markdown\b|artifact\.to_dict\("),
    ),
)
API_SURFACE_PATHS: Final = re.compile(
    r"^(?:src/apps/api/|frontend/src/app/types/studio\.ts$)"
)


def tracked_and_untracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        ROOT / raw_path
        for raw_path in result.stdout.splitlines()
        if (ROOT / raw_path).is_file()
    ]


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel in SKIP_PATHS or rel.startswith("openspec/changes/archive/"):
        return True
    return any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)


def is_allowed(rel_path: str, line: str) -> bool:
    return any(
        rule.path_regex.search(rel_path) and rule.line_regex.search(line)
        for rule in ALLOW_RULES
    )


def iter_text_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []


def temporary_project_failures() -> list[str]:
    return [
        f"{path.name}/: temporary top-level *_project directory is not allowed"
        for path in ROOT.iterdir()
        if path.is_dir() and re.fullmatch(r"[A-Za-z0-9_-]+_project", path.name)
    ]


def line_failures(rel_path: str, line_number: int, line: str) -> list[str]:
    if is_allowed(rel_path, line):
        return []

    failures = _pattern_failures(rel_path, line_number, line, FORBIDDEN_PATTERNS)
    if API_SURFACE_PATHS.search(rel_path):
        failures.extend(
            _pattern_failures(rel_path, line_number, line, API_SURFACE_FORBIDDEN)
        )
    return failures


def _pattern_failures(
    rel_path: str,
    line_number: int,
    line: str,
    patterns: tuple[ForbiddenPattern, ...],
) -> list[str]:
    return [
        f"{rel_path}:{line_number}: {pattern.name}: {line.strip()}"
        for pattern in patterns
        if pattern.regex.search(line)
    ]


def file_failures(path: Path) -> list[str]:
    rel_path = path.relative_to(ROOT).as_posix()
    failures: list[str] = []
    for line_number, line in enumerate(iter_text_lines(path), start=1):
        failures.extend(line_failures(rel_path, line_number, line))
    return failures


def failures() -> list[str]:
    found = temporary_project_failures()
    for path in tracked_and_untracked_files():
        if not should_skip(path):
            found.extend(file_failures(path))
    return found


def write_line(message: str, *, stderr: bool = False) -> None:
    stream = sys.stderr if stderr else sys.stdout
    stream.write(f"{message}\n")


def main() -> int:
    found = failures()
    if found:
        write_line("[repo-hygiene] forbidden residues found:", stderr=True)
        for failure in found:
            write_line(f"  {failure}", stderr=True)
        return 1

    write_line("[repo-hygiene] clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
