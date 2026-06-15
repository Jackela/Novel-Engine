"""Operational CLI for the self-hosted Novel Studio service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from src.contexts.studio.application.services import (
    StudioStore,
    configure_studio_store,
    is_studio_store_configured,
    studio_store,
)
from src.contexts.studio.infrastructure.ai_provider import (
    create_studio_text_generation_provider,
)
from src.contexts.studio.infrastructure.database import backup_database, studio_database
from src.contexts.studio.infrastructure.repository import SqlAlchemyStudioRepository
from src.shared.infrastructure.config.settings import get_settings


def _configure_store() -> None:
    """Wire the application-layer store singleton with infrastructure."""
    if is_studio_store_configured():
        return
    settings = get_settings()
    configure_studio_store(
        StudioStore(
            repository=SqlAlchemyStudioRepository(studio_database),
            data_dir=settings.data_dir,
            ai_provider_factory=create_studio_text_generation_provider,
        )
    )


def _prepare_database() -> None:
    """Back up the current SQLite store and apply all pending migrations."""
    _configure_store()
    path = studio_store.database.path
    if path is not None:
        backup_database(path)
    config = Config(str(get_settings().base_dir / "alembic.ini"))
    command.upgrade(config, "head")


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    _prepare_database()
    settings = get_settings()
    uvicorn.run(
        "src.apps.api.main:app",
        host=args.host or settings.api.host,
        port=args.port or settings.api.port,
        reload=bool(args.reload),
        log_level=settings.logging.level.value.lower(),
    )
    return 0


def _import_workspace(args: argparse.Namespace) -> int:
    _prepare_database()
    principal = studio_store.owner_principal(args.owner)
    project = studio_store.import_legacy_workspace(principal, Path(args.source))
    print(json.dumps(project, ensure_ascii=False, indent=2))
    return 0


def _backup(_args: argparse.Namespace) -> int:
    _configure_store()
    path = studio_store.database.path
    if path is None:
        raise RuntimeError("The configured database is not a file-backed SQLite database.")
    target = backup_database(path)
    print(str(target) if target else "No database exists yet.")
    return 0


def _doctor(_args: argparse.Namespace) -> int:
    _prepare_database()
    with studio_store.database.engine.connect() as connection:
        quick_check = connection.execute(text("PRAGMA quick_check")).scalar_one()
        journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
    payload = {
        "version": get_settings().project_version,
        "database": str(studio_store.database.path),
        "quick_check": quick_check,
        "journal_mode": journal_mode,
        "foreign_keys": bool(foreign_keys),
        "owner_configured": studio_store.owner_exists(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if quick_check == "ok" and foreign_keys else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="novel-engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the Novel Studio service.")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(handler=_serve)

    importer = subparsers.add_parser(
        "import",
        help="Import a legacy file workspace without modifying its source.",
    )
    importer.add_argument("--source", required=True)
    importer.add_argument("--owner")
    importer.set_defaults(handler=_import_workspace)

    backup = subparsers.add_parser("backup", help="Back up the SQLite database.")
    backup.set_defaults(handler=_backup)

    doctor = subparsers.add_parser("doctor", help="Validate the local installation.")
    doctor.set_defaults(handler=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["build_parser", "main"]
