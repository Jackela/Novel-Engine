"""Unit Tests for PacingService.

This test suite covers the PacingService which provides chapter-level
pacing analysis for Director Mode.
"""

from uuid import uuid4

import pytest

from src.contexts.narrative.application.services.pacing_service import (
    ChapterPacingReport,
    PacingIssue,
    PacingService,
    ScenePacingMetrics,
)
from src.contexts.narrative.domain.entities.scene import Scene


class TestScenePacingMetrics:
    """Test suite for ScenePacingMetrics dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_metrics(self):
        """Test creating ScenePacingMetrics."""
        scene_id = uuid4()
        metrics = ScenePacingMetrics(
            scene_id=scene_id,
            scene_title="Test Scene",
            order_index=0,
            tension_level=7,
            energy_level=5,
        )

        assert metrics.scene_id == scene_id
        assert metrics.scene_title == "Test Scene"
        assert metrics.order_index == 0
        assert metrics.tension_level == 7
        assert metrics.energy_level == 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_metrics_are_immutable(self):
        """Test that metrics are frozen (immutable)."""
        metrics = ScenePacingMetrics(
            scene_id=uuid4(),
            scene_title="Test",
            order_index=0,
            tension_level=5,
            energy_level=5,
        )

        with pytest.raises(AttributeError):
            metrics.tension_level = 10


class TestPacingIssue:
    """Test suite for PacingIssue dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_pacing_issue(self):
        """Test creating a PacingIssue."""
        scene_ids = [uuid4(), uuid4()]
        issue = PacingIssue(
            issue_type="monotonous_tension",
            description="3 scenes have the same tension",
            affected_scenes=scene_ids,
            severity="medium",
            suggestion="Vary the tension levels",
        )

        assert issue.issue_type == "monotonous_tension"
        assert issue.affected_scenes == scene_ids
        assert issue.severity == "medium"


class TestChapterPacingReport:
    """Test suite for ChapterPacingReport dataclass."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_report(self):
        """Test creating a ChapterPacingReport."""
        chapter_id = uuid4()
        metrics = [
            ScenePacingMetrics(
                scene_id=uuid4(),
                scene_title="Scene 1",
                order_index=0,
                tension_level=5,
                energy_level=6,
            )
        ]
        report = ChapterPacingReport(
            chapter_id=chapter_id,
            scene_metrics=metrics,
            issues=[],
            average_tension=5.0,
            average_energy=6.0,
            tension_range=(5, 5),
            energy_range=(6, 6),
        )

        assert report.chapter_id == chapter_id
        assert len(report.scene_metrics) == 1
        assert report.average_tension == 5.0
        assert report.tension_range == (5, 5)


class TestPacingServiceCalculateChapterPacing:
    """Test suite for PacingService.calculate_chapter_pacing()."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_scenes_returns_empty_report(self):
        """Test that empty scene list returns empty report."""
        service = PacingService()
        chapter_id = uuid4()

        report = service.calculate_chapter_pacing(chapter_id, [])

        assert report.chapter_id == chapter_id
        assert report.scene_metrics == []
        assert report.issues == []
        assert report.average_tension == 0.0
        assert report.average_energy == 0.0
        assert report.tension_range == (0, 0)
        assert report.energy_range == (0, 0)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_single_scene_metrics(self):
        """Test metrics calculation for a single scene."""
        service = PacingService()
        chapter_id = uuid4()
        scene = Scene(
            title="Solo Scene",
            chapter_id=chapter_id,
            order_index=0,
            tension_level=7,
            energy_level=4,
        )

        report = service.calculate_chapter_pacing(chapter_id, [scene])

        assert len(report.scene_metrics) == 1
        assert report.scene_metrics[0].scene_title == "Solo Scene"
        assert report.scene_metrics[0].tension_level == 7
        assert report.scene_metrics[0].energy_level == 4
        assert report.average_tension == 7.0
        assert report.average_energy == 4.0
        assert report.tension_range == (7, 7)
        assert report.energy_range == (4, 4)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_scenes_metrics(self):
        """Test metrics calculation for multiple scenes."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="Opening",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=4,
            ),
            Scene(
                title="Rising Action",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=6,
                energy_level=7,
            ),
            Scene(
                title="Climax",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=9,
                energy_level=10,
            ),
        ]

        report = service.calculate_chapter_pacing(chapter_id, scenes)

        assert len(report.scene_metrics) == 3
        assert report.average_tension == 6.0  # (3+6+9)/3
        assert report.average_energy == 7.0  # (4+7+10)/3
        assert report.tension_range == (3, 9)
        assert report.energy_range == (4, 10)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_scenes_sorted_by_order_index(self):
        """Test that scenes are sorted by order_index in output."""
        service = PacingService()
        chapter_id = uuid4()
        # Create scenes out of order
        scenes = [
            Scene(
                title="Third",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=9,
                energy_level=8,
            ),
            Scene(
                title="First",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=4,
            ),
            Scene(
                title="Second",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=6,
                energy_level=5,
            ),
        ]

        report = service.calculate_chapter_pacing(chapter_id, scenes)

        assert report.scene_metrics[0].scene_title == "First"
        assert report.scene_metrics[1].scene_title == "Second"
        assert report.scene_metrics[2].scene_title == "Third"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_average_tension_rounded(self):
        """Test that average tension is rounded to 2 decimal places."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(title="S1", chapter_id=chapter_id, tension_level=3, energy_level=5),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=5,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=7,
                energy_level=5,
            ),
        ]

        report = service.calculate_chapter_pacing(chapter_id, scenes)

        assert report.average_tension == 5.0  # (3+5+7)/3 = 5.0


class TestPacingServiceAnalyzePacingIssues:
    """Test suite for PacingService.analyze_pacing_issues()."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_no_issues_with_varied_pacing(self):
        """Test that varied pacing produces no issues."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=4,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=6,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=7,
                energy_level=5,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        assert len(issues) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_detect_monotonous_tension(self):
        """Test detection of monotonous tension (3+ same levels)."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=5,
                energy_level=4,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=6,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=5,
                energy_level=7,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        monotony_issues = [i for i in issues if i.issue_type == "monotonous_tension"]
        assert len(monotony_issues) == 1
        assert len(monotony_issues[0].affected_scenes) == 3
        assert "tension level (5)" in monotony_issues[0].description

    @pytest.mark.unit
    @pytest.mark.fast
    def test_detect_monotonous_energy(self):
        """Test detection of monotonous energy (3+ same levels)."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=7,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=7,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=6,
                energy_level=7,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        energy_issues = [i for i in issues if i.issue_type == "monotonous_energy"]
        assert len(energy_issues) == 1
        assert "energy level (7)" in energy_issues[0].description

    @pytest.mark.unit
    @pytest.mark.fast
    def test_monotony_severity_medium_for_three(self):
        """Test that exactly 3 monotonous scenes is medium severity."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=5,
                energy_level=3,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=4,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=5,
                energy_level=5,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        monotony_issues = [i for i in issues if i.issue_type == "monotonous_tension"]
        assert monotony_issues[0].severity == "medium"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_monotony_severity_high_for_more_than_three(self):
        """Test that >3 monotonous scenes is high severity."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title=f"S{i}",
                chapter_id=chapter_id,
                order_index=i,
                tension_level=5,
                energy_level=i + 1,
            )
            for i in range(4)
        ]

        issues = service.analyze_pacing_issues(scenes)

        monotony_issues = [i for i in issues if i.issue_type == "monotonous_tension"]
        assert monotony_issues[0].severity == "high"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_detect_tension_spike(self):
        """Test detection of abrupt tension spike (>4 level change)."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="Calm",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=2,
                energy_level=5,
            ),
            Scene(
                title="Intense",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=8,
                energy_level=5,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        spike_issues = [i for i in issues if i.issue_type == "tension_spike"]
        assert len(spike_issues) == 1
        assert "from 2 to 8" in spike_issues[0].description
        assert len(spike_issues[0].affected_scenes) == 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_detect_energy_spike(self):
        """Test detection of abrupt energy spike (>4 level change)."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="Active",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=5,
                energy_level=9,
            ),
            Scene(
                title="Quiet",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=3,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        spike_issues = [i for i in issues if i.issue_type == "energy_spike"]
        assert len(spike_issues) == 1
        assert "decrease" in spike_issues[0].description

    @pytest.mark.unit
    @pytest.mark.fast
    def test_no_spike_for_four_level_change(self):
        """Test that exactly 4 level change doesn't trigger spike."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=5,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=7,
                energy_level=5,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        spike_issues = [i for i in issues if "spike" in i.issue_type]
        assert len(spike_issues) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_less_than_two_scenes_returns_empty(self):
        """Test that <2 scenes returns no issues."""
        service = PacingService()
        chapter_id = uuid4()

        # Zero scenes
        assert service.analyze_pacing_issues([]) == []

        # One scene
        scene = Scene(title="Only", chapter_id=chapter_id, tension_level=5, energy_level=5)
        assert service.analyze_pacing_issues([scene]) == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_issues_detected(self):
        """Test that multiple different issues can be detected."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="S1",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=5,
                energy_level=5,
            ),
            Scene(
                title="S2",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=5,
            ),
            Scene(
                title="S3",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=5,
                energy_level=5,
            ),
            Scene(
                title="S4",
                chapter_id=chapter_id,
                order_index=3,
                tension_level=10,
                energy_level=10,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        # Should have monotony issues for the first 3 scenes and spike for last transition
        issue_types = {i.issue_type for i in issues}
        assert "monotonous_tension" in issue_types
        assert "monotonous_energy" in issue_types
        assert "tension_spike" in issue_types
        assert "energy_spike" in issue_types

    @pytest.mark.unit
    @pytest.mark.fast
    def test_monotony_at_end_of_chapter(self):
        """Test that monotony at the end of chapter is detected."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="Opening",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=5,
            ),
            Scene(
                title="M1",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=7,
                energy_level=5,
            ),
            Scene(
                title="M2",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=7,
                energy_level=5,
            ),
            Scene(
                title="M3",
                chapter_id=chapter_id,
                order_index=3,
                tension_level=7,
                energy_level=5,
            ),
        ]

        issues = service.analyze_pacing_issues(scenes)

        monotony_issues = [i for i in issues if i.issue_type == "monotonous_tension"]
        assert len(monotony_issues) == 1
        assert len(monotony_issues[0].affected_scenes) == 3


class TestPacingServiceIntegration:
    """Integration tests for PacingService with full reports."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_full_chapter_analysis(self):
        """Test complete chapter pacing analysis."""
        service = PacingService()
        chapter_id = uuid4()
        scenes = [
            Scene(
                title="Opening",
                chapter_id=chapter_id,
                order_index=0,
                tension_level=3,
                energy_level=4,
            ),
            Scene(
                title="Build Up",
                chapter_id=chapter_id,
                order_index=1,
                tension_level=5,
                energy_level=6,
            ),
            Scene(
                title="Tension Rises",
                chapter_id=chapter_id,
                order_index=2,
                tension_level=7,
                energy_level=8,
            ),
            Scene(
                title="Climax",
                chapter_id=chapter_id,
                order_index=3,
                tension_level=9,
                energy_level=10,
            ),
            Scene(
                title="Resolution",
                chapter_id=chapter_id,
                order_index=4,
                tension_level=4,
                energy_level=3,
            ),
        ]

        report = service.calculate_chapter_pacing(chapter_id, scenes)

        # Verify structure
        assert report.chapter_id == chapter_id
        assert len(report.scene_metrics) == 5

        # Verify metrics accuracy
        assert report.average_tension == 5.6  # (3+5+7+9+4)/5
        assert report.average_energy == 6.2  # (4+6+8+10+3)/5
        assert report.tension_range == (3, 9)
        assert report.energy_range == (3, 10)

        # Well-paced chapter should have minimal issues
        # Only the climax->resolution drop might trigger spike
        spike_issues = [i for i in report.issues if "spike" in i.issue_type]
        # Tension drops from 9 to 4 (5 points) and energy from 10 to 3 (7 points)
        assert len(spike_issues) == 2  # Both tension and energy spike

    @pytest.mark.unit
    @pytest.mark.fast
    def test_report_contains_scene_ids(self):
        """Test that scene IDs are preserved in metrics."""
        service = PacingService()
        chapter_id = uuid4()
        scene = Scene(title="Test", chapter_id=chapter_id, tension_level=5, energy_level=5)

        report = service.calculate_chapter_pacing(chapter_id, [scene])

        assert report.scene_metrics[0].scene_id == scene.id
