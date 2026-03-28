"""Pipeline runner for the story workflow facade."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from src.shared.application.result import Failure, Result, Success

StoryStageCallable = Callable[..., Awaitable[Result[dict[str, Any]]]]


class StoryPipelineRunner:
    """Thin orchestration runner for the full story pipeline."""

    def __init__(
        self,
        *,
        generate_blueprint: StoryStageCallable,
        generate_outline: StoryStageCallable,
        draft_story: StoryStageCallable,
        review_story: StoryStageCallable,
        revise_story: StoryStageCallable,
        export_story: StoryStageCallable,
        publish_story: StoryStageCallable,
        get_story: StoryStageCallable,
    ) -> None:
        self._generate_blueprint = generate_blueprint
        self._generate_outline = generate_outline
        self._draft_story = draft_story
        self._review_story = review_story
        self._revise_story = revise_story
        self._export_story = export_story
        self._publish_story = publish_story
        self._get_story = get_story

    async def run_existing_story(
        self,
        *,
        story_id: str,
        target_chapters: int | None,
        publish: bool,
    ) -> Result[dict[str, Any]]:
        blueprint_result = await self._generate_blueprint(story_id)
        if isinstance(blueprint_result, Failure):
            return blueprint_result

        outline_result = await self._generate_outline(story_id)
        if isinstance(outline_result, Failure):
            return outline_result

        draft_result = await self._draft_story(story_id, target_chapters=target_chapters)
        if isinstance(draft_result, Failure):
            return draft_result

        initial_review = await self._review_story(story_id)
        if isinstance(initial_review, Failure):
            return initial_review

        revision_result = await self._revise_story(story_id)
        if isinstance(revision_result, Failure):
            return revision_result

        final_review = await self._review_story(story_id)
        if isinstance(final_review, Failure):
            return final_review

        export_result = await self._export_story(story_id)
        if isinstance(export_result, Failure):
            return export_result

        publish_result: Result[dict[str, Any]] | None = None
        if publish:
            publish_result = await self._publish_story(story_id)
            if isinstance(publish_result, Failure):
                return publish_result

        final_story_result = await self._get_story(story_id)
        if isinstance(final_story_result, Failure):
            return final_story_result

        return Success(
            {
                "story": final_story_result.value["story"],
                "workspace": final_story_result.value["workspace"],
                "blueprint": blueprint_result.value["blueprint"],
                "outline": outline_result.value["outline"],
                "drafted_chapters": draft_result.value["drafted_chapters"],
                "initial_review": initial_review.value["report"],
                "revision_notes": revision_result.value["revision_notes"],
                "final_review": final_review.value["report"],
                "export": export_result.value["export"],
                "published": bool(
                    publish_result and not isinstance(publish_result, Failure)
                ),
            }
        )


__all__ = ["StoryPipelineRunner"]
