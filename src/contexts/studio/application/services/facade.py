from __future__ import annotations

from collections.abc import Mapping

from src.contexts.studio.application.ports import ExportFormatWriter
from src.contexts.studio.application.service_common import (
    Any,
    DocumentDto,
    DocumentKind,
    ExportFormat,
    InvalidOperation,
    JobDto,
    Path,
    Principal,
    ProjectDto,
    ReviewDto,
    RevisionDto,
    SnapshotDto,
    StudioRepository,
    T,
    TextGenerationProviderFactory,
    _document_payload,
    _job_payload,
    _project_payload,
    _review_payload,
    _revision_payload,
    _snapshot_payload,
    cast,
)

from .ai_service import AIService
from .auth_service import AuthService
from .document_service import DocumentService
from .export_service import ExportService
from .import_service import ImportService
from .job_service import JobService
from .project_service import ProjectService
from .review_service import ReviewService
from .revision_service import RevisionService
from .snapshot_service import SnapshotService

__all__ = ["StudioStore", "configure_studio_store", "is_studio_store_configured", "studio_store"]


class StudioStore:
    """Backward-compatible facade over the granular Studio domain services."""

    def __init__(
        self,
        repository: StudioRepository | None = None,
        *,
        data_dir: Path | None = None,
        ai_provider_factory: TextGenerationProviderFactory | None = None,
        export_writers: Mapping[ExportFormat, ExportFormatWriter] | None = None,
    ) -> None:
        self.repository = repository
        self.data_dir = data_dir
        self.ai_provider_factory = ai_provider_factory
        self.export_writers = export_writers
        self._build_services()

    def _build_services(self) -> None:
        repository = self.repository
        data_dir = self.data_dir
        ai_factory = self.ai_provider_factory
        if repository is None:
            self.auth: AuthService | None = None
            self.project_service: ProjectService | None = None
            self.document_service: DocumentService | None = None
            self.revision_service: RevisionService | None = None
            self.snapshot_service: SnapshotService | None = None
            self.review_service: ReviewService | None = None
            self.export_service: ExportService | None = None
            self.ai_service: AIService | None = None
            self.job_service: JobService | None = None
            self.import_service: ImportService | None = None
        else:
            self.auth = AuthService(repository)
            self.project_service = ProjectService(repository)
            self.document_service = DocumentService(repository)
            self.revision_service = RevisionService(repository, self.document_service)
            self.snapshot_service = SnapshotService(repository)
            self.review_service = ReviewService(repository)
            if data_dir is None:
                raise InvalidOperation("data_dir is required when a repository is provided.")
            self.export_service = ExportService(
                repository,
                data_dir=data_dir,
                writers=self.export_writers,
            )
            if ai_factory is None:
                raise InvalidOperation(
                    "ai_provider_factory is required when a repository is provided."
                )
            self.ai_service = AIService(repository, ai_factory)
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

    @property
    def database(self) -> Any:
        """Expose the underlying infrastructure database for diagnostics."""
        if self.repository is None:
            raise RuntimeError("StudioStore has not been configured with a repository.")
        return cast(Any, self.repository).database

    def _service(self, service: T | None) -> T:
        if service is None:
            raise RuntimeError("StudioStore has not been configured with a repository.")
        return service

    # Owner / auth
    def owner_exists(self) -> bool:
        return self._service(self.auth).owner_exists()

    def owner_principal(self, username: str | None = None) -> Principal:
        return self._service(self.auth).owner_principal(username)

    def setup_owner(self, username: str, password: str) -> dict[str, Any]:
        return self._service(self.auth).setup_owner(username, password)

    def create_owner_session(
        self,
        username: str,
        password: str,
    ) -> tuple[str, str, Principal]:
        return self._service(self.auth).create_owner_session(username, password)

    def create_guest_session(self) -> tuple[str, str, Principal]:
        return self._service(self.auth).create_guest_session()

    def csrf_token_for_session(self, token_hash: str) -> str | None:
        return self._service(self.auth).csrf_token_for_session(token_hash)

    def principal_from_token(self, token: str | None) -> Principal | None:
        return self._service(self.auth).principal_from_token(token)

    def logout(self, token: str | None) -> None:
        return self._service(self.auth).logout(token)

    def cleanup_expired_guests(self) -> int:
        return self._service(self.auth).cleanup_expired_guests()

    # Projects
    def create_project(
        self,
        principal: Principal,
        *,
        title: str,
        description: str = "",
        create_seed: bool = True,
    ) -> dict[str, Any]:
        return self._service(self.project_service).create_project(
            principal,
            title=title,
            description=description,
            create_seed=create_seed,
        )

    def list_projects(self, principal: Principal) -> list[dict[str, Any]]:
        return self._service(self.project_service).list_projects(principal)

    def get_project(self, principal: Principal, project_id: str) -> dict[str, Any]:
        return self._service(self.project_service).get_project(principal, project_id)

    def update_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._service(self.project_service).update_project(
            principal,
            project_id,
            title=title,
            description=description,
            settings=settings,
        )

    def delete_project(self, principal: Principal, project_id: str) -> None:
        return self._service(self.project_service).delete_project(principal, project_id)

    # Documents
    def create_document(
        self,
        principal: Principal,
        project_id: str,
        *,
        kind: DocumentKind,
        title: str,
        content_markdown: str = "",
        position: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._service(self.document_service).create_document(
            principal,
            project_id,
            kind=kind,
            title=title,
            content_markdown=content_markdown,
            position=position,
            metadata=metadata,
        )

    def get_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> dict[str, Any]:
        return self._service(self.document_service).get_document(
            principal, project_id, document_id
        )

    def delete_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> None:
        return self._service(self.document_service).delete_document(
            principal, project_id, document_id
        )

    def save_document(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        content_markdown: str,
        base_revision_id: str | None,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "author",
    ) -> dict[str, Any]:
        return self._service(self.document_service).save_document(
            principal,
            project_id,
            document_id,
            content_markdown=content_markdown,
            base_revision_id=base_revision_id,
            title=title,
            metadata=metadata,
            source=source,
        )

    def reorder_documents(
        self,
        principal: Principal,
        project_id: str,
        document_ids: list[str],
    ) -> list[dict[str, Any]]:
        return self._service(self.document_service).reorder_documents(
            principal, project_id, document_ids
        )

    def search(
        self,
        principal: Principal,
        project_id: str,
        query: str,
    ) -> list[dict[str, Any]]:
        return self._service(self.document_service).search(
            principal, project_id, query
        )

    # Revisions
    def list_revisions(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
    ) -> list[dict[str, Any]]:
        return self._service(self.revision_service).list_revisions(
            principal, project_id, document_id
        )

    def restore_revision(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        revision_id: str,
        *,
        base_revision_id: str | None,
    ) -> dict[str, Any]:
        return self._service(self.revision_service).restore_revision(
            principal,
            project_id,
            document_id,
            revision_id,
            base_revision_id=base_revision_id,
        )

    # Snapshots
    def create_snapshot(
        self,
        principal: Principal,
        project_id: str,
        *,
        reason: str,
    ) -> dict[str, Any]:
        return self._service(self.snapshot_service).create_snapshot(
            principal, project_id, reason=reason
        )

    def list_snapshots(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self._service(self.snapshot_service).list_snapshots(
            principal, project_id
        )

    # Reviews
    def review_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        provider: str = "deterministic",
        model: str = "studio-review-v1",
    ) -> dict[str, Any]:
        return self._service(self.review_service).review_project(
            principal, project_id, provider=provider, model=model
        )

    def list_reviews(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self._service(self.review_service).list_reviews(principal, project_id)

    # Exports
    def export_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        export_format: ExportFormat,
    ) -> dict[str, Any]:
        return self._service(self.export_service).export_project(
            principal, project_id, export_format=export_format
        )

    def list_exports(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        return self._service(self.export_service).list_exports(principal, project_id)

    def export_path(
        self,
        principal: Principal,
        project_id: str,
        export_id: str,
    ) -> Path:
        return self._service(self.export_service).export_path(
            principal, project_id, export_id
        )

    # AI proposals
    async def create_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        document_id: str,
        *,
        operation: str,
        instruction: str,
        provider: str = "mock",
        model: str = "studio-copilot-v1",
    ) -> dict[str, Any]:
        return await self._service(self.ai_service).create_ai_proposal(
            principal,
            project_id,
            document_id,
            operation=operation,
            instruction=instruction,
            provider=provider,
            model=model,
        )

    def accept_ai_proposal(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return self._service(self.ai_service).accept_ai_proposal(
            principal, project_id, job_id
        )

    # Jobs
    def list_jobs(self, principal: Principal, project_id: str) -> list[dict[str, Any]]:
        return self._service(self.job_service).list_jobs(principal, project_id)

    async def retry_job(
        self,
        principal: Principal,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return await self._service(self.job_service).retry_job(
            principal, project_id, job_id
        )

    # Import
    def preview_legacy_workspace(self, source: Path) -> dict[str, Any]:
        return self._service(self.import_service).preview_legacy_workspace(source)

    def import_legacy_workspace(
        self,
        principal: Principal,
        source: Path,
    ) -> dict[str, Any]:
        return self._service(self.import_service).import_legacy_workspace(
            principal, source
        )

    # Legacy payload helpers used by tests and diagnostics.
    def _project_payload(
        self,
        project: ProjectDto,
        *,
        include_documents: bool = True,
    ) -> dict[str, Any]:
        return _project_payload(project, include_documents=include_documents)

    def _document_payload(self, document: DocumentDto) -> dict[str, Any]:
        return _document_payload(document)

    def _revision_payload(self, revision: RevisionDto) -> dict[str, Any]:
        return _revision_payload(revision)

    def _snapshot_payload(self, snapshot: SnapshotDto) -> dict[str, Any]:
        return _snapshot_payload(snapshot)

    def _review_payload(self, review: ReviewDto) -> dict[str, Any]:
        return _review_payload(review)

    def _job_payload(self, job: JobDto) -> dict[str, Any]:
        return _job_payload(job)


# ---------------------------------------------------------------------------
# Singleton facade used by routers and CLI. Wired at application startup.
# ---------------------------------------------------------------------------
class _StudioStoreProxy:
    """Mutable proxy that lets routers and CLI import ``studio_store`` early.

    The real ``StudioStore`` instance is injected at application startup so
    that modules importing the singleton do not have to be imported after
    infrastructure wiring.
    """

    def __init__(self) -> None:
        self._instance: StudioStore | None = None

    def configure(
        self,
        instance: StudioStore,
    ) -> None:
        """Attach the configured facade instance."""
        self._instance = instance

    def __getattr__(self, name: str) -> Any:
        if self._instance is None:
            raise RuntimeError("StudioStore has not been configured with a repository.")
        return getattr(self._instance, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_instance":
            super().__setattr__(name, value)
            return
        if self._instance is None:
            raise RuntimeError("StudioStore has not been configured with a repository.")
        setattr(self._instance, name, value)


_studio_store_proxy = _StudioStoreProxy()


def configure_studio_store(instance: StudioStore) -> None:
    """Attach a configured facade to the module-level singleton."""
    _studio_store_proxy.configure(instance)


def is_studio_store_configured() -> bool:
    """Return whether the module-level singleton has been wired."""
    return _studio_store_proxy._instance is not None


# ``studio_store`` is annotated as ``StudioStore`` so that importers get
# precise type checking; at runtime it is the proxy above.
studio_store: StudioStore = cast(StudioStore, _studio_store_proxy)
