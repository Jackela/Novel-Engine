"""Story workflow application service.

This service owns the canonical long-form novel generation pipeline:
inspiration -> blueprint -> outline -> chapters -> review -> revision ->
export -> publish.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast
from uuid import UUID

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderError,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)
from src.contexts.narrative.domain.types import SceneType
from src.shared.application.result import Failure, Result, Success

ReviewSeverity = Literal["info", "warning", "blocker"]


@dataclass(slots=True)
class StoryReviewIssue:
    """A single quality gate issue discovered during review."""

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


@dataclass(slots=True)
class StoryReviewReport:
    """Structured story review result."""

    story_id: str
    quality_score: int
    ready_for_publish: bool
    summary: str
    issues: list[StoryReviewIssue] = field(default_factory=list)
    revision_notes: list[str] = field(default_factory=list)
    chapter_count: int = 0
    scene_count: int = 0
    continuity_checks: dict[str, bool] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
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
        }


class StoryWorkflowService:
    """Application service for the canonical novel-generation workflow."""

    def __init__(
        self,
        story_repository: StoryRepositoryPort,
        text_generation_provider: TextGenerationProvider,
        default_target_chapters: int = 12,
    ) -> None:
        if default_target_chapters < 1:
            raise ValueError("default_target_chapters must be positive")

        self._story_repository = story_repository
        self._provider = text_generation_provider
        self._default_target_chapters = default_target_chapters

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
        """Create a new draft story and seed its workflow memory."""
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
            self._workflow(story).update(
                {
                    "status": "created",
                    "premise": premise.strip(),
                    "tone": (tone or "commercial web fiction").strip(),
                    "target_chapters": resolved_target_chapters,
                    "generation_trace": [],
                    "chapter_memory": [],
                    "revision_notes": [],
                }
            )
            self._memory(story).update(
                {
                    "premise": premise.strip(),
                    "tone": (tone or "commercial web fiction").strip(),
                    "target_chapters": resolved_target_chapters,
                    "themes": theme_list,
                    "chapter_summaries": [],
                }
            )
            story.metadata["narrative_seed"] = {
                "premise": premise.strip(),
                "tone": (tone or "commercial web fiction").strip(),
                "target_chapters": resolved_target_chapters,
            }
            self._touch(story)
            await self._story_repository.save(story)
            return Success({"story": story.to_dict()})
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def get_story(self, story_id: str) -> Result[dict[str, Any]]:
        """Return a serialisable story snapshot."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error
        return Success({"story": story_or_error.to_dict()})

    async def list_stories(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        author_id: str | None = None,
    ) -> Result[dict[str, Any]]:
        """List stories, optionally filtered by author."""
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
                    "stories": [story.to_dict() for story in stories],
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
        """Generate or refresh the world and character bible."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        workflow = self._workflow(story)
        try:
            task = TextGenerationTask(
                step="bible",
                system_prompt=(
                    "You design durable long-form web novels. Return a compact "
                    "world bible and character bible that can support many chapters."
                ),
                user_prompt=(
                    f"Story title: {story.title}\n"
                    f"Genre: {story.genre}\n"
                    f"Premise: {workflow.get('premise', '')}\n"
                    f"Target chapters: {workflow.get('target_chapters', self._default_target_chapters)}\n"
                    f"Tone: {workflow.get('tone', 'commercial web fiction')}"
                ),
                response_schema={
                    "world_bible": {"type": "object"},
                    "character_bible": {"type": "object"},
                    "premise_summary": {"type": "string"},
                },
                temperature=0.35,
                metadata={
                    "story_id": str(story.id),
                    "title": story.title,
                    "genre": story.genre,
                    "author_id": story.author_id,
                    "target_chapters": workflow.get(
                        "target_chapters", self._default_target_chapters
                    ),
                },
            )
            result = await self._provider.generate_structured(task)
            blueprint = self._extract_blueprint(result, story)
            workflow["blueprint"] = blueprint
            workflow["blueprint_generated_at"] = self._now()
            self._record_generation_trace(workflow, result)
            story.metadata["world_bible"] = blueprint["world_bible"]
            story.metadata["character_bible"] = blueprint["character_bible"]
            story.metadata["premise_summary"] = blueprint["premise_summary"]
            self._memory(story)["active_characters"] = self._character_names(
                blueprint["character_bible"]
            )
            self._touch(story)
            await self._story_repository.save(story)
            return Success({"story": story.to_dict(), "blueprint": blueprint})
        except TextGenerationProviderError as exc:
            return Failure(str(exc), "GENERATION_ERROR")
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def generate_outline(self, story_id: str) -> Result[dict[str, Any]]:
        """Generate or refresh the chapter outline."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        workflow = self._workflow(story)
        blueprint = workflow.get("blueprint")
        if not isinstance(blueprint, dict):
            return Failure(
                "Blueprint must be generated before the outline",
                "MISSING_BLUEPRINT",
            )

        try:
            target_chapters = self._resolve_target_chapters(
                int(workflow.get("target_chapters", self._default_target_chapters))
            )
            task = TextGenerationTask(
                step="outline",
                system_prompt=(
                    "You design long-form web fiction outlines. Return a chapter "
                    "list with stable hooks, rising tension, and coherent pacing."
                ),
                user_prompt=(
                    f"Story title: {story.title}\n"
                    f"Premise: {workflow.get('premise', '')}\n"
                    f"World bible: {blueprint.get('world_bible', {})}\n"
                    f"Character bible: {blueprint.get('character_bible', {})}\n"
                    f"Target chapters: {target_chapters}\n"
                    f"Tone: {workflow.get('tone', 'commercial web fiction')}"
                ),
                response_schema={
                    "chapters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chapter_number": {"type": "integer"},
                                "title": {"type": "string"},
                                "summary": {"type": "string"},
                                "hook": {"type": "string"},
                            },
                        },
                    }
                },
                temperature=0.4,
                metadata={
                    "story_id": str(story.id),
                    "target_chapters": target_chapters,
                    "chapter_count": story.chapter_count,
                    "character_names": self._character_names(
                        blueprint.get("character_bible", {})
                    ),
                },
            )
            result = await self._provider.generate_structured(task)
            outline = self._extract_outline(result, target_chapters)
            workflow["outline"] = outline
            workflow["outline_generated_at"] = self._now()
            self._record_generation_trace(workflow, result)
            memory = self._memory(story)
            memory["outline_titles"] = [
                chapter["title"] for chapter in outline["chapters"]
            ]
            self._touch(story)
            await self._story_repository.save(story)
            return Success({"story": story.to_dict(), "outline": outline})
        except TextGenerationProviderError as exc:
            return Failure(str(exc), "GENERATION_ERROR")
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def draft_story(
        self,
        story_id: str,
        target_chapters: int | None = None,
    ) -> Result[dict[str, Any]]:
        """Draft missing chapters and scenes from the outline."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        workflow = self._workflow(story)
        outline = workflow.get("outline")
        if not isinstance(outline, dict):
            return Failure(
                "Outline must be generated before drafting chapters",
                "MISSING_OUTLINE",
            )

        chapters = outline.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            return Failure("Outline does not contain chapters", "GENERATION_ERROR")

        try:
            target_count = self._resolve_target_chapters(
                target_chapters
                if target_chapters is not None
                else int(workflow.get("target_chapters", self._default_target_chapters))
            )
            target_count = min(target_count, len(chapters))
            start_number = story.chapter_count + 1
            if start_number > target_count:
                return Success(
                    {
                        "story": story.to_dict(),
                        "drafted_chapters": story.chapter_count,
                        "skipped": True,
                    }
                )

            for chapter_number in range(start_number, target_count + 1):
                chapter_spec = self._outline_chapter_for_number(chapters, chapter_number)
                focus_character = self._select_focus_character(story, chapter_number)
                focus_motivation = self._focus_character_motivation(
                    story,
                    focus_character,
                )
                scene_result = await self._generate_chapter_scenes(
                    story=story,
                    chapter_spec=chapter_spec,
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                )
                scenes = self._extract_scenes(scene_result, chapter_spec)
                chapter = story.add_chapter(
                    title=chapter_spec["title"],
                    summary=chapter_spec["summary"],
                )
                chapter.metadata.update(
                    {
                        "chapter_number": chapter_number,
                        "focus_character": focus_character,
                        "focus_motivation": focus_motivation,
                        "timeline_day": chapter_number,
                        "outline_hook": chapter_spec.get("hook", ""),
                        "drafted_at": self._now(),
                    }
                )
                self._apply_scene_payload(
                    chapter=chapter,
                    scenes=scenes,
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                    hook=chapter_spec.get("hook", ""),
                )
                self._record_chapter_memory(
                    story,
                    chapter,
                    chapter_spec,
                    focus_character,
                    focus_motivation,
                )
                self._record_generation_trace(workflow, scene_result)
                self._touch(story)
                await self._story_repository.save(story)

            workflow["drafted_chapters"] = story.chapter_count
            workflow["status"] = "drafted"
            self._touch(story)
            await self._story_repository.save(story)
            return Success(
                {
                    "story": story.to_dict(),
                    "drafted_chapters": story.chapter_count,
                }
            )
        except TextGenerationProviderError as exc:
            return Failure(str(exc), "GENERATION_ERROR")
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

    async def review_story(self, story_id: str) -> Result[dict[str, Any]]:
        """Run structural and continuity checks over the story."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        workflow = self._workflow(story)
        blueprint = workflow.get("blueprint")
        outline = workflow.get("outline")
        target_chapters = self._resolve_target_chapters(
            int(workflow.get("target_chapters", self._default_target_chapters))
        )

        issues: list[StoryReviewIssue] = []
        continuity_checks: dict[str, bool] = {
            "blueprint_present": isinstance(blueprint, dict),
            "outline_present": isinstance(outline, dict),
            "chapters_present": story.chapter_count > 0,
            "chapter_count_complete": story.chapter_count >= target_chapters,
            "character_alignment": True,
            "motivation_alignment": True,
            "timeline_alignment": True,
            "hook_alignment": True,
        }

        if not continuity_checks["blueprint_present"]:
            issues.append(
                StoryReviewIssue(
                    code="missing_blueprint",
                    severity="blocker",
                    message="The world and character bible has not been generated.",
                    location="story",
                    suggestion="Generate the blueprint before reviewing or publishing.",
                )
            )
        if not continuity_checks["outline_present"]:
            issues.append(
                StoryReviewIssue(
                    code="missing_outline",
                    severity="blocker",
                    message="The chapter outline has not been generated.",
                    location="story",
                    suggestion="Generate the outline before drafting or publishing.",
                )
            )
        if story.chapter_count == 0:
            issues.append(
                StoryReviewIssue(
                    code="no_chapters",
                    severity="blocker",
                    message="The story does not contain any chapters yet.",
                    location="story",
                    suggestion="Draft chapters before attempting to publish.",
                )
            )
        if story.chapter_count < target_chapters:
            issues.append(
                StoryReviewIssue(
                    code="incomplete_story",
                    severity="blocker",
                    message=(
                        f"The story has {story.chapter_count} chapters but needs "
                        f"{target_chapters} to match the configured target."
                    ),
                    location="story",
                    suggestion="Draft the remaining chapters before publishing.",
                    details={
                        "actual_chapters": story.chapter_count,
                        "target_chapters": target_chapters,
                    },
                )
            )

        outline_chapters = self._outline_chapters(outline)
        for index, chapter in enumerate(story.chapters, start=1):
            self._review_chapter(
                story=story,
                chapter=chapter,
                index=index,
                outline_chapters=outline_chapters,
                issues=issues,
                continuity_checks=continuity_checks,
            )

        blocker_count = sum(1 for issue in issues if issue.severity == "blocker")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        quality_score = max(0, 100 - blocker_count * 20 - warning_count * 5)
        ready_for_publish = blocker_count == 0 and quality_score >= 80
        summary = (
            "Story passes the publication gate."
            if ready_for_publish
            else f"Story needs {blocker_count} blocker(s) and {warning_count} warning(s) addressed."
        )
        report = StoryReviewReport(
            story_id=str(story.id),
            quality_score=quality_score,
            ready_for_publish=ready_for_publish,
            summary=summary,
            issues=issues,
            revision_notes=list(workflow.get("revision_notes", [])),
            chapter_count=story.chapter_count,
            scene_count=sum(chapter.scene_count for chapter in story.chapters),
            continuity_checks=continuity_checks,
        )

        workflow["last_review"] = report.to_dict()
        workflow["status"] = "reviewed"
        self._touch(story)
        await self._story_repository.save(story)
        return Success({"story": story.to_dict(), "report": report.to_dict()})

    async def _load_story(self, story_id: str) -> Story | Failure:
        try:
            story_uuid = UUID(story_id)
        except ValueError:
            return Failure("Story ID must be a valid UUID", "VALIDATION_ERROR")

        story = await self._story_repository.get_by_id(story_uuid)
        if story is None:
            return Failure("Story not found", "NOT_FOUND")
        return story

    def _workflow(self, story: Story) -> dict[str, Any]:
        workflow = story.metadata.get("workflow")
        if not isinstance(workflow, dict):
            workflow = {}
            story.metadata["workflow"] = workflow
        return cast(dict[str, Any], workflow)

    def _memory(self, story: Story) -> dict[str, Any]:
        memory = story.metadata.get("story_memory")
        if not isinstance(memory, dict):
            memory = {}
            story.metadata["story_memory"] = memory
        return cast(dict[str, Any], memory)

    def _touch(self, story: Story) -> None:
        story.updated_at = datetime.utcnow()
        self._workflow(story)["last_updated_at"] = self._now()

    def _resolve_target_chapters(self, target_chapters: int | None) -> int:
        resolved = target_chapters or self._default_target_chapters
        if resolved < 1:
            raise ValueError("target_chapters must be positive")
        if resolved > Story.MAX_CHAPTERS:
            raise ValueError(
                f"target_chapters cannot exceed {Story.MAX_CHAPTERS}"
            )
        return resolved

    def _extract_blueprint(
        self,
        result: TextGenerationResult,
        story: Story,
    ) -> dict[str, Any]:
        world_bible = result.content.get("world_bible")
        character_bible = result.content.get("character_bible")
        premise_summary = str(result.content.get("premise_summary", "")).strip()
        if not isinstance(world_bible, dict):
            raise ValueError("Blueprint payload missing world_bible")
        if not isinstance(character_bible, dict):
            raise ValueError("Blueprint payload missing character_bible")

        return {
            "step": result.step,
            "provider": result.provider,
            "model": result.model,
            "generated_at": self._now(),
            "story_id": str(story.id),
            "world_bible": world_bible,
            "character_bible": character_bible,
            "premise_summary": premise_summary,
        }

    def _extract_outline(
        self,
        result: TextGenerationResult,
        target_chapters: int,
    ) -> dict[str, Any]:
        chapters = result.content.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            raise ValueError("Outline payload missing chapters")

        normalized_chapters: list[dict[str, Any]] = []
        for index, chapter in enumerate(chapters, start=1):
            if not isinstance(chapter, dict):
                raise ValueError("Outline chapter must be an object")
            chapter_number = self._chapter_number(chapter, index)
            title = str(chapter.get("title", "")).strip() or f"Chapter {index}"
            summary = str(chapter.get("summary", "")).strip()
            hook = str(chapter.get("hook", "")).strip()
            if not summary:
                raise ValueError("Outline chapter summary cannot be empty")
            normalized_chapters.append(
                {
                    "chapter_number": chapter_number,
                    "title": title,
                    "summary": summary,
                    "hook": hook,
                }
            )

        normalized_chapters.sort(key=lambda chapter: chapter["chapter_number"])
        return {
            "step": result.step,
            "provider": result.provider,
            "model": result.model,
            "generated_at": self._now(),
            "target_chapters": target_chapters,
            "chapters": normalized_chapters[:target_chapters],
        }

    @staticmethod
    def _chapter_number(chapter: dict[str, Any], fallback: int) -> int:
        value = chapter.get("chapter_number", fallback)
        try:
            chapter_number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Chapter number must be an integer") from exc
        if chapter_number < 1:
            raise ValueError("Chapter number must be positive")
        return chapter_number

    def _outline_chapters(
        self,
        outline: Any,
    ) -> list[dict[str, Any]]:
        if not isinstance(outline, dict):
            return []
        chapters = outline.get("chapters")
        if not isinstance(chapters, list):
            return []
        return [chapter for chapter in chapters if isinstance(chapter, dict)]

    def _outline_chapter_for_number(
        self,
        chapters: list[dict[str, Any]],
        chapter_number: int,
    ) -> dict[str, Any]:
        for chapter in chapters:
            if int(chapter.get("chapter_number", 0)) == chapter_number:
                return chapter
        raise ValueError(f"Outline chapter {chapter_number} not found")

    def _character_names(self, character_bible: dict[str, Any]) -> list[str]:
        characters = character_bible.get("characters", [])
        if not isinstance(characters, list):
            return []
        names: list[str] = []
        for character in characters:
            if isinstance(character, dict):
                name = str(character.get("name", "")).strip()
                if name:
                    names.append(name)
        return names

    @staticmethod
    def _normalize_scene_type(scene_type: Any) -> str:
        value = str(scene_type).strip().lower() or "narrative"
        valid_types = {
            "opening",
            "narrative",
            "dialogue",
            "action",
            "decision",
            "climax",
            "ending",
        }
        if value in valid_types:
            return value

        aliases: dict[str, str] = {
            "establishment": "opening",
            "setup": "opening",
            "introduction": "opening",
            "intro": "opening",
            "conversation": "dialogue",
            "interaction": "dialogue",
            "conflict": "action",
            "pressure": "action",
            "build-up": "narrative",
            "build": "narrative",
            "reveal": "climax",
            "twist": "climax",
            "resolution": "ending",
            "finale": "ending",
            "wrapup": "ending",
        }
        return str(aliases.get(value, "narrative"))

    def _character_profile(
        self,
        character_bible: dict[str, Any],
        focus_character: str,
    ) -> dict[str, Any]:
        characters = character_bible.get("characters", [])
        if not isinstance(characters, list):
            return {}

        for character in characters:
            if not isinstance(character, dict):
                continue
            name = str(character.get("name", "")).strip()
            if name == focus_character:
                return character
        return {}

    def _focus_character_motivation(
        self,
        story: Story,
        focus_character: str,
        chapter: Chapter | None = None,
    ) -> str:
        if chapter is not None:
            motivation = str(chapter.metadata.get("focus_motivation", "")).strip()
            if motivation:
                return motivation

        workflow = self._workflow(story)
        blueprint = workflow.get("blueprint")
        if isinstance(blueprint, dict):
            character_bible = blueprint.get("character_bible", {})
            if isinstance(character_bible, dict):
                profile = self._character_profile(character_bible, focus_character)
                motivation = str(profile.get("motivation", "")).strip()
                if motivation:
                    return motivation
        return ""

    @staticmethod
    def _issues_for_location(
        issues: list[StoryReviewIssue],
        location: str,
    ) -> list[StoryReviewIssue]:
        return [issue for issue in issues if issue.location == location]

    def _select_focus_character(self, story: Story, chapter_number: int) -> str:
        workflow = self._workflow(story)
        blueprint = workflow.get("blueprint")
        if isinstance(blueprint, dict):
            names = self._character_names(blueprint.get("character_bible", {}))
            if names:
                return names[(chapter_number - 1) % len(names)]
        return story.author_id

    async def _generate_chapter_scenes(
        self,
        *,
        story: Story,
        chapter_spec: dict[str, Any],
        focus_character: str,
        focus_motivation: str,
    ) -> TextGenerationResult:
        workflow = self._workflow(story)
        task = TextGenerationTask(
            step="chapter_scenes",
            system_prompt=(
                "You write coherent chapter scenes for a long-form web novel. "
                "Keep the pacing commercial, the continuity stable, and the hook strong. "
                "Use scene_type values from: opening, narrative, dialogue, action, "
                "decision, climax, ending."
            ),
            user_prompt=(
                f"Story title: {story.title}\n"
                f"Chapter number: {chapter_spec['chapter_number']}\n"
                f"Chapter title: {chapter_spec['title']}\n"
                f"Chapter summary: {chapter_spec['summary']}\n"
                f"Chapter hook: {chapter_spec.get('hook', '')}\n"
                f"Focus character: {focus_character}\n"
                f"Focus motivation: {focus_motivation}\n"
                f"Premise: {workflow.get('premise', '')}"
            ),
            response_schema={
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_type": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
            temperature=0.5,
            metadata={
                "story_id": str(story.id),
                "chapter_number": chapter_spec["chapter_number"],
                "chapter_title": chapter_spec["title"],
                "focus_character": focus_character,
                "focus_motivation": focus_motivation,
                "outline_hook": chapter_spec.get("hook", ""),
                "previous_summary": self._previous_chapter_summary(story),
            },
        )
        return await self._provider.generate_structured(task)

    def _extract_scenes(
        self,
        result: TextGenerationResult,
        chapter_spec: dict[str, Any],
    ) -> list[dict[str, Any]]:
        scenes = result.content.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise ValueError(
                f"Chapter {chapter_spec['chapter_number']} did not contain scenes"
            )

        normalized: list[dict[str, Any]] = []
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise ValueError("Scene payload must be an object")
            content = str(scene.get("content", "")).strip()
            scene_type = self._normalize_scene_type(
                scene.get("scene_type", "narrative")
            )
            title = str(scene.get("title", "")).strip() or (
                f"{chapter_spec['title']} - Scene {index}"
            )
            if not content:
                raise ValueError("Scene content cannot be empty")
            normalized.append(
                {
                    "scene_type": scene_type,
                    "title": title,
                    "content": content,
                }
            )
        return normalized

    def _apply_scene_payload(
        self,
        *,
        chapter: Chapter,
        scenes: list[dict[str, Any]],
        focus_character: str,
        focus_motivation: str,
        hook: str,
    ) -> None:
        for index, scene_payload in enumerate(scenes, start=1):
            content = scene_payload["content"].strip()
            if index == 1 and focus_character:
                content = self._ensure_character_anchor(content, focus_character)
            if index == 1 and focus_motivation:
                content = self._ensure_motivation_anchor(content, focus_motivation)
            if index == len(scenes):
                content = self._ensure_hook(content, hook)
            scene_type = cast(
                SceneType,
                self._normalize_scene_type(scene_payload["scene_type"]),
            )

            scene: Scene = chapter.add_scene(
                content=content,
                scene_type=scene_type,
                title=scene_payload["title"],
            )
            scene.metadata.update(
                {
                    "focus_character": focus_character,
                    "focus_motivation": focus_motivation,
                    "timeline_day": chapter.chapter_number,
                    "outline_hook": hook,
                    "scene_index": index,
                }
            )

    def _ensure_character_anchor(self, content: str, focus_character: str) -> str:
        if focus_character.lower() in content.lower():
            return content
        return f"{content} {focus_character} anchors the chapter."

    def _ensure_motivation_anchor(self, content: str, focus_motivation: str) -> str:
        if focus_motivation.lower() in content.lower():
            return content
        return f"{content} Their driving motive is to {focus_motivation}."

    def _ensure_hook(self, content: str, hook: str) -> str:
        if not hook:
            return content
        if hook.lower() in content.lower():
            return content
        if content.endswith("?"):
            return content
        return f"{content} {hook}"

    def _record_chapter_memory(
        self,
        story: Story,
        chapter: Chapter,
        chapter_spec: dict[str, Any],
        focus_character: str,
        focus_motivation: str,
    ) -> None:
        memory = self._memory(story)
        chapter_memory = memory.setdefault("chapter_summaries", [])
        if isinstance(chapter_memory, list):
            chapter_memory.append(
                {
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "summary": chapter.summary,
                    "focus_character": focus_character,
                    "focus_motivation": focus_motivation,
                    "hook": chapter_spec.get("hook", ""),
                }
            )
        workflow = self._workflow(story)
        workflow.setdefault("chapter_memory", []).append(
            {
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "focus_character": focus_character,
                "focus_motivation": focus_motivation,
                "scene_count": chapter.scene_count,
            }
        )

    def _previous_chapter_summary(self, story: Story) -> str:
        if not story.chapters:
            return ""
        previous = story.chapters[-1]
        return previous.summary or ""

    def _record_generation_trace(
        self,
        workflow: dict[str, Any],
        result: TextGenerationResult,
    ) -> None:
        trace = workflow.setdefault("generation_trace", [])
        if isinstance(trace, list):
            trace.append(
                {
                    "timestamp": self._now(),
                    "step": result.step,
                    "provider": result.provider,
                    "model": result.model,
                    "content_keys": sorted(result.content.keys()),
                }
            )

    def _review_chapter(
        self,
        *,
        story: Story,
        chapter: Chapter,
        index: int,
        outline_chapters: list[dict[str, Any]],
        issues: list[StoryReviewIssue],
        continuity_checks: dict[str, bool],
    ) -> None:
        expected_chapter = (
            outline_chapters[index - 1] if index <= len(outline_chapters) else {}
        )
        location = f"chapter-{chapter.chapter_number}"
        if chapter.chapter_number != index:
            continuity_checks["sequential_chapters"] = False
            issues.append(
                StoryReviewIssue(
                    code="non_sequential_chapter",
                    severity="blocker",
                    message=(
                        f"Chapter {chapter.chapter_number} is out of order; expected "
                        f"chapter {index}."
                    ),
                    location=location,
                    suggestion="Renumber or reorder chapters to restore continuity.",
                )
            )
        else:
            continuity_checks.setdefault("sequential_chapters", True)

        if not chapter.summary or not chapter.summary.strip():
            issues.append(
                StoryReviewIssue(
                    code="missing_summary",
                    severity="blocker",
                    message="The chapter summary is missing.",
                    location=location,
                    suggestion="Add a concise summary to keep the outline coherent.",
                )
            )

        if chapter.scene_count == 0:
            issues.append(
                StoryReviewIssue(
                    code="empty_chapter",
                    severity="blocker",
                    message="The chapter does not contain any scenes.",
                    location=location,
                    suggestion="Draft or repair the chapter scenes before publishing.",
                )
            )
            return

        if any(not scene.content.strip() for scene in chapter.scenes):
            issues.append(
                StoryReviewIssue(
                    code="empty_scene",
                    severity="blocker",
                    message="At least one scene is empty.",
                    location=location,
                    suggestion="Regenerate or rewrite the empty scene.",
                )
            )

        if len({scene.title for scene in chapter.scenes}) != len(chapter.scenes):
            issues.append(
                StoryReviewIssue(
                    code="duplicate_scene_title",
                    severity="warning",
                    message="Two or more scenes share the same title.",
                    location=location,
                    suggestion="Give each scene a distinct beat label.",
                )
            )

        focus_character = str(chapter.metadata.get("focus_character", "")).strip()
        if focus_character:
            if not any(
                focus_character.lower() in scene.content.lower()
                for scene in chapter.scenes
            ):
                continuity_checks["character_alignment"] = False
                issues.append(
                    StoryReviewIssue(
                        code="character_drift",
                        severity="blocker",
                        message=(
                            f"The focus character '{focus_character}' does not appear "
                            "in the chapter scenes."
                        ),
                        location=location,
                        suggestion="Re-anchor the chapter around the intended focal character.",
                    )
                )
        else:
            issues.append(
                StoryReviewIssue(
                    code="missing_focus_character",
                    severity="warning",
                    message="The chapter has no focus character metadata.",
                    location=location,
                    suggestion="Store the focus character in chapter metadata during drafting.",
                )
            )

        focus_motivation = self._focus_character_motivation(
            story,
            focus_character,
            chapter,
        )
        if focus_motivation and not any(
            focus_motivation.lower() in scene.content.lower()
            for scene in chapter.scenes
        ):
            continuity_checks["motivation_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="motivation_drift",
                    severity="blocker",
                    message=(
                        f"The focus character '{focus_character}' no longer reflects "
                        f"the motivation '{focus_motivation}'."
                    ),
                    location=location,
                    suggestion="Rebuild the chapter around the character's driving motive.",
                )
            )

        timeline_day = chapter.metadata.get("timeline_day")
        if timeline_day != chapter.chapter_number:
            continuity_checks["timeline_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="timeline_regression",
                    severity="blocker",
                    message="The chapter timeline metadata is out of sequence.",
                    location=location,
                    suggestion="Reset the chapter timeline marker to match the chapter number.",
                    details={"timeline_day": timeline_day},
                )
            )

        if index < len(story.chapters):
            hook = str(expected_chapter.get("hook", "")).strip()
            current_scene = chapter.current_scene
            current_content = current_scene.content if current_scene else ""
            if hook and not current_content.rstrip().endswith("?") and "hook" not in current_content.lower():
                continuity_checks["hook_alignment"] = False
                issues.append(
                    StoryReviewIssue(
                        code="missing_hook",
                        severity="warning",
                        message="The chapter does not surface its outline hook clearly.",
                        location=location,
                        suggestion="Close the chapter with a stronger cliffhanger or reveal.",
                    )
                )

        if expected_chapter:
            expected_title = str(expected_chapter.get("title", "")).strip()
            if expected_title and expected_title != chapter.title:
                issues.append(
                    StoryReviewIssue(
                        code="outline_mismatch",
                        severity="warning",
                        message="The chapter title diverges from the outline.",
                        location=location,
                        suggestion="Align the drafted chapter title with the outline.",
                    )
                )

    def _issues_from_payload(self, payload: dict[str, Any]) -> list[StoryReviewIssue]:
        issues: list[StoryReviewIssue] = []
        for issue_payload in payload.get("issues", []):
            if not isinstance(issue_payload, dict):
                continue
            severity = issue_payload.get("severity", "warning")
            if severity not in {"info", "warning", "blocker"}:
                severity = "warning"
            issues.append(
                StoryReviewIssue(
                    code=str(issue_payload.get("code", "unknown")),
                    severity=cast(ReviewSeverity, severity),
                    message=str(issue_payload.get("message", "")),
                    location=issue_payload.get("location"),
                    suggestion=issue_payload.get("suggestion"),
                    details=issue_payload.get("details", {})
                    if isinstance(issue_payload.get("details"), dict)
                    else {},
                )
            )
        return issues

    def _extract_revision_notes(
        self,
        result: TextGenerationResult,
    ) -> list[str]:
        revision_notes = result.content.get("revision_notes")
        if not isinstance(revision_notes, list) or not revision_notes:
            raise ValueError("Revision payload missing revision_notes")
        notes: list[str] = []
        for note in revision_notes:
            text = str(note).strip()
            if text:
                notes.append(text)
        if not notes:
            raise ValueError("Revision notes cannot be empty")
        return notes

    async def revise_story(self, story_id: str) -> Result[dict[str, Any]]:
        """Apply a revision pass to repair obvious continuity issues."""
        review_result = await self.review_story(story_id)
        if isinstance(review_result, Failure):
            return review_result

        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        review_payload = review_result.value["report"]
        workflow = self._workflow(story)
        outline = workflow.get("outline")
        outline_chapters = self._outline_chapters(outline)
        issues = self._issues_from_payload(review_payload)
        revision_notes: list[str] = []

        try:
            task = TextGenerationTask(
                step="revision",
                system_prompt=(
                    "You repair story structure, continuity, pacing, and hooks. "
                    "Return concise revision notes."
                ),
                user_prompt=(
                    f"Story title: {story.title}\n"
                    f"Review issues: {review_payload['issues']}\n"
                    f"Revision target: strengthen continuity and hooks."
                ),
                response_schema={
                    "revision_notes": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                temperature=0.2,
                metadata={
                    "story_id": str(story.id),
                    "issue_count": len(issues),
                    "chapter_count": story.chapter_count,
                },
            )
            result = await self._provider.generate_structured(task)
            revision_notes = self._extract_revision_notes(result)
            self._record_generation_trace(workflow, result)
        except TextGenerationProviderError as exc:
            return Failure(str(exc), "GENERATION_ERROR")
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

        repair_notes = await self._repair_story(story, outline_chapters, issues)
        revision_notes.extend(repair_notes)

        workflow["revision_notes"] = revision_notes
        workflow["revision_history"] = workflow.get("revision_history", []) + [
            {
                "timestamp": self._now(),
                "notes": revision_notes,
                "issue_count": len(issues),
            }
        ]
        workflow["status"] = "revised"
        self._memory(story)["revision_notes"] = revision_notes
        self._touch(story)
        await self._story_repository.save(story)
        return Success(
            {
                "story": story.to_dict(),
                "report": review_payload,
                "revision_notes": revision_notes,
            }
        )

    async def _repair_story(
        self,
        story: Story,
        outline_chapters: list[dict[str, Any]],
        issues: list[StoryReviewIssue],
    ) -> list[str]:
        repair_notes: list[str] = []
        outline_map = {
            int(chapter["chapter_number"]): chapter for chapter in outline_chapters
        }

        for chapter in story.chapters:
            chapter_spec = outline_map.get(chapter.chapter_number, {})
            focus_character = self._select_focus_character(story, chapter.chapter_number)
            focus_motivation = self._focus_character_motivation(
                story,
                focus_character,
                chapter,
            )
            location = f"chapter-{chapter.chapter_number}"
            chapter_issues = self._issues_for_location(issues, location)
            if chapter.summary is None or not chapter.summary.strip():
                summary = str(chapter_spec.get("summary", "")).strip()
                if summary:
                    chapter.summary = summary
                    repair_notes.append(
                        f"Restored the summary for chapter {chapter.chapter_number}."
                    )

            if chapter.scene_count == 0 or any(
                not scene.content.strip() for scene in chapter.scenes
            ) or any(
                issue.code in {"character_drift", "motivation_drift"}
                for issue in chapter_issues
            ):
                scene_result = await self._generate_chapter_scenes(
                    story=story,
                    chapter_spec={
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                        "summary": chapter.summary or str(chapter_spec.get("summary", "")),
                        "hook": chapter_spec.get("hook", ""),
                    },
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                )
                scenes = self._extract_scenes(
                    scene_result,
                    {
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                    },
                )
                chapter.scenes.clear()
                self._apply_scene_payload(
                    chapter=chapter,
                    scenes=scenes,
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                    hook=str(chapter_spec.get("hook", "")),
                )
                repair_notes.append(
                    f"Rebuilt the scene stack for chapter {chapter.chapter_number}."
                )

            if chapter.metadata.get("timeline_day") != chapter.chapter_number:
                chapter.metadata["timeline_day"] = chapter.chapter_number
                repair_notes.append(
                    f"Realigned the timeline marker for chapter {chapter.chapter_number}."
                )

            if not chapter.metadata.get("focus_character"):
                chapter.metadata["focus_character"] = focus_character
                repair_notes.append(
                    f"Restored the focus character for chapter {chapter.chapter_number}."
                )

            if chapter.current_scene:
                hook = str(chapter_spec.get("hook", "")).strip()
                if hook and hook.lower() not in chapter.current_scene.content.lower():
                    chapter.current_scene.update_content(
                        self._ensure_hook(chapter.current_scene.content, hook)
                    )
                    repair_notes.append(
                        f"Strengthened the hook for chapter {chapter.chapter_number}."
                    )

        if repair_notes:
            self._touch(story)
            await self._story_repository.save(story)
        return repair_notes

    async def export_story(self, story_id: str) -> Result[dict[str, Any]]:
        """Export a serialisable story snapshot."""
        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        workflow = self._workflow(story)
        export_payload = {
            "story": story.to_dict(),
            "workflow": workflow,
            "memory": self._memory(story),
            "blueprint": workflow.get("blueprint"),
            "outline": workflow.get("outline"),
            "last_review": workflow.get("last_review"),
            "revision_notes": workflow.get("revision_notes", []),
        }
        workflow["last_exported_at"] = self._now()
        workflow["status"] = "exported"
        self._touch(story)
        await self._story_repository.save(story)
        return Success({"story": story.to_dict(), "export": export_payload})

    async def publish_story(self, story_id: str) -> Result[dict[str, Any]]:
        """Publish a story when the quality gate passes."""
        review_result = await self.review_story(story_id)
        if isinstance(review_result, Failure):
            return review_result

        story_or_error = await self._load_story(story_id)
        if isinstance(story_or_error, Failure):
            return story_or_error

        story = story_or_error
        report = review_result.value["report"]
        if not report["ready_for_publish"]:
            return Failure(
                "Story does not pass the publication quality gate",
                "QUALITY_GATE_FAILED",
                details={"report": report},
            )

        try:
            story.publish()
            workflow = self._workflow(story)
            workflow["status"] = "published"
            workflow["published_at"] = self._now()
            self._touch(story)
            await self._story_repository.save(story)
            return Success({"story": story.to_dict(), "report": report})
        except ValueError as exc:
            return Failure(str(exc), "VALIDATION_ERROR")
        except Exception as exc:
            return Failure(str(exc), "INTERNAL_ERROR")

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
        """Run the full novel generation pipeline end to end."""
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

        story_id = create_result.value["story"]["id"]
        blueprint_result = await self.generate_blueprint(story_id)
        if isinstance(blueprint_result, Failure):
            return blueprint_result

        outline_result = await self.generate_outline(story_id)
        if isinstance(outline_result, Failure):
            return outline_result

        draft_result = await self.draft_story(
            story_id,
            target_chapters=target_chapters,
        )
        if isinstance(draft_result, Failure):
            return draft_result

        initial_review = await self.review_story(story_id)
        if isinstance(initial_review, Failure):
            return initial_review

        revision_result = await self.revise_story(story_id)
        if isinstance(revision_result, Failure):
            return revision_result

        final_review = await self.review_story(story_id)
        if isinstance(final_review, Failure):
            return final_review

        export_result = await self.export_story(story_id)
        if isinstance(export_result, Failure):
            return export_result

        publish_result: Result[dict[str, Any]] | None = None
        if publish:
            publish_result = await self.publish_story(story_id)
            if isinstance(publish_result, Failure):
                return publish_result

        final_story_result = await self.get_story(story_id)
        if isinstance(final_story_result, Failure):
            return final_story_result

        artifact = {
            "story": final_story_result.value["story"],
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
        return Success(artifact)

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()


__all__ = ["StoryReviewIssue", "StoryReviewReport", "StoryWorkflowService"]
