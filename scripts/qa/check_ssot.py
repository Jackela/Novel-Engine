"""Validate the editable Novel Studio version and product authority."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    if version != "0.3.1":
        failures.append(f"pyproject.toml must define release version 0.3.1, got {version}")

    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    if "version" in package:
        failures.append("frontend/package.json must not define a product version")
    if package.get("name") != "novel-engine-studio":
        failures.append("frontend package must be named novel-engine-studio")

    required = ROOT / "openspec" / "specs" / "novel-studio" / "spec.md"
    if not required.is_file():
        failures.append("canonical OpenSpec capability is missing")

    forbidden = re.compile(r"StoryForge|multi-agent narrative|Markdown files are the manuscript source of truth", re.I)
    for relative in ("README.md", "frontend/src", "src/apps/api"):
        path = ROOT / relative
        files = [path] if path.is_file() else list(path.rglob("*"))
        for file in files:
            if not file.is_file() or file.suffix not in {".md", ".py", ".ts", ".tsx"}:
                continue
            if forbidden.search(file.read_text(encoding="utf-8")):
                failures.append(f"{file.relative_to(ROOT)} contains a retired product identity")

    if failures:
        for failure in failures:
            print(f"[ssot] {failure}", file=sys.stderr)
        return 1
    print(f"[ssot] Novel Studio {version} is aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
