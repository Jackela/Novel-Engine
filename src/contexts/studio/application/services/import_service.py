from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    InvalidOperation,
    Iterable,
    Path,
    Principal,
    StudioRepository,
    _owner_scopes,
    _project_payload,
    hashlib,
    yaml,
)

from .document_service import DocumentService
from .project_service import ProjectService

__all__ = ["ImportService"]


class ImportService:
    """Legacy file-based workspace import."""

    def __init__(
        self,
        repository: StudioRepository,
        project_service: ProjectService,
        document_service: DocumentService,
    ) -> None:
        self._repository = repository
        self._project_service = project_service
        self._document_service = document_service

    def preview_legacy_workspace(self, source: Path) -> dict[str, Any]:
        source = source.expanduser().resolve()
        story_path = source / "story.yaml"
        if not story_path.is_file():
            raise InvalidOperation("Legacy workspace must contain story.yaml.")
        story = yaml.safe_load(story_path.read_text(encoding="utf-8")) or {}
        chapter_dir = source / "manuscript" / "chapters"
        chapters = sorted(chapter_dir.glob("chapter-*.md")) if chapter_dir.exists() else []
        source_hash = self._legacy_hash(source, [story_path, *chapters])
        return {
            "source": str(source),
            "source_hash": source_hash,
            "title": str(story.get("title", source.name)),
            "description": str(story.get("premise", "")),
            "chapter_count": len(chapters),
            "chapters": [
                {"filename": chapter.name, "bytes": chapter.stat().st_size}
                for chapter in chapters
            ],
        }

    def import_legacy_workspace(
        self,
        principal: Principal,
        source: Path,
    ) -> dict[str, Any]:
        preview = self.preview_legacy_workspace(source)
        owner_id, guest_session_id = _owner_scopes(principal)
        existing = self._repository.find_project_by_import_hash(
            preview["source_hash"],
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        if existing is not None:
            project = self._repository.get_project(
                existing.id,
                owner_id=owner_id,
                guest_session_id=guest_session_id,
            )
            return _project_payload(project)
        new_project = self._project_service.create_project(
            principal,
            title=str(preview["title"]),
            description=str(preview["description"]),
            create_seed=False,
        )
        source_root = Path(str(preview["source"]))
        for position, chapter_path in enumerate(
            sorted((source_root / "manuscript" / "chapters").glob("chapter-*.md")),
            start=1,
        ):
            self._document_service.create_document(
                principal,
                new_project["id"],
                kind="chapter",
                title=f"Chapter {position}",
                content_markdown=chapter_path.read_text(encoding="utf-8"),
                position=position,
                metadata={"legacy_filename": chapter_path.name},
            )
        self._repository.set_project_import_hash(
            new_project["id"],
            str(preview["source_hash"]),
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        stored = self._repository.get_project(
            new_project["id"],
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return _project_payload(stored)

    @staticmethod
    def _legacy_hash(root: Path, files: Iterable[Path]) -> str:
        digest = hashlib.sha256()
        digest.update(str(root).encode("utf-8"))
        for path in sorted(files):
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------
