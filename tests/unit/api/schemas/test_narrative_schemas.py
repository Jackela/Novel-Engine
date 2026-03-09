"""
Unit tests for Narrative API Schemas

Tests cover:
- NarrativeData/Response - Basic narrative responses
- SceneGenerationRequest/Response - Scene generation
- WorldContextEntity/WorldContext - World context for generation
- NarrativeStreamRequest/Chunk - Streaming narrative
- Story/Chapter/Scene/Beat CRUD schemas
- Pacing analysis schemas
- Conflict schemas
- Plotline schemas
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


class TestNarrativeData:
    """Tests for NarrativeData schema."""

    def test_valid_narrative_data(self) -> None:
        """Test valid narrative data."""
        from src.api.schemas.narrative_schemas import NarrativeData

        data = NarrativeData(
            story="Once upon a time...",
            participants=["char_001", "char_002"],
            turns_completed=5,
            last_generated="2024-01-15T10:30:00Z",
            has_content=True,
        )

        assert data.story == "Once upon a time..."
        assert data.participants == ["char_001", "char_002"]
        assert data.turns_completed == 5
        assert data.has_content is True

    def test_narrative_data_optional_last_generated(self) -> None:
        """Test narrative data with optional last_generated."""
        from src.api.schemas.narrative_schemas import NarrativeData

        data = NarrativeData(
            story="Story content",
            participants=[],
            turns_completed=0,
            has_content=False,
            last_generated=None,
        )

        assert data.last_generated is None


class TestNarrativeResponse:
    """Tests for NarrativeResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid narrative response."""
        from src.api.schemas.narrative_schemas import NarrativeData, NarrativeResponse

        data = NarrativeData(
            story="Test story",
            participants=["char_001"],
            turns_completed=3,
            has_content=True,
        )

        response = NarrativeResponse(success=True, data=data)

        assert response.success is True
        assert response.data.story == "Test story"


class TestSceneGenerationRequest:
    """Tests for SceneGenerationRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid scene generation request."""
        from src.api.schemas.character_schemas import CharacterGenerationResponse
        from src.api.schemas.narrative_schemas import SceneGenerationRequest

        char_context = CharacterGenerationResponse(
            name="Hero",
            tagline="The Brave",
            bio="A brave warrior",
            visual_prompt="Tall warrior",
            traits=["brave", "strong"],
        )

        request = SceneGenerationRequest(
            character_context=char_context,
            scene_type="opening",
            tone="heroic",
        )

        assert request.scene_type == "opening"
        assert request.tone == "heroic"


class TestSceneGenerationResponse:
    """Tests for SceneGenerationResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid scene generation response."""
        from src.api.schemas.narrative_schemas import SceneGenerationResponse

        response = SceneGenerationResponse(
            title="The Beginning",
            content="# The Beginning\n\nThe hero stood...",
            summary="Hero enters the village",
            visual_prompt="A village at sunset",
        )

        assert response.title == "The Beginning"
        assert "The hero stood" in response.content
        assert response.summary == "Hero enters the village"


class TestWorldContextEntity:
    """Tests for WorldContextEntity schema."""

    def test_valid_entity(self) -> None:
        """Test valid world context entity."""
        from src.api.schemas.narrative_schemas import WorldContextEntity

        entity = WorldContextEntity(
            id="char_001",
            name="Hero",
            type="character",
            description="A brave warrior",
            attributes={"strength": "high", "class": "warrior"},
        )

        assert entity.id == "char_001"
        assert entity.type == "character"
        assert entity.attributes["strength"] == "high"

    def test_entity_defaults(self) -> None:
        """Test default values for entity."""
        from src.api.schemas.narrative_schemas import WorldContextEntity

        entity = WorldContextEntity(
            id="loc_001",
            name="Village",
            type="location",
        )

        assert entity.description == ""
        assert entity.attributes == {}


class TestWorldContext:
    """Tests for WorldContext schema."""

    def test_valid_context(self) -> None:
        """Test valid world context."""
        from src.api.schemas.narrative_schemas import WorldContext, WorldContextEntity

        char = WorldContextEntity(id="char_001", name="Hero", type="character")
        loc = WorldContextEntity(id="loc_001", name="Village", type="location")
        item = WorldContextEntity(id="item_001", name="Sword", type="item")

        context = WorldContext(
            characters=[char],
            locations=[loc],
            entities=[item],
            current_scene="The hero enters the village",
            narrative_style="descriptive",
        )

        assert len(context.characters) == 1
        assert len(context.locations) == 1
        assert len(context.entities) == 1
        assert context.current_scene == "The hero enters the village"

    def test_context_defaults(self) -> None:
        """Test default values for world context."""
        from src.api.schemas.narrative_schemas import WorldContext

        context = WorldContext()

        assert context.characters == []
        assert context.locations == []
        assert context.entities == []
        assert context.current_scene is None
        assert context.narrative_style is None


class TestNarrativeStreamRequest:
    """Tests for NarrativeStreamRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid stream request."""
        from src.api.schemas.narrative_schemas import (
            NarrativeStreamRequest,
            WorldContext,
        )

        request = NarrativeStreamRequest(
            prompt="Write an opening scene",
            world_context=WorldContext(),
            chapter_title="Chapter 1",
            tone="mysterious",
            max_tokens=2000,
        )

        assert request.prompt == "Write an opening scene"
        assert request.max_tokens == 2000

    def test_request_validation(self) -> None:
        """Test request validation."""
        from src.api.schemas.narrative_schemas import (
            NarrativeStreamRequest,
            WorldContext,
        )

        # Too many tokens
        with pytest.raises(ValidationError) as exc_info:
            NarrativeStreamRequest(
                prompt="Test",
                world_context=WorldContext(),
                max_tokens=9000,
            )
        assert "less than or equal to 8000" in str(exc_info.value)

        # Too few tokens
        with pytest.raises(ValidationError) as exc_info:
            NarrativeStreamRequest(
                prompt="Test",
                world_context=WorldContext(),
                max_tokens=50,
            )
        assert "greater than or equal to 100" in str(exc_info.value)

        # Empty prompt
        with pytest.raises(ValidationError) as exc_info:
            NarrativeStreamRequest(
                prompt="",
                world_context=WorldContext(),
            )
        assert "String should have at least 1 character" in str(exc_info.value)


class TestNarrativeStreamChunk:
    """Tests for NarrativeStreamChunk schema."""

    def test_valid_chunk(self) -> None:
        """Test valid stream chunk."""
        from src.api.schemas.narrative_schemas import NarrativeStreamChunk

        chunk = NarrativeStreamChunk(
            type="chunk",
            content="The hero stepped forward.",
            sequence=1,
        )

        assert chunk.type == "chunk"
        assert chunk.content == "The hero stepped forward."
        assert chunk.sequence == 1

    def test_chunk_defaults(self) -> None:
        """Test default values for chunk."""
        from src.api.schemas.narrative_schemas import NarrativeStreamChunk

        chunk = NarrativeStreamChunk(type="done", content="")

        assert chunk.sequence == 0


class TestStorySchemas:
    """Tests for Story CRUD schemas."""

    def test_story_create_request(self) -> None:
        """Test story creation request."""
        from src.api.schemas.narrative_schemas import StoryCreateRequest

        request = StoryCreateRequest(
            title="The Great Adventure",
            summary="A hero's journey through dangerous lands.",
        )

        assert request.title == "The Great Adventure"
        assert request.summary == "A hero's journey through dangerous lands."

    def test_story_create_validation(self) -> None:
        """Test story creation validation."""
        from src.api.schemas.narrative_schemas import StoryCreateRequest

        # Empty title
        with pytest.raises(ValidationError) as exc_info:
            StoryCreateRequest(title="")
        assert "String should have at least 1 character" in str(exc_info.value)

        # Title too long
        with pytest.raises(ValidationError) as exc_info:
            StoryCreateRequest(title="x" * 201)
        assert "at most 200" in str(exc_info.value)

    def test_story_update_request(self) -> None:
        """Test story update request."""
        from src.api.schemas.narrative_schemas import StoryUpdateRequest

        request = StoryUpdateRequest(
            title="Updated Title",
            status="published",
        )

        assert request.title == "Updated Title"
        assert request.status == "published"

    def test_story_response(self) -> None:
        """Test story response."""
        from src.api.schemas.narrative_schemas import StoryResponse

        response = StoryResponse(
            id="story_001",
            title="The Adventure",
            summary="A great story",
            status="draft",
            chapter_count=5,
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T11:30:00Z",
        )

        assert response.id == "story_001"
        assert response.chapter_count == 5


class TestChapterSchemas:
    """Tests for Chapter CRUD schemas."""

    def test_chapter_create_request(self) -> None:
        """Test chapter creation request."""
        from src.api.schemas.narrative_schemas import ChapterCreateRequest

        request = ChapterCreateRequest(
            title="The Beginning",
            summary="Where it all starts",
            order_index=0,
        )

        assert request.title == "The Beginning"
        assert request.order_index == 0

    def test_chapter_create_validation(self) -> None:
        """Test chapter creation validation."""
        from src.api.schemas.narrative_schemas import ChapterCreateRequest

        # Negative order index
        with pytest.raises(ValidationError) as exc_info:
            ChapterCreateRequest(title="Test", order_index=-1)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_chapter_response(self) -> None:
        """Test chapter response."""
        from src.api.schemas.narrative_schemas import ChapterResponse

        response = ChapterResponse(
            id="chap_001",
            story_id="story_001",
            title="Chapter 1",
            summary="The beginning",
            order_index=0,
            status="draft",
            scene_count=3,
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T11:30:00Z",
        )

        assert response.scene_count == 3
        assert response.order_index == 0


class TestSceneSchemas:
    """Tests for Scene CRUD schemas."""

    def test_scene_create_request(self) -> None:
        """Test scene creation request."""
        from src.api.schemas.narrative_schemas import SceneCreateRequest

        request = SceneCreateRequest(
            title="The Market",
            summary="Hero visits the market",
            location="Town Square",
            order_index=0,
            story_phase="setup",
        )

        assert request.location == "Town Square"
        assert request.story_phase == "setup"

    def test_scene_create_defaults(self) -> None:
        """Test scene creation defaults."""
        from src.api.schemas.narrative_schemas import SceneCreateRequest

        request = SceneCreateRequest(title="Test Scene")

        assert request.summary == ""
        assert request.location == ""
        assert request.story_phase == "setup"

    def test_scene_response(self) -> None:
        """Test scene response."""
        from src.api.schemas.narrative_schemas import SceneResponse

        response = SceneResponse(
            id="scene_001",
            chapter_id="chap_001",
            title="The Market",
            summary="Hero visits market",
            location="Town Square",
            order_index=0,
            status="draft",
            story_phase="setup",
            beat_count=5,
            created_at="2024-01-15T10:30:00Z",
            updated_at="2024-01-15T11:30:00Z",
        )

        assert response.beat_count == 5
        assert response.story_phase == "setup"


class TestBeatSchemas:
    """Tests for Beat CRUD schemas."""

    def test_beat_create_request(self) -> None:
        """Test beat creation request."""
        from src.api.schemas.narrative_schemas import BeatCreateRequest

        request = BeatCreateRequest(
            content="The hero draws his sword.",
            beat_type="action",
            mood_shift=2,
            order_index=0,
        )

        assert request.beat_type == "action"
        assert request.mood_shift == 2

    def test_beat_create_defaults(self) -> None:
        """Test beat creation defaults."""
        from src.api.schemas.narrative_schemas import BeatCreateRequest

        request = BeatCreateRequest()

        assert request.beat_type == "action"
        assert request.mood_shift == 0

    def test_beat_mood_shift_validation(self) -> None:
        """Test mood shift validation (-5 to +5)."""
        from src.api.schemas.narrative_schemas import BeatCreateRequest

        # Too low
        with pytest.raises(ValidationError) as exc_info:
            BeatCreateRequest(mood_shift=-6)
        assert "greater than or equal to -5" in str(exc_info.value)

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            BeatCreateRequest(mood_shift=6)
        assert "less than or equal to 5" in str(exc_info.value)


class TestBeatSuggestionSchemas:
    """Tests for beat suggestion schemas."""

    def test_beat_suggestion_request(self) -> None:
        """Test beat suggestion request."""
        from src.api.schemas.narrative_schemas import BeatSuggestionRequest

        request = BeatSuggestionRequest(
            scene_id="scene_001",
            scene_context="Hero confronts villain",
            mood_target=3,
        )

        assert request.scene_id == "scene_001"
        assert request.mood_target == 3

    def test_beat_suggestion(self) -> None:
        """Test beat suggestion."""
        from src.api.schemas.narrative_schemas import BeatSuggestion

        suggestion = BeatSuggestion(
            beat_type="dialogue",
            content="'You shall not pass!' the hero shouts.",
            mood_shift=3,
            rationale="Raises tension for confrontation",
        )

        assert suggestion.beat_type == "dialogue"
        assert suggestion.mood_shift == 3


class TestPacingSchemas:
    """Tests for pacing analysis schemas."""

    def test_scene_pacing_metrics(self) -> None:
        """Test scene pacing metrics."""
        from src.api.schemas.narrative_schemas import ScenePacingMetricsResponse

        metrics = ScenePacingMetricsResponse(
            scene_id="scene_001",
            scene_title="The Chase",
            order_index=2,
            tension_level=8,
            energy_level=9,
        )

        assert metrics.tension_level == 8
        assert metrics.energy_level == 9

    def test_pacing_metrics_validation(self) -> None:
        """Test pacing metrics validation (1-10)."""
        from src.api.schemas.narrative_schemas import ScenePacingMetricsResponse

        with pytest.raises(ValidationError) as exc_info:
            ScenePacingMetricsResponse(
                scene_id="s001",
                scene_title="Test",
                order_index=0,
                tension_level=0,  # Too low
                energy_level=5,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_chapter_pacing_response(self) -> None:
        """Test chapter pacing response."""
        from src.api.schemas.narrative_schemas import (
            ChapterPacingResponse,
            ScenePacingMetricsResponse,
        )

        metrics = ScenePacingMetricsResponse(
            scene_id="s001",
            scene_title="Scene 1",
            order_index=0,
            tension_level=5,
            energy_level=6,
        )

        response = ChapterPacingResponse(
            chapter_id="chap_001",
            scene_metrics=[metrics],
            average_tension=5.5,
            average_energy=6.0,
            tension_range=[3, 8],
            energy_range=[4, 9],
        )

        assert response.average_tension == 5.5
        assert response.tension_range == [3, 8]


class TestConflictSchemas:
    """Tests for conflict schemas."""

    def test_conflict_create_request(self) -> None:
        """Test conflict creation request."""
        from src.api.schemas.narrative_schemas import ConflictCreateRequest

        request = ConflictCreateRequest(
            conflict_type="external",
            stakes="high",
            description="The hero must defeat the villain to save the kingdom.",
            resolution_status="unresolved",
        )

        assert request.conflict_type == "external"
        assert request.stakes == "high"

    def test_conflict_create_defaults(self) -> None:
        """Test conflict creation defaults."""
        from src.api.schemas.narrative_schemas import ConflictCreateRequest

        request = ConflictCreateRequest(
            conflict_type="external",
            description="Test conflict",
        )

        assert request.stakes == "medium"
        assert request.resolution_status == "unresolved"


class TestPlotlineSchemas:
    """Tests for plotline schemas."""

    def test_plotline_create_request(self) -> None:
        """Test plotline creation request."""
        from src.api.schemas.narrative_schemas import PlotlineCreateRequest

        request = PlotlineCreateRequest(
            name="The Hero's Journey",
            color="#ff5733",
            description="Main character development arc",
            status="active",
        )

        assert request.name == "The Hero's Journey"
        assert request.color == "#ff5733"

    def test_plotline_color_validation(self) -> None:
        """Test plotline color hex validation."""
        from src.api.schemas.narrative_schemas import PlotlineCreateRequest

        # Valid hex colors
        for color in ["#ff5733", "#FFF", "#123ABC", "#a1b2c3"]:
            request = PlotlineCreateRequest(name="Test", color=color)
            assert request.color == color

        # Invalid hex color
        with pytest.raises(ValidationError) as exc_info:
            PlotlineCreateRequest(name="Test", color="red")
        assert "String should match pattern" in str(exc_info.value)


class TestChapterHealthSchemas:
    """Tests for chapter health analysis schemas."""

    def test_phase_distribution_response(self) -> None:
        """Test phase distribution response."""
        from src.api.schemas.narrative_schemas import PhaseDistributionResponse

        distribution = PhaseDistributionResponse(
            setup=2,
            inciting_incident=1,
            rising_action=3,
            climax=1,
            resolution=1,
        )

        assert distribution.setup == 2
        assert distribution.rising_action == 3

    def test_chapter_health_report(self) -> None:
        """Test chapter health report."""
        from src.api.schemas.narrative_schemas import (
            ChapterHealthReportResponse,
            PhaseDistributionResponse,
            TensionArcShapeResponse,
            WordCountEstimateResponse,
        )

        report = ChapterHealthReportResponse(
            chapter_id="chap_001",
            health_score="good",
            phase_distribution=PhaseDistributionResponse(
                setup=2, inciting_incident=1, rising_action=3, climax=1, resolution=1
            ),
            word_count=WordCountEstimateResponse(
                total_words=5000, min_words=4500, max_words=5500, per_scene_average=1000
            ),
            total_scenes=5,
            total_beats=25,
            tension_arc=TensionArcShapeResponse(
                shape_type="rising",
                starts_at=3,
                peaks_at=9,
                ends_at=7,
                has_clear_climax=True,
                is_monotonic=False,
            ),
        )

        assert report.health_score == "good"
        assert report.total_scenes == 5
        assert report.tension_arc.has_clear_climax is True


class TestCritiqueSchemas:
    """Tests for scene critique schemas."""

    def test_critique_scene_request(self) -> None:
        """Test critique scene request."""
        from src.api.schemas.narrative_schemas import CritiqueSceneRequest

        request = CritiqueSceneRequest(
            scene_text="The hero walked into the room and looked around carefully, taking in every detail of the ancient chamber.",
            scene_goals=["Establish tension", "Introduce villain"],
        )

        assert len(request.scene_text) >= 50
        assert request.scene_goals == ["Establish tension", "Introduce villain"]

    def test_critique_scene_request_validation(self) -> None:
        """Test critique scene request validation."""
        from src.api.schemas.narrative_schemas import CritiqueSceneRequest

        # Too short
        with pytest.raises(ValidationError) as exc_info:
            CritiqueSceneRequest(scene_text="Too short")
        assert "String should have at least 50 characters" in str(exc_info.value)

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            CritiqueSceneRequest(scene_text="x" * 12001)
        assert "String should have at most 12000 characters" in str(exc_info.value)

    def test_critique_scene_response(self) -> None:
        """Test critique scene response."""
        from src.api.schemas.narrative_schemas import (
            CritiqueCategoryScoreResponse,
            CritiqueSceneResponse,
        )

        category = CritiqueCategoryScoreResponse(
            category="pacing",
            score=8,
            issues=["Slow in middle"],
            suggestions=["Tighten dialogue"],
        )

        response = CritiqueSceneResponse(
            overall_score=7,
            category_scores=[category],
            highlights=["Strong opening", "Good imagery"],
            summary="A solid scene with minor pacing issues.",
        )

        assert response.overall_score == 7
        assert len(response.category_scores) == 1


class TestForeshadowingSchemas:
    """Tests for foreshadowing schemas."""

    def test_foreshadowing_create_request(self) -> None:
        """Test foreshadowing creation request."""
        from src.api.schemas.narrative_schemas import ForeshadowingCreateRequest

        request = ForeshadowingCreateRequest(
            setup_scene_id="scene_001",
            description="The mysterious ring glows faintly",
            status="planted",
        )

        assert request.setup_scene_id == "scene_001"
        assert request.status == "planted"

    def test_foreshadowing_defaults(self) -> None:
        """Test foreshadowing default status."""
        from src.api.schemas.narrative_schemas import ForeshadowingCreateRequest

        request = ForeshadowingCreateRequest(
            setup_scene_id="scene_001",
            description="The sword has ancient runes",
        )

        assert request.status == "planted"


class TestMoveSchemas:
    """Tests for move/reorder schemas."""

    def test_move_chapter_request(self) -> None:
        """Test move chapter request."""
        from src.api.schemas.narrative_schemas import MoveChapterRequest

        request = MoveChapterRequest(new_order_index=2)

        assert request.new_order_index == 2

    def test_move_scene_request(self) -> None:
        """Test move scene request."""
        from src.api.schemas.narrative_schemas import MoveSceneRequest

        request = MoveSceneRequest(
            target_chapter_id="chap_002",
            new_order_index=1,
        )

        assert request.target_chapter_id == "chap_002"
        assert request.new_order_index == 1

    def test_reorder_beats_request(self) -> None:
        """Test reorder beats request."""
        from src.api.schemas.narrative_schemas import ReorderBeatsRequest

        request = ReorderBeatsRequest(beat_ids=["beat_003", "beat_001", "beat_002"])

        assert request.beat_ids == ["beat_003", "beat_001", "beat_002"]
