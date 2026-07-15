from __future__ import annotations

from collections.abc import Mapping

from src.contexts.studio.application.ports import ExportFormatWriter
from src.contexts.studio.application.service_common import (
    ExportFormat,
    Path,
    StudioRepository,
    TextGenerationProviderFactory,
)
from src.contexts.studio.application.services.ai_service import AIService
from src.contexts.studio.application.services.auth_service import AuthService
from src.contexts.studio.application.services.document_service import DocumentService
from src.contexts.studio.application.services.export_service import ExportService
from src.contexts.studio.application.services.import_service import ImportService
from src.contexts.studio.application.services.job_service import JobService
from src.contexts.studio.application.services.project_service import ProjectService
from src.contexts.studio.application.services.review_service import ReviewService
from src.contexts.studio.application.services.revision_service import RevisionService
from src.contexts.studio.application.services.snapshot_service import SnapshotService


class StudioServiceRegistry:
    def __init__(
        self,
        repository: StudioRepository,
        *,
        data_dir: Path,
        ai_provider_factory: TextGenerationProviderFactory,
        session_secret: str,
        export_writers: Mapping[ExportFormat, ExportFormatWriter] | None = None,
    ) -> None:
        self.repository = repository
        self.data_dir = data_dir
        self.ai_provider_factory = ai_provider_factory
        self.session_secret = session_secret
        self.export_writers = export_writers
        self._build_services()

    def _build_services(self) -> None:
        repository = self.repository
        self.auth = AuthService(repository, self.session_secret)
        self.project_service = ProjectService(repository)
        self.document_service = DocumentService(repository)
        self.revision_service = RevisionService(repository, self.document_service)
        self.snapshot_service = SnapshotService(repository)
        self.review_service = ReviewService(repository)
        self.export_service = ExportService(
            repository,
            data_dir=self.data_dir,
            writers=self.export_writers,
        )
        self.ai_service = AIService(repository, self.ai_provider_factory)
        self.job_service = JobService(
            repository,
            self.ai_service,
            self.review_service,
            self.export_service,
        )
        self.import_service = ImportService(
            repository,
            self.project_service,
            self.document_service,
        )
