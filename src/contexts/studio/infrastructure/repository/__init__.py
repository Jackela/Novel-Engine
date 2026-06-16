"""SQLAlchemy implementation of the Studio repository port."""

from src.contexts.studio.infrastructure.repository.auth import AuthRepositoryMixin
from src.contexts.studio.infrastructure.repository.base import RepositoryBase
from src.contexts.studio.infrastructure.repository.document import (
    DocumentRepositoryMixin,
)
from src.contexts.studio.infrastructure.repository.export import ExportRepositoryMixin
from src.contexts.studio.infrastructure.repository.job import JobRepositoryMixin
from src.contexts.studio.infrastructure.repository.project import ProjectRepositoryMixin
from src.contexts.studio.infrastructure.repository.review import ReviewRepositoryMixin
from src.contexts.studio.infrastructure.repository.snapshot import (
    SnapshotRepositoryMixin,
)


class SqlAlchemyStudioRepository(
    AuthRepositoryMixin,
    ProjectRepositoryMixin,
    DocumentRepositoryMixin,
    SnapshotRepositoryMixin,
    ReviewRepositoryMixin,
    ExportRepositoryMixin,
    JobRepositoryMixin,
    RepositoryBase,
):
    """SQLAlchemy-backed implementation of ``StudioRepository``."""


__all__ = ["SqlAlchemyStudioRepository"]
