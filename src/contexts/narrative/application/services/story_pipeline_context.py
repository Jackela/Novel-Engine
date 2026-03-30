"""Shared story workflow context used by stage services."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationResult,
)
from src.contexts.narrative.application.ports.generation_run_repository_port import (
    GenerationRunRepositoryPort,
)
from src.contexts.narrative.application.ports.story_artifact_repository_port import (
    StoryArtifactRepositoryPort,
)
from src.contexts.narrative.application.ports.story_generation_state_repository_port import (
    StoryGenerationStateRepositoryPort,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    ArtifactHistoryEntry,
    ArtifactKind,
    GenerationRun,
    GenerationRunMode,
    GenerationRunResourceState,
    RunEvent,
    RunEventType,
    RunSnapshot,
    RunSnapshotType,
    StoryArtifactResourceState,
    StoryExportArtifact,
    StoryGenerationState,
    StoryMemoryState,
    StoryWorkflowState,
    utcnow_iso,
)
from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)


@dataclass(slots=True)
class StoryWorkflowContext:
    """A mutable story workflow context for stage-oriented services."""

    story: Story
    repository: StoryRepositoryPort
    state_repository: StoryGenerationStateRepositoryPort
    run_repository: GenerationRunRepositoryPort
    artifact_repository: StoryArtifactRepositoryPort
    provider: TextGenerationProvider
    default_target_chapters: int
    workflow: StoryWorkflowState
    memory: StoryMemoryState
    run_history: list[GenerationRun]
    run_events: list[RunEvent]
    run_snapshots: list[RunSnapshot]
    artifact_history: list[ArtifactHistoryEntry]

    @classmethod
    def from_story(
        cls,
        *,
        story: Story,
        repository: StoryRepositoryPort,
        state_repository: StoryGenerationStateRepositoryPort,
        run_repository: GenerationRunRepositoryPort,
        artifact_repository: StoryArtifactRepositoryPort,
        provider: TextGenerationProvider,
        default_target_chapters: int,
        generation_state: StoryGenerationState | None = None,
        run_resource_state: GenerationRunResourceState | None = None,
        artifact_resource_state: StoryArtifactResourceState | None = None,
    ) -> StoryWorkflowContext:
        resolved_state = (
            generation_state
            or StoryGenerationState.from_legacy_metadata(str(story.id), story.metadata)
            or StoryGenerationState.empty(str(story.id))
        )
        resolved_run_state = (
            run_resource_state
            or GenerationRunResourceState.from_legacy_generation_state(resolved_state)
            or GenerationRunResourceState.empty(str(story.id))
        )
        resolved_artifact_state = (
            artifact_resource_state
            or StoryArtifactResourceState.from_legacy_generation_state(resolved_state)
            or StoryArtifactResourceState.empty(str(story.id))
        )
        workflow = StoryWorkflowState.from_dict(story.metadata.get("workflow"))
        if workflow.current_run_id is None:
            workflow.current_run_id = resolved_state.current_run_id
        if workflow.run_state is None and workflow.current_run_id is not None:
            workflow.run_state = next(
                (
                    run
                    for run in resolved_run_state.runs
                    if run.run_id == workflow.current_run_id
                ),
                None,
            )

        return cls(
            story=story,
            repository=repository,
            state_repository=state_repository,
            run_repository=run_repository,
            artifact_repository=artifact_repository,
            provider=provider,
            default_target_chapters=default_target_chapters,
            workflow=workflow,
            memory=StoryMemoryState.from_dict(story.metadata.get("story_memory")),
            run_history=resolved_run_state.runs,
            run_events=resolved_run_state.events,
            run_snapshots=resolved_run_state.snapshots,
            artifact_history=resolved_artifact_state.artifacts,
        )

    def resolve_target_chapters(self, target_chapters: int | None) -> int:
        """Resolve a target chapter count against story constraints."""
        resolved = target_chapters or self.workflow.target_chapters or self.default_target_chapters
        if resolved < 1:
            raise ValueError("target_chapters must be positive")
        if resolved > Story.MAX_CHAPTERS:
            raise ValueError(f"target_chapters cannot exceed {Story.MAX_CHAPTERS}")
        return resolved

    def persist_to_story(self) -> None:
        """Write typed workflow state back into story metadata."""
        self.story.metadata["workflow"] = self.workflow.to_dict()
        self.story.metadata["story_memory"] = self.memory.to_dict()
        self.story.metadata.pop("run_history", None)
        self.story.metadata.pop("run_events", None)
        self.story.metadata.pop("artifact_history", None)
        self.story.metadata.pop("current_run_id", None)
        self.story.metadata.pop("updated_at", None)

    async def save(self) -> None:
        """Persist the story through the repository."""
        self.persist_to_story()
        await self.repository.save(self.story)
        await self.state_repository.save(self._generation_state_snapshot())
        await self.run_repository.save(self._run_resource_snapshot())
        await self.artifact_repository.save(self._artifact_resource_snapshot())

    def touch(self) -> None:
        """Update shared timestamps."""
        now = datetime.utcnow()
        self.story.updated_at = now
        self.workflow.last_updated_at = now.isoformat()
        self.persist_to_story()

    def record_generation_trace(self, result: TextGenerationResult) -> None:
        """Append a generation trace entry into workflow state."""
        from src.contexts.narrative.application.services.story_workflow_types import (
            GenerationTraceEntry,
        )

        self.workflow.generation_trace.append(
            GenerationTraceEntry(
                timestamp=utcnow_iso(),
                step=result.step,
                provider=result.provider,
                model=result.model,
                content_keys=sorted(result.content.keys()),
            )
        )

    def start_run(self, mode: GenerationRunMode) -> None:
        """Start a fresh generation run."""
        run = GenerationRun.start(mode)
        self.workflow.run_state = run
        self.workflow.current_run_id = run.run_id
        self.run_history.append(run)
        self.record_run_event(
            "run_started",
            run_id=run.run_id,
            details={"mode": mode},
        )
        self.record_snapshot("run_started")

    def complete_run(self, published: bool = False) -> None:
        """Complete the current generation run."""
        if self.workflow.run_state is not None:
            self.workflow.run_state.mark_completed(published=published)
            self.record_run_event(
                "run_completed",
                run_id=self.workflow.run_state.run_id,
                details={"published": published},
            )
            self.record_snapshot("run_completed")

    def fail_run(
        self,
        stage_name: str,
        failure_code: str,
        failure_message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Mark the current run as failed."""
        run = self.workflow.run_state
        if run is None:
            run = GenerationRun.start("manual")
            self.workflow.run_state = run
            self.workflow.current_run_id = run.run_id
            self.run_history.append(run)
            self.record_run_event(
                "run_started",
                run_id=run.run_id,
                details={"mode": "manual"},
            )
        run.mark_stage_failed(stage_name, failure_code, failure_message, details)
        self.record_run_event(
            "stage_failed",
            run_id=run.run_id,
            stage_name=stage_name,
            details={
                "failure_code": failure_code,
                "failure_message": failure_message,
                **(details or {}),
            },
        )
        self.record_run_event(
            "run_failed",
            run_id=run.run_id,
            stage_name=stage_name,
            details={
                "failure_code": failure_code,
                "failure_message": failure_message,
                **(details or {}),
            },
        )
        self.record_snapshot(
            "run_failed",
            stage_name=stage_name,
            failed_stage=stage_name,
            failure_code=failure_code,
            failure_message=failure_message,
            failure_details=details or {},
        )

    def start_stage(
        self,
        stage_name: str,
        *,
        mode: GenerationRunMode | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Start a stage within the current generation run."""
        if self.workflow.run_state is None or self.workflow.run_state.status != "running":
            self.start_run(mode or "manual")
        if self.workflow.run_state is not None:
            self.workflow.run_state.mark_stage_started(stage_name, details)
            self.record_run_event(
                "stage_started",
                run_id=self.workflow.run_state.run_id,
                stage_name=stage_name,
                details=details,
            )

    def complete_stage(
        self,
        stage_name: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Complete a stage within the current generation run."""
        if self.workflow.run_state is not None:
            self.workflow.run_state.mark_stage_completed(stage_name, details)
            self.record_run_event(
                "stage_completed",
                run_id=self.workflow.run_state.run_id,
                stage_name=stage_name,
                details=details,
            )
            self.record_snapshot("stage_completed", stage_name=stage_name)

    def set_last_export(self, artifact: StoryExportArtifact) -> None:
        """Persist the latest export artifact outside the workflow state."""
        self.story.metadata["last_export"] = artifact.to_dict()

    def last_export(self) -> StoryExportArtifact | None:
        """Return the latest export artifact if one exists."""
        return StoryExportArtifact.from_dict(self.story.metadata.get("last_export"))

    def artifact_version(self, kind: ArtifactKind) -> int:
        """Return the next append-only artifact version for a kind."""
        versions = [
            entry.version for entry in self.artifact_history if entry.kind == kind
        ]
        return max(versions, default=0) + 1

    def latest_artifact_entry(self, kind: ArtifactKind) -> ArtifactHistoryEntry | None:
        """Return the most recent artifact history entry for a kind."""
        for entry in reversed(self.artifact_history):
            if entry.kind == kind:
                return entry
        return None

    def record_artifact(
        self,
        *,
        kind: ArtifactKind,
        payload: dict[str, Any],
        version: int,
        generated_at: str,
        source_stage: str,
        source_provider: str,
        source_model: str,
        parent_artifact_ids: list[str] | None = None,
        artifact_id: str | None = None,
    ) -> ArtifactHistoryEntry:
        """Append a typed artifact history entry."""
        run_id = self.workflow.run_state.run_id if self.workflow.run_state else None
        entry = ArtifactHistoryEntry(
            artifact_id=artifact_id or str(uuid4()),
            kind=kind,
            version=version,
            generated_at=generated_at,
            source_run_id=run_id,
            source_stage=source_stage,
            source_provider=source_provider,
            source_model=source_model,
            parent_artifact_ids=list(parent_artifact_ids or []),
            payload=payload,
        )
        self.artifact_history.append(entry)
        return entry

    def record_run_event(
        self,
        event_type: RunEventType,
        *,
        run_id: str | None = None,
        stage_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Append a run event for future incremental workspace feeds."""
        resolved_run_id = run_id or self.workflow.current_run_id or ""
        self.run_events.append(
            RunEvent(
                event_id=str(uuid4()),
                run_id=resolved_run_id,
                event_type=event_type,
                timestamp=utcnow_iso(),
                stage_name=stage_name,
                details=details or {},
            )
        )

    def record_snapshot(
        self,
        snapshot_type: RunSnapshotType,
        *,
        stage_name: str | None = None,
        failed_stage: str | None = None,
        failure_code: str | None = None,
        failure_message: str | None = None,
        failure_details: dict[str, Any] | None = None,
    ) -> None:
        """Append an immutable workspace snapshot for the current run."""
        run_id = self.workflow.current_run_id
        if not run_id:
            return
        self.run_snapshots.append(
            RunSnapshot(
                snapshot_id=str(uuid4()),
                story_id=str(self.story.id),
                run_id=run_id,
                snapshot_type=snapshot_type,
                captured_at=utcnow_iso(),
                stage_name=stage_name,
                failed_stage=failed_stage,
                failure_code=failure_code,
                failure_message=failure_message,
                failure_details=deepcopy(failure_details or {}),
                workspace=deepcopy(self.workspace_payload()),
            )
        )

    def latest_snapshot_for_run(self, run_id: str) -> RunSnapshot | None:
        """Return the latest immutable snapshot for a run."""
        for snapshot in reversed(self.run_snapshots):
            if snapshot.run_id == run_id:
                return snapshot
        return None

    def stage_snapshots_for_run(self, run_id: str) -> list[RunSnapshot]:
        """Return stage-completed snapshots for a run."""
        return [
            snapshot
            for snapshot in self.run_snapshots
            if snapshot.run_id == run_id and snapshot.stage_name is not None
        ]

    def context_pack(self) -> Any:
        """Build the current typed context pack on demand."""
        from src.contexts.narrative.application.services.story_context_pack import (
            StoryContextPack,
        )

        return StoryContextPack.from_context(self)

    def workspace_payload(self) -> dict[str, Any]:
        """Build the latest author workspace projection."""
        export_artifact = self.last_export()
        return {
            "story": self.story.to_dict(),
            "workflow": self.workflow.to_dict(),
            "memory": self.memory.to_dict(),
            "blueprint": self.workflow.blueprint.to_dict()
            if self.workflow.blueprint
            else None,
            "outline": self.workflow.outline.to_dict()
            if self.workflow.outline
            else None,
            "structural_review": self.workflow.last_structural_review.to_dict()
            if self.workflow.last_structural_review
            else None,
            "semantic_review": self.workflow.last_semantic_review.to_dict()
            if self.workflow.last_semantic_review
            else None,
            "hybrid_review": self.workflow.last_review.to_dict()
            if self.workflow.last_review
            else None,
            "review": self.workflow.last_review.to_dict()
            if self.workflow.last_review
            else None,
            "export": export_artifact.to_dict() if export_artifact else None,
            "revision_notes": list(self.workflow.revision_notes),
            "run": self.workflow.run_state.to_dict() if self.workflow.run_state else None,
            "run_history": [run.to_dict() for run in self.run_history],
            "run_events": [event.to_dict() for event in self.run_events],
            "artifact_history": [artifact.to_dict() for artifact in self.artifact_history],
        }

    def _generation_state_snapshot(self) -> StoryGenerationState:
        """Build the independent generation-state snapshot."""
        return StoryGenerationState(
            story_id=str(self.story.id),
            current_run_id=self.workflow.current_run_id,
            updated_at=self.workflow.last_updated_at or utcnow_iso(),
        )

    def _run_resource_snapshot(self) -> GenerationRunResourceState:
        """Build the independent generation run resource snapshot."""
        return GenerationRunResourceState(
            story_id=str(self.story.id),
            runs=self.run_history,
            events=self.run_events,
            snapshots=self.run_snapshots,
            updated_at=self.workflow.last_updated_at or utcnow_iso(),
        )

    def _artifact_resource_snapshot(self) -> StoryArtifactResourceState:
        """Build the independent story artifact resource snapshot."""
        return StoryArtifactResourceState(
            story_id=str(self.story.id),
            artifacts=self.artifact_history,
            updated_at=self.workflow.last_updated_at or utcnow_iso(),
        )
