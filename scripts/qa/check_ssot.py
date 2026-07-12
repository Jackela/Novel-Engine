from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
EXPECTED_VERSION: Final = "0.3.1"
TEXT_SUFFIXES: Final = frozenset({".md", ".py", ".ts", ".tsx"})
IDENTITY_SCAN_PATHS: Final = ("README.md", "frontend/src", "src/apps/api")
RETIRED_IDENTITY = re.compile(
    r"StoryForge|multi-agent narrative|Markdown files are the manuscript source of truth",
    re.I,
)


def _project_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(project["project"]["version"])


def _frontend_package() -> dict[str, str]:
    package = json.loads(
        (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    if not isinstance(package, dict):
        raise RuntimeError("frontend/package.json did not decode to an object.")
    return {str(key): str(value) for key, value in package.items()}


def _identity_files(relative: str) -> list[Path]:
    path = ROOT / relative
    if path.is_file():
        return [path]
    return [candidate for candidate in path.rglob("*") if candidate.is_file()]


def _version_failures() -> list[str]:
    version = _project_version()
    if version == EXPECTED_VERSION:
        return []
    return [
        f"pyproject.toml must define release version {EXPECTED_VERSION}, got {version}"
    ]


def _frontend_failures() -> list[str]:
    package = _frontend_package()
    failures: list[str] = []
    if "version" in package:
        failures.append("frontend/package.json must not define a product version")
    if package.get("name") != "novel-engine-studio":
        failures.append("frontend package must be named novel-engine-studio")
    return failures


def _openspec_failures() -> list[str]:
    required = ROOT / "openspec" / "specs" / "novel-studio" / "spec.md"
    if required.is_file():
        return []
    return ["canonical OpenSpec capability is missing"]


def _identity_failures() -> list[str]:
    failures: list[str] = []
    for relative in IDENTITY_SCAN_PATHS:
        for path in _identity_files(relative):
            if path.suffix not in TEXT_SUFFIXES:
                continue
            if RETIRED_IDENTITY.search(path.read_text(encoding="utf-8")):
                failures.append(
                    f"{path.relative_to(ROOT)} contains a retired product identity"
                )
    return failures


def _failures() -> list[str]:
    failures: list[str] = []
    failures.extend(_version_failures())
    failures.extend(_frontend_failures())
    failures.extend(_openspec_failures())
    failures.extend(_identity_failures())
    return failures


def write_line(message: str, *, stderr: bool = False) -> None:
    stream = sys.stderr if stderr else sys.stdout
    stream.write(f"{message}\n")


def main() -> int:
    failures = _failures()
    if failures:
        for failure in failures:
            write_line(f"[ssot] {failure}", stderr=True)
        return 1
    write_line(f"[ssot] Novel Studio {_project_version()} is aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
