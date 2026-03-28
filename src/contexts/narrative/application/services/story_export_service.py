"""Export stage for the typed story workflow."""

from __future__ import annotations

from copy import deepcopy

from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryExportArtifact,
    utcnow_iso,
)


class StoryExportService:
    """Build serializable export artifacts for the author workspace."""

    def export(self, ctx: StoryWorkflowContext) -> StoryExportArtifact:
        artifact = StoryExportArtifact(
            story=self._story_snapshot(ctx),
            workflow=ctx.workflow.to_dict(),
            memory=ctx.memory.to_dict(),
            blueprint=ctx.workflow.blueprint.to_dict() if ctx.workflow.blueprint else None,
            outline=ctx.workflow.outline.to_dict() if ctx.workflow.outline else None,
            last_review=ctx.workflow.last_review.to_dict()
            if ctx.workflow.last_review
            else None,
            revision_notes=list(ctx.workflow.revision_notes),
            exported_at=utcnow_iso(),
            version=ctx.artifact_version("export"),
            source_run_id=ctx.workflow.current_run_id,
            source_provider="system",
            source_model="workspace-export-v1",
        )
        parent_artifact_ids = [
            entry.artifact_id
            for entry in (
                ctx.latest_artifact_entry("blueprint"),
                ctx.latest_artifact_entry("outline"),
                ctx.latest_artifact_entry("review"),
            )
            if entry is not None
        ]
        ctx.record_artifact(
            kind="export",
            payload=artifact.to_dict(),
            version=artifact.version,
            generated_at=artifact.exported_at,
            source_stage="export",
            source_provider=artifact.source_provider,
            source_model=artifact.source_model,
            parent_artifact_ids=parent_artifact_ids,
            artifact_id=artifact.artifact_id,
        )
        ctx.set_last_export(artifact)
        ctx.workflow.last_exported_at = artifact.exported_at
        ctx.workflow.status = "exported"
        return artifact

    def _story_snapshot(self, ctx: StoryWorkflowContext) -> dict[str, object]:
        story_payload = deepcopy(ctx.story.to_dict())
        metadata = story_payload.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("last_export", None)
        return story_payload


__all__ = ["StoryExportService"]
