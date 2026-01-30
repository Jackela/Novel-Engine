#!/usr/bin/env python3
"""
Narrative Arc Application Service

This module implements the main application service for narrative arc operations,
providing a high-level interface that orchestrates between commands, queries, and domain services.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from ...domain.services.causal_graph_service import CausalGraphService
from ...domain.services.narrative_flow_service import NarrativeFlowService
from ..ports.narrative_arc_repository_port import INarrativeArcRepository
from ..command_handlers.narrative_arc_command_handlers import NarrativeArcCommandHandler
from ..commands.narrative_arc_commands import (
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
from ..queries.narrative_arc_queries import (
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
from ..query_handlers.narrative_arc_query_handlers import NarrativeArcQueryHandler

logger = logging.getLogger(__name__)


class NarrativeArcApplicationService:
    """
    Main application service for narrative arc operations.

    Provides high-level interface for all narrative arc functionality,
    orchestrating between command handlers, query handlers, and domain services.
    """

    def __init__(
        self,
        repository: INarrativeArcRepository,
        flow_service: Optional[NarrativeFlowService] = None,
        causal_service: Optional[CausalGraphService] = None,
    ):
        """
        Initialize application service.

        Args:
            repository: Repository for narrative arc persistence
            flow_service: Service for narrative flow analysis
            causal_service: Service for causal relationship management
        """
        self.repository = repository
        self.flow_service = flow_service or NarrativeFlowService()
        self.causal_service = causal_service or CausalGraphService()

        # Initialize handlers
        self.command_handler = NarrativeArcCommandHandler(
            repository=repository,
            flow_service=self.flow_service,
            causal_service=self.causal_service,
        )

        self.query_handler = NarrativeArcQueryHandler(
            repository=repository,
            flow_service=self.flow_service,
            causal_service=self.causal_service,
        )

        logger.info("Narrative Arc Application Service initialized")

    # Arc Lifecycle Management

    def create_narrative_arc(
        self,
        arc_name: str,
        arc_type: str,
        description: str = "",
        target_length: Optional[int] = None,
        primary_characters: Optional[List[UUID]] = None,
        created_by: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new narrative arc.

        Args:
            arc_name: Name of the narrative arc
            arc_type: Type of arc (main, subplot, character_arc, etc.)
            description: Detailed description of the arc
            target_length: Target number of sequences
            primary_characters: List of primary character IDs
            created_by: ID of creator
            tags: List of tags for categorization
            notes: Additional notes
            metadata: Additional metadata

        Returns:
            ID of the created narrative arc
        """
        command = CreateNarrativeArcCommand(
            arc_name=arc_name,
            arc_type=arc_type,
            description=description,
            target_length=target_length,
            primary_characters=set(primary_characters) if primary_characters else None,
            created_by=created_by,
            tags=set(tags) if tags else None,
            notes=notes,
            metadata=metadata,
        )

        return self.command_handler.handle_create_narrative_arc(command)

    def get_narrative_arc(
        self, arc_id: str, include_details: bool = True, include_events: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a narrative arc by ID.

        Args:
            arc_id: ID of the narrative arc
            include_details: Whether to include detailed information
            include_events: Whether to include uncommitted events

        Returns:
            Dictionary containing arc information, or None if not found
        """
        query = GetNarrativeArcQuery(
            arc_id=arc_id,
            include_details=include_details,
            include_events=include_events,
        )

        return self.query_handler.handle_get_narrative_arc(query)

    def update_narrative_arc(
        self,
        arc_id: str,
        arc_name: Optional[str] = None,
        arc_type: Optional[str] = None,
        description: Optional[str] = None,
        target_length: Optional[int] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update narrative arc properties."""
        command = UpdateNarrativeArcCommand(
            arc_id=arc_id,
            arc_name=arc_name,
            arc_type=arc_type,
            description=description,
            target_length=target_length,
            notes=notes,
            tags=set(tags) if tags else None,
            metadata=metadata,
        )

        self.command_handler.handle_update_narrative_arc(command)

    def start_narrative_arc(self, arc_id: str, start_sequence: int) -> None:
        """Start a narrative arc at a specific sequence."""
        command = StartNarrativeArcCommand(arc_id=arc_id, start_sequence=start_sequence)

        self.command_handler.handle_start_narrative_arc(command)

    def complete_narrative_arc(self, arc_id: str, end_sequence: int) -> None:
        """Complete a narrative arc."""
        command = CompleteNarrativeArcCommand(arc_id=arc_id, end_sequence=end_sequence)

        self.command_handler.handle_complete_narrative_arc(command)

    # Plot Point Management

    def add_plot_point(
        self,
        arc_id: str,
        plot_point_id: str,
        plot_point_type: str,
        importance: str,
        title: str,
        description: str,
        sequence_order: int,
        emotional_intensity: float = 5.0,
        dramatic_tension: float = 5.0,
        story_significance: float = 5.0,
        involved_characters: Optional[List[UUID]] = None,
        prerequisite_events: Optional[List[str]] = None,
        consequence_events: Optional[List[str]] = None,
        location: Optional[str] = None,
        time_context: Optional[str] = None,
        pov_character: Optional[UUID] = None,
        outcome: Optional[str] = None,
        conflict_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Add a plot point to a narrative arc."""
        from decimal import Decimal

        command = AddPlotPointCommand(
            arc_id=arc_id,
            plot_point_id=plot_point_id,
            plot_point_type=plot_point_type,
            importance=importance,
            title=title,
            description=description,
            sequence_order=sequence_order,
            emotional_intensity=Decimal(str(emotional_intensity)),
            dramatic_tension=Decimal(str(dramatic_tension)),
            story_significance=Decimal(str(story_significance)),
            involved_characters=(
                set(involved_characters) if involved_characters else None
            ),
            prerequisite_events=(
                set(prerequisite_events) if prerequisite_events else None
            ),
            consequence_events=set(consequence_events) if consequence_events else None,
            location=location,
            time_context=time_context,
            pov_character=pov_character,
            outcome=outcome,
            conflict_type=conflict_type,
            tags=set(tags) if tags else None,
            notes=notes,
        )

        self.command_handler.handle_add_plot_point(command)

    def get_plot_point(
        self, arc_id: str, plot_point_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific plot point."""
        query = GetPlotPointQuery(arc_id=arc_id, plot_point_id=plot_point_id)

        return self.query_handler.handle_get_plot_point(query)

    def get_plot_points_in_sequence(
        self,
        arc_id: str,
        start_sequence: Optional[int] = None,
        end_sequence: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get plot points in sequence order."""
        query = GetPlotPointsInSequenceQuery(
            arc_id=arc_id, start_sequence=start_sequence, end_sequence=end_sequence
        )

        return self.query_handler.handle_get_plot_points_in_sequence(query)

    def update_plot_point(
        self,
        arc_id: str,
        plot_point_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sequence_order: Optional[int] = None,
        emotional_intensity: Optional[float] = None,
        dramatic_tension: Optional[float] = None,
        story_significance: Optional[float] = None,
        outcome: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Update a plot point."""
        from decimal import Decimal

        command = UpdatePlotPointCommand(
            arc_id=arc_id,
            plot_point_id=plot_point_id,
            title=title,
            description=description,
            sequence_order=sequence_order,
            emotional_intensity=(
                Decimal(str(emotional_intensity))
                if emotional_intensity is not None
                else None
            ),
            dramatic_tension=(
                Decimal(str(dramatic_tension)) if dramatic_tension is not None else None
            ),
            story_significance=(
                Decimal(str(story_significance))
                if story_significance is not None
                else None
            ),
            outcome=outcome,
            notes=notes,
        )

        self.command_handler.handle_update_plot_point(command)

    def remove_plot_point(self, arc_id: str, plot_point_id: str) -> None:
        """Remove a plot point from a narrative arc."""
        command = RemovePlotPointCommand(arc_id=arc_id, plot_point_id=plot_point_id)

        self.command_handler.handle_remove_plot_point(command)

    # Theme Management

    def add_theme(
        self,
        arc_id: str,
        theme_id: str,
        theme_type: str,
        intensity: str,
        name: str,
        description: str,
        moral_complexity: float = 5.0,
        emotional_resonance: float = 5.0,
        universal_appeal: float = 5.0,
        cultural_significance: float = 5.0,
        development_potential: float = 5.0,
        symbolic_elements: Optional[List[str]] = None,
        introduction_sequence: Optional[int] = None,
        resolution_sequence: Optional[int] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Add a theme to a narrative arc."""
        from decimal import Decimal

        command = AddThemeCommand(
            arc_id=arc_id,
            theme_id=theme_id,
            theme_type=theme_type,
            intensity=intensity,
            name=name,
            description=description,
            moral_complexity=Decimal(str(moral_complexity)),
            emotional_resonance=Decimal(str(emotional_resonance)),
            universal_appeal=Decimal(str(universal_appeal)),
            cultural_significance=Decimal(str(cultural_significance)),
            development_potential=Decimal(str(development_potential)),
            symbolic_elements=set(symbolic_elements) if symbolic_elements else None,
            introduction_sequence=introduction_sequence,
            resolution_sequence=resolution_sequence,
            tags=set(tags) if tags else None,
            notes=notes,
        )

        self.command_handler.handle_add_theme(command)

    def get_theme(self, arc_id: str, theme_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific theme."""
        query = GetThemeQuery(arc_id=arc_id, theme_id=theme_id)

        return self.query_handler.handle_get_theme(query)

    def get_themes_at_sequence(
        self, arc_id: str, sequence: int
    ) -> List[Dict[str, Any]]:
        """Get themes active at a specific sequence."""
        query = GetThemesAtSequenceQuery(arc_id=arc_id, sequence=sequence)

        return self.query_handler.handle_get_themes_at_sequence(query)

    def develop_theme(
        self, arc_id: str, theme_id: str, sequence: int, development_notes: str = ""
    ) -> None:
        """Develop a theme at a specific sequence."""
        command = DevelopThemeCommand(
            arc_id=arc_id,
            theme_id=theme_id,
            sequence=sequence,
            development_notes=development_notes,
        )

        self.command_handler.handle_develop_theme(command)

    # Pacing Management

    def add_pacing_segment(
        self,
        arc_id: str,
        pacing_id: str,
        pacing_type: str,
        base_intensity: str,
        start_sequence: int,
        end_sequence: int,
        event_density: float = 5.0,
        tension_curve: Optional[List[float]] = None,
        dialogue_ratio: float = 0.4,
        action_ratio: float = 0.3,
        reflection_ratio: float = 0.3,
        description_density: float = 5.0,
        character_focus: Optional[List[UUID]] = None,
        narrative_techniques: Optional[List[str]] = None,
        reader_engagement_target: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Add a pacing segment to a narrative arc."""
        from decimal import Decimal

        command = AddPacingSegmentCommand(
            arc_id=arc_id,
            pacing_id=pacing_id,
            pacing_type=pacing_type,
            base_intensity=base_intensity,
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            event_density=Decimal(str(event_density)),
            tension_curve=(
                [Decimal(str(t)) for t in tension_curve] if tension_curve else None
            ),
            dialogue_ratio=Decimal(str(dialogue_ratio)),
            action_ratio=Decimal(str(action_ratio)),
            reflection_ratio=Decimal(str(reflection_ratio)),
            description_density=Decimal(str(description_density)),
            character_focus=set(character_focus) if character_focus else None,
            narrative_techniques=(
                set(narrative_techniques) if narrative_techniques else None
            ),
            reader_engagement_target=reader_engagement_target,
            tags=set(tags) if tags else None,
            notes=notes,
        )

        self.command_handler.handle_add_pacing_segment(command)

    # Context Management

    def add_narrative_context(
        self,
        arc_id: str,
        context_id: str,
        context_type: str,
        name: str,
        description: str,
        importance: float = 5.0,
        is_persistent: bool = False,
        start_sequence: Optional[int] = None,
        end_sequence: Optional[int] = None,
        location: Optional[str] = None,
        time_period: Optional[str] = None,
        mood: Optional[str] = None,
        atmosphere: Optional[str] = None,
        social_context: Optional[str] = None,
        cultural_context: Optional[str] = None,
        affected_characters: Optional[List[UUID]] = None,
        related_themes: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> None:
        """Add a narrative context to an arc."""
        from decimal import Decimal

        command = AddNarrativeContextCommand(
            arc_id=arc_id,
            context_id=context_id,
            context_type=context_type,
            name=name,
            description=description,
            importance=Decimal(str(importance)),
            is_persistent=is_persistent,
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            location=location,
            time_period=time_period,
            mood=mood,
            atmosphere=atmosphere,
            social_context=social_context,
            cultural_context=cultural_context,
            affected_characters=(
                set(affected_characters) if affected_characters else None
            ),
            related_themes=set(related_themes) if related_themes else None,
            tags=set(tags) if tags else None,
            notes=notes,
        )

        self.command_handler.handle_add_narrative_context(command)

    def activate_context(self, arc_id: str, context_id: str) -> None:
        """Activate a narrative context."""
        command = ActivateContextCommand(arc_id=arc_id, context_id=context_id)

        self.command_handler.handle_activate_context(command)

    def deactivate_context(self, arc_id: str, context_id: str) -> None:
        """Deactivate a narrative context."""
        command = DeactivateContextCommand(arc_id=arc_id, context_id=context_id)

        self.command_handler.handle_deactivate_context(command)

    # Character Management

    def add_character_to_arc(
        self, arc_id: str, character_id: UUID, role: str, character_arc_notes: str = ""
    ) -> None:
        """Add a character to a narrative arc."""
        command = AddCharacterToArcCommand(
            arc_id=arc_id,
            character_id=character_id,
            role=role,
            character_arc_notes=character_arc_notes,
        )

        self.command_handler.handle_add_character_to_arc(command)

    # Analysis and Optimization

    def analyze_narrative_flow(
        self,
        arc_id: str,
        include_recommendations: bool = True,
        include_tension_progression: bool = True,
    ) -> Dict[str, Any]:
        """Analyze narrative flow of an arc."""
        query = GetNarrativeFlowAnalysisQuery(
            arc_id=arc_id,
            include_recommendations=include_recommendations,
            include_tension_progression=include_tension_progression,
        )

        return self.query_handler.handle_get_narrative_flow_analysis(query)

    def optimize_sequence(
        self,
        arc_id: str,
        preserve_critical_order: bool = True,
        optimization_criteria: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Optimize plot point sequence."""
        command = OptimizeSequenceCommand(
            arc_id=arc_id,
            preserve_critical_order=preserve_critical_order,
            optimization_criteria=optimization_criteria,
        )

        return self.command_handler.handle_optimize_sequence(command)

    def establish_causal_link(
        self,
        arc_id: str,
        cause_id: str,
        effect_id: str,
        relationship_type: str = "direct_cause",
        strength: str = "moderate",
        certainty: float = 0.8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Establish causal relationship between plot points."""
        from decimal import Decimal

        command = EstablishCausalLinkCommand(
            arc_id=arc_id,
            cause_id=cause_id,
            effect_id=effect_id,
            relationship_type=relationship_type,
            strength=strength,
            certainty=Decimal(str(certainty)),
            metadata=metadata,
        )

        self.command_handler.handle_establish_causal_link(command)

    def analyze_causality(
        self,
        arc_id: str,
        include_paths: bool = True,
        include_loops: bool = True,
        max_path_depth: int = 5,
    ) -> Dict[str, Any]:
        """Analyze causality in narrative arc."""
        query = GetCausalAnalysisQuery(
            arc_id=arc_id,
            include_paths=include_paths,
            include_loops=include_loops,
            max_path_depth=max_path_depth,
        )

        return self.query_handler.handle_get_causal_analysis(query)

    # Comprehensive Analysis

    def get_arc_metrics(
        self,
        arc_id: str,
        include_coherence: bool = True,
        include_flow_analysis: bool = False,
        include_causal_analysis: bool = False,
    ) -> Dict[str, Any]:
        """Get comprehensive arc metrics."""
        query = GetArcMetricsQuery(
            arc_id=arc_id,
            include_coherence=include_coherence,
            include_flow_analysis=include_flow_analysis,
            include_causal_analysis=include_causal_analysis,
        )

        return self.query_handler.handle_get_arc_metrics(query)

    def get_arc_summary(
        self,
        arc_id: str,
        include_statistics: bool = True,
        include_progression: bool = True,
    ) -> Dict[str, Any]:
        """Get comprehensive arc summary."""
        query = GetArcSummaryQuery(
            arc_id=arc_id,
            include_statistics=include_statistics,
            include_progression=include_progression,
        )

        return self.query_handler.handle_get_arc_summary(query)

    # Search and Discovery

    def search_narrative_arcs(
        self,
        search_term: Optional[str] = None,
        arc_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        character_ids: Optional[List[UUID]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Search narrative arcs with various criteria."""
        query = SearchNarrativeArcsQuery(
            search_term=search_term,
            arc_types=arc_types,
            statuses=statuses,
            character_ids=character_ids,
            tags=tags,
            created_by=created_by,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return self.query_handler.handle_search_narrative_arcs(query)

    def get_arcs_by_type(
        self,
        arc_type: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get narrative arcs by type."""
        query = GetNarrativeArcsByTypeQuery(
            arc_type=arc_type, status=status, limit=limit, offset=offset
        )

        return self.query_handler.handle_get_narrative_arcs_by_type(query)
