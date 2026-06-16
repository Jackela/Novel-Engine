from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.studio.application.services import (
    Principal,
    StudioStore,
    _sanitize_chapter_markdown,
)
from src.contexts.studio.domain.exceptions import RevisionConflict
from src.contexts.studio.domain.types import ExportFormat
from src.contexts.studio.domain.utils import load_json, utcnow
from src.contexts.studio.infrastructure.ai_provider import (
    create_studio_text_generation_provider,
)
from src.contexts.studio.infrastructure.database import StudioDatabase, backup_database
from src.contexts.studio.infrastructure.models import (
    Job,
    JobEvent,
    Project,
    SessionRecord,
)
from src.contexts.studio.infrastructure.repository import SqlAlchemyStudioRepository
from src.shared.infrastructure.config import settings as settings_module


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> StudioStore:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    settings_module.reset_settings()
    database = StudioDatabase(f"sqlite:///{tmp_path / 'studio.sqlite3'}")
    database.initialize(create_backup=False)
    return StudioStore(
        repository=SqlAlchemyStudioRepository(database),
        data_dir=tmp_path,
        ai_provider_factory=create_studio_text_generation_provider,
    )


def _owner(store: StudioStore) -> Principal:
    store.setup_owner("author", "long-test-password")
    return store.owner_principal()


class MechanicalPhraseProvider:
    """Fixture provider that returns known mechanical DashScope phrases."""

    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self._payload = payload

    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        payload = self._payload or {
            "chapter_markdown": (
                "# Chapter 1: The Bell Debt\n\n"
                "Here is the first draft of the rewritten chapter.\n\n"
                "Mira followed the bell through the flooded arcade while every "
                "shopkeeper pretended not to hear it. The sound named a debt before "
                "the collector arrived, and that made the silence around her feel "
                "too carefully arranged.\n\n"
                "The chapter closes with Mira stepping into the counting room."
            )
        }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="mechanical-phrase-fixture",
            raw_text=json.dumps(payload, ensure_ascii=False),
            content=payload,
        )


def _assert_no_mechanical_prose(markdown: str) -> None:
    lowered = markdown.lower()
    forbidden = (
        "here is the first draft",
        "rewritten chapter",
        "the chapter closes",
        "revision anchor:",
        "focus_motivation",
        "relationship_status",
        "outline_hook",
    )
    for phrase in forbidden:
        assert phrase not in lowered, f"mechanical prose found: {phrase!r}"


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


def test_guest_cleanup_cascades_projects(store: StudioStore) -> None:
    _token, _csrf, principal = store.create_guest_session()
    project = store.create_project(principal, title="Temporary")
    with store.database.session() as session:
        record = session.get(SessionRecord, principal.session_id)
        assert record is not None
        record.expires_at = utcnow() - timedelta(minutes=1)

    assert store.cleanup_expired_guests() == 1
    with store.database.session() as session:
        assert session.get(Project, project["id"]) is None


async def test_running_jobs_are_interrupted_and_retryable(store: StudioStore) -> None:
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
    with store.database.session() as session:
        job = session.get(Job, proposal["id"])
        assert job is not None
        job.status = "running"

    assert store.database.recover_jobs() == 1
    with store.database.session() as session:
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
    assert (chapters / "chapter-001.md").read_text(encoding="utf-8").endswith("Original.")


def test_online_backup_is_consistent_with_wal(store: StudioStore) -> None:
    principal = _owner(store)
    project = store.create_project(principal, title="Backup Test")
    path = store.database.path
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


def test_load_json_returns_empty_for_invalid_json_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert load_json(None) == {}
    assert load_json("") == {}
    assert load_json('{"valid": true}') == {"valid": True}

    with caplog.at_level("WARNING"):
        assert load_json("not valid json") == {}

    assert "json_decode_failed" in caplog.text
    assert "not valid json" in caplog.text


def test_sanitize_chapter_markdown_removes_preambles_and_rewrites_phrases() -> None:
    raw = (
        "# Chapter 1\n\n"
        "Here is the first draft of the rewritten chapter.\n\n"
        "Revision anchor: keep the tension high.\n\n"
        "The focus character studied the focus_motivation and the relationship_status.\n\n"
        "The chapter closes with a whisper.\n\n"
        "The outline_hook will return in the next scene.\n\n"
        "Trailing spaces line.   \n"
        "\n\n\n\n"
        "Final paragraph."
    )
    cleaned = _sanitize_chapter_markdown(raw)

    _assert_no_mechanical_prose(cleaned)
    assert "# Chapter 1" in cleaned
    assert "central figure" in cleaned.lower()
    assert "central motivation" in cleaned.lower()
    assert "relationship state" in cleaned.lower()
    assert "the scene settles with a whisper" in cleaned.lower()
    assert "what follows" in cleaned.lower()
    assert "story hook" in cleaned.lower()
    assert "Trailing spaces line." in cleaned
    assert "   \n" not in cleaned
    assert "\n\n\n" not in cleaned


@pytest.mark.asyncio
async def test_create_ai_proposal_sanitizes_mechanical_phrases_before_storage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    settings_module.reset_settings()
    database = StudioDatabase(f"sqlite:///{tmp_path / 'studio.sqlite3'}")
    database.initialize(create_backup=False)
    store = StudioStore(
        repository=SqlAlchemyStudioRepository(database),
        data_dir=tmp_path,
        ai_provider_factory=lambda _provider, _model: MechanicalPhraseProvider(),
    )
    principal = _owner(store)
    project = store.create_project(principal, title="Sanitize Test")
    document = project["documents"][0]

    proposal = await store.create_ai_proposal(
        principal,
        project["id"],
        document["id"],
        operation="continue",
        instruction="Raise the stakes.",
        provider="mock",
        model="mechanical-phrase-fixture",
    )

    proposal_markdown = proposal["result"]["proposal_markdown"]
    _assert_no_mechanical_prose(proposal_markdown)
    assert "Mira followed the bell" in proposal_markdown
    assert "The scene settles with Mira stepping" in proposal_markdown
