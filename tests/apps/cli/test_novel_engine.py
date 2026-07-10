from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
from alembic.config import Config

from src.apps.cli import novel_engine
from tests.apps.cli.cli_fakes import (
    FakeDatabase,
    FakeRuntime,
    FakeSettings,
    FakeStore,
    fake_settings,
    install_runtime,
)


def test_configured_runtime_disposes_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeRuntime(
        store=FakeStore(),
        database=FakeDatabase(path=Path("studio.sqlite3")),
    )

    def fake_create_runtime() -> FakeRuntime:
        return runtime

    monkeypatch.setattr(novel_engine, "_create_runtime", fake_create_runtime)

    with novel_engine._configured_runtime():
        assert runtime.database.disposed is False

    assert runtime.database.disposed is True


def test_prepare_database_backs_up_then_applies_migrations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "studio.sqlite3"
    database = novel_engine.StudioDatabase(f"sqlite:///{database_path}")
    events: list[str] = []

    def fake_backup(path: Path) -> None:
        assert path == database_path
        events.append("backup")

    def fake_upgrade(config: Config, revision: str) -> None:
        assert config.config_file_name == str(tmp_path / "alembic.ini")
        assert revision == "head"
        events.append("upgrade")

    def tmp_settings() -> FakeSettings:
        return FakeSettings(base_dir=tmp_path)

    monkeypatch.setattr(novel_engine, "backup_database", fake_backup)
    monkeypatch.setattr(novel_engine.command, "upgrade", fake_upgrade)
    monkeypatch.setattr(novel_engine, "get_settings", tmp_settings)

    try:
        novel_engine._prepare_database(database)
    finally:
        database.dispose()

    assert events == ["backup", "upgrade"]


def test_help_does_not_require_production_secrets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "production")
    monkeypatch.delenv("SECURITY_SECRET_KEY", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        novel_engine.main(["--help"])

    assert exc_info.value.code == 0
    assert "novel-engine" in capsys.readouterr().out


def test_backup_requires_file_backed_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeRuntime(store=FakeStore(), database=FakeDatabase(path=None))
    install_runtime(monkeypatch, runtime)

    with pytest.raises(novel_engine.FileBackedDatabaseRequiredError):
        novel_engine.main(["backup"])

    assert runtime.database.disposed is True


def test_backup_prints_created_backup_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "studio.sqlite3"
    backup_path = tmp_path / "backups" / "studio.sqlite3.bak"
    runtime = FakeRuntime(store=FakeStore(), database=FakeDatabase(path=database_path))
    install_runtime(monkeypatch, runtime)

    def fake_backup(path: Path) -> Path:
        assert path == database_path
        return backup_path

    monkeypatch.setattr(novel_engine, "backup_database", fake_backup)

    assert novel_engine.main(["backup"]) == 0
    assert capsys.readouterr().out.strip() == str(backup_path)
    assert runtime.database.disposed is True


def test_doctor_reports_database_health(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(
        store=FakeStore(owner_configured=True),
        database=FakeDatabase(path=tmp_path / "studio.sqlite3"),
    )
    install_runtime(monkeypatch, runtime)
    prepared: list[FakeDatabase] = []

    def fake_prepare_database(database: FakeDatabase) -> None:
        prepared.append(database)

    monkeypatch.setattr(novel_engine, "_prepare_database", fake_prepare_database)
    monkeypatch.setattr(novel_engine, "get_settings", fake_settings)

    assert novel_engine.main(["doctor"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, dict)
    assert payload == {
        "version": "0.test",
        "database": str(runtime.database.path),
        "quick_check": "ok",
        "journal_mode": "wal",
        "foreign_keys": True,
        "owner_configured": True,
    }
    assert prepared == [runtime.database]
    assert runtime.database.disposed is True


def test_import_workspace_uses_owner_and_source(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    store = FakeStore()
    runtime = FakeRuntime(
        store=store,
        database=FakeDatabase(path=tmp_path / "studio.sqlite3"),
    )
    install_runtime(monkeypatch, runtime)

    def fake_prepare_database(database: FakeDatabase) -> None:
        assert database is runtime.database

    monkeypatch.setattr(novel_engine, "_prepare_database", fake_prepare_database)

    source = tmp_path / "legacy-workspace"
    assert novel_engine.main(["import", "--source", str(source), "--owner", "ada"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, dict)
    assert payload["id"] == "project-1"
    assert store.owner == "ada"
    assert store.imported_source == source
    assert runtime.database.disposed is True


def test_serve_prepares_database_before_starting_uvicorn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime = FakeRuntime(
        store=FakeStore(),
        database=FakeDatabase(path=tmp_path / "studio.sqlite3"),
    )
    install_runtime(monkeypatch, runtime)
    events: list[str] = []

    def fake_prepare_database(database: FakeDatabase) -> None:
        assert database is runtime.database
        events.append("prepared")

    def fake_run(app: str, **kwargs: str | int | bool) -> None:
        events.append("served")
        assert app == "src.apps.api.main:create_application"
        assert kwargs == {
            "host": "127.0.0.2",
            "port": 9000,
            "reload": True,
            "log_level": "info",
            "factory": True,
        }

    uvicorn_module = ModuleType("uvicorn")
    uvicorn_module.__dict__["run"] = fake_run
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn_module)
    monkeypatch.setattr(novel_engine, "_prepare_database", fake_prepare_database)
    monkeypatch.setattr(novel_engine, "get_settings", fake_settings)

    assert (
        novel_engine.main(
            ["serve", "--host", "127.0.0.2", "--port", "9000", "--reload"]
        )
        == 0
    )
    assert events == ["prepared", "served"]
    assert runtime.database.disposed is True
