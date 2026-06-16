from __future__ import annotations

from typing import TYPE_CHECKING

from src.contexts.studio.infrastructure.repository.common import (
    Export,
    ExportDto,
    NotFound,
    Project,
    Session,
    StudioDatabase,
    _export_dto,
    datetime,
    select,
)

__all__ = ["ExportRepositoryMixin"]


class ExportRepositoryMixin:
    database: StudioDatabase

    if TYPE_CHECKING:

        def _project(
            self,
            session: Session,
            project_id: str,
            owner_id: str | None,
            guest_session_id: str | None,
        ) -> Project: ...

    def create_export(
        self,
        *,
        export_id: str,
        project_id: str,
        snapshot_id: str,
        export_format: str,
        relative_path: str,
        size_bytes: int,
        checksum_sha256: str,
        now: datetime,
    ) -> ExportDto:
        with self.database.session() as session:
            export = Export(
                id=export_id,
                project_id=project_id,
                snapshot_id=snapshot_id,
                format=export_format,
                relative_path=relative_path,
                size_bytes=size_bytes,
                checksum_sha256=checksum_sha256,
                created_at=now,
            )
            session.add(export)
            session.flush()
            return _export_dto(export)

    def list_exports(
        self,
        project_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> list[ExportDto]:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            exports = session.scalars(
                select(Export)
                .where(Export.project_id == project.id)
                .order_by(Export.created_at.desc())
            ).all()
            return [_export_dto(item) for item in exports]

    def get_export(
        self,
        project_id: str,
        export_id: str,
        *,
        owner_id: str | None,
        guest_session_id: str | None,
    ) -> ExportDto:
        with self.database.session() as session:
            project = self._project(session, project_id, owner_id, guest_session_id)
            item = session.scalar(
                select(Export).where(
                    Export.id == export_id,
                    Export.project_id == project.id,
                )
            )
            if item is None:
                raise NotFound("Export not found.")
            return _export_dto(item)
