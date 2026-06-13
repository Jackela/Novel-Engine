"""SQLite database lifecycle for Novel Studio."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.contexts.studio.infrastructure.models import Base, Job, JobEvent
from src.shared.infrastructure.config.settings import get_settings


def _database_path_from_url(url: str) -> Path | None:
    prefix = "sqlite:///"
    if not url.startswith(prefix) or url.endswith(":memory:"):
        return None
    return Path(url.removeprefix(prefix)).expanduser().resolve()


def backup_database(path: Path) -> Path | None:
    """Create a consistent online backup for a non-empty SQLite database."""
    if not path.exists() or path.stat().st_size == 0:
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    target = backup_dir / f"{path.stem}-{timestamp}{path.suffix}.bak"
    with sqlite3.connect(path) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
    return target


class StudioDatabase:
    """Own the SQLite engine and transactional sessions."""

    def __init__(self, url: str | None = None) -> None:
        settings = get_settings()
        self.url = url or settings.database.url
        path = _database_path_from_url(self.url)
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.engine = create_engine(
            self.url,
            connect_args={"check_same_thread": False}
            if self.url.startswith("sqlite")
            else {},
            future=True,
        )
        self._session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
            future=True,
        )
        self._configure_sqlite(self.engine)

    @staticmethod
    def _configure_sqlite(engine: Engine) -> None:
        if not str(engine.url).startswith("sqlite"):
            return

        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    def initialize(
        self,
        *,
        create_backup: bool = True,
        create_schema: bool = True,
    ) -> None:
        if create_backup and self.path is not None:
            backup_database(self.path)
        if create_schema:
            Base.metadata.create_all(self.engine)
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE VIRTUAL TABLE IF NOT EXISTS document_search USING fts5("
                        "document_id UNINDEXED, project_id UNINDEXED, title, content)"
                    )
                )
        self.recover_jobs()

    def recover_jobs(self) -> int:
        """Mark lease-less running work interrupted after a process restart."""
        with self.session() as session:
            jobs = session.query(Job).filter(Job.status == "running").all()
            now = datetime.now(UTC)
            for job in jobs:
                job.status = "interrupted"
                job.error = "Job lost its execution lease during process restart."
                job.updated_at = now
                job.finished_at = now
                session.add(
                    JobEvent(
                        id=str(uuid4()),
                        job_id=job.id,
                        status="interrupted",
                        details_json=(
                            '{"reason":"execution_lease_lost_during_restart"}'
                        ),
                        created_at=now,
                    )
                )
            return len(jobs)

    def dispose(self) -> None:
        """Release pooled database connections during application shutdown."""
        self.engine.dispose()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


studio_database = StudioDatabase()


def initialize_studio_database() -> None:
    studio_database.initialize()
