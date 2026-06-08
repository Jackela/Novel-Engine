from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast

import pytest

from src.apps.cli.novel_engine import main
from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.local_writing_engine import (
    LocalDraftingEngine,
    LocalExporter,
    LocalReviewer,
    NovelWorkspace,
    StoryConfig,
)


def build_workspace(tmp_path: Path, *, target_chapters: int = 3) -> NovelWorkspace:
    return NovelWorkspace.create(
        tmp_path / "novel",
        StoryConfig(
            title="The Salt Ledger",
            genre="mystery",
            premise="A courier receives a page that names debts before they happen.",
            target_chapters=target_chapters,
            tone="sharp, atmospheric serial fiction",
        ),
    )


class MechanicalPhraseProvider:
    async def generate_structured(
        self,
        task: TextGenerationTask,
    ) -> TextGenerationResult:
        payload = {
            "chapter_markdown": (
                "# Chapter 1: The Bell Debt\n\n"
                "Here is the first draft of the rewritten chapter.\n\n"
                "Mira followed the bell through the flooded arcade while every "
                "shopkeeper pretended not to hear it. The sound named a debt before "
                "the collector arrived, and that made the silence around her feel "
                "too carefully arranged.\n\n"
                "The chapter closes with Mira stepping into the counting room."
            ),
            "sidecar_metadata": {
                "summary": "Mira follows a bell debt into the counting room.",
                "characters": ["Mira"],
                "promises": [],
                "continuity_changes": [],
                "style_notes": [],
            },
        }
        return TextGenerationResult(
            step=task.step,
            provider="mock",
            model="mechanical-phrase-fixture",
            raw_text=json.dumps(payload, ensure_ascii=False),
            content=payload,
        )


def assert_no_mechanical_prose(markdown: str) -> None:
    lowered = markdown.lower()
    forbidden = (
        "revision anchor:",
        "the chapter closes",
        "the next scene",
        "first draft",
        "rewritten chapter",
        "focus_motivation",
        "relationship_status",
        "outline_hook",
    )
    for phrase in forbidden:
        assert phrase not in lowered


@pytest.mark.asyncio
async def test_local_workspace_drafts_complete_chapter_artifact(
    tmp_path: Path,
) -> None:
    workspace = build_workspace(tmp_path)
    engine = LocalDraftingEngine(DeterministicTextGenerationProvider())

    artifact = await engine.draft_chapter(workspace, 1)

    chapter_path = workspace.chapter_path(1)
    assert chapter_path.exists()
    chapter_text = chapter_path.read_text(encoding="utf-8")
    assert chapter_text.startswith("# Chapter 1:")
    assert_no_mechanical_prose(chapter_text)

    assert artifact.sidecar_metadata["summary"]
    assert artifact.sidecar_metadata["characters"]
    sidecar_path = (
        workspace.runs_dir / artifact.run_id / "chapter-001.sidecar.json"
    )
    assert sidecar_path.exists()
    assert json.loads(sidecar_path.read_text(encoding="utf-8"))["summary"]


@pytest.mark.asyncio
async def test_provider_mechanical_phrases_are_sanitized_before_storage(
    tmp_path: Path,
) -> None:
    workspace = build_workspace(tmp_path, target_chapters=1)
    engine = LocalDraftingEngine(MechanicalPhraseProvider())

    artifact = await engine.draft_chapter(workspace, 1)

    chapter_text = workspace.read_chapter(1)
    assert_no_mechanical_prose(chapter_text)
    assert "Mira followed the bell" in chapter_text
    assert "The scene settles with Mira stepping into the counting room." in chapter_text
    assert "first draft" in artifact.raw_model_output.lower()
    assert artifact.chapter_markdown == chapter_text.strip()


@pytest.mark.asyncio
async def test_run_resumes_existing_chapters_without_overwrite(
    tmp_path: Path,
) -> None:
    workspace = build_workspace(tmp_path)
    engine = LocalDraftingEngine(DeterministicTextGenerationProvider())

    await engine.draft_chapter(workspace, 1)
    original = workspace.read_chapter(1)
    await engine.draft_chapter(workspace, 1)
    await engine.draft_chapter(workspace, 2)
    await engine.draft_chapter(workspace, 3)

    assert workspace.read_chapter(1) == original
    assert len(workspace.list_chapters()) == 3
    sidecars = workspace.load_latest_sidecars()
    assert set(sidecars) == {1, 2, 3}
    assert sidecars[1].get("skipped") is True


def test_review_warnings_do_not_block_export(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    workspace.write_chapter(1, "# Chapter 1\n\nShort but valid prose.")

    report = LocalReviewer().review(workspace)

    assert report.blockers == []
    assert [issue.code for issue in report.warnings] == ["thin_chapter"]
    assert {issue.code for issue in report.suggestions} == {
        "agency_attribution",
        "causal_continuity",
        "reader_pull",
        "closure_spacing",
        "promise_trust",
        "voice_stability",
    }
    assert all(issue.details.get("evidence") for issue in report.suggestions)
    exported = LocalExporter().export_markdown(workspace)
    assert exported.exists()
    assert "# The Salt Ledger" in exported.read_text(encoding="utf-8")


def test_review_blocks_empty_chapter_export(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    workspace.write_chapter(1, "")

    report = LocalReviewer().review(workspace)

    assert [issue.code for issue in report.blockers] == ["empty_chapter"]
    with pytest.raises(ValueError, match="Export blocked"):
        LocalExporter().export_markdown(workspace)


@pytest.mark.asyncio
async def test_revision_uses_full_rewrite_without_patch_anchor(
    tmp_path: Path,
) -> None:
    workspace = build_workspace(tmp_path)
    engine = LocalDraftingEngine(DeterministicTextGenerationProvider())
    await engine.draft_chapter(workspace, 1)

    artifact = await engine.revise_chapter(workspace, 1)

    chapter_text = workspace.read_chapter(1)
    assert_no_mechanical_prose(chapter_text)
    assert "The Debt in the Rain" in chapter_text
    assert artifact.sidecar_metadata["summary"]


def test_cli_init_draft_review_export_roundtrip(tmp_path: Path) -> None:
    workspace = tmp_path / "cli-novel"

    assert (
        main(
            [
                "init",
                "--workspace",
                str(workspace),
                "--title",
                "CLI Story",
                "--genre",
                "fantasy",
                "--premise",
                "A map starts answering questions before they are asked.",
                "--target-chapters",
                "1",
            ]
        )
        == 0
    )
    assert (
        main(["draft", "--workspace", str(workspace), "--chapter", "1"]) == 0
    )
    assert main(["review", "--workspace", str(workspace)]) == 0
    assert main(["export", "--workspace", str(workspace)]) == 0
    assert (workspace / "exports" / "manuscript.md").exists()


def test_cli_run_writes_one_recoverable_journal(tmp_path: Path) -> None:
    workspace = tmp_path / "cli-run-novel"

    assert (
        main(
            [
                "init",
                "--workspace",
                str(workspace),
                "--title",
                "Run Story",
                "--genre",
                "speculative mystery",
                "--premise",
                "A city archive starts filing records from tomorrow.",
                "--target-chapters",
                "3",
            ]
        )
        == 0
    )
    assert main(["run", "--workspace", str(workspace), "--target-chapters", "3"]) == 0

    run_dirs = sorted((workspace / "artifacts" / "runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "chapter-001.sidecar.json").exists()
    assert (run_dir / "chapter-002.sidecar.json").exists()
    assert (run_dir / "chapter-003.sidecar.json").exists()
    assert (run_dir / "review-report.json").exists()
    events = [
        json.loads(line)
        for line in (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events[0]["operation"] == "run"
    assert events[-1]["status"] == "completed"
    assert events[-1]["details"]["target_chapters"] == 3


def test_mock_provider_varies_chapter_surface(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)
    engine = LocalDraftingEngine(DeterministicTextGenerationProvider())

    async def draft_three() -> None:
        await engine.draft_chapter(workspace, 1)
        await engine.draft_chapter(workspace, 2)
        await engine.draft_chapter(workspace, 3)

    import asyncio

    asyncio.run(draft_three())

    chapters = [workspace.read_chapter(number) for number in range(1, 4)]
    assert len(set(chapters)) == 3
    assert "# Chapter 1: The First Cost" in chapters[0]
    assert "# Chapter 2: A Record Filed Early" in chapters[1]
    assert "# Chapter 3: The Witness Under Glass" in chapters[2]
    for chapter in chapters:
        assert_no_mechanical_prose(chapter)


def test_mock_editorial_judge_uses_distinct_manuscript_evidence(
    tmp_path: Path,
) -> None:
    workspace = build_workspace(tmp_path)
    engine = LocalDraftingEngine(DeterministicTextGenerationProvider())

    async def draft_and_review() -> list[dict[str, object]]:
        await engine.draft_chapter(workspace, 1)
        await engine.draft_chapter(workspace, 2)
        await engine.draft_chapter(workspace, 3)
        report = await LocalReviewer(
            DeterministicTextGenerationProvider()
        ).review_async(workspace)
        return [issue.to_dict() for issue in report.suggestions]

    import asyncio

    suggestions = asyncio.run(draft_and_review())

    assert [issue["code"] for issue in suggestions] == [
        "agency_attribution",
        "causal_continuity",
        "reader_pull",
        "closure_spacing",
        "promise_trust",
        "voice_stability",
    ]
    evidences = [
        str(cast(dict[str, object], issue["details"])["evidence"])
        for issue in suggestions
    ]
    assert len(set(evidences)) == 6
    assert len({str(issue["message"]) for issue in suggestions}) == 6
    assert len({str(issue["suggestion"]) for issue in suggestions}) == 6


def test_workspace_lock_blocks_cross_thread_writers(tmp_path: Path) -> None:
    workspace = build_workspace(tmp_path)

    def contend_for_lock() -> None:
        with pytest.raises(TimeoutError):
            with workspace.acquire_lock(operation="contender", timeout=0.05):
                pass

    with workspace.acquire_lock(operation="owner"):
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(contend_for_lock).result(timeout=1)
