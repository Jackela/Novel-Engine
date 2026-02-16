"""Unit Tests for ChapterAnalysisService.

This test suite covers the ChapterAnalysisService which provides
structural health analysis for Director Mode chapters.
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.application.services.chapter_analysis_service import (
    ChapterAnalysisService,
    HealthScore,
    HealthWarning,
    PhaseDistribution,
    TensionArcShape,
    WarningCategory,
    WordCountEstimate,
)
from src.contexts.narrative.domain.entities.beat import Beat, BeatType
from src.contexts.narrative.domain.entities.scene import Scene, SceneStatus, StoryPhase

pytestmark = pytest.mark.unit


class TestPhaseDistribution:
    """Test suite for PhaseDistribution dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_phase_distribution(self):
        """Test creating PhaseDistribution."""
        dist = PhaseDistribution(
            setup=2,
            inciting_incident=1,
            rising_action=3,
            climax=1,
            resolution=1,
        )

        assert dist.setup == 2
        assert dist.inciting_incident == 1
        assert dist.rising_action == 3
        assert dist.climax == 1
        assert dist.resolution == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_phase_distribution_is_immutable(self):
        """Test that PhaseDistribution is frozen."""
        dist = PhaseDistribution(1, 0, 1, 1, 0)

        with pytest.raises(AttributeError):
            dist.setup = 5


class TestWordCountEstimate:
    """Test suite for WordCountEstimate dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_word_count_estimate(self):
        """Test creating WordCountEstimate."""
        estimate = WordCountEstimate(
            total_words=5000,
            min_words=4000,
            max_words=6000,
            per_scene_average=500.0,
        )

        assert estimate.total_words == 5000
        assert estimate.min_words == 4000
        assert estimate.max_words == 6000
        assert estimate.per_scene_average == 500.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_estimate_is_immutable(self):
        """Test that WordCountEstimate is frozen."""
        estimate = WordCountEstimate(1000, 800, 1200, 100.0)

        with pytest.raises(AttributeError):
            estimate.total_words = 2000


class TestHealthWarning:
    """Test suite for HealthWarning dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_health_warning(self):
        """Test creating HealthWarning."""
        scene_id = uuid4()
        warning = HealthWarning(
            category=WarningCategory.STRUCTURE,
            title="Missing Climax",
            description="No climax scenes",
            severity="high",
            affected_scenes=[scene_id],
            recommendation="Add a climax",
        )

        assert warning.category == WarningCategory.STRUCTURE
        assert warning.title == "Missing Climax"
        assert warning.severity == "high"
        assert warning.affected_scenes == [scene_id]


class TestTensionArcShape:
    """Test suite for TensionArcShape dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_tension_arc_shape(self):
        """Test creating TensionArcShape."""
        arc = TensionArcShape(
            shape_type="mountain",
            starts_at=3,
            peaks_at=9,
            ends_at=4,
            has_clear_climax=True,
            is_monotonic=False,
        )

        assert arc.shape_type == "mountain"
        assert arc.starts_at == 3
        assert arc.peaks_at == 9
        assert arc.ends_at == 4
        assert arc.has_clear_climax is True
        assert arc.is_monotonic is False


class TestChapterAnalysisService:
    """Test suite for ChapterAnalysisService."""

    @pytest.fixture
    def service(self):
        """Return a ChapterAnalysisService instance."""
        return ChapterAnalysisService()

    @pytest.fixture
    def sample_scene(self):
        """Create a sample scene with beats."""

        def _create(
            title: str,
            order: int,
            phase: StoryPhase,
            tension: int = 5,
            energy: int = 5,
            beat_count: int = 5,
        ) -> Scene:
            scene = Scene(
                title=title,
                chapter_id=uuid4(),
                order_index=order,
                story_phase=phase,
                tension_level=tension,
                energy_level=energy,
                status=SceneStatus.DRAFT,
            )
            # Add beats
            for i in range(beat_count):
                beat = Beat(
                    scene_id=scene.id,
                    content=f"Beat {i}",
                    order_index=i,
                    beat_type=BeatType.ACTION,
                )
                scene.add_beat(beat)
            return scene

        return _create

    # analyze_chapter_structure tests

    @pytest.mark.unit
    @pytest.mark.fast
    def test_analyze_empty_chapter(self, service):
        """Test analysis of chapter with no scenes."""
        chapter_id = uuid4()
        report = service.analyze_chapter_structure(chapter_id, [])

        assert report.chapter_id == chapter_id
        assert report.total_scenes == 0
        assert report.total_beats == 0
        assert report.health_score == HealthScore.FAIR

    @pytest.mark.unit
    @pytest.mark.fast
    def test_analyze_healthy_chapter(self, service, sample_scene):
        """Test analysis of a well-structured chapter."""
        scenes = [
            sample_scene("Opening", 0, StoryPhase.SETUP, tension=3, energy=4),
            sample_scene(
                "Inciting", 1, StoryPhase.INCITING_INCIDENT, tension=5, energy=6
            ),
            sample_scene("Rise 1", 2, StoryPhase.RISING_ACTION, tension=6, energy=6),
            sample_scene("Rise 2", 3, StoryPhase.RISING_ACTION, tension=7, energy=7),
            sample_scene("Climax", 4, StoryPhase.CLIMAX, tension=9, energy=8),
            sample_scene("Falling", 5, StoryPhase.RESOLUTION, tension=5, energy=4),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert report.total_scenes == 6
        assert report.total_beats == 30  # 6 scenes * 5 beats
        assert report.health_score in [HealthScore.GOOD, HealthScore.EXCELLENT]
        assert report.phase_distribution.climax == 1
        assert report.phase_distribution.resolution == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_phase_distribution_calculation(self, service, sample_scene):
        """Test phase distribution analysis."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("S2", 1, StoryPhase.SETUP),
            sample_scene("I1", 2, StoryPhase.INCITING_INCIDENT),
            sample_scene("R1", 3, StoryPhase.RISING_ACTION),
            sample_scene("R2", 4, StoryPhase.RISING_ACTION),
            sample_scene("R3", 5, StoryPhase.RISING_ACTION),
            sample_scene("C1", 6, StoryPhase.CLIMAX),
            sample_scene("Res", 7, StoryPhase.RESOLUTION),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert report.phase_distribution.setup == 2
        assert report.phase_distribution.inciting_incident == 1
        assert report.phase_distribution.rising_action == 3
        assert report.phase_distribution.climax == 1
        assert report.phase_distribution.resolution == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_word_count_estimation(self, service, sample_scene):
        """Test word count estimation based on beats."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, beat_count=4),  # 4 beats
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, beat_count=6),  # 6 beats
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # 10 beats * 250 words/beat = 2500 estimated words
        assert report.word_count.total_words == 2500
        assert report.word_count.min_words == 2000  # 80% of 2500
        assert report.word_count.max_words == 3000  # 120% of 2500
        assert report.word_count.per_scene_average == 1250.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_tension_arc_mountain_shape(self, service, sample_scene):
        """Test detection of mountain-shaped tension arc."""
        scenes = [
            sample_scene("Low", 0, StoryPhase.SETUP, tension=3),
            sample_scene("Rising", 1, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("Higher", 2, StoryPhase.RISING_ACTION, tension=7),
            sample_scene("Peak", 3, StoryPhase.CLIMAX, tension=9),
            sample_scene("Falling", 4, StoryPhase.RESOLUTION, tension=4),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert report.tension_arc.shape_type == "mountain"
        assert report.tension_arc.starts_at == 3
        assert report.tension_arc.peaks_at == 9
        assert report.tension_arc.ends_at == 4
        assert report.tension_arc.has_clear_climax is True
        assert report.tension_arc.is_monotonic is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_tension_arc_flat_detection(self, service, sample_scene):
        """Test detection of flat tension arc."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=5),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=5),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert report.tension_arc.shape_type == "flat"
        assert report.tension_arc.is_monotonic is True

    # Warning generation tests

    @pytest.mark.unit
    @pytest.mark.fast
    def test_warning_missing_climax(self, service, sample_scene):
        """Test warning when chapter has no climax."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION),
            sample_scene("S3", 2, StoryPhase.RESOLUTION),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        climax_warnings = [w for w in report.warnings if w.title == "Missing Climax"]
        assert len(climax_warnings) == 1
        assert climax_warnings[0].severity == "high"
        assert climax_warnings[0].category == WarningCategory.STRUCTURE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_warning_missing_resolution(self, service, sample_scene):
        """Test warning when chapter has no resolution."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("S2", 1, StoryPhase.CLIMAX),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        resolution_warnings = [
            w for w in report.warnings if w.title == "Missing Resolution"
        ]
        assert len(resolution_warnings) == 1
        assert resolution_warnings[0].severity == "medium"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_warning_overlong_rising_action(self, service, sample_scene):
        """Test warning when >70% of scenes are rising action."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("R1", 1, StoryPhase.RISING_ACTION),
            sample_scene("R2", 2, StoryPhase.RISING_ACTION),
            sample_scene("R3", 3, StoryPhase.RISING_ACTION),
            sample_scene("R4", 4, StoryPhase.RISING_ACTION),
            sample_scene("R5", 5, StoryPhase.RISING_ACTION),
            sample_scene("R6", 6, StoryPhase.RISING_ACTION),
            sample_scene("R7", 7, StoryPhase.RISING_ACTION),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        rising_warnings = [
            w for w in report.warnings if w.title == "Overlong Rising Action"
        ]
        assert len(rising_warnings) == 1
        assert rising_warnings[0].category == WarningCategory.BALANCE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_warning_flat_tension_arc(self, service, sample_scene):
        """Test warning for flat tension arc with 3+ scenes."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=5),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S4", 3, StoryPhase.CLIMAX, tension=5),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        flat_warnings = [w for w in report.warnings if w.title == "Flat Tension Arc"]
        assert len(flat_warnings) == 1
        assert flat_warnings[0].category == WarningCategory.ARC

    @pytest.mark.unit
    @pytest.mark.fast
    def test_warning_underdeveloped_scenes(self, service, sample_scene):
        """Test warning for scenes with fewer than 3 beats."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, beat_count=5),
            sample_scene(
                "S2", 1, StoryPhase.RISING_ACTION, beat_count=2
            ),  # Underdeveloped
            sample_scene("S3", 2, StoryPhase.CLIMAX, beat_count=1),  # Underdeveloped
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        underdev_warnings = [
            w for w in report.warnings if w.title == "Underdeveloped Scenes"
        ]
        assert len(underdev_warnings) == 1
        assert len(underdev_warnings[0].affected_scenes) == 2

    # Health score calculation tests

    @pytest.mark.unit
    @pytest.mark.fast
    def test_health_score_critical(self, service, sample_scene):
        """Test critical health score with multiple high-severity warnings."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=5),
        ]  # No climax, no resolution = 2 high-severity warnings

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # Missing climax (high) + no resolution (medium) = at least POOR
        assert report.health_score in [HealthScore.CRITICAL, HealthScore.POOR]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_health_score_excellent(self, service, sample_scene):
        """Test excellent health score for well-structured chapter."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=3),
            sample_scene("S2", 1, StoryPhase.INCITING_INCIDENT, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=6),
            sample_scene("S4", 3, StoryPhase.RISING_ACTION, tension=7),
            sample_scene("S5", 4, StoryPhase.CLIMAX, tension=9),
            sample_scene("S6", 5, StoryPhase.RESOLUTION, tension=4),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # Well-structured chapter should have good/excellent score
        assert report.health_score in [HealthScore.GOOD, HealthScore.EXCELLENT]

    # Recommendation tests

    @pytest.mark.unit
    @pytest.mark.fast
    def test_recommendations_generated(self, service, sample_scene):
        """Test that recommendations are generated from warnings."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=5),
        ]  # Missing climax and resolution

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert len(report.recommendations) > 0
        # Check that recommendations reference the issues
        all_recs = " ".join(report.recommendations).lower()
        assert "climax" in all_recs or "resolution" in all_recs

    @pytest.mark.unit
    @pytest.mark.fast
    def test_recommendations_for_healthy_chapter(self, service, sample_scene):
        """Test recommendations for a chapter with no warnings."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=3),
            sample_scene("S2", 1, StoryPhase.INCITING_INCIDENT, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=6),
            sample_scene("S4", 3, StoryPhase.CLIMAX, tension=9),
            sample_scene("S5", 4, StoryPhase.RESOLUTION, tension=4),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # Should have positive recommendation even if no warnings
        assert len(report.recommendations) >= 1

    # Edge case tests

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scenes_sorted_by_order_index(self, service, sample_scene):
        """Test that scenes are analyzed in order_index order, not creation order."""
        scenes = [
            sample_scene("Last", 2, StoryPhase.RESOLUTION, tension=3),
            sample_scene("First", 0, StoryPhase.SETUP, tension=4),
            sample_scene("Middle", 1, StoryPhase.CLIMAX, tension=9),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # Tension arc should reflect sorted order: 4 -> 9 -> 3
        assert report.tension_arc.starts_at == 4
        assert report.tension_arc.peaks_at == 9
        assert report.tension_arc.ends_at == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_zero_beats_word_count(self, service):
        """Test word count estimation for scenes with no beats."""
        from src.contexts.narrative.domain.entities.scene import Scene

        scene1 = Scene(
            title="Empty1",
            chapter_id=uuid4(),
            order_index=0,
            story_phase=StoryPhase.SETUP,
        )
        scene2 = Scene(
            title="Empty2",
            chapter_id=uuid4(),
            order_index=1,
            story_phase=StoryPhase.RISING_ACTION,
        )

        report = service.analyze_chapter_structure(uuid4(), [scene1, scene2])

        assert report.word_count.total_words == 0
        assert report.word_count.per_scene_average == 0.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_phases_represented(self, service, sample_scene):
        """Test analysis when all phases have at least one scene."""
        scenes = [
            sample_scene("Setup", 0, StoryPhase.SETUP),
            sample_scene("Inciting", 1, StoryPhase.INCITING_INCIDENT),
            sample_scene("Rise", 2, StoryPhase.RISING_ACTION),
            sample_scene("Climax", 3, StoryPhase.CLIMAX),
            sample_scene("Resolve", 4, StoryPhase.RESOLUTION),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # All phases should be counted
        assert report.phase_distribution.setup == 1
        assert report.phase_distribution.inciting_incident == 1
        assert report.phase_distribution.rising_action == 1
        assert report.phase_distribution.climax == 1
        assert report.phase_distribution.resolution == 1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_climax_detection_in_final_40_percent(self, service, sample_scene):
        """Test that climax in final 40% is detected."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=3),
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=4),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S4", 3, StoryPhase.RISING_ACTION, tension=6),
            sample_scene(
                "S5", 4, StoryPhase.CLIMAX, tension=9
            ),  # Peak at 80% (5/5 scenes, position 4 >= 3)
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        assert report.tension_arc.has_clear_climax is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_no_clear_climax_peak_too_early(self, service, sample_scene):
        """Test that peak before final 40% is not detected as clear climax."""
        scenes = [
            sample_scene("S1", 0, StoryPhase.SETUP, tension=9),  # Peak at start
            sample_scene("S2", 1, StoryPhase.RISING_ACTION, tension=5),
            sample_scene("S3", 2, StoryPhase.RISING_ACTION, tension=4),
            sample_scene("S4", 3, StoryPhase.RISING_ACTION, tension=3),
            sample_scene("S5", 4, StoryPhase.CLIMAX, tension=7),
        ]

        report = service.analyze_chapter_structure(uuid4(), scenes)

        # Peak (9) is at position 0, which is not in final 60% (positions 3+ for 5 scenes)
        assert report.tension_arc.has_clear_climax is False
