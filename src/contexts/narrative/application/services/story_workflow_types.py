"""Typed workflow artifacts, memory, and run state for story generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast
from uuid import uuid4

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderName,
)

ReviewSeverity = Literal["info", "warning", "blocker"]
StageExecutionStatus = Literal["running", "completed", "failed"]
GenerationRunStatus = Literal["running", "completed", "failed"]
GenerationRunMode = Literal["manual", "pipeline"]
ArtifactKind = Literal[
    "blueprint",
    "outline",
    "review",
    "semantic_review",
    "hybrid_review",
    "draft_failure",
    "export",
]
NarrativeStrand = Literal["quest", "fire", "constellation"]
RunEventType = Literal[
    "run_started",
    "stage_started",
    "stage_completed",
    "stage_failed",
    "run_completed",
    "run_failed",
]
RunSnapshotType = Literal[
    "run_started",
    "stage_completed",
    "run_completed",
    "run_failed",
]


def utcnow_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item).strip() for item in _list(value) if str(item).strip()]


@dataclass(slots=True)
class GenerationTraceEntry:
    """A single structured generation trace entry."""

    timestamp: str
    step: str
    provider: TextGenerationProviderName
    model: str
    content_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "step": self.step,
            "provider": self.provider,
            "model": self.model,
            "content_keys": self.content_keys,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> GenerationTraceEntry:
        data = _dict(payload)
        provider = str(data.get("provider", "mock"))
        if provider not in {"mock", "dashscope", "openai_compatible"}:
            provider = "mock"
        return cls(
            timestamp=str(data.get("timestamp", utcnow_iso())),
            step=str(data.get("step", "")),
            provider=cast(TextGenerationProviderName, provider),
            model=str(data.get("model", "")),
            content_keys=sorted(_strings(data.get("content_keys"))),
        )


@dataclass(slots=True)
class StageExecution:
    """A single stage execution within a generation run."""

    name: str
    status: StageExecutionStatus
    started_at: str
    completed_at: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StageExecution:
        data = _dict(payload)
        status = str(data.get("status", "completed"))
        if status not in {"running", "completed", "failed"}:
            status = "completed"
        return cls(
            name=str(data.get("name", "")),
            status=cast(StageExecutionStatus, status),
            started_at=str(data.get("started_at", utcnow_iso())),
            completed_at=(
                str(data.get("completed_at"))
                if data.get("completed_at") is not None
                else None
            ),
            failure_code=(
                str(data.get("failure_code"))
                if data.get("failure_code") is not None
                else None
            ),
            failure_message=(
                str(data.get("failure_message"))
                if data.get("failure_message") is not None
                else None
            ),
            details=_dict(data.get("details")),
        )


@dataclass(slots=True)
class GenerationRun:
    """The latest generation run state for a story."""

    run_id: str
    mode: GenerationRunMode
    status: GenerationRunStatus
    started_at: str
    completed_at: str | None = None
    published: bool = False
    stages: list[StageExecution] = field(default_factory=list)

    @classmethod
    def start(cls, mode: GenerationRunMode) -> GenerationRun:
        return cls(
            run_id=str(uuid4()),
            mode=mode,
            status="running",
            started_at=utcnow_iso(),
        )

    def mark_stage_started(
        self,
        stage_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.stages.append(
            StageExecution(
                name=stage_name,
                status="running",
                started_at=utcnow_iso(),
                details=details or {},
            )
        )

    def mark_stage_completed(
        self,
        stage_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        stage = self._latest_stage(stage_name)
        if stage is None:
            self.mark_stage_started(stage_name, details)
            stage = self._latest_stage(stage_name)
            if stage is None:
                return
        stage.status = "completed"
        stage.completed_at = utcnow_iso()
        if details:
            stage.details.update(details)

    def mark_stage_failed(
        self,
        stage_name: str,
        failure_code: str,
        failure_message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        stage = self._latest_stage(stage_name)
        if stage is None:
            self.mark_stage_started(stage_name, details)
            stage = self._latest_stage(stage_name)
            if stage is None:
                return
        stage.status = "failed"
        stage.completed_at = utcnow_iso()
        stage.failure_code = failure_code
        stage.failure_message = failure_message
        if details:
            stage.details.update(details)
        self.status = "failed"
        self.completed_at = utcnow_iso()

    def mark_completed(self, published: bool = False) -> None:
        self.status = "completed"
        self.completed_at = utcnow_iso()
        self.published = published

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "published": self.published,
            "stages": [stage.to_dict() for stage in self.stages],
        }

    @classmethod
    def from_dict(cls, payload: Any) -> GenerationRun | None:
        data = _dict(payload)
        if not data:
            return None
        mode = str(data.get("mode", "manual"))
        if mode not in {"manual", "pipeline"}:
            mode = "manual"
        status = str(data.get("status", "completed"))
        if status not in {"running", "completed", "failed"}:
            status = "completed"
        return cls(
            run_id=str(data.get("run_id", str(uuid4()))),
            mode=cast(GenerationRunMode, mode),
            status=cast(GenerationRunStatus, status),
            started_at=str(data.get("started_at", utcnow_iso())),
            completed_at=(
                str(data.get("completed_at"))
                if data.get("completed_at") is not None
                else None
            ),
            published=bool(data.get("published", False)),
            stages=[
                StageExecution.from_dict(item) for item in _list(data.get("stages"))
            ],
        )

    def _latest_stage(self, stage_name: str) -> StageExecution | None:
        for stage in reversed(self.stages):
            if stage.name == stage_name:
                return stage
        return None


@dataclass(slots=True)
class RunEvent:
    """Append-only run event used by future incremental run feeds."""

    event_id: str
    run_id: str
    event_type: RunEventType
    timestamp: str
    stage_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "stage_name": self.stage_name,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> RunEvent:
        data = _dict(payload)
        event_type = str(data.get("event_type", "stage_completed"))
        if event_type not in {
            "run_started",
            "stage_started",
            "stage_completed",
            "stage_failed",
            "run_completed",
            "run_failed",
        }:
            event_type = "stage_completed"
        return cls(
            event_id=str(data.get("event_id", str(uuid4()))),
            run_id=str(data.get("run_id", "")),
            event_type=cast(RunEventType, event_type),
            timestamp=str(data.get("timestamp", utcnow_iso())),
            stage_name=(
                str(data.get("stage_name"))
                if data.get("stage_name") is not None
                else None
            ),
            details=_dict(data.get("details")),
        )


@dataclass(slots=True)
class ArtifactHistoryEntry:
    """Append-only artifact history entry for workspace projections."""

    artifact_id: str
    kind: ArtifactKind
    version: int
    generated_at: str
    source_run_id: str | None
    source_stage: str
    source_provider: str
    source_model: str
    parent_artifact_ids: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "version": self.version,
            "generated_at": self.generated_at,
            "source_run_id": self.source_run_id,
            "source_stage": self.source_stage,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "parent_artifact_ids": self.parent_artifact_ids,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> ArtifactHistoryEntry:
        data = _dict(payload)
        kind = str(data.get("kind", "blueprint"))
        if kind not in {"blueprint", "outline", "review", "semantic_review", "hybrid_review", "draft_failure", "export"}:
            kind = "blueprint"
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            kind=cast(ArtifactKind, kind),
            version=int(data.get("version", 1)),
            generated_at=str(data.get("generated_at", utcnow_iso())),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_stage=str(data.get("source_stage", kind)),
            source_provider=str(data.get("source_provider", "system")),
            source_model=str(data.get("source_model", "")),
            parent_artifact_ids=_strings(data.get("parent_artifact_ids")),
            payload=_dict(data.get("payload")),
        )


@dataclass(slots=True)
class RunSnapshot:
    """Immutable workspace snapshot captured during a generation run."""

    snapshot_id: str
    story_id: str
    run_id: str
    snapshot_type: RunSnapshotType
    captured_at: str
    workspace: dict[str, Any]
    stage_name: str | None = None
    failed_stage: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "story_id": self.story_id,
            "run_id": self.run_id,
            "snapshot_type": self.snapshot_type,
            "captured_at": self.captured_at,
            "stage_name": self.stage_name,
            "failed_stage": self.failed_stage,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "failure_details": deepcopy(self.failure_details),
            "workspace": deepcopy(self.workspace),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> RunSnapshot:
        data = _dict(payload)
        snapshot_type = str(data.get("snapshot_type", "stage_completed"))
        if snapshot_type not in {
            "run_started",
            "stage_completed",
            "run_completed",
            "run_failed",
        }:
            snapshot_type = "stage_completed"
        return cls(
            snapshot_id=str(data.get("snapshot_id", str(uuid4()))),
            story_id=str(data.get("story_id", "")),
            run_id=str(data.get("run_id", "")),
            snapshot_type=cast(RunSnapshotType, snapshot_type),
            captured_at=str(data.get("captured_at", utcnow_iso())),
            stage_name=(
                str(data.get("stage_name"))
                if data.get("stage_name") is not None
                else None
            ),
            failed_stage=(
                str(data.get("failed_stage"))
                if data.get("failed_stage") is not None
                else None
            ),
            failure_code=(
                str(data.get("failure_code"))
                if data.get("failure_code") is not None
                else None
            ),
            failure_message=(
                str(data.get("failure_message"))
                if data.get("failure_message") is not None
                else None
            ),
            failure_details=_dict(data.get("failure_details")),
            workspace=deepcopy(_dict(data.get("workspace"))),
        )


@dataclass(slots=True)
class DraftFailureArtifact:
    """Typed artifact capturing a failed draft attempt for debugging."""

    story_id: str
    stage_name: str
    chapter_number: int
    failure_code: str
    failure_message: str
    raw_text: str
    raw_payload: dict[str, Any]
    normalized_payload: dict[str, Any]
    validation_errors: list[str]
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    generated_at: str = field(default_factory=utcnow_iso)
    source_run_id: str | None = None
    source_provider: TextGenerationProviderName = "mock"
    source_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "generated_at": self.generated_at,
            "source_run_id": self.source_run_id,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "story_id": self.story_id,
            "stage_name": self.stage_name,
            "chapter_number": self.chapter_number,
            "failure_code": self.failure_code,
            "failure_message": self.failure_message,
            "raw_text": self.raw_text,
            "raw_payload": deepcopy(self.raw_payload),
            "normalized_payload": deepcopy(self.normalized_payload),
            "validation_errors": list(self.validation_errors),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> DraftFailureArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        provider = str(data.get("source_provider", "mock"))
        if provider not in {"mock", "dashscope", "openai_compatible"}:
            provider = "mock"
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            version=int(data.get("version", 1)),
            generated_at=str(data.get("generated_at", utcnow_iso())),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_provider=cast(TextGenerationProviderName, provider),
            source_model=str(data.get("source_model", "")),
            story_id=str(data.get("story_id", "")),
            stage_name=str(data.get("stage_name", "draft")),
            chapter_number=int(data.get("chapter_number", 0)),
            failure_code=str(data.get("failure_code", "DRAFT_VALIDATION_ERROR")),
            failure_message=str(data.get("failure_message", "")),
            raw_text=str(data.get("raw_text", "")),
            raw_payload=_dict(data.get("raw_payload")),
            normalized_payload=_dict(data.get("normalized_payload")),
            validation_errors=_strings(data.get("validation_errors")),
        )


@dataclass(slots=True)
class GenerationRunResourceState:
    """Independent append-only run resource state for a story."""

    story_id: str
    runs: list[GenerationRun] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)
    snapshots: list[RunSnapshot] = field(default_factory=list)
    updated_at: str = field(default_factory=utcnow_iso)

    @classmethod
    def empty(cls, story_id: str) -> GenerationRunResourceState:
        return cls(story_id=story_id)

    @classmethod
    def from_legacy_generation_state(
        cls,
        payload: StoryGenerationState | None,
    ) -> GenerationRunResourceState | None:
        if payload is None:
            return None
        if not payload.run_history and not payload.run_events:
            return None
        return cls(
            story_id=payload.story_id,
            runs=list(payload.run_history),
            events=list(payload.run_events),
            snapshots=[],
            updated_at=payload.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "runs": [run.to_dict() for run in self.runs],
            "events": [event.to_dict() for event in self.events],
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> GenerationRunResourceState | None:
        data = _dict(payload)
        if not data:
            return None
        runs: list[GenerationRun] = []
        for item in _list(data.get("runs")):
            run = GenerationRun.from_dict(item)
            if run is not None:
                runs.append(run)
        return cls(
            story_id=str(data.get("story_id", "")),
            runs=runs,
            events=[
                RunEvent.from_dict(item)
                for item in _list(data.get("events"))
                if isinstance(item, dict)
            ],
            snapshots=[
                RunSnapshot.from_dict(item)
                for item in _list(data.get("snapshots"))
                if isinstance(item, dict)
            ],
            updated_at=str(data.get("updated_at", utcnow_iso())),
        )


@dataclass(slots=True)
class StoryArtifactResourceState:
    """Independent append-only artifact resource state for a story."""

    story_id: str
    artifacts: list[ArtifactHistoryEntry] = field(default_factory=list)
    updated_at: str = field(default_factory=utcnow_iso)

    @classmethod
    def empty(cls, story_id: str) -> StoryArtifactResourceState:
        return cls(story_id=story_id)

    @classmethod
    def from_legacy_generation_state(
        cls,
        payload: StoryGenerationState | None,
    ) -> StoryArtifactResourceState | None:
        if payload is None or not payload.artifact_history:
            return None
        return cls(
            story_id=payload.story_id,
            artifacts=list(payload.artifact_history),
            updated_at=payload.updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryArtifactResourceState | None:
        data = _dict(payload)
        if not data:
            return None
        return cls(
            story_id=str(data.get("story_id", "")),
            artifacts=[
                ArtifactHistoryEntry.from_dict(item)
                for item in _list(data.get("artifacts"))
                if isinstance(item, dict)
            ],
            updated_at=str(data.get("updated_at", utcnow_iso())),
        )


@dataclass(slots=True)
class StoryGenerationState:
    """Independent generation-state snapshot for a story."""

    story_id: str
    current_run_id: str | None = None
    run_history: list[GenerationRun] = field(default_factory=list)
    run_events: list[RunEvent] = field(default_factory=list)
    artifact_history: list[ArtifactHistoryEntry] = field(default_factory=list)
    updated_at: str = field(default_factory=utcnow_iso)

    @classmethod
    def empty(cls, story_id: str) -> StoryGenerationState:
        return cls(story_id=story_id)

    @classmethod
    def from_legacy_metadata(
        cls,
        story_id: str,
        payload: Any,
    ) -> StoryGenerationState | None:
        data = _dict(payload)
        run_history: list[GenerationRun] = []
        for item in _list(data.get("run_history")):
            run = GenerationRun.from_dict(item)
            if run is not None:
                run_history.append(run)

        run_events = [
            RunEvent.from_dict(item)
            for item in _list(data.get("run_events"))
            if isinstance(item, dict)
        ]
        artifact_history = [
            ArtifactHistoryEntry.from_dict(item)
            for item in _list(data.get("artifact_history"))
            if isinstance(item, dict)
        ]
        current_run_id = (
            str(data.get("current_run_id"))
            if data.get("current_run_id") is not None
            else None
        )

        if current_run_id is None and not run_history and not run_events and not artifact_history:
            return None

        return cls(
            story_id=story_id,
            current_run_id=current_run_id,
            run_history=run_history,
            run_events=run_events,
            artifact_history=artifact_history,
            updated_at=str(data.get("updated_at", utcnow_iso())),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "current_run_id": self.current_run_id,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryGenerationState | None:
        data = _dict(payload)
        if not data:
            return None
        run_history: list[GenerationRun] = []
        for item in _list(data.get("run_history")):
            run = GenerationRun.from_dict(item)
            if run is not None:
                run_history.append(run)
        return cls(
            story_id=str(data.get("story_id", "")),
            current_run_id=(
                str(data.get("current_run_id"))
                if data.get("current_run_id") is not None
                else None
            ),
            run_history=run_history,
            run_events=[
                RunEvent.from_dict(item)
                for item in _list(data.get("run_events"))
                if isinstance(item, dict)
            ],
            artifact_history=[
                ArtifactHistoryEntry.from_dict(item)
                for item in _list(data.get("artifact_history"))
                if isinstance(item, dict)
            ],
            updated_at=str(data.get("updated_at", utcnow_iso())),
        )


@dataclass(slots=True)
class StoryOutlineChapter:
    """A normalized outline chapter entry."""

    chapter_number: int
    title: str
    summary: str
    hook: str
    promise: str = ""
    pacing_phase: str = ""
    narrative_strand: str = ""
    chapter_objective: str = ""
    primary_strand: str = ""
    secondary_strand: str | None = None
    promised_payoff: str = ""
    hook_strength: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "summary": self.summary,
            "hook": self.hook,
            "promise": self.promise,
            "pacing_phase": self.pacing_phase,
            "narrative_strand": self.narrative_strand,
            "chapter_objective": self.chapter_objective,
            "primary_strand": self.primary_strand,
            "secondary_strand": self.secondary_strand,
            "promised_payoff": self.promised_payoff,
            "hook_strength": self.hook_strength,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryOutlineChapter:
        data = _dict(payload)
        primary_strand = str(
            data.get("primary_strand", data.get("narrative_strand", ""))
        ).strip()
        promise = str(data.get("promise", data.get("promised_payoff", ""))).strip()
        return cls(
            chapter_number=int(data.get("chapter_number", 1)),
            title=str(data.get("title", "")).strip(),
            summary=str(data.get("summary", "")).strip(),
            hook=str(data.get("hook", "")).strip(),
            promise=promise,
            pacing_phase=str(data.get("pacing_phase", "")).strip(),
            narrative_strand=primary_strand,
            chapter_objective=str(data.get("chapter_objective", "")).strip(),
            primary_strand=primary_strand,
            secondary_strand=(
                str(data.get("secondary_strand")).strip()
                if data.get("secondary_strand") is not None
                else None
            ),
            promised_payoff=str(data.get("promised_payoff", promise)).strip(),
            hook_strength=int(data.get("hook_strength", 0)),
        )


@dataclass(slots=True)
class StoryBlueprintArtifact:
    """Typed world and character bible artifact."""

    step: str
    provider: TextGenerationProviderName
    model: str
    generated_at: str
    story_id: str
    version: int
    world_bible: dict[str, Any]
    character_bible: dict[str, Any]
    premise_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at,
            "story_id": self.story_id,
            "version": self.version,
            "world_bible": self.world_bible,
            "character_bible": self.character_bible,
            "premise_summary": self.premise_summary,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryBlueprintArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        provider = str(data.get("provider", "mock"))
        if provider not in {"mock", "dashscope", "openai_compatible"}:
            provider = "mock"
        return cls(
            step=str(data.get("step", "bible")),
            provider=cast(TextGenerationProviderName, provider),
            model=str(data.get("model", "")),
            generated_at=str(data.get("generated_at", utcnow_iso())),
            story_id=str(data.get("story_id", "")),
            version=int(data.get("version", 1)),
            world_bible=_dict(data.get("world_bible")),
            character_bible=_dict(data.get("character_bible")),
            premise_summary=str(data.get("premise_summary", "")).strip(),
        )


@dataclass(slots=True)
class StoryOutlineArtifact:
    """Typed outline artifact."""

    step: str
    provider: TextGenerationProviderName
    model: str
    generated_at: str
    target_chapters: int
    version: int
    chapters: list[StoryOutlineChapter] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "provider": self.provider,
            "model": self.model,
            "generated_at": self.generated_at,
            "target_chapters": self.target_chapters,
            "version": self.version,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryOutlineArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        provider = str(data.get("provider", "mock"))
        if provider not in {"mock", "dashscope", "openai_compatible"}:
            provider = "mock"
        return cls(
            step=str(data.get("step", "outline")),
            provider=cast(TextGenerationProviderName, provider),
            model=str(data.get("model", "")),
            generated_at=str(data.get("generated_at", utcnow_iso())),
            target_chapters=int(data.get("target_chapters", 0)),
            version=int(data.get("version", 1)),
            chapters=[
                StoryOutlineChapter.from_dict(item)
                for item in _list(data.get("chapters"))
            ],
        )


@dataclass(slots=True)
class StoryReviewIssue:
    """A single quality gate issue."""

    code: str
    severity: ReviewSeverity
    message: str
    location: str | None = None
    suggestion: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryReviewIssue:
        data = _dict(payload)
        severity = str(data.get("severity", "warning"))
        if severity not in {"info", "warning", "blocker"}:
            severity = "warning"
        return cls(
            code=str(data.get("code", "unknown")),
            severity=cast(ReviewSeverity, severity),
            message=str(data.get("message", "")),
            location=(
                str(data.get("location"))
                if data.get("location") is not None
                else None
            ),
            suggestion=(
                str(data.get("suggestion"))
                if data.get("suggestion") is not None
                else None
            ),
            details=_dict(data.get("details")),
        )


@dataclass(slots=True)
class StoryReviewMetrics:
    """Structured review metrics for continuity and pacing."""

    continuity_score: int
    pacing_score: int
    hook_score: int
    character_consistency_score: int
    timeline_consistency_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "continuity_score": self.continuity_score,
            "pacing_score": self.pacing_score,
            "hook_score": self.hook_score,
            "character_consistency_score": self.character_consistency_score,
            "timeline_consistency_score": self.timeline_consistency_score,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryReviewMetrics:
        data = _dict(payload)
        return cls(
            continuity_score=int(data.get("continuity_score", 0)),
            pacing_score=int(data.get("pacing_score", 0)),
            hook_score=int(data.get("hook_score", 0)),
            character_consistency_score=int(
                data.get("character_consistency_score", 0)
            ),
            timeline_consistency_score=int(
                data.get("timeline_consistency_score", 0)
            ),
        )


@dataclass(slots=True)
class StoryReviewArtifact:
    """Typed review artifact."""

    story_id: str
    quality_score: int
    ready_for_publish: bool
    summary: str
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    source_run_id: str | None = None
    source_provider: str = "system"
    source_model: str = "rule-review-v1"
    issues: list[StoryReviewIssue] = field(default_factory=list)
    revision_notes: list[str] = field(default_factory=list)
    chapter_count: int = 0
    scene_count: int = 0
    continuity_checks: dict[str, bool] = field(default_factory=dict)
    checked_at: str = field(default_factory=utcnow_iso)
    metrics: StoryReviewMetrics = field(
        default_factory=lambda: StoryReviewMetrics(0, 0, 0, 0, 0)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "source_run_id": self.source_run_id,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "story_id": self.story_id,
            "quality_score": self.quality_score,
            "ready_for_publish": self.ready_for_publish,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "revision_notes": self.revision_notes,
            "chapter_count": self.chapter_count,
            "scene_count": self.scene_count,
            "continuity_checks": self.continuity_checks,
            "checked_at": self.checked_at,
            "metrics": self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryReviewArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            version=int(data.get("version", 1)),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_provider=str(data.get("source_provider", "system")),
            source_model=str(data.get("source_model", "rule-review-v1")),
            story_id=str(data.get("story_id", "")),
            quality_score=int(data.get("quality_score", 0)),
            ready_for_publish=bool(data.get("ready_for_publish", False)),
            summary=str(data.get("summary", "")),
            issues=[StoryReviewIssue.from_dict(item) for item in _list(data.get("issues"))],
            revision_notes=_strings(data.get("revision_notes")),
            chapter_count=int(data.get("chapter_count", 0)),
            scene_count=int(data.get("scene_count", 0)),
            continuity_checks={
                str(key): bool(value)
                for key, value in _dict(data.get("continuity_checks")).items()
            },
            checked_at=str(data.get("checked_at", utcnow_iso())),
            metrics=StoryReviewMetrics.from_dict(data.get("metrics")),
        )


@dataclass(slots=True)
class SemanticReviewMetrics:
    """Structured semantic review metrics for reader pull and clarity."""

    semantic_score: int
    reader_pull_score: int
    plot_clarity_score: int
    ooc_risk_score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_score": self.semantic_score,
            "reader_pull_score": self.reader_pull_score,
            "plot_clarity_score": self.plot_clarity_score,
            "ooc_risk_score": self.ooc_risk_score,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> SemanticReviewMetrics:
        data = _dict(payload)
        return cls(
            semantic_score=int(data.get("semantic_score", 0)),
            reader_pull_score=int(data.get("reader_pull_score", 0)),
            plot_clarity_score=int(data.get("plot_clarity_score", 0)),
            ooc_risk_score=int(data.get("ooc_risk_score", 0)),
        )


@dataclass(slots=True)
class SemanticReviewArtifact:
    """Provider-backed semantic review artifact."""

    story_id: str
    semantic_score: int
    ready_for_publish: bool
    summary: str
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    source_run_id: str | None = None
    source_provider: TextGenerationProviderName = "mock"
    source_model: str = ""
    issues: list[StoryReviewIssue] = field(default_factory=list)
    repair_suggestions: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=utcnow_iso)
    metrics: SemanticReviewMetrics = field(
        default_factory=lambda: SemanticReviewMetrics(0, 0, 0, 0)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "source_run_id": self.source_run_id,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "story_id": self.story_id,
            "semantic_score": self.semantic_score,
            "ready_for_publish": self.ready_for_publish,
            "summary": self.summary,
            "issues": [issue.to_dict() for issue in self.issues],
            "repair_suggestions": self.repair_suggestions,
            "checked_at": self.checked_at,
            "metrics": self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> SemanticReviewArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        provider = str(data.get("source_provider", "mock"))
        if provider not in {"mock", "dashscope", "openai_compatible"}:
            provider = "mock"
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            version=int(data.get("version", 1)),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_provider=cast(TextGenerationProviderName, provider),
            source_model=str(data.get("source_model", "")),
            story_id=str(data.get("story_id", "")),
            semantic_score=int(data.get("semantic_score", 0)),
            ready_for_publish=bool(data.get("ready_for_publish", False)),
            summary=str(data.get("summary", "")),
            issues=[StoryReviewIssue.from_dict(item) for item in _list(data.get("issues"))],
            repair_suggestions=_strings(data.get("repair_suggestions")),
            checked_at=str(data.get("checked_at", utcnow_iso())),
            metrics=SemanticReviewMetrics.from_dict(data.get("metrics")),
        )


@dataclass(slots=True)
class HybridReviewReport:
    """Merged structural and semantic review used by publication gates."""

    story_id: str
    quality_score: int
    ready_for_publish: bool
    summary: str
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    source_run_id: str | None = None
    source_provider: str = "system"
    source_model: str = "hybrid-review-v1"
    structural_review: StoryReviewArtifact | None = None
    semantic_review: SemanticReviewArtifact | None = None
    issues: list[StoryReviewIssue] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)
    structural_gate_passed: bool = False
    semantic_gate_passed: bool = False
    publish_gate_passed: bool = False
    checked_at: str = field(default_factory=utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "source_run_id": self.source_run_id,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "story_id": self.story_id,
            "quality_score": self.quality_score,
            "ready_for_publish": self.ready_for_publish,
            "summary": self.summary,
            "structural_review": (
                self.structural_review.to_dict() if self.structural_review else None
            ),
            "semantic_review": (
                self.semantic_review.to_dict() if self.semantic_review else None
            ),
            "issues": [issue.to_dict() for issue in self.issues],
            "blocked_by": self.blocked_by,
            "structural_gate_passed": self.structural_gate_passed,
            "semantic_gate_passed": self.semantic_gate_passed,
            "publish_gate_passed": self.publish_gate_passed,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> HybridReviewReport | None:
        data = _dict(payload)
        if not data:
            return None
        structural_review = StoryReviewArtifact.from_dict(data.get("structural_review"))
        if structural_review is None and "metrics" in data:
            structural_review = StoryReviewArtifact.from_dict(data)
        semantic_review = SemanticReviewArtifact.from_dict(data.get("semantic_review"))
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            version=int(data.get("version", 1)),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_provider=str(data.get("source_provider", "system")),
            source_model=str(data.get("source_model", "hybrid-review-v1")),
            story_id=str(data.get("story_id", "")),
            quality_score=int(data.get("quality_score", 0)),
            ready_for_publish=bool(data.get("ready_for_publish", False)),
            summary=str(data.get("summary", "")),
            structural_review=structural_review,
            semantic_review=semantic_review,
            issues=[StoryReviewIssue.from_dict(item) for item in _list(data.get("issues"))],
            blocked_by=_strings(data.get("blocked_by")),
            structural_gate_passed=bool(
                data.get(
                    "structural_gate_passed",
                    structural_review.ready_for_publish if structural_review else False,
                )
            ),
            semantic_gate_passed=bool(
                data.get(
                    "semantic_gate_passed",
                    semantic_review.ready_for_publish if semantic_review else False,
                )
            ),
            publish_gate_passed=bool(
                data.get(
                    "publish_gate_passed",
                    bool(data.get("ready_for_publish", False)),
                )
            ),
            checked_at=str(data.get("checked_at", utcnow_iso())),
        )


@dataclass(slots=True)
class StoryChapterMemorySummary:
    """Compact memory entry per chapter."""

    chapter_number: int
    title: str
    summary: str
    focus_character: str
    focus_motivation: str
    hook: str
    promise: str = ""
    pacing_phase: str = ""
    narrative_strand: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "summary": self.summary,
            "focus_character": self.focus_character,
            "focus_motivation": self.focus_motivation,
            "hook": self.hook,
            "promise": self.promise,
            "pacing_phase": self.pacing_phase,
            "narrative_strand": self.narrative_strand,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryChapterMemorySummary:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            focus_character=str(data.get("focus_character", "")),
            focus_motivation=str(data.get("focus_motivation", "")),
            hook=str(data.get("hook", "")),
            promise=str(data.get("promise", "")).strip(),
            pacing_phase=str(data.get("pacing_phase", "")).strip(),
            narrative_strand=str(data.get("narrative_strand", "")).strip(),
        )


@dataclass(slots=True)
class TimelineLedgerEntry:
    """Timeline memory for a chapter."""

    chapter_number: int
    timeline_day: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "timeline_day": self.timeline_day,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> TimelineLedgerEntry:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            timeline_day=int(data.get("timeline_day", 0)),
            summary=str(data.get("summary", "")),
        )


@dataclass(slots=True)
class HookLedgerEntry:
    """Hook memory for a chapter."""

    chapter_number: int
    hook: str
    surfaced: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "hook": self.hook,
            "surfaced": self.surfaced,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> HookLedgerEntry:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            hook=str(data.get("hook", "")),
            surfaced=bool(data.get("surfaced", False)),
        )


@dataclass(slots=True)
class PromiseLedgerEntry:
    """Promise and payoff tracking for chapter-level serial momentum."""

    chapter_number: int
    promise: str
    surfaced: bool
    promise_id: str = field(default_factory=lambda: str(uuid4()))
    strand: str = ""
    chapter_objective: str = ""
    payoff_chapter: int | None = None
    due_by_chapter: int | None = None
    status: str = "open"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "promise": self.promise,
            "surfaced": self.surfaced,
            "promise_id": self.promise_id,
            "strand": self.strand,
            "chapter_objective": self.chapter_objective,
            "payoff_chapter": self.payoff_chapter,
            "due_by_chapter": self.due_by_chapter,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> PromiseLedgerEntry:
        data = _dict(payload)
        payoff_chapter = data.get("payoff_chapter")
        due_by_chapter = data.get("due_by_chapter")
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            promise=str(data.get("promise", "")),
            surfaced=bool(data.get("surfaced", False)),
            promise_id=str(data.get("promise_id", str(uuid4()))),
            strand=str(data.get("strand", "")),
            chapter_objective=str(data.get("chapter_objective", "")),
            payoff_chapter=int(payoff_chapter) if payoff_chapter is not None else None,
            due_by_chapter=int(due_by_chapter) if due_by_chapter is not None else None,
            status=str(data.get("status", "open")),
        )


@dataclass(slots=True)
class PacingLedgerEntry:
    """Per-chapter pacing signature for hybrid review."""

    chapter_number: int
    phase: str
    signature: str
    tension: int
    hook_strength: int = 0
    chapter_objective: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "phase": self.phase,
            "signature": self.signature,
            "tension": self.tension,
            "hook_strength": self.hook_strength,
            "chapter_objective": self.chapter_objective,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> PacingLedgerEntry:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            phase=str(data.get("phase", "")),
            signature=str(data.get("signature", "")),
            tension=int(data.get("tension", 0)),
            hook_strength=int(data.get("hook_strength", 0)),
            chapter_objective=str(data.get("chapter_objective", "")),
        )


@dataclass(slots=True)
class StoryPromise:
    """Typed promise emitted by the outline for long-range payoff tracking."""

    promise_id: str
    chapter_number: int
    text: str
    strand: str
    chapter_objective: str
    due_by_chapter: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "promise_id": self.promise_id,
            "chapter_number": self.chapter_number,
            "text": self.text,
            "strand": self.strand,
            "chapter_objective": self.chapter_objective,
            "due_by_chapter": self.due_by_chapter,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryPromise:
        data = _dict(payload)
        due_by_chapter = data.get("due_by_chapter")
        return cls(
            promise_id=str(data.get("promise_id", str(uuid4()))),
            chapter_number=int(data.get("chapter_number", 0)),
            text=str(data.get("text", "")),
            strand=str(data.get("strand", "")),
            chapter_objective=str(data.get("chapter_objective", "")),
            due_by_chapter=int(due_by_chapter) if due_by_chapter is not None else None,
        )


@dataclass(slots=True)
class PayoffBeat:
    """Resolved payoff beat captured from drafted chapters."""

    promise_id: str
    chapter_number: int
    payoff_text: str
    strength: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "promise_id": self.promise_id,
            "chapter_number": self.chapter_number,
            "payoff_text": self.payoff_text,
            "strength": self.strength,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> PayoffBeat:
        data = _dict(payload)
        return cls(
            promise_id=str(data.get("promise_id", str(uuid4()))),
            chapter_number=int(data.get("chapter_number", 0)),
            payoff_text=str(data.get("payoff_text", "")),
            strength=int(data.get("strength", 0)),
        )


@dataclass(slots=True)
class StrandLedgerEntry:
    """Narrative strand tracking for long-form progression."""

    chapter_number: int
    strand: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "strand": self.strand,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StrandLedgerEntry:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            strand=str(data.get("strand", "")),
            status=str(data.get("status", "")),
        )


@dataclass(slots=True)
class CharacterStateSnapshot:
    """Character state memory for continuity checks."""

    chapter_number: int
    name: str
    motivation: str
    role: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "name": self.name,
            "motivation": self.motivation,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> CharacterStateSnapshot:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            name=str(data.get("name", "")),
            motivation=str(data.get("motivation", "")),
            role=str(data.get("role", "")),
        )


@dataclass(slots=True)
class RelationshipSnapshot:
    """Relationship memory for future longer-form continuity checks."""

    chapter_number: int
    source: str
    target: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "source": self.source,
            "target": self.target,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> RelationshipSnapshot:
        data = _dict(payload)
        return cls(
            chapter_number=int(data.get("chapter_number", 0)),
            source=str(data.get("source", "")),
            target=str(data.get("target", "")),
            status=str(data.get("status", "")),
        )


@dataclass(slots=True)
class WorldRuleLedgerEntry:
    """World-rule memory captured from the blueprint."""

    rule: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {"rule": self.rule, "source": self.source}

    @classmethod
    def from_dict(cls, payload: Any) -> WorldRuleLedgerEntry:
        data = _dict(payload)
        return cls(
            rule=str(data.get("rule", "")),
            source=str(data.get("source", "")),
        )


@dataclass(slots=True)
class StoryMemoryState:
    """Typed story memory and continuity ledger."""

    schema_version: int = 1
    premise: str = ""
    tone: str = ""
    target_chapters: int = 0
    themes: list[str] = field(default_factory=list)
    chapter_summaries: list[StoryChapterMemorySummary] = field(default_factory=list)
    active_characters: list[str] = field(default_factory=list)
    outline_titles: list[str] = field(default_factory=list)
    story_promises: list[StoryPromise] = field(default_factory=list)
    timeline_ledger: list[TimelineLedgerEntry] = field(default_factory=list)
    hook_ledger: list[HookLedgerEntry] = field(default_factory=list)
    promise_ledger: list[PromiseLedgerEntry] = field(default_factory=list)
    payoff_beats: list[PayoffBeat] = field(default_factory=list)
    pacing_ledger: list[PacingLedgerEntry] = field(default_factory=list)
    strand_ledger: list[StrandLedgerEntry] = field(default_factory=list)
    character_states: list[CharacterStateSnapshot] = field(default_factory=list)
    relationship_states: list[RelationshipSnapshot] = field(default_factory=list)
    world_rules: list[WorldRuleLedgerEntry] = field(default_factory=list)
    revision_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "premise": self.premise,
            "tone": self.tone,
            "target_chapters": self.target_chapters,
            "themes": self.themes,
            "chapter_summaries": [
                summary.to_dict() for summary in self.chapter_summaries
            ],
            "active_characters": self.active_characters,
            "outline_titles": self.outline_titles,
            "story_promises": [entry.to_dict() for entry in self.story_promises],
            "timeline_ledger": [entry.to_dict() for entry in self.timeline_ledger],
            "hook_ledger": [entry.to_dict() for entry in self.hook_ledger],
            "promise_ledger": [entry.to_dict() for entry in self.promise_ledger],
            "payoff_beats": [entry.to_dict() for entry in self.payoff_beats],
            "pacing_ledger": [entry.to_dict() for entry in self.pacing_ledger],
            "strand_ledger": [entry.to_dict() for entry in self.strand_ledger],
            "character_states": [state.to_dict() for state in self.character_states],
            "relationship_states": [
                state.to_dict() for state in self.relationship_states
            ],
            "world_rules": [rule.to_dict() for rule in self.world_rules],
            "revision_notes": self.revision_notes,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryMemoryState:
        data = _dict(payload)
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            premise=str(data.get("premise", "")),
            tone=str(data.get("tone", "")),
            target_chapters=int(data.get("target_chapters", 0)),
            themes=_strings(data.get("themes")),
            chapter_summaries=[
                StoryChapterMemorySummary.from_dict(item)
                for item in _list(data.get("chapter_summaries"))
            ],
            active_characters=_strings(data.get("active_characters")),
            outline_titles=_strings(data.get("outline_titles")),
            story_promises=[
                StoryPromise.from_dict(item)
                for item in _list(data.get("story_promises"))
            ],
            timeline_ledger=[
                TimelineLedgerEntry.from_dict(item)
                for item in _list(data.get("timeline_ledger"))
            ],
            hook_ledger=[
                HookLedgerEntry.from_dict(item)
                for item in _list(data.get("hook_ledger"))
            ],
            promise_ledger=[
                PromiseLedgerEntry.from_dict(item)
                for item in _list(data.get("promise_ledger"))
            ],
            payoff_beats=[
                PayoffBeat.from_dict(item) for item in _list(data.get("payoff_beats"))
            ],
            pacing_ledger=[
                PacingLedgerEntry.from_dict(item)
                for item in _list(data.get("pacing_ledger"))
            ],
            strand_ledger=[
                StrandLedgerEntry.from_dict(item)
                for item in _list(data.get("strand_ledger"))
            ],
            character_states=[
                CharacterStateSnapshot.from_dict(item)
                for item in _list(data.get("character_states"))
            ],
            relationship_states=[
                RelationshipSnapshot.from_dict(item)
                for item in _list(data.get("relationship_states"))
            ],
            world_rules=[
                WorldRuleLedgerEntry.from_dict(item)
                for item in _list(data.get("world_rules"))
            ],
            revision_notes=_strings(data.get("revision_notes")),
        )


@dataclass(slots=True)
class StoryWorkflowState:
    """Typed workflow state persisted in story metadata."""

    schema_version: int = 1
    status: str = "created"
    premise: str = ""
    tone: str = "commercial web fiction"
    target_chapters: int = 0
    generation_trace: list[GenerationTraceEntry] = field(default_factory=list)
    chapter_memory: list[StoryChapterMemorySummary] = field(default_factory=list)
    revision_notes: list[str] = field(default_factory=list)
    blueprint: StoryBlueprintArtifact | None = None
    blueprint_generated_at: str | None = None
    outline: StoryOutlineArtifact | None = None
    outline_generated_at: str | None = None
    drafted_chapters: int = 0
    last_structural_review: StoryReviewArtifact | None = None
    last_semantic_review: SemanticReviewArtifact | None = None
    last_review: HybridReviewReport | None = None
    last_exported_at: str | None = None
    last_updated_at: str | None = None
    published_at: str | None = None
    revision_history: list[dict[str, Any]] = field(default_factory=list)
    run_state: GenerationRun | None = None
    current_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "premise": self.premise,
            "tone": self.tone,
            "target_chapters": self.target_chapters,
            "generation_trace": [entry.to_dict() for entry in self.generation_trace],
            "chapter_memory": [entry.to_dict() for entry in self.chapter_memory],
            "revision_notes": self.revision_notes,
            "blueprint": self.blueprint.to_dict() if self.blueprint else None,
            "blueprint_generated_at": self.blueprint_generated_at,
            "outline": self.outline.to_dict() if self.outline else None,
            "outline_generated_at": self.outline_generated_at,
            "drafted_chapters": self.drafted_chapters,
            "last_structural_review": (
                self.last_structural_review.to_dict()
                if self.last_structural_review
                else None
            ),
            "last_semantic_review": (
                self.last_semantic_review.to_dict()
                if self.last_semantic_review
                else None
            ),
            "last_review": self.last_review.to_dict() if self.last_review else None,
            "last_exported_at": self.last_exported_at,
            "last_updated_at": self.last_updated_at,
            "published_at": self.published_at,
            "revision_history": self.revision_history,
            "run_state": self.run_state.to_dict() if self.run_state else None,
            "current_run_id": self.current_run_id,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryWorkflowState:
        data = _dict(payload)
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            status=str(data.get("status", "created")),
            premise=str(data.get("premise", "")),
            tone=str(data.get("tone", "commercial web fiction")),
            target_chapters=int(data.get("target_chapters", 0)),
            generation_trace=[
                GenerationTraceEntry.from_dict(item)
                for item in _list(data.get("generation_trace"))
            ],
            chapter_memory=[
                StoryChapterMemorySummary.from_dict(item)
                for item in _list(data.get("chapter_memory"))
            ],
            revision_notes=_strings(data.get("revision_notes")),
            blueprint=StoryBlueprintArtifact.from_dict(data.get("blueprint")),
            blueprint_generated_at=(
                str(data.get("blueprint_generated_at"))
                if data.get("blueprint_generated_at") is not None
                else None
            ),
            outline=StoryOutlineArtifact.from_dict(data.get("outline")),
            outline_generated_at=(
                str(data.get("outline_generated_at"))
                if data.get("outline_generated_at") is not None
                else None
            ),
            drafted_chapters=int(data.get("drafted_chapters", 0)),
            last_structural_review=StoryReviewArtifact.from_dict(
                data.get("last_structural_review", data.get("last_review"))
            ),
            last_semantic_review=SemanticReviewArtifact.from_dict(
                data.get("last_semantic_review")
            ),
            last_review=HybridReviewReport.from_dict(data.get("last_review")),
            last_exported_at=(
                str(data.get("last_exported_at"))
                if data.get("last_exported_at") is not None
                else None
            ),
            last_updated_at=(
                str(data.get("last_updated_at"))
                if data.get("last_updated_at") is not None
                else None
            ),
            published_at=(
                str(data.get("published_at"))
                if data.get("published_at") is not None
                else None
            ),
            revision_history=[
                _dict(item) for item in _list(data.get("revision_history"))
            ],
            run_state=GenerationRun.from_dict(data.get("run_state")),
            current_run_id=(
                str(data.get("current_run_id"))
                if data.get("current_run_id") is not None
                else None
            ),
        )


@dataclass(slots=True)
class StoryExportArtifact:
    """Typed export payload for a story workspace."""

    story: dict[str, Any]
    workflow: dict[str, Any]
    memory: dict[str, Any]
    blueprint: dict[str, Any] | None
    outline: dict[str, Any] | None
    last_review: dict[str, Any] | None
    revision_notes: list[str]
    exported_at: str
    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    version: int = 1
    source_run_id: str | None = None
    source_provider: str = "system"
    source_model: str = "workspace-export-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "version": self.version,
            "source_run_id": self.source_run_id,
            "source_provider": self.source_provider,
            "source_model": self.source_model,
            "story": self.story,
            "workflow": self.workflow,
            "memory": self.memory,
            "blueprint": self.blueprint,
            "outline": self.outline,
            "last_review": self.last_review,
            "revision_notes": self.revision_notes,
            "exported_at": self.exported_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> StoryExportArtifact | None:
        data = _dict(payload)
        if not data:
            return None
        return cls(
            artifact_id=str(data.get("artifact_id", str(uuid4()))),
            version=int(data.get("version", 1)),
            source_run_id=(
                str(data.get("source_run_id"))
                if data.get("source_run_id") is not None
                else None
            ),
            source_provider=str(data.get("source_provider", "system")),
            source_model=str(data.get("source_model", "workspace-export-v1")),
            story=_dict(data.get("story")),
            workflow=_dict(data.get("workflow")),
            memory=_dict(data.get("memory")),
            blueprint=_dict(data.get("blueprint")) or None,
            outline=_dict(data.get("outline")) or None,
            last_review=_dict(data.get("last_review")) or None,
            revision_notes=_strings(data.get("revision_notes")),
            exported_at=str(data.get("exported_at", utcnow_iso())),
        )


__all__ = [
    "ArtifactHistoryEntry",
    "ArtifactKind",
    "CharacterStateSnapshot",
    "GenerationRunResourceState",
    "GenerationRun",
    "GenerationRunMode",
    "GenerationRunStatus",
    "GenerationTraceEntry",
    "HookLedgerEntry",
    "HybridReviewReport",
    "NarrativeStrand",
    "PayoffBeat",
    "PacingLedgerEntry",
    "PromiseLedgerEntry",
    "RelationshipSnapshot",
    "ReviewSeverity",
    "RunEvent",
    "RunEventType",
    "RunSnapshot",
    "RunSnapshotType",
    "StageExecution",
    "StageExecutionStatus",
    "StoryArtifactResourceState",
    "StoryBlueprintArtifact",
    "StoryChapterMemorySummary",
    "StoryExportArtifact",
    "StoryGenerationState",
    "StoryMemoryState",
    "StoryOutlineArtifact",
    "StoryOutlineChapter",
    "StoryPromise",
    "SemanticReviewArtifact",
    "SemanticReviewMetrics",
    "DraftFailureArtifact",
    "StoryReviewArtifact",
    "StoryReviewIssue",
    "StoryReviewMetrics",
    "StrandLedgerEntry",
    "StoryWorkflowState",
    "TimelineLedgerEntry",
    "WorldRuleLedgerEntry",
    "utcnow_iso",
]
