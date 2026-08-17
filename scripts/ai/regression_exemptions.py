"""Registry of planned safety-keyword removal exemptions.

Each entry is ``<repo path> :: <keyword> :: <reason>`` on one line of the
version-controlled registry, so every exemption is visible in the same diff
as the safety-keyword deletion it permits. Malformed input fails loudly so a
broken registry can never silently weaken the guardrail.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

EXEMPTION_SEPARATOR: Final = " :: "
EXEMPTION_FIELD_COUNT: Final = 3


def load_exemption_entries(
    registry_path: Path,
    *,
    allowed_keywords: Sequence[str],
    protected_paths: Sequence[str],
) -> frozenset[tuple[str, str]]:
    if not registry_path.is_file():
        return frozenset()
    entries: set[tuple[str, str]] = set()
    for line_number, raw_line in enumerate(
        registry_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(EXEMPTION_SEPARATOR)]
        prefix = f"{registry_path} line {line_number}: "
        if len(parts) != EXEMPTION_FIELD_COUNT or not all(parts):
            raise ValueError(prefix + "expected '<path> :: <keyword> :: <reason>'")
        path, keyword, _reason = parts
        if path in protected_paths:
            raise ValueError(prefix + f"'{path}' cannot be exempted")
        if keyword not in allowed_keywords:
            raise ValueError(prefix + f"unknown safety keyword '{keyword}'")
        entries.add((path, keyword))
    return frozenset(entries)
