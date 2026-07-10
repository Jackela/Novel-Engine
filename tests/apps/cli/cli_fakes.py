from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import TypedDict

import pytest
from sqlalchemy.sql.elements import TextClause

from src.apps.cli import novel_engine


class ProjectPayload(TypedDict):
    id: str
    title: str


class FakeConnection:
    def __init__(self) -> None:
        self.values: dict[str, str | int] = {
            "PRAGMA quick_check": "ok",
            "PRAGMA journal_mode": "wal",
            "PRAGMA foreign_keys": 1,
        }

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        del exc_type, exc_val, exc_tb

    def execute(self, statement: TextClause) -> FakeResult:
        query = str(statement)
        if query not in self.values:
            raise AssertionError(f"Unexpected doctor query: {query}")
        return FakeResult(self.values[query])


@dataclass(frozen=True, slots=True)
class FakeResult:
    value: str | int

    def scalar_one(self) -> str | int:
        return self.value


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def connect(self) -> FakeConnection:
        return self.connection


class FakeDatabase:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.engine = FakeEngine()
        self.disposed = False

    def dispose(self) -> None:
        self.disposed = True


class FakeStore:
    def __init__(self, *, owner_configured: bool = True) -> None:
        self.owner_configured = owner_configured
        self.owner: str | None = None
        self.imported_source: Path | None = None

    def owner_principal(self, owner: str | None) -> str:
        self.owner = owner
        return owner or "guest"

    def import_legacy_workspace(
        self,
        principal: str,
        source: Path,
    ) -> ProjectPayload:
        self.owner = principal
        self.imported_source = source
        return {"id": "project-1", "title": "Imported"}

    def owner_exists(self) -> bool:
        return self.owner_configured


@dataclass(frozen=True, slots=True)
class FakeRuntime:
    store: FakeStore
    database: FakeDatabase


@dataclass(frozen=True, slots=True)
class FakeApiSettings:
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass(frozen=True, slots=True)
class FakeLogLevel:
    value: str = "INFO"


@dataclass(frozen=True, slots=True)
class FakeLoggingSettings:
    level: FakeLogLevel = field(default_factory=FakeLogLevel)


@dataclass(frozen=True, slots=True)
class FakeSettings:
    project_version: str = "0.test"
    base_dir: Path = Path(".")
    api: FakeApiSettings = field(default_factory=FakeApiSettings)
    logging: FakeLoggingSettings = field(default_factory=FakeLoggingSettings)


def install_runtime(
    monkeypatch: pytest.MonkeyPatch,
    runtime: FakeRuntime,
) -> None:
    @contextmanager
    def fake_configured_runtime() -> Iterator[FakeRuntime]:
        try:
            yield runtime
        finally:
            runtime.database.dispose()

    monkeypatch.setattr(novel_engine, "_configured_runtime", fake_configured_runtime)


def fake_settings() -> FakeSettings:
    return FakeSettings()
