#!/usr/bin/env python3
"""
Narrative Arc Repository Implementation

This module provides the SQLAlchemy implementation of the narrative arc
repository interface defined in the application layer.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, cast
from uuid import UUID

import structlog
from sqlalchemy import (
    DECIMAL,
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Session, relationship

from ...application.ports.narrative_arc_repository_port import INarrativeArcRepository
from ...domain.aggregates.narrative_arc import NarrativeArc
from ...domain.value_objects.narrative_context import NarrativeContext
from ...domain.value_objects.narrative_id import NarrativeId
from ...domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)
from ...domain.value_objects.plot_point import (
    PlotPoint,
    PlotPointImportance,
    PlotPointType,
)
from ...domain.value_objects.story_pacing import (
    PacingIntensity,
    PacingType,
    StoryPacing,
)

logger = structlog.get_logger(__name__)


# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


# Association tables for many-to-many relationships
narrative_primary_characters = Table(
    "narrative_primary_characters",
    Base.metadata,
    Column("narrative_arc_id", PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id")),
    Column("character_id", PG_UUID(as_uuid=True)),
)

narrative_supporting_characters = Table(
    "narrative_supporting_characters",
    Base.metadata,
    Column("narrative_arc_id", PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id")),
    Column("character_id", PG_UUID(as_uuid=True)),
)

narrative_active_contexts = Table(
    "narrative_active_contexts",
    Base.metadata,
    Column("narrative_arc_id", PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id")),
    Column("narrative_context_id", String, ForeignKey("narrative_contexts.id")),
)


class NarrativeArcEntity(Base):
    """SQLAlchemy entity for narrative arcs."""

    __tablename__ = "narrative_arcs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    arc_name = Column(String(255), nullable=False, index=True)
    arc_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")

    # Arc structure
    plot_sequence = Column(JSON, default=list)  # List of plot point IDs in order

    # Thematic elements
    theme_development = Column(JSON, default=dict)  # Theme ID -> list of sequences

    # Pacing and flow
    pacing_sequence = Column(JSON, default=list)  # List of pacing segment IDs in order

    # Character involvement
    character_arcs = Column(JSON, default=dict)  # Character ID -> arc notes

    # Arc metrics and properties
    target_length = Column(Integer, nullable=True)
    current_length = Column(Integer, default=0)
    completion_percentage: Column[Any] = Column(DECIMAL(4, 3), default=0.0)
    complexity_score: Column[Any] = Column(DECIMAL(3, 1), default=5.0)

    # Arc status and lifecycle
    status = Column(String(50), default="planning", index=True)
    start_sequence = Column(Integer, nullable=True)
    end_sequence = Column(Integer, nullable=True)

    # Quality metrics
    narrative_coherence: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    thematic_consistency: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    pacing_effectiveness: Column[Any] = Column(DECIMAL(3, 1), default=5.0)

    # Relationships
    parent_arc_id = Column(PG_UUID(as_uuid=True), nullable=True)
    child_arc_ids = Column(JSON, default=list)  # List of child arc IDs
    related_threads = Column(JSON, default=list)  # List of related thread IDs

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )
    created_by = Column(PG_UUID(as_uuid=True), nullable=True)
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")
    arc_metadata = Column(JSON, default=dict)

    # Domain events and version
    version = Column(Integer, default=1)

    # Relationships
    plot_points = relationship(
        "PlotPointEntity", back_populates="narrative_arc", cascade="all, delete-orphan"
    )
    themes = relationship(
        "NarrativeThemeEntity",
        back_populates="narrative_arc",
        cascade="all, delete-orphan",
    )
    pacing_segments = relationship(
        "StoryPacingEntity",
        back_populates="narrative_arc",
        cascade="all, delete-orphan",
    )
    narrative_contexts = relationship(
        "NarrativeContextEntity",
        back_populates="narrative_arc",
        cascade="all, delete-orphan",
    )

    # Many-to-many relationships
    primary_characters = relationship(
        "Character", secondary=narrative_primary_characters, lazy="select"
    )
    supporting_characters = relationship(
        "Character", secondary=narrative_supporting_characters, lazy="select"
    )
    active_contexts = relationship(
        "NarrativeContextEntity", secondary=narrative_active_contexts, lazy="select"
    )


class PlotPointEntity(Base):
    """SQLAlchemy entity for plot points."""

    __tablename__ = "plot_points"

    id = Column(String(255), primary_key=True)
    narrative_arc_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id"), nullable=False
    )

    plot_point_type = Column(String(100), nullable=False)
    importance = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    sequence_order = Column(Integer, nullable=False, index=True)

    # Intensity metrics
    emotional_intensity: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    dramatic_tension: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    story_significance: Column[Any] = Column(DECIMAL(3, 1), default=5.0)

    # Character and event relationships
    involved_characters = Column(JSON, default=list)
    prerequisite_events = Column(JSON, default=list)
    consequence_events = Column(JSON, default=list)

    # Context information
    location = Column(String(500), nullable=True)
    time_context = Column(String(500), nullable=True)
    pov_character = Column(PG_UUID(as_uuid=True), nullable=True)
    outcome = Column(Text, nullable=True)
    conflict_type = Column(String(100), nullable=True)

    # Thematic connections
    thematic_relevance = Column(JSON, default=dict)

    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")

    # Relationships
    narrative_arc = relationship("NarrativeArcEntity", back_populates="plot_points")


class NarrativeThemeEntity(Base):
    """SQLAlchemy entity for narrative themes."""

    __tablename__ = "narrative_themes"

    id = Column(String(255), primary_key=True)
    narrative_arc_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id"), nullable=False
    )

    theme_type = Column(String(100), nullable=False)
    intensity = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Theme metrics
    moral_complexity: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    emotional_resonance: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    universal_appeal: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    cultural_significance: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    development_potential: Column[Any] = Column(DECIMAL(3, 1), default=5.0)

    # Theme development
    symbolic_elements = Column(JSON, default=list)
    introduction_sequence = Column(Integer, nullable=True)
    resolution_sequence = Column(Integer, nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")

    # Relationships
    narrative_arc = relationship("NarrativeArcEntity", back_populates="themes")


class StoryPacingEntity(Base):
    """SQLAlchemy entity for story pacing segments."""

    __tablename__ = "story_pacing"

    id = Column(String(255), primary_key=True)
    narrative_arc_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id"), nullable=False
    )

    pacing_type = Column(String(100), nullable=False)
    base_intensity = Column(String(50), nullable=False)
    start_sequence = Column(Integer, nullable=False)
    end_sequence = Column(Integer, nullable=False)

    # Pacing metrics
    event_density: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    tension_curve: Column[Any] = Column(JSON, default=list)
    dialogue_ratio: Column[Any] = Column(DECIMAL(3, 2), default=0.4)
    action_ratio: Column[Any] = Column(DECIMAL(3, 2), default=0.3)
    reflection_ratio: Column[Any] = Column(DECIMAL(3, 2), default=0.3)
    description_density: Column[Any] = Column(DECIMAL(3, 1), default=5.0)

    # Focus and techniques
    character_focus = Column(JSON, default=list)
    narrative_techniques = Column(JSON, default=list)
    reader_engagement_target = Column(String(100), nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")

    # Relationships
    narrative_arc = relationship("NarrativeArcEntity", back_populates="pacing_segments")


class NarrativeContextEntity(Base):
    """SQLAlchemy entity for narrative contexts."""

    __tablename__ = "narrative_contexts"

    id = Column(String(255), primary_key=True)
    narrative_arc_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("narrative_arcs.id"), nullable=False
    )

    context_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    importance: Column[Any] = Column(DECIMAL(3, 1), default=5.0)
    is_persistent = Column(Boolean, default=False)

    # Sequence range
    start_sequence = Column(Integer, nullable=True)
    end_sequence = Column(Integer, nullable=True)

    # Context details
    location = Column(String(500), nullable=True)
    time_period = Column(String(500), nullable=True)
    mood = Column(String(100), nullable=True)
    atmosphere = Column(String(100), nullable=True)
    social_context = Column(Text, nullable=True)
    cultural_context = Column(Text, nullable=True)

    # Relationships
    affected_characters = Column(JSON, default=list)
    related_themes = Column(JSON, default=list)

    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")

    # Relationships
    narrative_arc = relationship(
        "NarrativeArcEntity", back_populates="narrative_contexts"
    )


class Character(Base):
    """Placeholder Character entity for relationships."""

    __tablename__ = "narrative_characters"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)


class NarrativeArcRepository(INarrativeArcRepository):
    """
    SQLAlchemy implementation of the narrative arc repository.

    Handles persistence operations for narrative arcs using SQLAlchemy ORM.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def save(self, narrative_arc: NarrativeArc) -> None:
        """Save a narrative arc to the database."""
        try:
            # Check if arc already exists
            existing = (
                self.session.query(NarrativeArcEntity)
                .filter_by(id=narrative_arc.arc_id.value)
                .first()
            )

            if existing:
                # Update existing arc
                self._update_arc_entity(existing, narrative_arc)
            else:
                # Create new arc
                arc_entity = self._create_arc_entity(narrative_arc)
                self.session.add(arc_entity)

            self.session.commit()

            # Clear uncommitted events after successful save
            narrative_arc.clear_uncommitted_events()

            logger.debug("narrative_arc_saved", arc_id=str(narrative_arc.arc_id))

        except Exception as e:
            self.session.rollback()
            logger.error(
                "narrative_arc_save_failed",
                arc_id=str(narrative_arc.arc_id),
                error=str(e),
            )
            raise

    def get_by_id(self, arc_id: NarrativeId) -> Optional[NarrativeArc]:
        """Get a narrative arc by ID."""
        try:
            arc_entity = (
                self.session.query(NarrativeArcEntity)
                .filter_by(id=arc_id.value)
                .first()
            )

            if not arc_entity:
                return None

            return self._entity_to_aggregate(arc_entity)

        except Exception as e:
            logger.error(
                "narrative_arc_retrieval_failed", arc_id=str(arc_id), error=str(e)
            )
            raise

    def get_by_type(
        self,
        arc_type: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[NarrativeArc]:
        """Get narrative arcs by type."""
        try:
            query = self.session.query(NarrativeArcEntity).filter_by(arc_type=arc_type)

            if status:
                query = query.filter_by(status=status)

            query = query.order_by(NarrativeArcEntity.updated_at.desc())

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            arc_entities = query.all()
            return [self._entity_to_aggregate(entity) for entity in arc_entities]

        except Exception as e:
            logger.error(
                "narrative_arcs_by_type_retrieval_failed",
                arc_type=arc_type,
                error=str(e),
            )
            raise

    def search(
        self,
        search_term: Optional[str] = None,
        arc_types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        character_ids: Optional[List[UUID]] = None,
        theme_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
        min_complexity: Optional[Decimal] = None,
        max_complexity: Optional[Decimal] = None,
        min_completion: Optional[Decimal] = None,
        max_completion: Optional[Decimal] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        sort_by: Optional[str] = "updated_at",
        sort_order: str = "desc",
    ) -> Tuple[List[NarrativeArc], int]:
        """Search narrative arcs with various criteria."""
        try:
            query = self.session.query(NarrativeArcEntity)

            # Apply filters
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    (NarrativeArcEntity.arc_name.ilike(search_pattern))
                    | (NarrativeArcEntity.description.ilike(search_pattern))
                    | (NarrativeArcEntity.notes.ilike(search_pattern))
                )

            if arc_types:
                query = query.filter(NarrativeArcEntity.arc_type.in_(arc_types))

            if statuses:
                query = query.filter(NarrativeArcEntity.status.in_(statuses))

            if created_by:
                query = query.filter_by(created_by=created_by)

            if min_complexity is not None:
                query = query.filter(
                    NarrativeArcEntity.complexity_score >= min_complexity
                )

            if max_complexity is not None:
                query = query.filter(
                    NarrativeArcEntity.complexity_score <= max_complexity
                )

            if min_completion is not None:
                query = query.filter(
                    NarrativeArcEntity.completion_percentage >= min_completion
                )

            if max_completion is not None:
                query = query.filter(
                    NarrativeArcEntity.completion_percentage <= max_completion
                )

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting
            order_col: Any
            if sort_by == "created_at":
                order_col = NarrativeArcEntity.created_at
            elif sort_by == "updated_at":
                order_col = NarrativeArcEntity.updated_at
            elif sort_by == "arc_name":
                order_col = NarrativeArcEntity.arc_name
            elif sort_by == "complexity_score":
                order_col = NarrativeArcEntity.complexity_score
            elif sort_by == "completion_percentage":
                order_col = NarrativeArcEntity.completion_percentage
            else:
                order_col = NarrativeArcEntity.updated_at

            if sort_order.lower() == "asc":
                query = query.order_by(order_col.asc())
            else:
                query = query.order_by(order_col.desc())

            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            arc_entities = query.all()
            arcs = [self._entity_to_aggregate(entity) for entity in arc_entities]

            return arcs, total_count

        except Exception as e:
            logger.error("narrative_arc_search_failed", error=str(e))
            raise

    def delete(self, arc_id: NarrativeId) -> bool:
        """Delete a narrative arc by ID."""
        try:
            arc_entity = (
                self.session.query(NarrativeArcEntity)
                .filter_by(id=arc_id.value)
                .first()
            )

            if not arc_entity:
                return False

            self.session.delete(arc_entity)
            self.session.commit()

            logger.debug("narrative_arc_deleted", arc_id=str(arc_id))
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(
                "narrative_arc_deletion_failed", arc_id=str(arc_id), error=str(e)
            )
            raise

    def exists(self, arc_id: NarrativeId) -> bool:
        """Check if a narrative arc exists."""
        try:
            count: int = (
                self.session.query(NarrativeArcEntity)
                .filter_by(id=arc_id.value)
                .count()
            )
            return count > 0
        except Exception as e:
            logger.error(
                "narrative_arc_existence_check_failed", arc_id=str(arc_id), error=str(e)
            )
            raise

    def _create_arc_entity(self, narrative_arc: NarrativeArc) -> NarrativeArcEntity:
        """Create SQLAlchemy entity from domain aggregate."""
        arc_entity = NarrativeArcEntity(
            id=narrative_arc.arc_id.value,
            arc_name=narrative_arc.arc_name,
            arc_type=narrative_arc.arc_type,
            description=narrative_arc.description,
            plot_sequence=narrative_arc.plot_sequence,
            theme_development={
                k: v for k, v in narrative_arc.theme_development.items()
            },
            pacing_sequence=narrative_arc.pacing_sequence,
            character_arcs={str(k): v for k, v in narrative_arc.character_arcs.items()},
            target_length=narrative_arc.target_length,
            current_length=narrative_arc.current_length,
            completion_percentage=narrative_arc.completion_percentage,
            complexity_score=narrative_arc.complexity_score,
            status=narrative_arc.status,
            start_sequence=narrative_arc.start_sequence,
            end_sequence=narrative_arc.end_sequence,
            narrative_coherence=narrative_arc.narrative_coherence,
            thematic_consistency=narrative_arc.thematic_consistency,
            pacing_effectiveness=narrative_arc.pacing_effectiveness,
            parent_arc_id=(
                narrative_arc.parent_arc_id.value
                if narrative_arc.parent_arc_id
                else None
            ),
            child_arc_ids=[str(cid.value) for cid in narrative_arc.child_arc_ids],
            related_threads=[str(tid.value) for tid in narrative_arc.related_threads],
            created_at=narrative_arc.created_at,
            updated_at=narrative_arc.updated_at,
            created_by=narrative_arc.created_by,
            tags=list(narrative_arc.tags),
            notes=narrative_arc.notes,
            arc_metadata=narrative_arc.metadata,
            version=narrative_arc._version,
        )

        # Add plot points
        arc_id_val = cast(UUID, arc_entity.id)
        for plot_point in narrative_arc.plot_points.values():
            plot_entity = self._create_plot_point_entity(plot_point, arc_id_val)
            arc_entity.plot_points.append(plot_entity)

        # Add themes
        for theme in narrative_arc.themes.values():
            theme_entity = self._create_theme_entity(theme, arc_id_val)
            arc_entity.themes.append(theme_entity)

        # Add pacing segments
        for pacing in narrative_arc.pacing_segments.values():
            pacing_entity = self._create_pacing_entity(pacing, arc_id_val)
            arc_entity.pacing_segments.append(pacing_entity)

        # Add narrative contexts
        for context in narrative_arc.narrative_contexts.values():
            context_entity = self._create_context_entity(context, arc_id_val)
            arc_entity.narrative_contexts.append(context_entity)

        return arc_entity

    def _update_arc_entity(
        self, arc_entity: NarrativeArcEntity, narrative_arc: NarrativeArc
    ) -> None:
        """Update existing SQLAlchemy entity from domain aggregate."""
        # Update basic fields
        arc_entity.arc_name = narrative_arc.arc_name  # type: ignore[assignment]
        arc_entity.arc_type = narrative_arc.arc_type  # type: ignore[assignment]
        arc_entity.description = narrative_arc.description  # type: ignore[assignment]
        arc_entity.plot_sequence = narrative_arc.plot_sequence  # type: ignore[assignment]
        arc_entity.theme_development = {
            k: v for k, v in narrative_arc.theme_development.items()
        }  # type: ignore[assignment]
        arc_entity.pacing_sequence = narrative_arc.pacing_sequence  # type: ignore[assignment]
        arc_entity.character_arcs = {
            str(k): v for k, v in narrative_arc.character_arcs.items()
        }  # type: ignore[assignment]
        arc_entity.target_length = narrative_arc.target_length  # type: ignore[assignment]
        arc_entity.current_length = narrative_arc.current_length  # type: ignore[assignment]
        arc_entity.completion_percentage = narrative_arc.completion_percentage  # type: ignore[assignment]
        arc_entity.complexity_score = narrative_arc.complexity_score  # type: ignore[assignment]
        arc_entity.status = narrative_arc.status  # type: ignore[assignment]
        arc_entity.start_sequence = narrative_arc.start_sequence  # type: ignore[assignment]
        arc_entity.end_sequence = narrative_arc.end_sequence  # type: ignore[assignment]
        arc_entity.narrative_coherence = narrative_arc.narrative_coherence  # type: ignore[assignment]
        arc_entity.thematic_consistency = narrative_arc.thematic_consistency  # type: ignore[assignment]
        arc_entity.pacing_effectiveness = narrative_arc.pacing_effectiveness  # type: ignore[assignment]
        arc_entity.updated_at = narrative_arc.updated_at  # type: ignore[assignment]
        arc_entity.tags = list(narrative_arc.tags)  # type: ignore[assignment]
        arc_entity.notes = narrative_arc.notes  # type: ignore[assignment]
        arc_entity.arc_metadata = narrative_arc.metadata  # type: ignore[assignment]
        arc_entity.version = narrative_arc._version  # type: ignore[assignment]

        # Update child collections (simplified - in production, consider more efficient updates)
        # Clear existing and recreate
        for plot_point in arc_entity.plot_points:
            self.session.delete(plot_point)
        arc_entity.plot_points.clear()

        for theme in arc_entity.themes:
            self.session.delete(theme)
        arc_entity.themes.clear()

        for pacing in arc_entity.pacing_segments:
            self.session.delete(pacing)
        arc_entity.pacing_segments.clear()

        for context in arc_entity.narrative_contexts:
            self.session.delete(context)
        arc_entity.narrative_contexts.clear()

        # Add updated collections
        for plot_point in narrative_arc.plot_points.values():
            plot_entity = self._create_plot_point_entity(
                plot_point, cast(UUID, arc_entity.id)
            )
            arc_entity.plot_points.append(plot_entity)

        for theme in narrative_arc.themes.values():
            theme_entity = self._create_theme_entity(theme, cast(UUID, arc_entity.id))
            arc_entity.themes.append(theme_entity)

        for pacing in narrative_arc.pacing_segments.values():
            pacing_entity = self._create_pacing_entity(
                pacing, cast(UUID, arc_entity.id)
            )
            arc_entity.pacing_segments.append(pacing_entity)

        for context in narrative_arc.narrative_contexts.values():
            context_entity = self._create_context_entity(
                context, cast(UUID, arc_entity.id)
            )
            arc_entity.narrative_contexts.append(context_entity)

    def _create_plot_point_entity(
        self, plot_point: PlotPoint, arc_id: UUID
    ) -> PlotPointEntity:
        """Create PlotPoint entity from domain value object."""
        involved_chars: List[str] = []
        if plot_point.involved_characters:
            involved_chars = [str(cid) for cid in plot_point.involved_characters]
        prereq_events: List[str] = (
            list(plot_point.prerequisite_events)
            if plot_point.prerequisite_events
            else []
        )
        tags_list: List[str] = list(plot_point.tags) if plot_point.tags else []

        return PlotPointEntity(
            id=plot_point.plot_point_id,
            narrative_arc_id=arc_id,
            plot_point_type=plot_point.plot_point_type.value,
            importance=plot_point.importance.value,
            title=plot_point.title,
            description=plot_point.description,
            sequence_order=plot_point.sequence_order,
            emotional_intensity=plot_point.emotional_intensity,
            dramatic_tension=plot_point.dramatic_tension,
            story_significance=plot_point.story_significance,
            involved_characters=involved_chars,
            prerequisite_events=prereq_events,
            consequence_events=[],
            location=None,
            time_context=None,
            pov_character=None,
            outcome=None,
            conflict_type=None,
            thematic_relevance={},
            tags=tags_list,
            notes=plot_point.narrative_notes,
        )

    def _create_theme_entity(
        self, theme: NarrativeTheme, arc_id: UUID
    ) -> NarrativeThemeEntity:
        """Create NarrativeTheme entity from domain value object."""
        symbolic_elems: List[str] = (
            list(theme.symbolic_elements) if theme.symbolic_elements else []
        )
        tags_list: List[str] = list(theme.tags) if theme.tags else []

        return NarrativeThemeEntity(
            id=theme.theme_id,
            narrative_arc_id=arc_id,
            theme_type=theme.theme_type.value,
            intensity=theme.intensity.value,
            name=theme.name,
            description=theme.description,
            moral_complexity=theme.moral_complexity,
            emotional_resonance=theme.emotional_resonance,
            universal_appeal=theme.universal_appeal,
            cultural_significance=Decimal("5.0"),
            development_potential=Decimal("5.0"),
            symbolic_elements=symbolic_elems,
            introduction_sequence=theme.introduction_sequence,
            resolution_sequence=theme.resolution_sequence,
            tags=tags_list,
            notes="",
        )

    def _create_pacing_entity(
        self, pacing: StoryPacing, arc_id: UUID
    ) -> StoryPacingEntity:
        """Create StoryPacing entity from domain value object."""
        tension_list: List[float] = (
            [float(t) for t in pacing.tension_curve] if pacing.tension_curve else []
        )

        return StoryPacingEntity(
            id=pacing.pacing_id,
            narrative_arc_id=arc_id,
            pacing_type=pacing.pacing_type.value,
            base_intensity=pacing.base_intensity.value,
            start_sequence=pacing.start_sequence,
            end_sequence=pacing.end_sequence,
            event_density=pacing.event_density,
            tension_curve=tension_list,
            dialogue_ratio=pacing.dialogue_ratio,
            action_ratio=pacing.action_ratio,
            reflection_ratio=pacing.reflection_ratio,
            description_density=Decimal("5.0"),
            character_focus=[],
            narrative_techniques=[],
            reader_engagement_target=None,
            tags=[],
            notes=pacing.pacing_notes,
        )

    def _create_context_entity(
        self, context: NarrativeContext, arc_id: UUID
    ) -> NarrativeContextEntity:
        """Create NarrativeContext entity from domain value object."""
        affected_chars: List[str] = []
        if context.affected_characters:
            affected_chars = [str(cid) for cid in context.affected_characters]
        tags_list: List[str] = list(context.tags) if context.tags else []

        return NarrativeContextEntity(
            id=context.context_id,
            narrative_arc_id=arc_id,
            context_type=context.context_type.value,
            name=context.name,
            description=context.description,
            importance=context.narrative_importance,
            is_persistent=context.is_persistent,
            start_sequence=context.applies_from_sequence,
            end_sequence=context.applies_to_sequence,
            location=None,
            time_period=None,
            mood=None,
            atmosphere=None,
            social_context=None,
            cultural_context=None,
            affected_characters=affected_chars,
            related_themes=[],
            tags=tags_list,
            notes=context.research_notes,
        )

    def _entity_to_aggregate(self, arc_entity: NarrativeArcEntity) -> NarrativeArc:
        """Convert SQLAlchemy entity to domain aggregate."""
        from ...domain.value_objects.narrative_context import ContextScope

        # Convert plot points
        plot_points: Dict[str, PlotPoint] = {}
        for plot_entity in arc_entity.plot_points:
            involved_chars: Optional[FrozenSet[UUID]] = None
            prereq_events: Optional[List[str]] = None
            if plot_entity.involved_characters:
                involved_chars = frozenset(
                    UUID(cid) for cid in plot_entity.involved_characters
                )
            if plot_entity.prerequisite_events:
                prereq_events = list(plot_entity.prerequisite_events)
            pp_tags: Optional[FrozenSet[str]] = None
            if plot_entity.tags:
                pp_tags = frozenset(plot_entity.tags)
            plot_point = PlotPoint(
                plot_point_id=plot_entity.id,
                plot_point_type=PlotPointType(plot_entity.plot_point_type),
                importance=PlotPointImportance(plot_entity.importance),
                title=plot_entity.title,
                description=plot_entity.description,
                sequence_order=plot_entity.sequence_order,
                emotional_intensity=plot_entity.emotional_intensity,
                dramatic_tension=plot_entity.dramatic_tension,
                story_significance=plot_entity.story_significance,
                involved_characters=involved_chars,
                prerequisite_events=prereq_events,
                tags=pp_tags,
            )
            plot_points[plot_point.plot_point_id] = plot_point

        # Convert themes
        themes: Dict[str, NarrativeTheme] = {}
        for theme_entity in arc_entity.themes:
            symbolic_elems: Optional[FrozenSet[str]] = None
            theme_tags: Optional[FrozenSet[str]] = None
            if theme_entity.symbolic_elements:
                symbolic_elems = frozenset(theme_entity.symbolic_elements)
            if theme_entity.tags:
                theme_tags = frozenset(theme_entity.tags)
            theme = NarrativeTheme(
                theme_id=theme_entity.id,
                theme_type=ThemeType(theme_entity.theme_type),
                intensity=ThemeIntensity(theme_entity.intensity),
                name=theme_entity.name,
                description=theme_entity.description,
                moral_complexity=theme_entity.moral_complexity,
                emotional_resonance=theme_entity.emotional_resonance,
                universal_appeal=theme_entity.universal_appeal,
                symbolic_elements=symbolic_elems,
                introduction_sequence=theme_entity.introduction_sequence,
                resolution_sequence=theme_entity.resolution_sequence,
                tags=theme_tags,
            )
            themes[theme.theme_id] = theme

        # Convert pacing segments
        pacing_segments: Dict[str, StoryPacing] = {}
        for pacing_entity in arc_entity.pacing_segments:
            tension_curve_tuple: Optional[Tuple[Decimal, ...]] = None
            if pacing_entity.tension_curve:
                tension_curve_tuple = tuple(
                    Decimal(str(t)) for t in pacing_entity.tension_curve
                )
            pacing = StoryPacing(
                pacing_id=pacing_entity.id,
                pacing_type=PacingType(pacing_entity.pacing_type),
                base_intensity=PacingIntensity(pacing_entity.base_intensity),
                start_sequence=pacing_entity.start_sequence,
                end_sequence=pacing_entity.end_sequence,
                event_density=pacing_entity.event_density,
                tension_curve=tension_curve_tuple,
                dialogue_ratio=pacing_entity.dialogue_ratio,
                action_ratio=pacing_entity.action_ratio,
                reflection_ratio=pacing_entity.reflection_ratio,
            )
            pacing_segments[pacing.pacing_id] = pacing

        # Convert narrative contexts
        narrative_contexts: Dict[str, NarrativeContext] = {}
        for context_entity in arc_entity.narrative_contexts:
            affected_chars: Optional[FrozenSet[UUID]] = None
            context_tags: Optional[FrozenSet[str]] = None
            if context_entity.affected_characters:
                affected_chars = frozenset(
                    UUID(cid) for cid in context_entity.affected_characters
                )
            if context_entity.tags:
                context_tags = frozenset(context_entity.tags)
            context = NarrativeContext(
                context_id=context_entity.id,
                context_type=context_entity.context_type,
                scope=ContextScope.GLOBAL,  # Default scope
                name=context_entity.name,
                description=context_entity.description,
                applies_from_sequence=context_entity.start_sequence,
                applies_to_sequence=context_entity.end_sequence,
                is_persistent=context_entity.is_persistent,
                affected_characters=affected_chars,
                tags=context_tags,
            )
            narrative_contexts[context.context_id] = context

        # Get active contexts from entity relationships
        active_contexts: Set[str] = set()
        if hasattr(arc_entity, "active_contexts") and arc_entity.active_contexts:
            for ctx in arc_entity.active_contexts:
                if hasattr(ctx, "id"):
                    active_contexts.add(str(ctx.id))

        # Get primary characters from entity relationships
        primary_chars: Set[UUID] = set()
        if hasattr(arc_entity, "primary_characters") and arc_entity.primary_characters:
            for char in arc_entity.primary_characters:
                if hasattr(char, "id"):
                    primary_chars.add(cast(UUID, char.id))

        # Get supporting characters from entity relationships
        supporting_chars: Set[UUID] = set()
        if (
            hasattr(arc_entity, "supporting_characters")
            and arc_entity.supporting_characters
        ):
            for char in arc_entity.supporting_characters:
                if hasattr(char, "id"):
                    supporting_chars.add(cast(UUID, char.id))

        # Process child arc IDs
        child_arc_ids: Set[NarrativeId] = set()
        child_ids_raw = cast(Optional[List[str]], arc_entity.child_arc_ids)
        if child_ids_raw:
            for cid in child_ids_raw:
                child_arc_ids.add(NarrativeId(UUID(str(cid))))

        # Process related threads
        related_threads: Set[NarrativeId] = set()
        threads_raw = cast(Optional[List[str]], arc_entity.related_threads)
        if threads_raw:
            for tid in threads_raw:
                related_threads.add(NarrativeId(UUID(str(tid))))

        # Process plot sequence
        plot_seq_raw = cast(Optional[List[str]], arc_entity.plot_sequence)
        plot_seq: List[str] = list(plot_seq_raw) if plot_seq_raw else []

        # Process pacing sequence
        pacing_seq_raw = cast(Optional[List[str]], arc_entity.pacing_sequence)
        pacing_seq: List[str] = list(pacing_seq_raw) if pacing_seq_raw else []

        # Process tags
        tags_raw = cast(Optional[List[str]], arc_entity.tags)
        arc_tags: Set[str] = set(tags_raw) if tags_raw else set()

        # Process metadata
        metadata_raw = cast(Optional[Dict[str, Any]], arc_entity.arc_metadata)
        arc_metadata: Dict[str, Any] = dict(metadata_raw) if metadata_raw else {}

        # Process character arcs
        char_arcs: Dict[UUID, str] = {}
        char_arcs_raw = cast(Optional[Dict[str, str]], arc_entity.character_arcs)
        if char_arcs_raw:
            for k, v in char_arcs_raw.items():
                char_arcs[UUID(str(k))] = str(v)

        # Process theme development
        theme_dev_raw = cast(
            Optional[Dict[str, List[int]]], arc_entity.theme_development
        )
        theme_dev: Dict[str, List[int]] = dict(theme_dev_raw) if theme_dev_raw else {}

        # Create the aggregate
        narrative_arc = NarrativeArc(
            arc_id=NarrativeId(cast(UUID, arc_entity.id)),
            arc_name=str(arc_entity.arc_name),
            arc_type=str(arc_entity.arc_type),
            description=str(arc_entity.description) if arc_entity.description else "",
            plot_points=plot_points,
            plot_sequence=plot_seq,
            themes=themes,
            theme_development=theme_dev,
            pacing_segments=pacing_segments,
            pacing_sequence=pacing_seq,
            narrative_contexts=narrative_contexts,
            active_contexts=active_contexts,
            primary_characters=primary_chars,
            supporting_characters=supporting_chars,
            character_arcs=char_arcs,
            target_length=cast(Optional[int], arc_entity.target_length),
            current_length=cast(int, arc_entity.current_length)
            if arc_entity.current_length
            else 0,
            completion_percentage=cast(Decimal, arc_entity.completion_percentage),
            complexity_score=cast(Decimal, arc_entity.complexity_score),
            status=str(arc_entity.status) if arc_entity.status else "planning",
            start_sequence=cast(Optional[int], arc_entity.start_sequence),
            end_sequence=cast(Optional[int], arc_entity.end_sequence),
            narrative_coherence=cast(Decimal, arc_entity.narrative_coherence),
            thematic_consistency=cast(Decimal, arc_entity.thematic_consistency),
            pacing_effectiveness=cast(Decimal, arc_entity.pacing_effectiveness),
            parent_arc_id=(
                NarrativeId(cast(UUID, arc_entity.parent_arc_id))
                if arc_entity.parent_arc_id
                else None
            ),
            child_arc_ids=child_arc_ids,
            related_threads=related_threads,
            created_at=cast(datetime, arc_entity.created_at),
            updated_at=cast(datetime, arc_entity.updated_at),
            created_by=cast(Optional[UUID], arc_entity.created_by),
            tags=arc_tags,
            notes=str(arc_entity.notes) if arc_entity.notes else "",
            metadata=arc_metadata,
        )

        # Set internal version
        narrative_arc._version = (
            cast(int, arc_entity.version) if arc_entity.version else 1
        )

        return narrative_arc
