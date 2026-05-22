"""Local-first Novel Engine writing runtime.

The local workspace owns manuscript files, while structured data is recorded as
sidecar evidence for planning, review, and recovery.
"""

from __future__ import annotations

import contextvars
import json
import os
import re
import shutil
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

import yaml

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationResult,
    TextGenerationTask,
)

ReviewSeverity = Literal["blocker", "warning", "suggestion"]

LOCK_STALE_AFTER_SECONDS = 60 * 60
LOCK_WAIT_SECONDS = 30.0
LOCK_POLL_SECONDS = 0.05

FORBIDDEN_TEMPLATE_PHRASES = (
    "Revision anchor:",
    "The chapter closes",
    "The next scene",
    "first draft",
    "rewritten chapter",
    "focus character",
    "focus_motivation",
    "relationship_status",
    "outline_hook",
)

_active_lock_paths: contextvars.ContextVar[frozenset[Path]] = contextvars.ContextVar(
    "novel_engine_active_lock_paths",
    default=frozenset(),
)


def utcnow_iso() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def chapter_filename(chapter_number: int) -> str:
    """Return the canonical manuscript filename for a chapter."""
    if chapter_number < 1:
        raise ValueError("chapter_number must be positive")
    return f"chapter-{chapter_number:03d}.md"


def _safe_relative_path(path: Path, root: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes workspace root: {path}") from exc


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


@dataclass(slots=True)
class StoryConfig:
    """Local story configuration stored in story.yaml."""

    title: str
    genre: str
    premise: str
    target_chapters: int = 12
    tone: str = "immersive serial fiction"
    target_audience: str | None = None
    themes: list[str] = field(default_factory=list)
    style_profile: dict[str, Any] = field(default_factory=dict)
    continuity: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoryConfig:
        """Build a story config from YAML data."""
        title = str(data.get("title", "")).strip()
        genre = str(data.get("genre", "")).strip()
        premise = str(data.get("premise", "")).strip()
        if not title:
            raise ValueError("story.yaml missing title")
        if not genre:
            raise ValueError("story.yaml missing genre")
        if not premise:
            raise ValueError("story.yaml missing premise")
        target_chapters = int(data.get("target_chapters", 12))
        if target_chapters < 1:
            raise ValueError("target_chapters must be positive")
        themes = data.get("themes", [])
        style_profile = data.get("style_profile", {})
        continuity = data.get("continuity", {})
        return cls(
            title=title,
            genre=genre,
            premise=premise,
            target_chapters=target_chapters,
            tone=str(data.get("tone", "immersive serial fiction")).strip()
            or "immersive serial fiction",
            target_audience=(
                str(data["target_audience"]).strip()
                if data.get("target_audience")
                else None
            ),
            themes=[str(theme).strip() for theme in themes if str(theme).strip()]
            if isinstance(themes, list)
            else [],
            style_profile=dict(style_profile) if isinstance(style_profile, dict) else {},
            continuity=dict(continuity) if isinstance(continuity, dict) else {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the config for story.yaml."""
        return asdict(self)


@dataclass(slots=True)
class DraftChapterTask:
    """Input needed to draft a complete chapter."""

    config: StoryConfig
    chapter_number: int
    previous_summaries: list[str]
    unresolved_promises: list[str]
    character_state: list[str]
    style_profile: dict[str, Any]
    forbidden_phrases: tuple[str, ...] = FORBIDDEN_TEMPLATE_PHRASES


@dataclass(slots=True)
class ChapterDraftArtifact:
    """A complete chapter draft plus sidecar evidence."""

    chapter_number: int
    chapter_markdown: str
    sidecar_metadata: dict[str, Any]
    raw_model_output: str
    provider: str
    model: str
    created_at: str
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the chapter draft artifact."""
        return asdict(self)


@dataclass(slots=True)
class ReviewIssue:
    """A review issue that may or may not block export."""

    severity: ReviewSeverity
    code: str
    message: str
    location: str
    suggestion: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the review issue."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewIssue | None:
        """Build a review issue from stored JSON when severity is known."""
        severity = _review_severity(data.get("severity"))
        if severity is None:
            return None
        return cls(
            severity=severity,
            code=str(data.get("code", "")).strip(),
            message=str(data.get("message", "")).strip(),
            location=str(data.get("location", "")).strip(),
            suggestion=str(data.get("suggestion", "")).strip(),
            details=(
                dict(data["details"]) if isinstance(data.get("details"), dict) else {}
            ),
        )


def _review_severity(value: object) -> ReviewSeverity | None:
    """Return a typed review severity for stored JSON values."""
    if value in {"blocker", "warning", "suggestion"}:
        return cast(ReviewSeverity, value)
    return None


def _load_review_issues(items: object) -> list[ReviewIssue]:
    """Load review issues while ignoring malformed entries."""
    if not isinstance(items, list):
        return []
    issues: list[ReviewIssue] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        issue = ReviewIssue.from_dict(cast(dict[str, Any], item))
        if issue is not None:
            issues.append(issue)
    return issues


@dataclass(slots=True)
class ReviewReport:
    """Generic local review report."""

    story_title: str
    checked_at: str
    blockers: list[ReviewIssue] = field(default_factory=list)
    warnings: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[ReviewIssue] = field(default_factory=list)
    style_notes: list[str] = field(default_factory=list)

    @property
    def export_blocked(self) -> bool:
        """Return whether blockers prevent export."""
        return bool(self.blockers)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the review report."""
        return {
            "story_title": self.story_title,
            "checked_at": self.checked_at,
            "export_blocked": self.export_blocked,
            "blockers": [issue.to_dict() for issue in self.blockers],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "suggestions": [issue.to_dict() for issue in self.suggestions],
            "style_notes": list(self.style_notes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewReport:
        """Build a review report from stored JSON."""
        return cls(
            story_title=str(data.get("story_title", "")),
            checked_at=str(data.get("checked_at", "")),
            blockers=_load_review_issues(data.get("blockers")),
            warnings=_load_review_issues(data.get("warnings")),
            suggestions=_load_review_issues(data.get("suggestions")),
            style_notes=[
                str(note).strip()
                for note in data.get("style_notes", [])
                if str(note).strip()
            ],
        )


class NovelWorkspace:
    """Local workspace backed by story.yaml and manuscript artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.story_path = self.root / "story.yaml"
        self.chapters_dir = self.root / "manuscript" / "chapters"
        self.runs_dir = self.root / "artifacts" / "runs"
        self.exports_dir = self.root / "exports"
        self.reviews_dir = self.root / "artifacts" / "reviews"
        self.jobs_dir = self.root / "artifacts" / "jobs"
        self.lock_path = self.root / ".novel-engine.lock"

    @classmethod
    def create(
        cls,
        root: Path,
        config: StoryConfig,
        *,
        overwrite: bool = False,
    ) -> NovelWorkspace:
        """Create a local workspace."""
        workspace = cls(root)
        workspace.root.mkdir(parents=True, exist_ok=True)
        with workspace.acquire_lock(operation="init"):
            if workspace.story_path.exists() and not overwrite:
                raise FileExistsError(f"story.yaml already exists: {workspace.story_path}")
            if overwrite:
                workspace._clear_workspace_contents()
            workspace._ensure_directories()
            _atomic_write_text(
                workspace.story_path,
                yaml.safe_dump(config.to_dict(), sort_keys=False, allow_unicode=True),
            )
        return workspace

    def _ensure_directories(self) -> None:
        self.chapters_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def _clear_workspace_contents(self) -> None:
        """Remove workspace contents after verifying every path stays in root."""
        resolved_root = self.root.resolve()
        if resolved_root.parent == resolved_root:
            raise ValueError("refusing to clear filesystem root")
        lock_path = self.lock_path.resolve()
        for path in self.root.iterdir():
            resolved = path.resolve()
            if resolved_root not in {resolved, *resolved.parents}:
                raise ValueError(f"refusing to delete path outside workspace: {path}")
            if resolved == lock_path:
                continue
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

    @contextmanager
    def acquire_lock(
        self,
        *,
        operation: str,
        timeout: float = LOCK_WAIT_SECONDS,
    ) -> Iterator[None]:
        """Acquire a cross-process workspace lock."""
        self.root.mkdir(parents=True, exist_ok=True)
        lock_path = self.lock_path.resolve()
        active_paths = _active_lock_paths.get()
        if lock_path in active_paths:
            yield
            return

        deadline = time.monotonic() + timeout
        token: contextvars.Token[frozenset[Path]] | None = None
        acquired = False
        while not acquired:
            try:
                fd = os.open(
                    lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                if self._lock_is_stale():
                    try:
                        lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Workspace is locked by another operation: {self.root}"
                    )
                time.sleep(LOCK_POLL_SECONDS)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "operation": operation,
                            "created_at": utcnow_iso(),
                            "pid": os.getpid(),
                        },
                        ensure_ascii=False,
                    )
                )
            acquired = True

        try:
            token = _active_lock_paths.set(active_paths | {lock_path})
            yield
        finally:
            if token is not None:
                _active_lock_paths.reset(token)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _lock_is_stale(self) -> bool:
        try:
            created = self.lock_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return time.time() - created > LOCK_STALE_AFTER_SECONDS

    def relative_path(self, path: Path) -> str:
        """Return a browser-safe path relative to the workspace root."""
        return _safe_relative_path(path, self.root)

    def load_config(self) -> StoryConfig:
        """Load story.yaml."""
        if not self.story_path.exists():
            raise FileNotFoundError(f"story.yaml not found: {self.story_path}")
        payload = yaml.safe_load(self.story_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError("story.yaml must contain an object")
        return StoryConfig.from_dict(payload)

    def chapter_path(self, chapter_number: int) -> Path:
        """Return the canonical chapter path."""
        return self.chapters_dir / chapter_filename(chapter_number)

    def read_chapter(self, chapter_number: int) -> str:
        """Read a chapter manuscript."""
        return self.chapter_path(chapter_number).read_text(encoding="utf-8")

    def write_chapter(self, chapter_number: int, markdown: str) -> Path:
        """Write a complete chapter manuscript."""
        self._ensure_directories()
        path = self.chapter_path(chapter_number)
        _atomic_write_text(path, markdown.rstrip() + "\n")
        return path

    def list_chapters(self) -> list[Path]:
        """Return chapter files in manuscript order."""
        if not self.chapters_dir.exists():
            return []
        return sorted(self.chapters_dir.glob("chapter-*.md"))

    def latest_chapter_number(self) -> int:
        """Return the latest drafted chapter number."""
        latest = 0
        for path in self.list_chapters():
            try:
                latest = max(latest, int(path.stem.split("-")[-1]))
            except ValueError:
                continue
        return latest

    def start_run(self, operation: str) -> Path:
        """Create a new run directory."""
        self._ensure_directories()
        run_id = f"{utcnow_iso().replace(':', '').replace('.', '-')}-{uuid4().hex[:8]}"
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        self.append_event(run_dir, operation, "started", {"run_id": run_id})
        return run_dir

    def append_event(
        self,
        run_dir: Path,
        operation: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append a run event without copying the whole workspace."""
        event = {
            "timestamp": utcnow_iso(),
            "operation": operation,
            "status": status,
            "details": self._sanitize_event_details(details or {}),
        }
        run_dir.mkdir(parents=True, exist_ok=True)
        with (run_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _sanitize_event_details(self, value: object) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                next_key = str(key)
                if next_key == "chapter_file":
                    next_key = "chapter_relative_path"
                elif next_key == "review_report":
                    next_key = "review_report_relative_path"
                sanitized[next_key] = self._sanitize_event_details(item)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_event_details(item) for item in value]
        if isinstance(value, tuple):
            return [self._sanitize_event_details(item) for item in value]
        if isinstance(value, str):
            try:
                path = Path(value).resolve()
            except (OSError, ValueError):
                path = None
            if path is not None and self.root in {path, *path.parents}:
                return self.relative_path(path)
            return value.replace(str(self.root), "<workspace>")
        return value

    def store_artifact(self, artifact: ChapterDraftArtifact, run_dir: Path) -> None:
        """Store sidecar, raw provider output, and artifact manifest."""
        prefix = f"chapter-{artifact.chapter_number:03d}"
        _atomic_write_text(
            run_dir / f"{prefix}.sidecar.json",
            json.dumps(artifact.sidecar_metadata, ensure_ascii=False, indent=2),
        )
        _atomic_write_text(
            run_dir / f"{prefix}.raw.json",
            artifact.raw_model_output,
        )
        _atomic_write_text(
            run_dir / f"{prefix}.artifact.json",
            json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2),
        )

    def load_latest_sidecars(self) -> dict[int, dict[str, Any]]:
        """Load the latest sidecar metadata per chapter."""
        sidecars: dict[int, dict[str, Any]] = {}
        if not self.runs_dir.exists():
            return sidecars
        for path in sorted(self.runs_dir.glob("*/chapter-*.sidecar.json")):
            try:
                chapter_number = int(path.stem.split(".")[0].split("-")[-1])
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                sidecars[chapter_number] = payload
        return sidecars

    def store_review(self, report: ReviewReport) -> Path:
        """Store the latest and timestamped review reports."""
        self._ensure_directories()
        payload = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
        timestamped = self.reviews_dir / f"review-{utcnow_iso().replace(':', '')}.json"
        _atomic_write_text(timestamped, payload)
        _atomic_write_text(self.reviews_dir / "latest.json", payload)
        return timestamped

    def latest_review(self) -> ReviewReport | None:
        """Return the latest review report if one exists."""
        path = self.reviews_dir / "latest.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        return ReviewReport.from_dict(payload)


class LocalDraftingEngine:
    """Draft and revise full chapter manuscripts."""

    def __init__(self, provider: TextGenerationProvider) -> None:
        self._provider = provider

    async def draft_chapter(
        self,
        workspace: NovelWorkspace,
        chapter_number: int,
        *,
        force: bool = False,
        run_dir: Path | None = None,
    ) -> ChapterDraftArtifact:
        """Draft one complete chapter markdown file."""
        with workspace.acquire_lock(operation="draft"):
            return await self._draft_chapter_unlocked(
                workspace,
                chapter_number,
                force=force,
                run_dir=run_dir,
            )

    async def _draft_chapter_unlocked(
        self,
        workspace: NovelWorkspace,
        chapter_number: int,
        *,
        force: bool = False,
        run_dir: Path | None = None,
    ) -> ChapterDraftArtifact:
        current_run_dir = run_dir or workspace.start_run("draft")
        if workspace.chapter_path(chapter_number).exists() and not force:
            existing = workspace.read_chapter(chapter_number)
            artifact = ChapterDraftArtifact(
                chapter_number=chapter_number,
                chapter_markdown=existing,
                sidecar_metadata={
                    "summary": _summarize(existing),
                    "characters": [],
                    "promises": [],
                    "continuity_changes": [],
                    "style_notes": ["Existing chapter preserved during resume."],
                    "skipped": True,
                },
                raw_model_output=json.dumps({"skipped": True}, ensure_ascii=False),
                provider="local",
                model="existing-manuscript",
                created_at=utcnow_iso(),
                run_id=current_run_dir.name,
            )
            workspace.store_artifact(artifact, current_run_dir)
            workspace.append_event(
                current_run_dir,
                "draft",
                "skipped",
                {"chapter_number": chapter_number},
            )
            return artifact

        config = workspace.load_config()
        task = self._build_task(workspace, config, chapter_number)
        try:
            result = await self._provider.generate_structured(
                self._generation_task(task)
            )
            artifact = self._extract_artifact(
                result,
                chapter_number=chapter_number,
                run_id=current_run_dir.name,
            )
            self._validate_chapter_surface(artifact.chapter_markdown)
            workspace.write_chapter(chapter_number, artifact.chapter_markdown)
            workspace.store_artifact(artifact, current_run_dir)
            workspace.append_event(
                current_run_dir,
                "draft",
                "completed",
                {
                    "chapter_number": chapter_number,
                    "chapter_relative_path": workspace.relative_path(
                        workspace.chapter_path(chapter_number)
                    ),
                },
            )
            return artifact
        except Exception as exc:
            workspace.append_event(
                current_run_dir,
                "draft",
                "failed",
                {"chapter_number": chapter_number, "error": str(exc)},
            )
            raise

    async def revise_chapter(
        self,
        workspace: NovelWorkspace,
        chapter_number: int,
        report: ReviewReport | None = None,
    ) -> ChapterDraftArtifact:
        """Rewrite a chapter from an explicit revision brief."""
        with workspace.acquire_lock(operation="revise"):
            return await self._revise_chapter_unlocked(workspace, chapter_number, report)

    async def _revise_chapter_unlocked(
        self,
        workspace: NovelWorkspace,
        chapter_number: int,
        report: ReviewReport | None = None,
    ) -> ChapterDraftArtifact:
        config = workspace.load_config()
        current = workspace.read_chapter(chapter_number)
        issues = []
        if report is not None:
            issues = [
                issue.to_dict()
                for issue in [*report.blockers, *report.warnings]
                if issue.location == f"chapter-{chapter_number:03d}"
                or issue.location == f"chapter-{chapter_number}"
                or issue.location == "manuscript"
            ]
        run_dir = workspace.start_run("revise")
        brief = {
            "chapter_number": chapter_number,
            "issues": issues,
            "instruction": (
                "Rewrite the chapter as natural prose. Preserve the story direction, "
                "remove mechanical repair language, and avoid explaining metadata."
            ),
        }
        _atomic_write_text(
            run_dir / f"chapter-{chapter_number:03d}.revision-brief.json",
            json.dumps(brief, ensure_ascii=False, indent=2),
        )
        result = await self._provider.generate_structured(
            TextGenerationTask(
                step="chapter_revision",
                system_prompt=(
                    "You revise complete fiction chapters. Return JSON with "
                    "chapter_markdown and sidecar_metadata."
                ),
                user_prompt=(
                    f"Story: {config.title}\n"
                    f"Chapter: {chapter_number}\n"
                    f"Current chapter:\n{current}\n"
                    f"Revision brief: {brief}"
                ),
                response_schema={
                    "chapter_markdown": {"type": "string"},
                    "sidecar_metadata": {"type": "object"},
                },
                temperature=0.55,
                metadata={
                    "title": config.title,
                    "genre": config.genre,
                    "premise": config.premise,
                    "chapter_number": chapter_number,
                    "revision_issues": issues,
                    "current_summary": _summarize(current),
                },
            )
        )
        artifact = self._extract_artifact(
            result,
            chapter_number=chapter_number,
            run_id=run_dir.name,
        )
        self._validate_chapter_surface(artifact.chapter_markdown)
        workspace.write_chapter(chapter_number, artifact.chapter_markdown)
        workspace.store_artifact(artifact, run_dir)
        workspace.append_event(
            run_dir,
            "revise",
            "completed",
            {"chapter_number": chapter_number},
        )
        return artifact

    def _build_task(
        self,
        workspace: NovelWorkspace,
        config: StoryConfig,
        chapter_number: int,
    ) -> DraftChapterTask:
        sidecars = workspace.load_latest_sidecars()
        previous_summaries = [
            str(sidecars[number].get("summary", "")).strip()
            for number in sorted(sidecars)
            if number < chapter_number and str(sidecars[number].get("summary", "")).strip()
        ][-5:]
        unresolved_promises = _unresolved_promises(sidecars, chapter_number)
        character_state = _character_state(sidecars, chapter_number)
        return DraftChapterTask(
            config=config,
            chapter_number=chapter_number,
            previous_summaries=previous_summaries,
            unresolved_promises=unresolved_promises,
            character_state=character_state,
            style_profile=config.style_profile,
        )

    def _generation_task(self, task: DraftChapterTask) -> TextGenerationTask:
        config = task.config
        return TextGenerationTask(
            step="chapter_draft",
            system_prompt=(
                "You are a fiction writer drafting complete chapters, not scene JSON. "
                "Write natural, varied prose with concrete action, subtext, and momentum. "
                "The chapter_markdown is the only manuscript authority. "
                "The sidecar_metadata is only for continuity tracking and must not be "
                "copied into the prose."
            ),
            user_prompt=(
                f"Title: {config.title}\n"
                f"Genre: {config.genre}\n"
                f"Premise: {config.premise}\n"
                f"Tone: {config.tone}\n"
                f"Target audience: {config.target_audience or 'general'}\n"
                f"Themes: {config.themes}\n"
                f"Chapter number: {task.chapter_number}\n"
                f"Recent summaries: {task.previous_summaries}\n"
                f"Unresolved promises: {task.unresolved_promises}\n"
                f"Character state: {task.character_state}\n"
                f"Style profile: {task.style_profile}\n"
                f"Do not include these mechanical phrases: {list(task.forbidden_phrases)}"
            ),
            response_schema={
                "chapter_markdown": {"type": "string"},
                "sidecar_metadata": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "characters": {"type": "array", "items": {"type": "string"}},
                        "promises": {"type": "array", "items": {"type": "object"}},
                        "continuity_changes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "style_notes": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            temperature=0.7,
            metadata={
                "title": config.title,
                "genre": config.genre,
                "premise": config.premise,
                "tone": config.tone,
                "chapter_number": task.chapter_number,
                "previous_summaries": task.previous_summaries,
                "unresolved_promises": task.unresolved_promises,
                "character_state": task.character_state,
                "style_profile": task.style_profile,
            },
        )

    def _extract_artifact(
        self,
        result: TextGenerationResult,
        *,
        chapter_number: int,
        run_id: str,
    ) -> ChapterDraftArtifact:
        markdown = str(result.content.get("chapter_markdown", "")).strip()
        sidecar = result.content.get("sidecar_metadata", {})
        if not markdown:
            raise ValueError("Provider returned empty chapter_markdown")
        if not isinstance(sidecar, dict):
            sidecar = {}
        sidecar.setdefault("summary", _summarize(markdown))
        sidecar.setdefault("characters", [])
        sidecar.setdefault("promises", [])
        sidecar.setdefault("continuity_changes", [])
        sidecar.setdefault("style_notes", [])
        return ChapterDraftArtifact(
            chapter_number=chapter_number,
            chapter_markdown=markdown,
            sidecar_metadata=dict(sidecar),
            raw_model_output=result.raw_text,
            provider=result.provider,
            model=result.model,
            created_at=utcnow_iso(),
            run_id=run_id,
        )

    def _validate_chapter_surface(self, markdown: str) -> None:
        lowered = markdown.lower()
        for phrase in FORBIDDEN_TEMPLATE_PHRASES:
            if phrase.lower() in lowered:
                raise ValueError(f"Chapter prose contains forbidden phrase: {phrase}")


EDITORIAL_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("agency_attribution", "agency attribution"),
    ("causal_continuity", "causal continuity"),
    ("reader_pull", "reader pull"),
    ("closure_spacing", "closure spacing"),
    ("promise_trust", "promise trust"),
    ("voice_stability", "voice stability"),
)


class EditorialJudge:
    """Provider-backed editorial reviewer with a deterministic local fallback."""

    def __init__(self, provider: TextGenerationProvider | None = None) -> None:
        self._provider = provider

    async def judge(
        self,
        workspace: NovelWorkspace,
        chapters: list[Path],
        sidecars: dict[int, dict[str, Any]],
    ) -> list[ReviewIssue]:
        """Return editorial suggestions without blocking export."""
        fallback = self.deterministic_suggestions(chapters, sidecars)
        if self._provider is None or not fallback:
            return fallback
        result = await self._provider.generate_structured(
            self._review_task(workspace, chapters, sidecars)
        )
        return self._issues_from_provider(result.content, fallback)

    def deterministic_suggestions(
        self,
        chapters: list[Path],
        sidecars: dict[int, dict[str, Any]],
    ) -> list[ReviewIssue]:
        """Build prose-specific suggestions from manuscript text and sidecars."""
        if not chapters:
            return []
        chapter_texts = [
            (path, path.read_text(encoding="utf-8").strip()) for path in chapters
        ]
        first_path, first_text = chapter_texts[0]
        middle_path, middle_text = chapter_texts[len(chapter_texts) // 2]
        last_path, last_text = chapter_texts[-1]
        promise_texts = _promise_texts(sidecars)
        promise_count = len(promise_texts)
        summary_count = sum(
            1
            for sidecar in sidecars.values()
            if str(sidecar.get("summary", "")).strip()
        )
        short_chapters = [
            path.name
            for path, text in chapter_texts
            if len(text.split()) < 250
        ]
        dialogue_markers = sum(text.count('"') for _, text in chapter_texts)
        chapter_endings = " / ".join(
            f"{path.stem}: {_evidence_snippet(text, from_end=True, limit=72)}"
            for path, text in chapter_texts[-3:]
        )
        primary_promise = promise_texts[0] if promise_texts else _summarize(last_text, 120)
        evidence = {
            "agency_attribution": _evidence_snippet(first_text, limit=180),
            "causal_continuity": _evidence_window(middle_text, 0.45, limit=180),
            "reader_pull": _evidence_snippet(last_text, from_end=True, limit=180),
            "closure_spacing": chapter_endings,
            "promise_trust": primary_promise,
            "voice_stability": _evidence_window(first_text, 0.7, limit=180),
        }
        return [
            ReviewIssue(
                severity="suggestion",
                code="agency_attribution",
                message=(
                    f"{first_path.name} opens around \"{_short_quote(evidence['agency_attribution'])}\"; "
                    "check that the chapter turn is caused by a visible choice."
                ),
                location=first_path.stem,
                suggestion=(
                    f"Give the actor in {first_path.stem} one concrete decision before the reversal lands."
                ),
                details={
                    "dimension": "agency attribution",
                    "evidence": evidence["agency_attribution"],
                    "chapter_word_count": len(first_text.split()),
                },
            ),
            ReviewIssue(
                severity="suggestion",
                code="causal_continuity",
                message=(
                    f"{middle_path.name} carries the chain through \"{_short_quote(evidence['causal_continuity'])}\"; "
                    "verify the consequence follows from an earlier action."
                ),
                location=middle_path.stem,
                suggestion=(
                    f"Use one cause-and-effect sentence in {middle_path.stem} if the beat feels adjacent rather than inevitable."
                ),
                details={
                    "dimension": "causal continuity",
                    "evidence": evidence["causal_continuity"],
                    "sidecar_summaries": summary_count,
                },
            ),
            ReviewIssue(
                severity="suggestion",
                code="reader_pull",
                message=(
                    f"{last_path.name} ends near \"{_short_quote(evidence['reader_pull'])}\"; "
                    "make sure the remaining pressure is specific enough to pull the next chapter."
                ),
                location=last_path.stem,
                suggestion=(
                    f"Name the immediate cost or unanswered pressure at the end of {last_path.stem}."
                ),
                details={
                    "dimension": "reader pull",
                    "evidence": evidence["reader_pull"],
                },
            ),
            ReviewIssue(
                severity="suggestion",
                code="closure_spacing",
                message=(
                    "Recent endings show this cadence: "
                    f"\"{_short_quote(evidence['closure_spacing'], limit=120)}\"."
                ),
                location="manuscript",
                suggestion=(
                    "Vary whether chapters end on release, reversal, or delayed consequence."
                ),
                details={
                    "dimension": "closure spacing",
                    "short_chapters": short_chapters,
                    "evidence": evidence["closure_spacing"],
                },
            ),
            ReviewIssue(
                severity="suggestion",
                code="promise_trust",
                message=(
                    f"The sidecar promise \"{_short_quote(evidence['promise_trust'])}\" needs a visible prose echo."
                ),
                location="manuscript",
                suggestion=(
                    "Track open promises in action beats before introducing new obligations."
                ),
                details={
                    "dimension": "promise trust",
                    "open_promise_count": promise_count,
                    "evidence": evidence["promise_trust"],
                },
            ),
            ReviewIssue(
                severity="suggestion",
                code="voice_stability",
                message=(
                    f"The early voice sample \"{_short_quote(evidence['voice_stability'])}\" sets the diction baseline."
                ),
                location="manuscript",
                suggestion=(
                    "Use a voice pass to keep sentence rhythm intentional across dialogue and exposition."
                ),
                details={
                    "dimension": "voice stability",
                    "dialogue_marker_count": dialogue_markers,
                    "evidence": evidence["voice_stability"],
                },
            ),
        ]

    def _review_task(
        self,
        workspace: NovelWorkspace,
        chapters: list[Path],
        sidecars: dict[int, dict[str, Any]],
    ) -> TextGenerationTask:
        config = workspace.load_config()
        chapter_payload = []
        for path in chapters:
            text = path.read_text(encoding="utf-8").strip()
            chapter_payload.append(
                {
                    "filename": path.name,
                    "location": path.stem,
                    "word_count": len(text.split()),
                    "opening": _evidence_snippet(text, limit=260),
                    "middle": _evidence_window(text, 0.5, limit=260),
                    "ending": _evidence_snippet(text, from_end=True, limit=260),
                }
            )
        metadata = {
            "title": config.title,
            "genre": config.genre,
            "premise": config.premise,
            "dimensions": [
                {"code": code, "label": label} for code, label in EDITORIAL_DIMENSIONS
            ],
            "chapters": chapter_payload,
            "sidecars": sidecars,
        }
        return TextGenerationTask(
            step="editorial_review",
            system_prompt=(
                "You are an editorial reviewer for long-form fiction. Return JSON with "
                "a suggestions array. Keep blockers out of this response; only give "
                "non-blocking editorial advice grounded in manuscript evidence."
            ),
            user_prompt=json.dumps(metadata, ensure_ascii=False),
            response_schema={
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "message": {"type": "string"},
                            "location": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "evidence": {"type": "string"},
                        },
                    },
                }
            },
            temperature=0.25,
            metadata=metadata,
        )

    def _issues_from_provider(
        self,
        content: dict[str, Any],
        fallback: list[ReviewIssue],
    ) -> list[ReviewIssue]:
        raw_items = content.get("suggestions")
        if not isinstance(raw_items, list):
            raise ValueError("Provider editorial review did not return suggestions")
        raw_by_code: dict[str, dict[str, Any]] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            key = _normal_issue_code(item.get("code") or item.get("dimension"))
            if key:
                raw_by_code[key] = cast(dict[str, Any], item)
        issues: list[ReviewIssue] = []
        for fallback_issue in fallback:
            raw = raw_by_code.get(fallback_issue.code)
            if raw is None:
                issues.append(fallback_issue)
                continue
            details = dict(fallback_issue.details)
            raw_details = raw.get("details")
            if isinstance(raw_details, dict):
                details.update(raw_details)
            evidence = _clean_text(raw.get("evidence")) or _clean_text(
                details.get("evidence")
            )
            if evidence:
                details["evidence"] = evidence
            issues.append(
                ReviewIssue(
                    severity="suggestion",
                    code=fallback_issue.code,
                    message=_clean_text(raw.get("message")) or fallback_issue.message,
                    location=_clean_text(raw.get("location"))
                    or fallback_issue.location,
                    suggestion=_clean_text(raw.get("suggestion"))
                    or fallback_issue.suggestion,
                    details=details,
                )
            )
        return issues


class LocalReviewer:
    """Generic reviewer that separates hard blockers from editorial advice."""

    def __init__(self, editorial_provider: TextGenerationProvider | None = None) -> None:
        self._editorial_judge = EditorialJudge(editorial_provider)

    def review(self, workspace: NovelWorkspace) -> ReviewReport:
        """Review manuscript files without provider I/O."""
        with workspace.acquire_lock(operation="review"):
            report, chapters, sidecars = self._base_review_unlocked(workspace)
            if not report.blockers:
                report.suggestions.extend(
                    self._editorial_judge.deterministic_suggestions(chapters, sidecars)
                )
            self._finalize_report(workspace, report, chapters)
            return report

    def hard_check(self, workspace: NovelWorkspace, *, persist: bool = True) -> ReviewReport:
        """Run only deterministic export blockers and warnings."""
        with workspace.acquire_lock(operation="review"):
            report, chapters, _sidecars = self._base_review_unlocked(workspace)
            if persist:
                self._finalize_report(workspace, report, chapters)
            return report

    async def review_async(self, workspace: NovelWorkspace) -> ReviewReport:
        """Review manuscript files and use provider-backed editorial advice if configured."""
        with workspace.acquire_lock(operation="review"):
            report, chapters, sidecars = self._base_review_unlocked(workspace)
            if not report.blockers:
                report.suggestions.extend(
                    await self._editorial_judge.judge(workspace, chapters, sidecars)
                )
            self._finalize_report(workspace, report, chapters)
            return report

    def _base_review_unlocked(
        self,
        workspace: NovelWorkspace,
    ) -> tuple[ReviewReport, list[Path], dict[int, dict[str, Any]]]:
        config = workspace.load_config()
        chapters = workspace.list_chapters()
        sidecars = workspace.load_latest_sidecars()
        report = ReviewReport(story_title=config.title, checked_at=utcnow_iso())
        if not chapters:
            report.blockers.append(
                ReviewIssue(
                    severity="blocker",
                    code="missing_manuscript",
                    message="No chapter manuscripts exist.",
                    location="manuscript",
                    suggestion="Draft at least one complete chapter before export.",
                )
            )
            return report, chapters, sidecars

        expected = list(range(1, len(chapters) + 1))
        actual: list[int] = []
        for path in chapters:
            try:
                actual.append(int(path.stem.split("-")[-1]))
            except ValueError:
                report.warnings.append(
                    ReviewIssue(
                        severity="warning",
                        code="noncanonical_filename",
                        message=f"{path.name} is not a canonical chapter filename.",
                        location=path.name,
                        suggestion="Use chapter-001.md style filenames.",
                        details={"filename": path.name},
                    )
                )
        if actual and actual != expected:
            report.blockers.append(
                ReviewIssue(
                    severity="blocker",
                    code="chapter_sequence_gap",
                    message=f"Chapter sequence is {actual}, expected {expected}.",
                    location="manuscript",
                    suggestion="Rename or add chapters so numbering is contiguous.",
                    details={"actual": actual, "expected": expected},
                )
            )

        for path in chapters:
            text = path.read_text(encoding="utf-8").strip()
            location = path.stem
            word_count = len(text.split())
            if not text:
                report.blockers.append(
                    ReviewIssue(
                        severity="blocker",
                        code="empty_chapter",
                        message=f"{path.name} is empty.",
                        location=location,
                        suggestion="Regenerate or rewrite the chapter.",
                        details={"filename": path.name},
                    )
                )
                continue
            if word_count < 120:
                report.warnings.append(
                    ReviewIssue(
                        severity="warning",
                        code="thin_chapter",
                        message=f"{path.name} is only {word_count} words.",
                        location=location,
                        suggestion=(
                            "Consider expanding the chapter, but this does not block export."
                        ),
                        details={"word_count": word_count, "filename": path.name},
                    )
                )
            for phrase in FORBIDDEN_TEMPLATE_PHRASES:
                if phrase.lower() in text.lower():
                    report.blockers.append(
                        ReviewIssue(
                            severity="blocker",
                            code="mechanical_repair_language",
                            message=f"{path.name} contains mechanical repair text.",
                            location=location,
                            suggestion="Rewrite the affected passage as natural prose.",
                            details={"phrase": phrase, "filename": path.name},
                        )
                    )
        return report, chapters, sidecars

    def _finalize_report(
        self,
        workspace: NovelWorkspace,
        report: ReviewReport,
        chapters: list[Path],
    ) -> None:
        report.style_notes.extend(self._style_notes(chapters))
        workspace.store_review(report)

    def _style_notes(self, chapters: list[Path]) -> list[str]:
        notes: list[str] = []
        if chapters:
            notes.append("Markdown chapters are the manuscript authority.")
        return notes


class LocalExporter:
    """Export local manuscript chapters."""

    def export_markdown(self, workspace: NovelWorkspace, output: Path | None = None) -> Path:
        """Export the manuscript to one Markdown file if no blockers exist."""
        with workspace.acquire_lock(operation="export"):
            existing_review = workspace.latest_review()
            report = LocalReviewer().hard_check(workspace, persist=False)
            if report.export_blocked:
                workspace.store_review(report)
                blocker_codes = ", ".join(issue.code for issue in report.blockers)
                raise ValueError(f"Export blocked by review blockers: {blocker_codes}")
            if existing_review is None or existing_review.export_blocked:
                workspace.store_review(report)
            config = workspace.load_config()
            output_path = output or workspace.exports_dir / "manuscript.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            parts = [f"# {config.title}", ""]
            for chapter in workspace.list_chapters():
                parts.append(chapter.read_text(encoding="utf-8").strip())
                parts.append("")
            _atomic_write_text(output_path, "\n".join(parts).rstrip() + "\n")
            return output_path


def _summarize(markdown: str, limit: int = 240) -> str:
    cleaned = " ".join(line.strip("# ").strip() for line in markdown.splitlines())
    cleaned = " ".join(cleaned.split())
    return cleaned[:limit]


def _evidence_snippet(text: str, *, from_end: bool = False, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    if from_end:
        return cleaned[-limit:].lstrip()
    return cleaned[:limit].rstrip()


def _evidence_window(text: str, position: float, *, limit: int = 220) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    start = max(0, min(len(cleaned) - limit, int(len(cleaned) * position) - limit // 2))
    return cleaned[start : start + limit].strip()


def _short_quote(text: str, *, limit: int = 88) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _promise_texts(sidecars: dict[int, dict[str, Any]]) -> list[str]:
    promises: list[str] = []
    for sidecar in sidecars.values():
        items = sidecar.get("promises", [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
            else:
                text = str(item).strip()
            if text:
                promises.append(text)
    return promises


def _clean_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _normal_issue_code(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _clean_text(value).lower()).strip("_")


def _unresolved_promises(
    sidecars: dict[int, dict[str, Any]],
    chapter_number: int,
) -> list[str]:
    promises: list[str] = []
    for number, sidecar in sorted(sidecars.items()):
        if number >= chapter_number:
            continue
        raw_promises = sidecar.get("promises", [])
        if not isinstance(raw_promises, list):
            continue
        for promise in raw_promises:
            if isinstance(promise, dict):
                status = str(promise.get("status", "open")).lower()
                text = str(promise.get("text", "")).strip()
                if text and status not in {"resolved", "paid_off", "closed"}:
                    promises.append(text)
            elif str(promise).strip():
                promises.append(str(promise).strip())
    return promises[-8:]


def _character_state(
    sidecars: dict[int, dict[str, Any]],
    chapter_number: int,
) -> list[str]:
    states: list[str] = []
    for number, sidecar in sorted(sidecars.items()):
        if number >= chapter_number:
            continue
        characters = sidecar.get("characters", [])
        if isinstance(characters, list) and characters:
            states.append(f"Chapter {number}: {', '.join(str(item) for item in characters)}")
    return states[-5:]


__all__ = [
    "ChapterDraftArtifact",
    "DraftChapterTask",
    "FORBIDDEN_TEMPLATE_PHRASES",
    "LocalDraftingEngine",
    "LocalExporter",
    "LocalReviewer",
    "NovelWorkspace",
    "ReviewIssue",
    "ReviewReport",
    "ReviewSeverity",
    "StoryConfig",
    "chapter_filename",
    "utcnow_iso",
]
