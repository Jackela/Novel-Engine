#!/usr/bin/env python3
"""
SQLAlchemy TurnBrief Repository Implementation

This module provides a concrete implementation of ITurnBriefRepository
using SQLAlchemy ORM for data persistence. It handles the mapping between
domain objects and database entities.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ...domain.aggregates.turn_brief import TurnBrief
from ...domain.repositories.turn_brief_repository import (
    ConcurrencyException,
    ITurnBriefRepository,
    RepositoryException,
)
from ...domain.value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessModifier,
    AwarenessState,
)
from ...domain.value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeType,
)
from ...domain.value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionType,
)
from ...domain.value_objects.subjective_id import SubjectiveId
from ..persistence.subjective_models import KnowledgeItemORM, TurnBriefORM

logger = logging.getLogger(__name__)


class SQLAlchemyTurnBriefRepository(ITurnBriefRepository):
    """
    SQLAlchemy-based implementation of the TurnBrief repository.

    This repository provides persistence capabilities for TurnBrief
    aggregates using SQLAlchemy ORM and relational database storage.
    """

    def __init__(self, session_factory: sessionmaker):
        """
        Initialize the repository with a SQLAlchemy session factory.

        Args:
            session_factory: Factory for creating database sessions
        """
        self.session_factory = session_factory
        self.logger = logger.getChild(self.__class__.__name__)

    def get_by_id(self, turn_brief_id: SubjectiveId) -> Optional[TurnBrief]:
        """
        Retrieve a TurnBrief by its unique identifier.

        Args:
            turn_brief_id: The unique identifier for the TurnBrief

        Returns:
            The TurnBrief if found, None otherwise

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entity = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.turn_brief_id == turn_brief_id.value)
                    .first()
                )

                if orm_entity:
                    return self._map_orm_to_domain(orm_entity, session)
                return None

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error retrieving TurnBrief {turn_brief_id}: {e}"
            )
            raise RepositoryException(f"Failed to retrieve TurnBrief: {e}")

    def get_by_entity_id(self, entity_id: str) -> Optional[TurnBrief]:
        """
        Retrieve the current TurnBrief for a specific entity.

        Args:
            entity_id: The ID of the entity whose TurnBrief to retrieve

        Returns:
            The current TurnBrief for the entity if found, None otherwise

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entity = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.entity_id == entity_id)
                    .first()
                )

                if orm_entity:
                    return self._map_orm_to_domain(orm_entity, session)
                return None

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error retrieving TurnBrief for entity {entity_id}: {e}"
            )
            raise RepositoryException(
                f"Failed to retrieve TurnBrief for entity: {e}"
            )

    def save(self, turn_brief: TurnBrief) -> None:
        """
        Save a TurnBrief to persistent storage.

        Args:
            turn_brief: The TurnBrief to save

        Raises:
            ConcurrencyException: If a concurrency conflict occurs
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                # Check if this is an update (existing entity)
                existing_orm = (
                    session.query(TurnBriefORM)
                    .filter(
                        TurnBriefORM.turn_brief_id
                        == turn_brief.turn_brief_id.value
                    )
                    .first()
                )

                if existing_orm:
                    # Update existing entity
                    if existing_orm.version != turn_brief.version - 1:
                        raise ConcurrencyException(
                            f"Concurrency conflict for TurnBrief {turn_brief.turn_brief_id}. "
                            f"Expected version {turn_brief.version - 1}, got {existing_orm.version}"
                        )

                    self._update_orm_from_domain(
                        existing_orm, turn_brief, session
                    )
                else:
                    # Create new entity
                    new_orm = self._map_domain_to_orm(turn_brief)
                    session.add(new_orm)

                session.commit()
                self.logger.debug(
                    f"Saved TurnBrief {turn_brief.turn_brief_id}"
                )

        except ConcurrencyException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error saving TurnBrief {turn_brief.turn_brief_id}: {e}"
            )
            raise RepositoryException(f"Failed to save TurnBrief: {e}")

    def delete(self, turn_brief_id: SubjectiveId) -> bool:
        """
        Delete a TurnBrief from persistent storage.

        Args:
            turn_brief_id: The unique identifier of the TurnBrief to delete

        Returns:
            True if the TurnBrief was deleted, False if it didn't exist

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                deleted_count = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.turn_brief_id == turn_brief_id.value)
                    .delete()
                )

                session.commit()

                if deleted_count > 0:
                    self.logger.info(f"Deleted TurnBrief {turn_brief_id}")
                    return True
                else:
                    self.logger.warning(
                        f"TurnBrief {turn_brief_id} not found for deletion"
                    )
                    return False

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error deleting TurnBrief {turn_brief_id}: {e}"
            )
            raise RepositoryException(f"Failed to delete TurnBrief: {e}")

    def find_by_world_state_version(
        self, world_state_version: int
    ) -> List[TurnBrief]:
        """
        Find all TurnBriefs associated with a specific world state version.

        Args:
            world_state_version: The world state version to search for

        Returns:
            List of TurnBriefs for that world state version

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entities = (
                    session.query(TurnBriefORM)
                    .filter(
                        TurnBriefORM.world_state_version == world_state_version
                    )
                    .all()
                )

                return [
                    self._map_orm_to_domain(orm_entity, session)
                    for orm_entity in orm_entities
                ]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding TurnBriefs by world state version {world_state_version}: {e}"
            )
            raise RepositoryException(
                f"Failed to find TurnBriefs by world state version: {e}"
            )

    def find_by_alertness_level(
        self, alertness: AlertnessLevel
    ) -> List[TurnBrief]:
        """
        Find all TurnBriefs with entities at a specific alertness level.

        Args:
            alertness: The alertness level to search for

        Returns:
            List of TurnBriefs with entities at the specified alertness level

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entities = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.current_alertness == alertness.value)
                    .all()
                )

                return [
                    self._map_orm_to_domain(orm_entity, session)
                    for orm_entity in orm_entities
                ]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding TurnBriefs by alertness level {alertness}: {e}"
            )
            raise RepositoryException(
                f"Failed to find TurnBriefs by alertness level: {e}"
            )

    def find_stale_turn_briefs(self, cutoff_time: datetime) -> List[TurnBrief]:
        """
        Find TurnBriefs that haven't been updated since the cutoff time.

        Args:
            cutoff_time: The cutoff time for staleness

        Returns:
            List of stale TurnBriefs

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entities = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.updated_at < cutoff_time)
                    .all()
                )

                return [
                    self._map_orm_to_domain(orm_entity, session)
                    for orm_entity in orm_entities
                ]

        except SQLAlchemyError as e:
            self.logger.error(f"Database error finding stale TurnBriefs: {e}")
            raise RepositoryException(f"Failed to find stale TurnBriefs: {e}")

    def find_entities_with_knowledge_about(
        self,
        subject: str,
        min_certainty: CertaintyLevel = CertaintyLevel.MINIMAL,
    ) -> List[str]:
        """
        Find all entities that have knowledge about a specific subject.

        Args:
            subject: The subject to search for knowledge about
            min_certainty: Minimum certainty level required

        Returns:
            List of entity IDs that have knowledge about the subject

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                # Get certainty level ordering
                certainty_order = {
                    CertaintyLevel.UNKNOWN: 0,
                    CertaintyLevel.MINIMAL: 1,
                    CertaintyLevel.LOW: 2,
                    CertaintyLevel.MEDIUM: 3,
                    CertaintyLevel.HIGH: 4,
                    CertaintyLevel.ABSOLUTE: 5,
                }
                min_certainty_value = certainty_order[min_certainty]

                # Query for TurnBriefs that have knowledge items about the subject
                # with sufficient certainty
                results = (
                    session.query(TurnBriefORM.entity_id)
                    .join(KnowledgeItemORM)
                    .filter(
                        and_(
                            KnowledgeItemORM.subject == subject,
                            func.coalesce(
                                KnowledgeItemORM.expires_at, func.now()
                            )
                            > func.now(),
                        )
                    )
                    .distinct()
                    .all()
                )

                # Filter by certainty level (simplified - in production, this would be more sophisticated)
                entity_ids = []
                for result in results:
                    entity_id = result[0]
                    # Get the best certainty level for this entity about the subject
                    best_certainty = (
                        session.query(KnowledgeItemORM.certainty_level)
                        .filter(
                            and_(
                                KnowledgeItemORM.turn_brief_id
                                == session.query(TurnBriefORM.turn_brief_id)
                                .filter(TurnBriefORM.entity_id == entity_id)
                                .scalar(),
                                KnowledgeItemORM.subject == subject,
                            )
                        )
                        .first()
                    )

                    if best_certainty and best_certainty[0]:
                        try:
                            cert_level = CertaintyLevel(best_certainty[0])
                            if (
                                certainty_order.get(cert_level, 0)
                                >= min_certainty_value
                            ):
                                entity_ids.append(entity_id)
                        except ValueError:
                            continue

                return entity_ids

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding entities with knowledge about {subject}: {e}"
            )
            raise RepositoryException(
                f"Failed to find entities with knowledge: {e}"
            )

    def find_entities_in_perception_range_of_location(
        self,
        location_id: str,
        perception_type: Optional[PerceptionType] = None,
    ) -> List[str]:
        """
        Find all entities that can perceive a specific location.

        Args:
            location_id: The location to check perception for
            perception_type: Specific perception type to check (None for any)

        Returns:
            List of entity IDs that can perceive the location

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                # This is a simplified implementation - in production, this would involve
                # complex spatial queries and perception capability analysis
                orm_entities = session.query(TurnBriefORM).all()

                entity_ids = []
                for orm_entity in orm_entities:
                    # Check if entity's visible subjects include the location
                    visible_subjects = orm_entity.visible_subjects or {}
                    if location_id in visible_subjects:
                        entity_ids.append(orm_entity.entity_id)

                return entity_ids

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding entities that can perceive location {location_id}: {e}"
            )
            raise RepositoryException(
                f"Failed to find entities in perception range: {e}"
            )

    def find_entities_with_perception_type(
        self, perception_type: PerceptionType
    ) -> List[str]:
        """
        Find all entities that have a specific type of perception.

        Args:
            perception_type: The type of perception to search for

        Returns:
            List of entity IDs with that perception type

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                orm_entities = session.query(TurnBriefORM).all()

                entity_ids = []
                for orm_entity in orm_entities:
                    perception_capabilities = (
                        orm_entity.perception_capabilities or {}
                    )
                    if perception_type.value in perception_capabilities.get(
                        "perception_ranges", {}
                    ):
                        entity_ids.append(orm_entity.entity_id)

                return entity_ids

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding entities with perception type {perception_type}: {e}"
            )
            raise RepositoryException(
                f"Failed to find entities with perception type: {e}"
            )

    def get_knowledge_sharing_candidates(
        self,
        entity_id: str,
        knowledge_type: KnowledgeType,
        max_distance: Optional[float] = None,
    ) -> List[str]:
        """
        Find entities that could potentially share or receive knowledge with the given entity.

        Args:
            entity_id: The entity looking to share knowledge
            knowledge_type: The type of knowledge to share
            max_distance: Maximum distance for sharing (None for unlimited)

        Returns:
            List of entity IDs that are candidates for knowledge sharing

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                # Simplified implementation - in production would involve spatial queries
                candidates = (
                    session.query(TurnBriefORM.entity_id)
                    .filter(
                        and_(
                            TurnBriefORM.entity_id != entity_id,
                            TurnBriefORM.current_alertness != "unconscious",
                        )
                    )
                    .all()
                )

                return [candidate[0] for candidate in candidates]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error finding knowledge sharing candidates for {entity_id}: {e}"
            )
            raise RepositoryException(
                f"Failed to find knowledge sharing candidates: {e}"
            )

    def count_total_turn_briefs(self) -> int:
        """
        Count the total number of TurnBriefs in the repository.

        Returns:
            The total count of TurnBriefs

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                return session.query(func.count(TurnBriefORM.id)).scalar()

        except SQLAlchemyError as e:
            self.logger.error(f"Database error counting total TurnBriefs: {e}")
            raise RepositoryException(f"Failed to count TurnBriefs: {e}")

    def count_active_turn_briefs(
        self, cutoff_time: Optional[datetime] = None
    ) -> int:
        """
        Count TurnBriefs that have been updated recently (are considered active).

        Args:
            cutoff_time: The cutoff time for considering a TurnBrief active
                        (defaults to 1 hour ago if None)

        Returns:
            The count of active TurnBriefs

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            if cutoff_time is None:
                cutoff_time = datetime.now() - timedelta(hours=1)

            with self.session_factory() as session:
                return (
                    session.query(func.count(TurnBriefORM.id))
                    .filter(TurnBriefORM.updated_at > cutoff_time)
                    .scalar()
                )

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error counting active TurnBriefs: {e}"
            )
            raise RepositoryException(
                f"Failed to count active TurnBriefs: {e}"
            )

    def get_entities_needing_updates(
        self, world_state_version: int
    ) -> List[str]:
        """
        Get entities whose TurnBriefs need updates for a new world state version.

        Args:
            world_state_version: The new world state version

        Returns:
            List of entity IDs that need TurnBrief updates

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                results = (
                    session.query(TurnBriefORM.entity_id)
                    .filter(
                        TurnBriefORM.world_state_version < world_state_version
                    )
                    .all()
                )

                return [result[0] for result in results]

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error getting entities needing updates: {e}"
            )
            raise RepositoryException(
                f"Failed to get entities needing updates: {e}"
            )

    def batch_update_world_state_version(
        self, entity_ids: List[str], new_version: int
    ) -> int:
        """
        Update the world state version for multiple TurnBriefs in a batch operation.

        Args:
            entity_ids: List of entity IDs to update
            new_version: The new world state version

        Returns:
            The number of TurnBriefs actually updated

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                updated_count = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.entity_id.in_(entity_ids))
                    .update(
                        {
                            "world_state_version": new_version,
                            "last_world_update": func.now(),
                            "updated_at": func.now(),
                        },
                        synchronize_session=False,
                    )
                )

                session.commit()

                self.logger.info(
                    f"Batch updated {updated_count} TurnBriefs to world state version {new_version}"
                )
                return updated_count

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in batch update: {e}")
            raise RepositoryException(
                f"Failed to batch update world state version: {e}"
            )

    def cleanup_expired_turn_briefs(self, expiration_time: datetime) -> int:
        """
        Remove or mark as expired TurnBriefs older than the expiration time.

        Args:
            expiration_time: The time before which TurnBriefs should be expired

        Returns:
            The number of TurnBriefs cleaned up

        Raises:
            RepositoryException: If a repository error occurs
        """
        try:
            with self.session_factory() as session:
                deleted_count = (
                    session.query(TurnBriefORM)
                    .filter(TurnBriefORM.updated_at < expiration_time)
                    .delete()
                )

                session.commit()

                self.logger.info(
                    f"Cleaned up {deleted_count} expired TurnBriefs"
                )
                return deleted_count

        except SQLAlchemyError as e:
            self.logger.error(
                f"Database error cleaning up expired TurnBriefs: {e}"
            )
            raise RepositoryException(
                f"Failed to cleanup expired TurnBriefs: {e}"
            )

    # Private mapping methods

    def _map_domain_to_orm(self, turn_brief: TurnBrief) -> TurnBriefORM:
        """Map domain TurnBrief to ORM entity."""
        return TurnBriefORM(
            id=str(uuid4()),
            turn_brief_id=turn_brief.turn_brief_id.value,
            entity_id=turn_brief.entity_id,
            world_state_version=turn_brief.world_state_version,
            last_world_update=turn_brief.last_world_update,
            last_perception_update=turn_brief.last_perception_update,
            base_alertness=turn_brief.awareness_state.base_alertness.value,
            current_alertness=turn_brief.awareness_state.current_alertness.value,
            attention_focus=turn_brief.awareness_state.attention_focus.value,
            focus_target=turn_brief.awareness_state.focus_target,
            awareness_modifiers=self._serialize_awareness_modifiers(
                turn_brief.awareness_state.awareness_modifiers
            ),
            fatigue_level=turn_brief.awareness_state.fatigue_level,
            stress_level=turn_brief.awareness_state.stress_level,
            perception_capabilities=self._serialize_perception_capabilities(
                turn_brief.perception_capabilities
            ),
            visible_subjects=self._serialize_visible_subjects(
                turn_brief.visible_subjects
            ),
            known_threats=turn_brief.known_threats,
            created_at=turn_brief.created_at,
            updated_at=turn_brief.updated_at,
            version=turn_brief.version,
        )

    def _update_orm_from_domain(
        self, orm_entity: TurnBriefORM, turn_brief: TurnBrief, session: Session
    ) -> None:
        """Update existing ORM entity from domain object."""
        orm_entity.world_state_version = turn_brief.world_state_version
        orm_entity.last_world_update = turn_brief.last_world_update
        orm_entity.last_perception_update = turn_brief.last_perception_update
        orm_entity.base_alertness = (
            turn_brief.awareness_state.base_alertness.value
        )
        orm_entity.current_alertness = (
            turn_brief.awareness_state.current_alertness.value
        )
        orm_entity.attention_focus = (
            turn_brief.awareness_state.attention_focus.value
        )
        orm_entity.focus_target = turn_brief.awareness_state.focus_target
        orm_entity.awareness_modifiers = self._serialize_awareness_modifiers(
            turn_brief.awareness_state.awareness_modifiers
        )
        orm_entity.fatigue_level = turn_brief.awareness_state.fatigue_level
        orm_entity.stress_level = turn_brief.awareness_state.stress_level
        orm_entity.perception_capabilities = (
            self._serialize_perception_capabilities(
                turn_brief.perception_capabilities
            )
        )
        orm_entity.visible_subjects = self._serialize_visible_subjects(
            turn_brief.visible_subjects
        )
        orm_entity.known_threats = turn_brief.known_threats
        orm_entity.updated_at = turn_brief.updated_at
        orm_entity.version = turn_brief.version

    def _map_orm_to_domain(
        self, orm_entity: TurnBriefORM, session: Session
    ) -> TurnBrief:
        """Map ORM entity to domain TurnBrief."""
        # This is a simplified mapping - in production, you'd need full serialization/deserialization
        # For now, we'll create a basic TurnBrief that can be used for testing

        # Create basic domain objects (simplified)
        subjective_id = SubjectiveId(orm_entity.turn_brief_id)

        # Load knowledge base from related knowledge items
        (
            session.query(KnowledgeItemORM)
            .filter(KnowledgeItemORM.turn_brief_id == orm_entity.turn_brief_id)
            .all()
        )

        # This would need proper deserialization in production
        knowledge_base = KnowledgeBase(knowledge_items={})

        # Create awareness state (simplified)
        awareness_state = AwarenessState(
            base_alertness=AlertnessLevel(orm_entity.base_alertness),
            current_alertness=AlertnessLevel(orm_entity.current_alertness),
            attention_focus=AttentionFocus(orm_entity.attention_focus),
            focus_target=orm_entity.focus_target,
            awareness_modifiers=self._deserialize_awareness_modifiers(
                orm_entity.awareness_modifiers
            ),
            fatigue_level=orm_entity.fatigue_level,
            stress_level=orm_entity.stress_level,
        )

        # Create perception capabilities (simplified)
        perception_capabilities = self._deserialize_perception_capabilities(
            orm_entity.perception_capabilities
        )

        # Create visible subjects
        visible_subjects = self._deserialize_visible_subjects(
            orm_entity.visible_subjects
        )

        # Create TurnBrief
        turn_brief = TurnBrief(
            turn_brief_id=subjective_id,
            entity_id=orm_entity.entity_id,
            world_state_version=orm_entity.world_state_version,
            last_world_update=orm_entity.last_world_update,
            perception_capabilities=perception_capabilities,
            awareness_state=awareness_state,
            knowledge_base=knowledge_base,
            visible_subjects=visible_subjects,
            known_threats=orm_entity.known_threats or {},
            created_at=orm_entity.created_at,
            updated_at=orm_entity.updated_at,
            last_perception_update=orm_entity.last_perception_update,
            version=orm_entity.version,
        )

        return turn_brief

    def _serialize_awareness_modifiers(
        self, modifiers: Dict[AwarenessModifier, float]
    ) -> Dict[str, float]:
        """Serialize awareness modifiers for JSON storage."""
        return {modifier.value: value for modifier, value in modifiers.items()}

    def _deserialize_awareness_modifiers(
        self, data: Optional[Dict[str, Any]]
    ) -> Dict[AwarenessModifier, float]:
        """Deserialize awareness modifiers from JSON storage."""
        if not data:
            return {}

        result = {}
        for key, value in data.items():
            try:
                modifier = AwarenessModifier(key)
                result[modifier] = float(value)
            except (ValueError, TypeError):
                continue

        return result

    def _serialize_perception_capabilities(
        self, capabilities: PerceptionCapabilities
    ) -> Dict[str, Any]:
        """Serialize perception capabilities for JSON storage."""
        # Simplified serialization - would need full implementation in production
        return {
            "passive_awareness_bonus": capabilities.passive_awareness_bonus,
            "focused_perception_multiplier": capabilities.focused_perception_multiplier,
            "perception_ranges": {},  # Would need proper serialization
        }

    def _deserialize_perception_capabilities(
        self, data: Optional[Dict[str, Any]]
    ) -> PerceptionCapabilities:
        """Deserialize perception capabilities from JSON storage."""
        # Simplified deserialization - would need full implementation in production
        if not data:
            # Create minimal perception capabilities
            from ...domain.value_objects.perception_range import (
                PerceptionRange,
            )

            basic_visual = PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=10.0,
                effective_range=10.0,
                accuracy_modifier=0.8,
                environmental_modifiers={},
            )
            return PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: basic_visual}
            )

        # Would implement proper deserialization here
        basic_visual = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=10.0,
            effective_range=10.0,
            accuracy_modifier=0.8,
            environmental_modifiers={},
        )
        return PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: basic_visual},
            passive_awareness_bonus=data.get("passive_awareness_bonus", 0.0),
            focused_perception_multiplier=data.get(
                "focused_perception_multiplier", 1.5
            ),
        )

    def _serialize_visible_subjects(
        self, subjects: Dict[str, Any]
    ) -> Dict[str, str]:
        """Serialize visible subjects for JSON storage."""
        return {
            subject: str(level.value)
            if hasattr(level, "value")
            else str(level)
            for subject, level in subjects.items()
        }

    def _deserialize_visible_subjects(
        self, data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Deserialize visible subjects from JSON storage."""
        if not data:
            return {}

        from ...domain.value_objects.perception_range import VisibilityLevel

        result = {}
        for subject, level_str in data.items():
            try:
                level = VisibilityLevel(level_str)
                result[subject] = level
            except ValueError:
                continue

        return result
