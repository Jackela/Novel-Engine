#!/usr/bin/env python3
"""
Narrative Arc Repository Interface and Implementation

This module defines the repository interface and SQLAlchemy implementation
for narrative arc persistence operations.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, cast
from uuid import UUID

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
from .narrative_domain_types import (
    NarrativeDomainTyping,
    RepositoryHelpers,
    ValueObjectFactory,
    ensure_decimal,
    ensure_not_none,
    ensure_uuid,
)

logger = logging.getLogger(__name__)


# Base class for all SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Association tables for many-to-many relationships
narrative_primary_characters = Table(
    "narrative_primary_characters",
    Base.metadata,
    Column(
        "narrative_arc_id",
        PG_UUID(as_uuid=True),
        ForeignKey("narrative_arcs.id"),
    ),
    Column("character_id", PG_UUID(as_uuid=True)),
)

narrative_supporting_characters = Table(
    "narrative_supporting_characters",
    Base.metadata,
    Column(
        "narrative_arc_id",
        PG_UUID(as_uuid=True),
        ForeignKey("narrative_arcs.id"),
    ),
    Column("character_id", PG_UUID(as_uuid=True)),
)

narrative_active_contexts = Table(
    "narrative_active_contexts",
    Base.metadata,
    Column(
        "narrative_arc_id",
        PG_UUID(as_uuid=True),
        ForeignKey("narrative_arcs.id"),
    ),
    Column(
        "narrative_context_id", String, ForeignKey("narrative_contexts.id")
    ),
)


class NarrativeArcEntity(Base):
    """SQLAlchemy entity for narrative arcs."""

    __tablename__ = "narrative_arcs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    arc_name = Column(String(255), nullable=False, index=True)
    arc_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")

    # Arc structure
    plot_sequence = Column(
        JSON, default=list
    )  # List of plot point IDs in order

    # Thematic elements
    theme_development = Column(
        JSON, default=dict
    )  # Theme ID -> list of sequences

    # Pacing and flow
    pacing_sequence = Column(
        JSON, default=list
    )  # List of pacing segment IDs in order

    # Character involvement
    character_arcs = Column(JSON, default=dict)  # Character ID -> arc notes

    # Arc metrics and properties
    target_length = Column(Integer, nullable=True)
    current_length = Column(Integer, default=0)
    completion_percentage = Column(DECIMAL(4, 3), default=0.0)
    complexity_score = Column(DECIMAL(3, 1), default=5.0)

    # Arc status and lifecycle
    status = Column(String(50), default="planning", index=True)
    start_sequence = Column(Integer, nullable=True)
    end_sequence = Column(Integer, nullable=True)

    # Quality metrics
    narrative_coherence = Column(DECIMAL(3, 1), default=5.0)
    thematic_consistency = Column(DECIMAL(3, 1), default=5.0)
    pacing_effectiveness = Column(DECIMAL(3, 1), default=5.0)

    # Relationships
    parent_arc_id = Column(PG_UUID(as_uuid=True), nullable=True)
    child_arc_ids = Column(JSON, default=list)  # List of child arc IDs
    related_threads = Column(JSON, default=list)  # List of related thread IDs

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
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
        "PlotPointEntity",
        back_populates="narrative_arc",
        cascade="all, delete-orphan",
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
        "NarrativeContextEntity",
        secondary=narrative_active_contexts,
        lazy="select",
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
    emotional_intensity = Column(DECIMAL(3, 1), default=5.0)
    dramatic_tension = Column(DECIMAL(3, 1), default=5.0)
    story_significance = Column(DECIMAL(3, 1), default=5.0)

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
    narrative_arc = relationship(
        "NarrativeArcEntity", back_populates="plot_points"
    )


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
    moral_complexity = Column(DECIMAL(3, 1), default=5.0)
    emotional_resonance = Column(DECIMAL(3, 1), default=5.0)
    universal_appeal = Column(DECIMAL(3, 1), default=5.0)
    cultural_significance = Column(DECIMAL(3, 1), default=5.0)
    development_potential = Column(DECIMAL(3, 1), default=5.0)

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
    event_density = Column(DECIMAL(3, 1), default=5.0)
    tension_curve = Column(JSON, default=list)
    dialogue_ratio = Column(DECIMAL(3, 2), default=0.4)
    action_ratio = Column(DECIMAL(3, 2), default=0.3)
    reflection_ratio = Column(DECIMAL(3, 2), default=0.3)
    description_density = Column(DECIMAL(3, 1), default=5.0)

    # Focus and techniques
    character_focus = Column(JSON, default=list)
    narrative_techniques = Column(JSON, default=list)
    reader_engagement_target = Column(String(100), nullable=True)

    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, default="")

    # Relationships
    narrative_arc = relationship(
        "NarrativeArcEntity", back_populates="pacing_segments"
    )


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
    importance = Column(DECIMAL(3, 1), default=5.0)
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


class INarrativeArcRepository(ABC):
    """
    Abstract repository interface for narrative arc persistence operations.

    Defines the contract for narrative arc data access without specifying
    implementation details.
    """

    @abstractmethod
    def save(self, narrative_arc: NarrativeArc) -> None:
        """
        Save a narrative arc.

        Args:
            narrative_arc: NarrativeArc aggregate to save
        """
        pass

    @abstractmethod
    def get_by_id(self, arc_id: NarrativeId) -> Optional[NarrativeArc]:
        """
        Get a narrative arc by ID.

        Args:
            arc_id: NarrativeId to search for

        Returns:
            NarrativeArc if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_type(
        self,
        arc_type: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[NarrativeArc]:
        """
        Get narrative arcs by type.

        Args:
            arc_type: Type of narrative arc
            status: Optional status filter
            limit: Optional limit for results
            offset: Optional offset for pagination

        Returns:
            List of matching NarrativeArc objects
        """
        pass

    @abstractmethod
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
        """
        Search narrative arcs with various criteria.

        Returns:
            Tuple of (matching arcs, total count)
        """
        pass

    @abstractmethod
    def delete(self, arc_id: NarrativeId) -> bool:
        """
        Delete a narrative arc by ID.

        Args:
            arc_id: NarrativeId of arc to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, arc_id: NarrativeId) -> bool:
        """
        Check if a narrative arc exists.

        Args:
            arc_id: NarrativeId to check

        Returns:
            True if exists, False otherwise
        """
        pass


class NarrativeArcRepository(INarrativeArcRepository):
    """
    SQLAlchemy implementation of the narrative arc repository.

    Handles persistence operations for narrative arcs using SQLAlchemy ORM.
    """

    def __init__(self, session: Session):
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

            logger.debug(f"Saved narrative arc: {narrative_arc.arc_id}")

        except Exception as e:
            self.session.rollback()
            logger.error(
                f"Failed to save narrative arc {narrative_arc.arc_id}: {str(e)}"
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
            logger.error(f"Failed to get narrative arc {arc_id}: {str(e)}")
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
            query = self.session.query(NarrativeArcEntity).filter_by(
                arc_type=arc_type
            )

            if status:
                query = query.filter_by(status=status)

            query = query.order_by(NarrativeArcEntity.updated_at.desc())

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            arc_entities = query.all()
            return [
                self._entity_to_aggregate(entity) for entity in arc_entities
            ]

        except Exception as e:
            logger.error(
                f"Failed to get narrative arcs by type {arc_type}: {str(e)}"
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
                query = query.filter(
                    NarrativeArcEntity.arc_type.in_(arc_types)
                )

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
            arcs = [
                self._entity_to_aggregate(entity) for entity in arc_entities
            ]

            return arcs, total_count

        except Exception as e:
            logger.error(f"Failed to search narrative arcs: {str(e)}")
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

            logger.debug(f"Deleted narrative arc: {arc_id}")
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"Failed to delete narrative arc {arc_id}: {str(e)}")
            raise

    def exists(self, arc_id: NarrativeId) -> bool:
        """Check if a narrative arc exists."""
        try:
            return (
                self.session.query(NarrativeArcEntity)
                .filter_by(id=arc_id.value)
                .count()
                > 0
            )
        except Exception as e:
            logger.error(
                f"Failed to check if narrative arc exists {arc_id}: {str(e)}"
            )
            raise

    def _create_arc_entity(
        self, narrative_arc: NarrativeArc
    ) -> NarrativeArcEntity:
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
            character_arcs={
                str(k): v for k, v in narrative_arc.character_arcs.items()
            },
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
            child_arc_ids=[
                str(cid.value) for cid in narrative_arc.child_arc_ids
            ],
            related_threads=[
                str(tid.value) for tid in narrative_arc.related_threads
            ],
            created_at=narrative_arc.created_at,
            updated_at=narrative_arc.updated_at,
            created_by=narrative_arc.created_by,
            tags=list(narrative_arc.tags),
            notes=narrative_arc.notes,
            arc_metadata=narrative_arc.metadata,
            version=narrative_arc._version,
        )

        # Add plot points
        for plot_point in narrative_arc.plot_points.values():
            plot_entity = self._create_plot_point_entity(
                plot_point, arc_entity.id
            )
            arc_entity.plot_points.append(plot_entity)

        # Add themes
        for theme in narrative_arc.themes.values():
            theme_entity = self._create_theme_entity(theme, arc_entity.id)
            arc_entity.themes.append(theme_entity)

        # Add pacing segments
        for pacing in narrative_arc.pacing_segments.values():
            pacing_entity = self._create_pacing_entity(pacing, arc_entity.id)
            arc_entity.pacing_segments.append(pacing_entity)

        # Add narrative contexts
        for context in narrative_arc.narrative_contexts.values():
            context_entity = self._create_context_entity(
                context, arc_entity.id
            )
            arc_entity.narrative_contexts.append(context_entity)

        return arc_entity

    def _update_arc_entity(
        self, arc_entity: NarrativeArcEntity, narrative_arc: NarrativeArc
    ) -> None:
        """Update existing SQLAlchemy entity from domain aggregate."""
        # Update basic fields
        arc_entity.arc_name = narrative_arc.arc_name
        arc_entity.arc_type = narrative_arc.arc_type
        arc_entity.description = narrative_arc.description
        arc_entity.plot_sequence = narrative_arc.plot_sequence
        arc_entity.theme_development = {
            k: v for k, v in narrative_arc.theme_development.items()
        }
        arc_entity.pacing_sequence = narrative_arc.pacing_sequence
        arc_entity.character_arcs = {
            str(k): v for k, v in narrative_arc.character_arcs.items()
        }
        arc_entity.target_length = narrative_arc.target_length
        arc_entity.current_length = narrative_arc.current_length
        arc_entity.completion_percentage = narrative_arc.completion_percentage
        arc_entity.complexity_score = narrative_arc.complexity_score
        arc_entity.status = narrative_arc.status
        arc_entity.start_sequence = narrative_arc.start_sequence
        arc_entity.end_sequence = narrative_arc.end_sequence
        arc_entity.narrative_coherence = narrative_arc.narrative_coherence
        arc_entity.thematic_consistency = narrative_arc.thematic_consistency
        arc_entity.pacing_effectiveness = narrative_arc.pacing_effectiveness
        arc_entity.updated_at = narrative_arc.updated_at
        arc_entity.tags = list(narrative_arc.tags)
        arc_entity.notes = narrative_arc.notes
        arc_entity.arc_metadata = narrative_arc.metadata
        arc_entity.version = narrative_arc._version

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
                plot_point, arc_entity.id
            )
            arc_entity.plot_points.append(plot_entity)

        for theme in narrative_arc.themes.values():
            theme_entity = self._create_theme_entity(theme, arc_entity.id)
            arc_entity.themes.append(theme_entity)

        for pacing in narrative_arc.pacing_segments.values():
            pacing_entity = self._create_pacing_entity(pacing, arc_entity.id)
            arc_entity.pacing_segments.append(pacing_entity)

        for context in narrative_arc.narrative_contexts.values():
            context_entity = self._create_context_entity(
                context, arc_entity.id
            )
            arc_entity.narrative_contexts.append(context_entity)

    def _create_plot_point_entity(
        self, plot_point: PlotPoint, arc_id: UUID
    ) -> PlotPointEntity:
        """Create PlotPoint entity from domain value object."""
        return PlotPointEntity(
            id=plot_point.plot_point_id,
            narrative_arc_id=arc_id,
            plot_point_type=cast(str, plot_point.plot_point_type.value),
            importance=cast(str, plot_point.importance.value),
            title=plot_point.title,
            description=plot_point.description,
            sequence_order=plot_point.sequence_order,
            emotional_intensity=cast(Decimal, plot_point.emotional_intensity),
            dramatic_tension=cast(Decimal, plot_point.dramatic_tension),
            story_significance=cast(Decimal, plot_point.story_significance),
            involved_characters=[
                str(cid) for cid in plot_point.involved_characters
            ],
            prerequisite_events=list(plot_point.prerequisite_events),
            consequence_events=list(plot_point.consequence_events),
            location=plot_point.location,
            time_context=plot_point.time_context,
            pov_character=plot_point.pov_character,
            outcome=plot_point.outcome,
            conflict_type=plot_point.conflict_type,
            thematic_relevance={
                k: float(v) for k, v in plot_point.thematic_relevance.items()
            },
            tags=list(plot_point.tags),
            notes=plot_point.notes or "",
        )

    def _create_theme_entity(
        self, theme: NarrativeTheme, arc_id: UUID
    ) -> NarrativeThemeEntity:
        """Create NarrativeTheme entity from domain value object."""
        return NarrativeThemeEntity(
            id=theme.theme_id,
            narrative_arc_id=arc_id,
            theme_type=cast(str, theme.theme_type.value),
            intensity=cast(str, theme.intensity.value),
            name=theme.name,
            description=theme.description,
            moral_complexity=cast(Decimal, theme.moral_complexity),
            emotional_resonance=cast(Decimal, theme.emotional_resonance),
            universal_appeal=cast(Decimal, theme.universal_appeal),
            cultural_significance=cast(Decimal, theme.cultural_significance),
            development_potential=cast(Decimal, theme.development_potential),
            symbolic_elements=list(theme.symbolic_elements),
            introduction_sequence=theme.introduction_sequence,
            resolution_sequence=theme.resolution_sequence,
            tags=list(theme.tags),
            notes=theme.notes or "",
        )

    def _create_pacing_entity(
        self, pacing: StoryPacing, arc_id: UUID
    ) -> StoryPacingEntity:
        """Create StoryPacing entity from domain value object."""
        # Handle StoryPacing fields with proper type safety
        tension_curve = getattr(pacing, "tension_curve", [])
        if tension_curve is None:
            tension_curve = []

        # Map StoryPacing fields to entity fields with backwards compatibility
        description_density = getattr(
            pacing, "vocabulary_density", Decimal("5.0")
        )
        character_focus = getattr(
            pacing, "character_focus", set()
        )  # This might not exist in StoryPacing
        narrative_techniques = getattr(
            pacing, "narrative_techniques", set()
        )  # This might not exist in StoryPacing
        reader_engagement_target = getattr(
            pacing,
            "reader_engagement_target",
            getattr(pacing, "emotional_target", ""),
        )

        return StoryPacingEntity(
            id=pacing.pacing_id,
            narrative_arc_id=arc_id,
            pacing_type=cast(str, pacing.pacing_type.value),
            base_intensity=cast(str, pacing.base_intensity.value),
            start_sequence=pacing.start_sequence,
            end_sequence=pacing.end_sequence,
            event_density=cast(Decimal, pacing.event_density),
            tension_curve=[float(t) for t in tension_curve],
            dialogue_ratio=cast(Decimal, pacing.dialogue_ratio),
            action_ratio=cast(Decimal, pacing.action_ratio),
            reflection_ratio=cast(Decimal, pacing.reflection_ratio),
            description_density=cast(Decimal, description_density),
            character_focus=[str(cid) for cid in character_focus]
            if character_focus
            else [],
            narrative_techniques=list(narrative_techniques)
            if narrative_techniques
            else [],
            reader_engagement_target=reader_engagement_target or "",
            tags=list(getattr(pacing, "tags", set())),
            notes=getattr(
                pacing, "notes", getattr(pacing, "pacing_notes", "")
            ),
        )

    def _create_context_entity(
        self, context: NarrativeContext, arc_id: UUID
    ) -> NarrativeContextEntity:
        """Create NarrativeContext entity from domain value object."""
        # Handle field mapping with type safety
        affected_characters = getattr(context, "affected_characters", set())
        related_themes = getattr(context, "related_themes", set())
        locations = getattr(context, "locations", set())

        # Map context fields to entity fields
        start_sequence = getattr(
            context,
            "applies_from_sequence",
            getattr(context, "start_sequence", None),
        )
        end_sequence = getattr(
            context,
            "applies_to_sequence",
            getattr(context, "end_sequence", None),
        )
        importance = getattr(
            context,
            "narrative_importance",
            getattr(context, "importance", Decimal("5.0")),
        )

        return NarrativeContextEntity(
            id=context.context_id,
            narrative_arc_id=arc_id,
            context_type=cast(
                str,
                context.context_type.value
                if hasattr(context.context_type, "value")
                else str(context.context_type),
            ),
            name=context.name,
            description=context.description,
            importance=cast(Decimal, importance),
            is_persistent=getattr(context, "is_persistent", True),
            start_sequence=start_sequence,
            end_sequence=end_sequence,
            location=list(locations)[0]
            if locations
            else getattr(context, "location", None),
            time_period=getattr(context, "time_period", None),
            mood=getattr(context, "mood", None),
            atmosphere=getattr(context, "atmosphere", None),
            social_context=getattr(context, "social_context", None),
            cultural_context=getattr(context, "cultural_context", None),
            affected_characters=[str(cid) for cid in affected_characters]
            if affected_characters
            else [],
            related_themes=list(related_themes) if related_themes else [],
            tags=list(getattr(context, "tags", set())),
            notes=getattr(context, "notes", ""),
        )

    def _entity_to_aggregate(
        self, arc_entity: NarrativeArcEntity
    ) -> NarrativeArc:
        """Convert SQLAlchemy entity to domain aggregate."""
        # Convert plot points with type safety
        plot_points = {}
        for plot_entity in arc_entity.plot_points:
            plot_point = ValueObjectFactory.create_plot_point_with_validation(
                plot_point_id=plot_entity.id,
                plot_point_type=plot_entity.plot_point_type,
                importance=plot_entity.importance,
                title=plot_entity.title,
                description=plot_entity.description,
                sequence_order=plot_entity.sequence_order,
                emotional_intensity=plot_entity.emotional_intensity,
                dramatic_tension=plot_entity.dramatic_tension,
                story_significance=plot_entity.story_significance,
                involved_characters=plot_entity.involved_characters or [],
                prerequisite_events=plot_entity.prerequisite_events or [],
                consequence_events=plot_entity.consequence_events or [],
                location=plot_entity.location,
                time_context=plot_entity.time_context,
                pov_character=plot_entity.pov_character,
                outcome=plot_entity.outcome,
                conflict_type=plot_entity.conflict_type,
                thematic_relevance=plot_entity.thematic_relevance or {},
                tags=plot_entity.tags or [],
                notes=plot_entity.notes or "",
            )
            plot_points[plot_point.plot_point_id] = plot_point

        # Convert themes with type safety
        themes = {}
        for theme_entity in arc_entity.themes:
            theme = ValueObjectFactory.create_narrative_theme_with_validation(
                theme_id=theme_entity.id,
                theme_type=theme_entity.theme_type,
                intensity=theme_entity.intensity,
                name=theme_entity.name,
                description=theme_entity.description,
                moral_complexity=theme_entity.moral_complexity,
                emotional_resonance=theme_entity.emotional_resonance,
                universal_appeal=theme_entity.universal_appeal,
                cultural_significance=theme_entity.cultural_significance,
                development_potential=theme_entity.development_potential,
                symbolic_elements=theme_entity.symbolic_elements or [],
                introduction_sequence=theme_entity.introduction_sequence,
                resolution_sequence=theme_entity.resolution_sequence,
                tags=theme_entity.tags or [],
                notes=theme_entity.notes or "",
            )
            themes[theme.theme_id] = theme

        # Convert pacing segments with type safety
        pacing_segments = {}
        for pacing_entity in arc_entity.pacing_segments:
            pacing = ValueObjectFactory.create_story_pacing_with_validation(
                pacing_id=pacing_entity.id,
                pacing_type=pacing_entity.pacing_type,
                base_intensity=pacing_entity.base_intensity,
                start_sequence=pacing_entity.start_sequence,
                end_sequence=pacing_entity.end_sequence,
                event_density=pacing_entity.event_density,
                tension_curve=pacing_entity.tension_curve or [],
                dialogue_ratio=pacing_entity.dialogue_ratio,
                action_ratio=pacing_entity.action_ratio,
                reflection_ratio=pacing_entity.reflection_ratio,
                description_density=pacing_entity.description_density,
                character_focus=pacing_entity.character_focus or [],
                narrative_techniques=pacing_entity.narrative_techniques or [],
                reader_engagement_target=pacing_entity.reader_engagement_target,
                tags=pacing_entity.tags or [],
                notes=pacing_entity.notes or "",
            )
            pacing_segments[pacing.pacing_id] = pacing

        # Convert narrative contexts with type safety
        narrative_contexts = {}
        for context_entity in arc_entity.narrative_contexts:
            context = (
                ValueObjectFactory.create_narrative_context_with_validation(
                    context_id=context_entity.id,
                    context_type=context_entity.context_type,
                    name=context_entity.name,
                    description=context_entity.description,
                    importance=context_entity.importance,
                    is_persistent=context_entity.is_persistent,
                    start_sequence=context_entity.start_sequence,
                    end_sequence=context_entity.end_sequence,
                    location=context_entity.location,
                    time_period=context_entity.time_period,
                    mood=context_entity.mood,
                    atmosphere=context_entity.atmosphere,
                    social_context=context_entity.social_context,
                    cultural_context=context_entity.cultural_context,
                    affected_characters=context_entity.affected_characters
                    or [],
                    related_themes=context_entity.related_themes or [],
                    tags=context_entity.tags or [],
                    notes=context_entity.notes or "",
                )
            )
            narrative_contexts[context.context_id] = context

        # Create the aggregate
        narrative_arc = NarrativeArc(
            arc_id=NarrativeId(arc_entity.id),
            arc_name=arc_entity.arc_name,
            arc_type=arc_entity.arc_type,
            description=arc_entity.description,
            plot_points=plot_points,
            plot_sequence=list(arc_entity.plot_sequence),
            themes=themes,
            theme_development=dict(arc_entity.theme_development),
            pacing_segments=pacing_segments,
            pacing_sequence=list(arc_entity.pacing_sequence),
            narrative_contexts=narrative_contexts,
            active_contexts=(
                set(arc_entity.active_contexts)
                if hasattr(arc_entity, "active_contexts")
                else set()
            ),
            primary_characters=(
                set(arc_entity.primary_characters)
                if hasattr(arc_entity, "primary_characters")
                else set()
            ),
            supporting_characters=(
                set(arc_entity.supporting_characters)
                if hasattr(arc_entity, "supporting_characters")
                else set()
            ),
            character_arcs={
                UUID(k): v for k, v in arc_entity.character_arcs.items()
            },
            target_length=arc_entity.target_length,
            current_length=arc_entity.current_length,
            completion_percentage=arc_entity.completion_percentage,
            complexity_score=arc_entity.complexity_score,
            status=arc_entity.status,
            start_sequence=arc_entity.start_sequence,
            end_sequence=arc_entity.end_sequence,
            narrative_coherence=arc_entity.narrative_coherence,
            thematic_consistency=arc_entity.thematic_consistency,
            pacing_effectiveness=arc_entity.pacing_effectiveness,
            parent_arc_id=(
                NarrativeId(arc_entity.parent_arc_id)
                if arc_entity.parent_arc_id
                else None
            ),
            child_arc_ids=set(
                NarrativeId(UUID(cid)) for cid in arc_entity.child_arc_ids
            ),
            related_threads=set(
                NarrativeId(UUID(tid)) for tid in arc_entity.related_threads
            ),
            created_at=arc_entity.created_at,
            updated_at=arc_entity.updated_at,
            created_by=arc_entity.created_by,
            tags=set(arc_entity.tags),
            notes=arc_entity.notes,
            metadata=dict(arc_entity.arc_metadata),
        )

        # Set internal version
        narrative_arc._version = arc_entity.version

        return narrative_arc
