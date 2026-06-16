"""Concrete EPUB (.epub) export writer."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ebooklib import epub

from src.contexts.studio.application.ports.export_writer import ExportChapter
from src.contexts.studio.domain.utils import new_id


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


class EpubExportWriter:
    """Write prepared chapters as an EPUB e-book."""

    def write(
        self,
        path: Path,
        title: str,
        chapters: Iterable[ExportChapter],
    ) -> None:
        """Write ``chapters`` to ``path`` in EPUB format."""
        book = epub.EpubBook()
        book.set_identifier(new_id())
        book.set_title(title)
        book.set_language("en")
        epub_chapters: list[epub.EpubHtml] = []
        for index, chapter in enumerate(chapters, start=1):
            html_chapter = epub.EpubHtml(
                title=chapter.title,
                file_name=f"chapter-{index:03d}.xhtml",
                lang="en",
            )
            paragraphs = "".join(
                f"<p>{_escape_html(paragraph)}</p>"
                for paragraph in chapter.plain_text.split("\n\n")
                if paragraph.strip()
            )
            html_chapter.content = (
                f"<h1>{_escape_html(chapter.title)}</h1>{paragraphs}"
            )
            book.add_item(html_chapter)
            epub_chapters.append(html_chapter)
        book.toc = tuple(epub_chapters)
        book.spine = ["nav", *epub_chapters]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(path, book)
