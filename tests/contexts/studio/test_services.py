from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest

from src.contexts.studio.application.services import (
    Principal,
    StudioStore,
)
from src.contexts.studio.domain.exceptions import NotFound, RevisionConflict
from src.contexts.studio.domain.types import ExportFormat
from src.contexts.studio.domain.utils import load_json, utcnow
from src.contexts.studio.infrastructure.ai_provider import (
    create_studio_text_generation_provider,
)
from src.contexts.studio.infrastructure.database import StudioDatabase, backup_database
from src.contexts.studio.infrastructure.exporters import DEFAULT_EXPORT_WRITERS
from src.contexts.studio.infrastructure.models import (
    Job,
    JobEvent,
    Project,
    SessionRecord,
)
from src.contexts.studio.infrastructure.repository import SqlAlchemyStudioRepository
from src.shared.infrastructure.config import settings as settings_module


@pytest.fixture
def database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[StudioDatabase]:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    settings_module.reset_settings()
    database = StudioDatabase(f"sqlite:///{tmp_path / 'studio.sqlite3'}")
    database.initialize(create_backup=False)
    try:
        yield database
    finally:
        database.dispose()
        settings_module.reset_settings()


@pytest.fixture
def store(tmp_path: Path, database: StudioDatabase) -> StudioStore:
    return StudioStore(
        repository=SqlAlchemyStudioRepository(database),
        data_dir=tmp_path,
        ai_provider_factory=create_studio_text_generation_provider,
        session_secret=settings_module.get_settings().security.secret_key,
        export_writers=DEFAULT_EXPORT_WRITERS,
    )


def _owner(store: StudioStore) -> Principal:
    store.setup_owner("author", "long-test-password")
    return store.owner_principal()


def test_revisions_are_immutable_and_stale_saves_conflict(store: StudioStore) -> None:
    principal = _owner(store)
    project = store.create_project(principal, title="Revision Test")
    document = project["documents"][0]
    initial = document["current_revision_id"]

    saved = store.save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="# Chapter 1\n\nA changed paragraph.",
        base_revision_id=initial,
    )

    with pytest.raises(RevisionConflict):
        store.save_document(
            principal,
            project["id"],
            document["id"],
            content_markdown="stale overwrite",
            base_revision_id=initial,
        )

    revisions = store.list_revisions(principal, project["id"], document["id"])
    assert len(revisions) == 2
    assert [revision["revision_number"] for revision in revisions] == [2, 1]
    assert revisions[0]["parent_revision_id"] == initial
    assert saved["current_revision_id"] == revisions[0]["id"]
    assert revisions[1]["content_markdown"] == "# Chapter 1\n\n"


def test_session_secret_verifies_sessions_and_rotation_invalidates_old_tokens(
    tmp_path: Path,
    database: StudioDatabase,
) -> None:
    def build_store(session_secret: str) -> StudioStore:
        return StudioStore(
            repository=SqlAlchemyStudioRepository(database),
            data_dir=tmp_path,
            ai_provider_factory=create_studio_text_generation_provider,
            session_secret=session_secret,
            export_writers=DEFAULT_EXPORT_WRITERS,
        )

    original = build_store("session-secret-v1")
    token, csrf_token, principal = original.create_guest_session()

    assert csrf_token
    verified = original.principal_from_token(token)
    assert verified is not None
    assert verified.session_id == principal.session_id
    assert verified.kind == principal.kind
    assert verified.owner_id == principal.owner_id

    same_key = build_store("session-secret-v1")
    same_key_principal = same_key.principal_from_token(token)
    assert same_key_principal is not None
    assert same_key_principal.session_id == principal.session_id

    rotated = build_store("session-secret-v2")
    assert rotated.principal_from_token(token) is None


def test_search_snapshot_and_exports_use_exact_revisions(store: StudioStore) -> None:
    principal = _owner(store)
    project = store.create_project(principal, title="Snapshot Test")
    document = project["documents"][0]
    saved = store.save_document(
        principal,
        project["id"],
        document["id"],
        content_markdown="# Chapter 1\n\nThe lighthouse went dark.",
        base_revision_id=document["current_revision_id"],
    )

    results = store.search(principal, project["id"], "lighthouse")
    assert results[0]["document_id"] == document["id"]
    assert "<mark>" not in results[0]["excerpt"]

    malicious_results = store.search(
        principal,
        project["id"],
        'lighthouse" OR title:Chapter*',
    )
    assert malicious_results == []

    export_formats: tuple[ExportFormat, ...] = ("markdown", "docx", "epub")
    exports = [
        store.export_project(principal, project["id"], export_format=export_format)
        for export_format in export_formats
    ]
    assert len({item["snapshot_id"] for item in exports}) == 1

    snapshots = store.list_snapshots(principal, project["id"])
    snapshot_by_id = {snapshot["id"]: snapshot for snapshot in snapshots}
    for item in exports:
        snapshot = snapshot_by_id[item["snapshot_id"]]
        assert snapshot["documents"][0]["revision_id"] == saved["current_revision_id"]

    markdown_path = store.export_path(
        principal,
        project["id"],
        exports[0]["id"],
    )
    assert "The lighthouse went dark." in markdown_path.read_text(encoding="utf-8")


def test_guest_cleanup_cascades_projects(
    store: StudioStore,
    database: StudioDatabase,
) -> None:
    _token, _csrf, principal = store.create_guest_session()
    project = store.create_project(principal, title="Temporary")
    with database.session() as session:
        record = session.get(SessionRecord, principal.session_id)
        assert record is not None
        record.expires_at = utcnow() - timedelta(minutes=1)

    assert store.cleanup_expired_guests() == 1
    with database.session() as session:
        assert session.get(Project, project["id"]) is None


async def test_running_jobs_are_interrupted_and_retryable(
    store: StudioStore,
    database: StudioDatabase,
) -> None:
    principal = _owner(store)
    project = store.create_project(principal, title="Jobs")
    document = project["documents"][0]
    proposal = await store.create_ai_proposal(
        principal,
        project["id"],
        document["id"],
        operation="continue",
        instruction="Raise the stakes.",
        provider="mock",
        model="deterministic",
    )
    with database.session() as session:
        job = session.get(Job, proposal["id"])
        assert job is not None
        job.status = "running"

    assert database.recover_jobs() == 1
    with database.session() as session:
        event = session.query(JobEvent).filter(JobEvent.job_id == proposal["id"]).all()
        assert event[-1].status == "interrupted"
    retry = await store.retry_job(principal, project["id"], proposal["id"])
    # retry_job now immediately re-executes the work, so the mock provider
    # finishes synchronously and the retry job ends up completed.
    assert retry["status"] == "completed"
    assert retry["retry_of_job_id"] == proposal["id"]


def test_legacy_import_is_idempotent(store: StudioStore, tmp_path: Path) -> None:
    principal = _owner(store)
    legacy = tmp_path / "legacy"
    chapters = legacy / "manuscript" / "chapters"
    chapters.mkdir(parents=True)
    (legacy / "story.yaml").write_text(
        "title: Imported Story\npremise: A precise migration.\n",
        encoding="utf-8",
    )
    (chapters / "chapter-001.md").write_text("# One\n\nOriginal.", encoding="utf-8")

    first = store.import_legacy_workspace(principal, legacy)
    second = store.import_legacy_workspace(principal, legacy)

    assert first["id"] == second["id"]
    assert first["import_hash"] == second["import_hash"]
    assert (
        (chapters / "chapter-001.md").read_text(encoding="utf-8").endswith("Original.")
    )


def test_online_backup_is_consistent_with_wal(
    store: StudioStore,
    database: StudioDatabase,
) -> None:
    principal = _owner(store)
    project = store.create_project(principal, title="Backup Test")
    path = database.path
    assert path is not None

    backup = backup_database(path)

    assert backup is not None
    with sqlite3.connect(backup) as connection:
        title = connection.execute(
            "SELECT title FROM projects WHERE id = ?",
            (project["id"],),
        ).fetchone()
        integrity = connection.execute("PRAGMA quick_check").fetchone()
    assert title == ("Backup Test",)
    assert integrity == ("ok",)


def test_load_json_returns_empty_for_empty_input_and_raises_for_invalid_json() -> None:
    assert load_json(None) == {}
    assert load_json("") == {}
    assert load_json('{"valid": true}') == {"valid": True}

    with pytest.raises(ValueError, match="Malformed JSON"):
        load_json("not valid json")


def test_repository_scopes_isolate_projects_between_principals(
    store: StudioStore,
) -> None:
    owner = _owner(store)
    project = store.create_project(owner, title="Private")
    _, _, guest = store.auth.create_guest_session()

    with pytest.raises(NotFound):
        store.get_project(guest, project["id"])

    with pytest.raises(NotFound):
        store.delete_project(guest, project["id"])
