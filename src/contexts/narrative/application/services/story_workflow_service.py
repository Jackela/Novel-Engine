"""Story workflow facade for the canonical long-form novel pipeline."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
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
from src.contexts.narrative.application.services.chapter_drafting_service import (
    ChapterDraftingService,
    DraftChapterFailure,
)
from src.contexts.narrative.application.services.continuity_review_service import (
    ContinuityReviewService,
)
from src.contexts.narrative.application.services.hybrid_publication_gate import (
    HybridPublicationGate,
)
from src.contexts.narrative.application.services.semantic_review_service import (
    SemanticReviewService,
)
from src.contexts.narrative.application.services.story_export_service import (
    StoryExportService,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_planning_service import (
    StoryPlanningService,
)
from src.contexts.narrative.application.services.story_publication_service import (
    StoryPublicationService,
)
from src.contexts.narrative.application.services.story_revision_service import (
    StoryRevisionService,
)
from src.contexts.narrative.application.services.story_workflow_support import (
    character_names,
    extract_world_rules,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    GenerationRun,
    GenerationRunResourceState,
    HybridReviewReport,
    StoryArtifactResourceState,
    StoryGenerationState,
    StoryMemoryState,
    StoryReviewArtifact,
    StoryReviewIssue,
    StoryWorkflowState,
    WorldRuleLedgerEntry,
)
from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)
from src.shared.application.result import Failure, Result, Success

StoryReviewReport = HybridReviewReport
StoryRunOperation = Literal[
    "blueprint",
    "outline",
    "draft",
    "review",
    "revise",
    "export",
    "publish",
    "pipeline",
]
MAX_EDITORIAL_REVIEW_PASSES = 3
MAX_EDITORIAL_REVISION_PASSES = 2


@dataclass(slots=True)
class WorkflowStageError(Exception):
    """Typed stage failure used to keep result mapping explicit."""

    stage_name: str
    failure_code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class StoryWorkflowService:
    """Facade for the canonical long-form story generation workflow."""

    def __init__(
        self,
        story_repository: StoryRepositoryPort,
        generation_state_repository: StoryGenerationStateRepositoryPort,
        generation_run_repository: GenerationRunRepositoryPort,
        story_artifact_repository: StoryArtifactRepositoryPort,
        text_generation_provider: TextGenerationProvider,
        review_generation_provider: TextGenerationProvider | None = None,
        default_target_chapters: int = 12,
    ) -> None:
        if default_target_chapters < 1:
            raise ValueError("default_target_chapters must be positive")

        self._story_repository = story_repository
        self._generation_state_repository = generation_state_repository
        self._generation_run_repository = generation_run_repository
        self._story_artifact_repository = story_artifact_repository
        self._provider = text_generation_provider
        self._review_provider = review_generation_provider or text_generation_provider
        self._default_target_chapters = default_target_chapters
        self._planning_service = StoryPlanningService()
        self._drafting_service = ChapterDraftingService()
        self._review_service = ContinuityReviewService()
        self._semantic_review_service = SemanticReviewService(self._review_provider)
        self._hybrid_publication_gate = HybridPublicationGate()
        self._revision_service = StoryRevisionService(self._drafting_service)
        self._export_service = StoryExportService()
        self._publication_service = StoryPublicationService()

    async def create_story(
        self,
        *,
        title: str,
        genre: str,
        author_id: str,
        premise: str,
        target_chapters: int | None = None,
        target_audience: str | None = None,
        themes: list[str] | None = None,
        tone: str | None = None,
    ) -> Result[dict[str, Any]]:
        try:
            resolved_target_chapters = self._resolve_target_chapters(target_chapters)
            theme_list = [theme.strip() for theme in themes or [] if theme.strip()]
            story = Story(
                title=title.strip(),
                genre=genre.strip(),
                author_id=author_id.strip(),
                target_audience=target_audience.strip() if target_audience else None,
                themes=theme_list,
            )
            workflow = StoryWorkflowState(
                status="created",
                premise=premise.strip(),
                tone=(tone or "commercial web fiction").strip(),
                target_chapters=resolved_target_chapters,
            )
            memory = StoryMemoryState(
                premise=premise.strip(),
                tone=(tone or "commercial web fiction").strip(),
                target_chapters=resolved_target_chapters,
                themes=theme_list,
            )
            ctx = StoryWorkflowContext(
                story=story,
                repository=self._story_repository,
                state_repository=self._generation_state_repository,
                run_repository=self._generation_run_repository,
                artifact_repository=self._story_artifact_repository,
                provider=self._provider,
                default_target_chapters=self._default_target_chapters,
                workflow=workflow,
                memory=memory,
                run_history=[],
                run_events=[],
                run_snapshots=[],
                artifact_history=[],
            )
            story.metadata["narrative_seed"] = {
                "premise": premise.strip(),
                "tone": workflow.tone,
                "target_chapters": resolved_target_chapters,
            }
            ctx.touch()
            await ctx.save()
            return Success(
                {
                    "story": self._story_payload(story),
                    "workspace": self._workspace_payload(ctx),
                }
            )
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def get_story(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        return Success(
            {
                "story": self._story_payload(ctx.story),
                "workspace": self._workspace_payload(ctx),
            }
        )

    async def get_story_workspace(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        return Success({"workspace": self._workspace_payload(ctx)})

    async def get_story_runs(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        return Success(self._run_payload(ctx))

    async def get_story_run(
        self,
        story_id: str,
        run_id: str,
    ) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        if self._find_run(ctx, run_id) is None:
            return Failure("Run not found", "NOT_FOUND")
        return Success(self._single_run_payload(ctx, run_id))

    async def get_story_artifacts(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        return Success(self._artifact_payload(ctx))

    async def execute_story_run(
        self,
        story_id: str,
        *,
        operation: StoryRunOperation,
        target_chapters: int | None = None,
        publish: bool = False,
    ) -> Result[dict[str, Any]]:
        if operation == "pipeline":
            result = await self.run_story_pipeline(
                story_id,
                target_chapters=target_chapters,
                publish=publish,
            )
        elif operation == "blueprint":
            result = await self.generate_blueprint(story_id)
        elif operation == "outline":
            result = await self.generate_outline(story_id)
        elif operation == "draft":
            result = await self.draft_story(story_id, target_chapters=target_chapters)
        elif operation == "review":
            result = await self.review_story(story_id)
        elif operation == "revise":
            result = await self.revise_story(story_id)
        elif operation == "export":
            result = await self.export_story(story_id)
        else:
            result = await self.publish_story(story_id)

        if isinstance(result, Failure):
            return result

        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        run = ctx.workflow.run_state
        if run is None:
            return Failure(
                "Run execution completed without a recorded run state",
                "INTERNAL_ERROR",
            )
        payload = self._single_run_payload(ctx, run.run_id)
        payload["operation"] = operation
        return Success(payload)

    async def list_stories(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        author_id: str | None = None,
    ) -> Result[dict[str, Any]]:
        try:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            if offset < 0:
                raise ValueError("offset must be non-negative")

            if author_id:
                stories = await self._story_repository.list_by_author(
                    author_id=author_id.strip(),
                    limit=limit,
                )
            else:
                stories = await self._story_repository.list_all(
                    limit=limit,
                    offset=offset,
                )

            return Success(
                {
                    "stories": [self._story_payload(story) for story in stories],
                    "count": len(stories),
                    "limit": limit,
                    "offset": offset,
                }
            )
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def generate_blueprint(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            blueprint = await self._generate_blueprint_with_context(
                ctx,
                finalize_run=True,
            )
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "blueprint": blueprint.to_dict(),
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def generate_outline(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            outline = await self._generate_outline_with_context(
                ctx,
                finalize_run=True,
            )
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "outline": outline.to_dict(),
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def draft_story(
        self,
        story_id: str,
        target_chapters: int | None = None,
    ) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            drafted_chapters, skipped = await self._draft_story_with_context(
                ctx,
                target_chapters=target_chapters,
                finalize_run=True,
            )
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "drafted_chapters": drafted_chapters,
                    "skipped": skipped,
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def review_story(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            report = await self._review_story_with_context(ctx, finalize_run=True)
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "report": report.to_dict(),
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def revise_story(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            final_report, revision_notes = await self._close_editorial_loop(
                ctx,
                mode="manual",
                failure_stage="revise",
                finalize_run=True,
            )
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "report": final_report.to_dict(),
                    "revision_notes": revision_notes,
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def export_story(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            export = await self._export_story_with_context(ctx, finalize_run=True)
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "export": export.to_dict(),
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def publish_story(self, story_id: str) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            report, revision_notes = await self._close_editorial_loop(
                ctx,
                mode="manual",
                failure_stage="publish",
                finalize_run=False,
            )
            await self._publish_story_with_context(
                ctx,
                report=report,
                finalize_run=True,
            )
            return Success(
                {
                    "story": self._story_payload(ctx.story),
                    "workspace": self._workspace_payload(ctx),
                    "report": report.to_dict(),
                    "revision_notes": revision_notes,
                }
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def run_pipeline(
        self,
        *,
        title: str,
        genre: str,
        author_id: str,
        premise: str,
        target_chapters: int | None = None,
        target_audience: str | None = None,
        themes: list[str] | None = None,
        tone: str | None = None,
        publish: bool = True,
    ) -> Result[dict[str, Any]]:
        create_result = await self.create_story(
            title=title,
            genre=genre,
            author_id=author_id,
            premise=premise,
            target_chapters=target_chapters,
            target_audience=target_audience,
            themes=themes,
            tone=tone,
        )
        if isinstance(create_result, Failure):
            return create_result

        story_id = str(create_result.value["story"]["id"])
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error

        try:
            return Success(
                await self._execute_pipeline_with_context(
                    ctx,
                    target_chapters=target_chapters,
                    publish=publish,
                )
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def run_story_pipeline(
        self,
        story_id: str,
        *,
        target_chapters: int | None = None,
        publish: bool = False,
    ) -> Result[dict[str, Any]]:
        ctx_or_error = await self._load_context(story_id)
        if isinstance(ctx_or_error, Failure):
            return ctx_or_error
        ctx = ctx_or_error
        try:
            return Success(
                await self._execute_pipeline_with_context(
                    ctx,
                    target_chapters=target_chapters,
                    publish=publish,
                )
            )
        except WorkflowStageError as exc:
            return await self._handle_stage_error(ctx, exc)

    async def _execute_pipeline_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        target_chapters: int | None,
        publish: bool,
    ) -> dict[str, Any]:
        ctx.start_run("pipeline")
        ctx.touch()
        await ctx.save()

        blueprint = await self._generate_blueprint_with_context(
            ctx,
            mode="pipeline",
            finalize_run=False,
        )
        outline = await self._generate_outline_with_context(
            ctx,
            mode="pipeline",
            finalize_run=False,
        )
        drafted_chapters, _ = await self._draft_story_with_context(
            ctx,
            target_chapters=target_chapters,
            mode="pipeline",
            finalize_run=False,
        )
        initial_review = await self._review_story_with_context(
            ctx,
            mode="pipeline",
            finalize_run=False,
        )
        revision_notes: list[str] = []
        if publish:
            final_review, revision_notes = await self._close_editorial_loop(
                ctx,
                mode="pipeline",
                failure_stage="publish",
                finalize_run=False,
                initial_review=initial_review,
            )
        elif self._report_requires_editorial_closure(initial_review):
            revision_notes = await self._revise_story_with_context(
                ctx,
                mode="pipeline",
                finalize_run=False,
            )
            final_review = await self._review_story_with_context(
                ctx,
                mode="pipeline",
                finalize_run=False,
            )
        else:
            final_review = initial_review
        export = await self._export_story_with_context(
            ctx,
            mode="pipeline",
            finalize_run=False,
        )
        if publish:
            await self._publish_story_with_context(
                ctx,
                report=final_review,
                mode="pipeline",
                finalize_run=False,
            )
        ctx.complete_run(published=publish)
        ctx.touch()
        await ctx.save()
        return {
            "story": self._story_payload(ctx.story),
            "workspace": self._workspace_payload(ctx),
            "blueprint": blueprint.to_dict(),
            "outline": outline.to_dict(),
            "drafted_chapters": drafted_chapters,
            "initial_review": initial_review.to_dict(),
            "revision_notes": revision_notes,
            "final_review": final_review.to_dict(),
            "export": export.to_dict(),
            "published": publish,
        }

    async def _load_context(
        self,
        story_id: str,
    ) -> StoryWorkflowContext | Failure:
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error
        generation_state = await self._generation_state_repository.get_by_story_id(story_id)
        run_resource_state = await self._generation_run_repository.get_by_story_id(story_id)
        artifact_resource_state = await self._story_artifact_repository.get_by_story_id(
            story_id
        )
        return self._context_from_story(
            story_or_error,
            generation_state=generation_state,
            run_resource_state=run_resource_state,
            artifact_resource_state=artifact_resource_state,
        )

    async def _load_story(self, story_id: str) -> Story | Failure:
        try:
            story_uuid = UUID(story_id)
        except ValueError:
            return Failure("Story ID must be a valid UUID", "VALIDATION_ERROR")

        story = await self._story_repository.get_by_id(story_uuid)
        if story is None:
            return Failure("Story not found", "NOT_FOUND")
        return story

    def _context_from_story(
        self,
        story: Story,
        *,
        generation_state: StoryGenerationState | None = None,
        run_resource_state: GenerationRunResourceState | None = None,
        artifact_resource_state: StoryArtifactResourceState | None = None,
    ) -> StoryWorkflowContext:
        ctx = StoryWorkflowContext.from_story(
            story=story,
            repository=self._story_repository,
            state_repository=self._generation_state_repository,
            run_repository=self._generation_run_repository,
            artifact_repository=self._story_artifact_repository,
            provider=self._provider,
            default_target_chapters=self._default_target_chapters,
            generation_state=generation_state,
            run_resource_state=run_resource_state,
            artifact_resource_state=artifact_resource_state,
        )
        self._hydrate_context_memory(ctx)
        return ctx

    def _hydrate_context_memory(self, ctx: StoryWorkflowContext) -> None:
        blueprint = ctx.workflow.blueprint
        if blueprint is not None and not ctx.memory.active_characters:
            ctx.memory.active_characters = character_names(blueprint.character_bible)

        if ctx.memory.world_rules:
            return

        world_bible = (
            blueprint.world_bible
            if blueprint is not None
            else ctx.story.metadata.get("world_bible")
        )
        if not isinstance(world_bible, dict):
            return

        hydrated_rules = extract_world_rules(world_bible)
        if not hydrated_rules:
            return

        ctx.memory.world_rules = [
            WorldRuleLedgerEntry(rule=str(rule).strip(), source="blueprint")
            for rule in hydrated_rules
            if str(rule).strip()
        ]

    def _resolve_target_chapters(self, target_chapters: int | None) -> int:
        resolved = target_chapters or self._default_target_chapters
        if resolved < 1:
            raise ValueError("target_chapters must be positive")
        if resolved > Story.MAX_CHAPTERS:
            raise ValueError(f"target_chapters cannot exceed {Story.MAX_CHAPTERS}")
        return resolved

    @staticmethod
    def _issue_counts(report: HybridReviewReport | None) -> tuple[int, int]:
        if report is None:
            return 0, 0
        warning_count = sum(1 for issue in report.issues if issue.severity == "warning")
        blocker_count = sum(1 for issue in report.issues if issue.severity == "blocker")
        return warning_count, blocker_count

    def _report_requires_editorial_closure(self, report: HybridReviewReport) -> bool:
        warning_count, blocker_count = self._issue_counts(report)
        return (
            warning_count > 0
            or blocker_count > 0
            or not report.ready_for_publish
            or not report.publish_gate_passed
        )

    @staticmethod
    def _workspace_kind(author_id: str | None) -> str:
        normalized = (author_id or "").strip()
        if normalized.startswith("guest-"):
            return "guest"
        if normalized.startswith("user-"):
            return "user"
        return "unknown"

    def _workspace_context_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        workspace_id = str(ctx.story.author_id)
        workspace_kind = self._workspace_kind(workspace_id)
        return {
            "workspace_id": workspace_id,
            "workspace_kind": workspace_kind,
            "author_id": workspace_id,
            "label": "Guest workspace" if workspace_kind == "guest" else "Signed-in workspace",
            "summary": (
                "Guest drafting context with resumable workspace identity."
                if workspace_kind == "guest"
                else "Persistent author workspace bound to the signed-in session."
            ),
        }

    def _recommended_next_action_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        review = ctx.workflow.last_review
        warning_count, blocker_count = self._issue_counts(review)
        if ctx.workflow.blueprint is None:
            action = "generate_blueprint"
            label = "Generate blueprint"
            reason = "Create the world bible and character bible before outlining."
        elif ctx.workflow.outline is None:
            action = "generate_outline"
            label = "Generate outline"
            reason = "Turn the manuscript seed into a chapter-by-chapter plan."
        elif ctx.story.chapter_count < ctx.workflow.target_chapters:
            action = "draft"
            label = "Draft chapters"
            reason = "The manuscript has not yet reached the configured chapter target."
        elif review is None:
            action = "review"
            label = "Run review"
            reason = "Score continuity, reader pull, and publish readiness."
        elif blocker_count > 0 or warning_count > 0:
            action = "revise"
            label = "Close review warnings"
            reason = "Resolve all review issues before export and publication."
        elif ctx.last_export() is None:
            action = "export"
            label = "Export manuscript"
            reason = "Capture an immutable release candidate with evidence attached."
        elif ctx.workflow.published_at is None:
            action = "publish"
            label = "Publish manuscript"
            reason = "The story is exportable and zero-warning clean."
        else:
            action = "view_playback"
            label = "Inspect run playback"
            reason = "The manuscript is published; review immutable evidence and provenance."
        return {
            "action": action,
            "label": label,
            "reason": reason,
            "target_view": "playback" if action == "view_playback" else "workspace",
        }

    def _evidence_summary_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        review = ctx.workflow.last_review
        warning_count, blocker_count = self._issue_counts(review)
        return {
            "warning_count": warning_count,
            "blocker_count": blocker_count,
            "zero_warning": warning_count == 0 and blocker_count == 0,
            "published": ctx.workflow.published_at is not None,
            "publish_gate_passed": bool(review.publish_gate_passed) if review else False,
            "has_export": ctx.last_export() is not None,
            "latest_run_id": ctx.workflow.current_run_id,
            "artifact_count": len(ctx.artifact_history),
        }

    def _workspace_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        payload = ctx.workspace_payload()
        story_payload = payload.get("story")
        if isinstance(story_payload, dict):
            story_payload.setdefault("metadata", {})
            metadata = story_payload.get("metadata")
            if isinstance(metadata, dict):
                metadata.pop("last_export", None)
        payload["workspace_context"] = self._workspace_context_payload(ctx)
        payload["recommended_next_action"] = self._recommended_next_action_payload(ctx)
        payload["evidence_summary"] = self._evidence_summary_payload(ctx)
        return payload

    def _run_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        return {
            "current_run": ctx.workflow.run_state.to_dict()
            if ctx.workflow.run_state
            else None,
            "runs": [run.to_dict() for run in ctx.run_history],
        }

    def _artifact_payload(self, ctx: StoryWorkflowContext) -> dict[str, Any]:
        export_artifact = ctx.last_export()
        return {
            "current": {
                "blueprint": ctx.workflow.blueprint.to_dict()
                if ctx.workflow.blueprint
                else None,
                "outline": ctx.workflow.outline.to_dict()
                if ctx.workflow.outline
                else None,
                "structural_review": ctx.workflow.last_structural_review.to_dict()
                if ctx.workflow.last_structural_review
                else None,
                "semantic_review": ctx.workflow.last_semantic_review.to_dict()
                if ctx.workflow.last_semantic_review
                else None,
                "review": ctx.workflow.last_review.to_dict()
                if ctx.workflow.last_review
                else None,
                "export": export_artifact.to_dict() if export_artifact else None,
            },
            "history": [artifact.to_dict() for artifact in ctx.artifact_history],
        }

    def _single_run_payload(
        self,
        ctx: StoryWorkflowContext,
        run_id: str,
    ) -> dict[str, Any]:
        run = self._find_run(ctx, run_id)
        if run is None:
            raise ValueError(f"Unknown run_id: {run_id}")
        latest_snapshot = ctx.latest_snapshot_for_run(run_id)
        failure_snapshot = next(
            (
                snapshot
                for snapshot in reversed(ctx.run_snapshots)
                if snapshot.run_id == run_id and snapshot.snapshot_type == "run_failed"
            ),
            None,
        )
        failure_details = (
            deepcopy(failure_snapshot.failure_details) if failure_snapshot else {}
        )
        artifacts = [
            artifact.to_dict()
            for artifact in ctx.artifact_history
            if artifact.source_run_id == run_id
        ]
        latest_review = (
            HybridReviewReport.from_dict(latest_snapshot.workspace.get("review"))
            if latest_snapshot is not None
            else ctx.workflow.last_review
        )
        warning_count, blocker_count = self._issue_counts(latest_review)
        providers = sorted(
            {
                str(artifact.get("source_provider", "")).strip()
                for artifact in artifacts
                if str(artifact.get("source_provider", "")).strip()
            }
        )
        models = sorted(
            {
                str(artifact.get("source_model", "")).strip()
                for artifact in artifacts
                if str(artifact.get("source_model", "")).strip()
            }
        )
        failure_artifacts = [
            artifact
            for artifact in artifacts
            if artifact.get("kind") == "draft_failure"
        ]
        return {
            "run": run.to_dict(),
            "events": [
                event.to_dict() for event in ctx.run_events if event.run_id == run_id
            ],
            "artifacts": artifacts,
            "failure_artifacts": failure_artifacts,
            "latest_snapshot": latest_snapshot.to_dict() if latest_snapshot else None,
            "failure_snapshot": failure_snapshot.to_dict() if failure_snapshot else None,
            "stage_snapshots": [
                snapshot.to_dict()
                for snapshot in ctx.stage_snapshots_for_run(run_id)
            ],
            "failed_stage": failure_snapshot.failed_stage if failure_snapshot else None,
            "failure_code": failure_snapshot.failure_code if failure_snapshot else None,
            "failure_message": (
                failure_snapshot.failure_message if failure_snapshot else None
            ),
            "manuscript_preserved": (
                bool(failure_details.get("manuscript_preserved", True))
                if failure_snapshot
                else None
            ),
            "provenance": {
                "run_id": run.run_id,
                "mode": run.mode,
                "story_id": str(ctx.story.id),
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "source_providers": providers,
                "source_models": models,
                "snapshot_captured_at": latest_snapshot.captured_at if latest_snapshot else None,
            },
            "publish_verdict": {
                "published": run.published,
                "ready_for_publish": bool(latest_review.ready_for_publish)
                if latest_review
                else False,
                "publish_gate_passed": bool(latest_review.publish_gate_passed)
                if latest_review
                else False,
                "warning_count": warning_count,
                "blocker_count": blocker_count,
                "checked_at": latest_review.checked_at if latest_review else None,
            },
            "evidence_status": {
                "has_latest_snapshot": latest_snapshot is not None,
                "stage_snapshot_count": len(ctx.stage_snapshots_for_run(run_id)),
                "artifact_count": len(artifacts),
                "failure_artifact_count": len(failure_artifacts),
                "zero_warning": warning_count == 0 and blocker_count == 0,
            },
        }

    def _find_run(
        self,
        ctx: StoryWorkflowContext,
        run_id: str,
    ) -> GenerationRun | None:
        for run in ctx.run_history:
            if run.run_id == run_id:
                return run
        if ctx.workflow.run_state is not None and ctx.workflow.run_state.run_id == run_id:
            return ctx.workflow.run_state
        return None

    def _story_payload(self, story: Story) -> dict[str, Any]:
        payload = deepcopy(story.to_dict())
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            metadata.pop("last_export", None)
        return payload

    async def _handle_stage_error(
        self,
        ctx: StoryWorkflowContext,
        exc: WorkflowStageError,
    ) -> Failure:
        details = deepcopy(exc.details) if exc.details else {}
        details.setdefault("manuscript_preserved", True)
        ctx.fail_run(exc.stage_name, exc.failure_code, exc.message, details)
        ctx.touch()
        await ctx.save()
        return Failure(exc.message, exc.failure_code, details=details or None)

    async def _generate_blueprint_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> Any:
        ctx.start_stage("blueprint", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            blueprint = await self._planning_service.generate_blueprint(ctx)
            ctx.complete_stage(
                "blueprint",
                details={"provider": blueprint.provider, "model": blueprint.model},
            )
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return blueprint
        except ValueError as exc:
            raise WorkflowStageError("blueprint", "VALIDATION_ERROR", str(exc)) from exc
        except Exception as exc:
            code = "GENERATION_ERROR" if "generation" in exc.__class__.__name__.lower() else "INTERNAL_ERROR"
            raise WorkflowStageError("blueprint", code, str(exc)) from exc

    async def _generate_outline_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> Any:
        ctx.start_stage("outline", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            outline = await self._planning_service.generate_outline(ctx)
            ctx.complete_stage(
                "outline",
                details={"provider": outline.provider, "chapters": len(outline.chapters)},
            )
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return outline
        except ValueError as exc:
            code = "MISSING_BLUEPRINT" if "Blueprint must" in str(exc) else "VALIDATION_ERROR"
            raise WorkflowStageError("outline", code, str(exc)) from exc
        except Exception as exc:
            code = "GENERATION_ERROR" if "generation" in exc.__class__.__name__.lower() else "INTERNAL_ERROR"
            raise WorkflowStageError("outline", code, str(exc)) from exc

    async def _draft_story_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        target_chapters: int | None,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> tuple[int, bool]:
        ctx.start_stage("draft", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            drafted_chapters, skipped = await self._drafting_service.draft(
                ctx,
                target_chapters=target_chapters,
            )
            ctx.complete_stage(
                "draft",
                details={"drafted_chapters": drafted_chapters, "skipped": skipped},
            )
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return drafted_chapters, skipped
        except DraftChapterFailure as exc:
            raise WorkflowStageError(
                "draft",
                exc.failure_code,
                exc.message,
                details=deepcopy(exc.details),
            ) from exc
        except ValueError as exc:
            code = (
                "MISSING_OUTLINE"
                if "Outline must be generated" in str(exc)
                else "VALIDATION_ERROR"
            )
            raise WorkflowStageError("draft", code, str(exc)) from exc
        except Exception as exc:
            code = "GENERATION_ERROR" if "generation" in exc.__class__.__name__.lower() else "INTERNAL_ERROR"
            raise WorkflowStageError("draft", code, str(exc)) from exc

    async def _review_story_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> HybridReviewReport:
        ctx.start_stage("review", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            structural_review = self._review_service.review(ctx)
            semantic_review = await self._semantic_review_service.review(
                ctx,
                pack=ctx.context_pack(),
            )
            hybrid_review = self._hybrid_publication_gate.evaluate(
                story_id=str(ctx.story.id),
                run_id=ctx.workflow.current_run_id,
                structural_review=structural_review,
                semantic_review=semantic_review,
                version=ctx.artifact_version("hybrid_review"),
            )
            ctx.workflow.last_structural_review = structural_review
            ctx.workflow.last_semantic_review = semantic_review
            ctx.workflow.last_review = hybrid_review
            structural_entry = ctx.latest_artifact_entry("review")
            parent_artifact_ids = (
                [structural_entry.artifact_id] if structural_entry is not None else []
            )
            semantic_entry = ctx.record_artifact(
                kind="semantic_review",
                payload=semantic_review.to_dict(),
                version=semantic_review.version,
                generated_at=semantic_review.checked_at,
                source_stage="review",
                source_provider=semantic_review.source_provider,
                source_model=semantic_review.source_model,
                parent_artifact_ids=parent_artifact_ids,
                artifact_id=semantic_review.artifact_id,
            )
            ctx.record_artifact(
                kind="hybrid_review",
                payload=hybrid_review.to_dict(),
                version=hybrid_review.version,
                generated_at=hybrid_review.checked_at,
                source_stage="review",
                source_provider=hybrid_review.source_provider,
                source_model=hybrid_review.source_model,
                parent_artifact_ids=[
                    structural_review.artifact_id,
                    semantic_entry.artifact_id,
                ],
                artifact_id=hybrid_review.artifact_id,
            )
            ctx.complete_stage(
                "review",
                details={
                    "quality_score": hybrid_review.quality_score,
                    "ready_for_publish": hybrid_review.ready_for_publish,
                    "structural_quality_score": structural_review.quality_score,
                    "semantic_score": semantic_review.semantic_score,
                },
            )
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return hybrid_review
        except ValueError as exc:
            raise WorkflowStageError("review", "VALIDATION_ERROR", str(exc)) from exc
        except Exception as exc:
            code = (
                "GENERATION_ERROR"
                if "generation" in exc.__class__.__name__.lower()
                else "INTERNAL_ERROR"
            )
            raise WorkflowStageError("review", code, str(exc)) from exc

    async def _close_editorial_loop(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"],
        failure_stage: str,
        finalize_run: bool,
        initial_review: HybridReviewReport | None = None,
    ) -> tuple[HybridReviewReport, list[str]]:
        review_attempts = 0
        revision_attempts = 0
        revision_notes: list[str] = []
        report = initial_review

        if report is None:
            report = await self._review_story_with_context(
                ctx,
                mode=mode,
                finalize_run=False,
            )
            review_attempts += 1
        else:
            review_attempts = 1

        while self._report_requires_editorial_closure(report):
            warning_count, blocker_count = self._issue_counts(report)
            if (
                revision_attempts >= MAX_EDITORIAL_REVISION_PASSES
                or review_attempts >= MAX_EDITORIAL_REVIEW_PASSES
            ):
                raise WorkflowStageError(
                    failure_stage,
                    "QUALITY_GATE_FAILED",
                    "Story still has unresolved review warnings after the editorial closure loop.",
                    details={
                        "report": report.to_dict(),
                        "warning_count": warning_count,
                        "blocker_count": blocker_count,
                        "revision_attempts": revision_attempts,
                        "review_attempts": review_attempts,
                    },
                )

            revision_notes.extend(
                await self._revise_story_with_context(
                    ctx,
                    mode=mode,
                    finalize_run=False,
                )
            )
            revision_attempts += 1
            report = await self._review_story_with_context(
                ctx,
                mode=mode,
                finalize_run=False,
            )
            review_attempts += 1

        if finalize_run:
            ctx.complete_run()
            ctx.touch()
            await ctx.save()
        return report, revision_notes

    async def _revise_story_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> list[str]:
        ctx.start_stage("revise", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            current_review = self._revision_review(ctx)
            revision_notes = await self._revision_service.revise(ctx, current_review)
            ctx.complete_stage(
                "revise",
                details={"revision_notes": len(revision_notes)},
            )
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return revision_notes
        except ValueError as exc:
            raise WorkflowStageError("revise", "VALIDATION_ERROR", str(exc)) from exc
        except Exception as exc:
            code = "GENERATION_ERROR" if "generation" in exc.__class__.__name__.lower() else "INTERNAL_ERROR"
            raise WorkflowStageError("revise", code, str(exc)) from exc

    def _revision_review(self, ctx: StoryWorkflowContext) -> StoryReviewArtifact:
        structural_review = (
            ctx.workflow.last_structural_review or self._review_service.review(ctx)
        )
        hybrid_review = ctx.workflow.last_review
        semantic_review = hybrid_review.semantic_review if hybrid_review is not None else None
        if semantic_review is None:
            return structural_review

        merged_issues = self._dedupe_revision_issues(
            list(structural_review.issues) + list(semantic_review.issues)
        )
        revision_notes = list(structural_review.revision_notes) + list(
            semantic_review.repair_suggestions
        )
        hybrid_summary = (
            hybrid_review.summary if hybrid_review is not None else structural_review.summary
        )
        return StoryReviewArtifact(
            artifact_id=structural_review.artifact_id,
            version=structural_review.version,
            source_run_id=structural_review.source_run_id,
            source_provider=structural_review.source_provider,
            source_model=structural_review.source_model,
            story_id=structural_review.story_id,
            quality_score=structural_review.quality_score,
            ready_for_publish=structural_review.ready_for_publish,
            summary=hybrid_summary,
            issues=merged_issues,
            revision_notes=revision_notes,
            chapter_count=structural_review.chapter_count,
            scene_count=structural_review.scene_count,
            continuity_checks=dict(structural_review.continuity_checks),
            checked_at=structural_review.checked_at,
            metrics=structural_review.metrics,
        )

    @staticmethod
    def _dedupe_revision_issues(
        issues: list[StoryReviewIssue],
    ) -> list[StoryReviewIssue]:
        seen: set[tuple[str, str | None, str]] = set()
        deduped: list[StoryReviewIssue] = []
        for issue in issues:
            key = (issue.code, issue.location, issue.message)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue)
        return deduped

    async def _export_story_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> Any:
        ctx.start_stage("export", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            export = self._export_service.export(ctx)
            ctx.complete_stage("export", details={"exported_at": export.exported_at})
            if finalize_run:
                ctx.complete_run()
            ctx.touch()
            await ctx.save()
            return export
        except ValueError as exc:
            raise WorkflowStageError("export", "VALIDATION_ERROR", str(exc)) from exc
        except Exception as exc:
            raise WorkflowStageError("export", "INTERNAL_ERROR", str(exc)) from exc

    async def _publish_story_with_context(
        self,
        ctx: StoryWorkflowContext,
        *,
        report: HybridReviewReport,
        mode: Literal["manual", "pipeline"] = "manual",
        finalize_run: bool,
    ) -> None:
        ctx.start_stage("publish", mode=mode, details={"story_id": str(ctx.story.id)})
        try:
            self._publication_service.publish(ctx, report)
            ctx.complete_stage("publish", details={"published": True})
            if finalize_run:
                ctx.complete_run(published=True)
            ctx.touch()
            await ctx.save()
        except ValueError as exc:
            raise WorkflowStageError(
                "publish",
                "QUALITY_GATE_FAILED",
                str(exc),
                details={"report": report.to_dict()},
            ) from exc
        except Exception as exc:
            raise WorkflowStageError("publish", "INTERNAL_ERROR", str(exc)) from exc


__all__ = [
    "StoryReviewReport",
    "StoryWorkflowService",
]
