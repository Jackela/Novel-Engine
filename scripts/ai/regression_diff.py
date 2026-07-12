from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiffDetails:
    additions: dict[str, list[str]]
    deletions: dict[str, list[str]]
    deleted_files: set[str]

    def changed_files(self) -> set[str]:
        return set(self.additions) | set(self.deletions) | self.deleted_files


def _path_from_diff_header(line: str) -> str | None:
    parts = line.split()
    if len(parts) < 4:
        return None
    return parts[3].removeprefix("b/")


def _is_deleted_marker(line: str) -> bool:
    return line in {
        "deleted file mode 100644",
        "deleted file mode 100755",
    } or line.startswith("+++ /dev/null")


def _is_diff_metadata(line: str) -> bool:
    return line.startswith(("--- a/", "+++ b/"))


def parse_diff(diff: str) -> DiffDetails:
    additions: dict[str, list[str]] = {}
    deletions: dict[str, list[str]] = {}
    deleted_files: set[str] = set()
    current_file: str | None = None

    for line in diff.splitlines():
        if line.startswith("diff --git a/"):
            current_file = _path_from_diff_header(line)
            continue
        if _is_deleted_marker(line):
            if current_file is not None:
                deleted_files.add(current_file)
            continue
        if _is_diff_metadata(line) or current_file is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            additions.setdefault(current_file, []).append(line)
            continue
        if line.startswith("-") and not line.startswith("---"):
            deletions.setdefault(current_file, []).append(line)

    return DiffDetails(
        additions=additions, deletions=deletions, deleted_files=deleted_files
    )
