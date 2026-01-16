from __future__ import annotations

import os
from pathlib import Path


def find_project_root(start_path: str | None = None) -> Path:
    markers = ["pyproject.toml", "src", ".git"]
    current = Path(start_path or os.getcwd()).resolve()
    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent
    return Path.cwd().resolve()


def get_characters_directory_path() -> str:
    base_character_path = "characters"
    if not os.path.isabs(base_character_path):
        project_root = find_project_root()
        return str(project_root / base_character_path)
    return base_character_path
