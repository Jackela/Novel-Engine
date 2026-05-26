"""Fail on stale API-versioning and removed narrative-platform residues."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Pattern

ROOT = Path(__file__).resolve().parents[2]

SKIP_PATHS = {
    "docs/api/openapi.current.json",
    "frontend/package-lock.json",
    "uv.lock",
    "scripts/qa/check_repo_hygiene.py",
}

SKIP_PARTS = {
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


@dataclass(frozen=True)
class ForbiddenPattern:
    name: str
    regex: Pattern[str]


@dataclass(frozen=True)
class AllowRule:
    name: str
    path_regex: Pattern[str]
    line_regex: Pattern[str]


FORBIDDEN_PATTERNS = (
    ForbiddenPattern(
        "internal_api_versioning",
        re.compile(
            r"/api/v(?:1|2)(?:/|$)|/api/versions|"
            r"x-api-version|x-supported-versions",
            re.IGNORECASE,
        ),
    ),
    ForbiddenPattern(
        "v2_narrative_surface",
        re.compile(
            r"\bnarrative_v2\b|\btest_v2_workspaces\b|"
            r"\btest_novel_engine_v2\b|\bv2_workspaces\b|"
            r"\bV2(?:Workspace|Provider|Job|Review|Run|Artifact|Story)\b|"
            r"\bDashScope V2\b|\bV2 Workspace\b|\bNovel Engine V2\b|"
            r"\blocal-first V2\b|\bV2 writing\b|\bV2 engine\b|"
            r"\bv2_chapter_(?:draft|revision)\b|\bv2_editorial_review\b"
        ),
    ),
    ForbiddenPattern(
        "removed_story_pipeline",
        re.compile(
            r"StoryWorkflowService|StoryRevisionService|ChapterDraftingService|"
            r"StoryRunRequest|story_pipeline|terminal arc|vessel_agency|"
            r"keeper_motivation",
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

ALLOW_RULES = (
    AllowRule(
        "external_provider_api_versions",
        re.compile(
            r"^(?:"
            r"\.github/workflows/ci\.yml|"
            r"\.env\.example|"
            r"src/contexts/ai/infrastructure/providers/dashscope_text_generation_provider\.py|"
            r"src/shared/infrastructure/config/settings\.py|"
            r"tests/contexts/ai/infrastructure/test_provider_factory\.py|"
            r"tests/text_generation_contract_support\.py|"
            r"tests/unit/infrastructure/config/test_settings\.py"
            r")$"
        ),
        re.compile(r"/api/v(?:1|2)(?:/|$)"),
    ),
)


API_SURFACE_FORBIDDEN = (
    ForbiddenPattern(
        "api_private_payload_surface",
        re.compile(r"\braw_model_output\b|\bchapter_markdown\b|artifact\.to_dict\("),
    ),
)

API_SURFACE_PATHS = re.compile(
    r"^(?:src/apps/api/|frontend/src/app/types/story\.ts$)"
)

REQUIRED_TEST_MARKERS = (
    (
        "workspace_path_leak_regression",
        Path("tests/apps/api/test_workspaces.py"),
        "_assert_no_private_payload",
    ),
    (
        "raw_output_leak_regression",
        Path("tests/apps/api/test_workspaces.py"),
        "raw_model_output",
    ),
)


def tracked_and_untracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for raw_path in result.stdout.splitlines():
        path = ROOT / raw_path
        if path.is_file():
            files.append(path)
    return files


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel in SKIP_PATHS:
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


def main() -> int:
    failures: list[str] = []
    for path in ROOT.iterdir():
        if path.is_dir() and re.fullmatch(r"[A-Za-z0-9_-]+_project", path.name):
            failures.append(
                f"{path.name}/: temporary top-level *_project directory is not allowed"
            )

    for name, rel_path, marker in REQUIRED_TEST_MARKERS:
        path = ROOT / rel_path
        if not path.exists() or marker not in path.read_text(encoding="utf-8"):
            failures.append(f"{rel_path.as_posix()}: missing required {name} marker")

    for path in tracked_and_untracked_files():
        if should_skip(path):
            continue
        rel_path = path.relative_to(ROOT).as_posix()
        for line_number, line in enumerate(iter_text_lines(path), start=1):
            if is_allowed(rel_path, line):
                continue
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.regex.search(line):
                    failures.append(
                        f"{rel_path}:{line_number}: {pattern.name}: {line.strip()}"
                    )
            if API_SURFACE_PATHS.search(rel_path):
                for pattern in API_SURFACE_FORBIDDEN:
                    if pattern.regex.search(line):
                        failures.append(
                            f"{rel_path}:{line_number}: {pattern.name}: {line.strip()}"
                        )

    if failures:
        print("[repo-hygiene] forbidden residues found:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("[repo-hygiene] clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
