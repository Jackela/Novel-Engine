"""Concrete export writers for the Studio context."""

from __future__ import annotations

from src.contexts.studio.application.ports.export_writer import ExportFormatWriter
from src.contexts.studio.domain.types import ExportFormat
from src.contexts.studio.infrastructure.exporters.docx_exporter import DocxExportWriter
from src.contexts.studio.infrastructure.exporters.epub_exporter import EpubExportWriter

DEFAULT_EXPORT_WRITERS: dict[ExportFormat, ExportFormatWriter] = {
    "docx": DocxExportWriter(),
    "epub": EpubExportWriter(),
}

__all__ = ["DEFAULT_EXPORT_WRITERS", "DocxExportWriter", "EpubExportWriter"]
