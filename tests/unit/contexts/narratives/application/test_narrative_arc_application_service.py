#!/usr/bin/env python3
"""
Comprehensive Unit Tests for NarrativeArcApplicationService

Test suite covering service initialization, arc lifecycle management,
plot point management, theme management, analysis operations, and search functionality
in the Narrative Context application layer.
"""

from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from contexts.narratives.application.commands.narrative_arc_commands import (
    ActivateContextCommand,
    AddCharacterToArcCommand,
    AddNarrativeContextCommand,
    AddPacingSegmentCommand,
    AddPlotPointCommand,
    AddThemeCommand,
    CompleteNarrativeArcCommand,
    CreateNarrativeArcCommand,
    DeactivateContextCommand,
    DevelopThemeCommand,
    EstablishCausalLinkCommand,
    OptimizeSequenceCommand,
    RemovePlotPointCommand,
    StartNarrativeArcCommand,
    UpdateNarrativeArcCommand,
    UpdatePlotPointCommand,
)
from contexts.narratives.application.queries.narrative_arc_queries import (
    GetArcMetricsQuery,
    GetArcSummaryQuery,
    GetCausalAnalysisQuery,
    GetNarrativeArcQuery,
    GetNarrativeArcsByTypeQuery,
    GetNarrativeFlowAnalysisQuery,
    GetPlotPointQuery,
    GetPlotPointsInSequenceQuery,
    GetThemeQuery,
    GetThemesAtSequenceQuery,
    SearchNarrativeArcsQuery,
)
from contexts.narratives.application.services.narrative_arc_application_service import (
    NarrativeArcApplicationService,
)


class TestNarrativeArcApplicationServiceInitialization:
    """Test suite for NarrativeArcApplicationService initialization."""

    def test_initialization_with_required_repository(self):
        """Test service initialization with required repository."""
        mock_repository = Mock()

        service = NarrativeArcApplicationService(repository=mock_repository)

        assert service.repository == mock_repository
        assert service.flow_service is not None
        assert service.causal_service is not None
        assert service.command_handler is not None
        assert service.query_handler is not None

    def test_initialization_with_all_dependencies(self):
        """Test service initialization with all dependencies provided."""
        mock_repository = Mock()
        mock_flow_service = Mock()
        mock_causal_service = Mock()

        service = NarrativeArcApplicationService(
            repository=mock_repository,
            flow_service=mock_flow_service,
            causal_service=mock_causal_service,
        )

        assert service.repository == mock_repository
        assert service.flow_service == mock_flow_service
        assert service.causal_service == mock_causal_service
        assert service.command_handler is not None
        assert service.query_handler is not None

    @patch(
        "contexts.narratives.application.services.narrative_arc_application_service.NarrativeFlowService"
    )
    @patch(
        "contexts.narratives.application.services.narrative_arc_application_service.CausalGraphService"
    )
    def test_default_service_initialization(
        self, mock_causal_service, mock_flow_service
    ):
        """Test that default services are created when not provided."""
        mock_repository = Mock()
        mock_flow_instance = Mock()
        mock_causal_instance = Mock()
        mock_flow_service.return_value = mock_flow_instance
        mock_causal_service.return_value = mock_causal_instance

        service = NarrativeArcApplicationService(repository=mock_repository)

        mock_flow_service.assert_called_once()
        mock_causal_service.assert_called_once()
        assert service.flow_service == mock_flow_instance
        assert service.causal_service == mock_causal_instance

    @patch(
        "contexts.narratives.application.services.narrative_arc_application_service.logger"
    )
    def test_initialization_logging(self, mock_logger):
        """Test that initialization is logged."""
        mock_repository = Mock()

        NarrativeArcApplicationService(repository=mock_repository)

        mock_logger.info.assert_called_once_with(
            "Narrative Arc Application Service initialized"
        )


class TestArcLifecycleManagement:
    """Test suite for arc lifecycle management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.mock_flow_service = Mock()
        self.mock_causal_service = Mock()
        self.service = NarrativeArcApplicationService(
            repository=self.mock_repository,
            flow_service=self.mock_flow_service,
            causal_service=self.mock_causal_service,
        )

        # Mock handlers
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_create_narrative_arc_minimal_params(self):
        """Test creating narrative arc with minimal parameters."""
        expected_arc_id = "new-arc-123"
        self.service.command_handler.handle_create_narrative_arc.return_value = (
            expected_arc_id
        )

        arc_id = self.service.create_narrative_arc(
            arc_name="Test Arc", arc_type="main", description="A test narrative arc"
        )

        assert arc_id == expected_arc_id

        # Verify command was called correctly
        call_args = self.service.command_handler.handle_create_narrative_arc.call_args[
            0
        ][0]
        assert isinstance(call_args, CreateNarrativeArcCommand)
        assert call_args.arc_name == "Test Arc"
        assert call_args.arc_type == "main"
        assert call_args.description == "A test narrative arc"
        assert call_args.target_length is None
        assert call_args.primary_characters is None
        assert call_args.created_by is None
        assert call_args.tags is None
        assert call_args.notes == ""
        assert call_args.metadata is None

    def test_create_narrative_arc_full_params(self):
        """Test creating narrative arc with all parameters."""
        character_ids = [uuid4(), uuid4()]
        tags = ["action", "adventure"]
        metadata = {"version": "1.0", "priority": "high"}
        created_by = uuid4()

        expected_arc_id = "full-arc-456"
        self.service.command_handler.handle_create_narrative_arc.return_value = (
            expected_arc_id
        )

        arc_id = self.service.create_narrative_arc(
            arc_name="Full Test Arc",
            arc_type="subplot",
            description="A comprehensive test arc",
            target_length=100,
            primary_characters=character_ids,
            created_by=created_by,
            tags=tags,
            notes="Test notes",
            metadata=metadata,
        )

        assert arc_id == expected_arc_id

        call_args = self.service.command_handler.handle_create_narrative_arc.call_args[
            0
        ][0]
        assert call_args.arc_name == "Full Test Arc"
        assert call_args.arc_type == "subplot"
        assert call_args.target_length == 100
        assert call_args.primary_characters == set(character_ids)
        assert call_args.created_by == created_by
        assert call_args.tags == set(tags)
        assert call_args.notes == "Test notes"
        assert call_args.metadata == metadata

    def test_get_narrative_arc(self):
        """Test getting a narrative arc."""
        arc_id = "test-arc-789"
        expected_result = {
            "arc_id": arc_id,
            "arc_name": "Retrieved Arc",
            "arc_type": "main",
            "status": "active",
        }
        self.service.query_handler.handle_get_narrative_arc.return_value = (
            expected_result
        )

        result = self.service.get_narrative_arc(
            arc_id=arc_id, include_details=True, include_events=False
        )

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_narrative_arc.call_args[0][0]
        assert isinstance(call_args, GetNarrativeArcQuery)
        assert call_args.arc_id == arc_id
        assert call_args.include_details is True
        assert call_args.include_events is False

    def test_get_narrative_arc_not_found(self):
        """Test getting a non-existent narrative arc."""
        arc_id = "nonexistent-arc"
        self.service.query_handler.handle_get_narrative_arc.return_value = None

        result = self.service.get_narrative_arc(arc_id=arc_id)

        assert result is None

        call_args = self.service.query_handler.handle_get_narrative_arc.call_args[0][0]
        assert call_args.arc_id == arc_id
        assert call_args.include_details is True  # Default value
        assert call_args.include_events is False  # Default value

    def test_update_narrative_arc(self):
        """Test updating a narrative arc."""
        arc_id = "update-arc-123"
        new_tags = ["updated", "improved"]
        new_metadata = {"version": "2.0"}

        self.service.update_narrative_arc(
            arc_id=arc_id,
            arc_name="Updated Arc Name",
            arc_type="updated_type",
            description="Updated description",
            target_length=150,
            notes="Updated notes",
            tags=new_tags,
            metadata=new_metadata,
        )

        call_args = self.service.command_handler.handle_update_narrative_arc.call_args[
            0
        ][0]
        assert isinstance(call_args, UpdateNarrativeArcCommand)
        assert call_args.arc_id == arc_id
        assert call_args.arc_name == "Updated Arc Name"
        assert call_args.arc_type == "updated_type"
        assert call_args.description == "Updated description"
        assert call_args.target_length == 150
        assert call_args.notes == "Updated notes"
        assert call_args.tags == set(new_tags)
        assert call_args.metadata == new_metadata

    def test_start_narrative_arc(self):
        """Test starting a narrative arc."""
        arc_id = "start-arc-456"
        start_sequence = 10

        self.service.start_narrative_arc(arc_id=arc_id, start_sequence=start_sequence)

        call_args = self.service.command_handler.handle_start_narrative_arc.call_args[
            0
        ][0]
        assert isinstance(call_args, StartNarrativeArcCommand)
        assert call_args.arc_id == arc_id
        assert call_args.start_sequence == start_sequence

    def test_complete_narrative_arc(self):
        """Test completing a narrative arc."""
        arc_id = "complete-arc-789"
        end_sequence = 100

        self.service.complete_narrative_arc(arc_id=arc_id, end_sequence=end_sequence)

        call_args = (
            self.service.command_handler.handle_complete_narrative_arc.call_args[0][0]
        )
        assert isinstance(call_args, CompleteNarrativeArcCommand)
        assert call_args.arc_id == arc_id
        assert call_args.end_sequence == end_sequence


class TestPlotPointManagement:
    """Test suite for plot point management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_add_plot_point_minimal_params(self):
        """Test adding a plot point with minimal parameters."""
        arc_id = "test-arc"
        plot_point_id = "plot-1"

        self.service.add_plot_point(
            arc_id=arc_id,
            plot_point_id=plot_point_id,
            plot_point_type="inciting_incident",
            importance="high",
            title="The Beginning",
            description="Where it all starts",
            sequence_order=5,
        )

        call_args = self.service.command_handler.handle_add_plot_point.call_args[0][0]
        assert isinstance(call_args, AddPlotPointCommand)
        assert call_args.arc_id == arc_id
        assert call_args.plot_point_id == plot_point_id
        assert call_args.plot_point_type == "inciting_incident"
        assert call_args.importance == "high"
        assert call_args.title == "The Beginning"
        assert call_args.description == "Where it all starts"
        assert call_args.sequence_order == 5
        assert call_args.emotional_intensity == Decimal("5.0")
        assert call_args.dramatic_tension == Decimal("5.0")
        assert call_args.story_significance == Decimal("5.0")
        assert call_args.involved_characters is None

    def test_add_plot_point_full_params(self):
        """Test adding a plot point with all parameters."""
        arc_id = "test-arc"
        plot_point_id = "plot-full"
        character_ids = [uuid4(), uuid4()]
        prereq_events = ["event-1", "event-2"]
        consequence_events = ["event-3", "event-4"]
        tags = ["important", "climax"]
        pov_character = uuid4()

        self.service.add_plot_point(
            arc_id=arc_id,
            plot_point_id=plot_point_id,
            plot_point_type="climax",
            importance="critical",
            title="The Climax",
            description="Peak of tension",
            sequence_order=75,
            emotional_intensity=9.5,
            dramatic_tension=10.0,
            story_significance=9.8,
            involved_characters=character_ids,
            prerequisite_events=prereq_events,
            consequence_events=consequence_events,
            location="Castle Throne Room",
            time_context="Midnight",
            pov_character=pov_character,
            outcome="Victory against all odds",
            conflict_type="internal",
            tags=tags,
            notes="Critical story moment",
        )

        call_args = self.service.command_handler.handle_add_plot_point.call_args[0][0]
        assert call_args.arc_id == arc_id
        assert call_args.plot_point_id == plot_point_id
        assert call_args.emotional_intensity == Decimal("9.5")
        assert call_args.dramatic_tension == Decimal("10.0")
        assert call_args.story_significance == Decimal("9.8")
        assert call_args.involved_characters == set(character_ids)
        assert call_args.prerequisite_events == set(prereq_events)
        assert call_args.consequence_events == set(consequence_events)
        assert call_args.location == "Castle Throne Room"
        assert call_args.time_context == "Midnight"
        assert call_args.pov_character == pov_character
        assert call_args.outcome == "Victory against all odds"
        assert call_args.conflict_type == "internal"
        assert call_args.tags == set(tags)
        assert call_args.notes == "Critical story moment"

    def test_get_plot_point(self):
        """Test getting a specific plot point."""
        arc_id = "test-arc"
        plot_point_id = "plot-1"
        expected_result = {
            "plot_point_id": plot_point_id,
            "title": "Retrieved Plot Point",
            "sequence_order": 10,
        }
        self.service.query_handler.handle_get_plot_point.return_value = expected_result

        result = self.service.get_plot_point(arc_id=arc_id, plot_point_id=plot_point_id)

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_plot_point.call_args[0][0]
        assert isinstance(call_args, GetPlotPointQuery)
        assert call_args.arc_id == arc_id
        assert call_args.plot_point_id == plot_point_id

    def test_get_plot_points_in_sequence(self):
        """Test getting plot points in sequence order."""
        arc_id = "test-arc"
        expected_result = [
            {"plot_point_id": "plot-1", "sequence_order": 5},
            {"plot_point_id": "plot-2", "sequence_order": 10},
        ]
        self.service.query_handler.handle_get_plot_points_in_sequence.return_value = (
            expected_result
        )

        result = self.service.get_plot_points_in_sequence(
            arc_id=arc_id, start_sequence=1, end_sequence=20
        )

        assert result == expected_result

        call_args = (
            self.service.query_handler.handle_get_plot_points_in_sequence.call_args[0][
                0
            ]
        )
        assert isinstance(call_args, GetPlotPointsInSequenceQuery)
        assert call_args.arc_id == arc_id
        assert call_args.start_sequence == 1
        assert call_args.end_sequence == 20

    def test_update_plot_point(self):
        """Test updating a plot point."""
        arc_id = "test-arc"
        plot_point_id = "plot-1"

        self.service.update_plot_point(
            arc_id=arc_id,
            plot_point_id=plot_point_id,
            title="Updated Title",
            description="Updated description",
            sequence_order=15,
            emotional_intensity=8.0,
            dramatic_tension=7.5,
            story_significance=9.0,
            outcome="Updated outcome",
            notes="Updated notes",
        )

        call_args = self.service.command_handler.handle_update_plot_point.call_args[0][
            0
        ]
        assert isinstance(call_args, UpdatePlotPointCommand)
        assert call_args.arc_id == arc_id
        assert call_args.plot_point_id == plot_point_id
        assert call_args.title == "Updated Title"
        assert call_args.description == "Updated description"
        assert call_args.sequence_order == 15
        assert call_args.emotional_intensity == Decimal("8.0")
        assert call_args.dramatic_tension == Decimal("7.5")
        assert call_args.story_significance == Decimal("9.0")
        assert call_args.outcome == "Updated outcome"
        assert call_args.notes == "Updated notes"

    def test_update_plot_point_partial(self):
        """Test updating a plot point with partial parameters."""
        arc_id = "test-arc"
        plot_point_id = "plot-1"

        self.service.update_plot_point(
            arc_id=arc_id, plot_point_id=plot_point_id, title="New Title Only"
        )

        call_args = self.service.command_handler.handle_update_plot_point.call_args[0][
            0
        ]
        assert call_args.title == "New Title Only"
        assert call_args.description is None
        assert call_args.sequence_order is None
        assert call_args.emotional_intensity is None

    def test_remove_plot_point(self):
        """Test removing a plot point."""
        arc_id = "test-arc"
        plot_point_id = "plot-to-remove"

        self.service.remove_plot_point(arc_id=arc_id, plot_point_id=plot_point_id)

        call_args = self.service.command_handler.handle_remove_plot_point.call_args[0][
            0
        ]
        assert isinstance(call_args, RemovePlotPointCommand)
        assert call_args.arc_id == arc_id
        assert call_args.plot_point_id == plot_point_id


class TestThemeManagement:
    """Test suite for theme management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_add_theme_minimal_params(self):
        """Test adding a theme with minimal parameters."""
        arc_id = "test-arc"
        theme_id = "theme-1"

        self.service.add_theme(
            arc_id=arc_id,
            theme_id=theme_id,
            theme_type="moral",
            intensity="moderate",
            name="Good vs Evil",
            description="The classic struggle between good and evil",
        )

        call_args = self.service.command_handler.handle_add_theme.call_args[0][0]
        assert isinstance(call_args, AddThemeCommand)
        assert call_args.arc_id == arc_id
        assert call_args.theme_id == theme_id
        assert call_args.theme_type == "moral"
        assert call_args.intensity == "moderate"
        assert call_args.name == "Good vs Evil"
        assert call_args.description == "The classic struggle between good and evil"
        assert call_args.moral_complexity == Decimal("5.0")
        assert call_args.emotional_resonance == Decimal("5.0")
        assert call_args.universal_appeal == Decimal("5.0")
        assert call_args.cultural_significance == Decimal("5.0")
        assert call_args.development_potential == Decimal("5.0")

    def test_add_theme_full_params(self):
        """Test adding a theme with all parameters."""
        arc_id = "test-arc"
        theme_id = "theme-full"
        symbolic_elements = ["light", "darkness", "mirror"]
        tags = ["philosophical", "central"]

        self.service.add_theme(
            arc_id=arc_id,
            theme_id=theme_id,
            theme_type="philosophical",
            intensity="central",
            name="Identity and Self",
            description="Exploration of personal identity",
            moral_complexity=8.5,
            emotional_resonance=9.0,
            universal_appeal=7.5,
            cultural_significance=6.0,
            development_potential=8.0,
            symbolic_elements=symbolic_elements,
            introduction_sequence=5,
            resolution_sequence=95,
            tags=tags,
            notes="Core theme of the narrative",
        )

        call_args = self.service.command_handler.handle_add_theme.call_args[0][0]
        assert call_args.moral_complexity == Decimal("8.5")
        assert call_args.emotional_resonance == Decimal("9.0")
        assert call_args.universal_appeal == Decimal("7.5")
        assert call_args.cultural_significance == Decimal("6.0")
        assert call_args.development_potential == Decimal("8.0")
        assert call_args.symbolic_elements == set(symbolic_elements)
        assert call_args.introduction_sequence == 5
        assert call_args.resolution_sequence == 95
        assert call_args.tags == set(tags)
        assert call_args.notes == "Core theme of the narrative"

    def test_get_theme(self):
        """Test getting a specific theme."""
        arc_id = "test-arc"
        theme_id = "theme-1"
        expected_result = {
            "theme_id": theme_id,
            "name": "Retrieved Theme",
            "intensity": "moderate",
        }
        self.service.query_handler.handle_get_theme.return_value = expected_result

        result = self.service.get_theme(arc_id=arc_id, theme_id=theme_id)

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_theme.call_args[0][0]
        assert isinstance(call_args, GetThemeQuery)
        assert call_args.arc_id == arc_id
        assert call_args.theme_id == theme_id

    def test_get_themes_at_sequence(self):
        """Test getting themes active at a specific sequence."""
        arc_id = "test-arc"
        sequence = 50
        expected_result = [
            {"theme_id": "theme-1", "name": "Theme One"},
            {"theme_id": "theme-2", "name": "Theme Two"},
        ]
        self.service.query_handler.handle_get_themes_at_sequence.return_value = (
            expected_result
        )

        result = self.service.get_themes_at_sequence(arc_id=arc_id, sequence=sequence)

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_themes_at_sequence.call_args[
            0
        ][0]
        assert isinstance(call_args, GetThemesAtSequenceQuery)
        assert call_args.arc_id == arc_id
        assert call_args.sequence == sequence

    def test_develop_theme(self):
        """Test developing a theme at a specific sequence."""
        arc_id = "test-arc"
        theme_id = "theme-1"
        sequence = 30
        development_notes = "Character realizes the truth"

        self.service.develop_theme(
            arc_id=arc_id,
            theme_id=theme_id,
            sequence=sequence,
            development_notes=development_notes,
        )

        call_args = self.service.command_handler.handle_develop_theme.call_args[0][0]
        assert isinstance(call_args, DevelopThemeCommand)
        assert call_args.arc_id == arc_id
        assert call_args.theme_id == theme_id
        assert call_args.sequence == sequence
        assert call_args.development_notes == development_notes


class TestPacingManagement:
    """Test suite for pacing management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()

    def test_add_pacing_segment_minimal_params(self):
        """Test adding a pacing segment with minimal parameters."""
        arc_id = "test-arc"
        pacing_id = "pacing-1"

        self.service.add_pacing_segment(
            arc_id=arc_id,
            pacing_id=pacing_id,
            pacing_type="steady",
            base_intensity="moderate",
            start_sequence=10,
            end_sequence=20,
        )

        call_args = self.service.command_handler.handle_add_pacing_segment.call_args[0][
            0
        ]
        assert isinstance(call_args, AddPacingSegmentCommand)
        assert call_args.arc_id == arc_id
        assert call_args.pacing_id == pacing_id
        assert call_args.pacing_type == "steady"
        assert call_args.base_intensity == "moderate"
        assert call_args.start_sequence == 10
        assert call_args.end_sequence == 20
        assert call_args.event_density == Decimal("5.0")
        assert call_args.dialogue_ratio == Decimal("0.4")
        assert call_args.action_ratio == Decimal("0.3")
        assert call_args.reflection_ratio == Decimal("0.3")

    def test_add_pacing_segment_full_params(self):
        """Test adding a pacing segment with all parameters."""
        arc_id = "test-arc"
        pacing_id = "pacing-full"
        tension_curve = [3.0, 7.0, 9.0, 5.0]
        character_focus = [uuid4(), uuid4()]
        narrative_techniques = ["foreshadowing", "flashback"]
        tags = ["climactic", "intense"]

        self.service.add_pacing_segment(
            arc_id=arc_id,
            pacing_id=pacing_id,
            pacing_type="crescendo",
            base_intensity="fast",
            start_sequence=50,
            end_sequence=60,
            event_density=8.5,
            tension_curve=tension_curve,
            dialogue_ratio=0.2,
            action_ratio=0.6,
            reflection_ratio=0.2,
            description_density=7.0,
            character_focus=character_focus,
            narrative_techniques=narrative_techniques,
            reader_engagement_target="High tension and excitement",
            tags=tags,
            notes="Climactic battle sequence",
        )

        call_args = self.service.command_handler.handle_add_pacing_segment.call_args[0][
            0
        ]
        assert call_args.event_density == Decimal("8.5")
        assert call_args.tension_curve == [
            Decimal("3.0"),
            Decimal("7.0"),
            Decimal("9.0"),
            Decimal("5.0"),
        ]
        assert call_args.dialogue_ratio == Decimal("0.2")
        assert call_args.action_ratio == Decimal("0.6")
        assert call_args.reflection_ratio == Decimal("0.2")
        assert call_args.description_density == Decimal("7.0")
        assert call_args.character_focus == set(character_focus)
        assert call_args.narrative_techniques == set(narrative_techniques)
        assert call_args.reader_engagement_target == "High tension and excitement"
        assert call_args.tags == set(tags)
        assert call_args.notes == "Climactic battle sequence"


class TestContextManagement:
    """Test suite for context management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()

    def test_add_narrative_context_minimal_params(self):
        """Test adding a narrative context with minimal parameters."""
        arc_id = "test-arc"
        context_id = "context-1"

        self.service.add_narrative_context(
            arc_id=arc_id,
            context_id=context_id,
            context_type="setting",
            name="Castle Courtyard",
            description="A stone courtyard within the castle walls",
        )

        call_args = self.service.command_handler.handle_add_narrative_context.call_args[
            0
        ][0]
        assert isinstance(call_args, AddNarrativeContextCommand)
        assert call_args.arc_id == arc_id
        assert call_args.context_id == context_id
        assert call_args.context_type == "setting"
        assert call_args.name == "Castle Courtyard"
        assert call_args.description == "A stone courtyard within the castle walls"
        assert call_args.importance == Decimal("5.0")
        assert call_args.is_persistent is False

    def test_add_narrative_context_full_params(self):
        """Test adding a narrative context with all parameters."""
        arc_id = "test-arc"
        context_id = "context-full"
        affected_characters = [uuid4(), uuid4()]
        related_themes = ["theme-1", "theme-2"]
        tags = ["important", "recurring"]

        self.service.add_narrative_context(
            arc_id=arc_id,
            context_id=context_id,
            context_type="cultural",
            name="Royal Court Politics",
            description="Complex political dynamics of the royal court",
            importance=8.5,
            is_persistent=True,
            start_sequence=10,
            end_sequence=90,
            location="Royal Palace",
            time_period="Medieval Era",
            mood="Tense and suspicious",
            atmosphere="Formal but threatening",
            social_context="Nobility and servants",
            cultural_context="Feudal hierarchy",
            affected_characters=affected_characters,
            related_themes=related_themes,
            tags=tags,
            notes="Central to the political intrigue subplot",
        )

        call_args = self.service.command_handler.handle_add_narrative_context.call_args[
            0
        ][0]
        assert call_args.importance == Decimal("8.5")
        assert call_args.is_persistent is True
        assert call_args.start_sequence == 10
        assert call_args.end_sequence == 90
        assert call_args.location == "Royal Palace"
        assert call_args.time_period == "Medieval Era"
        assert call_args.mood == "Tense and suspicious"
        assert call_args.atmosphere == "Formal but threatening"
        assert call_args.social_context == "Nobility and servants"
        assert call_args.cultural_context == "Feudal hierarchy"
        assert call_args.affected_characters == set(affected_characters)
        assert call_args.related_themes == set(related_themes)
        assert call_args.tags == set(tags)
        assert call_args.notes == "Central to the political intrigue subplot"

    def test_activate_context(self):
        """Test activating a narrative context."""
        arc_id = "test-arc"
        context_id = "context-1"

        self.service.activate_context(arc_id=arc_id, context_id=context_id)

        call_args = self.service.command_handler.handle_activate_context.call_args[0][0]
        assert isinstance(call_args, ActivateContextCommand)
        assert call_args.arc_id == arc_id
        assert call_args.context_id == context_id

    def test_deactivate_context(self):
        """Test deactivating a narrative context."""
        arc_id = "test-arc"
        context_id = "context-1"

        self.service.deactivate_context(arc_id=arc_id, context_id=context_id)

        call_args = self.service.command_handler.handle_deactivate_context.call_args[0][
            0
        ]
        assert isinstance(call_args, DeactivateContextCommand)
        assert call_args.arc_id == arc_id
        assert call_args.context_id == context_id


class TestCharacterManagement:
    """Test suite for character management methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()

    def test_add_character_to_arc(self):
        """Test adding a character to a narrative arc."""
        arc_id = "test-arc"
        character_id = uuid4()

        self.service.add_character_to_arc(
            arc_id=arc_id,
            character_id=character_id,
            role="protagonist",
            character_arc_notes="Main character development notes",
        )

        call_args = self.service.command_handler.handle_add_character_to_arc.call_args[
            0
        ][0]
        assert isinstance(call_args, AddCharacterToArcCommand)
        assert call_args.arc_id == arc_id
        assert call_args.character_id == character_id
        assert call_args.role == "protagonist"
        assert call_args.character_arc_notes == "Main character development notes"

    def test_add_character_to_arc_minimal(self):
        """Test adding a character to arc with minimal parameters."""
        arc_id = "test-arc"
        character_id = uuid4()

        self.service.add_character_to_arc(
            arc_id=arc_id, character_id=character_id, role="supporting"
        )

        call_args = self.service.command_handler.handle_add_character_to_arc.call_args[
            0
        ][0]
        assert call_args.character_arc_notes == ""


class TestAnalysisAndOptimization:
    """Test suite for analysis and optimization methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_analyze_narrative_flow(self):
        """Test analyzing narrative flow."""
        arc_id = "test-arc"
        expected_result = {
            "flow_score": 8.5,
            "tension_curve": [3.0, 6.0, 9.0, 7.0, 5.0],
            "recommendations": ["Increase tension in middle", "Add climactic moment"],
        }
        self.service.query_handler.handle_get_narrative_flow_analysis.return_value = (
            expected_result
        )

        result = self.service.analyze_narrative_flow(
            arc_id=arc_id,
            include_recommendations=True,
            include_tension_progression=True,
        )

        assert result == expected_result

        call_args = (
            self.service.query_handler.handle_get_narrative_flow_analysis.call_args[0][
                0
            ]
        )
        assert isinstance(call_args, GetNarrativeFlowAnalysisQuery)
        assert call_args.arc_id == arc_id
        assert call_args.include_recommendations is True
        assert call_args.include_tension_progression is True

    def test_optimize_sequence(self):
        """Test optimizing plot point sequence."""
        arc_id = "test-arc"
        optimization_criteria = ["tension_progression", "character_development"]
        expected_result = {
            "optimized_sequence": ["plot-3", "plot-1", "plot-2"],
            "improvement_score": 7.2,
        }
        self.service.command_handler.handle_optimize_sequence.return_value = (
            expected_result
        )

        result = self.service.optimize_sequence(
            arc_id=arc_id,
            preserve_critical_order=True,
            optimization_criteria=optimization_criteria,
        )

        assert result == expected_result

        call_args = self.service.command_handler.handle_optimize_sequence.call_args[0][
            0
        ]
        assert isinstance(call_args, OptimizeSequenceCommand)
        assert call_args.arc_id == arc_id
        assert call_args.preserve_critical_order is True
        assert call_args.optimization_criteria == optimization_criteria

    def test_establish_causal_link(self):
        """Test establishing causal relationship between plot points."""
        arc_id = "test-arc"
        cause_id = "plot-1"
        effect_id = "plot-2"
        metadata = {"strength_reasoning": "Direct consequence"}

        self.service.establish_causal_link(
            arc_id=arc_id,
            cause_id=cause_id,
            effect_id=effect_id,
            relationship_type="direct_cause",
            strength="strong",
            certainty=0.9,
            metadata=metadata,
        )

        call_args = self.service.command_handler.handle_establish_causal_link.call_args[
            0
        ][0]
        assert isinstance(call_args, EstablishCausalLinkCommand)
        assert call_args.arc_id == arc_id
        assert call_args.cause_id == cause_id
        assert call_args.effect_id == effect_id
        assert call_args.relationship_type == "direct_cause"
        assert call_args.strength == "strong"
        assert call_args.certainty == Decimal("0.9")
        assert call_args.metadata == metadata

    def test_analyze_causality(self):
        """Test analyzing causality in narrative arc."""
        arc_id = "test-arc"
        expected_result = {
            "causal_paths": [["plot-1", "plot-2", "plot-3"]],
            "feedback_loops": [["plot-2", "plot-4", "plot-2"]],
            "complexity_score": 6.8,
        }
        self.service.query_handler.handle_get_causal_analysis.return_value = (
            expected_result
        )

        result = self.service.analyze_causality(
            arc_id=arc_id, include_paths=True, include_loops=True, max_path_depth=5
        )

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_causal_analysis.call_args[0][
            0
        ]
        assert isinstance(call_args, GetCausalAnalysisQuery)
        assert call_args.arc_id == arc_id
        assert call_args.include_paths is True
        assert call_args.include_loops is True
        assert call_args.max_path_depth == 5


class TestComprehensiveAnalysis:
    """Test suite for comprehensive analysis methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.query_handler = Mock()

    def test_get_arc_metrics(self):
        """Test getting comprehensive arc metrics."""
        arc_id = "test-arc"
        expected_result = {
            "coherence_score": 8.2,
            "flow_quality": 7.5,
            "causal_consistency": 9.1,
            "overall_rating": 8.3,
        }
        self.service.query_handler.handle_get_arc_metrics.return_value = expected_result

        result = self.service.get_arc_metrics(
            arc_id=arc_id,
            include_coherence=True,
            include_flow_analysis=False,
            include_causal_analysis=False,
        )

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_arc_metrics.call_args[0][0]
        assert isinstance(call_args, GetArcMetricsQuery)
        assert call_args.arc_id == arc_id
        assert call_args.include_coherence is True
        assert call_args.include_flow_analysis is False
        assert call_args.include_causal_analysis is False

    def test_get_arc_summary(self):
        """Test getting comprehensive arc summary."""
        arc_id = "test-arc"
        expected_result = {
            "arc_name": "Test Arc",
            "total_plot_points": 15,
            "theme_count": 3,
            "character_count": 5,
            "progression_status": "in_progress",
        }
        self.service.query_handler.handle_get_arc_summary.return_value = expected_result

        result = self.service.get_arc_summary(
            arc_id=arc_id, include_statistics=True, include_progression=True
        )

        assert result == expected_result

        call_args = self.service.query_handler.handle_get_arc_summary.call_args[0][0]
        assert isinstance(call_args, GetArcSummaryQuery)
        assert call_args.arc_id == arc_id
        assert call_args.include_statistics is True
        assert call_args.include_progression is True


class TestSearchAndDiscovery:
    """Test suite for search and discovery methods."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.query_handler = Mock()

    def test_search_narrative_arcs_minimal_params(self):
        """Test searching narrative arcs with minimal parameters."""
        expected_result = {
            "results": [
                {"arc_id": "arc-1", "arc_name": "First Arc"},
                {"arc_id": "arc-2", "arc_name": "Second Arc"},
            ],
            "total_count": 2,
        }
        self.service.query_handler.handle_search_narrative_arcs.return_value = (
            expected_result
        )

        result = self.service.search_narrative_arcs()

        assert result == expected_result

        call_args = self.service.query_handler.handle_search_narrative_arcs.call_args[
            0
        ][0]
        assert isinstance(call_args, SearchNarrativeArcsQuery)
        assert call_args.search_term is None
        assert call_args.arc_types is None
        assert call_args.statuses is None
        assert call_args.character_ids is None
        assert call_args.tags is None
        assert call_args.created_by is None
        assert call_args.limit == 50
        assert call_args.offset == 0
        assert call_args.sort_by == "updated_at"
        assert call_args.sort_order == "desc"

    def test_search_narrative_arcs_full_params(self):
        """Test searching narrative arcs with all parameters."""
        character_ids = [uuid4(), uuid4()]
        arc_types = ["main", "subplot"]
        statuses = ["active", "completed"]
        tags = ["action", "fantasy"]
        created_by = uuid4()

        expected_result = {
            "results": [{"arc_id": "arc-filtered", "arc_name": "Filtered Arc"}],
            "total_count": 1,
        }
        self.service.query_handler.handle_search_narrative_arcs.return_value = (
            expected_result
        )

        result = self.service.search_narrative_arcs(
            search_term="fantasy adventure",
            arc_types=arc_types,
            statuses=statuses,
            character_ids=character_ids,
            tags=tags,
            created_by=created_by,
            limit=20,
            offset=10,
            sort_by="created_at",
            sort_order="asc",
        )

        assert result == expected_result

        call_args = self.service.query_handler.handle_search_narrative_arcs.call_args[
            0
        ][0]
        assert call_args.search_term == "fantasy adventure"
        assert call_args.arc_types == arc_types
        assert call_args.statuses == statuses
        assert call_args.character_ids == character_ids
        assert call_args.tags == tags
        assert call_args.created_by == created_by
        assert call_args.limit == 20
        assert call_args.offset == 10
        assert call_args.sort_by == "created_at"
        assert call_args.sort_order == "asc"

    def test_get_arcs_by_type(self):
        """Test getting narrative arcs by type."""
        arc_type = "main"
        expected_result = [
            {"arc_id": "main-1", "arc_name": "First Main Arc"},
            {"arc_id": "main-2", "arc_name": "Second Main Arc"},
        ]
        self.service.query_handler.handle_get_narrative_arcs_by_type.return_value = (
            expected_result
        )

        result = self.service.get_arcs_by_type(
            arc_type=arc_type, status="active", limit=10, offset=0
        )

        assert result == expected_result

        call_args = (
            self.service.query_handler.handle_get_narrative_arcs_by_type.call_args[0][0]
        )
        assert isinstance(call_args, GetNarrativeArcsByTypeQuery)
        assert call_args.arc_type == arc_type
        assert call_args.status == "active"
        assert call_args.limit == 10
        assert call_args.offset == 0

    def test_get_arcs_by_type_minimal_params(self):
        """Test getting arcs by type with minimal parameters."""
        arc_type = "subplot"
        expected_result = [{"arc_id": "subplot-1", "arc_name": "Subplot Arc"}]
        self.service.query_handler.handle_get_narrative_arcs_by_type.return_value = (
            expected_result
        )

        result = self.service.get_arcs_by_type(arc_type=arc_type)

        assert result == expected_result

        call_args = (
            self.service.query_handler.handle_get_narrative_arcs_by_type.call_args[0][0]
        )
        assert call_args.arc_type == arc_type
        assert call_args.status is None
        assert call_args.limit is None
        assert call_args.offset is None


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_command_handler_exception_propagation(self):
        """Test that exceptions from command handler are properly propagated."""
        self.service.command_handler.handle_create_narrative_arc.side_effect = (
            ValueError("Invalid arc parameters")
        )

        with pytest.raises(ValueError, match="Invalid arc parameters"):
            self.service.create_narrative_arc(
                arc_name="Test Arc", arc_type="main", description="Test"
            )

    def test_query_handler_exception_propagation(self):
        """Test that exceptions from query handler are properly propagated."""
        self.service.query_handler.handle_get_narrative_arc.side_effect = RuntimeError(
            "Database connection failed"
        )

        with pytest.raises(RuntimeError, match="Database connection failed"):
            self.service.get_narrative_arc(arc_id="test-arc")

    def test_decimal_conversion_handling(self):
        """Test proper handling of decimal conversions."""
        # This should work fine with valid numeric values
        self.service.add_plot_point(
            arc_id="test-arc",
            plot_point_id="plot-1",
            plot_point_type="climax",
            importance="high",
            title="Test",
            description="Test",
            sequence_order=10,
            emotional_intensity=7.5,  # Should convert to Decimal
            dramatic_tension=8.0,
            story_significance=9.2,
        )

        # Verify the Decimal conversion occurred
        call_args = self.service.command_handler.handle_add_plot_point.call_args[0][0]
        assert call_args.emotional_intensity == Decimal("7.5")
        assert call_args.dramatic_tension == Decimal("8.0")
        assert call_args.story_significance == Decimal("9.2")


class TestIntegrationScenarios:
    """Test suite for complex integration scenarios."""

    def setup_method(self):
        """Set up test dependencies."""
        self.mock_repository = Mock()
        self.service = NarrativeArcApplicationService(repository=self.mock_repository)
        self.service.command_handler = Mock()
        self.service.query_handler = Mock()

    def test_complete_arc_creation_workflow(self):
        """Test complete workflow of creating and configuring an arc."""
        # 1. Create arc
        arc_id = "workflow-arc"
        self.service.command_handler.handle_create_narrative_arc.return_value = arc_id

        created_arc_id = self.service.create_narrative_arc(
            arc_name="Workflow Test Arc",
            arc_type="main",
            description="Testing complete workflow",
        )
        assert created_arc_id == arc_id

        # 2. Add plot point
        self.service.add_plot_point(
            arc_id=arc_id,
            plot_point_id="plot-1",
            plot_point_type="inciting_incident",
            importance="high",
            title="The Beginning",
            description="Start of the journey",
            sequence_order=10,
        )

        # 3. Add theme
        self.service.add_theme(
            arc_id=arc_id,
            theme_id="theme-1",
            theme_type="moral",
            intensity="moderate",
            name="Good vs Evil",
            description="Classic moral conflict",
        )

        # 4. Start the arc
        self.service.start_narrative_arc(arc_id=arc_id, start_sequence=1)

        # Verify all operations were called
        assert self.service.command_handler.handle_create_narrative_arc.called
        assert self.service.command_handler.handle_add_plot_point.called
        assert self.service.command_handler.handle_add_theme.called
        assert self.service.command_handler.handle_start_narrative_arc.called

    def test_analysis_workflow(self):
        """Test complete analysis workflow."""
        arc_id = "analysis-arc"

        # Mock analysis results
        flow_analysis = {"flow_score": 8.5, "recommendations": ["Improve pacing"]}
        causal_analysis = {"complexity_score": 7.2, "loops": []}
        metrics = {"overall_rating": 8.0}

        self.service.query_handler.handle_get_narrative_flow_analysis.return_value = (
            flow_analysis
        )
        self.service.query_handler.handle_get_causal_analysis.return_value = (
            causal_analysis
        )
        self.service.query_handler.handle_get_arc_metrics.return_value = metrics

        # Perform analysis
        flow_result = self.service.analyze_narrative_flow(arc_id=arc_id)
        causal_result = self.service.analyze_causality(arc_id=arc_id)
        metrics_result = self.service.get_arc_metrics(arc_id=arc_id)

        assert flow_result == flow_analysis
        assert causal_result == causal_analysis
        assert metrics_result == metrics

        # Verify all analysis queries were called
        assert self.service.query_handler.handle_get_narrative_flow_analysis.called
        assert self.service.query_handler.handle_get_causal_analysis.called
        assert self.service.query_handler.handle_get_arc_metrics.called
