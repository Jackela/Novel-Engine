"""Application-layer port for concrete export file-format writers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExportChapter:
    """A chapter prepared for export formatting.

    The application layer converts Markdown revisions to plain text before
    handing content to a format-specific writer, keeping presentation concerns
    in the infrastructure layer.
    """

    title: str
    plain_text: str


class ExportFormatWriter(Protocol):
    """Write prepared project chapters to a specific export file format."""

    def write(
        self,
        path: Path,
        title: str,
        chapters: Iterable[ExportChapter],
    ) -> None:
        """Write ``chapters`` to ``path`` using the format-specific backend."""
        ...


__all__ = ["ExportChapter", "ExportFormatWriter"]
